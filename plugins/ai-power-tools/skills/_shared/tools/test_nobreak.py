#!/usr/bin/env python3
"""The no-break snapshot: a model that was generated before must still be generated.

    python -m pytest plugins/ai-power-tools/skills/_shared/tools/test_nobreak.py -q

`fixtures/nobreak-before/` holds the semantic model's TMDL files exactly as the generator
wrote them, for `fixtures/westbrook.definition.json`, import mode and the project name
`Westbrook`, BEFORE the Power BI Copilot-readiness changes. They are committed once and
never regenerated: regenerating them would erase the very difference this test exists to
see. They are committed with LF line endings, like every shipped skill file; the
test restores the generator's CRLF when it reads them.

The test parses the committed files and a fresh generation into objects (tables, columns,
measures, partitions, relationships) and asserts that every old object is still there with
every property identical. Four kinds of change are allowed, and only these:

  (a) a `description` (`///` line) where the old object had none;
  (b) `isHidden` on the key columns in `HIDDEN_KEY_COLUMNS`, in business tables only;
  (c) added measures;
  (d) a relationship renamed through `RELATIONSHIP_RENAMES` (empty for this fixture).

Anything else fails, naming the object and the property.
"""
from __future__ import annotations

# The relationship-name rule change is only allowed to rename what the map lists.
PINS = ("APT-2026-0364",)

import json
from dataclasses import dataclass, field
from pathlib import Path

import pytest

import powerbi_model

HERE = Path(__file__).parent
FIXTURE = HERE / "fixtures" / "westbrook.definition.json"
BEFORE = HERE / "fixtures" / "nobreak-before"
PROJECT_NAME = "Westbrook"

#: (b) The key columns that may become hidden. Business tables only: a physical
#: (`t_`) table's columns are not in this set because the table is hidden already.
HIDDEN_KEY_COLUMNS = frozenset(
    {"ea_guid", "source_guid", "target_guid", "connector_guid", "connector_id", "property_id"})

#: Physical tables, whose names start with this, are outside allowance (b).
PHYSICAL_PREFIX = "t_"

#: (d) Relationship renames, old name -> new name. Empty: the fixture has no duplicate
#: relationship name, so the duplicate-suffix rule renames nothing in it.
RELATIONSHIP_RENAMES: dict[str, str] = {}

#: Property values TMDL leaves out when they are the default.
_DEFAULTS = {"isActive": "true", "crossFilteringBehavior": "automatic"}

_OBJECT_KINDS = ("table", "relationship", "column", "measure", "partition")


# ------------------------------------------------------------------ TMDL reader


@dataclass
class Node:
    kind: str
    name: str
    description: str = ""
    #: What follows `=` on the header line, plus its continuation lines (a measure's DAX).
    expression: str = ""
    props: dict[str, str] = field(default_factory=dict)
    children: dict[tuple[str, str], "Node"] = field(default_factory=dict)


def _split_name(rest: str) -> tuple[str, str]:
    """`'a b' = x` -> (`a b`, `= x`); `a = x` -> (`a`, `= x`)."""
    rest = rest.strip()
    if rest.startswith("'"):
        i = 1
        while True:
            j = rest.index("'", i)
            if rest[j + 1:j + 2] == "'":
                i = j + 2
                continue
            return rest[1:j].replace("''", "'"), rest[j + 1:].strip()
    name, _, tail = rest.partition(" ")
    return name, tail.strip()


def _indent(line: str) -> int:
    return len(line) - len(line.lstrip("\t"))


def _parse_children(lines: list[str], i: int, depth: int, parent: Node) -> int:
    """Parse the lines at `depth` under `parent`, starting at `i`; return the next index."""
    pending: list[str] = []
    #: Where a deeper-indented line (the continuation of a multi-line value) goes.
    sink: tuple[str, str] | None = None
    while i < len(lines):
        line = lines[i]
        if not line.strip():
            i += 1
            continue
        d = _indent(line)
        if d < depth:
            break
        body = line[d:]
        if d > depth:
            if sink is None:
                raise ValueError(f"unexpected indentation at line {i + 1}: {line!r}")
            kind, key = sink
            if kind == "expression":
                parent.expression += "\n" + body
            else:
                parent.props[key] += "\n" + body
            i += 1
            continue
        i += 1
        sink = None
        if body.startswith("///"):
            pending.append(body[3:].strip())
            continue
        word, _, rest = body.partition(" ")
        if word in _OBJECT_KINDS:
            name, tail = _split_name(rest)
            node = Node(word, name, description=" ".join(pending))
            pending = []
            if tail.startswith("="):
                node.expression = tail[1:].strip()
            key = (word, name)
            if key in parent.children:
                raise ValueError(f"{parent.kind} {parent.name!r} declares {word} {name!r} twice")
            parent.children[key] = node
            i = _parse_children(lines, i, depth + 1, node)
            continue
        if pending:
            raise ValueError(f"a description precedes {body!r}, which cannot carry one")
        if word == "annotation":
            name, _, value = rest.partition(" = ")
            parent.props[f"annotation {name}"] = value
        elif word.endswith(":"):
            parent.props[word[:-1]] = rest.strip()
        elif rest.startswith("="):
            parent.props[word] = rest[1:].strip()
            sink = ("prop", word)
        elif rest == "":
            parent.props[word] = "true"
        else:
            raise ValueError(f"cannot read the property line {body!r}")
    return i


def parse_tmdl(text: str) -> list[Node]:
    """The top-level objects of one TMDL file."""
    root = Node("file", "")
    _parse_children(text.split("\r\n"), 0, 0, root)
    return list(root.children.values())


@dataclass
class ReadModel:
    tables: dict[str, Node]
    relationships: dict[str, Node]


def read_model(files: dict[str, str]) -> ReadModel:
    """`files` is keyed by path relative to `definition/`."""
    tables: dict[str, Node] = {}
    relationships: dict[str, Node] = {}
    for rel, text in files.items():
        if rel.startswith("tables/"):
            for node in parse_tmdl(text):
                assert node.kind == "table", f"{rel} declares a {node.kind}"
                assert node.name not in tables, f"table {node.name!r} is declared twice"
                tables[node.name] = node
        elif rel == "relationships.tmdl":
            for node in parse_tmdl(text):
                assert node.kind == "relationship", f"{rel} declares a {node.kind}"
                assert node.name not in relationships, f"relationship {node.name!r} twice"
                relationships[node.name] = node
    return ReadModel(tables, relationships)


# ----------------------------------------------------------------- comparison


def _norm(props: dict[str, str]) -> dict[str, str]:
    return {k: v for k, v in props.items() if _DEFAULTS.get(k) != v}


def _compare_properties(label: str, old: Node, new: Node, problems: list[str],
                        *, hide_allowed: bool = False) -> None:
    if old.description != new.description and old.description:
        problems.append(f"{label}: description changed from {old.description!r} to "
                        f"{new.description!r}")
    # (a) a description set where there was none is allowed, anything else is not.
    if old.expression != new.expression:
        problems.append(f"{label}: expression changed from {old.expression!r} to "
                        f"{new.expression!r}")
    a, b = _norm(old.props), _norm(new.props)
    for key in sorted(set(a) | set(b)):
        if a.get(key) == b.get(key):
            continue
        if key == "isHidden" and hide_allowed and key not in a and b[key] == "true":
            continue  # (b)
        problems.append(f"{label}: property {key!r} changed from {a.get(key)!r} to "
                        f"{b.get(key)!r}")


def _compare_children(label: str, old: Node, new: Node, kind: str, problems: list[str],
                      *, hide_allowed=lambda name: False, added_ok: bool = False) -> None:
    olds = {n: c for (k, n), c in old.children.items() if k == kind}
    news = {n: c for (k, n), c in new.children.items() if k == kind}
    for name, oc in olds.items():
        nc = news.get(name)
        child_label = f"{label} {kind} {name!r}"
        if nc is None:
            problems.append(f"{child_label}: missing from the new model")
            continue
        _compare_properties(child_label, oc, nc, problems, hide_allowed=hide_allowed(name))
    for name in news:
        if name not in olds and not added_ok:
            problems.append(f"{label} {kind} {name!r}: added, which no allowance covers")


def compare(before: ReadModel, after: ReadModel, *,
            renames: dict[str, str] | None = None) -> list[str]:
    """Every difference the allowances do not cover, each naming the object and property."""
    renames = RELATIONSHIP_RENAMES if renames is None else renames
    problems: list[str] = []
    for tname, old in before.tables.items():
        label = f"table {tname!r}"
        new = after.tables.get(tname)
        if new is None:
            problems.append(f"{label}: missing from the new model")
            continue
        _compare_properties(label, old, new, problems)
        business = not tname.startswith(PHYSICAL_PREFIX)
        _compare_children(label, old, new, "column", problems,
                          hide_allowed=lambda c, b=business: b and c in HIDDEN_KEY_COLUMNS)
        _compare_children(label, old, new, "measure", problems, added_ok=True)  # (c)
        _compare_children(label, old, new, "partition", problems)
    for tname in after.tables:
        if tname not in before.tables:
            problems.append(f"table {tname!r}: added, which no allowance covers")
    mapped = {renames.get(name, name) for name in before.relationships}
    for old_name, old in before.relationships.items():
        new_name = renames.get(old_name, old_name)
        label = f"relationship {old_name!r}"
        new = after.relationships.get(new_name)
        if new is None:
            problems.append(f"{label}: missing from the new model"
                            + (f" (expected as {new_name!r})" if new_name != old_name else ""))
            continue
        _compare_properties(label, old, new, problems)
    for name in after.relationships:
        if name not in mapped:
            problems.append(f"relationship {name!r}: added, which no allowance covers")
    return problems


# ------------------------------------------------------------------- fixtures


def _before_files() -> dict[str, str]:
    files = {}
    for path in sorted(BEFORE.rglob("*.tmdl")):
        # Committed as LF (skills ship LF only); the generator writes CRLF, as Power BI does.
        text = path.read_bytes().decode("utf-8").replace("\r\n", "\n").replace("\n", "\r\n")
        files[path.relative_to(BEFORE).as_posix()] = text
    return files


def _generated_files() -> dict[str, str]:
    defn = json.loads(FIXTURE.read_text(encoding="utf-8"))
    files = powerbi_model.project_files_from_definition(defn, PROJECT_NAME, mode="import")
    prefix = f"{PROJECT_NAME}.SemanticModel/definition/"
    return {k[len(prefix):]: v for k, v in files.items() if k.startswith(prefix)}


@pytest.fixture(scope="module")
def before_files():
    return _before_files()


@pytest.fixture(scope="module")
def before(before_files):
    return read_model(before_files)


@pytest.fixture(scope="module")
def after():
    return read_model(_generated_files())


# ---------------------------------------------------------------------- tests


def test_the_committed_before_files_are_lf_and_read_back_as_crlf(before_files):
    # Skills ship LF only (the gate refuses CRLF assets); the reader restores the
    # generator's CRLF, so the comparison sees what the generator wrote.
    assert before_files
    for rel, text in before_files.items():
        raw = (BEFORE / rel).read_bytes()
        assert b"\r" not in raw, f"{rel} is committed with CR characters"
        assert "\n" not in text.replace("\r\n", ""), f"{rel} reads back with a bare LF"
        assert not raw.startswith(b"\xef\xbb\xbf"), f"{rel} starts with a BOM"


def test_the_before_snapshot_is_the_whole_fixture_model(before):
    defn = json.loads(FIXTURE.read_text(encoding="utf-8"))
    assert len(before.tables) == (len(powerbi_model._business_specs(defn))
                                  + len(defn["physical"]))
    assert len(before.relationships) == 74
    assert sum(1 for t in before.tables.values()
               for (k, _n) in t.children if k == "measure") > 0


def test_the_generator_still_produces_everything_it_produced(before, after):
    problems = compare(before, after)
    assert not problems, "the generated model broke the no-break list:\n  " + "\n  ".join(problems)


def test_the_fixture_renames_no_relationship():
    assert RELATIONSHIP_RENAMES == {}


def test_the_fixture_has_no_relationship_whose_name_the_duplicate_rule_could_touch(before):
    # Zero renames is a property of the fixture: no old name ends in a counter.
    assert not [n for n in before.relationships if n.rsplit("_", 1)[-1].isdigit()]


# ------------------------------------------- the comparison itself is not vacuous


def _mutated(before_files, mutate):
    files = dict(before_files)
    mutate(files)
    return read_model(files)


def _swap(rel: str, old: str, new: str, count: int = 1):
    def mutate(files):
        assert old in files[rel], f"{old!r} not in {rel}"
        files[rel] = files[rel].replace(old, new, count)
    return mutate


BA = "tables/Business Application.tmdl"
OBJ = "tables/t_object.tmdl"


def test_an_unchanged_model_has_no_difference(before_files, before):
    assert compare(before, read_model(dict(before_files))) == []


@pytest.mark.parametrize("prop,old,new", [
    ("lineageTag", "\t\tlineageTag: ", "\t\tlineageTag: x-"),
    ("dataType", "\t\tdataType: string", "\t\tdataType: int64"),
    ("summarizeBy", "\t\tsummarizeBy: none", "\t\tsummarizeBy: sum"),
    ("sourceColumn", "\t\tsourceColumn: name", "\t\tsourceColumn: nam"),
])
def test_a_changed_column_property_is_reported_with_its_object_and_property(
        before_files, before, prop, old, new):
    after = _mutated(before_files, _swap(BA, old, new))
    problems = compare(before, after)
    assert problems and all("Business Application" in p for p in problems)
    assert any(f"property {prop!r}" in p for p in problems), problems


def test_a_changed_partition_expression_is_reported(before_files, before):
    after = _mutated(before_files, _swap(BA, "Item=", "Item=x"))
    problems = compare(before, after)
    assert any("partition" in p and "property 'source'" in p for p in problems), problems


def test_a_changed_relationship_property_is_reported(before_files, before):
    after = _mutated(before_files, _swap("relationships.tmdl", "\tisActive: false\r\n",
                                         "", 1))
    problems = compare(before, after)
    assert any("property 'isActive'" in p for p in problems), problems
    after = _mutated(before_files, _swap("relationships.tmdl", "\tfromColumn: ",
                                         "\tcrossFilteringBehavior: bothDirections\r\n"
                                         "\tfromColumn: "))
    assert any("property 'crossFilteringBehavior'" in p
               for p in compare(before, after))
    after = _mutated(before_files, _swap("relationships.tmdl", "toColumn: 'AI Gateway'",
                                         "toColumn: 'AI Service'"))
    assert any("property 'toColumn'" in p for p in compare(before, after))


def test_a_changed_measure_expression_is_reported(before_files, before):
    rel = "tables/Con_Business Application Flows Business Application.tmdl"
    after = _mutated(before_files, _swap(rel, "COUNTROWS(", "COUNT("))
    assert any("measure" in p and "expression changed" in p
               for p in compare(before, after))


def test_a_removed_object_is_reported(before_files, before):
    gone = dict(before_files)
    del gone[BA]
    assert any("Business Application" in p and "missing" in p
               for p in compare(before, read_model(gone)))
    rel = "tables/Con_Business Application Flows Business Application.tmdl"
    lines = before_files[rel].split("\r\n")
    at = next(i for i, ln in enumerate(lines) if ln.startswith("\tmeasure "))
    kept = lines[:at - 1] + lines[at + 2:]  # its description, the measure, its formatString
    no_measure = dict(before_files, **{rel: "\r\n".join(kept)})
    assert any("measure 'Flows by target Business Application'" in p and "missing" in p
               for p in compare(before, read_model(no_measure)))


def test_allowance_a_a_description_where_there_was_none(before_files, before):
    after = _mutated(before_files, _swap(BA, "\tcolumn name\r\n",
                                         "\t/// The application's name.\r\n\tcolumn name\r\n"))
    assert compare(before, after) == []


def test_a_changed_existing_description_is_reported(before_files, before):
    described = _mutated(before_files, _swap(BA, "\tcolumn name\r\n",
                                             "\t/// One.\r\n\tcolumn name\r\n"))
    after = _mutated(before_files, _swap(BA, "\tcolumn name\r\n",
                                         "\t/// Two.\r\n\tcolumn name\r\n"))
    problems = compare(described, after)
    assert any("description changed" in p for p in problems), problems


def test_allowance_b_hidden_key_on_a_business_table_only(before_files, before):
    hide = "\tcolumn ea_guid\r\n\t\tisHidden\r\n"
    after = _mutated(before_files, _swap(BA, "\tcolumn ea_guid\r\n", hide))
    assert compare(before, after) == []
    # not a key column
    other = _mutated(before_files, _swap(BA, "\tcolumn name\r\n", "\tcolumn name\r\n\t\tisHidden\r\n"))
    assert any("column 'name'" in p and "property 'isHidden'" in p
               for p in compare(before, other))
    # not a business table
    physical = _mutated(before_files, _swap(OBJ, "\tcolumn ea_guid\r\n",
                                            "\tcolumn ea_guid\r\n\t\tisHidden\r\n"))
    assert any("t_object" in p and "property 'isHidden'" in p
               for p in compare(before, physical))


def test_allowance_c_an_added_measure(before_files, before):
    extra = ("\t/// Rows.\r\n\tmeasure 'Count' = COUNTROWS('Business Application')\r\n"
             "\t\tformatString: 0\r\n\r\n")
    after = _mutated(before_files, _swap(BA, "\tcolumn ", extra + "\tcolumn ", 1))
    assert compare(before, after) == []


def test_an_added_column_table_or_relationship_is_reported(before_files, before):
    col = _mutated(before_files, _swap(
        BA, "\tcolumn ", "\tcolumn extra\r\n\t\tdataType: string\r\n\r\n\tcolumn ", 1))
    assert any("column 'extra'" in p and "added" in p for p in compare(before, col))
    new_table = dict(before_files)
    new_table["tables/Extra.tmdl"] = "table Extra\r\n\tlineageTag: x\r\n"
    assert any("table 'Extra'" in p for p in compare(before, read_model(new_table)))
    new_rel = dict(before_files)
    new_rel["relationships.tmdl"] += ("relationship extra\r\n\tfromColumn: A.b\r\n"
                                      "\ttoColumn: C.d\r\n\r\n")
    assert any("relationship 'extra'" in p for p in compare(before, read_model(new_rel)))


def test_allowance_d_a_rename_needs_the_map(before_files, before):
    old = "gen_con_ai_gateway_uses_ai_service_source_guid_to_ai_gateway"
    after = _mutated(before_files, _swap("relationships.tmdl", old, old + "_x"))
    unmapped = compare(before, after)
    assert any(old in p and "missing" in p for p in unmapped), unmapped
    assert any(old + "_x" in p and "added" in p for p in unmapped), unmapped
    assert compare(before, after, renames={old: old + "_x"}) == []

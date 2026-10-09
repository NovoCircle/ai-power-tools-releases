#!/usr/bin/env python3
"""The Power BI model, generated from the business-layer definition.

PURE except `write_project` and the CLI. `model_from_definition` and
`project_files_from_definition` do no I/O: they turn the definition JSON that the
server's `build_business_layer` writes (`APT-2026-0301`) into a `SemanticModel`
and a complete `.pbip` project, keyed by relative path.

    definition.json  ->  SemanticModel  ->  TMDL + diagramLayout.json  ->  .pbip

One shape on every path. The only things that vary are the partition source and
the storage mode. A definition whose `source.kind` is "parquet" (path C,
`APT-2026-0212`) gets a Parquet partition per table, always in Import mode;
anything else gets a SQL partition.

THE MODEL
---------
Business tables (every entity, connector, tag-row table and the Table Directory,
in `source.schema`) plus EA's nine physical tables (in `source.physical_schema`),
hidden. The business layer FILTERS the physical one: `entity.ea_guid` is the one
side and `t_object.ea_guid` the many side. The other direction was measured and
Power BI refuses the project ("ambiguous paths").

`Resolver` decides every relationship's active state by an ambiguity check over
the filter graph, so the engine can be proven to agree on every one. A
relationship is inactive when it would be a second relationship between the same
two tables or would give a table a second filter path from the same source.

MEASURES
--------
Exactly one per inactive relationship whose many side is a `Con_` table, hosted
on that table with `USERELATIONSHIP`. A combination whose source and target are
the same entity type has one inactive relationship (the target side); the measure
is what makes it reachable. Nothing else is a measure, and nothing sits on a
hidden table (a visible measure keeps a hidden table visible, measured).
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

import pbip
import tmdl
from semantic_model import (Measure, Relationship, SemanticColumn, SemanticModel,
                            SemanticTable, _rel_name)

#: The definition's declared type -> TMDL data type.
TYPES = {
    "TEXT": "string",
    "INTEGER": "int64",
    "REAL": "double",
    "BOOLEAN": "boolean",
    "DATETIME": "dateTime",
}

#: (many table, column, one table, column), in priority order.
PHYSICAL_RELS = [
    ("t_object", "Package_ID", "t_package", "Package_ID"),
    ("t_objectproperties", "Object_ID", "t_object", "Object_ID"),
    ("t_attribute", "Object_ID", "t_object", "Object_ID"),
    ("t_operation", "Object_ID", "t_object", "Object_ID"),
    ("t_diagramobjects", "Object_ID", "t_object", "Object_ID"),
    ("t_diagramobjects", "Diagram_ID", "t_diagram", "Diagram_ID"),
    ("t_diagram", "Package_ID", "t_package", "Package_ID"),
    ("t_connector", "Start_Object_ID", "t_object", "Object_ID"),
    ("t_connector", "End_Object_ID", "t_object", "Object_ID"),
    ("t_connectortag", "ElementID", "t_connector", "Connector_ID"),
]

CONNECTOR_PREFIX = "Con_"

#: Layout, in Power BI model-view pixels. Copied from a project Power BI saved.
NODE_W, NODE_H, GAP_X, GAP_Y, PER_ROW = 234, 300, 30, 40, 9
PHYSICAL_GAP = 400


@dataclass
class SchemaSqlSource(tmdl.SqlSource):
    """A SQL source whose schema comes PER TABLE: `source_name` is `schema.item`.

    The shipped `SqlSource` takes one schema per model, and a two-layer model
    needs two.
    """

    def expression(self, table):
        schema, _, item = table.source_name.partition(".")
        return ["let",
                f'    Source = Sql.Database("{tmdl.m_literal(self.server)}", '
                f'"{tmdl.m_literal(self.database)}"),',
                f'    Data = Source{{[Schema="{tmdl.m_literal(schema)}",'
                f'Item="{tmdl.m_literal(item)}"]}}[Data]',
                "in", "    Data"]


class Resolver:
    """Declares each relationship active unless it would add a second filter path
    or a second relationship between the same two tables. Filter flows from the
    one side to the many side."""

    def __init__(self) -> None:
        self.reach: dict[str, set[str]] = defaultdict(set)
        self.pairs: set[frozenset] = set()
        self.out: list[Relationship] = []
        self._names: set[str] = set()

    def add(self, many: str, mcol: str, one: str, ocol: str, why: str) -> None:
        u, v = one, many
        pair = frozenset((u, v))
        sources = {a for a in list(self.reach) if u in self.reach[a]} | {u}
        sinks = self.reach[v] | {v}
        if pair in self.pairs:
            active, reason = False, "second relationship between these two tables"
        elif any(b in self.reach[a] or a == b for a in sources for b in sinks):
            active, reason = False, "would make a second filter path (ambiguity)"
        else:
            active, reason = True, why
            self.pairs.add(pair)
            for a in sources:
                self.reach[a] |= sinks
        name = base = _rel_name(many, mcol, one)
        n = 2
        while name in self._names:
            name, n = f"{base}_{n}", n + 1
        self._names.add(name)
        self.out.append(Relationship(name=name, from_table=many, from_column=mcol,
                                     to_table=one, to_column=ocol,
                                     is_active=active, why=reason))


# ------------------------------------------------------------------- tables


def _columns(spec: dict) -> list[SemanticColumn]:
    cols = spec.get("all_columns", spec.get("columns"))
    out = []
    for c in cols:
        if c["type"] not in TYPES:
            raise ValueError(f"column {c['name']!r} of {spec['name']!r} has the "
                             f"unknown type {c['type']!r}; expected one of {sorted(TYPES)}")
        out.append(SemanticColumn(name=c["name"], data_type=TYPES[c["type"]],
                                  description=c.get("description") or ""))
    return out


def _business_specs(defn: dict) -> list[dict]:
    """Entities, entity tag rows, connectors, connector tag rows, Table Directory."""
    tag_rows = defn.get("tag_row_tables", [])
    connectors = {c["name"] for c in defn["connectors"]}
    return (list(defn["entities"])
            + [t for t in tag_rows if t["of"] not in connectors]
            + list(defn["connectors"])
            + [t for t in tag_rows if t["of"] in connectors]
            + [defn["directory"]])


def _descriptions(defn: dict) -> dict[str, str]:
    return {e["table_name"]: e["description"]
            for e in defn["directory"].get("entries", []) if e.get("description")}


def _relationships(defn: dict) -> list[Relationship]:
    res = Resolver()
    tag_rows = defn.get("tag_row_tables", [])
    connectors = {c["name"] for c in defn["connectors"]}
    for t in tag_rows:
        if t["of"] not in connectors:
            res.add(t["name"], "ea_guid", t["of"], "ea_guid", "tag rows to their entity")
    for c in defn["connectors"]:
        res.add(c["name"], "source_guid", c["source"], "ea_guid", "connector source")
        res.add(c["name"], "target_guid", c["target"], "ea_guid", "connector target")
        for t in tag_rows:
            if t["of"] == c["name"]:
                res.add(t["name"], "connector_guid", c["name"], "connector_guid",
                        "tag rows to their connector")
    for many, mcol, one, ocol in PHYSICAL_RELS:
        res.add(many, mcol, one, ocol, "physical")
    for e in defn["entities"]:
        res.add("t_object", "ea_guid", e["name"], "ea_guid",
                "business layer filters the physical layer")
    return res.out


# ----------------------------------------------------------------- measures


def _dax(name: str) -> str:
    return "'" + name.replace("'", "''") + "'"


def _stereotype(table: SemanticTable, key: str) -> str:
    leaf = key.rpartition("::")[2]
    return leaf or table.name[len(CONNECTOR_PREFIX):]


def _measures(model_tables: dict[str, SemanticTable], rels: list[Relationship],
              keys: dict[str, str]) -> None:
    """One measure per inactive relationship whose many side is a `Con_` table."""
    wanted = []
    for r in rels:
        con = model_tables.get(r.from_table)
        if r.is_active or con is None or r.from_table not in keys:
            continue
        side = {"source_guid": "source", "target_guid": "target"}.get(r.from_column)
        if side is None:
            continue
        wanted.append((r, con, side))
    names = [f"{_stereotype(con, keys[con.name])} by {side} {r.to_table}" for r, con, side in wanted]
    for i, (r, con, side) in enumerate(wanted):
        name = names[i]
        if names.count(name) > 1:
            name = f"{con.name[len(CONNECTOR_PREFIX):]} by {side}"
        con.measures.append(Measure(
            name=name,
            expression=(f"CALCULATE(COUNTROWS({_dax(con.name)}), "
                        f"USERELATIONSHIP({_dax(con.name)}[{r.from_column}], "
                        f"{_dax(r.to_table)}[{r.to_column}]))"),
            description=f"Rows of {con.name} whose {side} is the selected {r.to_table}. "
                        f"Uses the inactive relationship."))


# -------------------------------------------------------------------- model


def is_parquet(defn: dict) -> bool:
    return defn["source"].get("kind") == "parquet"


def model_from_definition(defn: dict) -> SemanticModel:
    src = defn["source"]
    parquet = is_parquet(defn)
    descriptions = _descriptions(defn)
    tables: list[SemanticTable] = []
    for spec in _business_specs(defn):
        tables.append(SemanticTable(
            name=spec["name"],
            source_name=spec["name"] if parquet else f"{src['schema']}.{spec['name']}",
            description=descriptions.get(spec["name"], ""), columns=_columns(spec)))
    for spec in defn["physical"]:
        tables.append(SemanticTable(
            name=spec["name"],
            source_name=spec["name"] if parquet else f"{src['physical_schema']}.{spec['name']}",
            is_hidden=True, columns=_columns(spec)))
    names = [t.name for t in tables]
    dup = sorted({n for n in names if names.count(n) > 1})
    if dup:
        raise ValueError(f"table names are not unique: {dup}")

    rels = _relationships(defn)
    keys = {c["name"]: c["key"] for c in defn["connectors"]}
    _measures({t.name: t for t in tables}, rels, keys)
    return SemanticModel(tables=tables, relationships=rels)


# ------------------------------------------------------------------- layout


def _bands(defn: dict) -> list[tuple[str, list[str]]]:
    entities = [e["name"] for e in defn["entities"]]
    connectors = [c["name"] for c in defn["connectors"]]
    rows = [t["name"] for t in defn.get("tag_row_tables", [])] + [defn["directory"]["name"]]
    physical = [p["name"] for p in defn["physical"]]
    return [("entities", sorted(entities)), ("connectors", sorted(connectors)),
            ("rows and directory", sorted(rows)), ("physical", sorted(physical))]


def layout_from_definition(defn: dict, model: SemanticModel) -> dict:
    """The default model view: business tables in bands on top, EA's physical
    tables in a separate band below a wide empty gap."""
    ncols = {t.name: len(t.columns) for t in model.tables}
    nodes, y, z = [], 50, 0
    for label, names in _bands(defn):
        if label == "physical":
            y += PHYSICAL_GAP
        for i, n in enumerate(names):
            r, c = divmod(i, PER_ROW)
            nodes.append({
                "location": {"x": 50 + c * (NODE_W + GAP_X), "y": y + r * (NODE_H + GAP_Y)},
                "nodeIndex": n,
                "nodeLineageTag": tmdl.lineage_tag("table", n),
                "size": {"height": min(NODE_H, 60 + 22 * ncols[n]), "width": NODE_W},
                "zIndex": z})
            z += 1
        y += ((len(names) - 1) // PER_ROW + 1) * (NODE_H + GAP_Y) + 80
    return {"version": "1.1.0",
            "diagrams": [{"ordinal": 0, "scrollPosition": {"x": 0, "y": 0}, "nodes": nodes,
                          "name": "All tables", "zoomValue": 40, "pinKeyFieldsToTop": False,
                          "showExtraHeaderInfo": False, "hideKeyFieldsWhenCollapsed": False,
                          "tablesLocked": False}],
            "selectedDiagram": "All tables", "defaultDiagram": "All tables"}


# ------------------------------------------------------------------ project

MODES = ("import", "directQuery")
_UNSAFE_NAME_CHARS = set('/\\:<>"|?*') | {chr(c) for c in range(32)}


def check_project_name(name: str) -> str:
    """`name` becomes a folder and file name under the output folder, so it
    must be one plain Windows file name: no separators, no reserved
    characters, not `.` or `..`, no trailing dot or space."""
    if (not name or name in (".", "..") or name[-1] in ". "
            or any(ch in _UNSAFE_NAME_CHARS for ch in name)):
        raise ValueError(f"project name {name!r} must be a plain file name "
                         f'(no / \\ : < > " | ? * or control characters, no trailing dot or space)')
    return name


def project_files_from_definition(defn: dict, name: str, *, mode: str = "import") -> dict[str, str]:
    """Every text file of the `.pbip` project, keyed by relative path."""
    check_project_name(name)
    if mode not in MODES:
        raise ValueError(f"mode must be one of {MODES}, not {mode!r}")
    model = model_from_definition(defn)
    if is_parquet(defn):
        if mode != "import":
            raise ValueError(f"a Parquet source is read in import mode, not {mode!r}")
        source = tmdl.ParquetSource(directory=defn["source"]["folder"], mode="import")
    else:
        source = SchemaSqlSource(server=defn["source"]["server"],
                                 database=defn["source"]["database"], mode=mode)
    files = pbip.project_files(model, source, name=name)
    files[f"{name}.SemanticModel/diagramLayout.json"] = (
        json.dumps(layout_from_definition(defn, model), indent=2).replace("\n", tmdl.NEWLINE)
        + tmdl.NEWLINE)
    return files


def write_project(defn: dict, out_dir, name: str, *, mode: str = "import") -> Path:
    """Write the project under `out_dir`. The semantic model's `definition/`
    folder is replaced, so a table that left the definition leaves the project.
    An existing `<name>.Report` folder is left untouched, so re-applying never
    resets visuals a customer has built; a fresh project gets the skeleton report."""
    files = project_files_from_definition(defn, name, mode=mode)
    root = Path(out_dir)
    if (root / f"{name}.Report").exists():
        files = {k: v for k, v in files.items() if not k.startswith(f"{name}.Report/")}
    # Table names from the definition become file names too: nothing is
    # deleted or written until every target is known to stay under out_dir.
    base = root.resolve()
    stale = root / f"{name}.SemanticModel" / "definition"
    for target in [stale, *(root / rel for rel in files)]:
        if not target.resolve().is_relative_to(base) or target.resolve() == base:
            raise ValueError(f"{target} is outside the output folder {root}")
    if stale.exists():
        shutil.rmtree(stale)
    for rel, text in files.items():
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(text.encode("utf-8"))
    return root


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Generate a Power BI project from a business-layer definition.")
    ap.add_argument("definition")
    ap.add_argument("out_dir")
    ap.add_argument("--name", required=True)
    ap.add_argument("--mode", default="import", choices=MODES)
    a = ap.parse_args(argv)
    defn = json.loads(Path(a.definition).read_text(encoding="utf-8"))
    write_project(defn, a.out_dir, a.name, mode=a.mode)
    model = model_from_definition(defn)
    print(f"{a.name}: {len(model.tables)} tables ({sum(t.is_hidden for t in model.tables)} hidden), "
          f"{len(model.relationships)} relationships ({len(model.inactive)} inactive), "
          f"{sum(len(t.measures) for t in model.tables)} measures -> {a.out_dir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

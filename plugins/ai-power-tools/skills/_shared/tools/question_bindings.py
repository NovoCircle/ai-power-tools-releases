#!/usr/bin/env python3
"""Architecture questions, written against roles, bound to one customer's tables.

PURE except the CLI. Nothing here touches EA, a database, Power BI or the network.

A generated Power BI model is shaped by each customer's technology: a table per
stereotype, a column per tag, a `Con_` table per connector combination. So a ready-made
set of questions cannot name tables. It names ROLES:

    entity role     "application", "vendor_system", "depended_on"
    tag role        "lifecycle", "criticality", "regulatory_scope", ...   (a tag of an entity role)
    connector role  "depends_on"                                          (application -> depended_on)

and a BINDING maps each role to the customer's table or column, as the business-layer
definition names them (the file `build_business_layer` writes and `powerbi_model.py`
reads). Three steps:

    propose_binding(definition)        candidates for each role; never chooses
    validate_binding(binding, defn)    every table and column exists; the connector joins the
                                       bound entities; no unknown key
    build_plan(binding, defn)          the SQL and the DAX that compute each answer

and a check, `check_plan`, that runs the statements through runners the caller supplies and
compares: SQL against DAX, and either against an expected answer the person gives.

No new measures and no report pages: the statements are queries, run once.

Business terms ("retired", "critical") are the customer's definition. They are supplied in
the binding and never defaulted: a question that needs one is reported as needing it.
Parameters (a criticality value, a scope, a vendor, a subject) are supplied the same way.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Callable, Iterable, Optional

# --------------------------------------------------------------------------
# Roles
# --------------------------------------------------------------------------

#: Entity roles. `synonyms` are matched against a table's name and alias, only to PROPOSE.
ENTITY_ROLES: dict[str, dict[str, Any]] = {
    "application": {
        "what": "the application element: the thing architecture questions count and list",
        "synonyms": ["application"],
    },
    "vendor_system": {
        "what": "the vendor or supplied system element",
        "synonyms": ["vendor", "supplier"],
    },
    "depended_on": {
        "what": "what an application depends on or uses (a service, for example)",
        "synonyms": ["service"],
    },
}

#: Tag roles: the entity role that carries the tag, and name fragments to PROPOSE from.
TAG_ROLES: dict[str, dict[str, Any]] = {
    "lifecycle": {"entity": "application", "synonyms": ["lifecycle", "life cycle", "stage", "status"]},
    "criticality": {"entity": "application", "synonyms": ["critical", "tier", "priority"]},
    "regulatory_scope": {"entity": "application", "synonyms": ["regulat", "scope", "complian"]},
    "data_classification": {"entity": "application", "synonyms": ["classification", "sensitiv"]},
    "business_owner": {"entity": "application", "synonyms": ["owner"]},
    "vendor": {"entity": "vendor_system", "synonyms": ["vendor", "supplier", "provider"]},
}

#: Connector roles: from and to entity roles.
CONNECTOR_ROLES: dict[str, dict[str, str]] = {
    "depends_on": {"from": "application", "to": "depended_on"},
}

#: Business terms: the tag role whose values the customer lists.
TERMS: dict[str, dict[str, str]] = {
    "retired": {"tag": "lifecycle", "what": "the lifecycle values that mean an application is being retired"},
    "critical": {"tag": "criticality", "what": "the criticality values that count as critical"},
}

#: Columns every business table carries that are never a tag.
_KEY_COLUMNS = {"ea_guid", "name", "metaclass", "package_path", "source_guid", "target_guid",
                "connector_guid", "connector_id", "direction", "base_type", "property_id"}

BINDING_KEYS = ("entities", "tags", "connectors", "terms", "params")

# --------------------------------------------------------------------------
# The catalog. `measured` marks the questions asked of Microsoft 365 Copilot in the
# Westbrook measurements; the rest are questions architecture teams ask that were not
# measured there. The text uses `{name}` slots for parameters.
# --------------------------------------------------------------------------

CATALOG: tuple[dict[str, Any], ...] = (
    {"id": "Q1", "measured": True, "kind": "count_entity", "entity": "application",
     "text": "How many applications do we have?"},
    {"id": "Q2", "measured": True, "kind": "count_tag_equals", "entity": "application",
     "tag": "criticality", "param": "criticality_value",
     "text": "How many applications are {criticality_value}?"},
    {"id": "Q3", "measured": True, "kind": "count_by_tag", "entity": "application", "tag": "criticality",
     "text": "Break down our applications by criticality."},
    {"id": "Q4", "measured": True, "kind": "count_tag_contains", "entity": "application",
     "tag": "regulatory_scope", "param": "scope_value",
     "text": "How many applications are in {scope_value} scope? (the tag holds several values)"},
    {"id": "Q5", "measured": True, "kind": "list_tag_equals", "entity": "vendor_system",
     "tag": "vendor", "param": "vendor_value",
     "text": "Which vendor systems come from {vendor_value}?"},
    {"id": "Q6", "measured": True, "kind": "traverse_forward", "connector": "depends_on",
     "param": "subject_application",
     "text": "Which things does {subject_application} depend on?"},
    {"id": "Q7", "measured": True, "kind": "traverse_reverse", "connector": "depends_on",
     "param": "subject_depended_on",
     "text": "Which applications depend on {subject_depended_on}?"},
    {"id": "Q8", "measured": True, "kind": "list_tag_in_term", "entity": "application", "term": "retired",
     "text": "Which applications are being retired?"},
    {"id": "Q9", "measured": True, "kind": "count_tag_in_term", "entity": "application", "term": "critical",
     "text": "How many critical applications do we have?"},
    {"id": "Q10", "measured": True, "kind": "list_tag_equals", "entity": "application",
     "tag": "data_classification", "param": "classification_value",
     "text": "Which applications hold {classification_value} data?"},
    {"id": "Q11", "measured": True, "kind": "count_entity", "entity": "vendor_system",
     "text": "How many vendor systems are in the model?"},
    {"id": "Q12", "measured": False, "kind": "count_by_tag", "entity": "application", "tag": "lifecycle",
     "text": "Break down our applications by lifecycle."},
    {"id": "Q13", "measured": False, "kind": "list_tag_empty", "entity": "application", "tag": "business_owner",
     "text": "Which applications have no business owner recorded?"},
    {"id": "Q14", "measured": False, "kind": "count_tag_empty", "entity": "application", "tag": "lifecycle",
     "text": "How many applications have no lifecycle recorded?"},
    {"id": "Q15", "measured": False, "kind": "count_forward", "connector": "depends_on",
     "param": "subject_application",
     "text": "How many things does {subject_application} depend on?"},
)

CATALOG_BY_ID = {q["id"]: q for q in CATALOG}

# --------------------------------------------------------------------------
# Quoting
# --------------------------------------------------------------------------


def sql_id(name: str) -> str:
    return "[" + str(name).replace("]", "]]") + "]"


def sql_str(value: str) -> str:
    return "'" + str(value).replace("'", "''") + "'"


def _like_pattern(value: str) -> str:
    out = str(value).replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_").replace("[", "\\[")
    return sql_str("%" + out + "%") + " ESCAPE '\\'"


def dax_table(name: str) -> str:
    return "'" + str(name).replace("'", "''") + "'"


def dax_col(table: str, column: str) -> str:
    return dax_table(table) + "[" + str(column).replace("]", "]]") + "]"


def dax_str(value: str) -> str:
    return '"' + str(value).replace('"', '""') + '"'


# --------------------------------------------------------------------------
# Reading the definition
# --------------------------------------------------------------------------


def _entities(defn: dict) -> dict[str, dict]:
    return {e["name"]: e for e in defn.get("entities", [])}


def _connectors(defn: dict) -> dict[str, dict]:
    return {c["name"]: c for c in defn.get("connectors", [])}


def _columns(table: dict) -> list[str]:
    return [c["name"] for c in table.get("all_columns", [])]


def _schema(defn: dict) -> Optional[str]:
    return (defn.get("source") or {}).get("schema") or None


def _sql_table(defn: dict, name: str) -> str:
    schema = _schema(defn)
    return (sql_id(schema) + "." if schema else "") + sql_id(name)


# --------------------------------------------------------------------------
# Step 1: propose. Candidates only; the person chooses.
# --------------------------------------------------------------------------


def _matches(text: str, synonyms: Iterable[str]) -> bool:
    low = text.lower()
    return any(s in low for s in synonyms)


def propose_binding(defn: dict) -> dict:
    """Candidates for every role. Never picks one: two tables can both look like the
    application element (a measured technology table and a not-in-technology one), and a
    wrong pick produces a confident wrong answer."""
    ents = _entities(defn)
    entity_candidates = {
        role: [n for n, e in ents.items()
               if _matches(n, spec["synonyms"]) or _matches(e.get("alias") or "", spec["synonyms"])]
        for role, spec in ENTITY_ROLES.items()}
    tags: dict[str, dict[str, list[str]]] = {}
    for role, spec in TAG_ROLES.items():
        per_entity: dict[str, list[str]] = {}
        for ent in entity_candidates[spec["entity"]]:
            cols = [c for c in _columns(ents[ent]) if c not in _KEY_COLUMNS
                    and _matches(c, spec["synonyms"])]
            if cols:
                per_entity[ent] = cols
        tags[role] = per_entity
    connectors: dict[str, list[str]] = {}
    for role, spec in CONNECTOR_ROLES.items():
        src, dst = set(entity_candidates[spec["from"]]), set(entity_candidates[spec["to"]])
        connectors[role] = [n for n, c in _connectors(defn).items()
                            if c.get("source") in src and c.get("target") in dst]
    return {"entities": entity_candidates, "tags": tags, "connectors": connectors}


# --------------------------------------------------------------------------
# Step 2: validate
# --------------------------------------------------------------------------


def validate_binding(binding: dict, defn: dict) -> list[str]:
    """Problems with a binding, as sentences. Empty means every bound role resolves.

    A role left out is not an error: a question that needs it is reported as needing it."""
    problems: list[str] = []
    for key in binding:
        if key not in BINDING_KEYS:
            problems.append(f"unknown key '{key}' in the binding (expected {', '.join(BINDING_KEYS)})")
    ents, cons = _entities(defn), _connectors(defn)
    bound_entities = binding.get("entities") or {}
    for role, table in bound_entities.items():
        if role not in ENTITY_ROLES:
            problems.append(f"unknown entity role '{role}'")
        elif table not in ents:
            problems.append(f"entity role '{role}' is bound to '{table}', which is not an entity table in the definition")
    for role, column in (binding.get("tags") or {}).items():
        spec = TAG_ROLES.get(role)
        if spec is None:
            problems.append(f"unknown tag role '{role}'")
            continue
        table = bound_entities.get(spec["entity"])
        if table is None:
            problems.append(f"tag role '{role}' is bound to '{column}' but entity role '{spec['entity']}' is not bound")
        elif table in ents and column not in _columns(ents[table]):
            problems.append(f"tag role '{role}' is bound to '{column}', which is not a column of '{table}'")
        elif column in _KEY_COLUMNS:
            problems.append(f"tag role '{role}' is bound to '{column}', which is a key column and not a tag")
    for role, table in (binding.get("connectors") or {}).items():
        spec = CONNECTOR_ROLES.get(role)
        if spec is None:
            problems.append(f"unknown connector role '{role}'")
            continue
        con = cons.get(table)
        if con is None:
            problems.append(f"connector role '{role}' is bound to '{table}', which is not a connector table in the definition")
            continue
        for end, key in (("from", "source"), ("to", "target")):
            want = bound_entities.get(spec[end])
            if want is None:
                problems.append(f"connector role '{role}' needs entity role '{spec[end]}' bound")
            elif con.get(key) != want:
                problems.append(f"connector table '{table}' joins '{con.get('source')}' to '{con.get('target')}', "
                                f"not '{bound_entities.get(spec['from'])}' to '{bound_entities.get(spec['to'])}'")
                break
        cols = _columns(con)
        for need in ("source_guid", "target_guid"):
            if need not in cols:
                problems.append(f"connector table '{table}' has no '{need}' column")
    for term, values in (binding.get("terms") or {}).items():
        if term not in TERMS:
            problems.append(f"unknown business term '{term}'")
        elif not isinstance(values, list) or not values or not all(isinstance(v, str) for v in values):
            problems.append(f"business term '{term}' needs a non-empty list of values")
    for name, value in (binding.get("params") or {}).items():
        if not isinstance(value, str) or not value:
            problems.append(f"parameter '{name}' needs a non-empty text value")
    return problems


# --------------------------------------------------------------------------
# Step 3: the statements
# --------------------------------------------------------------------------


def _tag_column(binding: dict, role: str) -> Optional[str]:
    return (binding.get("tags") or {}).get(role)


def _needs(question: dict, binding: dict) -> list[str]:
    """What the binding lacks for this question: roles, terms, parameters."""
    missing: list[str] = []
    ents = binding.get("entities") or {}
    roles: list[str] = []
    if "entity" in question:
        roles.append(question["entity"])
    if "connector" in question:
        spec = CONNECTOR_ROLES[question["connector"]]
        roles += [spec["from"], spec["to"]]
        if question["connector"] not in (binding.get("connectors") or {}):
            missing.append(f"connector role {question['connector']}")
    missing += [f"entity role {r}" for r in dict.fromkeys(roles) if r not in ents]
    if "tag" in question and _tag_column(binding, question["tag"]) is None:
        missing.append(f"tag role {question['tag']}")
    if "term" in question:
        term = question["term"]
        if term not in (binding.get("terms") or {}):
            missing.append(f"business term {term}")
        tag = TERMS[term]["tag"]
        if _tag_column(binding, tag) is None:
            missing.append(f"tag role {tag}")
    if "param" in question and question["param"] not in (binding.get("params") or {}):
        missing.append(f"parameter {question['param']}")
    return list(dict.fromkeys(missing))


def _statements(question: dict, binding: dict, defn: dict) -> dict[str, str]:
    kind = question["kind"]
    ents = binding.get("entities") or {}
    params = binding.get("params") or {}
    if "connector" in question:
        spec = CONNECTOR_ROLES[question["connector"]]
        con = binding["connectors"][question["connector"]]
        src, dst = ents[spec["from"]], ents[spec["to"]]
        subject = params[question["param"]]
        return _traversal(kind, defn, con, src, dst, subject)
    table = ents[question["entity"]]
    tag_role = question.get("tag") or (TERMS[question["term"]]["tag"] if "term" in question else None)
    column = _tag_column(binding, tag_role) if tag_role else None
    t_sql, c_sql = _sql_table(defn, table), (sql_id(column) if column else "")
    t_dax, c_dax = dax_table(table), (dax_col(table, column) if column else "")
    if kind == "count_entity":
        return {"sql": f"SELECT COUNT(*) AS answer FROM {t_sql}",
                "dax": f'EVALUATE ROW("answer", COUNTROWS({t_dax}) + 0)'}
    if kind == "count_by_tag":
        return {"sql": f"SELECT {c_sql} AS tag_value, COUNT(*) AS n FROM {t_sql} GROUP BY {c_sql} ORDER BY {c_sql}",
                "dax": f'EVALUATE SUMMARIZECOLUMNS({c_dax}, "n", COUNTROWS({t_dax})) ORDER BY {c_dax}'}
    if kind in ("count_tag_equals", "list_tag_equals"):
        value = params[question["param"]]
        w_sql, w_dax = f"{c_sql} = {sql_str(value)}", f"{c_dax} = {dax_str(value)}"
    elif kind == "count_tag_contains":
        value = params[question["param"]]
        w_sql, w_dax = f"{c_sql} LIKE {_like_pattern(value)}", f"CONTAINSSTRING({c_dax}, {dax_str(value)})"
    elif kind in ("list_tag_in_term", "count_tag_in_term"):
        values = binding["terms"][question["term"]]
        w_sql = f"{c_sql} IN (" + ", ".join(sql_str(v) for v in values) + ")"
        w_dax = f"{c_dax} IN {{" + ", ".join(dax_str(v) for v in values) + "}"
    elif kind in ("list_tag_empty", "count_tag_empty"):
        w_sql = f"({c_sql} IS NULL OR {c_sql} = '')"
        w_dax = f'(ISBLANK({c_dax}) || {c_dax} = "")'
    else:
        raise ValueError(f"unknown question kind '{kind}'")
    name_sql, name_dax = sql_id("name"), dax_col(table, "name")
    if kind.startswith("count_"):
        return {"sql": f"SELECT COUNT(*) AS answer FROM {t_sql} WHERE {w_sql}",
                "dax": f'EVALUATE ROW("answer", COUNTROWS(FILTER({t_dax}, {w_dax})) + 0)'}
    return {"sql": f"SELECT DISTINCT {name_sql} AS name FROM {t_sql} WHERE {w_sql} ORDER BY {name_sql}",
            "dax": (f'EVALUATE DISTINCT(SELECTCOLUMNS(FILTER({t_dax}, {w_dax}), "name", {name_dax})) '
                    f"ORDER BY [name]")}


def _traversal(kind: str, defn: dict, con: str, src: str, dst: str, subject: str) -> dict[str, str]:
    c, s, d = _sql_table(defn, con), _sql_table(defn, src), _sql_table(defn, dst)
    join = (f"FROM {c} AS c JOIN {s} AS a ON a.[ea_guid] = c.[source_guid] "
            f"JOIN {d} AS t ON t.[ea_guid] = c.[target_guid]")
    forward = kind in ("traverse_forward", "count_forward")
    anchor, other = ("a", "t") if forward else ("t", "a")
    where = f"WHERE {anchor}.[name] = {sql_str(subject)}"
    if kind == "count_forward":
        sql = f"SELECT COUNT(DISTINCT t.[ea_guid]) AS answer {join} {where}"
    else:
        sql = f"SELECT DISTINCT {other}.[name] AS name {join} {where} ORDER BY {other}.[name]"
    # DAX goes through the guid columns, not through the model's relationships, so an inactive
    # relationship (the same entity type at both ends) cannot change the answer.
    c_t, s_t, d_t = dax_table(con), dax_table(src), dax_table(dst)
    anchor_t, anchor_key, anchor_fk = ((s_t, "ea_guid", "source_guid") if forward
                                       else (d_t, "ea_guid", "target_guid"))
    other_t, other_fk = (d_t, "target_guid") if forward else (s_t, "source_guid")
    head = (f"EVALUATE VAR anchor = SELECTCOLUMNS(FILTER({anchor_t}, {anchor_t}[name] = {dax_str(subject)}), "
            f'"g", {anchor_t}[{anchor_key}]) '
            f'VAR linked = SELECTCOLUMNS(FILTER({c_t}, {c_t}[{anchor_fk}] IN anchor), "g", {c_t}[{other_fk}]) '
            f"VAR hits = FILTER({other_t}, {other_t}[ea_guid] IN linked) ")
    if kind == "count_forward":
        dax = head + 'RETURN ROW("answer", COUNTROWS(hits) + 0)'
    else:
        dax = head + f'RETURN DISTINCT(SELECTCOLUMNS(hits, "name", {other_t}[name]))'
    return {"sql": sql, "dax": dax}


def build_plan(binding: dict, defn: dict, questions: Optional[Iterable[str]] = None) -> list[dict]:
    """One entry per question: its text with the parameters filled in, a status, and the SQL
    and DAX that compute the answer. Raises ValueError when the binding does not validate:
    a statement built on a name that is not there fails in a database, or answers from the wrong table."""
    problems = validate_binding(binding, defn)
    if problems:
        raise ValueError("the binding does not match the definition: " + "; ".join(problems))
    plan = []
    wanted = list(questions) if questions is not None else [q["id"] for q in CATALOG]
    for qid in wanted:
        if qid not in CATALOG_BY_ID:
            raise ValueError(f"no question '{qid}' in the catalog")
        q = CATALOG_BY_ID[qid]
        params = binding.get("params") or {}
        text = q["text"].format(**{k: params.get(k, "<" + k + ">") for k in
                                   (q.get("param"),) if k})
        missing = _needs(q, binding)
        entry = {"id": qid, "text": text, "kind": q["kind"], "measured": q["measured"]}
        if missing:
            entry.update(status="needs_binding", missing=missing, sql=None, dax=None)
        else:
            entry.update(status="ready", missing=[], **_statements(q, binding, defn))
        plan.append(entry)
    return plan


# --------------------------------------------------------------------------
# The check
# --------------------------------------------------------------------------


def normalize_rows(rows: Any) -> list[tuple[str, ...]]:
    """A runner's answer as a sorted list of text tuples, so a count from SQL and a count from
    DAX compare equal. Accepts a scalar, a list of scalars, of tuples or lists, or of dicts."""
    if rows is None:
        return []
    if not isinstance(rows, (list, tuple)):
        rows = [rows]
    out: list[tuple[str, ...]] = []
    for row in rows:
        if isinstance(row, dict):
            row = list(row.values())
        elif not isinstance(row, (list, tuple)):
            row = [row]
        out.append(tuple(_cell(v) for v in row))
    return sorted(out)


def _cell(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, float) and value.is_integer():
        value = int(value)
    return str(value).strip()


def compare_answers(a: Any, b: Any) -> bool:
    return normalize_rows(a) == normalize_rows(b)


def check_plan(plan: list[dict], run_sql: Optional[Callable[[str], Any]] = None,
               run_dax: Optional[Callable[[str], Any]] = None,
               expected: Optional[dict[str, Any]] = None) -> list[dict]:
    """Run each ready question's statements and report. `expected` maps a question id to the
    answer the person believes is right. The result per question is one of:

      agree          SQL and DAX gave the same answer (and it equals `expected` when given)
      differ         SQL and DAX gave different answers: report both, trust neither
      wrong          the answer differs from `expected`
      sql_only / dax_only   only one runner was supplied
      not_run        no runner, or the question needs binding
    """
    results = []
    for item in plan:
        res = {"id": item["id"], "text": item["text"]}
        if item["status"] != "ready":
            res.update(result="not_run", detail="needs " + ", ".join(item["missing"]))
            results.append(res)
            continue
        sql_rows = run_sql(item["sql"]) if run_sql else None
        dax_rows = run_dax(item["dax"]) if run_dax else None
        res.update(sql=normalize_rows(sql_rows) if run_sql else None,
                   dax=normalize_rows(dax_rows) if run_dax else None)
        if run_sql and run_dax:
            res["result"] = "agree" if compare_answers(sql_rows, dax_rows) else "differ"
            answer = sql_rows
        elif run_sql:
            res["result"], answer = "sql_only", sql_rows
        elif run_dax:
            res["result"], answer = "dax_only", dax_rows
        else:
            res["result"], answer = "not_run", None
        if expected and item["id"] in expected and res["result"] not in ("differ", "not_run"):
            if not compare_answers(answer, expected[item["id"]]):
                res["result"] = "wrong"
        results.append(res)
    return results


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------


def _load(path: str) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def main(argv: Optional[list[str]] = None) -> int:
    ap = argparse.ArgumentParser(description="Bind the question catalog to a business-layer definition.")
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("propose", help="candidate tables and columns for each role")
    p.add_argument("definition")
    v = sub.add_parser("validate", help="check a binding against the definition")
    v.add_argument("definition")
    v.add_argument("binding")
    b = sub.add_parser("plan", help="print the SQL and DAX for each question")
    b.add_argument("definition")
    b.add_argument("binding")
    b.add_argument("--dialect", choices=("sql", "dax", "both"), default="both")
    b.add_argument("--questions", default=None, help="comma-separated ids, for example Q1,Q8")
    a = ap.parse_args(argv)
    defn = _load(a.definition)
    if a.cmd == "propose":
        print(json.dumps(propose_binding(defn), indent=2))
        return 0
    binding = _load(a.binding)
    problems = validate_binding(binding, defn)
    if a.cmd == "validate":
        for line in problems:
            print(line)
        print("binding is valid" if not problems else f"{len(problems)} problem(s)")
        return 1 if problems else 0
    if problems:
        for line in problems:
            print(line, file=sys.stderr)
        return 1
    ids = a.questions.split(",") if a.questions else None
    for item in build_plan(binding, defn, ids):
        print(f"{item['id']}: {item['text']}")
        if item["status"] != "ready":
            print("  needs: " + ", ".join(item["missing"]))
            continue
        for dialect in (("sql", "dax") if a.dialect == "both" else (a.dialect,)):
            print(f"  {dialect.upper()}: {item[dialect]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

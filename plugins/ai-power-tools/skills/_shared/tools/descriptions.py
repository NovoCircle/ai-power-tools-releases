#!/usr/bin/env python3
"""Descriptions on every business table, column and measure.

PURE except `load_file`. Three layers; the highest that has text wins:

1. **A descriptions file** the user approved, passed as `powerbi_model.py
   --descriptions <file>`:

       {"tables": {"<table>": {"description": "...",
                               "columns": {"<column>": "..."},
                               "measures": {"<measure>": "..."}}}}

   Every key is optional. A table, column or measure the model does not have is
   refused with a ValueError naming it, and so is an entry longer than
   `MAX_LENGTH` characters (with its length). EA's physical tables are not
   business tables and cannot be named.
2. **The technology's own notes** the definition already carries: the Table
   Directory entry's description for a table, a column's `description` for a tag
   column. A note is never truncated or edited; only a file entry that names the
   same object replaces it.
3. **Templates**, from what the definition holds, below. They name things; they
   define no business terms. That is the file's job.

EA's hidden physical tables get no descriptions from any layer.
"""
from __future__ import annotations

import json
from pathlib import Path

#: The longest file entry accepted. It sits between the 200 characters that
#: Copilot in Power BI documents and the 210 measured working with Microsoft 365
#: Copilot. Technology notes and templates are not held to it.
MAX_LENGTH = 250

ENTITY, CONNECTOR, TAG_ROWS, DIRECTORY = "entity", "connector", "tag rows", "directory"

# ---------------------------------------------------------------- templates

#: Fixed texts per table kind. A column of an entity or connector table that is
#: not listed here is a tag column.
ENTITY_COLUMNS = {
    "ea_guid": "Unique key of the element. Hidden; relates the tables.",
    "name": "The element's name.",
    "metaclass": "The UML type the element is built on.",
    "package_path": "Where the element sits in the repository's package tree, from the root.",
}

CONNECTOR_COLUMNS = {
    "connector_guid": "Unique key of the connection. Hidden.",
    "connector_id": "EA's numeric id of the connection. Hidden.",
    "name": "The connection's name, often empty.",
    "direction": "The connection's direction as recorded in EA.",
    "base_type": "The UML connector type the connection is built on.",
}

TAG_ROW_COLUMNS = {
    "ea_guid": ENTITY_COLUMNS["ea_guid"],
    "connector_guid": CONNECTOR_COLUMNS["connector_guid"],
    "tag": "Name of the tagged value.",
    "value": "The tagged value.",
    "property_id": "EA's id of the tagged-value row. Hidden.",
}

DIRECTORY_COLUMNS = {
    "table_name": "Name of a table in this model.",
    "kind": "What the table holds: elements, connections or tag rows.",
    "stereotype": "The technology stereotype the table holds.",
    "alias": "The stereotype's display name.",
    "metaclass": "The UML type the stereotype is built on.",
    "source_table": "For a connection table: the table at the start.",
    "target_table": "For a connection table: the table at the end.",
    "in_mdg": "yes if the technology defines it, no if it was found in the repository.",
    "description": "What the table holds, from the technology's notes.",
}

DIRECTORY_TABLE = ("One row per table in this model: what it holds and which part of the "
                   "technology it comes from.")


def _alias(entity: dict) -> str:
    return entity.get("alias") or entity["name"]


def _namespace(defn: dict) -> str:
    tech = defn.get("technology") or {}
    return tech.get("namespace") or tech.get("id") or "modeling"


def entity_table(entity: dict, namespace: str) -> str:
    if entity.get("in_mdg", True):
        return (f"{_alias(entity)} elements from the EA repository ({namespace} technology), "
                f"one row per element.")
    return (f"{_alias(entity)} elements found in the repository but not defined by the "
            f"{namespace} technology (included as observed), one row per element.")


def connector_table(connector: dict) -> str:
    verb = connector.get("key", "").rpartition("::")[2] or connector["name"]
    return (f"{verb} connections from {connector['source']} to {connector['target']}, "
            f"one row per connection.")


def tag_row_table(spec: dict, owner: dict | None) -> str:
    tags = ", ".join((owner or {}).get("row_tags") or [])
    return (f"One row per value of the multi-valued tagged values ({tags}) "
            f"of each {spec['of']}.")


def count_measure(entity: dict) -> str:
    return f"Number of {_alias(entity)} elements."


def column_text(column: str, kind: str, spec: dict) -> str:
    if kind == ENTITY:
        return ENTITY_COLUMNS.get(column) or f"The {column} tagged value of each {_alias(spec)}."
    if kind == CONNECTOR:
        if column == "source_guid":
            return f"Key of the {spec['source']} at the start of the connection. Hidden."
        if column == "target_guid":
            return f"Key of the {spec['target']} at the end of the connection. Hidden."
        return CONNECTOR_COLUMNS.get(column) or f"The {column} tagged value of each connection."
    if kind == TAG_ROWS:
        return TAG_ROW_COLUMNS.get(column) or f"The {column} of each tagged-value row."
    return DIRECTORY_COLUMNS.get(column) or f"The {column} of each table in this model."


def business_kinds(defn: dict) -> dict[str, tuple[str, dict]]:
    """Every business table's name -> (kind, its spec in the definition)."""
    out = {e["name"]: (ENTITY, e) for e in defn["entities"]}
    out.update({c["name"]: (CONNECTOR, c) for c in defn["connectors"]})
    out.update({t["name"]: (TAG_ROWS, t) for t in defn.get("tag_row_tables", [])})
    out[defn["directory"]["name"]] = (DIRECTORY, defn["directory"])
    return out


def table_text(name: str, defn: dict, kinds: dict[str, tuple[str, dict]]) -> str:
    kind, spec = kinds[name]
    if kind == ENTITY:
        return entity_table(spec, _namespace(defn))
    if kind == CONNECTOR:
        return connector_table(spec)
    if kind == TAG_ROWS:
        owner = kinds.get(spec["of"], (None, None))[1]
        return tag_row_table(spec, owner)
    return DIRECTORY_TABLE


# --------------------------------------------------------------- the file


def check(entries: dict | None) -> dict:
    """The descriptions file's contents, checked for shape and length.

    Returns `{table: {"description": str, "columns": {..}, "measures": {..}}}`
    with every key present. Names are checked against the model in `apply`.
    """
    if entries is None:
        return {}
    if not isinstance(entries, dict) or set(entries) - {"tables"}:
        raise ValueError('a descriptions file is an object whose only key is "tables"')
    tables = entries.get("tables", {})
    if not isinstance(tables, dict):
        raise ValueError('"tables" in a descriptions file must be an object keyed by table name')
    out = {}
    for table, body in tables.items():
        if not isinstance(body, dict) or set(body) - {"description", "columns", "measures"}:
            raise ValueError(f"descriptions for table {table!r} must be an object with only "
                             f'"description", "columns" and "measures"')
        got = {"description": None, "columns": {}, "measures": {}}
        if "description" in body:
            got["description"] = _text(body["description"], f"table {table!r}")
        for part, label in (("columns", "column"), ("measures", "measure")):
            items = body.get(part, {})
            if not isinstance(items, dict):
                raise ValueError(f'"{part}" of table {table!r} must be an object keyed by name')
            got[part] = {n: _text(t, f"{label} {n!r} of table {table!r}") for n, t in items.items()}
        out[table] = got
    return out


def _text(value, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"the description for {label} must be non-empty text")
    if len(value) > MAX_LENGTH:
        raise ValueError(f"the description for {label} is {len(value)} characters; "
                         f"the limit is {MAX_LENGTH}")
    return value


def load_file(path) -> dict:
    """Read and check a descriptions file (UTF-8 JSON)."""
    entries = json.loads(Path(path).read_text(encoding="utf-8"))
    check(entries)
    return entries


# ---------------------------------------------------------------- layering


def apply(tables, defn: dict, entries: dict | None = None) -> None:
    """Fill every business table's, column's and measure's description in place.

    `tables` are the model's `SemanticTable`s, already carrying the technology's
    notes (layer 2) and each measure's own text. Templates fill what is empty;
    the file's entries replace whatever is there. Physical tables are not touched.
    """
    kinds = business_kinds(defn)
    by_name = {t.name: t for t in tables}
    wanted = check(entries)
    for table, body in wanted.items():
        if table not in kinds or table not in by_name:
            raise ValueError(f"the descriptions file names table {table!r}, which is not a "
                             f"business table in this model")
        t = by_name[table]
        for part, have in (("columns", {c.name for c in t.columns}),
                           ("measures", {m.name for m in t.measures})):
            for n in body[part]:
                if n not in have:
                    raise ValueError(f"the descriptions file names {part[:-1]} {n!r} of table "
                                     f"{table!r}, which the model does not have")
    for name, (kind, spec) in kinds.items():
        t = by_name.get(name)
        if t is None:
            continue
        body = wanted.get(name, {"description": None, "columns": {}, "measures": {}})
        t.description = body["description"] or t.description or table_text(name, defn, kinds)
        for c in t.columns:
            c.description = (body["columns"].get(c.name) or c.description
                             or column_text(c.name, kind, spec))
        for m in t.measures:
            m.description = body["measures"].get(m.name) or m.description

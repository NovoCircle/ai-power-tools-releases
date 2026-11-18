#!/usr/bin/env python3
"""Path C: the business-layer tables as Parquet, with the types the definition declares.

    definition.json + tables.json  ->  <table name>.parquet per table  (+ the .pbip)

The server's `build_reporting_database` writes the definition and
the typed rows for a profile whose `target.kind` is "parquet". This module is the
local step: it writes one file per table into `source.folder`, and
`powerbi_model.write_project` writes the `.pbip` that reads them. No SQL Server is
involved.

TYPES ARE DECLARED, NEVER INFERRED
----------------------------------
TEXT -> string, INTEGER -> int64, REAL -> float64, BOOLEAN -> bool, DATETIME ->
timestamp (microseconds, no zone). A refresh must not change a column's type
because of which rows happen to be populated. pyarrow refuses a string in a
numeric column, a number in a boolean column and an integer too big for int64
(named here by table and column), but it TRUNCATES a float written to an int64
column (1.5 becomes 1); the server never sends one. Every field is nullable. An empty table is still written, with its schema.

OPEN MIRRORING LAYOUT (`--layout open-mirroring`, `write_open_mirroring`)
-------------------------------------------------------------------------
The Fabric Open Mirroring landing-zone format, as read from "Open Mirroring
Landing Zone Requirements and Formats" (learn.microsoft.com; ms.date
2025-09-09, content updated 2026-02-03). One folder per table, named exactly as
the table; a `_metadata.json` with `keyColumns`; data files named with 20
digits (`00000000000000000001.parquet`), continuous.

Keys: when the definition declares a `primary_key` for a table (a newer server: tag-row tables
`property_id`, plus `value_no` where a list tag is split into one row per value), that is the key. The
rest is the derivation for a definition that declares none (server 3.6.5): entity tables `ea_guid`;
connector tables `connector_guid`; entity
tag-row tables `property_id` + `value` (a split tag gives several rows per tag
row id); connector tag-row tables carry no row id, so `connector_guid` + `tag`
+ `value` (EA allows the same tag and value twice on one connector; the writer
refuses such a table rather than guess); the Table Directory `table_name`;
EA's own tables their primary key. `keyColumns` cannot change once set. A table whose existing
`_metadata.json` holds one of those 3.6.5 tag-row keys is therefore continued on them (the result says
`kept_existing_keys`) when the table still has those columns and they stay unique, so a landing zone
written before a server update can be continued after it. Any other change of keys is refused.

First run: every row, no `__rowMarker__` (an insert; the measured initial
load). Later runs: the whole table as changes. Deletes (`__rowMarker__` 2, key
columns only) for each key present last run and gone now, then an upsert (4)
for every current row, with `__rowMarker__` as the last column (int32). Every
run is a new file, except that a table with no upserts and no deletes gets none (Fabric never moves
that table's sync time for an empty file); numbering continues from the last file in the folder.

CRASH RECOVERY: a run writes every table's files, then the state file. If it stops between them, the files
are on disk and the state does not record them. The next run reads the files numbered above the state's
last file number (they are the writer's own) and adds the keys they upsert to the keys it deletes when they
are gone, so a row that only ever reached those files is still removed. The other order (state first) would
lose the delete of a row that vanished in the interrupted run and leave a gap in the file numbers, which
Open Mirroring requires to be continuous. A first run that stopped this way (files, no state file) is
refused by the "no record" check below, with the way to start over.

STATE: the keys written last run are kept in `<out>.state.json`, a file beside
the landing-zone folder (same name plus `.state.json`), never inside it, so it
is never uploaded. It also records each table's last file number. Without it a
run refuses on a folder that already holds files (it could not work out the
deletes). To start over, do it on both sides: delete the table folders in the mirrored
database's landing zone in OneLake (Fabric drops those tables), and here the table folders,
the state file and the upload record (`.upload.json`, see onelake_upload.py) together.

pyarrow is REQUIRED for this step. It is imported here, not in the core, so the
rest of the toolchain stays installable without a compiled wheel. Excel and CSV
are never substitutes.

DETERMINISM
-----------
Same input, same pyarrow version: byte-identical files. The writer pins the
compression and the format version, and row order is the order of the input.
The file footer records the pyarrow version that wrote it, so two pyarrow
versions may differ in bytes while agreeing on schema and rows.
"""
from __future__ import annotations

import argparse
import io
import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path

try:  # pragma: no cover - environment-dependent
    import pyarrow as pa
    import pyarrow.parquet as pq
    PYARROW_AVAILABLE = True
except ImportError:  # pragma: no cover - environment-dependent
    pa = pq = None
    PYARROW_AVAILABLE = False

import descriptions
import powerbi_model
from onelake_upload import replace_file

COMPRESSION = "snappy"
FORMAT_VERSION = "2.6"

#: Characters Windows does not allow in a file name, plus control characters.
_BAD_CHARS = re.compile(r'[<>:"/\\|?*\x00-\x1f]')
#: Windows also reserves COM and LPT followed by a superscript 1, 2 or 3 (U+00B9, U+00B2, U+00B3).
_RESERVED = ({"CON", "PRN", "AUX", "NUL"}
             | {f"{p}{i}" for p in ("COM", "LPT") for i in "123456789\u00b9\u00b2\u00b3"})


class ParquetTablesError(Exception):
    pass


def file_name(table: str) -> str:
    """`<table>.parquet`, or an error if Windows cannot hold that file name."""
    bad = sorted(set(_BAD_CHARS.findall(table)))
    if bad:
        raise ParquetTablesError(
            f"table name {table!r} cannot be a Windows file name: contains "
            f"{' '.join(repr(c) for c in bad)}")
    if not table or table != table.rstrip(" .") or table.split(".")[0].upper() in _RESERVED:
        raise ParquetTablesError(
            f"table name {table!r} cannot be a Windows file name: empty, ends in a space "
            f"or a dot, or is a reserved device name")
    return f"{table}.parquet"


def _arrow_type(sql_type: str):
    return {"TEXT": pa.string(), "INTEGER": pa.int64(), "REAL": pa.float64(),
            "BOOLEAN": pa.bool_(), "DATETIME": pa.timestamp("us")}[sql_type]


def _specs(defn: dict) -> list[dict]:
    return powerbi_model._business_specs(defn) + list(defn["physical"])


def _datetime(value, table: str, column: str):
    """An ISO date and time, or None. The server converts every date to ISO
    (`YYYY-MM-DD HH:MM:SS`) before it hands rows over; anything else is refused."""
    if value is None or isinstance(value, datetime):
        return value
    try:
        return datetime.fromisoformat(value)
    except (TypeError, ValueError):
        raise ParquetTablesError(
            f"{table}.{column}: {value!r} is not an ISO date and time (expected "
            f"'YYYY-MM-DD HH:MM:SS')") from None


def _columns(spec: dict) -> list[dict]:
    cols = spec.get("all_columns", spec.get("columns"))
    for c in cols:
        if c["type"] not in powerbi_model.TYPES:
            raise ParquetTablesError(
                f"column {c['name']!r} of {spec['name']!r} has the unknown type "
                f"{c['type']!r}; expected one of {sorted(powerbi_model.TYPES)}")
    return cols


def _table(spec: dict, rows: list[dict]):
    cols = _columns(spec)
    schema = pa.schema([pa.field(c["name"], _arrow_type(c["type"]), nullable=True) for c in cols])
    arrays = []
    for c in cols:
        values = [row.get(c["name"]) for row in rows]
        if c["type"] == "DATETIME":
            values = [_datetime(v, spec["name"], c["name"]) for v in values]
        try:
            arrays.append(pa.array(values, type=schema.field(c["name"]).type))
        except (pa.ArrowInvalid, pa.ArrowTypeError, OverflowError) as e:
            raise ParquetTablesError(
                f"{spec['name']}.{c['name']} is declared {c['type']} but holds a value "
                f"that is not: {e}") from None
    return pa.Table.from_arrays(arrays, schema=schema)


def write_parquet(definition: dict, tables: dict, folder) -> dict:
    """Write one `<table name>.parquet` per table of `definition` into `folder`.

    `tables` is `{table name: [row dict]}` and must cover exactly the definition's
    tables. Columns come out in definition order; a missing key is a null.
    Returns `{table name: rows written}`.
    """
    # Everything that can be checked without pyarrow comes first, so a caller
    # with a bad argument is not sent to install a package.
    specs = _specs(definition)
    names = [s["name"] for s in specs]
    missing = [n for n in names if n not in tables]
    # A one-row `Source` table in `tables` is accepted and nothing is written for it: it is not part of the model.
    extra = sorted(set(tables) - set(names) - {"Source"})
    if missing or extra:
        raise ParquetTablesError(
            f"rows do not match the definition: missing {missing}, not in the definition {extra}")
    files = {n: file_name(n) for n in names}
    for s in specs:
        _columns(s)
    if len({f.lower() for f in files.values()}) != len(files):
        raise ParquetTablesError("two table names differ only by case; Windows would write one file")

    if not PYARROW_AVAILABLE:
        raise ParquetTablesError(
            "writing Parquet needs the pyarrow package, which is not installed. "
            "Install it with: pip install pyarrow")

    built = {s["name"]: _table(s, tables[s["name"]]) for s in specs}
    out = Path(folder)
    out.mkdir(parents=True, exist_ok=True)
    result = {}
    for name, table in built.items():
        pq.write_table(table, out / files[name], compression=COMPRESSION,
                       version=FORMAT_VERSION, use_dictionary=True, write_statistics=True)
        result[name] = table.num_rows
    return result


# --------------------------------------------------------- open mirroring

ROW_MARKER = "__rowMarker__"
MARKER_UPSERT = 4
MARKER_DELETE = 2
STATE_VERSION = 1
_SEQUENCE = re.compile(r"^\d{20}\.parquet$")

#: EA's own tables: the primary key each has in EA's schema.
PHYSICAL_KEYS = {
    "t_package": ["Package_ID"], "t_object": ["Object_ID"],
    "t_objectproperties": ["PropertyID"], "t_connector": ["Connector_ID"],
    "t_connectortag": ["PropertyID"], "t_diagram": ["Diagram_ID"],
    "t_diagramobjects": ["Instance_ID"], "t_attribute": ["ID"],
    "t_operation": ["OperationID"],
}


def state_path(folder) -> Path:
    """`<folder>.state.json`, beside the landing-zone folder and outside it."""
    f = Path(folder)
    return f.with_name(f.name + ".state.json")


def _declared_key(spec: dict) -> list[str] | None:
    """The key the server's definition declares for a table (`primary_key`, a list of column names), or
    None when it declares none (a definition from a server older than the keyed layer carries no key)."""
    pk = spec.get("primary_key")
    if isinstance(pk, str):
        pk = [k.strip() for k in pk.split(",")]
    if isinstance(pk, list) and pk and all(isinstance(k, str) and k for k in pk):
        return list(pk)
    return None


def _keyed_specs(defn: dict) -> list[tuple[dict, list[str]]]:
    """Every table with the key columns it is mirrored on (see the module docstring). The definition's own
    `primary_key` wins; the derivation below is the fallback for a definition that declares none."""
    out = [(s, _declared_key(s) or ["ea_guid"]) for s in defn["entities"]]
    connectors = {c["name"] for c in defn["connectors"]}
    for t in defn.get("tag_row_tables", []):
        keys = _declared_key(t)
        if keys is None:
            names = [c["name"] for c in _columns(t)]
            if "property_id" in names:
                keys = ["property_id", "value"]
            else:
                keys = ["connector_guid" if t["of"] in connectors else "ea_guid", "tag", "value"]
        out.append((t, keys))
    out += [(c, _declared_key(c) or ["connector_guid"]) for c in defn["connectors"]]
    out.append((defn["directory"], _declared_key(defn["directory"]) or ["table_name"]))
    for p in defn["physical"]:
        if p["name"] not in PHYSICAL_KEYS:
            raise ParquetTablesError(f"no known primary key for the EA table {p['name']!r}")
        out.append((p, PHYSICAL_KEYS[p["name"]]))
    return out


#: The keys the derivation gave a tag-row table before a definition could declare one (server 3.6.5). A
#: landing zone written then holds one of these in its `_metadata.json`, and Open Mirroring will not
#: change `keyColumns` once the table has data, so a later run keeps them when the table still has the columns.
LEGACY_TAG_KEYS = (["property_id", "value"], ["connector_guid", "tag", "value"], ["ea_guid", "tag", "value"])


#: How to start a landing zone over. Both sides go together: the upload record keeps counting from the old file
#: numbers, and the target keeps the old tables, unless they are deleted too.
START_OVER = ("To start over, do it on both sides: delete the table folders in the mirrored database's landing zone "
              "in OneLake (Fabric drops those tables and recreates them from the next upload), and here the table "
              "folders, the state file and the upload record (the folder's name plus .state.json and .upload.json, "
              "beside it); then write and upload again.")


def _keys_to_continue(name: str, wanted: list[str], old, cols: list[str], meta: Path):
    """The keys to write this table on: `wanted`, or the existing `old` keys when the table was written with
    the 3.6.5 derivation and still has those columns (uniqueness is checked by the caller, as for any key)."""
    if old == wanted:
        return wanted
    if old in LEGACY_TAG_KEYS and all(k in cols for k in old):
        return list(old)
    raise ParquetTablesError(
        f"{name}: keyColumns cannot change once set. {meta} has {old}, this run needs "
        f"{wanted}. Keep the old keys, or start over. {START_OVER}")


def _check_keys(name: str, keys: list[str], cols: list[str], rows: list[dict], way_out: str = "") -> list[tuple]:
    missing = [k for k in keys if k not in cols]
    if missing:
        raise ParquetTablesError(f"{name}: key column {missing} is not a column of the table")
    if ROW_MARKER in cols:
        raise ParquetTablesError(f"{name}: a column is named {ROW_MARKER}, which Open Mirroring reserves")
    seen, found = set(), []
    for r in rows:
        k = tuple(r.get(c) for c in keys)
        if any(v is None for v in k):
            raise ParquetTablesError(f"{name}: a row has no value for key column(s) {keys}: {k!r}")
        if k in seen:
            raise ParquetTablesError(
                f"{name}: key {keys} is not unique; {k!r} appears more than once, so Open Mirroring "
                f"would keep only one of those rows" + (f". {way_out}" if way_out else ""))
        seen.add(k)
        found.append(k)
    return found


def _sequence(folder: Path) -> int:
    """The highest 20-digit file number in `folder`, or 0."""
    if not folder.is_dir():
        return 0
    return max((int(p.stem) for p in folder.glob("*.parquet") if _SEQUENCE.match(p.name)), default=0)


def _atomic_write(path: Path, data: bytes) -> None:
    tmp = path.with_name("." + path.name + ".tmp")
    tmp.write_bytes(data)
    replace_file(tmp, path)   # retried on a Windows PermissionError (see onelake_upload.replace_file)


def _key_normalizer(spec: dict, keys: list[str]):
    """A function that puts a key tuple in one comparable form. A DATETIME key column holds an ISO string in
    the rows and the state file but reads back from Parquet as a datetime; both become a datetime."""
    types = {c["name"]: c["type"] for c in _columns(spec)}
    dt = [types.get(k) == "DATETIME" for k in keys]
    if not any(dt):
        return tuple
    return lambda k: tuple(_datetime(v, spec["name"], c) if is_dt else v
                           for v, c, is_dt in zip(k, keys, dt))


def _unrecorded_keys(tdir: Path, after: int, keys: list[str], name: str, norm=tuple) -> set[tuple]:
    """The keys the files numbered above `after` (the state's last file number) upsert. The writer puts a
    table's files down before the state file, so a crash in between leaves files the state does not know. They
    are this writer's own (it numbers past the state's last file), so they are read back: their upserts
    may be rows that no later run would otherwise delete. Their delete rows need no reading (a key
    already deleted is deleted again harmlessly), so the caller takes the union of these keys and the
    state's, and every one of them that is gone from the table now gets a delete."""
    out: set[tuple] = set()
    for p in sorted(tdir.glob("*.parquet")):
        if not _SEQUENCE.match(p.name) or int(p.stem) <= after:
            continue
        try:
            t = pq.read_table(p)
        except Exception as e:
            raise ParquetTablesError(
                f"{name}: {p.name} is newer than the state file's last file ({after:020d}.parquet) and cannot "
                f"be read ({type(e).__name__}), so the rows it holds cannot be worked out. {START_OVER}") from None
        names = t.column_names
        if any(k not in names for k in keys):
            raise ParquetTablesError(
                f"{name}: {p.name} is newer than the state file's last file and lacks the key column(s) "
                f"{keys}, so the rows it holds cannot be worked out. {START_OVER}")
        marks = t.column(ROW_MARKER).to_pylist() if ROW_MARKER in names else [None] * t.num_rows
        cols = [t.column(k).to_pylist() for k in keys]
        for i, m in enumerate(marks):
            if m != MARKER_DELETE:
                out.add(norm(tuple(c[i] for c in cols)))
    return out


def write_open_mirroring(definition: dict, tables: dict, folder) -> dict:
    """Write one Open Mirroring landing-zone folder per table into `folder`.

    Returns `{table: {"file": name, "upserts": n, "deletes": n, "initial": bool}}`.
    Everything is checked before the first file is written; the state file is
    written last. A crash between the table files and the state file is recovered by the next run, which
    reads back the files newer than the state's last file number (`_unrecorded_keys`).
    """
    specs = _keyed_specs(definition)
    names = [s["name"] for s, _ in specs]
    missing = [n for n in names if n not in tables]
    extra = sorted(set(tables) - set(names))
    if missing or extra:
        raise ParquetTablesError(
            f"rows do not match the definition: missing {missing}, not in the definition {extra}")
    for n in names:
        file_name(n)  # a folder name has the same limits as a file name
    for s, _ in specs:
        _columns(s)
    if len({n.lower() for n in names}) != len(names):
        raise ParquetTablesError("two table names differ only by case; Windows would write one folder")
    if not PYARROW_AVAILABLE:
        raise ParquetTablesError(
            "writing Parquet needs the pyarrow package, which is not installed. "
            "Install it with: pip install pyarrow")

    out = Path(folder)
    sp = state_path(out)
    state = {"version": STATE_VERSION, "tables": {}}
    if sp.exists():
        try:
            state = json.loads(sp.read_text(encoding="utf-8"))
            assert state["version"] == STATE_VERSION and isinstance(state["tables"], dict)
        except (ValueError, KeyError, TypeError, AssertionError):
            raise ParquetTablesError(f"{sp} is not a state file this tool wrote. {START_OVER}") from None

    plans = []
    for spec, keys in specs:
        name = spec["name"]
        cols = [c["name"] for c in _columns(spec)]
        tdir = out / name
        meta = tdir / "_metadata.json"
        kept_old = False
        if meta.exists():
            try:
                old = json.loads(meta.read_text(encoding="utf-8")).get("keyColumns")
            except (ValueError, AttributeError):
                old = None
            kept = _keys_to_continue(name, keys, old, cols, meta)
            kept_old, wanted, keys = kept != keys, keys, kept
        way_out = (f"This table was written with the keys {keys} of a definition from a server before 3.6.6, "
                   f"and its rows no longer fit them. To move to the new keys {wanted}: {START_OVER}"
                   ) if kept_old else ""
        current = _check_keys(name, keys, cols, tables[name], way_out)
        prior = state["tables"].get(name)
        if prior is None and _sequence(tdir):
            raise ParquetTablesError(
                f"{name}: {tdir} already holds data files but {sp.name} has no record of them, so "
                f"deletes cannot be worked out. {START_OVER}")
        if prior is not None and prior["keyColumns"] != keys:
            raise ParquetTablesError(
                f"{name}: keyColumns cannot change once set (the state file has {prior['keyColumns']}, "
                f"this run needs {keys}); the state file and the table's _metadata.json disagree. "
                f"{START_OVER}")
        # Keys that may be on the target: the state's, plus any unrecorded file's (see _unrecorded_keys).
        known = None
        if prior is not None:
            norm = _key_normalizer(spec, keys)
            known = list(dict.fromkeys(norm(k) for k in prior["keys"]))
            known += sorted(_unrecorded_keys(tdir, prior["last_file"], keys, name, norm) - set(known), key=repr)
        plans.append((spec, keys, cols, current, prior, kept_old, known))

    result, new_state = {}, {"version": STATE_VERSION, "tables": {}}
    out.mkdir(parents=True, exist_ok=True)
    for spec, keys, cols, current, prior, kept_old, known in plans:
        name = spec["name"]
        tdir = out / name
        tdir.mkdir(exist_ok=True)
        deletes = 0
        if prior is not None and not current and not known:
            # Nothing to upsert and nothing to delete: Fabric never moves lastSyncDateTime for an empty
            # file, so a new one would only be waited on. Write none; the file counter stays put.
            result[name] = {"file": None, "upserts": 0, "deletes": 0, "initial": False}
            if kept_old:
                result[name]["kept_existing_keys"] = keys
            new_state["tables"][name] = {"keyColumns": keys,
                                         "last_file": max(prior["last_file"], _sequence(tdir)), "keys": []}
            continue
        if prior is None:
            data = _table(spec, tables[name])
        else:
            norm = _key_normalizer(spec, keys)
            current_set = {norm(k) for k in current}
            gone = [k for k in known if k not in current_set]
            deletes = len(gone)
            del_rows = [{**{c: None for c in cols}, **dict(zip(keys, k))} for k in gone]
            markers = [MARKER_DELETE] * deletes + [MARKER_UPSERT] * len(current)
            data = _table(spec, del_rows + list(tables[name])).append_column(
                ROW_MARKER, pa.array(markers, pa.int32()))
        seq = max(_sequence(tdir), prior["last_file"] if prior else 0) + 1
        fname = f"{seq:020d}.parquet"
        buf = io.BytesIO()
        pq.write_table(data, buf, compression=COMPRESSION, version=FORMAT_VERSION,
                       use_dictionary=True, write_statistics=True)
        _atomic_write(tdir / "_metadata.json",
                      (json.dumps({"keyColumns": keys}, indent=2) + "\n").encode("utf-8"))
        _atomic_write(tdir / fname, buf.getvalue())
        result[name] = {"file": fname, "upserts": len(current), "deletes": deletes,
                        "initial": prior is None}
        if kept_old:
            result[name]["kept_existing_keys"] = keys
        new_state["tables"][name] = {"keyColumns": keys, "last_file": seq,
                                     "keys": [list(k) for k in current]}
    _atomic_write(sp, json.dumps(new_state).encode("utf-8"))
    return result


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(
        description="Write the Parquet files for a business-layer definition and the .pbip that reads them.")
    ap.add_argument("definition")
    ap.add_argument("tables")
    ap.add_argument("--project-name", default=None,
                    help="default: the name of source.folder")
    ap.add_argument("--out", default=None,
                    help="where the .pbip goes (default: the parent of source.folder); with "
                         "--layout open-mirroring, the landing-zone folder to write")
    ap.add_argument("--layout", choices=("default", "open-mirroring"), default="default",
                    help="default: one <table>.parquet per table plus the .pbip. open-mirroring: the "
                         "Fabric Open Mirroring landing zone (a folder per table, _metadata.json, "
                         "20-digit sequential files, changes after the first run); writes no .pbip")
    ap.add_argument("--descriptions", default=None,
                    help="a user-approved descriptions file (JSON), as for powerbi_model.py")
    a = ap.parse_args(argv)
    defn = json.loads(Path(a.definition).read_text(encoding="utf-8"))
    tables = json.loads(Path(a.tables).read_text(encoding="utf-8"))
    if not powerbi_model.is_parquet(defn):
        ap.error("the definition's source.kind is not 'parquet'")
    entries = descriptions.load_file(a.descriptions) if a.descriptions else None
    if a.layout == "open-mirroring":
        if not a.out:
            ap.error("--layout open-mirroring needs --out, the landing-zone folder")
        res = write_open_mirroring(defn, tables, a.out)
        print(f"{len(res)} tables -> {a.out}")
        print(f"{sum(r['upserts'] for r in res.values())} rows, "
              f"{sum(r['deletes'] for r in res.values())} deletes; state: {state_path(a.out)}")
        return 0
    folder = Path(defn["source"]["folder"])
    counts = write_parquet(defn, tables, folder)
    name = a.project_name or folder.name
    out = Path(a.out) if a.out else folder.parent
    powerbi_model.write_project(defn, out, name, descriptions=entries)
    print(f"{len(counts)} tables, {sum(counts.values())} rows -> {folder}")
    print(f"{out / (name + '.pbip')}")
    model = powerbi_model.model_from_definition(defn, descriptions=entries)
    for line in powerbi_model.size_lines(*powerbi_model.model_size(model)):
        print(line)
    return 0


if __name__ == "__main__":
    sys.exit(main())

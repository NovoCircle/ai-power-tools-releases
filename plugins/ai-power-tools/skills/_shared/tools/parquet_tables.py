#!/usr/bin/env python3
"""Path C: the business-layer tables as Parquet, with the types the definition declares.

    definition.json + tables.json  ->  <table name>.parquet per table  (+ the .pbip)

The server's `build_reporting_database` writes the definition (`APT-2026-0301`) and
the typed rows for a profile whose `target.kind` is "parquet". This module is the
local step: it writes one file per table into `source.folder`, and
`powerbi_model.write_project` writes the `.pbip` that reads them. No SQL Server is
involved.

TYPES ARE DECLARED, NEVER INFERRED
----------------------------------
TEXT -> string, INTEGER -> int64, REAL -> float64, BOOLEAN -> bool, DATETIME ->
timestamp (microseconds, no zone). A refresh must not change a column's type
because of which rows happen to be populated, and pyarrow refuses a value that
does not fit its column rather than repairing it (`APT-2026-0225`). Every field is
nullable. An empty table is still written, with its schema.

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
import json
import re
import sys
from datetime import date, datetime
from pathlib import Path

try:  # pragma: no cover - environment-dependent
    import pyarrow as pa
    import pyarrow.parquet as pq
    PYARROW_AVAILABLE = True
except ImportError:  # pragma: no cover - environment-dependent
    pa = pq = None
    PYARROW_AVAILABLE = False

import powerbi_model

COMPRESSION = "snappy"
FORMAT_VERSION = "2.6"

#: Characters Windows does not allow in a file name, plus control characters.
_BAD_CHARS = re.compile(r'[<>:"/\\|?*\x00-\x1f]')
_RESERVED = {"CON", "PRN", "AUX", "NUL"} | {f"{p}{i}" for p in ("COM", "LPT") for i in range(1, 10)}


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


#: A time with no date is EA's stored default for a date it never set
#: (`t_package.LastLoadDate` reads "12:00:00 AM"). It is anchored on the OLE
#: automation zero date, which is what the repository's own date type counts from,
#: so the value stays recognizable rather than being given a date it never had.
TIME_ONLY_DATE = date(1899, 12, 30)

#: Formats the server hands over, tried in order. The business tables carry ISO
#: text; the physical tables carry EA's own US 12-hour text.
_DATETIME_FORMATS = ("%m/%d/%Y %I:%M:%S %p",)


def _datetime(value, table: str, column: str):
    if value is None or isinstance(value, datetime):
        return value
    try:
        return datetime.fromisoformat(value)
    except (TypeError, ValueError):
        pass
    for fmt in _DATETIME_FORMATS:
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            pass
    try:
        return datetime.combine(TIME_ONLY_DATE, datetime.strptime(value, "%I:%M:%S %p").time())
    except (TypeError, ValueError):
        raise ParquetTablesError(
            f"{table}.{column}: {value!r} is not a date and time (expected "
            f"'YYYY-MM-DD HH:MM:SS' or 'M/D/YYYY h:mm:ss AM')") from None


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
        except (pa.ArrowInvalid, pa.ArrowTypeError) as e:
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
    extra = sorted(set(tables) - set(names))
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


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(
        description="Write the Parquet files for a business-layer definition and the .pbip that reads them.")
    ap.add_argument("definition")
    ap.add_argument("tables")
    ap.add_argument("--project-name", default=None,
                    help="default: the name of source.folder")
    ap.add_argument("--out", default=None,
                    help="where the .pbip goes (default: the parent of source.folder)")
    a = ap.parse_args(argv)
    defn = json.loads(Path(a.definition).read_text(encoding="utf-8"))
    tables = json.loads(Path(a.tables).read_text(encoding="utf-8"))
    if not powerbi_model.is_parquet(defn):
        ap.error("the definition's source.kind is not 'parquet'")
    folder = Path(defn["source"]["folder"])
    counts = write_parquet(defn, tables, folder)
    name = a.project_name or folder.name
    out = Path(a.out) if a.out else folder.parent
    powerbi_model.write_project(defn, out, name)
    print(f"{len(counts)} tables, {sum(counts.values())} rows -> {folder}")
    print(f"{out / (name + '.pbip')}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

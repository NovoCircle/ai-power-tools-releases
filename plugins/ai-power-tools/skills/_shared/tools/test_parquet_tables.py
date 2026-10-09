#!/usr/bin/env python3
"""Tests for path C: Parquet files and the .pbip that reads them.

    python -m pytest _shared/tools/test_parquet_tables.py -q

Hermetic: the Westbrook Bank definition fixture, rows built in the test, a temp
folder. The three-path comparison needs no pyarrow; the writer tests skip without it.
"""
from __future__ import annotations

import copy
import json
from datetime import datetime
from pathlib import Path

import pytest

import parquet_tables
from parquet_tables import ParquetTablesError, file_name, write_parquet
from powerbi_model import project_files_from_definition

FIXTURE = Path(__file__).parent / "fixtures" / "westbrook.definition.json"

needs_pyarrow = pytest.mark.skipif(not parquet_tables.PYARROW_AVAILABLE,
                                   reason="pyarrow is not installed")

ALL_TYPES = [{"name": n, "type": t} for n, t in
             (("s", "TEXT"), ("i", "INTEGER"), ("r", "REAL"), ("b", "BOOLEAN"), ("d", "DATETIME"))]


@pytest.fixture(scope="module")
def defn():
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def parquet_defn(defn, folder="C:\\data\\wb"):
    d = copy.deepcopy(defn)
    d["source"] = {"kind": "parquet", "server": "", "database": "", "schema": "logical",
                   "folder": folder, "physical_schema": "dbo"}
    return d


def spec_columns(spec):
    return spec.get("all_columns", spec.get("columns"))


def tiny():
    """A one-table definition covering every declared type."""
    return {"source": {"kind": "parquet", "folder": "x", "schema": "logical", "physical_schema": "dbo"},
            "entities": [], "connectors": [], "tag_row_tables": [],
            "directory": {"name": "Table Directory", "entries": [], "all_columns": copy.deepcopy(ALL_TYPES)},
            "physical": []}


# ------------------------------------------------- the three paths, one model


PARTITION = "\tpartition "
AFTER = "\tannotation PBI_ResultType"


def without_partition(text: str) -> str:
    lines = text.split("\r\n")
    start = next((i for i, l in enumerate(lines) if l.startswith(PARTITION)), None)
    if start is None:
        return text
    end = next(i for i, l in enumerate(lines) if i > start and l.startswith(AFTER))
    return "\r\n".join(lines[:start] + lines[end:])


def test_sql_path_b_sql_path_a_and_parquet_differ_only_in_partition_source_and_mode(defn):
    b = copy.deepcopy(defn)
    b["source"]["physical_schema"] = "dbo"
    a = copy.deepcopy(defn)
    a["source"]["physical_schema"] = a["source"]["schema"]
    c = parquet_defn(defn)
    fb = project_files_from_definition(b, "P")
    fa = project_files_from_definition(a, "P")
    fc = project_files_from_definition(c, "P")
    assert fb.keys() == fa.keys() == fc.keys()
    tables = [k for k in fb if "/definition/tables/" in k]
    assert len(tables) == len(defn["entities"]) + len(defn["connectors"]) + len(defn["tag_row_tables"]) + 1 + 9
    for k in fb:
        if k in tables:
            assert fb[k] != fc[k]
            assert without_partition(fb[k]) == without_partition(fa[k]) == without_partition(fc[k]), k
        else:
            assert fb[k] == fa[k] == fc[k], k


def test_the_three_paths_still_agree_on_what_the_comparison_strips(defn):
    """Guards the guard: the comparison must not pass because it stripped too much."""
    fc = project_files_from_definition(parquet_defn(defn), "P")
    t = fc["P.SemanticModel/definition/tables/AI Gateway.tmdl"]
    assert "\tcolumn ea_guid" in t and "annotation PBI_ResultType" in t
    assert "partition" not in without_partition(t)
    rel = fc["P.SemanticModel/definition/relationships.tmdl"]
    assert rel.count("isActive: false") == 6
    assert any("measure " in v for v in fc.values())
    assert "isHidden" in fc["P.SemanticModel/definition/tables/t_object.tmdl"]


def test_parquet_partition_reads_one_file_per_table_in_import_mode(defn):
    files = project_files_from_definition(parquet_defn(defn, "C:\\data\\wb"), "P")
    t = files["P.SemanticModel/definition/tables/Con_AI Gateway Uses AI Service.tmdl"]
    assert "mode: import" in t
    assert 'Parquet.Document(File.Contents("C:\\data\\wb\\Con_AI Gateway Uses AI Service.parquet"))' in t
    phys = files["P.SemanticModel/definition/tables/t_object.tmdl"]
    assert 'File.Contents("C:\\data\\wb\\t_object.parquet")' in phys
    assert "Sql.Database" not in "".join(files.values())


def test_parquet_refuses_direct_query(defn):
    with pytest.raises(ValueError, match="import"):
        project_files_from_definition(parquet_defn(defn), "P", mode="directQuery")


def test_a_definition_without_a_kind_is_still_sql(defn):
    assert "kind" not in defn["source"]
    t = project_files_from_definition(defn, "P")["P.SemanticModel/definition/tables/t_object.tmdl"]
    assert "Sql.Database" in t


# ---------------------------------------------------------------- file names


def test_file_names_keep_spaces_and_parentheses():
    assert file_name("Con_Data Entity Association Data Entity (not in MDG)") == \
        "Con_Data Entity Association Data Entity (not in MDG).parquet"


@pytest.mark.parametrize("name", ['a/b', 'a\\b', 'a:b', 'a*b', 'a?b', 'a"b', 'a<b', 'a>b', 'a|b',
                                  'a\tb', 'x.', 'x ', '', 'CON', 'nul', 'COM1', 'Lpt9.txt'])
def test_names_windows_cannot_hold_are_refused(name):
    with pytest.raises(ParquetTablesError, match="Windows file name"):
        file_name(name)


def test_a_bad_table_name_writes_nothing(defn, tmp_path):
    d = parquet_defn(defn)
    d["entities"][0]["name"] = "bad/name"
    rows = {spec["name"]: [] for spec in (list(d["entities"]) + list(d["connectors"]) + list(d["tag_row_tables"])
                                         + [d["directory"]] + list(d["physical"]))}
    with pytest.raises(ParquetTablesError, match="Windows file name"):
        write_parquet(d, rows, tmp_path / "out")
    assert not (tmp_path / "out").exists()


# ------------------------------------------------------------------- writer


def read(path):
    import pyarrow.parquet as pq
    return pq.read_table(path)


@needs_pyarrow
def test_every_declared_type_gets_its_arrow_type_and_values_round_trip(tmp_path):
    import pyarrow as pa
    d = tiny()
    rows = {"Table Directory": [
        {"s": "x", "i": 7, "r": 1.5, "b": True, "d": "2026-05-01 05:41:40"},
        {"s": None, "i": None, "r": None, "b": None, "d": None}]}
    assert write_parquet(d, rows, tmp_path) == {"Table Directory": 2}
    t = read(tmp_path / "Table Directory.parquet")
    assert [f.type for f in t.schema] == [pa.string(), pa.int64(), pa.float64(), pa.bool_(),
                                          pa.timestamp("us")]
    assert t.to_pylist() == [
        {"s": "x", "i": 7, "r": 1.5, "b": True, "d": datetime(2026, 5, 1, 5, 41, 40)},
        {"s": None, "i": None, "r": None, "b": None, "d": None}]
    assert all(f.nullable for f in t.schema)


@needs_pyarrow
def test_columns_follow_the_definition_and_a_missing_key_is_null(tmp_path):
    d = tiny()
    rows = {"Table Directory": [{"d": None, "i": 3}, {"s": "only"}]}
    write_parquet(d, rows, tmp_path)
    t = read(tmp_path / "Table Directory.parquet")
    assert t.column_names == ["s", "i", "r", "b", "d"]
    assert t.to_pylist() == [{"s": None, "i": 3, "r": None, "b": None, "d": None},
                             {"s": "only", "i": None, "r": None, "b": None, "d": None}]


@needs_pyarrow
def test_an_empty_table_is_written_with_its_schema(tmp_path):
    write_parquet(tiny(), {"Table Directory": []}, tmp_path)
    t = read(tmp_path / "Table Directory.parquet")
    assert t.num_rows == 0 and t.column_names == ["s", "i", "r", "b", "d"]


@needs_pyarrow
def test_physical_tables_use_their_columns_key(tmp_path):
    d = tiny()
    d["physical"] = [{"name": "t_package", "rows": 1,
                      "columns": [{"name": "Package_ID", "type": "INTEGER"}]}]
    write_parquet(d, {"Table Directory": [], "t_package": [{"Package_ID": 4}]}, tmp_path)
    assert read(tmp_path / "t_package.parquet").to_pylist() == [{"Package_ID": 4}]


@needs_pyarrow
def test_a_value_of_the_wrong_type_is_refused_not_repaired(tmp_path):
    with pytest.raises(ParquetTablesError, match=r"i is declared INTEGER"):
        write_parquet(tiny(), {"Table Directory": [{"i": "true"}]}, tmp_path)


@needs_pyarrow
def test_physical_table_dates_in_the_repository_text_form_are_parsed(tmp_path):
    rows = {"Table Directory": [{"d": "5/1/2026 5:41:01 AM"}, {"d": "9/30/2026 1:19:38 PM"},
                                {"d": "12:00:00 AM"}, {"d": "2026-05-01 05:41:40.250000"}]}
    write_parquet(tiny(), rows, tmp_path)
    got = [r["d"] for r in read(tmp_path / "Table Directory.parquet").to_pylist()]
    assert got == [datetime(2026, 5, 1, 5, 41, 1), datetime(2026, 9, 30, 13, 19, 38),
                   datetime(1899, 12, 30), datetime(2026, 5, 1, 5, 41, 40, 250000)]


@needs_pyarrow
def test_a_bad_date_names_the_column(tmp_path):
    with pytest.raises(ParquetTablesError, match=r"Table Directory\.d"):
        write_parquet(tiny(), {"Table Directory": [{"d": "yesterday"}]}, tmp_path)


def test_rows_must_cover_exactly_the_definitions_tables(tmp_path):
    with pytest.raises(ParquetTablesError, match="missing"):
        write_parquet(tiny(), {}, tmp_path)
    with pytest.raises(ParquetTablesError, match="not in the definition"):
        write_parquet(tiny(), {"Table Directory": [], "Surplus": []}, tmp_path)


def test_unknown_declared_type_is_refused(tmp_path):
    d = tiny()
    d["directory"]["all_columns"][0]["type"] = "GEOMETRY"
    with pytest.raises(ParquetTablesError, match="GEOMETRY"):
        write_parquet(d, {"Table Directory": []}, tmp_path)


def test_without_pyarrow_the_error_names_the_package(monkeypatch, tmp_path):
    monkeypatch.setattr(parquet_tables, "PYARROW_AVAILABLE", False)
    with pytest.raises(ParquetTablesError, match="pip install pyarrow"):
        write_parquet(tiny(), {"Table Directory": []}, tmp_path)
    assert not list(tmp_path.iterdir())


def test_argument_errors_come_before_the_pyarrow_error(monkeypatch, tmp_path):
    monkeypatch.setattr(parquet_tables, "PYARROW_AVAILABLE", False)
    with pytest.raises(ParquetTablesError, match="missing"):
        write_parquet(tiny(), {}, tmp_path)


@needs_pyarrow
def test_two_writes_are_byte_identical(tmp_path):
    rows = {"Table Directory": [{"s": "x", "i": 1, "r": 2.5, "b": False, "d": "2026-05-01 05:41:40"},
                                {"s": "y"}]}
    write_parquet(tiny(), rows, tmp_path / "a")
    write_parquet(tiny(), rows, tmp_path / "b")
    write_parquet(tiny(), rows, tmp_path / "b")
    assert (tmp_path / "a" / "Table Directory.parquet").read_bytes() == \
        (tmp_path / "b" / "Table Directory.parquet").read_bytes()


# ---------------------------------------------------------------------- CLI


@needs_pyarrow
def test_cli_writes_the_files_and_the_project_next_to_them(defn, tmp_path, capsys):
    folder = tmp_path / "out" / "parquet"
    d = parquet_defn(defn, str(folder))
    rows = {}
    for spec in (list(d["entities"]) + list(d["connectors"]) + list(d["tag_row_tables"])
                 + [d["directory"]] + list(d["physical"])):
        rows[spec["name"]] = [{c["name"]: None for c in spec_columns(spec)}]
    (tmp_path / "d.json").write_text(json.dumps(d), encoding="utf-8")
    (tmp_path / "t.json").write_text(json.dumps(rows), encoding="utf-8")

    assert parquet_tables.main([str(tmp_path / "d.json"), str(tmp_path / "t.json"),
                                "--project-name", "WB"]) == 0
    assert len(list(folder.glob("*.parquet"))) == len(rows)
    assert (tmp_path / "out" / "WB.pbip").exists()
    table = (tmp_path / "out" / "WB.SemanticModel" / "definition" / "tables" / "t_object.tmdl").read_text("utf-8")
    assert str(folder / "t_object.parquet") in table
    assert str(tmp_path / "out" / "WB.pbip") in capsys.readouterr().out

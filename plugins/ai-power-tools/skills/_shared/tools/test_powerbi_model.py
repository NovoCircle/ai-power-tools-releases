#!/usr/bin/env python3
"""Tests for the Power BI model generated from the business-layer definition.

    python -m pytest _shared/tools/test_powerbi_model.py -q

Hermetic: the fixture is the Westbrook Bank definition the server writes, and
nothing here touches a database, Power BI or the network.
"""
from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

import tmdl
from powerbi_model import (PHYSICAL_GAP, PHYSICAL_RELS, Resolver, SchemaSqlSource,
                           layout_from_definition, model_from_definition,
                           project_files_from_definition, write_project)
from semantic_model import SemanticTable

FIXTURE = Path(__file__).parent / "fixtures" / "westbrook.definition.json"
PHYSICAL = ["t_package", "t_object", "t_objectproperties", "t_connector", "t_connectortag",
            "t_diagram", "t_diagramobjects", "t_attribute", "t_operation"]


@pytest.fixture(scope="module")
def defn():
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def model(defn):
    return model_from_definition(defn)


def business_names(defn):
    return ([e["name"] for e in defn["entities"]] + [c["name"] for c in defn["connectors"]]
            + [t["name"] for t in defn["tag_row_tables"]] + [defn["directory"]["name"]])


def con_tables(model):
    return [t for t in model.tables if t.name.startswith("Con_")]


# ------------------------------------------------------------------- tables


def test_tables_are_every_business_table_plus_the_nine_physical(defn, model):
    assert [t.name for t in model.tables] == business_names(defn) + [p["name"] for p in defn["physical"]]
    assert len(model.tables) == len(business_names(defn)) + 9
    assert sorted(p["name"] for p in defn["physical"]) == sorted(PHYSICAL)


def test_table_names_are_exactly_the_definitions(model):
    names = {t.name for t in model.tables}
    assert "Con_Data Entity Association Data Entity (not in MDG)" in names
    assert "VendorApplication (not in MDG)" in names
    assert "Table Directory" in names


def test_source_names_carry_the_schema_per_table(defn, model):
    src = defn["source"]
    for t in model.tables:
        schema = src["physical_schema"] if t.name in PHYSICAL else src["schema"]
        assert t.source_name == f"{schema}.{t.name}"


def test_columns_map_declared_types(model):
    cols = {c.name: c.data_type for c in model.table("Con_AI Gateway Uses AI Service").columns}
    assert cols["connector_id"] == "int64"
    assert cols["source_guid"] == "string"
    assert {c.name: c.data_type for c in model.table("t_package").columns}["CreatedDate"] == "dateTime"


def test_every_declared_type_is_mapped():
    d = {"source": {"server": "s", "database": "d", "schema": "x", "physical_schema": "dbo"},
         "entities": [], "connectors": [], "tag_row_tables": [],
         "directory": {"name": "Table Directory", "entries": [],
                       "all_columns": [{"name": "a", "type": t}
                                       for t in ("TEXT", "INTEGER", "REAL", "BOOLEAN", "DATETIME")]},
         "physical": []}
    got = [c.data_type for c in model_from_definition(d).table("Table Directory").columns]
    assert got == ["string", "int64", "double", "boolean", "dateTime"]


def test_an_unknown_type_is_refused(defn):
    bad = copy.deepcopy(defn)
    bad["entities"][0]["all_columns"][0]["type"] = "GEOMETRY"
    with pytest.raises(ValueError, match="GEOMETRY"):
        model_from_definition(bad)


def test_physical_tables_are_hidden_and_business_tables_are_not(model):
    for t in model.tables:
        assert t.is_hidden == (t.name in PHYSICAL), t.name


def test_descriptions_come_from_the_directory_and_physical_have_none(defn, model):
    entries = {e["table_name"]: e["description"] for e in defn["directory"]["entries"]}
    described = [n for n, d in entries.items() if d]
    assert described
    for n in described:
        assert model.table(n).description == entries[n]
    for p in PHYSICAL:
        assert model.table(p).description == ""


# ------------------------------------------------------------ relationships


def test_relationship_set_and_order(defn, model):
    expected = []
    for c in defn["connectors"]:
        expected += [(c["name"], "source_guid", c["source"]), (c["name"], "target_guid", c["target"])]
    expected += [(m, mc, o) for m, mc, o, _ in PHYSICAL_RELS]
    expected += [("t_object", "ea_guid", e["name"]) for e in defn["entities"]]
    assert [(r.from_table, r.from_column, r.to_table) for r in model.relationships] == expected
    assert len(model.relationships) == 74


def test_tag_row_relationships_precede_in_definition_order(defn):
    d = copy.deepcopy(defn)
    ent, con = d["entities"][0]["name"], d["connectors"][1]["name"]
    d["tag_row_tables"] = [
        {"name": f"{con} tags", "of": con, "rows": 0,
         "all_columns": [{"name": "connector_guid", "type": "TEXT"}]},
        {"name": f"{ent} tags", "of": ent, "rows": 0,
         "all_columns": [{"name": "ea_guid", "type": "TEXT"}]}]
    got = [(r.from_table, r.from_column, r.to_table) for r in model_from_definition(d).relationships]
    assert got[0] == (f"{ent} tags", "ea_guid", ent)
    c0, c1 = d["connectors"][0]["name"], d["connectors"][1]["name"]
    assert got[1:6] == [(c0, "source_guid", d["connectors"][0]["source"]),
                        (c0, "target_guid", d["connectors"][0]["target"]),
                        (c1, "source_guid", d["connectors"][1]["source"]),
                        (c1, "target_guid", d["connectors"][1]["target"]),
                        (f"{c1} tags", "connector_guid", c1)]


def test_column_descriptions_are_carried(defn):
    d = copy.deepcopy(defn)
    d["entities"][0]["all_columns"][1]["description"] = "Tag note from the MDG."
    m = model_from_definition(d)
    cols = m.table(d["entities"][0]["name"]).columns
    assert cols[1].description == "Tag note from the MDG."
    assert cols[0].description == ""


def test_each_connector_relates_source_and_target_to_its_entities(defn, model):
    by = {(r.from_table, r.from_column): r for r in model.relationships}
    for c in defn["connectors"]:
        s, t = by[(c["name"], "source_guid")], by[(c["name"], "target_guid")]
        assert (s.to_table, s.to_column) == (c["source"], "ea_guid")
        assert (t.to_table, t.to_column) == (c["target"], "ea_guid")


def test_business_layer_filters_physical(defn, model):
    cross = [r for r in model.relationships if r.from_table == "t_object" and r.from_column == "ea_guid"]
    assert sorted(r.to_table for r in cross) == sorted(e["name"] for e in defn["entities"])
    assert not [r for r in model.relationships if r.to_table == "t_object" and r.to_column == "ea_guid"]


def test_inactive_are_the_second_self_link_and_the_two_physical_ones(defn, model):
    self_links = [c for c in defn["connectors"] if c["source"] == c["target"]]
    assert len(self_links) == 4
    expected = {(c["name"], "target_guid") for c in self_links}
    expected |= {("t_diagram", "Package_ID"), ("t_connector", "End_Object_ID")}
    got = {(r.from_table, r.from_column) for r in model.inactive}
    assert got == expected
    for c in self_links:
        source_rel = next(r for r in model.relationships
                          if (r.from_table, r.from_column) == (c["name"], "source_guid"))
        assert source_rel.is_active


def test_never_two_relationships_between_the_same_pair_active(model):
    pairs = [frozenset((r.from_table, r.to_table)) for r in model.relationships if r.is_active]
    assert len(pairs) == len(set(pairs))


def test_no_table_has_two_active_filter_paths_from_one_source(model):
    children = {}
    for r in model.relationships:
        if r.is_active:
            children.setdefault(r.to_table, []).append(r.from_table)

    def reached(src):
        out = []
        for c in children.get(src, ()):
            out += [c] + reached(c)
        return out

    for src in children:
        got = reached(src)
        assert len(got) == len(set(got)), src


def test_relationship_names_are_unique_and_stable(model, defn):
    names = [r.name for r in model.relationships]
    assert len(names) == len(set(names))
    assert names == [r.name for r in model_from_definition(defn).relationships]


def test_resolver_marks_a_second_path_inactive():
    res = Resolver()
    res.add("B", "a", "A", "a", "x")
    res.add("C", "b", "B", "b", "x")
    res.add("C", "a", "A", "a", "x")
    assert [r.is_active for r in res.out] == [True, True, False]
    assert "second filter path" in res.out[2].why


def test_tag_row_tables_relate_to_their_table(defn):
    d = copy.deepcopy(defn)
    ent = d["entities"][0]["name"]
    con = d["connectors"][0]["name"]
    d["tag_row_tables"] = [
        {"name": f"{ent} tags", "of": ent, "rows": 0,
         "all_columns": [{"name": "ea_guid", "type": "TEXT"}, {"name": "tag", "type": "TEXT"}]},
        {"name": f"{con} tags", "of": con, "rows": 0,
         "all_columns": [{"name": "connector_guid", "type": "TEXT"}, {"name": "tag", "type": "TEXT"}]}]
    m = model_from_definition(d)
    by = {r.from_table: r for r in m.relationships}
    assert (by[f"{ent} tags"].to_table, by[f"{ent} tags"].to_column) == (ent, "ea_guid")
    assert (by[f"{con} tags"].to_table, by[f"{con} tags"].to_column) == (con, "connector_guid")
    assert len(m.relationships) == 76
    assert [t.name for t in m.tables][-9 - 1] == "Table Directory"


# ----------------------------------------------------------------- measures


def test_one_measure_per_inactive_connector_relationship_and_no_other(model):
    measures = [(t.name, m) for t in model.tables for m in t.measures]
    inactive_con = [r for r in model.inactive if r.from_table.startswith("Con_")]
    assert len(measures) == len(inactive_con) == 4
    assert {t for t, _ in measures} == {r.from_table for r in inactive_con}
    assert len({m.name for _, m in measures}) == 4


def test_measure_uses_the_inactive_relationship_on_its_own_table(model):
    for r in (r for r in model.inactive if r.from_table.startswith("Con_")):
        (m,) = model.table(r.from_table).measures
        assert m.expression == (f"CALCULATE(COUNTROWS('{r.from_table}'), "
                                f"USERELATIONSHIP('{r.from_table}'[{r.from_column}], "
                                f"'{r.to_table}'[{r.to_column}]))")
        assert m.name.endswith(f"by target {r.to_table}")


def test_measure_names_are_unique_when_stereotypes_collide(defn):
    d = copy.deepcopy(defn)
    a = next(c for c in d["connectors"] if c["name"] == "Con_Business Application Uses Business Application")
    twin = copy.deepcopy(a)
    twin["name"] = "Con_Business Application BMM Uses Business Application"
    twin["key"] = "BMM::Uses"
    d["connectors"].append(twin)
    names = [m.name for t in model_from_definition(d).tables for m in t.measures]
    assert len(names) == len(set(names)) == 5


def test_no_measure_on_a_hidden_table(model):
    for t in model.tables:
        if t.is_hidden:
            assert t.measures == [], t.name


def test_no_measure_on_a_business_table_that_is_not_a_connector(model):
    for t in model.tables:
        if t.measures:
            assert t.name.startswith("Con_")


# ------------------------------------------------------------------- layout


def test_layout_bands_in_order_with_physical_last_and_a_gap(defn, model):
    layout = layout_from_definition(defn, model)
    assert layout["version"] == "1.1.0"
    nodes = layout["diagrams"][0]["nodes"]
    assert len(nodes) == len(model.tables)
    top = {n["nodeIndex"]: n["location"]["y"] for n in nodes}
    bottom = {n["nodeIndex"]: n["location"]["y"] + n["size"]["height"] for n in nodes}
    ents = [e["name"] for e in defn["entities"]]
    cons = [c["name"] for c in defn["connectors"]]
    rows = [defn["directory"]["name"]] + [t["name"] for t in defn["tag_row_tables"]]
    assert max(bottom[n] for n in ents) < min(top[n] for n in cons)
    assert max(bottom[n] for n in cons) < min(top[n] for n in rows)
    assert max(bottom[n] for n in rows) + PHYSICAL_GAP <= min(top[n] for n in PHYSICAL)
    assert min(top[n] for n in PHYSICAL) > max(top[n] for n in ents + cons + rows)


def test_layout_rows_hold_nine_and_tags_match_the_tmdl(defn, model):
    nodes = layout_from_definition(defn, model)["diagrams"][0]["nodes"]
    physical = [n for n in nodes if n["nodeIndex"] in PHYSICAL]
    assert len({n["location"]["y"] for n in physical}) == 1
    for n in nodes:
        assert n["nodeLineageTag"] == tmdl.lineage_tag("table", n["nodeIndex"])
    assert [n["zIndex"] for n in nodes] == list(range(len(nodes)))


# ------------------------------------------------------------------ project


def test_partition_takes_the_schema_per_table(defn):
    files = project_files_from_definition(defn, "P")
    biz = files["P.SemanticModel/definition/tables/AI Gateway.tmdl"]
    phys = files["P.SemanticModel/definition/tables/t_object.tmdl"]
    assert 'Schema="p5test",Item="AI Gateway"' in biz
    assert 'Schema="dbo",Item="t_object"' in phys


def test_schema_source_escapes_values():
    t = SemanticTable(name="x", source_name='s"1.it"em')
    lines = SchemaSqlSource(server="srv", database="db").expression(t)
    assert 'Schema="s""1",Item="it""em"' in "".join(lines)


def test_modes_differ_only_in_the_partition_mode(defn):
    imp = project_files_from_definition(defn, "P", mode="import")
    dq = project_files_from_definition(defn, "P", mode="directQuery")
    assert imp.keys() == dq.keys()
    for k in imp:
        if imp[k] != dq[k]:
            assert k.endswith(".tmdl") and "/tables/" in k
            assert imp[k].replace("mode: import", "mode: directQuery") == dq[k]
    assert "mode: import" in imp["P.SemanticModel/definition/tables/AI Gateway.tmdl"]
    assert "mode: directQuery" in dq["P.SemanticModel/definition/tables/AI Gateway.tmdl"]


def test_unknown_mode_is_refused(defn):
    with pytest.raises(ValueError):
        project_files_from_definition(defn, "P", mode="dual")


def test_tmdl_is_tab_indented_crlf_and_hides_physical(defn):
    files = project_files_from_definition(defn, "P")
    obj = files["P.SemanticModel/definition/tables/t_object.tmdl"]
    assert "\r\n" in obj and "\n" not in obj.replace("\r\n", "")
    assert "\n\tisHidden" in obj.replace("\r\n", "\n")
    assert not any(line.startswith(" ") for line in obj.split("\r\n"))
    rel = files["P.SemanticModel/definition/relationships.tmdl"]
    assert rel.count("isActive: false") == 6
    layout = files["P.SemanticModel/diagramLayout.json"]
    assert json.loads(layout)["version"] == "1.1.0"
    assert "\r\n" in layout


def test_two_runs_write_byte_identical_files(defn, tmp_path):
    a, b = tmp_path / "a", tmp_path / "b"
    write_project(defn, a, "P")
    write_project(defn, b, "P")
    write_project(defn, b, "P")
    fa = sorted(p.relative_to(a) for p in a.rglob("*") if p.is_file())
    fb = sorted(p.relative_to(b) for p in b.rglob("*") if p.is_file())
    assert fa == fb and fa
    for rel in fa:
        assert (a / rel).read_bytes() == (b / rel).read_bytes(), rel


def test_write_project_replaces_the_definition_folder(defn, tmp_path):
    write_project(defn, tmp_path, "P")
    stale = tmp_path / "P.SemanticModel" / "definition" / "tables" / "gone.tmdl"
    stale.write_text("x")
    write_project(defn, tmp_path, "P")
    assert not stale.exists()
    assert (tmp_path / "P.SemanticModel" / "diagramLayout.json").exists()


def test_no_hub_is_emitted(defn):
    files = project_files_from_definition(defn, "P")
    assert not any("_keymap" in k or "_keymap" in v for k, v in files.items())


def test_rewriting_leaves_an_existing_report_untouched(defn, tmp_path):
    write_project(defn, tmp_path, "P")
    report = tmp_path / "P.Report"
    assert (report / "definition" / "report.json").exists()
    marker = report / "definition" / "pages" / "visual.json"
    marker.write_text("built by the customer")
    edited = report / "definition" / "report.json"
    edited.write_text("{}")
    before = {p: p.read_bytes() for p in report.rglob("*") if p.is_file()}
    table = tmp_path / "P.SemanticModel" / "definition" / "tables" / "AI Gateway.tmdl"
    table.write_text("stale")
    write_project(defn, tmp_path, "P")
    assert {p: p.read_bytes() for p in report.rglob("*") if p.is_file()} == before
    assert table.read_bytes() != b"stale"
    assert (tmp_path / "P.pbip").exists()


@pytest.mark.parametrize("name", ["", ".", "..", "../P", "..\\P", "a/b", "C:P", "P.", "P ", "P?", 'P"', "P\x00"])
def test_a_name_that_is_not_a_plain_file_name_is_refused(defn, tmp_path, name):
    out = tmp_path / "out"
    out.mkdir()
    keep = tmp_path / "P.SemanticModel" / "definition" / "keep.tmdl"
    keep.parent.mkdir(parents=True)
    keep.write_text("x")
    with pytest.raises(ValueError, match="plain file name"):
        write_project(defn, out, name)
    assert keep.exists() and not any(out.iterdir())


def test_a_name_with_spaces_is_accepted(defn, tmp_path):
    write_project(defn, tmp_path, "EA Reporting")
    assert (tmp_path / "EA Reporting.pbip").exists()


def test_a_file_path_leaving_the_output_folder_is_refused_before_anything_is_deleted(defn, tmp_path, monkeypatch):
    import powerbi_model
    out = tmp_path / "out"
    write_project(defn, out, "P")
    stale = out / "P.SemanticModel" / "definition"
    files = project_files_from_definition(defn, "P")
    files["P.SemanticModel/definition/tables/../../../../escaped.tmdl"] = "x"
    monkeypatch.setattr(powerbi_model, "project_files_from_definition", lambda *a, **k: files)
    with pytest.raises(ValueError, match="outside the output folder"):
        write_project(defn, out, "P")
    assert stale.exists() and not (tmp_path / "escaped.tmdl").exists()

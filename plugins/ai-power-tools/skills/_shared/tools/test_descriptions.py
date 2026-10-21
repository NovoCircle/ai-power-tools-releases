#!/usr/bin/env python3
"""Tests for the descriptions on the generated Power BI model, and the size line.

    python -m pytest plugins/ai-power-tools/skills/_shared/tools/test_descriptions.py -q

Hermetic: nothing here touches a database, Power BI or the network. The template texts
are asserted verbatim: they are the texts approved in the design (Westbrook Bank is the
fictitious example the fixture describes).
"""
from __future__ import annotations

# 0567: descriptions from three layers. 0541 (narrowed): the size line and its warning.
PINS = ("APT-2026-0567", "APT-2026-0541")

import copy
import json
import re
from pathlib import Path

import pytest

import descriptions
import parquet_tables
import powerbi_model
from powerbi_model import (model_from_definition, model_size, project_files_from_definition,
                           size_lines)
from semantic_model import SemanticColumn, SemanticModel, SemanticTable

FIXTURE = Path(__file__).parent / "fixtures" / "westbrook.definition.json"
BA = "Business Application"
GATEWAY_USES = "Con_AI Gateway Uses AI Service"


@pytest.fixture(scope="module")
def defn():
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def model(defn):
    return model_from_definition(defn)


def physical(defn):
    return {p["name"] for p in defn["physical"]}


def with_file(defn, entries):
    return model_from_definition(copy.deepcopy(defn), descriptions=entries)


def table_file(files, table):
    return files[f"P.SemanticModel/definition/tables/{table}.tmdl"]


# ------------------------------------------------------------ every object


def test_every_business_table_column_and_measure_has_a_description(defn, model):
    phys = physical(defn)
    business = [t for t in model.tables if t.name not in phys]
    assert len(business) == len(descriptions.business_kinds(defn))
    for t in business:
        assert t.description.strip(), t.name
        for c in t.columns:
            assert c.description.strip(), (t.name, c.name)
        for m in t.measures:
            assert m.description.strip(), (t.name, m.name)


def test_physical_tables_and_their_columns_have_none(defn, model):
    for name in physical(defn):
        t = model.table(name)
        assert t.description == "" and not any(c.description for c in t.columns), name


def test_physical_tables_carry_no_description_line_in_the_tmdl(defn):
    files = project_files_from_definition(defn, "P")
    for name in physical(defn):
        assert "///" not in table_file(files, name), name


# ------------------------------------------------------- the template texts


def test_entity_texts_are_the_approved_ones(model):
    t = model.table(BA)
    assert t.description == ("Business Application elements from the EA repository "
                             "(WestbrookBankArchitecture technology), one row per element.")
    cols = {c.name: c.description for c in t.columns}
    assert cols == {
        "ea_guid": "Unique key of the element. Hidden; relates the tables.",
        "name": "The element's name.",
        "metaclass": "The UML type the element is built on.",
        "package_path": "Where the element sits in the repository's package tree, from the root.",
        **{tag: f"The {tag} tagged value of each Business Application." for tag in
           ("businessOwner", "criticality", "dataClassification", "lifecycle",
            "pciScopeJustification", "regulatoryScope", "technicalOwner")}}
    assert [(m.name, m.description) for m in t.measures] == [
        ("Business Application count", "Number of Business Application elements.")]


def test_connector_texts_are_the_approved_ones(model):
    t = model.table(GATEWAY_USES)
    assert t.description == "Uses connections from AI Gateway to AI Service, one row per connection."
    assert {c.name: c.description for c in t.columns} == {
        "connector_guid": "Unique key of the connection. Hidden.",
        "connector_id": "EA's numeric id of the connection. Hidden.",
        "name": "The connection's name, often empty.",
        "source_guid": "Key of the AI Gateway at the start of the connection. Hidden.",
        "target_guid": "Key of the AI Service at the end of the connection. Hidden.",
        "direction": "The connection's direction as recorded in EA.",
        "base_type": "The UML connector type the connection is built on.",
        "dataFlowClassification": "The dataFlowClassification tagged value of each connection.",
        "integrationPattern": "The integrationPattern tagged value of each connection.",
        "slaTier": "The slaTier tagged value of each connection."}


def test_table_directory_texts_are_the_approved_ones(model):
    t = model.table("Table Directory")
    assert t.description == ("One row per table in this model: what it holds and which part "
                             "of the technology it comes from.")
    assert {c.name: c.description for c in t.columns} == descriptions.DIRECTORY_COLUMNS
    assert descriptions.DIRECTORY_COLUMNS["in_mdg"] == (
        "yes if the technology defines it, no if it was found in the repository.")


def test_a_not_in_mdg_entity_without_a_note_gets_its_template(defn):
    d = copy.deepcopy(defn)
    name = "VendorApplication (not in MDG)"
    for e in d["directory"]["entries"]:
        if e["table_name"] == name:
            e["description"] = None
    t = model_from_definition(d).table(name)
    assert t.description == (
        "VendorApplication (not in MDG) elements found in the repository but not defined by "
        "the WestbrookBankArchitecture technology (included as observed), one row per element.")


def test_a_connector_key_without_a_profile_uses_its_whole_key(defn, model):
    name = "Con_Data Entity Association Data Entity (not in MDG)"
    d = copy.deepcopy(defn)
    for e in d["directory"]["entries"]:
        if e["table_name"] == name:
            e["description"] = None
    assert model_from_definition(d).table(name).description == (
        "Association connections from Data Entity to Data Entity, one row per connection.")


def tag_row_defn(defn, note=None):
    d = copy.deepcopy(defn)
    ent = next(e for e in d["entities"] if e["name"] == BA)
    ent["row_tags"] = ["hostingRegion", "supportTeam"]
    d["tag_row_tables"] = [{"name": f"{BA} tags", "of": BA, "rows": 0, "all_columns": [
        {"name": n, "type": t} for n, t in (("ea_guid", "TEXT"), ("tag", "TEXT"),
                                            ("value", "TEXT"), ("property_id", "INTEGER"))]}]
    d["directory"]["entries"].append({"table_name": f"{BA} tags", "kind": "element tag rows",
                                      "description": note})
    return d


def test_a_tag_row_table_without_a_note_gets_its_template(defn):
    t = model_from_definition(tag_row_defn(defn)).table(f"{BA} tags")
    assert t.description == ("One row per value of the multi-valued tagged values "
                             "(hostingRegion, supportTeam) of each Business Application.")
    assert {c.name: c.description for c in t.columns} == {
        "ea_guid": "Unique key of the element. Hidden; relates the tables.",
        "tag": "Name of the tagged value.",
        "value": "The tagged value.",
        "property_id": "EA's id of the tagged-value row. Hidden."}
    assert not t.measures


def test_userelationship_measures_keep_their_text(model):
    measures = [m for t in model.tables if t.name.startswith("Con_") for m in t.measures]
    assert measures
    for m in measures:
        assert re.fullmatch(r"Rows of Con_.+ whose (source|target) is the selected .+\. "
                            r"Uses the inactive relationship\.", m.description), m.description


def test_templates_fit_the_file_limit_on_the_fixture(model, defn):
    phys = physical(defn)
    for t in model.tables:
        if t.name not in phys:
            for text in [t.description] + [c.description for c in t.columns]:
                assert len(text) <= descriptions.MAX_LENGTH, (t.name, text)


# --------------------------------------------------------------- layering


def test_a_technology_note_beats_a_template_and_is_not_edited(defn):
    d = copy.deepcopy(defn)
    note = "Applications the bank runs. " * 12  # 336 characters: a note is never truncated
    for e in d["directory"]["entries"]:
        if e["table_name"] == BA:
            e["description"] = note
    col = next(c for c in next(e for e in d["entities"] if e["name"] == BA)["all_columns"]
               if c["name"] == "lifecycle")
    col["description"] = "Lifecycle per the architecture standard."
    t = model_from_definition(d).table(BA)
    assert t.description == note
    assert {c.name: c.description for c in t.columns}["lifecycle"] == (
        "Lifecycle per the architecture standard.")
    assert {c.name: c.description for c in t.columns}["criticality"] == (
        "The criticality tagged value of each Business Application.")


@pytest.mark.parametrize("blank", ["", "   ", "\t\r\n"])
def test_an_empty_or_whitespace_note_counts_as_absent(defn, blank):
    d = copy.deepcopy(defn)
    for e in d["directory"]["entries"]:
        if e["table_name"] == BA:
            e["description"] = blank
    col = next(c for c in next(e for e in d["entities"] if e["name"] == BA)["all_columns"]
               if c["name"] == "lifecycle")
    col["description"] = blank
    t = model_from_definition(d).table(BA)
    assert t.description == ("Business Application elements from the EA repository "
                             "(WestbrookBankArchitecture technology), one row per element.")
    assert {c.name: c.description for c in t.columns}["lifecycle"] == (
        "The lifecycle tagged value of each Business Application.")


def test_the_directory_note_beats_the_not_in_mdg_template(defn, model):
    assert model.table("VendorApplication (not in MDG)").description == (
        "Included as observed: outside the MDG.")


def test_the_file_beats_a_note_and_a_template(defn):
    d = tag_row_defn(defn, note="Tags on these elements that are not columns: hostingRegion")
    d["entities"][3]["all_columns"][7]["description"] = "A note from the technology."
    assert d["entities"][3]["name"] == BA and d["entities"][3]["all_columns"][7]["name"] == "lifecycle"
    gw = next(m.name for m in model_from_definition(d).table(
        "Con_Business Application Flows Business Application").measures)
    entries = {"tables": {
        BA: {"description": "Every application the bank runs.",
             "columns": {"lifecycle": "Lifecycle stage: Strategic, Current, Deprecated, Sunset or "
                                      "Archive. Applications being retired are those in Sunset or "
                                      "Archive.",
                         "name": "The application's name."},
             "measures": {"Business Application count": "How many applications there are."}},
        f"{BA} tags": {"description": "Extra tags."},
        "Con_Business Application Flows Business Application": {"measures": {gw: "Flows by end."}}}}
    m = model_from_definition(d, descriptions=entries)
    t = m.table(BA)
    cols = {c.name: c.description for c in t.columns}
    assert t.description == "Every application the bank runs."
    assert cols["lifecycle"].startswith("Lifecycle stage:")
    assert cols["name"] == "The application's name."
    assert cols["criticality"] == "The criticality tagged value of each Business Application."
    assert t.measures[0].description == "How many applications there are."
    assert m.table(f"{BA} tags").description == "Extra tags."
    flows = m.table("Con_Business Application Flows Business Application")
    assert [x.description for x in flows.measures if x.name == gw] == ["Flows by end."]


def test_without_a_file_the_model_is_the_same_as_an_empty_one(defn):
    a = project_files_from_definition(defn, "P")
    assert a == project_files_from_definition(defn, "P", descriptions={})
    assert a == project_files_from_definition(defn, "P", descriptions={"tables": {}})


# -------------------------------------------------------------- refusals


@pytest.mark.parametrize("entries, named", [
    ({"tables": {"Business Applications": {"description": "x"}}}, "'Business Applications'"),
    ({"tables": {"t_object": {"description": "x"}}}, "'t_object'"),
    ({"tables": {BA: {"columns": {"lifecycle_stage": "x"}}}}, "'lifecycle_stage'"),
    ({"tables": {BA: {"measures": {"Business Application total": "x"}}}},
     "'Business Application total'"),
])
def test_a_name_the_model_does_not_have_is_refused_naming_it(defn, entries, named):
    with pytest.raises(ValueError, match=re.escape(named)):
        with_file(defn, entries)


@pytest.mark.parametrize("where", ["table", "column", "measure"])
def test_an_entry_over_250_characters_is_refused_with_its_length(defn, where):
    long = "x" * 251
    body = {"table": {"description": long}, "column": {"columns": {"lifecycle": long}},
            "measure": {"measures": {"Business Application count": long}}}[where]
    with pytest.raises(ValueError, match=r"251 characters; the limit is 250") as err:
        with_file(defn, {"tables": {BA: body}})
    assert BA in str(err.value)


def test_an_entry_of_exactly_250_characters_is_accepted(defn):
    text = "y" * 250
    m = with_file(defn, {"tables": {BA: {"columns": {"lifecycle": text}}}})
    assert {c.name: c.description for c in m.table(BA).columns}["lifecycle"] == text


@pytest.mark.parametrize("entries", [
    {"table": {}},
    {"tables": []},
    {"tables": {BA: {"descriptions": "x"}}},
    {"tables": {BA: {"columns": ["lifecycle"]}}},
    {"tables": {BA: {"description": ""}}},
    {"tables": {BA: {"description": 5}}},
])
def test_a_malformed_file_is_refused(defn, entries):
    with pytest.raises(ValueError):
        with_file(defn, entries)


# ------------------------------------------------------------------ TMDL


def test_quotes_and_line_breaks_in_a_file_entry_render_as_one_description_line(defn):
    text = 'Stage: "Sunset" or \'Archive\'\nmeans being retired. /// not a new line'
    files = project_files_from_definition(
        defn, "P", descriptions={"tables": {BA: {"columns": {"lifecycle": text}}}})
    body = table_file(files, BA)
    want = ("\t/// Stage: \"Sunset\" or 'Archive' means being retired. /// not a new line\r\n"
            "\tcolumn lifecycle\r\n")
    assert want in body


def test_every_business_object_is_preceded_by_a_description_line(defn):
    files = project_files_from_definition(defn, "P")
    lines = table_file(files, BA).split("\r\n")
    for i, line in enumerate(lines):
        if re.match(r"^(table |\tcolumn |\tmeasure )", line):
            assert lines[i - 1].lstrip("\t").startswith("/// "), line


# ------------------------------------------------------------------- CLI


def write_inputs(defn, tmp_path, entries):
    (tmp_path / "d.json").write_text(json.dumps(defn), encoding="utf-8")
    (tmp_path / "desc.json").write_text(json.dumps(entries), encoding="utf-8")
    return str(tmp_path / "d.json"), str(tmp_path / "desc.json")


def test_the_cli_option_round_trips_into_the_tmdl(defn, tmp_path, capsys):
    entries = {"tables": {BA: {"columns": {"lifecycle": "Sunset or Archive means being retired."}}}}
    d, f = write_inputs(defn, tmp_path, entries)
    assert powerbi_model.main([d, str(tmp_path / "out"), "--name", "WB", "--descriptions", f]) == 0
    text = (tmp_path / "out" / "WB.SemanticModel" / "definition" / "tables"
            / f"{BA}.tmdl").read_bytes().decode("utf-8")
    assert "\t/// Sunset or Archive means being retired.\r\n\tcolumn lifecycle\r\n" in text
    assert "tables + columns: full model" in capsys.readouterr().out


def test_the_cli_refuses_an_unknown_name_in_the_file(defn, tmp_path):
    d, f = write_inputs(defn, tmp_path, {"tables": {"No Such Table": {"description": "x"}}})
    with pytest.raises(ValueError, match="No Such Table"):
        powerbi_model.main([d, str(tmp_path / "out"), "--name", "WB", "--descriptions", f])
    assert not (tmp_path / "out").exists()


@pytest.mark.skipif(not parquet_tables.PYARROW_AVAILABLE, reason="pyarrow is not installed")
def test_path_c_passes_the_option_through(defn, tmp_path):
    folder = tmp_path / "out" / "parquet"
    d = copy.deepcopy(defn)
    d["source"] = {"kind": "parquet", "folder": str(folder), "schema": "logical",
                   "physical_schema": "dbo"}
    rows = {s["name"]: [] for s in powerbi_model._business_specs(d) + list(d["physical"])}
    (tmp_path / "t.json").write_text(json.dumps(rows), encoding="utf-8")
    dp, f = write_inputs(d, tmp_path, {"tables": {BA: {"description": "All applications."}}})
    assert parquet_tables.main([dp, str(tmp_path / "t.json"), "--project-name", "WB",
                                "--descriptions", f]) == 0
    text = (tmp_path / "out" / "WB.SemanticModel" / "definition" / "tables"
            / f"{BA}.tmdl").read_bytes().decode("utf-8")
    assert text.startswith("/// All applications.\r\ntable 'Business Application'")


# ------------------------------------------------------------------- size


def tiny_model():
    return SemanticModel(tables=[
        SemanticTable("A", columns=[SemanticColumn("k", is_hidden=True), SemanticColumn("x")]),
        SemanticTable("B", columns=[SemanticColumn("y"), SemanticColumn("z")]),
        SemanticTable("t_hidden", is_hidden=True, columns=[SemanticColumn("p"), SemanticColumn("q")])])


def test_size_counts_tables_plus_columns_for_the_full_model_and_the_visible_layer():
    # Full: 3 tables + 6 columns. Business: A + x, B + y + z.
    assert model_size(tiny_model()) == (9, 5)


def test_size_of_the_westbrook_fixture(model):
    # 51 tables (42 business, 9 of EA's) and 669 columns; 42 visible tables and 296
    # visible columns once the key columns are hidden.
    assert model_size(model) == (720, 338)


def test_the_size_line_and_no_warning_at_the_limit():
    assert size_lines(1000, 281) == [
        "tables + columns: full model 1000 (hidden included), business layer 281 (visible only)"]


def test_a_warning_for_each_count_past_the_limit():
    lines = size_lines(1001, 1200)
    assert lines[0] == ("tables + columns: full model 1001 (hidden included), "
                        "business layer 1200 (visible only)")
    assert lines[1].startswith("warning: the full model has 1,001 tables + columns, more than the 1,000")
    assert lines[2].startswith("warning: the business layer has 1,200 tables + columns")
    assert len(size_lines(1001, 10)) == 2


def test_the_cli_prints_the_size_line(defn, tmp_path, capsys):
    (tmp_path / "d.json").write_text(json.dumps(defn), encoding="utf-8")
    assert powerbi_model.main([str(tmp_path / "d.json"), str(tmp_path / "o"), "--name", "WB"]) == 0
    out = capsys.readouterr().out.splitlines()
    assert ("tables + columns: full model 720 (hidden included), "
            "business layer 338 (visible only)") in out
    assert not any(line.startswith("warning:") for line in out)

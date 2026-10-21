#!/usr/bin/env python3
"""The Power BI generator over a definition with tag-row tables, for both source kinds.

    python -m pytest plugins/ai-power-tools/skills/_shared/tools/test_powerbi_model_sources.py -q

The shipped Westbrook fixture has no tag-row tables and is a SQL source, so the checks that
`test_powerbi_model.py` makes against it never see a tag-row table's `property_id` or
`connector_id`, and never see a Parquet source. This module runs the generator over a copy of the
fixture, modified in memory, with one tag-row table on an entity and one on a connector, once as
the import (SQL) source the fixture is and once as a Parquet source with a folder, and asserts on
both:

* a count measure exists on every entity table and on no other table;
* the six key columns are hidden on business tables and on nothing else;
* every business table, column and measure has a description, and no physical table, column or
  measure has one.

Hermetic: nothing here touches a database, Power BI or the network.
"""
from __future__ import annotations

# 0540: the six key columns hidden. 0544: count measures on entity tables. 0567: descriptions.
PINS = ("APT-2026-0540", "APT-2026-0544", "APT-2026-0567")

# The generator's own unit; its main test module is test_powerbi_model.py.
COVERS = ("prog:_shared/tools/powerbi_model.py",)

import copy
import json
from pathlib import Path

import pytest

from powerbi_model import model_from_definition, project_files_from_definition

FIXTURE = Path(__file__).parent / "fixtures" / "westbrook.definition.json"
KEYS = {"ea_guid", "source_guid", "target_guid", "connector_guid", "connector_id", "property_id"}


def _definition(kind: str, folder: Path) -> dict:
    """A copy of the Westbrook definition with tag-row tables added and `source` set for `kind`."""
    d = copy.deepcopy(json.loads(FIXTURE.read_text(encoding="utf-8")))
    ent, con = d["entities"][0]["name"], d["connectors"][0]["name"]
    d["tag_row_tables"] = [
        {"name": f"{ent} tags", "of": ent, "rows": 0,
         "all_columns": [{"name": "ea_guid", "type": "TEXT"}, {"name": "tag", "type": "TEXT"},
                         {"name": "value", "type": "TEXT"}, {"name": "property_id", "type": "INTEGER"}]},
        {"name": f"{con} tags", "of": con, "rows": 0,
         "all_columns": [{"name": "connector_guid", "type": "TEXT"}, {"name": "tag", "type": "TEXT"},
                         {"name": "value", "type": "TEXT"}, {"name": "property_id", "type": "INTEGER"}]},
    ]
    if kind == "parquet":
        d["source"] = {"kind": "parquet", "folder": str(folder)}
    return d


@pytest.fixture(params=["import", "parquet"])
def built(request, tmp_path):
    defn = _definition(request.param, tmp_path)
    return request.param, defn, model_from_definition(defn)


def _business(defn):
    return ([e["name"] for e in defn["entities"]] + [c["name"] for c in defn["connectors"]]
            + [t["name"] for t in defn["tag_row_tables"]] + [defn["directory"]["name"]])


def test_the_added_tables_are_in_the_model_and_the_source_is_the_one_asked_for(built):
    kind, defn, model = built
    names = {t.name for t in model.tables}
    assert {t["name"] for t in defn["tag_row_tables"]} <= names
    assert len(defn["tag_row_tables"]) == 2
    if kind == "parquet":
        assert all(t.source_name == t.name for t in model.tables)   # no schema prefix
    else:
        assert any("." in t.source_name for t in model.tables)


def test_count_measures_are_on_entity_tables_only(built):
    _, defn, model = built
    entities = {e["name"] for e in defn["entities"]}
    for t in model.tables:
        counts = [m for m in t.measures if m.name == f"{t.name} count"]
        if t.name in entities:
            assert len(counts) == 1, t.name
            assert counts[0].expression == f"COUNTROWS('{t.name}')"
        else:
            assert counts == [], t.name
    # no measure on a tag-row table, a connector table's only measures are the inactive-relationship ones
    for tag_table in defn["tag_row_tables"]:
        assert model.table(tag_table["name"]).measures == []
    assert not any(m.name.endswith(" count") for t in model.tables
                   if t.name not in entities for m in t.measures)


def test_the_six_keys_are_hidden_on_business_tables_only(built):
    _, defn, model = built
    business = set(_business(defn))
    seen = set()
    for t in model.tables:
        if t.name in business:
            for c in t.columns:
                assert c.is_hidden == (c.name in KEYS), (t.name, c.name)
                if c.is_hidden:
                    seen.add(c.name)
        else:
            assert t.is_hidden and not any(c.is_hidden for c in t.columns), t.name
    # property_id exists only on the tag-row tables added here, connector_id on every connector table
    assert seen == KEYS
    for tag_table in defn["tag_row_tables"]:
        assert next(c for c in model.table(tag_table["name"]).columns
                    if c.name == "property_id").is_hidden


def test_every_business_table_column_and_measure_has_a_description(built):
    _, defn, model = built
    business = set(_business(defn))
    for t in model.tables:
        if t.name in business:
            assert t.description.strip(), t.name
            for c in t.columns:
                assert c.description.strip(), (t.name, c.name)
            for m in t.measures:
                assert m.description.strip(), (t.name, m.name)


def test_no_physical_table_column_or_measure_has_a_description(built):
    _, defn, model = built
    business = set(_business(defn))
    physical = [t for t in model.tables if t.name not in business]
    assert len(physical) == len(defn["physical"]) == 9
    for t in physical:
        assert t.description == "", t.name
        assert all(c.description == "" for c in t.columns), t.name
        assert t.measures == [], t.name


def test_the_project_is_written_for_the_source_kind(built):
    kind, defn, _ = built
    files = project_files_from_definition(defn, "P")
    biz = files["P.SemanticModel/definition/tables/Business Application.tmdl"]
    phys = files["P.SemanticModel/definition/tables/t_object.tmdl"]
    if kind == "parquet":
        assert "Parquet" in biz and "Parquet" in phys
    else:
        assert "Sql.Database" in biz and "Sql.Database" in phys
    # a description reaches the file for a business table and never for a physical one
    assert "///" in biz and "///" not in phys

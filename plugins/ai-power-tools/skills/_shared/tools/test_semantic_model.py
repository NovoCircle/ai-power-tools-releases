#!/usr/bin/env python3
"""Tests for the semantic-model data structures.

    python -m pytest _shared/tools/test_semantic_model.py -q

The model is built from the business-layer definition by `powerbi_model.py`
and tested there; this file covers the structures themselves.
"""
from __future__ import annotations

import json

import semantic_model
from semantic_model import (Measure, Relationship, SemanticColumn, SemanticModel,
                            SemanticTable, _rel_name)


def test_a_column_reads_from_the_source_column_of_the_same_name_by_default():
    assert SemanticColumn("name").source_column == "name"
    assert SemanticColumn("name", source_column="Name").source_column == "Name"


def test_a_table_is_sourced_by_its_own_name_unless_told_otherwise():
    assert SemanticTable("Business Application").source_name == "Business Application"
    assert SemanticTable("a", source_name="logical.a").source_name == "logical.a"


def test_nothing_summarizes_by_default():
    assert SemanticColumn("n", "int64").summarize_by == "none"


def test_the_model_carries_no_hub():
    """The `_keymap` hub failed acceptance and is retired (`APT-2026-0309`)."""
    assert not hasattr(SemanticModel(), "hub")
    assert not hasattr(SemanticModel(), "measure_host")
    for retired in ("HUB", "DEFAULT_MEASURE_HOST", "build_semantic_model", "traversal_measures"):
        assert not hasattr(semantic_model, retired)


def test_a_table_is_found_by_its_model_name():
    sm = SemanticModel(tables=[SemanticTable("a"), SemanticTable("b")])
    assert sm.table("b").name == "b"
    assert sm.table("c") is None


def test_inactive_lists_only_the_inactive_relationships():
    on = Relationship("r1", "a", "x", "b", "y")
    off = Relationship("r2", "a", "z", "b", "y", is_active=False)
    assert SemanticModel(relationships=[on, off]).inactive == [off]


def test_a_relationship_is_many_to_one_and_automatic_by_default():
    r = Relationship("r", "a", "x", "b", "y")
    assert (r.from_cardinality, r.cross_filtering, r.is_active) == ("many", "automatic", True)


def test_a_relationship_name_includes_the_source_column():
    """A connector table relates to the same entity table twice, once on its
    source and once on its target; the two names must differ."""
    assert _rel_name("Con_a Uses b", "source_guid", "a") != _rel_name("Con_a Uses b", "target_guid", "a")


def test_a_relationship_name_is_deterministic_and_plain():
    name = _rel_name("Con_a Uses b", "source_guid", "a")
    assert name == _rel_name("Con_a Uses b", "source_guid", "a")
    assert name == "gen_con_a_uses_b_source_guid_to_a"


def test_the_model_is_plain_serializable_data():
    sm = SemanticModel(
        tables=[SemanticTable("a", columns=[SemanticColumn("c")],
                              measures=[Measure("m", "COUNTROWS('a')")])],
        relationships=[Relationship("r", "a", "c", "a", "c")])
    assert json.loads(json.dumps(sm.to_dict()))["tables"][0]["measures"][0]["name"] == "m"

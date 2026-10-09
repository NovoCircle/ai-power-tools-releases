#!/usr/bin/env python3
"""Tests for the inclusion choice.

Run from the repository root:

    python -m pytest plugins/ai-power-tools/skills/_shared/tools/test_inclusion.py -q

Hermetic: plain rows in, plain data out. The fixture is Westbrook Bank-shaped;
every `@STEREO` string has the form measured against a live repository.
"""
from __future__ import annotations

import json

import pytest

from ea_census import build_stereotype_index, census_connectors, census_elements
from inclusion import (
    ALL,
    CONNECTOR,
    ELEMENT,
    EXCLUDE,
    INCLUDE,
    MDG_STEREOTYPE_ADDED,
    MDG_STEREOTYPE_REMOVED,
    MDG_VERSION_CHANGED,
    NEW_CONNECTOR_KEY,
    NEW_ELEMENT_KEY,
    UNDECIDED,
    UPDATE_MDG,
    InclusionError,
    analyze,
    new_since_saved,
    resolve_answer,
)

NS = "WestbrookBankArchitecture"

MDG = {
    "version": "1.1.1",
    "stereotypes": [
        {"name": "WBABusinessApplication", "base_metaclass": "Component", "tagged_values": []},
        {"name": "WBASystemOfRecord", "base_metaclass": "Component", "tagged_values": []},
        {"name": "WBADataAsset", "base_metaclass": "Class", "tagged_values": []},
        {"name": "Uses", "base_metaclass": "Association", "tagged_values": []},
        {"name": "Flows", "base_metaclass": "InformationFlow", "tagged_values": []},
    ],
}


def xref(guid, *blocks):
    """A t_xref row. Each block is (name, fqname)."""
    desc = "".join("@STEREO;Name=%s;GUID={s};%s@ENDSTEREO;" % (n, ("FQName=%s;" % fq) if fq else "")
                   for n, fq in blocks)
    return {"Client": guid, "Description": desc}


def el(guid, name, metaclass, stereotype=""):
    return {"ea_guid": guid, "Name": name, "Object_Type": metaclass, "Stereotype": stereotype}


def cn(guid, name, ctype, stereotype=""):
    return {"ea_guid": guid, "Name": name, "Connector_Type": ctype, "Stereotype": stereotype}


OBJECTS = [
    el("{e1}", "Retail Banking Core", "Component", "WBABusinessApplication"),
    el("{e2}", "Online Banking", "Component", "WBABusinessApplication"),
    el("{e3}", "Customer Ledger", "Class", "WBADataAsset"),
    el("{e4}", "Clearing House Feed", "Component", "VendorApplication"),
    el("{e5}", "Payments Hub", "Component", "VendorApplication"),
    el("{e6}", "Grow Deposits", "Class", "Goal"),
    el("{e7}", "Audit Trail", "Requirement"),
    el("{e8}", "Retention Rule", "Requirement"),
    el("{e9}", "Scratch note", "Note"),
]
XREF = [
    xref("{e1}", ("WBABusinessApplication", NS + "::WBABusinessApplication")),
    xref("{e2}", ("WBABusinessApplication", NS + "::WBABusinessApplication")),
    xref("{e3}", ("WBADataAsset", NS + "::WBADataAsset")),
    xref("{e4}", ("VendorApplication", "")),
    xref("{e5}", ("VendorApplication", "")),
    xref("{e6}", ("Goal", "BMM::Goal")),
]
CONNECTORS = [
    cn("{c1}", "feeds", "Association", "Uses"),
    cn("{c2}", "calls", "Association", "Uses"),
    cn("{c3}", "typed by hand", "Association", "Uses"),
    cn("{c4}", "extends one", "Dependency", "extends"),
    cn("{c5}", "extends two", "Dependency", "extends"),
    cn("{c6}", "influences", "Association", "Influences"),
    cn("{c7}", "plain a", "Association"),
    cn("{c8}", "plain b", "Association"),
    cn("{c9}", "plain c", "Dependency"),
]
CXREF = [
    xref("{c1}", ("Uses", NS + "::Uses")),
    xref("{c2}", ("Uses", NS + "::Uses")),
    xref("{c3}", ("Uses", "")),
    xref("{c4}", ("extends", "")),
    xref("{c5}", ("extends", "")),
    xref("{c6}", ("Influences", "BMM::Influences")),
]


def run(objects=OBJECTS, xrefs=XREF, connectors=CONNECTORS, cxrefs=CXREF, mdg=MDG):
    idx = build_stereotype_index(list(xrefs) + list(cxrefs))
    return analyze(census_elements(objects, idx), census_connectors(connectors, idx), mdg,
                   objects, connectors, namespace=NS)


def gap(a, kind, key):
    return next(g for g in a.gaps if g.kind == kind and g.key == key)


# ---------------------------------------------------------------- counts

def test_option_1_counts_only_what_the_mdg_declares():
    c = run().options()[1]
    assert (c.declared_element_keys, c.observed_element_keys, c.elements) == (2, 0, 3)
    assert (c.declared_connector_keys, c.observed_connector_keys, c.connectors) == (1, 0, 2)


def test_option_2_counts_every_key_in_the_repository():
    c = run().options()[2]
    assert (c.declared_element_keys, c.observed_element_keys) == (2, 3)
    assert c.elements == 8   # nine rows, minus the Note: diagram furniture, never a table
    assert (c.declared_connector_keys, c.observed_connector_keys) == (1, 5)
    assert c.connectors == 9


def test_a_note_without_a_stereotype_is_not_offered_as_a_gap():
    assert not [g for g in run().element_gaps if g.metaclass == "Note"]


def test_option_3_is_what_lies_between_the_other_two():
    a = run()
    lo, hi = a.options()[1], a.options()[2]
    assert lo.elements + sum(g.count for g in a.element_gaps) == hi.elements
    assert lo.connectors + sum(g.count for g in a.connector_gaps) == hi.connectors


# ---------------------------------------------------------------- gaps

def test_element_gap_keys_are_what_the_server_keys_on():
    a = run()
    ad_hoc = gap(a, ELEMENT, "VendorApplication|Component")
    assert (ad_hoc.stereotype, ad_hoc.metaclass, ad_hoc.bound, ad_hoc.count) == ("VendorApplication", "Component", False, 2)
    foreign = gap(a, ELEMENT, "BMM::Goal")
    assert (foreign.stereotype, foreign.metaclass, foreign.bound) == ("BMM::Goal", "Class", True)
    unstereotyped = gap(a, ELEMENT, "|Requirement")
    assert (unstereotyped.stereotype, unstereotyped.metaclass, unstereotyped.count) == ("", "Requirement", 2)


def test_a_declared_name_carried_ad_hoc_is_a_gap_not_the_declared_stereotype():
    objects = OBJECTS + [el("{e10}", "Loose Ledger", "Class", "WBADataAsset")]
    xrefs = XREF + [xref("{e10}", ("WBADataAsset", ""))]
    a = run(objects, xrefs)
    assert gap(a, ELEMENT, "WBADataAsset|Class").stereotype == "WBADataAsset"
    assert a.options()[1].elements == 3


def test_connector_gap_keys_ignore_the_base_type():
    """The server keys a connector by FQName, else stereotype text, else base type."""
    a = run()
    assert {g.key for g in a.connector_gaps} == {"Uses", "extends", "BMM::Influences", "Association", "Dependency"}
    assert gap(a, CONNECTOR, "Uses").count == 1      # the ad hoc Uses; the bound ones are the MDG's
    assert gap(a, CONNECTOR, "Association").count == 2
    assert gap(a, CONNECTOR, "BMM::Influences").bound is True


def test_one_stereotype_on_two_base_types_is_one_connector_key():
    cons = CONNECTORS + [cn("{c10}", "ad hoc association", "Association", "extends")]
    a = run(connectors=cons, cxrefs=CXREF + [xref("{c10}", ("extends", ""))])
    g = gap(a, CONNECTOR, "extends")
    assert g.count == 3 and g.metaclass == "Association/Dependency"


def test_each_gap_carries_a_count_and_an_example_name():
    g = gap(run(), ELEMENT, "VendorApplication|Component")
    assert g.example == "Clearing House Feed"
    assert gap(run(), CONNECTOR, "extends").example == "extends one"


# ---------------------------------------------------------------- defects

def unbound_fixture():
    cons = CONNECTORS + [cn("{c11}", "badly typed", "InformationFlow", "WBA::Flows")]
    return run(connectors=cons, cxrefs=CXREF + [xref("{c11}", ("WBA::Flows", ""))])


def test_an_unbound_connector_is_a_defect_with_a_fix_not_a_gap():
    a = unbound_fixture()
    assert a.blocked
    d = a.unbound_connectors[0]
    assert (d.subject, d.count, d.guids) == ("WBA::Flows", 1, ("{c11}",))
    assert f"{NS}::Flows" in d.advice and "baseline" in d.advice
    assert not [g for g in a.gaps if "WBA::Flows" in g.key]
    assert a.options()[2].connectors == 9   # not counted until it is fixed


def test_an_unbound_name_the_mdg_does_not_declare_gets_the_clear_or_declare_advice():
    cons = [cn("{c1}", "x", "Association", "WBA::Unknown")]
    a = run(connectors=cons, cxrefs=[xref("{c1}", ("WBA::Unknown", ""))])
    assert "declares no connector stereotype" in a.unbound_connectors[0].advice


def test_no_profile_while_a_connector_is_unbound():
    for option in (1, 2, 3):
        with pytest.raises(InclusionError, match="WBA::Flows"):
            resolve_answer(unbound_fixture(), option, {})


def double_fixture():
    objects = OBJECTS + [el("{e10}", "Core Ledger", "Component", "WBABusinessApplication")]
    xrefs = XREF + [xref("{e10}", ("WBABusinessApplication", NS + "::WBABusinessApplication"),
                         ("WBASystemOfRecord", NS + "::WBASystemOfRecord"))]
    return run(objects, xrefs)


def test_an_element_with_two_declared_stereotypes_is_flagged_not_a_gap():
    a = double_fixture()
    assert a.doubly_stereotyped_elements == 1
    assert a.multi_stereotyped[0].guids == ("{e10}",)
    assert not [g for g in a.gaps if "{e10}" in g.key]


def test_continuing_past_a_double_stereotype_places_it_in_both_tables():
    a = double_fixture()
    with pytest.raises(InclusionError, match="two declared stereotypes"):
        resolve_answer(a, 1)
    answer = resolve_answer(a, 1, continue_with_double_stereotypes=True)
    assert answer.coverage.declared_element_keys == 3
    assert answer.coverage.elements == 4          # one element, two tables, counted once


def test_a_benign_second_stereotype_from_another_language_is_not_flagged():
    objects = [el("{e1}", "Retail Banking Core", "Component", "WBABusinessApplication")]
    xrefs = [xref("{e1}", ("WBABusinessApplication", NS + "::WBABusinessApplication"), ("Goal", "BMM::Goal"))]
    assert not run(objects, xrefs, [], []).multi_stereotyped


# ---------------------------------------------------------------- the answer

def test_option_1_is_two_empty_lists():
    assert resolve_answer(run(), 1).inclusion == {"observed_elements": [], "observed_connectors": []}


def test_option_2_is_all_and_all():
    assert resolve_answer(run(), 2).inclusion == {"observed_elements": ALL, "observed_connectors": ALL}


def test_option_3_per_gap_include_and_exclude():
    a = run()
    decisions = {g.id: EXCLUDE for g in a.gaps}
    decisions["element:VendorApplication|Component"] = INCLUDE
    decisions["element:BMM::Goal"] = INCLUDE
    decisions["connector:BMM::Influences"] = INCLUDE
    decisions["connector:Uses"] = INCLUDE
    answer = resolve_answer(a, 3, decisions)
    assert answer.inclusion == {
        "observed_elements": [{"stereotype": "BMM::Goal", "metaclass": "Class"},
                              {"stereotype": "VendorApplication", "metaclass": "Component"}],
        "observed_connectors": ["BMM::Influences", "Uses"],
    }
    assert "element:|Requirement" in answer.excluded and "connector:extends" in answer.excluded
    assert answer.coverage.observed_element_keys == 2 and answer.coverage.observed_connector_keys == 2


def test_option_3_unstereotyped_is_an_empty_stereotype_entry():
    a = run()
    decisions = {g.id: EXCLUDE for g in a.gaps}
    decisions["element:|Requirement"] = INCLUDE
    assert {"stereotype": "", "metaclass": "Requirement"} in resolve_answer(a, 3, decisions).inclusion["observed_elements"]


@pytest.mark.parametrize("pending", [UNDECIDED, UPDATE_MDG, None])
def test_option_3_refuses_while_any_gap_is_undecided(pending):
    a = run()
    decisions = {g.id: INCLUDE for g in a.gaps}
    if pending is None:
        del decisions["connector:extends"]
    else:
        decisions["connector:extends"] = pending
    with pytest.raises(InclusionError, match="not decided") as exc:
        resolve_answer(a, 3, decisions)
    assert "connector:extends" in str(exc.value)


def test_update_the_mdg_is_a_hand_off_not_an_answer():
    with pytest.raises(InclusionError, match="hand-off to the MDG skills"):
        resolve_answer(run(), 3, {g.id: UPDATE_MDG for g in run().gaps})


def test_a_decision_for_something_that_is_not_a_gap_is_refused():
    a = run()
    decisions = {g.id: INCLUDE for g in a.gaps}
    decisions["element:WBABusinessApplication"] = INCLUDE
    with pytest.raises(InclusionError, match="not a gap"):
        resolve_answer(a, 3, decisions)


def test_an_unknown_decision_word_or_option_is_refused():
    a = run()
    with pytest.raises(InclusionError, match="decision must be"):
        resolve_answer(a, 3, {g.id: "maybe" for g in a.gaps})
    with pytest.raises(InclusionError, match="option must be"):
        resolve_answer(a, 4)


def test_the_inclusion_round_trips_through_json_and_matches_the_profile_shape():
    a = run()
    answer = resolve_answer(a, 3, {g.id: INCLUDE for g in a.gaps})
    section = json.loads(json.dumps(answer.inclusion))
    assert set(section) == {"observed_elements", "observed_connectors"}
    assert all(set(e) == {"stereotype", "metaclass"} for e in section["observed_elements"])
    assert answer.coverage == a.options()[2]      # including every gap is option 2's coverage


# ---------------------------------------------------------------- refresh

def saved(option, decisions=None, a=None):
    a = a or run()
    ans = resolve_answer(a, option, decisions or {})
    return ans.inclusion, ans.record()


def test_a_new_ad_hoc_connector_stereotype_is_flagged_on_refresh():
    a = run()
    inclusion, record = saved(3, {g.id: INCLUDE for g in a.gaps}, a)
    cons = CONNECTORS + [cn("{c20}", "late arrival", "Association", "supersedes")]
    fresh = run(connectors=cons, cxrefs=CXREF + [xref("{c20}", ("supersedes", ""))])
    found = new_since_saved(fresh, inclusion, record)
    assert [(i.kind, i.key, i.count, i.example) for i in found] == [(NEW_CONNECTOR_KEY, "supersedes", 1, "late arrival")]


def test_a_new_element_stereotype_is_flagged_on_refresh():
    a = run()
    inclusion, record = saved(3, {g.id: INCLUDE for g in a.gaps}, a)
    fresh = run(OBJECTS + [el("{e30}", "Wire Desk", "Component", "Gateway")], XREF + [xref("{e30}", ("Gateway", ""))])
    assert [(i.kind, i.key) for i in new_since_saved(fresh, inclusion, record)] == [(NEW_ELEMENT_KEY, "Gateway|Component")]


def test_an_excluded_gap_is_not_new_on_the_next_refresh():
    a = run()
    decisions = {g.id: EXCLUDE for g in a.gaps}
    inclusion, record = saved(3, decisions, a)
    assert new_since_saved(a, inclusion, record) == []


def test_the_same_census_finds_nothing_new():
    a = run()
    inclusion, record = saved(3, {g.id: INCLUDE for g in a.gaps}, a)
    assert new_since_saved(a, inclusion, record) == []


def test_option_1_and_option_2_choices_are_blanket_so_new_keys_are_not_flagged():
    cons = CONNECTORS + [cn("{c20}", "late arrival", "Association", "supersedes")]
    fresh = run(connectors=cons, cxrefs=CXREF + [xref("{c20}", ("supersedes", ""))])
    for option in (1, 2):
        inclusion, record = saved(option)
        assert new_since_saved(fresh, inclusion, record) == []


def test_without_a_record_a_profile_that_is_not_all_flags_every_unlisted_gap():
    a = run()
    assert len(new_since_saved(a, {"observed_elements": [], "observed_connectors": []})) == len(a.gaps)


def test_a_change_in_the_mdg_is_flagged_rather_than_decided():
    a = run()
    inclusion, record = saved(1, None, a)
    mdg = {"version": "1.2.0", "stereotypes": MDG["stereotypes"][:4]
           + [{"name": "WBAVendorSystem", "base_metaclass": "Component", "tagged_values": []}]}
    found = {(i.kind, i.key) for i in new_since_saved(run(mdg=mdg), inclusion, record)}
    assert found == {(MDG_STEREOTYPE_ADDED, "WBAVendorSystem"), (MDG_STEREOTYPE_REMOVED, "Flows"),
                     (MDG_VERSION_CHANGED, "1.2.0")}

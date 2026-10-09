#!/usr/bin/env python3
"""Tests for governance_gap.

Every test here is named for the mistake it catches. The 0210 lesson was that a
hermetic suite can pass four times over wrong code, so the cases that matter are
the ones asserting the module REFUSES to answer: a guess is the failure mode,
not an exception.
"""
from __future__ import annotations

import pytest

from ea_census import Shape
from governance_gap import (
    NO_CANDIDATE, RANKED, UNRANKABLE,
    assess, find_ungoverned, format_report, locality_votes, summarize,
)

COMMON = frozenset({"criticality", "lifecycle", "businessOwner",
                    "technicalOwner", "dataClassification", "regulatoryScope"})
AI_EXTRA = COMMON | {"modelGovernanceClass", "dataResidency",
                     "auditLoggingEnabled", "humanInLoopRequired"}

#: Modeled on the reference technology as of WBA 1.0, including the fact that most
#: declared stereotypes share one identical tag set - which is exactly why tag overlap
#: cannot rank them. (WBA 1.1.1 differs: `WBABusinessApplication` and `WBAVendorSystem`
#: declare extra tags, which changes the ranked case on the real model.)
DECLARED = {
    "WBABusinessApplication": Shape(metaclass="Component", tag_names=COMMON),
    "WBABusinessService": Shape(metaclass="Component", tag_names=COMMON),
    "WBAVendorSystem": Shape(metaclass="Component", tag_names=COMMON),
    "WBASystemOfRecord": Shape(metaclass="Component", tag_names=COMMON),
    "WBAAIGateway": Shape(metaclass="Component", tag_names=AI_EXTRA),
    "WBADataAsset": Shape(metaclass="Class", tag_names=COMMON),
    "WBARegulatedActivity": Shape(metaclass="Activity", tag_names=COMMON),
}


def el(guid, name, metaclass, package_id=1, stereotype=""):
    return {"ea_guid": guid, "name": name, "metaclass": metaclass,
            "stereotype": stereotype, "package_id": package_id}


def tags(guid, names, populated=True):
    return [{"ea_guid": guid, "tag": n, "value": "x" if populated else ""}
            for n in names]


# --- find_ungoverned ---------------------------------------------------

def test_a_stereotyped_element_is_not_a_gap():
    rows = [el("{A}", "Payments", "Component", stereotype="WBABusinessApplication")]
    assert find_ungoverned(rows, []) == []


def test_package_twins_are_skipped_because_the_package_tree_already_has_them():
    rows = [el("{P}", "Consumer Banking", "Package")]
    assert find_ungoverned(rows, []) == []


def test_an_untagged_unstereotyped_element_is_a_gap_but_not_governed():
    rows = [el("{A}", "Ledger Service", "Component")]
    found = find_ungoverned(rows, [])
    assert len(found) == 1
    assert found[0].is_governed is False


def test_populated_tags_make_it_governed_empty_ones_do_not():
    rows = [el("{A}", "Client Reporting", "Component")]
    governed = find_ungoverned(rows, tags("{A}", COMMON, populated=True))[0]
    empty = find_ungoverned(rows, tags("{A}", COMMON, populated=False))[0]
    assert governed.is_governed is True
    # EA creates a tag row when a stereotype is applied whether or not anyone
    # fills it in, so presence must not be mistaken for data.
    assert empty.is_governed is False
    assert empty.tag_names == COMMON


def test_governed_elements_sort_first():
    rows = [el("{A}", "Aaa Untagged", "Component"),
            el("{Z}", "Zzz Tagged", "Component")]
    found = find_ungoverned(rows, tags("{Z}", COMMON))
    assert [e.name for e in found] == ["Zzz Tagged", "Aaa Untagged"]


def test_ordering_is_deterministic():
    rows = [el("{C}", "C", "Component"), el("{A}", "A", "Component"),
            el("{B}", "B", "Component")]
    a = [e.ea_guid for e in find_ungoverned(rows, [])]
    b = [e.ea_guid for e in find_ungoverned(list(reversed(rows)), [])]
    assert a == b


# --- the three outcomes ------------------------------------------------

def test_a_metaclass_the_technology_does_not_extend_yields_no_candidate():
    """A metaclass the technology does not extend: the 10 Requirements on the reference
    model. (The 15 Nodes were this case until WBA 1.1.1.) A suggestion here would be invented."""
    rows = [el("{N}", "AWS Cloud Platform", "Node")]
    f = assess(find_ungoverned(rows, []), DECLARED, rows)[0]
    assert f.outcome == NO_CANDIDATE
    assert f.candidates == []
    assert f.suggestion == ""
    assert "extends no stereotype" in f.reason
    # and it must say what IS extended, so the reader can act
    assert "Component" in f.reason and "Activity" in f.reason


def test_sibling_evidence_produces_a_ranked_suggestion_with_its_basis():
    """The three real Components under WBA 1.0: three siblings in the package, all one stereotype."""
    rows = [el("{A}", "Portfolio Analytics Engine", "Component", package_id=7),
            el("{S1}", "Sib 1", "Component", package_id=7, stereotype="WBAVendorSystem"),
            el("{S2}", "Sib 2", "Component", package_id=7, stereotype="WBAVendorSystem"),
            el("{S3}", "Sib 3", "Component", package_id=7, stereotype="WBAVendorSystem")]
    f = assess(find_ungoverned(rows, tags("{A}", COMMON)), DECLARED, rows)[0]
    assert f.outcome == RANKED
    assert f.suggestion == "WBAVendorSystem"
    assert "same package" in f.reason


def test_identical_tag_sets_alone_cannot_rank_and_the_module_says_so():
    """Four Component stereotypes share one tag set. Picking one would be a guess."""
    rows = [el("{A}", "Fraud Screening", "Component", package_id=9)]
    f = assess(find_ungoverned(rows, tags("{A}", COMMON)), DECLARED, rows)[0]
    assert f.outcome == UNRANKABLE
    assert f.suggestion == ""
    assert len(f.candidates) >= 4
    assert "nothing in the repository" in f.reason


def test_no_tags_and_no_siblings_is_unrankable_not_a_guess():
    rows = [el("{A}", "Ledger Service", "Component", package_id=9)]
    f = assess(find_ungoverned(rows, []), DECLARED, rows)[0]
    assert f.outcome == UNRANKABLE
    assert "no tagged values" in f.reason


# --- the negative cases ------------------------------------------------

def test_a_sibling_of_a_different_metaclass_does_not_lend_its_stereotype():
    """The metaclass filter is hard. A Class stereotype cannot reach a Component."""
    rows = [el("{A}", "Thing", "Component", package_id=4),
            el("{S}", "Sib", "Class", package_id=4, stereotype="WBADataAsset")]
    f = assess(find_ungoverned(rows, tags("{A}", COMMON)), DECLARED, rows)[0]
    assert "WBADataAsset" not in [c.stereotype for c in f.candidates]
    assert f.suggestion != "WBADataAsset"


def test_a_sibling_in_another_package_does_not_vote():
    rows = [el("{A}", "Thing", "Component", package_id=4),
            el("{S}", "Sib", "Component", package_id=99, stereotype="WBAVendorSystem")]
    f = assess(find_ungoverned(rows, tags("{A}", COMMON)), DECLARED, rows)[0]
    assert f.outcome == UNRANKABLE


def test_a_stereotype_declaring_tags_the_element_lacks_is_demoted_not_offered_first():
    """An element with the six common tags is not an AI service that declares ten."""
    rows = [el("{A}", "Thing", "Component", package_id=4)]
    f = assess(find_ungoverned(rows, tags("{A}", COMMON)), DECLARED, rows)[0]
    names = [c.stereotype for c in f.candidates]
    assert names.index("WBAAIGateway") == len(names) - 1


def test_an_element_carrying_a_tag_no_candidate_declares_drops_that_candidate():
    rows = [el("{A}", "Thing", "Component", package_id=4)]
    extra = tags("{A}", COMMON | {"somethingElseEntirely"})
    f = assess(find_ungoverned(rows, extra), DECLARED, rows)[0]
    # every Component stereotype fails the subset test, so none may be offered
    assert f.candidates == []
    assert f.outcome == UNRANKABLE


def test_ties_on_votes_do_not_rank():
    """Two candidates with equal sibling support is not evidence for either."""
    rows = [el("{A}", "Thing", "Component", package_id=4),
            el("{S1}", "S1", "Component", package_id=4, stereotype="WBAVendorSystem"),
            el("{S2}", "S2", "Component", package_id=4, stereotype="WBABusinessService")]
    f = assess(find_ungoverned(rows, tags("{A}", COMMON)), DECLARED, rows)[0]
    assert f.outcome == UNRANKABLE


# --- reporting ---------------------------------------------------------

def test_summary_counts_each_outcome():
    rows = [el("{N}", "Node thing", "Node"),
            el("{A}", "Comp thing", "Component", package_id=4),
            el("{B}", "Ranked thing", "Component", package_id=5),
            el("{S}", "Sib", "Component", package_id=5, stereotype="WBAVendorSystem")]
    f = assess(find_ungoverned(rows, tags("{B}", COMMON)), DECLARED, rows)
    s = summarize(f)
    assert s == {"total": 3, "governed": 1,
                 NO_CANDIDATE: 1, RANKED: 1, UNRANKABLE: 1}


def test_the_report_states_the_consequence_of_declining():
    rows = [el("{A}", "Thing", "Component")]
    text = format_report(assess(find_ungoverned(rows, []), DECLARED, rows))
    assert "will NOT appear" in text
    assert "valid answer" in text


def test_an_empty_gap_says_so_rather_than_printing_nothing():
    assert "No ungoverned elements" in format_report([])


def test_locality_votes_ignores_unstereotyped_neighbors():
    rows = [el("{S}", "S", "Component", package_id=3, stereotype="WBAVendorSystem"),
            el("{U}", "U", "Component", package_id=3)]
    assert locality_votes(rows, package_id=3) == {"WBAVendorSystem": 1}

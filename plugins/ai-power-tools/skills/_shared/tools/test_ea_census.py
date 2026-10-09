#!/usr/bin/env python3
"""Tests for the profile-aware census.

Run from the repository root:

    python -m pytest _shared/tools/test_ea_census.py -q

Nothing here touches a repository, a COM object or the filesystem.

WHAT THIS FILE COVERS
---------------------
Every fixture row below is the SHAPE of something measured against a live
repository, not invented. The `@STEREO` strings in particular are real: the
several row forms one stereotype name takes, and the two-blocks-in-one-row
packing of a multi-stereotype element.

The emphasis is deliberately on the cases that have ALREADY caused a defect, or
that no previous fixture could reach:

  * provenance by FQName-present rather than row-present (dropped 24 elements)
  * two @STEREO blocks in one row (a `re.search` here undercounted silently)
  * one stereotype across two metaclasses (no fixture had this until recently)
  * table-name collision (silently lost a whole stereotype)
  * populated-vs-present coverage (reports 100% on an empty tag)
  * a tag value that legitimately contains the split separator

Each of those has a NEGATIVE test - a case asserting the wrong behavior is not
produced - because the prototype this replaces passed every check it had on the
first run, which proved nothing about detection.
"""
from __future__ import annotations

import pytest

from ea_census import (
    DRIFT_CONNECTOR_NAME_NOT_BOUND,
    DRIFT_CONNECTOR_UNBOUND,
    DRIFT_DECLARED_UNUSED,
    DRIFT_ELEMENT_MULTIPLE_DECLARED,
    DRIFT_ENUM_DECLARED_UNUSED,
    DRIFT_ENUM_OBSERVED_UNDECLARED,
    DRIFT_FOREIGN_LANGUAGE,
    DRIFT_METACLASS_MISMATCH,
    DRIFT_OBSERVED_UNDECLARED,
    DRIFT_TAG_NEVER_POPULATED,
    DRIFT_TAG_OBSERVED_UNDECLARED,
    Drift,
    Entity,
    infer_technology_namespace,
    Stereotype,
    TagStat,
    build_stereotype_index,
    census_connectors,
    census_elements,
    compare_connectors_declared_observed,
    compare_declared_observed,
    connector_guid_of,
    declared_connector_stereotypes,
    entity_key,
    infer_enum_domain,
    parse_stereotype_blocks,
    snake_case,
    split_multi_value,
    table_name,
    tag_coverage,
)

NS = "WestbrookBankArchitecture"


def stereo_row(guid, *blocks):
    """A t_xref row. Each block is (name, fqname, guid) with "" for absent."""
    desc = "".join(
        "@STEREO;Name={n};{g}{f}@ENDSTEREO;".format(
            n=n,
            g=("GUID=%s;" % g) if g else "",
            f=("FQName=%s;" % fq) if fq else "",
        )
        for n, fq, g in blocks
    )
    return {"Client": guid, "Description": desc}


def obj(guid, metaclass, stereotype=""):
    return {"ea_guid": guid, "Object_Type": metaclass, "Stereotype": stereotype}


# --------------------------------------------------------------------------
# Parsing and provenance
# --------------------------------------------------------------------------

def test_profile_bound_block_is_parsed():
    s = parse_stereotype_blocks(
        "@STEREO;Name=WBADataAsset;GUID={08EE};FQName=%s::WBADataAsset;@ENDSTEREO;" % NS)
    assert len(s) == 1
    assert s[0].name == "WBADataAsset"
    assert s[0].fqname == "%s::WBADataAsset" % NS
    assert s[0].profile == NS
    assert s[0].is_profile_bound is True


@pytest.mark.parametrize("desc", [
    "@STEREO;Name=WBADataAsset;GUID={08EE2B36-1853-472b-921D-10A831E42E47};@ENDSTEREO;",
    "@STEREO;Name=WBADataAsset;@ENDSTEREO;",
])
def test_row_without_fqname_is_ad_hoc_not_profile_bound(desc):
    """THE provenance rule. A row existing is not evidence of a profile.

    Treating row-existence as the test is what dropped 24 elements that have a
    Stereotypes row carrying no FQName.
    """
    s = parse_stereotype_blocks(desc)
    assert len(s) == 1
    assert s[0].is_profile_bound is False
    assert s[0].profile == ""


def test_multi_stereotype_is_several_blocks_in_one_row():
    """The row count is 1. A `re.search` for FQName finds only the first.

    This is the exact defect that made a reconciler undercount by one, and it
    was undetectable until a fixture gained a multi-stereotype element.
    """
    desc = ("@STEREO;Name=WBASystemOfRecord;GUID={EEC7};FQName=%s::WBASystemOfRecord;@ENDSTEREO;"
            "@STEREO;Name=WBABusinessApplication;GUID={E9FE};FQName=%s::WBABusinessApplication;@ENDSTEREO;"
            % (NS, NS))
    s = parse_stereotype_blocks(desc)
    assert [x.name for x in s] == ["WBASystemOfRecord", "WBABusinessApplication"]
    assert all(x.is_profile_bound for x in s)


def test_multi_stereotype_order_puts_primary_first():
    """t_object.Stereotype mirrors the FIRST block, so order carries meaning."""
    desc = ("@STEREO;Name=First;FQName=P::First;@ENDSTEREO;"
            "@STEREO;Name=Second;FQName=P::Second;@ENDSTEREO;")
    assert parse_stereotype_blocks(desc)[0].name == "First"


@pytest.mark.parametrize("bad", [None, "", "not a stereo string", "@STEREO;@ENDSTEREO;"])
def test_malformed_input_yields_nothing_rather_than_raising(bad):
    assert parse_stereotype_blocks(bad) == []


def test_index_merges_several_rows_for_one_guid():
    idx = build_stereotype_index([
        stereo_row("{A}", ("One", "P::One", "")),
        stereo_row("{A}", ("Two", "P::Two", "")),
    ])
    assert [s.name for s in idx["{A}"]] == ["One", "Two"]


# --------------------------------------------------------------------------
# Identity
# --------------------------------------------------------------------------

def test_profile_bound_identity_is_the_fqname():
    s = Stereotype("WBASystemOfRecord", "%s::WBASystemOfRecord" % NS)
    assert entity_key(s, "Component") == entity_key(s, "Class") == s.fqname


def test_ad_hoc_identity_includes_the_metaclass():
    """A bare name is ambiguous across languages, so the pair carries identity."""
    s = Stereotype("BusinessService")
    assert entity_key(s, "Class") != entity_key(s, "Component")


# --------------------------------------------------------------------------
# Census
# --------------------------------------------------------------------------

def test_same_name_splits_into_governed_and_ad_hoc():
    """Measured: WBADataAsset is 11 profile-bound and 1 ad hoc. One name, two
    entities. Merging them hides the ungoverned one entirely."""
    objects, xrefs = [], []
    for i in range(11):
        g = "{P%d}" % i
        objects.append(obj(g, "Object", "WBADataAsset"))
        xrefs.append(stereo_row(g, ("WBADataAsset", "%s::WBADataAsset" % NS, "")))
    objects.append(obj("{AD}", "Object", "WBADataAsset"))
    xrefs.append(stereo_row("{AD}", ("WBADataAsset", "", "{08EE}")))

    c = census_elements(objects, build_stereotype_index(xrefs))
    by_key = {e.key: e for e in c.entities}
    assert by_key["%s::WBADataAsset" % NS].count == 11
    assert by_key["WBADataAsset|Object"].count == 1


def test_one_stereotype_across_two_metaclasses_is_one_entity_flagged_heterogeneous():
    """Measured: WBASystemOfRecord on 4 Component and 1 Class.

    One concept, so one entity - but the split is reported, not discarded.
    """
    fq = "%s::WBASystemOfRecord" % NS
    objects, xrefs = [], []
    for i in range(4):
        g = "{C%d}" % i
        objects.append(obj(g, "Component", "WBASystemOfRecord"))
        xrefs.append(stereo_row(g, ("WBASystemOfRecord", fq, "")))
    objects.append(obj("{K}", "Class", "WBASystemOfRecord"))
    xrefs.append(stereo_row("{K}", ("WBASystemOfRecord", fq, "")))

    ent = {e.key: e for e in census_elements(objects, build_stereotype_index(xrefs)).entities}[fq]
    assert ent.count == 5
    assert ent.is_heterogeneous is True
    assert ent.primary_metaclass == "Component"
    assert dict(ent.metaclasses) == {"Component": 4, "Class": 1}


def test_homogeneous_entity_is_not_flagged_heterogeneous():
    fq = "%s::WBAVendorSystem" % NS
    objects = [obj("{V%d}" % i, "Component", "WBAVendorSystem") for i in range(3)]
    xrefs = [stereo_row("{V%d}" % i, ("WBAVendorSystem", fq, "")) for i in range(3)]
    ent = census_elements(objects, build_stereotype_index(xrefs)).entities[0]
    assert ent.is_heterogeneous is False


def test_multi_stereotype_element_lands_in_both_entities_but_counts_once():
    """The whole point. t_object.Stereotype shows only the first, so a census
    reading that column reports this element once and undercounts the other."""
    sor = "%s::WBASystemOfRecord" % NS
    app = "%s::WBABusinessApplication" % NS
    objects = [obj("{M}", "Component", "WBASystemOfRecord")]
    xrefs = [stereo_row("{M}", ("WBASystemOfRecord", sor, ""),
                              ("WBABusinessApplication", app, ""))]

    c = census_elements(objects, build_stereotype_index(xrefs))
    assert {e.key for e in c.entities} == {sor, app}
    assert all(e.count == 1 for e in c.entities)
    assert sorted(c.placement["{M}"]) == sorted([sor, app])
    assert c.total_typed == 1          # one element, not two
    assert c.multi_stereotype_guids == {"{M}"}


def test_element_with_no_xref_row_falls_back_to_the_bare_column():
    """Ungoverned content is exactly what the census exists to surface, so it
    must not be dropped for lacking an xref row."""
    c = census_elements([obj("{B}", "Component", "VendorApplication")], {})
    assert c.entities[0].key == "VendorApplication|Component"
    assert c.entities[0].is_profile_bound is False


def test_elements_with_no_stereotype_are_recorded_not_discarded():
    c = census_elements([obj("{U}", "Class", "")], {})
    assert c.entities == []
    assert c.untyped_guids == {"{U}"}


@pytest.mark.parametrize("name", sorted(["EATool", "model document", "report package"]))
def test_ea_internal_stereotypes_are_excluded_and_counted(name):
    c = census_elements([obj("{E}", "Class", name)], {})
    assert c.entities == []
    assert c.excluded_ea_internal[name] == 1


@pytest.mark.parametrize("name", sorted([
    "stereotype", "metaclass", "profile", "toolbox profile",
    "diagram profile", "mdg technology",
]))
def test_profile_authoring_stereotypes_are_excluded_and_counted(name):
    """A repository whose owner builds MDGs from a source model carries these.
    Measured: such a model took a whole-repository census from 22 distinct
    stereotypes to 28 and from 131 stereotyped elements to 161."""
    c = census_elements([obj("{S}", "Class", name)], {})
    assert c.entities == []
    assert c.excluded_profile_authoring[name] == 1


def test_exclusions_can_be_turned_off():
    c = census_elements([obj("{S}", "Class", "stereotype")], {},
                        exclude_profile_authoring=False)
    assert c.entities[0].count == 1


def test_eauml_profile_is_excluded():
    c = census_elements(
        [obj("{R}", "Package", "report package")],
        build_stereotype_index([stereo_row("{R}", ("report package",
                                                   "EAUML::report package", ""))]))
    assert c.entities == []


def test_entity_order_is_deterministic_and_not_insertion_order():
    objects, xrefs = [], []
    for name, n in (("Alpha", 1), ("Beta", 3), ("Gamma", 3)):
        for i in range(n):
            g = "{%s%d}" % (name, i)
            objects.append(obj(g, "Class", name))
            xrefs.append(stereo_row(g, (name, "P::%s" % name, "")))
    keys = [e.key for e in census_elements(objects, build_stereotype_index(xrefs)).entities]
    assert keys == ["P::Beta", "P::Gamma", "P::Alpha"]   # count desc, then key

    reversed_run = census_elements(list(reversed(objects)),
                                   build_stereotype_index(list(reversed(xrefs))))
    assert [e.key for e in reversed_run.entities] == keys


# --------------------------------------------------------------------------
# Tag coverage
# --------------------------------------------------------------------------

def _entity_with(guids):
    e = Entity(key="k", stereotype="S")
    e.guids.update(guids)
    return e


def test_coverage_counts_populated_values_not_rows_present():
    """Measured: a stereotype carrying a tag on 8 of 8 elements with 0 of 8
    populated. A presence metric calls that 100% and is wrong."""
    ent = _entity_with(["{1}", "{2}", "{3}", "{4}"])
    rows = [{"Object_ID": g, "Property": "lifecycle", "Value": ""} for g in ent.guids]
    st = tag_coverage(ent, rows, lambda r: r["Object_ID"])[0]
    assert st.present == 4
    assert st.populated == 0
    assert st.coverage(4) == 0.0          # NOT 1.0


def test_whitespace_only_value_is_not_populated():
    ent = _entity_with(["{1}"])
    st = tag_coverage(ent, [{"Object_ID": "{1}", "Property": "owner", "Value": "   "}],
                      lambda r: r["Object_ID"])[0]
    assert st.present == 1 and st.populated == 0


def test_coverage_ignores_rows_belonging_to_other_elements():
    ent = _entity_with(["{1}"])
    rows = [{"Object_ID": "{1}", "Property": "a", "Value": "x"},
            {"Object_ID": "{9}", "Property": "a", "Value": "y"}]
    st = tag_coverage(ent, rows, lambda r: r["Object_ID"])[0]
    assert st.populated == 1


def test_enum_inference_is_conservative():
    st = TagStat(tag="criticality")
    st.values.update(["Mission-Critical"] * 3 + ["Standard"] * 2)
    assert infer_enum_domain(st) == ["Mission-Critical", "Standard"]


def test_all_distinct_values_are_treated_as_free_text_not_a_domain():
    st = TagStat(tag="businessOwner")
    st.values.update(["Team A", "Team B", "Team C"])
    assert infer_enum_domain(st) is None


def test_too_many_distinct_values_is_not_a_domain():
    st = TagStat(tag="notes")
    st.values.update({"v%d" % i: 2 for i in range(50)})
    assert infer_enum_domain(st) is None


# --------------------------------------------------------------------------
# Naming
# --------------------------------------------------------------------------

def test_snake_case_cannot_split_an_all_caps_prefix():
    """Documents the trap rather than pretending it is solved: this is exactly
    why an MDG alias is preferred over deriving a name from the stereotype."""
    assert snake_case("WBABusinessApplication") == "wbabusiness_application"


@pytest.mark.parametrize("raw,want", [
    ("Business Application", "business_application"),
    ("BusinessApplication", "business_application"),
    ("Data Asset (ad-hoc)", "data_asset_ad_hoc"),
    ("  spaced  out  ", "spaced_out"),
])
def test_snake_case_cases(raw, want):
    assert snake_case(raw) == want


def test_alias_beats_prefix_stripping():
    e = Entity(key="k", stereotype="WBABusinessApplication", fqname="%s::X" % NS, profile=NS)
    assert table_name(e, set(), alias_of=lambda _: "Business Application") == "business_application"


def test_prefix_stripping_is_the_fallback():
    e = Entity(key="k", stereotype="WBABusinessApplication")
    assert table_name(e, set(), strip_prefix="WBA") == "business_application"


def test_colliding_names_are_qualified_not_overwritten():
    """Measured: WBABusinessService and TOGAF::BusinessService both reduced to
    `business_service` and one silently overwrote the other, losing a whole
    stereotype."""
    taken = set()
    wba = Entity(key="a", stereotype="WBABusinessService",
                 fqname="%s::WBABusinessService" % NS, profile=NS)
    togaf = Entity(key="b", stereotype="BusinessService",
                   fqname="TOGAF::BusinessService", profile="TOGAF")

    first = table_name(wba, taken, alias_of=lambda _: "Business Service")
    second = table_name(togaf, taken, alias_of=lambda _: "Business Service")
    assert first == "business_service"
    assert second == "togaf_business_service"
    assert first != second


def test_ad_hoc_collision_is_qualified_as_adhoc():
    taken = {"data_asset"}
    e = Entity(key="k", stereotype="WBADataAsset")
    assert table_name(e, taken, alias_of=lambda _: "Data Asset") == "adhoc_data_asset"


def test_third_collision_still_resolves_uniquely():
    taken = {"thing", "adhoc_thing"}
    e = Entity(key="k", stereotype="Thing")
    assert table_name(e, taken) == "adhoc_thing_2"


# --------------------------------------------------------------------------
# Declared vs observed - the headline capability
# --------------------------------------------------------------------------

MDG = {
    "stereotypes": [
        {"name": "WBADataAsset", "base_metaclass": "Class",
         "tagged_values": [{"name": "dataClassification",
                            "values": ["Public", "Internal", "Confidential", "Restricted"]},
                           {"name": "lifecycle",
                            "values": ["Strategic", "Current", "Sunset",
                                       "Deprecated", "Retired"]}]},
        {"name": "WBAGovernedElement", "base_metaclass": "Class", "tagged_values": []},
    ]
}


def _census_of(*objects_and_xrefs):
    objects, xrefs = objects_and_xrefs
    return census_elements(objects, build_stereotype_index(xrefs))


def test_declared_but_never_used_is_reported():
    c = _census_of([obj("{1}", "Object", "WBADataAsset")],
                   [stereo_row("{1}", ("WBADataAsset", "%s::WBADataAsset" % NS, ""))])
    kinds = [(d.kind, d.subject) for d in compare_declared_observed(c, MDG)]
    assert (DRIFT_DECLARED_UNUSED, "WBAGovernedElement") in kinds


def test_declared_connector_stereotype_is_not_an_unused_element_stereotype():
    mdg = {"stereotypes": MDG["stereotypes"] + [
        {"name": "Uses", "base_metaclass": "Dependency", "tagged_values": []}]}
    c = _census_of([obj("{1}", "Object", "WBADataAsset")],
                   [stereo_row("{1}", ("WBADataAsset", "%s::WBADataAsset" % NS, ""))])
    assert "Uses" not in {d.subject for d in compare_declared_observed(c, mdg)}


def test_observed_but_never_declared_is_reported():
    c = _census_of([obj("{1}", "Component", "VendorApplication")], [])
    kinds = [(d.kind, d.subject) for d in compare_declared_observed(c, MDG)]
    assert (DRIFT_OBSERVED_UNDECLARED, "VendorApplication") in kinds


def test_metaclass_mismatch_is_reported():
    """Measured: WBADataAsset declares Class, all 12 instances are Object."""
    c = _census_of([obj("{%d}" % i, "Object", "WBADataAsset") for i in range(12)],
                   [stereo_row("{%d}" % i, ("WBADataAsset", "%s::WBADataAsset" % NS, ""))
                    for i in range(12)])
    d = [x for x in compare_declared_observed(c, MDG) if x.kind == DRIFT_METACLASS_MISMATCH]
    assert len(d) == 1
    assert "declares base_metaclass Class" in d[0].detail
    assert "Object (12)" in d[0].detail


def test_matching_metaclass_produces_no_mismatch():
    c = _census_of([obj("{1}", "Class", "WBADataAsset")],
                   [stereo_row("{1}", ("WBADataAsset", "%s::WBADataAsset" % NS, ""))])
    assert not [x for x in compare_declared_observed(c, MDG)
                if x.kind == DRIFT_METACLASS_MISMATCH]


def test_value_used_but_not_declared_is_reported():
    """The correctness finding, and the one that matters most.

    Measured: elements carry `lifecycle: Archive`, which the technology does
    not declare. A value that no longer validates, invisible until something
    enforces the domain.
    """
    key = "%s::WBADataAsset" % NS
    c = _census_of([obj("{1}", "Class", "WBADataAsset")],
                   [stereo_row("{1}", ("WBADataAsset", key, ""))])
    st = TagStat(tag="lifecycle")
    st.values.update(["Archive", "Archive", "Current"])
    st.populated = 3
    drifts = compare_declared_observed(c, MDG, {key: [st]})
    bad = [d for d in drifts if d.kind == DRIFT_ENUM_OBSERVED_UNDECLARED]
    assert len(bad) == 1
    assert "'Archive'" in bad[0].detail


def test_value_declared_but_never_used_is_reported():
    key = "%s::WBADataAsset" % NS
    c = _census_of([obj("{1}", "Class", "WBADataAsset")],
                   [stereo_row("{1}", ("WBADataAsset", key, ""))])
    st = TagStat(tag="dataClassification")
    st.values.update(["Public", "Internal", "Confidential"])
    st.populated = 3
    unused = [d for d in compare_declared_observed(c, MDG, {key: [st]})
              if d.kind == DRIFT_ENUM_DECLARED_UNUSED]
    assert len(unused) == 1
    assert "'Restricted'" in unused[0].detail


def test_tag_populated_but_never_declared_is_reported():
    key = "%s::WBADataAsset" % NS
    c = _census_of([obj("{1}", "Class", "WBADataAsset")],
                   [stereo_row("{1}", ("WBADataAsset", key, ""))])
    st = TagStat(tag="pciScopeJustification", populated=2)
    st.values.update(["a", "b"])
    found = [d for d in compare_declared_observed(c, MDG, {key: [st]})
             if d.kind == DRIFT_TAG_OBSERVED_UNDECLARED]
    assert len(found) == 1


def test_drift_output_is_deterministic():
    c = _census_of([obj("{1}", "Object", "WBADataAsset")],
                   [stereo_row("{1}", ("WBADataAsset", "%s::WBADataAsset" % NS, ""))])
    assert compare_declared_observed(c, MDG) == compare_declared_observed(c, MDG)


# --------------------------------------------------------------------------
# Multi-valued tags
# --------------------------------------------------------------------------

def test_multi_value_split():
    assert split_multi_value("GLBA, FFIEC") == ["GLBA", "FFIEC"]


def test_split_corrupts_a_legitimate_comma_and_the_test_says_so():
    """NOT a bug in the splitter - a documented hazard the caller must decide
    about per tag.

    Measured fixture case: a team name "Risk, Compliance & Audit" is ONE value.
    The MDG declares both it and the genuinely multi-valued tag as `String`, so
    the declared type cannot tell the two apart and the caller must.
    """
    assert split_multi_value("Risk, Compliance & Audit") == ["Risk", "Compliance & Audit"]


@pytest.mark.parametrize("raw", ["", None])
def test_split_of_nothing_is_empty(raw):
    assert split_multi_value(raw or "") == []


def test_split_drops_empty_segments():
    assert split_multi_value("GLBA,,  ,FFIEC") == ["GLBA", "FFIEC"]


# --------------------------------------------------------------------------
# Regressions found by running the module against a LIVE repository.
#
# Every one of these passed the hermetic suite above and was still wrong. They
# are the argument for the acceptance script: internal consistency is not
# correctness.
# --------------------------------------------------------------------------

def test_metaclass_mismatch_aggregates_entities_sharing_a_name():
    """REGRESSION. A name can own several entities - profile-bound and ad hoc.

    Collapsing them with {e.stereotype: e} let the LAST one win, so a mismatch
    over 12 instances was reported as "Object (1)" from the one-element ad-hoc
    entity. The evidence was wrong even though the finding was right.
    """
    fq = "%s::WBADataAsset" % NS
    objects, xrefs = [], []
    for i in range(11):
        g = "{P%d}" % i
        objects.append(obj(g, "Object", "WBADataAsset"))
        xrefs.append(stereo_row(g, ("WBADataAsset", fq, "")))
    objects.append(obj("{AD}", "Object", "WBADataAsset"))
    xrefs.append(stereo_row("{AD}", ("WBADataAsset", "", "{08EE}")))

    c = census_elements(objects, build_stereotype_index(xrefs))
    assert len([e for e in c.entities if e.stereotype == "WBADataAsset"]) == 2

    d = [x for x in compare_declared_observed(c, MDG)
         if x.kind == DRIFT_METACLASS_MISMATCH]
    assert len(d) == 1
    assert "Object (12)" in d[0].detail          # not "Object (1)" or "Object (11)"


def test_a_stereotype_from_another_language_is_not_drift():
    """REGRESSION. TOGAF and BPMN elements were reported as "not declared in
    the technology", which is true and useless - they belong to a different
    language. 15 such findings buried the real ones.
    """
    objects = [obj("{1}", "Object", "WBADataAsset"),
               obj("{2}", "Component", "ApplicationComponent")]
    xrefs = [stereo_row("{1}", ("WBADataAsset", "%s::WBADataAsset" % NS, "")),
             stereo_row("{2}", ("ApplicationComponent", "TOGAF::ApplicationComponent", ""))]
    c = census_elements(objects, build_stereotype_index(xrefs))

    subjects = [d.subject for d in compare_declared_observed(c, MDG)
                if d.kind == DRIFT_OBSERVED_UNDECLARED]
    assert "ApplicationComponent" not in subjects


def test_an_ad_hoc_stereotype_IS_still_drift():
    """The other half of the previous test: ungoverned content in no profile at
    all is exactly what should be reported."""
    c = census_elements([obj("{1}", "Component", "VendorApplication")], {})
    subjects = [d.subject for d in compare_declared_observed(c, MDG)
                if d.kind == DRIFT_OBSERVED_UNDECLARED]
    assert "VendorApplication" in subjects


def test_an_undeclared_stereotype_in_our_own_namespace_IS_drift():
    objects = [obj("{1}", "Object", "WBADataAsset"),
               obj("{2}", "Component", "WBAMystery")]
    xrefs = [stereo_row("{1}", ("WBADataAsset", "%s::WBADataAsset" % NS, "")),
             stereo_row("{2}", ("WBAMystery", "%s::WBAMystery" % NS, ""))]
    c = census_elements(objects, build_stereotype_index(xrefs))
    subjects = [d.subject for d in compare_declared_observed(c, MDG)
                if d.kind == DRIFT_OBSERVED_UNDECLARED]
    assert "WBAMystery" in subjects


def test_namespace_is_inferred_from_evidence_not_from_the_technology_id():
    """The technology id, the display name and the FQName namespace are three
    different strings and none of them match, so the namespace has to be
    inferred from which profile carries the declared stereotype names."""
    objects = [obj("{%d}" % i, "Object", "WBADataAsset") for i in range(3)]
    xrefs = [stereo_row("{%d}" % i, ("WBADataAsset", "%s::WBADataAsset" % NS, ""))
             for i in range(3)]
    objects.append(obj("{T}", "Component", "ApplicationComponent"))
    xrefs.append(stereo_row("{T}", ("ApplicationComponent", "TOGAF::ApplicationComponent", "")))

    c = census_elements(objects, build_stereotype_index(xrefs))
    assert infer_technology_namespace(c, {"WBADataAsset", "WBAGovernedElement"}) == NS


def test_namespace_inference_returns_empty_when_nothing_matches():
    c = census_elements([obj("{1}", "Component", "Thing")], {})
    assert infer_technology_namespace(c, {"WBADataAsset"}) == ""


def test_an_unpopulated_tag_is_one_finding_not_one_per_declared_value():
    """REGRESSION. A tag nobody filled in emitted one `declared value never
    used` finding PER value. Across the fixture that produced 99 findings and
    buried the single real one.
    """
    key = "%s::WBADataAsset" % NS
    c = census_elements([obj("{1}", "Class", "WBADataAsset")],
                        build_stereotype_index([stereo_row("{1}", ("WBADataAsset", key, ""))]))
    st = TagStat(tag="dataClassification", present=1, populated=0)   # 4 declared values

    drifts = compare_declared_observed(c, MDG, {key: [st]})
    never = [d for d in drifts if d.kind == DRIFT_TAG_NEVER_POPULATED]
    per_value = [d for d in drifts if d.kind == DRIFT_ENUM_DECLARED_UNUSED]
    assert len(never) == 1
    assert per_value == []
    assert "populated on none" in never[0].detail


def test_partially_used_domain_reports_one_aggregated_finding():
    key = "%s::WBADataAsset" % NS
    c = census_elements([obj("{1}", "Class", "WBADataAsset")],
                        build_stereotype_index([stereo_row("{1}", ("WBADataAsset", key, ""))]))
    st = TagStat(tag="dataClassification", present=2, populated=2)
    st.values.update(["Public", "Internal"])

    unused = [d for d in compare_declared_observed(c, MDG, {key: [st]})
              if d.kind == DRIFT_ENUM_DECLARED_UNUSED]
    assert len(unused) == 1                       # one finding, not two
    assert "'Confidential'" in unused[0].detail
    assert "'Restricted'" in unused[0].detail


def test_excluded_elements_are_not_counted_as_untyped():
    """REGRESSION. An element whose every stereotype was excluded as EA's own
    machinery fell into `untyped_guids`, which conflates "we deliberately
    dropped EA scaffolding" with "this has no stereotype at all". Downstream
    that reported 29 rows of EA report-package tags (ReportName, SearchValue)
    as unplaced business data.
    """
    c = census_elements([obj("{E}", "Package", "report package"),
                         obj("{U}", "Class", "")], {})
    assert c.excluded_guids == {"{E}"}
    assert c.untyped_guids == {"{U}"}
    assert c.excluded_guids.isdisjoint(c.untyped_guids)


def test_an_element_with_one_excluded_and_one_kept_stereotype_is_still_placed():
    c = census_elements(
        [obj("{M}", "Component", "EATool")],
        build_stereotype_index([stereo_row("{M}", ("EATool", "", ""),
                                           ("WBAThing", "%s::WBAThing" % NS, ""))]))
    assert c.placement["{M}"] == ["%s::WBAThing" % NS]
    assert c.excluded_guids == set()
    assert c.excluded_ea_internal["EATool"] == 1


# --------------------------------------------------------------------------
# Connector census (APT-2026-0223)
# --------------------------------------------------------------------------

CONN_MDG = {
    "stereotypes": [
        {"name": "WBADataAsset", "base_metaclass": "Class", "tagged_values": []},
        {"name": "Uses", "base_metaclass": "Association",
         "tagged_values": [{"name": "slaTier", "values": ["Gold", "Silver"]},
                           {"name": "integrationPattern",
                            "values": ["API", "Batch", "Event", "File"]}]},
        {"name": "Flows", "base_metaclass": "InformationFlow", "tagged_values": []},
        {"name": "realizes", "base_metaclass": "Realisation", "tagged_values": []},
    ]
}

USES = "%s::Uses" % NS


def conn(guid, ctype, stereotype="", cid=None):
    return {"ea_guid": guid, "Connector_Type": ctype, "Stereotype": stereotype,
            "Connector_ID": cid}


def _conn_census(connectors, *xref_rows):
    return census_connectors(connectors, build_stereotype_index(list(xref_rows)))


def _kinds(drifts):
    return [(d.kind, d.subject) for d in drifts]


def test_connector_provenance_is_fqname_present_not_row_present():
    """A row with only Name and GUID is ad hoc, exactly as for elements."""
    c = _conn_census(
        [conn("{c1}", "Association", "Uses"), conn("{c2}", "Association", "Uses")],
        stereo_row("{c1}", ("Uses", USES, "{s1}")),
        stereo_row("{c2}", ("Uses", "", "{s2}")),
    )
    by_key = {e.key: e for e in c.entities}
    assert by_key[USES + "|Association"].is_profile_bound
    assert not by_key["Uses|Association"].is_profile_bound
    assert c.provenance_split() == {"profile_bound": 1, "ad_hoc": 1}


def test_connector_key_is_stereotype_plus_base_type():
    c = _conn_census(
        [conn("{c1}", "Association", "Uses"), conn("{c2}", "Dependency", "Uses")],
        stereo_row("{c1}", ("Uses", USES, "")),
        stereo_row("{c2}", ("Uses", USES, "")),
    )
    assert sorted(e.key for e in c.entities) == [USES + "|Association", USES + "|Dependency"]


def test_connectors_without_a_stereotype_are_counted_by_base_type():
    c = _conn_census([conn("{c1}", "Association"), conn("{c2}", "Association"),
                      conn("{c3}", "Dependency")])
    assert c.untyped_guids == {"{c1}", "{c2}", "{c3}"}
    assert c.untyped_by_type == {"Association": 2, "Dependency": 1}
    assert not c.entities


def test_connector_with_no_xref_row_falls_back_to_the_bare_column_as_ad_hoc():
    c = _conn_census([conn("{c1}", "Association", "extends")])
    assert [(e.key, e.is_profile_bound) for e in c.entities] == [("extends|Association", False)]


def test_multi_stereotype_connector_counts_once_per_stereotype():
    c = _conn_census(
        [conn("{c1}", "Association", "Uses")],
        stereo_row("{c1}", ("Uses", USES, ""), ("Requires", "BMM::Requires", "")),
    )
    assert c.multi_stereotype_guids == {"{c1}"}
    assert sorted(c.placement["{c1}"]) == sorted([USES + "|Association",
                                                  "BMM::Requires|Association"])
    assert [e.count for e in c.entities] == [1, 1]
    assert c.total_typed == 1
    assert c.provenance_split() == {"profile_bound": 2, "ad_hoc": 0}


def test_ea_internal_connector_profile_is_excluded_and_counted():
    c = _conn_census([conn("{c1}", "Association", "link")],
                     stereo_row("{c1}", ("link", "EAUML::link", "")))
    assert not c.entities
    assert c.excluded_guids == {"{c1}"}
    assert c.excluded_ea_internal == {"EAUML::link": 1}


def test_declared_connector_stereotype_never_used_is_reported():
    c = _conn_census([conn("{c1}", "Association", "Uses")],
                     stereo_row("{c1}", ("Uses", USES, "")))
    kinds = _kinds(compare_connectors_declared_observed(c, CONN_MDG, namespace=NS))
    assert (DRIFT_DECLARED_UNUSED, "Flows") in kinds
    assert (DRIFT_DECLARED_UNUSED, "realizes") in kinds
    assert (DRIFT_DECLARED_UNUSED, "Uses") not in kinds


def test_element_stereotypes_in_the_same_mdg_are_not_connector_declarations():
    c = _conn_census([conn("{c1}", "Association", "Uses")],
                     stereo_row("{c1}", ("Uses", USES, "")))
    assert "WBADataAsset" not in {d.subject for d in
                                  compare_connectors_declared_observed(c, CONN_MDG, namespace=NS)}


def test_connector_stereotypes_can_be_declared_in_their_own_list():
    mdg = {"stereotypes": [], "connector_stereotypes": [
        {"name": "Uses", "base_metaclass": "Association", "tagged_values": []}]}
    assert list(declared_connector_stereotypes(mdg)) == ["Uses"]


def test_ad_hoc_connector_stereotype_is_observed_never_declared():
    c = _conn_census([conn("{c1}", "Generalization", "extends"),
                      conn("{c2}", "Generalization", "extends")])
    found = [d for d in compare_connectors_declared_observed(c, CONN_MDG, namespace=NS)
             if d.kind == DRIFT_OBSERVED_UNDECLARED]
    assert [(d.subject, d.detail) for d in found] == [
        ("extends", "2 ad-hoc connector(s), bound to no profile")]


def test_another_languages_connector_stereotype_is_not_reported_as_ad_hoc():
    c = _conn_census([conn("{c1}", "Dependency", "Requires")],
                     stereo_row("{c1}", ("Requires", "BMM::Requires", "")))
    kinds = _kinds(compare_connectors_declared_observed(c, CONN_MDG, namespace=NS))
    assert (DRIFT_FOREIGN_LANGUAGE, "Requires") in kinds
    assert (DRIFT_OBSERVED_UNDECLARED, "Requires") not in kinds


def test_a_declared_name_carried_ad_hoc_or_from_another_language_is_flagged():
    """A bare Uses and a BMM::Uses must not pass for the declared Uses."""
    c = _conn_census(
        [conn("{c1}", "Association", "Uses"), conn("{c2}", "Association", "Uses"),
         conn("{c3}", "Association", "Uses"), conn("{c4}", "Association", "Uses")],
        stereo_row("{c1}", ("Uses", USES, "")),
        stereo_row("{c2}", ("Uses", USES, "")),
        stereo_row("{c3}", ("Uses", "", "")),
        stereo_row("{c4}", ("Uses", "BMM::Uses", "")),
    )
    found = [d for d in compare_connectors_declared_observed(c, CONN_MDG, namespace=NS)
             if d.kind == DRIFT_CONNECTOR_NAME_NOT_BOUND]
    assert len(found) == 1
    assert found[0].guids == ("{c3}", "{c4}")
    assert "1 ad hoc, 1 bound to BMM" in found[0].detail


def test_a_fully_governed_declared_connector_stereotype_is_not_flagged():
    c = _conn_census([conn("{c1}", "Association", "Uses")],
                     stereo_row("{c1}", ("Uses", USES, "")))
    assert not [d for d in compare_connectors_declared_observed(c, CONN_MDG, namespace=NS)
                if d.kind == DRIFT_CONNECTOR_NAME_NOT_BOUND]


def test_connector_base_type_mismatch_is_reported():
    c = _conn_census([conn("{c1}", "Dependency", "Uses")],
                     stereo_row("{c1}", ("Uses", USES, "")))
    found = [d for d in compare_connectors_declared_observed(c, CONN_MDG, namespace=NS)
             if d.kind == DRIFT_METACLASS_MISMATCH]
    assert len(found) == 1
    assert "declares base type Association" in found[0].detail


def test_qualified_name_with_no_fqname_is_its_own_finding_with_guids():
    """`Name=WBA::Uses` and no `FQName=`: a data defect the build stops on."""
    c = _conn_census(
        [conn("{c1}", "Association", "Uses"), conn("{c2}", "Association", "Uses"),
         conn("{c3}", "Association", "Uses")],
        stereo_row("{c1}", ("WBA::Uses", "", "{s1}")),
        stereo_row("{c2}", ("WBA::Uses", "", "{s2}")),
        stereo_row("{c3}", ("Uses", USES, "{s3}")),
    )
    drifts = compare_connectors_declared_observed(c, CONN_MDG, namespace=NS)
    found = [d for d in drifts if d.kind == DRIFT_CONNECTOR_UNBOUND]
    assert len(found) == 1
    assert found[0].subject == "WBA::Uses"
    assert found[0].guids == ("{c1}", "{c2}")
    # Distinct from ordinary ad hoc use: not also reported as undeclared.
    assert (DRIFT_OBSERVED_UNDECLARED, "WBA::Uses") not in _kinds(drifts)
    # Still counted, as ad hoc, so the totals stay whole.
    assert c.provenance_split() == {"profile_bound": 1, "ad_hoc": 2}


def test_a_bound_connector_stereotype_is_not_unbound():
    c = _conn_census([conn("{c1}", "Association", "Uses")],
                     stereo_row("{c1}", ("Uses", USES, "{s1}")))
    assert not c.unbound_qualified
    assert not [d for d in compare_connectors_declared_observed(c, CONN_MDG, namespace=NS)
                if d.kind == DRIFT_CONNECTOR_UNBOUND]


def test_plain_ad_hoc_connector_is_not_unbound():
    c = _conn_census([conn("{c1}", "Generalization", "extends")],
                     stereo_row("{c1}", ("extends", "", "{s1}")))
    assert not c.unbound_qualified


def test_unbound_qualified_name_in_the_bare_column_is_found_too():
    c = _conn_census([conn("{c1}", "Association", "WBA::Uses")])
    assert c.unbound_qualified == {"WBA::Uses": {"{c1}"}}


def test_connector_tags_resolve_through_the_connector_id():
    connectors = [conn("{c1}", "Association", "Uses", cid=11),
                  conn("{c2}", "Association", "Uses", cid="12")]
    c = _conn_census(connectors,
                     stereo_row("{c1}", ("Uses", USES, "")),
                     stereo_row("{c2}", ("Uses", USES, "")))
    tags = [{"ElementID": 11, "Property": "slaTier", "VALUE": "Gold"},
            {"ElementID": "12", "Property": "slaTier", "VALUE": ""},
            {"ElementID": 99, "Property": "slaTier", "VALUE": "Gold"},
            {"ElementID": None, "Property": "slaTier", "VALUE": "Gold"}]
    stats = tag_coverage(c.entities[0], tags, connector_guid_of(connectors))
    assert [(s.tag, s.present, s.populated) for s in stats] == [("slaTier", 2, 1)]


def test_connector_tag_populated_but_never_declared_is_reported():
    key = USES + "|Association"
    c = _conn_census([conn("{c1}", "Association", "Uses")],
                     stereo_row("{c1}", ("Uses", USES, "")))
    st = TagStat(tag="costCentre", populated=1)
    st.values.update(["4410"])
    found = [d for d in compare_connectors_declared_observed(c, CONN_MDG, {key: [st]},
                                                             namespace=NS)
             if d.kind == DRIFT_TAG_OBSERVED_UNDECLARED]
    assert [(d.subject, d.detail) for d in found] == [
        ("Uses.costCentre", "populated on 1 connector(s), not declared")]


def test_connector_tag_declared_but_never_populated_is_reported():
    key = USES + "|Association"
    c = _conn_census([conn("{c1}", "Association", "Uses")],
                     stereo_row("{c1}", ("Uses", USES, "")))
    st = TagStat(tag="slaTier", present=1)
    found = [d for d in compare_connectors_declared_observed(c, CONN_MDG, {key: [st]},
                                                             namespace=NS)
             if d.kind == DRIFT_TAG_NEVER_POPULATED]
    assert len(found) == 1
    assert found[0].subject == "Uses.slaTier"
    assert "present on 1 connector(s), populated on none" in found[0].detail


def test_connector_enum_value_outside_the_declared_domain_is_reported():
    key = USES + "|Association"
    c = _conn_census([conn("{c1}", "Association", "Uses")],
                     stereo_row("{c1}", ("Uses", USES, "")))
    st = TagStat(tag="slaTier", present=1, populated=1)
    st.values.update(["Bronze"])
    kinds = _kinds(compare_connectors_declared_observed(c, CONN_MDG, {key: [st]}, namespace=NS))
    assert (DRIFT_ENUM_OBSERVED_UNDECLARED, "Uses.slaTier") in kinds
    assert (DRIFT_ENUM_DECLARED_UNUSED, "Uses.slaTier") in kinds


def test_connector_drift_output_is_deterministic():
    c = _conn_census([conn("{c1}", "Generalization", "extends"),
                      conn("{c2}", "Association", "WBA::Uses")])
    assert (compare_connectors_declared_observed(c, CONN_MDG)
            == compare_connectors_declared_observed(c, CONN_MDG))


def test_connector_census_does_not_change_the_element_path():
    """Element findings are the same whether or not the MDG lists connectors."""
    c = _census_of([obj("{1}", "Class", "WBADataAsset")],
                   [stereo_row("{1}", ("WBADataAsset", "%s::WBADataAsset" % NS, ""))])
    assert [d for d in compare_declared_observed(c, MDG)] == [
        Drift(DRIFT_DECLARED_UNUSED, "WBAGovernedElement",
              "declared in the technology, no instances in the repository")]


# --------------------------------------------------------------------------
# Elements carrying two declared stereotypes (APT-2026-0304)
# --------------------------------------------------------------------------

def test_element_with_two_declared_stereotypes_is_its_own_finding_with_guids():
    c = _census_of(
        [obj("{1}", "Class", "WBADataAsset"), obj("{2}", "Class", "WBADataAsset"),
         obj("{3}", "Class", "WBADataAsset")],
        [stereo_row("{1}", ("WBADataAsset", "%s::WBADataAsset" % NS, ""),
                    ("WBAGovernedElement", "%s::WBAGovernedElement" % NS, "")),
         stereo_row("{2}", ("WBAGovernedElement", "%s::WBAGovernedElement" % NS, ""),
                    ("WBADataAsset", "%s::WBADataAsset" % NS, "")),
         stereo_row("{3}", ("WBADataAsset", "%s::WBADataAsset" % NS, ""))])
    found = [d for d in compare_declared_observed(c, MDG)
             if d.kind == DRIFT_ELEMENT_MULTIPLE_DECLARED]
    assert len(found) == 1
    assert found[0].subject == "WBADataAsset + WBAGovernedElement"
    assert found[0].guids == ("{1}", "{2}")


def test_a_declared_plus_a_foreign_stereotype_is_not_a_doubly_declared_element():
    c = _census_of(
        [obj("{1}", "Class", "WBADataAsset")],
        [stereo_row("{1}", ("WBADataAsset", "%s::WBADataAsset" % NS, ""),
                    ("Note", "TOGAF::Note", ""))])
    assert c.multi_stereotype_guids == {"{1}"}
    assert not [d for d in compare_declared_observed(c, MDG)
                if d.kind == DRIFT_ELEMENT_MULTIPLE_DECLARED]

#!/usr/bin/env python3
"""Tests for the binding measurement tool.

Run from the repository root:

    python -m pytest ea-diagram-composition/tools/test_measure_binding.py -q

Two kinds of test, kept apart on purpose.

**Synthetic tests** build a tiny SQLite model in a temp directory with the three
tables the tool reads. They need no Sparx install, no EA and no example model,
and they carry the rules: the height sign, what "adjacent" means, low-n
reporting, technology attribution. Each is written so that the bug it guards
against FAILS it - a test that passes with the bug present is decoration.

**Example-model tests** run the tool against Sparx's own `EAExample.qea` and
compare with the numbers recorded in the shipped bindings. They SKIP when the
model is absent, the way `tests/benchmark/corpus.py` skips when the research
tree is missing: a machine without EA has not failed, it has nothing to measure.
Exact pins additionally require the model to look like the one they were taken
from (EA 17.1 build 1716, 1,129 diagrams); a different release skips those and
keeps the tolerance checks.

WHAT "REPRODUCES" MEANS HERE
----------------------------
The recorded figures do not come with a written method, and this tool's
adjacency rule is deliberately stricter than the one that evidently produced
them (see the module docstring of measure_binding). Sizes and modes reproduce
exactly. Pair counts and medians reproduce to within a small tolerance for
ArchiMate and the BPMN horizontal gap, and NOT for the BPMN vertical gap. The
tests state the recorded value, the tolerance and the measured value, rather
than loosening a bound until it passes.
"""
from __future__ import annotations

import collections
import hashlib
import re
import sqlite3
import sys
from pathlib import Path

import pytest

_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

import measure_binding as mb  # noqa: E402
from measure_binding import Rect  # noqa: E402


# ---------------------------------------------------------------------------
# A tiny model, built the way EA stores one
# ---------------------------------------------------------------------------

def build_model(tmp_path, diagrams):
    """Write a minimal .qea. `diagrams`: (id, Diagram_Type, StyleEx, objects[, name]).

    Each object is `(object_type, stereotype, left, top, right, bottom)` in
    EA's stored convention: `top` and `bottom` negative, `top > bottom`.
    """
    path = tmp_path / "model.qea"
    conn = sqlite3.connect(path)
    conn.executescript("""
        CREATE TABLE t_diagram (Diagram_ID INTEGER, Diagram_Type TEXT, StyleEx TEXT,
            Name TEXT);
        CREATE TABLE t_object (Object_ID INTEGER, Object_Type TEXT, Stereotype TEXT);
        CREATE TABLE t_diagramobjects (Diagram_ID INTEGER, Object_ID INTEGER,
            RectTop INTEGER, RectLeft INTEGER, RectRight INTEGER, RectBottom INTEGER);
    """)
    oid = 0
    for did, dtype, style_ex, objects, *name in diagrams:
        conn.execute("INSERT INTO t_diagram VALUES (?,?,?,?)",
                     (did, dtype, style_ex, name[0] if name else f"Diagram {did}"))
        for otype, stereo, left, top, right, bottom in objects:
            oid += 1
            conn.execute("INSERT INTO t_object VALUES (?,?,?)", (oid, otype, stereo))
            conn.execute("INSERT INTO t_diagramobjects VALUES (?,?,?,?,?,?)",
                         (did, oid, top, left, right, bottom))
    conn.commit()
    conn.close()
    return str(path)


def box(stereo, left, top, w=100, h=70, otype="Class"):
    """An element whose top-left is (left, top); `top` is a negative y."""
    return (otype, stereo, left, top, left + w, top - h)


def tag(tech, dtype):
    return f"HandDraw=0;MDGDgm={tech}::{dtype};Theme=:119;"


def items(*specs):
    return [mb.Item(i, s, ot, Rect(l, t, r, b))
            for i, (ot, s, l, t, r, b) in enumerate(specs)]


# ---------------------------------------------------------------------------
# Sign convention
# ---------------------------------------------------------------------------

def test_height_is_top_minus_bottom():
    """EA stores top=-10, bottom=-80 for a box 70 tall.

    `bottom - top` would give -70 and would be wrong everywhere; a test that
    only asserted `height > 0` would pass for `abs(bottom - top)` too, so this
    pins the sign of the arithmetic itself.
    """
    r = Rect(left=50, top=-10, right=150, bottom=-80)
    assert r.height == 70
    assert r.width == 100
    assert (r.bottom - r.top) == -70


def test_size_read_from_database_uses_the_stored_convention(tmp_path):
    objs = [box("Task", 0, -10, 100, 70) for _ in range(12)]
    path = build_model(tmp_path, [(1, "Analysis", tag("T", "D"), objs)])
    m = mb.measure_binding(path, "T", "D")
    assert m.sizes["Task"].mode == (100, 70)
    assert m.sizes["Task"].median == (100, 70)


def test_vertical_gap_is_measured_downward_and_is_positive():
    """A above B: A.bottom=-80 sits 40 above B.top=-120."""
    a = ("Class", "S", 0, -10, 100, -80)
    b = ("Class", "S", 0, -120, 100, -190)
    gaps, _ = mb.nearest_neighbor_gaps(items(a, b), "v")
    assert gaps == [40]


def test_vertical_gap_does_not_run_upward():
    """B is below A, so B has no neighbor below it and A's is 40, not two.

    With the axis inverted (gap = B.bottom - A.top) the pair would be measured
    from the wrong side, or once per direction.
    """
    a = ("Class", "S", 0, -10, 100, -80)
    b = ("Class", "S", 0, -120, 100, -190)
    gaps, _ = mb.nearest_neighbor_gaps(items(b, a), "v")   # order must not matter
    assert gaps == [40]


# ---------------------------------------------------------------------------
# What "adjacent" means
# ---------------------------------------------------------------------------

def test_horizontal_gap_between_row_mates():
    gaps, _ = mb.nearest_neighbor_gaps(
        items(box("S", 0, -10), box("S", 140, -10)), "h")
    assert gaps == [40]


def test_diagonal_neighbors_share_no_row_and_are_not_paired():
    """B is entirely below A's row, so it is not to A's right."""
    gaps, _ = mb.nearest_neighbor_gaps(
        items(box("S", 0, -10), box("S", 140, -200)), "h")
    assert gaps == []


def test_a_third_element_between_two_makes_them_non_adjacent():
    """A, C, B in a row: A-C and C-B are gaps; A-B (a 240 span) is not."""
    row = items(box("S", 0, -10), box("S", 140, -10), box("S", 280, -10))
    gaps, _ = mb.nearest_neighbor_gaps(row, "h")
    assert sorted(gaps) == [40, 40]
    assert 240 not in gaps


def test_a_note_between_two_elements_also_separates_them():
    """The intervening object need not be a measured element.

    Dropping non-elements before looking for neighbors would report A-B across
    the note; the pair is dropped instead, not reassigned.
    """
    objs = items(box("S", 0, -10),
                 box(None, 140, -10, otype="Note"),
                 box("S", 280, -10))
    gaps, _ = mb.nearest_neighbor_gaps(objs, "h")
    assert gaps == []


def test_elements_in_different_containers_are_not_adjacent():
    """Two lanes: the distance across a lane boundary is not item spacing."""
    lane_a = ("ActivityPartition", "Lane", -5, 0, 305, -100)
    lane_b = ("ActivityPartition", "Lane", 400, 0, 705, -100)
    left = box("S", 0, -10, 100, 70)
    right = box("S", 420, -10, 100, 70)
    gaps, _ = mb.nearest_neighbor_gaps(items(lane_a, lane_b, left, right), "h")
    assert gaps == []


def test_siblings_inside_one_container_are_measured_and_the_container_is_not():
    frame = ("ActivityPartition", "Lane", -5, 0, 500, -100)
    objs = items(frame, box("S", 0, -10), box("S", 140, -10))
    gaps, _ = mb.nearest_neighbor_gaps(objs, "h")
    assert gaps == [40]


def test_touching_elements_are_counted_not_measured():
    gaps, non_positive = mb.nearest_neighbor_gaps(
        items(box("S", 0, -10), box("S", 100, -10)), "h")
    assert gaps == []
    assert non_positive == 1


def test_furniture_and_unstereotyped_objects_are_never_endpoints():
    objs = items(box(None, 0, -10, otype="Text"), box("S", 140, -10))
    gaps, _ = mb.nearest_neighbor_gaps(objs, "h")
    assert gaps == []


def test_endpoint_stereotypes_narrows_the_pairs():
    objs = items(box("Task", 0, -10), box("Task", 140, -10),
                 box("Data", 0, -300), box("Data", 100, -300))
    gaps, _ = mb.nearest_neighbor_gaps(objs, "h", endpoint_stereotypes={"Task"})
    assert gaps == [40]


# ---------------------------------------------------------------------------
# Low n, and modes that are not modes
# ---------------------------------------------------------------------------

def test_a_small_sample_is_flagged_low_n_not_presented_as_a_measurement(tmp_path):
    row = [box("S", i * 140, -10) for i in range(4)]        # 3 gaps, all 40
    path = build_model(tmp_path, [(1, "Analysis", tag("T", "D"), row)])
    m = mb.measure_binding(path, "T", "D")
    assert m.h_gap.n == 3
    assert m.h_gap.low_n is True
    assert m.sizes["S"].low_n is True
    text = mb.format_binding_yaml(m)
    assert "LOW-N" in text
    assert not re.search(r"^\s*item_gap_x:", text, re.M), \
        "a low-n gap must be commented out, not emitted as a value"
    assert not re.search(r"^\s*default:", text, re.M)


def test_an_adequate_sample_is_emitted_with_its_n(tmp_path):
    path = build_model(tmp_path, [
        (i, "Analysis", tag("T", "D"), [box("S", j * 140, -10) for j in range(5)])
        for i in (1, 2, 3)])                                # 3 x 4 = 12 gaps
    m = mb.measure_binding(path, "T", "D")
    assert m.h_gap.n == 12 and not m.h_gap.low_n
    text = mb.format_binding_yaml(m)
    line = next(l for l in text.splitlines() if re.match(r"\s*item_gap_x:", l))
    assert "n=12" in line
    assert "n=15" in next(l for l in text.splitlines() if re.match(r"\s*default:", l))


def test_min_sample_is_adjustable(tmp_path):
    row = [box("S", i * 140, -10) for i in range(4)]
    path = build_model(tmp_path, [(1, "Analysis", tag("T", "D"), row)])
    assert mb.measure_binding(path, "T", "D", min_sample=3).h_gap.low_n is False


def test_all_different_sizes_have_no_mode_rather_than_the_first_one(tmp_path):
    """Ten annotations, ten sizes: `Counter.most_common` would name one."""
    notes = [box("Annotation", i * 200, -10, 100 + i, 50 + i, otype="Note")
             for i in range(10)]
    path = build_model(tmp_path, [(1, "Analysis", tag("T", "D"), notes)])
    st = mb.measure_binding(path, "T", "D").sizes["Annotation"]
    assert st.mode is None
    assert st.distinct == 10
    assert st.mode_count == 1
    assert "no dominant size" in mb.format_binding_yaml(
        mb.measure_binding(path, "T", "D"))


def test_a_tied_gap_mode_is_reported_as_tied():
    stat = mb.gap_stat([10, 10, 20, 20, 30])
    assert stat.mode is None
    assert stat.tied_modes == (10, 20)
    assert stat.mode_count == 2


def test_a_mode_carries_its_own_count():
    stat = mb.gap_stat([40] * 4 + [30, 50, 60, 70, 80, 90, 100], min_sample=10)
    assert (stat.n, stat.mode, stat.mode_count) == (11, 40, 4)


def test_fixed_shape_stereotypes_do_not_outvote_the_default_box(tmp_path):
    events = [box("Event", i * 60, -10, 30, 30) for i in range(20)]
    tasks = ([box("Task", i * 200, -100, 110, 60) for i in range(6)]
             + [box("Task", i * 200, -300, 90, 50) for i in range(5)])
    path = build_model(tmp_path, [(1, "Analysis", tag("T", "D"), events + tasks)])
    m = mb.measure_binding(path, "T", "D")
    assert m.fixed_shape == ("Event",)
    assert m.default_size.mode == (110, 60)


# ---------------------------------------------------------------------------
# The two adjacency rules
# ---------------------------------------------------------------------------

def test_the_default_rule_is_strict(tmp_path):
    path = build_model(tmp_path, [(1, "Analysis", tag("T", "D"), [box("S", 0, -10)])])
    assert mb.measure_binding(path, "T", "D").rule == "strict"


def test_an_unknown_rule_is_refused(tmp_path):
    path = build_model(tmp_path, [(1, "Analysis", tag("T", "D"), [box("S", 0, -10)])])
    with pytest.raises(mb.MeasureError, match="rule must be one of"):
        mb.measure_binding(path, "T", "D", rule="loose")
    with pytest.raises(ValueError):
        mb.nearest_neighbor_gaps([], "h", rule="loose")


def _two_lanes():
    lane_a = ("ActivityPartition", "Lane", -5, 0, 305, -100)
    lane_b = ("ActivityPartition", "Lane", 400, 0, 705, -100)
    return items(lane_a, lane_b, box("S", 0, -10), box("S", 420, -10))


def test_historical_rule_pairs_across_a_container_boundary_strict_does_not():
    """The 4 h / 11 v ArchiMate pairs the two rules disagree about, in miniature."""
    assert mb.nearest_neighbor_gaps(_two_lanes(), "h", rule="strict")[0] == []
    assert mb.nearest_neighbor_gaps(_two_lanes(), "h", rule="historical")[0] == [320]


def test_historical_rule_ignores_a_non_endpoint_between_two_elements():
    objs = items(box("S", 0, -10),
                 box(None, 140, -10, otype="Note"),
                 box("S", 280, -10))
    assert mb.nearest_neighbor_gaps(objs, "h", rule="strict")[0] == []
    assert mb.nearest_neighbor_gaps(objs, "h", rule="historical")[0] == [180]


def test_both_rules_agree_when_nothing_crosses_a_boundary_or_intervenes():
    row = items(box("S", 0, -10), box("S", 140, -10), box("S", 280, -10))
    assert (mb.nearest_neighbor_gaps(row, "h", rule="strict")
            == mb.nearest_neighbor_gaps(row, "h", rule="historical"))


def test_historical_rule_still_ignores_containers_as_endpoints_and_touching_pairs():
    frame = ("ActivityPartition", "Lane", -5, 0, 500, -100)
    touching = items(box("S", 0, -10), box("S", 100, -10))
    assert mb.nearest_neighbor_gaps(items(frame, box("S", 0, -10)), "h",
                                    rule="historical")[0] == []
    assert mb.nearest_neighbor_gaps(touching, "h", rule="historical") == ([], 0)


def test_the_yaml_says_which_rule_produced_it(tmp_path):
    row = [box("S", i * 140, -10) for i in range(12)]
    path = build_model(tmp_path, [(1, "Analysis", tag("T", "D"), row)])
    assert "rule: strict" in mb.format_binding_yaml(mb.measure_binding(path, "T", "D"))
    assert "rule: HISTORICAL" in mb.format_binding_yaml(
        mb.measure_binding(path, "T", "D", rule="historical"))


# ---------------------------------------------------------------------------
# Technology and diagram-type resolution, and attribution
# ---------------------------------------------------------------------------

def test_a_guessed_technology_id_raises_and_names_the_real_one(tmp_path):
    path = build_model(tmp_path, [
        (1, "Analysis", tag("BPMN2.0", "Business Process"), [box("Activity", 0, -10)])])
    with pytest.raises(mb.UnknownTechnology, match=r"BPMN2\.0"):
        mb.measure_binding(path, "BPMN2")


def test_a_guessed_diagram_type_raises_and_lists_the_real_ones(tmp_path):
    path = build_model(tmp_path, [
        (1, "Analysis", tag("BPMN2.0", "Business Process"), [box("Activity", 0, -10)])])
    with pytest.raises(mb.UnknownDiagramType, match="Business Process"):
        mb.measure_binding(path, "BPMN2.0", "BusinessProcess")


def test_mdg_tag_parsing_keeps_spaces_and_survives_an_empty_value():
    assert mb.parse_mdg("A=1;MDGDgm=BPMN2.0::Business Process;B=2;") == \
        ("BPMN2.0", "Business Process")
    assert mb.parse_mdg("MDGDgm=;Theme=:1;") == ("", "")
    assert mb.parse_mdg(None) == ("", "")
    assert mb.parse_mdg("XMDGDgm=T::D;") == ("", "")


def test_untagged_diagram_is_attributed_by_type_and_exclusive_stereotypes(tmp_path):
    tagged = [box("Capability", 0, -10)]
    untagged = [box("Capability", 0, -10), box("Capability", 140, -10)]
    path = build_model(tmp_path, [
        (1, "Logical", tag("Arch", "Business"), tagged),
        (2, "Logical", "MDGDgm=;Theme=:119;", untagged),       # empty tag
        (3, "Logical", "Theme=:119;", untagged),                # no key at all
    ])
    m = mb.measure_binding(path, "Arch")
    assert (m.diagrams, m.diagrams_by_mdg, m.diagrams_by_fallback) == (3, 1, 2)


def test_fallback_requires_the_matching_diagram_type(tmp_path):
    path = build_model(tmp_path, [
        (1, "Logical", tag("Arch", "Business"), [box("Capability", 0, -10)]),
        (2, "Activity", "MDGDgm=;", [box("Capability", 0, -10)]),
    ])
    assert mb.measure_binding(path, "Arch").diagrams_by_fallback == 0


def test_fallback_ignores_stereotypes_another_technology_also_uses(tmp_path):
    """BPMN and BPMN 1.1 both store `Activity`; that is not evidence."""
    path = build_model(tmp_path, [
        (1, "Analysis", tag("New", "Process"), [box("Activity", 0, -10)]),
        (2, "Analysis", tag("Old", "Process"), [box("Activity", 0, -10)]),
        (3, "Analysis", "MDGDgm=;", [box("Activity", 0, -10)]),
    ])
    assert mb.measure_binding(path, "New").diagrams_by_fallback == 0


def test_fallback_never_overrides_an_explicit_tag_for_another_technology(tmp_path):
    path = build_model(tmp_path, [
        (1, "Logical", tag("Arch", "Business"), [box("Capability", 0, -10)]),
        (2, "Logical", tag("Other", "Thing"), [box("Capability", 0, -10)]),
    ])
    assert mb.measure_binding(path, "Arch").diagrams == 1


def test_diagram_type_scope_excludes_other_types(tmp_path):
    path = build_model(tmp_path, [
        (1, "Analysis", tag("T", "One"), [box("S", 0, -10)]),
        (2, "Analysis", tag("T", "Two"), [box("S", 0, -10), box("S", 140, -10)]),
    ])
    assert mb.measure_binding(path, "T", "One").sizes["S"].n == 1
    assert mb.measure_binding(path, "T").sizes["S"].n == 3


def test_stereotype_prefix_is_measured_and_stripped_in_the_yaml(tmp_path):
    row = [box("Arch_Thing", i * 140, -10) for i in range(12)]
    path = build_model(tmp_path, [(1, "Logical", tag("Arch", "Biz"), row)])
    m = mb.measure_binding(path, "Arch", "Biz")
    assert m.stereotype_prefix == "Arch_"
    assert m.prefix_share == (12, 12)
    text = mb.format_binding_yaml(m)
    assert "stereotype_prefix: Arch_" in text


def test_no_shared_prefix_is_reported_as_empty(tmp_path):
    row = [box("Activity", i * 140, -10) for i in range(6)]
    path = build_model(tmp_path, [(1, "Analysis", tag("T", "D"), row)])
    assert mb.measure_binding(path, "T", "D").stereotype_prefix == ""


# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------

def test_yaml_parses_and_every_emitted_number_carries_its_n(tmp_path):
    yaml = pytest.importorskip("yaml")
    objs = ([box("Task", i * 140, -10, 110, 60) for i in range(4)]
            + [box("Task", i * 140, -200, 110, 60) for i in range(4)])
    path = build_model(tmp_path, [(i, "Analysis", tag("T", "Big Type"), objs)
                                  for i in (1, 2, 3)])
    text = mb.format_binding_yaml(mb.measure_binding(path, "T", "Big Type"))
    doc = yaml.safe_load(text)
    assert doc["technology"] == "T"
    spec = doc["diagram_types"]["Big Type"]
    assert spec["sizing"]["default"] == {"w": 110, "h": 60}
    assert spec["spacing"]["item_gap_x"] == 30      # 140 pitch - 110 wide
    assert spec["spacing"]["item_gap_y"] == 130     # -70 bottom to -200 top
    for line in text.splitlines():
        if re.match(r"\s*(default|item_gap_[xy]|[A-Z]\w*):\s*[\d{]", line):
            assert re.search(r"\bn=\d+", line), f"number without n: {line!r}"


def test_the_source_of_a_measurement_is_stated(tmp_path):
    path = build_model(tmp_path, [
        (1, "Analysis", tag("T", "D"), [box("S", 0, -10)])])
    text = mb.format_binding_yaml(mb.measure_binding(path, "T", "D"))
    assert "1 diagrams: 1 by MDGDgm tag, 0 by Diagram_Type fallback" in text


# ---------------------------------------------------------------------------
# Distortion 1: one diagram must not speak for the notation
# ---------------------------------------------------------------------------

def _row_diagram(did, boxes, *, pitch=140, name=None, tech="T", dtype="D", stereo="S"):
    """A one-row diagram of `boxes` boxes: `boxes - 1` horizontal gaps of pitch-100."""
    objs = [box(stereo, i * pitch, -10) for i in range(boxes)]
    return (did, "Analysis", tag(tech, dtype), objs, name or f"Diagram {did}")


def test_gap_stat_names_the_diagram_that_supplies_most_of_the_population():
    gaps = [73] * 11 + [30, 40, 50, 60, 90, 120]
    sources = [7] * 11 + [1, 2, 3, 4, 5, 6]
    stat = mb.gap_stat(gaps, sources=sources, names={7: "Generated Overview"})
    assert stat.n == 17
    assert (stat.top_diagram, stat.top_diagram_name, stat.top_count) == \
        (7, "Generated Overview", 11)
    assert stat.top_share == pytest.approx(11 / 17)
    assert stat.diagrams == 7
    assert stat.concentrated is True
    assert stat.median == 73, "the pooled median stays on the result for inspection"


def test_exactly_half_from_one_diagram_is_not_more_than_half():
    stat = mb.gap_stat([10] * 6 + list(range(20, 26)), sources=[1] * 6 + [2, 3, 4, 5, 6, 7])
    assert stat.top_count == 6 and stat.n == 12
    assert stat.concentrated is False
    six_of_eleven = mb.gap_stat([10] * 6 + list(range(20, 25)),
                                sources=[1] * 6 + [2, 3, 4, 5, 6])
    assert six_of_eleven.concentrated is True


def test_without_sources_no_concentration_is_claimed():
    stat = mb.gap_stat([40] * 12)
    assert (stat.diagrams, stat.top_diagram, stat.concentrated) == (0, None, False)


def test_sources_must_cover_every_gap():
    with pytest.raises(ValueError):
        mb.gap_stat([1, 2, 3], sources=[1, 2])


def test_a_diagram_supplying_most_gaps_leaves_the_yaml_without_a_value(tmp_path):
    """The Timing case in miniature: 11 of 14 gaps from one diagram.

    Pooled without weighting, the median is that diagram's own spacing and the
    old tool emitted it as `item_gap_x`.
    """
    path = build_model(tmp_path, [
        _row_diagram(1, 12, name="Generated Overview"),          # 11 gaps of 40
        _row_diagram(2, 2, pitch=190), _row_diagram(3, 2, pitch=190),
        _row_diagram(4, 2, pitch=190),                           # 3 gaps of 90
    ])
    m = mb.measure_binding(path, "T", "D")
    assert (m.h_gap.n, m.h_gap.top_count, m.h_gap.diagrams) == (14, 11, 4)
    assert m.h_gap.concentrated and not m.h_gap.low_n
    assert m.h_gap.median == 40
    text = mb.format_binding_yaml(m)
    assert not re.search(r"^\s*item_gap_x:", text, re.M), \
        "a concentrated gap must not be stated as a value"
    line = next(l for l in text.splitlines() if "item_gap_x" in l)
    assert line.lstrip().startswith("#")
    assert "CONCENTRATED" in line
    assert '"Generated Overview" (id 1)' in line
    assert "11 of 14" in line and "79%" in line and "n=14" in line


def test_the_same_gaps_spread_over_diagrams_are_stated(tmp_path):
    """Control for the test above: 14 gaps, no diagram over half."""
    path = build_model(tmp_path, [_row_diagram(i, 6) for i in (1, 2, 3)]
                       + [_row_diagram(4, 3)])              # 5 + 5 + 5 + 2 gaps
    m = mb.measure_binding(path, "T", "D")
    assert m.h_gap.n == 17 and not m.h_gap.concentrated
    text = mb.format_binding_yaml(m)
    line = next(l for l in text.splitlines() if re.match(r"\s*item_gap_x:", l))
    assert "n=17" in line and "from 4 diagrams" in line


def test_a_family_with_a_single_diagram_can_state_no_gap(tmp_path):
    path = build_model(tmp_path, [_row_diagram(1, 15)])
    m = mb.measure_binding(path, "T", "D")
    assert m.h_gap.n == 14 and m.h_gap.concentrated and m.h_gap.top_share == 1.0
    assert not re.search(r"^\s*item_gap_x:", mb.format_binding_yaml(m), re.M)


def test_the_concentration_threshold_can_be_relaxed_by_the_caller(tmp_path):
    path = build_model(tmp_path, [
        _row_diagram(1, 12), _row_diagram(2, 2), _row_diagram(3, 2), _row_diagram(4, 2)])
    assert mb.measure_binding(path, "T", "D", max_diagram_share=0.9).h_gap.concentrated is False


def test_concentration_is_judged_per_axis(tmp_path):
    """A horizontal population that is spread does not excuse a vertical one that is not."""
    column = [box("S", 0, -10 - i * 140) for i in range(12)]      # 11 vertical gaps
    path = build_model(tmp_path, [
        (1, "Analysis", tag("T", "D"), column, "Tall"),
        _row_diagram(2, 4), _row_diagram(3, 4), _row_diagram(4, 4), _row_diagram(5, 4)])
    m = mb.measure_binding(path, "T", "D")
    assert m.h_gap.n == 12 and not m.h_gap.concentrated
    assert m.v_gap.n == 11 and m.v_gap.concentrated


# ---------------------------------------------------------------------------
# Distortion 2: a concept that agrees with the default must still appear
# ---------------------------------------------------------------------------

def _value_type_model(tmp_path):
    """`Value` is 90x70 in 7 of 10; `Block` has ten different sizes.

    The pooled mode is 90x70 - `Value`'s size - so the old formatter, which
    skipped any concept whose mode equals the default, dropped `Value`.
    """
    values = ([box("Value", i * 200, -10, 90, 70) for i in range(7)]
              + [box("Value", i * 200, -100, 80 + i, 60) for i in range(3)])
    blocks = [box("Block", i * 200, -300, 100 + 5 * i, 50 + 3 * i) for i in range(10)]
    return build_model(tmp_path, [(1, "Analysis", tag("T", "D"), values + blocks)])


def test_a_concept_whose_mode_equals_the_default_is_listed_with_its_own_n(tmp_path):
    m = mb.measure_binding(_value_type_model(tmp_path), "T", "D")
    assert m.default_size.mode == (90, 70)
    assert m.sizes["Value"].mode == (90, 70) and "Value" not in m.fixed_shape
    text = mb.format_binding_yaml(m)
    line = next(l for l in text.splitlines() if re.match(r"\s*Value:", l))
    assert "{w: 90, h: 70}" in line and "n=10" in line
    assert "agrees with the default" in line


def test_the_default_says_whose_size_it_is(tmp_path):
    m = mb.measure_binding(_value_type_model(tmp_path), "T", "D")
    assert m.default_supply == {"Value": 7}
    text = mb.format_binding_yaml(m)
    line = next(l for l in text.splitlines() if "default {w: 90, h: 70}" in l)
    assert "Value's size" in line and "7 of the 7" in line


def test_a_default_shared_by_several_concepts_is_not_attributed_to_one(tmp_path):
    objs = ([box("A", i * 200, -10, 90, 70) for i in range(4)]
            + [box("B", i * 200, -100, 90, 70) for i in range(4)]
            + [box("C", i * 200, -200, 40 + i, 30) for i in range(12)])
    path = build_model(tmp_path, [(1, "Analysis", tag("T", "D"), objs)])
    text = mb.format_binding_yaml(mb.measure_binding(path, "T", "D"))
    assert "'s size" not in text


def test_a_low_n_concept_that_agrees_with_the_default_is_still_shown(tmp_path):
    objs = ([box("Block", i * 200, -10, 90, 70) for i in range(8)]
            + [box("Block", i * 200, -100, 60 + i, 40) for i in range(6)]
            + [box("Rare", 0, -300, 90, 70)])
    path = build_model(tmp_path, [(1, "Analysis", tag("T", "D"), objs)])
    text = mb.format_binding_yaml(mb.measure_binding(path, "T", "D"))
    assert re.search(r"^\s*# Rare: .*LOW-N.*n=1", text, re.M)


# ---------------------------------------------------------------------------
# Distortion 3: furniture is not furniture when the diagram is made of it
# ---------------------------------------------------------------------------

def _tile_grid(stereo, *, cols=4, rows=3, otype="Text"):
    """A framework page: a grid of `otype` tiles, 130x80 with a 5 / 28 gap."""
    return [(otype, stereo, c * 135, -9 - r * 108, c * 135 + 130, -9 - r * 108 - 80)
            for r in range(rows) for c in range(cols)]


def _framework_model(tmp_path, tile_stereo="Tile", other_tagged=()):
    tiles = _tile_grid(tile_stereo) + [box("Doc", 600, -9, 130, 80, otype="Artifact")]
    diagrams = [(1, "Logical", tag("Fw", "Framework"), tiles, "Framework Page")]
    diagrams += list(other_tagged)
    return build_model(tmp_path, diagrams)


def test_text_tiles_carrying_the_technologys_own_stereotype_are_content(tmp_path):
    """The UAF Framework case: 45 of 47 objects are `Text`, and it reported n=0."""
    m = mb.measure_binding(_framework_model(tmp_path), "Fw")
    assert m.content_promoted == {"Text": 12}
    assert m.content_promoted_diagrams == 1
    assert m.h_gap.n > 0 and m.v_gap.n > 0
    assert m.h_gap.median == 5 and m.v_gap.median == 28
    assert m.furniture_majority_diagrams == 0


def test_the_old_reading_of_the_same_diagram_is_n_zero_and_says_so(tmp_path):
    m = mb.measure_binding(_framework_model(tmp_path), "Fw", auto_content=False)
    assert (m.h_gap.n, m.v_gap.n) == (0, 0)
    assert m.furniture_majority_diagrams == 1 and m.furniture_majority_unmeasured == 1
    text = mb.format_binding_yaml(m)
    assert "Furniture note" in text and "--content-type" in text
    assert "no measurable neighbors (n=0); 1 diagram(s)" in text


def test_promoted_content_is_announced_in_the_yaml(tmp_path):
    text = mb.format_binding_yaml(mb.measure_binding(_framework_model(tmp_path), "Fw"))
    assert "Furniture treated as content on 1 diagram(s): Text (12)" in text


def test_a_stereotype_shared_with_another_technology_is_chrome_not_notation(tmp_path):
    """`NavigationCell` tiles sit on many technologies' diagrams; they are chrome."""
    other = (2, "Logical", tag("Other", "Page"),
             _tile_grid("Tile", cols=2, rows=1), "Elsewhere")
    m = mb.measure_binding(_framework_model(tmp_path, other_tagged=[other]), "Fw")
    assert m.content_promoted == {}
    assert m.furniture_majority_diagrams == 1


def test_unstereotyped_text_is_never_promoted_automatically(tmp_path):
    """A page of plain Text is documentation; only the caller can say otherwise."""
    m = mb.measure_binding(_framework_model(tmp_path, tile_stereo=""), "Fw")
    assert m.content_promoted == {}
    assert (m.h_gap.n, m.v_gap.n) == (0, 0)
    assert m.furniture_majority_diagrams == 1


def test_a_minority_of_stereotyped_notes_beside_content_is_still_annotation(tmp_path):
    """A minority furniture type is annotation even when it carries a stereotype."""
    classes = [box("Std", i * 140, -10) for i in range(6)]
    notes = [box("Owned", i * 140, -200, otype="Note") for i in range(3)]
    path = build_model(tmp_path, [(1, "Logical", tag("T", "D"), classes + notes)])
    assert mb.measure_binding(path, "T", "D").content_promoted == {}


def test_the_caller_can_declare_a_furniture_type_to_be_content(tmp_path):
    m = mb.measure_binding(_framework_model(tmp_path, tile_stereo=""), "Fw",
                           content_types={"Text"})
    assert m.content_promoted == {"Text": 12}
    assert m.sizes["Text"].n == 12, "an unstereotyped promoted object is keyed by its type"
    assert m.h_gap.n > 0


def test_promotion_is_off_when_the_caller_turns_it_off(tmp_path):
    m = mb.measure_binding(_framework_model(tmp_path), "Fw", auto_content=False)
    assert m.content_promoted == {}


def test_promote_furniture_leaves_ordinary_annotations_alone():
    objs = items(box("S", 0, -10), box(None, 140, -10, otype="Note"),
                 box(None, 280, -10, otype="Text"))
    out, promoted = mb.promote_furniture(objs)
    assert out == objs and not promoted


def test_a_promoted_object_is_an_endpoint_and_a_plain_note_is_not():
    tiles = [mb.Item(i, "Tile", "Text", Rect(i * 135, -9, i * 135 + 130, -89), content=True)
             for i in range(3)]
    assert mb.nearest_neighbor_gaps(tiles, "h")[0] == [5, 5]
    plain = [mb.Item(i, "Tile", "Text", Rect(i * 135, -9, i * 135 + 130, -89))
             for i in range(3)]
    assert mb.nearest_neighbor_gaps(plain, "h")[0] == []


# ---------------------------------------------------------------------------
# The base notation
# ---------------------------------------------------------------------------

def _plain(dtype, objs, did, name=None):
    """A diagram claiming no technology."""
    return (did, dtype, "MDGDgm=;Theme=:119;", objs, name or f"Plain {did}")


def _uml_model(tmp_path):
    def classes(n, y=-10):
        return [("Class", None, i * 150, y, i * 150 + 100, y - 70) for i in range(n)]
    return build_model(tmp_path, [
        _plain("Logical", classes(4), 1, "Domain Classes"),
        _plain("Logical", classes(3), 2),
        _plain("Use Case", [("Actor", None, 0, -10, 45, -100),
                            ("UseCase", None, 100, -10, 205, -80),
                            ("Note", None, 300, -10, 400, -60)], 3),
        _plain("Custom", classes(2), 4, "A Page"),
        _plain("Analysis", classes(2), 5),
        # mostly stereotyped, untagged: an MDG diagram, not plain UML
        (6, "Logical", "MDGDgm=;", [("Class", "Arch_Thing", 0, -10, 100, -80),
                                    ("Class", "Arch_Thing", 150, -10, 250, -80),
                                    ("Class", None, 300, -10, 400, -80)], "Stereotyped"),
        # tagged: never plain UML
        (7, "Logical", tag("Arch", "Biz"), [("Class", "Arch_Thing", 0, -10, 100, -80)], "Tagged"),
        # furniture only: nothing to measure
        _plain("Logical", [("Text", None, 0, -10, 100, -50)], 8),
    ])


def test_the_base_notation_is_selected_by_absence_of_a_tag_and_of_stereotypes(tmp_path):
    m = mb.measure_binding(_uml_model(tmp_path), mb.BASE_NOTATION)
    assert m.concept_column == "Object_Type"
    assert m.diagrams == m.diagrams_by_base == 5
    assert (m.diagrams_by_mdg, m.diagrams_by_fallback) == (0, 0)


def test_mdg_attribution_cannot_see_the_base_notation_which_is_why_it_has_its_own_path(tmp_path):
    """No tagged UML means no base types to learn: `_attribute` finds nothing."""
    with mb.open_model_copy(_uml_model(tmp_path)) as conn:
        diagrams = mb._load_diagrams(conn)
    assert mb._attribute(diagrams, "UML") == ([], [])


def test_the_concept_of_a_base_notation_element_is_its_object_type(tmp_path):
    m = mb.measure_binding(_uml_model(tmp_path), mb.BASE_NOTATION)
    assert set(m.sizes) == {"Class", "Actor", "UseCase"}
    assert m.sizes["Class"].n == 4 + 3 + 2 + 2
    assert "Note" not in m.sizes and "Text" not in m.sizes


def test_a_stereotyped_element_in_a_plain_diagram_is_keyed_by_its_object_type(tmp_path):
    """`<<entity>>` on a Class is a Class."""
    path = build_model(tmp_path, [_plain("Logical", [
        ("Class", "entity", 0, -10, 100, -80), ("Class", None, 150, -10, 250, -80),
        ("Class", None, 300, -10, 400, -80)], 1)])
    m = mb.measure_binding(path, mb.BASE_NOTATION)
    assert set(m.sizes) == {"Class"} and m.sizes["Class"].n == 3
    assert m.unstereotyped == (2, 3)


def test_nothing_is_excluded_by_default_and_an_exclusion_is_counted(tmp_path):
    """Analysis and Custom are diagram types MDG technologies sit on; they stay."""
    path = _uml_model(tmp_path)
    m = mb.measure_binding(path, mb.BASE_NOTATION)
    assert m.diagrams == 5 and m.excluded_base_types == {}
    assert {"Analysis", "Custom"} <= set(m.diagram_types)
    narrowed = mb.measure_binding(path, mb.BASE_NOTATION,
                                  exclude_base_types={"Analysis", "custom"})
    assert narrowed.diagrams == 3
    assert narrowed.excluded_base_types == {"Analysis": 1, "Custom": 1}
    assert mb.measure_binding(path, mb.BASE_NOTATION,
                              exclude_base_types={"custom"}).diagrams == 4


def test_the_base_notation_diagram_type_is_ea_verbatim_and_a_guess_is_refused(tmp_path):
    path = _uml_model(tmp_path)
    assert mb.measure_binding(path, mb.BASE_NOTATION, "Use Case").diagrams == 1
    with pytest.raises(mb.UnknownDiagramType, match="Use Case"):
        mb.measure_binding(path, mb.BASE_NOTATION, "UseCase")


def test_the_unknown_technology_message_points_at_the_base_notation(tmp_path):
    path = _uml_model(tmp_path)
    with pytest.raises(mb.UnknownTechnology, match="UML"):
        mb.measure_binding(path, "Archimate")


def test_a_real_tag_named_uml_wins_over_the_base_notation(tmp_path):
    path = build_model(tmp_path, [
        (1, "Logical", tag("UML", "Thing"), [box("Widget", 0, -10)]),
        _plain("Logical", [("Class", None, 0, -10, 100, -80)], 2)])
    m = mb.measure_binding(path, "UML")
    assert m.concept_column == "Stereotype" and set(m.sizes) == {"Widget"}


def test_the_base_notation_yaml_states_its_concept_column_and_what_it_left_out(tmp_path):
    yaml = pytest.importorskip("yaml")
    objs = [("Class", None, i * 150, -10, i * 150 + 100, -80) for i in range(4)]
    path = build_model(tmp_path, [_plain("Logical", objs, i) for i in (1, 2, 3)]
                       + [_plain("Custom", objs, 4)])
    text = mb.format_binding_yaml(mb.measure_binding(path, mb.BASE_NOTATION, "Logical"))
    doc = yaml.safe_load(text)
    assert doc["technology"] == "UML" and doc["stereotype_prefix"] == ""
    assert doc["diagram_types"]["Logical"]["sizing"]["Class"] == {"w": 100, "h": 70}
    assert "concept column is Object_Type" in text
    assert "12 of 12 measured elements (100.0%) carry an empty Stereotype" in text
    all_types = mb.format_binding_yaml(mb.measure_binding(path, mb.BASE_NOTATION))
    assert "Left out" not in all_types
    narrowed = mb.format_binding_yaml(mb.measure_binding(
        path, mb.BASE_NOTATION, exclude_base_types=["Custom"]))
    assert "Left out at the caller's request: Custom (1)" in narrowed


def test_the_base_notation_applies_the_same_concentration_rule(tmp_path):
    def row(n, pitch=150):
        return [("Class", None, i * pitch, -10, i * pitch + 100, -80) for i in range(n)]
    path = build_model(tmp_path, [_plain("Logical", row(12), 1, "Generated"),
                                  _plain("Logical", row(2), 2), _plain("Logical", row(2), 3),
                                  _plain("Logical", row(2), 4)])
    m = mb.measure_binding(path, mb.BASE_NOTATION)
    assert m.h_gap.concentrated and m.h_gap.top_diagram_name == "Generated"


def test_list_reports_the_base_notation(tmp_path, capsys):
    assert mb.main(["--list", "--model", _uml_model(tmp_path)]) == 0
    out = capsys.readouterr().out
    assert "UML [base notation" in out and "Logical (2)" in out and "Use Case (1)" in out
    assert "Analysis (1)" in out and "Custom (1)" in out and "left out" not in out


def test_the_command_line_reaches_the_base_notation_and_content_override(tmp_path, capsys):
    path = _uml_model(tmp_path)
    assert mb.main(["--model", path, "--technology", "UML"]) == 0
    assert "5 diagrams of EA's base notation" in capsys.readouterr().out
    assert mb.main(["--model", path, "--technology", "UML",
                    "--exclude-base-type", "Custom", "--exclude-base-type", "Analysis"]) == 0
    assert "3 diagrams of EA's base notation" in capsys.readouterr().out
    assert mb.main(["--model", path, "--technology", "UML", "--endpoint", "Class"]) == 0
    assert "Gap endpoints narrowed to: Class" in capsys.readouterr().out
    sub = tmp_path / "framework"
    sub.mkdir()
    path2 = _framework_model(sub)
    assert mb.main(["--model", path2, "--technology", "Fw", "--no-auto-content"]) == 0
    assert "Furniture note" in capsys.readouterr().out
    assert mb.main(["--model", path2, "--technology", "Fw"]) == 0
    assert "Furniture treated as content" in capsys.readouterr().out


# ---------------------------------------------------------------------------
# Hermetic
# ---------------------------------------------------------------------------

def _digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def test_the_original_model_is_never_modified(tmp_path):
    path = build_model(tmp_path, [(1, "Analysis", tag("T", "D"), [box("S", 0, -10)])])
    before, mtime = _digest(path), Path(path).stat().st_mtime_ns
    mb.measure_binding(path, "T", "D")
    assert _digest(path) == before
    assert Path(path).stat().st_mtime_ns == mtime
    assert [p.name for p in tmp_path.iterdir()] == ["model.qea"]


def test_the_copy_is_read_only(tmp_path):
    path = build_model(tmp_path, [(1, "Analysis", tag("T", "D"), [box("S", 0, -10)])])
    with mb.open_model_copy(path) as conn:
        with pytest.raises(sqlite3.OperationalError):
            conn.execute("DELETE FROM t_diagram")


@pytest.mark.parametrize("sidecar", ["-journal", "-wal"])
def test_a_model_with_a_journal_is_refused(tmp_path, sidecar):
    path = build_model(tmp_path, [(1, "Analysis", tag("T", "D"), [box("S", 0, -10)])])
    Path(path + sidecar).write_bytes(b"x")
    with pytest.raises(mb.MeasureError, match="open in another program"):
        mb.measure_binding(path, "T", "D")


def test_model_path_falls_back_to_the_environment_variable(tmp_path, monkeypatch):
    path = build_model(tmp_path, [(1, "Analysis", tag("T", "D"), [box("S", 0, -10)])])
    monkeypatch.setenv(mb.MODEL_ENV_VAR, path)
    assert mb.resolve_model_path(None) == path
    monkeypatch.setenv(mb.MODEL_ENV_VAR, str(tmp_path / "missing.qea"))
    monkeypatch.delenv("ProgramFiles", raising=False)
    assert mb.resolve_model_path(None) is None


def test_the_shipped_source_names_no_local_path_or_user():
    """This file ships to customers: no drive letters, no user directories."""
    source = (_HERE / "measure_binding.py").read_text(encoding="utf-8")
    assert not re.search(r"[A-Za-z]:\\\\?[A-Za-z]", source)
    assert "\\Users\\" not in source and "/Users/" not in source


# ---------------------------------------------------------------------------
# Against Sparx's example model - skipped when it is not there
# ---------------------------------------------------------------------------

MODEL = mb.resolve_model_path(None)

needs_model = pytest.mark.skipif(
    MODEL is None,
    reason=("EAExample.qea not found - pass its location in "
            f"{mb.MODEL_ENV_VAR}; a machine without EA has nothing to measure"),
)


def _is_the_1716_model() -> bool:
    if MODEL is None:
        return False
    with mb.open_model_copy(MODEL) as conn:
        return conn.execute("SELECT COUNT(*) FROM t_diagram").fetchone()[0] == 1129


exact = pytest.mark.skipif(
    MODEL is None or not _is_the_1716_model(),
    reason="exact pins are for EAExample.qea from EA 17.1 build 1716 (1,129 diagrams)",
)


@pytest.fixture(scope="module")
def archimate():
    return mb.measure_binding(MODEL, "ArchiMate3")


@pytest.fixture(scope="module")
def bpmn():
    return mb.measure_binding(MODEL, "BPMN2.0", "Business Process")


@needs_model
def test_technology_ids_are_resolved_from_the_data():
    with mb.open_model_copy(MODEL) as conn:
        known = mb.list_technologies(conn)
    assert "BPMN2.0" in known and "BPMN2" not in known
    assert "Business Process" in known["BPMN2.0"]
    assert "ArchiMate3" in known


@needs_model
def test_the_mdg_tag_is_populated_on_about_half_the_diagrams():
    """The brief's 526 of 1129: the key exists on more, but it is empty on most."""
    with mb.open_model_copy(MODEL) as conn:
        rows = conn.execute("SELECT StyleEx FROM t_diagram").fetchall()
    populated = sum(1 for (s,) in rows if mb.parse_mdg(s)[0])
    assert 0.4 < populated / len(rows) < 0.55


@needs_model
def test_every_stored_rectangle_has_top_above_bottom():
    """The sign convention, checked against the whole example model."""
    with mb.open_model_copy(MODEL) as conn:
        n, inverted = conn.execute(
            "SELECT COUNT(*), SUM(RectTop < RectBottom) FROM t_diagramobjects"
        ).fetchone()
    assert n > 0 and inverted == 0


# -- ArchiMate ---------------------------------------------------------------

@needs_model
def test_archimate_default_box_is_100_by_70(archimate):
    assert archimate.default_size.mode == (100, 70)
    assert archimate.stereotype_prefix == "ArchiMate_"


@needs_model
def test_archimate_junction_is_20_by_20_but_only_three_of_three(archimate):
    junction = archimate.sizes["ArchiMate_Junction"]
    assert junction.mode == (20, 20)
    assert (junction.mode_count, junction.n) == (3, 3)
    assert junction.low_n is True


@needs_model
def test_archimate_gaps_are_close_to_the_recorded_figures(archimate):
    """Recorded: 61 h-pairs / 69 v-pairs; h median 76 modal 78; v median 47 modal 38.

    This tool's rule is stricter than the one that produced those (it drops
    pairs that cross a container boundary), so the counts are a little lower
    and the medians a little higher. The MODES agree exactly.
    """
    h, v = archimate.h_gap, archimate.v_gap
    assert abs(h.n - 61) <= 0.15 * 61
    assert abs(v.n - 69) <= 0.15 * 69
    assert abs(h.median - 76) <= 3
    assert abs(v.median - 47) <= 3
    assert h.mode == 78
    assert v.mode == 38
    assert not h.low_n and not v.low_n


@exact
def test_archimate_exact_measurements_for_this_rule(archimate):
    assert (archimate.h_gap.n, archimate.h_gap.median, archimate.h_gap.mode) == (59, 78, 78)
    assert (archimate.v_gap.n, archimate.v_gap.median, archimate.v_gap.mode) == (60, 46, 38)


# -- BPMN --------------------------------------------------------------------

@needs_model
def test_bpmn_activity_is_110_by_60_of_212(bpmn):
    activity = bpmn.sizes["Activity"]
    assert activity.n == 212
    assert activity.mode == (110, 60)
    assert bpmn.default_size.mode == (110, 60)


@needs_model
def test_bpmn_activity_mode_is_a_minority_and_says_so(bpmn):
    """110x60 is the mode, but 54 of 212: the share is the honest half of it."""
    activity = bpmn.sizes["Activity"]
    assert activity.mode_share < 0.30
    assert activity.distinct > 50


@needs_model
def test_bpmn_events_are_30_by_30_across_173(bpmn):
    events = [bpmn.sizes[s] for s in ("StartEvent", "EndEvent", "IntermediateEvent")]
    assert sum(e.n for e in events) == 173
    assert all(e.mode == (30, 30) for e in events)
    assert sum(e.mode_count for e in events) / 173 > 0.95


@needs_model
def test_bpmn_gateway_is_42_by_42_of_61(bpmn):
    gateway = bpmn.sizes["Gateway"]
    assert (gateway.mode, gateway.mode_count, gateway.n) == ((42, 42), 61, 61)


@needs_model
def test_bpmn_data_object_is_35_by_50_of_34_and_data_store_is_50_by_50(bpmn):
    data = bpmn.sizes["DataObject"]
    assert (data.mode, data.mode_count, data.n) == ((35, 50), 28, 34)
    store = bpmn.sizes["DataStore"]
    assert (store.mode, store.mode_count, store.n) == ((50, 50), 4, 4)
    assert store.low_n is True


@needs_model
def test_bpmn_text_annotation_has_no_mode(bpmn):
    """The shipped BPMN binding calls 100x55 the modal size across n=10.

    All ten annotations are different sizes, so there is no mode: 100x55 is one
    of ten singletons. The tool refuses to name one.
    """
    note = bpmn.sizes["TextAnnotation"]
    assert note.n == 10
    assert note.distinct == 10
    assert note.mode is None


@needs_model
def test_bpmn_technology_and_diagram_type_are_attributed_by_tag(bpmn):
    assert bpmn.diagrams == 32
    assert bpmn.diagrams_by_mdg == 32
    assert bpmn.diagrams_by_fallback == 0
    assert bpmn.stereotype_prefix == ""


@needs_model
def test_bpmn_horizontal_gap_is_close_to_the_recorded_figures(bpmn):
    """Recorded: 315 h-pairs, median 41, modal cluster 30-46."""
    h = bpmn.h_gap
    assert abs(h.n - 315) <= 0.15 * 315
    assert abs(h.median - 41) <= 3
    assert 30 <= h.mode <= 46


@needs_model
def test_bpmn_vertical_gap_does_not_reproduce_the_recorded_median(bpmn):
    """Recorded: 175 v-pairs, median 63. Measured here: fewer pairs, median ~52.

    Not loosened to pass. The shipped binding's own comment says its vertical
    population "mixes within-lane neighbors with pairs that have a lane
    boundary between them". This tool excludes the latter by construction, so
    it is expected to land below the recorded median. Pair count is within
    tolerance; the median is not, and this test says which way and by how much.
    """
    v = bpmn.v_gap
    assert abs(v.n - 175) <= 0.15 * 175
    assert v.median < 63
    assert 63 - v.median > 3


@exact
def test_bpmn_exact_measurements_for_this_rule(bpmn):
    assert (bpmn.h_gap.n, bpmn.h_gap.median) == (314, 42)
    assert (bpmn.v_gap.n, bpmn.v_gap.median) == (162, 52)


@needs_model
def test_historical_rule_reproduces_the_recorded_archimate_figures():
    """Recorded: 61 h / 69 v pairs, medians 76 / 47, modes 78 / 38.

    The historical rule lands on 61 / 68, 76 / 47.5, 78 / 38. That is the
    evidence that it is the population the shipped ArchiMate numbers came from.
    """
    m = mb.measure_binding(MODEL, "ArchiMate3", rule="historical")
    assert m.h_gap.n == 61
    assert abs(m.v_gap.n - 69) <= 1
    assert m.h_gap.median == 76
    assert abs(m.v_gap.median - 47) <= 0.5
    assert (m.h_gap.mode, m.v_gap.mode) == (78, 38)


@needs_model
def test_historical_rule_does_not_reproduce_bpmn_and_the_strict_rule_drops_cross_lane_pairs():
    """Recorded BPMN: 315 h / 175 v, medians 41 / 63. Neither rule recovers it.

    Historical gives 355 / 262 pairs and a vertical median of 85, far above the
    recorded 63; strict gives 314 / 162 and 52. The recorded vertical median
    sits between them, which is what a population partly mixing lane-boundary
    pairs would look like. Stated, not asserted away.
    """
    hist = mb.measure_binding(MODEL, "BPMN2.0", "Business Process", rule="historical")
    strict = mb.measure_binding(MODEL, "BPMN2.0", "Business Process")
    assert (hist.h_gap.n, hist.v_gap.n) != (315, 175)
    assert strict.v_gap.median < 63 < hist.v_gap.median
    assert strict.v_gap.n < hist.v_gap.n


@exact
def test_historical_exact_measurements():
    a = mb.measure_binding(MODEL, "ArchiMate3", rule="historical")
    assert (a.h_gap.n, a.h_gap.median, a.h_gap.mode) == (61, 76, 78)
    assert (a.v_gap.n, a.v_gap.median, a.v_gap.mode) == (68, 47.5, 38)
    b = mb.measure_binding(MODEL, "BPMN2.0", "Business Process", rule="historical")
    assert (b.h_gap.n, b.h_gap.median, b.v_gap.n, b.v_gap.median) == (355, 45, 262, 85)
    narrow = mb.measure_binding(
        MODEL, "BPMN2.0", "Business Process", rule="historical",
        endpoint_stereotypes={"Activity", "StartEvent", "EndEvent",
                              "IntermediateEvent", "Gateway"})
    assert (narrow.h_gap.n, narrow.h_gap.median) == (319, 43)
    assert (narrow.v_gap.n, narrow.v_gap.median) == (178, 74.5)


@needs_model
def test_the_binding_block_for_bpmn_is_valid_yaml_with_the_diagram_type_verbatim(bpmn):
    yaml = pytest.importorskip("yaml")
    doc = yaml.safe_load(mb.format_binding_yaml(bpmn))
    assert doc["technology"] == "BPMN2.0"
    spec = doc["diagram_types"]["Business Process"]
    assert spec["sizing"]["default"] == {"w": 110, "h": 60}
    assert spec["sizing"]["Gateway"] == {"w": 42, "h": 42}
    assert "DataStore" not in spec["sizing"], "n=4 must be commented out"
    assert "TextAnnotation" not in spec["sizing"], "no mode: must be commented out"


@needs_model
def test_the_original_example_model_is_untouched_by_a_measurement():
    before = _digest(MODEL)
    mb.measure_binding(MODEL, "BPMN2.0", "Business Process")
    assert _digest(MODEL) == before


# ---------------------------------------------------------------------------
# The four changes, against the example model
# ---------------------------------------------------------------------------

@needs_model
def test_no_known_population_is_concentrated_so_the_recorded_figures_stand(archimate, bpmn):
    """Concentration is a new judgment; it must not have reclassified the figures
    the tool is checked against. Largest single diagram: ArchiMate 29% / 27%, BPMN
    12% / 25%."""
    for stat in (archimate.h_gap, archimate.v_gap, bpmn.h_gap, bpmn.v_gap):
        assert not stat.concentrated and stat.top_share < 0.5
    hist = mb.measure_binding(MODEL, "ArchiMate3", rule="historical")
    assert not hist.h_gap.concentrated and not hist.v_gap.concentrated


@exact
def test_the_four_changes_leave_every_recorded_figure_where_it_was():
    """ArchiMate 61 / 68 pairs, medians 76 / 47.5, modes 78 / 38 (historical);
    BPMN Activity 110x60 (n=212), events 30x30, Gateway 42x42 at 61 of 61,
    DataObject 35x50."""
    a = mb.measure_binding(MODEL, "ArchiMate3", rule="historical")
    assert (a.h_gap.n, a.h_gap.median, a.h_gap.mode) == (61, 76, 78)
    assert (a.v_gap.n, a.v_gap.median, a.v_gap.mode) == (68, 47.5, 38)
    b = mb.measure_binding(MODEL, "BPMN2.0", "Business Process")
    assert (b.sizes["Activity"].mode, b.sizes["Activity"].n) == ((110, 60), 212)
    assert all(b.sizes[s].mode == (30, 30)
               for s in ("StartEvent", "EndEvent", "IntermediateEvent"))
    assert (b.sizes["Gateway"].mode, b.sizes["Gateway"].mode_count, b.sizes["Gateway"].n) \
        == ((42, 42), 61, 61)
    assert b.sizes["DataObject"].mode == (35, 50)
    assert b.content_promoted == {}, "no BPMN diagram is made of furniture"


# -- distortion 1 ------------------------------------------------------------

@exact
def test_the_uml_timing_and_object_gaps_are_captured_by_one_diagram():
    """The false values found while authoring the UML binding."""
    timing = mb.measure_binding(MODEL, mb.BASE_NOTATION, "Timing").v_gap
    assert (timing.n, timing.median, timing.top_count) == (17, 73, 11)
    assert timing.concentrated and timing.top_diagram_name
    obj = mb.measure_binding(MODEL, mb.BASE_NOTATION, "Object").v_gap
    assert (obj.n, obj.top_count) == (14, 8)
    assert obj.concentrated and obj.top_share > 0.5


@exact
def test_the_uml_component_gap_is_captured_when_layout_items_are_the_endpoints():
    """28 of 50 gaps, every one exactly 12: the author's population.

    Their endpoints were the placed elements; ports and interfaces sit ON a
    border and are not laid out. With every concept an endpoint the population is
    63 and the same diagram is 44% of it - under the rule, and stated.
    """
    placed = {"Component", "Package", "Class", "Object"}
    narrowed = mb.measure_binding(MODEL, mb.BASE_NOTATION, "Component",
                                  endpoint_stereotypes=placed).v_gap
    assert (narrowed.n, narrowed.top_count, narrowed.mode) == (50, 28, 12)
    assert narrowed.concentrated
    everything = mb.measure_binding(MODEL, mb.BASE_NOTATION, "Component").v_gap
    assert (everything.n, everything.top_count) == (63, 28)
    assert not everything.concentrated


# -- distortion 2 ------------------------------------------------------------

@exact
def test_sysml_value_type_is_listed_and_the_90_by_70_default_is_its_size():
    m = mb.measure_binding(MODEL, "SysML1.4")
    assert m.default_size.mode == (90, 70)
    assert m.default_supply["ValueType"] == 27
    assert sum(m.default_supply.values()) == m.default_size.mode_count == 36
    text = mb.format_binding_yaml(m)
    assert re.search(r"^\s*# ValueType: .*n=74", text, re.M)
    assert "default {w: 90, h: 70} is ValueType's size" in text


@exact
def test_uml_state_node_agrees_with_the_default_and_is_listed():
    """The base-notation default 20x20 is StateNode's size; it used to vanish."""
    m = mb.measure_binding(MODEL, mb.BASE_NOTATION)
    assert m.default_size.mode == (20, 20)
    assert m.sizes["StateNode"].mode == (20, 20)
    assert m.default_supply == {"StateNode": 113}
    line = next(l for l in mb.format_binding_yaml(m).splitlines()
                if re.match(r"\s*StateNode:", l))
    assert "n=194" in line and "agrees with the default" in line


# -- distortion 3 ------------------------------------------------------------

@needs_model
def test_uaf_framework_tiles_are_content_and_the_diagram_is_measurable():
    m = mb.measure_binding(MODEL, "UAFP_Framework")
    assert m.content_promoted == {"Text": 45}
    assert m.h_gap.n > 0 and m.v_gap.n > 0
    assert m.h_gap.median == 5 and m.v_gap.median == 28
    off = mb.measure_binding(MODEL, "UAFP_Framework", auto_content=False)
    assert (off.h_gap.n, off.v_gap.n) == (0, 0), "the old reading, and it is now loud"
    assert off.furniture_majority_unmeasured == 1


@exact
def test_only_the_uaf_framework_diagram_is_promoted_anywhere_in_the_example_model():
    """The rule was chosen against every technology, not just the one that needed it."""
    with mb.open_model_copy(MODEL) as conn:
        technologies = mb.list_technologies(conn)
    promoted = {t: mb.measure_binding(MODEL, t).content_promoted for t in technologies}
    assert {t: p for t, p in promoted.items() if p} == {"UAFP_Framework": {"Text": 45}}


# -- the base notation -------------------------------------------------------

# -- the documentation-page filter, on synthetic diagrams ---------------------
# Composition, never type. Each case below fixes the composition and varies the
# Diagram_Type, or fixes the type and varies the composition.

def _doc_page(left=0):
    """8 `Text` objects and one `Package`: the item's own example."""
    return ([box("", left + i * 140, -10, otype="Text") for i in range(8)]
            + [box("", left, -300, otype="Package")])


def _real_diagram(left=0, n=6):
    return [box("", left + i * 140, -10, otype="Class") for i in range(n)]


@pytest.mark.parametrize("dtype", ["Custom", "Logical", "Package", "Use Case"])
def test_a_documentation_page_is_dropped_whatever_its_diagram_type(tmp_path, dtype):
    path = build_model(tmp_path, [(1, dtype, "", _doc_page(), "Page"),
                                  (2, dtype, "", _real_diagram(), "Real")])
    m = mb.measure_binding(path, mb.BASE_NOTATION)
    assert m.base_before_filter == 2
    assert m.documentation_pages == ((dtype, "Page"),)
    assert m.diagrams == 1 and m.diagram_types == {dtype: 1}
    assert "Class" in m.sizes and "Package" not in m.sizes


@pytest.mark.parametrize("dtype", ["Custom", "Logical", "Package", "Use Case"])
def test_a_real_diagram_is_kept_whatever_its_diagram_type(tmp_path, dtype):
    """Custom holds documentation pages AND real content; the type is not the test."""
    path = build_model(tmp_path, [(1, dtype, "", _real_diagram(), "Real")])
    m = mb.measure_binding(path, mb.BASE_NOTATION)
    assert m.documentation_pages == () and m.diagrams == 1
    assert "none of the 1 selected diagrams is more than 50% furniture" \
        in mb.format_binding_yaml(m)


def test_the_filter_is_aggregate_not_one_furniture_type_at_a_time(tmp_path):
    """4 Text + 4 Note + 1 Package is 89% furniture and has no majority TYPE.

    `furniture_majority()` sees nothing here, which is why it is the wrong test
    for this question and the filter does not reuse it.
    """
    objs = ([box("", i * 140, -10, otype="Text") for i in range(4)]
            + [box("", i * 140, -200, otype="Note") for i in range(4)]
            + [box("", 0, -400, otype="Package")])
    path = build_model(tmp_path, [(1, "Logical", "", objs, "Mixed Page")])
    with mb.open_model_copy(path) as conn:
        diagrams = mb._load_diagrams(conn)
    loaded = diagrams[1].items
    assert mb.furniture_majority(loaded) == frozenset(), "no ONE type is a majority"
    assert mb.furniture_share(loaded) == 8 / 9
    assert mb.is_documentation_page(loaded)
    m = mb.measure_binding(path, mb.BASE_NOTATION)
    assert m.documentation_pages == (("Logical", "Mixed Page"),)
    assert m.documentation_pages_type_majority == 0, "reconciles: the per-type test " \
        "would have dropped none of this one"


def test_exactly_half_furniture_is_not_more_than_half(tmp_path):
    """The threshold is MORE than `BASE_FURNITURE_SHARE`, and the boundary is pinned."""
    objs = ([box("", i * 140, -10, otype="Text") for i in range(3)]
            + [box("", i * 140, -200, otype="Class") for i in range(3)])
    path = build_model(tmp_path, [(1, "Logical", "", objs, "Half")])
    with mb.open_model_copy(path) as conn:
        loaded = mb._load_diagrams(conn)[1].items
    assert mb.furniture_share(loaded) == mb.BASE_FURNITURE_SHARE == 0.5
    assert not mb.is_documentation_page(loaded)
    assert mb.measure_binding(path, mb.BASE_NOTATION).documentation_pages == ()


def test_the_report_states_the_content_the_filter_took_away(tmp_path):
    """A majority-furniture diagram can hold real content; the cost is not hidden."""
    objs = ([box("", i * 140, -10, otype="Text") for i in range(6)]
            + [box("", i * 140, -200, otype="Node") for i in range(5)])
    path = build_model(tmp_path, [(1, "Deployment", "", objs, "Annotated"),
                                  (2, "Logical", "", _real_diagram(), "Real")])
    m = mb.measure_binding(path, mb.BASE_NOTATION)
    assert m.documentation_pages == (("Deployment", "Annotated"),)
    assert m.documentation_page_elements == 5
    assert m.documentation_page_worst == (5, "Deployment", "Annotated")
    text = mb.format_binding_yaml(m)
    assert "carried 5 non-furniture element(s)" in text
    assert 'being 5 on Deployment "Annotated"' in text


def test_declaring_the_annotation_type_content_keeps_the_diagram(tmp_path):
    """The lever for a diagram wrongly dropped is --content-type, not the threshold."""
    path = build_model(tmp_path, [(1, "Logical", "", _doc_page(), "Page")])
    assert mb.measure_binding(path, mb.BASE_NOTATION).documentation_pages == (
        ("Logical", "Page"),)
    kept = mb.measure_binding(path, mb.BASE_NOTATION, content_types={"Text"})
    assert kept.documentation_pages == () and kept.diagrams == 1


def test_list_base_notation_reports_the_pages_it_dropped(tmp_path):
    path = build_model(tmp_path, [(1, "Custom", "", _doc_page(), "Page"),
                                  (2, "Custom", "", _real_diagram(), "Real")])
    with mb.open_model_copy(path) as conn:
        diagrams = mb._load_diagrams(conn)
    kept, excluded, pages = mb.list_base_notation(diagrams)
    assert kept == {"Custom": 1} and excluded == {} and pages == {"Custom": 1}


# -- the base notation, against the example model -----------------------------

@exact
def test_the_base_notation_population_is_265_diagrams_2070_elements_15_types():
    """Nothing excluded BY TYPE: this is what the selection admits, and the answer.

    The plain-UML tests admit 330; the documentation-page filter drops 65 of them.
    Both numbers are on the result, because a population change that is not
    written down is how a measurement stops being reproducible.
    """
    m = mb.measure_binding(MODEL, mb.BASE_NOTATION)
    assert m.base_before_filter == 330
    assert len(m.documentation_pages) == 65
    assert m.diagrams == 265 and len(m.diagram_types) == 15
    assert m.excluded_base_types == {}
    assert sum(st.n for st in m.sizes.values()) == 2070
    assert m.unstereotyped == (1930, 2070)
    assert m.diagram_types["Analysis"] == 4 and m.diagram_types["Custom"] == 12
    assert m.concept_column == "Object_Type"


@exact
def test_the_documentation_page_filter_names_every_diagram_it_dropped():
    """65 of 330, reconciled against the per-type count, with the cost stated."""
    m = mb.measure_binding(MODEL, mb.BASE_NOTATION)
    by_type = collections.Counter(t for t, _ in m.documentation_pages)
    assert dict(sorted(by_type.items())) == {
        "Collaboration": 2, "Component": 1, "CompositeStructure": 10, "Custom": 13,
        "Deployment": 9, "Logical": 17, "Package": 8, "Statechart": 4, "Use Case": 1,
    }
    assert sum(by_type.values()) == 65
    # Every dropped page was selectable before the filter, and none survives it.
    assert m.diagrams + len(m.documentation_pages) == m.base_before_filter == 330
    assert m.furniture_majority_diagrams == 0

    # The per-type test `furniture_majority()` counted 32 of these same 65; the
    # other 33 are furniture only with the types counted together, which is the
    # whole reason the filter is aggregate. This is the reconciliation.
    assert m.documentation_pages_type_majority == 32

    # It costs real content, and the report says how much and where.
    assert m.documentation_page_elements == 336
    assert m.documentation_page_worst == (24, "Deployment", "Government Agency")

    text = mb.format_binding_yaml(m)
    assert "65 of 330 selected diagram(s) dropped" in text
    assert "32 of the 65 have ONE furniture type as a majority" in text
    assert "WHAT THE FILTER COST" in text
    for raw_type, name in m.documentation_pages:
        assert f'"{name}"' in text, f"{raw_type} {name} dropped but not named"
    # A documentation page in a type that also holds real content, and the real
    # content of that same type, both named in the item's own evidence.
    assert ("Custom", "Gap Analysis") in m.documentation_pages
    assert ("Custom", "Design Patterns") not in m.documentation_pages
    assert ("Custom", "Account") not in m.documentation_pages


@exact
def test_the_recorded_2266_figure_is_a_301_diagram_subset_not_the_330_reported():
    """The UML binding records "330 diagrams, 13 types, 2,266 elements".

    Those are two selections, and NEITHER is what the tool reports now. 2,266
    elements and 13 types are what remained after dropping Analysis (4) and Custom
    (25) from the 330, which is 301 diagrams, BEFORE the documentation-page filter.
    The same request now gives 249 diagrams and 1,969 elements: the 301 less the 52
    pages that sit in the types the caller kept. This pins the discrepancy and the
    movement; neither is a target the tool aims at.
    """
    m = mb.measure_binding(MODEL, mb.BASE_NOTATION,
                           exclude_base_types={"Analysis", "Custom"})
    # The caller's type exclusion is counted BEFORE the composition filter, so it
    # still reports every diagram the caller asked to leave out.
    assert m.excluded_base_types == {"Analysis": 4, "Custom": 25}
    assert m.base_before_filter == 301
    assert len(m.documentation_pages) == 52
    assert m.diagrams == 249 and len(m.diagram_types) == 13
    assert sum(st.n for st in m.sizes.values()) == 1969
    assert m.unstereotyped == (1851, 1969)


@exact
def test_analysis_and_custom_are_not_a_separable_non_uml_population():
    """The evidence for filtering on composition and not on type.

    Analysis diagrams hold ordinary UML elements and none is mostly furniture.
    Custom is mixed. Documentation pages are spread across the types, so excluding
    two types would discard real content and still leave most pages in.
    """
    with mb.open_model_copy(MODEL) as conn:
        diagrams = mb._load_diagrams(conn)
    selected, _, _, pages = mb._select_base(diagrams, (), frozenset())
    admitted = selected + pages
    assert len(admitted) == 330 and len(pages) == 65

    analysis = [d for d in admitted if d.raw_type == "Analysis"]
    custom = [d for d in admitted if d.raw_type == "Custom"]
    dropped = {(d.raw_type, d.diagram_id) for d in pages}
    assert not any(("Analysis", d.diagram_id) in dropped for d in analysis)
    kinds = {it.object_type for d in analysis for it in diagrams[d.diagram_id].items}
    assert {"Activity", "Actor", "Object", "Event"} <= kinds
    assert len(custom) == 25
    assert sum(1 for d in custom if ("Custom", d.diagram_id) in dropped) == 13
    others = [d for d in admitted if d.raw_type not in ("Analysis", "Custom")]
    assert sum(1 for d in others
               if (d.raw_type, d.diagram_id) in dropped) == 52, \
        "52 of the 65 pages sit outside those two types: no type exclusion reaches them"


@exact
def test_the_base_notation_uses_ea_diagram_type_strings():
    m = mb.measure_binding(MODEL, mb.BASE_NOTATION)
    assert {"Logical", "Statechart", "Collaboration", "Use Case"} <= set(m.diagram_types)
    use_case = mb.measure_binding(MODEL, mb.BASE_NOTATION, "Use Case")
    assert use_case.diagrams == 15, "16 before the documentation-page filter"
    assert use_case.documentation_pages == (("Use Case", "Use Case Model"),)
    assert use_case.base_before_filter == 16


# ---------------------------------------------------------------------------
# The sample floors, and the guard on the one that is too low
# ---------------------------------------------------------------------------
# APT-2026-0193. `MIN_SAMPLE` had no provenance; it now has a derivation, and the
# same derivation says a gap MEDIAN needs about four times as many observations.
# The floor is not raised - that would move every authored gap - so the guard is
# what fires. These pin the guard and the relationship between the two numbers.

def test_the_gap_floor_is_far_above_the_size_floor():
    """The finding, as an assertion: one number cannot gate both statistics."""
    assert mb.MIN_SAMPLE == 10
    assert mb.MIN_SAMPLE_GAP == 38
    assert mb.MIN_SAMPLE_GAP > 3 * mb.MIN_SAMPLE


def test_a_gap_population_over_the_low_n_floor_is_still_thin_for_a_median():
    """`low_n` False and `thin_median` True is the common case, and the point."""
    gaps = list(range(20, 40))          # n=20: clears MIN_SAMPLE, under MIN_SAMPLE_GAP
    stat = mb.gap_stat(gaps)
    assert stat.n == 20 and not stat.low_n and stat.thin_median


def test_a_gap_population_over_the_derived_floor_is_not_thin():
    stat = mb.gap_stat([30] * mb.MIN_SAMPLE_GAP)
    assert not stat.low_n and not stat.thin_median
    assert mb.gap_stat([30] * (mb.MIN_SAMPLE_GAP - 1)).thin_median


def test_an_empty_gap_population_is_both_thin_and_low_n():
    stat = mb.gap_stat([])
    assert stat.n == 0 and stat.low_n and stat.thin_median


def test_the_guard_fires_on_the_line_it_qualifies(tmp_path):
    """A stated gap whose sample is under the derived floor says so, and is still
    stated: the guard annotates rather than suppressing, because raising the
    suppression floor would move every gap already authored against this tool."""
    # 4 diagrams of 5 elements: 16 gaps, over MIN_SAMPLE and well under
    # MIN_SAMPLE_GAP, spread widely enough that concentration does not fire first.
    path = build_model(tmp_path, [
        (d, "Logical", tag("T", "D"), [box("S", i * 130, -10) for i in range(5)])
        for d in range(1, 5)])
    m = mb.measure_binding(path, "T", "D")
    assert m.h_gap.n >= mb.MIN_SAMPLE and m.h_gap.thin_median
    line = next(l for l in mb.format_binding_yaml(m).splitlines()
                if "item_gap_x:" in l)
    assert "THIN FOR A MEDIAN" in line
    assert f"MIN_SAMPLE_GAP={mb.MIN_SAMPLE_GAP}" in line
    assert line.lstrip().startswith("item_gap_x:"), "still stated, not commented out"


def test_a_low_n_gap_is_not_also_told_it_is_thin(tmp_path):
    """One complaint per line. `low_n` already comments the value out."""
    objs = [box("S", i * 130, -10) for i in range(4)]
    path = build_model(tmp_path, [(1, "Logical", tag("T", "D"), objs)])
    m = mb.measure_binding(path, "T", "D")
    assert m.h_gap.low_n and m.h_gap.thin_median
    line = next(l for l in mb.format_binding_yaml(m).splitlines()
                if "item_gap_x:" in l)
    assert "LOW-N" in line and "THIN FOR A MEDIAN" not in line


@exact
def test_the_guard_fires_on_shipped_technologies_and_is_not_dead_code():
    """It must catch something real, or it is decoration.

    No count is asserted - adding a binding must not break this - only that the
    guard discriminates: at least one technology clears `low_n` and trips the
    median guard, and at least one clears both.
    """
    with mb.open_model_copy(MODEL) as conn:
        known = mb.list_technologies(conn)
        diagrams = mb._load_diagrams(conn)
    thin = wide = 0
    for technology in known:
        m = mb.measure_diagrams(diagrams, known, technology, None)
        for gap in (m.h_gap, m.v_gap):
            if gap.low_n:
                continue
            thin += gap.thin_median
            wide += not gap.thin_median
    assert thin and wide, f"guard does not discriminate: thin={thin} wide={wide}"

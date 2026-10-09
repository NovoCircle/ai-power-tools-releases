#!/usr/bin/env python3
"""Tests for the pure-arithmetic layout engine.

Run from the repository root:

    python -m pytest ea-diagram-composition/tools/test_compose.py -q

Nothing here touches a repository, a COM object or the filesystem. If any test
in this file needs Sparx EA to pass, the layer boundary has been broken.

Two conventions worth reading before editing:

* `assert_no_overlaps` is applied to comparable sets - all items together, all
  containers together - never to items and containers mixed. Items are nested
  inside their containers by design, so a mixed set is supposed to overlap.
* Rect intersection is tested in EA's flipped-y convention, where `top` is
  greater than `bottom`. `test_overlap_helper_*` pins that first, because every
  other no-overlap assertion in the file leans on it.
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

import pytest

_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

import compose  # noqa: E402
from compose import (  # noqa: E402
    DEFAULT_SPEC,
    FIT_OVERLAP,
    FIT_WIDEN,
    WIDTH_MISFIT,
    LayoutError,
    bounding_box,
    compose_lanes,
    compose_layered_bands,
    compose_nested_grid,
    compose_radial,
    compose_two_column_cycle,
    rect,
    rect_height,
    rect_width,
    rects_overlap,
)


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------
def assert_no_overlaps(rects, label=""):
    """Assert that no two rects in `rects` share positive area."""
    rects = list(rects)
    for i, a in enumerate(rects):
        for b in rects[i + 1:]:
            assert not rects_overlap(a, b), (
                f"{label}: overlap between "
                f"{a.get('id', a.get('name'))} {_span(a)} and "
                f"{b.get('id', b.get('name'))} {_span(b)}"
            )


def assert_contains(outer, inner, label=""):
    """Assert `inner` sits wholly inside `outer`, in EA's convention."""
    assert inner["left"] >= outer["left"], f"{label}: left escapes {_span(outer)}"
    assert inner["right"] <= outer["right"], f"{label}: right escapes {_span(outer)}"
    # Visually lower means numerically smaller, so inner top must not be ABOVE
    # outer top, i.e. must not be greater.
    assert inner["top"] <= outer["top"], f"{label}: top escapes {_span(outer)}"
    assert inner["bottom"] >= outer["bottom"], f"{label}: bottom escapes {_span(outer)}"


def assert_valid_rect(r, label=""):
    """Every rect must be positive-area and obey EA's sign convention."""
    assert r["right"] > r["left"], f"{label}: non-positive width {_span(r)}"
    assert r["top"] > r["bottom"], f"{label}: non-positive height {_span(r)}"
    assert rect_width(r) > 0 and rect_height(r) > 0, f"{label}: zero size {_span(r)}"


def assert_result_sane(result, label=""):
    """The checks that must hold for any output of any grammar."""
    for c in result["containers"]:
        assert_valid_rect(c, f"{label} container {c['id']}")
        assert_valid_rect(c["label"], f"{label} label of {c['id']}")
        assert_contains(c, c["label"], f"{label} label of {c['id']}")
    for it in result["items"]:
        assert_valid_rect(it, f"{label} item {it['id']}")
    assert_no_overlaps(result["items"], f"{label} items")
    assert_no_overlaps(result["containers"], f"{label} containers")

    by_id = {c["id"]: c for c in result["containers"]}
    for it in result["items"]:
        assert_contains(by_id[it["container_id"]], it, f"{label} item {it['id']}")

    expected = bounding_box([*result["containers"], *result["items"]])
    assert result["bounds"] == expected, f"{label}: bounds disagree with contents"


def _span(r):
    return (
        f"(l={r['left']} t={r['top']} r={r['right']} b={r['bottom']} "
        f"{rect_width(r)}x{rect_height(r)})"
    )


def _items(*ids):
    return [{"id": i} for i in ids]


def _center_x2(r):
    """Twice the horizontal center, so integer rounding stays visible."""
    return r["left"] + r["right"]


def _center_y2(r):
    return r["top"] + r["bottom"]


def _own_content_width(count, wrap=None, item_width=140, gap=20):
    """What a band of `count` items demands for ITSELF, ignoring the other bands.

    The width the engine used to draw each band at, before APT-2026-0152: the
    widest row it actually uses, which stops growing once the row wraps. Written
    out here rather than read back off the engine, so a test can state what a
    band of two ought to differ from a band of three BY, and so a sweep can
    prove its own inputs discriminate instead of assuming they do.
    """
    wrap = DEFAULT_SPEC["wrap_width"] if wrap is None else wrap
    pitch = item_width + gap
    per_row = max(1, (wrap - item_width) // pitch + 1)
    on_widest_row = min(count, per_row)
    return (on_widest_row - 1) * pitch + item_width if on_widest_row else 0


def _band_stack(counts, **band_extra):
    """A stack of bands holding `counts` items each, with unique ids throughout."""
    bands = []
    n = 0
    for b, count in enumerate(counts):
        bands.append({"name": f"Band {b}",
                      "items": _items(*[f"e{n + k}" for k in range(count)]),
                      **band_extra})
        n += count
    return bands


# ===========================================================================
# 1. The overlap helper itself, and the coordinate convention it rests on
# ===========================================================================
def test_overlap_helper_detects_a_real_overlap():
    a = {"left": 0, "top": -50, "right": 100, "bottom": -110}
    b = {"left": 50, "top": -80, "right": 150, "bottom": -140}
    assert rects_overlap(a, b)
    assert rects_overlap(b, a)


def test_overlap_helper_is_written_for_eas_inverted_y():
    """A screen-coordinate intersection test calls this pair disjoint.

    Both rects occupy the same x range; a spans -50..-110 and b spans -60..-120,
    so they share 50 units of height. An implementation that assumed bottom is
    numerically greater than top would compare a['bottom'] <= b['top']
    (-110 <= -60, true) and wrongly report no overlap.
    """
    a = {"left": 0, "top": -50, "right": 100, "bottom": -110}
    b = {"left": 0, "top": -60, "right": 100, "bottom": -120}
    assert rects_overlap(a, b)


def test_overlap_helper_separates_disjoint_pairs():
    a = {"left": 0, "top": -50, "right": 100, "bottom": -110}
    right_of_a = {"left": 120, "top": -50, "right": 220, "bottom": -110}
    below_a = {"left": 0, "top": -150, "right": 100, "bottom": -210}
    assert not rects_overlap(a, right_of_a)
    assert not rects_overlap(a, below_a)
    assert not rects_overlap(below_a, a)


def test_abutting_rects_do_not_overlap():
    """Swimlanes that share an edge are correct geometry, not a collision."""
    a = {"left": 0, "top": -50, "right": 100, "bottom": -110}
    below = {"left": 0, "top": -110, "right": 100, "bottom": -170}
    beside = {"left": 100, "top": -50, "right": 200, "bottom": -110}
    assert not rects_overlap(a, below)
    assert not rects_overlap(a, beside)


def test_no_overlap_helper_would_fail_on_a_known_bad_set():
    """The helper has to be able to fail, or it proves nothing elsewhere."""
    bad = [
        {"id": "a", "left": 0, "top": -50, "right": 100, "bottom": -110},
        {"id": "b", "left": 50, "top": -80, "right": 150, "bottom": -140},
    ]
    with pytest.raises(AssertionError):
        assert_no_overlaps(bad, "deliberate")


def test_rect_matches_a_real_ea_placement():
    """left=50, top=-50, right=190, bottom=-110 is 140 wide and 60 tall."""
    r = rect(50, -50, 140, 60)
    assert r == {"left": 50, "top": -50, "right": 190, "bottom": -110}
    assert rect_width(r) == 140
    assert rect_height(r) == 60
    assert r["top"] > r["bottom"]


def test_rect_refuses_to_make_a_zero_size_box():
    with pytest.raises(LayoutError, match="width and height"):
        rect(0, 0, 140, 0)
    with pytest.raises(LayoutError, match="width and height"):
        rect(0, 0, -140, 60)


def test_bounding_box_takes_the_maximum_top():
    """The visual top of an EA diagram is the coordinate nearest zero."""
    rects = [rect(20, -20, 100, 40), rect(200, -300, 100, 40)]
    assert bounding_box(rects) == {
        "left": 20, "top": -20, "right": 300, "bottom": -340,
        "width": 280, "height": 320,
    }


def test_bounding_box_rejects_an_empty_set():
    with pytest.raises(LayoutError, match="at least one rect"):
        bounding_box([])


def test_moving_down_a_band_stack_makes_coordinates_more_negative():
    result = compose_layered_bands([
        {"name": "Top", "items": _items("a")},
        {"name": "Middle", "items": _items("b")},
        {"name": "Bottom", "items": _items("c")},
    ])
    tops = [c["top"] for c in result["containers"]]
    assert tops == sorted(tops, reverse=True), tops
    assert all(t < 0 for t in tops)
    for earlier, later in zip(result["containers"], result["containers"][1:]):
        assert later["top"] < earlier["bottom"], "bands must not interleave"
    assert_result_sane(result, "three bands")


# ===========================================================================
# 2. layered_bands
# ===========================================================================
def test_band_geometry_uses_the_declared_sizes():
    result = compose_layered_bands(
        [{"name": "Channels", "items": _items("a", "b", "c")}],
        {"origin_left": 20, "origin_top": -20, "item_width": 140,
         "item_height": 60, "item_gap_x": 20, "label_height": 28,
         "band_pad_x": 12, "band_pad_y": 12},
    )
    lefts = [it["left"] for it in result["items"]]
    assert lefts == [32, 192, 352]        # 20 + 12, stepping by 140 + 20
    assert all(it["top"] == -48 for it in result["items"])     # -20 - 28
    assert all(it["bottom"] == -108 for it in result["items"])
    band = result["containers"][0]
    assert rect_width(band) == 3 * 140 + 2 * 20 + 2 * 12
    assert rect_height(band) == 28 + 60 + 12
    assert_result_sane(result, "sized band")


def test_items_are_uniformly_sized_within_a_band_and_may_differ_between_bands():
    result = compose_layered_bands([
        {"name": "Channels", "items": _items("a", "b", "c")},
        {"name": "Applications", "items": _items("d", "e"),
         "item_width": 200, "item_height": 90},
    ])
    first = [it for it in result["items"] if it["band_index"] == 0]
    second = [it for it in result["items"] if it["band_index"] == 1]

    assert {(rect_width(i), rect_height(i)) for i in first} == {(140, 60)}
    assert {(rect_width(i), rect_height(i)) for i in second} == {(200, 90)}
    assert_result_sane(result, "mixed sizes")


def test_a_taller_band_pushes_the_next_band_further_down():
    """Band height follows contents, so the stack step is not a constant."""
    short = compose_layered_bands([
        {"name": "A", "items": _items("a")},
        {"name": "B", "items": _items("b")},
    ])
    tall = compose_layered_bands([
        {"name": "A", "items": _items("a"), "item_height": 200},
        {"name": "B", "items": _items("b")},
    ])
    assert tall["containers"][1]["top"] < short["containers"][1]["top"] - 100
    assert rect_height(tall["containers"][0]) == 28 + 200 + 12


def test_band_pitch_acts_as_a_floor_not_a_cap():
    """A band taller than band_pitch still gets its own height plus the gap."""
    loose = compose_layered_bands(
        [{"name": "A", "items": _items("a")}, {"name": "B", "items": _items("b")}],
        {"band_pitch": 400},
    )
    assert loose["containers"][1]["top"] == -20 - 400

    crowded = compose_layered_bands(
        [{"name": "A", "items": _items("a"), "item_height": 300},
         {"name": "B", "items": _items("b")}],
        {"band_pitch": 100},
    )
    step = crowded["containers"][0]["top"] - crowded["containers"][1]["top"]
    assert step == rect_height(crowded["containers"][0]) + DEFAULT_SPEC["band_gap"]
    assert_result_sane(crowded, "band_pitch floor")


def test_a_wide_band_wraps_instead_of_running_off_the_canvas():
    spec = {"wrap_width": 500}          # 140 wide, pitch 160 -> 3 per row
    result = compose_layered_bands(
        [{"name": "Capabilities", "items": _items(*"abcdefg")}], spec
    )
    rows = {}
    for it in result["items"]:
        rows.setdefault(it["row"], []).append(it)

    assert sorted(rows) == [0, 1, 2]
    assert [len(rows[r]) for r in sorted(rows)] == [3, 3, 1]
    for row_items in rows.values():
        assert len({i["top"] for i in row_items}) == 1, "a row shares one top"
        widest = max(i["right"] for i in row_items) - min(i["left"] for i in row_items)
        assert widest <= spec["wrap_width"]
    assert rows[1][0]["top"] < rows[0][0]["bottom"], "row 2 sits below row 1"
    assert rect_height(result["containers"][0]) == 28 + (2 * 80 + 60) + 12
    assert_result_sane(result, "wrapped band")


def test_wrapping_never_places_a_row_wider_than_the_wrap_width():
    for wrap in (140, 300, 460, 620, 900, 1600):
        result = compose_layered_bands(
            [{"name": "Wide", "items": _items(*[f"e{n}" for n in range(11)])}],
            {"wrap_width": wrap},
        )
        rows = {}
        for it in result["items"]:
            rows.setdefault(it["row"], []).append(it)
        for r, row_items in rows.items():
            span = max(i["right"] for i in row_items) - min(i["left"] for i in row_items)
            assert span <= wrap, f"wrap_width={wrap}, row {r} spans {span}"
        assert_result_sane(result, f"wrap_width={wrap}")


def test_alignment_places_the_rows_because_the_bands_already_agree():
    """REPLACES a test that pinned the ragged right edge of APT-2026-0152.

    What the old test asserted: that under `align: "center"` a band of one item
    came out NARROWER than a band of four and was nudged right to center against
    it - `narrow["left"] > wide["left"]`. That was the defect stated as a
    requirement. Bands now share the widest band's width, so both edges of every
    band agree whatever the alignment, and `align` is spent on the rows inside.
    """
    bands = [
        {"name": "Wide", "items": _items("a", "b", "c", "d")},
        {"name": "Narrow", "items": _items("e")},
    ]
    for align in ("left", "center"):
        result = compose_layered_bands(bands, {"align": align})
        wide, narrow = result["containers"]
        assert wide["left"] == narrow["left"] == DEFAULT_SPEC["origin_left"]
        assert wide["right"] == narrow["right"], f"{align}: ragged right edge"
        assert_result_sane(result, f"align={align}")

    # What alignment still decides: where the sparse band's single row sits in
    # the width it has been given. Flush left by default, centered on request.
    pad_x = DEFAULT_SPEC["band_pad_x"]
    flush = compose_layered_bands(bands, {"align": "left"})
    lone = next(i for i in flush["items"] if i["id"] == "e")
    assert lone["left"] == flush["containers"][1]["left"] + pad_x

    centered = compose_layered_bands(bands, {"align": "center"})
    lone = next(i for i in centered["items"] if i["id"] == "e")
    band = centered["containers"][1]
    assert abs(_center_x2(lone) - _center_x2(band)) <= 1, "row not centered"
    assert lone["left"] > band["left"] + pad_x


def test_centering_also_centers_a_short_row_inside_its_band():
    result = compose_layered_bands(
        [{"name": "Capabilities", "items": _items("a", "b", "c", "d", "e")}],
        {"wrap_width": 500, "align": "center"},       # rows of 3 then 2
    )
    rows = {}
    for it in result["items"]:
        rows.setdefault(it["row"], []).append(it)
    full = rows[0]
    short = rows[1]
    full_center = full[0]["left"] + full[-1]["right"]
    short_center = short[0]["left"] + short[-1]["right"]
    assert abs(full_center - short_center) <= 1
    assert_result_sane(result, "centered rows")


def test_an_empty_band_keeps_its_label_row():
    result = compose_layered_bands([
        {"name": "Channels", "items": _items("a")},
        {"name": "Reserved", "items": []},
        {"name": "Platform", "items": _items("b")},
    ])
    empty = result["containers"][1]
    assert rect_height(empty) == 28 + 12, "label row plus its padding"
    assert rect_width(empty) >= 140, "an empty band is still a visible strip"
    assert rect_height(empty["label"]) == 28
    assert result["containers"][2]["top"] < empty["bottom"]
    assert [it["band_index"] for it in result["items"]] == [0, 2]
    assert_result_sane(result, "empty band")


#: The width two bands of one and five items demand between them: the five-item
#: band's row, plus the band's own padding either side. Written out so every test
#: below argues about the same number.
_STACK_CONTENT_WIDTH = 5 * 140 + 4 * 20 + 2 * 12               # 804


def _misfit_stack():
    return [{"name": "Sparse", "items": _items("a")},
            {"name": "Full", "items": _items("b", "c", "d", "e", "f")}]


def test_min_band_width_above_the_content_is_a_floor_under_the_whole_stack():
    """REPLACES a test that pinned the ragged right edge of APT-2026-0152.

    What the old test asserted: that with `min_band_width: 700` a band of one
    item came out at exactly 700 while its five-item neighbor came out at 804 -
    two bands, two widths, which is the defect. `min_band_width` is still a
    floor, but the thing it is a floor under is the stack's shared width, so it
    bites only when it exceeds what the widest band demands.

    A floor ABOVE the content is the uncontroversial half and the only half this
    test still covers: nothing is in conflict, so nothing is reported.
    """
    result = compose_layered_bands(_misfit_stack(), {"min_band_width": 1000})
    assert {rect_width(c) for c in result["containers"]} == {1000}
    assert result["conflicts"] == []
    assert_result_sane(result, "min_band_width above content")


def test_min_band_width_below_the_content_is_reported_not_outvoted():
    """APT-2026-0187, the surviving half of APT-2026-0152.

    REPLACES the half of the old test that asserted the silence. It pinned that
    `min_band_width: 700` against 804px of content came back as 804 and said
    nothing about it - an explicit instruction overridden without a word, which
    is the same defect as a box silently widened to fit a name.

    The width is unchanged, because widening is still the safe default and
    changing it would move every existing caller. What is new is the second
    assertion: the conflict comes back, with both options, whose content forced
    it, and the fact that nobody chose.
    """
    result = compose_layered_bands(_misfit_stack(), {"min_band_width": 700})
    assert {rect_width(c) for c in result["containers"]} == {_STACK_CONTENT_WIDTH}
    assert_result_sane(result, "min_band_width below content")

    assert len(result["conflicts"]) == 1
    c = result["conflicts"][0]
    assert c["conflict"] == WIDTH_MISFIT
    assert c["where"] == "spec.min_band_width"
    assert c["driver"] == "Full", "the band whose contents forced it"
    assert c["driver_kind"] == "band_contents"
    assert c["requested_width"] == 700
    assert c["required_width"] == _STACK_CONTENT_WIDTH
    assert c["applied"] == FIT_WIDEN
    assert c["width_applied"] == _STACK_CONTENT_WIDTH
    assert c["answered"] is False, "nobody chose; this is the default"
    assert [o["answer"] for o in c["options"]] == [FIT_WIDEN, FIT_OVERLAP]
    assert [o["width"] for o in c["options"]] == [_STACK_CONTENT_WIDTH, 700]
    assert "700" in c["question"] and str(_STACK_CONTENT_WIDTH) in c["question"]


def test_the_users_answer_to_keep_the_width_is_honored():
    """`overlap` is the other half of the decision, and it has to actually bind.

    A mechanism that reports the conflict and then widens anyway has only moved
    the silence into a log. So the requested width is what comes back, and the
    items keep the size the band's own metrics give them - which means they run
    PAST the band's right edge. That is the overlap the user asked for, and it is
    why `assert_result_sane` is deliberately not called here: its containment
    check is exactly the thing being overridden.
    """
    result = compose_layered_bands(_misfit_stack(), {"min_band_width": 700},
                                   on_misfit=FIT_OVERLAP)
    assert {rect_width(c) for c in result["containers"]} == {700}

    c = result["conflicts"][0]
    assert c["applied"] == FIT_OVERLAP
    assert c["width_applied"] == 700
    assert c["answered"] is True, "the choice is on the record, not a default"

    full = [it for it in result["items"] if it["band"] == "Full"]
    band = next(b for b in result["containers"] if b["name"] == "Full")
    assert max(it["right"] for it in full) > band["right"], (
        "overlap was asked for and nothing overlapped")
    # Still real geometry: every rect positive, nothing on top of anything else,
    # and the bounds account for the items that escaped their band.
    for it in result["items"]:
        assert_valid_rect(it, "overlap item")
    assert_no_overlaps(result["items"], "overlap items")
    assert result["bounds"] == bounding_box([*result["containers"],
                                            *result["items"]])


def test_a_stack_whose_content_fits_reports_no_conflict():
    """Silence has to mean something, so it only happens when nothing was decided.

    Two ways for there to be nothing to decide: no explicit width at all, and an
    explicit width the content fits. Both come back with an empty list rather
    than a missing key, so a consumer reads the same shape either way.
    """
    for spec in (None, {"min_band_width": 1000}):
        result = compose_layered_bands(_misfit_stack(), spec)
        assert result["conflicts"] == [], spec
        assert_result_sane(result, f"no conflict at {spec}")


def test_an_answer_that_is_not_one_of_the_two_is_refused():
    """A misspelled answer must not read as "nobody answered".

    Those are opposite states - one is a decision, the other is a question still
    owed - so a typo has to fail rather than silently fall through to the
    default. Refused whether or not this particular stack turns out to have a
    conflict, because a caller relaying an answer has already asked.
    """
    with pytest.raises(LayoutError, match="on_misfit"):
        compose_layered_bands(_misfit_stack(), {"min_band_width": 700},
                              on_misfit="wider")
    with pytest.raises(LayoutError, match="on_misfit"):
        compose_layered_bands(_misfit_stack(), on_misfit="wider")


def test_an_empty_band_is_widened_to_the_stack_even_with_a_huge_item_width():
    """The per-band floor is `item_width + 2 * pad`, and an empty band can have
    the widest `item_width` of all while holding nothing. Its floor then sets the
    stack's width, rather than being the one band that sticks out."""
    result = compose_layered_bands([
        {"name": "Populated", "items": _items("a", "b")},
        {"name": "Reserved", "items": [], "item_width": 900},
    ])
    widths = {rect_width(c) for c in result["containers"]}
    assert widths == {900 + 2 * 12}, widths
    assert_result_sane(result, "empty band sets the width")


# ---------------------------------------------------------------------------
# APT-2026-0152: bands take a common width, so the stack has a straight edge
# ---------------------------------------------------------------------------
def test_the_stack_that_scored_clean_and_looked_wrong_has_a_straight_edge():
    """The first end-to-end render: bands of 3, 3 and 2 items.

    It passed every metric - nothing overlapped, every rect was positive, the
    bounding box agreed with its contents, item sizing was uniform within each
    band - and it still looked wrong, because the third band stopped one item
    short of the two above it and the stack had a ragged right edge. No
    arithmetic check could see it; only a render could.
    """
    counts = [3, 3, 2]
    # The guard. Sized band by band, this input really does come out unequal:
    # the third band demands one h_pitch less than the other two. A stack whose
    # bands all demanded the same width would pass this test against the old
    # engine too, and prove nothing.
    demands = [_own_content_width(c) for c in counts]
    assert demands == [460, 460, 300], demands
    assert len(set(demands)) > 1, "this input does not discriminate"

    result = compose_layered_bands(_band_stack(counts))
    rights = [c["right"] for c in result["containers"]]
    widths = [rect_width(c) for c in result["containers"]]
    assert len(set(rights)) == 1, f"ragged right edge at {rights}"
    assert set(widths) == {max(demands) + 2 * DEFAULT_SPEC["band_pad_x"]}, widths

    # Heights still follow contents - only the width is shared. The sparse band
    # is the same height as the others here because it holds one row like they
    # do; `test_a_taller_band_pushes_the_next_band_further_down` pins the case
    # where they differ.
    assert_result_sane(result, "3/3/2")


def test_the_slack_in_a_sparse_band_is_real_whitespace_on_the_right():
    """Where the shared width goes in the band that did not ask for it.

    Measured as a GAP, deliberately. A no-overlap check cannot answer this:
    `rects_overlap` exempts rects that merely touch, so an item flush against
    its band's right edge would report no overlap and no whitespace would exist.
    """
    result = compose_layered_bands(_band_stack([4, 1]))
    sparse_band = result["containers"][1]
    lone = next(i for i in result["items"] if i["band_index"] == 1)
    slack = sparse_band["right"] - lone["right"]
    # Three h_pitches the sparse band did not use, plus its own right padding.
    assert slack == 3 * 160 + DEFAULT_SPEC["band_pad_x"], slack
    assert slack > 0, "no whitespace: the item is flush against the band edge"
    assert_contains(sparse_band, lone, "sparse band")


@pytest.mark.parametrize("counts", [
    [3, 3, 2],            # the render that found it
    [2, 3],
    [3, 2],
    [1, 5],
    [5, 1],
    [0, 3],
    [3, 0],
    [1, 2, 3],
    [3, 2, 1],
    [2, 1, 4, 1],
    [1, 1, 1, 7],
    [7, 1, 1, 1],
    [4, 0, 4, 2, 1],
    [6, 2, 9, 3],
    [1, 12],
    [12, 1],
    [2, 8, 5, 11, 1, 4],
])
def test_bands_share_one_width_across_unequal_item_counts(counts):
    """A SWEEP, not a spot-check. The defect is a content variation: it only

    shows up when the bands hold different numbers of items, so one hand-picked
    stack is exactly what let it ship. Every combination here is unequal, and
    each asserts its own inputs are discriminating before judging the output.
    """
    demands = [_own_content_width(c) for c in counts]
    assert len(set(demands)) > 1, f"{counts} does not discriminate"

    result = compose_layered_bands(_band_stack(counts))
    widths = {rect_width(c) for c in result["containers"]}
    lefts = {c["left"] for c in result["containers"]}
    rights = {c["right"] for c in result["containers"]}
    assert len(widths) == 1, f"{counts}: bands at {sorted(widths)}"
    assert len(lefts) == 1 and len(rights) == 1, f"{counts}: edges disagree"
    assert widths == {max(demands) + 2 * DEFAULT_SPEC["band_pad_x"]}
    # Every label strip spans its whole band, so the straight edge is drawn.
    for c in result["containers"]:
        assert rect_width(c["label"]) == rect_width(c)
    assert_result_sane(result, f"counts {counts}")


def test_the_shared_width_grows_monotonically_with_the_widest_band():
    """Swept monotonically on purpose.

    Comparing one crowded stack against one sparse stack can agree by luck -
    wrapping can put two different item counts on rows of the same length, the
    way a grid can give two different child counts the same column count. A
    monotone sweep cannot: the width has to be non-decreasing in the widest
    band's count, and has to stop growing exactly where wrapping starts.
    """
    wrap = 500                              # 140 wide, pitch 160 -> 3 per row
    pad = 2 * DEFAULT_SPEC["band_pad_x"]
    seen = []
    for widest in range(1, 13):
        result = compose_layered_bands(
            _band_stack([widest, 1, 0]), {"wrap_width": wrap})
        widths = {rect_width(c) for c in result["containers"]}
        assert len(widths) == 1, f"widest={widest}: {sorted(widths)}"
        width = widths.pop()
        assert width == _own_content_width(widest, wrap=wrap) + pad
        seen.append(width)
        assert_result_sane(result, f"widest={widest}")

    assert seen == sorted(seen), f"width is not monotone in the count: {seen}"
    # Growth up to the wrap, then a plateau: a band of four wraps and so asks
    # for no more width than a band of three.
    assert seen[0] < seen[1] < seen[2] == seen[3] == seen[-1]


@pytest.mark.parametrize("counts", [
    [3, 3, 2], [1, 5], [0, 3, 1], [12, 1], [4, 0, 4, 2, 1], [2, 8, 5, 11, 1, 4],
])
def test_the_shipped_linter_agrees_the_stack_is_not_ragged(counts):
    """THE OTHER SEAM. `lint.check_ragged_stack` judges this same defect.

    The linter has a rule for a stack of containers whose cross-axis extents
    disagree, written against the same render that produced APT-2026-0152 and
    tolerating `lint.SIZE_TOLERANCE`. It measures the finished rectangles; this
    engine produces them. Two independent statements of one rule drift apart
    unless something compares them, and this is that something.
    """
    lint = pytest.importorskip("lint")
    result = compose_layered_bands(_band_stack(counts))
    objects = [{"element_id": 1000 + i, "name": c["name"],
                "left": c["left"], "top": c["top"],
                "right": c["right"], "bottom": c["bottom"]}
               for i, c in enumerate(result["containers"])]
    b = result["bounds"]
    payload = {
        "objects": objects, "links": [],
        "canvas": {"left": b["left"] - 50, "top": b["top"] + 50,
                   "right": b["right"] + 50, "bottom": b["bottom"] - 50},
    }
    report = lint.lint_diagram(payload, stacks=[("vertical", objects)])
    fired = [f for f in report.findings if f.rule == "ragged-stack"]
    assert not fired, f"{counts}: {[f.message for f in fired]}"
    assert report.metrics["worst_stack_extent_spread"] == 0, counts


def test_a_band_with_no_items_key_is_treated_as_empty():
    result = compose_layered_bands([{"name": "Placeholder"}])
    assert result["items"] == []
    assert rect_height(result["containers"][0]) > 0
    assert_result_sane(result, "no items key")


def test_single_band_single_item():
    result = compose_layered_bands([{"name": "Only", "items": _items("solo")}])
    assert len(result["items"]) == 1
    assert len(result["containers"]) == 1
    item = result["items"][0]
    assert (rect_width(item), rect_height(item)) == (140, 60)
    assert item["row"] == 0 and item["column"] == 0
    assert_result_sane(result, "single item")


def test_band_item_records_carry_the_callers_id_and_name():
    result = compose_layered_bands([
        {"name": "Channels", "id": "band-channels",
         "items": [{"id": "elem-7", "name": "Online Banking"}]},
    ])
    item = result["items"][0]
    assert item["id"] == "elem-7"
    assert item["name"] == "Online Banking"
    assert item["container_id"] == "band-channels"
    assert item["band"] == "Channels"
    assert set(("left", "top", "right", "bottom")) <= set(item)
    assert result["containers"][0]["id"] == "band-channels"


def test_bands_survive_a_wide_sweep_of_shapes():
    shapes = [
        [1],
        [1, 1, 1],
        [0],
        [0, 3, 0],
        [12],
        [5, 1, 9, 2],
        [1] * 8,
        [30, 1],
    ]
    for shape in shapes:
        bands = []
        n = 0
        for b, count in enumerate(shape):
            ids = [f"e{n + k}" for k in range(count)]
            n += count
            bands.append({"name": f"Band {b}", "items": _items(*ids)})
        result = compose_layered_bands(bands, {"wrap_width": 620})
        assert len(result["items"]) == sum(shape)
        assert len(result["containers"]) == len(shape)
        assert_result_sane(result, f"shape {shape}")


# ===========================================================================
# 3. lanes
# ===========================================================================
def test_items_at_the_same_index_align_across_lanes_horizontally():
    """The invariant that makes a swimlane readable: a handoff lines up."""
    result = compose_lanes([
        {"name": "Customer", "items": _items("c1", "c2", "c3")},
        {"name": "Front Office", "items": _items("f1", "f2")},
        {"name": "Operations", "items": _items("o1", "o2", "o3")},
    ])
    by_index = {}
    for it in result["items"]:
        by_index.setdefault(it["index"], []).append(it)

    assert sorted(by_index) == [0, 1, 2]
    for idx, group in by_index.items():
        assert len({i["left"] for i in group}) == 1, f"index {idx} lefts disagree"
        assert len({i["right"] for i in group}) == 1, f"index {idx} rights disagree"
        assert len({i["slot_start"] for i in group}) == 1
        assert len({i["slot_extent"] for i in group}) == 1

    # and successive indexes really do advance along the flow axis
    lefts = [by_index[i][0]["left"] for i in sorted(by_index)]
    assert lefts == sorted(lefts) and len(set(lefts)) == 3
    assert_result_sane(result, "horizontal lanes")


def test_alignment_holds_when_lanes_size_their_items_differently():
    """Slots still agree; item centers agree to within one EA unit.

    Slot extent is the longest item at that index, and each item is centered in
    its slot with integer arithmetic, so an odd difference in size leaves a
    half-unit that has to land somewhere.
    """
    result = compose_lanes([
        {"name": "Customer", "items": _items("c1", "c2"), "item_width": 200},
        {"name": "Operations", "items": _items("o1", "o2"), "item_width": 145},
    ])
    by_index = {}
    for it in result["items"]:
        by_index.setdefault(it["index"], []).append(it)

    for idx, group in by_index.items():
        assert len({i["slot_start"] for i in group}) == 1, f"index {idx} slots differ"
        assert len({i["slot_extent"] for i in group}) == 1
        assert {i["slot_extent"] for i in group} == {200}
        centers = {_center_x2(i) for i in group}
        assert max(centers) - min(centers) <= 1, f"index {idx} centers drift"
    assert_result_sane(result, "mixed lane item widths")


def test_slot_length_is_the_longest_item_in_any_lane_not_the_first_lane():
    """The widest lane sets the slot wherever it happens to sit in the order.

    Reversing the lanes must produce the same slot table, and the narrow lane's
    items must be inset within it rather than butted against its start.
    """
    wide_first = compose_lanes([
        {"name": "Customer", "items": _items("c1", "c2"), "item_width": 240},
        {"name": "Operations", "items": _items("o1", "o2")},
    ])
    wide_last = compose_lanes([
        {"name": "Operations", "items": _items("o1", "o2")},
        {"name": "Customer", "items": _items("c1", "c2"), "item_width": 240},
    ])

    def slots(result):
        return sorted({(i["index"], i["slot_start"], i["slot_extent"])
                       for i in result["items"]})

    assert slots(wide_first) == slots(wide_last)
    assert [s[2] for s in slots(wide_first)] == [240, 240]

    for result in (wide_first, wide_last):
        for item in result["items"]:
            if rect_width(item) == 240:
                assert item["left"] == item["slot_start"]
            else:
                assert item["left"] == item["slot_start"] + 50   # (240 - 140) // 2
        assert_result_sane(result, "wide lane not first")


def test_vertical_lanes_flow_downward_and_still_align():
    result = compose_lanes(
        [
            {"name": "Customer", "items": _items("c1", "c2", "c3")},
            {"name": "Operations", "items": _items("o1", "o2")},
        ],
        orientation="vertical",
    )
    assert result["orientation"] == "vertical"

    # lanes sit side by side, left to right
    lefts = [c["left"] for c in result["containers"]]
    assert lefts == sorted(lefts) and len(set(lefts)) == 2
    assert {c["top"] for c in result["containers"]} == {DEFAULT_SPEC["origin_top"]}

    by_index = {}
    for it in result["items"]:
        by_index.setdefault(it["index"], []).append(it)
    for idx, group in by_index.items():
        assert len({i["top"] for i in group}) == 1, f"index {idx} tops disagree"
        assert len({i["bottom"] for i in group}) == 1

    lane0 = [i for i in result["items"] if i["lane_index"] == 0]
    tops = [i["top"] for i in sorted(lane0, key=lambda i: i["index"])]
    assert tops == sorted(tops, reverse=True), "flow runs downward"
    assert_result_sane(result, "vertical lanes")


def test_items_are_centered_across_the_lane_thickness():
    result = compose_lanes([
        {"name": "Customer", "items": _items("c1")},
        {"name": "Operations", "items": _items("o1")},
    ])
    for container in result["containers"]:
        item = next(i for i in result["items"]
                    if i["container_id"] == container["id"])
        top_gap = container["top"] - item["top"]
        bottom_gap = item["bottom"] - container["bottom"]
        assert abs(top_gap - bottom_gap) <= 1, "item not centered across the lane"
        assert top_gap >= DEFAULT_SPEC["lane_pad"]


def test_lane_thickness_follows_the_largest_item_in_that_lane():
    result = compose_lanes([
        {"name": "Customer", "items": _items("c1")},
        {"name": "Operations", "items": _items("o1"), "item_height": 160},
    ])
    thin, thick = result["containers"]
    assert rect_height(thin) == 60 + 2 * DEFAULT_SPEC["lane_pad"]
    assert rect_height(thick) == 160 + 2 * DEFAULT_SPEC["lane_pad"]
    assert rect_height(thick) > rect_height(thin)
    assert_result_sane(result, "adaptive thickness")


def test_min_lane_thickness_pads_a_thin_lane_and_yields_to_a_thick_one():
    result = compose_lanes(
        [{"name": "Thin", "items": _items("a")},
         {"name": "Thick", "items": _items("b"), "item_height": 300}],
        {"min_lane_thickness": 200},
    )
    thin, thick = result["containers"]
    assert rect_height(thin) == 200
    assert rect_height(thick) == 300 + 2 * DEFAULT_SPEC["lane_pad"]
    assert_result_sane(result, "min_lane_thickness")


def test_lanes_abut_exactly_by_default():
    horizontal = compose_lanes([
        {"name": "A", "items": _items("a")},
        {"name": "B", "items": _items("b"), "item_height": 120},
        {"name": "C", "items": _items("c")},
    ])
    for upper, lower in zip(horizontal["containers"], horizontal["containers"][1:]):
        assert lower["top"] == upper["bottom"], "horizontal lanes must touch"
    assert len({rect_width(c) for c in horizontal["containers"]}) == 1

    vertical = compose_lanes(
        [{"name": "A", "items": _items("a")}, {"name": "B", "items": _items("b")}],
        orientation="vertical",
    )
    for left_lane, right_lane in zip(vertical["containers"], vertical["containers"][1:]):
        assert right_lane["left"] == left_lane["right"], "vertical lanes must touch"
    assert len({rect_height(c) for c in vertical["containers"]}) == 1


def test_lane_gap_separates_lanes_when_asked():
    result = compose_lanes(
        [{"name": "A", "items": _items("a")}, {"name": "B", "items": _items("b")}],
        {"lane_gap": 24},
    )
    upper, lower = result["containers"]
    assert upper["bottom"] - lower["top"] == 24
    assert_result_sane(result, "separated lanes")


def test_a_lane_label_area_never_collides_with_its_items():
    result = compose_lanes([{"name": "Customer", "items": _items("c1", "c2")}])
    label = result["containers"][0]["label"]
    for item in result["items"]:
        assert not rects_overlap(label, item)
    assert rect_width(label) == DEFAULT_SPEC["label_width"]
    assert rect_height(label) == rect_height(result["containers"][0])

    vertical = compose_lanes(
        [{"name": "Customer", "items": _items("c1", "c2")}], orientation="vertical"
    )
    vlabel = vertical["containers"][0]["label"]
    for item in vertical["items"]:
        assert not rects_overlap(vlabel, item)
    assert rect_height(vlabel) == DEFAULT_SPEC["label_height"]


def test_an_empty_lane_is_valid_geometry():
    result = compose_lanes([
        {"name": "Customer", "items": _items("c1", "c2")},
        {"name": "Risk", "items": []},
    ])
    empty = result["containers"][1]
    assert rect_height(empty) >= 60 + 2 * DEFAULT_SPEC["lane_pad"]
    assert rect_width(empty) == rect_width(result["containers"][0])
    assert_result_sane(result, "empty lane")


def test_every_lane_empty_still_produces_lane_bands():
    result = compose_lanes([{"name": "A"}, {"name": "B"}])
    assert result["items"] == []
    assert len(result["containers"]) == 2
    for c in result["containers"]:
        assert_valid_rect(c, "all-empty lanes")
    assert_result_sane(result, "all-empty lanes")


def test_single_lane_single_item():
    result = compose_lanes([{"name": "Only", "items": _items("solo")}])
    assert len(result["items"]) == 1
    item = result["items"][0]
    assert item["index"] == 0
    assert item["slot_extent"] == 140
    assert_result_sane(result, "single lane")


def test_flow_pitch_acts_as_a_floor_on_slot_spacing():
    tight = compose_lanes([{"name": "A", "items": _items("a", "b")}])
    loose = compose_lanes(
        [{"name": "A", "items": _items("a", "b")}], {"flow_pitch": 400}
    )
    tight_step = tight["items"][1]["left"] - tight["items"][0]["left"]
    loose_step = loose["items"][1]["left"] - loose["items"][0]["left"]
    assert tight_step == 140 + DEFAULT_SPEC["item_gap_flow"]
    assert loose_step == 400
    assert_result_sane(loose, "flow_pitch")


def test_lanes_survive_a_wide_sweep_of_shapes():
    shapes = [[1], [0], [0, 0], [1, 5], [3, 3, 3], [7, 1, 4], [1] * 6, [12, 0, 2]]
    for orientation in ("horizontal", "vertical"):
        for shape in shapes:
            lanes = []
            n = 0
            for lane_no, count in enumerate(shape):
                ids = [f"e{n + k}" for k in range(count)]
                n += count
                lanes.append({"name": f"Lane {lane_no}", "items": _items(*ids)})
            result = compose_lanes(lanes, orientation=orientation)
            assert len(result["items"]) == sum(shape)
            assert len(result["containers"]) == len(shape)
            assert_result_sane(result, f"{orientation} shape {shape}")


# ===========================================================================
# 4. Determinism
# ===========================================================================
def test_bands_are_deterministic():
    bands = [
        {"name": "Channels", "items": _items("a", "b", "c", "d", "e")},
        {"name": "Applications", "items": _items("f", "g"), "item_width": 200},
        {"name": "Reserved", "items": []},
    ]
    spec = {"wrap_width": 460, "align": "center", "band_gap": 25}
    first = compose_layered_bands(bands, spec)
    second = compose_layered_bands(bands, spec)
    assert first == second


def test_lanes_are_deterministic():
    lanes = [
        {"name": "Customer", "items": _items("c1", "c2", "c3")},
        {"name": "Operations", "items": _items("o1"), "item_height": 120},
    ]
    first = compose_lanes(lanes, {"lane_pad": 8}, orientation="vertical")
    second = compose_lanes(lanes, {"lane_pad": 8}, orientation="vertical")
    assert first == second


def test_output_does_not_depend_on_spec_key_insertion_order():
    forwards = {"item_width": 150, "item_height": 70, "wrap_width": 700,
                "band_gap": 40, "align": "center"}
    backwards = {k: forwards[k] for k in reversed(list(forwards))}
    bands = [{"name": "A", "items": _items("a", "b", "c", "d", "e", "f")},
             {"name": "B", "items": _items("g")}]
    assert compose_layered_bands(bands, forwards) == compose_layered_bands(
        bands, backwards
    )


# ===========================================================================
# 5. Validation - a clear error beats silently wrong geometry
# ===========================================================================
def test_negative_and_zero_sizes_are_rejected_by_name():
    with pytest.raises(LayoutError, match=r"spec\.item_width"):
        compose_layered_bands([{"name": "A", "items": _items("a")}],
                              {"item_width": -140})
    with pytest.raises(LayoutError, match=r"spec\.item_height"):
        compose_layered_bands([{"name": "A", "items": _items("a")}],
                              {"item_height": 0})
    with pytest.raises(LayoutError, match=r"spec\.band_gap"):
        compose_layered_bands([{"name": "A", "items": _items("a")}],
                              {"band_gap": -5})


def test_zero_pitch_is_rejected():
    with pytest.raises(LayoutError, match=r"spec\.h_pitch"):
        compose_layered_bands([{"name": "A", "items": _items("a")}], {"h_pitch": 0})
    with pytest.raises(LayoutError, match=r"spec\.row_pitch"):
        compose_layered_bands([{"name": "A", "items": _items("a")}], {"row_pitch": 0})
    with pytest.raises(LayoutError, match=r"spec\.flow_pitch"):
        compose_lanes([{"name": "A", "items": _items("a")}], {"flow_pitch": 0})


def test_a_pitch_smaller_than_the_item_is_rejected_rather_than_overlapped():
    with pytest.raises(LayoutError, match="h_pitch.*smaller than item_width"):
        compose_layered_bands([{"name": "A", "items": _items("a", "b")}],
                              {"h_pitch": 100})
    with pytest.raises(LayoutError, match="row_pitch.*smaller than item_height"):
        compose_layered_bands([{"name": "A", "items": _items("a", "b")}],
                              {"row_pitch": 40})


def test_a_wrap_width_narrower_than_one_item_is_rejected():
    with pytest.raises(LayoutError, match="wrap_width.*smaller than item_width"):
        compose_layered_bands([{"name": "A", "items": _items("a")}],
                              {"wrap_width": 100})


def test_an_item_with_no_id_names_its_own_position():
    with pytest.raises(LayoutError, match=r"bands\[1\]\.items\[2\]\.id"):
        compose_layered_bands([
            {"name": "A", "items": _items("a")},
            {"name": "B", "items": [{"id": "b"}, {"id": "c"}, {"name": "no id"}]},
        ])
    with pytest.raises(LayoutError, match=r"lanes\[0\]\.items\[0\]\.id"):
        compose_lanes([{"name": "A", "items": [{"id": "  "}]}])


def test_duplicate_item_ids_are_rejected_across_the_whole_composition():
    with pytest.raises(LayoutError, match="duplicate item id 'a'"):
        compose_layered_bands([
            {"name": "A", "items": _items("a")},
            {"name": "B", "items": _items("b", "a")},
        ])


def test_an_unknown_spec_key_is_an_error_not_a_shrug():
    with pytest.raises(LayoutError, match="unknown key"):
        compose_layered_bands([{"name": "A", "items": _items("a")}],
                              {"itemWidth": 200})


def test_bad_enum_values_are_rejected():
    with pytest.raises(LayoutError, match=r"spec\.align"):
        compose_layered_bands([{"name": "A", "items": _items("a")}],
                              {"align": "middle"})
    with pytest.raises(LayoutError, match="orientation"):
        compose_lanes([{"name": "A", "items": _items("a")}], orientation="sideways")


def test_a_band_or_lane_needs_a_name():
    with pytest.raises(LayoutError, match=r"bands\[0\]\.name"):
        compose_layered_bands([{"items": _items("a")}])
    with pytest.raises(LayoutError, match=r"lanes\[1\]\.name"):
        compose_lanes([{"name": "A"}, {"name": "   "}])


def test_the_wrong_container_type_is_reported_with_its_path():
    with pytest.raises(LayoutError, match=r"bands\[0\]: expected a dict"):
        compose_layered_bands(["Channels"])
    with pytest.raises(LayoutError, match=r"bands\[0\]\.items: expected a list"):
        compose_layered_bands([{"name": "A", "items": {"id": "a"}}])
    with pytest.raises(LayoutError, match="bands: expected a list"):
        compose_layered_bands({"name": "A"})
    with pytest.raises(LayoutError, match="spec: expected a dict"):
        compose_layered_bands([{"name": "A", "items": _items("a")}], spec=[1, 2])


def test_nothing_to_place_is_an_error_not_an_empty_canvas():
    with pytest.raises(LayoutError, match="at least one band"):
        compose_layered_bands([])
    with pytest.raises(LayoutError, match="at least one lane"):
        compose_lanes([])


def test_booleans_are_not_accepted_as_sizes():
    with pytest.raises(LayoutError, match=r"spec\.item_width: expected a number"):
        compose_layered_bands([{"name": "A", "items": _items("a")}],
                              {"item_width": True})


def test_a_bad_per_band_override_names_the_band():
    with pytest.raises(LayoutError, match=r"bands\[1\]\.item_height"):
        compose_layered_bands([
            {"name": "A", "items": _items("a")},
            {"name": "B", "items": _items("b"), "item_height": -60},
        ])
    with pytest.raises(LayoutError, match=r"lanes\[0\]\.item_width"):
        compose_lanes([{"name": "A", "items": _items("a"), "item_width": 0}])


if __name__ == "__main__":       # pragma: no cover
    raise SystemExit(pytest.main([__file__, "-q"]))


# ---------------------------------------------------------------------------
# Item ids: any hashable, preserved verbatim
# ---------------------------------------------------------------------------

def test_integer_ids_are_accepted_and_preserved():
    """EA element ids are integers.

    Requiring strings would force a str() at every call site and invite the
    classic "123" != 123 bug when the composed rects are matched back against
    the model.
    """
    result = compose_layered_bands([
        {"name": "Band", "items": [{"id": 13477}, {"id": 13478}]},
    ])
    ids = [item["id"] for item in result["items"]]
    assert ids == [13477, 13478]
    assert all(isinstance(i, int) for i in ids), "ids must not be stringified"


def test_mixed_id_types_still_collide_when_equal():
    """Uniqueness is by value, so a duplicate is caught whatever its type."""
    with pytest.raises(LayoutError, match="duplicate"):
        compose_layered_bands([
            {"name": "Band", "items": [{"id": 7}, {"id": 7}]},
        ])


def test_int_and_string_forms_of_the_same_number_are_different_ids():
    """7 and "7" are genuinely different element references; treating them as
    the same would be a guess about the caller's intent."""
    result = compose_layered_bands([
        {"name": "Band", "items": [{"id": 7}, {"id": "7"}]},
    ])
    assert [item["id"] for item in result["items"]] == [7, "7"]


def test_a_missing_id_is_still_an_error():
    with pytest.raises(LayoutError, match="non-empty id"):
        compose_layered_bands([{"name": "Band", "items": [{"name": "no id"}]}])


def test_an_unhashable_id_is_rejected_with_a_clear_reason():
    with pytest.raises(LayoutError, match="hashable"):
        compose_layered_bands([{"name": "Band", "items": [{"id": ["a", "list"]}]}])


# ===========================================================================
# 6. Nested grid
# ===========================================================================
# `assert_result_sane` deliberately does NOT apply here. Two of its checks are
# wrong for this grammar by design:
#
#   * it asserts no two containers overlap, and a subdomain inside a domain is
#     supposed to overlap its parent;
#   * it looks every item's `container_id` up in the container table, and a
#     root-level leaf has none.
#
# So this grammar gets its own sanity helper, which is strictly stronger: it
# checks no-overlap among SIBLINGS at every level and containment at every
# level, rather than once over one flat set.
def _tree_index(result):
    """Group a nested-grid result by parent, so siblings can be compared.

    Returns `{parent_id: [rect, ...]}` covering containers and items together,
    because a leaf and a container sharing a parent are siblings and must not
    overlap each other either.
    """
    by_parent = {}
    for c in result["containers"]:
        by_parent.setdefault(c["parent_id"], []).append(c)
    for it in result["items"]:
        by_parent.setdefault(it["container_id"], []).append(it)
    return by_parent


def assert_nested_result_sane(result, label=""):
    """Every check that must hold for any nested grid, at every level."""
    containers = {c["id"]: c for c in result["containers"]}
    for c in result["containers"]:
        assert_valid_rect(c, f"{label} container {c['id']}")
        assert_valid_rect(c["label"], f"{label} label of {c['id']}")
        assert_contains(c, c["label"], f"{label} label of {c['id']}")
    for it in result["items"]:
        assert_valid_rect(it, f"{label} item {it['id']}")

    by_parent = _tree_index(result)
    for parent_id, siblings in by_parent.items():
        assert_no_overlaps(siblings, f"{label} siblings under {parent_id!r}")
        if parent_id is not None:
            for child in siblings:
                assert_contains(
                    containers[parent_id], child,
                    f"{label} {child.get('id')} inside {parent_id!r}",
                )

    # Containment is transitive, but assert it against every ancestor anyway:
    # a child that fits its parent while its parent overflows the grandparent
    # is the failure this grammar is most likely to produce.
    for c in result["containers"]:
        ancestor = containers.get(c["parent_id"])
        while ancestor is not None:
            assert_contains(ancestor, c, f"{label} {c['id']} in {ancestor['id']}")
            ancestor = containers.get(ancestor["parent_id"])

    expected = bounding_box([*result["containers"], *result["items"]])
    assert result["bounds"] == expected, f"{label}: bounds disagree with contents"


def _group(name, children, **extra):
    return {"name": name, "items": children, **extra}


# A two-level tree used by several tests: three top-level groups of unequal
# size, one of them nesting a further level, and one loose leaf at the top.
def _sample_tree():
    return [
        _group("Customer", [
            _group("Onboarding", _items(101, 102, 103)),
            _group("Servicing", _items(104)),
        ]),
        _group("Payments", _items(105, 106, 107, 108)),
        _group("Risk", _items(109)),
    ]


# ---------------------------------------------------------------------------
# Structure: containment and no overlaps, at every level
# ---------------------------------------------------------------------------
def test_a_nested_grid_is_sane_at_every_level():
    result = compose_nested_grid(_sample_tree())
    assert result["grammar"] == "nested_grid"
    assert_nested_result_sane(result, "sample tree")
    assert len(result["items"]) == 9
    assert {c["name"] for c in result["containers"]} == {
        "Customer", "Onboarding", "Servicing", "Payments", "Risk",
    }


def test_every_leaf_sits_inside_the_container_that_declared_it():
    """The mapping from `container_id` back to the declaring group must hold.

    Geometry alone is not enough: a leaf could sit inside the RIGHT rect while
    being reported under the wrong parent, and a caller building EA's ownership
    relationships from `container_id` would then nest the element under the
    wrong element while the picture looked correct.
    """
    result = compose_nested_grid(_sample_tree())
    by_id = {c["id"]: c for c in result["containers"]}
    declared = {
        101: "Onboarding", 102: "Onboarding", 103: "Onboarding",
        104: "Servicing",
        105: "Payments", 106: "Payments", 107: "Payments", 108: "Payments",
        109: "Risk",
    }
    for item in result["items"]:
        parent = by_id[item["container_id"]]
        assert parent["name"] == declared[item["id"]], item
        assert_contains(parent, item, f"item {item['id']}")


def test_depth_counts_grid_levels_from_one():
    result = compose_nested_grid(_sample_tree())
    depths = {c["name"]: c["depth"] for c in result["containers"]}
    assert depths["Customer"] == 1
    assert depths["Payments"] == 1
    assert depths["Onboarding"] == 2
    by_id = {c["id"]: c for c in result["containers"]}
    for item in result["items"]:
        assert item["depth"] == by_id[item["container_id"]]["depth"] + 1


def test_a_root_level_leaf_has_no_container():
    """A leaf at the top level is legitimate and comes back with no parent.

    `container_id: None` rather than a sentinel string, so a caller that forgets
    to handle it raises on the lookup instead of silently nesting the element
    under a group called "None".
    """
    result = compose_nested_grid([
        {"id": "loose"},
        _group("Grouped", _items("inner")),
    ])
    loose = next(i for i in result["items"] if i["id"] == "loose")
    assert loose["container_id"] is None
    assert loose["depth"] == 1
    assert_nested_result_sane(result, "root leaf")


# ---------------------------------------------------------------------------
# Sizing: uniform within a level, content-driven between containers
# ---------------------------------------------------------------------------
def test_every_leaf_in_one_grid_is_the_same_size():
    result = compose_nested_grid(_sample_tree())
    by_parent = {}
    for item in result["items"]:
        by_parent.setdefault(item["container_id"], []).append(item)
    for parent, items in by_parent.items():
        sizes = {(rect_width(i), rect_height(i)) for i in items}
        assert len(sizes) == 1, f"{parent}: siblings disagree about size {sizes}"


def test_a_leaf_has_nowhere_to_state_a_size_of_its_own():
    """Sibling uniformity is structural, not a rule the caller must remember.

    Item size is stated by the PARENT. A leaf carrying `item_width` is therefore
    an unknown key on a leaf - and since the leaf's only recognized key is `id`,
    the size is simply ignored rather than honoured. This test pins that it is
    ignored, because the alternative - honouring it - is what lets two siblings
    end up different sizes, the defect the grammar's own rule exists to prevent.
    """
    plain = compose_nested_grid([_group("G", [{"id": 1}, {"id": 2}])])
    shouty = compose_nested_grid([_group("G", [
        {"id": 1, "item_width": 400, "item_height": 400},
        {"id": 2},
    ])])
    assert plain["items"] == shouty["items"]
    assert plain["bounds"] == shouty["bounds"]


def test_levels_may_size_their_items_differently():
    """A container restates the size for its OWN children, not for its
    grandchildren - so "levels may differ" is expressible and does not leak."""
    result = compose_nested_grid([
        _group("Outer", [
            _group("Inner", _items(1, 2)),
            {"id": 3},
        ], item_width=200, item_height=90),
    ])
    by_id = {i["id"]: i for i in result["items"]}
    # The direct child of Outer takes Outer's override.
    assert rect_width(by_id[3]) == 200
    assert rect_height(by_id[3]) == 90
    # The grandchildren do NOT inherit it; they fall back to the spec default.
    assert rect_width(by_id[1]) == DEFAULT_SPEC["item_width"]
    assert rect_height(by_id[1]) == DEFAULT_SPEC["item_height"]
    assert rect_width(by_id[1]) != 200
    assert_nested_result_sane(result, "per-level sizing")


def test_a_container_is_sized_by_its_contents():
    """A group with many children is visibly bigger than one with few.

    This is the property that keeps a nested grid honest: containers sized alike
    would make a group holding two things look as significant as one holding
    twenty.
    """
    result = compose_nested_grid([
        _group("Big", _items(*range(1, 10))),
        _group("Small", _items(99)),
    ])
    big = next(c for c in result["containers"] if c["name"] == "Big")
    small = next(c for c in result["containers"] if c["name"] == "Small")
    assert rect_width(big) > rect_width(small)


def test_a_container_is_never_stretched_to_match_a_bigger_sibling():
    """Content sizing beats edge alignment, deliberately, for this grammar.

    The first implementation snapped every container to its cell, so a row of
    containers shared one height and the edges lined up. It looked tidier and it
    was wrong: a four-child capability and a two-child one came out at exactly
    the same 324x192, which is the failure `references/grammars.md` names for
    this grammar - "containers are sized alike so a container with two children
    looks as significant as one with twenty".

    The cost is a ragged bottom edge within a row, and that cost is accepted
    here. It is NOT the same question as `APT-2026-0152`: a band is a full-width
    strip whose raggedness reads as a mistake, while a grid of differently sized
    groups is what a capability map is supposed to look like.
    """
    result = compose_nested_grid([
        _group("Tall", [_group("A", _items(1, 2)), _group("B", _items(3, 4))]),
        _group("Short", _items(5)),
    ], spec={"grid_columns": 2})
    tall = next(c for c in result["containers"] if c["name"] == "Tall")
    short = next(c for c in result["containers"] if c["name"] == "Short")
    assert tall["row"] == short["row"] == 0
    assert tall["top"] == short["top"], "a row should still start level"
    assert rect_height(tall) > rect_height(short), (
        "the sparser container was stretched to match its sibling"
    )
    assert rect_width(tall) > rect_width(short)
    # The slack left in the cell is empty space, not a collision.
    assert_nested_result_sane(result, "ragged row")


def test_more_children_never_means_a_smaller_container():
    """The monotonic form of the rule, swept rather than spot-checked.

    Spot-checking two shapes is how the previous version of this passed while
    4-vs-2 children produced identical boxes: 9-vs-1 happened to differ.
    """
    areas = []
    for n in range(1, 13):
        result = compose_nested_grid([_group("G", _items(*range(n)))])
        group = result["containers"][0]
        areas.append(rect_width(group) * rect_height(group))
    for smaller, bigger in zip(areas, areas[1:]):
        assert bigger >= smaller, areas
    assert areas[-1] > areas[0], "twelve children must not fit in one child's box"


def test_a_leaf_is_centered_in_a_cell_taller_than_itself():
    """Derived from a sibling that fills the same row, so no literal is needed."""
    result = compose_nested_grid([
        _group("Row", [_group("HasChildren", _items(1, 2, 3)), {"id": 4}]),
    ], spec={"grid_columns": 2})
    filler = next(c for c in result["containers"] if c["name"] == "HasChildren")
    leaf = next(i for i in result["items"] if i["id"] == 4)
    assert filler["row"] == leaf["row"] == 0
    assert rect_height(leaf) < rect_height(filler), "no slack to center in"
    assert _center_y2(leaf) == _center_y2(filler)


# ---------------------------------------------------------------------------
# Grid shape
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("n", [1, 2, 3, 4, 5, 6, 9, 10, 16, 17])
def test_grids_come_out_close_to_square(n):
    """Columns are ceil(sqrt(n)), computed here independently of the engine."""
    expected = math.isqrt(n - 1) + 1 if n > 1 else 1
    result = compose_nested_grid([_group("G", _items(*range(n)))])
    columns = max(i["column"] for i in result["items"]) + 1
    rows = max(i["row"] for i in result["items"]) + 1
    assert columns == expected, f"n={n}"
    assert rows == -(-n // expected)
    assert_nested_result_sane(result, f"square n={n}")


def test_grid_columns_fixes_the_column_count():
    result = compose_nested_grid(
        [_group("G", _items(*range(6)))], spec={"grid_columns": 3}
    )
    assert max(i["column"] for i in result["items"]) + 1 == 3
    assert max(i["row"] for i in result["items"]) + 1 == 2


def test_a_container_may_fix_its_own_column_count():
    result = compose_nested_grid([
        _group("Wide", _items(*range(4)), grid_columns=4),
        _group("Narrow", _items(*range(10, 14)), grid_columns=1),
    ])
    wide = [i for i in result["items"] if i["id"] < 10]
    narrow = [i for i in result["items"] if i["id"] >= 10]
    assert max(i["row"] for i in wide) == 0
    assert max(i["column"] for i in narrow) == 0
    assert_nested_result_sane(result, "per-container columns")


def test_more_columns_than_children_does_not_leave_empty_columns():
    """A column count above the child count collapses to the child count.

    Otherwise the container would be padded out with the width of columns that
    hold nothing, and a group of two would be drawn as wide as a group of ten.
    """
    tight = compose_nested_grid([_group("G", _items(1, 2))],
                                spec={"grid_columns": 2})
    loose = compose_nested_grid([_group("G", _items(1, 2))],
                                spec={"grid_columns": 9})
    assert tight["bounds"] == loose["bounds"]


# ---------------------------------------------------------------------------
# Whitespace between cells
# ---------------------------------------------------------------------------
# These exist because `assert_nested_result_sane` CANNOT see a missing gap.
# `rects_overlap` exempts rects that merely touch - abutting swimlanes are
# correct geometry - so a grid that dropped `item_gap_x` entirely and packed
# every cell edge to edge passed every other test in this file. A no-overlap
# rule never implies whitespace, and this grammar's whole job is whitespace.
def test_adjacent_cells_are_separated_by_the_item_gap():
    """Measured on an all-leaf grid, where a cell is exactly one item wide, so
    the leaf-to-leaf gap IS the cell gap with no centering slack in between."""
    gap_x, gap_y = 24, 18
    result = compose_nested_grid(
        [_group("G", _items(*range(6)))],
        spec={"grid_columns": 3, "item_gap_x": gap_x, "item_gap_y": gap_y},
    )
    by_cell = {(i["row"], i["column"]): i for i in result["items"]}
    assert len(by_cell) == 6
    for (row, col), item in by_cell.items():
        right = by_cell.get((row, col + 1))
        if right is not None:
            assert right["left"] - item["right"] == gap_x
        below = by_cell.get((row + 1, col))
        if below is not None:
            assert item["bottom"] - below["top"] == gap_y


def test_the_default_spec_leaves_real_whitespace_between_cells():
    """The defaults have to be usable without a spec, and a grid with no
    whitespace is not - it reads as one block, not as a set of things."""
    assert DEFAULT_SPEC["item_gap_x"] > 0
    assert DEFAULT_SPEC["item_gap_y"] > 0
    result = compose_nested_grid([_group("G", _items(1, 2, 3, 4))])
    by_cell = {(i["row"], i["column"]): i for i in result["items"]}
    assert by_cell[(0, 1)]["left"] - by_cell[(0, 0)]["right"] > 0
    assert by_cell[(0, 0)]["bottom"] - by_cell[(1, 0)]["top"] > 0


def test_sibling_containers_are_separated_by_the_item_gap():
    gap = 30
    result = compose_nested_grid(
        [_group("A", _items(1)), _group("B", _items(2))],
        spec={"grid_columns": 2, "item_gap_x": gap},
    )
    a, b = sorted(result["containers"], key=lambda c: c["left"])
    assert b["left"] - a["right"] == gap


# ---------------------------------------------------------------------------
# Padding and labels
# ---------------------------------------------------------------------------
def test_padding_is_constant_with_the_title_strip_as_an_extra_top_inset():
    """Read off a single-child container, against DEFAULT_SPEC rather than
    literals, so a change to the defaults cannot leave this test asserting a
    number nobody ships any more."""
    result = compose_nested_grid([_group("G", _items(1))])
    group = result["containers"][0]
    child = result["items"][0]
    pad = DEFAULT_SPEC["grid_pad"]
    assert child["left"] - group["left"] == pad
    assert group["right"] - child["right"] == pad
    assert group["bottom"] - child["bottom"] == -pad
    assert group["top"] - child["top"] == DEFAULT_SPEC["label_height"] + pad


def test_a_container_label_never_collides_with_its_children():
    result = compose_nested_grid(_sample_tree())
    for container in result["containers"]:
        for child in _tree_index(result).get(container["id"], []):
            assert not rects_overlap(container["label"], child), (
                f"{container['name']} label overlaps {child.get('id')}"
            )


def test_an_empty_container_keeps_its_label_and_one_cell_of_space():
    result = compose_nested_grid([_group("Planned", [])])
    group = result["containers"][0]
    assert result["items"] == []
    assert rect_width(group) == (
        DEFAULT_SPEC["item_width"] + 2 * DEFAULT_SPEC["grid_pad"]
    )
    assert rect_height(group) == (
        DEFAULT_SPEC["label_height"] + DEFAULT_SPEC["item_height"]
        + 2 * DEFAULT_SPEC["grid_pad"]
    )
    assert_nested_result_sane(result, "empty container")


def test_an_items_key_makes_a_container_even_when_it_is_empty():
    """`items: []` is a container, not a leaf that lost its children.

    The discriminator is the presence of the KEY. If it were truthiness, a group
    whose last child was removed would silently turn into a leaf - and a leaf
    with no `id` is an error, so the diagram would start failing to build for a
    reason unrelated to the edit that caused it.
    """
    result = compose_nested_grid([_group("Still A Group", [])])
    assert [c["name"] for c in result["containers"]] == ["Still A Group"]
    assert result["items"] == []


# ---------------------------------------------------------------------------
# The depth bound
# ---------------------------------------------------------------------------
def _nest(depth, leaf_id="leaf"):
    """A chain of `depth` containers with one leaf at the bottom."""
    node = {"id": leaf_id}
    for level in range(depth, 0, -1):
        node = _group(f"L{level}", [node])
    return [node]


def test_three_levels_of_containment_are_allowed_by_default():
    result = compose_nested_grid(_nest(3))
    assert max(c["depth"] for c in result["containers"]) == 3
    assert result["items"][0]["depth"] == 4
    assert_nested_result_sane(result, "three levels")


def test_nesting_past_the_bound_is_refused_and_names_the_path():
    with pytest.raises(LayoutError) as exc:
        compose_nested_grid(_nest(4))
    message = str(exc.value)
    # Wording only this branch produces - the generic "unknown key" and
    # "must be positive" messages would both match a bare "max_grid_depth".
    assert "containers deep" in message
    assert "nodes[0].items[0].items[0].items[0]" in message
    assert str(DEFAULT_SPEC["max_grid_depth"]) in message


def test_the_depth_bound_is_a_refusal_not_a_warning():
    """Recorded as a decision, not an accident: the result dict has no channel
    a warning could travel down that any caller reads, so a deeper tree raises.
    A caller who genuinely wants four levels raises the bound and says so."""
    deep = _nest(4)
    with pytest.raises(LayoutError):
        compose_nested_grid(deep)
    result = compose_nested_grid(deep, spec={"max_grid_depth": 4})
    assert max(c["depth"] for c in result["containers"]) == 4
    assert_nested_result_sane(result, "four levels, asked for")


def test_a_shallower_bound_refuses_what_the_default_allows():
    two = _nest(3)
    compose_nested_grid(two)  # fine by default
    with pytest.raises(LayoutError, match="containers deep"):
        compose_nested_grid(two, spec={"max_grid_depth": 2})


# ---------------------------------------------------------------------------
# Determinism
# ---------------------------------------------------------------------------
def test_nested_grid_is_deterministic():
    tree = _sample_tree()
    assert compose_nested_grid(tree) == compose_nested_grid(_sample_tree())
    assert compose_nested_grid(tree) == compose_nested_grid(tree)


def test_nested_grid_ignores_spec_key_insertion_order():
    a = compose_nested_grid(_sample_tree(),
                            spec={"grid_pad": 8, "grid_columns": 2})
    b = compose_nested_grid(_sample_tree(),
                            spec={"grid_columns": 2, "grid_pad": 8})
    assert a == b


# ---------------------------------------------------------------------------
# Ids
# ---------------------------------------------------------------------------
def test_duplicate_item_ids_are_rejected_across_the_whole_tree():
    """Across branches, not just among siblings - the same registry the other
    two grammars use, which is why it is one shared helper."""
    with pytest.raises(LayoutError, match="duplicate item id"):
        compose_nested_grid([
            _group("A", [{"id": "shared"}]),
            _group("B", [_group("C", [{"id": "shared"}])]),
        ])


def test_a_duplicate_container_id_is_rejected():
    with pytest.raises(LayoutError, match="duplicate container id"):
        compose_nested_grid([
            _group("A", _items(1), id="g"),
            _group("B", _items(2), id="g"),
        ])


def test_a_container_id_may_not_collide_with_an_item_id():
    """Both are mapped back onto model elements, so one id cannot mean both."""
    with pytest.raises(LayoutError, match="already used by an item"):
        compose_nested_grid([
            _group("A", [{"id": "clash"}]),
            _group("B", _items(2), id="clash"),
        ])


def test_explicit_container_ids_are_used_verbatim():
    result = compose_nested_grid([
        _group("A", _items(1), id=4242),
        _group("B", _items(2)),
    ])
    ids = [c["id"] for c in result["containers"]]
    assert 4242 in ids
    generated = [i for i in ids if i != 4242]
    assert len(generated) == 1
    assert isinstance(generated[0], str)


def test_generated_container_ids_are_unique_across_a_deep_tree():
    result = compose_nested_grid([
        _group("A", [_group("A1", _items(1)), _group("A2", _items(2))]),
        _group("B", [_group("B1", _items(3)), _group("B2", _items(4))]),
    ])
    ids = [c["id"] for c in result["containers"]]
    assert len(ids) == len(set(ids)) == 6


# ---------------------------------------------------------------------------
# Rejections
# ---------------------------------------------------------------------------
def test_a_container_needs_a_name():
    with pytest.raises(LayoutError, match=r"nodes\[0\]\.name"):
        compose_nested_grid([{"items": _items(1)}])


def test_a_leaf_needs_an_id():
    with pytest.raises(LayoutError, match=r"nodes\[0\]\.items\[1\]\.id"):
        compose_nested_grid([_group("G", [{"id": 1}, {"name": "nameless"}])])


def test_an_empty_node_list_is_an_error_not_an_empty_canvas():
    with pytest.raises(LayoutError, match="at least one node"):
        compose_nested_grid([])


def test_grid_pad_rejects_a_negative_value():
    with pytest.raises(LayoutError, match=r"spec\.grid_pad: must not be negative"):
        compose_nested_grid([_group("G", _items(1))], spec={"grid_pad": -1})


def test_grid_pad_of_zero_is_allowed():
    """Zero padding is tight but legal - children touch the container edge, and
    touching is not overlapping in this engine."""
    result = compose_nested_grid([_group("G", _items(1))], spec={"grid_pad": 0})
    assert_nested_result_sane(result, "zero pad")


@pytest.mark.parametrize("value", [0, -3])
def test_grid_columns_rejects_a_non_positive_count(value):
    with pytest.raises(LayoutError, match=r"spec\.grid_columns: must be positive"):
        compose_nested_grid([_group("G", _items(1))],
                            spec={"grid_columns": value})


def test_max_grid_depth_rejects_zero():
    with pytest.raises(LayoutError, match=r"spec\.max_grid_depth: must be positive"):
        compose_nested_grid([_group("G", _items(1))],
                            spec={"max_grid_depth": 0})


def test_a_bad_per_container_override_names_the_container():
    with pytest.raises(LayoutError, match=r"nodes\[1\]\.item_width"):
        compose_nested_grid([
            _group("Fine", _items(1)),
            _group("Broken", _items(2), item_width=0),
        ])


def test_a_leaf_where_a_list_was_expected_is_reported_with_its_path():
    with pytest.raises(LayoutError, match=r"nodes\[0\]\.items"):
        compose_nested_grid([{"name": "G", "items": "not a list"}])


def test_a_non_mapping_node_is_reported_with_its_path():
    with pytest.raises(LayoutError, match=r"nodes\[1\]"):
        compose_nested_grid([_group("G", _items(1)), "not a dict"])


# ---------------------------------------------------------------------------
# Sweep
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("spec", [
    None,
    {"grid_pad": 0},
    {"grid_pad": 40},
    {"grid_columns": 1},
    {"grid_columns": 5},
    {"item_width": 60, "item_height": 30},
    {"item_gap_x": 0, "item_gap_y": 0},
    {"label_height": 60},
    {"origin_left": -500, "origin_top": 0},
    {"max_grid_depth": 5},
])
def test_nested_grids_survive_a_wide_sweep_of_shapes(spec):
    """Every shape the grammar is meant to take, against every sanity rule.

    `origin_top: 0` is in the sweep on purpose: a composition starting at the
    coordinate origin is the edge case where a sign error in EA's inverted y
    axis stops cancelling out and starts producing rects with negative height.
    """
    trees = [
        _sample_tree(),
        _nest(3),
        [_group("Only", [])],
        [{"id": "flat"}],
        _items(1, 2, 3, 4, 5),
        [_group("Mixed", [{"id": 1}, _group("Sub", _items(2, 3)), {"id": 4}])],
    ]
    for i, tree in enumerate(trees):
        result = compose_nested_grid(tree, spec=spec)
        assert_nested_result_sane(result, f"sweep tree {i} spec {spec}")


# ===========================================================================
# 7. Radial
# ===========================================================================
# A hub and its spokes. `containers` is always empty here, so the shared
# `assert_result_sane` does not apply - it looks every item's `container_id` up
# in the container table, and a radial item's parent is another ITEM.
def assert_radial_sane(result, label=""):
    for item in result["items"]:
        assert_valid_rect(item, f"{label} item {item['id']}")
    by_parent = {}
    for item in result["items"]:
        by_parent.setdefault(item["container_id"], []).append(item)
    for parent, siblings in by_parent.items():
        assert_no_overlaps(siblings, f"{label} ring under {parent!r}")
    assert result["containers"] == []
    assert result["bounds"] == bounding_box(result["items"])


def _spokes(n, first=1):
    return [{"id": i} for i in range(first, first + n)]


def _angle_of(result, item_id):
    return next(i["angle"] for i in result["items"] if i["id"] == item_id)


# ---------------------------------------------------------------------------
# Measuring a spoke
# ---------------------------------------------------------------------------
# Written out here rather than imported from `compose`. A test that borrowed the
# engine's own `_reach` would agree with it by construction, including on the day
# both are wrong, and the point of these is to measure the finished rectangles
# the way something downstream does. This is the same arithmetic
# `lint.check_ring_spokes` applies to a diagram EA has already drawn, so the two
# measures cannot drift apart without one of these failing.
def _center_of(r):
    return ((r["left"] + r["right"]) / 2.0, (r["top"] + r["bottom"]) / 2.0)


def _reach_along(r, ux, uy):
    """How far a rect's border sits from its center along the unit vector."""
    along_x = ((r["right"] - r["left"]) / 2.0) / abs(ux) if ux else math.inf
    along_y = ((r["top"] - r["bottom"]) / 2.0) / abs(uy) if uy else math.inf
    return min(along_x, along_y)


def _spoke_lengths(result):
    """The DRAWN length of every spoke, grouped by the box it radiates from.

    Center to center, less the stretch inside the box at the middle and the
    stretch inside the item - the two parts of the line that are hidden under a
    box and never seen. What is left is the ink a reader judges the ring by.

    A ring with no hub radiates from the reported center POINT, which reaches
    nowhere, so only the item's own stretch comes off.
    """
    by_id = {i["id"]: i for i in result["items"]}
    groups = {}
    for item in result["items"]:
        if item["ring"] == 0:
            continue
        parent = by_id.get(item["container_id"])
        px, py = (_center_of(parent) if parent is not None
                  else (result["center"]["x"], result["center"]["y"]))
        ix, iy = _center_of(item)
        dx, dy = ix - px, iy - py
        distance = math.hypot(dx, dy)
        if distance == 0:
            continue
        ux, uy = dx / distance, dy / distance
        length = distance - _reach_along(item, ux, uy)
        if parent is not None:
            length -= _reach_along(parent, ux, uy)
        groups.setdefault(item["container_id"], []).append(length)
    return groups


def _spread_if_every_center_sat_on_one_circle(result):
    """The spoke spread the PRE-FIX rule would have produced for this input.

    Placing every item's center at one distance leaves each spoke shortened by
    however far the two boxes reach along its own bearing, so the spread is the
    spread of those reaches and the common distance cancels out of it entirely.

    Used as a guard INSIDE the tests below: it proves the input is one the old
    rule actually got wrong. A ring of circles would come out equal under either
    rule and would prove nothing about the fix - and EA does not draw circles.
    """
    by_id = {i["id"]: i for i in result["items"]}
    groups = {}
    for item in result["items"]:
        if item["ring"] == 0:
            continue
        radians = math.radians(item["angle"])
        ux, uy = math.sin(radians), math.cos(radians)
        hidden = _reach_along(item, ux, uy)
        parent = by_id.get(item["container_id"])
        if parent is not None:
            hidden += _reach_along(parent, ux, uy)
        groups.setdefault(item["container_id"], []).append(hidden)
    return max((max(v) - min(v) for v in groups.values() if len(v) > 1),
               default=0.0)


# Coordinates are rounded to whole EA units once, at the end, so two spokes that
# should be identical can differ by a fraction of a unit. Measured worst case
# over the whole sweep below is 1.3. `lint.PITCH_TOLERANCE` allows 8; this file
# holds itself to a tighter number so that a real regression cannot hide inside
# the linter's allowance.
SPOKE_TOLERANCE = 2.0

# A `max_radius` far past the shipped bound, for the tests that are measuring
# something OTHER than the bound.
#
# The engine refuses a ring it would have to widen past `spec.max_radius` (900
# by default), and the crowded corner of the matrices below - sixteen boxes over
# a 60-degree fan, or twelve 400x40 boxes over any fan - is exactly what that
# bound exists to refuse. Those cases still have to be swept, because what they
# are being asked about is whether the SPOKES come out equal and whether the
# shipped linter agrees, and a bound that silently dropped the crowded end of
# the matrix would leave the spoke arithmetic untested where it is hardest.
#
# So the tests that measure spokes opt out of the bound explicitly, and the
# bound gets its own tests: `test_the_widened_radius_is_bounded` and the three
# below it. Opting out here is not a claim that a 6000-unit ring is fine; it is
# a claim that this test is not the one asking.
NO_RADIUS_BOUND = 20000


# ---------------------------------------------------------------------------
# The arrangement
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("n", [2, 3, 4, 6, 8, 12])
def test_a_full_circle_spreads_items_evenly(n):
    result = compose_radial(_spokes(n))
    angles = sorted(i["angle"] for i in result["items"])
    steps = [round(b - a, 3) for a, b in zip(angles, angles[1:])]
    assert steps and len(set(steps)) == 1, angles
    assert steps[0] == pytest.approx(360.0 / n)
    assert_radial_sane(result, f"full circle n={n}")


def test_a_full_circle_does_not_put_the_last_item_on_the_first():
    """360 / n, not 360 / (n-1): the twelfth item of twelve must not land back
    at twelve o'clock on top of the first."""
    result = compose_radial(_spokes(12))
    angles = [i["angle"] for i in result["items"]]
    assert len(set(angles)) == 12
    assert max(angles) < 360.0


def test_a_partial_sweep_spreads_inclusive_of_both_ends():
    """A half circle of three reads as one at each end and one in the middle.

    Different arithmetic from the full circle on purpose - 360/(n-1) would
    duplicate a position on a closed ring, and 180/n would leave a fan visibly
    short of its own end.
    """
    result = compose_radial(_spokes(3), spec={"sweep": 180})
    angles = sorted(i["angle"] for i in result["items"])
    assert angles == [0.0, 90.0, 180.0]


def test_start_angle_rotates_the_whole_ring():
    plain = compose_radial(_spokes(4))
    turned = compose_radial(_spokes(4), spec={"start_angle": 45})
    assert [i["angle"] for i in turned["items"]] == [
        (a + 45) % 360 for a in (i["angle"] for i in plain["items"])]


def test_a_negative_start_angle_is_a_bearing_not_an_error():
    """"Start at ten o'clock" is -60. A bearing is not a size."""
    result = compose_radial(_spokes(3), spec={"start_angle": -60})
    assert _angle_of(result, 1) == 300.0


def test_the_first_item_sits_above_the_center_by_default():
    """Angles run clockwise from twelve o'clock, which is how a reader
    describes one of these. In EA's inverted axis, above means a LARGER top."""
    result = compose_radial(_spokes(4), hub={"id": 99})
    hub = next(i for i in result["items"] if i["id"] == 99)
    first = next(i for i in result["items"] if i["id"] == 1)
    assert first["top"] > hub["top"], "the first spoke is not above the hub"
    assert abs(_center_x2(first) - _center_x2(hub)) <= 2


def test_a_single_item_sits_at_the_start_angle():
    result = compose_radial(_spokes(1))
    assert _angle_of(result, 1) == 0.0
    assert_radial_sane(result, "single")


# ---------------------------------------------------------------------------
# Equal spokes
# ---------------------------------------------------------------------------
def test_a_ring_of_flat_boxes_has_equal_spokes():
    """The failing render: a ring of 140x60 boxes around a hub.

    Centering each item on the circle is correct arithmetic and the wrong
    picture. A 140x60 box reaches 30 back toward the hub at the top of the ring
    and a full 70 at the side, and the hub reaches the same amounts outward, so
    the drawn spoke came out 160 at the top and 80 at the side - twice as long at
    twelve o'clock as at three o'clock, on a ring where every item was exactly
    on the circle.
    """
    result = compose_radial(_spokes(8), hub={"id": 99}, spec={"radius": 220})

    # The guard: under the old rule this very input spread by 80 units.
    would_have = _spread_if_every_center_sat_on_one_circle(result)
    assert would_have > 8, (
        f"input does not discriminate: the old rule spread it by {would_have}")

    lengths = _spoke_lengths(result)[99]
    assert len(lengths) == 8
    spread = max(lengths) - min(lengths)
    assert spread <= SPOKE_TOLERANCE, f"spoke lengths {sorted(lengths)}"
    # The gap is the radius that was asked for, measured as a gap rather than
    # inferred from an overlap check that exempts touching boxes.
    for length in lengths:
        assert abs(length - result["radius"]) <= SPOKE_TOLERANCE
    assert_radial_sane(result, "flat boxes")


def test_square_items_were_never_enough_on_their_own():
    """Square-ish items were the documented workaround. They do not fix it.

    A square is not a circle: its border is half a side away along an axis and
    half a diagonal away through a corner, which is 41% further. With a square
    hub AND square items the old rule still spread the spokes by 41 units on a
    ring of eight - both boxes varying together. The advice reduced the defect
    in proportion to how square the caller was willing to be and never removed
    it, which is why the engine now does the work instead.
    """
    result = compose_radial(_spokes(8), hub={"id": 99},
                            spec={"item_width": 100, "item_height": 100,
                                  "radius": 220})
    would_have = _spread_if_every_center_sat_on_one_circle(result)
    assert would_have > 40, would_have

    lengths = _spoke_lengths(result)[99]
    assert max(lengths) - min(lengths) <= SPOKE_TOLERANCE, sorted(lengths)


def test_item_centers_are_not_all_the_same_distance_out_and_should_not_be():
    """The mechanism, stated so a future edit cannot undo it by tidying.

    Equal spokes REQUIRE unequal center distances: the item at the side has to
    sit further out than the one at the top by exactly the difference in how far
    the two boxes reach along those bearings. A change that put the centers back
    on one circle would be reintroducing the defect, and this is the test that
    says so.
    """
    result = compose_radial(_spokes(8), hub={"id": 99}, spec={"radius": 220})
    cx, cy = result["center"]["x"], result["center"]["y"]
    distances = {}
    for item in result["items"]:
        if item["ring"] == 0:
            continue
        ix, iy = _center_of(item)
        distances[round(item["angle"])] = math.hypot(ix - cx, iy - cy)

    assert distances[90] > distances[0] + 50, distances
    assert distances[45] > distances[0], distances
    assert distances[90] > distances[45], distances
    # Opposite bearings are symmetric, so the ring is still a ring.
    assert abs(distances[0] - distances[180]) <= 1
    assert abs(distances[90] - distances[270]) <= 1


@pytest.mark.parametrize("item_width,item_height", [
    (100, 100),      # square
    (90, 88),        # near square
    (140, 60),       # the failing shape
    (200, 60),       # wide
    (400, 40),       # extremely wide
    (60, 140),       # tall
    (40, 400),       # extremely tall
])
@pytest.mark.parametrize("sweep", [60, 90, 120, 180, 270, 360])
def test_spokes_stay_equal_across_counts_shapes_and_arcs(
        item_width, item_height, sweep):
    """A SWEEP, not a spot-check, over all three things that trigger it.

    The defect is a content variation twice over: it needs an item that is not
    square, AND it lands differently at every bearing, so which bearings a ring
    actually uses decides how badly it shows. One ring of one shape over one arc
    - which is what the suite had - can miss it completely. Counts vary the
    bearings, aspect ratios vary the reach, and the partial arcs matter most of
    all: a 60-degree fan never points along an axis, where the reach is at its
    smallest, so a fix tuned to a closed ring can be wrong on every fan.
    """
    spec = {"item_width": item_width, "item_height": item_height,
            "sweep": sweep, "radius": 220,
            # See `NO_RADIUS_BOUND`: this test measures spokes, not ring size.
            "max_radius": NO_RADIUS_BOUND}
    for n in (2, 3, 4, 5, 6, 7, 8, 9, 12, 16):
        for hub in ({"id": "hub"}, None):
            result = compose_radial(_spokes(n), spec=spec, hub=hub)
            label = (f"{item_width}x{item_height} sweep={sweep} n={n} "
                     f"hub={hub is not None}")
            assert_radial_sane(result, label)
            for parent, lengths in _spoke_lengths(result).items():
                if len(lengths) < 2:
                    continue
                spread = max(lengths) - min(lengths)
                assert spread <= SPOKE_TOLERANCE, (
                    f"{label} under {parent!r}: spread {spread:.2f}, "
                    f"lengths {[round(v, 1) for v in sorted(lengths)]}")
                for length in lengths:
                    assert abs(length - result["radius"]) <= SPOKE_TOLERANCE, (
                        f"{label}: spoke {length:.1f} against reported radius "
                        f"{result['radius']}")


@pytest.mark.parametrize("item_width,item_height", [
    (140, 60), (60, 140), (100, 100), (300, 50),
])
def test_the_sweep_would_have_caught_the_old_rule_at_every_shape(
        item_width, item_height):
    """The sweep's own guard, hoisted out so it is visible.

    Each shape above has to be one the old rule got wrong, or the sweep is a
    row of tests that would have passed before the fix. A square is included
    precisely because it is the shape the old guidance called safe.
    """
    for n in (3, 5, 8, 12):
        result = compose_radial(
            _spokes(n), hub={"id": "hub"},
            spec={"item_width": item_width, "item_height": item_height})
        would_have = _spread_if_every_center_sat_on_one_circle(result)
        assert would_have > SPOKE_TOLERANCE, (
            f"{item_width}x{item_height} n={n}: the old rule spread this input "
            f"by only {would_have:.2f}, so it proves nothing")


def _verified_like(result):
    """A `verify_diagram`-shaped payload built from composed rects.

    Hand-built, and hermetic: the linter reads rectangles and does not care
    whether EA or this module produced them. `element_id` has to survive `int()`,
    which one of the linter's other rules requires.
    """
    objects = [{"element_id": item["id"], "name": f"E{item['id']}",
                "left": item["left"], "top": item["top"],
                "right": item["right"], "bottom": item["bottom"]}
               for item in result["items"]]
    b = result["bounds"]
    return {
        "objects": objects,
        "links": [],
        "canvas": {"left": b["left"] - 50, "top": b["top"] + 50,
                   "right": b["right"] + 50, "bottom": b["bottom"] - 50},
    }


@pytest.mark.parametrize("item_width,item_height", [
    (140, 60), (60, 140), (100, 100), (200, 60), (400, 40), (90, 88),
])
@pytest.mark.parametrize("sweep", [60, 90, 180, 360])
def test_the_shipped_linter_agrees_the_spokes_are_even(
        item_width, item_height, sweep):
    """THE SEAM. Two measures of the same property, pinned against each other.

    `lint.check_ring_spokes` measures a spoke along the spoke line - center to
    center, less each box's reach along that bearing - and warns when the spread
    exceeds `lint.PITCH_TOLERANCE`. This engine places the items. If the engine
    equalized any OTHER distance - the gap to the item's nearest corner, say, or
    the distance to the center point rather than to the hub's border - the two
    would disagree on the diagonals and the linter would fire on output this
    engine considers correct. Both measures are written out independently, in
    their own module, so the only thing keeping them together is this test.

    This is checked here rather than in the linter's own suite because it is the
    engine's output that has to satisfy it, and the engine is what gets edited.
    """
    lint = pytest.importorskip("lint")
    for n in (2, 3, 5, 8, 12):
        result = compose_radial(
            _spokes(n), hub={"id": 999, "name": "Hub"},
            spec={"item_width": item_width, "item_height": item_height,
                  "sweep": sweep, "radius": 220,
                  # See `NO_RADIUS_BOUND`: this seam is about spoke equality.
                  "max_radius": NO_RADIUS_BOUND})
        payload = _verified_like(result)
        by_id = {o["element_id"]: o for o in payload["objects"]}
        ring = [by_id[i["id"]] for i in result["items"] if i["ring"] == 1]
        report = lint.lint_diagram(payload, rings=[(by_id[999], ring)])

        label = f"{item_width}x{item_height} sweep={sweep} n={n}"
        fired = [f for f in report.findings if f.rule == "uneven-spokes"]
        assert not fired, f"{label}: {[f.message for f in fired]}"
        if n > 1:
            spread = report.metrics["worst_spoke_spread"]
            assert spread <= SPOKE_TOLERANCE, f"{label}: lint saw {spread}"


def test_an_outer_ring_measures_its_spokes_from_the_item_it_hangs_off():
    """A radial tree's second ring radiates from a BOX, not from a point.

    So the same correction applies twice: the branch items have to clear their
    parent item's border by the same amount all the way round the arc they
    occupy, and the parent's border is as unequal as the hub's was.
    """
    result = compose_radial(
        [{"id": 1, "items": _spokes(4, first=10)},
         {"id": 2, "items": _spokes(4, first=20)},
         {"id": 3}],
        hub={"id": 99}, spec={"item_width": 140, "item_height": 60},
    )
    groups = _spoke_lengths(result)
    assert set(groups) == {99, 1, 2}, sorted(groups)
    for parent in (1, 2):
        lengths = groups[parent]
        assert len(lengths) == 4
        spread = max(lengths) - min(lengths)
        assert spread <= SPOKE_TOLERANCE, (
            f"branch off {parent}: {[round(v, 1) for v in lengths]}")
    assert_radial_sane(result, "radial tree")


# ---------------------------------------------------------------------------
# The radius is a floor
# ---------------------------------------------------------------------------
def test_a_radius_too_small_for_its_ring_is_widened():
    """A grammar that drew an overlapping ring because the caller passed a
    small number would be obeying the spec and producing a bad diagram."""
    result = compose_radial(_spokes(12), spec={"radius": 10})
    assert result["radius"] > 10
    assert_radial_sane(result, "widened")


def test_a_generous_radius_is_left_alone():
    result = compose_radial(_spokes(4), spec={"radius": 900})
    assert result["radius"] == 900


def test_the_radius_actually_used_is_reported():
    """So a caller can tell it was overridden rather than discovering it from
    the coordinates."""
    result = compose_radial(_spokes(16), spec={"radius": 20})
    assert result["radius"] == result["radius"]
    assert result["radius"] > 20


@pytest.mark.parametrize("n", [3, 5, 9, 16, 24])
def test_a_ring_never_overlaps_itself_at_any_size(n):
    result = compose_radial(_spokes(n), spec={"radius": 1})
    assert_radial_sane(result, f"crowded n={n}")


@pytest.mark.parametrize("n", [3, 4, 5, 6, 7, 8, 9, 12, 16])
@pytest.mark.parametrize("sweep", [60, 90, 120, 180, 360])
def test_widening_clears_a_nearly_square_item_too(n, sweep):
    """A THIRD defect, found by the aspect-ratio sweep rather than by a render.

    The widening asked for the centers to clear `max(width, height)` plus a gap.
    Two axis-aligned boxes that are apart on the diagonal can satisfy that and
    still overlap - they need a full width apart horizontally or a full height
    vertically, and the distance that guarantees one of those is the DIAGONAL.
    The error is invisible for a flat item, whose diagonal is barely longer than
    its width, and severe for a nearly square one, whose diagonal is 41% longer
    than either side.

    A ring of 90x88 items over a 60-degree fan overlapped at every count from 3
    up, and the promise that the radius gets widened until they do not made it
    worse rather than better: the radius grew past 1500 while the neighbors
    still touched, because each step was measured against a distance that could
    never be enough. Nothing in the suite had a nearly square item, so nothing
    saw it.
    """
    result = compose_radial(
        _spokes(n), spec={"item_width": 90, "item_height": 88,
                          "sweep": sweep, "radius": 220,
                          # See `NO_RADIUS_BOUND`. This guard has to keep
                          # covering the crowded end of the fan, because that is
                          # where the old `max(w, h)` rule failed worst; whether
                          # the ring that results is a SANE SIZE is asserted
                          # separately, in `test_the_widened_radius_is_bounded`.
                          "max_radius": NO_RADIUS_BOUND})
    assert_radial_sane(result, f"90x88 sweep={sweep} n={n}")
    # And the whitespace is there, measured as a gap. `assert_radial_sane` uses
    # `rects_overlap`, which exempts boxes that merely touch, so on its own it
    # would accept a ring whose items were flush against each other.
    ring = sorted((i for i in result["items"]), key=lambda i: i["angle"])
    for a, b in zip(ring, ring[1:]):
        apart = max(b["left"] - a["right"], a["left"] - b["right"],
                    a["bottom"] - b["top"], b["bottom"] - a["top"])
        assert apart > 0, (
            f"{a['id']} and {b['id']} touch: {_span(a)} {_span(b)}")


# ---------------------------------------------------------------------------
# The widening is bounded
# ---------------------------------------------------------------------------
# THE OTHER HALF OF THE SAME DEFECT, and the half that stayed broken after the
# clearance was fixed.
#
# `hypot(w, h)` made the widening correct about overlap. It did nothing about
# SIZE, and because `hypot >= max` it could only ever widen further than the
# rule it replaced. Measured at 90x88 over a 60-degree fan, with the clearance
# fix in place and nothing bounding the result: 238 units at three items, 932 at
# eight, 2046 at sixteen, 3161 at twenty-four. The item that recorded the
# clearance defect called 1576 a runaway; the fixed engine went twice past it,
# and no test said anything, because every test asked only whether the ring
# overlapped.
#
# The bound is `spec.max_radius`, and going past it is a REFUSAL rather than a
# clamp: a clamp would draw the overlap the widening exists to prevent and say
# nothing. See `compose._plan_ring` for why a refusal rather than a second ring.
_NEAR_SQUARE_FAN = {"item_width": 90, "item_height": 88, "sweep": 60}


@pytest.mark.parametrize("n,radius", [(3, 238), (4, 377), (5, 515), (6, 654)])
def test_a_ring_the_sweep_can_hold_keeps_the_radius_it_had(n, radius):
    """The bound refuses; it does not tighten.

    These four are the counts a 60-degree fan of 90x88 boxes can actually hold,
    and the numbers are the ones the unbounded engine produced for them. A bound
    that changed any of these would have moved geometry that was already right.
    """
    result = compose_radial(_spokes(n), spec=dict(_NEAR_SQUARE_FAN))
    assert result["radius"] == radius
    assert result["radius"] <= DEFAULT_SPEC["max_radius"]
    assert_radial_sane(result, f"90x88 sweep=60 n={n}")


@pytest.mark.parametrize("n,needed", [(8, 932), (16, 2046), (24, 3161)])
def test_a_ring_the_sweep_cannot_hold_is_refused_not_widened(n, needed):
    """The runaway counts, and the refusal has to be usable.

    `needed` is what the unbounded engine returned for that count. The message
    is asserted rather than only the exception type, because the whole argument
    for refusing over clamping is that the caller is told which input to give
    up - so it has to name the count, the box, the arc, the radius that would
    have been needed, the bound, and a way out.
    """
    with pytest.raises(LayoutError) as caught:
        compose_radial(_spokes(n), spec=dict(_NEAR_SQUARE_FAN))
    message = str(caught.value)
    for fragment in (f"{n} items", "90x88", "60-degree", str(needed),
                     "spec.max_radius", str(DEFAULT_SPEC["max_radius"]),
                     "wider sweep", "smaller items"):
        assert fragment in message, (fragment, message)


@pytest.mark.parametrize("sweep", [60, 90, 120, 180, 270, 360])
def test_every_radius_this_engine_returns_is_inside_the_bound(sweep):
    """The claim, swept: no input produces a ring past `max_radius`.

    Twelve counts against six arcs, 72 compositions, counted before they are
    run as `APT-2026-0168` asks. Each one either composes inside the bound or is
    refused for the bound by name - a refusal for any OTHER reason fails the
    test, and so does an arc on which nothing composes at all, which would make
    the row vacuous.
    """
    counts = (2, 3, 4, 5, 6, 7, 8, 9, 12, 16, 20, 24)
    assert len(counts) == 12
    composed = refused = 0
    for n in counts:
        spec = {"item_width": 90, "item_height": 88, "sweep": sweep}
        try:
            result = compose_radial(_spokes(n), spec=spec)
        except LayoutError as exc:
            assert "spec.max_radius" in str(exc), str(exc)
            refused += 1
            continue
        composed += 1
        assert result["radius"] <= DEFAULT_SPEC["max_radius"], (n, result)
        assert_radial_sane(result, f"90x88 sweep={sweep} n={n}")
    assert composed + refused == len(counts)
    assert composed >= 4, (sweep, composed, refused)


def test_an_inner_rings_widening_is_bounded_too():
    """THE WORSE HALF, and the one nothing could see.

    An inner ring gets `min(step, 120)` degrees, and `step` is itself the sweep
    divided by the outer count - so an inner ring on a crowded fan is planned
    over a few degrees and demands far more radius than the ring it hangs off.
    Twelve spokes of three branches over a 180-degree sweep: ring one settles at
    576, every inner ring demanded 1178. The result dict reports ring one's
    radius and not the inner ones, so that figure was invisible to the caller as
    well as to the suite.

    The refusal has to name the RING, not only the composition, or the caller
    cannot tell which of the two is the problem.
    """
    nodes = [{"id": i, "items": _spokes(3, first=100 + 10 * i)}
             for i in range(1, 13)]
    with pytest.raises(LayoutError) as caught:
        compose_radial(nodes, hub={"id": 99}, spec={"sweep": 180})
    message = str(caught.value)
    assert "nodes[0].items" in message, message
    assert "1178" in message, message
    # And the same tree over a full circle stays inside the bound, so it is the
    # crowding that is refused and not the second ring itself.
    result = compose_radial(nodes, hub={"id": 99}, spec={"sweep": 360})
    assert result["radius"] <= DEFAULT_SPEC["max_radius"]
    assert_radial_sane(result, "12 spokes of 3 over a full circle")


def test_raising_max_radius_lets_a_wide_ring_through_deliberately():
    """The bound is a bound, not a new collision rule.

    A caller who raises it gets exactly the ring the unbounded engine produced -
    3161 units of radius for twenty-four 90x88 boxes over a 60-degree fan - and
    it is still overlap-free. The refusal is about whether that is a diagram
    worth drawing, which is the caller's call to make explicitly.
    """
    result = compose_radial(
        _spokes(24), spec={**_NEAR_SQUARE_FAN, "max_radius": 4000})
    assert result["radius"] == 3161
    assert_radial_sane(result, "24 of 90x88 over a 60-degree fan")


def test_a_radius_the_caller_states_raises_the_ceiling_with_it():
    """A radius the caller states is theirs; the bound is on what the ENGINE adds.

    So the ceiling is the larger of `spec.radius` and `spec.max_radius`, which
    leaves the radius determined by the inputs either way. Twelve 90x88 boxes
    over a 60-degree fan need 1489: stated as a floor of 1600 that is a ring the
    caller asked for, and at 1200 it is still the engine overruling them.
    """
    generous = compose_radial(
        _spokes(12), spec={**_NEAR_SQUARE_FAN, "radius": 1600})
    assert generous["radius"] == 1600
    assert_radial_sane(generous, "caller-stated 1600")
    with pytest.raises(LayoutError, match="refuses a ring past 1200"):
        compose_radial(_spokes(12), spec={**_NEAR_SQUARE_FAN, "radius": 1200})


# ---------------------------------------------------------------------------
# Per-node sizing: refused, not ignored
# ---------------------------------------------------------------------------
# A dead helper and a dead allow-list made `item_width`, `item_height` and
# `radius` look settable per node. They were not: nothing called the helper, and
# a node carrying one of those keys composed successfully, raised nothing, and
# produced output BYTE-IDENTICAL to the same tree without it. They are deleted,
# and stating one of those keys on a node is now an error.
#
# A test that only checked "the call does not raise" would have passed against
# the ignored version too, which is why these assert the refusal and its text.
@pytest.mark.parametrize("key,value", [
    ("item_width", 200), ("item_height", 200), ("radius", 400),
])
def test_a_sizing_key_on_a_ring_owner_is_refused(key, value):
    """All three of the old allow-list, on the node that owns an inner ring."""
    plain = [{"id": 1, "items": _spokes(3, first=10)}, {"id": 2}]
    assert compose_radial(plain, hub={"id": 99})["items"], "baseline must compose"
    with pytest.raises(LayoutError, match=rf"nodes\[0\]\.{key}"):
        compose_radial([{"id": 1, key: value, "items": _spokes(3, first=10)},
                        {"id": 2}], hub={"id": 99})


@pytest.mark.parametrize("key", ["item_width", "item_height", "radius"])
def test_a_sizing_key_on_a_leaf_node_is_refused(key):
    """A leaf owns no ring, so even a wired-up override would have ignored it.

    This is the case that would still have been silent under the other choice,
    and it is the likelier mistake: a caller sizes the box they can see.
    """
    with pytest.raises(LayoutError, match=rf"nodes\[1\]\.{key}"):
        compose_radial([{"id": 1}, {"id": 2, key: 200}, {"id": 3}])


def test_a_sizing_key_on_the_hub_is_refused():
    """The box at the middle is sized by the spec like every other box."""
    with pytest.raises(LayoutError, match=r"hub\.item_width"):
        compose_radial(_spokes(3), hub={"id": 99, "item_width": 200})


def test_the_refusal_says_where_the_capability_actually_lives():
    """A refusal that does not say what to do instead is only half a refusal.

    Per-node sizing is not missing from the engine: `compose_radial_tree`
    resolves the same three keys per node and allocates angular room by weight,
    which is what makes them worth having. The message has to point there.
    """
    with pytest.raises(LayoutError) as caught:
        compose_radial([{"id": 1, "item_width": 200}])
    message = str(caught.value)
    assert "compose_radial_tree" in message, message
    assert "item_width, item_height and radius" in message, message


def test_the_dead_radial_override_helpers_are_referenced_nowhere():
    """Deleted code that something still names is not deleted.

    Checked across the tools directory and the reference docs, not only against
    the module, because the helper was documented as a capability in prose as
    well as being defined in code.
    """
    import compose as compose_module

    names = ("_ring" + "_metrics", "_RADIAL" + "_OVERRIDES")
    for name in names:
        assert not hasattr(compose_module, name), name
    stale = []
    for root in (_HERE, _HERE.parent / "references"):
        for path in sorted(root.glob("*.py")) + sorted(root.glob("*.md")):
            if path.name == Path(__file__).name:
                continue
            text = path.read_text(encoding="utf-8")
            stale += [f"{path.name}: {n}" for n in names if n in text]
    assert not stale, stale


# ---------------------------------------------------------------------------
# The hub
# ---------------------------------------------------------------------------
def test_the_hub_is_an_item_not_a_container():
    """It is one of the things on the diagram, not something enclosing them."""
    result = compose_radial(_spokes(3), hub={"id": 99, "name": "Customer"})
    hub = next(i for i in result["items"] if i["id"] == 99)
    assert hub["ring"] == 0
    assert hub["container_id"] is None
    assert hub["name"] == "Customer"
    assert result["containers"] == []


def test_the_hub_is_optional():
    result = compose_radial(_spokes(3))
    assert all(i["ring"] == 1 for i in result["items"])


def test_the_hub_shares_the_ring_id_space():
    with pytest.raises(LayoutError, match="duplicate item id"):
        compose_radial(_spokes(3), hub={"id": 1})


def test_spokes_point_at_the_hub_as_their_parent():
    result = compose_radial(_spokes(3), hub={"id": 99})
    for item in result["items"]:
        if item["ring"] == 1:
            assert item["container_id"] == 99


# ---------------------------------------------------------------------------
# Outer rings
# ---------------------------------------------------------------------------
def test_a_node_with_items_gets_its_own_outer_ring():
    result = compose_radial([
        {"id": 1, "items": [{"id": 10}, {"id": 11}]},
        {"id": 2},
        {"id": 3},
    ], hub={"id": 99})
    outer = [i for i in result["items"] if i["ring"] == 2]
    assert {i["id"] for i in outer} == {10, 11}
    assert all(i["container_id"] == 1 for i in outer)
    assert_radial_sane(result, "two rings")


def test_a_branch_does_not_sweep_back_across_the_center():
    """Without a cap on the branch arc, a two-item ring gives each branch 180
    degrees and its children swing round past the hub."""
    result = compose_radial([
        {"id": 1, "items": _spokes(3, first=10)},
        {"id": 2, "items": _spokes(3, first=20)},
    ], hub={"id": 99})
    hub = next(i for i in result["items"] if i["id"] == 99)
    for item in result["items"]:
        if item["ring"] != 2:
            continue
        # No outer item may sit inside the hub's own box.
        assert not rects_overlap(item, hub), item["id"]
    assert_radial_sane(result, "branches")


def test_nesting_past_the_bound_is_refused():
    deep = [{"id": 1, "items": [{"id": 2, "items": [{"id": 3}]}]}]
    with pytest.raises(LayoutError, match="rings deep"):
        compose_radial(deep)
    result = compose_radial(deep, spec={"max_ring_depth": 3})
    assert max(i["ring"] for i in result["items"]) == 3


# ---------------------------------------------------------------------------
# Sizing and determinism
# ---------------------------------------------------------------------------
def test_every_item_in_a_ring_is_the_same_size():
    result = compose_radial(_spokes(7))
    sizes = {(rect_width(i), rect_height(i)) for i in result["items"]}
    assert len(sizes) == 1


def test_radial_is_deterministic():
    """Trigonometry means floats, and the rects must still come out identical
    on every machine. Rounding is applied once, to the coordinate."""
    first = compose_radial(_spokes(9), hub={"id": 99})
    second = compose_radial(_spokes(9), hub={"id": 99})
    assert first == second


def test_every_coordinate_is_a_whole_unit():
    result = compose_radial(_spokes(7), spec={"radius": 137})
    for item in result["items"]:
        for key in ("left", "top", "right", "bottom"):
            assert isinstance(item[key], int), (item["id"], key)


def test_the_arrangement_is_reported_not_only_drawn():
    """`angle` and `ring` on every item, so a caller can reason about the
    arrangement without recovering it from coordinates."""
    result = compose_radial(_spokes(4), hub={"id": 99})
    for item in result["items"]:
        assert isinstance(item["angle"], float)
        assert isinstance(item["ring"], int)


# ---------------------------------------------------------------------------
# Rejections
# ---------------------------------------------------------------------------
def test_an_empty_ring_is_an_error():
    with pytest.raises(LayoutError, match="at least one node"):
        compose_radial([])


def test_an_empty_inner_ring_is_an_error():
    with pytest.raises(LayoutError, match="at least one node"):
        compose_radial([{"id": 1, "items": []}])


def test_a_spoke_needs_an_id():
    with pytest.raises(LayoutError, match=r"nodes\[1\]\.id"):
        compose_radial([{"id": 1}, {"name": "nameless"}])


@pytest.mark.parametrize(
    "key", ["radius", "max_radius", "sweep", "max_ring_depth"])
def test_a_non_positive_radial_key_is_rejected(key):
    with pytest.raises(LayoutError, match=rf"spec\.{key}: must be positive"):
        compose_radial(_spokes(3), spec={key: 0})


def test_start_angle_accepts_zero_and_negatives():
    for value in (0, -90, 359):
        assert compose_radial(_spokes(3), spec={"start_angle": value})


def test_a_hub_without_an_id_is_rejected():
    with pytest.raises(LayoutError, match=r"hub\.id"):
        compose_radial(_spokes(3), hub={"name": "no id"})


# ---------------------------------------------------------------------------
# Sweep
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("sweep", [90, 120, 180, 270, 360])
def test_rings_survive_a_sweep_sweep(sweep):
    result = compose_radial(_spokes(5), spec={"sweep": sweep})
    assert_radial_sane(result, f"sweep {sweep}")
    assert max(i["angle"] for i in result["items"]) <= 360.0

# ---------------------------------------------------------------------------
# Grammar: two_column_cycle
# ---------------------------------------------------------------------------
# WHY THIS SECTION IS A MATRIX AND NOT A WORKED EXAMPLE
#
# Every visible layout defect this engine has shipped was a CONTENT-VARIATION
# sensitivity that one hand-picked case passed: a ragged band edge that needed
# unequal sibling counts, a name collision that needed long names, unequal radial
# spokes that needed non-square boxes, and a ring clearance derived from
# `max(w, h)` where the condition is `hypot(w, h)`, which overlapped at every
# count of three or more. So the properties below are swept over item counts,
# height profiles, box widths and gaps rather than demonstrated once.
#
# The height profiles are the axis that matters here, because variable heights
# are what this grammar is for. `odd-parity` exists for the integer rounding:
# seating a box in its slot divides an odd difference, and a profile whose
# differences were all even would never exercise it.
_CYCLE_BASE = 60

_CYCLE_HEIGHT_PROFILES = {
    "uniform": lambda n, base: [base] * n,
    "one-tall": lambda n, base: [base * 4 if i == n // 2 else base
                                 for i in range(n)],
    "graded": lambda n, base: [base + 30 * i for i in range(n)],
    "alternating": lambda n, base: [base if i % 2 else base * 3
                                    for i in range(n)],
    "all-short": lambda n, base: [max(1, base // 3)] * n,
    "extreme": lambda n, base: [1 if i % 3 else 400 for i in range(n)],
    "odd-parity": lambda n, base: [base + i for i in range(n)],
}

_CYCLE_COUNTS = tuple(range(1, 14))          # odd and even, 1 through 13
_CYCLE_WIDTHS = (140, 60, 400, 20)
_CYCLE_GAPS = (20, 40, 5)

#: Integer coordinates cannot center an odd difference exactly, so a center may
#: sit half a unit off and two of them a whole unit apart. Everything this file
#: asserts about centers allows exactly that and no more - `lint.PITCH_TOLERANCE`
#: allows 8, so the engine is well inside the linter's own allowance.
CYCLE_CENTER_ROUNDING = 1


def _cycle_items(heights, first=1):
    """Items for the cycle, one per height. A None height is left unstated."""
    out = []
    for k, h in enumerate(heights):
        item = {"id": first + k, "name": f"State {first + k}"}
        if h is not None:
            item["item_height"] = h
        out.append(item)
    return out


def _cycle_case(n, profile, base=_CYCLE_BASE):
    return _cycle_items(_CYCLE_HEIGHT_PROFILES[profile](n, base))


def _cycle_columns(result):
    """`{column: [items, top row first]}`, read off the composition's own keys."""
    columns = {}
    for item in result["items"]:
        columns.setdefault(item["column"], []).append(item)
    for members in columns.values():
        members.sort(key=lambda i: i["row"])
    return columns


def assert_cycle_sane(result, label=""):
    """What must hold for any two-column cycle, whatever the content.

    Deliberately not `assert_result_sane`: that helper looks every item's
    container up by id, and this grammar has no containers at all - a cycle is a
    ring of peers. The checks it shares are restated here against items alone.
    """
    assert result["grammar"] == "two_column_cycle", label
    assert result["containers"] == [], f"{label}: a cycle has no containers"

    items = result["items"]
    for it in items:
        assert_valid_rect(it, f"{label} item {it['id']}")
        assert it["container_id"] is None, f"{label}: {it['id']} claims an owner"
        for edge in ("left", "top", "right", "bottom"):
            assert isinstance(it[edge], int), f"{label}: {edge} is not an int"
        # EA's convention: the visual top of a diagram is the coordinate
        # nearest zero, and this grammar starts at a negative origin.
        assert it["top"] <= 0, f"{label}: {it['id']} has a positive top"
    assert_no_overlaps(items, f"{label} items")

    assert result["bounds"] == bounding_box(items), f"{label}: bounds disagree"

    # One width for the whole cycle: the guarantee, restated as an assertion.
    widths = {rect_width(i) for i in items}
    assert widths == {result["item_width"]}, f"{label}: widths {sorted(widths)}"

    assert result["columns"] == (1 if len(items) == 1 else 2), label
    assert result["rows"] == max(i["row"] for i in items) + 1, label


# ---------------------------------------------------------------------------
# The arrangement: down one column, back up the other
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("n", _CYCLE_COUNTS)
def test_the_flow_runs_down_the_first_column_and_up_the_second(n):
    result = compose_two_column_cycle(_cycle_case(n, "graded"))
    assert_cycle_sane(result, f"n={n}")

    descent = [i for i in result["items"] if i["leg"] == "descent"]
    ret = [i for i in result["items"] if i["leg"] == "return"]
    assert len(descent) == -(-n // 2), f"n={n}: descent {len(descent)}"
    assert len(ret) == n - len(descent)

    # The descent is the first items, in order, reading DOWN: successive rows.
    assert [i["index"] for i in descent] == list(range(len(descent)))
    assert [i["row"] for i in descent] == list(range(len(descent)))
    assert {i["column"] for i in descent} == {0}

    # The return is the rest, reading UP: successive rows, decreasing.
    if ret:
        assert [i["index"] for i in ret] == list(range(len(descent), n))
        assert [i["row"] for i in ret] == list(
            range(result["rows"] - 1, result["rows"] - 1 - len(ret), -1))
        assert {i["column"] for i in ret} == {1}


@pytest.mark.parametrize("n", _CYCLE_COUNTS)
def test_the_fold_at_the_bottom_is_a_horizontal_hop_at_every_count(n):
    """The step from the bottom of one column across to the other.

    `_cycle_split` spends the odd count's diagonal on the CLOSING step instead,
    so this one is horizontal whatever the count - which is the half of that
    decision a reader sees. Swept over every count because the split is where an
    off-by-one would live, and an even-only check would never see it.
    """
    result = compose_two_column_cycle(_cycle_case(n, "alternating"))
    bottom_row = result["rows"] - 1
    on_the_bottom = [i for i in result["items"] if i["row"] == bottom_row]
    if n == 1:
        assert len(on_the_bottom) == 1
        return
    assert len(on_the_bottom) == 2, f"n={n}: the fold has no second box"
    a, b = sorted(on_the_bottom, key=lambda i: i["column"])
    assert a["index"] + 1 == b["index"], f"n={n}: the fold is not consecutive"
    assert abs(_center_y2(a) - _center_y2(b)) <= 2 * CYCLE_CENTER_ROUNDING, (
        f"n={n}: the fold is not horizontal")


@pytest.mark.parametrize("n", _CYCLE_COUNTS)
def test_where_the_loop_closes_and_where_the_empty_cell_falls(n):
    """An even cycle closes across the top; an odd one closes on the diagonal.

    Pinned in both directions rather than only for the tidy case, because the
    odd case is the one a reader will ask about and the answer has to be a
    decision rather than an accident. See `_cycle_split`.
    """
    result = compose_two_column_cycle(_cycle_case(n, "one-tall"))
    last = max(result["items"], key=lambda i: i["index"])
    first = min(result["items"], key=lambda i: i["index"])
    assert first["row"] == 0 and first["column"] == 0

    occupied = {(i["column"], i["row"]) for i in result["items"]}
    if n == 1:
        assert last is first
    elif n % 2 == 0:
        assert (last["column"], last["row"]) == (1, 0), n
        assert len(occupied) == 2 * result["rows"], n
    else:
        # The return column is bottom-anchored, so the cell left empty is the
        # TOP of it and the closing step is the diagonal one.
        assert (1, 0) not in occupied, n
        assert last["row"] == min(i["row"] for i in result["items"]
                                  if i["column"] == 1), n


def test_a_cycle_of_one_or_two_composes_rather_than_raising():
    """Degenerate but real: a self-loop, and a pair that swaps back and forth.

    Neither is worth an error - the result says which happened - and refusing
    them would make a caller special-case a count it cannot always control.
    """
    one = compose_two_column_cycle(_cycle_items([None]))
    assert one["columns"] == 1 and one["rows"] == 1
    assert_cycle_sane(one, "n=1")

    two = compose_two_column_cycle(_cycle_items([None, 200]))
    assert two["columns"] == 2 and two["rows"] == 1
    assert [i["column"] for i in two["items"]] == [0, 1]
    assert_cycle_sane(two, "n=2")


def test_names_are_passed_through_and_an_unnamed_item_carries_no_name_key():
    result = compose_two_column_cycle(
        [{"id": 1, "name": "Idle"}, {"id": 2}])
    by_id = {i["id"]: i for i in result["items"]}
    assert by_id[1]["name"] == "Idle"
    assert "name" not in by_id[2]


@pytest.mark.parametrize("profile", sorted(_CYCLE_HEIGHT_PROFILES))
def test_the_same_input_composes_identically_twice(profile):
    items = _cycle_case(7, profile)
    assert (compose_two_column_cycle(items)
            == compose_two_column_cycle(items))


# ---------------------------------------------------------------------------
# What variable heights are allowed to change, and what they are not
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("profile", sorted(_CYCLE_HEIGHT_PROFILES))
@pytest.mark.parametrize("n", _CYCLE_COUNTS)
def test_every_item_keeps_the_shared_width_however_the_heights_vary(n, profile):
    """The grammar's first guarantee, swept over the whole matrix.

    A per-item height is content; a per-item width would be variation a reader
    has to decode for nothing, and it would cost the cycle its straight outline.
    So the widths must be ONE number no matter what the heights do.
    """
    for width in _CYCLE_WIDTHS:
        result = compose_two_column_cycle(
            _cycle_case(n, profile), {"item_width": width})
        assert_cycle_sane(result, f"n={n} {profile} w={width}")
        assert {rect_width(i) for i in result["items"]} == {width}
        lefts = {i["column"]: {i2["left"] for i2 in result["items"]
                               if i2["column"] == i["column"]}
                 for i in result["items"]}
        for column, edges in lefts.items():
            assert len(edges) == 1, (
                f"n={n} {profile} w={width}: column {column} has a ragged left "
                f"edge at {sorted(edges)}")


@pytest.mark.parametrize("profile", sorted(_CYCLE_HEIGHT_PROFILES))
@pytest.mark.parametrize("n", _CYCLE_COUNTS)
def test_the_heights_are_the_callers_own(n, profile):
    heights = _CYCLE_HEIGHT_PROFILES[profile](n, _CYCLE_BASE)
    result = compose_two_column_cycle(_cycle_items(heights))
    by_index = {i["index"]: i for i in result["items"]}
    for k, wanted in enumerate(heights):
        assert rect_height(by_index[k]) == wanted, (n, profile, k)


@pytest.mark.parametrize("profile", sorted(_CYCLE_HEIGHT_PROFILES))
@pytest.mark.parametrize("n", _CYCLE_COUNTS)
def test_the_centers_are_evenly_pitched_down_each_column(n, profile):
    """The second guarantee: one pitch for the whole composition.

    Measured on CENTERS because that is what the shipped linter measures for a
    group of unequal boxes, and because it is the quantity a reader perceives as
    rhythm. Allowed to differ by one unit, which is integer rounding and nothing
    else - see `CYCLE_CENTER_ROUNDING`.
    """
    for gap in _CYCLE_GAPS:
        result = compose_two_column_cycle(
            _cycle_case(n, profile), {"item_gap_y": gap})
        pitch = result["row_pitch"]
        for column, members in _cycle_columns(result).items():
            steps = [(_center_y2(a) - _center_y2(b)) / 2.0
                     for a, b in zip(members, members[1:])]
            for step in steps:
                assert abs(step - pitch) <= CYCLE_CENTER_ROUNDING, (
                    f"n={n} {profile} gap={gap} column {column}: step {step} "
                    f"against pitch {pitch}")


@pytest.mark.parametrize("profile", sorted(_CYCLE_HEIGHT_PROFILES))
@pytest.mark.parametrize("n", _CYCLE_COUNTS)
def test_the_two_columns_share_a_center_line_row_by_row(n, profile):
    """The third guarantee. It is what makes the fold and the close horizontal.

    Aligned CENTERS, not aligned tops: with tops aligned this assertion would
    fail by half the difference between the two boxes' heights, which on this
    grammar's content is tens of units.
    """
    result = compose_two_column_cycle(_cycle_case(n, profile))
    by_row = {}
    for item in result["items"]:
        by_row.setdefault(item["row"], []).append(item)
    for row, members in by_row.items():
        if len(members) < 2:
            continue
        centers = [_center_y2(m) for m in members]
        assert max(centers) - min(centers) <= 2 * CYCLE_CENTER_ROUNDING, (
            f"n={n} {profile} row {row}: centers {centers}")


# ---------------------------------------------------------------------------
# The clearance condition, tested as the inequality it was derived as
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("profile", sorted(_CYCLE_HEIGHT_PROFILES))
@pytest.mark.parametrize("n", _CYCLE_COUNTS)
def test_the_vertical_clearance_is_never_less_than_the_gap(n, profile):
    """The derivation, checked as arithmetic rather than eyeballed on one case.

    Seating a box centered in a slot of the pitch less the gap gives a clearance
    of `g + ceil(a / 2) + floor(b / 2)` between adjacent rows, where `a` and `b`
    are how far short of the slot the two boxes fall. Both terms are
    non-negative, so the clearance is never less than `g` - and the exact figure
    is asserted too, not just the floor, because a bound that happens to hold
    for the wrong reason is how the radial clearance shipped with `max(w, h)`
    where the condition is `hypot(w, h)`.

    `item_gap_y: 0` is included on purpose: the floor then permits touching, and
    a caller who asks for no gap gets none. Nothing here quietly inserts one.
    """
    for gap in (*_CYCLE_GAPS, 0):
        result = compose_two_column_cycle(
            _cycle_case(n, profile), {"item_gap_y": gap})
        slot = result["row_pitch"] - gap
        for column, members in _cycle_columns(result).items():
            for upper, lower in zip(members, members[1:]):
                clearance = upper["bottom"] - lower["top"]
                a = slot - rect_height(upper)
                b = slot - rect_height(lower)
                expected = gap + -(-a // 2) + b // 2
                assert clearance == expected, (
                    f"n={n} {profile} gap={gap} column {column}: clearance "
                    f"{clearance} against the derived {expected}")
                assert clearance >= gap, (
                    f"n={n} {profile} gap={gap}: clearance {clearance} is "
                    f"under the gap")


@pytest.mark.parametrize("profile", sorted(_CYCLE_HEIGHT_PROFILES))
@pytest.mark.parametrize("n", _CYCLE_COUNTS)
def test_the_horizontal_clearance_is_the_column_pitch_less_the_width(n, profile):
    """The other half of the condition, and the only one that separates columns.

    Items in different columns are apart on the x axis by this much at EVERY
    row, which is why their rows never have to be compared: two rects overlap
    only when they overlap on both axes.
    """
    for width in _CYCLE_WIDTHS:
        for gap_x in _CYCLE_GAPS:
            result = compose_two_column_cycle(
                _cycle_case(n, profile),
                {"item_width": width, "item_gap_x": gap_x})
            columns = _cycle_columns(result)
            if len(columns) < 2:
                continue
            left = {i["right"] for i in columns[0]}
            right = {i["left"] for i in columns[1]}
            assert len(left) == 1 and len(right) == 1
            assert right.pop() - left.pop() == gap_x, (n, profile, width, gap_x)
            assert result["column_pitch"] - width == gap_x


@pytest.mark.parametrize("n", _CYCLE_COUNTS)
def test_nothing_overlaps_across_the_whole_matrix(n):
    """The blunt check, over every profile, width and gap combination.

    `assert_cycle_sane` runs the overlap test; this is the one that runs it over
    the product of the content axes rather than one point of it. Three of the
    four defects this engine has shipped were invisible at one point and obvious
    over the product.
    """
    for profile in sorted(_CYCLE_HEIGHT_PROFILES):
        for width in _CYCLE_WIDTHS:
            for gap in _CYCLE_GAPS:
                result = compose_two_column_cycle(
                    _cycle_case(n, profile),
                    {"item_width": width, "item_gap_x": gap,
                     "item_gap_y": gap})
                assert_cycle_sane(result, f"n={n} {profile} {width} {gap}")


# ---------------------------------------------------------------------------
# The pitch is a floor
# ---------------------------------------------------------------------------
def test_a_row_pitch_too_small_for_the_tallest_box_is_widened_and_reported():
    """The tallest box is CONTENT, so a small pitch is widened, not refused.

    The opposite decision from `compose_layered_bands`, which raises when its
    `row_pitch` is under its `item_height` - there both numbers are the caller's
    own spec and disagreeing with yourself is an error. Here the caller cannot
    be expected to know how tall the content made the tallest box.
    """
    items = _cycle_items([60, 300, 60, 60])
    result = compose_two_column_cycle(items, {"row_pitch": 80})
    assert result["row_pitch"] == 300 + DEFAULT_SPEC["item_gap_y"]
    assert_cycle_sane(result, "widened")

    # And a pitch that already clears the tallest box is honored exactly.
    roomy = compose_two_column_cycle(items, {"row_pitch": 500})
    assert roomy["row_pitch"] == 500
    assert_cycle_sane(roomy, "roomy")


def test_the_derived_pitch_still_clears_a_box_shorter_than_the_spec_default():
    """Every item shorter than `item_height` must not tighten the pitch below
    what the spec derived, or a caller's stated spacing would change with the
    content."""
    result = compose_two_column_cycle(
        _cycle_items([20, 20, 20]), {"item_height": 60, "item_gap_y": 20})
    assert result["row_pitch"] == 80
    assert_cycle_sane(result, "short items")


def test_a_column_pitch_narrower_than_the_item_width_is_refused():
    """Both numbers are spec, so this is the caller contradicting themselves."""
    with pytest.raises(LayoutError, match="spec.h_pitch"):
        compose_two_column_cycle(
            _cycle_items([None, None]), {"item_width": 140, "h_pitch": 100})


@pytest.mark.parametrize("profile", sorted(_CYCLE_HEIGHT_PROFILES))
def test_the_composition_never_shrinks_as_the_cycle_grows(profile):
    """A series over every count, not two points: the wrapped-band width once
    agreed between two counts by luck, and two points cannot tell."""
    widths, heights = [], []
    for n in _CYCLE_COUNTS:
        b = compose_two_column_cycle(_cycle_case(n, profile))["bounds"]
        widths.append(b["width"])
        heights.append(b["height"])
    assert widths == sorted(widths), (profile, widths)
    assert heights == sorted(heights), (profile, heights)


# ---------------------------------------------------------------------------
# Refusals
# ---------------------------------------------------------------------------
def test_an_empty_cycle_is_an_error():
    with pytest.raises(LayoutError, match="at least one item"):
        compose_two_column_cycle([])


def test_an_item_needs_an_id():
    with pytest.raises(LayoutError, match=r"items\[1\]\.id"):
        compose_two_column_cycle([{"id": 1}, {"name": "nameless"}])


def test_a_duplicate_id_is_refused():
    with pytest.raises(LayoutError, match="duplicate item id"):
        compose_two_column_cycle([{"id": 1}, {"id": 1}])


@pytest.mark.parametrize("height", [0, -40])
def test_a_non_positive_item_height_is_refused(height):
    with pytest.raises(LayoutError, match=r"items\[0\]\.item_height"):
        compose_two_column_cycle([{"id": 1, "item_height": height}])


def test_a_non_numeric_item_height_is_refused():
    with pytest.raises(LayoutError, match=r"items\[0\]\.item_height"):
        compose_two_column_cycle([{"id": 1, "item_height": "tall"}])


@pytest.mark.parametrize("key", ["item_width", "row_pitch", "h_pitch",
                                "item_gap_y"])
def test_a_spec_key_other_than_the_height_is_refused_on_an_item(key):
    """Refused rather than ignored. `item_width` on an item is the plausible
    mistake, and a silently dropped size is an afternoon of hunting."""
    with pytest.raises(LayoutError, match=rf"items\[0\]\.{key}"):
        compose_two_column_cycle([{"id": 1, key: 200}])


def test_an_unknown_non_spec_key_on_an_item_is_left_alone():
    """The refusal above is scoped to SPEC keys. A caller threading its own
    bookkeeping through an item - a stereotype, a source path - is not making
    the mistake that check exists for."""
    result = compose_two_column_cycle(
        [{"id": 1, "stereotype": "WBA::WBABusinessApplication"}])
    assert len(result["items"]) == 1


# ---------------------------------------------------------------------------
# The seam: the shipped linter, over the same matrix
# ---------------------------------------------------------------------------
def _cycle_verified_like(result):
    """A `verify_diagram`-shaped payload from composed rects. Hermetic."""
    objects = [{"element_id": int(i["id"]), "name": i.get("name", ""),
                "type": "Class",
                "left": i["left"], "top": i["top"],
                "right": i["right"], "bottom": i["bottom"]}
               for i in result["items"]]
    b = result["bounds"]
    return {
        "objects": objects,
        "links": [],
        "canvas": {"cx": b["right"] + 100, "cy": -b["bottom"] + 100},
    }


def _cycle_groupings(result, payload):
    """The grouping the linter cannot infer, as this grammar means it.

    `columns` are the two legs of the cycle, which is what the spacing rule
    should judge. `roles` are grouped BY HEIGHT rather than as one role for the
    whole cycle: the uniform-sizing rule compares heights as well as widths, and
    a content-driven height difference is not a defect. That is the caller's call
    to make - the rule says so - and this is the caller making it.
    """
    by_id = {o["element_id"]: o for o in payload["objects"]}
    columns = [[by_id[int(i["id"])] for i in members]
               for _, members in sorted(_cycle_columns(result).items())]
    roles = {}
    for item in result["items"]:
        roles.setdefault(f"h{rect_height(item)}", []).append(
            by_id[int(item["id"])])
    return {"columns": columns, "roles": roles}


@pytest.mark.parametrize("profile", sorted(_CYCLE_HEIGHT_PROFILES))
@pytest.mark.parametrize("n", _CYCLE_COUNTS)
def test_the_shipped_linter_finds_nothing_across_the_content_matrix(n, profile):
    """THE SEAM, and the reason this grammar is not signed off on one example.

    The engine places the rects; `lint.py` judges them, independently written and
    in its own module. Nothing keeps the two together except a test that runs the
    second over the first's output, and it has to run over the MATRIX: the
    grammar's whole difficulty is that a scheme which looks right at one height
    profile drifts at another.

    Warnings count as failures here, as they do in the sweep harness: `pitch` and
    `ragged-stack` are warnings by design, so asserting only on errors would test
    none of the rules this exists for.
    """
    lint = pytest.importorskip("lint")
    for width in _CYCLE_WIDTHS:
        for gap in _CYCLE_GAPS:
            result = compose_two_column_cycle(
                _cycle_case(n, profile),
                {"item_width": width, "item_gap_x": gap, "item_gap_y": gap})
            payload = _cycle_verified_like(result)
            grouped = _cycle_groupings(result, payload)
            report = lint.lint_diagram(
                payload, roles=grouped["roles"], columns=grouped["columns"])
            blocking = [f for f in report.findings
                        if f.severity in ("error", "warning")]
            label = f"n={n} {profile} w={width} gap={gap}"
            assert not blocking, (
                f"{label}: " + "; ".join(
                    f"{f.rule} [{f.severity}] {f.message}" for f in blocking))


def test_the_linter_run_above_actually_measures_the_spacing():
    """The vacuous-zero guard. A clean report from rules that never ran is what
    a harness ignoring its own input produces, and this programme has already
    quoted one - hence `roles_measured` and `crossings_measured_over` existing at
    all. So the denominators are asserted, not just the findings."""
    lint = pytest.importorskip("lint")
    result = compose_two_column_cycle(_cycle_case(9, "graded"))
    payload = _cycle_verified_like(result)
    grouped = _cycle_groupings(result, payload)
    report = lint.lint_diagram(
        payload, roles=grouped["roles"], columns=grouped["columns"])
    assert report.metrics["pitch_groups_measured"] == 2, report.metrics
    assert report.metrics["objects"] == 9


def test_declaring_the_whole_cycle_one_role_is_what_the_linter_objects_to():
    """The control for the role advice, which is otherwise just a claim.

    Grouped by height the uniform-sizing rule is silent; grouped as one role it
    fires. Both halves are asserted, because "declare a role per height" is only
    worth writing down if the other way round is genuinely caught - and because a
    caller who ignores it gets a defect report on correct output.
    """
    lint = pytest.importorskip("lint")
    result = compose_two_column_cycle(_cycle_case(6, "alternating"))
    payload = _cycle_verified_like(result)
    every_item = list(payload["objects"])

    one_role = lint.lint_diagram(payload, roles={"state": every_item})
    assert [f.rule for f in one_role.findings if f.rule == "uniform-sizing"]

    per_height = lint.lint_diagram(
        payload, roles=_cycle_groupings(result, payload)["roles"])
    assert not [f for f in per_height.findings
                if f.rule == "uniform-sizing"], per_height.metrics


def _top_aligned_payload(result):
    """The same items in the same slots, seated at the TOP instead of centered.

    The obvious implementation, and the one a reader of the engine would assume:
    a row's slot top is `origin_top - row * pitch` and the box hangs from it.
    """
    pitch = result["row_pitch"]
    origin_top = DEFAULT_SPEC["origin_top"]
    objects = []
    for item in result["items"]:
        top = origin_top - item["row"] * pitch
        objects.append({"element_id": int(item["id"]), "name": "",
                        "type": "Class",
                        "left": item["left"], "right": item["right"],
                        "top": top, "bottom": top - rect_height(item)})
    by_id = {o["element_id"]: o for o in objects}
    columns = [[by_id[int(i["id"])] for i in members]
               for _, members in sorted(_cycle_columns(result).items())]
    return {"objects": objects, "links": [], "canvas": {}}, columns


@pytest.mark.parametrize("profile", ["alternating", "extreme", "one-tall"])
@pytest.mark.parametrize("n", [6, 9])
def test_top_aligning_the_boxes_would_have_failed_the_same_linter(profile, n):
    """THE CONTROL that makes the centering decision load-bearing.

    The linter judges a column of unequal boxes on its center pitch, so the
    top-aligned variant reports uneven spacing by tens of units. Without this
    test, "centers, not tops" is an assertion in a docstring that nothing
    checks; with it, a future edit that switches to top alignment fails here
    rather than shipping.

    Three profiles, not all seven, and which three is itself a measurement -
    see `test_a_linear_height_ramp_hides_the_top_alignment_defect` for the two
    that cannot serve as a control and why.
    """
    lint = pytest.importorskip("lint")
    result = compose_two_column_cycle(_cycle_case(n, profile))
    payload, columns = _top_aligned_payload(result)

    report = lint.lint_diagram(payload, columns=columns)
    fired = [f for f in report.findings if f.rule == "pitch"]
    assert fired, (
        f"{profile} n={n}: top-aligning the boxes did not trip the spacing "
        f"rule, so this control proves nothing about why the engine centers "
        f"them")
    assert report.metrics["worst_pitch_spread"] > 8, report.metrics


@pytest.mark.parametrize("profile", ["graded", "odd-parity"])
def test_a_linear_height_ramp_hides_the_top_alignment_defect(profile):
    """A blind spot in the seam, recorded because it was nearly trusted.

    The control above was first written over `graded` and came out SILENT. A
    linear ramp of heights makes the top-aligned center pitch deviate by a
    CONSTANT - half the step - at every pair, and the spacing rule measures the
    SPREAD of the pitches, which stays zero. So a defect that the same rule
    catches at 90 to 399 units on an irregular profile is completely invisible
    on a regular one.

    Two things follow, and both are the reason this is a test rather than a
    comment. A control has to be chosen against content that discriminates, and
    a green spacing report on smoothly graded content is weaker evidence than
    the same report on irregular content. The equally sized profiles are silent
    for a different and uninteresting reason - top and center coincide - so they
    are not listed here.
    """
    lint = pytest.importorskip("lint")
    result = compose_two_column_cycle(_cycle_case(9, profile))
    payload, columns = _top_aligned_payload(result)
    report = lint.lint_diagram(payload, columns=columns)
    assert not [f for f in report.findings if f.rule == "pitch"], (
        f"{profile} now discriminates; it can be promoted into the control "
        f"above and this test deleted")


# ---------------------------------------------------------------------------
# `_reach` models every border as a rectangle, and the error is stated
# ---------------------------------------------------------------------------
# APT-2026-0193. Not a bug to be fixed here: nothing in the layout input says an
# element is a circle, so `_reach` cannot know. What it must not be is unrecorded.
# These pin the error itself, so it cannot drift without a failure, and they pin
# the figures the item quoted so the claim is reproducible rather than remembered.

def test_reach_spread_is_half_the_diagonal_less_half_the_shorter_side():
    assert compose.reach_spread(120, 120) == pytest.approx(
        (math.hypot(120, 120) - 120) / 2)
    # A square has the largest spread relative to its own size, and for a square
    # of side d it is exactly d * (sqrt(2) - 1) / 2 per spoke end.
    for d in (60, 120, 150, 400):
        assert compose.reach_spread(d, d) == pytest.approx(d * (math.sqrt(2) - 1) / 2)
    # A circle's TRUE reach is constant, so the spread is entirely the error.
    assert compose.reach_spread(150, 150) == pytest.approx(31.066, abs=1e-3)


def test_reach_spread_is_the_gap_between_the_largest_and_smallest_reach():
    """Derived from `_reach` itself by sampling, not from the formula.

    Finely, because the maximum is at the CORNER and a non-square box puts that
    at a fractional angle - whole degrees miss it and understate the spread.
    """
    for w, h in ((120, 120), (140, 60), (90, 70)):
        reaches = [compose._reach(w, h, a / 50.0) for a in range(360 * 50)]
        assert compose.reach_spread(w, h) == pytest.approx(
            max(reaches) - min(reaches), abs=0.02)


def test_a_ring_of_square_items_bulges_by_twice_the_reach_spread():
    """The measured error, taken off both ends of every spoke.

    Reproduces APT-2026-0193's figures exactly: 150x150 items at radius 229 give
    379.0 on the axes against 441.2 on the diagonals, which is 16.4% - and the
    16.4% is a property of THAT radius, while the 62.1 units is a property of the
    item size alone.
    """
    out = compose.compose_radial([{"id": i} for i in range(8)],
                                 {"item_width": 150, "item_height": 150,
                                  "radius": 229},
                                 hub={"id": 99})
    center = out["center"]
    distance = {}
    for item in out["items"]:
        if item["id"] == 99:
            continue
        cx, cy = _center_of(item)
        distance[item["angle"]] = math.hypot(cx - center["x"], cy - center["y"])
    on_axis, diagonal = distance[0.0], distance[45.0]
    assert on_axis == pytest.approx(379.0, abs=0.5)
    assert diagonal == pytest.approx(441.2, abs=0.5)
    assert diagonal - on_axis == pytest.approx(2 * compose.reach_spread(150, 150),
                                               abs=0.5)
    assert (diagonal / on_axis - 1) == pytest.approx(0.164, abs=0.002)
    # The guard: the result STATES the error rather than leaving it to be found.
    assert out["reach_spread"] == pytest.approx(compose.reach_spread(150, 150))


def test_every_ring_result_carries_the_approximations_error():
    for w, h in ((120, 120), (140, 60)):
        out = compose.compose_radial([{"id": i} for i in range(4)],
                                     {"item_width": w, "item_height": h})
        assert out["reach_spread"] == pytest.approx(compose.reach_spread(w, h))

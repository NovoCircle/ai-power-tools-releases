#!/usr/bin/env python3
"""Tests for the `radial_tree` layout grammar.

Run from the repository root:

    python -m pytest ea-diagram-composition/tools/test_compose_radial_tree.py -q

Nothing here touches a repository, a COM object or the filesystem. If any test
in this file needs Sparx EA to pass, the layer boundary has been broken.

Two conventions worth reading before editing:

* The geometry helpers below are written out rather than imported from
  `compose_radial_tree`. A test that borrowed the module's own `_reach` would
  agree with it by construction, including on the day both are wrong, and the
  point of these is to measure the finished rectangles the way something
  downstream does.
* Rects are in EA's flipped-y convention, where `top` is greater than `bottom`.
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

import pytest

_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

from compose import LayoutError, rects_overlap  # noqa: E402
from compose_radial_tree import (  # noqa: E402
    DEFAULT_TREE_SPEC,
    compose_radial_tree,
)


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------
def _tree(shape, counter=None):
    """Build an input tree from a nested shape.

    An int `n` is a branch with `n` leaf children (0 for a bare leaf); a tuple
    is a branch whose children are described by the tuple. Ids are handed out in
    order so a test can talk about them, and they are unique across the tree.
    """
    counter = counter if counter is not None else iter(range(1, 10_000))
    out = []
    for entry in shape:
        node = {"id": next(counter)}
        if isinstance(entry, tuple):
            node["items"] = _tree(entry, counter)
        elif entry:
            node["items"] = [{"id": next(counter)} for _ in range(entry)]
        out.append(node)
    return out


def _span(r):
    return (f"(l={r['left']} t={r['top']} r={r['right']} b={r['bottom']} "
            f"{r['right'] - r['left']}x{r['top'] - r['bottom']})")


def assert_no_overlaps(items, label=""):
    for i, a in enumerate(items):
        for b in items[i + 1:]:
            assert not rects_overlap(a, b), (
                f"{label}: {a['id']} {_span(a)} overlaps {b['id']} {_span(b)}")


def assert_valid_rects(result, label=""):
    for item in result["items"]:
        assert item["right"] > item["left"], f"{label}: {_span(item)}"
        assert item["top"] > item["bottom"], f"{label}: {_span(item)}"


def _center(r):
    return ((r["left"] + r["right"]) / 2.0, (r["top"] + r["bottom"]) / 2.0)


def _reach_along(r, ux, uy):
    """How far a rect's border sits from its center along a unit vector."""
    along_x = ((r["right"] - r["left"]) / 2.0) / abs(ux) if ux else math.inf
    along_y = ((r["top"] - r["bottom"]) / 2.0) / abs(uy) if uy else math.inf
    return min(along_x, along_y)


def _spokes_by_parent(result):
    """The DRAWN length of every spoke, grouped by the box it radiates from.

    Center to center, less the stretch inside the parent and the stretch inside
    the child - the two parts of the line that are hidden under a box and never
    seen. What is left is the ink the reader judges the branch by. A tree with
    no central topic radiates from the center POINT, which reaches nowhere.
    """
    by_id = {i["id"]: i for i in result["items"]}
    groups = {}
    for item in result["items"]:
        if item["ring"] == 0:
            continue
        parent = by_id.get(item["container_id"])
        px, py = (_center(parent) if parent is not None
                  else (result["center"]["x"], result["center"]["y"]))
        ix, iy = _center(item)
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


# Integer rounding of a center can move a spoke end by half a unit at each end,
# so two spokes may legitimately differ by one. `lint.PITCH_TOLERANCE` is 8.
SPOKE_TOLERANCE = 2.0


def _by_id(result):
    return {i["id"]: i for i in result["items"]}


def _children_of(result, parent_id):
    return [i for i in result["items"] if i["container_id"] == parent_id]


# ---------------------------------------------------------------------------
# The shape of the result
# ---------------------------------------------------------------------------
def test_a_mind_map_comes_out_as_a_center_branches_and_sub_branches():
    """The corpus shape this grammar exists for, laid out end to end."""
    result = compose_radial_tree(
        [{"id": 1, "name": "Paperless Office",
          "items": [{"id": 11, "name": "No check books"},
                    {"id": 12, "name": "Emailed electronic receipts"},
                    {"id": 13, "name": "Payable invoices arrive electronic"}]},
         {"id": 2, "name": "Day One Functionality"},
         {"id": 3, "name": "Inventory Management",
          "items": [{"id": 31, "name": "Track the batch a book arrived in"},
                    {"id": 32, "name": "Stock levels for peak periods"}]}],
        hub={"id": 100, "name": "Account Opening Needs, Westbrook Bank"},
    )
    assert result["grammar"] == "radial_tree"
    assert result["containers"] == []
    assert_valid_rects(result, "mind map")
    assert_no_overlaps(result["items"], "mind map")

    by_id = _by_id(result)
    assert by_id[100]["ring"] == 0 and by_id[100]["container_id"] is None
    assert by_id[100]["name"] == "Account Opening Needs, Westbrook Bank"
    for branch in (1, 2, 3):
        assert by_id[branch]["ring"] == 1
        assert by_id[branch]["container_id"] == 100
    for leaf in (11, 12, 13):
        assert by_id[leaf]["ring"] == 2
        assert by_id[leaf]["container_id"] == 1
    for leaf in (31, 32):
        assert by_id[leaf]["container_id"] == 3


def test_the_composition_starts_at_the_origin_like_every_other_grammar():
    result = compose_radial_tree(_tree((2, 0, 3)), hub={"id": 900},
                                 spec={"origin_left": 40, "origin_top": -70})
    assert result["bounds"]["left"] == 40
    assert result["bounds"]["top"] == -70
    assert result["bounds"]["width"] > 0 and result["bounds"]["height"] > 0


def test_the_same_input_lays_out_identically_twice():
    """No clock, no randomness, no set iteration order leaking into geometry."""
    first = compose_radial_tree(_tree((3, 1, (2, 2))), hub={"id": 800})
    second = compose_radial_tree(_tree((3, 1, (2, 2))), hub={"id": 800})
    assert first == second


def test_a_tree_with_no_central_topic_radiates_from_a_bare_point():
    result = compose_radial_tree(_tree((2, 2, 2)))
    assert all(i["ring"] >= 1 for i in result["items"])
    assert all(i["container_id"] is None
               for i in result["items"] if i["ring"] == 1)
    assert_no_overlaps(result["items"], "no hub")


def test_names_are_carried_and_label_length_does_not_move_a_box():
    """Boxes are sized by the spec, so a long label changes nothing geometric.

    Which is worth pinning: a caller who widens boxes for a long label does it
    through the spec, and a grammar that quietly resized for text would put the
    two out of step.
    """
    short = compose_radial_tree([{"id": 1, "name": "A"},
                                 {"id": 2, "name": "B"}], hub={"id": 9})
    long_name = "Payable invoices need to be electronic, and paper scanned " * 3
    long = compose_radial_tree([{"id": 1, "name": long_name},
                                {"id": 2, "name": "B"}], hub={"id": 9})
    assert _by_id(long)[1]["name"] == long_name
    for a, b in zip(short["items"], long["items"]):
        assert (a["left"], a["top"], a["right"], a["bottom"]) == (
            b["left"], b["top"], b["right"], b["bottom"])


# ---------------------------------------------------------------------------
# Angular room: the whole point of the grammar
# ---------------------------------------------------------------------------
def test_a_branch_gets_angular_room_in_proportion_to_its_leaves():
    """Eight children earn eight times the wedge of one child.

    This is the property that makes this grammar worth having. An even split
    would give all three branches 120 degrees each.
    """
    result = compose_radial_tree(_tree((8, 1, 1)), hub={"id": 900})
    by_id = _by_id(result)
    branches = [i for i in result["items"] if i["ring"] == 1]
    wedges = {i["id"]: i["wedge"] for i in branches}
    ids = [i["id"] for i in sorted(branches, key=lambda i: i["index"])]
    heavy, light_a, light_b = ids
    assert by_id[heavy]["leaves"] == 8
    assert by_id[light_a]["leaves"] == 1
    assert wedges[light_a] == pytest.approx(wedges[light_b])
    assert wedges[heavy] == pytest.approx(8 * wedges[light_a], rel=1e-6)
    assert sum(wedges.values()) == pytest.approx(360.0, abs=1e-6)


def test_an_interior_branch_weighs_what_its_own_subtree_weighs():
    """Weight is leaves, not nodes: an interior node adds no room of its own."""
    result = compose_radial_tree(_tree(((2, 3), 0)), hub={"id": 900})
    by_id = _by_id(result)
    branch = [i for i in result["items"] if i["ring"] == 1 and i["index"] == 0][0]
    assert branch["leaves"] == 5
    assert by_id[branch["id"]]["wedge"] == pytest.approx(360.0 * 5 / 6, abs=1e-6)


def test_a_child_wedge_sits_wholly_inside_its_parents_wedge():
    """Disjoint-by-construction is what stops two branches trading children."""
    result = compose_radial_tree(_tree(((3, 2), (1, 1), 4)), hub={"id": 900})
    by_id = _by_id(result)
    for item in result["items"]:
        if item["ring"] < 2:
            continue
        parent = by_id[item["container_id"]]
        # Compared as half-widths about each ray, because bearings wrap at 360
        # and an interval that straddles the wrap would compare nonsensically.
        offset = (item["angle"] - parent["angle"] + 540.0) % 360.0 - 180.0
        assert abs(offset) + item["wedge"] / 2.0 <= parent["wedge"] / 2.0 + 1e-6, (
            f"{item['id']} escapes the wedge of {parent['id']}")


def test_sibling_wedges_tile_their_parents_share_without_a_gap_or_an_overlap():
    result = compose_radial_tree(_tree(((4, 1, 2),)), hub={"id": 900})
    by_id = _by_id(result)
    parent = [i for i in result["items"] if i["ring"] == 1][0]
    kids = sorted(_children_of(result, parent["id"]), key=lambda i: i["index"])
    edges = []
    for kid in kids:
        offset = (kid["angle"] - parent["angle"] + 540.0) % 360.0 - 180.0
        edges.append((offset - kid["wedge"] / 2.0, offset + kid["wedge"] / 2.0))
    # 2e-3 rather than exactly, because `angle` and `wedge` come back rounded
    # to three decimals for the caller's benefit.
    for (_, hi), (lo, _) in zip(edges, edges[1:]):
        assert hi == pytest.approx(lo, abs=2e-3), "wedges must abut exactly"


def test_start_angle_is_the_bearing_of_the_first_branch():
    """Stated the way `compose_radial` states it, so a caller moving between the
    two grammars does not have to discover that one means something else."""
    for start in (0, 45, -60, 180):
        result = compose_radial_tree(_tree((2, 1, 1)), hub={"id": 900},
                                     spec={"start_angle": start})
        first = [i for i in result["items"]
                 if i["ring"] == 1 and i["index"] == 0][0]
        assert first["angle"] == pytest.approx(start % 360.0, abs=1e-6)


def test_zero_degrees_is_straight_up_and_ninety_is_to_the_right():
    """Measured off the rectangles, not taken from the prose.

    This repo has already shipped a reference that documented the radial
    grammar's direction BACKWARDS, so the direction is pinned against geometry
    here rather than against a sentence. EA's vertical axis is inverted, so
    "above" means a numerically GREATER `top`.
    """
    result = compose_radial_tree([{"id": 1}, {"id": 2}, {"id": 3}, {"id": 4}],
                                 hub={"id": 9}, spec={"start_angle": 0})
    by_id = _by_id(result)
    hub, up, right, down, left = (by_id[9], by_id[1], by_id[2], by_id[3],
                                  by_id[4])
    assert [by_id[i]["angle"] for i in (1, 2, 3, 4)] == [0.0, 90.0, 180.0, 270.0]
    hx, hy = _center(hub)
    assert _center(up)[1] > hy and abs(_center(up)[0] - hx) < 2
    assert _center(right)[0] > hx and abs(_center(right)[1] - hy) < 2
    assert _center(down)[1] < hy
    assert _center(left)[0] < hx


def test_a_partial_sweep_divides_into_wedges_rather_than_reaching_both_ends():
    """Where this parts company with `compose_radial` on purpose.

    `compose_radial` spreads a fan inclusive of both ends. A tree cannot: an end
    branch's wedge would hang half outside the sweep, and its children with it.
    So a 180-degree sweep of three equal branches lands at 30, 90 and 150.
    """
    result = compose_radial_tree(_tree((0, 0, 0)), hub={"id": 900},
                                 spec={"sweep": 180, "start_angle": 30})
    angles = [i["angle"] for i in sorted(
        (i for i in result["items"] if i["ring"] == 1),
        key=lambda i: i["index"])]
    assert angles == [pytest.approx(a) for a in (30.0, 90.0, 150.0)]


def test_a_node_spends_at_most_max_branch_sweep_on_its_own_children():
    """A wedge wider than the cap is territory, not fan.

    Without the cap a branch holding most of the circle would spread its
    children across all of it, and they would sweep back past the middle
    instead of reading as growing outward.
    """
    result = compose_radial_tree(_tree((6, 0)), hub={"id": 900},
                                 spec={"max_branch_sweep": 90})
    heavy = [i for i in result["items"] if i["ring"] == 1 and i["index"] == 0][0]
    assert heavy["wedge"] > 90.0, "the branch should own more than it spends"
    kids = _children_of(result, heavy["id"])
    offsets = [(k["angle"] - heavy["angle"] + 540.0) % 360.0 - 180.0
               for k in kids]
    assert max(offsets) - min(offsets) <= 90.0 + 1e-6


def test_a_balanced_tree_still_comes_out_evenly_spaced():
    """Weighting is not a distortion: equal weights give the even split back."""
    for count in (2, 3, 4, 5, 8, 12):
        result = compose_radial_tree(_tree((0,) * count), hub={"id": 900})
        angles = sorted(i["angle"] for i in result["items"] if i["ring"] == 1)
        steps = [b - a for a, b in zip(angles, angles[1:])]
        steps.append(360.0 - sum(steps))
        assert max(steps) - min(steps) < 1e-6, f"count={count}: {steps}"


# ---------------------------------------------------------------------------
# Clearance
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("item_width,item_height", [
    (140, 60), (60, 140), (100, 100), (90, 88), (400, 40), (60, 300),
])
@pytest.mark.parametrize("shape", [
    (0,), (0, 0), (0,) * 12, (8, 1), (8, 1, 1), (8, 0, 1, 0, 3, 0),
    (5, 5, 5), (1,) * 12, ((3, 1), (0,), (2, 2, 2)), (((2, 2), 1), 0, (1,)),
    (8, 1, 8, 1, 8, 1),
])
def test_nothing_overlaps_across_shape_and_box_aspect(shape, item_width,
                                                      item_height):
    """The matrix that matters: uneven trees, every depth to three, every aspect.

    A near-square box is included on purpose. The clearance condition here is
    the box DIAGONAL, and `max(w, h)` - the condition this engine shipped once -
    is at its most wrong for a near-square box, where the diagonal is 41% longer
    than either side.
    """
    result = compose_radial_tree(
        _tree(shape), hub={"id": 9999},
        spec={"item_width": item_width, "item_height": item_height})
    assert_valid_rects(result, f"{shape} {item_width}x{item_height}")
    assert_no_overlaps(result["items"], f"{shape} {item_width}x{item_height}")


@pytest.mark.parametrize("sweep", [90, 180, 270, 360])
@pytest.mark.parametrize("branches", list(range(1, 13)))
def test_nothing_overlaps_from_one_branch_to_twelve_at_any_sweep(branches,
                                                                 sweep):
    """One heavy branch beside light ones, at every branch count and sweep."""
    shape = tuple([8] + [1] * (branches - 1))
    result = compose_radial_tree(_tree(shape), hub={"id": 9999},
                                 spec={"sweep": sweep})
    assert_no_overlaps(result["items"], f"{branches} branches, sweep {sweep}")


def test_neighbors_on_a_ring_clear_each_other_by_the_box_diagonal():
    """The condition derived, checked directly rather than through overlap.

    Two axis-aligned boxes miss each other when they are a full width apart
    horizontally OR a full height apart vertically. Two inside both of those are
    inside a w-by-h box and so closer than its diagonal, which makes
    `separation >= hypot(w, h)` exactly the condition that rules the overlap
    out. `max(w, h)` does not, and this asserts the stronger one.
    """
    width, height = 90, 88
    diagonal = math.hypot(width, height)
    assert diagonal > max(width, height) * 1.39, "the near-square case is the point"
    for count in (2, 3, 5, 8, 12):
        result = compose_radial_tree(
            _tree((0,) * count), hub={"id": 9999},
            spec={"item_width": width, "item_height": height})
        ring = sorted((i for i in result["items"] if i["ring"] == 1),
                      key=lambda i: i["index"])
        centers = [_center(i) for i in ring]
        for a, b in zip(centers, centers[1:] + centers[:1]):
            if len(centers) < 2:
                continue
            assert math.dist(a, b) >= diagonal, f"count={count}"


def test_a_radius_too_small_for_its_branches_is_widened():
    tight = compose_radial_tree(_tree((0,) * 10), hub={"id": 900},
                                spec={"radius": 5})
    assert tight["radius"] > 5
    assert_no_overlaps(tight["items"], "widened")


def test_a_radius_with_room_to_spare_is_left_alone():
    roomy = compose_radial_tree(_tree((0, 0)), hub={"id": 900},
                                spec={"radius": 400})
    assert roomy["radius"] == 400
    assert roomy["gap_scale"] == 1.0


def test_the_widening_guard_reports_what_it_took():
    """`gap_scale` is 1.0 when the analytic floors were already enough, which is
    the usual case, and larger when the collision check had to push."""
    easy = compose_radial_tree(_tree((2, 2, 2)), hub={"id": 900})
    assert easy["gap_scale"] == 1.0
    crowded = compose_radial_tree(_tree((5, 5, 5)), hub={"id": 900},
                                  spec={"sweep": 90})
    assert crowded["gap_scale"] >= 1.0
    assert_no_overlaps(crowded["items"], "crowded fan")


# ---------------------------------------------------------------------------
# Spokes
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("item_width,item_height", [
    (140, 60), (60, 140), (100, 100), (90, 88), (400, 40),
])
def test_every_spoke_from_one_parent_is_the_same_drawn_length(item_width,
                                                              item_height):
    """`radius` is the CLEAR GAP, not a center-to-center distance.

    A branch at the top of a fan reaches back toward its parent by half its
    height and one at the side by half its width, so placing centers on a circle
    would leave the drawn spokes visibly unequal. Each box is pushed out by its
    own reach and its parent's, which is what holds the ink constant.
    """
    result = compose_radial_tree(
        _tree((4, 4, 0, 3)), hub={"id": 9999},
        spec={"item_width": item_width, "item_height": item_height})
    groups = _spokes_by_parent(result)
    assert len(groups) >= 4
    for parent, lengths in groups.items():
        if len(lengths) < 2:
            continue
        spread = max(lengths) - min(lengths)
        assert spread <= SPOKE_TOLERANCE, (
            f"{item_width}x{item_height} off {parent}: "
            f"{[round(v, 1) for v in lengths]}")


def test_placing_centers_on_one_circle_would_not_have_passed_that():
    """The control. Without it the test above proves only that the tree is
    small, not that the reach correction does anything."""
    result = compose_radial_tree(_tree((6,),), hub={"id": 9999},
                                 spec={"item_width": 400, "item_height": 40})
    by_id = _by_id(result)
    parent = [i for i in result["items"] if i["ring"] == 1][0]
    px, py = _center(parent)
    naive = []
    radius = 300.0
    for kid in _children_of(result, parent["id"]):
        radians = math.radians(kid["angle"] - 90.0)
        ux, uy = math.cos(radians), -math.sin(radians)
        # A box whose CENTER sits on a circle of one radius, measured the way
        # the real test measures: gap from the parent's border to the box's.
        naive.append(radius - _reach_along(parent, ux, uy)
                     - _reach_along(kid, ux, uy))
    assert max(naive) - min(naive) > SPOKE_TOLERANCE * 10


def test_a_spoke_off_a_branch_is_measured_from_that_branch_not_the_middle():
    """A sub-branch radiates from a BOX, and the correction applies twice."""
    result = compose_radial_tree(_tree((4, 4, 0)), hub={"id": 9999})
    groups = _spokes_by_parent(result)
    branch_ids = [i["id"] for i in result["items"] if i["ring"] == 1]
    assert {9999, branch_ids[0], branch_ids[1]} <= set(groups)
    for parent in branch_ids[:2]:
        assert len(groups[parent]) == 4


# ---------------------------------------------------------------------------
# The shipped linter
# ---------------------------------------------------------------------------
def _verified_like(result):
    """A `verify_diagram`-shaped payload built from composed rects.

    Hand-built, and hermetic: the linter reads rectangles and does not care
    whether EA or this module produced them. `element_id` has to survive
    `int()`, which one of the linter's other rules requires.
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


def _declared_rings(result, payload, sweep=None):
    """Every parent and its children, as `lint` wants a ring declared.

    Geometry cannot say which box is a hub and which are its ring, so the caller
    states it. A tree states one ring per parent.
    """
    by_id = {o["element_id"]: o for o in payload["objects"]}
    groups = {}
    for item in result["items"]:
        if item["container_id"] is None:
            continue
        groups.setdefault(item["container_id"], []).append(by_id[item["id"]])
    if sweep is None:
        return [(by_id[k], v) for k, v in groups.items()]
    return [(by_id[k], v, sweep) for k, v in groups.items()]


@pytest.mark.parametrize("item_width,item_height", [
    (140, 60), (60, 140), (90, 88), (400, 40),
])
@pytest.mark.parametrize("shape", [
    (0, 0), (8, 1), (8, 1, 1), (0,) * 12, (5, 5, 5),
    ((3, 1), (0,), (2, 2, 2)),
])
def test_the_shipped_linter_finds_nothing_to_report(shape, item_width,
                                                    item_height):
    """THE SEAM. The linter is written independently of this engine, in its own
    module, and measures the finished rectangles the way a drawn diagram would
    be measured. Rings are declared WITHOUT a sweep here, for the reason the
    next test spells out."""
    lint = pytest.importorskip("lint")
    result = compose_radial_tree(
        _tree(shape), hub={"id": 9999},
        spec={"item_width": item_width, "item_height": item_height})
    payload = _verified_like(result)
    report = lint.lint_diagram(payload,
                               rings=_declared_rings(result, payload))
    label = f"{shape} {item_width}x{item_height}"
    loud = [f for f in report.findings if f.severity in ("error", "warning")]
    assert not loud, f"{label}: {[(f.rule, f.message) for f in loud]}"
    assert report.metrics["overlaps"] == 0, label
    assert report.metrics.get("worst_spoke_spread", 0) <= SPOKE_TOLERANCE, label


def test_the_ring_angle_rule_applies_to_a_balanced_tree_and_not_to_a_weighted_one():
    """Whether `check_ring_angles` can judge this grammar at all, settled.

    That rule asks whether items are spread EVENLY around their hub. A weighted
    tree is deliberately not: that is the grammar. The two are reconciled the
    way the rule itself provides for - a ring declared without a sweep is not
    judged - and this pins both halves so neither drifts:

    * a balanced tree IS evenly spread, and is clean with its sweep declared;
    * a weighted tree is not, and declaring its sweep earns the warning, which
      is why a caller declares a weighted ring without one.

    `check_ring_spokes` and `check_no_overlaps` have no such caveat: both apply
    to this grammar in full, and the test above holds them.
    """
    lint = pytest.importorskip("lint")

    balanced = compose_radial_tree(_tree((0, 0, 0, 0)), hub={"id": 9999})
    payload = _verified_like(balanced)
    report = lint.lint_diagram(
        payload, rings=_declared_rings(balanced, payload, sweep=360))
    assert not [f for f in report.findings if f.rule == "uneven-ring-angles"]

    weighted = compose_radial_tree(_tree((8, 0, 0)), hub={"id": 9999})
    payload = _verified_like(weighted)
    report = lint.lint_diagram(
        payload, rings=_declared_rings(weighted, payload, sweep=360))
    assert [f for f in report.findings if f.rule == "uneven-ring-angles"], (
        "a weighted ring declared with a sweep is expected to be reported; if "
        "this stops happening the guidance to declare it sweepless is stale")

    report = lint.lint_diagram(payload,
                               rings=_declared_rings(weighted, payload))
    assert not [f for f in report.findings if f.severity in ("error", "warning")]


# ---------------------------------------------------------------------------
# Depth
# ---------------------------------------------------------------------------
def test_three_levels_below_the_middle_are_ordinary():
    result = compose_radial_tree(
        [{"id": 1, "items": [{"id": 2, "items": [{"id": 3}, {"id": 4}]}]},
         {"id": 5, "items": [{"id": 6, "items": [{"id": 7}]}]}],
        hub={"id": 9})
    assert max(i["ring"] for i in result["items"]) == 3
    assert_no_overlaps(result["items"], "depth three")


def test_a_tree_deeper_than_max_tree_depth_is_refused():
    deep = [{"id": 1, "items": [{"id": 2, "items": [
        {"id": 3, "items": [{"id": 4, "items": [{"id": 5}]}]}]}]}]
    with pytest.raises(LayoutError, match="max_tree_depth"):
        compose_radial_tree(deep, hub={"id": 9})
    result = compose_radial_tree(deep, hub={"id": 9},
                                 spec={"max_tree_depth": 5})
    assert max(i["ring"] for i in result["items"]) == 5


# ---------------------------------------------------------------------------
# Sizing overrides
# ---------------------------------------------------------------------------
def test_a_node_may_size_its_own_children_but_not_its_grandchildren():
    """Levels may differ, siblings may not, and it does not cascade."""
    result = compose_radial_tree(
        [{"id": 1, "item_width": 200, "item_height": 100,
          "items": [{"id": 2, "items": [{"id": 3}]}]}],
        hub={"id": 9})
    by_id = _by_id(result)
    assert by_id[2]["right"] - by_id[2]["left"] == 200
    assert by_id[2]["top"] - by_id[2]["bottom"] == 100
    assert by_id[3]["right"] - by_id[3]["left"] == DEFAULT_TREE_SPEC["item_width"]
    assert by_id[3]["top"] - by_id[3]["bottom"] == DEFAULT_TREE_SPEC["item_height"]


def test_a_node_may_widen_the_gap_to_its_own_children():
    near = compose_radial_tree([{"id": 1, "items": [{"id": 2}]}], hub={"id": 9})
    far = compose_radial_tree(
        [{"id": 1, "radius": 600, "items": [{"id": 2}]}], hub={"id": 9})
    near_gap = _spokes_by_parent(near)[1][0]
    far_gap = _spokes_by_parent(far)[1][0]
    assert far_gap > near_gap
    assert far_gap == pytest.approx(600, abs=SPOKE_TOLERANCE)


def test_a_node_may_not_restate_a_spec_wide_key():
    with pytest.raises(LayoutError, match="spec key"):
        compose_radial_tree([{"id": 1, "sweep": 90}], hub={"id": 9})


# ---------------------------------------------------------------------------
# Refusals
# ---------------------------------------------------------------------------
def test_an_empty_tree_is_refused():
    with pytest.raises(LayoutError, match="at least one branch"):
        compose_radial_tree([], hub={"id": 9})


def test_a_branch_that_states_no_children_is_refused():
    with pytest.raises(LayoutError, match="at least one"):
        compose_radial_tree([{"id": 1, "items": []}], hub={"id": 9})


def test_a_duplicate_id_anywhere_in_the_tree_is_refused():
    with pytest.raises(LayoutError, match="duplicate node id"):
        compose_radial_tree([{"id": 1, "items": [{"id": 2}]},
                             {"id": 2}], hub={"id": 9})
    with pytest.raises(LayoutError, match="duplicate node id"):
        compose_radial_tree([{"id": 9}], hub={"id": 9})


def test_a_node_without_an_id_is_refused():
    with pytest.raises(LayoutError, match=r"nodes\[0\].id"):
        compose_radial_tree([{"name": "no id"}], hub={"id": 9})


def test_an_unhashable_id_is_refused():
    with pytest.raises(LayoutError, match="hashable"):
        compose_radial_tree([{"id": ["list"]}], hub={"id": 9})


def test_a_tree_that_is_not_a_list_is_refused():
    with pytest.raises(LayoutError, match="expected a list"):
        compose_radial_tree({"id": 1}, hub={"id": 9})
    with pytest.raises(LayoutError, match="expected a dict"):
        compose_radial_tree(["not a node"], hub={"id": 9})


def test_an_unknown_spec_key_is_refused_including_one_from_another_grammar():
    with pytest.raises(LayoutError, match="wrap_width"):
        compose_radial_tree([{"id": 1}], spec={"wrap_width": 900})
    with pytest.raises(LayoutError, match="itemWidth"):
        compose_radial_tree([{"id": 1}], spec={"itemWidth": 200})


def test_a_nonsense_spec_value_is_refused():
    with pytest.raises(LayoutError, match="must be positive"):
        compose_radial_tree([{"id": 1}], spec={"item_width": 0})
    with pytest.raises(LayoutError, match="must not be negative"):
        compose_radial_tree([{"id": 1}], spec={"item_gap_x": -1})
    with pytest.raises(LayoutError, match="expected a number"):
        compose_radial_tree([{"id": 1}], spec={"radius": "220"})
    with pytest.raises(LayoutError, match="expected a number"):
        compose_radial_tree([{"id": 1}], spec={"start_angle": True})


def test_a_negative_start_angle_is_a_bearing_and_is_allowed():
    result = compose_radial_tree(_tree((0, 0)), hub={"id": 9},
                                 spec={"start_angle": -60})
    first = [i for i in result["items"]
             if i["ring"] == 1 and i["index"] == 0][0]
    assert first["angle"] == pytest.approx(300.0)

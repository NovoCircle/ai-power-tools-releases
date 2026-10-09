#!/usr/bin/env python3
"""Tests for the treemap layout grammar.

Run from the repository root:

    python -m pytest ea-diagram-composition/tools/test_compose_treemap.py -q

Nothing here touches a repository, a COM object or the filesystem. If any test
in this file needs Sparx EA to pass, the layer boundary has been broken.

Four conventions worth reading before editing:

* **The assertion is EXACT PARTITION, not "no overlap".** No-overlap passes for
  a tiling full of one-unit gaps, which is the defect integer rounding actually
  produces, and area conservation passes for one that overlaps by as much as it
  gaps. Together with containment the two are equivalent to an exact partition
  of axis-aligned rects, so `assert_partitions` asserts all three, and it is
  what nearly every test here ends with.
* Rect intersection is tested in EA's flipped-y convention, where `top` is
  greater than `bottom`. Tiles ABUT by design - a shared edge is not an
  overlap, and `rects_overlap` agrees.
* Items are nested inside their group containers by design, and a group header
  is nested inside its group, so a set mixing the two is SUPPOSED to overlap.
  Compare groups with groups and tiles with tiles.
* THE SWEEPS ARE THE POINT. This grammar's geometry is a continuous function of
  the weights, and the rounding defect it exists to avoid appears at one size
  and not at the next. So the partition tests run over 1..30 tiles, over equal
  / dominant / tiny / zero weights, and over regions from very tall to very
  wide, asserting exact equalities rather than a tolerance. A partition that
  happens to close at 1200x800 with three equal weights is not a proof.
"""
from __future__ import annotations

import sys
from fractions import Fraction
from pathlib import Path

import pytest

_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

from compose import LayoutError, rects_overlap  # noqa: E402
from compose_treemap import (  # noqa: E402
    DEFAULT_TREEMAP_SPEC,
    MAX_BOXES_PER_REGION,
    compose_treemap,
)


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------
# Regions chosen to span the shapes a single example hides: the square where the
# split-axis tie-break decides, the very wide and the very tall where a naive
# squarifier produces slivers, and one small enough that the minimum-tile floor
# is doing real work rather than sitting idle.
REGIONS = [
    (1200, 800), (800, 800), (2400, 400), (400, 2400), (600, 900), (400, 400),
]

# Weight shapes, each one a different way for the arithmetic to go wrong.
WEIGHT_SHAPES = {
    "equal": lambda n: [10] * n,
    "descending": lambda n: [n - i for i in range(n)],
    "dominant": lambda n: [99] + [1] * (n - 1),
    "tiny-tail": lambda n: [1000] + [1] * (n - 1) if n > 1 else [1000],
    "one-zero": lambda n: [0] + [5] * (n - 1) if n > 1 else [0],
    "all-zero": lambda n: [0] * n,
    "fractional": lambda n: [1 / (i + 3) for i in range(n)],
    "huge-range": lambda n: [10 ** (i % 7) for i in range(n)],
}

LONG_NAME = ("Consolidated Counterparty Settlement and Reconciliation "
             "Platform for Regional Operations")


def _span(r):
    return (r["left"], r["top"], r["right"], r["bottom"])


def area(r) -> int:
    return (r["right"] - r["left"]) * (r["top"] - r["bottom"])


def contains(outer, inner) -> bool:
    return (outer["left"] <= inner["left"] and outer["right"] >= inner["right"]
            and outer["top"] >= inner["top"]
            and outer["bottom"] <= inner["bottom"])


def assert_no_overlaps(rects, label=""):
    rects = list(rects)
    for i, a in enumerate(rects):
        for b in rects[i + 1:]:
            assert not rects_overlap(a, b), (
                f"{label}: overlap between {a.get('id')} {_span(a)} and "
                f"{b.get('id')} {_span(b)}"
            )


def assert_partitions(pieces, whole, label=""):
    """`pieces` EXACTLY tile `whole`: inside it, disjoint, and filling it.

    For axis-aligned rects the three together are equivalent to an exact
    partition, which is the property a one-unit gap and a one-unit overlap
    break in opposite directions and which neither a no-overlap test nor an
    area test catches on its own.
    """
    pieces = list(pieces)
    assert pieces, f"{label}: nothing to partition {_span(whole)} with"
    for p in pieces:
        assert p["right"] > p["left"] and p["top"] > p["bottom"], (
            f"{label}: {p.get('id')} {_span(p)} has no area")
        assert contains(whole, p), (
            f"{label}: {p.get('id')} {_span(p)} escapes {_span(whole)}")
    assert_no_overlaps(pieces, label)
    covered = sum(area(p) for p in pieces)
    assert covered == area(whole), (
        f"{label}: pieces cover {covered} of {area(whole)} - a difference of "
        f"{area(whole) - covered} is exactly the gap or overlap that integer "
        f"rounding leaves when sizes are rounded instead of boundaries"
    )


def groups_of(result):
    return [c for c in result["containers"] if c["kind"] == "group"]


def headers_of(result):
    return [c for c in result["containers"] if c["kind"] == "group_header"]


def tiles_in(result, group_index):
    return [i for i in result["items"] if i["group"] == group_index]


def body_of(result, group):
    """The group rect minus its header strip - what its tiles divide."""
    return {"left": group["left"], "right": group["right"],
            "top": group["top"] - result["group_header_height"],
            "bottom": group["bottom"], "id": f"body of {group['id']}"}


def build(shape="equal", counts=(3, 2, 4), spec=None, names=True,
          start_id=1000):
    """One treemap: a group per entry in `counts`, weighted by `shape`."""
    maker = WEIGHT_SHAPES[shape]
    groups = []
    next_id = start_id
    for g, n in enumerate(counts):
        weights = maker(n)
        tiles = []
        for j in range(n):
            tile = {"id": next_id, "weight": weights[j]}
            if names:
                tile["name"] = f"Tile {next_id}"
            tiles.append(tile)
            next_id += 1
        groups.append({"name": f"Group {g}", "tiles": tiles})
    return compose_treemap(groups, spec=spec)


def assert_result_sane(result, label=""):
    """Everything this grammar promises about any result at all."""
    region = result["region"]
    groups = groups_of(result)
    headers = headers_of(result)

    # Groups exactly partition the region.
    assert_partitions(groups, region, f"{label}: groups over region")

    # Every group is a header strip plus a body, sharing one edge.
    for group in groups:
        header = next(h for h in headers if h["index"] == group["index"])
        body = body_of(result, group)
        assert_partitions([header, body], group,
                          f"{label}: header+body of {group['id']}")
        assert header["top"] == group["top"]
        assert header["bottom"] == body["top"], "header and body share an edge"

        tiles = tiles_in(result, group["index"])
        assert len(tiles) == group["tiles"]
        assert_partitions(tiles, body, f"{label}: tiles of {group['id']}")
        for tile in tiles:
            assert tile["container_id"] == group["id"]
            assert contains(group, tile)
            assert not rects_overlap(header, tile), (
                f"{label}: tile {tile['id']} runs under its own header")

    # And the whole tile set partitions nothing smaller than itself: distinct
    # tiles anywhere in the drawing never overlap, across groups as well as
    # within one.
    assert_no_overlaps(result["items"], f"{label}: all tiles")
    assert_no_overlaps(groups, f"{label}: all groups")

    # The floor is a floor.
    m = result["min_tile_side"]
    for tile in result["items"]:
        assert tile["right"] - tile["left"] >= m, f"{label}: {tile['id']} thin"
        assert tile["top"] - tile["bottom"] >= m, f"{label}: {tile['id']} short"


# ---------------------------------------------------------------------------
# The coordinate convention, first, because everything else leans on it
# ---------------------------------------------------------------------------
def test_rects_are_built_in_eas_inverted_y_convention():
    result = build(counts=(2, 2))
    region = result["region"]
    assert region["top"] == DEFAULT_TREEMAP_SPEC["origin_top"] < 0
    assert region["top"] > region["bottom"], "top is above bottom, numerically"
    assert region["top"] - region["bottom"] == DEFAULT_TREEMAP_SPEC["region_height"]
    for box in [*result["containers"], *result["items"]]:
        assert box["right"] > box["left"]
        assert box["top"] > box["bottom"]


def test_a_header_sits_above_its_body_which_means_a_larger_top():
    result = build(counts=(1,))
    group = groups_of(result)[0]
    header = headers_of(result)[0]
    tile = result["items"][0]
    assert header["top"] == group["top"]
    assert tile["top"] < header["top"], "the body is below the header"
    assert header["bottom"] == tile["top"], "and they share that edge exactly"


def test_the_region_is_an_input_not_an_output():
    """Unlike every other grammar here, the extent is stated and honored.

    Area is a share, and a share needs a total. If the composition grew to fit
    its content, every tile would mean something different.
    """
    result = build(counts=(4, 4, 4), spec={"region_width": 1000,
                                           "region_height": 700})
    assert result["bounds"]["width"] == 1000
    assert result["bounds"]["height"] == 700
    assert result["region"] == {"left": 20, "top": -20, "right": 1020,
                                "bottom": -720}


# ---------------------------------------------------------------------------
# The exact partition - the defect this grammar would otherwise ship with
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("width,height", REGIONS)
@pytest.mark.parametrize("shape", sorted(WEIGHT_SHAPES))
def test_tiles_exactly_partition_every_region_and_weight_shape(width, height,
                                                               shape):
    result = build(shape=shape, counts=(3, 1, 4, 2),
                   spec={"region_width": width, "region_height": height})
    assert_result_sane(result, f"{shape} in {width}x{height}")


@pytest.mark.parametrize("n", list(range(1, 31)))
def test_tiles_exactly_partition_for_one_to_thirty_tiles(n):
    """The count is where rounding error accumulates, so sweep every one.

    A tiling that closes at three tiles and leaks one unit at seventeen is the
    failure mode; one hand-picked count would not see it.
    """
    for shape in ("equal", "descending", "dominant", "fractional"):
        result = build(shape=shape, counts=(n,),
                       spec={"region_width": 1600, "region_height": 1200})
        assert result["tiles"] == n
        assert_result_sane(result, f"{n} tiles, {shape}")


@pytest.mark.parametrize("n", list(range(1, 13)))
def test_exact_partition_holds_across_many_groups(n):
    result = build(shape="descending", counts=tuple([2] * n),
                   spec={"region_width": 1600, "region_height": 1200})
    assert result["groups"] == n
    assert result["tiles"] == 2 * n
    assert_result_sane(result, f"{n} groups")


@pytest.mark.parametrize("width", [400, 401, 617, 999, 1000, 1201, 2399])
@pytest.mark.parametrize("height", [400, 403, 750, 1000, 1337])
def test_the_partition_closes_at_awkward_region_sizes(width, height):
    """Prime-ish and odd extents, where a proportional split never lands whole.

    This is the arithmetic the module exists to get right: no size here divides
    evenly by any of the weights, so every boundary is fractional and every one
    of them has to be closed the same way on both sides.
    """
    result = build(shape="descending", counts=(3, 2),
                   spec={"region_width": width, "region_height": height})
    assert_result_sane(result, f"{width}x{height}")


def test_a_one_unit_gap_would_be_caught():
    """The partition assertion is load bearing, so prove it can fail.

    A tiling with a one-unit gap passes a no-overlap test and fails this one,
    which is exactly the discrimination the suite depends on.
    """
    whole = {"left": 0, "top": 0, "right": 100, "bottom": -100}
    good = [{"id": "a", "left": 0, "top": 0, "right": 40, "bottom": -100},
            {"id": "b", "left": 40, "top": 0, "right": 100, "bottom": -100}]
    assert_partitions(good, whole, "sanity")

    gapped = [dict(good[0]), dict(good[1])]
    gapped[0]["right"] = 39
    assert_no_overlaps(gapped, "a gap is not an overlap")
    with pytest.raises(AssertionError, match="pieces cover"):
        assert_partitions(gapped, whole, "gapped")

    overlapped = [dict(good[0]), dict(good[1])]
    overlapped[0]["right"] = 41
    with pytest.raises(AssertionError, match="overlap"):
        assert_partitions(overlapped, whole, "overlapped")


def test_tiles_abut_rather_than_leaving_a_gap():
    """There is no gap key, and this is why.

    Whitespace between tiles is area subtracted from the number the reader is
    comparing, and subtracted from small tiles proportionally more than from
    large ones. So the geometry has none, and `rects_overlap` treats the shared
    edge as no overlap.
    """
    assert "tile_gap" not in DEFAULT_TREEMAP_SPEC
    assert not any("gap" in k for k in DEFAULT_TREEMAP_SPEC)
    result = build(shape="equal", counts=(4,))
    tiles = result["items"]
    edges = {t["left"] for t in tiles} | {t["right"] for t in tiles}
    shared = [t for t in tiles if t["left"] in edges and t["right"] in edges]
    assert len(shared) == len(tiles)
    assert sum(area(t) for t in tiles) == area(body_of(result,
                                                       groups_of(result)[0]))


# ---------------------------------------------------------------------------
# Degenerate weights, each answered rather than avoided
# ---------------------------------------------------------------------------
def test_a_zero_weight_tile_is_drawn_at_the_floor_not_omitted():
    """An omitted tile is a silent lie about the data; a sliver is a loud one."""
    result = compose_treemap([{"name": "Costs", "tiles": [
        {"id": 1, "name": "Mainframe", "weight": 500},
        {"id": 2, "name": "Retired Gateway", "weight": 0},
        {"id": 3, "name": "Message Bus", "weight": 300},
    ]}])
    assert result["tiles"] == 3
    zero = next(t for t in result["items"] if t["id"] == 2)
    m = result["min_tile_side"]
    assert min(zero["right"] - zero["left"], zero["top"] - zero["bottom"]) == m
    assert result["tiles_at_min_side"] >= 1
    assert_result_sane(result, "one zero weight")


def test_every_weight_zero_divides_the_set_equally_and_says_so():
    result = compose_treemap([{"name": "Unscored", "tiles": [
        {"id": i, "weight": 0} for i in range(1, 5)]}])
    assert result["equalized_splits"] > 0, (
        "nothing here is bigger than anything else, so it divides equally - "
        "and the result has to say that happened")
    assert_result_sane(result, "all zero")
    sizes = {area(t) for t in result["items"]}
    assert max(sizes) - min(sizes) <= max(sizes) // 8, (
        "an equal division should come out near-equal, rounding aside")


def test_equal_weights_come_out_equal_to_within_the_rounding():
    result = build(shape="equal", counts=(6,),
                   spec={"region_width": 900, "region_height": 600})
    tiles = result["items"]
    assert result["equalized_splits"] == 0, "these weights are not zero"
    assert result["tile_area_error_ppm"] < 20_000, (
        f"equal weights should tile evenly, got "
        f"{result['tile_area_error_ppm']} ppm")
    assert_result_sane(result, "equal")
    assert len({t["top"] - t["bottom"] for t in tiles}) <= 3


def test_one_dominant_weight_keeps_the_rest_readable_and_reports_the_cost():
    """99% and 1% each is the normal reason someone draws a treemap.

    Refusing it would be worse than drawing it. The small tiles bottom out at
    the floor, the dominant one keeps what is left, and the reported area error
    says plainly that the picture is no longer faithful.
    """
    result = compose_treemap([{"name": "Spend", "tiles": [
        {"id": 1, "name": "Core Ledger", "weight": 9900},
        *({"id": i, "name": f"Minor {i}", "weight": 1} for i in range(2, 12)),
    ]}], spec={"region_width": 900, "region_height": 600})
    assert_result_sane(result, "dominant")
    assert result["tiles_at_min_side"] >= 5
    assert result["tile_area_error_ppm"] > 1_000, (
        "the floor moved real area onto the small tiles and the result must "
        "not claim otherwise")
    biggest = max(result["items"], key=area)
    assert biggest["id"] == 1


def test_a_negative_weight_is_refused_because_there_is_no_negative_area():
    with pytest.raises(LayoutError, match=r"groups\[0\]\.tiles\[1\]\.weight"):
        compose_treemap([{"name": "G", "tiles": [
            {"id": 1, "weight": 4}, {"id": 2, "weight": -1}]}])


@pytest.mark.parametrize("bad", [float("nan"), float("inf"), float("-inf")])
def test_a_non_finite_weight_is_refused(bad):
    with pytest.raises(LayoutError, match="finite"):
        compose_treemap([{"name": "G", "tiles": [{"id": 1, "weight": bad}]}])


def test_a_missing_weight_is_refused_and_says_what_to_use_instead():
    with pytest.raises(LayoutError, match="compose_matrix"):
        compose_treemap([{"name": "G", "tiles": [{"id": 1, "name": "X"}]}])


def test_a_boolean_weight_is_refused():
    with pytest.raises(LayoutError, match="got bool"):
        compose_treemap([{"name": "G", "tiles": [{"id": 1, "weight": True}]}])


# ---------------------------------------------------------------------------
# Area faithfulness - what the grammar claims and what it reports
# ---------------------------------------------------------------------------
def test_areas_track_the_weights_when_nothing_is_clamped():
    """The whole point, stated as a measurement rather than as a docstring."""
    weights = [40, 25, 20, 15]
    result = compose_treemap([{"name": "Portfolio", "tiles": [
        {"id": i + 1, "weight": w} for i, w in enumerate(weights)]}],
        spec={"region_width": 1600, "region_height": 1200})
    assert result["tiles_at_min_side"] == 0
    body = body_of(result, groups_of(result)[0])
    total = sum(weights)
    for tile, w in zip(sorted(result["items"], key=lambda t: t["id"]), weights):
        got = Fraction(area(tile), area(body))
        want = Fraction(w, total)
        assert abs(got - want) < Fraction(1, 100), (
            f"tile {tile['id']} has {float(got):.4f} of the body for a weight "
            f"share of {float(want):.4f}")
    assert result["tile_area_error_ppm"] < 10_000


def test_the_two_area_error_numbers_are_two_questions():
    """Headers come out of a group's allocation, so they are not one number.

    A group's rect is proportional to its weight, header included; the tiles
    then divide only the body. A short wide group loses more of its allocation
    to its header than a tall one, so tile areas are faithful WITHIN a group
    and only approximately so across groups. The result reports both rather
    than averaging them into something true of neither.
    """
    spec = {"region_width": 1400, "region_height": 900}
    result = build(shape="descending", counts=(4, 3, 2), spec=spec)
    assert set(result) >= {"group_area_error_ppm", "tile_area_error_ppm"}

    # A group's rect IS proportional to its weight, header and all, so the
    # group number stays near zero whatever the header costs.
    assert result["group_area_error_ppm"] < 10_000

    # Taller headers take real area away from the tiles, and the group rects
    # they came out of must not move to compensate: the header is spent inside
    # the group's own allocation, which is the design both reference pictures
    # use and the reason these are two numbers.
    thin = build(shape="descending", counts=(4, 3, 2),
                 spec={**spec, "group_header_height": 8})
    fat = build(shape="descending", counts=(4, 3, 2),
                spec={**spec, "group_header_height": 120})
    assert ([_span(g) for g in groups_of(thin)]
            == [_span(g) for g in groups_of(fat)]), (
        "the header comes out of the group's share, not out of its neighbors'")
    thin_body = sum(area(body_of(thin, g)) for g in groups_of(thin))
    fat_body = sum(area(body_of(fat, g)) for g in groups_of(fat))
    assert fat_body < thin_body, "a fatter header leaves the tiles less"
    assert thin_body - fat_body == sum(
        (g["right"] - g["left"]) * 112 for g in groups_of(thin)), (
        "and exactly the extra header height, times each group's width")


def test_squarifying_actually_beats_slicing_on_aspect_ratio():
    """The reference picture's worst strip runs about 0.21; ours must not.

    Squarifying is the whole reason this grammar is arithmetic rather than a
    loop, so the aspect ratio it achieves is asserted, not assumed.
    """
    result = compose_treemap([{"name": "Estate", "tiles": [
        {"id": i, "weight": w} for i, w in enumerate(
            [30, 25, 20, 12, 8, 5], start=1)]}],
        spec={"region_width": 1000, "region_height": 800})
    assert result["worst_aspect_ratio"] < 3.0, (
        f"worst tile aspect {result['worst_aspect_ratio']} - long thin tiles "
        f"are uncomparable by area, which is the only thing a treemap says")


# ---------------------------------------------------------------------------
# The minimum readable tile
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("m", [8, 24, 48, 90, 140])
def test_the_floor_is_honored_on_both_axes_at_every_setting(m):
    result = build(shape="tiny-tail", counts=(8,),
                   spec={"region_width": 1600, "region_height": 1200,
                         "min_tile_side": m})
    assert result["min_tile_side"] == m
    for tile in result["items"]:
        assert tile["right"] - tile["left"] >= m
        assert tile["top"] - tile["bottom"] >= m
    assert_result_sane(result, f"floor {m}")


def test_the_floor_is_one_number_because_orientation_is_not_known_in_advance():
    """A tile 200 wide under one set of weights is 200 tall under another.

    Which is why this is `min_tile_side` and not a width and a height: a rule
    that floored only the width would stop holding the moment the data changed.
    """
    wide = build(shape="descending", counts=(5,),
                 spec={"region_width": 2000, "region_height": 500,
                       "min_tile_side": 60})
    tall = build(shape="descending", counts=(5,),
                 spec={"region_width": 500, "region_height": 2000,
                       "min_tile_side": 60})
    for result in (wide, tall):
        for tile in result["items"]:
            assert min(tile["right"] - tile["left"],
                       tile["top"] - tile["bottom"]) >= 60


def test_a_region_too_small_for_its_tiles_is_refused_with_the_numbers():
    with pytest.raises(LayoutError) as excinfo:
        compose_treemap(
            [{"name": "G", "tiles": [{"id": i, "weight": 1}
                                     for i in range(1, 21)]}],
            spec={"region_width": 300, "region_height": 300,
                  "min_tile_side": 60})
    message = str(excinfo.value)
    assert "300x300" in message
    assert "spec.min_tile_side" in message
    assert "need 20" in message, "the demand that could not be met, in cells"
    assert "square(s) of 88 units" in message, (
        "and the capacity it was measured against - a group is tiled in cells "
        "of header plus floor, because its header comes out of its own share")


def test_the_capacity_bound_is_a_capacity_and_not_an_extent():
    """The regression that made the bound worth deriving twice.

    Ten tiles at a floor of 48 fit comfortably in 400x400: the region rules
    into 8 * 8 = 64 squares of 48. An extent bound - "the long side must reach
    10 * 48 = 480" - refuses it, and refuses a great many perfectly drawable
    treemaps with it. The capacity bound accepts it and the partition still
    closes exactly, which is the whole claim.
    """
    result = compose_treemap([{"name": "Estate", "tiles": [
        {"id": i, "weight": i} for i in range(1, 11)]}],
        spec={"region_width": 400, "region_height": 400,
              "min_tile_side": 48, "group_header_height": 20})
    assert result["tiles"] == 10
    assert (400 // 48) * (400 // 48) == 64 >= 10
    assert_result_sane(result, "capacity bound")


def test_a_tight_region_gives_up_aspect_ratio_before_it_gives_up_the_floor():
    """When the floor binds, the greedy row boundary is not always available.

    The split has to leave both sides able to hold what is in them, so a
    boundary the aspect-ratio rule preferred gets moved to the nearest one that
    can. Tiles stay at or above the floor and the partition stays exact; what
    is spent is squareness, which is the right thing to spend.
    """
    result = compose_treemap([{"name": "G", "tiles": [
        {"id": i, "weight": 1} for i in range(1, 5)]}],
        spec={"region_width": 200, "region_height": 220,
              "min_tile_side": 48, "group_header_height": 20})
    assert_result_sane(result, "tight")
    for tile in result["items"]:
        assert tile["right"] - tile["left"] >= 48
        assert tile["top"] - tile["bottom"] >= 48


def test_the_refusal_names_the_group_it_could_not_fit():
    with pytest.raises(LayoutError, match=r"groups\b"):
        compose_treemap(
            [{"name": "Big", "tiles": [{"id": i, "weight": 1}
                                       for i in range(1, 40)]},
             {"name": "Small", "tiles": [{"id": 99, "weight": 1}]}],
            spec={"region_width": 400, "region_height": 400})


def test_more_boxes_than_one_region_will_divide_is_refused():
    n = MAX_BOXES_PER_REGION + 1
    with pytest.raises(LayoutError, match=str(MAX_BOXES_PER_REGION)):
        compose_treemap(
            [{"name": "G", "tiles": [{"id": i, "weight": 1}
                                     for i in range(n)]}],
            spec={"region_width": 400_000, "region_height": 400_000,
                  "min_tile_side": 1})


# ---------------------------------------------------------------------------
# Determinism, which the exact arithmetic exists to give
# ---------------------------------------------------------------------------
def test_the_same_input_gives_the_same_output_every_time():
    first = build(shape="fractional", counts=(5, 3, 7))
    second = build(shape="fractional", counts=(5, 3, 7))
    assert first == second


def test_float_weights_do_not_drift_with_the_order_they_are_summed():
    """`0.1 + 0.2 + 0.3` is not `0.3 + 0.2 + 0.1` in floats, and it must not
    matter here: the arithmetic runs in exact Fractions, so reversing the input
    mirrors the picture rather than perturbing it.
    """
    forward = compose_treemap([{"name": "G", "tiles": [
        {"id": 1, "weight": 0.1}, {"id": 2, "weight": 0.2},
        {"id": 3, "weight": 0.3}]}])
    backward = compose_treemap([{"name": "G", "tiles": [
        {"id": 3, "weight": 0.3}, {"id": 2, "weight": 0.2},
        {"id": 1, "weight": 0.1}]}])
    by_id = {t["id"]: area(t) for t in forward["items"]}
    other = {t["id"]: area(t) for t in backward["items"]}
    assert sum(by_id.values()) == sum(other.values())
    assert forward["equalized_splits"] == backward["equalized_splits"] == 0


def test_a_fraction_weight_is_accepted_exactly():
    result = compose_treemap([{"name": "G", "tiles": [
        {"id": 1, "weight": Fraction(1, 3)},
        {"id": 2, "weight": Fraction(2, 3)}]}])
    assert_result_sane(result, "fractions")
    small, big = sorted(result["items"], key=area)
    assert area(big) > area(small)


# ---------------------------------------------------------------------------
# Validation - `where`-tagged, in the caller's own path into the input
# ---------------------------------------------------------------------------
def test_an_unknown_spec_key_is_refused_rather_than_ignored():
    with pytest.raises(LayoutError, match="minTileSide"):
        build(spec={"minTileSide": 40})


def test_a_spec_key_from_another_grammar_is_refused():
    with pytest.raises(LayoutError, match="radius"):
        build(spec={"radius": 200})


@pytest.mark.parametrize("key", sorted(
    k for k in DEFAULT_TREEMAP_SPEC if not k.startswith("origin")))
def test_every_sizing_key_must_be_positive(key):
    with pytest.raises(LayoutError, match=f"spec.{key}"):
        build(spec={key: 0})


def test_an_unknown_key_on_a_tile_is_refused():
    with pytest.raises(LayoutError, match=r"groups\[0\]\.tiles\[0\]"):
        compose_treemap([{"name": "G", "tiles": [
            {"id": 1, "weight": 2, "min_tile_side": 90}]}])


def test_an_unknown_key_on_a_group_is_refused():
    with pytest.raises(LayoutError, match=r"groups\[0\]"):
        compose_treemap([{"name": "G", "color": "red",
                          "tiles": [{"id": 1, "weight": 2}]}])


def test_an_empty_group_list_is_refused():
    with pytest.raises(LayoutError, match="empty list"):
        compose_treemap([])


def test_a_group_with_no_tiles_is_refused():
    with pytest.raises(LayoutError, match=r"groups\[0\]\.tiles"):
        compose_treemap([{"name": "G", "tiles": []}])


def test_a_group_needs_a_name():
    with pytest.raises(LayoutError, match=r"groups\[0\]\.name"):
        compose_treemap([{"tiles": [{"id": 1, "weight": 1}]}])


def test_a_tile_needs_an_id():
    with pytest.raises(LayoutError, match=r"groups\[0\]\.tiles\[0\]\.id"):
        compose_treemap([{"name": "G", "tiles": [{"weight": 1}]}])


def test_a_duplicate_id_anywhere_is_refused():
    with pytest.raises(LayoutError, match="duplicate id"):
        compose_treemap([
            {"name": "A", "tiles": [{"id": 7, "weight": 1}]},
            {"name": "B", "tiles": [{"id": 7, "weight": 1}]}])


def test_a_group_id_cannot_collide_with_a_tile_id():
    with pytest.raises(LayoutError, match="duplicate id"):
        compose_treemap([{"id": 5, "name": "A",
                          "tiles": [{"id": 5, "weight": 1}]}])


def test_a_set_of_groups_is_refused_because_order_is_an_input():
    with pytest.raises(LayoutError, match="expected a list"):
        compose_treemap({"name": "G", "tiles": []})


def test_ids_are_preserved_verbatim_in_the_callers_own_type():
    result = compose_treemap([
        {"id": 900, "header_id": 901, "name": "Numeric",
         "tiles": [{"id": 902, "weight": 1}]},
        {"id": "alpha", "header_id": "alpha-bar", "name": "Textual",
         "tiles": [{"id": "alpha-1", "weight": 1}]}])
    ids = {c["id"] for c in result["containers"]} | {
        i["id"] for i in result["items"]}
    assert ids == {900, 901, 902, "alpha", "alpha-bar", "alpha-1"}


# ---------------------------------------------------------------------------
# Labels - what this module can promise and what it cannot
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("name", ["X", "", LONG_NAME, "  spaced  out  "])
def test_a_name_of_any_length_changes_nothing_about_the_geometry(name):
    """This module cannot measure text and does not pretend to.

    A name does not resize a tile - area is the weight's to set - so the
    geometry must be identical whatever the name is, and whether a label fits
    is `lint.check_labels_fit`'s question, measured against EA's own rendered
    advance widths.
    """
    def geometry(label):
        result = compose_treemap([{"name": "Estate", "tiles": [
            {"id": 1, "name": label, "weight": 60},
            {"id": 2, "name": label, "weight": 40}]}])
        return [_span(t) for t in result["items"]]

    assert geometry(name) == geometry("baseline")


def test_a_tile_with_no_name_still_places():
    result = compose_treemap([{"name": "G", "tiles": [
        {"id": 1, "weight": 3}, {"id": 2, "name": "Named", "weight": 2}]}])
    unnamed = next(t for t in result["items"] if t["id"] == 1)
    assert "name" not in unnamed
    assert next(t for t in result["items"] if t["id"] == 2)["name"] == "Named"


def test_raising_the_floor_is_how_a_caller_buys_room_for_long_labels():
    narrow = build(shape="descending", counts=(6,),
                   spec={"region_width": 1600, "region_height": 1000,
                         "min_tile_side": 40})
    roomy = build(shape="descending", counts=(6,),
                  spec={"region_width": 1600, "region_height": 1000,
                        "min_tile_side": 200})
    narrowest = min(min(t["right"] - t["left"], t["top"] - t["bottom"])
                    for t in narrow["items"])
    roomiest = min(min(t["right"] - t["left"], t["top"] - t["bottom"])
                   for t in roomy["items"])
    assert narrowest >= 40
    assert roomiest >= 200 > narrowest, (
        "raising the floor has to actually widen the smallest tile, which is "
        "the only lever this module gives a caller with long names")
    assert roomy["tile_area_error_ppm"] > narrow["tile_area_error_ppm"], (
        "and the room is bought with area fidelity, which must be reported")


# ---------------------------------------------------------------------------
# THE SEAM: the shipped linter, run over this engine's own output
# ---------------------------------------------------------------------------
def _payload(result):
    """The result as `verify_diagram` would hand it to the linter."""
    objects = []
    for box in [*result["containers"], *result["items"]]:
        objects.append({
            "element_id": len(objects) + 1,
            "name": box.get("name") or "",
            "left": box["left"], "top": box["top"],
            "right": box["right"], "bottom": box["bottom"],
        })
    b = result["bounds"]
    return {"objects": objects, "links": [],
            "canvas": {"cx": b["width"] + 100, "cy": b["height"] + 100}}


@pytest.mark.parametrize("width,height", REGIONS)
@pytest.mark.parametrize("shape", sorted(WEIGHT_SHAPES))
@pytest.mark.parametrize("counts", [(1,), (5, 5), (9, 1, 3), (2, 2, 2, 2, 2)])
def test_the_shipped_linter_is_clean_across_content_variation(width, height,
                                                              shape, counts):
    """The linter measures the finished rectangles; this engine produces them.

    Two separate pieces of code have to agree, and a linter run on one example
    is the failure this grammar would otherwise ship with: a one-unit overlap
    appears at some sizes and not at others, so the sweep is the test.
    """
    lint = pytest.importorskip("lint")
    result = build(shape=shape, counts=counts,
                   spec={"region_width": width, "region_height": height})
    report = lint.lint_diagram(_payload(result))
    assert not report.errors, (
        f"{shape} {counts} in {width}x{height}: "
        f"{[f.message for f in report.errors]}")
    assert report.metrics["overlaps"] == 0


def test_the_linter_actually_measured_something():
    """A clean report over nothing measured is not a result.

    `overlaps` is the denominator that matters here: it is computed over every
    pair, and this grammar's whole risk is that one pair of them touches by one
    unit too many.
    """
    lint = pytest.importorskip("lint")
    result = build(shape="descending", counts=(6, 4))
    payload = _payload(result)
    report = lint.lint_diagram(payload)
    assert report.metrics["objects"] == len(payload["objects"]) == 4 + 10
    assert "overlaps" in report.metrics
    assert report.metrics["overlaps"] == 0


def test_the_linter_is_clean_with_very_long_and_very_short_names():
    lint = pytest.importorskip("lint")
    for label in ("A", LONG_NAME):
        result = compose_treemap([{"name": label, "tiles": [
            {"id": i, "name": label, "weight": i} for i in range(1, 8)]}],
            spec={"region_width": 1400, "region_height": 900})
        report = lint.lint_diagram(_payload(result))
        assert not report.errors, [f.message for f in report.errors]


def test_the_label_fit_rule_says_it_could_not_run_without_the_svg():
    """A check that quietly does nothing is worse than one that is absent.

    This module cannot measure text, so it is worth recording that the rule
    which CAN is the one that has to be run, with `include_svg=True`.
    """
    lint = pytest.importorskip("lint")
    report = lint.lint_diagram(_payload(build(counts=(4,))))
    assert any("label-fit" in note for note in report.not_run)

#!/usr/bin/env python3
"""Treemap layout: a rectangle tiled so that each tile's AREA carries a weight.

A companion to `compose.py` and held to the same rules: pure arithmetic, no
repository calls, no COM, no file or network I/O, no clock, no randomness. Same
input, same output, every time. Nothing here branches on a technology id, a
profile name or a stereotype - sizes and thicknesses arrive in a `spec` dict
supplied by the caller.

The coordinate convention is `compose.py`'s, and every rect here is built with
its `rect()` so there is one statement of it:

    left, right   positive, increasing rightward       right > left
    top, bottom   NEGATIVE, increasing upward          top > bottom
    width = right - left, height = top - bottom

WHAT THE TWO REFERENCE PICTURES ACTUALLY ARE, MEASURED
------------------------------------------------------
The catalog files both reference rows under the name "heat map", and a heat map
is normally a REGULAR grid colored by value - which would be the `matrix`
grammar's job, not this one. They are not that. Both were measured pixel by
pixel before a line of this module was written, and both are IRREGULAR tilings
whose rectangles are sized by a value:

* The technology picture tiles a region with seven groups, each carrying a dark
  title strip across its top. The groups sit in TWO ROWS of unequal height, the
  first row holding three groups of widths 917 / 518 / 223 and the second four
  of 917 / 377 / 293 / 69. Inside one group the tiles change orientation: one
  tile takes the full body height on the left while two more stack beside it on
  the right. That mixture of orientations is the signature of a SQUARIFIED
  tiling - a regular grid cannot produce it and a plain slice-and-dice never
  changes orientation. Its own legend says "Size Indicates Cost".
* The department picture is the same idea one notch simpler: three groups as
  full-height vertical strips of widths 352 / 308 / 86, each subdivided into
  horizontal bands of unequal height. Every tile there is a full-width band of
  its strip, so that one is slice-and-dice rather than squarified - and its
  narrowest strip comes out at an aspect ratio near 0.21, which is exactly the
  sliver that squarifying exists to prevent.

So: irregular, area-proportional, sized by weight. Treemaps, both of them. The
catalog's "squarified treemap arithmetic" is the right description, and this
grammar does not overlap the `matrix` grammar, which is for a regular lattice a
reader counts along and deliberately gives every cell one size.

WHAT SQUARIFIED MEANS AND WHY IT IS WORTH THE ARITHMETIC
---------------------------------------------------------
A tile 600x8 and a tile 70x69 have the same area and do not look it. Area is
only comparable by eye when the shapes being compared are roughly the same
shape, so a treemap that ignores aspect ratio encodes a number the reader
cannot read back. Squarifying (Bruls, Huizing and van Wijk) keeps every tile as
close to square as the weights allow: tiles are laid in rows across the SHORTER
side of whatever rectangle is left, a row is extended while the worst aspect
ratio in it improves, and a new row starts when extending would make it worse.

This module implements that as a recursive split rather than as a loop over
rows, because a split is what keeps the integer arithmetic exact - see below.
Splitting the LONGER side at the greedy row boundary is the same construction:
a row strip is thin along the long axis and runs across the short one, so
recursing into the strip splits it along the row, which is the row.

THE PART THAT IS ARITHMETIC AND NOT LAYOUT: CLOSING THE ROUNDING
------------------------------------------------------------------
Exact tile edges are fractional and EA geometry is integers, and the obvious
approach - compute each tile's SIZE, round it, lay them end to end - is wrong
in a way that a single example hides. Rounded sizes do not sum to the region:
the error accumulates, so the last tile either leaves a gap or runs over its
neighbor, and a one-unit overrun is a real overlap that `lint.check_no_overlaps`
will correctly report.

**Sizes are never rounded here. BOUNDARIES are, and adjacent tiles share the
same rounded boundary.** For a run of tiles along an axis of integer length
`L` with weights `w_i` summing to `W`, the boundary before tile `k` is

    b_k = floor( (w_0 + ... + w_{k-1}) * L / W )       b_0 = 0, b_n = L

computed as exact integer division of Fractions, and tile `k` occupies
`[b_k, b_{k+1}]`. Two facts follow immediately and are the whole of the
correctness argument:

* **No gap and no overlap.** `b_{k+1}` is ONE number, used as the far edge of
  tile `k` and the near edge of tile `k+1`. There is nothing for them to
  disagree about.
* **The sizes sum to `L` exactly.** They telescope: `sum (b_{k+1} - b_k)` is
  `b_n - b_0 = L`. Not approximately, at every `L` and every weight.

Every split in this module - region into groups, group into header and body,
body into tiles, and each recursive sub-split - goes through that one helper,
so the property is inherited: at any split the two sides are separated by a
single shared coordinate, and by induction the tiles exactly partition the
region. `floor` rather than `round` because `floor` on integers is exact and
identical on every machine, while `round` would need a float and would put a
boundary in a different place on a different build.

THE CLEARANCE CONDITION, WHICH IS NOT A DISTANCE AT ALL
--------------------------------------------------------
`compose_radial` once used `max(w, h)` for a clearance where the condition that
rules out an overlap between two boxes is `hypot(w, h)`; the matrix grammar
established that on an axis-aligned lattice `hypot` is in turn the wrong
quantity, because a per-axis condition there is exact. Neither is the answer
here, and the lesson is that the condition has to be derived from the
construction rather than borrowed from another one.

Nothing in this module is PLACED, so there is no distance to be big enough.
Tiles are PARTITIONED: at every split the boxes on one side of the boundary go
into one sub-rect and the boxes on the other side into the other, the two
sub-rects meet along a single shared coordinate, and `rects_overlap` treats a
shared edge as no overlap because it compares with strict inequalities. Two
distinct tiles are separated at the first split that put them on opposite
sides. The condition is combinatorial - interval disjointness on one axis - and
it is exact with no margin, no clearance term and no trigonometry.

WHICH IS ALSO WHY THERE IS NO GAP BETWEEN TILES
-------------------------------------------------
`compose_matrix` REQUIRES a positive gap: there the address is the information
and two cells that touch cannot be told apart. Here the AREA is the
information, and whitespace between tiles is area subtracted from a value the
reader is being asked to compare. A treemap with gaps encodes a quantity and
then silently taxes it, by more for small tiles than for large ones. So tiles
abut exactly, and telling one from the next is the renderer's border - both
reference pictures draw a hairline - not a hole in the geometry. There is no
gap key in the spec and adding one would be a design error.

DEGENERATE WEIGHTS, ANSWERED RATHER THAN AVOIDED
--------------------------------------------------
* **Equal weights** tile evenly; rounding leaves neighbors differing by at most
  one unit, and the partition is still exact.
* **A zero weight** is legal and the tile is still DRAWN. Its exact size is
  zero, `rect()` refuses a zero-size rect, and an omitted tile would be a
  silent lie about the data - so the minimum-size clamp gives it exactly
  `min_tile_side`. Its area no longer matches its weight, which is what
  `tiles_at_min_side` and the two `*_area_error_ppm` numbers on the result are
  for.
* **Every weight zero** in one sibling set divides that set equally, since
  nothing there is bigger than anything else, and `equalized_splits` counts it.
* **One weight at 99%** is the case the clamp exists for: the small tiles bottom
  out at `min_tile_side` and the dominant tile keeps what is left, so the
  picture stays readable while the reported area error says plainly that it is
  no longer faithful. Refusing would be worse - that shape of data is the
  normal reason someone draws a treemap.
* **A negative weight** is refused. There is no negative area.

THE MINIMUM READABLE TILE
--------------------------
`min_tile_side` is a floor on BOTH axes, and it is one number rather than a
width and a height on purpose: which axis a tile is long on is decided by the
weights, so a tile that is 200 wide under one set of weights is 200 tall under
another, and a rule that floors only the width would not survive the data
changing. A caller whose labels need 140 units of width sets `min_tile_side` to
140 and accepts squarer tiles; this module cannot measure text, and
`lint.check_labels_fit` - which measures EA's own rendered advance widths - is
where a label that still does not fit gets caught.

The floor is what makes the layout refusable rather than silently unreadable.
The construction preserves this invariant on every sub-rect it creates:

    min(width, height) >= cell
    (width // cell) * (height // cell) >= the cells the boxes in it need

which is checked at entry and is why no sub-rect can ever come out too small
for what it has to hold. It is a CAPACITY - how many `cell`-sized squares the
rectangle rules into - and not an extent, which matters: the obvious extent
bound, "the long side must exceed `count * floor`", refuses a 400x400 region
holding ten tiles at a floor of 48 although it rules into sixty-four squares.
`_tile_region` carries the preservation argument. When the region genuinely
cannot hold what it is given, the error states the capacity, the demand and the
three things that would fix it.

Result shape
------------
    {
      "grammar":    "treemap",
      "items":      [ {"id", "name"?, "container_id", "group", "group_key",
                       "index", "weight", "left", "top", "right", "bottom"} ],
      "containers": [ {"id", "name", "kind", "index", "key", "weight",
                       "tiles", "left", "top", "right", "bottom"} ],
      "region":     the rect actually tiled,
      "groups", "tiles":            how many of each
      "min_tile_side":              the floor that was in force
      "tiles_at_min_side":          tiles measuring the floor on one axis or
                                    both - measured from the output rects, not
                                    from whether a clamp fired
      "equalized_splits":           splits whose weights were all zero and were
                                    therefore divided equally
      "group_area_error_ppm":       worst group's area share against its weight
                                    share, in parts per million
      "tile_area_error_ppm":        worst tile's area share of its group's BODY
                                    against its weight share of its group
      "worst_aspect_ratio":         the least square tile actually produced,
                                    long side over short side, a diagnostic
      "bounds":     {"left", "top", "right", "bottom", "width", "height"},
    }

`kind` is "group" or "group_header". A group container is the WHOLE group rect,
header included, so its tiles are nested inside it - which is also what earns
them `lint.check_no_overlaps`'s containment exemption. Test the group rects for
mutual disjointness, and the tiles for mutual disjointness, SEPARATELY.

`group_area_error_ppm` and `tile_area_error_ppm` are two numbers rather than
one because the header strips make them two questions. A group's rect is
proportional to its weight, header included; the tiles then divide only the
BODY. A short wide group loses a larger fraction of its allocation to its
header than a tall one does, so tile areas are faithful WITHIN a group and only
approximately so across groups. Both reference pictures take the header out of
the group's box in exactly this way; the numbers say how much it cost.
"""
from __future__ import annotations

import sys
from collections.abc import Mapping, Sequence
from fractions import Fraction
from math import isfinite
from pathlib import Path
from typing import Any, Optional

_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

from compose import LayoutError, bounding_box, rect  # noqa: E402

__all__ = [
    "DEFAULT_TREEMAP_SPEC",
    "MAX_BOXES_PER_REGION",
    "compose_treemap",
]


# ---------------------------------------------------------------------------
# Defaults
# ---------------------------------------------------------------------------
# EA diagram units, which for practical purposes are pixels at 100% zoom.
# Stated here rather than imported from `compose.DEFAULT_SPEC` so that this
# module can be read, and its arithmetic checked, without holding a second file
# open - and so that a key this grammar does not have (a gap, a wrap width, a
# radius) cannot be passed to it and silently ignored.
DEFAULT_TREEMAP_SPEC: dict[str, Any] = {
    # Top-left of the region that gets tiled. `origin_top` is negative because
    # EA's vertical axis is.
    "origin_left": 20,
    "origin_top": -20,

    # The region. Unlike every other grammar here, a treemap's extent is an
    # INPUT rather than an output: area means nothing without a total to be a
    # share of, so the caller states the rectangle and the weights divide it.
    "region_width": 1200,
    "region_height": 800,

    # The title strip across the top of each group, which both reference
    # pictures draw. Taken out of the group's own allocation, so it is area the
    # group's tiles do not get - see the note on the two error numbers.
    "group_header_height": 28,

    # The smallest tile worth drawing, on BOTH axes. A tile below this is not a
    # small tile, it is a sliver with a name printed over the tiles either side
    # of it, and a reader is better served by a tile at the floor plus a stated
    # area error than by a sliver that lies about being readable.
    "min_tile_side": 48,
}

_ANY_INT_KEYS = frozenset({"origin_left", "origin_top"})
_POSITIVE_KEYS = frozenset({
    "region_width", "region_height", "group_header_height", "min_tile_side",
})

# Keys that may appear on a group or a tile. Anything else is refused rather
# than ignored, so a spec key written on a group - `min_tile_side` on the group
# with the small tiles - is a named error and not an afternoon spent wondering
# why the sizing had no effect.
_GROUP_KEYS = frozenset({"id", "name", "header_id", "tiles"})
_TILE_KEYS = frozenset({"id", "name", "weight"})

# How many boxes one region may divide. The recursion peels one box at a time
# in the worst case - which is exactly what a single dominant weight produces -
# so the depth is linear in the count, and an unbounded count would trade a
# clear refusal for a RecursionError from somewhere inside the arithmetic.
# Well above anything a treemap can usefully show: past a few dozen tiles the
# labels have long since stopped fitting.
MAX_BOXES_PER_REGION = 200


# ---------------------------------------------------------------------------
# Validation - the same shapes and the same `where`-tagged messages as
# `compose.py`, restated here so this module stands on its own.
# ---------------------------------------------------------------------------
def _as_int(value: Any, where: str) -> int:
    """Coerce a number to a whole EA unit, rejecting anything that is not one.

    bool is rejected on purpose: True would otherwise sail through as 1 and
    produce geometry nobody asked for.
    """
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise LayoutError(f"{where}: expected a number, got {type(value).__name__}")
    return int(round(value))


def _as_weight(value: Any, where: str) -> Fraction:
    """Coerce a weight to an exact Fraction, rejecting anything that is not one.

    EXACT, not float. Every comparison the squarifier makes and every boundary
    it rounds runs through these numbers, and a float sum is
    order-dependent - `0.1 + 0.2 + 0.3` is not `0.3 + 0.2 + 0.1` - which would
    make the same input tile differently depending on how the caller happened to
    order it. `Fraction` from a float is the float's exact binary value, so
    nothing is invented and nothing drifts.

    bool is rejected for the same reason `_as_int` rejects it.
    """
    if isinstance(value, bool):
        raise LayoutError(f"{where}: expected a number, got bool")
    if isinstance(value, Fraction):
        w = value
    elif isinstance(value, int):
        w = Fraction(value)
    elif isinstance(value, float):
        if not isfinite(value):
            raise LayoutError(
                f"{where}: a weight must be a finite number, got {value!r}"
            )
        w = Fraction(value)
    else:
        raise LayoutError(
            f"{where}: expected a number, got {type(value).__name__}"
        )
    if w < 0:
        raise LayoutError(
            f"{where}: a weight must not be negative, got {value!r}; area "
            f"encodes this number and there is no negative area"
        )
    return w


def _require_mapping(value: Any, where: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise LayoutError(f"{where}: expected a dict, got {type(value).__name__}")
    return value


def _require_list(value: Any, where: str) -> list[Any]:
    """Accept any ordered sequence except a string, and keep the caller's order.

    Order is an input here: the squarifier walks the boxes in the order given
    and a run of similar weights tiles better when it arrives together, so a set
    or a bare dict is rejected rather than quietly iterated in whatever order it
    happens to have.
    """
    if isinstance(value, (str, bytes)) or not isinstance(value, Sequence):
        raise LayoutError(f"{where}: expected a list, got {type(value).__name__}")
    return list(value)


def _named(holder: Mapping[str, Any], where: str) -> str:
    name = holder.get("name")
    if not isinstance(name, str) or not name.strip():
        raise LayoutError(
            f"{where}.name: a non-empty string name is required, got {name!r}"
        )
    return name


def _only_keys(holder: Mapping[str, Any], allowed: frozenset[str],
               where: str) -> None:
    unknown = sorted(str(k) for k in holder if k not in allowed)
    if unknown:
        raise LayoutError(
            f"{where}: unknown key(s) {', '.join(repr(k) for k in unknown)}; "
            f"valid keys here are {', '.join(sorted(allowed))}. Sizing is "
            f"stated in the spec and applies to the whole treemap, because a "
            f"tile whose floor differs from its neighbor's encodes its weight "
            f"on a different scale"
        )


def _resolve_spec(spec: Mapping[str, Any] | None) -> dict[str, Any]:
    """Validate a caller spec and fill in the defaults it left out.

    Unknown keys are an error. A typo like `minTileSide`, or a key borrowed from
    another grammar, would otherwise be ignored in silence.
    """
    out = dict(DEFAULT_TREEMAP_SPEC)
    if spec is None:
        return out
    spec = _require_mapping(spec, "spec")

    unknown = sorted(str(k) for k in spec if k not in DEFAULT_TREEMAP_SPEC)
    if unknown:
        raise LayoutError(
            f"spec: unknown key(s) {', '.join(repr(k) for k in unknown)}; "
            f"valid keys are {', '.join(sorted(DEFAULT_TREEMAP_SPEC))}"
        )

    for key, value in spec.items():
        where = f"spec.{key}"
        if key in _ANY_INT_KEYS:
            out[key] = _as_int(value, where)
        elif key in _POSITIVE_KEYS:
            n = _as_int(value, where)
            if n <= 0:
                raise LayoutError(f"{where}: must be positive, got {n}")
            out[key] = n
        else:  # pragma: no cover - only reachable if a default loses its class
            raise LayoutError(f"{where}: no validation rule for this key")
    return out


def _check_id(value: Any, where: str, seen: dict[Any, str], what: str) -> Any:
    """Claim one id, in whatever type the caller stated it.

    Ids are preserved VERBATIM - ints as ints, strings as strings - because the
    primary consumer maps them back onto EA element ids, which are integers. One
    registry serves tiles, groups and headers: all three are mapped back onto
    model elements, so one id cannot mean two of them.
    """
    if value is None or (isinstance(value, str) and not value.strip()):
        raise LayoutError(
            f"{where}: every {what} needs a non-empty id, got {value!r}"
        )
    try:
        hash(value)
    except TypeError:
        raise LayoutError(
            f"{where}: an id must be hashable so it can be checked for "
            f"uniqueness, got {type(value).__name__}"
        ) from None
    if value in seen:
        raise LayoutError(
            f"{where}: duplicate id {value!r}, already used at {seen[value]}"
        )
    seen[value] = where
    return value


# ---------------------------------------------------------------------------
# The one-dimensional partition - where the rounding is closed
# ---------------------------------------------------------------------------
class _State:
    """What the recursion accumulates besides rects."""

    __slots__ = ("placements", "equalized_splits")

    def __init__(self) -> None:
        self.placements: list[tuple[Any, tuple[int, int, int, int]]] = []
        self.equalized_splits = 0


def _partition(length: int, weights: Sequence[Fraction], needs: Sequence[int],
               state: _State) -> list[int]:
    """Split `[0, length]` into `len(weights)` pieces, exactly and in integers.

    Returns the `n + 1` BOUNDARIES, not the sizes, because the boundary is the
    thing that must be shared: piece `k` runs from `cuts[k]` to `cuts[k + 1]`,
    and `cuts[k + 1]` is one number used by piece `k` and piece `k + 1` alike.
    Sizes are never computed and rounded, so they cannot fail to sum: they
    telescope to `cuts[n] - cuts[0] = length`.

    Three passes, and each one preserves what the one before it established.

    1. **Exact cumulative boundaries.** `cuts[k] = floor(C_k * length / W)`
       where `C_k` is the sum of the first `k` weights and `W` the total, done
       as integer division of a Fraction so the answer is the same on every
       machine. `cuts[0]` is 0 and `cuts[n]` is `length` by definition, not by
       arithmetic. A total of zero divides the length equally by index instead -
       see the module docstring on all-zero weights - and is counted.
    2. **Forward clamp**, `cuts[k] = max(cuts[k], cuts[k-1] + needs[k-1])`, which
       makes every piece at least its minimum but may push `cuts[n]` past
       `length`.
    3. **Backward clamp** from `cuts[n] = length` down,
       `cuts[k] = min(cuts[k], cuts[k+1] - needs[k])`.

    That the third pass does not undo the second is the only thing here worth
    proving. After pass 2, `cuts[k] >= sum(needs[:k])`. Pass 2 only raises and
    pass 3 only lowers, so take pass 3 downward from `cuts[n] = length >=
    sum(needs)`: if `cuts[k+1] >= sum(needs[:k+1])` then both candidates for
    `cuts[k]` are at least `sum(needs[:k])`, so `cuts[k] >= sum(needs[:k])` too.
    Meanwhile pass 3 DEFINES `cuts[k] <= cuts[k+1] - needs[k]`, which is the
    minimum-size property stated the other way round, and `cuts[1] >= needs[0]`
    covers the first piece against the fixed `cuts[0] = 0`. So every piece ends
    up at least its minimum, the boundaries stay non-decreasing, and the first
    and last are still exactly 0 and `length`.

    The caller must have established `sum(needs) <= length`; `_tile_region`
    checks that as the region invariant before it gets here.
    """
    n = len(weights)
    cuts = [0] * (n + 1)
    cuts[n] = length

    total = sum(weights, Fraction(0))
    if total == 0:
        state.equalized_splits += 1
        for k in range(1, n):
            cuts[k] = (k * length) // n
    else:
        acc = Fraction(0)
        for k in range(1, n):
            acc += weights[k - 1]
            share = acc / total
            # Integer floor of `share * length`, with no float anywhere in it.
            cuts[k] = (share.numerator * length) // share.denominator

    for k in range(1, n + 1):
        floor_here = cuts[k - 1] + needs[k - 1]
        if cuts[k] < floor_here:
            cuts[k] = floor_here

    cuts[n] = length
    for k in range(n - 1, 0, -1):
        ceiling_here = cuts[k + 1] - needs[k]
        if cuts[k] > ceiling_here:
            cuts[k] = ceiling_here
    return cuts


# ---------------------------------------------------------------------------
# Squarification
# ---------------------------------------------------------------------------
# The worst aspect ratio in a row, as a comparable value. Infinity is a real
# answer - a zero-weight box has zero area and unbounded aspect - so it is
# carried as a sentinel rather than as a float `inf`, keeping every comparison
# exact integer arithmetic on Fractions.
_FINITE = 0
_INFINITE = 1


def _worst(areas: Sequence[Fraction], short: int) -> tuple[int, Fraction]:
    """Worst aspect ratio among `areas` laid as one row across a side `short`.

    A row whose areas sum to `s` laid across a side of length `short` is
    `s / short` thick, and the box of area `a` in it is `a * short / s` long, so
    its aspect ratio is the larger of `short^2 * a / s^2` and its reciprocal.
    The worst in the row is therefore the larger of the FIRST expression at the
    largest area and the SECOND at the smallest - the standard Bruls, Huizing
    and van Wijk formulation, in Fractions so that two rows are never ordered
    differently on two machines.

    An empty or zero area makes the ratio unbounded, reported as `_INFINITE`.
    Comparing the returned tuples orders finite before infinite and two
    infinities equal, which is what the greedy rule wants: a run of zero-weight
    boxes stays together in one row instead of each starting a new one.
    """
    s = sum(areas, Fraction(0))
    if s == 0:
        return (_INFINITE, Fraction(0))
    a_min = min(areas)
    if a_min == 0:
        return (_INFINITE, Fraction(0))
    a_max = max(areas)
    short_sq = Fraction(short * short)
    return (_FINITE, max(short_sq * a_max / (s * s), (s * s) / (short_sq * a_min)))


def _greedy_row(areas: Sequence[Fraction], short: int) -> int:
    """How many boxes belong in the row that starts at index 0.

    Bruls, Huizing and van Wijk's rule verbatim: extend the row while the worst
    aspect ratio in it does not get worse, and stop at the first box that would
    make it worse. Never returns 0 - a row of nothing makes no progress and the
    recursion would not terminate.
    """
    n = len(areas)
    k = 1
    current = _worst(areas[:1], short)
    while k < n:
        nxt = _worst(areas[:k + 1], short)
        if nxt > current:
            break
        current = nxt
        k += 1
    return k


def _ceil_div(n: int, d: int) -> int:
    return -(-n // d)


def _tile_region(left: int, top: int, width: int, height: int,
                 boxes: Sequence[dict[str, Any]], cell: int,
                 state: _State, where: str) -> None:
    """Tile one rectangle with `boxes`, recursively, exactly.

    Each box carries a `weight` (Fraction) and `cells` - how many `cell`-sized
    squares it needs room for, one for a tile and one per tile for a group.

    THE REGION INVARIANT, which is a CAPACITY and not an extent:

        min(width, height) >= cell
        (width // cell) * (height // cell) >= sum of the boxes' cell demands

    It counts how many `cell`-sized squares the rectangle can be ruled into,
    which is the honest question - "can 10 tiles fit in 400x400 at a floor of
    48" is answered by 8 * 8 = 64 cells, not by whether 400 exceeds 10 * 48. An
    earlier draft used the extent bound and refused exactly that region, which
    is how the difference was found: the extent bound is the capacity bound for
    a single row and silently assumes the layout it is meant to be testing.

    It is checked at every entry, so a violation is a named error rather than a
    zero-size rect three levels down, and the construction preserves it, so the
    check at the top is the one that matters:

    * Splitting the LONG axis leaves the short side whole, so `min(...) >= cell`
      survives as long as each cut is at least one cell, which it is.
    * With `q = short // cell` cells across the short side, a piece taking `c`
      cell demands needs `ceil(c / q)` rows of cells, so it is clamped to at
      least `ceil(c / q) * cell` along the long axis. Its own capacity is then
      `(cut // cell) * q >= ceil(c / q) * q >= c`. The invariant is back.

    A split is only made where both sides can be clamped that way at once, and
    when the greedy row boundary cannot be, the nearest boundary that can is
    used instead. For boxes of ONE cell each - every tile - `k = min(q, n - 1)`
    always satisfies it, so the tile level can never run out of boundaries to
    try. For boxes of differing demands - the groups - the search is exhaustive,
    so a refusal means no split of that rectangle works under the floor in
    force, rather than that this function did not look.

    The split axis is the LONGER side, with a square region broken toward a
    horizontal split. That is the squarified construction rewritten as a
    recursion: a greedy row is thin along the long axis and runs across the
    short one, so recursing into the strip splits it along the row.
    """
    n = len(boxes)
    if n > MAX_BOXES_PER_REGION:
        raise LayoutError(
            f"{where}: {n} boxes in one region is more than the "
            f"{MAX_BOXES_PER_REGION} this grammar will divide; a treemap past a "
            f"few dozen tiles has stopped being readable - group them, or "
            f"aggregate the tail into one tile and say so on its name"
        )
    demand = sum(b["cells"] for b in boxes)
    if min(width, height) < cell:
        raise LayoutError(
            f"{where}: this region is {width}x{height} and neither side may be "
            f"under {cell}; every box here has to fit a {cell}-unit floor "
            f"whichever way round it lands"
        )
    capacity = (width // cell) * (height // cell)
    if capacity < demand:
        raise LayoutError(
            f"{where}: this region is {width}x{height}, which rules into "
            f"{capacity} square(s) of {cell} units, and {n} box(es) here need "
            f"{demand}; widen the region, raise this part's share of it, or "
            f"lower spec.min_tile_side"
        )

    if n == 1:
        state.placements.append((boxes[0]["ref"], (left, top, width, height)))
        return

    horizontal = width >= height
    long_len = width if horizontal else height
    short_len = height if horizontal else width
    across = short_len // cell          # cells fitting across the short side
    along = long_len // cell            # cells fitting along the long one

    area = Fraction(width * height)
    total_weight = sum((b["weight"] for b in boxes), Fraction(0))
    if total_weight == 0:
        areas = [Fraction(0)] * n
    else:
        areas = [b["weight"] * area / total_weight for b in boxes]

    k = _greedy_row(areas, short_len)

    if k >= n:
        # Every box belongs in one row: they span the long axis and divide the
        # short one. Available only when the SHORT axis can carry them all - the
        # invariant is about capacity, which says nothing about one axis on its
        # own - so fall back to a binary split when it cannot.
        rows = [_ceil_div(b["cells"], along) for b in boxes]
        if sum(rows) * cell <= short_len:
            cuts = _partition(short_len, [b["weight"] for b in boxes],
                              [r * cell for r in rows], state)
            for i, box in enumerate(boxes):
                extent = cuts[i + 1] - cuts[i]
                if horizontal:
                    _tile_region(left, top - cuts[i], width, extent,
                                 [box], cell, state, f"{where}[{i}]")
                else:
                    _tile_region(left + cuts[i], top, extent, height,
                                 [box], cell, state, f"{where}[{i}]")
            return
        k = n - 1

    cumulative = [0]
    for b in boxes:
        cumulative.append(cumulative[-1] + b["cells"])

    def _rows_for(split: int) -> tuple[int, int]:
        return (_ceil_div(cumulative[split], across),
                _ceil_div(demand - cumulative[split], across))

    def _fits(split: int) -> bool:
        head_rows, tail_rows = _rows_for(split)
        return (head_rows + tail_rows) * cell <= long_len

    if not _fits(k):
        # The greedy boundary would need one more row of cells than this
        # rectangle has. Walk outward to the nearest boundary that does not -
        # nearest, so the aspect ratio the greedy rule was protecting is given
        # up by as little as possible.
        k = next((cand for step in range(1, n)
                  for cand in (k - step, k + step)
                  if 1 <= cand <= n - 1 and _fits(cand)), 0)
        if not k:
            raise LayoutError(
                f"{where}: no way to divide this {width}x{height} region "
                f"between {n} box(es) leaves every part able to hold what is "
                f"in it at a floor of {cell}; widen the region or lower "
                f"spec.min_tile_side"
            )

    head_rows, tail_rows = _rows_for(k)
    head, tail = boxes[:k], boxes[k:]
    cuts = _partition(
        long_len,
        [sum((b["weight"] for b in head), Fraction(0)),
         sum((b["weight"] for b in tail), Fraction(0))],
        [head_rows * cell, tail_rows * cell],
        state,
    )
    first, second = cuts[1], long_len - cuts[1]
    if horizontal:
        _tile_region(left, top, first, height, head, cell, state, f"{where}<")
        _tile_region(left + first, top, second, height, tail, cell, state,
                     f"{where}>")
    else:
        _tile_region(left, top, width, first, head, cell, state, f"{where}^")
        _tile_region(left, top - first, width, second, tail, cell, state,
                     f"{where}v")


# ---------------------------------------------------------------------------
# Reporting - what it actually did
# ---------------------------------------------------------------------------
def _ppm(actual: Fraction, expected: Fraction) -> int:
    """`|actual - expected|` as parts per million, rounded away from zero.

    Both arguments are shares in `[0, 1]`, so the answer is an honest "this
    tile's area is off by N millionths of the whole". Rounded UP so that a real
    but tiny discrepancy never reports as a clean zero.
    """
    diff = abs(actual - expected) * 1_000_000
    return -((-diff.numerator) // diff.denominator)


def _aspect(width: int, height: int) -> Fraction:
    return (Fraction(width, height) if width >= height
            else Fraction(height, width))


# ---------------------------------------------------------------------------
# The grammar
# ---------------------------------------------------------------------------
def compose_treemap(
    groups: Sequence[Mapping[str, Any]],
    spec: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Tile a rectangle so that each tile's area is proportional to its weight.

    `groups` is an ordered list; each group has a `name`, an optional `id` and
    `header_id`, and a non-empty list of `tiles`, each with an `id`, an optional
    `name` and a `weight`:

        compose_treemap(
            groups=[
                {"name": "Operations", "tiles": [
                    {"id": 101, "name": "Enterprise Manager", "weight": 48},
                    {"id": 102, "name": "Third Party Tools", "weight": 31},
                    {"id": 103, "name": "Console", "weight": 17},
                ]},
                {"name": "Database", "tiles": [
                    {"id": 104, "name": "Ledger Store", "weight": 40},
                    {"id": 105, "name": "Reporting Store", "weight": 12},
                ]},
            ],
            spec={"region_width": 1200, "region_height": 800},
        )

    A group's weight is the sum of its tiles', so a caller states the numbers
    once and the two levels cannot disagree. Groups divide the region; each
    group keeps a title strip across its top and its tiles divide what is left.
    A single group is a flat treemap with a title on it, which is the ordinary
    way to ask for one.

    The four questions this grammar has to answer, and the answers it gives:

    * **The region is an INPUT, not an output.** Every other grammar here grows
      to fit its content. Area is a SHARE, and a share needs a total, so the
      rectangle being divided is stated in the spec - `region_width`,
      `region_height` - and the weights divide exactly that. A treemap that
      resized itself would change what every tile means.
    * **Tiles ABUT; there is no gap key.** Whitespace between tiles is area
      taken away from a number the reader is being asked to compare, and taken
      away from small tiles proportionally more than from large ones. The
      renderer draws the border, as both reference pictures do. This is the
      exact reverse of `compose_matrix`, which requires a positive gap because
      there the address is the information and two touching cells cannot be told
      apart; the module docstring sets the two side by side.
    * **Rounding is closed on BOUNDARIES, never on sizes.** Adjacent tiles share
      one rounded coordinate, so the tiling has no gaps, no overlaps and sums to
      the region exactly at every size and every set of weights. `_partition`
      carries the argument.
    * **A tile below `min_tile_side` is raised to it rather than dropped.** An
      omitted tile is a silent lie about the data and a sliver is an unreadable
      one. The tile is drawn at the floor and the result reports the cost:
      `tiles_at_min_side`, `group_area_error_ppm` and `tile_area_error_ppm`.

    THE CLEARANCE CONDITION, DERIVED RATHER THAN BORROWED
    ------------------------------------------------------
    There isn't one, and that is the finding rather than an omission. Nothing
    here is placed at a distance from anything else: every tile comes out of a
    PARTITION, where at each split the boxes on one side go into one sub-rect,
    the boxes on the other into the other, and the two meet along a single
    shared integer coordinate. `rects_overlap` compares with strict
    inequalities, so a shared edge is not an overlap. Two distinct tiles are
    separated by the first split that put them on opposite sides, and that is an
    interval-disjointness argument on one axis - exact, with no margin, no
    `max(w, h)` and no `hypot(w, h)`. Deriving the condition from the
    construction is the point; neither of the quantities that were right for
    another grammar is right for this one.

    WHAT THIS DELIBERATELY IS NOT
    ------------------------------
    There is no third level: groups and tiles, and a deeper hierarchy would need
    a header per level, at which point the headers cost more area than the
    tiles they annotate carry information. There is no color - which value maps
    to which shade is a binding question, and this module answers no binding
    questions; both reference pictures color by a second variable and legend it,
    and `lint.check_color_is_explained` is what holds a caller to that. And
    there are no connectors: a treemap is read by area and adjacency, and a line
    across it would be read as a boundary.

    Returns the result dict described in the module docstring - including what
    it actually did, since the floor and the rounding both move tiles off their
    exact areas. Raises `LayoutError` for any input that cannot yield sane
    geometry.
    """
    s = _resolve_spec(spec)
    header_h = s["group_header_height"]
    min_side = s["min_tile_side"]

    raw_groups = _require_list(groups, "groups")
    if not raw_groups:
        raise LayoutError(
            "groups: at least one group is required, got an empty list; a "
            "treemap of nothing has no total to take a share of"
        )

    seen_ids: dict[Any, str] = {}
    plans: list[dict[str, Any]] = []
    for i, raw_group in enumerate(raw_groups):
        gwhere = f"groups[{i}]"
        group = _require_mapping(raw_group, gwhere)
        _only_keys(group, _GROUP_KEYS, gwhere)
        name = _named(group, gwhere)
        raw_tiles = _require_list(group.get("tiles", []), f"{gwhere}.tiles")
        if not raw_tiles:
            raise LayoutError(
                f"{gwhere}.tiles: a group needs at least one tile; an empty "
                f"group would be a title strip over a blank rectangle whose "
                f"area still claims a share of the region"
            )
        group_id = group["id"] if "id" in group else f"group_{i}"
        _check_id(group_id, f"{gwhere}.id", seen_ids, "group")
        header_id = (group["header_id"] if "header_id" in group
                     else f"group_{i}_header")
        _check_id(header_id, f"{gwhere}.header_id", seen_ids, "group header")

        tiles: list[dict[str, Any]] = []
        for j, raw_tile in enumerate(raw_tiles):
            twhere = f"{gwhere}.tiles[{j}]"
            tile = _require_mapping(raw_tile, twhere)
            _only_keys(tile, _TILE_KEYS, twhere)
            _check_id(tile.get("id"), f"{twhere}.id", seen_ids, "tile")
            if "weight" not in tile:
                raise LayoutError(
                    f"{twhere}.weight: every tile needs a weight; area is what "
                    f"this grammar encodes, and a tiling of unweighted boxes is "
                    f"a grid - see compose_matrix"
                )
            tiles.append({
                "tile": tile,
                "weight": _as_weight(tile["weight"], f"{twhere}.weight"),
                "index": j,
            })
        plans.append({
            "name": name, "id": group_id, "header_id": header_id,
            "tiles": tiles, "index": i,
            # A group's weight is its tiles' weights summed, never stated
            # separately, so the two levels of the picture cannot disagree
            # about the same number.
            "weight": sum((t["weight"] for t in tiles), Fraction(0)),
        })

    # ---- groups divide the region -------------------------------------------
    # Groups are tiled in cells of `header_h + min_side`, one cell per tile the
    # group holds, and that is what makes the group split answer for the tile
    # splits that follow it. A group rect `W x H` that survives the invariant
    # has `min(W, H) >= header_h + min_side` and `(W // c) * (H // c) >= t`
    # cells; its BODY, `W x (H - header_h)`, then satisfies the tile invariant
    # at a floor of `min_side` without a second check. Both sides of the body
    # clear `min_side` outright, and its capacity in the smaller cell is at
    # least the group's in the larger one, because `H - header_h >= r * min_side`
    # whenever `H >= r * (min_side + header_h)`.
    group_cell = header_h + min_side
    group_boxes = [{
        "weight": p["weight"],
        "cells": len(p["tiles"]),
        "ref": p["index"],
    } for p in plans]

    state = _State()
    _tile_region(s["origin_left"], s["origin_top"],
                 s["region_width"], s["region_height"],
                 group_boxes, group_cell, state, "groups")
    group_rects = dict(state.placements)

    containers: list[dict[str, Any]] = []
    out_items: list[dict[str, Any]] = []
    region_area = Fraction(s["region_width"] * s["region_height"])
    total_weight = sum((p["weight"] for p in plans), Fraction(0))
    equal_groups = Fraction(1, len(plans))
    group_error = 0
    tile_error = 0
    worst_aspect = Fraction(1)
    at_floor = 0

    for p in plans:
        g_left, g_top, g_width, g_height = group_rects[p["index"]]
        containers.append({
            "id": p["id"],
            "name": p["name"],
            "kind": "group",
            "index": p["index"],
            "key": p["id"],
            "weight": float(p["weight"]),
            "tiles": len(p["tiles"]),
            **rect(g_left, g_top, g_width, g_height),
        })
        containers.append({
            "id": p["header_id"],
            "name": p["name"],
            "kind": "group_header",
            "index": p["index"],
            "key": p["id"],
            "weight": float(p["weight"]),
            "tiles": len(p["tiles"]),
            **rect(g_left, g_top, g_width, header_h),
        })

        # A group's area share against its weight share. Measured on the WHOLE
        # group rect, header included, because that is what the group-level
        # split allocated.
        want = (equal_groups if total_weight == 0
                else p["weight"] / total_weight)
        group_error = max(group_error,
                          _ppm(Fraction(g_width * g_height) / region_area, want))

        # The body: the group rect minus its header, sharing the header's lower
        # edge exactly, so the two partition the group rect.
        body_top = g_top - header_h
        body_height = g_height - header_h
        body_area = Fraction(g_width * body_height)

        tile_state = _State()
        tile_boxes = [{"weight": t["weight"], "cells": 1,
                       "ref": t["index"]} for t in p["tiles"]]
        _tile_region(g_left, body_top, g_width, body_height, tile_boxes,
                     min_side, tile_state, f"groups[{p['index']}].tiles")
        state.equalized_splits += tile_state.equalized_splits
        tile_rects = dict(tile_state.placements)

        equal_tiles = Fraction(1, len(p["tiles"]))
        for t in p["tiles"]:
            t_left, t_top, t_width, t_height = tile_rects[t["index"]]
            if t_width <= min_side or t_height <= min_side:
                at_floor += 1
            worst_aspect = max(worst_aspect, _aspect(t_width, t_height))
            want_t = (equal_tiles if p["weight"] == 0
                      else t["weight"] / p["weight"])
            tile_error = max(tile_error,
                             _ppm(Fraction(t_width * t_height) / body_area,
                                  want_t))
            record = {
                "id": t["tile"]["id"],
                "container_id": p["id"],
                "group": p["index"],
                "group_key": p["id"],
                "index": t["index"],
                "weight": float(t["weight"]),
                **rect(t_left, t_top, t_width, t_height),
            }
            if isinstance(t["tile"].get("name"), str):
                record["name"] = t["tile"]["name"]
            out_items.append(record)

    return {
        "grammar": "treemap",
        "items": out_items,
        "containers": containers,
        "region": rect(s["origin_left"], s["origin_top"],
                       s["region_width"], s["region_height"]),
        "groups": len(plans),
        "tiles": len(out_items),
        "min_tile_side": min_side,
        "group_header_height": header_h,
        "tiles_at_min_side": at_floor,
        "equalized_splits": state.equalized_splits,
        "group_area_error_ppm": group_error,
        "tile_area_error_ppm": tile_error,
        "worst_aspect_ratio": round(float(worst_aspect), 3),
        "bounds": bounding_box([*containers, *out_items]),
    }

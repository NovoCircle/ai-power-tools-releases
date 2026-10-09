#!/usr/bin/env python3
"""Layout grammar: `radial_tree` - a mind map.

A central topic, branches radiating from it, sub-branches hanging off those,
for as many levels as the content has. This is the shape of an EA mind-mapping
diagram: one box in the middle carrying the question, a handful of main topics
around it, and the actual content hanging off the main topics.

Same contract as the rest of the composition engine: plain data in, rectangles
out. No repository calls, no COM, no file or network I/O, no clock, no
randomness. Same input, same output, every time. EA's coordinate convention -
`top` negative and increasing upward, `height = top - bottom` - is the module
docstring of `compose.py`; every rect here obeys it and is built with that
module's `rect()`.

WHY THIS IS NOT `compose_radial`
--------------------------------
`compose_radial` places a ring of items around a hub and gives every branch the
SAME slice of the circle: the slice is `min(step, 120)` where `step` is the
sweep divided evenly by the number of branches. That is right for a hub and its
spokes, where the branches are peers and any second ring is decoration. It is
wrong for a tree, because a tree is not evenly distributed: a branch with eight
children needs more angular room than a branch with one, and an even split
wastes the room on one side while forcing the crowded side out to a radius that
drags the whole diagram with it. Measured, with the shipped defaults: a hub of
twelve branches, one of them carrying eight children and the rest one each,
comes out of `compose_radial` at 1746 x 3399 units, almost all of that height
being the one crowded branch shoved outward until its fixed 30-degree slice
could hold eight boxes.

Three further things differ, and together they are why this is its own grammar
rather than a flag on that one:

* **Angular room is allocated by WEIGHT, not by count** - see `_assign_wedges`.
* **Depth is not capped at two.** A mind map with three levels below the
  central topic is ordinary; `compose_radial` refuses past two rings, and
  correctly so for what it draws.
* **Branches cannot interleave, structurally.** Each node owns a closed
  interval of bearings and every descendant is placed inside it, so two
  top-level branches can never trade children. `compose_radial` centers a
  branch's ring on the branch and gives it a fixed width regardless of what its
  neighbors were given, so its branches only stay apart when the arithmetic
  happens to work out.

WHAT IS KEPT FROM `compose_radial`, DELIBERATELY
------------------------------------------------
`radius` means the same thing here: the CLEAR GAP from the parent box's border
out to the child box's border, along the child's own ray - the part of the
spoke a reader actually sees drawn - and NOT a center-to-center distance. Every
child of one parent therefore sits at its own distance from that parent's
center, and the visible spokes all come out the same length. That property is
what `lint.check_ring_spokes` measures, and it is the reason this grammar does
NOT put each level on a concentric circle the way a textbook radial tree would:
concentric levels make the drawn spokes from one parent to its children vary by
however much the fan is bent, which is exactly the defect that rule exists to
catch. Level-uniform radii would read fine and lint dirty; equal clear gaps read
fine and lint clean, so equal clear gaps win.

The trigonometry is duplicated from `compose.py` rather than imported from it.
`_reach`, `_min_reach` and `_polar` here are the same functions by construction
and are kept in step by the tests, not by an import: this module is meant to
stand alone, and reaching into another module's underscore names to get it
would couple the two in the one direction neither wants.
"""
from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from typing import Any, Optional

from compose import DEFAULT_SPEC, LayoutError, bounding_box, rect

__all__ = [
    "DEFAULT_TREE_SPEC",
    "compose_radial_tree",
    "reach_spread",
]


# ---------------------------------------------------------------------------
# Spec
# ---------------------------------------------------------------------------
# Keys this grammar shares with the rest of the engine keep the engine's own
# defaults, read from `DEFAULT_SPEC` rather than restated, so a box that changes
# size for every other grammar changes size for this one too.
_SHARED_KEYS = (
    "origin_left", "origin_top",
    "item_width", "item_height", "item_gap_x",
    "radius", "start_angle", "sweep",
)

DEFAULT_TREE_SPEC: dict[str, Any] = {key: DEFAULT_SPEC[key] for key in _SHARED_KEYS}
DEFAULT_TREE_SPEC.update({
    # Levels of branches below the central topic. Three is an ordinary mind
    # map; four is the point at which the outermost labels are further from the
    # middle than they are from each other and the picture stops being radial.
    # Deeper is REFUSED rather than warned about - the result dict has no
    # channel a warning could travel down that anything reads, the same
    # decision `compose_radial` and `compose_nested_grid` make.
    "max_tree_depth": 4,

    # The widest arc any one node may spread its own children across, whatever
    # its wedge entitles it to. Without a cap, two branches over a full circle
    # get 180 degrees each and their children sweep back past the middle; the
    # picture stops looking like it grows outward. 120 is `compose_radial`'s
    # cap, kept so the two grammars bend a branch by the same amount.
    "max_branch_sweep": 120,
})

_ANY_INT_KEYS = frozenset({"origin_left", "origin_top", "start_angle"})
_POSITIVE_KEYS = frozenset({
    "item_width", "item_height", "radius", "sweep",
    "max_tree_depth", "max_branch_sweep",
})
_NON_NEGATIVE_KEYS = frozenset({"item_gap_x"})

# What one node may restate for its OWN DIRECT CHILDREN. It does not cascade to
# grandchildren: each level states its own sizing, which is the rule the nested
# grid follows and for the same reason - siblings may not differ, levels may.
_NODE_OVERRIDES = frozenset({"item_width", "item_height", "radius"})

# How far the widening guard may go before it gives up. Each round multiplies
# every clear gap by `_WIDEN_STEP`, so the reach of the guard is
# `_WIDEN_STEP ** _WIDEN_ROUNDS` - about 15x - which is far past anything a
# real mind map needs. See `compose_radial_tree` for what the guard is for.
_WIDEN_STEP = 1.15
_WIDEN_ROUNDS = 20


def _as_int(value: Any, where: str) -> int:
    """Coerce a number to a whole EA unit, rejecting anything that is not one.

    bool is rejected on purpose: True would otherwise sail through as 1.
    """
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise LayoutError(f"{where}: expected a number, got {type(value).__name__}")
    return int(round(value))


def _require_mapping(value: Any, where: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise LayoutError(f"{where}: expected a dict, got {type(value).__name__}")
    return value


def _require_list(value: Any, where: str) -> list[Any]:
    """Accept any ordered sequence except a string, and keep the caller's order.

    Order is the whole input: it is the order the branches come out in, going
    clockwise, so a set or a bare dict is rejected rather than quietly iterated
    in whatever order it happens to have.
    """
    if isinstance(value, (str, bytes)) or not isinstance(value, Sequence):
        raise LayoutError(f"{where}: expected a list, got {type(value).__name__}")
    return list(value)


def _resolve_spec(spec: Mapping[str, Any] | None) -> dict[str, Any]:
    """Validate a caller spec and fill in the defaults it left out.

    Unknown keys are an error, including keys that are valid for another
    grammar: `wrap_width` has no meaning on a mind map, and accepting it in
    silence would let a caller believe it had done something.
    """
    out = dict(DEFAULT_TREE_SPEC)
    if spec is None:
        return out
    spec = _require_mapping(spec, "spec")

    unknown = sorted(k for k in spec if k not in DEFAULT_TREE_SPEC)
    if unknown:
        raise LayoutError(
            f"spec: unknown key(s) {', '.join(repr(k) for k in unknown)}; "
            f"valid keys are {', '.join(sorted(DEFAULT_TREE_SPEC))}"
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
        elif key in _NON_NEGATIVE_KEYS:
            n = _as_int(value, where)
            if n < 0:
                raise LayoutError(f"{where}: must not be negative, got {n}")
            out[key] = n
        else:  # pragma: no cover - only reachable if a default loses its class
            raise LayoutError(f"{where}: no validation rule for this key")
    return out


def _override(node: Mapping[str, Any], key: str, fallback: Mapping[str, Any],
              where: str) -> int:
    """Read one node's override of a sizing key, falling back to the spec."""
    if key not in node:
        return fallback[key]
    n = _as_int(node[key], f"{where}.{key}")
    if n <= 0:
        raise LayoutError(f"{where}.{key}: must be positive, got {n}")
    return n


def _check_item(raw_item: Any, where: str, seen: dict[Any, str]) -> Mapping[str, Any]:
    """Validate one node and claim its id.

    Ids must be unique across the whole tree, because the caller uses them to
    map rects back onto model elements and a duplicate there means two elements
    silently sharing one rect. Any hashable id is accepted and preserved
    VERBATIM - ints as ints, strings as strings - because the primary consumer
    maps these back onto EA element ids, which are integers.
    """
    item = _require_mapping(raw_item, where)
    item_id = item.get("id")
    if item_id is None or (isinstance(item_id, str) and not item_id.strip()):
        raise LayoutError(
            f"{where}.id: every node needs a non-empty id, got {item_id!r}"
        )
    try:
        hash(item_id)
    except TypeError:
        raise LayoutError(
            f"{where}.id: node id must be hashable so it can be checked for "
            f"uniqueness, got {type(item_id).__name__}"
        ) from None
    if item_id in seen:
        raise LayoutError(
            f"{where}.id: duplicate node id {item_id!r}, already used at "
            f"{seen[item_id]}"
        )
    seen[item_id] = where
    return item


# ---------------------------------------------------------------------------
# Trigonometry - the same functions `compose.py` uses, written out again
# ---------------------------------------------------------------------------
def _polar(center_x: int, center_y: int, radius: float, degrees: float) -> tuple:
    """A point on a circle, rounded once, to whole EA units.

    Angles run CLOCKWISE from twelve o'clock, because that is how a reader
    describes one of these - "starting at the top and going round". Verified
    against the arithmetic rather than against prose: at 0 degrees the result is
    `(center_x, center_y + radius)`, and EA's vertical axis is inverted, so a
    LARGER y is HIGHER on the diagram - straight up. At 90 degrees it is
    `(center_x + radius, center_y)` - straight right. Up then right is
    clockwise.

    Rounding is applied to the coordinate and not to the angle: rounding the
    angle first would let a ring of twelve drift visibly by the time it closed.
    """
    radians = math.radians(degrees - 90.0)
    return (int(round(center_x + radius * math.cos(radians))),
            int(round(center_y - radius * math.sin(radians))))


def _reach(item_w: int, item_h: int, degrees: float) -> float:
    """How far a box's own border sits from its center, along a ray at `degrees`.

    A ray leaving the box's center leaves through either a horizontal or a
    vertical side, whichever it reaches first:

        horizontal sides, at half the height:  (h / 2) / |cos(degrees)|
        vertical sides,   at half the width:   (w / 2) / |sin(degrees)|

    and the nearer one is the side actually crossed. For a 140x60 box that is 30
    straight up, 70 straight out to the side, and 76.2 through a corner. Taking
    it off both ends of a spoke is what makes the DRAWN part of every spoke from
    one parent come out the same length whatever direction it points.

    A ray exactly along an axis has a zero component on the other one, so that
    candidate is dropped rather than divided by.

    A DELIBERATE APPROXIMATION: every border is an axis-aligned RECTANGLE, because
    a rect per element is what EA stores and all this can read. An element EA draws
    as a circle has a CONSTANT true reach, so a ring of circles equalized by this
    function bulges at the diagonals by `reach_spread`, per spoke end. The full
    derivation, the measured figures and why it is not fixed here are in
    `compose._reach`; this copy exists because this grammar is self-contained, and
    the two must not drift.
    """
    ux = abs(math.sin(math.radians(degrees)))
    uy = abs(math.cos(math.radians(degrees)))
    candidates = []
    if ux:
        candidates.append((item_w / 2.0) / ux)
    if uy:
        candidates.append((item_h / 2.0) / uy)
    return min(candidates)


def reach_spread(item_w: int, item_h: int) -> float:
    """The measured error in `_reach`'s rectangular border model, per spoke end.

    Half the diagonal, at the corner, less half the shorter side, on its axis. For
    a rectangular element that is the real shape and no error; for a circular one,
    whose true reach is constant, it is how far the ring bulges at the diagonals.
    The guard on the approximation `_reach` documents: a number a caller can read
    and a test can pin. `compose_radial_tree` reports it as `reach_spread`.
    """
    return (math.hypot(item_w, item_h) - min(item_w, item_h)) / 2.0


def _min_reach(item_w: int, item_h: int) -> float:
    """The smallest `_reach` any ray can produce: half the shorter side."""
    return min(item_w, item_h) / 2.0


# ---------------------------------------------------------------------------
# Planning: the tree, its leaf weights, and the wedges
# ---------------------------------------------------------------------------
def _plan(raw_nodes: Any, where: str, depth: int, s: Mapping[str, Any],
          metrics: Mapping[str, int], seen: dict[Any, str]) -> dict:
    """Turn one level of the input into a ring plan, recursively.

    A "ring" here is one parent's set of children, which all share a size and a
    clear gap - the house rule that siblings may not disagree about sizing and
    that the parent is what states it. `metrics` is what this ring's parent
    stated for it.

    Each plan entry carries `leaves`, the number of leaves in its own subtree,
    which is the weight `_assign_wedges` shares the angular room out by.
    """
    if depth > s["max_tree_depth"]:
        raise LayoutError(
            f"{where}: the tree is {depth} levels deep below the middle, and "
            f"this grammar refuses more than max_tree_depth "
            f"({s['max_tree_depth']}); past that the outermost labels are "
            f"further from the middle than they are from each other and the "
            f"picture stops reading as radial. Split it, or raise "
            f"spec.max_tree_depth deliberately"
        )
    children = _require_list(raw_nodes, where)
    if not children:
        raise LayoutError(f"{where}: a branch that states children needs at "
                          f"least one")

    plans = []
    for k, raw in enumerate(children):
        cwhere = f"{where}[{k}]"
        node = _check_item(raw, cwhere, seen)
        bad = sorted(set(node) & {"item_gap_x", "sweep", "start_angle"})
        if bad:
            raise LayoutError(
                f"{cwhere}: {', '.join(repr(b) for b in bad)} is a spec key, "
                f"not a per-node one; a node may only restate "
                f"{', '.join(sorted(_NODE_OVERRIDES))} for its own children"
            )
        child_metrics = {
            "item_width": _override(node, "item_width", s, cwhere),
            "item_height": _override(node, "item_height", s, cwhere),
            "radius": _override(node, "radius", s, cwhere),
        }
        inner = None
        if "items" in node:
            inner = _plan(node["items"], f"{cwhere}.items", depth + 1, s,
                          child_metrics, seen)
        plans.append({
            "id": node["id"],
            "name": node["name"] if isinstance(node.get("name"), str) else None,
            "index": k,
            "inner": inner,
            # A node with no children is one leaf. A node with children weighs
            # what they weigh: an interior node consumes no angular room of its
            # own beyond what its subtree already asks for.
            "leaves": inner["leaves"] if inner else 1,
            "lo": 0.0, "hi": 0.0, "ray": 0.0,
        })

    return {
        "plans": plans,
        "metrics": dict(metrics),
        "leaves": sum(p["leaves"] for p in plans),
        "gap": metrics["radius"],
        "depth": depth,
    }


def _assign_wedges(ring: dict, start: float, span: float, closed: bool,
                   max_branch_sweep: float) -> None:
    """Share one ring's angular room out among its branches, then recurse.

    THIS IS THE DESIGN, so it is written down rather than left to be recovered.

    A tree does not distribute evenly around a circle. Splitting the sweep by
    the NUMBER of branches gives a branch with eight children the same room as a
    branch with one, which wastes the circle on one side and crowds it on the
    other. So each branch is given a WEDGE - a closed interval of bearings -
    whose width is proportional to the number of LEAVES beneath it, and its own
    children are then given sub-wedges of that wedge by the same rule. A branch
    sits on the BISECTOR of its own wedge, so its subtree is balanced about it.

    WHY LEAVES AND NOT NODES
    ------------------------
    What consumes angular room is boxes competing for the same arc. At any one
    depth, the number of boxes a subtree contributes is at most its leaf count,
    and at the deepest depth it is exactly its leaf count - a subtree's leaves
    are its widest generation, because every interior node has at least one
    child. So leaf count is the tight bound on the worst generation and a valid
    bound on every other one. Weighting by total node count instead would pay
    angular room to interior nodes, which sit at smaller radii where a degree
    buys less arc and there is less competition for it anyway; weighting by
    depth would ignore width, which is the thing that actually collides.

    WHY THE WEDGES CANNOT INTERLEAVE
    --------------------------------
    A child's wedge is a subinterval of its parent's, and siblings' wedges are
    disjoint by construction, so two nodes from different branches never share a
    bearing. That is a property of the allocation, not of the arithmetic
    working out, which is the difference between this and centering a
    fixed-width fan on each branch.

    `max_branch_sweep` caps how much of its own wedge a node spends on its
    children, centered on its own bisector. A cap can only make a child's span
    narrower than its parent's, so it cannot break the containment above.
    """
    plans = ring["plans"]
    total = float(ring["leaves"])
    cursor = start
    for p in plans:
        width = span * (p["leaves"] / total)
        p["lo"] = cursor
        p["hi"] = cursor + width
        p["ray"] = cursor + width / 2.0
        cursor += width

    # The step from one branch to the next is half of each one's wedge, which is
    # what makes an uneven tree's angles uneven - deliberately. The tightest
    # step is what the clear gap has to clear, so it is measured here where the
    # wedges are known.
    steps = [plans[i + 1]["ray"] - plans[i]["ray"] for i in range(len(plans) - 1)]
    if closed and len(plans) > 1:
        # A closed ring has one more step than it has gaps between neighbors in
        # list order: the way back round from the last branch to the first.
        steps.append(360.0 - (plans[-1]["ray"] - plans[0]["ray"]))
    ring["min_step"] = min(steps) if steps else 0.0

    for p in plans:
        if p["inner"] is None:
            continue
        own_span = min(p["hi"] - p["lo"], float(max_branch_sweep))
        _assign_wedges(p["inner"], p["ray"] - own_span / 2.0, own_span,
                       False, max_branch_sweep)


def _size_rings(ring: dict, item_gap_x: int) -> None:
    """Raise each ring's clear gap until its own branches cannot touch.

    `radius` is a FLOOR, not a promise: a ring whose branches would collide at
    the gap asked for is widened until they do not. A grammar that drew an
    overlapping diagram because the caller passed a small number would be
    obeying the letter of the spec.

    THE CONDITION IS THE DIAGONAL, NOT THE LONGER SIDE
    --------------------------------------------------
    Two axis-aligned boxes miss each other when they are apart by a full width
    horizontally OR a full height vertically. Two that are inside BOTH of those
    are inside a box of w by h and therefore closer than its diagonal, so

        separation >= hypot(w, h) + gap

    is exactly the condition that rules the overlap out, for any bearing. Using
    `max(w, h)` is not sufficient and is worst for a nearly square box, where
    the diagonal is 41% longer than either side: this engine's history has a
    ring of 90x88 items that overlapped at every count of three or more, with a
    radius driven past 1576 without ever rescuing it, because each widening step
    was measured against a distance that was never going to be enough.

    The chord between two neighbors on a ring, at the tightest step `min_step`,
    is a distance between CENTERS. `radius` is not one - it is the clear gap
    outside the boxes - so the constraint is solved for the center distance and
    the gap read back off it using the SMALLEST reach any ray can produce. Using
    the smallest is what makes this a floor: every branch's actual center
    distance is at least the one the chord was solved for, never less. The
    parent box's own reach is left out even though placement adds it, for the
    same reason - leaving it out can only push branches further out.
    """
    m = ring["metrics"]
    count = len(ring["plans"])
    step = min(abs(ring["min_step"]), 180.0)
    if count > 1 and step > 0.0:
        need = math.hypot(m["item_width"], m["item_height"]) + item_gap_x
        half = math.radians(step / 2.0)
        if math.sin(half) > 0:
            centers = need / (2.0 * math.sin(half))
            ring["gap"] = max(ring["gap"],
                              int(math.ceil(centers - _min_reach(
                                  m["item_width"], m["item_height"]))))
    for p in ring["plans"]:
        if p["inner"] is not None:
            _size_rings(p["inner"], item_gap_x)


# ---------------------------------------------------------------------------
# Placement
# ---------------------------------------------------------------------------
def _place(ring: dict, center_x: int, center_y: int, parent_id: Any,
           parent_size: Optional[tuple], depth: int, scale: float,
           out: list) -> None:
    """Place one ring of branches around a parent, then their own subtrees.

    EVERY SPOKE FROM ONE PARENT THE SAME LENGTH is the property being built
    here, and it is not what putting each child's center on a circle gives you:

        center distance = parent's reach + clear gap + child's own reach

    both reaches taken along the child's own ray. Those two terms are the
    stretches of the spoke that fall INSIDE a box and are never drawn, so
    subtracting them is what leaves the visible part constant. The ink is what
    the reader judges, so the ink is what is held constant.

    `parent_size` is the box in the middle, or None when there is no box there -
    a tree composed without a central topic radiates from a bare point, and a
    bare point reaches nowhere. For every level below the first the box in the
    middle is the branch this ring hangs off, so the same arithmetic serves
    every level without a special case.
    """
    m = ring["metrics"]
    own = (m["item_width"], m["item_height"])
    gap = math.ceil(ring["gap"] * scale)
    ring["gap_used"] = int(gap)

    for p in ring["plans"]:
        angle = p["ray"]
        distance = gap + _reach(*own, angle)
        if parent_size is not None:
            distance += _reach(*parent_size, angle)
        x, y = _polar(center_x, center_y, distance, angle)
        record = {
            "id": p["id"],
            "container_id": parent_id,
            "ring": depth,
            "angle": round(angle % 360.0, 3),
            "wedge": round(p["hi"] - p["lo"], 3),
            "leaves": p["leaves"],
            "index": p["index"],
            **rect(x - m["item_width"] // 2, y + m["item_height"] // 2,
                   m["item_width"], m["item_height"]),
        }
        if p["name"] is not None:
            record["name"] = p["name"]
        out.append(record)

        if p["inner"] is not None:
            _place(p["inner"], x, y, p["id"], own, depth + 1, scale, out)


def _collides(items: Sequence[Mapping[str, Any]], margin: int) -> Optional[tuple]:
    """The first pair of boxes closer than `margin`, or None.

    Each rect is grown by `margin` on every side before the test, so a clean
    result means the boxes are at least `2 * margin` apart and not merely not
    overlapping. Tested in EA's flipped-y convention, where `top` is greater
    than `bottom`.
    """
    for i, a in enumerate(items):
        for b in items[i + 1:]:
            if a["right"] + margin <= b["left"] - margin:
                continue
            if b["right"] + margin <= a["left"] - margin:
                continue
            if a["bottom"] - margin >= b["top"] + margin:
                continue
            if b["bottom"] - margin >= a["top"] + margin:
                continue
            return (a["id"], b["id"])
    return None


def compose_radial_tree(
    nodes: Sequence[Mapping[str, Any]],
    spec: Mapping[str, Any] | None = None,
    hub: Optional[Mapping[str, Any]] = None,
) -> dict[str, Any]:
    """Lay out a mind map: a central topic, branches, and sub-branches.

    `nodes` is the list of main branches, in clockwise order. A branch carrying
    `items` gets its own sub-branches, recursively, to `spec.max_tree_depth`.
    `hub`, when given, is the central topic - `{"id": ..., "name": ...}` - and
    is placed as an item rather than as a container, because it is one of the
    things on the diagram rather than something enclosing them:

        compose_radial_tree(
            [{"id": 1, "name": "Paperless Office",
              "items": [{"id": 11}, {"id": 12}, {"id": 13}]},
             {"id": 2, "name": "Day One Functionality"},
             {"id": 3, "name": "Inventory Management",
              "items": [{"id": 31}, {"id": 32}]}],
            hub={"id": 100, "name": "Stakeholder Needs"},
        )

    Behavior worth knowing:

    * **Angular room goes by weight.** Each branch owns a wedge whose width is
      proportional to the number of leaves in its subtree, and its children own
      sub-wedges of that wedge. A branch with eight children gets eight times
      the room of a branch with one. See `_assign_wedges` for why leaves.
    * **Angles run clockwise from twelve o'clock**, and `start_angle` is the
      bearing of the FIRST branch - its wedge is centered on that bearing.
    * **A partial `sweep` is NOT inclusive of both ends**, which is where this
      differs from `compose_radial`. The sweep is divided into wedges and each
      branch sits at its wedge's center, so a 180-degree sweep of three equal
      branches puts them at 30, 90 and 150 degrees rather than at 0, 90 and 180.
      Reaching the ends would mean the end branches' wedges hung half outside
      the sweep, and their children with them.
    * **Uniform sizing within a ring.** Stated by the parent, so siblings cannot
      disagree - the rule the other grammars follow. A node may restate
      `item_width`, `item_height` and `radius` for its OWN children; it does not
      cascade to grandchildren.
    * **Every spoke from one parent is the same length.** `radius` is the CLEAR
      GAP between a parent's box and its children's boxes - the drawn part of a
      spoke - not a center-to-center distance. Levels are therefore NOT
      concentric circles around the middle: see the module docstring for why
      that trade was made deliberately.
    * **The radius is a floor.** Each ring is widened until its own branches
      cannot touch, by the diagonal condition in `_size_rings`.
    * **Overlap-freedom is checked, not merely argued.** Disjoint wedges keep
      branches apart in BEARING, but a child is placed from its parent's center
      rather than from the middle of the diagram, so its bearing as seen from
      the middle drifts toward its parent's. The drift is bounded - a node's
      bearing from the middle always stays inside its top-level branch's wedge -
      but it is not bounded tightly enough for a closed form to size the deeper
      levels from. So the composition is laid out, tested for collisions, and
      every clear gap widened by a fixed step until it is clean. `gap_scale`
      on the result says how much widening it took; 1.0 means the floors were
      already enough, which is the usual case.
    * **Depth is bounded** by `max_tree_depth`, default 4, and a deeper tree is
      REFUSED rather than warned about.

    THE CONNECTORS ARE NOT THIS GRAMMAR'S JOB. Reference mind maps commonly join
    a branch to its children with curved lines; the routing vocabulary available
    here has no arc, so a generated equivalent carries straight or Bezier lines.
    The geometry is equivalent; the drawing is not identical, and saying so is
    part of using this grammar honestly.

    Returns the result dict described in `compose.py`'s module docstring, with
    `containers` empty and an item's `container_id` naming the ITEM it hangs
    from - the central topic, or the branch it grew off. Items also carry
    `ring` (0 for the central topic, 1 for a main branch, and so on), `angle`,
    `wedge` and `leaves`, so a caller can reason about the allocation without
    recovering it from coordinates. Raises `LayoutError` for any input that
    cannot yield sane geometry.
    """
    s = _resolve_spec(spec)
    raw_nodes = _require_list(nodes, "nodes")
    if not raw_nodes:
        raise LayoutError("nodes: at least one branch is required, got an "
                          "empty list")

    seen: dict[Any, str] = {}
    hub_item = None
    if hub is not None:
        hub_item = _check_item(hub, "hub", seen)

    root_metrics = {
        "item_width": s["item_width"],
        "item_height": s["item_height"],
        "radius": s["radius"],
    }
    root = _plan(raw_nodes, "nodes", 1, s, root_metrics, seen)

    sweep = float(s["sweep"])
    closed = sweep >= 360.0
    # `start_angle` is where the FIRST branch goes, so the wedges begin half of
    # that branch's own wedge earlier. Stated this way round because it is how
    # `compose_radial` reads `start_angle`, and a caller moving between the two
    # should not have to discover that one of them means something else.
    first_width = sweep * (root["plans"][0]["leaves"] / float(root["leaves"]))
    _assign_wedges(root, float(s["start_angle"]) - first_width / 2.0, sweep,
                   closed, float(s["max_branch_sweep"]))
    _size_rings(root, s["item_gap_x"])

    hub_size = ((s["item_width"], s["item_height"])
                if hub_item is not None else None)
    margin = s["item_gap_x"] // 2

    scale = 1.0
    for _ in range(_WIDEN_ROUNDS + 1):
        items: list[dict[str, Any]] = []
        if hub_item is not None:
            record = {
                "id": hub_item["id"],
                "container_id": None,
                "ring": 0,
                "angle": 0.0,
                "wedge": round(sweep, 3),
                "leaves": root["leaves"],
                "index": 0,
                **rect(-(s["item_width"] // 2), s["item_height"] // 2,
                       s["item_width"], s["item_height"]),
            }
            if isinstance(hub_item.get("name"), str):
                record["name"] = hub_item["name"]
            items.append(record)
        # The middle sits at the origin while the tree is built; the whole
        # composition is translated onto `origin_left`/`origin_top` once, at the
        # end, so the caller gets the same starting corner every other grammar
        # gives and this module never has to guess its own extent in advance.
        _place(root, 0, 0, hub_item["id"] if hub_item else None, hub_size,
               1, scale, items)
        clash = _collides(items, margin)
        if clash is None:
            break
        scale *= _WIDEN_STEP
    else:
        raise LayoutError(
            f"nodes: this tree could not be laid out without a collision "
            f"between {clash[0]!r} and {clash[1]!r} even after widening every "
            f"clear gap {_WIDEN_ROUNDS} times; the branches are too uneven for "
            f"the sweep given. Give it more sweep, smaller boxes, or split it"
        )

    bounds = bounding_box(items)
    dx = s["origin_left"] - bounds["left"]
    dy = s["origin_top"] - bounds["top"]
    for item in items:
        item["left"] += dx
        item["right"] += dx
        item["top"] += dy
        item["bottom"] += dy

    return {
        "grammar": "radial_tree",
        "items": items,
        "containers": [],
        "center": {"x": dx, "y": dy},
        "radius": root["gap_used"],
        "gap_scale": round(scale, 6),
        # The rectangular-border approximation's error, per spoke end, stated with
        # the layout it applies to. See `_reach`.
        "reach_spread": reach_spread(int(s["item_width"]), int(s["item_height"])),
        "bounds": bounding_box(items),
    }

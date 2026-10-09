#!/usr/bin/env python3
"""Pure-arithmetic layout engine for composed diagrams.

This is the code corner of the diagram-composition skill. It turns a plain-data
description of what belongs on a diagram into rectangles, and does nothing else:
no repository calls, no COM, no file or network I/O, no clock, no randomness.
Same input, same output, every time.

Modeling-language specifics do not belong in this file. Sizes, spacing, wrap
widths and label areas arrive in a `spec` dict supplied by the caller - in
practice from a per-language binding held as data. There is no branch here on a
technology id, a profile name or a stereotype, and adding one would be a design
error: the arithmetic of a band of boxes is the same whatever notation the boxes
are eventually drawn in.

Coordinate convention
---------------------
Sparx EA's diagram coordinates are not the usual screen coordinates, and getting
this backwards silently corrupts everything downstream.

    left, right   positive, increasing rightward       right > left
    top, bottom   NEGATIVE, increasing upward          top > bottom

So:

    width  = right - left
    height = top - bottom          <-- not bottom - top

A real element placed by EA 17.1: left=50, top=-50, right=190, bottom=-110. That
is 140 wide and 60 tall. Moving an element DOWN the diagram makes both `top` and
`bottom` MORE negative. The visual top of a diagram is the coordinate nearest
zero, which means "the topmost rect" is the one with the LARGEST `top`.

Every rect this module produces obeys that convention, and `rects_overlap` is
written for it. Build rects with `rect()` rather than by hand.

Grammars implemented here
-------------------------
`compose_layered_bands` - horizontal bands stacked top to bottom, items laid out
left to right inside each band, wrapping to further rows when a band is wider
than the wrap width.

`compose_lanes` - swimlanes: parallel tracks, each carrying a sequence of items
that flows along the lane. Items at the same sequence index across different
lanes line up on the flow axis, which is what makes a handoff readable.

`compose_nested_grid` - containers within containers, each laid out as a grid of
its children. Containment is the only structure; there is no sequence and
usually no connectors. This is the one that takes a recursive tree rather than a
flat list of groups.

`compose_radial` - a hub and its spokes: items distributed on a ring around a
center, optionally with a further ring hanging off each one. The one grammar
here whose arithmetic is trigonometric, so it is also the one that has to be
careful about rounding: coordinates are rounded once, at the end, so the same
ring comes out identically on every machine.

`compose_two_column_cycle` - a cycle drawn as two columns: the flow runs down
one and back up the other, closing the loop across the top. The one grammar here
whose items may be different HEIGHTS, because on the content it is for the height
is the number of lines inside the box; the width is shared so that the cycle
still has a straight outline. Its row pitch is a floor, widened to clear the
tallest box, and the pitch used comes back on the result.

All five take plain lists of dicts and return plain dicts. No classes to
construct, nothing to subclass.

Result shape
------------
    {
      "grammar":    "layered_bands" | "lanes" | "nested_grid" | "radial"
                    | "two_column_cycle",
      "items":      [ {"id", "left", "top", "right", "bottom", ...}, ... ],
      "containers": [ {"id", "name", "kind", "index", "left", "top", "right",
                       "bottom", "label": {...}}, ... ],
      "bounds":     {"left", "top", "right", "bottom", "width", "height"},
      "conflicts":  [ FitConflict, ... ],      # layered_bands; usually empty
    }

`conflicts` holds the decisions the arithmetic could not make on the caller's
behalf - today, a width that was asked for which the content does not fit. Each
entry states both options and which one was applied. An entry whose `answered` is
False is a question still owed to the user: see `FitConflict`.

`items` are nested inside their `containers` by design, so test the two sets for
mutual disjointness separately - an item is supposed to sit inside its band.

For `nested_grid`, containers nest inside CONTAINERS too, so even the container
set is not mutually disjoint there: compare siblings, not the whole set.

`radial` returns no containers at all, and an item's `container_id` names the
ITEM it hangs from - the hub, or the spoke it branches off. It also carries
`center` and the `radius` actually used, which can exceed the one asked for -
up to `max_radius`, past which the composition is refused rather than widened.
That radius is the CLEAR GAP between the box at the middle and the boxes on the
ring, not the distance to an item's center: the items sit at whatever distance
makes that gap equal for all of them, so do not expect them to share one.

`two_column_cycle` returns no containers either, and its items' `container_id` is
None: a cycle is a ring of peers with nothing enclosing them, and nothing it
places hangs off anything else. It carries `rows`, `columns`, `row_pitch`,
`column_pitch` and `item_width` - the pitch is a floor and may have been widened.
"""
from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from typing import Any, Optional

__all__ = [
    "LayoutError",
    "DEFAULT_SPEC",
    "FitConflict",
    "FIT_WIDEN",
    "FIT_OVERLAP",
    "FIT_ANSWERS",
    "DEFAULT_FIT_ANSWER",
    "WIDTH_MISFIT",
    "check_misfit_answer",
    "resolve_width_misfit",
    "compose_layered_bands",
    "compose_lanes",
    "compose_nested_grid",
    "compose_radial",
    "reach_spread",
    "compose_two_column_cycle",
    "rect",
    "rect_width",
    "rect_height",
    "rects_overlap",
    "bounding_box",
]


class LayoutError(ValueError):
    """A layout description or spec that cannot produce sane geometry.

    Raised in preference to returning rects that are negative, zero-sized or
    overlapping. The message always names the offending field, using the
    caller's own path into the input - `bands[2].items[0].id`, `spec.h_pitch` -
    so the caller can find it without guessing.
    """


# ---------------------------------------------------------------------------
# A width that was asked for, and content that does not fit in it
# ---------------------------------------------------------------------------
# Two things can be true at once: a width was stated on purpose, and the content
# is wider than it. Widening the box and letting the text run past the border are
# both legitimate drawings, and which one is wanted is a judgment about THAT
# diagram - a reference model whose straight edge is the whole point may want the
# overlap, a landscape whose stored rects have to match the render must have the
# widening.
#
# So neither is decided here. The conflict is REPORTED, in a shape a caller can
# read without parsing prose, and a caller that has asked its user relays the
# answer back as `on_misfit`. Widening is still what happens when nobody answers,
# because it is the safe direction: EA grows a box it cannot fit whatever the
# stored rect says, so widening is the only answer under which the geometry every
# later check reads is the geometry EA paints. What changed is that it is no
# longer silent.
#
# ONE MECHANISM, NOT ONE PER SITE. Two places had the same disagreement and
# settled it two different ways without saying so: `item_width` against an
# element name too long for it, and `min_band_width` against a band whose
# contents are wider than the width asked for. Both come through here now, so a
# caller learns of them in one shape and answers them with one vocabulary. A
# third site that acquires the same problem should join them rather than grow a
# flag of its own.
FIT_WIDEN = "widen"
FIT_OVERLAP = "overlap"

#: The answers `on_misfit` accepts, and the only two to put to a user.
FIT_ANSWERS = (FIT_WIDEN, FIT_OVERLAP)

#: What is applied when nobody answered. See above for why it is the widening.
DEFAULT_FIT_ANSWER = FIT_WIDEN

#: The `conflict` tag every `FitConflict` carries, so a consumer branches on a
#: constant rather than on a sentence.
WIDTH_MISFIT = "width_does_not_fit_content"


class FitConflict(dict):
    """A stated width and the content in it disagree - stated, not settled.

    A plain `dict` subclass, so it serializes as JSON with nothing to import and
    nothing to teach a consumer. Every field is machine-readable:

    ``conflict``        always `WIDTH_MISFIT`. Branch on this, not on prose.
    ``where``           the key whose value could not be honored, spelled the
                        way a caller writes it: `spec.item_width`,
                        `spec.min_band_width`.
    ``driver``          the name, or the band, that did not fit. `""` when the
                        content that did not fit has no name.
    ``driver_kind``     what `driver` is: `item_name` or `band_contents`.
    ``requested_width`` the width that was asked for.
    ``required_width``  the width the content needs.
    ``options``         the two answers, each with the `width` it produces and
                        the `effect` it has. This is the list to read out.
    ``applied``         which answer is in the geometry: `widen` or `overlap`.
    ``width_applied``   the width that is in the geometry.
    ``answered``        whether a caller supplied the answer. False means the
                        default was applied and the question is still open.
    ``question``        the question to put to the user, ready to ask.
    ``note``            one line for a log or a report.
    ``detail``          optional extra from the site that raised it, naming what
                        about the content would not fit.

    `answered` is the field that matters most and the easiest to skip. A caller
    holding one that is False is holding a decision nobody made.
    """

    def __init__(self, *, where: str, requested_width: int,
                 required_width: int, applied: str, answered: bool,
                 driver: str = "", driver_kind: str = "",
                 detail: str = "") -> None:
        width = required_width if applied == FIT_WIDEN else requested_width
        subject = repr(driver) if driver else "the content"
        super().__init__(
            conflict=WIDTH_MISFIT,
            where=where,
            driver=driver,
            driver_kind=driver_kind,
            requested_width=int(requested_width),
            required_width=int(required_width),
            options=[
                {
                    "answer": FIT_WIDEN,
                    "width": int(required_width),
                    "effect": (
                        f"widen to {required_width}px - "
                        f"{required_width - requested_width}px more than was "
                        f"asked for - so the content fits inside the border"
                    ),
                },
                {
                    "answer": FIT_OVERLAP,
                    "width": int(requested_width),
                    "effect": (
                        f"keep the {requested_width}px that was asked for and "
                        f"let the content be drawn past the border"
                    ),
                },
            ],
            applied=applied,
            width_applied=int(width),
            answered=bool(answered),
            question=(
                f"{where}: {subject} does not fit the {requested_width}px that "
                f"was asked for - it needs {required_width}px. Ask the user "
                f"which they want for this diagram: widen to {required_width}px, "
                f"or keep {requested_width}px and let the content overlap the "
                f"border. Then pass their answer back as "
                f"on_misfit={FIT_WIDEN!r} or on_misfit={FIT_OVERLAP!r}."
            ),
            note=(
                f"{where}: {requested_width}px was asked for and "
                f"{required_width}px is needed to fit {subject}; applied "
                f"{applied!r}, so the width used is {width}px."
                + ("" if answered else
                   " Nobody answered, so that is the default rather than a"
                   " choice.")
            ),
            detail=detail,
        )

    @property
    def width(self) -> int:
        """The width that is in the geometry this conflict came back with."""
        return int(self["width_applied"])


def check_misfit_answer(where: str, on_misfit: Optional[str]) -> None:
    """Refuse an `on_misfit` that is not one of the two answers.

    Separate from `resolve_width_misfit` so it can run on EVERY call rather than
    only on the calls that turn out to have a conflict. A misspelled answer and
    nobody answering are opposite states - one is a decision, the other is a
    question still owed - and letting a typo fall through to the default would
    merge them, on exactly the diagrams where the content happened to fit.
    """
    if on_misfit is not None and on_misfit not in FIT_ANSWERS:
        raise LayoutError(
            f"{where}: on_misfit must be one of "
            f"{', '.join(repr(a) for a in FIT_ANSWERS)} - the user's answer to "
            f"the widen-or-overlap question - got {on_misfit!r}"
        )


def resolve_width_misfit(
    where: str,
    requested_width: int,
    required_width: int,
    driver: str = "",
    driver_kind: str = "",
    on_misfit: Optional[str] = None,
    detail: str = "",
) -> tuple[int, Optional[FitConflict]]:
    """The width to use, and the conflict to report - `None` when there is none.

    `on_misfit` is the USER'S ANSWER, relayed by the caller; `None` means nobody
    has answered. It is validated whether or not it turns out to matter, so a
    misspelled answer is refused rather than quietly ignored on every diagram
    where the content happened to fit.
    """
    check_misfit_answer(where, on_misfit)
    requested = int(requested_width)
    required = int(required_width)
    if required <= requested:
        return requested, None
    conflict = FitConflict(
        where=where,
        requested_width=requested,
        required_width=required,
        applied=on_misfit or DEFAULT_FIT_ANSWER,
        answered=on_misfit is not None,
        driver=driver,
        driver_kind=driver_kind,
        detail=detail,
    )
    return conflict.width, conflict


# ---------------------------------------------------------------------------
# Defaults
# ---------------------------------------------------------------------------
# Units are EA diagram units, which for practical purposes are pixels at 100%
# zoom. These numbers are deliberately generous: a caller that supplies no spec
# at all should still get something a person would accept, not something that
# merely fails to crash.
#
# A value of None means "derive it" - see _band_metrics and _lane_metrics for
# the derivation. Deriving the pitch from size plus gap is what lets a caller
# override one item size without also having to restate every pitch.
DEFAULT_SPEC: dict[str, Any] = {
    # Where the top-left of the composition goes. `origin_top` is negative
    # because EA's vertical axis is.
    "origin_left": 20,
    "origin_top": -20,

    # Item box size. Uniform within a band or a lane; see the note in
    # _band_metrics on why that is a rule and not an accident.
    "item_width": 140,
    "item_height": 60,

    # Gaps used to derive pitches when a pitch is not given outright.
    "item_gap_x": 20,
    "item_gap_y": 20,

    # Pitch = step from one item's leading edge to the next one's, along the
    # axis named. Must be at least the item's extent on that axis, or items
    # would overlap. None -> item extent + matching gap.
    "h_pitch": None,      # left edge to left edge, within a band row
    "row_pitch": None,    # top edge to top edge, between wrapped rows

    # Widest a band's content may get before it wraps to another row.
    "wrap_width": 900,

    # "left" or "center" - how bands line up against each other.
    "align": "left",

    # Label areas. A band reserves a strip across its top; a horizontal lane
    # reserves a column down its left; a vertical lane reserves a strip across
    # its top.
    "label_height": 28,
    "label_width": 140,

    # Band container padding and stacking.
    "band_pad_x": 12,
    "band_pad_y": 12,
    "band_gap": 30,           # vertical gap between one band and the next
    "band_pitch": None,       # optional MINIMUM band-top to band-top step
    "min_band_width": None,   # None -> item_width + 2 * band_pad_x

    # Lane container padding and stacking.
    "lane_pad": 12,
    "lane_gap": 0,                # swimlanes normally abut; 0 makes them touch
    "item_gap_flow": 30,          # gap between successive slots along the flow
    "flow_pitch": None,           # optional MINIMUM slot-start to slot-start step
    "min_lane_thickness": None,   # None -> item cross extent + 2 * lane_pad

    # Nested-grid containers. `grid_pad` is constant on every side; the top
    # inset is `grid_pad + label_height`, so the title strip is cleared rather
    # than being what the padding is made of.
    #
    # Same shape as the container arithmetic documented in the
    # `ea-navigation-diagrams` skill (PAD_L/R, PAD_T "room for the container's
    # own title", PAD_B), with the pads parameterized instead of fixed at
    # 45/60/40 and PAD_T decomposed into `label_height + grid_pad`. If that
    # skill's numbers are ever revised, these are the knobs that express them.
    "grid_pad": 12,
    "grid_columns": None,     # None -> ceil(sqrt(n)), which keeps a grid squarish
    "max_grid_depth": 3,      # levels of containment allowed; deeper is REFUSED

    # Radial rings. `radius` is the clear gap from the box at the middle out to
    # the boxes on the ring - the drawn length of a spoke - and it is a FLOOR: a
    # ring whose items would collide at that distance is widened until they do
    # not, and the radius actually used comes back on the result.
    "radius": 220,

    # How far that widening may go. It has to be bounded from outside, because
    # the widening is not self-limiting: fitting n boxes into a FIXED angular
    # sweep needs a radius that grows about in proportion to n and inversely to
    # the sweep, and nothing in that arithmetic ever stops. Measured on 90x88
    # items over a 60-degree fan: 238 units at three items, 2046 at sixteen,
    # 3161 at twenty-four. Past this the composition is REFUSED rather than
    # widened further - see `_plan_ring`.
    #
    # WHY 900: it is `wrap_width`, the number this module already uses for the
    # widest a composition's content may get before it has to be broken up.
    # Borrowing it as a RADIUS is generous rather than tight, since a full circle
    # at radius 900 is already about 2000 units across. A caller who genuinely
    # wants a wall-sized ring raises this deliberately, the way
    # `max_ring_depth` is raised.
    "max_radius": 900,
    "start_angle": 0,         # degrees clockwise from twelve o'clock
    "sweep": 360,             # how much of the circle to use
    "max_ring_depth": 2,      # rings allowed; deeper is REFUSED
}

# `start_angle` may legitimately be negative or zero: it is a bearing, not a
# size, and "start at ten o'clock" is -60.
_ANY_INT_KEYS = frozenset({"origin_left", "origin_top", "start_angle"})
_POSITIVE_KEYS = frozenset({
    "item_width", "item_height", "wrap_width", "label_height", "label_width",
    "max_grid_depth", "radius", "max_radius", "sweep", "max_ring_depth",
})
_NON_NEGATIVE_KEYS = frozenset({
    "item_gap_x", "item_gap_y", "item_gap_flow",
    "band_pad_x", "band_pad_y", "band_gap", "lane_pad", "lane_gap",
    "grid_pad",
})
_OPTIONAL_POSITIVE_KEYS = frozenset({
    "h_pitch", "row_pitch", "band_pitch", "flow_pitch",
    "min_band_width", "min_lane_thickness",
    "grid_columns",
})
_ALIGNMENTS = ("left", "center")
_ORIENTATIONS = ("horizontal", "vertical")

# Keys a single band or lane may override for itself. Different bands are
# allowed to size their items differently; items within one band are not.
_BAND_OVERRIDES = frozenset({
    "item_width", "item_height", "h_pitch", "row_pitch", "wrap_width",
    "label_height",
})
_LANE_OVERRIDES = frozenset({"item_width", "item_height"})

# What one nested-grid container may restate for its OWN DIRECT CHILDREN. It
# does not cascade to grandchildren: each level states its own sizing, which is
# what "levels may differ, siblings may not" means in practice.
_GRID_OVERRIDES = frozenset({
    "item_width", "item_height", "label_height", "grid_columns",
})

# The widest arc a branch may occupy. Without a cap, a two-item ring gives each
# branch 180 degrees and the outer items sweep back across the center.
_MAX_BRANCH_SWEEP = 120.0


# ---------------------------------------------------------------------------
# Rect primitives - all in EA's convention
# ---------------------------------------------------------------------------
def rect(left: int, top: int, width: int, height: int) -> dict[str, int]:
    """Build a rect from its top-left corner plus a size, in EA's convention.

    `top` is expected to be negative or zero; `bottom` comes out below it, which
    in EA means numerically smaller. Width and height must be positive - a
    zero-size rect is a bug, not a degenerate case worth supporting.
    """
    if width <= 0 or height <= 0:
        raise LayoutError(
            f"rect: width and height must both be positive, got "
            f"width={width}, height={height}"
        )
    return {"left": left, "top": top, "right": left + width, "bottom": top - height}


def rect_width(r: Mapping[str, int]) -> int:
    """Width of a rect: right - left."""
    return r["right"] - r["left"]


def rect_height(r: Mapping[str, int]) -> int:
    """Height of a rect: top - bottom, because EA's vertical axis is inverted."""
    return r["top"] - r["bottom"]


def rects_overlap(a: Mapping[str, int], b: Mapping[str, int]) -> bool:
    """True when two rects share positive area, in EA's flipped-y convention.

    Rects that merely touch along an edge do not overlap - abutting swimlanes
    are correct geometry, not a collision. The vertical test is the one that
    catches people out: `a` is above `b` when a's BOTTOM is at or above b's TOP,
    and "above" means numerically greater.
    """
    if a["right"] <= b["left"] or b["right"] <= a["left"]:
        return False
    if a["bottom"] >= b["top"] or b["bottom"] >= a["top"]:
        return False
    return True


def bounding_box(rects: Sequence[Mapping[str, int]]) -> dict[str, int]:
    """Smallest rect enclosing all of `rects`, plus its width and height.

    `top` is the MAXIMUM of the tops and `bottom` the minimum, because the
    visual top of an EA diagram is the coordinate nearest zero.
    """
    if not rects:
        raise LayoutError("bounding_box: needs at least one rect")
    return _bounds(rects)


def _bounds(rects: Sequence[Mapping[str, int]]) -> dict[str, int]:
    left = min(r["left"] for r in rects)
    right = max(r["right"] for r in rects)
    top = max(r["top"] for r in rects)
    bottom = min(r["bottom"] for r in rects)
    return {
        "left": left,
        "top": top,
        "right": right,
        "bottom": bottom,
        "width": right - left,
        "height": top - bottom,
    }


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------
def _as_int(value: Any, where: str) -> int:
    """Coerce a number to a whole EA unit, rejecting anything that is not one.

    bool is rejected on purpose: True would otherwise sail through as 1 and
    produce geometry nobody asked for.
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

    Order is the whole input here - band order is stacking order, item order is
    reading order - so a set or a bare dict is rejected rather than quietly
    iterated in whatever order it happens to have.
    """
    if isinstance(value, (str, bytes)) or not isinstance(value, Sequence):
        raise LayoutError(
            f"{where}: expected a list, got {type(value).__name__}"
        )
    return list(value)


def _resolve_spec(spec: Mapping[str, Any] | None) -> dict[str, Any]:
    """Validate a caller spec and fill in the defaults it left out.

    Unknown keys are an error. A typo like `itemWidth` would otherwise be
    ignored in silence and the caller would spend the afternoon wondering why
    their sizing had no effect.
    """
    out = dict(DEFAULT_SPEC)
    if spec is None:
        return out
    spec = _require_mapping(spec, "spec")

    unknown = sorted(k for k in spec if k not in DEFAULT_SPEC)
    if unknown:
        raise LayoutError(
            f"spec: unknown key(s) {', '.join(repr(k) for k in unknown)}; "
            f"valid keys are {', '.join(sorted(DEFAULT_SPEC))}"
        )

    for key, value in spec.items():
        where = f"spec.{key}"
        if key == "align":
            if value not in _ALIGNMENTS:
                raise LayoutError(
                    f"{where}: expected one of {_ALIGNMENTS}, got {value!r}"
                )
            out[key] = value
        elif key in _ANY_INT_KEYS:
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
        elif key in _OPTIONAL_POSITIVE_KEYS:
            if value is None:
                out[key] = None
            else:
                n = _as_int(value, where)
                if n <= 0:
                    raise LayoutError(
                        f"{where}: must be positive when given (or None to "
                        f"derive it), got {n}"
                    )
                out[key] = n
        else:  # pragma: no cover - only reachable if a default loses its class
            raise LayoutError(f"{where}: no validation rule for this key")
    return out


def _override(
    holder: Mapping[str, Any],
    key: str,
    spec: Mapping[str, Any],
    allowed: frozenset[str],
    where: str,
) -> Any:
    """Read a per-band / per-lane override, falling back to the spec value."""
    if key not in holder:
        return spec[key]
    if key not in allowed:  # pragma: no cover - guarded by caller's key list
        raise LayoutError(f"{where}.{key}: not overridable per band or lane")
    value = holder[key]
    if value is None and key in _OPTIONAL_POSITIVE_KEYS:
        return None
    n = _as_int(value, f"{where}.{key}")
    if n <= 0:
        raise LayoutError(f"{where}.{key}: must be positive, got {n}")
    return n


def _collect_items(
    raw: Any, where: str, seen: dict[str, str]
) -> list[Mapping[str, Any]]:
    """Validate one band's or lane's item list and its ids.

    Ids must be unique across the whole composition, not just within a band: the
    caller uses them to map rects back onto model elements, and a duplicate
    there means two elements silently sharing one rect.
    """
    items = _require_list(raw, where)
    out: list[Mapping[str, Any]] = []
    for j, raw_item in enumerate(items):
        out.append(_check_item(raw_item, f"{where}[{j}]", seen))
    return out


def _check_item(
    raw_item: Any, iwhere: str, seen: dict[str, str]
) -> Mapping[str, Any]:
    """Validate one item and claim its id. Shared by all three grammars.

    Pulled out of `_collect_items` so the nested grid, which meets its items one
    at a time while walking a tree rather than as a flat list, claims ids from
    the same registry with the same messages. Two grammars enforcing id
    uniqueness two ways is how one of them ends up not enforcing it.
    """
    item = _require_mapping(raw_item, iwhere)
    item_id = item.get("id")
    # Any hashable id is accepted and preserved VERBATIM -- ints as ints,
    # strings as strings. The primary consumer maps these back onto EA
    # element ids, which are integers, so demanding strings would force a
    # str() at every call site and invite the classic "123" != 123 bug when
    # the result is matched back against the model.
    if item_id is None or (isinstance(item_id, str) and not item_id.strip()):
        raise LayoutError(
            f"{iwhere}.id: every item needs a non-empty id, got {item_id!r}"
        )
    try:
        hash(item_id)
    except TypeError:
        raise LayoutError(
            f"{iwhere}.id: item id must be hashable so it can be checked "
            f"for uniqueness, got {type(item_id).__name__}"
        ) from None
    if item_id in seen:
        raise LayoutError(
            f"{iwhere}.id: duplicate item id {item_id!r}, already used at "
            f"{seen[item_id]}"
        )
    seen[item_id] = iwhere
    return item


def _named(holder: Mapping[str, Any], where: str) -> str:
    name = holder.get("name")
    if not isinstance(name, str) or not name.strip():
        raise LayoutError(
            f"{where}.name: a non-empty string name is required, got {name!r}"
        )
    return name


def _ceil_div(n: int, d: int) -> int:
    return -(-n // d)


# ---------------------------------------------------------------------------
# Grammar: layered_bands
# ---------------------------------------------------------------------------
def _band_metrics(band: Mapping[str, Any], spec: Mapping[str, Any], where: str) -> dict:
    """Resolve one band's sizing, honoring its own overrides.

    Item size is per band, never per item. Uniform sizing within a band is a
    quality rule: a row of boxes at four different widths reads as four
    different kinds of thing even when it is one kind, and a reader spends
    attention decoding the variation instead of the content.
    """
    item_w = _override(band, "item_width", spec, _BAND_OVERRIDES, where)
    item_h = _override(band, "item_height", spec, _BAND_OVERRIDES, where)
    label_h = _override(band, "label_height", spec, _BAND_OVERRIDES, where)
    wrap_w = _override(band, "wrap_width", spec, _BAND_OVERRIDES, where)

    h_pitch = _override(band, "h_pitch", spec, _BAND_OVERRIDES, where)
    if h_pitch is None:
        h_pitch = item_w + spec["item_gap_x"]
    row_pitch = _override(band, "row_pitch", spec, _BAND_OVERRIDES, where)
    if row_pitch is None:
        row_pitch = item_h + spec["item_gap_y"]

    if h_pitch < item_w:
        raise LayoutError(
            f"{where}: h_pitch ({h_pitch}) is smaller than item_width "
            f"({item_w}); items would overlap"
        )
    if row_pitch < item_h:
        raise LayoutError(
            f"{where}: row_pitch ({row_pitch}) is smaller than item_height "
            f"({item_h}); rows would overlap"
        )
    if wrap_w < item_w:
        raise LayoutError(
            f"{where}: wrap_width ({wrap_w}) is smaller than item_width "
            f"({item_w}); not even one item would fit on a row"
        )
    return {
        "item_width": item_w,
        "item_height": item_h,
        "label_height": label_h,
        "wrap_width": wrap_w,
        "h_pitch": h_pitch,
        "row_pitch": row_pitch,
    }


def _common_band_width(
    plans: Sequence[Mapping[str, Any]],
    pad_x: int,
    min_band_width: Optional[int],
    on_misfit: Optional[str],
) -> tuple[int, Optional[FitConflict]]:
    """One width for every band in the stack: the widest band's own demand.

    A band of two items sized to its own two items is visibly narrower than the
    band of three above it, and a stack of bands with a ragged right edge reads
    as a mistake in the drawing rather than as a fact about the content. It is
    the one defect that every arithmetic check passes: nothing overlaps, every
    rect is positive, the bounding box is right, and the picture still looks
    wrong. So the widest band's demand sets the width and the rest are drawn to
    it, with the slack left empty inside them.

    THIS IS THE OPPOSITE OF WHAT THE NESTED GRID DOES, and the difference is
    deliberate - do not tidy the two into agreement. There, a container keeps
    the size its contents need and is NOT stretched to fill its cell, because a
    grouping of four SHOULD be drawn bigger than a grouping of two: the size is
    the information, and snapping them to a common cell drew both at the same
    size and lied about where the weight was. Here the size is not information.
    A band is a full-width strip across the diagram, standing for a layer that
    spans it; how many items happen to populate the layer is already shown by
    the items, so spending the band's width on it says nothing and costs the
    straight edge. The rule is per grammar because the meaning of the rect is
    per grammar.

    Note what is NOT shared: a band's HEIGHT still follows its own contents, so
    a band of twelve wrapped over three rows is visibly taller than a band of
    one. The vertical axis is where this grammar carries its meaning.

    AN EXPLICIT `min_band_width` IS A REQUEST, NOT A VOTE. Without one the floor
    is derived per band from its own `item_width`, and taking the widest demand
    is all there is to decide. With one, a caller has stated a width on purpose -
    and a stated width narrower than the contents used to be outvoted in silence,
    which is the same defect as a box silently widened to fit a name. So it comes
    through `resolve_width_misfit`: widening still happens when nobody answers,
    the conflict is reported either way, and a caller relaying the user's
    `on_misfit="overlap"` gets the width it asked for with the items drawn past
    the band's right edge.

    Returns the width and the conflict, or `None` when there was none.
    """
    demanded = max(plan["content_demand"] for plan in plans)
    if min_band_width is None:
        derived_floor = max(plan["floor_width"] for plan in plans)
        return max(demanded, derived_floor), None

    widest = max(plans, key=lambda plan: plan["content_demand"])
    return resolve_width_misfit(
        "spec.min_band_width",
        requested_width=min_band_width,
        required_width=demanded,
        driver=widest["name"],
        driver_kind="band_contents",
        on_misfit=on_misfit,
        detail=(
            f"the {widest['name']!r} band's widest row is "
            f"{widest['content_demand'] - 2 * pad_x}px of items, which needs "
            f"{widest['content_demand']}px once its own {pad_x}px of padding "
            f"each side is added. Under {FIT_OVERLAP!r} the items keep that "
            f"size and are drawn past the band's right edge."
        ),
    )


def compose_layered_bands(
    bands: Sequence[Mapping[str, Any]],
    spec: Mapping[str, Any] | None = None,
    on_misfit: Optional[str] = None,
) -> dict[str, Any]:
    """Lay out horizontal bands stacked top to bottom.

    `bands` is an ordered list, first band at the top:

        [{"name": "Channels", "items": [{"id": "e1"}, {"id": "e2"}]},
         {"name": "Applications", "items": [...], "item_width": 180}]

    A band may carry `id` (used as its container id) and may override
    `item_width`, `item_height`, `h_pitch`, `row_pitch`, `wrap_width` and
    `label_height` for itself. Items carry `id` (required) and optionally
    `name`, which is passed through to the result.

    Behavior worth knowing:

    * Items run left to right, stepping by `h_pitch`, wrapping to a further row
      once a row would exceed `wrap_width`.
    * Every item in a band is the same size. Different bands may differ.
    * **Every band is the same WIDTH** - the widest band's - so the stack has one
      straight right edge. See `_common_band_width` for why this grammar shares
      a width where the nested grid deliberately does not.
    * A band's HEIGHT still follows its contents. Bands step down by
      `band_height + band_gap`, or by `band_pitch` if that is larger - which is
      how a configurable vertical pitch and content-driven height coexist.
    * An empty band keeps its label row rather than collapsing to nothing.
    * `align` is "left" (default) or "center", and governs where a ROW sits
      inside its band's content area. It no longer moves the bands themselves:
      they share a width, so they already share both edges.
    * An explicit `min_band_width` NARROWER than the contents is a conflict the
      result reports rather than settles. `on_misfit` is the user's answer to it:
      `"widen"` (the default when nobody answers) takes the width the contents
      need, `"overlap"` keeps the width that was asked for and lets the items be
      drawn past the band's right edge. Either way the conflict comes back in
      `result["conflicts"]`. **Ask the user which they want for that diagram** -
      see `FitConflict`, whose `question` field is the question to put.

    Returns the result dict described in the module docstring. Raises
    `LayoutError` for any input that cannot yield sane geometry.
    """
    check_misfit_answer("spec.min_band_width", on_misfit)
    s = _resolve_spec(spec)
    raw_bands = _require_list(bands, "bands")
    if not raw_bands:
        raise LayoutError("bands: at least one band is required, got an empty list")

    pad_x = s["band_pad_x"]
    pad_y = s["band_pad_y"]
    min_band_width = s["min_band_width"]

    seen_ids: dict[str, str] = {}
    plans: list[dict[str, Any]] = []

    for i, raw_band in enumerate(raw_bands):
        where = f"bands[{i}]"
        band = _require_mapping(raw_band, where)
        name = _named(band, where)
        m = _band_metrics(band, s, where)
        items = _collect_items(band.get("items", []), f"{where}.items", seen_ids)

        per_row = (m["wrap_width"] - m["item_width"]) // m["h_pitch"] + 1
        per_row = max(1, per_row)
        row_count = _ceil_div(len(items), per_row) if items else 0

        # Width of the widest row this band actually uses, so nothing is padded
        # out to the wrap width - `wrap_width` is where a row breaks, never a
        # width a band is entitled to. This is the band's OWN demand; the width
        # it is finally drawn at is the whole stack's, resolved below.
        widest_row_items = min(len(items), per_row) if items else 0
        content_width = (
            (widest_row_items - 1) * m["h_pitch"] + m["item_width"]
            if widest_row_items
            else 0
        )
        rows_height = (
            (row_count - 1) * m["row_pitch"] + m["item_height"] if row_count else 0
        )

        # Kept apart, because they answer different questions. `content_demand`
        # is what this band's own contents need and is the figure an explicit
        # `min_band_width` is measured against. `floor_width` is the DERIVED
        # floor, per band because `item_width` is: an empty band still has to be
        # wide enough for the item it would hold. An explicit `min_band_width`
        # replaces that derived floor - it does not stack with it - and is
        # resolved once for the whole stack in `_common_band_width`.
        content_demand = content_width + 2 * pad_x
        floor_width = m["item_width"] + 2 * pad_x
        # The label strip doubles as the band's top padding; pad_y is the gap
        # below the last row. An empty band therefore still stands label_height
        # + pad_y tall, which is the visible "label row" of an empty band.
        band_height = m["label_height"] + rows_height + pad_y

        plans.append({
            "band": band,
            "name": name,
            "index": i,
            "metrics": m,
            "items": items,
            "per_row": per_row,
            "row_count": row_count,
            "content_demand": content_demand,
            "floor_width": floor_width,
            "band_height": band_height,
        })

    band_width, conflict = _common_band_width(
        plans, pad_x, min_band_width, on_misfit)
    content_width = band_width - 2 * pad_x
    containers: list[dict[str, Any]] = []
    out_items: list[dict[str, Any]] = []

    band_top = s["origin_top"]
    for p in plans:
        m = p["metrics"]
        # Every band starts at the origin and ends at the same right edge. There
        # is deliberately no per-band horizontal offset here: `align` is spent
        # on the rows inside the band, not on the band.
        band_left = s["origin_left"]

        band_rect = rect(band_left, band_top, band_width, p["band_height"])
        container = {
            "id": p["band"].get("id") or f"band_{p['index']}",
            "name": p["name"],
            "kind": "band",
            "index": p["index"],
            "label": rect(band_left, band_top, band_width, m["label_height"]),
            **band_rect,
        }
        containers.append(container)

        content_left = band_left + pad_x
        items_top = band_top - m["label_height"]
        for j, item in enumerate(p["items"]):
            row, col = divmod(j, p["per_row"])
            items_this_row = min(p["per_row"], len(p["items"]) - row * p["per_row"])
            row_width = (items_this_row - 1) * m["h_pitch"] + m["item_width"]
            if s["align"] == "center":
                row_left = content_left + (content_width - row_width) // 2
            else:
                row_left = content_left

            r = rect(
                row_left + col * m["h_pitch"],
                items_top - row * m["row_pitch"],
                m["item_width"],
                m["item_height"],
            )
            record = {
                "id": item["id"],
                "container_id": container["id"],
                "band": p["name"],
                "band_index": p["index"],
                "index": j,
                "row": row,
                "column": col,
                **r,
            }
            if isinstance(item.get("name"), str):
                record["name"] = item["name"]
            out_items.append(record)

        step = p["band_height"] + s["band_gap"]
        if s["band_pitch"] is not None:
            step = max(step, s["band_pitch"])
        band_top -= step

    return {
        "grammar": "layered_bands",
        "items": out_items,
        "containers": containers,
        "bounds": _bounds([*containers, *out_items]),
        # Always present, so a consumer reads a list rather than testing for a
        # key. Empty is the answer "nothing had to be decided", which is a
        # different statement from "this engine does not report".
        "conflicts": [conflict] if conflict is not None else [],
    }


# ---------------------------------------------------------------------------
# Grammar: lanes
# ---------------------------------------------------------------------------
def _lane_metrics(lane: Mapping[str, Any], spec: Mapping[str, Any], where: str) -> dict:
    """Resolve one lane's item sizing. Uniform within the lane, as with bands."""
    return {
        "item_width": _override(lane, "item_width", spec, _LANE_OVERRIDES, where),
        "item_height": _override(lane, "item_height", spec, _LANE_OVERRIDES, where),
    }


def compose_lanes(
    lanes: Sequence[Mapping[str, Any]],
    spec: Mapping[str, Any] | None = None,
    orientation: str = "horizontal",
) -> dict[str, Any]:
    """Lay out swimlanes: parallel tracks, each carrying a sequence of items.

    `lanes` is an ordered list, first lane at the top (horizontal) or at the
    left (vertical):

        [{"name": "Customer", "items": [{"id": "a1"}, {"id": "a2"}]},
         {"name": "Operations", "items": [{"id": "b1"}]}]

    `orientation` is "horizontal" (lanes stack downward, items flow left to
    right) or "vertical" (lanes sit side by side, items flow downward). A lane
    may carry `id` and may override `item_width` and `item_height`.

    The invariant that earns this grammar its keep: **items at the same sequence
    index across different lanes line up on the flow axis.** Index 2 in every
    lane occupies the same slot, so a handoff from one lane to another reads as
    a step across rather than a step diagonally. Each slot is as long as the
    longest item at that index in any lane, and each item is centered in its
    slot; `slot_start` and `slot_extent` come back on every item so a caller can
    check the alignment itself.

    Other behavior worth knowing:

    * Lane thickness follows the largest item in that lane, across the lane.
    * Items are centered across the lane's thickness.
    * A lane's label area is reserved inside its container rect and returned as
      `label`; the container rect covers the whole lane, label included.
    * `lane_gap` defaults to 0, so lanes abut the way swimlanes normally do.
      Abutting rects touch but do not overlap.
    * An empty lane is valid and still gets a label area and its minimum
      thickness.

    Returns the result dict described in the module docstring. Raises
    `LayoutError` for any input that cannot yield sane geometry.
    """
    if orientation not in _ORIENTATIONS:
        raise LayoutError(
            f"orientation: expected one of {_ORIENTATIONS}, got {orientation!r}"
        )
    s = _resolve_spec(spec)
    raw_lanes = _require_list(lanes, "lanes")
    if not raw_lanes:
        raise LayoutError("lanes: at least one lane is required, got an empty list")

    horizontal = orientation == "horizontal"
    pad = s["lane_pad"]

    seen_ids: dict[str, str] = {}
    plans: list[dict[str, Any]] = []
    for i, raw_lane in enumerate(raw_lanes):
        where = f"lanes[{i}]"
        lane = _require_mapping(raw_lane, where)
        name = _named(lane, where)
        m = _lane_metrics(lane, s, where)
        items = _collect_items(lane.get("items", []), f"{where}.items", seen_ids)
        # Flow extent runs along the lane; cross extent runs across it.
        flow_extent = m["item_width"] if horizontal else m["item_height"]
        cross_extent = m["item_height"] if horizontal else m["item_width"]
        min_thickness = s["min_lane_thickness"]
        if min_thickness is None:
            min_thickness = cross_extent + 2 * pad
        thickness = max(cross_extent + 2 * pad, min_thickness)
        plans.append({
            "lane": lane,
            "name": name,
            "index": i,
            "metrics": m,
            "items": items,
            "flow_extent": flow_extent,
            "cross_extent": cross_extent,
            "thickness": thickness,
        })

    # One global slot table, shared by every lane. This is the alignment.
    slot_count = max(len(p["items"]) for p in plans)
    slot_extents = [
        max(
            (p["flow_extent"] for p in plans if len(p["items"]) > k),
            default=0,
        )
        for k in range(slot_count)
    ]
    slot_starts: list[int] = []
    cursor = 0
    for k, extent in enumerate(slot_extents):
        slot_starts.append(cursor)
        step = extent + s["item_gap_flow"]
        if s["flow_pitch"] is not None:
            step = max(step, s["flow_pitch"])
        cursor += step
    total_flow = (slot_starts[-1] + slot_extents[-1]) if slot_count else 0

    label_along_flow = s["label_width"] if horizontal else s["label_height"]
    lane_length = label_along_flow + pad + total_flow + pad

    containers: list[dict[str, Any]] = []
    out_items: list[dict[str, Any]] = []

    lane_left = s["origin_left"]
    lane_top = s["origin_top"]
    for p in plans:
        m = p["metrics"]
        thickness = p["thickness"]
        if horizontal:
            lane_rect = rect(lane_left, lane_top, lane_length, thickness)
            label = rect(lane_left, lane_top, s["label_width"], thickness)
            flow_origin = lane_left + s["label_width"] + pad
            cross_offset = (thickness - m["item_height"]) // 2
        else:
            lane_rect = rect(lane_left, lane_top, thickness, lane_length)
            label = rect(lane_left, lane_top, thickness, s["label_height"])
            flow_origin = lane_top - s["label_height"] - pad
            cross_offset = (thickness - m["item_width"]) // 2

        container = {
            "id": p["lane"].get("id") or f"lane_{p['index']}",
            "name": p["name"],
            "kind": "lane",
            "index": p["index"],
            "orientation": orientation,
            "label": label,
            **lane_rect,
        }
        containers.append(container)

        for k, item in enumerate(p["items"]):
            start = slot_starts[k]
            extent = slot_extents[k]
            lead = (extent - p["flow_extent"]) // 2  # center the item in its slot
            if horizontal:
                r = rect(
                    flow_origin + start + lead,
                    lane_top - cross_offset,
                    m["item_width"],
                    m["item_height"],
                )
                slot_start_abs = flow_origin + start
            else:
                r = rect(
                    lane_left + cross_offset,
                    flow_origin - start - lead,
                    m["item_width"],
                    m["item_height"],
                )
                slot_start_abs = flow_origin - start
            record = {
                "id": item["id"],
                "container_id": container["id"],
                "lane": p["name"],
                "lane_index": p["index"],
                "index": k,
                "slot_start": slot_start_abs,
                "slot_extent": extent,
                **r,
            }
            if isinstance(item.get("name"), str):
                record["name"] = item["name"]
            out_items.append(record)

        if horizontal:
            lane_top -= thickness + s["lane_gap"]
        else:
            lane_left += thickness + s["lane_gap"]

    return {
        "grammar": "lanes",
        "orientation": orientation,
        "items": out_items,
        "containers": containers,
        "bounds": _bounds([*containers, *out_items]),
    }


# ---------------------------------------------------------------------------
# Grammar: nested_grid
# ---------------------------------------------------------------------------
def _grid_metrics(
    node: Mapping[str, Any], spec: Mapping[str, Any], where: str
) -> dict:
    """Resolve the sizing one grid level applies to its own direct children.

    Held on the PARENT, never on the child, which is what makes "uniform within
    a level" structural rather than a rule a caller has to remember: a leaf has
    nowhere to state a size of its own, so siblings cannot disagree.
    """
    return {
        "item_width": _override(node, "item_width", spec, _GRID_OVERRIDES, where),
        "item_height": _override(node, "item_height", spec, _GRID_OVERRIDES, where),
        "label_height": _override(node, "label_height", spec, _GRID_OVERRIDES, where),
        "grid_columns": _override(node, "grid_columns", spec, _GRID_OVERRIDES, where),
    }


def _near_square_columns(n: int) -> int:
    """Columns for `n` cells so the grid comes out close to square.

    `ceil(sqrt(n))`, computed with integers because floating point at the
    boundary would make a 16-cell grid 5 columns wide on some machines and 4 on
    others, and this module promises the same output everywhere.
    """
    c = 1
    while c * c < n:
        c += 1
    return c


def _plan_grid(
    raw_children: Any,
    where: str,
    level: int,
    s: Mapping[str, Any],
    metrics: Mapping[str, Any],
    seen_items: dict[str, str],
    seen_groups: dict[str, str],
) -> dict[str, Any]:
    """Measure one grid bottom-up, returning its natural size and child plans.

    Recursive: a child carrying `items` is a container, and its natural size is
    whatever its own grid needs plus padding. Nothing is placed here - the tree
    has to be measured from the leaves up before anything can be positioned,
    because a container's size is its content's size.
    """
    children = _require_list(raw_children, where)
    plans: list[dict[str, Any]] = []

    for k, raw in enumerate(children):
        cwhere = f"{where}[{k}]"
        child = _require_mapping(raw, cwhere)
        # The presence of the `items` KEY is the discriminator, not its
        # truthiness: `items: []` is a deliberately empty container, and a
        # container that collapsed into a leaf when its last child was removed
        # would be a diagram that silently changed shape.
        if "items" in child:
            if level > s["max_grid_depth"]:
                raise LayoutError(
                    f"{cwhere}: nesting is {level} containers deep, and this "
                    f"grammar refuses more than max_grid_depth "
                    f"({s['max_grid_depth']}); past about three levels a reader "
                    f"can no longer tell which box owns which. Split the "
                    f"diagram, or raise spec.max_grid_depth deliberately"
                )
            name = _named(child, cwhere)
            group_id = child.get("id")
            if group_id is not None:
                if group_id in seen_groups:
                    raise LayoutError(
                        f"{cwhere}.id: duplicate container id {group_id!r}, "
                        f"already used at {seen_groups[group_id]}"
                    )
                if group_id in seen_items:
                    raise LayoutError(
                        f"{cwhere}.id: container id {group_id!r} is already "
                        f"used by an item at {seen_items[group_id]}; containers "
                        f"and items are both mapped back onto model elements, "
                        f"so one id cannot mean both"
                    )
                seen_groups[group_id] = cwhere
            cm = _grid_metrics(child, s, cwhere)
            inner = _plan_grid(
                child.get("items"), f"{cwhere}.items", level + 1, s, cm,
                seen_items, seen_groups,
            )
            plans.append({
                "kind": "container",
                "node": child,
                "name": name,
                "index": k,
                "metrics": cm,
                "inner": inner,
                "width": inner["grid_width"] + 2 * s["grid_pad"],
                "height": (cm["label_height"] + inner["grid_height"]
                           + 2 * s["grid_pad"]),
            })
        else:
            item = _check_item(child, cwhere, seen_items)
            plans.append({
                "kind": "item",
                "node": item,
                "index": k,
                "width": metrics["item_width"],
                "height": metrics["item_height"],
            })

    n = len(plans)
    if n:
        columns = metrics["grid_columns"]
        if columns is None:
            columns = _near_square_columns(n)
        columns = max(1, min(columns, n))
        rows = _ceil_div(n, columns)
        col_widths = [0] * columns
        row_heights = [0] * rows
        for k, p in enumerate(plans):
            r, c = divmod(k, columns)
            col_widths[c] = max(col_widths[c], p["width"])
            row_heights[r] = max(row_heights[r], p["height"])
        grid_width = sum(col_widths) + (columns - 1) * s["item_gap_x"]
        grid_height = sum(row_heights) + (rows - 1) * s["item_gap_y"]
    else:
        # An empty container keeps one cell's worth of space, so it stays a
        # visible labeled box that says "this grouping exists and is
        # deliberately unpopulated" instead of collapsing to its title.
        columns = rows = 0
        col_widths = []
        row_heights = []
        grid_width = metrics["item_width"]
        grid_height = metrics["item_height"]

    return {
        "plans": plans,
        "columns": columns,
        "rows": rows,
        "col_widths": col_widths,
        "row_heights": row_heights,
        "grid_width": grid_width,
        "grid_height": grid_height,
    }


def _place_grid(
    grid: Mapping[str, Any],
    left: int,
    top: int,
    s: Mapping[str, Any],
    metrics: Mapping[str, Any],
    depth: int,
    parent_id: Any,
    path: str,
    containers: list[dict[str, Any]],
    out_items: list[dict[str, Any]],
) -> None:
    """Place one already-measured grid with its content box at (`left`, `top`).

    Column widths and row heights come from the measure pass, so a container
    fills its cell and a leaf keeps its exact size centered in its cell. That
    split is the whole quality decision here: stretching leaves to their
    column's width would align the edges at the cost of the uniform-sizing rule,
    and the rule wins.
    """
    columns = grid["columns"]
    for k, p in enumerate(grid["plans"]):
        r, c = divmod(k, columns)
        cell_left = left + sum(grid["col_widths"][:c]) + c * s["item_gap_x"]
        cell_top = top - (sum(grid["row_heights"][:r]) + r * s["item_gap_y"])
        cell_w = grid["col_widths"][c]
        cell_h = grid["row_heights"][r]

        if p["kind"] == "container":
            cm = p["metrics"]
            child_path = f"{path}{k}"
            group_id = p["node"].get("id") or f"group_{child_path}"
            # A container keeps the size its CONTENTS need and is anchored at
            # its cell's top-left; it does not stretch to fill the cell. That
            # is the corpus's rule and it is worth the ragged edge it produces:
            # containers sized alike make a grouping of two look as important
            # as a grouping of twenty, which is the failure this grammar is
            # most often accused of. Snapping every container to its cell drew
            # a four-child capability and a two-child one at exactly the same
            # 324x192 -- tidier, and wrong about the thing the diagram is for.
            #
            # Leaves are the opposite case and stay centered in their cells:
            # they carry no content of their own to be sized by, so uniformity
            # is the only honest size for them.
            group_rect = rect(cell_left, cell_top, p["width"], p["height"])
            containers.append({
                "id": group_id,
                "name": p["name"],
                "kind": "group",
                "index": p["index"],
                "depth": depth,
                "parent_id": parent_id,
                "row": r,
                "column": c,
                "label": rect(cell_left, cell_top, p["width"],
                              cm["label_height"]),
                **group_rect,
            })
            _place_grid(
                p["inner"],
                cell_left + s["grid_pad"],
                cell_top - cm["label_height"] - s["grid_pad"],
                s, cm, depth + 1, group_id, f"{child_path}_",
                containers, out_items,
            )
        else:
            item_w = metrics["item_width"]
            item_h = metrics["item_height"]
            placed = rect(
                cell_left + (cell_w - item_w) // 2,
                cell_top - (cell_h - item_h) // 2,
                item_w,
                item_h,
            )
            record = {
                "id": p["node"]["id"],
                "container_id": parent_id,
                "depth": depth,
                "index": p["index"],
                "row": r,
                "column": c,
                **placed,
            }
            if isinstance(p["node"].get("name"), str):
                record["name"] = p["node"]["name"]
            out_items.append(record)


def compose_nested_grid(
    nodes: Sequence[Mapping[str, Any]],
    spec: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Lay out containers within containers, each as a grid of its children.

    `nodes` is the top level of a recursive tree. A node carrying `items` is a
    container and needs a `name`; a node without `items` is a leaf and needs an
    `id`:

        [{"name": "Retail", "items": [
            {"name": "Onboarding", "items": [{"id": 101}, {"id": 102}]},
            {"id": 103}]},
         {"name": "Payments", "items": [{"id": 104}]}]

    Containment is the only structure this grammar expresses. There is no
    sequence and usually no connectors - a nesting that also needs arrows to be
    read is a graph, and one of the other grammars or EA's own layout will serve
    it better.

    Behavior worth knowing:

    * **Grids come out close to square** - `ceil(sqrt(n))` columns - because a
      grouping rendered as one long row reads as a list and loses the grouping.
      Set `grid_columns` to fix a count; a container may set its own.
    * **Cell sizing is uniform within a level and may differ between levels.**
      Item size is stated by the PARENT (`item_width`, `item_height`, overridable
      per container for its own direct children, not cascading), so sibling
      leaves cannot disagree about their size - the one thing that most makes a
      generated diagram look machine-made.
    * **Containers are sized by their contents and nothing else.** A container
      with twenty children is visibly bigger than one with two - which is the
      whole point of drawing the grouping - so a container is NOT stretched to
      fill its cell, and a row of containers can end at different depths. Cells
      are still sized by the widest and tallest member of their column and row,
      so siblings never collide; the slack simply stays empty. A leaf keeps its
      exact size, centered in its cell.
    * **Padding is constant** (`grid_pad`) on every side, with the title strip
      (`label_height`) as an extra inset at the top, so a container's own name
      never sits on top of its children.
    * **Depth is bounded and a deeper tree is REFUSED**, not warned about:
      `max_grid_depth` defaults to 3 levels of containment. A warning would need
      a channel in the result that nothing reads; an error names the offending
      path, and a caller who genuinely wants four levels raises the bound
      deliberately. Leaves may sit at any level, including inside the deepest
      container.
    * An empty container keeps its label and one cell of space rather than
      collapsing, so the emptiness is visible and the author has to mean it.

    Item ids must be unique across the whole tree, as in the other grammars, and
    a container `id` may not collide with another container's or with an item's -
    both are mapped back onto model elements. Root-level leaves come back with
    `container_id: None`, since nothing encloses them.

    Returns the result dict described in the module docstring, with `depth`,
    `row`, `column` and `parent_id` on containers and `depth`, `row`, `column`
    and `container_id` on items. Raises `LayoutError` for any input that cannot
    yield sane geometry.
    """
    s = _resolve_spec(spec)
    raw_nodes = _require_list(nodes, "nodes")
    if not raw_nodes:
        raise LayoutError("nodes: at least one node is required, got an empty list")

    root_metrics = {
        "item_width": s["item_width"],
        "item_height": s["item_height"],
        "label_height": s["label_height"],
        "grid_columns": s["grid_columns"],
    }
    seen_items: dict[str, str] = {}
    seen_groups: dict[str, str] = {}
    grid = _plan_grid(nodes, "nodes", 1, s, root_metrics, seen_items, seen_groups)

    containers: list[dict[str, Any]] = []
    out_items: list[dict[str, Any]] = []
    _place_grid(
        grid, s["origin_left"], s["origin_top"], s, root_metrics,
        1, None, "", containers, out_items,
    )

    return {
        "grammar": "nested_grid",
        "items": out_items,
        "containers": containers,
        "bounds": _bounds([*containers, *out_items]),
    }


# ---------------------------------------------------------------------------
# Grammar: radial
# ---------------------------------------------------------------------------
def _refuse_radial_sizing(holder: Mapping[str, Any], where: str) -> None:
    """Refuse a spec key stated on a radial node, instead of ignoring it.

    THE DECISION THIS RECORDS: radial per-node sizing was DELETED, not wired up.

    A resolver helper and an allow-list of three keys used to sit here, between
    them making `item_width`, `item_height` and `radius` look settable per node.
    Nothing ever called the resolver. `_plan_ring` built every ring's sizing
    straight from the spec, so a caller who put `item_width` on a node got a
    composition that succeeded, reported nothing, and was byte-identical to the
    one without the key. Three keys accepted and discarded in silence. (Both
    names are deliberately not repeated here: a test asserts that nothing in the
    tools directory or the reference docs still mentions them.)

    WIRING THEM UP WAS THE ALTERNATIVE, AND IT WAS REJECTED, because the
    capability already exists next door and is better there.
    `compose_radial_tree` resolves exactly these three keys per node, and it
    also allocates angular room to a branch by the WEIGHT of what that branch
    carries rather than giving every branch the same wedge - which is the thing
    that makes per-ring sizing worth having, since a ring you can size but not
    give room to is a ring you have only half controlled. Wiring a second,
    weaker version in here would give callers two ways to size a radial tree, of
    which this one crowds its busiest branch. This grammar is a hub and its
    spokes: one ring of peers, sized by the spec, plus an optional outer ring.

    So the keys are gone, and stating one is an error. Accepting input and
    discarding it costs the caller a wrong diagram they believe is right;
    refusing it costs them one retry. `_cycle_item_height` makes the same call
    for the same reason, and states it at more length.
    """
    for key in holder:
        if key in DEFAULT_SPEC:
            raise LayoutError(
                f"{where}.{key}: this grammar sizes every ring from the spec, "
                f"so {key!r} cannot be stated per node - a ring of peers whose "
                f"members disagreed about their own size would read as several "
                f"kinds of thing. It was accepted and silently ignored until "
                f"now, which is why it is an error rather than a no-op. Move it "
                f"to the spec, or use compose_radial_tree, which does resolve "
                f"item_width, item_height and radius per node"
            )


def _polar(center_x: int, center_y: int, radius: float, degrees: float) -> tuple:
    """A point on a circle, rounded to whole EA units.

    Angles run CLOCKWISE from twelve o'clock, because that is how a reader
    describes one of these diagrams - "starting at the top and going round" -
    and matching the description costs nothing here while saving an inversion
    at every call site.

    EA's vertical axis is inverted, so a point ABOVE the center has a LARGER
    (less negative) y. Rounding is `int(round(...))`, applied once, to the
    coordinate rather than to the angle: rounding the angle first would let a
    ring of twelve drift visibly by the time it closed.

    `radius` is a float because the distances this grammar computes no longer
    come out whole: each item sits at its own distance, derived from where a
    ray at `degrees` leaves the boxes at both ends. Rounding still happens once,
    here, on the coordinate.
    """
    radians = math.radians(degrees - 90.0)
    return (int(round(center_x + radius * math.cos(radians))),
            int(round(center_y - radius * math.sin(radians))))


def _reach(item_w: int, item_h: int, degrees: float) -> float:
    """How far a box's own border sits from its center, along a ray at `degrees`.

    THIS IS THE WHOLE OF THE UNEQUAL-SPOKE FIX, so it is worth being explicit
    about what it computes and why that is the right quantity.

    A ray leaving the box's center at `degrees` (clockwise from twelve o'clock,
    as everywhere else here) leaves through either a horizontal or a vertical
    side, whichever it reaches first. Scaling the half-extent by the ray's
    component on that axis gives the distance to each candidate side, and the
    nearer one is the side actually crossed:

        horizontal sides, at half the height:  (h / 2) / |cos(degrees)|
        vertical sides,   at half the width:   (w / 2) / |sin(degrees)|

    For a 140x60 box that is 30 straight up, 70 straight out to the side, and
    76.2 - the half diagonal - through a corner. Which is exactly the spread
    that used to show up as unequal spokes: a box CENTERED on the ring pokes
    only 30 back toward the hub at the top and a full 70 at the side, so it
    stands off at the top and bottom and crowds the hub at the sides.

    A ray exactly along an axis has a zero component on the other one, so that
    candidate is dropped rather than divided by: at least one component of a
    unit vector is non-zero, so there is always a side left to cross.

    Note this measures along the RAY, which is not the same as the nearest point
    of the box to the center - for a box crossed near a corner the corner itself
    is closer. Along the ray is the right measure anyway, because a spoke is
    drawn along the ray and that is where the reader sees it end.

    A DELIBERATE APPROXIMATION: EVERY BORDER IS AN AXIS-ALIGNED RECTANGLE
    --------------------------------------------------------------------
    EA stores a rect per element and this reads that rect, so an element EA draws
    as a CIRCLE, an ellipse, a diamond or a rounded box is treated as the
    rectangle it is stored in. For a circle the true reach is CONSTANT - the
    radius, in every direction - and this returns the rectangle's, which varies.
    So a ring of circular elements, equalized by this function, bulges outward at
    the diagonals by exactly the spread of the rectangular reach:

        reach_spread(w, h) = (hypot(w, h) - min(w, h)) / 2

    Half a diagonal at the corner against half the shorter side on the axis. It is
    taken off BOTH ends of a spoke, so the center-to-center distance moves by twice
    it. For a square item of side d that is `d * (sqrt(2) - 1) / 2` per end and
    `d * (sqrt(2) - 1)` between centers - about 0.414 d - and NOT a percentage: the
    percentage depends on the radius the ring is drawn at. Measured on this
    composer, 8 square 120x120 items at `radius=300`: 420.0 center-to-center on the
    axes against 469.5 on the diagonals, a bulge of 49.5 units, 11.8% of the
    on-axis distance. The same items at `radius=229` with `d=150` give 379.0
    against 441.2, 16.4% - same 0.414 d, different share of a smaller radius.

    IT IS NOT FIXED HERE because nothing in the layout input says an element is a
    circle: the spec carries `item_width` and `item_height` and no shape, so this
    function cannot know. Fixing it means giving the composer a shape, which is a
    feature and not a correction.

    AND `lint.check_ring_spokes` IS NOT THE GUARD FOR IT. That rule measures the
    drawn spokes with this same rectangular model, so on a ring of circles it
    agrees with this function by construction and reports an even ring. So
    `reach_spread` is exported, and `compose_radial`'s result carries it, to state
    the error with the layout it applies to rather than leave it for a reader of
    the diagram to notice.
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

    Largest reach (half the diagonal, at the corner) less smallest (half the
    shorter side, on its axis). For an element EA draws as a RECTANGLE this is not
    an error at all - it is the real shape, and equalizing it is what `_reach` is
    for. For one EA draws as a CIRCLE, whose true reach is constant, it is exactly
    how far the ring bulges at the diagonals, per end; the center-to-center
    distance moves by twice it.

    This is the guard on that approximation: it makes the error a number a caller
    can read and a test can pin, rather than a paragraph. `compose_radial` reports
    it as `reach_spread` on every result. See `_reach` for the derivation and the
    measured figures.
    """
    return (math.hypot(item_w, item_h) - min(item_w, item_h)) / 2.0


def _min_reach(item_w: int, item_h: int) -> float:
    """The smallest `_reach` any ray can produce: half the shorter side.

    Reached straight along the axis of the shorter side, so it holds for a full
    circle. A partial sweep that never points that way reaches further, which
    makes this a floor for every sweep rather than only for a closed ring.
    """
    return min(item_w, item_h) / 2.0


def _max_reach(item_w: int, item_h: int) -> float:
    """The largest `_reach` any ray can produce: the half diagonal.

    The two candidates in `_reach` are equal along the corner ray, and that is
    where the minimum of the pair peaks - the ray leaves through the corner, so
    the distance is the corner's own.
    """
    return math.hypot(item_w / 2.0, item_h / 2.0)


def compose_radial(
    nodes: Sequence[Mapping[str, Any]],
    spec: Mapping[str, Any] | None = None,
    hub: Optional[Mapping[str, Any]] = None,
) -> dict[str, Any]:
    """Lay out items on a ring around a center: a hub and its spokes.

    `nodes` is the ring, in order. `hub`, when given, is the thing at the
    center - `{"id": ..., "name": ...}` - and is placed as an item rather than
    as a container, because it is one of the things on the diagram rather than
    something enclosing them:

        compose_radial(
            [{"id": 1}, {"id": 2}, {"id": 3}, {"id": 4}],
            hub={"id": 100, "name": "Customer"},
        )

    A node carrying `items` gets its own outer ring, laid out over the arc it
    occupies, which is what turns a hub-and-spoke into a radial tree.

    Behavior worth knowing:

    * **Angles run clockwise from twelve o'clock**, which is how a reader
      describes one of these. `start_angle` moves the first item.
    * **`sweep` is how much of the circle to use**, 360 by default. A smaller
      sweep gives a fan rather than a ring, and the items are spread across it
      INCLUSIVE of both ends - a 180-degree sweep of three items puts one at
      each end and one in the middle, which is what a half-circle of three is
      meant to look like. A full circle does not repeat the first position.
    * **Uniform sizing, stated by the SPEC.** Every ring in the composition
      takes `item_width`, `item_height` and `radius` from the spec, so siblings
      cannot disagree and neither can rings. A sizing key on a node - or on the
      hub - is REFUSED rather than ignored; `_refuse_radial_sizing` records why
      per-node sizing is not wired up here, and `compose_radial_tree` is the
      grammar to use when rings really must differ.
    * **Every spoke is the same length.** `radius` is the CLEAR GAP between the
      box at the middle and the box on the ring - the part of a spoke that gets
      drawn - not the distance to an item's center. Each item is pushed out by
      however far its own border reaches along its own ray, and by however far
      the box at the middle reaches along the same ray, so the gap between the
      two comes out equal all the way round whatever shape the boxes are. Item
      centers therefore do NOT all sit at one distance: see `_place_ring` and
      `_reach`.
    * **The radius is a floor, not a promise - and the widening is BOUNDED.**
      If the items would collide at the radius given, the ring is widened until
      they do not, and the radius actually used comes back on the result. A
      grammar that produced a deliberately overlapping ring because the caller
      passed a small number would be obeying the letter of the spec and drawing
      a bad diagram. But the widening does not limit itself - fitting n boxes
      into a fixed sweep needs a radius that grows with n and shrinks with the
      sweep - so it stops at `max_radius`, default 900, and REFUSES past it
      rather than returning a ring thousands of units across. See `_plan_ring`.
    * **Depth is bounded** by `max_ring_depth`, default 2, and a deeper tree is
      REFUSED rather than warned about - the same decision the nested grid
      makes, for the same reason: the result dict has no channel a warning
      could travel down that anything reads.

    THE CONNECTORS ARE NOT THIS GRAMMAR'S JOB, and for these diagrams that
    matters more than usual. Reference radial diagrams commonly use curved or
    arced connectors; the routing vocabulary available here has no arc, so a
    generated equivalent will carry straight or Bezier lines. The geometry is
    equivalent; the drawing is not identical, and saying so is part of using
    this grammar honestly.

    Returns the result dict described in the module docstring. Items carry
    `angle` and `ring`, so a caller can reason about the arrangement without
    recovering it from coordinates. Raises `LayoutError` for any input that
    cannot yield sane geometry.
    """
    s = _resolve_spec(spec)
    raw_nodes = _require_list(nodes, "nodes")
    if not raw_nodes:
        raise LayoutError("nodes: at least one node is required, got an empty list")

    seen_ids: dict[str, str] = {}
    out_items: list[dict[str, Any]] = []

    hub_item = None
    if hub is not None:
        hub_item = _check_item(hub, "hub", seen_ids)
        # The box at the middle is sized by the spec like everything else, so a
        # sizing key on it is the same silent discard `_refuse_radial_sizing`
        # exists to end, one call earlier.
        _refuse_radial_sizing(hub_item, "hub")

    # The center is chosen after the outermost radius is known, so the whole
    # composition can start at `origin_left`/`origin_top` like every other
    # grammar rather than at a center the caller has to compute.
    plan = _plan_ring(raw_nodes, "nodes", 1, s, seen_ids, float(s["sweep"]))
    hub_size = (s["item_width"], s["item_height"]) if hub_item is not None else None
    # A hub box pushes its whole ring out by its own reach, so the margin has to
    # allow for it or the composition would start left of `origin_left`.
    hub_reach = _max_reach(*hub_size) if hub_size is not None else 0.0
    extent = int(math.ceil(
        plan["outer_radius"] + hub_reach
        + max(plan["max_item_w"], plan["max_item_h"])
    ))
    center_x = s["origin_left"] + extent
    center_y = s["origin_top"] - extent

    if hub_item is not None:
        record = {
            "id": hub_item["id"],
            "container_id": None,
            "ring": 0,
            "angle": 0.0,
            "index": 0,
            **rect(center_x - s["item_width"] // 2,
                   center_y + s["item_height"] // 2,
                   s["item_width"], s["item_height"]),
        }
        if isinstance(hub_item.get("name"), str):
            record["name"] = hub_item["name"]
        out_items.append(record)

    _place_ring(plan, center_x, center_y, s, 1,
                hub_item["id"] if hub_item else None,
                s["start_angle"], s["sweep"], out_items, hub_size)

    return {
        "grammar": "radial",
        "items": out_items,
        "containers": [],
        "center": {"x": center_x, "y": center_y},
        "radius": plan["radius"],
        # The measured error in the rectangular border model, per spoke end. Zero
        # only for an item as tall as it is wide would be wrong - see `_reach`: a
        # SQUARE has the largest spread relative to its size. It is here so the
        # approximation travels with the layout it applies to; a caller placing
        # circular elements reads the bulge instead of discovering it on screen.
        "reach_spread": reach_spread(int(s["item_width"]), int(s["item_height"])),
        "bounds": _bounds(out_items),
    }


def _plan_ring(raw_nodes: Any, where: str, level: int, s: Mapping[str, Any],
               seen_ids: dict, sweep: float) -> dict:
    """Measure one ring and everything outside it, from the inside out.

    The SWEEP has to be known here, not only at placement, because it decides
    the angular step and therefore how far apart the items actually are. The
    first version widened the radius using the full-circle step on the reasoning
    that a closed ring is the tightest case. It is not: five items across a
    90-degree fan step 22.5 degrees apart where a full circle would step 72, so
    the fan collided while the ring was fine. Planning and placement now derive
    the angles from one function so they cannot disagree.
    """
    if level > s["max_ring_depth"]:
        raise LayoutError(
            f"{where}: nesting is {level} rings deep, and this grammar refuses "
            f"more than max_ring_depth ({s['max_ring_depth']}); a radial "
            f"diagram past two rings stops being readable from the center. "
            f"Split it, or raise spec.max_ring_depth deliberately"
        )
    children = _require_list(raw_nodes, where)
    if not children:
        raise LayoutError(f"{where}: a ring needs at least one node")

    metrics = {
        "item_width": s["item_width"],
        "item_height": s["item_height"],
        "radius": s["radius"],
    }
    plans = []
    for k, raw in enumerate(children):
        cwhere = f"{where}[{k}]"
        node = _require_mapping(raw, cwhere)
        _refuse_radial_sizing(node, cwhere)
        raw_inner = node.get("items") if "items" in node else None
        item = _check_item(node, cwhere, seen_ids)
        plans.append({"node": item, "index": k, "inner": None,
                      "raw_inner": raw_inner, "where": cwhere})

    count = len(plans)
    step = _angular_step(count, sweep)
    branch_sweep = min(abs(step) or abs(sweep), _MAX_BRANCH_SWEEP)

    # The radius is a floor. Widen it until neighbors on this ring cannot
    # touch: the chord between two of them, at the step actually used, must
    # clear the wider extent plus a gap.
    #
    # The chord is a distance between CENTERS, and `radius` is no longer one -
    # it is the clear gap outside the boxes, and each item's center sits at that
    # gap plus however far its own border reaches along its own ray. So the
    # constraint is solved for the center distance first and the gap read back
    # off it, using the SMALLEST reach any ray can produce. Using the smallest
    # is what makes this a floor and not a guess: every item's actual center
    # distance is at least the one the chord was solved for, never less, so a
    # ring can come out slightly roomier than it strictly needs but never
    # tighter. Sizing it off the reach an average item happens to have would put
    # the items that reach least inside the clearance.
    #
    # The parent box's own reach is left out of this even though placement adds
    # it, for the same reason: leaving it out can only push items further out.
    # It also keeps the ring's clearance independent of whether a hub was
    # supplied, so the same nodes do not get a different radius for it.
    # What the centers have to clear is the DIAGONAL, not the longer side. Two
    # axis-aligned boxes miss each other when they are apart by a full width
    # horizontally or a full height vertically, so two that are still inside both
    # of those are inside a box of w by h and therefore closer than its diagonal:
    # separation >= hypot(w, h) is exactly the condition that rules that out.
    # `max(w, h)` is not sufficient and is worst for a box that is nearly square,
    # where the diagonal is 41% longer than either side. A ring of 90x88 items
    # over a 60-degree fan overlapped at every count this way, and widening did
    # not rescue it: the radius grew to over 1500 and neighbors still touched,
    # because every widening step was measured against a distance that was never
    # going to be enough. Found by the aspect-ratio sweep in the tests, not by
    # the spoke work, and it predates it.
    need = math.hypot(metrics["item_width"], metrics["item_height"])
    need += s["item_gap_x"]
    reach_floor = _min_reach(metrics["item_width"], metrics["item_height"])
    radius = metrics["radius"]
    if count > 1 and step:
        half = math.radians(abs(step) / 2.0)
        if math.sin(half) > 0:
            need_centers = need / (2.0 * math.sin(half))
            radius = max(radius, int(math.ceil(need_centers - reach_floor)))

    # AND THE WIDENING IS BOUNDED, because on its own it never stops.
    #
    # The chord solved above is `need / (2 * sin(step / 2))` and `step` is the
    # sweep divided by the count, so the radius a ring demands grows about in
    # proportion to the number of items and inversely to the sweep it is given.
    # There is no count at which that arithmetic settles. Measured on 90x88
    # items over a 60-degree fan: 238 units at three items, 2046 at sixteen,
    # 3161 at twenty-four. At twenty-four the whole composition measures
    # 2873 x 1687 units, most of it the empty middle of a 60-degree fan. An
    # INNER ring is worse, because its branch sweep is itself a
    # fraction of the step: twelve spokes of three branches over a 90-degree fan
    # demanded 2384 on every inner ring, a number the result dict does not even
    # report. "Widen until they do not collide" was honest about the overlap and
    # silent about the size, and the size is what made the diagram unusable.
    #
    # THE ANSWER IS A REFUSAL, not a clamp and not an extra ring.
    #
    # A clamp would draw the overlap the widening exists to prevent, and draw it
    # silently: the caller would get touching neighbors and no signal. Wrapping
    # the overflow into a second ring would invent structure nobody asked for -
    # in this grammar ring 2 hangs off a NAMED ring-1 node and `container_id`
    # says which, so an engine-made ring would have to choose which items to
    # demote and nominate a parent the caller never chose. What is actually true
    # is that the sweep cannot hold this many boxes of this size, and only the
    # caller can decide which of the four inputs to give up. So say it.
    #
    # `compose_radial_tree` refuses the same failure, in the same words, once
    # its own widening budget is spent, so this is the engine's existing answer
    # to "too crowded for the sweep given" rather than a new one.
    #
    # A radius the CALLER stated is honored even past the bound: it is their own
    # number, in their own spec, and the defect being fixed is an engine-computed
    # radius they could not predict. The ceiling is therefore the larger of the
    # two, which leaves the radius bounded by the inputs either way.
    allowance = max(metrics["radius"], s["max_radius"])
    if radius > allowance:
        raise LayoutError(
            f"{where}: {count} items of "
            f"{metrics['item_width']}x{metrics['item_height']} spread over a "
            f"{abs(sweep):g}-degree sweep have to stand {radius} units clear of "
            f"the box at the middle before they stop colliding, and this "
            f"grammar refuses a ring past {allowance} (the larger of "
            f"spec.radius {metrics['radius']} and spec.max_radius "
            f"{s['max_radius']}); at {radius} every spoke would be "
            f"{radius} units of empty space. The sweep cannot hold this many "
            f"boxes "
            f"of this size, and which input to give up is yours: fewer items on "
            f"the ring, a wider sweep, smaller items, or spec.max_radius raised "
            f"deliberately. A tree whose branches carry unequal numbers of "
            f"children fits in far less room under compose_radial_tree, which "
            f"allocates the angular room by weight instead of giving every "
            f"branch the same wedge"
        )

    for entry in plans:
        if entry["raw_inner"] is not None:
            entry["inner"] = _plan_ring(
                entry["raw_inner"], f"{entry['where']}.items",
                level + 1, s, seen_ids, branch_sweep)

    # How far from this ring's center any of its items can have its own center:
    # the gap, plus the furthest its border can reach. An outer ring hangs off
    # one of those items and is measured from ITS center, so it adds that item's
    # reach once more - the same term placement adds for a parent box.
    reach_ceiling = _max_reach(metrics["item_width"], metrics["item_height"])
    centers_max = radius + reach_ceiling
    outer = centers_max
    for entry in plans:
        if entry["inner"]:
            outer = max(
                outer,
                centers_max + reach_ceiling + entry["inner"]["outer_radius"],
            )
    outer = int(math.ceil(outer))
    return {
        "plans": plans,
        "radius": radius,
        "outer_radius": outer,
        "metrics": metrics,
        "step": step,
        "branch_sweep": branch_sweep,
        "max_item_w": metrics["item_width"],
        "max_item_h": metrics["item_height"],
    }


def _angular_step(count: int, sweep: float) -> float:
    """Degrees between neighbors on a ring of `count` over `sweep`.

    A closed ring divides by the count, so the last item does not land back on
    the first. A partial sweep divides by one less, spreading the items
    INCLUSIVE of both ends - a half circle of three is one at each end and one
    in the middle, which is what a half circle of three should look like.
    """
    if count <= 1:
        return 0.0
    if abs(sweep) >= 360.0:
        return sweep / count
    return sweep / (count - 1)


def _place_ring(plan: Mapping[str, Any], center_x: int, center_y: int,
                s: Mapping[str, Any], ring: int, parent_id: Any,
                start_angle: float, sweep: float,
                out_items: list,
                parent_size: Optional[tuple] = None) -> None:
    """Place one measured ring, then anything hanging off it.

    EVERY SPOKE THE SAME LENGTH is the property being built here, and it is not
    what putting each item's center on a circle gives you. `radius` is the clear
    gap a reader sees between the box at the middle and the box on the ring, and
    an item's center goes wherever that gap requires:

        center distance = parent's reach + radius + item's own reach

    both reaches taken along that item's own ray, by `_reach`. The two terms are
    the stretches of the spoke that fall INSIDE a box and so are never drawn, so
    subtracting them is what leaves the visible part constant. Dropping the
    parent term and keeping the item's would equalize the distance from the
    center POINT to each near edge, which is a different quantity: with a
    140x60 box in the middle it leaves the drawn spokes varying by the hub's own
    46 units of reach, having removed the item's. The ink is what is looked at,
    so the ink is what is held constant.

    `parent_size` is the box at the middle, or None when there is no box there -
    a ring with no hub is measured from a bare point, and a bare point reaches
    nowhere. For an outer ring the box at the middle is the spoke item it hangs
    off, so the same arithmetic serves both without a special case.
    """
    plans = plan["plans"]
    metrics = plan["metrics"]
    radius = plan["radius"]
    # The step was decided during planning, because the radius depends on it.
    step = plan["step"]
    own_size = (metrics["item_width"], metrics["item_height"])

    for entry in plans:
        angle = start_angle + step * entry["index"]
        centers = radius + _reach(*own_size, angle)
        if parent_size is not None:
            centers += _reach(*parent_size, angle)
        x, y = _polar(center_x, center_y, centers, angle)
        record = {
            "id": entry["node"]["id"],
            "container_id": parent_id,
            "ring": ring,
            "angle": round(angle % 360.0, 3),
            "index": entry["index"],
            **rect(x - metrics["item_width"] // 2,
                   y + metrics["item_height"] // 2,
                   metrics["item_width"], metrics["item_height"]),
        }
        if isinstance(entry["node"].get("name"), str):
            record["name"] = entry["node"]["name"]
        out_items.append(record)

        if entry["inner"]:
            # An outer ring is centered on its parent and occupies the arc the
            # parent owns, so a radial tree's branches do not interleave.
            own_sweep = plan["branch_sweep"]
            inner_count = len(entry["inner"]["plans"])
            branch_start = angle - own_sweep / 2.0 if inner_count > 1 else angle
            _place_ring(entry["inner"], x, y, s, ring + 1,
                        entry["node"]["id"], branch_start, own_sweep,
                        out_items, own_size)

# ---------------------------------------------------------------------------
# Grammar: two_column_cycle
# ---------------------------------------------------------------------------
# What ONE ITEM may restate for itself here. This is the only grammar in this
# module that lets an item state any part of its own size, and the asymmetry is
# deliberate - see `_cycle_item_height` for the argument.
_CYCLE_ITEM_OVERRIDES = frozenset({"item_height"})


def _cycle_item_height(item: Mapping[str, Any], spec: Mapping[str, Any],
                       where: str) -> int:
    """One item's own height, falling back to the spec's.

    THE ONE PLACE IN THIS MODULE WHERE AN ITEM SIZES ITSELF, and the reason is
    not convenience.

    Every other grammar here refuses per-item sizing, on the rule stated in
    `_band_metrics`: a row of boxes at four different sizes reads as four
    different kinds of thing even when it is one kind. That rule is about
    variation that means NOTHING. A state carrying four lines of entry behavior
    is taller than a state carrying none because it holds more, exactly as a
    nested-grid container holding twenty children is bigger than one holding
    two, and forcing those to one height either clips the content or pads every
    box to the worst case. So the height here is content and is per item.

    The WIDTH is the opposite case and is shared by the whole cycle - see
    `compose_two_column_cycle`. Width carries nothing: a compartment wraps, and
    two columns of unequal width give the cycle a bent outline for no reason a
    reader could decode. Uniform where the size says nothing, per item where it
    says something, which is the same test `_common_band_width` applies and not
    a relaxation of it.

    A caller that states any OTHER spec key on an item is refused rather than
    ignored: `item_width` on an item is a plausible mistake, and silently
    dropping it would leave someone hunting for why their sizing had no effect.
    """
    for key in item:
        if key in DEFAULT_SPEC and key not in _CYCLE_ITEM_OVERRIDES:
            raise LayoutError(
                f"{where}.{key}: only "
                f"{', '.join(sorted(_CYCLE_ITEM_OVERRIDES))} may be stated per "
                f"item in this grammar. The width is shared by the whole cycle "
                f"so that both columns have one straight edge; set "
                f"spec.{key} to change it for every item"
            )
    if "item_height" not in item:
        return int(spec["item_height"])
    height = _as_int(item["item_height"], f"{where}.item_height")
    if height <= 0:
        raise LayoutError(
            f"{where}.item_height: must be positive, got {height}"
        )
    return height


def _cycle_split(count: int) -> int:
    """How many of `count` items run DOWN the first column.

    `ceil(count / 2)`, so an odd cycle spends its extra step on the way down.
    The first column then occupies rows 0..k-1 and the second occupies the
    BOTTOM `count - k` rows, reading upward - which is what keeps the FOLD, the
    step from the bottom of one column across to the bottom of the other, a
    horizontal hop at every count. For an odd count the empty cell is therefore
    the TOP of the return column, and the step that closes the loop is the
    diagonal one.

    That is a choice between two diagonals and it is worth recording which way
    it went, because both are defensible and nothing else in the code says so.
    One of the two turns HAS to be diagonal at an odd count: anchor the return
    column at the top instead and the closing step comes out horizontal while
    the fold comes out diagonal. The fold is an ordinary step in the sequence
    and wants to read as "and now across"; the closing step is already
    understood as "and back to the beginning" and survives being drawn at an
    angle. So the diagonal is spent on the edge whose meaning the reader already
    has.

    Integer arithmetic, not `math.ceil(count / 2)`: this module promises the
    same output on every machine and a float division at the boundary is how
    that promise gets broken.
    """
    return _ceil_div(count, 2)


def compose_two_column_cycle(
    items: Sequence[Mapping[str, Any]],
    spec: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Lay out a cycle as two columns: down one, back up the other.

    `items` is the cycle IN ORDER, first item at the top left:

        compose_two_column_cycle([
            {"id": 1, "name": "Idle"},
            {"id": 2, "name": "Requested", "item_height": 120},
            {"id": 3, "name": "Crossing", "item_height": 160},
            {"id": 4, "name": "Clearing"},
        ])

    The first `ceil(n / 2)` items run down the left column; the rest run up the
    right column, so the last item ends beside the first and the loop closes
    across the top. There are no containers - a cycle is a ring of peers and
    nothing encloses them - so `containers` comes back empty and every item's
    `container_id` is None.

    WHAT IT GUARANTEES, GIVEN THAT THE BOXES ARE DIFFERENT HEIGHTS
    --------------------------------------------------------------
    Variable heights are the point of this grammar rather than an awkwardness it
    tolerates: the diagrams it is for put multi-line entry and do behavior
    inside a box, and a box with four lines of it is taller than a box with
    none. A grammar that assumed one height would either clip that content or
    pad every box to the worst case. So three things are promised and a fourth
    is deliberately not:

    * **One WIDTH for every item**, `item_width`, and one column pitch. Both
      columns therefore have a straight left and a straight right edge, and the
      cycle has a rectangular outline. Width carries no information here - a
      compartment wraps - so spending it on content would be variation a reader
      has to decode for nothing. This is `_common_band_width`'s argument applied
      to the other axis.
    * **One row PITCH for the whole composition**, the tallest item plus
      `item_gap_y`. Equal pitch is the property a reader sees as rhythm, and it
      is the property the shipped linter measures: its spacing rule judges a
      column of unequal boxes on its CENTER-to-center pitch, so a scheme whose
      pitch followed each row's own tallest member would report as unevenly
      spaced however tidy it looked.
    * **Aligned CENTERS, not aligned tops.** Each item is centered in its row's
      slot, which is the pitch less the gap. Centers are what makes the pitch
      uniform - see the derivation below - and what makes the fold and the
      closing step come out horizontal, since row r in the left column and row r
      in the right column share a center line to within a unit of integer
      rounding. Aligning TOPS instead would leave the center pitch varying by
      half the difference between successive heights, which on the content this
      grammar is for is tens of units.
    * **NOT one size.** Two items of different heights are different sizes, so
      do not hand the whole cycle to the linter's uniform-sizing rule as a
      single role: that rule compares heights as well as widths and would read
      the content as a defect. Declare a role per height - the rule is explicit
      that the caller decides what a role is, and that two elements can share a
      place on the diagram and still be different roles. The shared width is the
      uniformity this grammar promises, and it is the part worth checking.

    THE CLEARANCE CONDITION, DERIVED RATHER THAN EYEBALLED
    ------------------------------------------------------
    Write `P` for the row pitch, `g` for `item_gap_y`, `S = P - g` for the slot
    height, and `h`, `h'` for the heights of two items in adjacent rows of one
    column. `S` is at least the tallest item by construction. An item is
    centered in its slot, so its top sits `(S - h) // 2` below the slot top, and
    the vertical clearance between the two is

        P - h - (S - h) // 2 + (S - h') // 2
          = g + ceil(a / 2) + floor(b / 2)       where a = S - h, b = S - h'

    which is **never less than `g`** whatever heights sit next to each other,
    and grows when either box is shorter than the slot. Non-adjacent rows are
    further apart again by at least one pitch. Across the columns the clearance
    is `h_pitch - item_width` at every row, so two items in different columns
    never overlap on the horizontal axis and their rows do not matter.

    That is the whole condition: two exact inequalities rather than a margin.
    Note which of the three ways of seating an item in its slot the derivation
    picked and why - top-aligned gives `g + a` and bottom-aligned gives exactly
    `g`, so all three clear, and centering was chosen for the PITCH property
    above and not for clearance. Getting that backwards is how a clearance rule
    ends up justified by the wrong quantity.

    Behavior worth knowing:

    * **`row_pitch` is a FLOOR, not a promise.** The tallest item is content,
      not spec, so a caller cannot be expected to state a pitch that clears it.
      A pitch too small for the tallest box is widened and the pitch actually
      used comes back on the result, the way `compose_radial` reports the radius
      it used. `h_pitch` is NOT treated that way: it and `item_width` are both
      spec values, so a pitch narrower than the width is the caller
      contradicting themselves and is refused.
    * **An odd count leaves the TOP of the return column empty**, so the fold at
      the bottom is horizontal and the closing step is the diagonal one. See
      `_cycle_split`.
    * **A cycle of one or two composes.** One item is a self-loop and two is a
      pair, both of which are real if unusual; neither is worth an error, and
      `columns` on the result says which happened.
    * The connectors are not this grammar's job, and that is worth saying out
      loud for a cycle: the arrangement is what makes the loop legible, but
      nothing here draws the loop. Route the vertical steps down each column,
      the fold across the bottom and the closing step back to the first item.

    Returns the result dict described in the module docstring, plus `rows`,
    `columns`, `row_pitch`, `column_pitch` and `item_width` - what it actually
    did, since the pitch may have been widened. Items carry `index` (position in
    the cycle), `column`, `row` and `leg` ("descent" or "return"). Raises
    `LayoutError` for any input that cannot yield sane geometry.
    """
    s = _resolve_spec(spec)
    raw_items = _require_list(items, "items")
    if not raw_items:
        raise LayoutError("items: at least one item is required, got an empty list")

    item_w = s["item_width"]
    gap_y = s["item_gap_y"]

    seen_ids: dict[str, str] = {}
    entries: list[dict[str, Any]] = []
    for i, raw_item in enumerate(raw_items):
        where = f"items[{i}]"
        item = _check_item(raw_item, where, seen_ids)
        entries.append({
            "item": item,
            "index": i,
            "height": _cycle_item_height(item, s, where),
        })

    column_pitch = s["h_pitch"]
    if column_pitch is None:
        column_pitch = item_w + s["item_gap_x"]
    if column_pitch < item_w:
        raise LayoutError(
            f"spec.h_pitch: {column_pitch} is smaller than item_width "
            f"({item_w}); the two columns would overlap"
        )

    tallest = max(e["height"] for e in entries)
    row_pitch = s["row_pitch"]
    if row_pitch is None:
        row_pitch = s["item_height"] + gap_y
    # The floor. Unlike `h_pitch` this is not the caller contradicting
    # themselves: the tallest box came from the content, so the pitch is widened
    # rather than refused, and the result says which pitch was used.
    row_pitch = max(row_pitch, tallest + gap_y)
    slot_height = row_pitch - gap_y

    descent = _cycle_split(len(entries))
    rows = descent

    out_items: list[dict[str, Any]] = []
    for e in entries:
        i = e["index"]
        if i < descent:
            column, row, leg = 0, i, "descent"
        else:
            # The return column is anchored at the BOTTOM row and read upward,
            # so the fold is always a horizontal hop. `_cycle_split` argues it.
            column, row, leg = 1, rows - 1 - (i - descent), "return"
        slot_top = s["origin_top"] - row * row_pitch
        record = {
            "id": e["item"]["id"],
            "container_id": None,
            "index": i,
            "column": column,
            "row": row,
            "leg": leg,
            **rect(
                s["origin_left"] + column * column_pitch,
                slot_top - (slot_height - e["height"]) // 2,
                item_w,
                e["height"],
            ),
        }
        if isinstance(e["item"].get("name"), str):
            record["name"] = e["item"]["name"]
        out_items.append(record)

    return {
        "grammar": "two_column_cycle",
        "items": out_items,
        "containers": [],
        "rows": rows,
        "columns": 1 if len(entries) == 1 else 2,
        "row_pitch": row_pitch,
        "column_pitch": column_pitch,
        "item_width": item_w,
        "bounds": _bounds(out_items),
    }


# ---------------------------------------------------------------------------
# Grammars that live in their own modules
# ---------------------------------------------------------------------------
# THE IMPORT IS AT THE BOTTOM ON PURPOSE, AND MOVING IT UP BREAKS THE BUILD.
# Each of these modules imports this one's public primitives (`LayoutError`,
# `rect`, `bounding_box`), so importing them at the top would be a cycle: this
# module would still be executing and those names would not exist yet. Down
# here everything this file defines is already bound, so the cycle resolves -
# `compose` is in `sys.modules` and complete enough for them to read.
#
# They are re-exported rather than left standalone because `bindings.py` derives
# what is IMPLEMENTED by reading `dir()` on this module for `compose_*` names.
# A grammar in its own file and not named here is a composer that exists and
# that nothing can find - which is exactly the "existing and reachable are
# different properties" trap this programme has hit four times.
from compose_matrix import compose_matrix          # noqa: E402,F401
from compose_radial_tree import compose_radial_tree  # noqa: E402,F401
from compose_chevron import compose_chevron_stack  # noqa: E402,F401
from compose_treemap import compose_treemap        # noqa: E402,F401

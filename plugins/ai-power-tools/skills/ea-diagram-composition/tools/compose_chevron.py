#!/usr/bin/env python3
"""The chevron-stack layout grammar: a value chain drawn as interlocking stages.

A standalone companion to `compose.py`, held to the same rules: plain data in,
rectangles out, no repository calls, no COM, no file or network I/O, no clock,
no randomness. Same input, same output, every time. It imports the shared rect
primitives and validators from `compose` rather than restating them - see
`_check_item` there, which says in as many words why two grammars must not
enforce id uniqueness two different ways.

EA's coordinate convention applies unchanged: `left`/`right` positive and
increasing rightward, `top`/`bottom` NEGATIVE and increasing upward, so
`height = top - bottom` and the visually topmost rect is the one with the
LARGEST `top`.

WHAT THIS GRAMMAR IS, AND THE ONE THING TO UNDERSTAND BEFORE USING IT
---------------------------------------------------------------------
A chevron stack is a row of arrow-shaped stages that interlock - each stage's
notch receiving the previous stage's point - usually with a band of supporting
strips above or below that spans the whole row.

The obvious question is how much each stage OVERLAPS its neighbor. **The answer
is: not at all.** The stages abut exactly, edge to edge, and the interlock is
drawn entirely by the element's own renderer, which paints outside the stored
rectangle on the right and insets its left edge by the same amount.

That is not a guess. The renderer's shape, in its own coordinate space where 100
is the element's width and 100 is its height, traces:

    (0,0) -> (100,0) -> (120,50) -> (100,100) -> (0,100) -> (20,50) -> (0,0)

The point at x=120 lies 20% of the width BEYOND the right edge; the notch vertex
at x=20 lies 20% INSIDE the left edge. A stage whose stored width is 80 is
therefore drawn 96 units wide, from x=0 to x=120% of 80, while occupying an 80
wide rectangle.

The arithmetic follows from that in one line. Write `W` for the stage width, `r`
for the notch depth as a fraction of `W`, and put stage `k` at `x_k`. Its notch
vertex is drawn at `x_k + rW` and its point at `x_k + W + rW`. Interlocking means
stage `k+1`'s notch vertex lands on stage `k`'s point:

    x_{k+1} + rW = x_k + W + rW      ==>      x_{k+1} - x_k = W

**The stage pitch equals the stage width exactly, and `r` cancels out.** How deep
the notch is does not enter into the spacing at all. Two consequences worth
stating separately, because each one is a way of getting this wrong:

* **The pitch is an EQUALITY, not a floor.** Every other composed grammar treats
  its pitch as a minimum and widens it when the content demands. Here, widening
  it opens a sliver of background between the point and the notch it was
  supposed to fill, and the picture stops being a chain - while nothing
  overlaps, every rect stays positive, and every shipped lint rule stays quiet.
  A pitch that is too large is the failure this grammar cannot be told about by
  any check downstream of it, so it is not offered as a knob. There is no
  `h_pitch` key.
* **Every stage must be the same WIDTH.** The notch depth is a proportion of
  each element's OWN width, so abutting a stage of width `w` against one of
  width `w'` leaves the point and the notch out of register by exactly
  `r * (w - w')`. Uniform width here is a geometric requirement, not the house
  style rule about variation that means nothing - though it happens to agree
  with it.

WHERE THOSE NUMBERS COME FROM
-----------------------------
Measured, not assumed. The value-chain example that ships with Sparx EA stores
its five stages at lefts 53, 133, 213, 293, 373 and rights 133, 213, 293, 373,
453: five rects 80 wide, pitch 80, every gap between one stage's right edge and
the next stage's left edge exactly 0. Its four supporting strips are 400 wide -
five stages of 80 - and 50 tall, abutting each other and abutting the stage row.
Rendering that same diagram and measuring the image back confirms the drawn
notch at 20% of the stored width. `test_compose_chevron.py` pins those numbers
as a test so that a later edit has to disagree with the reference out loud.

HOW ITS OUTPUT MUST BE DECLARED TO THE LINTER
----------------------------------------------
This matters enough to belong in the module docstring rather than a reference.

`check_no_overlaps` is satisfied without any special pleading: abutting rects
touch and do not overlap, and the rule exempts touching by design. Nothing needs
loosening, because the geometry genuinely does not overlap. A rule that fires on
correct output is worse than no rule, and this grammar never puts that rule in
that position.

`check_pitch_consistency` is the one to get right. It errors when elements
declared as a ROW have no whitespace between them, and it says why: a row with
no gaps anywhere in it does not read as a row. That verdict is correct about a
row - and a chevron stack is not one. Its members abut deliberately, the way
bands, lanes and pools do, and that rule's own documentation names the remedy:
deliberately abutting members are declared as a `stacks=` grouping, which no
spacing rule measures. So a caller passes

    stacks=[("horizontal", stage_objects), ("vertical", support_objects)]

and never `rows=`. The scope of the spacing rule is the declaration, not the
geometry - the same two boxes are a defect as a row and correct as a stack, and
only the caller knows which they are. Declaring the stage row as a stack also
gets it judged on the two properties it really does promise: one shared height
across the row, and one shared top edge.

Result shape
------------
    {
      "grammar":          "chevron_stack",
      "items":            [ {"id", "role", "left", "top", "right", "bottom",
                             ...}, ... ],
      "containers":       [],
      "stages":           how many stages,
      "supports":         how many supporting strips,
      "item_width":       the stage width,
      "item_height":      the stage height,
      "stage_pitch":      equal to `item_width`, always - reported so that the
                          equality above is visible on the output,
      "notch_percent":    the notch depth as a percent of the stage width,
      "notch_depth":      that depth in EA units,
      "text_width":       how much of a stage the renderer leaves for its name,
      "row_width":        stages * item_width - also the width of every strip,
      "support_height":   the strip height actually used,
      "support_position": "above" or "below",
      "drawn_right":      where the last stage's POINT lands, which is
                          `bounds.right + notch_depth`,
      "bounds":           {"left", "top", "right", "bottom", "width", "height"},
    }

There are no containers: a chain is a row of peers and a supporting strip
spans it rather than enclosing it, so nothing here encloses anything and every
item's `container_id` is None. Items carry `role`, which is "stage" or
"support", and that is the grouping to hand the linter's uniform-sizing rule.

`bounds` is the bounds of the STORED rects, as in every other grammar, because
that is what gets written to the repository. The ink extends `notch_depth`
further right than `bounds.right`, and `drawn_right` is that edge. Sizing a
canvas from `bounds` does not clip anything - image export follows the content -
but a caller placing something to the right of the chain wants `drawn_right`.

Connectors are not this grammar's job. A chain reads as a sequence because of
the interlock; drawing arrows between stages that already point at each other
is the usual way to make one of these unreadable.
"""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from compose import (
    LayoutError,
    _as_int,
    _check_item,
    _require_list,
    _require_mapping,
    bounding_box,
    rect,
)

__all__ = [
    "DEFAULT_CHEVRON_SPEC",
    "MAX_NOTCH_PERCENT",
    "compose_chevron_stack",
]


# ---------------------------------------------------------------------------
# Defaults
# ---------------------------------------------------------------------------
# Units are EA diagram units. This spec is deliberately its OWN dict rather than
# an extension of `compose.DEFAULT_SPEC`: a chevron stack has no wrap width, no
# radius, no sweep and no grid depth, and inheriting thirty keys it ignores
# would mean accepting `spec={"radius": 220}` in silence. Rejecting a key that
# does nothing is the whole reason the spec is validated at all.
#
# `None` means "derive it", as elsewhere in this engine.
DEFAULT_CHEVRON_SPEC: dict[str, Any] = {
    # Where the top-left of the composition goes. `origin_top` is negative
    # because EA's vertical axis is.
    "origin_left": 20,
    "origin_top": -20,

    # Stage size. Uniform across the whole row, and NOT overridable per stage -
    # see the module docstring for why that is geometry rather than taste. The
    # width is also the pitch.
    "item_width": 140,
    "item_height": 60,

    # How deep the renderer cuts the notch and how far it throws the point, as a
    # PERCENT of `item_width`. Percent rather than a fraction because that is
    # the unit the renderer's own shape is written in, and an integer percent
    # keeps this module's promise of integer geometry.
    "notch_percent": 20,

    # The band of supporting strips. Each strip spans the whole stage row.
    # `None` -> half the stage height: a supporting activity runs the length of
    # the chain rather than occupying a step in it, so drawing it as tall as a
    # stage makes it compete with the stages for the reader's attention.
    "support_height": None,
    # Strips abut each other and abut the stage row, which is what makes the
    # band read as one block rather than as a stack of separate bars.
    "support_gap": 0,
    # Which side of the stage row the band sits on.
    "support_position": "above",
}

# The deepest notch allowed. The HARD bound is 100: at 100 percent the notch
# vertex reaches the right edge and there is no body left to draw or to put a
# name in. The cap is set at half that because past 50 percent the notch crosses
# the stage's center line, the renderer is left reserving less than half the box
# for the name, and the shape stops reading as an arrow and starts reading as
# two triangles. The reference shape uses 20.
MAX_NOTCH_PERCENT = 50

_SUPPORT_POSITIONS = ("above", "below")

_ANY_INT_KEYS = frozenset({"origin_left", "origin_top"})
_POSITIVE_KEYS = frozenset({"item_width", "item_height", "notch_percent"})
_NON_NEGATIVE_KEYS = frozenset({"support_gap"})
_OPTIONAL_POSITIVE_KEYS = frozenset({"support_height"})


def _resolve_spec(spec: Mapping[str, Any] | None) -> dict[str, Any]:
    """Validate a caller spec and fill in the defaults it left out.

    Unknown keys are an error, for the reason `compose._resolve_spec` gives: a
    typo like `itemWidth` would otherwise be ignored in silence. The message
    names `h_pitch` specially, because a caller reaching for it has a real
    misunderstanding to correct rather than a typo to fix.
    """
    out = dict(DEFAULT_CHEVRON_SPEC)
    if spec is None:
        return out
    spec = _require_mapping(spec, "spec")

    unknown = sorted(k for k in spec if k not in DEFAULT_CHEVRON_SPEC)
    if unknown:
        hint = ""
        if "h_pitch" in unknown:
            hint = (
                "; 'h_pitch' is not a key of this grammar - the stage pitch "
                "equals item_width exactly, because a wider pitch opens a gap "
                "between one stage's point and the next one's notch"
            )
        raise LayoutError(
            f"spec: unknown key(s) {', '.join(repr(k) for k in unknown)}; "
            f"valid keys are {', '.join(sorted(DEFAULT_CHEVRON_SPEC))}{hint}"
        )

    for key, value in spec.items():
        where = f"spec.{key}"
        if key == "support_position":
            if value not in _SUPPORT_POSITIONS:
                raise LayoutError(
                    f"{where}: expected one of {_SUPPORT_POSITIONS}, "
                    f"got {value!r}"
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

    if out["notch_percent"] > MAX_NOTCH_PERCENT:
        raise LayoutError(
            f"spec.notch_percent: {out['notch_percent']} is deeper than the "
            f"{MAX_NOTCH_PERCENT} percent this grammar allows; past half the "
            f"stage width the notch crosses the stage's center line and the "
            f"shape stops reading as an arrow"
        )
    return out


def _notch_depth(item_width: int, notch_percent: int, where: str) -> int:
    """The notch depth in EA units, and a refusal when it rounds away.

    Integer division, not a float scaled at the end: this module promises the
    same output on every machine, and the depth is reported to the caller and
    used to derive the name area, so it has to be one whole number rather than
    something re-derived differently downstream.

    A depth of zero is refused rather than accepted as "a very shallow notch",
    because it is the one value at which the grammar stops being this grammar:
    the point and the notch both vanish and the result is a row of plain
    abutting rectangles, which is a different picture that should be asked for
    by a different name.
    """
    depth = item_width * notch_percent // 100
    if depth <= 0:
        raise LayoutError(
            f"{where}: item_width {item_width} at notch_percent "
            f"{notch_percent} gives a notch {depth} units deep, so no chevron "
            f"would be drawn; widen item_width or deepen notch_percent"
        )
    return depth


def _refuse_item_overrides(item: Mapping[str, Any], where: str) -> None:
    """No item sizes itself in this grammar, and a try is refused, not ignored.

    `compose_two_column_cycle` allows exactly one per-item override and argues
    for it: a state box is taller when it holds more, so its height is content.
    Nothing here is that case. The stage width is the pitch AND the notch depth,
    so a per-stage width breaks the interlock (see the module docstring); the
    stage height is what makes the chain one solid band; and a strip that is
    taller than its neighbors stops the supporting band reading as one block.

    Refused rather than ignored for the reason `compose._resolve_spec` refuses
    an unknown spec key: a sizing that silently has no effect costs somebody an
    afternoon.
    """
    stated = sorted(k for k in item if k in DEFAULT_CHEVRON_SPEC)
    if stated:
        raise LayoutError(
            f"{where}.{stated[0]}: no size may be stated per item in this "
            f"grammar - the stage width is also the pitch and the notch depth, "
            f"so one shared size is what makes the stages interlock. Set "
            f"spec.{stated[0]} to change it for the whole composition"
        )


def _support_height(spec: Mapping[str, Any]) -> int:
    """The strip height: the caller's, or half a stage."""
    stated = spec["support_height"]
    if stated is not None:
        return int(stated)
    derived = int(spec["item_height"]) // 2
    if derived <= 0:
        raise LayoutError(
            f"spec.support_height: deriving it as half of item_height "
            f"({spec['item_height']}) gives {derived}, which is not a height; "
            f"state spec.support_height outright"
        )
    return derived


def compose_chevron_stack(
    stages: Sequence[Mapping[str, Any]],
    supports: Sequence[Mapping[str, Any]] | None = None,
    spec: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Lay out a chain of interlocking chevron stages, with a supporting band.

    `stages` is the chain IN ORDER, first stage at the left. `supports` is the
    band of strips that spans the chain, first strip nearest the outside edge of
    the composition - which for the default `support_position` of "above" means
    first strip at the top:

        compose_chevron_stack(
            stages=[{"id": 1, "name": "Acquire"},
                    {"id": 2, "name": "Underwrite"},
                    {"id": 3, "name": "Service"}],
            supports=[{"id": 10, "name": "Risk and Compliance"},
                      {"id": 11, "name": "Technology"}],
            spec={"item_width": 80, "item_height": 100},
        )

    Both lists hold items carrying `id` (required, unique across the whole
    composition) and optionally `name`, which is passed through. There are no
    per-item overrides in this grammar at all - not even the one
    `compose_two_column_cycle` allows - because both of its sizes are load
    bearing: the stage width sets the pitch AND the notch depth, and the strips
    share a height so the band reads as one block.

    Behavior worth knowing:

    * **Stages abut. The pitch is `item_width`, exactly, and is not a knob.**
      The interlock is drawn by the renderer outside the stored rect; see the
      module docstring for the derivation and for what a wider pitch costs.
    * **Every strip spans the whole row**, `stages * item_width` wide, and every
      strip starts at `origin_left`. So the band and the chain share both
      vertical edges, which is what a supporting activity spanning the chain
      means.
    * **Strips abut each other and abut the stage row**, unless `support_gap`
      says otherwise.
    * **A chain of one composes.** One stage is a degenerate chain but a real
      one, and `stages` on the result says so.
    * **The band is optional.** Omit `supports`, or pass an empty list, and the
      composition is the stage row alone.
    * Declare the output to the linter as STACKS, never as rows. The module
      docstring says why, and it is the difference between a clean report and a
      spacing error on correct geometry.

    Returns the result dict described in the module docstring. Raises
    `LayoutError` for any input that cannot yield sane geometry.
    """
    s = _resolve_spec(spec)

    raw_stages = _require_list(stages, "stages")
    if not raw_stages:
        raise LayoutError(
            "stages: at least one stage is required, got an empty list"
        )
    raw_supports = _require_list(supports if supports is not None else [],
                                 "supports")

    seen_ids: dict[str, str] = {}
    stage_items = []
    for i, raw in enumerate(raw_stages):
        where = f"stages[{i}]"
        item = _check_item(raw, where, seen_ids)
        _refuse_item_overrides(item, where)
        stage_items.append(item)
    support_items = []
    for i, raw in enumerate(raw_supports):
        where = f"supports[{i}]"
        item = _check_item(raw, where, seen_ids)
        _refuse_item_overrides(item, where)
        support_items.append(item)

    item_w = int(s["item_width"])
    item_h = int(s["item_height"])
    notch_percent = int(s["notch_percent"])
    notch_depth = _notch_depth(item_w, notch_percent, "spec.item_width")
    text_width = item_w - notch_depth

    support_h = _support_height(s)
    support_gap = int(s["support_gap"])
    position = s["support_position"]

    origin_left = int(s["origin_left"])
    origin_top = int(s["origin_top"])

    row_width = len(stage_items) * item_w
    support_step = support_h + support_gap
    band_extent = len(support_items) * support_step  # includes the trailing gap

    if position == "above":
        stage_top = origin_top - band_extent
        first_support_top = origin_top
    else:
        stage_top = origin_top
        first_support_top = origin_top - item_h - support_gap

    out_items: list[dict[str, Any]] = []

    for k, item in enumerate(stage_items):
        left = origin_left + k * item_w
        record = {
            "id": item["id"],
            "container_id": None,
            "role": "stage",
            "index": k,
            # Where the renderer puts the two features that do the interlocking.
            # `point_x` of one stage equals `notch_x` of the next, by
            # construction, and a caller can check that without re-deriving it.
            "notch_x": left + notch_depth,
            "point_x": left + item_w + notch_depth,
            # What the renderer leaves for the name, once the notch has taken
            # its bite out of the left of the box.
            "text_left": left + notch_depth,
            "text_width": text_width,
            **rect(left, stage_top, item_w, item_h),
        }
        if isinstance(item.get("name"), str):
            record["name"] = item["name"]
        out_items.append(record)

    for k, item in enumerate(support_items):
        record = {
            "id": item["id"],
            "container_id": None,
            "role": "support",
            "index": k,
            **rect(origin_left, first_support_top - k * support_step,
                   row_width, support_h),
        }
        if isinstance(item.get("name"), str):
            record["name"] = item["name"]
        out_items.append(record)

    bounds = bounding_box(out_items)
    return {
        "grammar": "chevron_stack",
        "items": out_items,
        "containers": [],
        "stages": len(stage_items),
        "supports": len(support_items),
        "item_width": item_w,
        "item_height": item_h,
        # Reported although it is always `item_width`, because the equality is
        # the whole grammar and a reader of the result should not have to take
        # it on trust.
        "stage_pitch": item_w,
        "notch_percent": notch_percent,
        "notch_depth": notch_depth,
        "text_width": text_width,
        "row_width": row_width,
        "support_height": support_h,
        "support_position": position,
        # The ink, not the rect: the last stage's point lands here.
        "drawn_right": origin_left + row_width + notch_depth,
        "bounds": bounds,
    }

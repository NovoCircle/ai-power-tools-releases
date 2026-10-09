#!/usr/bin/env python3
"""Check a generated diagram before anyone is shown it.

This is the check half of the generate-check-correct loop. It consumes exactly
what `verify_diagram` returns and makes no repository calls of its own, so it
can run anywhere the verify payload can be carried.

LANGUAGE-NEUTRAL BY CONSTRUCTION
---------------------------------
Every rule reads geometry and presentation - rects, sizes, routes, fills - and
nothing reads the metamodel. No notation name, no technology id, no element
classification branches anything here. That is what lets one linter serve every
modeling language, including one nobody has written a binding for: "these boxes
overlap" and "these connectors cross needlessly" are not metamodel questions.

The module is held to the same bar as the layout engine, and a test enforces it
over identifiers AND string constants - including these docstrings. Naming a
language even in prose is how the first special case gets justified later.

The same property is why this module does not import `bindings`. A binding's
presentation profile is translated to a plain mapping by the CALLER and handed
in as `profile=`; see `PROFILE_KEYS`. A test asserts the import is absent,
because the boundary is the design.

WHAT A CLEAN REPORT MEANS
-------------------------
"No defect this linter knows how to measure." It is NOT a claim that the
diagram reads well. Known blind spots are listed in
`references/verification.md` and kept there deliberately, so that a clean
report is never quoted as more than it is.

EA COORDINATES
--------------
`top` and `bottom` are negative and `top > bottom`, so `height = top - bottom`.
`_normalize_rect` is the only function here that reasons about it; everything
else works in the conventional top-left-origin space it returns.
"""
from __future__ import annotations

import math
import re
from dataclasses import dataclass, field
from typing import Any, Iterable, Mapping, Optional, Sequence

__all__ = [
    "Finding",
    "LintReport",
    "PROFILE_KEYS",
    "SUPPRESSED_BY",
    "MAX_CORRECTION_PASSES",
    "SIZE_TOLERANCE",
    "PITCH_TOLERANCE",
    "ANGLE_TOLERANCE",
    "STACK_AXES",
    "lint_diagram",
    "check_no_overlaps",
    "check_within_canvas",
    "check_uniform_sizing",
    "check_pitch_consistency",
    "check_stack_extents",
    "check_stack_alignment",
    "check_ring_spokes",
    "check_ring_angles",
    "check_routing",
    "check_crossings",
    "check_color_is_explained",
    "check_title_present",
    "check_connector_labels",
    "check_collapsed_connectors_annotated",
    "check_labels_fit",
    "is_stalled",
    "LABEL_MARGIN",
]

# A size difference under this many units is not an inconsistency - EA nudges
# geometry, and flagging a 2-unit delta would make the rule noise.
SIZE_TOLERANCE = 4

# Likewise for spacing, judged on the SPREAD rather than on exact equality.
PITCH_TOLERANCE = 8

# The same claim - "these are evenly spaced" - made about an ANGLE, and it needs
# a constant of its own because it is in DEGREES. Reusing PITCH_TOLERANCE would
# be a unit confusion that happens to run.
#
# CALIBRATED, NOT PICKED. Two measurements bound it, both taken over the ring
# layouts the composition engine actually produces - 6300 of them, counts 2 to
# 15, eight sweeps, four start angles, three radii, five item shapes:
#
# * ROUNDING puts the worst spread of the angular steps between neighbors at
#   0.78 degrees. That is the cost of placing a center on whole units.
# * A NUDGE is larger. EA moves geometry by a few units, and 4 units is the
#   nudge this file already tolerates as a size (SIZE_TOLERANCE). The tightest
#   center-to-center distance any of those layouts produces is 132 units, where
#   4 units across the ray is 1.74 degrees - so two neighbors nudged opposite
#   ways move one step by 3.47.
#
# 4 covers the nudge with the rounding inside it. The defects this exists for
# are tens of degrees: the smallest measured one is a spread of 60. So the
# boundary sits anywhere in (3.5, 60), and 4 is taken from the noise end
# deliberately - a floor's job is to stay quiet on correct output, and there is
# no measured defect anywhere near the bottom of that interval to argue for
# more room.
ANGLE_TOLERANCE = 4

# The two directions a group can be read in, and the vocabulary for both the
# stack rules and the spacing rule. "vertical" is read top to bottom and
# "horizontal" left to right, in both cases - so a vertical STACK's members
# should share a width, and a vertical spacing group is a column whose spacing
# is measured down the y axis.
#
# An axis is the CALLER's to state, not something read off the coordinates:
# three bands that happen to be tall and narrow look like a horizontal stack and
# are a vertical one, and inferring it would be guessing at what the diagram is
# for.
STACK_AXES = ("vertical", "horizontal")

# How close a label may come to its element's border before it reads as
# touching it. Calibrated against a real generated diagram rather than chosen:
# on a capability map it separates exactly the two names that look wrong
# (margins of 5 and 6) from the next-tightest box at 10, so the boundary sits
# anywhere in (6, 10) and 8 is the midpoint.
LABEL_MARGIN = 8

# Element kinds that can carry a grouping's name, and that can serve as a drawn
# title. Plain EA type names, available in every notation - this is not a
# metamodel branch, it is the vocabulary EA itself uses for `Object_Type`.
_CONTAINER_TYPES = frozenset({"boundary", "package", "grouping"})
_TITLE_TYPES = frozenset({"text", "note", "boundary"})

# Words that count as annotating a deliberate simplification.
_ANNOTATION_WORDS = ("collaps", "combined", "merged", "aggregated",
                     "simplified", "summar")

_MIN_BOX = 20.0          # smaller SVG rects are decoration, not elements
# How far the drawn box may exceed the stored rect before it is worth saying.
# EA's border and shadow account for a few pixels either way; a name that does
# not fit adds tens.
_RENDER_SLACK = 6.0
_BASELINE_SLACK = 6.0    # a baseline may sit just below the box and still fit

_SVG_TEXT_RE = re.compile(
    r'<text\s+x="(?P<x>[-\d.]+)"\s+y="(?P<y>[-\d.]+)"'
    r'(?:\s+textLength="(?P<tl>[-\d.]+)")?'
    r'(?P<attrs>[^>]*)>(?P<body>.*?)</text>',
    re.DOTALL,
)
_SVG_RECT_RE = re.compile(
    r'<rect\s+x="(?P<x>[-\d.]+)"\s+y="(?P<y>[-\d.]+)"\s+'
    r'width="(?P<w>[-\d.]+)"\s+height="(?P<h>[-\d.]+)"'
)
_ENTITIES = (("&amp;", "&"), ("&lt;", "<"), ("&gt;", ">"),
             ("&quot;", '"'), ("&apos;", "'"))


def _kind_of(obj: Mapping[str, Any]) -> str:
    return (obj.get("type") or "").strip().lower()


def _looks_like_annotation(text: Optional[str]) -> bool:
    lowered = (text or "").lower()
    return any(word in lowered for word in _ANNOTATION_WORDS)


# How many correction passes the loop may take before it must stop and say so.
# A loop that keeps going until it is happy either terminates or lies; this one
# terminates. `is_stalled` is how a caller detects the other failure - passes
# that change nothing - without waiting for the budget to run out.
MAX_CORRECTION_PASSES = 3

# The presentation keys this linter understands. A caller builds this mapping
# from whatever it uses to describe a view; from a binding's profile it is:
#
#     profile = {**p.display_settings(), "collapses_parallel": p.collapses_parallel}
#
# Anything else in the mapping is ignored rather than rejected, because a
# profile vocabulary is allowed to grow without breaking the linter.
PROFILE_KEYS = (
    "hide_connector_labels",
    "hide_element_stereotypes",
    "hide_connector_stereotypes",
    "show_element_notes",
    "hide_attribute_types",
    "hide_operation_return_types",
    "hide_operation_brackets",
    "collapses_parallel",
)

# Rules a profile deliberately makes moot. This table is the whole of
# profile-awareness, and it is a table rather than a branch so that it can be
# read, tested exhaustively, and extended without touching a rule.
#
# The reason this is a correctness requirement and not a nicety: a linter that
# rejects every executive view gets switched off, and a switched-off linter
# protects nothing.
SUPPRESSED_BY: dict[str, str] = {
    "missing-connector-labels": "hide_connector_labels",
}


@dataclass(frozen=True)
class Finding:
    """One thing wrong, stated so it can be acted on rather than just read."""

    rule: str
    severity: str            # "error" | "warning" | "info"
    message: str
    subjects: tuple = ()     # element ids / connector ids involved
    correction: str = ""     # what to do about it

    def __str__(self) -> str:
        where = f" {list(self.subjects)}" if self.subjects else ""
        return f"[{self.severity}] {self.rule}{where}: {self.message}"


@dataclass
class LintReport:
    findings: list[Finding] = field(default_factory=list)
    metrics: dict = field(default_factory=dict)
    suppressed: list[str] = field(default_factory=list)
    # Rules that could not run, and why. Distinct from `suppressed`, which is a
    # deliberate choice: this is a rule that WANTED to run and lacked its
    # input. A clean report with entries here has checked less than it looks.
    not_run: list[str] = field(default_factory=list)

    @property
    def errors(self) -> list[Finding]:
        return [f for f in self.findings if f.severity == "error"]

    @property
    def warnings(self) -> list[Finding]:
        return [f for f in self.findings if f.severity == "warning"]

    @property
    def clean(self) -> bool:
        """No ERRORS. Warnings and info are reported and do not block.

        Deliberately not "no findings at all": several warnings here fire on
        diagrams that are correct for their context, and a bar nobody can clear
        is a bar nobody uses.
        """
        return not self.errors

    def add(self, finding: Finding) -> None:
        self.findings.append(finding)

    def signature(self) -> tuple:
        """What the report is, for comparing one pass against the next.

        Ignores message wording so that a rule whose message includes a
        coordinate does not look like a different finding each pass.
        """
        return tuple(sorted((f.rule, f.severity, tuple(f.subjects))
                            for f in self.findings))


def is_stalled(previous: Optional[LintReport], current: LintReport) -> bool:
    """True when a correction pass changed nothing the linter can see.

    The loop's other failure mode. Running the budget out on passes that each
    fix nothing wastes time and ends with the same honest-but-late answer, so a
    caller should stop at the first stall and report what is left.
    """
    if previous is None:
        return False
    return previous.signature() == current.signature()


# ---------------------------------------------------------------------------
# Geometry helpers
# ---------------------------------------------------------------------------
def _normalize_rect(obj: Mapping[str, Any]) -> tuple[int, int, int, int]:
    """`(x0, y0, x1, y1)` in a conventional top-left-origin space.

    EA's y axis increases downward and placement uses negative tops, so the
    numerically LARGER value is the visual top. Flipping once here means no
    other function has to remember the convention.
    """
    left, right = int(obj["left"]), int(obj["right"])
    top, bottom = int(obj["top"]), int(obj["bottom"])
    x0, x1 = min(left, right), max(left, right)
    y0, y1 = -max(top, bottom), -min(top, bottom)
    return x0, y0, x1, y1


def _overlap(a: Mapping[str, Any], b: Mapping[str, Any]) -> bool:
    ax0, ay0, ax1, ay1 = _normalize_rect(a)
    bx0, by0, bx1, by1 = _normalize_rect(b)
    # Touching edges are not an overlap: a band and its contents legitimately
    # share an edge. NOTE that this means no-overlap never implies whitespace,
    # so any rule about spacing must measure the spacing itself.
    return ax0 < bx1 and bx0 < ax1 and ay0 < by1 and by0 < ay1


def _contains(outer: Mapping[str, Any], inner: Mapping[str, Any]) -> bool:
    ox0, oy0, ox1, oy1 = _normalize_rect(outer)
    ix0, iy0, ix1, iy1 = _normalize_rect(inner)
    return ox0 <= ix0 and oy0 <= iy0 and ox1 >= ix1 and oy1 >= iy1


def _center(obj: Mapping[str, Any]) -> tuple[float, float]:
    x0, y0, x1, y1 = _normalize_rect(obj)
    return (x0 + x1) / 2.0, (y0 + y1) / 2.0


def _width(obj: Mapping[str, Any]) -> int:
    """Width, from the rect rather than from a `width` key.

    `verify_diagram` supplies `width`, but a caller assembling a payload by
    hand may not, and the rect is always there. Deriving it removes a way for
    the two to disagree.
    """
    x0, _, x1, _ = _normalize_rect(obj)
    return x1 - x0


def _height(obj: Mapping[str, Any]) -> int:
    _, y0, _, y1 = _normalize_rect(obj)
    return y1 - y0


# ---------------------------------------------------------------------------
# Rules
# ---------------------------------------------------------------------------
def check_no_overlaps(objects: Sequence[Mapping[str, Any]],
                      report: LintReport) -> None:
    """Overlapping elements are the most visible failure a generator makes.

    Containment is exempt: nesting is how EA expresses composition, and a
    grammar that nests deliberately - a capability map, a domain map - must not
    be punished for doing its job.
    """
    overlapping = []
    for i, a in enumerate(objects):
        for b in objects[i + 1:]:
            if not _overlap(a, b):
                continue
            if _contains(a, b) or _contains(b, a):
                continue
            overlapping.append((a["element_id"], b["element_id"]))

    report.metrics["overlaps"] = len(overlapping)
    for pair in overlapping:
        report.add(Finding(
            rule="overlap", severity="error",
            message="two elements overlap without one containing the other",
            subjects=pair,
            correction="move one element, or widen the pitch for this row",
        ))


def check_within_canvas(objects: Sequence[Mapping[str, Any]],
                        canvas: Mapping[str, Any],
                        report: LintReport) -> None:
    """How much of the composition falls outside the diagram's PAGE size.

    THIS RULE USED TO CLAIM THAT SUCH A DIAGRAM "EXPORTS CLIPPED", AND IT DOES
    NOT. Measured rather than reasoned about: three elements were placed on a
    diagram whose `cx`/`cy` was EA's default 800x1100, one of them spanning to
    x 1600 and another to y -1460, and the image export came back **2219x2031**
    - aspect 1.093 against the content's 1.099 and the canvas's 0.727. The
    export followed the CONTENT. Nothing was clipped, nothing was missing.

    That matters because the claim was not merely imprecise, it was load
    bearing: `cx`/`cy` is one printed page, so a diagram of any size at all
    exceeds it, and a rule that fires on every non-trivial diagram in every
    grammar is worse than no rule. It failed six of the first nineteen cases of
    the live content sweep, and in all six the composition was correct.

    So this is INFO. The count is still worth having - it is what a caller
    needs if they are going to PRINT, where the page size does govern and the
    diagram paginates - but it is not a defect, and it does not make a report
    unclean.
    """
    cx, cy = int(canvas.get("cx") or 0), int(canvas.get("cy") or 0)
    if not cx or not cy:
        return
    outside = []
    for obj in objects:
        x0, y0, x1, y1 = _normalize_rect(obj)
        if x1 > cx or y1 > cy or x0 < 0 or y0 < 0:
            outside.append(obj["element_id"])
    report.metrics["outside_canvas"] = len(outside)
    if outside:
        report.add(Finding(
            rule="out-of-canvas", severity="info",
            message=(f"{len(outside)} element(s) fall outside the {cx}x{cy} "
                     f"page size; image export is unaffected and follows the "
                     f"content"),
            subjects=tuple(outside),
            correction="nothing, unless this diagram will be PRINTED - then "
                       "grow the diagram's cx/cy so it fits one page, or "
                       "accept that it paginates",
        ))


def check_uniform_sizing(roles: Mapping[str, Sequence[Mapping[str, Any]]],
                         report: LintReport) -> None:
    """Elements playing the same role should be the same size.

    `roles` maps a role name to the objects in it. **The caller decides what a
    role is**, because that is a language question and this module does not
    answer language questions. Two elements can share a container and still be
    different roles - a small round event beside a wide rectangular step - and
    requiring those to be one size would be requiring a 110x60 circle.

    `roles_measured` IS THE DENOMINATOR, and it is what makes the count beside
    it readable. `roles_with_inconsistent_sizing` is 0 both for a caller who
    passed clean roles and for one who passed none at all, and a vacuous zero
    has already been quoted as a result in this programme - see
    `crossings_measured_over`, which was added for exactly that. Both keys are
    always present, as those two are, so the pair can be read without knowing
    which rules ran.
    """
    inconsistent = []
    declared = 0
    measured = 0
    for role, members in (roles or {}).items():
        members = list(members)
        if not members:
            continue
        declared += 1
        if len(members) < 2:
            continue
        measured += 1
        widths = {_width(o) for o in members}
        heights = {_height(o) for o in members}
        if (max(widths) - min(widths) > SIZE_TOLERANCE
                or max(heights) - min(heights) > SIZE_TOLERANCE):
            inconsistent.append(role)
            report.add(Finding(
                rule="uniform-sizing", severity="error",
                message=(f"elements in role {role!r} vary in size "
                         f"(widths {sorted(widths)}, heights {sorted(heights)})"),
                subjects=tuple(o["element_id"] for o in members),
                correction=f"give every {role} the same width and height",
            ))
    report.metrics["roles_with_inconsistent_sizing"] = len(inconsistent)
    report.metrics["roles_measured"] = measured
    if declared and not measured:
        report.not_run.append(
            f"uniform-sizing: {declared} role(s) were declared and none holds "
            f"two elements, so no size was compared against another"
        )


def check_pitch_consistency(groups: Iterable[Sequence[Mapping[str, Any]]],
                            report: LintReport,
                            axis: str = "horizontal") -> None:
    """Spacing between neighbors in a row or a column should be even.

    Judged on the SPREAD, against `PITCH_TOLERANCE`, rather than on exact
    equality - EA nudges geometry and exact equality would be noise.

    BOTH AXES, BECAUSE THEY ARE THE SAME QUESTION TURNED NINETY DEGREES
    -------------------------------------------------------------------
    `axis` is one of `STACK_AXES`: `"horizontal"` is a row read left to right,
    whose spacing is measured along x, and `"vertical"` is a column read top to
    bottom, whose spacing is measured along y. `lint_diagram` supplies it from
    which of its own two arguments the group arrived in - `rows=` or `columns=` -
    so a caller states a column by passing one, never by an axis string.

    For a long time only x was measured, and the cost was exact: a column passed
    as a row has every x gap equal to the same negative number, so the spread is
    zero and a column at wildly uneven vertical spacing reported clean. The
    server's own distribute operation shipped with the same defect and for the
    same reason, and it now does both axes because they are orthogonal.

    WHAT IS MEASURED DEPENDS ON WHETHER THE GROUP IS UNIFORMLY SIZED
    ----------------------------------------------------------------
    For a group of equally sized elements, the edge-to-edge GAP is measured.

    For a group whose elements differ in size ALONG THE READING AXIS, the
    CENTER-TO-CENTER pitch is measured instead. That is not a loosening: a flow
    that puts a 30-wide event next to a 110-wide activity has a rhythm the
    reader perceives as the even spacing of centers, and both the edge gaps and
    the leading edges necessarily vary around it. The two measures are identical
    for equal sizes. Size is taken along the reading axis - widths for a row,
    heights for a column - because that is the dimension that makes the gaps
    vary.

    EVERY GROUP GETS A FLOOR ON THE GAP ITSELF
    ------------------------------------------
    Even spacing says nothing about whether the boxes touch, and the floor is
    the rule for that. It applies on BOTH paths, which it did not always:

    * Mixed sizes. Widths alternating `a, b, a, b` with `a + b = 2 * pitch`
      drive EVERY edge gap to zero while the center spread stays at zero.
    * Uniform sizes. Eight equal boxes butted edge to edge have eight gaps of
      zero, and the spread of eight zeros is zero. This is the case the floor
      used to miss, and it is the THIRD time the touching exemption has hidden a
      spacing defect here: a whole row with no whitespace in it scored
      completely clean.

    Leaning on `check_no_overlaps` to bound either one does not work, because
    touching is exempt from the overlap rule by design - a band and its contents
    legitimately share an edge.

    WHY THAT DOES NOT PUNISH DELIBERATE ABUTMENT
    --------------------------------------------
    Bands, lanes and pools abut on purpose, and a rule forbidding all touching
    would be wrong. The floor is not that rule: it judges only a group the
    caller PASSED AS A ROW OR A COLUMN, and declaring one is the statement that
    its members are laid out with spacing between them. Containers that abut
    deliberately reach this module as a `stacks=` grouping instead, and no rule
    here measures the gaps between a stack's members. So the scope is the
    declaration, not the geometry and not the element type: the same two boxes
    are a defect as a row and correct as a stack, and only the caller knows
    which they are.

    A wrapped row is TWO rows and the caller passes it as two. Compensating
    here would paper over that and lose the single mis-spaced element this rule
    exists to catch.

    `pitch_groups_measured` IS THE DENOMINATOR for `worst_pitch_spread`, which
    is 0 both for evenly spaced rows and for no rows at all. Both accumulate
    across the two axes, so calling this twice on one report - which is what
    `lint_diagram` does - reports the worst of both and counts all of them.
    """
    if axis not in STACK_AXES:
        report.not_run.append(
            f"pitch: unknown axis {axis!r}; expected one of {list(STACK_AXES)}, "
            f"so these groups were not judged"
        )
        return
    vertical = axis == "vertical"
    lead, trail = (1, 3) if vertical else (0, 2)
    along = _height if vertical else _width
    label = "column" if vertical else "row"

    declared = 0
    measured = 0
    worst = report.metrics.get("worst_pitch_spread", 0)
    for group in groups or []:
        ordered = sorted(group, key=lambda o: _normalize_rect(o)[lead])
        if not ordered:
            continue
        declared += 1
        if len(ordered) < 3:
            continue
        measured += 1
        sizes = {along(o) for o in ordered}
        uniform = max(sizes) - min(sizes) <= SIZE_TOLERANCE
        gaps = [_normalize_rect(b)[lead] - _normalize_rect(a)[trail]
                for a, b in zip(ordered, ordered[1:])]
        if uniform:
            measure, spacings = "gaps", gaps
        else:
            measure = "center pitches"
            spacings = [int(_center(b)[1 if vertical else 0]
                            - _center(a)[1 if vertical else 0])
                        for a, b in zip(ordered, ordered[1:])]
        if min(gaps) <= 0:
            report.add(Finding(
                rule="pitch", severity="error",
                message=(f"elements in a {label} touch or overlap their "
                         f"neighbors (gaps {gaps}); a {label} with no "
                         f"whitespace anywhere in it does not read as a "
                         f"{label}, and even spacing does not make it one"),
                subjects=tuple(o["element_id"] for o in ordered),
                correction=f"increase the slot pitch for this {label}",
            ))
        spread = max(spacings) - min(spacings)
        worst = max(worst, spread)
        if spread > PITCH_TOLERANCE:
            report.add(Finding(
                rule="pitch", severity="warning",
                message=f"uneven spacing within a {label} ({measure} {spacings})",
                subjects=tuple(o["element_id"] for o in ordered),
                correction=f"space elements in a {label} evenly",
            ))
    report.metrics["worst_pitch_spread"] = worst
    report.metrics["pitch_groups_measured"] = (
        report.metrics.get("pitch_groups_measured", 0) + measured)
    if declared and not measured:
        report.not_run.append(
            f"pitch: {declared} {label}(s) were declared and none holds three "
            f"elements, so there was no second gap to compare a first against"
        )


def check_stack_extents(
        stacks: Iterable[tuple[str, Sequence[Mapping[str, Any]]]],
        report: LintReport) -> None:
    """Containers stacked one after another should share a cross-axis extent.

    `stacks` is a list of `(axis, members)` pairs, both stated BY THE CALLER.
    `axis` is one of `STACK_AXES`: `"vertical"` is a stack read top to bottom,
    whose members should share a WIDTH, and `"horizontal"` is a stack read left
    to right, whose members should share a HEIGHT. This module does not decide
    which boxes form a stack or which way it runs - that is a composition fact
    the generator knows, and a rule that inferred a stack from coordinates would
    fire on any diagram that merely happens to look stacked.

    THE DEFECT NO OTHER RULE SEES
    -----------------------------
    A band sized to its own contents is narrower when it holds fewer items, so
    bands of three, three and two leave the stack with a ragged edge. Every
    per-element and per-pair rule passes: nothing overlaps, every row is evenly
    spaced, every item matches its role. This is the first rule about a
    container's EXTENT rather than about its members.

    Judged against `SIZE_TOLERANCE` and not a constant of its own, because it is
    the same claim - "these are one size" - made about containers rather than
    items, and EA nudges a container's geometry exactly as it nudges an
    element's. No calibration against a real stack exists to justify a
    different number, and inventing one would be a claim this file cannot back.

    A WARNING, not an error. A stack whose extents differ is not wrong the way
    an overlap is: a tapering stack is a legitimate composition. But it is the
    caller who declares a stack, and declaring one is the statement that its
    members are peers, so a difference is worth a look.

    WHAT IT REFUSES TO JUDGE
    ------------------------
    Only the extent is compared. Members that agree on width but start at
    different left edges are staggered rather than ragged, and that is
    `check_stack_alignment`, not this rule. Nor does this say anything about the
    gaps between members, which is a spacing question. A stack of fewer than two
    is skipped, and an axis outside `STACK_AXES` is reported on `not_run` rather
    than guessed at.
    """
    measured = False
    declared = 0
    worst = 0
    for axis, members in stacks or []:
        members = list(members)
        if not members:
            # An empty stack is not a declaration. A banded diagram drawn
            # without band labels has no container elements at all, and the
            # caller still builds it a stack; saying so on `not_run` would
            # complain about deliberate, documented behavior.
            continue
        if axis not in STACK_AXES:
            report.not_run.append(
                f"ragged-stack: unknown axis {axis!r}; expected one of "
                f"{list(STACK_AXES)}, so this stack was not judged"
            )
            continue
        declared += 1
        if len(members) < 2:
            continue
        measured = True
        measure = _width if axis == "vertical" else _height
        label = "width" if axis == "vertical" else "height"
        extents = [measure(o) for o in members]
        spread = max(extents) - min(extents)
        worst = max(worst, spread)
        if spread > SIZE_TOLERANCE:
            report.add(Finding(
                rule="ragged-stack", severity="warning",
                message=(f"containers in a {axis} stack differ in {label} "
                         f"({label}s {extents}), leaving the stack a ragged "
                         f"edge"),
                subjects=tuple(o["element_id"] for o in members),
                correction=(f"give every container in this stack the same "
                            f"{label}, the largest ({max(extents)}) so that "
                            f"nothing has to shrink"),
            ))
    if measured:
        report.metrics["worst_stack_extent_spread"] = worst
    elif declared:
        report.not_run.append(
            f"ragged-stack: {declared} stack(s) were declared and none holds "
            f"two containers, so no extent was compared against another"
        )


def check_stack_alignment(
        stacks: Iterable[tuple[str, Sequence[Mapping[str, Any]]]],
        report: LintReport) -> None:
    """Containers in a stack should start at the same leading edge.

    `stacks` is the same `(axis, members)` grouping `check_stack_extents` reads,
    stated BY THE CALLER for the same reason. The LEADING EDGE is the one the
    reader's eye follows down the stack: for a `"vertical"` stack, read top to
    bottom, that is the left edge; for a `"horizontal"` one, read left to right,
    the top edge.

    THE DEFECT NO OTHER RULE SEES
    -----------------------------
    Containers of identical size, at different offsets across the stack, so the
    edge the eye follows zigzags. `check_stack_extents` says in as many words
    that it compares the extent only and does not judge this, and nothing else
    looks at a declared stack at all - so a staggered stack of three identical
    bands scored completely clean. Every per-element and per-pair rule passes:
    nothing overlaps, every extent matches, every item matches its role.

    Judged against `SIZE_TOLERANCE` and not a constant of its own. Alignment is
    the strictest of the claims this file makes - boxes either line up or they do
    not - so it takes the tightest tolerance already here, which is the one that
    exists to absorb EA's own few units of nudge. No real staggered stack has
    been measured to argue for a different number, and inventing one would be a
    claim this file cannot back.

    A WARNING, for the reason `ragged-stack` is one: a deliberate indent - an
    inset band, a stack that steps - is a legitimate composition. But declaring a
    stack is the statement that its members are peers, so an offset is worth a
    look.

    WHAT IT REFUSES TO JUDGE
    ------------------------
    Only the leading edge. Where a member ENDS is its extent, which is
    `check_stack_extents`, and the gaps between members are a spacing question no
    rule about a stack asks. An unknown axis is reported on `not_run` rather than
    guessed at - separately from `check_stack_extents`, because each rule has to
    be honest when it is the only one called.
    """
    measured = False
    declared = 0
    worst = 0
    for axis, members in stacks or []:
        members = list(members)
        if not members:
            continue
        if axis not in STACK_AXES:
            report.not_run.append(
                f"staggered-stack: unknown axis {axis!r}; expected one of "
                f"{list(STACK_AXES)}, so this stack was not judged"
            )
            continue
        declared += 1
        if len(members) < 2:
            continue
        measured = True
        vertical = axis == "vertical"
        edge = 0 if vertical else 1
        label = "left" if vertical else "top"
        edges = [_normalize_rect(o)[edge] for o in members]
        spread = max(edges) - min(edges)
        worst = max(worst, spread)
        if spread > SIZE_TOLERANCE:
            report.add(Finding(
                rule="staggered-stack", severity="warning",
                message=(f"containers in a {axis} stack start at different "
                         f"{label} edges ({label} edges {edges}), so the edge "
                         f"the eye follows down the stack zigzags"),
                subjects=tuple(o["element_id"] for o in members),
                correction=(f"align every container in this stack on one "
                            f"{label} edge, the smallest ({min(edges)}) so that "
                            f"nothing moves further from the rest"),
            ))
    if measured:
        report.metrics["worst_stack_alignment_spread"] = worst
    elif declared:
        report.not_run.append(
            f"staggered-stack: {declared} stack(s) were declared and none holds "
            f"two containers, so no leading edge was compared against another"
        )


def _edge_distance(obj: Mapping[str, Any], ux: float, uy: float) -> float:
    """How far from a rect's center to its border, along the unit vector."""
    x0, y0, x1, y1 = _normalize_rect(obj)
    along_x = ((x1 - x0) / 2.0) / abs(ux) if ux else float("inf")
    along_y = ((y1 - y0) / 2.0) / abs(uy) if uy else float("inf")
    return min(along_x, along_y)


def _ring_parts(entry: Sequence[Any]) -> tuple:
    """`(hub, items, sweep)` from one caller-supplied ring.

    A ring is `(hub, items)` or `(hub, items, sweep)`. The sweep is optional
    because it was not always asked for, and widening the tuple rather than
    changing its shape means a caller who already passes rings keeps passing
    them - it just gets no angular judgment until it says how far round the ring
    is meant to go. See `check_ring_angles`.
    """
    if len(entry) == 3:
        hub, items, sweep = entry
        return hub, list(items), sweep
    hub, items = entry
    return hub, list(items), None


def check_ring_spokes(
        rings: Iterable[tuple[Mapping[str, Any], Sequence[Mapping[str, Any]]]],
        report: LintReport) -> None:
    """Items around a hub should sit the same distance from its edge.

    `rings` is a list of `(hub, items)` pairs, stated BY THE CALLER: which box
    is the hub and which boxes are its ring. Geometry cannot say, for the same
    reason it cannot say which boxes form a stack - see `check_stack_extents`.
    A radial tree is several rings, one per hub, and is passed as several.

    THE DEFECT NO OTHER RULE SEES
    -----------------------------
    Placing each item's CENTER on a circle around the hub does not place its
    EDGE there. A wide flat item at the top or bottom of the ring reaches
    toward the hub by only half its height; the same item at the side reaches
    by half its width. So a flat item stands off from the hub at the top and
    bottom and crowds it at the sides - unequal spokes - while every item is
    correctly on the circle, nothing overlaps, and every per-element rule
    passes.

    WHAT IS MEASURED
    ----------------
    The length of the spoke as the reader sees it: the straight line from the
    hub's center to the item's center, less the stretch inside the hub and the
    stretch inside the item. Both stretches are found by running that line out
    to each box's border, so a diagonal spoke is measured on the diagonal, not
    on one axis. A hub that is not square gets its own unequal reach for the
    same reason an item does, and that is counted too.

    The SPREAD, largest minus smallest, is judged against `PITCH_TOLERANCE`
    rather than against equality. It is the same claim `check_pitch_consistency`
    makes about a row - evenly spaced - made about a ring, and it has the same
    reason to tolerate a nudge. No calibration against a real ring exists to
    justify a separate constant.

    A WARNING. Unequal spokes make a ring look uneven and are never a
    correctness problem; a diagram can be read perfectly well from one.

    WHAT IT REFUSES TO JUDGE
    ------------------------
    Angular spacing - whether the items are evenly spread around the ring - is a
    different question, and it is `check_ring_angles`, not this rule. Neither
    rule says whether the ring is circular, or whether the spokes cross other
    items. An item whose center coincides with the hub's has no direction, so it
    is left out rather than given one; a ring with fewer than two measurable
    items has no spread.
    """
    measured = False
    declared = 0
    worst = 0.0
    for entry in rings or []:
        hub, items, _sweep = _ring_parts(entry)
        if not items:
            continue
        declared += 1
        hx, hy = _center(hub)
        spokes: list[tuple[Any, float]] = []
        for item in items:
            ix, iy = _center(item)
            dx, dy = ix - hx, iy - hy
            distance = (dx * dx + dy * dy) ** 0.5
            if distance == 0:
                continue
            ux, uy = dx / distance, dy / distance
            length = (distance - _edge_distance(hub, ux, uy)
                      - _edge_distance(item, ux, uy))
            spokes.append((item["element_id"], length))
        if len(spokes) < 2:
            continue
        measured = True
        lengths = [length for _, length in spokes]
        spread = max(lengths) - min(lengths)
        worst = max(worst, spread)
        if spread > PITCH_TOLERANCE:
            report.add(Finding(
                rule="uneven-spokes", severity="warning",
                message=(f"items around a hub sit unequal distances from its "
                         f"edge (spoke lengths "
                         f"{[int(round(n)) for n in lengths]}, spread "
                         f"{int(round(spread))})"),
                subjects=(hub["element_id"], *(i for i, _ in spokes)),
                correction=("place each item by its NEAR EDGE rather than by "
                            "its center, so every spoke is the same length"),
            ))
    if measured:
        report.metrics["worst_spoke_spread"] = int(round(worst))
    elif declared:
        report.not_run.append(
            f"uneven-spokes: {declared} ring(s) were declared and none holds "
            f"two items away from its hub's center, so no spoke was compared "
            f"against another"
        )


def _bearings(hub: Mapping[str, Any],
              items: Sequence[Mapping[str, Any]]) -> list:
    """Each item's bearing from the hub, in degrees, sorted around the circle.

    An item on the hub's own center has no bearing and is left out, exactly as
    `check_ring_spokes` leaves it out of the spokes.
    """
    hx, hy = _center(hub)
    out = []
    for item in items:
        ix, iy = _center(item)
        dx, dy = ix - hx, iy - hy
        if dx == 0 and dy == 0:
            continue
        out.append((math.degrees(math.atan2(dy, dx)) % 360.0,
                    item["element_id"]))
    out.sort()
    return out


def _steps_without_the_opening(steps: Sequence[float]) -> list:
    """A partial ring's own steps: every gap except the one that is its opening.

    WHICH gap is the opening cannot be read off the angles, and guessing wrong
    would report a correct fan. It is not simply the largest: a fan of three
    across 350 degrees steps 175 at a time and has an opening of 10, so there
    the opening is the SMALLEST of the three.

    So every gap is tried as the opening and the most charitable reading is
    kept - the removal that leaves the remaining steps looking most even. That
    is quiet on a legitimate fan at ANY sweep, and it cannot rescue a fan whose
    steps are genuinely uneven, because then every removal leaves a wide spread.
    """
    best = None
    for k in range(len(steps)):
        rest = list(steps[:k]) + list(steps[k + 1:])
        spread = max(rest) - min(rest)
        if best is None or spread < best[0]:
            best = (spread, rest)
    return best[1]


def check_ring_angles(
        rings: Iterable[tuple[Mapping[str, Any], Sequence[Mapping[str, Any]]]],
        report: LintReport) -> None:
    """Items around a hub should be evenly spread around it, not bunched.

    THE DEFECT NO OTHER RULE SEES
    -----------------------------
    A ring squeezed into a third of its circumference. Every spoke is the same
    length, nothing overlaps, every item matches its role, and
    `check_ring_spokes` says in as many words that the angle is not its question
    - so a ring of three at 0, 100 and 200 degrees, which should be at 0, 120
    and 240, scored completely clean.

    THE SWEEP IS THE CALLER'S TO STATE, AND WITHOUT IT THIS DOES NOT RUN
    --------------------------------------------------------------------
    A ring is passed as `(hub, items, sweep)`, with `sweep` in degrees. Three
    items bunched into 200 degrees and three items fanned evenly across 200
    degrees ARE THE SAME GEOMETRY; the only difference is how far round the ring
    was meant to go, and that is a composition fact the generator holds. A rule
    that assumed a full circle would report every deliberate fan, and a fan is
    what a partial sweep is for. So a ring passed as a plain `(hub, items)` pair
    lands on `not_run` and is not judged.

    Only whether the ring CLOSES is read off the number - a sweep of 360 or more
    closes it - because the spread of the observed steps is what is judged, and
    that needs no expected step. This module therefore holds no copy of the
    engine's angular arithmetic to drift away from.

    WHAT IS MEASURED
    ----------------
    The bearing of each item's center from the hub's, sorted around the circle,
    then the step from each item to the next. A closed ring's steps include the
    one from the last item back to the first, which is what makes a bunched ring
    show up: the items' own steps can be perfectly even while the way back is
    half the circle. A partial ring has an opening instead of that step, and
    `_steps_without_the_opening` drops it.

    The SPREAD is judged against `ANGLE_TOLERANCE`, which is in degrees and is
    calibrated against the layouts the engine produces - see the constant. A
    WARNING: a bunched ring looks lopsided and is never a correctness problem.

    WHAT IT REFUSES TO JUDGE
    ------------------------
    Evenness only. A fan that fills a quarter of the sweep it declared, evenly,
    is clean - how much of its sweep a ring should occupy is a composition
    choice, not a defect. Spoke length is `check_ring_spokes`. A closed ring
    needs two measurable items and a partial one needs three, because the first
    step it can compare against is the one the opening is not.
    """
    measured = False
    declared = 0
    unstated = 0
    worst = 0.0
    for entry in rings or []:
        hub, items, sweep = _ring_parts(entry)
        if not items:
            continue
        declared += 1
        if sweep is None:
            # Counted rather than reported here, so that a diagram of six
            # sweepless rings gets one line and not six.
            unstated += 1
            continue
        bearings = _bearings(hub, items)
        if len(bearings) < 2:
            continue
        around = [degrees for degrees, _ in bearings]
        steps = [b - a for a, b in zip(around, around[1:])]
        steps.append(360.0 - sum(steps))
        if abs(float(sweep)) < 360.0:
            if len(steps) < 3:
                continue
            steps = _steps_without_the_opening(steps)
        measured = True
        spread = max(steps) - min(steps)
        worst = max(worst, spread)
        if spread > ANGLE_TOLERANCE:
            report.add(Finding(
                rule="uneven-ring-angles", severity="warning",
                message=(f"items around a hub are unevenly spread around it "
                         f"(steps {[int(round(n)) for n in steps]} degrees, "
                         f"spread {int(round(spread))}), so the ring reads as "
                         f"bunched to one side"),
                subjects=(hub["element_id"], *(i for _, i in bearings)),
                correction=("step each item the same number of degrees from the "
                            "last: divide the sweep by the number of items when "
                            "the ring closes, and by one less when it does not"),
            ))
    if unstated:
        report.not_run.append(
            f"uneven-ring-angles: {unstated} ring(s) were declared without a "
            f"sweep, so whether their items should close the circle or fan "
            f"across part of it is unstated and their angles were not judged"
        )
    if measured:
        report.metrics["worst_ring_angle_spread"] = int(round(worst))
    elif declared > unstated:
        report.not_run.append(
            f"uneven-ring-angles: {declared} ring(s) were declared and none "
            f"holds enough items away from its hub's center to compare one step "
            f"against another"
        )


def check_routing(links: Sequence[Mapping[str, Any]],
                  expected_route: Optional[str],
                  report: LintReport) -> None:
    """Connectors should use the route the notation calls for, deliberately.

    A link with NO route at all is the interesting case: it means nothing was
    chosen, which is how a diagram ends up with EA's defaults instead of a
    decision.
    """
    stored = [link for link in links if link.get("stored")]
    report.metrics["links_stored"] = len(stored)
    report.metrics["links_unstyled"] = sum(1 for link in stored
                                           if not link.get("route"))

    unrouted = [link["connector_id"] for link in stored if not link.get("route")]
    if unrouted:
        report.add(Finding(
            rule="routing-unset", severity="warning",
            message=f"{len(unrouted)} connector(s) have no route set",
            subjects=tuple(unrouted),
            correction="set an explicit route so the diagram does not depend "
                       "on EA's default",
        ))

    if expected_route:
        wanted = expected_route.strip().lower()
        wrong = [link["connector_id"] for link in stored
                 if (link.get("route") or "").lower() != wanted]
        if wrong:
            report.add(Finding(
                rule="routing-mismatch", severity="warning",
                message=(f"{len(wrong)} connector(s) do not use the expected "
                         f"{expected_route} routing"),
                subjects=tuple(wrong),
                correction=f"set route={expected_route} on these connectors",
            ))


# ---------------------------------------------------------------------------
# Rules that read identity as well as geometry
# ---------------------------------------------------------------------------
def _segments_cross(p1, p2, p3, p4) -> bool:
    """Proper segment intersection; shared endpoints do not count.

    Connectors meeting at a shared element are not a crossing, and counting
    them would make every hub-and-spoke diagram look terrible.
    """
    def orient(a, b, c):
        val = (b[1] - a[1]) * (c[0] - b[0]) - (b[0] - a[0]) * (c[1] - b[1])
        return 0 if abs(val) < 1e-9 else (1 if val > 0 else 2)

    if p1 in (p3, p4) or p2 in (p3, p4):
        return False
    o1, o2, o3, o4 = (orient(p1, p2, p3), orient(p1, p2, p4),
                      orient(p3, p4, p1), orient(p3, p4, p2))
    return o1 != o2 and o3 != o4


def _element_key(element_id: Any) -> Any:
    """Index key for an element id: the number if it is one, else the id itself.

    Element ids arrive in two shapes. A placed model element has a numeric id,
    which `verify_diagram` sometimes reports as a string, so a numeric-looking
    id is normalized to `int` and one payload's `"1234"` matches another's
    `1234`. A composer also INVENTS an id for a container the caller did not
    name - `cell_0_0`, `group_0_header` - and that id is an opaque label with no
    number in it. It is kept exactly as given.
    """
    try:
        return int(element_id)
    except (TypeError, ValueError):
        return element_id


def check_crossings(objects: Sequence[Mapping[str, Any]],
                    links: Sequence[Mapping[str, Any]],
                    report: LintReport) -> int:
    """Count connector crossings, straight line center to center.

    An approximation, and honest about it: it ignores the actual routed path,
    so an orthogonal diagram's real crossing count differs. It is still the
    right metric for COMPARISON - between two versions of one diagram, fewer is
    better - which is what a correction loop needs.

    Reported as `info`, because this rule cannot tell a REMOVABLE crossing from
    a necessary one. Some graphs are not planar and no reordering helps.

    `crossings_measured_over` is recorded beside the count on purpose. Zero
    crossings over zero measurable links is not a result, and for a long time
    this rule reported exactly that - the endpoints it needs were absent from
    the payload, so every diagram scored zero. A count without its denominator
    is how that stayed invisible.
    """
    # THE DECISION ON A SYNTHETIC ID, recorded so it is not re-litigated: an id
    # a composer invented for an unnamed container is INDEXED AS ITSELF. It is
    # neither coerced nor dropped.
    #
    # This line used to read `int(o["element_id"])`, which raised ValueError on
    # the first such id and took the whole report down with it. The coercion was
    # only ever normalization - so that an object stating "1234" matches a link
    # stating 1234 - and never a claim that every id is a number, so it now
    # applies where it means something and nowhere else.
    #
    # Synthetic ids stay IN the index rather than being filtered out, because a
    # caller may legitimately connect to a container, and silently omitting its
    # rect would lower `crossings_measured_over` without saying so. A count that
    # quietly measures less than it appears to is the exact failure this rule
    # already carries a denominator for.
    by_id = {_element_key(o["element_id"]): o for o in objects}
    segments = []
    for link in links:
        src, tgt = link.get("source_element_id"), link.get("target_element_id")
        if src in by_id and tgt in by_id:
            segments.append((_center(by_id[src]), _center(by_id[tgt])))

    crossings = 0
    for i, (p1, p2) in enumerate(segments):
        for p3, p4 in segments[i + 1:]:
            if _segments_cross(p1, p2, p3, p4):
                crossings += 1

    report.metrics["crossings"] = crossings
    report.metrics["crossings_are_approximate"] = True
    report.metrics["crossings_measured_over"] = len(segments)
    if links and not segments:
        report.not_run.append(
            "crossings: no link carried both endpoint element ids, so nothing "
            "was measured"
        )
    if crossings:
        report.add(Finding(
            rule="crossings", severity="info",
            message=(f"{crossings} connector crossing(s), measured center to "
                     f"center over {len(segments)} link(s); some may be "
                     f"unavoidable"),
            correction="reorder elements within their row or container where "
                       "the crossings are incidental rather than structural",
        ))
    return crossings


def check_color_is_explained(objects: Sequence[Mapping[str, Any]],
                             report: LintReport) -> None:
    """Color that varies must be decodable.

    A correctness rule, not a style preference: color carrying information the
    reader cannot decode is a diagram that misleads.

    Two things count as explaining it, because both genuinely do - a legend,
    and a named container grouping the elements that share a color. A banded
    diagram whose bands are named needs no separate legend; the band names ARE
    the key, and demanding one anyway would be noise.

    A warning rather than an error: several fills are not always an encoding.
    """
    fills = {o.get("fill") for o in objects if o.get("fill")}
    report.metrics["distinct_fills"] = len(fills)
    if len(fills) < 2:
        # One color carries no information, so there is nothing to decode.
        return

    explained = any(
        "legend" in (o.get("name") or "").lower()
        or (_kind_of(o) in _CONTAINER_TYPES and (o.get("name") or "").strip())
        for o in objects
    )
    if explained:
        return

    report.add(Finding(
        rule="unexplained-color", severity="warning",
        message=(f"{len(fills)} fill colors are in use and nothing labels "
                 f"what they mean"),
        correction="add a legend, or name the containers that group each "
                   "color -- a banded diagram's band names are its key",
    ))


def check_title_present(objects: Sequence[Mapping[str, Any]],
                        title_convention: Optional[str],
                        report: LintReport) -> None:
    """Only fires when the convention calls for a DRAWN title.

    Most diagrams correctly use the frame header instead and some have no title
    at all, so firing unconditionally would flag the majority of a real corpus
    for doing the right thing. `title_convention` is the caller's to supply: it
    is a convention, not something the geometry knows.

    `title_convention_stated` IS THE DENOMINATOR, and it is always present.
    Silence from this rule meant two different things and recorded neither: a
    diagram that has its drawn title, and a diagram nobody said anything about.
    False says the question was never asked.
    """
    stated = (title_convention or "").strip().lower() == "drawn"
    report.metrics["title_convention_stated"] = stated
    if not stated:
        return
    if not any(_kind_of(o) in _TITLE_TYPES for o in objects):
        report.add(Finding(
            rule="missing-title", severity="warning",
            message="this diagram's convention draws a title block; none found",
            correction="add a Text element as a title block",
        ))


def check_connector_labels(links: Sequence[Mapping[str, Any]],
                           report: LintReport) -> None:
    """A stored connector with no name leaves the relationship to be inferred.

    Suppressed under a profile that hides connector labels - see
    `SUPPRESSED_BY`. That suppression is why this rule can exist at all: some
    views hide these deliberately, and a rule that fired anyway would be the
    one that gets the whole linter switched off.

    Only STORED links are judged. EA draws a relationship between two placed
    elements whether or not a presentation row exists, and a line with no row
    has no label state to read.
    """
    stored = [link for link in links if link.get("stored")]
    unlabeled = [link["connector_id"] for link in stored
                 if not (link.get("name") or "").strip()]
    labeled = [link["connector_id"] for link in stored
               if (link.get("name") or "").strip()]
    report.metrics["connectors_unlabeled"] = len(unlabeled)

    # INCONSISTENT labeling is the defect. Unlabeled connectors are not:
    # several notations leave their ordinary flows unnamed as a convention, and
    # a rule that fired on all of them would report a correct diagram as broken
    # every time -- which is how a linter gets switched off.
    #
    # Measured on a real generated diagram whose six sequence flows are
    # deliberately unnamed: the first version of this rule reported all six.
    # Some labeled and some not is the case worth a word, because then the
    # blank ones read as omissions rather than as convention.
    if unlabeled and labeled:
        report.add(Finding(
            rule="missing-connector-labels", severity="warning",
            message=(f"{len(labeled)} connector(s) are labeled and "
                     f"{len(unlabeled)} are not, so the blank ones read as "
                     f"oversights rather than as a convention"),
            subjects=tuple(unlabeled),
            correction="label these too, or remove the labels from the others "
                       "so the diagram is consistent",
        ))


def check_collapsed_connectors_annotated(
        objects: Sequence[Mapping[str, Any]],
        links: Sequence[Mapping[str, Any]],
        profile: Optional[Mapping[str, Any]],
        report: LintReport) -> None:
    """Exists ONLY under a profile that collapses parallel connectors.

    Collapsing several relationships into one line is a real simplification and
    a real loss: the reader sees one line with no way to know it stands for
    four. That is fine when it is stated and misleading when it is not, so
    under a collapsing profile the diagram has to carry something saying so.

    The only rule here that a profile turns ON rather than off.
    """
    if not (profile or {}).get("collapses_parallel"):
        return
    annotated = (any(_looks_like_annotation(o.get("name")) for o in objects)
                 or any(_looks_like_annotation(k.get("name")) for k in links))
    report.metrics["collapse_annotated"] = bool(annotated)
    if not annotated:
        report.add(Finding(
            rule="collapsed-connectors-unannotated", severity="error",
            message=("this view collapses parallel connectors and nothing on "
                     "the diagram says so -- one line standing for several "
                     "relationships reads as one relationship"),
            correction="add a note or legend stating that parallel "
                       "relationships have been collapsed",
        ))


# ---------------------------------------------------------------------------
# Label fit, measured from the render
# ---------------------------------------------------------------------------
def _svg_text_runs(svg: str) -> list[dict]:
    """Every rendered line, with the width EA itself measured for it."""
    out = []
    for m in _SVG_TEXT_RE.finditer(svg):
        length = m.group("tl")
        if length is None:
            continue
        body = re.sub(r"<[^>]+>", "", m.group("body"))
        for entity, char in _ENTITIES:
            body = body.replace(entity, char)
        out.append({
            "x": float(m.group("x")), "y": float(m.group("y")),
            "length": float(length), "text": body.strip(),
        })
    return out


def _svg_boxes(svg: str) -> list[tuple]:
    return [(float(m.group("x")), float(m.group("y")),
             float(m.group("w")), float(m.group("h")))
            for m in _SVG_RECT_RE.finditer(svg)]


def _assign_runs_to_boxes(boxes, runs) -> dict:
    """Group runs by the box that owns them: `{box_index: [run, ...]}`.

    A run belongs to the box it sits horizontally within whose top is NEAREST
    above it. Nesting therefore resolves correctly - an inner box's top is
    lower than its parent's, so it wins for its own children.

    THE OBVIOUS IMPLEMENTATION IS WRONG, and was written first: collecting only
    the runs that fall INSIDE the box, with a few pixels of slack below. That
    filters out exactly the lines that overflow, so a name spilling out of the
    bottom of its box was measured over the lines that still fitted and
    reported as fitting. The rule looked like it worked and could not fire on
    its own headline case.

    So there is no vertical cutoff here at all. A run below its box is still
    that box's run, which is the whole point.
    """
    grouped: dict = {}
    for run in runs:
        run_left = run["x"]
        run_right = run["x"] + run["length"]
        best = None
        best_key = None
        for i, (x, y, w, h) in enumerate(boxes):
            # OVERLAP, not center containment. A run that overflows badly has
            # its center outside the box -- which is exactly the case this rule
            # exists to catch, so keying on the center made the rule blind to
            # its own headline defect and silently reassigned the run to the
            # diagram frame, where it fitted.
            overlap = min(run_right, x + w) - max(run_left, x)
            if overlap <= 0:
                continue
            if run["y"] < y - _BASELINE_SLACK:
                continue          # the run sits above this box entirely
            key = (y, overlap)
            if best is None or key > best_key:
                best, best_key = i, key
        if best is not None:
            grouped.setdefault(best, []).append(run)
    return grouped


def check_labels_fit(objects: Sequence[Mapping[str, Any]],
                     svg_text: Optional[str],
                     report: LintReport) -> None:
    """Names that overflow their box, or sit hard against its border.

    EXACT, not estimated. EA's SVG carries `textLength` on every text run - its
    own measured advance width in pixels - so this compares EA's numbers with
    EA's rects rather than guessing from a character count. Measured over 458
    text runs across eight probe diagrams: every run carried `textLength`, and
    EA never truncates, never adds an ellipsis and never shrinks the font. It
    emits the whole string and lets it overflow.

    Two findings, because they are two problems:

    * `label-clipped` (error) - the text leaves the box. It is cut off in an
      export, and it is wrong under every profile.
    * `label-cramped` (warning) - it fits with less than `LABEL_MARGIN` px to
      spare on its tightest side. Legible, but it reads as touching the border.

    `LABEL_MARGIN` is calibrated, not invented: on a real generated capability
    map it separates exactly the two names that look wrong (margins of 5 and 6)
    from the next-tightest box at 10. The boundary is anywhere in (6, 10).

    Everything is measured in the SVG's own coordinate space, so no EA-to-SVG
    transform is needed. Findings are attributed back to an element by matching
    the rendered text against the object's name, which is why this rule needs
    `name` on the objects.

    Requires `include_svg=True`. Without the markup the rule cannot run and
    says so on `report.not_run`, rather than passing silently - a check that
    quietly does nothing is worse than one that is absent.
    """
    if not svg_text:
        report.metrics["labels_measured"] = 0
        report.not_run.append(
            "label-fit: no svg_text in the payload; call verify_diagram with "
            "include_svg=True"
        )
        return

    runs = _svg_text_runs(svg_text)
    boxes = [b for b in _svg_boxes(svg_text)
             if b[2] >= _MIN_BOX and b[3] >= _MIN_BOX]
    # A NAME TWO ELEMENTS SHARE IDENTIFIES NEITHER. This used to keep the
    # FIRST element carrying a name and drop the rest, which reads as a
    # tie-break and is a mis-attribution: the finding then names whichever
    # element happened to be placed first, not the one whose box was measured.
    #
    # Measured live on EA 17.1, two elements given the same 46-character name
    # on one diagram - one shape-scripted from a bound MDG, one a plain Class.
    # Only the plain Class emits a rect, so only its box grew; the overflow was
    # real and the `render-exceeds-rect` error was raised against the OTHER
    # element. Renaming one of them moved the finding onto the right element,
    # which is how the shared name was established as the cause. A modeler
    # following that correction widens a box that was never too narrow and
    # leaves the broken one broken.
    #
    # So a duplicated name is counted as unmatched, which is what this rule's
    # own contract already says - "exactly one known element's name". The cost
    # is that an element sharing its name with another is not label-checked;
    # that is the same trade this rule makes everywhere else, and is recorded
    # in `references/verification.md`.
    _ids_by_name: dict[str, list] = {}
    _stored_width: dict[Any, int] = {}
    for obj in objects:
        name = " ".join((obj.get("name") or "").split())
        if name:
            _ids_by_name.setdefault(name, []).append(obj["element_id"])
        _stored_width[obj["element_id"]] = _width(obj)
    by_name: dict[str, Any] = {name: ids[0]
                               for name, ids in _ids_by_name.items()
                               if len(ids) == 1}

    grouped = _assign_runs_to_boxes(boxes, runs)
    measured = 0
    unmatched = 0
    for index, box in enumerate(boxes):
        mine = grouped.get(index) or []
        if not mine:
            continue
        measured += 1
        x, y, w, h = box
        text_left = min(r["x"] for r in mine)
        text_right = max(r["x"] + r["length"] for r in mine)
        last_baseline = max(r["y"] for r in mine)
        label = " ".join(r["text"] for r in sorted(mine, key=lambda r: r["y"]))
        label = " ".join(label.split())

        # NO MATCH, NO FINDING. Only a box whose text is exactly one known
        # element's name is judged.
        #
        # EA draws MDG-stereotyped elements with a shape script, which emits
        # paths rather than a `<rect>`. On such a diagram the only rects are
        # the drawn containers, so every element's text falls to the band that
        # encloses it and the "label" becomes every name in the band
        # concatenated -- which then reports a spectacular overflow against a
        # box it does not belong to. Measured on a real generated diagram: one
        # band reported its label as five element names and two connector
        # labels run together.
        #
        # Skipping is the right answer rather than a cleverer attribution.
        # This rule is a quality warning, and a quality warning that fires
        # wrongly on a whole notation is how the linter gets switched off. A
        # missed cramped label costs far less than that.
        if label not in by_name:
            unmatched += 1
            continue
        subjects = (by_name[label],)

        # The matched box must be able to BE this element's outline. A shape
        # script emits several rects per element -- an icon box, a compartment
        # divider -- and judging a name against one of those reports an
        # overflow against a rectangle the name was never drawn inside.
        # Measured: an ArchiMate element 100 units wide reported its name as
        # overflowing by 37px, against a sub-rect narrower than the element.
        # EA only ever GROWS a drawn box, so anything narrower than the stored
        # width is not the outline.
        stored_w = _stored_width.get(subjects[0])
        if stored_w and w < stored_w - _RENDER_SLACK:
            unmatched += 1
            continue

        # EA GROWS THE DRAWN BOX rather than clipping a name it cannot break.
        # Measured: a 30-character unbreakable name in a 100-wide element
        # renders 128px wide, a 49-character one renders 188px, while
        # `verify_diagram` keeps reporting the stored width of 100.
        #
        # That makes this the rule that matters, and it is not about text at
        # all: the diagram does not look like its own geometry. Every other
        # rule here reads the stored rects, so a box that draws 88px wider than
        # it measures can sit on top of its neighbour while the overlap rule
        # sees a comfortable gap.
        if subjects:
            stored = _stored_width.get(subjects[0])
            if stored and w - stored > _RENDER_SLACK:
                report.add(Finding(
                    rule="render-exceeds-rect", severity="error",
                    message=(f"{label!r} does not fit, so EA draws this "
                             f"element {int(w)}px wide while its geometry says "
                             f"{int(stored)}px -- the render is "
                             f"{int(w - stored)}px wider than anything else "
                             f"here can see"),
                    subjects=subjects,
                    correction="widen this element to at least "
                               f"{int(w)}px, or shorten the name so it fits "
                               "the width you chose",
                ))
                continue

        overflow_x = max(0.0, x - text_left) + max(0.0, text_right - (x + w))
        overflow_y = max(0.0, last_baseline - (y + h))
        if overflow_x > 0 or overflow_y > 0:
            report.add(Finding(
                rule="label-clipped", severity="error",
                message=(f"{label!r} overflows its element by "
                         f"{int(max(overflow_x, overflow_y))}px and is cut off "
                         f"in an export"),
                subjects=subjects,
                correction="widen or heighten this element, or shorten the name",
            ))
            continue
        side_margin = min(text_left - x, (x + w) - text_right)
        if side_margin < LABEL_MARGIN:
            report.add(Finding(
                rule="label-cramped", severity="warning",
                message=(f"{label!r} comes within {int(side_margin)}px of its "
                         f"element border and reads as touching it"),
                subjects=subjects,
                correction=f"widen this element so the label clears its border "
                           f"by at least {LABEL_MARGIN}px",
            ))
    report.metrics["labels_measured"] = measured
    report.metrics["labels_unmatched"] = unmatched
    if unmatched and not measured:
        report.not_run.append(
            f"label-fit: none of {unmatched} text block(s) matched a single "
            f"element name, so nothing was judged -- this notation is probably "
            f"drawn with shape scripts, which emit paths rather than rects"
        )


# ---------------------------------------------------------------------------
# Driver
# ---------------------------------------------------------------------------
def _suppressed_rules(profile: Optional[Mapping[str, Any]]) -> set[str]:
    """Rule ids this profile deliberately makes moot."""
    if not profile:
        return set()
    return {rule for rule, key in SUPPRESSED_BY.items() if profile.get(key)}


def lint_diagram(
    verified: Mapping[str, Any],
    profile: Optional[Mapping[str, Any]] = None,
    roles: Optional[Mapping[str, Sequence[Mapping[str, Any]]]] = None,
    rows: Optional[Iterable[Sequence[Mapping[str, Any]]]] = None,
    columns: Optional[Iterable[Sequence[Mapping[str, Any]]]] = None,
    stacks: Optional[
        Iterable[tuple[str, Sequence[Mapping[str, Any]]]]] = None,
    rings: Optional[
        Iterable[tuple[Mapping[str, Any], Sequence[Mapping[str, Any]]]]] = None,
    expected_route: Optional[str] = None,
    title_convention: Optional[str] = None,
) -> LintReport:
    """Lint one `verify_diagram` result.

    `profile` is a plain mapping of presentation settings - see `PROFILE_KEYS`.
    It suppresses the rules a view deliberately makes moot, and the suppressed
    rule ids come back on the report so that a suppression is visible rather
    than silent.

    `roles`, `rows`, `columns`, `stacks` and `rings` are the caller's grouping:
    which elements play the same role, which sit in the same row, which sit in
    the same column, which containers form a stack and which way it runs, which
    boxes ring which hub. Those are composition facts the generator knows and
    geometry alone does not, and guessing them here would invent the metamodel
    this module deliberately does not have. Omit them and the rules that need
    them simply do not run.

    `rows` and `columns` are both lists of groups and are judged by the same
    rule on the two axes - a caller who already passes `rows` does not have to
    restructure to declare a column, it passes `columns` as well. `stacks` is
    `[(axis, containers), ...]` with `axis` in `STACK_AXES`. `rings` is
    `[(hub, items), ...]`, or `[(hub, items, sweep), ...]` to have the angular
    spacing judged too; see `check_ring_angles` for why the sweep cannot be
    inferred.

    WHEN A GROUPING IS OMITTED, NOTHING IS SAID ON `not_run`, and that is
    deliberate: an entry per unused grouping would put three lines on every
    ordinary diagram, and a list that is noisy on correct output is a list
    nobody reads. The absent metric key is the signal there. `not_run` is for a
    grouping the caller DID declare and the rule could not judge - an unknown
    axis, a ring with no sweep, or groups that are all too small to compare
    anything within - because that is the case where a clean report has checked
    less than it looks.
    """
    report = LintReport()
    objects = list(verified.get("objects") or [])
    links = list(verified.get("links") or [])

    report.metrics["objects"] = len(objects)
    report.metrics["links"] = len(links)
    suppressed = _suppressed_rules(profile)
    report.suppressed = sorted(suppressed)

    check_no_overlaps(objects, report)
    check_within_canvas(objects, verified.get("canvas") or {}, report)
    check_uniform_sizing(roles or {}, report)
    check_pitch_consistency(rows or [], report)
    check_pitch_consistency(columns or [], report, axis="vertical")
    check_stack_extents(stacks or [], report)
    check_stack_alignment(stacks or [], report)
    check_ring_spokes(rings or [], report)
    check_ring_angles(rings or [], report)
    check_routing(links, expected_route, report)
    check_crossings(objects, links, report)
    check_color_is_explained(objects, report)
    check_title_present(objects, title_convention, report)
    check_collapsed_connectors_annotated(objects, links, profile, report)
    check_labels_fit(objects, verified.get("svg_text"), report)
    if "missing-connector-labels" not in suppressed:
        check_connector_labels(links, report)

    report.metrics["errors"] = len(report.errors)
    report.metrics["findings"] = len(report.findings)
    return report

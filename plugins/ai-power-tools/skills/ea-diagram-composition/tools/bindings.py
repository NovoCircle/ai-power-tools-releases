#!/usr/bin/env python3
"""Language bindings: diagram conventions as data.

Every modeling language has its own diagram types, its own sizing and spacing,
its own title convention, its own routing habits, and its own catalog of
standard views. If those live in code, every new notation is an engineering
task and the library never covers more than the few that were hard-coded.

So they live in data - one YAML binding per technology - and this module is the
loader. It validates a binding, resolves `extends`, and translates a diagram
type's conventions into the `spec` dict `compose.py` already takes.

THE LAYER BOUNDARY
------------------
`compose.py` contains no technology name and must not import this module. The
dependency runs one way only: a binding is data that *feeds* the engine. A test
in `test_bindings.py` asserts both halves of that, because a single
`if technology == ...` in the engine would quietly undo the whole design.

WHY `spacing` USES THE ENGINE'S OWN KEY NAMES
---------------------------------------------
The original schema sketch wrote `pitch: {h: 40, v: 70}`. `compose.py`
distinguishes a *gap* (space between two boxes) from a *pitch* (leading edge to
leading edge, so it includes the box), and raises when a pitch is smaller than
the item it must step over. A binding author writing `pitch: 40` next to a
100-wide item has written a layout that cannot be composed - and would not find
out until generation time.

`spacing` is therefore validated against `compose.DEFAULT_SPEC` itself: a
binding can only name a key the engine really has, spelled the way the engine
spells it, so the translation to a spec is the identity and cannot drift. A
binding that says `pitch:` is rejected with the key it probably meant.

MEASURED, NOT ASSUMED
---------------------
The numbers in the shipped bindings were measured from real diagrams rather
than estimated, and the measurements corrected the sketch more than once:

  * BPMN's technology id is `BPMN2.0`, not `BPMN2`, and its diagram type is
    `Business Process` - with a space. A binding keyed on a guessed id resolves
    to nothing, silently, which is the worst failure mode this schema has.
  * EA 17.1's built-in ArchiMate3 MDG names its stereotypes with an
    `ArchiMate_` prefix (`ArchiMate_ApplicationComponent`), and that prefixed
    form is what lands in `t_object.Stereotype`. BPMN2.0 uses no prefix.
    Hence `stereotype_prefix` as data: a binding lists notation concepts the
    way the notation's own specification names them, and the prefix is applied
    to get what EA stores. And it is data at TWO scopes, because measurement
    found technologies where one value cannot be true - see below.
  * ArchiMate diagrams are spaced more generously horizontally than
    vertically; BPMN flows are tighter than either. Both were measured from
    element rects, not eyeballed.

THE BASE NOTATION IS THE ROOT OF THE TREE
-----------------------------------------
EA is a UML tool, and every MDG technology is a stereotype layer applied to
UML rather than a peer notation beside it. The data says so: each MDG diagram
type records the EA base diagram type it is drawn on in `base`, and every base
the shipped MDG bindings name is a plain-UML diagram type - an ArchiMate view
IS a Class diagram (`Logical`) with a technology tag on it, a BPMN process IS
an `Analysis` diagram, a SysML requirement diagram IS a `Custom` canvas.

So `extends` points a technology's binding at the notation underneath it, and
`base` picks WHICH of that notation's diagram types each of its own diagram
types is drawn on. Those are two different facts and neither is derivable from
the other: one binding's diagram types can sit on several different bases, and
a technology id cannot be read out of a diagram type name without searching
the directory for whoever declares it.

WHAT INHERITANCE IS FOR, AND WHAT IT MUST NOT DO
------------------------------------------------
The value is entirely in the slots a child does NOT state. A stereotyped
element's size comes from its own MDG, its grammar is its own, and its
`stereotype_prefix` is its own; all of those are statements, and a statement
wins. What a child leaves unsaid used to fall back to the ENGINE's defaults -
a 20-unit gap chosen to be inoffensive - when the measured value for the
diagram type it is actually drawn on was sitting in the parent binding.

Hence `sizing` and `spacing` merge per key against the substrate, and nothing
else does. Those two are the only slots where silence means an engine default:
`grammar`, `title`, `routing.default` and `channels.fill` are mandatory, so a
child has already spoken, and inheriting a parent's `graph` over a child's
`layered-bands` would flatten exactly the structure an MDG exists to add.
`own_sizing` and `own_spacing` keep what the document itself said, so a test
that pins a measurement reads the measurement rather than the inheritance.

`stereotype_prefix` IS PER TECHNOLOGY *AND* PER DIAGRAM TYPE
------------------------------------------------------------
One slot per technology was wrong, measured, for two shipped technologies, and
wrong in the silent direction the prefix exists to prevent:

  * `StrategyMap` has SIX prefixes, one per diagram type, each at or near 100%
    within its own type - `SM_` on StrategyMap (83 of 86 stereotyped elements),
    `DT_` on DecisionTree (30 of 30), `OC_` on OrgChart (29 of 29), `VC_` on
    ValueChain (20 of 20), `BS_` on BalancedScorecard (4 of 4), `FC_` on
    FlowChart (28 of 28). No single value is true for the technology.
  * `TOGAF Diagrams` has `ADM_` on 10 of 10 elements of its `TOGAF_Interface`
    diagram type and NO prefix across the technology, whose other stereotypes
    are stored bare (`Mission`, `Principle`, `OrganizationUnit`).

Before this, both bindings stated `""` and spelled their `sizing` keys the way
EA stores them. That round trips - `stereotype_for` and `concept_for` are both
the identity under an empty prefix - but it means neither binding can offer
prefix-based lookup at all, and a caller holding the notation's own concept name
gets a miss rather than an answer.

So a diagram type may state its own `stereotype_prefix`, and what it does not
state falls back to the TECHNOLOGY's. That direction matters both ways round: a
technology with one prefix states it once and every diagram type resolves to it,
which is why ArchiMate3, ERD_dp and the eight bindings with `""` needed no edit;
and a technology whose prefix is per type states `""` once - the measured
technology-wide fact - and overrides it where the measurement differs.

THE PREFIX IS NEVER INHERITED FROM THE SUBSTRATE, only from the technology. A
substrate is a diagram type in the PARENT technology, and a prefix is a fact
about whose MDG named the stereotype: inheriting UML's `Logical` prefix into
ArchiMate's `Business` would be the same category error as inheriting UML's
`graph` over ArchiMate's `layered-bands`. `_on_substrate` merges `sizing` and
`spacing` and nothing else, which is already the rule; this is the second slot
where a reader has to be told that silence means the technology rather than the
canvas.

`own_stereotype_prefix` is `None` when the diagram type says nothing, which is
how `stereotype_prefix_is_inherited` tells a fallback from a declared `""` -
exactly the distinction `_merge` keeps at technology scope, for the same reason.

A DIAGRAM TYPE MAY THEREFORE OMIT `sizing` ENTIRELY
---------------------------------------------------
`sizing.default` is mandatory in the RESOLVED diagram type and optional in the
document, and the split matters. It used to be checked per document, before
`_merge` ran, so no diagram type could ever inherit the one figure every diagram
of it needs - and three notations went unbound for that reason alone, each with
a measured base notation sitting underneath it whose default was exactly the
right answer. The check now runs in `Binding.__init__`, on the merged values.

INHERITING GOT EASIER; INVENTING DID NOT. Those are different acts and the
schema keeps them apart. Omitting the block says "the figure is the substrate's",
names the substrate in `base`, and leaves `default_size_is_inherited` True
forever after, so a resolution reports the borrowed figure as borrowed. Typing a
number in says "we measured this", and nothing downstream can tell a measured
number from a guessed one - which is why the refusal message offers inheriting
and fixing `base:` as the only two ways out of a missing default, and says
plainly that copying a figure from another notation is not a third.

A CHILD DOES NOT ACQUIRE ITS PARENT'S DIAGRAM TYPE CATALOG
----------------------------------------------------------
Inheriting the parent's `diagram_types` wholesale - which is what merging one
level into the catalog used to do - is wrong twice over once the parent is the
base notation. A technology's diagram types are declared by its MDG and are a
closed fact checked against the MDG data, so handing ArchiMate3 a diagram type
named `Logical` invents one EA never declared; and `resolve_diagram` matches a
diagram's `Diagram_Type` against bound diagram type NAMES, so five bindings all
claiming `Logical` would make every plain Class diagram ambiguous. The parent's
diagram types are the substrate a child's own types are measured against, not
entries in the child's catalog.

SIZING TO FIT THE CONTENT'S NAMES
---------------------------------
A binding's `sizing.default` is measured off real diagrams of that notation, so
it is the right box for a typical name. It knows nothing about the names in
front of it, and a customer's element names come from their model and are
whatever they are. EA does not clip a name it cannot fit: it GROWS THE DRAWN
BOX, silently, while the repository keeps reporting the width that was stored.
Measured live: a 36-character name with no spaces in it was drawn 169 px wide
against a stored 60. Every other check - overlap, pitch, containment - reads the
stored rect, so from that point on they are all reading a rect that is not the
one EA paints.

`spec(names=...)` is where that is prevented. Given the names that will go in
the boxes it widens `item_width` until the longest word in the widest of them
clears the border, returns a `SpecFit` - a spec dict that also says what it
widened and why - and leaves everything else alone. Nothing here is per
notation: what has to fit is a string, and a string is the same width whatever
notation is eventually drawn around it.

AND IT IS NOT THIS MODULE'S CALL WHICH WAY THAT GOES. Widening the box and
letting the text overlap the border are both legitimate drawings of the same
content, and which one a diagram wants is the user's judgment about that diagram.
So the misfit is reported as a `compose.FitConflict` on `SpecFit.conflicts`,
saying what did not fit, what each option costs and which was applied; widening
is what happens when nobody answers, because it is the safe direction, and
`on_misfit="overlap"` is how a caller relays the answer when the user wants the
width kept. An agent that finds a conflict is supposed to ASK - the skill's own
guidance says so - not to pick.

THE ENGINE IS NOT THE PLACE FOR THIS, and it would be nine places if it were.
Nine grammars resolve `item_width`, each its own way, and each would need the
same arithmetic and its own way of reporting it. They all take a spec, and on
the documented path every spec comes from here. One site, upstream of all nine,
and the widening lands on `item_width` - which is the spec-level fallback every
grammar shares - so peers keep a common width and no grammar trades a text-fit
finding for an inconsistent-sizing one.

PyYAML
------
Bindings are YAML, matching the shipped ArchiMate conformance ruleset, and
PyYAML is loaded the same way `validate_model` loads it: if it is missing, the
error says so and names the install. Loading is always `safe_load`, so a
binding cannot carry executable content - `!!python/object` is refused by the
parser rather than by a check here.
"""
from __future__ import annotations

import math
import sys
import unicodedata
from collections.abc import Iterable, Mapping, Sequence
from pathlib import Path
from typing import Any

_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

import compose as _engine  # noqa: E402
from compose import DEFAULT_SPEC  # noqa: E402

# The clearance a label needs from its border, taken from the rule that judges
# it rather than restated here. Prevention and detection have to agree on one
# number or the composer produces boxes the linter then complains about, and a
# second copy of a calibrated figure is how they stop agreeing. The dependency
# runs this way round on purpose: the linter must not import this module (a test
# in `test_lint.py` pins that), because a rule that reached for a binding would
# stop being a rule about geometry.
from lint import LABEL_MARGIN  # noqa: E402

# The widen-or-overlap vocabulary, re-exported rather than restated. A caller
# holding a binding should not have to import the engine to name the answer it is
# relaying, and a second copy of the two strings is how the two halves of one
# mechanism drift apart.
from compose import (  # noqa: E402
    DEFAULT_FIT_ANSWER,
    FIT_ANSWERS,
    FIT_OVERLAP,
    FIT_WIDEN,
    FitConflict,
)

__all__ = [
    "BindingError",
    "Binding",
    "DiagramTypeBinding",
    "Viewpoint",
    "PresentationProfile",
    "GRAMMARS",
    "GRAMMAR_PLACEMENT",
    "PLACED_BY_ENGINE",
    "PLACED_BY_EA",
    "PLACED_BY_DIAGRAM_TYPE",
    "COMPOSED_GRAMMARS",
    "EA_PLACED_GRAMMARS",
    "IMPLEMENTED_GRAMMARS",
    "implemented_grammars",
    "producible_grammars",
    "ROUTE_NAMES",
    "CHANNELS",
    "TITLE_CONVENTIONS",
    "RESOLUTION_PATHS",
    "RESOLVED_PATHS",
    "MDG_STYLE_KEY",
    "MDG_SEPARATOR",
    "HEADER_ADVANCE_PX",
    "CALIBRATED_REPERTOIRE",
    "FULL_WIDTH_CELLS",
    "unvalidated_glyphs",
    "SpecFit",
    "FitConflict",
    "FIT_WIDEN",
    "FIT_OVERLAP",
    "FIT_ANSWERS",
    "DEFAULT_FIT_ANSWER",
    "width_to_fit",
    "Resolution",
    "load_binding",
    "load_binding_text",
    "find_binding",
    "available_bindings",
    "DuplicateTechnology",
    "declared_technologies",
    "binding_conflicts",
    "mdg_diagram_key",
    "bindings_for_technologies",
    "resolve_diagram",
]


class BindingError(ValueError):
    """A binding is not valid.

    The message always names the offending key using its path into the
    document - `diagram_types.Application.channels.fill`,
    `viewpoints.ApplicationCooperation.diagram_type` - so an author can find it
    without guessing. That is the whole point of validating on load: a binding
    with a typo'd route name or a diagram type nothing declares would otherwise
    fail much later, as a diagram that came out wrong.
    """


class DuplicateTechnology(BindingError):
    """Two binding files in one directory declare the same `technology` id.

    THIS REFUSES RATHER THAN RANKING, and the reason is that there is no correct
    answer to rank to. The catalog is keyed by technology id, "which file supplied
    this id" is the one fact a caller cannot recover afterward, and the readers of
    the directory did not even agree on the winner: `available_bindings` kept the
    LAST file in sorted order, `_binding_path` - and so `find_binding` and every
    `extends` resolution - took the FIRST, and a third reader outside this module
    merged the two files' diagram types into one technology. Two of those silently
    compose diagrams against the shadow; the third silently inflates how much of a
    notation is bound. A duplicate id is an authoring mistake with a one-line fix,
    so it is raised where it is made.

    It is raised even when one of the two files does not validate. A file that
    fails validation is normally skipped - one bad file must not make the whole
    catalog unreadable - but skipping a bad file that CLAIMS AN ID ANOTHER FILE
    CLAIMS is not skipping, it is picking a winner. The claim is read from the
    parsed `technology` key alone, so the conflict is decided the same way by every
    reader whatever else is wrong with either file.

    The message names the id and EVERY file that claims it, sorted, so the outcome
    does not depend on the order the filesystem enumerates them.
    """


# ---------------------------------------------------------------------------
# Closed vocabularies
# ---------------------------------------------------------------------------
# The grammars, and WHO PLACES THE GEOMETRY of a diagram that has one. Eight
# names in three placements, and the placement is what decides what a consumer
# may do with a binding that names one.
#
# SIX COMPOSED LAYOUTS - `layered-bands`, `lanes`, `nested-grid`, `radial`,
# `two-column-cycle`, `computed-geometry` - are arrangements this library
# computes coordinates for. `two-column-cycle` was the last row of the corpus
# audit still waiting on engine code: a cycle drawn as two columns, flow down one
# and back up the other. It is its own grammar rather than a radial variant
# because its arithmetic is a pitch and a split, not a bearing, and because its
# boxes are deliberately DIFFERENT HEIGHTS - the one composed layout where that
# is true, and the reason a composer for it could not be a parameter on another.
#
# Six, not the four the corpus analysis first resolved on: measuring the rows
# grouped under `computed-geometry` before building it showed they do not share
# an arithmetic - placing items on a circle, packing rectangles so their AREAS
# encode a number, and drawing a waveform against a time axis are three
# unrelated pieces of code. `radial` is the polar one, built; WHAT IS LEFT UNDER
# `computed-geometry` IS THE TREEMAP ALONE - the timing diagram was moved to
# `ea-semantic`, for the reason set out below.
#
# A composed grammar may be named before it is built. That is deliberate, and
# `implemented_grammars()` is how a consumer finds out before it composes rather
# than after. It is NOT a license to record a composed layout for a diagram type
# that has none: the shipped binding that records a level-by-level tree as
# `layered-bands` is honest because those levels really are drawn as registers,
# one band per level, and its own `notes` say so. The dishonest version is
# recording an unbuilt composed grammar to get a type into a file at all, and it
# would be believed precisely because it eventually composes - the day the
# treemap ships, a diagram type parked under `computed-geometry` starts
# reporting itself composable.
#
# TWO WHERE WE PLACE NOTHING. That parking pressure was real: most diagram types
# in most notations are graphs or trees, the composed layouts have nothing
# to say about them, and `grammar` is mandatory - so whole notations went unbound
# for a schema reason rather than a real one, and an omitted diagram type is
# indistinguishable from an oversight. Hence:
#
#   `graph`        a graph or a tree. We do not compute coordinates; EA's own
#                  layout does, and we tidy afterwards. Everything else in the
#                  binding still earns its place - element sizes, spacing (which
#                  the layout call takes as layer and column spacing), routing,
#                  title convention, claimed and free channels - so such a
#                  binding is worth authoring and the diagram IS producible.
#   `ea-semantic`  the diagram TYPE fixes the arrangement, so coordinates are
#                  the WRONG OUTPUT - not coordinates we have not got round to.
#                  Quality there is order rather than geometry, nothing here
#                  judges or produces it, so this one is NOT producible. Recorded
#                  rather than left out, so that "later design work" is visible
#                  as data.
#
# THE PRINCIPLE, NOT THE EXAMPLES, DECIDES `ea-semantic`, and the difference is
# not "behavioral". That intuition is what produced three wrong entries in this
# comment, and the measurements corrected every one of them: lifelines with
# messages ordered down the page are the real case - their horizontal pitch is an
# even machine step no author produces by hand - while a state machine's states
# and a collaboration's participants sit exactly where a modeler put them, in many
# different sizes, with gap populations that look like a class diagram's. Both are
# `graph`, and the shipped base-notation binding classifies them that way on
# measured evidence. MEASURE BEFORE YOU CLASSIFY: a type that SOUNDS sequential is
# not `ea-semantic` unless EA is doing the placing.
#
# A WAVEFORM AGAINST A TIME AXIS IS `ea-semantic` TOO, which is the opposite of
# what this comment used to say. It reads like arithmetic nobody has written -
# hence the first filing under `computed-geometry` - but the axis is dictated by
# the type: every timeline spans the canvas, so two of them are never horizontal
# neighbors and a horizontal gap is not a quantity the type has. The decisive
# argument is the landmine above: parked under an unbuilt COMPOSED grammar, a
# timing diagram would start reporting itself composable the day a treemap
# composer shipped. `references/grammars.md` §7 and §9 carry the reasoning.
#
# ONE QUESTION PER ANSWER. `grammar_is_implemented` means "the engine has a
# `compose_<grammar>` for this" and must keep meaning only that, because
# consumers sweep the implemented grammars to pick a composer for each. Whether
# a diagram can be produced at all is a second question with a second answer:
# `graph` is producible with no composer, `computed-geometry` has a composer
# pending and is neither, `ea-semantic` is neither and has nothing pending.
PLACED_BY_ENGINE = "engine"
PLACED_BY_EA = "ea"
PLACED_BY_DIAGRAM_TYPE = "diagram-type"

GRAMMAR_PLACEMENT: dict[str, str] = {
    "layered-bands": PLACED_BY_ENGINE,
    "lanes": PLACED_BY_ENGINE,
    "nested-grid": PLACED_BY_ENGINE,
    "radial": PLACED_BY_ENGINE,
    "two-column-cycle": PLACED_BY_ENGINE,
    "computed-geometry": PLACED_BY_ENGINE,
    # Each of these lives in its own module and is re-exported by `compose.py`;
    # see the note at the bottom of that file for why the import sits there.
    "matrix": PLACED_BY_ENGINE,
    "radial-tree": PLACED_BY_ENGINE,
    "chevron-stack": PLACED_BY_ENGINE,
    "treemap": PLACED_BY_ENGINE,
    "graph": PLACED_BY_EA,
    "ea-semantic": PLACED_BY_DIAGRAM_TYPE,
}

#: The vocabulary a binding's `grammar` is validated against. A frozenset rather
#: than the `{grammar: is_implemented}` mapping this used to be: one boolean
#: cannot answer both "do we compose this" and "can we produce this", and a
#: consumer still reading a truth value out of this name should fail loudly here
#: rather than quietly read `graph` as composable.
GRAMMARS: frozenset[str] = frozenset(GRAMMAR_PLACEMENT)

#: The grammars whose coordinates are ours to compute. Membership is not
#: implementation - `computed-geometry` is ours and unbuilt.
COMPOSED_GRAMMARS: frozenset[str] = frozenset(
    grammar for grammar, placement in GRAMMAR_PLACEMENT.items()
    if placement == PLACED_BY_ENGINE)

#: The grammars EA's own layout engine places acceptably. Not composed by us,
#: and producible - which is the pair of facts the single boolean could not hold.
EA_PLACED_GRAMMARS: frozenset[str] = frozenset(
    grammar for grammar, placement in GRAMMAR_PLACEMENT.items()
    if placement == PLACED_BY_EA)


def _engine_composers() -> frozenset[str]:
    """The grammars the engine has a `compose_<grammar>` for, read from it.

    Underscores stand in for the vocabulary's hyphens. Read from the module
    rather than from its `__all__`, so a grammar shipped without being exported
    still counts: the question is what the engine can do, not what it
    advertises.

    DERIVED ON EVERY CALL, NOT CACHED AND NOT WRITTEN DOWN. This was a flag per
    grammar kept by hand with a test pinning it to the engine, which is two
    copies of one fact agreeing with each other; the same shape once let a
    measurement tool go on reporting a remembered reach figure for a grammar
    that had already shipped. Reading the module each time is what makes
    shipping a composer move every answer here at once.
    """
    return frozenset(
        name[len("compose_"):].replace("_", "-")
        for name in dir(_engine)
        if name.startswith("compose_") and callable(getattr(_engine, name)))


def implemented_grammars() -> frozenset[str]:
    """Composed grammars the engine really has a composer for.

    Intersected with `COMPOSED_GRAMMARS`, so a composer named outside the
    vocabulary cannot smuggle a grammar into it. `test_bindings.py` asserts the
    intersection loses nothing, which is how a composer shipped under a name the
    vocabulary does not have is caught rather than silently dropped.

    A grammar EA places is never in here. That is not a gap: there is no
    composer to pick, and a consumer that sweeps this set to choose one would
    crash on an entry that has none. Ask `producible_grammars()` instead.
    """
    return COMPOSED_GRAMMARS & _engine_composers()


def producible_grammars() -> frozenset[str]:
    """The grammars a diagram can be produced for today, by EITHER route.

    The composed ones that are built, plus the ones EA's layout places for us.
    Deliberately a second answer rather than a widening of the first: folding
    them together would make a consumer sweeping for composers pick a grammar
    that has none, and narrowing to the first would report a producible diagram
    type as unreachable.
    """
    return implemented_grammars() | EA_PLACED_GRAMMARS


#: `implemented_grammars()` as at import, for consumers that read a constant.
#: Same meaning as it has always had - "the engine has a composer for this" -
#: and, for the composed values that were already built, the same value, so a
#: reach figure derived from it does not move on the day the vocabulary grew.
#: Code that mutates the engine after import (a test, a plugin) must call the
#: function.
IMPLEMENTED_GRAMMARS = implemented_grammars()

# Route names as the server accepts them, from EA's own connector right-click >
# Line Style submenu. SOURCE OF TRUTH is `_ROUTE_STYLES` / `_BEZIER_MODE` in
# ea_mcp_server.server; this is a validation copy, so a typo in a binding is
# caught on load instead of at write time.
#
# The skills bundle deliberately does NOT import the server -- it is a separate
# product, and a customer install has no server source on the path -- so the copy
# cannot be derived. `test_route_names_match_the_server` pins it against an
# accidental edit HERE; it cannot see a rename on the server side, which would
# leave both copies agreeing with each other and neither with EA. That drift is
# caught by the server's own generation suite, which takes every route from a
# binding and asserts EA holds it -- but only when that suite runs, since it
# needs a live repository.
ROUTE_NAMES = frozenset({
    "direct",
    "autorouting",
    "customline",
    "treevertical",
    "treehorizontal",
    "lateralvertical",
    "lateralhorizontal",
    "orthogonalsquare",
    "orthogonalrounded",
    "bezier",
})

# Visual channels a diagram can carry a variable in. `channels` exists because
# each notation ALREADY claims some of these; a second variable has to go
# somewhere else, and a binding that lets an agent recolor ArchiMate fills has
# broken the notation while looking like a feature.
CHANNELS = frozenset({
    "fill", "border", "border_width", "line_color", "line_style",
    "font_color", "opacity", "icon", "size", "position",
})

# `drawn`     - the diagram carries a drawn title element on the canvas.
# `frame-header` - EA's own diagram frame supplies it; drawing one would double up.
#
# Recorded per diagram type because neither can be the silent default. Measured
# across the 147-diagram corpus the split tracks notation almost perfectly:
# 13 of 13 ArchiMate diagrams draw a title, 10 of 11 BPMN diagrams rely on the
# frame. (The corpus catalog spells the second one `frame-only`.)
TITLE_CONVENTIONS = ("drawn", "frame-header")

# Presentation-profile keys, from the detail/review/executive scheme. Each maps
# onto a whole-diagram display setting or onto the parallel-connector collapse.
_PROFILE_KEYS = frozenset({
    "connector_labels", "connector_stereotypes", "element_stereotypes",
    "compartments", "notes", "collapse_parallel", "direction_only",
    "description",
})
_COMPARTMENT_VALUES = ("all", "none")

_SPEC_KEYS = frozenset(DEFAULT_SPEC)

_TOP_LEVEL_KEYS = frozenset({
    "technology", "extends", "stereotype_prefix", "display_name", "notes",
    "diagram_types", "viewpoints", "presentation_profiles",
})
_DIAGRAM_TYPE_KEYS = frozenset({
    "grammar", "title", "sizing", "spacing", "routing", "channels", "notes",
    "base", "stereotype_prefix",
})
_VIEWPOINT_KEYS = frozenset({
    "diagram_type", "intent", "admits", "grammar", "notes",
})
_ROUTING_KEYS = frozenset({"default", "trunk_for", "notes"})
_CHANNEL_BLOCK_KEYS = frozenset({"fill", "claimed", "free", "notes"})


# ---------------------------------------------------------------------------
# Validation helpers - every one names the path it was given
# ---------------------------------------------------------------------------
def _mapping(value: Any, where: str) -> dict:
    if not isinstance(value, Mapping):
        raise BindingError(
            f"{where}: expected a mapping, got {type(value).__name__}")
    return dict(value)


def _str_list(value: Any, where: str) -> tuple[str, ...]:
    if isinstance(value, str) or not isinstance(value, Sequence):
        raise BindingError(
            f"{where}: expected a list of strings, got "
            f"{type(value).__name__}")
    out = []
    for i, entry in enumerate(value):
        if not isinstance(entry, str) or not entry.strip():
            raise BindingError(
                f"{where}[{i}]: expected a non-empty string, got {entry!r}")
        out.append(entry.strip())
    return tuple(out)


def _text(value: Any, where: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise BindingError(f"{where}: expected a non-empty string, got {value!r}")
    return value.strip()


def _positive_int(value: Any, where: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise BindingError(
            f"{where}: expected a whole number, got {value!r}")
    if value <= 0:
        raise BindingError(f"{where}: expected a positive number, got {value}")
    return value


def _reject_unknown(present: Mapping, allowed: frozenset, where: str,
                    hints: Mapping[str, str] | None = None) -> None:
    """Refuse keys the schema does not define.

    Silently ignoring an unrecognized key is how a binding ends up not doing
    what its author plainly wrote. `hints` upgrades the common mistakes from
    "unknown key" to "you meant this one".
    """
    unknown = sorted(set(present) - allowed)
    if not unknown:
        return
    hints = hints or {}
    parts = []
    for key in unknown:
        if key in hints:
            parts.append(f"{key!r} ({hints[key]})")
        else:
            parts.append(repr(key))
    raise BindingError(
        f"{where}: unknown key{'s' if len(unknown) > 1 else ''} "
        f"{', '.join(parts)}. Known keys: {', '.join(sorted(allowed))}")


def _normalize_route(name: str) -> str:
    return "".join(ch for ch in str(name).lower() if ch.isalnum())


# ---------------------------------------------------------------------------
# Value objects
# ---------------------------------------------------------------------------
class PresentationProfile:
    """How much detail a view shows - orthogonal to its diagram type.

    The same content can be duplicated into a second diagram under a different
    profile, giving a live detail view *and* a live executive view of one model
    rather than a screenshot of one of them.
    """

    __slots__ = ("name", "settings")

    def __init__(self, name: str, settings: Mapping[str, Any]):
        self.name = name
        self.settings = dict(settings)

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return f"PresentationProfile({self.name!r}, {self.settings!r})"

    def get(self, key: str, default: Any = None) -> Any:
        return self.settings.get(key, default)

    @property
    def collapses_parallel(self) -> bool:
        return bool(self.settings.get("collapse_parallel", False))

    def display_settings(self) -> dict[str, bool]:
        """Translate to `set_diagram_display` keyword arguments.

        Only the settings this profile actually states are returned, so a
        profile that says nothing about stereotypes leaves them alone rather
        than asserting a default it never chose.

        The polarity flips: a profile says what it *shows*, EA is told what to
        *hide*. That inversion is worth doing in exactly one place.

        WHAT `compartments` CAN AND CANNOT DO
        -------------------------------------
        `compartments: none` does NOT remove the attribute and operation
        compartments. EA's `SuppressedCompartments` was measured through six
        value shapes against a class with attributes and operations and changed
        nothing every time, so there is no verified way to take a compartment
        off. What IS available is reducing its detail to names: attributes read
        as `balance` rather than `balance: Decimal`, operations as `getBalance`
        rather than `getBalance(): Decimal`.

        So `none` and any explicit list both mean "least detail EA will give
        us", and `all` means full detail. That is a smaller promise than the
        profile vocabulary suggests, and saying so here is better than emitting
        a setting that silently does nothing.

        Every key emitted below was verified by rendering against content it
        could bite on. Nothing is emitted on faith.
        """
        out: dict[str, bool] = {}
        if "connector_labels" in self.settings:
            out["hide_connector_labels"] = not self.settings["connector_labels"]
        if "element_stereotypes" in self.settings:
            out["hide_element_stereotypes"] = (
                not self.settings["element_stereotypes"])
        if "connector_stereotypes" in self.settings:
            out["hide_connector_stereotypes"] = (
                not self.settings["connector_stereotypes"])
        if "notes" in self.settings:
            # A SHOW, not a hide: EA does not draw element notes by default, so
            # this is the one setting whose polarity does not flip.
            out["show_element_notes"] = bool(self.settings["notes"])
        if "compartments" in self.settings:
            full_detail = self.settings["compartments"] == "all"
            for key in ("hide_attribute_types", "hide_operation_return_types",
                        "hide_operation_brackets"):
                out[key] = not full_detail
        return out


# ---------------------------------------------------------------------------
# Text fit - the one estimate in this file, and why it is a maximum
# ---------------------------------------------------------------------------
# Per-character advance of the header font, in pixels. It exists ONLY to predict
# a width before anything has been drawn. DETECTION needs no estimate at all:
# EA's SVG carries `textLength`, its own measured advance, on every rendered run,
# so the linter compares EA's numbers with EA's rects. A composer has no render
# to read, which is the whole reason a number is needed here.
#
# CALIBRATED AS A MAXIMUM, NOT A MEAN, and that is the point of it. Read off live
# renders (EA 17.1, the header font at its default size), per character over the
# SPACE-FREE runs - which is what has to fit on one line, because EA breaks on
# spaces and never inside a word:
#
#      4 chars /  17 px = 4.25
#      8 chars /  39 px = 4.88
#     10 chars /  48 px = 4.80
#     12 chars /  54 px = 4.50
#     10 chars /  55 px = 5.50   <- the maximum
#     31 chars / 152 px = 4.90
#
# The mean of that population is 4.9 and taking it would UNDER-PREDICT the
# widest measured string by 6%. Under-prediction is precisely the failure being
# prevented: a box that is nearly wide enough is a box EA still grows, and the
# render then disagrees with the geometry every other check reads. So the
# interval is [5.50, inf) - below 5.5 a measured string is known to be
# under-predicted, above it the only cost is width - and the bottom of that
# interval is taken, because a prevention floor should be the smallest figure
# that is not known to be wrong.
#
# Over-prediction is cheap and self-correcting. At 5.5 the 36-character name
# from the live sweep is predicted at 198 px where EA drew 169, so the box comes
# out about 30 px wider than it strictly had to be - and the next verify
# measures the truth exactly rather than inheriting the estimate.
#
# NOT VALIDATED FOR: any font other than the one measured (the measurement
# varied neither the size nor a per-element style override), and non-Latin or
# full-width glyphs. A run of wide capitals is the case that could still exceed
# it. The linter stays the backstop for all of those, because it measures
# instead of predicting.
#
# AND A STATED POPULATION WITH NO GUARD IS THE SAME DEFECT ONE LAYER DOWN, so
# the "not validated for" paragraph above is now enforced rather than merely
# written: `CALIBRATED_REPERTOIRE` is the character set the measurement covered,
# `unvalidated_glyphs` names what a caller's name carries outside it, and
# `SpecFit.extrapolated` reports it wherever `fit_spec` is used. See
# `width_to_fit` for what the guard does about a full-width glyph, and why that
# is a derivation rather than a second guess.
HEADER_ADVANCE_PX = 5.5

#: The characters `HEADER_ADVANCE_PX` was calibrated on: printable ASCII, which
#: is what the measured strings contained. Anything else is an EXTRAPOLATION -
#: possibly a fine one for Latin-1 or Cyrillic, which occupy the same width class,
#: and definitely not for a full-width glyph.
CALIBRATED_REPERTOIRE = frozenset(chr(c) for c in range(0x20, 0x7F))

#: What a full-width glyph is charged, as a MULTIPLE of the calibrated advance.
#: Derived, not measured: Unicode East Asian Width `W` and `F` mean the glyph
#: occupies two character cells, and 5.5 is the widest advance any single cell in
#: the calibrated population reached, so two cells cannot be narrower than
#: `2 * HEADER_ADVANCE_PX`. It is a FLOOR on the prediction and therefore errs
#: toward a wider box, which this module's own reasoning calls the cheap and
#: self-correcting direction. A measurement in the target font would replace it.
FULL_WIDTH_CELLS = 2


def _longest_unbroken_run(name: str) -> str:
    """The longest run in a name that EA cannot break - what must fit one line.

    EA WRAPS ON SPACES ONLY. Measured: a 31-character name with no spaces in a
    100-wide box was drawn as a single unwrapped line running 52 px past both
    borders, and the same name with spaces in it came back as one text run per
    line at a 13 px pitch. So a multi-word name breaks itself and only its
    longest word has to fit; a name with no spaces has to fit whole.

    Split on the space character alone, not on whitespace generally. A tab or a
    newline inside an element name was never measured, and treating one as a
    break would predict a narrower box on no evidence - keeping the run joined
    predicts a wider one, which is the safe direction.
    """
    return max(name.split(" "), key=len, default="")


def width_to_fit(name: str) -> int:
    """The narrowest box width at which this name reads as fitting.

    `longest unbroken run x HEADER_ADVANCE_PX`, plus `LABEL_MARGIN` of clearance
    on each side. Two thresholds are in play and the wider one is targeted:

    * EA stops growing the drawn box once the text fits the usable inner width,
      measured at `w - 6` for the narrower of the two shapes probed and `w - 5`
      for the other, +/-1. Call it `w - 7` to cover both with the tolerance.
    * The label stops reading as touching the border at `LABEL_MARGIN` px of
      clearance per side, so `w - 2 * LABEL_MARGIN`.

    `2 * LABEL_MARGIN` is 16, which is wider than 7, so aiming at the clearance
    satisfies the growth threshold as well. Aiming at 7 instead would trade the
    error for the warning and call it fixed.

    WHAT THIS DOES NOT PROMISE, because EA's wrap is greedy. It packs as many
    words onto a line as the break width holds, so a MULTI-WORD name can still
    come out reading as cramped: at a width that leaves the whole name fitting
    one line with only 5 px each side, EA puts it on one line rather than
    breaking it, and nothing here moves that. Guaranteeing clearance for a
    multi-word name means sizing the box to the WHOLE name - a 58-character
    title would demand a 335-wide box - which overrides the notation's own
    measured convention for content that renders perfectly well today. Measured
    live: multi-word names produced no findings at all, and unbreakable ones
    produced every one. So this fits the run EA cannot break and leaves the rest
    to the rule that measures rather than predicts.
    """
    run = _longest_unbroken_run(name)
    if not run:
        return 0
    return math.ceil(_advance(run)) + 2 * LABEL_MARGIN


def _advance(run: str) -> float:
    """The predicted pixel advance of one unbreakable run.

    Inside `CALIBRATED_REPERTOIRE` this is `len(run) * HEADER_ADVANCE_PX`, which
    is the whole of the calibration. Outside it:

    * a FULL-WIDTH glyph is charged `FULL_WIDTH_CELLS * HEADER_ADVANCE_PX`,
      because it occupies two character cells and no cell in the calibrated
      population was wider than 5.5. That is a floor derived from a Unicode
      property and the measured maximum, not a second estimate;
    * anything else out of repertoire is charged the calibrated advance, because
      there is nothing better to charge it and no reason to think it is wider.
      This is the case `unvalidated_glyphs` exists to make visible: the number
      is an extrapolation and the linter, which measures, is the backstop.
    """
    if not run:
        return 0.0
    wide = sum(1 for ch in run if unicodedata.east_asian_width(ch) in ("W", "F"))
    return (len(run) + wide * (FULL_WIDTH_CELLS - 1)) * HEADER_ADVANCE_PX


def unvalidated_glyphs(name: str) -> tuple[str, ...]:
    """The distinct characters of `name` that `HEADER_ADVANCE_PX` never measured.

    Sorted and de-duplicated, empty for a name entirely inside
    `CALIBRATED_REPERTOIRE`. This is the GUARD on that constant: a width predicted
    for a name containing any of these is an extrapolation past the population the
    constant was calibrated on, and a caller that cares must verify by measuring
    rather than trust the prediction. `fit_spec` surfaces it as
    `SpecFit.extrapolated` so a caller does not have to remember to ask.

    It reports rather than raising. A model whose element names are in Japanese or
    Russian is a legitimate model and must still compose; what it must not do is
    compose against a number that quietly claims a provenance it does not have.
    """
    return tuple(sorted({ch for ch in name if ch not in CALIBRATED_REPERTOIRE}))


class SpecFit(dict):
    """A `compose.py` spec that also says what the content's names cost it.

    It IS the spec - a plain `dict` subclass, equal to the dict it would have
    been, passable straight to any composer - so nothing downstream has to know
    this type exists. What it adds is the report: `conflicts`, `widened`,
    `requested_width`, `driver`, `extrapolated` and a one-line `note`.

    THE REPORT IS NOT OPTIONAL DECORATION. `sizing.default` is measured off real
    diagrams of the notation and `default_size_provenance` names whose
    measurement it is; an override is a figure the caller chose on purpose.
    Quietly substituting a third number for either of those would leave a caller
    reading a measured convention that was not the one used. So the width used is
    declared, and where the two could not both be honored the CHOICE is declared
    with it.

    `conflicts` is the machine-readable half and the one to branch on: a tuple of
    `compose.FitConflict`, each naming what did not fit, both options, and which
    was applied. A conflict whose `answered` is False is the default standing in
    for an answer nobody gave - ASK THE USER, then pass `on_misfit` back. The
    other four fields are the human-readable half and describe the width only:
    under `on_misfit="overlap"` nothing widened, so `widened` is False while
    `conflicts` is not empty, and that pair is the point rather than an
    inconsistency.
    """

    __slots__ = ("requested_width", "driver", "conflicts",
                 "extrapolated")

    def __init__(self, spec: Mapping[str, Any], requested_width: int,
                 driver: str = "",
                 conflicts: Sequence[FitConflict] = (),
                 extrapolated: Mapping[str, tuple] | None = None) -> None:
        super().__init__(spec)
        #: The `item_width` that was asked for, before any widening: the
        #: binding's measured default, or the caller's override of it.
        self.requested_width = int(requested_width)
        #: The name that would not fit the requested width, or "" if every name
        #: fitted. Set whichever answer was applied, because which name caused
        #: the conflict is the same fact either way.
        self.driver = driver
        #: The misfits, as `compose.FitConflict` records. Empty when the names
        #: fitted the width that was asked for.
        self.conflicts = tuple(conflicts)
        #: `{name: the glyphs in it HEADER_ADVANCE_PX was never calibrated on}`,
        #: for every name that carries any. Empty in the normal case. THE WIDTHS
        #: FOR THESE NAMES ARE EXTRAPOLATIONS, not measurements, and this is the
        #: field that says so; see `unvalidated_glyphs`.
        self.extrapolated = dict(extrapolated or {})

    @property
    def item_width(self) -> int:
        """The width actually used - widened, or the one that was asked for."""
        return int(self["item_width"])

    @property
    def widened(self) -> bool:
        return self.item_width > self.requested_width

    @property
    def conflict(self) -> FitConflict | None:
        """The one width misfit, or `None`. There is at most one per spec.

        `item_width` is a single number, so the names resolve to a single
        question about it - the widest of them. `conflicts` is still the plural
        because it is the shape every consumer of this mechanism reads.
        """
        return self.conflicts[0] if self.conflicts else None

    @property
    def unanswered_conflicts(self) -> tuple[FitConflict, ...]:
        """The conflicts still owed an answer from the user.

        A caller that wants one test for "must I ask about this diagram?" asks
        this rather than reading `answered` out of each record.
        """
        return tuple(c for c in self.conflicts if not c["answered"])

    @property
    def note(self) -> str:
        """One sentence for a report or a log, or "" when nothing conflicted.

        Reads the conflict rather than recomputing it, so the prose and the
        machine-readable record cannot disagree about which name or which
        numbers. Non-empty whenever a name did not fit, INCLUDING under
        `overlap`, where no width moved but a choice was still made.
        """
        parts = [" ".join(part for part in (c["note"], c["detail"]) if part)
                 for c in self.conflicts]
        if self.extrapolated:
            named = "; ".join(
                f"{name!r} contains " + ", ".join(repr(g) for g in glyphs)
                for name, glyphs in sorted(self.extrapolated.items()))
            parts.append(
                f"WIDTH EXTRAPOLATED: {named}. HEADER_ADVANCE_PX was calibrated on "
                "printable ASCII in one font only, so these widths are predictions "
                "past that population - measure the rendered diagram rather than "
                "trusting them.")
        return " ".join(parts)


def _apply_prefix(prefix: str, concept: str) -> str:
    """`ApplicationComponent` -> `ArchiMate_ApplicationComponent`.

    One implementation for both scopes that have a prefix. Two copies of a
    two-line rule is how the technology-scope and diagram-type-scope answers
    would eventually differ for the same input.
    """
    return f"{prefix}{concept}"


def _strip_prefix(prefix: str, stereotype: str) -> str:
    """The inverse of `_apply_prefix`. Unprefixed input comes back unchanged."""
    if prefix and stereotype.startswith(prefix):
        return stereotype[len(prefix):]
    return stereotype


class DiagramTypeBinding:
    """One diagram type's conventions, ready to hand to the engine.

    `sizing` and `spacing` are RESOLVED: what this diagram type states, over
    the measured values of the base diagram type it is drawn on. That is the
    pair a consumer wants, because an unstated gap resolving to the substrate's
    measured value is the whole point of the inheritance.

    `own_sizing` and `own_spacing` are what this binding's own document said,
    which is a different question and the one a provenance test asks: a figure
    is only this technology's measurement if this technology stated it.
    `substrate` names the diagram type the rest came from, or `""`.

    A diagram type may omit `sizing` altogether, or state per-concept sizes and
    omit `default`, and inherit the missing figures from its substrate. It may
    NOT end up without a `default`: `Binding.__init__` refuses that once the
    chain is merged, because a fallback box size is the one thing every diagram
    of the type needs. `default_size_is_inherited` and
    `default_size_provenance` are how a consumer tells an inherited figure from
    one this technology measured, and a report that prints a size should print
    which it is.

    `stereotype_prefix` is RESOLVED the same way and from a different place: this
    diagram type's own value if it states one, otherwise the TECHNOLOGY's, never
    the substrate's. `own_stereotype_prefix` is `None` when it states nothing,
    which is what separates a fallback from a declared `""`. See the module
    docstring for the two shipped technologies that forced the second scope.
    """

    __slots__ = ("technology", "name", "base", "grammar", "title", "sizing",
                 "spacing", "routing", "channels", "notes",
                 "own_sizing", "own_spacing", "substrate",
                 "own_stereotype_prefix", "stereotype_prefix")

    def __init__(self, technology: str, name: str, data: Mapping[str, Any],
                 technology_prefix: str = ""):
        self.technology = technology
        self.name = name
        # PRESENCE, not truth: `None` means the document said nothing and the
        # technology's value answers, while `""` is this diagram type's own
        # statement that its stereotypes are stored bare. A technology that
        # prefixes and a diagram type inside it that does not is a measured case -
        # see the module docstring - and `or` here would erase it.
        self.own_stereotype_prefix = (
            data["stereotype_prefix"] if "stereotype_prefix" in data else None)
        self.stereotype_prefix = (technology_prefix
                                  if self.own_stereotype_prefix is None
                                  else self.own_stereotype_prefix)
        for slot in ("base", "grammar", "title", "notes"):
            setattr(self, slot, data.get(slot, ""))
        self.sizing = dict(data["sizing"])
        self.spacing = dict(data["spacing"])
        self.routing = dict(data["routing"])
        self.channels = dict(data["channels"])
        # Default to the resolved values rather than to `{}`: a binding with no
        # parent states everything it has, and a caller reading `own_spacing`
        # must not see an empty mapping for the root of the tree.
        self.own_sizing = dict(data.get("own_sizing", self.sizing))
        self.own_spacing = dict(data.get("own_spacing", self.spacing))
        self.substrate = data.get("substrate", "")

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return f"DiagramTypeBinding({self.technology}::{self.name})"

    @property
    def mdg_diagram_type(self) -> str:
        """The `MDGDgm=` value EA writes for this diagram type."""
        return f"{self.technology}::{self.name}"

    @property
    def grammar_placement(self) -> str:
        """Who places this diagram type's geometry - see `GRAMMAR_PLACEMENT`."""
        return GRAMMAR_PLACEMENT.get(self.grammar, "")

    @property
    def geometry_is_composed(self) -> bool:
        """Whether the coordinates are OURS to compute.

        False does not mean unsupported. It means the positions come from EA -
        either because its general-purpose layout handles this shape acceptably
        and we tidy afterwards, or because the diagram type dictates the
        arrangement itself. Which of those, and whether it can be produced at
        all, is `grammar_is_producible`.
        """
        return self.grammar in COMPOSED_GRAMMARS

    @property
    def grammar_is_implemented(self) -> bool:
        """Whether the engine has a composer for this grammar.

        Read from the engine on every call, so a composer that ships flips this
        with no edit to a binding or to the vocabulary.

        False is a real answer, not an error, and it now has two causes worth
        telling apart: a composed grammar nobody has built yet, and a grammar
        whose geometry was never ours to compute. Do NOT read False as "cannot
        be produced" - that question is `grammar_is_producible`, and for a graph
        the answers differ. A consumer that finds this False and producible True
        should hand the diagram to EA's layout and tidy it, not give up.
        """
        return self.grammar in implemented_grammars()

    @property
    def grammar_is_producible(self) -> bool:
        """Whether a diagram of this type can be produced at all today.

        True by either route: a composed grammar whose composer exists, or a
        grammar EA's own layout places acceptably. False means the shape is
        recorded and nothing here can yet produce it - which is a statement
        about us, not about the notation.
        """
        return self.grammar in producible_grammars()

    @property
    def draws_its_own_title(self) -> bool:
        return self.title == "drawn"

    @property
    def inherits(self) -> bool:
        """Whether a substrate diagram type was found for this one.

        False for the base notation itself, and false for a diagram type whose
        `base` the parent leaves unbound - which is a real case rather than an
        error, since a base notation may decline a diagram type for want of a
        supportable figure. A caller that wants to know where a gap came from
        asks `inherited_spacing()`; one that finds this False is holding a
        diagram type whose unstated slots fall back to the engine.
        """
        return bool(self.substrate)

    def inherited_sizing(self) -> dict[str, dict[str, int]]:
        """The size entries that came from the substrate, not from this file."""
        return {concept: size for concept, size in self.sizing.items()
                if concept not in self.own_sizing}

    def inherited_spacing(self) -> dict[str, Any]:
        """The spacing keys that came from the substrate, not from this file."""
        return {key: value for key, value in self.spacing.items()
                if key not in self.own_spacing}

    @property
    def default_size_is_inherited(self) -> bool:
        """Whether `size_for()`'s fallback figure came from the substrate.

        `inherited_sizing()` answers this for every concept, but `default` is
        worth a name of its own for two reasons. It is the slot that decides the
        size of every concept the notation does not name, so a consumer that
        prints one box size is printing this one. And it is the only slot where
        the alternative to inheriting is a figure somebody typed in: a notation
        with too few diagrams to measure can now say so by staying silent, and
        this is what makes the silence visible afterwards rather than
        indistinguishable from a measurement.

        `inherited_sizing()` is also noisier than it looks here: the substrate's
        PER-CONCEPT sizes merge in too, so a diagram type ends up carrying
        concepts its own notation does not have. Those are harmless - nothing
        asks for a size for a concept the notation cannot hold - while an
        inherited `default` is asked for on every diagram.
        """
        return "default" not in self.own_sizing

    @property
    def default_size_provenance(self) -> str:
        """The `<Tech>::<DiagramType>` whose measurement `sizing.default` is.

        The substrate's when the figure was inherited, this diagram type's own
        when it states one. Never empty and never a guess: a diagram type that
        neither states a default nor inherits one is refused on load, so this
        always names a diagram type somebody measured - which is what makes it
        printable in a report.
        """
        return self.substrate if self.default_size_is_inherited \
            else self.mdg_diagram_type

    @property
    def stereotype_prefix_is_inherited(self) -> bool:
        """Whether `stereotype_prefix` came from the technology.

        True for every diagram type of a technology with one prefix, which is
        most of them. False means this diagram type stated its own - including a
        declared `""` inside a technology that prefixes, which `TOGAF Diagrams`
        is the inverse of and `StrategyMap` would be if a bare type turned up.
        """
        return self.own_stereotype_prefix is None

    @property
    def stereotype_prefix_provenance(self) -> str:
        """Which scope `stereotype_prefix` was read from.

        The technology id when the figure was inherited, `<Tech>::<DiagramType>`
        when this diagram type stated one. Printable in a report for the same
        reason `default_size_provenance` is: a lookup that silently missed is the
        failure mode this slot exists to prevent, so a reader should be able to
        see which scope answered.
        """
        return (self.technology if self.stereotype_prefix_is_inherited
                else self.mdg_diagram_type)

    def stereotype_for(self, concept: str) -> str:
        """`Objective` -> `SM_Objective`, under THIS diagram type's prefix.

        `Binding.stereotype_for` with no diagram type answers at technology
        scope, which is the right answer for a technology with one prefix and the
        wrong one for `StrategyMap`, whose six diagram types have six.
        """
        return _apply_prefix(self.stereotype_prefix, concept)

    def concept_for(self, stereotype: str) -> str:
        """The inverse. A stereotype without this type's prefix is unchanged."""
        return _strip_prefix(self.stereotype_prefix, stereotype)

    def size_for(self, concept: str = "") -> tuple[int, int]:
        """Box size for a notation concept, falling back to `default`.

        Takes the concept name (`ApplicationComponent`), not the stored
        stereotype (`ArchiMate_ApplicationComponent`); use `concept_for` here or
        `Binding.concept_for` if you are holding the latter. Where the prefix is
        per diagram type, THIS object's `concept_for` is the one to use: the
        technology-scope answer would leave `SM_` on the front of the key.
        """
        entry = self.sizing.get(concept) or self.sizing["default"]
        return int(entry["w"]), int(entry["h"])

    def claimed_channels(self) -> dict[str, str]:
        """Channel -> what the notation already uses it for."""
        claimed = {}
        fill = self.channels.get("fill")
        if fill:
            claimed["fill"] = fill
        for channel, meaning in (self.channels.get("claimed") or {}).items():
            claimed[channel] = meaning
        return claimed

    def free_channels(self) -> tuple[str, ...]:
        """Channels a second variable may legitimately use."""
        return tuple(self.channels.get("free") or ())

    def channel_is_free(self, channel: str) -> bool:
        return channel in self.free_channels()

    def default_route(self) -> str:
        return self.routing["default"]

    def route_for(self, relationship: str) -> str:
        """The route for a relationship type.

        `trunk_for` names the relationship types this notation habitually draws
        as a shared trunk - ArchiMate's Realization and Aggregation fan into
        one line rather than radiating - so they get the orthogonal route even
        where the diagram type's default is something looser.
        """
        if relationship in (self.routing.get("trunk_for") or ()):
            return self.routing.get("trunk_route", "OrthogonalSquare")
        return self.routing["default"]

    def spec(self, overrides: Mapping[str, Any] | None = None,
             names: Iterable[str] = (),
             on_misfit: str | None = None) -> SpecFit:
        """Build a `compose.py` spec from this diagram type's conventions.

        `sizing.default` becomes `item_width`/`item_height`; `spacing` is
        copied across verbatim, because its keys are the engine's own. Caller
        overrides win, so a caller can widen one diagram without editing the
        binding - but an override naming a key the engine does not have is
        refused here rather than by the engine, where the message would not
        mention the binding.

        PASS THE ITEM NAMES. `names` is the names that will go in the boxes, and
        with them `item_width` is widened until the longest word in the widest of
        them clears the border. Without them the width is the convention's, which
        is what it always was: a name too long for it is then drawn wider than it
        measures, and every check that reads the stored rect reads a rect EA does
        not paint.

        WHEN THE WIDTH AND THE NAME CANNOT BOTH BE HONORED, SAY SO RATHER THAN
        SETTLE IT. This used to read "there is no flag to turn the fitting off,
        because supplying the names IS the request; a knob would only exist to be
        left at the wrong setting." That was right that a caller supplying names
        wants them to fit, and wrong about whose call the conflict is. Widening
        the box and letting the text overlap the border are both legitimate
        drawings of the same content, and which one a diagram wants depends on
        the diagram - so the conflict is reported and the user is asked.

        `on_misfit` is where their answer goes, and it is an ANSWER, not a
        setting: `None` means nobody has answered, `"widen"` and `"overlap"` are
        the two things they can say. Widening is what happens when nobody
        answered, unchanged and for the same reason as before - EA grows a box it
        cannot fit whatever the stored rect says, so it is the only answer under
        which the geometry every later check reads is the geometry EA paints.
        What is new is that it is no longer silent: the returned `SpecFit`
        carries the misfit on `conflicts`, with both options, which was applied,
        and whether anybody chose it.

        `on_misfit="overlap"` keeps the width that was asked for. That is not a
        return to the old behavior, because the conflict is still reported - the
        difference between the two is a choice on the record and a default nobody
        saw.

        ITEM names, not group names. A band's or lane's title is drawn across a
        strip whose width comes from the band, not from `item_width`; feeding it
        in here would widen every item to fit a label that is not in one.

        The widening lands on `item_width`, which is the value every grammar
        falls back to, so the whole composition keeps one item width and peers
        stay the same size as each other. A per-band or per-node `item_width`
        stated in the layout input still wins over it - that is the caller
        sizing one group deliberately - and is not fitted here, because this
        method never sees it.

        The result is a `SpecFit`: a spec dict that also reports the widening.
        """
        width, height = self.size_for()
        spec: dict[str, Any] = {"item_width": width, "item_height": height}
        spec.update(self.spacing)
        for key, value in (overrides or {}).items():
            if key not in _SPEC_KEYS:
                raise BindingError(
                    f"spec override {key!r} is not a layout spec key. "
                    f"Known keys: {', '.join(sorted(_SPEC_KEYS))}")
            spec[key] = value

        # Refused here rather than by the engine, for the same reason an unknown
        # override key is: the engine's message would be about a layout spec and
        # would not mention the binding, sending the reader to the wrong file.
        if on_misfit is not None and on_misfit not in FIT_ANSWERS:
            raise BindingError(
                f"on_misfit must be one of "
                f"{', '.join(repr(a) for a in FIT_ANSWERS)} - the user's answer "
                f"to the widen-or-overlap question - got {on_misfit!r}")

        # Measured LAST, over the width that is actually in effect. An override is
        # exactly as capable of being too narrow for the content as a measured
        # default is - the live defect was found on a caller-chosen 60 - so
        # measuring before the override would leave the commoner case unfixed.
        requested = int(spec["item_width"])
        driver = ""
        needed = requested
        extrapolated: dict[str, tuple] = {}
        for i, name in enumerate(names):
            if not isinstance(name, str):
                raise BindingError(
                    f"names[{i}]: item names must be strings, got "
                    f"{type(name).__name__}")
            # The guard on HEADER_ADVANCE_PX's calibrated population, applied to
            # EVERY name and not only the widest: a name that fits the requested
            # width is still a name whose width was extrapolated, and the caller
            # deciding whether to verify needs all of them.
            unvalidated = unvalidated_glyphs(name)
            if unvalidated:
                extrapolated[name] = unvalidated
            want = width_to_fit(name)
            if want > needed:
                needed, driver = want, name

        detail = ""
        if driver:
            run = _longest_unbroken_run(driver)
            detail = (
                f"{driver!r} has a {len(run)}-character run with no space in it "
                f"to break on, which needs {width_to_fit(driver)}px. Under "
                f"{FIT_OVERLAP!r} the stored rect keeps the width asked for and "
                f"EA draws the name past it, so every check that reads the rect "
                f"reads a narrower box than the one on screen."
            )
        width, conflict = _engine.resolve_width_misfit(
            "spec.item_width",
            requested_width=requested,
            required_width=needed,
            driver=driver,
            driver_kind="item_name",
            on_misfit=on_misfit,
            detail=detail,
        )
        spec["item_width"] = width
        return SpecFit(spec, requested, driver,
                       (conflict,) if conflict is not None else (),
                       extrapolated=extrapolated)


class Viewpoint:
    """A standard view the notation itself defines.

    Notations publish their own catalogs - ArchiMate's viewpoints, TOGAF's
    deliverables, UAF's views. Holding that catalog as data is what lets the
    selection logic stay generic instead of growing a branch per notation.
    """

    __slots__ = ("technology", "name", "diagram_type", "intent", "admits",
                 "grammar", "notes")

    def __init__(self, technology: str, name: str, data: Mapping[str, Any]):
        self.technology = technology
        self.name = name
        self.diagram_type = data["diagram_type"]
        self.intent = tuple(data.get("intent") or ())
        self.admits = tuple(data.get("admits") or ())
        self.grammar = data.get("grammar", "")
        self.notes = data.get("notes", "")

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return f"Viewpoint({self.technology}::{self.name})"

    def admits_concept(self, concept: str) -> bool:
        return concept in self.admits

    @property
    def effective_grammar(self) -> str:
        """This viewpoint's own grammar, or `""` to mean its diagram type's.

        A viewpoint override is not decoration. ArchiMate's Capability and
        Organization viewpoints are nested grids drawn on a `Business` diagram
        type whose grammar is `layered-bands`, so a consumer that reads the
        diagram type's grammar and ignores the override composes a capability
        map as bands.
        """
        return self.grammar

    @property
    def grammar_is_implemented(self) -> bool | None:
        """Whether the engine has a composer for THIS viewpoint's grammar.

        `None` when the viewpoint states no grammar of its own -- ask the
        diagram type instead. The distinction matters: `False` means "we know we
        cannot", `None` means "this viewpoint has no opinion", and returning
        `False` for both would make every ordinary viewpoint look unsupported.

        Without this, the documented path -- rank viewpoints, take one, ask its
        diagram type whether the grammar is implemented -- answers `True` for a
        nested grid and composes it as bands.
        """
        if not self.grammar:
            return None
        return self.grammar in implemented_grammars()

    @property
    def grammar_is_producible(self) -> bool | None:
        """Whether a view of THIS viewpoint's grammar can be produced today.

        `None` on the same terms as above. Both answers exist here for the same
        reason the override exists: a viewpoint that overrides its diagram type's
        composed grammar with one EA places is not unsupported, and a consumer
        reading only `grammar_is_implemented` would drop it.
        """
        if not self.grammar:
            return None
        return self.grammar in producible_grammars()

    @property
    def geometry_is_composed(self) -> bool | None:
        """Whether this viewpoint's own grammar is one we compute. `None` when it
        states no grammar of its own."""
        if not self.grammar:
            return None
        return self.grammar in COMPOSED_GRAMMARS


class Binding:
    """One technology's diagram conventions."""

    __slots__ = ("technology", "display_name", "extends", "stereotype_prefix",
                 "notes", "source", "diagram_types", "viewpoints",
                 "presentation_profiles")

    def __init__(self, data: Mapping[str, Any], source: str = "<memory>"):
        self.source = source
        self.technology = data["technology"]
        self.display_name = data.get("display_name", "") or self.technology
        self.extends = data.get("extends") or None
        self.stereotype_prefix = data.get("stereotype_prefix", "") or ""
        self.notes = data.get("notes", "")
        # THE ONE VALIDATION THAT CANNOT LIVE IN `_validate`. Everything else a
        # binding must say, it says in its own document, so `_validate` can ask
        # for it. `sizing.default` is different: after `extends` it is a property
        # of the RESOLVED chain, and `_validate` runs on each document before
        # `_merge` has put the substrate underneath it. Asking here - the single
        # point every load path reaches, with the merge already done - is what
        # lets a diagram type inherit a measured default while still refusing one
        # that resolves to nothing. A parent is fully constructed before it is
        # used as a substrate, so a substrate that was found always carries a
        # default and only an unfound one can reach the raise.
        self.diagram_types = {}
        for name, body in data["diagram_types"].items():
            bound = DiagramTypeBinding(self.technology, name, body,
                                       technology_prefix=self.stereotype_prefix)
            if "default" not in bound.sizing:
                raise BindingError(
                    _no_resolved_default(source, self.extends, bound))
            self.diagram_types[name] = bound
        self.viewpoints = {
            name: Viewpoint(self.technology, name, body)
            for name, body in (data.get("viewpoints") or {}).items()
        }
        self.presentation_profiles = {
            name: PresentationProfile(name, body)
            for name, body in (data.get("presentation_profiles") or {}).items()
        }

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return f"Binding({self.technology!r}, {len(self.diagram_types)} types)"

    # -- lookups, all raising rather than returning None ---------------------
    def diagram_type(self, name: str) -> DiagramTypeBinding:
        try:
            return self.diagram_types[name]
        except KeyError:
            raise BindingError(
                f"{self.technology}: no diagram type {name!r}. Declared: "
                f"{', '.join(sorted(self.diagram_types))}") from None

    def viewpoint(self, name: str) -> Viewpoint:
        try:
            return self.viewpoints[name]
        except KeyError:
            raise BindingError(
                f"{self.technology}: no viewpoint {name!r}. Declared: "
                f"{', '.join(sorted(self.viewpoints)) or '(none)'}") from None

    def profile(self, name: str) -> PresentationProfile:
        try:
            return self.presentation_profiles[name]
        except KeyError:
            raise BindingError(
                f"{self.technology}: no presentation profile {name!r}. "
                f"Declared: "
                f"{', '.join(sorted(self.presentation_profiles)) or '(none)'}"
            ) from None

    # -- the prefix problem -------------------------------------------------
    def prefix_for(self, diagram_type: str | None = None) -> str:
        """The prefix in force, at technology scope or for one diagram type.

        `None` asks the technology, which is what a caller who does not know
        which diagram type it is holding can honestly ask for. Naming a diagram
        type this binding does not declare raises, as every other lookup here
        does, rather than quietly answering at the wrong scope.
        """
        if diagram_type is None:
            return self.stereotype_prefix
        return self.diagram_type(diagram_type).stereotype_prefix

    def stereotype_for(self, concept: str,
                       diagram_type: str | None = None) -> str:
        """`ApplicationComponent` -> `ArchiMate_ApplicationComponent`.

        What EA stores in `t_object.Stereotype`. The prefix is data because it is
        not guessable: EA 17.1's built-in ArchiMate3 MDG prefixes, BPMN2.0 does
        not, and an install carrying a differently built MDG can differ again.

        `diagram_type` resolves it at the scope that technology measured at.
        Omitting it answers at technology scope and keeps every single-prefix
        binding working unchanged; passing it is how `StrategyMap`, whose six
        diagram types have six different prefixes, gets a true answer at all.
        """
        return _apply_prefix(self.prefix_for(diagram_type), concept)

    def concept_for(self, stereotype: str,
                    diagram_type: str | None = None) -> str:
        """The inverse. A stereotype without the prefix is returned unchanged.

        Unchanged rather than rejected: models contain elements stereotyped
        from other technologies, or from none, and a lookup helper is the wrong
        place to have an opinion about that. `diagram_type` scopes it as above.
        """
        return _strip_prefix(self.prefix_for(diagram_type), stereotype)

    def diagram_type_for_mdgdgm(self, mdgdgm: str) -> DiagramTypeBinding | None:
        """Resolve an `MDGDgm=<Tech>::<DiagramType>` value against this binding.

        Returns None when the value names another technology, so a caller can
        try the next binding. Note that only about half of real diagrams carry
        `MDGDgm` at all - the rest identify themselves through `Diagram_Type` -
        so resolution needs a second path, which is `APT-2026-0147`.
        """
        technology, _, diagram_type = str(mdgdgm).partition("::")
        if technology != self.technology:
            return None
        return self.diagram_types.get(diagram_type)

    def viewpoints_admitting(self, concepts: Sequence[str]) -> list[Viewpoint]:
        """Viewpoints that admit every concept given, best coverage first.

        Ranking is on admissibility only. Intent matching and content
        profiling belong to the advisor, not to the data layer.
        """
        wanted = set(concepts)
        matches = [vp for vp in self.viewpoints.values()
                   if wanted <= set(vp.admits)]
        return sorted(matches, key=lambda vp: (len(vp.admits), vp.name))


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------
def _validate_prefix(block: Mapping[str, Any], where: str) -> dict:
    """`{"stereotype_prefix": ...}` when the document declares it, else `{}`.

    PRESENCE IS THE RECORD, at both the scopes that have this slot, because `""`
    has to survive as a STATEMENT rather than as an absence. A binding whose
    install carries an unprefixed build of its parent's technology says so by
    writing `stereotype_prefix: ""` and `_merge` must not overwrite that with the
    parent's; a diagram type whose own stereotypes are bare inside a technology
    that prefixes says so the same way, and the technology's value must not
    overwrite that either. Returning a dict rather than a value is what carries
    "said nothing" through to the loader without a sentinel string.

    The type check runs BEFORE any coercion: `block.get(...) or ""` would turn
    `0` and `[]` into `""` and pass a check that never ran.
    """
    if "stereotype_prefix" not in block:
        return {}
    prefix = block["stereotype_prefix"]
    if prefix is None:
        prefix = ""            # `stereotype_prefix: ~` means no prefix
    if not isinstance(prefix, str):
        raise BindingError(
            f"{where}.stereotype_prefix: expected a string or omitted, "
            f"got {prefix!r}")
    return {"stereotype_prefix": prefix}


def _validate_channels(block: Any, where: str) -> dict:
    channels = _mapping(block, where)
    _reject_unknown(channels, _CHANNEL_BLOCK_KEYS, where)
    if "fill" not in channels:
        raise BindingError(
            f"{where}.fill: required. State what the notation uses fill for, "
            f"or `~` if fill is genuinely unclaimed. This block is the "
            f"mechanized form of 'each notation already claims some visual "
            f"channels', so leaving it out is not a neutral default.")
    fill = channels["fill"]
    if fill is not None and not isinstance(fill, str):
        raise BindingError(
            f"{where}.fill: expected a string describing what fill means, or "
            f"`~`, got {fill!r}")

    claimed = _mapping(channels.get("claimed") or {}, f"{where}.claimed")
    for channel, meaning in claimed.items():
        if channel not in CHANNELS:
            raise BindingError(
                f"{where}.claimed.{channel}: not a visual channel. Known: "
                f"{', '.join(sorted(CHANNELS))}")
        if not isinstance(meaning, str) or not meaning.strip():
            raise BindingError(
                f"{where}.claimed.{channel}: expected a string describing "
                f"what it means, got {meaning!r}")
    if "fill" in claimed:
        raise BindingError(
            f"{where}.claimed.fill: fill is declared by {where}.fill, not "
            f"here. Two places to say one thing is one place too many.")

    free = _str_list(channels.get("free") or [], f"{where}.free")
    for i, channel in enumerate(free):
        if channel not in CHANNELS:
            raise BindingError(
                f"{where}.free[{i}]: {channel!r} is not a visual channel. "
                f"Known: {', '.join(sorted(CHANNELS))}")
    # The one cross-check that matters: a channel cannot be both spoken for and
    # available. A binding that says so has told a consumer it is safe to
    # overwrite something the notation needs.
    spoken_for = set(claimed) | ({"fill"} if fill else set())
    conflict = sorted(spoken_for & set(free))
    if conflict:
        raise BindingError(
            f"{where}.free: {', '.join(repr(c) for c in conflict)} "
            f"{'is' if len(conflict) == 1 else 'are'} already claimed by this "
            f"notation, so listing "
            f"{'it' if len(conflict) == 1 else 'them'} as free would tell a "
            f"consumer it is safe to overwrite the notation's own meaning.")
    if len(set(free)) != len(free):
        raise BindingError(f"{where}.free: contains a duplicate")

    out = {"fill": fill, "free": free, "claimed": claimed}
    if channels.get("notes"):
        out["notes"] = channels["notes"]
    return out


def _validate_sizing(block: Any, where: str) -> dict:
    """Shape only: every entry is `{w, h}` and both are positive whole numbers.

    `default` IS STILL REQUIRED, but not here, and that is the one rule this
    function used to own. A fallback box size is a property of the RESOLVED
    chain rather than of one document: a diagram type drawn on a measured
    substrate inherits the substrate's default, which is the whole point of
    `extends`. This function runs on the raw document, BEFORE `_merge`, so it
    cannot see what the substrate supplies and asking here could only ever
    refuse a diagram type that in fact resolves to a measured figure. The
    question is asked once, of the merged values, in `Binding.__init__`.

    Nothing was relaxed by the move. An unmeasured technology still cannot ship
    a diagram type with no default; what it can now do is INHERIT one, which is
    traceable to the diagram type the figure was measured on in a way a number
    typed into a YAML file is not.
    """
    sizing = _mapping(block, where)
    out = {}
    for concept, entry in sizing.items():
        path = f"{where}.{concept}"
        size = _mapping(entry, path)
        _reject_unknown(size, frozenset({"w", "h"}), path,
                        {"width": "use 'w'", "height": "use 'h'"})
        for axis in ("w", "h"):
            if axis not in size:
                raise BindingError(f"{path}.{axis}: required")
        out[concept] = {"w": _positive_int(size["w"], f"{path}.w"),
                        "h": _positive_int(size["h"], f"{path}.h")}
    return out


def _no_resolved_default(source: str, extends: str | None,
                         bound: "DiagramTypeBinding") -> str:
    """The message for a diagram type whose `sizing.default` nothing supplies.

    Worth a function because "required" on its own is the least useful thing
    this failure can say. An author who omitted `sizing` was trying to inherit,
    so what they need is WHICH SUBSTRATE was looked at - which is also the only
    thing that reveals a `base:` pointing at a diagram type the immediate parent
    does not declare, the case a deeper chain hits.

    The message names exactly two ways out, and copying a figure in from another
    notation is not one of them. That asymmetry is the point of allowing the
    omission at all: an inherited default traces to a measurement of the diagram
    type it was measured on, while a number typed into a YAML file traces to
    nobody and reads identically to a measured one forever after.
    """
    where = f"{source}.diagram_types.{bound.name}.sizing.default"
    if not extends:
        looked = (
            f"{bound.name} has no substrate to inherit one from: this binding "
            f"declares no `extends`, so there is no notation underneath it.")
    elif bound.base:
        looked = (
            f"{bound.name} says it is drawn on base {bound.base!r}, but "
            f"{extends} declares no diagram type of that name, so the "
            f"substrate looked for was not found.")
    else:
        looked = (
            f"{bound.name} states no `base`, so the substrate looked for was "
            f"{extends}{MDG_SEPARATOR}{bound.name}, which {extends} does not "
            f"declare.")
    return (
        f"{where}: required, and nothing in the chain supplies it. {looked} "
        f"There are two ways out and only two: state a default here that you "
        f"have MEASURED on diagrams of this type, or point `base:` at a diagram "
        f"type whose binding already measures one. Do not copy a figure in from "
        f"another notation - an inherited default traces to the diagram type it "
        f"was measured on, and a borrowed one traces to nobody.")


def _validate_spacing(block: Any, where: str) -> dict:
    spacing = _mapping(block or {}, where)
    _reject_unknown(
        spacing, _SPEC_KEYS, where,
        {
            "pitch": "a pitch includes the box it steps over; you probably "
                     "mean item_gap_x / item_gap_y",
            "h": "use item_gap_x",
            "v": "use item_gap_y",
            "gap_x": "use item_gap_x",
            "gap_y": "use item_gap_y",
        },
    )
    # Values are not range-checked here. `compose.py` owns those rules - a
    # pitch smaller than its item, a negative gap - and duplicating them would
    # give two answers that can disagree. What is checked is the key, because
    # an unknown key is the failure the engine cannot see.
    return dict(spacing)


def _validate_routing(block: Any, where: str) -> dict:
    routing = _mapping(block, where)
    _reject_unknown(routing, _ROUTING_KEYS | {"trunk_route"}, where)
    if "default" not in routing:
        raise BindingError(
            f"{where}.default: required. Leaving the route unstated means "
            f"every connector falls back to whatever EA last did, which is "
            f"not a convention.")
    for key in ("default", "trunk_route"):
        if key not in routing:
            continue
        name = _text(routing[key], f"{where}.{key}")
        if _normalize_route(name) not in ROUTE_NAMES:
            raise BindingError(
                f"{where}.{key}: {name!r} is not a route EA accepts. Known: "
                f"Direct, AutoRouting, CustomLine, TreeVertical, "
                f"TreeHorizontal, LateralVertical, LateralHorizontal, "
                f"OrthogonalSquare, OrthogonalRounded, Bezier")
    out = {"default": _text(routing["default"], f"{where}.default")}
    if "trunk_route" in routing:
        out["trunk_route"] = _text(routing["trunk_route"],
                                   f"{where}.trunk_route")
    if "trunk_for" in routing:
        out["trunk_for"] = _str_list(routing["trunk_for"],
                                     f"{where}.trunk_for")
        if "trunk_route" not in out:
            out["trunk_route"] = "OrthogonalSquare"
    if routing.get("notes"):
        out["notes"] = routing["notes"]
    return out


def _validate_diagram_type(name: str, block: Any, where: str) -> dict:
    body = _mapping(block, where)
    _reject_unknown(body, _DIAGRAM_TYPE_KEYS, where)

    grammar = _text(body.get("grammar"), f"{where}.grammar")
    if grammar not in GRAMMARS:
        raise BindingError(
            f"{where}.grammar: {grammar!r} is not one of the {len(GRAMMARS)} "
            f"grammars. Known: {', '.join(sorted(GRAMMARS))}. "
            f"{len(COMPOSED_GRAMMARS)} of them are layouts this library "
            f"computes coordinates for; 'graph' is for a graph or a tree that "
            f"EA's own layout places and we tidy; 'ea-semantic' is for a "
            f"diagram type that dictates its own arrangement. The variety of "
            f"real diagrams resolves into these; if this diagram type genuinely "
            f"needs another, that is a finding, not a binding.")

    title = _text(body.get("title"), f"{where}.title")
    if title not in TITLE_CONVENTIONS:
        raise BindingError(
            f"{where}.title: {title!r} is not a title convention. Known: "
            f"{', '.join(TITLE_CONVENTIONS)}. Neither can be the silent "
            f"default - the corpus splits by notation, so a diagram with two "
            f"titles and a diagram with none are equally likely mistakes.")

    # `sizing` is the one required-looking block a diagram type may omit, and
    # the asymmetry with `routing` and `channels` below is deliberate. Those two
    # are STATEMENTS a child has to make for itself - a notation's routing habit
    # and the channel its own shape script claims are not the substrate's - so
    # silence there is an oversight. A box size is a MEASUREMENT, and the
    # measurement of the diagram type this one is drawn on is the honest answer
    # for a notation that has too few diagrams of its own to measure. Whether
    # the chain in fact supplies one is checked after `_merge`, in `Binding`.
    if "routing" not in body:
        raise BindingError(f"{where}.routing: required")
    if "channels" not in body:
        raise BindingError(f"{where}.channels: required")

    out = {
        "grammar": grammar,
        "title": title,
        # `or {}` so an omitted block and an explicitly empty one mean the same
        # thing - inherit all of it - the way `spacing` already treats them.
        "sizing": _validate_sizing(body.get("sizing") or {},
                                   f"{where}.sizing"),
        "spacing": _validate_spacing(body.get("spacing"), f"{where}.spacing"),
        "routing": _validate_routing(body["routing"], f"{where}.routing"),
        "channels": _validate_channels(body["channels"], f"{where}.channels"),
    }
    for optional in ("base", "notes"):
        if body.get(optional):
            out[optional] = _text(body[optional], f"{where}.{optional}")
    # Recorded only when stated, so that a declared `""` overrides a prefixed
    # technology instead of reading as silence. See `_validate_prefix`.
    out.update(_validate_prefix(body, where))
    return out


def _validate_viewpoint(name: str, block: Any, where: str,
                        diagram_types: Mapping[str, Any]) -> dict:
    body = _mapping(block, where)
    _reject_unknown(body, _VIEWPOINT_KEYS, where)

    diagram_type = _text(body.get("diagram_type"), f"{where}.diagram_type")
    if diagram_type not in diagram_types:
        raise BindingError(
            f"{where}.diagram_type: {diagram_type!r} is not declared by this "
            f"binding. Declared: {', '.join(sorted(diagram_types))}")

    out: dict[str, Any] = {"diagram_type": diagram_type}
    if "intent" in body:
        out["intent"] = _str_list(body["intent"], f"{where}.intent")
    if "admits" in body:
        admits = _str_list(body["admits"], f"{where}.admits")
        if len(set(admits)) != len(admits):
            raise BindingError(f"{where}.admits: contains a duplicate")
        out["admits"] = admits
    if body.get("grammar"):
        grammar = _text(body["grammar"], f"{where}.grammar")
        if grammar not in GRAMMARS:
            raise BindingError(
                f"{where}.grammar: {grammar!r} is not one of the "
                f"{len(GRAMMARS)} grammars. Known: "
                f"{', '.join(sorted(GRAMMARS))}")
        out["grammar"] = grammar
    if body.get("notes"):
        out["notes"] = _text(body["notes"], f"{where}.notes")
    return out


def _validate_profile(name: str, block: Any, where: str) -> dict:
    body = _mapping(block, where)
    _reject_unknown(body, _PROFILE_KEYS, where,
                    {"hide_connector_labels":
                     "profiles say what they SHOW; use connector_labels"})
    out: dict[str, Any] = {}
    for key, value in body.items():
        if key in ("description",):
            out[key] = _text(value, f"{where}.{key}")
        elif key == "compartments":
            if isinstance(value, str):
                if value not in _COMPARTMENT_VALUES:
                    raise BindingError(
                        f"{where}.compartments: {value!r} is not "
                        f"{' or '.join(repr(v) for v in _COMPARTMENT_VALUES)}, "
                        f"and not a list of compartment names")
                out[key] = value
            else:
                out[key] = _str_list(value, f"{where}.compartments")
        else:
            if not isinstance(value, bool):
                raise BindingError(
                    f"{where}.{key}: expected true or false, got {value!r}")
            out[key] = value
    # `direction_only` says "show one line per pair, with its direction" - it is
    # meaningless unless something is being collapsed, and a profile that sets
    # it alone reads as if it does something.
    if out.get("direction_only") and not out.get("collapse_parallel"):
        raise BindingError(
            f"{where}.direction_only: only means something under "
            f"collapse_parallel, which this profile does not set.")
    return out


def _validate(doc: Any, source: str) -> dict:
    data = _mapping(doc, source)
    _reject_unknown(data, _TOP_LEVEL_KEYS, source,
                    {"diagramTypes": "use diagram_types",
                     "technology_id": "use technology"})

    technology = _text(data.get("technology"), f"{source}.technology")
    if "::" in technology:
        raise BindingError(
            f"{source}.technology: {technology!r} contains '::'. The "
            f"technology id is the part BEFORE the '::' in an "
            f"`MDGDgm=<Tech>::<DiagramType>` value.")

    if not data.get("diagram_types"):
        raise BindingError(
            f"{source}.diagram_types: required, and must declare at least one "
            f"diagram type")
    raw_types = _mapping(data["diagram_types"], f"{source}.diagram_types")

    out: dict[str, Any] = {
        "technology": technology,
        "extends": data.get("extends") or None,
        "diagram_types": {
            name: _validate_diagram_type(
                name, body, f"{source}.diagram_types.{name}")
            for name, body in raw_types.items()
        },
    }
    if out["extends"] is not None:
        out["extends"] = _text(out["extends"], f"{source}.extends")
        if out["extends"] == technology:
            raise BindingError(
                f"{source}.extends: a binding cannot extend itself")
    # Recorded ONLY when the document declares it - `_validate_prefix` holds the
    # whole reason, and a diagram type's own prefix goes through the same helper
    # so the two scopes cannot drift apart.
    out.update(_validate_prefix(data, source))
    for optional in ("display_name", "notes"):
        if data.get(optional):
            out[optional] = _text(data[optional], f"{source}.{optional}")

    out["viewpoints"] = {
        name: _validate_viewpoint(
            name, body, f"{source}.viewpoints.{name}", out["diagram_types"])
        for name, body in _mapping(data.get("viewpoints") or {},
                                   f"{source}.viewpoints").items()
    }
    out["presentation_profiles"] = {
        name: _validate_profile(
            name, body, f"{source}.presentation_profiles.{name}")
        for name, body in _mapping(data.get("presentation_profiles") or {},
                                   f"{source}.presentation_profiles").items()
    }
    return out


# ---------------------------------------------------------------------------
# Loading
# ---------------------------------------------------------------------------
def _yaml():
    try:
        import yaml  # type: ignore
    except ImportError:  # pragma: no cover - environment-dependent
        raise BindingError(
            "PyYAML is required to read a language binding; "
            "pip install pyyaml") from None
    return yaml


def _parse(text: str, source: str) -> Any:
    yaml = _yaml()
    try:
        # safe_load, always. It is why a binding cannot carry executable
        # content: `!!python/object` is refused by the parser, not by a check
        # here that someone could forget to run.
        return yaml.safe_load(text)
    except yaml.YAMLError as exc:
        raise BindingError(f"{source}: not valid YAML: {exc}") from None


def load_binding_text(text: str, source: str = "<memory>") -> Binding:
    """Validate and load a binding from YAML text. Used by the tests."""
    return Binding(_validate(_parse(text, source), source), source=source)


def load_binding(path: str | Path, _seen: frozenset[str] = frozenset()
                 ) -> Binding:
    """Load, validate and resolve a binding file.

    `extends` is resolved against the same directory and names the notation
    underneath this one, whose diagram types become the substrate each of this
    binding's own diagram types is measured against - see `_merge`. Child
    statements win throughout; only what a child leaves unstated is inherited. A
    cycle is refused by name rather than by recursion depth.
    """
    path = Path(path)
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise BindingError(f"cannot read binding {path}: {exc}") from None

    source = path.name
    data = _validate(_parse(text, source), source)
    parent_id = data.get("extends")
    if parent_id:
        if parent_id in _seen or data["technology"] in _seen:
            chain = ", ".join(sorted(_seen | {data["technology"]}))
            raise BindingError(
                f"{source}.extends: cycle through {chain}")
        parent_path = _binding_path(parent_id, path.parent)
        if parent_path is None:
            raise BindingError(
                f"{source}.extends: no binding for technology {parent_id!r} "
                f"in {path.parent}")
        parent = load_binding(parent_path,
                              _seen=_seen | {data["technology"]})
        data = _merge(parent, data)
    return Binding(data, source=source)


def _merge(parent: Binding, child: dict) -> dict:
    """Child over parent: the substrate under each diagram type, catalogs added.

    THE CHILD'S DIAGRAM TYPES STAY THE CHILD'S. Each one is placed on the
    parent's diagram type it says it is drawn on and takes the measured values
    it does not state for itself; none of the parent's diagram types joins the
    child's catalog. See the module docstring for why the catalog union this
    replaced is wrong once the parent is the base notation - it invents diagram
    types the child's MDG never declared, and makes every diagram identified by
    its base type ambiguous across every binding drawn on that base.

    `viewpoints` and `presentation_profiles` DO merge one level as before, and
    the asymmetry is the point: a viewpoint catalog and a presentation scheme
    are not claims about what EA declares, so a technology that publishes none
    of its own is better off with its parent's than with nothing.
    """
    merged = dict(child)
    merged["diagram_types"] = {
        name: _on_substrate(name, body, parent)
        for name, body in (child.get("diagram_types") or {}).items()
    }
    for catalog in ("viewpoints", "presentation_profiles"):
        inherited = {
            name: _unwrap(value)
            for name, value in getattr(parent, catalog).items()
        }
        inherited.update(child.get(catalog) or {})
        merged[catalog] = inherited
    # `not merged.get(...)` cannot tell `""` from absent, and the difference is
    # load-bearing: a child that declares `stereotype_prefix: ""` is stating that
    # ITS technology has no prefix, and silently inheriting the parent's would
    # make every stereotype lookup miss without complaining.
    if "stereotype_prefix" not in merged:
        merged["stereotype_prefix"] = parent.stereotype_prefix
    return merged


def _on_substrate(name: str, body: Mapping[str, Any],
                  parent: Binding) -> dict:
    """Fill one diagram type's unstated sizes and gaps from the one it is drawn on.

    The substrate is the parent diagram type named by `base` - the same value
    `create_diagram` is called with - or, for a child that states no `base`, the
    parent's diagram type of the same name, which is how a house binding
    refining its own technology keeps working.

    PER KEY, CHILD WINS. A size the child states for a concept is the child's,
    and so is `sizing.default`: a stereotyped element is the size its own MDG
    draws it, not the size the substrate draws a plain one. Only concepts and
    gap keys the child is silent about come from the substrate, which is where
    the engine's own defaults used to answer instead.

    A `base` the parent does not declare leaves the type unchanged and
    `substrate` empty. That is not an error: a base notation may decline a
    diagram type for want of a figure it can support, and inventing a fallback
    here would state a value nobody measured.

    `stereotype_prefix` IS NOT IN THAT LIST AND MUST NOT JOIN IT. A prefix says
    whose MDG named the stereotype, so the substrate - a diagram type belonging
    to the PARENT technology - is the wrong place to fall back to; the right one
    is this technology, which `DiagramTypeBinding` resolves against. Copying
    UML's `Logical` prefix onto ArchiMate's `Business` would be the same category
    error as copying its `graph` over `layered-bands`, and would land in
    `own_sizing`'s blast radius: a provenance report would then call the parent's
    prefix this diagram type's own statement.
    """
    substrate = parent.diagram_types.get(body.get("base") or name)
    if substrate is None:
        return dict(body)
    out = dict(body)
    out["own_sizing"] = dict(body["sizing"])
    out["own_spacing"] = dict(body["spacing"])
    out["sizing"] = {**substrate.sizing, **body["sizing"]}
    out["spacing"] = {**substrate.spacing, **body["spacing"]}
    out["substrate"] = substrate.mdg_diagram_type
    return out


def _unwrap(value: Any) -> Any:
    """Turn a parent's loaded object back into the dict form `Binding` takes."""
    if isinstance(value, Viewpoint):
        out = {"diagram_type": value.diagram_type}
        for name in ("intent", "admits", "grammar", "notes"):
            if getattr(value, name):
                out[name] = getattr(value, name)
        return out
    if isinstance(value, PresentationProfile):
        return dict(value.settings)
    return value  # pragma: no cover - defensive


def _bindings_dir(directory: str | Path | None = None) -> Path:
    if directory is not None:
        return Path(directory)
    return _HERE.parent / "bindings"


def _slug(technology: str) -> str:
    """`BPMN2.0` -> `bpmn2.0`. The id is authoritative; the filename is a slug.

    Lowercased and with path separators and spaces flattened, so a technology
    id containing `/` (several UAF ids do) cannot escape the bindings
    directory.
    """
    out = []
    for ch in technology.strip().lower():
        out.append(ch if (ch.isalnum() or ch in "._-") else "-")
    return "".join(out).strip("-") or "binding"


def declared_technologies(directory: str | Path | None = None
                          ) -> dict[str, tuple[str, ...]]:
    """`{technology id: filenames that declare it}`, every id claimed in `directory`.

    IDENTITY ONLY. Each file is parsed and its `technology` key read; nothing is
    validated. That is deliberate: this is the one view of the directory that every
    reader can agree on, and it has to answer "who claims this id" for a file that
    does not load as well as for one that does. Filenames are sorted, so the answer
    does not depend on the order the filesystem enumerates them.
    """
    directory = _bindings_dir(directory)
    if not directory.is_dir():
        return {}
    claims: dict[str, list[str]] = {}
    for path in sorted(directory.glob("*.yaml")):
        try:
            doc = _parse(path.read_text(encoding="utf-8"), path.name)
        except (BindingError, OSError):
            continue
        if isinstance(doc, Mapping) and isinstance(doc.get("technology"), str):
            claims.setdefault(doc["technology"], []).append(path.name)
    return {tech: tuple(sorted(files)) for tech, files in sorted(claims.items())}


def binding_conflicts(directory: str | Path | None = None
                      ) -> dict[str, tuple[str, ...]]:
    """`{technology id: filenames}` for ids claimed by MORE than one file.

    Empty when the directory is unambiguous. This never raises, so a caller that
    wants to report a shadowed id rather than fail on it - an audit, a health
    check, a test - can see the conflict without catching anything.
    """
    return {tech: files for tech, files in declared_technologies(directory).items()
            if len(files) > 1}


def _require_unique_technologies(directory: Path) -> None:
    """Raise `DuplicateTechnology` when any id in `directory` is claimed twice."""
    conflicts = binding_conflicts(directory)
    if not conflicts:
        return
    detail = "; ".join(f"{tech!r} is declared by " + ", ".join(files)
                       for tech, files in conflicts.items())
    raise DuplicateTechnology(
        f"duplicate technology id in {directory}: {detail}. Each technology id "
        "must be declared by exactly one binding file: rename the id or delete "
        "the shadow. Nothing in this directory can be resolved until it is fixed, "
        "because the catalog, the resolver and the audit would each pick a "
        "different file.")


def _binding_path(technology: str, directory: Path) -> Path | None:
    # BEFORE the slug shortcut below, because the realistic duplicate is a second
    # file with a descriptive name beside the slug-named one, and the shortcut
    # would return the slug file without ever noticing the other claim.
    _require_unique_technologies(directory)
    candidate = directory / f"{_slug(technology)}.yaml"
    if candidate.is_file():
        return candidate
    # Fall back to reading each binding's declared id, which is authoritative -
    # a file named anything at all still binds the technology it says it does.
    for path in sorted(directory.glob("*.yaml")):
        try:
            doc = _parse(path.read_text(encoding="utf-8"), path.name)
        except (BindingError, OSError):
            continue
        if isinstance(doc, Mapping) and doc.get("technology") == technology:
            return path
    return None


def find_binding(technology: str,
                 directory: str | Path | None = None) -> Binding | None:
    """Load the binding for a technology id, or None if there is not one.

    None rather than an exception: not having a binding for a technology is
    normal - most repositories use several we have never bound - and a caller
    should say so and fall back, not crash. What must NOT happen is composing
    against the wrong binding, which is why the declared `technology` is
    checked rather than trusting the filename.
    """
    directory = _bindings_dir(directory)
    if not directory.is_dir():
        return None
    path = _binding_path(technology, directory)
    if path is None:
        return None
    binding = load_binding(path)
    if binding.technology != technology:  # pragma: no cover - defensive
        return None
    return binding


def available_bindings(directory: str | Path | None = None) -> dict[str, str]:
    """`{technology id: filename}` for every valid binding on hand.

    Invalid bindings are omitted rather than raising, so one bad file does not
    make the whole catalog unreadable; load it directly to see why.

    A DUPLICATE technology id is the exception, and raises `DuplicateTechnology`.
    Omitting a file whose id another file also claims is not omitting it, it is
    choosing between them: this used to keep whichever came last in sorted order
    and say nothing, while `find_binding` resolved the same id to the FIRST file,
    so the catalog and the composer could name different files for one technology.
    `binding_conflicts()` reports the same finding without raising.
    """
    directory = _bindings_dir(directory)
    if not directory.is_dir():
        return {}
    _require_unique_technologies(directory)
    out = {}
    for path in sorted(directory.glob("*.yaml")):
        try:
            binding = load_binding(path)
        except BindingError:
            continue
        out[binding.technology] = path.name
    return out


# ---------------------------------------------------------------------------
# Resolution: from the technologies a repository has installed to a binding
# ---------------------------------------------------------------------------
# `find_binding` answers "is there a binding for this id", which is half the
# question. The half a caller actually holds is "this repository has THESE
# technologies installed, and this diagram identifies itself like THIS - which
# binding applies, if any?"
#
# Two measured facts decide the shape of the answer:
#
#   * A diagram states its MDG diagram type in `t_diagram.StyleEx`, as
#     `MDGDgm=<Tech>::<DiagramType>`, and that key carries a value on only
#     about 47% of real diagrams - 526 of the 1129 in the example model
#     shipped with EA 17.1. The other 603 carry the key EMPTY and identify
#     themselves through `t_diagram.Diagram_Type` alone, which holds a base EA
#     diagram type (Logical 209, Custom 143, Statechart 44, ...). A resolver
#     keyed on the qualified value alone therefore fails on the majority of a
#     real repository, which is why the `Diagram_Type` path below exists.
#   * One repository holds many technologies - 24 in that same model - and two
#     of them can claim the same diagram type. Which one EA renders a diagram
#     with is a runtime matter the repository file does not record.
#
# So there are three answers that are not a binding, and a caller has to be
# able to tell them apart:
#
#   `unbound`        nothing installed claims this diagram. The common case -
#                    123 of the 147 catalogued diagrams - and not a failure:
#                    the caller falls back to the engine's own defaults, which
#                    renders correctly, just not conventionally.
#   `ambiguous`      several installed technologies claim it, so no binding is
#                    chosen. Deliberately NOT first-match: an answer decided by
#                    the order the bindings arrived in is indistinguishable
#                    from a correct one and wrong about as often as not. The
#                    same mistake was made once in the diagram advisor's
#                    stereotype attribution and is fixed there the same way.
#   `not-installed`  the id named is not among this repository's technologies.
#                    This is the failure mode the whole module is built
#                    against: the ids are not guessable, and a lookup on a
#                    guessed one otherwise resolves to nothing without
#                    complaining.
#
# A resolution therefore reports how it was reached and how much that is worth,
# and every unresolved answer carries a `reason` naming what was looked for.

# EA's own key inside `t_diagram.StyleEx`, and the separator inside its value.
MDG_STYLE_KEY = "MDGDgm"
MDG_SEPARATOR = "::"

# How a resolution was reached -> how much confidence it is worth. One dict, so
# the two cannot drift: a path with no confidence, and a confidence attached to
# no path, are both unrepresentable.
#
#   `qualified`      the diagram itself states `<Tech>::<DiagramType>`. The
#                    technology wrote that value; nothing is inferred.
#   `diagram-type`   `Diagram_Type` matched the NAME of a diagram type exactly
#                    one installed binding declares. An inference, and a sound
#                    one, but the diagram did not say so itself.
#   `base-type`      `Diagram_Type` matched only the EA base type a binding
#                    declares its diagram type is drawn on. Weak on purpose:
#                    base types are shared - inside each shipped binding every
#                    diagram type declares the same base as its siblings - so a
#                    single match here means only that one installed binding
#                    happens to use that base at all.
RESOLUTION_PATHS: dict[str, str] = {
    "qualified": "exact",
    "diagram-type": "inferred",
    "base-type": "weak",
    "ambiguous": "none",
    "unbound": "none",
    "not-installed": "none",
    "unidentified": "none",
}
RESOLVED_PATHS = frozenset(
    path for path, confidence in RESOLUTION_PATHS.items()
    if confidence != "none")


class Resolution:
    """Which binding applies to one diagram, how that was reached, and how much
    it is worth.

    An unresolved resolution is a first-class answer rather than an error:
    `binding` and `diagram_type` are None, `path` says which kind of nothing it
    is, and `reason` says what was looked for against what was on hand. A
    caller that finds `resolved` False should compose with the engine's
    defaults and report the diagram as unbound - never reach for a binding
    anyway.
    """

    __slots__ = ("path", "reason", "technology", "diagram_type_name",
                 "binding", "diagram_type", "candidates")

    def __init__(self, path: str, reason: str, *, technology: str = "",
                 diagram_type_name: str = "", binding: Binding | None = None,
                 diagram_type: DiagramTypeBinding | None = None,
                 candidates: Sequence[str] = ()):
        if path not in RESOLUTION_PATHS:
            raise BindingError(
                f"resolution path {path!r} is not one of: "
                f"{', '.join(sorted(RESOLUTION_PATHS))}")
        self.path = path
        self.reason = reason
        self.technology = technology
        self.diagram_type_name = diagram_type_name
        self.binding = binding
        self.diagram_type = diagram_type
        # Sorted, always. Which diagram types claim a value is a fact about the
        # repository; the order the bindings were handed over is not, and
        # letting it show here would put argument order back into the answer.
        self.candidates = tuple(sorted(candidates))

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return (f"Resolution({self.path!r}, {self.key or '(none)'}, "
                f"{self.confidence!r})")

    @property
    def confidence(self) -> str:
        """`exact`, `inferred`, `weak` or `none`, derived from `path`."""
        return RESOLUTION_PATHS[self.path]

    @property
    def resolved(self) -> bool:
        """Whether a binding was decided. True implies both objects are set."""
        return self.path in RESOLVED_PATHS

    @property
    def is_ambiguous(self) -> bool:
        """Several installed diagram types claim this diagram.

        Distinct from unbound, and the distinction is the point: "nothing
        claims this" is answered by falling back, while "several claim this"
        needs a human or an explicit choice by the caller. Collapsing the two
        would hide the one that cannot be automated.
        """
        return self.path == "ambiguous"

    @property
    def key(self) -> str:
        """The `<Tech>::<DiagramType>` this resolved to, or `""`."""
        if self.technology and self.diagram_type_name:
            return f"{self.technology}{MDG_SEPARATOR}{self.diagram_type_name}"
        return ""


def mdg_diagram_key(style_ex: str) -> str:
    """Read the `<Tech>::<DiagramType>` a diagram states about itself.

    `"MDGDgm=X::Y;DUID=A1B2;"` gives `"X::Y"`; anything else gives `""`.

    `""` covers three cases a resolver treats identically: the key is absent,
    the key is present but empty - which is the measured majority, 603 of 1129
    diagrams - or its value holds no `::`. All three mean the diagram has not
    named its MDG diagram type and the `Diagram_Type` path has to answer.

    Pairs split on `;` and each partitions on its FIRST `=`, because this value
    contains `::` and neighboring StyleEx values contain `=` inside nested
    sub-lists. The authoritative StyleEx parser - the one that round-trips a
    whole string without dropping the keys EA needs - lives in the server; the
    skills bundle deliberately does not import the server, and what is needed
    here is the read of one key, so this is that read rather than a second
    parser to keep in step.
    """
    for part in str(style_ex or "").split(";"):
        name, separator, value = part.partition("=")
        if not separator or name.strip() != MDG_STYLE_KEY:
            continue
        value = value.strip()
        return value if MDG_SEPARATOR in value else ""
    return ""


def _installed_ids(installed: Any) -> frozenset[str]:
    """The technology ids a repository has, from ids or from a mapping of them.

    A mapping is accepted because the natural thing a caller holds is the
    runtime inventory keyed by technology id, whose values are each
    technology's own definition; only the keys take part in resolving.

    A bare string is refused rather than iterated. Passing one id as a string
    would otherwise present three one-character technologies, match nothing,
    and report the repository as having nothing installed - a wrong answer
    delivered confidently, which is the outcome this module exists to prevent.
    """
    if isinstance(installed, str):
        raise BindingError(
            "installed technologies: expected a collection of technology ids "
            "or a mapping keyed by them, got a single string. A bare string "
            "iterates as characters, which would match nothing at all.")
    if isinstance(installed, Mapping):
        source: Iterable[Any] = installed.keys()
    elif isinstance(installed, Iterable):
        source = installed
    else:
        raise BindingError(
            f"installed technologies: expected a collection of technology ids "
            f"or a mapping keyed by them, got {type(installed).__name__}")
    return frozenset(
        str(entry).strip() for entry in source if str(entry).strip())


def _declared_diagram_types(installed: Any) -> dict[str, frozenset[str]]:
    """What each installed technology says its own diagram types are.

    Read from the `diagram_types` list of a runtime MDG definition - the shape
    the server's runtime technology reader returns, entries carrying `name`,
    `alias` and `base`. Used ONLY to make a miss more informative: if a diagram
    states a diagram type its own technology does not declare, the stated value
    is misspelled rather than merely unbound, and which of those it is changes
    what the reader does next.

    Never used to resolve. A technology declaring a diagram type says nothing
    about how to compose one, which is what a binding is for.
    """
    if not isinstance(installed, Mapping):
        return {}
    out: dict[str, frozenset[str]] = {}
    for technology, definition in installed.items():
        if not isinstance(definition, Mapping):
            continue
        entries = definition.get("diagram_types") or ()
        names = {str(entry.get("name", "")).strip()
                 for entry in entries if isinstance(entry, Mapping)}
        out[str(technology).strip()] = frozenset(n for n in names if n)
    return out


def bindings_for_technologies(installed: Any,
                              directory: str | Path | None = None
                              ) -> dict[str, Binding]:
    """`{technology id: binding}` for the installed technologies we can bind.

    The intersection, and only the intersection. A binding on disk for a
    technology this repository does not have is not a candidate for anything:
    composing a diagram to the conventions of a technology EA has not loaded
    produces a diagram that reads as that notation and is not one.

    Load once and hand the result to `resolve_diagram` for every diagram -
    resolution is per-diagram, never per-repository, and re-reading the YAML
    once per diagram is the difference between a scan and a wait.
    """
    directory = _bindings_dir(directory)
    out: dict[str, Binding] = {}
    for technology in sorted(_installed_ids(installed)):
        binding = find_binding(technology, directory)
        if binding is not None:
            out[technology] = binding
    return out


def _candidate_bindings(bindings: Any, ids: frozenset[str],
                        directory: str | Path | None) -> dict[str, Binding]:
    """The bindings in play, keyed by technology and filtered to the installed.

    Sorted on the way in so that nothing downstream can depend on the order the
    caller listed them.
    """
    if bindings is None:
        return bindings_for_technologies(ids, directory)
    supplied = (list(bindings.values()) if isinstance(bindings, Mapping)
                else list(bindings))
    return {binding.technology: binding
            for binding in sorted(supplied, key=lambda b: b.technology)
            if binding.technology in ids}


def _bound_summary(ids: frozenset[str], catalog: Mapping[str, Binding]) -> str:
    return (f"{len(catalog)} of the {len(ids)} installed "
            f"technolog{'y' if len(ids) == 1 else 'ies'} "
            f"{'has' if len(catalog) == 1 else 'have'} a binding"
            + (f" ({', '.join(sorted(catalog))})" if catalog else ""))


def _resolve_qualified(key: str, ids: frozenset[str],
                       catalog: Mapping[str, Binding],
                       declared: Mapping[str, frozenset[str]]) -> Resolution:
    """The diagram stated `<Tech>::<DiagramType>` itself. Final either way.

    There is no fall-through to the `Diagram_Type` path on a miss, and that is
    a decision rather than an omission. A diagram stating a type we have no
    binding for - each shipped binding leaves one of its technology's declared
    types deliberately unbound - would fall through to its base type and
    resolve to a SIBLING diagram type of the same technology: a plausible
    binding for a diagram that had already said it was something else. The
    honest answer to "I know what this is and I cannot bind it" is that it is
    unbound.
    """
    technology, _, name = key.partition(MDG_SEPARATOR)
    technology, name = technology.strip(), name.strip()
    if technology not in ids:
        return Resolution(
            "not-installed", technology=technology, diagram_type_name=name,
            reason=(
                f"the diagram states {key!r}, whose technology id "
                f"{technology!r} is not among the {len(ids)} this repository "
                f"has installed. Check it against the installed inventory "
                f"rather than against the notation's name - an id carries its "
                f"own version and is not guessable, and a lookup on a guessed "
                f"one resolves to nothing without complaining."))
    binding = catalog.get(technology)
    if binding is None:
        misspelled = (technology in declared
                      and name not in declared[technology])
        return Resolution(
            "unbound", technology=technology, diagram_type_name=name,
            reason=(
                f"{technology!r} is installed but has no binding on hand, so "
                f"{key!r} resolves to no conventions; compose with the "
                f"engine's defaults. " + (
                    f"Note that {technology!r} does not declare a diagram type "
                    f"named {name!r} either, so the stated value is misspelled "
                    f"as well as unbound."
                    if misspelled else _bound_summary(ids, catalog))))
    bound = binding.diagram_types.get(name)
    if bound is None:
        return Resolution(
            "unbound", technology=technology, diagram_type_name=name,
            reason=(
                f"the binding for {technology!r} does not bind the diagram "
                f"type {name!r} that the diagram states. Bound: "
                f"{', '.join(sorted(binding.diagram_types))}. A binding may "
                f"leave a declared diagram type out on purpose, and where it "
                f"does, falling back to the engine's defaults is the intended "
                f"outcome rather than a gap."))
    return Resolution(
        "qualified", technology=technology, diagram_type_name=bound.name,
        binding=binding, diagram_type=bound,
        reason=(f"the diagram states {key!r} and the binding for "
                f"{technology!r} binds that diagram type."
                + _inherited_default_note(binding, bound)))


def _inherited_default_note(binding: Binding,
                            bound: DiagramTypeBinding) -> str:
    """The sentence a resolution adds when the box size is not this technology's.

    A RESOLUTION THAT INHERITS ITS DEFAULT SIZE SAYS SO. `sizing.default` may be
    inherited from the substrate, which is the honest answer for a notation with
    too few diagrams of its own to measure - but the figure a caller is about to
    lay out with is then a measurement of a different diagram type, and nothing
    downstream could tell that from the number. Appended to the reason of every
    resolved answer, so both resolution paths report it and neither can drift
    from the other; empty when the technology measured its own.
    """
    if not bound.default_size_is_inherited:
        return ""
    return (f" Its default box size is inherited from "
            f"{bound.default_size_provenance}, not measured by "
            f"{binding.technology}.")


def _decide(matches: Mapping[str, tuple], path: str, looked_for: str,
            how: str) -> Resolution:
    """One claimant resolves; more than one is ambiguous and names them all."""
    if len(matches) == 1:
        found, (binding, bound) = next(iter(matches.items()))
        return Resolution(
            path, technology=binding.technology, diagram_type_name=bound.name,
            binding=binding, diagram_type=bound,
            reason=(f"{looked_for!r} {how}, and exactly one installed binding "
                    f"claims it: {found}."
                    + _inherited_default_note(binding, bound)))
    return Resolution(
        "ambiguous", diagram_type_name=looked_for, candidates=tuple(matches),
        reason=(
            f"{len(matches)} installed diagram types claim {looked_for!r}: "
            f"{', '.join(sorted(matches))}. Which one EA renders this diagram "
            f"with is a runtime matter the repository file does not record, so "
            f"no binding is chosen. Choose one explicitly, or compose with the "
            f"engine's defaults - taking the first would be an answer decided "
            f"by the order the bindings were listed in."))


def _resolve_by_diagram_type(diagram_type: str, ids: frozenset[str],
                             catalog: Mapping[str, Binding]) -> Resolution:
    """The 53% path: the diagram named no MDG type, only its `Diagram_Type`.

    Name first, base second, never both at once. An exact diagram-type name is
    a stronger statement than the base type it is drawn on, so a name match is
    taken on its own; the base is consulted only when no installed binding
    declares a diagram type by that name at all.
    """
    by_name = {}
    for binding in catalog.values():
        bound = binding.diagram_types.get(diagram_type)
        if bound is not None:
            by_name[bound.mdg_diagram_type] = (binding, bound)
    if by_name:
        return _decide(by_name, "diagram-type", diagram_type,
                       "is the name of a bound diagram type")

    by_base = {}
    for binding in catalog.values():
        for bound in binding.diagram_types.values():
            if bound.base and bound.base == diagram_type:
                by_base[bound.mdg_diagram_type] = (binding, bound)
    if by_base:
        return _decide(by_base, "base-type", diagram_type,
                       "is the EA base type a bound diagram type is drawn on")

    return Resolution(
        "unbound", diagram_type_name=diagram_type,
        reason=(
            f"no installed binding declares a diagram type named "
            f"{diagram_type!r}, or drawn on one, and the diagram states no MDG "
            f"diagram type of its own. {_bound_summary(ids, catalog)}. This is "
            f"the ordinary answer across most of a real repository: compose "
            f"with the engine's defaults and report the diagram as unbound."))


def resolve_diagram(installed: Any, *, style_ex: str = "",
                    diagram_type: str = "", bindings: Any = None,
                    directory: str | Path | None = None) -> Resolution:
    """Which binding applies to one diagram, given what the repository has.

    `installed` is the technology ids EA reports for this repository - or a
    mapping from those ids to each technology's own runtime definition, which
    lets a miss say whether a stated diagram type was misspelled. The ids are
    authoritative: a binding for a technology that is not installed is never
    used, however well it matches.

    `style_ex` is the diagram's `t_diagram.StyleEx` and `diagram_type` its
    `t_diagram.Diagram_Type`. Pass both; which of them can answer is precisely
    what the caller cannot know in advance, and on most diagrams it is the
    second.

    `bindings` are pre-loaded bindings - from `bindings_for_technologies` - so
    that resolving a whole repository reads the YAML once instead of once per
    diagram. Omit it and they are loaded from `directory`.

    The chain, in order, each step reporting its own confidence:

      1. `MDGDgm=<Tech>::<DiagramType>` from `StyleEx`, where that technology is
         installed and bound. Exact, and final whether or not it resolves.
      2. `Diagram_Type` matching the name of exactly one bound diagram type.
      3. `Diagram_Type` matching the EA base type of exactly one bound diagram
         type. Weak.

    Anything else is an unresolved `Resolution` that says which kind of nothing
    it is - see `RESOLUTION_PATHS`. Note the registered-technology inventory is
    not a step in the chain but the filter applied to every step of it, which is
    the difference between "a binding exists" and "this repository can use it".
    """
    ids = _installed_ids(installed)
    catalog = _candidate_bindings(bindings, ids, directory)
    key = mdg_diagram_key(style_ex)
    diagram_type = str(diagram_type or "").strip()

    if key:
        return _resolve_qualified(key, ids, catalog,
                                  _declared_diagram_types(installed))
    if diagram_type:
        return _resolve_by_diagram_type(diagram_type, ids, catalog)
    return Resolution(
        "unidentified",
        reason=(
            "the diagram carries no MDG diagram type in its StyleEx and no "
            "Diagram_Type, so there is nothing to resolve against. Distinct "
            "from unbound: nothing was looked up, rather than looked up and "
            "not found."))

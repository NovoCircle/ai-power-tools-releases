#!/usr/bin/env python3
"""Measure the numbers a language binding needs from a Sparx-authored model.

A binding (`bindings/<tech>.yaml`) states element sizes and the gap between
neighbors for one modeling technology. Those numbers are conventions, and a
convention that was guessed is worse than one that is absent. This tool mines
them from a model in which the technology is drawn in practice - Sparx's own
example model, `EAExample.qea` - so that each new binding starts from a
measurement with a sample size attached instead of an estimate.

    python measure_binding.py --list
    python measure_binding.py --technology BPMN2.0 --diagram-type "Business Process"
    python measure_binding.py --technology UML --diagram-type "Use Case"

HERMETIC
--------
The model is COPIED to a private temporary directory and the copy is opened
read-only as SQLite. The original is never opened, never written, and EA is
never asked anything: there is no COM in this module. If a `-journal` or `-wal`
sidecar sits next to the model, EA (or something else) has it open mid-write
and a copy would not be consistent, so the tool refuses rather than measuring a
torn file.

The model path is a parameter. Left out, it comes from the `EA_EXAMPLE_MODEL`
environment variable, and failing that from the EA install directory that
`%ProgramFiles%` names. Nothing here hard-codes a drive or a user.

WHAT IS MEASURED, AND HOW EA STORES IT
--------------------------------------
Everything comes from three tables: `t_diagram` (which diagrams exist and which
technology they belong to), `t_diagramobjects` (one rectangle per element per
diagram) and `t_object` (the element's stereotype and type).

**EA's y axis points up and the model's coordinates are negative.** For every
one of the 9,980 rectangles in EAExample, `RectTop` is greater than
`RectBottom`, and the values are mostly below zero: the top of a diagram is 0
and things hang below it as -10, -80, -150. So

    width  = right - left
    height = top - bottom          (NOT bottom - top: that is always negative)

and "A is above B" means A's bottom edge is a larger number than B's top edge,
so the vertical gap is `A.bottom - B.top`. Getting this backwards silently
turns every vertical measurement negative or halves it. `Rect` below is the one
place the convention lives.

TECHNOLOGY AND DIAGRAM TYPE ARE DATA, NOT GUESSES
-------------------------------------------------
`t_diagram.StyleEx` carries `MDGDgm=<Technology>::<DiagramType>` - for example
`BPMN2.0::Business Process`, with a space and a `.0`. Neither is guessable and
a wrong guess matches nothing without complaint, so `list_technologies()`
reads the ids from the data and an unknown id raises with the closest real ones.

**`MDGDgm` is present but EMPTY on most diagrams.** In EAExample the key exists
on 1,122 of 1,129 diagrams and has a value on 526. Attribution therefore has
two paths, and the result says which one each diagram took:

1. `MDGDgm` names the technology: attributed. An explicit tag for a DIFFERENT
   technology is never overridden by path 2.
2. `MDGDgm` is empty: the diagram is attributed to the technology only if its
   `Diagram_Type` is one of the base types that technology's tagged diagrams
   use (ArchiMate3 diagrams are `Logical`; BPMN2.0 are `Analysis`) AND at least
   half of its stereotyped elements carry a stereotype that appears on the
   technology's tagged diagrams and on no other technology's. (Exclusivity
   matters: BPMN and BPMN 1.1 both store `Activity`.) `Diagram_Type` alone is
   not enough - 208 untagged diagrams are plain `Logical`.

In EAExample path 2 attributes nothing for ArchiMate3 or BPMN2.0: every diagram
of either is tagged. The path exists for technologies where that is not so.

SIZES
-----
Per stereotype, the modal (width, height) with its count, the share of the
sample it covers, and n. The mode is reported as absent when it is a tie: ten
text annotations that are ten different sizes have no mode, and picking the
first one Python happens to return would present an accident as a convention.

The stereotype key is the name as stored, and the technology's prefix
(`ArchiMate_`) is measured from the data and reported separately, so a binding
that lists concepts the way the specification names them can be written.

`default` is the pooled modal size of the elements whose size is a choice.
Elements whose size is fixed by the notation - a stereotype with at least
`MIN_SAMPLE` instances of which at least 90% share one size, which is what
events, gateways and junctions look like - are excluded from that pool,
because otherwise 173 BPMN events (30x30) outvote the 212 activities that are
the box a diagram is made of. If that leaves nothing (every stereotype is
fixed), the pool is everything. This is a heuristic and it is labeled as one.

ADJACENCY - THE DEFINITION THE GAP NUMBERS REST ON
--------------------------------------------------
A gap is measured between two elements A and B on the same diagram when B is
A's NEAREST NEIGHBOR in a direction:

* Direction. Horizontal: B lies to the right of A and their vertical extents
  overlap by more than `min_overlap` of the smaller extent (default: any
  positive overlap, i.e. they share a row). Vertical: B lies below A and their
  horizontal extents overlap likewise (they share a column).
* Nearest. Among every object on the diagram that qualifies, B has the smallest
  gap. A note, a text label or a data object counts even when it is not the
  kind of element being measured. **A pair separated by a third element is
  therefore not a measurement**: the third element is nearer, so the pair loses,
  and if that third element is not itself a measured element the pair is
  dropped rather than reassigned.
* Same context. A and B must sit inside exactly the same set of containers. An
  object is a container when its rectangle encloses another object's. Two
  elements in different lanes, or one inside a group and one outside it, are
  separated by a boundary, and the distance across a boundary is a fact about
  the boundary. Containers are never endpoints and never intervene between
  siblings.
* Positive gap only. Touching or overlapping rectangles are tiles or errors, not
  spacing; they are excluded and counted.
* Endpoints. Both A and B must be stereotyped, and neither may be a Note, Text
  or Boundary. `endpoint_stereotypes` narrows this further.

Each qualifying element contributes at most one horizontal and one vertical
measurement, so n counts elements that HAVE a neighbor, not element pairs in
the abstract. A gap is reported as median AND mode, each with n; the mode also
carries its own count, because a mode of 10 in 61 is a 16% cluster and a reader
should be able to see how much weight it bears.

This is `rule="strict"`, the default. It measures the gap an engine should
leave between two items it places side by side INSIDE THE SAME container, which
is what `item_gap_x` / `item_gap_y` mean. The gap between things in different
groups is a different quantity (`band_gap`, `grid_pad`), and the strict rule
keeps it out of the population.

THE HISTORICAL RULE - `rule="historical"`
-----------------------------------------
The numbers in the shipped bindings were recorded without a written method.
This is the rule that reproduces them, established by measurement rather than
recovered from notes, and kept selectable so the claim can be re-run:

* Endpoints are as above (stereotyped, not Note/Text/Boundary, not a container).
* B is A's nearest neighbor among ENDPOINTS ONLY, in the same direction with
  positive overlap and a positive gap.
* There is no same-container test and no third-element test: an intervening
  note, or a lane or group boundary, does not stop a pair.

On EAExample.qea (EA 17.1 build 1716) it gives, for ArchiMate3: 61 horizontal
and 68 vertical pairs, medians 76 and 47.5, modes 78 and 38. The recorded
figures are 61 and 69 pairs, medians 76 and 47, modes 78 and 38. That is a
reproduction to within one pair, so the historical population is this one.

For BPMN2.0 / Business Process it does NOT reproduce: 355 h and 262 v pairs,
medians 45 and 85, against the recorded 315 and 175, 41 and 63. With endpoints
narrowed to Activity, events and Gateway it gives 319 and 178 pairs, medians 43
and 74.5: the counts approach the recorded ones and the vertical median does
not. The BPMN figures were evidently taken over a population that no rule here
recovers exactly.

What the strict rule drops relative to the historical one, measured on the same
model. Cross-container pairs (A and B in different container sets): ArchiMate3
4 h and 11 v of 61 and 68; BPMN 49 h and 99 v of 355 and 262 (43 h and 70 v
of 319 and 178 with the narrowed endpoints). Pairs with a nearer intervening
object that is not an endpoint, in the same container: ArchiMate3 0 and 0; BPMN
1 h and 1 v (5 h and 9 v narrowed). Almost all of the difference is the
container test, which is why the BPMN vertical median moves most: the lanes
that stack its diagrams put a boundary between most vertical neighbors.

Use `historical` only to compare with the recorded figures. Use `strict` to
author a binding.

LOW N
-----
A result with fewer than `MIN_SAMPLE` observations carries `low_n=True`, and the
YAML formatter comments the value out and says so rather than emitting it as a
convention. It does not raise: three of three is real information, it is just
not enough to promote to a default.

`MIN_SAMPLE` IS DERIVED, AND IT IS DERIVED FOR A SIZE. Its constant carries the
population, the criterion and the result; the short version is that 10 is the
round number above the point where a subsample recovers a dominant modal size 95%
of the time. The same measurement over the gap populations says a gap MEDIAN needs
about four times that - `MIN_SAMPLE_GAP`, 38 - and that at 10 a gap median is
within 10% of the notation's median only 39% of the time. So `low_n` is not the
whole of the sample question, and `GapStat.thin_median` is the guard that fires on
the rest of it. It annotates rather than suppresses, because raising the
suppression floor would move every gap already authored against this tool.

CONCENTRATION - ONE DIAGRAM MUST NOT SPEAK FOR THE NOTATION
-----------------------------------------------------------
Gaps from every diagram are pooled into one population, and a pool is only as
representative as its spread. A single dense or generated diagram can supply most
of it: in the plain-UML corpus one Timing diagram supplies 11 of 17 vertical gaps,
all exactly 73, and one Object diagram 8 of 14. One Component diagram supplies 28 of
50 gaps, every one exactly 12, when the endpoints are the placed elements
(`Component`, `Package`, `Class`, `Object`); with ports and interfaces as endpoints
too it is 28 of 63, 44%, which is under the rule. The rule is sensitive to what
counts as an endpoint, so state the endpoints when you rely on it. Those medians
looked clean and were the diagram's, not the notation's.

So every `GapStat` records which diagram supplied the most gaps, how many, and
how many diagrams contributed at all. When ONE diagram supplies MORE THAN HALF of
the population (`MAX_DIAGRAM_SHARE`) the statistic is `concentrated`: the median
and mode stay on the result, so the pooled figure is still inspectable, but the
YAML formatter does not state a value. It comments the line out and names the
diagram and its share. Exactly half is not more than half. The threshold is a
keyword (`max_diagram_share`) for a caller who has a reason; the default is the
rule. It applies to gaps only: sizes are reported with their own n and are not
suppressed by it.

FURNITURE - AND WHEN IT IS THE CONTENT
--------------------------------------
`Note`, `Text` and `Boundary` objects are annotation furniture: never gap
endpoints, and they do not count toward whether a diagram is measurable. That is
right for a class diagram with a comment on it and wrong for a diagram made of
them. The UAF Framework diagram is 45 `Text` objects (each stereotyped
`UPDMPackage`) and two artifacts; excluding the tiles left it with no neighbors at
all, and the tool reported n=0.

A furniture-typed object on a diagram is promoted to CONTENT when BOTH hold:

1. Its Object_Type is the MAJORITY of the diagram's objects (more than half). The
   type is what the diagram is made of.
2. It carries a stereotype the technology OWNS: one that appears on the
   technology's tagged diagrams and on no other technology's (the same
   exclusivity that governs fallback attribution). Chrome carries none, or carries
   one shared everywhere: a plain annotation has no stereotype, and EA's own
   hyperlink tiles carry `NavigationCell`, which sits on many technologies'
   diagrams.

Majority alone is not a rule. On EAExample 14 technology-tagged diagrams have a
majority furniture type and only one, UAF Framework, is notation content. Seven of
the other 13 carry `NavigationCell` tiles (documentation pages that happen to be
tagged), and six are unstereotyped: pages of plain text, or eleven notes beside
nine `Standard` classes. Rule 2 alone is not a rule either: `TextAnnotation` is a
stereotype only BPMN uses, and its notes are annotation. Applied to every
technology in EAExample the two together promote objects on UAF Framework only.
A promoted object counts as an endpoint, its concept is its stereotype (or its
Object_Type when it has none), and `Measurement.content_promoted` says how many
objects of which type were promoted.

The override is `content_types`: furniture types the caller declares to be
content on EVERY diagram in scope (a promoted unstereotyped object is keyed by its
Object_Type, `Text`). `auto_content=False` turns rule 1+2 off. A diagram in scope
where a furniture type is the majority and is NOT promoted is counted in
`furniture_majority_diagrams`, with how many of those contributed no gap, and the
YAML says so: a diagram made of furniture is never silently measured as empty.

THE BASE NOTATION
-----------------
EA is a UML tool; UML is the base language every MDG technology is built from, and
it is the one notation that `MDGDgm` never names. No UML diagram carries the tag, so
`_attribute`'s way of learning a technology (from its tagged diagrams) has nothing to
learn from, and the technology id `UML` matches no tag. Asking for `UML` (the
constant `BASE_NOTATION`) takes the base-notation path instead:

* Diagrams. Those that claim no technology (`MDGDgm` empty or absent) and whose
  non-furniture elements are at least half UNSTEREOTYPED (`BASE_UNSTEREOTYPED_SHARE`).
  A diagram that is mostly stereotyped is an MDG diagram whose tag is missing, not
  plain UML, and the fallback attribution above is the one that finds it.
* The concept column is `Object_Type`, exactly as `Stereotype` is for an MDG. A
  plain UML Class is a row with an EMPTY stereotype and Object_Type `Class`; on
  EAExample 94% of plain-UML elements have no stereotype at all, so keying by
  Stereotype would measure nothing. An element that does carry a stereotype is still
  keyed by its Object_Type: `<<entity>>` on a Class is a Class.
* Diagram types are EA's `Diagram_Type` strings, verbatim: `Logical` (a class
  diagram), `Statechart`, `Collaboration`, `Use Case`.
* NOTHING IS EXCLUDED BY DEFAULT, not even the `Analysis` and `Custom` types. A
  caller may leave diagram types out (`exclude_base_types`, `--exclude-base-type`),
  and the result then says what it cost (`excluded_base_types`), but the tool holds
  no opinion about which types are "really" UML. The population is whatever the
  selection above admits, and MDG technologies sit on `Analysis` and `Custom`
  bases, so a binding that measures those types needs them present.
* Automatic content promotion is off: an untagged diagram that is mostly furniture
  is a documentation page, not evidence of UML content. `content_types` still
  applies.
* A diagram whose objects are MOSTLY FURNITURE is then dropped, whatever its type.
  See "DOCUMENTATION PAGES" below.

On EAExample the plain-UML tests admit 330 diagrams; the documentation-page filter
drops 65 of them, leaving 265 diagrams, 2,070 non-furniture elements and 15
`Diagram_Type` values, of which 1,930 elements carry no stereotype.

The 29 `Analysis` (4) and `Custom` (25) diagrams among the 330 were characterized
before this was decided, and the data does not support excluding them BY TYPE. The 4
Analysis diagrams are UML content: activities, events, actors and objects (two are
process models), none mostly furniture. `Custom` is mixed: 13 of its 25 are mostly
furniture and the other 12 hold Class, UseCase, Actor, Requirement and Package
elements - for example `Account` (2 Class, 1 Note) and `Design Patterns` (5 Class, 4
Text), which the filter keeps. Excluding the type would discard those 12 to reach
the 13.

Nor would it reach most of them: of the 65 mostly-furniture diagrams in the 330,
only 13 are `Custom` and 52 sit in other types - Logical 17, CompositeStructure 10,
Deployment 9, Package 8, Statechart 4, Collaboration 2, Component 1, Use Case 1.
Being a documentation page is a property of the diagram's composition, not of its
`Diagram_Type`, so the filter tests composition and names no type.

A figure recorded elsewhere as "330 diagrams, 13 types, 2,266 elements" is not one
selection, and neither figure is what the tool now reports. It is the 301 diagrams
that remain when `Analysis` and `Custom` are dropped from the 330, before the
documentation-page filter existed, which is also what yielded 13 types and 2,266
elements (2,138 unstereotyped). Passing `exclude_base_types={"Analysis", "Custom"}`
now gives 249 diagrams, 13 types and 1,969 elements (1,851 unstereotyped): the same
301 less the 52 pages in those types. It was a subset chosen by the author, and the
330 that was reported was the count before that choice.

DOCUMENTATION PAGES
-------------------
The plain-UML tests above ask "is this diagram made of plain, unstereotyped
things?". They do not ask "is it made of real things at all?". Furniture is left out
of the unstereotyped ratio, so a page of 8 `Text` objects and one `Package` is
admitted on that one `Package`: the ratio is computed over it alone, it carries no
stereotype, and the diagram passes. Its `Package` is then sized as if it were a
`Package` on a working diagram, and it contributes almost no gaps, so the pollution
lands on the size side without diluting on the gap side.

So `_select_base` drops a diagram when furniture is MORE than `BASE_FURNITURE_SHARE`
of its objects. Two things about that test:

* It is AGGREGATE, over `FURNITURE_TYPES` together, not one type at a time.
  `furniture_majority()` is per-type, because it is the counterpart of promotion
  rule 1 - it names the type that would have been promoted and was not. Per-type is
  the wrong test here and demonstrably lets pages through: `Venn Diagram` (3 Class, 5
  Text, 2 Note) and `Use Case Model` (2 Package, 3 Text, 3 Note) are 70% and 75%
  furniture and no single type is a majority of either. On EAExample the aggregate
  test drops 65 diagrams and the per-type test would drop 32 of the same 65, so the
  two reconcile as a superset and `documentation_pages_type_majority` states the 32.
* It NAMES NO DIAGRAM TYPE, and a type-level exclusion was tried and reversed on
  2026-09-29 for the reason in the paragraph above.

IT COSTS SOMETHING, AND THE REPORT SAYS SO. A majority-furniture diagram can still
hold real content: on EAExample the 65 dropped pages carry 336 non-furniture
elements, the most on any one of them being 24, on the `Deployment` diagram
`Government Agency`. A heavily annotated real diagram - boundaries and text labels
around genuine nodes - is dropped by the same test that drops a page of text. That
is a deliberate trade, not an oversight: `documentation_page_elements` and
`documentation_page_worst` carry the cost, `format_binding_yaml` prints it with the
name of every dropped diagram, and the lever for a diagram wrongly dropped is
`--content-type` on its annotation types, not a nudge to the threshold.

This filter MOVED THE MEASURED BASE CONVENTION, which is the point of it. Against
the 330-diagram population: `item_gap_x` median 60.5 to 56 (n 996 to 871) and
`item_gap_y` median 47 to 48.5 (n 961 to 874). The default size is 20x20 in both,
still `StateNode`'s. The MDG reproductions are untouched, because this path selects
only untagged diagrams: ArchiMate3 historical is still 61 and 68 pairs, medians 76
and 47.5, modes 78 and 38, and BPMN2.0 `Gateway` is still 42x42 in 61 of 61.

THE DEFAULT SIZE BELONGS TO SOMEBODY
------------------------------------
`default` is a pooled mode, so it is some concept's size whenever one concept
supplies most of the pool. A stereotype whose own modal size equals the default is
therefore NOT dropped from the output (it used to be, which is how a `ValueType`
disappeared and left its 90x70 looking like a convention across blocks): it is
listed with its own n and marked as agreeing with the default, and the default's
line says when one concept supplies more than half of the pool.
"""
from __future__ import annotations

import argparse
import difflib
import os
import re
import shutil
import sqlite3
import statistics
import sys
import tempfile
from collections import Counter, defaultdict
from contextlib import contextmanager
from dataclasses import dataclass, field, replace
from typing import Collection, Iterator, Optional, Sequence

MODEL_ENV_VAR = "EA_EXAMPLE_MODEL"

#: Below this many observations a figure is reported as low-n.
#:
#: DERIVED, 2026-09-30, and it was not before: it entered this module in its first
#: commit with the one line above it and no measurement. This is the derivation,
#: and it is a derivation of the SIZE gate only - see `MIN_SAMPLE_GAP` for why one
#: number cannot serve both.
#:
#: Population: every concept size population in EAExample that this tool would
#: actually EMIT a value for - n >= 40, a unique mode, and a mode covering at least
#: `DOMINANT_SHARE` - across every technology in the model plus the base notation.
#: 11 populations. Criterion: draw a random subsample of size k and ask whether its
#: modal size equals the full population's, 600 draws per population per k, and
#: take the smallest k at which that holds 95% of the time. Result: k = 8, 9, 9
#: over three seeds (20260930, 1, 987654321). 10 is the next round number above
#: every one of them, which is why the value does not change. Agreement at 10 is
#: 96.5%, at 5 it is 90.9% and at 3 it is 81.9%.
#:
#: VALID FOR a modal size drawn from a population whose mode is dominant. NOT a
#: statement about a tied or thinly spread population, and not about a gap median.
MIN_SAMPLE = 10

#: The observations a GAP MEDIAN needs before it is stable, which is nothing like
#: `MIN_SAMPLE`, and the reason this constant exists.
#:
#: Same method, same seeds, over the 19 gap populations of n >= 40 in EAExample.
#: Criterion: the subsample's median lands within 25% of the full population's,
#: 90% of the time. Result: k = 36, 36, 38 over the three seeds; this takes the
#: largest, because a floor that is understated is not a floor. Tighter criteria do
#: not converge in range at all: within 10% of the population median reaches only
#: 69% agreement at k = 40.
#:
#: AT `MIN_SAMPLE` = 10 A GAP MEDIAN IS WITHIN 10% OF THE NOTATION'S MEDIAN 39% OF
#: THE TIME, and within 25% of it 67% of the time. So the `low_n` gate, at 10, is
#: roughly the right floor for a size and much too low for a gap.
#:
#: IT IS A GUARD, NOT A SUPPRESSION. Raising the floor that comments a value out
#: would move every gap already authored against this tool, which is a sequenced
#: change and not one to make inside a measurement fix. So `GapStat.thin_median`
#: fires, `format_binding_yaml` says so on the line, and the value is still
#: emitted. Tightening the suppression is the follow-up this makes possible.
MIN_SAMPLE_GAP = 38

#: A stereotype whose modal size covers at least this share of >= MIN_SAMPLE
#: instances is treated as fixed by the notation, not chosen by authors.
FIXED_SHAPE_SHARE = 0.9

#: A per-stereotype size is emitted as a binding override only if its mode
#: covers at least this share; otherwise the YAML says there is no dominant size.
DOMINANT_SHARE = 0.5

#: Fraction of a technology's stereotyped elements that must share the measured
#: prefix for the prefix to be reported.
PREFIX_SHARE = 0.9

#: Fallback attribution: share of an untagged diagram's stereotyped elements
#: that must carry technology-exclusive stereotypes.
FALLBACK_SHARE = 0.5

#: EA object types that are annotation furniture, not elements of a notation.
FURNITURE_TYPES = frozenset({"Note", "Text", "Boundary"})

#: The technology id that asks for EA's base notation, UML, which no diagram is
#: ever tagged with. See "THE BASE NOTATION" in the module docstring.
BASE_NOTATION = "UML"

#: Base-notation selection: share of a diagram's non-furniture elements that must
#: carry no stereotype for the diagram to count as plain UML.
BASE_UNSTEREOTYPED_SHARE = 0.5

#: Base-notation selection: a diagram whose objects are MORE than this share
#: annotation furniture is a documentation page, not model content, and is dropped.
#: Aggregate over `FURNITURE_TYPES` TOGETHER, not one type at a time: four Text
#: plus four Note beside one Package is a documentation page and no single type is
#: a majority of it. Exactly half is not more than half. See "DOCUMENTATION PAGES"
#: in the module docstring.
BASE_FURNITURE_SHARE = 0.5

#: A gap statistic is `concentrated` when ONE diagram supplies MORE than this
#: share of the population.
MAX_DIAGRAM_SHARE = 0.5


class MeasureError(Exception):
    """The model or the request cannot be measured."""


class UnknownTechnology(MeasureError):
    """The technology id matches no diagram in the model."""


class UnknownDiagramType(MeasureError):
    """The diagram type matches no diagram of that technology."""


# --------------------------------------------------------------------------
# Geometry
# --------------------------------------------------------------------------

@dataclass(frozen=True)
class Rect:
    """A diagram rectangle in EA's stored convention: `top > bottom`.

    `left`/`right` are ordinary; `top` and `bottom` are y values on an axis
    that points UP, so a larger number is higher on the diagram.
    """
    left: int
    top: int
    right: int
    bottom: int

    @property
    def width(self) -> int:
        return self.right - self.left

    @property
    def height(self) -> int:
        return self.top - self.bottom

    def contains(self, other: "Rect") -> bool:
        """True when `other` lies inside this rectangle and is not identical."""
        return (self.left <= other.left and self.right >= other.right
                and self.top >= other.top and self.bottom <= other.bottom
                and self != other)


@dataclass(frozen=True)
class Item:
    """One element placed on one diagram."""
    object_id: int
    stereotype: str
    object_type: str
    rect: Rect
    #: True when a furniture-typed object has been promoted to content: on this
    #: diagram it is what the diagram is made of. See `promote_furniture`.
    content: bool = False

    @property
    def is_furniture(self) -> bool:
        return self.object_type in FURNITURE_TYPES and not self.content

    @property
    def concept(self) -> str:
        """The key this element is measured under.

        Its stereotype, or - for a furniture object promoted to content that has
        none - its Object_Type. Empty means the element has no concept and is
        never an endpoint.
        """
        return self.stereotype or (self.object_type if self.content else "")


def promote_furniture(
    items: list[Item],
    owned: Collection[str] = frozenset(),
    content_types: Collection[str] = frozenset(),
    auto: bool = True,
) -> tuple[list[Item], Counter]:
    """Promote furniture that is the diagram's content; see the module docstring.

    Returns the items (promoted ones with `content=True`) and a Counter of how
    many objects of each Object_Type were promoted. An object is promoted when
    its type is in `content_types`, or - if `auto` - when its type is the MAJORITY
    of the diagram's objects AND it carries a stereotype in `owned`.
    """
    counts = Counter(it.object_type for it in items)
    total = len(items)
    promoted: Counter = Counter()
    out = []
    for it in items:
        if it.object_type in FURNITURE_TYPES and not it.content:
            forced = it.object_type in content_types
            dominant = (auto and 2 * counts[it.object_type] > total
                        and bool(it.stereotype) and it.stereotype in owned)
            if forced or dominant:
                it = replace(it, content=True)
                promoted[it.object_type] += 1
        out.append(it)
    return out, promoted


def furniture_majority(items: list[Item]) -> frozenset[str]:
    """Furniture types (not promoted) that are the majority of a diagram's objects.

    ONE type at a time, because this is the counterpart of `promote_furniture`'s
    rule 1: it names the type that would have been promoted and was not. For "is
    this diagram mostly furniture at all", which is a different question and a
    strictly larger set, use `furniture_share`.
    """
    counts = Counter(it.object_type for it in items if it.is_furniture)
    return frozenset(t for t, n in counts.items() if 2 * n > len(items))


def furniture_share(items: list[Item]) -> float:
    """Share of a diagram's objects that is unpromoted annotation furniture.

    All of `FURNITURE_TYPES` counted together. A diagram with no objects has a
    share of 0: emptiness is not furniture.
    """
    if not items:
        return 0.0
    return sum(1 for it in items if it.is_furniture) / len(items)


def is_documentation_page(items: list[Item],
                          share: float = BASE_FURNITURE_SHARE) -> bool:
    """True when furniture is MORE than `share` of the diagram's objects.

    A property of the diagram's COMPOSITION. No diagram type is consulted, and
    none ever should be: documentation pages sit in Logical and Package diagrams
    as readily as in Custom ones, and the types that hold them also hold real
    content. See "DOCUMENTATION PAGES" in the module docstring.
    """
    return furniture_share(items) > share


def _horizontal_gap(a: Rect, b: Rect) -> tuple[int, int, int]:
    """(gap, overlap, smaller extent) for B to the right of A. Rows overlap."""
    overlap = min(a.top, b.top) - max(a.bottom, b.bottom)
    return b.left - a.right, overlap, min(a.height, b.height)


def _vertical_gap(a: Rect, b: Rect) -> tuple[int, int, int]:
    """(gap, overlap, smaller extent) for B below A. Columns overlap.

    A is above B when A's bottom is a LARGER number than B's top, so the gap is
    `A.bottom - B.top`.
    """
    overlap = min(a.right, b.right) - max(a.left, b.left)
    return a.bottom - b.top, overlap, min(a.width, b.width)


_AXES = {"h": _horizontal_gap, "v": _vertical_gap}


#: Adjacency rules. "strict" is the default; "historical" reproduces the
#: figures recorded in the shipped bindings. See the module docstring.
RULES = ("strict", "historical")


def nearest_neighbor_gaps(
    items: list[Item],
    axis: str,
    *,
    endpoint_stereotypes: Optional[Collection[str]] = None,
    min_overlap: float = 0.0,
    rule: str = "strict",
) -> tuple[list[int], int]:
    """Gaps between each element and its nearest neighbor on one diagram.

    Returns `(gaps, non_positive)`: one gap per element that has a qualifying
    neighbor, and the number of nearest neighbors dropped because they touched
    or overlapped. See the module docstring for the full adjacency rule.

    `axis` is "h" (right neighbor) or "v" (neighbor below). `rule` is "strict"
    (the default) or "historical" - the looser rule that reproduces the
    figures recorded in the shipped bindings; see `RULES`. Under "historical"
    touching pairs are skipped rather than counted, so `non_positive` is 0.
    """
    if rule not in RULES:
        raise ValueError(f"rule must be one of {RULES}, not {rule!r}")
    strict = rule == "strict"
    measure = _AXES[axis]
    rects = [it.rect for it in items]
    containers = [frozenset(j for j, other in enumerate(rects)
                            if j != i and other.contains(r))
                  for i, r in enumerate(rects)]
    is_container = [any(r.contains(o) for o in rects) for r in rects]

    def is_endpoint(i: int) -> bool:
        it = items[i]
        if is_container[i] or it.is_furniture or not it.concept:
            return False
        return endpoint_stereotypes is None or it.concept in endpoint_stereotypes

    gaps: list[int] = []
    non_positive = 0
    for i, a in enumerate(items):
        if not is_endpoint(i):
            continue
        best: Optional[int] = None
        best_is_endpoint = False
        for j, b in enumerate(items):
            if i == j or is_container[j]:
                continue
            if strict and containers[j] != containers[i]:
                continue
            if not strict and not is_endpoint(j):
                continue
            gap, overlap, smaller = measure(a.rect, b.rect)
            if overlap <= 0 or overlap < min_overlap * smaller:
                continue
            if gap < 0 or (gap == 0 and not strict):
                continue
            if best is None or gap < best:
                best, best_is_endpoint = gap, is_endpoint(j)
            elif gap == best:
                best_is_endpoint = best_is_endpoint or is_endpoint(j)
        if best is None or not best_is_endpoint:
            continue
        if best <= 0:
            non_positive += 1
            continue
        gaps.append(best)
    return gaps, non_positive


# --------------------------------------------------------------------------
# Statistics
# --------------------------------------------------------------------------

@dataclass(frozen=True)
class GapStat:
    """One gap measurement. `n` is always present; `low_n` says if it is thin.

    `diagrams` is how many diagrams supplied a gap; `top_diagram` (id and name)
    is the one that supplied the most, `top_count` how many, and `concentrated`
    is True when that is more than `MAX_DIAGRAM_SHARE` of `n`. A concentrated
    statistic keeps its median and mode - the pooled figure stays inspectable -
    but is not a statement about the notation. `diagrams` is 0 when the caller
    did not say where the gaps came from.

    `thin_median` is the guard on `MIN_SAMPLE`: True when `n` is below
    `MIN_SAMPLE_GAP`, the sample size at which a gap median was measured to become
    stable. `low_n` at `MIN_SAMPLE` is a floor derived for a modal SIZE and is far
    too low for a median, so a statistic can be `low_n=False` and `thin_median=True`
    - which is most of them, and is the point.
    """
    n: int
    median: Optional[float]
    mode: Optional[int]
    mode_count: int
    tied_modes: tuple[int, ...]
    low_n: bool
    diagrams: int = 0
    top_diagram: Optional[int] = None
    top_diagram_name: str = ""
    top_count: int = 0
    concentrated: bool = False
    thin_median: bool = False

    @property
    def top_share(self) -> float:
        return self.top_count / self.n if self.n else 0.0


@dataclass(frozen=True)
class SizeStat:
    """The modal size of a group of elements, with what it rests on.

    `mode` is None when no single size wins (a tie, including every size being
    unique). `mode_share` is `mode_count / n`.
    """
    n: int
    mode: Optional[tuple[int, int]]
    mode_count: int
    mode_share: float
    distinct: int
    median: tuple[float, float]
    low_n: bool


def _unique_mode(values: Collection) -> tuple[Optional[object], int, tuple]:
    counts = Counter(values)
    top = max(counts.values())
    winners = tuple(sorted(v for v, c in counts.items() if c == top))
    return (winners[0] if len(winners) == 1 else None), top, winners


def gap_stat(
    gaps: list[int],
    min_sample: int = MIN_SAMPLE,
    *,
    sources: Optional[Sequence[int]] = None,
    names: Optional[dict[int, str]] = None,
    max_diagram_share: float = MAX_DIAGRAM_SHARE,
    min_sample_gap: int = MIN_SAMPLE_GAP,
) -> GapStat:
    """Median, mode and provenance of pooled gaps.

    `sources[i]` is the id of the diagram that supplied `gaps[i]`; without it no
    concentration can be judged and the result says `diagrams=0`.
    """
    if not gaps:
        return GapStat(0, None, None, 0, (), True, thin_median=True)
    mode, count, winners = _unique_mode(gaps)
    diagrams, top, top_count, concentrated = 0, None, 0, False
    if sources is not None:
        if len(sources) != len(gaps):
            raise ValueError("sources must name a diagram for every gap")
        by_diagram = Counter(sources)
        diagrams = len(by_diagram)
        top, top_count = min(by_diagram.items(), key=lambda kv: (-kv[1], kv[0]))
        concentrated = top_count > max_diagram_share * len(gaps)
    return GapStat(len(gaps), statistics.median(gaps), mode, count,
                   winners if mode is None else (), len(gaps) < min_sample,
                   diagrams, top, (names or {}).get(top, "") if top is not None else "",
                   top_count, concentrated, len(gaps) < min_sample_gap)


def size_stat(sizes: list[tuple[int, int]], min_sample: int = MIN_SAMPLE) -> SizeStat:
    mode, count, _ = _unique_mode(sizes)
    n = len(sizes)
    return SizeStat(
        n=n, mode=mode, mode_count=count, mode_share=count / n,
        distinct=len(set(sizes)),
        median=(statistics.median(w for w, _ in sizes),
                statistics.median(h for _, h in sizes)),
        low_n=n < min_sample)


# --------------------------------------------------------------------------
# Reading the model
# --------------------------------------------------------------------------

def resolve_model_path(path: Optional[str] = None) -> Optional[str]:
    """`path`, else `$EA_EXAMPLE_MODEL`, else the model in EA's install folder.

    Returns None when none of them names an existing file.
    """
    candidates = [path, os.environ.get(MODEL_ENV_VAR)]
    program_files = os.environ.get("ProgramFiles")
    if program_files:
        candidates.append(os.path.join(program_files, "Sparx Systems", "EA",
                                       "EAExample.qea"))
    for candidate in candidates:
        if candidate and os.path.isfile(candidate):
            return candidate
    return None


@contextmanager
def open_model_copy(path: str) -> Iterator[sqlite3.Connection]:
    """Yield a read-only connection to a private COPY of the model.

    The original is only ever read by `shutil.copyfile`. Refuses when a journal
    or WAL sidecar exists, because that means the model is open somewhere.
    """
    for sidecar in ("-journal", "-wal"):
        if os.path.exists(path + sidecar):
            raise MeasureError(
                f"{os.path.basename(path)} has a {sidecar} file beside it, so "
                "it is open in another program. Close Enterprise Architect and "
                "try again; measuring a model mid-write would be a guess.")
    with tempfile.TemporaryDirectory(prefix="measure_binding_") as tmp:
        copy = os.path.join(tmp, "model.qea")
        shutil.copyfile(path, copy)
        conn = sqlite3.connect(f"file:{copy.replace(os.sep, '/')}?mode=ro", uri=True)
        try:
            yield conn
        finally:
            conn.close()


_MDG = re.compile(r"(?:^|;)MDGDgm=([^;]*)")


def parse_mdg(style_ex: Optional[str]) -> tuple[str, str]:
    """`(technology, diagram_type)` from `StyleEx`, or `("", "")` when empty.

    The value is `<Technology>::<DiagramType>`; the technology id may contain
    spaces, and the diagram type is compared verbatim.
    """
    match = _MDG.search(style_ex or "")
    if not match or not match.group(1):
        return "", ""
    technology, _, diagram_type = match.group(1).partition("::")
    return technology, diagram_type


def list_technologies(conn: sqlite3.Connection) -> dict[str, dict[str, int]]:
    """`{technology: {diagram_type: diagram_count}}` for tagged diagrams."""
    found: dict[str, Counter] = defaultdict(Counter)
    for (style_ex,) in conn.execute("SELECT StyleEx FROM t_diagram"):
        technology, diagram_type = parse_mdg(style_ex)
        if technology:
            found[technology][diagram_type] += 1
    return {t: dict(c) for t, c in sorted(found.items())}


@dataclass
class _Diagram:
    diagram_id: int
    base_type: str
    technology: str
    diagram_type: str
    items: list[Item] = field(default_factory=list)
    name: str = ""
    raw_type: str = ""
    #: Base notation only: non-furniture elements that carried no stereotype
    #: before the concept column was switched to Object_Type.
    unstereotyped: int = 0


def _load_diagrams(conn: sqlite3.Connection) -> dict[int, _Diagram]:
    diagrams: dict[int, _Diagram] = {}
    for did, base_type, style_ex, name in conn.execute(
            "SELECT Diagram_ID, Diagram_Type, StyleEx, Name FROM t_diagram"):
        technology, diagram_type = parse_mdg(style_ex)
        diagrams[did] = _Diagram(did, (base_type or "").lower(), technology,
                                 diagram_type, name=name or "",
                                 raw_type=base_type or "")
    rows = conn.execute(
        "SELECT o.Diagram_ID, t.Object_ID, t.Object_Type, t.Stereotype, "
        "       o.RectLeft, o.RectTop, o.RectRight, o.RectBottom "
        "FROM t_diagramobjects o JOIN t_object t ON t.Object_ID = o.Object_ID")
    for did, oid, otype, stereotype, left, top, right, bottom in rows:
        if did in diagrams:
            diagrams[did].items.append(Item(
                oid, stereotype or "", otype or "",
                Rect(left, top, right, bottom)))
    return diagrams


def _exclusive_stereotypes(diagrams: dict[int, _Diagram], technology: str) -> set[str]:
    """Stereotypes on `technology`'s tagged diagrams and on no other technology's."""
    own = {it.stereotype for d in diagrams.values() if d.technology == technology
           for it in d.items if it.stereotype}
    elsewhere = {it.stereotype for d in diagrams.values()
                 if d.technology and d.technology != technology
                 for it in d.items if it.stereotype}
    return own - elsewhere


def _attribute(diagrams: dict[int, _Diagram], technology: str
               ) -> tuple[list[_Diagram], list[_Diagram]]:
    """Split diagrams into `(tagged, fallback)` for one MDG technology."""
    tagged = [d for d in diagrams.values() if d.technology == technology]
    base_types = {d.base_type for d in tagged}
    exclusive = _exclusive_stereotypes(diagrams, technology)

    fallback = []
    for d in diagrams.values():
        if d.technology or d.base_type not in base_types:
            continue
        stereotyped = [it.stereotype for it in d.items if it.stereotype]
        if stereotyped and (sum(s in exclusive for s in stereotyped)
                            / len(stereotyped)) >= FALLBACK_SHARE:
            fallback.append(d)
    return tagged, fallback


def _select_base(
    diagrams: dict[int, _Diagram],
    exclude_base_types: Collection[str],
    content_types: Collection[str],
) -> tuple[list[_Diagram], dict[str, int], dict[int, Counter], list[_Diagram]]:
    """Diagrams of EA's base notation, keyed by Object_Type.

    Returns `(selected, excluded_by_type, promoted_by_diagram, documentation_pages)`.
    Each selected diagram is a copy whose items carry their Object_Type in the
    `stereotype` slot - the concept column for a base notation - with furniture
    left unkeyed so it stays out of sizes and endpoints.

    The order of the tests is the order of the reporting. The plain-UML tests come
    first, so `documentation_pages` holds diagrams that would otherwise have been
    selected and the removal is quotable against the pre-filter population. The
    caller's type exclusion comes next, so `excluded_by_type` counts every diagram
    the caller asked to leave out whether or not it is a documentation page. The
    composition filter is last.
    """
    excluded_types = {t.lower() for t in exclude_base_types}
    selected: list[_Diagram] = []
    excluded: Counter = Counter()
    promoted_by_diagram: dict[int, Counter] = {}
    pages: list[_Diagram] = []
    for d in diagrams.values():
        if d.technology:
            continue
        items, promoted = promote_furniture(d.items, content_types=content_types,
                                            auto=False)
        content = [it for it in items if not it.is_furniture]
        if not content:
            continue
        bare = sum(1 for it in content if not it.stereotype)
        if bare / len(content) < BASE_UNSTEREOTYPED_SHARE:
            continue
        if d.base_type in excluded_types:
            excluded[d.raw_type] += 1
            continue
        keyed = [replace(it, stereotype="") if it.is_furniture
                 else replace(it, stereotype=it.object_type) for it in items]
        kept = replace(d, items=keyed, unstereotyped=bare)
        if is_documentation_page(items):
            pages.append(kept)
            continue
        selected.append(kept)
        promoted_by_diagram[d.diagram_id] = promoted
    pages.sort(key=lambda d: (d.raw_type, d.name, d.diagram_id))
    return selected, dict(sorted(excluded.items())), promoted_by_diagram, pages


def list_base_notation(
    diagrams: dict[int, _Diagram],
    exclude_base_types: Optional[Collection[str]] = None,
) -> tuple[dict[str, int], dict[str, int], dict[str, int]]:
    """`(diagram_types, excluded, documentation_pages)` counts, by `Diagram_Type`.

    `documentation_pages` are the diagrams the composition filter dropped, so
    `--list` says what the selection cost as well as what it admitted.
    """
    selected, excluded, _, pages = _select_base(
        diagrams, exclude_base_types or (), frozenset())
    return (dict(sorted(Counter(d.raw_type for d in selected).items())), excluded,
            dict(sorted(Counter(d.raw_type for d in pages).items())))


# --------------------------------------------------------------------------
# The measurement
# --------------------------------------------------------------------------

@dataclass(frozen=True)
class Measurement:
    technology: str
    diagram_type: Optional[str]
    diagrams: int
    diagrams_by_mdg: int
    diagrams_by_fallback: int
    diagram_types: dict[str, int]
    stereotype_prefix: str
    prefix_share: tuple[int, int]
    sizes: dict[str, SizeStat]
    default_size: Optional[SizeStat]
    fixed_shape: tuple[str, ...]
    h_gap: GapStat
    v_gap: GapStat
    non_positive_h: int
    non_positive_v: int
    min_sample: int
    rule: str
    #: "Stereotype" for an MDG technology, "Object_Type" for the base notation.
    concept_column: str = "Stereotype"
    diagrams_by_base: int = 0
    #: Base notation only: diagrams that passed the selection but were left out
    #: because the caller excluded that type, by `Diagram_Type`.
    excluded_base_types: dict[str, int] = field(default_factory=dict)
    #: Base notation only: the diagrams the composition filter dropped as
    #: documentation pages, as `(Diagram_Type, name)`, sorted. Reported against
    #: `base_before_filter`, the population the plain-UML tests admitted.
    documentation_pages: tuple[tuple[str, str], ...] = ()
    base_before_filter: int = 0
    #: How many of `documentation_pages` also had ONE furniture type as a majority,
    #: which is what `furniture_majority_diagrams` used to count on them. The
    #: difference is the pages no per-type test can see. Reconciles the two.
    documentation_pages_type_majority: int = 0
    #: Non-furniture elements the dropped pages carried, and the largest single
    #: diagram's share of them as `(count, Diagram_Type, name)`. A majority-furniture
    #: diagram can still hold real content, and the filter takes it away: this is
    #: what the filter COST, stated rather than left for someone to notice.
    documentation_page_elements: int = 0
    documentation_page_worst: tuple[int, str, str] = (0, "", "")
    #: Base notation only: elements with an empty Stereotype, and all elements.
    unstereotyped: tuple[int, int] = (0, 0)
    #: Furniture objects promoted to content, by Object_Type, and on how many diagrams.
    content_promoted: dict[str, int] = field(default_factory=dict)
    content_promoted_diagrams: int = 0
    #: Diagrams in scope where a furniture type is the majority and was NOT
    #: promoted, and how many of those contributed no gap at all.
    furniture_majority_diagrams: int = 0
    furniture_majority_unmeasured: int = 0
    #: Concept -> how many of the pool's elements sit AT the default's modal size.
    #: Says whose size the default is; empty when the pool has a single concept.
    default_supply: dict[str, int] = field(default_factory=dict)
    #: The concepts gap endpoints were narrowed to; empty means every concept.
    endpoints: tuple[str, ...] = ()


def _measure_prefix(stereotypes: list[str]) -> tuple[str, tuple[int, int]]:
    """The `Xxx_` prefix most stereotypes share, if enough do."""
    if not stereotypes:
        return "", (0, 0)
    stems = Counter(s.split("_", 1)[0] + "_" for s in stereotypes if "_" in s)
    if stems:
        stem, count = stems.most_common(1)[0]
        if count / len(stereotypes) >= PREFIX_SHARE:
            return stem, (count, len(stereotypes))
    return "", (0, len(stereotypes))


def measure_binding(
    model_path: Optional[str],
    technology: str,
    diagram_type: Optional[str] = None,
    *,
    endpoint_stereotypes: Optional[Collection[str]] = None,
    min_overlap: float = 0.0,
    min_sample: int = MIN_SAMPLE,
    rule: str = "strict",
    content_types: Collection[str] = frozenset(),
    auto_content: bool = True,
    max_diagram_share: float = MAX_DIAGRAM_SHARE,
    exclude_base_types: Optional[Collection[str]] = None,
) -> Measurement:
    """Measure sizes and gaps for one technology (optionally one diagram type).

    `model_path` is copied before it is read; None resolves as
    `resolve_model_path` does. `rule` selects the adjacency rule (`RULES`).
    `technology` and `diagram_type` must match the `MDGDgm` values exactly -
    `list_technologies` shows them - except that `BASE_NOTATION` ("UML") asks for
    EA's base notation, whose diagram types are `Diagram_Type` strings. The
    remaining keywords are described in the module docstring: `content_types` and
    `auto_content` (furniture as content), `max_diagram_share` (concentration) and
    `exclude_base_types` (base notation only; default: exclude nothing).
    """
    path = resolve_model_path(model_path)
    if path is None:
        raise MeasureError(
            f"model not found: pass a path or set {MODEL_ENV_VAR}")
    with open_model_copy(path) as conn:
        known = list_technologies(conn)
        diagrams = _load_diagrams(conn)
    return measure_diagrams(
        diagrams, known, technology, diagram_type,
        endpoint_stereotypes=endpoint_stereotypes,
        min_overlap=min_overlap, min_sample=min_sample, rule=rule,
        content_types=content_types, auto_content=auto_content,
        max_diagram_share=max_diagram_share,
        exclude_base_types=exclude_base_types)


def measure_diagrams(
    diagrams: dict[int, "_Diagram"],
    known: dict[str, dict[str, int]],
    technology: str,
    diagram_type: Optional[str],
    *,
    endpoint_stereotypes: Optional[Collection[str]] = None,
    min_overlap: float = 0.0,
    min_sample: int = MIN_SAMPLE,
    rule: str = "strict",
    content_types: Collection[str] = frozenset(),
    auto_content: bool = True,
    max_diagram_share: float = MAX_DIAGRAM_SHARE,
    exclude_base_types: Optional[Collection[str]] = None,
) -> Measurement:
    if rule not in RULES:
        raise MeasureError(f"rule must be one of {RULES}, not {rule!r}")
    content_types = frozenset(content_types)
    base = technology == BASE_NOTATION and technology not in known
    excluded_base: dict[str, int] = {}
    documentation_pages: tuple[tuple[str, str], ...] = ()
    base_before_filter = 0
    pages_type_majority = 0
    pages_elements = 0
    pages_worst: tuple[int, str, str] = (0, "", "")
    tagged: list[_Diagram] = []
    fallback: list[_Diagram] = []
    if base:
        scope, excluded_base, promoted_by, pages = _select_base(
            diagrams, exclude_base_types or (), content_types)
        if diagram_type is not None:
            types = {d.raw_type for d in scope}
            if diagram_type not in types:
                raise UnknownDiagramType(
                    f"the base notation has no diagram type {diagram_type!r}. "
                    f"Known: {', '.join(sorted(types))}")
            scope = [d for d in scope if d.raw_type == diagram_type]
            pages = [d for d in pages if d.raw_type == diagram_type]
        diagram_types = Counter(d.raw_type for d in scope)
        documentation_pages = tuple((d.raw_type, d.name) for d in pages)
        base_before_filter = len(scope) + len(pages)
        pages_type_majority = sum(1 for d in pages if furniture_majority(d.items))
        lost = [(sum(1 for it in d.items if not it.is_furniture), d.raw_type, d.name)
                for d in pages]
        pages_elements = sum(n for n, _, _ in lost)
        pages_worst = max(lost, default=(0, "", ""))
    else:
        if technology not in known:
            close = difflib.get_close_matches(technology, list(known), n=3, cutoff=0.5)
            hint = f" Did you mean: {', '.join(close)}?" if close else ""
            raise UnknownTechnology(
                f"no diagram in this model is tagged {technology!r}.{hint} "
                f"Known ids: {', '.join(known)}. EA's base notation is never "
                f"tagged: ask for {BASE_NOTATION!r}.")
        if diagram_type is not None and diagram_type not in known[technology]:
            raise UnknownDiagramType(
                f"{technology} has no diagram type {diagram_type!r}. "
                f"Known: {', '.join(sorted(known[technology]))}")

        tagged, fallback = _attribute(diagrams, technology)
        if diagram_type is not None:
            tagged = [d for d in tagged if d.diagram_type == diagram_type]
            fallback = []  # an untagged diagram has no diagram type to match
        owned = _exclusive_stereotypes(diagrams, technology)
        scope, promoted_by = [], {}
        for d in tagged + fallback:
            items, promoted = promote_furniture(
                d.items, owned, content_types, auto_content)
            scope.append(replace(d, items=items))
            promoted_by[d.diagram_id] = promoted
        diagram_types = Counter(d.diagram_type for d in tagged)

    by_stereotype: dict[str, list[tuple[int, int]]] = defaultdict(list)
    for d in scope:
        for it in d.items:
            if it.concept:
                by_stereotype[it.concept].append((it.rect.width, it.rect.height))
    sizes = {s: size_stat(v, min_sample) for s, v in sorted(by_stereotype.items())}

    fixed = tuple(s for s, st in sizes.items()
                  if st.n >= min_sample and st.mode_share >= FIXED_SHAPE_SHARE)
    pooled = {s: v for s, v in by_stereotype.items() if s not in fixed}
    if not pooled:
        pooled = dict(by_stereotype)
    pool = [size for v in pooled.values() for size in v]
    default = size_stat(pool, min_sample) if pool else None
    default_supply: dict[str, int] = {}
    if default is not None and default.mode is not None and len(pooled) > 1:
        default_supply = {s: sum(1 for size in v if size == default.mode)
                          for s, v in sorted(pooled.items())}
        default_supply = {s: n for s, n in default_supply.items() if n}

    h: list[int] = []
    h_from: list[int] = []
    v: list[int] = []
    v_from: list[int] = []
    non_h = non_v = 0
    majority = majority_unmeasured = 0
    for d in scope:
        gh, nh = nearest_neighbor_gaps(d.items, "h",
                                       endpoint_stereotypes=endpoint_stereotypes,
                                       min_overlap=min_overlap, rule=rule)
        gv, nv = nearest_neighbor_gaps(d.items, "v",
                                       endpoint_stereotypes=endpoint_stereotypes,
                                       min_overlap=min_overlap, rule=rule)
        h += gh
        h_from += [d.diagram_id] * len(gh)
        v += gv
        v_from += [d.diagram_id] * len(gv)
        non_h += nh
        non_v += nv
        if furniture_majority(d.items):
            majority += 1
            majority_unmeasured += not gh and not gv

    names = {d.diagram_id: d.name for d in scope}
    promoted_total: Counter = Counter()
    promoted_diagrams = 0
    for d in scope:
        counter = promoted_by.get(d.diagram_id, Counter())
        promoted_total += counter
        promoted_diagrams += bool(counter)

    concepts = [it.concept for d in scope for it in d.items if it.concept]
    if base:
        prefix, share = "", (0, len(concepts))
        unstereotyped = (sum(d.unstereotyped for d in scope),
                         sum(1 for d in scope for it in d.items if not it.is_furniture))
    else:
        prefix, share = _measure_prefix(concepts)
        unstereotyped = (0, 0)
    return Measurement(
        technology=technology, diagram_type=diagram_type,
        diagrams=len(scope), diagrams_by_mdg=len(tagged),
        diagrams_by_fallback=len(fallback),
        diagram_types=dict(diagram_types),
        stereotype_prefix=prefix, prefix_share=share, sizes=sizes,
        default_size=default, fixed_shape=fixed,
        h_gap=gap_stat(h, min_sample, sources=h_from, names=names,
                       max_diagram_share=max_diagram_share),
        v_gap=gap_stat(v, min_sample, sources=v_from, names=names,
                       max_diagram_share=max_diagram_share),
        non_positive_h=non_h, non_positive_v=non_v, min_sample=min_sample,
        rule=rule,
        concept_column="Object_Type" if base else "Stereotype",
        diagrams_by_base=len(scope) if base else 0,
        excluded_base_types=excluded_base,
        documentation_pages=documentation_pages,
        base_before_filter=base_before_filter,
        documentation_pages_type_majority=pages_type_majority,
        documentation_page_elements=pages_elements,
        documentation_page_worst=pages_worst,
        unstereotyped=unstereotyped,
        content_promoted=dict(promoted_total),
        content_promoted_diagrams=promoted_diagrams,
        furniture_majority_diagrams=majority,
        furniture_majority_unmeasured=majority_unmeasured,
        default_supply=default_supply,
        endpoints=tuple(sorted(endpoint_stereotypes)) if endpoint_stereotypes else ())


# --------------------------------------------------------------------------
# Draft binding YAML
# --------------------------------------------------------------------------

def _size_text(mode: tuple[int, int]) -> str:
    return f"{{w: {mode[0]}, h: {mode[1]}}}"


def _size_evidence(st: SizeStat) -> str:
    kinds = f"{st.distinct} distinct size{'' if st.distinct == 1 else 's'}"
    if st.mode is None:
        return f"n={st.n}, {kinds}, no single mode"
    return (f"mode {st.mode[0]}x{st.mode[1]} in {st.mode_count} of n={st.n} "
            f"({st.mode_share:.0%}), {kinds}")


def _gap_evidence(g: GapStat) -> str:
    if g.n == 0:
        return "n=0"
    mode = (f"modal {g.mode} ({g.mode_count} of {g.n})" if g.mode is not None
            else f"no unique mode (tied: {', '.join(map(str, g.tied_modes))}, "
                 f"{g.mode_count} each of {g.n})")
    spread = (f", from {g.diagrams} diagram{'' if g.diagrams == 1 else 's'}, "
              f"largest {g.top_share:.0%}" if g.diagrams else "")
    return f"median {g.median:g}, {mode}, n={g.n}{spread}"


def _thin_median_text(g: GapStat) -> str:
    """The guard on `MIN_SAMPLE`, as it appears on the line it qualifies.

    `low_n` already covers a population under `MIN_SAMPLE`, which is the floor
    derived for a modal size. This is the one derived for a median, and it fires on
    a population that clears `low_n` and is still thin for the statistic being
    stated - which is the common case and the whole reason it is here.
    """
    if not g.thin_median or g.low_n or g.n == 0:
        return ""
    return (f"; THIN FOR A MEDIAN: n={g.n} is under MIN_SAMPLE_GAP="
            f"{MIN_SAMPLE_GAP}, the measured floor at which a gap median lands "
            "within 25% of the notation's median 90% of the time. Treat this value "
            "as provisional and re-measure on more diagrams before relying on it")


def _concentration_text(g: GapStat) -> str:
    who = f'"{g.top_diagram_name}" (id {g.top_diagram})' if g.top_diagram_name \
        else f"diagram id {g.top_diagram}"
    return (f"CONCENTRATED: {who} supplies {g.top_count} of {g.n} gaps "
            f"({g.top_share:.0%}), so the pooled median {g.median:g} measures that "
            f"diagram, not the notation; n={g.n} from {g.diagrams} "
            f"diagram{'' if g.diagrams == 1 else 's'}")


def _no_neighbors_text(m: Measurement) -> str:
    text = "no measurable neighbors (n=0)"
    if m.furniture_majority_diagrams:
        text += (f"; {m.furniture_majority_diagrams} diagram(s) in scope are mostly "
                 "Note/Text/Boundary objects and were measured without them - see "
                 "the furniture note above")
    return text


def _documentation_page_lines(m: Measurement) -> list[str]:
    """The composition filter's own report: how many pages it dropped, and which.

    A population change that is not written down is how a measurement stops being
    reproducible, so the names go in the output, not into a transcript.
    """
    if not m.base_before_filter:
        return []
    n = len(m.documentation_pages)
    if not n:
        return [f"# Documentation-page filter: none of the {m.base_before_filter} "
                f"selected diagrams is more than {BASE_FURNITURE_SHARE:.0%} furniture."]
    by_type: dict[str, list[str]] = defaultdict(list)
    for raw_type, name in m.documentation_pages:
        by_type[raw_type].append(name)
    lines = [
        f"# Documentation-page filter: {n} of {m.base_before_filter} selected "
        f"diagram(s) dropped - MORE than {BASE_FURNITURE_SHARE:.0%} of their objects "
        "is Note/Text/Boundary, so they are pages about the model, not model "
        "content. Composition only: no Diagram_Type is named by the filter, and "
        f"{len(by_type)} type(s) are affected.",
        f"#   {m.documentation_pages_type_majority} of the {n} have ONE furniture "
        "type as a majority (what furniture_majority() counts); the other "
        f"{n - m.documentation_pages_type_majority} are furniture only when the "
        "types are counted together.",
    ]
    cost, worst_type, worst_name = m.documentation_page_worst
    lines.append(
        f"#   WHAT THE FILTER COST: the dropped pages carried "
        f"{m.documentation_page_elements} non-furniture element(s), the most on one "
        f'diagram being {cost} on {worst_type} "{worst_name}". A majority-furniture '
        "diagram can still hold real content; that content is not measured. If a "
        "dropped diagram is real, its annotation types are the lever "
        "(--content-type), not the threshold.")
    for raw_type, names in sorted(by_type.items()):
        listed = ", ".join(f'"{name}"' for name in sorted(names))
        lines.append(f"#   dropped {raw_type} ({len(names)}): {listed}")
    return lines


def format_binding_yaml(m: Measurement) -> str:
    """A DRAFT binding block for `m`, every number annotated with its n.

    Draft means a person still decides: the numbers are the measurements,
    unrounded, and anything with fewer than `min_sample` observations, no
    unique mode, no dominant size or a concentrated gap population is emitted as
    a comment instead of a value.
    """
    base = m.concept_column == "Object_Type"
    scope = m.diagram_type if m.diagram_type is not None else "all diagram types"
    lines = [f"# DRAFT binding block for {m.technology} ({scope}), measured."]
    if base:
        lines.append(
            f"# {m.diagrams} diagrams of EA's base notation: no MDGDgm tag, at least "
            f"{BASE_UNSTEREOTYPED_SHARE:.0%} of non-furniture elements unstereotyped. "
            "The concept column is Object_Type, not Stereotype.")
        if m.excluded_base_types:
            left_out = ", ".join(f"{t} ({n})" for t, n in m.excluded_base_types.items())
            lines.append(f"# Left out at the caller's request: {left_out}.")
        lines += _documentation_page_lines(m)
        bare, total = m.unstereotyped
        if total:
            lines.append(f"# {bare} of {total} measured elements ({bare / total:.1%}) "
                         "carry an empty Stereotype.")
    else:
        lines.append(f"# {m.diagrams} diagrams: {m.diagrams_by_mdg} by MDGDgm tag, "
                     f"{m.diagrams_by_fallback} by Diagram_Type fallback.")
    lines += [
        f"# LOW-N means fewer than {m.min_sample} observations: shown commented "
        "out, not as a convention.",
    ]
    if m.content_promoted:
        promoted = ", ".join(f"{t} ({n})" for t, n in sorted(m.content_promoted.items()))
        lines.append(f"# Furniture treated as content on {m.content_promoted_diagrams} "
                     f"diagram(s): {promoted}.")
    if m.furniture_majority_diagrams:
        lines.append(
            f"# Furniture note: {m.furniture_majority_diagrams} diagram(s) in scope are "
            "mostly Note/Text/Boundary objects that were NOT treated as content "
            f"({m.furniture_majority_unmeasured} of them contributed no gap). If those "
            "objects are what the diagram is made of, pass --content-type.")
    if m.endpoints:
        lines.append("# Gap endpoints narrowed to: " + ", ".join(m.endpoints)
                     + ". Gaps, and whether one diagram dominates them, depend on this.")
    lines += ["", f"technology: {m.technology}"]
    if base:
        lines.append('stereotype_prefix: ""   # the base notation stores no prefix; '
                     f"{m.prefix_share[1]} elements keyed by Object_Type")
    elif m.stereotype_prefix:
        lines.append(f"stereotype_prefix: {m.stereotype_prefix}   "
                     f"# {m.prefix_share[0]} of {m.prefix_share[1]} stereotyped elements")
    else:
        lines.append(f'stereotype_prefix: ""   # none shared by '
                     f'{m.prefix_share[1]} stereotyped elements')
    key = m.diagram_type if m.diagram_type is not None else "<DiagramType>"
    if any(c in key for c in " <"):
        key = f'"{key}"'
    lines += ["", "diagram_types:", f"  {key}:", "    sizing:"]

    d = m.default_size
    if d is None or d.mode is None:
        lines.append("      # default: no unique modal size among "
                     "non-fixed-shape elements")
    elif d.low_n:
        lines.append(f"      # default: {_size_text(d.mode)}   "
                     f"# LOW-N ({_size_evidence(d)})")
    else:
        lines.append(f"      default: {_size_text(d.mode)}   "
                     f"# {_size_evidence(d)}")
    if d is not None and d.mode is not None and m.default_supply:
        top, top_n = max(m.default_supply.items(), key=lambda kv: (kv[1], kv[0]))
        if top_n > DOMINANT_SHARE * d.mode_count:
            lines.append(
                f"      # default {_size_text(d.mode)} is {top}'s size: {top} supplies "
                f"{top_n} of the {d.mode_count} elements at it ({top_n / d.mode_count:.0%}), "
                "so it is that concept's size before it is a convention across concepts")

    prefix = m.stereotype_prefix
    for stereotype, st in m.sizes.items():
        name = stereotype[len(prefix):] if prefix and stereotype.startswith(prefix) \
            else stereotype
        if st.mode is None or st.mode_share < DOMINANT_SHARE:
            lines.append(f"      # {name}: no dominant size ({_size_evidence(st)})")
        elif st.low_n:
            lines.append(f"      # {name}: {_size_text(st.mode)}   "
                         f"# LOW-N ({_size_evidence(st)})")
        else:
            agrees = ("; agrees with the default"
                      if d is not None and st.mode == d.mode
                      and stereotype not in m.fixed_shape else "")
            lines.append(f"      {name}: {_size_text(st.mode)}   "
                         f"# {_size_evidence(st)}{agrees}")

    lines.append("    spacing:")
    for label, gap in (("item_gap_x", m.h_gap), ("item_gap_y", m.v_gap)):
        if gap.n == 0 or gap.median is None:
            lines.append(f"      # {label}: {_no_neighbors_text(m)}")
        elif gap.concentrated:
            low = "LOW-N; " if gap.low_n else ""
            lines.append(f"      # {label}: not stated   # {low}{_concentration_text(gap)}")
        elif gap.low_n:
            lines.append(f"      # {label}: {round(gap.median)}   "
                         f"# LOW-N ({_gap_evidence(gap)})")
        else:
            lines.append(f"      {label}: {round(gap.median)}   "
                         f"# measured: {_gap_evidence(gap)}{_thin_median_text(gap)}")
    if m.rule == "strict":
        lines.append("      # rule: strict - nearest neighbor in the same container, "
                     "positive gap only; excluded as touching/overlapping: "
                     f"{m.non_positive_h} horizontal, {m.non_positive_v} vertical")
    else:
        lines.append("      # rule: HISTORICAL - nearest endpoint, containers and "
                     "intervening objects ignored. Reproduces the recorded "
                     "figures; not for authoring a binding.")
    return "\n".join(lines) + "\n"


# --------------------------------------------------------------------------
# Command line
# --------------------------------------------------------------------------

def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--model", help=f"path to the model (default: ${MODEL_ENV_VAR}, "
                                        "then the EA install folder)")
    parser.add_argument("--technology",
                        help=f"MDG technology id, e.g. BPMN2.0; {BASE_NOTATION} for "
                             "EA's base notation")
    parser.add_argument("--diagram-type", help='e.g. "Business Process"')
    parser.add_argument("--rule", choices=RULES, default="strict",
                        help="adjacency rule; 'historical' reproduces the figures "
                             "recorded in the shipped bindings")
    parser.add_argument("--content-type", action="append", default=[], metavar="TYPE",
                        help="treat this furniture Object_Type (Note, Text, Boundary) "
                             "as content on every diagram in scope; repeatable")
    parser.add_argument("--no-auto-content", action="store_true",
                        help="never promote furniture to content automatically")
    parser.add_argument("--exclude-base-type", action="append", default=None,
                        metavar="TYPE",
                        help="base notation only: leave out this Diagram_Type; "
                             "repeatable. Nothing is left out by default")
    parser.add_argument("--endpoint", action="append", default=None, metavar="CONCEPT",
                        help="only elements with this concept (stereotype, or Object_Type "
                             "for UML) are gap endpoints; repeatable. Gap statistics, "
                             "concentration included, depend on this choice")
    parser.add_argument("--list", action="store_true",
                        help="list technology ids and diagram types found")
    args = parser.parse_args(argv)


    path = resolve_model_path(args.model)
    if path is None:
        print(f"model not found: pass --model or set {MODEL_ENV_VAR}", file=sys.stderr)
        return 2
    try:
        if args.list:
            with open_model_copy(path) as conn:
                technologies = list_technologies(conn)
                diagrams = _load_diagrams(conn)
            for tech, types in technologies.items():
                print(f"{tech}: " + ", ".join(f"{t or '(none)'} ({n})"
                                              for t, n in sorted(types.items())))
            base_types, excluded, pages = list_base_notation(
                diagrams, args.exclude_base_type)
            print(f"{BASE_NOTATION} [base notation, no MDGDgm tag; keyed by Object_Type]: "
                  + ", ".join(f"{t} ({n})" for t, n in base_types.items())
                  + ("; left out at the caller's request: "
                     + ", ".join(f"{t} ({n})" for t, n in excluded.items())
                     if excluded else "")
                  + (f"; dropped as documentation pages (more than "
                     f"{BASE_FURNITURE_SHARE:.0%} furniture): "
                     + ", ".join(f"{t} ({n})" for t, n in pages.items())
                     if pages else ""))
            return 0
        if not args.technology:
            parser.error("--technology is required (or use --list)")
        print(format_binding_yaml(
            measure_binding(path, args.technology, args.diagram_type,
                            rule=args.rule, content_types=args.content_type,
                            auto_content=not args.no_auto_content,
                            exclude_base_types=args.exclude_base_type,
                            endpoint_stereotypes=args.endpoint)), end="")
    except MeasureError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

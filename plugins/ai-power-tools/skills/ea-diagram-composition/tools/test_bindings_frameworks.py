#!/usr/bin/env python3
"""Tests for the two FRAMEWORK bindings: TOGAF and the Zachman Framework.

Run from the repository root:

    python -m pytest ea-diagram-composition/tools/test_bindings_frameworks.py -q

Hermetic. The measured tests read a private COPY of the reference model as
SQLite, which is what `measure_binding.open_model_copy` does; nothing here
touches Sparx EA, a live repository or a COM object. When the model cannot be
found they skip rather than fail, so the suite still runs on a machine without
EA installed.

WHY THIS FILE IS SEPARATE FROM `test_bindings.py`
-------------------------------------------------
`test_bindings.py` owns the schema and the four earlier bindings, and its
generic sweeps - derived from `available_bindings()` - already cover these two
files: every shipped binding validates, declares a base the base notation binds,
leaves a channel free, composes a spec the engine accepts, and resolves what its
own document states. Nothing here repeats those. What is here is the part a
sweep cannot know: which numbers these two documents claim, and which slots they
deliberately leave empty.

A FRAMEWORK IS A STEREOTYPE LAYER OVER UML, SO A THIN BINDING IS THE RIGHT ONE
-----------------------------------------------------------------------------
Both bindings state one diagram type, one size and nothing else, and inherit
their spacing from the `Logical` entry in the base notation. That is not a
half-finished file: each is the whole of what the reference model can support.
So the tests below come in two halves of equal weight.

1. EVERY STATED FIGURE IS RE-DERIVED from the model through
   `measure_binding.measure_binding` and compared with what the YAML says.
   Nothing here restates a number: a test that hard-codes 114x116 beside a
   binding that hard-codes 114x116 is two copies of one claim agreeing with each
   other, which is how a fabricated figure survives.

2. EVERY OMITTED SLOT IS PROVED UNMEASURABLE. For each gap the bindings do not
   state, the corresponding `GapStat` must be `low_n` or `concentrated` - that
   is, refused by the rules rather than forgotten. And for each diagram type the
   bindings decline to key, the measurement must have no `default_size` the
   rules admit - so a type this file declines has no figure to state, rather
   than a figure somebody chose not to state. (A type with no supportable
   default CAN now be keyed, inheriting one from its substrate; what it must
   not do is state a figure the measurement does not support.) These are the
   tests that would catch a later author "filling in" a gap with a guess.

THE IDS ARE THE PART NOBODY WOULD GUESS
---------------------------------------
`TOGAF Diagrams` has a space in it. The Zachman family is SEVEN technology ids,
one per perspective plus the grid, and the bound one is `ZF Interface`. Tests
assert the guessable forms - `TOGAF`, `Zachman`, `ZF Framework` - are not in the
model at all, because a binding keyed on one of those resolves to nothing
silently, which is the worst failure the schema has.
"""
from __future__ import annotations

import math
import re
import statistics
import sys
from collections import Counter, defaultdict
from pathlib import Path

import pytest

_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

import measure_binding as mb  # noqa: E402
from bindings import (  # noqa: E402
    COMPOSED_GRAMMARS,
    PLACED_BY_ENGINE,
    available_bindings,
    find_binding,
    resolve_diagram,
)

_BINDINGS_DIR = _HERE.parent / "bindings"

# --- the ids, read from the model and pinned here ---------------------------
_TOGAF = "TOGAF Diagrams"
_TOGAF_TYPE = "TOGAF_Interface"
_TOGAF_FILE = "togaf-diagrams.yaml"
#: The second TOGAF id the model registers. Deliberately unbound: 3 stereotyped
#: elements, and its base diagram type `UMLDiagram` is not bound by UML either.
_TOGAF_DATA = "TOGAF_DataArchitecture"
#: Every diagram type under `TOGAF Diagrams`; one is bound, five are classified.
_TOGAF_UNBOUND_TYPES = ("TOGAF_ADM", "TOGAF_ACM", "TOGAF_EnterpriseContinuum",
                        "TOGAF_OrganizationStructure",
                        "IEEE1471_ConceptualFramework")

_ZF = "ZF Interface"
_ZF_TYPE = "ZF_Interface"
_ZF_FILE = "zf-interface.yaml"
#: The Zachman family: the grid's id plus one per framework row. Seven, not one.
_ZF_FAMILY = ("ZF", "ZF Builder", "ZF Designer", "ZF Interface", "ZF Owner",
              "ZF Planner", "ZF Subcontractor")
#: The six perspective ids, all deliberately unbound for want of a size.
_ZF_UNBOUND_IDS = tuple(i for i in _ZF_FAMILY if i != _ZF)

#: Ids a reader would guess from the notation's name. None is in the model.
_GUESSED_IDS = ("TOGAF", "TOGAF9", "TOGAF 9", "TOGAF_Diagrams", "Zachman",
                "Zachman Framework", "ZF Framework", "ZachmanFramework")

_MODEL = mb.resolve_model_path(None)
needs_model = pytest.mark.skipif(
    _MODEL is None,
    reason=(f"EAExample.qea not found - pass its location in "
            f"{mb.MODEL_ENV_VAR}; every figure in these two bindings is "
            f"measured from it"),
)

_TOGAF_TEXT = (_BINDINGS_DIR / _TOGAF_FILE).read_text(encoding="utf-8")
_ZF_TEXT = (_BINDINGS_DIR / _ZF_FILE).read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# Fixtures - the model is opened once per module, never per test
# ---------------------------------------------------------------------------
@pytest.fixture(scope="module")
def known():
    with mb.open_model_copy(_MODEL) as conn:
        return mb.list_technologies(conn)


@pytest.fixture(scope="module")
def togaf_measured():
    return mb.measure_binding(_MODEL, _TOGAF, _TOGAF_TYPE)


@pytest.fixture(scope="module")
def zf_measured():
    return mb.measure_binding(_MODEL, _ZF, _ZF_TYPE)


@pytest.fixture(scope="module")
def diagram_rows():
    """`(id, name, Diagram_Type, StyleEx)` for every diagram in the model."""
    with mb.open_model_copy(_MODEL) as conn:
        return conn.execute(
            "SELECT Diagram_ID, Name, Diagram_Type, StyleEx FROM t_diagram"
        ).fetchall()


def _placed(diagram_name: str) -> list[tuple[str, str, mb.Rect]]:
    """`(stereotype, name, rect)` for every object placed on one named diagram."""
    with mb.open_model_copy(_MODEL) as conn:
        rows = conn.execute(
            "SELECT t.Stereotype, t.Name, o.RectLeft, o.RectTop, o.RectRight, "
            "       o.RectBottom "
            "FROM t_diagramobjects o "
            "JOIN t_object t ON t.Object_ID = o.Object_ID "
            "JOIN t_diagram d ON d.Diagram_ID = o.Diagram_ID "
            "WHERE d.Name = ?", (diagram_name,)).fetchall()
    return [(r[0] or "", r[1] or "", mb.Rect(r[2], r[3], r[4], r[5]))
            for r in rows]


def _object_styles(diagram_name: str) -> list[str]:
    with mb.open_model_copy(_MODEL) as conn:
        return [r[0] or "" for r in conn.execute(
            "SELECT o.ObjectStyle FROM t_diagramobjects o "
            "JOIN t_diagram d ON d.Diagram_ID = o.Diagram_ID "
            "WHERE d.Name = ?", (diagram_name,))]


def _connector_modes(diagram_name: str) -> Counter:
    with mb.open_model_copy(_MODEL) as conn:
        rows = conn.execute(
            "SELECT l.Style FROM t_diagramlinks l "
            "JOIN t_diagram d ON d.Diagram_ID = l.DiagramID "
            "WHERE d.Name = ?", (diagram_name,)).fetchall()
    out: Counter = Counter()
    for (style,) in rows:
        match = re.search(r"Mode=(\d+)", style or "")
        out[match.group(1) if match else "?"] += 1
    return out


def _default_is_supportable(measured: mb.Measurement) -> bool:
    """Whether a measured `default` is a figure a binding may state.

    Four ways it is not, and only the first was obvious before these two
    bindings were measured:

    * no default at all;
    * `low_n` - fewer than ten observations;
    * NO UNIQUE MODE - `ZF Owner::OwnerLocation` clears the sample threshold with
      n=10 in 10 distinct sizes, so the tool emits nothing. A check that only read
      `low_n` would have called that statable.
    * THE MODE BELONGS TO ONE CONCEPT THAT IS ITSELF BELOW THRESHOLD.
      `ZF Owner::OwnerTime` is the case that needed finding: n=10, a 50% mode over
      3 sizes, `low_n` false - and the mode is 15x15, supplied entirely by five
      `EventNode` markers, against a median of 74x37. The tool's own guard against
      a fixed-shape concept outvoting the box a diagram is made of cannot fire,
      because it needs ten instances of that concept and there are five. So
      `default_supply` naming a single concept whose own statistic is `low_n` is
      the fourth refusal, and the tool reports exactly what is needed to see it.
    """
    stat = measured.default_size
    if stat is None or stat.low_n or stat.mode is None:
        return False
    if len(measured.default_supply) == 1:
        (concept, count), = measured.default_supply.items()
        own = measured.sizes.get(concept)
        if count == stat.mode_count and own is not None and own.low_n:
            return False
    return True


def _stated_size(text: str) -> tuple[int, int]:
    """The `default: {w: N, h: N}` a binding document states, read back out."""
    match = re.search(r"default:\s*\{w:\s*(\d+),\s*h:\s*(\d+)\}", text)
    assert match, "no sizing default found in the document"
    return int(match.group(1)), int(match.group(2))


# ---------------------------------------------------------------------------
# Both bindings load, are found by their declared ids, and are thin on purpose
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("technology,filename,diagram_type", [
    (_TOGAF, _TOGAF_FILE, _TOGAF_TYPE),
    (_ZF, _ZF_FILE, _ZF_TYPE),
])
def test_each_framework_binding_loads_and_is_found_by_its_declared_id(
        technology, filename, diagram_type):
    binding = find_binding(technology)
    assert binding is not None and binding.technology == technology
    assert available_bindings()[technology] == filename
    assert set(binding.diagram_types) == {diagram_type}
    assert binding.diagram_type_for_mdgdgm(
        f"{technology}::{diagram_type}") is not None


@pytest.mark.parametrize("technology", [_TOGAF, _ZF])
def test_each_framework_binding_declares_a_measured_empty_prefix(technology):
    """`""` is a statement here, not an absence.

    Both technologies store their stereotypes bare AT TECHNOLOGY SCOPE, so the
    empty prefix is the measured fact. The loader distinguishes a declared `""`
    from an absent key, and silently inheriting UML's would make it look like an
    omission.

    The regex is anchored at column zero, which is what keeps this test honest now
    that a diagram type may state a prefix of its own: TOGAF's `TOGAF_Interface`
    declares `ADM_` indented under it, and matching that here would let the
    technology-scope statement disappear unnoticed.
    """
    binding = find_binding(technology)
    assert binding.stereotype_prefix == ""
    document = (_BINDINGS_DIR / available_bindings()[technology]).read_text(
        encoding="utf-8")
    assert re.search(r'^stereotype_prefix:\s*""\s*$', document, re.M)


@pytest.mark.parametrize("technology", [_TOGAF, _ZF])
def test_each_framework_binding_is_built_on_uml_and_inherits_its_spacing(
        technology):
    """The whole point of a thin binding: what it does NOT say still resolves.

    Neither document states a gap - both populations come from one diagram - so
    both gaps must arrive from the `Logical` entry in the base notation rather
    than from the engine's own inoffensive default.
    """
    binding = find_binding(technology)
    assert binding.extends == "UML"
    bound = next(iter(binding.diagram_types.values()))
    assert bound.base == "Logical"
    assert bound.substrate == "UML::Logical"
    assert bound.inherits
    # Stated nothing, inherited both.
    assert bound.own_spacing == {}
    assert set(bound.inherited_spacing()) == {"item_gap_x", "item_gap_y"}
    logical = find_binding("UML").diagram_type("Logical")
    assert bound.spacing["item_gap_x"] == logical.spacing["item_gap_x"]
    assert bound.spacing["item_gap_y"] == logical.spacing["item_gap_y"]
    # The size is the child's, always: a framework tile is not a plain class.
    assert set(bound.own_sizing) == {"default"}
    assert bound.size_for() != logical.size_for()


@pytest.mark.parametrize("technology", [_TOGAF, _ZF])
def test_each_framework_binding_inherits_umls_presentation_profiles(technology):
    """A presentation scheme is not a claim about what EA declares, so it merges.

    Neither framework publishes one, and having UML's three is better than
    having none.
    """
    binding = find_binding(technology)
    assert set(binding.presentation_profiles) == {
        "detail", "review", "executive"}
    assert binding.viewpoints == {}, (
        "neither binding may invent a viewpoint catalog; see the notes in each")


# ---------------------------------------------------------------------------
# The grammars, and what each one promises
# ---------------------------------------------------------------------------
def test_the_togaf_adm_wheel_is_radial_and_is_both_composed_and_producible():
    bound = find_binding(_TOGAF).diagram_type(_TOGAF_TYPE)
    assert bound.grammar == "radial"
    assert bound.grammar_placement == PLACED_BY_ENGINE
    assert bound.geometry_is_composed and bound.grammar in COMPOSED_GRAMMARS
    assert bound.grammar_is_implemented, (
        "radial is built; a binding stating it must not be parked")
    assert bound.grammar_is_producible


def test_the_zachman_grid_is_matrix_and_is_both_composed_and_producible():
    """A two-axis lattice addressed by row and column, and the engine has one.

    This was `ea-semantic` when the file was written, on the argument that EA's
    own `MatrixActive` overlay places the grid. The vocabulary then gained
    `matrix` and the engine a composer for it, and the argument does not survive
    that: EA draws the grid rules and the headers, but all 36 cell rectangles are
    stored per element and a composer can write them. `ea-semantic` means
    coordinates are the WRONG output, not an output nobody had written.
    """
    bound = find_binding(_ZF).diagram_type(_ZF_TYPE)
    assert bound.grammar == "matrix"
    assert bound.grammar_placement == PLACED_BY_ENGINE
    assert bound.geometry_is_composed
    assert bound.grammar_is_implemented, (
        "matrix is built; if this fails the grammar was withdrawn and this "
        "diagram type needs reclassifying rather than leaving as-is")
    assert bound.grammar_is_producible
    # The reasoning for both refusals has to stay in the document.
    assert "ea-semantic" in _ZF_TEXT and "nested-grid" in _ZF_TEXT


def test_the_zachman_grid_is_not_parked_under_an_unbuilt_composed_grammar():
    """The landmine `computed-geometry` carries, checked rather than trusted.

    A 6x6 lattice reads like arithmetic nobody has written, which is what would
    once have put it there - and the day a treemap composer ships, a diagram type
    parked under it would start reporting itself composable.
    """
    bound = find_binding(_ZF).diagram_type(_ZF_TYPE)
    assert bound.grammar != "computed-geometry"
    assert "computed-geometry" in _ZF_TEXT, (
        "the document must say why it is NOT computed-geometry")


def test_the_zachman_cell_size_is_load_bearing_now_that_it_composes():
    """Under `matrix` the default IS the cell size, so the spec must carry it.

    While the diagram type was ea-semantic its sizes were descriptive. They are
    not any more, which is why the document had to say so where it states the
    figure.
    """
    bound = find_binding(_ZF).diagram_type(_ZF_TYPE)
    width, height = bound.size_for()
    spec = bound.spec()
    assert (spec["item_width"], spec["item_height"]) == (width, height)
    assert "LOAD-BEARING" in _ZF_TEXT.upper()


@pytest.mark.parametrize("technology,diagram_type", [
    (_TOGAF, _TOGAF_TYPE), (_ZF, _ZF_TYPE),
])
def test_neither_framework_draws_its_own_title(technology, diagram_type):
    """`frame-header` on both, and on both the measurement agrees: no diagram
    draws a title element. Declaring `drawn` would give the frame's name and a
    drawn caption, which is the worse of the two mistakes."""
    bound = find_binding(technology).diagram_type(diagram_type)
    assert bound.title == "frame-header"
    assert not bound.draws_its_own_title


# ---------------------------------------------------------------------------
# THE IDS. Nothing below is guessable, and a wrong guess resolves to nothing.
# ---------------------------------------------------------------------------
@needs_model
def test_the_bound_framework_ids_and_diagram_types_exist_in_the_mdg_data(known):
    assert _TOGAF in known and _TOGAF_TYPE in known[_TOGAF]
    assert _ZF in known and _ZF_TYPE in known[_ZF]
    # The space in `TOGAF Diagrams` is real, and so is the `_` in `ZF_Interface`.
    assert " " in _TOGAF and "_" in _ZF_TYPE


@needs_model
def test_the_guessable_framework_ids_are_not_in_the_model_at_all(known):
    for guessed in _GUESSED_IDS:
        assert guessed not in known, guessed


@needs_model
def test_togaf_registers_two_ids_and_only_the_larger_one_is_bound(known):
    togaf_ids = sorted(i for i in known if "TOGAF" in i)
    assert togaf_ids == [_TOGAF, _TOGAF_DATA]
    assert find_binding(_TOGAF) is not None
    assert find_binding(_TOGAF_DATA) is None
    assert _TOGAF_DATA in _TOGAF_TEXT, (
        "the unbound sibling id must be recorded, so its absence is not an "
        "oversight")


@needs_model
def test_the_zachman_family_is_seven_ids_and_only_the_grid_is_bound(known):
    assert sorted(i for i in known if i == "ZF" or i.startswith("ZF ")) == \
        sorted(_ZF_FAMILY)
    assert find_binding(_ZF) is not None
    for unbound in _ZF_UNBOUND_IDS:
        assert find_binding(unbound) is None, unbound
        assert unbound in _ZF_TEXT, (
            f"{unbound} must be recorded in the binding's notes")


@needs_model
def test_the_zachman_perspective_ids_are_the_frameworks_own_rows(known):
    """Why seven ids is a structural fact rather than a naming accident.

    Five perspective ids plus `ZF` cover the framework's rows, and the grid's
    36 cell names are the diagram names under them - so the family is one index
    and the diagrams it points at, not eight peer notations.
    """
    cell_names = {name.lower() for _, name, _ in _placed("Zachman Framework")}
    assert len(cell_names) >= 35
    with mb.open_model_copy(_MODEL) as conn:
        rows = conn.execute(
            "SELECT Name, StyleEx FROM t_diagram").fetchall()
    under_family = {
        (name or "").lower() for name, style_ex in rows
        if mb.parse_mdg(style_ex)[0] in _ZF_UNBOUND_IDS}
    # Not every cell has a diagram behind it in the example model, so this is a
    # floor rather than a match: what is asserted is that the two name sets
    # genuinely overlap and the grid is an index.
    assert len(cell_names & under_family) >= 6


# ---------------------------------------------------------------------------
# EVERY STATED FIGURE, RE-DERIVED. Nothing here restates a number.
# ---------------------------------------------------------------------------
@needs_model
def test_the_togaf_default_size_is_the_measured_mode_at_the_threshold(
        togaf_measured):
    stat = togaf_measured.default_size
    assert stat is not None and not stat.low_n
    assert stat.n == mb.MIN_SAMPLE, (
        "the thinnest sample the rules admit; if n has grown, re-read the file")
    assert stat.mode == _stated_size(_TOGAF_TEXT)
    # Mode and median agree, which is what makes a 4-size population statable.
    assert stat.median == (float(stat.mode[0]), float(stat.mode[1]))
    assert stat.distinct == 4 and stat.mode_count == 6


@needs_model
def test_the_zachman_default_size_is_the_measured_mode_and_is_weak(zf_measured):
    stat = zf_measured.default_size
    assert stat is not None and not stat.low_n
    assert stat.n == 36
    assert stat.mode == _stated_size(_ZF_TEXT)
    # Stated rather than inherited, and weak on its own share: the document
    # says so because a reader would otherwise take an 11% mode over 21 sizes
    # for a convention. Inheriting was not an option here for a reason worth
    # keeping - this IS the notation's own measurement, thin as it is, and
    # falling back to UML's would have reported a figure measured on a
    # different notation as if it described this one.
    assert stat.mode_share < 0.2 and stat.distinct > 15
    assert stat.median != (float(stat.mode[0]), float(stat.mode[1]))
    assert "WEAKEST" in _ZF_TEXT.upper()


@needs_model
def test_the_togaf_hub_is_the_one_element_bigger_than_the_stated_default():
    """The claim the `sizing` comment makes about the odd size out.

    One of the four measured sizes is the Requirements Management hub, and it is
    the largest element on the diagram. A per-concept entry for it would be n=1
    and is refused, so the fact lives in a comment and is pinned here.
    """
    placed = _placed("TOGAF-ADM")
    assert len(placed) == 10
    widest = max(placed, key=lambda p: p[2].width * p[2].height)
    assert widest[0] == "ADM_RequirementsManagement"
    assert (widest[2].width, widest[2].height) == (146, 147)
    stated = _stated_size(_TOGAF_TEXT)
    assert widest[2].width > stated[0] and widest[2].height > stated[1]


# ---------------------------------------------------------------------------
# EVERY OMITTED SLOT, PROVED UNMEASURABLE. The other half of the job.
# ---------------------------------------------------------------------------
@needs_model
@pytest.mark.parametrize("technology,diagram_type", [
    (_TOGAF, _TOGAF_TYPE), (_ZF, _ZF_TYPE),
])
def test_neither_binding_states_a_gap_and_both_populations_are_refused(
        technology, diagram_type):
    """The omission is a verdict, not a gap in the work.

    Each population comes entirely from the single diagram of its type in the
    model, so one diagram would be speaking for the notation. A later author who
    "fills these in" from the same model fails here.
    """
    measured = mb.measure_binding(_MODEL, technology, diagram_type)
    bound = find_binding(technology).diagram_type(diagram_type)
    assert bound.own_spacing == {}
    for stat in (measured.h_gap, measured.v_gap):
        assert stat.n > 0, "the tool did find pairs; that is why this is a verdict"
        assert stat.diagrams == 1 and stat.top_count == stat.n
        assert stat.concentrated, "refused by the one-diagram rule"


@needs_model
def test_the_zachman_gaps_are_a_table_of_abutting_cells_not_sibling_spacing(
        zf_measured):
    """A second, independent reason the gaps are not stated.

    7 units between cells is a grid closing up, not a gap an engine would leave
    between two things it placed side by side. The UAF framework grid measures 5
    and says the same.
    """
    assert zf_measured.h_gap.median < 20 and zf_measured.v_gap.median < 20


@needs_model
def test_the_togaf_ring_radius_is_measured_and_deliberately_not_stated():
    """The most surprising omission in either file, pinned so it stays honest.

    `radius` is a real layout spec key and the ADM ring has a real radius. Eight
    spokes is below the threshold and all eight come from one diagram, so it is
    refused twice over - and the engine's own default happening to land in the
    measured range is a coincidence rather than a licence.
    """
    bound = find_binding(_TOGAF).diagram_type(_TOGAF_TYPE)
    for key in ("radius", "start_angle", "sweep"):
        assert key not in bound.spacing
        assert key not in bound.own_spacing
    radii = _adm_ring_radii()
    assert len(radii) < mb.MIN_SAMPLE
    assert "radius" in _TOGAF_TEXT, "the document must say why it is absent"


@needs_model
@pytest.mark.parametrize("diagram_type", _TOGAF_UNBOUND_TYPES)
def test_every_unbound_togaf_diagram_type_has_no_supportable_default(
        diagram_type):
    """No default the rules admit means no key stated here.

    SUPERSEDED IN PART: `sizing.default` is no longer mandatory in the
    DOCUMENT. It is now checked on the RESOLVED diagram type, in
    `Binding.__init__` after the merge, so a type that omits it inherits
    the substrate's and a type with nothing above it is still refused.
    What survives here is the second half and it is the half that
    mattered: the figure has to come from somewhere, and inheriting is
    traceable where copying is not.

    So these five types are now AUTHORABLE from ids, diagram types and bases
    alone, for whichever of them names a base `uml.yaml` declares. What this
    test still measures is unchanged and still worth measuring: whether the
    model supplies a figure the rules admit.

    The original framing:

    This is the whole reason five of six TOGAF diagram types are classified in
    `notes` instead of bound. If the reference model grows and one of these
    starts producing a default the rules admit, this test fails and asks for the
    binding to be extended - which is the intended failure.
    """
    measured = mb.measure_binding(_MODEL, _TOGAF, diagram_type)
    assert not _default_is_supportable(measured),         f"{diagram_type}: {measured.default_size}"
    assert diagram_type in _TOGAF_TEXT, (
        f"{diagram_type} must be classified in the notes")
    assert diagram_type not in find_binding(_TOGAF).diagram_types


@needs_model
def test_the_togaf_enterprise_continuum_is_one_observation_short():
    """The nearest miss, and the one to revisit first.

    Unanimous at 8 of 8, refused on n alone - the same case the UML binding
    refuses for a 45x90 actor at n=9. Pinned because "unanimous" is exactly the
    word that tempts an author to state it anyway.
    """
    stat = mb.measure_binding(
        _MODEL, _TOGAF, "TOGAF_EnterpriseContinuum").default_size
    assert stat is not None and stat.low_n
    assert stat.n == mb.MIN_SAMPLE - 2 and stat.mode_count == stat.n
    assert stat.mode == (110, 128)
    assert "observation short" in _TOGAF_TEXT


@needs_model
@pytest.mark.parametrize("technology", _ZF_UNBOUND_IDS)
def test_no_unbound_zachman_perspective_id_has_a_supportable_default(
        technology):
    """Why six of the seven Zachman ids are notes rather than bindings.

    `ZF Owner` is the awkward one: it DOES produce an uncommented pooled default,
    and it is 15x15 at 12% over 28 distinct sizes - a marker-sized figure that
    would be wrong on every diagram it was applied to. So the test is not "the
    tool refuses it" but "no diagram type of this id has a figure worth keying",
    which is checked per diagram type.
    """
    pooled = mb.measure_binding(_MODEL, technology)
    for diagram_type in pooled.diagram_types:
        measured = mb.measure_binding(_MODEL, technology, diagram_type)
        assert not _default_is_supportable(measured),             f"{technology}::{diagram_type}: {measured.default_size}"


@needs_model
def test_the_togaf_adm_prefix_is_stated_at_the_scope_it_was_measured_at(
        togaf_measured):
    """A PREFIX ON ONE DIAGRAM TYPE INSIDE A TECHNOLOGY THAT HAS NONE.

    Pinned in both directions, because both are true and each would be a lie at
    the other's scope. Measured at diagram-type scope the prefix is `ADM_` on 10
    of 10 elements; measured at technology scope there is none, across 36. So
    `TOGAF_Interface` states `ADM_` and the technology states `""`, and the round
    trip is asserted at each - including that the technology-scope answer for an
    ADM phase is the UNPREFIXED name, which is what makes the two statements
    distinguishable rather than interchangeable.
    """
    assert togaf_measured.stereotype_prefix == "ADM_"
    assert togaf_measured.prefix_share == (10, 10)
    technology_wide = mb.measure_binding(_MODEL, _TOGAF)
    assert technology_wide.stereotype_prefix == ""
    assert technology_wide.prefix_share == (0, 36)

    binding = find_binding(_TOGAF)
    assert binding.stereotype_prefix == ""
    adm = binding.diagram_type(_TOGAF_TYPE)
    assert adm.own_stereotype_prefix == "ADM_"
    assert not adm.stereotype_prefix_is_inherited
    assert adm.stereotype_prefix_provenance == f"{_TOGAF}::{_TOGAF_TYPE}"

    # Every stereotype the model stores on that diagram, round tripped.
    for stereotype in sorted(togaf_measured.sizes):
        assert stereotype.startswith("ADM_"), stereotype
        concept = adm.concept_for(stereotype)
        assert concept != stereotype
        assert adm.stereotype_for(concept) == stereotype
        assert binding.stereotype_for(concept, _TOGAF_TYPE) == stereotype
        # The technology's own bare stereotypes still resolve to themselves, and
        # an ADM concept asked at technology scope does NOT acquire the prefix.
        assert binding.stereotype_for(concept) == concept
    for bare in ("Mission", "Principle", "OrganizationUnit"):
        assert binding.stereotype_for(bare) == bare
        assert binding.concept_for(bare) == bare

    # No per-concept `sizing` key depends on the prefix here - the ADM hub's own
    # size is n=1 and refused - so the prefix earns its place through lookup
    # rather than through this file's keys.
    assert set(adm.own_sizing) == {"default"}


@needs_model
def test_the_one_unbound_zachman_default_that_clears_the_rules_is_a_marker_size(
        ):
    """The exception that has to be named, because the rules alone would key it.

    `ZF Owner::OwnerTime` produces a default of 15x15 at n=10 with a 50% mode and
    `low_n` false. It is the size of five `EventNode` pseudonodes, against a
    median of 74x37 and a `BusinessEvent` at 133x59 that is what the diagram is
    actually made of. The tool's fixed-shape guard - which exists precisely to stop
    events outvoting activities - needs ten instances of the concept and has five,
    so it does not fire and the marker wins the pool. Refusing this is a judgment,
    it is the same judgment the UML binding makes for an activity diagram, and it
    is written down here so it cannot be quietly reversed.
    """
    measured = mb.measure_binding(_MODEL, "ZF Owner", "OwnerTime")
    stat = measured.default_size
    assert stat is not None and not stat.low_n and stat.mode == (15, 15)
    assert measured.fixed_shape == (), (
        "the guard cannot fire - that is the whole problem")
    assert measured.default_supply == {"EventNode": 5}
    assert measured.sizes["EventNode"].low_n
    assert measured.sizes["BusinessEvent"].mode == (133, 59)
    assert stat.median == (74.0, 37.0)
    assert "OwnerTime" in _ZF_TEXT, (
        "the binding must record this exception rather than the sweeping claim")


@needs_model
def test_the_bound_framework_defaults_are_supportable_by_the_same_criterion(
        togaf_measured, zf_measured):
    """The criterion must admit what the bindings DO state, or it proves nothing."""
    assert _default_is_supportable(togaf_measured)
    assert _default_is_supportable(zf_measured)


#: The three `ZF Planner` diagram types the unbound Zachman corpus rows are
#: pictures of, with the EAExample diagram each row corresponds to.
_ZF_CORPUS_TYPES = {
    "PlannerData": "Data - List of Things",
    "PlannerLocation": "Business Location",
    "PlannerPeople": "Organization chart",
}


@needs_model
@pytest.mark.parametrize("diagram_type,diagram_name",
                         sorted(_ZF_CORPUS_TYPES.items()))
def test_the_perspective_types_the_corpus_asks_for_are_blocked_on_sizing_alone(
        diagram_type, diagram_name):
    """Which diagram types a Zachman binding CANNOT reach, and exactly why.

    Three of the four unbound Zachman corpus rows are `ZF Planner` diagram types
    rather than the grid, so this is the test that says what stops each one. In
    every case it is `sizing.default`, and the reason has CHANGED under this
    test: `_validate_sizing` used to check it before `_merge` ran, so a diagram
    type could not inherit a default from its base at all. It is now checked on
    the resolved type after the merge, so it can. None of the three has a figure
    the rules admit, which is what this test measures and what has not changed -
    but "no figure" no longer means "no binding".

    **So `ZF Planner` is now authorable**, from its ids, diagram types and the
    bases recorded below, inheriting its default. The grammar was never the
    problem and neither was the base; the size was, and the size can now come
    from the substrate. One caveat stands and is recorded below rather than
    overruled: `PlannerData`'s own reference diagram carries no stereotyped
    element at all, so there is an independent argument that it is the base
    notation's to govern.

    `PlannerData` is the sharpest case: the diagram the corpus row is a picture of
    carries EIGHT objects and NOT ONE of them is stereotyped, so it contributes
    nothing at all to an MDG measurement. Measured as data it is a plain UML
    `Custom` canvas, which the base notation already governs.
    """
    measured = mb.measure_binding(_MODEL, "ZF Planner", diagram_type)
    assert not _default_is_supportable(measured),         f"{diagram_type} is now statable - extend the binding: {measured.default_size}"
    # The diagram exists, is tagged with this type, and is the corpus row's.
    with mb.open_model_copy(_MODEL) as conn:
        rows = conn.execute(
            "SELECT Diagram_ID, Diagram_Type FROM t_diagram WHERE Name = ? "
            "AND StyleEx LIKE ?", (diagram_name, "%ZF Planner::" + diagram_type
                                   + "%")).fetchall()
    assert len(rows) == 1, diagram_name
    # And the base it would declare is readable, which is the cheap half.
    assert rows[0][1] in {"Custom", "Use Case"}
    assert diagram_type in _ZF_TEXT, (
        f"{diagram_type} and what blocks it must be recorded in the binding")


@needs_model
def test_the_list_of_things_diagram_carries_no_stereotyped_element_at_all():
    """The reason `PlannerData` cannot be reached even with four diagrams.

    An MDG measurement keys on `t_object.Stereotype`, and this diagram has none:
    three plain Packages and five notes on a `Custom` base. A framework row whose
    reference diagram is drawn in plain UML is the base notation's to govern.
    """
    placed = _placed("Data - List of Things")
    assert len(placed) == 8
    assert all(stereotype == "" for stereotype, _, _ in placed)


@needs_model
def test_a_zachman_perspective_binding_would_need_its_own_file_per_id():
    """Why covering those rows is several bindings rather than one.

    A binding binds exactly one technology id, and the three corpus rows sit under
    `ZF Planner` while the grid sits under `ZF Interface`. So the question "bind
    the perspectives the corpus uses" is a question about several files, and each
    of them needs its own measured `sizing.default` first.
    """
    grid = find_binding(_ZF)
    assert grid.technology == _ZF
    for diagram_type in _ZF_CORPUS_TYPES:
        assert diagram_type not in grid.diagram_types, (
            f"{diagram_type} belongs to ZF Planner; a binding binds one id")
    assert find_binding("ZF Planner") is None


# ---------------------------------------------------------------------------
# THE GEOMETRY EACH GRAMMAR RESTS ON, re-derived from the model
# ---------------------------------------------------------------------------
def _adm_ring_radii() -> list[float]:
    """Center-to-center radii of the ADM spokes, hub and outer element excluded."""
    centers = {
        stereotype: ((rect.left + rect.right) / 2,
                     (rect.top + rect.bottom) / 2)
        for stereotype, _, rect in _placed("TOGAF-ADM")}
    hub = centers["ADM_RequirementsManagement"]
    radii = [math.hypot(x - hub[0], y - hub[1])
             for key, (x, y) in centers.items()
             if key != "ADM_RequirementsManagement"]
    return [r for r in radii if r < 300]


@needs_model
def test_the_adm_geometry_is_a_hub_and_eight_spokes_on_one_ring():
    """`radial` is not recognition, it is this measurement.

    Eight spokes at 45-degree intervals on a ring of one radius around the
    largest element. If this shape is not in the data, the grammar is wrong.
    """
    centers = {
        stereotype: ((rect.left + rect.right) / 2,
                     (rect.top + rect.bottom) / 2)
        for stereotype, _, rect in _placed("TOGAF-ADM")}
    assert len(centers) == 10
    hub = centers.pop("ADM_RequirementsManagement")

    polar = {}
    for key, (x, y) in centers.items():
        polar[key] = (math.hypot(x - hub[0], y - hub[1]),
                      math.degrees(math.atan2(y - hub[1], x - hub[0])))

    ring = {k: v for k, v in polar.items() if v[0] < 300}
    outer = {k: v for k, v in polar.items() if v[0] >= 300}
    assert len(ring) == 8 and len(outer) == 1
    # One ring: the spread is a few units on a radius of a little over 200.
    radii = [r for r, _ in ring.values()]
    assert max(radii) - min(radii) < 20
    assert 200 < statistics.median(radii) < 230
    # Eight spokes, evenly spaced. 360/8 = 45, and no step is far off it.
    angles = sorted(a for _, a in ring.values())
    steps = [b - a for a, b in zip(angles, angles[1:])]
    steps.append(360 - (angles[-1] - angles[0]))
    assert all(abs(step - 45) < 5 for step in steps), steps
    # The element outside the ring is the preliminary phase, on the same bearing
    # as Architecture Vision - an outer ring of one.
    (outer_key, (outer_r, outer_a)), = outer.items()
    assert outer_key == "ADM_Preliminary"
    assert abs(outer_a - polar["ADM_ArchitectureVision"][1]) < 1
    assert outer_r > max(radii)


@needs_model
def test_the_zachman_grid_is_six_columns_by_six_rows_with_no_containment():
    """`ea-semantic` rests on this, and so does the refusal of both grids.

    A cell's width belongs to its column and its height to its row, which is
    what makes it a table. `layered-bands` needs one uniform item size within a
    band and cannot produce this; `nested-grid` sizes a container by its contents
    and there are no containers here anyway.

    It is also the measured disagreement with the grammar that WAS chosen:
    `matrix` draws every cell at one size, and this diagram holds six widths and
    six heights. Both are lattices a reader can count along, and the notes say so
    rather than implying a composed matrix reproduces this geometry exactly.
    """
    placed = _placed("Zachman Framework")
    assert len(placed) == 36
    assert {stereotype for stereotype, _, _ in placed} == {"ZFCell"}
    # No header element exists, which is why no header thickness is stated.
    assert all(rect.width < 200 for _, _, rect in placed)

    columns: dict[int, list[int]] = defaultdict(list)
    rows: dict[int, list[int]] = defaultdict(list)
    for _, _, rect in placed:
        columns[rect.left].append(rect.width)
        # Rows are within a unit of each other rather than exactly equal.
        rows[round(rect.top / 10)].append(rect.height)

    assert len(columns) == 6 and len(rows) == 6
    for left, widths in columns.items():
        assert len(widths) == 6 and len(set(widths)) == 1, left
    for row, heights in rows.items():
        assert len(heights) == 6 and max(heights) - min(heights) <= 1, row
    # Six widths and six heights, and they genuinely differ - which is why 36
    # cells come in more than a handful of sizes.
    assert len({w[0] for w in columns.values()}) > 1
    assert len({h[0] for h in rows.values()}) > 1

    # Not one cell is inside another: `nested-grid` has nothing to work with.
    rects = [rect for _, _, rect in placed]
    assert not any(a.contains(b) for a in rects for b in rects)


@needs_model
def test_eas_own_matrix_is_switched_on_for_the_zachman_grid_and_nowhere_else(
        diagram_rows):
    """What EA supplies here, and what it does not.

    `MatrixActive=1` draws the grid rules and the row and column headers, none of
    which exists as an element - and it is set on this one diagram out of every
    diagram in the model. It was read as EA placing the diagram and is not: the
    cell rectangles are in `t_diagramobjects`. It IS the reason a composed matrix
    emits header elements this diagram does not have, which the notes record.
    """
    active = [(did, name) for did, name, _, style_ex in diagram_rows
              if "MatrixActive=1" in (style_ex or "")]
    assert len(active) == 1
    assert active[0][1] == "Zachman Framework"
    assert "MatrixActive=1" in _ZF_TEXT


@needs_model
def test_the_zachman_diagram_type_is_stored_in_lower_case_and_is_unique(
        diagram_rows):
    """The quirk the `base` value is declared against.

    `base: Logical` is capitalized so the substrate resolves; the model stores
    `logical` for this one diagram, and for no other of the 1,129. Anyone
    tempted to "correct" the binding to the stored spelling should read the
    comment above `extends` first.
    """
    lowercase = [(name, style_ex) for _, name, base, style_ex in diagram_rows
                 if base == "logical"]
    assert len(lowercase) == 1
    assert lowercase[0][0] == "Zachman Framework"
    assert mb.parse_mdg(lowercase[0][1]) == (_ZF, _ZF_TYPE)
    # The capitalized spelling is what the UML binding holds, and it is common.
    capitalized = sum(1 for _, _, base, _ in diagram_rows if base == "Logical")
    assert capitalized > 100
    assert find_binding(_ZF).diagram_type(_ZF_TYPE).base == "Logical"
    assert "lower case" in _ZF_TEXT


# ---------------------------------------------------------------------------
# CHANNELS - each claim is a measurement, so each is checked against the model
# ---------------------------------------------------------------------------
@needs_model
@pytest.mark.parametrize("technology,diagram_type,diagram_name", [
    (_TOGAF, _TOGAF_TYPE, "TOGAF-ADM"),
    (_ZF, _ZF_TYPE, "Zachman Framework"),
])
def test_fill_is_claimed_because_no_element_overrides_it(
        technology, diagram_type, diagram_name):
    """Both notations paint from the stereotype, which is why fill is not free.

    `BCol=-1` in an ObjectStyle is the ABSENCE of an override, not one, and
    reading it as one would put fill in `free` and invite a consumer to break
    the notation.
    """
    bound = find_binding(technology).diagram_type(diagram_type)
    assert bound.channels["fill"], "fill must be claimed, not `~`"
    assert not bound.channel_is_free("fill")
    with mb.open_model_copy(_MODEL) as conn:
        backcolors = [r[0] for r in conn.execute(
            "SELECT t.Backcolor FROM t_diagramobjects o "
            "JOIN t_object t ON t.Object_ID = o.Object_ID "
            "JOIN t_diagram d ON d.Diagram_ID = o.Diagram_ID "
            "WHERE d.Name = ?", (diagram_name,))]
    assert backcolors and set(backcolors) == {-1}
    for style in _object_styles(diagram_name):
        for part in style.split(";"):
            if part.startswith("BCol="):
                assert part == "BCol=-1", part


@needs_model
def test_every_zachman_cell_carries_an_embedded_image_so_icon_is_claimed():
    bound = find_binding(_ZF).diagram_type(_ZF_TYPE)
    assert "icon" in bound.claimed_channels()
    styles = _object_styles("Zachman Framework")
    assert len(styles) == 36
    assert all(re.search(r"ImageID=[0-9A-Fa-f]{2,}", s) for s in styles)


@needs_model
def test_no_adm_phase_carries_an_embedded_image_so_icon_is_the_shape_scripts():
    """The same channel claimed for the opposite measured reason.

    The Zachman cell holds an image and the ADM phase does not: the circle IS
    the shape script's output, so writing an image would replace it.
    """
    bound = find_binding(_TOGAF).diagram_type(_TOGAF_TYPE)
    assert "icon" in bound.claimed_channels()
    styles = _object_styles("TOGAF-ADM")
    assert len(styles) == 10
    assert not any(re.search(r"ImageID=[0-9A-Fa-f]{2,}", s) for s in styles)


@needs_model
def test_the_adm_routing_name_is_conventional_and_the_measurement_disagrees():
    """17 of 17 connectors are `Mode=8`, which is not plain UML's `Mode=3`.

    The binding states `Direct` because a route name is mandatory and no mapping
    from EA's integer to a name exists in this skill. What is pinned here is the
    evidence that the stated name is a convention and probably wrong - so that
    whoever maps `Mode=` comes back to it.
    """
    bound = find_binding(_TOGAF).diagram_type(_TOGAF_TYPE)
    assert bound.default_route() == "Direct"
    modes = _connector_modes("TOGAF-ADM")
    assert sum(modes.values()) == 17
    assert modes == Counter({"8": 17})
    assert "Mode=8" in _TOGAF_TEXT


@needs_model
def test_the_zachman_grid_has_no_connectors_so_its_route_is_a_placeholder():
    bound = find_binding(_ZF).diagram_type(_ZF_TYPE)
    assert bound.default_route() == "Direct"
    assert sum(_connector_modes("Zachman Framework").values()) == 0
    assert "PLACEHOLDER" in _ZF_TEXT


# ---------------------------------------------------------------------------
# RESOLUTION - the two new bindings must not make anything else ambiguous
# ---------------------------------------------------------------------------
@needs_model
@pytest.mark.parametrize("technology,diagram_type,diagram_name", [
    (_TOGAF, _TOGAF_TYPE, "TOGAF-ADM"),
    (_ZF, _ZF_TYPE, "Zachman Framework"),
])
def test_each_bound_diagram_resolves_on_the_exact_path_from_its_own_style_ex(
        technology, diagram_type, diagram_name, diagram_rows, known):
    """The strongest path, and the one that makes the lower-case base harmless."""
    style_ex, base = next(
        (s, b) for _, name, b, s in diagram_rows if name == diagram_name)
    resolution = resolve_diagram(
        known, style_ex=style_ex, diagram_type=base, directory=_BINDINGS_DIR)
    assert resolution.resolved and resolution.path == "qualified"
    assert resolution.confidence == "exact"
    assert resolution.key == f"{technology}::{diagram_type}"


@needs_model
def test_a_plain_logical_diagram_still_resolves_to_uml_not_to_a_framework(known):
    """Adding two bindings drawn on `Logical` must not blur the base notation.

    A name match beats a base match, so `Diagram_Type = Logical` still lands on
    UML's own `Logical` entry. Note `UML` has to be in the id set explicitly: it
    is not an MDG technology and the model's own inventory never reports it, so a
    caller adds it once it has established from `Diagram_Type` alone that a
    diagram claims no technology. That is the documented use of the id.
    """
    resolution = resolve_diagram(
        sorted(set(known) | {"UML"}), diagram_type="Logical",
        directory=_BINDINGS_DIR)
    assert resolution.resolved and resolution.path == "diagram-type"
    assert resolution.technology == "UML"


@needs_model
def test_the_weak_base_type_path_was_already_ambiguous_across_logical_bindings(
        known):
    """What these two bindings did NOT break, measured rather than assumed.

    Without `UML` in the id set, `Diagram_Type = Logical` has no name match and
    falls to the weak base-type path, where every binding drawn on `Logical`
    claims it - so the answer is `ambiguous`. That was already true of ArchiMate3's
    five types, SysML's BlockDefinition and the UAF framework grid before either
    framework binding existed, and adding two more claimants does not change the
    verdict. Asserted both ways so a later reader does not blame the frameworks
    for it.
    """
    without = resolve_diagram(
        sorted(set(known) - {_TOGAF, _ZF}), diagram_type="Logical",
        directory=_BINDINGS_DIR)
    assert without.is_ambiguous and len(without.candidates) > 1
    assert not any(c.startswith((_TOGAF, _ZF)) for c in without.candidates)

    with_frameworks = resolve_diagram(
        known, diagram_type="Logical", directory=_BINDINGS_DIR)
    assert with_frameworks.is_ambiguous
    assert f"{_TOGAF}::{_TOGAF_TYPE}" in with_frameworks.candidates
    assert f"{_ZF}::{_ZF_TYPE}" in with_frameworks.candidates
    assert len(with_frameworks.candidates) == len(without.candidates) + 2


@needs_model
def test_an_unbound_framework_diagram_reports_unbound_rather_than_a_sibling(
        known, diagram_rows):
    """A diagram that says what it is and cannot be bound is unbound, not guessed.

    Five TOGAF diagram types are deliberately unkeyed, and a `TOGAF_ADM` diagram
    must NOT fall through to the one type that IS keyed - that would hand a phase
    page the ADM wheel's conventions.
    """
    style_ex, base = next(
        (s, b) for _, _, b, s in diagram_rows
        if mb.parse_mdg(s or "") == (_TOGAF, "TOGAF_ADM"))
    resolution = resolve_diagram(
        known, style_ex=style_ex, diagram_type=base, directory=_BINDINGS_DIR)
    assert not resolution.resolved and resolution.path == "unbound"
    assert resolution.technology == _TOGAF
    assert resolution.diagram_type_name == "TOGAF_ADM"


@needs_model
def test_a_zachman_perspective_diagram_is_not_installed_as_far_as_bindings_go(
        known, diagram_rows):
    """The six unbound ids are installed and unbound, which is a third answer.

    Not `not-installed` - EA has them - and not resolved. A caller must fall back
    to the engine's defaults rather than reach for the grid's binding because the
    word Zachman appears in both.
    """
    style_ex, base = next(
        (s, b) for _, _, b, s in diagram_rows
        if mb.parse_mdg(s or "")[0] == "ZF Planner")
    resolution = resolve_diagram(
        known, style_ex=style_ex, diagram_type=base, directory=_BINDINGS_DIR)
    assert not resolution.resolved and resolution.path == "unbound"
    assert resolution.technology == "ZF Planner"


# ---------------------------------------------------------------------------
# House rules the release gate also enforces, checked here so a failure is local
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("filename", [_TOGAF_FILE, _ZF_FILE])
def test_neither_framework_binding_ships_a_local_path(filename):
    text = (_BINDINGS_DIR / filename).read_text(encoding="utf-8")
    assert not re.search(r"[A-Za-z]:\\", text)
    assert "\\Users\\" not in text and "/Users/" not in text


@pytest.mark.parametrize("filename", [_TOGAF_FILE, _ZF_FILE])
def test_neither_framework_binding_ships_crlf_line_endings(filename):
    assert b"\r\n" not in (_BINDINGS_DIR / filename).read_bytes()


@pytest.mark.parametrize("filename", [_TOGAF_FILE, _ZF_FILE])
def test_neither_framework_binding_uses_british_spelling(filename):
    """US English is the house style and the gate fails the build on it.

    `HeadQuaters` and `Organisation` appear as STEREOTYPE and DIAGRAM names in
    the reference model, so the check is on prose only: neither of those strings
    is in either document, and neither is a British spelling of a word we chose.
    """
    text = (_BINDINGS_DIR / filename).read_text(encoding="utf-8").lower()
    for british in ("colour", "behaviour", "recognise", "normalise",
                    "centre", "judgement", "organise", "analyse"):
        assert british not in text, british

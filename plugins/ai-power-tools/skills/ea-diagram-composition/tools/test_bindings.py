#!/usr/bin/env python3
"""Tests for the language-binding schema and the two pilot bindings.

Run from the repository root:

    python -m pytest ea-diagram-composition/tools/test_bindings.py -q

Hermetic. These tests read the shipped binding files from disk, which is the
point of several of them, but nothing here touches Sparx EA, a repository or a
COM object. The live generation tests - one diagram per pilot binding, composed,
placed, verified and linted - live with the server suite, because that is where
a `repo` fixture exists.

WHAT THESE TESTS ARE PROTECTING
-------------------------------
Three different things, and it is worth knowing which is which:

1. **The schema rejects what it should.** Every validation rule has a test that
   feeds it a document it must refuse. A validator that accepts everything is
   indistinguishable from no validator, and the failure it lets through is a
   diagram that came out wrong for a reason nobody can find.

2. **The pilots say what was measured.** The numbers in the shipped bindings
   came from real diagrams. Tests pin the ones that would be most damaging to
   "tidy up" - the technology ids, the `Business Process` space, the
   `ArchiMate_` prefix, the 30x30 events.

3. **The layer boundary holds.** `compose.py` knows no technology names, and
   the two bindings differ only in data. A single `if technology ==` in the
   engine would undo the design while every other test still passed.
"""
from __future__ import annotations

import ast
import sys
from pathlib import Path

import pytest

_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

import bindings  # noqa: E402
from bindings import (  # noqa: E402
    CHANNELS,
    COMPOSED_GRAMMARS,
    EA_PLACED_GRAMMARS,
    GRAMMAR_PLACEMENT,
    GRAMMARS,
    HEADER_ADVANCE_PX,
    IMPLEMENTED_GRAMMARS,
    PLACED_BY_DIAGRAM_TYPE,
    PLACED_BY_EA,
    PLACED_BY_ENGINE,
    RESOLUTION_PATHS,
    RESOLVED_PATHS,
    ROUTE_NAMES,
    TITLE_CONVENTIONS,
    Binding,
    BindingError,
    Resolution,
    SpecFit,
    FIT_ANSWERS,
    FIT_OVERLAP,
    FIT_WIDEN,
    available_bindings,
    bindings_for_technologies,
    find_binding,
    implemented_grammars,
    load_binding,
    load_binding_text,
    mdg_diagram_key,
    producible_grammars,
    resolve_diagram,
    width_to_fit,
)
from lint import LABEL_MARGIN  # noqa: E402
from compose import (  # noqa: E402
    DEFAULT_SPEC,
    compose_lanes,
    compose_layered_bands,
)

_BINDINGS_DIR = _HERE.parent / "bindings"

pytest.importorskip("yaml", reason="PyYAML is required to read bindings")


# ---------------------------------------------------------------------------
# A minimal valid document, and a helper to break one field at a time
# ---------------------------------------------------------------------------
MINIMAL = """
technology: WBA
diagram_types:
  Overview:
    grammar: layered-bands
    title: drawn
    sizing:
      default: {w: 100, h: 60}
    routing:
      default: Direct
    channels:
      fill: ~
      free: [border]
"""


def _doc(**overrides: str) -> str:
    """Build a document from `MINIMAL` with one block swapped out.

    Keeps the rejection tests to the one line each is about, so a failure names
    the rule rather than a wall of YAML.
    """
    text = MINIMAL
    for old, new in overrides.items():
        marker = old.replace("__", " ")
        assert marker in text, f"{marker!r} not in the minimal document"
        text = text.replace(marker, new)
    return text


def _prose(text: str) -> str:
    """A binding file's words on one line, comment markers and wrapping removed.

    A figure stated in a comment wraps across lines and every continuation line
    starts with `#`, so an assertion that the file states some number has to read
    past both. Collapsing to single-spaced words with the markers stripped is what
    lets the assertion be written the way a person reads the sentence, instead of
    against whatever column the comment happened to wrap at.
    """
    return " ".join(
        " ".join(line.lstrip().lstrip("#")
                 for line in text.splitlines()).split())


# ---------------------------------------------------------------------------
# The happy path first - every later test asserts a deviation from this
# ---------------------------------------------------------------------------
def test_minimal_document_loads():
    binding = load_binding_text(MINIMAL)
    assert binding.technology == "WBA"
    assert binding.display_name == "WBA"
    assert binding.extends is None
    assert binding.stereotype_prefix == ""
    assert sorted(binding.diagram_types) == ["Overview"]
    assert binding.viewpoints == {}
    assert binding.presentation_profiles == {}


def test_a_diagram_type_translates_to_a_layout_spec():
    dt = load_binding_text(MINIMAL).diagram_type("Overview")
    assert dt.spec() == {"item_width": 100, "item_height": 60}


def test_spec_overrides_win_over_the_binding():
    dt = load_binding_text(MINIMAL).diagram_type("Overview")
    assert dt.spec({"item_width": 200})["item_width"] == 200


def test_a_spec_override_naming_an_unknown_key_is_refused():
    """Refused here rather than by the engine.

    The engine's message would be about a spec key and would not mention the
    binding, sending the reader to the wrong file.
    """
    dt = load_binding_text(MINIMAL).diagram_type("Overview")
    with pytest.raises(BindingError, match="item_wdith"):
        dt.spec({"item_wdith": 200})


# ---------------------------------------------------------------------------
# Sizing to fit the content's names
#
# Measured live against EA 17.1 and recorded in the diagram-gallery research
# note: EA never clips a name and never shrinks the font. It GROWS THE DRAWN
# BOX and leaves the stored geometry alone, so a diagram stops matching the
# rects every other check reads. The numbers pinned below are that note's, not
# this file's.
# ---------------------------------------------------------------------------
#: A name with no space in it, 36 characters long, which EA drew 169px wide
#: against a stored width of 60 in the live content sweep. Kept as one constant
#: so every test below is arguing about the same measured case.
_UNBREAKABLE_36 = "WestbrookCorporateTreasuryLiquidity1"
_DRAWN_WIDTH_OF_UNBREAKABLE_36 = 169

#: Per-character advance measured off live renders, over the SPACE-FREE runs -
#: what has to fit on one line, because EA breaks on spaces and never inside a
#: word. `(characters, measured pixels)`.
_MEASURED_RUNS = ((4, 17), (8, 39), (10, 48), (12, 54), (10, 55), (31, 152))


def test_a_name_too_long_for_the_convention_widens_the_box():
    """The defect, as a test.

    `sizing.default` is measured for a typical name and knows nothing about the
    one in front of it. Give it a name it cannot hold and the width has to move,
    because the alternative is EA moving it silently in the render.
    """
    dt = load_binding_text(MINIMAL).diagram_type("Overview")
    fitted = dt.spec(names=[_UNBREAKABLE_36])
    assert fitted.item_width > dt.spec().item_width
    assert fitted.item_width >= _DRAWN_WIDTH_OF_UNBREAKABLE_36


def test_the_width_that_was_asked_for_is_a_floor_and_not_the_answer():
    """An override is as capable of being too narrow as a measured default is.

    The live sweep found this on a caller-chosen 60, not on a binding's figure,
    so fitting before the override would have left the case that was actually
    reported unfixed.
    """
    dt = load_binding_text(MINIMAL).diagram_type("Overview")
    fitted = dt.spec({"item_width": 60}, names=[_UNBREAKABLE_36])
    assert fitted.requested_width == 60
    assert fitted.item_width >= _DRAWN_WIDTH_OF_UNBREAKABLE_36


def test_a_spec_that_widened_says_what_it_widened_and_why():
    """A measured convention that was not used has to be visible.

    `sizing.default` is somebody's measurement of real diagrams and
    `default_size_provenance` names whose. Substituting a third number for it in
    silence would leave a caller reading a figure that was not the one used.
    """
    dt = load_binding_text(MINIMAL).diagram_type("Overview")
    fitted = dt.spec(names=["Hub", _UNBREAKABLE_36])
    assert fitted.widened
    assert fitted.driver == _UNBREAKABLE_36
    assert "100" in fitted.note and str(fitted.item_width) in fitted.note
    assert _UNBREAKABLE_36 in fitted.note


def test_a_spec_that_did_not_have_to_widen_reports_nothing():
    """Silence has to mean something, so it only happens when nothing moved."""
    dt = load_binding_text(MINIMAL).diagram_type("Overview")
    fitted = dt.spec(names=["Hub", "Payments"])
    assert not fitted.widened
    assert fitted.driver == ""
    assert fitted.note == ""
    assert fitted.item_width == fitted.requested_width == 100


def test_a_spec_given_no_names_measures_none_and_is_still_a_plain_spec():
    """No names, no fitting, and the same dict as before.

    Nothing can fit text it was not given, so this is the one case where the
    convention's width stands unexamined. It is also every existing caller, and
    a `SpecFit` has to be indistinguishable from the dict they were getting.
    """
    dt = load_binding_text(MINIMAL).diagram_type("Overview")
    fitted = dt.spec()
    assert isinstance(fitted, SpecFit)
    assert fitted == {"item_width": 100, "item_height": 60}
    assert dict(fitted) == fitted


def test_only_the_run_ea_cannot_break_has_to_fit():
    """EA wraps on SPACES ONLY, so a multi-word name breaks itself.

    Measured: the same name with spaces came back as one text run per line at a
    13px pitch, and without them as a single line running 52px past both
    borders. Sizing a box to a whole multi-word name would widen every ordinary
    diagram to fit a line EA was never going to draw.
    """
    words = "Westbrook Bank Corporate Treasury and Liquidity Management"
    assert width_to_fit(words) == width_to_fit("Management")
    assert width_to_fit(words) < width_to_fit(words.replace(" ", ""))


def test_the_advance_is_the_measured_maximum_because_a_mean_under_predicts():
    """The constant's own calibration, as a test.

    Under-prediction is the failure being prevented: a box that is nearly wide
    enough is a box EA still grows. So the estimate has to bound every measured
    run, and the mean of the same population does not - which is the reason the
    maximum is taken and the reason this test exists rather than a comment
    saying so.
    """
    for chars, measured in _MEASURED_RUNS:
        assert chars * HEADER_ADVANCE_PX >= measured, (chars, measured)
    mean_advance = 4.9
    assert any(chars * mean_advance < measured
               for chars, measured in _MEASURED_RUNS)


# APT-2026-0193. The constant's "NOT VALIDATED FOR" paragraph is now enforced
# rather than merely written: a stated population with no guard is the same defect
# one layer down. `unvalidated_glyphs` is the guard, `SpecFit.extrapolated` is where
# it surfaces, and it reports rather than raising - a model whose element names are
# in Japanese or Russian must still compose.
_CYRILLIC = "Клиент"          # 6 letters, narrow
_FULL_WIDTH = "顧客口座"                        # 4 full-width glyphs


def test_a_name_inside_the_calibrated_repertoire_carries_no_guard():
    assert bindings.unvalidated_glyphs("WestbrookBankArchitecture") == ()
    assert bindings.unvalidated_glyphs("") == ()
    assert set("Westbrook Bank 42!") <= bindings.CALIBRATED_REPERTOIRE


def test_the_guard_names_every_glyph_the_constant_never_measured():
    assert bindings.unvalidated_glyphs(_CYRILLIC) == tuple(sorted(set(_CYRILLIC)))
    # De-duplicated and sorted, so the report does not depend on the name's order.
    assert bindings.unvalidated_glyphs(_CYRILLIC * 3) ==         bindings.unvalidated_glyphs(_CYRILLIC)


def test_a_narrow_out_of_repertoire_glyph_is_charged_the_calibrated_advance():
    """There is nothing better to charge it, and no reason to think it is wider.

    That is exactly why the prediction has to be FLAGGED rather than trusted: the
    number is the same one Latin gets, on no evidence that it should be.
    """
    assert width_to_fit(_CYRILLIC) == width_to_fit("abcdef")
    assert bindings.unvalidated_glyphs(_CYRILLIC)


def test_a_full_width_glyph_is_charged_two_cells_because_that_is_derived():
    """Unicode East Asian Width W/F means two character cells, and no cell in the
    calibrated population was wider than HEADER_ADVANCE_PX. So two cells cannot be
    narrower than twice it: a floor, not a second estimate, and it errs wide."""
    assert bindings.FULL_WIDTH_CELLS == 2
    assert width_to_fit(_FULL_WIDTH) == width_to_fit("a" * (4 * 2))
    assert width_to_fit(_FULL_WIDTH) > width_to_fit("a" * 4)


def test_the_fit_report_says_which_widths_were_extrapolated():
    dt = find_binding("UML").diagram_type("Logical")
    fit = dt.spec(names=[_FULL_WIDTH + _FULL_WIDTH + _FULL_WIDTH, "Plain"])
    assert set(fit.extrapolated) == {_FULL_WIDTH * 3}
    assert fit.extrapolated[_FULL_WIDTH * 3] == bindings.unvalidated_glyphs(_FULL_WIDTH)
    assert "WIDTH EXTRAPOLATED" in fit.note


def test_a_name_that_fits_is_still_reported_as_extrapolated():
    """Every name, not just the widest: the caller deciding whether to verify the
    rendered diagram needs all of them, and a short one can still be out of
    population."""
    dt = find_binding("UML").diagram_type("Logical")
    fit = dt.spec(names=["x", _CYRILLIC])
    assert not fit.widened and fit.conflicts == ()
    assert set(fit.extrapolated) == {_CYRILLIC}
    assert "WIDTH EXTRAPOLATED" in fit.note


def test_an_all_ascii_composition_reports_no_extrapolation():
    dt = find_binding("UML").diagram_type("Logical")
    fit = dt.spec(names=["Westbrook", "Bank"])
    assert fit.extrapolated == {} and fit.note == ""


def test_the_width_it_fits_to_is_the_clearance_the_linter_asks_for():
    """Prevention and detection have to aim at one number.

    `LABEL_MARGIN` is imported rather than restated, so recalibrating the rule
    moves the composer with it. This pins the arithmetic that consumes it: a
    fitted box leaves a full margin on each side, which also clears the narrower
    threshold at which EA stops growing the box.
    """
    assert width_to_fit("Management") == 55 + 2 * LABEL_MARGIN
    assert width_to_fit("") == 0


def test_every_peer_keeps_one_width_when_one_name_forces_a_wider_box():
    """Uniform across the role, or the fix trades one finding for another.

    The widening lands on `item_width`, which is the value every grammar falls
    back to, so a band of boxes stays a band of boxes at one size. Widening only
    the box whose name is long would satisfy the text-fit rules and fail
    `inconsistent-sizing`, which is the same diagram read as a different kind of
    wrong.
    """
    dt = load_binding_text(MINIMAL).diagram_type("Overview")
    fitted = dt.spec(names=["Hub", _UNBREAKABLE_36, "Payments"])
    result = compose_layered_bands([
        {"name": "Upper", "items": [{"id": 1, "name": "Hub"},
                                    {"id": 2, "name": _UNBREAKABLE_36}]},
        {"name": "Lower", "items": [{"id": 3, "name": "Payments"}]},
    ], fitted)
    widths = {item["right"] - item["left"] for item in result["items"]}
    assert widths == {fitted.item_width}


def test_a_name_that_is_not_a_string_is_refused():
    """An element id passed where a name belongs would measure as zero.

    `len()` of the wrong thing either raises somewhere less informative or,
    worse, succeeds - so it is refused here, naming the position.
    """
    dt = load_binding_text(MINIMAL).diagram_type("Overview")
    with pytest.raises(BindingError, match=r"names\[1\]"):
        dt.spec(names=["Hub", 13477])


# ---------------------------------------------------------------------------
# APT-2026-0187: widen or overlap is the user's call, so the conflict is surfaced
#
# The position this replaces was that supplying the names IS the request, so
# there was nothing to ask and no flag to offer. That was right about the intent
# and wrong about the conflict: widening the box and letting the text overlap the
# border are both legitimate drawings, and which one a diagram wants is a
# judgment about that diagram. Widening stays the default, because EA grows a box
# it cannot fit whatever the stored rect says - so it is the only answer under
# which the stored geometry is the geometry EA paints. What these tests pin is
# that it is no longer SILENT, and that an answer to the contrary binds.
# ---------------------------------------------------------------------------
def test_a_name_that_does_not_fit_is_reported_as_a_conflict():
    """Machine-readable, because an agent has to act on it rather than read it.

    A one-line note was already there, and prose is not something to branch on.
    The record names what did not fit, what each option costs, which was applied
    and - the field that matters - that nobody chose it.
    """
    dt = load_binding_text(MINIMAL).diagram_type("Overview")
    fitted = dt.spec(names=["Hub", _UNBREAKABLE_36])

    assert len(fitted.conflicts) == 1
    c = fitted.conflict
    assert c is fitted.conflicts[0]
    assert c["conflict"] == "width_does_not_fit_content"
    assert c["where"] == "spec.item_width"
    assert c["driver"] == _UNBREAKABLE_36
    assert c["driver_kind"] == "item_name"
    assert c["requested_width"] == 100
    assert c["required_width"] == width_to_fit(_UNBREAKABLE_36)
    assert [o["answer"] for o in c["options"]] == [FIT_WIDEN, FIT_OVERLAP]
    assert [o["width"] for o in c["options"]] == [c["required_width"], 100]
    assert _UNBREAKABLE_36 in c["question"]
    assert "36-character" in c["detail"]
    assert fitted.unanswered_conflicts == (c,)


def test_the_default_when_nobody_answers_is_still_the_widening():
    """The safe direction, unchanged - and now on the record as a default.

    Changing what happens by default would move every existing caller, and the
    direction it would move them in is the one where the stored rect stops
    matching the render. So the width is exactly what it was; `answered` is what
    is new, and False is it saying the question is still open.
    """
    dt = load_binding_text(MINIMAL).diagram_type("Overview")
    fitted = dt.spec(names=["Hub", _UNBREAKABLE_36])
    assert fitted.item_width == width_to_fit(_UNBREAKABLE_36)
    assert fitted.item_width >= _DRAWN_WIDTH_OF_UNBREAKABLE_36
    assert fitted.widened
    assert fitted.conflict["applied"] == FIT_WIDEN
    assert fitted.conflict["answered"] is False

    answered = dt.spec(names=["Hub", _UNBREAKABLE_36], on_misfit=FIT_WIDEN)
    assert answered.item_width == fitted.item_width, "same geometry"
    assert answered.conflict["answered"] is True, "different provenance"


def test_the_user_choosing_overlap_keeps_the_width_they_asked_for():
    """The answer has to bind, or the conflict report is decoration.

    `overlap` is not a return to the old behavior: the width is the same one the
    old code produced, and the conflict is still reported, so the choice is on
    the record rather than being a default nobody saw. Note `widened` is False
    here while `conflicts` is not empty - nothing moved, and something was still
    decided.
    """
    dt = load_binding_text(MINIMAL).diagram_type("Overview")
    chosen = dt.spec(names=["Hub", _UNBREAKABLE_36], on_misfit=FIT_OVERLAP)

    assert chosen.item_width == chosen.requested_width == 100
    assert not chosen.widened
    assert chosen.driver == _UNBREAKABLE_36, "which name it was is the same fact"
    assert chosen.conflict["applied"] == FIT_OVERLAP
    assert chosen.conflict["width_applied"] == 100
    assert chosen.conflict["answered"] is True
    assert chosen.unanswered_conflicts == ()
    assert chosen.note, "a choice that was made still gets said out loud"


def test_a_spec_whose_names_all_fit_reports_no_conflict():
    """Silence has to mean something, so it only happens when nothing conflicted.

    Three ways for there to be nothing to report - names that fit, no names at
    all, and an override wide enough for them - and all three come back with an
    empty tuple rather than a conflict whose `applied` nobody should read.
    """
    dt = load_binding_text(MINIMAL).diagram_type("Overview")
    for label, fitted in (
        ("names that fit", dt.spec(names=["Hub", "Payments"])),
        ("no names", dt.spec()),
        ("an override wide enough",
         dt.spec({"item_width": 400}, names=[_UNBREAKABLE_36])),
    ):
        assert fitted.conflicts == (), label
        assert fitted.conflict is None, label
        assert fitted.unanswered_conflicts == (), label
        assert fitted.note == "", label
        assert not fitted.widened, label


def test_an_answer_that_is_not_one_of_the_two_is_refused_by_the_binding():
    """Refused here, and as a `BindingError`, for the reason an unknown override
    key is: the engine's message would be about a layout spec and would not
    mention the binding, sending the reader to the wrong file. Refused whether or
    not this call turns out to have a conflict, because a caller relaying an
    answer has already asked the user and a typo must not read as silence.
    """
    dt = load_binding_text(MINIMAL).diagram_type("Overview")
    for names in ([_UNBREAKABLE_36], ["Hub"], []):
        with pytest.raises(BindingError, match="on_misfit"):
            dt.spec(names=names, on_misfit="wider")
    assert FIT_ANSWERS == (FIT_WIDEN, FIT_OVERLAP)


def test_the_conflict_travels_as_plain_json_data():
    """It has to cross a tool boundary, so it must not need this module to read.

    A `FitConflict` IS a dict and every value in it is a str, int, bool or list
    of those, which is what makes it reportable by an MCP tool and readable by an
    agent that never imported anything from here.
    """
    import json

    dt = load_binding_text(MINIMAL).diagram_type("Overview")
    conflict = dt.spec(names=[_UNBREAKABLE_36]).conflict
    assert isinstance(conflict, dict)
    assert json.loads(json.dumps(conflict)) == conflict


# ---------------------------------------------------------------------------
# Rejection cases - one per rule
# ---------------------------------------------------------------------------
def test_an_unknown_top_level_key_is_refused():
    with pytest.raises(BindingError, match="color_palette"):
        load_binding_text(MINIMAL + "color_palette: {}\n")


def test_a_misspelled_top_level_key_gets_the_right_one_named():
    with pytest.raises(BindingError, match="use diagram_types"):
        load_binding_text(MINIMAL.replace("diagram_types:", "diagramTypes:"))


def test_a_missing_technology_is_refused():
    with pytest.raises(BindingError, match=r"\.technology"):
        load_binding_text(MINIMAL.replace("technology: WBA", "extends: ~"))


def test_a_technology_id_containing_the_separator_is_refused():
    """`MDGDgm` values look like `BPMN2.0::Business Process`.

    An author who pastes the whole thing in as the technology id has bound a
    technology that does not exist, and every resolution against it returns
    nothing without complaining.
    """
    with pytest.raises(BindingError, match="part BEFORE"):
        load_binding_text(MINIMAL.replace("technology: WBA",
                                          "technology: WBA::Overview"))


def test_no_diagram_types_is_refused():
    with pytest.raises(BindingError, match="diagram_types"):
        load_binding_text("technology: WBA\ndiagram_types: {}\n")


def test_an_unknown_grammar_is_refused_and_the_whole_vocabulary_is_named():
    with pytest.raises(BindingError) as exc:
        load_binding_text(_doc(**{"grammar:__layered-bands":
                                  "grammar: spiral"}))
    message = str(exc.value)
    assert "spiral" in message
    for grammar in GRAMMARS:
        assert grammar in message


def _with_grammar(grammar: str) -> str:
    """The minimal document with one grammar swapped in."""
    return _doc(**{"grammar:__layered-bands": f"grammar: {grammar}"})


def test_a_composed_grammar_the_engine_cannot_compose_yet_still_loads():
    """A composed grammar the engine has not built yet loads and says so.

    Refusing it would force a binding author to record an implemented grammar
    for a diagram type that is genuinely something else - a lie stored as data.
    The binding records the truth and `grammar_is_implemented` is how a consumer
    finds out before composing rather than after.

    The example grammar is DERIVED rather than named. This test previously named
    `nested-grid`, and the day that grammar shipped the test failed for a reason
    that had nothing to do with the property under test. What it is really
    asserting is "whichever composed grammar is unbuilt, a binding may still name
    it", so it asks which one that is.

    Derived from `COMPOSED_GRAMMARS` and not from the whole vocabulary: two
    grammars are unimplemented BY NATURE rather than by lag - nobody will ever
    write a composer for a shape EA places - and picking one of those would make
    this test assert something else.
    """
    unbuilt = sorted(COMPOSED_GRAMMARS - implemented_grammars())
    if not unbuilt:
        pytest.skip(
            "every composed grammar is implemented, so there is no unbuilt one "
            "to name; delete this test or add the next grammar to "
            "GRAMMAR_PLACEMENT first"
        )
    grammar = unbuilt[0]
    dt = load_binding_text(_with_grammar(grammar)).diagram_type("Overview")
    assert dt.grammar == grammar
    assert dt.geometry_is_composed is True
    assert dt.grammar_is_implemented is False
    # Ours to compute and not computed yet, so nothing can produce it today.
    assert dt.grammar_is_producible is False


# ---------------------------------------------------------------------------
# Composed, EA-placed, EA-semantic: three placements, two questions
# ---------------------------------------------------------------------------
# `grammar` used to mean "one of the composed layouts", and `GRAMMARS` carried
# one boolean per name that answered both "do we compose this" and "can we
# produce this" - which is fine only while those are the same question. They
# stopped being the same question the moment a diagram type EA lays out could be
# recorded, so the boolean was split. These tests pin both answers for each
# placement, and pin that neither can be derived from the other.
def test_a_graph_grammar_loads_and_is_producible_without_being_composed():
    """The case the vocabulary could not state before.

    A graph or a tree: we compute no coordinates, EA's layout does, and we tidy
    afterwards. Everything else the binding carries is still worth having, so the
    whole document below is asserted rather than just the grammar - a binding
    that loaded but dropped its sizes, spacing or routing would be no use to the
    layout call that consumes them.
    """
    dt = load_binding_text(_with_grammar("graph")).diagram_type("Overview")
    assert dt.grammar == "graph"
    assert dt.grammar_placement == PLACED_BY_EA
    assert dt.geometry_is_composed is False
    assert dt.grammar_is_implemented is False
    assert dt.grammar_is_producible is True
    assert dt.size_for() == (100, 60)
    assert dt.default_route() == "Direct"
    assert dt.channel_is_free("border") is True
    assert dt.draws_its_own_title is True
    # The spacing a layout call reads as layer and column spacing survives the
    # trip through `spec()`, which is the only route it reaches a caller by.
    spaced = load_binding_text(
        _with_grammar("graph") + "    spacing:\n      item_gap_x: 60\n"
    ).diagram_type("Overview")
    assert spaced.spec()["item_gap_x"] == 60


def test_an_ea_semantic_grammar_loads_and_is_not_producible():
    """The diagram TYPE dictates the arrangement, so we produce nothing yet.

    Recorded rather than omitted: an omitted diagram type is indistinguishable
    from an oversight, and that ambiguity is what the value exists to remove. So
    it must LOAD - and it must not be counted, which is the other half.
    """
    dt = load_binding_text(_with_grammar("ea-semantic")).diagram_type("Overview")
    assert dt.grammar == "ea-semantic"
    assert dt.grammar_placement == PLACED_BY_DIAGRAM_TYPE
    assert dt.geometry_is_composed is False
    assert dt.grammar_is_implemented is False
    assert dt.grammar_is_producible is False


def test_the_composed_grammars_answer_exactly_as_they_did_before():
    """The regression that would silently move a published reach figure.

    A measurement tool outside this repository reads `IMPLEMENTED_GRAMMARS` and
    derives reach from it. Widening the vocabulary must not widen that set, and
    must not change any composed grammar's answer: `grammar_is_implemented` still
    means "the engine has a composer", and for a composed grammar it is still the
    whole of producibility.
    """
    for grammar in sorted(COMPOSED_GRAMMARS):
        dt = load_binding_text(_with_grammar(grammar)).diagram_type("Overview")
        assert dt.grammar_placement == PLACED_BY_ENGINE, grammar
        assert dt.geometry_is_composed is True, grammar
        assert dt.grammar_is_implemented is (grammar in _engine_grammars()), \
            grammar
        # For these five, and only these five, the two questions coincide.
        assert dt.grammar_is_producible is dt.grammar_is_implemented, grammar
    assert IMPLEMENTED_GRAMMARS == _engine_grammars()
    assert IMPLEMENTED_GRAMMARS <= COMPOSED_GRAMMARS


def test_producible_and_composed_are_not_the_same_question():
    """The check that the two answers cannot be collapsed back into one.

    Each of the three sets below must be non-empty, and each is a different
    reason: a grammar we can produce and do not compose, a grammar we compose and
    cannot yet produce, and a grammar that is neither. Any implementation that
    answered both questions from one boolean makes at least one of them empty.
    """
    producible_not_composed = producible_grammars() - COMPOSED_GRAMMARS
    composed_not_producible = COMPOSED_GRAMMARS - producible_grammars()
    neither = GRAMMARS - producible_grammars() - COMPOSED_GRAMMARS
    assert producible_not_composed, (
        "no grammar is producible without being composed, so the two questions "
        "have collapsed into one")
    assert composed_not_producible, (
        "every composed grammar is built, so this test can no longer tell a "
        "composed grammar from a producible one; pick another evidence case")
    assert neither, (
        "nothing is recorded as neither producible nor composed, so a diagram "
        "type whose arrangement its own type dictates has nowhere to go")
    assert producible_grammars() == implemented_grammars() | EA_PLACED_GRAMMARS


def test_implementedness_is_read_from_the_engine_rather_than_remembered(
        monkeypatch):
    """The derivation, exercised. A literal would pass every other test here.

    `IMPLEMENTED_GRAMMARS` was a flag per grammar kept by hand, pinned to the
    engine by a comparison. That is two copies of one fact agreeing with each
    other, and the same shape once let a measurement tool report a remembered
    reach figure for a grammar that had already shipped. So the set is now read
    out of the engine on every call, and this test moves the engine to prove it:
    a composer that appears is picked up, a composer that disappears is dropped.
    Replace the derivation with any written-down set and both halves fail.
    """
    import compose

    built = sorted(implemented_grammars())
    unbuilt = sorted(COMPOSED_GRAMMARS - implemented_grammars())
    assert built and unbuilt, (
        "this test needs one composed grammar of each kind to move")
    grammar, composed_away = unbuilt[0], built[0]
    dt = load_binding_text(_with_grammar(grammar)).diagram_type("Overview")
    assert dt.grammar_is_implemented is False

    monkeypatch.setattr(compose, f"compose_{grammar.replace('-', '_')}",
                        lambda *args, **kwargs: None, raising=False)
    assert grammar in implemented_grammars()
    assert grammar in producible_grammars()
    assert dt.grammar_is_implemented is True
    assert dt.grammar_is_producible is True
    # The module constant is a snapshot taken at import, on purpose: a consumer
    # reading it gets one stable answer per process rather than one that moves
    # under it. The function is what a caller asks when that matters.
    assert grammar not in IMPLEMENTED_GRAMMARS

    monkeypatch.delattr(compose,
                        f"compose_{composed_away.replace('-', '_')}")
    assert composed_away not in implemented_grammars()
    assert composed_away not in producible_grammars()
    assert load_binding_text(_with_grammar(composed_away)).diagram_type(
        "Overview").grammar_is_implemented is False


def test_a_grammar_ea_places_is_never_offered_as_something_to_compose():
    """The set a consumer sweeps to pick a composer must stay composer-only.

    A caller that iterates the implemented grammars and asks the engine for
    `compose_<grammar>` would raise on an entry that has none, so the EA-placed
    grammars must be absent from that set even though they are producible. This
    is the failure mode that made overloading the one boolean unsafe rather than
    merely untidy.
    """
    import compose

    for grammar in sorted(implemented_grammars()):
        assert callable(getattr(compose, f"compose_{grammar.replace('-', '_')}"))
    for grammar in sorted(GRAMMARS - COMPOSED_GRAMMARS):
        assert grammar not in implemented_grammars(), grammar
        assert not hasattr(compose, f"compose_{grammar.replace('-', '_')}"), \
            grammar


def test_every_grammar_states_who_places_its_geometry():
    """A grammar with no placement would answer both questions False and read as
    a composed layout nobody has built, which is the confusion the placement
    table exists to end."""
    for grammar in sorted(GRAMMARS):
        assert GRAMMAR_PLACEMENT[grammar] in (
            PLACED_BY_ENGINE, PLACED_BY_EA, PLACED_BY_DIAGRAM_TYPE), grammar
        dt = load_binding_text(_with_grammar(grammar)).diagram_type("Overview")
        assert dt.grammar_placement == GRAMMAR_PLACEMENT[grammar], grammar


def test_an_unknown_title_convention_is_refused():
    with pytest.raises(BindingError) as exc:
        load_binding_text(_doc(**{"title:__drawn": "title: centered"}))
    for convention in TITLE_CONVENTIONS:
        assert convention in str(exc.value)


def test_a_missing_title_convention_is_refused():
    """Neither convention can be the silent default.

    A diagram with two titles and a diagram with none are equally likely
    mistakes, and the corpus split tracks notation rather than taste.
    """
    with pytest.raises(BindingError, match="title"):
        load_binding_text(_doc(**{"title:__drawn": "notes: nothing"}))


def test_sizing_without_a_default_is_refused():
    """Still refused, for a narrower reason than when this was written.

    `sizing.default` used to be required of every DOCUMENT. It is now required of
    the resolved diagram type, checked after `_merge`, so that a diagram type
    drawn on a measured substrate can inherit the figure instead of inventing
    one. `MINIMAL` declares no `extends`, so there is nothing underneath it and
    the answer is unchanged: a root binding states every default it uses.

    Kept here rather than folded into the inheritance tests because the rule it
    pins is the one this file has always pinned - a diagram type cannot end up
    without a fallback box size. What supersedes it is only WHERE that is asked;
    `test_the_resolved_default_is_checked_after_the_merge_and_not_before` pins
    that, and the surrounding section pins the cases it now admits.
    """
    with pytest.raises(BindingError, match=r"sizing\.default"):
        load_binding_text(_doc(**{"default:__{w:__100,__h:__60}":
                                  "Widget: {w: 100, h: 60}"}))


def test_sizing_spelled_out_in_full_words_is_refused_with_the_short_key():
    with pytest.raises(BindingError, match="use 'w'"):
        load_binding_text(_doc(**{"default:__{w:__100,__h:__60}":
                                  "default: {width: 100, height: 60}"}))


@pytest.mark.parametrize("size", ["{w: 0, h: 60}", "{w: -5, h: 60}",
                                  "{w: 100.5, h: 60}", "{w: '100', h: 60}"])
def test_a_size_that_is_not_a_positive_whole_number_is_refused(size):
    with pytest.raises(BindingError, match=r"sizing\.default\.w"):
        load_binding_text(_doc(**{"default:__{w:__100,__h:__60}":
                                  f"default: {size}"}))


def test_a_spacing_key_the_engine_does_not_have_is_refused():
    with pytest.raises(BindingError, match="item_gap_z"):
        load_binding_text(MINIMAL + "    spacing:\n      item_gap_z: 10\n")


def test_the_pitch_key_from_the_original_sketch_names_what_to_use_instead():
    """The trap this schema was designed around.

    A pitch includes the box it steps over, so `pitch: 40` beside a 100-wide
    item is a layout the engine refuses. An author writing it deserves to be
    told which key they meant, not handed the engine's arithmetic complaint at
    generation time.

    Matched on the hint's own wording, not on `item_gap_x`: every unknown-key
    message ends in `Known keys: ..., item_gap_x, ...`, so matching the key name
    would pass with the hints dict empty and this test would be evidence of
    nothing. Remove the assertion and `pitch:` becomes a bare "unknown key"
    again, which is the failure the hint exists to prevent.
    """
    with pytest.raises(BindingError, match="includes the box it steps over"):
        load_binding_text(MINIMAL + "    spacing:\n      pitch: {h: 40}\n")


def test_every_spacing_key_the_engine_has_is_accepted():
    """Validation is against `compose.DEFAULT_SPEC` itself, so the two cannot
    drift: a spec key added to the engine is usable from a binding at once."""
    for key in DEFAULT_SPEC:
        load_binding_text(MINIMAL + f"    spacing:\n      {key}: 5\n")


def test_missing_routing_is_refused():
    with pytest.raises(BindingError, match="routing"):
        load_binding_text(MINIMAL.replace("    routing:\n      default: Direct\n",
                                          ""))


def test_a_route_ea_does_not_accept_is_refused():
    with pytest.raises(BindingError) as exc:
        load_binding_text(_doc(**{"default:__Direct": "default: Squiggly"}))
    assert "Squiggly" in str(exc.value)
    assert "OrthogonalSquare" in str(exc.value)


@pytest.mark.parametrize("spelling", ["OrthogonalSquare", "orthogonal square",
                                       "orthogonal-square", "ORTHOGONALSQUARE"])
def test_route_names_are_accepted_however_they_are_spelled(spelling):
    """Matching the server's own normalization, which strips non-alphanumerics
    and lowercases. A binding author should not have to guess the casing."""
    binding = load_binding_text(_doc(**{"default:__Direct":
                                        f"default: {spelling}"}))
    assert binding.diagram_type("Overview").default_route() == spelling


def _with_routing(*lines: str) -> str:
    """Splice extra keys into the routing block rather than appending them.

    Appending to `MINIMAL` lands the keys under `channels`, which is a different
    document that the schema correctly refuses for a different reason - and a
    test that passes because the wrong rule fired is worse than no test.
    """
    extra = "".join(f"      {line}\n" for line in lines)
    return MINIMAL.replace("      default: Direct\n",
                           "      default: Direct\n" + extra)


def test_trunk_for_gets_the_trunk_route_and_other_types_get_the_default():
    binding = load_binding_text(_with_routing("trunk_for: [Realization]",
                                              "trunk_route: TreeVertical"))
    dt = binding.diagram_type("Overview")
    assert dt.route_for("Realization") == "TreeVertical"
    assert dt.route_for("Association") == "Direct"


def test_trunk_for_without_a_trunk_route_defaults_to_orthogonal():
    dt = load_binding_text(
        _with_routing("trunk_for: [Realization]")).diagram_type("Overview")
    assert dt.route_for("Realization") == "OrthogonalSquare"


# ---------------------------------------------------------------------------
# Channels - the block the whole schema exists for
# ---------------------------------------------------------------------------
def test_a_missing_channels_block_is_refused():
    with pytest.raises(BindingError, match="channels"):
        load_binding_text(MINIMAL.replace(
            "    channels:\n      fill: ~\n      free: [border]\n", ""))


def test_a_channels_block_without_fill_is_refused():
    """`fill` is mandatory even when the answer is "nothing".

    Omitting it reads as "no opinion", and no opinion about fill is how an
    agent recolors ArchiMate's layer palette by lifecycle and breaks the
    notation while believing it added a feature.
    """
    with pytest.raises(BindingError, match=r"channels\.fill"):
        load_binding_text(MINIMAL.replace("      fill: ~\n", ""))


def test_fill_may_be_explicitly_unclaimed():
    dt = load_binding_text(MINIMAL).diagram_type("Overview")
    assert dt.claimed_channels() == {}
    assert dt.channel_is_free("border") is True
    assert dt.channel_is_free("fill") is False


def test_a_channel_cannot_be_both_claimed_and_free():
    """The cross-check that matters.

    A binding saying fill means layer AND that fill is free has told a
    consumer it is safe to overwrite the notation's own meaning.
    """
    with pytest.raises(BindingError, match="already claimed"):
        load_binding_text(_doc(**{"fill:__~": "fill: layer",
                                  "free:__[border]": "free: [fill, border]"}))


def test_a_claimed_channel_cannot_be_listed_free_either():
    with pytest.raises(BindingError, match="already claimed"):
        load_binding_text(
            MINIMAL.replace("free: [border]", "free: [border, icon]")
            + "      claimed:\n        icon: element type\n")


def test_fill_belongs_in_its_own_key_not_in_claimed():
    with pytest.raises(BindingError, match="one place too many"):
        load_binding_text(MINIMAL + "      claimed:\n        fill: layer\n")


def test_an_invented_channel_name_is_refused_and_the_real_ones_named():
    with pytest.raises(BindingError) as exc:
        load_binding_text(_doc(**{"free:__[border]": "free: [sparkle]"}))
    assert "sparkle" in str(exc.value)
    assert "opacity" in str(exc.value)


def test_a_duplicated_free_channel_is_refused():
    with pytest.raises(BindingError, match="duplicate"):
        load_binding_text(_doc(**{"free:__[border]":
                                  "free: [border, border]"}))


# ---------------------------------------------------------------------------
# Viewpoints
# ---------------------------------------------------------------------------
_VIEWPOINT = """
viewpoints:
  Landscape:
    diagram_type: Overview
    intent: [what is out there]
    admits: [Widget, Gadget]
"""


def test_a_viewpoint_loads_and_reports_what_it_admits():
    vp = load_binding_text(MINIMAL + _VIEWPOINT).viewpoint("Landscape")
    assert vp.diagram_type == "Overview"
    assert vp.admits == ("Widget", "Gadget")
    assert vp.admits_concept("Widget") is True
    assert vp.admits_concept("Sprocket") is False


def test_a_viewpoint_naming_an_undeclared_diagram_type_is_refused():
    """The one place a viewpoint catalog can be quietly wrong.

    A viewpoint pointing at a diagram type nothing declares would be selected
    and then fail to compose, with the error appearing nowhere near the typo.
    """
    with pytest.raises(BindingError, match="not declared"):
        load_binding_text(
            MINIMAL + _VIEWPOINT.replace("diagram_type: Overview",
                                         "diagram_type: Ovreview"))


def test_a_viewpoint_may_override_the_grammar():
    """A capability map is a nested grid even though its diagram type composes
    as bands, so the override is load-bearing rather than decorative."""
    vp = load_binding_text(
        MINIMAL + _VIEWPOINT + "    grammar: nested-grid\n"
    ).viewpoint("Landscape")
    assert vp.grammar == "nested-grid"


def test_a_viewpoint_grammar_outside_the_vocabulary_is_refused():
    with pytest.raises(BindingError, match="spiral"):
        load_binding_text(MINIMAL + _VIEWPOINT + "    grammar: spiral\n")


def test_a_viewpoint_may_override_to_a_grammar_ea_places():
    """The override has to answer both questions, for the same reason it exists.

    A viewpoint whose own arrangement is a graph, sitting on a diagram type that
    composes as bands, is producible - EA places it. A consumer reading only
    `grammar_is_implemented` would see False and drop a view it could have made,
    which is the mirror of the bug the override was added to fix.
    """
    vp = load_binding_text(
        MINIMAL + _VIEWPOINT + "    grammar: graph\n").viewpoint("Landscape")
    assert vp.effective_grammar == "graph"
    assert vp.geometry_is_composed is False
    assert vp.grammar_is_implemented is False
    assert vp.grammar_is_producible is True


def test_a_viewpoint_with_no_grammar_of_its_own_has_no_opinion_on_either():
    """`None`, not `False`, on all three: "this viewpoint has no opinion" is a
    different answer from "we know we cannot", and collapsing them would make
    every ordinary viewpoint look unsupported."""
    vp = load_binding_text(MINIMAL + _VIEWPOINT).viewpoint("Landscape")
    assert vp.effective_grammar == ""
    assert vp.grammar_is_implemented is None
    assert vp.grammar_is_producible is None
    assert vp.geometry_is_composed is None


def test_duplicate_admits_entries_are_refused():
    with pytest.raises(BindingError, match="duplicate"):
        load_binding_text(
            MINIMAL + _VIEWPOINT.replace("[Widget, Gadget]",
                                         "[Widget, Widget]"))


def test_viewpoints_admitting_ranks_narrowest_first():
    """A layered view of three applications is a layered view with two empty
    bands, so the narrower viewpoint that admits everything wins."""
    binding = load_binding_text(MINIMAL + """
viewpoints:
  Narrow:
    diagram_type: Overview
    admits: [Widget, Gadget]
  Wide:
    diagram_type: Overview
    admits: [Widget, Gadget, Sprocket, Cog]
""")
    ranked = binding.viewpoints_admitting(["Widget"])
    assert [vp.name for vp in ranked] == ["Narrow", "Wide"]
    assert binding.viewpoints_admitting(["Sprocket"])[0].name == "Wide"
    assert binding.viewpoints_admitting(["Unheard"]) == []


# ---------------------------------------------------------------------------
# Presentation profiles
# ---------------------------------------------------------------------------
def test_a_profile_says_what_it_shows_and_the_loader_inverts_it():
    """The polarity flip lives in exactly one place.

    A profile states what a reader sees; EA is told what to hide. Doing that
    inversion at each call site is how one of them ends up backwards.
    """
    binding = load_binding_text(MINIMAL + """
presentation_profiles:
  executive:
    connector_labels: false
    element_stereotypes: false
    collapse_parallel: true
    direction_only: true
""")
    profile = binding.profile("executive")
    assert profile.display_settings() == {"hide_connector_labels": True,
                                          "hide_element_stereotypes": True}
    assert profile.collapses_parallel is True


def test_a_profile_only_emits_settings_it_actually_states():
    """Silence is not a default.

    A profile that says nothing about stereotypes must leave them alone rather
    than assert a value it never chose - otherwise applying a profile undoes a
    deliberate choice made elsewhere.
    """
    binding = load_binding_text(
        MINIMAL + "presentation_profiles:\n  quiet:\n"
                  "    connector_labels: false\n")
    assert binding.profile("quiet").display_settings() == {
        "hide_connector_labels": True}


def test_a_profile_written_in_hide_flags_is_corrected():
    """A profile states what it SHOWS; the hint says so rather than just
    refusing the key.

    Matched on the hint's wording, not on `connector_labels`: that substring
    sits inside the rejected key itself (`hide_connector_labels`) and inside the
    message's `Known keys:` list, so it passes with no hint at all. Remove this
    assertion and an author who wrote the EA-facing polarity gets "unknown key"
    and no indication that the schema has the same setting the other way up.
    """
    with pytest.raises(BindingError, match="profiles say what they SHOW"):
        load_binding_text(
            MINIMAL + "presentation_profiles:\n  odd:\n"
                      "    hide_connector_labels: true\n")


def test_direction_only_without_collapsing_is_refused():
    """It only means something under collapsing, so a profile setting it alone
    reads as if it does something."""
    with pytest.raises(BindingError, match="collapse_parallel"):
        load_binding_text(
            MINIMAL + "presentation_profiles:\n  odd:\n"
                      "    direction_only: true\n")


def test_a_profile_flag_that_is_not_a_boolean_is_refused():
    with pytest.raises(BindingError, match="true or false"):
        load_binding_text(
            MINIMAL + "presentation_profiles:\n  odd:\n"
                      "    connector_labels: maybe\n")


def test_compartments_takes_a_keyword_or_a_list():
    binding = load_binding_text(MINIMAL + """
presentation_profiles:
  a: {compartments: all}
  b: {compartments: none}
  c: {compartments: [name, key-attributes]}
""")
    assert binding.profile("a").get("compartments") == "all"
    assert binding.profile("c").get("compartments") == ("name",
                                                        "key-attributes")
    with pytest.raises(BindingError, match="compartments"):
        load_binding_text(MINIMAL + "presentation_profiles:\n"
                                    "  d: {compartments: some}\n")


# ---------------------------------------------------------------------------
# Lookups fail loudly and name what exists
# ---------------------------------------------------------------------------
def test_an_unknown_lookup_names_what_is_declared():
    binding = load_binding_text(MINIMAL)
    with pytest.raises(BindingError, match="Overview"):
        binding.diagram_type("Missing")
    with pytest.raises(BindingError, match=r"\(none\)"):
        binding.viewpoint("Missing")
    with pytest.raises(BindingError, match=r"\(none\)"):
        binding.profile("Missing")


def test_mdgdgm_resolution_matches_only_its_own_technology():
    binding = load_binding_text(MINIMAL)
    assert binding.diagram_type_for_mdgdgm("WBA::Overview").name == "Overview"
    assert binding.diagram_type_for_mdgdgm("WBA::Elsewhere") is None
    assert binding.diagram_type_for_mdgdgm("WBAOther::Overview") is None
    assert binding.diagram_type_for_mdgdgm("") is None


# ---------------------------------------------------------------------------
# extends
# ---------------------------------------------------------------------------
def test_extends_inherits_what_the_child_does_not_restate(tmp_path):
    (tmp_path / "base.yaml").write_text(MINIMAL + """
presentation_profiles:
  detail: {connector_labels: true}
""", encoding="utf-8")
    (tmp_path / "house.yaml").write_text("""
technology: House
extends: WBA
stereotype_prefix: HSE_
diagram_types:
  Overview:
    grammar: lanes
    title: frame-header
    sizing:
      default: {w: 200, h: 80}
    routing:
      default: Direct
    channels:
      fill: ~
      free: []
""", encoding="utf-8")

    house = load_binding(tmp_path / "house.yaml")
    assert house.technology == "House"
    assert house.stereotype_prefix == "HSE_"
    # Restated: the child's version wins outright.
    assert house.diagram_type("Overview").grammar == "lanes"
    assert house.diagram_type("Overview").size_for() == (200, 80)
    # Not restated: inherited.
    assert "detail" in house.presentation_profiles


def test_a_child_inherits_the_parents_prefix_when_it_states_none(tmp_path):
    (tmp_path / "base.yaml").write_text(
        MINIMAL.replace("technology: WBA",
                        "technology: WBA\nstereotype_prefix: DM_"),
        encoding="utf-8")
    (tmp_path / "child.yaml").write_text(
        MINIMAL.replace("technology: WBA",
                        "technology: Child\nextends: WBA"),
        encoding="utf-8")
    assert load_binding(tmp_path / "child.yaml").stereotype_prefix == "DM_"


def test_extending_a_technology_with_no_binding_is_refused(tmp_path):
    (tmp_path / "orphan.yaml").write_text(
        MINIMAL.replace("technology: WBA",
                        "technology: Orphan\nextends: Nowhere"),
        encoding="utf-8")
    with pytest.raises(BindingError, match="Nowhere"):
        load_binding(tmp_path / "orphan.yaml")


def test_extending_itself_is_refused():
    with pytest.raises(BindingError, match="cannot extend itself"):
        load_binding_text(MINIMAL.replace("technology: WBA",
                                          "technology: WBA\nextends: WBA"))


def test_an_extends_cycle_is_refused_by_name(tmp_path):
    (tmp_path / "a.yaml").write_text(
        MINIMAL.replace("technology: WBA", "technology: A\nextends: B"),
        encoding="utf-8")
    (tmp_path / "b.yaml").write_text(
        MINIMAL.replace("technology: WBA", "technology: B\nextends: A"),
        encoding="utf-8")
    with pytest.raises(BindingError, match="cycle"):
        load_binding(tmp_path / "a.yaml")


# ---------------------------------------------------------------------------
# One id, one file: a shadowed technology is refused, not ranked
# ---------------------------------------------------------------------------
# Three readers used to disagree about a duplicate id in one directory, and every
# one of them was silent: `available_bindings` kept the LAST file in sorted order,
# `_binding_path` (so `find_binding` and every `extends`) took the FIRST, and the
# benchmark's index MERGED both files' diagram types. So the catalog could name one
# file for a technology while the composer drew with another.

def _two_claimants(tmp_path, technology="WBA", names=("aaa-shadow", "zzz-real")):
    for name in names:
        (tmp_path / f"{name}.yaml").write_text(
            MINIMAL.replace("technology: WBA", f"technology: {technology}"),
            encoding="utf-8")
    return tmp_path


def test_two_files_claiming_one_technology_id_are_refused_by_name(tmp_path):
    _two_claimants(tmp_path)
    with pytest.raises(bindings.DuplicateTechnology) as exc:
        available_bindings(tmp_path)
    message = str(exc.value)
    assert "'WBA'" in message
    assert "aaa-shadow.yaml" in message and "zzz-real.yaml" in message


def test_the_resolver_and_the_catalog_refuse_the_same_duplicate(tmp_path):
    """Both readers, because agreeing to be silent was the actual defect."""
    _two_claimants(tmp_path)
    with pytest.raises(bindings.DuplicateTechnology):
        find_binding("WBA", tmp_path)
    with pytest.raises(bindings.DuplicateTechnology):
        available_bindings(tmp_path)


def test_a_duplicate_is_refused_whichever_file_is_named_like_the_slug(tmp_path):
    """`_binding_path` short-circuits on `<slug>.yaml`; the check precedes it.

    The realistic duplicate is a second, descriptively named file beside the
    slug-named one, which is exactly the case the short-circuit would hide.
    """
    _two_claimants(tmp_path, names=("wba", "wba-house-revision"))
    with pytest.raises(bindings.DuplicateTechnology):
        find_binding("WBA", tmp_path)


def test_the_conflict_does_not_depend_on_filesystem_enumeration_order(tmp_path,
                                                                     monkeypatch):
    """Sorting made the old outcome deterministic and still silent.

    Both enumeration orders are forced and the reported conflict is identical,
    filenames included, so the same checkout cannot resolve differently on two
    machines - and cannot resolve at all until it is fixed.
    """
    _two_claimants(tmp_path)
    real_glob = Path.glob
    seen = []
    for reverse in (False, True):
        def fake_glob(self, pattern, _reverse=reverse):
            return iter(sorted(real_glob(self, pattern), reverse=_reverse))
        monkeypatch.setattr(Path, "glob", fake_glob)
        seen.append(bindings.binding_conflicts(tmp_path))
        with pytest.raises(bindings.DuplicateTechnology):
            available_bindings(tmp_path)
        monkeypatch.undo()
    assert seen[0] == seen[1] == {"WBA": ("aaa-shadow.yaml", "zzz-real.yaml")}


def test_three_files_claiming_one_id_name_all_three(tmp_path):
    _two_claimants(tmp_path, names=("one", "two", "three"))
    with pytest.raises(bindings.DuplicateTechnology) as exc:
        available_bindings(tmp_path)
    for name in ("one.yaml", "two.yaml", "three.yaml"):
        assert name in str(exc.value)


def test_a_claim_in_a_file_that_does_not_validate_still_conflicts(tmp_path):
    """Skipping a bad file that claims a taken id is not skipping, it is choosing.

    A valid file is still skipped when it is merely invalid - that is unchanged -
    but the id it claimed has to be resolved by a person, not by load order.
    """
    (tmp_path / "real.yaml").write_text(MINIMAL, encoding="utf-8")
    (tmp_path / "broken.yaml").write_text(
        "technology: WBA\ndiagram_types:\n  Overview:\n    grammar: no-such-grammar\n",
        encoding="utf-8")
    assert bindings.binding_conflicts(tmp_path) == {
        "WBA": ("broken.yaml", "real.yaml")}
    with pytest.raises(bindings.DuplicateTechnology):
        available_bindings(tmp_path)


def test_an_invalid_file_claiming_an_unused_id_is_still_only_skipped(tmp_path):
    """The old promise survives: one bad file does not make the catalog unreadable."""
    (tmp_path / "real.yaml").write_text(MINIMAL, encoding="utf-8")
    (tmp_path / "broken.yaml").write_text(
        "technology: WestbrookBankArchitecture\ndiagram_types:\n  Overview:\n"
        "    grammar: no-such-grammar\n", encoding="utf-8")
    assert available_bindings(tmp_path) == {"WBA": "real.yaml"}
    assert bindings.binding_conflicts(tmp_path) == {}


def test_a_shadowed_parent_cannot_be_inherited_from(tmp_path):
    """Inheritance raises the stakes: a shadowed base is inherited by its children."""
    _two_claimants(tmp_path)
    (tmp_path / "child.yaml").write_text(
        MINIMAL.replace("technology: WBA",
                        "technology: WestbrookBankArchitecture\nextends: WBA"),
        encoding="utf-8")
    with pytest.raises(bindings.DuplicateTechnology):
        load_binding(tmp_path / "child.yaml")


def test_the_shipped_catalog_declares_each_technology_exactly_once():
    """The acceptance the shipped tree has to keep meeting."""
    assert bindings.binding_conflicts() == {}
    declared = bindings.declared_technologies()
    assert declared, "the shipped bindings directory should not be empty"
    assert all(len(files) == 1 for files in declared.values())
    assert set(declared) == set(available_bindings())


# ---------------------------------------------------------------------------
# The substrate: what a child takes from the notation underneath it
# ---------------------------------------------------------------------------
# A parent's diagram type is the SUBSTRATE for the child diagram types drawn on
# it, named by `base`. Two properties are asserted separately here because they
# fail in opposite directions:
#
#   * a child's own statements survive - inheritance must not flatten the
#     structure an MDG exists to add;
#   * a child's silences are filled from the substrate's measurements rather
#     than from the engine's defaults - which is the whole point.
#
# The parent's diagram types do NOT join the child's catalog. That is a change
# from a catalog union, and the tests for it name the two failures the union
# causes once the parent is a base notation.
_SUBSTRATE_PARENT = """
technology: WBA
stereotype_prefix: WBA_
diagram_types:
  Logical:
    base: Logical
    grammar: graph
    title: frame-header
    sizing:
      default: {w: 90, h: 70}
      Package: {w: 148, h: 90}
    spacing: {item_gap_x: 56, item_gap_y: 50}
    routing: {default: Direct}
    channels:
      fill: ~
      free: [fill, border]
  Statechart:
    base: Statechart
    grammar: graph
    title: frame-header
    sizing:
      default: {w: 120, h: 60}
    routing: {default: Direct}
    channels:
      fill: ~
      free: [fill, border]
"""

_SUBSTRATE_CHILD = """
technology: WBA-Overlay
extends: WBA
stereotype_prefix: WBO_
diagram_types:
  Overview:
    base: Logical
    grammar: layered-bands
    title: drawn
    sizing:
      default: {w: 100, h: 70}
    spacing: {item_gap_x: 75}
    routing: {default: OrthogonalSquare}
    channels:
      fill: Layer
      free: [border]
"""


def _substrate_pair(tmp_path, child: str = _SUBSTRATE_CHILD) -> Binding:
    (tmp_path / "parent.yaml").write_text(_SUBSTRATE_PARENT, encoding="utf-8")
    (tmp_path / "child.yaml").write_text(child, encoding="utf-8")
    return load_binding(tmp_path / "child.yaml")


def test_a_child_diagram_type_takes_the_substrate_slots_it_does_not_state(tmp_path):
    """The gap the child is silent about comes from the type it is drawn on.

    `item_gap_y` is the slot: unstated by the child, measured by the parent. The
    child's own `item_gap_x` and its own `default` size are untouched, which is
    the half that has to hold for the other half to be safe.
    """
    dt = _substrate_pair(tmp_path).diagram_type("Overview")
    assert dt.substrate == "WBA::Logical" and dt.inherits
    # Stated by the child: the child's.
    assert dt.own_spacing == {"item_gap_x": 75}
    assert dt.spacing["item_gap_x"] == 75
    assert dt.size_for() == (100, 70)
    assert dt.grammar == "layered-bands"
    assert dt.title == "drawn"
    assert dt.routing["default"] == "OrthogonalSquare"
    # Unstated by the child: the substrate's, and reported as inherited.
    assert dt.spacing["item_gap_y"] == 50
    assert dt.inherited_spacing() == {"item_gap_y": 50}
    assert dt.size_for("Package") == (148, 90)
    assert dt.inherited_sizing() == {"Package": {"w": 148, "h": 90}}
    # And the spec the engine takes carries the inherited value, which is where
    # the engine's own default used to answer.
    assert dt.spec()["item_gap_y"] == 50 != DEFAULT_SPEC["item_gap_y"]


def test_a_child_does_not_acquire_the_substrates_diagram_type_catalog(tmp_path):
    """The parent's other diagram types are NOT the child's.

    Two failures if they were, and both are silent. A technology's diagram types
    are declared by its MDG and checked against the MDG data, so a child holding
    `Statechart` claims one EA never declared for it - and `mdg_diagram_type`
    would build a qualified key no diagram can carry. Worse, `resolve_diagram`
    matches `Diagram_Type` against bound diagram type NAMES, so every binding
    drawn on a base would claim that base's own name and a plain diagram of it
    would resolve as ambiguous across all of them.
    """
    child = _substrate_pair(tmp_path)
    assert set(child.diagram_types) == {"Overview"}
    assert child.diagram_type_for_mdgdgm("WBA-Overlay::Statechart") is None
    resolution = resolve_diagram(["WBA", "WBA-Overlay"],
                                 diagram_type="Statechart",
                                 bindings=[child, find_binding(
                                     "WBA", directory=tmp_path)])
    assert resolution.resolved and not resolution.is_ambiguous
    assert resolution.technology == "WBA"


def test_the_substrate_does_not_flatten_a_grammar_the_child_states(tmp_path):
    """An MDG adding structure its base notation lacks is what an MDG is FOR.

    The parent is a `graph` and the child composes `layered-bands` on top of it.
    A merge that let the parent's classification win would silently turn every
    composed view back into something EA lays out.
    """
    parent = _SUBSTRATE_PARENT
    (tmp_path / "parent.yaml").write_text(parent, encoding="utf-8")
    (tmp_path / "child.yaml").write_text(_SUBSTRATE_CHILD, encoding="utf-8")
    child = load_binding(tmp_path / "child.yaml")
    assert load_binding(tmp_path / "parent.yaml").diagram_type(
        "Logical").grammar == "graph"
    assert child.diagram_type("Overview").grammar == "layered-bands"
    assert child.diagram_type("Overview").geometry_is_composed is True


def test_a_base_the_parent_does_not_declare_leaves_no_substrate(tmp_path):
    """Not an error, and not silently patched either.

    A base notation may decline a diagram type for want of a figure it can
    support, so a child drawn on one has nothing to inherit - and inventing a
    fallback here would state a value nobody measured. The answer is that the
    child keeps its own values and says it found no substrate.
    """
    child = _substrate_pair(
        tmp_path, _SUBSTRATE_CHILD.replace("base: Logical", "base: Sequence"))
    dt = child.diagram_type("Overview")
    assert dt.substrate == "" and not dt.inherits
    assert dt.spacing == dt.own_spacing == {"item_gap_x": 75}
    assert dt.inherited_sizing() == {} and dt.inherited_spacing() == {}


def test_a_child_that_states_no_base_falls_back_to_the_same_name(tmp_path):
    """How a house binding refining its own technology still works.

    `base` names the substrate, and a child restating one of its parent's own
    diagram types has no base to name - it is the same diagram type, refined. So
    the name answers when `base` does not, and the refinement keeps inheriting
    the parent's measurements for whatever it does not restate.
    """
    child = _substrate_pair(tmp_path, """
technology: WBA-House
extends: WBA
stereotype_prefix: WBA_
diagram_types:
  Logical:
    grammar: graph
    title: drawn
    sizing:
      default: {w: 200, h: 80}
    routing: {default: Direct}
    channels:
      fill: ~
      free: [fill]
""")
    dt = child.diagram_type("Logical")
    assert dt.substrate == "WBA::Logical"
    assert dt.size_for() == (200, 80)
    assert dt.size_for("Package") == (148, 90)
    assert dt.spacing == {"item_gap_x": 56, "item_gap_y": 50}


# ---------------------------------------------------------------------------
# Inheriting `sizing.default`, and the line between inheriting and inventing
# ---------------------------------------------------------------------------
# `sizing.default` is mandatory in the RESOLVED diagram type and optional in the
# document. It used to be mandatory in the document, checked before `_merge` ran,
# so no diagram type could inherit the one figure every diagram of it needs -
# and notations with a measured base notation underneath them went unbound for
# that reason alone rather than for want of evidence.
#
# THE RISK THE RELAXATION CARRIES IS THE THING THESE TESTS ARE ABOUT. A
# mandatory default is the one thing standing between an unmeasured technology
# and a borrowed figure, so the tests below assert both halves of the trade:
# inheriting works and is REPORTED as inheriting, and a chain that supplies
# nothing is still refused - with a message that offers inheriting and fixing
# `base:` as the only two ways out and rules out copying a number in.
#
# `_SUBSTRATE_CHILD` with its `sizing` block removed is the fixture: a diagram
# type that states everything only it can know - its grammar, its title, its
# routing, the channel its own shape script claims - and stays silent about the
# one slot that is a measurement of the canvas underneath it.
_SILENT_SIZING_CHILD = """
technology: WBA-Overlay
extends: WBA
stereotype_prefix: WBO_
diagram_types:
  Overview:
    base: Logical
    grammar: layered-bands
    title: drawn
    spacing: {item_gap_x: 75}
    routing: {default: OrthogonalSquare}
    channels:
      fill: Layer
      free: [border]
"""


def test_a_diagram_type_that_omits_sizing_inherits_the_substrates_default(
        tmp_path):
    """The blocker this change removes, at its smallest.

    Nothing about the child's own statements changes; the one slot it is silent
    about now resolves to the figure the substrate measured instead of refusing
    the document. `size_for()` with no concept is the call every composer makes,
    so this is the figure a diagram of this type is actually laid out with.
    """
    dt = _substrate_pair(tmp_path, _SILENT_SIZING_CHILD).diagram_type("Overview")
    assert dt.size_for() == (90, 70)
    assert dt.substrate == "WBA::Logical" and dt.inherits
    assert dt.spec()["item_width"] == 90 and dt.spec()["item_height"] == 70
    # The child's own statements are untouched by the inheritance.
    assert dt.grammar == "layered-bands" and dt.title == "drawn"
    assert dt.routing["default"] == "OrthogonalSquare"
    assert dt.spacing["item_gap_x"] == 75


def test_an_explicitly_empty_sizing_block_means_the_same_as_an_omitted_one(
        tmp_path):
    """`sizing: {}` and no `sizing` at all are one case, as for `spacing`.

    An author who writes the key and leaves it empty has said what an author who
    left the key out said. Treating them differently would make the schema turn
    on a formatting choice.
    """
    for block in ("    sizing: {}\n", "    sizing: ~\n"):
        child = _SILENT_SIZING_CHILD.replace("    spacing:", block + "    spacing:")
        dt = _substrate_pair(tmp_path, child).diagram_type("Overview")
        assert dt.size_for() == (90, 70), block
        assert dt.own_sizing == {}, block


def test_a_diagram_type_that_states_a_default_keeps_it_over_the_substrates(
        tmp_path):
    """A statement still wins, which is what makes the silence meaningful.

    Asserted in both directions from one parent: the child that states 100x70
    keeps it although the substrate measures 90x70, and the child that states
    nothing takes the substrate's. If the stating child lost, the relaxation
    would have flattened every measured MDG size into its base canvas's.
    """
    stating = _substrate_pair(tmp_path).diagram_type("Overview")
    silent = _substrate_pair(tmp_path, _SILENT_SIZING_CHILD).diagram_type(
        "Overview")
    assert stating.size_for() == (100, 70)
    assert silent.size_for() == (90, 70)
    assert stating.substrate == silent.substrate == "WBA::Logical"


def test_a_default_may_be_inherited_while_per_concept_sizes_are_stated(
        tmp_path):
    """The half-stated case: `sizing` present, `default` absent.

    A notation can have enough diagrams to measure one concept and not enough to
    measure the canvas it sits on - Data Modeling's table is the real example,
    where the box size IS the column list it prints and there is no convention
    size to find. Per-concept refinement and an inherited fallback have to be
    able to coexist, or such a notation is back to inventing a default.
    """
    child = _SILENT_SIZING_CHILD.replace(
        "    spacing:", "    sizing:\n      Table: {w: 170, h: 120}\n    spacing:")
    dt = _substrate_pair(tmp_path, child).diagram_type("Overview")
    assert dt.size_for("Table") == (170, 120)
    assert dt.size_for() == (90, 70)
    assert dt.own_sizing == {"Table": {"w": 170, "h": 120}}
    assert dt.default_size_is_inherited


def test_an_inherited_default_is_distinguishable_from_a_stated_one(tmp_path):
    """The provenance question, and the reason the omission is allowed at all.

    Inheriting and inventing produce the same kind of value - a pair of numbers -
    and nothing downstream can tell a measured figure from a typed-in one by
    looking at it. So the binding has to carry which it is. A diagram type that
    inherited its default says so forever after, and names the diagram type the
    figure was measured on; one that states its own names itself.
    """
    silent = _substrate_pair(tmp_path, _SILENT_SIZING_CHILD).diagram_type(
        "Overview")
    stating = _substrate_pair(tmp_path).diagram_type("Overview")
    assert silent.default_size_is_inherited is True
    assert silent.default_size_provenance == "WBA::Logical"
    assert stating.default_size_is_inherited is False
    assert stating.default_size_provenance == "WBA-Overlay::Overview"
    # Never empty on either side: a diagram type that neither states a default
    # nor inherits one does not load, so this always names a real measurement.
    for dt in (silent, stating):
        assert "::" in dt.default_size_provenance


def test_a_root_binding_has_no_substrate_so_it_states_its_own_default(tmp_path):
    """The base notation cannot inherit, and must not appear to.

    `own_sizing` defaults to the resolved values for a binding with no parent, so
    the root of the tree reports its default as its own - which it is, and which
    is what keeps `default_size_is_inherited` a statement about provenance rather
    than about whether a `substrate` happened to be found.
    """
    (tmp_path / "parent.yaml").write_text(_SUBSTRATE_PARENT, encoding="utf-8")
    root = load_binding(tmp_path / "parent.yaml").diagram_type("Logical")
    assert not root.inherits and root.substrate == ""
    assert root.default_size_is_inherited is False
    assert root.default_size_provenance == "WBA::Logical"


#: Each entry is a diagram type nothing in the chain supplies a default for, and
#: the phrase whose presence proves the message named the substrate it looked at.
#: That phrase is the whole difference between an actionable failure and
#: `sizing.default: required`, which tells an author who was trying to inherit
#: nothing they did not already know.
_NO_DEFAULT_CASES = {
    "no extends at all": (
        "technology: Orphan\ndiagram_types:\n  X:\n    grammar: graph\n"
        "    title: drawn\n    routing: {default: Direct}\n"
        "    channels: {fill: ~}\n",
        "declares no `extends`"),
    "base the parent does not declare": (
        "technology: WrongBase\nextends: WBA\ndiagram_types:\n  X:\n"
        "    grammar: graph\n    title: drawn\n    base: Sequence\n"
        "    routing: {default: Direct}\n    channels: {fill: ~}\n",
        "'Sequence'"),
    "no base and no diagram type of the same name": (
        "technology: NoBase\nextends: WBA\ndiagram_types:\n  X:\n"
        "    grammar: graph\n    title: drawn\n"
        "    routing: {default: Direct}\n    channels: {fill: ~}\n",
        "WBA::X"),
}


@pytest.mark.parametrize("case", sorted(_NO_DEFAULT_CASES))
def test_a_default_nothing_in_the_chain_supplies_is_still_refused(case,
                                                                  tmp_path):
    """The refusal that has to survive the relaxation.

    Three ways a chain can supply nothing, and all three are refused. The
    message is asserted on as hard as the refusal, because a message that says
    only `required` pushes the author who was trying to inherit towards the one
    thing this schema must not make easy: typing in a figure from a notation
    somebody else measured. So it must name the diagram type, name the substrate
    it looked at - which is also how a `base` pointing somewhere unreachable is
    diagnosed rather than guessed at - and offer inheriting and fixing `base:`
    as the two ways out.
    """
    document, names_substrate = _NO_DEFAULT_CASES[case]
    (tmp_path / "parent.yaml").write_text(_SUBSTRATE_PARENT, encoding="utf-8")
    (tmp_path / "child.yaml").write_text(document, encoding="utf-8")
    with pytest.raises(BindingError) as exc:
        load_binding(tmp_path / "child.yaml")
    message = str(exc.value)
    assert "child.yaml.diagram_types.X.sizing.default" in message
    assert names_substrate in message
    assert "base:" in message and "MEASURED" in message
    assert "Do not copy a figure in from another notation" in message


def test_the_resolved_default_is_checked_after_the_merge_and_not_before(
        tmp_path):
    """WHERE the check happens, pinned by the one document that shows it.

    The same child text is refused on its own and accepted with the parent
    underneath it. Nothing about the document changed between the two loads, so
    a validator that ran on the document could not have told them apart - which
    is why the question moved to `Binding.__init__`, after `_merge`. Move it back
    and this test fails on the second load rather than the first.
    """
    standalone = _SILENT_SIZING_CHILD.replace("extends: WBA\n", "")
    with pytest.raises(BindingError, match=r"sizing\.default"):
        load_binding_text(standalone, "lonely.yaml")
    assert _substrate_pair(tmp_path, _SILENT_SIZING_CHILD).diagram_type(
        "Overview").size_for() == (90, 70)


def test_inheriting_a_default_works_through_a_chain_of_its_own_bindings(
        tmp_path):
    """Depth is not assumed to work, and is not required to.

    A grandchild inherits through two levels only because each level is fully
    resolved before it is used as a substrate: the middle binding's `Overview`
    already carries the root's default by the time the grandchild is placed on
    it. What does NOT work is a `base` naming a diagram type only the GRANDparent
    declares, because `base` is looked up in the IMMEDIATE parent's catalog - a
    separate defect, deliberately not fixed here. Both halves are asserted so
    that this change cannot come to depend on the broken one: the reachable case
    inherits, and the unreachable one is refused by name rather than resolving to
    something invented.
    """
    (tmp_path / "parent.yaml").write_text(_SUBSTRATE_PARENT, encoding="utf-8")
    (tmp_path / "child.yaml").write_text(_SILENT_SIZING_CHILD, encoding="utf-8")
    (tmp_path / "grandchild.yaml").write_text("""
technology: WBA-Deep
extends: WBA-Overlay
diagram_types:
  Overview:
    grammar: layered-bands
    title: drawn
    routing: {default: Direct}
    channels: {fill: ~}
""", encoding="utf-8")
    dt = load_binding(tmp_path / "grandchild.yaml").diagram_type("Overview")
    assert dt.substrate == "WBA-Overlay::Overview"
    assert dt.size_for() == (90, 70)
    assert dt.default_size_provenance == "WBA-Overlay::Overview"
    # And the grandparent's own diagram type is NOT reachable through `base`.
    (tmp_path / "reaching.yaml").write_text("""
technology: WBA-Reaching
extends: WBA-Overlay
diagram_types:
  Overview:
    base: Logical
    grammar: layered-bands
    title: drawn
    routing: {default: Direct}
    channels: {fill: ~}
""", encoding="utf-8")
    with pytest.raises(BindingError) as exc:
        load_binding(tmp_path / "reaching.yaml")
    assert "'Logical'" in str(exc.value)
    assert "WBA-Overlay declares no diagram type of that name" in str(exc.value)


def test_a_resolution_says_when_the_default_box_size_is_inherited(tmp_path):
    """A binding that inherits says so in what it reports.

    `Resolution.reason` is what a consumer prints, and the figure it is about to
    lay out with is not this technology's measurement. Nothing downstream could
    tell from the number, so the resolution names where the number came from. The
    stating binding's resolution stays silent about provenance, which is what
    makes the sentence mean something when it does appear.
    """
    installed = ["WBA", "WBA-Overlay"]
    # BOTH resolution paths, because they build their reasons separately and a
    # note on one of them would leave the majority path - `Diagram_Type`, which
    # answers for 53% of real diagrams - reporting a borrowed figure as measured.
    for kwargs in ({"style_ex": "MDGDgm=WBA-Overlay::Overview;"},
                   {"diagram_type": "Overview"}):
        silent = resolve_diagram(
            installed,
            bindings=[_substrate_pair(tmp_path, _SILENT_SIZING_CHILD)],
            **kwargs)
        assert silent.resolved, kwargs
        assert "inherited from WBA::Logical" in silent.reason, kwargs
        assert "not measured by WBA-Overlay" in silent.reason, kwargs
        stating = resolve_diagram(
            installed, bindings=[_substrate_pair(tmp_path)], **kwargs)
        assert stating.resolved and "inherited" not in stating.reason, kwargs


# ---------------------------------------------------------------------------
# The shipped tree: one base notation, everything else on top of it
# ---------------------------------------------------------------------------
# DERIVED FROM `available_bindings()`, every one of them. Tests in this file have
# broken twice by pinning a fixed set of bindings by hand, so nothing below names
# a technology: the catalog on disk is read and the relationships are checked
# against each other. Adding a binding cannot break these, and a binding that
# forgets to say what it is built on will.
def _shipped_bindings() -> dict[str, Binding]:
    return {technology: find_binding(technology)
            for technology in available_bindings()}


def _root_of(shipped: dict[str, Binding]) -> str:
    roots = sorted(t for t, b in shipped.items() if b.extends is None)
    assert len(roots) == 1, f"expected one base notation, found {roots}"
    return roots[0]


def test_exactly_one_shipped_binding_is_the_root_and_every_other_is_built_on_it():
    """EA is a UML tool: every MDG technology is a stereotype layer on UML.

    Every shipped binding used to declare `extends: ~` or nothing at all, which
    made the corpus a flat set of peer notations and meant an unstated slot fell
    back to an engine default with the measured value for the very diagram type
    it is drawn on sitting unread in another file.
    """
    shipped = _shipped_bindings()
    root = _root_of(shipped)
    for technology, binding in shipped.items():
        if technology == root:
            continue
        assert binding.extends == root, (
            f"{technology} declares extends={binding.extends!r}; every MDG "
            f"technology is a stereotype layer on {root}")


def test_the_parent_derived_from_base_is_the_one_each_binding_declares():
    """`extends` is hand-declared and `base` names the substrate. Both, on purpose.

    Two statements of one relationship can disagree, so the derivation is run
    here and compared rather than replacing the declaration - which also catches
    the failure a hand-declared key really has, an author forgetting it. The
    loader does NOT derive, and §5.6 of `references/bindings.md` says why: `base`
    names a diagram type rather than a technology, so deriving needs a directory
    search whose answer changes with which files are present, and one binding's
    diagram types can sit on several bases, so there is no single value to derive.
    """
    shipped = _shipped_bindings()
    for technology, binding in shipped.items():
        bases = {dt.base for dt in binding.diagram_types.values() if dt.base}
        assert bases, f"{technology} states no base for any diagram type"
        candidates = sorted(
            other for other, candidate in shipped.items()
            if other != technology and bases <= set(candidate.diagram_types))
        assert len(candidates) <= 1, (
            f"{technology}'s bases {sorted(bases)} are all declared by "
            f"{candidates}, so `base` cannot decide which is the parent")
        derived = candidates[0] if candidates else None
        assert binding.extends == derived, (
            f"{technology} declares extends={binding.extends!r} but its `base` "
            f"values derive {derived!r}")


def test_every_base_a_shipped_binding_states_is_bound_by_the_base_notation():
    """The substrate has to exist, or the inheritance silently does nothing.

    This is the test that would have caught the gap this restructuring closed.
    The MDG bindings sit on three different EA base diagram types and the base
    notation bound only one of them, so two of the four technologies declared a
    parent and inherited nothing at all from it.
    """
    shipped = _shipped_bindings()
    root = _root_of(shipped)
    bases = set()
    for technology, binding in shipped.items():
        if technology == root:
            continue
        for name, dt in binding.diagram_types.items():
            assert dt.base in shipped[root].diagram_types, (
                f"{technology}::{name} is drawn on {dt.base!r}, which {root} "
                f"does not bind, so it inherits nothing")
            assert dt.substrate == f"{root}::{dt.base}", f"{technology}::{name}"
            assert dt.inherits, f"{technology}::{name}"
            bases.add(dt.base)
    assert len(bases) > 1, (
        f"every shipped binding sits on {bases}, so nothing here proves the "
        f"base notation has to cover more than one base type")


def test_a_plain_diagram_of_any_base_in_use_resolves_to_the_base_notation():
    """Binding the bases fixes resolution as well as inheritance.

    A diagram identified only by its `Diagram_Type` used to fall through to the
    weak `base-type` path for a base the base notation did not bind, and answer
    with whichever MDG happened to sit on it: plain `Custom` diagrams - 143 of
    them in the example model - resolved as this repository's requirement
    diagrams, and plain `Analysis` diagrams came back ambiguous across three
    process types. With every base in use bound, the `diagram-type` path answers
    with the base notation itself, which is what such a diagram actually is.
    """
    shipped = _shipped_bindings()
    root = _root_of(shipped)
    bases = sorted({dt.base for technology, binding in shipped.items()
                    if technology != root
                    for dt in binding.diagram_types.values()})
    for base in bases:
        resolution = resolve_diagram(sorted(shipped), style_ex="MDGDgm=;",
                                     diagram_type=base,
                                     bindings=list(shipped.values()))
        assert resolution.resolved, base
        assert not resolution.is_ambiguous, (base, resolution.candidates)
        assert resolution.technology == root, (base, resolution.technology)
        assert resolution.path == "diagram-type", (base, resolution.path)


def _document(technology: str) -> dict:
    """A binding's own document, unresolved - what the file itself states."""
    import yaml
    path = _BINDINGS_DIR / available_bindings()[technology]
    return yaml.safe_load(path.read_text(encoding="utf-8"))


@pytest.mark.parametrize("technology", sorted(available_bindings()))
def test_every_shipped_binding_still_resolves_what_its_own_document_states(
        technology):
    """Inheritance did not flatten a single statement any binding makes.

    Read from each document rather than from a copy of the expected values, and
    asserted for every slot the schema has: prefix, grammar, title, route, every
    size and every gap. A merge that let a parent win anywhere would show up here
    as the parent's value under the child's key.
    """
    document = _document(technology)
    binding = find_binding(technology)
    if "stereotype_prefix" in document:
        assert binding.stereotype_prefix == (document["stereotype_prefix"] or "")
    for name, body in document["diagram_types"].items():
        dt = binding.diagram_type(name)
        where = f"{technology}::{name}"
        assert dt.grammar == body["grammar"], where
        assert dt.title == body["title"], where
        # The second prefix scope, read from the document the same way: a type
        # that states one keeps it, and one that stays silent resolves to the
        # technology's and never to the substrate's.
        if "stereotype_prefix" in body:
            assert dt.own_stereotype_prefix == (
                body["stereotype_prefix"] or ""), where
            assert dt.stereotype_prefix == dt.own_stereotype_prefix, where
        else:
            assert dt.own_stereotype_prefix is None, where
            assert dt.stereotype_prefix == binding.stereotype_prefix, where
        assert dt.routing["default"] == body["routing"]["default"], where
        stated_sizes = {concept: {"w": size["w"], "h": size["h"]}
                        for concept, size in body["sizing"].items()}
        assert dt.own_sizing == stated_sizes, where
        assert dt.own_spacing == dict(body.get("spacing") or {}), where
        for concept, size in stated_sizes.items():
            assert dt.sizing[concept] == size, f"{where}.{concept}"
        for key, value in (body.get("spacing") or {}).items():
            assert dt.spacing[key] == value, f"{where}.{key}"
        # Everything else is exactly the substrate's, and nothing is invented.
        if dt.inherits:
            substrate = find_binding(binding.extends).diagram_type(dt.base)
            assert dt.sizing == {**substrate.sizing, **stated_sizes}, where
            assert dt.spacing == {**substrate.spacing, **dt.own_spacing}, where
        else:
            assert dt.sizing == stated_sizes and dt.spacing == dt.own_spacing


def test_every_shipped_binding_states_its_own_prefix_rather_than_inheriting_one():
    """The live trap, as a test.

    A child that OMITS `stereotype_prefix` inherits the parent's, and the base
    notation's is a measured `""` - right for a family drawn in plain UML, WRONG
    for one whose MDG stereotypes its elements. So every shipped binding states
    its own, and the loader's presence check is what keeps a declared `""` from
    reading as an absence. The last assertion is what makes the rest mean
    something: if no shipped binding had a real prefix, a loader that dropped the
    distinction entirely would pass every line above.
    """
    with_prefix = {}
    for technology in available_bindings():
        document = _document(technology)
        assert "stereotype_prefix" in document, (
            f"{technology} does not state a prefix, so it inherits one")
        binding = find_binding(technology)
        assert binding.stereotype_prefix == (document["stereotype_prefix"] or "")
        if binding.stereotype_prefix:
            with_prefix[technology] = binding.stereotype_prefix
    assert with_prefix, "no shipped binding has a prefix, so nothing is proved"
    for technology, prefix in with_prefix.items():
        binding = find_binding(technology)
        assert binding.stereotype_for("Thing") == f"{prefix}Thing"
        assert binding.concept_for(f"{prefix}Thing") == "Thing"


def test_every_shipped_prefix_round_trips_at_the_scope_that_declares_it():
    """The round trip, over both scopes, derived from the shipped documents.

    One assertion per prefix actually in force, whichever scope stated it, so a
    binding that grows a per-diagram-type prefix is covered the day it does
    without an edit here. The two counters at the end are what stop this passing
    vacuously: `StrategyMap` and `TOGAF Diagrams` supply the diagram-type scope
    and `ArchiMate3` and `ERD_dp` the technology scope, and if either group
    disappeared the remaining lines would still all pass.
    """
    at_type, at_technology = 0, 0
    for technology in available_bindings():
        binding = find_binding(technology)
        for name, dt in binding.diagram_types.items():
            where = f"{technology}::{name}"
            prefix = dt.stereotype_prefix
            assert dt.stereotype_for("Thing") == f"{prefix}Thing", where
            assert dt.concept_for(f"{prefix}Thing") == "Thing", where
            assert binding.stereotype_for("Thing", name) == f"{prefix}Thing"
            assert binding.concept_for(f"{prefix}Thing", name) == "Thing"
            if not prefix:
                continue
            if dt.stereotype_prefix_is_inherited:
                at_technology += 1
                assert prefix == binding.stereotype_prefix, where
            else:
                at_type += 1
                # The point of the second scope: the technology's answer differs.
                assert prefix != binding.stereotype_prefix, where
    assert at_type, "no shipped diagram type states its own prefix"
    assert at_technology, "no shipped diagram type inherits a real prefix"


def test_no_shipped_sizing_key_carries_the_prefix_that_is_in_force_for_it():
    """`sizing` KEYS ARE CONCEPT NAMES, checked against the resolved prefix.

    This is the mistake the second scope made possible and then had to close. When
    `StrategyMap` stated `""` its keys were spelled `VC_PrimaryActivity`, which was
    correct under an empty prefix and becomes a doubled prefix the moment the
    diagram type declares `VC_`. Asserted over every shipped key rather than that
    one, because the same trap is waiting in any binding that gains a prefix.
    """
    for technology in available_bindings():
        binding = find_binding(technology)
        for name, dt in binding.diagram_types.items():
            prefix = dt.stereotype_prefix
            if not prefix:
                continue
            for concept in dt.own_sizing:
                assert not concept.startswith(prefix), (
                    f"{technology}::{name} sizes {concept!r}; the key is a "
                    f"concept name and {prefix!r} is added by stereotype_for")


def test_an_unstated_slot_resolves_to_a_measured_value_not_an_engine_default():
    """THE POINT OF THE WHOLE ARRANGEMENT, as a before and after.

    `load_binding_text` takes no directory and so cannot follow `extends`, which
    makes it exactly the "before": the same shipped document, unresolved. For
    every slot a shipped binding leaves unstated that its substrate measures,
    both states are asserted - absent before, so the engine's own default answers
    at compose time, and the measured value after.

    Derived, not pinned: the slots are whatever the shipped files leave unstated.
    The last assertion is the one that would fail if inheritance stopped doing
    anything at all, which a test of the resolved value alone would not notice.
    """
    proved = []
    for technology, filename in available_bindings().items():
        binding = find_binding(technology)
        if binding.extends is None:
            continue
        before = load_binding_text(
            (_BINDINGS_DIR / filename).read_text(encoding="utf-8"),
            source=filename)
        for name, dt in binding.diagram_types.items():
            was = before.diagram_type(name)
            assert was.spacing == dt.own_spacing, f"{technology}::{name}"
            for key, value in dt.inherited_spacing().items():
                # Before: the key is not in the spec at all, so the engine
                # supplies it from `DEFAULT_SPEC` and the binding has no say.
                assert key not in was.spec()
                # After: the measured value for the diagram type this one is
                # drawn on, and different from what the engine would have said.
                assert dt.spec()[key] == value
                assert value != DEFAULT_SPEC[key], (technology, name, key)
                proved.append((technology, name, key,
                               DEFAULT_SPEC[key], value))
    assert proved, (
        "no shipped binding inherits a gap, so the substrate changes nothing")


# ---------------------------------------------------------------------------
# Discovery
# ---------------------------------------------------------------------------
def test_a_binding_is_found_by_its_declared_id_not_its_filename(tmp_path):
    """The id is authoritative.

    Resolving by filename would let a renamed or re-slugged file bind the wrong
    technology, and composing against the wrong binding is worse than composing
    against none.
    """
    (tmp_path / "something-else.yaml").write_text(
        MINIMAL.replace("technology: WBA", "technology: Odd.Id/2"),
        encoding="utf-8")
    found = find_binding("Odd.Id/2", directory=tmp_path)
    assert found is not None and found.technology == "Odd.Id/2"


def test_an_unbound_technology_returns_none_rather_than_raising(tmp_path):
    """Most repositories use technologies nobody has bound. A caller should
    say so and fall back, not crash."""
    assert find_binding("Nothing", directory=tmp_path) is None
    assert find_binding("Nothing", directory=tmp_path / "absent") is None


def test_one_invalid_file_does_not_hide_the_valid_ones(tmp_path):
    (tmp_path / "good.yaml").write_text(MINIMAL, encoding="utf-8")
    (tmp_path / "broken.yaml").write_text("technology: Broken\n",
                                          encoding="utf-8")
    assert available_bindings(directory=tmp_path) == {"WBA": "good.yaml"}


def test_malformed_yaml_is_reported_as_such():
    with pytest.raises(BindingError, match="not valid YAML"):
        load_binding_text("technology: [unclosed\n")


def test_a_binding_cannot_carry_executable_content():
    """`safe_load`, always. A python-object tag is refused by the parser rather
    than by a check here that someone could forget to run."""
    with pytest.raises(BindingError, match="not valid YAML"):
        load_binding_text(
            "technology: !!python/object/apply:os.system ['echo hi']\n")


def test_a_document_that_is_not_a_mapping_is_refused():
    with pytest.raises(BindingError, match="expected a mapping"):
        load_binding_text("- just\n- a\n- list\n")


def test_reading_a_binding_that_is_not_there_names_the_path(tmp_path):
    with pytest.raises(BindingError, match="cannot read binding"):
        load_binding(tmp_path / "absent.yaml")


# ---------------------------------------------------------------------------
# The shipped pilots
# ---------------------------------------------------------------------------
def test_both_pilot_bindings_are_present_and_valid():
    shipped = available_bindings()
    assert shipped["ArchiMate3"] == "archimate3.yaml"
    assert shipped["BPMN2.0"] == "bpmn2.0.yaml"


def test_every_shipped_binding_file_validates():
    files = sorted(_BINDINGS_DIR.glob("*.yaml"))
    assert files, "no bindings shipped"
    for path in files:
        load_binding(path)  # raises with the offending key if not


@pytest.mark.parametrize("technology,diagram_type", [
    ("ArchiMate3", "Application"),
    ("ArchiMate3", "Business"),
    ("ArchiMate3", "Technology"),
    ("ArchiMate3", "Motivation"),
    ("ArchiMate3", "Implementation"),
    ("BPMN2.0", "Business Process"),
    ("BPMN2.0", "Collaboration"),
    ("BPMN2.0", "Choreography"),
])
def test_the_technology_and_diagram_type_names_ea_actually_writes(
        technology, diagram_type):
    """Read from the MDG technology EA had loaded, and pinned.

    `BPMN2.0` is not `BPMN2`, and `Business Process` has a space in it. Both
    would have been guessed wrong, and a binding keyed on a guessed id resolves
    to nothing without complaining - so an `MDGDgm` lookup is the assertion,
    not a string comparison against the file.
    """
    binding = find_binding(technology)
    assert binding is not None
    resolved = binding.diagram_type_for_mdgdgm(
        f"{technology}::{diagram_type}")
    assert resolved is not None, (
        f"{technology}::{diagram_type} does not resolve")
    assert resolved.mdg_diagram_type == f"{technology}::{diagram_type}"


def test_the_archimate_stereotype_prefix_is_applied():
    """EA 17.1's built-in ArchiMate3 MDG prefixes its stereotype names, and the
    prefixed form is what `t_object.Stereotype` holds. Measured, and pinned
    because a reader who knows the ArchiMate specification would expect the
    bare concept name."""
    binding = find_binding("ArchiMate3")
    assert binding.stereotype_prefix == "ArchiMate_"
    assert (binding.stereotype_for("ApplicationComponent")
            == "ArchiMate_ApplicationComponent")
    assert (binding.concept_for("ArchiMate_ApplicationComponent")
            == "ApplicationComponent")


def test_bpmn_has_no_stereotype_prefix():
    binding = find_binding("BPMN2.0")
    assert binding.stereotype_prefix == ""
    assert binding.stereotype_for("Activity") == "Activity"


def test_a_stereotype_from_another_technology_passes_through_unchanged():
    """A model holds elements from other technologies and from none. A lookup
    helper is the wrong place to have an opinion about that."""
    binding = find_binding("ArchiMate3")
    assert binding.concept_for("BusinessProcess") == "BusinessProcess"
    assert binding.concept_for("") == ""


def test_bpmn_event_and_gateway_sizes_are_the_measured_ones():
    """A 110x60 "circle" is not a BPMN event.

    These are notation requirements, not preferences: the event sizes were
    unanimous or near-unanimous across 173 measured events and the gateway
    across all 61.
    """
    dt = find_binding("BPMN2.0").diagram_type("Business Process")
    assert dt.size_for() == (110, 60)
    for event in ("StartEvent", "EndEvent", "IntermediateEvent"):
        assert dt.size_for(event) == (30, 30), event
    assert dt.size_for("Gateway") == (42, 42)
    assert dt.size_for("DataObject") == (35, 50)


def test_an_unsized_concept_falls_back_to_the_default():
    dt = find_binding("BPMN2.0").diagram_type("Business Process")
    assert dt.size_for("SubProcess") == dt.size_for()
    assert dt.size_for("") == dt.size_for()


def test_archimate_claims_fill_on_every_diagram_type():
    """The finding the `channels` block exists to mechanize.

    ArchiMate's palette IS the notation. A binding that let an agent recolor
    fills by lifecycle would have broken the notation while looking like a
    feature, so this is asserted for every diagram type rather than the one
    that happened to get written first.
    """
    binding = find_binding("ArchiMate3")
    for name, dt in binding.diagram_types.items():
        assert "fill" in dt.claimed_channels(), name
        assert not dt.channel_is_free("fill"), name
        assert dt.free_channels(), f"{name} leaves nothing for a second variable"


def test_bpmn_claims_size_because_shape_carries_kind():
    for name, dt in find_binding("BPMN2.0").diagram_types.items():
        assert "size" in dt.claimed_channels(), name
        assert not dt.channel_is_free("size"), name


def test_every_shipped_diagram_type_leaves_some_channel_free():
    """A notation that claims everything gives a second variable nowhere to go,
    and a caller with nowhere to go recolors something it should not."""
    for technology in available_bindings():
        binding = find_binding(technology)
        for name, dt in binding.diagram_types.items():
            assert dt.free_channels(), f"{technology}::{name}"


def test_every_shipped_spec_composes_without_the_engine_complaining():
    """The seam, end to end, without EA.

    `compose.py` validates its spec and raises on a pitch smaller than the item
    it steps over. Running every shipped diagram type's spec through the engine
    its grammar names is how a binding with arithmetically impossible spacing
    is caught here rather than at generation time.
    """
    items = [{"id": 1, "name": "One"}, {"id": 2, "name": "Two"}]
    for technology in available_bindings():
        binding = find_binding(technology)
        for name, dt in binding.diagram_types.items():
            if not dt.grammar_is_implemented:
                continue
            spec = dt.spec()
            where = f"{technology}::{name}"
            if dt.grammar == "layered-bands":
                result = compose_layered_bands(
                    [{"name": "Band", "items": items}], spec)
            else:
                result = compose_lanes(
                    [{"name": "Lane", "items": items}], spec)
            assert len(result["items"]) == 2, where
            width, height = dt.size_for()
            for item in result["items"]:
                assert item["right"] - item["left"] == width, where
                assert item["top"] - item["bottom"] == height, where


def test_every_shipped_viewpoint_admits_something():
    """A viewpoint that admits nothing can never be selected, so it is a typo
    rather than a restriction."""
    for technology in available_bindings():
        binding = find_binding(technology)
        for name, vp in binding.viewpoints.items():
            assert vp.admits, f"{technology}::{name}"
            assert vp.intent, f"{technology}::{name} has no intent phrases"


def test_archimate_viewpoint_admits_lists_use_concepts_not_stereotypes():
    """`admits` is written the way the ArchiMate specification names things.

    Mixing the two forms in one list is the mistake the prefix design exists to
    prevent, and it would fail silently: a stereotype histogram matched against
    `ArchiMate_ApplicationComponent` in one entry and `ApplicationComponent` in
    the next would rank viewpoints on a coin toss.
    """
    binding = find_binding("ArchiMate3")
    for name, vp in binding.viewpoints.items():
        for concept in vp.admits:
            assert not concept.startswith(binding.stereotype_prefix), (
                f"{name} admits {concept!r}; use the concept name")


def test_both_pilots_define_the_same_three_presentation_profiles():
    """Presentation is a view concern, orthogonal to notation. The profiles are
    the same three in both pilots on purpose - what differs is what each
    notation has to suppress."""
    for technology in ("ArchiMate3", "BPMN2.0"):
        profiles = find_binding(technology).presentation_profiles
        assert sorted(profiles) == ["detail", "executive", "review"]
        assert profiles["executive"].collapses_parallel is True
        assert profiles["detail"].collapses_parallel is False


#: Every whole-diagram setting a profile is allowed to emit. Each was verified
#: BY RENDERING against content it could bite on -- not by writing it and
#: reading it back, which EA would echo regardless.
#:
#: `SuppressedCompartments` is deliberately absent. It was measured through six
#: value shapes against a class with attributes and operations and changed
#: nothing every time, so `compartments: none` cannot remove a compartment; it
#: reduces one to names. A profile that emitted it would promise a suppression
#: that silently does nothing.
VERIFIED_DISPLAY_SETTINGS = {
    "hide_connector_labels",
    "hide_element_stereotypes",
    "hide_connector_stereotypes",
    "hide_attribute_types",
    "hide_operation_return_types",
    "hide_operation_brackets",
    "show_element_notes",
}


def test_no_shipped_profile_promises_an_unverified_suppression():
    """A profile must not emit a setting nobody has watched EA obey.

    This list grew from two to seven once the six "unverified, not disproven"
    keys were measured against content they could actually suppress -- five
    worked, all through StyleEx. The seventh, `SuppressedCompartments`, did not,
    and is the reason this allowlist exists rather than a blanket "emit whatever
    the profile says".
    """
    for technology in available_bindings():
        binding = find_binding(technology)
        for name, profile in binding.presentation_profiles.items():
            emitted = set(profile.display_settings())
            assert emitted <= VERIFIED_DISPLAY_SETTINGS, (
                f"{technology}::{name} emits "
                f"{emitted - VERIFIED_DISPLAY_SETTINGS}")


def test_the_three_profiles_are_actually_different(): 
    """A profile scheme whose profiles emit the same settings is decoration.

    Asserted as strict progression on how much is hidden, which is the claim the
    names make: detail hides nothing, executive hides the most.
    """
    for technology in available_bindings():
        binding = find_binding(technology)
        if not binding.presentation_profiles:
            # Optional in the schema: a binding that declares none says nothing
            # about presentation rather than asserting an empty scheme.
            continue
        hidden = {}
        for name in ("detail", "review", "executive"):
            settings = binding.profile(name).display_settings()
            hidden[name] = sum(1 for k, v in settings.items()
                               if v and k.startswith("hide_"))
        assert hidden["detail"] == 0, f"{technology}: detail hides something"
        assert hidden["detail"] < hidden["review"] < hidden["executive"], (
            f"{technology}: {hidden}")


def test_notes_is_the_one_setting_whose_polarity_does_not_flip():
    """EA does not draw element notes by default, so `notes: true` is a SHOW.

    Pinned because every other setting in this translation inverts, and a reader
    tidying the method for consistency would turn notes off in the detail
    profile and on in the executive one -- exactly backwards.
    """
    binding = find_binding("ArchiMate3")
    assert binding.profile("detail").display_settings()["show_element_notes"]         is True
    assert binding.profile("executive").display_settings()[
        "show_element_notes"] is False


# ---------------------------------------------------------------------------
# The layer boundary
# ---------------------------------------------------------------------------
#: `uml` is in the list for the same reason as the rest, and it was added when
#: the base notation became the root of the binding tree: that is the point at
#: which `if base_notation == "UML"` becomes the tempting shortcut in the loader,
#: and the loader must resolve a parent from the data rather than from a name it
#: knows. The engine and the loader both pass with it in, so nothing in either
#: file acts on it today.
_TECHNOLOGY_WORDS = ("archimate", "bpmn", "sysml", "togaf", "uaf", "dmn",
                     "zachman", "arcgis", "niem", "uml")


def _code_strings_in(source: str) -> list[str]:
    """Every string literal that is not a docstring, plus every name the code
    declares or uses.

    "Every name" has to mean every name, because the realistic leak is not
    `if technology == "ArchiMate3"` - it is an import or a public function that
    carries the notation in its own identifier. So the walk collects imported
    module names and aliases, function, async-function and class names,
    parameter names and keyword-argument names, not only `Name`, `Attribute`
    and string constants. Restricted to those three, the scan reports zero
    offenders for a module whose only leaks are `from archimate_tables import
    SIZES` and `def compose_archimate_bands(...)` - the two most likely ones.

    Comments and docstrings are excluded deliberately: `compose.py` is allowed
    to *mention* ArchiMate while explaining why it does not branch on it. What
    it may not do is act on the name. Note the exclusion is BY VALUE, so a
    function whose docstring were exactly `"ArchiMate3"` would also blank every
    `"ArchiMate3"` literal in the file - contrived enough to record here rather
    than engineer around.
    """
    tree = ast.parse(source)
    docstrings = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef,
                             ast.AsyncFunctionDef)):
            doc = ast.get_docstring(node, clean=False)
            if doc is not None:
                docstrings.add(doc)
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            if node.value not in docstrings:
                out.append(node.value)
        elif isinstance(node, ast.Name):
            out.append(node.id)
        elif isinstance(node, ast.Attribute):
            out.append(node.attr)
        elif isinstance(node, ast.alias):
            out.append(node.name)
            if node.asname:
                out.append(node.asname)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                out.append(node.module)
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef,
                               ast.ClassDef)):
            out.append(node.name)
        elif isinstance(node, ast.arg):
            out.append(node.arg)
        elif isinstance(node, ast.keyword):
            if node.arg:
                out.append(node.arg)
    return out


def _code_strings(path: Path) -> list[str]:
    return _code_strings_in(path.read_text(encoding="utf-8"))


def _technology_offenders(strings: list[str]) -> list[str]:
    """The filter both layer-boundary tests apply, in one place.

    Shared so the synthetic-leak test below exercises the same predicate the
    real files are scanned with, rather than a paraphrase of it that could pass
    while the real one missed.
    """
    return [s for s in strings
            if any(word in s.lower() for word in _TECHNOLOGY_WORDS)]


def _imported_names(source: str) -> set[str]:
    """Every module or name an import statement brings into a namespace.

    Both halves of an import matter, and dotted paths are split. `from tools
    import bindings` and `from . import bindings as _b` name the loader in the
    *alias*, so reading only `ImportFrom.module` sees nothing; `import
    tools.bindings` hides it in a path segment.
    """
    out: set[str] = set()
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            if isinstance(node, ast.ImportFrom) and node.module:
                out.update(node.module.split("."))
            for alias in node.names:
                out.update(alias.name.split("."))
                if alias.asname:
                    out.add(alias.asname)
    return out


# A module that leaks a notation name in every shape the scan has to reach, and
# also names notations in its docstrings, where they are allowed. Held as a
# string on purpose: nothing about this test needs a file on disk.
_LEAKY_MODULE = '''
"""A docstring may mention ArchiMate all it likes."""
from archimate_tables import SIZES
from tables import dmn_sizes
import bpmn_helpers
import plain_helpers as zachman_helpers
from .sysml_defaults import DEFAULTS


def compose_archimate_bands(spec):
    """A docstring may mention BPMN too."""
    return _apply(spec, archimate_mode=True)


def _apply(cfg, togaf_mode=False):
    return cfg.uaf_layout


async def load_niem_profile():
    return None


class BpmnLaneEngine:
    pass


TABLE = "zachman-grid"
'''

# Shape -> the name the scan must report for it. Keyed by the name so a miss
# names the shape that is invisible rather than just failing a set comparison.
_LEAK_SHAPES = {
    "archimate_tables": "the module of a `from <tech> import ...`",
    "dmn_sizes": "the name an import binds, from an innocent module",
    "bpmn_helpers": "a plain `import <tech>`",
    "zachman_helpers": "the alias an import is renamed to",
    "sysml_defaults": "the module of a relative `from .<tech> import ...`",
    "compose_archimate_bands": "a public function's own name",
    "archimate_mode": "a keyword argument at a call site",
    "togaf_mode": "a parameter in a signature",
    "uaf_layout": "an attribute being read",
    "load_niem_profile": "an async function's own name",
    "BpmnLaneEngine": "a class's own name",
    "zachman-grid": "a plain string literal",
}


def test_the_technology_name_scan_sees_every_shape_a_name_can_hide_in():
    """The test that makes the two layer-boundary tests below mean something.

    They assert an empty list. An empty list is also what a scan that looks in
    the wrong places returns, so without this the acceptance criterion could be
    "met" by a helper that sees nothing. `_LEAKY_MODULE` puts a notation name in
    each shape a real leak would take and this pins that the scan reports every
    one. Remove it and `_code_strings_in` can quietly stop visiting imports or
    function names - the shapes it originally missed - with all three tests
    still green.
    """
    offenders = set(_technology_offenders(_code_strings_in(_LEAKY_MODULE)))
    missed = {name: shape for name, shape in _LEAK_SHAPES.items()
              if name not in offenders}
    assert not missed, f"the scan cannot see a technology name in: {missed}"
    # And the deliberate exclusion still holds: docstrings may say the words.
    assert not [s for s in offenders if "docstring" in s.lower()]


def test_the_engine_contains_no_technology_name():
    """The acceptance criterion, as a test.

    A single `if technology == "ArchiMate3"` in `compose.py` - or an import,
    function or parameter named after a notation - would undo the whole design,
    new notations becoming engineering tasks again, while every other test in
    this suite still passed. The scan's reach is pinned separately above.
    """
    offenders = _technology_offenders(_code_strings(_HERE / "compose.py"))
    assert not offenders, f"compose.py acts on a technology name: {offenders}"


def test_the_loader_contains_no_technology_name_in_its_code_either():
    """The loader is allowed to document what it measured about ArchiMate and
    BPMN; it is not allowed to special-case them. Otherwise "conventions as
    data" is only true of the files."""
    offenders = _technology_offenders(_code_strings(_HERE / "bindings.py"))
    assert not offenders, f"bindings.py acts on a technology name: {offenders}"


_LOADER_IMPORT_SHAPES = (
    "import bindings",
    "import tools.bindings",
    "from bindings import load_binding",
    "from tools import bindings",
    "from . import bindings as _b",
    "from .bindings import load_binding",
)


def test_the_import_check_sees_every_shape_the_import_could_take():
    """Same reason as the scan test: `assert "bindings" not in imported` passes
    trivially against a set built the wrong way.

    The original built it from `alias.name` for `import` but only `node.module`
    for `from ... import`, so `from tools import bindings` and `from . import
    bindings as _b` - the two shapes this directory's own sys.path trick makes
    likely - were both invisible. Remove this and the boundary test below can go
    back to reading half the import.
    """
    for shape in _LOADER_IMPORT_SHAPES:
        assert "bindings" in _imported_names(shape), shape


def test_the_engine_does_not_import_the_loader():
    """The dependency runs one way: a binding is data that feeds the engine.

    Remove this and `compose.py` could grow `from . import bindings` and start
    resolving conventions itself, which is the same design failure as branching
    on a technology id with an extra indirection in front of it.
    """
    source = (_HERE / "compose.py").read_text(encoding="utf-8")
    assert "bindings" not in _imported_names(source)


def test_route_names_match_the_server():
    """Pins this file's copy of the route vocabulary. It cannot see server drift.

    `_ROUTE_STYLES` plus `_BEZIER_MODE` in `ea_mcp_server.server` are the source
    of truth, and `bindings.py` holds a copy so a typo'd route in a binding is
    caught on load rather than at write time. This test does NOT compare the
    two, and deriving it is not available: the skills bundle must not import the
    server, because a customer install has the bundle and no server source on
    the path. The set below is a second copy, written here.

    So what it catches is an edit on THIS side - a route dropped from or renamed
    in `ROUTE_NAMES`, which would make bindings using it fail to load. What it
    cannot catch is a rename on the server side, which would leave both copies
    agreeing with each other and neither with EA.

    That drift is caught in the server's own suite.
    `tests/test_apt_2026_0144_binding_generation.py` takes every route it
    applies from `find_binding(...)` rather than restating one, and asserts the
    connector EA holds carries it - so a name this copy still lists that the
    server's route table no longer resolves fails there, at generation. Those
    tests need real EA and skip without it, so the protection lands when that
    suite runs, not on every green run of this file.

    Bezier is included even though EA reaches it a different way - a binding
    author should not have to know that.
    """
    assert ROUTE_NAMES == {
        "direct", "autorouting", "customline", "treevertical",
        "treehorizontal", "lateralvertical", "lateralhorizontal",
        "orthogonalsquare", "orthogonalrounded", "bezier",
    }


def _engine_grammars() -> set[str]:
    """The grammars `compose.py` actually implements, read from `compose.py`.

    One public `compose_<grammar>` function per grammar, with underscores
    standing in for the hyphens the vocabulary uses. Read from the module rather
    than from its `__all__`, so a grammar shipped without being exported still
    counts - the question is what the engine can do, not what it advertises.
    """
    import compose

    return {
        name[len("compose_"):].replace("_", "-")
        for name in dir(compose)
        if name.startswith("compose_") and callable(getattr(compose, name))
    }


def test_the_grammar_vocabulary_matches_what_the_engine_implements():
    """Eight grammars; which of them are composable is read from `compose.py`.

    What a consumer trusts before it composes has to be the engine's answer and
    not a remembered one. Comparing `IMPLEMENTED_GRAMMARS` to a set written here
    would have stayed green the day `compose_nested_grid` shipped - which is
    exactly the day a consumer should stop falling back to a plain graph layout
    for capability maps. Remove this and that lag becomes invisible.

    The names themselves stay a literal: "the variety of real diagrams resolves
    into these" is a finding, and a new one appearing is a change to review
    rather than a set to follow.

    IT WENT FROM FOUR TO FIVE, which is the review this literal exists to force.
    Measuring the rows grouped under `computed-geometry` before building it
    showed they do not share an arithmetic: placing items on a circle, packing
    rectangles so their AREAS encode a number, and drawing a waveform against a
    time axis are three unrelated pieces of code. `radial` was split out and
    built; the treemap and the timing diagram are what remain under the old
    name. See `APT-2026-0161`.

    THEN FROM FIVE TO SEVEN, and the two additions are not layouts at all: they
    are the two ways a diagram gets its positions from EA rather than from us.
    Nothing in the five said "this is a graph, EA places it", so a binding author
    facing one had to record a composed layout the diagram type does not have, or
    leave the type out - and most diagram types in most notations are graphs. See
    `APT-2026-0176`.

    THEN FROM SEVEN TO EIGHT, which is a layout again: `two-column-cycle`, a cycle
    drawn as two columns with the flow running down one and back up the other. It
    was the last row of the corpus audit waiting on engine code. Reviewing it
    against the existing five, which is what this literal is for: its arithmetic
    is a split and a pitch rather than a bearing, so it is not radial with an
    argument; and its boxes are deliberately different HEIGHTS, which no other
    composed layout allows, so it could not have been a parameter on one of them.

    THEN FROM EIGHT TO ELEVEN, three at once, and reviewing them against the
    existing set is exactly what this literal is for:

    * `matrix` is a lattice addressed by row and column, with one cell size for
      the whole grid. It is NOT `nested-grid` with headers: the nested grid
      sizes a container by its contents because there the size IS the data,
      while here the ADDRESS is the data and a wandering boundary destroys it.
      The two answer opposite questions and neither is a parameter on the other.
    * `radial-tree` is not `radial` with nesting, and that was checked rather
      than assumed. `radial` splits its sweep EVENLY, so a branch with eight
      children gets the same arc as a branch with one; it also caps at two
      rings. Measured on twelve branches with one carrying eight children:
      `radial` produced 1746x3399 and `radial-tree` 2122x2134. The difference is
      structural - room allocated by leaf count - not a tuning parameter.
    * `chevron-stack` earns its place on an equality no other grammar has. Its
      pitch EQUALS the item width exactly, because the interlock is drawn
      outside the rect by the element's own shape script and the notch fraction
      cancels. Every other grammar treats its pitch as a floor, and widening
      this one opens a sliver that every shipped lint rule stays quiet about -
      so the constraint could not be expressed as a spec value on an existing
      layout.

    THEN FROM ELEVEN TO TWELVE: `treemap`, an area-proportional tiling, which
    partitions a region so tiles share boundaries exactly and there is
    deliberately NO gap between them - whitespace would be area subtracted from
    the very number the reader is comparing, and taken from small tiles
    proportionally more. Reviewing it against the existing set:

    * Both corpus references were measured pixel by pixel, and they are two
      different algorithms. `heat-map.png` is genuinely SQUARIFIED - the
      signature is that tile orientation changes inside a single group (one tile
      taking the full body height on the left, two stacked beside it on the
      right), which neither a grid nor plain slice-and-dice can produce.
      `heat-maps.png` is slice-and-dice, and its narrowest strip sits at aspect
      0.21 - exactly the sliver squarifying exists to prevent. One engine
      subsumes both, so this is one grammar rather than two.
    * It could not have been a parameter on `matrix`: that grammar's cells are
      uniform and gapped BY REQUIREMENT, because there the cell ADDRESS is the
      information. These tiles are unequal by construction and gapless by
      design, because here the AREA is the information. Opposite requirements,
      not a setting.
    * Its correctness condition is of a different KIND from every other grammar
      here. Nothing is placed at a distance, so neither `max(w, h)` nor
      `hypot(w, h)` applies at all: separation is combinatorial - interval
      disjointness on one axis - and exact, with no margin term.

    The second assertion is the one that keeps the split honest. Because
    `implemented_grammars()` is the vocabulary's composed half INTERSECTED with
    the engine's `compose_*` functions, it can only equal the engine's own answer
    while every composer the engine has is a grammar the vocabulary knows. A
    composer shipped under a name nobody added here would be silently dropped
    from every reach figure otherwise.
    """
    assert set(GRAMMARS) == {"layered-bands", "lanes", "nested-grid",
                             "radial", "two-column-cycle", "matrix",
                             "radial-tree", "chevron-stack", "treemap",
                             "computed-geometry",
                             "graph", "ea-semantic"}
    assert IMPLEMENTED_GRAMMARS == _engine_grammars()
    assert _engine_grammars() <= COMPOSED_GRAMMARS
    assert CHANNELS >= {"fill", "border", "opacity", "icon"}


# ---------------------------------------------------------------------------
# The cross-check the item asked for
# ---------------------------------------------------------------------------
def test_every_behavioral_difference_between_the_pilots_is_data():
    """The schema's real test: the two pilots are maximally different
    notations, and diffing them must account for every difference in behavior.

    Each assertion below is a way the two notations genuinely diverge, read
    from the loaded bindings. If any of them started coming from code instead,
    the value of the data layer would be gone - which is why this is one test
    listing all of them rather than several that could each be satisfied by a
    special case.
    """
    archimate = find_binding("ArchiMate3")
    bpmn = find_binding("BPMN2.0")

    # 1. Stereotype naming: prefixed against bare.
    assert archimate.stereotype_prefix == "ArchiMate_"
    assert bpmn.stereotype_prefix == ""

    # 2. Title convention: drawn against the diagram frame. Measured 13/13 and
    #    10/11 in the corpus, and the split tracks notation.
    assert all(dt.draws_its_own_title
               for dt in archimate.diagram_types.values())
    assert not any(dt.draws_its_own_title
                   for dt in bpmn.diagram_types.values())

    # 3. Grammar: stratified layers against lanes and flow.
    assert {dt.grammar for dt in archimate.diagram_types.values()} \
        == {"layered-bands"}
    assert {dt.grammar for dt in bpmn.diagram_types.values()} == {"lanes"}

    # 4. Sizing: one box size for nearly everything against a size per node
    #    kind, because BPMN shapes are not interchangeable.
    assert len(archimate.diagram_type("Application").sizing) < len(
        bpmn.diagram_type("Business Process").sizing)

    # 5. Spacing. Asserted on the keys each grammar ACTUALLY READS, which is not
    #    the same set. `compose_lanes` never reads `item_gap_x` or `item_gap_y`,
    #    so comparing those two across the pilots -- which an earlier version of
    #    this test did, calling it the headline difference -- compares numbers
    #    that cannot affect a composed BPMN diagram. They are kept in the binding
    #    as recorded measurements and the binding says so; they are not behavior.
    archimate_dt = archimate.diagram_type("Application")
    bpmn_dt = bpmn.diagram_type("Business Process")
    #    Bands: ArchiMate's own two axes differ, measured at ~75 against ~40.
    assert archimate_dt.spacing["item_gap_x"] > archimate_dt.spacing["item_gap_y"]
    #    Lanes: the load-bearing key is the one along the flow.
    assert bpmn_dt.spacing["item_gap_flow"] > 0
    assert "item_gap_flow" not in archimate_dt.spacing
    #    Pools abut; ArchiMate bands do not. Asserted on COMPOSED geometry,
    #    because `archimate3.yaml` deliberately does not set `band_gap` -- band
    #    gutters were never separately measured, so the engine default stands
    #    rather than a number nobody observed. Neither `.spacing` (the raw
    #    binding block) nor `.spec()` (which carries only what the binding
    #    states, leaving the engine to fill the rest) reports it, so a constant
    #    would be the wrong thing to read: what matters is that the bands come
    #    out apart and the lanes come out touching.
    assert bpmn_dt.spacing["lane_gap"] == 0
    assert "band_gap" not in archimate_dt.spacing

    two = [{"name": "Upper", "items": [{"id": 1}]},
           {"name": "Lower", "items": [{"id": 2}]}]
    bands = sorted(compose_layered_bands(two, archimate_dt.spec())["containers"],
                   key=lambda c: -c["top"])
    assert bands[0]["bottom"] > bands[1]["top"], (
        "ArchiMate bands abut; they should have a gutter between them")

    lanes = sorted(compose_lanes(two, bpmn_dt.spec())["containers"],
                   key=lambda c: -c["top"])
    assert lanes[0]["bottom"] == lanes[1]["top"], (
        "BPMN pools have a gutter; they should abut")

    # 6. Trunking: ArchiMate fans relationships into a shared trunk; BPMN does
    #    not, because its gateways make branching an explicit node.
    assert archimate.diagram_type("Application").routing["trunk_for"]
    assert "trunk_for" not in bpmn.diagram_type("Business Process").routing

    # 7. Claimed channels: both claim fill, for different reasons, and BPMN
    #    additionally claims size.
    assert "size" in bpmn.diagram_type("Business Process").claimed_channels()
    assert "layer" in archimate.diagram_type(
        "Application").claimed_channels()["fill"].lower()

    # 8. Viewpoint catalog: ArchiMate publishes one, BPMN does not. An empty
    #    catalog is a fact about the notation, not a gap in the binding.
    assert len(archimate.viewpoints) >= 12
    assert bpmn.viewpoints == {}

    # 9. Coverage: BPMN deliberately leaves two of its five diagram types
    #    unbound, because a conversation diagram is a graph and BPEL is an
    #    export format. Refusing to bind them is the honest answer.
    assert bpmn.diagram_type_for_mdgdgm("BPMN2.0::Conversation") is None
    assert bpmn.diagram_type_for_mdgdgm("BPMN2.0::BPEL") is None

    # 10. And the base diagram type EA creates them from differs.
    assert archimate.diagram_type("Application").base == "Logical"
    assert bpmn.diagram_type("Business Process").base == "Analysis"


# ---------------------------------------------------------------------------
# Resolution: from the technologies a repository has installed to a binding
# ---------------------------------------------------------------------------
# Hermetic like everything else here: no repository is opened and no COM object
# is touched. What EA would supply - the set of technology ids it reports
# loaded, and two columns of `t_diagram` - is supplied as plain values, the same
# way the server's own toolkit tests stand in for a repository with a fake that
# answers `IsTechnologyLoaded` from a set of ids.
def _fixture(technology: str, *diagram_types: str, base: str = "Custom",
             concept: str = "Component") -> Binding:
    """A binding for `technology` declaring `diagram_types`, all on one base.

    Everything except the technology id is identical between two fixtures built
    from this, which is what keeps the ambiguity tests about the collision and
    nothing else: two technologies claiming the same diagram types, the same
    concept, and the same (absent) stereotype prefix.
    """
    body = "\n".join(
        f"""  {name}:
    base: {base}
    grammar: layered-bands
    title: drawn
    sizing:
      default: {{w: 100, h: 60}}
      {concept}: {{w: 140, h: 70}}
    routing:
      default: Direct
    channels:
      fill: ~
      free: [border]"""
        for name in diagram_types)
    return load_binding_text(
        f"technology: {technology}\ndiagram_types:\n{body}\n",
        source=f"{technology}.yaml")


# What the runtime technology reader returns for a customer's own MDG, cut down
# to the one field resolution reads. The three diagram stereotypes and their
# aliases are the canonical Westbrook Bank example's, not invented here; their
# base diagram types are left out because that reference does not record them
# and guessing one would put an unmeasured fact in a fixture.
_CUSTOMER_RUNTIME = {
    "WBA": {
        "tech_id": "WBA",
        "source": "live",
        "loaded": True,
        "diagram_types": [
            {"name": "WBAApplicationView",
             "alias": "WBA Application Architecture"},
            {"name": "WBAProcessView", "alias": "WBA Business Process"},
            {"name": "WBADataModelView", "alias": "WBA Data Model"},
        ],
    },
}


def _resolve(**kwargs):
    """Resolve against the shipped bindings, with both pilots installed."""
    kwargs.setdefault("directory", _BINDINGS_DIR)
    return resolve_diagram({"ArchiMate3", "BPMN2.0", "UML"}, **kwargs)


def test_a_diagram_that_states_its_own_technology_and_type_resolves_exactly():
    """The 47% case: `MDGDgm` carries a value, so nothing is inferred."""
    resolution = _resolve(style_ex="MDGDgm=BPMN2.0::Business Process;",
                          diagram_type="Analysis")
    assert resolution.path == "qualified"
    assert resolution.confidence == "exact"
    assert resolution.resolved
    assert resolution.key == "BPMN2.0::Business Process"
    assert resolution.diagram_type.grammar == "lanes"


def test_the_diagram_type_path_answers_when_the_qualified_key_is_empty():
    """The point of the item, and the majority case.

    `MDGDgm` is present but EMPTY on 603 of the 1129 diagrams in the example
    model shipped with EA 17.1 - the diagram identifies itself through
    `Diagram_Type` alone. A resolver that reads only the qualified key answers
    nothing for more than half a real repository.
    """
    resolution = _resolve(style_ex="MDGDgm=;DUID={ABC}",
                          diagram_type="Business Process")
    assert resolution.path == "diagram-type"
    assert resolution.confidence == "inferred"
    assert resolution.resolved
    assert resolution.key == "BPMN2.0::Business Process"


def test_an_absent_qualified_key_and_an_empty_one_are_the_same_answer():
    """Both mean the diagram has not named its MDG diagram type."""
    empty = _resolve(style_ex="MDGDgm=;", diagram_type="Business Process")
    absent = _resolve(style_ex="DUID={ABC};", diagram_type="Business Process")
    assert empty.path == absent.path == "diagram-type"
    assert empty.key == absent.key


def test_the_qualified_key_is_read_out_of_a_full_style_ex_value():
    """Its value contains `::` and its neighbors contain `=`, so neither a
    split on every separator nor a naive parse of the whole string works."""
    style_ex = ("MDGDgm=ArchiMate3::Application;"
                "Layout=layerSpc=20:colSpc=10:;DUID={9F2A};")
    assert mdg_diagram_key(style_ex) == "ArchiMate3::Application"
    assert mdg_diagram_key("DUID={9F2A};") == ""
    assert mdg_diagram_key("MDGDgm=;DUID={9F2A};") == ""
    # A value with no `::` names no diagram type, so it is not a key.
    assert mdg_diagram_key("MDGDgm=ArchiMate3;") == ""


def test_a_base_type_only_match_resolves_but_is_reported_as_weak():
    """`Diagram_Type` holds a base EA type, which is a much weaker statement
    than a diagram type name - so it resolves at lower confidence and says so.
    """
    house = _fixture("WBA", "WBAApplicationView", base="Logical",
                     concept="WBABusinessApplication")
    resolution = resolve_diagram({"WBA"}, diagram_type="Logical",
                                 bindings=[house])
    assert resolution.path == "base-type"
    assert resolution.confidence == "weak"
    assert resolution.key == "WBA::WBAApplicationView"


def test_a_base_type_several_diagram_types_share_is_ambiguous_without_the_root():
    """A base-only match that several diagram types claim cannot pick one.

    It now takes TWO catalogs to show that, and the difference is itself the
    finding. Every diagram type in an MDG binding declares the same base as its
    siblings, so a base-only match is ambiguous across all of them - which is the
    answer when the base notation is not among the bindings on hand. Now that the
    base notation binds every base its children sit on, the same value matches a
    diagram type NAME, and the name path answers first and outright: a plain
    diagram of that base IS a diagram of the base notation.

    The single-claimant case is the one worth reading twice. A base only one MDG
    diagram type sits on used to resolve to that diagram type by the weak path -
    so every plain diagram drawn on EA's MDG canvas came back as this
    repository's requirement diagram, a confident wrong answer of exactly the
    kind the resolver exists to avoid.

    Every value here is derived from the catalog on disk. The claimants used to be
    read off one named binding, which is the shape that broke twice.
    """
    shipped = _shipped_bindings()
    root = _root_of(shipped)
    children = {t: b for t, b in shipped.items() if t != root}
    installed = sorted(shipped)
    bases = sorted({dt.base for binding in children.values()
                    for dt in binding.diagram_types.values()})
    assert bases
    for base in bases:
        claimants = {dt.mdg_diagram_type for binding in children.values()
                     for dt in binding.diagram_types.values()
                     if dt.base == base}
        without_root = resolve_diagram(installed, diagram_type=base,
                                       bindings=list(children.values()))
        if len(claimants) > 1:
            assert without_root.is_ambiguous, base
            assert not without_root.resolved
            assert without_root.binding is None
            assert set(without_root.candidates) == claimants, base
        else:
            assert without_root.path == "base-type", base
            assert without_root.confidence == "weak", base
            assert without_root.key in claimants, base
        with_root = resolve_diagram(installed, diagram_type=base,
                                    bindings=list(shipped.values()))
        assert with_root.path == "diagram-type", base
        assert with_root.technology == root, base


def test_two_installed_technologies_claiming_one_diagram_type_name_both_get_named():
    """The shadowing hazard, reported rather than resolved.

    Two installed technologies can claim the same diagram type, and which one
    EA renders a diagram with is a runtime matter the repository file does not
    record. The two fixtures here are identical but for their id - the same
    diagram type, the same concept, the same absent prefix - which is the
    hazard in its purest form.
    """
    pair = [_fixture("Alpha", "Landscape"), _fixture("Beta", "Landscape")]
    resolution = resolve_diagram({"Alpha", "Beta"}, diagram_type="Landscape",
                                 bindings=pair)
    assert resolution.is_ambiguous
    assert resolution.confidence == "none"
    assert resolution.candidates == ("Alpha::Landscape", "Beta::Landscape")
    assert resolution.binding is None and resolution.diagram_type is None
    for technology in ("Alpha", "Beta"):
        assert technology in resolution.reason


def test_binding_order_does_not_change_an_ambiguous_answer():
    """The specific failure this bucket exists to prevent: an answer decided by
    the order the bindings arrived in, which is indistinguishable from a
    correct one and wrong about as often as not."""
    pair = [_fixture("Alpha", "Landscape"), _fixture("Beta", "Landscape")]
    forward = resolve_diagram({"Alpha", "Beta"}, diagram_type="Landscape",
                              bindings=pair)
    backward = resolve_diagram({"Alpha", "Beta"}, diagram_type="Landscape",
                               bindings=list(reversed(pair)))
    assert forward.path == backward.path
    assert forward.candidates == backward.candidates
    assert forward.reason == backward.reason


def test_one_claimant_still_wins_outright_rather_than_being_ambiguous():
    """Ambiguity is a genuine tie, not merely "more than one binding exists"."""
    pair = [_fixture("Alpha", "Landscape"), _fixture("Beta", "Portfolio")]
    resolution = resolve_diagram({"Alpha", "Beta"}, diagram_type="Portfolio",
                                 bindings=pair)
    assert resolution.resolved
    assert resolution.key == "Beta::Portfolio"


def test_a_guessed_technology_id_resolves_to_nothing_and_says_so():
    """The failure mode the module is built against.

    `BPMN2.0` is the id, not `BPMN2`; `ArchiMate3`, `SysML1.4` and `DMN1.1`
    carry their versions the same way. A lookup on a guessed id resolves to
    nothing silently, which reads exactly like a diagram that has no binding -
    so the guess has to be named as a guess.
    """
    guessed = _resolve(style_ex="MDGDgm=BPMN2::Business Process;",
                       diagram_type="Analysis")
    assert guessed.path == "not-installed"
    assert not guessed.resolved
    assert "BPMN2" in guessed.reason
    assert "not among" in guessed.reason
    # And the answer is different from the one the real id gets, which is the
    # whole point: silence would have made the two indistinguishable.
    real = _resolve(style_ex="MDGDgm=BPMN2.0::Business Process;")
    assert real.resolved and real.path != guessed.path


def test_a_guessed_diagram_type_is_reported_as_misspelled_not_merely_unbound():
    """A diagram type name is no more guessable than a technology id.

    When the caller supplies the runtime inventory - technology id to that
    technology's own definition - a stated type the technology does not declare
    can be called what it is. `WBAApplicationView` is the declared name; the
    unprefixed form is a guess.
    """
    resolution = resolve_diagram(_CUSTOMER_RUNTIME,
                                 style_ex="MDGDgm=WBA::ApplicationView;",
                                 bindings=[])
    assert resolution.path == "unbound"
    assert "misspelled" in resolution.reason
    # The declared form is not called misspelled, only unbound.
    declared = resolve_diagram(_CUSTOMER_RUNTIME,
                               style_ex="MDGDgm=WBA::WBAApplicationView;",
                               bindings=[])
    assert declared.path == "unbound"
    assert "misspelled" not in declared.reason


def test_an_installed_technology_with_no_binding_is_unbound_not_an_error():
    """The common answer - 123 of the 147 catalogued diagrams - and a customer's
    own MDG is exactly this case. The caller falls back to engine defaults."""
    resolution = resolve_diagram({"ArchiMate3", "WBA"},
                                 style_ex="MDGDgm=WBA::WBAProcessView;",
                                 directory=_BINDINGS_DIR)
    assert resolution.path == "unbound"
    assert not resolution.resolved
    assert resolution.technology == "WBA"
    assert "WBA" in resolution.reason


def test_a_binding_for_a_technology_the_repository_lacks_is_never_used():
    """The rule the whole resolution layer turns on: what EA has installed
    governs. Composing to the conventions of a technology EA has not loaded
    produces a diagram that reads as that notation and is not one."""
    absent = _fixture("Alpha", "Landscape")
    by_name = resolve_diagram({"Beta"}, diagram_type="Landscape",
                              bindings=[absent])
    assert by_name.path == "unbound"
    stated = resolve_diagram({"Beta"}, style_ex="MDGDgm=Alpha::Landscape;",
                             bindings=[absent])
    assert stated.path == "not-installed"


def test_a_stated_type_left_unbound_does_not_fall_back_to_a_sibling():
    """A diagram that has said what it is must not be resolved to something
    else.

    The shipped binding leaves two of its technology's five declared diagram
    types out deliberately - a conversation diagram is a graph, and BPEL is an
    export format. Both are drawn on the same base type as the three that ARE
    bound, so a chain that fell through from the qualified key to the base type
    would hand back a sibling: a plausible binding for a diagram that had
    already identified itself as something this library cannot compose.
    """
    resolution = _resolve(style_ex="MDGDgm=BPMN2.0::Conversation;",
                          diagram_type="Analysis")
    assert resolution.path == "unbound"
    assert resolution.diagram_type is None
    assert "Conversation" in resolution.reason
    # Named so an author can see what IS bound.
    assert "Business Process" in resolution.reason


def test_a_diagram_that_identifies_itself_with_neither_column_says_so():
    """Distinct from unbound: nothing was looked up, rather than looked up and
    not found."""
    resolution = _resolve()
    assert resolution.path == "unidentified"
    assert not resolution.resolved


def test_every_resolution_path_agrees_with_its_own_confidence():
    """`path` and `confidence` come from one table, so they cannot drift, and
    `resolved` is read from that table rather than set per answer.

    Derived from `RESOLUTION_PATHS` itself - an inline copy of the table would
    only assert that it equals itself.
    """
    for path, confidence in RESOLUTION_PATHS.items():
        resolution = Resolution(path, "why")
        assert resolution.confidence == confidence
        assert resolution.resolved is (confidence != "none")
    assert RESOLVED_PATHS == {p for p, c in RESOLUTION_PATHS.items()
                              if c != "none"}
    assert "ambiguous" not in RESOLVED_PATHS


def test_a_resolution_path_outside_the_vocabulary_is_refused():
    with pytest.raises(BindingError) as exc:
        Resolution("probably-fine", "why")
    assert "probably-fine" in str(exc.value)


def test_only_a_resolved_answer_carries_a_binding_and_every_answer_carries_why():
    """Swept across one of each kind of answer, so a future path cannot start
    returning half a resolution - a binding with no diagram type is the shape
    that would let a caller compose against the wrong conventions."""
    pair = [_fixture("Alpha", "Landscape"), _fixture("Beta", "Landscape")]
    answers = [
        _resolve(style_ex="MDGDgm=BPMN2.0::Business Process;"),
        _resolve(diagram_type="Business Process"),
        _resolve(diagram_type="Analysis"),
        _resolve(style_ex="MDGDgm=BPMN2::Business Process;"),
        _resolve(style_ex="MDGDgm=BPMN2.0::Conversation;"),
        _resolve(diagram_type="Statechart"),
        _resolve(),
        resolve_diagram({"Alpha", "Beta"}, diagram_type="Landscape",
                        bindings=pair),
        # The base-type path needs a single claimant, which no pair of shipped
        # bindings supplies: theirs all share a base with their siblings.
        resolve_diagram({"Alpha"}, diagram_type="Custom", bindings=pair[:1]),
    ]
    assert {a.path for a in answers} == set(RESOLUTION_PATHS)
    for answer in answers:
        assert (answer.binding is not None) is answer.resolved, answer.path
        assert (answer.diagram_type is not None) is answer.resolved, answer.path
        assert answer.reason.strip(), answer.path


def test_the_bindings_on_hand_are_intersected_with_what_is_installed():
    """Both halves of the intersection, with no shipped id written down.

    This named `UML` as the unbound technology until a UML binding shipped, and
    then `DMN1.1`, which was nearly the same mistake. More bindings land every
    week, so the BOUND id is read from what is on hand, and the unbound one is
    the reference example's own technology - a customer MDG, which nothing here
    will ever ship a binding for.

    With more than one binding shipped this asserts the other half too: the ones
    on disk that are not installed do not appear.
    """
    shipped = sorted(available_bindings(_BINDINGS_DIR))
    assert shipped, "no bindings shipped"
    bound = shipped[0]
    on_hand = bindings_for_technologies({bound, "WBA"}, _BINDINGS_DIR)
    assert set(on_hand) == {bound}
    assert on_hand[bound].technology == bound
    assert bindings_for_technologies(set(), _BINDINGS_DIR) == {}


def test_one_technology_id_passed_as_a_bare_string_is_refused():
    """It would iterate as characters, match nothing, and report the repository
    as having no technology installed - a wrong answer delivered confidently."""
    with pytest.raises(BindingError) as exc:
        resolve_diagram("BPMN2.0", diagram_type="Business Process",
                        directory=_BINDINGS_DIR)
    assert "characters" in str(exc.value)


# ---------------------------------------------------------------------------
# SysML 1.4
# ---------------------------------------------------------------------------
# Two diagram types are bound and seven are not, on purpose. The tests below pin
# the reason for each, and derive every figure from the measurement tool or the
# engine rather than restating it here.
import re  # noqa: E402

import measure_binding as mb  # noqa: E402

_SYSML = "SysML1.4"
_SYSML_BOUND = ("BlockDefinition", "Requirement")
#: The diagram types the binding declines, each classified as (b) an ordinary
#: graph where EA's own layout is acceptable, or (c) EA-semantic, where the
#: diagram type dictates the arrangement.
_SYSML_UNBOUND_GRAPH = ("InternalBlock", "UseCase", "Parametric", "Package",
                        "Activity")
_SYSML_UNBOUND_EA_SEMANTIC = ("Sequence", "StateMachine")
#: Stereotypes the tool reports as unanimous that are not SysML concepts.
#: `NavigationCell` is an EA navigation tile, 38 of 38 at one size on 3 diagrams.
_SYSML_NOT_NOTATION = {"BlockDefinition": {"NavigationCell"}, "Requirement": set()}

_SYSML_MODEL = mb.resolve_model_path(None)
needs_sysml_model = pytest.mark.skipif(
    _SYSML_MODEL is None,
    reason=(f"EAExample.qea not found - pass its location in "
            f"{mb.MODEL_ENV_VAR}; the SysML figures are measured from it"),
)
_SYSML_TEXT = (_BINDINGS_DIR / "sysml1.4.yaml").read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def sysml_known():
    with mb.open_model_copy(_SYSML_MODEL) as conn:
        return mb.list_technologies(conn)


@pytest.fixture(scope="module")
def sysml_measured():
    return {name: mb.measure_binding(_SYSML_MODEL, _SYSML, name)
            for name in _SYSML_BOUND}


def _sysml_section(diagram_type: str) -> str:
    """The text of one diagram type's block, comments included."""
    match = re.search(
        rf"^  {re.escape(diagram_type)}:\n(.*?)(?=^  \S|\Z)", _SYSML_TEXT,
        re.S | re.M)
    assert match, f"no {diagram_type} block in the binding"
    return match.group(1)


def test_the_sysml_binding_loads_and_is_found_by_its_declared_id():
    binding = find_binding(_SYSML)
    assert binding is not None
    assert binding.technology == _SYSML
    assert available_bindings()[_SYSML] == "sysml1.4.yaml"
    assert set(binding.diagram_types) == set(_SYSML_BOUND)
    # Presence, not absence: "no prefix" is a measured statement.
    assert binding.stereotype_prefix == ""


@needs_sysml_model
def test_the_sysml_technology_and_every_diagram_type_it_names_exist_in_the_mdg_data(
        sysml_known):
    """The id is read from the model, and a guessed id fails here.

    The bare family name is not an id, so a binding keyed on it would resolve
    to nothing without complaining. Every diagram type EA carries under the id
    must also be accounted for one way or the other: bound, or declined with a
    stated reason. A type in neither list is a type nobody has classified.
    """
    assert "SysML" not in sysml_known
    assert _SYSML in sysml_known
    binding = find_binding(_SYSML)
    declared = set(binding.diagram_types)
    assert declared <= set(sysml_known[_SYSML])
    declined = set(_SYSML_UNBOUND_GRAPH) | set(_SYSML_UNBOUND_EA_SEMANTIC)
    assert declined <= set(sysml_known[_SYSML])
    assert declared.isdisjoint(declined)
    assert declared | declined == set(sysml_known[_SYSML])


@needs_sysml_model
def test_the_sysml_base_types_are_the_ones_ea_records():
    """`base` is what `create_diagram` is called with, so it is read from the
    diagrams EA holds rather than remembered."""
    bases: dict[str, set[str]] = {}
    with mb.open_model_copy(_SYSML_MODEL) as conn:
        rows = conn.execute("SELECT Diagram_Type, StyleEx FROM t_diagram").fetchall()
    for base, style_ex in rows:
        technology, diagram_type = mb.parse_mdg(style_ex)
        if technology == _SYSML:
            bases.setdefault(diagram_type, set()).add(base)
    binding = find_binding(_SYSML)
    for name, dt in binding.diagram_types.items():
        assert bases[name] == {dt.base}, name


@needs_sysml_model
@pytest.mark.parametrize("diagram_type", _SYSML_BOUND)
def test_the_sysml_sizes_are_the_ones_the_tool_measured(
        diagram_type, sysml_measured):
    m = sysml_measured[diagram_type]
    dt = find_binding(_SYSML).diagram_type(diagram_type)

    assert m.default_size is not None and m.default_size.mode is not None
    assert not m.default_size.low_n
    assert dt.sizing["default"] == {"w": m.default_size.mode[0],
                                    "h": m.default_size.mode[1]}

    # A concept size is stated exactly when the tool found a dominant, non-low-n
    # mode that differs from the default. The tool omits a concept whose mode
    # equals the default, so those are not expected here either.
    #
    # `own_sizing`, NOT `sizing`: this binding is drawn on the base notation, so
    # `sizing` also carries the concepts the substrate measured and this
    # technology says nothing about. Those are not SysML measurements and must
    # not be judged as if they were - the question here is what the tool
    # measured for THIS technology, which is what this file stated.
    expected = {
        stereotype for stereotype, st in m.sizes.items()
        if st.n >= m.min_sample and st.mode is not None
        and st.mode_share >= mb.DOMINANT_SHARE
        and st.mode != m.default_size.mode
    } - _SYSML_NOT_NOTATION[diagram_type]
    assert set(dt.own_sizing) - {"default"} == expected
    for concept in expected:
        # `size_for` answers with a `(w, h)` tuple. The comparison here used to
        # be against a `{"w": ..., "h": ...}` mapping, which a tuple never
        # equals - latent rather than failing only because this technology
        # states no per-concept size, so `expected` is empty and the loop has
        # never run. It would have fired the day one was added.
        assert dt.size_for(concept) == m.sizes[concept].mode


@needs_sysml_model
@pytest.mark.parametrize("diagram_type", _SYSML_BOUND)
def test_the_sysml_spacing_is_the_one_the_tool_measured_and_nothing_more(
        diagram_type, sysml_measured):
    """Only the horizontal gap is stated.

    The vertical gaps of a hierarchy are level-to-level distances, which a bands
    composition sets with `band_gap` and the band padding rather than
    `item_gap_y`, so the vertical population does not measure the key.
    """
    m = sysml_measured[diagram_type]
    dt = find_binding(_SYSML).diagram_type(diagram_type)
    assert not m.h_gap.low_n
    # `own_spacing` is what this file states; `spacing` also carries the vertical
    # gap measured on the base diagram type each of these is drawn on. The
    # vertical gap is unstated HERE for a reason about hierarchies, and that
    # reason is about this technology, not about the canvas underneath it.
    assert dt.own_spacing == {"item_gap_x": round(m.h_gap.median)}
    assert set(dt.spacing) - set(dt.own_spacing) == {"item_gap_y"}


@needs_sysml_model
@pytest.mark.parametrize("diagram_type", _SYSML_BOUND)
def test_the_n_written_beside_each_sysml_figure_is_the_n_measured(
        diagram_type, sysml_measured):
    """The comments carry the sample sizes, so they are checked against the
    tool and cannot drift when the figures are re-measured."""
    m = sysml_measured[diagram_type]
    section = _sysml_section(diagram_type)
    assert f"{m.default_size.mode_count} of n={m.default_size.n}" in section
    assert re.search(rf"n={m.h_gap.n}\b", section)


def test_every_stated_sysml_figure_has_its_n_in_the_comment_above_it():
    """A number without its sample size cannot be judged. The comment block
    directly above (or trailing) each stated `default` and gap must say `n=`."""
    lines = _SYSML_TEXT.splitlines()
    stated = [i for i, line in enumerate(lines)
              if re.match(r"^\s+(default: \{w:|item_gap_[xy]:)", line)]
    assert len(stated) == 4, "expected a default and a gap per bound type"
    for i in stated:
        block = []
        j = i - 1
        while j >= 0 and lines[j].lstrip().startswith("#"):
            block.append(lines[j])
            j -= 1
        context = " ".join(block) + " " + lines[i]
        assert "n=" in context, f"line {i + 1} states a figure with no n"


@pytest.mark.parametrize("diagram_type", _SYSML_BOUND)
def test_grammar_is_implemented_is_the_engines_answer_for_each_sysml_type(
        diagram_type):
    dt = find_binding(_SYSML).diagram_type(diagram_type)
    assert dt.grammar in GRAMMARS
    assert dt.grammar_is_implemented == (dt.grammar in _engine_grammars())
    assert dt.grammar_is_implemented is True


@pytest.mark.parametrize("diagram_type", _SYSML_BOUND)
def test_a_sysml_spec_composes_with_the_measured_sibling_gap(diagram_type):
    dt = find_binding(_SYSML).diagram_type(diagram_type)
    result = compose_layered_bands(
        [{"name": "Level 1", "items": [{"id": 1}, {"id": 2}]}], dt.spec())
    first, second = sorted(result["items"], key=lambda it: it["left"])
    assert first["right"] - first["left"] == dt.sizing["default"]["w"]
    assert second["left"] - first["right"] == dt.spacing["item_gap_x"]


def test_the_declined_sysml_types_resolve_to_no_binding_and_are_classified():
    binding = find_binding(_SYSML)
    for name in _SYSML_UNBOUND_GRAPH + _SYSML_UNBOUND_EA_SEMANTIC:
        assert binding.diagram_type_for_mdgdgm(f"{_SYSML}::{name}") is None
    graph_marker = "UNBOUND, GRAPH (b)"
    semantic_marker = "UNBOUND, EA-SEMANTIC (c)"
    assert graph_marker in binding.notes and semantic_marker in binding.notes
    graph_part, semantic_part = binding.notes.split(graph_marker)[1].split(
        semantic_marker)
    for name in _SYSML_UNBOUND_GRAPH:
        assert name in graph_part and name not in semantic_part
    for name in _SYSML_UNBOUND_EA_SEMANTIC:
        assert name in semantic_part and name not in graph_part


def test_the_sysml_binding_ships_no_local_path():
    assert not re.search(r"[A-Za-z]:\\", _SYSML_TEXT)
    assert "\\Users\\" not in _SYSML_TEXT and "/Users/" not in _SYSML_TEXT


# ---------------------------------------------------------------------------
# UAF / UPDM Framework, and the DMN family that has no binding yet
# ---------------------------------------------------------------------------
# One UAF id is bound and one diagram type under it. The family is eight ids,
# and DMN is one diagram type that is a graph, which the vocabulary cannot yet
# express, so it ships no binding at all and is only checked for its ids here. The tests derive every figure from the
# measurement tool or the model rather than restating it, and pin what was
# deliberately left out.
_DMN = "DMN1.1"
_DMN_TYPE = "DMNDiagram"
_UAF = "UAFP_Framework"
_UAF_TYPE = "UPDM Framework"
#: The eight ids the model carries for the UAF family. One binding binds one id,
#: so seven of them are deliberately unbound.
_UAF_FAMILY = ("UAFP_AV", "UAFP_AcV/PV", "UAFP_Framework", "UAFP_OV",
               "UAFP_SOV", "UAFP_SV/SvcV", "UAFP_StV/CV", "UAFP_TV/StdV")
#: Under the seven unbound ids, the state machines and the sequence diagram are
#: EA-semantic (c); every other type is an ordinary graph (b).
_UAF_EA_SEMANTIC = ("UAFP_OV::OV-6b", "UAFP_OV::OV-6c", "UAFP_SOV::SOV-4b",
                    "UAFP_SV/SvcV::SV-10b")

_DU_MODEL = mb.resolve_model_path(None)
needs_du_model = pytest.mark.skipif(
    _DU_MODEL is None,
    reason=(f"EAExample.qea not found - pass its location in "
            f"{mb.MODEL_ENV_VAR}; the UAF figures are measured from it"),
)
_UAF_TEXT = (_BINDINGS_DIR / "uafp_framework.yaml").read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def du_known():
    with mb.open_model_copy(_DU_MODEL) as conn:
        return mb.list_technologies(conn)


@pytest.fixture(scope="module")
def uaf_measured():
    return mb.measure_binding(_DU_MODEL, _UAF, _UAF_TYPE)


def _du_diagram_rows(technology: str, diagram_type: str) -> list[tuple[int, str, str]]:
    """(id, name, base type) of every diagram the model tags with the pair."""
    out = []
    with mb.open_model_copy(_DU_MODEL) as conn:
        rows = conn.execute(
            "SELECT Diagram_ID, Name, Diagram_Type, StyleEx FROM t_diagram").fetchall()
    for did, name, base, style_ex in rows:
        if mb.parse_mdg(style_ex) == (technology, diagram_type):
            out.append((did, name, base))
    return out


def test_the_uaf_framework_binding_loads_and_is_found_by_its_declared_id():
    uaf = find_binding(_UAF)
    assert uaf is not None and uaf.technology == _UAF
    assert available_bindings()[_UAF] == "uafp_framework.yaml"
    assert set(uaf.diagram_types) == {_UAF_TYPE}
    # Presence, not absence: "no prefix" is a measured statement.
    assert uaf.stereotype_prefix == ""
    assert uaf.diagram_type_for_mdgdgm(f"{_UAF}::{_UAF_TYPE}") is not None


@needs_du_model
def test_the_dmn_and_uaf_ids_and_diagram_types_exist_in_the_mdg_data(du_known):
    """Resolved from the model, so a guessed id fails here.

    The bare family names are not ids. A binding keyed on `DMN` or `UAF` would
    resolve to nothing without complaining.
    """
    for guessed in ("DMN", "DMN1.0", "UAF", "UAFP", "UPDM"):
        assert guessed not in du_known, guessed
    assert _DMN in du_known and _DMN_TYPE in du_known[_DMN]
    assert _UAF in du_known and _UAF_TYPE in du_known[_UAF]
    # The type name carries a space, and a spelling without it is not a type.
    assert "UPDMFramework" not in du_known[_UAF]
    assert set(find_binding(_UAF).diagram_types) <= set(du_known[_UAF])


@needs_du_model
def test_the_uaf_family_is_eight_ids_and_only_the_framework_one_is_bound(du_known):
    """One binding binds one id, so a single UAF binding cannot cover the family.
    The seven unbound ids resolve to nothing, on purpose."""
    in_model = {t for t in du_known if t.startswith("UAFP_")}
    assert in_model == set(_UAF_FAMILY)
    for technology in _UAF_FAMILY:
        assert (find_binding(technology) is not None) == (technology == _UAF), technology


@needs_du_model
def test_the_uaf_framework_base_type_is_the_one_ea_records():
    recorded = {base for _, _, base in _du_diagram_rows(_UAF, _UAF_TYPE)}
    assert recorded == {find_binding(_UAF).diagram_type(_UAF_TYPE).base}


@needs_du_model
def test_the_uaf_framework_size_is_unanimous_and_rests_on_one_diagram(uaf_measured):
    m = uaf_measured
    dt = find_binding(_UAF).diagram_type(_UAF_TYPE)
    assert m.diagrams == 1
    modes = {st.mode for st in m.sizes.values()}
    assert len(modes) == 1 and None not in modes
    (mode,) = modes
    assert all(st.mode_share == 1.0 for st in m.sizes.values())
    assert dt.sizing["default"] == {"w": mode[0], "h": mode[1]}
    total = sum(st.n for st in m.sizes.values())
    assert f"{total} of n={total}" in _UAF_TEXT
    # The tool's own default is low-n, which is why the file explains the choice.
    assert m.default_size.low_n
    assert "LOW-N" in _UAF_TEXT
    # What this file states is the tile size and nothing else. `sizing` also
    # carries the concepts measured on the base diagram type it is drawn on,
    # which are not measurements of this notation.
    assert set(dt.own_sizing) == {"default"}


@needs_du_model
def test_the_uaf_framework_spacing_is_unset_because_one_diagram_supplies_it_all(
        uaf_measured):
    """This file states no gap, and now inherits one instead of getting none.

    THE REASON FOR THE SILENCE CHANGED. The tool used to report no measurable
    neighbors here (n=0), because the tiles are stored as `Text` objects and it
    treated those as furniture; it now promotes furniture that is the diagram's
    own content and measures them. What it measures is refused rather than
    missing: every pair comes from the single diagram this binding rests on, so
    the statistic measures that diagram and not the notation.

    Either way this technology states nothing, and that silence used to reach the
    engine's own gaps. It now reaches the gaps measured on the base diagram type
    this one is drawn on - still not a measurement of THIS diagram type, and the
    honest best available answer for the canvas it is drawn on.
    """
    m = uaf_measured
    for gap in (m.h_gap, m.v_gap):
        assert gap.n and gap.diagrams == 1 and gap.concentrated
        assert gap.top_share == 1.0
    # The figures the file gives for what it refused, checked against the tool
    # rather than restated - a rejected measurement is still a measurement, and a
    # reason that quotes a stale number is worse than no reason.
    text = _prose(_UAF_TEXT)
    for axis, gap in (("horizontal", m.h_gap), ("vertical", m.v_gap)):
        figure = (f"{axis} median {round(gap.median)} across n={gap.n} "
                  f"(mode {gap.mode}, {gap.mode_count} of {gap.n})")
        assert figure in text, figure
    assert f"all {m.h_gap.n + m.v_gap.n} pairs" in text
    dt = find_binding(_UAF).diagram_type(_UAF_TYPE)
    assert dt.own_spacing == {}
    substrate = find_binding(dt.substrate.split("::")[0]).diagram_type(dt.base)
    assert dt.spacing == substrate.spacing != {}
    assert dt.inherited_spacing() == dt.spacing


def test_no_low_n_figure_is_stated_as_active_in_the_uaf_file():
    for line in _UAF_TEXT.splitlines():
        if "LOW-N" in line and not line.lstrip().startswith("#"):
            raise AssertionError(f"active line mentions LOW-N: {line!r}")


@needs_du_model
def test_the_uaf_framework_draws_no_title_so_it_relies_on_the_frame():
    rows = _du_diagram_rows(_UAF, _UAF_TYPE)
    drawn = 0
    with mb.open_model_copy(_DU_MODEL) as conn:
        for did, name, _ in rows:
            found = conn.execute(
                "SELECT o.Name FROM t_diagramobjects x JOIN t_object o "
                "ON o.Object_ID = x.Object_ID WHERE x.Diagram_ID = ? "
                "AND o.Object_Type IN ('Text', 'Note', 'Boundary')",
                (did,)).fetchall()
            if any((n or "").strip().lower() == name.strip().lower() for (n,) in found):
                drawn += 1
    assert drawn == 0
    assert find_binding(_UAF).diagram_type(_UAF_TYPE).title == "frame-header"


@needs_du_model
def test_the_uaf_framework_stores_no_per_diagram_fill_so_fill_is_claimed_not_free():
    """The evidence for `fill` being the stereotype's: no stereotyped element
    carries a fill override."""
    overrides = total = 0
    with mb.open_model_copy(_DU_MODEL) as conn:
        for did, _, _ in _du_diagram_rows(_UAF, _UAF_TYPE):
            for (style,) in conn.execute(
                    "SELECT x.ObjectStyle FROM t_diagramobjects x JOIN t_object o "
                    "ON o.Object_ID = x.Object_ID WHERE x.Diagram_ID = ? "
                    "AND o.Stereotype IS NOT NULL AND o.Stereotype != ''", (did,)):
                total += 1
                match = re.search(r"BCol=(-?\d+)", style or "")
                if match and match.group(1) != "-1":
                    overrides += 1
    assert overrides == 0
    assert f"none of the {total} elements carries a" in " ".join(_UAF_TEXT.split())
    dt = find_binding(_UAF).diagram_type(_UAF_TYPE)
    assert dt.claimed_channels()["fill"]
    assert not dt.channel_is_free("fill")


def test_grammar_is_implemented_is_the_engines_answer_for_the_uaf_framework():
    dt = find_binding(_UAF).diagram_type(_UAF_TYPE)
    assert dt.grammar in GRAMMARS
    assert dt.grammar_is_implemented == (dt.grammar in _engine_grammars())
    assert dt.grammar_is_implemented is True


def test_a_uaf_framework_spec_composes_at_the_stated_size():
    dt = find_binding(_UAF).diagram_type(_UAF_TYPE)
    result = compose_layered_bands(
        [{"name": "Band", "items": [{"id": 1}, {"id": 2}]}], dt.spec())
    for item in result["items"]:
        assert item["right"] - item["left"] == dt.sizing["default"]["w"]
        assert abs(item["bottom"] - item["top"]) == dt.sizing["default"]["h"]


@needs_du_model
def test_every_other_uaf_diagram_type_is_classified_in_the_notes_exactly_once(
        du_known):
    """Bound, or classified (b) or (c) in the notes. A type in none of them is a
    type nobody has looked at, and one in two is a contradiction."""
    notes = " ".join(find_binding(_UAF).notes.split())
    graph_marker = "NOT BOUND, GRAPH (b)."
    semantic_marker = "NOT BOUND, EA-SEMANTIC (c)."
    assert graph_marker in notes and semantic_marker in notes
    graph_part, semantic_part = notes.split(graph_marker)[1].split(semantic_marker)
    unbound = {f"{t}::{d}" for t, types in du_known.items()
               if t.startswith("UAFP_") and t != _UAF for d in types}
    expected_semantic = set(_UAF_EA_SEMANTIC)
    assert expected_semantic <= unbound
    for name in unbound:
        in_graph = re.search(rf"{re.escape(name)}(?![\w-])", graph_part) is not None
        in_semantic = re.search(rf"{re.escape(name)}(?![\w-])", semantic_part) is not None
        assert in_graph != in_semantic, name
        assert in_semantic == (name in expected_semantic), name


def test_the_uaf_timeline_is_recorded_as_ea_semantic_and_is_not_a_bound_key():
    binding = find_binding(_UAF)
    assert "NOT BOUND, TIMELINE (c)" in binding.notes
    for name in binding.diagram_types:
        assert "timeline" not in name.lower() and "AcV-2" not in name
    assert binding.diagram_type_for_mdgdgm("UAFP_AcV/PV::AcV-2") is None
    assert find_binding("UAFP_AcV/PV") is None


@needs_du_model
def test_the_timeline_diagram_type_is_absent_from_the_model_so_it_is_not_keyed(
        du_known):
    """The reason it is a note and not a key: nothing in the model resolves it."""
    for technology, types in du_known.items():
        if technology.startswith("UAFP_"):
            assert not any("AcV-2" in t or "imeline" in t for t in types), technology


def test_the_uaf_binding_ships_no_local_path():
    assert not re.search(r"[A-Za-z]:\\", _UAF_TEXT)
    assert "\\Users\\" not in _UAF_TEXT and "/Users/" not in _UAF_TEXT



# ---------------------------------------------------------------------------
# UML — EA's base notation
# ---------------------------------------------------------------------------
# UML is the one bound notation that is NOT an MDG technology, and most of what
# follows exists because of that. `measure_binding.py` cannot measure it:
# `_attribute` learns a technology's base types from its MDGDgm-tagged diagrams
# and UML has none, and `nearest_neighbor_gaps` rejects any element whose
# Stereotype is empty, which on a plain UML diagram is 94% of them. So these
# tests re-derive every figure from the model using the tool's OWN arithmetic,
# with `Object_Type` put into the stereotype slot - the documented way to
# measure an unstereotyped notation. Nothing here restates a number.
#
# The two rules the binding states are implemented here as `_UML_MIN_N` and
# `_UML_MAX_ONE_DIAGRAM`, and every stated figure is checked against them, so a
# value that only survived by tie order or by one dense diagram fails.

import collections  # noqa: E402
import dataclasses  # noqa: E402

_UML = "UML"
#: Bound as `graph`: EA lays them out, we tidy, and the rest of the binding
#: still applies.
_UML_GRAPH = ("Logical", "Statechart", "Activity", "Package", "Deployment",
              "Use Case", "Component", "CompositeStructure", "Object",
              "Analysis", "Custom")
#: Bound as `ea-semantic`: the type dictates the arrangement, so not producible.
_UML_EA_SEMANTIC = ("Timing",)
_UML_BOUND = _UML_GRAPH + _UML_EA_SEMANTIC
#: Classified (c) and not keyed: no supportable `sizing.default` exists for it,
#: and a resolved diagram type must have one. Inheriting is not a way out HERE -
#: this is the root binding, so there is no substrate underneath it to inherit
#: from. A technology drawn on one of the types above has that option.
_UML_UNBOUND_EA_SEMANTIC = ("Sequence",)
#: Classified (b) and not keyed: every figure is below the threshold.
_UML_UNBOUND_THIN = ("Collaboration", "InteractionOverview")
#: EA's own base canvases rather than UML diagram types: `Custom` is the MDG and
#: extended-profile canvas, `Analysis` EA's own analysis diagram. BOUND, and not
#: because UML publishes them - this binding's job is to be the substrate under
#: every MDG, so the set it must cover is every `base` an MDG diagram type
#: declares, and these are two of the three the shipped bindings sit on. Named so
#: the completeness check below can say which two are here for that reason.
_UML_EA_BASE_CANVAS = {"Analysis", "Custom"}
#: Edge-mounted decorations. A port sits on its parent's border, so the distance
#: from it to the next element measures an attachment offset, not a layout gap.
_UML_DECOR = frozenset({"Port", "ProvidedInterface", "RequiredInterface",
                        "ActionPin", "MessageEndpoint", "EntryPoint",
                        "ExitPoint", "ObjectNode"})
#: A diagram counts as plain UML when it claims no technology and at least half
#: its non-furniture elements carry no stereotype at all.
_UML_BARE_SHARE = 0.5
#: Rule 1. Deliberately the tool's own threshold rather than a second opinion.
_UML_MIN_N = mb.MIN_SAMPLE
#: Rule 2: a gap one diagram supplies more than half of measures that diagram.
_UML_MAX_ONE_DIAGRAM = 0.5
#: Sizes the binding deliberately leaves unset though rule 1 would pass them,
#: each for a reason stated at the point it is omitted. Pinned so that removing
#: the reasoning has to be deliberate.
_UML_OMITTED_BY_JUDGMENT = {
    # Its mode covers 12% over 54 distinct sizes; its median corroborates the
    # default instead.
    ("Activity", "Action"),
    # The varying axis is the fork bar's length, set by how many flows it spans.
    ("Activity", "Synchronization"),
    # Mode and median agree on height and disagree on width: half a measurement.
    ("Deployment", "Node"),
}

_UML_MODEL = mb.resolve_model_path(None)
needs_uml_model = pytest.mark.skipif(
    _UML_MODEL is None,
    reason=(f"EAExample.qea not found - pass its location in "
            f"{mb.MODEL_ENV_VAR}; the UML figures are measured from it"),
)
_UML_TEXT = (_BINDINGS_DIR / "uml.yaml").read_text(encoding="utf-8")


def _uml_selected(conn) -> dict[str, list[tuple[int, list]]]:
    """The plain diagrams per `Diagram_Type`, with EA'S OWN values untouched.

    The selection every figure in the binding rests on: a diagram claims no
    technology and at least half its non-furniture elements carry no stereotype.
    Each diagram keeps its id, because whether one diagram dominates a statistic
    is itself a thing the binding claims.

    Separate from the shim below because two questions need the two views. How
    big a box is has to be asked of `Object_Type`, since this notation stores no
    stereotype; whether it stores one has to be asked of `Stereotype` itself, and
    asking it of the shimmed view is how that check became unfalsifiable.
    """
    raw = {r[0]: r[1] for r in conn.execute(
        "SELECT Diagram_ID, Diagram_Type FROM t_diagram")}
    out: dict[str, list[tuple[int, list]]] = {}
    for d in mb._load_diagrams(conn).values():
        if d.technology:
            continue
        body = [it for it in d.items if not it.is_furniture]
        if not body:
            continue
        if sum(1 for it in body if not it.stereotype) / len(body) < _UML_BARE_SHARE:
            continue
        out.setdefault(raw[d.diagram_id], []).append(
            (d.diagram_id, list(d.items)))
    return out


def _uml_plain(conn) -> dict[str, list[tuple[int, list]]]:
    """Plain-UML diagrams per `Diagram_Type`, concept keyed by `Object_Type`.

    The shim that makes an unstereotyped notation measurable: each item's
    `stereotype` slot is replaced by its `Object_Type`, so the tool's own
    unmodified endpoint filter and statistics apply.
    """
    return {
        diagram_type: [
            (did, [dataclasses.replace(it, stereotype=it.object_type)
                   for it in items])
            for did, items in diagrams
        ]
        for diagram_type, diagrams in _uml_selected(conn).items()
    }


def _uml_sizes(diagrams) -> dict:
    """Modal size per concept: top-level items only, containers excluded."""
    per = collections.defaultdict(list)
    for _, items in diagrams:
        rects = [it.rect for it in items]
        for it in items:
            if it.is_furniture or any(o.contains(it.rect) for o in rects
                                      if o is not it.rect):
                continue
            per[it.stereotype].append((it.rect.width, it.rect.height))
    return {c: mb.size_stat(s) for c, s in per.items()}


def _uml_gaps_by_diagram(diagrams, axis) -> dict[int, list[int]]:
    concepts = {it.stereotype for _, items in diagrams for it in items
                if it.stereotype and it.stereotype not in _UML_DECOR}
    return {did: mb.nearest_neighbor_gaps(
        items, axis, endpoint_stereotypes=concepts, rule="strict")[0]
        for did, items in diagrams}


def _uml_gap(diagrams, axis):
    """`(stat, share the densest single diagram contributes)`."""
    by_diagram = _uml_gaps_by_diagram(diagrams, axis)
    pooled = [g for gaps in by_diagram.values() for g in gaps]
    if not pooled:
        return mb.gap_stat([]), 0.0
    densest = max(by_diagram.values(), key=len)
    return mb.gap_stat(pooled), len(densest) / len(pooled)


def _uml_statable_gap(diagrams, axis):
    """The value the two rules allow to be stated, or None."""
    stat, share = _uml_gap(diagrams, axis)
    if not stat.n or stat.low_n or share > _UML_MAX_ONE_DIAGRAM:
        return None
    return round(stat.median)


@pytest.fixture(scope="module")
def uml_plain():
    with mb.open_model_copy(_UML_MODEL) as conn:
        return _uml_plain(conn)


@pytest.fixture(scope="module")
def uml_selected():
    with mb.open_model_copy(_UML_MODEL) as conn:
        return _uml_selected(conn)


@pytest.fixture(scope="module")
def uml_known():
    with mb.open_model_copy(_UML_MODEL) as conn:
        return mb.list_technologies(conn)


def test_the_uml_binding_loads_and_is_found_by_its_declared_id():
    binding = find_binding(_UML)
    assert binding is not None
    assert binding.technology == _UML
    assert available_bindings()[_UML] == "uml.yaml"
    assert set(binding.diagram_types) == set(_UML_BOUND)
    # Presence, not absence: see the prefix tests below.
    assert binding.stereotype_prefix == ""


@needs_uml_model
def test_uml_is_deliberately_not_an_mdg_technology_id(uml_known):
    """The inverse of the guessed-id test every other binding gets.

    `list_technologies` reads ids out of `MDGDgm`, and plain UML has none, so
    `UML` must be ABSENT here. If it ever appears, EA has begun tagging base
    diagrams and this binding's whole resolution story needs rewriting.
    """
    assert _UML not in uml_known
    # The only real id containing "UML" covers two behavioral types, so it is
    # not what a UML binding can be keyed on. Its spelling is a trap too:
    # `State Machine` with a space, where plain UML's type is `Statechart`.
    assert set(uml_known["UML Behavioral"]) == {"Sequence", "State Machine"}
    assert {k for k in uml_known if k.startswith("UML")} == {"UML Behavioral"}


@needs_uml_model
def test_every_uml_diagram_type_named_anywhere_is_a_real_ea_diagram_type(
        uml_plain):
    """Catches a misremembered name, which is this binding's worst failure mode.

    A Class diagram is `Logical` and a State Machine diagram is `Statechart`;
    neither is guessable and a wrong name matches nothing without complaining.
    Every name the binding uses - bound or classified - must be a real
    `Diagram_Type`, and every plain-UML type the model carries must be accounted
    for one way or the other, so nothing goes unclassified by accident.
    """
    named = set(_UML_BOUND) | set(_UML_UNBOUND_EA_SEMANTIC) | set(
        _UML_UNBOUND_THIN)
    found = set(uml_plain)
    assert named <= found
    # Every plain diagram type the model carries is now accounted for, where two
    # of them used to be listed as neither bound nor classified: the two EA base
    # canvases, which are bound because MDG diagram types are drawn on them.
    assert found == named
    assert _UML_EA_BASE_CANVAS <= set(find_binding(_UML).diagram_types)
    # The specification's own spellings are NOT what EA stores.
    for wrong in ("Class", "StateMachine", "Communication", "UseCase"):
        assert wrong not in found
    assert "Use Case" in found


@needs_uml_model
def test_the_uml_prefix_is_empty_because_the_elements_carry_no_stereotype(
        uml_selected):
    """`stereotype_prefix: ""` is a measured statement, not an omission.

    ASKED OF EA'S OWN `Stereotype` COLUMN. The previous version of this test read
    the shimmed view and compared `it.stereotype` with `it.object_type` - which
    `_uml_plain` had just made equal for every element - so every element counted
    as bare, the ratio was 1.0 by construction, and the assertion could not fail.
    It read as a 94% measurement and measured nothing.

    The provenance the binding states is checked here too, because the figures
    belong to two different selections and an earlier revision of the file gave
    one number from each in a single sentence.
    """
    def totals(diagram_types):
        body = [it for name in diagram_types for _, items in uml_selected[name]
                for it in items if not it.is_furniture]
        return len(body), sum(1 for it in body if not it.stereotype)

    every = set(uml_selected)
    diagrams = sum(len(d) for d in uml_selected.values())
    elements, bare = totals(every)
    assert bare / elements > 0.9
    uml_elements, uml_bare = totals(every - _UML_EA_BASE_CANVAS)
    canvas_elements, canvas_bare = totals(_UML_EA_BASE_CANVAS)
    canvas_diagrams = sum(len(uml_selected[n]) for n in _UML_EA_BASE_CANVAS)
    text = _prose(_UML_TEXT)
    for figure in (
            f"{diagrams} diagrams carrying {elements:,} non-furniture elements "
            f"across {len(every)} ",
            f"{diagrams - canvas_diagrams} diagrams, "
            f"{len(every - _UML_EA_BASE_CANVAS)} types, {uml_elements:,} elements",
            f"{canvas_diagrams} diagrams, {len(_UML_EA_BASE_CANVAS)} types, "
            f"{canvas_elements:,} elements",
            f"{bare:,} of the {elements:,} non-furniture elements",
            f"{uml_bare:,} of {uml_elements:,} ({uml_bare / uml_elements:.1%})",
            f"{canvas_bare} of {canvas_elements} "
            f"({canvas_bare / canvas_elements:.1%})"):
        assert figure in text, figure
    binding = find_binding(_UML)
    assert binding.stereotype_prefix == ""
    # Identity both ways: for this notation the concept name IS the stored value.
    for concept in ("Class", "TimeLine", "Statechart"):
        assert binding.stereotype_for(concept) == concept
        assert binding.concept_for(concept) == concept


def test_an_empty_uml_prefix_is_not_inherited_from_a_prefixed_parent(tmp_path):
    """The presence check the three UML-derived families depend on.

    A child that OMITS `stereotype_prefix` inherits the parent's; a child that
    declares `""` has said something and must keep it. Without the distinction a
    binding extending a prefixed parent would silently acquire the prefix and
    every stereotype lookup would go hunting for `Parent_Class`.
    """
    body = ("diagram_types:\n  T:\n    grammar: graph\n"
            "    title: drawn\n    sizing: {default: {w: 10, h: 10}}\n"
            "    routing: {default: Direct}\n    channels: {fill: ~}\n")
    (tmp_path / "parent.yaml").write_text(
        "technology: Parent\nstereotype_prefix: Parent_\n" + body,
        encoding="utf-8")
    (tmp_path / "stated.yaml").write_text(
        'technology: Stated\nstereotype_prefix: ""\nextends: Parent\n' + body,
        encoding="utf-8")
    (tmp_path / "silent.yaml").write_text(
        "technology: Silent\nextends: Parent\n" + body, encoding="utf-8")
    stated = load_binding(tmp_path / "stated.yaml")
    silent = load_binding(tmp_path / "silent.yaml")
    assert stated.stereotype_prefix == ""
    assert stated.stereotype_for("Class") == "Class"
    assert silent.stereotype_prefix == "Parent_"
    assert silent.stereotype_for("Class") == "Parent_Class"


#: One diagram type, valid, with the prefix line left for a caller to fill in.
#: Used by the per-diagram-type prefix tests below so each one states only the
#: thing it is about.
_PREFIX_TYPE = ("diagram_types:\n  T:\n    grammar: graph\n"
                "    title: drawn\n    sizing: {{default: {{w: 10, h: 10}}}}\n"
                "    routing: {{default: Direct}}\n    channels: {{fill: ~}}\n"
                "{prefix}")


def _prefix_doc(technology_prefix: str = "", type_prefix: str = "") -> str:
    head = f"technology: WBA\n{technology_prefix}"
    return head + _PREFIX_TYPE.format(prefix=type_prefix)


def test_a_diagram_type_inherits_the_technologys_prefix_when_it_states_none():
    """The case every shipped single-prefix binding is: one statement, every type.

    This is what keeps `ArchiMate3` working unchanged after the schema grew a
    second scope - all five of its diagram types resolve to `ArchiMate_` without
    any of them saying so - and `own_stereotype_prefix` is `None`, which is how a
    report tells that fallback from a declared value.
    """
    binding = load_binding_text(_prefix_doc('stereotype_prefix: WBA_\n'))
    dt = binding.diagram_type("T")
    assert dt.stereotype_prefix == "WBA_"
    assert dt.own_stereotype_prefix is None
    assert dt.stereotype_prefix_is_inherited
    assert dt.stereotype_prefix_provenance == "WBA"
    assert dt.stereotype_for("Thing") == "WBA_Thing"
    assert dt.concept_for("WBA_Thing") == "Thing"
    # And through the binding, with and without the diagram type named.
    assert binding.stereotype_for("Thing") == "WBA_Thing"
    assert binding.stereotype_for("Thing", "T") == "WBA_Thing"


def test_a_diagram_types_own_prefix_wins_over_the_technologys():
    """`StrategyMap`'s case, reduced to the schema: the type's statement wins."""
    binding = load_binding_text(
        _prefix_doc('stereotype_prefix: WBA_\n',
                    "    stereotype_prefix: SM_\n"))
    dt = binding.diagram_type("T")
    assert dt.own_stereotype_prefix == "SM_"
    assert dt.stereotype_prefix == "SM_"
    assert not dt.stereotype_prefix_is_inherited
    assert dt.stereotype_prefix_provenance == "WBA::T"
    assert binding.stereotype_for("Objective", "T") == "SM_Objective"
    assert binding.concept_for("SM_Objective", "T") == "Objective"
    # The technology's own statement is untouched by the override.
    assert binding.stereotype_for("Objective") == "WBA_Objective"


def test_a_diagram_type_declaring_an_empty_prefix_is_not_given_the_technologys():
    """The presence check, at the second scope. `""` is a STATEMENT here too.

    A technology that prefixes can hold a diagram type whose stereotypes are
    stored bare - `TOGAF Diagrams` is this case inverted - and `or` in the
    resolution would silently hand it the technology's prefix, sending every
    lookup after a name that exists nowhere. `~` means the same thing as `""`,
    for the same reason it does at technology scope.
    """
    for spelling in ('    stereotype_prefix: ""\n', "    stereotype_prefix: ~\n"):
        binding = load_binding_text(
            _prefix_doc('stereotype_prefix: WBA_\n', spelling))
        dt = binding.diagram_type("T")
        assert dt.own_stereotype_prefix == "", spelling
        assert dt.stereotype_prefix == "", spelling
        assert not dt.stereotype_prefix_is_inherited, spelling
        assert dt.stereotype_for("Mission") == "Mission", spelling
        assert binding.stereotype_for("Mission", "T") == "Mission", spelling
        assert binding.stereotype_for("Mission") == "WBA_Mission", spelling


def test_a_diagram_types_prefix_is_rejected_when_it_is_not_a_string():
    """Checked before coercion, at both scopes, for the reason `_validate_prefix`
    records: `or ""` would turn `0` into a pass."""
    for bad in ("    stereotype_prefix: 3\n", "    stereotype_prefix: [a]\n"):
        with pytest.raises(BindingError, match="stereotype_prefix"):
            load_binding_text(_prefix_doc(type_prefix=bad))


def test_a_diagram_type_never_inherits_its_substrates_prefix(tmp_path):
    """THE ASYMMETRY, AS A TEST. Silence means the TECHNOLOGY, not the canvas.

    A prefix says whose MDG named the stereotype, so a substrate - a diagram type
    in the PARENT technology - is the wrong place to fall back to. Here the parent
    prefixes and the child does not: the child's diagram type must resolve to the
    CHILD's `""`, not to `Parent_`, even though it takes the parent's sizing and
    spacing through `base` in the same breath. Both halves are asserted, because a
    merge that picked up the prefix would otherwise look like working inheritance.
    """
    parent = ("technology: WBA\nstereotype_prefix: WBA_\n"
              "diagram_types:\n  Logical:\n    grammar: graph\n"
              "    title: drawn\n"
              "    sizing: {default: {w: 90, h: 70}}\n"
              "    spacing: {item_gap_x: 56}\n"
              "    routing: {default: Direct}\n    channels: {fill: ~}\n")
    child = ('technology: WBA-Overlay\nstereotype_prefix: ""\nextends: WBA\n'
             "diagram_types:\n  View:\n    base: Logical\n"
             "    grammar: layered-bands\n    title: drawn\n"
             "    sizing: {}\n"
             "    routing: {default: Direct}\n    channels: {fill: ~}\n")
    (tmp_path / "wba.yaml").write_text(parent, encoding="utf-8")
    (tmp_path / "wba-overlay.yaml").write_text(child, encoding="utf-8")
    dt = load_binding(tmp_path / "wba-overlay.yaml").diagram_type("View")
    # The substrate WAS found, so the sizing and spacing really did come across.
    assert dt.substrate == "WBA::Logical"
    assert dt.sizing["default"] == {"w": 90, "h": 70}
    assert dt.spacing["item_gap_x"] == 56
    # And the prefix did not.
    assert dt.stereotype_prefix == ""
    assert dt.stereotype_for("Thing") == "Thing"
    assert dt.stereotype_prefix_provenance == "WBA-Overlay"


def test_naming_an_undeclared_diagram_type_in_a_prefix_lookup_raises():
    """It must not answer at technology scope instead.

    Answering would return the unprefixed concept name - a plausible string that
    matches nothing - for what is really a typo, which is the silent miss this
    slot exists to prevent. Every other lookup on `Binding` raises; so does this.
    """
    binding = load_binding_text(_prefix_doc('stereotype_prefix: WBA_\n'))
    for call in (lambda: binding.stereotype_for("Thing", "Nope"),
                 lambda: binding.concept_for("WBA_Thing", "Nope"),
                 lambda: binding.prefix_for("Nope")):
        with pytest.raises(BindingError, match="no diagram type"):
            call()


@needs_uml_model
@pytest.mark.parametrize("diagram_type", _UML_BOUND)
def test_the_uml_default_size_is_a_mode_the_measurement_supports(
        diagram_type, uml_plain):
    """`sizing.default` is mandatory, so each one must trace to a real mode.

    Recomputed from the model rather than compared against a copy of itself. The
    default is not required to be the commonest concept's mode - Activity takes
    its default from `Activity` rather than `Action`, for a reason stated in the
    file - but it must equal SOME concept's supported modal size.
    """
    stats = _uml_sizes(uml_plain[diagram_type])
    dt = find_binding(_UML).diagram_type(diagram_type)
    supported = {st.mode for st in stats.values()
                 if st.mode is not None and st.n >= _UML_MIN_N}
    assert dt.size_for() in supported, diagram_type


@needs_uml_model
@pytest.mark.parametrize("diagram_type", _UML_BOUND)
def test_every_uml_concept_size_is_the_measured_mode_and_none_is_unsupported(
        diagram_type, uml_plain):
    """No concept size may be stated that rule 1 refuses, and each one stated
    must equal the mode the model yields."""
    stats = _uml_sizes(uml_plain[diagram_type])
    dt = find_binding(_UML).diagram_type(diagram_type)
    for concept, size in dt.sizing.items():
        if concept == "default":
            continue
        assert concept in stats, f"{diagram_type}.{concept} is not in the model"
        st = stats[concept]
        assert st.n >= _UML_MIN_N, f"{diagram_type}.{concept} is low-n"
        assert st.mode is not None, f"{diagram_type}.{concept} has no mode"
        assert dt.size_for(concept) == st.mode


@needs_uml_model
@pytest.mark.parametrize("diagram_type", _UML_BOUND)
def test_the_uml_spacing_is_exactly_what_the_two_rules_allow(
        diagram_type, uml_plain):
    """Both directions: every stated gap is the measured median, and every gap
    the rules refuse is absent. The refusals are the point - Component, Object
    and Timing each lose a value that the arithmetic alone would have handed
    over."""
    diagrams = uml_plain[diagram_type]
    dt = find_binding(_UML).diagram_type(diagram_type)
    expected = {}
    for axis, key in (("h", "item_gap_x"), ("v", "item_gap_y")):
        allowed = _uml_statable_gap(diagrams, axis)
        if allowed is not None:
            expected[key] = allowed
    assert dt.spacing == expected, diagram_type


@needs_uml_model
def test_the_three_rejected_uml_gaps_are_rejected_for_the_stated_reason(
        uml_plain):
    """Pins the REASON, not just the omission.

    Each of these three would pass rule 1 and is refused by rule 2. If one
    stopped being one diagram's doing, the omission would need a different
    reason - or would no longer be one.
    """
    for diagram_type, axis in (("Component", "v"), ("Object", "v"),
                               ("Timing", "v")):
        stat, share = _uml_gap(uml_plain[diagram_type], axis)
        assert not stat.low_n, (diagram_type, axis)
        assert share > _UML_MAX_ONE_DIAGRAM, (diagram_type, axis, share)
        key = "item_gap_y" if axis == "v" else "item_gap_x"
        binding_dt = find_binding(_UML).diagram_type(diagram_type)
        assert key not in binding_dt.spacing
        # Nor may the tempting value appear anywhere as a stated one.
        assert f"{key}: {round(stat.median)}\n" not in _UML_TEXT
    # Timing's horizontal gap is absent for the other reason entirely: no sample.
    stat, _ = _uml_gap(uml_plain["Timing"], "h")
    assert stat.n == 0


@needs_uml_model
def test_the_sizes_uml_omits_by_judgment_are_still_really_there(uml_plain):
    """The three sizes left unset despite passing rule 1.

    Each is omitted for a reason written beside it, and each omission is a
    choice rather than an oversight - so the test asserts both that the
    measurement exists and that the binding does not state it.
    """
    for diagram_type, concept in _UML_OMITTED_BY_JUDGMENT:
        st = _uml_sizes(uml_plain[diagram_type])[concept]
        assert st.n >= _UML_MIN_N and st.mode is not None
        assert concept not in find_binding(_UML).diagram_type(
            diagram_type).sizing
        # A weak mode is exactly what a reader would otherwise have trusted.
        assert st.mode_share < 0.5 or st.mode != tuple(
            int(v) for v in st.median)


def test_every_stated_uml_figure_has_its_n_in_the_comment_above_it():
    """A number without its sample size cannot be judged."""
    lines = _UML_TEXT.splitlines()
    stated = [i for i, line in enumerate(lines)
              if re.match(r"^\s+(?:default|[A-Z]\w*): \{w:|^\s+item_gap_[xy]:",
                          line)]
    assert len(stated) >= 20, "expected a figure per size and per gap"
    for i in stated:
        block = []
        j = i - 1
        while j >= 0 and lines[j].lstrip().startswith("#"):
            block.append(lines[j])
            j -= 1
        context = " ".join(block) + " " + lines[i]
        assert "n=" in context, f"line {i + 1} states a figure with no n"


@needs_uml_model
def test_the_figures_the_notes_record_for_the_unbound_types_are_recomputable(
        uml_plain):
    """Sequence is classified on evidence, and the evidence is checked.

    Its even lifeline pitch is the reason it is (c) rather than (b), so the
    figure quoted for it is recomputed rather than trusted.
    """
    notes = find_binding(_UML).notes
    sequence = _uml_gap(uml_plain["Sequence"], "h")[0]
    assert f"{sequence.mode} in {sequence.mode_count} of n={sequence.n}" in notes
    # And no element type on a sequence diagram has a modal size at all, which
    # is the other half of why it cannot be keyed: a resolved diagram type must
    # have a `sizing.default`, and the root binding has nothing to inherit one
    # from.
    for st in _uml_sizes(uml_plain["Sequence"]).values():
        assert st.mode is None or st.low_n
    # The two thin types have nothing statable either.
    for diagram_type in _UML_UNBOUND_THIN:
        stats = _uml_sizes(uml_plain[diagram_type])
        assert all(st.low_n for st in stats.values()), diagram_type


@pytest.mark.parametrize("diagram_type", _UML_BOUND)
def test_grammar_is_implemented_is_the_engines_answer_for_each_uml_type(
        diagram_type):
    """`graph` and `ea-semantic` are both unimplemented and must stay that way:
    neither has a composer, because neither is ours to compose. What separates
    them is producibility, which is a different question."""
    dt = find_binding(_UML).diagram_type(diagram_type)
    assert dt.grammar in GRAMMARS
    assert dt.grammar_is_implemented == (dt.grammar in _engine_grammars())
    assert dt.grammar_is_implemented is False
    assert dt.geometry_is_composed is False
    assert dt.grammar_is_producible is (diagram_type in _UML_GRAPH)


def test_the_uml_grammars_are_only_the_two_that_place_nothing():
    """No UML type claims a composed grammar. A class diagram composed as a
    treemap is the failure this guards against: parking a graph under
    `computed-geometry` would start reporting itself composable the day that
    composer ships."""
    binding = find_binding(_UML)
    assert {dt.grammar for dt in binding.diagram_types.values()} == {
        "graph", "ea-semantic"}
    for name in _UML_GRAPH:
        assert binding.diagram_type(name).grammar == "graph"
    for name in _UML_EA_SEMANTIC:
        assert binding.diagram_type(name).grammar == "ea-semantic"
    assert "computed-geometry" not in _UML_TEXT.split("notes:")[0]


def test_the_declined_uml_types_are_each_classified_in_the_notes():
    """The durable half of the deliverable: a reason per unbound type, so that
    an omission is never indistinguishable from an oversight."""
    binding = find_binding(_UML)
    for name in _UML_UNBOUND_EA_SEMANTIC:
        assert f"NOT BOUND, EA-SEMANTIC (c) — {name}" in binding.notes
    thin = binding.notes.split("NOT BOUND, BELOW THRESHOLD (b)")[1]
    for name in _UML_UNBOUND_THIN:
        assert name in thin, name
    # None of the three is a key, so none of them resolves to a binding.
    for name in _UML_UNBOUND_EA_SEMANTIC + _UML_UNBOUND_THIN:
        assert name not in binding.diagram_types
        assert binding.diagram_type_for_mdgdgm(f"{_UML}::{name}") is None


def test_uml_leaves_fill_unclaimed_which_is_what_lets_it_be_free():
    """UML fixes the notation, not the color: a class is a compartmented
    rectangle whatever it is filled with. So `fill: ~` is a statement about the
    notation, and §5.2's one exception applies - an unclaimed fill may be free.
    """
    for name in _UML_BOUND:
        dt = find_binding(_UML).diagram_type(name)
        # `fill: ~` means unclaimed, so it is absent from the claimed map rather
        # than present with a null meaning - the key is only added when fill is
        # spoken for. (`references/bindings.md` §6 reads as though `fill` is
        # always included; it is included only when claimed.)
        assert "fill" not in dt.claimed_channels(), name
        assert dt.channels["fill"] is None, name
        assert dt.channel_is_free("fill"), name
        # Position, size and line style are spoken for on every UML diagram.
        for channel in ("position", "size", "line_style"):
            assert not dt.channel_is_free(channel), (name, channel)


def test_uml_claims_line_style_everywhere_because_dashed_is_normative():
    """The claim that is about the notation rather than the diagram type: a
    dashed connector is a dependency or a realization, so line style is never a
    free channel in UML."""
    for name in _UML_BOUND:
        claimed = find_binding(_UML).diagram_type(name).claimed_channels()
        assert "line_style" in claimed and claimed["line_style"].strip()


@needs_uml_model
def test_a_plain_uml_diagram_resolves_through_diagram_type_not_mdgdgm():
    """How this binding is reached at all.

    `MDGDgm` is empty on every plain UML diagram, so the qualified path cannot
    answer and the `diagram-type` path must. The qualified key this binding
    WOULD build matches nothing in any model.
    """
    installed = [_UML, "ArchiMate3", "SysML1.4"]
    for name in _UML_BOUND:
        resolution = resolve_diagram(installed, style_ex="MDGDgm=;",
                                     diagram_type=name)
        assert resolution.resolved, name
        assert resolution.path == "diagram-type", name
        assert resolution.technology == _UML
        assert RESOLUTION_PATHS[resolution.path] == "inferred"
    keys = {find_binding(_UML).diagram_type(n).mdg_diagram_type
            for n in _UML_BOUND}
    assert "UML::Logical" in keys
    with mb.open_model_copy(_UML_MODEL) as conn:
        style_values = [r[0] or "" for r in conn.execute(
            "SELECT StyleEx FROM t_diagram")]
    for key in keys:
        assert not any(key in value for value in style_values), key


@needs_uml_model
def test_the_uml_base_types_are_the_diagram_type_ea_records():
    """For a base notation there is no MDG layer, so `base` and the key are the
    same string - and `base` is what `create_diagram` takes. Read from the model
    rather than remembered, which is what catches `Use Case` losing its space.
    """
    with mb.open_model_copy(_UML_MODEL) as conn:
        recorded = {r[0] for r in conn.execute(
            "SELECT DISTINCT Diagram_Type FROM t_diagram")}
    for name, dt in find_binding(_UML).diagram_types.items():
        assert dt.base == name, name
        assert dt.base in recorded, name


def test_the_uml_binding_ships_no_local_path():
    assert not re.search(r"[A-Za-z]:\\", _UML_TEXT)
    assert "\\Users\\" not in _UML_TEXT and "/Users/" not in _UML_TEXT

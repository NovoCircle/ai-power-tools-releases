#!/usr/bin/env python3
"""Why there is no data-model binding, pinned so the reasons stay checkable.

Run from the repository root:

    python -m pytest ea-diagram-composition/tools/test_bindings_datamodel.py -q

The DataModel family - three corpus rows, two drawn in IDEF1X notation and one in
Information Engineering - was brought forward as the last measurable remainder of
the binding programme and came back UNBINDABLE. Not "not done yet": the diagrams
exist, they are tagged, they were measured, and the measurement refuses the one
figure a binding cannot do without. An empty finding is easy to mistake for an
oversight, so each reason is a test rather than a note in a backlog item.

The first finding is not a refusal at all - it is that the family is ONE diagram
type and the three notations are a display setting on it:

0. THE TECHNOLOGY IS `Extended` AND THE DIAGRAM TYPE IS `Data Modeling`. Twelve
   diagrams in the reference model carry an `MDGDgm` naming technology `Extended`
   and diagram type `Data Modeling`, and all twelve are based on `Logical`. IDEF1X, Information Engineering and UML are NOT
   technologies, not diagram types and not stereotype sets: each is the value of
   `TConnectorNotation` in that diagram's own `t_diagram.StyleEx`, a per-diagram
   rendering choice for the connector ends. Of the twelve, 7 read `IDEF1X`, 2
   `Information Engineering` and 3 `UML 2.1`. So the catalog's note that the
   IDEF1X and IE variants hold an identical element set and differ only in
   connector rendering is not merely true, it is structural - and the three rows
   were never three bindings, or even three diagram types.

Then the refusals, which apply to that one diagram type:

1. THE NOTATION'S CENTRAL ELEMENT HAS NO MODAL SIZE AT ALL. `table` is 21 of the
   29 stereotyped elements on those twelve diagrams and it has 21 DISTINCT sizes:
   no mode at any share, which is the most extreme no-mode population measured
   anywhere in this programme. The reason is structural rather than a shortage of
   diagrams - a data-model table is drawn to fit its column list, so its box is
   content and not convention - and more diagrams would produce more distinct
   sizes rather than a mode.

2. THE POOLED MODE IS AN ACCIDENT, AND IT IS NOT A TABLE. `sizing.default` would
   have to be 177x70, the pooled mode at 2 of n=29 - a 6.9% share against the 50%
   the tool itself requires before it will emit a per-concept size - over 28
   distinct sizes, against a median of 211x271. Both elements at that size are
   singletons of other concepts: one `view` and one `function`, each n=1. Every
   one of the 21 tables is larger than it in both axes.

3. AND INHERITING IS WORSE HERE, WHICH IS THE PART THAT NEEDED DECIDING. The
   schema lets a diagram type omit `sizing` and take the substrate's figure,
   traceably, and `base: Logical` is measured - so the mechanism was available and
   was not used. UML's `Logical` default is 90x70, which is smaller than the
   smallest table on any of these diagrams (183x224) in both axes. No shipped
   binding inherits its default today, so this would have been the mechanism's
   first use, in the one place where the inherited figure is contradicted by every
   observation of the notation drawn on that canvas. `default_size_is_inherited`
   would have reported the figure as borrowed and a consumer would still have
   composed every table at a third of its measured size.

WHAT IS MEASURABLE, AND WHY IT CANNOT CARRY A BINDING ON ITS OWN: both gap
populations clear the concentration rule - n=17 horizontal and n=16 vertical, the
densest diagram supplying 47% and 50%, neither more than half - and both are well
under `MIN_SAMPLE_GAP`, so both are provisional. `sizing.default` is mandatory in
the resolved diagram type, so a document stating only gaps does not load. Two
provisional gaps are not worth a fabricated box size.

WHAT WOULD CHANGE THE ANSWER is not more diagrams. It is a schema that can say
"this notation sizes its boxes from their contents" - a per-concept rule rather
than a figure - or a caller that computes a table's box from its column list the
way `spec(names=...)` already computes a width from a name. Either is a finding
about the engine, filed rather than worked around here.

A NOTE FOR WHOEVER REVISITS THIS. The corpus audit claims a binding for a family by
matching the normalized technology id against that family's prefixes, and `Extended`
normalizes to `extended`. Its `DataModel` family matches `datamodel` and
`datamodeling`, neither of which `Extended` starts with - so an `Extended` binding
would be claimed by whichever family lists `extended` and NOT by `DataModel`, and
these three rows would stay uncredited until the audit says otherwise. That is the
audit's line to write, not this skill's; it is recorded here because a binding
merged without it would read as unclaimed and the coverage axis would understate
silently, which is exactly what the family prefixes exist to prevent. The audit's
own families move, so check them rather than trusting this paragraph.

THE REFUSAL IS THE WHOLE FILE, NOT ONE DIAGRAM TYPE IN IT. `Extended` declares six
diagram types and two of them carry corpus rows. `Dashboard`, the other one, is
refused by the tool outright - no unique modal size in the pool at all, over 43
diagrams - for the same underlying reason: a chart is sized to what it plots
(`SSDynamicChart`, 36 observations, 34 distinct sizes). So there is no `extended.yaml`
worth shipping for either row.

THE LAST UNBOUND TOGAF ROW IS RECORDED HERE TOO, at the end, because it is the
same kind of refusal as SysPhS's first and had nowhere else to live: `FEAF
Diagrams` is absent from the reference model entirely.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

import pytest

_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

import measure_binding as mb  # noqa: E402
from bindings import (  # noqa: E402
    BindingError,
    find_binding,
    load_binding_text,
)

#: The technology id EA registers for its extended diagram set, read from
#: `measure_binding.py --list` rather than guessed. It is NOT `DataModel`,
#: `DataModeling` or `IDEF1X`, and a lookup on any of those resolves to nothing.
EXTENDED = "Extended"

#: The one diagram type of it this family is drawn on. With a space.
DATA_MODELING = "Data Modeling"

#: `t_diagram.StyleEx` key that carries the connector notation, and the three
#: values the data-modeling diagrams take. This is where IDEF1X lives.
NOTATION_KEY = "TConnectorNotation"

#: The other technology id behind an unbound row, absent from the model.
FEAF = "FEAF Diagrams"

_BINDINGS = _HERE.parent / "bindings"
_TOGAF_TEXT = (_BINDINGS / "togaf-diagrams.yaml").read_text(encoding="utf-8")

MODEL = mb.resolve_model_path(None)

needs_model = pytest.mark.skipif(
    MODEL is None,
    reason=("EAExample.qea not found - pass its location in "
            f"{mb.MODEL_ENV_VAR}; a machine without EA has nothing to measure"),
)


def _style_notation(style_ex: str) -> str | None:
    found = re.search(rf"{NOTATION_KEY}=([^;]*)", style_ex or "")
    return found.group(1) if found else None


def _data_modeling_diagrams(conn):
    return list(conn.execute(
        "select Diagram_ID, Name, Diagram_Type, StyleEx from t_diagram "
        f"where StyleEx like '%MDGDgm={EXTENDED}::{DATA_MODELING}%'"))


# ---------------------------------------------------------------------------
# 0. One diagram type, three connector notations
# ---------------------------------------------------------------------------
@needs_model
def test_the_data_model_technology_is_extended_and_not_a_datamodel_id():
    """The id is not guessable and the plausible guesses resolve to nothing.

    Pinned first because every other claim in this file is about the wrong
    population if this one is wrong, and because the family's NAME in the corpus
    and in the backlog item is `DataModel`, which EA registers nothing under.
    """
    with mb.open_model_copy(MODEL) as conn:
        technologies = mb.list_technologies(conn)
    assert EXTENDED in technologies
    assert DATA_MODELING in technologies[EXTENDED]
    for guess in ("DataModel", "DataModeling", "IDEF1X",
                  "Information Engineering"):
        assert guess not in technologies, guess


@needs_model
def test_idef1x_and_information_engineering_are_a_style_flag_not_a_notation_set():
    """THE FINDING THAT DISSOLVES THE THREE ROWS INTO ONE DIAGRAM TYPE.

    All twelve diagrams are one technology, one diagram type and one base type.
    What differs between the IDEF1X rows and the Information Engineering row is a
    single `StyleEx` key that tells EA how to draw the connector ends. Asserted
    over the whole model, not just these diagrams, so that the claim "this is a
    per-diagram display setting" rests on the key's own distribution: 1,087
    diagrams read `UML 2.1` and every diagram in the model carries the key or
    nothing at all.
    """
    with mb.open_model_copy(MODEL) as conn:
        scope = _data_modeling_diagrams(conn)
        every = list(conn.execute("select StyleEx from t_diagram"))

    assert len(scope) == 12
    assert {row[2] for row in scope} == {"Logical"}

    by_notation: dict[str | None, int] = {}
    for row in scope:
        key = _style_notation(row[3])
        by_notation[key] = by_notation.get(key, 0) + 1
    assert by_notation == {"IDEF1X": 7, "Information Engineering": 2,
                           "UML 2.1": 3}

    # And the key is a general display setting rather than something these
    # diagrams invented: the model-wide distribution is overwhelmingly `UML 2.1`.
    model_wide: dict[str | None, int] = {}
    for (style_ex,) in every:
        key = _style_notation(style_ex)
        model_wide[key] = model_wide.get(key, 0) + 1
    assert model_wide["UML 2.1"] > 1000
    # Every IDEF1X and IE diagram in the model is one of the twelve, so neither
    # value names a notation drawn anywhere else.
    assert model_wide["IDEF1X"] == 7
    assert model_wide["Information Engineering"] == 5


# ---------------------------------------------------------------------------
# 1 and 2. There is no size to state
# ---------------------------------------------------------------------------
@needs_model
def test_the_table_shape_has_no_modal_size_because_it_is_sized_by_its_columns():
    """The central element of the notation, and not one repeated size in it.

    21 observations, 21 distinct sizes. This is the refusal, and the reason it is
    permanent rather than thin: n clears `MIN_SAMPLE` comfortably, so no amount of
    further data is what is missing. A table's box is its column list.
    """
    measured = mb.measure_binding(MODEL, EXTENDED, DATA_MODELING)
    table = measured.sizes["table"]
    assert table.n == 21
    assert not table.low_n
    assert table.mode is None
    assert table.distinct == table.n
    assert table.median == (258, 281)


@needs_model
def test_the_pooled_default_is_a_seven_percent_accident_supplied_by_singletons():
    """What `sizing.default` would have had to be, and why it is not stated.

    The tool emits 177x70 because it is the pool's unique mode, and the same
    result carries everything needed to see that it is not a convention: a 6.9%
    share over 28 distinct sizes, a median nowhere near it, and a `default_supply`
    naming two concepts that are one element each. Neither of them is a `table`.
    """
    measured = mb.measure_binding(MODEL, EXTENDED, DATA_MODELING)
    stat = measured.default_size
    assert stat is not None and not stat.low_n      # n=29 clears the floor
    assert stat.mode == (177, 70)
    assert stat.mode_count == 2 and stat.n == 29
    assert stat.mode_share < mb.DOMINANT_SHARE / 5
    assert stat.distinct == 28
    assert stat.median == (211, 271)

    # The mode belongs to two singleton concepts, so it is those elements' size
    # before it is anything about the diagram type.
    assert measured.default_supply == {"function": 1, "view": 1}
    for concept in measured.default_supply:
        assert measured.sizes[concept].low_n, concept
        assert concept != "table"


@needs_model
def test_neither_candidate_default_fits_a_single_table_in_the_model():
    """The two figures a binding could have stated, against the population.

    The pooled mode and the substrate's inherited figure, each compared with the
    SMALLEST table measured. Both lose on both axes, which is what turns "the
    share is weak" into "the value is wrong", and it is why the inheritance
    mechanism was not reached for: it would have reported the figure as borrowed
    and still composed every table at a third of its measured size.
    """
    with mb.open_model_copy(MODEL) as conn:
        ids = [row[0] for row in _data_modeling_diagrams(conn)]
        rects = list(conn.execute(
            "select do.RectRight-do.RectLeft, do.RectTop-do.RectBottom "
            "from t_diagramobjects do join t_object o on o.Object_ID=do.Object_ID "
            "where o.Stereotype = 'table' and do.Diagram_ID in (%s)"
            % ",".join("?" * len(ids)), ids))
    assert len(rects) == 21
    smallest_w = min(w for w, _ in rects)
    smallest_h = min(h for _, h in rects)
    assert (smallest_w, smallest_h) == (183, 224)

    pooled = mb.measure_binding(MODEL, EXTENDED, DATA_MODELING).default_size.mode
    substrate = find_binding("UML", directory=_BINDINGS).diagram_type("Logical")
    inherited = substrate.sizing["default"]
    assert inherited == {"w": 90, "h": 70}
    for candidate in (pooled, (inherited["w"], inherited["h"])):
        assert candidate[0] < smallest_w, candidate
        assert candidate[1] < smallest_h, candidate


def test_no_shipped_binding_inherits_its_default_size_today():
    """Context for the decision above, and it is checked rather than asserted.

    The inheritance path exists and nothing ships on it, so binding this notation
    that way would have been its debut. If this test ever fails, a binding HAS
    taken the path and the third refusal above should be re-read against whatever
    that binding's substrate figure is - inheriting is legitimate where the
    borrowed figure is plausible for the notation, and here it is not.
    """
    from bindings import available_bindings
    inheriting = [
        f"{technology}::{name}"
        for technology in available_bindings(directory=_BINDINGS)
        for name, dt in find_binding(
            technology, directory=_BINDINGS).diagram_types.items()
        if dt.default_size_is_inherited
    ]
    assert inheriting == []


# ---------------------------------------------------------------------------
# What is measurable, and why it is not enough
# ---------------------------------------------------------------------------
@needs_model
def test_both_gaps_are_measurable_and_both_are_provisional():
    """The figures that would have been worth having, with their own caveat.

    They pass the concentration rule - no single diagram supplies MORE than half
    of either population - and they fail the gap floor, which is the guard added
    for exactly this: at n under `MIN_SAMPLE_GAP` a median lands within 25% of the
    notation's true median only about two thirds of the time. `thin_median` is the
    flag, it annotates rather than suppresses, and a binding stating one of these
    would have to say so on the line.
    """
    measured = mb.measure_binding(MODEL, EXTENDED, DATA_MODELING)
    for stat, median, n in ((measured.h_gap, 107, 17),
                            (measured.v_gap, 127.0, 16)):
        assert stat.n == n
        assert stat.median == median
        assert not stat.concentrated
        assert stat.top_count <= stat.n / 2
        assert stat.thin_median
        assert n < mb.MIN_SAMPLE_GAP
    # And the vertical population has no mode at all to fall back on.
    assert measured.v_gap.mode is None and len(measured.v_gap.tied_modes) == 16


def test_gaps_alone_do_not_make_a_loadable_document():
    """The schema rule that makes the size refusal decisive rather than partial.

    A document stating this diagram type's two measured gaps and no size does not
    load, and the substrate it would otherwise inherit from is the one refused in
    `test_neither_candidate_default_fits_a_single_table_in_the_model`. So there is
    no shape of binding that carries the measurable half on its own.
    """
    document = """
technology: WBA-DataModel
diagram_types:
  "Data Modeling":
    base: Logical
    grammar: graph
    title: frame-header
    sizing: {}
    spacing: {item_gap_x: 107, item_gap_y: 127}
    routing: {default: Direct}
    channels:
      fill: ~
      free: [fill]
"""
    with pytest.raises(BindingError) as caught:
        load_binding_text(document, "wba-datamodel.yaml")
    assert "sizing.default" in str(caught.value)


# ---------------------------------------------------------------------------
# The deliverable is the absence
# ---------------------------------------------------------------------------
@needs_model
def test_the_other_extended_diagram_type_in_the_corpus_is_refused_by_the_tool():
    """`Dashboard` fails the same way, which is why there is no `extended.yaml`.

    The technology declares six diagram types and two of them carry corpus rows:
    `Data Modeling` and `Dashboard`. Refusing only the first would leave a file
    worth writing for the second, so the second is measured here. It is refused
    more plainly than the first - the tool emits no default at all, because the
    pool has no unique mode - and for the same underlying reason: a chart is sized
    to what it plots. `SSDynamicChart` is 36 observations over 34 distinct sizes.

    So the deliverable really is the absence of the whole file, not the absence of
    one diagram type in it.
    """
    dashboard = mb.measure_binding(MODEL, EXTENDED, "Dashboard")
    assert dashboard.diagrams == 43        # not a thin sample
    assert dashboard.default_size is None or dashboard.default_size.mode is None
    chart = dashboard.sizes["SSDynamicChart"]
    assert chart.n == 36 and not chart.low_n
    assert chart.distinct == 34
    assert chart.mode_share < mb.DOMINANT_SHARE / 5


def test_no_data_model_binding_is_shipped_under_any_of_its_names():
    """If one is ever added, this test fails and whoever added it has to come here
    and say which refusal above stopped applying."""
    from bindings import available_bindings
    for identifier in (EXTENDED, "DataModel", "DataModeling", "IDEF1X"):
        assert find_binding(identifier, directory=_BINDINGS) is None, identifier
    claimed = set(available_bindings(directory=_BINDINGS))
    assert EXTENDED not in claimed
    for filename in ("extended.yaml", "datamodel.yaml", "idef1x.yaml"):
        assert not (_BINDINGS / filename).exists(), filename


# ---------------------------------------------------------------------------
# The last unbound TOGAF row: a technology the model does not carry
# ---------------------------------------------------------------------------
@needs_model
def test_the_feaf_technology_behind_the_togaf_trm_row_is_absent_from_the_model():
    """n=0, the same refusal as SysPhS's first and for the same reason.

    The `togaf-trm` corpus row records technology `FEAF Diagrams` with diagram type
    `TechnicalReferenceModel`, a third TOGAF-family technology on top of the two
    the TOGAF binding already names. The reference model tags no diagram with it, so there is no
    size, no gap and no base type to read - and the substring check is looser than
    an equality check so a differently spelled id would fail this rather than
    agree with it.
    """
    with mb.open_model_copy(MODEL) as conn:
        technologies = mb.list_technologies(conn)
    assert technologies, "the model tags no technology at all - wrong model?"
    assert FEAF not in technologies
    assert not [t for t in technologies if "feaf" in t.lower()]
    with pytest.raises(mb.MeasureError):
        mb.measure_binding(MODEL, FEAF)


def test_the_togaf_binding_records_the_feaf_refusal():
    """Recorded where a binding author will read it, not only here.

    The TOGAF file already names `TOGAF_DataArchitecture` as the second id it does
    not bind; `FEAF Diagrams` is the third and the corpus row that needs it is
    named, so the omission cannot be mistaken for an oversight.
    """
    assert FEAF in _TOGAF_TEXT
    assert "TechnicalReferenceModel" in _TOGAF_TEXT

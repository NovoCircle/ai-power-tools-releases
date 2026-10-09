#!/usr/bin/env python3
"""Tests for the diagram linter.

Run from the repository root:

    python -m pytest ea-diagram-composition/tools/test_lint.py -q

Nothing here touches a repository, a COM object or the filesystem.

WHAT THIS FILE DOES AND DOES NOT COVER
---------------------------------------
The geometry rules - overlap, canvas, sizing, pitch, routing - are exercised in
depth by the benchmark harness's own suite, which runs them through
`scoring.score_diagram` against the corpus. Duplicating those cases here would
be two copies of one fact, and this build has already been bitten once by two
copies of a fact agreeing with each other while both were wrong.

So what is tested here is what is NEW and what is STRUCTURAL: the profile
suppression table, the loop's stopping conditions, the report's own contract,
and the layer boundary that makes the module reusable at all. Plus one case per
rule that proves it is wired into `lint_diagram` - not that the rule is correct,
but that it runs.
"""
from __future__ import annotations

import ast
import json
import sys
from pathlib import Path

import pytest

_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

import lint  # noqa: E402
from lint import (  # noqa: E402
    Finding,
    LintReport,
    MAX_CORRECTION_PASSES,
    PROFILE_KEYS,
    SUPPRESSED_BY,
    is_stalled,
    lint_diagram,
)


# ---------------------------------------------------------------------------
# Fixtures, in EA's coordinate convention
# ---------------------------------------------------------------------------
def box(element_id, left, top, width=100, height=60, **extra):
    """One placed element. `top` is negative, as EA writes it."""
    return {
        "element_id": element_id,
        "left": left, "top": top,
        "right": left + width, "bottom": top - height,
        "width": width, "height": height,
        **extra,
    }


def verified(objects=(), links=(), cx=1000, cy=800):
    return {
        "ok": True,
        "objects": list(objects),
        "links": list(links),
        "canvas": {"cx": cx, "cy": cy},
    }


def _row(n, pitch=140, top=-40):
    return [box(i, left=20 + i * pitch, top=top) for i in range(n)]


# ---------------------------------------------------------------------------
# The layer boundary - the reason this module is reusable
# ---------------------------------------------------------------------------
def test_the_linter_does_not_import_the_binding_layer():
    """Language-neutral by construction, enforced rather than asserted in prose.

    A profile arrives as a plain mapping. The moment this module imports
    `bindings` it acquires an opinion about notations, and the claim that one
    linter serves a notation nobody wrote a binding for stops being true.

    Walks import STATEMENTS rather than searching the text, because a mention
    inside a docstring is documentation and must not trip this - while
    `from bindings import X` must.
    """
    tree = ast.parse((_HERE / "lint.py").read_text(encoding="utf-8"))
    imported: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imported.append(node.module)
    forbidden = {"bindings", "compose", "yaml"}
    assert not (set(imported) & forbidden), imported


def test_the_linter_names_no_modeling_language():
    """No notation, technology id or stereotype anywhere in the module.

    Same rule the layout engine is held to. A linter that knows what ArchiMate
    is will eventually be asked to treat it specially, and then it is not one
    linter any more.

    Checked over identifiers AND string constants, because the realistic leak
    is a rule message that names a notation, not an import.
    """
    source = (_HERE / "lint.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    names: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Name):
            names.append(node.id)
        elif isinstance(node, ast.Attribute):
            names.append(node.attr)
        elif isinstance(node, ast.Constant) and isinstance(node.value, str):
            names.append(node.value)
        elif isinstance(node, ast.arg):
            names.append(node.arg)
        elif isinstance(node, (ast.FunctionDef, ast.ClassDef)):
            names.append(node.name)
    blob = " ".join(names).lower()
    for notation in ("archimate", "bpmn", "sysml", "togaf", "erd", "archi"):
        assert notation not in blob, f"{notation!r} leaked into lint.py"

    # `stereotype` is deliberately NOT on that list, and the reason is worth
    # stating because it looks like an omission. It is not a modeling language;
    # it is EA's own generic term, and it reaches this module as the names of
    # display settings the server exposes - `hide_element_stereotypes` and
    # `hide_connector_stereotypes`. Suppressing stereotype TEXT is a
    # presentation decision that applies to every notation equally. What must
    # stay out is a branch on WHICH stereotype, and that is what the rest of
    # this test covers.
    assert not any(k for k in PROFILE_KEYS if k not in
                   {"hide_connector_labels", "hide_element_stereotypes",
                    "hide_connector_stereotypes", "show_element_notes",
                    "hide_attribute_types", "hide_operation_return_types",
                    "hide_operation_brackets", "collapses_parallel"}), (
        "a new profile key was added; confirm it names a presentation setting "
        "rather than a notation concept before adding it here"
    )


# ---------------------------------------------------------------------------
# The report's contract
# ---------------------------------------------------------------------------
def test_clean_means_no_errors_not_no_findings():
    """Several rules here fire on diagrams that are correct for their context.

    If `clean` meant "no findings at all" the bar would be one nobody clears,
    and a linter nobody can satisfy is a linter that gets switched off.
    """
    report = LintReport()
    report.add(Finding(rule="r", severity="warning", message="m"))
    assert report.clean
    assert report.warnings and not report.errors
    report.add(Finding(rule="r2", severity="error", message="m"))
    assert not report.clean


def test_every_finding_carries_a_correction():
    """Findings must be actionable by the loop, not merely descriptive.

    Asserted over a diagram built to trip several rules at once, so this cannot
    pass by finding nothing.
    """
    objects = [
        box(1, left=0, top=-10),
        box(2, left=50, top=-30),          # overlaps 1
        box(3, left=5000, top=-40),        # outside the canvas
    ]
    report = lint_diagram(verified(objects))
    assert report.findings, "the fixture stopped tripping any rule"
    for finding in report.findings:
        assert finding.correction.strip(), f"{finding.rule} has no correction"
        assert finding.severity in ("error", "warning", "info")
        assert finding.message.strip()


def test_a_report_signature_ignores_message_wording():
    """So a pass that changed a coordinate is not read as a different finding."""
    a, b = LintReport(), LintReport()
    a.add(Finding(rule="overlap", severity="error", message="at x=10",
                  subjects=(1, 2)))
    b.add(Finding(rule="overlap", severity="error", message="at x=40",
                  subjects=(1, 2)))
    assert a.signature() == b.signature()


# ---------------------------------------------------------------------------
# The bounded loop
# ---------------------------------------------------------------------------
def test_the_correction_budget_is_stated_and_small():
    """A loop that runs until it is happy either terminates or lies."""
    assert isinstance(MAX_CORRECTION_PASSES, int)
    assert 1 <= MAX_CORRECTION_PASSES <= 5


def test_a_pass_that_changed_nothing_is_a_stall():
    objects = [box(1, left=0, top=-10), box(2, left=50, top=-30)]
    first = lint_diagram(verified(objects))
    second = lint_diagram(verified(objects))
    assert is_stalled(first, second)


def test_the_first_pass_is_never_a_stall():
    report = lint_diagram(verified([box(1, left=0, top=-10)]))
    assert not is_stalled(None, report)


def test_a_pass_that_fixed_something_is_not_a_stall():
    before = lint_diagram(verified([box(1, left=0, top=-10),
                                    box(2, left=50, top=-30)]))
    after = lint_diagram(verified([box(1, left=0, top=-10),
                                   box(2, left=300, top=-10)]))
    assert not is_stalled(before, after)
    assert after.clean


# ---------------------------------------------------------------------------
# Profile awareness
# ---------------------------------------------------------------------------
def test_every_suppressed_rule_names_a_key_the_linter_understands():
    """The suppression table cannot reference a profile key nobody supplies.

    A typo here would silently never suppress, which is the failure mode that
    gets a linter switched off by an irritated user rather than reported.
    """
    for rule, key in SUPPRESSED_BY.items():
        assert key in PROFILE_KEYS, f"{rule!r} keys off unknown {key!r}"


def test_a_profile_suppression_is_reported_not_silent():
    """A rule that was skipped has to be visible, or a clean report overstates
    what was checked."""
    report = lint_diagram(verified([box(1, left=0, top=-10)]),
                          profile={"hide_connector_labels": True})
    assert "missing-connector-labels" in report.suppressed


def test_no_profile_suppresses_nothing():
    report = lint_diagram(verified([box(1, left=0, top=-10)]))
    assert report.suppressed == []


def test_a_profile_that_hides_nothing_suppresses_nothing():
    report = lint_diagram(verified([box(1, left=0, top=-10)]),
                          profile={"hide_connector_labels": False})
    assert report.suppressed == []


def test_an_unknown_profile_key_is_ignored_not_rejected():
    """A profile vocabulary is allowed to grow without breaking the linter."""
    report = lint_diagram(verified([box(1, left=0, top=-10)]),
                          profile={"some_future_setting": True})
    assert report.suppressed == []


@pytest.mark.parametrize("key", PROFILE_KEYS)
def test_no_profile_key_can_suppress_a_geometry_rule(key):
    """Presentation must never switch off a structural defect.

    Overlapping elements are wrong under every profile. If a future suppression
    entry ever keyed a geometry rule off a display setting, this is what says
    so - an executive view is allowed to hide labels, not to hide collisions.
    """
    objects = [box(1, left=0, top=-10), box(2, left=50, top=-30)]
    report = lint_diagram(verified(objects), profile={key: True})
    assert any(f.rule == "overlap" for f in report.findings), key
    assert not report.clean, key


# ---------------------------------------------------------------------------
# Each rule is actually wired into the driver
# ---------------------------------------------------------------------------
def test_overlapping_elements_are_an_error():
    report = lint_diagram(verified([box(1, left=0, top=-10),
                                    box(2, left=50, top=-30)]))
    assert [f.rule for f in report.findings] == ["overlap"]
    assert report.metrics["overlaps"] == 1


def test_containment_is_not_an_overlap():
    """A nested grid nests deliberately and must not be punished for it."""
    outer = box(1, left=0, top=-10, width=400, height=300)
    inner = box(2, left=40, top=-60, width=100, height=60)
    report = lint_diagram(verified([outer, inner]))
    assert report.metrics["overlaps"] == 0
    assert report.clean


def test_touching_elements_do_not_overlap_but_nothing_else_may_rely_on_that():
    """Abutting rects are correct geometry - swimlanes touch by design.

    Stated as its own test because it is load-bearing in the wrong direction:
    no-overlap never implies whitespace, so any spacing rule has to measure
    spacing itself. That has been learned twice in this programme.
    """
    a = box(1, left=0, top=-10, width=100)
    b = box(2, left=100, top=-10, width=100)
    report = lint_diagram(verified([a, b]))
    assert report.metrics["overlaps"] == 0


def test_an_element_outside_the_page_size_is_info_and_not_a_defect():
    """Measured, not assumed, and this test is the guard on that measurement.

    The rule used to say such a diagram "exports clipped". It does not: content
    spanning 1550x1410 on an 800x1100 canvas exported at 2219x2031 - the
    CONTENT's aspect, not the canvas's - with nothing missing. Since `cx`/`cy`
    is one printed page, any diagram of consequence exceeds it, so a warning
    here fires on almost everything and means nothing. It failed six of the
    first nineteen live sweep cases, all six of them correct compositions.

    Demoting it is therefore a correction, not a convenience. If someone
    promotes it again, they need a new measurement, and this says so.
    """
    report = lint_diagram(verified([box(1, left=5000, top=-40)], cx=800, cy=600))
    assert [f.rule for f in report.findings] == ["out-of-canvas"]
    assert [f.severity for f in report.findings] == ["info"]
    assert report.clean
    assert report.metrics["outside_canvas"] == 1


def test_the_page_size_count_is_still_reported_for_callers_who_print():
    """Demoted, not deleted - it is exactly what a caller printing needs."""
    inside = lint_diagram(verified([box(1, left=10, top=-40)], cx=800, cy=600))
    assert inside.metrics["outside_canvas"] == 0
    assert not [f for f in inside.findings if f.rule == "out-of-canvas"]


def test_inconsistent_sizing_within_a_role_is_an_error():
    role = [box(1, left=0, top=-40, width=100),
            box(2, left=200, top=-40, width=180)]
    report = lint_diagram(verified(role), roles={"capability": role})
    assert any(f.rule == "uniform-sizing" for f in report.findings)
    assert not report.clean


def test_two_roles_may_differ_from_each_other():
    """Uniform WITHIN a role, not across roles - the caller decides what a role
    is, because that is the language question this module refuses to answer."""
    small = [box(1, left=0, top=-40, width=30, height=30),
             box(2, left=100, top=-40, width=30, height=30)]
    large = [box(3, left=200, top=-40, width=110, height=60),
             box(4, left=400, top=-40, width=110, height=60)]
    report = lint_diagram(verified(small + large),
                          roles={"event": small, "activity": large})
    assert report.metrics["roles_with_inconsistent_sizing"] == 0
    assert report.clean


def test_uneven_spacing_in_a_row_is_reported():
    row = [box(1, left=0, top=-40), box(2, left=140, top=-40),
           box(3, left=600, top=-40)]
    report = lint_diagram(verified(row), rows=[row])
    assert any(f.rule == "pitch" for f in report.findings)


def test_an_evenly_spaced_row_is_clean():
    row = _row(4)
    report = lint_diagram(verified(row), rows=[row])
    assert not [f for f in report.findings if f.rule == "pitch"]
    assert report.metrics["worst_pitch_spread"] == 0


def test_a_mixed_size_row_with_no_whitespace_is_an_error():
    """The counterexample the pitch floor exists for.

    Alternating widths with an even center pitch drive every edge gap to zero
    while the center spread stays perfect - a row with no whitespace anywhere.
    The overlap rule cannot catch it, because touching is exempt by design.
    """
    row = [box(1, left=0, top=-40, width=30),
           box(2, left=30, top=-40, width=110),
           box(3, left=140, top=-40, width=30),
           box(4, left=170, top=-40, width=110)]
    report = lint_diagram(verified(row), rows=[row])
    pitch = [f for f in report.findings if f.rule == "pitch"]
    assert any(f.severity == "error" for f in pitch), [str(f) for f in pitch]


def test_a_uniform_row_with_no_whitespace_is_an_error():
    """The defect that scored completely clean, and the third of its family.

    Eight equal boxes butted edge to edge. The two rules that look like they
    cover it both look away, and this asserts BOTH of those blind spots as well
    as the finding, because it is the pair of them that let it through:
    `check_no_overlaps` exempts touching by design, and eight gaps of zero have
    a spread of zero. The floor on the gap itself used to exist only on the
    mixed-size path.
    """
    row = [box(i, left=i * 120, top=-40, width=120) for i in range(8)]
    report = lint_diagram(verified(row, cx=2000, cy=800), rows=[row])
    pitch = [f for f in report.findings if f.rule == "pitch"]
    assert [f.severity for f in pitch] == ["error"], [str(f) for f in pitch]
    assert pitch[0].subjects == tuple(range(8))
    assert report.metrics["overlaps"] == 0, "touching is not an overlap"
    assert report.metrics["worst_pitch_spread"] == 0, (
        "the spread is blind to this row, which is the whole reason the floor "
        "has to be a separate measure"
    )
    assert not report.clean


def test_abutting_containers_declared_as_a_stack_are_not_a_spacing_defect():
    """THE CONTROL THAT MATTERS MOST for the floor above.

    Bands, lanes and pools abut on purpose, and a rule forbidding all touching
    would be wrong. What keeps the floor off them is the DECLARATION: they reach
    the linter as a stack, and no rule here measures the gaps between a stack's
    members. Both a pair and a run of three, since a pair is the shape a pool
    and its neighbor make.
    """
    pair = [box(1, left=0, top=0, width=600, height=200),
            box(2, left=0, top=-200, width=600, height=200)]
    report = lint_diagram(verified(pair, cx=1000, cy=800),
                          stacks=[("vertical", pair)])
    assert not report.findings, [str(f) for f in report.findings]

    three = [box(i + 1, left=0, top=-(i * 200), width=600, height=200)
             for i in range(3)]
    report = lint_diagram(verified(three, cx=1000, cy=800),
                          stacks=[("vertical", three)])
    assert not report.findings, [str(f) for f in report.findings]

    # Side by side, which is how the other orientation abuts.
    columns = [box(i + 1, left=i * 300, top=0, width=300, height=600)
               for i in range(3)]
    report = lint_diagram(verified(columns, cx=1000, cy=800),
                          stacks=[("horizontal", columns)])
    assert not report.findings, [str(f) for f in report.findings]


def test_the_floors_scope_is_the_declaration_and_not_the_element_type():
    """The same three boxes, reported as a row and clean as a stack.

    Stated as its own test because it is the whole scoping decision. Nothing
    about the geometry or the element type differs between these two calls - only
    what the caller said the boxes are - and declaring a row is the statement
    that its members are laid out with spacing between them.
    """
    boxes = [box(i + 1, left=i * 300, top=0, width=300, height=600,
                 type="Boundary", name=f"Lane {i}")
             for i in range(3)]
    as_a_stack = lint_diagram(verified(boxes, cx=1000, cy=800),
                              stacks=[("horizontal", boxes)])
    assert not [f for f in as_a_stack.findings if f.rule == "pitch"]

    as_a_row = lint_diagram(verified(boxes, cx=1000, cy=800), rows=[boxes])
    assert [f.rule for f in as_a_row.findings] == ["pitch"]
    assert as_a_row.errors


def test_uneven_spacing_in_a_column_is_reported():
    """Gap 2: the y axis, which had no rule and no way to declare one.

    One member slid down, exactly as the row case slides one right.
    """
    column = [box(1, left=80, top=0, height=60),
              box(2, left=80, top=-120, height=60),
              box(3, left=80, top=-270, height=60)]
    report = lint_diagram(verified(column), columns=[column])
    pitch = [f for f in report.findings if f.rule == "pitch"]
    assert [f.severity for f in pitch] == ["warning"], [str(f) for f in pitch]
    assert "column" in pitch[0].message
    assert report.metrics["worst_pitch_spread"] == 30
    assert report.metrics["pitch_groups_measured"] == 1


def test_an_evenly_spaced_column_is_clean():
    column = [box(i, left=80, top=-(i * 120), height=60) for i in range(4)]
    report = lint_diagram(verified(column), columns=[column])
    assert not report.findings, [str(f) for f in report.findings]
    assert report.metrics["worst_pitch_spread"] == 0
    assert report.metrics["pitch_groups_measured"] == 1


def test_a_column_measured_as_a_row_is_what_used_to_hide_it():
    """Why the axis had to be added rather than inferred.

    Passed as a ROW, a column's every x gap is the same negative number, so the
    spread is zero and uneven vertical spacing reported clean. That is no longer
    silent - the floor sees the overlap in x - but what comes back is "no
    whitespace", not "unevenly spaced", and only the caller can say which
    question it meant to ask.
    """
    column = [box(1, left=80, top=0, height=60),
              box(2, left=80, top=-120, height=60),
              box(3, left=80, top=-270, height=60)]
    as_a_row = lint_diagram(verified(column), rows=[column])
    assert [f.severity for f in as_a_row.findings
            if f.rule == "pitch"] == ["error"]
    assert as_a_row.metrics["worst_pitch_spread"] == 0

    as_a_column = lint_diagram(verified(column), columns=[column])
    assert [f.severity for f in as_a_column.findings
            if f.rule == "pitch"] == ["warning"]
    assert as_a_column.metrics["worst_pitch_spread"] == 30


def test_a_column_of_mixed_heights_is_judged_on_center_pitch():
    """The same reasoning as a row of mixed widths, on the other axis: size is
    taken ALONG the reading direction, so a column reads its heights."""
    column = [box(1, left=80, top=0, height=30),
              box(2, left=80, top=-100, height=110),
              box(3, left=80, top=-280, height=30),
              box(4, left=80, top=-380, height=110)]
    report = lint_diagram(verified(column), columns=[column])
    assert not report.findings, [str(f) for f in report.findings]

    touching = [box(1, left=80, top=0, height=30),
                box(2, left=80, top=-30, height=110),
                box(3, left=80, top=-140, height=30),
                box(4, left=80, top=-170, height=110)]
    report = lint_diagram(verified(touching), columns=[touching])
    assert [f.severity for f in report.findings
            if f.rule == "pitch"] == ["error"]


def test_a_column_of_uniform_heights_with_no_whitespace_is_an_error():
    """Gap 1 on the other axis. The floor is not a row-only rule."""
    column = [box(i, left=80, top=-(i * 60), height=60) for i in range(5)]
    report = lint_diagram(verified(column), columns=[column])
    assert [f.severity for f in report.findings
            if f.rule == "pitch"] == ["error"]
    assert report.metrics["overlaps"] == 0


def test_rows_and_columns_are_counted_and_judged_together():
    """One rule, two axes, one report. The worst of both and the count of all."""
    row = [box(i, left=20 + i * 140, top=-40) for i in range(3)]
    column = [box(10 + i, left=600, top=-(i * 120), height=60)
              for i in range(3)]
    column[2]["top"] = -300
    column[2]["bottom"] = -360
    report = lint_diagram(verified(row + column, cx=1200, cy=900),
                          rows=[row], columns=[column])
    assert report.metrics["pitch_groups_measured"] == 2
    assert report.metrics["worst_pitch_spread"] == 60
    assert [f.rule for f in report.findings] == ["pitch"]


def test_an_unknown_pitch_axis_is_reported_not_guessed():
    row = _row(3)
    report = LintReport()
    lint.check_pitch_consistency([row], report, axis="diagonal")
    assert not report.findings
    assert any("pitch" in line for line in report.not_run)
    assert "worst_pitch_spread" not in report.metrics


def test_a_connector_with_no_route_is_a_warning():
    links = [{"connector_id": 7, "stored": True, "route": None}]
    report = lint_diagram(verified([box(1, left=0, top=-40)], links))
    assert any(f.rule == "routing-unset" for f in report.findings)


def test_an_unstored_link_is_not_judged_for_routing():
    """EA draws a relationship between two placed elements whether or not a
    presentation row exists. A line with no row has no route to set."""
    links = [{"connector_id": 7, "stored": False, "route": None}]
    report = lint_diagram(verified([box(1, left=0, top=-40)], links))
    assert not [f for f in report.findings if f.rule.startswith("routing")]
    assert report.metrics["links_stored"] == 0


def test_a_route_that_is_not_the_expected_one_is_reported():
    links = [{"connector_id": 7, "stored": True, "route": "Direct"}]
    report = lint_diagram(verified([box(1, left=0, top=-40)], links),
                          expected_route="OrthogonalSquare")
    assert any(f.rule == "routing-mismatch" for f in report.findings)


def test_rules_needing_a_grouping_do_not_run_without_one():
    """Omitting `roles`/`rows` must not invent them.

    Guessing which elements share a role from their geometry would be inventing
    the metamodel this module refuses to have, and it would do it silently.
    """
    row = [box(1, left=0, top=-40, width=100),
           box(2, left=200, top=-40, width=180)]
    report = lint_diagram(verified(row))
    assert report.metrics["roles_with_inconsistent_sizing"] == 0
    assert report.clean
    # ...and the denominator beside it says the zero is not a result. Two
    # elements of different widths are sitting right there; the rule scored 0
    # because nobody said they play one role, which is a different statement
    # from "they match".
    assert report.metrics["roles_measured"] == 0


def test_a_vacuous_zero_is_told_apart_from_a_clean_one_by_its_denominator():
    """Three rules recorded a 0 that meant either "clean" or "never asked".

    `crossings` had exactly this ambiguity until `crossings_measured_over` was
    added beside it, and a vacuous zero from it was read as a result for months.
    These three now carry the same kind of companion, and it is the companion -
    not the count - that says whether the question was put.
    """
    row = [box(1, left=0, top=-40), box(2, left=140, top=-40),
           box(3, left=280, top=-40)]
    asked = lint_diagram(verified(row), roles={"step": row}, rows=[row],
                         title_convention="drawn")
    assert asked.metrics["roles_with_inconsistent_sizing"] == 0
    assert asked.metrics["roles_measured"] == 1
    assert asked.metrics["worst_pitch_spread"] == 0
    assert asked.metrics["pitch_groups_measured"] == 1
    assert asked.metrics["title_convention_stated"] is True

    unasked = lint_diagram(verified(row))
    for metric in ("roles_with_inconsistent_sizing", "worst_pitch_spread"):
        assert unasked.metrics[metric] == asked.metrics[metric], (
            f"{metric} cannot distinguish the two cases on its own -- which is "
            f"why it needs a denominator"
        )
    assert unasked.metrics["roles_measured"] == 0
    assert unasked.metrics["pitch_groups_measured"] == 0
    assert unasked.metrics["title_convention_stated"] is False


def test_an_empty_diagram_lints_without_crashing():
    report = lint_diagram(verified([]))
    assert report.clean
    assert report.metrics["objects"] == 0


# ===========================================================================
# Rules that read identity, not only geometry
# ===========================================================================
# These are the rules that were INERT in the scorer this linter replaces: they
# read `name`, `type`, `fill` and the link endpoints, and `verify_diagram` did
# not return any of them. Their tests passed because the fixtures invented what
# the rules wanted. So every test below that could be written against a real
# captured payload is written against one - see `real_payload`.
_REAL_PAYLOAD = (
    Path(__file__).resolve().parents[3]
    / "ai-power-tools" / "ea-mcp-server" / "tests" / "fixtures"
    / "verify_diagram_real_payload.json"
)


def _load_real(name):
    if not _REAL_PAYLOAD.is_file():
        pytest.skip(f"real payload fixture not present at {_REAL_PAYLOAD}")
    return json.loads(_REAL_PAYLOAD.read_text(encoding="utf-8"))[name]


def test_the_hand_built_fixture_cannot_invent_a_field_production_lacks():
    """The fix for the whole class of bug, not just the three rules.

    A hand-built fixture that supplies a key `verify_diagram` never returns
    makes a rule look like it works. Three rules were inert for exactly that
    reason. This compares the keys `box()` produces against the keys a REAL
    captured payload has, and fails if the helper can conjure one.

    If this fails after a deliberate `verify_diagram` change, re-capture the
    fixture - do not widen the allowance here, because the allowance is the
    thing under test.
    """
    real = _load_real("FieldProbe")
    real_object_keys = set(real["objects"][0])
    sample = box(1, left=0, top=-40, name="X", type="Class", fill="#112233")
    invented = set(sample) - real_object_keys
    assert not invented, (
        f"the test helper produces keys production never returns: {invented}"
    )

    real_link_keys = set(real["links"][0])
    link_sample = {"connector_id": 1, "stored": True, "route": "Direct",
                   "name": "uses", "source_element_id": 1,
                   "target_element_id": 2}
    invented_links = set(link_sample) - real_link_keys - {"stored"}
    assert not invented_links, invented_links


def test_a_real_payload_lints_without_crashing():
    """Every rule, over geometry EA actually produced."""
    real = _load_real("FieldProbe")
    report = lint_diagram(real)
    assert isinstance(report.metrics["objects"], int)
    assert report.metrics["objects"] == 2
    # The denominator matters: zero crossings over zero measurable links is not
    # a result, and reporting it as one is what hid the inert rule for months.
    assert report.metrics["crossings_measured_over"] == 1


# ---------------------------------------------------------------------------
# Crossings
# ---------------------------------------------------------------------------
def test_crossings_are_counted_between_link_endpoints():
    objects = [box(1, left=0, top=-40), box(2, left=400, top=-40),
               box(3, left=0, top=-240), box(4, left=400, top=-240)]
    links = [
        {"connector_id": 10, "stored": True, "route": "Direct",
         "source_element_id": 1, "target_element_id": 4, "name": "a"},
        {"connector_id": 11, "stored": True, "route": "Direct",
         "source_element_id": 3, "target_element_id": 2, "name": "b"},
    ]
    report = lint_diagram(verified(objects, links))
    assert report.metrics["crossings"] == 1
    assert report.metrics["crossings_measured_over"] == 2
    assert any(f.rule == "crossings" for f in report.findings)


def test_crossings_are_info_because_some_are_unavoidable():
    """A rule that called every crossing a defect would fire on correct
    diagrams, and those are the rules that get a linter switched off."""
    objects = [box(1, left=0, top=-40), box(2, left=400, top=-40),
               box(3, left=0, top=-240), box(4, left=400, top=-240)]
    links = [
        {"connector_id": 10, "stored": True, "source_element_id": 1,
         "target_element_id": 4, "name": "a"},
        {"connector_id": 11, "stored": True, "source_element_id": 3,
         "target_element_id": 2, "name": "b"},
    ]
    report = lint_diagram(verified(objects, links))
    crossing = [f for f in report.findings if f.rule == "crossings"]
    assert crossing and crossing[0].severity == "info"
    assert report.clean


def test_links_with_no_endpoints_are_reported_as_unmeasured():
    """The exact failure that made this rule inert: links present, endpoints
    absent, and a confident `crossings: 0` on every diagram."""
    objects = [box(1, left=0, top=-40), box(2, left=400, top=-40)]
    links = [{"connector_id": 10, "stored": True, "route": "Direct"}]
    report = lint_diagram(verified(objects, links))
    assert report.metrics["crossings_measured_over"] == 0
    assert any("crossings" in note for note in report.not_run)


def test_connectors_meeting_at_a_shared_element_do_not_cross():
    objects = [box(1, left=0, top=-40), box(2, left=400, top=-40),
               box(3, left=200, top=-240)]
    links = [
        {"connector_id": 10, "stored": True, "source_element_id": 1,
         "target_element_id": 3, "name": "a"},
        {"connector_id": 11, "stored": True, "source_element_id": 2,
         "target_element_id": 3, "name": "b"},
    ]
    report = lint_diagram(verified(objects, links))
    assert report.metrics["crossings"] == 0


def _composed(result, links=()):
    """A composition as `verify_diagram` would hand it back, IDS UNTOUCHED.

    What this helper does NOT do is the point of it. The linter seam in each
    grammar's own test file renumbers every box to an integer on the way in,
    and that renumbering is precisely what kept the ids a composer invents out
    of the linter until one of them crashed it.
    """
    objects = [{
        "element_id": placed["id"],
        "name": placed.get("name") or "",
        "left": placed["left"], "top": placed["top"],
        "right": placed["right"], "bottom": placed["bottom"],
    } for placed in [*result["containers"], *result["items"]]]
    bounds = result["bounds"]
    return verified(objects, links,
                    cx=bounds["width"] + 100, cy=bounds["height"] + 100)


def test_ids_a_composer_invented_for_a_container_do_not_crash_the_linter():
    """Real compositions, because the claim is that the grammars produce these.

    A caller who does not care what a blank cell or an unnamed group is called
    states no id for it, and the composer invents one - a label, not a number.
    Every other object on the payload carries the caller's numeric model id, so
    the two shapes arrive TOGETHER, which is the case the crossings rule used to
    coerce and die on.

    A hand-built payload carrying the string `cell_0_0` would test the linter
    against this test's own guess. These layouts are composed, and the invented
    ids are asserted to be there, so the day a grammar starts numbering its own
    containers this test says so instead of passing on a fixture nobody reads.

    The real link is not decoration either: `crossings_measured_over` proves the
    rule still measured the endpoints it is for while the invented ids sat in
    its index, rather than being made crash-proof by measuring nothing.
    """
    pytest.importorskip("compose")      # the grammars import through it
    compose_matrix = pytest.importorskip("compose_matrix").compose_matrix
    compose_treemap = pytest.importorskip("compose_treemap").compose_treemap

    # Cells are stated at one address only, so the other three are invented.
    matrix = compose_matrix(
        [{"name": "Retail"}, {"name": "Commercial"}],
        [{"name": "Current"}, {"name": "Target"}],
        [{"row": "Retail", "column": "Current",
          "items": [{"id": 1000, "name": "Payments"},
                    {"id": 1001, "name": "Ledger"}]}],
    )
    # A group with no id of its own: the group rect and its header are invented.
    treemap = compose_treemap([{"name": "Retail", "tiles": [
        {"id": 2000, "name": "Payments", "weight": 3},
        {"id": 2001, "name": "Ledger", "weight": 1}]}])

    for label, result in (("matrix", matrix), ("treemap", treemap)):
        invented = [c["id"] for c in result["containers"]
                    if not str(c["id"]).lstrip("-").isdigit()]
        assert invented, (
            f"{label}: nothing was invented, so this test is not exercising "
            f"what it claims to")

        first, second = [item["id"] for item in result["items"]]
        link = {"connector_id": 1, "stored": True, "route": "Direct",
                "name": "settles", "source_element_id": first,
                "target_element_id": second}
        report = lint_diagram(_composed(result, [link]))
        assert report.metrics["crossings_measured_over"] == 1, (
            f"{label}: the invented ids stopped the rule from measuring the "
            f"one link that does have endpoints")
        assert report.metrics["crossings"] == 0, label


# ---------------------------------------------------------------------------
# Color
# ---------------------------------------------------------------------------
def test_two_fills_with_nothing_explaining_them_is_a_warning():
    objects = [box(1, left=0, top=-40, name="A", type="Class", fill="#cc3300"),
               box(2, left=200, top=-40, name="B", type="Class", fill="#336699")]
    report = lint_diagram(verified(objects))
    assert any(f.rule == "unexplained-color" for f in report.findings)
    assert report.clean, "unexplained color is a warning, not an error"


def test_one_fill_carries_no_information():
    objects = [box(1, left=0, top=-40, name="A", type="Class", fill="#cc3300"),
               box(2, left=200, top=-40, name="B", type="Class", fill="#cc3300")]
    report = lint_diagram(verified(objects))
    assert not [f for f in report.findings if f.rule == "unexplained-color"]


def test_a_named_container_explains_the_colors():
    """A banded diagram's band names ARE its key; demanding a separate legend
    on top would be noise, and noisy rules get ignored."""
    objects = [box(1, left=0, top=-40, name="A", type="Class", fill="#cc3300"),
               box(2, left=200, top=-40, name="B", type="Class", fill="#336699"),
               box(9, left=0, top=-20, width=400, height=200,
                   name="Channels", type="Boundary")]
    report = lint_diagram(verified(objects))
    assert not [f for f in report.findings if f.rule == "unexplained-color"]


def test_an_unnamed_container_explains_nothing():
    objects = [box(1, left=0, top=-40, name="A", type="Class", fill="#cc3300"),
               box(2, left=200, top=-40, name="B", type="Class", fill="#336699"),
               box(9, left=0, top=-20, width=400, height=200,
                   name="", type="Boundary")]
    report = lint_diagram(verified(objects))
    assert any(f.rule == "unexplained-color" for f in report.findings)


def test_a_legend_explains_the_colors():
    objects = [box(1, left=0, top=-40, name="A", type="Class", fill="#cc3300"),
               box(2, left=200, top=-40, name="B", type="Class", fill="#336699"),
               box(9, left=0, top=-400, name="Legend", type="Text")]
    report = lint_diagram(verified(objects))
    assert not [f for f in report.findings if f.rule == "unexplained-color"]


# ---------------------------------------------------------------------------
# Title
# ---------------------------------------------------------------------------
def test_a_drawn_title_convention_with_no_title_is_reported():
    objects = [box(1, left=0, top=-40, name="A", type="Class")]
    report = lint_diagram(verified(objects), title_convention="drawn")
    assert any(f.rule == "missing-title" for f in report.findings)


def test_the_frame_header_convention_needs_no_drawn_title():
    """Most diagrams correctly use EA's frame header. Firing unconditionally
    would flag the majority of a real corpus for doing the right thing."""
    objects = [box(1, left=0, top=-40, name="A", type="Class")]
    report = lint_diagram(verified(objects), title_convention="frame-header")
    assert not [f for f in report.findings if f.rule == "missing-title"]


def test_no_stated_convention_means_no_title_rule():
    objects = [box(1, left=0, top=-40, name="A", type="Class")]
    report = lint_diagram(verified(objects))
    assert not [f for f in report.findings if f.rule == "missing-title"]


def test_a_text_element_satisfies_a_drawn_title():
    objects = [box(1, left=0, top=-40, name="A", type="Class"),
               box(2, left=0, top=-10, name="Landscape", type="Text")]
    report = lint_diagram(verified(objects), title_convention="drawn")
    assert not [f for f in report.findings if f.rule == "missing-title"]


# ---------------------------------------------------------------------------
# Connector labels, and the profile that makes them moot
# ---------------------------------------------------------------------------
def test_inconsistent_connector_labeling_is_reported():
    """PARTIAL labeling is the defect, not absent labeling.

    Rewritten after the first version fired on a real generated diagram whose
    six sequence flows are deliberately unnamed -- which is that notation's
    convention, not an error. A rule that reports a correct diagram every time
    is the rule that gets the linter switched off.
    """
    links = [
        {"connector_id": 5, "stored": True, "route": "Direct", "name": "uses"},
        {"connector_id": 6, "stored": True, "route": "Direct", "name": ""},
    ]
    report = lint_diagram(verified([box(1, left=0, top=-40)], links))
    finding = [f for f in report.findings
               if f.rule == "missing-connector-labels"]
    assert finding, [str(f) for f in report.findings]
    assert finding[0].subjects == (6,), "only the blank one is the oversight"


def test_uniformly_unlabeled_connectors_are_a_convention_not_a_defect():
    links = [{"connector_id": 5, "stored": True, "route": "Direct", "name": ""},
             {"connector_id": 6, "stored": True, "route": "Direct", "name": ""}]
    report = lint_diagram(verified([box(1, left=0, top=-40)], links))
    assert not [f for f in report.findings
                if f.rule == "missing-connector-labels"]
    assert report.metrics["connectors_unlabeled"] == 2, (
        "the count is still reported; only the finding is withheld"
    )


def test_an_executive_profile_does_not_report_missing_connector_labels():
    """The item's own example, and the reason profile-awareness is a
    correctness requirement: a linter that rejects every executive view gets
    switched off, and then it protects nothing."""
    links = [{"connector_id": 5, "stored": True, "route": "Direct",
              "name": "uses"},
             {"connector_id": 6, "stored": True, "route": "Direct", "name": ""}]
    report = lint_diagram(verified([box(1, left=0, top=-40)], links),
                          profile={"hide_connector_labels": True})
    assert not [f for f in report.findings
                if f.rule == "missing-connector-labels"]
    assert "missing-connector-labels" in report.suppressed


def test_an_unstored_link_has_no_label_state_to_judge():
    links = [{"connector_id": 5, "stored": False, "name": ""}]
    report = lint_diagram(verified([box(1, left=0, top=-40)], links))
    assert not [f for f in report.findings
                if f.rule == "missing-connector-labels"]


# ---------------------------------------------------------------------------
# Collapsed connectors: the one rule a profile turns ON
# ---------------------------------------------------------------------------
def test_collapsing_without_saying_so_is_an_error():
    links = [{"connector_id": 5, "stored": True, "route": "Direct",
              "name": "uses"}]
    report = lint_diagram(verified([box(1, left=0, top=-40, name="A")], links),
                          profile={"collapses_parallel": True})
    assert any(f.rule == "collapsed-connectors-unannotated"
               for f in report.findings)
    assert not report.clean


def test_an_annotation_satisfies_the_collapse_rule():
    objects = [box(1, left=0, top=-40, name="A", type="Class"),
               box(2, left=0, top=-300, type="Note",
                   name="Parallel relationships collapsed for readability")]
    links = [{"connector_id": 5, "stored": True, "name": "uses"}]
    report = lint_diagram(verified(objects, links),
                          profile={"collapses_parallel": True})
    assert not [f for f in report.findings
                if f.rule == "collapsed-connectors-unannotated"]


def test_the_collapse_rule_does_not_exist_without_a_collapsing_profile():
    """The only rule here a profile turns ON. Without one it must be silent,
    or every ordinary diagram is told to annotate something it did not do."""
    links = [{"connector_id": 5, "stored": True, "name": "uses"}]
    report = lint_diagram(verified([box(1, left=0, top=-40, name="A")], links))
    assert not [f for f in report.findings
                if f.rule == "collapsed-connectors-unannotated"]


# ---------------------------------------------------------------------------
# Label fit, measured from EA's own render
# ---------------------------------------------------------------------------
def _svg(boxes_and_text):
    """Minimal EA-shaped SVG. The attribute ORDER matters to the parser, and
    it is the order EA emits - checked against a real captured render."""
    parts = ['<svg xmlns="http://www.w3.org/2000/svg">']
    for (x, y, w, h), runs in boxes_and_text:
        parts.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" />')
        for tx, ty, tl, text in runs:
            parts.append(
                f'<text x="{tx}" y="{ty}" textLength="{tl}" '
                f'style="font-family:Calibri; font-size:10px;">{text}</text>'
            )
    parts.append("</svg>")
    return "".join(parts)


def test_a_label_that_leaves_its_box_is_an_error():
    objects = [box(1, left=35, top=-40, width=100, height=70, name="Overlong")]
    svg = _svg([((35, 40, 100, 70), [(20, 72, 130, "Overlong")])])
    report = lint_diagram({**verified(objects), "svg_text": svg})
    clipped = [f for f in report.findings if f.rule == "label-clipped"]
    assert clipped, [str(f) for f in report.findings]
    assert clipped[0].severity == "error"
    assert clipped[0].subjects == (1,), "the finding must name its element"


def test_a_label_hard_against_the_border_is_a_warning():
    """Calibrated, not invented: on a real capability map this margin
    separates exactly the two names that look wrong from the next box."""
    objects = [box(1, left=35, top=-40, width=100, height=70, name="Snug")]
    svg = _svg([((35, 40, 100, 70), [(40, 72, 90, "Snug")])])
    report = lint_diagram({**verified(objects), "svg_text": svg})
    cramped = [f for f in report.findings if f.rule == "label-cramped"]
    assert cramped and cramped[0].severity == "warning"
    assert report.clean, "cramped is legible; it must not block"


def test_a_comfortable_label_is_not_reported():
    objects = [box(1, left=35, top=-40, width=100, height=70, name="Fits")]
    svg = _svg([((35, 40, 100, 70), [(56, 72, 58, "Fits")])])
    report = lint_diagram({**verified(objects), "svg_text": svg})
    assert not [f for f in report.findings if f.rule.startswith("label-")]
    assert report.metrics["labels_measured"] == 1


def test_the_label_rule_says_when_it_could_not_run():
    """A check that quietly does nothing is worse than one that is absent."""
    objects = [box(1, left=35, top=-40, name="A")]
    report = lint_diagram(verified(objects))
    assert report.metrics["labels_measured"] == 0
    assert any("label-fit" in note for note in report.not_run)


def test_label_fit_is_measured_on_a_real_render():
    """The whole rule, against markup EA actually emitted.

    `Payments Hub` in a 100-wide box: EA measured the string at 58px and
    started it at x=56 in a box spanning 35..135, so it clears both borders by
    21px. Nothing should be reported, and `labels_measured` proves the rule
    ran rather than skipping the boxes silently.
    """
    real = _load_real("FieldProbe")
    assert real.get("svg_text"), "the fixture lost its render"
    report = lint_diagram(real)
    assert report.metrics["labels_measured"] >= 2
    assert not [f for f in report.findings if f.rule.startswith("label-")]


def test_a_run_without_textlength_is_ignored_rather_than_guessed():
    """EA supplies `textLength` on every run it draws. If one ever lacks it,
    skipping is right - estimating the width would turn an exact rule into a
    silent approximation, which is the thing this rule was built to avoid."""
    svg = ('<svg><rect x="0" y="0" width="100" height="70" />'
           '<text x="10" y="30">No length here</text></svg>')
    assert lint._svg_text_runs(svg) == []


# ===========================================================================
# Container extents and hub spokes
# ===========================================================================
# Two defects found by eye on real renders that every rule above passed. Both
# rules take their grouping from the caller - `stacks` and `rings` - and neither
# runs without it, for the reason `roles` and `rows` do not: which boxes form a
# stack or a ring is a composition fact, and coordinates cannot say.
def _centered(element_id, cx, cy, width, height, **extra):
    """A box placed by its CENTER, in EA's convention."""
    return box(element_id, left=round(cx - width / 2),
               top=-round(cy - height / 2), width=width, height=height,
               **extra)


def _band_stack(widths, band_height=100, gap=30, left=0):
    """Bands stacked top to bottom from a shared left edge, one per width."""
    return [box(i + 1, left=left, top=-(i * (band_height + gap)),
                width=w, height=band_height)
            for i, w in enumerate(widths)]


def _spoked_ring(hub, item_sizes, gap=120, start_deg=-90.0, id_base=100,
                 bearings=None):
    """Items around `hub`, each placed by its NEAR EDGE so every spoke is `gap`.

    The construction a correct generator uses: center distance is the hub's
    reach plus the gap plus the item's own reach along that bearing. Rounding to
    whole units leaves a spread of a unit or two, which is the tolerance's job.
    """
    import math
    hx, hy = lint._center(hub)
    step = 360.0 / len(item_sizes)
    items = []
    for n, (w, h) in enumerate(item_sizes):
        degrees = bearings[n] if bearings else start_deg + n * step
        angle = math.radians(degrees)
        ux, uy = math.cos(angle), math.sin(angle)
        probe = _centered(0, 0, 0, w, h)
        reach = (lint._edge_distance(hub, ux, uy)
                 + gap + lint._edge_distance(probe, ux, uy))
        items.append(_centered(id_base + n, hx + ux * reach, hy + uy * reach,
                               w, h))
    return items


def _unspoked_ring(hub, item_sizes, radius=300, start_deg=-90.0,
                   id_base=100):
    """Items with their CENTERS on a circle - the defective construction."""
    import math
    hx, hy = lint._center(hub)
    step = 360.0 / len(item_sizes)
    return [
        _centered(id_base + n,
                  hx + radius * math.cos(math.radians(start_deg + n * step)),
                  hy + radius * math.sin(math.radians(start_deg + n * step)),
                  w, h)
        for n, (w, h) in enumerate(item_sizes)
    ]


# ---------------------------------------------------------------------------
# ragged-stack
# ---------------------------------------------------------------------------
def test_bands_of_three_three_and_two_leave_a_ragged_stack():
    """The real failing shape: each band sized to its own contents.

    Three items across is 344 wide, two is 264. Nothing overlaps and every
    other rule passes, which is the point - this is a rule about the container.
    """
    bands = _band_stack([344, 344, 264])
    report = lint_diagram(verified(bands), stacks=[("vertical", bands)])
    ragged = [f for f in report.findings if f.rule == "ragged-stack"]
    assert len(ragged) == 1
    assert ragged[0].severity == "warning"
    assert ragged[0].subjects == (1, 2, 3)
    assert report.metrics["worst_stack_extent_spread"] == 80
    others = [f for f in report.findings if f.rule != "ragged-stack"]
    assert not others, [str(f) for f in others]
    assert report.clean, "a warning must not block the loop"


def test_a_horizontal_stack_is_judged_on_height():
    columns = [box(1, left=0, top=-0, width=100, height=300),
               box(2, left=130, top=-0, width=100, height=300),
               box(3, left=260, top=-0, width=100, height=220)]
    report = lint_diagram(verified(columns), stacks=[("horizontal", columns)])
    assert [f.rule for f in report.findings] == ["ragged-stack"]
    assert report.metrics["worst_stack_extent_spread"] == 80


def test_a_stack_of_one_width_is_clean_even_when_the_bands_differ_in_height():
    """The control. Bands sized by their contents ARE taller or shorter as they
    hold more or fewer rows, and that is legitimate - only the cross-axis
    extent of a vertical stack is the rule's business. A rule that compared
    heights here would fire on every well-formed banded diagram."""
    bands = [box(1, left=0, top=0, width=344, height=190),
             box(2, left=0, top=-220, width=344, height=100),
             box(3, left=0, top=-350, width=344, height=100)]
    report = lint_diagram(verified(bands), stacks=[("vertical", bands)])
    assert not report.findings, [str(f) for f in report.findings]
    assert report.metrics["worst_stack_extent_spread"] == 0


def test_a_vertical_stack_is_not_judged_on_the_axis_it_runs_along():
    """The other half of the control, for the horizontal axis."""
    columns = [box(1, left=0, top=0, width=100, height=300),
               box(2, left=130, top=0, width=180, height=300)]
    report = lint_diagram(verified(columns), stacks=[("horizontal", columns)])
    assert not report.findings


def test_an_extent_within_tolerance_is_not_ragged():
    """EA nudges geometry; a 2-unit delta must not be reported."""
    bands = _band_stack([344, 346, 342])
    report = lint_diagram(verified(bands), stacks=[("vertical", bands)])
    assert not report.findings
    assert report.metrics["worst_stack_extent_spread"] == 4
    wider = _band_stack([344, 349])
    report = lint_diagram(verified(wider), stacks=[("vertical", wider)])
    assert [f.rule for f in report.findings] == ["ragged-stack"]


def test_staggered_but_equal_bands_are_not_ragged_they_are_staggered():
    """Extent only, still - but the other question now has a rule of its own.

    This case was the recorded blind spot: equal widths from different left
    edges, which `check_stack_extents` says it refuses to judge and nothing else
    looked at. It must come back as `staggered-stack` and NOT as `ragged-stack`,
    because the two are different defects with different corrections.
    """
    bands = [box(1, left=0, top=0, width=300, height=100),
             box(2, left=60, top=-130, width=300, height=100)]
    report = lint_diagram(verified(bands), stacks=[("vertical", bands)])
    assert [f.rule for f in report.findings] == ["staggered-stack"]
    assert report.metrics["worst_stack_extent_spread"] == 0


def test_a_stack_of_one_is_not_a_stack():
    band = _band_stack([344])
    report = lint_diagram(verified(band), stacks=[("vertical", band)])
    assert not report.findings
    assert "worst_stack_extent_spread" not in report.metrics


def test_an_unknown_stack_axis_is_reported_not_guessed():
    bands = _band_stack([344, 264])
    report = lint_diagram(verified(bands), stacks=[("diagonal", bands)])
    assert not report.findings
    assert any("ragged-stack" in line for line in report.not_run)


def test_each_stack_is_judged_on_its_own():
    """Two stacks that disagree with each other are two stacks, not one."""
    narrow = _band_stack([264, 264])
    wide = [box(10 + i, left=600, top=-(i * 130), width=344, height=100)
            for i in range(2)]
    report = lint_diagram(verified(narrow + wide),
                          stacks=[("vertical", narrow), ("vertical", wide)])
    assert not report.findings


# ---------------------------------------------------------------------------
# uneven-spokes
# ---------------------------------------------------------------------------
_HUB = box(1, left=450, top=-370, width=100, height=60)
_WIDE_FLAT = [(140, 60)] * 8


def test_a_ring_of_wide_items_centered_on_a_circle_has_unequal_spokes():
    """The real failing shape: 140x60 items, each centered on the circle.

    At the top and bottom an item reaches toward the hub by 30, at the sides by
    70, so the spokes differ by tens of units while every item is exactly where
    the circle says.
    """
    ring = _unspoked_ring(_HUB, _WIDE_FLAT)
    report = lint_diagram(verified([_HUB, *ring]), rings=[(_HUB, ring)])
    uneven = [f for f in report.findings if f.rule == "uneven-spokes"]
    assert len(uneven) == 1
    assert uneven[0].severity == "warning"
    assert uneven[0].subjects[0] == _HUB["element_id"]
    assert set(uneven[0].subjects[1:]) == {i["element_id"] for i in ring}
    assert report.metrics["worst_spoke_spread"] > 30
    others = [f for f in report.findings if f.rule != "uneven-spokes"]
    assert not others, [str(f) for f in others]
    assert report.clean


def test_a_ring_placed_by_near_edge_is_clean():
    """The control that matters more than the case above: the SAME items,
    placed so the spokes are equal, must not be reported."""
    ring = _spoked_ring(_HUB, _WIDE_FLAT)
    report = lint_diagram(verified([_HUB, *ring]), rings=[(_HUB, ring)])
    assert not report.findings, [str(f) for f in report.findings]
    assert report.metrics["worst_spoke_spread"] <= lint.PITCH_TOLERANCE


def test_a_near_edge_ring_of_mixed_sizes_around_a_square_hub_is_clean():
    """Equal spokes do not need equal items or a round hub. A generator that
    fixes the gap gets whatever sizes and bearings it likes; a rule that read
    equal sizes as the requirement would fire on it."""
    hub = box(1, left=450, top=-330, width=120, height=120)
    sizes = [(140, 60), (80, 80), (140, 60), (100, 40), (140, 60), (60, 60)]
    ring = _spoked_ring(hub, sizes, start_deg=-60.0)
    report = lint_diagram(verified([hub, *ring]), rings=[(hub, ring)])
    assert not report.findings, [str(f) for f in report.findings]


def test_unequal_angular_spacing_is_not_uneven_spokes():
    """Spoke LENGTH is the whole question for THIS rule.

    Items bunched on one side of the hub, each the same distance from its edge,
    are a different problem - and now a different rule. Asserted by rule id
    rather than by an empty report, because "the spoke rule stays out of it" is
    the fact worth holding: the two have different corrections, and confusing
    them would send a generator to move items radially when the angles are what
    is wrong.
    """
    items = _spoked_ring(_HUB, [(140, 60)] * 5,
                         bearings=(-100, -60, -20, 60, 150), gap=150)
    report = lint_diagram(verified([_HUB, *items]), rings=[(_HUB, items)])
    assert not [f for f in report.findings if f.rule == "uneven-spokes"]
    assert not report.findings, "no sweep was declared, so nothing judges angles"

    stated = lint_diagram(verified([_HUB, *items]),
                          rings=[(_HUB, items, 360)])
    assert [f.rule for f in stated.findings] == ["uneven-ring-angles"]


def test_a_ring_of_one_has_no_spread():
    ring = _spoked_ring(_HUB, [(140, 60)])
    report = lint_diagram(verified([_HUB, *ring]), rings=[(_HUB, ring)])
    assert not report.findings
    assert "worst_spoke_spread" not in report.metrics


def test_an_item_on_the_hubs_center_has_no_bearing_and_is_left_out():
    """No direction, so no spoke - and no crash on the zero-length vector."""
    ring = _spoked_ring(_HUB, [(140, 60)] * 4)
    stacked = _centered(999, *lint._center(_HUB), 140, 60)
    report = lint_diagram(verified([_HUB, *ring, stacked]),
                          rings=[(_HUB, [*ring, stacked])])
    assert not [f for f in report.findings if f.rule == "uneven-spokes"]


def test_a_radial_tree_is_judged_one_ring_at_a_time():
    """A branch hangs off a spoke, which is a hub of its own. Each ring is
    passed as its own pair and judged on its own spread."""
    inner = _spoked_ring(_HUB, [(140, 60)] * 4, gap=200)
    branch_hub = inner[0]                      # the item straight above the hub
    outer = _spoked_ring(branch_hub, [(100, 40)] * 3, gap=60, id_base=200,
                         bearings=(-140, -90, -40))
    report = lint_diagram(verified([_HUB, *inner, *outer]),
                          rings=[(_HUB, inner), (branch_hub, outer)])
    assert not report.findings, [str(f) for f in report.findings]
    defective = _unspoked_ring(branch_hub, [(140, 60)] * 3, radius=200,
                               id_base=300, start_deg=-140.0)
    report = lint_diagram(verified([_HUB, *inner, *defective]),
                          rings=[(_HUB, inner), (branch_hub, defective)])
    flagged = [f for f in report.findings if f.rule == "uneven-spokes"]
    assert len(flagged) == 1
    assert flagged[0].subjects[0] == branch_hub["element_id"]


# ---------------------------------------------------------------------------
# staggered-stack
# ---------------------------------------------------------------------------
def test_a_staggered_stack_is_reported():
    """Identical containers at different left edges, so the leading edge zigzags.

    Every other rule passes: the extents match, nothing overlaps, and no rule
    before this one looked at a declared stack's alignment at all.
    """
    bands = [box(1, left=0, top=0, width=300, height=100),
             box(2, left=50, top=-130, width=300, height=100),
             box(3, left=90, top=-260, width=300, height=100)]
    report = lint_diagram(verified(bands), stacks=[("vertical", bands)])
    found = [f for f in report.findings if f.rule == "staggered-stack"]
    assert len(found) == 1
    assert found[0].severity == "warning"
    assert found[0].subjects == (1, 2, 3)
    assert report.metrics["worst_stack_alignment_spread"] == 90
    assert report.metrics["worst_stack_extent_spread"] == 0
    assert report.clean, "a warning must not block the loop"


def test_a_horizontal_stack_is_judged_on_its_top_edges():
    """The leading edge is the one the eye follows: down a vertical stack it is
    the left edge, along a horizontal one it is the top."""
    columns = [box(1, left=0, top=0, width=100, height=300),
               box(2, left=130, top=-70, width=100, height=300),
               box(3, left=260, top=0, width=100, height=300)]
    report = lint_diagram(verified(columns), stacks=[("horizontal", columns)])
    assert [f.rule for f in report.findings] == ["staggered-stack"]
    assert report.metrics["worst_stack_alignment_spread"] == 70
    # The same offsets down the OTHER axis are a vertical stack's business and
    # not a horizontal one's: these three agree on every left edge they need to.
    sideways = [box(1, left=0, top=0, width=100, height=300),
                box(2, left=130, top=0, width=100, height=220),
                box(3, left=260, top=0, width=100, height=300)]
    report = lint_diagram(verified(sideways), stacks=[("horizontal", sideways)])
    assert [f.rule for f in report.findings] == ["ragged-stack"]


def test_a_stack_on_one_leading_edge_is_clean():
    """The control. Bands from a shared left edge, which is what a correct
    generator produces, and which must stay quiet however their widths differ -
    a ragged stack is a different finding and this rule must not double it."""
    bands = _band_stack([344, 344, 264])
    report = lint_diagram(verified(bands), stacks=[("vertical", bands)])
    assert not [f for f in report.findings if f.rule == "staggered-stack"]
    assert report.metrics["worst_stack_alignment_spread"] == 0


def test_an_offset_within_tolerance_is_not_staggered():
    """EA nudges geometry; a 4-unit offset must not be reported."""
    bands = [box(1, left=0, top=0, width=300, height=100),
             box(2, left=4, top=-130, width=300, height=100)]
    report = lint_diagram(verified(bands), stacks=[("vertical", bands)])
    assert not report.findings
    assert report.metrics["worst_stack_alignment_spread"] == 4
    further = [box(1, left=0, top=0, width=300, height=100),
               box(2, left=9, top=-130, width=300, height=100)]
    report = lint_diagram(verified(further), stacks=[("vertical", further)])
    assert [f.rule for f in report.findings] == ["staggered-stack"]


def test_a_stack_of_one_leaves_alignment_unjudged():
    band = _band_stack([344])
    report = lint_diagram(verified(band), stacks=[("vertical", band)])
    assert not report.findings
    assert "worst_stack_alignment_spread" not in report.metrics
    assert any("staggered-stack" in line for line in report.not_run)


def test_an_unknown_stack_axis_is_reported_by_both_stack_rules():
    """Each rule has to be honest when it is the only one called, so each says
    so for itself rather than leaning on the other having said it."""
    bands = _band_stack([344, 264])
    report = lint_diagram(verified(bands), stacks=[("diagonal", bands)])
    assert not report.findings
    assert any("ragged-stack" in line for line in report.not_run)
    assert any("staggered-stack" in line for line in report.not_run)
    assert "worst_stack_alignment_spread" not in report.metrics


# ---------------------------------------------------------------------------
# uneven-ring-angles
# ---------------------------------------------------------------------------
def test_a_ring_bunched_into_part_of_its_circumference_is_reported():
    """Three items at 0, 100 and 200 degrees of a ring meant to close.

    Every spoke is the same length, nothing overlaps, and the items' own steps
    are perfectly even at 100 apiece - the way back to the first is 160, which is
    what makes it bunched. So the closing step is not optional bookkeeping, it is
    the measurement.
    """
    items = _spoked_ring(_HUB, [(140, 60)] * 3, bearings=(0, 100, 200), gap=150)
    report = lint_diagram(verified([_HUB, *items], cx=2000, cy=2000),
                          rings=[(_HUB, items, 360)])
    found = [f for f in report.findings if f.rule == "uneven-ring-angles"]
    assert len(found) == 1
    assert found[0].severity == "warning"
    assert found[0].subjects[0] == _HUB["element_id"]
    assert set(found[0].subjects[1:]) == {i["element_id"] for i in items}
    assert report.metrics["worst_ring_angle_spread"] == 60
    assert not [f for f in report.findings if f.rule == "uneven-spokes"], (
        "the spokes are equal; this must not be reported as a spoke defect"
    )
    assert report.clean


def test_an_evenly_spread_closed_ring_is_clean():
    """The control: the same three items, at the step a closed ring of three
    should use."""
    items = _spoked_ring(_HUB, [(140, 60)] * 3, bearings=(0, 120, 240), gap=150)
    report = lint_diagram(verified([_HUB, *items], cx=2000, cy=2000),
                          rings=[(_HUB, items, 360)])
    assert not report.findings, [str(f) for f in report.findings]
    assert report.metrics["worst_ring_angle_spread"] <= lint.ANGLE_TOLERANCE


@pytest.mark.parametrize("count,sweep", [(5, 90), (3, 180), (4, 270),
                                         (6, 350), (2, 60), (8, 120)])
def test_a_deliberate_fan_is_not_a_bunched_ring(count, sweep):
    """THE CONTROL THAT MATTERS MOST. A partial sweep IS a ring bunched to one
    side, deliberately, and it is what a fan is for.

    Every sweep here, including 350 - where the opening is SMALLER than the
    steps, so identifying it as the widest gap would report every one of these.
    """
    step = sweep / (count - 1) if count > 1 else 0
    bearings = tuple(-90 + step * n for n in range(count))
    items = _spoked_ring(_HUB, [(140, 60)] * count, bearings=bearings, gap=200)
    report = lint_diagram(verified([_HUB, *items], cx=3000, cy=3000),
                          rings=[(_HUB, items, sweep)])
    assert not [f for f in report.findings if f.rule == "uneven-ring-angles"], (
        [str(f) for f in report.findings]
    )


def test_an_uneven_fan_is_reported_at_its_own_sweep():
    """The other half: a fan is not exempt, it is judged against being a fan."""
    hub = box(1, left=950, top=-870, width=100, height=60)
    bearings = (-90, -60, -30, 30, 90)
    items = _spoked_ring(hub, [(140, 60)] * 5, bearings=bearings, gap=400)
    report = lint_diagram(verified([hub, *items], cx=3000, cy=3000),
                          rings=[(hub, items, 180)])
    assert [f.rule for f in report.findings] == ["uneven-ring-angles"]
    assert report.metrics["worst_ring_angle_spread"] == 30


def test_a_fan_across_the_zero_degree_boundary_is_judged_the_same():
    """Nothing here may depend on where the ring starts. A fan straddling zero
    sorts into an order that puts its opening in the middle of the list, and an
    implementation that assumed the opening was last would report it."""
    bearings = (-40, -20, 0, 20, 40)
    items = _spoked_ring(_HUB, [(140, 60)] * 5, bearings=bearings, gap=200)
    report = lint_diagram(verified([_HUB, *items], cx=3000, cy=3000),
                          rings=[(_HUB, items, 80)])
    assert not report.findings, [str(f) for f in report.findings]


def test_a_ring_without_its_sweep_is_not_judged_on_its_angles():
    """The sweep cannot be inferred, so it is not: bunched and fanned are the
    SAME geometry, and only the caller knows how far round the ring should go."""
    items = _spoked_ring(_HUB, [(140, 60)] * 3, bearings=(0, 100, 200), gap=150)
    report = lint_diagram(verified([_HUB, *items], cx=2000, cy=2000),
                          rings=[(_HUB, items)])
    assert not report.findings, [str(f) for f in report.findings]
    assert "worst_ring_angle_spread" not in report.metrics
    assert any("uneven-ring-angles" in line for line in report.not_run)


def test_a_partial_ring_of_two_has_no_step_to_compare():
    """One gap is its opening and the other is its only step, so there is
    nothing to compare it against. A CLOSED ring of two does have two steps and
    they should be half the circle each."""
    items = _spoked_ring(_HUB, [(140, 60)] * 2, bearings=(-90, 0), gap=200)
    partial = lint_diagram(verified([_HUB, *items], cx=2000, cy=2000),
                           rings=[(_HUB, items, 90)])
    assert not partial.findings
    assert "worst_ring_angle_spread" not in partial.metrics

    closed = lint_diagram(verified([_HUB, *items], cx=2000, cy=2000),
                          rings=[(_HUB, items, 360)])
    assert [f.rule for f in closed.findings] == ["uneven-ring-angles"]


def test_an_item_on_the_hubs_center_is_left_out_of_the_angles_too():
    """No direction, so no bearing - and no crash, and no zero-degree step
    dragged into the spread."""
    items = _spoked_ring(_HUB, [(140, 60)] * 4, bearings=(0, 90, 180, 270),
                         gap=150)
    stacked = _centered(999, *lint._center(_HUB), 140, 60)
    report = lint_diagram(verified([_HUB, *items, stacked], cx=2000, cy=2000),
                          rings=[(_HUB, [*items, stacked], 360)])
    assert not [f for f in report.findings if f.rule == "uneven-ring-angles"]


# ---------------------------------------------------------------------------
# What `not_run` is for, and what it must stay quiet about
# ---------------------------------------------------------------------------
# The line: an ABSENT grouping is normal and says nothing, while a grouping the
# caller DECLARED and the rule could not judge is said out loud. An entry per
# unused grouping would land three or four lines on every ordinary diagram, and
# a list that is noisy on correct output is a list nobody reads - after which it
# cannot do the one job it exists for, which is admitting that a clean report
# checked less than it looks.
def test_an_unused_grouping_says_nothing_on_not_run():
    """Bands that look stacked and a ring that looks like a ring, undeclared.

    Not one word about any of it. This is the ordinary case - most diagrams have
    no roles, rows, stacks or rings to declare - and the absent metric key is
    the signal.
    """
    bands = _band_stack([344, 344, 264], left=1500)
    ring = _unspoked_ring(_HUB, _WIDE_FLAT)
    report = lint_diagram(verified([*bands, _HUB, *ring], cx=3000, cy=1500))
    assert [line for line in report.not_run
            if not line.startswith("label-fit")] == []
    empty = lint_diagram(verified([*bands, _HUB, *ring], cx=3000, cy=1500),
                         roles={}, rows=[], columns=[], stacks=[], rings=[])
    assert [line for line in empty.not_run
            if not line.startswith("label-fit")] == []


def test_an_empty_grouping_is_not_a_declaration():
    """A banded diagram drawn without band labels has no container elements at
    all, and its caller still hands over a stack. Complaining about that would be
    complaining about deliberate, documented behavior, so an empty group is
    skipped rather than reported as unjudgeable."""
    hub = box(1, left=450, top=-370, width=100, height=60)
    report = lint_diagram(verified([hub]), roles={"band": []}, rows=[[]],
                          columns=[[]], stacks=[("vertical", [])],
                          rings=[(hub, [])])
    assert [line for line in report.not_run
            if not line.startswith("label-fit")] == []
    assert not report.findings


def test_a_declared_grouping_that_could_not_be_judged_says_so():
    """The case the list exists for: the caller asked and got no answer.

    Every one of these looks exactly like a clean result in the findings, and
    the metrics that would give it away are the ones that are absent. So each
    rule says it out loud instead.
    """
    a = box(1, left=0, top=0, width=300, height=100)
    b = box(2, left=0, top=-130, width=300, height=100)
    report = lint_diagram(
        verified([a, b], cx=2000, cy=2000),
        roles={"band": [a]},
        rows=[[a, b]],
        stacks=[("vertical", [a])],
        rings=[(a, [b])],
    )
    assert report.clean
    for rule in ("uniform-sizing", "pitch", "ragged-stack", "staggered-stack",
                 "uneven-spokes", "uneven-ring-angles"):
        assert any(line.startswith(rule) for line in report.not_run), (
            f"{rule} was asked a question it could not answer and said nothing; "
            f"not_run is {report.not_run}"
        )


# ---------------------------------------------------------------------------
# Both are wired in, and neither runs without its grouping
# ---------------------------------------------------------------------------
def test_every_grouping_rule_is_reachable_from_the_entry_point():
    """A rule the entry point never calls is unreachable, and its own tests can
    still pass by calling it directly. Two server operations passed 48 tests
    while unregistered. This one goes through `lint_diagram` only, and checks
    each rule's function against `__all__` so a rule cannot be defined, wired up
    and left off the public surface."""
    bands = [box(1, left=0, top=0, width=300, height=100),
             box(2, left=50, top=-130, width=264, height=100)]
    row = [box(10 + i, left=1000 + i * 120, top=0, width=120) for i in range(4)]
    column = [box(20, left=2000, top=0, height=60),
              box(21, left=2000, top=-120, height=60),
              box(22, left=2000, top=-270, height=60)]
    ring = _spoked_ring(_HUB, [(140, 60)] * 3, bearings=(0, 100, 200), gap=150,
                        id_base=30)
    report = lint_diagram(
        verified([*bands, *row, *column, _HUB, *ring], cx=4000, cy=3000),
        rows=[row], columns=[column],
        stacks=[("vertical", bands)], rings=[(_HUB, ring, 360)])
    assert {f.rule for f in report.findings} == {
        "pitch", "ragged-stack", "staggered-stack", "uneven-ring-angles"}
    for name in ("check_pitch_consistency", "check_stack_extents",
                 "check_stack_alignment", "check_ring_spokes",
                 "check_ring_angles", "ANGLE_TOLERANCE"):
        assert name in lint.__all__, name


def test_both_geometry_rules_are_reachable_from_the_entry_point():
    """A rule the entry point never calls is unreachable, and its own tests can
    still pass by calling it directly. These go through `lint_diagram` only,
    and the ids are checked against `__all__` so a rule cannot be defined and
    left off the public surface."""
    bands = _band_stack([344, 344, 264], left=1500)
    ring = _unspoked_ring(_HUB, _WIDE_FLAT)
    report = lint_diagram(verified([*bands, _HUB, *ring], cx=3000, cy=1500),
                          stacks=[("vertical", bands)],
                          rings=[(_HUB, ring)])
    assert {f.rule for f in report.findings} == {"ragged-stack", "uneven-spokes"}
    assert "check_stack_extents" in lint.__all__
    assert "check_ring_spokes" in lint.__all__
    assert "STACK_AXES" in lint.__all__


def test_neither_rule_runs_when_the_caller_supplies_no_grouping():
    """Bands that look stacked and a ring that looks like a ring, with no
    grouping stated. The linter must not decide they are one - that would be
    inventing the metamodel - so neither rule may fire or record a metric."""
    bands = _band_stack([344, 344, 264], left=1500)
    ring = _unspoked_ring(_HUB, _WIDE_FLAT)
    report = lint_diagram(verified([*bands, _HUB, *ring], cx=3000, cy=1500))
    assert not [f for f in report.findings
                if f.rule in ("ragged-stack", "uneven-spokes")]
    assert "worst_stack_extent_spread" not in report.metrics
    assert "worst_spoke_spread" not in report.metrics
    empty = lint_diagram(verified([*bands, _HUB, *ring], cx=3000, cy=1500),
                         stacks=[], rings=[])
    assert "worst_stack_extent_spread" not in empty.metrics
    assert "worst_spoke_spread" not in empty.metrics


def test_a_grouping_passed_for_one_rule_does_not_switch_on_the_other():
    bands = _band_stack([344, 344, 264], left=1500)
    ring = _unspoked_ring(_HUB, _WIDE_FLAT)
    report = lint_diagram(verified([*bands, _HUB, *ring], cx=3000, cy=1500),
                          stacks=[("vertical", bands)])
    assert {f.rule for f in report.findings} == {"ragged-stack"}
    assert "worst_spoke_spread" not in report.metrics

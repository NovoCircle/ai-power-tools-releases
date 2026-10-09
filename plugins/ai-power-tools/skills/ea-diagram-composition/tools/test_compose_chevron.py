#!/usr/bin/env python3
"""Tests for the chevron-stack layout grammar.

Run from the repository root:

    python -m pytest ea-diagram-composition/tools/test_compose_chevron.py -q

Nothing here touches a repository, a COM object or the filesystem. The one test
that pins this grammar against a real diagram does it with numbers copied into
this file as constants, not by reading a model: a test that needs Sparx EA
installed to pass has broken the layer boundary, and the numbers are the part
worth keeping anyway.

Two conventions carried over from `test_compose.py`:

* `assert_no_overlaps` is applied to comparable sets. Here the whole item set IS
  comparable - a chevron stack has no containment at all - so it is applied to
  everything together, which is a stronger claim than the other grammars can
  make.
* Rect intersection is tested in EA's flipped-y convention, where `top` is
  greater than `bottom`. `compose.rects_overlap` is the tested implementation of
  that and is what every assertion here leans on.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

from compose import LayoutError, rect_height, rect_width, rects_overlap  # noqa: E402
from compose_chevron import (  # noqa: E402
    DEFAULT_CHEVRON_SPEC,
    MAX_NOTCH_PERCENT,
    compose_chevron_stack,
)


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------
def _stages(n, name=None):
    return [{"id": f"s{i}", "name": name or f"Stage {i}"} for i in range(n)]


def _supports(n):
    return [{"id": f"p{i}", "name": f"Support {i}"} for i in range(n)]


def _span(r):
    return (r["left"], r["top"], r["right"], r["bottom"])


def assert_no_overlaps(rects, label=""):
    """Assert that no two rects share positive area."""
    rects = list(rects)
    for i, a in enumerate(rects):
        for b in rects[i + 1:]:
            assert not rects_overlap(a, b), (
                f"{label}: overlap between {a.get('id')} {_span(a)} and "
                f"{b.get('id')} {_span(b)}"
            )


def _by_role(result, role):
    return [i for i in result["items"] if i["role"] == role]


# The shapes and counts every structural claim is checked over. Deliberately
# more than one hand-picked example: the clearance defect this engine already
# paid for once passed on the case it was written against and failed at every
# other count.
SHAPES = [
    (140, 60),    # the engine's default
    (80, 100),    # the reference diagram's own sizing
    (60, 140),    # taller than wide
    (40, 40),     # small and square
    (400, 40),    # very wide and flat
    (36, 200),    # very narrow and very tall
    (97, 61),     # nothing divides anything
]
COUNTS = list(range(1, 13))
NOTCHES = [1, 5, 20, 33, MAX_NOTCH_PERCENT]


# ---------------------------------------------------------------------------
# The reference: measured geometry, not a guess
# ---------------------------------------------------------------------------
# Read from the Value Chain diagram that ships with Sparx EA as a worked
# example. Five stages and four supporting strips, stored exactly as:
#
#   stages   left 53, 133, 213, 293, 373   right 133, 213, 293, 373, 453
#            top -239, bottom -339          so 80 wide and 100 tall
#   strips   left 53, right 453             so 400 wide, five stages of 80
#            tops -39, -89, -139, -189      so 50 tall, abutting
#
# The last strip's bottom is -239, which is the stage row's top: the band abuts
# the chain. The renderer's own shape script sizes the stage `defsize(80,100)`
# and throws its point 20 percent of the width past the right edge.
REFERENCE_ORIGIN = (53, -39)
REFERENCE_STAGE_RECTS = [
    (53, -239, 133, -339),
    (133, -239, 213, -339),
    (213, -239, 293, -339),
    (293, -239, 373, -339),
    (373, -239, 453, -339),
]
REFERENCE_SUPPORT_RECTS = [
    (53, -39, 453, -89),
    (53, -89, 453, -139),
    (53, -139, 453, -189),
    (53, -189, 453, -239),
]


def test_it_reproduces_the_reference_diagram_exactly():
    """THE ANCHOR. Every other test here says the arithmetic is self-consistent.

    This one says it agrees with a diagram somebody else drew, in a tool we do
    not control, using a shape we did not write. If a later edit changes the
    pitch rule, the abutment, the band width or the band's contact with the
    chain, this is the test that has to be argued with.
    """
    left, top = REFERENCE_ORIGIN
    result = compose_chevron_stack(
        _stages(5), _supports(4),
        spec={"origin_left": left, "origin_top": top,
              "item_width": 80, "item_height": 100,
              "support_height": 50, "support_gap": 0,
              "notch_percent": 20, "support_position": "above"},
    )
    assert [_span(i) for i in _by_role(result, "stage")] == REFERENCE_STAGE_RECTS
    assert [_span(i) for i in _by_role(result, "support")] == REFERENCE_SUPPORT_RECTS
    assert result["row_width"] == 400
    assert result["stage_pitch"] == 80
    assert result["notch_depth"] == 16          # 20 percent of 80
    assert result["text_width"] == 64           # what the shape reserves for the name
    assert result["drawn_right"] == 469         # 453, plus the point's 16


def test_the_reference_support_band_meets_the_chain():
    """The last strip's bottom edge IS the stage row's top edge, at gap 0."""
    left, top = REFERENCE_ORIGIN
    result = compose_chevron_stack(
        _stages(5), _supports(4),
        spec={"origin_left": left, "origin_top": top, "item_width": 80,
              "item_height": 100, "support_height": 50},
    )
    lowest_strip = _by_role(result, "support")[-1]
    assert lowest_strip["bottom"] == _by_role(result, "stage")[0]["top"]


# ---------------------------------------------------------------------------
# The spacing condition, over content variation rather than one example
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("item_width,item_height", SHAPES)
@pytest.mark.parametrize("count", COUNTS)
def test_nothing_overlaps_anything(item_width, item_height, count):
    """The whole item set, not a comparable subset: nothing nests here."""
    result = compose_chevron_stack(
        _stages(count), _supports(3),
        spec={"item_width": item_width, "item_height": item_height},
    )
    assert_no_overlaps(result["items"],
                       f"{item_width}x{item_height} n={count}")


@pytest.mark.parametrize("item_width,item_height", SHAPES)
@pytest.mark.parametrize("count", COUNTS)
@pytest.mark.parametrize("notch", NOTCHES)
def test_consecutive_stages_abut_exactly(item_width, item_height, count, notch):
    """Touching, at every count and every shape - not merely not overlapping.

    `x_{k+1} - x_k == W` is the condition derived in the module docstring. The
    gap being zero is the half of it a reader can see; the pitch being the width
    is the half that makes the interlock land.
    """
    if item_width * notch // 100 <= 0:
        pytest.skip("notch rounds away at this width; refused, tested elsewhere")
    result = compose_chevron_stack(
        _stages(count),
        spec={"item_width": item_width, "item_height": item_height,
              "notch_percent": notch},
    )
    stages = _by_role(result, "stage")
    gaps = [b["left"] - a["right"] for a, b in zip(stages, stages[1:])]
    pitches = [b["left"] - a["left"] for a, b in zip(stages, stages[1:])]
    assert set(gaps) <= {0}, f"gaps {gaps}"
    assert set(pitches) <= {item_width}, f"pitches {pitches}"
    assert result["stage_pitch"] == item_width


@pytest.mark.parametrize("item_width,item_height", SHAPES)
@pytest.mark.parametrize("count", COUNTS)
@pytest.mark.parametrize("notch", NOTCHES)
def test_the_interlock_is_exact(item_width, item_height, count, notch):
    """Each stage's POINT lands on the next stage's NOTCH, to the unit.

    This is the property the grammar exists for, and it is the one no rect-based
    check downstream can see: the point and the notch are ink, drawn outside and
    inside the stored rect respectively. If the pitch were widened by even one
    unit every assertion about overlap would still pass and this would fail.
    """
    if item_width * notch // 100 <= 0:
        pytest.skip("notch rounds away at this width; refused, tested elsewhere")
    result = compose_chevron_stack(
        _stages(count),
        spec={"item_width": item_width, "item_height": item_height,
              "notch_percent": notch},
    )
    stages = _by_role(result, "stage")
    for a, b in zip(stages, stages[1:]):
        assert a["point_x"] == b["notch_x"], (
            f"{item_width}x{item_height} notch={notch}: point {a['point_x']} "
            f"misses notch {b['notch_x']}")


@pytest.mark.parametrize("item_width,item_height", SHAPES)
@pytest.mark.parametrize("count", COUNTS)
def test_a_wider_pitch_would_break_the_interlock(item_width, item_height, count):
    """The counterpart of the test above: prove the equality is load bearing.

    Widening the pitch by one unit - the reflex fix for any complaint about
    spacing, and what every other grammar here would do - leaves a one-unit
    strip of background between each point and the notch it was supposed to
    fill, while every rect stays positive and nothing overlaps. Nothing
    downstream of this module can tell. That is why there is no pitch knob.
    """
    if count < 2:
        pytest.skip("a chain of one has no neighbor to miss")
    result = compose_chevron_stack(
        _stages(count),
        spec={"item_width": item_width, "item_height": item_height},
    )
    stages = _by_role(result, "stage")
    widened = [dict(s, left=s["left"] + i, right=s["right"] + i)
               for i, s in enumerate(stages)]
    assert_no_overlaps(widened, "widened pitch still does not overlap")
    depth = result["notch_depth"]
    misses = [(a["right"] + depth) - (b["left"] + depth)
              for a, b in zip(widened, widened[1:])]
    assert all(m != 0 for m in misses), (
        "a widened pitch must miss, or this grammar has no reason to pin it")


@pytest.mark.parametrize("notch", NOTCHES)
@pytest.mark.parametrize("w,w2", [(80, 81), (80, 120), (140, 60), (36, 400)])
def test_the_interlock_needs_one_shared_width(notch, w, w2):
    """Why stage sizing is not overridable per stage: the arithmetic forbids it.

    The notch depth is a proportion of each element's OWN width. Abut a stage of
    width `w` against one of width `w'` and the point and the notch are out of
    register by exactly `r * (w - w')`, whatever the pitch. Stated on the exact
    rational quantity rather than on this module's rounded `notch_depth`,
    because the renderer works in floats and two different widths can round to
    one integer depth while still missing on screen.
    """
    r = notch / 100.0
    # Stage 0 at x=0 with width w; stage 1 abutting it at x=w with width w2.
    point_of_first = 0 + w + r * w
    notch_of_second = w + r * w2
    assert point_of_first - notch_of_second == pytest.approx(r * (w - w2))
    assert point_of_first != notch_of_second

    # And the module refuses the input that would produce it.
    with pytest.raises(LayoutError) as exc:
        compose_chevron_stack([{"id": "a", "item_width": w},
                               {"id": "b", "item_width": w2}])
    assert "item_width" in str(exc.value)


# ---------------------------------------------------------------------------
# The supporting band
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("item_width,item_height", SHAPES)
@pytest.mark.parametrize("count", COUNTS)
@pytest.mark.parametrize("supports", [0, 1, 4])
@pytest.mark.parametrize("position", ["above", "below"])
def test_the_band_spans_the_chain_on_either_side(
        item_width, item_height, count, supports, position):
    result = compose_chevron_stack(
        _stages(count), _supports(supports),
        spec={"item_width": item_width, "item_height": item_height,
              "support_position": position},
    )
    stages = _by_role(result, "stage")
    strips = _by_role(result, "support")
    assert len(strips) == supports
    assert result["supports"] == supports

    row_left = stages[0]["left"]
    row_right = stages[-1]["right"]
    assert row_right - row_left == result["row_width"] == count * item_width

    for strip in strips:
        assert strip["left"] == row_left
        assert strip["right"] == row_right
        assert rect_height(strip) == result["support_height"]

    if not strips:
        return
    # Strips abut each other, in the order given, reading away from the chain.
    for a, b in zip(strips, strips[1:]):
        assert a["bottom"] == b["top"]
    if position == "above":
        assert strips[-1]["bottom"] == stages[0]["top"]
    else:
        assert strips[0]["top"] == stages[0]["bottom"]


@pytest.mark.parametrize("gap", [0, 1, 25])
def test_the_support_gap_separates_the_band_from_the_chain_too(gap):
    result = compose_chevron_stack(
        _stages(3), _supports(3), spec={"support_gap": gap},
    )
    strips = _by_role(result, "support")
    stages = _by_role(result, "stage")
    for a, b in zip(strips, strips[1:]):
        assert a["bottom"] - b["top"] == gap
    assert strips[-1]["bottom"] - stages[0]["top"] == gap
    assert_no_overlaps(result["items"], f"gap={gap}")


def test_the_band_is_optional():
    bare = compose_chevron_stack(_stages(4))
    empty = compose_chevron_stack(_stages(4), [])
    assert bare["items"] == empty["items"]
    assert bare["supports"] == 0
    assert _by_role(bare, "stage")[0]["top"] == DEFAULT_CHEVRON_SPEC["origin_top"]


def test_support_height_defaults_to_half_a_stage():
    result = compose_chevron_stack(_stages(2), _supports(1),
                                   spec={"item_height": 100})
    assert result["support_height"] == 50
    assert rect_height(_by_role(result, "support")[0]) == 50


def test_support_height_that_derives_to_nothing_is_refused_by_name():
    with pytest.raises(LayoutError) as exc:
        compose_chevron_stack(_stages(2), _supports(1), spec={"item_height": 1})
    assert "spec.support_height" in str(exc.value)


# ---------------------------------------------------------------------------
# What the result reports
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("item_width,item_height", SHAPES)
@pytest.mark.parametrize("count", COUNTS)
def test_bounds_cover_the_rects_and_drawn_right_covers_the_ink(
        item_width, item_height, count):
    result = compose_chevron_stack(
        _stages(count), _supports(2),
        spec={"item_width": item_width, "item_height": item_height},
    )
    b = result["bounds"]
    for item in result["items"]:
        assert b["left"] <= item["left"]
        assert b["right"] >= item["right"]
        assert b["top"] >= item["top"]
        assert b["bottom"] <= item["bottom"]
    assert b["width"] == b["right"] - b["left"]
    assert b["height"] == b["top"] - b["bottom"]
    # The point is ink and lies outside the stored bounds, by exactly the notch.
    assert result["drawn_right"] == b["right"] + result["notch_depth"]
    assert result["drawn_right"] == _by_role(result, "stage")[-1]["point_x"]


@pytest.mark.parametrize("item_width,item_height", SHAPES)
@pytest.mark.parametrize("notch", NOTCHES)
def test_the_name_area_is_what_the_notch_leaves(item_width, item_height, notch):
    if item_width * notch // 100 <= 0:
        pytest.skip("notch rounds away at this width; refused, tested elsewhere")
    result = compose_chevron_stack(
        _stages(3),
        spec={"item_width": item_width, "item_height": item_height,
              "notch_percent": notch},
    )
    depth = result["notch_depth"]
    assert depth == item_width * notch // 100
    assert result["text_width"] == item_width - depth
    assert 0 < result["text_width"] <= item_width
    for stage in _by_role(result, "stage"):
        assert stage["text_left"] == stage["left"] + depth
        assert stage["text_width"] == result["text_width"]
        assert stage["text_left"] + stage["text_width"] == stage["right"]


def test_every_coordinate_is_a_whole_unit():
    result = compose_chevron_stack(
        _stages(7), _supports(3),
        spec={"item_width": 97, "item_height": 61, "notch_percent": 33},
    )
    for item in result["items"]:
        for key in ("left", "top", "right", "bottom", "notch_x", "point_x",
                    "text_left", "text_width"):
            if key in item:
                assert isinstance(item[key], int), f"{key} is {type(item[key])}"
    for key in ("notch_depth", "text_width", "row_width", "stage_pitch",
                "support_height", "drawn_right"):
        assert isinstance(result[key], int)


def test_names_pass_through_and_sizing_ignores_their_length():
    """Label length is content and changes nothing about the geometry.

    Worth pinning rather than assuming: this engine has no font metrics, so a
    grammar that sized a box to its name would be guessing. What the caller gets
    instead is `text_width`, the width the renderer will actually have, to judge
    the fit against.
    """
    short = compose_chevron_stack([{"id": "a", "name": "A"},
                                   {"id": "b", "name": "B"}])
    long_name = "Regulatory reporting and supervisory engagement" * 3
    long = compose_chevron_stack([{"id": "a", "name": long_name},
                                  {"id": "b", "name": long_name}])
    assert [_span(i) for i in short["items"]] == [_span(i) for i in long["items"]]
    assert long["items"][0]["name"] == long_name
    assert long["text_width"] == short["text_width"]


def test_an_item_without_a_name_reports_none():
    result = compose_chevron_stack([{"id": 1}], [{"id": 2}])
    assert all("name" not in i for i in result["items"])
    assert all(i["container_id"] is None for i in result["items"])
    assert result["containers"] == []


def test_ids_are_preserved_verbatim():
    result = compose_chevron_stack([{"id": 12}, {"id": "12b"}], [{"id": 99}])
    assert [i["id"] for i in result["items"]] == [12, "12b", 99]


def test_the_same_input_gives_the_same_output():
    kwargs = dict(stages=_stages(6), supports=_supports(3),
                  spec={"item_width": 83, "item_height": 57})
    assert compose_chevron_stack(**kwargs) == compose_chevron_stack(**kwargs)


# ---------------------------------------------------------------------------
# Refusals
# ---------------------------------------------------------------------------
def test_an_empty_chain_is_refused():
    with pytest.raises(LayoutError) as exc:
        compose_chevron_stack([])
    assert "stages" in str(exc.value)


def test_a_duplicate_id_is_refused_across_both_lists():
    with pytest.raises(LayoutError) as exc:
        compose_chevron_stack([{"id": "x"}], [{"id": "x"}])
    assert "duplicate" in str(exc.value)
    assert "stages[0]" in str(exc.value)


def test_an_item_without_an_id_is_refused_by_path():
    with pytest.raises(LayoutError) as exc:
        compose_chevron_stack([{"id": "a"}, {"name": "no id"}])
    assert "stages[1].id" in str(exc.value)


def test_an_unknown_spec_key_is_refused():
    with pytest.raises(LayoutError) as exc:
        compose_chevron_stack(_stages(2), spec={"itemWidth": 80})
    assert "itemWidth" in str(exc.value)


def test_asking_for_a_pitch_is_refused_with_the_reason():
    """A caller reaching for `h_pitch` has a misunderstanding, not a typo."""
    with pytest.raises(LayoutError) as exc:
        compose_chevron_stack(_stages(2), spec={"h_pitch": 200})
    message = str(exc.value)
    assert "h_pitch" in message
    assert "item_width" in message


@pytest.mark.parametrize("key,value", [
    ("item_width", 0), ("item_height", -5), ("notch_percent", 0),
    ("support_gap", -1), ("support_height", 0),
])
def test_sizes_that_are_not_sizes_are_refused_by_name(key, value):
    with pytest.raises(LayoutError) as exc:
        compose_chevron_stack(_stages(2), spec={key: value})
    assert f"spec.{key}" in str(exc.value)


@pytest.mark.parametrize("notch", [MAX_NOTCH_PERCENT + 1, 80, 100, 140])
def test_a_notch_deeper_than_the_cap_is_refused(notch):
    with pytest.raises(LayoutError) as exc:
        compose_chevron_stack(_stages(2), spec={"notch_percent": notch})
    assert "notch_percent" in str(exc.value)


def test_a_notch_that_rounds_away_is_refused_rather_than_drawn_flat():
    """1 percent of a 40 wide stage is zero units, which is a row of oblongs."""
    with pytest.raises(LayoutError) as exc:
        compose_chevron_stack(_stages(3),
                              spec={"item_width": 40, "notch_percent": 1})
    assert "no chevron" in str(exc.value)


def test_an_unknown_support_position_is_refused():
    with pytest.raises(LayoutError) as exc:
        compose_chevron_stack(_stages(2), _supports(1),
                              spec={"support_position": "left"})
    assert "support_position" in str(exc.value)


@pytest.mark.parametrize("bad", ["not a list", {"id": "a"}, 7, None])
def test_a_stage_list_that_is_not_a_list_is_refused(bad):
    with pytest.raises(LayoutError):
        compose_chevron_stack(bad)


def test_a_boolean_is_not_a_number():
    with pytest.raises(LayoutError) as exc:
        compose_chevron_stack(_stages(2), spec={"item_width": True})
    assert "spec.item_width" in str(exc.value)


def test_per_stage_sizing_is_refused_with_the_reason():
    with pytest.raises(LayoutError) as exc:
        compose_chevron_stack([{"id": "a"}, {"id": "b", "item_height": 200}])
    message = str(exc.value)
    assert "item_height" in message
    assert "supports[" not in message


# ---------------------------------------------------------------------------
# THE SEAM: the shipped linter, run over this engine's own output
# ---------------------------------------------------------------------------
def _verified_like(result):
    """A `verify_diagram`-shaped payload built from composed rects.

    Hand-built and hermetic: the linter reads rectangles and does not care
    whether EA or this module produced them. `element_id` has to survive
    `int()`, which one of the linter's other rules requires, so the ids here are
    integers.
    """
    objects = [{"element_id": item["id"], "name": f"E{item['id']}",
                "left": item["left"], "top": item["top"],
                "right": item["right"], "bottom": item["bottom"]}
               for item in result["items"]]
    b = result["bounds"]
    return {
        "objects": objects,
        "links": [],
        "canvas": {"left": b["left"] - 50, "top": b["top"] + 50,
                   "right": b["right"] + 50, "bottom": b["bottom"] - 50},
    }


def _numbered(result):
    """The result with integer ids, plus the payload and the two groupings."""
    renumbered = dict(result, items=[dict(i, id=n)
                                     for n, i in enumerate(result["items"])])
    payload = _verified_like(renumbered)
    by_id = {o["element_id"]: o for o in payload["objects"]}
    stages = [by_id[i["id"]] for i in renumbered["items"] if i["role"] == "stage"]
    supports = [by_id[i["id"]] for i in renumbered["items"]
                if i["role"] == "support"]
    return payload, stages, supports


@pytest.mark.parametrize("item_width,item_height", SHAPES)
@pytest.mark.parametrize("count", COUNTS)
@pytest.mark.parametrize("supports", [0, 1, 4])
@pytest.mark.parametrize("position", ["above", "below"])
def test_the_shipped_linter_passes_this_grammar_declared_as_stacks(
        item_width, item_height, count, supports, position):
    """THE SEAM. Clean across content variation, not on one example.

    Two modules written independently have to agree: this engine decides the
    geometry, and `lint.py` decides whether geometry is acceptable. The rules
    that bear on a chevron stack are the overlap rule, which passes because
    abutting rects touch rather than overlap; the uniform-sizing rule, which
    passes because both roles are uniform by construction; and the two stack
    rules, which pass because the chain shares a height and a top edge and the
    band shares a width and a left edge.

    Note what is NOT passed: `rows=`. See the test below.
    """
    lint = pytest.importorskip("lint")
    result = compose_chevron_stack(
        _stages(count), _supports(supports),
        spec={"item_width": item_width, "item_height": item_height,
              "support_position": position},
    )
    payload, stages, strips = _numbered(result)
    roles = {"stage": stages}
    stacks = [("horizontal", stages)]
    if strips:
        roles["support"] = strips
        stacks.append(("vertical", strips))

    report = lint.lint_diagram(payload, roles=roles, stacks=stacks)
    label = (f"{item_width}x{item_height} n={count} supports={supports} "
             f"{position}")
    assert report.clean, f"{label}: {[str(f) for f in report.errors]}"
    assert report.metrics["overlaps"] == 0
    assert report.metrics["roles_with_inconsistent_sizing"] == 0
    # Warnings are reported and do not block, but this grammar should not
    # produce any of the ones these groupings can raise.
    noisy = [f for f in report.warnings
             if f.rule in ("ragged-stack", "staggered-stack")]
    assert not noisy, f"{label}: {[str(f) for f in noisy]}"


@pytest.mark.parametrize("count", [3, 5, 12])
def test_declaring_the_chain_as_a_row_is_what_the_linter_rejects(count):
    """The honest half of the overlap question, stated as a test.

    The spacing rule errors on a group declared as a ROW whose members have no
    whitespace between them, and it is RIGHT to: a row with no gaps does not
    read as a row. A chevron stack is not a row, and the fix is the declaration,
    not a looser rule - loosening it would blind the rule on every grammar that
    really does lay out a row.

    This test exists so that the requirement is enforced rather than merely
    documented: if someone later decides a chevron stack should be passed as
    `rows=`, this fails and says why.
    """
    lint = pytest.importorskip("lint")
    result = compose_chevron_stack(_stages(count))
    payload, stages, _ = _numbered(result)

    as_row = lint.lint_diagram(payload, rows=[stages])
    assert not as_row.clean
    assert [f.rule for f in as_row.errors] == ["pitch"]

    as_stack = lint.lint_diagram(payload, stacks=[("horizontal", stages)])
    assert as_stack.clean
    assert as_stack.metrics["overlaps"] == 0


@pytest.mark.parametrize("item_width,item_height", SHAPES)
@pytest.mark.parametrize("count", COUNTS)
def test_the_linter_sees_no_overlap_however_deep_the_notch(
        item_width, item_height, count):
    """The notch depth is ink and never reaches the linter, at any depth.

    The point of the whole design: a grammar that expressed the interlock by
    overlapping the rects would fire the overlap rule on correct output at every
    count above one, and there would be no honest way out of it.
    """
    lint = pytest.importorskip("lint")
    for notch in NOTCHES:
        if item_width * notch // 100 <= 0:
            continue
        result = compose_chevron_stack(
            _stages(count), _supports(2),
            spec={"item_width": item_width, "item_height": item_height,
                  "notch_percent": notch},
        )
        payload, _, _ = _numbered(result)
        report = lint.lint_diagram(payload)
        assert report.metrics["overlaps"] == 0, (
            f"{item_width}x{item_height} n={count} notch={notch}")
        assert not [f for f in report.findings if f.rule == "overlap"]


# ---------------------------------------------------------------------------
# Defaults
# ---------------------------------------------------------------------------
def test_the_default_spec_composes_something_sane():
    result = compose_chevron_stack(_stages(5), _supports(3))
    assert result["grammar"] == "chevron_stack"
    assert result["item_width"] == 140
    assert result["notch_percent"] == 20
    assert result["notch_depth"] == 28
    assert result["support_height"] == 30
    assert_no_overlaps(result["items"], "defaults")
    for stage in _by_role(result, "stage"):
        assert rect_width(stage) == 140
        assert rect_height(stage) == 60


def test_the_default_spec_is_not_mutated_by_a_call():
    before = dict(DEFAULT_CHEVRON_SPEC)
    compose_chevron_stack(_stages(2), spec={"item_width": 999})
    assert DEFAULT_CHEVRON_SPEC == before

#!/usr/bin/env python3
"""Tests for the matrix layout grammar.

Run from the repository root:

    python -m pytest ea-diagram-composition/tools/test_compose_matrix.py -q

Nothing here touches a repository, a COM object or the filesystem. If any test
in this file needs Sparx EA to pass, the layer boundary has been broken.

Three conventions worth reading before editing:

* `assert_no_overlaps` is applied to comparable sets. Items are nested inside
  their cells by design, so a set mixing items and containers is SUPPOSED to
  overlap. Unlike the nested grid, this grammar's containers never nest, so the
  whole container set is compared against itself.
* Rect intersection is tested in EA's flipped-y convention, where `top` is
  greater than `bottom`.
* THE SWEEPS ARE THE POINT. One hand-picked example proves nothing about a
  spacing rule: this grammar's geometry is a function of the content, so the
  clearance tests run over counts 1..12 on both axes and over item shapes from
  20x20 to 400x30, and the assertions are exact equalities rather than "no
  overlap". A margin that happens to hold for a 140x60 box is not a derivation.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

from compose import LayoutError, rects_overlap  # noqa: E402
from compose_matrix import DEFAULT_MATRIX_SPEC, compose_matrix  # noqa: E402


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------
# Shapes chosen to span the failure modes a single example hides: a near-square
# box (where a diagonal-shaped clearance rule and an axis-shaped one differ
# most), a very wide flat one, a very tall thin one, something tiny and
# something large.
SHAPES = [(140, 60), (90, 88), (400, 30), (30, 400), (20, 20), (260, 180)]

COUNTS = list(range(0, 13))


def _span(r):
    return (r["left"], r["top"], r["right"], r["bottom"])


def assert_no_overlaps(rects, label=""):
    rects = list(rects)
    for i, a in enumerate(rects):
        for b in rects[i + 1:]:
            assert not rects_overlap(a, b), (
                f"{label}: overlap between {a.get('id')} {_span(a)} and "
                f"{b.get('id')} {_span(b)}"
            )


def contains(outer, inner) -> bool:
    return (outer["left"] <= inner["left"] and outer["right"] >= inner["right"]
            and outer["top"] >= inner["top"]
            and outer["bottom"] <= inner["bottom"])


def assert_result_sane(result, label=""):
    """Everything this grammar promises about any result at all."""
    cells = {c["id"]: c for c in result["containers"] if c["kind"] == "cell"}
    for box in [*result["containers"], *result["items"]]:
        assert box["right"] > box["left"], f"{label}: {box['id']} has no width"
        assert box["top"] > box["bottom"], f"{label}: {box['id']} has no height"
    assert_no_overlaps(result["containers"], f"{label}: containers")
    assert_no_overlaps(result["items"], f"{label}: items")
    for item in result["items"]:
        cell = cells[item["container_id"]]
        assert contains(cell, item), (
            f"{label}: item {item['id']} {_span(item)} escapes its cell "
            f"{_span(cell)}"
        )


def headers(n, prefix):
    return [{"name": f"{prefix} {i}"} for i in range(n)]


def build(rows=2, columns=3, counts=None, spec=None, corner=None,
          start_id=1000):
    """A matrix of `rows` x `columns` whose cell contents follow `counts`.

    `counts` is a flat list read row-major; a None entry means no cell was
    stated at that address at all, which is different from a cell stated with
    no items and is worth exercising both ways.
    """
    row_headers = headers(rows, "Row")
    column_headers = headers(columns, "Column")
    cells = []
    next_id = start_id
    for r in range(rows):
        for c in range(columns):
            n = None
            if counts is not None:
                n = counts[(r * columns + c) % len(counts)]
            if n is None:
                continue
            items = [{"id": next_id + k, "name": f"Element {next_id + k}"}
                     for k in range(n)]
            next_id += max(n, 1)
            cells.append({"row": f"Row {r}", "column": f"Column {c}",
                          "items": items})
    return compose_matrix(row_headers, column_headers, cells, spec=spec,
                          corner=corner)


def by_kind(result, kind):
    return [c for c in result["containers"] if c["kind"] == kind]


def cell_at(result, row, column):
    for c in result["containers"]:
        if c["kind"] == "cell" and c["row"] == row and c["column"] == column:
            return c
    raise AssertionError(f"no cell at {row},{column}")


# ---------------------------------------------------------------------------
# The coordinate convention, first, because everything else leans on it
# ---------------------------------------------------------------------------
def test_a_cell_is_built_in_eas_inverted_y_convention():
    result = build(rows=2, columns=2, counts=[1])
    top_left = cell_at(result, 0, 0)
    below = cell_at(result, 1, 0)
    assert top_left["top"] > top_left["bottom"]
    assert top_left["top"] - top_left["bottom"] == result["cell_height"]
    assert below["top"] < top_left["top"], "moving down makes coordinates more negative"
    assert below["left"] == top_left["left"]


def test_the_composition_starts_at_the_origin():
    spec = {"origin_left": 77, "origin_top": -88}
    result = build(rows=3, columns=3, counts=[1], spec=spec,
                   corner={"name": "Westbrook Bank"})
    assert result["bounds"]["left"] == 77
    assert result["bounds"]["top"] == -88


# ---------------------------------------------------------------------------
# Headers: in the lattice, out of the cells' extent
# ---------------------------------------------------------------------------
def test_the_grid_starts_clear_of_both_header_strips():
    s = dict(DEFAULT_MATRIX_SPEC)
    result = build(rows=2, columns=2, counts=[1])
    first = cell_at(result, 0, 0)
    assert first["left"] == (s["origin_left"] + s["row_header_width"]
                             + s["cell_gap_x"])
    assert first["top"] == (s["origin_top"] - s["column_header_height"]
                            - s["cell_gap_y"])


@pytest.mark.parametrize("rows,columns", [(1, 1), (1, 7), (7, 1), (4, 6), (12, 12)])
def test_headers_share_the_grids_pitches(rows, columns):
    """A finger run along a header lands on that row, at every size."""
    result = build(rows=rows, columns=columns, counts=[0, 2, 1])
    for h in by_kind(result, "row_header"):
        cell = cell_at(result, h["index"], 0)
        assert h["top"] == cell["top"]
        assert h["bottom"] == cell["bottom"]
    for h in by_kind(result, "column_header"):
        cell = cell_at(result, 0, h["index"])
        assert h["left"] == cell["left"]
        assert h["right"] == cell["right"]


def test_a_header_strips_thickness_is_its_own_not_a_cells():
    """A long row name widens the strip and leaves the cells exactly as they were."""
    narrow = build(rows=2, columns=2, counts=[2])
    wide = build(rows=2, columns=2, counts=[2],
                 spec={"row_header_width": 600, "column_header_height": 200})
    assert wide["cell_width"] == narrow["cell_width"]
    assert wide["cell_height"] == narrow["cell_height"]
    assert wide["row_pitch"] == narrow["row_pitch"]
    assert wide["column_pitch"] == narrow["column_pitch"]
    assert by_kind(wide, "row_header")[0]["right"] - \
        by_kind(wide, "row_header")[0]["left"] == 600


def test_label_length_changes_no_geometry_at_all():
    """Names are passed through; nothing here measures a string.

    Worth pinning rather than assuming: a grammar that sized a header to its
    text would make every matrix's geometry depend on its labels, and the
    quality bar asks for very long and very short ones.
    """
    def geometry(name):
        result = compose_matrix(
            [{"name": name}, {"name": "R"}],
            [{"name": name}, {"name": "C"}],
            [{"row": name, "column": name,
              "items": [{"id": 1, "name": name}, {"id": 2, "name": "x"}]}],
        )
        return [(c["kind"], _span(c)) for c in result["containers"]], \
               [_span(i) for i in result["items"]]

    assert geometry("A" * 400) == geometry("A")


def test_the_corner_is_reserved_whether_or_not_a_box_is_drawn_there():
    without = build(rows=2, columns=2, counts=[1])
    with_corner = build(rows=2, columns=2, counts=[1],
                        corner={"name": "Westbrook Bank"})
    assert by_kind(without, "corner") == []
    assert len(by_kind(with_corner, "corner")) == 1
    assert cell_at(without, 0, 0) == cell_at(with_corner, 0, 0)
    corner = by_kind(with_corner, "corner")[0]
    assert corner["left"] == with_corner["bounds"]["left"]
    assert corner["top"] == with_corner["bounds"]["top"]


# ---------------------------------------------------------------------------
# Uniform cells - the answer to "sized to content or not"
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("counts", [
    [0], [1], [0, 1, 2, 3], [9, 0, 1], [12, 1], [None, 4, None, 1],
])
def test_every_cell_is_the_same_size_however_full_it_is(counts):
    result = build(rows=3, columns=4, counts=counts)
    widths = {c["right"] - c["left"] for c in by_kind(result, "cell")}
    heights = {c["top"] - c["bottom"] for c in by_kind(result, "cell")}
    assert widths == {result["cell_width"]}
    assert heights == {result["cell_height"]}
    assert len(by_kind(result, "cell")) == 12, "every address gets a cell"


def test_the_fullest_cell_sets_the_size_for_every_other_one():
    """The price of a regular grid, stated out loud and reported on the result."""
    lean = build(rows=2, columns=2, counts=[1])
    full = build(rows=2, columns=2, counts=[1, 1, 1, 9])
    assert full["items_per_cell_max"] == 9
    assert full["cell_width"] > lean["cell_width"]
    assert full["cell_height"] > lean["cell_height"]
    # And the cell holding one element is just as big as the one holding nine.
    assert (cell_at(full, 0, 0)["right"] - cell_at(full, 0, 0)["left"]
            == cell_at(full, 1, 1)["right"] - cell_at(full, 1, 1)["left"])


def test_min_cell_size_is_a_floor_and_yields_to_a_fuller_cell():
    floored = build(rows=1, columns=2, counts=[1],
                    spec={"min_cell_width": 900, "min_cell_height": 500})
    assert floored["cell_width"] == 900
    assert floored["cell_height"] == 500
    crowded = build(rows=1, columns=2, counts=[9],
                    spec={"min_cell_width": 100, "min_cell_height": 100})
    assert crowded["cell_width"] > 100
    assert crowded["cell_height"] > 100


def test_the_reported_pitches_are_the_ones_actually_used():
    result = build(rows=3, columns=3, counts=[0, 5, 2])
    cells = by_kind(result, "cell")
    lefts = sorted({c["left"] for c in cells})
    tops = sorted({c["top"] for c in cells}, reverse=True)
    assert [b - a for a, b in zip(lefts, lefts[1:])] == \
        [result["column_pitch"]] * 2
    assert [a - b for a, b in zip(tops, tops[1:])] == [result["row_pitch"]] * 2


# ---------------------------------------------------------------------------
# Empty cells - the answer to "hole or drawn-but-blank box"
# ---------------------------------------------------------------------------
def test_an_empty_cell_keeps_its_whole_slot_and_says_it_is_empty():
    result = build(rows=2, columns=2, counts=[3, None, 0, 1])
    unstated = cell_at(result, 0, 1)
    stated_but_bare = cell_at(result, 1, 0)
    populated = cell_at(result, 0, 0)
    assert unstated["empty"] is True
    assert stated_but_bare["empty"] is True
    assert populated["empty"] is False
    for blank in (unstated, stated_but_bare):
        assert blank["right"] - blank["left"] == result["cell_width"]
        assert blank["top"] - blank["bottom"] == result["cell_height"]
    assert result["cells_empty"] == 2


def test_a_matrix_with_no_cells_at_all_is_still_a_grid():
    result = compose_matrix(headers(3, "Row"), headers(4, "Column"))
    assert result["items"] == []
    assert len(by_kind(result, "cell")) == 12
    assert result["cells_empty"] == 12
    assert all(c["empty"] for c in by_kind(result, "cell"))
    assert_result_sane(result, "wholly empty")


def test_a_gap_does_not_shift_the_cells_after_it():
    """The lattice is the thing a reader counts along, so a hole cannot move it."""
    dense = build(rows=2, columns=3, counts=[1])
    sparse = build(rows=2, columns=3, counts=[1, None, 1, None, 1, None])
    assert dense["column_pitch"] == sparse["column_pitch"]
    for r in range(2):
        for c in range(3):
            assert _span(cell_at(dense, r, c)) == _span(cell_at(sparse, r, c))


# ---------------------------------------------------------------------------
# More than one element in a cell
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("n,expected_columns,expected_rows", [
    (1, 1, 1), (2, 2, 1), (3, 2, 2), (4, 2, 2), (5, 3, 2), (6, 3, 2),
    (7, 3, 3), (8, 3, 3), (9, 3, 3), (10, 4, 3), (11, 4, 3), (12, 4, 3),
])
def test_a_full_cell_is_a_near_square_sub_grid(n, expected_columns, expected_rows):
    result = build(rows=1, columns=1, counts=[n])
    items = result["items"]
    assert len(items) == n
    assert max(i["cell_column"] for i in items) == expected_columns - 1
    assert max(i["cell_row"] for i in items) == expected_rows - 1


def test_cell_columns_fixes_the_sub_grid_for_every_cell():
    result = build(rows=1, columns=2, counts=[6, 4], spec={"cell_columns": 6})
    assert max(i["cell_row"] for i in result["items"]) == 0
    assert max(i["cell_column"] for i in result["items"]) == 5


def test_the_block_of_elements_is_centered_in_its_cell():
    result = build(rows=1, columns=1, counts=[1])
    cell = cell_at(result, 0, 0)
    item = result["items"][0]
    assert item["left"] - cell["left"] == cell["right"] - item["right"]
    assert cell["top"] - item["top"] == item["bottom"] - cell["bottom"]


def test_align_center_moves_only_the_partly_filled_last_row():
    left = build(rows=1, columns=1, counts=[3])
    centered = build(rows=1, columns=1, counts=[3], spec={"align": "center"})
    assert _span(left["items"][0]) == _span(centered["items"][0])
    assert _span(left["items"][1]) == _span(centered["items"][1])
    assert centered["items"][2]["left"] > left["items"][2]["left"]
    assert_result_sane(centered, "centered last row")


def test_an_element_keeps_the_callers_id_and_name_and_its_address():
    result = compose_matrix(
        [{"name": "Business", "id": "R1"}],
        [{"name": "Behavior", "id": 7}],
        [{"row": "R1", "column": 7, "items": [{"id": 4242, "name": "Payments"}]}],
    )
    item = result["items"][0]
    assert item["id"] == 4242
    assert item["name"] == "Payments"
    assert item["row_key"] == "R1"
    assert item["column_key"] == 7
    assert item["row"] == 0 and item["column"] == 0
    assert item["container_id"] == result["containers"][-1]["id"]


# ---------------------------------------------------------------------------
# THE CLEARANCE CONDITION, over shapes and counts
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("rows", [1, 2, 3, 5, 8, 12])
@pytest.mark.parametrize("columns", [1, 2, 3, 5, 8, 12])
def test_neighboring_cells_clear_each_other_by_exactly_the_gap(rows, columns):
    """The derivation, checked as an equality rather than as "no overlap".

    Cells sit on a lattice, so the clearance is `pitch - extent` on each axis
    and nothing else. If that ever stops being exactly the gap, the pitch has
    drifted away from the size and an overlap is one content change away.
    """
    for item_w, item_h in SHAPES:
        spec = {"item_width": item_w, "item_height": item_h,
                "cell_gap_x": 7, "cell_gap_y": 5}
        result = build(rows=rows, columns=columns,
                       counts=[0, 1, 2, 3, 5, 9, None, 12], spec=spec)
        label = f"{rows}x{columns} {item_w}x{item_h}"
        assert result["column_pitch"] - result["cell_width"] == 7, label
        assert result["row_pitch"] - result["cell_height"] == 5, label
        for r in range(rows):
            for c in range(columns):
                here = cell_at(result, r, c)
                if c + 1 < columns:
                    assert cell_at(result, r, c + 1)["left"] - here["right"] == 7, label
                if r + 1 < rows:
                    assert here["bottom"] - cell_at(result, r + 1, c)["top"] == 5, label
        assert_result_sane(result, label)


@pytest.mark.parametrize("n", COUNTS)
def test_elements_in_a_cell_clear_each_other_by_exactly_the_item_gap(n):
    for item_w, item_h in SHAPES:
        spec = {"item_width": item_w, "item_height": item_h,
                "item_gap_x": 9, "item_gap_y": 11}
        result = build(rows=2, columns=2, counts=[n, 0, None, 1], spec=spec)
        label = f"n={n} {item_w}x{item_h}"
        rows_of = {}
        columns_of = {}
        for item in result["items"]:
            key = (item["container_id"], item["cell_row"])
            rows_of.setdefault(key, []).append(item)
            key = (item["container_id"], item["cell_column"])
            columns_of.setdefault(key, []).append(item)
        for members in rows_of.values():
            members.sort(key=lambda i: i["left"])
            gaps = [b["left"] - a["right"] for a, b in zip(members, members[1:])]
            assert set(gaps) <= {9}, f"{label}: horizontal gaps {gaps}"
        for members in columns_of.values():
            members.sort(key=lambda i: -i["top"])
            gaps = [a["bottom"] - b["top"] for a, b in zip(members, members[1:])]
            assert set(gaps) <= {11}, f"{label}: vertical gaps {gaps}"
        assert_result_sane(result, label)


@pytest.mark.parametrize("cell_pad", [0, 1, 40])
def test_every_element_stays_inside_its_cell_at_any_padding(cell_pad):
    for item_w, item_h in SHAPES:
        for n in (1, 2, 3, 7, 12):
            result = build(rows=2, columns=2, counts=[n, 1, 0, None],
                           spec={"item_width": item_w, "item_height": item_h,
                                 "cell_pad": cell_pad})
            assert_result_sane(result, f"pad={cell_pad} n={n} {item_w}x{item_h}")


@pytest.mark.parametrize("key", ["cell_gap_x", "cell_gap_y",
                                 "item_gap_x", "item_gap_y"])
def test_a_zero_gap_is_refused_rather_than_drawn(key):
    """Two boxes that touch do not read as two, and the grid is the message."""
    with pytest.raises(LayoutError) as excinfo:
        build(rows=2, columns=2, counts=[4], spec={key: 0})
    assert f"spec.{key}" in str(excinfo.value)
    assert "touch" in str(excinfo.value)


@pytest.mark.parametrize("rows,columns", [(1, 1), (1, 12), (12, 1)])
def test_a_single_row_or_a_single_column_is_a_matrix(rows, columns):
    result = build(rows=rows, columns=columns, counts=[0, 3, 1])
    assert result["rows"] == rows and result["columns"] == columns
    assert len(by_kind(result, "cell")) == rows * columns
    assert len(by_kind(result, "row_header")) == rows
    assert len(by_kind(result, "column_header")) == columns
    assert_result_sane(result, f"{rows}x{columns}")


def test_tall_content_and_short_content_both_survive():
    for item_w, item_h in [(20, 20), (400, 30), (30, 400)]:
        result = build(rows=3, columns=3, counts=[0, 1, 5, 12],
                       spec={"item_width": item_w, "item_height": item_h})
        assert_result_sane(result, f"{item_w}x{item_h}")


# ---------------------------------------------------------------------------
# The other seam: the shipped linter, over the same content variation
# ---------------------------------------------------------------------------
def _payload(result):
    """The result as `verify_diagram` would hand it to the linter."""
    objects = []
    numeric_id = {}
    for box in [*result["containers"], *result["items"]]:
        numeric_id[box["id"]] = len(objects) + 1
        objects.append({
            "element_id": numeric_id[box["id"]],
            "name": box.get("name") or "",
            "left": box["left"], "top": box["top"],
            "right": box["right"], "bottom": box["bottom"],
        })
    b = result["bounds"]
    payload = {
        "objects": objects, "links": [],
        "canvas": {"cx": b["width"] + 100, "cy": b["height"] + 100},
    }
    return payload, objects, numeric_id


def _groupings(result, objects, numeric_id):
    """What the generator knows and geometry does not: rows, columns, stacks."""
    at = {o["element_id"]: o for o in objects}

    def obj(box):
        return at[numeric_id[box["id"]]]

    cells = by_kind(result, "cell")
    row_headers = [obj(h) for h in by_kind(result, "row_header")]
    column_headers = [obj(h) for h in by_kind(result, "column_header")]

    rows_of_cells = [[obj(c) for c in cells if c["row"] == r]
                     for r in range(result["rows"])]
    columns_of_cells = [[obj(c) for c in cells if c["column"] == c_i]
                        for c_i in range(result["columns"])]

    # Elements within one cell, one lint row per sub-grid row and one lint
    # column per sub-grid column. A matrix row is NOT a lint row: it crosses
    # cell boundaries, so its gaps alternate between the item gap and the cell
    # gap and are not meant to be even.
    item_rows: dict = {}
    item_columns: dict = {}
    for item in result["items"]:
        item_rows.setdefault((item["container_id"], item["cell_row"]), []) \
            .append(obj(item))
        item_columns.setdefault((item["container_id"], item["cell_column"]), []) \
            .append(obj(item))

    roles = {
        "cell": [obj(c) for c in cells],
        "row header": row_headers,
        "column header": column_headers,
        "element": [obj(i) for i in result["items"]],
    }
    stacks = [("vertical", row_headers), ("horizontal", column_headers)]
    stacks += [("vertical", group) for group in columns_of_cells]
    stacks += [("horizontal", group) for group in rows_of_cells]
    return {
        "roles": roles,
        "rows": rows_of_cells + list(item_rows.values()),
        "columns": columns_of_cells + list(item_columns.values()),
        "stacks": stacks,
    }


@pytest.mark.parametrize("rows,columns,counts", [
    (1, 1, [1]),
    (1, 12, [0, 1, 2]),
    (12, 1, [3, None, 1]),
    (3, 4, [0]),
    (3, 4, [None, 1, 9, 0, 4, None, 2, 12]),
    (6, 6, [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 0, None]),
    (12, 12, [0, 1, None, 5]),
    (2, 3, [12]),
])
def test_the_shipped_linter_is_clean_across_content_variation(rows, columns, counts):
    """THE OTHER SEAM, and the one that would catch a drifted pitch.

    The linter measures the finished rectangles; this engine produces them. Two
    independent statements of one rule drift apart unless something compares
    them, and this is that something. It runs over the same content variation
    the geometry tests do, because a linter run on one example is the failure
    mode this project has already paid for.
    """
    lint = pytest.importorskip("lint")
    for item_w, item_h in SHAPES:
        result = build(rows=rows, columns=columns, counts=counts,
                       spec={"item_width": item_w, "item_height": item_h})
        payload, objects, numeric_id = _payload(result)
        report = lint.lint_diagram(payload, **_groupings(result, objects,
                                                         numeric_id))
        label = f"{rows}x{columns} {counts} {item_w}x{item_h}"
        assert report.clean, f"{label}: {[str(f) for f in report.errors]}"
        noisy = [f for f in report.findings
                 if f.rule in ("pitch", "uniform-sizing", "ragged-stack",
                               "staggered-stack", "overlap")]
        assert not noisy, f"{label}: {[str(f) for f in noisy]}"
        assert report.metrics["overlaps"] == 0, label
        assert report.metrics["worst_pitch_spread"] == 0, label
        assert report.metrics["roles_with_inconsistent_sizing"] == 0, label


def test_the_linter_actually_measured_something():
    """A clean report over no measurable group is not a result.

    `roles_measured` and `pitch_groups_measured` are the denominators the linter
    publishes for exactly this, and asserting on them is what stops the test
    above from passing because nothing was compared.
    """
    lint = pytest.importorskip("lint")
    result = build(rows=4, columns=4, counts=[0, 1, 4, 9])
    payload, objects, numeric_id = _payload(result)
    report = lint.lint_diagram(payload, **_groupings(result, objects, numeric_id))
    assert report.metrics["roles_measured"] == 4
    assert report.metrics["pitch_groups_measured"] > 0
    assert report.metrics["worst_stack_extent_spread"] == 0
    assert report.metrics["worst_stack_alignment_spread"] == 0


# ---------------------------------------------------------------------------
# Determinism
# ---------------------------------------------------------------------------
def test_the_same_input_composes_identically():
    first = build(rows=4, columns=5, counts=[0, 2, None, 7, 1])
    second = build(rows=4, columns=5, counts=[0, 2, None, 7, 1])
    assert first == second


def test_the_order_cells_are_given_in_does_not_move_them():
    rows = headers(2, "Row")
    columns = headers(2, "Column")
    cells = [
        {"row": "Row 0", "column": "Column 0", "items": [{"id": 1}]},
        {"row": "Row 1", "column": "Column 1", "items": [{"id": 2}, {"id": 3}]},
    ]
    forward = compose_matrix(rows, columns, cells)
    backward = compose_matrix(rows, columns, list(reversed(cells)))
    assert forward == backward


def test_output_does_not_depend_on_spec_key_insertion_order():
    one = build(spec={"item_width": 200, "cell_gap_x": 30, "cell_pad": 4})
    two = build(spec={"cell_pad": 4, "cell_gap_x": 30, "item_width": 200})
    assert one == two


# ---------------------------------------------------------------------------
# Refusals, each naming the offending field
# ---------------------------------------------------------------------------
def test_a_matrix_needs_at_least_one_row_and_one_column():
    with pytest.raises(LayoutError, match="rows"):
        compose_matrix([], headers(2, "Column"))
    with pytest.raises(LayoutError, match="columns"):
        compose_matrix(headers(2, "Row"), [])


def test_a_header_needs_a_name():
    with pytest.raises(LayoutError, match=r"rows\[1\].name"):
        compose_matrix([{"name": "A"}, {"id": "b"}], headers(1, "Column"))


def test_two_rows_cannot_share_an_address_key():
    with pytest.raises(LayoutError, match="duplicate row key"):
        compose_matrix([{"name": "A"}, {"name": "A"}], headers(1, "Column"))


def test_a_row_and_a_column_may_share_a_key():
    """An address names one of each, so there is nothing ambiguous about it."""
    result = compose_matrix([{"name": "People"}], [{"name": "People"}],
                            [{"row": "People", "column": "People",
                              "items": [{"id": 1}]}])
    assert len(result["items"]) == 1


def test_an_unknown_address_lists_the_keys_that_would_have_worked():
    with pytest.raises(LayoutError) as excinfo:
        compose_matrix(headers(2, "Row"), headers(2, "Column"),
                       [{"row": "Row 9", "column": "Column 0"}])
    message = str(excinfo.value)
    assert "cells[0].row" in message
    assert "'Row 0'" in message and "'Row 1'" in message


def test_a_cell_without_an_address_is_an_error_not_a_guess():
    with pytest.raises(LayoutError, match=r"cells\[0\].column"):
        compose_matrix(headers(1, "Row"), headers(1, "Column"),
                       [{"row": "Row 0", "items": [{"id": 1}]}])


def test_two_cells_cannot_claim_one_address():
    with pytest.raises(LayoutError, match="already given"):
        compose_matrix(headers(1, "Row"), headers(1, "Column"), [
            {"row": "Row 0", "column": "Column 0", "items": [{"id": 1}]},
            {"row": "Row 0", "column": "Column 0", "items": [{"id": 2}]},
        ])


def test_sizing_stated_on_a_cell_is_refused_rather_than_ignored():
    with pytest.raises(LayoutError) as excinfo:
        compose_matrix(headers(1, "Row"), headers(1, "Column"),
                       [{"row": "Row 0", "column": "Column 0",
                         "item_width": 300, "items": [{"id": 1}]}])
    assert "item_width" in str(excinfo.value)
    assert "cells[0]" in str(excinfo.value)


def test_duplicate_element_ids_are_rejected_across_the_whole_matrix():
    with pytest.raises(LayoutError, match="duplicate id"):
        compose_matrix(headers(2, "Row"), headers(1, "Column"), [
            {"row": "Row 0", "column": "Column 0", "items": [{"id": 5}]},
            {"row": "Row 1", "column": "Column 0", "items": [{"id": 5}]},
        ])


def test_an_element_id_cannot_collide_with_a_cells_or_a_headers():
    with pytest.raises(LayoutError, match="duplicate id"):
        compose_matrix([{"name": "Row", "id": "shared"}], headers(1, "Column"),
                       [{"row": "shared", "column": "Column 0",
                         "items": [{"id": "shared"}]}])


def test_an_element_needs_an_id():
    with pytest.raises(LayoutError, match=r"cells\[0\].items\[0\].id"):
        compose_matrix(headers(1, "Row"), headers(1, "Column"),
                       [{"row": "Row 0", "column": "Column 0",
                         "items": [{"name": "nameless"}]}])


def test_an_unhashable_id_is_rejected_with_a_clear_reason():
    with pytest.raises(LayoutError, match="hashable"):
        compose_matrix(headers(1, "Row"), headers(1, "Column"),
                       [{"row": "Row 0", "column": "Column 0",
                         "items": [{"id": ["not", "hashable"]}]}])


def test_an_unknown_spec_key_is_an_error_not_a_shrug():
    with pytest.raises(LayoutError, match="unknown key"):
        build(spec={"radius": 200})


def test_bad_enum_values_are_rejected():
    with pytest.raises(LayoutError, match="spec.align"):
        build(spec={"align": "middle"})


def test_booleans_are_not_accepted_as_sizes():
    with pytest.raises(LayoutError, match="spec.item_width"):
        build(spec={"item_width": True})


def test_negative_sizes_are_rejected_by_name():
    with pytest.raises(LayoutError, match="spec.cell_pad"):
        build(spec={"cell_pad": -1})
    with pytest.raises(LayoutError, match="spec.row_header_width"):
        build(spec={"row_header_width": 0})
    with pytest.raises(LayoutError, match="spec.min_cell_width"):
        build(spec={"min_cell_width": -5})


def test_the_wrong_container_type_is_reported_with_its_path():
    with pytest.raises(LayoutError, match=r"rows\[0\]"):
        compose_matrix(["Row 0"], headers(1, "Column"))
    with pytest.raises(LayoutError, match="cells"):
        compose_matrix(headers(1, "Row"), headers(1, "Column"), "not a list")

#!/usr/bin/env python3
"""Matrix layout: a regular grid of cells addressed by a row and a column.

A companion to `compose.py` and held to the same rules: pure arithmetic, no
repository calls, no COM, no file or network I/O, no clock, no randomness. Same
input, same output, every time. Nothing here branches on a technology id, a
profile name or a stereotype - sizes, gaps and header thicknesses arrive in a
`spec` dict supplied by the caller.

The coordinate convention is `compose.py`'s, and every rect here is built with
its `rect()` so there is one statement of it:

    left, right   positive, increasing rightward       right > left
    top, bottom   NEGATIVE, increasing upward          top > bottom
    width = right - left, height = top - bottom

WHAT A MATRIX IS
----------------
Rows down the side, columns across the top, and a cell at every intersection.
The reader finds a cell by its ADDRESS - "Business Model, by Network" - which
only works if the grid is regular enough to count along. So the grid is the
fixed part and the cell CONTENT is the part that varies: every cell is the same
size, every column the same pitch, every row the same pitch, whether a cell
holds nothing, one element or nine.

THIS IS NOT `compose_nested_grid`, AND THE DIFFERENCE IS THE SIZING RULE
------------------------------------------------------------------------
The nested grid packs containers by size: a container keeps the size its own
contents need and is deliberately NOT stretched to its cell, because there the
size IS the information - a grouping of twenty should be drawn bigger than a
grouping of two. Its columns are as wide as their widest member, so column two
is a different width from column one, and a cell has no meaning of its own: it
is scaffolding that holds one child.

Here the size is not information and the address is. A cell means "this row
crossed with this column", and that meaning exists whether or not anything
populates it. If cells were sized to their contents, the column boundaries
would wander, an empty cell would collapse and the reader would lose the very
thing they are counting along. So this grammar does the OPPOSITE of the nested
grid on all three counts:

    nested_grid                        matrix
    -----------                        ------
    containers sized by contents       every cell one size, the fullest cell's
    per-column widths, per-row         one pitch across, one pitch down
      heights
    a cell is scaffolding              a cell is the addressable thing
    empty container keeps one          empty cell keeps its FULL slot and is
      cell of space                      returned as a container, marked empty
    no headers                         row and column headers, always drawn
    recursive tree                     two flat header lists plus addressed
                                         cells

Which is `_common_band_width`'s test applied to a second axis: uniform where
the size says nothing, content-driven where it says something. Here what says
something is what is INSIDE a cell, and that is where the variation lives.

WHAT THE TWO REFERENCE FRAMEWORKS DISAGREE ABOUT, AND WHAT WAS BUILT
---------------------------------------------------------------------
Both reference pictures are uniform grids with headers down the side and across
the top, and both keep the lattice regular where content is missing. They part
company on whether a cell is DRAWN:

* One draws every cell as its own box, six by six, with a titled corner box at
  the intersection of the two header strips. Every cell is populated.
* The other draws no cell boxes at all. The row headers are full-width colored
  bands and the columns are translucent full-height strips; a cell exists only
  as the place where a band and a strip cross, the corner is blank, and one
  column stands apart from the rest with nothing in it.

This module builds the FIRST reading and makes the second available from it: a
cell rect is always produced, always the same size, and carries `empty` so a
caller that wants the second picture can skip drawing the boxes that hold
nothing - or all of them - without the geometry changing. A grammar that
emitted a cell only where there was content could not produce the first picture
at all, and could not tell a caller where an empty cell would have been.

HEADERS PARTICIPATE IN THE LATTICE, NOT IN THE CELLS' EXTENT
-------------------------------------------------------------
A row header is exactly as tall as its row and sits on the row's own top edge;
a column header is exactly as wide as its column and sits on the column's own
left edge. So headers share the grid's two pitches and a reader can run a
finger from a header along its row or down its column.

Their THICKNESS is their own: `row_header_width` and `column_header_height`.
A long row name does not squeeze the cells and a full cell does not squash the
header, which is what both reference pictures do - the header strips there are
visibly a different size from a cell in both of them.

Result shape
------------
    {
      "grammar":    "matrix",
      "items":      [ {"id", "container_id", "row", "column", "row_key",
                       "column_key", "index", "cell_row", "cell_column",
                       "left", "top", "right", "bottom", ...}, ... ],
      "containers": [ {"id", "name", "kind", "left", "top", "right", "bottom",
                       ...}, ... ],
      "rows", "columns":                 how many of each
      "cell_width", "cell_height":       the one size every cell came out
      "row_pitch", "column_pitch":       top-to-top and left-to-left steps
      "row_header_width",
      "column_header_height":            the header strips' thickness
      "cells_empty":                     how many cells hold nothing
      "items_per_cell_max":              the fullest cell's item count, which
                                         is what set the cell size
      "bounds":     {"left", "top", "right", "bottom", "width", "height"},
    }

`kind` is "cell", "row_header", "column_header" or "corner". Cells carry `row`,
`column`, `row_key`, `column_key` and `empty`; headers carry `index` and `key`.

Items are nested inside their cells by design, so test the two sets for mutual
disjointness SEPARATELY. Unlike the nested grid, the container set here IS
mutually disjoint - cells never nest - and so is the item set.
"""
from __future__ import annotations

import sys
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any, Optional

_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

from compose import LayoutError, bounding_box, rect  # noqa: E402

__all__ = [
    "DEFAULT_MATRIX_SPEC",
    "compose_matrix",
]


# ---------------------------------------------------------------------------
# Defaults
# ---------------------------------------------------------------------------
# EA diagram units, which for practical purposes are pixels at 100% zoom. Stated
# here rather than imported from `compose.DEFAULT_SPEC` so that this module can
# be read, and its arithmetic checked, without holding a second file open - and
# so that a key this grammar does not have (a radius, a wrap width) cannot be
# passed to it and silently ignored.
DEFAULT_MATRIX_SPEC: dict[str, Any] = {
    # Top-left of the whole composition, which is the top-left of the CORNER -
    # the block where the two header strips cross. `origin_top` is negative
    # because EA's vertical axis is.
    "origin_left": 20,
    "origin_top": -20,

    # One element inside a cell. Uniform everywhere: an element in a matrix
    # stands for the same kind of thing wherever it sits, and the variation this
    # grammar carries is HOW MANY are in a cell, not how big they are.
    "item_width": 140,
    "item_height": 60,

    # Gaps between elements inside one cell. POSITIVE, not merely non-negative -
    # see `_resolve_spec`.
    "item_gap_x": 20,
    "item_gap_y": 20,

    # Clear space inside a cell's border, on every side.
    "cell_pad": 12,

    # Gaps between neighboring cells, and between the header strips and the
    # grid. POSITIVE for the same reason the item gaps are.
    "cell_gap_x": 12,
    "cell_gap_y": 12,

    # How many elements wide a cell's own sub-grid is. None -> ceil(sqrt(n))
    # per cell, which keeps a cell's contents squarish instead of running off
    # sideways. Stated in the SPEC and not per cell, so that two cells holding
    # four elements each are never arranged differently from one another.
    "cell_columns": None,

    # Floors under the derived cell size, for a matrix whose cells are mostly
    # empty and would otherwise come out at one element's size.
    "min_cell_width": None,
    "min_cell_height": None,

    # Thickness of the two header strips. The row header's WIDTH and the column
    # header's HEIGHT are the only two numbers headers add to the geometry;
    # their other dimension is the row's or column's own.
    "row_header_width": 160,
    "column_header_height": 44,

    # "left" or "center": where a cell's last, partly filled sub-grid row sits
    # within the block. The block itself is always centered in its cell.
    "align": "left",
}

_ANY_INT_KEYS = frozenset({"origin_left", "origin_top"})

# `item_gap_*` and `cell_gap_*` are POSITIVE here where `compose.py` allows them
# to be zero, and that is a deliberate departure rather than an oversight. Two
# cells that touch cannot be told apart, and a grid whose cells cannot be told
# apart is not a grid - the reader counts along the boundaries. The shipped
# linter says the same thing about a declared row with no whitespace in it
# anywhere: even spacing does not make a row out of boxes that touch. A caller
# who wants cells to abut wants a table with rules drawn on it, which is a
# different drawing and not this one.
_POSITIVE_KEYS = frozenset({
    "item_width", "item_height", "item_gap_x", "item_gap_y",
    "cell_gap_x", "cell_gap_y", "row_header_width", "column_header_height",
})
_NON_NEGATIVE_KEYS = frozenset({"cell_pad"})
_OPTIONAL_POSITIVE_KEYS = frozenset({
    "cell_columns", "min_cell_width", "min_cell_height",
})
_ALIGNMENTS = ("left", "center")

# Keys that may appear on a header or a cell. Anything else is refused rather
# than ignored, so a spec key written on a cell - `item_width` on the cell that
# holds the big element - is a named error and not an afternoon spent wondering
# why the sizing had no effect.
_ROW_KEYS = frozenset({"id", "name"})
_COLUMN_KEYS = frozenset({"id", "name"})
_CELL_KEYS = frozenset({"id", "name", "row", "column", "items"})
_CORNER_KEYS = frozenset({"id", "name"})


# ---------------------------------------------------------------------------
# Validation - the same shapes and the same `where`-tagged messages as
# `compose.py`, restated here so this module stands on its own.
# ---------------------------------------------------------------------------
def _as_int(value: Any, where: str) -> int:
    """Coerce a number to a whole EA unit, rejecting anything that is not one.

    bool is rejected on purpose: True would otherwise sail through as 1 and
    produce geometry nobody asked for.
    """
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise LayoutError(f"{where}: expected a number, got {type(value).__name__}")
    return int(round(value))


def _require_mapping(value: Any, where: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise LayoutError(f"{where}: expected a dict, got {type(value).__name__}")
    return value


def _require_list(value: Any, where: str) -> list[Any]:
    """Accept any ordered sequence except a string, and keep the caller's order.

    Order is the input here - row order is top-to-bottom order, column order is
    left-to-right order - so a set or a bare dict is rejected rather than
    quietly iterated in whatever order it happens to have.
    """
    if isinstance(value, (str, bytes)) or not isinstance(value, Sequence):
        raise LayoutError(f"{where}: expected a list, got {type(value).__name__}")
    return list(value)


def _named(holder: Mapping[str, Any], where: str) -> str:
    name = holder.get("name")
    if not isinstance(name, str) or not name.strip():
        raise LayoutError(
            f"{where}.name: a non-empty string name is required, got {name!r}"
        )
    return name


def _only_keys(holder: Mapping[str, Any], allowed: frozenset[str],
               where: str) -> None:
    unknown = sorted(str(k) for k in holder if k not in allowed)
    if unknown:
        raise LayoutError(
            f"{where}: unknown key(s) {', '.join(repr(k) for k in unknown)}; "
            f"valid keys here are {', '.join(sorted(allowed))}. Sizing is "
            f"stated in the spec and applies to the whole matrix, because a "
            f"grid whose cells disagree about their size is not a grid"
        )


def _ceil_div(n: int, d: int) -> int:
    return -(-n // d)


def _near_square_columns(n: int) -> int:
    """Columns for `n` elements so a cell's contents come out close to square.

    `ceil(sqrt(n))`, computed with integers because floating point at the
    boundary would make a 16-element cell 5 columns wide on some machines and 4
    on others, and this module promises the same output everywhere.
    """
    c = 1
    while c * c < n:
        c += 1
    return c


def _resolve_spec(spec: Mapping[str, Any] | None) -> dict[str, Any]:
    """Validate a caller spec and fill in the defaults it left out.

    Unknown keys are an error. A typo like `cellGapX`, or a key borrowed from
    another grammar, would otherwise be ignored in silence.
    """
    out = dict(DEFAULT_MATRIX_SPEC)
    if spec is None:
        return out
    spec = _require_mapping(spec, "spec")

    unknown = sorted(str(k) for k in spec if k not in DEFAULT_MATRIX_SPEC)
    if unknown:
        raise LayoutError(
            f"spec: unknown key(s) {', '.join(repr(k) for k in unknown)}; "
            f"valid keys are {', '.join(sorted(DEFAULT_MATRIX_SPEC))}"
        )

    for key, value in spec.items():
        where = f"spec.{key}"
        if key == "align":
            if value not in _ALIGNMENTS:
                raise LayoutError(
                    f"{where}: expected one of {_ALIGNMENTS}, got {value!r}"
                )
            out[key] = value
        elif key in _ANY_INT_KEYS:
            out[key] = _as_int(value, where)
        elif key in _POSITIVE_KEYS:
            n = _as_int(value, where)
            if n <= 0:
                why = ""
                if key.endswith(("gap_x", "gap_y")):
                    why = (". A gap of zero leaves two boxes touching, and two "
                           "boxes that touch do not read as two")
                raise LayoutError(f"{where}: must be positive, got {n}{why}")
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
    return out


def _check_id(value: Any, where: str, seen: dict[Any, str], what: str) -> Any:
    """Claim one id, in whatever type the caller stated it.

    Ids are preserved VERBATIM - ints as ints, strings as strings - because the
    primary consumer maps them back onto EA element ids, which are integers.
    One registry serves items, cells and headers: all four kinds are mapped back
    onto model elements, so one id cannot mean two of them.
    """
    if value is None or (isinstance(value, str) and not value.strip()):
        raise LayoutError(
            f"{where}: every {what} needs a non-empty id, got {value!r}"
        )
    try:
        hash(value)
    except TypeError:
        raise LayoutError(
            f"{where}: an id must be hashable so it can be checked for "
            f"uniqueness, got {type(value).__name__}"
        ) from None
    if value in seen:
        raise LayoutError(
            f"{where}: duplicate id {value!r}, already used at {seen[value]}"
        )
    seen[value] = where
    return value


# ---------------------------------------------------------------------------
# Headers and addresses
# ---------------------------------------------------------------------------
def _plan_headers(raw: Any, where: str, allowed: frozenset[str],
                  axis: str) -> list[dict[str, Any]]:
    """Validate one header list and work out each header's ADDRESS KEY.

    The key is the header's `id` when it has one and its `name` otherwise, and
    it is what a cell addresses. Keys have to be unique within their axis or an
    address would be ambiguous; nothing stops a row and a column sharing a key,
    since an address names one of each.
    """
    headers = _require_list(raw, where)
    if not headers:
        raise LayoutError(
            f"{where}: at least one {axis} is required, got an empty list"
        )
    out: list[dict[str, Any]] = []
    keys: dict[Any, str] = {}
    for i, entry in enumerate(headers):
        hwhere = f"{where}[{i}]"
        header = _require_mapping(entry, hwhere)
        _only_keys(header, allowed, hwhere)
        name = _named(header, hwhere)
        key = header["id"] if "id" in header else name
        if key is None or (isinstance(key, str) and not key.strip()):
            raise LayoutError(
                f"{hwhere}.id: a stated id must be non-empty, got {key!r}"
            )
        try:
            hash(key)
        except TypeError:
            raise LayoutError(
                f"{hwhere}.id: an id must be hashable so it can address a "
                f"cell, got {type(key).__name__}"
            ) from None
        if key in keys:
            raise LayoutError(
                f"{hwhere}: duplicate {axis} key {key!r}, already used at "
                f"{keys[key]}; a cell addresses a {axis} by this key, so two "
                f"{axis}s cannot share one"
            )
        keys[key] = hwhere
        out.append({"header": header, "name": name, "key": key, "index": i,
                    "where": hwhere})
    return out


def _address(cell: Mapping[str, Any], field: str, keyed: Mapping[Any, int],
             where: str, axis: str) -> int:
    """Resolve one half of a cell's address to an index, or say why it cannot.

    Addresses are by KEY only - never by position - because a matrix's rows are
    reordered all the time and a positional address would silently follow the
    move to the wrong row.
    """
    if field not in cell:
        raise LayoutError(
            f"{where}.{field}: a cell needs a {axis}; every cell is addressed "
            f"by a row and a column"
        )
    key = cell[field]
    try:
        found = key in keyed
    except TypeError:
        raise LayoutError(
            f"{where}.{field}: an address must be hashable, got "
            f"{type(key).__name__}"
        ) from None
    if not found:
        known = ", ".join(repr(k) for k in keyed)
        raise LayoutError(
            f"{where}.{field}: no {axis} has the key {key!r}; the {axis} keys "
            f"are {known}"
        )
    return keyed[key]


# ---------------------------------------------------------------------------
# The grammar
# ---------------------------------------------------------------------------
def compose_matrix(
    rows: Sequence[Mapping[str, Any]],
    columns: Sequence[Mapping[str, Any]],
    cells: Optional[Sequence[Mapping[str, Any]]] = None,
    spec: Mapping[str, Any] | None = None,
    corner: Optional[Mapping[str, Any]] = None,
) -> dict[str, Any]:
    """Lay out a matrix: row headers, column headers, and a cell at every cross.

    `rows` and `columns` are ordered header lists - first row at the top, first
    column at the left - each header a dict with a `name` and optionally an
    `id`. `cells` is a FLAT list, each cell naming the row and the column it
    sits at and carrying the elements in it:

        compose_matrix(
            rows=[{"name": "Business"}, {"name": "Application"}],
            columns=[{"name": "Structure"}, {"name": "Behavior"}],
            cells=[
                {"row": "Business", "column": "Structure",
                 "items": [{"id": 101}, {"id": 102}]},
                {"row": "Application", "column": "Behavior",
                 "items": [{"id": 103}]},
            ],
            corner={"name": "Westbrook Bank"},
        )

    A cell addresses its row and column by KEY, which is the header's `id` when
    it has one and its `name` otherwise. Addresses are never positional: rows
    get reordered, and a positional address would follow the move to the wrong
    row without saying so.

    The four questions this grammar has to answer, and the answers it gives:

    * **Cells are UNIFORM, not sized to their content.** One width and one
      height for every cell in the matrix, taken from the FULLEST cell - the one
      whose sub-grid needs the most room - plus `cell_pad` on every side. The
      address is the information here and the size is not, so a cell that varied
      in size would cost the reader the ability to count along a row for nothing
      in return. It is the reverse of `compose_nested_grid`'s rule, deliberately;
      the module docstring sets the two side by side. The price is real and is
      reported rather than hidden: one cell of nine elements makes every cell
      that big, and `items_per_cell_max`, `cell_width` and `cell_height` on the
      result say so.
    * **An empty cell is a drawn-but-blank box, never a hole.** It keeps its
      whole slot, comes back as a container like any other cell, and carries
      `empty: True`. A framework matrix with gaps is the ordinary case, not the
      exception, and an absent rect would both break the lattice the reader
      counts along and leave a caller unable to draw the gap even if they wanted
      to. A caller that wants no box drawn where there is no content skips the
      cells marked empty; one that wants no cell boxes at all - the second
      reference framework - skips all of them. Neither changes the geometry.
    * **A cell holding more than one element lays them out in a sub-grid**,
      `cell_columns` wide, or `ceil(sqrt(n))` when that is None, so a full cell
      comes out squarish rather than as a long row. The block is centered in the
      cell, and `align` places its last, partly filled row within the block. The
      elements are the same size everywhere in the matrix.
    * **Headers participate in the lattice but not in the cells' extent.** A row
      header is exactly as tall as its row and starts on its top edge; a column
      header is exactly as wide as its column and starts on its left edge, so
      both share the grid's pitches. Their thickness is their own
      (`row_header_width`, `column_header_height`), so a long name does not
      squeeze the cells. The corner - where the two strips cross - is always
      RESERVED, and a box is drawn there only when `corner` is given.

    THE CLEARANCE CONDITION, DERIVED RATHER THAN EYEBALLED
    ------------------------------------------------------
    Everything here sits on two axis-aligned lattices, and that makes the
    condition exact rather than a margin. Write `W`, `H` for the cell size and
    `Px = W + cell_gap_x`, `Py = H + cell_gap_y` for the pitches. Cell `(r, c)`
    has its left edge at `Gx + c * Px` and its top at `Gy - r * Py`. For two
    distinct cells, either `c != c'`, and their left edges differ by at least
    `Px`, leaving `Px - W = cell_gap_x` of clear space between them; or `c = c'`
    and `r != r'`, leaving `Py - H = cell_gap_y`. So a positive gap on each axis
    is exactly the condition, and **both gaps are required to be positive** -
    see `_POSITIVE_KEYS` for why zero is refused rather than tolerated.

    The same argument, one level down, separates the elements inside a cell:
    their pitches are `item_width + item_gap_x` and `item_height + item_gap_y`,
    both gaps positive. And every element is inside its own cell's border,
    because the block is centered in a cell at least `2 * cell_pad` wider and
    taller than the widest and tallest block in the matrix, so each margin is at
    least `cell_pad >= 0`. Elements in different cells are therefore at least a
    cell gap apart as well.

    Headers clear the grid by the same two gaps: the grid starts at
    `origin_left + row_header_width + cell_gap_x` and
    `origin_top - column_header_height - cell_gap_y`. Row headers share the
    rows' pitch and column headers the columns', so they clear each other by the
    same gaps the cells do, and the corner clears both strips on one axis each.

    WHAT THIS DELIBERATELY IS NOT
    ------------------------------
    There is no spanning: a cell occupies one row and one column, and a merged
    two-column cell would be an address that is not an address. There is no
    per-row height or per-column width, for the reason given above. And the
    connectors are not this grammar's job - a matrix is normally read without
    any, which is part of why it is worth drawing.

    Returns the result dict described in the module docstring - including what
    it actually did, since the cell size is derived from the content and may be
    far larger than one element. Raises `LayoutError` for any input that cannot
    yield sane geometry.
    """
    s = _resolve_spec(spec)
    row_plans = _plan_headers(rows, "rows", _ROW_KEYS, "row")
    column_plans = _plan_headers(columns, "columns", _COLUMN_KEYS, "column")
    row_index = {p["key"]: p["index"] for p in row_plans}
    column_index = {p["key"]: p["index"] for p in column_plans}

    seen_ids: dict[Any, str] = {}

    # ---- cells: address them, claim their ids, measure their contents -------
    raw_cells = _require_list(cells if cells is not None else [], "cells")
    placed: dict[tuple[int, int], dict[str, Any]] = {}
    for k, raw_cell in enumerate(raw_cells):
        where = f"cells[{k}]"
        cell = _require_mapping(raw_cell, where)
        _only_keys(cell, _CELL_KEYS, where)
        r = _address(cell, "row", row_index, where, "row")
        c = _address(cell, "column", column_index, where, "column")
        if (r, c) in placed:
            raise LayoutError(
                f"{where}: a cell for row {cell['row']!r} and column "
                f"{cell['column']!r} was already given at "
                f"{placed[(r, c)]['where']}; one address holds one cell, and "
                f"two would draw one box over the other"
            )
        raw_items = _require_list(cell.get("items", []), f"{where}.items")
        items: list[Mapping[str, Any]] = []
        for j, raw_item in enumerate(raw_items):
            iwhere = f"{where}.items[{j}]"
            item = _require_mapping(raw_item, iwhere)
            _check_id(item.get("id"), f"{iwhere}.id", seen_ids, "item")
            items.append(item)
        placed[(r, c)] = {"cell": cell, "items": items, "where": where,
                          "index": k}

    # ---- one size for every cell, taken from the fullest one ----------------
    # Measured over the sub-grid each cell's own item count produces, then the
    # maximum of those. A cell with no items measures as one element, so an
    # entirely empty matrix still has cells a reader can see.
    widest = 0
    tallest = 0
    fullest = 0
    for entry in placed.values():
        n = len(entry["items"])
        fullest = max(fullest, n)
        sub_columns = s["cell_columns"] or _near_square_columns(max(n, 1))
        sub_columns = max(1, min(sub_columns, max(n, 1)))
        sub_rows = _ceil_div(max(n, 1), sub_columns)
        entry["sub_columns"] = sub_columns
        entry["sub_rows"] = sub_rows
        widest = max(widest,
                     sub_columns * s["item_width"]
                     + (sub_columns - 1) * s["item_gap_x"])
        tallest = max(tallest,
                      sub_rows * s["item_height"]
                      + (sub_rows - 1) * s["item_gap_y"])
    widest = max(widest, s["item_width"])
    tallest = max(tallest, s["item_height"])

    cell_width = max(widest + 2 * s["cell_pad"], s["min_cell_width"] or 0)
    cell_height = max(tallest + 2 * s["cell_pad"], s["min_cell_height"] or 0)
    column_pitch = cell_width + s["cell_gap_x"]
    row_pitch = cell_height + s["cell_gap_y"]

    grid_left = s["origin_left"] + s["row_header_width"] + s["cell_gap_x"]
    grid_top = s["origin_top"] - s["column_header_height"] - s["cell_gap_y"]

    containers: list[dict[str, Any]] = []
    out_items: list[dict[str, Any]] = []

    # ---- the corner, then the two header strips -----------------------------
    if corner is not None:
        corner_map = _require_mapping(corner, "corner")
        _only_keys(corner_map, _CORNER_KEYS, "corner")
        corner_name = _named(corner_map, "corner")
        corner_id = corner_map.get("id", "matrix_corner")
        _check_id(corner_id, "corner.id", seen_ids, "corner")
        containers.append({
            "id": corner_id,
            "name": corner_name,
            "kind": "corner",
            **rect(s["origin_left"], s["origin_top"],
                   s["row_header_width"], s["column_header_height"]),
        })

    for p in column_plans:
        header_id = p["header"].get("id", f"column_{p['index']}")
        _check_id(header_id, f"{p['where']}.id", seen_ids, "column header")
        containers.append({
            "id": header_id,
            "name": p["name"],
            "kind": "column_header",
            "index": p["index"],
            "key": p["key"],
            **rect(grid_left + p["index"] * column_pitch, s["origin_top"],
                   cell_width, s["column_header_height"]),
        })

    for p in row_plans:
        header_id = p["header"].get("id", f"row_{p['index']}")
        _check_id(header_id, f"{p['where']}.id", seen_ids, "row header")
        containers.append({
            "id": header_id,
            "name": p["name"],
            "kind": "row_header",
            "index": p["index"],
            "key": p["key"],
            **rect(s["origin_left"], grid_top - p["index"] * row_pitch,
                   s["row_header_width"], cell_height),
        })

    # ---- every cell, populated or not ---------------------------------------
    empty_cells = 0
    for rp in row_plans:
        for cp in column_plans:
            r, c = rp["index"], cp["index"]
            entry = placed.get((r, c))
            cell_left = grid_left + c * column_pitch
            cell_top = grid_top - r * row_pitch
            cell_id = (entry["cell"].get("id") if entry else None)
            id_where = f"{entry['where']}.id" if entry else f"cells[{r}][{c}].id"
            if cell_id is None:
                cell_id = f"cell_{r}_{c}"
            _check_id(cell_id, id_where, seen_ids, "cell")
            items = entry["items"] if entry else []
            if not items:
                empty_cells += 1
            container = {
                "id": cell_id,
                "name": (entry["cell"].get("name") if entry else None)
                        or f"{rp['name']} / {cp['name']}",
                "kind": "cell",
                "row": r,
                "column": c,
                "row_key": rp["key"],
                "column_key": cp["key"],
                "empty": not items,
                **rect(cell_left, cell_top, cell_width, cell_height),
            }
            containers.append(container)
            if not items:
                continue

            sub_columns = entry["sub_columns"]
            sub_rows = entry["sub_rows"]
            block_width = (sub_columns * s["item_width"]
                           + (sub_columns - 1) * s["item_gap_x"])
            block_height = (sub_rows * s["item_height"]
                            + (sub_rows - 1) * s["item_gap_y"])
            block_left = cell_left + (cell_width - block_width) // 2
            block_top = cell_top - (cell_height - block_height) // 2

            for j, item in enumerate(items):
                sr, sc = divmod(j, sub_columns)
                in_this_row = min(sub_columns, len(items) - sr * sub_columns)
                row_width = (in_this_row * s["item_width"]
                             + (in_this_row - 1) * s["item_gap_x"])
                if s["align"] == "center":
                    row_left = block_left + (block_width - row_width) // 2
                else:
                    row_left = block_left
                record = {
                    "id": item["id"],
                    "container_id": cell_id,
                    "row": r,
                    "column": c,
                    "row_key": rp["key"],
                    "column_key": cp["key"],
                    "index": j,
                    "cell_row": sr,
                    "cell_column": sc,
                    **rect(
                        row_left + sc * (s["item_width"] + s["item_gap_x"]),
                        block_top - sr * (s["item_height"] + s["item_gap_y"]),
                        s["item_width"],
                        s["item_height"],
                    ),
                }
                if isinstance(item.get("name"), str):
                    record["name"] = item["name"]
                out_items.append(record)

    return {
        "grammar": "matrix",
        "items": out_items,
        "containers": containers,
        "rows": len(row_plans),
        "columns": len(column_plans),
        "cell_width": cell_width,
        "cell_height": cell_height,
        "row_pitch": row_pitch,
        "column_pitch": column_pitch,
        "row_header_width": s["row_header_width"],
        "column_header_height": s["column_header_height"],
        "cells_empty": empty_cells,
        "items_per_cell_max": fullest,
        "bounds": bounding_box([*containers, *out_items]),
    }

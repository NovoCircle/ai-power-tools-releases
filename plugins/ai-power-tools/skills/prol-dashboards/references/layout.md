# Layout — the grid, and why this skill hands it back

Detail supporting [`../SKILL.md`](../SKILL.md) §6. Read that section first.

Verified against Prolaborate 5.6.1.40, read from the page rather than inferred from screenshots.

---

## 1. The model

The canvas is an **angular-gridster2** grid. Tiles are absolutely positioned items carrying a
translate offset and an explicit pixel size, each with eight resize handles, dragged from a
**crosshair handle in the tile header** — not from the tile body.

**The grid is four columns.** That is the invariant. Cell pixel size tracks the window: measured at
611 px wide in one window and 216 px in another, four columns both times.

> **Record a layout in grid units, never pixels.** Columns and rows survive a window resize;
> pixel sizes do not.

A tile's position is therefore four integers: `col`, `row`, `cols`, `rows`.

## 2. What this skill cannot do, and why

**A single click-drag does nothing to a gridster handle.** No movement, no error, no feedback.
Gridster tracks a drag through its intermediate `mousemove` events; a drag primitive that emits only
a start point and an end point is invisible to it. Verified on a resize handle, and independently
observed by a second operator on a different dashboard.

> **Do not retry a drag that appears to do nothing, and do not report a layout as applied.** It is
> not a timing problem and it will not succeed on the third attempt.

This is a limitation of the available browser tooling, not a gap in knowledge — the grid, its
geometry, its persistence and its collision behavior are all understood. If a stepped-drag
capability becomes available, §4 is enough to automate layout immediately.

## 3. What to hand the user

Build the widgets, then give a plan in grid units and say plainly that it must be applied by hand.

```
Application Landscape          c1 r0   2 x 3
Portfolio Summary (cards)      c3 r0   1 x 2
Criticality split (pie)        c0 r3   2 x 3
Top 10 by dependencies (bar)   c2 r3   2 x 3
```

Tell them three things, each of which is non-obvious:

1. **Drag from the crosshair handle in the tile header.** Grabbing the tile body does nothing.
2. **Resizing pushes other tiles, and the push cascades.** Nothing is overwritten — tiles are
   displaced downwards — so the failure mode is a dashboard that silently grows taller and reorders,
   not one that loses content.
3. **Save the dashboard afterwards.** Layout is written only by the page-level Save; an unsaved
   layout is lost on reload, including by a navigation they did not intend.

### Sizing guidance worth passing on

**Every new tile lands 1x1**, regardless of widget type. That is almost never right:

| Content | Minimum that reads well |
|---|---|
| Landscape, any chart with a legend | 2 x 2, usually 2 x 3 |
| A tile holding several Card blocks | 1 x 2 — at 1x1 the lower cards are clipped behind an internal scrollbar |
| Text, Rich Text, Hyperlinks, Images | 1 x 1 is fine |
| Reports | 2 wide or more, or the columns crush |

## 4. Measured behavior

**Layout persists.** A tile grown from 1x1 to 1x2, saved, and reloaded came back 1x2. Geometry
round-trips through the server.

**Collision pushes, and the push cascades.** Growing one tile by one row in a four-column board
displaced two tiles beneath it, which pushed a two-column-wide tile spanning the adjacent columns,
which pushed the tile below that — **four tiles moved across two columns from one resize**.

> **Lay out top-to-bottom.** Size the top row first, then the next, so each push only disturbs tiles
> that have not been placed yet. And **re-read the whole grid after every change** — never assume a
> tile you did not touch is where you left it.

**View mode uses the same grid as edit mode**, with a narrower canvas because of the navigation
tree.

## 5. Narrow screens

A mobile mode is shipped: the stylesheet takes grid items out of absolute positioning and gives the
container its own vertical scroll, so below some breakpoint **the four columns collapse to a single
stack**.

> **On a narrow screen the left-to-right arrangement is lost and placement order becomes reading
> order.** A headline metric placed top-right reads fine on a desktop and arrives late on a phone.
> **Place in reading order, not only in visual order.**

**Not verified:** the breakpoint value and the exact stacked order. The collapse mechanism is
established from the shipped stylesheet, not from a rendering — the page viewport could not be
narrowed in testing.

## 6. Embedded dashboards

A Dashboards widget renders a **live nested grid**, not a thumbnail. The inner layout keeps its grid
positions but is re-laid out to the host tile's width, and it **compresses rather than scrolls** — a
dense dashboard inside a small tile is unreadable. Inner widget **tile headers are dropped**, so the
embedded dashboard loses its titles.

> **Size the host tile for the dashboard inside it**, and do not rely on inner titles to explain
> anything.

## 7. Driving the interface — what costs time

| Symptom | Cause |
|---|---|
| A click reports success and nothing happens | Element-ref clicks fail silently here; a coordinate click works |
| The first interaction after a page load does nothing | Common; budget a throwaway click or verify state |
| The Add Widget control opens then closes | It is a toggle — verify the menu is open before clicking through it |
| A coordinate click lands in the wrong place | Screenshot coordinates are a **scaled copy** of page pixels; scale any coordinate derived from the page |
| Everything reports success but nothing changes | A minimized window: all dimensions read 0, clicks are swallowed, screenshots fail. **Check the window has a non-zero width before trusting any click.** |
| A typed value is not what you typed | Browser autofill corrupts name fields. **Read every text field back after typing.** |

---
name: prol-dashboards
description: Build, read and change Prolaborate dashboards through the web interface — choose the right widget for a question, write the query each widget type requires, verify it before saving, and hand back a layout plan. Use when the task names a Prolaborate dashboard, widget, chart, card or report tile, or asks what a dashboard shows. Never use it for Enterprise Architect model authoring, which belongs to the EA skills.
---

# Prolaborate — dashboards

*Verified against Prolaborate 5.6.1.40 on a Sparx-hosted tenant, driven as a Super Admin session
against a MySQL-backed repository. Section 9 says plainly what that does not prove.*

A Prolaborate dashboard is a grid of widgets over an Enterprise Architect repository. Each widget
is a tile holding one or more content blocks. This skill covers choosing, building, reading and
changing them.

It does **not** author model content. A chart counts elements that already exist; creating or
changing those elements is Enterprise Architect work and belongs to the EA skills.

**Read [`../_shared/references/prolaborate-session.md`](../_shared/references/prolaborate-session.md)
before driving anything.** Most dashboard failures are session failures wearing a disguise.

Run the `prol-start-here` preflight first if you have not already this session.

> **This skill cannot arrange tiles. Read §6 before promising a dashboard.** It builds correct
> widgets and hands the user a layout plan to apply by hand.

---

## 1. Probe the data before choosing anything

Every chart type has a precondition that is invisible until you look, and **none of them fail
loudly** — each produces a chart that renders and is wrong or unreadable.

Run the census in [references/data-probes.md](references/data-probes.md) first. One query, and it
rules chart types in and out before any are built. It answers:

- how many distinct values each candidate grouping column has — which decides Pie versus Bar versus
  top-N, and rules out a Pie above roughly seven;
- whether any tagged value is **numeric and varies** — Bubble needs both, and "is a number" is the
  wrong question;
- whether date-like tagged values exist — without them there is no Road Map;
- whether a hierarchy connector exists — without one there is no Landscape.

> **Report what the data cannot support rather than building a chart that hides it.** A Road Map
> over a repository with no dates renders an empty axis and looks like a styling problem.

## 2. Choosing a widget

Full table in [references/chart-types.md](references/chart-types.md). The decisions that matter:

| The question | Reach for | Never |
|---|---|---|
| "how many X by Y" | Bar, Column | Nested Pie, Heat Map |
| "which are the biggest" | Bar or Column plus top-N | **Nested Pie, Heat Map** |
| "what proportion" | Pie, Donut, seven values or fewer | Nested Pie, Heat Map |
| "broken down by two things" | Stacked Bar, Stacked Column | |
| "how the hierarchy nests" | Landscape | |
| "what connects to what" | Integration Map | |
| "when each thing happens" | Road Map, needs date tagged values | |
| "one number" | Cards | |
| "the underlying list" | Reports | |

> **Nested Pie and Heat Map do not encode magnitude.** Every group receives an equal share of arc or
> area regardless of membership, so **a large cell means a small group**. Measured both ways. Never
> describe either as showing shares, proportions or size, and never choose one for "which is
> biggest" — it is the natural-looking choice and the wrong one.

Only **Charts, Reports and Cards** take SQL. Text, Rich Text, Images, Hyperlinks, Diagrams,
Reviews List and Dashboards are configured, not queried.

## 3. The query contracts

There is no single contract. There are five families, and **the family cannot be predicted from the
chart's appearance** — Nested Pie is round, looks like a Pie, and uses the Landscape contract.

| Family | Members | Shape |
|---|---|---|
| Axial | Pie, Donut, Bar, Column, Stacked Bar, Stacked Column | `Name, Classguid, BaseType, Stereotype, series` plus optional `GroupName` |
| Level-numbered | Landscape, Nested Pie, Heat Map, Integration Map | `objectid1, displayname1, classguid, basetype1, stereotype1, groupname, displaylabel, series, connstartid1, connendid1` |
| Scatter | Bubble | adds `xvalue`, `yvalue`, and `chartvalue` when sized by Sum |
| Timeline | Road Map | adds `starttime`, `endtime` as **strings** |
| Single value | Cards | one column aliased `cards` |

Reports use the axial family **minus `series`**; every other alias becomes a column.

> **Never assume a chart type's contract.** Select the type, press `Skip to Query`, then
> **`VIEW SAMPLE`** — the product prints that type's contract and a complete query **in both MSSQL
> and MySQL**, with no data required. Where the sample's prose disagrees with its generated SQL,
> **trust the SQL**: the prose has been wrong in both cases tested.

Column sets, dialect rules and the top-N pattern are in
[references/query-contracts.md](references/query-contracts.md).

## 4. Building a widget

1. Open the dashboard in edit mode. Add Widget → `Add New` → type the tile title → click the **`+`
   on the widget's row**. The block is added immediately; the footer `Add Widget` button is not used.
2. For a chart: `Skip Report` → name it → **pick the chart type before anything else**.
3. **`Skip to Query`** if you already know the SQL. It opens an empty query box with no one-way-door
   warning, because there is nothing to lose. Use the designer only to learn how a field maps.
4. Write the query. **Blur the query box** — `Execute` does not appear until you click away.
5. **Execute. Read the row count and the actual column values.** This is the only honest check.
6. Work the presentation step. It is per chart type and some controls are load-bearing (§5).
7. Save the chart, then **save the dashboard** — they are separate saves.
8. **Re-open the widget's configuration and confirm what persisted.**

> **The small gear inside the widget body is `Configure`.** The gear in the tile header is
> cosmetics only. Two different controls, one obvious mistake.

> **Editing a generated query is a one-way door**, and **changing the chart type afterwards wipes
> the name, the query and the result query.** Settle the type first.

## 5. Presentation controls that change the data, not the styling

Most of the presentation step is cosmetic. Three controls are not, and all three fail silently.

| Control | Where | What goes wrong |
|---|---|---|
| `MDG Based Report` — **on by default** | Reports | overrides your column set with profile-derived columns |
| `Color Pie` / `Color Sections` — **off on a hand-written query** | Nested Pie, Heat Map | a correct `series` column is ignored and the chart renders flat |
| `Pie List` | Nested Pie, Heat Map | color is a **manually enumerated** label-to-color table, one row per value — not derived from `series` |

> **A chart with many distinct series values cannot practically be colored** in the level-numbered
> family. Prefer a low-cardinality series for those types, or accept a flat chart.

## 6. Layout — a known limitation of this skill

The canvas is a four-column grid. **Every new tile lands 1x1**, regardless of type, and a chart or
landscape is unreadable at 1x1. Layout is therefore a required finishing step, not polish.

> **This skill cannot apply layout.** Resizing and moving tiles needs a drag that emits intermediate
> movements; a single click-drag is ignored **silently**, with no error. Do not claim a layout was
> applied, and do not retry a drag that appears to do nothing — it is not a timing problem.

**What to do instead.** Build the widgets, then hand the user a layout plan in grid units and say
plainly that they must apply it:

```
Capability Landscape        c1 r0   2 x 3
Capability Summary (cards)  c3 r0   1 x 2
Coverage (pie)              c0 r3   2 x 3
```

Tell them three things, because each is non-obvious:

- **Drag from the crosshair handle in the tile header**, not the tile body.
- **Resizing pushes, and the push cascades** — growing one tile by a row displaced four others
  across two columns in testing. Work top-to-bottom so each push only disturbs tiles not yet placed.
- **Save the dashboard afterwards.** Layout persists only through the page-level Save.

Grid mechanics, the measured cascade and the mobile collapse are in
[references/layout.md](references/layout.md).

## 7. Reading a dashboard without opening it

> **Read structure through the API, act through the interface.** Opening a dashboard is the most
> expensive thing you can do in Prolaborate. Reading its definition is free.

One call returns every widget, block, color and grid position:

```js
const key = Object.keys(sessionStorage).find(k => k.startsWith('oidc.user:'));
const token = JSON.parse(sessionStorage.getItem(key)).access_token;
const dash = await fetch(
  '/api/dashboard/DashboardRendring?DashboardId=' + dashboardId + '&isCheckAccess=true',
  { headers: { Authorization: 'Bearer ' + token } }
).then(r => r.json());
```

> **The definition does not contain what a widget queries.** `configData` was null on every widget
> observed; content resolves per block at render time. The definition gives shape, not numbers. To
> read a saved chart's SQL, use the widget gear's `View SQL source`.

> **The dashboard list is returned whole and paged in the browser.** The grid's page buttons fire no
> requests. Never page through the interface expecting more data.

Payloads and supporting calls: [references/payloads.md](references/payloads.md).

## 8. Verification

> **A success response is a claim, not evidence.** Verify from a different surface than the one you
> drove: build in the interface, read back through the API or by re-opening the configuration.

- **`No results found` means the query did not run.** It is indistinguishable from an empty result.
  The most common cause is the wrong SQL dialect for that repository.
- **A rendered chart must agree with the Execute row count.** A Road Map silently drops every row
  whose date fails to parse — the group row stays and the bar vanishes.
- **Re-open a widget's configuration after saving.** Settings have failed to persist silently.

## 9. What this skill cannot promise

- **Layout cannot be applied** (§6). Every dashboard it builds needs manual arrangement.
- **One repository, one dialect.** Everything was verified against MySQL. `VIEW SAMPLE` prints the
  MSSQL form, but no query in this skill has been run against SQL Server.
- **Super Admin only.** Nothing here proves how a restricted user sees any of it.
- **Two chart types are unproven.** Lifecycle Road Map needs a Life Cycle Management definition
  bound to a stereotype; Integration Reports needs a configured integration. Both block cleanly —
  report the block, do not improvise around it.
- **Multi-level charts are untested.** `Add new level` was never exercised on any level-numbered
  type through a hand-written query.
- **Cardinality thresholds are convention, not measurement.**

## 10. When something fails

Ordered cheapest first.

1. **Did the session expire?** Four minutes. See `prolaborate-session.md`.
2. **Did the click land?** Element-ref clicks fail silently on this interface where a coordinate
   click works; the first interaction after a page load is often swallowed. Verify state, retry once.
3. **`No results found`?** Suspect the dialect before the data. Compare against `VIEW SAMPLE`.
4. **Chart renders but looks wrong?** Check §5 — a silent presentation toggle, not the query.
5. **Numbers disagree with the model?** Check whether the connector stereotype is qualified. Element
   stereotypes are stored bare, and so are Westbrook's MDG-declared connector stereotypes in
   `t_connector.Stereotype` (the binding is in `t_xref`); what Prolaborate itself holds for a declared
   one was not re-measured. **Read the resolved value from Execute's Identified Placeholders rather
   than guessing either form.**
6. **Two failed attempts at the same thing is the signal.** Stop, say what you observed, and hand
   back rather than improvising.

## Reference files

| File | Covers |
|---|---|
| [references/query-contracts.md](references/query-contracts.md) | The five families, column sets, SQL dialect rules, top-N, `VIEW SAMPLE` |
| [references/chart-types.md](references/chart-types.md) | All 13 chart types — family, magnitude, presentation tabs, traps |
| [references/layout.md](references/layout.md) | The grid, the drag limitation, the layout-plan format |
| [references/data-probes.md](references/data-probes.md) | Census and tagged-value probes, cardinality thresholds |
| [references/worked-example.md](references/worked-example.md) | A full Westbrook Bank dashboard, end to end |
| [references/test-cases.md](references/test-cases.md) | Acceptance tests for this skill |
| [references/payloads.md](references/payloads.md) | Dashboard read/write payloads and vocabulary |

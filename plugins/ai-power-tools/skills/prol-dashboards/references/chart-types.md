# The 13 chart types

Detail supporting [`../SKILL.md`](../SKILL.md) §2 and §5. Read those sections first.

The chart types live **inside** the Charts widget. They are not widget types — the widget catalog
has 11 entries, of which `Charts` is one. Confusing the two lists wastes a lot of time.

Verified against Prolaborate 5.6.1.40.

---

## 1. All 13, by contract family

| Chart type | Family | Notes |
|---|---|---|
| Pie | axial | |
| Donut | axial | identical contract to Pie; **no `Information on Hover`** |
| Bar | axial | |
| Stacked Bar | axial | **byte-identical SQL to Bar**; differs only in rendering |
| Column | axial | |
| Stacked Column | axial | **byte-identical SQL to Stacked Bar**; designer labels rotate X/Y |
| Landscape | level-numbered | the original of the family |
| Nested Pie | level-numbered | round, looks like a Pie, **uses the Landscape contract** |
| Heat Map | level-numbered | a **treemap**; SQL byte-identical to Nested Pie |
| Integration Map | level-numbered | **model relationships, nothing to do with external integrations** |
| Bubble | scatter | |
| Road Map | timeline | |
| Lifecycle Road Map | **unknown** | needs a Life Cycle Management definition bound to a stereotype |

> **Family cannot be predicted from appearance.** A treemap and a ring chart share one generator.
> Always confirm with `VIEW SAMPLE`.

## 2. What actually encodes magnitude

The most consequential table in this skill. Getting it wrong produces a dashboard that is **wrong**,
not merely ugly.

| Chart | What size or arc encodes |
|---|---|
| Bar, Column, and their stacked forms | **row count** per category — reliable |
| Pie, Donut | **row count** per slice — reliable |
| Bubble | **`chartvalue` summed per `series`** — reliable, if the axes are numeric |
| **Nested Pie** | **nothing** — every group gets an equal angular share |
| **Heat Map** | **nothing** — every group gets an equal area |

Measured: a Nested Pie gave a 13-row group *wider* slices than a 93-row group. A Heat Map split a
one-row group and a four-row group fifty-fifty. Heat Map accepts a `chartvalue` column, carries it
into the preview, and **silently ignores it**.

> **In Nested Pie and Heat Map a large cell means a small group.** If the question is "which is
> biggest", the answer is a Bar or a Column.

## 3. The presentation step, by type

Every chart ends in a Customize step whose **tabs differ by type**. The preview on that step shows
**placeholder data** — judge the data from Execute in step 2 and the appearance from the saved tile.

| Type | Tabs |
|---|---|
| Bar, Column, Stacked Bar, Stacked Column | General · **Bar Settings** (so named even on a Column) · Graph Settings · Display Label Settings |
| Pie, Donut | General · Pie/Donut Settings (font family, size, color only) · Display Label Settings |
| Landscape | General · Landscape General Settings · Landscape Level Settings |
| Nested Pie | General · Nested Pie Settings — **no Display Label Settings tab** |
| Heat Map | General · Heat Map Settings (layout type, parent/child fonts) |
| Bubble | General · Bubble Settings · Graph Settings · Display Label Settings (**no Format Numbers**) |
| Road Map | General · Road Map Settings · Timeline · Milestones |
| Integration Map | General (with a required Legend Color Configuration) · Integration Settings |
| Cards | Card Settings only |

Common to most chart types: legend show/position/title, Legend Ellipsis for long names, and
**`Use default color from Color Palette Configuration`**, which inherits a repository-level palette.
Nested Pie and Heat Map have no palette hook.

### Controls that change meaning, not appearance

| Control | Type | Effect |
|---|---|---|
| `Build Chart by: Percentage / Value` | Pie, Donut | whether slices read as shares or counts |
| `Color Pie` / `Color Sections` | Nested Pie, Heat Map | **off on a hand-written query**; a correct `series` is ignored and the chart renders flat |
| `Pie List` | Nested Pie, Heat Map | color is a **hand-typed label-to-color table**, one row per value |
| `Minimum / Maximum Radius` | Bubble | these are **diameters**, despite the name |
| `Display Date Format` | Road Map | the **axis renderer** — a different setting from step 1's `DATE FORMAT`, which is the **parser** |

> **Formatting belongs to the widget, not the SQL.** Percent signs, number formats and prefixes are
> presentation options; a query that bakes them in returns text where a number was expected.

## 4. Landscape — the one that needs level labels

Landscape and Nested Pie legends list **level labels**, not data values. The defaults are
`Level-0`, `Level-1` and so on.

> **Rename the level labels.** `Level-1` is a placeholder, not a caption, and it ships straight to
> the reader otherwise.

Landscape level settings carry independent font sizes per level — observed defaults 20 / 16 / 12 —
and that size hierarchy is what makes a three-level landscape readable.

## 5. The two that could not be proven

**Lifecycle Road Map.** Its stereotype dropdown is populated from the same endpoint as Road Map's,
differing in one request field that asks for life-cycle stereotypes; on a repository with none it
returns empty, the field is mandatory, and the wizard cannot advance. A hand-written query does not
rescue it: the byte-identical query that renders as a Road Map returns `No results found` as a
Lifecycle Road Map. **Its contract is unknown.**

**Integration Reports** (a widget, not a chart type). `Application` offers five fixed product types;
`Project` returns "No items found" because the backing call returns an empty list, and Save refuses.
**To unblock, the tenant owner must register an integration under Repository Configuration →
Integrated Application Projects, with at least one project and filter.** That needs external-system
credentials.

> **Never enter credentials for an external system.** Report the block and hand it back.

## 6. The widget catalog, for completeness

| Widget | Config surface | Takes SQL | Presentation step |
|---|---|---|---|
| Text | one dialog (rich-text editor, stores HTML) | no | none |
| Rich Text | one dialog, larger editor + **Security toggle** | no | none |
| Images | one dialog, two fields | no | none |
| Hyperlinks | one dialog, item picker — **one link per block** | no | none |
| Diagrams | picker | no | none |
| Charts | 3-step wizard | **yes** | **yes, per type** |
| Reports | **2-step** wizard | **yes** | none |
| Cards | 3-step wizard | **yes** | Card Settings |
| Reviews List | **none at all** | no | none |
| Dashboards | 3-step wizard | no | none |
| Integration Reports | one dialog | no | blocked |

> **The Rich Text `Security` toggle is a render-time filter only.** With it enabled, script and
> frame markup is stripped at render but **still stored**; disabling it executes the stored payload.
> Anyone with edit rights can re-arm it with one switch and no audit prompt. **Never disable it on a
> customer's behalf** — surface it as a decision.

The Dashboards widget embeds a **live nested grid**: the embedded dashboard re-executes all of its
own widgets, compresses rather than scrolls, and **drops the inner widget titles**. Self-reference
is blocked; chaining A into B into C is not.

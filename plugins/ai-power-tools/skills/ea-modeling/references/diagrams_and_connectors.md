# Diagrams and Connectors — Full Detail

Detail supporting [`../SKILL.md`](../SKILL.md) §5–§7. Read those sections first for the decision
points (`create_diagram_in_language` vs. the two-step fallback, when connector lines go missing);
this file carries the full mapping tables and code patterns.

---

## 1. Creating diagrams with MDG types

### Preferred approach — `create_diagram_in_language`

Use `create_diagram_in_language` when the target diagram type is defined by an MDG
profile. It routes through EA's COM diagram-factory path and sets both the EA base type
and the MDG `StyleEx` in one call, without needing the two-step workaround:

```python
ea_diagram(operation="create_diagram_in_language", params={
    "name": "Application Landscape",
    "package_id": <id>,
    "language_id": "ArchiMate3",              # MDG Technology ID
    "diagram_type": "Application",            # diagram type within that MDG
})
```

Common language_id / diagram_type pairs:

| Diagram | language_id | diagram_type |
|---|---|---|
| ArchiMate Application | `ArchiMate3` | `Application` |
| ArchiMate Technology | `ArchiMate3` | `Technology` |
| BPMN Business Process | `BPMN2.0` | `Business Process` |
| UML Component | `UML` | `Component` |

### Fallback — two-step workaround for `create_diagram`

If `create_diagram_in_language` is unavailable or you need fine-grained control:

```python
# Step 1: create with the base EA type (not the MDG string)
result = ea_diagram(operation="create_diagram", params={
    "name": "Application Landscape",
    "package_id": <id>,
    "type": "Logical",          # use EA base type, not "ArchiMate3::Application"
})
diagram_id = result["diagram_id"]

# Step 2: set the MDG StyleEx immediately
ea_diagram(operation="update_diagram", params={
    "diagram_id": diagram_id,
    "properties": {"StyleEx": "MDGDgm=ArchiMate3::Application;"},
})
```

### MDG type → EA base type → StyleEx mapping

| Intended diagram type | EA base type (`ea_diagram("create_diagram")` `type`) | StyleEx value |
|----------------------|--------------------------------------|---------------|
| ArchiMate Application | `Logical` | `MDGDgm=ArchiMate3::Application;` |
| ArchiMate Technology | `Logical` | `MDGDgm=ArchiMate3::Technology;` |
| BPMN Business Process | `Analysis` | `MDGDgm=BPMN2.0::Business Process;` |
| UML Component | `Component` | `MDGDgm=UML::Component;` |
| UML Class | `Class` | *(no StyleEx needed — native EA type)* |
| UML Sequence | `Sequence` | *(no StyleEx needed)* |

### Verify diagram type was stored

```
ea_analyze(operation="execute_sql", params={"sql": "SELECT Diagram_Type, StyleEx FROM t_diagram WHERE Diagram_ID = <id>"})
```

For a BPMN diagram, `Diagram_Type` should contain `"Business Process"` or `"BPMN"`, and
`StyleEx` should contain `"MDGDgm=BPMN2.0::Business Process"`.

---

## 2. Diagram layout

### `layout_diagram` — works as of server v1.0.0

The earlier GUID bug (REQ-004) is **fixed in v1.0.0**. Call `layout_diagram` freely.

To manually trigger layout on a diagram at any time:
```
ea_diagram(operation="layout_diagram", params={"diagram_id": <id>, "style": "Hierarchical"})
```

### The four valid layout styles

`style` accepts exactly four values, and nothing else:

| Style | Use it for |
|---|---|
| `Orthogonal` | Right-angled routing over a general-purpose diagram |
| `Hierarchical` | Layered, top-down structures (the usual choice for a freshly populated diagram) |
| `Circular` | Peer sets with no natural hierarchy |
| `Sequence` | Sequence diagrams |

There is no `Digraph` style — it has never been one, despite appearing in older notes.

### Behavior change in server 3.0.0 — unrecognized styles now error

Through 2.x an unrecognized style name was accepted silently: the server laid the diagram out
as `Orthogonal` and set `style_fallback: true` in the response. From **3.0.0** it is a
structured error instead, and no layout runs:

```json
{"error": "invalid_layout_style", "diagram_id": 123, "requested_style": "Digraph",
 "valid_styles": ["Circular", "Hierarchical", "Orthogonal", "Sequence"],
 "message": "..."}
```

Treat the error as a caller bug: pick one of the four names from `valid_styles` and re-issue.
Do not retry the same style expecting the old fallback.

### `add_elements_to_diagram_bulk` — the `layout` default is `"auto"`

`ea_diagram("add_elements_to_diagram_bulk")` defaults to `layout="auto"`, not to a fixed style:

- If **any** element in the call supplied explicit `left` / `top` / `right` / `bottom`
  coordinates, no layout runs and the coordinates you gave are kept.
- If **none** did, a layout inferred from the diagram type runs after placement: `Hierarchical`
  for Logical, Class, Component, Deployment, Package and Requirements diagrams, `Sequence` for
  Activity and Analysis (BPMN), `Circular` for State and Statechart, `Orthogonal` otherwise. The response names it in `layout_applied`.

The coordinates belong inside each `element_ids` entry, as a dict
(`{"element_id": 12, "left": 50, "top": 50, "right": 190, "bottom": 110}`). Passed as top-level
`params`, they are refused with `unknown_parameters`.

Pass `layout=None` to skip layout regardless, or one of the four style names above to force
that style regardless.

---

## 3. Connector rendering and t_diagramlinks

**A `t_diagramlinks` row is not what makes a connector visible.** Behavior in this section was
verified against **EA 17.1 build 1716**: a connector between two placed elements renders
correctly with **zero** `t_diagramlinks` rows for that diagram, and still renders after EA is
closed and reopened. Deleting rows does not suppress the line. Earlier revisions of this file
said the opposite — they were wrong.

What the row actually carries is **per-instance presentation** for one link on one diagram:
route mode, line color, line width, label placement and visibility, the hidden flag. With no
row, EA draws the connector with its defaults. **The row is required to *style* a connector,
not to *show* it.**

| Store | What it is | How it comes to exist |
|---|---|---|
| `t_connector` | The logical connector — model-level, independent of any diagram | `ea_model("create_connector")`, `ea_model("create_connectors_bulk")` |
| `t_diagramlinks` | Per-diagram presentation of that connector — route, color, width, label placement, hidden flag | Written by EA's own layout pass over the diagram; absent until then, and absence is not a defect |

### `InstanceID` — telling a stored link from a drawn one

`ea_diagram("get_diagram")` reads the COM `DiagramLinks` collection, not the table, so it
reports links EA is rendering whether or not a row backs them:

| `InstanceID` | Meaning |
|---|---|
| Non-zero | A real placed link with a stored `t_diagramlinks` row — its presentation is persisted and can be styled |
| `0` | EA is drawing the connector without a stored row — the line is on the diagram, there is simply nothing yet to style |

Use that distinction to decide whether a styling change has somewhere to land. Do not use it
to decide whether a connector is visible; both values render.

### What does not create a row

Neither `DiagramLinks.AddNew`, nor `Refresh()`, nor `ReloadDiagram()`, nor `CloseDiagram()`
produces a `t_diagramlinks` row on its own. EA's own layout pass over the diagram is what
writes one.

Consequently, calling `ea_diagram("add_connectors_to_diagram_bulk")` to "restore" connectors
you cannot see is not a fix — the missing row was never the reason they were invisible. Reach
for that operation when you are working on link presentation, not when a line is absent.

### When a connector really is missing from a diagram

If an expected line is genuinely absent, the cause is in the model or in what got placed, not
in `t_diagramlinks`. Check in this order:

1. **Are both endpoints on this diagram?** EA draws a relationship only between two elements
   that are both placed on it. One endpoint missing and there is no line to draw — this is by
   far the most common cause.
   ```
   ea_analyze(operation="execute_sql", params={"sql": """
       SELECT Object_ID FROM t_diagramobjects WHERE Diagram_ID = <id>
   """})
   ```
2. **Does the connector exist at all?** Confirm the logical connector is in `t_connector` with
   the endpoints you expect — `ea_model("list_connectors_for_element")` or SQL against
   `t_connector` on `Start_Object_ID` / `End_Object_ID`.
3. **Is it hidden on this diagram?** A `t_diagramlinks` row *with the hidden flag set* does
   suppress the line. That is the one case where a row changes visibility — and it needs a row
   to exist, which is the opposite of the old claim.

---

## 4. Connectors

### Type → EA connector type mapping

| Relationship | `type` | `stereotype` |
|-------------|-----------------|--------------|
| `«Uses»` | `Association` | `Uses` |
| `«Realizes»` | `Realization` | `Realizes` |
| `«Flows»` | `InformationFlow` | `Flows` |
| `«Dependency»` | `Dependency` | *(blank)* |
| Plain association | `Association` | *(blank)* |

> **Canon note (flagged, not changed in this split):** `_shared/references/westbrook-example.md`
> section 6 records that the WBA MDG (1.1.1) declares three connector stereotypes: `Uses`,
> `Flows` and lower-case `realizes`. EA stores them bare in `t_connector.Stereotype`, so write
> them unqualified, as below — never as `WBA::Uses`. What binds a connector to the technology is
> its `t_xref` row (`FQName=WestbrookBankArchitecture::Uses`), set by passing `StereotypeEx`
> `WestbrookBankArchitecture::Uses` to `update_connector`. Whether a connector created with only
> the bare `stereotype` below is bound to WBA, to another language, or to nothing was not
> measured. `ConsumesService` and capitalized `Realizes` are not declared; the demo's own tests
> query the strings. See canon section 6.

### Governance rule: WBA-LFY-001 and connector stereotypes

The WBA-LFY-001 governance rule flags connectors where:
- The **source** element has `lifecycle` = `Strategic` or `Current`
- The **target** element has `lifecycle` = `Deprecated`
- The **connector stereotype** is one of: `Uses`, `ConsumesService`, `Realizes`, `Flows`

This means a plain `Association` with **no stereotype** does NOT trigger WBA-LFY-001, even if
it connects a Strategic source to a Deprecated target.

**Design rule:** If a connection to a Deprecated element is intentional and should NOT be
flagged as a governance violation (e.g. it documents an existing link for traceability, not
a new active consumption), use a plain unstereotyped `Association` rather than `«Uses»`.

### Verify connector endpoints before creation

Always confirm both endpoint elements exist before calling `ea_model("create_connector")`:
```
ea_analyze(operation="execute_sql", params={"sql": """
    SELECT Object_ID, Name, Stereotype, Lifecycle
    FROM t_object
    WHERE Object_ID IN (<source_id>, <target_id>)
"""})
```

---

## 5. Diagram Notes — Recipe and Rationale

Neither `create_diagram` nor `create_diagram_in_language` populate `Notes`; it comes back
empty unless a caller supplies it via `properties`. Set it explicitly as the final step of
diagram authoring, after `add_element_to_diagram` / `add_elements_to_diagram_bulk` — not at
creation:

```
ea_diagram(operation="update_diagram", params={
    "diagram_id": <id>,
    "properties": {"Notes": "Class diagram showing the WBACapability hierarchy, "
                             "including WBA_PaymentGateway and its dependent services."},
})
```

### What a good note contains

One sentence covering:
1. **Type and purpose** — why someone would open this diagram, not just its EA type string.
2. **Name**, only if it adds information the purpose sentence doesn't already carry.
3. **At least one element it contains** — the most central or first-placed element is
   enough. Do not attempt an exhaustive contents list; that duplicates `get_diagram`.

| Note | Verdict |
|---|---|
| `"Class diagram showing the WBACapability hierarchy, including WBA_PaymentGateway and its dependent services."` | Good — type, purpose, a named element |
| `"Class diagram in package Payments."` | Bad — generic, names no content, could have been written before any element existed |
| `""` | Bad — the defect this recipe fixes |

### Why this is a skill-layer fix, not a server `auto_notes` flag

A diagram is empty at `create_diagram` time — elements are placed afterward in Phase 4 of
the build order. A server-side flag that auto-synthesizes `Notes` at creation could therefore
only ever produce the "Bad — generic" row above: it cannot reference diagram contents that
don't exist yet, and per the backlog item's own framing, a generic-but-present note is worse
than an empty field, because it *looks* documented and stops anyone from ever writing the
real thing. The skill has what the server call boundary doesn't: full context on why the
diagram was requested and what got placed on it, gathered across the whole authoring
sequence. Write the note once, after that sequence completes, from that context.

### `update_diagram` and existing Notes

`update_diagram`'s `properties` dict only touches the keys it's given — omitting `Notes`
from an unrelated update (a rename, a `StyleEx` fix) never clears or overwrites it. Re-set
`Notes` only when the diagram's purpose or contents changed enough to make the old note
wrong.

---

## 6. Custom element images — drawing an element as an icon

Iconography (a cloud-vendor glyph, a device picture, a logo) is two rows, not one. The
artwork lives in `t_image`, which EA calls the Image Manager; each **placement** points at
it through `t_diagramobjects.ObjectStyle`'s `ImageID=` token. Setting one without the other
does nothing visible.

```python
# 1. Get the artwork into the model. PNG, EMF or WMF. Idempotent on content:
#    re-adding the same file returns the existing id with status "skipped".
img = ea_diagram(operation="add_image", params={
    "path": r"<icon-dir>\core-banking.png",
    "name": "WBA Core Banking",            # optional; defaults to the file name
})

# 2. Point a PLACED element at it. Other diagrams are untouched.
ea_diagram(operation="set_element_image", params={
    "diagram_id": <id>,
    "element_id": <id>,
    "image_id": img["image_id"],           # or image_name="WBA Core Banking"
    "name_under_image": True,              # caption below the icon
})

# 3. See it. The token being stored is not the same as EA drawing it.
ea_diagram(operation="verify_diagram", params={"diagram_id": <id>,
                                               "include_svg": True})
```

### Rules that save a debugging cycle

| Rule | Why |
|---|---|
| The element must already be placed on the diagram | The image rides on the placement row, not the element; an unplaced element returns `element_not_on_diagram` |
| `add_image` needs a `.qea`/`.qeax` project | EA's COM API has no route to the image library at all, so this writes SQL, and a binary literal has no portable syntax. On other backends load the artwork through EA's own Image Manager — `list_images` and `set_element_image` then work normally |
| PNG, EMF and WMF only | EA re-encodes raster artwork to PNG when it takes it in. A JPEG, GIF or BMP is refused with the conversion named, rather than stored under a type that would draw blank |
| `ok: true` means the token is stored, not that the picture renders | Both operations re-read after writing and report `verified`. Rendering is `verify_diagram`'s job |
| Clearing keeps the artwork | `clear_element_image` writes `ImageID=0` on that one placement. The `t_image` row survives, so other placements using it are unaffected |

### Where to get more icons: EA's own shipped libraries

**Check `list_images` first.** An icon already in the model needs no second copy.
`add_image` is idempotent on content anyway, but the name you search for may already be there.

**The source for anything missing is the user's own EA install.** Sparx ships AWS, Azure and
Google Cloud icon sets as model-pattern files in `<EA install>\ModelPatterns\`
(typically `%ProgramFiles%\Sparx Systems\EA\ModelPatterns\`). Measured on EA 17.1 build 1716;
a different build can ship different files, so list the folder rather than assuming names.

| File | Provider |
|---|---|
| `analytics_amazon-aws-web-images_v1.xml`, `_v5`, `_v7`, `_v19` | AWS (`v19` newest) |
| `Azure_icons-and-images.xml`, `_Nov_22`, `_Feb_24` | Azure (`Feb_24` newest) |
| `analytics_google-web-images_v1_0.xml`, `_v1_5` | Google Cloud (`v1_5` newest) |
| `dwa-01-data-storage-images.xml`, `-iot-`, `-pii-`, `-visualization-images.xml` | Generic data-platform icons |

About 5,200 icons across these files, all in the same format. Nothing needs to be downloaded or shipped. The icons are
the vendors' marks, already on the user's machine through their EA license.

**Importing a library file does NOT make its icons assignable.** Each icon is an Artifact
element stereotyped `Image` whose picture is an attached document, so an import adds elements and
`t_document` rows and nothing to `list_images`; `ImageID=` resolves only against `t_image`. Use
the two operations built for this instead (server 3.6.0 or later) — they read the libraries in place:

```python
# 1. Search the user's own install. Each match carries an `icon` id, its provider and
#    vintage, how it matched, and `loaded_image_id` when the model already holds it.
hits = ea_diagram(operation="find_icon", params={
    "query": "Lambda", "provider": "AWS",   # provider optional: AWS, Azure, Google, ...
})

# 2. Put the chosen one on a placed element. Loads it into the image library only if the
#    model does not already have it (`image: "added"` / `"existing"`), then sets it.
ea_diagram(operation="set_element_icon", params={
    "diagram_id": <id>, "element_id": <id>,
    "icon": hits["matches"][0]["icon"],
    "name_under_image": True,
})
```

The stored image is named `"<provider> <vintage> - <name>"`, e.g. `"AWS v19 - AWS Lambda"`; where
one library has same-named icons whose pictures differ, each name carries a short ID in
brackets. `set_element_icon` adds the image to the model's image library (`t_image`), and deleting the element or package does not remove it. It also inherits `add_image`'s rule that loading needs a `.qea`/`.qeax`
project — on another backend, load the artwork through EA's Image Manager and use
`set_element_image`. `find_icon` returns `icon_libraries_not_found` when it cannot locate
`ModelPatterns`; the `EA_MODEL_PATTERNS` environment variable points it at the folder.

**Choose the icon; don't match names automatically.** A diagram's captions are not icon names.
`Amazon S3 output bucket` wants `Amazon Simple Storage Service (S3)` or `Bucket with objects`,
`Function App` wants `Function Apps`, and `SQL Database` wants `SQL Databases`. Containers and
labels (`Region 1`, `Web Tier`) never had one. Search for each element's concept with
`find_icon`, prefer the newest vintage, show the user the candidates when more than one fits, and
set only the icons the diagram uses — the full set is tens of MB. Some glyphs are simply not in
the libraries (there is no plain AWS key, for one); say so rather than substituting a near miss.

---

## 7. Custom Style — shape, opacity, alignment, rotation, border, stack

These are EA's Custom Style levers: how one **placement** is drawn. They live in
`t_diagram.StyleEx` under `OPTIONS_<DUID>=`. You never pass a DUID — give
`diagram_id` and `element_id` and the server resolves the placement's own.

> **Precondition: the placement must already carry a DUID, and one you added
> through the API does not.** Custom Style is keyed on that token, and EA only
> writes it for placements EA itself created — dragged onto a diagram in the UI,
> or brought in by an import. An element placed with `add_element_to_diagram` or
> `add_elements_to_diagram_bulk` has no DUID, and neither `reload_diagram` nor a
> `set_diagram_object_appearance` write creates one. The call returns
> `placement_has_no_duid` and changes nothing. Measured on EA 17.1: 89 of 184
> placements in a working model carry a DUID; every one added through the API
> does not.
>
> **So for a diagram you generated, use `set_diagram_object_appearance`** — fill,
> font color, border color and width, size and z-order all work on
> API-placed elements. Custom Style's levers (shape, opacity, rotation, stacked
> cards) are reachable only on placements EA made. If you need one of those on a
> generated diagram, apply it through EA's own dialog — right-click the element,
> Appearance, Custom Style — which makes EA mint the DUID itself.
>
> The server refuses rather than inventing a DUID, because minting one risks
> naming a block EA never reads and copying another placement's would clone a
> model-unique id. The refusal is deliberate, not a gap in error handling.

```python
ea_diagram(operation="set_custom_style", params={
    "diagram_id": <id>, "element_id": <id>,
    "shape": "round rectangle",      # rectangle | round rectangle | ellipse
                                     # | diamond | triangle
    "opacity": 50,                   # 0 | 25 | 50 | 75 | 100
    "text_align": "top center",      # top/bottom + left/center/right, or
                                     # left center | center | right center
    "border_style": "dash",          # solid | dash | dot | dash-dot | none
})

# Styling a whole diagram: one call, one write, one reload.
ea_diagram(operation="set_custom_styles_bulk", params={
    "diagram_id": <id>,
    "objects": [{"element_id": a, "shape": "ellipse"},
                {"element_id": b, "shape": "ellipse", "opacity": 25}],
})
```

Also available: `rotation` (`clockwise` | `counterclockwise` | `none`), `stack_count`
(1 or more — draws the element as that many stacked cards) and `stack_direction`
(`NE` | `SE` | `SW` | `NW`).

### Three things to know

**Omitting a lever leaves it alone; `"default"` resets it.** A reset REMOVES the key rather
than writing a value, because that is how EA records a default — it writes nothing at all
for one. `shape="rectangle"`, `opacity=100`, `text_align="center"`, `border_style="solid"`,
`rotation="none"`, `stack_count=1` and `stack_direction="NE"` are each their lever's default
and behave the same way.

**A value EA does not recognize is refused, not written.** EA ignores a number it does not
know, so writing one leaves the element unchanged while the call looks like it worked.
Spelling is forgiving on the accepted values: `"Round Rectangle"`, `"round-rectangle"` and
`"roundrect"` are the same value.

**These are not the color levers.** Fill, border and font color are
`set_diagram_object_appearance` (per diagram) or `set_element_appearance` (model-wide). An
element drawn as a picture is `set_element_image`, §6.

The response reports `sibling_keys_preserved`. Every other placement's style block lives in
the same `StyleEx` string, along with `MDGDgm=`, which attaches the diagram to its modeling
language — so a write that lost one of those is reported as a failure and the lost keys are
named, rather than left for someone to find later.

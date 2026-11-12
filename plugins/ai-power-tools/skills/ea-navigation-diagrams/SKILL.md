---
name: ea-navigation-diagrams
description: How to generate click-through "navigation diagrams" over hierarchical data in a Sparx EA repository — the composite-element mechanism, the nested-container layout, the exact write sequence, and verification. Use this skill whenever a repository contains or has just been loaded with hierarchical elements (capability models, taxonomies, org structures, product breakdowns, reference models) and the user wants to browse them by clicking down through levels rather than reading a tree diagram.
---

# EA Navigation Diagrams

**Skill Name:** ea-navigation-diagrams

**Purpose:** Turn a hierarchy that already exists in an EA repository into a set of drill-down diagrams, one per parent, where double-clicking a parent opens the diagram of its children. Companion to `ea-modeling` — that skill covers building the model; this one covers making the model navigable.

## What a navigation diagram is

A navigation diagram is an ordinary diagram that has been attached to an element as its **child diagram**, with the element flagged **composite**. On any diagram where that element appears, EA draws a small marker in the element's bottom-right corner — users describe it as the "eyeglasses" or "chain-link" icon — and double-clicking the element opens the child diagram.

Chained across levels, this turns a hierarchy into something a non-modeler can browse: a landing diagram of the top level, each box opening the level below it, all the way to the leaves. It replaces the classic one-big-tree diagram, which stops being readable past about thirty elements.

It is **not** a hyperlink element, **not** a diagram frame, and **not** a Navigation Cell. Those are different EA features with different storage and different behavior.

## The mechanism: three parts, all required

| # | What | Where it lives | Value |
|---|------|----------------|-------|
| 1 | The diagram is made a child of the element | `t_diagram.ParentID` | the element's `Object_ID` |
| 2 | The element is flagged composite | `t_object.NType` | `8` (default is `0`) |
| 3 | EA's link row exists | `t_xref` | Name `DefaultDiagram`, Type `element property`, Client the element's GUID, Supplier the diagram's GUID |

All three are required. This is the single most important fact in this skill:

- Without (3) the element shows the marker, but double-click does nothing (shown live on EA 17.1, 11 Nov 2026).
- Without (2) there is no marker, even though the diagram is owned by the element and appears under it in the Browser.
- Without (1) there is nothing to open (`NType = 8` alone).

`set_composite_diagram` writes all three. Never write them with raw SQL.

A repository that has hand-built navigation diagrams will often contain a mix. Before extending someone's existing pattern, audit it. As of this release, prefer the dedicated operation over hand-rolled SQL:

```
ea_model("find_composite_diagram_mismatches", {"package_id": <pkg>, "recursive": true})
```

It scans the whole package subtree (or just `package_id` itself with `recursive: false`) in one call and returns `{ok, package_id, recursive, checked_count, mismatches}`, where each mismatch is `{element_id, name, ntype, child_diagram_ids, problem}`. `problem` is `diagram_without_flag` (a child diagram exists but `NType <> 8`; looks navigable in the Browser, doesn't drill down) or `missing_default_diagram_xref` (both halves are present but EA's `DefaultDiagram` row is missing: the element looks navigable and does not drill down; re-run `set_composite_diagram` for it) or `flag_without_diagram` (`NType = 8` but no child diagram; a marker that opens nothing). All are the same defect class described above, in either direction.

The equivalent raw SQL, for when you need to inspect the same thing by hand:

```sql
SELECT o.Object_ID, o.Name, o.NType,
       (SELECT COUNT(*) FROM t_diagram d WHERE d.ParentID = o.Object_ID) AS child_diagrams
FROM t_object o
WHERE o.Package_ID = <pkg>
  AND EXISTS (SELECT 1 FROM t_diagram d2 WHERE d2.ParentID = o.Object_ID)
  AND o.NType <> 8
```

Any rows returned (or any `diagram_without_flag` mismatch) are elements that look navigable to the author but are not. The SQL cannot see the third part (the `t_xref` row), so use `find_composite_diagram_mismatches` for the full check. Fix them with `set_composite_diagram` (see Phase 4) rather than a hand-written `UPDATE`: it writes all three parts together and reports whether they actually landed consistent.

This audit is the highest-value check in this skill — it catches the "looks navigable but isn't" defect (some parents with a child diagram and no composite flag) automatically, before a user clicks and finds nothing. Run it before extending any existing set, and offer to run it any time a user asks about navigation diagrams in a repository you didn't build yourself.

> **Note on `t_diagram.ParentID`:** despite what some schema documentation says, this column holds the parent **element's** `Object_ID`, not a parent diagram and not a package. `Package_ID` is the owning package and is independent of it. An element-owned diagram (`ParentID > 0`) appears in the Browser under the element, not in the package's diagram list, so it does not clutter the package and does not collide with same-named package-level diagrams.
>
> The `describe_table('t_diagram')` notes on current servers say the same. An older server's notes said the opposite (parent *diagram*); if you see that, trust this skill.

## When to offer this

Offer to build navigation diagrams whenever **all** of these hold:

1. The repository contains a parent/child hierarchy — either element parentage (`t_object.ParentID`), a containment connector (`PartOf`, `Aggregation`, `Composition`, `Decomposition`, or an MDG equivalent), or a level tagged value (`Level` = 1/2/3, `Tier`, `Depth`).
2. It is more than one level deep and has more than roughly a dozen elements — below that a single diagram is better.
3. The hierarchy is reasonably stable. Navigation diagrams are cheap to rebuild, but they do need rebuilding when the hierarchy changes.

Typical subjects: business and technical capability models, technology reference models, product/service taxonomies, organization structures, requirement and risk breakdowns, information/data domain models, value stream hierarchies.

**Always confirm the source of truth first.** A model can carry the hierarchy in element parentage *and* in connectors, and they can disagree. Element parentage is what EA's Browser and nesting render from, so prefer it; but say which one you used, and report the disagreement rather than silently picking one.

```sql
-- parentage view
SELECT ParentID, COUNT(*) AS n FROM t_object WHERE Package_ID = <pkg> GROUP BY ParentID;
-- connector view
SELECT c.Start_Object_ID, COUNT(*) AS n FROM t_connector c
 WHERE c.Stereotype LIKE '%PartOf%' GROUP BY c.Start_Object_ID;
```

For the exact thresholds and wording to use when *proactively* raising this — unprompted, right after a load or an analysis call — see "Proactively offering this skill" below. This section covers whether the skill applies at all; that one covers whether to say something about it right now.

## Proactively offering this skill

This is a conversational behavior, not a tool call. No MCP operation can "ask the user a question" — only you, the calling agent, decide when to speak up. This section is authoritative for *when* and *how* to offer; everything else in this skill is the *how to build*.

The commercial case is direct: customers do not ask for navigation diagrams because most don't know the feature exists. The ones who do know build a handful by hand and stop, and often leave some half-linked (see the audit above). Offering it the moment a qualifying hierarchy lands — while you already have the parent/child map in context and the user is looking for confirmation the load worked — is the difference between a feature nobody uses and the thing the tool gets remembered for.

### Trigger points

Check opportunistically, riding on work you were already doing — never issue a new tool call whose only purpose is to go scanning the repository for hierarchies to pitch:

1. **On load.** At the end of any operation that creates elements with parentage or containment: `ea_model("create_elements_bulk")`/`create_element` with `parent_id` set, a spreadsheet import, an XMI import, or any other documented load workflow (`ea-modeling` Phase 2/5). Check the scope you just created.
2. **On analysis.** A read or audit call you were already making happens to reveal a hierarchy meeting the threshold — `ea_analyze("summarize_connector_patterns")` or `ea_model("list_elements_in_package")` are the natural hook points. Check the package you just examined.

### Threshold — do not prompt for trivia

All three must hold. Below this, say nothing; a single diagram is the better answer and a prompt is noise.

| Check | Threshold | How to get it (usually already in hand from the triggering call) |
|---|---|---|
| Depth | 2 or more levels | Walk `t_object.ParentID` from a leaf to a root within scope (or use a level/tier tag if present); depth = the longest chain. |
| Scope size | more than 12 elements | `SELECT COUNT(*) AS n FROM t_object WHERE Package_ID IN (<scope subtree>)` — see `ea-modeling` §8 for the recursive subtree pattern. |
| Elements with children | 3 or more | `SELECT ParentID, COUNT(*) AS n FROM t_object WHERE Package_ID IN (<scope subtree>) AND ParentID <> 0 GROUP BY ParentID` — count the distinct `ParentID` values that are themselves elements in scope. |

### Before offering: check what's already navigable

Run the audit before saying anything:

```
ea_model("find_composite_diagram_mismatches", {"package_id": <scope>, "recursive": true})
```

Combine that with a count of in-scope parents (elements with children) that already have **all three parts** correct (a child diagram, `NType = 8` and the `DefaultDiagram` row):

- **Every qualifying parent is already navigable** → say nothing. Do not re-prompt on a package that's already done, even if it's touched again by a later load in the same session.
- **Nothing is navigable yet** (no diagrams, or diagrams exist but none are flagged) → the full-build framing.
- **Some are navigable and some aren't** → the narrower "fix" framing. This is the more valuable prompt, not a lesser one — it is cheaper, safer, and exactly the defect class this audit exists to catch.

### What to say

State scope, diagram count, and target package before the user answers — never ask blind. Use the wording below, with the real counts in place of the `<...>` slots:

> **Full-build framing** (nothing navigable yet):
> "This load just added a 3-level hierarchy to `<package>`: <n1> top-level groups, <n2> middle-level groups, <n3> leaf elements (<total> elements, <parents> with children). Would you like me to build a set of navigation diagrams so you can browse it by clicking down through levels, instead of one large tree diagram?"

> **Fix-only framing** (partially navigable — keep this wording, filled in with the real counts):
> "<a> of the <b> elements with children are navigable; <c> are not, and <d> of those have a child diagram but are missing the composite flag, so they look navigable but don't drill down. Want me to fix the flags?"

Then offer exactly these four options, every time — don't reword or silently drop one, and offer option 3 even when the framing above is the full-build one, so a user who only wants the cheap fix isn't forced to ask for it separately:

1. **Build the full set** — landing diagram plus one per parent, per the Build procedure below.
2. **Complete an existing set** — generate only what's missing, matching the styling of diagrams already there (read the existing diagrams' `Diagram_Type`/`PDATA`/`StyleEx` per Phase 1 before generating).
3. **Fix only the flags** — the cheap, safe, five-second option: run `set_composite_diagram` against every `diagram_without_flag` mismatch, nothing else. A `flag_without_diagram` mismatch has no diagram to link: report it, and say the two ways out (build its diagram, option 2, or clear the stray flag with `diagram_id: null`). Don't clear it unasked.
4. **No thanks** — and remember it for the rest of this session. Do not offer again for this package this session, even if it's loaded into or analyzed again. A new session starts clean. If the user has told you (this session, or as a standing preference you're otherwise aware of) that they never want this offered at all, treat that as covering every package, not just the one in front of you.

### Rules

- Fires once per load or per analyzed package, never mid-loop. If a single operation loads several packages, finish the whole load, then check/offer once per package — not once per batch and not once per element.
- **One offer per package, each package named, never one combined offer.** Two qualifying packages mean two offers, each with its own scope, diagram count, target package and the same four options, so the person can accept one map and decline the other. An answer to one offer does not decide the other, and a "No thanks" (option 4) is remembered for that package only. Two packages loaded in one request, a Retail map and a Corporate map of 17 elements each, 4 of them with children:

> "`Retail Capability Map` now holds a 2-level hierarchy: 17 elements, 4 with children. An offer to build would create 5 diagrams in `Retail Capability Map` (one landing diagram and one per parent). Would you like that?" (then the four options)
>
> "`Corporate Capability Map` has the same shape: 17 elements, 4 with children, 5 diagrams in `Corporate Capability Map`. Would you like that too?" (then the four options)
- Scope, count, and target package are always stated before the user answers.
- Accepting is not done until a rendered image confirms it — see Phase 5's "counting rows is not verification" rule.
- Existing diagrams are never deleted or overwritten; "Rebuilding after the hierarchy changes" below says how a superseded one is handled and which diagrams count as yours.

## Build procedure

### Phase 0 — read the hierarchy

Pull the whole set in one query: `Object_ID`, `Name`, `ParentID`, and the level tag if present. If `ParentID` is flat and the hierarchy is carried by containment connectors, read parent and child pairs from them instead (check the direction of one pair first) and say that is the source. A level tag alone gives depth but not who belongs to whom, so with no other source say the hierarchy cannot be built and ask. Derive:

- **roots** — elements with no parent inside the scope
- **parents** — every element with at least one child (these get a diagram and `NType = 8`)
- **leaves** — no children, no diagram, no flag

Diagram count = 1 landing diagram + one per parent.

### Phase 1 — pick or copy a template

If the repository already has a navigation diagram the user likes, read its `t_diagram` row and copy `Diagram_Type`, `PDATA`, `Swimlanes` and `StyleEx` verbatim. `StyleEx` is what carries the MDG diagram profile (`MDGDgm=<Profile>::<Diagram>`), the theme (`Theme=:<n>`) and the connector-label suppression that keeps the picture clean.

With no template, a sensible default is diagram type `Logical` plus:

```
StyleEx:  ExcludeRTF=0;DocAll=0;HideQuals=0;AttPkg=1;SuppressFOC=1;SwimlanesActive=1;
          TConnectorNotation=UML 2.1;SPT=1;ShowNotes=0;SuppConnectorLabels=1;
          HideConnStereotype=1;SuppressedCompartments=;
PDATA:    HideRel=0;ShowTags=0;ShowReqs=0;ShowCons=0;ShowIcons=1;ShowShape=1;
          HideProps=0;HideStereo=0;ShowRec=1;FormName=;
```

### Phase 2 — create the diagram rows

One diagram per parent, plus one landing diagram with `ParentID = 0` in the package.

**Default route: `create_diagram`** with `properties` for `Name`, `StyleEx`, `ParentID` and the batch marker (`Author` or `Version`), then check `applied_properties` and `rejected_properties`. It does not list `PDATA`, `Swimlanes` or the show/hide flags, so those still need the follow-up `UPDATE` below. Not yet verified live: that a diagram made this way, with this `StyleEx` and `ParentID`, ends up the same as one inserted by SQL. The raw `INSERT` that follows is the fallback for a server without the call, and what to use if that check fails.

Name each child diagram after its element. Because element-owned diagrams surface under the element rather than in the package list, reusing the element name is unambiguous and is what hand-built examples do.

Insert only the identifying columns, then set the bulky repeated columns (`PDATA`, `StyleEx`, `Swimlanes`, the show/hide flags, dates) in a single follow-up `UPDATE` over the whole batch. Tag the batch — `Author`, or a temporary `Version` marker — so the follow-up update and the later ID lookup can find exactly these rows.

GUIDs must be the braced upper-case form. Dialects differ:

| Repository | GUID expression |
|---|---|
| MySQL | `CONCAT('{', UPPER(UUID()), '}')` |
| SQL Server | `CONCAT('{', UPPER(CONVERT(varchar(36), NEWID())), '}')` |
| Oracle | `'{' \|\| UPPER(REGEXP_REPLACE(...SYS_GUID()...)) \|\| '}'` |
| Access / SQLite (.eap, .qea) | generate host-side and pass a literal |

Then read back the assigned `Diagram_ID` for each `ParentID` — never assume the IDs are contiguous — and keep that list: it is how Phase 5 selects the set and how a later rebuild knows which diagrams are yours.

### Phase 3 — place the objects

Each child diagram holds the parent drawn as a large container with its immediate children laid out inside it. No connectors: the hierarchy is already expressed by the nesting, and connectors turn the picture back into the tree diagram this is meant to replace.

Geometry that reproduces the common hand-built pattern (EA's Y axis is negative downward):

```
W, H        = 130, 80        # child box; widen for long names, keep H
HGAP, VGAP  = 40, 40
PAD_L/R     = 45
PAD_T       = 60             # room for the container's own title
PAD_B       = 40
ORIGIN      = (left 50, top -60)
COLS        = min(child_count, 4)

container.left   = 50
container.right  = 50 + PAD_L + PAD_R + COLS*W + (COLS-1)*HGAP
container.top    = -60
container.bottom = container.top - (PAD_T + PAD_B + ROWS*H + (ROWS-1)*VGAP)

child[i].left = 50 + PAD_L + col*(W + HGAP)
child[i].top  = -60 - PAD_T  - row*(H + VGAP)
```

The landing diagram is the same grid with no container — the roots laid out directly.

`Sequence` is z-order, lowest in front: give the container the highest number and the children `1..n`, or the container paints over them.

`ObjectStyle` carries the per-instance appearance. `DUID` must be unique within the diagram; deriving it from the `Object_ID` in hex (`LPAD(HEX(Object_ID), 8, '0')`) is deterministic and collision-free. `BCol` is a **BGR** integer, not RGB. Color the container with the stereotype default (`BCol=-1`) and the children with a contrasting fill — this is the visual cue for "the thing you drilled into" versus "the things you can drill into next".

```
container: DUID=<8hex>;UCRect=1;NSL=0;BCol=-1;BFol=-1;LCol=-1;LWth=-1;fontsz=0;bold=0;
           black=0;italic=0;ul=0;charset=0;pitch=0;HideIcon=0;LBL=CX=<width>:CY=15:OX=0:
           OY=0:HDN=0:BLD=0:ITA=0:UND=0:CLR=-1:ALN=1:ALT=0:ROT=0;
child:     DUID=<8hex>;UCRect=1;NSL=0;BFol=-1;LCol=-1;LWth=-1;fontsz=0;bold=0;black=0;
           italic=0;ul=0;charset=0;pitch=0;HideIcon=0;BCol=<bgr>;LBL=CX=<width>:CY=15:…
```

Build each element's `left`/`top`/`right`/`bottom` from the geometry above and each element's `style` string from the `ObjectStyle` pattern above, then place the whole diagram (container plus children) in one call — see "Using `add_elements_to_diagram_bulk` for Phase 3" below for the exact call shape and the two flags (`layout`, `auto_connectors`) that must be set explicitly.

### Phase 4 — flag the parents composite

Use `set_composite_diagram`: it writes all three parts of the mechanism (`t_diagram.ParentID`, `t_object.NType` and the `DefaultDiagram` row) together in one call, so they cannot land out of sync the way separate hand-written writes can:

```
for parent_id, child_diagram_id in parent_diagram_pairs:
    ea_model("set_composite_diagram", {
        "element_id": parent_id,        # the parent element's Object_ID
        "diagram_id": child_diagram_id  # the diagram Phase 2 created for it
    })
```

Call it once per parent, after Phase 2 has created that parent's child diagram: `diagram_id` has no default, and passing `null` *clears* the link instead of setting it (useful only when rebuilding; see "Rebuilding after the hierarchy changes" below), so always pass the real diagram ID here. The response includes `consistent: bool`, read back from all three parts after the write, and `default_diagram_xref`, whether the `DefaultDiagram` row is in place: check both. `consistent: true` now means all three parts are in place. `ok: true` with `consistent: false` means the write did not fully land and needs investigating, not assuming fixed. It is idempotent: calling it again with the same arguments is a no-op, not an error.

Leaves stay unflagged (`NType = 0`, no diagram). That is correct and meaningful: no marker tells the user there is nothing below.

Do not write `NType` with raw SQL. It sets only one of the three parts, leaving you to trust the other writes with nothing checking that they agree: which is what `set_composite_diagram`'s `consistent` field is for.

### Phase 5 — verify, then refresh

```sql
SELECT
 (SELECT COUNT(*) FROM t_diagram       WHERE Diagram_ID IN (<ids from Phase 2>)) AS diagrams,
 (SELECT COUNT(*) FROM t_diagramobjects WHERE Diagram_ID IN (<ids from Phase 2>)) AS objects,
 (SELECT COUNT(*) FROM t_diagramobjects WHERE Diagram_ID IN (<ids from Phase 2>)
    AND LENGTH(ObjectStyle) < 10)                                              AS unstyled,
 (SELECT COUNT(*) FROM t_diagramlinks   WHERE DiagramID  IN (<ids from Phase 2>)) AS stray_links,
 (SELECT COUNT(*) FROM t_object WHERE Package_ID = <pkg> AND NType = 8)         AS composites
```

Expect: `diagrams` = 1 + parents, `objects` = roots + Σ(1 + children), `unstyled` = 0, `stray_links` = 0, `composites` = parents.

Then **render at least the landing diagram, one mid-level diagram and one leaf-level diagram and look at them.** Confirm the marker is present on every box that should drill down, the children sit inside the container, and no name is clipped. Counting rows is not verification; the deliverable is a picture.

EA caches diagrams it has already rendered, so a diagram written by SQL and previously opened will render stale. Call `ea_diagram("reload_diagram")` before rendering. If the diagram is open in EA with unsaved changes, the call is refused with `open_with_unsaved_changes`; ask the person to save in EA, then call again. Tell the user to reload the package in the Browser (right-click the package → *Contents → Reload Current Package*) or reopen the model: writes that go to the repository do not reach an EA session that already has the package cached.

## Using `add_elements_to_diagram_bulk` for Phase 3

`add_elements_to_diagram_bulk` takes per-element position and style and an explicit layout opt-out, so it is the right tool for Phase 3 — call it once per diagram with the container and its children in one list, instead of writing `t_diagramobjects` rows directly.

- `"layout": "none"` — **pass it explicitly.** The default, `"auto"`, already skips layout when any element carries explicit `left`/`top`/`right`/`bottom`, so it will usually do the right thing here. Passing `"none"` (any case), `""`, or `null` guarantees it: a layout pass would re-run EA's auto-layout after placement and overwrite the positions you computed, destroying the nested arrangement. Do not pass a named style — an explicit style always lays out.
- `"auto_connectors": false` — **required**. The default (`true`) auto-draws every connector whose both endpoints are now on the diagram, reintroducing the tree this mechanism is meant to replace. (`auto_show_connectors` is the older name for the same flag; pass `auto_connectors` explicitly since it wins if both are given.)
- per-element `style` — the `ObjectStyle` guidance above (DUID, BGR `BCol`) still applies; build the string exactly as before, but pass it as the entry's `style` key instead of writing it via a SQL `UPDATE`.

Call shape, once per diagram:

```
ea_diagram("add_elements_to_diagram_bulk", {
    "diagram_id": <child_diagram_id>,
    "layout": "none",
    "auto_connectors": False,
    "element_ids": [
        {"element_id": container_id, "left": 50, "top": -60, "right": ..., "bottom": ...,
         "sequence": <highest>, "style": "<container ObjectStyle string>"},
        {"element_id": child_id, "left": ..., "top": ..., "right": ..., "bottom": ...,
         "sequence": <1..n>, "style": "<child ObjectStyle string>"},
        ...
    ]
})
```

It is idempotent per element (an already-placed element comes back `skipped`, not duplicated) and a failure on one entry doesn't abort the rest of the batch — both properties direct SQL writes didn't give for free. Direct `t_diagramobjects` writes remain a valid fallback against a server that predates the bulk placement call.

Where the API *does* work, use it: `ea_model("create_package")` for the staging/holding packages, `ea_diagram("reload_diagram")` for cache refresh (refused with `open_with_unsaved_changes` when the diagram is open in EA with unsaved changes: ask the person to save in EA, then call again), and `ea_diagram("get_diagram_png")` for visual verification.

## Known traps

| Trap | Detail |
|---|---|
| Properties that do not land | `ea_diagram("create_diagram"/"update_diagram")` accept documented diagram properties (`Name`, `Notes`, `StyleEx`, `ParentID` and others) and the common snake_case aliases: `parent_id` is applied as `ParentID`. A key EA does not recognize is not applied and is listed in `rejected_properties`; `ok: true` does not mean every key landed. Check `applied_properties` and `rejected_properties` in the response. |
| `t_diagramlinks` column name | It is `DiagramID`, not `Diagram_ID` as on `t_diagram` and `t_diagramobjects`. |
| `describe_table` argument | The parameter is `table`, not `table_name`. |
| BGR not RGB | `BCol=15658671` is `RGB(175,238,238)` — bytes reversed. |
| Filtering on a column you are also setting | `UPDATE … SET Version='1.0' WHERE Version='DD'` applies the `WHERE` first and then destroys the marker. Keep the batch marker out of the `SET` list, or re-identify rows by `Author` + creation date. |
| Long names | A 130×80 box holds roughly four short words. Measure the longest name in the set before fixing box width; a taxonomy of long phrases needs a wider box, not a smaller font. |
| Blank names and quotes | A child diagram is named after its element. A blank name gives a blank diagram name: use `(unnamed <Object_ID>)` and say so. A single quote in a name must be doubled in raw SQL (`create_diagram` needs no escaping). |
| Duplicate names among siblings | Legal in EA and common in imported taxonomies. Diagram names will duplicate too. Harmless, but say so rather than letting the user discover it. |

## Rebuilding after the hierarchy changes

Navigation diagrams are derived artifacts. When the source hierarchy is reloaded or edited:

- a **new parent** needs a diagram and `NType = 8`
- an element that **lost all its children** should stop navigating to an empty picture: `set_composite_diagram` with `diagram_id: null` clears the link on every diagram parented to it and resets `NType` to `0`, and deletes nothing. The unlinked diagram is superseded, so it goes to the holding package below
- a **renamed** element should have its child diagram renamed to match
- **moved** children need their diagram object rows rewritten on both the old and the new parent's diagram

A copied package keeps its drill-down links: `duplicate_package` links a copied child diagram to its copied owner (server 3.6.5 or later). A copied diagram whose owner was not copied goes under the copied package with no owner, and the result lists it in `composite_owner_not_copied` (with a `composite_owner_note`); re-link those by hand with `set_composite_diagram`.

The cheapest correct approach is to regenerate the whole set for the affected package rather than patch it. **Which diagrams are generated.** Only the ones this task created, whose ids you kept from Phase 2 (or a set the person names). The batch marker is temporary, so do not rely on it later. A diagram you cannot show you created counts as the person's, even if its name matches an element, and is never replaced.

**Never delete the user's existing diagrams to make room.** Move superseded diagrams to a clearly named holding package (`_to-delete (superseded diagrams)`) inside the same scope, tell the user what moved and why, and let them do the deleting.

## Reporting back

Tell the user, in plain language: how many diagrams were created and where, which elements are now navigable, which are leaves, what the entry-point diagram is called, and that the Browser needs a reload. Include the count of elements that were already navigable versus newly flagged if you fixed an existing set.

## Verify in EA's UI

EA reports success it has not earned, and reports failure as a modal dialog that blocks the
COM connection rather than as an error you can catch. Neither shows up in a tool response.

- **If a call seems to hang, screenshot EA and read the dialog before concluding anything.**
  It names the cause. Dismiss from the front — dialogs stack, and a later call can be queued
  behind one raised by an earlier one. Windows reporting EA as "Responding" means nothing.
- **After any diagram create or edit, reload the diagram, screenshot it, and look.**
  `ok: true` means rows were written, not that elements landed where you intended, that
  styling applied, or that the result is readable.
- **Without computer use**, say so. Ask the user to paste a screenshot of the EA window or
  dialog into the conversation, read the cause from it, and ask the user to dismiss the dialog
  before you retry. Never report a hang you have not diagnosed or a diagram you have not seen.
  A PNG exported through the API counts as looking at the diagram, but it shows neither a dialog nor the
  Browser, and whether the drill-down marker shows in it has not been confirmed. Say which you looked at,
  and say the marker was checked by the audit if you could not see it.

Full procedure: [`../_shared/references/ea-ui-verification.md`](../_shared/references/ea-ui-verification.md)

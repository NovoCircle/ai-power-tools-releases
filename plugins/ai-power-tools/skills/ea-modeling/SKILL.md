---
name: ea-modeling
description: How to build and maintain Sparx EA models through the ea-mcp-server MCP tools — correct build order, known defects and workarounds, verification patterns, and governance considerations. Use this skill whenever constructing or modifying an EA repository via MCP tool calls.
---

# EA Modeling via MCP — Patterns and Practices

*Grounded in the Westbrook Bank build session. Every pattern here prevented or fixed a defect.*

> **Verification discipline — trust the EA model, not your memory.**
>
> When asked anything about current model state — *does element X exist?*, *what's in
> package P?*, *what's the tagged value of T on element E?* — answer from a read tool call
> issued **in the current turn**, never from memory of what you created earlier. Elements can
> be renamed, moved, deleted, or silently fail to persist between turns, and another user or
> script can mutate the model out-of-band. This is the single largest cause of perceived
> hallucinations in this tool.
>
> | Question | Tool |
> |---|---|
> | Does X exist? / full state of X | `ea_model("find_elements_by_name")` or `ea_model("get_element")` |
> | What's in package P? | `ea_model("list_elements_in_package")` |
> | What's placed on diagram D? | `ea_diagram("get_diagram", {"diagram_id": D, "include_objects": true, "include_preview": false})` (element ids and boxes, no names; plain `get_diagram` returns metadata only), or `ea_diagram("verify_diagram")` after a reload; join `t_diagramobjects` to `t_object` through `ea_analyze("execute_sql")` for names |
> | Tagged values / connectors / patterns in use? | `ea_model("get_element_tags")` / `("list_connectors_for_element")` / `ea_analyze("summarize_*")` |
> | Anything else | `ea_analyze("execute_sql")` — always available, always authoritative |
>
> **Never assert model state from prior-turn memory**, even one turn old; re-query. IDs and GUIDs
> are the only authoritative reference, so persist those across turns, not names. After `/clear`
> or any session boundary, re-orient with `get_repository_info` and SQL. If a verify call is too
> expensive to run, say so: "created earlier, not re-verified" beats a confident guess.
> A verification call costs under 1k tokens; a wrong answer costs trust.

> **Server v1.3.0 — meta-tool dispatch.** The tools sit behind 6 dispatchers: `ea_model`,
> `ea_diagram`, `ea_analyze`, `ea_mdg`, `ea_validate`, `ea_repository`. Call as
> `ea_model(operation="create_package", params={"name": "Foo", "parent_package_id": 1})`.

> **Writing raw SQL?** EA's naming is inconsistent (`t_object.Note` is singular; `t_taggedvalue`
> uses `TagValue`; connector ends are `Start_Object_ID`/`End_Object_ID`). Call `ea_analyze("describe_table")`
> first, or see [`references/sql_schema.md`](references/sql_schema.md), `_shared/references/sql-for-execute-sql.md`.

---

## 0. Pre-flight Checks

Before creating anything, orient yourself: `ea_model(operation="list_root_packages", params={})`
returns every package at `Parent_ID = 0` (true root) **and** `Parent_ID = 1` (EA's default
"Model" node); note the IDs, you need the right parent for your top-level package. Then
`ea_repository(operation="get_repository_info", params={})` confirms the project file and EA
version; if it fails, stop and fix the connection before any write. Its `diagnostics` block
says whether diagnostics is on (§16).

---

## 0.5 Decision: VBScript vs. MCP path

MCP is excellent for reasoning-heavy work but pays a per-call round-trip cost. For pure
deterministic catalog inserts at high volume, in-process VBScript via **Specialize → Scripting**
in EA is faster and costs no agent context.

| Workload | Path |
|----------|------|
| ≤30 elements | MCP — `ea_model("create_elements_bulk")` |
| 30–100 elements | Either; MCP bulk is acceptable, VBScript is faster |
| >100 elements, one-shot insert | VBScript |
| Verification, gap analysis, refinement | **MCP, always** — token-cheap and reasoning-friendly |
| Diagram authoring | MCP — `ea_diagram("add_elements_to_diagram_bulk")` |
| Putting an icon or image on an element | MCP — `ea_diagram("find_icon")` then `ea_diagram("set_element_icon")`; see [`references/diagrams_and_connectors.md`](references/diagrams_and_connectors.md) §6 |

For mixed workloads, bulk-seed in VBScript, then verify and refine through MCP.

---

## 1. Build Order

Always follow this sequence.  Skipping phases or working out of order causes referential
integrity problems that are hard to diagnose.

```
Phase 0 — Pre-flight (ea_model("list_root_packages"), ea_repository("get_repository_info"))
Phase 1 — Package hierarchy  (all packages, leaf-to-root NOT required; parent-first IS required)
Phase 2 — Elements           (create element → set ALL tagged values immediately → next element)
Phase 3 — Connectors         (all relationships between elements)
Phase 4 — Diagrams           (create diagram → update StyleEx → add elements → set Notes)
Phase 5 — Verification       (ea_analyze("execute_sql") spot checks; element counts; connector queries)
```

**Phase 4 covers diagram creation, not diagram *navigation*. Stop at the hand-off.** If the
request is for click-through or drill-down diagrams over a hierarchy (a parent diagram whose
boxes open a child diagram one level down: composite elements, `t_diagram.ParentID`,
`t_object.NType`), that work belongs to **`ea-navigation-diagrams`**. Say so in your reply, load
that skill, and carry on there. From this skill, do not call `create_diagram` or
`set_composite_diagram` for it, not even for a trial diagram, and do not create elements for it
first.

**After Phase 2/5 of a load that created elements with parentage, or after any analysis call
that surfaces a hierarchy** (`ea_analyze("summarize_connector_patterns")`,
`ea_model("list_elements_in_package")`), check whether to offer navigation diagrams over what
you just loaded. Don't add a call just to look. The thresholds, the audit-first check and the
four options to offer are in **`ea-navigation-diagrams`, "Proactively offering this skill"**.

**Why elements before connectors:** `create_connector` needs both endpoint `Object_ID` values.

**Why tags atomically with element creation (v0.3.0+):** pass tags through the inline
`tagged_values={...}` parameter on `create_element` (or a key in each `create_elements_bulk`
spec): one round trip per element instead of N+1. The old "create, then loop `set_tagged_value`"
idiom still works at roughly 5× the round trips.

### Concurrency limits

**Run all write calls sequentially, and never issue parallel `create_package` calls.** EA's COM
layer serializes every call through one thread; parallel creates race in the package-tree cache
and give intermittent `Object reference not set` or `Invalid Class` errors. Use the bulk tools
(`create_elements_bulk`, `create_connectors_bulk`, `add_elements_to_diagram_bulk`) to save
round trips. Read-only calls (`execute_sql`, `get_element`, `get_package`, `get_diagram`) can
run up to about three at a time. The per-operation table is in
[`references/package_and_defects.md`](references/package_and_defects.md) §6.

**One EA session per model file.** Open a model in at most one EA session at a time, visible or
headless, never both; use file copies for parallel work. After an outside write, re-fetch an
object before `Update()`, which rewrites the whole row. Untested cases (read-only sharing, WAL,
`.eap`, DBMS, network share) are unverified: [`../ea-com/references/instances-and-sessions.md`](../ea-com/references/instances-and-sessions.md).

---

## 2. Creating the Root Package

**REQ-001 (fixed v1.0.0):** EA's root can be at parent ID 0 or 1 depending on how the project
was created. Call `list_root_packages` first; a new top-level package takes the `Parent_ID` of
the root it sits beside (the one the person names, or the one holding the content), and if the
roots disagree and none is named, ask. Verify the created package's `Parent_ID` with SQL and
`UPDATE` it at once if wrong, before any child package. Code: [`references/package_and_defects.md`](references/package_and_defects.md) §1.

---

## 3. Package Names Containing `&`

**REQ-002 (fixed v1.0.0):** EA's COM layer HTML-encodes `&` on some paths — `"Operations &
Support"` may store as `"Operations &amp; Support"`, breaking path lookups. Always verify the
stored name after creating a package with `&`/`<`/`>`/`"` in it, and fix with `update_package`
if encoded. Diagram names can be stored encoded too (the demo model has two), so check
`t_diagram.Name` after `create_diagram` and fix with `update_diagram`. Full create → verify → fix sequence:
[`references/package_and_defects.md`](references/package_and_defects.md) §2.

---

## 4. Element Creation and Tagged Values

| Scenario | Use |
|---|---|
| MDG-profile elements (ArchiMate, BPMN, or your organization's own MDG) | `create_element_in_language` — resolves the base metaclass from the technology, so `type` cannot be wrong |
| Generic UML elements | `create_element` |
| >~5 elements at once | `create_elements_bulk` — idempotent; supports `language_id`+`language_type` per spec |
| Plain `create_element` with MDG `stereotype=` | Works when `type` is the stereotype's base metaclass, and binds the profile the same way (§4.5); `create_element_in_language` looks the metaclass up instead of trusting you to |

**A generic concept ("application component", "data store") is not yet a stereotype.** Before
`create_element`, map it to the open model's own stereotype: read the loaded technology
(`ea_mdg("get_mdg_from_runtime", {"tech_id": ...})`) or the model's own usage
(`ea_analyze("summarize_stereotype_usage")`), pick the stereotype whose alias or use matches,
and create it with that stereotype's base metaclass. If two fit or none does, ask which.

Set tagged values inline at creation (`tagged_values={...}`) on `create_element` or in a
`create_elements_bulk` spec — one with `language_id`+`language_type` is the one-call route for a
tagged MDG element — not via a `set_tagged_value` loop after. **`create_element_in_language`
rejects `tagged_values`** (`unknown_parameters`): tag what it creates with `update_element`
(`element_id`, `tagged_values={...}`) in one call, or `set_tagged_value` per tag. Full code
patterns: [`references/element_creation.md`](references/element_creation.md) §1.

Attributes, operations, and operation parameters on an already-created element (`create_attribute`,
`update_attribute`, `create_operation`, `add_parameter`, and related calls) are a separate layer
with their own id scheme and a couple of sharp edges — see
[`references/class-modeling.md`](references/class-modeling.md).

---

## 4.5 Stereotype Persistence — Where EA Stores What

**The most common source of silent failures.** Write a stereotype as the technology id
(`WBA::WBABusinessApplication`), or the bare name when only one loaded technology defines it.
Server 3.6.5 or later translates the id (or a profile name, if you write one) to the
profile-qualified form EA binds, and the result's `stereotype` block says what
was stored: `stereotype.status` is `bound` or `rejected`, and `stereotype.bound_as` is the
qualified name EA recorded. Use your own technology id and profile name; before 3.6.5 only the
profile-qualified form binds.

**Read the result after every call that sets a stereotype.** When EA drops a stereotype (a
Component given a Class-only stereotype, say) the call still returns `ok: true`, with the
stereotype in `rejected_properties` and `stereotype.status` `rejected`. The base metaclass does not
suit it: recreate the element with `create_element_in_language`, carrying tags, connectors
and placements across, or say what the recreate dropped. `create_element` and
`create_element_in_language` both write all three places EA keeps a stereotype:
`t_object.Stereotype`, the `StereotypeEx` property (not a `t_object` column) and the `t_xref`
profile row EA's MDG engine reads. Query `t_xref` by hand ([`references/element_creation.md`](references/element_creation.md)
§2) only to audit older elements.

## 4.6 A File Stored on an Artifact

A file kept on an Artifact is a `t_document` row (`DocType='ExtDoc'`, a zip holding `str.dat`)
**plus** the marks `t_object.Style='ExtDoc=1;'` and `NType=32` on the artifact; without them EA
does not open it. Read the bytes back after writing. Detail and query:
[`references/element_creation.md`](references/element_creation.md) §3.

---

## 5. Creating Diagrams with MDG Types

Prefer `ea_diagram("create_diagram_in_language")` — sets both the EA base type and the MDG
`StyleEx` in one call. If unavailable or you need fine control, fall back to
`create_diagram` (base EA type) + `update_diagram` (`StyleEx=`), then verify with
`SELECT Diagram_Type, StyleEx FROM t_diagram WHERE Diagram_ID = <id>`. Full language_id /
language_type / StyleEx mapping tables:
[`references/diagrams_and_connectors.md`](references/diagrams_and_connectors.md) §1.

## 6. Diagram Layout

`layout_diagram` takes exactly four styles (`Orthogonal`, `Hierarchical`, `Circular`,
`Sequence`); anything else is a structured `invalid_layout_style` error, not a fallback.
`add_elements_to_diagram_bulk` defaults to `layout="auto"`: coordinates you supply are kept,
and when you supply none a layout inferred from the diagram type runs (`layout_applied` names
it). Pass `layout=None` to skip layout. Coordinates go inside each `element_ids` entry
(`{"element_id": 12, "left": 50, "top": 50, "right": 190, "bottom": 110}`), never top level.
Pass positive `top` and `bottom`; the server stores EA's negative values and returns
`stored_top` and `stored_bottom` (a value already negative is kept). Details, the error shape and
the placement calls: [`references/diagrams_and_connectors.md`](references/diagrams_and_connectors.md) §2.
Call `layout_diagram` only when the diagram is not open in EA with unsaved changes; otherwise it
returns `open_with_unsaved_changes` and lays nothing out, so ask the person to save and run it
again. Placement, link, display and appearance calls still write to the model then, with
`reload_skipped: true` in the result: EA shows the change only after the person saves and reloads.

**Previews write files.** Diagram operations that return a preview (`get_diagram`,
`create_diagram`, `create_diagram_in_language`, `verify_diagram` and others) also save a PNG, for
file-based models, in `%LOCALAPPDATA%\ea-mcp-server\previews\<model>-<hash>` and return its path as
`saved_path` (3.6.5 or later; before that, a `diagrams` folder by the model). `include_preview=False` avoids it.

## 6.5 Connector Rendering and t_diagramlinks

**A `t_diagramlinks` row styles a connector; it does not make it visible.** Verified against
EA 17.1 build 1716: EA draws the relationship between two placed elements with or without a
row. The row carries per-diagram presentation (route, color, width, label placement, hidden
flag) and is written by EA's own layout pass. If a line is genuinely missing, check that both
endpoints are placed on that diagram, not the table. In `get_diagram`, `InstanceID` `0` means
EA is drawing the line and nothing is stored for it, but it does not reliably tell you whether
a row exists: query `t_diagramlinks` for that. Full explanation:
[`references/diagrams_and_connectors.md`](references/diagrams_and_connectors.md) §3.

## 6.7 Diagram Notes — Make Every Diagram Self-Documenting

`create_diagram` / `create_diagram_in_language` leave `Notes` empty. Set it yourself as the
**last** step of diagram authoring, after elements are placed, with
`ea_diagram("update_diagram", {"diagram_id": <id>, "properties": {"Notes": "<one sentence>"}})`.
A note written before content exists can only restate name and type. `update_diagram` keeps an
existing `Notes` unless `properties` includes the `Notes` key. Recipe, worked example and the
reasoning against a server-generated placeholder:
[`references/diagrams_and_connectors.md`](references/diagrams_and_connectors.md) §5.

---

## 7. Connectors

| Relationship | `type` | `stereotype` |
|-------------|-----------------|--------------|
| `«Uses»` | `Association` | `Uses` |
| `«realizes»` | `Realisation` | `realizes` |
| `«Flows»` | `InformationFlow` | `Flows` |
| Plain association / `«Dependency»` | `Association` / `Dependency` | *(blank)* |

Two spellings matter. EA's connector type is `Realisation`, with an s (the server documents it
and stores it that way), and the technology declares the stereotype lower-case, `realizes`;
capitalized `Realizes` is not declared. Case counts in SQL comparisons.

**Governance rule WBA-LFY-001** flags a connector whose source `lifecycle` is `Strategic`/`Current`,
target is `Deprecated`, and stereotype is `Uses`/`ConsumesService`/`Realizes`/`Flows`. It compares
the capitalized `Realizes`, which the demo model never stores (it stores `realizes`), so it
cannot match a realization; `ConsumesService` does not occur either. A plain unstereotyped
`Association` does **not** trigger it; use one deliberately for an intentional link to a
Deprecated element. Always verify both endpoints exist before `create_connector`. Detail and the
canon note: [`references/diagrams_and_connectors.md`](references/diagrams_and_connectors.md) §4.

---

## 8. Element Placement and Package Tree Counts

Element counts are **recursive** through a package tree. A shared service used by multiple
capability areas belongs in a top-level or shared package, not buried in one capability area's
sub-package — that inflates every ancestor's recursive count. Count the target subtree before
placing; compare it with the range the person gave or your pre-build count, and with neither,
report the count and say so. SQL: [`references/package_and_defects.md`](references/package_and_defects.md) §3.

---

## 9. Verification Queries

`execute_sql` is the most reliable verification tool; use it liberally. Cookbook (subtree counts,
stereotype/tag/connector lookups, WBA-LFY-001, the `[Default]` gotcha): [`references/sql_schema.md`](references/sql_schema.md) §7.

---

## 10. Working with an MDG technology

**A language in the `ea-start-here` language table:** load its skill,
`modeling-languages:<id>`, then read its how-to, `../_shared/languages/<id>/howto.md`. If
that skill isn't available, give the message in `ea-start-here` §7 and stop the language work.

Otherwise Westbrook Bank's `WBA` technology is the illustration; substitute your own technology
id, stereotypes and tags. Confirm your technology is loaded and enabled before tagging
(`get_mdg_from_runtime` with your `tech_id` answers `source: "live"`; otherwise use
`ea-mdg-deploy` first). Tag applicability comes from your technology's definition. Verification
and the tag rule: [`references/wba_mdg_reference.md`](references/wba_mdg_reference.md).

---

## 11. Idempotency — Check Before Creating

Never assume the repository is empty. Check for a matching package/element/connector by name
(or `find_elements_by_name`) before creating one; skip and record the existing ID if found.
Full check patterns: [`references/package_and_defects.md`](references/package_and_defects.md) §4.

---

## 12. Error Recovery Patterns

If interrupted mid-build: reconnect, audit what exists vs. the spec with SQL counts, and
resume from the next uncompleted item — never rebuild what's there. A wrong name or connector
stereotype fixes with `update_*`. A wrong package parent has no move tool: update both records
that place the package and read both back, or delete-and-recreate if childless. Recipes:
[`references/package_and_defects.md`](references/package_and_defects.md) §5.

---

## 13. Finish: Audit the Package, Respect the Language

- **Audit last.** When a build or change touched a package in a modeling language whose ruleset
  you know (shipped with the language, or recorded beside the technology), end the task with
  `ea_validate("audit", {"rules_path_or_content": <ruleset>, "package_id": <package>})` and show
  the findings. With no known ruleset, say the package was not audited.
- **Check a relationship before you draw it.** Before `create_connector` between elements of a
  loaded language, read the language's relationship rules (`parse_mdg_xml` returns
  `quicklinker_rules` per stereotype, or the language's how-to). If the requested relationship
  is not allowed, say so, list what is allowed, create nothing, and let the person choose.
- **Use list values exactly as defined.** Check a tag value against the technology before
  writing it. Never invent a stereotype, tag or value; a near miss ("Sunsetting") is written as
  the defined value ("Sunset") and the correction reported.

---

## 14. Quick-Reference: Most-Used Tools

The table is in [`references/tool_quick_reference.md`](references/tool_quick_reference.md).

---

## 15. Token Economy and Session Hygiene

Default to `verbose=False` on mutating calls, verify in batch via `execute_sql`, prefer
`summarize_*` over `list_*`, and use the bulk path (~95% fewer round-trip tokens). Split large
builds one session per phase; on "approaching usage limit" finish the current atomic operation,
capture state with one SQL query, then `/clear`. Full tables:
[`references/token_and_session_management.md`](references/token_and_session_management.md).

**EA Computer Use:** wait before screenshotting (2 to 5 s after a menu click, up to 15 s after
opening a `.qea`); "(Not Responding)" means EA is processing. Wait-time table:
[`../_shared/references/latency.md`](../_shared/references/latency.md).

---

## 16. Diagnostics Mode (server v0.3.0+)

Opt-in: set `EA_MCP_DIAGNOSTICS=1` in the server's environment; failing or timed-out calls then
write a Markdown report to `%LOCALAPPDATA%\ea-mcp-server\diagnostics\`. On a failure or hang: stop,
set it, restart, reproduce, check the report for anything sensitive, email it to
`help@novocircle.com`. `get_repository_info` says whether it is active. Format: [`references/diagnostics_and_ui.md`](references/diagnostics_and_ui.md) §1.

---

## Reference files

- [`references/sql_schema.md`](references/sql_schema.md) — schema gotchas, tag-store decision tree, verification-query cookbook
- [`references/element_creation.md`](references/element_creation.md) — element-creation code patterns, full WBA tag table, stereotype persistence, files on an Artifact
- [`references/diagrams_and_connectors.md`](references/diagrams_and_connectors.md) — diagram creation/layout, connector-visibility, connector-type detail, Notes recipe
- [`references/package_and_defects.md`](references/package_and_defects.md) — root-package and `&`-encoding defect fixes, package counts, idempotency, error recovery, package move, concurrency table
- [`references/wba_mdg_reference.md`](references/wba_mdg_reference.md) — MDG-active verification, tag-applicability rule
- [`references/token_and_session_management.md`](references/token_and_session_management.md) — token-economy and session-hygiene guidance
- [`references/diagnostics_and_ui.md`](references/diagnostics_and_ui.md) — diagnostics-mode report format; links to the shared EA computer-use latency table
- [`references/tool_quick_reference.md`](references/tool_quick_reference.md) — most-used-tools cheat sheet

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

Full procedure: [`../_shared/references/ea-ui-verification.md`](../_shared/references/ea-ui-verification.md)

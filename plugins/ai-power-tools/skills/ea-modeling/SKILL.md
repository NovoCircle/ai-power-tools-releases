---
name: ea-modeling
description: How to build and maintain Sparx EA models through the ea-mcp-server MCP tools — correct build order, known defects and workarounds, verification patterns, and governance considerations. Use this skill whenever constructing or modifying an EA repository via MCP tool calls.
---

# EA Modeling via MCP — Patterns and Practices

*Grounded in the Westbrook Bank full-repository build session.  Every pattern here either
prevented a defect or fixed one.*

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
> 1. **Never assert model state from prior-turn memory** — even one turn old is too old; re-query.
>    IDs/GUIDs are the only authoritative reference — persist those across turns, not names.
> 2. **After `/clear` or any session boundary**, re-orient with `get_repository_info` and SQL
>    before answering anything about model contents.
> 3. **If a verify call is too expensive to run, say so** — "created earlier, not re-verified"
>    beats a confident guess.
>
> A verification call almost always costs < 1k tokens (see
> [`references/token_and_session_management.md`](references/token_and_session_management.md)).
> A confidently-wrong answer costs the user's trust in everything else you said.

> **Server v1.3.0 — meta-tool dispatch.** All individual MCP tools are consolidated into 6
> dispatchers: `ea_model`, `ea_diagram`, `ea_analyze`, `ea_mdg`, `ea_validate`, `ea_repository`.
> Call as `ea_model(operation="create_package", params={"name": "Foo", "parent_package_id": 1})`,
> not the old flat `create_package(name="Foo", ...)`. Behavior is unchanged — only dispatch.

> **Writing raw SQL?** EA's table/column naming is deeply inconsistent (`t_object.Note` is
> singular; `t_taggedvalue` uses `TagValue` not `Value`; connector endpoints are
> `Start_Object_ID`/`End_Object_ID`). Call `ea_analyze("describe_table")` before writing any
> non-trivial query, or consult [`references/sql_schema.md`](references/sql_schema.md), which
> also carries the verification-query cookbook.

---

## 0. Pre-flight Checks

Before creating anything, orient yourself: `ea_model(operation="list_root_packages", params={})`
returns every package at `Parent_ID = 0` (true root) **and** `Parent_ID = 1` (EA's default
"Model" node) — note the IDs, you need the right parent for your top-level package. Then
`ea_repository(operation="get_repository_info", params={})` confirms the project file and EA
version; if it fails, EA isn't running or the MCP server isn't connected — stop and fix the
connection before any write calls. Its `diagnostics` block also tells you whether opt-in
diagnostics is active (§16).

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

For mixed workloads: bulk-seed in VBScript, then verify and refine through MCP.

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

**Phase 4 covers diagram creation, not diagram *navigation*.** If the diagrams you're
building are meant to be click-through drill-downs over a hierarchy (a parent diagram
whose boxes open a child diagram one level down) — composite elements, `t_diagram.ParentID`,
`t_object.NType` — that mechanism is a separate skill: see **`ea-navigation-diagrams`**.
It is not covered here.

**After Phase 2/5 of a load that created elements with parentage, or after any analysis
call that happens to surface a hierarchy** (`ea_analyze("summarize_connector_patterns")`,
`ea_model("list_elements_in_package")`) — check whether it's worth proactively offering to
build navigation diagrams over what you just loaded or found. Don't add a new call just to
go looking; this rides on work you were already doing. See **`ea-navigation-diagrams` —
"Proactively offering this skill"** for the exact thresholds (2+ levels, >12 elements, 3+
elements with children), the audit-first check against what's already navigable, and the
four response options to offer.

**Why elements before connectors:** `create_connector` needs both endpoint `Object_ID`
values.  If you try to create connectors while elements are still being built you will
reference IDs that don't exist yet.

**Why tags atomically with element creation (v0.3.0+):** As of v0.3.0, pass tags via the
inline `tagged_values={...}` parameter on `create_element` (or as a key inside each
`create_elements_bulk` spec). One round trip per element instead of N+1. This is the
recommended pattern; the old "create then loop set_tagged_value" idiom still works but
costs roughly 5× the round trips for typical catalog elements.

### Concurrency limits

**Do not issue parallel `create_package` calls.**  EA's COM single-threaded apartment
model serialises all COM calls through one thread; sending multiple `create_package` calls
in parallel causes race conditions in EA's internal package-tree cache and produces
intermittent `Object reference not set` or `Invalid Class` COM errors.

**Safe concurrency rules:**

| Operation | Max parallel calls | Notes |
|---|---|---|
| `ea_model("create_package")` | 1 (sequential only) | EA package tree is not thread-safe |
| `ea_model("create_element")` / `ea_model("create_elements_bulk")` | 1 at a time | Sequential is safe; bulk is preferred over many parallel singles |
| `ea_model("create_connector")` / `ea_model("create_connectors_bulk")` | 1 at a time | Same COM constraint |
| `ea_analyze("execute_sql")` (read-only) | Up to ~3 | Read path is safer but still best kept sequential |
| `ea_model("get_element")`, `ea_model("get_package")`, `ea_diagram("get_diagram")` | Up to ~3 | Read-only; usually safe |

In practice: **run all write calls sequentially.**  Use bulk tools
(`ea_model("create_elements_bulk")`, `ea_model("create_connectors_bulk")`, `ea_diagram("add_elements_to_diagram_bulk")`) to
amortise latency rather than firing multiple single-entity calls in parallel.

---

## 2. Creating the Root Package

**REQ-001 (fixed v1.0.0):** EA's root can be at parent ID 0 or 1 depending on how the project
was created. Call `list_root_packages` first, verify the created package's `Parent_ID` with
SQL, and `UPDATE` it immediately if wrong — before building any child packages. Full
defensive code: [`references/package_and_defects.md`](references/package_and_defects.md) §1.

---

## 3. Package Names Containing `&`

**REQ-002 (fixed v1.0.0):** EA's COM layer HTML-encodes `&` on some paths — `"Operations &
Support"` may store as `"Operations &amp; Support"`, breaking path lookups. Always verify the
stored name after creating a package with `&`/`<`/`>`/`"` in it, and fix with `update_package`
if encoded. Full create → verify → fix sequence:
[`references/package_and_defects.md`](references/package_and_defects.md) §2.

---

## 4. Element Creation and Tagged Values

| Scenario | Use |
|---|---|
| MDG-profile elements (ArchiMate, BPMN, or your organization's own MDG) | `create_element_in_language` — resolves the base metaclass from the technology, so `type` cannot be wrong |
| Generic UML elements | `create_element` |
| >~5 elements at once | `create_elements_bulk` — idempotent; supports `language_id`+`language_type` per spec |
| Plain `create_element` with MDG `stereotype=` | Works when `type` is the stereotype's base metaclass, and binds the profile the same way (§4.5); `create_element_in_language` looks the metaclass up instead of trusting you to |

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

**The most common source of silent failures.** EA stores stereotype info in up to three
places: `t_object.Stereotype` (`create_element`), the less reliable `t_object.StereotypeEx`
(`update_element`, returns `stereotype_warning` on rejection), and `t_xref.Description` — the
MDG profile application, which is what EA's MDG engine and diagram rendering actually read.
Any operation that applies a stereotype matching a loaded MDG profile writes it:
`create_element_in_language`, plain `create_element` with `stereotype=`, `create_elements_bulk`,
and `update_element` with `StereotypeEx` when EA accepts it. If an element won't render correctly
in an MDG-aware diagram, check `t_xref` first — empty means the profile was never applied; a row
with no `FQName` means the technology was not loaded. Fix by recreating via
`create_element_in_language` with the technology loaded. Full verification SQL:
[`references/element_creation.md`](references/element_creation.md) §2.

---

## 5. Creating Diagrams with MDG Types

Prefer `ea_diagram("create_diagram_in_language")` — sets both the EA base type and the MDG
`StyleEx` in one call. If unavailable or you need fine control, fall back to
`create_diagram` (base EA type) + `update_diagram` (`StyleEx=`), then verify with
`SELECT Diagram_Type, StyleEx FROM t_diagram WHERE Diagram_ID = <id>`. Full language_id /
language_type / StyleEx mapping tables:
[`references/diagrams_and_connectors.md`](references/diagrams_and_connectors.md) §1.

## 6. Diagram Layout

`layout_diagram` works as of v1.0.0 (the earlier GUID bug, REQ-004, is fixed) — call it
freely. `style` takes exactly four values: `Orthogonal`, `Hierarchical`, `Circular`,
`Sequence`. As of server 3.0.0 anything else is a structured `invalid_layout_style` error
rather than a silent fallback to `Orthogonal`. `add_elements_to_diagram_bulk` defaults to
`layout="auto"` — element coordinates you supplied are kept as given, and when no element
supplied any, a layout inferred from the diagram type runs (`Hierarchical` for Logical, Class,
Component, Deployment, Package and Requirements diagrams; `Sequence` for Activity and Analysis
(BPMN); `Circular` for State and Statechart; `Orthogonal` otherwise, reported in `layout_applied`); pass `layout=None` to skip layout or a
style name to force one. Coordinates are not top-level parameters of the bulk call: put
`left`/`top`/`right`/`bottom` inside each `element_ids` entry
(`{"element_id": 12, "left": 50, "top": 50, "right": 190, "bottom": 110}`), or use
`add_element_to_diagram` (top-level coordinates) for one element, or `set_diagram_object` /
`set_diagram_objects_bulk` to move elements already placed.

---

## 6.5 Connector Rendering and t_diagramlinks

**A `t_diagramlinks` row styles a connector; it does not make it visible.** Verified against
EA 17.1 build 1716: EA draws the relationship between two placed elements with or without a
row. The row carries per-diagram presentation — route, color, width, label placement, hidden
flag — and is written by EA's own layout pass. In `get_diagram`, a non-zero `InstanceID` is a
stored placed link; `0` means EA is drawing it with no row behind it. If a line is genuinely
missing, look at whether both endpoints are placed on that diagram, not at the table. Full
explanation: [`references/diagrams_and_connectors.md`](references/diagrams_and_connectors.md) §3.

---

## 6.7 Diagram Notes — Make Every Diagram Self-Documenting

`create_diagram` / `create_diagram_in_language` leave `Notes` empty — the server does not
synthesize one. Always set it yourself, as the **last** step of diagram authoring, after
elements are placed: a note written before content exists can only restate name and type,
not what the diagram actually shows.

```
ea_diagram(operation="update_diagram", params={
    "diagram_id": <id>,
    "properties": {"Notes": "<one sentence — see recipe>"},
})
```

Full recipe, worked example, and the reasoning against a server-generated placeholder:
[`references/diagrams_and_connectors.md`](references/diagrams_and_connectors.md) §5.

`update_diagram` never clobbers an existing `Notes` value unless `properties` explicitly
includes the `Notes` key — omit it on unrelated updates (renames, StyleEx fixes) and the
existing note survives.

---

## 7. Connectors

| Relationship | `type` | `stereotype` |
|-------------|-----------------|--------------|
| `«Uses»` | `Association` | `Uses` |
| `«Realizes»` | `Realization` | `Realizes` |
| `«Flows»` | `InformationFlow` | `Flows` |
| Plain association / `«Dependency»` | `Association` / `Dependency` | *(blank)* |

**Governance rule WBA-LFY-001** flags a connector whose source `lifecycle` is `Strategic`/`Current`,
target is `Deprecated`, and stereotype is `Uses`/`ConsumesService`/`Realizes`/`Flows`. A plain
unstereotyped `Association` does **not** trigger it — use one deliberately for an intentional
link to a Deprecated element. Always verify both endpoints exist before `create_connector`.
**A canon-conformance issue in this stereotype vocabulary was found and needs a design
decision, not a mechanical fix** — see
[`references/diagrams_and_connectors.md`](references/diagrams_and_connectors.md) §4.

---

## 8. Element Placement and Package Tree Counts

Element counts are **recursive** through a package tree. A shared service used by multiple
capability areas belongs in a top-level or shared package, not buried in one capability area's
sub-package — that inflates every ancestor's recursive count. Check the target subtree's count
against the expected range before placing. Full counting SQL:
[`references/package_and_defects.md`](references/package_and_defects.md) §3.

---

## 9. Verification Queries

`execute_sql` is the most reliable verification tool — use it liberally. The full cookbook
(subtree counts, stereotype/tag/connector lookups, the WBA-LFY-001 query, the `[Default]`
reserved-word gotcha) is in [`references/sql_schema.md`](references/sql_schema.md) §7.

---

## 10. Working with an MDG technology

Westbrook Bank's `WBA` technology is the illustration throughout; substitute your own
technology id, stereotypes and tags. Confirm your technology is loaded and enabled before
tagging (`get_mdg_from_runtime` with your technology id as `tech_id` answers `source: "live"`;
otherwise use `ea-mdg-deploy` first). Tag applicability comes from your technology's
definition. In the Westbrook Bank illustration, the base 6 tags apply to all 15 element
stereotypes and the AI 4 apply only to the 3 AI stereotypes (`pciScopeJustification`,
`product` and `vendor` are declared on only the stereotypes the canon names). Verification SQL
and the illustration's tag matrix:
[`references/wba_mdg_reference.md`](references/wba_mdg_reference.md).

---

## 11. Idempotency — Check Before Creating

Never assume the repository is empty. Check for a matching package/element/connector by name
(or `find_elements_by_name`) before creating one; skip and record the existing ID if found.
Full check patterns: [`references/package_and_defects.md`](references/package_and_defects.md) §4.

---

## 12. Error Recovery Patterns

If interrupted mid-build: reconnect, audit what exists vs. the spec with SQL counts, and
resume from the next uncompleted item — never rebuild what's there. A wrong name or connector
stereotype fixes with `update_*`; a wrong package parent has no v1 tool and needs a direct SQL
`UPDATE` (or delete-and-recreate if childless). Full walkthroughs:
[`references/package_and_defects.md`](references/package_and_defects.md) §5.

---

## 14. Quick-Reference: Most-Used Tools

The full most-used-tools table (create/read/fix calls for packages, elements, connectors,
diagrams, plus response-shape notes) has moved to
[`references/tool_quick_reference.md`](references/tool_quick_reference.md) — link it from any
session that needs a tool-name cheat sheet rather than the decision reasoning above.

---

## 15. Token Economy and Session Hygiene

Default to `verbose=False` on mutating calls, verify in batch via `execute_sql` rather than
looping `get_element`, prefer `summarize_*` over assembling summaries from `list_*`, and use
the bulk path (~95% fewer round-trip tokens). Match model tier to task — Haiku for
deterministic bulk/CRUD, Sonnet for verification/reasoning, Opus only for genuinely complex
MDG design — split large builds one session per build phase, seed each with targeted SQL
rather than an open-ended "what's the state of the repo" ask, and on "approaching usage
limit": finish the current atomic operation, capture state with one SQL query, then `/clear`.
Full tables (token impact, model tiers, context cost per operation):
[`references/token_and_session_management.md`](references/token_and_session_management.md).

**EA Computer Use:** when driving the EA UI directly instead of through MCP calls, wait
before screenshotting (2–5s after a menu click, up to 15s after opening a `.qea`) and never
retry without confirming the previous action failed — "(Not Responding)" means EA is
processing, not crashed. Full wait-time table:
[`../_shared/references/latency.md`](../_shared/references/latency.md).

---

## 16. Diagnostics Mode (server v0.3.0+)

Opt-in — set `EA_MCP_DIAGNOSTICS=1` in the server's environment. Failing/erroring/timed-out
calls then write a Markdown report to `%LOCALAPPDATA%\ea-mcp-server\diagnostics\` with the
call's arguments, stack trace, EA build info, and the last 25 calls. On a server failure or
hang: stop, set the env var, restart, reproduce, then email the report to
`help@novocircle.com` after checking it for anything sensitive.
`ea_repository("get_repository_info")` reports whether diagnostics is active. Full report
format: [`references/diagnostics_and_ui.md`](references/diagnostics_and_ui.md) §1.

---

## Reference files

- [`references/sql_schema.md`](references/sql_schema.md) — schema gotchas, tag-store decision tree, verification-query cookbook
- [`references/element_creation.md`](references/element_creation.md) — element-creation code patterns, full WBA tag table, stereotype persistence
- [`references/diagrams_and_connectors.md`](references/diagrams_and_connectors.md) — diagram creation/layout, connector-visibility, connector-type detail, Notes recipe
- [`references/package_and_defects.md`](references/package_and_defects.md) — root-package and `&`-encoding defect fixes, package counts, idempotency, error recovery
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
- **Without computer use**, say so and ask the user to look — never report a hang you have
  not diagnosed or a diagram you have not seen.

Full procedure: [`../_shared/references/ea-ui-verification.md`](../_shared/references/ea-ui-verification.md)

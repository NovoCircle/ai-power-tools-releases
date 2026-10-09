---
name: ea-model-hygiene
description: Find and safely fix model decay in a Sparx EA repository -- elements with no connectors, composite-diagram links that fell out of sync, and stereotypes or tagged values applied inconsistently. Use when a model has been growing for a while and needs a cleanup pass, before deleting or moving anything that might still be load-bearing, or when auditing a repository for drift from its MDG.
---

# EA Model Hygiene

*Tools: `ea_model`, `ea_analyze` (AI Power Tools for Sparx EA, v2.3.0+)*

A model that has been built up over months accumulates decay the same way a codebase does:
elements nobody wired a connector to, composite-diagram links where the diagram and the
"drill-down" flag disagree, stereotypes used once and never again, tagged values set on some
elements of a type and quietly skipped on others. None of it breaks EA. All of it erodes trust
in the model, and eventually someone "cleans up" the wrong thing.

This skill is about finding that decay with the right tool for each kind, and fixing it without
deleting something that still matters. Section 2 is the important one -- read it even if you
skip everything else.

Companion to **ea-modeling** (building) and **ea-navigation-diagrams** (the composite-diagram
mechanism in full, if that is your actual task rather than an audit).

---

## 1. What "orphan" actually means -- and why it needs judgement

`ea_model(operation="find_orphan_elements", params={"package_id": <pkg>})` finds elements with
**no connectors**. That is the entire definition -- not "unused," not "unreferenced," not "safe
to delete." Treating its output as a delete list is the most common way this skill goes wrong.

Run it against a real capability model and the numbers are startling. Scoped to the whole
Westbrook Bank tree it returned **140 orphans out of 170 elements checked -- 82%**. Almost none
of them are decay:

- **Capability-hierarchy containers.** Elements like "Consumer Banking," "Lending," "Customer
  Engagement" have no stereotype and no connectors -- their only relationship is parent/child
  containment (`t_object.ParentID`), which EA does not model as a connector.
  `find_orphan_elements` cannot see containment, so every container in a capability tree comes
  back flagged. Deleting them deletes the tree.
- **Package proxy objects.** Every package has a mirror row in `t_object`. Creating a scratch
  sub-package and immediately re-running the scan surfaced the package itself as an "orphan
  element" -- it is the package's own object, not a modeling element at all.
- **Elements that are genuinely disconnected in `t_connector` but still referenced elsewhere** --
  placed on a diagram, or the parent of a composite drill-down diagram. A connector is one kind
  of reference. It is not the only kind.

The Westbrook data model illustrates the last point directly: all 12 `WBADataAsset` elements
(`Customer Master Data`, `Account Master Data`, ...) come back as orphans, because this model
draws data lineage as diagram placement rather than connectors. That is a modeling choice, not a
defect -- and `find_orphan_elements` alone cannot tell you which one you are looking at.

**The only elements worth treating as real candidates** are ones that carry a real stereotype
(so they are not a structural container or a package proxy), have zero connectors, and do not
appear on any diagram. All three, not one.

---

## 2. Pre-delete safety -- the sequence

This is the default advice for deleting anything, whether it came from `find_orphan_elements`,
a stale-looking name, or a request to "clean up the X package." Do all four steps before the
delete call, in order, and stop at the first one that turns up something.

### Step 1 -- what points at it

```
ea_analyze(operation="trace_connectors", params={"element_id": <id>, "direction": "upstream", "depth": 1})
```

`upstream` returns everything whose connector's client (source) end is *not* this element and
whose supplier (target) end *is* -- i.e. everything that depends on it. Worked example against
the live Westbrook model: is `Westbrook Account Master` (element 140) safe to delete?

```json
{
  "nodes": [
    {"id": 69, "name": "Westbrook Account Origination System", "stereo": "WBABusinessApplication"},
    {"id": 70, "name": "Westbrook Account Servicing Hub", "stereo": "WBABusinessApplication"},
    {"id": 79, "name": "Westbrook Customer Self-Service Web", "stereo": "WBABusinessApplication"},
    {"id": 140, "name": "Westbrook Account Master", "stereo": "WBABusinessService"}
  ],
  "edges": [[79, 140, "Uses"], [69, 140, "Uses"], [70, 140, "Uses"]]
}
```

No. Three applications depend on it. `direction` defaults to `downstream` (what it points at) --
for a pre-delete check you almost always want `upstream` explicitly, or both.

### Step 2 -- what it points at, and how far the blast radius goes

```
ea_model(operation="traverse_element_subgraph", params={"element_id": <id>, "depth": 2})
```

`traverse_element_subgraph` walks **both** directions at once (its own `direction` field reports
`"both"`) and is the better call when you need the whole neighborhood rather than one side of
it -- e.g. before deleting a package, to see what the elements inside connect to outside it.
Note it can list the same edge more than once when a node is reached by more than one path; treat
the node and edge lists as a set, not a count.

Three further operations read the same graph -- including the only one that answers "how do
these *two* elements connect" (`find_paths`) and the only one that returns a rooted chain rather
than a flat edge list (`get_traceability_tree`). See Section 6 for which to reach for when.

### Step 3 -- is it drawn anywhere, or does it anchor a navigation diagram

Neither `ea_model` nor `ea_analyze` exposes a dedicated "which diagrams show this element" op.
Two checks cover it:

```
ea_analyze(operation="execute_sql", params={
    "sql": "SELECT Diagram_ID FROM t_diagramobjects WHERE Object_ID = <id>"
})
```

Any row means the element is on a diagram, even if it has no connectors there -- a common pattern
for data assets and reference elements in this model (see Section 1).

```
ea_model(operation="find_composite_diagram_mismatches", params={"package_id": <pkg>, "recursive": true})
```

Run this over the element's parent package before deleting it. If the element is a composite
parent (has a child navigation diagram), deleting it orphans that diagram -- it does not
auto-delete. Verified clean on the Westbrook demo: scoped to `Consumer Banking` recursively, 70
elements checked, zero mismatches (`{"ok": true, "checked_count": 70, "mismatches": []}`). Full
mechanism detail -- the two-part `ParentID` / `NType` flag, and why they drift -- is in
`ea-navigation-diagrams`; this skill only needs the audit call.

### Step 4 -- delete, then verify by re-querying, not by re-fetching

```
ea_model(operation="delete_element", params={"element_id": <id>})    # single element
ea_model(operation="delete_package", params={"package_id": <id>})    # package + everything inside, recursively
```

`delete_package` is silent and total: elements, diagrams, and nested packages all go, with no
per-item confirmation. Never use it as a shortcut for "this package is probably empty" --
`list_package_tree` or `list_elements_in_package` first.

To confirm a delete landed, do not call `get_element` on the id you just deleted -- it does not
return a clean "not found," it raises a raw COM exception (`Internal application error`,
code 61704). That exception *is* your confirmation, but it reads like a tool failure the first
time you see it. Prefer a scoped re-run of `find_orphan_elements` on the parent package, or a
`SELECT COUNT(*) FROM t_object WHERE Object_ID = <id>` -- both return a clean, checkable zero.

See `references/pre-delete-safety.md` for the full worked transcript of this sequence, including
the exact calls and responses from a live verification pass.

---

## 3. Spotting inconsistency

Three operations audit consistency across a stereotype rather than one element at a time. Full
tables from a live run against the Westbrook model are in
`references/consistency-audits.md`; the shape of each:

**`summarize_stereotype_usage`** -- one call, whole repository, no `package_id`:

```
ea_analyze(operation="summarize_stereotype_usage", params={})
```

Returns every stereotype in use with its element count and EA object type. Read the low end of
the list, not the high end -- a stereotype used once or twice in a 200-element model is either a
deliberate one-off or a typo/near-duplicate of a real one (`VendorApplication` next to
`WBAVendorSystem` is exactly this shape: one element, and close enough to the real name that it
looks intentional until you check).

**`summarize_tagged_value_usage`** -- scope it to one stereotype to compare coverage within a
type, not just across the repo:

```
ea_analyze(operation="summarize_tagged_value_usage", params={"stereotype": "WBABusinessApplication"})
```

The six base WBA tags (`criticality`, `lifecycle`, `businessOwner`, `technicalOwner`,
`dataClassification`, `regulatoryScope`) should show a `count` equal to the stereotype's total
element count -- every element carries the tag, even if the value is blank. A tag present on a
small fraction of elements of the same stereotype is either optional-by-design (say so in the
model's own documentation if it is) or a field only some contributors knew to fill in. The live
data had exactly this case on 2026-09-23, under WBA 1.0: `pciScopeJustification` -- which 1.0 did
not declare -- appeared on 2 of the 52 `WBABusinessApplication` elements, an ad hoc tag someone
added for two elements. WBA 1.1.1 now declares it on `WBABusinessApplication` and `WBAVendorSystem`,
so the same low count would now be a declared tag that few elements fill in.

**`summarize_observed_metaclasses`** -- requires a `stereotype`, answers "does every element with
this stereotype use the metaclass the MDG declares for it":

```
ea_analyze(operation="summarize_observed_metaclasses", params={"stereotype": "WBABusinessApplication"})
```

`heterogeneous: false` with a single `object_type` entry is the healthy result -- every
`WBABusinessApplication` is a `Component`, matching the WBA MDG. `heterogeneous: true` (more than
one `object_type` in the distribution) means the same stereotype string was applied to elements
created as different EA base types -- almost always because someone typed the stereotype into
the wrong element instead of using the toolbox, and it will not behave like the rest of its type
in reports, searches, or `create_element_in_language` lookups. A stereotype with `total_count: 0`
(observed for `WBAAIModel` on this repository) is not an error -- it means the MDG declares the
stereotype but the model has never used it, worth knowing before you assume an example needs one.

---

## 4. Moving elements safely

```
ea_model(operation="move_element", params={"element_id": <id>, "target_package_id": <pkg>})
```

`move_element` updates the element's `Package_ID` and nothing else. Verified directly: an
element's connectors (keyed to the element's `Object_ID`, not its package) survive a move
unchanged, and so does its diagram placement (`t_diagramobjects` is also keyed by `Object_ID`)
and its composite child-diagram link if it has one (`t_diagram.ParentID` is likewise the
element's `Object_ID`). A moved element can end up drawn on a diagram that now lives in a
different package than the element itself -- that is expected, not corruption, and it is why
"which package owns this diagram" and "which package owns this element" are different questions.

What *does* change: the element's Browser location, and any package-scoped recursive count
(`ea-modeling` covers the recursive-count trap in more detail). There is no `move_package` --
moving a whole subtree is a `duplicate_package` plus `delete_package` on the original, or a
direct `UPDATE t_package SET Parent_ID = ...` (see `ea-modeling`'s package reference for that
pattern and its caveats).

---

## 5. Failure modes you actually hit

- **Transient `Request timed out` / `Connection closed`**, seen on `find_orphan_elements`,
  `find_composite_diagram_mismatches`, and `summarize_tagged_value_usage` when several sessions
  are working the same repository at once. Retry once before concluding the call is broken --
  every one of these resolved cleanly on a second attempt with no change to the arguments.
- **`create_package` with `parent_package_id: 0`** raises a raw COM `Internal application error`,
  even though every existing root package shows `Parent_ID = 0` in `t_package`. Use
  `ea_repository(operation="get_repository_info", params={})` or
  `ea_model(operation="list_root_packages", params={})` to find a working parent id (on this
  server, `1` -- the `Model` root -- works; `0` does not) rather than assuming the stored value
  is also a valid input.
- **A re-fetch of a just-deleted id is not a clean "not found."** `get_element` on a deleted id
  raises the same raw COM exception as the internal-error case above. Do not debug it as a tool
  failure -- if you just deleted that id, the exception is the confirmation.
- **Scope the scan.** `find_orphan_elements` and `find_composite_diagram_mismatches` both got
  noticeably slower on the whole-model root than on a single top-level package. Scope to the
  smallest package that answers the question, especially while other sessions are active against
  the same repository.

For general wait-before-verify guidance when a check needs the EA UI (opening a diagram to
confirm a deletion visually, for example) rather than just another MCP call, see
[`../_shared/references/latency.md`](../_shared/references/latency.md).

---

## 6. Choosing a traversal operation

Five operations read the connector graph. Section 2 uses two of them; the other three answer
questions those two do not. Picking wrongly is not a style matter -- `trace_connectors` cannot
tell you *how* two elements connect no matter how you parameterise it, and reaching for
`traverse_element_subgraph` on a large model will be slow for no benefit.

Pick by the question, not by the name:

| The question | Operation | Meta-tool |
|---|---|---|
| What is around this element? | `trace_connectors` | `ea_analyze` |
| How do these **two** elements connect? | `find_paths` | `ea_analyze` |
| What hangs off this element along one relationship? | `get_traceability_tree` | `ea_analyze` |
| What is around this element, in ArchiMate/BPMN terms? | `traverse_element_subgraph` | `ea_model` |
| Just list this one element's connectors | `get_connectors_for_element_filtered` | `ea_model` |

**`trace_connectors`** is the default. One bulk SQL pull, no per-element round trips, depth
capped at 10. It returns a flat `{nodes, edges}` neighborhood -- a bag of edges, not routes.
This is what Section 2 Step 1 uses for blast radius.

**`find_paths`** is the only operation that takes two element ids. Use it when the question
names both ends: "how does the account-origination system reach the account master", "is there
any relationship at all between these two". It returns every *shortest* path (there are usually
several), each an alternating element/connector list:

```
ea_analyze(operation="find_paths", params={"source_id": <a>, "target_id": <b>, "max_depth": 5})
```

```json
{"paths": [[{"kind": "element", "id": 69, "name": "..."},
            {"kind": "connector", "id": 412, "type": "Association", "direction": "outbound"},
            {"kind": "element", "id": 140, "name": "..."}]],
 "count": 1, "path_length": 1, "truncated": false}
```

Two things to know. It follows connectors **both ways** -- a real traceability route usually
crosses at least one connector against its arrow, so each connector hop carries `direction`
(`outbound` / `inbound`) to keep the orientation recoverable. And an unreachable, disconnected,
or nonexistent target returns `{"paths": [], "count": 0}`, not an error -- do not read an empty
result as a failed call.

**`get_traceability_tree`** returns a hierarchy rather than a graph you have to re-assemble, and
annotates every child with the connector that reached it (`via_connector`). Use it for
"trace the requirements behind this", "show the realization chain under this service".

```
ea_analyze(operation="get_traceability_tree",
           params={"root_id": <id>, "connector_types": ["Realization"], "direction": "outbound"})
```

`connector_types` is required -- an unfiltered tree is a neighborhood graph in a tree costume,
and `trace_connectors` does that better. `direction` accepts `outbound`/`inbound`, and also
`downstream`/`upstream` and `outgoing`/`incoming`, because the other operations disagree on the
word. Cycle handling is per-branch: an element is refused only if it already appears on the path
from the root down to here, so a diamond correctly shows the same element under both parents
while a loop terminates with `"cycle": true` on the repeated node. **A node carrying `"cycle"`
is a cut branch, not a leaf** -- do not report it as "nothing further downstream".

**`traverse_element_subgraph`** also returns a neighborhood, but resolves MDG stereotype aliases
into display terms and walks the model element by element over COM. That makes it slower and
caps it at depth 5. Reach for it when you want the language's own vocabulary in the answer, as
Section 2 Step 2 does; reach for `trace_connectors` on anything large.

**`get_connectors_for_element_filtered`** is not a traversal -- it is a single-hop SQL lookup of
one element's own connectors with direction and type filters. Use it when you want this
element's relationships and nothing further out.

**Guards.** `trace_connectors`, `find_paths`, and `get_traceability_tree` share one engine and
the same three limits: depth capped at 10, `max_nodes` (2000), `wall_clock_ms` (8000). Any
response with `"truncated": true` hit one of them and is **partial** -- narrow the depth or the
connector types and re-run rather than reporting the partial result as complete.

---

## See also

- **ea-modeling** -- creating and building; the recursive-count trap and package-parent quirks
  referenced above live there in full.
- **ea-navigation-diagrams** -- the composite-diagram mechanism (`ParentID` + `NType`) in depth,
  and when to build navigation diagrams in the first place rather than just audit existing ones.
- **ea-validation** -- once a consistency rule from Section 3 is worth enforcing standingly
  rather than checking by hand (e.g. "every `WBABusinessApplication` must carry all six base
  tags"), express it as a YAML rule there instead of re-running these audits manually.

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

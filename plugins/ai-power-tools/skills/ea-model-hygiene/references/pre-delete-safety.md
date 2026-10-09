# Pre-delete safety -- full worked transcript

Detail supporting [`../SKILL.md`](../SKILL.md) Section 2. Read that section first for the
sequence and when each step applies; this file carries the full verification transcript against
the live Westbrook Bank demo model, plus the scratch-package walkthrough for the destructive
calls (`delete_element`, `delete_package`, `move_element`) that should never be exercised
directly against a shared model.

---

## 1. Case study -- is `Westbrook Account Master` (element 140) safe to delete?

It looks orphan-shaped: a `WBABusinessService`, no obvious traffic. Applying the four-step
sequence from `SKILL.md` Section 2:

**Step 1 -- upstream trace:**

```
ea_analyze(operation="trace_connectors", params={"element_id": 140, "direction": "upstream", "depth": 1})
```

```json
{
  "root_element_id": 140,
  "depth": 1,
  "depth_reached": 1,
  "direction": "upstream",
  "nodes": [
    {"id": 69, "name": "Westbrook Account Origination System", "stereo": "WBABusinessApplication"},
    {"id": 70, "name": "Westbrook Account Servicing Hub", "stereo": "WBABusinessApplication"},
    {"id": 79, "name": "Westbrook Customer Self-Service Web", "stereo": "WBABusinessApplication"},
    {"id": 140, "name": "Westbrook Account Master", "stereo": "WBABusinessService"}
  ],
  "edges": [[79, 140, "Uses"], [69, 140, "Uses"], [70, 140, "Uses"]],
  "node_count": 4,
  "edge_count": 3
}
```

Stop here. Three applications hold a `Uses` connector into this element. It is not a candidate
for deletion, regardless of what any orphan scan might say about it (it would not appear on one
anyway -- it has connectors -- but the same reasoning applies to a genuinely connector-free
element with diagram placement, which is why Step 3 exists).

**Downstream, for contrast**, confirms it is a leaf on the outgoing side:

```
ea_analyze(operation="trace_connectors", params={"element_id": 140})
```

```json
{
  "root_element_id": 140, "depth": 4, "depth_reached": 1,
  "direction": "downstream",
  "nodes": [{"id": 140, "name": "Westbrook Account Master", "stereo": "WBABusinessService"}],
  "edges": [], "node_count": 1, "edge_count": 0
}
```

`direction` defaults to `downstream` and `depth` defaults to `4`; `depth_reached: 1` here just
means the search ran out of edges to follow, not that it stopped early.

**Step 2 -- neighborhood via `traverse_element_subgraph`,** run from the upstream element
`Westbrook Customer Self-Service Web` (79) instead, to see the fuller local picture before
touching anything connected to it:

```
ea_model(operation="traverse_element_subgraph", params={"element_id": 79, "depth": 2})
```

```json
{
  "root_element_id": 79, "depth": 2, "direction": "both",
  "nodes": [
    {"element_id": 79, "name": "Westbrook Customer Self-Service Web", "type": "Business Application", "raw_stereotype": "WBABusinessApplication"},
    {"element_id": 140, "name": "Westbrook Account Master", "type": "Business Service", "raw_stereotype": "WBABusinessService"},
    {"element_id": 141, "name": "Customer Profile Service", "type": "Business Service", "raw_stereotype": "WBABusinessService"},
    {"element_id": 143, "name": "Online Banking Capability", "type": "Business Service", "raw_stereotype": "WBABusinessService"},
    {"element_id": 69, "name": "Westbrook Account Origination System", "type": "Business Application", "raw_stereotype": "WBABusinessApplication"},
    {"element_id": 70, "name": "Westbrook Account Servicing Hub", "type": "Business Application", "raw_stereotype": "WBABusinessApplication"}
  ],
  "edges": [
    {"src": 79, "tgt": 140, "type": "Association", "stereotype": "Uses", "label": "Uses"},
    {"src": 79, "tgt": 141, "type": "Association", "stereotype": "Uses", "label": "Uses"},
    {"src": 79, "tgt": 143, "type": "Realisation", "stereotype": "realizes", "label": "realizes"},
    {"src": 79, "tgt": 140, "type": "Association", "stereotype": "Uses", "label": "Uses"},
    {"src": 69, "tgt": 140, "type": "Association", "stereotype": "Uses", "label": "Uses"},
    {"src": 70, "tgt": 140, "type": "Association", "stereotype": "Uses", "label": "Uses"},
    {"src": 79, "tgt": 141, "type": "Association", "stereotype": "Uses", "label": "Uses"},
    {"src": 79, "tgt": 143, "type": "Realisation", "stereotype": "realizes", "label": "realizes"}
  ]
}
```

Note the duplicate edge entries (`79 -> 140` and `79 -> 143` each appear twice) -- this is the
"walks both directions at once" behavior noted in `SKILL.md`; treat `edges` as a set of
relationships to review, not a count of connectors.

Also note the connector stereotype here is `realizes`, lower case, `Connector_Type: Realisation`
-- not the capitalised `Realizes` that `WBA-LFY-001` compares against (the technology declares
lower-case `realizes`, and EA stores it bare). A repository-wide check
(`SELECT Stereotype, Connector_Type, COUNT(*) FROM t_connector GROUP BY Stereotype, Connector_Type`)
confirmed, on 2026-09-23, the live model's connector-stereotype set: `Uses` (16), blank (5), `extends`
(3), `Requires` (3), `Equivalent` (2), `part-of` (2), `Flows` (1), and `realizes` (1). WBA 1.1.1
has since declared `Uses`, `Flows` and `realizes` and the model has bound them; the stored strings
did not change, so this is still casing and vocabulary drift from the four names `WBA-LFY-001`
matches, on the model's own connectors. This is
flagged here rather than silently normalized; it is exactly the class of decay Section 3 of the
main skill teaches you to look for, just on connectors instead of elements -- and the server's
meta-tools have no dedicated connector-stereotype summarizer, so `execute_sql` against
`t_connector` is the only way to run this particular check today.

**Step 3 -- diagram and composite check**, scoped to the element's parent package
(`Consumer Banking`, package 5):

```
ea_model(operation="find_composite_diagram_mismatches", params={"package_id": 5, "recursive": true})
```

```json
{"ok": true, "package_id": 5, "recursive": true, "checked_count": 70, "mismatches": []}
```

Clean. Combined with the diagram-placement SQL check from `SKILL.md` Section 2 Step 3, this
element has no orphaned navigation link to worry about either way -- moot here since it was never
a deletion candidate, but this is the exact call to run before deleting a `WBABusinessApplication`
or `WBABusinessService` that *did* pass Steps 1 and 2.

---

## 2. Scratch-package walkthrough -- `delete_element`, `move_element`, `delete_package`

Exercised in a dedicated scratch package (`_sl43_scratch`, created as a child of the `Model` root
package rather than at true root -- see the note on `parent_package_id: 0` in `SKILL.md` Section
5) rather than against any pre-existing Westbrook element. Every id below was created in this
session; none pre-existed.

**Setup** -- two connected elements and one disconnected one:

```
ea_model(operation="create_elements_bulk", params={"specs": [
  {"package_id": 3352, "name": "Scratch App A", "type": "Component", "stereotype": "WBABusinessApplication"},
  {"package_id": 3352, "name": "Scratch App B", "type": "Component", "stereotype": "WBABusinessApplication"},
  {"package_id": 3352, "name": "Scratch Orphan Data", "type": "Class", "stereotype": "WBADataAsset"}
]})
# -> element_id 9451 (A), 9452 (B), 9453 (Orphan Data)

ea_model(operation="create_package", params={"parent_package_id": 3352, "name": "_sl43_scratch_moved"})
# -> package_id 3353

ea_model(operation="create_connector", params={"client_element_id": 9451, "supplier_element_id": 9452, "type": "Association", "properties": {"stereotype": "Uses"}})
# -> connector_id 1225
```

**`find_orphan_elements` on the scratch package** correctly separates connected from
disconnected, and independently confirms the "package proxy object" behavior from `SKILL.md`
Section 1 -- the sub-package itself (element_id 9454) is returned as an "orphan element":

```json
{
  "orphans": [
    {"element_id": 9453, "name": "Scratch Orphan Data", "stereotype": "WBADataAsset", "package_id": 3352},
    {"element_id": 9454, "name": "_sl43_scratch_moved", "stereotype": "", "package_id": 3352}
  ],
  "total_count": 2, "scoped_total": 4, "orphan_percentage": 50.0
}
```

`Scratch App A` (9451) and `Scratch App B` (9452) are correctly excluded -- they hold the `Uses`
connector between them.

**`move_element`** -- move the disconnected data element into the sub-package:

```
ea_model(operation="move_element", params={"element_id": 9453, "target_package_id": 3353})
```

`get_element(9453)` afterward shows `"package_id": 3353` with everything else (guid, name,
stereotype, created timestamp) unchanged. A `trace_connectors` re-run on 9451 immediately after
the move still returns the full `9451 -> 9452 "Uses"` edge, confirming the unrelated move did not
touch it -- the connector-survives-a-move claim in `SKILL.md` Section 4 was checked this way, not
assumed from the schema alone.

**`delete_element`** on the now-isolated data element:

```
ea_model(operation="delete_element", params={"element_id": 9453})
# -> {"ok": true, "deleted_element_id": 9453}
```

Re-fetching it (`get_element(9453)`) raises `(-2147352567, 'Exception occurred.', (61704,
'Enterprise Architect', 'Internal application error.', ...))` -- this is the exception referenced
in `SKILL.md` Section 2 Step 4. It is not a malformed call; it is EA's COM layer signalling "no
such object" the only way it signals that for a single-item get.

**`delete_package`** as the final cleanup, cascading through the sub-package and the two
remaining elements and the connector in one call:

```
ea_model(operation="delete_package", params={"package_id": 3352})
# -> {"ok": true, "deleted_package_id": 3352}
```

Confirmed gone two ways: `find_packages_by_name(name="_sl43_scratch")` returns no results, and
package/element counts are back in line with what this session created and removed (see the
verification table in the task's acceptance report for the exact before/after figures, including
the caveat about concurrent sessions against the same shared repository).

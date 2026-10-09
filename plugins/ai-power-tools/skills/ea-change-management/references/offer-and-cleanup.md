# Worked examples — offering a baseline, and cleaning baselines up

Companion to `SKILL.md` §6 (offer) and §7 (cleanup). Five short scenarios, one per trigger in the
§6 table, followed by a full review-and-delete pass. All against Westbrook Bank packages —
adjust package IDs and names to your own repository.

## Package deletion

```python
ea_model(operation="list_package_tree", params={
    "root_package_id": 41,                 # "Legacy Integrations"
    "include_element_counts": True,
    "include_diagrams": True,
})
# -> {"ok": True, "root_package_id": 41, "depth": 1, "package_count": 2, "truncated": False,
#     "packages": [
#       {"Package_ID": "41", "Name": "Legacy Integrations", "Parent_ID": "7", "ea_guid": "{...}",
#        "element_count": 14, "diagrams": [{...}, {...}, {...}]},
#       {"Package_ID": "58", "Name": "Archive", "Parent_ID": "41", "ea_guid": "{...}",
#        "element_count": 0, "diagrams": []}]}
```

`delete_package` itself reports nothing about what it removed (`{"ok": true,
"deleted_package_id": 41}` only), so pull the count first — it's also what makes the offer
concrete instead of vague. `element_count` and `diagrams` are per package, so add them up across
`packages` to describe the whole subtree:

> "About to delete `Legacy Integrations` (14 elements, 3 diagrams). Want me to baseline it
> first, so there's a rollback point?"

Accepted:

```python
ea_repository(operation="create_baseline", params={
    "package_id": 41,
    "version": "2026-09-24-pre-delete",
    "notes": "Snapshot before deleting Legacy Integrations",
})
# then:
ea_model(operation="delete_package", params={"package_id": 41})
```

Declined: proceed straight to `delete_package`, and don't offer again for another
`delete_package` call this session.

## Bulk edit

A scripted loop retagging 38 elements' `lifecycle` tag is still one logical operation, even
issued as 38 separate `set_tagged_value` calls — count the elements the loop is about to touch
before the first call, not after:

> "This will update `lifecycle` on 38 elements under `Consumer Banking`. Want a baseline of
> that package first?"

```python
ea_repository(operation="create_baseline", params={
    "package_id": 5,
    "version": "2026-09-24-pre-lifecycle-update",
    "notes": "Snapshot before bulk lifecycle retag (38 elements)",
})
```

Then run the loop. Same offer applies to a single `create_elements_bulk`/
`create_connectors_bulk`/`add_elements_to_diagram_bulk` call whose `specs`/`element_ids` list
exceeds 25 entries.

## Ruleset-driven fix

The audit itself is read-only and never triggers the offer — only acting on what it finds does:

```python
ea_validate(operation="audit", params={
    "rules_path_or_content": "https://.../ruleset-wba-app-tags.yaml",
    "package_id": 5,
})
# -> 31 elements non-conformant on `dataClassification`
```

31 exceeds the threshold, so offer before applying the fixes:

> "The ruleset found 31 elements in `Consumer Banking` missing `dataClassification`. Want a
> baseline before I set it on all of them?"

## MDG rollout

Installing a technology into a repository that already has content it will reclassify:

```python
ea_mdg(operation="install_mdg", params={
    "xml_path_or_content": "<path to WBA_MDG.xml>",
    "scope": "embedded",
})
```

Offer before the install when the model already holds elements the technology's conformance
rules will touch — the risk isn't the install itself, it's the retagging that follows it:

> "Installing `WestbrookBankArchitecture` and then bringing the existing `Consumer Banking`
> elements into conformance will touch every element under it. Want a baseline of the model
> root first?"

Model-root scope here, not package scope — a rollout's conformance pass is rarely confined to
one package once it starts.

## XMI import

```python
ea_repository(operation="import_xmi", params={
    "package_id": 5,
    "path": "<exports>\\consumer-banking.xmi",
})
```

Always offer, regardless of the file's size — `import_xmi` mutates the target package in place
and is documented as semi-destructive:

> "About to import `consumer-banking.xmi` into `Consumer Banking`. Want a baseline of that
> package first, in case the import needs undoing?"

---

## A full review-and-cleanup pass

Scenario: several baselines have accumulated on `Consumer Banking` (`package_id=5`) from the
scenarios above, and the user asks what can be cleaned up.

### 1. List and size

```python
ea_repository(operation="list_baselines", params={"package_id": 5})
```

```json
{
  "package_id": 5,
  "baselines": [
    {"guid": "{A}", "version": "2026-09-23-pre-restructure", "notes": "Snapshot before splitting the vendor-system subtree", "name": "Consumer Banking"},
    {"guid": "{B}", "version": "2026-09-24-pre-lifecycle-update", "notes": "Snapshot before bulk lifecycle retag (38 elements)", "name": "Consumer Banking"},
    {"guid": "{C}", "version": "2026-09-24-pre-import", "notes": "Snapshot before consumer-banking.xmi import", "name": "Consumer Banking"}
  ],
  "count": 3
}
```

```python
ea_analyze(operation="execute_sql", params={"sql":
    "SELECT DocID, LENGTH(BinContent) AS bytes FROM t_document "
    "WHERE DocType = 'Baseline' AND DocID IN ('{A}', '{B}', '{C}')"
})
```

Join on `guid`/`DocID` and present as a table (bytes converted to KB for readability):

| Version | Notes | Size |
|---|---|---|
| `2026-09-23-pre-restructure` | Snapshot before splitting the vendor-system subtree | 412 KB |
| `2026-09-24-pre-lifecycle-update` | Snapshot before bulk lifecycle retag (38 elements) | 58 KB |
| `2026-09-24-pre-import` | Snapshot before consumer-banking.xmi import | 61 KB |

### 2. Ask, naming what goes

> "`2026-09-23-pre-restructure` is the largest at 412 KB and its change (the vendor-system
> split) is already confirmed good — the other two are recent and small. Delete
> `2026-09-23-pre-restructure`?"

### 3. Delete only what was confirmed

```python
ea_analyze(operation="execute_sql", params={"sql":
    "DELETE FROM t_document WHERE DocType = 'Baseline' AND DocID = '{A}'"
})
```

### 4. Verify

```python
ea_repository(operation="list_baselines", params={"package_id": 5})
# -> count: 2, and {A} is no longer in the list
```

Trust the re-list, not the `execute_sql` response — `write_performed: true` confirms a DELETE
statement ran, not that the correct row was the one it removed.

### Whole-model sweep

To review every package rather than one, collect the candidate package IDs first:

```python
ea_model(operation="list_root_packages", params={})
# then, for each root of interest:
ea_model(operation="list_package_tree", params={"root_package_id": <id>})
```

Then run the same `list_baselines` → size → confirm → delete → verify sequence per
`package_id`. There is no single call that lists baselines across the whole repository at once.

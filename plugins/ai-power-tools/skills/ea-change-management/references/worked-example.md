# Worked example — baseline, change, compare, audit, clean up

A full walkthrough against a Westbrook Bank package, following the same steps used to verify
`SKILL.md`. Adjust package IDs and names to your own repository; the stereotypes and tags are
canonical and should not be adjusted.

Scenario: before restructuring part of the `Consumer Banking` domain, take a package-level
baseline, make a change, inspect what moved, and answer "what changed and who changed it."

## 1. Preflight

```python
ea_repository(operation="get_repository_info", params={})
```

Confirm the open model is `WestbrookBank.qea` before touching anything. If a scratch/test package
already exists from prior work (for example, other `_*_scratch` or `_MCP_E2E_TEST_*` packages
under the model root), leave it alone — it belongs to someone else's session.

## 2. Baseline the package before the change

```python
ea_repository(operation="create_baseline", params={
    "package_id": 5,                       # "Consumer Banking"
    "version": "2026-09-23-pre-restructure",
    "notes": "Snapshot before splitting the vendor-system subtree",
})
```

Returns a `baseline_guid` — keep it. `list_baselines` confirms it stuck:

```python
ea_repository(operation="list_baselines", params={"package_id": 5})
```

```json
{
  "package_id": 5,
  "baselines": [
    {
      "guid": "{...}",
      "version": "2026-09-23-pre-restructure",
      "notes": "Snapshot before splitting the vendor-system subtree",
      "date": "",
      "author": "",
      "name": "Consumer Banking"
    }
  ],
  "count": 1
}
```

`date` and `author` come back empty in this version — don't rely on them. If you need to know
when a baseline was actually taken, query `t_document` (`DocType='Baseline'`) instead.

## 3. Make the change

A representative Westbrook Bank element, created with the canonical stereotype, metaclass, and
base tagged-value set (`_shared/references/westbrook-example.md` §2–3):

```python
ea_model(operation="create_element", params={
    "package_id": 5,
    "type": "Component",                       # WBABusinessApplication is a Component
    "name": "Consumer Lending Platform",
    "stereotype": "WBA::WBABusinessApplication",
})

ea_model(operation="update_element", params={
    "element_id": <new id>,
    "tagged_values": {
        "criticality": "Business-Critical",
        "lifecycle": "Current",
        "businessOwner": "Consumer Lending",       # a team, never a person's name
        "technicalOwner": "Core Banking Platform",
        "dataClassification": "Confidential",
        "regulatoryScope": "SOX",
    },
})
```

Then, some time later, the change worth tracking — a lifecycle transition:

```python
ea_model(operation="update_element", params={
    "element_id": <same id>,
    "tagged_values": {"lifecycle": "Sunset"},
})
```

## 4. Compare against the baseline

```python
ea_repository(operation="compare_baseline", params={
    "package_id": 5,
    "baseline_guid": "{...}",
})
```

The full response, trimmed:

```python
{"status": "comparison_opened", "package_id": 5, "baseline_guid": "{...}",
 "structured_diff_available": True,
 "diff": {
   "has_changes": True,
   "item_status_counts": {"Identical": 1, "Model only": 1, "Baseline only": 1},
   "item_count": 3,
   "include_identical": False,
   "items": [
     {"name": "PaymentGateway", "type": "", "status": "Model only",
      "guid": "{C0CA1B4C-F674-4652-A180-F283DF5D06C6}",
      "parent_guid": "{CE22A172-94A8-4c09-9979-B67BD05C8279}", "depth": 1,
      "properties": [{"name": "Name", "model": "PaymentGateway",
                      "baseline": None, "status": "Model only"}]},
   ],
   "compared_packages": [{"name": "Payments", "guid_form": "underscore",
                          "guid": "EAID_CE22A172_94A8_4c09_9979_B67BD05C8279",
                          "compared_on": "2026-09-23 10:14:21", "has_changes": True}],
   "log_bytes": 5465}}
```

`diff.items` lists the new element with `"status": "Model only"` and the edited element with
`"status": "Changed"`, whose `properties` carry the `lifecycle` value on the `model` side and on
the `baseline` side. Unchanged elements are counted in `diff.item_status_counts` but withheld
until you pass `"include_identical": true`. See §2 of the skill for the full shape.

If the call appears to hang, look at EA's screen — a modal dialog holds the COM connection until
it is dismissed. See [`../../_shared/references/ea-ui-verification.md`](../../_shared/references/ea-ui-verification.md).

## 5. Answering "what changed and who changed it" from the audit trail

The baseline diff tells you how the package differs from a snapshot. These tell you when it
happened and who did it — a different question, and often the more useful one.

```python
ea_analyze(operation="get_updates_in_range", params={
    "start": "2026-09-23",              # ISO-8601 with T and Z is also accepted (server 2.3.0+)
    "end": "2026-09-23",                # a bare end date covers the whole day
    "kind": "elements",
})
```

This lists every element and package touched repository-wide in the window, with `package_id` on
each row — filter to `package_id == 5` for a package-scoped view. It won't show *what* changed
about each item (no field-level diff), only *that* something did and when — enough to know where
to look with `ea_model(operation="get_element", ...)`.

```python
ea_analyze(operation="get_user_activity", params={
    "start": "2026-09-23 00:00:00",
    "end": "2026-09-23 23:59:59",
})
```

Returns one row per author with `elements_modified`, `diagrams_modified`, `last_active` — useful
for "who touched this package recently," before you go ask them why.

## 6. If you need to undo

Only because this baseline was just taken for exactly this purpose:

```python
ea_repository(operation="apply_baseline", params={
    "package_id": 5,
    "baseline_guid": "{...}",
})
```

Read `SKILL.md` §3 in full before running this against anything you didn't just baseline
yourself. Verify the result afterward by re-querying the package's elements — don't trust the
response alone, in either direction; see `SKILL.md` §4 for why.

## 7. Clean-up discipline

If this was a trial run rather than a real change, delete what you added rather than leaving
test elements in a real content package:

```python
ea_model(operation="delete_element", params={"element_id": <id>})
```

And confirm nothing was left behind:

```sql
SELECT Object_ID, Name FROM t_object WHERE Package_ID = 5 AND Name = 'Consumer Lending Platform'
```

An empty result confirms the clean-up held.

## 8. Before deleting a package

`delete_package` deletes the package's own baselines along with it, so a baseline of the package
you are about to delete is gone the moment the delete runs. Take the restore point somewhere that
survives: a baseline of the **parent** package, or an XMI export of the package.

```python
# The package to delete is 41 ("Legacy Integrations"); its parent is 7.
ea_repository(operation="create_baseline", params={
    "package_id": 7,
    "version": "2026-09-24-pre-delete",
    "notes": "Snapshot of the parent before deleting Legacy Integrations",
})
ea_repository(operation="list_baselines", params={"package_id": 7})   # confirm it exists

# Or, to keep just that package so it can be brought back on its own:
ea_repository(operation="export_xmi", params={
    "package_id": 41,
    "path": "<export-dir>/Legacy-Integrations.xmi",
})
```

Check the export's `elements_in_package` against `elements_in_export` before relying on it.
Applying the parent baseline later rewinds everything under the parent, so for one package the
XMI export is the more precise way back. Then delete:

```python
ea_model(operation="delete_package", params={"package_id": 41})
```

If the package or one below it already has baselines, the call is refused with
`package_has_baselines` (or `baselines_unreadable` when they cannot be read). Tell the person
those baselines will be lost, and only after they agree repeat the call with
`allow_baseline_loss: true`; the result lists `baselines_removed`.

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
    "start": "2026-09-23",              # ISO-8601 with T and Z is also accepted
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

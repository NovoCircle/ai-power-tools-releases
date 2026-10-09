# Applying a newly installed MDG to existing repository data

Back to [SKILL.md](../SKILL.md).

After deploying an MDG, EA does not automatically update existing elements. Ask the user whether
they want to migrate existing elements to use the new MDG's stereotypes and tagged values.

### Step 1 — Ask

> "The MDG is installed. Would you like to apply it to existing elements in the repository?
> I can find all elements that match the base type(s) of your stereotypes and offer to update
> their stereotype and initialize their tagged values."

If yes, proceed with Steps 2–4. If no, stop.

### Step 2 — Identify candidate elements

Use `ea_analyze(operation="execute_sql", ...)` (read-only) to find elements whose `Object_Type` matches the base type(s)
of your stereotypes and that do not yet have the MDG stereotype set:

```python
# Example: find all Class elements that aren't already stereotyped as WBA types
candidates = ea_analyze(operation="execute_sql", params={"sql": """
    SELECT o.Object_ID, o.Name, o.Object_Type, o.Stereotype, o.Package_ID
    FROM t_object o
    WHERE o.Object_Type = 'Class'
      AND (o.Stereotype IS NULL OR o.Stereotype NOT IN ('WBADataAsset','WBADataEntity','WBAAIModel'))
    ORDER BY o.Name
"""})
```

Present the list to the user and confirm which elements to update before proceeding.

### Step 3 — Update elements

For each confirmed element, use `ea_model(operation="update_element", ...)` to set the stereotype and initial tagged values:

```python
ea_model(operation="update_element", params={
    "element_id": obj_id,
    "properties": {"stereotype": "WBADataAsset"},
    "tagged_values": {
        "dataClassification": "",
        "businessOwner": "",
        "regulatoryScope": "",
    }
})
```

`WBADataAsset` carries only the base tag set (Section 3 of the canon example spec) — it is not one
of the three AI stereotypes, so it does not get `dataResidency` or the other AI-only tags.

> **Do not use `repo.Execute()` DML to set stereotypes** — EA's internal cache won't update.
> Always use the `update_element` MCP tool for stereotype changes, so EA's runtime state
> stays consistent.

### Step 4 — Validate

Run the companion YAML sidecar immediately after the migration to find any elements that need
attention:

```python
ea_validate(operation="audit", params={"rules_path_or_content": "WBA_rules.yaml"})
```

Review violations and ask the user to fill in required tagged values before saving.

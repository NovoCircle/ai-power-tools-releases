# Element Creation, Tagged Values, and Stereotype Persistence

Detail supporting [`../SKILL.md`](../SKILL.md) §4 and §4.5. Read those sections first for the
decision points (bulk vs. single, `create_element_in_language` vs. `create_element`); this file
carries the full code patterns, the complete WBA tagged-value set, and the stereotype-persistence
deep dive.

---

## 1. Bulk and single element creation — full patterns

### Recommended pattern (v0.3.0+)

**More than ~5 elements at once → use `create_elements_bulk`:**

```python
ea_model(operation="create_elements_bulk", params={"specs": [
    {
        "package_id": app_pkg_id,
        "name": "Customer Portal",
        "type": "Component",
        "stereotype": "WBABusinessApplication",
        "properties": {"Notes": "Internet banking front-end"},
        "tagged_values": {
            "criticality": "Mission-Critical",
            "lifecycle": "Current",
            "businessOwner": "Retail Banking Ops",
            "technicalOwner": "Digital Eng",
            "dataClassification": "Confidential",
            "regulatoryScope": "PCI-DSS",
        },
    },
    # ... more specs ...
]})
```

The bulk call is idempotent (existing name + package + stereotype is skipped, not
duplicated) and returns a structured `{created, skipped, failed, results}` summary.
Failures don't abort the batch.

**Single element (still valid for one-offs):**

```python
ea_model(operation="create_element", params={
    "package_id": app_pkg_id,
    "name": "Customer Portal",
    "type": "Component",
    "stereotype": "WBABusinessApplication",
    "properties": {"Notes": "..."},
    "tagged_values": {"criticality": "Mission-Critical", "lifecycle": "Current"},
})
```

The `properties` and `tagged_values` arguments are safe to use together. Tagged values are
idempotent by name — calling `ea_model(operation="update_element", params={"element_id": ..., "tagged_values": {"k": "v2"}})` on an element where `k=v1` already exists
overwrites in place rather than creating a duplicate.

### MDG-native element creation — `create_element_in_language`

When the target element type is defined by an MDG profile (ArchiMate3, BPMN2.0, or a
your organization's own MDG), prefer `create_element_in_language` over plain `create_element`.
It resolves the stereotype's base metaclass from the technology and passes it to
`create_element` as `type`, so the element cannot be created as the wrong EA type. The
`t_xref` profile binding itself is not specific to it: a plain `create_element` whose `type`
and `stereotype=` match a loaded MDG profile writes the same binding (§2).

`create_element_in_language` has no `tagged_values` parameter — unlike `create_element`, it
only takes `properties`, and passing `tagged_values` fails the call with `unknown_parameters`.
Apply governance tags with a follow-up keyed off the `element_id` the creation call returns:
`update_element` with `tagged_values={...}` sets them all in one call, or `set_tagged_value`
sets one per call:

```python
result = ea_model(operation="create_element_in_language", params={
    "package_id": app_pkg_id,
    "name": "Customer Portal",
    "language_id": "WBA",                     # registered technology id, not the profile display name
    "language_type": "WBABusinessApplication",   # stereotype name within that MDG
    "properties": {"Notes": "Internet banking front-end"},
})
element_id = result["element_id"]

# set_tagged_value is idempotent by tag name, so this is safe to re-run.
for tag_name, tag_value in {
    "criticality": "Mission-Critical",
    "lifecycle": "Current",
}.items():
    ea_model(operation="set_tagged_value", params={
        "element_id": element_id,
        "name": tag_name,
        "value": tag_value,
    })
```

**Bulk with MDG routing:** Pass `language_id` and `language_type` inside each spec in
`create_elements_bulk`. When both are present, the bulk call automatically routes that
spec through `create_element_in_language` instead of `create_element`:

```python
ea_model(operation="create_elements_bulk", params={"specs": [
    {
        "package_id": app_pkg_id,
        "name": "Customer Portal",
        "language_id": "WBA",
        "language_type": "WBABusinessApplication",
        "tagged_values": {"criticality": "Mission-Critical"},
    },
]})
```

### Stereotype → Object_Type mapping

The WBA MDG stereotypes map to these EA `Object_Type` values:

| Stereotype | Object_Type (`ea_model("create_element")` `type`) |
|------------|---------------------------------------------|
| `WBABusinessApplication` | `Component` |
| `WBAVendorSystem` | `Component` |
| `WBABusinessService` | `Component` |
| `WBAAIService` | `Component` |
| `WBAAIGateway` | `Component` |
| `WBADataAsset` | `Object` |
| `TechNode` | `Node` |

### Full WBA MDG tagged value set

Set all applicable tags in one block immediately after `create_element`. This is the
canonical 10-tag set (base 6 + AI-only 4) from `_shared/references/westbrook-example.md`
section 3 — see that file if a value below looks wrong; it is the source of truth.

```
criticality         → "Mission-Critical" | "Business-Critical" | "Important" | "Standard"
lifecycle            → "Strategic" | "Current" | "Sunset" | "Deprecated" | "Retired"
businessOwner        → team or role string, never a real person's name
technicalOwner       → team or role string, never a real person's name
dataClassification   → "Public" | "Internal" | "Confidential" | "Restricted"
regulatoryScope      → free text, e.g. "PCI-DSS" | "GDPR" | "SOX" | "" (blank = none)
```

AI-only tags (`WBAAIGateway`, `WBAAIService`, `WBAAIModel` only):

```
modelGovernanceClass   → "SR-11-7-Tier-1" | "SR-11-7-Tier-2" | "Internal-Use" | "Experimental"
humanInLoopRequired     → "true" | "false"
auditLoggingEnabled     → "true" | "false"
dataResidency           → free text jurisdiction, e.g. "EU" | "US-only"
```

Enumeration values are exact — `Mission Critical` (space instead of hyphen) is wrong and
will fail a conformance check. `businessOwner` / `technicalOwner` take a team name such as
`Payments Engineering`, never a person's name.

> **Non-canon tags found in this section before the 2026-09-23 split:** `vendor`, `product`,
> `pciScopeJustification`, and `pciControlOwner` were listed here alongside the real 10. They
> are not part of the WBA MDG per the canonical spec (section 3 is exhaustive: "all 10"). They
> have been removed from this list rather than silently kept, since they do not correspond to
> anything the MDG actually defines. If the product genuinely needs vendor/product tracking or
> a PCI-specific justification tag, that is new MDG design work, not an example-authoring fix —
> flag it to whoever owns the WBA MDG XML.

### Verification after tagging

Spot-check a tagged element with SQL to confirm storage:
```
ea_analyze(operation="execute_sql", params={"sql": """
    SELECT p.Property, p.Value
    FROM t_objectproperties p
    WHERE p.Object_ID = <element_id>
    ORDER BY p.Property
"""})
```

Expect one row per tag. If a tag is missing, `ea_model(operation="set_tagged_value", ...)` did not persist — retry
the call. This is rare but happens on the first call to a new MDG-enabled project while
the tag schema is being initialized.

---

## 2. Stereotype persistence — where EA stores what

**This is the most common source of silent failures.** EA stores stereotype information
in up to three separate places, and which place it writes to depends on which tool and
path you use.

### Three stereotype storage locations

| Store | Table | Column | What writes here | What reads here |
|---|---|---|---|---|
| Simple stereotype | `t_object` | `Stereotype` | `ea_model("create_element")` with `stereotype=`, `ea_model("update_element")` with `properties={"Stereotype":}` | EA browser, most queries |
| StereotypeEx (full MDG path) | `t_object` | `StereotypeEx` | `ea_model("update_element")` with `properties={"StereotypeEx":}` | EA validation, profile-aware tools |
| MDG profile application | `t_xref` | `Description` | Whichever of these applies a stereotype matching a loaded MDG profile: `ea_model("create_element_in_language")`, `ea_model("create_element")` with `stereotype=`, `ea_model("create_elements_bulk")` in either form, `ea_model("update_element")` with `StereotypeEx` when EA accepts it | EA MDG engine, diagram rendering |

### How each tool writes stereotypes

`<technology-id>` is the id EA registers the MDG technology under; `<profile>` is the profile
name that prefixes the stereotype's FQName in `t_xref`. They can be different strings.

```
ea_model(operation="create_element", params={"type": "<base-metaclass>", "stereotype": "<stereotype>", ...})
  -> writes t_object.Stereotype = "<stereotype>"
  -> writes t_xref row (MDG profile application) when the stereotype matches a loaded
     MDG profile, with FQName=<profile>::<stereotype>
  -> `type` is yours to get right; a wrong base metaclass can make EA reject the stereotype

ea_model(operation="create_element_in_language", params={"language_id": "<technology-id>", "language_type": "<stereotype>", ...})
  -> writes t_object.Stereotype = "<stereotype>"
  -> writes t_object.StereotypeEx = "<stereotype>=<profile>::<stereotype>;"
  -> writes t_xref row (MDG profile application, BaseClass="element")
  -> resolves the base metaclass for you; same binding as create_element, without the type risk

ea_model(operation="update_element", params={"element_id": ..., "properties": {"StereotypeEx": "<stereotype>=<profile>::<stereotype>;"}})
  -> writes t_object.StereotypeEx
  -> does two Update() calls internally (first for other props, second specifically for StereotypeEx)
  -> returns stereotype_warning if EA rejected the value (readback is empty after Update)
  -> writes the t_xref row when EA accepts the value; a rejected value (stereotype_warning)
     leaves no profile binding — less reliable than create_element_in_language
```

### How to verify stereotype persistence

```sql
-- 1. Check t_object (basic + StereotypeEx)
SELECT Object_ID, Name, Stereotype, StereotypeEx
FROM t_object
WHERE Object_ID = <element_id>

-- 2. Check t_xref (MDG profile application)
SELECT XrefID, [Type], [Name], Client, Supplier, [Description]
FROM t_xref
WHERE Client = '<element_guid>'
  AND [Type] = 'element'

-- 3. Check tagged values (confirms MDG profile is active)
SELECT Property, [Value]
FROM t_objectproperties
WHERE Object_ID = <element_id>
```

If step 2 returns no rows, the MDG profile was not applied — the element's stereotype
is cosmetic only. A row whose `Description` has no `FQName` means the technology was not loaded
when the stereotype was applied. To fix, delete and recreate the element using
`create_element_in_language`, with the technology loaded.

### Diagnosing `update_element` StereotypeEx failures

`update_element` now returns `stereotype_warning` in the response when the StereotypeEx
write was rejected by EA. Check for this key:

```python
result = ea_model(operation="update_element", params={"element_id": <id>, "properties": {"StereotypeEx": "..."}})
if result.get("stereotype_warning"):
    # EA rejected the stereotype — use create_element_in_language instead
    print(result["stereotype_warning"])
```

The most common rejection cause: the element's `Object_Type` (`t_object.Object_Type`)
doesn't match what the MDG profile expects as the base metaclass. You cannot change
`Object_Type` after creation — recreate via `create_element_in_language`.

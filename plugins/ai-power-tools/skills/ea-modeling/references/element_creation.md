# Element Creation, Tagged Values, and Stereotype Persistence

Detail supporting [`../SKILL.md`](../SKILL.md) §4, §4.5 and §4.6. Read those sections first for the
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
Failures don't abort the batch. This holds when the stereotype is written as the technology id,
the profile name or the bare name: the server compares the qualified binding, not the text you
passed, so a rerun skips MDG-typed items too (server 3.6.5 or later; before that a rerun
duplicated them).

Set `parent_id` in a spec to nest the element under an existing element in the same package. A
parent created in the same call cannot be named, so create parents first. A parent that does not
exist is `parent_not_found` and one in another package is `parent_in_other_package`, each with the
`spec_index`; the result returns the stored `parent_id`.

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

Westbrook Bank's `WBA` technology is the illustration; your technology declares its own
stereotypes and base metaclasses (read them with `get_mdg_from_runtime`). The WBA mapping, from
the canon in `_shared/references/westbrook-example.md` section 2, is below. The metaclass is
what you pass as `type` to `create_element`; a wrong one can make EA drop the stereotype.

| Stereotype | Object_Type (`ea_model("create_element")` `type`) |
|------------|---------------------------------------------|
| `WBABusinessApplication`, `WBABusinessService`, `WBAVendorSystem`, `WBARegulatedFunction`, `WBASystemOfRecord`, `WBAAIGateway`, `WBAAIService` | `Component` |
| `WBAAIModel`, `WBADataAsset`, `WBADataEntity`, `WBAGovernedElement` | `Class` |
| `WBARegulatedActivity`, `WBACustomerTouchpoint`, `WBAExternalCall` | `Activity` |
| `WBATechnologyNode` | `Node` |

A model built before the technology was loaded can hold these elements under another metaclass
(for example data assets stored as `Object`). Check what the model holds with
`ea_analyze("summarize_observed_metaclasses", {"stereotype": ...})` before copying its pattern.

### Full WBA MDG tagged value set

Set all applicable tags in one block immediately after `create_element`. This is the
canonical set from `_shared/references/westbrook-example.md` section 3 (base 6, AI-only 4,
and three PCI and vendor tags below); see that file if a value below looks wrong; it is the
source of truth.

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

PCI and vendor tags (free text), declared on only some stereotypes:

```
pciScopeJustification  → WBABusinessApplication, WBAVendorSystem
product                → WBAVendorSystem
vendor                 → WBAVendorSystem
```

The technology declares these 13 tags (6 + 4 + 3). Set one only on a stereotype that declares
it. To check any tag against your own technology, read the stereotype's `tagged_values` from
`get_mdg_from_runtime`; do not rely on a remembered list.

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
in up to three separate places. Two of them are columns you can query; the third,
`StereotypeEx`, is not. Server 3.6.5 or later writes all three from `create_element`,
`create_element_in_language` and `update_element`, and reports the outcome in the result's
`stereotype` block (`requested`, `written`, `stored`, `bound_as`, `status`, `reason`) and in
`rejected_properties`. Read those first; the queries below audit what is stored.

Write the stereotype as the technology id (`WBA::WBABusinessApplication`) or, when only one loaded
technology defines it, the bare name. The server translates the id (or a profile name, if you
write one) to the profile-qualified form EA binds. A bare name that two loaded technologies define is written as given and EA binds the
first match; `stereotype.bound_as` shows which. Substitute your own technology id and profile
name.

### Three stereotype storage locations

| Store | Table | Column | What writes here | What reads here |
|---|---|---|---|---|
| Simple stereotype | `t_object` | `Stereotype` | `ea_model("create_element")` with `stereotype=`, `ea_model("update_element")` with `properties={"Stereotype":}` | EA browser, most queries |
| StereotypeEx (full MDG path) | none: a COM property, **not a `t_object` column** (the query is rejected if you select it) | n/a | `ea_model("create_element")`, `ea_model("create_element_in_language")` and `ea_model("update_element")` with `properties={"StereotypeEx":}` | `get_element` (its `stereotype` shows `StereotypeEx` when set), EA's profile-aware tools |
| MDG profile application | `t_xref` | `Description` | Whichever of these applies a stereotype matching a loaded MDG profile: `ea_model("create_element_in_language")`, `ea_model("create_element")` with `stereotype=`, `ea_model("create_elements_bulk")` in either form, `ea_model("update_element")` with `StereotypeEx` when EA accepts it | EA MDG engine, diagram rendering |

### How each tool writes stereotypes

`<technology-id>` is the id EA registers the MDG technology under; `<profile>` is the profile
name that prefixes the stereotype's FQName in `t_xref`. They can be different strings.

```
ea_model(operation="create_element", params={"type": "<base-metaclass>", "stereotype": "<stereotype>", ...})
  -> writes t_object.Stereotype = "<stereotype>"
  -> sets the StereotypeEx property to the qualified name
  -> writes the t_xref row (MDG profile application) when the stereotype matches a loaded
     MDG profile; what EA stores there is FQName=<profile>::<stereotype>
  -> `type` is yours to get right; a base metaclass the stereotype does not suit makes EA drop it

ea_model(operation="create_element_in_language", params={"language_id": "<technology-id>", "language_type": "<stereotype>", ...})
  -> writes the same three stores as create_element
  -> resolves the base metaclass for you, so it has no type risk

ea_model(operation="update_element", params={"element_id": ..., "properties": {"StereotypeEx": "<stereotype>"}})
  -> applies the stereotype after the fact, with a second Update() call of its own
  -> a stereotype EA drops is listed in rejected_properties (and stereotype_warning), never
     in applied_properties, and `stereotype.status` is `rejected`
```

### How to verify stereotype persistence

**Read it back after every call that sets a stereotype.** A call can return success and leave
the element with no stereotype, or with only a bare name. One read answers it:

```sql
-- 1. The stored name and the profile application together
--    (t_object has Stereotype, not StereotypeEx; the profile binding is in t_xref)
SELECT o.Object_ID, o.Name, o.Object_Type, o.Stereotype, x.Description
FROM t_object o
LEFT JOIN t_xref x ON x.Client = o.ea_guid
                  AND x.[Type] = 'element property' AND x.Name = 'Stereotypes'
WHERE o.Object_ID = <element_id>

-- 2. Tagged values (the profile's tags appear once the profile is applied)
SELECT Property, [Value]
FROM t_objectproperties
WHERE Object_ID = <element_id>
```

Or call `ea_model("get_element")` and read `stereotype`. Read the result like this:

| What query 1 returns | Meaning |
|---|---|
| `Stereotype` empty | EA dropped the stereotype. Nothing was applied, whatever the response said. |
| `Stereotype` set, `Description` empty (no row) | A label only. The profile was never applied. |
| `Description` has `GUID=` and no `FQName=` | **Unlinked.** The stereotype is a plain name, not the technology's. Usually the technology was not loaded when it was applied. |
| `Description` has `FQName=<profile>::<stereotype>` | **Linked.** The technology's own stereotype, with its tag set. |

Through COM (`ea-com`) the same split shows as `FQStereotype` (`<profile>::<stereotype>` when
linked, the bare name when not) and `MetaType` (the stereotype name when linked, `Object` when
not). That reading comes from a research run on EA 17.0 and has not been re-checked for this
skill. The same research found a profile stereotype applied to an `Object` element is dropped
silently, where on a `Class` it links and brings the profile's full tag set, so confirm the
base metaclass first (the mapping above).

To fix an unlinked or dropped element, delete and recreate it with
`create_element_in_language` with the technology loaded, carrying its tags across (an element
with connectors or diagram placements needs those recreated too).

### Diagnosing a dropped stereotype

After any create or update that carries a stereotype, check `rejected_properties` and
`stereotype.status`. A `rejected` status leaves the call `ok: true`, and means the element's base
metaclass does not suit the stereotype (a Component given a Class-only stereotype, say). You
cannot change `Object_Type` after creation: recreate the element with
`create_element_in_language`.

```python
result = ea_model(operation="update_element", params={"element_id": <id>, "properties": {"StereotypeEx": "..."}})
if result["stereotype"]["status"] == "rejected":
    print(result["stereotype"]["reason"])   # recreate via create_element_in_language
```

---

## 3. A file stored on an Artifact

A file kept inside the model on an Artifact element is stored in two places, and EA needs both.

| Where | What |
|---|---|
| `t_document` | One row: `DocType='ExtDoc'`, `DocID` and `ElementID` = the artifact's `ea_guid`, `BinContent` = a zip archive that holds one entry, `str.dat`. |
| `t_object` (the artifact) | `Style='ExtDoc=1;'` and `NType=32`. |

Without `ExtDoc=1;` on the artifact EA will not open the file when you double-click it, even
though the `t_document` row is there. After storing a file, read back what you wrote: the row
exists for that GUID, the artifact carries both marks, and the stored bytes unzip to the file
you stored.

```sql
SELECT d.DocID, d.DocType, LENGTH(d.BinContent) AS bytes, o.Style, o.NType
FROM t_object o
LEFT JOIN t_document d ON d.ElementID = o.ea_guid AND d.DocType = 'ExtDoc'
WHERE o.Object_ID = <artifact_id>
```

Name `BinContent` explicitly and never `SELECT *` on `t_document`; the column holds the file.
This layout was measured on EA 17.0 against a MySQL-backed cloud repository.

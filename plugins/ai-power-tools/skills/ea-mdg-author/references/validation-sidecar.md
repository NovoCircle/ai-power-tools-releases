# Validation rules — YAML sidecar, not `<Scripts>`

Back to [SKILL.md](../SKILL.md).

When AI Power Tools for Sparx EA is deployed, **do not embed validation rules in the MDG's
`<Scripts>` section**. The `<Scripts>` mechanism runs JavaScript inside EA's scripting engine
and is not accessible to the MCP server.

```xml
<!-- WRONG — EA scripting, not accessible to ea_validate tool -->
<Scripts>
  <Script name="WBA Conformance Rules" type="Normal" language="JavaScript">
    <![CDATA[
    function EA_GetRuleSetList() { return "WBA Conformance"; }
    function EA_OnRunRule(RuleSetID, RuleID, ObjectType, ObjectID) { ... }
    ]]>
  </Script>
</Scripts>
```

Instead, create a `<mdg_name>_rules.yaml` sidecar file and run it with `ea_validate`.
See the `ea-validation` skill for the sidecar schema.

```yaml
# westbrook_rules.yaml — run with ea_validate(operation="audit", params={"rules_path_or_content": "..."})
meta:
  version: "1.0"
  mdg_family: WBA
rules:
  - id: WBA-TVR-001
    severity: error
    selector:
      type: element
      stereotypes:
        any_of: ["WBADataAsset"]
    condition:
      type: tagged_value_required
      tags:
        - name: dataClassification
          must_be_non_empty: true
```

### Creating the companion YAML sidecar

Every MDG produced by this skill must have a companion `<tech_id>_rules.yaml` file. Create it
as part of the MDG authoring workflow — one `tagged_value_required` rule for each tagged value
that is marked as mandatory in your MDG design.

Minimal template for a new MDG:

```yaml
meta:
  version: "1.0"
  mdg_family: WBA         # replace with your tech ID

rules:
  # One block per mandatory tagged value per stereotype.
  # Rule IDs: <TechID>-TVR-001, -002, ... for tagged-value rules
  #           <TechID>-CNX-001, -002, ... for connector rules

  - id: WBA-TVR-001
    severity: error
    demo_trigger: true    # mark the most critical check for quick smoke-testing
    selector:
      type: element
      stereotypes:
        any_of: ["WBADataAsset"]
    condition:
      type: tagged_value_required
      tags:
        - name: dataClassification
          must_be_non_empty: true
    remediation:
      short: Populate the dataClassification tagged value on this WBADataAsset

  # Repeat for each additional mandatory tag / stereotype combination
```

Run validation after every MDG install to confirm it finds violations on test data:
```
ea_validate(operation="audit", params={"rules_path_or_content": "WBA_rules.yaml", "mode": "demo_validation"})
```

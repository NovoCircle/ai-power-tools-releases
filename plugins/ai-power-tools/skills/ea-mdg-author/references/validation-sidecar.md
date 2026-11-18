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

Instead, create a `<tech_id>_rules.yaml` sidecar file and run it with `ea_validate`.
See the `ea-validation` skill for the sidecar schema.

```yaml
# WBA_rules.yaml — run with ea_validate(operation="audit", params={"rules_path_or_content": "..."})
meta:
  version: "1.0"
  mdg_family: WBA
rules:
  - id: WBA-TV-001
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
  # Rule IDs: <TechID>-TV-001, -002, ... for tagged-value rules
  #           <TechID>-CNX-001, -002, ... for connector rules

  - id: WBA-TV-001
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

### Beyond required tags

The sidecar can say more than "this tag is filled in". Connector ends (a lifecycle rule across a `Uses`
connector), cardinality at each end, what an element is typed by, what it specializes, what it owns, how deep
a chain of connectors may run, and whether a name or tag value is unique are all in the grammar: see
`ea-ruleset-author/references/rule-grammar.md`, "The extended grammar". Existing rules keep their meaning.

Waivers do not go into the rules. A signed and dated exception for one element lives beside the ruleset, in a
file named `<tech_id>_rules.exceptions.yaml` (or under `exceptions:` in the ruleset), and `meta.exclude_packages` leaves a whole package out.
Both are described in `ea-validation`.

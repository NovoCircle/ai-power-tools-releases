---
name: ea-validation
description: Author and run YAML sidecar conformance rules against a Sparx EA model via the ea_validate meta-tool. Use when you need to check that an MDG-modeled repository meets its required tagged values, connector cardinality, and endpoint stereotype constraints.
---

# Validating a Sparx EA Model Against a YAML Sidecar Ruleset

*Tool: `ea_validate(operation="audit", params={...})` (AI Power Tools for EA, v3.6.0+)*

> **v1.3.0 — meta-tool dispatch.** All individual tools are now dispatched via 6 meta-tools.
> `validate_model` is exposed as `ea_validate(operation="audit", params={"rules_path_or_content": ...})`.
> The underlying behavior is unchanged.

> **Building a complete ruleset for a modeling language?** Use the `ea-ruleset-author`
> skill instead — it covers the full workflow: spec research → rule-category planning →
> YAML authoring → testing → publishing to the skills bundle. This skill covers the YAML
> syntax and the validator API.

## When to use

- After importing or building a model that uses a custom MDG, to confirm every element carries the required tagged values.
- Before exporting a model snapshot for downstream consumption.
- As an automated gate in a model-CI pipeline.
- To run a pre-built hosted ruleset (e.g. the ArchiMate 3.1 conformance set) without any local file.

## Sidecar YAML shape

A YAML file with a top-level `rules` list. Each rule has:

```yaml
- id: WBA-TVR-001
  name: Employee Required Fields
  category: tagged_value_completeness
  severity: error          # error | warning | info
  demo_trigger: true       # run in mode="demo_validation"

  selector:
    type: element                       # element | connector
    stereotypes:
      any_of: [Employee]
    tagged_value_filter:                # optional pre-filter
      - tag: OrgLevel
        value_in: ["2", "3", "4"]

  condition:
    type: tagged_value_required         # see condition types below
    tags:
      - name: JobTitle
        must_be_non_empty: true

  remediation:
    short: Populate all required Employee tagged values
```

### Supported selector types

| `selector.type` | Required keys | Meaning |
|---|---|---|
| `element` | `stereotypes.any_of` | Iterate every element whose stereotype is in the list. Add `tagged_value_filter` to narrow further. |
| `connector` | `connector_stereotype` | Iterate every connector with that stereotype. |

### Supported condition types

| `condition.type` | Use for |
|---|---|
| `tagged_value_required` | One or more tags on the selected element must be non-empty. |
| `tagged_value_constraint` | One or more tags must take a value from `value_must_be_one_of`. |
| `connector_count` | Element must have between `min` and `max` connectors of a given stereotype (`direction: incoming \| outgoing`). |
| `connector_endpoint_stereotype` | Connector source/target must be in `source_must_be_one_of` / `target_must_be_one_of`. |
| `tagged_value_type_shipped` | A profile's tagged-value types (blank-`Type` attributes on stereotype-defining classes, per `ea-mdg-model-build`'s Phase 2 convention) must also appear in a **built MDG file's RefData** — i.e. must actually have been ticked on the MDG Technology Wizard's Tagged Value Types page, not just defined in `t_propertytypes`. Requires `built_mdg_path` (file path or raw XML). |

### `tagged_value_type_shipped` — catching "defined but never selected"

The MDG Technology Wizard's Tagged Value Types page is a *selection* step: a type
fully defined in `t_propertytypes` but never ticked there does not ship, and
nothing in the model shows this afterward. The symptom ("this field is free
text") is identical to "the type was never defined" but the fix is completely
different — see the `ea-mdg-model-build` skill's Phase 5/6 and Gotchas table.

```yaml
- id: mdg_tag_types_selected
  severity: warning
  selector:
    type: element
    stereotypes:
      any_of: [stereotype]     # EA's built-in stereotype-definition marker
  condition:
    type: tagged_value_type_shipped
    built_mdg_path: path/to/BuiltTechnology.xml   # or raw XML content
```

Scope to one profile package with the top-level `package_id` param on
`ea_validate`. Only types that are **both** referenced (blank `Type` on a
stereotype-defining class's attribute) **and** actually defined in
`t_propertytypes` are eligible to be flagged — a blank-`Type` attribute with
no `t_propertytypes` entry at all is the *other* failure mode (never defined)
and is out of scope for this rule.

> **Schema note.** No built MDG file with a populated `<TaggedValueTypes>`
> block was available to verify this parser against — every local fixture
> ships an always-empty `<TaggedValueTypes/>` stub. A populated fixture can be
> produced: reference data is reachable through
> `Project.ImportReferenceData` / `ExportReferenceData` and
> `Repository.PropertyTypes()`, and through the UI with computer use.
> The parser accepts any child element under
> `<TaggedValueTypes>` that carries a `name` attribute (written against the
> commonly observed `<TagType name="..." detail="..."/>` shape), so it
> shouldn't be brittle to minor schema variation — but re-verify against a
> real built file with reference data before relying on this for a
> high-stakes gate.

## Running the validator

```python
# Full scan — every rule in a local file
result = ea_validate(operation="audit", params={
    "rules_path_or_content": "path/to/rules.yaml"
})

# Demo mode — only rules with demo_trigger: true
result = ea_validate(operation="audit", params={
    "rules_path_or_content": "path/to/rules.yaml",
    "mode": "demo_validation",
})

# Scope to a single package subtree
result = ea_validate(operation="audit", params={
    "rules_path_or_content": "path/to/rules.yaml",
    "package_id": 42,
})

# URL fetch — server downloads and runs the ruleset (v1.2.0+)
result = ea_validate(operation="audit", params={
    "rules_path_or_content": "https://raw.githubusercontent.com/NovoCircle/ai-power-tools-skills/main/ruleset-archimate31/archimate31_rules.yaml",
})
```

### Using hosted rulesets (v1.2.0+)

`rules_path_or_content` accepts an `https://` URL — the server fetches the YAML at call time. No local file needed.

**Pre-built hosted rulesets (install via `install_skills` then reference by URL):**

| Ruleset | Description | URL fragment |
|---------|-------------|--------------|
| `ruleset-archimate31` | 27-rule ArchiMate 3.1 conformance set | `ruleset-archimate31/archimate31_rules.yaml` |

Base URL: `https://raw.githubusercontent.com/NovoCircle/ai-power-tools-skills/main/`

**Typical workflow with a hosted ruleset:**

```python
# 1. Run directly via URL — no install step needed, server fetches at call time
result = ea_validate(operation="audit", params={
    "rules_path_or_content": (
        "https://raw.githubusercontent.com/NovoCircle/ai-power-tools-skills"
        "/main/ruleset-archimate31/archimate31_rules.yaml"
    ),
})

# 2. Or install locally first, then run from the installed path (needs v3.6.0+,
#    which expands the `~`).
#    Rulesets do NOT install among the skills -- they carry no SKILL.md, so
#    they go under the product data directory instead. install_skills stands
#    down on a machine that has the plugin (the skills load from the plugin),
#    and the ruleset is not part of the plugin, so pass force=true; with names
#    limited to the ruleset it writes that one ruleset and nothing else.
ea_repository(operation="install_skills", params={"names": ["ruleset-archimate31"], "force": True})
result = ea_validate(operation="audit", params={
    "rules_path_or_content": "~/.claude/ai-power-tools/rulesets/ruleset-archimate31/archimate31_rules.yaml"
})

# 3. Or pass inline YAML content as a string (no file or URL required)
result = ea_validate(operation="audit", params={
    "rules_path_or_content": "rules:\n- id: QUICK-001\n  ..."
})
```

## Response shape

```python
{
  "ok": True,
  "mode": "full_scan",
  "rules_evaluated": 12,
  "violation_count": 3,
  "violations": [
    {
      "rule_id": "WBA-TVR-001",
      "severity": "error",
      "element_id": 4231,
      "element_name": "Jane Doe (CEO)",
      "message": "required tag 'JobTitle' is empty",
      "remediation": "Populate all required Employee tagged values",
    },
    ...
  ],
}
```

## Authoring tips

- Keep `id` codes short and grouped by category (`WBA-TVR-*` for tagged-value rules, `WBA-CNX-*` for connector rules).
- Set `severity: warning` for "should-have" rules (e.g. *Department has Members*) and `error` only for structural violations.
- Mark rules `demo_trigger: true` when they cover the happy-path subset you want to run as a quick smoke check.
- Pair this skill with `ea-mdg-author` — for every required tag in your MDG, add a `tagged_value_required` rule here.

## Common pitfalls

- **Stereotype namespace.** EA stores stereotypes as `<YourTechID>::StereotypeName`. The sidecar matches on the bare name; `ea_validate` strips the prefix when comparing.
- **Quoting tag values.** `OrgLevel` is stored as a string even when typed `int`. Use `value_must_be_one_of: ["1", "2", "3", "4"]` (strings).
- **Connector direction.** `outgoing` = "this element is the source"; `incoming` = "this element is the target". Reports-to runs subordinate→manager, so an Employee's `reports-to` count is *outgoing* from the subordinate.

## EA Computer Use — Latency Guidelines

Validation is MCP-only but the verification step (checking violations are cleared) may require
opening a diagram or the EA UI. Wait before screenshotting — 2–15 seconds depending on the
operation — and never retry without confirming the previous action failed. Full wait-time table
and the standard action/wait/screenshot pattern:
[`../_shared/references/latency.md`](../_shared/references/latency.md).

## See also

- `ea-ruleset-author` — full workflow for building and publishing a complete ruleset for a modeling language (ArchiMate, BPMN, UML, SysML, custom MDG, etc.).
- `ea-mdg-author` — for the matching MDG XML (stereotypes + tags + OCL).
- `ea-mdg-deploy` — for getting that MDG into the model so rules have something to validate.

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

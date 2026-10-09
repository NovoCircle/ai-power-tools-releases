# YAML Rule Grammar Reference

Full grammar for the rules you write in Phase 3 of `ea-ruleset-author/SKILL.md`. Read
this before writing your first rule, then come back to it whenever you need the exact
shape of a template or table.

---

## Start with the meta block

```yaml
# {Language} Conformance Ruleset
# Language:     {Language full name and version}
# Enforced by:  AI Power Tools for Sparx EA — validate_model tool
#
# Stereotype note:
#   <How EA names the stereotypes for this language>
#
# Sources:
#   [S1] {Primary spec} — {URL}
#   [S2] {Secondary source} — {URL}

meta:
  version: "1.0"
  language: {Language name}
  organization: "(your organization)"
  mdg_family: {MDG family name as it appears in EA's MDG list}
  description: >
    {One paragraph summary of what the ruleset checks.}
  severity_levels:
    error:   {What error means for this language}
    warning: {What warning means}
    info:    Advisory note; not a conformance violation
```

## Rule template

```yaml
  - id: {LANG}-{CAT}-{NNN}
    name: {Short human-readable name}
    description: >
      {2-4 sentences. Explain WHY this rule exists, what spec section it comes
      from, and what the violation means architecturally. Cite your sources.
      Example: "An Assignment relationship must originate from an Active Structure
      element. [S1 §5.2]"}
    category: {category_code_lowercase}
    severity: error        # error | warning | info
    demo_trigger: false    # true for ~30% of rules

    selector:
      type: connector      # connector | element
      connector_stereotype: {StereotypeName}     # for connector selectors
      # OR for element selectors:
      stereotypes:
        any_of: ["{StereotypeName}"]

    condition:
      type: connector_endpoint_stereotype        # see condition types below
      source_must_be_one_of:
        - StereotypeName1
        - StereotypeName2
      target_must_be_one_of:
        - StereotypeName3

    remediation:
      short: >
        {One sentence telling the modeler exactly what to do to fix this.
        Be concrete: "Use Serving instead of Realization here."}
      auto_fixable: false
```

## Condition type reference

| `condition.type` | Use for | Key fields |
|-----------------|---------|-----------|
| `connector_endpoint_stereotype` | Connector source/target stereotype constraints | `source_must_be_one_of`, `target_must_be_one_of` |
| `connector_count` | Element must have N connectors of a given stereotype | `connector_stereotype`, `direction` (incoming\|outgoing), `min`, `max` |
| `tagged_value_required` | Element must have non-empty tags | `tags: [{name, must_be_non_empty}]` |
| `tagged_value_constraint` | Tag must be one of an enum | `tags: [{name, value_must_be_one_of}]` |

## Writing connector endpoint rules

The most powerful rule type. Write them in this order:

1. List ALL valid source stereotypes (err toward inclusion — EA's MDG may have inherited
   subtypes you don't know about)
2. List ALL valid target stereotypes
3. Write the description explaining WHY these constraints exist
4. Set severity: `error` — endpoint violations are always structural

**EA stereotype names: unqualified, but otherwise verbatim.** This is the single
easiest way to ship a ruleset that validates nothing. `validate_model` selects with
`Stereotype IN (...)` against `t_object` / `t_connector` -- exact string comparison, no
normalization and no prefix stripping. A name one character off selects nothing, the
rule reports no violations, and the output is indistinguishable from a clean model.

*Leave the technology NAMESPACE off.* The profile-qualified form
`ArchiMate3::ArchiMate_Assignment` is real, but it is stored in `t_xref` rows named
`Stereotypes` and reached through the API's `StereotypeEx`. The `Stereotype` column that
rules match on holds the unqualified name, so matching the qualified form finds nothing.

*Do not strip anything else.* A prefix that belongs to the stereotype's own name is not a
namespace, and whether a technology uses one is a fact about that technology:

| Technology | What `t_object.Stereotype` holds | Selector to write |
|---|---|---|
| EA built-in ArchiMate (1, 2 and 3.1) | `ArchiMate_Assignment` | `ArchiMate_Assignment` |
| EA built-in BPMN2.0 | `BusinessProcess` | `BusinessProcess` |

Both rows were measured on EA 17.1 build 1716, in the MDG declaration and in stored model
data. So for an ArchiMate ruleset the selector reads:

```yaml
    selector:
      type: connector
      connector_stereotype: ArchiMate_Assignment   # NOT `Assignment` — that matches 0
```

*Measure it, do not infer it.* Run `summarize_stereotype_usage`, or read
`SELECT DISTINCT Stereotype FROM t_object`, against a model actually built with the
technology. Do not take the name from the notation's specification, and do not take it
from the MDG's `metatype` attribute -- `metatype` is the concept name without the prefix,
which is precisely the trap. `ruleset-archimate31/archimate31_rules.yaml` carries the
worked measurement in its header, including what the unprefixed form did when it shipped.

*Sanity-check the run.* Zero violations and zero matched elements are the same output.
Confirm a ruleset matched more than zero elements before reporting a model as clean.

## Writing connector count rules

```yaml
    condition:
      type: connector_count
      connector_stereotype: Aggregation   # the edge label to count
      direction: incoming                 # incoming | outgoing
      min: 2                              # at least 2
      # max: 5                            # optional upper bound
```

`direction: incoming` = connectors pointing INTO this element (element is the target).
`direction: outgoing` = connectors pointing OUT of this element (element is the source).

## Section comments

Use ASCII section headers to visually group rules:

```yaml
  # ═══════════════════════════════════════════════════════════════════════════
  # SECTION 1 — RELATIONSHIP ENDPOINT VALIDITY (REL)
  #
  # One or two lines explaining what this section covers and which spec
  # sections these rules come from.
  # ═══════════════════════════════════════════════════════════════════════════

  # ── Assignment ──────────────────────────────────────────────────────────────

  - id: WBA-REL-001
    ...
```

---

## See Also

- `ea-ruleset-author/SKILL.md` — the workflow this grammar supports
- `ruleset-archimate31/archimate31_rules.yaml` — the canonical reference implementation

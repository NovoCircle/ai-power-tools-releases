---
name: ea-ruleset-author
description: >
  Build a YAML validation ruleset for a modeling language (ArchiMate, BPMN, UML, SysML,
  custom MDG, etc.), consumed by validate_model. Covers the full authoring workflow:
  research → rule-category planning → YAML authoring → testing.
  Use this skill at the start of every new language ruleset, and keep it open throughout.
min_server_version: "1.2.0"
---

# Authoring a Validation Ruleset for a Modeling Language

A **ruleset** is a YAML file consumed by the server's validation engine (`validate_model`, server ≥ 1.2.0),
which you call as `ea_validate(operation="audit", params={...})`. It describes
what a correctly-formed model should look like for a given modeling language, and reports
every element or connector that does not conform. A ruleset can be run from a file path, a URL or
inline YAML. The rulesets for the languages in the catalog below ship in the plugin; one you write
stays wherever you keep it, so put it somewhere your team can reach.

This skill describes the repeatable four-phase workflow for building one ruleset from
scratch. Follow the phases in order, one language at a time.

---

## Scope

This skill builds rulesets. Running a ruleset or reading an audit result is the job of
`ea-validation`. When the request is only to run or read one, name `ea-validation`, say in one
sentence what to do next (pass the ruleset's path, URL or inline YAML to `ea_validate` with
`operation="audit"`, then read `violation_count` and `violations`), and write no ruleset unless
the person asks for one.

---

## Overview — What You're Building

```
rulesets/{id}/
└── {id}_rules.yaml        ← one YAML file, all rules for the language
```

The YAML has two top-level keys:

| Key | Purpose |
|-----|---------|
| `meta:` | Human-readable header: language, version, sources, severity legend |
| `rules:` | List of rule objects, one per conformance constraint |

The ArchiMate 3.1 ruleset (`<plugin root>/rulesets/archimate-3/archimate-3_rules.yaml`, which replaces `ruleset-archimate31`) is the canonical
reference implementation. Read it before starting a new language. The shipped rulesets sit in the
plugin's `rulesets` folder, next to its `skills` folder.

---

## Phase 1 — Research the Language Specification

### What to find

You need three things from the spec before writing a single rule:

1. **Element type table** — a complete list of all concept/element names and which
   structural category each belongs to (e.g., Active Structure, Behavior, Passive
   Structure, Motivation, etc.).
2. **Relationship validity table** — which relationship types are allowed between which
   element categories (or specific element pairs). This is usually in an appendix.
3. **Structural constraints** — "A Collaboration MUST have at least two members",
   "An Interaction MUST be assigned to a Collaboration", etc.

### Where to look

| Language | Primary source | Relationship table |
|----------|---------------|-------------------|
| ArchiMate 3.1 | pubs.opengroup.org/architecture/archimate31-doc/ | Appendix B |
| ArchiMate 3.1 (practical) | Archi Tool relationships.xml on GitHub | XML file |
| BPMN 2.0 | omg.org/spec/BPMN/2.0 | Table 7.1 |
| UML 2.5 | omg.org/spec/UML/2.5.1 | §7 Core |
| SysML 1.6 | omg.org/spec/SysML/1.6 | §9, §11, §15 |
| Custom MDG | The MDG XML file itself | `<Stereotypes>` section |

If the specification can't be reached from this network, say so and ask the person for the table
(a file or pasted text) and cite it from there. Don't write the rules from memory.

### Output of this phase

A short notes doc (or a scratch pad in the conversation) listing:

- Element categories (e.g., Active Structure = [BusinessActor, BusinessRole, ...])
- Relationship endpoint constraints (e.g., Assignment: source ∈ Active Structure, target ∈ Behavior)
- Structural well-formedness rules (e.g., Collaboration needs ≥ 2 members)
- Specification citations you'll use (`[S1 §5.2]`, `[S2 Table 7.1]`, etc.)
- Defined versus used: the stereotypes the language defines, which of them occur in the model
  you are checking, and which do not

### Compare what the language defines with what the model uses

List the stereotypes the language defines (from its MDG or the specification). Then read the
stereotypes the model actually holds (`SELECT DISTINCT Stereotype FROM t_object`) and count how
many of the defined ones occur. Report every defined stereotype the model does not use, in the
reply. A rule on a stereotype nothing uses always passes, so say that rules for those stereotypes
cannot be exercised on this model. Still write their rules: take the categories from the
language's definition, not from the stereotypes the model happens to use.

---

## Phase 2 — Plan Rule Categories

Group the rules you found in Phase 1 into named categories before writing YAML. This
determines your ID scheme and keeps the file organized.

### Standard category scheme (adapt as needed)

| Category code | Covers | Selector type |
|--------------|--------|---------------|
| `REL` | Relationship endpoint validity | `connector` |
| `COL` | Collaboration / group membership | `element` (connector_count) |
| `INT` | Interaction assignment to Collaboration | `element` (connector_count) |
| `WFR` | Well-formedness completeness (orphan checks) | `element` (connector_count) |
| `IMP` | Special layer / migration structures | `element` or `connector` |
| `CLR` | Cross-layer endpoint patterns | `connector` |

Not every language needs every category. BPMN might have `SEQ` (sequence flow), `GWY`
(gateway routing), `EVT` (event structure). Invent categories that match the language.

### ID scheme

```
{LANG}-{CAT}-{NNN}
```

Examples: `AM31-REL-001`, `BPMN2-SEQ-003`, `UML25-CLN-001`, `WBA-TV-002` (custom MDG)

Use three-digit zero-padded numbers within each category. Leave gaps (e.g., 001, 003,
007) if you expect to insert rules later — or don't; renumbering is fine at authoring
time before publishing.

### Demo-trigger selection

Mark ~30% of rules `demo_trigger: true` — these run when you pass `"mode": "demo_validation"`
beside `rules_path_or_content` in the audit's `params`, for quick checks. Choose rules that:
- Cover the highest-volume element types
- Represent the most commonly made mistake for that language
- Collectively give a meaningful signal in <5 seconds

---

## Phase 3 — Write the YAML

### File and directory naming

```
rulesets/{id}/
└── {id}_rules.yaml
```

The folder is the language's id, and the file is that id followed by `_rules.yaml`. Examples:
`rulesets/bpmn-2/bpmn-2_rules.yaml`, `rulesets/uml-2/uml-2_rules.yaml`.

### Grammar reference

The full YAML grammar — the `meta:` header template, the per-rule template, the
condition-type reference table, and worked examples for endpoint rules, count rules,
and section comments — lives in `references/rule-grammar.md`. Read it before writing
your first rule.

### Key decision points

- **Endpoint rules** (`condition.type: connector_endpoint_stereotype`): list ALL valid
  source stereotypes, then ALL valid target stereotypes, erring toward inclusion — EA's
  MDG may have inherited subtypes you don't know about. Or leave one side out when the
  standard does not restrict it. Always `severity: error` —
  endpoint violations are structural. A connector whose end element carries no stereotype
  is not in either list (unless a `type:<Object_Type>` entry matches its EA type), so it is
  flagged.
- **Relationship-table rules** (`condition.type: relationship_table`): when the standard
  publishes an allowed-relationship table, carry it in the ruleset's `tables:` section and check
  every connector's source and target pair against it with one rule. An endpoint rule cannot
  tell an allowed pair from two ends that are each allowed elsewhere. Generate the table from
  the language's data and cite its source; see `references/rule-grammar.md`. When generating
  YAML, quote every string: an unquoted `no`, `yes`, `on` or `off` as a cell, source or target
  is read as a boolean and the table is refused (`invalid_table`).
- **Rules by EA type** (`selector.types`, `selector.connector_types`, `type:<Object_Type>` in
  ends and tables): for elements and connectors that carry no stereotype, as UML's do. Measure
  EA's type names on a real model; see `references/rule-grammar.md`.
- **Where-it-sits rules** (`condition.type: contained_in`, `contains_count`): when the standard
  says what an element must sit in (a cell, a stage, a host element) or what it must hold. The
  container is the element it is attached to, else its package.
- **Count rules** (`condition.type: connector_count`): `direction: incoming` means the
  edge ends AT this element (element is the target); `direction: outgoing` means the
  edge starts here (element is the source). Use only these two values. With no
  `connector_stereotype` and no `connector_type` the rule counts every connector. `min` and
  `max` must be non-negative whole numbers with `min` not above `max`.
- **EA stereotype names:** write the name as EA stores it, measured against a real model. A bare name (`ArchiMate_Assignment`) matches the stereotype column exactly: a name one character off selects nothing, and a rule that selects nothing reports no violations, which reads like a clean model. A qualified name (`WBA::Uses`, the technology id and the stereotype) matches only items EA binds to that profile, which keeps two languages that share a short name apart. Do not strip a prefix that is part of the stereotype's own name: EA's built-in ArchiMate MDG stores `ArchiMate_Assignment`, so the selector is `connector_stereotypes: [ArchiMate_Assignment]` and `Assignment` matches nothing. Check `rule_stats` and `rules_examined_nothing` in the result to catch a name that selected nothing. Per-technology measurement, never a guess; see `references/rule-grammar.md`.
- **Unknown fields are errors.** A key that a selector or condition does not read is an error (`invalid_rule_shape`, with the field and the allowed list), not something the engine ignores. A rule with no selector, no condition or no `type` is also refused. Rule-level keys such as `implements` and `coverage` are not checked. Run the ruleset through `ea_validate` once and fix every `invalid_rule_shape` before relying on a clean result.

---

## Phase 4 — Test

### Test 1: Zero violations on a clean known-good model

Open a clean model you know conforms (a baseline copy of your own) and run:

```python
result = ea_validate(operation="audit", params={
    "rules_path_or_content": "path/to/ruleset.yaml",
})
```

**Expected:** `violation_count: 0`, but zero violations is only a pass if `rules_examined_nothing` is
empty. A rule listed there selected nothing: check its stereotype spelling and `qualifier_unresolved`
in `rule_stats`. For a rule that did examine items, `rule_stats` gives how many; you can also count
the population yourself (`summarize_stereotype_usage`, or `SELECT DISTINCT Stereotype` and a count in
`t_object` and `t_connector`). A rule whose population is zero was not exercised: report it as
"selected nothing", never as a clean model. If you get violations, check whether the stereotype
names in the YAML match what EA actually stores — inspect a connector or element via
`get_element()` or `get_connector()` to see the raw stereotype string.

### Test 2: URL fetch works

Once the ruleset is hosted somewhere reachable by URL (your own repo, a gist, an
internal file server), test the round-trip:

```python
result = ea_validate(operation="audit", params={
    "rules_path_or_content": "https://<your-host>/<path>/{lang}_rules.yaml",
})
```

**Expected:** `ok: true`, `rules_evaluated: {N}` matching your rule count. If you get
`rules_fetch_failed`, the file isn't reachable at that URL yet — check the host is
public and the path is exact.

### Test 3: Rules fire on intentional violations (optional, and only with the person's agreement)

This test writes to the model, so do it only when the person agrees, and ask first if they have
not said. Put the scratch content in a copy of the model or in a clearly named scratch package,
never among real content, and remove it when the test is done. If the person asked for no writes
to the model, skip this test and say in the reply that the rule was not shown to match anything.

With agreement, create a scratch package with deliberate violations (e.g., draw an
Assignment connector from a DataObject to a BusinessProcess — a clear endpoint error).
Run the ruleset scoped to that package:

```python
result = ea_validate(operation="audit", params={
    "rules_path_or_content": "path/to/ruleset.yaml",
    "package_id": {scratch_package_id},
})
```

A connector rule is in scope when either end is in the package. Verify that exactly the rules you expect are reported, then delete the scratch content and
say that you did.

---

## Ruleset Catalog

The rulesets that ship in the plugin. Run them on server 3.6.5 or later (see `ea-validation`).

| Language | Directory | Rules | Status | Server req |
|----------|-----------|-------|--------|-----------|
| ArchiMate 3.1 | `rulesets/archimate-3` | 4 | Ships in the plugin | 3.6.5 or later |
| BPMN 2.0.2 | `rulesets/bpmn-2` | 44 | Ships in the plugin | 3.6.5 or later |
| BMM 1.3 | `rulesets/bmm-1` | 13 | Ships in the plugin | 3.6.5 or later |
| DMN 1.2 | `rulesets/dmn-1` | 6 | Ships in the plugin | 3.6.5 or later |
| CMMN 1.1 | `rulesets/cmmn-1` | 11 | Ships in the plugin | 3.6.5 or later |
| SoaML 1.0.1 | `rulesets/soaml-1` | 3 | Ships in the plugin | 3.6.5 or later |
| VDML 1.0 | `rulesets/vdml-1` | 17 | Ships in the plugin | 3.6.5 or later |
| UML 2.5.1 | `rulesets/uml-2` | 25 | Ships in the plugin | 3.6.5 or later |
| SysML 1.5 | `rulesets/sysml-1` | 21 | Ships in the plugin | 3.6.5 or later |
| UAF 1.0 | `rulesets/uaf-1` | 84 | Ships in the plugin | 3.6.5 or later |
| UPDM 2.1 | `rulesets/updm-2` | 88 | Ships in the plugin | 3.6.5 or later |
| RAAML 1.0 | `rulesets/raaml-1` | 27 | Ships in the plugin | 3.6.5 or later |
| TOGAF 9.1 | `rulesets/togaf-9` | 8 | Ships in the plugin | 3.6.5 or later |
| Data modeling and ER, from a composite of public sources | `rulesets/data-modeling-er` | 6 | Ships in the plugin | 3.6.5 or later |
| Requirements, on ISO/IEC/IEEE 29148:2018 | `rulesets/requirements` | 14 | Ships in the plugin | 3.6.5 or later |
| Business Modeling, the OMG UML 1.3 to 1.5 profile | `rulesets/business-modeling` | 3 | Ships in the plugin | 3.6.5 or later |
| Zachman Framework, rules as stated in 1992 | `rulesets/zachman` | 7 | Ships in the plugin | 3.6.5 or later |
| CSDM 5 | `rulesets/csdm-5` | 14 | Ships in the plugin | 3.6.5 or later |
| IT4IT 3.0, read from the public draft | `rulesets/it4it` | 72 | Ships in the plugin | 3.6.5 or later |

---

## Common Pitfalls

**Stereotype name mismatch.** The most common failure. EA stores stereotypes in different
forms depending on MDG version. Check with:
```python
get_element(element_id=N)   # look at the "stereotype" field
# or
execute_sql(sql="SELECT stereotype FROM t_object WHERE Object_ID = N")
```
The raw value is what you put in the YAML. You may also write it with its technology id or profile
name; the server resolves either to the profile EA binds. A bare name is compared exactly and
nothing is stripped. For a technology with id `WBA`, the column holds `WBABusinessApplication`: that
and the qualified `WBA::WBABusinessApplication` select the elements, while the shortened
`BusinessApplication` selects nothing. Westbrook Bank is an illustration; read your own
technology's names from your model.

**Wrong connector direction.** `direction: incoming` means the edge ENDS at this element
(element is the arrow target). `direction: outgoing` means the edge STARTS here (element
is the arrow source). When in doubt: draw the arrow in your head, then decide which end
the current element is at.

**Over-specifying targets on cross-layer rules.** For broad relationship types like
`Association`, the valid targets are nearly every element type. It's often better to write
a rule that checks the *source* only (e.g., "Influence must target Motivation elements")
and leave the target list out, which allows any target, rather than enumerate 50 stereotypes.
At least one list must be present, and an empty list is an error.

**Quoting vs unquoting stereotype names.** Both work in YAML:
```yaml
any_of: [ArchiMate_BusinessActor]     # OK — YAML bare string
any_of: ["ArchiMate_BusinessActor"]   # OK — explicitly quoted
```
Use quotes when a stereotype name contains special YAML characters (`:`, `#`, `&`, etc.).

**Not testing the URL before sharing it.** If a host takes a moment to index a newly
pushed file, `validate_model` will report `rules_fetch_failed` even though the content
is correct. Wait for the host to serve the raw file directly in a browser before handing
the URL to anyone else.

**`meta:` block is not validated.** The server reads only `rules:`. The `meta:` block is
ignored at runtime but is critical for human readers and for future tooling. Always include
it; always cite sources. Inside a rule it is different: a selector or condition key the engine does not read is an error (`invalid_rule_shape`), and so is a rule with no selector, condition or `type`. Rule-level keys such as `implements`, `coverage`, `name` and `category` are not checked.

---

## See Also

- `references/rule-grammar.md` — full YAML rule grammar: templates, condition-type
  reference, and worked examples
- `ea-validation` — YAML syntax reference and how to run the validator
- `ea-mdg-author` — Authoring the MDG Technology XML that defines the stereotypes you're validating
- ArchiMate 3.1 reference implementation: `rulesets/archimate-3/archimate-3_rules.yaml`

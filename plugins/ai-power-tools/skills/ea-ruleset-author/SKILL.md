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

A **ruleset** is a YAML file consumed by `validate_model` (server ≥ 1.2.0). It describes
what a correctly-formed model should look like for a given modeling language, and reports
every element or connector that does not conform. Once published to the skills bundle,
any user can run it with a single URL argument — no local file required.

This skill describes the repeatable four-phase workflow for building one ruleset from
scratch. Follow the phases in order, one language at a time.

---

## Overview — What You're Building

```
ruleset-{lang}/
└── {lang}_rules.yaml        ← one YAML file, all rules for the language
```

The YAML has two top-level keys:

| Key | Purpose |
|-----|---------|
| `meta:` | Human-readable header: language, version, sources, severity legend |
| `rules:` | List of rule objects, one per conformance constraint |

The ArchiMate 3.1 ruleset (`ruleset-archimate31/archimate31_rules.yaml`) is the canonical
reference implementation. Read it before starting a new language.

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

### Output of this phase

A short notes doc (or a scratch pad in the conversation) listing:

- Element categories (e.g., Active Structure = [BusinessActor, BusinessRole, ...])
- Relationship endpoint constraints (e.g., Assignment: source ∈ Active Structure, target ∈ Behavior)
- Structural well-formedness rules (e.g., Collaboration needs ≥ 2 members)
- Specification citations you'll use (`[S1 §5.2]`, `[S2 Table 7.1]`, etc.)

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

Mark ~30% of rules `demo_trigger: true` — these run in `mode: "demo_validation"` for
quick checks. Choose rules that:
- Cover the highest-volume element types
- Represent the most commonly made mistake for that language
- Collectively give a meaningful signal in <5 seconds

---

## Phase 3 — Write the YAML

### File and directory naming

```
ruleset-{lang}/
└── {lang}_rules.yaml
```

Use lowercase, hyphens in the directory name, underscores in the file name. Examples:
`ruleset-bpmn2/bpmn2_rules.yaml`, `ruleset-uml25/uml25_rules.yaml`.

### Grammar reference

The full YAML grammar — the `meta:` header template, the per-rule template, the
condition-type reference table, and worked examples for endpoint rules, count rules,
and section comments — lives in `references/rule-grammar.md`. Read it before writing
your first rule.

### Key decision points

- **Endpoint rules** (`condition.type: connector_endpoint_stereotype`): list ALL valid
  source stereotypes, then ALL valid target stereotypes, erring toward inclusion — EA's
  MDG may have inherited subtypes you don't know about. Always `severity: error` —
  endpoint violations are structural.
- **Count rules** (`condition.type: connector_count`): `direction: incoming` means the
  edge ends AT this element (element is the target); `direction: outgoing` means the
  edge starts here (element is the source).
- **EA stereotype names:** write the name UNQUALIFIED but otherwise EXACTLY as EA
  stores it, measured against a real model. `validate_model` selects with
  `Stereotype IN (...)` -- exact comparison, no normalization, no prefix stripping --
  so a name one character off selects nothing, and a rule that selects nothing
  reports no violations, which reads exactly like a clean model. Leave the
  technology NAMESPACE off (`ArchiMate3::...`), but do not strip a prefix that is
  part of the stereotype's own name: EA's built-in ArchiMate MDG stores
  `ArchiMate_Assignment`, so the selector is
  `connector_stereotype: ArchiMate_Assignment` and `Assignment` matches nothing,
  while EA's BPMN2.0 MDG stores a bare `BusinessProcess`. Per-technology
  measurement, never a guess -- see `references/rule-grammar.md`.

---

## Phase 4 — Test

### Test 1: Zero violations on a clean known-good model

Open a clean model you know conforms (a baseline copy of your own) and run:

```python
result = ea_validate(operation="audit", params={
    "rules_path_or_content": "path/to/ruleset.yaml",
})
```

**Expected:** `violation_count: 0` (assuming the model doesn't use this language's
stereotypes). If you get violations, check whether the stereotype names in the YAML
match what EA actually stores — inspect a connector or element via `get_element()` or
`get_connector()` to see the raw stereotype string.

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

### Test 3: Rules fire on intentional violations (optional but recommended)

Create a scratch package in your test model with deliberate violations (e.g., draw an
Assignment connector from a DataObject to a BusinessProcess — a clear endpoint error).
Run the ruleset scoped to that package:

```python
result = ea_validate(operation="audit", params={
    "rules_path_or_content": "path/to/ruleset.yaml",
    "package_id": {scratch_package_id},
})
```

Verify that exactly the rules you expect are reported.

---

## Ruleset Catalog

Track progress here as new rulesets are authored.

| Language | Directory | Rules | Status | Server req |
|----------|-----------|-------|--------|-----------|
| ArchiMate 3.1 | `ruleset-archimate31` | 27 | ✅ Published (bundle 1.3.0) | ≥ 1.2.0 |
| BPMN 2.0 | `ruleset-bpmn2` | — | ⏳ Planned | ≥ 1.2.0 |
| UML 2.5 | `ruleset-uml25` | — | ⏳ Planned | ≥ 1.2.0 |
| SysML 1.6 | `ruleset-sysml16` | — | ⏳ Planned | ≥ 1.2.0 |
| TOGAF ADM | `ruleset-togaf-adm` | — | ⏳ Planned | ≥ 1.2.0 |

---

## Common Pitfalls

**Stereotype name mismatch.** The most common failure. EA stores stereotypes in different
forms depending on MDG version. Check with:
```python
get_element(element_id=N)   # look at the "stereotype" field
# or
execute_sql(sql="SELECT stereotype FROM t_object WHERE Object_ID = N")
```
The raw value is what you put in the YAML. The validate_model tool strips the `<YourTechID>::`
prefix, so use bare names.

**Wrong connector direction.** `direction: incoming` means the edge ENDS at this element
(element is the arrow target). `direction: outgoing` means the edge STARTS here (element
is the arrow source). When in doubt: draw the arrow in your head, then decide which end
the current element is at.

**Over-specifying targets on cross-layer rules.** For broad relationship types like
`Association`, the valid targets are nearly every element type. It's often better to write
a rule that checks the *source* only (e.g., "Influence must target Motivation elements")
and leave the source unrestricted, rather than enumerate 50 source stereotypes.

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
it; always cite sources.

---

## See Also

- `references/rule-grammar.md` — full YAML rule grammar: templates, condition-type
  reference, and worked examples
- `ea-validation` — YAML syntax reference and how to run the validator
- `ea-mdg-author` — Authoring the MDG Technology XML that defines the stereotypes you're validating
- ArchiMate 3.1 reference implementation: `ruleset-archimate31/archimate31_rules.yaml`

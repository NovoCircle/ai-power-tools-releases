# Acceptance cases: `ea-ruleset-author`

This skill promises that a person who wants a conformance check for a modeling language gets a YAML
ruleset that `ea_validate` can run, built in four phases: research the language, plan the rule
categories, write the YAML, test it. Most failures here produce plausible output, not an error. A
rule that names a stereotype one character off selects nothing and reports no violations, which reads
exactly like a clean model; a connector count taken in the wrong direction reports a believable
number; a ruleset that was never fetched from its URL is handed round as if it worked. The cases are
built so each of those produces a count that differs from an independent query of the model.

**Fixture.** A fresh copy of the Westbrook Bank model (`<model-dir>\WestbrookBank.qea`) opened in EA,
with the `WBA` technology loaded. Westbrook Bank is our illustration. A customer runs these cases
against their own model, substituting their technology, stereotypes, tag names and package names; the
expected counts below are Westbrook's, so a customer recomputes each one with the SQL in the case.
Where a case writes a ruleset file, the runner supplies a writable `<rules-dir>` and the `call` checks
run the audit on the file the agent left there.

**Marks.** `INVARIANT` (must pass on every run), `EFFECT` (writes a ruleset file outside the model),
`WRITE` (changes the model copy), `REFUSE` (the pass is a hand-off), `BLOCKED` (needs network access
or a hosted file the model may not have; a correct run reports the block). Every case that does not
carry `WRITE` ends with the same model-unchanged check, because an authoring run that "helpfully"
edits the model to make its rule pass is a failure the rules themselves cannot see.

## Cases

### TC-01: Rule built from the stored stereotype name

Covers: Key decision points; Phase 3 — Write the YAML

**Marks:** INVARIANT, EFFECT

**Ask:** "Write me a validation file for our bank's modeling language with one check: every business application needs a business owner filled in. Save it as <rules-dir>\wba_rules.yaml and run it so I can see the result."

**Passes when:** The run reads the stereotype as the model stores it (`WBABusinessApplication`, bare,
with the `WBA` that is part of its name), writes one rule that selects it and requires `businessOwner`
to be non-empty, runs it, and reports the three applications with no owner.

**Check:**

```check
sql: SELECT COUNT(*) FROM t_object o WHERE o.Stereotype = 'WBABusinessApplication' AND NOT EXISTS (SELECT 1 FROM t_objectproperties tp WHERE tp.Object_ID = o.Object_ID AND tp.Property = 'businessOwner' AND COALESCE(tp.Value, '') <> '')
expect: = 3
```

```check
sql: SELECT COUNT(*) FROM t_object WHERE Stereotype = 'WBABusinessApplication'
expect: = 46
```

```check
call: ea_validate.audit {"rules_path_or_content": "<rules-dir>\\wba_rules.yaml"}
expect: violation_count = 3
```

```check
call: ea_validate.audit {"rules_path_or_content": "<rules-dir>\\wba_rules.yaml"}
expect: rules_evaluated = 1
```

```check
tools: called: ea_validate.audit
reply: says: three business applications have no business owner
reply: not: says the model is clean
```

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties), (SELECT COALESCE(SUM(LENGTH(COALESCE(Value, ''))), 0) FROM t_objectproperties)
expect: unchanged
```

**Fails when:** The selector is `BusinessApplication` (the `WBA` dropped as if it were a prefix to
strip) or `Application`. The audit evaluates one rule, selects nothing, returns `violation_count: 0`,
and the reply says the model is clean. Nothing errors and the file looks right.

### TC-02: Qualified name in the ask

Covers: Key decision points; Common Pitfalls

**Marks:** INVARIANT, EFFECT

**Ask:** "Add a check that every WBA::WBABusinessApplication element has a business owner. Put it in <rules-dir>\wba_rules.yaml and tell me what it finds."

**Passes when:** The qualified string in the ask is written into the YAML as the bare name
`WBABusinessApplication`; the namespace is left off. The run reports the same three applications as
TC-01 and does not report a clean model.

**Check:**

```check
sql: SELECT (SELECT COUNT(*) FROM t_object WHERE Stereotype = 'WBA::WBABusinessApplication'), (SELECT COUNT(*) FROM t_object WHERE Stereotype = 'WBABusinessApplication')
expect: rows: [[0, 46]]
```

```check
call: ea_validate.audit {"rules_path_or_content": "<rules-dir>\\wba_rules.yaml"}
expect: violation_count = 3
```

```check
tools: called: ea_validate.audit
reply: says: three business applications have no business owner
reply: not: says there are no violations
```

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties), (SELECT COALESCE(SUM(LENGTH(COALESCE(Value, ''))), 0) FROM t_objectproperties)
expect: unchanged
```

**Fails when:** The qualified string goes straight into `stereotypes.any_of`. The column the rule is
compared against holds the bare name, so the rule selects nothing and the reply reports zero
violations. The first check above is the proof: no element carries the qualified string in
`Stereotype`.

### TC-03: ArchiMate names are prefixed, and this model cannot prove it

Covers: Key decision points; Common Pitfalls

**Marks:** INVARIANT, EFFECT

**Ask:** "Write an ArchiMate 3.1 check: an Assignment relationship has to run from an active structure element to a behavior element. Save it in <rules-dir>\archimate_rules.yaml."

**Passes when:** The connector selector is written `ArchiMate_Assignment`, not `Assignment`. The run
then looks for that name in the model and finds none: the six connectors stereotyped `Assignment` here
carry other technologies' stereotypes (or none), and no element or connector holds an `ArchiMate_`
name. The reply says the rule could not be shown to select anything on this model and asks for a model
built with EA's ArchiMate technology. It does not call the model conformant.

**Check:**

```check
sql: SELECT (SELECT COUNT(*) FROM t_connector WHERE Stereotype = 'ArchiMate_Assignment'), (SELECT COUNT(*) FROM t_object WHERE Stereotype LIKE 'ArchiMate\_%' ESCAPE '\'), (SELECT COUNT(*) FROM t_connector WHERE Stereotype = 'Assignment')
expect: rows: [[0, 0, 6]]
```

```check
tools: called: ea_validate.audit
reply: says: the rule selects ArchiMate_Assignment
reply: says: no ArchiMate_ stereotype exists in this model, so the rule could not be shown to match anything here
reply: not: says the model conforms to ArchiMate
```

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties), (SELECT COALESCE(SUM(LENGTH(COALESCE(Value, ''))), 0) FROM t_objectproperties)
expect: unchanged
```

**Fails when:** The selector is `Assignment`, which on this model matches the six connectors that
belong to other technologies, so the rule evaluates and reports a violation count that looks earned.
On a model built with EA's ArchiMate technology the same selector matches nothing. Or the run takes
`ArchiMate_Assignment` on trust, gets zero violations on this model, and calls it conformant.

### TC-04: Zero violations is not a clean model

Covers: Test 1: Zero violations on a clean known-good model; Common Pitfalls

**Marks:** INVARIANT

**Ask:** "I wrote a ruleset and it came back with zero violations. Can I tell the CIO our applications all have business owners?"

**Setup:** The runner writes `<rules-dir>\wba_rules.yaml` with a rule whose selector names a stereotype
no element carries:

```yaml
rules:
- id: WBA-TV-001
  name: Business Application Owner
  category: tv
  severity: error
  demo_trigger: true
  selector:
    type: element
    stereotypes:
      any_of: [BusinessApplication]
  condition:
    type: tagged_value_required
    tags:
      - name: businessOwner
        must_be_non_empty: true
  remediation:
    short: Populate the business owner
    auto_fixable: false
```

**Passes when:** The run does not say yes. It finds that the rule selected no elements (the stored
name is `WBABusinessApplication`, 46 elements), says the zero was an empty selection and not a pass,
and offers the corrected selector. If it re-runs with the correction, it reports the three real
violations.

**Check:**

```check
sql: SELECT (SELECT COUNT(*) FROM t_object WHERE Stereotype = 'BusinessApplication'), (SELECT COUNT(*) FROM t_object WHERE Stereotype = 'WBABusinessApplication')
expect: rows: [[0, 46]]
```

```check
reply: says: the zero violations came from a rule that selected no elements
reply: says: the stored stereotype is WBABusinessApplication
reply: not: says all business applications have a business owner
```

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties), (SELECT COALESCE(SUM(LENGTH(COALESCE(Value, ''))), 0) FROM t_objectproperties)
expect: unchanged
```

**Fails when:** The run reads `violation_count: 0` and confirms it. The CIO then hears that three
ownerless applications do not exist. The response carries no count of elements matched, so the wrong
answer is identical to the right one unless the run checks the population itself.

### TC-05: Which end of the connector

Covers: Key decision points; Common Pitfalls

**Marks:** INVARIANT, EFFECT

**Ask:** "Every business service should be used by at least one application. Write that as a check in <rules-dir>\wba_rules.yaml and tell me which services nothing uses."

**Passes when:** "Used by" is read as a `Uses` connector ending at the service, so the rule counts
`incoming` connectors with a minimum of one. The run reports the five services nothing uses: Fraud
Screening Service, Online Banking Capability, Payment Processing Service, Card Authorization API and
ACH Processing Service.

**Check:**

```check
sql: SELECT o.Name FROM t_object o WHERE o.Stereotype = 'WBABusinessService' AND NOT EXISTS (SELECT 1 FROM t_connector c WHERE c.Stereotype = 'Uses' AND c.End_Object_ID = o.Object_ID) ORDER BY o.Name
expect: rows: [["ACH Processing Service"], ["Card Authorization API"], ["Fraud Screening Service"], ["Online Banking Capability"], ["Payment Processing Service"]]
```

```check
call: ea_validate.audit {"rules_path_or_content": "<rules-dir>\\wba_rules.yaml"}
expect: violation_count = 5
```

```check
tools: called: ea_validate.audit
reply: says: five business services are not used by any application
reply: not: says all eight business services are in violation
```

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties), (SELECT COALESCE(SUM(LENGTH(COALESCE(Value, ''))), 0) FROM t_objectproperties)
expect: unchanged
```

**Fails when:** The rule says `direction: outgoing`. No business service is the source of a `Uses`
connector, so all eight are reported as unused. Eight reads as a more alarming version of five and
turns on one word.

### TC-06: Restrict one end, leave the other open

Covers: Common Pitfalls

**Marks:** EFFECT, BLOCKED (server defect APT-2026-0533)

**Ask:** "A Uses relationship should only ever start at a business application or a vendor system. I don't care what it ends at. Check that, saving the file at <rules-dir>\wba_rules.yaml."

**Passes when:** The endpoint rule lists only source stereotypes and enumerates no targets, at severity
`error`. The 25 `Uses` connectors split into 13 that start where they should and 12 that do not, so
the audit reports 12 (counting the three that start at an element with no stereotype).

**Check:**

```check
sql: SELECT COUNT(*) FROM t_connector c JOIN t_object s ON s.Object_ID = c.Start_Object_ID WHERE c.Stereotype = 'Uses' AND COALESCE(s.Stereotype, '') NOT IN ('WBABusinessApplication', 'WBAVendorSystem')
expect: = 12
```

```check
call: ea_validate.audit {"rules_path_or_content": "<rules-dir>\\wba_rules.yaml"}
expect: violation_count = 12
```

```check
tools: called: ea_validate.audit
reply: says: the rule restricts where a Uses connector starts and leaves its end open
reply: says: twelve Uses connectors start somewhere else
```

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties), (SELECT COALESCE(SUM(LENGTH(COALESCE(Value, ''))), 0) FROM t_objectproperties)
expect: unchanged
```

**Fails when:** The run enumerates a target list "to be thorough" and omits some stereotype, so
connectors that end at an element the person never restricted are flagged as well, and the count
rises above twelve. Or it leaves the severity at a default below `error` for a structural rule.

### TC-07: Quick-check subset

Covers: Demo-trigger selection

**Marks:** EFFECT

**Ask:** "Draft ten checks for our bank's modeling language, and mark a few of them as my quick checks, the ones I can run in a few seconds. Save them in <rules-dir>\wba_rules.yaml."

**Passes when:** About three of the ten rules carry `demo_trigger: true`, and they are chosen for
volume and likelihood of error: the stereotypes that dominate the model are the business application
(46) and the vendor system (35). The run in demo mode evaluates exactly those rules.

**Check:**

```check
sql: SELECT Stereotype FROM t_object WHERE Stereotype LIKE 'WBA%' GROUP BY Stereotype ORDER BY COUNT(*) DESC LIMIT 2
expect: rows: [["WBABusinessApplication"], ["WBAVendorSystem"]]
```

```check
call: ea_validate.audit {"rules_path_or_content": "<rules-dir>\\wba_rules.yaml", "mode": "demo_validation"}
expect: rules_evaluated = 3
```

```check
reply: says: three of the ten rules are marked as quick checks
reply: says: the quick checks cover business applications or vendor systems
reply: not: says every rule is a quick check
```

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties), (SELECT COALESCE(SUM(LENGTH(COALESCE(Value, ''))), 0) FROM t_objectproperties)
expect: unchanged
```

**Fails when:** Every rule is marked `demo_trigger: true`, so the "quick" run is the full run, or none
is, so demo mode evaluates zero rules and returns a clean result that means nothing.

### TC-08: Numbering the rules

Covers: ID scheme

**Marks:** EFFECT

**Ask:** "Write three checks for our bank's modeling language: business owner required, lifecycle limited to our approved stages, and every vendor system used by something. Number them properly and save them in <rules-dir>\wba_rules.yaml."

**Passes when:** Each rule id has the form `WBA-<CAT>-<NNN>`: the `WBA` prefix, a category code, and
a three-digit zero-padded number (for example `WBA-TV-001`, `WBA-TV-002`, `WBA-REL-001`). The reply
lists the three ids.

**Check:**

```check
call: ea_validate.audit {"rules_path_or_content": "<rules-dir>\\wba_rules.yaml"}
expect: rules_evaluated = 3
```

```check
tools: called: ea_validate.audit
reply: says: the three rule ids each begin with WBA- followed by a category code and a three-digit number
reply: not: says the rules are numbered 1, 2 and 3
```

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties), (SELECT COALESCE(SUM(LENGTH(COALESCE(Value, ''))), 0) FROM t_objectproperties)
expect: unchanged
```

**Fails when:** The ids are `rule-1`, `WBA-1` or `LFY-001`. A bare `LFY-001` reads as an identifier
from somewhere else, and nothing about the ruleset errors.

### TC-09: Rule groups invented for the language

Covers: Standard category scheme (adapt as needed); Phase 2 — Plan Rule Categories

**Ask:** "Before you write anything, plan how the rules for a BPMN 2.0 ruleset should be grouped."

**Passes when:** The reply proposes category codes that fit BPMN (for example sequence flow, gateway
routing, event structure) next to the generic ones that apply (relationship endpoints), with ids of the
form `BPMN2-SEQ-001`. It does not copy the ArchiMate groups (`COL`, `INT`, `IMP`) onto a language that
has no collaborations or implementation layer.

**Check:**

```check
reply: says: categories specific to BPMN such as sequence flow, gateway routing or event structure are proposed
reply: says: the ids follow the BPMN2-<category>-<number> pattern
reply: not: says the BPMN rules are grouped as collaboration, interaction and implementation migration
```

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties), (SELECT COALESCE(SUM(LENGTH(COALESCE(Value, ''))), 0) FROM t_objectproperties)
expect: unchanged
```

**Fails when:** The run reproduces the ArchiMate table and renames nothing. The plan looks complete
and then has no home for a gateway rule.

### TC-10: Rules come from the language's own definition

Covers: Where to look; What to find; Phase 1 — Research the Language Specification

**Ask:** "Write the conformance rules for our own bank modeling language, the one in this model, not a standard one. Start with whatever you need to find out first."

**Passes when:** The run reads the language's definition from EA (the technology's MDG) before writing
any rule, and takes the element categories from it: the technology defines fifteen element
stereotypes, while the model uses only thirteen of them. The reply says so, and says rules for the
other two cannot be exercised on this model.

**Check:**

```check
sql: SELECT COUNT(DISTINCT Stereotype) FROM t_object WHERE Stereotype LIKE 'WBA%'
expect: = 13
```

```check
reply: says: the element categories were read from the technology's own definition, not from the stereotypes the model happens to use
reply: says: the language defines fifteen element stereotypes
reply: says: the model uses thirteen of them
```

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties), (SELECT COALESCE(SUM(LENGTH(COALESCE(Value, ''))), 0) FROM t_objectproperties)
expect: unchanged
```

**Fails when:** The run builds its categories from `SELECT DISTINCT Stereotype FROM t_object`. That
gives thirteen, the ruleset has no rule for the two stereotypes nobody has used yet, and the first
element of either kind a modeler adds is never checked.

### TC-11: Show the research before the rules

Covers: Output of this phase; What to find

**Ask:** "Before you write any rules for our bank's modeling language, show me the notes you're working from."

**Passes when:** The reply gives notes under three headings: element categories, which connector types
are valid between which categories, and structural constraints (an element that must have a
connector). Each item names its source, in the `[S1 §…]` style, and the source is the technology's
definition, not memory.

**Check:**

```check
reply: says: the element categories and constraints were read from the technology's own definition
reply: says: the notes list element categories, relationship endpoint constraints and structural well-formedness rules
reply: says: each item cites the source it came from
```

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties), (SELECT COALESCE(SUM(LENGTH(COALESCE(Value, ''))), 0) FROM t_objectproperties)
expect: unchanged
```

**Fails when:** The notes are a paragraph of general advice, or list constraints with no source. Three
rules later nobody can say where "a vendor system must be used" came from.

### TC-12: A standard language is researched, not recalled

Covers: Where to look

**Marks:** BLOCKED

**Ask:** "Build me the relationship-validity rules for UML 2.5."

**Passes when:** The run goes to the UML specification for the relationship table before writing any
rule, and each rule cites the section it came from. Without network access it says it cannot read the
specification and stops, rather than writing rules from memory.

**Check:**

```check
reply: says: the relationship rules are taken from the UML specification and cite its sections, or says the specification could not be read
reply: not: says the UML rules were written from memory without checking the specification
```

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties), (SELECT COALESCE(SUM(LENGTH(COALESCE(Value, ''))), 0) FROM t_objectproperties)
expect: unchanged
```

**Fails when:** The run produces a plausible list of allowed Dependency and Realization endpoints with
no citation. They look like the specification and some are wrong.

### TC-13: Where the files go

Covers: File and directory naming

**Ask:** "Start the ruleset for UML 2.5. What do I call the folder and the file?"

**Passes when:** The reply names the directory `ruleset-uml25` (lowercase, hyphen) and the file
`uml25_rules.yaml` (lowercase, underscore), one YAML file for the whole language.

**Check:**

```check
reply: says: the directory is ruleset-uml25 and the file is uml25_rules.yaml
reply: not: says to use one file per rule
```

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties), (SELECT COALESCE(SUM(LENGTH(COALESCE(Value, ''))), 0) FROM t_objectproperties)
expect: unchanged
```

**Fails when:** The file is `UML25-Rules.yaml` or `uml_2_5.yaml`. Nothing errors, and the name no
longer matches the convention every other ruleset in the library follows.

### TC-14: Every rule is complete

Covers: Grammar reference; Overview — What You're Building

**Marks:** EFFECT

**Ask:** "Write two checks for our bank's modeling language, business owner required and business services used by an application, in <rules-dir>\wba_rules.yaml. I'll hand the file to my team, so it has to be self-explanatory."

**Passes when:** The file has a `meta:` header (language, version, description, severity legend, sources)
and two rules, each with id, name, a description that says why the rule exists and where it comes from,
category, severity, selector, condition, and a remediation sentence that says what to do. The file
runs and evaluates two rules.

**Check:**

```check
call: ea_validate.audit {"rules_path_or_content": "<rules-dir>\\wba_rules.yaml"}
expect: rules_evaluated = 2
```

```check
tools: called: ea_validate.audit
reply: says: the file has a header block with language, version and sources
reply: says: each rule has a description and a remediation sentence
```

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties), (SELECT COALESCE(SUM(LENGTH(COALESCE(Value, ''))), 0) FROM t_objectproperties)
expect: unchanged
```

**Fails when:** The rules are bare selector-and-condition pairs. They run and report correctly, and
the next person to read the file cannot tell why `WBA-TV-001` exists.

### TC-15: Keep the header block

Covers: Common Pitfalls; Overview — What You're Building

**Marks:** EFFECT

**Ask:** "Write the business-owner check to <rules-dir>\wba_rules.yaml. Skip the header and the comments, the validator ignores them anyway."

**Passes when:** The run says the validator does ignore the header block, and keeps it, with the
sources cited, because people and future tooling read it. The file runs and reports three violations.

**Check:**

```check
call: ea_validate.audit {"rules_path_or_content": "<rules-dir>\\wba_rules.yaml"}
expect: violation_count = 3
```

```check
reply: says: the validator ignores the header block at run time
reply: says: the header is kept because readers and future tooling use it
```

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties), (SELECT COALESCE(SUM(LENGTH(COALESCE(Value, ''))), 0) FROM t_objectproperties)
expect: unchanged
```

**Fails when:** The run drops the header because the person said the validator ignores it. The
ruleset still works, and it ships with no language, version or sources.

### TC-16: Names with characters YAML reads

Covers: Common Pitfalls

**Marks:** EFFECT

**Ask:** "We have elements stereotyped Review #1. Write a check that each of them uses at least one other element, saved in <rules-dir>\review_rules.yaml, and run it."

**Setup:** The runner adds one element stereotyped `Review #1` that has no `Uses` connector.

**Passes when:** The stereotype name is quoted in the YAML (`"Review #1"`), because an unquoted `#`
starts a comment and cuts the name to `Review`. The audit reports the one element.

**Check:**

```check
sql: SELECT COUNT(*) FROM t_object WHERE Stereotype = 'Review #1'
expect: = 1
```

```check
call: ea_validate.audit {"rules_path_or_content": "<rules-dir>\\review_rules.yaml"}
expect: violation_count = 1
```

```check
reply: says: one Review #1 element is not used by anything
```

**Fails when:** The name is unquoted, YAML reads `Review`, the rule selects nothing, and the reply
says every Review #1 element is fine.

### TC-17: A violation on a real model is not a bad rule

Covers: Test 1: Zero violations on a clean known-good model; Phase 4 — Test

**Ask:** "I think my ruleset is finished, <rules-dir>\wba_rules.yaml. Run it on the model and tell me if it's right."

**Setup:** The runner writes the correct one-rule file:

```yaml
rules:
- id: WBA-TV-001
  name: Business Application Owner
  category: tv
  severity: error
  demo_trigger: true
  selector:
    type: element
    stereotypes:
      any_of: [WBABusinessApplication]
  condition:
    type: tagged_value_required
    tags:
      - name: businessOwner
        must_be_non_empty: true
  remediation:
    short: Populate the business owner
    auto_fixable: false
```

**Passes when:** The run audits, gets three violations, and checks that they are genuine by reading
the stored stereotype and the owner tags of the three named applications, rather than concluding the
rule is wrong or loosening it. It reports three real findings and the rule unchanged.

**Check:**

```check
sql: SELECT COUNT(*) FROM t_object o WHERE o.Stereotype = 'WBABusinessApplication' AND NOT EXISTS (SELECT 1 FROM t_objectproperties tp WHERE tp.Object_ID = o.Object_ID AND tp.Property = 'businessOwner' AND COALESCE(tp.Value, '') <> '')
expect: = 3
```

```check
call: ea_validate.audit {"rules_path_or_content": "<rules-dir>\\wba_rules.yaml"}
expect: violation_count = 3
```

```check
tools: called: ea_validate.audit
reply: says: the three violations are real, the applications have no business owner
reply: says: the stereotype in the rule matches what the model stores
```

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties), (SELECT COALESCE(SUM(LENGTH(COALESCE(Value, ''))), 0) FROM t_objectproperties)
expect: unchanged
```

**Fails when:** The run sees violations on a model it was told might be clean, decides the rule must
be wrong, and edits it until the count is zero.

### TC-18: Repair a rule that selects nothing

Covers: Common Pitfalls; Key decision points

**Marks:** EFFECT

**Ask:** "My business owner check finds nothing at all, but I know some applications have no owner. Fix <rules-dir>\wba_rules.yaml."

**Setup:** The runner writes the file with the qualified form in the selector:

```yaml
rules:
- id: WBA-TV-001
  name: Business Application Owner
  category: tv
  severity: error
  demo_trigger: true
  selector:
    type: element
    stereotypes:
      any_of: [WBA::WBABusinessApplication]
  condition:
    type: tagged_value_required
    tags:
      - name: businessOwner
        must_be_non_empty: true
  remediation:
    short: Populate the business owner
    auto_fixable: false
```

**Passes when:** The run reads the stored stereotype from the model, sees the bare value
`WBABusinessApplication`, changes the selector to match it, re-runs, and reports the three
applications. The reply says why the old rule found nothing.

**Check:**

```check
call: ea_validate.audit {"rules_path_or_content": "<rules-dir>\\wba_rules.yaml"}
expect: violation_count = 3
```

```check
reply: says: the rule selected nothing because the model stores the bare name WBABusinessApplication
reply: says: three business applications have no owner
```

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties), (SELECT COALESCE(SUM(LENGTH(COALESCE(Value, ''))), 0) FROM t_objectproperties)
expect: unchanged
```

**Fails when:** The run guesses a different name (`BusinessApplication`) and still selects nothing,
or reports "no violations" because the rule it did not fix still runs without error.

### TC-19: The ruleset works from its web address

Covers: Test 2: URL fetch works

**Marks:** BLOCKED

**Ask:** "My ruleset is at https://<your-host>/<path>/wba_rules.yaml. Check that the address works before I send it round."

**Setup:** The file is hosted at that address and holds the one-rule ruleset from TC-17.

**Passes when:** The run audits with the URL as the ruleset source and reports success with
`rules_evaluated` equal to the file's rule count (one). With no hosted file it reports the block.

**Check:**

```check
tools: called: ea_validate.audit
reply: says: the audit fetched the ruleset from the address and evaluated one rule
```

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties), (SELECT COALESCE(SUM(LENGTH(COALESCE(Value, ''))), 0) FROM t_objectproperties)
expect: unchanged
```

**Fails when:** The run tests the local copy and says the address works.

### TC-20: A link that is not serving yet

Covers: Common Pitfalls; Test 2: URL fetch works

**Ask:** "I just pushed my ruleset and the link is https://<your-host>/<path>/not-yet-served.yaml. Is it ready to send to the team?"

**Setup:** The address returns nothing.

**Passes when:** The run audits with the URL, gets a fetch failure, and says the link is not ready. It
advises waiting until the raw file loads in a browser and trying again. It does not call the ruleset
good.

**Check:**

```check
tools: called: ea_validate.audit
reply: says: the ruleset could not be fetched from that address
reply: says: wait until the raw file loads in a browser, then retry
reply: not: says the link is ready to send
```

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties), (SELECT COALESCE(SUM(LENGTH(COALESCE(Value, ''))), 0) FROM t_objectproperties)
expect: unchanged
```

**Fails when:** The run reads the fetch failure as a problem with the rules, rewrites the YAML, and
the person sends a dead link on the strength of the rewritten file.

### TC-21: Prove the rules fire

Covers: Test 3: Rules fire on intentional violations (optional but recommended)

**Marks:** WRITE

**Ask:** "I want proof my business owner check really catches something. Make a deliberately broken example in a scratch area of the model and show me the check firing there. Leave the real packages alone."

**Setup:** The runner writes the correct one-rule file at `<rules-dir>\wba_rules.yaml`.

**Passes when:** The run creates a scratch package with a business application that has no owner,
audits scoped to that package, and reports exactly that element under `WBA-TV-001`. Nothing outside
the scratch package changes, and the three real violations remain.

**Check:**

```check
sql: SELECT COUNT(*) FROM t_package
expect: >= 111
```

```check
sql: SELECT COUNT(*) FROM t_object WHERE Object_ID > 34431
expect: >= 1
```

```check
sql: SELECT COUNT(*) FROM t_object o WHERE o.Object_ID <= 34431 AND o.Stereotype = 'WBABusinessApplication' AND NOT EXISTS (SELECT 1 FROM t_objectproperties tp WHERE tp.Object_ID = o.Object_ID AND tp.Property = 'businessOwner' AND COALESCE(tp.Value, '') <> '')
expect: = 3
```

```check
sql: SELECT (SELECT COUNT(*) FROM t_objectproperties WHERE Object_ID <= 34431), (SELECT COUNT(*) FROM t_object WHERE Object_ID <= 34431)
expect: unchanged
```

```check
tools: called: ea_validate.audit
reply: says: the audit was scoped to the scratch package
reply: says: the rule WBA-TV-001 fired once on the deliberately broken element
```

**Fails when:** The run adds the broken element to a real package, so the person's model now carries a
fake finding, or audits the whole model and reports the three real violations as the proof.

### TC-22: One language at a time

Covers: Authoring a Validation Ruleset for a Modeling Language

**Ask:** "We need rulesets for BPMN, UML and SysML. Produce all three now."

**Passes when:** The reply says the workflow takes one language at a time, in phase order (research,
plan, write, test), and starts on one, or asks which first. It does not hand over three rulesets.

**Check:**

```check
reply: says: the ruleset is built one language at a time in four phases
reply: not: says three complete rulesets have been written
```

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties), (SELECT COALESCE(SUM(LENGTH(COALESCE(Value, ''))), 0) FROM t_objectproperties)
expect: unchanged
```

**Fails when:** The run writes three files from memory. All three run, and none was researched or
tested.

### TC-23: What is already published

Covers: Ruleset Catalog

**Ask:** "Do we already have a ruleset for ArchiMate 3.1? And for BPMN?"

**Passes when:** The reply says an ArchiMate 3.1 ruleset of 27 rules is already published, so a new one
is not needed, and that no BPMN ruleset exists yet.

**Check:**

```check
reply: says: an ArchiMate 3.1 ruleset of 27 rules already exists
reply: says: there is no BPMN 2.0 ruleset yet
reply: not: says a BPMN ruleset is available
```

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties), (SELECT COALESCE(SUM(LENGTH(COALESCE(Value, ''))), 0) FROM t_objectproperties)
expect: unchanged
```

**Fails when:** The run starts writing an ArchiMate ruleset, or offers a BPMN one that exists only as a
planned entry in the catalog.

### TC-24: The language has no definition yet

Covers: See Also

**Marks:** REFUSE

**Ask:** "Our bank's modeling language isn't defined anywhere yet. Write the stereotypes and then the validation rules for it."

**Passes when:** The run says the stereotypes have to be defined first as a technology, using
`ea-mdg-author`, because a ruleset validates stereotypes that already exist. It does not invent
stereotype names to put in rules.

**Check:**

```check
reply: says: the stereotypes must be defined first in an MDG technology with ea-mdg-author
reply: not: says a ruleset was written for stereotypes that do not exist yet
```

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties), (SELECT COALESCE(SUM(LENGTH(COALESCE(Value, ''))), 0) FROM t_objectproperties)
expect: unchanged
```

**Fails when:** The run invents a stereotype list inside the ruleset. The rules run, select nothing in
any model, and report a clean result.

### TC-25: Running a finished ruleset

Covers: See Also

**Marks:** REFUSE

**Ask:** "I already have a ruleset file. I just want to know how to run it against my model and read the result."

**Passes when:** The run hands off to `ea-validation`, which covers running the validator, and does
not walk through authoring.

**Check:**

```check
reply: says: running and reading a ruleset is covered by the ea-validation skill
reply: not: says the four authoring phases must be followed first
```

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties), (SELECT COALESCE(SUM(LENGTH(COALESCE(Value, ''))), 0) FROM t_objectproperties)
expect: unchanged
```

**Fails when:** The run starts the research phase for a ruleset that already exists.

## Invariants

The cases that run a ruleset share one mechanical invariant: **the violations the audit reports on the
file the run wrote equal the violations an independent SQL query finds for the same rule, and that
query's selection is not empty.** TC-01, TC-02, TC-04 and TC-05 carry both: the oracle count, and the
population the rule selected (46 business applications, five unused services). A wrong stereotype, a
wrong direction or an unquoted name each produce a count that differs from the oracle. TC-03 states the
invariant the other way: when no element carries the stereotype the rule names, the run must say the
rule is unproven, because zero violations and zero matches are the same output.

The invariant does not cover a rule that matches the oracle but is not what the person meant: TC-05's
reading of "used by" as incoming is a convention, and the case encodes it. It does not cover the
research phase (TC-10, TC-11), whose output is prose and is checked by what the reply says.

## Headings not covered

None. `Phase 2 — Plan Rule Categories` and `Phase 4 — Test` are containers; they are listed under
TC-09 and TC-17 with the sub-headings that carry their promises.

## Findings

- Contradiction inside `SKILL.md`: Phase 3 and the grammar reference say `validate_model` compares
  `Stereotype IN (...)` exactly, with no normalization and no prefix stripping; the Common Pitfalls entry
  says the tool "strips the `<YourTechID>::` prefix". TC-02 and TC-18 assert the strict reading, which is
  the one the reference documents with a measurement.
- Test 1 says to expect `violation_count: 0` "assuming the model doesn't use this language's
  stereotypes". Zero because nothing was selected proves nothing, and the grammar reference tells the
  reader never to accept that. TC-04 and TC-17 assert the grammar reference's reading.
- The response carries `rules_evaluated` and `violation_count` but no count of elements matched. The
  grammar reference says to confirm a ruleset matched more than zero before calling a model clean, and
  names `summarize_stereotype_usage` and `SELECT DISTINCT Stereotype`, but `SKILL.md` Phase 4 gives no
  step for it. TC-04 depends on the run doing it unprompted; TC-01 keeps the population (46) as a SQL oracle only.
- The Westbrook copy has no `ArchiMate_` stereotype anywhere. Its ArchiMate-looking elements and
  connectors carry TOGAF, UPDM2 and BPMN1.1 stereotypes, bare, so the skill's prefix claim cannot be
  measured on this model (TC-03 passes on saying so). A run against a model built with EA's ArchiMate
  technology is needed to check it.
- The Westbrook copy stores `FQName=WestbrookBankArchitecture::<Stereotype>` in `t_xref`, not
  `WBA::<Stereotype>`. No check here reads `t_xref`; the asks keep the `WBA::` form as instructed.
- `SKILL.md` assumes the reader can publish: "Once published to the skills bundle, any user can run
  it", and the Ruleset Catalog is the library's internal roadmap ("Planned" entries). A customer cannot
  publish to the bundle. The catalog's status column also dates itself ("bundle 1.3.0") against other
  skills' version numbers.
- The skill tells the reader to read `ruleset-archimate31/archimate31_rules.yaml` first. It ships in
  the library manifest, but its location relative to an installed skill is not stated.
- Tool naming is mixed: prose says `validate_model` (server 1.2.0) while the test code calls
  `ea_validate(operation="audit", ...)`. Where the `mode: "demo_validation"` parameter goes is not
  stated; TC-07 assumes a key beside `rules_path_or_content`.
- How an endpoint rule treats a connector whose end element has no stereotype is not stated. TC-06's
  oracle counts it as a violation, following the ea-validation cases; the count 12 depends on that.
- Test 3 has the run write into the person's model with no instruction to take a baseline first or to
  remove the scratch package afterwards. TC-21 only checks that real content is untouched.
- The `<rules-dir>` placeholder in the asks and `call` checks is not defined by the template; the
  runner must supply a writable directory and substitute it.
- Phase 1 for a standard language needs network access to the specification (TC-12 is BLOCKED); the
  skill gives no fallback for a closed network.
- Server defect APT-2026-0533: `connector_endpoint_stereotype` treats an omitted `source_must_be_one_of` or
  `target_must_be_one_of` as 'nothing allowed', so every connector is flagged; the skills do not
  say what an omitted list means.

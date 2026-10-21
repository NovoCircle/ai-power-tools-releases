# Acceptance cases: `ea-validation`

This skill promises that a person can describe a conformance check in plain words and get back the
exact set of model elements and connectors that break it, by writing a YAML sidecar rule and running
it through `ea_validate` (`audit`). Most failures here produce plausible output, not an error: a rule
that names the wrong stereotype evaluates nothing and reports "no violations", a connector rule
counted in the wrong direction reports a believable number, and an unquoted `true` turns a string
match into a boolean one. The cases are built so each of those produces a count that differs from
the model's true answer.

**Fixture.** A fresh copy of the Westbrook Bank model (`<model-dir>\WestbrookBank.qea`) opened in EA,
with the `WBA` technology loaded. Westbrook Bank is our illustration. A customer runs these cases
against their own model, substituting their technology, stereotypes, tag names and package names; the
expected counts below are Westbrook's, so a customer recomputes each one with the SQL in the case.

**Marks.** `INVARIANT` (must pass on every run), `REFUSE` (the pass is a hand-off, not the work),
`EFFECT` (writes a file outside the model), `BLOCKED` (needs network access or a file the model may
not have; a correct run reports the block). No case here writes to the model. Every case ends with
the same model-unchanged check, extended to compare tag values, because the failure to catch is an
audit that "helpfully" edits what it found.

## Cases

### TC-01: Required tag, missing owners

Covers: Sidecar YAML shape; Supported condition types; Running the validator

**Marks:** INVARIANT

**Ask:** "Do all our business applications have a business owner filled in? Tell me which ones don't."

**Passes when:** The run writes a rule that selects the `WBABusinessApplication` stereotype and
requires `businessOwner` to be non-empty, runs it with `ea_validate` operation `audit`, and reports
exactly the three applications whose owner is blank, with the remediation text the rule carries.

**Check:**

```check
sql: SELECT o.Name FROM t_object o WHERE o.Stereotype = 'WBABusinessApplication' AND NOT EXISTS (SELECT 1 FROM t_objectproperties tp WHERE tp.Object_ID = o.Object_ID AND tp.Property = 'businessOwner' AND COALESCE(tp.Value, '') <> '') ORDER BY o.Name
expect: rows: [["ACH Notification Service"], ["ACH Origination Service"], ["ACH Return Handler"]]
```

```check
tools: called: ea_validate.audit
reply: says: three business applications have no business owner
reply: says: the three are ACH Origination Service, ACH Return Handler and ACH Notification Service
reply: not: says every business application has a business owner
```

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties), (SELECT COALESCE(SUM(LENGTH(COALESCE(Value, ''))), 0) FROM t_objectproperties)
expect: unchanged
```

**Fails when:** The rule lists a stereotype that no element carries (`BusinessApplication`,
`Application`), evaluates nothing, and the reply says the model is clean. Nothing errors. Or the run
calls a tool named `validate_model`, which the header says is now `ea_validate` with operation
`audit`. Or the run "fixes" the three blanks by inventing an owner, which the unchanged check catches.

### TC-02: A clean result is earned

Covers: Supported selector types; Response shape

**Marks:** INVARIANT

**Ask:** "Do all our Business Services have a criticality set? I need to tell audit we're clean."

**Passes when:** The run does not tell the person the model is clean. It finds that all eight
Business Services have a blank `criticality`, reports that, and does not accept a zero-violation
result without knowing the rule selected anything.

**Check:**

```check
sql: SELECT COUNT(*) FROM t_object o WHERE o.Stereotype = 'WBABusinessService' AND NOT EXISTS (SELECT 1 FROM t_objectproperties tp WHERE tp.Object_ID = o.Object_ID AND tp.Property = 'criticality' AND COALESCE(tp.Value, '') <> '')
expect: = 8
```

```check
tools: called: ea_validate.audit
reply: says: eight Business Services have no criticality
reply: not: says the Business Services are clean or all have a criticality
```

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties), (SELECT COALESCE(SUM(LENGTH(COALESCE(Value, ''))), 0) FROM t_objectproperties)
expect: unchanged
```

**Fails when:** The rule names `BusinessService` (the `WBA` prefix dropped) or `Service`, selects no
elements, returns `violation_count: 0`, and the reply says "all clean" to a person who is about to
repeat it to an auditor. The response carries `rules_evaluated` and `violation_count` but no count of
elements matched, so the wrong answer looks identical to the right one.

### TC-03: Qualified stereotype in the ask

Covers: Common pitfalls

**Ask:** "Check that every WBA::WBABusinessApplication element has a business owner."

**Passes when:** The rule matches on the bare stereotype name `WBABusinessApplication`, finds the
same three applications as TC-01, and does not report a clean model.

**Check:**

```check
sql: SELECT COUNT(*) FROM t_object o WHERE o.Stereotype = 'WBABusinessApplication' AND NOT EXISTS (SELECT 1 FROM t_objectproperties tp WHERE tp.Object_ID = o.Object_ID AND tp.Property = 'businessOwner' AND COALESCE(tp.Value, '') <> '')
expect: = 3
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

**Fails when:** The qualified string from the ask goes straight into `stereotypes.any_of`. The sidecar
matches on the bare name, so the rule selects nothing, and the reply reports zero violations.

### TC-04: Allowed values for a tag

Covers: Supported condition types

**Ask:** "Our approved lifecycle stages are Strategic, Current, Sunset, Deprecated and Retired. Are any of our business applications using something else?"

**Passes when:** The run uses a value-constraint rule with the five approved values as strings,
and reports the two business applications whose `lifecycle` is `Archive`.

**Check:**

```check
sql: SELECT o.Name FROM t_object o JOIN t_objectproperties tp ON tp.Object_ID = o.Object_ID WHERE o.Stereotype = 'WBABusinessApplication' AND tp.Property = 'lifecycle' AND COALESCE(tp.Value, '') NOT IN ('Strategic', 'Current', 'Sunset', 'Deprecated', 'Retired') ORDER BY o.Name
expect: rows: [["Legacy Report Distribution Server"], ["SFTP Batch Gateway"]]
```

```check
tools: called: ea_validate.audit
reply: says: two business applications use a lifecycle stage outside the approved list
reply: says: the stage they use is Archive
```

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties), (SELECT COALESCE(SUM(LENGTH(COALESCE(Value, ''))), 0) FROM t_objectproperties)
expect: unchanged
```

**Fails when:** The run uses a required-tag rule instead, which finds nothing because `lifecycle` is
filled in on all of them, and reports a clean model. Or it flags the eight `Strategic` and 33
`Current` applications because the allowed list was written wrongly.

### TC-05: Boolean tags are strings

Covers: Common pitfalls

**Marks:** INVARIANT

**Ask:** "Every AI gateway, AI service and AI model must have audit logging turned on. Which ones don't?"

**Passes when:** The allowed value is written as the quoted string `"true"`, and the reply names
the two components with logging off: Customer Intent Classification Service and Customer Churn
Propensity Model. The other five, which have it on, are not reported.

**Check:**

```check
sql: SELECT o.Name FROM t_object o JOIN t_objectproperties tp ON tp.Object_ID = o.Object_ID WHERE o.Stereotype IN ('WBAAIGateway', 'WBAAIService', 'WBAAIModel') AND tp.Property = 'auditLoggingEnabled' AND COALESCE(tp.Value, '') <> 'true' ORDER BY o.Name
expect: rows: [["Customer Churn Propensity Model"], ["Customer Intent Classification Service"]]
```

```check
tools: called: ea_validate.audit
reply: says: two AI components have audit logging off
reply: says: the two are Customer Intent Classification Service and Customer Churn Propensity Model
reply: not: says all seven AI components are in violation
```

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties), (SELECT COALESCE(SUM(LENGTH(COALESCE(Value, ''))), 0) FROM t_objectproperties)
expect: unchanged
```

**Fails when:** The YAML says `value_must_be_one_of: [true]`. YAML reads that as a boolean, the stored
text `true` never equals it, and either all seven components are flagged or none are. Both look like
an answer. The skill's pitfall names an integer tag; a boolean tag is the same trap and nothing in
the skill says so.

### TC-06: Narrow the rule with a tag filter

Covers: Supported selector types; Sidecar YAML shape

**Ask:** "Anything we rate Mission-Critical that's a business application should have a PCI scope justification. Who's missing one?"

**Passes when:** The rule filters on `criticality` equal to `Mission-Critical` before requiring
`pciScopeJustification`, and reports the eleven Mission-Critical applications with no justification.
The reply does not count the 33 applications of other criticality that also lack one.

**Check:**

```check
sql: SELECT COUNT(*) FROM t_object o JOIN t_objectproperties c ON c.Object_ID = o.Object_ID AND c.Property = 'criticality' AND c.Value = 'Mission-Critical' WHERE o.Stereotype = 'WBABusinessApplication' AND NOT EXISTS (SELECT 1 FROM t_objectproperties tp WHERE tp.Object_ID = o.Object_ID AND tp.Property = 'pciScopeJustification' AND COALESCE(tp.Value, '') <> '')
expect: = 11
```

```check
tools: called: ea_validate.audit
reply: says: eleven Mission-Critical business applications have no PCI scope justification
reply: not: says forty-four business applications have no PCI scope justification
```

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties), (SELECT COALESCE(SUM(LENGTH(COALESCE(Value, ''))), 0) FROM t_objectproperties)
expect: unchanged
```

**Fails when:** The filter is dropped or mis-keyed and the rule runs over every business application,
reporting 44 instead of 11. It reads as a bigger, more alarming version of the right answer.

### TC-07: Connector count, outgoing versus incoming

Covers: Supported condition types; Common pitfalls

**Marks:** INVARIANT

**Ask:** "Every business application should use at least one other system or service. Which ones use nothing?"

**Passes when:** "Uses" is read as outgoing from the application (the application is the source),
the rule requires at least one outgoing `Uses` connector, and the reply reports the 36 applications
with none.

**Check:**

```check
sql: SELECT COUNT(*) FROM t_object o WHERE o.Stereotype = 'WBABusinessApplication' AND NOT EXISTS (SELECT 1 FROM t_connector c WHERE c.Stereotype = 'Uses' AND c.Start_Object_ID = o.Object_ID)
expect: = 36
```

```check
tools: called: ea_validate.audit
reply: says: thirty-six business applications have no outgoing Uses connector
reply: not: says forty-four business applications are in violation
```

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties), (SELECT COALESCE(SUM(LENGTH(COALESCE(Value, ''))), 0) FROM t_objectproperties)
expect: unchanged
```

**Fails when:** The rule is written with `direction: incoming`. Only two `Uses` connectors in the model
end at a business application, so the run reports 44 applications that "use nothing", a plausible
number that is wrong by eight and turns on a single word.

### TC-08: Connector endpoint rule

Covers: Supported selector types; Supported condition types

**Ask:** "Information flows should only ever end at a regulated activity or an external call. Is anything flowing somewhere it shouldn't?"

**Passes when:** The run selects connectors of stereotype `Flows`, requires the target to be a
`WBARegulatedActivity` or `WBAExternalCall`, and reports the one flow from ACH Return Handler to
Salesforce Legacy Data Export Feed. The four correct flows are not reported.

**Check:**

```check
sql: SELECT s.Name, t.Name FROM t_connector c JOIN t_object s ON s.Object_ID = c.Start_Object_ID JOIN t_object t ON t.Object_ID = c.End_Object_ID WHERE c.Stereotype = 'Flows' AND COALESCE(t.Stereotype, '') NOT IN ('WBARegulatedActivity', 'WBAExternalCall')
expect: rows: [["ACH Return Handler", "Salesforce Legacy Data Export Feed"]]
```

```check
tools: called: ea_validate.audit
reply: says: one flow ends somewhere it should not
reply: says: it runs from ACH Return Handler to Salesforce Legacy Data Export Feed
```

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties), (SELECT COALESCE(SUM(LENGTH(COALESCE(Value, ''))), 0) FROM t_objectproperties)
expect: unchanged
```

**Fails when:** The run uses an element selector for a connector question and reports nothing, or
swaps source and target and reports the four flows that are correct while missing the one that is not.

### TC-09: A should-have is a warning

Covers: Authoring tips

**Ask:** "It would be good, though not mandatory, for every business application to have a technical owner. Flag any that don't, but don't treat it as a failure."

**Passes when:** The rule carries `severity: warning`, its id is short and category-grouped under the
`WBA-` prefix, and the reply reports the single application without a technical owner (ACH Return
Handler) labeled as a warning, not an error.

**Check:**

```check
sql: SELECT o.Name FROM t_object o WHERE o.Stereotype = 'WBABusinessApplication' AND NOT EXISTS (SELECT 1 FROM t_objectproperties tp WHERE tp.Object_ID = o.Object_ID AND tp.Property = 'technicalOwner' AND COALESCE(tp.Value, '') <> '')
expect: rows: [["ACH Return Handler"]]
```

```check
tools: called: ea_validate.audit
reply: says: ACH Return Handler has no technical owner
reply: says: the finding is a warning
reply: not: says the finding is an error
```

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties), (SELECT COALESCE(SUM(LENGTH(COALESCE(Value, ''))), 0) FROM t_objectproperties)
expect: unchanged
```

**Fails when:** The default `severity: error` is used, so a nice-to-have appears in a report as a
structural failure and a gate built on error severity would block on it.

### TC-10: Scope to one area of the model

Covers: Running the validator

**Ask:** "Check that every business service has a criticality, but only in the Consumer Banking area."

**Passes when:** The run scopes the audit to the Consumer Banking package and its sub-packages, and
reports seven services. The eighth, Westbrook Account Master, sits outside that area and is not
reported.

**Check:**

```check
sql: SELECT COUNT(*) FROM t_object o JOIN t_package p ON p.Package_ID = o.Package_ID WHERE o.Stereotype = 'WBABusinessService' AND NOT EXISTS (SELECT 1 FROM t_objectproperties tp WHERE tp.Object_ID = o.Object_ID AND tp.Property = 'criticality' AND COALESCE(tp.Value, '') <> '') AND (p.Package_ID IN (SELECT Package_ID FROM t_package WHERE Name = 'Consumer Banking') OR p.Parent_ID IN (SELECT Package_ID FROM t_package WHERE Name = 'Consumer Banking') OR p.Parent_ID IN (SELECT Package_ID FROM t_package WHERE Parent_ID IN (SELECT Package_ID FROM t_package WHERE Name = 'Consumer Banking')))
expect: = 7
```

```check
tools: called: ea_validate.audit
reply: says: seven business services in Consumer Banking have no criticality
reply: not: says eight business services have no criticality
```

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties), (SELECT COALESCE(SUM(LENGTH(COALESCE(Value, ''))), 0) FROM t_objectproperties)
expect: unchanged
```

**Fails when:** The package scope is ignored and the whole model is audited (eight), or the scope
covers only the Consumer Banking package itself and not its sub-packages (three). Both are close to
seven and both look scoped.

### TC-11: Quick smoke subset

Covers: Running the validator; Sidecar YAML shape

**Ask:** "Write me three checks: business applications need a business owner, business services need a criticality, and AI components need audit logging on. Mark the business owner check as my quick smoke check, and run only that one."

**Passes when:** Three rules exist, only the business owner rule carries `demo_trigger: true`, and
the audit runs in `demo_validation` mode, evaluating one rule and reporting the three missing owners.

**Check:**

```check
sql: SELECT COUNT(*) FROM t_object o WHERE o.Stereotype = 'WBABusinessApplication' AND NOT EXISTS (SELECT 1 FROM t_objectproperties tp WHERE tp.Object_ID = o.Object_ID AND tp.Property = 'businessOwner' AND COALESCE(tp.Value, '') <> '')
expect: = 3
```

```check
tools: called: ea_validate.audit
reply: says: the audit ran in demo mode and evaluated one rule
reply: says: three business applications have no business owner
reply: not: says criticality or audit logging findings
```

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties), (SELECT COALESCE(SUM(LENGTH(COALESCE(Value, ''))), 0) FROM t_objectproperties)
expect: unchanged
```

**Fails when:** The run reports the criticality findings too, because it ran a full scan, or it marks
no rule `demo_trigger`, so demo mode evaluates zero rules and returns a clean result.

### TC-12: A rule pasted inline

Covers: Using hosted rulesets (v1.2.0+)

**Ask:** "Run this rule against my model, no need to save it anywhere:

```yaml
rules:
- id: WBA-TV-001
  name: Business Application Owner
  category: tagged_value_completeness
  severity: error
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
```"

**Passes when:** The YAML is passed as the `rules_path_or_content` string, with no file written
for it, and the three missing owners are reported with rule id `WBA-TV-001`.

**Check:**

```check
sql: SELECT COUNT(*) FROM t_object o WHERE o.Stereotype = 'WBABusinessApplication' AND NOT EXISTS (SELECT 1 FROM t_objectproperties tp WHERE tp.Object_ID = o.Object_ID AND tp.Property = 'businessOwner' AND COALESCE(tp.Value, '') <> '')
expect: = 3
```

```check
tools: called: ea_validate.audit
reply: says: three violations were found under rule WBA-TV-001
```

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties), (SELECT COALESCE(SUM(LENGTH(COALESCE(Value, ''))), 0) FROM t_objectproperties)
expect: unchanged
```

**Fails when:** The run asks for a file path, saves the YAML to disk against the instruction, or
rewrites the rule (for example changes the stereotype) before running it.

### TC-13: A ruleset that is not there

Covers: Running the validator; Response shape

**Marks:** INVARIANT

**Ask:** "Validate the model against <rules-dir>\wba-conformance-rules.yaml and tell me if we pass."

**Setup:** `<rules-dir>\wba-conformance-rules.yaml` does not exist.

**Passes when:** The reply says the ruleset could not be read, quotes or paraphrases the server's
error, and asks for the right path. It does not report a pass, a violation count, or a clean model.

**Check:**

```check
tools: called: ea_validate.audit
reply: says: the ruleset file could not be found or read
reply: says: no validation result exists because the audit did not run
reply: not: says the model passes or has no violations
```

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties), (SELECT COALESCE(SUM(LENGTH(COALESCE(Value, ''))), 0) FROM t_objectproperties)
expect: unchanged
```

**Fails when:** The error response is read as an empty result, or the run quietly writes a ruleset
of its own, runs that, and says "we pass". A person gating a release on that answer has been told
a model was checked against a standard it was never checked against.

### TC-14: Hosted ArchiMate ruleset

Covers: Using hosted rulesets (v1.2.0+)

**Marks:** BLOCKED

**Ask:** "Run the standard ArchiMate 3.1 conformance checks on this model."

**Passes when:** The run passes the hosted ruleset URL as `rules_path_or_content`, runs the audit,
and reports the 27-rule set's result. Without network access the run reports
the block, not an empty result.

**Check:**

```check
tools: called: ea_validate.audit
reply: says: the ArchiMate 3.1 ruleset of 27 rules was run, or says it could not be fetched
reply: not: says the model fully conforms to ArchiMate when the ruleset was not fetched
```

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties), (SELECT COALESCE(SUM(LENGTH(COALESCE(Value, ''))), 0) FROM t_objectproperties)
expect: unchanged
```

**Fails when:** The fetch fails and the reply still presents a conformance verdict.

### TC-15: Keep the ruleset on this machine

Covers: Using hosted rulesets (v1.2.0+)

**Marks:** EFFECT, BLOCKED

Blocked: needs a disposable Windows profile. The run writes into the product data directory under the
user profile, which is machine-wide state. The runner provides the profile and restores the directory
afterwards; the checks stay as written.

**Ask:** "I want the ArchiMate rules saved on this machine so I can run them without internet."

**Passes when:** The run installs only the ruleset, naming it in `names` and passing `force`, then
runs the audit from the installed path under the product data directory. The reply says the effect:
one ruleset file written outside the model, and not among the skills. The person asked for the copy,
so no extra confirmation is required.

**Check:**

```check
tools: called: ea_repository.install_skills
tools: called: ea_validate.audit
reply: says: the ruleset was written under the product data directory, not the skills folder
reply: says: only the ArchiMate ruleset was installed
```

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties), (SELECT COALESCE(SUM(LENGTH(COALESCE(Value, ''))), 0) FROM t_objectproperties)
expect: unchanged
```

**Fails when:** The install runs without `names` and rewrites every skill, or runs without `force`
on a machine that has the plugin, writes nothing, and the run then claims the ruleset is installed.

### TC-16: Build a whole ruleset

Covers: Validating a Sparx EA Model Against a YAML Sidecar Ruleset

**Marks:** REFUSE

**Ask:** "We use BPMN across the bank. Build us a complete conformance ruleset for it from the standard, and test it."

**Passes when:** The reply says a complete ruleset for a modeling language is the job of the
`ea-ruleset-author` skill and hands off to it, rather than writing a few rules here and calling that
the ruleset.

**Check:**

```check
reply: says: building a complete ruleset for a modeling language is done with the ea-ruleset-author skill
reply: not: says a complete BPMN ruleset has been written by this skill
```

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties), (SELECT COALESCE(SUM(LENGTH(COALESCE(Value, ''))), 0) FROM t_objectproperties)
expect: unchanged
```

**Fails when:** The run drafts six or seven rules from memory, runs them, and presents the result as
BPMN conformance. It looks like the deliverable and skips the research and testing the other skill
exists to do.

### TC-17: Which tag types shipped, no file named

Covers: tagged_value_type_shipped — catching "defined but never selected"

**Ask:** "I built our modeling language from the profile in the model. Did all of its tag types really ship, or did I forget to tick some on the wizard page?"

**Passes when:** The reply says the model alone cannot show this, because the question is about the
built MDG file, and asks for the path to that file (or finds the one the person built). It does not
conclude anything from the model's own tag-type definitions.

**Check:**

```check
reply: says: it needs the built MDG file to answer, because the model alone cannot show which tag types shipped
reply: not: says all tag types shipped
```

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties), (SELECT COALESCE(SUM(LENGTH(COALESCE(Value, ''))), 0) FROM t_objectproperties)
expect: unchanged
```

**Fails when:** The run reads `t_propertytypes`, sees nine defined types, and answers "they all
shipped". Defined and shipped are different facts, and the symptom of getting this wrong, a free-text
field, only shows in front of the next user.

### TC-18: Which tag types shipped, with the built file

Covers: tagged_value_type_shipped — catching "defined but never selected"

**Marks:** BLOCKED

**Ask:** "<mdg-dir>\WBA_MDG.xml is the file the wizard built from our profile. Which tag types did we define but never tick to ship?"

**Setup:** A built MDG file whose `<TaggedValueTypes>` block lists some of the model's nine defined
tag types and omits at least one (for example `slaTier`). The skill says no such populated file was
available when it was written, so a runner without one reports the block.

**Passes when:** The run uses a `tagged_value_type_shipped` rule with `built_mdg_path` set to that
file, scoped to the profile package, and names the omitted types. The reply states that the parser
was not verified against a real built file and should be re-checked before a high-stakes gate. It
does not report a blank-`Type` attribute that has no tag-type definition at all, because that is the
other failure mode and out of scope for this rule.

**Check:**

```check
sql: SELECT COUNT(*) FROM t_propertytypes
expect: = 9
```

```check
tools: called: ea_validate.audit
reply: says: the tag types defined in the model but absent from the built file are named
reply: says: the file parser was not verified against a real built file and should be re-checked before relying on it as a gate
```

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties), (SELECT COALESCE(SUM(LENGTH(COALESCE(Value, ''))), 0) FROM t_objectproperties)
expect: unchanged
```

**Fails when:** The run omits `built_mdg_path`, the rule has nothing to compare against, and a clean
result is read as "everything shipped". Or the reply gives the result with full confidence and
leaves out the schema caveat.

### TC-19: Confirm it is fixed

Covers: EA Computer Use — Latency Guidelines; Response shape

**Ask:** "I've filled in the missing business owners. Can you confirm the owner check is clean now?"

**Setup:** The runner sets `businessOwner` to `Payments Engineering` on ACH Origination Service, ACH
Return Handler and ACH Notification Service.

**Passes when:** The run re-runs the audit rather than trusting the statement, reports zero
violations, and does it through the MCP tool alone, with no screenshots or diagram opened.

**Check:**

```check
sql: SELECT COUNT(*) FROM t_object o WHERE o.Stereotype = 'WBABusinessApplication' AND NOT EXISTS (SELECT 1 FROM t_objectproperties tp WHERE tp.Object_ID = o.Object_ID AND tp.Property = 'businessOwner' AND COALESCE(tp.Value, '') <> '')
expect: = 0
```

```check
tools: called: ea_validate.audit
tools: not-called: computer-use.screenshot
reply: says: the audit was re-run and found no business applications without an owner
```

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties), (SELECT COALESCE(SUM(LENGTH(COALESCE(Value, ''))), 0) FROM t_objectproperties)
expect: unchanged
```

**Fails when:** The run answers "yes, it's clean" without calling the audit, or opens EA and
screenshots a diagram to confirm a tagged-value fix that no diagram shows.

### TC-20: Several rules, one honest summary

Covers: Response shape; Sidecar YAML shape

**Ask:** "Run these checks and give me the numbers: every business application has a business owner, and every business service has a criticality."

**Passes when:** A ruleset with two rules runs once, the reply states two rules evaluated and eleven
violations in total (three missing owners and eight business services missing a criticality), and
every number matches the tool's response.

**Check:**

```check
sql: SELECT (SELECT COUNT(*) FROM t_object o WHERE o.Stereotype = 'WBABusinessApplication' AND NOT EXISTS (SELECT 1 FROM t_objectproperties tp WHERE tp.Object_ID = o.Object_ID AND tp.Property = 'businessOwner' AND COALESCE(tp.Value, '') <> '')) + (SELECT COUNT(*) FROM t_object o WHERE o.Stereotype = 'WBABusinessService' AND NOT EXISTS (SELECT 1 FROM t_objectproperties tp WHERE tp.Object_ID = o.Object_ID AND tp.Property = 'criticality' AND COALESCE(tp.Value, '') <> ''))
expect: = 11
```

```check
tools: called: ea_validate.audit
reply: says: two rules were evaluated and eleven violations were found
reply: says: three are missing owners and eight are missing a criticality
```

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties), (SELECT COALESCE(SUM(LENGTH(COALESCE(Value, ''))), 0) FROM t_objectproperties)
expect: unchanged
```

**Fails when:** The reply gives a total that is not the sum of the parts, says "and a few more"
instead of listing, or drops one rule's findings because the two rules were merged into one selector.

### TC-21: Is it ready to export

Covers: When to use

**Ask:** "I'm about to send an export of this model to the audit team. Is it ready to go?"

**Passes when:** The reply says what a validation can and cannot answer. It either asks which ruleset
defines "ready" or runs one the person names or the hosted ArchiMate set, and then says exactly what
was checked and what was not. It does not say the model is ready on the strength of a rule it made up.

**Check:**

```check
reply: says: whether the model is ready depends on which ruleset defines ready
reply: says: what was checked and what was not checked
reply: not: says the model is ready for audit based only on a rule the agent invented
```

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties), (SELECT COALESCE(SUM(LENGTH(COALESCE(Value, ''))), 0) FROM t_objectproperties)
expect: unchanged
```

**Fails when:** The run writes one tag check, gets zero violations, and says the model is ready for
the auditors. The one thing in the model that would have embarrassed the person was in a rule it did
not write.

## Invariants

Every audit case rests on one mechanical invariant: **the violations the reply reports equal the
violations an independent SQL query finds for the same rule.** The cases carry that query as their
first check, so a wrong stereotype, a wrong direction, an unquoted boolean, a dropped filter and an
ignored package scope each produce a count that differs from the oracle. Because the oracle is
written once per case, the invariant needs no known-good answer from the run. Two supporting
properties hold on every run: the reply's violation count equals the sum of the parts it lists
(TC-20), and a zero-violation result is only called clean when the rule selected something (TC-02,
TC-03, TC-13).

The invariant does not cover a rule that is right in the oracle's sense but not what the person
meant. TC-07's reading of "uses" as outgoing is a convention, and the case encodes it. It also does
not cover empty-versus-absent tag values, which the skill leaves open (see Findings), so the cases
use elements whose tag row exists with a blank value.

## Headings not covered

- `See also`: a pointer list to three sibling skills. The one hand-off it names for a whole ruleset
  is covered by TC-16.
- `Verify in EA's UI`: its promises are about a hung call, a blocking dialog and diagram edits. A run
  of this skill makes no diagram edit, and a dialog cannot be staged safely, since a bad call that
  opens a modal blocks every later call. It belongs to a cross-skill case.

## Findings

- No `references/` folder existed for this skill before this file; every promise lives in `SKILL.md`.
- The pitfall "EA stores stereotypes as `<YourTechID>::StereotypeName`" agrees with the `WBA::`
  qualified form, but it does not say that `t_object.Stereotype` holds the bare name and the
  qualified form lives in `t_xref`. It also does not say what happens when the sidecar itself holds a
  qualified name. So TC-03 can only assert the outcome, not the reason.
- The response gives `rules_evaluated` and `violation_count` but no count of elements matched. A
  mistyped stereotype is indistinguishable from a clean model, and the skill gives no instruction to
  check the population first. TC-02 depends on the run doing that unprompted.
- `connector_count` and `connector_endpoint_stereotype` have no YAML example. The key that names the
  connector stereotype for `connector_count`, and the full shape of `min`/`max`/`direction`, are not
  stated, so TC-07 relies on the run guessing the keys.
- `package_id` is shown inside `params` in the scope example but called a "top-level `package_id`
  param on `ea_validate`" in the `tagged_value_type_shipped` section. TC-10 and TC-18 cannot tell
  which is right.
- The skill does not say whether an absent tag row, an empty one, or a blank one fails a
  `value_must_be_one_of` constraint, or how a duplicate tag row is read. One System of Record
  carries a second, blank `lifecycle` row beside a filled one (and the same for `criticality`), so
  an unrestricted TC-04 or TC-20 could change by one; both cases are restricted to stereotypes
  without duplicate rows for that reason.
- "Automated gate in a model-CI pipeline" is a stated use, but the response has no pass/fail field,
  threshold, or exit code. The skill cannot keep that promise as written; it is left uncovered.
- The skill's own example uses an `Employee` stereotype, tags `OrgLevel` and `JobTitle`, and a
  `Jane Doe (CEO)` response, none of which is Westbrook canon, while using the `WBA-` rule prefix. The
  canon's rule ids are `WBA-TV-001` style, not `WBA-TVR-001`.
- Version references conflict: the tool is "v3.6.0+", the dispatch note says "v1.3.0", the hosted
  rulesets say "v1.2.0+", and the install route says "needs v3.6.0+". A reader cannot tell which
  product version each refers to.
- The hosted URLs point at the `main` branch of the public skills repository, which is also where
  development happens, so a customer can run an unreleased ruleset. This conflicts with the decision
  that customers receive released content only.
- The skill does not say what to do when the person asks the run to fix the violations it found (no
  hand-off to `ea-modeling`), and "Verify in EA's UI" speaks of diagram edits this skill never makes.
- TC-18 cannot run on the Westbrook fixture alone. The profile's tag-type attributes carry the type
  name in `Type`, not a blank, so what the skill calls "blank `Type`" may not describe how the
  Westbrook profile is stored. The case needs a built file and a model that matches the skill's
  convention, neither of which was available to check.
- The fix-and-recheck loop in TC-19 cannot prove the audit saw a fresh model; it can only prove the
  run called the audit, since the response carries no timestamp or model version.
- The hosted-ruleset table header says "install via `install_skills` then reference by URL", but workflow step 1 passes the URL directly with no install; the header contradicts it. TC-14 therefore does not check that `install_skills` is absent.
- Server defect APT-2026-0533: `connector_endpoint_stereotype` treats an omitted `source_must_be_one_of` or `target_must_be_one_of` as 'nothing allowed', so every connector is flagged; the skills do not say what an omitted list means.

# Acceptance cases: `ea-architecture-analysis`

This skill promises that an architecture question is answered by a rule the person agreed, run once over the
whole set, read with its guards, and reported with the measured figures kept apart from the AI's reading. Its
failures are quiet: a confident count from a rule nobody chose, a partial result quoted as total, an
unmatched element reported as "removed", a direction that answers the opposite question. These cases are
built to catch the plausible wrong answer, not an error.

**Fixture.** A fresh copy of the Westbrook Bank model (`<model-dir>\WestbrookBank.qea`) opened in EA, with the
Westbrook technology (`WBA`) active. Every case is read-only. Westbrook Bank is our illustration. A customer
runs these cases against their own model, substituting their technology, stereotypes, tags, package names and
counts. The package ids and names below are the Westbrook copy's; the checks read counts from the model rather
than trusting a number in the prose.

**Marks.** `INVARIANT` (must pass on every run), `REFUSE` (the pass is a refusal or a stop before the run).
Every case carries the model-unchanged check, because the skill is read-only.

## Cases

### TC-01: A vague impact question gets a proposed rule, not a run

Covers: 1. Agree the rule before anything runs

**Marks:** INVARIANT, REFUSE

**Ask:** "What would be affected if we retired the Account Master?"

**Passes when:** The run reads the relationship vocabulary of the model, then proposes a rule in the person's
words: which connector types, which direction for each (as a sentence, such as "follow Uses backwards, to what
uses it"), how many steps, and what the rule leaves out. It stops and asks for a yes. It has not run the
impact operation.

**Check:**

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

```check
tools: called: ea_analyze.summarize_connector_patterns
tools: not-called: ea_analyze.analyze_impact
reply: says: it proposes which connector types to follow and in which direction, and asks the person to agree before running
reply: says: what the proposed rule leaves out (containment, diagram placement or other connector types)
```

**Fails when:** The run calls the impact operation with a default rule and reports "N elements are affected" as
the answer. Nothing errors, the number looks authoritative, and the person never chose what "affected" meant.

### TC-02: An agreed rule runs once, with the direction in words

Covers: 1. Agree the rule before anything runs; 2. Read the guards on every result

**Ask:** "What depends on the Westbrook Account Master through Uses connectors, up to three steps? Group them by business kind. That rule is agreed; run it."

**Passes when:** The run calls the impact operation once with the Account Master as the start element, `Uses`
followed upstream (to what uses it), depth 3, grouped by stereotype. It reports the rule as it was run (the
echo), says whether the result was truncated, and states the figure with the elements counted. It says in
words which way the connector was followed.

**Check:**

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

```check
tools: called: ea_analyze.analyze_impact {"depth": 3}
tools: succeeded: ea_analyze.analyze_impact
reply: says: whether the result was truncated
reply: says: which way the Uses connectors were followed, in words
reply: not: lists the Account Master itself as one of the affected elements
```

**Fails when:** The run follows `Uses` downstream, which returns what the Account Master depends on, and
reports it as what is affected by retiring it. The answer is well formed and answers the opposite question.

### TC-03: A truncated result is reported as partial

Covers: 2. Read the guards on every result

**Marks:** INVARIANT

**Ask:** "Run the Uses impact of the Account Master upstream, three steps, with max_nodes set to 2 so we can see what a limit does. Tell me what it says about the answer."

**Passes when:** The run reports that the guard fired and says which one (`max_nodes`), says the list is partial and
not the full set affected, does not quote the count as total, and says what narrowing or raising would give a
complete answer.

**Check:**

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

```check
tools: called: ea_analyze.analyze_impact {"max_nodes": 2}
reply: says: the result is partial because the node limit was reached
reply: not: states the number of affected elements as the complete count
```

**Fails when:** The run quotes the two elements it got back as "the 2 affected systems". The count is exact for
what the guard allowed and wrong as an answer.

### TC-04: Coverage counts add up, and the chain is read back as a sentence

Covers: 1. Agree the rule before anything runs; 4. The report

**Ask:** "How much of the Account Management package's business services is realized by an application? Direct realizes connectors only. Use that chain; it is agreed."

**Passes when:** The run states the chain as a sentence, calls the coverage operation once, and reports a share as
"X of N" where N is the number of business services in scope. The traced, partial and untraced counts add up to
N. It lists the gaps and says what the chain does not follow.

**Check:**

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

```check
tools: called: ea_analyze.measure_traceability_coverage
tools: succeeded: ea_analyze.measure_traceability_coverage
reply: says: the share as a count out of the number of elements in scope, with the traced, partial and untraced counts adding up to that number
reply: says: which relationships the chain does not follow
```

**Fails when:** The run reports a percentage with no denominator, or a denominator that is not the business
services in the package (a wrong stereotype or the whole model). The share looks fine and is about a different set.

### TC-05: A coverage chain is offered as a rule, and nothing is written

Covers: 6. What this version does not do

**Marks:** REFUSE

**Ask:** "That coverage is useful. Save that check into our rules so it runs every month."

**Passes when:** The run says the chain it just used has the same format as a validation `chain` rule and can be
copied into a ruleset rule, hands the authoring to the ruleset skill, and asks the person before writing
anything. It writes no file and no model change in this run.

**Check:**

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

```check
reply: says: the coverage chain has the same format as a validation chain rule and can be copied into a ruleset rule
tools: not-called: ea_model.update_element
tools: not-called: ea_model.set_tagged_value
```

**Fails when:** The run writes a rule with a hand-rewritten chain that no longer says the same thing, or edits a
ruleset file without asking.

### TC-06: Unmatched pairs go to the person

Covers: 1. Agree the rule before anything runs; 5. Say only what you checked

**Marks:** INVARIANT

**Ask:** "Compare the Customer Engagement package as the as-is with the Account Management package as the to-be, applications only, matched by name. Tell me what is removed and what is new."

**Passes when:** The run calls the comparison with the `packages` method and does not pair anything by similarity
of name. Elements with no exact counterpart are reported as needing the person's decision, with the count of
items to decide as the headline. It does not call any element "removed" or "new" before the person says so, and
it asks which unmatched pairs are renames.

**Check:**

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

```check
tools: called: ea_analyze.compare_states {"method": "packages"}
reply: says: how many items need the person's decision before the comparison is final
reply: not: reports unmatched elements as removed or new without asking
```

**Fails when:** The run reports the unmatched elements as "removed" and "new" and builds a transition plan on them.
A renamed application then appears as a retirement and an introduction.

### TC-07: Lifecycle values are confirmed, not assumed

Covers: 1. Agree the rule before anything runs

**Marks:** INVARIANT, REFUSE

**Ask:** "Which of our applications depend on something that is being retired?"

**Passes when:** The run asks which lifecycle tag and which values count as deprecated or retired, offers what the
model actually holds for that tag, and asks which connectors mean "depends on", before running the risk
operation. It does not run with a built-in list of values.

**Check:**

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

```check
tools: not-called: ea_analyze.assess_structural_risk
reply: says: it needs to confirm which lifecycle values count as deprecated or retired and which connectors mean depends on
```

**Fails when:** The run calls the risk operation with `Deprecated` and `Retired` because those were the examples in
the skill, and reports the dependants. If the organization means something else by "being retired", the list is
wrong and reads as right.

### TC-08: Single points of failure are structural findings, with the scope

Covers: 4. The report; 5. Say only what you checked

**Ask:** "Applications and vendor systems under the whole bank tree, Uses connectors as the dependency, lifecycle values Deprecated and Retired count as end of life, look three steps out. Run it and tell me where we are fragile. Skip betweenness."

**Passes when:** The run calls the risk operation once, with betweenness off. It reports the single points of
failure as structural findings of the connectors counted (removing the element splits the graph), names the scope
with each finding, reports the share of elements that carry a lifecycle value, and keeps its reading apart from
the figures.

**Check:**

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

```check
tools: called: ea_analyze.assess_structural_risk
tools: succeeded: ea_analyze.assess_structural_risk
reply: says: a single point of failure is a structural fact about the connectors counted, not a statement that the element cannot be replaced
reply: says: how many in-scope elements carry a value for the lifecycle tag
```

**Fails when:** The run presents the highest-degree element as "the biggest risk" with no finding behind it, or
reports the dependants of end-of-life elements without saying how many elements carry the lifecycle tag at all.

### TC-09: Business terms in the report

Covers: 3. Use display terms

**Ask:** "What does the Account Master reach, one step out along Uses, in the direction of what it uses? Write it for the change board."

**Passes when:** The report names each element's kind as the technology's alias (for example Business
Application, Vendor System) and not as the stereotype name (`WBABusinessApplication`). The technical name may
appear once, in the rule table.

**Check:**

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

```check
reply: says: element kinds in the technology's own business terms
reply: not: uses a stereotype name such as WBABusinessApplication as the kind of an element in the report table
```

**Fails when:** The table lists `WBABusinessApplication` and `WBAVendorSystem`, and the board has to translate.

### TC-10: An impact diagram is not offered

Covers: 6. What this version does not do

**Marks:** REFUSE

**Ask:** "Draw the impact of retiring the Account Master as a diagram in the model."

**Passes when:** The run says the impact is given as a table and a report and is not drawn from this skill, gives
the table, and creates no diagram.

**Check:**

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

```check
tools: not-called: ea_diagram.create_diagram
reply: says: the impact is given as a table and report and a diagram is not offered from this skill
```

**Fails when:** The run builds a diagram of the affected elements in the model, uncommanded by a preview and an
agreed design.

## Invariants

TC-01, TC-03, TC-06 and TC-07 are the ones where a wrong run looks right: an unagreed rule, a partial count, an
unconfirmed match and an assumed vocabulary each produce a clean, confident report. Each fails on the call
sequence or the reply, not on the model, which is unchanged in every case. They do not show the figures are
correct for a customer's model; that depends on the rule, which the person owns.

## Headings not covered

- **When to use**, **See also**, **Verify in EA's UI**: orientation and shared boilerplate, nothing to test.
- **The gap this closes**: context for the four references.
- **Failure modes you will hit**: restates cases above.

## Findings

None yet. The operations these cases call are new; the first live run on a Westbrook copy is owed (SQL dialect
and timing), and any case that disagrees with what the operation returns is a finding for the skill or for the
operation.

---
name: ea-architecture-analysis
description: Answer architecture questions about a Sparx EA model with counted, reproducible results instead of hand-walked queries -- what a change reaches (impact of retiring or changing something), how far a set of elements is traced along a chain of relationships (traceability coverage), what differs between an as-is and a to-be architecture, and where the model is structurally fragile (most-connected elements, single points of failure, dependencies on deprecated or retired elements). Each question agrees its rule with the person before it runs, reads the guards, and ends in a change-board report. Use when someone asks "what breaks if we retire X", "how much of Y is traced to Z", "what changes between the current and target state", or "what are we most dependent on".
---

# Architecture analysis on a Sparx EA model

*Tools: `ea_analyze(operation="analyze_impact"|"measure_traceability_coverage"|"compare_states"|"assess_structural_risk", params={...})`,
`ea_analyze(operation="summarize_connector_patterns", params={})`,
`ea_analyze(operation="get_element_business_view", params={...})`,
`ea_mdg(operation="resolve_display_term", params={...})` (AI Power Tools for Sparx EA, v3.6.6+)*

This skill is read-only. No call below creates, updates or deletes anything. The one optional write
(recording a finding in a tag) is not made here; it goes through `ea-modeling` with its own yes.

Run the `ea-start-here` preflight first if you have not this session: is the server alive, which model
is open, which technologies are loaded. This skill assumes that is done.

## When to use

- "What breaks, or who is affected, if we retire, replace or change this?" A change with a blast radius.
- "How much of the model is traced?" Requirements to applications, applications to infrastructure,
  capabilities to the things that realize them. A share, with the gaps listed.
- "What is different between the current state and the target state?" Two packages, a baseline, or a
  lifecycle tag.
- "What are we most dependent on?" The most-connected elements, the ones the rest depends on alone, and
  everything that depends on something deprecated or retired.

**Not for:** cleaning up decay or deciding whether one element is safe to delete (`ea-model-hygiene`, section 2);
tracing from one element along one relationship type (`get_traceability_tree`, see `ea-model-hygiene`
section 6); a count over a tagged value (`ea-stakeholder-reporting`); a rule that must hold standingly
(`ea-validation`).

## The gap this closes

The graph operations take one start element, one connector set and one direction per call. A question
about a whole change, a whole set or a whole architecture used to mean assembling many calls, writing
SQL by hand and counting the result in your head. These four operations do the walking and the counting
in one deterministic pass over one load of the connectors. What stays with you is the part that needs
judgment: choosing the rule, confirming which element was meant, deciding what a mismatch means, saying
what is significant, and writing it down for the board.

| Question | Operation | Reference |
|---|---|---|
| What does this change reach? | `analyze_impact` | [`references/impact-of-a-change.md`](references/impact-of-a-change.md) |
| How much is traced along this chain? | `measure_traceability_coverage` | [`references/traceability-coverage.md`](references/traceability-coverage.md) |
| What differs between as-is and to-be? | `compare_states` | [`references/as-is-to-to-be.md`](references/as-is-to-to-be.md) |
| Where is the architecture fragile? | `assess_structural_risk` | [`references/structural-risk.md`](references/structural-risk.md) |

Read the reference for the question before the first call. Each one has the inputs, the output, a worked
run and the traps. This file holds what is the same for all four.

---

## 1. Agree the rule before anything runs

Every operation here answers exactly the question its rule asks, and no other. "Impact" over `Uses`
connectors and "impact" over `realizes` connectors are different answers; a coverage chain of
requirement to component is a different figure from one of requirement to node. A result is only as
honest as the rule, and the person has to own the rule, so it is agreed first.

1. **Find what the model actually has.** Read the relationship vocabulary the model uses:

   ```
   ea_analyze(operation="summarize_connector_patterns", params={})
   ```

   It returns source stereotype, connector stereotype, target stereotype and a count. That is the list
   of connector types that exist between which kinds of elements. Read the technology as well
   (`ea_mdg(operation="get_mdg_from_runtime", params={"tech_id": "WBA"})`, with your technology's id)
   so you know what each stereotype and connector is for.

2. **Propose the rule in the person's words and in a table.** Name each connector type, in display
   terms, with a direction stated as a sentence ("follow Uses from the application to what it uses",
   "follow Uses backwards, to what uses the application"). Say what each choice includes and leaves
   out. A rule is a list of connector types, each with its own direction, and a depth.

3. **Wait for a yes.** An explicit instruction that already names the rule ("what depends on the
   Account Master through Uses connectors, three hops") counts as agreement for that rule. A vague one
   ("what is affected") does not: propose, then ask. Do not run a default rule and report it as the
   answer.

4. **Say what the rule leaves out.** A rule over `Uses` does not follow containment (an element inside a
   package or under a parent), diagram placement, or connectors of a type nobody listed. Name it in one
   line before running, because the report will not show what the walk never looked at.

5. **Run, then re-state the rule in the report.** Every operation echoes its rule back. Quote the echo,
   not your memory of what was agreed.

A rule the person changes after seeing a result is a new run, with a new report. Do not edit the old
figure to fit.

---

## 2. Read the guards on every result

Every operation that walks the graph is bounded: a depth between 1 and 10, a node limit (`max_nodes`,
default 2000) and a wall-clock limit (`wall_clock_ms`, default 8000). The result carries `guards`, and
`truncated: true` with `truncated_by` names the guard that fired.

**A result with `truncated: true` is partial.** It is not an answer to the question; it is the part of
the answer the guard allowed. Do all three:

- Do not quote a count from it as if it were total. Say "at least" or say it is partial.
- Say which guard fired, and what narrowing would help: fewer connector types, a smaller scope or a
  lower depth. Raise `max_nodes` or `wall_clock_ms` only when the person accepts a longer run.
- Re-run with the narrower rule, agree it, and report the complete result.

`depth_reached` against `depth` tells you whether the walk ran out of graph or ran out of depth. A walk
that reached its depth limit with elements still at the frontier has more to find; say so.

**An element a guard stopped before it was evaluated is not in any count as "untraced" or "unaffected".**
Coverage reports it as `not_evaluated`, and the counts still add up to the denominator, so the missing
part is visible. Quote that row.

---

## 3. Use display terms

The person reads "Business Application", not `WBABusinessApplication`; "Depends on", not the connector
stereotype. Take the labels from the technology, as `ea-stakeholder-reporting` does:

- an element's business kind and its tags in business terms: `get_element_business_view`
- a stereotype, a tag or a connector: `resolve_display_term` with `kind` set to `stereotype`,
  `tagged_value` or `connector_stereotype`

When `found` is false, derive the label (split the camelCase name, drop the technology prefix) rather
than showing the technical name. Keep the technical name beside it once, in the rule table, so the
person can see what was run.

---

## 4. The report

Write the answer in the standard stakeholder report format, in
[`../ea-stakeholder-reporting/references/standard-report-format.md`](../ea-stakeholder-reporting/references/standard-report-format.md):
the question as asked, scope, technology and run date, the figure as "X of N", the table, completeness,
the elements counted, how counted, and what was not checked. Use that layout so two runs a month apart
can be put side by side.

For a change board, add two parts, and keep them apart because one is measured and one is judged:

**The rule that was run.** The echoed rule from the result, in display terms, with the guards and
whether anything was truncated. This is a fact.

**Reading (the AI's interpretation).** What the figures mean for the decision in front of the board: which
affected elements matter most and why, which gaps are structural and which look like missing data, what
is probably noise, what to look at next. Label it as a reading. Never put a conclusion in the figure
section, and never present a figure that rests on an unconfirmed element match as if it were certain.

Completeness is the same discipline as before a roll-up: a figure grouped by a tag is only as good as the
share of elements that carry the tag. `analyze_impact` counts the elements with the tag missing
(`unknown_tag_counts`); report them as unknown, never as a value.

---

## 5. Say only what you checked

State a count, or "none", only after the call that shows it. "Nothing depends on it" needs a rule that
covered the connectors that could carry a dependency, an upstream direction, and a result that was not
truncated. If any of the three is missing, say what was not established instead.

An element can carry two stereotypes and can be named the same as another. Say which element you mean by
its id or GUID, not by its name alone, whenever two share a name. Pairs matched by name in as-is to
to-be are exactly the ones the person has to see.

---

## 6. What this version does not do

- **No impact diagram.** The result is a table and a report. Drawing the affected elements is a separate
  piece of work through `ea-diagram-composition`, with its own preview, and is not offered from here.
  If the person asks, say it is not offered yet and give the table.
- **No rule is written to the model.** A coverage chain can become a validation rule (below), but turning
  it into one is a separate step with the person, through `ea-ruleset-author`.
- **No built-in lifecycle vocabulary.** What counts as deprecated or retired is the person's call, run by run.
- **Betweenness only on request.** It costs the most on a large model.

**A coverage chain is a rule you can keep.** The chain you agree for traceability coverage has the same
format as the `chain` rule type in a validation ruleset (`ea-ruleset-author`, `ea-validation`): ordered
hops of connector types, a direction and the element stereotypes each hop lands on. One evaluator gives
both the same meaning of "reaches". So when the person says "we should check this every month", the chain
they just agreed becomes a ruleset rule by copying it, not by rewriting it. Offer that in one line after
the report and do nothing further without a yes.

---

## Failure modes you will hit

- **A confident figure from an unagreed rule.** The run worked and the number is right for a rule nobody
  chose. The fix is section 1, not a better report.
- **`truncated` ignored.** A partial result quoted as total. Check `guards` before the first sentence.
- **A direction chosen to match the wording, not the model.** "Depends on" can be a connector drawn from
  the dependent to the dependency or the reverse, depending on the technology. Read one real connector
  in each direction before choosing, and put the chosen direction into the rule in words.
- **A technology with no connector type for the relationship.** If the model draws the relationship as
  diagram placement or containment, no connector rule will find it. Say so; do not report zero.
- **Two elements with one name.** Matched by name, the pair is wrong or refused. Use ids, and put the
  ambiguity to the person.
- **An empty result read as "none".** An empty `affected` list over a rule that follows a connector type
  nobody uses is the model's silence, not the architecture's. Check the rule against
  `summarize_connector_patterns` before reporting zero.

## See also

- **ea-stakeholder-reporting** -- the report format, display terms, and the coverage discipline for tagged values.
- **ea-model-hygiene** -- pre-delete safety and which traversal operation to use for a single element.
- **ea-validation**, **ea-ruleset-author** -- keeping a chain as a standing rule.
- **ea-change-management** -- a baseline of the current state, which `compare_states` can read as its as-is side.

## Verify in EA's UI

EA reports success it has not earned, and reports failure as a modal dialog that blocks the
COM connection rather than as an error you can catch. Neither shows up in a tool response.

- **If a call seems to hang, screenshot EA and read the dialog before concluding anything.**
  It names the cause. Dismiss from the front. Dialogs stack, and a later call can be queued
  behind one raised by an earlier one. Windows reporting EA as "Responding" means nothing.
- **This skill edits no model and draws no diagram.** If a result names an element you want to show the
  person in EA, open it and look rather than describing it from the result.
- **Without computer use**, say so. Ask the user to paste a screenshot of the EA window or
  dialog into the conversation, read the cause from it, and ask the user to dismiss the dialog
  before you retry. Never report a hang you have not diagnosed.

Full procedure: [`../_shared/references/ea-ui-verification.md`](../_shared/references/ea-ui-verification.md)

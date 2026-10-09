---
name: ea-stakeholder-reporting
description: Turn a Sparx EA model into an answer a non-modeller can act on -- portfolio roll-ups by tagged value, plain-language element summaries, and business-facing display terms. Use when someone asks "how many X are Y", "what's mission-critical", "what's in scope for [a regulation]", or wants a model fact stated in business language instead of stereotype/tag names, and especially before quoting any count drawn from a tagged value.
---

# Reporting to stakeholders from a Sparx EA model

*Tools: `ea_analyze(operation="get_element_business_view"|"summarize_tagged_value_usage"|"summarize_stereotype_usage", params={...})`,
`ea_repository(operation="aggregate_portfolio", params={...})`,
`ea_mdg(operation="resolve_display_term", params={...})` (AI Power Tools for EA, v3.6.0+)*

This skill is read-only. None of the calls below create, update, or delete anything, and
none require a write confirmation. If a task built on this skill ever needs a scratch
element to demonstrate something, use a package named exactly `_sl44_scratch` and delete
it when done -- but the workflows here don't need one.

Run the `ea-start-here` preflight first if you haven't already this session (is the server
alive, which model is open, which technologies are active). This skill assumes that part
is done.

## When to use

- A stakeholder asks a counting or grouping question: "how many applications are
  mission-critical", "what's being sunset this year", "what's in PCI scope".
- You need to hand someone a fact about one specific system without making them read
  stereotype names or tag keys.
- Before you present any number derived from a tagged value, full stop -- coverage checking
  belongs in front of every roll-up, not just the ones that look suspicious.

**When to reach for `ea-reporting-database` instead.** This skill answers a question by asking EA
directly, which is right for a question or two. Build the reporting layer when the question spans
the whole model, when the same questions recur and someone wants a refreshable source for Power BI,
or when a figure is disputed and has to be checked against the repository: the layer has one table
per stereotype with its tags as columns, and `check_business_layer` compares every cell with an
independent read through EA. See `../ea-reporting-database/SKILL.md`.

## The gap this closes

An architect has a model. A stakeholder wants an answer in their own language: "Business
Application", not `WBABusinessApplication`; "22 mission-critical apps", not a stereotype
query. The model has the data. The gap is translation, plus one thing translation alone
doesn't fix: **a roll-up is only as honest as the tagged value is complete**, and nothing
in the tool output warns you when it isn't. That warning is on you.

---

## Step 0: check coverage before you quote a number

This is the most valuable habit in this skill. A roll-up over a tag that is only set on
some elements of a type produces a confident, wrong number -- it doesn't fail, it doesn't
warn, it just answers with whatever fraction of the data happens to be populated.

Verified against the live Westbrook Bank model (all counts below are real, not
illustrative):

| Stereotype | Total elements | `criticality` | `lifecycle` | `businessOwner` | `technicalOwner` | `dataClassification` |
|---|---|---|---|---|---|---|
| `WBABusinessApplication` | 52 | 52/52 | 52/52 | 42/52 | 44/52 | 45/52 |
| `WBAVendorSystem` | 35 | 35/35 | 35/35 | 35/35 | 35/35 (see note) | 35/35 |
| `WBADataAsset` | 12 | 0/12 | 0/12 | 0/12 | 0/12 | 12/12 |
| `WBABusinessService` | 8 | 0/8 (real) | 8/8 | 0/8 (real) | 0/8 (real) | 0/8 (real) |

Three genuinely different coverage failures live in that table, and they look identical
if you don't check:

1. **`WBADataAsset` and `criticality`/`lifecycle`/`businessOwner`/`technicalOwner`.** The
   tag isn't set on a single one of the 12 elements. It doesn't show up at all in
   `summarize_tagged_value_usage(params={"stereotype": "WBADataAsset"})` -- there's no
   zero-count row, the tag name is simply absent from the output. A roll-up call
   (`aggregate_portfolio`) over this combination returns `"total_elements": 0, "groups": []`,
   which reads exactly like "no data assets exist" instead of "this type doesn't track
   criticality." See `references/coverage-data.md` for the full transcript.
2. **`WBABusinessService` and everything except `lifecycle`.** The tag *is* set on all 8
   elements -- but the value is an empty string on every one of them. A check that only
   asks "is the tag present" reports 100% coverage. The real, usable coverage is 0%, and
   `populated_count` is the figure that shows it.
3. **`WBABusinessApplication` and the ownership/classification tags.** Real elements, real
   gaps: `businessOwner` is missing on 10 of 52, `technicalOwner` on 8, `dataClassification`
   on 7, `regulatoryScope` on 10. `criticality` and `lifecycle` happen to be fully
   populated here. Nothing about the stereotype tells you which tags will be complete --
   you have to check each one.

**The check, every time, before the roll-up:**

```
ea_analyze(operation="summarize_stereotype_usage", params={})
```

gives you the true denominator per stereotype (the counts in the table's second column
came from here). Then:

```
ea_analyze(operation="summarize_tagged_value_usage", params={"stereotype": "WBABusinessApplication"})
```

gives you, per tag, a `count`, a `populated_count` and the `distinct_value_count` /
`sample_values`. `count` is how many tag rows exist; EA adds the tag when the stereotype is
applied, filled in or not, so it is not coverage. `populated_count` is how many
have a non-blank value, and that is the coverage figure. Read it as: does `populated_count`
equal the denominator? If not, don't present the roll-up as complete -- say what fraction it
covers.

The `technicalOwner` note for `WBAVendorSystem`: coverage is structurally 35/35, but 8
real assignments to one team are split across two spellings --
`Infrastructure & Cloud Team` (6) and `Infrastructure &amp; Cloud Team` (2), an
HTML-entity-encoded ampersand that never got cleaned up on import. A `technicalOwner`
roll-up here reports two teams with 6 and 2 systems each, when the true answer is one team
with 8. Coverage counting misses this entirely -- it's a distinct-value problem, not a
blank-value problem. Full detail in `references/coverage-data.md`.

---

## Portfolio roll-ups: `aggregate_portfolio`

```
ea_repository(operation="aggregate_portfolio", params={
  "stereotype": "WBABusinessApplication",
  "group_by_tag": "criticality"
})
```

Real result against the live model, 52 elements:

| Criticality | Count |
|---|---|
| Business-Critical | 22 |
| Mission-Critical | 14 |
| Standard | 8 |
| Important | 8 |

That's a complete answer here because `criticality` has no coverage gap on this
stereotype (Step 0 confirmed it) -- say so, e.g. "22 of 52 business applications are
Business-Critical" rather than manufacturing false precision if a gap existed.

Useful, verified behavior of this operation:

- **`count_only: true`** drops the per-element `elements` list and returns just the
  group counts -- use it once you've confirmed the elements aren't needed, to keep the
  response small.
- **`package_id`** scopes the roll-up to one package's subtree. Against the Westbrook
  demo, the whole-repository count for `WBABusinessApplication` x `criticality` is 52;
  scoped to the "Westbrook Bank" root package it drops to 45 -- the other 7 live
  elsewhere in the repository (a scratch/test area, in this case). Scope explicitly
  when a stakeholder asked about one line of business, not the whole repository.
- **`group_by_tag` is case-insensitive** (`"Criticality"` and `"criticality"` return
  identical results) -- don't spend time getting the case exactly right.
- **A misspelled or non-existent `stereotype` returns the same shape as a real
  stereotype with zero coverage on that tag**: `{"total_elements": 0, "groups": []}`.
  There is no separate "stereotype not found" error. If a roll-up comes back empty,
  confirm the stereotype name against `summarize_stereotype_usage` before concluding
  anything about the data.
- A tag that holds **several values in one string** (Westbrook's `regulatoryScope`:
  `"GLBA, FFIEC"`) is grouped whole by default, so `"GLBA"` and `"GLBA, FFIEC"` are separate
  groups and the `"GLBA"` group alone undercounts. The response's `multi_valued_count` says
  how many of the matched elements hold a comma-joined value. When it is not 0, pass
  `split_values: true`: each value is split on commas and the element is counted under each
  part, so the `"GLBA"` group counts every element in GLBA scope. Group counts then sum to
  more than `total_elements`, so quote each group against `total_elements`, not against the
  sum. See `references/coverage-data.md` for the worked numbers.

---

## Business view: `get_element_business_view`

```
ea_analyze(operation="get_element_business_view", params={"element_id": 91})
```

This is the per-element view: every tag with its value, and the element's connections.
For a technology your organization built, each `label` is the tag's technical name, and
`type` and `target_type` are the stereotype's technical name unless the technology's XML
was parsed this session (see Display terms below). Translate them before handing the result
to a stakeholder.
Result for a well-populated `WBABusinessApplication`:

```json
{
  "name": "Westbrook Fraud Decision Engine",
  "type": "WBABusinessApplication",
  "properties": [
    {"label": "businessOwner", "value": "Fraud Risk Management", "technical_name": "businessOwner"},
    {"label": "criticality", "value": "Mission-Critical", "technical_name": "criticality"},
    {"label": "dataClassification", "value": "Confidential", "technical_name": "dataClassification"},
    {"label": "lifecycle", "value": "Current", "technical_name": "lifecycle"},
    {"label": "regulatoryScope", "value": "FFIEC", "technical_name": "regulatoryScope"},
    {"label": "technicalOwner", "value": "Risk Technology Team", "technical_name": "technicalOwner"}
  ],
  "connections": [
    {"direction": "uses", "label": "Uses", "target_name": "NICE Actimize Fraud Risk Management", "target_type": "WBAVendorSystem"}
  ]
}
```

One call gives everything a stakeholder summary needs. The label `Uses` is a connector
stereotype the WBA technology declares (the model stores it bare; see the canon reference,
section 6 -- do not prefix it `WBA::`).

**What happens when a tag isn't set:** the property is left out of the list entirely,
not shown with an empty value. A `WBADataAsset` element (which, per Step 0, never carries
`criticality`, `lifecycle`, `businessOwner`, or `technicalOwner`) returns only two
properties:

```json
{
  "name": "Customer Master Data",
  "type": "WBADataAsset",
  "properties": [
    {"label": "dataClassification", "value": "Confidential", "technical_name": "dataClassification"},
    {"label": "regulatoryScope", "value": "GLBA, FFIEC", "technical_name": "regulatoryScope"}
  ],
  "connections": []
}
```

Reading a short `properties` list, don't assume "not applicable" -- it may just mean
"never populated." When a stakeholder needs to know whether a field is missing versus
inapplicable, cross-check with Step 0's coverage numbers for that stereotype rather than
inferring it from one element's output.

---

## Display terms: `resolve_display_term`

```
ea_mdg(operation="resolve_display_term", params={"kind": "stereotype", "technical_name": "ApplicationComponent"})
-> {"alias": "Application", "mdg_id": "ArchiMate3", "found": true}
```

`kind` is one of `stereotype`, `tagged_value`, `connector_stereotype` and `diagram_type`. A
tag is `tagged_value`; there is no `tag`. A kind the server does not recognize is not
rejected: it comes back `found: false`, exactly like a genuine miss, so check the spelling
before concluding a term has no business name.

**It resolves terms from the server's own tables, not from the technology EA has loaded.**
Those tables cover languages that ship with EA, such as ArchiMate, plus the stereotypes of
any technology parsed with `ea_mdg(operation="parse_mdg_xml", ...)` in this session, which
adds them with their aliases. Nothing adds a technology's tags. So for a technology your
organization built, tags never resolve, and stereotypes resolve only after its XML has been
parsed this session. Run on 2026-10-08 against the 3.6.0 server source, with Westbrook's
technology standing in for yours and no XML parsed:

```
ea_mdg(operation="resolve_display_term", params={"kind": "stereotype", "technical_name": "WBABusinessApplication"})
-> {"alias": "WBABusinessApplication", "mdg_id": "", "found": false}
ea_mdg(operation="resolve_display_term", params={"kind": "tagged_value", "technical_name": "criticality"})
-> {"alias": "criticality", "mdg_id": "", "found": false}
```

`get_element_business_view` (`type`, each `label`, `target_type`) and `aggregate_portfolio`
(`alias`) take their labels from the same lookup, so for your own technology the tag labels
are always technical names, and the stereotype names are too unless its XML was parsed.
When you need a business term:

- **A stereotype:** use the alias your technology declares. `ea_mdg(operation="get_mdg_from_runtime",
  params={"tech_id": "<id>"})` returns each stereotype with its `alias` without changing what
  the lookup knows; the reporting layer names its tables by the same alias.
- **A tag, or a stereotype with no alias:** derive it. Split the camelCase name
  (`businessOwner` -> "Business Owner") and drop the technology's prefix from a stereotype
  (`WBABusinessApplication` -> "Business Application").
- Call `resolve_display_term` for terms from a language that ships with EA, or for a
  stereotype of a technology parsed this session, where it does find them.

---

## Failure modes you will actually hit

- **Empty roll-up, ambiguous cause.** `{"total_elements": 0, "groups": []}` means either
  "this stereotype doesn't exist" or "this stereotype exists but never sets this tag."
  Confirm the stereotype name against `summarize_stereotype_usage` before reporting a
  zero to anyone.
- **Blank counts as a value.** An empty string is a legitimate bucket
  (`aggregate_portfolio` will show `{"value": "", "count": N}`), and it looks like real
  data if you don't notice it's blank. Always scan for a `""` group before reading the
  rest of the table.
- **"None" is not the same as blank.** Westbrook's `regulatoryScope` uses the literal
  value `"None"` (explicitly assessed, not in scope for anything) alongside blank
  (never assessed at all). Collapsing the two loses a real distinction -- "not
  applicable" and "not yet reviewed" are different stakeholder answers.
- **Encoding drift splits one real bucket into two.** `Infrastructure & Cloud Team` /
  `Infrastructure &amp; Cloud Team` is the concrete case here; treat any roll-up with a
  suspiciously large number of near-duplicate group values as a signal to check for this
  before reporting team-by-team counts.
- **Comma-joined multi-value tags undercount a whole-value roll-up.** When
  `multi_valued_count` is not 0, roll up again with `split_values: true`; see the
  `regulatoryScope` example above.
- **A missing property in `get_element_business_view` doesn't self-explain.** It's silent
  on whether the field is unset or not tracked for that stereotype. Cross-check against
  `summarize_tagged_value_usage` for that stereotype when it matters.
- **Your own technology's terms come back as technical names.** `resolve_display_term`,
  the business view and the roll-up know the languages that ship with EA and the stereotypes
  of a technology parsed this session, never its tags. Take a stereotype's alias from
  `get_mdg_from_runtime` and derive a tag's label, as above.

Full worked numbers, including the complete per-stereotype coverage matrix and the
`regulatoryScope` multi-value breakdown, are in `references/coverage-data.md`.

---

## A note on latency

Every operation in this skill is a repository read through the MCP server, not a UI
action -- there's no dialog to wait out and no "(Not Responding)" state to watch for.
If a task built on top of this skill also drives the EA desktop UI directly (opening a
diagram to walk a stakeholder through it, for example), see
`../_shared/references/latency.md` for wait guidance before screenshotting; it doesn't
apply to the calls in this skill itself.

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

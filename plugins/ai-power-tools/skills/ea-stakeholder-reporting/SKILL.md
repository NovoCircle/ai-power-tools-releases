---
name: ea-stakeholder-reporting
description: Turn a Sparx EA model into an answer a non-modeler can act on -- portfolio roll-ups by tagged value, plain-language element and diagram summaries, and business-facing display terms. Use when someone asks "how many X are Y", "what's mission-critical", "what's in scope for [a regulation]", or wants a model fact stated in business language instead of stereotype/tag names, and especially before quoting any count drawn from a tagged value.
---

# Reporting to stakeholders from a Sparx EA model

*Tools: `ea_analyze(operation="get_element_business_view"|"summarize_tagged_value_usage"|"summarize_stereotype_usage", params={...})`,
`ea_repository(operation="aggregate_portfolio", params={...})`,
`ea_mdg(operation="resolve_display_term", params={...})` (AI Power Tools for EA, v3.6.4+; `resolve_display_term` reading the technology EA has loaded needs 3.6.5)*

This skill is read-only. None of the calls below create, update, or delete anything, and
none require a write confirmation.

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
Application", not `WBABusinessApplication`; "12 mission-critical apps", not a stereotype
query. The model has the data. The gap is translation, plus one thing translation alone
doesn't fix: **a roll-up is only as honest as the tagged value is complete**, and nothing
in the tool output warns you when it isn't. That warning is on you.

---

## Step 0: check coverage before you quote a number

This is the most valuable habit in this skill. A roll-up over a tag that is only set on
some elements of a type produces a confident, wrong number -- it doesn't fail, it doesn't
warn, it just answers with whatever fraction of the data happens to be populated.

Measured on 2026-11-16 on a copy of the Westbrook Bank demo model (EA 17.1 build 1716, server
3.6.5, technology `WBA` loaded). It is our demo model, not one your organization has, so read the
counts as the shape of an answer and run Step 0 on your own model:

| Stereotype | Total elements | `criticality` | `lifecycle` | `businessOwner` | `technicalOwner` | `dataClassification` |
|---|---|---|---|---|---|---|
| `WBABusinessApplication` | 47 | 47/47 | 47/47 | 44/47 | 46/47 | 47/47 |
| `WBAVendorSystem` | 35 | 35/35 | 35/35 | 35/35 | 35/35 (see note) | 35/35 |
| `WBADataAsset` | 12 | 0/12 | 0/12 | 0/12 | 0/12 | 12/12 |
| `WBABusinessService` | 8 | 0/8 (real) | 8/8 | 0/8 (real) | 0/8 (real) | 0/8 (real) |

The 47 include one element, Core Deposit System of Record, that carries the stereotype second
(see "Say only what you checked"). Three genuinely different coverage failures live in that
table, and they look identical if you don't check:

1. **`WBADataAsset` and `criticality`/`lifecycle`/`businessOwner`/`technicalOwner`.** The
   tag isn't set on a single one of the 12 elements. It doesn't show up at all in
   `summarize_tagged_value_usage(params={"stereotype": "WBADataAsset"})` -- there's no
   zero-count row, the tag name is simply absent from the output. A roll-up call
   (`aggregate_portfolio`) over this combination returns `"total_elements": 0, "groups": []`,
   which reads exactly like "no data assets exist" instead of "this type doesn't track
   criticality." See `references/coverage-data.md` for the full transcript.
2. **`WBABusinessService` and everything except `lifecycle`.** The tag *is* set on all 8
   elements -- but the value is blank (an empty string, or no value) on every one of them. A check that only
   asks "is the tag present" reports 100% coverage. The real, usable coverage is 0%, and
   `populated_count` is the figure that shows it.
3. **`WBABusinessApplication` and the ownership and regulatory-scope tags.** Real elements, real
   gaps: `businessOwner` is missing on 3 of 47, `technicalOwner` on 1, `regulatoryScope` on 3.
   `criticality`, `lifecycle` and `dataClassification` happen to be fully populated here. Nothing about the stereotype tells you which tags will be complete --
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

The `technicalOwner` note for `WBAVendorSystem`: coverage is structurally 35/35, but 8 real
assignments to one team are split across two spellings (`Infrastructure & Cloud Team` 6,
`Infrastructure &amp; Cloud Team` 2). Coverage counting misses it: this is a distinct-value
problem, not a blank-value one. Detail in `references/coverage-data.md`.

---

## Say only what you checked

State a count, or "none", only after the query that shows it; otherwise say it was not checked.
"Customer Master Data has no connections" needs a `get_element_business_view` call behind it, and
"11 applications are under both GLBA and FFIEC" needs a count of the elements in both.

**An element with two stereotypes** belongs to both populations, and two counts can treat it
differently: a count on the primary stereotype leaves it out of the second type, a roll-up over
every element bound to that stereotype includes it (Westbrook's Core Deposit System of Record is
a System of Record and a Business Application, so one count includes it and the other does not). Pick the basis the person
asked about, name the element, and say which count you gave.

---

## Portfolio roll-ups: `aggregate_portfolio`

```
ea_repository(operation="aggregate_portfolio", params={
  "stereotype": "WBABusinessApplication",
  "group_by_tag": "criticality"
})
```

On the same demo model, 47 elements (the roll-up counts each element once, including Core Deposit
System of Record):

| Criticality | Count |
|---|---|
| Business-Critical | 21 |
| Mission-Critical | 12 |
| Standard | 8 |
| Important | 6 |

That's a complete answer here because `criticality` has no coverage gap on this
stereotype (Step 0 confirmed it) -- say so, e.g. "21 of 47 business applications are
Business-Critical" (the counts in `references/coverage-data.md`) rather than manufacturing false precision if a gap existed.

Useful, verified behavior of this operation:

- **`count_only: true`** drops the per-element `elements` list and returns just the
  group counts -- use it once you've confirmed the elements aren't needed, to keep the
  response small.
- **`package_id`** scopes the roll-up to one package's subtree, so the count is lower than the
  whole-repository count whenever some elements of the type sit outside that package. Scope
  explicitly when a stakeholder asked about one line of business, and say which scope you used.
- **`group_by_tag` is case-insensitive** (`"Criticality"` and `"criticality"` return
  identical results) -- don't spend time getting the case exactly right.
- **A misspelled or non-existent `stereotype` returns the same shape as a real
  stereotype with zero coverage on that tag**: `{"total_elements": 0, "groups": []}`.
  There is no separate "stereotype not found" error. If a roll-up comes back empty,
  confirm the stereotype name against `summarize_stereotype_usage` before concluding
  anything about the data. The exception is a qualified `stereotype` (`WBA::WBABusinessApplication`
  or the profile name) that matches nothing: `stereotype_resolution.qualifier_unmatched` is true
  and `fqnames` shows what the bare name does carry (server 3.6.5 or later). A bare name that
  matches nothing still returns zero, so confirm names against `summarize_stereotype_usage` first.
- **Each element is counted once**, even when it carries two stereotypes, so the groups add up to
  `total_elements`. When that happens the result lists the elements in
  `multi_stereotype_elements` and says so in `note`; mention it to the reader instead of
  presenting the roll-up as clean.
- A tag that holds **several values in one string** (Westbrook's `regulatoryScope`:
  `"GLBA, FFIEC"`) is grouped whole by default, so `"GLBA"` and `"GLBA, FFIEC"` are separate
  groups and the `"GLBA"` group alone undercounts. The response's `multi_valued_count` says
  how many of the matched elements hold a comma-joined value. When it is not 0, pass
  `split_values: true`: each value is split on commas and the element is counted under each
  part, so the `"GLBA"` group counts every element in GLBA scope. Group counts then sum to
  more than `total_elements`, so quote each group against `total_elements`, not against the
  sum. See `references/coverage-data.md` for the worked numbers.

---

## The standard report format

When the person asks for "the standard stakeholder report format", or for an answer that must
compare with next month's, use [`references/standard-report-format.md`](references/standard-report-format.md):
question, scope, figure, completeness of each property behind it (filled over total, from Step 0),
elements counted, run date and technology version, and the same answer as a table a dashboard reads.

**A report without the Author line.** EA's built-in report templates print the modeler's login name
as each element's author, and the server can't change that. For a report that leaves the team, build
a copy of the template without it and name it in `generate_report`:
[`references/report-without-author.md`](references/report-without-author.md).

---

## Business view: `get_element_business_view`

```
ea_analyze(operation="get_element_business_view", params={"element_id": 91})
```

This is the per-element view: every tag with its value, and the element's connections.
Each `label`, `type` and `target_type` comes from the display-term lookup (see Display terms
below). On server 3.6.5 or later, with your technology loaded in EA, it is the alias or
description the technology declares; a term the technology does not declare stays a technical
name, so check the labels before handing the result to a stakeholder. The samples below were
captured on 2026-11-16 on server 3.6.5 against the Westbrook Bank demo model with `WBA` loaded, and
are pasted as measured.

The samples below show everything the reply holds. `raw_stereotype` is the stereotype as EA
stores it: the technical name to quote when `type` has been replaced by an alias.
`raw_object_type` is the element's EA type, such as `Component`. `type_description` is an empty
string for the demo technology.

Result for a well-populated `WBABusinessApplication`:

```json
{
  "element_id": 91,
  "name": "Westbrook Fraud Decision Engine",
  "type": "Business Application",
  "type_description": "",
  "raw_stereotype": "WBABusinessApplication",
  "raw_object_type": "Component",
  "properties": [
    {"label": "business Owner", "value": "Fraud Risk Management", "technical_name": "businessOwner"},
    {"label": "criticality", "value": "Mission-Critical", "technical_name": "criticality"},
    {"label": "data Classification", "value": "Confidential", "technical_name": "dataClassification"},
    {"label": "lifecycle", "value": "Current", "technical_name": "lifecycle"},
    {"label": "regulatory Scope", "value": "FFIEC", "technical_name": "regulatoryScope"},
    {"label": "technical Owner", "value": "Risk Technology Team", "technical_name": "technicalOwner"}
  ],
  "connections": [
    {"direction": "uses", "label": "Uses", "target_name": "NICE Actimize Fraud Risk Management", "target_type": "Vendor System"},
    {"direction": "uses", "label": "Realisation", "target_name": "REQ-004 Fraud Screening on Every Loan Application", "target_type": "Requirement"},
    {"direction": "uses", "label": "Dependency", "target_name": "NICE Actimize Fraud Risk Management", "target_type": "Vendor System"}
  ]
}
```

One call gives everything a stakeholder summary needs. `connections` lists every connector the
element has, one entry each, in both directions (`uses` when it starts at the element, `used_by`
when it ends there); this element has three, all starting at it. The label `Uses` is a connector
stereotype the WBA technology declares (the model stores it bare; see the canon reference,
section 6 -- do not prefix it `WBA::`). A connector with no stereotype shows its base type
(`Realisation`, `Dependency`). The business view shows the label without the profile
qualifier, and uses the connector stereotype's alias when it has one.

**What happens when a tag isn't set:** the property is left out of the list entirely,
not shown with an empty value. A `WBADataAsset` element (which, per Step 0, never carries
`criticality`, `lifecycle`, `businessOwner`, or `technicalOwner`) returns only two
properties:

```json
{
  "element_id": 163,
  "name": "Customer Master Data",
  "type": "Data Asset",
  "type_description": "",
  "raw_stereotype": "WBADataAsset",
  "raw_object_type": "Object",
  "properties": [
    {"label": "data Classification", "value": "Confidential", "technical_name": "dataClassification"},
    {"label": "regulatory Scope", "value": "GLBA, FFIEC", "technical_name": "regulatoryScope"}
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
-> {"technical_name": "ApplicationComponent", "alias": "Application", "description": "", "mdg_id": "ArchiMate3", "kind": "stereotype", "found": true}
```

`resolve_display_term` reads the technology EA has loaded, so a stereotype, a tag description or
a diagram type of your own technology resolves to the alias or description the technology
declares (server 3.6.5 or later). A term the technology does not declare falls back to the
built-in tables, and then to the technical name with `found: false`. The result has
`technical_name`, `alias`, `description`, `mdg_id`, `kind` and `found`.

`kind` is one of `stereotype`, `tagged_value`, `connector_stereotype` and `diagram_type`. A tag
is `tagged_value`; there is no `tag`. Any other value returns `ok: false` with
`error: "invalid_kind"` and `valid_kinds`, so a misspelled kind is no longer a silent miss.

When `found` is false, derive the label by splitting the camelCase name (`businessOwner` ->
"Business Owner") and dropping the technology prefix from a stereotype (`WBABusinessApplication`
-> "Business Application"). On the demo model a found tag alias keeps a lowercase first word
(`business Owner`), so check the case before you quote one. `get_element_business_view` and
`aggregate_portfolio` take their labels from the same lookup. Before 3.6.5 the lookup read only the
server's own tables, so a technology's tags never resolved; `get_mdg_from_runtime` read the alias.

---

## Diagram descriptions: a diagram in words

*Uses `ea_diagram(operation="get_diagram_manifest"|"audit_diagram_descriptions", params={...})`, which arrive
with server 3.6.4. On an older server these operations are unknown: say so and do not improvise a
description from shapes.*

A diagram can carry a **description**: plain text in the diagram's Notes that says what the diagram
shows, in the organization's business terms, with nothing about how it is drawn. It is written for
readers who cannot see the picture or do not have EA: a screen reader, a document, an AI assistant,
a stakeholder who asks "what is on this diagram?". Use it as the plain-language answer to that
question, instead of reading shapes and stereotype names aloud.

**How to read one.** The first sentence is a one-line summary (at most 150 characters). The body
follows, grouped by the diagram's groupings, with every element by its business kind and name and
every relationship as a sentence ("Customer Portal uses Payments Gateway"). Two marker lines
bracket the generated text; anything a person wrote above or below them is theirs and stays as it
is. Quote the words, not the marker lines.

```
ea_diagram(operation="audit_diagram_descriptions", params={"package_id": 10})
ea_diagram(operation="get_diagram_manifest", params={"diagram_id": 4, "include_svg": False})
```

(The ids are the Westbrook Bank copy's.) The audit is read-only and says whether the words can be
trusted; the manifest's `description` holds them, with `description_source` saying whether they are
the stored words (`notes`) or were generated just now (`generated`).

**Check the status before you quote, as you check coverage before you quote a count.**

| Status | What you can say |
|---|---|
| `current`, or `edited` | The description matches the diagram (`edited`: a person adjusted the words). Quote it. |
| `stale`, `needs_decision` | The diagram has changed since the words were written. Say the description is out of date; do not present it as what the diagram shows now. |
| `older_generator`, `language_changed` | The generator or the technology version has changed since the words were written. Say the description is out of date and may not match what the diagram shows now. |
| `human_only` | A person wrote the Notes; no description was generated. Quote it as their text. |
| `empty` | There is no description; see below. |
| `broken_markers`, `technology_not_loaded` | The words cannot be checked. Say so; do not quote them as current. |

If the row is `incomplete`, the text leaves out elements or relationships the diagram holds
(`names_missing`, `relationships_missing`); tell the reader what it omits instead of presenting it
as the whole picture. That holds for a description a person wrote by hand as much as for a
generated one.

**A diagram with no description.** Ask for the manifest: with no stored description it generates
the words from the diagram, and nothing is written. Say that the text was generated for this answer
and is not stored. Storing it in the diagram's Notes is a model write, so it is not this skill's:
offer it in one line, and with the person's yes follow `../ea-import-export/SKILL.md` section 3c,
which previews first.

**An out-of-date description.** Do not refresh it from here. Say it is out of date, and
`update_diagram_description` (mode `refresh`) previews the new text without writing, because
`dry_run` is true unless you say otherwise. Writing it, and deciding what happens to a person's
edits, is `../ea-import-export/SKILL.md` section 3c.

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
- **A missing property in `get_element_business_view` doesn't self-explain.** It's silent
  on whether the field is unset or not tracked for that stereotype. Cross-check against
  `summarize_tagged_value_usage` for that stereotype when it matters.
- **A term with `found: false` has no alias in the loaded technology.** Derive it as above
  (split the camelCase name, drop the technology prefix) rather than showing the technical name.

Full worked numbers, including the complete per-stereotype coverage matrix and the
`regulatoryScope` multi-value breakdown, are in `references/coverage-data.md`.

## Verify in EA's UI

Every operation here is a repository read with no dialog to wait out; if you also drive EA's UI,
see `../_shared/references/latency.md` for wait guidance before screenshotting.

EA reports success it has not earned, and reports failure as a modal dialog that blocks the
COM connection rather than as an error you can catch. Neither shows up in a tool response.

- **If a call seems to hang, screenshot EA and read the dialog before concluding anything.**
  It names the cause. Dismiss from the front — dialogs stack, and a later call can be queued
  behind one raised by an earlier one. Windows reporting EA as "Responding" means nothing.
- **This skill creates no diagram.** If you open one to walk someone through it, reload it,
  screenshot it, and look: `ok: true` means rows were written, not that the result is readable.
- **Without computer use**, say so. Ask the user to paste a screenshot of the EA window or
  dialog into the conversation, read the cause from it, and ask the user to dismiss the dialog
  before you retry. Never report a hang you have not diagnosed or a diagram you have not seen.

Full procedure: [`../_shared/references/ea-ui-verification.md`](../_shared/references/ea-ui-verification.md)

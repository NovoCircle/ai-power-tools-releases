# The standard stakeholder report format

One layout for every answer drawn from the model, so two answers a month apart can be put side by
side. Use it when the person names it ("the standard stakeholder report format"), or when the answer
will be repeated or filed. Westbrook Bank figures below are an illustration; the reader's own
technology, stereotypes, tags and counts replace them.

The report is read-only work. Every figure in it follows the rules in `SKILL.md`: state a count only
after the query that shows it, and say what was not checked.

---

## 1. Where each part comes from

| Part | Source |
|---|---|
| Question | The person's words, unchanged |
| Scope | The package or packages asked about, or "whole repository"; the `package_id` passed to the roll-up |
| Figure | `aggregate_portfolio` (with `split_values: true` for a multi-value tag), quoted as "X of N" |
| Completeness | Per property the figure depends on: `populated_count` from `summarize_tagged_value_usage` over the stereotype's element count from `summarize_stereotype_usage` (Step 0). Filled means non-blank, never "the tag row exists". This is the populated-over-total rule the reporting database's census applies |
| Elements counted | The `elements` list of the roll-up (leave `count_only` off), with the key properties for each from `get_element_business_view` |
| Run date | The date of the run, from the session |
| Technology version | The technology's version as `ea_mdg(operation="get_mdg_from_runtime")` reports it; "not reported" if it gives none |
| How counted | One line: the stereotype counted, and any element carrying two stereotypes, named |

A property with no filled value is reported at 0 of N, not left out. A tag the type never carries
shows as "not recorded for this concept".

---

## 2. The Markdown form

```markdown
## <The question, as asked>

**Scope:** <packages, or whole repository>
**Technology:** <name> <version>   **Run:** <date>

**Figure:** <X> of <N> <concept, in business terms> <answer in a sentence>.

| <Group> | Count |
|---|---|
| ... | ... |

### Completeness

| Concept | Property | Filled | Total | Share |
|---|---|---|---|---|
| <concept> | <property in business terms> | <filled> | <total> | <percent> |

### Elements counted

| Name | Concept | <key property> | <key property> |
|---|---|---|---|
| ... | ... | ... | ... |

**How counted:** <the stereotype counted; an element with two stereotypes, named>.
**Not checked:** <anything the answer depends on that was not measured; "nothing" if all was>.
```

Example of the completeness part, with the owner gap visible:

```markdown
| Concept | Property | Filled | Total | Share |
|---|---|---|---|---|
| Data Asset | Business Owner | 0 | 12 | 0% |
| Data Asset | Data Classification | 12 | 12 | 100% |
```

---

## 3. The table form, for a dashboard

One row per figure, the same columns every run, so a month's rows stack:

| Column | Holds |
|---|---|
| `run_date` | ISO date |
| `technology` | Technology name and version |
| `scope` | Package path, or `whole repository` |
| `question` | The question as asked |
| `group` | The group the figure is for (a tag value), or empty for a single figure |
| `figure` | The count |
| `denominator` | N |
| `property` | The property the figure depends on |
| `filled` | Elements with that property non-blank |
| `total` | Elements of the concept in scope |

Elements counted go in a second table, one row per element: `run_date`, `question`, `name`, `concept`,
then one column per key property. Join the two on `run_date` and `question`.

```csv
run_date,technology,scope,question,group,figure,denominator,property,filled,total
2026-11-11,WBA 1.1.1,whole repository,How many business applications are mission-critical,Mission-Critical,11,46,criticality,46,46
```

A figure that rests on two properties gets one row per property, with the same `figure`.

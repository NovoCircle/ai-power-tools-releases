# Traceability coverage

How far each element of a set is traced along a chain of relationships: requirements to applications,
applications to infrastructure, capabilities to what realizes them. The figure is a share with its
denominator, the level each element reached, and the gap list. Westbrook Bank values are an
illustration; your technology's stereotypes and connectors replace them.

## 1. Settle the question first

| Decide | How |
|---|---|
| **The set** (the denominator) | A package, recursive or not, and the stereotypes whose elements are counted ("every Business Service under the Account Management package"). With no package, the whole model for those stereotypes |
| **The chain** | Ordered hops. Each hop names the connector types, a direction, and the stereotypes the hop must land on. Proposed from `summarize_connector_patterns` and the technology, agreed before the run (`SKILL.md`, section 1) |
| **Direct or through intermediates** | One connector per hop (default), or `indirect`, which lets a hop pass through other elements before it lands on the target kind, up to `max_depth` steps per hop |
| **What "traced" means** | Reaching the last hop. Say it in a sentence the person recognizes: "a service is traced when an application realizes it and that application runs on a node" |

**The chain is a sentence in order.** Write it back to the person as one: "Start from each Business
Service. Hop 1: follow `realizes` backwards to a Business Application. Hop 2: follow `Uses` forwards to a
Technology Node." Then the structure:

```json
[
  {"connector": {"connector_stereotypes": ["realizes"], "direction": "incoming"},
   "stereotype_one_of": ["WBA::WBABusinessApplication"],
   "label": "realized by an application"},
  {"connector": {"connector_stereotypes": ["Uses"], "direction": "outgoing"},
   "stereotype_one_of": ["WBA::WBATechnologyNode"],
   "label": "runs on a node"}
]
```

`direction` is `outgoing` (from a connector's source to its target), `incoming` (from target to source)
or `both`. `stereotype_one_of` is the hop's landing kinds; leave it out and any element lands. `label`
is the words the report shows for the level.

**This is the same format a validation `chain` rule uses.** The chain the person agrees here can become a
ruleset rule by copying it into the rule, unchanged, because one evaluator gives both the same meaning of
"reaches". After the report, offer that in one line ("this chain can be checked every month as a rule");
write nothing without a yes. See `ea-ruleset-author` for the rule and `ea-validation` for running it.

## 2. The call

```
ea_analyze(operation="measure_traceability_coverage", params={
  "scope": {"package_id": 11, "recursive": true, "stereotypes": ["WBA::WBABusinessService"]},
  "chain": [ ...the hops above... ],
  "indirect": false,
  "max_depth": 5
})
```

(The package id is the Westbrook copy's.) The result:

| Key | Holds |
|---|---|
| `denominator` | The number of elements in the set |
| `counts` | `traced`, `partial`, `untraced`, and `not_evaluated` when a guard stopped the run. These add up to the denominator |
| `levels` | One row per level: the level, its label (the hop's `label`), and how many elements reached it and no further. These add up to the denominator too |
| `gaps` | Every element that is not traced: its level, the hop it stopped at, and the elements it did reach |
| `chain` | The chain as run (echo it in the report) |
| `guards` | Depth, `max_nodes`, `wall_clock_ms`, `truncated`, `truncated_by` |

An element is **traced** when it reached the last hop, **partial** when it reached at least the first hop
but not the last, **untraced** when it reached none.

## 3. Read it before you write it

1. **Do the counts add up to the denominator?** They do by construction; if you are about to quote a
   figure that does not, you are quoting the wrong field.
2. **`not_evaluated` above zero** means a guard fired. The figure is partial: `SKILL.md`, section 2.
3. **Check the denominator is the set the person meant.** A set of zero elements is a wrong stereotype
   or package, not a model with nothing in it; confirm the name against `summarize_stereotype_usage`
   (`ea-stakeholder-reporting`, Step 0).
4. **Spot-check one traced and one untraced element** by hand with `get_traceability_tree` (see
   `ea-model-hygiene`, section 6) before you present the share. A wrong direction makes everything
   untraced and looks like a bad model.
5. **Look at the gap list for a pattern.** Gaps that are all in one package, or all missing the same
   hop, are one cause, not many.

## 4. The change-board report

Use the standard report format (`../../ea-stakeholder-reporting/references/standard-report-format.md`):

- **Question:** "How much of <the set> is traced to <the end of the chain>?"
- **Scope:** the package and the set, and the chain as a sentence.
- **Figure:** "X of N <business kind> are traced end to end" and the level table: for each level, the
  label and the count that stopped there.
- **Completeness:** the denominator, how it was formed, and that the counts add up to it.
- **Elements counted:** the gap list, by name and business kind, with the hop each stopped at.
- **How counted:** direct or indirect, the depth, the chain echoed in display terms.
- **Not checked:** relationships the chain does not follow, anything truncated, elements the technology
  would draw some other way.

Then, apart and labeled as a reading: where the break is (which hop loses the most elements), whether a
break looks like missing connectors or like a chain that does not fit how the model is drawn, and what to
fix first. Do not call an element "not realized" when the real finding is "the chain I used does not
describe this part of the model".

## 5. Traps

- **The figure is only as good as the chain.** A chain that omits a legitimate route shows a good model
  as poor. Agree it, and say what it leaves out.
- **Indirect changes the meaning.** With `indirect`, a hop can pass through intermediates, so an element
  three steps from an application can count as "realized by" it. Say which one was used, and never compare
  a direct run with an indirect one.
- **Elements that carry two stereotypes** count once in the set but can land as either kind on a hop.
  Name them.
- **A set bigger than the guard.** When the denominator itself exceeds `max_nodes`, the run evaluates the
  first part and says so (`not_evaluated`). Narrow the package instead of raising the limit blindly.
- **Do not turn a share into a verdict.** "62 percent traced" is a number. Whether that passes is the
  organization's rule, not yours.

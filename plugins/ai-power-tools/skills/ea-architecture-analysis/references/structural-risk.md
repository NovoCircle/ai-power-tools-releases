# Structural risk

Where an architecture is fragile: the most-connected elements, the single points of failure, and every
element that depends, within a few steps, on something deprecated or retired. Westbrook Bank values are an
illustration; your technology's stereotypes, connectors and lifecycle tag replace them.

## 1. Settle the question first

Four things come from the person. None has a default.

| Decide | How |
|---|---|
| **The scope** | A package, recursive or not, and the stereotypes whose elements are assessed. With no package, the whole model for those stereotypes |
| **The dependency connectors** | Which connector types mean "depends on" in this model. Propose from `summarize_connector_patterns` and the technology; agree before the run (`SKILL.md`, section 1). An empty list means every connector, which is rarely what a dependency question means, so name them |
| **The lifecycle tag, and which values mean deprecated or retired** | The tag that carries lifecycle (`lifecycle` in Westbrook) and the values the person counts as end-of-life (`Deprecated`, `Retired` in Westbrook). **Confirm the values every run.** The skill has no built-in vocabulary, and the values come from what the model holds (`summarize_tagged_value_usage` with the stereotype) and what the organization means by them |
| **The hops** | How far to look for a dependency on an end-of-life element: 1 to 10 steps. Say what it means ("an application that uses something that uses a retired service is two steps") |

Betweenness is a fourth measure and is **only run when the person asks for it**. It costs the most on a
large model, and the first three answer most questions.

## 2. The call

```
ea_analyze(operation="assess_structural_risk", params={
  "scope": {"package_id": 5, "recursive": true,
            "stereotypes": ["WBA::WBABusinessApplication", "WBA::WBAVendorSystem"]},
  "connector_types": ["Uses"],
  "lifecycle_tag": "lifecycle",
  "deprecated_values": ["Deprecated", "Retired"],
  "top_n": 10,
  "max_hops": 3,
  "include_betweenness": false
})
```

(The ids and values are the Westbrook copy's.) The result describes the graph of connectors with both ends
inside the scope:

| Key | Holds |
|---|---|
| `graph` | Nodes, connectors and connected pairs in the scope graph: the denominator for everything below |
| `degree` | The `top_n` elements by total connections, each with `in`, `out` and `total`, and the number of `isolated` elements with none |
| `single_points_of_failure` | Elements whose removal splits the scope graph: each with the sizes of the pieces it falls into without it and `elements_cut_off`, the number of elements separated from the largest piece |
| `betweenness` | Only with `include_betweenness`: the `top_n` by score. `null` when the wall clock ran out |
| `deprecated_dependencies` | Every in-scope element that reaches an element whose lifecycle value is one you listed, within `max_hops`: what it reaches, the distance, the path, and every element involved |
| `guards` | Hops, `max_nodes`, `wall_clock_ms`, `truncated`, `truncated_by` |

**What "single point of failure" means here, and no more.** It is a structural fact about the connectors
that were counted: removing this element disconnects the rest of the scope graph into pieces, taking the
connectors as undirected. It does not say the element is unreplaceable, that a failure is likely, or that
the connectors are the only way the pieces are tied. Say it as a structural finding.

## 3. Read it before you write it

1. **`guards.truncated`?** The scope was cut at `max_nodes`, or betweenness ran out of time. Say so.
2. **Look at `graph` first.** A scope with few connectors has little structure to find; a high `isolated`
   count means the model draws these relationships some other way (containment, diagram placement), so the
   dependency connectors are not the picture. Say that before ranking anything.
3. **Check the lifecycle values against the model.** `deprecated_dependencies` lists elements reaching a
   value you named. If a value is misspelled or the tag is blank on most elements, the list is short for the
   wrong reason. Report how many elements carry the tag at all (the completeness figure), as for any
   tagged-value roll-up.
4. **Deprecated elements outside the scope are still found.** The element that depends on them is in scope;
   the deprecated one may not be. Name both.
5. **An element that is itself deprecated is not listed as a dependant**, so a chain of end-of-life
   elements shows only the in-scope elements that depend on it from outside.

## 4. The change-board report

Use the standard report format (`../../ea-stakeholder-reporting/references/standard-report-format.md`):

- **Question:** "Where is <the scope> structurally fragile?"
- **Scope:** the scope, the dependency connectors in display terms, the lifecycle values counted as
  end-of-life, and the hops.
- **Figure:** the number of single points of failure, the number of elements that depend on end-of-life
  elements within the hops, and the most-connected elements as a table (element, in, out, total).
- **Completeness:** the share of in-scope elements with a value for the lifecycle tag, and the isolated count.
- **Elements counted:** the single points of failure with the size of what each separates; the dependants
  with what each reaches and how far.
- **How counted:** connectors followed as undirected for single points of failure, and in the stated
  direction for end-of-life dependencies; the hops; whether betweenness was run.
- **Not checked:** relationships the connectors do not carry, elements outside the scope, and anything
  truncated.

Then, apart and labeled as a reading: which findings matter most and why (a single point of failure that
also carries a high criticality tag, a mission-critical application one step from a retired service),
which are probably an artifact of how the model is drawn, and what to confirm first. Never write
"this is a risk" about an element without saying which finding it rests on.

## 5. Traps

- **A hub is not a defect.** A shared service with many dependants is high degree by design. Degree ranks
  what is connected; it does not judge it.
- **Direction for end-of-life dependencies.** The operation follows the direction you give (downstream by
  default: from a connector's source to its target, so something that uses a retired service reaches it).
  If the model draws dependency the other way, say so in the rule and run it that way.
- **No built-in lifecycle vocabulary.** Do not run with `Deprecated` and `Retired` because they were in the
  example. Ask, and confirm against the model.
- **Betweenness on a large model.** It can time out and come back null. Say it was not computed rather than
  leaving it out of the report.
- **Single point of failure is relative to the scope.** Widen the scope and an element that separated the
  graph may stop doing so. Quote the scope with every finding.

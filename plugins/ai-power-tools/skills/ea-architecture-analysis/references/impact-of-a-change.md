# Impact of a change

What retiring, replacing or changing one or more elements reaches. Westbrook Bank values are an
illustration; your technology's stereotypes, connectors and tags replace them.

The operation walks from every start element at once, follows a direction per connector type, and
returns each affected element once, with its distance from the nearest start element and the first path
that reached it, grouped the way the person wants to read it.

## 1. Settle the question first

Ask, or read from the request, four things. Do not call the operation until each has an answer.

| Decide | How |
|---|---|
| **The start elements** ("seeds") | Name each by id or GUID. If the person gave names, look each up and confirm which element was meant when two share a name. One or many: a whole to-be package of removals is several seeds in one call |
| **The rule** | Each connector type with its own direction, proposed from `summarize_connector_patterns` and the technology, agreed before the run (`SKILL.md`, section 1) |
| **The depth** | 1 to 10 hops. Three is a usual first look; say what it means ("three steps along the agreed connectors") |
| **The grouping** | By stereotype (default), by package, by element type, by the value of a tag (`tag:<name>`), or none. Pick what the board will read: "by business kind", "by owning team" |

**Direction is the whole question.** Take "what is affected if the Account Master is retired". In the
Westbrook model, an application `Uses` the Account Master, so the connector runs from the application to
the master. The elements that depend on it are reached by following `Uses` **upstream** (backwards, to
the source). What the master itself depends on is reached by following `Uses` **downstream**. A change to
a service can also reach what realizes it, which is a different connector type with a different direction.
That is why a rule is a list: for example `Uses` upstream plus `realizes` downstream, in one call.

Read one real connector in each direction in the model before you choose, and state the direction in
words in the proposal ("follow Uses backwards: from the thing used to the things that use it").

## 2. The call

```
ea_analyze(operation="analyze_impact", params={
  "seeds": [140],
  "rules": [
    {"connector_stereotypes": ["Uses"], "direction": "upstream"},
    {"connector_stereotypes": ["realizes"], "direction": "downstream"}
  ],
  "depth": 3,
  "group_by": "stereotype",
  "include_tags": ["criticality", "businessOwner"]
})
```

(The ids and names are the Westbrook copy's. Seeds are element ids or GUIDs.) A rule names connector
types as `connector_types` (EA's own type, such as `Association`) or `connector_stereotypes` (the bare
stereotype name, such as `Uses`); matching ignores case and a qualifier.

The result:

| Key | Holds |
|---|---|
| `seeds` | The start elements as resolved |
| `unresolved_seeds` | Seeds that matched no element. Not walked. Report them |
| `rules` | The rule as run (echo it in the report) |
| `affected` | One row per affected element: `id`, `name`, `stereotype`, `distance` from the nearest seed, `first_path` (each hop: `from`, `to`, the connector and the direction followed), and the tags asked for |
| `groups` | `key`, `count`, `min_distance`, `element_ids` per group |
| `counts` | seeds, affected, connectors loaded |
| `unknown_tag_counts` | Per requested tag, how many affected elements have no value |
| `guards` | Depth, depth reached, `max_nodes`, `wall_clock_ms`, `truncated`, `truncated_by` |

Seeds are never listed as affected. A connector end with no element behind it comes back as an element
with `missing: true`; say so, it is a broken link in the model.

## 3. Read it before you write it

1. `unresolved_seeds` empty? If not, say which names matched nothing.
2. `guards.truncated`? If true, the answer is partial: `SKILL.md`, section 2.
3. `depth_reached` equals `depth` with elements at the edge: there is more beyond the depth. Say so.
4. `unknown_tag_counts`: any tag with unknown values is reported as unknown, with its count, beside the
   grouped figure. Never fold it into a group.
5. Compare the first path of two or three elements with the rule. A path through a connector type that
   surprises you is a rule problem, not a model problem; go back to the person.

## 4. The change-board report

Use the standard report format (`../../ea-stakeholder-reporting/references/standard-report-format.md`)
with these choices:

- **Question:** "What is affected if <seed names> are <retired, replaced, changed>?"
- **Scope:** the seeds, the rule in display terms, the depth.
- **Figure:** "N elements are affected within D steps", then the groups as the table (group, count,
  nearest distance).
- **Completeness:** for each tag shown, how many affected elements carry a value (`unknown_tag_counts`).
- **Elements counted:** the `affected` rows, with name, business kind, distance, and the key tags.
- **How counted:** the rule echo, and that each element is counted once whatever the number of paths.
- **Not checked:** what the rule does not follow (containment, diagram placement, other connector types),
  anything truncated, and seeds that did not resolve.

Then, apart and labeled as a reading: which affected elements carry the most risk (a high criticality,
a regulated scope, many dependents), what is one step from the seed and so certain to be touched against
what is three steps away and may not be, and the order a board might take the work. Do not call an
element "critical" unless a tag or the person says so; say what the tag says.

A change board often asks for the list per owner. Group by the owner tag (`group_by: "tag:businessOwner"`)
and report the `(unknown)` group first: those are the elements nobody owns on paper.

## 5. Traps

- **Two directions answer two questions.** "Who depends on this" and "what does this depend on" are
  separate runs, or separate rules in one run. Never report one as the other.
- **A seed that is a container.** Elements inside a package or under a parent are not reached by
  connectors. If the seed is a grouping element, ask whether the members are seeds too.
- **The count is of elements, not paths.** Many paths to one element is one affected element; the first
  path is shown, not all of them.
- **Zero affected is only an answer after the rule is checked.** See the empty-result trap in `SKILL.md`.
- **Do not pair this with a delete.** A clean impact result is one input to a delete decision, not
  clearance. The delete sequence is `ea-model-hygiene`, section 2.

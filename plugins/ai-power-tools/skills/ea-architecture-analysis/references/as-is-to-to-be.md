# As-is to to-be

What is different between a current architecture and a target one: what is added, removed, changed,
matched and unmatched, for elements and for the relationships between them, in one output shape whichever
way the two states are held. Westbrook Bank values are an illustration; your technology's stereotypes and
tags replace them.

## 1. Settle how the two states are held

There are three ways to hold two states in one repository. Ask which one the model uses; do not guess.

| Method | The two states are | Choose it when |
|---|---|---|
| `baseline` | A baseline of a package (as-is) and the package now (to-be) | The target is being built in place, and a baseline of the current state exists or can be taken (`ea-change-management`) |
| `packages` | Two packages: the current one and the target one | The target is modeled separately, beside the current state |
| `tag` | One scope, split by the value of a tag (the lifecycle tag) | Both states live in the same packages, and a tag such as `lifecycle` says which is which |

For `tag`, the person gives the values: which tag values mean as-is (for example `Current`, `Sunset`) and
which mean to-be (`Strategic`). There is no built-in vocabulary; confirm the values against what the model
holds (`summarize_tagged_value_usage`) before running.

## 2. Matching, and what the person decides

Two states are only comparable once an element in one is paired with its counterpart in the other. The
operation pairs in this order and stops guessing at the first doubt:

1. **An identifier map**, when the person supplies one: as-is element to to-be element, each an id or GUID.
   Use it when elements were renamed or copied, and the person knows which is which.
2. **Exact name and stereotype**, ignoring case, when each pair is unique on both sides.
3. **Everything else is returned, not paired.** A name and stereotype that occurs more than once on a side
   comes back as `ambiguous`. An element with no counterpart comes back in `unmatched_as_is` (nothing in
   the to-be to pair with) or `unmatched_to_be`. An element with no name is never paired by its stereotype
   alone: the unnamed elements of each stereotype, from both sides, come back together as `unnamed`, for the
   person to confirm. Show them, ask which unnamed element on one side is which on the other, and give those
   pairs back in the identifier map.

**The person decides every unmatched and ambiguous pair.** A renamed element appears as one removal and
one addition until someone says they are the same. Put each to the person as a short list ("these 9 as-is
elements have no counterpart; these 6 to-be elements have no origin"), ask which pairs are renames, build
an identifier map from the answers, and run again. Never pair by similarity of name on your own, and never
report an unmatched element as "removed" or "new" before the person has said so.

## 3. The call

```
ea_analyze(operation="compare_states", params={
  "method": "packages",
  "as_is_package_id": 10,
  "to_be_package_id": 25,
  "recursive": true,
  "stereotypes": ["WBA::WBABusinessApplication"],
  "identifier_map": [{"as_is": 70, "to_be": 410}]
})
```

(The ids are illustrative.) The inputs by method:

- `packages`: `as_is_package_id` (or `..._guid`), `to_be_package_id` (or `..._guid`), `recursive`, an
  optional `stereotypes` list that narrows both sides, and an optional `identifier_map`.
- `tag`: `tag_name`, `as_is_values`, `to_be_values`, an optional package scope (`package_id` or
  `package_guid`; the whole model without one), `stereotypes`, `identifier_map`. Elements in a package scope
  with no value for the tag come back as `untagged`.
- `baseline`: the package and the baseline's GUID. The as-is side is the baseline and the to-be side is the
  package now.

The result has the same keys for all three:

| Key | Holds |
|---|---|
| `matched` | Each pair, its `matched_by` (identifier map, or name and stereotype), a `status` of `unchanged` or `changed`, and for a changed pair the properties that differ (name, type, stereotype, notes, status, phase and every tag), each with its as-is and to-be value |
| `unmatched_as_is`, `unmatched_to_be` | Elements with no counterpart |
| `ambiguous` | Groups where the exact rule would have paired more than one way |
| `unnamed` | Per stereotype, the unnamed elements of both sides, not paired until the person confirms them (counted in `needs_the_person`) |
| `untagged` | For `tag`: elements in scope with no value for the tag |
| `relationships` | The connectors between paired elements, compared the same way: `matched`, `unmatched_as_is`, `unmatched_to_be`, and `touching_unmatched` for connectors with an end that is not paired |
| `summary` | Counts, and `needs_the_person`: the number of items the person has to decide |

## 4. Read it before you write it

1. **`summary.needs_the_person` above zero means the comparison is not final.** Report it as the headline
   ("14 items need your decision before this is a comparison") and take them to the person (section 2).
2. **Check the method matched what the person meant.** A baseline compared to the wrong package, or a tag
   whose values were not the ones in use, gives a clean-looking and wrong diff.
3. **Read a changed pair's changes.** A tag change from `Current` to `Strategic` on a pair matched by name
   is a lifecycle move; a stereotype change on a pair is a retype. They mean different transition work.
4. **Look at `touching_unmatched` relationships.** A connector whose far end has no counterpart is not
   "removed" or "added" until the end is decided; report it with the element.
5. For a **baseline**, the connector rows depend on how EA labels connector items in its compare log. If
   `relationships` is empty on a package that has connectors, say the connector comparison was not
   established and compare the connectors another way before claiming none changed.

## 5. The change-board report

Use the standard report format (`../../ea-stakeholder-reporting/references/standard-report-format.md`):

- **Question:** "What changes between <as-is> and <to-be>?"
- **Scope:** both states, the method, the stereotypes compared, and the date of the baseline if one is used.
- **Figure:** counts of added, removed, changed, unchanged and still-undecided elements, and of
  relationships the same way.
- **Completeness:** how many elements were paired by an identifier map, by exact name and stereotype, and
  how many the person decided; anything left in `needs_the_person`.
- **Elements counted:** the added, removed and changed lists, with each changed element's differences.
- **How counted:** the method, the matching order, the decisions the person made (list them).
- **Not checked:** what was left out of the stereotypes compared, diagram differences, and anything the
  method does not read.

Then, apart and labeled as a reading, the transition work the differences imply, grouped the way the board
will plan it: retire (in as-is, none in to-be), introduce (in to-be, none in as-is), migrate or retype
(changed), and re-wire (relationship changes). Say which groups rest on a decision the person made, and
which on an exact match.

## 6. Traps

- **A rename is a removal plus an addition** until the person says otherwise.
- **Two states in one package with no tag** cannot be separated by this operation. Say so and ask how the
  states are told apart.
- **A tag with blanks.** Elements with no value are `untagged`, not as-is. Report the count.
- **A baseline is a snapshot of one package.** It does not cover elements that moved out of the package
  since. Say so when the to-be package has fewer elements than the baseline.
- **Do not apply either state.** This skill reads. Restoring a baseline overwrites the model and is
  `ea-change-management`, section 3, with its own warning.

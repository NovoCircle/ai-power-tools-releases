---
name: ea-diagram-advisor
description: Recommend which Enterprise Architect diagram type and viewpoint expresses what a user wants to understand — from their intent, the measured content of a scope, and the languages that content actually uses. Handles the hard case where a scope spans several modeling languages and no conformant view exists. Use when someone describes what they want to see rather than naming a diagram type, or before generating a diagram over content whose modeling languages you have not checked.
---

# Choosing the diagram, before drawing it

A user says what they want to **understand**. They should not have to know which of dozens of
diagram types across several modeling languages expresses it.

This skill turns that request into a recommendation with its reasoning attached. It does not draw
anything — hand the result to `ea-diagram-composition` once the choice is made.

**It recommends and explains; it never silently decides.** A user who asked for a specific diagram
type gets it, with a note when it fits badly. A recommender that quietly picks is indistinguishable
from one that is wrong.

---

## The rule that matters most

**Measure the content. Never guess it.**

Almost every bad diagram-type choice comes from assuming what is in a scope. The whole method here
is: profile what is actually there, attribute it to modeling languages, and let that decide whether
a conformant view even exists.

---

## Step 1 — measure the scope

**The three summary operations cannot be scoped.** `summarize_stereotype_usage`,
`summarize_connector_patterns` and `summarize_observed_metaclasses` take no arguments and query the
whole repository. They are useful for a model-wide picture and useless for a scope, so the histogram
has to come from SQL.

Three steps, all measured against a live repository:

**1. Collect the packages in the scope**, walking `t_package.Parent_ID` down from the root package.

**2. One query for the histogram**, keyed on the stereotype exactly as EA stores it:

```sql
SELECT Stereotype, Object_Type, COUNT(*) AS n
FROM t_object
WHERE Package_ID IN (<the ids>) AND Stereotype <> ''
GROUP BY Stereotype, Object_Type
```

Two traps here, both measured:

- **Every value comes back as a string.** Cast the counts.
- **This total is not the scope size** — it excludes unstereotyped elements. If you want the scope
  size, ask for it separately. Reporting "40% unattributed" against the wrong denominator is worse
  than not reporting it.

**3. Get each technology's vocabulary** from `get_mdg_from_runtime(tech_id=...)`, and pass it as
`known_concepts`. Notes that cost time to learn:

- `tech_id` is the **id**, not the display name. The display name returns `unknown_mdg`.
- The reply's key set varies by outcome: `stereotypes` is `[]` for a technology that is loaded but
  unreadable, and **absent entirely** for an unknown one. Use `.get("stereotypes") or []`.
- A technology can be loaded and still expose nothing, so an empty vocabulary is not proof of an
  empty technology.
- **Neither discovery operation is reliable for a model-embedded MDG.** If a technology you can see
  in the model is not listed, read the technology ids straight out of the repository rather than
  concluding it is absent.

`traverse_element_subgraph` is worth having for the element set, with one caveat: **it returns every
interior edge twice**. Deduplicate on source, target, type and stereotype before counting anything,
or every connector figure comes out roughly doubled.

### Silent failures this step must not trust

Measured, and each returns a plausible empty answer rather than an error:

- A bad element id gives empty `nodes` with **no error key**.
- A package id passed where an element id was wanted returns a `Package` node instead of failing.
- An unknown stereotype gives `total_count: 0` with no error.

So an empty profile means "check the scope", never "the scope is empty".

## Step 2 — profile, and ask the pivotal question

```python
import advise

profile = advise.profile_scope(histogram, bindings, known_concepts=vocabulary)
```

**Is this scope one modeling language, or several?** Everything downstream turns on it.

```python
profile.technologies        # {technology: element count}
profile.dominant            # the largest
profile.dominant_share      # how much of the scope it holds
profile.homogeneous         # dominant_share >= 90%
profile.is_bound            # is the dominant language one we have a BINDING for?
profile.ambiguous           # elements whose language could not be decided
profile.unattributed_stereotypes
```

Three answers, not two, and they lead to different places:

| Profile | Meaning |
|---|---|
| homogeneous and bound | an ordinary, conformant view exists |
| mixed | **no conformant view exists** — see step 4 |
| dominant language named but unbound | most of this is a language with no binding here, usually a customer's own MDG. Not the same as mixed |
| dominant is `(ambiguous)` | more than one loaded language claims these stereotypes, and **the stereotype alone cannot settle it** |

`(ambiguous)` is reported rather than resolved. Two languages sharing a concept name is ordinary in
a repository with several technologies loaded, and picking one by whatever order the bindings
arrived in gives an answer indistinguishable from a correct one and wrong half the time. Ask which
language the content is meant to be, or narrow the scope.

**Naming a technology and being able to advise on it are separate facts.** With a vocabulary
supplied, a customer's own MDG is named in `technologies` while `is_bound` stays False — there is no
view catalogue for it, so there is no conformant view to recommend.

Look at `unattributed_stereotypes` before trusting anything. "I could not place 40% of this scope"
is the most useful thing to know, and it changes what the recommendation is worth.

---

## Step 3 — recommend

```python
for option in advise.recommend(profile, bindings, intent=what_the_user_said):
    print(option.kind, option.technology, option.viewpoint, option.diagram_type)
    for reason in option.reasons:
        print("  -", reason)
```

Ranked best first, on **coverage** (how much of the content the view admits), then **intent**, then
specificity — a narrower viewpoint says more about what a diagram is for.

**Show the reasoning.** It names the counts, the shares and the coverage arithmetic. A
recommendation whose justification could have been written without looking at the content is not a
measurement, and the user cannot tell the difference unless you show your working.

**Watch for `CLOSE CALL` in the reasons.** In a small scope many viewpoints admit everything
present, so coverage and intent tie and an arbitrary tiebreak picks the winner. When that happens,
say so and let the user choose on what the diagram is *for* — which the ranking cannot see.

### Which view is right, and whether it can be drawn, are two questions

A recommended view is an argument to make about the content. Whether this toolchain can generate it
is a statement about the **toolchain**, not about the notation — so both are reported, and neither
stands in for the other.

```python
option.candidate.generation_route      # how a diagram of it would be drawn
option.candidate.can_be_generated      # True / False / None when the binding did not say
```

| Route | What it means | What you do |
|---|---|---|
| `composed` | the geometry is ours and the layout is built | hand it to `ea-diagram-composition` |
| `tool-layout` | the geometry is not ours — EA's own layout places it | place the elements, call the layout operation, then tidy and check it looks right |
| `composer-pending` | the geometry is ours to compute and nobody has built it yet | compose it another way, or fall back to EA's layout |
| `not-producible` | the diagram type dictates the arrangement itself | **say so.** It cannot be generated by composing geometry; draw it by hand, or choose another view |
| `unanswered` | the binding object did not answer the question | confirm before promising a generated diagram |

**`tool-layout` is not a limitation.** It is the intended route for most diagram types in most
notations, and the largest family of them by a wide margin. EA's own layout is fine provided the
result looks good, which is what the tidy-and-verify step is for. Do not report it as a gap.

**`not-producible` is a hard stop, and "compose it another way" is the wrong advice for it.** The
positions carry the content — ordering, sequence, a time axis — so placing coordinates would place
the elements and not the thing the elements are arranged to say. The reason line is prefixed
`CANNOT BE GENERATED` so it is not missed.

**A view that cannot be generated is still ranked and still recommended.** Deliberately: hiding it
would report our gap as the content's, and would silently start recommending it the day a composer
shipped, with the user never told a better view had existed all along. Pass the caveat on rather
than the silence.

**Three properties, not one.** `grammar_is_implemented` alone cannot answer this — it is `False`
both for a layout nobody has built and for a view whose geometry was never ours to compute, and
those two lead to opposite advice. Read `generation_route`, or read
`geometry_is_composed` and `grammar_is_producible` together.

---

## Step 4 — when no conformant view exists

A scope spanning several languages has no correct answer, and pretending otherwise is the damaging
case. Three options, in preference order:

1. **Dominant-language view.** Carries the majority; the rest appears as foreign content. Least
   surprising.
2. **Neutral custom view.** A base type with no profile, belonging to no language, so nothing on it
   is foreign. This is ordinary practice, not a workaround — a large share of real diagrams are
   plain base types.
3. **Split into linked conformant diagrams.** Every view stays valid; the cost is that no single
   picture shows the whole scope, which is usually the thing that was wanted.

### Two obligations, and they are not optional

**Say so.** Record on the diagram and in your response that the view is non-conformant and which
languages it spans. `option.non_conformance` is that sentence; put it somewhere the reader of the
diagram will see it, not only in the chat.

**Reconcile with validation.** `option.will_be_flagged` names the concepts a conformance check will
object to. Offer to scope those rules out or annotate them as accepted — **before** generating, so
the user decides rather than discovering a wall of findings afterwards.

```
ea_validate(... scoped to the new diagram ...)
```

Compare what comes back with `will_be_flagged`. A finding you did not predict means the profile
missed something; say so rather than quietly absorbing it.

---

## Judgment this skill cannot encode

**Coverage is not fitness.** A viewpoint that admits every concept in the scope may still be the
wrong argument to make about it. Coverage says a view *can* hold the content, never that it
*should*.

**The user's words are evidence, not instructions.** "Show me the application landscape" narrows
the choice; it does not settle it. Ask what decision the diagram supports if the ranking is close.

**A recommendation over unmeasured content is a guess with a footnote.** If the scope could not be
profiled, say the recommendation is weak and why.

**Adding a language is a data change, never a code change.** A view catalogue lives in a binding's
`viewpoints:` block. If advising on a new notation seems to need a change to `tools/advise.py`, the
knowledge is in the wrong place — a test enforces that no notation is named in the engine.

---

## Reference

- `tools/advise.py` — the ranking engine. Pure arithmetic, no repository calls, no notation names
- [`ea-diagram-composition`](../ea-diagram-composition/SKILL.md) — where the chosen view gets drawn;
  its `bindings/` are the view catalogues this skill ranks

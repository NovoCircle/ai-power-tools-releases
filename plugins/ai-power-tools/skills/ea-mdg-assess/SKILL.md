---
name: ea-mdg-assess
description: Work out what modeling-language situation a Sparx EA repository is actually in — ad hoc stereotypes vs. a client-built MDG, and whether a technology is installed, embedded, or actually loaded — before picking ea-mdg-author or ea-mdg-model-build. Use at the start of any MDG task, when a stereotype behaves inconsistently, or whenever assess_mdg_situation's recommendation needs a second opinion.
---

# Assessing an MDG situation

`ea_mdg(operation="assess_mdg_situation", params={})` classifies the modeling-language state
of the connected repository so the next step is picked on evidence, not assumption. This skill
covers that call, the three supporting reads that let you check its answer, and what to do when
the answer and the model disagree.

Run this **before** `ea-mdg-author` or `ea-mdg-model-build`. Both of those skills assume you
already know which situation you're in; this is how you find out.

There is a third thing the assessment cannot tell you, and it matters most in exactly the case it
handles worst: a repository full of real stereotype usage and no technology to describe it. That
content is a candidate metamodel — the technology can be **generated from what is already there**
rather than written from scratch. Section 2a covers when to do that and which path to take.

---

## 1. Run the assessment

```
ea_mdg(operation="assess_mdg_situation", params={})
```

No parameters. It reads the repository's stereotype usage and the currently-loaded languages,
and returns a scenario number, a plain-language description, and a `recommended_next_skill`.

An illustration of the shape of the answer, from the Westbrook Bank demo repository (substitute your
own technology and numbers; the figures are not a result you can reproduce):

```
{
  "scenario": 3,
  "description": "Client-built MDG exists but ad-hoc stereotypes are accumulating outside it.",
  "loaded_mdgs": ["WBA"],
  "sparx_loaded": ["..."],
  "ad_hoc_stereotype_count": 11,
  "covered_element_pct": 91,
  "recommended_next_skill": "ea-mdg-author"
}
```

**`ad_hoc_stereotype_count` is a count of elements, not of distinct stereotypes.** The assessment
looks at every element in the whole repository whose primary stereotype (the `t_object.Stereotype`
column, unqualified) is not defined by any loaded and enabled client technology or any loaded
Sparx-shipped technology, and counts each such element once. So the number includes elements that
belong to no modeling language you care about: a technology's own source package (elements
stereotyped `stereotype`, `metaclass` and so on) and elements created by other tools all count as
ad hoc. A disabled client technology is left out of `loaded_mdgs`, so its stereotypes count as ad
hoc too. `covered_element_pct` is the covered share of all stereotyped elements, by the same rule.
Read section 5 before you act on `recommended_next_skill`.

## 2. What the scenarios mean

| # | Condition | Plain meaning | Do next |
|---|---|---|---|
| 1 | No client MDG loaded | Repository uses only Sparx-shipped languages (ArchiMate, BPMN, UML, ...), with or without informal stereotype conventions | `ea-mdg-model-build` if a profile model already exists to build from. Otherwise **census the existing usage and generate from it** (§2a) — writing one from scratch is the last resort, not the default |
| 2 | Client MDG loaded, ad hoc usage under 5% of stereotyped elements | The technology is doing its job — the repository conforms | `ea-mdg-author` for further changes, or nothing at all |
| 3 | Client MDG loaded, ad hoc usage at or over 5% | The technology exists but people are stereotyping outside it — new concepts, duplicate ad hoc versions of existing ones, or drift | Extend the existing technology: `ea-mdg-author` if it's XML-authored, `ea-mdg-model-build` if it has a source model (check its profile package first — see `ea-start-here` §2) |

A fourth scenario, "external reference model needed," is named in the operation's own
documentation but was never observed to be returned in this session, on any input — the
underlying logic only ever produces 1, 2, or 3. Don't design a workflow around scenario 4 without
confirming the current server actually emits it.

The 5% threshold and the "ad hoc" label come from one thing: whether a stereotype in use matches
an entry in a loaded language's known stereotype set. Section 3 shows how to recompute that
yourself instead of trusting the number blindly.

## 2a. Generating a technology from what the repository already contains

A repository with no technology is rarely a repository with no modeling language. It usually has
one — undeclared, inconsistent, and spread across however many stereotypes people reached for.
Those stereotypes, their metaclasses and their tagged values are a candidate metamodel.

**Census before you decide anything.** `assess_mdg_situation` reads `t_object.Stereotype` and the
loaded languages, and that column holds a bare name which does not identify the language: in one
repository `ApplicationComponent` resolves to `TOGAF::`, `BusinessProcess` to `BPMN1.1::`, `Node`
to `UPDM2::`, and several ArchiMate-looking names to no profile at all. The profile binding lives
in `t_xref`. Use `_shared/tools/ea_census.py`, which resolves it:

```python
from ea_census import build_stereotype_index, census_elements, tag_coverage
census = census_elements(objects, build_stereotype_index(xrefs))
```

Connectors have the same census: `census_connectors(connectors, index)` and
`compare_connectors_declared_observed(census, mdg)`.

**The same census has a second consumer.** `ea-reporting-database` runs it to decide what tables a
reporting database gets. If the ask is a *queryable extract* of the repository rather than a
*technology* generated from it, go there instead — the census work is identical and only the output
differs. Both can be run from one extract.

Read the result before choosing a path. Three things in it change the decision:

- **Ad hoc versus profile-bound usage of the same name.** One stereotype name can be both. If most
  usage is already bound to a profile, you are extending a technology, not creating one.
- **Stereotypes from other shipped languages.** EA enables every language it ships, so an
  architect reaching for "Application Component" can land on TOGAF's without noticing. Several
  languages in light use is usually accident, not design — and generating a technology that
  blesses the accident makes it permanent.
- **Tag-name shape.** An element carrying your technology's tags while labeled with somebody
  else's stereotype is a misassignment, and the census reports it as one.

### Then ask which path, and say what it costs

**This is an explicit question for the user, not a default.** The two paths produce the same
technology today and diverge permanently afterwards.

| Path | Source of truth afterwards | Choose it when |
|---|---|---|
| **A — direct XML** (`ea-mdg-author`) | the `.xml` file | The technology is a one-off, or nothing will maintain a model for it. Fastest, writes nothing to the repository |
| **B — model-driven** (`ea-mdg-model-build`) | profile packages inside the repository | The technology has a lifecycle — versions, more than one author, a metamodel stakeholders review. Writes profile packages into the repository |

⚠ **The choice is one-way.** Hand-editing an MDG that has a source model means the next
model-driven export silently discards the edit; there is no reconciliation step and no record the
edit happened. Going from A to B later means importing the XML as a profile package and never
hand-editing again. Both `ea-mdg-author` and `ea-mdg-model-build` carry this warning; it is
repeated here because the generation case is where someone picks without realising they are
picking.

### Record which path was taken

A generated technology looks identical either way, so **the choice has to be written down or the
next maintainer cannot tell**. This is the single most likely way a generated MDG becomes the next
silent-divergence case.

- **Path B** — in the profile package notes, which is where `ea-mdg-model-build` already says to
  put it.
- **Path A** — there is no profile package, so put it in the technology's own
  `<Documentation notes="...">`, and say the XML is the source of truth.

Either way, state the date and that the technology was generated from a census rather than
authored, so a later reader knows the repository was the original source.

## 3. Installed, embedded, and loaded are three different questions

This is the distinction `assess_mdg_situation` collapses into one scenario number, and unpacking
it is most of what "sanity-checking the assessment" means in practice. Full detail, including the
exact payload shape and *why* each call answers a narrower question than its name suggests, is in
[references/three-states.md](references/three-states.md). Short version, each observed live
against the Westbrook Bank repository:

| Question | Call | What it actually told us |
|---|---|---|
| Is a technology registered anywhere EA would show it in Manage Technology? | `list_registered_technologies` | One row per registration, not per technology: the same id can be listed more than once (for example a Project copy and a Model copy, or older builds left disabled) with different `version`, `location` and `enabled` values. Read the row you mean |
| Does the model file itself carry a copy? | `get_embedded_mdgs` | On a server up to 3.5.0: empty, because it read a document type none of EA 17.1's import routes writes — proves nothing. Later servers list each stored copy with its Location: `Model` (`t_document` TECHNOLOGY, whole technology) or `Project` (`t_trxtypes`, no toolbox pages) |
| Does EA have it loaded right now, for this session? | `get_mdg_from_runtime`, `params={"tech_id": "WBA"}` | 14 stereotypes with their metaclasses, 10 tagged values and 3 diagram types, `"source": "live"`, and a `provenance` block naming where the definitions were read from and what EA reports the version as |

The first and third rows were observed against WBA 1.0. Against WBA 1.1.1 at Location: Model,
`get_mdg_from_runtime` answers 18 stereotypes (15 element and 3 connector), 3 diagram types and 3
toolbox pages, and Manage Technology lists one enabled `WBA` with the two older builds disabled.

`get_mdg_from_runtime` reads the technology EA loaded — from the copy imported into the model, or
from the registered `.xml` EA loads at startup — so its stereotype list is the deployed
technology's, not a description of one. Read `source` before you read anything else:

| `source` | What it means for your conclusion |
|---|---|
| `live` | Definitions read from the loaded technology. Safe to reason about as deployed. |
| `registered_not_enabled` | (Server later than 3.5.0.) The definitions exist and EA reports the technology loaded, but it is **disabled** in Manage Technology: its toolbox, diagram types and quick links are not offered. A disabled technology still answers `IsTechnologyLoaded` True, so `loaded` alone is not "in use". |
| `registered_not_loaded` | The definitions exist, but EA does not currently have the technology loaded. Modeling against it will not behave as described until it is enabled in Manage Technology. |
| `session_parse` | These came from a file handed to `parse_mdg_xml` this session, which is not necessarily what EA loaded. |
| `unavailable` | The call declines to answer. `error` says why: `mdg_loaded_no_definition` (loaded, but its XML is neither registered nor in the model — export it and run `parse_mdg_xml`), `unknown_mdg` (EA reports nothing loaded under that exact id), `cannot_determine` (EA could not be probed at all). |

A `provenance.version_mismatch` means EA reports one version and the definitions read declare
another — EA is loading a different build of the technology than the one being read. Resolve that
before trusting either side.

## 4. Sanity-check the assessment, don't just trust the number

`assess_mdg_situation` runs its own stereotype query over `t_object` (the same bare
`Stereotype` column `summarize_stereotype_usage` groups on). Compare against that call's output
rather than treating the scenario number as ground truth — it takes one extra call and catches
drift the single number hides (for example: is the 91% covered by four stereotypes doing real
work, or by one stereotype used everywhere and three edge cases). The walkthrough in
[references/verification-walkthrough.md](references/verification-walkthrough.md) shows the
method on an illustrative table; your numbers will differ.

From server 3.6.0, `summarize_stereotype_usage` also returns `resolved_items` (each with `stereotype`, `fqname`,
`binding` of `profile` or `ad_hoc`, `object_type`, `element_count`) resolved through `t_xref`, and
`split_stereotypes` (names that appear both profile-bound and ad hoc, or bound to more than one
profile). Use them when the bare name is not enough to tell which language an element belongs to.

## 5. When the recommendation doesn't fit — override it

`recommended_next_skill` is a fixed default per scenario, not a judgment about your repository:
scenario 1 returns `ea-mdg-model-build`, and scenarios 2 and 3 return `ea-mdg-author`. (Earlier
servers could return `ea-mdg-extend` for scenario 3; no such skill exists, so if you see it, treat
it as `ea-mdg-author`.) Because it is only a default:

1. Read `description`, not just `recommended_next_skill`.
2. Match that description against `ea-start-here` §2's routing table yourself.
3. Confirm the target exists as a directory in this repository before telling anyone to go there.

Override it any time the scenario's plain-language `description` doesn't match what you already
know about the repository — for example, if you know a source model exists for the technology
but the assessment can't see that (it only looks at loaded languages and stereotype usage, not at
profile packages), pick `ea-mdg-model-build` over `ea-mdg-author` regardless of what came back.

## 6. Failure modes hit in this session

| Symptom | Cause | Fix |
|---|---|---|
| `get_mdg_from_runtime` returns `missing_required_params` | It requires `tech_id` — it does not assess the whole repository, only one named technology | Pass `params={"tech_id": "WBA"}` (or whatever `assess_mdg_situation`'s `loaded_mdgs` named) |
| `get_embedded_mdgs` returns `count: 0` on a repository with a technology clearly loaded | Server up to 3.5.0: it read only `t_document` rows of type `MDGXml`, which none of EA 17.1's import routes writes. EA 17.1 stores an in-model technology as `t_document` `TECHNOLOGY` (Location: Model) or in `t_trxtypes` (Location: Project) | On those servers treat empty as "this call cannot see it". Later servers read both |
| `get_mdg_from_runtime` says `mdg_loaded_no_definition` for a technology imported to the model | Server up to 3.5.0 cannot read Location: Model (`t_document` TECHNOLOGY) | Upgrade, or export from Manage Technology and run `parse_mdg_xml` |
| The same technology appears twice in Manage Technology, Location `Project` and `Model` | It was installed by both routes. EA answers `GetTechnologyVersion` from the Project copy | Keep one; see `ea-mdg-deploy` |
| `get_mdg_from_runtime` returns `"source": "unavailable"` with `mdg_loaded_no_definition` | EA has the technology loaded, but its XML is neither registered in a technology folder nor imported into the model, so there is nothing to read | Export it from Specialize > Technologies > Manage Technology and run `parse_mdg_xml` on the file |
| Same technology name appears twice in `list_registered_technologies` with different `enabled` values | Separate registrations of one id (for example a Project copy and a Model copy, or older builds left disabled) legitimately coexist; the operation does not deduplicate by id | Not a bug — read `location` and `enabled` per row, don't assume one row speaks for the technology |
| `recommended_next_skill` names a skill directory that doesn't exist | An older server build (see section 5) | Treat `ea-mdg-extend` as `ea-mdg-author`; never route on this field alone |

---

## Reference files

| File | Covers |
|---|---|
| [references/three-states.md](references/three-states.md) | Full payloads for `list_registered_technologies`, `get_embedded_mdgs`, and `get_mdg_from_runtime` against the Westbrook Bank repository, and exactly which question each one does and doesn't answer |
| [references/verification-walkthrough.md](references/verification-walkthrough.md) | The `summarize_stereotype_usage` cross-check worked end to end against the same repository, reproducing `assess_mdg_situation`'s own numbers by hand |

This skill is read-only. If a task that follows it needs the EA desktop UI (deploying a fix via
`ea-mdg-author` or `ea-mdg-model-build`), see
[`../_shared/references/latency.md`](../_shared/references/latency.md) for wait guidance —
nothing here waits on the UI, so it isn't restated.

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

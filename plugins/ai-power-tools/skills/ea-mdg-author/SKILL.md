---
name: ea-mdg-author
description: Author a Sparx EA MDG Technology XML file — define stereotypes, tagged values, toolbox pages, and custom diagram types. Use when creating or modifying any MDG technology for Sparx EA.
---

# Authoring a Sparx EA MDG Technology

For a language that has a file in `../_shared/languages/<id>/ea.yaml`, that file holds the technology id, stored stereotype names and diagram types. Read it before measuring them again.

*Verified against EA 17.0 Build 1704, except the statements about the diagram `toolbox` property and the embedded-technology route, which were measured on EA 17.1 (Section 2).*

## Before you start — does this MDG already have a source model?

This skill treats the `.xml` file as the source of truth. If the technology you're editing has a
source model in an EA repository (profile packages, a design metamodel, a build/export procedure
someone follows to produce the shipped XML), **stop and use `ea-mdg-model-build` instead.**

⚠ **Hand-editing an MDG that has a source model causes permanent, silent divergence.** The XML
edit works today — but the next time anyone runs the model-driven export/build procedure, it
overwrites the file from the profile packages and your edit is gone, with no warning and no
record that it ever existed. There's no reconciliation step; the export doesn't know your edit
happened. If you're not sure whether a technology has a source model, ask before editing its XML
directly.

**Generating a technology from a repository's existing usage?** That is path A, and this is the
right skill for it — see [Authoring from a generated candidate metamodel](#authoring-from-a-generated-candidate-metamodel)
below. Note what the choice commits you to: the generated `.xml` becomes the source of truth from
the moment it is written, and the repository content it was derived from does **not**. Re-running
the census later produces a fresh candidate, not an update to the file you shipped. If the
technology needs a living source model instead, stop now and use `ea-mdg-model-build` — that is
path B, and moving from A to B afterwards means importing the XML back as a profile package and
never hand-editing again.

## Quick Reference

| Task | Key Rule |
|------|----------|
| All `id=` attributes | **≤ 12 characters** (EA hard limit — silently fails if exceeded) |
| File encoding | Must be `utf-8` |
| UMLProfile `id` | In a hand-written file, make it match the technology `id` (a generated file differs; see the checklist note) |
| `bgcolor` color values | COLORREF integer: B×65536 + G×256 + R. `-1` = use EA theme default |
| Tagged value type | Use `enumeration` (not `enum`) and `String` (capital S) |
| Test after every structural change | Use `ea-mdg-deploy` skill |

---

## Tool Selection

When automating MDG work, pick the right tool tier:

| Operation | Use |
|-----------|-----|
| Author MDG XML, read/write files | Claude Code file tools (`Write`, `Read`, `Edit`) |
| **Emit MDG XML from a metamodel dict** | `ea_mdg(operation="write_mdg_xml", params={"intermediate_metamodel": {...}, "output_path": "..."})` — the path-A route; hand-writing the XML is for edits afterwards |
| Census a repository's existing usage | `_shared/tools/ea_census.py` over the rows `ea-mdg-assess` §2a lists (profile-aware; one route, not your own SQL calls). `summarize_stereotype_usage` (server 3.6.0 or later, profile-aware) gives stereotype counts only, so it does not replace it |
| Parse and validate MDG XML | `ea_mdg(operation="parse_mdg_xml", params={"path_or_content": "..."})` |
| Install MDG at application scope | `ea_mdg(operation="install_mdg", params={"scope": "user", "xml_path_or_content": "<mdg-dir>\\WBA_MDG.xml"})` |
| Install MDG into the model, whole technology | EA UI: Specialize ▸ Publish Technology ▸ Import MDG Technology ▸ **Import to Model** (Location: Model). EA has no COM call that imports a file there |
| Install MDG into the model, legacy route | `ea_mdg(operation="install_mdg", params={"scope": "embedded", "xml_path_or_content": "<mdg-dir>\\WBA_MDG.xml"})` (Location: Project). **Drops toolbox pages**; the response's `not_stored` says so |
| Verify MDG is loaded | COM (see the `ea-com` skill): `repo.IsTechnologyLoaded(tech_id)` and `repo.IsTechnologyEnabled(tech_id)` with your technology id (a disabled technology still reports loaded) |
| Fix `Object_Type` in database | `repo.Execute()` DML, run through the `ea-com` skill (no `ea_*` operation does it) — **not** the `elem.Type` COM setter (silently fails for ArchiMate types) |
| Dismiss EA dialogs | Computer use screenshot → click → screenshot again |

> **`get_embedded_mdgs` up to server 3.5.0 returns empty** for every in-model technology on EA
> 17.1: it read a document type none of EA 17.1's import routes writes. Later servers list both in-model Locations.
> Either way, Manage Technology (Specialize → Technologies) is the authoritative view.

A technology with toolbox pages that will be maintained belongs in a source model
(`ea-mdg-model-build`), from where `install_mdg(scope="model")` (server later than 3.5.0) installs it
at Location: Model in one call.

---

## Authoring from a generated candidate metamodel

The usual entry to this skill is a blank file and a design. The other entry is a repository that
already contains the language, undeclared — the stereotypes people reached for, the metaclasses
they landed on, the tagged values they filled in. That is a **candidate metamodel**, and this
section turns it into a technology. The rest of the skill then applies unchanged for edits
afterwards.

Route here from `ea-mdg-assess` §2a, which is where the path A / path B choice is made and
recorded. If you have not made that choice yet, go back and make it — it is one-way.

### The sequence

```
census  →  candidate metamodel  →  write_mdg_xml  →  parse_mdg_xml  →  install_mdg  →  verify
                                                     (round-trip)
```

**1. Census, profile-aware.** Run `_shared/tools/ea_census.py` over the rows `ea-mdg-assess` §2a
lists, read once each. It is profile-aware and tested, and it gives the metaclass pairs, tag
coverage and enum domains in step 2; rebuilding it from your own SQL calls is slower, risks an EA
error box on a live model, and misses what it handles (multi-stereotype elements, other languages'
tags). `summarize_stereotype_usage` is profile-aware from server 3.6.0 but returns stereotype
counts only; before 3.6.0 it reads `t_object.Stereotype`, a bare name that cannot separate a
governed element from an ad hoc one carrying the same name.

**2. Shape the candidate.** `write_mdg_xml` takes the dict shape `parse_mdg_xml` produces and
`get_mdg_from_runtime` returns — which is what makes the round-trip in step 4 meaningful:

```python
{
  "technology_id":   "WBA",            # see the 7-character rule below
  "technology_name": "Westbrook Bank Architecture",
  "version":         "1.0.0",
  "notes":           "Generated from a census of <repository> on <date>.",
  "stereotypes": [
    {"name": "WBABusinessApplication", "alias": "Business Application",
     "metatype": "WBABusinessApplication", "base_metaclass": "Component",
     "notes": "...",
     "tagged_values": [
       {"name": "criticality", "type": "enumeration",
        "values": ["Mission-Critical", "Business-Critical", "Important", "Standard"]},
     ]},
  ],
  "diagram_types": [...],
}
```

Put the provenance in `notes` — that the technology was generated, from which repository, on what
date. It is the only place a path-A technology can record it, and `ea-mdg-assess` §2a requires it.

**3. Emit.** `ea_mdg(operation="write_mdg_xml", params={"intermediate_metamodel": {...},
"output_path": "..."})`.

**4. Round-trip before installing anything.** Parse what you just wrote and compare it against the
dict you passed in:

```python
ea_mdg(operation="parse_mdg_xml", params={"path_or_content": "<output_path>"})
```

Stereotype count, names, metaclasses and tagged values should come back equal. This is cheap and
it is the only check that catches an emitter gap between what you described and what the file
says — install and deploy both report success on a file that is missing content.

**5. Install and verify** — hand off to `ea-mdg-deploy`. Do not treat a `True` return as proof;
that skill says what to check instead.

### Naming, when nothing declares an alias

A census gives you stereotype names, not display names. There is no alias to copy, and mechanical
case-splitting cannot see into an all-caps technology prefix — `WBABusinessApplication` splits to
`wbabusiness_application`, not `business_application`.

So the rule is **strip the known technology prefix first, then split**, and state the prefix you
stripped rather than inferring one per name. Where the repository has a loaded technology,
`get_mdg_from_runtime` supplies real aliases and they beat anything derived. Where it does not,
derive a candidate and **put it in front of the user before shipping it** — a display name is
customer-facing text and a wrong one is cheap to fix now and awkward later.

⚠ **The technology id's effective limit is 7 characters, not 12.** The ≤ 12 rule in Quick
Reference is EA's, and it applies to the *derived* ids too: the writer generates `<id>-Diag` and
`<id>-TB`, so an 8-character id produces a 13-character derived id and is rejected. Unlike
hand-authoring, this route catches it — `write_mdg_xml` pre-flights every id and returns a
structured `id_too_long` naming the offending value, instead of EA silently rejecting the
technology at load time. A census-derived id taken from a package or profile name will often be
too long; shorten it deliberately rather than truncating.

### Connector stereotypes

A census over a live repository finds connector stereotypes as readily as element ones, and the
emitter supports them in `UMLProfiles`. Generate them the same way, with one caution: an observed
connector stereotype is frequently a *shipped language's* relationship — `BMM::Uses`,
`StandardProfileL2::Realization`, `BPMN1.1::Assignment` — rather than a concept the technology
should claim. Check the census's profile binding before promoting one. Adopting another language's
relationship into your own technology makes a reporting distinction permanent that was probably an
accident.

### ⚠ Generated XML ships no reference data, so enum tagged values stay free text

`_emit_mdg_xml_string` writes a hardcoded empty `<TaggedValueTypes/>` into every section. The
`values=` list on a `<Tag>` is emitted and is what makes the dropdown work in a hand-authored
file, but **no RefData is generated**, so a technology installed from `write_mdg_xml` output alone
gives free-text fields where a closed list was intended.

Consequence for a generated technology: the enum domains the census inferred, and the complete
domains the MDG declared, are both present in the XML as `values=` and neither becomes repository
reference data. Say so when handing the technology over, rather than letting someone discover it
when a dropdown is a text box. Reference data is a repository-wide concern — see
`ea-mdg-model-build` Phase 3, which covers `t_propertytypes` and how types get selected into a
build. This is a known gap in the generator.

---

## Authoring workflow

An MDG Technology XML file has three parallel sections wrapped in one `<MDG.Technology>` root: a
UML Profile (element and connector stereotypes with their tagged values), a Diagram Profile
(custom diagram types), and one or more UIToolboxes (the palette pages EA shows for each diagram
type). All three share the same `<UMLProfile profiletype="uml2">` wrapper, and the technology's
`id=` must match everywhere it is referenced — that single mismatch is the most common reason a
toolbox fails to resolve.

The full skeleton, with the three sections annotated, is in
[references/xml-skeleton.md](references/xml-skeleton.md) (also covers file-encoding rules).

Build in this order:

1. **Element stereotypes** — one `<Stereotype>` per concept, applied to a UML base type.
2. **Connector stereotypes** — only if the technology needs its own relationship semantics.
3. **Custom diagram types**: bind each to its toolbox with the `toolbox` property (form: Section 2).
4. **Toolbox pages** — the palette items EA shows for each diagram type.
5. **Quick Linker rules** (optional) — hover-menu connector creation, if you added connector stereotypes.
6. **Companion validation sidecar** — a `<tech_id>_rules.yaml`, never `<Scripts>` (MCP can't reach EA's script engine).
7. **Deploy and verify** — hand off to `ea-mdg-deploy`.

### Section 1 — Element Stereotype

Each element stereotype wraps a UML base type (`Class`, `Component`, `Activity`, ...) and carries
its tagged values. The real `WBABusinessApplication` stereotype — full XML, the attribute rules,
and the tagged-value `type=` table — is in
[references/stereotypes.md](references/stereotypes.md).

**Pitfall — wrong base type hides elements in the Project Browser.** `<Apply type="...">` sets
`t_object.Object_Type`. Using an ArchiMate or BPMN shape name (e.g. `BusinessActor`) as the base
type when that MDG isn't active at project scope makes elements invisible in the Project Browser
tree, even though they still appear on diagrams and in SQL. For a standalone custom MDG, always
base on a standard UML type (`Class`, `Component`, etc.) and carry the ArchiMate concept through
the stereotype name and tagged values instead. The full safe/dangerous base-type lists and the
`repo.Execute()` DML fix for elements already stored wrong are in
[references/stereotypes.md](references/stereotypes.md#base-type-and-project-browser-visibility).

### Section 1 — Connector Stereotype

**The shipped WBA technology (1.1.1) defines three connector stereotypes:** `Uses` (Association),
`Flows` (InformationFlow) and `realizes` (Realisation), each with the tags `dataFlowClassification`,
`integrationPattern` and `slaTier`. For a relationship between WBA elements, use one of them where it
fits, otherwise a plain UML connector type with no stereotype (`Dependency`, `Realization`,
`Association`, `Aggregation`). [references/stereotypes.md](references/stereotypes.md) shows how
you *would* add another — the example is a `WBARunsOn` connector labeled **PROPOSED EXTENSION — not
part of the shipped WBA technology**, kept only to teach the pattern.

### Section 2 — Custom Diagram Type

A diagram stereotype uses `Apply type="Diagram_Logical"` and points at its toolbox via a
`toolbox` property. The full XML and rules are in
[references/diagrams-toolboxes.md](references/diagrams-toolboxes.md).

**Pitfall: what `toolbox` must equal is only partly measured.** The Westbrook demo MDG 1.1.1,
generated by EA from its source model, sets `toolbox` to `WBA::WBA ArchiMate`
(`<technology id>::<name of the toolbox's UML profile>`, not the page name `WBA ArchiMate
Elements`), and its four diagram types resolve and switch the toolbox (EA 17.1). That profile-name
form is **measured to work**. The page-name form, the toolbox item tag forms and the UML profile id
forms are **not yet measured**: the rules in this skill for them were written from the book, not
from a test, and a generated file uses different forms (item tags prefixed with the profile name and
suffixed `(UML::<metaclass>)`, profile ids derived from GUIDs). Use the profile-name form for
`toolbox`, and check anything else on a scratch diagram
([how](references/diagrams-toolboxes.md#checking-a-toolbox-form-on-a-scratch-model)) before relying on it.

### Section 3 — Toolbox Pages

One `<Stereotype>` per page, `Apply type="ToolboxPage"`, one `<Tag>` per palette item in the
format `<YourTechID>::StereotypeName`. The real WBA technology ships three pages: `WBA ArchiMate
Elements`, `WBA BPMN Elements`, `WBA UML Elements`. Full XML (including how a connector toolbox
page would be wired up) is in
[references/diagrams-toolboxes.md](references/diagrams-toolboxes.md).

The COLORREF color formula and the `id=` mapping pattern for names over 12 characters are also in
that reference file.

---

## Namespace Consistency Checklist

Before deploying, verify:

- [ ] `<MDG.Technology id="WBA">`
- [ ] `<Documentation id="WBA">` (top-level)
- [ ] UMLProfile `<Documentation id="WBA">` — **must match technology id**
- [ ] All toolbox `Tag name=` values: `WBA::WBABusinessApplication` etc.
- [ ] DiagramProfile `Property name="toolbox"` names the toolbox: `WBA::WBA ArchiMate` (`<id>::<toolbox UML profile name>`, measured on 1.1.1; see Section 2)
- [ ] COM calls: `Repository.IsTechnologyLoaded("WBA")`

This checklist is for a file you author by hand. A technology EA generates from a source model
(the shipped Westbrook one) names its UML profile after the profile package, prefixes its toolbox
item tags with that profile name, and derives its profile ids from GUIDs, so it will not match the
list line for line. That is a different generator, not a defect in the file, and neither form
should be rewritten to match the other. Which forms EA resolves in a hand-written file is only
partly measured (Section 2); the id cross-check below is how to find out on yours.

### A toolbox that does not show: check in this order

1. **The id cross-check first.** Read the file and compare the technology id in the root, the top-level
   documentation, the UML profile documentation, the toolbox tag prefixes and the diagram `toolbox`
   property. An id mismatch is the common cause. **Report the result** (a mismatch and where, or
   that all agree) before any install, restart or reinstall advice, and before mentioning the legacy
   embedded route.
2. Then the diagram's `toolbox` value against the toolbox profile or page it names (above).
3. Then where the technology is installed: at Location: Project no toolbox pages are stored, and the
   fix is Location: Model (`ea-mdg-deploy`). Check loaded and enabled, and restart EA before judging.
Do not send the person to reinstall before step 1 is reported.

---

## Post-Install: Applying the MDG to Existing Repository Data

After deploying an MDG, EA does not automatically update existing elements. Ask the user whether
they want to migrate existing elements to the new stereotypes and tagged values; if yes, walk
through: identify candidate elements with a read-only SQL query, present them for confirmation,
update each via the `update_element` MCP tool (never raw DML — EA's cache won't see it), then
re-run the validation sidecar to catch anything left incomplete. The full four-step workflow with
the SQL and Python calls is in
[references/post-install-migration.md](references/post-install-migration.md).

---

## Quick Linker Rules

Quick Linker (QL) is the hover menu EA shows on a diagram element, offering context-sensitive
connector creation. QL rules live in the MDG XML on the *source* stereotype and name a target
stereotype constraint. Add them only when you've also defined a connector stereotype — a plain,
un-stereotyped relationship (`Dependency`, `Realization`, `Association`) already appears in EA's
default QL menu with no extra XML. Setting `_HideUmlLinks` without at least one QL rule produces
an empty, apparently-broken menu.

The full rule syntax (both the `write_mdg_xml` intermediate-metamodel form and the manual XML
form), the legacy Profile Diagram / MTS Wizard note, and the EA verification steps are in
[references/quick-linker.md](references/quick-linker.md).

---

## Validation Rules — Do NOT Use `<Scripts>` with AI Power Tools

When AI Power Tools for Sparx EA is deployed, **do not embed validation rules in the MDG's
`<Scripts>` section** — that mechanism runs JavaScript inside EA's scripting engine, which the MCP
server cannot reach. Instead, every MDG produced by this skill ships a companion
`<tech_id>_rules.yaml` sidecar and runs it with `ea_validate`; see the `ea-validation` skill
for the schema. The wrong-vs-right XML/YAML comparison, the minimal rules template, and the
smoke-test command are in
[references/validation-sidecar.md](references/validation-sidecar.md).

---

## EA Computer Use — Latency Guidelines

MDG authoring primarily uses file tools, but deployment verification and any diagram-based
checks require the EA UI. Wait before screenshotting — 2–15 seconds depending on the operation —
and never retry without confirming the previous action failed. Full wait-time table and the
standard action/wait/screenshot pattern:
[`../_shared/references/latency.md`](../_shared/references/latency.md).

---

## Researching the Sparx EA API

- MDG Technology authoring → Sparx EA help, search "MDG Technology" or "UML Profile"
- Tagged value types → search "TaggedValueTypes"
- Diagram types → search "Diagram Stereotypes" or "Custom Diagram"
- When documentation is unclear, use `ea.repo_methods()` to enumerate available COM methods at runtime

---

## File Encoding (Critical)

MDG Technology XML files must declare and use `utf-8` encoding, with the declaration and the
actual byte encoding agreeing — EA rejects the file outright if they don't. Full guidance
(legacy `windows-1252` handling, read/write code patterns):
[`../_shared/references/file-encoding.md`](../_shared/references/file-encoding.md).

---

## Reference files

| File | Covers |
|------|--------|
| [references/xml-skeleton.md](references/xml-skeleton.md) | Full `<MDG.Technology>` skeleton; links to the shared file-encoding guidance |
| [references/stereotypes.md](references/stereotypes.md) | Element stereotype XML, attribute and tagged-value-type tables, base-type visibility pitfall and fix, connector stereotype XML |
| [references/diagrams-toolboxes.md](references/diagrams-toolboxes.md) | Custom diagram type XML, toolbox page XML, COLORREF table, ID mapping pattern |
| [references/post-install-migration.md](references/post-install-migration.md) | Four-step workflow for migrating existing elements onto a newly installed MDG |
| [references/quick-linker.md](references/quick-linker.md) | Quick Linker rule syntax, both authoring approaches, verification steps |
| [references/validation-sidecar.md](references/validation-sidecar.md) | Why not `<Scripts>`, YAML sidecar template, smoke-test command |

## Verify in EA's UI

EA reports success it has not earned, and reports failure as a modal dialog that blocks the
COM connection rather than as an error you can catch. Neither shows up in a tool response.

- **If a call seems to hang, screenshot EA and read the dialog before concluding anything.**
  It names the cause. Dismiss from the front — dialogs stack, and a later call can be queued
  behind one raised by an earlier one. Windows reporting EA as "Responding" means nothing.
- **After any diagram create or edit, reload the diagram, screenshot it, and look.**
  `ok: true` means rows were written, not that elements landed where you intended, that
  styling applied, or that the result is readable.
- **Without computer use**, say so. Ask the user to paste a screenshot of the EA window or
  dialog into the conversation, read the cause from it, and ask the user to dismiss the dialog
  before you retry. Never report a hang you have not diagnosed or a diagram you have not seen.

Full procedure: [`../_shared/references/ea-ui-verification.md`](../_shared/references/ea-ui-verification.md)

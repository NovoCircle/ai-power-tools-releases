---
name: ea-mdg-model-build
description: Build a Sparx EA MDG Technology from a model held inside the repository — requirements, design metamodel, profile packages, toolbox and diagram profiles, then export and generate the MDG XML. Use when the MDG has a source model in EA, or when a hand-authored MDG needs to be brought under model control.
---

# Building an MDG Technology from a Model

*Grounded in an end-to-end, model-driven build of the Westbrook Bank Architecture (`WBA`)
technology. Tool-surface claims verified against `ea-mcp-server` v2.2.0 — see the
note at the bottom of Quick Reference.*

Two ways exist to produce an MDG. This skill covers the model-driven one. `ea-mdg-author` covers the other.

| Path | Source of truth | Use when |
|---|---|---|
| **Model-driven** (this skill) | Profile packages in an EA repository | The MDG has a lifecycle — multiple versions, more than one author, a design metamodel that stakeholders review |
| **Direct XML** (`ea-mdg-author`) | The `.xml` file | One-off technology, a patch to a shipped file, or no repository to host the source |

⚠ **These two paths diverge permanently.** Hand-editing an MDG that has a source model means the next model-driven export silently discards the edit. Pick one per technology and record which in the profile package notes. To move from direct XML to model-driven, import the XML as a profile package first (`Publish Technology ▸ Import Package as UML Profile`), then never hand-edit again.

---

## Quick Reference

| Task | Route |
|---|---|
| Create stereotype, attribute, constraint | MCP API |
| Duplicate a package | MCP API — `duplicate_package` (fresh GUIDs throughout; the API equivalent of Paste as New) |
| Connector tagged value (Quick Linker constraint) | MCP API — `set_connector_tagged_value` / `get_connector_tags` / `list_connector_tagged_values` / `delete_connector_tagged_value` |
| Element appearance — background, font, border | MCP API — `set_element_appearance` for the model-wide default; `set_diagram_object` for one placement on one diagram |
| Export a profile | MCP API — `publish_package_as_profile` (always pass `version`) |
| Build the MDG | **EA 17.1+:** `Specialize ▸ Publish Technology ▸ Save Package as MDG Technology` — one command over the package tree, no `.mts`. **Pre-17.1:** COM `Repository.GenerateMDGTechnology(mtsFilename)`, whose `.mts` has to come from the wizard first. No MCP operation for either |
| Reference data (tagged value types) | COM — `Project.ImportReferenceData` / `ExportReferenceData`, `Repository.PropertyTypes()`. No MCP operation |
| Verify anything | MCP API + parse the built XML, **and look at the UI** |

The rule that keeps this efficient: **build with the API, verify with both.**

> ### Three surfaces, not one
>
> "No MCP operation" does not mean "impossible". You have three ways to do anything in EA,
> and they are not ranked by preference alone:
>
> | Route | Use it when |
> |---|---|
> | **MCP operation** | One exists. Fastest, and the only one that needs nothing on screen |
> | **COM directly** (see **ea-com**) | EA exposes it but the MCP server does not wrap it yet — as with the two COM rows above |
> | **EA's UI with computer use** | Neither of the above, *or* you need to see what actually happened |
>
> The UI is not a fallback. The API tells you a call returned; the UI shows you what the
> model now looks like and surfaces the error dialogs EA raises instead of returning errors.
> Use them together — see
> [`../_shared/references/ea-ui-verification.md`](../_shared/references/ea-ui-verification.md).
>
> Before concluding EA cannot do something, read its type library. It takes two minutes and
> gives you the real method and parameter names:
>
> ```python
> ti = repo.GetProjectInterface()._oleobj_.GetTypeInfo()
> # walk GetFuncDesc / GetNames
> ```

> **Re-check this table against all three surfaces before each release** — the MCP operation
> list, EA's COM type library, and the UI. Checking only the MCP operation list tells you
> what we wrap, not what EA can do.

---

## Phase 0 — Protect the baseline before you touch anything

Skipping this is the single most expensive mistake available, because one step in Phase 3 is irreversible in a way that leaves no error and no visible symptom.

| # | Task |
|---|---|
| 0.1 | Confirm the current technology is imported **and enabled** in the target repository |
| 0.2 | Re-export the current profiles and diff them against the deployed file; account for every delta |
| 0.3 | Rebuild a current-version-equivalent MDG from the source |
| 0.4 | Archive every artifact — profile XMLs, `.mts`, MDG — into a `Files` package |
| 0.5 | Baseline the source packages |
| 0.6 | Rename the baseline package roots unmistakably, e.g. `[3.0.14 BASELINE - DO NOT EDIT]` |

⚠ **0.4 gates Phase 3.** Tagged Value Types live in `t_propertytypes`, which is **repository-wide**. The moment a new-version type is added, any export from the old profile packages stops being the old version — silently, with no error and no visible change in the Browser. Archive first or the baseline is unrecoverable.

⚠ **0.1 needs the UI — which means computer use, not a manual detour.** Untick "Hide disabled Technologies" in Manage Technology. `get_mdg_from_runtime` separates present-but-disabled from absent only where it can read the technology's XML: `registered_not_loaded` means registered and readable but not loaded, while `unknown_mdg` for a technology with no readable copy cannot tell disabled from never installed. Drive it with computer use and screenshot the result; only ask the user to do it by hand if computer use is unavailable in the session.

⚠ **0.6 matters more than it looks.** A duplicated profile package has the same name as its source — both trees show a child called `WBA`. Renaming the baseline root is the cheapest protection for the remaining phases, and unlike locking it blocks nobody.

**Verifying baseline scope.** A package baseline covers the whole subtree. Confirm it rather than assume: a package holding no elements directly still produces a large compressed payload if its children are captured.

```sql
SELECT DocID, DocName, LENGTH(BinContent) AS bytes
FROM t_document WHERE DocType = 'Baseline'
```

> **Use `LENGTH`, never `OCTET_LENGTH`.** A `.qea` repository is SQLite, which has no
> `OCTET_LENGTH` function. EA answers an unrunnable query with a **modal dialog**, which blocks
> the calling tool until someone clicks OK at the machine — it does not return an error you can
> catch. `LENGTH(...)` returns the byte count of a BLOB and is the correct form.

---

## Phase 1 — Package structure

```
Model
├── <Tech> design metamodel V<n>     ArchiMate view, human-readable
└── <Tech> profile V<n>
    ├── <Tech>  «profile»            stereotypes, metaclasses, constraints
    ├── <Tech>  «diagram profile»    custom diagram types
    └── <Tech>  «toolbox profile»    toolbox pages, one diagram per toolbox
```

### Where this tree comes from

Two cases, and they start differently.

**A later version of a technology that already has one** — duplicate the existing tree. That is
the rest of this phase.

**A first version, generated from what the repository already contains** — there is nothing to
duplicate, so the tree is created and populated from a census. That is a different procedure:
see [references/generating-from-a-census.md](references/generating-from-a-census.md). Route there
from `ea-mdg-assess` §2a, which is where path B is chosen and recorded.

⚠ **The child package's stereotype routes its content into a section of the built MDG** —
`«profile»` → `<UMLProfiles>`, `«toolbox profile»` → `<UIToolboxes>`, `«diagram profile»` →
`<DiagramProfile>`. Stereotyping all three `«profile»` piles everything into `<UMLProfiles>` and
the other two sections come out empty. Measured. Our own MDG book says EA accepts either and
repeats the error in its own dev model — it does not.

---

Duplicate with `ea_model(operation="duplicate_package", ...)`, which generates fresh GUIDs
throughout — the API equivalent of Paste as New. It does not carry diagrams or diagram
objects; if the package holds diagrams you need, use Paste as New in the UI instead, or copy
them separately. XMI export/import is not a substitute — it does not dependably strip GUIDs,
and two packages claiming the same profile `id` is worse than a manual copy.

**Verify the copy immediately** — element counts, attribute counts, connector counts and diagram populations against the source, and confirm no cross-package leakage back into the original's metaclasses.

Record the new package GUIDs and the toolbox **diagram** GUIDs. The profile `id` values in the built MDG are derived from them, and that is how you later prove a file was built from the right source.

---

## Phase 2 — Profile mechanics

Read from working stereotypes so new work matches. Every one of these is a modeling convention, not an EA feature you can look up.

| Aspect | Mechanism |
|---|---|
| Stereotype | Class with stereotype `«stereotype»`, in the `«profile»` package |
| Display name | Attribute `_metatype`, `Default` = friendly name |
| Enforcement | Attribute `_strictness`, `Default` = `profile` |
| Tagged value | Attribute. `Type` blank for enums — the type comes from reference data of the same name — or a primitive (`int`, `Date`) |
| Metaclass binding, every base | **Extension** connector to the plain `«Metaclass»` element — ArchiMate included |
| Quick Linker rule | **Dependency** stereotyped `stereotyped relationship`, with a **connector tagged value** `stereotype = <Tech>::<Relationship>` |

⚠ **A stereotype with no Extension never exports.** It will sit in the profile package looking complete — tags, `_metatype`, even constraints — and appear in no MDG. If a stereotype is missing from a built file, check its Extension first.

⚠ **`Generalization` is not an alternative to `Extension`, for any base.** An earlier version of the table above offered it for ArchiMate-derived stereotypes. Measured against EA 17.1 build 1716: three builds made that way came out with `Apply=0` and every stereotype extending nothing. Converting one connector to `Extension` produced exactly one `<Apply type="Component"/>`; converting all twenty produced `Apply=20`, an exact match to the authored file. The Profile toolbox's *Profile Relationships* page lists Extension, Generalize, Tagged Value and Redefines — only Extension binds a stereotype to a metaclass. The book's prose calls it "Extend", which is what made this easy to get wrong.

⚠ **Namespace-qualify every constraint value.** `WBA::WBABusinessApplication`, never `WBABusinessApplication`. Unqualified constraints do not resolve and fail silently. Where `_strictness = profile` is set, enforcement is live against a rule that cannot resolve — the worst combination.

**Connector tagged values are scriptable.** Use `set_connector_tagged_value`, and read them back with `get_connector_tags` or `list_connector_tagged_values`. `update_connector` ignores a tagged value passed as an ordinary property — use the dedicated operations, not a property write.

**Telling identical connectors apart.** Two reflexive connectors on the same element are indistinguishable in EA's Relationships grid, which shows no name and no stereotype column. Set a temporary name on the new one, do the work, then clear it — and verify the clear.

---

## Phase 3 — Reference data

⚠ **Do not start until Phase 0.4 is archived.**

Tagged value types live in `t_propertytypes` and are repository-wide, not per-profile.

**Check what already exists before authoring anything.**

```sql
SELECT Property, Notes FROM t_propertytypes ORDER BY Property
```

A type is defined if `Notes` carries `Type=Enum;Values=...;` or `Type=Date;` etc. Types frequently already exist and have simply never been **selected into a build** — see Phase 5. A tag behaving as free text does not prove the type is missing.

### Enum domains from a census

Where the technology is being generated (Phase 1), the census supplies candidate domains: for each
tag it reports the distinct values actually in use, and flags a tag whose values look like a closed
set rather than free text.

**Treat an inferred domain as a candidate, never as the answer.** Observation can only ever show
the values that happen to have been used, so a domain derived from a repository is a lower bound.
Two consequences worth acting on rather than smoothing over:

- **A value in use that no declared domain allows is a finding, not noise.** If the repository
  already carries a technology, compare its declared domain against observed usage before writing
  reference data — a live value outside the declared set means something stopped validating, and
  importing the observed set silently blesses it.
- **A declared value nobody has used is usually fine.** It is a process that has not happened yet,
  not a mistake. Do not prune a domain to match observation.

Where the repository has a loaded technology, `ea_mdg(operation="get_mdg_from_runtime", ...)`
returns its **complete** declared domains, which beat anything inferred. Use those and keep the
census's observed values for the comparison above.

Where a profile carries Enumeration classes on a data-types diagram, those value lists are usually accurate and complete. Transferring them into reference data is a transfer, not a harvesting exercise.

**Check defaults against real values in use.** A default absent from its own value list means the dropdown cannot round-trip data the repository already holds:

```sql
SELECT [Value], COUNT(*) FROM t_objectproperties WHERE Property = '<tag>' GROUP BY [Value]
```

`Value` is a reserved-word column on `t_objectproperties` — bracket it, or the query is rejected. (See the `ea-modeling` SQL reference for the full reserved-word list.)

⚠ **Renaming a tag orphans its values** in `t_objectproperties`. Fix trailing spaces and spelling before a production load, never after.

---

## Phase 4 — Toolbox and diagram profiles

Toolbox pages are **elements on the toolbox diagram**. Each page's entries are **attributes** on the page element:

| Attribute field | Meaning |
|---|---|
| `Name` | `<Tech>::<Stereotype>(UML::<Metaclass>)` |
| `Default` | The label shown in the toolbox |
| `Type` | Leave blank — a populated `Type` is a defect |

So toolbox work is `create_attribute` / `update_attribute` / `delete_attribute` against the page element. Fully API-scriptable.

**Deleting a stereotype leaves its toolbox entry behind.** Removing a stereotype from the profile does not touch the toolbox, and a dangling entry points at nothing. Sweep the toolbox after every stereotype removal.

**A stereotype on no toolbox page ships invisible.** It exists, it validates, and no user can place it.

---

## Phase 5 — Build

Two halves, and only the first is scriptable today. The sequence matters and several steps are easy to get subtly wrong.

1. **Export each profile** — `ea_mdg(operation="publish_package_as_profile", ...)`.
   - The UML profile exports from the `«profile»` package.
   - The diagram profile exports from the `«diagram profile»` package.
   - **Each toolbox exports from its diagram**, which has no MCP operation — use `Repository.SaveDiagramAsUMLProfile(dgmGUID, Filename)` through COM, or `Publish Diagram as UML Profile` in the UI.
2. **Build the MDG.** Which command depends on the EA version, and they are not interchangeable:

   **EA 17.1+ — `Specialize ▸ Publish Technology ▸ Save Package as MDG Technology`.** Point it at the
   `«mdg technology»` package and it assembles the whole technology from the package tree in one
   step: no intermediate profile exports, no `.mts`, a Save As dialog, and `MDG Technology
   successfully saved to file`. This is the route to use on a current EA.

   Two things to know before relying on it:

   - **The technology id comes from the package name**, and a name over 12 characters has been
     seen truncated (`WBA Technology` became `WBA Technolo`) on one route and kept whole on
     another. Name the package for the id you want, in 12 characters or fewer.
   - **Generated files come out with an empty `version` attribute**, and setting the package
     `Version` beforehand does not carry through. Stamp it afterwards — two unversioned builds are
     indistinguishable in Manage Technologies, which is a mistake that has already been made here.
   - **Read System Output, not just the return.** It carries diagnostics the result does not, such
     as `WARNING: Duplicate profile name: …`.

   **Pre-17.1 — the MTS Generation Wizard**, `Specialize ▸ Publish Technology ▸ Generate MDG
   Technology`. Needs the `.mts` described below, and needs the profile exports from step 1. Use it
   only when the EA in front of you predates 17.1.

   ⚠ **`Save Package as MDG Technology` and `Import Package as MDG Technology` do different
   things.** Save writes a file and installs nothing. Import builds the same technology and imports
   it into the open model at Location: Model (one `t_document` TECHNOLOGY row, toolbox pages
   included) and writes no file. Measured on EA 17.1 build 1716; `t_trxtypes` is not touched by
   Import, so checking it reports a failure that did not happen. Deploying is Phase 7.

```python
ea_mdg(operation="publish_package_as_profile", params={
    "package_id": 4213,
    "output_path": r"<build-dir>\WBA-profile.xml",
    "version": "3.0.14",
})
```

⚠ **Always pass `version`.** EA reads a package's `Version` property the first time that package is published in a session and then caches it — republish after changing the package and you get the old value, silently. This is the same stale-version failure the UI export dialog has, and it is why the operation takes an explicit `version` and stamps it into the generated XML rather than trusting EA. The response reports `version_from_ea` alongside it, so you can see what EA would have shipped.

⚠ **`Publish Diagram as UML Profile` is greyed out unless the diagram is open.** Selecting it in the Browser is not enough.

⚠ **The MTS wizard route is for pre-17.1 only, and its `.mts` cannot be hand-written.** On EA 17.1+ use `Save Package as MDG Technology` above and skip this entirely. `Repository.GenerateMDGTechnology(mtsFilename)` is callable and validates its argument, but the `.mts` schema is not published — Sparx documents the root element, the hand-edited `<ModelValidation>` and `<ModelTemplates>` sections, and the wizard's section list, but not the element names the wizard writes per section or the on-disk form of the tagged-value-type inclusion list. A hand-reconstructed file is rejected for reasons nothing explains. Run the wizard once to emit a real `.mts`, keep it under version control, and edit that file from then on.

⚠ **The wizard's Tagged Value Types page is a selection step, not an inclusion step.** Types not selected here do not ship, however completely they are defined. This is the usual cause of "the type exists but the field is still free text" — and because the omission is invisible in the model, it can persist across many releases. Detect it: `ea-validation`'s `tagged_value_type_shipped` rule condition compares a profile's blank-`Type` tagged-value attributes against a built MDG file's RefData and flags anything defined but not shipped. Run it as part of Phase 6 verification.

⚠ **Match the Contents checkboxes to the shape of the current deployed file** rather than guessing. Parse the deployed file and tick to match:

```
<MDG.Technology>
  <Documentation/>      → (header fields)
  <UMLProfiles>         → Profiles
  <TaggedValueTypes>    → Tagged Value Types
  <DiagramProfile>      → Diagram Types
  <UIToolboxes>         → Toolboxes
```

**Filenames.** Use stable unversioned names in the build folder — the `.mts` references the profile XMLs **by filename**, so versioned names force a rename and an `.mts` rebuild every release, and a stale `.mts` silently ships the previous version's content. Add the version only when archiving.

---

## Phase 6 — Verify

Verification is API work and should be mechanical. Parse the built XML and compare against the source.

**The check that catches the expensive mistake:** the four profile `id` values must match the V<n> package and diagram GUIDs recorded in Phase 1, not the previous version's. A correctly-versioned file built from the wrong package source passes every other check.

The `id` is a 10-character slice of the GUID:

```
Package GUID {8D977401-A156-34A8-9198-C05706C802DE}
Profile id                          C05706C802
```

**A full structural diff is worth automating.** Load both files, build `{stereotype: {base, generalizes, bgcolor, tags, constraints}}` and compare. Anything other than the deltas you intended is a finding.

Checklist:

- [ ] Profile `id` values match the current source packages
- [ ] Every new stereotype has `baseStereotypes` populated — an empty one is the symptom of a missing Extension connector, and the stereotype will not appear in the built MDG. `generalizes` is only populated where the stereotype derives from another *stereotype*; most do not, and an empty `generalizes` is not a fault
- [ ] Every constraint value is namespace-qualified
- [ ] Widened constraints list all targets, semicolon-separated
- [ ] Removed stereotypes absent — and similarly-named ones still present
- [ ] New tagged value types present on their stereotypes **and** in `RefData`
- [ ] All profiles stamped with the new version

⚠ **Match on exact strings, never prefixes.** Profiles routinely contain near-identical names (`AI Technology` vs `AI Type`) whose blast radius differs by an order of magnitude.

---

## Phase 7 — Deploy

An MDG is deployed either **into the repository** (a model technology, picked up by everyone connecting to it) or **as a file registered on a workstation** (a runtime technology, seen only by that machine). They look identical in Manage Technology apart from the `Location` field. See `ea-mdg-deploy`'s Deployment Modes table for the mechanics; this phase is about the traps that show up once a *model-driven* build is what's landing on top of them.

| Location | Scope | How a model-driven build gets there |
|---|---|---|
| `Model` | Every user of that repository, whole technology | `install_mdg(scope="model", package_id=<«mdg technology» package>)` (server later than 3.5.0), or Import Package as MDG Technology in the UI |
| `Project` | Every user of that repository, **without toolbox pages** | `install_mdg(scope="embedded", xml_path_or_content=<saved file>)`. Avoid for a technology that has toolbox pages |
| A file path | That workstation only | `install_mdg(scope="user", xml_path_or_content=<saved file>)` |

A model-driven technology belongs at **Location: Model**: it is the only in-model Location that keeps
the toolbox profiles this skill builds in Phase 4.

⚠ **EA auto-registers any MDG file found on its search path.** The path list is at `Manage Technology ▸ Advanced`, and it routinely includes a user's `Downloads` folder. A build written there registers itself silently, shadows the model copy, and makes deployment appear to succeed on the author's desktop while nothing changes for anyone else. The search path is **not** recursive — a subfolder is safe.

**Before validating any deployment**, check Manage Technology with "Hide disabled Technologies" unticked and confirm one entry, at `Location: Model`, at the expected version. More than one entry for the same technology means something is shadowing something else.

Then: import, confirm **enabled** rather than merely present, **restart EA** (until then the toolbox may not switch to the new pages, though they are already loaded), and validate on a scratch diagram — toolbox page, Quick Linker, tag dropdowns — before any content is touched. Measured for WBA 1.1.1 after a restart: each of the three diagram types opened its own page (12, 5 and 5 items), and a dragged item came out bound to `WestbrookBankArchitecture::`.

---

## Gotchas

| Symptom | Cause |
|---|---|
| Stereotype missing from the built MDG | No Extension to a metaclass |
| Tag ships as free text despite a complete definition | Not selected on the wizard's Tagged Value Types page — run `ea-validation`'s `tagged_value_type_shipped` rule to detect this |
| Quick Linker rule never fires | Constraint value not namespace-qualified |
| Toolbox entry points at nothing | Stereotype deleted, toolbox not swept |
| New stereotype invisible to users | On no toolbox page |
| An element's color changed on one diagram but not the others | `set_diagram_object` restyles one placement. The model-wide default is `set_element_appearance` |
| A color comes out with red and blue swapped | An integer color is EA's Win32 COLORREF, `0x00BBGGRR` — `255` is red, not blue. Pass `"#RRGGBB"` instead and the swap is handled for you |
| Published profile carries the wrong version | `version` was omitted, so EA supplied its cached value — always pass it |
| Connector tagged value not applied | `update_connector` ignores it as a property — use `set_connector_tagged_value` instead |
| `get_mdg_from_runtime` says `unknown_mdg` | EA reports nothing loaded under that exact id, and neither a registered technology file nor the model holds its XML. The registered id often differs from the display name — confirm it in Manage Technology |
| `get_embedded_mdgs` returns empty on a server up to 3.5.0 | Those servers read a document type none of EA 17.1's import routes writes. Later servers list both in-model Locations. Confirm in the UI |
| Designed toolbox pages missing; one automatic page instead | The technology is at Location: Project, which stores no toolbox pages. Install at Location: Model |
| `get_mdg_from_runtime` answers from version A while Manage Technology shows version B | The same id is stored at both Locations and EA answers from Project. Remove one; `provenance.also_stored` names the other |
| Only the author sees the new version | File-based registration shadowing the model copy |
| Export produces the previous version's content | `.mts` still referencing old filenames |
| A query hangs and EA shows "SQL API Open FAILED" | The SQL used a function this backend lacks (e.g. `OCTET_LENGTH` on a `.qea`). Click OK on the dialog; use `LENGTH(...)` |

---

## Working rules

- **Ask before writing SQL** against a live repository, and never assume `execute_sql` is read-only — it accepts writes.
- **Never edit the baseline packages.** Protect them by renaming; lock only where you know who the lock applies to.
- **Do not fix things out of sequence.** A toolbox defect found during profile work is recorded, not corrected — nothing exports until the build phase, and out-of-sequence edits are how verification stops being meaningful.
- **Measure against the repository, not against the plan.** Counts in planning documents go stale, and a sandbox is not production.

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

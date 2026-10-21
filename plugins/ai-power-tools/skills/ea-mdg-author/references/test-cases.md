# Acceptance cases: `ea-mdg-author`

This skill promises to write a Sparx EA MDG Technology XML file that EA actually loads, and to stop
before it hand-edits a technology that has a source model. Almost every failure here produces a
plausible file, not an error: an id one character too long, a stereotype on the wrong metaclass, a
toolbox whose namespace does not match, a menu that comes up empty, a dropdown that installs as a
text box. EA accepts the file, reports `True`, and the damage shows up later. This file is built to
catch those, and to catch the one that costs most: an edit to an XML file that the next model-driven
export silently overwrites.

**Fixture.** A fresh copy of the Westbrook Bank model opened in EA (technology `WBA`, qualified
stereotype form `WBA::`, for example `WBA::WBABusinessApplication`). The copy holds the source model
of the `WBA` technology: a `WBA Technology` package with an `mdg technology` package, a `profile`,
a `diagram profile` and three `toolbox profile` packages. Westbrook Bank is our illustration. A
customer runs these cases against their own model, substituting their technology, stereotypes and
package names. Authoring cases write a trial technology file (`WBAMini`, a subset of the real
stereotypes) into the run's working folder; the runner reads that file back with `parse_mdg_xml`.
Counts quoted below describe the Westbrook copy at the time of writing.

**Marks.** `WRITE` (the run changes the copy), `EFFECT` (the run writes a file outside the model;
the case says which), `REFUSE` (the pass is a refusal, a stop, or a hand-off), `INVARIANT` (must
pass on every run), `BLOCKED` (needs setup the run may not have).

## Cases

### TC-01: A technology with a source model is not hand-edited

Covers: Before you start — does this MDG already have a source model?

**Marks:** REFUSE, INVARIANT

**Ask:** "Add a Payment Rail stereotype to our WBA MDG file. Just edit the XML directly, it's quicker."

**Passes when:** The run looks for a source model before touching the XML, finds the profile packages in the `WBA Technology` package, and stops. It tells the person that an XML edit would be overwritten by the next model-driven export with no warning, and routes the job to `ea-mdg-model-build`. If it cannot tell whether a source model exists, it asks before editing. The model is unchanged and no MDG XML was generated.

**Check:**

```check
# ground truth: the technology has a source model (technology, profile, diagram profile, three toolbox profiles)
sql: SELECT COUNT(*) FROM t_object WHERE Stereotype IN ('mdg technology', 'profile', 'diagram profile', 'toolbox profile')
expect: = 6
```

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

```check
tools: not-called: ea_mdg.write_mdg_xml
tools: not-called: ea_mdg.install_mdg
reply: says: the technology has a source model in the repository
reply: says: an edit to the XML is lost the next time the model-driven export runs, with no warning
reply: says: the change belongs in the source model and hands off to ea-mdg-model-build
reply: not: reports the stereotype was added to the XML
```

**Fails when:** The run opens the XML, adds a `Payment Rail` stereotype, and reports success. The file loads, the stereotype appears, and nothing errors. The profile packages in the model never learn about it, and the next export from the model silently removes it. A second wrong shape: the run decides the question by whether an XML file exists on disk, which is true of every shipped technology.

### TC-02: A new technology gets all three sections, one namespace

Covers: Authoring workflow; Namespace Consistency Checklist

**Marks:** EFFECT

**Ask:** "I want to try a small trial technology called WBAMini on a scratch model: just the Business Application and Vendor System stereotypes, a diagram type for application views, and a toolbox page for them. Write the MDG file as <output-dir>\WBAMini.xml."

**Passes when:** The run writes one `<MDG.Technology>` file with a UML profile, a diagram profile and a toolbox section, and the technology id is the same wherever it is referenced: the root, the top-level documentation, the UML profile documentation and the toolbox tag prefix. It builds element stereotypes before diagram types and toolboxes, and it hands installation to `ea-mdg-deploy` rather than declaring the file good. The file parses.

**Check:**

```check
call: ea_mdg.parse_mdg_xml {"path_or_content": "<output-dir>\\WBAMini.xml"}
expect: technology_id = WBAMini
```

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

```check
reply: says: the file has a UML profile, a diagram profile and a toolbox section
reply: says: the technology id matches in the root, the documentation, the profile and the toolbox tags
reply: says: the file has not been installed or tried in EA yet
reply: not: reports the technology works
```

**Fails when:** The file has a profile and stereotypes but no diagram profile or toolbox, or the toolbox tags read `WBAMini::` while the profile documentation carries a different id. EA loads it, the stereotypes work, and the toolbox never resolves. The id mismatch is the most common reason a toolbox fails and nothing reports it.

### TC-03: Business Application is a Component

Covers: Section 1 — Element Stereotype

**Marks:** EFFECT, INVARIANT

**Ask:** "Add a Business Application element type to <output-dir>\WBAMini.xml. It's an application the bank runs, with a criticality dropdown, a lifecycle dropdown and a business owner field."

**Passes when:** The stereotype is `WBABusinessApplication`, applied to the `Component` metaclass, carrying the three tags. The run says it chose Component because that is the metaclass the Westbrook technology declares for this concept, not Class. The file parses.

**Check:**

```check
call: ea_mdg.parse_mdg_xml {"path_or_content": "<output-dir>\\WBAMini.xml"}
expect: technology_id = WBAMini
```

```check
# the real technology declares this stereotype against Component; the model shows it in use that way
sql: SELECT DISTINCT Object_Type FROM t_object WHERE Stereotype = 'WBABusinessApplication'
expect: rows: [["Component"]]
```

```check
reply: says: the stereotype is applied to Component
reply: not: applies WBABusinessApplication to Class
```

**Fails when:** The stereotype is applied to `Class`. The file loads and the element can be created, but it is not the metaclass the technology declares, the toolbox in the real technology never offers it, and every conformance rule that selects by metaclass misses it. Nothing errors.

### TC-04: Tagged value types are spelled the way EA reads them

Covers: Quick Reference

**Marks:** EFFECT

**Ask:** "In <output-dir>\WBAMini.xml, give Business Application a criticality dropdown (Mission-Critical, Business-Critical, Important, Standard), a free-text business owner, and a checkbox for 'reviewed'."

**Passes when:** The dropdown tag has type `enumeration` with its values as a comma-separated `values=` list, the free-text tag has type `String` with a capital S, and the checkbox is `Boolean`. The run does not write `enum` or `string`. The file parses.

**Check:**

```check
call: ea_mdg.parse_mdg_xml {"path_or_content": "<output-dir>\\WBAMini.xml"}
expect: technology_id = WBAMini
```

```check
reply: says: the dropdown is type enumeration, the free-text field is type String, the checkbox is type Boolean
reply: not: uses enum as a tag type
```

**Fails when:** The dropdown is written `enum` or `Enumeration`, or the text field `string`. The file loads, the tag exists, and EA shows a plain text box with no list. A person fills in `Mission Critical` with a space and no conformance rule can tell.

### TC-05: A long technology id is caught before EA rejects it

Covers: Quick Reference

**Marks:** EFFECT, INVARIANT

**Ask:** "Write an MDG file for a trial technology called WestbrookBankPortfolio with just the Business Application stereotype and a diagram type. Save it as <output-dir>\TrialPortfolio.xml."

**Passes when:** The run notices the name is too long for an id, since every `id=` attribute is limited to 12 characters and the diagram and toolbox ids are derived from the technology id with a suffix. It uses a short id (7 characters or fewer) and keeps `WestbrookBankPortfolio` as the display name, or asks the person which short id to use. It says which it chose.

**Check:**

```check
reply: says: ids are limited to 12 characters and either the technology id was shortened (WestbrookBankPortfolio kept as the display name) or the person was asked which short id to use
reply: not: uses WestbrookBankPortfolio as the technology id
```

**Fails when:** The file uses `WestbrookBankPortfolio` as the id. EA silently fails to load the technology, and the run reports a file written. The id length is checked by the Invariants section, because the check grammar cannot assert a length.

### TC-06: Colors are written in EA's byte order

Covers: Quick Reference

**Marks:** EFFECT

**Ask:** "Make Business Application elements light blue in <output-dir>\WBAMini.xml, the soft one, RGB 180, 210, 240. Tell me the exact number you put in the file."

**Passes when:** The run writes `bgcolor="15782580"` and says so. That is blue times 65536 plus green times 256 plus red, not the RGB order.

**Check:**

```check
call: ea_mdg.parse_mdg_xml {"path_or_content": "<output-dir>\\WBAMini.xml"}
expect: technology_id = WBAMini
```

```check
reply: says: the color value is 15782580
reply: not: the color value is 11850480
```

**Fails when:** The run computes the integer in RGB order (11850480) or writes a hex string. The file loads and the element shows a pale orange-brown instead of light blue. Nothing errors.

### TC-07: The file is UTF-8 and says so

Covers: File Encoding (Critical)

**Marks:** EFFECT

**Ask:** "Write <output-dir>\WBAMini.xml with the technology notes 'Westbrook Bank — application portfolio, café-style naming trial' so the Manage Technologies dialog shows them."

**Passes when:** The declaration reads `encoding="utf-8"` and the bytes are UTF-8, so the em dash and the accented letter survive. The file parses and the notes come back intact.

**Check:**

```check
call: ea_mdg.parse_mdg_xml {"path_or_content": "<output-dir>\\WBAMini.xml"}
expect: technology_id = WBAMini
```

```check
reply: says: the file is declared and written as utf-8
reply: not: converts the notes to plain ASCII to avoid the question
```

**Fails when:** The declaration says `utf-8` and the bytes are `windows-1252` (or the reverse). EA rejects the file outright, or shows garbled notes, depending on the route; a parser that is lenient hides the mismatch until EA opens it.

### TC-08: ArchiMate shapes are not used as base types

Covers: Section 1 — Element Stereotype

**Marks:** INVARIANT

**Ask:** "For our own Business Application and Business Service types, base them on ArchiMate's Application Component and Business Service so they line up with the ArchiMate model. Is that fine?"

**Passes when:** The run says no, with the reason: elements based on an ArchiMate or BPMN shape are invisible in the Project Browser tree unless that language is active at project scope, even though they still show on diagrams and in SQL. It recommends a standard UML base (`Component` for these two) and carrying the ArchiMate concept in the stereotype name, tags and documentation. The model is unchanged.

**Check:**

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

```check
reply: says: elements with an ArchiMate base type are invisible in the Project Browser tree unless that language is active at project scope
reply: says: the base should be a standard UML type such as Component
reply: not: agrees to base the stereotypes on Application Component
```

**Fails when:** The run agrees and writes `<Apply type="ApplicationComponent"/>`. The file loads, the elements are created, they appear on diagrams, and the person spends an afternoon looking for them in the tree.

### TC-09: Fixing a wrong base type uses a database update

Covers: Section 1 — Element Stereotype; Tool Selection

**Marks:** WRITE

**Setup:** The runner sets `Object_Type` to `ApplicationComponent` on the three elements stereotyped `WBAAIService` on the copy.

**Ask:** "The AI Service applications are on the diagrams and in queries, but they don't show up in the Project Browser tree. Can you get them to show up again?"

**Passes when:** The run recognizes the stored base type as the cause, sets `Object_Type` back to `Component` by a database update (`repo.Execute()`), not by assigning `elem.Type`, which silently does nothing for ArchiMate types, and tells the person to close and reopen the project so EA's cache refreshes. Only the three elements change.

**Check:**

```check
sql: SELECT COUNT(*) FROM t_object WHERE Stereotype = 'WBAAIService' AND Object_Type = 'Component'
expect: = 3
```

```check
sql: SELECT COUNT(*) FROM t_object WHERE Object_Type = 'ApplicationComponent'
expect: = 0
```

```check
reply: says: the project must be closed and reopened to flush EA's cache
reply: not: reports the fix done after setting the element type through the COM property
```

**Fails when:** The run sets `elem.Type = "Component"`, receives no error, and reports the fix. The database still says `ApplicationComponent`, the SQL above returns 0 and 3 the wrong way round, and the tree is still empty.

### TC-10: Relationships use the shipped connector stereotypes

Covers: Section 1 — Connector Stereotype

**Marks:** INVARIANT

**Ask:** "I need a way to show that a Business Application runs on a Vendor System. Which connector should I use, and can you add a WBA::dependsOn stereotype to the technology for it?"

**Passes when:** The run says the Westbrook technology declares three connector stereotypes (`Uses`, `Flows`, `realizes`), recommends `Uses` or a plain Dependency, and says `dependsOn` is not part of the technology. If the person still wants a new connector stereotype, the run offers it labeled plainly as a proposed extension. It does not present `dependsOn` or `WBARunsOn` as shipped. The model is unchanged.

**Check:**

```check
sql: SELECT COUNT(*) FROM t_object WHERE Stereotype = 'stereotype' AND Name IN ('Uses', 'Flows', 'realizes')
expect: = 3
```

```check
sql: SELECT COUNT(*) FROM t_object WHERE Stereotype = 'stereotype' AND Name IN ('dependsOn', 'WBARunsOn', 'mastersData')
expect: = 0
```

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

```check
reply: says: the technology declares Uses, Flows and realizes as its connector stereotypes
reply: says: any new connector stereotype is a proposed extension, not part of the shipped technology
reply: not: describes dependsOn as part of the WBA technology
```

**Fails when:** The run adds `WBA::dependsOn` and describes it as the technology's vocabulary. The XML is valid, the stereotype appears, and the technology now contradicts the model and every modeling skill that reads the shipped three.

### TC-11: A custom diagram type points at a toolbox that exists

Covers: Section 2 — Custom Diagram Type

**Marks:** EFFECT, INVARIANT

**Ask:** "Add an Application View diagram type to <output-dir>\WBAMini.xml that opens with the application toolbox page showing."

**Passes when:** The diagram stereotype applies to `Diagram_Logical` (not `Logical`), carries an alias and a `diagramID`, and its `toolbox` property names the toolbox consistently with the toolbox section. The run says the exact form EA resolves should be tried on a scratch diagram before anyone relies on it, since the two forms the skill documents differ. The file parses.

**Check:**

```check
call: ea_mdg.parse_mdg_xml {"path_or_content": "<output-dir>\\WBAMini.xml"}
expect: technology_id = WBAMini
```

```check
reply: says: the diagram type applies to Diagram_Logical
reply: says: the toolbox property has not been proven until it is tried on a scratch diagram in EA
reply: not: reports the toolbox switches on when the diagram opens
```

**Fails when:** The file uses `Apply type="Logical"`, or the `toolbox` property names a page that does not exist. The technology loads, the diagram type is listed, and the toolbox never appears. The run reports a working diagram type it has never opened.

### TC-12: A toolbox page lists qualified stereotypes

Covers: Section 3 — Toolbox Pages

**Marks:** EFFECT

**Ask:** "Give <output-dir>\WBAMini.xml a toolbox page called 'WBA ArchiMate Elements' with Business Application, Business Service and Vendor System on it."

**Passes when:** The page is one stereotype applied to `ToolboxPage`, with one tag per item, each tag named `<technology prefix>::<stereotype>` (for example `WBA::WBABusinessApplication` in the real technology) with the palette label as the default. The prefix is the one the profile documentation declares. The file parses.

**Check:**

```check
call: ea_mdg.parse_mdg_xml {"path_or_content": "<output-dir>\\WBAMini.xml"}
expect: technology_id = WBAMini
```

```check
reply: says: the page has one tag per palette item, named with the technology prefix and the stereotype name
reply: says: the prefix matches the profile documentation id
```

**Fails when:** The tags name bare stereotypes (`WBABusinessApplication`) or use a prefix that matches nothing. EA loads the page, shows it empty, and reports nothing.

### TC-13: An unresolved toolbox is a namespace question first

Covers: Namespace Consistency Checklist

**Ask:** "I installed the trial technology and the call said True, but the toolbox for our Application View diagram never shows up. What's the most likely cause?"

**Passes when:** The run starts with the namespace: the technology id, the top-level documentation id, the UML profile documentation id, the toolbox tag prefixes and the diagram `toolbox` property must agree. It asks to see the file or reads it, and checks the loaded and enabled state afterwards. It does not start by blaming EA or reinstalling. The model is unchanged.

**Check:**

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

```check
reply: says: the first thing to check is that the technology id matches everywhere it is referenced
reply: says: the toolbox tag prefix and the diagram's toolbox property must name the same namespace
reply: not: suggests reinstalling before reading the file
```

**Fails when:** The run says "restart EA and reinstall", the toolbox is still missing, and the id mismatch that caused it is never found.

### TC-14: Hiding the default link menu needs a rule behind it

Covers: Quick Linker Rules

**Marks:** EFFECT

**Ask:** "In <output-dir>\WBAMini.xml, switch off EA's default link suggestions on Business Application so people only see our options. We haven't defined any connector types of our own."

**Passes when:** The run warns that hiding the default entries with no Quick Linker rule leaves an empty menu that looks broken, and does not set `_HideUmlLinks`. It explains that plain Dependency, Realization and Association already appear in EA's default menu, and offers to add the hiding together with a rule once a connector stereotype exists (the shipped `Uses`, for example).

**Check:**

```check
reply: says: hiding the default links without at least one Quick Linker rule produces an empty menu
reply: says: plain Dependency, Realization and Association already appear in the default menu
reply: not: sets _HideUmlLinks with no rule
```

**Fails when:** The file carries `_HideUmlLinks` and no `stereotypedrelationship`. EA loads it and the hover menu is empty on every Business Application.

### TC-15: Validation rules do not go into Scripts

Covers: Validation Rules — Do NOT Use <Scripts> with AI Power Tools

**Marks:** EFFECT

**Ask:** "Make the trial technology flag any Business Application that has no criticality set. Put the check in the MDG file itself."

**Passes when:** The run does not add a `<Scripts>` section. It explains that script rules run in EA's scripting engine, which the tools cannot reach, and writes the rule as a `tagged_value_required` rule in a companion YAML file that `ea_validate` runs.

**Check:**

```check
reply: says: scripts embedded in the MDG run in EA's scripting engine, which the tools cannot reach
reply: says: the rule is written as a companion YAML file and run with ea_validate
reply: not: adds a Scripts section to the MDG file
```

**Fails when:** The MDG carries a JavaScript rule set. EA may run it; `ea_validate` never sees it, so no audit finds a violation and nobody knows the check is not running.

### TC-16: Every MDG ships with a rules sidecar

Covers: Validation Rules — Do NOT Use <Scripts> with AI Power Tools; Authoring workflow

**Marks:** EFFECT

**Ask:** "Write <output-dir>\WBAMini.xml with the Business Application stereotype, and criticality and businessOwner are mandatory."

**Passes when:** The run writes the MDG and a companion `<tech id>_rules.yaml` with one `tagged_value_required` rule per mandatory tag (two here), with rule ids in the form `<TechID>-TVR-001`. It mentions the sidecar to the person without being asked.

**Check:**

```check
call: ea_mdg.parse_mdg_xml {"path_or_content": "<output-dir>\\WBAMini.xml"}
expect: technology_id = WBAMini
```

```check
reply: says: a companion WBAMini_rules.yaml was written with a rule for criticality and a rule for businessOwner
```

**Fails when:** The MDG is written with the mandatory tags declared and no rules file. Mandatory means nothing, because nothing enforces it, and the person assumes it does.

### TC-17: Putting a technology in the model file keeps its toolboxes

Covers: Tool Selection

**Marks:** INVARIANT

**Ask:** "How do I get our MDG into the model file itself, so colleagues who open the .qea get it with its toolbox pages?"

**Passes when:** The run recommends installing at Location: Model (the Import to Model route in EA's Publish Technology menu, or `install_mdg` with `scope="model"` on a server later than 3.5.0) and warns that the legacy embedded route (`scope="embedded"`, Location: Project) drops toolbox pages, which the response reports as `not_stored`. It points a technology with toolboxes that will be maintained at a source model. The model is unchanged.

**Check:**

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

```check
tools: not-called: ea_mdg.install_mdg
reply: says: the embedded route drops the toolbox pages
reply: says: Location: Model is the route that keeps them
reply: not: recommends scope embedded without the toolbox warning
```

**Fails when:** The run calls `install_mdg` with `scope="embedded"` and reports the technology installed in the model. The stereotypes work and every toolbox page is missing for everyone who opens the file.

### TC-18: An empty embedded-technology list is not an answer

Covers: Tool Selection

**Ask:** "Which MDG technologies are stored inside this model file? I asked for the embedded list and got nothing back."

**Passes when:** The run says an empty `get_embedded_mdgs` is not proof on servers up to 3.5.0 with EA 17.1, because that call read a document type none of EA 17.1's import routes writes, and sends the person to Manage Technology (Specialize, then Technologies) as the authoritative view. It does not say the model holds no technologies.

**Check:**

```check
# ground truth: the copy does hold technologies stored in the model
sql: SELECT COUNT(*) FROM t_document WHERE DocType = 'TECHNOLOGY'
expect: >= 1
```

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

```check
reply: says: an empty result from the embedded list does not prove the model has none
reply: says: Manage Technology is the authoritative view
reply: not: concludes the model contains no technologies
```

**Fails when:** The run reads the empty list as "nothing embedded", tells the person to install the technology, and installs a second copy of one the model already holds.

### TC-19: A `True` from install is not proof

Covers: The sequence; Tool Selection

**Ask:** "I installed the updated WBA technology and the call returned True. So we're done, right?"

**Passes when:** The run says no. It checks that the technology is loaded and enabled (a disabled technology still reports loaded), and that its stereotypes, diagram types and toolbox pages behave, and hands the verification to `ea-mdg-deploy`. It does not say the install is confirmed on the strength of the return value.

**Check:**

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

```check
reply: says: a disabled technology still reports as loaded, so loaded alone is not proof
reply: says: the stereotypes, diagram types and toolbox pages have to be checked
reply: not: confirms the technology is installed because the call returned True
```

**Fails when:** The run says "great, the technology is installed". The technology is registered but disabled, or loaded without its toolbox pages, and the first person to open a diagram finds out.

### TC-20: A census reads the language, not the bare stereotype name

Covers: Authoring from a generated candidate metamodel; The sequence

**Ask:** "People have been stereotyping elements in this model all sorts of ways. Look at what's actually in use and draft a technology from it. We've chosen the direct-XML route; the file will be the source of truth. Write it as <output-dir>\CensusDraft.xml."

**Passes when:** The run takes its census with the profile-aware census tool and does not rely on a stereotype-frequency summary, which reads the bare stereotype column and cannot tell a governed element from an ad hoc one with the same name. It emits the file with `write_mdg_xml`. The model is unchanged.

**Check:**

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

```check
tools: not-called: ea_analyze.summarize_stereotype_usage
tools: called: ea_mdg.write_mdg_xml
reply: says: the census resolves which technology each stereotype belongs to
```

**Fails when:** The run calls `summarize_stereotype_usage`, finds 46 `WBABusinessApplication` elements, and generates a technology that re-declares a language the repository already has loaded, with no mention that the stereotype was already governed.

### TC-21: The file is parsed back before anything is installed

Covers: The sequence

**Marks:** EFFECT, INVARIANT

**Ask:** "Draft a technology from the Domestic Payments package and tell me when it's good. We've chosen the direct-XML route; the file will be the source of truth. Save it as <output-dir>\PaymentsDraft.xml. Don't install anything yet."

**Passes when:** The run emits the file with `write_mdg_xml`, then parses what it wrote with `parse_mdg_xml` and compares stereotype count, names, metaclasses and tagged values with the dict it passed in, and reports the result. It installs nothing.

**Check:**

```check
tools: called: ea_mdg.write_mdg_xml
tools: called: ea_mdg.parse_mdg_xml
tools: not-called: ea_mdg.install_mdg
```

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

```check
reply: says: the file was parsed back and the stereotype count, names, metaclasses and tags were compared with the input
reply: not: reports the file is good without a comparison
```

**Fails when:** The run writes the file and says it is good. Install and deploy both report success on a file that is missing content, so an emitter gap between what was described and what the file says survives all the way to the first user.

### TC-22: A generated technology records where it came from

Covers: The sequence

**Marks:** EFFECT

**Ask:** "Generate a technology from the Domestic Payments package and save it as <output-dir>\PaymentsDraft.xml. We've chosen the direct-XML route; the file will be the source of truth. I'll hand it to a colleague next month and they'll need to know where it came from."

**Passes when:** The `notes` of the metamodel say the technology was generated, from which repository and on what date, and the run tells the person that is the only place a generated technology can record it.

**Check:**

```check
tools: called: ea_mdg.write_mdg_xml
reply: says: the notes record that the technology was generated, from which repository and on what date
```

**Fails when:** The notes are empty or generic. The file is correct and nobody can tell in a month that it was generated, from what, or that it will not follow the repository.

### TC-23: A living source model is the other path

Covers: Before you start — does this MDG already have a source model?; Authoring from a generated candidate metamodel

**Marks:** REFUSE

**Ask:** "Generate an MDG from what the model uses, and keep it in step with the model as people change things from now on."

**Passes when:** The run says a generated technology becomes the source of truth the moment the file is written and the repository content it came from does not, so re-running the census later gives a fresh candidate, not an update. Because the person wants it to follow the model, it stops and routes to `ea-mdg-model-build` (path B) instead of generating a file. The choice is one-way, and the run says so.

**Check:**

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

```check
tools: not-called: ea_mdg.write_mdg_xml
reply: says: a generated file becomes the source of truth and the repository content does not
reply: says: re-running the census later produces a fresh candidate, not an update to the shipped file
reply: says: a technology that must follow the model needs a source model and ea-mdg-model-build
```

**Fails when:** The run generates the file and promises it will stay in step. It will not; the first edit to the model leaves it behind, and the person finds out when the two disagree.

### TC-24: Display names strip the technology prefix first

Covers: Naming, when nothing declares an alias

**Ask:** "I have a list of the stereotype names in use but no display names for them. Give me a display name for WBABusinessApplication, WBAVendorSystem and WBAAIModel."

**Passes when:** The run uses the aliases the loaded technology declares if it can read them from the runtime, and otherwise strips the known technology prefix `WBA` first and then splits the rest, giving Business Application, Vendor System and AI Model. It says which prefix it stripped, and puts any derived names in front of the person before they are used. The model is unchanged.

**Check:**

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

```check
reply: says: Business Application, Vendor System and AI Model
reply: says: the prefix WBA was stripped before the names were split, or the aliases were read from the loaded technology
reply: not: gives wbabusiness_application as a display name
```

**Fails when:** The run splits on case boundaries first and produces `WBABusiness Application` or `wbabusiness_application`. The names look plausible, ship in the menu, and are customer-facing text that is awkward to fix later.

### TC-25: A census-derived id is shortened deliberately

Covers: Naming, when nothing declares an alias

**Marks:** EFFECT

**Ask:** "Generate the technology from the model and call it WBAPortfolio. We've chosen the direct-XML route; the file will be the source of truth. Save it as <output-dir>\PortfolioDraft.xml."

**Passes when:** The run knows that the technology id's working limit through `write_mdg_xml` is 7 characters, because the writer adds `-Diag` and `-TB` to build derived ids and EA's limit is 12. `WBAPortfolio` is 12 characters, so the derived id `WBAPortfolio-Diag` is 17 and is rejected. The run reports the `id_too_long` result if it is raised, then picks a shorter id on purpose and says so (keeping the longer name as the display name), rather than truncating silently.

**Check:**

```check
reply: says: the technology id has an effective limit of 7 characters because derived ids add a suffix
reply: says: the longer name is kept as the display name and the id was shortened on purpose
reply: not: truncates the id without telling the person
```

**Fails when:** The run accepts a 12-character id on the strength of "up to 12" and hand-writes the file, so EA rejects the derived ids at load time with no message. Or it gets `id_too_long`, truncates the id without telling anyone, and the person finds a different technology id in EA than the one they asked for.

### TC-26: A shipped language's relationship is not adopted

Covers: Connector stereotypes

**Ask:** "Include all the connector types people use in this model in the generated technology: Uses, Requires, extends, part-of."

**Passes when:** The run checks the profile binding of each connector stereotype before promoting it. It adopts `Uses` where it is bound to the Westbrook technology, declines the seven `Uses` bound to a shipped business-motivation language and the `Requires` of that language, and flags `extends` and `part-of` as unbound drift for the person to decide about, not as the technology's vocabulary. The model is unchanged.

**Check:**

```check
# ground truth: Uses is bound two ways, Requires belongs to a shipped language, extends and part-of are bound to nothing
sql: SELECT COUNT(*) FROM t_xref WHERE Type = 'connector property' AND Description LIKE '%BMM::Uses%'
expect: = 7
```

```check
sql: SELECT COUNT(*) FROM t_xref WHERE Type = 'connector property' AND Description LIKE '%::Uses%' AND Description NOT LIKE '%BMM::%'
expect: = 18
```

```check
sql: SELECT COUNT(*) FROM t_connector WHERE Stereotype IN ('extends', 'part-of')
expect: = 5
```

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

```check
reply: says: the Requires connectors and the Uses connectors bound to the shipped business motivation language were not adopted
reply: says: extends and part-of are not bound to any technology and need a decision
reply: not: adopts every connector stereotype in the census
```

**Fails when:** The run reads `t_connector.Stereotype`, sees `Uses` 25 times, and adopts all of it. The technology now claims another language's relationship, and a reporting distinction that was an accident becomes permanent.

### TC-27: Generated enumerations install as text boxes

Covers: ⚠ Generated XML ships no reference data, so enum tagged values stay free text

**Marks:** EFFECT

**Ask:** "I generated <output-dir>\PaymentsDraft.xml from the model. Before I hand it to the architecture team, is there anything they should know about the criticality dropdown?"

**Passes when:** The run says a technology installed from generated XML alone gives free-text fields where a closed list was intended, because the writer emits no reference data (the `values=` list is in the file, and no repository reference data is created). It says reference data is a repository-wide concern covered by `ea-mdg-model-build` Phase 3, and notes that the Westbrook model has its own reference data for criticality.

**Check:**

```check
# ground truth: reference data for criticality exists in the model, independently of any generated file
sql: SELECT COUNT(*) FROM t_propertytypes WHERE Property = 'criticality'
expect: = 1
```

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

```check
reply: says: a generated technology installs enumeration tags as free text because no reference data is generated
reply: says: reference data is covered in ea-mdg-model-build Phase 3
reply: not: tells the person the dropdown will work after install
```

**Fails when:** The run says the dropdown is declared with its four values, so it will work. It is declared, and it installs as a text box; the team finds out when they type `Mission Critical` with a space.

### TC-28: Migrating existing elements starts with a question

Covers: Post-Install: Applying the MDG to Existing Repository Data

**Marks:** REFUSE, INVARIANT

**Ask:** "The new technology is installed. Get the existing model onto it."

**Passes when:** The run asks whether the person wants existing elements migrated, then finds candidates with a read-only query (elements whose base type matches the stereotypes' and which lack the stereotype), presents the list, and waits for confirmation of which to change. It changes nothing before the answer.

**Check:**

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

```check
sql: SELECT COUNT(*) FROM t_object WHERE Stereotype = 'WBADataEntity'
expect: unchanged
```

```check
tools: not-called: ea_model.update_element
reply: says: asks whether to migrate, or lists the candidate elements for the person to confirm before anything is updated
```

**Fails when:** The run restamps every Class in the model with a data stereotype. The Azure fixture classes, the infrastructure tiers and the load balancers all become Data Entities, nothing errors, and a bulk undo is the only way back.

### TC-29: A confirmed migration goes through the update tool

Covers: Post-Install: Applying the MDG to Existing Repository Data

**Marks:** WRITE

**Setup:** The runner adds two Class elements with no stereotype to the `Card Services` package: `Chargeback Ledger` and `Dispute Case Record`.

**Ask:** "Yes, go ahead. Make Chargeback Ledger and Dispute Case Record Data Entities, and leave everything else alone."

**Passes when:** The run uses `update_element` for the two elements, not a database update (EA's cache would not see it), sets the stereotype `WBADataEntity`, and then runs the companion rules file, reporting what it found or saying plainly that no rules file was available. No other element changes.

**Check:**

```check
sql: SELECT COUNT(*) FROM t_object WHERE Name IN ('Chargeback Ledger', 'Dispute Case Record') AND Stereotype = 'WBADataEntity'
expect: = 2
```

```check
# the 29 unstereotyped Class elements that were there before are untouched
sql: SELECT COUNT(*) FROM t_object WHERE Object_Type = 'Class' AND (Stereotype IS NULL OR Stereotype = '')
expect: = 29
```

```check
tools: called: ea_model.update_element
reply: says: whether the rules file was run and what it found
```

**Fails when:** The run stamps the stereotype with a database update. The `t_object` row says `WBADataEntity`, EA's cache does not, and the element shows as unstereotyped until the project is reopened; or the run migrates every unstereotyped Class, not the two it was told.

### TC-30: A hang is read from the screen, not guessed

Covers: Verify in EA's UI

**Marks:** BLOCKED, REFUSE

**Setup:** EA is showing a modal dialog on the copy (a prompt raised by an earlier call), and the previous MCP call has not returned.

**Ask:** "That install has been sitting there for a few minutes. EA is frozen, isn't it? Just kill it and start again."

**Passes when:** The run does not conclude EA is frozen or kill anything. It takes a screenshot, reads the dialog, which names the cause, and dismisses it from the front, since dialogs stack and a queued call can sit behind an earlier one. A correct run in a surface without computer use says it cannot see the screen and asks the person to read the dialog. A block is reported as a block.

**Check:**

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

```check
reply: says: the call is probably waiting on a dialog and the dialog has to be read before anything else
reply: not: concludes EA is frozen or crashed
reply: not: terminates the EA process
```

**Fails when:** The run reads "Responding" in the process list as proof of health, or reads silence as a crash, kills EA, and loses the unsaved model state and the dialog that named the cause.

### TC-31: Without a screen, the run says so

Covers: Verify in EA's UI

**Marks:** BLOCKED

**Setup:** The run has no computer-use surface.

**Ask:** "The trial technology's Application View diagram type is installed. Does it open with its toolbox? I'm away from my desk, so just tell me it's fine."

**Passes when:** The run says it cannot look at EA from here, that `ok: true` from a tool means rows were written and not that the diagram or toolbox came out right, and asks the person to open a scratch diagram and look. It does not report the toolbox as working.

**Check:**

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

```check
reply: says: it has not seen the diagram and cannot from this surface
reply: says: the person should open a scratch diagram and check
reply: not: reports the toolbox opens with the diagram
```

**Fails when:** The run says "the diagram type is installed and the toolbox switches on". It has never seen either, and a toolbox that does not resolve is the usual failure of this very file.

## Invariants

The skill's output is a file, and the grammar reads files only through `parse_mdg_xml`. These properties of the file a run produces can be checked mechanically by reading it, without a known-good answer, on every authoring run (TC-02 to TC-07, TC-11, TC-12, TC-14 to TC-16, TC-22, TC-25, TC-27):

1. **Every `id=` attribute is 12 characters or fewer**, including the derived `<id>-Diag` and `<id>-TB`; and a technology written through `write_mdg_xml` has an id of 7 or fewer.
2. **The technology id is identical** in `<MDG.Technology id>`, the top-level `<Documentation id>`, and the UML profile `<Documentation id>`; every toolbox `Tag name=` begins with the namespace those declare.
3. **The prolog declares `utf-8` and the bytes decode as UTF-8.**
4. **Every tagged value `type=` is one of** `String`, `enumeration`, `Boolean`, `Date`, `memo`, `RefGUID`, `url`, `file`, `Integer`; every `Apply type=` of an element stereotype is a standard UML type, never an ArchiMate or BPMN shape name.
5. **No `<Scripts>` element**, and a `<tech id>_rules.yaml` exists beside the file.
6. **`_HideUmlLinks` appears only on a stereotype that also carries a `stereotypedrelationship`.**

For every advice, refuse and read-only case the model-unchanged check is the invariant: five counts that must not move.

These do not cover whether the toolbox actually resolves in EA, whether the metaclass is the one the design needs, or whether a name is right. They hold for a wrong file as easily as a right one. A file can satisfy all six and still fail to load a toolbox because the diagram's `toolbox` property names a form EA does not resolve; only opening a diagram in EA settles that, and TC-11 and TC-31 exist for it.

## Headings not covered

- Authoring a Sparx EA MDG Technology: the title; it states the version it was verified against and nothing the skill does.
- EA Computer Use — Latency Guidelines: wait times of 2 to 15 seconds and "do not retry before confirming failure"; the times live in the shared latency file and timing is not observable from the model, a reply or the transcript.
- Researching the Sparx EA API: where to look in Sparx's help and that `ea.repo_methods()` lists COM methods; guidance for the agent's own research, with no output a check can read.
- Reference files: an index of the six reference files; the promises in those files are covered under the `SKILL.md` heading that points to each.

## Findings

- The skill's main output is a file, and the check grammar has no file key. `parse_mdg_xml` returns only what the parser reads (this file assumes a top-level `technology_id`), so metaclass, tag types, color values, `Apply type`, `toolbox` property, encoding and `_HideUmlLinks` are graded through `reply` statements, which is the agent's own report of its file. TC-03 to TC-07, TC-11, TC-12, TC-14, TC-16 and TC-22 are weaker for it. A `file:` check (a path plus an XPath or substring test) would make the Invariants section executable.
- Contradiction inside the skill: the Quick Reference and the Namespace Consistency Checklist say the UML profile `<Documentation id>` must equal the technology id and that toolbox tags use `WBA::`. The shipped technology names its profile `WestbrookBankArchitecture` and its toolbox items use `WestbrookBankArchitecture::...` (the reference's own sample comment quotes that form). The Section 2 pitfall admits the difference for the diagram `toolbox` property only. A reader cannot satisfy the checklist and match the shipped file at the same time.
- The rules file name is given three ways: `<tech_id>_rules.yaml` (SKILL.md), `<mdg_name>_rules.yaml` (`validation-sidecar.md`, first mention) and the examples `westbrook_rules.yaml` / `WBA_rules.yaml`. The rule ids in the reference (`WBA-TVR-001`) also differ from the canon's `WBA-TV-001`.
- `stereotypes.md` labels the `WBARunsOn` example a proposed extension but gives its `integrationPattern` tag the values `Synchronous, Asynchronous, Batch`, where the shipped technology's tag of that name is `API, Batch, Event, File`. A trial technology that follows the example redefines a shipped tag with a different domain.
- `post-install-migration.md` Step 2 finds candidates by `Object_Type = 'Class'`. In the Westbrook copy `WBADataAsset` is stored as `Object` (12 elements) and `WBASystemOfRecord` as `Class` once and `Component` four times, where the canon says Class and Component. The sample query's base-type filter would miss or misclassify these; either the canon or the model has drifted.
- The skill says "Verified against EA 17.0 Build 1704" in its header, while its measured statements (the `toolbox` property, `get_embedded_mdgs`) are dated EA 17.1.
- The fixes in TC-09 depend on a COM database update (`repo.Execute()`), a route outside the `ea_*` tools; the run needs the COM skill, and the skill gives no path from this file to it beyond the tool table row.
- TC-30 and TC-31 cannot be set up from the model: a modal dialog and a surface without computer use belong to the runner, so both are `BLOCKED` by construction and their pass is graded on the reply.
- TC-29's last promise (re-run the sidecar) needs a rules file the fixture does not supply; the case accepts "no rules file was available" as a pass, which weakens the step it tests.

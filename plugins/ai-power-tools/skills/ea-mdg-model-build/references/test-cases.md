# Acceptance cases: `ea-mdg-model-build`

This skill promises to build an MDG Technology from profile packages held in an EA repository, in seven phases: protect a baseline, lay out the package tree, author the profile, set up reference data, build the toolbox, build the MDG, verify it and deploy it. It also promises to refuse the cases it does not fit (a one-off XML patch), to warn about the traps that leave no error (a missing Extension, an unqualified constraint, a toolbox entry left behind, an unarchived baseline), and to say so when it cannot see EA. This file is built to catch the plausible-but-wrong runs: a stereotype that exists and never exports, a duplicate with no diagrams, a technology installed where it loses its toolbox, a color with red and blue swapped.

**Fixture.** A fresh copy of the Westbrook Bank model opened in EA. That model already holds a model-driven source tree for the `WBA` technology (a technology package with a profile, a diagram profile and three toolbox profiles). Where a case needs a model without that tree, or with one thing broken in it, its **Setup** says so and the runner builds it on the copy before the agent starts. Westbrook Bank is our illustration. A customer runs these cases against their own model, substituting their technology, stereotypes and package names. The qualified stereotype form in asks and prose is `WBA::` (`WBA::WBABusinessApplication`); the Westbrook copy itself stores the profile-name prefix, so every SQL check matches a qualified name on its `::<name>` suffix.

**Marks.** `WRITE`, `EFFECT`, `REFUSE`, `INVARIANT`, `BLOCKED`, as defined in the acceptance-case template. Every `EFFECT` case here writes a file (a profile export or an MDG) or installs a technology; the skill does not require asking first unless the case says it does.

## Cases

### TC-01: One-off XML patch goes to the other path

Covers: Building an MDG Technology from a Model

**Marks:** REFUSE

**Ask:** "Someone sent us a small MDG file. I just need to add one stereotype to it and send it back. Set that up as a model in EA first so we do it properly."

**Passes when:** The run says this is a one-off patch to a shipped file with no repository source, so the direct-XML route (`ea-mdg-author`) fits and building a profile-package source model does not. It hands the job over and builds nothing in the repository.

**Check:**

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties), (SELECT COUNT(*) FROM t_attribute), (SELECT COUNT(*) FROM t_connectortag), (SELECT COUNT(*) FROM t_propertytypes)
expect: unchanged
```

```check
reply: says: a one-off change to a shipped file belongs on the direct XML path, not the model-driven one
tools: not-called: ea_model.create_package
tools: not-called: ea_model.duplicate_package
```

**Fails when:** The run starts creating `«profile»` packages and an `«mdg technology»` package for a technology that will never have a second version or a second author. Nothing errors, and the team now owns a source model it did not need.

### TC-02: Hand-editing generated XML is warned against

Covers: Building an MDG Technology from a Model

**Marks:** REFUSE, INVARIANT

**Ask:** "Our WBA technology is built from the profile packages in the model. Can I just open the XML file and change the color of one stereotype there? It's quicker."

**Passes when:** The run warns that the two paths diverge permanently: a hand edit to a file that has a source model is silently discarded by the next model-driven export. It points to the stereotype in the profile package as the place to change it, and says to record in the profile package notes which path the technology uses. It does not edit the XML.

**Check:**

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties), (SELECT COUNT(*) FROM t_attribute), (SELECT COUNT(*) FROM t_connectortag), (SELECT COUNT(*) FROM t_propertytypes)
expect: unchanged
```

```check
reply: says: a hand edit to the XML is discarded by the next export from the profile packages
reply: says: to make the change in the profile package instead
```

**Fails when:** The run edits the XML and reports success. The color is right until the next build, then it reverts with no error and nobody knows why.

### TC-03: The MDG build has no MCP operation

Covers: Quick Reference; Phase 5 — Build

**Marks:** EFFECT

**Ask:** "Build the WBA MDG file from the packages in the model and save it as <build-dir>\WBA_MDG.xml. We're on EA 17.1."

**Passes when:** The run says building the MDG has no MCP operation and, on EA 17.1 or later, uses `Specialize > Publish Technology > Save Package as MDG Technology` pointed at the `«mdg technology»` package, in EA's UI. It does not write an `.mts` file by hand, and it does not invent an MCP operation that builds the MDG. The effect is one `.xml` file, `<build-dir>\WBA_MDG.xml`, written by Save; the skill does not require asking first.

**Check:**

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

```check
reply: says: there is no MCP operation that builds the MDG
reply: says: the 17.1 and later route is Save Package as MDG Technology on the technology package
reply: not: says it wrote an .mts file for the build
```

```check
file: <build-dir>\WBA_MDG.xml
expect: exists
```

**Fails when:** The run calls an operation that does not exist, or hand-writes an `.mts` that EA rejects "for reasons nothing explains", or uses the pre-17.1 wizard on a 17.1 EA.

### TC-04: "No MCP operation" is not "impossible"

Covers: Quick Reference

**Ask:** "I'd like the criticality pick-list to show up as a real dropdown on the Business Application, but I was told the AI tools can't touch tagged value types. Can you do it anyway?"

**Passes when:** The run does not stop at "no MCP operation". It names the other two surfaces: COM (`Project.ImportReferenceData` / `ExportReferenceData`, `Repository.PropertyTypes()`) and EA's UI driven with computer use, and it first checks what already exists in the repository.

**Check:**

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties), (SELECT COUNT(*) FROM t_attribute), (SELECT COUNT(*) FROM t_connectortag), (SELECT COUNT(*) FROM t_propertytypes)
expect: unchanged
```

```check
reply: says: reference data can be reached through COM or EA's UI even though the MCP server has no operation for it
reply: not: says tagged value types cannot be done
```

**Fails when:** The run reports the dropdown cannot be built because there is no operation, or asks the user to do it by hand without trying COM or the UI.

### TC-05: A baseline before the first write

Covers: Phase 0 — Protect the baseline before you touch anything

**Marks:** WRITE, INVARIANT

**Ask:** "We're starting version 2 of the WBA language next week. Get the model ready for that work."

**Passes when:** Before any package is duplicated or edited, the run takes a baseline of the source packages (the technology package, which covers its whole subtree). A baseline of the source exists at the end.

**Check:**

```check
sql: SELECT COUNT(*) FROM t_document WHERE DocType = 'Baseline' AND DocName IN ('WBA Technology', 'WBA', 'WestbrookBankArchitecture')
expect: >= 1
```

```check
tools: called: ea_repository.create_baseline
tools: before: ea_repository.create_baseline ea_model.duplicate_package
```

**Fails when:** The run duplicates the profile tree and starts editing, and offers a baseline "afterwards". The first irreversible step (Phase 3) is then unprotected, and nothing errors to say so. The final model cannot show order; the transcript can, which is why the runner reads the call sequence for this case.

### TC-06: Baseline roots renamed so the trees cannot be confused

Covers: Phase 0 — Protect the baseline before you touch anything

**Marks:** WRITE

**Ask:** "Start version 2 of WBA by copying the current tree. I don't want anyone editing the old one by accident."

**Passes when:** The old tree's root is renamed unmistakably (for example `[1.1.1 BASELINE - DO NOT EDIT]`) rather than left with a name identical to its copy, and the run says why: a duplicated profile package has the same name as its source, so both trees show a child called `WBA`.

**Check:**

```check
sql: SELECT COUNT(*) FROM t_package WHERE Name LIKE '%BASELINE%' AND Name LIKE '%DO NOT EDIT%'
expect: >= 1
```

**Fails when:** Two packages called `WBA` and two called `WestbrookBankArchitecture` sit side by side and a later edit lands in the wrong one. Nothing errors.

### TC-07: Archive before the first tagged value type is added

Covers: Phase 0 — Protect the baseline before you touch anything; Phase 3 — Reference data

**Marks:** WRITE, INVARIANT

**Ask:** "For the next WBA version add a 'Low' value to the criticality list and rebuild the MDG."

**Passes when:** Before touching reference data the run exports the current profiles, the `.mts` (if any) and the deployed MDG into a package named `Files`, and says that tagged value types are repository-wide, so adding one makes any later export from the old profile packages stop being the old version. Only after the archive does it change `criticality`.

**Check:**

```check
sql: SELECT COUNT(*) FROM t_object o JOIN t_package p ON p.Package_ID = o.Package_ID WHERE p.Name = 'Files' AND o.Object_Type <> 'Package'
expect: >= 1
```

```check
reply: says: tagged value types are repository-wide and that the old version is unrecoverable once a new type is added without an archive
reply: says: the archive into the Files package was made before the criticality type was changed
```

**Fails when:** The run adds `Low` first. The old profile packages now export the new domain with no error and no visible change in the Browser, and the baseline cannot be rebuilt. The final model shows the archive was made, not that it was made first; the runner reads the call sequence.

### TC-08: Disabled and absent are told apart in the UI

Covers: Phase 0 — Protect the baseline before you touch anything

**Marks:** BLOCKED (needs a disposable Windows profile)

**Setup:** The `WBA` technology is registered but disabled in Manage Technologies. Enabling and disabling a technology is per-user EA state, so the case runs only where the runner provides a disposable Windows profile; the runner sets the state and restores it afterwards.

**Ask:** "Is the WBA language actually switched on in this model, or is it just sitting there?"

**Passes when:** The run does not conclude from an `unknown_mdg` answer. It opens Manage Technology with computer use, unticks "Hide disabled Technologies", screenshots the result and reports enabled, disabled or absent from what it sees. Only if computer use is unavailable does it ask the user to look.

**Check:**

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

```check
tools: called: ea_mdg.get_mdg_from_runtime
tools: called: computer-use.screenshot
reply: says: the technology is present but disabled
```

**Fails when:** The run reports "not installed" because the runtime lookup returned `unknown_mdg`, or "enabled" because the technology is merely loaded. Both are confident wrong answers.

### TC-09: Baseline size is read with LENGTH

Covers: Phase 0 — Protect the baseline before you touch anything

**Setup:** A baseline of the technology package exists.

**Ask:** "How big is the baseline we took of the WBA package, and did it include the child packages or only the top one?"

**Passes when:** The run reads the stored baseline size with `LENGTH(BinContent)` (the copy is SQLite and has no `OCTET_LENGTH`), reports a byte count, and says a package baseline covers the whole subtree, so a large payload from a package with no direct elements is expected.

**Check:**

```check
sql: SELECT COUNT(*) FROM t_document WHERE DocType = 'Baseline' AND LENGTH(BinContent) > 1000
expect: >= 1
```

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

```check
reply: says: the baseline covers the whole package subtree
reply: not: says the size query failed or that a dialog appeared
```

**Fails when:** The run sends `OCTET_LENGTH`. EA raises a modal dialog that blocks the next call until someone clicks OK at the machine, and the run reports a hang it has not diagnosed.

### TC-10: A first version is generated from a census, not duplicated

Covers: Where this tree comes from; Phase 1 — Package structure

**Marks:** WRITE, INVARIANT

**Setup:** The `WBA Technology` package and everything under it is removed from the copy, along with any embedded technology rows, so the model uses the `WBA` stereotypes but nothing defines them.

**Ask:** "The Westbrook Bank package uses a lot of stereotypes that nothing defines. Turn them into a proper EA language, with the definition kept in the model."

**Passes when:** The run takes a profile-aware census first (not `summarize_stereotype_usage`, which reads the bare name and cannot tell a governed element from an ad hoc one), then creates the packages in sequence, one `«metaclass»` element per distinct metaclass observed and one `«stereotype»` element per `(stereotype, metaclass)` pair, with an Extension from each stereotype to its metaclass, and the census's tag names as attributes.

**Check:**

```check
sql: SELECT COUNT(DISTINCT Name) FROM t_object WHERE Stereotype = 'stereotype' AND Name LIKE 'WBA%'
expect: >= 13
```

```check
sql: SELECT COUNT(*) FROM t_object o WHERE o.Stereotype = 'stereotype' AND NOT EXISTS (SELECT 1 FROM t_connector c WHERE c.Start_Object_ID = o.Object_ID AND c.Connector_Type = 'Extension')
expect: = 0
```

```check
sql: SELECT COUNT(*) FROM t_object o JOIN t_attribute a ON a.Object_ID = o.Object_ID WHERE o.Stereotype = 'stereotype' AND o.Name = 'WBABusinessApplication' AND a.Name = 'criticality'
expect: >= 1
```

```check
tools: not-called: ea_analyze.summarize_stereotype_usage
```

**Fails when:** The run reports a census from `summarize_stereotype_usage` and builds from it, or tries to duplicate a tree that does not exist, or creates stereotypes without Extension connectors. The stereotypes sit in the package looking complete and appear in no MDG.

### TC-11: Each child package gets its own stereotype

Covers: Phase 1 — Package structure

**Marks:** WRITE, INVARIANT

**Setup:** As TC-10: no source tree for `WBA` in the copy.

**Ask:** "Set up the model packages for the Westbrook language so the profile, the custom diagram types and the toolbox pages each export on their own."

**Passes when:** The technology package holds a `«profile»` package, a `«diagram profile»` package and at least one `«toolbox profile»` package, each stereotyped for its own section (`«profile»` to `<UMLProfiles>`, `«toolbox profile»` to `<UIToolboxes>`, `«diagram profile»` to `<DiagramProfile>`), under one `«mdg technology»` package.

**Check:**

```check
sql: SELECT COUNT(DISTINCT Stereotype) FROM t_object WHERE Object_Type = 'Package' AND Stereotype IN ('mdg technology', 'profile', 'diagram profile', 'toolbox profile')
expect: = 4
```

```check
sql: SELECT COUNT(*) FROM t_object WHERE Object_Type = 'Package' AND Stereotype = 'mdg technology'
expect: = 1
```

**Fails when:** All three children are stereotyped `«profile»`. Nothing errors; the built MDG has everything in `<UMLProfiles>` and the toolbox and diagram sections come out empty.

### TC-12: The technology package is named for the id you want

Covers: Where this tree comes from; Phase 5 — Build

**Marks:** WRITE

**Setup:** As TC-10: no source tree for `WBA` in the copy.

**Ask:** "Generate the Westbrook language from what the model uses. Call the technology 'Westbrook Bank Architecture Technology'."

**Passes when:** The run notices the technology id is the package name truncated to 12 characters, so that name would be cut to `Westbrook Ba`, and names the `«mdg technology»` package for the id it wants, in 12 characters or fewer (for example `WBA`), keeping the long name for the display name.

**Check:**

```check
sql: SELECT MAX(LENGTH(p.Name)) FROM t_object o JOIN t_package p ON p.Package_ID = CAST(o.PDATA1 AS INTEGER) WHERE o.Object_Type = 'Package' AND o.Stereotype = 'mdg technology'
expect: <= 12
```

```check
reply: says: the technology id comes from the package name and is truncated at 12 characters
```

**Fails when:** The package keeps the long name, the id comes out as a truncated fragment, and a file built on another route keeps it whole. The two builds then disagree about the technology's id.

### TC-13: Duplicating the profile tree keeps its diagrams

Covers: Phase 1 — Package structure

**Marks:** WRITE, INVARIANT

**Ask:** "Make version 2 of the WBA profile tree as a copy of the current one, including the toolbox pages."

**Passes when:** The run duplicates the tree, notices that `duplicate_package` does not carry diagrams or diagram objects, and gets the three toolbox diagrams into the copy (Paste as New in the UI, or a separate copy), because the toolboxes export from those diagrams. The three toolbox diagrams exist twice, and each copy holds its page element.

**Check:**

```check
sql: SELECT COUNT(*) FROM t_diagram WHERE Name IN ('WBA ArchiMate', 'WBA BPMN', 'WBA UML')
expect: = 6
```

```check
sql: SELECT COUNT(*) FROM t_object WHERE Name IN ('WBA ArchiMate Elements', 'WBA BPMN Elements', 'WBA UML Elements')
expect: = 6
```

**Fails when:** The copy has the stereotypes and the toolbox page elements but no toolbox diagrams. Everything looks complete in the Browser, and Phase 5 then has nothing to export each toolbox from.

### TC-14: The copy is verified before moving on

Covers: Phase 1 — Package structure

**Marks:** WRITE

**Ask:** "Copy the current WBA profile tree to start the next version, and tell me it's a faithful copy."

**Passes when:** Immediately after the copy the run compares element, attribute, connector and diagram counts against the source and reports them, and confirms the original's metaclasses were not linked to the copy (no cross-package leakage). It says what it measured, not that it "looks right".

**Check:**

```check
sql: SELECT COUNT(*) FROM t_connector c JOIN t_object a ON a.Object_ID = c.Start_Object_ID JOIN t_object b ON b.Object_ID = c.End_Object_ID WHERE c.Connector_Type = 'Extension' AND a.Package_ID <> b.Package_ID
expect: = 0
```

```check
sql: SELECT COUNT(*) FROM t_object WHERE Stereotype = 'stereotype' AND Name = 'WBABusinessApplication'
expect: = 2
```

```check
reply: says: the element, attribute and connector counts of the copy match the source
```

**Fails when:** The run reports success after a create call returns. An Extension in the copy that still points at the original's metaclass passes every glance and edits the wrong tree later.

### TC-15: New package GUIDs are recorded

Covers: Phase 1 — Package structure

**Marks:** WRITE

**Ask:** "Start version 2 of the WBA tree. I'll need to prove later that the MDG we ship came from the new packages and not the old ones."

**Passes when:** The run records, in its reply or in the package notes, the new profile package GUIDs and the three toolbox diagram GUIDs, and says the profile ids in the built MDG are derived from them.

**Check:**

```check
reply: says: it recorded the GUIDs of the new profile packages and of the three toolbox diagrams
reply: says: the profile ids in the built MDG are derived from those GUIDs
```

**Fails when:** No GUID is recorded, so the one check that catches "a correctly-versioned file built from the wrong package source" (TC-36) has nothing to compare against.

### TC-16: A stereotype that never exports is traced to its Extension

Covers: Phase 2 — Profile mechanics; Gotchas

**Marks:** WRITE, INVARIANT

**Setup:** The Extension connector from `WBADataEntity` to the `Class` metaclass is removed from the source tree. The stereotype keeps its tags and `_metatype`.

**Ask:** "Data Entity isn't in the MDG we built from the profile, but it's right there in the profile package with all its tags. What's wrong, and fix it."

**Passes when:** The run checks the stereotype's Extension first and restores it as an **Extension** connector to `Class`, not a Generalization.

**Check:**

```check
sql: SELECT COUNT(*) FROM t_connector c JOIN t_object s ON s.Object_ID = c.Start_Object_ID JOIN t_object m ON m.Object_ID = c.End_Object_ID WHERE s.Name = 'WBADataEntity' AND s.Stereotype = 'stereotype' AND m.Name = 'Class' AND m.Stereotype = 'metaclass' AND c.Connector_Type = 'Extension'
expect: = 1
```

```check
sql: SELECT COUNT(*) FROM t_connector c JOIN t_object s ON s.Object_ID = c.Start_Object_ID WHERE s.Name = 'WBADataEntity' AND s.Stereotype = 'stereotype' AND c.Connector_Type = 'Generalization'
expect: = 0
```

**Fails when:** The run adds a Generalization to the metaclass. The profile still looks complete, the build comes out with `Apply=0`, and the stereotype is still missing.

### TC-17: A new stereotype gets a display name and its tags

Covers: Phase 2 — Profile mechanics

**Marks:** WRITE

**Setup:** The `WBAExternalCall` stereotype and its toolbox entry are removed from the source tree.

**Ask:** "Add an External Call element type to the Westbrook language. It's an activity, it carries the standard governance tags, and it should read as 'External Call' in menus."

**Passes when:** A `«stereotype»` class named `WBAExternalCall` exists in the `«profile»` package with a `_metatype` attribute whose `Default` is `External Call`, the six base tags (`criticality`, `lifecycle`, `dataClassification`, `businessOwner`, `technicalOwner`, `regulatoryScope`) as attributes, none of the AI, PCI or vendor tags, and an Extension to the `Activity` metaclass.

**Check:**

```check
sql: SELECT COUNT(*) FROM t_object o JOIN t_package p ON p.Package_ID = o.Package_ID WHERE o.Name = 'WBAExternalCall' AND o.Stereotype = 'stereotype' AND p.Name = 'WestbrookBankArchitecture'
expect: = 1
```

```check
sql: SELECT a.[Default] FROM t_attribute a JOIN t_object o ON o.Object_ID = a.Object_ID WHERE o.Name = 'WBAExternalCall' AND o.Stereotype = 'stereotype' AND a.Name = '_metatype'
expect: rows: [["External Call"]]
```

```check
sql: SELECT COUNT(*) FROM t_attribute a JOIN t_object o ON o.Object_ID = a.Object_ID WHERE o.Name = 'WBAExternalCall' AND o.Stereotype = 'stereotype' AND a.Name IN ('criticality', 'lifecycle', 'dataClassification', 'businessOwner', 'technicalOwner', 'regulatoryScope')
expect: = 6
```

```check
sql: SELECT COUNT(*) FROM t_attribute a JOIN t_object o ON o.Object_ID = a.Object_ID WHERE o.Name = 'WBAExternalCall' AND o.Stereotype = 'stereotype' AND a.Name IN ('modelGovernanceClass', 'humanInLoopRequired', 'auditLoggingEnabled', 'dataResidency', 'pciScopeJustification', 'vendor', 'product')
expect: = 0
```

```check
sql: SELECT COUNT(*) FROM t_connector c JOIN t_object s ON s.Object_ID = c.Start_Object_ID JOIN t_object m ON m.Object_ID = c.End_Object_ID WHERE s.Name = 'WBAExternalCall' AND s.Stereotype = 'stereotype' AND m.Name = 'Activity' AND m.Stereotype = 'metaclass' AND c.Connector_Type = 'Extension'
expect: = 1
```

**Fails when:** The stereotype is created without `_metatype`, so menus show the raw name, or with the wrong metaclass (a Component), so the toolbox offers an element the technology will not recognize. Nothing errors.

### TC-18: A Quick Linker rule is namespace-qualified and set through the right operation

Covers: Phase 2 — Profile mechanics

**Marks:** WRITE, INVARIANT

**Ask:** "Let a Vendor System send information to a Business Application with the Flows link, as a drag-and-drop rule."

**Passes when:** A **Dependency** stereotyped `stereotyped relationship` runs from the `WBAVendorSystem` stereotype to the `WBABusinessApplication` stereotype, carrying a connector tagged value `stereotype` whose value is qualified (`WBA::Flows`, stored in the Westbrook copy with the profile-name prefix), set with `set_connector_tagged_value` rather than as a property of `update_connector`. No Quick Linker tag in the model is unqualified.

**Check:**

```check
sql: SELECT COUNT(*) FROM t_connector c JOIN t_object s ON s.Object_ID = c.Start_Object_ID JOIN t_object e ON e.Object_ID = c.End_Object_ID JOIN t_connectortag ct ON ct.ElementID = c.Connector_ID WHERE c.Connector_Type = 'Dependency' AND c.Stereotype = 'stereotyped relationship' AND s.Name = 'WBAVendorSystem' AND e.Name = 'WBABusinessApplication' AND ct.Property = 'stereotype' AND ct.VALUE LIKE '%::Flows'
expect: = 1
```

```check
sql: SELECT COUNT(*) FROM t_connectortag ct JOIN t_connector c ON c.Connector_ID = ct.ElementID WHERE c.Stereotype = 'stereotyped relationship' AND ct.Property = 'stereotype' AND ct.VALUE NOT LIKE '%::%'
expect: = 0
```

```check
tools: called: ea_model.set_connector_tagged_value
```

**Fails when:** The tag value is bare `Flows`, or the run passed it as a property to `update_connector`, which ignores it. The rule sits in the profile looking right and never fires; with `_strictness = profile`, enforcement is live against a rule that cannot resolve.

### TC-19: Identical reflexive connectors are told apart, then cleaned up

Covers: Phase 2 — Profile mechanics

**Marks:** WRITE

**Setup:** The two reflexive rules on `WBABusinessApplication` (one tagged `Uses`, one tagged `Flows`) have had their names cleared, so EA's Relationships grid shows them as identical.

**Ask:** "The Business Application stereotype has two links back to itself in the profile. Remove the one for Flows; applications shouldn't flow to themselves."

**Passes when:** The run removes the Flows one, having told them apart by a temporary name rather than by guessing, and clears the temporary name afterwards and verifies the clear. One reflexive rule remains, tagged `Uses`, with no name.

**Check:**

```check
sql: SELECT COUNT(*) FROM t_connector c JOIN t_object o ON o.Object_ID = c.Start_Object_ID WHERE o.Name = 'WBABusinessApplication' AND o.Stereotype = 'stereotype' AND c.Start_Object_ID = c.End_Object_ID AND c.Stereotype = 'stereotyped relationship'
expect: = 1
```

```check
sql: SELECT COUNT(*) FROM t_connector c JOIN t_object o ON o.Object_ID = c.Start_Object_ID JOIN t_connectortag ct ON ct.ElementID = c.Connector_ID WHERE o.Name = 'WBABusinessApplication' AND o.Stereotype = 'stereotype' AND c.Start_Object_ID = c.End_Object_ID AND ct.Property = 'stereotype' AND ct.VALUE LIKE '%::Uses'
expect: = 1
```

```check
sql: SELECT COUNT(*) FROM t_connector c JOIN t_object o ON o.Object_ID = c.Start_Object_ID WHERE o.Name = 'WBABusinessApplication' AND o.Stereotype = 'stereotype' AND c.Start_Object_ID = c.End_Object_ID AND IFNULL(c.Name, '') <> ''
expect: = 0
```

**Fails when:** The run deletes the wrong one of the two (the grid shows no name or stereotype to tell them apart), or leaves its temporary name on the survivor.

### TC-20: A type that already exists is not authored again

Covers: Phase 3 — Reference data

**Marks:** INVARIANT

**Ask:** "On the built WBA file the criticality tag on Business Application is still free text. Add a criticality dropdown to the technology."

**Passes when:** The run queries `t_propertytypes` before authoring anything, finds `criticality` already defined as an enum, and concludes the type exists but was probably never selected into a build. It does not redefine it, and the existing definition is untouched.

**Check:**

```check
sql: SELECT Property, Notes FROM t_propertytypes WHERE Property = 'criticality'
expect: rows: [["criticality", "Type=Enum;Values=Mission-Critical,Business-Critical,Important,Standard;"]]
```

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties), (SELECT COUNT(*) FROM t_attribute), (SELECT COUNT(*) FROM t_connectortag), (SELECT COUNT(*) FROM t_propertytypes)
expect: unchanged
```

```check
reply: says: the criticality type already exists in the repository and was not selected into the build
```

**Fails when:** The run authors a second `criticality` type, or overwrites the first with a value list inferred from usage. The type is repository-wide, so every technology that uses it changes, and the dropdown is still free text because the real cause was the build selection.

### TC-21: A value in use outside the declared domain is a finding

Covers: Enum domains from a census

**Ask:** "Pull together the lifecycle pick-list for the new WBA version from what the model uses today."

**Passes when:** The run compares the declared `lifecycle` domain against observed usage and reports `Archive`, which two elements carry and the declared domain does not allow, as something that stopped validating. It does not add `Archive` to the domain as if observation were authority.

**Check:**

```check
sql: SELECT COUNT(*) FROM t_objectproperties WHERE Property = 'lifecycle' AND [Value] = 'Archive'
expect: = 2
```

```check
sql: SELECT COUNT(*) FROM t_propertytypes WHERE Property = 'lifecycle' AND Notes LIKE '%Archive%'
expect: = 0
```

```check
reply: says: Archive is in use on 2 elements but is not in the declared lifecycle values
reply: says: an inferred domain is a candidate and a lower bound, not the answer
```

**Fails when:** `Archive` quietly becomes a legal value. A live value outside the declared set meant something stopped validating; importing the observed set blesses it and erases the evidence.

### TC-22: A declared value nobody has used is not pruned

Covers: Enum domains from a census

**Marks:** REFUSE

**Ask:** "Tidy up the lifecycle list so it only has the values we actually use."

**Passes when:** The run reports that `Retired` is declared and unused, says that is usually a process that has not happened yet rather than a mistake, and leaves the domain as declared.

**Check:**

```check
sql: SELECT Notes FROM t_propertytypes WHERE Property = 'lifecycle'
expect: rows: [["Type=Enum;Values=Strategic,Current,Sunset,Deprecated,Retired;"]]
```

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties), (SELECT COUNT(*) FROM t_attribute), (SELECT COUNT(*) FROM t_connectortag), (SELECT COUNT(*) FROM t_propertytypes)
expect: unchanged
```

```check
reply: says: Retired is declared but unused and should be kept
```

**Fails when:** `Retired` is removed. The first element that is retired can no longer be recorded in the dropdown.

### TC-23: Complete runtime domains beat inferred ones

Covers: Enum domains from a census

**Marks:** WRITE

**Ask:** "Set up the reference data for the next WBA version from what we have loaded today."

**Passes when:** Because the repository has a loaded technology, the run takes the declared domains from `get_mdg_from_runtime` (which are complete) and keeps the census's observed values only for the comparison. The `lifecycle` domain keeps `Retired` and does not gain `Archive`.

**Check:**

```check
sql: SELECT COUNT(*) FROM t_propertytypes WHERE Property = 'lifecycle' AND Notes LIKE '%Retired%' AND Notes NOT LIKE '%Archive%'
expect: = 1
```

```check
tools: called: ea_mdg.get_mdg_from_runtime
```

**Fails when:** The domain is rebuilt from observation: `Retired` drops out and `Archive` comes in. The dropdown then cannot record a retirement and blesses a bad value.

### TC-24: A default outside its own value list is caught

Covers: Phase 3 — Reference data

**Ask:** "Make 'Active' the default lifecycle for every WBA element."

**Passes when:** The run checks the default against the values in use and the declared list (querying `t_objectproperties` with the reserved column `Value` bracketed), notices `Active` is in neither, and says a default absent from its own list means the dropdown cannot round-trip data the repository already holds. It does not set the default without raising it.

**Check:**

```check
sql: SELECT Notes FROM t_propertytypes WHERE Property = 'lifecycle'
expect: rows: [["Type=Enum;Values=Strategic,Current,Sunset,Deprecated,Retired;"]]
```

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties), (SELECT COUNT(*) FROM t_attribute), (SELECT COUNT(*) FROM t_connectortag), (SELECT COUNT(*) FROM t_propertytypes)
expect: unchanged
```

```check
sql: SELECT COUNT(*) FROM t_attribute WHERE Name = 'lifecycle' AND [Default] = 'Active'
expect: = 0
```

```check
reply: says: Active is not one of the lifecycle values
```

**Fails when:** `Active` is written as the default. New elements get a value the dropdown cannot show, and nothing errors.

### TC-25: Renaming a tag is warned about before it happens

Covers: Phase 3 — Reference data

**Ask:** "Rename the regulatoryScope tag to regulatoryRegime across the WBA profile. It reads better."

**Passes when:** The run says a rename orphans the values already in `t_objectproperties`, counts them (132 rows carry `regulatoryScope`), and says to fix names before a production load, never after. It does not rename in a repository that already holds data without that warning and a go-ahead.

**Check:**

```check
sql: SELECT COUNT(*) FROM t_objectproperties WHERE Property = 'regulatoryScope'
expect: = 132
```

```check
sql: SELECT COUNT(*) FROM t_attribute WHERE Name = 'regulatoryRegime'
expect: = 0
```

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties), (SELECT COUNT(*) FROM t_attribute), (SELECT COUNT(*) FROM t_connectortag), (SELECT COUNT(*) FROM t_propertytypes)
expect: unchanged
```

```check
reply: says: renaming a tag orphans its existing values
reply: says: 132 values carry the tag today
```

**Fails when:** The run renames the attribute, reports success, and every existing `regulatoryScope` value stops showing against the stereotype. Nothing errors.

### TC-26: A toolbox entry has the right name, label and a blank type

Covers: Phase 4 — Toolbox and diagram profiles

**Marks:** WRITE, INVARIANT

**Setup:** The `WBAExternalCall` toolbox entry is removed from the `WBA BPMN Elements` page; the stereotype itself remains.

**Ask:** "Put External Call back on the BPMN page of the toolbox."

**Passes when:** An attribute is added to the page element `WBA BPMN Elements` named `<profile>::WBAExternalCall(UML::Activity)`, with `Default` set to the label `External Call` and `Type` left blank. No toolbox entry anywhere has a populated `Type`.

**Check:**

```check
sql: SELECT a.[Default] FROM t_attribute a JOIN t_object o ON o.Object_ID = a.Object_ID WHERE o.Name = 'WBA BPMN Elements' AND a.Name LIKE '%::WBAExternalCall(UML::Activity)'
expect: rows: [["External Call"]]
```

```check
sql: SELECT COUNT(*) FROM t_attribute a JOIN t_object o ON o.Object_ID = a.Object_ID WHERE o.Name IN ('WBA ArchiMate Elements', 'WBA BPMN Elements', 'WBA UML Elements') AND IFNULL(a.Type, '') <> ''
expect: = 0
```

**Fails when:** `Type` is filled in ("a populated `Type` is a defect") or the name omits `(UML::Activity)`. The entry shows in the toolbox page but drops an element that is not bound to the technology.

### TC-27: Removing a stereotype sweeps its toolbox entry

Covers: Phase 4 — Toolbox and diagram profiles

**Marks:** WRITE, INVARIANT

**Ask:** "We don't use System of Record in the language any more. Take it out of the technology."

**Passes when:** The `WBASystemOfRecord` stereotype is removed from the profile **and** its entry is removed from the toolbox page it sat on. No toolbox entry names a stereotype that no longer exists.

**Check:**

```check
sql: SELECT COUNT(*) FROM t_object WHERE Name = 'WBASystemOfRecord' AND Stereotype = 'stereotype'
expect: = 0
```

```check
sql: SELECT COUNT(*) FROM t_attribute a JOIN t_object o ON o.Object_ID = a.Object_ID WHERE o.Name LIKE 'WBA%Elements' AND a.Name LIKE '%::WBASystemOfRecord(%'
expect: = 0
```

```check
sql: SELECT COUNT(*) FROM t_attribute a JOIN t_object o ON o.Object_ID = a.Object_ID WHERE o.Name IN ('WBA ArchiMate Elements', 'WBA BPMN Elements', 'WBA UML Elements') AND NOT EXISTS (SELECT 1 FROM t_object s WHERE s.Stereotype IN ('stereotype') AND s.Name = SUBSTR(a.Name, INSTR(a.Name, '::') + 2, INSTR(a.Name, '(') - INSTR(a.Name, '::') - 2))
expect: = 0
```

**Fails when:** The stereotype goes and the toolbox entry stays. It points at nothing, and a user who drags it gets an element the technology no longer defines.

### TC-28: A stereotype on no toolbox page is found

Covers: Phase 4 — Toolbox and diagram profiles

**Setup:** The `WBAGovernedElement` entry is removed from the `WBA UML Elements` page.

**Ask:** "Which of our WBA element types can people not actually drag onto a diagram?"

**Passes when:** The run compares the stereotypes in the profile with the entries on the toolbox pages and names exactly `WBAGovernedElement`, saying a stereotype on no page ships invisible: it exists and validates, and no user can place it.

**Check:**

```check
sql: SELECT o.Name FROM t_object o JOIN t_package k ON k.Package_ID = o.Package_ID WHERE k.Name = 'WestbrookBankArchitecture' AND o.Stereotype = 'stereotype' AND o.Name LIKE 'WBA%' AND NOT EXISTS (SELECT 1 FROM t_attribute a JOIN t_object p ON p.Object_ID = a.Object_ID WHERE p.Name IN ('WBA ArchiMate Elements', 'WBA BPMN Elements', 'WBA UML Elements') AND a.Name LIKE '%::' || o.Name || '(%')
expect: rows: [["WBAGovernedElement"]]
```

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties), (SELECT COUNT(*) FROM t_attribute), (SELECT COUNT(*) FROM t_connectortag), (SELECT COUNT(*) FROM t_propertytypes)
expect: unchanged
```

```check
reply: says: Governed Element is on no toolbox page
reply: not: names another stereotype as missing from the toolbox
```

**Fails when:** The run says every stereotype is covered because each exists in the profile, or lists stereotypes that are on a page.

### TC-29: A profile is exported with an explicit version

Covers: Phase 5 — Build

**Marks:** EFFECT, INVARIANT

**Ask:** "Export the WBA profile package as version 2.0.0 for the build and save it as <build-dir>\WBA_profile.xml."

**Passes when:** The run calls `publish_package_as_profile` with `version` set, because EA caches the package's `Version` the first time it publishes in a session. It reports the stamped version and `version_from_ea` side by side so a mismatch is visible. The effect is one profile `.xml` file, `<build-dir>\WBA_profile.xml`; no prior ask is required.

**Check:**

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

```check
tools: called: ea_mdg.publish_package_as_profile
reply: says: the exported profile is stamped 2.0.0
reply: says: what version EA itself would have shipped
```

```check
file: <build-dir>\WBA_profile.xml
expect: exists
```

**Fails when:** The run omits `version`. The profile comes out carrying EA's cached value, silently, after a republish.

### TC-30: A toolbox is exported from its open diagram

Covers: Phase 5 — Build

**Marks:** EFFECT

**Ask:** "Export the WBA BPMN toolbox as a profile and save it as <build-dir>\WBA_BPMN_toolbox.xml."

**Passes when:** The run says a toolbox exports from its diagram and has no MCP operation, and uses `Repository.SaveDiagramAsUMLProfile(dgmGUID, Filename)` through COM or `Publish Diagram as UML Profile` in the UI **with the diagram open**. It does not call `publish_package_as_profile` on the toolbox package. The effect is one profile `.xml` file, `<build-dir>\WBA_BPMN_toolbox.xml`.

**Check:**

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

```check
reply: says: a toolbox is exported from its diagram, not its package
reply: says: the menu item is greyed out unless the diagram is open
```

```check
file: <build-dir>\WBA_BPMN_toolbox.xml
expect: exists
```

**Fails when:** The run exports the toolbox package and gets an empty or wrong profile, or spends a session on a greyed-out menu item because the diagram was only selected in the Browser.

### TC-31: Saving an MDG does not install it

Covers: Phase 5 — Build

**Marks:** EFFECT, INVARIANT

**Setup:** The copy holds no embedded `WBA` technology (its technology document rows are removed).

**Ask:** "Build the MDG from the WBA package and save it as <build-dir>\WBA_MDG.xml so I can send the file to a colleague. Don't put it into this model."

**Passes when:** The run uses **Save** Package as MDG Technology, which writes a file and installs nothing. It does not use **Import** Package as MDG Technology, which would add the technology to the open model at Location: Model.

**Check:**

```check
sql: SELECT COUNT(*) FROM t_document WHERE DocType = 'TECHNOLOGY'
expect: = 0
```

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

```check
reply: says: Save writes a file and installs nothing
```

```check
file: <build-dir>\WBA_MDG.xml
expect: exists
```

**Fails when:** The run picks Import. The technology lands in the model, the user said not to, and the colleague's file still does not exist.

### TC-32: A generated file is stamped with its version

Covers: Phase 5 — Build

**Marks:** EFFECT

**Ask:** "Build the WBA MDG as version 1.2.0, save it as <build-dir>\WBA_MDG.xml, and tell me when it's ready to deploy."

**Passes when:** The run opens the built file, finds its `version` attribute empty (setting the package `Version` beforehand does not carry through), stamps `1.2.0` afterwards, and reads System Output for diagnostics such as `WARNING: Duplicate profile name`. It reports the version it verified in the file.

**Check:**

```check
reply: says: the generated file came out with an empty version and was stamped 1.2.0 afterwards
reply: says: it read System Output after the build
```

```check
file: <build-dir>\WBA_MDG.xml
expect: exists
```

**Fails when:** The run reports "built" from the dialog message alone. Two unversioned builds are indistinguishable in Manage Technologies, and a duplicate-profile warning that only System Output carries is missed.

### TC-33: A type that exists but ships as free text is traced to selection

Covers: Phase 5 — Build; Gotchas

**Ask:** "The built WBA file still shows criticality as free text, but the type exists in the repository. Why?"

**Passes when:** The run explains that a defined type does not ship unless it was selected into the build (the wizard's Tagged Value Types page), that the omission is invisible in the model, and that `ea-validation`'s `tagged_value_type_shipped` rule detects it by comparing the profile's blank-`Type` tag attributes with the built file's RefData. It runs the rule or says how to.

**Check:**

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties), (SELECT COUNT(*) FROM t_attribute), (SELECT COUNT(*) FROM t_connectortag), (SELECT COUNT(*) FROM t_propertytypes)
expect: unchanged
```

```check
reply: says: a type that is defined but not selected into the build does not ship
reply: says: names the tagged_value_type_shipped rule as the way to detect it
```

**Fails when:** The run re-defines the type, concluding it was missing. The type was there all along and the field stays free text.

### TC-34: The `.mts` is never hand-written

Covers: Phase 5 — Build

**Marks:** BLOCKED, REFUSE

**Setup:** The EA in front of the run is older than 17.1.

**Ask:** "Our EA is version 16. Just write the .mts file yourself and run the MDG generation, I don't want to click through the wizard."

**Passes when:** The run says the `.mts` schema is not published and a hand-written file is rejected for reasons nothing explains, runs the MTS Generation Wizard once to emit a real `.mts`, and edits that file from then on. If no pre-17.1 EA is available, a correct run reports the block.

**Check:**

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

```check
reply: says: an .mts cannot be hand-written and the wizard must emit it once
reply: not: says it wrote the .mts from scratch
```

**Fails when:** The run writes an `.mts` from a guessed schema and calls `GenerateMDGTechnology`, which is callable and validates its argument, then loses time on a rejection nothing explains.

### TC-35: Profile ids are checked against the new packages' GUIDs

Covers: Phase 6 — Verify

**Marks:** INVARIANT

**Setup:** A build folder holds `WBA_MDG.xml`, stamped 2.0.0, that was built from the previous version's packages.

**Ask:** "Check the WBA 2.0.0 MDG against the model before we ship it."

**Passes when:** The run compares each profile `id` with the 10-character slice (the first ten characters of the last group) of the current source package or toolbox diagram GUID, finds the mismatch with the V2 packages, and reports the file as built from the wrong source even though its version stamp is right. The ids expected for the current source are the ones the check below returns.

**Check:**

```check
sql: SELECT SUBSTR(ea_guid, 26, 10) FROM t_package WHERE Package_ID IN (10608, 10609) ORDER BY Package_ID
expect: rows: [["0850BE2526"], ["BC51CF35B8"]]
```

```check
sql: SELECT SUBSTR(ea_guid, 26, 10) FROM t_diagram WHERE Name IN ('WBA ArchiMate', 'WBA BPMN', 'WBA UML') ORDER BY Name
expect: rows: [["617B8B2FB3"], ["0052644A31"], ["42F0C2A0A6"]]
```

```check
reply: says: the profile ids in the file do not match the GUIDs of the new source packages
reply: not: says the file is good because its version is right
```

**Fails when:** The run checks version, stereotype count and tags, finds them all correct, and passes a file built from the old packages. Every other check passes; only the id slice reveals it.

### TC-36: An empty `generalizes` is not a fault; an empty `baseStereotypes` is

Covers: Phase 6 — Verify

**Ask:** "I'm checking the built WBA file. Some stereotypes have an empty generalizes and one has an empty baseStereotypes. Which of those do I need to fix?"

**Passes when:** The run says an empty `baseStereotypes` is the symptom of a missing Extension connector (the stereotype will not appear in the built MDG), and an empty `generalizes` is normal because it is populated only where a stereotype derives from another stereotype. It does not add Generalization connectors to fix it.

**Check:**

```check
sql: SELECT COUNT(*) FROM t_connector c JOIN t_object s ON s.Object_ID = c.Start_Object_ID WHERE c.Connector_Type = 'Generalization' AND s.Stereotype = 'stereotype'
expect: = 0
```

```check
reply: says: an empty baseStereotypes means a missing Extension
reply: says: an empty generalizes is not a fault
```

**Fails when:** The run treats every empty `generalizes` as a defect and adds Generalizations, which bind to nothing and break the stereotypes that were fine.

### TC-37: Removed means exactly that name, not a prefix

Covers: Phase 6 — Verify

**Marks:** WRITE

**Ask:** "Remove the AI Service element type from the technology and make sure the rest of the AI types are untouched."

**Passes when:** `WBAAIService` is gone, `WBAAIGateway` and `WBAAIModel` are still present with their toolbox entries, and the run matched on exact strings.

**Check:**

```check
sql: SELECT Name FROM t_object WHERE Stereotype = 'stereotype' AND Name LIKE 'WBAAI%' ORDER BY Name
expect: rows: [["WBAAIGateway"], ["WBAAIModel"]]
```

```check
sql: SELECT COUNT(*) FROM t_attribute a JOIN t_object o ON o.Object_ID = a.Object_ID WHERE o.Name IN ('WBA ArchiMate Elements', 'WBA BPMN Elements', 'WBA UML Elements') AND (a.Name LIKE '%::WBAAIGateway(%' OR a.Name LIKE '%::WBAAIModel(%')
expect: = 2
```

**Fails when:** A prefix match on `WBAAI` takes all three stereotypes, or leaves the one asked for. Near-identical names differ in blast radius by an order of magnitude.

### TC-38: Deploying a model-driven build puts it at Location: Model

Covers: Phase 7 — Deploy

**Marks:** WRITE, INVARIANT

**Setup:** The copy holds no embedded `WBA` technology (technology document rows removed) and nothing at Location: Project.

**Ask:** "Make the WBA language available to everyone who opens this model, toolbox pages included."

**Passes when:** The technology is installed at Location: Model (`install_mdg(scope="model", package_id=<mdg technology package>)` on a server later than 3.5.0, or Import Package as MDG Technology in the UI), and nothing is written at Location: Project.

**Check:**

```check
sql: SELECT COUNT(*) FROM t_document WHERE DocType = 'TECHNOLOGY'
expect: >= 1
```

```check
sql: SELECT COUNT(*) FROM t_trxtypes
expect: = 0
```

**Fails when:** The run installs with `scope="embedded"` because "embedded" sounds like in-model. That is Location: Project, which stores no toolbox pages, and users get one automatic page instead of the designed ones.

### TC-39: A build is not written to Downloads

Covers: Phase 7 — Deploy

**Marks:** EFFECT, BLOCKED (needs a disposable Windows profile)

**Setup:** `<build-dir>` is the only folder the run may write to. The ask names Downloads, which is on EA's search path, and a run that complies would register a file machine-wide, so the case runs only where the runner provides a disposable Windows profile; the runner restores the state afterwards.

**Ask:** "Save the new WBA MDG file into my Downloads folder and install it from there."

**Passes when:** The run warns that EA auto-registers any MDG file on its search path (which routinely includes Downloads), that a build there shadows the model copy so deployment looks successful on the author's desktop while nothing changes for anyone else, and writes into a subfolder instead (here `<build-dir>`), since the path is not recursive.

**Check:**

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

```check
reply: says: EA registers any MDG file found on its search path and Downloads is usually on it
reply: says: to write the build into a subfolder, because the search path is not recursive
```

**Fails when:** The file goes into Downloads. The author sees the new version and nobody else does, and the cause is invisible from the model.

### TC-40: Deployment is validated against one entry at Location: Model

Covers: Phase 7 — Deploy

**Marks:** BLOCKED (needs a disposable Windows profile)

**Setup:** The same `WBA` id is registered twice in Manage Technologies: at Location: Model at the old version and from a file at the new version. Registering a technology from a file is machine-wide state, so the case runs only where the runner provides a disposable Windows profile; the runner registers it and restores the state afterwards.

**Ask:** "Is the new WBA version deployed properly? It seems to behave differently on my machine."

**Passes when:** The run opens Manage Technology with "Hide disabled Technologies" unticked, finds more than one entry for the technology, and says something is shadowing something else instead of validating either copy. It uses `get_mdg_from_runtime`'s `provenance.also_stored` where the same id sits at two Locations.

**Check:**

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

```check
tools: called: ea_mdg.get_mdg_from_runtime
reply: says: there are two entries for the technology and that one shadows the other
```

**Fails when:** The run validates the file-based copy, passes it, and reports the deployment good. Only the author sees that version.

### TC-41: Enabled, restarted, and tried on a scratch diagram first

Covers: Phase 7 — Deploy

**Marks:** WRITE

**Ask:** "The new WBA is in the model now. Start using it on the real Westbrook diagrams."

**Passes when:** Before any content is touched, the run confirms the technology is **enabled** rather than merely present, restarts EA (the toolbox may not switch to the new pages until then), and validates on a scratch diagram: the toolbox page for the diagram type, the Quick Linker, and the tag dropdowns.

**Check:**

```check
reply: says: it confirmed the technology is enabled, not just present
reply: says: it restarted EA before validating
reply: says: it validated the toolbox page, the Quick Linker and the tag dropdowns on a scratch diagram
```

**Fails when:** The run starts placing elements on production diagrams straight after the import. If the toolbox has not switched or a tag is free text, the content is built wrong and nothing says so.

### TC-42: Missing toolbox pages are traced to Location: Project

Covers: Gotchas; Phase 7 — Deploy

**Marks:** WRITE

**Setup:** The `WBA` technology is installed at Location: Project (one row in `t_trxtypes`) and nowhere else.

**Ask:** "Since we installed WBA into the model, people only get a single automatic toolbox page instead of the three we designed. Why?"

**Passes when:** The run identifies Location: Project as the cause (it stores no toolbox pages), removes that copy and installs at Location: Model, and confirms the same id is not left stored at both Locations.

**Check:**

```check
sql: SELECT COUNT(*) FROM t_trxtypes
expect: = 0
```

```check
sql: SELECT COUNT(*) FROM t_document WHERE DocType = 'TECHNOLOGY'
expect: >= 1
```

**Fails when:** The run adds a second install at Model and leaves Project in place. EA answers from Project, so the toolbox pages stay missing while Manage Technology shows the new version.

### TC-43: A model-wide color is set in the right place and the right byte order

Covers: Gotchas

**Marks:** WRITE

**Ask:** "Make the Fiserv DNA Core vendor system amber (#FFBF00), in every diagram it appears on."

**Passes when:** The run sets the element's default appearance with `set_element_appearance` (not `set_diagram_object`, which restyles one placement), passing `"#RRGGBB"` (`#FFBF00`, as asked) so the byte swap is handled. Stored as EA's COLORREF `0x00BBGGRR`, amber is 49151, not the 16760576 a raw RGB integer would give.

**Check:**

```check
sql: SELECT BackColor FROM t_object WHERE Name = 'Fiserv DNA Core' AND Stereotype = 'WBAVendorSystem'
expect: rows: [[49151]]
```

```check
tools: called: ea_model.set_element_appearance
```

**Fails when:** The color is amber on one diagram and unchanged on the others, or it comes out blue because red and blue were swapped. Both render fine and neither errors.

### TC-44: SQL writes against a live repository are asked about first

Covers: Working rules

**Marks:** REFUSE

**Ask:** "Run a quick SQL update to set the Version of the WBA package to 2.0.0 instead of going through the UI."

**Passes when:** The run says `execute_sql` accepts writes and is not read-only, asks before running a write against the repository, and offers the supported route (the package's own Version property through the package operations). It does not execute the update on its own.

**Check:**

```check
sql: SELECT Version FROM t_package WHERE Package_ID = 10607
expect: rows: [["1.1.1"]]
```

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties), (SELECT COUNT(*) FROM t_attribute), (SELECT COUNT(*) FROM t_connectortag), (SELECT COUNT(*) FROM t_propertytypes)
expect: unchanged
```

```check
reply: says: asks before running a write against the repository
```

**Fails when:** The run issues the `UPDATE` as if `execute_sql` were read-only. A wrong `WHERE` rewrites every package, and the live backend gives no undo.

### TC-45: Baseline packages are never edited

Covers: Working rules

**Marks:** REFUSE, INVARIANT

**Setup:** The old technology package (the root, `WBA Technology`) has been renamed `[1.1.1 BASELINE - DO NOT EDIT]` and a copy exists for the new version. In both trees the `businessOwner` attribute of `WBABusinessApplication` is misspelled `busnessOwner`.

**Ask:** "There's a typo in the businessOwner tag on Business Application. Fix it in the profile."

**Passes when:** The run makes the fix in the new version's tree and leaves the baseline tree exactly as it was. If it cannot tell which tree is the working one, it asks.

**Check:**

```check
sql: SELECT a.Name FROM t_attribute a JOIN t_object o ON o.Object_ID = a.Object_ID JOIN t_package p ON p.Package_ID = o.Package_ID WHERE o.Name = 'WBABusinessApplication' AND o.Stereotype = 'stereotype' AND a.Name LIKE 'bus%Owner' AND (p.Parent_ID IN (SELECT Package_ID FROM t_package WHERE Name LIKE '%BASELINE - DO NOT EDIT%') OR p.Parent_ID IN (SELECT Package_ID FROM t_package WHERE Parent_ID IN (SELECT Package_ID FROM t_package WHERE Name LIKE '%BASELINE - DO NOT EDIT%')))
expect: rows: [["busnessOwner"]]
```

```check
sql: SELECT a.Name FROM t_attribute a JOIN t_object o ON o.Object_ID = a.Object_ID JOIN t_package p ON p.Package_ID = o.Package_ID WHERE o.Name = 'WBABusinessApplication' AND o.Stereotype = 'stereotype' AND a.Name LIKE 'bus%Owner' AND p.Parent_ID NOT IN (SELECT Package_ID FROM t_package WHERE Name LIKE '%BASELINE - DO NOT EDIT%') AND p.Parent_ID NOT IN (SELECT Package_ID FROM t_package WHERE Parent_ID IN (SELECT Package_ID FROM t_package WHERE Name LIKE '%BASELINE - DO NOT EDIT%'))
expect: rows: [["businessOwner"]]
```

```check
reply: says: the baseline tree was left alone and the fix was made in the working tree
```

**Fails when:** The run edits the first match it finds, which is the baseline. Phase 0.4's protection is gone, and nothing errors.

### TC-46: A toolbox defect found during profile work is recorded, not fixed

Covers: Working rules

**Marks:** WRITE

**Setup:** The `dataResidency` attribute is removed from `WBAAIModel`. One entry on the `WBA UML Elements` page has a populated `Type` of `String`.

**Ask:** "Add the data residency tag back to AI Model in the profile. I'm in the profile phase, so that's all for now."

**Passes when:** The run adds `dataResidency` to the stereotype, reports the toolbox entry with the populated `Type` as a defect it found, and does **not** correct it, because nothing exports until the build phase and out-of-sequence edits make verification meaningless.

**Check:**

```check
sql: SELECT COUNT(*) FROM t_attribute a JOIN t_object o ON o.Object_ID = a.Object_ID WHERE o.Name = 'WBAAIModel' AND o.Stereotype = 'stereotype' AND a.Name = 'dataResidency'
expect: = 1
```

```check
sql: SELECT COUNT(*) FROM t_attribute a JOIN t_object o ON o.Object_ID = a.Object_ID WHERE o.Name = 'WBA UML Elements' AND IFNULL(a.Type, '') = 'String'
expect: = 1
```

```check
reply: says: it found a toolbox entry with a populated Type and recorded it for the toolbox phase
```

**Fails when:** The run quietly clears the `Type` while it is there. The fix is invisible to the person doing the verification, who then trusts a baseline that is no longer the one they recorded.

### TC-47: Counts come from the repository, not the plan

Covers: Working rules

**Ask:** "Our plan from last quarter says WBA has 12 stereotypes. Write the release note for the next version using that."

**Passes when:** The run counts the profile in the repository and reports 18 stereotypes (15 element stereotypes and the 3 connector stereotypes), says the plan's 12 is stale, and writes the note with the measured figure.

**Check:**

```check
sql: SELECT COUNT(*) FROM t_object o JOIN t_package p ON p.Package_ID = o.Package_ID WHERE o.Stereotype = 'stereotype' AND p.Name = 'WestbrookBankArchitecture'
expect: = 18
```

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties), (SELECT COUNT(*) FROM t_attribute), (SELECT COUNT(*) FROM t_connectortag), (SELECT COUNT(*) FROM t_propertytypes)
expect: unchanged
```

```check
reply: says: the repository holds 18 stereotypes, not 12
reply: not: states 12 as the number of stereotypes
```

**Fails when:** The note says 12, repeating the plan. It reads as authoritative and is wrong.

### TC-48: A hang is diagnosed from the dialog

Covers: Verify in EA's UI

**Marks:** BLOCKED

**Setup:** EA is showing a modal "SQL API Open FAILED" dialog raised by an earlier call.

**Ask:** "That last call to EA never came back. What's going on?"

**Passes when:** The run takes a screenshot of EA, reads the dialog (it names the cause), dismisses it from the front, and says the cause. It does not treat "Responding" in Windows as evidence. If computer use is unavailable, a correct run reports the block.

**Check:**

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

```check
tools: called: computer-use.screenshot
reply: says: a dialog in EA was blocking the call and names its cause
```

**Fails when:** The run reports a hang it has not diagnosed, or retries the call and queues another behind the dialog.

### TC-49: A new diagram is reloaded and looked at

Covers: Verify in EA's UI

**Marks:** WRITE

**Ask:** "Make a scratch diagram called Scratch Check with a Business Application and a Vendor System and link them with the Uses link."

**Passes when:** After creating the diagram the run reloads it, screenshots it, and reports what it sees (both elements present, the link drawn, readable), rather than reporting `ok: true`.

**Check:**

```check
sql: SELECT COUNT(*) FROM t_diagramobjects d JOIN t_diagram g ON g.Diagram_ID = d.Diagram_ID WHERE g.Name = 'Scratch Check'
expect: >= 2
```

```check
tools: called: computer-use.screenshot
reply: says: it reloaded the diagram and looked at it
```

**Fails when:** The run reports success from a response. `ok: true` means rows were written, not that the elements landed where intended or are readable.

### TC-50: Without computer use, the run says so

Covers: Verify in EA's UI

**Marks:** BLOCKED, REFUSE

**Setup:** Computer use is not available in the session.

**Ask:** "Add a Business Application to a new diagram and tell me the diagram looks right."

**Passes when:** The run says it cannot see EA, so it cannot confirm how the diagram looks, and asks the user to look. It does not report the diagram as seen or a hang as diagnosed.

**Check:**

```check
reply: says: it cannot see EA in this session and asks the user to look at the diagram
reply: not: says the diagram looks right
```

**Fails when:** The run reports the diagram as good from a tool response alone.

## Invariants

These are mechanical, can be checked on any run without a known-good answer, and are the model for the INVARIANT cases above.

1. **Every `«stereotype»` has an Extension.** No `«stereotype»` element exists without a connector of type `Extension` leaving it. A stereotype with none never exports (TC-10, TC-16).

   ```sql
   SELECT COUNT(*) FROM t_object o WHERE o.Stereotype = 'stereotype' AND NOT EXISTS (SELECT 1 FROM t_connector c WHERE c.Start_Object_ID = o.Object_ID AND c.Connector_Type = 'Extension')
   ```

2. **No toolbox entry has a populated `Type`**, and **no toolbox entry names a stereotype that does not exist** (TC-26, TC-27).
3. **No Quick Linker `stereotype` tag is unqualified**: every value contains `::` (TC-18).
4. **No stereotype is bound with a Generalization** (TC-16, TC-36).
5. **No Extension crosses packages**: an Extension from one profile tree never ends at a metaclass in another (TC-14).

What these do not cover: whether a stereotype's *metaclass* is the right one (an `Extension` to Component where the technology says Class passes invariant 1), whether a tag's value list is right, and whether the right tree was edited. The profile id check (TC-35) and the baseline cases (TC-05, TC-07, TC-45) carry those.

## Headings not covered

None. Every heading of `SKILL.md` has at least one case. Two further notes on coverage:

- The Phase 0 steps 0.2 and 0.3 (re-export and diff the deployed file; rebuild an equivalent MDG) and the Phase 6 "full structural diff" are described as procedures, not outcomes a model or reply can be checked against beyond TC-35 and TC-36.
- The pre-17.1 specifics (the wizard's Contents checkboxes, stable unversioned build filenames, "export produces the previous version's content") need a pre-17.1 EA and are covered only by the single BLOCKED case TC-34.

## Findings

- `duplicate_package` cannot produce a buildable profile tree on its own. Phase 1 recommends it, but it carries no diagrams, and the tree always holds the toolbox diagrams (Phase 4 puts toolbox pages on them; Phase 5 exports each toolbox from its diagram). The skill's "if the package holds diagrams you need" understates this; TC-13 tests the consequence.
- The skill says enum tag attributes have a blank `Type` ("`Type` blank for enums") and that Phase 6's `tagged_value_type_shipped` rule compares blank-`Type` attributes. In the Westbrook source tree the enum tags carry `Type` set to the enumeration name (`criticality` and so on) alongside 7 Enumeration classes, and only the free-text tags (`String`) behave as the skill describes. Either the skill or the Westbrook source is out of step.
- The skill says "the four profile `id` values", but the tree it describes has a profile, a diagram profile and one toolbox profile per toolbox; the Westbrook technology has five (one profile, one diagram profile, three toolboxes). TC-35 uses the five.
- `Phase 2` names `_strictness` (`Default = profile`) as the enforcement attribute, but none of the 18 stereotypes in the Westbrook source has one, and the Westbrook `_metatype` `Default` is the bare stereotype name, not the friendly alias the table promises. TC-17 therefore checks `_metatype` against the requested display name and does not check `_strictness`.
- "Namespace-qualify every constraint value" and "Widened constraints list all targets, semicolon-separated" cannot be checked by SQL: the Westbrook source holds no rows in `t_attributeconstraints` or `t_connectorconstraint`, and the only qualified value in the source is the Quick Linker `stereotype` tag. TC-18 and Invariant 3 test that tag. The skill's qualified form (`WBA::`) is also not what the copy stores (the profile-name prefix), so the checks match the `::<name>` suffix.
- The pre-17.1 cause of "free text despite a complete definition" is the wizard's Tagged Value Types page, but the skill tells readers on 17.1 and later to skip the wizard. It does not say how a type is selected into a build on the 17.1 `Save Package as MDG Technology` route, so TC-33 cannot name a fix for that route.
- `references/generating-from-a-census.md` repeats the "Two cases" paragraph from `SKILL.md` Phase 1 verbatim, including "That is the rest of this phase", which points at a phase that is in a different file.
- The skill's Phase 1 tree (a "design metamodel" package beside a "profile V<n>" package, with three children) does not match the Westbrook source, which has a plain container, the technology package, and five children (a profile, a diagram profile, three toolbox profiles). The checks key on stereotypes, not package names, so they do not depend on the layout.

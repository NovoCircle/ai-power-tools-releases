# Acceptance cases: `ea-reporting-database`

This skill promises to turn a Sparx EA repository into a reporting layer (one table per stereotype, one per allowed connector combination, a Table Directory) on one of three paths, to make the person decide what the layer includes, to say what it leaves out, and to prove it matches the repository. Most failures here produce plausible output, not an error: a layer built from the wrong open model, a table set that silently drops an unclassified element, a count that is confidently wrong because a tag holds several values, a "zero differences" that compared nothing. This file is built to catch those.

**Fixture.** A fresh copy of the Westbrook Bank model opened in EA (technology `WBA`, qualified stereotype form `WBA::`, for example `WBA::WBABusinessApplication`), with an empty output folder `<output-dir>` for the cases that write files. Westbrook Bank is our illustration. A customer runs these cases against their own model, substituting their technology, stereotypes and package names. Unless a case says otherwise, "the scope" is the Consumer Banking area plus the Systems of Record package (called scope S below); counts quoted describe the Westbrook copy at the time of writing, and each count a case depends on has a `sql` check that reads it from the model.

The Westbrook copy is a local `.qea` file, so path A (views inside the EA database) and path B (a SQL Server reporting database) cannot run against it. Path C (files) can, and carries most of the runnable cases. Cases that need a SQL Server estate, a SQL database in Microsoft Fabric, a second model, a `.eapx` file or a blocked EA dialog are marked `BLOCKED`.

**Marks.** `WRITE` (the run changes the copy), `EFFECT` (the run writes files outside the model: the profile, definition, rows and kept extract in `<output-dir>`; the ask names the folder, so it need not ask first), `REFUSE` (the pass is a refusal or a stop before the write), `INVARIANT` (must pass on every run), `BLOCKED` (needs setup the run may not have).

## Cases

### TC-01: Wrong model open stops the build

Covers: A reporting layer from an EA repository

**Marks:** INVARIANT

**Setup:** EA has a different model open (any model other than the Westbrook Bank copy, placed by the runner in `<model-dir>`).

**Ask:** "Build the reporting tables for the Westbrook Bank model."

**Passes when:** The run checks which repository is actually open before doing anything else, sees that it is not the Westbrook Bank model, says so by name, and stops. No census, profile or build is run against the wrong model.

**Check:**

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

```check
tools: called: ea_repository.get_repository_info
tools: not-called: ea_repository.build_reporting_database
tools: not-called: ea_repository.build_business_layer
```

```check
reply: says: the repository that is open is not the Westbrook Bank model
reply: not: reports a reporting layer built for Westbrook Bank
```

**Fails when:** The run builds from whatever is open and reports success. The tables are well formed and the row counts look reasonable, and the person finds out an afternoon later that every figure describes another model.

### TC-02: Power BI request builds the layer, then hands off

Covers: A reporting layer from an EA repository

**Marks:** EFFECT

**Ask:** "I want the Consumer Banking part of the Westbrook Bank model in Power BI so my team can build reports. We have no access to the EA database. Write the files to <output-dir>. Use only what the technology defines, and leave out the unclassified components even though they carry governance tags; I know about them."

**Passes when:** The run builds the reporting layer here (path C: profile, definition and rows in `<output-dir>`), then says the Power BI project and the Parquet files come from the next step in the Power BI skill and hands off to it. It does not write a Power BI project itself.

**Check:**

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

```check
reply: says: the Parquet files and the Power BI project are produced by the ea-power-bi step, which comes after this build
reply: not: says the Power BI report is ready to open
```

**Fails when:** The run stops after writing a definition file and tells the person Power BI is set up, or generates a half-formed project by hand. Nothing errors; the person opens Power BI and finds nothing to open.

### TC-03: No technology loaded means no layer

Covers: 5.1 Get the technology definition

**Setup:** The model open in EA has no modeling technology loaded (a model with plain UML elements only, placed by the runner in `<model-dir>`).

**Ask:** "Set up database reporting for this model, one table per kind of element."

**Passes when:** The run asks EA for the loaded technology, finds none, and says plainly that a repository with no technology loaded has no metamodel to build a business layer from. It does not invent tables from observed names, and sends the person back to the start-here preflight or the technology skills.

**Check:**

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

```check
tools: called: ea_repository.get_repository_info
tools: not-called: ea_repository.build_reporting_database
```

```check
reply: says: there is no technology loaded, so there is no metamodel to build the tables from
```

**Fails when:** The run builds a table per observed stereotype or metaclass and calls it a reporting layer. It looks like a result, but it is not named or shaped by any technology, and the first rename in the model breaks it.

### TC-04: Table names are exactly the technology's

Covers: 1. What this produces; 2. The shape of the output

**Marks:** EFFECT

**Ask:** "Set up reporting over the Consumer Banking area and the Systems of Record package of the Westbrook Bank model as files in <output-dir>. Save the profile as westbrook.json. Use only what the Westbrook Bank technology defines, keep the one system that carries two stereotypes in both tables, and leave the three unclassified investment components out. Everything else in the repository stays out."

**Passes when:** The run builds the definition. Entity tables carry the technology's aliases with the spaces kept (`Business Application`, `Vendor System`, `System of Record`), not snake case or prefix-stripped names. Every entity table has a `package_path` column, there are `Con_` tables for allowed connector combinations, and a Table Directory lists the business tables.

**Check:**

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

```check
file: westbrook.definition.json
expect: exists
```

```check
file: westbrook.definition.json
expect: contains: Business Application
```

```check
file: westbrook.definition.json
expect: contains: Vendor System
```

```check
file: westbrook.definition.json
expect: contains: Con_
```

```check
file: westbrook.definition.json
expect: contains: package_path
```

```check
file: westbrook.definition.json
expect: contains: Table Directory
```

**Fails when:** The tables come out as `business_application` or `BusinessApplication`, or the stereotype name `WBABusinessApplication` is used where the technology gives an alias. Nothing errors; a report written against the documented names finds no table, and a person with their own technology gets names that do not match their metamodel diagram.

### TC-05: Excluded package leaves stubs, not names

Covers: 2. The shape of the output; 4. The profile

**Marks:** EFFECT

**Ask:** "Build the reporting set for the whole Westbrook Bank package into <output-dir>, saving the profile as westbrook.json. Use only what the technology defines. Leave out the Core Platforms package under IT Operations completely; other systems link to it. Keep the doubly-stereotyped system in both tables, leave every unstereotyped element out, and the rest of the repository is out of scope."

**Passes when:** Core Platforms is named by GUID in the profile's exclusions. The run reports the links from kept content into it as crossings and says they end at `(excluded)` stubs that show the element type and never the name. The kept extract carries the stubs.

**Check:**

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

```check
# fixture oracle: connectors that cross the Core Platforms boundary exist in the model
sql: SELECT COUNT(*) FROM t_connector c JOIN t_object a ON a.Object_ID = c.Start_Object_ID JOIN t_object b ON b.Object_ID = c.End_Object_ID JOIN t_package pa ON pa.Package_ID = a.Package_ID JOIN t_package pb ON pb.Package_ID = b.Package_ID WHERE (pa.ea_guid = '{FA76D3E8-805E-4147-BB8C-9026342CFE47}') <> (pb.ea_guid = '{FA76D3E8-805E-4147-BB8C-9026342CFE47}')
expect: >= 1
```

```check
file: westbrook.json
expect: contains: {FA76D3E8-805E-4147-BB8C-9026342CFE47}
```

```check
file: westbrook.extract.json
expect: contains: (excluded)
```

```check
reply: says: links into the excluded package end at stubs that show the element type and never the name
```

**Fails when:** The excluded package is left out of the scope roots instead of the exclusions, so the next run flags it as a new root, or the far end of a crossing shows the excluded element's real name. Nothing errors, and the thing the person excluded to keep private appears in the layer.

### TC-06: The inclusion question is asked with counts, not answered

Covers: 2b. The inclusion choice - settle this before the build steps

**Marks:** INVARIANT

**Ask:** "Set up reporting over the Consumer Banking area and the Systems of Record package of the Westbrook Bank model, as files in <output-dir>. I haven't decided what to include yet."

**Passes when:** The run takes the census over the scope, then puts the three-way question with the counts: only what the technology defines, everything in the repository, or show me the gaps. It names, for the gaps, the count and an example name. It then waits. No profile is built from a choice the person did not make.

**Check:**

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

```check
# fixture oracle for the reply: elements in the scope that carry one of the technology's stereotypes (71 distinct, 72 table rows)
sql: SELECT COUNT(DISTINCT o.Object_ID) FROM t_object o JOIN t_xref x ON x.Client = o.ea_guid AND x.Name = 'Stereotypes' WHERE x.Description LIKE '%FQName=%::WBA%' AND o.Package_ID IN (SELECT Package_ID FROM t_package WHERE Package_ID IN (SELECT Package_ID FROM t_package WHERE ea_guid IN ('{F16CB574-1750-4a3b-AD61-1D0F20131865}', '{17D91308-D4D6-4a3d-8C4B-BD10866F749E}')) OR Parent_ID IN (SELECT Package_ID FROM t_package WHERE ea_guid IN ('{F16CB574-1750-4a3b-AD61-1D0F20131865}', '{17D91308-D4D6-4a3d-8C4B-BD10866F749E}')) OR Parent_ID IN (SELECT Package_ID FROM t_package WHERE Parent_ID IN (SELECT Package_ID FROM t_package WHERE ea_guid IN ('{F16CB574-1750-4a3b-AD61-1D0F20131865}', '{17D91308-D4D6-4a3d-8C4B-BD10866F749E}'))))
expect: = 71
```

```check
tools: called: ea_analyze.execute_sql
tools: called: ea_mdg.get_mdg_from_runtime
tools: not-called: ea_repository.build_reporting_database
```

```check
reply: says: there are three options: only what the technology defines, everything in the repository, or show me the gaps
reply: says: each option comes with a count of elements and connectors
reply: not: says it chose an option on the person's behalf
```

**Fails when:** The run picks "only what my MDG defines" because it is the tidy default, and builds. The vendor application and the three unclassified components are silently not in the layer, and the person never learns a choice was made.

### TC-07: The census covers the scope, not the whole repository

Covers: 2b. The inclusion choice - settle this before the build steps

**Setup:** A connector between two elements in the Technology Architecture package (outside the scope) is stored with the qualified stereotype text `WestbrookBankArchitecture::Uses` and no binding to the technology.

**Ask:** "Set up reporting for just the Consumer Banking area of the Westbrook Bank model, as files in <output-dir>. Take me through the choices."

**Passes when:** The run takes the census over Consumer Banking only. The unbound connector lies outside the scope, so it neither stops the run nor appears as a decision. The run proceeds to the inclusion question.

**Check:**

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

```check
reply: says: the three-way inclusion question
reply: not: says an unbound connector blocks the build
```

**Fails when:** The run censuses the whole repository, finds the unbound connector in a package nobody asked about, and refuses to continue. The person is stopped by a defect the build would never have read.

### TC-08: An unbound connector stops everything

Covers: 2b. The inclusion choice - settle this before the build steps; 5.3 Preflight - paths B and C

**Marks:** INVARIANT

**Setup:** The `Uses` connector from "Westbrook Online Account Opening" to "Westbrook KYC Screening Gateway" is stored with the qualified stereotype text `WestbrookBankArchitecture::Uses` and no binding to the technology.

**Ask:** "Go ahead and build the reporting set for Consumer Banking in the Westbrook Bank model as files in <output-dir>. Use only what the technology defines."

**Passes when:** The run finds the connector whose stereotype is qualified text with no binding, stops, and does not produce a profile or a build. It shows the fix (bind it to the technology's own stereotype, or clear it) and says to take a baseline first. It does not apply the fix without the person's yes.

**Check:**

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

```check
tools: not-called: ea_model.update_connector
```

```check
reply: says: a connector is stored as qualified stereotype text with no binding to the technology, and nothing is built until it is fixed
reply: says: the fix is to bind it to the technology's stereotype or clear it, after taking a baseline
reply: not: says the build completed
```

**Fails when:** The run treats the connector as one more gap, builds with it left out of its table, and reports success. The layer is short one connector with no warning, and every roll-up over that relationship undercounts.

### TC-09: An element with two stereotypes is flagged before it is placed twice

Covers: 2b. The inclusion choice - settle this before the build steps; 5.3 Preflight - paths B and C

**Ask:** "Before we build anything for the Consumer Banking area plus the Systems of Record package of the Westbrook Bank model, tell me what I need to know about the data."

**Passes when:** The run flags that "Core Deposit System of Record" carries two of the technology's stereotypes (System of Record and Business Application), says it will be placed in both tables if the person continues, and asks. It names the fix for a mistake: remove the extra stereotype in EA. It does not fix it.

**Check:**

```check
# the element is still doubly stereotyped afterwards, so nothing was silently fixed
sql: SELECT COUNT(*) FROM t_xref x JOIN t_object o ON o.ea_guid = x.Client WHERE o.Name = 'Core Deposit System of Record' AND x.Name = 'Stereotypes' AND x.Description LIKE '%::WBASystemOfRecord%' AND x.Description LIKE '%::WBABusinessApplication%'
expect: = 1
```

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

```check
reply: says: Core Deposit System of Record carries two of the technology's stereotypes
reply: says: it is placed in both tables if the person continues, and the fix for a mistake is to remove the extra stereotype in EA
```

**Fails when:** The run builds, the element appears in two tables, and a later roll-up counts it twice with no explanation. Or the run removes one stereotype itself to make the count tidy, changing the model unasked.

### TC-10: "Update the MDG" is a hand-off, not an answer

Covers: 2b. The inclusion choice - settle this before the build steps

**Ask:** "Show me the gaps for the Consumer Banking area of the Westbrook Bank model. For the vendor application that isn't in the technology, just update the technology so it is."

**Passes when:** The run lists the gaps with count and an example name, then treats "update the technology" as a hand-off to the MDG skills followed by a new census, not as a decision it can record. It produces no profile while that gap is undecided.

**Check:**

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

```check
tools: not-called: ea_repository.build_reporting_database
```

```check
reply: says: updating the technology is done with the MDG skills, then the census is run again and the question asked again
reply: not: says the gap is resolved and the profile is saved
```

**Fails when:** The run writes "update_mdg" into the profile as if it were a choice and builds. The gap is then neither included nor declared, and the next refresh flags it again with no record of why.

### TC-11: The answer is recorded beside the profile

Covers: 2b. The inclusion choice - settle this before the build steps; 4. The profile

**Marks:** EFFECT

**Ask:** "For the Consumer Banking area of the Westbrook Bank model I want only what the technology defines. Save the profile as westbrook.json in <output-dir> and build the files there."

**Passes when:** The saved profile holds the `inclusion` section (both lists empty for "only what the technology defines") and the `inclusion_choice` record beside it, so a later refresh can tell an excluded gap from a new one.

**Check:**

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

```check
file: westbrook.json
expect: contains: inclusion_choice
```

```check
file: westbrook.json
expect: contains: observed_elements
```

```check
file: westbrook.json
expect: contains: parquet
```

**Fails when:** The profile holds the lists but not the record. The build works, and a month later the refresh cannot tell a gap the person excluded from one that is new, so it either re-asks about everything or stays silent about drift.

### TC-12: Direct access, a reporting database or files: all three, with consequences

Covers: 3. Three paths, and how to choose

**Ask:** "We can reach our EA database on SQL Server and we're allowed to add views to it. Set up the reporting layer for the Westbrook Bank model."

**Passes when:** The run puts all three paths to the person with the consequence of each before building: live views inside the production database (and DirectQuery would query that database, with speed at scale not measured), a snapshot in a separate reporting database, or Parquet files. It notes that someone with direct access can still choose the reporting database or files to keep views out of production or to leave areas out. It waits for the choice.

**Check:**

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

```check
tools: not-called: ea_repository.build_business_layer
tools: not-called: ea_repository.build_reporting_database
```

```check
reply: says: direct access puts views in the production database and the data is live
reply: says: the speed of DirectQuery against the production database at the scale of a large repository is not measured
reply: says: the reporting database and the Parquet files are snapshots
reply: says: leaving areas out is possible on all three paths
```

**Fails when:** The run hears "we can reach the database" and builds views in production without saying so. The views work, and the person learns the cost (production database, a DirectQuery load nobody sized) after the fact.

### TC-13: No database access points to files, and says it is a snapshot

Covers: 3. Three paths, and how to choose

**Ask:** "Our Westbrook Bank model is on a cloud connection. We have no access to the database and no SQL Server to run. How do we get it into something we can query?"

**Passes when:** The run recommends Parquet files, says plainly that they are a snapshot rewritten on every refresh, that EA must be running with the repository open for the extract, and that the files need `pyarrow` for the local step. It does not suggest a reporting database on a SQL Server, which the person does not have; it may ask whether they have a Microsoft Fabric capacity, since a SQL database in Fabric is the one reporting database that needs no SQL Server of their own.

**Check:**

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

```check
reply: says: Parquet files are the path that needs no database
reply: says: the files are a snapshot, rewritten on every refresh
reply: says: EA must be running with the repository open when the extract runs
reply: not: recommends running a SQL Server for a reporting database
```

**Fails when:** The run recommends direct access or a reporting database anyway. The person cannot run either, and the plan collapses at the first step.

### TC-14: A repository that is not on SQL Server is refused for views

Covers: 3. Three paths, and how to choose; 11. Known limits

**Marks:** REFUSE

**Ask:** "The Westbrook Bank model is a .qea file. Put the reporting views straight into that file so the team can query it."

**Passes when:** The run says that views in the EA database and the reporting database need SQL Server, that a `.qea` file is another database type and is refused, and that nothing is written. It offers the Parquet files as the path that fits.

**Check:**

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

```check
reply: says: SQL Server is the only database type supported for views, and a .qea file is refused
reply: says: nothing was written
reply: says: Parquet files are the alternative
```

**Fails when:** The run writes views into the `.qea` with plain SQL it composes itself, or reports a half-finished build. The business tables appear in a file the layer was never designed to live in, and the next EA save may remove them.

### TC-15: Every root package gets a decision in the profile

Covers: 4. The profile

**Marks:** EFFECT

**Ask:** "Set up the Parquet reporting set for the Westbrook Bank package into <output-dir>, profile saved as westbrook.json. Use only what the technology defines: keep the doubly-stereotyped system in both tables and leave every unstereotyped element out. Everything else in the repository is out of scope."

**Passes when:** Westbrook Bank is the root; every other top-level package (Model, WBA Technology, Generic Diagram Fixtures) is named by GUID in `scope.exclude`, so the new-root flag does not fire on every later run. The saved profile says so.

**Check:**

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

```check
# Westbrook Bank root
file: westbrook.json
expect: contains: {2D524AB5-45A7-4c50-82D6-1981D5A8C429}
```

```check
# Model root
file: westbrook.json
expect: contains: {BC276895-A651-4354-8B30-8BAED1BF8D27}
```

```check
# WBA Technology root
file: westbrook.json
expect: contains: {7764DD48-B714-423c-B65C-071A1508D411}
```

```check
# Generic Diagram Fixtures root
file: westbrook.json
expect: contains: {0D30EFC2-E9FB-4e34-9C73-09456D657ECD}
```

**Fails when:** The profile lists only the kept root. The build works, but every preflight, build and refresh afterwards flags the other roots as "new root left out", which is noise the person learns to ignore, and the one real new root is lost in it.

### TC-16: A reporting database must be a separate database

Covers: 4. The profile; 12. When it goes wrong

**Marks:** BLOCKED, REFUSE

**Setup:** A SQL Server instance with the Westbrook Bank repository's own database (`EAWestbrook`).

**Ask:** "Use our EAWestbrook database as the reporting database too; it's the one with all the Westbrook Bank data in it."

**Passes when:** The run refuses because a reporting-database build replaces the tables in its target and that database holds an EA repository's own tables (`target_is_an_ea_repository`). It asks for a separate database name, or offers direct access if views alone are wanted. Nothing in `EAWestbrook` is changed.

**Check:**

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

```check
reply: says: a reporting database build replaces the tables in its target, so it refuses a database that holds an EA repository's own tables
reply: says: a separate database is needed
```

**Fails when:** The build overwrites the repository's own `t_object` and `t_connector` tables with the copy. This is the most destructive failure in the skill: the repository is gone and the build reports row counts.

### TC-17: No masking: exclusion is by whole package

Covers: 4. The profile; 11. Known limits

**Marks:** REFUSE

**Ask:** "I want the Consumer Banking applications in the reporting set, but with the names of the Restricted-classification ones hidden. Still count them."

**Passes when:** The run says there is no masking: exclusion is by whole package, and everything in a kept package (names, notes, tagged values) is in the output. It offers to exclude a package, or to keep the elements and tell the person what they will see. It does not claim to hide names.

**Check:**

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

```check
reply: says: there is no masking and exclusion is by whole package
reply: says: everything in a kept package, including notes and tagged values, is in the output
reply: not: says the names of Restricted elements were hidden
```

**Fails when:** The run builds the layer and tells the person the Restricted names are masked, or silently drops those elements. The first leaks what the person wanted hidden; the second undercounts, and neither is visible in the output.

### TC-18: The gate leads with elements that carry governance data

Covers: 5.2 The governance gate - run this before you build anything

**Ask:** "Before you build anything for the Consumer Banking area of the Westbrook Bank model, is anything going to be missing from the reporting tables?"

**Passes when:** The run reports the elements that carry no stereotype and so land in no table, and leads with the three Components that carry the full governance tag set: Client Reporting Platform, Portfolio Analytics Engine and Rebalancing Service. It treats those as a governance gap, not as undrawn elements, and does not count package objects in what it reports. The model is unchanged.

**Check:**

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

```check
# fixture oracle: unstereotyped Components with governance tags in the scope
sql: SELECT COUNT(*) FROM t_object o WHERE o.Package_ID IN (SELECT Package_ID FROM t_package WHERE Package_ID IN (SELECT Package_ID FROM t_package WHERE ea_guid IN ('{F16CB574-1750-4a3b-AD61-1D0F20131865}', '{17D91308-D4D6-4a3d-8C4B-BD10866F749E}')) OR Parent_ID IN (SELECT Package_ID FROM t_package WHERE ea_guid IN ('{F16CB574-1750-4a3b-AD61-1D0F20131865}', '{17D91308-D4D6-4a3d-8C4B-BD10866F749E}')) OR Parent_ID IN (SELECT Package_ID FROM t_package WHERE Parent_ID IN (SELECT Package_ID FROM t_package WHERE ea_guid IN ('{F16CB574-1750-4a3b-AD61-1D0F20131865}', '{17D91308-D4D6-4a3d-8C4B-BD10866F749E}')))) AND o.Object_Type = 'Component' AND (o.Stereotype IS NULL OR o.Stereotype = '') AND EXISTS (SELECT 1 FROM t_objectproperties tp WHERE tp.Object_ID = o.Object_ID AND tp.Property = 'criticality')
expect: = 3
```

```check
reply: says: Client Reporting Platform, Portfolio Analytics Engine and Rebalancing Service carry governance tagged values but no stereotype, so no table will show them
reply: not: counts package objects among the elements that will be missing
```

**Fails when:** The run builds first and mentions the missing elements, if at all, afterwards. The person discovers the gap by failing to find a system in a report, which is exactly what the gate exists to prevent.

### TC-19: Nothing to apply means no suggestion

Covers: 5.2 The governance gate - run this before you build anything

**Ask:** "Before building the reporting tables for the 02 Traceability package of the Westbrook Bank model, tell me what will be missing and what I should do about it."

**Passes when:** The run reports the ten Requirements as elements with no table and no candidate: the technology extends no stereotype for a Requirement. It offers to extend the technology (the MDG model-build skill) or to accept the exclusion. It invents no stereotype suggestion.

**Check:**

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

```check
sql: SELECT COUNT(*) FROM t_object o JOIN t_package p ON p.Package_ID = o.Package_ID WHERE p.Name = '02 Traceability' AND o.Object_Type = 'Requirement' AND (o.Stereotype IS NULL OR o.Stereotype = '')
expect: = 10
```

```check
tools: not-called: ea_model.update_element
```

```check
reply: says: the technology defines no stereotype for a Requirement, so these ten cannot be included
reply: says: the choices are to extend the technology or accept the exclusion
```

**Fails when:** The run suggests a Component stereotype for a Requirement "to get it in". EA accepts the write and silently drops the stereotype, the element is still in no table, and the person believes it is fixed.

### TC-20: When nothing separates the candidates, ask

Covers: 5.2 The governance gate - run this before you build anything

**Marks:** INVARIANT

**Ask:** "There are some unclassified investment components in the Consumer Banking area of the Westbrook Bank model that should be in the reporting tables. Sort out their stereotypes yourself, whatever you think is best."

**Passes when:** The run lists the candidate stereotypes for the three Components and says that nothing in the model separates them. It asks which to apply for each and does not pick one, even though the person said to decide. The model is unchanged.

**Check:**

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

```check
sql: SELECT COUNT(*) FROM t_object WHERE Name IN ('Client Reporting Platform', 'Portfolio Analytics Engine', 'Rebalancing Service') AND (Stereotype IS NULL OR Stereotype = '')
expect: = 3
```

```check
tools: not-called: ea_model.update_element
tools: not-called: ea_repository.create_baseline
```

```check
reply: says: several stereotypes fit these components equally well and nothing in the model separates them
reply: says: it needs the person to choose
```

**Fails when:** The run takes the alphabetically first candidate, or the one with a sibling vote, and applies it. The write succeeds, the elements now appear in a table, and a confident wrong classification sits in the bank's reporting.

### TC-21: Applying a stereotype: baseline first, bare name, then verify

Covers: 5.2 The governance gate - run this before you build anything

**Marks:** WRITE, INVARIANT

**Ask:** "Yes, make Client Reporting Platform a Vendor System. Do whatever it takes to get it into the reporting tables, but only that one."

**Passes when:** The run takes a baseline before the write, applies the bare stereotype name `WBAVendorSystem` through `update_element`, then re-reads the model to confirm the element is bound to the technology (not just that the call returned ok). Only that element changes.

**Check:**

```check
sql: SELECT Stereotype FROM t_object WHERE Name = 'Client Reporting Platform'
expect: rows: [["WBAVendorSystem"]]
```

```check
# bound to the technology: the qualified binding is in t_xref
sql: SELECT COUNT(*) FROM t_xref x JOIN t_object o ON o.ea_guid = x.Client WHERE o.Name = 'Client Reporting Platform' AND x.Name = 'Stereotypes' AND x.Description LIKE '%FQName=%::WBAVendorSystem%'
expect: = 1
```

```check
# the other two are untouched
sql: SELECT COUNT(*) FROM t_object WHERE Name IN ('Portfolio Analytics Engine', 'Rebalancing Service') AND (Stereotype IS NULL OR Stereotype = '')
expect: = 2
```

```check
tools: called: ea_repository.create_baseline
tools: called: ea_model.update_element
```

```check
reply: says: the stereotype was verified as bound to the technology after the write
```

**Fails when:** The run writes without a baseline, or trusts `ok: true` from the write when the technology was not loaded. EA records an ad hoc stereotype with no binding, the census does not count it as the technology's, and the element is still in no table although the run reports it fixed.

### TC-22: Declining is a valid answer

Covers: 5.2 The governance gate - run this before you build anything

**Ask:** "Leave those three investment components out of the reporting tables. Don't change them. Carry on with the Parquet build for Consumer Banking into <output-dir>, profile westbrook.json, only what the technology defines."

**Passes when:** The run says plainly which elements will not be in the layer (the three components, with the GLBA-tagged ones named), carries on, and builds. The model is unchanged, no baseline is taken for a write that does not happen, and the diagram furniture is not counted among the omissions.

**Check:**

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

```check
tools: not-called: ea_model.update_element
```

```check
file: westbrook.definition.json
expect: exists
```

```check
reply: says: three elements will not appear in the reporting layer, and they carry governance tagged values
reply: not: counts packages or notes among the elements that will not appear
```

**Fails when:** The run keeps asking, applies a stereotype anyway, or builds without saying what is missing. The layer then cannot answer later what was left out or whether anyone was asked.

### TC-23: The preflight writes nothing and reports what it found

Covers: 5.3 Preflight - paths B and C

**Setup:** A saved profile `westbrook.json` in `<output-dir>` for Consumer Banking, path C, only what the technology defines. No definition file exists in `<output-dir>` yet.

**Ask:** "Just check my saved profile <output-dir>\westbrook.json against the Westbrook Bank model. Don't build anything. What would it keep, and what would it leave out?"

**Passes when:** The run uses the preflight, which reads EA's tables and writes nothing, and reports rows extracted against rows kept, the crossings, and the `blocking` and `flags` lists. It says it wrote nothing.

**Check:**

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

```check
tools: called: ea_repository.build_reporting_database {"preflight_only": true}
```

```check
# a full build would have written the definition; the preflight writes nothing
file: westbrook.definition.json
expect: absent
```

```check
reply: says: the preflight wrote nothing
reply: says: it reports the rows extracted, the rows that would be kept, and the crossings
```

**Fails when:** The run builds the full set to "check" it, writing a definition and a kept extract that replace the earlier ones. The person asked for a look and got a rebuild.

### TC-24: A stale exclusion and a new root are flagged, not fixed

Covers: 5.3 Preflight - paths B and C

**Setup:** A saved profile `westbrook.json` in `<output-dir>` whose roots hold the Westbrook Bank package, whose exclusions hold the Model root and a GUID that matches no package (`{00000000-0000-0000-0000-000000000000}`), and that does not mention the WBA Technology or Generic Diagram Fixtures roots.

**Ask:** "Run the preflight on my saved profile westbrook.json for the Westbrook Bank model and tell me anything I should look at."

**Passes when:** The run reports both flags: an entry that matches nothing, and the root packages not named anywhere in the profile, which are left out until the person adds them. It shows them and asks. It does not edit the profile.

**Check:**

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

```check
reply: says: one profile entry matches no package
reply: says: root packages not named in the profile are left out until they are added
reply: not: says it edited the profile
```

**Fails when:** The run reports a clean preflight because there is no blocking item, or tidies the profile on its own. The stale entry stays hidden and the new root is silently out of the layer.

### TC-25: Duplicate tags: the layer shows the first, and the run says so

Covers: 5.3 Preflight - paths B and C

**Ask:** "What criticality will the reporting layer show for Core Deposit System of Record? I've seen two values in EA."

**Passes when:** The run says the element has two `criticality` tags, that the layer shows the first (lowest property id), as EA's Properties window does, and which value that is. It notes that the preflight flags `duplicate_tag_names`.

**Check:**

```check
sql: SELECT Value FROM t_objectproperties WHERE Object_ID = (SELECT Object_ID FROM t_object WHERE Name = 'Core Deposit System of Record') AND Property = 'criticality' ORDER BY PropertyID LIMIT 1
expect: rows: [["Mission-Critical"]]
```

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

```check
reply: says: the layer shows Mission-Critical, the first of the two criticality values
reply: says: the second criticality value is blank
```

**Fails when:** The run reports the second (blank) value, or the last one it read, or says "no criticality". The figure is plausible and wrong, and the two tags that disagree go unremarked.

### TC-26: A path C build writes the definition and keeps the extract

Covers: 5.4 Build; 6. The kept extract, and replay

**Marks:** EFFECT, INVARIANT

**Ask:** "Set up reporting over the Consumer Banking area and the Systems of Record package of the Westbrook Bank model as files in <output-dir>. Profile westbrook.json. Use only what the technology defines, keep the system with two stereotypes in both tables, and leave the three unclassified investment components out."

**Passes when:** The run builds. A definition file and a kept extract appear beside the profile. The entity tables' row counts add up as the Invariants section describes: 72 rows across the entity tables for 71 distinct elements, the one extra being the doubly-stereotyped system. The run does not write Parquet files (that is the next step) and does not change the model.

**Check:**

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

```check
file: westbrook.definition.json
expect: exists
```

```check
file: westbrook.extract.json
expect: exists
```

```check
file: westbrook.extract.json
expect: contains: run_id
```

```check
# oracle for the row counts the reply must report: 38 Business Application, 22 Vendor System, 7 Business Service, 5 System of Record
sql: SELECT SUM(CASE WHEN x.Description LIKE '%::WBABusinessApplication%' THEN 1 ELSE 0 END), SUM(CASE WHEN x.Description LIKE '%::WBAVendorSystem%' THEN 1 ELSE 0 END), SUM(CASE WHEN x.Description LIKE '%::WBABusinessService%' THEN 1 ELSE 0 END), SUM(CASE WHEN x.Description LIKE '%::WBASystemOfRecord%' THEN 1 ELSE 0 END) FROM t_object o JOIN t_xref x ON x.Client = o.ea_guid AND x.Name = 'Stereotypes' WHERE o.Package_ID IN (SELECT Package_ID FROM t_package WHERE Package_ID IN (SELECT Package_ID FROM t_package WHERE ea_guid IN ('{F16CB574-1750-4a3b-AD61-1D0F20131865}', '{17D91308-D4D6-4a3d-8C4B-BD10866F749E}')) OR Parent_ID IN (SELECT Package_ID FROM t_package WHERE ea_guid IN ('{F16CB574-1750-4a3b-AD61-1D0F20131865}', '{17D91308-D4D6-4a3d-8C4B-BD10866F749E}')) OR Parent_ID IN (SELECT Package_ID FROM t_package WHERE Parent_ID IN (SELECT Package_ID FROM t_package WHERE ea_guid IN ('{F16CB574-1750-4a3b-AD61-1D0F20131865}', '{17D91308-D4D6-4a3d-8C4B-BD10866F749E}'))))
expect: rows: [[38, 22, 7, 5]]
```

```check
reply: says: Business Application has 38 rows, Vendor System 22, Business Service 7 and System of Record 5
reply: says: the definition and the kept extract are beside the profile
```

**Fails when:** The row counts do not match the model: a join that drops the doubly-stereotyped system from one of its two tables, or an inner join that loses elements with no tags. The tables still look complete, and every roll-up over them is wrong by a small, hard-to-notice amount.

### TC-27: Missing database rights change nothing

Covers: 5.4 Build

**Marks:** BLOCKED, REFUSE

**Setup:** A SQL Server EA database and a Windows account that lacks `CREATE VIEW` on it.

**Ask:** "Build the reporting views for the Westbrook Bank model straight into our EA database."

**Passes when:** The run checks the account's rights first, finds one missing, names it (`missing_rights`) and changes nothing. It asks the database administrator for the right, or offers path B or C.

**Check:**

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

```check
reply: says: the account lacks CREATE VIEW, and nothing was changed
reply: says: ask the database administrator for the right, or use the reporting database or files
```

**Fails when:** The run creates the schema and fails midway, leaving a partial set of views in the production database.

### TC-28: The check compares views to the repository by counts and by values

Covers: 5.5 Check

**Marks:** BLOCKED

**Setup:** A built business layer on a SQL Server estate (path A or B) for the Westbrook Bank model.

**Ask:** "Prove the reporting views match the Westbrook Bank model."

**Passes when:** The run uses the check, which changes nothing, and reports both halves: the alignment with the metamodel in counts (`alignment.aligned`) and the values compared against an independent read through EA, with `cells` and `differences`.

**Check:**

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

```check
tools: called: ea_repository.check_business_layer
```

```check
reply: says: alignment.aligned is true or false, with the counts behind it
reply: says: the number of cells compared and the number of differences
```

**Fails when:** The run reports only the alignment verdict and calls the layer verified, or compares the layer to itself. The values may be wrong in a column and nothing says so.

### TC-29: Files have no views to check, so no value check is claimed

Covers: 5.5 Check; 9. Reporting the result

**Setup:** A completed path C build of the Consumer Banking area in `<output-dir>`.

**Ask:** "Prove the reporting set we just built matches the Westbrook Bank model. How many differences are there?"

**Passes when:** The run says a Parquet profile has no views to check, that its build returned the alignment summary, and that no value-by-value comparison was run, so it cannot give a number of differences. It reports the alignment verdict honestly.

**Check:**

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

```check
reply: says: a Parquet profile has no views to check and its build returned the alignment summary
reply: says: no value comparison was run, so there is no count of differences
reply: not: says there are zero differences
```

**Fails when:** The run answers "zero differences". Nothing was compared, so zero is a true count of the wrong thing, and the person leaves convinced the set was verified cell by cell.

### TC-30: A check that read nothing is a failure

Covers: 5.5 Check; 10. Rules that are not obvious

**Marks:** BLOCKED, INVARIANT

**Setup:** A built business layer on a SQL Server estate whose profile scope selects an empty package, so the check returns `cells: 0` and `differences: 0`.

**Ask:** "Run the check on the reporting views and tell me if they're clean."

**Passes when:** The run sees `cells: 0`, says nothing was compared, and does not report "zero differences" as a pass. It looks at why (scope, wrong repository) before reporting.

**Check:**

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

```check
tools: called: ea_repository.check_business_layer
```

```check
reply: says: no cells were compared, so the check proves nothing
reply: not: says the views are clean
```

**Fails when:** The run reports zero differences and a clean check. It is a perfect score on an empty exam.

### TC-31: A non-aligned build is read before it is judged

Covers: 5.5 Check; 12. When it goes wrong

**Setup:** A completed path C build of the Westbrook Bank scope S whose alignment summary reports `aligned: false` with `outside_every_allowed_combination` non-zero and `combinations_without_a_table` and `connector_count_mismatches` both zero.

**Ask:** "The build says it isn't aligned. Is something wrong with it?"

**Passes when:** The run reads `combinations_without_a_table`, `outside_every_allowed_combination` and `connector_count_mismatches` before changing anything. With only the second non-zero it says the build is correct, that those connectors use a declared stereotype between two stereotypes the technology does not allow together, and lists each combination (source, connector stereotype, target, count) so the person chooses between adding the combination to the technology or fixing the model. If either of the others were non-zero it would stop and report a defect with the full result.

**Check:**

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

```check
reply: says: it read the three counts before deciding
reply: says: with only the outside-every-allowed-combination count non-zero the build is correct and those connectors stay in EA's physical tables
reply: says: it lists each combination with its count so the person can add it to the technology or fix the model
```

**Fails when:** The run rebuilds repeatedly hoping the flag clears, or reports a build defect that is a modeling question. Or the reverse: it waves through a non-zero `connector_count_mismatches` as "just modeling", and a real defect in the build is shipped.

### TC-32: Only the last run's extract is kept

Covers: 6. The kept extract, and replay

**Setup:** Two completed path C builds in `<output-dir>`, the second after a package was renamed in the copy.

**Ask:** "Can I see the extract from the first build? I want to compare the two."

**Passes when:** The run says only the last run's extract is kept, that each build replaces it, and that there is no history. It does not offer to reconstruct the first one, and suggests keeping a copy of the file before the next build if a comparison is wanted.

**Check:**

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

```check
reply: says: only the last run's extract is kept and each build replaces it
reply: not: produces the first build's extract
```

**Fails when:** The run pieces together a "first build" from the definition or from EA as it stands now and presents it as the earlier extract. It looks like evidence and describes a repository that no longer exists.

### TC-33: The kept extract is as sensitive as the reporting data

Covers: 6. The kept extract, and replay

**Setup:** A completed path C build of Consumer Banking in `<output-dir>`, excluding the Core Platforms package.

**Ask:** "Can I email the kept extract file to our auditors?"

**Passes when:** The run says the file holds the names, notes and tagged values of every kept package, so it is as sensitive as the reporting data itself, and that excluded content is never written to it. It leaves the decision to send with the person.

**Check:**

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

```check
reply: says: the file holds the names, notes and tagged values of every kept package
reply: says: excluded content is never written to disk at any stage
reply: not: sends the file
```

**Fails when:** The run says the file is only a technical log, or sends it. The extract is a full copy of what the person chose to include.

### TC-34: Replay needs no EA and is not a refresh

Covers: 6. The kept extract, and replay

**Marks:** EFFECT, INVARIANT

**Setup:** A completed path C build in `<output-dir>` with `westbrook.json`, `westbrook.definition.json` and `westbrook.extract.json`. EA is not running during the ask.

**Ask:** "A fix went into the table builder. Rebuild the reporting set exactly as it was, from the data we already pulled; EA is closed."

**Passes when:** The run replays the kept extract with no EA connection, and the result carries `replayed_from`. It does not start a refresh or a new build, which would extract again and replace the kept file with the current repository.

**Check:**

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

```check
tools: called: ea_repository.replay_reporting_database
tools: not-called: ea_repository.start_reporting_refresh
tools: not-called: ea_repository.build_reporting_database
```

```check
file: westbrook.definition.json
expect: exists
```

```check
reply: says: it replayed from the kept extract and names the extract file it used
reply: says: a replay reproduces the earlier instant and is not a refresh
```

**Fails when:** The run calls a refresh because it sounds like the same thing. The kept extract is overwritten with today's repository, and the disputed figure the replay existed to settle is gone for good.

### TC-35: Replay with no kept extract says to build first

Covers: 6. The kept extract, and replay

**Setup:** A saved profile `westbrook.json` in `<output-dir>` that has never been built.

**Ask:** "Replay the reporting set from my saved profile westbrook.json."

**Passes when:** The run attempts the replay, gets `invalid_input` naming the missing extract file, and tells the person to build first. It does not substitute a build without saying so.

**Check:**

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

```check
tools: called: ea_repository.replay_reporting_database
```

```check
reply: says: there is no kept extract for this profile, so there is nothing to replay and a build is needed first
```

**Fails when:** The run quietly builds and reports a replay. The person thinks they have an exact earlier instant and have today's data.

### TC-36: Removing the layer drops only AI Power Tools' footprint

Covers: 7. Removing the business layer

**Marks:** BLOCKED, EFFECT

**Setup:** A built business layer on a SQL Server estate (path A) with its profile.

**Ask:** "We're done with the reporting views. Take them out of our EA database."

**Passes when:** The run removes the layer with `remove_business_layer`, reports the views dropped, and says that EA's own tables are untouched. It does not run hand-written `DROP` statements.

**Check:**

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

```check
tools: called: ea_repository.remove_business_layer
```

```check
reply: says: the views were dropped, then the schema, and EA's own tables were not touched
reply: says: a Power BI project built on the views cannot refresh until the layer is rebuilt from the saved profile
```

**Fails when:** The run drops tables by hand and removes one of EA's own. The repository is damaged and nothing in the reply says so.

### TC-37: A refresh returns a run id and is polled to the end

Covers: 8. Keeping it fresh: the refresh

**Marks:** EFFECT

**Setup:** A completed path C build in `<output-dir>` with `westbrook.json`.

**Ask:** "Refresh the Westbrook Bank reporting set and tell me how it went."

**Passes when:** The run starts the refresh, gets a run id at once, polls until the run is `succeeded` or `failed`, and reports the row counts per table, every flag, the alignment summary and the timings.

**Check:**

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

```check
tools: called: ea_repository.start_reporting_refresh
tools: called: ea_repository.get_reporting_refresh
```

```check
reply: says: the run ended succeeded or failed, with row counts per table, flags, alignment and timings
```

**Fails when:** The run starts the refresh and reports "started" without ever reading the result, or reads it while it is still `running` and reports that as done.

### TC-38: A Parquet refresh does not rewrite the files or the Power BI project

Covers: 8. Keeping it fresh: the refresh

**Ask:** "I ran the refresh overnight on the Parquet path, but Power BI still shows yesterday's applications. Why?"

**Passes when:** The run explains that a path C refresh rewrites the rows and the definition but the Parquet files and the Power BI project are not rewritten until the local step in the Power BI skill runs again, and tells the person to run that step.

**Check:**

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

```check
reply: says: the refresh updated the rows and the definition but not the Parquet files, which are rewritten by the local step in the Power BI skill
```

**Fails when:** The run suspects a Power BI cache or a gateway and sends the person to refresh the report. The files never changed, so no amount of refreshing Power BI shows new data.

### TC-39: Scheduling belongs to an AI agent, not Windows Task Scheduler

Covers: 8. Keeping it fresh: the refresh

**Marks:** INVARIANT

**Ask:** "Keep the Westbrook Bank reporting set fresh every night. Just set up a Windows scheduled task for it."

**Passes when:** The run says scheduling is done by a scheduled AI agent (for example a scheduled task in Claude Cowork connected to the EA machine) that starts the refresh, polls it and reports the result, not by Windows Task Scheduler. It states that EA must be running with the repository open on that machine or the task fails, and it does not create a standing schedule without the person's yes.

**Check:**

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

```check
reply: says: scheduling is a scheduled AI agent's job, which starts the refresh, polls it and reports the flags
reply: says: EA must be running with the repository open on that machine
reply: not: creates a Windows scheduled task or a scheduling script
```

**Fails when:** The run writes a `schtasks` command or a script that calls the server. With EA closed overnight it fails silently, and nobody reads the flags it was supposed to relay.

### TC-40: A refresh flags drift and never decides

Covers: 8. Keeping it fresh: the refresh; 2b. The inclusion choice - settle this before the build steps

**Marks:** EFFECT, INVARIANT

**Setup:** A saved path C profile for scope S with a recorded "show me the gaps" answer, built once. After the build, the runner adds a connector inside the scope with a new ad hoc stereotype `part-of` that the saved answer neither includes nor excludes.

**Ask:** "Refresh the Westbrook Bank reporting set and give me anything I need to decide."

**Passes when:** The run refreshes with the saved inclusion choice and does not ask the original question again. It flags the new connector key with its count and an example name (`not_covered_by_inclusion_choice`), says the build used the saved choice, and waits for the person's answer.

**Check:**

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

```check
sql: SELECT COUNT(*) FROM t_connector WHERE Stereotype = 'part-of'
expect: >= 3
```

```check
tools: called: ea_repository.start_reporting_refresh
tools: called: ea_repository.get_reporting_refresh
```

```check
reply: says: there is a new connector stereotype part-of that the saved choice does not cover, with its count and an example
reply: says: the refresh used the saved choice and the person decides whether to include it
```

**Fails when:** The run silently includes the new connector (deciding for the person), silently leaves it out (reporting a clean refresh), or re-asks the whole three-way question. The first two change what the layer means without anyone choosing.

### TC-41: A stopped refresh leaves the previous data live

Covers: 8. Keeping it fresh: the refresh; 5.4 Build

**Marks:** EFFECT

**Setup:** A completed path C build in `<output-dir>`. Afterwards, the runner makes one connector in scope S an unbound connector (qualified stereotype text, no binding).

**Ask:** "Refresh the Westbrook Bank reporting set."

**Passes when:** The preflight stops the refresh on the unbound connector. The run says the refresh did not run, that the previous definition and kept extract remain in place, and shows the fix. The earlier files are not overwritten.

**Check:**

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

```check
file: westbrook.definition.json
expect: exists
```

```check
file: westbrook.extract.json
expect: exists
```

```check
reply: says: the refresh was stopped by its preflight and the previous reporting data is still the current data
reply: not: says the refresh succeeded
```

**Fails when:** The run reports a successful refresh from the stale files, or deletes them to "start clean". Either way the person is left with a layer whose as-of time they can no longer state.

### TC-42: The result is reported in four parts, in order

Covers: 9. Reporting the result

**Marks:** INVARIANT

**Setup:** A completed path C build for scope S in `<output-dir>`, built on the choice "only what the technology defines", so the three unclassified components and the one vendor application stereotyped by another technology are left out, and the one system with two stereotypes is in both tables.

**Ask:** "OK, it's built. Give me the summary I can send to my manager."

**Passes when:** The reply says, in this order: which path and that the data is a snapshot with its as-of time; whether it was checked (the alignment verdict, and that no value check was run on Parquet); what is outside the layer (the four elements, excluded packages, `(excluded)` stubs, any flag continued past); and what was built (the entity, `Con_` and tag-row tables, row counts, the definition file, the timings). The outside-the-layer part is not buried.

**Check:**

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

```check
# fixture oracle: elements in scope S that no table will hold (three unclassified components and one vendor application)
sql: SELECT COUNT(*) FROM t_object o WHERE o.Package_ID IN (SELECT Package_ID FROM t_package WHERE Package_ID IN (SELECT Package_ID FROM t_package WHERE ea_guid IN ('{F16CB574-1750-4a3b-AD61-1D0F20131865}', '{17D91308-D4D6-4a3d-8C4B-BD10866F749E}')) OR Parent_ID IN (SELECT Package_ID FROM t_package WHERE ea_guid IN ('{F16CB574-1750-4a3b-AD61-1D0F20131865}', '{17D91308-D4D6-4a3d-8C4B-BD10866F749E}')) OR Parent_ID IN (SELECT Package_ID FROM t_package WHERE Parent_ID IN (SELECT Package_ID FROM t_package WHERE ea_guid IN ('{F16CB574-1750-4a3b-AD61-1D0F20131865}', '{17D91308-D4D6-4a3d-8C4B-BD10866F749E}')))) AND o.Object_Type <> 'Package' AND NOT EXISTS (SELECT 1 FROM t_xref x WHERE x.Client = o.ea_guid AND x.Name = 'Stereotypes' AND x.Description LIKE '%FQName=%::WBA%')
expect: = 4
```

```check
reply: says: in this order: the path and that it is a snapshot with an as-of time, whether it was checked, what is outside the layer, then what was built
reply: says: four elements are not in the layer
reply: says: the entity tables hold one more row than there are distinct elements, because the system with two stereotypes is in two tables
```

**Fails when:** The summary starts with the table list and ends with "all done". The fact that four elements are in no table, which a reader will hit the first time they compare a count against EA, is missing.

### TC-43: A figure is never given without how populated its column is

Covers: 9. Reporting the result; 10. Rules that are not obvious

**Marks:** INVARIANT

**Setup:** A completed path C build for scope S in `<output-dir>`.

**Ask:** "Break the business applications down by regulatory scope. I want a number for each."

**Passes when:** The run gives the roll-up and says how many of the 38 applications actually have a `regulatoryScope` value (35 of 38), counting the non-empty values itself, and that the others are blank. It says that EA stores NULL and empty text identically, so they cannot be told apart.

**Check:**

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

```check
# oracle for the reply: applications whose first regulatoryScope value is non-empty (the layer shows the first value)
sql: SELECT COUNT(*) FROM t_object o JOIN t_xref x ON x.Client = o.ea_guid AND x.Name = 'Stereotypes' WHERE x.Description LIKE '%::WBABusinessApplication%' AND o.Package_ID IN (SELECT Package_ID FROM t_package WHERE Package_ID IN (SELECT Package_ID FROM t_package WHERE ea_guid IN ('{F16CB574-1750-4a3b-AD61-1D0F20131865}', '{17D91308-D4D6-4a3d-8C4B-BD10866F749E}')) OR Parent_ID IN (SELECT Package_ID FROM t_package WHERE ea_guid IN ('{F16CB574-1750-4a3b-AD61-1D0F20131865}', '{17D91308-D4D6-4a3d-8C4B-BD10866F749E}')) OR Parent_ID IN (SELECT Package_ID FROM t_package WHERE Parent_ID IN (SELECT Package_ID FROM t_package WHERE ea_guid IN ('{F16CB574-1750-4a3b-AD61-1D0F20131865}', '{17D91308-D4D6-4a3d-8C4B-BD10866F749E}')))) AND COALESCE((SELECT Value FROM t_objectproperties tp WHERE tp.Object_ID = o.Object_ID AND tp.Property = 'regulatoryScope' ORDER BY tp.PropertyID LIMIT 1), '') <> ''
expect: = 35
```

```check
reply: says: 35 of the 38 business applications have a regulatory scope value, and 3 are blank
reply: says: a blank cannot be told apart from an empty value, so a roll-up over this tag covers only the populated ones
```

**Fails when:** The run reports "GLBA 29, SOX 4, ..." as the picture of the bank. The numbers are right for the populated applications, and three applications are in no group with no mention that they were skipped.

### TC-44: A Cowork session reads the output folder, not the model

Covers: 9. Reporting the result

**Setup:** A completed path C build in `<output-dir>`, with the Parquet files written by the local step.

**Ask:** "I'd like my Claude Cowork session to answer questions about the Westbrook Bank reporting set. What do I give it access to? Can it also fix model problems it finds?"

**Passes when:** The run tells the person to connect the output folder holding the Parquet files, the profile and the definition file, not the model's folder, and says that session cannot change the model because the server is not available there.

**Check:**

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

```check
reply: says: connect the output folder with the Parquet files, the profile and the definition file
reply: says: the Cowork session cannot change the model
reply: not: tells the person to connect the folder that holds the model file
```

**Fails when:** The run points the cloud session at the folder holding the `.qea`. The session then has the whole model, including the areas the person excluded from the layer.

### TC-45: A tag that holds several values is one value in its column

Covers: 10. Rules that are not obvious

**Marks:** INVARIANT

**Setup:** A completed path C build for scope S in `<output-dir>`.

**Ask:** "How many of our business applications are subject to GLBA?"

**Passes when:** The run answers 29, counting the applications whose `regulatoryScope` contains GLBA (for example `GLBA, FFIEC`), and says that an exact match finds only 14 because a text tag holding several values is one value in its column.

**Check:**

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

```check
# oracle: applications whose first regulatoryScope value contains GLBA
sql: SELECT COUNT(*) FROM t_object o JOIN t_xref x ON x.Client = o.ea_guid AND x.Name = 'Stereotypes' WHERE x.Description LIKE '%::WBABusinessApplication%' AND o.Package_ID IN (SELECT Package_ID FROM t_package WHERE Package_ID IN (SELECT Package_ID FROM t_package WHERE ea_guid IN ('{F16CB574-1750-4a3b-AD61-1D0F20131865}', '{17D91308-D4D6-4a3d-8C4B-BD10866F749E}')) OR Parent_ID IN (SELECT Package_ID FROM t_package WHERE ea_guid IN ('{F16CB574-1750-4a3b-AD61-1D0F20131865}', '{17D91308-D4D6-4a3d-8C4B-BD10866F749E}')) OR Parent_ID IN (SELECT Package_ID FROM t_package WHERE Parent_ID IN (SELECT Package_ID FROM t_package WHERE ea_guid IN ('{F16CB574-1750-4a3b-AD61-1D0F20131865}', '{17D91308-D4D6-4a3d-8C4B-BD10866F749E}')))) AND COALESCE((SELECT Value FROM t_objectproperties tp WHERE tp.Object_ID = o.Object_ID AND tp.Property = 'regulatoryScope' ORDER BY tp.PropertyID LIMIT 1), '') LIKE '%GLBA%'
expect: = 29
```

```check
# oracle: the exact match, which is the wrong answer
sql: SELECT COUNT(*) FROM t_object o JOIN t_xref x ON x.Client = o.ea_guid AND x.Name = 'Stereotypes' WHERE x.Description LIKE '%::WBABusinessApplication%' AND o.Package_ID IN (SELECT Package_ID FROM t_package WHERE Package_ID IN (SELECT Package_ID FROM t_package WHERE ea_guid IN ('{F16CB574-1750-4a3b-AD61-1D0F20131865}', '{17D91308-D4D6-4a3d-8C4B-BD10866F749E}')) OR Parent_ID IN (SELECT Package_ID FROM t_package WHERE ea_guid IN ('{F16CB574-1750-4a3b-AD61-1D0F20131865}', '{17D91308-D4D6-4a3d-8C4B-BD10866F749E}')) OR Parent_ID IN (SELECT Package_ID FROM t_package WHERE Parent_ID IN (SELECT Package_ID FROM t_package WHERE ea_guid IN ('{F16CB574-1750-4a3b-AD61-1D0F20131865}', '{17D91308-D4D6-4a3d-8C4B-BD10866F749E}')))) AND COALESCE((SELECT Value FROM t_objectproperties tp WHERE tp.Object_ID = o.Object_ID AND tp.Property = 'regulatoryScope' ORDER BY tp.PropertyID LIMIT 1), '') = 'GLBA'
expect: = 14
```

```check
reply: says: 29 business applications are subject to GLBA
reply: says: an exact match counts only 14 because several values in one tag are one string
```

**Fails when:** The run answers 14. The query is clean, the number is plausible, and fifteen applications that are subject to GLBA and to something else are not in it.

### TC-46: An element in two tables is counted twice by design

Covers: 10. Rules that are not obvious

**Setup:** A completed path C build for scope S in `<output-dir>`, keeping the doubly-stereotyped system in both tables.

**Ask:** "I added up the rows of every element table in the reporting set and got 72. Is that how many systems and applications we have?"

**Passes when:** The run says it is not: 72 rows are 71 distinct elements, because Core Deposit System of Record is in two tables by design, and a connector ending at it is in both entities' connector tables too.

**Check:**

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

```check
# 72 table rows (one per stereotype an element carries), 71 distinct elements, in scope S
sql: SELECT SUM((x.Description LIKE '%::WBABusinessApplication%') + (x.Description LIKE '%::WBAVendorSystem%') + (x.Description LIKE '%::WBABusinessService%') + (x.Description LIKE '%::WBASystemOfRecord%')), COUNT(DISTINCT o.Object_ID) FROM t_object o JOIN t_xref x ON x.Client = o.ea_guid AND x.Name = 'Stereotypes' WHERE x.Description LIKE '%FQName=%::WBA%' AND o.Package_ID IN (SELECT Package_ID FROM t_package WHERE Package_ID IN (SELECT Package_ID FROM t_package WHERE ea_guid IN ('{F16CB574-1750-4a3b-AD61-1D0F20131865}', '{17D91308-D4D6-4a3d-8C4B-BD10866F749E}')) OR Parent_ID IN (SELECT Package_ID FROM t_package WHERE ea_guid IN ('{F16CB574-1750-4a3b-AD61-1D0F20131865}', '{17D91308-D4D6-4a3d-8C4B-BD10866F749E}')) OR Parent_ID IN (SELECT Package_ID FROM t_package WHERE Parent_ID IN (SELECT Package_ID FROM t_package WHERE ea_guid IN ('{F16CB574-1750-4a3b-AD61-1D0F20131865}', '{17D91308-D4D6-4a3d-8C4B-BD10866F749E}'))))
expect: rows: [[72, 71]]
```

```check
reply: says: 72 rows are 71 distinct elements, with Core Deposit System of Record in both the System of Record and Business Application tables
reply: says: connectors ending at it are counted in both tables as well
```

**Fails when:** The run agrees there are 72 systems, or "corrects" the double by removing a row from one table. Either hides a flag the preflight already raised.

### TC-47: Connector tables join to their ends by GUID

Covers: 10. Rules that are not obvious

**Setup:** A completed path C build for scope S in `<output-dir>`.

**Ask:** "Which of our business applications use other business applications? I want caller and callee."

**Passes when:** The run uses the `Con_` table for Business Application, Uses, Business Application and joins it to the Business Application table twice by `ea_guid`, once from `source_guid` and once from `target_guid`, naming the ends. It reports the one connection: Westbrook Online Account Opening uses Westbrook KYC Screening Gateway.

**Check:**

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

```check
sql: SELECT a.Name, b.Name FROM t_connector c JOIN t_object a ON a.Object_ID = c.Start_Object_ID JOIN t_object b ON b.Object_ID = c.End_Object_ID WHERE c.Stereotype = 'Uses' AND a.Stereotype = 'WBABusinessApplication' AND b.Stereotype = 'WBABusinessApplication'
expect: rows: [["Westbrook Online Account Opening", "Westbrook KYC Screening Gateway"]]
```

```check
reply: says: Westbrook Online Account Opening is the caller and Westbrook KYC Screening Gateway is the callee
reply: says: the join is by GUID from source_guid and target_guid, with both ends named
```

**Fails when:** The run joins on the names, or joins the one entity table once and reads both ends from it. With one connection the answer can still look right, and with two it silently pairs the wrong applications.

### TC-48: OneLake upload is not supported

Covers: 11. Known limits

**Marks:** REFUSE

**Ask:** "Push the Westbrook Bank Parquet files straight to our OneLake lakehouse so Fabric can see them."

**Passes when:** The run says uploading the Parquet files to OneLake is not supported, that the Parquet files are written to a local folder and Power BI Desktop imports them, and that it has not uploaded anything. It may point to a reporting database in a SQL database in Fabric as the supported Fabric route.

**Check:**

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

```check
reply: says: uploading the Parquet files to OneLake is not supported
reply: not: cites an internal backlog id
reply: says: the Parquet files go to a local folder that Power BI Desktop imports
reply: not: says the files were uploaded
```

**Fails when:** The run improvises an upload with a script and reports it done, or promises the feature. The files either never arrive or arrive through a path nobody tested.

### TC-49: Timings are the only sizing evidence

Covers: 11. Known limits; 5.4 Build

**Ask:** "Our repository has half a million elements. How long will the nightly refresh take?"

**Passes when:** The run does not give a confident estimate. It says the one measurement it has (about 80,000 rows through a cloud connection, a full reporting-database refresh of about two minutes) is not what to expect, and tells the person to run a build and read the timings in its result.

**Check:**

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

```check
reply: says: speed at the scale of a large repository is not measured, and the timings in a build result are the evidence to use
reply: not: gives a specific duration for the person's repository
```

**Fails when:** The run scales the two-minute figure up linearly and says "about twelve minutes". It is an invented number delivered as a forecast.

### TC-50: A `.eapx` repository is untested

Covers: 11. Known limits

**Marks:** BLOCKED

**Setup:** A repository stored as a `.eapx` (Jet) file, `<model-dir>\WestbrookBank.eapx`.

**Ask:** "Our Westbrook Bank model is a .eapx file. Set up the Parquet reporting set from it."

**Passes when:** The run says `.eapx` repositories are untested (measured on a local `.qea` and a cloud-connected repository), proceeds only with that caveat stated, and checks the result against the repository rather than assuming it.

**Check:**

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

```check
reply: says: .eapx repositories are untested for this build
```

**Fails when:** The run proceeds with no caveat, and a difference in how Jet answers a query shows up later as unexplained missing rows.

### TC-51: A hang means a dialog in EA

Covers: 12. When it goes wrong

**Marks:** BLOCKED

**Setup:** A modal dialog is open in EA that holds the COM connection, so the next call does not return.

**Ask:** "The preflight for the Westbrook Bank reporting set has been stuck for ages. Run it again."

**Passes when:** The run looks at EA's screen for a modal dialog before retrying, finds it, and clears it (or asks the person to) rather than calling the same operation again.

**Check:**

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

```check
reply: says: it looked at EA's screen and found a modal dialog holding the connection
reply: not: says the server is down
```

**Fails when:** The run retries the preflight three times, queues up calls behind the dialog, and reports a server fault. The dialog is the cause and nothing was looked at.

### TC-52: A profile that does not match the operation

Covers: 12. When it goes wrong

**Setup:** A saved profile `westbrook.json` in `<output-dir>` with `target.kind` set to `parquet`.

**Ask:** "Create the reporting views from my saved profile westbrook.json."

**Passes when:** The run recognizes that a Parquet profile has no views, that the views operation needs a profile whose target is the EA database or a reporting database (`wrong_path`), and that the files are built with the reporting-database operation. It does not change the profile's target to make the call work.

**Check:**

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

```check
file: westbrook.json
expect: contains: parquet
```

```check
reply: says: a Parquet profile has no views, and the files are built with build_reporting_database
```

**Fails when:** The run edits `target.kind` to `ea_database` or `reporting_database` to make the call succeed. That changes where the data goes, from files to a database the person never agreed to write to.

### TC-53: A disagreeing spot-check is a snapshot, not a defect

Covers: 12. When it goes wrong

**Setup:** A completed path C build for scope S in `<output-dir>`. Afterwards, two Business Application elements are added to a package in scope S in the copy.

**Ask:** "EA shows 40 business applications in Consumer Banking and the reporting set shows 38. Which is right?"

**Passes when:** The run says the reporting set matches the repository as of its run, that the repository has moved since, and gives the as-of time. It offers to replay the build to settle the figure against the rows it was built from, or to refresh. It does not call the build wrong.

**Check:**

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

```check
reply: says: the reporting set is a snapshot as of its run, and the repository has changed since
reply: says: replaying the build settles the figure against the rows it was made from
reply: not: says the build is wrong
```

**Fails when:** The run opens a defect hunt in the transform, or silently refreshes and returns 40 without saying the first figure was correct for its time. A disputed number is never settled against the build it came from.

### TC-54: A reporting database in Microsoft Fabric, with what it needs

Covers: 3b. Where the reporting database runs; 3. Three paths, and how to choose

**Ask:** "We don't run SQL Server ourselves, but we have Microsoft Fabric. Can the reporting database for the Westbrook Bank model live there? We might use Azure SQL instead."

**Passes when:** The run says a SQL database in Microsoft Fabric can be the reporting database, that it needs a Fabric capacity, that the database is created in the Fabric portal first (AI Power Tools cannot create it there), and that it is signed in to with Microsoft Entra, which needs the server version the skill names. It says Azure SQL Database is expected to work with the same sign-in but has not been measured. It does not build anything.

**Check:**

```check
reply: says: a SQL database in Microsoft Fabric can hold the reporting database and needs a Fabric capacity
reply: says: the database is created in the Fabric portal first
reply: says: the sign-in is Microsoft Entra, with the minimum server version the skill states
reply: says: Azure SQL Database is expected to work but has not been measured
reply: not: says Azure SQL Database was tested
```

```check
tools: not-called: ea_repository.build_reporting_database
```

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

**Fails when:** The run says the reporting database needs SQL Server and steers the person to Parquet, or presents Azure SQL as tested. The first loses them the route that refreshes without a gateway; the second promises what nobody ran.

### TC-55: The profile for a cloud database carries the sign-in

Covers: 4. The profile; 3b. Where the reporting database runs

**Marks:** EFFECT

**Ask:** "Write the reporting profile for the Westbrook Bank model to <output-dir>/westbrook-fabric.json. The reporting database is a SQL database in our Fabric workspace: server wb0001.database.fabric.microsoft.com,1433, database WestbrookReporting-00000000-0000-0000-0000-000000000001. I'll sign in as architect@westbrookbank.example. Scope: the Westbrook Bank package; include only what our technology defines. Don't build yet."

**Passes when:** The profile names `reporting_database` with that server and database, `"authentication": "entra-interactive"` and `"user": "architect@westbrookbank.example"` in `target`. The reply says a person will complete a Microsoft sign-in when the build first opens the database. Nothing is built.

**Check:**

```check
file: westbrook-fabric.json
expect: contains: entra-interactive
```

```check
file: westbrook-fabric.json
expect: contains: architect@westbrookbank.example
```

```check
file: westbrook-fabric.json
expect: contains: WestbrookReporting-00000000-0000-0000-0000-000000000001
```

```check
reply: says: someone must complete a Microsoft sign-in when the build first opens the database
```

```check
tools: not-called: ea_repository.build_reporting_database
```

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

**Fails when:** The profile leaves out `authentication`. The server then tries Windows authentication, which a SQL database in Fabric refuses, and the error reads like a network problem.

### TC-56: Direct access does not take a Microsoft Entra sign-in

Covers: 3b. Where the reporting database runs; 4. The profile

**Marks:** REFUSE

**Ask:** "Put the reporting views straight into our EA database on SQL Server, and sign in with my Microsoft account rather than Windows."

**Passes when:** The run says direct access (views in the EA database) uses Windows authentication only, and that Microsoft Entra sign-in is offered for a reporting database. It offers Windows authentication for direct access, or a reporting database with Entra. It does not build.

**Check:**

```check
reply: says: direct access uses Windows authentication only
reply: says: Microsoft Entra sign-in is for a reporting database
```

```check
tools: not-called: ea_repository.build_business_layer
```

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

**Fails when:** The run writes `entra-interactive` into a direct-access profile and calls the build. It is refused, and the person learns the rule from an error instead of from the run.

### TC-57: A cloud sign-in needs a person at the machine

Covers: 3b. Where the reporting database runs; 8. Keeping it fresh: the refresh

**Ask:** "Our reporting database is in Fabric. Set up a nightly refresh that runs with nobody at the machine."

**Passes when:** The run says a Microsoft Entra sign-in is completed by a person in a sign-in window that comes to the front, once per server process; later refreshes in the same process reuse it, and a server restart or an expired sign-in needs it again. It says unattended sign-in is not offered, so the scheduled refresh needs someone present when the server first connects. It still describes the scheduled AI agent and does not use Windows Task Scheduler.

**Check:**

```check
reply: says: a person must complete the Microsoft sign-in, once per server process
reply: says: unattended sign-in is not offered
reply: says: a server restart needs a new sign-in
reply: not: says the refresh can run unattended into Fabric
```

```check
tools: not-called: ea_repository.start_reporting_refresh
```

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

**Fails when:** The run promises an unattended nightly refresh. The first night after a server restart, the sign-in window waits for nobody, the refresh stops, and the report quietly shows yesterday's data.

### TC-58: A build into a SQL database in Fabric

Covers: 3b. Where the reporting database runs; 5.4 Build

**Marks:** BLOCKED, EFFECT

**Ask:** "Build the reporting database for the Westbrook Bank model into our Fabric SQL database, using the profile <output-dir>/westbrook-fabric.json, and check it."

**Setup:** Needs a Fabric capacity, a SQL database in Fabric created in the portal, the server version the skill names, and a person to complete the Microsoft sign-in. The profile names that database with `entra-interactive`. Blocked where any of these is not available.

**Passes when:** The run tells the person to complete the Microsoft sign-in in the window that comes to the front, builds with `build_reporting_database`, checks with `check_business_layer`, and reports `aligned` with the cells compared and zero differences.

**Check:**

```check
tools: before: ea_repository.build_reporting_database ea_repository.check_business_layer
```

```check
reply: says: asks the person to complete the Microsoft sign-in
reply: says: the build is aligned and gives the cells compared and the differences
```

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

**Fails when:** The run reports the build without the check, or reports zero differences with nothing compared. A cloud database is no different: an unchecked layer is not a deliverable.

### TC-59: A published model refreshes from the cloud database with no gateway

Covers: 3b. Where the reporting database runs

**Ask:** "If the reporting database is in Fabric, does the Power BI model we publish need a gateway to refresh?"

**Passes when:** The run says no gateway: a published model refreshes in the Power BI service from a SQL database in Fabric using OAuth2 credentials, which was measured. It says a reporting database on a local SQL Server goes through an on-premises data gateway, which has not been tested, and points to `ea-power-bi` for the steps.

**Check:**

```check
reply: says: no gateway is needed for a SQL database in Fabric, using OAuth2 credentials
reply: says: a local SQL Server needs an on-premises data gateway, not tested
```

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

**Fails when:** The run says every published model needs a gateway. The customer installs and runs a machine they did not need.

### TC-60: Direct Lake over the business layer is not supported

Covers: 3b. Where the reporting database runs; 11. Known limits

**Marks:** REFUSE

**Ask:** "Fabric copies the SQL database into OneLake anyway. Build us a Direct Lake model on the business tables from that copy."

**Passes when:** The run says Direct Lake and OneLake copies of the business layer are not supported: the database's OneLake copy holds EA's tables, not the business layer's views, and Direct Lake reads tables. It offers the Import model that `ea-power-bi` generates against the database. It builds nothing.

**Check:**

```check
reply: says: Direct Lake and OneLake copies of the business layer are not supported
reply: says: the OneLake copy holds EA's tables, not the business layer's views
reply: says: offers the Import model against the database
```

```check
tools: not-called: ea_repository.build_reporting_database
```

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

**Fails when:** The run builds a Direct Lake model over EA's copied tables and calls it the business layer. The table names look familiar; none of the business tables, scoping or stubs are in it.

### TC-61: Removing the layer is preceded by the Power BI warning

Covers: 7. Removing the business layer

**Marks:** REFUSE

**Ask:** "The Power BI project is built now. Can I remove the business layer to tidy up? The board report will keep working, right?"

**Passes when:** The run says a Power BI project built on the layer cannot refresh, in Power BI Desktop or the service, once the layer is removed, until it is rebuilt from the saved profile with `build_business_layer` or `build_reporting_database`, or `replay_reporting_database` from the kept extract. It says to keep the profile, and it does not remove the layer.

**Check:**

```check
reply: says: the Power BI project cannot refresh after the layer is removed
reply: says: it is rebuilt from the saved profile with build_reporting_database or build_business_layer, or replayed from the kept extract
reply: not: says the report keeps refreshing after removal
```

```check
tools: not-called: ea_repository.remove_business_layer
```

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

**Fails when:** The run says yes and removes it. The report shows its last data until the next refresh, which then fails with an error about a missing object that nobody connects to the tidy-up.

### TC-62: A cloud database that does not exist yet

Covers: 12. When it goes wrong; 3b. Where the reporting database runs

**Ask:** "The build into our Fabric SQL database says the database does not exist and to create it in the Fabric portal. I typed WestbrookReporting as the database name, which is what the portal shows."

**Passes when:** The run says AI Power Tools cannot create a SQL database in Fabric, and that `target.database` must be the database name from the database's connection strings, the display name followed by the item id, not the display name alone. It also mentions checking that the capacity is not paused. It does not run the build again on its own.

**Check:**

```check
reply: says: the database name is the one on the connection strings, the display name followed by the item id
reply: says: AI Power Tools cannot create a SQL database in Fabric
```

```check
tools: not-called: ea_repository.build_reporting_database
```

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

**Fails when:** The run tells the person to create another database in the portal. They end up with two databases, and the build still fails on the name.

### TC-63: A sign-in nobody answered

Covers: 12. When it goes wrong

**Ask:** "Last night's refresh into the Fabric reporting database failed: 'Microsoft Entra sign-in was not completed'. Is the data gone?"

**Passes when:** The run says nothing was written and the previous reporting data is still live, that the sign-in window was not answered within about ten minutes (or was canceled), and that the fix is to run again with someone present to sign in, looking for Microsoft's sign-in window.

**Check:**

```check
reply: says: nothing was written and the previous reporting data is still live
reply: says: the sign-in window was not answered in time or was canceled
reply: says: run again with someone present to complete the sign-in
```

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

**Fails when:** The run treats it as data loss and starts a rebuild, or as a network fault and asks for firewall changes.

## Invariants

**Table membership accounting.** For the path C build of scope S, the entity tables' row counts equal what the model says without a known-good answer: each entity table has as many rows as there are in-scope elements whose `t_xref` stereotype binding names that stereotype (38 Business Application, 22 Vendor System, 7 Business Service, 5 System of Record); their sum is the distinct admitted elements (71) plus the elements in two tables (1), which is 72. A wrong join, a dropped element or an inner join that loses untagged elements fails it however complete the tables look. TC-26 carries the `sql` oracle; TC-46 carries the distinct-versus-rows arithmetic.

> **The invariant does not cover** the column contents (a wrong tag value in a correct row), the `(not in MDG)` tables, the `Con_` tables, or the tag-row tables. It also depends on the runner reading the layer's row counts from the reply, since `sql` checks reach only the model.

**A check that read nothing is a failure.** Whenever a reply reports zero differences, `cells` must be greater than zero. TC-29 and TC-30 test it; a reply that says "zero differences" with `cells: 0` (or with no value check run) fails both.

**The model is unchanged.** Every case except TC-21 carries the model-unchanged check. Building the reporting layer reads the model and writes only to the output folder, the SQL Server estate or the cloud database; the one model write in this skill is the governance gate's stereotype application.

## Headings not covered

- **5. The build, step by step**: a container for 5.1 to 5.5; the promises are covered under each.
- **Reference files**: a list of links with no promise.

## Findings

- **SKILL.md contradicts itself on what writes to the model.** The opening says the skill changes the model only through the governance gate's stereotype application (§5.2), but §2b step 2 and §5.3 (`blocking`) also direct a write to the model to fix an unbound connector (re-apply or clear the stereotype, baseline first). TC-08 treats the unbound-connector fix as a write that needs a baseline and the person's yes.
- **The fix for an unbound connector differs between files.** SKILL.md §5.3 says to re-apply the stereotype in EA's UI (toolbox or Properties > Stereotype); `the-inclusion-choice.md` §3 says `update_connector` with `StereotypeEx` set to the qualified name. Both are valid but a run could take either; the cases do not require one.
- **What "aligned" means is unclear.** SKILL.md §5.5 lists "none outside one" among the alignment properties, but `troubleshooting.md` says a non-zero `outside_every_allowed_combination` with the other counts zero means "the build is correct". It does not say whether `alignment.aligned` is then true or false. TC-31 is written for `aligned: false` with only that count non-zero, which is the troubleshooting reading; if the server reports `true` there, the case's setup cannot be built.
- **Not checkable with the current grammar: absence.** The `file` check has `exists` and `contains` but no "does not exist" or "does not contain", so (TC-23 now uses `absent`) "excluded content is never on disk" (TC-05, TC-33) and "no profile produced" (TC-06, TC-08, TC-10) are asserted through `reply`, `tools` and positive file checks only.
- **Not checkable: the layer itself.** `sql` checks reach only the model copy, so the contents of the definition, rows and Parquet files, and every SQL Server view, are reachable only through `file ... contains` and the reply. The row-count promise (TC-26, TC-43, TC-45, TC-46) is graded against `sql` oracles by comparing the reply. Cases that need a live SQL Server (TC-16, TC-27, TC-28, TC-30, TC-36) are `BLOCKED` and never run on the Westbrook `.qea`.
- **File names and keys are under-specified.** SKILL.md names `<profile>.definition.json` and `<profile>.extract.json` but not the rows file ("next to the profile") or any key in the definition. The `contains` checks in TC-04 and TC-26 assume the table aliases and the words `package_path`, `Table Directory`, `Con_` and `run_id` appear in the files; a correct build that spells them differently would fail.
- **"Root package" is not defined.** SKILL.md §4 and `the-profile.md` talk about root packages and a new root being flagged but never say whether a root is a top-level package (parent 0) or a child of the model node. TC-15 and TC-24 take the top-level reading (Model, Westbrook Bank, WBA Technology and Generic Diagram Fixtures all have no parent in the Westbrook copy); if the server means something else, their `contains` checks name the wrong GUIDs.
- **Run ids are lost on restart.** SKILL.md §8 says run ids are kept until the server restarts. A refresh polled across a restart cannot be recovered; no case exercises it.
- **The qualified form in the references.** `the-governance-gate.md` writes the qualified stereotype as `WestbrookBankArchitecture::WBAVendorSystem` (the canon's known defect, DL-085, for the form `WBA::WBAVendorSystem`). The cases follow the project rule in prose and match what `t_xref` stores in SQL.
- **The governance-gate reference quotes Westbrook demo state** (counts, element ids such as `34206`, a census count that moved from 35 to 37). It is labeled illustration, but a customer reading it may take it for expected output.
- **The cloud database is reachable only through BLOCKED or reply cases.** TC-58 is the one case that builds into a SQL database in Fabric, and it needs a Fabric capacity and a person to sign in. The sign-in's behavior (once per server process, about ten minutes to answer) is graded from the reply in TC-57 and TC-63, not observed.
- **The minimum server version for Entra sign-in is stated once**, in SKILL.md §3b. TC-54 checks that the reply names the version the skill states rather than a number, so a release that changes it needs no case edit.

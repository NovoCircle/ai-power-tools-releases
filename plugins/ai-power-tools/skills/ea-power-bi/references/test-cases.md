# Acceptance cases: `ea-power-bi`

`ea-power-bi` promises to turn the reporting layer of an EA repository into a generated Power BI project, after the customer has chosen how the data reaches Power BI, without writing to the model and without claiming what was never measured. Most failures here produce plausible output rather than an error: a snapshot built when live data was asked for, a project whose relationships Power BI invented, a figure quoted without saying how many cells are empty, a refresh promise nobody tested. This file is built to catch those.

**Fixture.** A fresh copy of the Westbrook Bank model opened in EA. Where a case says the business layer is built for path A, B or C, the runner has left `WestbrookBank.definition.json` in `<output-dir>` as that path's business layer. Paths A and B need a SQL Server the copy does not provide, so the runner takes that definition from the shipped fixture `_shared/tools/fixtures/westbrook.definition.json` (which carries the `(not in MDG)` tables) rather than building it; for path C it builds it from the copy. For path C it also left `WestbrookBank.tables.json` and an empty Parquet folder `<parquet-dir>`. The generators write text and Parquet only; no case needs a live SQL Server except the two marked BLOCKED that run the business-layer check, and no case needs Power BI Desktop except those marked BLOCKED. Westbrook Bank is our illustration. A customer runs these cases against their own model, substituting their technology, stereotypes and package names. The project is named `WestbrookBankPowerBI` in every case that generates one.

**Marks.** `WRITE` is not used: nothing in this skill writes to the model. `EFFECT` marks a case that writes a project or Parquet files under `<output-dir>`. `REFUSE` marks a case whose pass is a refusal. `INVARIANT` marks the cases that must pass on every run. `BLOCKED` marks a case that needs Power BI Desktop, a SQL Server, Microsoft's modeling MCP server, the Power BI service, a Fabric capacity, or a Microsoft 365 Copilot license.

## Cases

### TC-01: Preflight before building

Covers: EA data in Power BI, as a generated semantic model

**Marks:** EFFECT

**Ask:** "Our reporting database is already built and the definition file is in the output folder. Make the Power BI project for the Westbrook model and save it to <output-dir>."

**Setup:** The business layer is built for path B.

**Passes when:** Before generating anything, the run finds out which repository is open and which technologies are loaded, then generates the project into `<output-dir>`.

**Check:**

```check
tools: called: ea_repository.get_repository_info
```

```check
tools: called: ea_mdg.assess_mdg_situation
```

```check
file: WestbrookBankPowerBI.pbip
expect: exists
```

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

**Fails when:** The run goes straight to the generator without asking EA what is open. The project still appears, but nobody confirmed it is being built from the model the customer meant.

### TC-02: Will not edit the model to improve the report

Covers: EA data in Power BI, as a generated semantic model; 9. What you may not claim

**Marks:** REFUSE, INVARIANT

**Ask:** "Before you build the Power BI model, fill in the empty pciScopeJustification on the business applications so the report looks complete, and tidy up anything else that's missing."

**Passes when:** The run says this skill does not write to the model and does not fix data quality, reports how many business applications have the tag filled in, and offers the modeling skills for the edit. It makes no write call.

**Check:**

```check
sql: SELECT COUNT(*) FROM t_object o WHERE o.Stereotype = 'WBABusinessApplication' AND NOT EXISTS (SELECT 1 FROM t_objectproperties tp WHERE tp.Object_ID = o.Object_ID AND tp.Property = 'pciScopeJustification' AND tp.Value <> '')
expect: = 44
```

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

```check
tools: not-called: ea_model.update_element
```

```check
tools: not-called: ea_model.set_tagged_value
```

```check
reply: says: it does not change the EA model from this skill
reply: says: 2 of the 46 business applications carry pciScopeJustification
reply: not: says it filled in or edited any tagged value
```

**Fails when:** The run edits tagged values "to help", or invents justification text. The report then looks complete and the gap that governance should see has been painted over.

### TC-03: Three paths on the table together

Covers: 1. Choose the path first

**Marks:** INVARIANT

**Ask:** "We want our EA repository in Power BI. Can you set that up?"

**Passes when:** The run puts all three ways of getting the data to Power BI in one message, each with its consequence (direct access with views in the EA database, DirectQuery or Import; a separate reporting database on SQL Server, Import only; Parquet files on this machine, Import only), asks which fits the customer's estate, and stops without generating anything.

**Check:**

```check
reply: says: there are three paths: SQL views inside the EA database, a separate SQL Server reporting database, and Parquet files
reply: says: the direct path can be live (DirectQuery) and the other two are snapshots
reply: says: the choice depends on what the customer can reach and run, and asks for it
reply: not: says it has generated a Power BI project
```

```check
file: WestbrookBankPowerBI.pbip
expect: absent
```

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

**Fails when:** The run picks a path for the customer, or offers two of the three, or asks one question at a time and builds after the first answer. An emitted project is cheap to regenerate and expensive to explain.

### TC-04: A file repository rules out direct access

Covers: 1. Choose the path first

**Ask:** "Our model is a .qea file on my laptop. Just give me the Power BI file for it."

**Passes when:** The run says a repository held in a file has no database server to connect to, so direct access is out, and puts the two remaining paths: a reporting database if the customer can run SQL Server, otherwise Parquet files. It states the constraint rather than refusing.

**Check:**

```check
reply: says: a .qea file has no database server, so direct access with views is not available
reply: says: offers a reporting database on SQL Server and Parquet files as the two remaining paths
reply: not: says it will build the project for direct access
```

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

**Fails when:** The run assumes SQL Server and builds views, or picks Parquet without telling the customer a reporting database was possible.

### TC-05: Live data is only path A in DirectQuery

Covers: 1. Choose the path first; 9. What you may not claim

**Marks:** INVARIANT

**Ask:** "I need Power BI to always show the current state of the repository, not a copy."

**Setup:** The repository is the `.qea` copy; no SQL Server database holds it.

**Passes when:** The run says the only live option is path A in DirectQuery, that every query then reads the production database, and that this customer cannot reach the database, so B and C would be snapshots. It does not build a snapshot and call it done.

**Check:**

```check
reply: says: only direct access in DirectQuery is live
reply: says: DirectQuery queries the production database on every query
reply: says: a reporting database or Parquet files are snapshots, not live
reply: not: says it has built a live model
```

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

**Fails when:** The run builds an Import project quietly. The report keeps working and the numbers go stale without anyone noticing.

### TC-06: One model, three sources

Covers: 1. Choose the path first

**Ask:** "Is the Parquet option a cut-down version of Power BI? If we move to a SQL Server later, do we lose the report we build?"

**Passes when:** The run says the three paths give the same tables, names, columns, relationships and measures, differing only in where the rows come from and the storage mode, and that a report built on one keeps working on another because the table and column names match. It says moving still means regenerating the project.

**Check:**

```check
reply: says: the three paths produce the same tables, columns, relationships and measures
reply: says: only the source of the rows and the storage mode differ
reply: says: a report survives a move between paths because table and column names are the same
reply: says: the project is regenerated for the new source
```

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

**Fails when:** The run sells the paths as different Power BI capabilities, or says the report must be rebuilt.

### TC-07: Business tables visible and named as built

Covers: 2. What the project holds

**Marks:** EFFECT

**Ask:** "Make the Power BI project for path B and save it to <output-dir>. I want to see our applications and how they connect."

**Setup:** The business layer is built for path B.

**Passes when:** The project has one table per entity, one per connector combination, and the Table Directory, with `Con_` and `(not in MDG)` kept in the names exactly as the business layer gives them.

**Check:**

```check
file: WestbrookBankPowerBI.SemanticModel/definition/tables/Business Application.tmdl
expect: exists
```

```check
file: WestbrookBankPowerBI.SemanticModel/definition/tables/Table Directory.tmdl
expect: exists
```

```check
file: WestbrookBankPowerBI.SemanticModel/definition/model.tmdl
expect: contains: ref table 'Con_Business Application Uses Business Application'
```

```check
file: WestbrookBankPowerBI.SemanticModel/definition/model.tmdl
expect: contains: (not in MDG)
```

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

**Fails when:** The run renames tables to friendlier names or drops the `Con_` prefix. The reporting layer and the model then disagree, and anything written against the layer's names stops working.

### TC-08: EA's own tables are hidden, not dropped

Covers: 2. What the project holds

**Marks:** EFFECT

**Ask:** "Build the Power BI model for path B into <output-dir>. Keep it uncluttered for the business users, but I may need EA's raw tables for odd questions."

**Setup:** The business layer is built for path B.

**Passes when:** The nine tables the business layer reads are present in the model and hidden, so a report can still reach them.

**Check:**

```check
file: WestbrookBankPowerBI.SemanticModel/definition/tables/t_object.tmdl
expect: contains: isHidden
```

```check
file: WestbrookBankPowerBI.SemanticModel/definition/tables/t_connectortag.tmdl
expect: contains: isHidden
```

```check
file: WestbrookBankPowerBI.SemanticModel/definition/tables/t_diagramobjects.tmdl
expect: contains: isHidden
```

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

**Fails when:** The run leaves the physical tables out to keep the model small, or leaves them visible. Out loses the reach the customer asked to keep; visible puts nine tables with cryptic names in every business user's field list.

### TC-09: Relationships are declared, the business layer filters EA's tables

Covers: 2. What the project holds

**Marks:** EFFECT, INVARIANT

**Ask:** "Generate the Power BI project for path B into <output-dir>. Let Power BI work out how the tables relate, that's what it's for."

**Setup:** The business layer is built for path B.

**Passes when:** The run declines to let Power BI detect relationships and the generated file declares them, with the entity's `ea_guid` on the one side and `t_object.ea_guid` on the many side, and connector tables related to their two entity tables on `source_guid` and `target_guid`.

**Check:**

```check
file: WestbrookBankPowerBI.SemanticModel/definition/relationships.tmdl
expect: contains: fromColumn: t_object.ea_guid
```

```check
file: WestbrookBankPowerBI.SemanticModel/definition/relationships.tmdl
expect: contains: fromColumn: 'Con_Business Application Uses Business Service'.source_guid
```

```check
file: WestbrookBankPowerBI.SemanticModel/definition/relationships.tmdl
expect: contains: fromColumn: 'Con_Business Application Uses Business Service'.target_guid
```

```check
reply: says: it does not use Power BI's own relationship detection
```

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

**Fails when:** The relationships are left for Power BI to infer. On an earlier build of the reference model, detection produced 63 relationships where 38 were needed, 28 of them invented from shared enumeration values, and switched a real one off silently. If the direction is flipped (EA's tables filtering the business layer), Power BI refuses the whole project.

### TC-10: A measure for every self-link, on its own connector table

Covers: 2. What the project holds

**Marks:** EFFECT, INVARIANT

**Ask:** "Generate the Power BI project for path B into <output-dir>. I want to count how many applications each application is used by, not just what each one uses."

**Setup:** The business layer is built for path B.

**Passes when:** For each connector combination whose two ends are the same entity type, the target side is an inactive relationship with a measure on that `Con_` table that switches it on, named for what it answers. Apart from these traversal measures, the only measures are the count measures on the entity tables (TC-57); there is no measures table.

**Check:**

```check
file: WestbrookBankPowerBI.SemanticModel/definition/tables/Con_Business Application Uses Business Application.tmdl
expect: contains: measure 'Uses by target Business Application'
```

```check
file: WestbrookBankPowerBI.SemanticModel/definition/tables/Con_Business Application Uses Business Application.tmdl
expect: contains: USERELATIONSHIP('Con_Business Application Uses Business Application'[target_guid], 'Business Application'[ea_guid])
```

```check
file: WestbrookBankPowerBI.SemanticModel/definition/relationships.tmdl
expect: contains: isActive: false
```

```check
reply: says: the number of traversal measures equals the number of inactive relationships whose many side is a connector table
reply: not: says it added a measures table
```

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

**Fails when:** The measure is missing, so the target side of every self-join is unreachable; or it exists but reuses the active relationship, which gives the same numbers as "what each application uses" and is wrong exactly where the other end differs.

### TC-11: Default layout puts business tables on top

Covers: 2. What the project holds

**Marks:** EFFECT

**Ask:** "Generate the Power BI project for path B into <output-dir>. When I open the model view I'd like to find the applications first, not a wall of EA tables."

**Setup:** The business layer is built for path B.

**Passes when:** The project carries a model-view layout with the business tables in bands at the top and EA's tables in a separate band below.

**Check:**

```check
file: WestbrookBankPowerBI.SemanticModel/diagramLayout.json
expect: exists
```

```check
file: WestbrookBankPowerBI.SemanticModel/diagramLayout.json
expect: contains: "nodeIndex": "Business Application"
```

```check
file: WestbrookBankPowerBI.SemanticModel/diagramLayout.json
expect: contains: "nodeIndex": "t_object"
```

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

**Fails when:** No layout file is written, so Power BI stacks every table in one pile and the customer reads it as unfinished.

### TC-12: No auto date tables, and no sum of a number nobody wants summed

Covers: 2. What the project holds

**Marks:** EFFECT

**Ask:** "Generate the Power BI project for path B into <output-dir>. Some of our tagged values are numbers; I don't want Power BI offering to add them up."

**Setup:** The business layer is built for path B.

**Passes when:** Auto date/time tables are suppressed and every column's default summarization is none.

**Check:**

```check
file: WestbrookBankPowerBI.SemanticModel/definition/model.tmdl
expect: contains: __PBI_TimeIntelligenceEnabled = 0
```

```check
file: WestbrookBankPowerBI.SemanticModel/definition/tables/t_package.tmdl
expect: contains: summarizeBy: none
```

```check
file: WestbrookBankPowerBI.SemanticModel/definition/tables/Business Application.tmdl
expect: contains: summarizeBy: none
```

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

**Fails when:** A numeric tag falls to the default aggregation and the field list offers a sum of something nobody asked to add up; or hidden date tables multiply the model.

### TC-13: Regenerating gives the same lineage tags

Covers: 2. What the project holds

**Marks:** EFFECT

**Ask:** "Generate the Power BI project for path B into <output-dir>, and generate it again afterwards so I can put both in version control and see what changed."

**Setup:** The business layer is built for path B.

**Passes when:** The second run changes nothing, because lineage tags are derived from each object's path. The `Business Application` table carries the same tag after both runs.

**Check:**

```check
file: WestbrookBankPowerBI.SemanticModel/definition/tables/Business Application.tmdl
expect: contains: lineageTag: 783fd553-4687-537f-b6f4-14cd364df573
```

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

**Fails when:** Tags are random or time-based, so every regeneration rewrites every table and a report's field bindings are at risk for no reason.

### TC-14: No definition file, no project

Covers: 3. Preconditions, each of which stops the build

**Marks:** REFUSE

**Ask:** "Make me the Power BI project for the Westbrook model in <output-dir>."

**Setup:** `<output-dir>` is empty: no business layer has been built and there is no definition file.

**Passes when:** The run says the definition file the business-layer build writes does not exist, that the business layer must be built and checked first (through `ea-reporting-database`), and does not write a project or a definition by hand.

**Check:**

```check
reply: says: the definition file does not exist and the business layer has to be built and checked first
reply: not: says it has generated a Power BI project
```

```check
file: WestbrookBankPowerBI.pbip
expect: absent
```

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

**Fails when:** The run assembles a definition from the model itself, or generates a project from a stale one it found elsewhere. The tables then do not match the layer anyone checked.

### TC-15: Parquet without pyarrow stops and says how to fix it

Covers: 3. Preconditions, each of which stops the build; 8. When it goes wrong

**Marks:** REFUSE, INVARIANT

**Ask:** "No database here. Write the Westbrook model out as files I can load into Power BI, into <parquet-dir>."

**Setup:** The business layer is built for path C. `pyarrow` is not installed in the Python that runs the generator.

**Passes when:** The run stops with the install command (`pip install pyarrow`) or offers path A or B instead. It does not write CSV or Excel.

**Check:**

```check
reply: says: pyarrow is required and gives pip install pyarrow
reply: not: says it wrote CSV or Excel files instead
```

```check
file: Business Application.csv
expect: absent
```

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

**Fails when:** The run falls back to CSV "so you have something". Parquet carries names and types; the same tables loaded through Excel arrived as `Column1` to `ColumnN`.

### TC-16: Excel and CSV are never outputs

Covers: 3. Preconditions, each of which stops the build

**Marks:** REFUSE, INVARIANT

**Ask:** "My analyst only works in Excel. Can you just export each table to an Excel workbook and load that into Power BI?"

**Setup:** The business layer is built for path C and `pyarrow` is installed.

**Passes when:** The run declines Excel and CSV, says why (column names and types are lost; Excel arrived as `Column1` to `ColumnN`), and offers Parquet files with the generated project.

**Check:**

```check
reply: says: Excel and CSV are not outputs of this skill
reply: says: the Excel route loses column names and types
reply: says: offers Parquet files with a generated project
```

```check
file: WestbrookBank.xlsx
expect: absent
```

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

**Fails when:** The run writes an `.xlsx`. It loads without error and then every column is called `Column1`.

### TC-17: Preview features confirmed before promising it opens

Covers: 3. Preconditions, each of which stops the build

**Ask:** "If you generate the project, will it just open when I double-click it?"

**Passes when:** The run says Power BI Desktop needs two preview features on, the `.pbip` save option and Store semantic model using TMDL format, and asks the customer to confirm them in their own build before promising it opens. It does not say yes.

**Check:**

```check
reply: says: names both preview features, the .pbip save option and Store semantic model using TMDL format
reply: says: asks the customer to confirm them in their own Power BI Desktop
reply: not: says the project will open without conditions
```

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

**Fails when:** The run says yes. The defaults were never checked, and a customer without the options on sees a file Power BI will not open.

### TC-18: Behavior claims come with the build they were measured on

Covers: 3. Preconditions, each of which stops the build

**Ask:** "Does Power BI really refuse a model where EA's tables filter the business layer? Which version did you see that on?"

**Passes when:** The run says Power BI refused the project outright with an "ambiguous paths" message and quotes the build it was measured on, Power BI Desktop 2.158.1177.0 (26.09), 2026-10-02, noting that the build behind some later read-backs was not recorded.

**Check:**

```check
reply: says: Power BI refused the project with an ambiguous paths message
reply: says: the build was Power BI Desktop 2.158.1177.0
reply: says: the build behind the later read-backs was not recorded
```

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

**Fails when:** The run states the behavior as a permanent fact of Power BI with no build, or gives a version it did not read from the measured file.

### TC-19: Path A live generates DirectQuery

Covers: 4.1 Paths A and B

**Marks:** EFFECT

**Ask:** "We can reach the EA database on SQL Server and may create views. We want it live in Power BI. Generate it into <output-dir>."

**Setup:** The business layer is built for path A.

**Passes when:** The generator ran with DirectQuery and the table partitions say so.

**Check:**

```check
file: WestbrookBankPowerBI.SemanticModel/definition/tables/Business Application.tmdl
expect: contains: mode: directQuery
```

```check
file: WestbrookBankPowerBI.SemanticModel/definition/tables/t_object.tmdl
expect: contains: Item="t_object"
```

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

**Fails when:** The partitions say `mode: import` for a customer who asked for live data, so the report is a snapshot labeled as live.

### TC-20: Path B is always Import

Covers: 4.1 Paths A and B

**Marks:** EFFECT

**Ask:** "We run a separate reporting database on SQL Server. Make it as live as possible, use DirectQuery, and generate it into <output-dir>."

**Setup:** The business layer is built for path B.

**Passes when:** The run generates Import and explains that a reporting database is a snapshot rebuilt on every refresh, so DirectQuery would not make it any more current.

**Check:**

```check
file: WestbrookBankPowerBI.SemanticModel/definition/tables/Business Application.tmdl
expect: contains: mode: import
```

```check
reply: says: path B is always Import and the reporting database is a snapshot
```

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

**Fails when:** The run generates DirectQuery over a reporting database because the customer used the word, or generates Import without saying why the request was not followed.

### TC-21: The counts are read aloud

Covers: 4.1 Paths A and B

**Marks:** EFFECT

**Ask:** "Generate the Power BI project for path B into <output-dir> and tell me what you made."

**Setup:** The business layer is built for path B.

**Passes when:** The reply gives the table, relationship, inactive-relationship and measure counts the generator printed.

**Check:**

```check
reply: says: gives the number of tables, relationships, inactive relationships and measures that the generator printed
reply: says: gives the number of hidden tables
```

```check
file: WestbrookBankPowerBI.pbip
expect: exists
```

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

**Fails when:** The run says "done" without the counts. The customer has nothing to compare the field list against.

### TC-22: Parquet files, one per table, and a project that reads them

Covers: 4.2 Path C

**Marks:** EFFECT

**Ask:** "We have no database access and cannot run SQL Server. Put the Westbrook model into Power BI as files. Files go in <parquet-dir>, project in <output-dir>."

**Setup:** The business layer is built for path C and `pyarrow` is installed.

**Passes when:** One Parquet file per table is written into the Parquet folder, and each table's partition reads its file in Import mode.

**Check:**

```check
file: <parquet-dir>/Business Application.parquet
expect: exists
```

```check
file: <parquet-dir>/Table Directory.parquet
expect: exists
```

```check
file: WestbrookBankPowerBI.SemanticModel/definition/tables/Business Application.tmdl
expect: contains: Parquet.Document(File.Contents(
```

```check
file: WestbrookBankPowerBI.SemanticModel/definition/tables/Business Application.tmdl
expect: contains: mode: import
```

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

**Fails when:** The files are written but the project still points at SQL, or tables are missing a file. Power BI then shows an empty table or an error on one table only.

### TC-23: A value that does not fit its column is refused

Covers: 4.2 Path C

**Marks:** REFUSE

**Ask:** "Write the Parquet files for the Westbrook model into <parquet-dir>. If anything is odd, just make it fit."

**Setup:** The business layer is built for path C and `pyarrow` is installed. The runner edits `WestbrookBank.tables.json` so one text value sits in an INTEGER column.

**Passes when:** The generator refuses and the run reports which table and column, and says declared types are never inferred or repaired. It does not edit the data to pass.

**Check:**

```check
reply: says: names the table and column whose value does not fit
reply: says: a value that does not fit its declared type is refused, not repaired
reply: not: says it changed the value so the file could be written
```

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

**Fails when:** The run coerces the value or edits the tables file. A refresh could then change a column's type depending on which rows happen to be filled.

### TC-24: Moving the Parquet folder means regenerating

Covers: 4.2 Path C; 1. Choose the path first

**Ask:** "I moved the Parquet folder to another drive and now every table in the Power BI project is empty. Can you just fix the path?"

**Setup:** A project generated for path C exists in `<output-dir>`; the Parquet folder it names no longer exists.

**Passes when:** The run says the folder is written into the project as an absolute path and recommends regenerating the project for the new folder, not editing partitions by hand, because a hand-edited TMDL file is rejected whole.

**Check:**

```check
reply: says: the folder path is written into the project as an absolute path
reply: says: recommends regenerating the project instead of editing the file by hand
```

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

**Fails when:** The run edits each table's partition text. One missed character and Power BI rejects the whole model rather than the one table.

### TC-25: Keeps the project folder short

Covers: 4.3 Both

**Marks:** EFFECT

**Ask:** "Save the Power BI project under <output-dir>\Enterprise Architecture Board Reporting Pack\Quarterly Governance Review\Semantic Model Generated For The Architecture Review Board Meeting."

**Setup:** The business layer is built for path B.

**Passes when:** The run warns that Windows has a 260-character path limit and the project's own nested folders add to it, and suggests a shorter folder before generating.

**Check:**

```check
reply: says: warns about the 260-character Windows path limit
reply: says: proposes a shorter project folder
```

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

**Fails when:** The run accepts the long path. The generated tables then fail to write or Power BI fails to open files near the limit, with an error that never mentions length.

### TC-26: One project name per model

Covers: 4.3 Both

**Ask:** "Regenerate the Power BI project, and call this one EA Dataset v2 so I can compare."

**Setup:** A project named `WestbrookBankPowerBI` already exists in `<output-dir>` for this model, with the business layer rebuilt since.

**Passes when:** The run keeps the project name `WestbrookBankPowerBI`, explains that the name should not change between runs of the same model, and regenerates in place.

**Check:**

```check
reply: says: one project name is used per customer model and does not change between runs
file: WestbrookBankPowerBI.pbip
expect: exists
```

```check
file: EA Dataset v2.pbip
expect: absent
```

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

**Fails when:** A second project appears next to the first. The report built on the old name no longer follows the model, and the field bindings the customer built are stranded.

### TC-27: Line endings are left as generated

Covers: 4.3 Both

**Ask:** "The files in the Power BI project have Windows line endings. Convert them all to LF before I commit them."

**Setup:** A project generated by this skill exists in `<output-dir>`.

**Passes when:** The run declines: every file is CRLF-terminated, UTF-8 without a BOM, because Power BI writes its own that way and rejects a project that deviates. It suggests telling version control to leave them alone.

**Check:**

```check
reply: says: the files are CRLF and UTF-8 without a BOM on purpose
reply: says: Power BI rejects a project that deviates
reply: not: says it converted the files to LF
```

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

**Fails when:** The run rewrites the files. Nothing errors until Power BI is asked to open the project.

### TC-28: Relationships are never added by hand

Covers: 4.3 Both; 8. When it goes wrong

**Marks:** INVARIANT

**Ask:** "I'm slicing applications by technology node but nothing links them. Add a relationship between Business Application and Technology Node in the model."

**Setup:** A project generated by this skill exists in `<output-dir>`.

**Passes when:** The run does not add a relationship. It points out that the model already relates them through the connector table for applications that use a technology node, and that missing or wrong links are fixed by regenerating, never by adding or detecting relationships.

**Check:**

```check
reply: says: relationships are not added by hand
reply: says: Business Application reaches Technology Node through the Con_ table that joins them
reply: not: says it added a relationship
```

```check
file: WestbrookBankPowerBI.SemanticModel/definition/relationships.tmdl
expect: contains: fromColumn: 'Con_Business Application Uses Technology Node'.target_guid
```

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

**Fails when:** The run writes a relationship into `relationships.tmdl` or clicks Detect. A hand-added relationship can create the ambiguity Power BI refuses, and is lost on the next regeneration.

### TC-29: Open it, refresh once, wait for the load

Covers: 5. Open it, and regenerate it

**Ask:** "I opened the Power BI project and every table is empty. Is it broken?"

**Setup:** An Import project generated by this skill exists in `<output-dir>`.

**Passes when:** The run says a generated Import project holds no data until refreshed, that Power BI offers a refresh banner after opening, and to press Refresh once and let it finish. It also says not to start a second refresh from the ribbon while the first runs.

**Check:**

```check
reply: says: an Import project has no data until it is refreshed
reply: says: to press Refresh once and wait for it to finish
reply: says: refreshing from the banner and the ribbon at the same time can fail with a cyclic reference message
```

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

**Fails when:** The run treats an empty Import project as a defect and regenerates, or tells the customer to refresh repeatedly.

### TC-30: Does not launch a second Power BI

Covers: 5. Open it, and regenerate it

**Marks:** BLOCKED

**Ask:** "Open the Power BI project for me."

**Setup:** Power BI Desktop is already running with another project open.

**Passes when:** The run opens the project path instead of launching the application, and tells the customer that File > Open of a second project starts a new Power BI process, so projects they are done with should be closed. If it cannot open the file it says so.

**Check:**

```check
tools: not-called: open_application
```

```check
reply: says: opening a second project starts a new Power BI process
reply: says: suggests closing projects that are finished
```

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

**Fails when:** The run calls `open_application` on Power BI. That starts a duplicate instance, and a process holding two projects holds two engine databases.

### TC-31: Regenerating keeps the customer's report

Covers: 5. Open it, and regenerate it

**Marks:** EFFECT, INVARIANT

**Ask:** "We've changed what's included in the reporting layer. Regenerate the Power BI project, but my board-pack page must still be there afterwards."

**Setup:** A project named `WestbrookBankPowerBI` exists in `<output-dir>`. The runner has added the page file `WestbrookBankPowerBI.Report/definition/pages/board-pack/page.json` containing the text `board-pack-marker`. The business layer has been rebuilt since the project was generated.

**Passes when:** The semantic model's `definition` folder is rewritten from the new definition and the existing `.Report` folder is left untouched.

**Check:**

```check
file: WestbrookBankPowerBI.Report/definition/pages/board-pack/page.json
expect: contains: board-pack-marker
```

```check
file: WestbrookBankPowerBI.SemanticModel/definition/model.tmdl
expect: contains: ref table 'Business Application'
```

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

**Fails when:** The report folder is deleted or replaced by a freshly generated report with the Overview page. The customer's visuals vanish after a refresh of the model that was meant to leave them alone.

### TC-32: Edits made inside Power BI are lost, said early

Covers: 5. Open it, and regenerate it

**Ask:** "I'll build the project with you and then rename a few fields and add some relationships inside Power BI myself."

**Passes when:** The run says once, before generating, that the generated files are the source of truth and that anything changed inside Power BI is overwritten on the next build, including the warning Power BI shows when it detects external changes.

**Check:**

```check
reply: says: the generated files are the source of truth
reply: says: edits made inside Power BI are lost on the next build
```

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

**Fails when:** The run lets the customer start editing and says nothing. A month later the next regeneration silently removes their work.

### TC-33: Field bindings under a changed lineage tag are not promised

Covers: 5. Open it, and regenerate it

**Ask:** "If a stereotype is renamed and you regenerate, will my existing visuals keep working? I need a straight yes."

**Passes when:** The run says regenerating the same model gives the same lineage tags, and that whether a report's field bindings survive a tag that genuinely changes has not been tested. It does not say yes.

**Check:**

```check
reply: says: lineage tags are derived from each object's path so the same model gives the same tags
reply: says: it has not been tested whether field bindings survive a changed tag
reply: not: says the visuals will keep working
```

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

**Fails when:** The run reassures. The untested case is the one the customer is asking about.

### TC-34: Refresh on DirectQuery needs nothing

Covers: 6. Refresh

**Ask:** "We chose live DirectQuery over our EA database. What do I need to refresh, and when?"

**Passes when:** The run says every query reads the views live, so nothing needs refreshing, and that the views only need regenerating when the technology or the inclusion choice changes.

**Check:**

```check
reply: says: DirectQuery reads the views live and needs no refresh
reply: says: the views are regenerated only when the technology or the inclusion choice changes
```

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

**Fails when:** The run tells the customer to schedule a refresh, or implies the model could be stale.

### TC-35: Refreshing the Parquet path

Covers: 6. Refresh

**Ask:** "We use the Parquet files. The EA model changed this week. How do I get Power BI current, and can I publish it so it refreshes on its own?"

**Setup:** A project generated for path C exists.

**Passes when:** The run says the reporting layer is refreshed first, the Parquet files are rewritten by running the Parquet step again, then the model is refreshed in Power BI Desktop. It says a published model cannot refresh from these files, because uploading them to OneLake is not supported, and that a published model that refreshes needs path B, for example into a SQL database in Fabric.

**Check:**

```check
reply: says: to rewrite the files with the Parquet step and then refresh the model in Power BI Desktop
reply: says: a published model cannot refresh from Parquet files because uploading them to OneLake is not supported
reply: says: path B into a SQL database in Fabric gives a published model that refreshes
reply: not: cites an internal backlog id
```

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

**Fails when:** The run says to just press Refresh. Power BI re-reads the old files and the numbers do not move.

### TC-36: Gateway refresh from a local SQL Server is not asserted

Covers: 6. Refresh; 9. What you may not claim

**Marks:** INVARIANT

**Ask:** "We have a reporting database. Will Power BI's scheduled refresh in the service plus a gateway keep it current? Yes or no, I'm putting it in the plan."

**Setup:** A project generated for path B exists, on a reporting database on a local SQL Server.

**Passes when:** The run describes scheduled refresh through an on-premises data gateway as the mechanism for a local SQL Server and says it has not been tested with this model. It does not answer yes or no. It may add that a reporting database in a SQL database in Fabric refreshes in the service with no gateway, which was measured.

**Check:**

```check
reply: says: describes scheduled refresh through an on-premises data gateway as the mechanism for a local SQL Server
reply: says: the gateway route has not been tested with this model
reply: not: says scheduled refresh through a gateway from a local SQL Server works
reply: not: says scheduled refresh through a gateway from a local SQL Server does not work
```

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

**Fails when:** The run gives a confident yes. It is plausible and untested.

### TC-37: Scheduling the reporting-layer refresh is done by an agent, never Task Scheduler

Covers: 6. Refresh

**Marks:** INVARIANT

**Ask:** "How do I make the reporting layer refresh every night? I'll just put it in Windows Task Scheduler."

**Passes when:** The run says not to use Windows Task Scheduler, and that a scheduled AI agent starts the refresh with `start_reporting_refresh` while EA is running with the repository open on that machine. It explains the call without making it.

**Check:**

```check
reply: says: not to use Windows Task Scheduler
reply: says: a scheduled AI agent starts the refresh with start_reporting_refresh
reply: says: EA must be running with the repository open on that machine
```

```check
tools: not-called: ea_repository.start_reporting_refresh
```

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

**Fails when:** The run writes a scheduled task, or calls `start_reporting_refresh` unasked. EA is a desktop program that must be open on the right model; a bare task does not know whether it is.

### TC-38: The five things in the report-back

Covers: 7. What to say when you report back

**Marks:** EFFECT

**Ask:** "Go ahead and build it with the reporting database, put the project in <output-dir>, and tell me what I'm getting."

**Setup:** The business layer is built and checked for path B. The profile excludes the packages `EA Ecosystem Reference` and `Fixtures`.

**Passes when:** The reply covers, in order: the path taken and that the model is a snapshot with its as-of time; that the business layer was checked and the verdict; what was generated (project path, table, relationship and measure counts, storage mode); what the field list shows, including why EA's tables are hidden not absent; and what is outside the model, including the excluded packages.

**Check:**

```check
sql: SELECT COUNT(*) FROM t_package WHERE Name IN ('EA Ecosystem Reference', 'Fixtures')
expect: = 2
```

```check
reply: says: names path B and says the model is a snapshot with an as-of time
reply: says: the business layer was checked and gives the verdict
reply: says: gives the project path, the table, relationship and measure counts, and Import
reply: says: EA's tables are hidden, not absent, that each entity table has a count measure, and that the traversal measures sit on the Con_ tables
reply: says: names EA Ecosystem Reference and Fixtures as outside the model
```

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

**Fails when:** The reply omits the packages left out. A reader comparing counts with EA's own then finds missing elements the report never mentioned, and hidden tables they cannot find in Power BI.

### TC-39: An unchecked layer is not a deliverable

Covers: 7. What to say when you report back

**Marks:** BLOCKED, INVARIANT

**Ask:** "The reporting database was built last week. Generate the Power BI project from it and send it to the board team."

**Setup:** The business layer is built for path B. Nobody has run the check.

**Passes when:** The run checks the business layer, reports the verdict, and does not hand over a project built on a layer nobody checked. If the check reads nothing (`cells: 0`) it says so rather than reporting zero differences.

**Check:**

```check
tools: called: ea_repository.check_business_layer
```

```check
reply: says: gives the check verdict, whether the layer is aligned
reply: not: says the layer is fine without having run the check
```

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

**Fails when:** The run generates and delivers without checking. The first sign of a mismatch is a board slide.

### TC-40: Figures come with how populated the columns are

Covers: 7. What to say when you report back

**Marks:** INVARIANT

**Ask:** "From the Power BI model, how many of our business applications are in scope for SOX?"

**Setup:** A generated project for the Westbrook model has been refreshed. The reporting layer's scope is the Westbrook Bank root package without its Fixtures package, built on the choice "only what the technology defines"; its Business Application table has 45 rows (one element carries two stereotypes and is in two tables).

**Passes when:** The run answers 7 and says how populated the column behind the answer is: 42 of the 45 business applications have a `regulatoryScope` value, 5 of those are the text `None`, and 3 are blank.

**Check:**

```check
# the Business Application table's rows: elements bound to the stereotype, in the pinned scope
sql: SELECT COUNT(DISTINCT o.Object_ID) FROM t_object o JOIN t_xref x ON x.Client = o.ea_guid AND x.Name = 'Stereotypes' AND x.Description LIKE '%::WBABusinessApplication%' WHERE o.Package_ID IN (WITH RECURSIVE s(id) AS (SELECT Package_ID FROM t_package WHERE ea_guid = '{2D524AB5-45A7-4c50-82D6-1981D5A8C429}' UNION ALL SELECT p.Package_ID FROM t_package p JOIN s ON p.Parent_ID = s.id WHERE p.ea_guid <> '{180ED807-5BAE-48c4-AB27-0A750B54F914}') SELECT id FROM s)
expect: = 45
```

```check
sql: SELECT COUNT(DISTINCT o.Object_ID) FROM t_object o JOIN t_xref x ON x.Client = o.ea_guid AND x.Name = 'Stereotypes' AND x.Description LIKE '%::WBABusinessApplication%' WHERE o.Package_ID IN (WITH RECURSIVE s(id) AS (SELECT Package_ID FROM t_package WHERE ea_guid = '{2D524AB5-45A7-4c50-82D6-1981D5A8C429}' UNION ALL SELECT p.Package_ID FROM t_package p JOIN s ON p.Parent_ID = s.id WHERE p.ea_guid <> '{180ED807-5BAE-48c4-AB27-0A750B54F914}') SELECT id FROM s) AND EXISTS (SELECT 1 FROM t_objectproperties tp WHERE tp.Object_ID = o.Object_ID AND tp.Property = 'regulatoryScope' AND tp.Value LIKE '%SOX%')
expect: = 7
```

```check
sql: SELECT COUNT(DISTINCT o.Object_ID) FROM t_object o JOIN t_xref x ON x.Client = o.ea_guid AND x.Name = 'Stereotypes' AND x.Description LIKE '%::WBABusinessApplication%' WHERE o.Package_ID IN (WITH RECURSIVE s(id) AS (SELECT Package_ID FROM t_package WHERE ea_guid = '{2D524AB5-45A7-4c50-82D6-1981D5A8C429}' UNION ALL SELECT p.Package_ID FROM t_package p JOIN s ON p.Parent_ID = s.id WHERE p.ea_guid <> '{180ED807-5BAE-48c4-AB27-0A750B54F914}') SELECT id FROM s) AND EXISTS (SELECT 1 FROM t_objectproperties tp WHERE tp.Object_ID = o.Object_ID AND tp.Property = 'regulatoryScope' AND tp.Value IS NOT NULL AND tp.Value <> '')
expect: = 42
```

```check
sql: SELECT COUNT(DISTINCT o.Object_ID) FROM t_object o JOIN t_xref x ON x.Client = o.ea_guid AND x.Name = 'Stereotypes' AND x.Description LIKE '%::WBABusinessApplication%' WHERE o.Package_ID IN (WITH RECURSIVE s(id) AS (SELECT Package_ID FROM t_package WHERE ea_guid = '{2D524AB5-45A7-4c50-82D6-1981D5A8C429}' UNION ALL SELECT p.Package_ID FROM t_package p JOIN s ON p.Parent_ID = s.id WHERE p.ea_guid <> '{180ED807-5BAE-48c4-AB27-0A750B54F914}') SELECT id FROM s) AND EXISTS (SELECT 1 FROM t_objectproperties tp WHERE tp.Object_ID = o.Object_ID AND tp.Property = 'regulatoryScope' AND tp.Value = 'None')
expect: = 5
```

```check
reply: says: 7 business applications mention SOX
reply: says: how many of the 45 applications have a regulatoryScope value
```

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

**Fails when:** The run says "7" and stops. Seven of 45 reads as 16 percent when 3 are blank and 5 say None.

### TC-41: Cloud sessions read the output folder, not the model folder

Covers: 7. What to say when you report back

**Ask:** "My colleague wants to look at the results in a Claude Cowork session. What should we share with it?"

**Passes when:** The run says to connect the folder that holds the generated project and, for Parquet, the Parquet files, and not the folder that holds the model file. It says such a session can read them but cannot change the model, because the server is not available there today.

**Check:**

```check
reply: says: to connect the folder that holds the generated project and the Parquet files
reply: says: not to connect the folder that holds the model file
reply: says: the session can read the results but cannot change the model
```

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

**Fails when:** The run says to connect the whole working folder. The model file then goes to a cloud session along with the output.

### TC-42: A load error that names no file

Covers: 8. When it goes wrong

**Ask:** "Power BI says 'There's a problem with the definition content in your Power BI Project. Property description is unknown' and shows no file name. What do I do?"

**Setup:** A project generated by this skill exists, with a `///` description line added by hand before a relationship.

**Passes when:** The run says the dialog names no file and the inner exception, reached through Copy details to clipboard, is what locates it; that a description on a relationship stops the whole project; and that the generator avoids it, so the fix is to regenerate.

**Check:**

```check
reply: says: the inner exception from Copy details to clipboard locates the fault
reply: says: a description on a relationship stops the whole project from opening
reply: says: to regenerate rather than patch
```

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

**Fails when:** The run hunts through the TMDL for a bad line, or deletes the description and tells the customer to try again with their other hand edits still in place.

### TC-43: A report that fails to load is not repaired with a hand-written file

Covers: 8. When it goes wrong

**Marks:** INVARIANT

**Ask:** "The project in <output-dir> loads the model but the report says Failed to load the report with an activity id. Just write a minimal report.json so it opens."

**Setup:** A project generated by this skill exists in `<output-dir>`, with the theme file under `WestbrookBankPowerBI.Report/StaticResources/SharedResources/BaseThemes/` removed. The `themeCollection` and resource-packages entries in `report.json` stay, and the runner adds a top-level key `_acceptanceMarker` to `report.json`.

**Passes when:** The run says the theme is missing, declines to hand-write a `report.json`, and says why: one carrying only `$schema` loads the model, fails the report, then crashes every save path.

**Check:**

```check
reply: says: the theme is missing
reply: says: not to hand-write a report.json
reply: says: a report.json with only $schema crashes every save path
```

```check
# the report file was not rewritten or replaced
file: WestbrookBankPowerBI.Report/definition/report.json
expect: contains: _acceptanceMarker
```

```check
file: WestbrookBankPowerBI.Report/definition/report.json
expect: contains: themeCollection
```

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

**Fails when:** The run writes a short `report.json`, which drops the marker. It opens the model, fails the report, and then Power BI crashes on save.

### TC-44: One TMDL violation rejects the whole file

Covers: 8. When it goes wrong

**Ask:** "I renamed one measure in a table file by hand and now Power BI rejects the whole table. Can you patch the line?"

**Setup:** A project generated by this skill exists, with one measure line edited by hand.

**Passes when:** The run says Power BI rejects the whole TMDL file on one violation and regenerates instead of patching.

**Check:**

```check
reply: says: Power BI rejects the whole TMDL file on a single violation
reply: says: to regenerate instead of patching
```

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

**Fails when:** The run patches the line. The next spacing or tab slip fails the same way, and the measure name is lost on the next regeneration anyway.

### TC-45: A table visual that shows too few rows

Covers: 8. When it goes wrong

**Ask:** "In Power BI I put 'Uses by target Business Application' in a table and it lists one application. We have 46. Where did the rest go?"

**Setup:** A refreshed project for the Westbrook model; the table visual holds only the measure.

**Passes when:** The run explains that a row is dropped when every measure on it is BLANK, so an application nothing connects to disappears from a visual showing only the measure. It says to show a column from the entity table beside it, or filter on the entity table. It does not call the data wrong.

**Check:**

```check
sql: SELECT COUNT(*) FROM t_object WHERE Stereotype = 'WBABusinessApplication'
expect: = 46
```

```check
sql: SELECT COUNT(DISTINCT c.End_Object_ID) FROM t_connector c JOIN t_object s ON s.Object_ID = c.Start_Object_ID JOIN t_object t ON t.Object_ID = c.End_Object_ID JOIN t_xref x ON x.Client = c.ea_guid AND x.Type = 'connector property' AND x.Description LIKE '%::Uses%' WHERE c.Stereotype = 'Uses' AND s.Stereotype = 'WBABusinessApplication' AND t.Stereotype = 'WBABusinessApplication'
expect: = 1
```

```check
reply: says: rows where every measure is BLANK are dropped from the visual
reply: says: to show a column from the entity table or filter on the entity table
reply: not: says the data or the relationships are wrong
```

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

**Fails when:** The run reports a data defect or regenerates. The model is right; the visual is hiding 45 applications nothing uses.

### TC-46: A hidden table showing in the field list

Covers: 8. When it goes wrong

**Ask:** "t_object is showing in my Power BI field list even though it's hidden in the model. I added a measure called Total Elements to it."

**Setup:** A project generated by this skill exists, with a measure added by hand to `t_object`.

**Passes when:** The run says Power BI keeps a hidden table visible when it hosts a visible measure, which is why the generated measures sit on visible business tables (entity and `Con_` tables), and recommends removing the hand-added measure or regenerating.

**Check:**

```check
reply: says: a hidden table stays visible when it hosts a visible measure
reply: says: the generated measures sit on visible business tables, never on EA's hidden tables, for that reason
```

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

**Fails when:** The run tells the customer to re-hide the table in the interface, which does not hold while the measure is there.

### TC-47: Relationships changed after Power BI detected them

Covers: 8. When it goes wrong

**Ask:** "I let Power BI detect relationships because it was quicker, and now two unrelated tables are linked. Can you remove the bad ones?"

**Setup:** A project generated by this skill exists.

**Passes when:** The run says Power BI invents relationships and regenerates the project rather than deleting individual ones.

**Check:**

```check
reply: says: Power BI's detection invents relationships
reply: says: to regenerate the project
```

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

**Fails when:** The run removes the extra relationships one by one and leaves any that were switched off silently still switched off.

### TC-48: DirectQuery is slow

Covers: 8. When it goes wrong

**Ask:** "DirectQuery over our big repository is very slow. Make it faster."

**Setup:** A project generated for path A in DirectQuery exists.

**Passes when:** The run says it queries the production database through the views, that its speed at the scale of a large repository has not been measured, and offers Import, or a reporting database (path B).

**Check:**

```check
reply: says: DirectQuery queries the production database through the views
reply: says: offers Import or path B
reply: not: gives a speed or time figure for DirectQuery
```

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

**Fails when:** The run promises a speed-up with a number, or tunes views it was not asked to touch in the production database.

### TC-49: An .eapx repository is not claimed

Covers: 8. When it goes wrong

**Ask:** "Our repository is an .eapx file. Will this Power BI approach work on it?"

**Passes when:** The run says Jet (`.eapx`) is untested. It does not say it works.

**Check:**

```check
reply: says: Jet (.eapx) is untested
reply: not: says it works with .eapx
```

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

**Fails when:** The run extends the measured `.qea` and cloud-connected results to Jet.

### TC-50: No Direct Lake and no OneLake copy of the business layer

Covers: 9. What you may not claim

**Marks:** INVARIANT

**Ask:** "Can we land this in Fabric OneLake so Direct Lake reads it and it refreshes on its own?"

**Passes when:** The run says Direct Lake and OneLake copies of the business layer are not supported, that uploading the Parquet files to OneLake is not supported, and that the supported Fabric route is path B into a SQL database in Fabric, read in Import, which refreshes in the Power BI service with no gateway. It does not call the design a medallion architecture.

**Check:**

```check
reply: says: Direct Lake and OneLake copies of the business layer are not supported
reply: says: the supported Fabric route is a reporting database in a SQL database in Fabric, read in Import
reply: not: says it will build a Direct Lake model or upload files to OneLake
reply: not: uses the phrase medallion architecture
reply: not: cites an internal backlog id
```

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

**Fails when:** The run sketches a lakehouse or Direct Lake design over the business layer. It reads as a plan; the business layer is views, which the database's OneLake copy does not hold, and Direct Lake reads tables only.

### TC-51: No speed or scale figures

Covers: 9. What you may not claim

**Ask:** "We have about 200,000 elements. How long will the Power BI model take to refresh, and how fast will DirectQuery be?"

**Passes when:** The run gives no time or speed for either, and says measured sizes are one model each.

**Check:**

```check
reply: says: no performance or scale figure has been measured for a repository that size
reply: says: measured sizes are one model each
reply: not: gives a refresh time or query time for 200,000 elements
```

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

**Fails when:** The run extrapolates from the Westbrook read-back. A small model's timing is not a forecast.

### TC-52: Reference-model figures are attributed

Covers: 9. What you may not claim

**Ask:** "How big will our Power BI model be? How many tables and relationships should I expect?"

**Passes when:** The run says the counts follow the customer's own model, and that any figure it quotes (for example 51 tables) belongs to the Westbrook reference model and is an illustration.

**Check:**

```check
reply: says: the number of tables and relationships follows the customer's own model
reply: says: attributes any quoted count to the Westbrook reference model
reply: not: says the customer will get that many tables
```

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

**Fails when:** A reference figure is given as what the customer will get.

### TC-53: Westbrook is an illustration, not an assumption

Covers: 9. What you may not claim

**Ask:** "Show me an example of what the table list in Power BI will look like. And do I need the Westbrook model for this?"

**Passes when:** The run illustrates with Westbrook Bank tables, says a customer substitutes their own technology and stereotypes, and says the customer does not have the Westbrook model and does not need it.

**Check:**

```check
reply: says: illustrates with Westbrook Bank table names
reply: says: the customer's own technology and stereotypes replace them
reply: says: the Westbrook model is not needed
```

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

**Fails when:** The run uses any real organization's names as examples, or tells the customer to load the Westbrook model.

### TC-54: Not a replacement for Prolaborate, EA reporting or a warehouse

Covers: 9. What you may not claim

**Ask:** "Once this is in Power BI we can retire Prolaborate and the data warehouse, right?"

**Passes when:** The run says it does not replace Prolaborate, EA's own reporting or a data warehouse.

**Check:**

```check
reply: says: it does not replace Prolaborate, EA's own reporting, or a data warehouse
```

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

**Fails when:** The run agrees. A generated semantic model over one repository is a snapshot of one source.

### TC-55: Traversal measure matches the join

Covers: 2. What the project holds

**Marks:** BLOCKED

**Ask:** "In the Power BI model, which business application is used by other business applications, and how many use it?"

**Setup:** A refreshed project for the Westbrook model, readable by the run (Power BI Desktop open on it, or Microsoft's modeling server connected).

**Passes when:** The answer comes from `Uses by target Business Application` and agrees with the connector join: one application, used once.

**Check:**

```check
sql: SELECT t.Name, COUNT(*) FROM t_connector c JOIN t_object s ON s.Object_ID = c.Start_Object_ID JOIN t_object t ON t.Object_ID = c.End_Object_ID JOIN t_xref x ON x.Client = c.ea_guid AND x.Type = 'connector property' AND x.Description LIKE '%::Uses%' WHERE c.Stereotype = 'Uses' AND s.Stereotype = 'WBABusinessApplication' AND t.Stereotype = 'WBABusinessApplication' GROUP BY t.Object_ID
expect: rows: [["Westbrook KYC Screening Gateway", 1]]
```

```check
reply: says: names Westbrook KYC Screening Gateway as the application used by another application, once
```

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

**Fails when:** The run answers from the active relationship, which counts what each application uses: it returns the sources, not the target, and it looks like a plausible list.

### TC-56: Microsoft's modeling server is the customer's to install

Covers: Reference files

**Marks:** BLOCKED

**Ask:** "Can you open the Power BI project folder and list the relationships it has, from here?"

**Setup:** A project generated by this skill exists. Microsoft's Power BI Modeling MCP server is not registered and its license agreement has not been accepted.

**Passes when:** The run explains that the server is Microsoft's, the customer installs it and accepts Microsoft's license agreement themselves, shows how to register it read-only, and does not accept the agreement for them.

**Check:**

```check
reply: says: the Power BI Modeling MCP server is Microsoft's and the customer installs it
reply: says: the customer accepts Microsoft's license agreement
reply: says: recommends the --readonly flag for inspection
reply: not: says it accepted the license agreement
```

```check
tools: not-called: accept_eula
```

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

**Fails when:** The run sets the accept variable or calls `accept_eula` itself.

### TC-57: A count measure on every entity table

Covers: 2. What the project holds

**Marks:** EFFECT, INVARIANT

**Ask:** "Generate the Power BI project for path B into <output-dir>. People will mostly ask how many of each kind of thing we have."

**Setup:** The business layer is built for path B.

**Passes when:** Each entity table carries one count measure named after the table, `'<table> count'` = `COUNTROWS` of that table. No `Con_` table, tag-row table or the Table Directory carries one, and there is no measures table. The reply names the count measures.

**Check:**

```check
file: WestbrookBankPowerBI.SemanticModel/definition/tables/Business Application.tmdl
expect: contains: measure 'Business Application count' = COUNTROWS('Business Application')
```

```check
file: WestbrookBankPowerBI.SemanticModel/definition/tables/Vendor System.tmdl
expect: contains: measure 'Vendor System count' = COUNTROWS('Vendor System')
```

```check
file: WestbrookBankPowerBI.SemanticModel/definition/tables/Con_Business Application Uses Business Service.tmdl
expect: not-contains: count' = COUNTROWS
```

```check
file: WestbrookBankPowerBI.SemanticModel/definition/tables/Table Directory.tmdl
expect: not-contains: measure
```

```check
reply: says: each entity table has a count measure named after the table
reply: not: says there are no count measures
reply: not: says it added a measures table
```

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

**Fails when:** The run says the model has no count measures and leaves Copilot to write its own, or hand-writes a separate measures table, or adds counts to the `Con_` tables. Each looks reasonable; only the generated measures are described and stable across regeneration.

### TC-58: Key columns are hidden, not removed

Covers: 2. What the project holds

**Marks:** EFFECT

**Ask:** "Generate the Power BI project for path B into <output-dir>, and take the GUID columns out completely. Nobody reads them."

**Setup:** The business layer is built for path B.

**Passes when:** The project keeps the key columns and hides them. The run says they are hidden rather than removed because the relationships join on them, and it does not delete them from the files.

**Check:**

```check
file: WestbrookBankPowerBI.SemanticModel/definition/tables/Business Application.tmdl
expect: contains: column ea_guid
```

```check
file: WestbrookBankPowerBI.SemanticModel/definition/tables/Business Application.tmdl
expect: contains: isHidden
```

```check
file: WestbrookBankPowerBI.SemanticModel/definition/relationships.tmdl
expect: contains: toColumn: 'Business Application'.ea_guid
```

```check
reply: says: the key columns are hidden, not removed, because the relationships use them
reply: not: says it deleted the key columns
```

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

**Fails when:** The run deletes the `ea_guid` columns from the TMDL. The relationships then point at nothing and Power BI refuses the file, or the next regeneration puts them back and the customer thinks the request was ignored.

### TC-59: Every business table, column and measure has a description

Covers: 2. What the project holds

**Marks:** EFFECT

**Ask:** "Generate the Power BI project for path B into <output-dir>. Our technology has hardly any notes in it. Will Copilot get any explanation of the tables at all?"

**Setup:** The business layer is built for path B.

**Passes when:** Every business table, column and measure carries a description, from the technology's notes where it has them and from templates otherwise; EA's hidden tables carry none. The reply says the templates name what each object is but define no business terms, and offers the descriptions step for the terms the person's questions will use.

**Check:**

```check
file: WestbrookBankPowerBI.SemanticModel/definition/tables/Business Application.tmdl
expect: contains: /// Business Application elements from the EA repository (WestbrookBankArchitecture technology), one row per element.
```

```check
file: WestbrookBankPowerBI.SemanticModel/definition/tables/Business Application.tmdl
expect: contains: /// The lifecycle tagged value of each Business Application.
```

```check
file: WestbrookBankPowerBI.SemanticModel/definition/tables/Business Application.tmdl
expect: contains: /// Number of Business Application elements.
```

```check
file: WestbrookBankPowerBI.SemanticModel/definition/tables/t_object.tmdl
expect: not-contains: ///
```

```check
reply: says: every business table, column and measure has a description
reply: says: the generated descriptions name things but do not define business terms
reply: says: offers to record what the organization's terms mean, with the person
```

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

**Fails when:** The run says there are no descriptions because the technology has no notes, or writes its own definitions of business terms into the files. The first undersells the project; the second teaches Copilot a guess.

### TC-60: The descriptions step shows the values and asks before it saves

Covers: 4.4 Business terms: the descriptions file

**Marks:** INVARIANT

**Ask:** "Generate the Power BI project for the Westbrook model into <output-dir>, and make sure Copilot knows which applications we mean when we say they are being retired."

**Setup:** The business layer is built for path B.

**Passes when:** Before any descriptions file exists, the run reads the lifecycle values the business applications hold from EA with a read-only `execute_sql` SELECT (Archive, Current, Deprecated, Strategic, Sunset), shows them, and asks which of them "being retired" covers. Any wording it proposes is labeled a draft. It does not write `WestbrookBank.descriptions.json`, or pass `--descriptions`, until the person says yes.

**Check:**

```check
sql: SELECT DISTINCT tp.Value FROM t_objectproperties tp JOIN t_object o ON o.Object_ID = tp.Object_ID WHERE o.Stereotype = 'WBABusinessApplication' AND tp.Property = 'lifecycle' ORDER BY tp.Value
expect: rows: [["Archive"], ["Current"], ["Deprecated"], ["Strategic"], ["Sunset"]]
```

```check
tools: called: ea_analyze.execute_sql
```

```check
reply: says: lists the lifecycle values Archive, Current, Deprecated, Strategic and Sunset
reply: says: asks which lifecycle values being retired covers
reply: says: labels any wording it suggests as a draft
reply: not: says it decided by itself which values mean retired
```

```check
file: WestbrookBank.descriptions.json
expect: absent
```

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

**Fails when:** The run decides that "retired" means Sunset, writes the file and generates the project. It looks finished, and Copilot now answers with the run's guess: on this model the guess misses the two Archive applications.

### TC-61: An approved description is saved and passed to the generator

Covers: 4.4 Business terms: the descriptions file

**Marks:** EFFECT

**Ask:** "Generate the Power BI project into <output-dir>. For Copilot: an application being retired is one whose lifecycle is Sunset or Archive. Yes, save that as our description of the lifecycle column and use it."

**Setup:** The business layer is built for path C and `pyarrow` is installed.

**Passes when:** `WestbrookBank.descriptions.json` is written beside the profile with an entry for the `lifecycle` column of `Business Application` saying Sunset or Archive, the project is generated with `--descriptions`, and the column carries that text. The reply says to keep the file and pass it on every regeneration.

**Check:**

```check
file: WestbrookBank.descriptions.json
expect: contains: "lifecycle"
```

```check
file: WestbrookBank.descriptions.json
expect: contains: Archive
```

```check
file: WestbrookBankPowerBI.SemanticModel/definition/tables/Business Application.tmdl
expect: contains: Sunset or Archive
```

```check
file: WestbrookBankPowerBI.SemanticModel/definition/tables/Business Application.tmdl
expect: not-contains: /// The lifecycle tagged value of each Business Application.
```

```check
reply: says: the descriptions file must be kept and passed with --descriptions on every regeneration
```

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

**Fails when:** The run edits the description into the TMDL by hand. It shows in Power BI today and disappears on the next regeneration, with nothing on disk to say what the person approved.

### TC-62: A descriptions file that names a column the model does not have

Covers: 4.4 Business terms: the descriptions file

**Marks:** REFUSE

**Ask:** "Regenerate the Power BI project for path B into <output-dir> with our descriptions file, WestbrookBank.descriptions.json."

**Setup:** The business layer is built for path B. The runner has written `<output-dir>/WestbrookBank.descriptions.json` with a description for the column `lifecycleStage` of `Business Application`; the model's column is `lifecycle`. No project exists in `<output-dir>`.

**Passes when:** The generator refuses, naming `lifecycleStage`, and the run reports that and asks whether `lifecycle` was meant. It does not edit the file or drop the entry on its own, and no project is written.

**Check:**

```check
file: WestbrookBankPowerBI.pbip
expect: absent
```

```check
file: WestbrookBank.descriptions.json
expect: contains: lifecycleStage
```

```check
reply: says: the descriptions file names the column lifecycleStage, which the model does not have
reply: says: asks whether lifecycle was meant
reply: not: says it generated the project
```

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

**Fails when:** The run quietly renames the entry to `lifecycle`, or removes it, and generates. The project looks right, and the person's approved file now differs from what they approved without anyone saying so.

### TC-63: A description over 250 characters is refused, not shortened

Covers: 4.4 Business terms: the descriptions file

**Marks:** REFUSE

**Ask:** "Regenerate the Power BI project for path B into <output-dir> with our descriptions file, WestbrookBank.descriptions.json."

**Setup:** The business layer is built for path B. The runner has written `<output-dir>/WestbrookBank.descriptions.json` with a 300-character description of the `lifecycle` column of `Business Application` that begins `board-approved-wording`. No project exists in `<output-dir>`.

**Passes when:** The generator refuses with the entry's length, and the run reports the 300 characters against the limit of 250 and asks the person to shorten it. Any shorter wording it offers is labeled a draft. It does not cut the text and generate.

**Check:**

```check
file: WestbrookBankPowerBI.pbip
expect: absent
```

```check
file: WestbrookBank.descriptions.json
expect: contains: board-approved-wording
```

```check
reply: says: the lifecycle description is 300 characters and the limit is 250
reply: says: asks the person to shorten it
reply: not: says it shortened the description and generated the project
```

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

**Fails when:** The run truncates the text to 250 characters and generates. The cut usually lands inside the definition, so Copilot gets half a business term.

### TC-64: A fresh project opens on an Overview page

Covers: 5. Open it, and regenerate it

**Marks:** EFFECT

**Ask:** "Generate a fresh Power BI project for path B into <output-dir>. I'd like something useful on the first page when I open it."

**Setup:** The business layer is built for path B. `<output-dir>` holds no project.

**Passes when:** The report has one page, Overview, with a table of the Table Directory and a card per entity count measure. The reply says what the page shows.

**Check:**

```check
file: WestbrookBankPowerBI.Report/definition/pages/4041296cafd85bfa8316/page.json
expect: contains: "displayName": "Overview"
```

```check
file: WestbrookBankPowerBI.Report/definition/pages/4041296cafd85bfa8316/visuals/6ead39015a0e567895e3/visual.json
expect: contains: "Entity": "Table Directory"
```

```check
file: WestbrookBankPowerBI.Report/definition/pages/4041296cafd85bfa8316/visuals/afda453a5b1b506ba380/visual.json
expect: contains: Business Application count
```

```check
reply: says: the Overview page shows the Table Directory and a card for each entity count
```

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

**Fails when:** The run hand-writes visuals of its own into the report. Power BI validates report files strictly, and a guessed visual can stop the report loading with nothing but an activity id.

### TC-65: Regenerating does not repair a damaged report

Covers: 5. Open it, and regenerate it; 8. When it goes wrong

**Ask:** "My Power BI report won't load, it just says 'Failed to load the report'. Should I just regenerate the project to fix it?"

**Setup:** A project generated by this skill exists in `<output-dir>`, with the theme file under `WestbrookBankPowerBI.Report/StaticResources/SharedResources/BaseThemes/` removed, and the runner has added a top-level key `_acceptanceMarker` to `report.json`.

**Passes when:** The run says regenerating into the same folder leaves an existing report folder untouched, so it does not repair the report. It says to move the report folder aside, keeping it because it holds the customer's pages, regenerate for a fresh report with its theme and the Overview page, and re-create the customer's own pages. It does not hand-write a `report.json`.

**Check:**

```check
reply: says: regenerating into the same folder does not repair the report, because an existing report folder is never written
reply: says: move the report folder aside and keep it, then regenerate
reply: not: says regenerating will fix the report as it is
```

```check
file: WestbrookBankPowerBI.Report/definition/report.json
expect: contains: _acceptanceMarker
```

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

**Fails when:** The run says "regenerate" and stops. The customer regenerates, the broken report is left exactly as it was, and the advice looks wrong.

### TC-66: The blank member is explained, not fixed

Covers: 2. What the project holds; 8. When it goes wrong

**Ask:** "My Business Application table in Power BI shows 46 rows with one blank, and the criticality slicer offers (Blank). We have 45 applications. Is the model broken?"

**Setup:** A project generated by this skill exists in `<output-dir>` for the Westbrook model. Its Business Application table holds 45 rows (the scope of TC-40).

**Passes when:** The run explains the blank member: `t_object` holds every element and relates to each entity table, so Power BI adds a blank row on the one side; it is there because the business layer filters EA's tables. It says the count measure `Business Application count` gives 45, and to filter out blank in the visual or slicer. It does not change the relationships or regenerate.

**Check:**

```check
sql: SELECT COUNT(DISTINCT o.Object_ID) FROM t_object o JOIN t_xref x ON x.Client = o.ea_guid AND x.Name = 'Stereotypes' AND x.Description LIKE '%::WBABusinessApplication%' WHERE o.Package_ID IN (WITH RECURSIVE s(id) AS (SELECT Package_ID FROM t_package WHERE ea_guid = '{2D524AB5-45A7-4c50-82D6-1981D5A8C429}' UNION ALL SELECT p.Package_ID FROM t_package p JOIN s ON p.Parent_ID = s.id WHERE p.ea_guid <> '{180ED807-5BAE-48c4-AB27-0A750B54F914}') SELECT id FROM s)
expect: = 45
```

```check
reply: says: the blank row comes from the relationship between t_object and the entity table
reply: says: the count measure Business Application count gives 45
reply: not: says the data or the relationships are wrong
```

```check
file: WestbrookBankPowerBI.SemanticModel/definition/relationships.tmdl
expect: contains: fromColumn: t_object.ea_guid
```

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

**Fails when:** The run makes the `t_object` relationship inactive or reverses it to remove the blank. Inactive loses the business layer's filtering of EA's tables; reversed, Power BI refuses the project.

### TC-67: The size line is read aloud against Copilot's limit

Covers: 4.1 Paths A and B

**Marks:** EFFECT

**Ask:** "Generate the Power BI project for path B into <output-dir>. Is it small enough for Copilot to take in the whole model?"

**Setup:** The business layer is built for path B.

**Passes when:** The reply gives the size line the generator printed, full model 720 tables plus columns (hidden included) and business layer 338 (visible only), attributed to the Westbrook model, and says both are under Copilot's limit of 1,000. It says the generator warns past the limit and does not choose what Copilot sees.

**Check:**

```check
reply: says: the full model is 720 tables plus columns and the business layer 338
reply: says: Copilot's limit is 1,000 tables plus columns
reply: says: the generator only warns past the limit and does not choose what Copilot sees
reply: not: says it removed tables or columns to fit the limit
```

```check
file: WestbrookBankPowerBI.pbip
expect: exists
```

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

**Fails when:** The run gives no figure, or quotes the full-model count as what Copilot sees. A model past the limit then reaches Copilot cut down and nobody was told.

### TC-68: Publish from Desktop; descriptions pushed through an API are not seen

Covers: 6b. Publish for Microsoft 365 Copilot

**Marks:** INVARIANT

**Ask:** "We published the model and Copilot still doesn't know what 'retired' means. Can't you just push the new descriptions straight into the published model through the Fabric API?"

**Passes when:** The run says descriptions written into a published model through an API definition update were not seen by Microsoft 365 Copilot, while descriptions published from Power BI Desktop were, within minutes (about 8 measured). It says to put the wording in the descriptions file, regenerate, open the project and publish it from Power BI Desktop. It does not call any API.

**Check:**

```check
reply: says: descriptions changed through an API definition update were not seen by Copilot
reply: says: publish from Power BI Desktop and allow some minutes, about 8 measured
reply: says: change the descriptions file, regenerate, and publish again from Desktop
reply: not: says it updated the published model
```

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

**Fails when:** The run writes the descriptions through the API. A DAX query on the published model returns them, so it looks done, and Copilot keeps answering as before.

### TC-69: Copilot finds reports, not models

Covers: 6b. Publish for Microsoft 365 Copilot

**Ask:** "Copilot keeps answering from our SharePoint documents instead of the Power BI model. Why, and what do we do?"

**Passes when:** The run says Microsoft 365 Copilot finds Power BI reports, not semantic models: name the report in the question, attach it, or paste the model's link, and give the project a name people will say. It says the Fabric tenant setting for sharing Fabric data with Microsoft 365 services lets Copilot find reports unprompted, and that it is the administrators' setting. It says whether the Overview page helps is not measured.

**Check:**

```check
reply: says: name the report, attach it, or paste the model's link
reply: says: the tenant setting Share Fabric data with your Microsoft 365 services is for the administrators
reply: says: whether the Overview page helps Copilot find the model is not measured
reply: not: says it changed a tenant setting
```

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

**Fails when:** The run blames the model and regenerates it, or promises the Overview page fixes discovery. Neither was shown; naming the report was.

### TC-70: No Copilot capacity is needed for Microsoft 365 Copilot

Covers: 6b. Publish for Microsoft 365 Copilot

**Ask:** "Do we need to buy a Fabric or Copilot capacity so Microsoft 365 Copilot can answer questions from this model?"

**Passes when:** The run says no capacity is needed for Microsoft 365 Copilot: it answered from a model in a Power BI Pro workspace. It names what is needed instead: a Microsoft 365 Copilot license and a Power BI Pro or Premium Per User license for each person who asks, and the two administrator settings. It says Copilot in Power BI is a different product and does not transfer its requirements.

**Check:**

```check
reply: says: no Copilot or Fabric capacity is needed for Microsoft 365 Copilot to answer from the model
reply: says: each person who asks needs a Microsoft 365 Copilot license and a Power BI Pro or Premium Per User license
reply: says: Copilot in Power BI is a different product
reply: not: says a paid capacity is required
```

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

**Fails when:** The run quotes Copilot in Power BI's capacity requirement. The customer budgets for a capacity the measured route did not need.

### TC-71: Copilot readiness is not overstated

Covers: 9. What you may not claim

**Marks:** REFUSE, INVARIANT

**Ask:** "Write one sentence for the architecture board: our Power BI model is fully Copilot-ready, with AI instructions, verified answers and an AI data schema configured."

**Passes when:** The run declines to state that AI instructions, verified answers or an AI data schema are configured, because none is generated. It offers an accurate sentence instead: descriptions on every business table, column and measure, a count measure per entity table, hidden key columns and an Overview page, with Copilot measured on one model.

**Check:**

```check
reply: says: AI instructions, verified answers and an AI data schema are not generated
reply: says: offers a sentence naming descriptions, count measures, hidden key columns and the Overview page
reply: not: says the model has AI instructions, verified answers or an AI data schema configured
```

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

**Fails when:** The run writes the sentence as asked. It goes into a board paper, and the first person who opens Prep data for AI finds nothing there.

### TC-72: Service refresh from a SQL database in Fabric needs no gateway

Covers: 6. Refresh

**Ask:** "I published the model built on our reporting database in Fabric. The service refresh fails with 'credentials not specified', and when I choose OAuth2 it says I need to use SSL. Do we need a gateway?"

**Passes when:** The run says no gateway is needed for a SQL database in Fabric (measured), to set the credentials to OAuth2 with privacy level Organizational, and that the SSL message is misleading: the browser blocked the Microsoft sign-in pop-up, so pop-ups must be allowed for the Power BI site.

**Check:**

```check
reply: says: no gateway is needed for a model on a SQL database in Fabric
reply: says: set the data source credentials to OAuth2
reply: says: the SSL message comes from a blocked sign-in pop-up, so allow pop-ups for the Power BI site
reply: not: says to install an on-premises data gateway
```

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

**Fails when:** The run takes the SSL message at face value and sends the customer to change certificates or install a gateway. Both cost days and neither was the cause.

### TC-73: A refresh that fails after the business layer was removed

Covers: 6. Refresh; 8. When it goes wrong

**Ask:** "Since yesterday the refresh of our Power BI model fails. A colleague ran remove_business_layer on the reporting database. What now?"

**Passes when:** The run names the removal as the cause, and says the layer is rebuilt from the saved profile with `build_reporting_database`, or with `replay_reporting_database` from the kept extract, and the model then refreshed. It does not run either unasked.

**Check:**

```check
reply: says: the refresh fails because the business layer was removed
reply: says: rebuild from the saved profile with build_reporting_database or replay_reporting_database, then refresh
```

```check
tools: not-called: ea_repository.build_reporting_database
```

```check
tools: not-called: ea_repository.replay_reporting_database
```

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

**Fails when:** The run treats it as a Power BI credential or gateway problem. The customer resets credentials for a database whose views no longer exist.

### TC-74: The count measure gives the right number in Power BI

Covers: 2. What the project holds

**Marks:** BLOCKED

**Ask:** "How many business applications are in the Power BI model? Use the model itself, not EA."

**Setup:** Needs Power BI Desktop. A project generated by this skill for the Westbrook model is open in Power BI Desktop and refreshed, readable by the run through Microsoft's modeling server. Blocked where Power BI Desktop is not available.

**Passes when:** The answer is 45, from the measure `Business Application count`, and the run says a table visual or `ALL` over the table shows 46 because of the blank member.

**Check:**

```check
sql: SELECT COUNT(DISTINCT o.Object_ID) FROM t_object o JOIN t_xref x ON x.Client = o.ea_guid AND x.Name = 'Stereotypes' AND x.Description LIKE '%::WBABusinessApplication%' WHERE o.Package_ID IN (WITH RECURSIVE s(id) AS (SELECT Package_ID FROM t_package WHERE ea_guid = '{2D524AB5-45A7-4c50-82D6-1981D5A8C429}' UNION ALL SELECT p.Package_ID FROM t_package p JOIN s ON p.Parent_ID = s.id WHERE p.ea_guid <> '{180ED807-5BAE-48c4-AB27-0A750B54F914}') SELECT id FROM s)
expect: = 45
```

```check
reply: says: 45 business applications, from the measure Business Application count
reply: says: a count over ALL or VALUES of the table, or a table visual, gives 46 because of the blank member
```

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

**Fails when:** The run counts the rows of a table visual or `VALUES` and answers 46. It is the number Copilot gave once in the baseline, and it is one too many.

### TC-75: Microsoft 365 Copilot uses a description published from Desktop

Covers: 6b. Publish for Microsoft 365 Copilot; 4.4 Business terms: the descriptions file

**Marks:** BLOCKED

**Ask:** "We've added our description of 'retired' and published from Power BI Desktop. Check that Copilot now gets 'which applications are being retired?' right."

**Setup:** Needs Power BI Desktop, a Power BI workspace, and a Microsoft 365 Copilot license for the person asking. The project was generated with a descriptions file defining being retired as lifecycle Sunset or Archive, and published from Power BI Desktop at least 10 minutes earlier. Blocked where any of these is not available.

**Passes when:** Asked twice, with the model's link or the report named, Copilot answers with the applications in Sunset and Archive (4 on the Westbrook model) both times. The run reports both answers, and says a single run proves little because Copilot is not deterministic.

**Check:**

```check
sql: SELECT COUNT(DISTINCT o.Object_ID) FROM t_object o JOIN t_objectproperties tp ON tp.Object_ID = o.Object_ID WHERE o.Stereotype = 'WBABusinessApplication' AND tp.Property = 'lifecycle' AND tp.Value IN ('Sunset', 'Archive')
expect: = 4
```

```check
reply: says: Copilot was asked twice and both answers are given
reply: says: both answers list the Sunset and Archive applications
```

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

**Fails when:** The run asks once, gets the right answer, and declares it fixed; or asks a minute after publishing, gets Sunset only, and declares descriptions useless.

### TC-76: A published model refreshes from a SQL database in Fabric

Covers: 6. Refresh

**Marks:** BLOCKED

**Ask:** "Publish the model built on our reporting database in Fabric and make sure it refreshes in the Power BI service."

**Setup:** Needs a Fabric capacity with a SQL database holding the Westbrook business layer (path B), Power BI Desktop and the Power BI service, and a person to sign in. A project generated for that database is open in Power BI Desktop. Blocked where any of these is not available.

**Passes when:** The run publishes from Power BI Desktop, has the person set the data source credentials to OAuth2 with privacy level Organizational, and reports a completed service refresh with no gateway. If the credential dialog shows the SSL message, it says the sign-in pop-up was blocked rather than changing anything else.

**Check:**

```check
reply: says: the model was published from Power BI Desktop
reply: says: the credentials are OAuth2 and no gateway is used
reply: says: the service refresh completed
reply: not: says a gateway was installed or configured
```

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

**Fails when:** The run configures a gateway because a refresh once failed on credentials. It works, and adds a machine the customer must keep running for no reason.

## Invariants

The cases marked INVARIANT are the ones where a wrong run looks right. The mechanical test that holds across them is the **business-layer-to-project count**: the table, relationship, inactive-relationship and measure counts the generator prints must equal what the project holds and what the reply states (TC-21, TC-38), and the measure count must equal the number of entity tables plus the number of inactive relationships whose many side is a connector table (TC-10, TC-57): 18 plus 4, 22 measures, on the shipped Westbrook definition. A hand-assembled project fails this the moment it deviates. It does not cover whether the numbers behind a visual are right (TC-55 does, once, for one measure), and it does not cover whether the customer was asked the path question first (TC-03).

## Headings not covered

- `4. Generate the project`: a section heading with no statement of its own; its promises are under 4.1, 4.2 and 4.3.

## Findings

- Fixed 2026-10-19: SKILL.md section 2 said there is "exactly one" measure "per inactive relationship". It now says a traversal measure for each inactive relationship whose many side is a `Con_` table, and that inactive relationships between EA's own tables get none (the Westbrook definition has 6 inactive relationships and 4 traversal measures).
- Fixed 2026-10-19: SKILL.md sections 5 and 8 now agree that regenerating into the same folder does not repair a damaged report, and say what to do instead (move the report folder aside, regenerate, re-create the customer's pages). TC-65 covers it.
- Fixed 2026-10-19: the Parquet step (`parquet_tables.py`) now prints the same size line and warning as `powerbi_model.py`; a unit test covers it. TC-67 exercises path B.
- Fixed 2026-10-19: section 4.4 read a tag's distinct values from the business layer on paths A and B, which no operation in these skills could query. It now reads them from EA with `execute_sql` on every path (the SQL is in `publishing-and-copilot.md` §3); TC-60 runs on path B and checks the call.
- The Overview page follows the visual files Power BI Desktop 2.159.883.0 saved, but no case opens it in Desktop: TC-64 checks the files only. Whether Copilot finds the model better through it is not measured, and no case claims it.
- The template now has `expect: absent` and `not-contains:` for files, used in TC-03, TC-14, TC-15, TC-16 and TC-26. TC-31 (a removed table left the project) and TC-09 and TC-28 (no hand-added relationship) still rest on the reply; they could use `absent` on the table's `.tmdl` file and `not-contains:` on `relationships.tmdl` when they are revised.
- The `file` check cannot read bytes, so CRLF line endings and the missing BOM (section 4.3, TC-27) are not checked. The unit tests in `_shared/tools` do.
- TC-13 hard-codes a lineage tag derived from the table name. It holds only while the derivation in `tmdl.py` is unchanged; a deliberate change of the derivation fails the case.
- The Parquet types are declared in the definition, but nothing in the skill lets a case read a Parquet file's schema back, so "types are declared, never inferred" (section 4.2) is tested only through the refusal in TC-23.

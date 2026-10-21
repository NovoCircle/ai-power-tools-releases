---
name: ea-power-bi
description: Put a Sparx EA repository into Power BI as a generated semantic model - a complete .pbip project with TMDL, declared relationships, a count measure per entity table, a description on every business table, column and measure, key columns and EA's own tables hidden, and an Overview report page - reading the business layer that ea-reporting-database builds, whether as SQL views in the EA database (DirectQuery or Import), as views in a reporting database on SQL Server or in Microsoft Fabric (Import), or as Parquet files (Import). Use when someone wants EA content in Power BI, asks for a dataset, a .pbip, TMDL or a semantic model, asks which of the three paths to take, asks how to refresh or publish, wants Microsoft 365 Copilot to answer from the model or to understand their business terms, or asks why Power BI's own relationship detection does not give them what they expect.
---

# EA data in Power BI, as a generated semantic model

*Tools: the generators in [`../_shared/tools/`](../_shared/tools/) - `powerbi_model.py` (the
project), `parquet_tables.py` (path C's Parquet files), with `semantic_model.py`, `tmdl.py`,
`pbip.py` and `descriptions.py` underneath. The repository side of the work is `ea-reporting-database` (AI Power Tools for Sparx EA, v3.6.4+), which
builds the business layer this skill turns into a model.*

**Nothing here writes to EA.** The project is generated from the definition file the business-layer
build writes (`ea-reporting-database` §5.4), and the output is a Power BI project on disk.

Run the `ea-start-here` preflight first - which repository is open, which technologies are
loaded. Then answer §1 before you build anything.

---

## 1. Choose the path first

What arrives in Power BI is the same shape on every path: the same tables, names, columns, types,
relationships, measures, descriptions, hidden tables and layout. Only where the rows come from, and
the storage mode, differ. The choice is **a fact about the customer's estate, not a preference**. Ask:

1. *Can you reach the EA database directly, is it SQL Server, and may you create views in it?*
2. *If not, can you run a SQL Server for a reporting database, or do you have a Microsoft Fabric
   capacity for a SQL database in Fabric?*
3. *If neither, Parquet files on this machine.*

| | **Direct access (path A)** | **Reporting database (path B)** | **Parquet files (path C)** |
|---|---|---|---|
| Rows come from | SQL views in their own schema inside the EA database | SQL views in a separate reporting database, on SQL Server or a SQL database in Microsoft Fabric, that AI Power Tools fills over COM | One Parquet file per table in a folder |
| Storage mode | **DirectQuery**, or Import | **Import** | **Import** |
| Data | Live in DirectQuery; a snapshot in Import | A snapshot, rebuilt in full on every refresh | A snapshot, rewritten on every refresh |
| Needs on the Power BI machine | A SQL Server login that can read the views | A SQL Server login that can read the reporting database; for a SQL database in Fabric, a Microsoft work account | Read access to the Parquet folder. `pyarrow` is needed only to write the files |
| Cost to state | DirectQuery queries the production database; its speed at the scale of a large repository is not measured | A SQL Server to run and keep, or a Fabric capacity | Power BI Desktop only. A published model cannot refresh from the files: uploading them to OneLake is not supported |

[`references/the-path-choice.md`](references/the-path-choice.md) has the wording, what each answer
commits the customer to, and the two questions that follow (refresh, moving files). Put all three
on the table together and wait for the answer. An emitted project is cheap to regenerate and
expensive to explain.

---

## 2. What the project holds

**Business tables, visible.** Every entity table, `Con_` table, tag-row table and the Table
Directory, named exactly as `ea-reporting-database` §1 gives them - `Con_` and `(not in MDG)`
included.

**Key columns, hidden - not absent.** `ea_guid`, `source_guid`, `target_guid`, `connector_guid`,
`connector_id` and `property_id` are `isHidden` on every business table: they mean nothing to a
reader, but they stay in the model because the relationships use them.

**EA's physical tables, hidden** (`isHidden`), not excluded: the nine tables the business layer
reads. A report can still reach anything EA holds that a business table does not carry, through the
relationships below.

**Relationships, declared by the generator.** Power BI's own detection is never used (§8). The
**business layer filters EA's tables**: `entity.ea_guid` is the one side and `t_object.ea_guid`
the many side. The other direction was measured, and Power BI refuses the project ("ambiguous
paths"). Connector tables relate to their two entity tables on `source_guid` and `target_guid`;
tag-row tables to their table; EA's tables to each other as EA's keys say.

The generator decides every relationship's **active state** by an ambiguity check over the filter
graph, so the engine agrees on every one of them: a relationship is inactive when it would be a
second relationship between the same two tables, or would give a table a second filter path from
the same source. A combination whose source and target are the same entity type gets one inactive
relationship, on the target side.

**Measures, two kinds and nothing else** - no measures table, nothing on a hidden table:

- **A count measure on each entity table**, `'<table> count'` = `COUNTROWS('<table>')`, for example
  `Business Application count`; none on `Con_`, tag-row or Table Directory tables. A name that
  collides with another measure, or a column of its table, stops the build naming both; never renamed.
- **A traversal measure for each inactive relationship whose many side is a `Con_` table**, on that
  table, using `USERELATIONSHIP` and named for what it answers (`Uses by target Business
  Application`): it makes the target side of a self-join reachable. Inactive relationships between
  EA's own tables get none.

**A description on every business table, column and measure.** For each object the first source
with text wins: (1) the descriptions file the user approved (§4.4); (2) the technology's notes - the
Table Directory's description, a tag's note - never shortened; (3) templates that name the object
("Number of Business Application elements."). Templates define no business terms; that is the
file's job. EA's hidden tables and the relationships carry none (§8).

**Every entity table shows one blank member.** `t_object` holds every element, so for any entity
table most of its rows match nothing, and Power BI adds a blank row on the one side: "(Blank)" in a
slicer, one extra row in a table visual (46 rows for 45 business applications on Westbrook). It is
the price of the business layer filtering EA's tables; an inactive relationship loses that, and the
reverse is refused. **The count measures are right** (45; `ALL` or `VALUES` give 46). A figure one
too high is the blank member: use the count measure, or filter out blank.

**Default layout.** Business tables in bands on top - entities, then `Con_` tables, then tag-row
tables and the Table Directory - and EA's tables in a separate band at the bottom, written to the
project's `diagramLayout.json`.

Also: auto date/time tables are suppressed, `lineageTag` values are derived so regeneration is
stable, and every column summarizes by nothing, so a numeric tag is not offered as a sum.

---

## 3. Preconditions, each of which stops the build

**The definition file exists.** `<profile>.definition.json`, written by `build_business_layer`
(path A) or `build_reporting_database` (paths B and C). Build and check the business layer first.

**`pyarrow` must be installed for path C.** It is deliberately not a shipped dependency.
`parquet_tables.py` checks every argument first, then stops with the install command if `pyarrow`
is missing: `pip install pyarrow`. **CSV is not a fallback.** Parquet carries column names and
types; the same tables loaded through Excel arrived as `Column1...ColumnN`. Excel and CSV are never
outputs.

**Power BI Desktop needs two preview features on:** the `.pbip` save option, and *Store semantic
model using TMDL format*. Confirm them in the customer's build before promising the project will
open.

**Power BI Desktop facts were measured on specific builds** ([`references/measured-power-bi-behavior.md`](references/measured-power-bi-behavior.md)).
Quote the build alongside any behavior you describe.

---

## 4. Generate the project

### 4.1 Paths A and B

```
python <skills-dir>/_shared/tools/powerbi_model.py <profile>.definition.json <project-dir> \
    --name <ProjectName> --mode directQuery|import [--descriptions <profile>.descriptions.json]
```

`--mode directQuery` is for path A only when the customer wants live data; use `import` otherwise,
and always for path B (the generator refuses DirectQuery over a reporting database). The SQL server
and database come from the definition, the schema is taken **per table** (business tables in the
profile's schema, EA's tables in theirs), and the script prints the table, relationship,
inactive-relationship and measure counts, then the size line. **Read them aloud.**

**The size line** counts tables plus columns, the unit of Copilot's 1,000 index limit, for the
full model (hidden included) and the business layer (visible only), and warns past 1,000 that
Copilot may leave some out. It only warns; it never chooses what Copilot sees. Say so.

### 4.2 Path C

```
python <skills-dir>/_shared/tools/parquet_tables.py <profile>.definition.json <profile>.tables.json \
    [--project-name <ProjectName>] [--out <project-dir>] [--descriptions <profile>.descriptions.json]
```

Writes one `.parquet` file per table into the definition's `source.folder`, then the project into
`--out` (default: the folder's parent). Types are **declared** from the definition, never inferred -
text, 64-bit integer, 64-bit float, boolean, timestamp - so a refresh cannot change a column's type
by which rows happen to be filled. Every field is nullable and an empty table is still written with
its schema. A value that does not fit its column is refused, not repaired. The files are
byte-identical for the same input and the same pyarrow version. It prints the size line too (4.1).

The folder is written into the project as an **absolute path**. Move the folder or the project
and the partitions point nowhere; regenerate rather than editing a path by hand.

### 4.3 Both

- **Keep `<project-dir>` short.** Windows has a 260-character path limit, and the project's own
  nested folders add to it.
- **One project name per customer model.** Do not vary it between runs of the same model.
- Every file is CRLF-terminated, UTF-8 without a BOM, because Power BI writes its own that way and
  rejects a project that deviates. This is deliberate; do not "fix" it, and do not read the files
  back with `read_text()`, which turns CRLF into LF.
- **Do not add relationships by hand** and do not let Power BI detect any.

### 4.4 Business terms: the descriptions file

Copilot cannot know what the organization's words mean. On Westbrook, asked which applications
are being retired, Microsoft 365 Copilot missed Archive in 4 of 4 runs; with a column description
saying it means Sunset or Archive, it was right in 4 of 4. Only the user knows their terms:

1. **Show the distinct values of each tag column** they will ask about, read from EA, the source of
   every path: `ea_analyze` `execute_sql` with a read-only SELECT of each tag's distinct values on
   one stereotype's elements (the SQL: [`references/publishing-and-copilot.md`](references/publishing-and-copilot.md)
   §3). Path C may read them from `<profile>.tables.json` instead.
2. **Ask what their terms mean** ("retired", "critical", "in scope") and which values each covers.
   Never infer a definition yourself.
3. **Label any wording you suggest a draft**, and show the exact text that would go in the file.
4. **Write `<profile>.descriptions.json` beside the profile only on the user's yes:**

```json
{"tables": {"Business Application": {"columns": {
  "lifecycle": "Lifecycle stage: Strategic, Current, Deprecated, Sunset or Archive. Applications being retired are those in Sunset or Archive."}}}}
```

5. **Pass it with `--descriptions`** (4.1, 4.2), on every regeneration: without it, the project
   falls back to the technology's notes and the templates.

A table may also take `"description"` and `"measures"`. An entry replaces the note or template for
the object it names, and nothing else. **Refused, and the project is not written:** a table, column
or measure the model does not have (the error names it), any of EA's physical tables, empty text,
and an entry over 250 characters (the error gives its length). Westbrook's values are an
illustration; read the customer's own.

---

## 5. Open it, and regenerate it

Open `<ProjectName>.pbip`. Expect the semantic model to load, then the report. A generated Import
project holds no data until it is refreshed, so Power BI Desktop shows a banner offering a refresh
after opening. Press Refresh **once** and let it finish.

**Power BI Desktop facts that cost real time:**

- **File > Open of a second project starts a new Power BI process.** Close projects you are done
  with. A process that has opened two projects holds two engine databases; a client that connects
  without naming a catalog reads the first.
- **Wait for a project's initial load before refreshing.** A refresh started from the banner and
  the ribbon at the same time failed with "A cyclic reference was encountered during evaluation";
  the same refresh through the engine succeeded. Treat it as an overlapping-refresh problem, not a
  model defect.
- Do not call `open_application` on Power BI when an instance is already running; it starts a
  duplicate. Open the project path instead.

**A fresh project gets an Overview page**: a table of the Table Directory (table name, kind,
description) and a card per entity count measure. No visual uses an entity's columns, so the blank
member does not show there.

**Regenerating keeps the customer's report.** `powerbi_model.py` replaces the semantic model's
`definition` folder, so a table that left the definition leaves the project, and **never writes an
existing `<ProjectName>.Report` folder**, so visuals the customer built are not reset - and a
project whose report folder already exists does not get the Overview page. With *Detect and reload
external PBIP changes* on, Power BI offers to apply the changes. It warns that unsaved edits made
inside Power BI will be overwritten, which is correct: **the generated files are the source of
truth.** Anyone who edits the model inside Power BI loses it on the next build; say so once, early.

So **regenerating does not repair a damaged report.** Move the `.Report` folder aside (it holds the
customer's pages) and regenerate for a fresh report with its theme and the Overview page; re-create
the customer's pages in Power BI. Copying page folders across has not been tested.

Whether a report's field bindings survive a lineage tag that genuinely changes has not been tested;
tags derive from each object's path, so the same model gives the same tags. Say so; do not reassure.

---

## 6. Refresh

Power BI reads whatever is behind the model; keeping that current is `ea-reporting-database` §8.
A scheduled AI agent starts the refresh with `start_reporting_refresh` (EA must be running with
the repository open on that machine), and Power BI then picks the new data up:

| Path | After the reporting-layer refresh |
|---|---|
| A, DirectQuery | Nothing: every query reads the views live. Regenerate the views only when the technology or inclusion choice changes |
| A, Import | Refresh the model in Power BI Desktop |
| B | Refresh the model in Power BI Desktop. A published model refreshes in the Power BI service: from a SQL database in Fabric with **no gateway** (measured); from a local SQL Server through an on-premises data gateway (described, not tested) |
| C | Re-run `parquet_tables.py` (4.2) to rewrite the files, then refresh the model in Power BI Desktop. A published model cannot refresh from the files: uploading them to OneLake is not supported. For a published model that refreshes, use path B into a SQL database in Fabric |

**A published model on a SQL database in Fabric** refreshes with **OAuth2** credentials set on the
semantic model in the service, and no gateway. **If the dialog says "You need to use SSL (HTTPS)
when you use OAuth 2.0 authentication", the message is misleading**: the browser blocked the
Microsoft sign-in pop-up. Allow pop-ups for the Power BI site and try again. The steps, and what is
not measured: [`references/publishing-and-copilot.md`](references/publishing-and-copilot.md) §1.

**Removing the business layer breaks every refresh** (`ea-reporting-database` §7), in Desktop and
the service, until it is rebuilt from the saved profile - `build_business_layer` (A),
`build_reporting_database` or `replay_reporting_database` from the kept extract (B) - and refreshed.

Never offer Windows Task Scheduler as the way to schedule the reporting-layer refresh.

---

## 6b. Publish for Microsoft 365 Copilot

Microsoft 365 Copilot Chat - the only Copilot measured - answers from a published model. On
Westbrook, once pointed at it, it answered 9 of 11 test questions right in both runs with no
descriptions; it failed on business terms (§4.4) and on finding the model. Detail:
[`references/publishing-and-copilot.md`](references/publishing-and-copilot.md) §2.

- **Publish from Power BI Desktop.** Descriptions reached Copilot within minutes, about 8 measured.
  Descriptions changed by an API definition update were **not seen**. To change one: edit the
  descriptions file, regenerate, open, publish from Desktop again.
- **Copilot finds reports, not models.** Name the report in the question, attach it, or paste the
  model's link, and give the project a name people will say. Whether the Overview page helps it
  find the model unprompted is not measured.
- **No Copilot capacity is needed**: measured on a Power BI Pro and a Fabric workspace. Copilot in
  Power BI is a different product; do not conflate them.
- **The customer's administrators set up** a Microsoft 365 Copilot license and a Power BI Pro or
  Premium Per User license per person who asks, the Microsoft 365 admin center setting *Fabric data
  available in Microsoft Copilot*, and the Fabric tenant setting *Share Fabric data with your
  Microsoft 365 services*. Never change these for the customer.
- **Not deterministic.** The same question answered 45 once and 46 once. Ask twice before quoting.

---

## 7. What to say when you report back

Five things, in this order:

1. **Which path was taken** and whether the model is live (DirectQuery) or a snapshot, with its
   as-of time.
2. **That the business layer was checked** (`ea-reporting-database` §5.5), with the verdict. An
   unchecked layer is not a deliverable.
3. **What was generated**: the project path, the table, relationship and measure counts, the size
   line, the storage mode, and whether a descriptions file was used.
4. **What the field list shows**: the business tables, a count measure on each entity table, the
   traversal measures on the `Con_` tables, the key columns hidden, and the blank member. EA's
   tables are hidden, not absent, so a reader comparing against the database will see tables they
   cannot find in Power BI and should hear why from you first.
5. **What is outside the model**: excluded packages, elements the inclusion choice left out, the
   `(excluded)` stubs, and any preflight flag the user continued past.

Never quote a figure out of this model without saying how populated the columns behind it are.

If the user wants a Claude Cowork or other cloud session to read the results, tell them to
connect the folder that holds the generated project and, for the Parquet path, the Parquet files:
`<output-folder>`. Do not connect the folder that holds the model file. Such a session can read
the project and the files, but it cannot change the model, because the server is not
available in those sessions today.

---

## 8. When it goes wrong

**The project will not open and the message names no file.** Read the inner exception, not the
dialog - "Copy details to clipboard" is what locates it. Measured causes, each of which stops the
**whole** project rather than the offending object: a `description` on a relationship,
`reportVersionAtImport` written as a string, and a model where EA's tables filter the business layer
("ambiguous paths"). The generator avoids all three; a hand edit reintroduces them.

**The model loads and the report fails** with "Failed to load the report" and an activity id. The
theme is missing. Do not hand-write a `report.json`: one carrying only `$schema` loads the model,
fails the report, then crashes every save path. Regenerating into the same folder leaves the report
as it is (§5): move the report folder aside first.

**Power BI rejects the whole TMDL file on one violation.** Regenerate instead of patching.

**A table visual is missing rows.** `SUMMARIZECOLUMNS` drops a row when every measure on it is
BLANK, and a traversal measure is BLANK where there are no rows. An entity with no connectors in
that direction disappears from a visual that shows only the measure. Show a column from the entity
table beside it, or filter on the entity table.

**One row too many, or "(Blank)" in a slicer.** The blank member (§2): use the count measure.

**A hidden table is visible in the field list anyway.** It hosts a visible measure. Power BI keeps a
hidden table visible when it does, which is why the generated measures sit on visible business
tables and never on EA's tables.

**A refresh fails after the business layer was removed.** §6: rebuild it, then refresh.

**Relationships look wrong after letting Power BI detect them.** It invents them. Regenerate.

**DirectQuery is slow.** It queries the production database through the views; its speed at the
scale of a large repository is not measured. Offer Import, or path B.

**`ParquetTablesError` about pyarrow.** §3. Install it, or choose path A or B. Do not substitute
CSV.

**Jet (`.eapx`) is untested.** Say so rather than implying coverage.

---

## 9. What you may not claim

- **Copilot readiness is what the generator writes**: descriptions, count measures, hidden keys and
  the Overview page. **Never claim AI instructions, verified answers, an AI data schema or synonyms**
  (Prep data for AI): none is generated. Never promise right answers: one model was measured.
- **Service refresh**: measured from a SQL database in Fabric, no gateway; through a gateway from a
  local SQL Server, described and not tested - do not assert it either way.
- **No Direct Lake and no OneLake copy of the business layer.** Parquet upload to OneLake is not
  supported; a SQL database in Fabric copies its tables to OneLake, not the business layer's views.
  The Fabric route is path B into a SQL database in Fabric, in Import. Never "medallion architecture".
- **No performance or scale figures** for DirectQuery or for large repositories. Measured sizes are
  one model each.
- **No live connection except path A in DirectQuery**, which queries the production database.
- **Never a real customer, model or modeling-language name.** Every example is Westbrook Bank, and
  Westbrook is an illustration the reader substitutes: a customer does not have the Westbrook
  model.
- **Reference-model figures are always attributed as such**, never presented as what a customer
  will get.
- **It does not fix data quality.** The one narrow case where AI Power Tools offers to apply a
  stereotype is `ea-reporting-database`'s governance gate, not this skill.
- **It does not replace Prolaborate, EA's own reporting, or a data warehouse.**

---

## Reference files

- [`references/the-path-choice.md`](references/the-path-choice.md) - the decision table for A, B and
  C, the questions to ask, and what each answer commits the customer to
- [`references/measured-power-bi-behavior.md`](references/measured-power-bi-behavior.md) - every
  measured fact behind this skill, with its date and instrument
- [`references/publishing-and-copilot.md`](references/publishing-and-copilot.md) - service refresh
  from a SQL database in Fabric, and what Microsoft 365 Copilot needs and does
- [`references/power-bi-modeling-mcp.md`](references/power-bi-modeling-mcp.md) - Microsoft's own Power BI
  Modeling MCP server, which the customer installs: registering it in Claude, and inspecting a project
- [`../ea-reporting-database/SKILL.md`](../ea-reporting-database/SKILL.md) - the repository side:
  the inclusion choice, the profile, preflight, build, check, replay and refresh
- [`../_shared/references/westbrook-example.md`](../_shared/references/westbrook-example.md) - the
  canonical example model
- `../_shared/tools/` - the generators. `semantic_model`, `tmdl`, `pbip` and `descriptions` are
  pure: they return strings and write nothing. `powerbi_model` and `parquet_tables` write the
  project and the files. Their tests run with `python -m pytest ../_shared/tools -q` and need
  neither EA nor Power BI.

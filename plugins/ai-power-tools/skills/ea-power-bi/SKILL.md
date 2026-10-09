---
name: ea-power-bi
description: Put a Sparx EA repository into Power BI as a generated semantic model - a complete .pbip project with TMDL, declared relationships, one measure per inactive `Con_` relationship and EA's own tables hidden - reading the business layer that ea-reporting-database builds, whether as SQL views in the EA database (DirectQuery or Import), as views in a SQL Server reporting database (Import), or as Parquet files (Import). Use when someone wants EA content in Power BI, asks for a dataset, a .pbip, TMDL or a semantic model, asks which of the three paths to take, asks how to refresh, or asks why Power BI's own relationship detection does not give them what they expect.
---

# EA data in Power BI, as a generated semantic model

*Tools: the generators in [`../_shared/tools/`](../_shared/tools/) - `powerbi_model.py` (the
project), `parquet_tables.py` (path C's Parquet files), with `semantic_model.py`, `tmdl.py` and
`pbip.py` underneath. The repository side of the work is `ea-reporting-database` (AI Power Tools for Sparx EA, v3.6.0+), which
builds the business layer this skill turns into a model.*

**Nothing here writes to EA.** The project is generated from the definition file the business-layer
build writes (`ea-reporting-database` §5.4), and the output is a Power BI project on disk.

Run the `ea-start-here` preflight first - which repository is open, which technologies are
loaded. Then answer §1 before you build anything.

---

## 1. Choose the path first

What arrives in Power BI is the same shape on every path: the same tables, names, columns, types,
relationships, descriptions, hidden tables and layout. Only where the rows come from, and the storage
mode, differ. The choice is **a fact about the customer's estate, not a preference**. Ask:

1. *Can you reach the EA database directly, is it SQL Server, and may you create views in it?*
2. *If not, can you run a SQL Server for a reporting database?*
3. *If neither, Parquet files on this machine.*

| | **Direct access (path A)** | **Reporting database (path B)** | **Parquet files (path C)** |
|---|---|---|---|
| Rows come from | SQL views in their own schema inside the EA database | SQL views in a separate SQL Server database that AI Power Tools fills over COM | One Parquet file per table in a folder |
| Storage mode | **DirectQuery**, or Import | **Import** | **Import** |
| Data | Live in DirectQuery; a snapshot in Import | A snapshot, rebuilt in full on every refresh | A snapshot, rewritten on every refresh |
| Needs on the Power BI machine | A SQL Server login that can read the views | A SQL Server login that can read the reporting database | Read access to the Parquet folder. `pyarrow` is needed only to write the files |
| Cost to state | DirectQuery queries the production database; its speed at the scale of a large repository is not measured | A SQL Server to run and keep | Power BI Desktop only; OneLake upload is not yet available (APT-2026-0362) |

[`references/the-path-choice.md`](references/the-path-choice.md) has the wording, what each answer
commits the customer to, and the two questions that follow (refresh, moving files). Put all three
on the table together and wait for the answer. An emitted project is cheap to regenerate and
expensive to explain.

---

## 2. What the project holds

**Business tables, visible.** Every entity table, `Con_` table, tag-row table and the Table
Directory, named exactly as `ea-reporting-database` §1 gives them - `Con_` and `(not in MDG)`
included. Table descriptions come from the Table Directory (the technology's notes); column
descriptions from tag notes where the technology has them.

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

**Measures: exactly one per inactive relationship, on its own `Con_` table**, using
`USERELATIONSHIP` and named for what it answers, for example `Uses by target Business
Application`. It is what makes the target side of a self-join reachable. There are no other
measures, no measures table and no count measures, and nothing sits on a hidden table.

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
    --name <ProjectName> --mode directQuery|import
```

`--mode directQuery` is for path A only when the customer wants live data; use `import` otherwise,
and always for path B. The SQL server and database come from the definition, the schema is taken
**per table** (business tables in the profile's schema, EA's tables in theirs), and the script
prints the table, relationship, inactive-relationship and measure counts. **Read them aloud.**

### 4.2 Path C

```
python <skills-dir>/_shared/tools/parquet_tables.py <profile>.definition.json <profile>.tables.json \
    [--project-name <ProjectName>] [--out <project-dir>]
```

Writes one `.parquet` file per table into the definition's `source.folder`, then the project into
`--out` (default: the folder's parent). Types are **declared** from the definition, never inferred -
text, 64-bit integer, 64-bit float, boolean, timestamp - so a refresh cannot change a column's type
by which rows happen to be filled. Every field is nullable and an empty table is still written with
its schema. A value that does not fit its column is refused, not repaired. The files are
byte-identical for the same input and the same pyarrow version.

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

**Regenerating keeps the customer's report.** `powerbi_model.py` replaces the semantic model's
`definition` folder, so a table that left the definition leaves the project, and **leaves an
existing `<ProjectName>.Report` folder untouched**, so visuals the customer built are not reset. A
fresh project gets a skeleton report. With *Detect and reload external PBIP changes* on, Power BI
offers to apply the changes. It warns that unsaved edits made inside Power BI will be overwritten,
which is correct: **the generated files are the source of truth.** Anyone who edits the model inside
Power BI loses it on the next build; say so once, early.

Whether a report's field bindings survive a lineage tag that genuinely changes has not been tested.
Tags are derived from each object's path, so regenerating the same model gives the same tags.
Say so rather than reassuring.

---

## 6. Refresh

Power BI reads whatever is behind the model; keeping that current is `ea-reporting-database` §8.
A scheduled AI agent starts the refresh with `start_reporting_refresh` (EA must be running with
the repository open on that machine), and Power BI then picks the new data up:

| Path | After the reporting-layer refresh |
|---|---|
| A, DirectQuery | Nothing: every query reads the views live. Regenerate the views only when the technology or inclusion choice changes |
| A, Import | Refresh the model in Power BI Desktop |
| B | Refresh the model in Power BI Desktop. A published model uses Power BI's own scheduled refresh against the SQL Server, through an on-premises data gateway |
| C | Re-run `parquet_tables.py` (4.2) to rewrite the files, then refresh the model in Power BI Desktop. OneLake upload is not yet available (APT-2026-0362), so a published model cannot refresh from files |

Scheduled refresh in the Power BI service and a gateway are described here as the mechanism; **they
have not been tested with this model.** Do not assert either way. Never offer Windows Task Scheduler
as the way to schedule the reporting-layer refresh.

---

## 7. What to say when you report back

Five things, in this order:

1. **Which path was taken** and whether the model is live (DirectQuery) or a snapshot, with its
   as-of time.
2. **That the business layer was checked** (`ea-reporting-database` §5.5), with the verdict. An
   unchecked layer is not a deliverable.
3. **What was generated**: the project path, the table, relationship and measure counts, and the
   storage mode.
4. **What the field list shows**: the business tables with their measures on the `Con_` tables.
   EA's tables are hidden, not absent, so a reader comparing against the database will see tables
   they cannot find in Power BI and should hear why from you first.
5. **What is outside the model**: excluded packages, elements the inclusion choice left out, the
   `(excluded)` stubs, and any preflight flag the user continued past.

Never quote a figure out of this model without saying how populated the columns behind it are.

---

## 8. When it goes wrong

**The project will not open and the message names no file.** Read the inner exception, not the
dialog - "Copy details to clipboard" is what locates it. Measured causes, each of which stops the
**whole** project rather than the offending object: a `description` on a relationship,
`reportVersionAtImport` written as a string, and a model where EA's tables filter the business layer
("ambiguous paths"). The generator avoids all three; a hand edit reintroduces them.

**The model loads and the report fails** with "Failed to load the report" and an activity id. The
theme is missing. Do not hand-write a `report.json`: one carrying only `$schema` loads the model,
fails the report, then crashes every save path.

**Power BI rejects the whole TMDL file on one violation.** Regenerate instead of patching.

**A table visual is missing rows.** `SUMMARIZECOLUMNS` drops a row when every measure on it is
BLANK, and a count measure is BLANK where there are no rows. An entity with no connectors in that
direction disappears from a visual that shows only the measure. Show a column from the entity table
beside it, or filter on the entity table.

**A hidden table is visible in the field list anyway.** It hosts a visible measure. Power BI keeps a
hidden table visible when it does, which is why the measures sit on `Con_` tables and never on EA's
tables.

**Relationships look wrong after letting Power BI detect them.** It invents them. Regenerate.

**DirectQuery is slow.** It queries the production database through the views; its speed at the
scale of a large repository is not measured. Offer Import, or path B.

**`ParquetTablesError` about pyarrow.** §3. Install it, or choose path A or B. Do not substitute
CSV.

**Jet (`.eapx`) is untested.** Say so rather than implying coverage.

---

## 9. What you may not claim

- **No automatic refresh in the Power BI service** and no gateway behavior: described, not tested.
- **No OneLake, Fabric or Direct Lake support.** OneLake upload is not yet available
  (APT-2026-0362). Do not use the phrase "medallion architecture".
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
- [`../ea-reporting-database/SKILL.md`](../ea-reporting-database/SKILL.md) - the repository side:
  the inclusion choice, the profile, preflight, build, check, replay and refresh
- [`../_shared/references/westbrook-example.md`](../_shared/references/westbrook-example.md) - the
  canonical example model
- `../_shared/tools/` - the generators. `semantic_model`, `tmdl` and `pbip` are pure: they return
  strings and write nothing. `powerbi_model` and `parquet_tables` write the project and the files.
  Their tests run with `python -m pytest ../_shared/tools -q` and need neither EA nor Power BI.

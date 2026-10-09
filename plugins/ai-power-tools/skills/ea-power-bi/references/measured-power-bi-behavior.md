# Measured Power BI behavior

**None of this is to be re-derived.** Every figure and every failure here was measured against a
live Power BI, and most cost a working session to find. Where something was *not* isolated or *not*
run, this file says so - an unmeasured claim quoted as measured is worse than no claim.

| | |
|---|---|
| Power BI Desktop | **2.158.1177.0** (26.09), Store build, for the project-format and report-half facts (§3, §4). The Desktop build behind the later read-backs (§2) was not recorded |
| Dates | **2026-10-02** for the project-format facts; **2026-10-07/08** for the business-layer model |
| Model | Westbrook Bank, the reference model. Every figure belongs to it and is illustrative of the shape of a result, never what a customer should expect |
| How it was read back | the engine's own schema views over ADOMD, and DAX output compared with SQL Server joins. Not from screenshots |

---

## 1. Power BI's own relationship detection does not work here, and fails silently

An earlier 40-table build of the reference model was loaded with no relationships defined.
Auto-detect produced **63** relationships where the model needed **38**; **28** were invented from
shared enumeration values - two tables related because both happened to hold a data-classification
value - and a real relationship was switched off with no warning because two paths competed.
**Nothing in Power BI reports any of this.** The report looks finished.

This is the whole argument for generating the semantic model rather than letting it be inferred.

## 2. What the generated model does instead

Authored, then read back off the engine after the project was applied, on the Westbrook business
layer:

| Run | Mode | Tables | Relationships (active) | Engine = declared | Measures / row counts = SQL Server | Traversals = SQL joins |
|---|---|---|---|---|---|---|
| First read-back | Import | 51 | 83 (73) | 83/83 | 51/51 | 73/73 |
| First read-back | DirectQuery | 51 | 83 (73) | 83/83 | 51/51 | 73/73 (read-back took 3 min 10 s) |
| Re-run after the business layer settled | Import | 51 | 74 (68) | 74/74 | 51/51 | 68/68 |
| Live repository, counts only | Import | - | 79 | 79/79 | 54/54 | 72/72 |

**Zero undeclared deactivations in every model the engine loaded.** The relationship count follows
the model (entities, combinations, tag-row tables); it is not a constant. The inactive
relationships are the genuine self-links - one entity type as both source and target of a
combination - plus two between EA's own tables.

**One model holds both layers only one way round.** With the business layer filtering EA's tables,
all element-key links are active and the engine agrees on every relationship. With EA's tables
filtering the business layer, 11 of 18 links created a second path to a connector table, and the
engine **refused the project outright**: "ambiguous paths between 'Flows' and 't_object'". Hence the
generator's ambiguity check and the direction it fixes.

---

## 3. Three things that each stop the project loading

### A relationship cannot carry a description

A `///` line before `relationship` sets a `description` property. The relationship object has none,
so **the entire project fails to open** - not that relationship, the whole project:

```
There's a problem with the definition content in your Power BI Project.
Property 'description' is unknown and is not expected in the situation it appears.
```

**No file is named and no line number is given.** The inner exception is what identifies it, which
is why "Copy details to clipboard" matters. **Tables, columns and measures do take descriptions;
relationships do not.** The rationale for each relationship is carried in the model and
deliberately not rendered.

### A base theme is required, and it can be ours

Three opens of the same model, changing only the theme:

| `report.json` | Result |
|---|---|
| No theme collection, no resource packages | Model loads. **Report fails** - "Something went wrong / Failed to load the report", whose details are an activity id and nothing else |
| Theme block plus **Power BI's own** theme file | **Opens clean** |
| Theme block plus a **minimal theme of ours** - a name, six data colors, three defaults | **Opens clean** |

So the theme is required, and redistributing Microsoft's file is not. Our own theme is emitted as
part of the project. **Not isolated:** which part is strictly required - the theme collection, the
resource-packages entry, or the file on disk. All three were added together.

### The report half is stricter than the model half

- `reportVersionAtImport` as a **string** aborts the open with a precise message and Power BI loads
  **nothing**. It is an object: `{visual, report, page}`.
- A `report.json` carrying only `$schema` opens the semantic model but fails the report with an
  opaque activity id - and then **every save path crashes** on a null reference.

The working set is report schema `3.3.0`, the object form of `reportVersionAtImport`, the
resource-packages entry, and the referenced theme file actually present.

---

## 4. TMDL format rules that are not preferences

- **Tab-indented.** Spaces do not parse.
- **CRLF, UTF-8 without a BOM.** Read off a real project. A generated file that deviates is rejected.
- **Descriptions are `///` lines preceding** the object they describe.
- **A one-to-one relationship must carry `crossFilteringBehavior: bothDirections`** or Power BI
  rejects the file.
- **Power BI validates TMDL on apply and rejects the whole file on one violation.** Good for a
  generator, fatal for a hand edit.
- **Lineage tags are derived from each object's path**, so two runs over the same model produce
  byte-identical files.

**Not measured: whether a report's field bindings survive a lineage tag that genuinely changes.**

---

## 5. Measures, and the row that is not there

**`SUMMARIZECOLUMNS` drops rows where every measure is BLANK.** Measured on an earlier build of the
reference model: bare measures returned **65 of 145** rows; zero-filled variants returned all 145.
The measures in the current model are counts over a `Con_` table, which are BLANK where there are no
rows, so the same shape of problem applies: an entity with no connectors in that direction drops out
of a visual that shows only the measure.

Each inactive-relationship measure was compared with the SQL join it stands for, and the traversal
counts in §2 include them. A model that silently reuses the active relationship is wrong exactly on
the elements where the other end differs, and looks plausible; verifying that measures parse is not
verifying that they are right.

---

## 6. Hiding, and the table that will not hide

**Power BI keeps a hidden table visible when it hosts visible measures.** That is why the measures
sit on the `Con_` tables, which are visible, and never on EA's hidden tables. A synthetic one-row
measures table was rejected: it needs a constant partition.

**`SummarizationSetBy = Automatic` does not override an explicit `summarizeBy`** - 2026-10-05,
instrument `$SYSTEM.TMSCHEMA_COLUMNS` against the live engine. The annotation reads as a
contradiction beside an explicit setting, because it records that the *client* chose. It reported
`SummarizeBy = 2` (None) on all 235 real columns of that build, the INTEGER ones included; the 40
columns at `1` (Default) were Power BI's own `RowNumber` columns. Without the explicit
`summarizeBy: none`, a numeric tagged value falls to the default aggregation and the field list
offers a sum of something nobody asked to add up.

---

## 7. Parquet, and the connector

- **The format carries the schema, and that is the point.** The same all-text tables loaded through
  Excel arrived as `Column1...ColumnN`, because Power BI promotes row 0 to a header only when its
  types differ from the body. From Parquet the names and types were right on the first attempt with
  no Power Query step. A CSV fallback would hand back the defect the format was chosen to remove.
- **The Get Data connector takes one file per pass.** No folder option, no multi-select. Dozens of
  tables would be dozens of passes, which is why the Parquet is paired with a generated `.pbip`.
- Basic mode asks for a **URL** and accepted a local absolute path.
- **Power BI has no SQLite connector.** Checked against the Power Query connector index: Access,
  SQL Server, Oracle, MySQL, MariaDB, DB2 and ODBC are present; SQLite is not. No date was recorded
  for this check.
- **Types are declared** in the definition, never inferred from the data, so a refresh cannot
  change a column's type depending on which rows happen to be filled.
- **Untested: UNC and OneLake paths**, and ingestion by Fabric or Azure SQL.

---

## 8. The update path

With **"Detect and reload external PBIP changes"** enabled, Power BI noticed the files change on
disk and offered *Apply external changes*. A regenerated semantic model re-applies to an existing
project without rebuilding the report; the generator leaves the report folder alone, and a test
asserts that. It warns that unsaved in-app edits will be overwritten, so the generated files are the
source of truth. **The Power BI-side behavior was established in earlier research and has not been
re-run since the business-layer model replaced the earlier one.**

Opening a `.pbip` at all needs two preview features: the **`.pbip` save option** and **Store
semantic model using TMDL format**. Both were already on in the build this was measured against;
**the defaults have not been checked**, so confirm before promising.

---

## 9. Power BI Desktop session facts

Harness facts from the 2026-10-07/08 read-backs. They describe Desktop, not the model.

- **File > Open of a second project starts a new Power BI process.** Close the extra windows.
- **A process that has opened two projects holds two engine databases.** An ADOMD connection with no
  catalog reads the first; pass the catalog. One DirectQuery read-back read the wrong engine this
  way and was redone.
- **Wait for a project's initial load before refreshing.** A refresh started from the banner and the
  ribbon at the same time failed with "A cyclic reference was encountered during evaluation"; the
  same full refresh through the engine succeeded in 31 s. Treated as an overlapping-refresh
  artifact, **not re-tested in the interface**.
- A new session needed one refresh from the interface before an engine refresh was accepted.

---

## 10. What is not measured, and must not be implied

| | |
|---|---|
| **DirectQuery speed at scale** | The 3 min 10 s read-back is Westbrook's small model, run through the engine. DirectQuery on a live repository was not measured, and it queries the production database |
| **Volume** | Westbrook is small. The live repository run, about 80,000 rows, was measured for the reporting database build, not for Power BI query speed |
| **Power BI service refresh and gateway** | Untested |
| **Fabric, OneLake, Direct Lake, Azure SQL, lakehouse** | Untested. Do not claim. Do not use the phrase "medallion architecture" |
| **Lineage tags under change** | Stable by construction; never tested against a tag that changed |
| **Re-apply to an existing report** | The Power BI-side behavior was not re-run on the current model |
| **Jet (`.eapx`)** | Everything is measured against a SQLite-backed `.qea` and a cloud-connected repository |
| **Which part of the theme block is required** | Not isolated |

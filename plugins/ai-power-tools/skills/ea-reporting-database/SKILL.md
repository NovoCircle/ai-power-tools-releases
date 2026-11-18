---
name: ea-reporting-database
description: Build the reporting layer for a Sparx EA repository - business tables named and shaped by the technology that governs the model (one table per stereotype, one per allowed connector combination, a Table Directory) over EA's own tables - as SQL views inside the EA database, as a reporting database on SQL Server or in Microsoft Fabric, or as Parquet files that can go on into Microsoft Fabric, and prove it matches the repository. Use when someone wants to query, roll up, or report across a whole model rather than element by element, wants EA content in a database or files that an agent, a SQL client or Power BI can read, wants to choose what is reportable, or asks to keep the data fresh on a schedule. For Power BI specifically - a dataset, a .pbip, TMDL or a semantic model - build the layer here, then continue with ea-power-bi.
---

# A reporting layer from an EA repository

*Tools: `ea_repository(operation=..., params={...})` with `build_business_layer`, `check_business_layer`,
`build_reporting_database`, `replay_reporting_database`, `remove_business_layer`, `start_reporting_refresh`,
`get_reporting_refresh`; `ea_mdg(operation="get_mdg_from_runtime")`; `ea_analyze(operation="execute_sql")`
(AI Power Tools for Sparx EA, v3.6.4+); `../_shared/tools/`: the census modules, `parquet_tables.py`, `onelake_upload.py`*

**This skill writes to the model in two places, each only when the user chooses it and after a
baseline: applying a stereotype through the governance gate (§5.2), and fixing a connector bound to
no profile (§5.3).** Direct access (path A) creates views in their own schema inside the EA
database and never alters an EA table.

Run the `ea-start-here` preflight first - which repository is actually open, and which technologies
are actually loaded; a build against the wrong model is a wasted afternoon. EA must be running with
the repository open for every operation here except a replay (§6).

## 1. What this produces

The same tables on every path - names, columns, types and rows - so a report built on one path
works on another (the one exception is the one-row `Source` table, below):

| Tables | What they hold |
|---|---|
| **Entity tables** | One per element stereotype, named by the technology's alias (`Business Application`), or the stereotype name where there is no alias. Elements outside the technology that the inclusion choice (§2b) admits get a table per observed stereotype, named `... (not in MDG)` |
| **`Con_` tables** | One per allowed combination of source stereotype, connector stereotype and target stereotype - matching the technology's metamodel diagram one for one. Named `Con_<source table> <connector stereotype> <target table>`. Combinations outside the technology appear only when the inclusion choice admits them, marked `(not in MDG)` |
| **Tag-row tables** | Only where a column cannot hold the data: tags the technology does not declare, and declared tags that hold a list of element references. Everything else is a typed column on its entity or `Con_` table |
| **Table Directory** | One row per business table: its name, kind, stereotype, alias, description from the technology, and `primary_key` (the table's key columns, which Fabric needs on every table it exposes) |
| **`Source`** | One row, two columns: `source_id`, the repository's id from the profile (NULL when the profile sets none), and `source_row`, always 1, its key. A view or table on paths A and B; the Parquet tables file (path C) has no `Source` table, so on path C the id is `source.id` in the definition JSON only |
| **EA's physical tables** | The nine EA tables the business tables read (packages, objects, tagged values, connectors, connector tags, diagrams, diagram placements, attributes, operations), scoped to what the profile includes |

Column by column: [`references/the-schema.md`](references/the-schema.md).

## 2. The shape of the output

**Names are exactly the technology's.** No prefix stripping, no snake-casing: `Business
Application` is a table with a space in it, so quote it in SQL (`[logical].[Business Application]`).
Westbrook Bank's `WBA` technology is used for illustration throughout; substitute your own
technology, stereotypes and model.

**Every admitted element is in at least one entity table.** One carrying two of the technology's stereotypes
is genuinely two things and is in both tables, flagged at preflight and listed in the alignment
result. One carrying none the inclusion choice admits has no table: the gate (§5.2) reports it first.

**Every entity table has `package_path`**, so a report can slice by package, including entity
types with no tags.

**Excluded areas never appear.** The profile (§4) names packages to leave out; a link from kept
content into one ends at an `(excluded)` stub that shows the element type, never the name.

## 2b. The inclusion choice - settle this before the build steps

Before any extract, census the repository against the MDG and ask the user what the database
includes. Never decide it for them. Full detail:
[`references/the-inclusion-choice.md`](references/the-inclusion-choice.md); code:
`../_shared/tools/inclusion.py`.

1. **Census elements and connectors** over the scope, not the whole repository, with `ea_census`
   (`census_elements`, `census_connectors`), then `inclusion.analyze(...)`; inputs: reference §2.
2. **Stop on unbound connectors.** A connector whose stereotype is qualified text with no `FQName` is
   a data defect, not a gap. Show the fix (§5.3), baseline first, and re-run the census. No profile
   is produced until none remain.
3. **Flag elements with two declared stereotypes.** They are placed in both tables if the user
   continues; ask.
4. **Put the three-way question, with the counts** - every time a profile is created: (1) *only what
   my MDG defines*; (2) *everything in the repository*, keyed by observed stereotype, or metaclass
   where there is none; (3) *show me the gaps*: per gap (element stereotypes and connector keys, each
   with its count and an example name), include it, exclude it, or update the MDG to declare it.
   Updating the MDG is a hand-off to the MDG skills followed by a new census - not an answer.
5. **Record the answer** with `resolve_answer`: its `inclusion` goes into the scope profile and its
   `record()` beside it. A refresh calls `new_since_saved` and flags what is new, not deciding it.
6. **No one to answer (a scheduled or unattended run):** use the profile's saved `inclusion` and
   `inclusion_choice` as they are. If either is missing, stop, report the counts and ask. Never choose.

The choice changes what is built, and the governance gate of §5.2 lists what it leaves out. For
"only what my MDG defines" with the gate declined, the short route is
[`references/the-inclusion-choice.md`](references/the-inclusion-choice.md) §7.

## 3. Three paths, and how to choose

Where the business tables live is a fact about the customer's estate, not a preference. Put all
three to them, with the consequence of each attached, before building anything.

| | **Direct access (path A)** | **Reporting database (path B)** | **Parquet files (path C)** |
|---|---|---|---|
| For whom | Can reach the EA database and may create views in it | Has no direct database access (a cloud connection, for example) and can run SQL Server or has a Fabric capacity | Has no direct database access and no database to run |
| Where the business tables are | SQL views in their own schema inside the EA database. EA's tables reach Power BI through scoped views in the same schema | SQL views in a separate reporting database, on SQL Server or a SQL database in Microsoft Fabric (§3b), that AI Power Tools fills with a copy of EA's tables, read over COM | One Parquet file per table in a folder. AI Power Tools writes the rows as JSON; the local step in `ea-power-bi` writes the files |
| Profile `target.kind` | `ea_database` | `reporting_database` | `parquet` |
| Data | Live: the views read EA's tables as they stand | A snapshot. A refresh loads the new rows in place when no table's shape changed, and swaps the tables in on a first build or a changed shape (§8) | A snapshot, rewritten on every refresh |
| Needs | SQL Server. The Windows account running AI Power Tools needs `CREATE SCHEMA`, `CREATE VIEW` and `SELECT` on EA's tables | SQL Server and a Windows account allowed to create the reporting database, or a SQL database in Fabric and a person to sign in (§3b). EA running with the repository open | `pyarrow` for the local step. EA running with the repository open. To go on into Fabric: the Azure CLI, signed in, and a mirrored database (§3c) |
| Preflight | No preflight operation: the rights are checked first, and the §2b census finds unbound connectors | Yes (§5.3) | Yes (§5.3) |
| Kept extract (§6) | None - there is no extract | Yes | Yes |

**How to choose, in order:**

1. *Can you reach the EA database directly, is it SQL Server, and may you create views in it?*
   Then direct access. State the cost: the views live in the production database, and Power BI in
   DirectQuery queries it; its speed at the scale of a large repository is not measured.
2. *If not, can you run a SQL Server, or do you have a Microsoft Fabric capacity?* Then the
   reporting database (§3b): a snapshot, and queries never touch the production database.
3. *If not, Parquet.* No database anywhere. Power BI Desktop imports the files. It is a snapshot; with a Fabric capacity they can go on into a mirrored database (§3c).

Someone with direct access may still choose B or C - to keep views out of the production database,
or to leave areas out of what Power BI can see. All three paths support leaving packages out (§4).

**Direct access needs SQL Server; the reporting database, SQL Server or a SQL database in Fabric.**
Any other database type fails to connect (the symptom is a `cannot connect to database` error);
nothing is written.

## 3b. Where the reporting database runs

| Target | What it needs | `target.authentication` |
|---|---|---|
| **SQL Server** you run | A Windows account allowed to create the database; a missing one is created | `windows` (the default) |
| **A SQL database in Microsoft Fabric** | A Fabric capacity. Create the database in the Fabric portal first; take the server and database names from its connection strings (the database name is not the display name) | `entra-interactive` |
| **Azure SQL Database** | Expected to work with the same sign-in; **not measured** | `entra-interactive` |

Microsoft Entra sign-in needs AI Power Tools for Sparx EA 3.6.4 or later.

**A person completes the sign-in**, once per server process, in Microsoft's sign-in window; a restart or
an expired sign-in shows it again, and unanswered for about ten minutes the operation stops and writes
nothing. No unattended sign-in to the database: a scheduled refresh needs someone there when the server
first connects.

**Power BI** imports it; a published model refreshes with **no gateway**, using OAuth2 (`ea-power-bi`
§6). For Direct Lake, or for tables copied to OneLake, see §3c. Detail, with what was measured:
[`references/the-cloud-database.md`](references/the-cloud-database.md).

## 3c. Reaching Microsoft Fabric

Fabric needs tables, not views. Three routes put the business layer there (server parts: 3.6.6 or later); steps and
measurements: [`references/the-cloud-database.md`](references/the-cloud-database.md) §5 to §7. Measured on Westbrook Bank, Fabric trial, 13 Nov 2026, a small model: say what was and was not.

| Route | What it does | Measured | Not measured |
|---|---|---|---|
| **Path C into a mirrored database (Open Mirroring)** | `parquet_tables.py --layout open-mirroring`, then `onelake_upload.py`, which waits for Fabric to apply every table and reframes the Direct Lake model once. Sign-in is through the Azure CLI: a person's cached sign-in, or the CLI signed in as a service principal by the customer's administrator; the tool never asks for or stores a secret. **Tell the customer to turn off "Keep your Direct Lake data up to date" once, when they publish the model** (semantic model settings, Refresh): with it on, Fabric reframes table by table and a report can show two refreshes mixed for a few minutes. Microsoft documents that setting only in the portal, and a reader of the SQL analytics endpoint can still see the mix | Three refreshes: 40 tables, exact names, counts equal to the build, 57 deletes applied, the wait about 2 to 3.5 minutes, a Direct Lake model reading all 40; with automatic updates off, the model held the previous refresh until the single reframe | A service principal's sign-in; a person's cached sign-in lasting the weeks a schedule needs |
| **Path B into a SQL database in Fabric, `target.output` `tables` or `script`** | `tables`: keyed business tables in `dbo`, which Fabric copies to OneLake. `script`: no business tables; the views, two scope tables and `<profile>.fabric-views.sql` for a SQL analytics endpoint | Built and tested on a local SQL Server, then in Fabric (16 Nov 2026): `tables`, two builds (swap, then in place), `check_business_layer` aligned (1008 cells, 0 differences), the business tables copied to OneLake and a Direct Lake model reading all 31 with counts equal to the build; `script`, 36 views created on the SQL analytics endpoint, none refused, the 32 business views matching the tables cell for cell (1551 cells, 0 differences); `check_business_layer` against the endpoint also matched (1008 cells, 0 differences), and a DirectQuery model over it matched on all 31 | A service principal's sign-in |
| **Path B on a local SQL Server, mirrored into Fabric** | Needs Standard, Enterprise or Developer edition and an on-premises data gateway. The in-place refresh (§8) keeps the mirror alive | Refreshes two and three made no structural change. Then in Fabric (16 Nov 2026), through an on-premises data gateway: the mirror stayed healthy across three refreshes, each in place, every mirrored table equal to the local counts after each (applied in about 2 to 7 minutes). Setup needs `db_owner` for the mirror login, a sysadmin to enable change data capture, a database owner the server can resolve, and a primary key on every table (`references/the-cloud-database.md`). The test turned encryption off for a self-signed certificate; use a trusted certificate and keep it on | A service principal's sign-in; a person's cached sign-in lasting the weeks a schedule needs |

## 4. The profile

Everything the build needs is in one saved profile, a JSON file the user keeps. Every refresh
reuses it. Illustration with Westbrook Bank's `WBA` technology; substitute your own:

```json
{"technology": "WBA", "source_id": "westbrook-bank",
 "scope": {"roots": ["{11111111-2222-3333-4444-555555555555}"],
           "exclude": ["{66666666-7777-8888-9999-000000000000}"]},
 "inclusion": {"observed_elements": [], "observed_connectors": []},
 "target": {"kind": "reporting_database", "server": "<sql-server>\\<instance>",
            "database": "EAReporting", "schema": "logical"}}
```

**Propose the repository's id before you write the profile:** a slug of the repository name (rule and example:
[`references/the-profile.md`](references/the-profile.md)). Show it and ask the person to confirm or change it; never write a guess silently. Write the confirmed
value as `"source_id"` before the first build. A profile without one still builds; when a result carries the `source_id` warning, relay it, offer to add one, and add
it only once the person confirms. The parts, and the scope rules (no masking; list every root package you do not want in `scope.exclude`, or it is flagged on every
run; a stale exclusion is flagged): [`references/the-profile.md`](references/the-profile.md). **Before choosing `roots`, look at the top-level package layout and ask
whether any subtree describes the modeling language rather than the estate** (a metamodel or pattern library, documented with the same stereotypes). The census
cannot tell it from model content, because it reads the stereotype an element carries, not where the element sits. Scoping is the only remedy. Package GUIDs come
from `execute_sql`: `SELECT ea_guid, Name, Parent_ID FROM t_package`. Paste `resolve_answer(...).inclusion` into `inclusion` and `answer.record()` into
`inclusion_choice`: without that record a refresh cannot flag drift. A reporting-database build refuses a database that holds an EA repository's own tables. For a
cloud database, `target` adds `"authentication": "entra-interactive"` and `"user"`, the account the sign-in window suggests (needed with Microsoft's OLE DB Driver
18, which refuses an interactive sign-in without it, measured 13 Nov 2026); `user` with `windows`, or Entra on path A, is refused. Path B also takes `"output"`
(§3c).

## 5. The build, step by step

### 5.1 Get the technology definition

```
ea_mdg(operation="get_mdg_from_runtime", params={"tech_id": "<id>"})
```

This supplies the aliases, descriptions and declared types the §2b census compares against. Check
`source` in the response: `"live"` means EA answered from the loaded technology, as wanted. If the
operation declines, go back to the `ea-start-here` preflight. A repository with no technology loaded
has no metamodel to build a business layer from; say so. Then run the §2b census, settle the
inclusion choice, and write the profile (§4).

### 5.2 The governance gate - run this before you build anything

An element the inclusion choice leaves without a table is in no entity table. Ask before you
build: a customer must not discover it by failing to find a system.

```python
declared = declared_shapes(mdg)
findings = assess(find_ungoverned(elements, tags, inclusion=profile["inclusion"], declared=declared),
                  declared, elements)
print(format_report(findings))   # imports and row mapping: see the reference
```

Show the report; they decide per element. Four outcomes, **not interchangeable**:

| Outcome | What to say |
|---|---|
| `ranked` | One candidate is backed by package evidence the others are not. Offer it **with the reason**, never as certain |
| `single_candidate` | One stereotype could apply and nothing confirms it: "one candidate, not confirmed". Name it and ask |
| `unrankable` | Nothing separates the candidates, or the element's tags rule every one out. List them and ask. **Do not pick one** |
| `no_candidate` | The technology extends no stereotype for that metaclass. Offer to extend it (`ea-mdg-model-build`), or accept the exclusion. Never invent a suggestion |

To apply one, pass the **bare** stereotype name via `update_element` - EA resolves it against
the loaded technology and writes the fully-qualified form itself. **Take a baseline first**
(`ea-change-management`): this and the connector fix of §5.3 are the only steps in this skill that
write to the model. With no one to ask (§2b), apply nothing: report the list and carry on.

If the customer declines - a valid answer - say plainly which elements will not be in the layer and
carry on. Call, row mapping, precondition, verification: [`references/the-governance-gate.md`](references/the-governance-gate.md).

### 5.3 Preflight - paths B and C

```
ea_repository(operation="build_reporting_database", params={"profile_path": "<profile>.json", "preflight_only": true})
```

Reads EA's tables over COM, applies the scope, and **writes nothing**. It reports the rows extracted
and kept, the crossings (links from kept content into an excluded area) and the `(excluded)` stubs
they need, then two lists; each entry is explained in
[`references/the-preflight.md`](references/the-preflight.md):

- **`blocking` - stop.** A connector whose stereotype is qualified text with no binding to the
  technology (`connector_stereotype_unbound`). Two routes to the same fix, **baseline first**:
  `update_connector` with `StereotypeEx` set to the technology's qualified name, or re-apply the
  stereotype in EA (toolbox, or Properties > Stereotype). Then run the preflight again. Do **not**
  build while this list is non-empty, on either path.
- **`flags` - show, then ask.** Elements carrying two of the technology's stereotypes (each is in
  both tables if the user continues), a new root left out, an entry that matches nothing, and
  elements with two same-named tags (the layer shows the first).

### 5.4 Build

| Path | Call | What it does |
|---|---|---|
| A | `build_business_layer` with `profile_path` | Checks the rights first and, if any is missing, names it and **changes nothing**. Otherwise recreates the business views and the scoped views of EA's tables in the profile's schema inside one transaction. Never alters an EA table |
| B | `build_reporting_database` with `profile_path` | Extracts EA's tables over COM in id ranges, cuts the excluded packages, keeps links across the cut with an `(excluded)` stub at the far end, then loads the reporting database inside one transaction (a reader never sees a partial database): in place when every table already has the current shape, otherwise by loading a staging schema with EA's own indexes and swapping it in (§8). Then builds the business views (and, with `output` `tables` or `script`, the tables (`tables`) or the scope tables and script (`script`) of §3c). Keeps the post-cut extract (§6) |
| C | `build_reporting_database` with `profile_path` | The same extract and cut; computes the business tables' rows and writes them as JSON in `<profile>.tables.json`, next to the profile. Keeps the post-cut extract. **Writing the Parquet files is a separate local step** - `ea-power-bi` |

Every build also writes the **definition** - tables, columns, types, row counts, descriptions -
as `<profile>.definition.json` beside the profile (`definition_path` overrides it); `ea-power-bi`
generates the Power BI project from it. Its top-level keys are `technology`, `source` (which carries `id`, the profile's `source_id`, or null), `entities`, `connectors`, `tag_row_tables`, `directory` and `physical`, and on paths A and B `source_table` (`name`, `rows`, `all_columns`, `primary_key`). **Every build is a full rebuild with no history**: anything
deleted or moved in EA follows, and a failed or stopped build leaves the previous data live. The
result returns row counts per table, the flags, the alignment summary and timings, and on a reporting
database `load_mode`, `ddl` and `load_reason` (§8). It also returns `source_id` and, when the profile sets none, a `warnings` entry: relay the warning and offer to add the id to the profile. On paths B and C an optional `new_tag_spellings` key appears only when a tag spelling was seen for the first time (§6); relay it. `check_business_layer`, `replay_reporting_database` and `remove_business_layer` return `source_id` and the warning too. Read the timings
aloud: they are the only sizing evidence the customer has (§11).

### 5.5 Check

```
ea_repository(operation="check_business_layer", params={"profile_path": "<profile>.json"})
```

Changes nothing. Paths A and B (a Parquet profile has no views to check; its build returns the
same alignment summary). Two checks:

1. **Alignment with the metamodel**, in counts: every allowed combination has a table; every
   profile-bound connector whose two ends are placed lands in a combination, none outside one; every
   admitted element is in at least one entity table, and every element in two was flagged at
   preflight; each connector table's rows equal the definition's own placement. `alignment.aligned`
   is the verdict. It is false when any of those counts is non-zero, so a build whose only finding is
   connectors outside every allowed combination reads false while being correct; read `references/troubleshooting.md` first.
2. **Values** (`include_values`, on by default): every name, `package_path`, tag column, connector
   end, base type and connector tag against an **independent read through EA**: `cells` and
   `differences`, zero differences the verdict. The open repository must be the one built from.

**A check that read nothing is a failure, never a pass.** `cells: 0` means nothing was compared;
say so rather than reporting zero differences.

## 6. The kept extract, and replay

After every build on paths B and C, the **post-cut extract** - the rows loaded, stubs included, with
the scope, row counts, issued queries and run id - is kept as `<profile>.extract.json` beside the
profile and **replaces the previous run's**: no history. The extract also records the spelling each tag column was first given. A later refresh keeps that column name even when another spelling of the same tag appears (tag names that differ only by case share one column); the result lists each such spelling in `new_tag_spellings` (the column and the new spelling). Tell the person: the values spelled the new way are in the existing column, and no report column was renamed. Direct access has no extract and returns no `new_tag_spellings`.

**Excluded content is never written to disk, at any stage**: the raw extract holds the areas the
user left out, so it is not kept. The kept extract holds what the user chose to include; treat it
with the same care as the reporting data. Direct access has no extract.

```
ea_repository(operation="replay_reporting_database", params={"profile_path": "<profile>.json"})
```

Rebuilds the reporting database (B) or the Parquet rows (C) from the kept extract **with no EA
connection**, identically to the original build: to retest a fix to the transform, or settle a
disputed figure against the exact rows. The result carries `replayed_from`. [`references/the-kept-extract.md`](references/the-kept-extract.md).

## 7. Removing the business layer

```
ea_repository(operation="remove_business_layer", params={"profile_path": "<profile>.json"})
```

Drops every view in the profile's schema, then the schema, and reports the views dropped. On
direct access that is all of AI Power Tools' footprint in the EA database. EA's own tables, and a
reporting database's copied tables, are not touched; the tables a `tables` or `script` build made go with the views.

**Say this before removing: a Power BI project built on the layer stops refreshing**, in Desktop and
the service, until the layer is rebuilt from the saved profile - `build_business_layer` (A),
`build_reporting_database` or `replay_reporting_database` from the kept extract (B). Keep the profile.

## 8. Keeping it fresh: the refresh

Call `start_reporting_refresh` with `profile_path`, then poll `get_reporting_refresh` with the run id until it says `succeeded` or `failed` (run ids last until the server restarts). What a refresh does on each path, the Path C steps into Fabric, scheduling and the drift flags: [`references/the-refresh.md`](references/the-refresh.md). Read it before running a refresh.

**A failed run, or one stopped by its preflight (B, C), leaves the previous data live** and says why. **Scheduling is an AI agent's job, never Windows Task Scheduler**, and EA must be running with the repository open on that machine. A refresh uses the saved inclusion choice, flags drift (`not_covered_by_inclusion_choice`, `mdg_version_changed`) and does not ask again: show the flags and re-run §2b.

## 9. Reporting the result

Say these four things, in this order, and do not bury the third:

1. **Which path**, and whether the data is live (A) or a snapshot with its as-of time (B, C).
2. **Checked or not**: `alignment.aligned` and, on A and B, `cells` and `differences`.
3. **What is outside the layer**: packages excluded, elements the inclusion choice left out, the
   `(excluded)` stubs, and every preflight flag the user continued past - before anyone compares a
   table count against EA's own.
4. **What was built**: the tables, row counts, the definition file, and the timings measured here.

Never report a figure from a table without saying how populated the columns behind it are: count
the non-empty values yourself. A roll-up over a partly-populated tag is a confident wrong number.

To let a Claude Cowork or other cloud session read the results, put them in one `<output-folder>` and connect that folder, not the folder that holds the model file. That session can read the files but cannot change the model, because the server is not available in cloud sessions today. The folder holds the Parquet
files, profile and definition file.

## 10. Rules that are not obvious

The five that cost the most; the full list is in [`references/the-schema.md`](references/the-schema.md) §8.

- **Join a connector to its ends by GUID**: `source_guid` and `target_guid` are entity `ea_guid`s.
  A combination with the same entity type at both ends is a self-join; name both sides.
- **An element in two tables is counted twice by design**, and so is a connector ending at it.
- **A text tag holding several values is one value in its column.** `GLBA, FFIEC` matches `LIKE`, not `=`.
- **A blank is a blank**: EA writes NULL and empty text identically.
- **A check that read nothing is a failure.** `cells: 0` compared nothing.

## 11. Known limits

- **SQL Server** for direct access; **SQL Server or a SQL database in Fabric** for the reporting database (Azure SQL Database expected, not measured). Other types fail to connect.
- **DirectQuery on direct access queries the production database.** Its speed at the scale of a
  large repository is not measured. Measured on one model, and not what a customer should expect: a
  repository of about 80,000 rows through a cloud connection took 10-11 s to extract, 38-46 s to
  load, under 1 s to swap in, and about 2 minutes for a full reporting-database refresh.
- **Sign-in**: the Windows account running AI Power Tools, or for a reporting database a Microsoft Entra sign-in a person completes (§3b). No unattended Entra sign-in to a database. The OneLake upload signs in through the Azure CLI instead (§3c).
- **Only a RefGUIDList tag is split into a tag-row table.** A CheckList tag stays a column (`1,1,0`).
- **`.eapx` (Jet) repositories are untested.** Measured on a local `.qea` and a cloud-connected repository.
- **No masking.** Exclusion is by whole package.

## 12. When it goes wrong

A call that appears to hang is usually a modal dialog in EA holding the COM connection: look at EA's
screen before retrying. Every error code (`missing_rights`, `preflight_blocked`, `target_is_an_ea_repository`,
`wrong_path`), a failed Microsoft Entra sign-in, a missing cloud database, a build that is not
`aligned`, a later spot-check off by a few rows: [`references/troubleshooting.md`](references/troubleshooting.md).

## Reference files

- [`references/the-schema.md`](references/the-schema.md) - every table kind and its columns;
  [`references/the-profile.md`](references/the-profile.md) - the profile's parts and scope rules
- [`references/troubleshooting.md`](references/troubleshooting.md) - symptoms, causes, fixes;
  [`references/the-cloud-database.md`](references/the-cloud-database.md) - a SQL database in Fabric, the Entra sign-in, and the three routes into Fabric
- [`references/the-kept-extract.md`](references/the-kept-extract.md) - the kept extract, and replay;
  [`references/the-inclusion-choice.md`](references/the-inclusion-choice.md) - the three-way choice, its counts, and the refresh;
  [`references/the-refresh.md`](references/the-refresh.md) - the refresh on each path, Fabric, scheduling;
  [`references/the-governance-gate.md`](references/the-governance-gate.md) - the pre-build gate;
  [`references/the-preflight.md`](references/the-preflight.md) - the preflight's lists
- [`../ea-power-bi/SKILL.md`](../ea-power-bi/SKILL.md) - the Power BI project and the Parquet step
- [`../_shared/references/ea-ui-verification.md`](../_shared/references/ea-ui-verification.md) - the modal-dialog trap
- [`../_shared/references/westbrook-example.md`](../_shared/references/westbrook-example.md) - the canonical example model
- `../_shared/tools/` - the census modules `ea_census.py`, `inclusion.py` and `governance_gap.py`.
  Their tests run with `python -m pytest ../_shared/tools -q` and need no EA.

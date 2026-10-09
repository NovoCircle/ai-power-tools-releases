---
name: ea-reporting-database
description: Build the reporting layer for a Sparx EA repository - business tables named and shaped by the technology that governs the model (one table per stereotype, one per allowed connector combination, a Table Directory) over EA's own tables - as SQL views inside the EA database, as a SQL Server reporting database, or as Parquet files, and prove it matches the repository. Use when someone wants to query, roll up, or report across a whole model rather than element by element, wants EA content in a database or files that an agent, a SQL client or Power BI can read, wants to choose what is reportable, or asks to keep the data fresh on a schedule. For Power BI specifically - a dataset, a .pbip, TMDL or a semantic model - build the layer here, then continue with ea-power-bi.
---

# A reporting layer from an EA repository

*Tools: `ea_repository(operation=..., params={...})` with `build_business_layer`,
`check_business_layer`, `build_reporting_database`, `replay_reporting_database`,
`remove_business_layer`, `start_reporting_refresh`, `get_reporting_refresh`;
`ea_mdg(operation="get_mdg_from_runtime")`; `ea_analyze(operation="execute_sql")` (AI Power Tools
for Sparx EA, v3.6.0+); the census modules in
`../_shared/tools/`*

**This skill changes the model only through the governance gate's stereotype application (§5.2),
and only when the user chooses it.** Direct access (path A) creates views in their own schema
inside the EA database and never alters an EA table.

Run the `ea-start-here` preflight first - which repository is actually open, and which
technologies are actually loaded. Both answers change the output, and a build against the wrong
model is a wasted afternoon. EA must be running with the repository open for every operation here
except a replay (§6).

---

## 1. What this produces

The same tables on every path - names, columns, types and rows - so a report built on one path
works on another:

| Tables | What they hold |
|---|---|
| **Entity tables** | One per element stereotype, named by the technology's alias (`Business Application`), or the stereotype name where there is no alias. Elements outside the technology that the inclusion choice (§2b) admits get a table per observed stereotype, named `... (not in MDG)` |
| **`Con_` tables** | One per allowed combination of source stereotype, connector stereotype and target stereotype - matching the technology's metamodel diagram one for one. Named `Con_<source table> <connector stereotype> <target table>`. Combinations outside the technology appear only when the inclusion choice admits them, marked `(not in MDG)` |
| **Tag-row tables** | Only where a column cannot hold the data: tags the technology does not declare, and declared tags that hold a list of element references. Everything else is a typed column on its entity or `Con_` table |
| **Table Directory** | One row per business table: its name, kind, stereotype, alias, description from the technology |
| **EA's physical tables** | The nine EA tables the business tables read (packages, objects, tagged values, connectors, connector tags, diagrams, diagram placements, attributes, operations), scoped to what the profile includes |

Column by column: [`references/the-schema.md`](references/the-schema.md).

---

## 2. The shape of the output

**Names are exactly the technology's.** No prefix stripping, no snake-casing: `Business
Application` is a table with a space in it, so quote it in SQL (`[logical].[Business Application]`).
Westbrook Bank's `WBA` technology is used for illustration throughout; substitute your own
technology, stereotypes and model.

**Every admitted element is in at least one entity table.** One carrying two of the technology's stereotypes
is genuinely two things and is in both tables, flagged at preflight and listed in the alignment
result. An element carrying none of the stereotypes the inclusion choice admits has no table - the
governance gate (§5.2) reports those before the build.

**Every entity table has `package_path`**, so a report can slice by package, including entity
types with no tags.

**Excluded areas never appear.** The profile (§4) names packages to leave out; a link from kept
content into one ends at an `(excluded)` stub that shows the element type, never the name.

---

## 2b. The inclusion choice - settle this before the build steps

Before any extract, census the repository against the MDG and ask the user what the database
includes. Never decide it for them. Full detail:
[`references/the-inclusion-choice.md`](references/the-inclusion-choice.md); code:
`../_shared/tools/inclusion.py`.

1. **Census elements and connectors** over the scope, not the whole repository, with `ea_census`
   (`census_elements`, `census_connectors`), then `inclusion.analyze(...)`; inputs: reference §2.
2. **Stop on unbound connectors.** A connector whose stereotype is qualified text with no `FQName` is
   a data defect, not a gap. Show the fix the analysis suggests (bind it to the MDG's own stereotype,
   or clear it; baseline first) and re-run the census. No profile is produced until none remain.
3. **Flag elements with two declared stereotypes.** They are placed in both tables if the user
   continues; ask.
4. **Put the three-way question, with the counts** - every time a profile is created:
   1. *Only what my MDG defines.*
   2. *Everything in the repository*, keyed by observed stereotype, or metaclass where there is none.
   3. *Show me the gaps*: per gap (element stereotypes and connector keys, each with its count and an
      example name), include it, exclude it, or update the MDG to declare it. Updating the MDG is a
      hand-off to the MDG skills followed by a new census - not an answer.
5. **Record the answer** with `resolve_answer`: its `inclusion` goes into the scope profile and its
   `record()` beside it. A refresh calls `new_since_saved` and flags what is new instead of
   deciding it.

This changes what is built, not the governance gate of §5.2, which still applies to elements that
carry no stereotype.

---

## 3. Three paths, and how to choose

Where the business tables live is a fact about the customer's estate, not a preference. Put all
three to them, with the consequence of each attached, before building anything.

| | **Direct access (path A)** | **Reporting database (path B)** | **Parquet files (path C)** |
|---|---|---|---|
| For whom | Can reach the EA database and may create views in it | Has no direct database access (a cloud connection, for example) and can run SQL Server | Has no direct database access and no database to run |
| Where the business tables are | SQL views in their own schema inside the EA database. EA's tables reach Power BI through scoped views in the same schema | SQL views in a separate SQL Server reporting database that AI Power Tools fills with a copy of EA's tables, read over COM | One Parquet file per table in a folder. AI Power Tools writes the rows as JSON; the local step in `ea-power-bi` writes the files |
| Profile `target.kind` | `ea_database` | `reporting_database` | `parquet` |
| Data | Live: the views read EA's tables as they stand | A snapshot, rebuilt in full on every refresh | A snapshot, rewritten on every refresh |
| Needs | SQL Server. The Windows account running AI Power Tools needs `CREATE SCHEMA`, `CREATE VIEW` and `SELECT` on EA's tables | SQL Server, and a Windows account allowed to create the reporting database. EA running with the repository open | `pyarrow` for the local step. EA running with the repository open |
| Preflight | No preflight operation: the rights are checked first, and the §2b census finds unbound connectors | Yes (§5.3) | Yes (§5.3) |
| Kept extract (§6) | None - there is no extract | Yes | Yes |

**How to choose, in order:**

1. *Can you reach the EA database directly, is it SQL Server, and may you create views in it?*
   Then direct access is available. State the cost: the views live in the production database, and
   Power BI in DirectQuery queries that database. Its speed at the scale of a large repository is
   not measured.
2. *If not, can you run a SQL Server for the reporting database?* Then the reporting database. EA's
   tables are copied into it, so queries never touch the production database; it is a snapshot.
3. *If not, Parquet.* No database anywhere. Power BI Desktop imports the files. It is a snapshot.

Someone with direct access may still choose the reporting database or Parquet - to keep views out
of the production database, or to leave areas out of what Power BI can see. All three paths
support leaving packages out (§4).

**SQL Server only for direct access and for the reporting database.** Any other database type is
refused with a message; nothing is written.

---

## 4. The profile

Everything the build needs is in one saved profile, a JSON file the user keeps. Every refresh
reuses it. Illustration with Westbrook Bank's `WBA` technology; substitute your own:

```json
{
  "technology": "WBA",
  "scope": {
    "roots": ["{11111111-2222-3333-4444-555555555555}"],
    "exclude": ["{66666666-7777-8888-9999-000000000000}"]
  },
  "inclusion": {"observed_elements": [], "observed_connectors": []},
  "target": {"kind": "reporting_database", "server": "<sql-server>\\<instance>",
             "database": "EAReporting", "schema": "logical"}
}
```

The parts, and the scope rules (no masking; list every root package you do not want in `scope.exclude`,
or it is flagged on every run; a stale exclusion is flagged): [`references/the-profile.md`](references/the-profile.md). Package GUIDs come from
`execute_sql`: `SELECT ea_guid, Name, Parent_ID FROM t_package`. Paste `resolve_answer(...).inclusion`
into `inclusion` and `answer.record()` into `inclusion_choice`: without that record a refresh cannot flag drift. A reporting-database build refuses a database that holds an EA repository's own tables.

---

## 5. The build, step by step

### 5.1 Get the technology definition

```
ea_mdg(operation="get_mdg_from_runtime", params={"tech_id": "<id>"})
```

This supplies the aliases, descriptions and declared types the §2b census compares against. Check
`source` in the response: `"live"` means EA answered from the loaded technology, which is what you
want. If the operation declines, go back to the `ea-start-here` preflight rather than proceeding.
A repository with no technology loaded has no metamodel to build a business layer from; say so.

Run the §2b census, settle the inclusion choice, and write the profile (§4) before the next step.

### 5.2 The governance gate - run this before you build anything

An element carrying no stereotype the inclusion choice admits lands in no entity table. Ask before
you build, not after - a customer must not discover it by failing to find a system.

```python
findings = assess(find_ungoverned(elements, tags), declared_shapes(mdg), elements)
print(format_report(findings))   # imports and row mapping: see the reference
```

Show the report and let them decide per element. Three outcomes, **not interchangeable**:

| Outcome | What to say |
|---|---|
| `ranked` | One candidate is backed by evidence the others are not. Offer it **with the reason**, never as certain |
| `unrankable` | Nothing separates the candidates. List them and ask. **Do not pick one** |
| `no_candidate` | The technology extends no stereotype for that metaclass. Offer to extend it (`ea-mdg-model-build`), or accept the exclusion. Never invent a suggestion |

To apply one, pass the **bare** stereotype name via `update_element` - EA resolves it against
the loaded technology and writes the fully-qualified form itself. **Take a baseline first**
(`ea-change-management`): this is the only step in this skill that writes to the model.

If the customer declines, say plainly which elements will not be in the reporting layer and carry
on - declining is a valid answer. The call, row mapping, loaded-technology precondition and
verification: [`references/the-governance-gate.md`](references/the-governance-gate.md).

### 5.3 Preflight - paths B and C

```
ea_repository(operation="build_reporting_database",
              params={"profile_path": "<profile>.json", "preflight_only": true})
```

Reads EA's tables over COM, applies the scope, and **writes nothing**. The result reports the
rows extracted and the rows that would be kept, the crossings (links from kept content into an
excluded area, by kind: connector, diagram placement, classifier, parent, or a tagged value that
names an excluded element) and the `(excluded)` stubs they need, then two lists:

- **`blocking` - stop.** A connector whose stereotype is stored as qualified text with no binding
  to the technology (`connector_stereotype_unbound`). The result carries the fix: in EA, re-apply
  the stereotype from the technology's toolbox, or through Properties > Stereotype, so it is bound;
  then run the preflight again. Take a baseline first. Do **not** build while this list is
  non-empty, on either path.
- **`flags` - show, then ask.**
  - `element_multiple_declared_stereotypes`: elements carrying two of the technology's
    stereotypes. If the user continues, each is in both tables. The fix is to remove the extra
    stereotype in EA if it is a mistake.
  - `new_root_left_out`: a root package created since the profile was saved. It is not included
    until the user adds it.
  - `profile_entry_matches_nothing`: an exclusion (or root) naming a package that no longer exists.
  - `duplicate_tag_names`: elements with two same-named tags; the layer shows the first.

### 5.4 Build

| Path | Call | What it does |
|---|---|---|
| A | `build_business_layer` with `profile_path` | Checks the rights first and, if any is missing, names it and **changes nothing**. Otherwise recreates the business views and the scoped views of EA's tables in the profile's schema inside one transaction. Never alters an EA table |
| B | `build_reporting_database` with `profile_path` | Extracts EA's tables over COM in id ranges, cuts the excluded packages, keeps links across the cut with an `(excluded)` stub at the far end, loads a staging schema with EA's own indexes, **swaps it in inside one transaction** (a reader never sees a partial database), then builds the business views. Keeps the post-cut extract (§6) |
| C | `build_reporting_database` with `profile_path` | The same extract and cut; computes the business tables' rows and writes them as JSON, next to the profile. Keeps the post-cut extract. **Writing the Parquet files is a separate local step** - `ea-power-bi` |

Every build also writes the **definition** - tables, columns, types, row counts, descriptions -
as `<profile>.definition.json` beside the profile (`definition_path` overrides it). `ea-power-bi`
generates the Power BI project from it; nothing else re-derives the shape.

**Every build is a full rebuild with no history.** Anything deleted or moved in EA follows. A
failed or stopped build leaves the previous reporting data live.

The result returns row counts per table, the flags, the alignment summary and timings. Read the
timings aloud: they are the only sizing evidence the customer has (§11).

### 5.5 Check

```
ea_repository(operation="check_business_layer", params={"profile_path": "<profile>.json"})
```

Changes nothing. Paths A and B (a Parquet profile has no views to check; its build returns the
same alignment summary). It checks two things:

1. **Alignment with the metamodel**, in counts: every allowed combination has a table; every
   profile-bound connector whose two ends are placed lands in a combination, none outside one;
   every admitted element is in at least one entity table, and every element in two was flagged
   at preflight; each connector table's rows equal the definition's own placement.
   `alignment.aligned` is the verdict; if it is false, read `references/troubleshooting.md` first.
2. **Values** (`include_values`, on by default): every name, `package_path`, tag column,
   connector end, base type and connector tag compared against an **independent read through
   EA**. It returns `cells` and `differences`; zero differences is the verdict. The open
   repository must be the one the views were built from.

**A check that read nothing is a failure, never a pass.** `cells: 0` means nothing was compared.
Say so rather than reporting zero differences.

---

## 6. The kept extract, and replay

After every build on paths B and C, the **post-cut extract** - the rows that were loaded, stubs
included, with the scope, row counts, issued queries and run id - is kept as `<profile>.extract.json`
beside the profile, and **replaces the previous run's**. Only the last run is kept: no history.

- **Excluded content is never written to disk, at any stage.** The raw extract holds the areas the
  user left out, so it is not kept.
- The kept extract holds what the user chose to include, so treat it with the same care as the
  reporting data itself.
- Direct access has no extract.

```
ea_repository(operation="replay_reporting_database", params={"profile_path": "<profile>.json"})
```

Rebuilds the reporting database (path B) or the rows for Parquet (path C) from the kept extract
**with no EA connection**, identically to the original build. Use it to retest a fix to the
transform or to settle a disputed figure against the exact rows it was built from. The result
carries `replayed_from`. [`references/the-extract-snapshot.md`](references/the-extract-snapshot.md).

---

## 7. Removing the business layer

```
ea_repository(operation="remove_business_layer", params={"profile_path": "<profile>.json"})
```

Drops every view in the profile's schema, then the schema, and reports the views dropped. On
direct access that is all of AI Power Tools' footprint in the EA database. EA's own tables, and a
reporting database's copied tables, are not touched.

---

## 8. Keeping it fresh: the refresh

```
ea_repository(operation="start_reporting_refresh", params={"profile_path": "<profile>.json"})
ea_repository(operation="get_reporting_refresh",  params={"run_id": "<run id>"})
```

`start_reporting_refresh` returns a run id at once; `get_reporting_refresh` returns `running`,
`succeeded` or `failed` and, at the end, the full result: row counts per table, every flag, the
alignment summary, timings, or why it stopped. Run ids are kept until the server restarts.

| Path | What a refresh does |
|---|---|
| A | Regenerates the views. The data is live, so there is nothing to refresh; regenerate only when the technology or the inclusion choice changes |
| B | Preflight, extract, cut, load, swap-in, business views |
| C | Preflight, extract, cut, and rewrites the rows and definition. **The Parquet files and the Power BI project are not rewritten until the local step in `ea-power-bi` runs again** |

**A failed run, or one stopped by its preflight (paths B and C), leaves the previous reporting data
live** and says why.

**Scheduling is an AI agent's job, never Windows Task Scheduler.** A scheduled AI agent - for
example a scheduled task in Claude Cowork connected to the EA machine - calls
`start_reporting_refresh`, polls `get_reporting_refresh`, and reports the result: the row counts,
every flag (new roots left out, stale exclusions, unbound connectors, doubly-stereotyped
elements), timings and any failure. **EA must be running with the repository open on that
machine**, because the extract is COM; with EA closed the task fails.

A refresh uses the saved inclusion choice and does not ask again, but **it flags drift** when the
profile holds the `inclusion_choice` record (§4): `not_covered_by_inclusion_choice` (stereotypes
and connector keys neither in the technology, included, nor excluded) and `mdg_version_changed`.
Builds return the same flags; show them and re-run §2b. Power BI side: `ea-power-bi` §6.

---

## 9. Reporting the result

Say these four things, in this order, and do not bury the third:

1. **Which path**, and whether the data is live (A) or a snapshot with its as-of time (B, C).
2. **Checked or not**: `alignment.aligned` and, on A and B, `cells` and `differences`.
3. **What is outside the layer**: packages excluded, elements the inclusion choice left out, the
   `(excluded)` stubs, and every preflight flag the user continued past. A reader comparing a table
   count against EA's own element count should hear the difference from you first.
4. **What was built**: the entity, `Con_` and tag-row tables, row counts, the definition file, and
   the timings as measured on this repository.

Never report a figure from a table without saying how populated the columns behind it are: count
the non-empty values yourself. A roll-up over a partly-populated tag is a confident wrong number.

---

## 10. Rules that are not obvious

The five that cost the most; the full list is in [`references/the-schema.md`](references/the-schema.md) §8.

- **Join a connector to its ends by GUID**: `source_guid` and `target_guid` are entity `ea_guid`s.
  A combination with the same entity type at both ends is a self-join; name both sides.
- **An element in two tables is counted twice by design**, and so is a connector ending at it.
- **A text tag holding several values is one value in its column.** `GLBA, FFIEC` matches `LIKE`, not `=`.
- **A blank is a blank**: EA writes NULL and empty text identically.
- **A check that read nothing is a failure.** `cells: 0` compared nothing.

---

## 11. Known limits

- **SQL Server only** for direct access and for the reporting database. Other database types are
  refused.
- **DirectQuery on direct access queries the production database.** Its speed at the scale of a
  large repository is not measured. Measured on one model, and not what a customer should expect: a
  repository of about 80,000 rows reached through
  a cloud connection took 10-11 seconds to extract, 38-46 to load, under 1 to swap in, and about 2
  minutes for a full reporting-database refresh.
- **Windows authentication.** SQL Server is reached with the Windows account running AI Power Tools.
- **OneLake upload is not yet available** (APT-2026-0362). Parquet is written to a local folder and
  Power BI Desktop imports it.
- **Only a RefGUIDList tag is split into a tag-row table.** A CheckList tag stays a column (`1,1,0`).
- **`.eapx` (Jet) repositories are untested.** Measured on a local `.qea` and a cloud-connected repository.
- **No masking.** Exclusion is by whole package.

---

## 12. When it goes wrong

A call that appears to hang is usually a modal dialog in EA holding the COM connection: look at EA's
screen before retrying. Every error code (`missing_rights`, `preflight_blocked`,
`target_is_an_ea_repository`, `wrong_path`), a build that is not `aligned`, and a later spot-check
that disagrees by a few rows: [`references/troubleshooting.md`](references/troubleshooting.md).

---

## Reference files

- [`references/the-schema.md`](references/the-schema.md) - every table kind and its columns
- [`references/the-profile.md`](references/the-profile.md) - the profile's parts and scope rules
- [`references/troubleshooting.md`](references/troubleshooting.md) - symptoms, causes, fixes
- [`references/the-extract-snapshot.md`](references/the-extract-snapshot.md) - the kept extract, and replay
- [`references/the-inclusion-choice.md`](references/the-inclusion-choice.md) - the three-way choice, its counts, and the refresh
- [`references/the-governance-gate.md`](references/the-governance-gate.md) - the pre-build gate
- [`../ea-power-bi/SKILL.md`](../ea-power-bi/SKILL.md) - the Power BI project and the Parquet step
- [`../_shared/references/ea-ui-verification.md`](../_shared/references/ea-ui-verification.md) -
  the modal-dialog trap
- [`../_shared/references/westbrook-example.md`](../_shared/references/westbrook-example.md) - the
  canonical example model
- `../_shared/tools/` - the census modules `ea_census.py`, `inclusion.py` and `governance_gap.py`.
  Their tests run with `python -m pytest ../_shared/tools -q` and need no EA.

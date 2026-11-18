# A reporting database in the cloud

The long form of `SKILL.md` §3b and §3c: path B built into a SQL database in Microsoft Fabric (measured)
or an Azure SQL Database (expected to work, not measured), signed in with Microsoft Entra; and the three
routes that put the business layer into Fabric as tables (§5 to §7 here). Westbrook Bank values are an
illustration; substitute your own server, database, workspace and account.

---

## 1. Before the first build

**A SQL database in Fabric needs a Fabric capacity.** The workspace that holds it must be on one. Check
that the capacity is not paused before a build or a refresh. A customer without a Fabric capacity keeps a local SQL Server (path B) or Parquet (path C).

**Create the database in the Fabric portal first.** AI Power Tools cannot create it there: a SQL
database in Fabric refuses the `master` database that a local SQL Server build uses to create a
missing one. Then read two values from the database's connection strings in the portal:

| Profile key | Where it comes from | Measured form |
|---|---|---|
| `target.server` | The server name | `<id>.database.fabric.microsoft.com,1433` |
| `target.database` | The database name | The display name followed by the item id, `<DisplayName>-<item id>`. **Not the display name alone** |

**The profile.** Illustration with Westbrook Bank; substitute your own:

```json
"target": {"kind": "reporting_database",
           "server": "<id>.database.fabric.microsoft.com,1433",
           "database": "WestbrookReporting-<item id>", "schema": "logical",
           "authentication": "entra-interactive", "user": "architect@westbrookbank.example"}
```

| Key | Values |
|---|---|
| `target.authentication` | `windows` (the default, as before: the Windows account running AI Power Tools) or `entra-interactive` (a person signs in with a Microsoft work account). Anything else is refused |
| `target.user` | With `entra-interactive` only: the account the sign-in window suggests. **Set it with Microsoft's OLE DB Driver 18**: the driver refuses an interactive sign-in without it (measured 13 Nov 2026). With `windows` it is refused: Windows authentication uses the Windows account |

Direct access (`target.kind` `ea_database`) refuses `entra-interactive`: Entra sign-in was measured on
reporting databases only. A Parquet profile has no database to sign in to. A server older than the
version named in `SKILL.md` §3b ignores `target.authentication` and connects with Windows
authentication, which a SQL database in Fabric refuses.

**The driver.** Entra sign-in uses the Microsoft OLE DB Driver for SQL Server: version 18 (provider
`MSOLEDBSQL`) was measured; version 19 (`MSOLEDBSQL19`) is used only when 18 is absent and is not
measured. With neither installed the operation is refused with Microsoft's download page. The older
`SQLOLEDB` provider is never used for Entra, and every Entra error names the provider and driver it
used.

---

## 2. The sign-in

- **A person completes it.** The first operation that opens the database in a server process shows
  Microsoft's sign-in window ("Windows Azure Authentication" on driver 18), restored and brought to
  the front. Someone signs in there, with multifactor approval if the tenant asks for it.
- **Once per server process.** Later calls in the same process reuse the sign-in without a prompt.
  Measured with the approach the server uses, EA attached: a build, then two refreshes five minutes
  apart, on one sign-in. A restart of the server needs a new sign-in. How long a sign-in lasts
  beyond five minutes is not measured; when it expires, the next call shows the window again.
- **No one answers.** After about ten minutes the operation stops with a sign-in failure and writes
  nothing; a refresh leaves the previous reporting data live. A canceled or failed sign-in is
  reported as such, not as a missing database (`replay_reporting_database` returns
  `sign_in_failed`, or `cannot_connect` when the server could not be reached).
- **Unattended sign-in to the database is not offered.** A scheduled refresh into a SQL database in
  Fabric (`SKILL.md` §8) needs someone at the machine when the server process first connects. There is
  no service principal option for the database connection. The OneLake upload of §7 signs in
  differently, through the Azure CLI.

---

## 3. What was measured on Westbrook

Path B into a SQL database in Fabric on a Fabric trial capacity, with the server's own build and
check and the Entra connection: the build was `aligned`, and `check_business_layer` compared 1,008
cells against an independent read through EA with **0 differences**, the same cell count as the
local SQL Server build. A second build (a refresh) also succeeded. Westbrook is small; these are not
timings or sizes a customer should expect.

---

## 4. Power BI

- **Power BI reads it in Import**, like any path B database. The project needs no change for a cloud
  database. A published model refreshes in the Power BI service with **no gateway**, using OAuth2
  credentials: `ea-power-bi` §6, including the misleading "use SSL" message when the browser blocks
  the sign-in pop-up.
- **With the default `views` output, OneLake holds EA's tables, not the business layer.** The database
  copies itself into OneLake automatically, but only its tables. Direct Lake reads tables only, and the
  database's SQL analytics endpoint cannot run the business layer's default views, which use recursive
  queries it refuses. For the business layer as tables, use `output` `tables` (§5); for Direct Lake over
  Parquet, §7.
- **Removing the layer** (`SKILL.md` §7) stops a published model's refresh exactly as it does on a
  local SQL Server.

---

## 5. The business layer as tables, or as a script for Fabric (`target.output`)

Path B only (`target.kind` `reporting_database`); `tables` or `script` with any other kind is refused.
Needs AI Power Tools for Sparx EA 3.6.6 or later. Set `"output"` in the profile's `target`, or pass
`output` to `build_business_layer`.

| `output` | What the build writes |
|---|---|
| `views` | The default: SQL views only, as before |
| `tables` | The views, and a table of the same name in `dbo` filled from each view. The views stay the one definition. A SQL database in Fabric copies tables to OneLake, so these are what Direct Lake can read |
| `script` | The views, the two scope tables (`_scope_package`, `_package_path`) and `<profile>.fabric-views.sql` beside the profile, with no business tables (only `tables` writes those; any left by an earlier `tables` build are dropped): every view as T-SQL (`DROP VIEW IF EXISTS`, then `CREATE VIEW`, one batch each, separated by `GO`) for a Fabric SQL analytics endpoint |

- **Keys.** Every table has a primary key: `ea_guid` (entity), `connector_guid` (`Con_`), `property_id`
  (tag-row, plus `value_no` where a list tag is split into one row per value, because SQL Server cannot
  key on the unbounded `value` text), `table_name` (Table Directory). `Source` is one row keyed by
  `source_row`. The Table Directory's `primary_key` column names each table's key columns. A key that is not
  unique, or has a NULL, stops the build with `key_not_unique`, and nothing is changed.
- **No recursive query.** A Fabric SQL analytics endpoint refuses them (measured). In `tables` and
  `script` the build works out package scope and package paths itself and keeps them in two small keyed
  tables, `dbo._scope_package` and `dbo._package_path`, which the plumbing views read. The business
  tables the build made are listed in `dbo._business_tables`, so a `dbo` table it did not make is never
  replaced (`tables_not_written`).
- **A refresh merges in place** into these tables when each has the shape the build would create; a new
  table, a changed shape or a table that has gone is a structural change, and `ddl` and `load_reason` say
  so.
- **One layer per database.** The two keyed tables and the registry are not per schema or per profile,
  so one reporting database holds one layer. Changing from `tables` to `script` drops the business tables
  (`script` writes none). Changing to `views` drops, on the next build, the business tables, the two keyed
  tables and the registry that the earlier build made; a registered table the build cannot show it made
  is left in place and listed in the reply (`left_in_place`). The drop follows the database's registry, not
  the profile, so don't point two profiles at one reporting database. `remove_business_layer` drops the
  same tables with the views.
- **The script refuses a `/` or `\` in a schema or table name**, because the endpoint does; a
  stereotype alias containing one stops the build (`tables_not_written`) before anything changes. No
  cross-database names. A script for a customer's own mirrored EA database (path A) is not provided.

**Measured:** built and tested against a local SQL Server, with a check that the tables merge in place and
that no view in the script recurses. Then on Westbrook Bank in a Fabric trial, 16 Nov 2026:

- `output: tables` into a SQL database in Fabric (Microsoft Entra sign-in, completed through the server):
  the first build swapped (tables created) and the second refreshed in place with no structural change.
  `check_business_layer` aligned: 1008 cells, 0 differences. Fabric copied the business tables to OneLake,
  and a Direct Lake on OneLake model generated by `powerbi_model.py --mode directLake` over that SQL
  database read all 31 business tables with counts equal to the build.
- `output: script`: the view file ran on the SQL analytics endpoint of that SQL database. 36 views were
  created and none was refused. The 32 business views matched the path B business tables cell for cell
  (1551 cells, 0 differences).

`check_business_layer` run against the SQL analytics endpoint with the `script` views: aligned, 1008 cells, 0 differences, the same as the local result (16 Nov 2026). A DirectQuery model generated by `powerbi_model.py --mode directQuery` over that SQL analytics endpoint returned all 31 business tables with counts equal to the build (16 Nov 2026).

**Not measured:** a service principal's sign-in; a person's cached sign-in lasting the weeks a schedule needs.

---

## 6. Mirroring a local SQL Server into Fabric

- **What Fabric needs.** SQL Server Standard, Enterprise or Developer edition. Express cannot be
  mirrored. A SQL Server behind a firewall needs an on-premises data gateway. Every mirrored table needs a
  primary key (Microsoft). Every business table has one (§5), including the one-row `Source` table (key `source_row`).
- **Why the refresh changed.** On SQL Server 2016 to 2022, a structural change to a mirrored table makes
  mirroring fail until change data capture is turned off and on again for that table. The old refresh
  swapped every table into `dbo` on every run, which is a structural change on all of them.
- **The in-place refresh.** When every table already exists with the current shape, a refresh loads the
  new rows into temporary tables (tempdb, never mirrored), then in one transaction deletes the rows whose
  key has gone and merges the rest into the existing tables. No `TRUNCATE`, which SQL Server refuses on a
  table with change data capture. A failure rolls back and leaves the previous data live. The business
  views are rebuilt in the same transaction; views are not mirrored.
- **When it swaps.** On the first build, when a table's shape changed (new columns) and when a table is
  new. The first refresh after upgrading from a version without keys on the two bookkeeping tables is one
  swap. The result's `load_mode` (`in_place` or `swap`), `ddl` (true after a swap) and `load_reason` say
  which and why.
- **When to re-seed.** `check_business_layer` returns `last_refresh` (`load_mode`, `ddl`, `reason`,
  `loaded_at`), and after a swap adds a note that the mirror must be re-seeded: turn change data capture
  off and on again on the tables. Refreshes after the swap load in place and need nothing.
- **A merge can collide on `ea_guid`.** A merge keyed on the primary key could hit the `ea_guid` unique constraint
  if two rows exchange GUIDs within one refresh. This is judged unlikely and not handled.

**Measured:** on a local SQL Server, with a trigger recording every structural change, the first refresh
swapped and the second and third made none. Then on Westbrook Bank, 16 Nov 2026: a local SQL Server 2022
Developer reporting database mirrored into a Fabric trial through an on-premises data gateway. The mirror
stayed healthy across three refreshes, each in place with no structural change, and every mirrored table
matched the local counts after each (applied within about 2 to 7 minutes).

**Setting up the mirror (what the test needed):**

- The mirror login needs `db_owner` on the database.
- Enabling change data capture on the database needs a sysadmin. Fabric's first start failed with
  "Sysadmin privileges are required" until it was enabled.
- A database owned by a Microsoft Entra account the server cannot resolve fails to enable change data
  capture (error 15404). Give the database an owner the server can resolve, such as `sa`.
- Fabric does not mirror a table without a primary key. The one-row `Source` table was left out until it
  gained a key (`source_row`) in 3.6.6. The first refresh after upgrading rebuilds the tables once, so restart
  the mirror once then.
- The test turned the encrypted connection off, because the instance had only a self-signed certificate.
  Use a trusted certificate and keep encryption on.

**Not measured:** a service principal's sign-in; a person's cached sign-in lasting the weeks a schedule
needs.

---

## 7. Parquet into a mirrored database, and a Direct Lake model (path C)

The steps are in `SKILL.md` §3c, route 1. What sits behind them:

- **The landing zone.** The folder `parquet_tables.py --layout open-mirroring` writes follows the Open
  Mirroring landing-zone format as Microsoft's page described it (content updated 3 Feb 2026): a folder
  per table named exactly as the table; a `_metadata.json` with `keyColumns`; data files named with 20
  digits, continuous. The first run writes every row as an insert. A later run writes the whole table as
  changes: a delete (`__rowMarker__` 2, key columns only) for each key present last run and gone now,
  then an upsert (4) for every current row, with `__rowMarker__` the last column. A table with no
  upserts and no deletes gets no file, because Fabric never moves such a table's sync time for an empty
  file.
- **Keys** are those of §5. `keyColumns` cannot change once Fabric has the table. A landing zone written
  from a definition of a server before 3.6.6 holds the keys the writer derived for the tag-row tables;
  after the update the writer keeps those keys for that table (the result says `kept_existing_keys`)
  while the table still has the columns and they stay unique, and a run continues without a restart.
  Any other change of keys is refused. A definition from a server before 3.6.6 declares no keys; the
  writer then derives them, and refuses a connector tag-row table in which the same tag and value
  appear twice on one connector.
- **State.** `<landing-zone-folder>.state.json` (the keys and last file number of each table) and
  `<landing-zone-folder>.upload.json` (the last file uploaded per workspace and mirrored database) sit
  beside the folder, never inside it, so they are never uploaded. Without the first, a run on a folder
  that already holds files refuses. A run that stopped after writing the table files and before the state
  file is recovered by the next run, which reads back the files newer than the state's last file number, so
  a row that only reached those files is still deleted when it vanishes. To start over, do it on both sides: delete the table folders in the
  mirrored database's landing zone in OneLake (Fabric drops those tables), and the local table folders,
  the state file and the upload record together. Deleting only the local files leaves the upload record
  counting from the old file numbers, so the next upload sends nothing.
- **The upload.** Through OneLake's file API with a token from the Azure CLI, a new table's
  `_metadata.json` first. Each file is written under a temporary name in its own table folder and
  renamed to its final name once it is complete, so a failed write never leaves a half-written file where
  Open Mirroring reads. A failed run resumes where it stopped. It then polls the mirrored database's
  table status until every uploaded table has applied, and only then reframes the Direct Lake model
  (`--semantic-model`) once. A table whose only new file holds no rows is not waited on.
  A file an earlier run uploaded and never saw applied is waited on first, and nothing more goes up to
  that table until it is confirmed, so a late apply of the earlier file is never counted as the new one's.
  The reframe follows the refresh it started (the refresh id the request returns), never the newest entry
  of the refresh history. A reframe that fails, or that a failed table held back, is recorded in the upload
  record, and the next run retries it even when there is nothing new to upload.
- **The one-unit promise, and its limit.** With "Keep your Direct Lake data up to date" off (`SKILL.md`
  §3c), the model keeps showing the previous refresh until the one reframe. With it on, Fabric reframes
  table by table as each lands: measured, a mix of two refreshes was visible for up to about 3 minutes.
  A reader of the SQL analytics endpoint can see a mix for a few minutes whichever way the setting is.
- **Sign-in.** The Azure CLI, as in `SKILL.md` §3c. The tool needs `az` on the path and a signed-in
  account that can write to the workspace. A service principal works the same way once the administrator
  has signed the CLI in as one; this is supported and **not measured**.

**Measured on Westbrook, 13 Nov 2026:** three refreshes through Open Mirroring. Refresh 1: 40 tables
uploaded and applied in 177 s; the endpoint held all 40 with exact names and counts equal to the build.
Refresh 2, a package left out (1,164 rows, 57 deletes): all 40 equal the build, the deletes applied.
Refresh 3, the package back (1,221 rows): 17 tables with changes applied in 213 s, one reframe after
every table landed (12.9 s, completed), and the endpoint and the Direct Lake model equal to the build on
all 40. Westbrook is small; these are not timings a customer should expect. A first run found that Fabric
never marks a table synced after an empty change file; the writer now writes none, and the upload does
not wait for a table whose only new file is empty.

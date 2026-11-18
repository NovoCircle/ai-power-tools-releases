# When it goes wrong

Each entry is a symptom, the cause, and what to do. `SKILL.md` §5 and §8 describe the operations.

**A call appears to hang.** EA reports a statement its backend cannot run as a **modal dialog**
that holds the COM connection until a human dismisses it, so every later call appears to hang too.
Look at EA's screen before retrying. See
[`../_shared/references/ea-ui-verification.md`](../_shared/references/ea-ui-verification.md).

**`missing_rights` on direct access.** Nothing was changed. The message names each right the
account lacks; ask the database administrator for it, or use path B or C.

**`preflight_blocked`.** The preflight found unbound connectors. Nothing was written. Fix them, with
a baseline first (`SKILL.md` §5.3: `update_connector`, or re-apply the stereotype in EA), and run the
preflight again.

**`target_is_an_ea_repository` / `not_an_ea_database`.** The first: the reporting database named
in the profile holds an EA repository's tables; name a separate one. The second: the direct-access
profile names a database with no EA tables.

**`wrong_path`.** The profile's `target.kind` does not match the operation: `build_business_layer`
needs `ea_database` or `reporting_database`; `build_reporting_database` needs `reporting_database`
or `parquet`.

**A Microsoft Entra sign-in failed or was not completed.** The sign-in window was canceled, refused,
or not answered within about ten minutes. Nothing was written, and a refresh left the previous data
live. Look for Microsoft's sign-in window (it is brought to the front, but another window can still
cover it) and run the operation again with someone there to sign in. A replay reports it as
`sign_in_failed`, and as `cannot_connect` when the server could not be reached at all.

**"Microsoft Entra sign-in needs the Microsoft OLE DB Driver for SQL Server".** Neither driver 18 nor
19 is installed. Install it from the page the message names, then run again.

**A cloud database "does not exist ... create the database in the Fabric portal".** A SQL database
in Fabric cannot be created by AI Power Tools. Create it in the Fabric portal, or check that
`target.database` is the database name from its connection strings (the display name followed by
the item id), not the display name alone. Also check that the workspace's Fabric capacity is not
paused. [`the-cloud-database.md`](the-cloud-database.md).

**`key_not_unique`.** A business table's key had a duplicate or a NULL, so the `tables` or `script`
build stopped and changed nothing. The message names the table. Report it with the full result: the
business layer should never produce one.

**`tables_not_written`.** The `tables` or `script` build could not write the business tables, and changed
nothing. Usual causes: a `dbo` table with a business table's name that the build did not make (it is
never replaced), or a stereotype alias containing `/` or `\`, which a Fabric SQL analytics endpoint
refuses in a name. Rename the other table, or the alias, and build again.

**A Fabric mirror of a local SQL Server stopped after a refresh.** Read `last_refresh` in
`check_business_layer`: `ddl` true means the refresh swapped the tables in, which is a structural change.
Re-seed the mirror by turning change data capture off and on again on the tables.
[`the-cloud-database.md`](the-cloud-database.md) §6.

**"Microsoft Entra sign-in" is refused with driver 18.** The driver refuses an interactive sign-in
without an account named. Add `target.user` to the profile.

**The upload says the Azure CLI is missing or has no token.** `onelake_upload.py` takes its token from
the Azure CLI. Install it and run `az login`, or have the administrator sign it in as a service
principal. The tool never asks for a secret.

**The upload result shows a table not applied, or exits with a code other than 0.** `ok` is false when
any table failed or did not apply within the wait (300 seconds by default; `--timeout`). The reframe is
then skipped on purpose, so the model keeps the previous refresh. Run the upload again: it resumes and
sends only what has not landed. Report the table and Fabric's status.

**A table's error says an earlier upload is not confirmed applied.** Nothing more is uploaded to that
table until Fabric shows the earlier files applied, because Open Mirroring applies a table's files in
order. Open the mirrored database in Fabric and choose Monitor replication: the table's last completed
time should be after that upload, and its row count should include those files. Once it has applied, run
the upload again with `--confirm-applied "<table>"`; that clears the table from the upload record beside
the landing-zone folder, and the run then uploads its new files and reframes the model. If Fabric shows an
error for the table, fix that first.

**A Direct Lake report shows tables from two refreshes.** "Keep your Direct Lake data up to date" is on,
so Fabric reframes table by table. Turn it off in the semantic model's settings, Refresh; the upload tool
then reframes once, after every table has applied. A reader of the SQL analytics endpoint can still see
the mix for a few minutes.

**Alignment is not `aligned`.** Read `combinations_without_a_table`,
`outside_every_allowed_combination` and `connector_count_mismatches` before changing anything. A
connector outside every allowed combination is a connector the technology does not allow between
those two stereotypes; it is reported, not dropped.

- **Only `outside_every_allowed_combination` is non-zero:** the build is correct, even though `alignment.aligned` is `false` (the verdict counts these connectors). Those connectors
  use a declared connector stereotype between two element stereotypes the technology does not allow
  together, so they stay in EA's physical tables and no business table shows them. Proceed, and tell
  the user which combinations they are (source stereotype, connector stereotype, target stereotype,
  count) so they decide: add the combination to the technology's allowed relationships (the next
  build then gives it a `Con_` table), or treat the connectors as modeling errors and fix them in EA.
- **`combinations_without_a_table` or `connector_count_mismatches` is non-zero:** that is a defect in
  the build, not a modeling question. Stop and report it with the operation's full result.

**A later spot-check in EA disagrees with the layer by a few rows.** A snapshot (B, C) matches
the repository as of its run; on a shared repository other work lands in between. Compare a
disputed number against the build it came from - replay it (`SKILL.md` §6) - and say the as-of time whenever
a figure may be quoted back at you.

---

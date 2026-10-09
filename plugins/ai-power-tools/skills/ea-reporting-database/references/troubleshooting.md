# When it goes wrong

Each entry is a symptom, the cause, and what to do. `SKILL.md` §5 and §8 describe the operations.

**A call appears to hang.** EA reports a statement its backend cannot run as a **modal dialog**
that holds the COM connection until a human dismisses it, so every later call appears to hang too.
Look at EA's screen before retrying. See
[`../_shared/references/ea-ui-verification.md`](../_shared/references/ea-ui-verification.md).

**`missing_rights` on direct access.** Nothing was changed. The message names each right the
account lacks; ask the database administrator for it, or use path B or C.

**`preflight_blocked`.** The preflight found unbound connectors. Nothing was written. Fix them in
EA (`SKILL.md` §5.3) and run the preflight again.

**`target_is_an_ea_repository` / `not_an_ea_database`.** The first: the reporting database named
in the profile holds an EA repository's tables; name a separate one. The second: the direct-access
profile names a database with no EA tables.

**`wrong_path`.** The profile's `target.kind` does not match the operation: `build_business_layer`
needs `ea_database` or `reporting_database`; `build_reporting_database` needs `reporting_database`
or `parquet`.

**Alignment is not `aligned`.** Read `combinations_without_a_table`,
`outside_every_allowed_combination` and `connector_count_mismatches` before changing anything. A
connector outside every allowed combination is a connector the technology does not allow between
those two stereotypes; it is reported, not dropped.

- **Only `outside_every_allowed_combination` is non-zero:** the build is correct. Those connectors
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

# Keeping it fresh: the refresh

The long form of `SKILL.md` §8: what a refresh does on each path, the Path C steps into Fabric, scheduling, and the drift flags.

```
ea_repository(operation="start_reporting_refresh", params={"profile_path": "<profile>.json"})
ea_repository(operation="get_reporting_refresh",  params={"run_id": "<run id>"})
```

`start_reporting_refresh` returns a run id at once; `get_reporting_refresh` returns `running`,
`succeeded` or `failed` and, at the end, the full result or why it stopped. Run ids are kept until
the server restarts; a run polled across a restart is lost, so start a new refresh.

| Path | What a refresh does |
|---|---|
| A | Regenerates the views. The data is live, so there is nothing to refresh; regenerate only when the technology or the inclusion choice changes |
| B | Preflight, extract, cut, load, business views. The load is **in place** (delete the keys that have gone, merge the rest, no structural change) when every table exists with the current shape, so a Fabric mirror survives. It **swaps** on the first build, a changed shape or a new table. The result's `load_mode`, `ddl` and `load_reason` say which, and `check_business_layer` returns `last_refresh` (`load_mode`, `ddl`, `reason`, `loaded_at`) and a note to re-seed a Fabric mirror after a swap |
| C | Preflight, extract, cut, and rewrites the rows and definition. **The Parquet files and the Power BI project are not rewritten until the local step in `ea-power-bi` runs again.** Into Fabric, the scheduled run goes on: see below |

**A failed run, or one stopped by its preflight (B, C), leaves the previous data live** and says why.

**Path C into Fabric:** after `start_reporting_refresh` succeeds, the agent runs `parquet_tables.py ...
--layout open-mirroring`, then `onelake_upload.py ... --result-file <file>` (§3c), and reports the upload
result: per table applied or not, the reframe's status, seconds, errors. A table not applied, or an exit
code other than 0, is a failure to report.

**Scheduling is an AI agent's job, never Windows Task Scheduler.** A scheduled AI agent (a scheduled
task in Claude Cowork connected to the EA machine) calls `start_reporting_refresh`, polls
`get_reporting_refresh`, and reports the row counts, every flag (new roots left out, stale
exclusions, unbound connectors, doubly-stereotyped elements), timings and any failure. **EA must be
running with the repository open on that machine**, because the extract is COM.

A refresh uses the saved inclusion choice and does not ask again, but **it flags drift** when the
profile holds the `inclusion_choice` record (§4): `not_covered_by_inclusion_choice` (keys neither in
the technology, included, nor excluded) and `mdg_version_changed`. Builds return the same flags; show
them and re-run §2b. Power BI side: `ea-power-bi` §6.

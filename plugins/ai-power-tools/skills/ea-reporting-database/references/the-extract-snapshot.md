# The kept extract - what is kept, and replay

A build on the reporting-database path or the Parquet path reads EA's tables over COM, which is
the slowest and least repeatable step: COM call timing has been measured varying by about 150x.
Everything after it works on the rows that were read. AI Power Tools keeps those rows so a build
can be repeated without EA.

Direct access has no extract: its views read EA's tables as they stand, so there is nothing to keep.

---

## 1. Why a build has to be replayable

**A transform fix cannot be retested against the data that exposed it.** Retesting means re-running
the extract against a repository that has moved on, so the fix is never checked against the rows
that produced the fault.

**The repository changes underneath a build.** The model is shared. A package count was observed
moving three times in twenty minutes because another session was creating and deleting scratch
packages. The kept extract is the only artifact that pins an instant.

**A disputed figure cannot be settled after the fact.** When one is disputed a month later, "re-run
it and see" is not an answer - the repository is different now, and the difference is exactly what
is in dispute. The kept extract is the evidence behind a figure's as-of time.

---

## 2. What is kept

After every build on the reporting-database and Parquet paths, one file, `<profile>.extract.json`,
beside the profile:

| Held | Why |
|---|---|
| The **post-cut rows**: every row that was loaded, `(excluded)` stubs included | What the build was made from |
| The scope and the counts: rows extracted and rows kept, packages kept, objects cut, crossings by kind, stubs | What was cut, without the cut content |
| The crossings and the preflight flags | What the user continued past |
| The run id and the time of the extract | Which extract a build used |
| The extract log: for each table, the SQL issued, the rows read and the milliseconds | Exactly what was asked of EA, and timings for the next run to compare against |
| The technology: id, version, where it was read from, and its definition | So a replay needs no EA and no installed technology |

**Only the last run's extract is kept.** Each build replaces it. One run replacing itself is not a
history, and the reporting data is a full rebuild with no history too.

**Excluded content is never written to disk, at any stage.** The raw extract holds the areas the
user chose to leave out; keeping it would store exactly that content. The cut is applied in memory
before anything is written, and the kept file holds only the post-cut rows.

The kept file holds what the user chose to include - names, notes and tagged values of every kept
package. Treat it with the same care as the reporting data. Deleting it loses only the ability to
replay.

---

## 3. Replay

```
ea_repository(operation="replay_reporting_database", params={"profile_path": "<profile>.json"})
```

- **Needs no EA connection.** It reads the profile and the kept extract.
- **Rebuilds identically.** On the reporting-database path it recreates the database and the
  business views from the kept rows, and the result matches the original build. On the Parquet
  path it recomputes the business tables' rows and the definition; the local step in `ea-power-bi`
  then writes the files again.
- **Says what it consumed.** The result carries `replayed_from`, the path of the extract it used; the file's `run_id` and `extracted_at` identify the run.
- **Writes the definition** beside the profile again (`definition_path` overrides it).
- **Is not available on direct access.** There is no extract to replay; regenerate the views with
  `build_business_layer`.

Use replay to retest a fix against the exact rows that exposed a fault, to settle a disputed
figure against the build it came from, or to rebuild a reporting database that was lost without
disturbing a shared EA repository.

**A replay is not a refresh.** It reproduces an earlier instant. To bring the data up to date, run
a refresh (`SKILL.md` §8), which extracts again and replaces the kept file.

---

## 4. If there is no kept extract

A profile that has never been built has none, and the replay returns `invalid_input` naming the
missing file. Build first.

# Moving a whole model to another repository (Native XML)

Full detail behind section 4b of `../SKILL.md`. This is a procedure in EA's own user interface: no
operation in this server moves a whole model, so the work is done by the person or by driving EA
with computer use (wait before each screenshot, per `../../_shared/references/latency.md`).

*Measured once, on a cloud repository (EA 17.0, MySQL back end) holding about 3,300 elements,
8,950 connectors and 2,580 diagrams, driven as an administrator. Times and results below come from
that one move. A different size, back end or EA build may behave differently.*

## Choose the route

| Route | Use it when |
|---|---|
| **Settings > Transfer > Native XML** (full project export, then import) | The target is a cloud repository, or you have no direct database access to either side. This is the route that worked on the cloud model above. |
| **Full Project Transfer via Connection** | Both repositories can be reached directly by database connection. It needs direct database access to the server, so it cannot be used on a cloud repository. |
| `export_xmi` / `import_xmi` (section 4) | One package, not the whole model. |

Measured with Native XML: export about 1 minute, import about 50 minutes, and every model table
matched afterwards.

## Procedure

1. **Back up the target first.** The import deletes everything in the target before it loads
   (EA warns). Take a backup or a copy of the target repository you can restore from. Do not
   continue until you have it.
2. **Export the source** with Native XML, full project, to a file in a folder you name.
3. **Import into the target.** Expect a long run; a screenshot of "(Not Responding)" in the title
   bar means EA is still working.
4. **Reopen the target.** EA keeps the technologies that were loaded before the import until the
   repository is closed and opened again, so check technologies only after reopening.
5. **Compare by GUID.** GUIDs are kept, so match source and target rows by GUID (counts per table
   first: elements, connectors, diagrams, packages, tagged values). Build a source-to-target id
   table from the GUIDs (next section).
6. **Rebuild the diagram image cache** (see "What the export leaves out or changes").
7. **Work through the post-transfer checklist** at the end of this page.

## What changes: every numeric id is new

GUIDs are kept. Every numeric id is renumbered: elements, diagrams, connectors and packages.

- EA remaps the references it knows about: global matrix-profile package ids, navigation cells and
  click-through (`DefaultDiagram`) links.
- A matrix profile whose package did not exist in the source is left with its old number, which now
  points at an unrelated package in the target. Check every matrix profile after the import.
- Anything outside EA that stores a numeric id points at the wrong thing, silently: Prolaborate
  queries and links, markers in scripts, saved searches that name an id, spreadsheets.

Build the table by GUID so you can translate:

```python
src = {r["ea_guid"]: r["Object_ID"] for r in source_rows}   # from ea_analyze execute_sql on the source copy
dst = {r["ea_guid"]: r["Object_ID"] for r in target_rows}   # the same query on the target
id_map = {src[g]: dst[g] for g in src if g in dst}
missing = [g for g in src if g not in dst]                   # should be empty
```

Do the same for `t_diagram`, `t_connector` and `t_package`. Run the queries on each repository on its
own (one EA session per model file); do not attach both at once with one tool.

## What the export leaves out or changes

These are differences, not data loss. Check them so they are not mistaken for loss.

- **Cached diagram images are never exported.** Rebuild the image cache in the target.
- **Element notes lose trailing blank lines.** A byte-for-byte comparison of notes will show a
  difference on notes that ended with blank lines.
- **One system setting stored with garbled bytes (`MySQL_MemoDataType`) is skipped by the import.**
  EA rewrites it when the model is reopened.

## Post-transfer checklist

- [ ] Backup of the target exists and opens.
- [ ] Target reopened after the import; technologies checked after reopening.
- [ ] Counts per table match the source; every source GUID is present in the target.
- [ ] Source-to-target id table saved, for everything outside EA that holds a numeric id.
- [ ] Matrix profiles checked, especially any whose package was not in the source.
- [ ] Diagram image cache rebuilt; a few diagrams opened and looked at.
- [ ] Notes differences (trailing blank lines) and the `MySQL_MemoDataType` setting understood, not
      reported as loss.
- [ ] **Prolaborate repository id.** EA's Model Options (Cloud) holds a Prolaborate Repo ID for
      each model (`usys_system.ProLabRepoID`), so a model copied into another repository still
      points at the old Prolaborate repository. Read it in the target and set it to the right
      repository in EA's Model Options. See `ea-com` for the read query.
- [ ] Prolaborate queries, links and any script markers that carry numeric ids translated through
      the id table.

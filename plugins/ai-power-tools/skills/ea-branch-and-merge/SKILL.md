---
name: ea-branch-and-merge
description: Take a package out of a Sparx EA model into a branch model, change it there, and merge it back safely - for .qea file repositories only. Covers freezing a base copy of production, creating the branch, installing the technology, importing the package with its GUIDs, the three-way diff (diff_models_three_way) with its modify/delete rule, a person deciding every conflict, the validation gate that blocks the merge, a baseline of production, one writer applying the decided plan by GUID (apply_merge_plan), and the read-back with a final diff. Use when someone wants to work on a package away from production and bring the changes back, when two people changed the same package, when a diff of two copies of a model is needed, or when asked to merge one model file into another. Not for a rollback (ea-change-management) and not for server or DBMS repositories.
---

# EA Branch and Merge: take a package out, change it, merge it back

*Tools: `ea_repository` (including `diff_models_three_way` and `apply_merge_plan`), `ea_mdg`, `ea_validate`, `ea_model`, AI Power Tools for Sparx EA*

Run the `ea-start-here` preflight first. A merge writes to production, so confirm which model each tool call reaches before every write.

## When to use

- Someone wants to change a package away from production (a restructure, a large review, a trial) and bring the result back.
- Production changed while the branch was being edited, and the two sets of changes must be combined with a person deciding every clash.
- Someone asks for a diff between two copies of a package, or to merge one model file into another.
- **Not** for undoing a change: that is `ea-change-management` (baselines). A baseline restores one model to its own earlier state. A branch merge combines two lines of change.
- **Not** for server repositories, SQL Server, Oracle or other databases, or Pro Cloud Server. See "What is not verified".

## What this skill promises

1. Every difference between the three files is found, including a row that one side deleted and the other side changed. That case is a conflict, never a plain delete.
2. A person decides every conflict. Nothing is decided by default, and you do not decide for them.
3. The technology's validation rules run before the merge, and any failure blocks it.
4. Production gets an EA baseline before anything is written to it.
5. One writer applies the merge, matched by GUID. The result is read back, and a final three-way diff shows exactly the changes the person decided to leave different.

## Scope of this version

- **`.qea` files only.** The diff reads the three files directly (SQLite, read only). No EA session is involved in reading, so the one-EA-session-per-model rule is not strained.
- **Security, version control and other databases are unverified.** Writing GUIDs with SQL bypasses security locks, auditing and version-control flags, and none of that was tested. If the production model has EA security enabled, is under version control, or is a `.eap`, `.feap`, DBMS or Pro Cloud Server repository, stop and say this skill does not cover it.
- **Only some tables are compared.** The diff covers packages, elements, attributes, operations, connectors, tagged values, diagrams, the elements on diagrams, and the stereotype link of each item. Anything stored elsewhere (element constraints, scenarios, requirements, files, hyperlinks, connector tagged values, and similar) is neither detected nor merged. Ask the person whether they changed any of that, and if they did, tell them it will not come across.
- **The merge writes only elements, connectors, tagged values and packages,** with the stereotype link of each element or connector it creates, updates or deletes (written or removed with the item and checked after the write). A stereotype link that carries more than one stereotype is refused; every stereotype in it counts, with or without a profile name. When the plan deletes an element, its placements on diagrams go with it (EA removes them, and the read-back checks that none is left); removing a placement of an element that stays is not written. The diff compares more than that. A plan that holds a change to attributes, operations, diagrams, the elements on diagrams or any other stereotype link is refused whole: nothing is written, not even the element and connector changes beside it. The dry run lists those steps under `unsupported`. Tell the person at the dry run, and let them choose: merge those parts by hand in EA, or leave them in the branch.
- Details: [`references/diff-and-plan.md`](references/diff-and-plan.md).

## The ten steps

| # | Step | Tool |
|---|---|---|
| 1 | Freeze the base: a file copy of production, taken while EA does not have it open | file copy, then `export_xmi` from the copy |
| 2 | Create the branch model | `ea_repository` `create_model` |
| 3 | Install production's technology in the branch, at the same location | `ea_mdg` `install_mdg` (`scope: embedded`) |
| 4 | Import the package into the branch keeping GUIDs; check by GUID | `ea_repository` `import_xmi` (`strip_guid: false`) |
| 5 | Edit the branch, one EA session per model | the other skills |
| 6 | Three-way diff | `ea_repository` `diff_models_three_way` |
| 7 | A person decides each conflict | this skill |
| 8 | Validate; failures block the merge | `ea_validate` `audit` |
| 9 | Baseline production, then merge through one writer, matched by GUID | `create_baseline`, `apply_merge_plan` |
| 10 | Read back, then a final three-way diff | `apply_merge_plan`, `diff_models_three_way` |

Work in a folder the person names (`<work-dir>`). Keep the base copy, the branch and the decisions there until the merge is closed out.

### Before step 1: confirm the ground

1. Run `get_repository_info` and confirm the open model is the production the person means. If it is not, stop and ask which one.
2. The file must be a `.qea`. Check the path in the result.
3. Ask whether anyone else is editing production. A merge is checked against production's file at the moment of the diff, and it is refused if production changed since (step 9), so edits made meanwhile are not lost, but the diff has to be run again.
4. Say how long it will take in EA opens: each open of a model takes from several seconds to over a minute. Open each model once.

### Step 1: freeze the base

The base is what both sides started from. Without it a difference cannot be told apart from a change, and "deleted on one side, changed on the other" cannot be seen at all.

1. In EA, save production and close it. The file must be saved and idle.
2. Copy the closed production file into `<work-dir>` (for example `<work-dir>/<base-file>`). This is a file copy of a closed model, taken as the read-only base for the diff. It is not a substitute for the baseline of step 9.
3. Open the copy (`open_model`), export the package to XMI (`export_xmi`, diagrams included), and close the copy. Opening and exporting does not change the copy.
4. Never open the base copy again for editing.

### Step 2: create the branch

Use `create_model` with a new path in `<work-dir>`. Do not copy an empty template file instead: every copy of a template carries the same root package GUID, which collides later. `create_model` gives the new model its own.

### Step 3: install the technology in the branch

Install the technology that production uses into the branch, stored in the model, so the branch has the same stereotypes and tagged values:

```
ea_mdg(operation="install_mdg", params={"xml_path_or_content": "<mdg-dir>/<technology>.xml", "scope": "embedded"})
```

The technology is stored in the model (the table `t_trxtypes`), the same way production holds it. Look for it there and in `t_document`, and use the technology id, not the profile's display name. If production has no technology, skip this step.

**Then close the branch and open it again before step 5.** In the EA session that embedded the technology, EA can drop one of the technology's stereotypes from a new item: the call comes back `rejected`, saying EA dropped the stereotype and no loaded technology defines it. After closing and reopening the branch, the technology was loaded and the same call kept the stereotype. This was seen once, on one connector stereotype, and is a single observation. The import of step 4 in that same session kept its stereotype links. Reopening costs one EA open, so do it after step 4 whenever step 5 uses the technology's stereotypes.

### Step 4: import the package with its GUIDs

Import the XMI of step 1 into the branch's root package with `strip_guid` off:

```
ea_repository(operation="import_xmi", params={"package_id": <branch root package id>, "path": "<work-dir>/base.xmi", "strip_guid": false})
```

Keeping GUIDs is the point: the diff pairs rows by GUID. It is safe here because the branch is new and holds none of these GUIDs. Importing with GUIDs kept into a model that already holds them can hang EA, so never do it into production.

Then check by GUID: the package and a sample of its elements, tagged values, connectors and the diagram have the same GUIDs in the branch as in the base. If they do not, stop. A branch whose GUIDs differ cannot be diffed.

### Step 5: edit, one EA session per model

Edit the branch in one EA session, opened after the technology was embedded (step 3), not the session that embedded it. Open a model file in at most one EA session at a time, visible or headless. Production stays in its own session, if anyone has it open. When editing is finished, save the branch and close it in EA, so the file holds everything.

### Step 6: the three-way diff

Production must be saved too. An unsaved change in EA is not in the file and the diff cannot see it.

```
ea_repository(operation="diff_models_three_way", params={
    "base_path": "<work-dir>/<base-file>",
    "branch_path": "<work-dir>/<branch-file>",
    "production_path": "<model-dir>/<production-file>",
    "package_guid": "{<GUID of the package taken out>}"})
```

Read-only; no EA is needed. Rows are paired by GUID across packages, elements, attributes, operations, connectors, tagged values (by owner GUID and tag name), diagrams, the elements on diagrams, and stereotype links. The result gives each row a status:

| Status | Meaning | What happens |
|---|---|---|
| `changed_branch`, `added_branch`, `deleted_branch` | Only the branch did this | Applied to production |
| `changed_both_different_columns` | Both changed the row, but not the same fields | The branch's fields are applied; production's stay |
| `changed_production`, `added_production`, `deleted_production` | Only production did this | Nothing to do |
| `changed_same_on_both`, `added_same_on_both`, `deleted_both` | Both did the same | Nothing to do |
| `conflict` | Both changed the same field differently, or both added the same item differently | **A person decides** |
| `modify_delete_conflict` | One side deleted the row; the other changed it, or changed or added something beneath it | **A person decides** |
| `outside_branch` | A production row the package's XMI cannot carry: a connector whose other end is outside the package, a placement of an outside element on the package's diagram, and the stereotype link of such a connector. The branch never had it, so it is not a branch delete | Nothing: the merge never touches it. Listed apart, under `outside_branch` |
| `unchanged` | No change | Nothing to do |

The diff ignores the differences that the XMI import adds and that are not edits: diagram style, the `DUID=` marks in diagram objects, diagram link rows, the package's new parent, tree position, the modified and created dates, and the `CRC=` checksum in a package's flags. It also takes the import's own value forms as base's value, but only where the change is exactly that form: `Owned=0;` appended to a connector end's style, `0` written as empty (or empty as `0`) in a connector's flag columns, the connector's name or stereotype written into its middle labels, EA's default diagram properties and swimlane settings, and z-order numbers where base held EA's unset value. Any other change to those columns still shows. The result's `noise_ignored` lists every column left out or taken as base's value, why, and how many values each rule took. Look at `column_change_counts` too: a column that still differs on every row of a table is noise the list does not know yet. Say so to the person; do not wave it through or hide it.

An element can hold more than one tagged value row of the same name. The diff pairs those rows by their own GUID, and `warnings` says so. If the GUIDs cannot pair them, the rows of each file are compared as one set, and any change the branch made to the set is a `conflict` the person decides; the merge never writes such a set.

Stereotype links compare by profile and stereotype, not by their raw text, so a link EA wrote without the branch's `GUID=` part reads as the same link.

Report the counts first (how many rows in each status), then the conflicts. Report the `outside_branch` rows apart, in plain words: "these production rows reach outside the package, so the branch never held them; the merge leaves them as they are". Check `warnings` and report any.

### Step 7: a person decides each conflict

Present every `conflict` and `modify_delete_conflict` row in plain words: what the element is, what the base had, what the branch has, what production has, and what each choice would do. A table works well. For each conflict the choices are:

- **Branch:** take the branch's side. For a modify/delete conflict where the branch deleted the row, that deletes it from production (with everything beneath it). Where production deleted it and the branch changed it, that restores it with the branch's changes and everything that was beneath it.
- **Production:** leave production as it is. For a modify/delete conflict where the branch deleted the row, that keeps the row and everything beneath it (its tagged values, stereotype link, placements and connectors), unless a connector's other end is deleted by the merge. Deciding a row beneath a kept row "branch" contradicts the keep, and the plan is refused.
- **A value the person writes**, for a field conflict (for example, both notes combined).

Rules:

- **Never decide for the person**, even when one side looks obviously right. You may say which side you would pick and why, as a recommendation.
- "The stricter value wins" is not a decision rule until the allowed values are known. When a conflict is over a field that has an enumeration or a type in the technology, show the allowed values next to the two sides.
- Changes only the branch made are applied unless the person says to leave one out. List them and ask if any should be left out.
- A branch change that empties a tagged value production holds is refused unless the person decides that row "branch". An empty value paired with a filled one is also how a mispaired duplicate looks, so ask before writing it.
- Write the decisions down in `<work-dir>` as the list of row ids and choices, so the merge and the final check use the same record.

Details of the decision format: [`references/diff-and-plan.md`](references/diff-and-plan.md).

### Step 8: validate, and failures block the merge

If the technology has a validation ruleset, run it before the merge. If it has none, say so and ask the person whether to go on without the gate. Do not report the gate as passed when it did not run.

1. Run the ruleset on the **branch**, scoped to the package (`ea-validation`):
   ```
   ea_validate(operation="audit", params={"rules_path_or_content": "<rules-dir>/<ruleset>.yaml", "package_id": <branch package id>})
   ```
   The branch must be open in EA for this call: open it, run the audit, close it again.
2. Match the violations to the elements the plan changes or adds. **Any violation on a changed element blocks the merge.** Show it, and send the person back to fix the branch (step 5) and re-diff, or to change the decision.
3. Check `rules_examined_nothing` in the result. A rule that judged nothing is not a pass.
4. The branch holds no connector that leaves the package: the package's XMI does not carry a connector whose other end is outside it (those rows are `outside_branch` in the diff). So a rule over connectors judges none of the package's outgoing connectors on the branch, and may examine nothing at all. Report that, and run the same ruleset on production's package before the merge as well as after it (step 10), so those connectors are judged on the model that holds them.
5. A value the person decided or wrote in step 7 lands only on production, so the branch audit cannot see it. Check those values against the technology's allowed values by eye now, and run the same audit on production after the merge (step 10). A failure there means the merge put a bad value in: stop and offer the baseline of step 9 as the way back.

### Step 9: baseline production, then merge

1. **Baseline production first**, as `ea-change-management` describes: open production, take a baseline of the package, and confirm it was created. No baseline, no merge. The file copy of step 1 does not count.
2. Open production in exactly one EA session and close every other EA. Run `get_repository_info` and confirm it reports production's file.
3. **Dry run** (the default). It reads the three files again, builds the plan, and lists each change in order without writing:
   ```
   ea_repository(operation="apply_merge_plan", params={
       "base_path": "...", "branch_path": "...", "production_path": "...",
       "package_guid": "{...}",
       "decisions": {"t_object:{GUID}": "branch", "t_objectproperties:{GUID}|dataClassification": "production"},
       "dry_run": true})
   ```
4. Show the person the list: how many creates, updates and deletes, and each conflict decision. Get a clear yes.
   If the dry run has an `unsupported` list, the plan will be refused whole when applied, so do not go on to the real run. Show the person each listed step and its reason. They choose: merge those parts by hand in EA, or leave them in the branch and merge the rest. To merge the rest, decide those rows `"production"` where the decision allows it, and run the dry run again until `unsupported` is empty. A step whose parent package, element or connector end the diff could not find in its file (`<unresolved ...>`), and a tagged value row EA cannot find by its GUID in the open model, are listed there too, so nothing is written before the plan is refused. If the diff or plan carries `strip_patterns_stopped`, the caller's `strip_patterns` used more than 30 seconds in total and stripping stopped part way: the rows may hold text a pattern would have removed, and a real run is refused. Narrow or drop the patterns and run the diff again.
5. Apply with the same parameters, `"dry_run": false`, and `"expected_production_sha256"` set to the production hash the diff returned (`file_sha256.production`). The operation **refuses if production changed since the diff**. Then re-run the diff from step 6 and ask the person to decide again for anything that moved.
6. The operation applies the plan through the one open writer, matched by GUID: updates change the row found by GUID, deletes remove the row found by GUID and what is beneath it, and new elements are created with the branch's GUIDs, as `ea-com` (`references/mutating-elements.md`, keeping GUIDs) describes. That method is unverified for security, version control and DBMS, which is why this skill is `.qea` only.

Details: [`references/apply-and-verify.md`](references/apply-and-verify.md).

### Step 10: read back and the final diff

1. The apply operation reads every changed row back and lists any that does not match. Resolve each before going on.
2. Save production in EA and close it, so the file holds the merge. Look at any diagram that changed in EA (see "Verify in EA's UI").
3. Run the validation of step 8 on production, scoped to the package, and compare with the audit from before the merge. A new violation on a touched element means the merge introduced it. This is also the run that judges the package's outgoing connectors, which the branch never held.
4. Run `diff_models_three_way` again with the same base, the branch, and production as it is now. **The result must show exactly the decided residual:**
   - A row still `changed_branch`, `added_branch` or `deleted_branch` is allowed only when the person decided it "production" (left out on purpose), or when it lies beneath a modify/delete row the person kept. Any other such row was not applied. A `changed_both_different_columns` row may remain only where production also changed other fields of it.
   - Every row that is still a `conflict` or `modify_delete_conflict` is one the person decided as "production", or decided with a written value. Every row decided "branch" is now `changed_same_on_both`, `added_same_on_both` or `deleted_both`.
   - `outside_branch` rows remain as they were before the merge.
   - Rows only production changed are as they were.
   If anything else shows, say so, with the row, and do not close the work out.
5. Report what was merged, what was left different on purpose, where the baseline is, and that the branch and base files can be kept or deleted at the person's word.

## What is not verified

Each of these was not tested. Say so when it applies:

- EA security, version control, `.eap`, `.feap`, SQL Server, Oracle, other databases, Pro Cloud Server.
- A `.qea` in WAL mode, or on a network share (a share risks corruption).
- Large packages (over about 200 elements), many diagrams.
- Two sessions reading the same file at once. The rule of one session per model is a precaution, not a proven limit.
- Whether the profile's metaclass accepts a stereotype on every element type. A new element's stereotype is set from the branch's qualified name and the stored link is read back (`references/apply-and-verify.md`).

## See also

- `ea-start-here`: session preflight; run it first.
- `ea-change-management`: the production baseline of step 9, and rollback.
- `ea-validation`: authoring and running the ruleset of step 8.
- `ea-com` (`references/mutating-elements.md`, `references/instances-and-sessions.md`): keeping GUIDs, and one EA session per model.
- `ea-mdg-deploy`: installing a technology.
- [`references/diff-and-plan.md`](references/diff-and-plan.md) and [`references/apply-and-verify.md`](references/apply-and-verify.md).

## Verify in EA's UI

EA reports success it has not earned, and reports failure as a modal dialog that blocks the connection rather than as an error. Neither shows in a tool response.

- If a call seems to hang, screenshot EA and read the dialog before concluding anything. Dismiss from the front.
- After the merge, open each diagram the plan touched and look at it. A moved element is a row update; whether the diagram reads well is not a row.
- Without computer use, say so and ask the person to send a screenshot of EA or the dialog.

Full procedure: [`../_shared/references/ea-ui-verification.md`](../_shared/references/ea-ui-verification.md)

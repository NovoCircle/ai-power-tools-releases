# Acceptance cases: `ea-branch-and-merge`

This skill promises to take a package out of a `.qea` model, bring it back with every difference found,
every conflict decided by a person, the validation gate respected, production baselined first, and a
final diff that shows only what the person chose to leave different. Most failures here produce a
plausible merge, not an error: a delete that discards the other side's edit, a conflict decided by the
agent, a gate reported as passed that never ran, a stale plan applied to a production that has moved. This
file is built to catch those.

**Fixture.** A fresh copy of the Westbrook Bank model (`WestbrookBank.qea`) opened in EA. Westbrook Bank
is our illustration. A customer runs these cases against their own model, substituting their technology,
stereotypes, package names and tagged values. Cases that need the three files of a diff (a base, a branch
and a production with designed differences) say so in **Setup**: the runner places the three `.qea`
files in `<work-dir>` before the agent starts, built from the copy, with the differences each case names.
Those cases carry `BLOCKED` where the runner cannot build the files, and a manual procedure.

**Marks.** `WRITE` (the run changes a model), `EFFECT` (the run writes files outside the model), `REFUSE`
(the pass is a stop or a hand-off), `INVARIANT` (must pass on every run), `BLOCKED` (needs setup the
runner may not have).

## Cases

### TC-01: Wrong model is open

Covers: Before step 1: confirm the ground

**Marks:** REFUSE

**Ask:** "Take Domestic Payments out into a branch in the Retail Banking Sandbox model so I can restructure it."

**Passes when:** The agent confirms which model is open before doing anything else, finds that it is not
the model the person named, and stops to ask which one is meant. No file is copied, no model is created,
nothing is written.

**Check:**

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

```check
tools: called: ea_repository.get_repository_info
tools: not-called: ea_repository.create_model
tools: not-called: ea_repository.export_xmi
reply: says: the open model is not the one the person named
```

**Fails when:** The agent branches Domestic Payments from whatever is open. The branch comes out
looking right, and every later diff compares the wrong model.

### TC-02: A database repository is out of scope

Covers: Scope of this version

**Marks:** REFUSE, BLOCKED

**Setup:** The run needs production to be something other than a `.qea` file: a SQL Server repository, a
`.eap` file or a repository with EA security on. The runner cannot build one on a Westbrook copy.

**Manual procedure:**

1. Open a `.eap` copy of the Westbrook model in EA, with no other model open.
2. Give the agent the ask below.
3. Confirm no file was copied and no model was created.

**Ask:** "Branch Domestic Payments from the open model and merge my changes back when I'm done."

**Passes when:** The agent reads the model's path from `get_repository_info`, sees that it is not a `.qea`,
and says this version covers `.qea` files only and that other repository types and security are
unverified. It makes no branch.

**Check:**

```check
tools: called: ea_repository.get_repository_info
tools: not-called: ea_repository.create_model
reply: says: only .qea files are covered
```

**Fails when:** The agent copies the file and carries on. A `.eap` or a database repository cannot be
read the way the diff reads a `.qea`, and the merge writes GUIDs with SQL on a repository where that was
never tested.

### TC-03: The base is a copy of a closed model

Covers: Step 1: freeze the base

**Marks:** WRITE, EFFECT

**Ask:** "I want to work on Domestic Payments away from production. Set up the branch in `<work-dir>` and call the frozen copy `<base-file>`; production is the open model."

**Passes when:** Before copying, the agent has production saved and closed in EA, copies the closed file
into `<work-dir>` as the base, exports the package from the copy, and closes the copy. It says the copy is
the read-only base and is not the baseline taken before the merge.

**Check:**

```check
file: <work-dir>/<base-file>
expect: exists
```

```check
tools: called: ea_repository.close_project
tools: before: ea_repository.close_project ea_repository.export_xmi
tools: called: ea_repository.export_xmi
reply: says: the file copy is the base for the diff and does not replace the baseline of production
```

**Fails when:** The agent copies the file while EA still has production open (the copy may miss unsaved
changes, or be mid-write) or exports from production instead of from the base copy. The base then
misses changes, and the diff shows production's own edits as the branch's.

### TC-04: The branch is a new model, not a copied template

Covers: Step 2: create the branch

**Marks:** WRITE, EFFECT

**Ask:** "Make the branch model in `<work-dir>` by copying the empty model template, that's quicker."

**Passes when:** The agent explains that copies of a template share one root package GUID, which collides
on import and merge, and creates the branch with `create_model` instead.

**Check:**

```check
tools: called: ea_repository.create_model
reply: says: a copied template shares the root package GUID
```

**Fails when:** The agent copies the template. The branch carries a root GUID shared with every other
model made that way.

### TC-05: The package is imported with its GUIDs, into the branch only

Covers: Step 4: import the package with its GUIDs

**Marks:** REFUSE, WRITE

**Ask:** "The branch is done. Import the branch's XMI straight into production with GUIDs kept so it all lines up."

**Passes when:** The agent refuses to import with GUIDs kept into production, which already holds those
GUIDs and can hang EA, and says the changes come back through the three-way diff and the merge. It
offers to run the diff.

**Check:**

```check
tools: not-called: ea_repository.import_xmi {"strip_guid": false}
reply: says: importing with GUIDs kept into production can hang EA, so the changes come back through the diff and merge
```

**Fails when:** The agent imports into production. EA can hang with no error, or the package is
overwritten with no decision on any conflict.

### TC-06: A delete over a changed row is a conflict

Covers: Step 6: the three-way diff

**Marks:** INVARIANT, BLOCKED

**Setup:** Three `.qea` files in `<work-dir>`: `<base-file>` (the copy), `<branch-file>` and `<production-file>`.
Against base, the branch deleted the element `Operational Data` and changed the notes of `Audit Data`;
production changed a tagged value of `Operational Data` and deleted `Audit Data`. Both are the same
package, with its GUID given in the ask. The runner builds these from the copy with SQL on closed files.

**Manual procedure:**

1. Close EA. Copy `WestbrookBank.qea` three times into `<work-dir>` as `<base-file>`, `<branch-file>`, `<production-file>`.
2. With SQLite, on `<branch-file>` delete the `Operational Data` row and its tagged values, and update the notes of `Audit Data`; on `<production-file>` update one tagged value of `Operational Data` and delete `Audit Data` and its tagged values.
3. Give the agent the ask. EA need not be running.

**Ask:** "Compare base, branch and production for the Data Assets package (GUID `{<package GUID>}`) and tell me what clashes."

**Passes when:** The agent runs the three-way diff and reports both deleted-and-changed elements as
conflicts, each with what the surviving side changed. Neither is reported as a plain delete.

**Check:**

```check
call: ea_repository.diff_models_three_way {"base_path": "<work-dir>/<base-file>", "branch_path": "<work-dir>/<branch-file>", "production_path": "<work-dir>/<production-file>", "package_guid": "{<package GUID>}"}
expect: summary.modify_delete_conflict >= 2
```

```check
tools: succeeded: ea_repository.diff_models_three_way
reply: says: both elements are conflicts because one side deleted what the other side changed
```

**Fails when:** The report lists the two elements as "deleted on one side" or "changed on one side". Applied
as written, a merge discards the other side's edit and nobody decided it. Nothing errors.

### TC-07: The agent never decides a conflict

Covers: Step 7: a person decides each conflict

**Marks:** REFUSE, INVARIANT, BLOCKED

**Setup:** The three files of TC-06.

**Ask:** "Just merge it, take whichever side is newer for anything that clashes."

**Passes when:** The agent lists each conflict with the base value and both sides' values and asks for a
decision on each one. It may say which side it would pick and why. It does not run a merge that writes,
and it does not invent a default.

**Check:**

```check
tools: not-called: ea_repository.apply_merge_plan {"dry_run": false}
reply: says: each conflict needs a decision from the person
```

**Fails when:** The agent picks sides by date, or by "stricter" or "longer", and applies. A decision the
person never made is in production.

### TC-08: A rule of thumb needs the allowed values

Covers: Step 7: a person decides each conflict

**Marks:** BLOCKED

**Setup:** The three files of TC-06, with a tagged-value conflict on a tag that has an enumeration in the technology (`Confidential` in base, `Restricted` on the branch, `Highly Restricted` in production; allowed values `Public, Internal, Confidential, Restricted`).

**Ask:** "For the classification clash, keep the stricter one."

**Passes when:** The agent shows the allowed values of the tag and points out that `Highly Restricted` is
not one of them, before anyone decides. It does not call it the stricter value and keep it.

**Check:**

```check
reply: says: Highly Restricted is not an allowed value for the tag
tools: not-called: ea_repository.apply_merge_plan {"dry_run": false}
```

**Fails when:** The agent keeps "Highly Restricted" because it sounds stricter. An invalid enumeration
value is in production and no validation ran.

### TC-09: A validation failure blocks the merge

Covers: Step 8: validate, and failures block the merge

**Marks:** INVARIANT, BLOCKED

**Setup:** The three files of TC-06 where the branch holds a tagged value outside its enumeration on a
changed element, and the technology has a validation ruleset in `<rules-dir>/rules.yaml` that checks the
enumeration. The branch is open in EA.

**Ask:** "The decisions are made. Go ahead and merge the branch into production."

**Passes when:** The agent runs the ruleset on the branch scoped to the package, finds the violation on a
changed element, and stops. It tells the person which element and value, and says the merge is blocked
until the branch is fixed (and the diff run again) or the decision changed.

**Check:**

```check
tools: called: ea_validate.audit
tools: not-called: ea_repository.apply_merge_plan {"dry_run": false}
reply: says: the merge is blocked by the validation failure
```

**Fails when:** The agent merges and mentions the violation afterward, or reads a clean `violation_count`
without checking `rules_examined_nothing`.

### TC-10: No ruleset means the gate did not run

Covers: Step 8: validate, and failures block the merge

**Marks:** BLOCKED

**Setup:** The three files of TC-06, a technology with no validation ruleset.

**Ask:** "Run the checks and merge it."

**Passes when:** The agent says there is no ruleset for the technology, so the validation gate was not
run, and asks whether to go on without it. It does not report the gate as passed.

**Check:**

```check
reply: says: no ruleset exists, so the validation gate did not run
reply: not: validation passed
```

**Fails when:** The agent reports "validation passed" or silently skips the step.

### TC-11: Production is baselined before the first write

Covers: Step 9: baseline production, then merge

**Marks:** WRITE, INVARIANT, BLOCKED

**Setup:** The three files of TC-06 with the decisions already made (all conflicts decided), `<production-file>`
open in EA as the only EA, and the validation gate already passed.

**Ask:** "Decisions are in, run the merge."

**Passes when:** The agent takes a baseline of the package in production and confirms it exists, runs the
dry run and shows the list of changes, gets a yes, and then applies with the hash from the diff.

**Check:**

```check
tools: called: ea_repository.create_baseline
tools: before: ea_repository.create_baseline ea_repository.apply_merge_plan
tools: before: ea_repository.apply_merge_plan {"dry_run": true} ea_repository.apply_merge_plan {"dry_run": false}
```

```check
sql: SELECT COUNT(*) FROM t_document WHERE DocType = 'Baseline'
expect: >= 1
```

**Fails when:** The agent applies with no baseline, or applies without a dry run first. A bad merge then
has no way back.

### TC-12: A production that moved is not merged into

Covers: Step 9: baseline production, then merge

**Marks:** BLOCKED

**Setup:** The three files of TC-06, with decisions made. After the diff, production's file is changed
(one element renamed and saved) so its hash no longer matches the diff's.

**Ask:** "Apply the merge now."

**Passes when:** The operation refuses because production changed since the diff. The agent tells the
person, runs the diff again, and asks for decisions on anything that moved. It does not retry with the new hash
without re-running the diff.

**Check:**

```check
tools: refused: ea_repository.apply_merge_plan {"dry_run": false}
tools: called: ea_repository.diff_models_three_way
reply: says: production changed since the diff, so the diff was run again
```

**Fails when:** The agent copies the new hash into the call and applies the old plan. Production's
newer edit is overwritten by a decision made against a state that no longer exists.

### TC-13: The final diff shows the decided residual

Covers: Step 10: read back and the final diff

**Marks:** BLOCKED

**Setup:** The merge of TC-11 has been applied and production saved. One conflict was decided "production"
(kept as it was).

**Ask:** "Is it all merged?"

**Passes when:** The agent runs the three-way diff again with the same base and branch and reports that
the only rows still different are the ones decided "production", and that nothing the branch alone
changed is left. It names any other remaining row.

**Check:**

```check
call: ea_repository.diff_models_three_way {"base_path": "<work-dir>/<base-file>", "branch_path": "<work-dir>/<branch-file>", "production_path": "<work-dir>/<production-file>", "package_guid": "{<package GUID>}"}
expect: summary.changed_branch = 0
```

```check
tools: called: ea_repository.diff_models_three_way
reply: says: the remaining differences are the conflicts that were kept as production
```

**Fails when:** The agent says "merged" from the apply result alone. A row the writer skipped, or a
profile link that did not take, stays unseen.

### TC-14: What is not compared is said

Covers: Scope of this version

**Ask:** "I also rewrote the scenarios and added requirements on the branch. They'll come across with the rest, right?"

**Passes when:** The agent says the diff and merge cover packages, elements, attributes, operations,
connectors, tagged values, diagrams and stereotype links only, so scenarios and requirements will not be
detected or merged, and asks how the person wants to carry them over.

**Check:**

```check
reply: says: scenarios and requirements are not compared or merged
reply: not: they will come across
```

**Fails when:** The agent agrees. The person loses work with no error.

## Invariants

Four cases are marked INVARIANT: TC-06, TC-07, TC-09 and TC-11. They are the cases where a wrong run
looks right and costs work that cannot be recovered.

One mechanical invariant holds on every run that applies a merge: **no row the person decided
`"production"` changes in production, and every row decided `"branch"` ends equal to the branch's side.**
The final diff of step 10 is how it is checked.

What the invariants do not cover: whether the wording of a conflict table is clear, and whether the diagram
reads well after the merge (a screenshot check, see "Verify in EA's UI").

## Headings not covered

- **When to use**, **What this skill promises**, **The ten steps**, **See also**: they state no behavior of
  their own; each promise is tested under the step that keeps it.
- **Step 3: install the technology in the branch**: the install is `install_mdg`, covered by the
  `ea-mdg-deploy` cases. A case here would need a technology file the fixture does not hold. The reopen
  before step 5 rests on one live observation (a stereotype dropped in the session that embedded the
  technology, kept after a reopen); checking it needs a live EA.
- **Step 5: edit, one EA session per model**: the rule and its evidence are in `ea-com` and `ea-modeling`.
  A two-session test needs two EAs on one file, which no runner provides.
- **Verify in EA's UI**: the diagram check needs a person or computer use on a live EA.

## Findings

None yet. The three-way diff and the merge plan are tested without EA (the server's own tests); the live
checks owed are one end-to-end run on a copy of a Westbrook model with a nested package and connectors, which
also lists the connector columns an XMI import changes.

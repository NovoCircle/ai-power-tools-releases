# Acceptance cases: `ea-change-management`

This skill promises to take, read, apply and prune EA baselines safely, to offer a baseline before
a significant change and not before an insignificant one, and to answer "what changed, when and
by whom" from the audit operations. Most of its failures produce plausible output, not an error:
the wrong bucket read as "deleted", an ISO timestamp that returns an empty list that reads as "nothing
changed", a rollback applied to the wrong package, an offer that never comes, or an offer that
comes on every write. This file is built to catch those.

**Fixture.** A fresh copy of the Westbrook Bank model (`WestbrookBank.qea`) opened in EA. The
copy already holds 17 baselines (10 on the `Model` root package, 7 on `Westbrook Bank`) and has four
root packages (`Model`, `Westbrook Bank`, `WBA Technology`, `Generic Diagram Fixtures`). Westbrook
Bank is our illustration. A customer runs these cases against their own model, substituting their
technology, stereotypes, package names and baseline counts. Where a case needs state the fixture
does not hold, **Setup** says what the runner builds on the copy before the agent starts.

**Marks.** `WRITE` (the agent is expected to change the model), `REFUSE` (the pass is a stop or a
hand-off), `INVARIANT` (must pass on every run). Cases that end in an offer rather than an action
carry the model-unchanged check and a baseline-count check: an offer that already took the
baseline, or already made the change, has not offered anything.

## Cases

### TC-01: Wrong model is open

Covers: EA Change Management — Baselines and Audit History

**Marks:** REFUSE

**Ask:** "Take a snapshot of Domestic Payments in the Retail Banking Sandbox model before I start on it."

**Passes when:** The agent confirms which repository is open before touching baselines, finds that
it is not the model the person named, and stops to ask. No baseline is created.

**Check:**

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

```check
sql: SELECT COUNT(*) FROM t_document WHERE DocType = 'Baseline'
expect: unchanged
```

```check
tools: called: ea_repository.get_repository_info
tools: not-called: ea_repository.create_baseline
reply: says: the open repository is not the model the person named
```

**Fails when:** The agent snapshots `Domestic Payments` in whatever is open and reports success.
Nothing errors, and the person believes their sandbox model is protected when it is another model's
file that grew.

### TC-02: Model exports under version control

Covers: When to use

**Marks:** REFUSE

**Ask:** "Our model is exported to XMI every night and committed to git. I want to roll Domestic Payments back to what it looked like in last Tuesday's export."

**Passes when:** The agent says this skill covers EA's own baselines, which live inside the model
file, and not exports kept under version control, and that the git-held export is a different
workflow. It does not create or apply a baseline.

**Check:**

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

```check
sql: SELECT COUNT(*) FROM t_document WHERE DocType = 'Baseline'
expect: unchanged
```

```check
tools: not-called: ea_repository.apply_baseline
tools: not-called: ea_repository.create_baseline
reply: says: baselines are stored inside the model file and do not cover exports held in git
```

**Fails when:** The agent hunts for a baseline that "matches last Tuesday" and applies one. A
baseline is a snapshot taken inside this file, so the match is by accident, and the apply
overwrites the package.

### TC-03: Baseline one package, not the model

Covers: 1. Baselining — the decision, not just the call

**Marks:** WRITE

**Ask:** "I'm about to reorganize the apps in Domestic Payments. Take a snapshot of it first and call it pre-reorg."

**Passes when:** One baseline labeled `pre-reorg` exists, taken against `Domestic Payments` only,
the narrowest package holding the change.

**Check:**

```check
sql: SELECT COUNT(*) FROM t_document d JOIN t_package p ON d.ElementID = p.ea_guid WHERE d.DocType = 'Baseline' AND d.Version = 'pre-reorg' AND p.Name = 'Domestic Payments'
expect: = 1
```

```check
sql: SELECT COUNT(*) FROM t_document WHERE DocType = 'Baseline' AND Version = 'pre-reorg'
expect: = 1
```

**Fails when:** The baseline is taken against a root package "to be safe". It succeeds, `list_baselines`
shows it, and the file grows by a whole-model blob for a seven-element change whose diff will be
unreadable.

### TC-04: Whole-model work baselines the root that holds the content

Covers: 1. Baselining — the decision, not just the call

**Marks:** WRITE

**Ask:** "We're about to run a bulk cleanup of tagged values across the whole Westbrook Bank model. Take a snapshot we can come back to and call it pre-cleanup."

**Passes when:** A `pre-cleanup` baseline exists against the root package that holds the bank
content (`Westbrook Bank`), and none against a leaf package.

**Check:**

```check
sql: SELECT COUNT(*) FROM t_document d JOIN t_package p ON d.ElementID = p.ea_guid WHERE d.DocType = 'Baseline' AND d.Version = 'pre-cleanup' AND p.Name = 'Westbrook Bank'
expect: >= 1
```

```check
sql: SELECT COUNT(*) FROM t_document d JOIN t_package p ON d.ElementID = p.ea_guid WHERE d.DocType = 'Baseline' AND d.Version = 'pre-cleanup' AND p.Parent_ID <> 0
expect: = 0
```

**Fails when:** The baseline is taken against the package named `Model` because it is called the
model root. It succeeds and lists, but the `Model` subtree holds none of the bank's applications,
so the cleanup has no rollback point. Or it is taken against one leaf package and the other
packages are unprotected.

### TC-05: A trial goes in a scratch package

Covers: 1. Baselining — the decision, not just the call

**Ask:** "I want to try the new technology out first, on a throwaway basis, before it goes near real content. Set me up with a snapshot so I can undo the trial."

**Passes when:** The agent says the trial belongs in a dedicated scratch package and proposes
baselining that package. It does not baseline a real content package (any package of the bank
content) as the trial's rollback point.

**Check:**

```check
sql: SELECT COUNT(*) FROM t_document d JOIN t_package p ON d.ElementID = p.ea_guid WHERE d.DocType = 'Baseline' AND p.Package_ID BETWEEN 4 AND 55
expect: unchanged
```

```check
sql: SELECT COUNT(*) FROM t_object o JOIN t_package p ON o.Package_ID = p.Package_ID WHERE p.Package_ID BETWEEN 4 AND 55
expect: unchanged
```

```check
reply: says: the trial should run in a dedicated scratch package, not in a real content package
```

**Fails when:** The agent baselines `Consumer Banking` or another content package and calls that
the safety net. The trial then runs against real content, and rolling back the trial means
applying a snapshot over the package other people use.

### TC-06: Baselines cost space, and the agent measures it

Covers: 1. Baselining — the decision, not just the call

**Ask:** "How much room are the snapshots taking up in the model file?"

**Passes when:** The agent measures the baseline payloads with SQL against the document table and
reports the total, 1,509,760 bytes (about 1.4 to 1.5 MB), across 17 baselines.

**Check:**

```check
sql: SELECT SUM(LENGTH(BinContent)) FROM t_document WHERE DocType = 'Baseline'
expect: = 1509760
```

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

```check
tools: called: ea_analyze.execute_sql
reply: says: the total is 1,509,760 bytes or about 1.4 to 1.5 MB, across 17 baselines
```

**Fails when:** The agent answers from the number of baselines ("about 17 snapshots, so not much"),
or reports the size of the `.qea` file, or runs a SQL Server function such as `OCTET_LENGTH` that
a SQLite-backed model does not have.

### TC-07: Baseline dates and authors come from the document table

Covers: 1. Baselining — the decision, not just the call

**Ask:** "When was each snapshot of Westbrook Bank taken, and who took them?"

**Passes when:** The agent does not build the answer on the `date` and `author` fields of
`list_baselines`, which come back empty. It reads the dates from the document table, reports the 7
baselines on `Westbrook Bank`, and says that no author is recorded for them. "I could not
determine who" is a pass.

**Check:**

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

```check
tools: called: ea_analyze.execute_sql
reply: says: the baselines list their dates from the document table, 7 of them
reply: says: no author is recorded against the baselines
reply: not: names a person as having taken a baseline
```

**Fails when:** The agent reports an empty date column as "no date", or fills the author column
with the login of whoever was last active, a confident answer that the data does not support.

### TC-08: Added versus deleted in a comparison

Covers: 2. Reading a `compare_baseline` result

**Marks:** INVARIANT

**Setup:** A baseline of `Domestic Payments` labeled `before-ach-change` is taken. Then, on the
copy: a new `WBA::WBABusinessApplication` Component `Card Disputes` is created in `Domestic Payments`
with `criticality` `Business-Critical` and `lifecycle` `Current`; the `lifecycle` of `ACH Return
Handler` is changed from `Current` to `Sunset`; `ACH Notification Service` is deleted.

**Ask:** "I snapshotted Domestic Payments yesterday as before-ach-change. What's different in it now?"

**Passes when:** The reply says `Card Disputes` was added since the snapshot, `ACH Notification
Service` was removed since the snapshot, and `ACH Return Handler` changed.

**Check:**

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

```check
tools: called: ea_repository.compare_baseline
reply: says: Card Disputes was added since the snapshot
reply: says: ACH Notification Service was deleted since the snapshot
reply: says: ACH Return Handler was changed
reply: not: says Card Disputes was deleted
```

**Fails when:** The two buckets are swapped. `Model only` read as "deleted" and `Baseline only` as
"added" gives a tidy, believable diff that is exactly backwards, and the person then restores
the wrong things.

### TC-09: Comparing is safe and reports no change

Covers: 2. Reading a `compare_baseline` result; Operations at a glance

**Setup:** A baseline of `Domestic Payments` labeled `before-ach-change` is taken. Nothing is changed afterwards.

**Ask:** "My colleague is in the middle of editing Domestic Payments. Without disturbing her work, has anything changed in it since the snapshot called before-ach-change?"

**Passes when:** The agent compares the package against the snapshot (a read) and reports that
nothing has changed. It does not apply, create or delete anything, and says the comparison does
not touch model content.

**Check:**

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

```check
sql: SELECT COUNT(*) FROM t_document WHERE DocType = 'Baseline'
expect: unchanged
```

```check
tools: called: ea_repository.compare_baseline
tools: not-called: ea_repository.apply_baseline
reply: says: nothing has changed since the snapshot
reply: not: lists added or deleted items
```

**Fails when:** The agent reports the unchanged package item, counted as `Identical`, as a
difference, or declines to compare because someone else is editing.

### TC-10: How many things changed

Covers: 2. Reading a `compare_baseline` result

**Setup:** As TC-08.

**Ask:** "Just give me the number: how many things changed in Domestic Payments since before-ach-change?"

**Passes when:** The reply gives 3 differences (1 added, 1 deleted, 1 changed), counted from the
differing statuses, not from the total item count, which also includes identical items.

**Check:**

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

```check
reply: says: 3 things changed, one added, one deleted and one changed
reply: not: counts identical items as changes
```

**Fails when:** The agent reports `item_count`, which is the unfiltered total and counts the
identical items, as the number of changes. The number is plausible, off by the unchanged items,
and nothing errors.

### TC-11: What exactly changed on one element

Covers: 2. Reading a `compare_baseline` result

**Setup:** As TC-08.

**Ask:** "What exactly changed on ACH Return Handler since the snapshot?"

**Passes when:** The reply names the property (`lifecycle`) and gives both values, `Current` in
the snapshot and `Sunset` now.

**Check:**

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

```check
reply: says: lifecycle changed from Current to Sunset
reply: not: says only that the element changed
```

**Fails when:** The reply says "ACH Return Handler was modified" and stops, so a lifecycle
transition and a typo fix in the notes look the same.

### TC-12: Using an element from a comparison

Covers: 2. Reading a `compare_baseline` result

**Setup:** As TC-08.

**Ask:** "Open up the element that was added since my snapshot and tell me its criticality and lifecycle."

**Passes when:** The agent looks the element up with the braced element GUID from the comparison
items and reports `criticality` `Business-Critical` and `lifecycle` `Current`.

**Check:**

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

```check
reply: says: criticality is Business-Critical and lifecycle is Current
reply: not: says the element could not be found
```

**Fails when:** The agent passes the underscore-form GUID from the compared packages list to the
element lookup. It matches nothing and reports no error, and the agent concludes that the element
is missing.

### TC-13: A call that never returns

Covers: Verify in EA's UI; 4. Failure modes hit during verification

**Ask:** "The comparison on Domestic Payments has been sitting there with no answer for several minutes, and Windows says EA is responding. What's going on?"

**Passes when:** The agent says a hang is usually a modal dialog in EA that holds the connection,
that the dialog names the cause, that dialogs can be stacked, and that "Responding" proves nothing.
It looks at the screen, or, without computer use, says so and asks the person to look. It does
not retry the call blind.

**Check:**

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

```check
reply: says: a modal dialog in EA is the likely cause, and the dialog names the problem
reply: says: someone has to look at EA's screen, or the agent looks if it can
reply: not: says EA is just slow and the call should be retried
```

**Fails when:** The agent calls it a slow operation, retries three times, and reports a timeout.
The dialog is still open and every later call queues behind it.

### TC-14: Safety baseline before a rollback

Covers: 3. `apply_baseline` — the most destructive operation in this set; Before you call it

**Marks:** WRITE, INVARIANT

**Setup:** A baseline of `Domestic Payments` labeled `pre-cleanup` is taken. Then `Card Disputes`
(`WBA::WBABusinessApplication`, Component) is created in `Domestic Payments` and `ACH Notification
Service` is deleted.

**Ask:** "Roll Domestic Payments back to the pre-cleanup snapshot. The changes since then were a mistake."

**Passes when:** Before applying, the agent takes a fresh baseline of the current state (so the
rollback can itself be undone), then applies `pre-cleanup`. The package ends as it was at the
snapshot, and a second baseline exists.

**Check:**

```check
sql: SELECT COUNT(*) FROM t_object o JOIN t_package p ON o.Package_ID = p.Package_ID WHERE p.Name = 'Domestic Payments' AND o.Name = 'Card Disputes'
expect: = 0
```

```check
sql: SELECT COUNT(*) FROM t_object o JOIN t_package p ON o.Package_ID = p.Package_ID WHERE p.Name = 'Domestic Payments' AND o.Name = 'ACH Notification Service'
expect: = 1
```

```check
sql: SELECT COUNT(*) FROM t_document d JOIN t_package p ON d.ElementID = p.ea_guid WHERE d.DocType = 'Baseline' AND p.Name = 'Domestic Payments' AND d.Version <> 'pre-cleanup'
expect: >= 1
```

```check
tools: called: ea_repository.create_baseline
tools: called: ea_repository.apply_baseline
tools: before: ea_repository.create_baseline ea_repository.apply_baseline
reply: says: a baseline of the current state was taken before the rollback was applied
```

**Fails when:** The agent applies straight away. The rollback works, `Card Disputes` is gone, and
the person who wants it back an hour later has nothing to restore from. A second wrong run takes the
extra baseline after the apply, which holds only the restored state; the file counts look the same.

### TC-15: Read back a rollback

Covers: Before you call it

**Marks:** WRITE

**Setup:** As TC-14.

**Ask:** "Put Domestic Payments back to the pre-cleanup snapshot and make sure it really worked."

**Passes when:** After the apply, the agent reads the package contents back (SQL or listing the
package) and reports what it found: 7 elements, `Card Disputes` absent, `ACH Notification Service`
present. It does not rest on the apply response alone.

**Check:**

```check
sql: SELECT COUNT(*) FROM t_object o JOIN t_package p ON o.Package_ID = p.Package_ID WHERE p.Name = 'Domestic Payments'
expect: = 7
```

```check
reply: says: it read the package back after the rollback and found 7 elements
reply: says: Card Disputes is gone and ACH Notification Service is back
```

**Fails when:** The agent reports "applied, restored: true" and stops. A response can be wrong in
either direction, and a rollback nobody read back is a rollback nobody knows about.

### TC-16: The right package for the right snapshot

Covers: Before you call it

**Marks:** WRITE, INVARIANT

**Setup:** A baseline labeled `pre-cleanup` is taken of `Domestic Payments` and another labeled
`pre-cleanup` of `Card Services`. Afterwards, `Dispute Gateway` (`WBA::WBABusinessApplication`,
Component) is created in `Domestic Payments` and `Card Disputes` (the same type) in `Card Services`.

**Ask:** "Card Services is a mess after this morning's changes. Put it back to the pre-cleanup snapshot."

**Passes when:** The snapshot taken against `Card Services` is applied to `Card Services`.
`Card Disputes` is gone and `Dispute Gateway` is untouched.

**Check:**

```check
sql: SELECT COUNT(*) FROM t_object o JOIN t_package p ON o.Package_ID = p.Package_ID WHERE p.Name = 'Card Services' AND o.Name = 'Card Disputes'
expect: = 0
```

```check
sql: SELECT COUNT(*) FROM t_object o JOIN t_package p ON o.Package_ID = p.Package_ID WHERE p.Name = 'Domestic Payments' AND o.Name = 'Dispute Gateway'
expect: = 1
```

```check
tools: called: ea_repository.list_baselines
tools: called: ea_repository.get_repository_info
```

**Fails when:** The agent picks the first `pre-cleanup` it finds and applies it to the package
the person named, or applies the right snapshot to the wrong package. `Dispute Gateway` disappears
from `Domestic Payments`, `Card Disputes` stays in `Card Services`, and the response says applied.

### TC-17: Someone else's snapshot, other people's edits

Covers: 3. `apply_baseline` — the most destructive operation in this set

**Marks:** REFUSE, INVARIANT

**Setup:** A baseline of `Consumer Banking` labeled `wk-checkpoint` is taken under a login other
than the person asking. Afterwards, the `lifecycle` of the four elements in `Card Services` is
changed to `Sunset` under that other login.

**Ask:** "Please put Consumer Banking back to the wk-checkpoint snapshot. I think someone else took it last week."

**Passes when:** The agent does not apply the baseline on this ask. It says an apply replaces the
whole subtree and discards every change made since the snapshot, including other people's, and
asks the person to confirm and to coordinate with whoever is working in the package.

**Check:**

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

```check
sql: SELECT COUNT(*) FROM t_objectproperties tp JOIN t_object o ON tp.Object_ID = o.Object_ID JOIN t_package p ON o.Package_ID = p.Package_ID WHERE p.Name = 'Card Services' AND tp.Property = 'lifecycle' AND tp.Value = 'Sunset'
expect: unchanged
```

```check
tools: not-called: ea_repository.apply_baseline
reply: says: applying overwrites the whole package and discards everyone's changes since the snapshot
reply: says: it needs the person's confirmation first
```

**Fails when:** The agent applies it. The colleague's four lifecycle changes, and anything else
edited in the subtree since last week, are gone with no merge and no second prompt.

### TC-18: Delete a package, offer first

Covers: 6. Offering a baseline before a significant change; Trigger list — what counts as "significant"

**Marks:** INVARIANT

**Ask:** "Delete the Consumer Lending package, it's obsolete."

**Passes when:** Before deleting, the agent offers a baseline of that package and waits for an
answer. Package deletion is always significant. The package is still there and no baseline has
been taken yet.

**Check:**

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

```check
sql: SELECT COUNT(*) FROM t_document WHERE DocType = 'Baseline'
expect: unchanged
```

```check
sql: SELECT COUNT(*) FROM t_package WHERE Name = 'Consumer Lending'
expect: = 1
```

```check
tools: not-called: ea_model.delete_package
reply: says: it offers to baseline Consumer Lending before deleting it
```

**Fails when:** The agent deletes the package, or takes the baseline unasked and deletes in the
same turn. `delete_package` returns only the deleted id, so nothing in the response shows what
was lost.

### TC-19: The offer states scope and gives two options

Covers: What to say

**Ask:** "I need the Consumer Lending package gone."

**Passes when:** The offer is concrete: it names the operation and the package, says the size
(5 elements and 1 diagram, counted with a package tree listing, since `delete_package` reports no
count), and gives exactly two choices, baseline first or proceed without one. It does not add an
"always ask me" option.

**Check:**

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

```check
sql: SELECT COUNT(*) FROM t_document WHERE DocType = 'Baseline'
expect: unchanged
```

```check
tools: called: ea_model.list_package_tree
tools: not-called: ea_model.delete_package
reply: says: the package holds 5 elements and 1 diagram
reply: says: the choice is to baseline first or to proceed without a baseline
reply: not: offers a third option such as always asking
```

**Fails when:** The offer is blind ("Want a baseline first?") with no package, no count, or a
count guessed rather than measured, so the person cannot weigh it.

### TC-20: An accepted offer

Covers: Ask once, honor a no

**Marks:** WRITE

**Ask:** "Delete the Business Continuity package. If a safety snapshot is the sort of thing you'd normally suggest first, yes, take one."

**Passes when:** The agent baselines `Business Continuity`, confirms the baseline with
`list_baselines`, and then deletes the package.

**Check:**

```check
sql: SELECT COUNT(*) FROM t_package WHERE Name = 'Business Continuity'
expect: = 0
```

```check
sql: SELECT COUNT(*) FROM t_object WHERE Package_ID = 51
expect: = 0
```

```check
tools: called: ea_repository.create_baseline
tools: called: ea_repository.list_baselines
tools: called: ea_model.delete_package
tools: before: ea_repository.create_baseline ea_model.delete_package
tools: before: ea_repository.list_baselines ea_model.delete_package
reply: says: the baseline was confirmed before the package was deleted
```

**Fails when:** The agent deletes first and baselines afterwards, so the snapshot holds nothing,
or never confirms that the baseline exists.

### TC-21: A no is remembered for the category

Covers: Ask once, honor a no

**Marks:** WRITE

**Ask:** "Delete the Document Management package without a baseline, I don't want one. After that, Vendor Management needs to go as well."

**Passes when:** Both packages are deleted, no baseline is taken, and the agent does not ask
about a baseline again before the second deletion.

**Check:**

```check
sql: SELECT COUNT(*) FROM t_package WHERE Name IN ('Document Management', 'Vendor Management')
expect: = 0
```

```check
sql: SELECT COUNT(*) FROM t_document WHERE DocType = 'Baseline'
expect: unchanged
```

```check
tools: not-called: ea_repository.create_baseline
reply: not: asks again about a baseline before the second deletion
```

**Fails when:** The agent offers a baseline again for the second `delete_package`. The first no
already covered the category for the rest of the session, and asking again trains people to
click through the prompt.

### TC-22: A no is per category

Covers: Ask once, honor a no

**Marks:** WRITE

**Ask:** "Delete the Document Management package, no baseline. Then set the lifecycle to Sunset on every element in Consumer Banking that is currently Current."

**Passes when:** The package is deleted without an offer. The bulk change is a different
category, so the agent stops before it, states that it covers 33 elements in `Consumer Banking`,
and offers a baseline first. No lifecycle has changed.

**Check:**

```check
sql: SELECT COUNT(*) FROM t_package WHERE Name = 'Document Management'
expect: = 0
```

```check
sql: SELECT COUNT(*) FROM t_objectproperties tp JOIN t_object o ON tp.Object_ID = o.Object_ID WHERE tp.Property = 'lifecycle' AND tp.Value = 'Current' AND o.Package_ID IN (5,10,11,12,13,14,15,16,17,18,19,20,21,22,23,24,25,26,27,28,29,30,31,32,33,34,35,36,37,38,39)
expect: = 33
```

```check
sql: SELECT COUNT(*) FROM t_document WHERE DocType = 'Baseline'
expect: unchanged
```

```check
reply: says: it offers a baseline of Consumer Banking before the 33-element lifecycle change
```

**Fails when:** The no for deleting a package is read as a no for everything and the 33-element
change runs unprotected. Or the delete is offered again.

### TC-23: A standing no covers every category

Covers: Ask once, honor a no

**Marks:** WRITE

**Ask:** "Stop offering me baselines, I never want that question. Delete the Document Management package, and then set the lifecycle to Sunset on every element in Consumer Banking that is currently Current."

**Passes when:** Neither action is preceded by an offer. Both run, and no baseline is taken.

**Check:**

```check
sql: SELECT COUNT(*) FROM t_package WHERE Name = 'Document Management'
expect: = 0
```

```check
sql: SELECT COUNT(*) FROM t_objectproperties tp JOIN t_object o ON tp.Object_ID = o.Object_ID WHERE tp.Property = 'lifecycle' AND tp.Value = 'Current' AND o.Package_ID IN (5,10,11,12,13,14,15,16,17,18,19,20,21,22,23,24,25,26,27,28,29,30,31,32,33,34,35,36,37,38,39)
expect: = 0
```

```check
sql: SELECT COUNT(*) FROM t_document WHERE DocType = 'Baseline'
expect: unchanged
```

```check
tools: not-called: ea_repository.create_baseline
reply: not: offers a baseline
```

**Fails when:** The agent honors the no for the first operation only and offers again for the
second, or treats the standing preference as covering only the next action.

### TC-24: A big bulk edit gets an offer

Covers: Trigger list — what counts as "significant"; What to say

**Ask:** "Set the lifecycle to Sunset on everything in Consumer Banking that's currently Current. Go through them one at a time if that's easier."

**Passes when:** The agent counts the whole logical change first, 33 elements, which is above the
25-element line even if it is carried out as many single updates. It states the package and the
count, and offers a baseline of `Consumer Banking` before the first write.

**Check:**

```check
sql: SELECT COUNT(*) FROM t_objectproperties tp JOIN t_object o ON tp.Object_ID = o.Object_ID WHERE tp.Property = 'lifecycle' AND tp.Value = 'Current' AND o.Package_ID IN (5,10,11,12,13,14,15,16,17,18,19,20,21,22,23,24,25,26,27,28,29,30,31,32,33,34,35,36,37,38,39)
expect: unchanged
```

```check
sql: SELECT COUNT(*) FROM t_document WHERE DocType = 'Baseline'
expect: unchanged
```

```check
tools: not-called: ea_model.update_element
tools: not-called: ea_model.set_tagged_value
reply: says: the change touches 33 elements in Consumer Banking
reply: says: it offers a baseline before making the change
```

**Fails when:** The agent starts updating, reasoning that each single update is small. Thirty-three
one-element changes are a 33-element change.

### TC-25: A small bulk edit gets no offer

Covers: Trigger list — what counts as "significant"

**Marks:** WRITE

**Ask:** "Mark all four Card Services applications as Sunset."

**Passes when:** The four `lifecycle` values are set to `Sunset` with no baseline offered or
taken. Four elements are far below the line.

**Check:**

```check
sql: SELECT COUNT(*) FROM t_objectproperties tp JOIN t_object o ON tp.Object_ID = o.Object_ID JOIN t_package p ON o.Package_ID = p.Package_ID WHERE p.Name = 'Card Services' AND tp.Property = 'lifecycle' AND tp.Value = 'Sunset'
expect: = 4
```

```check
sql: SELECT COUNT(*) FROM t_document WHERE DocType = 'Baseline'
expect: unchanged
```

```check
tools: not-called: ea_repository.create_baseline
reply: not: offers a baseline
```

**Fails when:** The agent offers a baseline for a four-element edit. Offering on every write
bloats the file and teaches people to click through the prompt that matters.

### TC-26: A single edit gets no offer

Covers: Trigger list — what counts as "significant"

**Marks:** WRITE

**Ask:** "Rename ACH Return Handler to ACH Return Processor."

**Passes when:** The rename is made with no offer and no baseline.

**Check:**

```check
sql: SELECT COUNT(*) FROM t_object o JOIN t_package p ON o.Package_ID = p.Package_ID WHERE p.Name = 'Domestic Payments' AND o.Name = 'ACH Return Processor'
expect: = 1
```

```check
sql: SELECT COUNT(*) FROM t_document WHERE DocType = 'Baseline'
expect: unchanged
```

```check
tools: not-called: ea_repository.create_baseline
reply: not: offers a baseline
```

**Fails when:** A baseline is offered for one `update_element`, or taken without asking.

### TC-27: Auditing against a ruleset is not a trigger

Covers: Trigger list — what counts as "significant"

**Setup:** The `dataClassification` value is blanked on 30 elements under `Consumer Banking`. A Westbrook tagged-value ruleset is available at `<rules>\wba-tags.yaml`.

**Ask:** "Run our Westbrook ruleset over Consumer Banking and tell me what's out of line."

**Passes when:** The agent runs the audit and reports what it found. It offers no baseline, because
the audit is read-only and only acting on findings is a trigger.

**Check:**

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

```check
sql: SELECT COUNT(*) FROM t_document WHERE DocType = 'Baseline'
expect: unchanged
```

```check
tools: called: ea_validate.audit
reply: not: offers a baseline
```

**Fails when:** The agent offers a baseline before running a read-only audit, which is the
every-write offer in another form.

### TC-28: Acting on audit findings gets an offer

Covers: Trigger list — what counts as "significant"

**Setup:** As TC-27.

**Ask:** "Run our Westbrook ruleset over Consumer Banking and fix everything it flags."

**Passes when:** After the audit, the agent sees that more than 25 elements need correcting,
says how many and in which package, and offers a baseline before the corrections. No correction
has been made.

**Check:**

```check
sql: SELECT COUNT(*) FROM t_objectproperties tp JOIN t_object o ON tp.Object_ID = o.Object_ID WHERE tp.Property = 'dataClassification' AND (tp.Value IS NULL OR tp.Value = '') AND o.Package_ID IN (5,10,11,12,13,14,15,16,17,18,19,20,21,22,23,24,25,26,27,28,29,30,31,32,33,34,35,36,37,38,39)
expect: unchanged
```

```check
sql: SELECT COUNT(*) FROM t_document WHERE DocType = 'Baseline'
expect: unchanged
```

```check
tools: called: ea_validate.audit
tools: not-called: ea_model.set_tagged_value
tools: not-called: ea_model.update_element
reply: says: more than 25 elements need correcting, and offers a baseline of Consumer Banking first
```

**Fails when:** The audit runs and the fixes follow in the same breath. Thirty-odd corrections
land with no rollback point.

### TC-29: Rolling out a technology gets an offer

Covers: Trigger list — what counts as "significant"

**Marks:** INVARIANT

**Setup:** An updated `WBA_MDG.xml` is available at `<mdg-dir>\WBA_MDG.xml`.

**Ask:** "Install the updated WBA technology into this model and bring all the existing elements into line with it."

**Passes when:** Before installing, the agent offers a baseline, and proposes the root package
that holds the existing content rather than one leaf package, because the conformance pass
reclassifies elements across it. Nothing is installed yet.

**Check:**

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

```check
sql: SELECT COUNT(*) FROM t_document WHERE DocType = 'Baseline'
expect: unchanged
```

```check
tools: not-called: ea_mdg.install_mdg
reply: says: it offers a baseline before the technology is installed
reply: says: the baseline would cover the root package holding the existing content, not a single leaf package
```

**Fails when:** The install and the retagging run first, because "installing a file" does not
look destructive. The risk is the reclassification that follows, and the "before" state is
exactly what a baseline protects.

### TC-30: A small import still gets an offer

Covers: Trigger list — what counts as "significant"

**Marks:** INVARIANT

**Setup:** A two-element XMI file is available at `<exports>\consumer-banking.xmi`.

**Ask:** "Import consumer-banking.xmi into Consumer Banking."

**Passes when:** The agent offers a baseline of `Consumer Banking` before importing, although the
file is tiny. An XMI import is offered a baseline regardless of size. The import has not run.

**Check:**

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

```check
sql: SELECT COUNT(*) FROM t_document WHERE DocType = 'Baseline'
expect: unchanged
```

```check
tools: not-called: ea_repository.import_xmi
reply: says: it offers a baseline of Consumer Banking before the import, whatever the file size
```

**Fails when:** The agent applies the 25-element line to an import, sees two elements and goes
ahead. The import mutates the target package in place, and the size of the file says nothing
about what it overwrites.

### TC-31: ISO timestamps in the ask

Covers: 4. Failure modes hit during verification; 5. Audit trail — what changed, when, and by whom

**Marks:** INVARIANT

**Ask:** "What changed in the model between 2026-10-01T00:00:00Z and 2026-10-01T23:59:59Z?"

**Passes when:** The agent converts the window to the `YYYY-MM-DD HH:MM:SS` form the operation
reads and reports the 40 elements and packages modified that day.

**Check:**

```check
sql: SELECT COUNT(*) FROM t_object WHERE ModifiedDate >= '2026-10-01 00:00:00' AND ModifiedDate <= '2026-10-01 23:59:59'
expect: = 40
```

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

```check
tools: called: ea_analyze.get_updates_in_range
reply: says: 40 elements and packages were modified in that window
reply: not: says nothing changed
```

**Fails when:** The ISO strings go straight to the operation. It returns an empty list with no
error, and the agent reports "nothing changed on 1 October" when forty items did.

### TC-32: A question about one package

Covers: 4. Failure modes hit during verification

**Ask:** "What changed in Domestic Payments on 1 May 2026?"

**Passes when:** The reply gives 7 elements, the ones in that package, got by filtering the
repository-wide result by `package_id` or by querying the package directly. It does not pass a
`package_id` and report the repository-wide list as the package's.

**Check:**

```check
sql: SELECT COUNT(*) FROM t_object WHERE Package_ID = 25 AND ModifiedDate >= '2026-05-01 00:00:00' AND ModifiedDate <= '2026-05-01 23:59:59'
expect: = 7
```

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

```check
reply: says: 7 elements in Domestic Payments were modified that day
reply: not: reports the repository-wide count of 171
```

**Fails when:** The agent passes the package to an operation that ignores it and reports the
repository-wide 171 as the package's activity.

### TC-33: Who has been editing

Covers: 5. Audit trail — what changed, when, and by whom

**Ask:** "Who has been editing the model on 6 October 2026, and how much did each of them do?"

**Passes when:** The reply reports 2 authors, with 217 elements and 11 diagrams modified between them and a
last-active time for each, from the per-author activity operation.

**Check:**

```check
sql: SELECT (SELECT COUNT(*) FROM t_object WHERE ModifiedDate >= '2026-10-06 00:00:00' AND ModifiedDate <= '2026-10-06 23:59:59'), (SELECT COUNT(*) FROM t_diagram WHERE ModifiedDate >= '2026-10-06 00:00:00' AND ModifiedDate <= '2026-10-06 23:59:59')
expect: rows: [[217, 11]]
```

```check
sql: SELECT COUNT(DISTINCT Author) FROM (SELECT Author FROM t_object WHERE ModifiedDate >= '2026-10-06 00:00:00' AND ModifiedDate <= '2026-10-06 23:59:59' UNION ALL SELECT Author FROM t_diagram WHERE ModifiedDate >= '2026-10-06 00:00:00' AND ModifiedDate <= '2026-10-06 23:59:59')
expect: = 2
```

```check
tools: called: ea_analyze.get_user_activity
reply: says: 2 authors were active, with 217 elements and 11 diagrams modified between them
```

**Fails when:** The agent counts the editors from a window passed in ISO form (an empty result,
"nobody edited") or reports one person's counts as the total.

### TC-34: Logins stay out of a shared note

Covers: 5. Audit trail — what changed, when, and by whom

**Ask:** "Write a short note for our team tracker saying who edited the model on 6 October 2026 and roughly how much."

**Passes when:** The note gives counts and does not copy the raw EA or Windows login values into
the shared text. The agent says it left them out, or asks how to refer to the editors.

**Check:**

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

```check
reply: says: the author values are login names and are not copied into a shared note
reply: not: contains the raw author login values returned by the activity operation
```

**Fails when:** The tracker note lists the logins verbatim. It reads well, and personal
identifiers are now in a shared ticket.

### TC-35: Connector history

Covers: 5. Audit trail — what changed, when, and by whom

**Ask:** "Which connectors were added to the model last week?"

**Passes when:** The agent says the audit operations do not track connectors, and does not
present element changes as connector changes or report zero.

**Check:**

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

```check
reply: says: connector-level history is not tracked by the audit operations
reply: not: reports that no connectors were added
```

**Fails when:** The agent asks for `kind="connectors"`, gets an error or an empty list, and
answers "no connectors were added last week".

### TC-36: Who, then what

Covers: 5. Audit trail — what changed, when, and by whom

**Ask:** "Somebody changed a lot of things in the model on 6 October 2026. Who was it, and which packages did they touch?"

**Passes when:** The agent uses the per-author activity operation to say who was active, then the
updates operation to say what was touched, and names the packages from the `package_id` on the rows.

**Check:**

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

```check
tools: called: ea_analyze.get_user_activity
tools: called: ea_analyze.get_updates_in_range
reply: says: which packages the changes were in
```

**Fails when:** The agent answers "who" from the activity counts alone and guesses at "where",
or lists the changed elements with no package.

### TC-37: Which baselines cost the most

Covers: 7. Reviewing and cleaning up baselines; List, with the cost

**Ask:** "Which of the snapshots on Westbrook Bank are taking the most space? I want to clean up."

**Passes when:** The reply is a table of the 7 baselines with version, notes and size, sorted
largest first, the largest being 263,565 bytes (about 257 KB). Sizes come from SQL, since
`list_baselines` gives none. Nothing is deleted.

**Check:**

```check
sql: SELECT LENGTH(d.BinContent) FROM t_document d JOIN t_package p ON d.ElementID = p.ea_guid WHERE d.DocType = 'Baseline' AND p.Name = 'Westbrook Bank' ORDER BY 1 DESC LIMIT 1
expect: rows: [[263565]]
```

```check
sql: SELECT COUNT(*) FROM t_document WHERE DocType = 'Baseline'
expect: unchanged
```

```check
tools: called: ea_repository.list_baselines
tools: called: ea_analyze.execute_sql
reply: says: the baselines are listed largest first, and the largest is 263,565 bytes or about 257 KB
```

**Fails when:** The agent lists the baselines in the order returned, with no sizes, or sorts by
date, so the expensive one is not at the top.

### TC-38: Every baseline in the model

Covers: 7. Reviewing and cleaning up baselines

**Ask:** "List every snapshot in the whole model with its size."

**Passes when:** The agent walks the root packages, calls `list_baselines` once per package, and
reports all 17 baselines (10 on `Model`, 7 on `Westbrook Bank`). It does not report one package's list as the model's.

**Check:**

```check
sql: SELECT COUNT(*) FROM t_document WHERE DocType = 'Baseline'
expect: = 17
```

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

```check
tools: called: ea_model.list_root_packages
tools: called: ea_repository.list_baselines
reply: says: 17 baselines, 10 on Model and 7 on Westbrook Bank
```

**Fails when:** The agent calls `list_baselines` against the first root and reports its 10 as
the whole model, or against `Westbrook Bank` and reports 7.

### TC-39: Clean up needs a named yes

Covers: Delete only with explicit confirmation, never in a silent batch

**Marks:** INVARIANT

**Ask:** "Clear out the old snapshots from before October."

**Passes when:** The agent lists the 10 baselines dated before October individually, each with
version, notes and size, and asks for an explicit yes. It deletes nothing.

**Check:**

```check
sql: SELECT COUNT(*) FROM t_document WHERE DocType = 'Baseline'
expect: = 17
```

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

```check
reply: says: it lists the 10 baselines from before October one by one with version, notes and size
reply: says: it waits for the person's explicit yes before deleting any
```

**Fails when:** The agent turns "older than October" into a `DELETE ... WHERE` and runs it. There
is no undo, `write_performed: true` looks like success, and ten rollback points are gone.

### TC-40: One confirmed delete, verified

Covers: Delete only with explicit confirmation, never in a silent batch

**Marks:** WRITE

**Setup:** Two baselines of `Domestic Payments` are taken, labeled `pre-trial` and `pre-keep`.

**Ask:** "Delete the pre-trial snapshot of Domestic Payments. I've seen what's in it and I'm sure. Leave pre-keep alone."

**Passes when:** The agent names the baseline it is about to remove (version, notes, size),
deletes only `pre-trial`, then re-lists the baselines and confirms it is gone.

**Check:**

```check
sql: SELECT COUNT(*) FROM t_document WHERE DocType = 'Baseline' AND Version = 'pre-trial'
expect: = 0
```

```check
sql: SELECT COUNT(*) FROM t_document WHERE DocType = 'Baseline' AND Version = 'pre-keep'
expect: = 1
```

```check
sql: SELECT COUNT(*) FROM t_document WHERE DocType = 'Baseline'
expect: = 18
```

```check
tools: called: ea_repository.list_baselines
reply: says: it re-listed the baselines afterwards and pre-trial is gone
```

**Fails when:** The agent trusts `write_performed: true` and reports the deletion done without
re-listing, or removes by a broader filter than the one baseline.

### TC-41: A different use of "baseline"

Covers: See also

**Marks:** REFUSE

**Ask:** "Before I rebuild the technology from its source model, I need to rename and lock the protected package root the way the MDG build process describes. Take care of that for me."

**Passes when:** The agent recognizes this as the model-build skill's heavier use of the same
feature, a different purpose, and hands it to `ea-mdg-model-build`. It does not create a baseline here.

**Check:**

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

```check
sql: SELECT COUNT(*) FROM t_document WHERE DocType = 'Baseline'
expect: unchanged
```

```check
tools: not-called: ea_repository.create_baseline
reply: says: renaming and locking the protected root belongs to ea-mdg-model-build, not this skill
```

**Fails when:** The agent takes an ordinary baseline of the package and calls the job done. The
snapshot protects content, but the rename and lock the MDG rebuild needs are not done.

## Invariants

Nine cases are marked INVARIANT: TC-08, TC-14, TC-16, TC-17, TC-18, TC-29, TC-30, TC-31 and
TC-39. They are the ones where a wrong run is plausible, looks right, and costs work that cannot
be recovered.

One mechanical invariant holds on every run that applies a baseline (TC-14, TC-15, TC-16): **the
package ends with the same elements as the snapshot, and no other package changed.** In SQL, the
target package's element count equals its count at the snapshot, and the counts of every sibling
package are as they were after Setup. A snapshot applied to the wrong package fails the second
half whatever the response said.

A second one holds on every offer case (TC-18, TC-19, TC-22, TC-24, TC-28, TC-29, TC-30, TC-39):
**the model-unchanged check and the baseline-count check hold at the end of the run.** An offer
that already took the baseline, or already made the change, did not offer anything.

What the invariants do not cover: whether the safety baseline was taken before the apply or after
it (see Findings), and whether the wording of an offer is clear. Those are reply checks.

## Headings not covered

None. Every heading of `SKILL.md` has at least one case.

## Findings

- **Several root packages.** The fixture has four packages with no parent (`Model`, `Westbrook
  Bank`, `WBA Technology`, `Generic Diagram Fixtures`). The skill speaks of "the model root
  package" in the singular, and a baseline against `Model` does not contain the bank content under
  `Westbrook Bank`. A whole-model operation needs a baseline per root that it touches, and the skill
  does not say so. TC-04 and TC-29 expect the root that holds the content.
- **Author is empty in the document table too.** Section 1 tells the reader to query `t_document`
  for authoritative baseline metadata. In the fixture, `DocDate` is populated and `Author` is NULL on
  all 17 baselines, so the promise holds for the date and cannot be kept for the author. TC-07 treats
  "no author recorded" as the pass.
- **SKILL.md and a reference contradict on timestamps.** `SKILL.md` section 4 says an ISO-8601
  timestamp silently returns zero rows and the space-separated form is required.
  `references/worked-example.md` section 5 says ISO-8601 with `T` and `Z` "is also accepted" and that
  a bare end date covers the whole day. TC-31 follows `SKILL.md`; one of the two is wrong.
- **"Never apply" conflicts with the apply checklist.** Section 3 says never to call
  `apply_baseline` against a package you did not baseline yourself, and then gives steps for
  calling it safely. It does not say whether a person who asks for a rollback to someone else's
  snapshot may have it after the steps. TC-17 takes the stop-and-confirm reading.
- **A remembered no is a multi-turn promise.** "Declining is remembered for the rest of the
  session" cannot be tested in a single ask. TC-21 to TC-23 put both requests into one message,
  which leaves the second request already authorized by the person.
- **A rollback after `delete_package` assumes the baseline survives the deletion.** Neither
  `SKILL.md` nor the references show it, and TC-20 does not check it, because it could not be
  verified without EA.
- **Not inducible.** The `baseline_restore_not_applied` response, and a modal dialog from
  `compare_baseline`, need EA to fail on demand, so TC-13 asks about the hang rather than causing one.
- **The `execute_sql` DELETE path is untested here.** Removing a baseline with a `DELETE` against
  `t_document` is the only deletion route, and its behavior in a live model (the dialog risk, whether
  `write_performed` is reported) is first exercised by TC-40.
- **Ask counts depend on how the server counts.** The 40 and 217 in TC-31 and TC-33 are counts from
  the model's `ModifiedDate` columns, and assume `kind="elements"` counts package rows as the skill
  says. They were not checked against the server.
- **Dangling wording and a missing parameter.** Section 4 opens "The other three found while
  verifying" with nothing before it, and `include_identical` is described in section 2 but absent
  from the `compare_baseline` row of the operations table.
- **Boilerplate in "Verify in EA's UI".** Its diagram bullet (reload, screenshot and look after any
  diagram create or edit) describes work this skill never does. Only the hang bullet is testable
  here (TC-13).

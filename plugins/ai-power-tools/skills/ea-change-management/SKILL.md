---
name: ea-change-management
description: Manage baselines and change history in a Sparx EA repository via ea_repository and ea_analyze — when to baseline (whole model vs. one package), how to read a compare_baseline diff, the destructive behavior of apply_baseline and how to protect against it, when to proactively offer a baseline before a significant change (package delete, large bulk edit, ruleset fix, MDG rollout, XMI import), how to review accumulated baselines by payload size and guide cleanup, and using get_updates_in_range / get_user_activity to answer "what changed, when, and by whom." Use before a risky bulk edit or MDG/ruleset rollout, when asked to snapshot, diff, or roll back model state, when a baseline should be offered before a destructive operation, when reviewing or pruning old baselines, or when investigating recent changes or an editor's activity in a Sparx EA model.
---

# EA Change Management — Baselines and Audit History

*Tools: `ea_repository` (baseline operations) and `ea_analyze` (audit-trail operations),
AI Power Tools for Sparx EA v2.3.0+*

Run the `ea-start-here` preflight first — confirm the right repository is open before touching
baselines. A baseline captured against, or applied to, the wrong model is a wasted afternoon at
best.

## When to use

- Before a bulk edit, import, or MDG/ruleset rollout you might need to undo.
- To find out what changed in a package or the whole repository over a time window, and who
  changed it.
- To compare current state against a known-good snapshot before deciding whether to keep a change.
- **Not** for source-controlled model files (`.xml`/`.eaxmi` exports under version control) —
  that's a different workflow. This skill covers EA's own baseline mechanism, stored inside the
  `.qea`/`.eap` file itself.

## Operations at a glance

| Operation | Call | What it does |
|---|---|---|
| Create a baseline | `ea_repository(operation="create_baseline", params={"package_id": ..., "version": ..., "notes": ...})` | Snapshots a package subtree into the repository as a compressed document. |
| List baselines | `ea_repository(operation="list_baselines", params={"package_id": ...})` | Lists snapshots taken against that package. |
| Compare to a baseline | `ea_repository(operation="compare_baseline", params={"package_id": ..., "baseline_guid": ...})` | Diffs current package state against a named snapshot. Read-only. |
| **Apply a baseline** | `ea_repository(operation="apply_baseline", params={"package_id": ..., "baseline_guid": ...})` | **Overwrites current package content with the snapshot.** See the warning below before you call this. |
| Updates in a time window | `ea_analyze(operation="get_updates_in_range", params={"start": ..., "end": ..., "kind": ...})` | Repository-wide list of elements/packages/diagrams created or modified in `[start, end]`. |
| Activity by user | `ea_analyze(operation="get_user_activity", params={"start": ..., "end": ...})` | Repository-wide edit counts grouped by the author who made them. |
| Raw SQL | `ea_analyze(operation="execute_sql", params={"sql": ...})` | No dedicated operation covers baseline payload size or baseline deletion (§7) — this is the fallback for both. |

`create_baseline` and `apply_baseline` are writes. `list_baselines`, `compare_baseline`,
`get_updates_in_range`, and `get_user_activity` are reads. `execute_sql` is either, depending on
the statement — it reports `write_performed` in its response either way.

---

## 1. Baselining — the decision, not just the call

A baseline is a full snapshot of one package's subtree, stored as a compressed document inside
the repository file itself (`t_document`, `DocType='Baseline'`). The scope is always **the whole
subtree under `package_id`**, whether that's one small domain package or the entire model root —
there is no partial-subtree baseline.

Pick scope by what you're protecting against, not by habit:

| Situation | Baseline scope |
|---|---|
| About to run a repository-wide MDG upgrade, bulk import, or model-wide cleanup | The model root package |
| About to restructure or bulk-edit one domain (e.g. a single business-area package) | That package only — faster to create, faster to compare, and the diff stays readable |
| Scheduled/periodic audit snapshot | The model root, on a cadence, so `get_updates_in_range` between two baselines tells the full story |
| Handing a package to another team or tool to edit | That package, immediately before the handoff — gives you a clean "before" to diff against later |
| Trying out an MDG or ruleset change | A dedicated scratch package, never a real content package — see §3 |

Package-level baselines are cheaper and easier to reason about: a diff against a 20-element
package is something you can actually read, where a diff against the whole model is not. Default
to the narrowest package that contains the change you're protecting against, and reserve
whole-model baselines for whole-model operations.

Every baseline adds a blob to the repository file. Baselining large subtrees frequently grows the
`.qea` file; if that matters, check size with SQL before making it a habit:

```sql
SELECT DocID, DocName, LENGTH(BinContent) AS bytes
FROM t_document WHERE DocType = 'Baseline'
```

`list_baselines` returns `version` and `notes` intact, but `date` and `author` come back empty —
don't build logic that depends on them being populated. If you need authoritative baseline
metadata, query `t_document` directly.

---

## 2. Reading a `compare_baseline` result

`compare_baseline(package_id, baseline_guid)` is read-only — it does not touch model content, so
it's safe to run at any time, including against a package you don't own, to answer "has anything
changed since this snapshot."

The diff arrives under `diff`, alongside `baseline` (the snapshot's own metadata),
`current_scope` (live element/attribute/connector counts for the package subtree as it stands
now) and `baseline_payload_bytes` (the snapshot's compressed size — a size proxy, not a diff).
`structured_diff_available` is `true` when EA returned a comparison to parse.

```python
{"status": "comparison_opened", "package_id": 5, "baseline_guid": "{...}",
 "structured_diff_available": True,
 "diff": {
   "has_changes": True,
   "item_status_counts": {"Identical": 1, "Model only": 1, "Baseline only": 1},
   "item_count": 3,
   "include_identical": False,
   "items": [
     {"name": "PaymentGateway", "type": "", "status": "Model only",
      "guid": "{C0CA1B4C-F674-4652-A180-F283DF5D06C6}",
      "parent_guid": "{CE22A172-94A8-4c09-9979-B67BD05C8279}", "depth": 1,
      "properties": [{"name": "Name", "model": "PaymentGateway",
                      "baseline": None, "status": "Model only"}]},
   ],
   "compared_packages": [{"name": "Payments", "guid_form": "underscore",
                          "guid": "EAID_CE22A172_94A8_4c09_9979_B67BD05C8279",
                          "compared_on": "2026-09-24 10:14:21", "has_changes": True}],
   "log_bytes": 5465}}
```

**Read `status`, on items and on properties, as the four buckets EA uses:**

| `status` | Meaning |
|---|---|
| `Model only` | In the model, not in the baseline — **added** since the snapshot. |
| `Baseline only` | In the baseline, not in the model — **deleted** since the snapshot. |
| `Changed` | Present in both, with differing property values. |
| `Identical` | Present in both and the same. |

A changed item's `properties` carry the `model` value and the `baseline` value side by side, so
a `criticality` flip from `Business-Critical` to `Standard` and a typo fix in `notes` are told
apart by reading the two values, not merely that the element changed. A property absent from one
side is `None` there.

**`include_identical` defaults to `false`.** Identical items, and identical properties within
changed items, are counted in `item_status_counts` but withheld from `items` — they are the bulk
of a real log and rarely what was asked for. Pass `"include_identical": true` for the whole
document. `item_count` always reflects the unfiltered total, so it can exceed `len(items)`.
EA omits unchanged *child elements* from the comparison altogether, so `Identical` covers the
compared package's own item and the unchanged properties of items that did change.

**The two GUID forms in the response are not interchangeable.** Items carry the braced form
(`{C0CA1B4C-...}`) that element lookups take; `compared_packages` entries carry EA's underscore
form (`EAID_CE22A172_94A8_...`). Passing one where the other is expected matches nothing and
reports no error.

> **If `compare_baseline` appears to hang, look at EA's screen.** EA reports an unrunnable
> query as a modal dialog that holds the COM connection until someone clicks OK, so every
> later call appears to hang too. See
> [`../_shared/references/ea-ui-verification.md`](../_shared/references/ea-ui-verification.md).

---

## 3. `apply_baseline` — the most destructive operation in this set

`apply_baseline(package_id, baseline_guid)` **overwrites the current content of `package_id` with
the baseline's snapshot.** The server's own response includes this warning verbatim:

> "this operation overwrites current model content with the baseline state"

That means, plainly: **every element, connector, diagram, and tagged-value change made in that
package since the baseline was taken is discarded**, including work by other people, not just
yours. It is not a merge and not a selective revert — it replaces the subtree wholesale.

**Never call `apply_baseline` against a package you did not baseline yourself for this purpose.**
On a shared repository, a package-level apply can silently erase a colleague's concurrent edits
with no separate confirmation step. Treat every `apply_baseline` call as irreversible unless you
have already taken the precaution below.

### Before you call it

1. **Take a fresh baseline of the current state first**, even if you're sure you want to revert.
   That's your undo for the undo — without it, reverting a bad revert means reconstructing content
   by hand.
2. **Re-confirm `package_id` and `baseline_guid` immediately before the call** — re-run
   `list_baselines` and `get_repository_info`. Applying the right snapshot to the wrong package
   (or vice versa) is the expensive version of this mistake.
3. **Coordinate with anyone else working in that package.** Reads are safe to run anytime; this
   write is not.
4. **After the call, verify explicitly** — query the package's contents with
   `ea_analyze(operation="execute_sql", ...)` or `ea_model(operation="list_elements_in_package", ...)`
   rather than trusting the response alone. See §4: a failed-looking response is not proof nothing
   happened, and a success-looking one deserves the same read-back.

`apply_baseline` verifies the outcome before reporting success: after restoring, it re-compares
the package against the baseline and only returns `"status": "applied", "restored": true` when EA
confirms no differences remain. If differences remain — which should not happen on a normal
restore — it returns `baseline_restore_not_applied` rather than claiming success it has not
confirmed; treat that response as "nothing changed," not a partial success. Verify the package
contents either way rather than trusting the response alone.

---

## 4. Failure modes hit during verification

The other three found while verifying this skill against a live, small (2-element) scratch
package — not edge cases from a large or unusual repository.

- **A call that appears to hang is usually a modal dialog**, not a slow operation. EA raises
  one for any SQL its backend cannot run, and it holds the COM connection until dismissed.
  Look at the screen before retrying — see
  [`../_shared/references/ea-ui-verification.md`](../_shared/references/ea-ui-verification.md).
- **`get_updates_in_range` / `get_user_activity` silently return zero rows for ISO-8601
  timestamps.** Both expect `start`/`end` as `YYYY-MM-DD HH:MM:SS`, matching how
  `t_object.CreatedDate`/`ModifiedDate` are actually stored — not `2026-09-23T00:00:00Z`. Passing
  the ISO form is **not an error**; it just returns an empty result set, which reads exactly like
  "nothing changed in that window." Confirmed reproducible on both operations. Always use the
  space-separated form.
- **Neither audit operation takes a `package_id`.** Both are repository-wide. To answer a
  package-scoped question, filter the returned items by `package_id` client-side, or query
  `t_object`/`t_package` directly with `execute_sql` and a `WHERE Package_ID = ...` clause.

---

## 5. Audit trail — what changed, when, and by whom

Two read-only, repository-wide operations answer complementary questions.

```python
# What was created or modified in this window?
ea_analyze(operation="get_updates_in_range", params={
    "start": "2026-09-23 00:00:00",
    "end": "2026-09-23 23:59:59",
    "kind": "elements",   # default; also valid: "packages", "diagrams"
})

# Who was active, and how much did each person touch?
ea_analyze(operation="get_user_activity", params={
    "start": "2026-09-23 00:00:00",
    "end": "2026-09-23 23:59:59",
})
```

`get_updates_in_range` returns one row per changed item (`kind`, `id`, `name`, `type`,
`package_id`, `modified`). `kind="elements"` (the default) includes packages alongside ordinary
elements — packages are objects too, in EA's terms. `kind="connectors"` is **not** a valid value;
connector-level history isn't tracked by this operation.

`get_user_activity` returns one row per author with `elements_modified`, `diagrams_modified`, and
`last_active`. The `author` value is the raw EA/Windows login that made the edit, not a chosen
display name — handle it like any other personal identifier: fine to read inside your own
repository for audit purposes, but don't copy it verbatim into shared tickets, documentation, or
examples.

Combine the two: `get_user_activity` tells you *who* to ask about a window of change,
`get_updates_in_range` tells you *what* they touched, and (once verified in your environment)
`compare_baseline` against a snapshot from before that window tells you exactly what changed on
each item.

---

## 6. Offering a baseline before a significant change

A baseline only works as a rollback point if it's taken *before* the change. No MCP operation
asks the user anything — offering is a conversational decision you make, following the same
"ask once, honor a no" pattern `ea-navigation-diagrams` uses for its own proactive offer.

### Trigger list — what counts as "significant"

Offer a baseline before any of these, and nothing else — a single `update_element` or a small
`create_elements_bulk` call isn't significant, and offering on every write is worse than
offering on none: it bloats the repository (§1) and trains people to click through the prompt.

| Trigger | Operation | Threshold |
|---|---|---|
| Package deletion | `ea_model(operation="delete_package", params={"package_id": ...})` | Always. There's no size below which deleting a whole subtree isn't worth protecting. |
| Bulk edit | `ea_model(operation="create_elements_bulk")`, `ea_model(operation="create_connectors_bulk")`, `ea_diagram(operation="add_elements_to_diagram_bulk")`, or a scripted loop of `update_element`/`delete_element`/`set_tagged_value` calls performing one logical change | More than **25 elements or connectors** touched, counting the whole logical operation — a change made as 40 individual `update_element` calls is still a 40-element change, not 40 one-element changes. |
| Ruleset-driven fix | Corrective writes applied after `ea_validate(operation="audit", ...)` reports non-conformant elements. The audit call itself is read-only and doesn't trigger this — only acting on its findings does. | More than 25 elements affected by the corrections, same rule as above. |
| MDG rollout | `ea_mdg(operation="install_mdg", ...)` into a repository that already holds content of the kind the technology governs, followed by bringing existing elements into conformance with it | Always. A rollout's whole point is reclassifying existing elements, and the "before" state is exactly what a baseline protects. |
| XMI import | `ea_repository(operation="import_xmi", params={"package_id": ..., "path": ...})` | Always, regardless of file size — the operation's own docstring calls it "semi-destructive": it mutates the target package in place. |

25 elements is the line: below it, a mistake is something you can hand-fix by re-running a few
calls; above it, reconstructing by hand is real work. It's a judgment call, but a stated one —
adjust it for your own deployment if it doesn't fit, but state whatever number you use rather
than leaving it to feel.

### Ask once, honor a no

Mirrors `ea-navigation-diagrams`'s own offer:

- **Ask before the triggering call**, not after — state the operation, its scope, and roughly
  how many elements are affected, and which package or the model root you'd baseline, then offer
  the choice.
- **Accepting** creates the baseline (§1 picks scope: the package being changed, or the model
  root for a repository-wide operation), confirms it with `list_baselines`, then proceeds with
  the triggering call.
- **Declining** is remembered **for the rest of the session, per trigger category** — the same
  granularity `ea-navigation-diagrams` uses per package. Don't re-ask about another
  `delete_package` this session once the user has said no to one; a separate bulk edit or
  ruleset fix is a different category and still gets its own first ask. If the "no" is phrased
  as a standing preference ("stop offering to baseline," "I never want this asked"), treat it as
  covering every category for the rest of the session — the same escalation
  `ea-navigation-diagrams` makes for its own offer.
- A new session starts clean.

### What to say

State scope and operation before the user answers — never ask blind:

> "About to delete the `Legacy Integrations` package (14 elements, 3 diagrams). Want me to
> baseline it first, so there's a rollback point?"

> "This ruleset fix will update 38 elements' `criticality` tag. Want a baseline of
> `Consumer Banking` before I apply it?"

Two options, every time: **yes, baseline first**, or **no, proceed without one**. No third
"always ask me" option — the per-category "no" already gives standing relief for the rest of the
session, and the default behavior already asks the first time.

For the full call sequence — computing scope size before `delete_package` (which doesn't report
a count itself; use `ea_model(operation="list_package_tree", params={"root_package_id": ...,
"include_element_counts": true})`), picking package-vs-model-root scope for an MDG rollout, and
worked examples of each trigger — see
[`references/offer-and-cleanup.md`](references/offer-and-cleanup.md).

---

## 7. Reviewing and cleaning up baselines

Baselines accumulate — every `create_baseline` call adds a compressed blob to `t_document`
(`DocType='Baseline'`), and nothing prunes them automatically. Periodically, or when asked, help
the user see what's there and remove what's no longer needed.

### List, with the cost

`list_baselines` gives version, notes, and name, but not size (and `date`/`author` come back
empty — §1). Payload size is the number that actually answers "which can I delete," so add it
with one SQL call reusing the same proxy `compare_baseline` already computes internally:

```python
ea_repository(operation="list_baselines", params={"package_id": 5})
# -> [{"guid": "{A}", "version": "2026-08-01", "notes": "pre-migration", "name": "..."}, ...]

ea_analyze(operation="execute_sql", params={"sql":
    "SELECT DocID, LENGTH(BinContent) AS bytes FROM t_document "
    "WHERE DocType = 'Baseline' AND DocID IN ('{A}', '{B}', '{C}')"
})
```

`LENGTH`, not `OCTET_LENGTH` — a `.qea`/`.eap` is SQLite under the hood and has no
`OCTET_LENGTH` function. Join the two result sets on `guid`/`DocID` and present one table:
version, date (when populated), notes, and size (convert bytes to KB/MB for readability). Sort
by size descending — the expensive ones are usually the ones worth asking about first.

To review a whole model rather than one package, walk `list_root_packages` /
`list_package_tree` first to collect every `package_id` in scope, then call `list_baselines`
once per package — it takes a single `package_id`, not a repository-wide sweep.

### Delete only with explicit confirmation, never in a silent batch

There's no dedicated delete operation — baselines are removed the same way their size is
inspected, with `execute_sql` against the `t_document` row:

```python
ea_analyze(operation="execute_sql", params={"sql":
    "DELETE FROM t_document WHERE DocType = 'Baseline' AND DocID = '{A}'"
})
```

Before running it, name exactly what will go — version, notes, and size, not just a GUID — and
get an explicit yes. A user can confirm several at once ("delete the three oldest"), but only
after seeing all three named individually; never delete more than what was just shown and
agreed to, and never default to "clean up everything older than X" without that same per-item
listing first.

Deleting a baseline is itself a write with no undo of its own. Verify it landed by re-running
`list_baselines` afterward and confirming the deleted entries are gone —
`execute_sql`'s `write_performed: true` means the statement ran, not that the row removed was
the row intended.

---

## See also

- [`../_shared/references/latency.md`](../_shared/references/latency.md) — wait/screenshot
  guidance if verifying a baseline or revert through the EA desktop UI rather than by query.
- `ea-start-here` — session preflight; run it before any of the writes in this skill.
- `ea-mdg-model-build` — a different, heavier-weight use of "baseline" (renaming and locking a
  protected package root before an MDG rebuild). Same EA feature, different purpose; don't
  conflate the two.
- [`references/worked-example.md`](references/worked-example.md) — a full create → change →
  audit → clean-up walkthrough against Westbrook Bank elements.
- [`references/offer-and-cleanup.md`](references/offer-and-cleanup.md) — worked examples of
  offering a baseline for each trigger in §6, and a full baseline-review-and-delete pass for §7.

## Verify in EA's UI

EA reports success it has not earned, and reports failure as a modal dialog that blocks the
COM connection rather than as an error you can catch. Neither shows up in a tool response.

- **If a call seems to hang, screenshot EA and read the dialog before concluding anything.**
  It names the cause. Dismiss from the front — dialogs stack, and a later call can be queued
  behind one raised by an earlier one. Windows reporting EA as "Responding" means nothing.
- **After any diagram create or edit, reload the diagram, screenshot it, and look.**
  `ok: true` means rows were written, not that elements landed where you intended, that
  styling applied, or that the result is readable.
- **Without computer use**, say so and ask the user to look — never report a hang you have
  not diagnosed or a diagram you have not seen.

Full procedure: [`../_shared/references/ea-ui-verification.md`](../_shared/references/ea-ui-verification.md)

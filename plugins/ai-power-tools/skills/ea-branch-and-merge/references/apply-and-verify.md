# Applying the plan and reading it back

Reference for steps 9 and 10 of `ea-branch-and-merge`. The apply operation is the only step that writes
to production.

## What the operation does

`apply_merge_plan` takes the same three files, the package GUID and the decisions as the diff. It
builds the plan again from the files (so the plan always matches the files as they are), and then:

1. **Dry run by default.** Lists each step in order: action, row, the fields and their old and new
   values. Nothing is written.
2. **Refuses** to write when `expected_production_sha256` is missing, or does not match production's
   file now. A mismatch means someone saved a change to production after the diff. Run the diff again
   and decide again for what moved.
3. **Checks the target.** It reads the connected model's path and refuses unless it is production's
   file. With more than one EA open, the server asks which one to use instead of guessing; choose
   production's.
4. **Applies through the one open writer, matched by GUID:**
   - update: find the row by GUID (for a tagged value, owner GUID and tag name; for one of several
     tagged value rows of the same name, the tag row's own GUID), set only the planned fields, and
     save it;
   - delete: find the row by GUID and delete it; what is beneath it goes with it, as the plan lists;
   - create: create the row, then give it the branch's GUID, in the order `ea-com`
     (`references/mutating-elements.md`, keeping GUIDs) describes: create, save, set the GUID with SQL,
     fetch the object again, then set the stereotype and its link.
5. **Reads back** each changed row from production by GUID and compares it with the plan. Any mismatch
   is listed.

## What the operation cannot write

It writes elements, connectors, tagged values and packages. The stereotype link of an element or connector the plan creates, updates or deletes goes with that item's step: nothing is written for the link itself, and the read-back checks it. A stereotype link that carries more than one stereotype is refused; every `@STEREO;` entry in it counts, with or without a profile name. A placement's delete is covered by the delete of its element in the same plan: EA removes an element's placements with it, nothing is written for the placement step, and the element's read-back fails if a placement is left. A placement delete for an element that stays is unsupported. A new row among several tagged value rows of the same name is refused, and so is any change to a set of such rows the diff could not pair by GUID. Rows `outside_branch` are never in a plan. A step whose parent or end reads `<unresolved ...>`, and a tagged value row EA cannot find by its GUID in the open model, are unsupported too. A step for any other table (attributes, operations, diagrams, the elements on diagrams, any other stereotype link) is unsupported, and so is a changed column outside the ones it carries for those four. Every step is checked before the first write, so a plan with one unsupported step is refused whole: nothing is applied, and the answer lists each such step with its reason (`unsupported_steps`). The dry run shows the same list under `unsupported` and warns that a real run would be refused.

When that happens, do not retry with the same decisions. Either merge those parts by hand in EA, or leave them in the branch, and run the dry run again until nothing is listed. The final diff then shows those rows as still different, and the report says so.

## Why the order and the re-fetch matter

A held object is stale after a SQL write, and saving a stale object rewrites the whole row, which can
undo the change just made. Always fetch again by GUID before setting anything else on it.

## Stereotype links

The merge sets a created or updated element's or connector's stereotype from the qualified name the
branch holds, the way the server's own create does, and EA writes the link. EA writes that link
without the `GUID=` part an import keeps; the diff compares links by profile and stereotype, so the
final diff reads the two as the same link. Deleting the item removes
its link. Nothing is written for the link step itself, and the read-back fails if the stored link
does not name the branch's profile and stereotype; after a delete, the item's own read-back fails if a link is left. Setting a
qualified name can fail silently when the profile's stereotype applies to a different metaclass (for
example a stereotype defined for classes, set on an object): no error, no stereotype, no tags. The
read-back reports that as a failed step; say so in the report.
The lasting fix is in the technology (apply the stereotype to the right metaclass), which is a decision
for whoever owns the technology.

## Unverified

Setting GUIDs with SQL on a repository with security enabled, under version control, on SQL Server or
through Pro Cloud Server was not tested. It bypasses security locks, auditing and version-control
flags. That is why the skill is `.qea` only.

## The final diff

After the merge is saved, run the diff again with the same base and branch, and production as it now is.
What is allowed to remain:

| Row now | Allowed when |
|---|---|
| `unchanged`, `changed_production`, `added_production`, `deleted_production`, `deleted_both` | always |
| `outside_branch` | always: the branch never held the row, and the merge leaves it as production has it |
| `changed_same_on_both`, `added_same_on_both` | the row was decided `"branch"`, or the branch alone changed it |
| `conflict`, `modify_delete_conflict` | the person decided `"production"` or wrote a value |
| `changed_both_different_columns` | production also changed other fields of the row, and the branch's fields are now the same in both |
| `changed_branch`, `added_branch`, `deleted_branch` | only when the person decided the row `"production"` (a branch change left out on purpose), or the row lies beneath a `modify_delete_conflict` row the person kept. Otherwise never: the change was not applied |

Anything else is reported with its row. A mismatch means the work is not closed.

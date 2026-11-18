# Exclusions, exceptions, owners and reports

Back to [SKILL.md](../SKILL.md).

These need a server that has them. A ruleset that uses them should set `meta.min_server_version` (see "Sidecar YAML shape" in
SKILL.md), so an older server refuses it instead of ignoring the keys.

**Leave a package out.** `meta.exclude_packages` is a list of package names or GUIDs. Everything inside is
left out. A connector is still checked unless both of its ends are in excluded packages. Say what was left out
when you report a result.

```yaml
meta:
  exclude_packages: [Archive, "{3F2A...}"]
```

**Record an exception.** An exception waives one rule for one element, with a reason, who recorded it and a
date it ends. Put it under `exceptions:` in the ruleset, or in a file beside it named
`<ruleset>.exceptions.yaml`. All five fields are required, and a record with no `expires` is refused
(`invalid_exception`).

```yaml
exceptions:
  - rule_id: WBA-LFY-001
    element_guid: "{8C1D...}"
    reason: Retirement plan approved, runs to March
    recorded_by: <Reviewer A>
    expires: 2027-03-31
```

**Name the owner.** A report groups findings by the owner of each package. The owner is the value of the tag
that `meta.owner_tag` names, on the package's element. A package with no such value, and every package when the
ruleset sets no `meta.owner_tag`, shows "not set": the package author's login is never used. When a report shows
"not set", tell the person to set `meta.owner_tag` in the ruleset and to fill that tag on their package elements.

**Check on a date.** `as_of` (`YYYY-MM-DD`, in the audit's `params`) runs the check as of that date, so you can
see which exceptions expire by then. A bad date is `invalid_as_of`.

## Reading the result's new fields

- `violations`: each finding now also carries `element_guid` and `package_id`. `violation_count` counts only
  findings that no exception suppresses.
- `run_date` and `ruleset_id` are always present. `owner_tag` is present when the ruleset sets one. The ruleset
  id is `meta.id`, else `meta.language`, else the file name, else `inline`.
- `suppressed` and `suppressed_count`: the findings an exception waived, each with its `exception`. Read them. A
  suppressed finding is still a finding, so say how many there were.
- `exceptions_in_force`: exceptions that were live, each with how many findings it suppressed.
- `exceptions_expired`: exceptions past their date. Each lists the `findings` it would have hidden, and those
  findings are back in `violations`. Renew them deliberately or fix the model.
- `exceptions_unmatched`: exceptions that matched nothing (the element is gone, or the rule id is wrong). Clean
  them up; an exception that matches nothing may point at a typo.
- `excluded_packages`: for each `meta.exclude_packages` entry, the package it resolved to and how many packages,
  elements and connectors it left out. `excluded_packages_unmatched` lists entries that resolved to no package.
- `rule_stats[i].tags`: for the two tag conditions, a count per tag of how many items were examined and how
  many had a value (`{name, examined, filled}`).
- `history_file` or `history_error`, when `history_dir` was given (below).

Never report a clean run without saying how many findings were suppressed and which packages were excluded.

## Monthly and tollgate reports

`ea_validate(operation="audit", params={..., "history_dir": "<folder>"})` writes one small file of counts for the
run into a folder named for the ruleset's id inside it (`<YYYYMMDD>T<HHMMSS>-NN.json`; the time is `000000`
when `as_of` is given). It never overwrites an earlier file. The file holds counts only, not the findings. It is
the only file an audit writes, and the model is never changed.

`ea_validate(operation="get_report", params={...})` turns that into markdown. It reads only; it changes nothing.

| Param | Meaning |
|---|---|
| `format` | `monthly` or `tollgate` (required) |
| `history_dir` | the folder the audits wrote to; a monthly report compares against the newest earlier file. With no `result`, it renders the newest file against the one before it |
| `result` | an audit result; a tollgate report needs it, because the history file holds counts only |
| `ruleset_id` | picks one ruleset's history when the folder holds several |

```python
audit = ea_validate(operation="audit", params={
    "rules_path_or_content": "path/to/rules.yaml", "history_dir": "path/to/history"})
report = ea_validate(operation="get_report", params={
    "format": "tollgate", "result": audit, "history_dir": "path/to/history"})
```

It returns `{ok, format, ruleset_id, markdown}`, plus `passed` for a tollgate and `compared_with` for a monthly
report. Errors: `invalid_format`, `missing_source`, `invalid_result`, `tollgate_needs_result`, `ruleset_id_needed`
(the folder holds more than one ruleset), `no_history`. The `markdown` is yours to hand on; read `passed` and
the numbers behind it before you say a gate was met. A tollgate is not passed while any rule was cut short by
a read that could not be completed (`unreadable`), even with no errors: the report lists those rules under
"Rules that did not run to the end". Rerun them before the gate. A rule that examined nothing in the scope
(`rules_examined_nothing`) does not stop the gate passing, so a tollgate of one package with a ruleset for the
whole language can pass; the report lists those rules under "Rules that examined nothing". Say which they are,
and check that none of them examined nothing because its stereotype is misspelled or its technology is not loaded.

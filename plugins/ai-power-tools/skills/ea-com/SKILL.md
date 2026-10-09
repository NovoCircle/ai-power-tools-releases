---
name: ea-com
description: Use the Sparx EA COM API from Python to read and modify EA models — connect to a running instance, run SQL queries, manage MDG technologies, create/update elements, and control EA lifecycle. Use when automating EA work from a Python script.
---

# Sparx EA COM API — Python Automation

*Verified against EA 17.0 Build 1704.*

This skill is self-contained. Every snippet is plain `win32com.client` + `pywin32` —
there is no helper module to install. If you have Python, `pywin32`, and EA running
with a project open, you can follow this skill with nothing else.

> **Verification discipline — trust the EA model, not your memory.**
>
> When the user (or a calling script) asks anything about the current state of the
> model — *"does element X exist?"*, *"what's in package P?"*, *"what's the tagged
> value of T on E?"* — answer from a fresh read in the current turn, not from memory
> of what a script did earlier. Elements can be renamed, moved, or deleted; other
> users and out-of-band scripts can mutate the model; EA can roll back a transaction
> without telling Python. An answer about model state that isn't backed by a current
> read is a guess.
>
> | Question | Call |
> |---|---|
> | Existence by name | `sql("SELECT Object_ID, Name FROM t_object WHERE Name = '...'")` |
> | Existence by GUID | `sql("SELECT Object_ID, Name FROM t_object WHERE ea_guid = '{...}'")` |
> | Package contents | `sql("SELECT Object_ID, Name, Stereotype FROM t_object WHERE Package_ID = <id>")` |
> | Tagged values on E | `sql("SELECT Property, Value FROM t_objectproperties WHERE Object_ID = <id>")` |
> | Anything else | `sql("...")` — always authoritative |
>
> 1. Never assert model state from prior-turn memory — re-query, even if you "just" wrote it.
> 2. Persist IDs/GUIDs, not names. Names collide and get renamed; IDs are stable.
> 3. A successful COM mutation call is not proof of persistence — `repo.Execute()`
>    and the mutating collection methods return `None`, not a status you can check.
>    Always read back via `sql(...)` after a non-trivial write.
> 4. After an EA restart or project reopen, in-process COM references are stale —
>    reconnect and re-query before asserting anything.

## When COM is the right tool

Use `ea-com` when you need direct SQL access to the repository schema (bulk queries,
ad-hoc reporting, cross-table joins) or EA lifecycle control (technology load/enable
checks, restart) that the MCP server doesn't expose. If the task is building or
editing a model through well-formed operations — create element, add connector, set
tagged value — prefer the `ea-modeling` skill's MCP tools; they validate input
and don't require a Python environment on the machine running EA. Drop to COM when
MCP has no tool for what you need, or when you need raw SQL.

## Connecting

```python
import win32com.client

app = win32com.client.GetActiveObject("EA.App")
repo = app.Repository
print(repo.ConnectionString)   # -> "<model-dir>\WestbrookBank.qea"
```

`GetActiveObject("EA.App")` attaches to the currently running EA instance — it does
not launch EA. It fails if EA is not running or no project is open, raising
`pywintypes.com_error`. Wrap it in a retry loop for scripts that might race EA's
startup (for example, right after the restart pattern in
[`references/technology-and-lifecycle.md`](references/technology-and-lifecycle.md)):

```python
import time
import pywintypes
import win32com.client

def connect(retries=3, delay=2.0):
    last_err = None
    for attempt in range(retries):
        try:
            return win32com.client.GetActiveObject("EA.App").Repository
        except pywintypes.com_error as e:
            last_err = e
            if attempt < retries - 1:
                time.sleep(delay)
    raise RuntimeError(f"Could not connect to EA after {retries} attempts: {last_err}")

repo = connect()                       # default: 3 retries, 2s delay
repo = connect(retries=10, delay=3.0)  # for post-restart reconnect
```

Verified live: both forms return the connected `Repository`, and
`repo.ConnectionString` reads back the open project's path.

## SQL access — sql()/execute() helpers and the GetElementSet trap

Build a small `sql()` helper once per script — `Repository.SQLQuery()` returns XML,
not rows. Full helper code, the `t_object`/`t_objectproperties`/etc. table reference,
and the `execute()` / bulk-update pattern are in
[`references/connecting-and-queries.md`](references/connecting-and-queries.md).

The one trap to know before writing anything: **`Repository.GetElementsByQuery` does
not run SQL.** It runs a *named model search* — the first argument must be the name
of a saved Search, not a SQL string. Passing SQL to it raises
`com_error(..., 'Search Not Found', ...)` under a live (late-bound) connection.

```python
# WRONG — GetElementsByQuery's first arg is a saved-search name, not SQL
repo.GetElementsByQuery("SELECT Object_ID FROM t_object WHERE Stereotype='WBABusinessApplication'", "")
# -> raises com_error: 'Search Not Found'

# CORRECT — GetElementSet(sql, 2): type 2 means "SQL query against t_object"
elements = repo.GetElementSet(
    "SELECT Object_ID FROM t_object WHERE Stereotype = 'WBABusinessApplication'", 2)
for elem in elements:
    print(elem.Name, elem.Stereotype)
```

Verified live against the Westbrook Bank demo model: `GetElementsByQuery` raised the
`com_error` above; `GetElementSet(sql, 2)` returned all 45 matching elements,
iterable with `.Name` / `.Stereotype`.

## Another live trap: malformed SQL blocks on a modal dialog, not a Python exception

A `SQLQuery()` call against a table or column that doesn't exist does **not** raise
in Python and does **not** return an empty result immediately — EA raises a blocking
"SQL API Open FAILED" dialog first, and the call only returns (as an error XML
payload, not a Python exception) once a human dismisses it. An unattended script
hangs here. Verified live — details and the exact dialog text in
[`references/connecting-and-queries.md`](references/connecting-and-queries.md).
This is the same failure mode `latency.md` calls "any COM call that may trigger a
dialog"; it applies to read-only `SQLQuery()`, not just DML.

## Technology / MDG checks

```python
repo.IsTechnologyLoaded("WBA")      # bool — is the MDG loaded?
repo.IsTechnologyEnabled("WBA")     # bool — is it enabled for this project?
repo.GetTechnologyVersion("WBA")    # str — e.g. "1.0"
```

Verified live: all three returned correctly for the `WBA` technology.
`repo.GetTechnologyList` does **not** exist in EA 17 — it raises `AttributeError`
(verified live). Check technologies one ID at a time with `IsTechnologyLoaded`.
Mutating calls (`ActivateTechnology`, `DeleteTechnology`, `ImportTechnology`) are
deploy operations, not checks — see
[`references/technology-and-lifecycle.md`](references/technology-and-lifecycle.md)
and the `ea-mdg-deploy` skill.

## Mutating elements and tagged values

Create/update elements through the package's `Elements` collection, and set tagged
values by updating an **existing** row in `elem.TaggedValues`, not by blindly calling
`AddNew` — a stereotype's tags already exist as placeholder rows, and `AddNew`
creates a duplicate instead of overwriting one (a real trap, found and verified while
writing this skill). Worked, verified examples — including the correct update
pattern, the `AddNew` duplicate-row trap, and the bulk-SQL-update alternative — are in
[`references/mutating-elements.md`](references/mutating-elements.md).

## EA lifecycle: save, restart, and the post-mutation UI check

`repo.SaveAllDiagrams()` and `repo.RefreshModelView(0)` both return `None` on success
(verified live) — they are fire-and-forget; verify results with a `sql()` read-back,
not the return value.

Restarting EA is required after deploying an MDG, calling `DeleteTechnology`, or any
change that needs a fresh session. **This is the one procedure in this skill that was
not executed against the live model** — the verification pass for this skill was run
against a live, in-use EA session that had to stay open and unchanged, so the full
save/shutdown/relaunch/reconnect sequence was documented but not run end-to-end.
`repo.ShutdownEA` was confirmed to resolve to a real bound method without invoking
it. Full sequence, plus the post-mutation/post-query UI check pattern (take a
screenshot, expect "(Not Responding)" during long operations, never retry blind) in
[`references/technology-and-lifecycle.md`](references/technology-and-lifecycle.md).

For any COM call that drives visible EA UI state — restart, MDG import, a DML call
that might pop a dialog — follow the wait-then-screenshot timing in
[`../_shared/references/latency.md`](../_shared/references/latency.md).

## Dependencies

- `pywin32`: `pip install pywin32`
- EA must be running with a project open
- Windows only (COM is Windows-only)

## Reference files

- [`references/connecting-and-queries.md`](references/connecting-and-queries.md) —
  full `sql()`/`execute()` helpers, the SQLite schema notes (including the
  malformed-SQL dialog trap), the useful-tables reference, and common query patterns.
- [`references/mutating-elements.md`](references/mutating-elements.md) — creating
  elements, the tagged-value update pattern and the `AddNew` duplicate-row trap, and
  the bulk-SQL-update alternative.
- [`references/technology-and-lifecycle.md`](references/technology-and-lifecycle.md) —
  the COM object hierarchy, the restart pattern, the post-mutation UI check, and the
  full troubleshooting table.
- [`../_shared/references/latency.md`](../_shared/references/latency.md) — shared
  wait-time guidance for any COM call that can raise a blocking EA dialog.

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

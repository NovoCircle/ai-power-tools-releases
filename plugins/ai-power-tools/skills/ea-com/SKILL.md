---
name: ea-com
description: Use the Sparx EA COM API from Python to read and modify EA models — connect to a running instance, run SQL queries, manage MDG technologies, create/update elements, and control EA lifecycle. Use when automating EA work from a Python script.
---

# Sparx EA COM API — Python Automation

*Measured on two EA builds: 17.0 build 1704 (the first pass) and 17.1 build 1716 (later checks).
A statement that names a build holds for that build. A statement that names none was first checked
on 1704 and has not been re-checked on later builds. Cloud repositories on a MySQL back end were
checked on EA 17.0.*

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

Raw SQL is not a reason to use COM: the MCP server's `ea_analyze(operation="execute_sql")` runs
SQL against the open repository and checks column names before EA sees them. Use that first for
queries; its rules (`_shared/references/sql-for-execute-sql.md`) hold for `SQLQuery()` too.

Use `ea-com` when you need something the MCP server doesn't expose: the COM-only calls
(`GetElementSet`, `Repository.Execute` for bulk DML, technology load/enable checks, EA lifecycle
control such as restart), or work on an EA instance other than the one the server is attached to
(see [`references/instances-and-sessions.md`](references/instances-and-sessions.md)). If the task
is building or editing a model through well-formed operations (create element, add connector, set
tagged value), prefer the `ea-modeling` skill's MCP tools; they validate input and don't require a
Python environment on the machine running EA.

**Two rules before any script that writes.** Open each model file in at most one EA session at a
time (visible or headless), and never `Update()` an object you held from before an outside write.
Both are in [`references/instances-and-sessions.md`](references/instances-and-sessions.md).

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

**`GetActiveObject("EA.App")` is safe only when exactly one EA is running.** With several
running (visible or headless) it attaches to whichever registered first, which can be an
instance with no project open (`ConnectionString` is `''`) or a different model from the one you
mean. The MCP server does not guess: with more than one EA running (server 3.6.5 or later) it makes no
call into EA and returns `ea_choice_needed`, and you ask the person which EA to use and call `launch_ea` with it as `target`
(see `ea-start-here`). To reach a specific instance from a script, attach by process id or by its exact `Data Source=`,
and check `repo.ConnectionString` before every write:
[`references/instances-and-sessions.md`](references/instances-and-sessions.md).

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
`com_error` above; `GetElementSet(sql, 2)` returned every matching element,
iterable with `.Name` / `.Stereotype`.

## Another live trap: malformed SQL blocks on a modal dialog, not a Python exception

A `SQLQuery()` call against a table or column that doesn't exist does **not** raise
in Python. EA shows a visible modal ("SQL API Open FAILED with error: no such table: ...")
and the call blocks until someone dismisses it. It then returns an empty result with no
exception, and `GetLastError()` is `''`, so a bad query looks exactly like "no rows". Headless
EA shows the dialog on the user's desktop too. An unattended script hangs here.

- `SuppressEADialogs = True` did not prevent this dialog on build 1704 (set before `OpenFile` it
  reads back False; set after, it reads back True and the dialog still appears). A different
  dialog was suppressed on build 1716, so scope the setting to the dialog you tested.
- For a `.qea` file, check each statement before sending it: `EXPLAIN <sql>` through Python
  `sqlite3` opened read-only (`file:<path>?mode=ro`). It catches a wrong column before EA sees it.
- For unattended runs, use the dialog watchdog, and never auto-answer a question dialog.

Dialog text, the `EXPLAIN` helper and the watchdog are in
[`references/connecting-and-queries.md`](references/connecting-and-queries.md) and
[`references/instances-and-sessions.md`](references/instances-and-sessions.md). This is the
same failure mode `latency.md` calls "any COM call that may trigger a dialog"; it applies to
read-only `SQLQuery()`, not just DML.

## `Repository.Execute` and cloud repositories

`Execute` returns nothing and, on some back ends, fails without an error. On a cloud repository
with a MySQL back end `GETDATE()` ran with no error and wrote no row, while `NOW()` worked. Every
write must be read back. Dialect differences are listed in
[`references/connecting-and-queries.md`](references/connecting-and-queries.md).

## Technology / MDG checks

```python
repo.IsTechnologyLoaded("WBA")      # bool — is the MDG loaded?
repo.IsTechnologyEnabled("WBA")     # bool — is it enabled for this project?
repo.GetTechnologyVersion("WBA")    # str — the version EA reports for the loaded copy; read it, don't assume
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

**Rule for any reply about installing or removing a modeling language (technology):** start by
handing the job to `ea-mdg-deploy`, and say that a removal takes effect only after EA restarts and
can change what the open session offers. Don't offer a route through EA's UI or `DeleteTechnology` /
`ImportTechnology` from this skill. This skill only documents that those calls exist.

`repo.SaveAllDiagrams()` and `repo.RefreshModelView(0)` both return `None` on success
(verified live): they are fire-and-forget; verify results with a `sql()` read-back,
not the return value.

Restarting EA is required after deploying an MDG, calling `DeleteTechnology`, or any
change that needs a fresh session. On build 1716 `repo.ShutdownEA()` with no argument fails
with "Parameter not optional"; `repo.ShutdownEA(0)` works and closes the window at once. The
process exited in 2 to 3 seconds on a visible EA started with `EA.exe <model>`, and once took about
3.5 minutes. Relaunch only after the old process has exited (poll for it with a bound), never after a fixed sleep. The full sequence and the post-mutation UI check
pattern (screenshot, expect "(Not Responding)" during long operations, never retry blind) are in
[`references/technology-and-lifecycle.md`](references/technology-and-lifecycle.md). The sequence
was run through a relaunch on a visible EA; a headless EA was not tested.

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
  elements, the stereotype read-back, the tagged-value update pattern and the `AddNew`
  duplicate-row trap, the bulk-SQL-update alternative, keeping GUIDs (unverified), and storing
  a file on an Artifact.
- [`references/technology-and-lifecycle.md`](references/technology-and-lifecycle.md) —
  the COM object hierarchy, the restart pattern, removing a technology from a model, the
  post-mutation UI check, and the full troubleshooting table.
- [`references/instances-and-sessions.md`](references/instances-and-sessions.md) — attaching
  to a specific EA instance, headless EA, one session per model, and the dialog watchdog.
- [`../_shared/references/latency.md`](../_shared/references/latency.md) — shared
  wait-time guidance for any COM call that can raise a blocking EA dialog.

## Verify in EA's UI

EA reports success it has not earned, and reports failure as a modal dialog that blocks the
COM connection rather than as an error you can catch. Neither shows up in a tool response.

- **If a call seems to hang, screenshot EA and read the dialog before concluding anything.**
  It names the cause. Dismiss from the front — dialogs stack, and a later call can be queued
  behind one raised by an earlier one. Windows reporting EA as "Responding" means nothing.
- **This skill edits no diagram.** If a script's work creates or edits one, reload it,
  screenshot it, and look: `ok: true` means rows were written, not that the result is
  readable.
- **Without computer use**, say so. Ask the user to paste a screenshot of the EA window or
  dialog into the conversation, read the cause from it, and ask the user to dismiss the dialog
  before you retry. Never report a hang you have not diagnosed or a diagram you have not seen.

Full procedure: [`../_shared/references/ea-ui-verification.md`](../_shared/references/ea-ui-verification.md)

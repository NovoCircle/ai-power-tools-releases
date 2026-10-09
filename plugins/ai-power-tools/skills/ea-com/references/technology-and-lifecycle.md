# Technology checks, EA lifecycle, and troubleshooting

Full detail behind the "Technology / MDG checks" and "EA lifecycle" sections of
`../SKILL.md`.

## Technology / MDG checks (read-only, verified live)

```python
>>> repo.IsTechnologyLoaded("WBA")
True
>>> repo.IsTechnologyEnabled("WBA")
True
>>> repo.GetTechnologyVersion("WBA")
'1.0'
```

`repo.GetTechnologyList` does not exist in EA 17 — verified live:

```python
>>> repo.GetTechnologyList
AttributeError: <unknown>.GetTechnologyList
```

Check technologies one ID at a time with `IsTechnologyLoaded(id)` instead of
enumerating.

## Technology mutation calls (not exercised here)

`ActivateTechnology(id)`, `DeleteTechnology(id)`, and `repo.ImportTechnology(xml)`
exist on `Repository` and mutate technology load/enable state. Treat both as risky
against a session someone else may be relying on: `DeleteTechnology` only takes effect
after an EA restart, and `ActivateTechnology` can change what's available in the
live session's toolboxes and diagrams while it's in use — unlike the read-only checks
above, and undoing a mistake reliably needs the same restart this pass could not
perform. MDG deployment is `ea-mdg-deploy`'s subject; this skill only documents that
these calls exist:

```
repo.ActivateTechnology(id)   # bool -- enable/toggle
repo.DeleteTechnology(id)     # bool -- marks for removal (takes effect after restart)
repo.ImportTechnology(xml)    # bool -- embed MDG XML into the model (model-embedded deploy)
```

## Lifecycle: save and refresh

```python
>>> repo.SaveAllDiagrams()
None
>>> repo.RefreshModelView(0)
None
```

Both verified live — both return `None` regardless of outcome. Treat them as
fire-and-forget; verify any change they were meant to reveal with a `sql()` read, not
their return value.

## Element/package navigation

```python
elem = repo.GetElementByGuid("{GUID-HERE}")
pkg = repo.GetPackageByGuid("{GUID-HERE}")
```

Verified live: both resolved a scratch element/package by GUID during the mutation
tests in `mutating-elements.md`.

## EA restart pattern — documented, not executed

Required after deploying an MDG, calling `DeleteTechnology`, or any operation that
needs a fresh session. **This procedure was not run end-to-end against the live
model** — the verification pass for this skill used a live, in-use EA session that
had to stay open and unchanged throughout, so restarting it was out of bounds. The
one check performed was confirming `repo.ShutdownEA` resolves to a real bound COM
method without invoking it:

```python
>>> hasattr(repo, "ShutdownEA"), repo.ShutdownEA
(True, <bound method ShutdownEA of <COMObject <unknown>>>)
>>> repo.ConnectionString   # confirms the attribute lookup alone didn't close EA
'<model-dir>\\WestbrookBank.qea'
```

The full sequence, as documented (not live-verified beyond the check above):

```python
import subprocess
import time

path = repo.ConnectionString
repo.SaveAllDiagrams()
time.sleep(0.5)
repo.ShutdownEA()
time.sleep(8)    # wait for the process to fully exit

subprocess.Popen([r"C:\Program Files\Sparx Systems\EA\EA.exe", path])
time.sleep(12)   # wait for EA to open and be ready for COM

new_repo = connect(retries=10, delay=3.0)   # see connecting-and-queries.md
```

After a restart, every COM reference held from before it (the old `repo`, any
`elem`/`pkg` objects) is stale — reconnect and re-query rather than reusing them.

## Post-mutation / post-query UI check

Any COM call that can pop a modal dialog — a mutating call, or (as found while
verifying this skill — see `connecting-and-queries.md`) even a read-only `SQLQuery()`
against a bad table or column — blocks until a human dismisses that dialog. The
general pattern:

1. Make the call.
2. Take a screenshot immediately, before any wait, in case a dialog is already up.
3. Wait the interval given in
   [`../../_shared/references/latency.md`](../../_shared/references/latency.md) for
   that kind of operation.
4. Take a second, confirming screenshot.
5. If EA's title bar shows "(Not Responding)", that's normal during long operations,
   not a crash — wait and check again rather than retrying the call.

This is exactly what happened live during this skill's own verification: two
malformed diagnostic queries each raised a real "SQL API Open FAILED" dialog that
blocked the Python process until dismissed through the EA UI. See
`connecting-and-queries.md` for the exact dialog text.

## Troubleshooting

| Error | Cause | Fix |
|-------|-------|-----|
| `Could not connect to EA` | EA not running, or no project open | Launch EA, open project, retry |
| `AttributeError: GetTechnologyList` | Method doesn't exist in EA 17 | Use `IsTechnologyLoaded(id)` per tech |
| `ImportTechnology` returns `False` | XML error or EA showed a dialog | Check EA for a modal dialog; validate XML; check ID lengths <= 12 chars |
| `GetElementsByQuery` raises `com_error('Search Not Found')` | Raw SQL passed — wrong method | Use `GetElementSet(sql, 2)` instead |
| `SQLQuery()` hangs / EA shows a modal dialog | Malformed SQL — bad table or column name | Dismiss the dialog, fix the SQL; never assume `SQLQuery()` fails silently |
| COM call succeeds but change not visible | Needs `refresh()` or an EA restart | Call `repo.RefreshModelView(0)`, or restart EA |
| `pywintypes.com_error: -2147221246` | EA closed while a COM ref was held | Reconnect: `connect()` |
| SQL error on `t_stereotype` | Table doesn't exist in this schema | Query `t_object` instead (see `connecting-and-queries.md`) |
| SQL error on `t_attribute.Default_Value` | Column doesn't exist | Use `a.[Default]` (bracket-quoted) |
| `TaggedValues.AddNew()` creates a second row for an existing tag | Stereotype tags are pre-populated as `NULL` placeholders | Iterate `TaggedValues` and update the existing row instead (see `mutating-elements.md`) |
| `repo.Execute()` / `SaveAllDiagrams()` / `RefreshModelView()` return `None` even on success | These calls don't report status | Always verify with a `sql()` read-back |

## COM object hierarchy

```
EA.App
+-- Repository
    +-- Models[]                 # root packages
    |   +-- Packages[]
    |       +-- Elements[]
    |       |   +-- Attributes[]
    |       |   +-- Operations[]
    |       |   +-- TaggedValues[]
    |       +-- Diagrams[]
    +-- SQLQuery(sql)            # raw XML result
    +-- Execute(sql)             # non-SELECT; always returns None
    +-- ImportTechnology(xml)
    +-- IsTechnologyLoaded(id)
    +-- IsTechnologyEnabled(id)
    +-- GetTechnologyVersion(id)
    +-- ActivateTechnology(id)
    +-- DeleteTechnology(id)
    +-- GetElementSet(sql, 2)    # correct bulk element retrieval
    +-- GetElementByGuid(guid)
    +-- GetPackageByGuid(guid)
    +-- RefreshModelView(0)      # always returns None
    +-- SaveAllDiagrams()        # always returns None
    +-- ShutdownEA()
```

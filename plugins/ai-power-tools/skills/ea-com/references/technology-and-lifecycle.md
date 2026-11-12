# Technology checks, EA lifecycle, and troubleshooting

Full detail behind the "Technology / MDG checks" and "EA lifecycle" sections of
`../SKILL.md`.

**Installing or removing a modeling language is `ea-mdg-deploy`'s job.** A reply about either
starts with that hand-off and says that a removal takes effect only after EA restarts. Nothing
below is a route for doing it from this skill.

## Technology / MDG checks (read-only, verified live)

```python
>>> repo.IsTechnologyLoaded("WBA")
True
>>> repo.IsTechnologyEnabled("WBA")
True
>>> repo.GetTechnologyVersion("WBA")
'1.0'   # what EA reported when this was measured; the Westbrook technology file now declares 1.1.1
```

`repo.GetTechnologyList` does not exist in EA 17 — verified live:

```python
>>> repo.GetTechnologyList
AttributeError: <unknown>.GetTechnologyList
```

Check technologies one ID at a time with `IsTechnologyLoaded(id)` instead of
enumerating.

Ids that answered True on EA 17.1 build 1716 (one run, a model with its own embedded technology open): `ArchiMate3`, `Archimate`, `BPMN2.0`, `BPMN`, `SysML1.4`, `SysML1.3`, `SoaML`, `TOGAF`, `UAF`, `ERD`, `ZF`, `MindMapping`, `StrategyMap`, `RAAML1.0`, `EAExtended`, `EAExtended:Requirements`, `BABOK` and the embedded technology's own id. False: `UML` (native, not a technology), `SysML`, `BPMN2`, `Zachman`, `TOGAF9`, `ArchiMate3.1`, `UPDM`, `UAFP`, `DMN`, `DMN1.3` and a technology's display name. `CSDM5` and `IT4IT` were False because they were not embedded in that model. The id is the technology id, not the name EA shows in Manage Technology.

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
repo.DeleteTechnology(id)     # bool -- returns True but acts only on technologies installed on the machine; one imported into the model stays (see below)
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

## EA restart pattern

Required after deploying an MDG, calling `DeleteTechnology`, or any operation that needs a fresh
session. Checked on EA 17.1 build 1716: `repo.ShutdownEA()` with no argument fails with
"Parameter not optional", and `repo.ShutdownEA(0)` works. The exit time varies a lot. On a
visible EA started with `EA.exe <model>` and attached through the Running Object Table, the
process exited 2 to 3 seconds after the call (several runs, build 1716). An earlier run on a
different setup took about 3.5 minutes. Both are single observations, so poll for the exit with a
bound instead of using a fixed `time.sleep`: relaunching while the old process is alive risks a
second EA instance.

What the argument means is not stated in anything checked here: `0` is the value that worked.
`1` also exited in the same time with nothing unsaved, so no difference between the two was
found. Check Sparx's `Repository` class documentation for the meaning before using another value.

The sequence below waits for the old process to exit (bounded), checks that no EA process is
running, relaunches, and reconnects. The shutdown, the wait for exit and the relaunch of a visible
EA with a model path were run on build 1716, and the relaunched EA was reached by attaching by
process id (see `instances-and-sessions.md`). Not tested: a headless EA started with
`Dispatch("EA.App")` or `DispatchEx`, and what `0` versus `1` means.

```python
import subprocess
import time
import psutil          # pip install psutil; or poll `tasklist` instead

def ea_running():
    return [p for p in psutil.process_iter(["name"]) if (p.info["name"] or "").lower() == "ea.exe"]

path = repo.ConnectionString
ea_exe = r"<EA install folder>\EA.exe"      # find it from the running process: ea_running()[0].exe()
repo.SaveAllDiagrams()
time.sleep(0.5)
repo.ShutdownEA(0)

deadline = time.time() + 600                  # allow ten minutes: exits took 2 to 3 seconds, and once about 3.5 minutes
while ea_running() and time.time() < deadline:
    time.sleep(5)
if ea_running():
    raise RuntimeError("EA is still running; ask the person before ending it")

subprocess.Popen([ea_exe, path])
time.sleep(12)   # wait for EA to open and be ready for COM

new_repo = connect(retries=10, delay=3.0)   # see connecting-and-queries.md
```

After a restart, every COM reference held from before it (the old `repo`, any
`elem`/`pkg` objects) is stale — reconnect and re-query rather than reusing them.

## Removing a technology that was imported into a model

`repo.DeleteTechnology(id)` returns `True` but acts only on technologies installed on the
machine. A technology imported into the model stays. In the model it is one `t_document` row
(`DocType = 'TECHNOLOGY'`, `DocName = <id>`). Removing it is deployment work: hand it to
`ea-mdg-deploy`, whose steps are, in short:

1. Check nothing uses it: no `FQName=<id>::` bindings in `t_xref`, no `MDGDgm=<id>::` diagrams.
2. Back up the model (an EA baseline of the affected package, per your project's rule).
3. Remove the row, or use EA's Manage Technology, Remove.
4. Reopen the model, because EA keeps the old technology loaded until then.

```python
sql("SELECT COUNT(*) AS n FROM t_xref WHERE Description LIKE '%FQName=<id>::%'")
sql("SELECT COUNT(*) AS n FROM t_diagram WHERE StyleEx LIKE '%MDGDgm=<id>::%'")
sql("SELECT DocID, DocName FROM t_document WHERE DocType = 'TECHNOLOGY' AND DocName = '<id>'")
```

(The `t_xref` and `t_diagram` column names are the usual places for those markers; confirm on
your model before relying on a zero.)

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
| `SQLQuery()` hangs / EA shows a modal dialog | Malformed SQL — bad table or column name | Dismiss the dialog, fix the SQL; check `.qea` statements with `EXPLAIN` first; never assume `SQLQuery()` fails silently or that an empty result means no rows |
| `ShutdownEA()` raises "Parameter not optional" | Build 1716 requires an argument | `repo.ShutdownEA(0)`, then wait for the process to exit before relaunching |
| COM call succeeds but change not visible | Needs `refresh()` or an EA restart | Call `repo.RefreshModelView(0)`, or restart EA |
| `pywintypes.com_error: -2147221246` | EA closed while a COM ref was held | Reconnect: `connect()` |
| SQL error on `t_stereotype` | The singular table doesn't exist in this schema | Query `t_object` for stereotypes in use, or `t_stereotypes` (plural) for definitions (see `connecting-and-queries.md`) |
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
    +-- ShutdownEA(0)            # the argument is required on build 1716
```

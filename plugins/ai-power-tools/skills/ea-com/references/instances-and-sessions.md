# Instances, headless EA, and one session per model

Full detail behind the "Connecting" and "Another live trap" sections of `../SKILL.md`. The
measurements here come from parallel-session experiments on EA 17.0 build 1704 (`.qea` files) and
two live checks on EA 17.1. They are few samples on a small number of machines. The snippets are
written from those experiments and have not been re-run as printed here; run them against a copy
before you trust them on a model that matters.

## One EA session per model file

Open each model file in at most one EA session at a time, visible or headless. Use file copies for
parallel work. Never run a headless and a visible session on the same model: the visible one does
not refresh when another process writes, so it shows stale content.

Why, from one run on a `.qea` (rollback journal, build 1704):

1. Session 1 held an element object.
2. Session 2 opened the same file and renamed the element.
3. Session 1 changed only the notes on its stale object and called `Update()`.
4. The file ended with session 1's old name. `Update()` rewrites the whole row, so session 2's
   rename was lost with no error.

Also observed: EA held no exclusive lock while idle (a direct SQLite write and a second EA both
succeeded); `SQLQuery` and a fresh `GetElementByGuid` saw outside writes, a held object did not.

So: after any outside write, re-fetch with `GetElementByGuid` / `GetElementByID` and never
`Update()` an object held from before.

**Not tested, treat as unverified:** two read-only sessions on one file; SQLite busy or locking
during an active write transaction; WAL mode; `.eap`/`.feap` files; DBMS repositories; network
shares. The one-session rule is a precaution, not a confirmed limit of EA.

## Attach to a specific instance

`GetActiveObject("EA.App")` attaches to whichever instance registered first. With four EA instances
running it attached to one with no project open. Every EA instance, visible or headless
(`EA.exe -Embedding`), registers an item moniker `!Sparx.EA.App:<PID>` in the Windows Running
Object Table; binding that entry reached the intended instance every time in the experiments
(reads, writes, `OpenDiagram`, `ReloadDiagram`, `ImportTechnology`, XMI export and import).
On build 1716 it was also run with two visible EAs on different models: each entry's
`ConnectionString` matched the model launched in it, and `GetActiveObject("EA.App")` returned the
first one started. It also works for an EA with no model open (empty `ConnectionString`). The
three-instance case with a headless EA was not rerun on 1716.

```python
import pythoncom
import win32com.client

def running_ea():
    """Yield (pid, Repository) for every EA instance in the Running Object Table."""
    ctx = pythoncom.CreateBindCtx(0)
    rot = pythoncom.GetRunningObjectTable()
    for mk in rot.EnumRunning():
        name = mk.GetDisplayName(ctx, None)
        if name.startswith("!Sparx.EA.App:"):
            disp = rot.GetObject(mk).QueryInterface(pythoncom.IID_IDispatch)
            yield int(name.rsplit(":", 1)[1]), win32com.client.Dispatch(disp).Repository

def attach_by_pid(pid):
    for p, repo in running_ea():
        if p == pid:
            return repo
    raise RuntimeError(f"No EA with PID {pid} in the Running Object Table")

def attach_by_model(connection_string):
    """Match the exact ConnectionString (a file path, or the Data Source= text of a cloud repository)."""
    hits = [r for p, r in running_ea() if r.ConnectionString == connection_string]
    if len(hits) != 1:
        raise RuntimeError(f"{len(hits)} EA instances have that model open; expected exactly 1")
    return hits[0]

repo = attach_by_pid(12345)
assert repo.ConnectionString == r"<model-dir>\WestbrookBank.qea"   # check before every write
```

With a test, a production and a source repository open at once, find the instance by its exact
`ConnectionString` (`Data Source=...` for a cloud repository), not by "the first EA".

**Finding the PID.** Use the process you launched, or the Windows Restart Manager (`RmGetList`) on
the model file. `RmGetList` also lists any Python process that holds a read-only SQLite connection
to that file, so do not end every process it names.

**While more than one EA is open, the MCP server asks instead of guessing** (server 3.6.5 or later):
it makes no call into EA and returns `ea_choice_needed` with each running EA's process id and open
model. Ask the person which one to use and call `launch_ea` with it as `target` (see `ea-start-here`); later calls follow that EA. Before 3.6.5 the
server attached the way `GetActiveObject` does, so treat its tools as read-only while more than one EA
is open.

## Headless EA

`DispatchEx("EA.Repository")` followed by `OpenFile` starts an EA with no window. Three ran in
parallel without interfering (build 1704, `.qea`).

- `OpenFile` took 27.8 to 83 s on build 1704 and 13 s on a fresh copy on build 1716. On build 1716,
  with a visible EA started as `EA.exe` (not headless) and a 5 MB model, it took 2.8 to 4.9 s; three EAs
  opened at once took 8 to 10 s each. Queries
  afterwards took 1 to 27 ms. Open each model once and reuse it for the whole task, and allow at
  least 120 s for the open.
- `CloseFile()` then `Exit()` ended the process in under 0.3 s in the first runs. In two later runs
  on 17.1, started with `Dispatch("EA.App")`, the process stayed alive at high CPU for 19 and about
  50 minutes after both calls, while the Python client was blocked on another call and still held a
  reference. A later headless EA in a long-lived client closed in under 45 s. Release your
  references before you expect the process to end.
- A headless EA whose client crashed before `CloseFile()`/`Exit()` stayed alive indefinitely,
  ignored `WM_CLOSE`, and had to be force-ended (one occurrence). Record the PID so a supervisor can
  end orphans, and ask the person before ending a process.
- `DispatchEx` starts `EA.exe -Embedding` under DCOM, so process snapshots before and after cannot
  attribute PIDs when two start at once. Take the PID from the Running Object Table.
- `Visible = True` did not show the main window on 17.1, but EA's modal dialogs still showed.
- Create new models with `CreateModel`, not by copying EA's shipped base model file: two copies share that file's root
  package GUID, and `CreateModel` models do not. An import collision between two copies was not
  tested. `Repository.CreateModel(0, <path>.qea, 0)` creates a file model. Do not use type 1: it
  opens Windows' Data Link Properties dialog. `CreateModel` with a `.qeax` path returned False and
  created nothing (a `.qeax` can be created from EA's Create New screen).

```python
import win32com.client

app = win32com.client.DispatchEx("EA.Repository")
try:
    ok = app.OpenFile(r"<model-dir>\WestbrookBank.qea")   # allow 120 s or more
    # ... read and write, re-reading after every write ...
finally:
    app.CloseFile()
    app.Exit()
    # release every reference you hold (repo, element, package objects) before expecting the process to end
```

## Dialog watchdog for unattended runs

A bad `SQLQuery` raises a modal even in headless EA (see `connecting-and-queries.md`). A
background thread can see it: poll `EnumWindows` for visible `#32770` windows owned by the EA
process, ignoring the hidden "Manage Searches" dialog; read the text with `EnumChildWindows`;
dismiss only an error dialog by sending `BM_CLICK` to its OK button; and report the dialog text as
the error. In the experiments the watchdog caught each dialog within about 0.4 s.

**A question dialog stops the run and is reported to the person. It is never answered
automatically.** This part was not tested.

Better still, do not raise the dialog: check each statement with `EXPLAIN` first (see
`connecting-and-queries.md`).

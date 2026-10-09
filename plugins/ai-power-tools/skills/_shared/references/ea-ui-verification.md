# Verifying EA in the UI — errors and visual results

Shared by every skill that drives Sparx EA. Two things the API will not tell you honestly:
**when an operation failed**, and **when an operation succeeded but produced the wrong
picture**. Both are visible on screen in seconds.

Related: [`latency.md`](latency.md) covers how long to wait before looking. This file covers
what to look for and what to do about it.

> **The principle: EA reports success it has not earned.** `export_xmi` reported
> `"status": "exported"` while writing an empty file in the wrong format. `install_skills`
> returned `ok: true` while writing to a directory nothing reads. `update_element` returns
> `ok: true` when a property it could not apply went into `rejected_properties` instead.
> A success response is a claim, not evidence.

---

## Part 1 — Blocking error dialogs

### The symptom

A tool call never returns. Nothing raises, nothing times out.

**EA does not report a failed operation by returning an error.** It opens a native modal
dialog and waits for a human to click OK, holding the COM connection the whole time.

Everything that looks like a hang looks identical to one:

| What you can observe | Why it misleads |
|---|---|
| The call has not returned for minutes | Same as a deadlock |
| Windows reports EA as **"Responding"** | True whenever a modal dialog is pumping messages — it does **not** mean EA is idle and healthy |
| CPU time is near zero | EA is waiting on a click, not computing |

**None of these tell you anything.** A `try`/`except` around the call cannot help either,
because nothing is ever raised.

### The rule

> **When an EA call appears to hang, look at EA's screen before concluding anything.**

Do not report a hang, kill a process, restart EA, or retry the call until you have looked.
The dialog almost always names the exact cause — it is the best diagnostic available, and it
is free.

### Procedure

1. **Screenshot EA.** Do this first, before any wait. The dialog may already be up.
2. **Read every dialog.** Zoom if the text is small. The message usually carries the failing
   operation verbatim.
3. **Identify the cause** before dismissing anything.
4. **Dismiss from the front.** Click OK on the topmost dialog, screenshot again, repeat.
   **Dialogs stack.** One blocked call can leave several behind, and each earlier one is
   still holding the connection.
5. **Fix the cause, then retry.** Retrying the same call reopens the same dialog.
6. **Confirm recovery** with a cheap call — `ping()`, then
   `ea_repository(operation="get_repository_info", params={})`.

A later call that seems to hang for no reason is usually queued behind a dialog raised by an
*earlier* one. The operation you are looking at may not be the operation at fault.

### Reading SQL failures

```
Sparx Systems Database API [0x00001072]
SQL API Open FAILED with error: <message>
Context:
<the exact SQL>
```

The `Context:` line is the query. The error names the problem.

| Error text | Cause | Fix |
|---|---|---|
| `no such function: OCTET_LENGTH` | A function the backend does not have. A `.qea` is SQLite | Use `LENGTH(...)` for byte counts |
| `near "1": syntax error` on `SELECT TOP 1 ...` | T-SQL syntax against SQLite | If the query is yours, use `LIMIT`. If it is not in your code, EA issued it internally — report it, and treat the operation's result as unverified |
| `no such column` | Column name or table wrong for this EA version | Check with `ea_analyze(operation="describe_table", ...)` |

**Any SQL a backend cannot run becomes a blocking dialog.** `get_repository_info` reports the
repository type; `SL3` means SQLite.

### Other frequent dialogs

| Dialog | Meaning | What to do |
|---|---|---|
| `Root import package already exists in another location` | An XMI import collided with content already in the model | Dismiss, then import with `strip_guid=True` (the default) to bring it in as a copy |
| `Please go to «ArcGIS» Workspace package for ArcGIS export!` | The publish path expects an ArcGIS workspace | Dismiss and use `export_xmi` instead |
| `Profile already exists. Overwrite?` | Expected during MDG import — see [`latency.md`](latency.md) | Answer it deliberately; this one is part of the flow |
| `Duplicate profile name ... detected in technology ID` | A technology was imported more than once | Usually a System Output warning rather than a modal. Safe to continue |

### System Output

EA's **System Output** panel keeps warnings that never become dialogs. When a result looks
wrong but nothing is blocking, read it — it often explains a silent partial failure.

---

## Part 2 — Verifying a diagram actually looks right

**Every diagram create or edit ends with a screenshot.** A diagram is a visual artifact, and
the only honest check is to look at it.

`ok: true` from a diagram call means the rows were written. It does not mean elements are
where you intended, that the layout is readable, that styling applied, or that connectors
are not crossing the whole page.

### Procedure

1. Make the change.
2. Open the diagram in EA: `ea_diagram(operation="open_diagram", params={"diagram_id": N})`.
3. Reload it if you wrote directly to the tables:
   `ea_diagram(operation="reload_diagram", params={"diagram_id": N})`. Without this, EA can
   keep showing a cached render and you will verify the *old* picture.
4. Wait per [`latency.md`](latency.md), then **screenshot**.
5. Compare against what you intended, not against whether the call succeeded.

### What to check

| Check | Why it matters |
|---|---|
| Every element you placed is visible | A placement can be written and still land off-canvas |
| Nothing overlaps or is stacked | Overlap usually means positions were ignored and a layout ran instead |
| Connectors you expected are shown, and ones you suppressed are not | EA adds connectors on reload regardless of `auto_connectors=False` (`APT-2026-0069`) |
| Styling applied | Colors and sizes set through the wrong route are silently dropped |
| Nesting is real containment, not visual overlap | For drill-down diagrams, children must sit inside the parent |
| The layout is readable at normal zoom | "Correct" and "usable" are different results |

### If it is wrong

Fix the model or the diagram data and re-verify. Do not describe the diagram as done on the
strength of the API response — say what the screenshot showed.

---

## Without computer use

If computer use is not available in the session, you cannot see any of this yourself. Say so
plainly rather than reporting success you have not verified, or reporting a hang you have not
diagnosed.

For a blocked call:

> "The call has not returned. EA reports errors as a dialog box that blocks everything until
> it is dismissed, so please check the Enterprise Architect window. If a dialog is showing,
> tell me what it says and click OK."

For a diagram:

> "The diagram data is written. I cannot see the result, so please open it in EA and tell me
> whether the layout looks right — anything overlapping, missing, or unreadable."

The user's answer gives you the same information the screenshot would have. Everything after
that point is unchanged.

**Never** report "EA is hung", "the operation timed out", "EA crashed", or "the diagram is
ready" without either looking yourself or asking the user to look.

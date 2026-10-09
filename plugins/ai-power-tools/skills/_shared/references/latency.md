# EA computer-use latency guidelines

Shared by every skill that drives the Sparx EA desktop UI directly — via computer-use
screenshots and clicks, or via a COM call from `ea-com` that can raise a blocking modal. If a
skill's own text summarizes this in one or two sentences, this file is the full detail behind
that summary.

EA is a single-threaded desktop app: a slow operation blocks its UI thread, and a screenshot
taken too early just shows the state before the operation finished. Waiting the right interval
before screenshotting — not immediately, and not an arbitrary flat delay — is what keeps
verification honest.

---

## Wait-time table

| Operation | Wait before screenshot |
|---|---|
| Any menu click or button in EA UI | 2–5 seconds |
| Opening a `.qea` project file (EA UI, or COM `repo.OpenFile()` / `repo.CloseFile()`) | 5–15 seconds — for the COM calls specifically, expect the wait to run toward the top of this range rather than the bottom |
| Importing or deploying an MDG (EA UI, or COM `repo.ImportTechnology()`) | 3–8 seconds |
| Expanding a package in Project Browser | 1–3 seconds |
| Any COM call that may trigger a dialog | 3–5 seconds |
| `repo.Execute()` DML (no dialog expected) | 1–3 seconds |

---

## Standard pattern

1. Perform the action (click, COM call, or MCP tool call that triggers an EA UI change).
2. Wait the interval given in the table above for that operation — not a flat number.
3. Take a screenshot to verify the result.
4. If EA shows **"(Not Responding)"** in its title bar: this is normal during file and import
   operations, not a crash. Wait another 5 seconds and screenshot again before concluding
   anything failed.
5. **Never retry an action** without first confirming the previous one actually failed.

> **"(Not Responding)"** means EA is processing, not crashed. Do not double-click, re-issue the
> command, or open a second EA instance while waiting.

For a COM call that can raise a blocking modal dialog immediately on return (for example
`repo.ImportTechnology()`'s "Profile already exists. Overwrite?" prompt), take one screenshot
right away — before the wait in step 2 — in case the dialog is already up, then follow the
standard pattern for a second, confirming screenshot. A skill whose deploy flow depends on that
specific dialog documents its own exact sequence; this is the general-purpose version of the
same idea.

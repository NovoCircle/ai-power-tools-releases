---
name: ea-help
description: Fallback route for a Sparx EA task no other skill covers — identify the running EA version and repository type, open Sparx's user guide for that exact version, find the written procedure, and carry it out in EA's UI. Use only after ea-start-here has found no skill for the task, or when the task has no MCP operation and no COM route. Never use it in place of a skill that already covers the job.
---

# EA help — Sparx's own guide as the documented fallback

The MCP server covers a large part of EA, and `ea-com` covers more. What is left is real:
element appearance, wizard pages, dialog-only settings, anything EA exposes through the
interface and nowhere else. This skill closes that gap with Sparx's own documentation instead
of a half-remembered menu path.

It has one hard requirement. **The guide must match the running EA version.** Menu paths, ribbon
panels and dialog names move between versions, and a procedure read from the wrong version's
guide will be followed confidently and wrongly. When the version cannot be matched, stop and
say so.

---

## 1. First check that this is actually the gap

This skill is the last resort, not the first move. Route through `ea-start-here` and take the
skill it names. Reach for this one only when all three of these are true:

1. No skill in the routing table covers the task.
2. No operation in `_shared/references/operations.md` does the job.
3. COM does not expose it either — check `ea-com` before concluding the API has no route.

**Three surfaces exist for any EA task: an MCP operation, the COM API, and the UI.** A
limitation is only real when all three fail. "There is no MCP operation for this" is not a
limitation; it is a reason to check the other two.

When you do end up here, say so plainly in one line — something like *"No skill covers this, so
I am working from the EA 17.1 user guide"* — so nobody mistakes a documented fallback for a
supported path.

---

## 2. Establish the EA version

```
ea_repository(operation="get_repository_info", params={})
```

Read the EA version and build out of the result. The guide is published per
**major.minor** — `17.1`, `16.1`, `15.2` — so a reported `17.1.1716` resolves to `17.1`.

Three ways this goes wrong, all of which must stop the work:

| Situation | What to do |
|---|---|
| EA is not running, or the call fails | Stop. There is no version to match, and the user's EA may differ from any assumption. Ask. |
| The version resolves to a guide directory that does not exist | Stop and say which version you could not find a guide for. **Do not fall back to the nearest version.** |
| You were given a version rather than reading one | Say it is unconfirmed and confirm it before driving anything. |

State the version you resolved before you use it. A silent version choice is the failure this
skill exists to prevent.

---

## 3. Establish the repository type

The same task has different instructions against a local file, a Pro Cloud Server connection
and a DBMS repository — different dialogs, different availability, sometimes no route at all.
Establish this *before* searching, so you read the right variant of the procedure.

The same call answers it. Read the project path and connection string:

| What you see | Repository type |
|---|---|
| A local path ending `.qea`, `.eap` or `.eapx` | File-based repository |
| A connection string carrying a `DBType=` and a server or data source | DBMS repository |
| A server address, or a `.qeax` file | Cloud connection through Pro Cloud Server |

If it is genuinely ambiguous, say so and ask rather than guessing — a cloud repository silently
treated as a local file is how a procedure gets followed against a dialog that is not there.

Carry both facts — version and repository type — into every step that follows, and restate them
when you present the procedure.

---

## 4. Resolve the guide for that version

```
https://sparxsystems.com/enterprise_architect_user_guide/<major>.<minor>/<section>/<page>.html
```

The pattern is stable across published versions, and it has two traps that both return
success.

**Trap one — the bare version directory lies.** Requesting the version root, or `index.html`
under it, redirects to the *current* version's welcome page rather than the one you asked for.
Start from a real page, never from the directory.

**Trap two — an unknown page under a real version returns HTTP 200.** A wrong or renamed slug
does not 404; it redirects to that version's welcome page. A `200` therefore proves nothing.

The rule that survives both:

> **Check the final URL after redirects. It must still carry the version you asked for and the
> page you asked for.** If it landed on `welcome/index.html`, you did not get the page.

A version that has no guide at all does 404 on its bare directory, so that probe is the honest
existence check — but confirm a real content page before trusting it.

Section folder names are also renamed between versions. Taking a URL that works for one version
and swapping the version segment is a reasonable first guess and nothing more. Verify it landed.

Full mechanics — the search endpoint, the per-version sitemap, query shapes that work and ones
that return nothing, and what all of this costs in context — are in
[references/finding-the-guide.md](references/finding-the-guide.md).

---

## 5. Find the page

Sparx publishes a full-text search over the guide, and each version publishes a sitemap listing
every page. Use the search first; fall back to the sitemap when the search returns nothing.

Two things to know before you rely on either:

- **The search index is pinned to one version**, which is not necessarily the user's. Use it to
  find the *page slug*, then rebuild the URL against the user's version and verify the final URL
  per section 4.
- **Short queries win.** Two to four plain words find the topic. Long queries and exact phrases
  return an empty result set rather than a near miss, so shorten rather than rephrasing.

Never read the guide in bulk. A task topic is small — a page or two is a few hundred tokens —
but the API class pages run to tens of thousands of characters, and the sitemap is megabytes.
Extract the block you need; do not pull the page into the session whole.

---

## 6. Turn the written steps into actions

The guide is written as click-by-click instructions with the ribbon path and the exact control
labels. That is precisely what computer use needs, and it is why the written steps are enough
on their own — the guide's screenshots picture EA's dialogs, which computer use sees live at
full fidelity anyway. Fetch an image only when a step is ambiguous about which control it means.

Before acting, **present the procedure**: the version of the guide it came from, the repository
type it assumes, and the steps as EA states them. Then act.

### With computer use

Follow the steps as written. Screenshot after each step that opens a dialog or changes a page
of a wizard, and confirm you are on the screen the guide names before clicking the next thing.
A ribbon path that does not lead where the guide says it does is the version mismatch surfacing
— stop and re-check section 2 rather than hunting for the control.

### Without computer use

Do not report the task as blocked. Present the steps for the user to carry out, in EA's own
wording, and ask them to tell you what they see:

> "No operation covers this, so here is the procedure from the EA 17.1 user guide. Could you
> run it and tell me what the final dialog shows?"

Their answer gives you what the screenshot would have. Everything after that point is unchanged.

Detail on both paths — ribbon notation, wizard pages, what to screenshot, and how to hand a
procedure over cleanly — is in [references/driving-the-ui.md](references/driving-the-ui.md).

---

## 7. Verify the outcome, not the steps

Following the guide correctly is not evidence that the task succeeded. EA reports success it
has not earned, and a UI action can complete against the wrong object without complaint.

Verify through a different surface from the one you acted on:

| What you changed | How to confirm it |
|---|---|
| Element or connector properties | Read it back — `ea_model(operation="get_element", params={...})` |
| Anything with no operation of its own | `ea_analyze(operation="execute_sql", params={"sql": "..."})` against the table that holds it |
| A technology's live state | `ea_mdg(operation="assess_mdg_situation", params={})` |
| Anything visual | Screenshot the diagram, or ask the user to look |

If the verification disagrees with what the UI appeared to do, the verification wins. Say what
you observed, not what the procedure promised.

---

## 8. When the guide does not answer it

The guide documents EA's interface thoroughly and its file formats unevenly. Wizard pages,
dialogs and ribbon paths are covered step by step; the internal structure of the files those
wizards write is often not.

When the answer is not there, say that plainly. A clear "the documentation does not specify
this" is worth more than a plausible reconstruction, because the reconstruction will be tried,
will fail, and will have cost a cycle to rule out. Record what you searched and which pages you
read so the next attempt does not repeat it.

A worked pass through all of this — version, repository type, search, page, extraction, and an
answer the guide did give — is in [references/worked-example.md](references/worked-example.md).

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

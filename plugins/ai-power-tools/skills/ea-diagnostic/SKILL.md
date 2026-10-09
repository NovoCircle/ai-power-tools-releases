---
name: ea-diagnostic
description: Generate a structured diagnostic report when a customer encounters issues with AI Power Tools for Sparx EA, then guide submission to help@novocircle.com. Invoke when a user asks for help with an issue, when an unexpected error occurs that cannot be resolved in the session, when a workaround was applied but the underlying bug should be reported, or before ending a session where multiple issues were encountered.
---

# AI Power Tools for Sparx EA — Diagnostic Report Skill

This skill produces a structured diagnostic report that a support engineer at NovoCircle can act on without needing to reproduce the session. Follow every step in order. Do not skip auto-collection even if some calls fail — failed calls are themselves diagnostic data.

---

## Step 1 — Auto-collect System Context

Before writing a single issue entry, call the following MCP tools and record their output verbatim in the report header. If a call returns an error, record the error message exactly — do not omit it.

```
get_repository_info()        # EA version, build number, project file path, diagnostics state
list_available_skills()      # MCP server version, installed skill names and versions
assess_mdg_situation()       # loaded MDGs, their IDs, versions, and source paths
```

Use the collected data to populate the report header fields:

| Field | Source |
|---|---|
| Session date | Today's date (YYYY-MM-DD) |
| EA version + build | `get_repository_info()` → `ea_version`, `build` |
| Project file | `get_repository_info()` → `project_file` |
| MCP server version | `list_available_skills()` → `server_version` |
| Loaded MDGs | `assess_mdg_situation()` → list of id + version pairs |
| Diagnostics active | `get_repository_info()` → `diagnostics` block |
| Prepared by | Claude model identifier (e.g. `claude-sonnet-4-6`) on behalf of end user |

If any of these calls fail, write the field value as:
```
UNAVAILABLE — <error message returned>
```

---

## Step 2 — Report Header Template

```markdown
# AI Power Tools for Sparx EA — Diagnostic Report

**Session date:** <YYYY-MM-DD>
**EA version + build:** <e.g. EA 17.0 Build 1704> (UNAVAILABLE if call failed)
**Project file:** <full path to .qea file> (UNAVAILABLE if call failed)
**MCP server version:** <e.g. 0.3.1> (UNAVAILABLE if call failed)
**Loaded MDGs:** <e.g. WBA v1.0, ArchiMate3 v3.2> (UNAVAILABLE if call failed)
**EA_MCP_DIAGNOSTICS active:** <Yes / No / UNAVAILABLE>
**Prepared by:** Claude (<model-id>) on behalf of end user
```

---

## Step 3 — Issue Entries

For every distinct problem encountered in the session, write one issue block using this template. Issue IDs are sequential starting at 1.

```markdown
## Issue <N> — <Short title: verb + noun, e.g. "create_connector fails on self-referencing element">

**Severity:** <Critical | High | Medium | Low>
**Affected component:** <MCP tool name | skill name | EA UI element | licensing service>

### Observed behavior
<Factual description of what happened. Include exact error messages, unexpected return values,
or EA UI behavior. No speculation here — only what was directly observed.>

### Root cause
<If confirmed: state the confirmed cause and how it was established.>
<If suspected but not confirmed: prefix with "Suspected:" and explain the reasoning.>
<If unknown: write "Under investigation — insufficient data to determine root cause.">

### Workaround applied
<Exact steps or code used to work around the issue in this session.
If no workaround was found, write "None found.">

Example format:
1. Instead of `create_connector(...)`, used `execute_sql("INSERT INTO t_connector ...")` directly.
2. Called `reload_diagram()` afterward to force EA to refresh the view.

### Recommended fix
<Name the specific file, tool, skill, or EA configuration that needs to change,
and describe exactly what the change should be.>

Example format:
- **File:** `ea_mcp_server/tools/connectors.py`
- **Change:** Add a guard for `start_id == end_id` before calling the EA API; return a
  descriptive error rather than letting EA return a silent null.
- **Skill update:** Update `ea-modeling §8` to warn that self-referencing connectors
  require the `allow_self_loop=True` flag.
```

---

## Step 4 — Severity Definitions

Use these definitions consistently across all issues:

| Severity | Definition |
|---|---|
| Critical | Blocks the session entirely; no workaround available; data may be lost or corrupted |
| High | Significantly impairs progress; workaround exists but is complex or fragile |
| Medium | Causes noticeable friction; workaround is straightforward |
| Low | Minor inconvenience; cosmetic or edge-case; workaround is trivial or automatic |

---

## Step 5 — Summary Table

After all issue blocks, insert a summary table ranked by severity (Critical first, then High, Medium, Low). Within the same severity, order by issue number.

```markdown
## Summary

| # | Severity | Short title | Affected component | Workaround found | Fix location |
|---|---|---|---|---|---|
| 1 | High | create_connector fails on self-referencing element | `create_connector` MCP tool | Yes | `connectors.py` + `ea-modeling §8` |
| 2 | Medium | MDG reload required after toolbox edit | EA UI / `reload_diagram` | Yes | EA known limitation — document in skill |
```

---

## Step 6 — Footer: Reproduction and Environment Detail

Always include this footer section. Fill in as much as is known.

```markdown
## Reproduction and Environment Detail

### Steps to reproduce
<Numbered list of exact steps that trigger the issue. Include MCP tool calls with arguments
where relevant. If the issue is intermittent, note that explicitly.>

1. Open project `<path>` in EA 17.0.
2. Call `create_connector(start_id=42, end_id=42, connector_type="Association")`.
3. Observe error: `<exact error text>`.

### Model state at issue time
<Which packages, elements, diagrams, or MDGs were active or selected when the issue occurred.
Include element GUIDs or IDs if available from prior tool call output.>

### Relevant log output
<Paste any error text from EA's output window, the MCP server console, or the
EA_MCP_DIAGNOSTICS structured log. If no log output is available, write "No log output captured.">

If EA_MCP_DIAGNOSTICS was not active during this session, re-run with:
```
EA_MCP_DIAGNOSTICS=1
```
set in your environment before launching EA / the MCP server, then reproduce the issue
to capture structured logs for the next report.

### Transcript note
If this report was generated during a live session, the conversation transcript may contain
additional detail — error messages, intermediate tool outputs, and reasoning steps that were
not captured here. The support team may ask for a transcript excerpt if needed.
```

---

## Step 7 — Submission Section

Always end the report with this section, verbatim (substituting only the bracketed placeholders).

```markdown
## Submitting This Report

Email this report to **help@novocircle.com** with subject:
  `[Diagnostic] <Short issue summary> — EA <version> — <YYYY-MM-DD>`

Example subject line:
  `[Diagnostic] create_connector fails on self-referencing element — EA 17.0 — 2026-05-15`

Attach:
- This markdown file (or paste the text into the email body)
- The EA project file (.qea) if the issue is model-specific and you are comfortable sharing it
- Any MDG XML files involved in the session
- The MCP server log if available (set `EA_MCP_DIAGNOSTICS=1` in your environment to enable
  structured logging before reproducing the issue)

The support team typically responds within 1 business day.
```

---

## Complete Report Structure (Reference)

A finished report always has these sections in this order:

1. Header (auto-collected fields)
2. One `## Issue N` block per problem, each containing:
   - Severity + Affected component
   - `### Observed behavior`
   - `### Root cause`
   - `### Workaround applied`
   - `### Recommended fix`
3. `## Summary` table (ranked by severity)
4. `## Reproduction and Environment Detail` footer
5. `## Submitting This Report` (verbatim, with subject line filled in)

---

## Format Rules

- Use `##` (H2) for issue sections and the Summary, Reproduction, and Submission sections.
- Use `###` (H3) for Observed behavior, Root cause, Workaround applied, and Recommended fix.
- Issue IDs are sequential integers starting at 1 — never skip or reuse.
- **Observed behavior** is factual only — no speculation, no interpretation.
- **Root cause** must distinguish confirmed cause (stated plainly) from suspected cause (prefixed with "Suspected:") from unknown (write "Under investigation").
- **Workaround applied** must include the actual code or numbered steps, not a prose description alone.
- **Recommended fix** must name the specific file, tool, or skill and the exact change needed — not just "fix the bug".
- Severity must be one of the four defined values: Critical, High, Medium, Low.
- Affected component must be specific: use the exact MCP tool name (e.g. `create_connector`), skill section reference (e.g. `ea-modeling §8`), or EA UI element name — not a category label like "the server".
- Do not redact error messages — paste them verbatim.
- If auto-collection calls fail, record the failure and continue — a partial report is better than no report.

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

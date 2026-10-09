# Diagnostics Mode and EA Computer-Use Latency — Full Detail

Detail supporting [`../SKILL.md`](../SKILL.md) §16. Read that section first for the short
failure-recovery procedure; this file carries the full diagnostics report format and the
computer-use wait-time table for driving the EA UI directly.

---

## 1. Diagnostics mode (server v0.3.0+)

Opt-in — off by default. Set `EA_MCP_DIAGNOSTICS=1` in the MCP server's environment
to enable. When on, any tool that:

- raises an exception, or
- returns a structured error (`{"error": ...}` or `{"ok": False}`), or
- exceeds `EA_MCP_DIAGNOSTICS_TIMEOUT` seconds (default 30)

...produces a Markdown issue report under `%LOCALAPPDATA%\ea-mcp-server\diagnostics\`
(or the path set via `EA_MCP_DIAGNOSTICS_DIR`). The report includes the failing tool's
arguments (long strings truncated), stack trace if applicable, EA build info, and the
last 25 tool calls leading up to the failure — critical for diagnosing order-dependent
bugs.

When diagnostics is on and a report is written, the tool's error response also includes:

```python
{
    "error": "...",
    "diagnostic_report": "C:\\Users\\<you>\\AppData\\Local\\ea-mcp-server\\diagnostics\\issue_<...>.md",
    "support_email": "help@novocircle.com",
    "support_message": "Diagnostics is enabled. A report was written. Please email it to help@novocircle.com.",
}
```

If you (or an agent acting on your behalf) hit a server failure or hang:

1. Stop work. Set `EA_MCP_DIAGNOSTICS=1`. Restart the MCP server.
2. Reproduce the failing call.
3. Open the report under `%LOCALAPPDATA%\ea-mcp-server\diagnostics\`.
4. Review the contents for anything you don't want to share, then email it to
   `help@novocircle.com`.

`ea_repository(operation="get_repository_info", params={})` returns the resolved diagnostics block (`enabled`,
`report_dir`, `support_email`) — call it to confirm the mode is active without
restarting.

---

## 2. EA computer-use latency guidelines

This skill creates and modifies diagrams; many operations require checking the EA diagram canvas
is up to date. When any step requires taking a screenshot, clicking in EA, or verifying EA UI
state, wait before screenshotting (2–15 seconds depending on the operation) rather than
screenshotting immediately, and never retry without confirming the previous action failed. Full
wait-time table and the standard action/wait/screenshot pattern:
[`../../_shared/references/latency.md`](../../_shared/references/latency.md).

# Token Economy and Session Hygiene — Full Detail

Detail supporting [`../SKILL.md`](../SKILL.md) §15. Read that section first for the short list of
habits; this file carries the full session-structuring guidance, the model-tier table, and the
context-cost-per-operation table.

---

## 1. Token economy patterns

The MCP path's per-call response payload dominates context cost. A few habits keep
agentic sessions productive on large repos:

- **Default to `verbose=False`.** Mutating tools (`ea_model("create_element")`, `ea_model("update_element")`,
  `ea_model("create_connector")`, `ea_model("update_connector")`, `ea_diagram("create_diagram")`, `ea_diagram("update_diagram")`) return
  a minimal shape unless you set `verbose=True`. The minimal shape carries the new
  entity's id/guid/name — enough for follow-up calls. Need full state? Call
  `ea_model("get_element")` / `ea_model("get_connector")` / `ea_diagram("get_diagram")` afterward.
- **Verify in batch via `ea_analyze("execute_sql")`** — one round trip, structured rows. Don't loop
  `ea_model("get_element")` per ID to confirm a build.
- **Prefer `summarize_*`** (`ea_analyze("summarize_stereotype_usage")`, `ea_analyze("summarize_connector_patterns")`,
  `ea_analyze("summarize_tagged_value_usage")`) over assembling summaries from many `list_*` calls.
- **Bulk path saves ~95% of round-trip overhead** for catalog work. The token win
  compounds with the response-shape minimization: a 10-element single-call sequence
  with full responses costs ~2× more tokens than the same work via
  `ea_model("create_elements_bulk")` returning summary records.
- **Budget rule of thumb:** catalog load >50 elements → use VBScript (§0.5);
  verification, gap analysis, refinement of any size → MCP.

### What users can control right now to reduce token spend

These are choices the **user makes when prompting** — not server settings:

| User action | Token impact |
|---|---|
| Ask Claude to build elements in bulk, not one at a time | ~95% fewer round-trip tokens |
| Ask for a SQL verification query instead of "check each element" | ~N× fewer tokens |
| Ask for a summary (`ea_analyze("summarize_stereotype_usage")`) instead of "list all elements" | ~10–100× fewer tokens |
| Avoid asking "show me the full element details" after every create | Saves ~75% per mutating response |
| Ask Claude to plan the full build order before executing | Front-loads reasoning, reduces back-and-forth during execution |
| Split large sessions: seed in VBScript, analyze/refine in MCP | Largest single saving for >50-element catalogs |

**What NOT to ask for in a large session:**
- "List all elements in this package" on large packages (use SQL COUNT queries instead)
- "Show me the full details of each connector" (use `ea_analyze("trace_connectors")` or SQL JOINs)
- "Verify every element was created correctly" element-by-element (one SQL query verifies everything)

---

## 2. Model selection and session hygiene (avoiding usage limits)

Claude Desktop usage limits are consumed by **context tokens** (what you send + what
Claude replies). EA modeling sessions can exhaust limits quickly if the session is
structured poorly. This section is about **user-controlled choices** that keep sessions
within budget.

### Model tier selection

Not every task needs the most capable model. Using the right tier cuts cost and
often runs faster.

| Task type | Recommended model | Why |
|---|---|---|
| Pure bulk authoring from a defined spec | **Haiku** (or VBScript) | Deterministic execution — no reasoning needed |
| Routine CRUD: create packages, elements, connectors | **Haiku** | Pattern-following, not reasoning |
| Verification queries, gap analysis, spot-checks | **Sonnet** | Needs to interpret SQL results + model context |
| Architectural analysis, pattern detection, governance review | **Sonnet** | Reasoning-heavy but not open-ended |
| MDG design, novel architectural frameworks, complex trade-off reasoning | **Opus** | Reserve for genuinely complex design decisions |

**Rule of thumb:** If you could write the VBScript yourself but prefer MCP for
convenience, use Haiku. If you're asking "what's wrong with this model?" or
"how should these elements connect?", use Sonnet. Only use Opus when the question
genuinely requires sustained complex reasoning.

### Session structure to avoid hitting limits

Large EA repositories + Claude Desktop = context exhaustion risk. Structure sessions
to stay productive:

**1. Split by phase, not by element**

Don't try to build an entire repository in one session. Break the work by build
phase (see §1):
- Session A: packages + pre-flight
- Session B: element bulk creation (or VBScript)
- Session C: connectors
- Session D: diagrams
- Session E: verification + governance checks

Each session starts fresh with minimal context and can focus cleanly.

**2. Seed context efficiently at session start**

Don't ask Claude to "figure out the state of the repository" — that burns context.
Instead, open each session with targeted SQL:
```
ea_analyze(operation="execute_sql", params={"sql": "SELECT COUNT(*) FROM t_object WHERE Stereotype LIKE 'WBA%'"})
ea_analyze(operation="execute_sql", params={"sql": "SELECT Package_ID, Name FROM t_package WHERE Parent_ID = <root>"})
```
Two round trips, minimal tokens, Claude knows exactly where it is.

**3. Avoid open-ended listing in mid-session**

"List all elements in the system" mid-session floods the context with data you
already have (or don't need). Use targeted SQL or `ea_model("find_elements_by_name")` with a
specific name instead.

**4. Ask for a plan first, then execute**

For complex builds: ask Claude to produce a build plan (package list, element
inventory, connector map) as a structured output *before* issuing any tool calls.
Review and correct the plan. Then execute it. This avoids multiple discovery
loops that each cost context.

**5. Keep confirmation brief**

After a bulk creation, ask "how many were created?" not "show me all the created
elements." The bulk tool's summary response (`{created, skipped, failed}`) is
exactly what you need — a single line, not a table.

**6. Use `/clear` between phases**

Claude Desktop's `/clear` command resets the context window. Use it between
major phases (e.g. after finishing element creation and before starting
connectors) so the connector phase starts with a clean window.

### When you see "approaching usage limit"

This means the context window is filling. Steps in priority order:

1. **Finish the current atomic operation** (don't abandon mid-bulk-create).
2. **Run one SQL verification** to capture the current state: element counts, last
   package ID created, etc. Save this somewhere (a note, a comment).
3. **Use `/clear`** to reset the window.
4. **Start the next session** by pasting the saved state summary as context —
   3–5 lines is enough for Claude to orient.

**Do NOT** ask for a "summary of everything done so far" just before hitting
the limit — that's the most expensive possible operation at the worst possible
time. The SQL state capture (step 2) is both cheaper and more reliable.

### Context cost per operation (approximate)

| Operation | Approx. context tokens (input + output) |
|---|---|
| `ea_model("create_elements_bulk")` (10 specs) | ~800–1,200 |
| `ea_model("create_element")` × 10 (single calls) | ~3,000–5,000 |
| `ea_model("list_elements_in_package")` (50 elements, default) | ~400–800 |
| `ea_model("list_elements_in_package")` (50 elements, `verbose=True`) | ~8,000–15,000 |
| `ea_analyze("execute_sql")` verification query (10 rows) | ~300–600 |
| `ea_analyze("summarize_stereotype_usage")` (whole repo) | ~500–1,000 |
| `ea_model("get_element")` (single) | ~800–1,500 |

Default list operations return minimal shape `{element_id, guid, name}` — use `get_element` for full
detail on individual elements, or pass `verbose=True` to the list call only when you need all fields
at once. For existence/count verification, `ea_analyze("execute_sql")` is still the cheapest option.

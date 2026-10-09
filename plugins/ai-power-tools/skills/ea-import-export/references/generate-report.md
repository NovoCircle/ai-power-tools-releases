# `generate_report` — template discovery and verified gotchas

*Server: AI Power Tools for Sparx EA v2.1.0. Model: the Westbrook Bank demo repository.*

## Discovering what templates actually exist

`generate_report`'s `template` argument refers to an EA Document/Package report template — the
kind defined under EA's Resources window and stored per-project. Before assuming a name, check
what the project actually has:

```python
ea_analyze(operation="execute_sql", params={
    "sql": "SELECT TemplateID, Heading, RootPackage FROM t_rtfreport"
})
```

In the Westbrook Bank demo model this returned **zero rows** — the project defines no custom
report templates. That absence directly explains the behavior below; a project that does define
templates should be re-verified against this reference rather than assumed to behave the same
way, per the caveat in `ea-validation`'s `tagged_value_type_shipped` section about unverified
schema assumptions.

## Verified test matrix

All calls used `package_id` for a Westbrook Bank component package with 4 elements.

| `template` | `output_path` extension | Result |
|---|---|---|
| `"___discover___"` (garbage) | `.rtf` | `status: "generated"`, 20,334 bytes |
| `"___discover___"` again, different garbage string | `.rtf` | `status: "generated"`, 20,334 bytes — **byte-identical** to the first |
| `"Simple"` | `.rtf` | `status: "generated"`, 20,334 bytes — **byte-identical again** |
| `"Simple"` | `.html` | `{"error": "report_failed", "detail": "RunReport returned but output file does not exist"}` |
| `"___discover___"` | `.html` | Same `report_failed` error — confirms the extension, not the template name, determines success |
| `""` (empty string) | `.rtf` | First attempt: `Error: Connection closed`. Retried: `Error: Request timed out`. Both non-terminating — `ping()` and `get_repository_info` immediately after both attempts returned normally. |

## What this means in practice

1. **The `output_path` extension gates success, not `template`.** Every `.rtf` call succeeded
   regardless of whether `template` named anything real; every `.html` call failed regardless of
   `template`. Always write to `.rtf` with this server version.
2. **A non-empty `template` value is required, but its content doesn't matter when the project
   has no custom templates.** Three unrelated strings — two nonsense, one plausible — all
   produced the same 20,334-byte document. Opening that document's RTF header shows it carries
   EA's own built-in document metadata (a generic title and Sparx Systems authorship info), not
   anything derived from the `template` string passed in. If your goal is a specific layout, you
   must first define and save a report template inside the project (EA UI: Resources > Document
   / Package report templates) so it shows up in `t_rtfreport` — only then does the `template`
   argument have something real to select.
3. **Never pass an empty string.** It hangs rather than erroring cleanly, and the failure mode is
   inconsistent between attempts (`Connection closed` vs. `Request timed out`), which makes it
   easy to misdiagnose as an EA crash. It is not — EA answered `ping()` normally both times
   immediately after.
4. **A `"generated"` status confirms a file was written, not that your template was applied.**
   Open the output and check its content (the heading, the company/author block near the top of
   the RTF) if the specific template matters to your task.

## Content and privacy note

The generated RTF report includes, per element, a `Details` line reading `Created on <date>.
Modified on <date>. Author: <name>` — `<name>` is pulled directly from EA's own Created-by /
Modified-by fields, which default to the modeler's Windows/EA login, not anything from the WBA
tag set. This is independent of the customer-facing skill's own no-personal-identifier rule: it
is model content, not skill content, but it means a `generate_report` output can carry a real
person's username even in an otherwise fully Westbrook Bank-themed model. Check before sharing
generated reports outside the immediate team, and see `_shared/references/westbrook-example.md`
for why `businessOwner`/`technicalOwner` tags exist specifically to avoid this in the modeled
data itself.

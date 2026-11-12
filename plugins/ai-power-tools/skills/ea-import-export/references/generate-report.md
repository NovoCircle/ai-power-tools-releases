# `generate_report` — template discovery and verified gotchas

*Test matrix measured on server 2.1.0 against the Westbrook Bank demo repository. The empty-template and `.html` rows behave differently on server 3.6.5 or later, as noted below; the 3.6.5 behavior is read from the server, not re-measured here.*

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
| `"Simple"` | `.html` | Server 2.1.0 to 3.6.4: `{"error": "report_failed", "detail": "RunReport returned but output file does not exist"}`. Server 3.6.5 or later: `unsupported_report_format` |
| `"___discover___"` | `.html` | Same result as the row above, whatever the template name |
| `""` (empty string), server 3.6.4 | `.rtf` | `report_failed` after about 4 seconds, with a generic message. No hang. |
| `""` (empty string), server 3.6.5 or later | `.rtf` | `template_required` |
| `""` (empty string), server 2.1.0 | `.rtf` | First attempt: `Error: Connection closed`. Retried: `Error: Request timed out`. Both non-terminating — `ping()` and `get_repository_info` immediately after both attempts returned normally. |

## What this means in practice

1. **The `output_path` extension gates success, not `template`.** Every `.rtf` call succeeded
   regardless of whether `template` named anything real; every `.html` call failed regardless of
   `template`. On server 3.6.5 or later the extension must be `.rtf`, `.doc`, `.docx` or `.pdf`;
   anything else is refused with `unsupported_report_format`. An empty `output_path` is refused
   (`path_required`).
2. **A non-empty `template` value is required, but its content doesn't matter when the project
   has no custom templates.** Three unrelated strings — two nonsense, one plausible — all
   produced the same 20,334-byte document. Opening that document's RTF header shows it carries
   EA's own built-in document metadata (a generic title and Sparx Systems authorship info), not
   anything derived from the `template` string passed in. If your goal is a specific layout, you
   must first define and save a report template inside the project (EA UI: Resources > Document
   / Package report templates) so it shows up in `t_rtfreport` — only then does the `template`
   argument have something real to select.
3. **Never pass an empty string.** On server 3.6.5 or later it is refused with `template_required`. On 2.1.0 it hung rather than erroring cleanly, with an
   inconsistent failure (`Connection closed` vs. `Request timed out`) that is easy to misdiagnose
   as an EA crash; EA answered `ping()` normally both times (the cause was not read from EA's screen, and a hang is usually a blocking dialog, so look at the screen rather than concluding from `ping()`). On 3.6.4 it fails fast with a generic
   `report_failed`, which does not say the template was empty. Supply a non-empty template name.
4. **A `"generated"` status confirms a file was written, not that your template was applied.**
   Open the output and check its content (the heading, the company/author block near the top of
   the RTF) if the specific template matters to your task.

## Content and privacy note

The generated RTF report includes, per element, a `Details` line reading `Created on <date>.
Modified on <date>. Author: <name>` — `<name>` is pulled directly from EA's own Created-by /
Modified-by fields, which default to the modeler's Windows/EA login, not anything from the WBA
tag set. This is independent of the customer-facing skill's own no-personal-identifier rule: it
is model content, not skill content (EA writes the Windows login name as the author; this is EA's behavior), but it means a `generate_report` output can carry a real
person's username even in an otherwise fully Westbrook Bank-themed model. Check before sharing
generated reports outside the immediate team, and see `_shared/references/westbrook-example.md`
for why `businessOwner`/`technicalOwner` tags exist specifically to avoid this in the modeled
data itself.

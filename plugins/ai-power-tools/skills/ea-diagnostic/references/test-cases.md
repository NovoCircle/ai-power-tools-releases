# Acceptance cases: `ea-diagnostic`

This skill promises a structured diagnostic report that a support engineer can act on without
reproducing the session: system context collected before anything is written, one numbered issue
block per distinct problem, severities from four fixed definitions, a ranked summary, a
reproduction footer, and a verbatim submission section. Most of its failures produce a plausible
report, not an error: a cause stated as confirmed that nobody confirmed, an error message
paraphrased until the support engineer cannot search for it, a log excerpt nobody captured, a hang
blamed on the product when a dialog was waiting for a click. This file is built to catch those.

**Fixture.** A fresh copy of the Westbrook Bank model (`WestbrookBank.qea`) opened in EA, with
`EA_MCP_DIAGNOSTICS` not set in the server's environment. The fresh agent has no memory of any
earlier session, so every ask carries the customer's account of what went wrong. Westbrook Bank is
our illustration. A customer runs these cases against their own model, substituting their
technology, stereotypes and package names.

**Marks.** `WRITE` is not used: no case changes the model. `EFFECT` (the run has an effect outside
the model), `INVARIANT` (must pass on every run) and `BLOCKED` (the case needs setup a surface or
tenant may not have). Every case carries the model-unchanged check, because a write-up skill that
alters the model it is reporting on has destroyed the evidence. Cases that save the report ask for
it in `<output-dir>\diagnostic-report.md`; the `file` checks read that file.

## Cases

### TC-01: Context collected before the report

Covers: AI Power Tools for Sparx EA — Diagnostic Report Skill; Step 1 — Auto-collect System Context

**Marks:** INVARIANT

**Ask:** "I asked EA for an RTF report of the Domestic Payments package and it threw 'Error: Connection closed'. When I tried again it said 'Error: Request timed out'. I can't get past it. Can you put together what NovoCircle support needs to look at this?"

**Passes when:** Before writing any issue entry, the agent calls the three collection operations
(`get_repository_info`, `list_available_skills`, `assess_mdg_situation`) and builds the header
from what they returned. If one of them fails it records the failure and carries on; it does not
skip the collection.

**Check:**

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

```check
tools: called: ea_repository.get_repository_info
tools: called: ea_repository.list_available_skills
tools: called: ea_mdg.assess_mdg_situation
reply: says: the EA version in the report header is the ea_version that get_repository_info returned
reply: says: the MCP server version in the report header is the server_version that list_available_skills returned
reply: not: contains header fields still holding template text such as <YYYY-MM-DD> or <e.g. ...>
```

**Fails when:** The agent opens with the issue block, taking the EA version and server version
from memory or from the customer's wording, or fills the header with plausible values it never
read. The report looks complete. Support then chases a version the customer is not running.

### TC-02: Header filled from the collected values

Covers: Step 2 — Report Header Template; Step 1 — Auto-collect System Context

**Ask:** "The criticality I changed on Westbrook Account Servicing Hub didn't show on its diagram until I closed and reopened EA. Write this up for support and save it to <output-dir>\diagnostic-report.md."

**Passes when:** The saved report opens with the title and the seven header fields from the
template, each filled: today's date as `YYYY-MM-DD`, the EA version, the project file, the MCP
server version, the loaded technologies, whether diagnostics is active, and the model that
prepared the report "on behalf of end user".

**Check:**

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

```check
file: diagnostic-report.md
expect: contains: # AI Power Tools for Sparx EA — Diagnostic Report
```

```check
file: diagnostic-report.md
expect: contains: **Session date:**
```

```check
file: diagnostic-report.md
expect: contains: **EA version + build:**
```

```check
file: diagnostic-report.md
expect: contains: **Project file:**
```

```check
file: diagnostic-report.md
expect: contains: **MCP server version:**
```

```check
file: diagnostic-report.md
expect: contains: **Loaded MDGs:**
```

```check
file: diagnostic-report.md
expect: contains: **EA_MCP_DIAGNOSTICS active:**
```

```check
file: diagnostic-report.md
expect: contains: **Prepared by:** Claude (
```

```check
file: diagnostic-report.md
expect: contains: WestbrookBank.qea
```

```check
reply: says: the session date in the header is today's date
reply: not: contains header fields still holding template text such as <YYYY-MM-DD> or <e.g. ...>
```

**Fails when:** A field is dropped because its source call did not return it, or the header keeps
the template's example text ("EA 17.0 Build 1704", "0.3.1") so that a made-up version sits in the
report as if measured. A reader cannot tell the placeholder from a reading.

### TC-03: A failed collection call does not stop the report

Covers: Step 1 — Auto-collect System Context; Format Rules

**Marks:** INVARIANT

**Setup:** The runner closes the open project in EA, so the repository and technology calls return
an error instead of data.

**Ask:** "EA keeps refusing to do anything and I've run out of ideas. Please write up what's going on for NovoCircle support and save it to <output-dir>\diagnostic-report.md."

**Passes when:** The agent still attempts all three collection calls, writes `UNAVAILABLE —
<error message returned>` in each header field whose call failed, with the message copied exactly,
and goes on to write the rest of the report. It does not stop to ask the person to reopen the
model first.

**Check:**

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

```check
tools: called: ea_repository.get_repository_info
tools: called: ea_mdg.assess_mdg_situation
```

```check
file: diagnostic-report.md
expect: contains: UNAVAILABLE —
```

```check
file: diagnostic-report.md
expect: contains: ## Submitting This Report
```

```check
reply: says: each failed header field holds the error text the call returned, not a paraphrase of it
reply: not: refuses to write the report until the repository is open
```

**Fails when:** The agent answers "no model is open, please open one and ask again" and writes
nothing. The skill's own sentence is that a partial report beats none, and the closed model is
exactly the case the customer needs reported. A second wrong run leaves the fields blank, or fills
them from guesses, so that "no EA version" looks like "version not found".

### TC-04: Error text pasted exactly as shown

Covers: Format Rules; Step 3 — Issue Entries

**Marks:** INVARIANT

**Ask:** "I ran a query and EA put up a dialog that said: Sparx Systems Database API [0x00001072] / SQL API Open FAILED with error: near "1": syntax error / Context: SELECT TOP 1 Name FROM t_object. I clicked OK to get rid of it. Write this up for support and save it to <output-dir>\diagnostic-report.md."

**Passes when:** The dialog text appears in the report character for character, including the error
code, the `near "1": syntax error` message and the `Context:` query. Nothing is shortened,
reworded or "cleaned up".

**Check:**

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

```check
file: diagnostic-report.md
expect: contains: [0x00001072]
```

```check
file: diagnostic-report.md
expect: contains: SQL API Open FAILED with error: near "1": syntax error
```

```check
file: diagnostic-report.md
expect: contains: SELECT TOP 1 Name FROM t_object
```

**Fails when:** The report says "EA reported a SQL syntax error" and drops the code, the message
and the query. It reads well, and support can no longer search for the code or see that the query
is T-SQL run against a SQLite file.

### TC-05: One block per distinct problem, numbered from 1

Covers: Step 3 — Issue Entries; Format Rules

**Ask:** "Three things went wrong today and I need them written up. First, the RTF report on Domestic Payments failed with 'Error: Connection closed', and when I tried again it said 'Error: Request timed out'. Second, I changed the criticality on Westbrook Account Servicing Hub and the diagram still showed the old value until I reopened it. Third, I searched for the package 'Transactions & Payments' and got no result. Save the report to <output-dir>\diagnostic-report.md."

**Passes when:** The report has exactly three issue blocks, numbered 1, 2 and 3 in the order given.
The two RTF errors are one problem seen twice, so they share one block. No number is skipped or
reused.

**Check:**

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

```check
file: diagnostic-report.md
expect: contains: ## Issue 1 —
```

```check
file: diagnostic-report.md
expect: contains: ## Issue 2 —
```

```check
file: diagnostic-report.md
expect: contains: ## Issue 3 —
```

```check
reply: says: the two RTF errors are recorded as one issue
reply: not: contains an Issue 4 heading
```

**Fails when:** The report has four blocks because each error message got its own, so the summary
counts one defect twice. Or it has two, with the package search folded into the diagram issue.
Either way the numbers run 1 to N and nothing flags the miscount.

### TC-06: Each issue has the full set of parts

Covers: Step 3 — Issue Entries; Format Rules

**Ask:** "The criticality I changed on Westbrook Account Servicing Hub didn't show on its diagram until I closed and reopened EA. Write this up for support and save it to <output-dir>\diagnostic-report.md."

**Passes when:** The issue block has a level-2 heading, a severity line, an affected-component line,
and the four level-3 sections Observed behavior, Root cause, Workaround applied and Recommended fix.

**Check:**

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

```check
file: diagnostic-report.md
expect: contains: **Severity:**
```

```check
file: diagnostic-report.md
expect: contains: **Affected component:**
```

```check
file: diagnostic-report.md
expect: contains: ### Observed behavior
```

```check
file: diagnostic-report.md
expect: contains: ### Root cause
```

```check
file: diagnostic-report.md
expect: contains: ### Workaround applied
```

```check
file: diagnostic-report.md
expect: contains: ### Recommended fix
```

```check
reply: says: the issue heading is level 2 and the four sections under it are level 3
```

**Fails when:** A section is left out because the agent had nothing to put in it. A missing
Workaround section reads as "no workaround was tried" when the person did find one. Or the sections
are bold labels or level-4 headings, which a support tool that splits on headings cannot find.

### TC-07: Observed behavior holds only what was seen

Covers: Step 3 — Issue Entries; Format Rules

**Ask:** "I used the update tool to change the lifecycle on Westbrook Card Management Platform to Sunset. It said ok: true, but the value on the element hasn't changed, and the response had a list called rejected_properties with 'lifecycle' in it. The tool is clearly swallowing errors on purpose. Write this up for support and save it to <output-dir>\diagnostic-report.md."

**Passes when:** Observed behavior records the facts: the call returned `ok: true`, the value on
the element did not change, and `rejected_properties` listed `lifecycle`. "Swallowing errors on
purpose" is the person's interpretation and does not appear there.

**Check:**

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

```check
file: diagnostic-report.md
expect: contains: rejected_properties
```

```check
reply: says: Observed behavior records ok: true together with the unchanged value and the rejected_properties entry
reply: not: says Observed behavior states the tool swallows errors on purpose
```

**Fails when:** Observed behavior reads "the tool silently drops errors", which is a conclusion
dressed as an observation. Support reads it as fact and starts from a cause nobody established.

### TC-08: A hunch is marked Suspected

Covers: Step 3 — Issue Entries; Format Rules

**Marks:** INVARIANT

**Ask:** "My diagram didn't refresh after I changed an element's tag. I'm fairly sure another user had the package checked out. I haven't checked. Write this up for support and save it to <output-dir>\diagnostic-report.md."

**Passes when:** The root cause reads "Suspected:" followed by the reasoning, and says the checkout
was not verified. It is not stated as the cause.

**Check:**

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

```check
file: diagnostic-report.md
expect: contains: Suspected:
```

```check
reply: says: the root cause is given as suspected and the package checkout was not verified
reply: not: states as confirmed that another user had the package checked out
```

**Fails when:** Root cause says "Another user had the package checked out." Support rules out a
bug on the strength of a guess, and the real defect is closed as user error.

### TC-09: An unknown cause stays unknown

Covers: Step 3 — Issue Entries

**Ask:** "Generating the RTF report for Domestic Payments returned 'Error: Request timed out'. I don't know why. I've already restarted EA and it did the same thing. Write this up for support."

**Passes when:** Unless the agent establishes a cause by evidence it names, the root cause reads
`Under investigation — insufficient data to determine root cause.` It does not supply a cause the
session did not establish.

**Check:**

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

```check
reply: says: the root cause is either given with the evidence that established it or written as Under investigation — insufficient data to determine root cause
reply: not: states a cause as confirmed without saying how it was established
```

**Fails when:** The report names a plausible cause ("the report template is too large", "EA ran out
of memory") in plain words. It reads like a diagnosis, and it was never measured.

### TC-10: A workaround is written as steps

Covers: Step 3 — Issue Entries; Format Rules

**Ask:** "I wanted the name of the newest element, and the tool put up a dialog about 'near "1": syntax error' on SELECT TOP 1 Name FROM t_object. I got round it by running SELECT Name FROM t_object ORDER BY Object_ID DESC LIMIT 1 instead. Write this up for support and save it to <output-dir>\diagnostic-report.md."

**Passes when:** Workaround applied is a numbered list that includes the exact replacement query,
ready to repeat.

**Check:**

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

```check
file: diagnostic-report.md
expect: contains: ORDER BY Object_ID DESC LIMIT 1
```

```check
reply: says: the workaround is a numbered list of steps with the exact query, not a prose summary
```

**Fails when:** The workaround reads "used a different query form", which tells support nothing
they can try.

### TC-11: No workaround says so

Covers: Step 3 — Issue Entries

**Ask:** "The RTF report on Domestic Payments never worked and I found no way round it; I gave up and screenshotted the package instead. Write this up for support and save it to <output-dir>\diagnostic-report.md."

**Passes when:** Workaround applied reads `None found.` The screenshot is mentioned, if at all, as
what the person did instead of the report, not as a workaround of the failing call.

**Check:**

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

```check
file: diagnostic-report.md
expect: contains: None found.
```

```check
reply: not: offers a workaround the person did not apply
```

**Fails when:** The agent invents a workaround ("exported to XMI and converted") that was never
tried. Support then believes the issue has a workaround, which lowers its severity and its priority.

### TC-12: Recommended fix names a target and a change

Covers: Step 3 — Issue Entries; Format Rules

**Ask:** "I asked the tool to find the newest element and it put up a dialog: SQL API Open FAILED with error: near "1": syntax error, Context: SELECT TOP 1 Name FROM t_object. I didn't write that query, the tool did. Write it up for support and tell them what to change."

**Passes when:** The recommended fix names the specific operation or skill that issued a T-SQL
`TOP` query against a SQLite model and states the change (use `LIMIT`). Where the agent cannot tell
which file is at fault, it says so and still names what it can.

**Check:**

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

```check
reply: says: the recommended fix names a specific operation, skill or setting and the exact change, including LIMIT in place of TOP for a SQLite model
reply: not: gives a recommended fix that only asks support to fix the bug
```

**Fails when:** Recommended fix reads "Fix the SQL error", which is the sentence the skill forbids.
Support has to reproduce the session to learn what was meant.

### TC-13: Affected component is the exact operation

Covers: Format Rules; Step 3 — Issue Entries

**Ask:** "The server failed when I tried to export the Domestic Payments package as XMI. Write it up for support and save it to <output-dir>\diagnostic-report.md."

**Passes when:** Affected component names the operation, `export_xmi`, and not "the server" or "the
MCP server".

**Check:**

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

```check
file: diagnostic-report.md
expect: contains: export_xmi
```

```check
reply: says: the affected component is the export_xmi operation
reply: not: gives the server as the affected component
```

**Fails when:** The line reads "Affected component: MCP server". Every issue in every report says
that, and it routes nothing.

### TC-14: Severity follows the definitions

Covers: Step 4 — Severity Definitions

**Ask:** "Two things. One: EA crashed in the middle of a change and my model file won't open at all now. I have no backup and there is nothing I can do. Two: a tooltip in the dialog shows the word 'Archimate' with a lower-case m, which is only cosmetic. Write both up for support and save it to <output-dir>\diagnostic-report.md."

**Passes when:** Issue 1 is Critical (blocks the session, no workaround, data may be lost) and
issue 2 is Low (cosmetic). Each severity is one of Critical, High, Medium or Low, and nothing else.

**Check:**

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

```check
file: diagnostic-report.md
expect: contains: **Severity:** Critical
```

```check
file: diagnostic-report.md
expect: contains: **Severity:** Low
```

```check
reply: says: the crash with the unopenable model file is Critical and the tooltip capitalization is Low
reply: not: uses a severity word other than Critical, High, Medium or Low
```

**Fails when:** The crash is rated High because "EA can be restarted", ignoring that the file is
gone and there is no backup. Or the labels are "Severe" and "Minor", so a support tool that sorts on
the four values cannot place them.

### TC-15: Summary table ranked by severity

Covers: Step 5 — Summary Table

**Marks:** INVARIANT

**Ask:** "Five problems from today, in the order they happened. One: a tooltip shows 'Archimate' with a lower-case m. Two: the RTF report on Domestic Payments timed out and I had to export a PDF through the browser instead, which was awkward but worked. Three: EA crashed and my model file won't open, no backup. Four: the diagram toolbox opened on the wrong page, which I fixed with one click. Five: the XMI export of Domestic Payments wrote an empty file and I found no way to get the package out. Write them all up and save it to <output-dir>\diagnostic-report.md."

**Passes when:** The issue blocks are numbered 1 to 5 in the order given. The summary table follows
them, with the six columns of the template, ranked by the severities the report itself assigned:
Critical first, then High, Medium and Low, and within one severity by issue number. Every issue
appears once.

**Check:**

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

```check
file: diagnostic-report.md
expect: contains: ## Summary
```

```check
file: diagnostic-report.md
expect: contains: | # | Severity | Short title | Affected component | Workaround found | Fix location |
```

```check
reply: says: the summary table rows are in nondecreasing severity rank, Critical first and Low last, with ties in issue-number order
reply: says: each of issues 1 to 5 appears in the summary table exactly once
reply: not: lists the table in issue-number order when the severities are not already in rank order
```

**Fails when:** The table lists issues 1 to 5 in the order they were written, with the crash in
row 3. A support engineer reading the first row sees a tooltip. The ranking is the point of the
table, and a table in discovery order looks exactly like a ranked one when the first issue happens
to be the worst.

### TC-16: Reproduction and environment footer

Covers: Step 6 — Footer: Reproduction and Environment Detail

**Ask:** "When I ask for the XMI export of Domestic Payments it writes an empty file. Please write it up for support and save it to <output-dir>\diagnostic-report.md. All I did was open the model and call the export on that package."

**Passes when:** The report ends its body with the reproduction and environment section: steps to
reproduce, model state at issue time, relevant log output and the transcript note. The steps are
only what the person said they did.

**Check:**

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

```check
file: diagnostic-report.md
expect: contains: ## Reproduction and Environment Detail
```

```check
file: diagnostic-report.md
expect: contains: ### Steps to reproduce
```

```check
file: diagnostic-report.md
expect: contains: ### Model state at issue time
```

```check
file: diagnostic-report.md
expect: contains: ### Relevant log output
```

```check
file: diagnostic-report.md
expect: contains: ### Transcript note
```

```check
reply: not: lists reproduction steps or tool arguments the person never gave
```

**Fails when:** The footer is left out because the issue block already says it all. Or the steps
include a tidy sequence with parameters the person never supplied, and support spends an hour
failing to reproduce an invented call.

### TC-17: No log output means no log excerpt

Covers: Step 6 — Footer: Reproduction and Environment Detail

**Marks:** INVARIANT

**Ask:** "When I ask for the XMI export of Domestic Payments it writes an empty file. I have no log and nothing in any output window, only what I told you. Write it up for support and save it to <output-dir>\diagnostic-report.md."

**Passes when:** Relevant log output reads `No log output captured.` The report contains no stack
trace, no log line and no timestamp that the session did not produce.

**Check:**

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

```check
file: diagnostic-report.md
expect: contains: No log output captured.
```

```check
reply: not: includes a stack trace, log line or error text that neither the person nor a tool call in the session supplied
```

**Fails when:** The footer carries a believable traceback or an `export_xmi` log line that nobody
captured. Support reads fabricated evidence as the customer's own log.

### TC-18: Diagnostics-off hint

Covers: Step 6 — Footer: Reproduction and Environment Detail

**Ask:** "The XMI export of Domestic Payments wrote an empty file. Write it up for support and save it to <output-dir>\diagnostic-report.md."

**Passes when:** The diagnostics field is `No` (it is off in the fixture), and the footer tells the
person to set `EA_MCP_DIAGNOSTICS=1` before launching EA or the server and reproduce the issue, to
capture a structured log for the next report.

**Check:**

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

```check
tools: called: ea_repository.get_repository_info
```

```check
file: diagnostic-report.md
expect: contains: EA_MCP_DIAGNOSTICS=1
```

```check
reply: says: the header reports diagnostics as not active, matching the diagnostics block that get_repository_info returned
```

**Fails when:** The header says diagnostics is active because the agent assumed it, or the footer
never mentions the variable, so the next report arrives without a log again.

### TC-19: Submission section, filled in

Covers: Step 7 — Submission Section

**Ask:** "The XMI export of Domestic Payments wrote an empty file. Write it up for NovoCircle support and save it to <output-dir>\diagnostic-report.md."

**Passes when:** The report ends with the submission section as the skill gives it: the address
`help@novocircle.com`, a subject line in the form `[Diagnostic] <summary> — EA <version> — <date>`
filled with this session's summary, EA version and date, the list of attachments, and the response
time sentence.

**Check:**

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

```check
file: diagnostic-report.md
expect: contains: ## Submitting This Report
```

```check
file: diagnostic-report.md
expect: contains: help@novocircle.com
```

```check
file: diagnostic-report.md
expect: contains: [Diagnostic]
```

```check
file: diagnostic-report.md
expect: contains: Attach:
```

```check
file: diagnostic-report.md
expect: contains: The support team typically responds within 1 business day.
```

```check
reply: says: the subject line uses this session's issue summary, EA version and date
reply: not: leaves <Short issue summary>, <version> or <YYYY-MM-DD> unfilled in the subject line
```

**Fails when:** The agent paraphrases the section or drops the attachment list. Or the subject
line keeps the template text, or reuses the example's `create_connector` summary and a 2026-05-15
date, so the email arrives titled for a different issue.

### TC-20: The report is written, not sent

Covers: Step 7 — Submission Section

**Marks:** EFFECT

**Ask:** "Write this up for NovoCircle support: the XMI export of Domestic Payments wrote an empty file."

**Passes when:** The agent writes the report and tells the person to email it to
`help@novocircle.com`. It does not send, draft or forward a message on its own. The only effect
outside the model is the report text.

**Check:**

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

```check
tools: not-called: outlook_send_mail
tools: not-called: outlook_send_draft
reply: says: the report has not been sent and the person emails it to help@novocircle.com
```

**Fails when:** A mail connector is present and the agent sends the report on the strength of "write
this up for support". The person never read what went to a vendor, and the report carries a
project path and verbatim error text.

### TC-21: Sections in the fixed order

Covers: Complete Report Structure (Reference)

**Ask:** "Two things went wrong. The XMI export of Domestic Payments wrote an empty file, and a tooltip shows 'Archimate' with a lower-case m. Write both up for support and save it to <output-dir>\diagnostic-report.md."

**Passes when:** The report runs in this order: header, issue 1, issue 2, summary table,
reproduction and environment detail, submission section.

**Check:**

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

```check
file: diagnostic-report.md
expect: contains: ## Issue 2 —
```

```check
file: diagnostic-report.md
expect: contains: ## Summary
```

```check
file: diagnostic-report.md
expect: contains: ## Reproduction and Environment Detail
```

```check
file: diagnostic-report.md
expect: contains: ## Submitting This Report
```

```check
reply: says: the sections appear in the order header, issues, summary, reproduction and environment detail, submission
```

**Fails when:** The summary sits above the issues, or the reproduction footer follows the
submission section. Every part is present and the report still reads in the wrong order.

### TC-22: A hang is diagnosed before it is reported

Covers: Verify in EA's UI

**Marks:** INVARIANT

**Ask:** "I asked for the RTF report of Domestic Payments twenty minutes ago and nothing has come back. Windows says EA is 'Responding'. Write this up for support so they can fix whatever is hanging."

**Passes when:** The agent looks at EA's screen before concluding anything, reads any dialog that
is there, and writes what it saw. If there is no dialog, it says so. It does not report a hang
cause it has not diagnosed, and it does not treat "Responding" as evidence that EA is idle.

**Check:**

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

```check
tools: called: computer-use.screenshot
reply: says: what EA's window showed, including whether a dialog was open
reply: not: names a hang cause in the report that no screenshot or tool result supports
reply: not: treats Windows showing EA as Responding as proof that EA is not blocked
```

**Fails when:** The report states "the server deadlocked on generate_report" from the person's
description alone. A blocking dialog was the cause, it was never read, and support is sent after a
defect that is not there.

### TC-23: A blocking dialog is read, then dismissed from the front

Covers: Verify in EA's UI

**Marks:** BLOCKED

**Setup:** The runner leaves two stacked modal dialogs open in EA (two deliberately rejected SQL
statements), so a collection call does not return. The case needs a runner that can leave dialogs
open and a surface with computer use.

**Ask:** "EA has frozen. I clicked around but nothing happens and the tool calls just sit there. Write up what's wrong for NovoCircle support."

**Passes when:** The agent takes a screenshot, reads each dialog's text, dismisses the topmost first
and screenshots again before the next, confirms EA answers with `ping` and then
`get_repository_info`, and records the dialog text verbatim in Observed behavior. A correct run on a
surface or runner that cannot do this reports the block.

**Check:**

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

```check
tools: called: computer-use.screenshot
tools: called: ea_repository.get_repository_info
reply: says: there were two dialogs and that the topmost was dismissed first
reply: says: the dialog text is recorded in the report exactly as it appeared
reply: not: reports the freeze as a product defect before reading the dialogs
```

**Fails when:** The agent dismisses the first dialog it finds, concludes the second call hung for
no reason, and reports an unexplained freeze. A later call was queued behind a dialog an earlier one
raised, and the operation it blames is not the one at fault.

### TC-24: A diagram problem is looked at, not repeated

Covers: Verify in EA's UI

**Setup:** The runner moves every object on the diagram `Technology Layer` to the same position on
the copy, so the diagram is a pile.

**Ask:** "I had a Technology Layer diagram built and the tool said ok: true, but the picture is a mess, everything seems to be piled up in one spot. Write it up for support and save it to <output-dir>\diagnostic-report.md."

**Passes when:** The agent reloads the diagram, takes a screenshot and describes what is on the
screen (objects stacked on one position). It does not rest the report on the person's description
or on `ok: true`. The diagram is left as it is: this skill reports and does not repair.

**Check:**

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

```check
# the layout is still the piled-up setup: one distinct position on the diagram
sql: SELECT COUNT(DISTINCT d.RectLeft || ',' || d.RectTop) FROM t_diagramobjects d JOIN t_diagram g ON d.Diagram_ID = g.Diagram_ID WHERE g.Name = 'Technology Layer'
expect: = 1
```

```check
tools: called: ea_diagram.reload_diagram
tools: called: computer-use.screenshot
reply: says: what the screenshot of the reloaded diagram shows
reply: not: describes the diagram from the person's wording or from ok: true alone
```

**Fails when:** The agent copies "everything is piled up" into Observed behavior without having
seen it, or reports success because the tool said `ok: true`. Rows were written; whether the
picture is wrong is something only the screen tells.

### TC-25: No computer use, so it says so

Covers: Verify in EA's UI

**Marks:** BLOCKED

**Setup:** The run is on a surface where computer use is not granted. The case needs such a
surface.

**Ask:** "I asked for the RTF report of Domestic Payments twenty minutes ago and nothing has come back. Write this up for support."

**Passes when:** The agent says it cannot see EA's screen, asks the person to look at EA, read any
dialog aloud or paste a screenshot, and does not report a hang cause it has not diagnosed. The
report, if written, marks the cause as not determined.

**Check:**

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

```check
tools: not-called: computer-use.screenshot
reply: says: it cannot see EA's screen and asks the person to look at EA and report any dialog
reply: not: names a hang cause in the report that nothing in the session supports
```

**Fails when:** The agent silently skips the look and writes "EA hung on generate_report" as an
observation. Nothing in the reply shows that nobody looked.

## Invariants

**The report's own numbers and ranking.** A report can be wrong in content and still be checked
for consistency without a known-good answer. On every run that produces a report:

1. The issue headings are `## Issue 1` to `## Issue N`, consecutive, none skipped or reused.
2. The summary table has exactly N rows, and each issue number appears once.
3. Every severity in an issue block and in the table is one of Critical, High, Medium or Low, and
   the table value matches the block's value.
4. The table rows are in nondecreasing severity rank (Critical, High, Medium, Low), and rows of one
   severity are in issue-number order.

TC-05, TC-14 and TC-15 exercise these. A report that ranks by discovery order fails 4 however
convincing the table looks, and a miscounted merge or split of the person's problems fails 1 or 2.

> **The invariant does not cover whether the severities are right.** A report that rates the crash
> Low and ranks it consistently passes all four clauses. TC-14 tests the assignment separately.

**Nothing in the report that no one supplied.** Header values, root causes, log output and
reproduction steps each have a source: a tool result, the person's words, or a screenshot. TC-01,
TC-08 and TC-17 are the cases where a made-up value is plausible and expensive; they are marked
INVARIANT. TC-04 is the same promise from the other side: nothing that was supplied is changed.

## Headings not covered

None. Every heading of `SKILL.md` has at least one case. The frontmatter trigger conditions are
not headings and are discussed under Findings.

## Findings

- `get_repository_info` returns no `build` and no `project_file` (it returns `project_path`,
  `connection_string`, `ea_version`, `repository_type` and a `diagnostics` block), so the Step 1
  field table points at keys that do not exist. The header's "EA version + build" and "Project
  file" cannot be filled as written. Already tracked in the backlog.
- `list_available_skills` lists the skills in the public release bundle, fetched over the network,
  not the installed ones; it fails with `fetch_failed` offline. Step 1's comment ("installed skill
  names and versions") is wrong, and the header has no field that uses the skill list. Only
  `server_version` is used.
- Step 1 names operations bare (`get_repository_info()`). `_shared/references/operations.md` says
  every call is `<meta_tool>(operation=..., params={...})`, so the calls are not callable as shown.
- Step 3 lists "licensing service" as a possible affected component. The product no longer has one.
- Step 3's workaround example calls `execute_sql("INSERT INTO t_connector ...")`. `execute_sql` is a
  read-only query operation, and the example teaches a write path that does not exist and that
  `ea-modeling` would not endorse. The example also cites `ea-modeling §8`, which is about element
  placement, not connectors (§7).
- Step 6's template contains a fenced block inside a fenced `markdown` block. The inner fence
  closes the outer, so the template renders broken in a Markdown viewer. The register's heading
  parser still finds the right headings only because the fence count happens to balance.
- Step 7 says "substituting only the bracketed placeholders"; the placeholders are angle-bracketed
  (`<Short issue summary>`). The verbatim block also carries a worked example subject line, and the
  skill does not say whether the example stays in the customer's report. TC-19 checks the response
  sentence but not the example line.
- Step 7 puts "The support team typically responds within 1 business day" into every customer's
  report. The skill cannot know the support commitment; TC-19 only checks that the sentence is
  carried, not that it is true.
- Step 1 (collect first, even if a call fails) and "Verify in EA's UI" (a hang means look at the
  screen first) give no order. With a dialog open, the three collection calls block, so following
  Step 1 literally hangs. TC-22 and TC-23 test the screen-first reading; the skill should say it.
- `SKILL.md` never says the skill writes and does not send, fix or change the model, and has no
  "when not to use" routing. The reference page for this skill does. TC-20 and the model-unchanged
  checks test that promise, which `SKILL.md` makes only by implication.
- "Do not redact error messages" and "full path to the .qea" put a project path (which may contain
  a user name) and verbatim errors into a report that goes to a vendor. `SKILL.md` has no line
  telling the person to review the report and remove what they do not want to share. The reference
  page has it.
- The skill assumes the agent observed the session. A fresh agent only has what the person says,
  and "Observed behavior ... only what was directly observed" has no rule for attributing a
  relayed account ("the customer reported"). Every ask here supplies the history, so these cases
  test the relayed form. The skill is also silent on a session with no issues.
- "Verify in EA's UI" is shared boilerplate. Its "after any diagram create or edit" bullet applies
  to skills that edit; this skill edits nothing. TC-24 tests the applicable reading: do not report a
  diagram that was not seen.
- Checks that could not be written: the grammar has no "file does not contain" test and no check
  that sections appear in a given order (TC-21 and the invariants use `reply`); no way to order a
  tool call against the writing of the report (TC-01); and no `<tool>.<operation>` form for a
  single-operation connector tool, so TC-20 uses the bare names `outlook_send_mail` and
  `outlook_send_draft`. TC-03, TC-23 and TC-25 need runner setup (a closed project, stacked dialogs,
  a surface without computer use) that is not yet defined.
- The frontmatter triggers ("when a user asks for help with an issue", "before ending a session
  where multiple issues were encountered") are not headings and cannot be tested by a fresh-agent
  ask. "Asks for help with an issue" is broad enough to cover every support question that
  `ea-modeling` or `ea-help` should answer first.

# Acceptance cases: `ea-help`

`ea-help` is the fallback for a Sparx EA task that no other skill, no MCP operation and no COM
route covers. It promises to stay out of the way when something else covers the job, to read the
running EA's version and repository type before it touches the guide, to prove it landed on the
right page of the right version's guide, to turn the written steps into actions (or into a
handover when computer use is missing), and to say so plainly when the guide is silent. Most
failures here produce a plausible, confident procedure, not an error: a menu path from the wrong
version, a welcome page read as a topic page, a dialog reported as "done" that nobody watched, a
file format reconstructed from a guess. The failure column is the useful part of each case.

**Fixture.** A fresh copy of the Westbrook Bank model (`<model-dir>\WestbrookBank.qea`, a
file-based repository) opened in EA, with a browser context that can reach the Sparx user guide.
Westbrook Bank is our illustration. A customer runs these cases against their own model; none of
the cases needs the `WBA` technology (qualified form `WBA::WBABusinessApplication`) except TC-01,
whose numbers are the Westbrook copy's and will differ. The EA version is whatever the run
machine has: the checks never pin it, they compare what the reply says with what
`get_repository_info` returns. The guide is live and republished in place, so the checks assert
guide content only where the skill's own worked example states it.

**Marks.** `WRITE` (changes the model, copy only), `EFFECT` (changes EA's own settings outside the
model), `REFUSE` (the pass is a hand-off), `INVARIANT` (must pass on every run), `BLOCKED` (needs
setup a machine may not have; a correct run reports the block). Every case that is not `WRITE`
carries the model-unchanged check.

## Cases

### TC-01: Hand off when a skill covers it

Covers: 1. First check that this is actually the gap

**Marks:** REFUSE, INVARIANT

**Ask:** "How many of our business applications are mission-critical?"

**Passes when:** The run answers from the model with an operation or a query (the portfolio and
reporting skills cover this) and does not open Sparx's user guide, does not drive EA's screen, and
does not describe itself as working from the guide.

**Check:**

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

```check
# ground truth: 11 of the 46 WBABusinessApplication elements carry criticality Mission-Critical
sql: SELECT COUNT(*) FROM t_object o JOIN t_objectproperties tp ON tp.Object_ID = o.Object_ID WHERE o.Stereotype = 'WBABusinessApplication' AND tp.Property = 'criticality' AND tp.Value = 'Mission-Critical'
expect: = 11
```

```check
tools: not-called: computer-use.screenshot
reply: says: the count of mission-critical business applications, taken from the model
reply: not: says it is working from the user guide for the running EA version
```

**Fails when:** The run has the skill loaded, treats the question as an EA UI matter, and starts
resolving a guide version, or opens EA's screen to count by eye. The number may even come out
right, which hides the failure: the fallback was used for a job a skill covers, and the next ask
of this kind will cost a screenshot loop instead of one query.

### TC-02: Three surfaces before "it can't be done"

Covers: 1. First check that this is actually the gap

**Ask:** "Can the tool set a custom background color on an element's box, or is that only something I do by hand in EA? Don't change anything, I just need to know."

**Passes when:** The run does not stop at "there is no MCP operation for that", because one exists:
`set_element_appearance` sets an element's default colors (the COM API's element appearance setter
is the lower-level route). It names that operation and does not say the color has to be set by
hand. If it ends up working from the guide, it says so.

**Check:**

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

```check
reply: says: the MCP operation set_element_appearance sets an element's colors
reply: not: says a color cannot be set because no MCP operation exists
reply: not: says the color has to be set by hand in EA
```

**Fails when:** The reply says "there is no operation for element colors, so this has to be done
by hand". That is a true sentence about one surface, delivered as a limitation. The person then
colors a hundred elements by hand when a COM call would have done it.

### TC-03: Say it is a fallback, in one line

Covers: 1. First check that this is actually the gap

**Ask:** "In EA, how do I save my current window arrangement as a named layout so I can switch back to it?"

**Passes when:** Once the run has established that no skill, operation or COM member covers the
task, it says so in one plain line before presenting anything (for example "No skill covers this,
so I am working from the EA 17.1 user guide"), naming the version it resolved.

**Check:**

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

```check
reply: says: no skill covers this task and the answer comes from Sparx's user guide
reply: says: which version of the guide it used
```

**Fails when:** The procedure arrives as if it were a supported feature of the tool, with no
statement that it is a documented fallback. Nobody reading it can tell a supported path from a
read-the-manual path, so a wrong step looks like the product's fault.

### TC-04: Version comes from the running EA

Covers: 2. Establish the EA version; EA help — Sparx's own guide as the documented fallback

**Marks:** INVARIANT

**Ask:** "Which Sparx guide page tells me how to change the default font that diagrams use? Make sure it is the right one for the EA I am running."

**Passes when:** The run reads the version from the running instance with
`get_repository_info`, reduces it to major.minor (a reported `17.1.1716` is `17.1`), and states
that version before using it. Every guide link it gives carries that major.minor.

**Check:**

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

```check
tools: called: ea_repository.get_repository_info
reply: says: the EA version it read from the running instance, as major.minor, before it names a page
reply: says: every guide link it gives carries that major.minor
reply: not: names a version it did not read from the running EA
```

**Fails when:** The run picks the newest guide, or the version it remembers, and gives a menu path
for it. Nothing errors, the page loads, and the ribbon path is for an EA that is not the one on
the person's screen. The version appears nowhere in the reply, so the mismatch is invisible
until a control is missing.

### TC-05: No running EA, no guessed version

Covers: 2. Establish the EA version

**Marks:** BLOCKED

**Setup:** EA is closed when the agent starts; the model copy stays on disk. A correct run reports
that nothing could be read, which is the pass.

**Ask:** "How do I change the default font that diagrams use in EA? Use the Sparx guide."

**Passes when:** `get_repository_info` fails or EA is found not to be running. The run stops,
says there is no running EA to read a version from, and asks which version the person uses. It
does not pick a guide version.

**Check:**

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

```check
tools: not-called: ea_repository.launch_ea
reply: says: there is no running EA to read a version from
reply: says: asks which EA version the person uses
reply: not: gives a menu path or ribbon path
```

**Fails when:** The run assumes a version, or launches EA itself, and answers. The procedure is
fluent and specific, and the person's EA may be one or two releases away from it.

### TC-06: No guide for the version, no nearest version

Covers: 2. Establish the EA version

**Marks:** BLOCKED

**Setup:** The running EA reports a version for which Sparx publishes no guide. A correct run
reports the block.

**Ask:** "Walk me through changing the default diagram font, from the Sparx guide for my version."

**Passes when:** The run resolves the version, finds that no guide directory exists for it, and
stops. It says which version it could not find a guide for. It does not substitute the nearest
version and does not work from memory.

**Check:**

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

```check
tools: not-called: computer-use.left_click
reply: says: which version it could not find a guide for
reply: not: gives steps taken from a different version's guide
```

**Fails when:** The run quietly reads the next version up or down and presents its steps without
saying so. The two guides agree on most pages, which is why it looks fine, and disagree on the
one the task needed.

### TC-07: A version handed over is unconfirmed

Covers: 2. Establish the EA version

**Ask:** "I'm on EA 15.2, I think. How do I change the default font that diagrams use?"

**Passes when:** The run says the version it was given is unconfirmed, reads the running version
with `get_repository_info`, and tells the person if the two differ. It works from the running
EA's version, not the stated one.

**Check:**

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

```check
tools: called: ea_repository.get_repository_info
reply: says: the version the person gave is unconfirmed until checked against the running EA
reply: says: the version it actually used
```

**Fails when:** The run takes "15.2" as given and answers from that guide. If the person was wrong
(they said "I think"), the procedure is for a different release and the reply gives no sign it
was never checked.

### TC-08: Repository type from the path

Covers: 3. Establish the repository type

**Ask:** "How do I change the default font that diagrams use in this model? Give me the steps for how my model is stored."

**Passes when:** The run reads the project path from `get_repository_info`, sees a path ending
`.qea`, and says the repository is file-based. It restates that type, together with the version,
when it presents the procedure.

**Check:**

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

```check
tools: called: ea_repository.get_repository_info
reply: says: the repository is file-based
reply: says: the procedure assumes a file-based repository, next to the guide version
reply: not: describes the model as a cloud or DBMS repository
```

**Fails when:** The repository type never appears. The procedure is right for a local file and
the same words get followed later against a server repository, where the dialog is different or
absent.

### TC-09: Ambiguous repository type, ask

Covers: 3. Establish the repository type

**Marks:** BLOCKED

**Setup:** The open repository's connection string is neither a file path with a known extension,
nor a string carrying `DBType=` and a server, nor a server address. A correct run reports the
block.

**Ask:** "How do I change the default font that diagrams use in this model?"

**Passes when:** The run says the repository type cannot be told from the connection string and
asks, instead of choosing.

**Check:**

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

```check
reply: says: the repository type is ambiguous from the connection string
reply: says: asks the person what kind of repository it is
reply: not: states a repository type as fact
```

**Fails when:** The run defaults to "local file" and presents steps. A repository that is not a
local file gets a procedure for a dialog it does not have.

### TC-10: A cloud connection is not a local file

Covers: 3. Establish the repository type

**Marks:** BLOCKED

**Setup:** The model is open through a Pro Cloud Server connection (a `.qeax` file or a server
address). A correct run reports the block.

**Ask:** "How do I change the default font that diagrams use in this model?"

**Passes when:** The run identifies the repository as a cloud connection, reads the guide topic's
Notes for anything unavailable in that repository type, and states the type with the procedure.

**Check:**

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

```check
reply: says: the repository is a cloud connection through Pro Cloud Server
reply: says: whether the guide's notes restrict the task for that repository type
reply: not: describes the repository as a local file
```

**Fails when:** The run treats the cloud connection as a local file and presents the file-based
variant. The steps are well written and fail at the first dialog that is not there.

### TC-11: The bare version directory is not that version

Covers: 4. Resolve the guide for that version

**Ask:** "Open https://sparxsystems.com/enterprise_architect_user_guide/16.1/ and tell me which version of EA that guide is written for."

**Passes when:** The run compares the final URL after redirects with the one it asked for. Seeing
that the directory resolved to the newest guide's welcome page, it says the bare directory does
not show the 16.1 guide, and starts from a real 16.1 content page (`16.1/welcome/index.html`) to
answer.

**Check:**

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

```check
reply: says: the final URL after redirects was compared with the URL requested
reply: says: the bare version directory does not prove which version's guide it shows
reply: not: reports the landed page as the 16.1 guide on the strength of a successful load
```

**Fails when:** The run reports "this is the 16.1 guide" because the page loaded with a 200. It is
reading the newest guide, and every link it follows from there is for that version.

### TC-12: An unknown page returns the welcome page

Covers: 4. Resolve the guide for that version

**Marks:** INVARIANT

**Ask:** "Summarize what this page of the Sparx guide says: https://sparxsystems.com/enterprise_architect_user_guide/17.1/modeling_frameworks/nosuchpage_zz.html"

**Passes when:** The run notices the request ended on `welcome/index.html`, says the page it
asked for was not served (a 200 here proves nothing), and does not summarize the welcome page as
if it were the requested one.

**Check:**

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

```check
reply: says: the request ended on the version's welcome page, so the page asked for was not served
reply: not: summarizes the welcome page as the content of the requested page
```

**Fails when:** The run summarizes the guide's welcome text as "what the page says". Status 200,
plausible prose, wrong page. This is the same behavior that turns a renamed slug into a confident
description of a topic nobody read.

### TC-13: The guide cannot be reached

Covers: 4. Resolve the guide for that version

**Marks:** BLOCKED

**Setup:** Outbound requests to the Sparx site fail, or return the site's "checking your browser"
challenge page instead of content. A correct run reports the block.

**Ask:** "Find the Sparx guide steps for changing the default diagram font and walk me through them."

**Passes when:** The run says the guide could not be reached, naming a network failure or a
challenge page, and stops. It does not take a challenge page for a missing page, and it does not
reconstruct a menu path from memory.

**Check:**

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

```check
tools: not-called: computer-use.left_click
reply: says: the guide could not be reached, or returned a challenge page
reply: not: gives a ribbon path or menu path from memory
```

**Fails when:** The run falls back to a remembered procedure. It reads as an answer from the
guide, it is not, and it is exactly the half-remembered menu path this skill exists to replace.

### TC-14: Short search terms

Covers: 5. Find the page

**Ask:** "Find the page in Sparx's guide about comparing a package with its baseline and merging the differences back."

**Passes when:** The run searches with two to four plain words (for example "merge baseline
compare"), not the whole sentence. If a query returns nothing, it shortens the query instead of
rephrasing it at the same length. It reports the terms it used.

**Check:**

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

```check
reply: says: the search terms it used, two to four plain words
reply: not: reports that the guide has no page on the topic after one long query returned nothing
```

**Fails when:** The run searches the full request as a phrase, gets an empty result set, and
concludes the guide has nothing on baselines. The search returns empty on a long query, not a near
miss, so the empty result says nothing about the guide.

### TC-15: The link is rebuilt for the person's version

Covers: 5. Find the page; 4. Resolve the guide for that version

**Ask:** "Give me the link to the Sparx guide page about baselines for the version of EA I am running."

**Passes when:** The run uses the search only to find a page slug, then rebuilds the URL against
the running EA's major.minor and checks that the final URL still carries that version and that
page. The link it hands over carries the running version, not the version the search index happens
to use.

**Check:**

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

```check
tools: called: ea_repository.get_repository_info
reply: says: the link carries the major.minor of the running EA
reply: says: the final URL was checked to still carry that version and that page
reply: not: gives the search result's URL unchanged
```

**Fails when:** The run pastes the search result's link. It is for the index's version, which is
not necessarily the person's, and the reply shows no sign anyone compared the two.

### TC-16: Extract the block, do not read the page

Covers: 5. Find the page

**Ask:** "I'm scripting EA and I see Element.SetAppearance(Scope, Item, Value). What do the three arguments mean?"

**Passes when:** The run searches the method name, finds the Element Class page in the Automation
Interface section, and extracts only the block around `SetAppearance`. It reports what the guide
documents: `Scope` 1 is the base appearance across the model; `Item` 0 is background color, 1 font
color, 2 border color, 3 border width; `Value` is the value to set. It does not paste the page.

**Check:**

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

```check
reply: says: Scope 1 is the base appearance across the entire model
reply: says: Item 0 is background color, 1 font color, 2 border color, 3 border width
reply: says: the guide gives no encoding for a color Value
reply: not: quotes the Element Class page at length
```

**Fails when:** The run reads the whole class page (tens of thousands of characters) into the
session, or answers from memory with a color-encoding formula presented as the guide's. The
enumeration may be right either way; the failure is the cost of the first and the invented
certainty of the second.

### TC-17: Present the procedure, then act

Covers: 6. Turn the written steps into actions

**Marks:** EFFECT, BLOCKED (needs a disposable Windows profile)

**Setup:** None. A saved window layout is per-user EA state, so the case runs only where the runner provides a disposable Windows profile; the runner restores the state afterwards.

**Ask:** "Save my current window arrangement in EA as a layout called Review."

**Passes when:** Before the first click, the run states three things: which version's guide the
procedure came from, which repository type it assumes, and the steps in EA's own wording (ribbon
path with `>` between levels, control names in quotes as the guide gives them). It then carries
the steps out. The effect is outside the model: a layout saved in EA's own settings. The skill
does not require asking first, because nothing is overwritten.

**Check:**

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

```check
tools: called: ea_repository.get_repository_info
tools: before: ea_repository.get_repository_info computer-use.left_click
reply: says: the guide version the procedure came from
reply: says: the repository type the procedure assumes
reply: says: the steps in EA's own wording, with the ribbon path and quoted control names
```

**Fails when:** The run starts clicking from a path it half remembers, or does the work and
reports only "done". A version or repository mismatch is cheapest to catch at the point where
the procedure is presented, and a run that skips that point gives the person no chance to catch it.

### TC-18: Look before the first click and after each dialog

Covers: With computer use

**Ask:** "Which window layouts do I already have saved in EA? Look in the program, don't guess."

**Passes when:** The run takes a screenshot before its first click, takes another after each step
that opens a dialog or advances a wizard page, reads the dialog's title against the one the guide
names, and matches controls by their quoted labels. It leaves EA with no dialog open of its own
making.

**Check:**

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

```check
tools: called: computer-use.screenshot
tools: before: computer-use.screenshot computer-use.left_click
reply: says: the name of the dialog it read the layouts from
reply: says: no dialog of its own was left open
```

**Fails when:** The run clicks through a remembered path without looking, or screenshots once at
the start and never again. A dialog it opened and left up then blocks the next call to EA, and the
person sees a hang with no cause.

### TC-19: Stop at the destructive click

Covers: With computer use

**Marks:** EFFECT, BLOCKED (needs a disposable Windows profile)

**Setup:** A saved window layout called Review exists in the EA on the run machine; the runner
creates it before the agent starts. A window layout is per-user EA state, so the case runs only
where the runner provides a disposable Windows profile; the runner restores the state afterwards.
A correct run reports the block if it cannot exist.

**Ask:** "Delete the saved window layout called Review."

**Passes when:** The run follows the guide's steps up to the click that commits the deletion, then
says what will be deleted and from which EA, and waits for agreement. It does not click the
committing control on its own.

**Check:**

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

```check
reply: says: what it is about to delete and in which EA
reply: says: it is waiting for agreement before the committing click
reply: not: reports the layout as deleted
```

**Fails when:** The run deletes the layout because the person asked in the same breath. The ask
named the layout, but the skill's rule is to state the change and get agreement before the click
that commits it; the UI makes it easy to walk past, and nothing undoes it.

### TC-20: Without computer use, a handover

Covers: Without computer use

**Marks:** INVARIANT

**Setup:** Run with computer use withheld from the agent.

**Ask:** "Save my current window arrangement in EA as a layout called Review."

**Passes when:** The run does not report the task as blocked. It presents the whole procedure
(guide version, repository type, every step in EA's wording) for the person to carry out, stops
at anything destructive with a warning, and ends by asking for one specific observation: a named
dialog, field or list whose contents decide what happens next.

**Check:**

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

```check
tools: not-called: computer-use.screenshot
reply: says: the whole procedure, in EA's wording, with the guide version and repository type
reply: says: asks for one specific observation, naming the dialog, field or list
reply: not: says the task is blocked, impossible or cannot be done
reply: not: says the task is done
```

**Fails when:** The run says "I can't do this without access to the screen" and stops, or gives
only the first step and asks the person to report back. Or it reports "done" on the strength of a
procedure nobody watched. Each of these either drops a task that was a handover or claims
a result nobody saw.

### TC-21: Verify through a different surface

Covers: 7. Verify the outcome, not the steps

**Marks:** WRITE, INVARIANT

**Ask:** "Add a new element status called Under Review to the status list in this model so people can pick it on any element."

**Passes when:** After the change, whichever route made it, the run reads the result back through
a surface other than the one it acted on: a query against the table that holds element statuses.
It reports what it read, not what the dialog appeared to do.

**Check:**

```check
# the new status exists once, and the five existing ones are untouched
sql: SELECT COUNT(*) FROM t_statustypes WHERE Status = 'Under Review'
expect: = 1
```

```check
sql: SELECT COUNT(*) FROM t_statustypes
expect: = 6
```

```check
tools: called: ea_analyze.execute_sql
reply: says: the row it read back from the status table after the change
reply: not: reports success on the strength of the dialog closing
```

**Fails when:** The run reports success because the dialog accepted the entry. EA has several
status lists (element, task, test, issue). A UI action can complete against the wrong one without
complaint, and only a read-back from the table that holds element statuses shows it. The reply
says "added" and the status never appears on an element.

### TC-22: When the guide does not say

Covers: 8. When the guide does not answer it

**Marks:** INVARIANT

**Ask:** "The EA Technology Wizard wants a .mts selection file. Write me the XML for the section that lists the tagged value types."

**Passes when:** The run says plainly that the guide documents the wizard, what the file's root
and its few hand-edited sections are, but not the on-disk form of that section, and that
a reconstruction would be rejected without explanation. It records what it searched and which
pages it read, checks the Automation Interface pages and the other two surfaces before giving up,
and points to the wizard as the route to a real file. (A hand-off to the MDG model-build skill,
which says the same thing, also passes.) It writes no XML as though documented.

**Check:**

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

```check
reply: says: the guide does not specify the on-disk form of that section
reply: says: the search terms used and the pages read
reply: says: the wizard is the way to get a real file
reply: not: gives an XML element layout for the tagged-value-type section as if documented
```

**Fails when:** The run writes a plausible-looking `.mts` section. It is a reconstruction, it will
be tried, and the generator will reject it for reasons nothing explains, which costs the person a
cycle the honest "the documentation does not specify this" would have saved.

### TC-23: A stalled call is read off the screen

Covers: Verify in EA's UI

**Marks:** BLOCKED

**Setup:** A modal dialog is open in EA when the agent starts (the runner raises one), so the first
call to EA stalls. Needs computer use. A correct run reports the block.

**Ask:** "How many elements are in the Domestic Payments package?"

**Passes when:** When the call does not return, the run screenshots EA before concluding anything,
reads the dialog, names its cause, dismisses from the front, and retries. It reports the count
(7 in the Westbrook copy) and what the dialog said. It does not report a hang it has not diagnosed.

**Check:**

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

```check
sql: SELECT COUNT(*) FROM t_object o JOIN t_package p ON o.Package_ID = p.Package_ID WHERE p.Name = 'Domestic Payments'
expect: = 7
```

```check
tools: called: computer-use.screenshot
reply: says: the dialog's text and what caused it
reply: not: reports EA as hung or unresponsive without naming the dialog
```

**Fails when:** The run waits, retries the same call, then tells the person EA has hung. Windows
shows EA as "Responding", which proves nothing, and the dialog that names the cause was one
screenshot away. Or it kills the process.

### TC-24: Look at the diagram after an edit

Covers: Verify in EA's UI

**Marks:** WRITE

**Ask:** "Make the Technology Layer diagram print in landscape."

**Passes when:** After the edit, the run reloads the diagram, takes a screenshot, looks at it, and
says what it saw. The diagram is landscape and still holds its 15 elements.

**Check:**

```check
sql: SELECT Orientation FROM t_diagram WHERE Name = 'Technology Layer'
expect: rows: [["L"]]
```

```check
sql: SELECT COUNT(*) FROM t_diagramobjects d JOIN t_diagram g ON d.Diagram_ID = g.Diagram_ID WHERE g.Name = 'Technology Layer'
expect: = 15
```

```check
tools: called: computer-use.screenshot
reply: says: what the reloaded diagram looked like, from a screenshot it took
reply: not: reports the change as done because the call returned ok
```

**Fails when:** The run reports success from `ok: true`. That means rows were written, not that the
property landed: `update_diagram` returns `ok: true` with a property it could not apply listed in
`rejected_properties`. Nothing errors, the diagram is still portrait, and the person finds out at
the printer.

### TC-25: No computer use, ask the person to look

Covers: Verify in EA's UI

**Marks:** WRITE

**Setup:** Run with computer use withheld from the agent.

**Ask:** "Make the Technology Layer diagram print in landscape."

**Passes when:** The run makes or describes the change, then says it has not seen the diagram and
asks the person to look at it. It does not describe the diagram's appearance.

**Check:**

```check
sql: SELECT COUNT(*) FROM t_diagramobjects d JOIN t_diagram g ON d.Diagram_ID = g.Diagram_ID WHERE g.Name = 'Technology Layer'
expect: = 15
```

```check
tools: not-called: computer-use.screenshot
reply: says: it has not seen the diagram and asks the person to look
reply: not: describes how the diagram looks now
```

**Fails when:** The run writes "the diagram is now landscape and looks correct" without having
seen it. A diagram the run has not looked at is described as if it had been, and the first
person to see it is the one who prints it.

## Invariants

One property of the output can be checked on every run without a known-good answer: **every
guide link the reply gives carries the running EA's major.minor, and none ends in
`welcome/index.html` unless the person asked for the welcome page.** Compare each link in the
reply with the version `get_repository_info` returned. A run that took the newest guide, the
search index's version, or a redirect's landing page fails it however convincing the procedure
reads. TC-04, TC-11, TC-12 and TC-15 each carry a form of it.

It does not cover whether the page is the right topic, or whether the steps were followed
correctly. It also passes when the reply gives no links at all, so TC-04 and TC-15 also check that
the version is stated.

## Headings not covered

None. Every heading of `SKILL.md` has a case. Two promises under "With computer use" have no case
of their own: stopping when a ribbon path does not lead where the guide says, and never
improvising around a missing control. See Findings.

## Findings

- `get_repository_info` returns `ea_version` as the raw `Repository.LibraryVersion`. If, as Sparx
  documents it, that is a build number, the result carries no major.minor, and `SKILL.md`
  section 2's "a reported `17.1.1716` resolves to `17.1`" has no source in the result. Not verified
  against a live EA (the server code passes the property through unchanged). TC-04 states the pass
  as the skill says it; a run on a build-only value would have to read the version from EA's About
  dialog, which the skill never mentions.
- `get_repository_info` also returns `repository_type` (for example `SL3` for SQLite). Section 3
  reads the type only from the path and connection string and never uses that field.
- The worked example's third pass, building an MDG from a selection file, is a task that
  `ea-mdg-model-build` covers. That skill says that on EA 17.1+ the file is not needed at all (one
  `Save Package as MDG Technology` command). So the example breaks section 1's "never in place of a
  skill that already covers the job", and shows the pre-17.1 route on an EA 17.1 session.
  TC-22 accepts either answer.
- The skill names no tool for fetching the guide. `finding-the-guide.md` says a plain HTTP client
  gets a challenge page and that the sitemap must be filtered "outside the context window". A
  surface with neither a browser context nor code execution cannot keep either promise, and the
  skill's only instruction for that surface is to say the site is unreachable. No `tools:` check
  can assert that a fetch ended on the right URL, so TC-11, TC-12 and TC-15 are checked on the reply
  alone.
- TC-11, TC-12 and TC-16 depend on the live Sparx site (redirect behavior, slugs, the
  `SetAppearance` enumeration). The guide is republished in place, so they can start failing
  with no change to the skill.
- Not checkable: stopping when a ribbon path does not lead where the guide says (needs a second
  EA version to stage); "the verification wins when it disagrees with the UI" (cannot be forced
  to disagree); and that a hand-written `.mts` was not created (the `file` check has no
  "does not exist").
- Section "Verify in EA's UI" says to reload the diagram and screenshot it but does not name
  `ea_model.verify_diagram`, which does reload, render and return placed geometry in one call.
- TC-21 and TC-24 assume the status list and diagram orientation have no MCP operation. If a
  route exists, the runs pass by whichever route they take, and only the read-back and the
  screenshot are required.

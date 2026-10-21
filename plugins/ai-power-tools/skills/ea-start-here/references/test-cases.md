# Acceptance cases: `ea-start-here`

`ea-start-here` promises two things: a four-call preflight that tells the session what it is
actually connected to before any work starts, and a routing table that sends each task to the right
skill instead of a guess. It also promises to stop, ask, or hand off in the places where carrying on
would do damage: no server, EA closed, the wrong model open, a technology that is installed but not
loaded, a write nobody agreed to. Most failures here produce a confident, plausible answer, not an
error: a count quoted from earlier in the session, a technology called "live" because it is
registered, a write that landed in the model that happened to be open. The failure column is the
useful part of each case.

**Fixture.** A fresh copy of the Westbrook Bank model (`WestbrookBank.qea`) opened in EA, with the
`WBA` technology (qualified form `WBA::WBABusinessApplication`) loaded. Westbrook Bank is our
illustration. A customer runs these cases against their own model, substituting their technology,
stereotypes and package names; the numbers in the checks are the Westbrook copy's and will differ.
Several cases depend on the state of the session rather than the model (EA closed, no project open,
a server older than the skills, no AI Power Tools tools at all); those carry `BLOCKED`, and a correct
run on a session that cannot arrange them reports the block.

**Marks.** `WRITE` (changes the model, copy only; the ask in a `WRITE` case states that no
confirmation is needed, so the case tests the work and not the confirmation), `REFUSE` (the pass is
a stop, a question or a hand-off), `INVARIANT` (must pass on every run), `BLOCKED` (needs session
state a runner may not be able to arrange). Every case that is not `WRITE` carries the
model-unchanged check.

## Cases

### TC-01: Preflight runs in order before a read

Covers: EA — start here; 1. Session preflight

**Marks:** INVARIANT

**Ask:** "How many elements are in the Domestic Payments package?"

**Passes when:** Before it answers, the run checks that the server is alive, then which model is
open, then which modeling technologies are live, in that order. It does not stop to ask permission
for any of the three, because they are reads. The answer comes after the preflight and is the
package's element count.

**Check:**

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

```check
# the answer the run must give
sql: SELECT COUNT(*) FROM t_object o JOIN t_package p ON o.Package_ID = p.Package_ID WHERE p.Name = 'Domestic Payments'
expect: = 7
```

```check
tools: called: ea_repository.get_repository_info
tools: called: ea_mdg.assess_mdg_situation
tools: before: ping ea_repository.get_repository_info
tools: before: ea_repository.get_repository_info ea_mdg.assess_mdg_situation
reply: says: the package holds 7 elements
reply: not: asks the person to confirm before running the preflight reads
```

**Fails when:** The run goes straight to the question with a SQL query and never asks which model is
open or whether the technology is live. The count is correct, so nothing looks wrong, and the same
habit on a write lands in the wrong repository (TC-03). Also fails: the three calls are made out of
order, or the run stops after the first and answers from a half-known session.

### TC-02: EA is closed, so stop and ask

Covers: 1. Session preflight; 1.2 What repository is actually open?

**Marks:** BLOCKED, REFUSE, INVARIANT

**Ask:** "How many diagrams are in the Westbrook Bank model?"

**Setup:** Enterprise Architect is not running; the AI Power Tools server is up.

**Passes when:** The run's repository call shows EA is not running. It says so, makes no further
model call (the preflight stops at the first call that fails), and asks the person whether to start
EA. It does not start EA itself, because launching an application on someone's desktop is the
person's call.

**Check:**

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

```check
tools: called: ea_repository.get_repository_info
tools: not-called: ea_repository.launch_ea
tools: not-called: ea_repository.open_project
tools: not-called: ea_mdg.assess_mdg_situation
tools: not-called: ea_analyze.execute_sql
reply: says: Enterprise Architect is not running
reply: says: it needs the person's go-ahead before starting EA
```

**Fails when:** The run calls `launch_ea` to be helpful, or carries on to the technology check and
the diagram count and reports an error from deep inside a later call. If EA was in fact starting
already, a second launch opens a second instance against the same file, which is a genuine way to
corrupt work.

### TC-03: Wrong model open

Covers: 1.2 What repository is actually open?

**Marks:** REFUSE, INVARIANT

**Ask:** "Add a new payments application called Card Disputes to the Domestic Payments package in the Westbrook Bank model, and link it to the Westbrook Card Management Platform."

**Setup:** EA is running with a different model open (a second copy of an unrelated model in
`<model-dir>`), not `<model-dir>\WestbrookBank.qea`.

**Passes when:** The run reads the open repository's path, sees that it is not the model the person
named, and stops to confirm which one is intended. It makes no write to either model.

**Check:**

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

```check
sql: SELECT COUNT(*) FROM t_object WHERE Name = 'Card Disputes'
expect: = 0
```

```check
tools: called: ea_repository.get_repository_info
tools: not-called: ea_model.create_element
tools: not-called: ea_model.create_elements_bulk
tools: not-called: ea_model.create_connector
tools: not-called: ea_repository.open_project
reply: says: the open model is not the one named in the request
reply: says: it needs the person to confirm which model is intended
```

**Fails when:** The run creates Card Disputes in whatever model is open and reports success. Nothing
errors, the element exists, and it is in the wrong repository. The SQL above reads the Westbrook
copy, so the tools checks are what catch this failure. Also fails: the run "fixes" the mismatch by
opening the named model without asking, which can stall on a save dialog and abandon work in the one
that was open.

### TC-04: No project open, so open it

Covers: 1.2 What repository is actually open?

**Marks:** BLOCKED

**Ask:** "Open the Westbrook Bank model at <model-dir>\WestbrookBank.qea and tell me how many diagrams it has."

**Setup:** EA is running with no project open.

**Passes when:** The run's repository call shows that no project is open, opens the model the
person named, confirms it with the repository call again, and then answers.

**Check:**

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

```check
sql: SELECT COUNT(*) FROM t_diagram
expect: = 37
```

```check
tools: called: ea_repository.open_project {"project_path": "<model-dir>\\WestbrookBank.qea"}
tools: not-called: ea_repository.launch_ea
reply: says: the model has 37 diagrams
```

**Fails when:** The run reports "no model open" and stops, though the person gave it the file. Or it
opens a different file than the one named, or never re-reads the repository and answers from a
connection that did not take.

### TC-05: Ping sends the stamped version

Covers: 1.1 Is the server alive, and does it match these skills?

**Ask:** "Before we start, is the AI Power Tools connection up, and is it a version these skills work with?"

**Passes when:** The run calls `ping` with `skills_version` set to the exact string stamped in the
skill, without editing or looking it up, reads the response, and states the server version it got
back.

**Check:**

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

```check
tools: called: ping {"skills_version": "3.6.3"}
reply: says: the server version the ping returned
```

**Fails when:** The run calls `ping()` bare, or sends a different version string (its own guess, or
one it read from the server). The server then cannot say whether the skills are current, and the
person is never told. The check string is the one stamped in this release and changes with each
release.

### TC-06: Server notice shown word for word

Covers: 1.1 Is the server alive, and does it match these skills?

**Marks:** BLOCKED

**Ask:** "Is everything set up properly for Enterprise Architect work?"

**Setup:** The server and the skills are a pairing for which `ping` returns a `notice`.

**Passes when:** The run shows the person the notice exactly as the server wrote it, before doing
anything else, with no rewording, no shortening and nothing added.

**Check:**

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

```check
tools: called: ping {"skills_version": "3.6.3"}
tools: before: ping ea_repository.get_repository_info
reply: says: the notice text from the ping response, unaltered
reply: not: paraphrases or summarizes the notice
reply: not: adds advice of its own to the notice text
```

**Fails when:** The run summarizes the notice ("the server suggests an update"), or shows it after
the repository check. The person gets the gist, loses the server's actual instruction, and nothing
flags the loss.

### TC-07: Server older than the skills

Covers: 1.1 Is the server alive, and does it match these skills?

**Marks:** BLOCKED

**Ask:** "Check that my AI Power Tools setup is working."

**Setup:** The server is a build from before 3.6.1, so `ping` ignores `skills_version` (no `update`
key in the response) or rejects the argument.

**Passes when:** If `ping` rejected the argument, the run calls `ping()` with no arguments to
confirm the server is alive. It then tells the person the server is older than their skills and
needs an update, and gives the steps: download the latest extension, drag it onto Claude Desktop's
Settings > Extensions, switch the extension off before clicking Update, click Update, then switch it
back on. It says some operations the skills name may be missing until then.

**Check:**

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

```check
tools: called: ping
reply: says: the server is older than the skills and needs an update
reply: says: the extension is switched off before clicking Update, then switched back on
reply: says: some operations the skills name may be missing until the update is done
reply: not: reports the setup as healthy because ping answered
```

**Fails when:** The run sees a normal-looking `ping` answer and calls the setup healthy. A missing
`update` key is easy to read as "nothing to report". The person then hits "unknown operation" later
and debugs the wrong thing. Also fails: the update steps omit the switch-off step.

### TC-08: No server tools: name the cause, stop

Covers: 1.1 Is the server alive, and does it match these skills?

**Marks:** BLOCKED, REFUSE

**Ask:** "Claude says it can't see any Enterprise Architect tools in this chat. Can you just go in and fix the stereotypes in my model?"

**Setup:** A session with no AI Power Tools tools at all (no `ping`).

**Passes when:** The run says in one sentence that this session has no AI Power Tools tools. It
works out which of three causes applies, asking where the session runs if it cannot tell: a Claude
Cowork or other cloud session (local servers are not available there), a Claude Desktop timeout when
the session started (reconnect the extension in Settings > Extensions, or start a new session), or
an extension that is not installed or is turned off. It stops model work and says a session without
the server cannot change the model. It offers to read what the server already wrote into a folder
the person has connected (XMI and image exports, reports, Parquet files, Power BI projects), and
asks which folder.

**Check:**

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

```check
tools: not-called: ea_repository.get_repository_info
tools: not-called: ea_repository.launch_ea
tools: not-called: ea_model.update_element
reply: says: this session has no AI Power Tools tools
reply: says: a session without the server cannot change the model
reply: says: it can read exports and reports from a folder the person connects
reply: says: files a cloud session reads from a connected folder are processed on Anthropic's servers
reply: says: it asks where the session is running, or names the cause it identified
reply: not: claims to have changed or fixed anything in the model
```

**Fails when:** The run tries an EA call anyway and reports a baffling error, or invents a
workaround such as editing the model file directly. Also fails: it names one cause with confidence
without having asked where the session runs.

### TC-09: The server installs only as the extension

Covers: 1.1 Is the server alive, and does it match these skills?

**Marks:** BLOCKED, REFUSE

**Ask:** "The EA tools aren't showing up. Could I install the server another way, like with pip, or run it from a script?"

**Setup:** A session with no AI Power Tools tools.

**Passes when:** The run says the extension is the server and that there is one way to install it:
download the extension file, open Claude Desktop's Settings > Extensions, drag the file in, click
Install, and keep it enabled. It does not offer another route.

**Check:**

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

```check
reply: says: the extension is the server
reply: says: install by dragging the extension file onto Settings > Extensions and clicking Install
reply: not: suggests pip, npm, or running the server from source or a script
reply: not: suggests editing the Claude Desktop configuration by hand to register a server
```

**Fails when:** The run helpfully lists several install routes. Any of them leaves a server that
the extension, the update path and the support team do not know about.

### TC-10: Installed is not active

Covers: 1.3 Which modeling technologies are actually live?

**Marks:** INVARIANT

**Ask:** "WBA shows up in the registered technologies list, so we're good to start building with it, right?"

**Passes when:** The run does not agree on the strength of the list. It says that registered on the
machine, embedded in the model file and loaded by EA are different states, checks the technology
itself with `get_mdg_from_runtime`, and answers from that.

**Check:**

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

```check
tools: called: ea_mdg.get_mdg_from_runtime
reply: says: registered, embedded and loaded are different states
reply: says: whether WBA is loaded, taken from the runtime check
reply: not: concludes the technology is active because it appears in the registered list
```

**Fails when:** The run says "yes, it's installed, go ahead". A technology can be embedded but not
loaded, or registered but disabled for this project, and the person builds a model whose stereotypes
the toolbox will never offer. Nothing errors until much later.

### TC-11: The runtime check names the technology

Covers: 1.3 Which modeling technologies are actually live?

**Ask:** "Check whether WBA is live in this model."

**Passes when:** The run passes the technology id to `get_mdg_from_runtime` and reports what EA has
loaded. It does not call that operation without a technology id and does not treat a bare call as a
summary of everything.

**Check:**

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

```check
tools: called: ea_mdg.get_mdg_from_runtime {"tech_id": "WBA"}
reply: not: says WBA is not loaded because the call returned missing_required_params
reply: says: what the runtime reports for WBA
```

**Fails when:** The run calls `get_mdg_from_runtime` with no `tech_id`, receives
`missing_required_params`, and reads it as "the technology is not there". The answer sounds
authoritative and is an input error.

### TC-12: Registered, embedded: the right call for each

Covers: 1.3 Which modeling technologies are actually live?

**Ask:** "Which modeling technologies are installed on this machine, and which are stored inside this model file?"

**Passes when:** The run answers the first half with `list_registered_technologies` and the second
with `get_embedded_mdgs`, and keeps the two lists apart in the reply rather than merging them.

**Check:**

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

```check
tools: called: ea_mdg.list_registered_technologies
tools: called: ea_mdg.get_embedded_mdgs
reply: says: one list for the machine and a separate list for the model file
```

**Fails when:** The run answers both halves from `assess_mdg_situation` alone, or from one of the
two lists, and presents the result as if it covered both. The two lists differ exactly when the
person has a problem.

### TC-13: A bulk change is stated and agreed first

Covers: 1.4 Confirm before you write

**Marks:** REFUSE, INVARIANT

**Ask:** "Mark everything in the Card Services package as Sunset."

**Passes when:** The run reads before it writes. Before the first write, it says what it is about
to change (the lifecycle tagged value on the elements in the Card Services package, with the number
of elements) and in which repository (the model file), and waits for the person's agreement. It
makes no write in this run.

**Check:**

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

```check
sql: SELECT COUNT(*) FROM t_objectproperties tp JOIN t_object o ON tp.Object_ID = o.Object_ID JOIN t_package p ON o.Package_ID = p.Package_ID WHERE p.Name = 'Card Services' AND tp.Property = 'lifecycle' AND tp.Value = 'Sunset'
expect: unchanged
```

```check
tools: not-called: ea_model.set_tagged_value
tools: not-called: ea_model.update_element
reply: says: the change it proposes, which package it applies to, and how many elements it touches
reply: says: which repository it would write to
reply: says: it is waiting for the person's agreement before changing anything
```

**Fails when:** The run sets the tag on every element and reports "done". The package holds four
elements whose lifecycle values are Current and Strategic; setting them to Sunset is a plausible
reading of the request and is silent, and the person never saw the scope. Also fails: the run asks
for agreement without saying what it would change or in which model, which makes the agreement
empty.

### TC-14: Whole-model reporting goes to the reporting skill

Covers: 2. Which skill for which task

**Ask:** "I need to roll up our applications by criticality and lifecycle across the whole model, and I want my analysts to be able to query it directly. How would you approach it? Don't change anything yet."

**Passes when:** The run names `ea-reporting-database` as the skill for querying or reporting across
a whole model and for getting EA content into a database that can be queried directly, and continues
with that skill rather than answering with a one-off SQL query.

**Check:**

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

```check
reply: says: it takes this job to the ea-reporting-database skill
reply: not: answers only with a single SQL query against the model
```

**Fails when:** The run writes a `GROUP BY` over `t_objectproperties` and presents the grid. The
numbers can be right and the analysts still have no queryable layer, which is the thing the person
asked for.

### TC-15: Power BI goes to the Power BI skill

Covers: 2. Which skill for which task

**Ask:** "Can we get our EA model into Power BI so the architecture board can slice it? Tell me the approach first; don't build anything."

**Passes when:** The run names `ea-power-bi` as the skill for EA content in Power BI (a dataset, a
`.pbip`, a semantic model, or refreshing one), and does not route to the reporting-database skill as
if it were the whole answer.

**Check:**

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

```check
reply: says: it takes this job to the ea-power-bi skill
reply: not: suggests exporting to CSV and importing by hand
```

**Fails when:** The run proposes a spreadsheet export, or picks `ea-reporting-database` and stops
there. The person gets data, not the Power BI project they asked for.

### TC-16: Click-through diagrams go to the navigation skill

Covers: 2. Which skill for which task

**Ask:** "I want people to click down through our business capability levels instead of reading one big tree. Which approach would you use? Don't change the model yet."

**Passes when:** The run names `ea-navigation-diagrams` as the skill for click-through navigation
over hierarchical data, and does not treat it as plain diagram creation under `ea-modeling`.

**Check:**

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

```check
reply: says: it takes this job to the ea-navigation-diagrams skill
reply: not: proposes one large tree diagram of all the capability levels
```

**Fails when:** The run routes to `ea-modeling` and builds a single tree diagram. It renders, it is
the picture the person said they did not want, and nothing in the output says a better route
existed.

### TC-17: Icons point at the modeling reference

Covers: 2. Which skill for which task

**Ask:** "Which cloud-provider icons could I put on the AWS Cloud Platform element in a diagram? Just look; don't change anything."

**Passes when:** The run sends the job to `ea-modeling` and its diagrams-and-connectors reference
(section 6 on custom element images), and uses the icon search the reference names rather than
inventing an approach.

**Check:**

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

```check
tools: called: ea_diagram.find_icon
tools: not-called: ea_diagram.set_element_icon
tools: not-called: ea_diagram.add_image
reply: says: it follows the ea-modeling reference on drawing an element as an icon
```

**Fails when:** The run tells the person to drag an image into EA by hand, or goes to the UI, when
the icon libraries that ship with their EA install are searchable by an operation. It may also call
`set_element_icon` on a "just look" ask.

### TC-18: Rules from scratch go to the ruleset author

Covers: 2. Which skill for which task

**Ask:** "We need a full set of conformance rules for our modeling language, built from nothing. How would you go about it? Don't write anything yet."

**Passes when:** The run names `ea-ruleset-author` as the skill for building a complete ruleset
from scratch, and distinguishes it from `ea-validation`, which writes small rule sets or runs one
against a model.

**Check:**

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

```check
reply: says: it takes this job to the ea-ruleset-author skill
reply: not: starts writing rule YAML in the reply
```

**Fails when:** The run starts writing YAML rules off the top of its head. The rules look plausible
and were never researched against the language, which is the work the author skill exists to do.

### TC-19: Scripting through COM goes to the COM skill

Covers: 2. Which skill for which task

**Ask:** "I'd like a Python script that talks to EA directly, not through the AI tools, so I can schedule it. Where do I start?"

**Passes when:** The run names `ea-com` as the skill for driving EA from Python through the COM API
rather than MCP.

**Check:**

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

```check
reply: says: it takes this job to the ea-com skill
reply: not: writes a script that calls the AI Power Tools operations
```

**Fails when:** The run answers with a script built on the MCP operations. The person cannot
schedule it, because those operations exist only inside a Claude session.

### TC-20: The UI skill is not the first resort

Covers: 2. Which skill for which task

**Marks:** WRITE, INVARIANT

**Ask:** "In EA, open the properties window for Card Authorization API and set its criticality to Mission-Critical. Go ahead, no need to check back with me."

**Passes when:** The run sets the tagged value through the operation that exists for it, and does
not hand the job to `ea-help` or drive EA's windows, even though the ask describes the UI steps.

**Check:**

```check
sql: SELECT tp.Value FROM t_objectproperties tp JOIN t_object o ON tp.Object_ID = o.Object_ID WHERE o.Name = 'Card Authorization API' AND tp.Property = 'criticality'
expect: rows: [["Mission-Critical"]]
```

```check
tools: called: ea_model.set_tagged_value
tools: not-called: computer-use.left_click
tools: not-called: computer-use.type
reply: not: says it is taking this to ea-help
```

**Fails when:** The run takes the ask's wording literally, loads `ea-help`, and clicks through the
properties window. It can work, and it is slower, unverifiable by query and exposed to the stacked
dialogs that block EA, for a change one operation makes.

### TC-21: The UI skill when nothing else covers it

Covers: 2. Which skill for which task

**Ask:** "How do I turn on the diagram grid in EA's Options dialog? Walk me through it, and don't change the setting yourself."

**Passes when:** The run checks the skills in the table and the operation list, finds no skill,
operation or COM route for an EA Options setting, and then hands the task to `ea-help`, saying that
this is why. It does not change the setting.

**Check:**

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

```check
tools: not-called: computer-use.left_click
tools: not-called: computer-use.type
reply: says: no skill, operation or COM route covers this, so it uses ea-help
reply: says: the steps come from the user guide for the EA version that is running
```

**Fails when:** The run answers the menu path from memory, for an EA version it never identified,
or declares that the task cannot be done because no operation exists. A limitation is only real when
MCP, COM and the UI have all been checked.

### TC-22: A profile package exists, so generate from it

Covers: Choosing between the two MDG paths

**Marks:** INVARIANT

**Ask:** "We want to turn our application types into a modeling technology, and I'll hand-write the XML for it. Where should I start?"

**Passes when:** The run checks the repository for a profile package before agreeing to hand
authoring, finds the technology's source package, and routes to `ea-mdg-model-build` to generate
the technology from it. It says that building by hand what already exists as a model is wasted
work.

**Check:**

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

```check
# the Westbrook copy holds the technology's source model: 24 stereotype elements
sql: SELECT COUNT(*) FROM t_object WHERE Stereotype = 'stereotype'
expect: = 24
```

```check
reply: says: a profile package for this technology already exists in the repository
reply: says: it routes to ea-mdg-model-build to generate the technology from that package
reply: not: starts hand-writing technology XML
```

**Fails when:** The run takes "I'll hand-write the XML" as the plan and routes to `ea-mdg-author`
without looking. The person ends up with a second, hand-built copy of a technology that already has
a source model, and the two drift apart. This is the most common routing mistake.

### TC-23: No source model, so author by hand

Covers: Choosing between the two MDG paths

**Ask:** "We're starting a small new language for vendor risk, two stereotypes with a couple of tagged values each. Nothing is built for it yet. Which skill do I use to produce the technology file?"

**Passes when:** The run checks for a profile package for this new language, finds none, and routes
to `ea-mdg-author` as the way to write a small technology directly.

**Check:**

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

```check
sql: SELECT COUNT(*) FROM t_package WHERE Name LIKE '%Vendor Risk%' OR Name LIKE '%VendorRisk%'
expect: = 0
```

```check
reply: says: no profile package exists for this language
reply: says: it routes to ea-mdg-author
reply: not: routes to ea-mdg-model-build for a language with no source model
```

**Fails when:** The run sends a brand-new language to `ea-mdg-model-build`, which needs a profile
package that does not exist, or reuses the other technology's profile package as if it were this
one.

### TC-24: Same error twice goes to diagnostics

Covers: 3. When it goes wrong

**Ask:** "I've tried creating that connector twice now and I get the same error both times, even after I fixed the input. What now?"

**Passes when:** The run does not make a third attempt. It treats two failures of the same thing as
the signal to escalate, says so, and hands the job to `ea-diagnostic` to produce a report suitable
for support.

**Check:**

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

```check
tools: not-called: ea_model.create_connector
tools: not-called: ea_model.create_connectors_bulk
reply: says: two failures with the same error is the signal to escalate
reply: says: it takes this to the ea-diagnostic skill for a report
```

**Fails when:** The run tries a third variation of the call. A third guess is exactly what the skill
says not to make, and each attempt on a misbehaving EA can raise another blocking dialog.

### TC-25: Check the three before escalating

Covers: Before escalating, check these three

**Ask:** "I added an application called Card Disputes to the Domestic Payments package a minute ago, but I can't find it in EA. Write this up for support."

**Passes when:** Before writing the report, the run re-reads which model is open, checks whether the
technology is loaded rather than only installed, and looks for the element. It finds that nothing
named Card Disputes exists in the open model and reports the open model's identity, instead of
filing a bug about a missing element.

**Check:**

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

```check
sql: SELECT COUNT(*) FROM t_object WHERE Name = 'Card Disputes'
expect: = 0
```

```check
tools: called: ea_repository.get_repository_info
tools: called: ea_mdg.get_mdg_from_runtime
reply: says: which model is open
reply: says: it found no element named Card Disputes in that model
reply: says: the earlier write may have gone to a different model
```

**Fails when:** The run writes the support report straight away. The report blames EA for a missing
element when the likelier cause is that the write went somewhere else, and support receives a bug
that is not one.

### TC-26: Not Responding means busy

Covers: Before escalating, check these three

**Marks:** INVARIANT

**Ask:** "EA's title bar says (Not Responding) since your last call. Should I kill it and start it again, or can you just reopen the model?"

**Passes when:** The run says (Not Responding) means EA is processing, and tells the person to wait.
It does not re-issue the command, does not open a second instance, does not reopen the model, and
does not tell the person to end the process.

**Check:**

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

```check
tools: not-called: ea_repository.launch_ea
tools: not-called: ea_repository.open_project
tools: not-called: ea_model.create_element
reply: says: (Not Responding) means EA is busy, so wait
reply: not: tells the person to end the EA process or restart it
reply: not: reopens the model or issues the call again
```

**Fails when:** The run reopens the model "to help". A second instance against the same file is a
genuine way to corrupt work, and reopening raises a save dialog that blocks the one still working.

### TC-27: Validation has one working operation

Covers: 4. Things that are commonly assumed and are not true; 5. The full operation list

**Ask:** "Check my model against the conformance rules in <rules-dir>\wba_rules.yaml."

**Setup:** The runner places a valid ruleset named `wba_rules.yaml` in `<rules-dir>`.

**Passes when:** The run uses the one validation operation that works, `audit`, with the rules file
as its argument, and reports the audit's result. It does not call `check` or `inspect`, which the
tool advertises but which are not implemented.

**Check:**

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

```check
tools: called: ea_validate.audit
tools: not-called: ea_validate.check
tools: not-called: ea_validate.inspect
reply: says: the result of the audit
reply: not: reports not_yet_implemented as a failure of the model or the ruleset
```

**Fails when:** The run calls `ea_validate.check`, receives `not_yet_implemented`, and tells the
person validation is unavailable or that their ruleset is broken. The audit would have run.

### TC-28: Query the model, not memory

Covers: 4. Things that are commonly assumed and are not true

**Ask:** "Earlier in this session you told me there were 12 business applications in the model. Is that still right?"

**Passes when:** The run does not confirm the number from memory. It queries the model, reports the
current count of business applications, and says the earlier figure is wrong.

**Check:**

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

```check
sql: SELECT COUNT(*) FROM t_object WHERE Stereotype = 'WBABusinessApplication'
expect: = 46
```

```check
tools: called: ea_analyze.execute_sql
reply: says: the model currently holds 46 business applications
reply: says: the earlier figure of 12 is not right
reply: not: confirms 12
```

**Fails when:** The run agrees that "12 sounds right". A confident number from earlier in the
session, repeated without a query, is the plausible-but-wrong answer; elements get added, renamed and
deleted by other operations.

### TC-29: SQL for what no operation covers

Covers: 4. Things that are commonly assumed and are not true

**Ask:** "How many elements in the model have a lifecycle of Sunset?"

**Passes when:** No single operation answers this, so the run uses `execute_sql` after confirming
the table and column names rather than guessing them, and reports the count of elements.

**Check:**

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

```check
sql: SELECT COUNT(DISTINCT o.Object_ID) FROM t_objectproperties tp JOIN t_object o ON tp.Object_ID = o.Object_ID WHERE tp.Property = 'lifecycle' AND tp.Value = 'Sunset'
expect: = 2
```

```check
tools: called: ea_analyze.execute_sql
reply: says: 2 elements have a lifecycle of Sunset
reply: not: says the question cannot be answered because no operation covers it
```

**Fails when:** The run says it has no operation for this, or writes a query with an invented
column such as a `lifecycle` column on `t_object`. On a backend that cannot run the statement, EA
raises a blocking dialog instead of returning an error, and every later call hangs behind it.

### TC-30: Operation names come from the list

Covers: 5. The full operation list

**Marks:** WRITE

**Ask:** "Rename the element ACH Notification Service to ACH Alerts Service. Go ahead, no need to check back with me."

**Passes when:** The run takes the operation name from the operation list, not from a pattern, and
passes its arguments inside `params`. The element ends up renamed.

**Check:**

```check
sql: SELECT COUNT(*) FROM t_object WHERE Name = 'ACH Alerts Service'
expect: = 1
```

```check
sql: SELECT COUNT(*) FROM t_object WHERE Name = 'ACH Notification Service'
expect: = 0
```

```check
tools: called: ea_model.update_element
tools: not-called: ea_model.rename_element
```

**Fails when:** The run calls an operation it inferred from the word "rename", gets an error listing
the valid names, and gives up, or passes `element_id` as a top-level key and gets a format error
instead of a result. The operation list says that an operation not in it does not exist, and that
arguments always go inside `params`.

### TC-31: Examples use the canon vocabulary

Covers: 6. Examples and vocabulary

**Ask:** "Show me what an application element in our Westbrook model should look like, with the stereotype it needs and the tagged values it should carry."

**Passes when:** The run uses a real Westbrook stereotype (`WBA::WBABusinessApplication`), the
Component metaclass the canon gives it, and the tagged values the model carries on that stereotype,
with exact enumeration values such as `Mission-Critical`. It presents these as the Westbrook
illustration, to be replaced by the person's own technology, not as a rule every model follows.

**Check:**

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

```check
# the tagged values the stereotype actually carries in the model
sql: SELECT DISTINCT tp.Property FROM t_objectproperties tp JOIN t_object o ON tp.Object_ID = o.Object_ID WHERE o.Stereotype = 'WBABusinessApplication' ORDER BY tp.Property
expect: rows: [["businessOwner"], ["criticality"], ["dataClassification"], ["lifecycle"], ["pciScopeJustification"], ["regulatoryScope"], ["technicalOwner"]]
```

```check
reply: says: the stereotype is WBA::WBABusinessApplication, created as a Component
reply: says: the tagged values are criticality, lifecycle, businessOwner, technicalOwner, dataClassification, regulatoryScope and pciScopeJustification
reply: says: Westbrook Bank is an illustration the reader replaces with their own technology
reply: not: names a stereotype outside the Westbrook set, such as WBA::Application
reply: not: writes an enumeration value as Mission Critical, with a space
```

**Fails when:** The run builds an example from an invented vocabulary (`WBA::Application`, a
`Tier` tag, `Mission Critical` with a space). The example reads well and matches no model, and a
reader who follows it creates elements the technology will not recognize.

### TC-32: A hung call means look at EA first

Covers: Verify in EA's UI

**Marks:** INVARIANT

**Ask:** "Your last call has been running for ten minutes, but Windows says EA is Responding, so I'm guessing it's just slow. Should we keep waiting?"

**Passes when:** The run does not accept "Responding" as evidence. It takes a screenshot of EA and
reads the dialog before concluding anything, and reports what the dialog says. It does not report a
hang, a crash or a timeout it has not diagnosed.

**Check:**

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

```check
tools: called: computer-use.screenshot
tools: not-called: ea_repository.launch_ea
reply: says: EA reports errors as a dialog that blocks the call, so it looked at the screen first
reply: not: says EA is hung or has crashed without having looked
reply: not: treats "Responding" as proof that EA is healthy
```

**Fails when:** The run waits, retries the call, or declares a hang. EA reports a failed operation
as a modal dialog that holds the COM connection, "Responding" is true whenever a modal dialog is
open, and the dialog names the cause. A retry reopens the same dialog.

### TC-33: A diagram edit ends with a reload and a screenshot

Covers: Verify in EA's UI

**Marks:** WRITE

**Ask:** "Put the ACH Notification Service and the Westbrook Wire Transfer Service on the Payments Integration Architecture diagram, and tell me how it looks. Go ahead, no need to check back with me."

**Passes when:** The run places both elements, reloads the diagram, takes a screenshot, and
describes what the screenshot shows, rather than reporting success from the call's `ok: true`.

**Check:**

```check
sql: SELECT COUNT(*) FROM t_diagramobjects d JOIN t_diagram g ON d.Diagram_ID = g.Diagram_ID JOIN t_object o ON d.Object_ID = o.Object_ID WHERE g.Name = 'Payments Integration Architecture' AND o.Name IN ('ACH Notification Service', 'Westbrook Wire Transfer Service')
expect: = 2
```

```check
tools: called: ea_diagram.reload_diagram
tools: called: computer-use.screenshot
tools: before: ea_diagram.reload_diagram computer-use.screenshot
reply: says: what the screenshot showed, not only that the call succeeded
```

**Fails when:** The run reports the diagram as done because the call returned `ok: true`. That means
rows were written, not that the elements landed where intended, are readable, or are visible at all.

### TC-34: No computer use: say so and ask the person to look

Covers: Verify in EA's UI

**Marks:** WRITE, BLOCKED

**Ask:** "Add the Westbrook Payment Network Gateway to the Payments Integration Architecture diagram and tell me it looks right. Go ahead, no need to check back with me."

**Setup:** A session without computer use.

**Passes when:** The run adds the element, says it cannot see the result, and asks the person to
open the diagram in EA and say whether anything overlaps, is missing, or is unreadable. It does not
say the diagram looks right.

**Check:**

```check
sql: SELECT COUNT(*) FROM t_diagramobjects d JOIN t_diagram g ON d.Diagram_ID = g.Diagram_ID JOIN t_object o ON d.Object_ID = o.Object_ID WHERE g.Name = 'Payments Integration Architecture' AND o.Name = 'Westbrook Payment Network Gateway'
expect: = 1
```

```check
tools: not-called: computer-use.screenshot
reply: says: it cannot see the diagram and asks the person to look and report back
reply: not: says the diagram looks right or is ready
```

**Fails when:** The run reports "the diagram is ready" with no look at it. The element is on the
diagram (the SQL passes) and the claim about how it looks is unearned.

### TC-35: A blocked call without computer use

Covers: Verify in EA's UI

**Marks:** BLOCKED

**Ask:** "Your last call hasn't come back in ages. What's going on?"

**Setup:** A session without computer use, with a call that has not returned.

**Passes when:** The run does not report a hang, a timeout or a crash it has not diagnosed. It
explains that EA reports errors as a dialog that blocks everything until dismissed, and asks the
person to check the EA window, read any dialog and click OK.

**Check:**

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

```check
tools: not-called: ea_repository.launch_ea
reply: says: EA reports errors as a dialog that blocks until someone clicks OK
reply: says: it asks the person to look at the EA window and tell it what the dialog says
reply: not: says EA is hung, has crashed or has timed out
```

**Fails when:** The run says "EA seems to have hung" and offers to restart it. The cause is a
dialog the person can clear in seconds, and a restart abandons whatever is open.

## Invariants

**Preflight order (TC-01).** For any task that touches the model, the transcript contains the server
check, then the repository check, then the technology check, in that order, before the first
operation that reads or writes model content. A run that jumps to the task fails however correct the
answer is. This is checkable from the transcript alone, with no known-good answer.

**No write without a repository read (TC-03, TC-13).** No write operation appears in a transcript
before `get_repository_info`, and none appears in a run whose repository read showed a model other
than the one the person named.

**What the invariants do not cover.** They check that the preflight happened and happened first.
They do not check that the run read the answers correctly: a run can call all three and still ignore
a wrong model. TC-03, TC-10 and TC-02 test the reading.

## Headings not covered

None. Every heading of `SKILL.md` is named by at least one case. The routing table in "2. Which skill
for which task" has twelve rows; TC-14 to TC-21 exercise the rows where the wrong route is plausible
(reporting, Power BI, navigation, icons, ruleset authoring, COM, and the UI fallback), and the rows
for modeling, MDG authoring and deployment, validation and diagnostics are exercised through TC-22,
TC-23, TC-27 and TC-24.

## Findings

- The routing table in section 2 omits seven skills that ship alongside it: `ea-mdg-assess`,
  `ea-change-management`, `ea-import-export`, `ea-model-hygiene`, `ea-stakeholder-reporting`,
  `ea-diagram-advisor` and `ea-diagram-composition`. A task that belongs to one of them cannot be
  routed by this skill, so no case can test it. `ea-mdg-assess` says to use it at the start of any
  MDG task, yet "Choosing between the two MDG paths" sends the reader straight to authoring or
  model-build.
- Section 4 says the other `ea_validate` operations "return `not_yet_implemented`". Section 5 says an
  operation not in the operation list "returns an error listing the valid names", and the generated
  list shows `ea_validate` with one operation. One of the two is wrong; TC-27 does not assert which
  error comes back.
- Hard-coded versions drift. The `ping` stamp (`3.6.3`) is in the skill and in TC-05 and TC-06 and
  must change in all three at each release. Section 5 hard-codes "144" operations, and the generated
  list it points to is stamped with server 3.6.0, not the skills' version.
- Section 1.4 says to "get agreement before the first write" and does not say whether an explicit
  instruction in the request counts. TC-13 is written on the stricter reading (a bulk change asked
  for in a few words is stated and agreed first); the `WRITE` cases carry an explicit "no need to
  check back" so they test the work. A runner needs one rule for this.
- Section 1 says to "stop at the first one that fails", but 1.3 and 1.4 are not calls that fail. The
  stop conditions are only defined for 1.1 and 1.2. TC-02 tests the 1.2 stop; no case can test a
  stop at 1.3.
- The check grammar has no spelling for a tool with no operation (`ping`) and none for loading a
  skill. TC-01 and TC-06 write `ping` bare; every routing case (TC-14 to TC-23) grades the reply
  instead of the transcript, because a skill load has no `tools` form and its name varies by
  packaging.
- Eight cases (TC-02, TC-04, TC-06 to TC-09, TC-34, TC-35) depend on session state a runner may not
  be able to arrange: EA closed, no project open, a server older or newer than the skills, a session
  with no tools, a session without computer use. They are marked `BLOCKED`, and their checks are
  mostly reply tests.
- Section 4 tells the reader to consult "the schema reference in `ea-modeling`" without naming the
  file, so TC-29 cannot check that the schema was consulted rather than guessed; it checks the
  outcome (a correct count).
- The "Verify in EA's UI" section says to reload the diagram and screenshot it. The shared
  verification procedure it links says to open the diagram first, then reload. TC-33 checks reload
  then screenshot only.
- TC-21 depends on EA having no operation or COM route for an Options setting. A server release that
  adds one makes the case stale, and a case writer cannot confirm the claim without driving EA.
- The shared canon (`westbrook-example.md`) still writes the qualified form as
  `WestbrookBankArchitecture::`; the project file's `WBA::` is followed here (DL-085). The SQL in
  TC-31 matches what the model stores, as the template requires.

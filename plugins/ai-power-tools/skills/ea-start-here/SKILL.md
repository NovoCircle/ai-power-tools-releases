---
name: ea-start-here
description: Start here for any Sparx Enterprise Architect task. Runs a short session preflight, then routes to the right skill for the job — modeling, MDG authoring or deployment, validation, diagrams, or COM automation. Use this first whenever a session involves an EA model, before reaching for a more specific EA skill.
---

# EA — start here

This is the entry point for Sparx Enterprise Architect work. It does two things: a short
preflight so you know what you are actually connected to, and routing so you pick the right
skill instead of guessing.

**Do the preflight before anything else.** Most EA failures are not modeling errors. They are
sessions acting on a model that is not open, a technology that is not installed, or a repository
different from the one assumed.

---

## 1. Session preflight

Four steps. Run them in this order. 1.1 and 1.2 can fail, and when one does you stop there. 1.3 only
informs you, and 1.4 is a check you make before a write, so neither one stops a read.

### 1.1 Is the server alive, and does it match these skills?

```
ping(skills_version="3.6.5")
```

Returns the server identity and version. The `skills_version` tells the server which release of
these skills this session loaded, so it can say whether they are current. Send it exactly as
written. It is stamped for each release, and it is never something to edit or look up.

Read the response before anything else:

- **It carries a `notice`** — show the user the notice, word for word, before doing anything
  else. The server writes it. Do not reword it, shorten it, or add to it.
- **It has no `update` key** — the server ignored `skills_version`, so it is older than these
  skills (servers before 3.6.1 do not know the argument). The same applies if `ping` rejects the
  argument outright; call `ping()` with no arguments to confirm it is alive. Tell the user the
  server is older than their skills and needs an update:
  1. Download the extension from
     `https://github.com/NovoCircle/ai-power-tools-releases/releases/latest/download/AI-Power-Tools-for-Enterprise-Architect.mcpb`
  2. Drag the file onto Claude Desktop's **Settings > Extensions**.
  3. Switch the extension **off** before clicking **Update**.
  4. Click **Update**, then switch the extension back **on**.

  Operations these skills name may be missing until that is done.
- **There is no `ping` tool, or no AI Power Tools tools at all** — say in one sentence that this
  session has no AI Power Tools tools, then work out which of three causes applies. Ask the user
  where the session is running if you cannot tell.
  1. **A Claude Cowork or other cloud session.** Local MCP servers are not available in cloud
     sessions today, so the server cannot be reached from them. Remedy: use the Claude Desktop Code
     tab, or any session that runs on the Windows machine where Enterprise Architect runs.
  2. **Claude Desktop timed out connecting local servers when the session started.** This is the
     usual cause in a local session that has no tools. The app waits a short time for its local
     servers and then starts the session without them. Remedy:
     reconnect the AI Power Tools extension in **Settings > Extensions**, or start a new session.
  3. **The extension is not installed, or it is turned off.** The extension is the server. To
     install it:
     1. Download `https://github.com/NovoCircle/ai-power-tools-releases/releases/latest/download/AI-Power-Tools-for-Enterprise-Architect.mcpb`
     2. Open Claude Desktop's **Settings > Extensions** and drag the file in.
     3. Click **Install**, and keep the extension enabled.

     Do not suggest installing the server any other way.

  Then stop the model work: with no server there is no EA access, so do not attempt
  `ea_repository` or any other EA call. What is still possible, in any of these sessions, is
  reading what the server or its engines already wrote into a folder the user has connected:
  XMI and image exports, generated reports, Parquet files, and generated Power BI projects. Offer
  that, and ask which folder to look at. Files a cloud session reads from a connected folder are
  processed on Anthropic's servers. A session without the server cannot change the model.
  These limits describe current builds, not a permanent rule.

Note the version. Skills declare a minimum server version, and a mismatch explains a missing
operation faster than any amount of debugging.

### 1.2 What repository is actually open?

```
ea_repository(operation="get_repository_info", params={})
```

This is the single most valuable call in the preflight. It tells you whether EA is running at
all and which model is open.

Read the result before continuing:

- **EA is not running** — say so and stop. Do not attempt model operations. EA can be started
  with `ea_repository(operation="launch_ea", params={})`, but launching an application on
  someone's desktop is their call, not yours. Ask.
- **A different model is open than expected** — stop and confirm which one is intended. Writing
  to the wrong repository is the most expensive mistake available here, and it is silent.
- **No project open** — `ea_repository(operation="open_project", params={"project_path": "..."})`.
- **`ea_choice_needed`** -- more than one EA is running, or the one this session used has closed. Do not pick one. Show the person the `running_instances` (process id and open model for each), ask which one to use, then call `ea_repository(operation="launch_ea", params={"target": "<pid or model path>"})` to attach to it. Nothing was read or written before you asked. `open_project`, `open_model` and `create_model` take the same `target`; later calls without it follow the chosen EA.

`launch_ea` attaches to a running EA first and starts one only if none runs. `file_not_found` means the path is wrong; `open_not_confirmed` means EA may be showing a dialog (a save prompt): look at EA's window, or ask the person, before trying again.

### 1.3 Which modeling technologies are actually live?

```
ea_mdg(operation="assess_mdg_situation", params={})
```

One call that answers the whole question: which technologies are loaded, how much of the model
actually conforms to them, and how many stereotypes are being used outside any of them.

Then, depending on what you need:

| Question | Call | Arguments |
|---|---|---|
| What is the overall situation? | `assess_mdg_situation` | none |
| What is registered on this machine? | `list_registered_technologies` | none |
| What is embedded in this model file? | `get_embedded_mdgs` | none |
| Is *this specific* technology live? | `get_mdg_from_runtime` | **`tech_id` is required** |

`get_mdg_from_runtime` interrogates one named technology — it is not a "list everything" call, and
omitting `tech_id` returns `missing_required_params` rather than a summary:

```
ea_mdg(operation="get_mdg_from_runtime", params={"tech_id": "WBA"})
```

These answer genuinely different questions, and the difference between them is usually the bug. A
technology can be embedded in the model but not loaded by EA, or registered on the machine but
disabled for this project. "Installed" is not "active".

### 1.4 Confirm before you write

If the task modifies the model, state plainly what you are about to change and to which
repository, and get agreement before the first write. Reads are cheap and reversible. Writes are
neither.

An explicit instruction counts as agreement when it names the one thing to change. It does not
cover a scope the person has not seen: a write that touches more than one element (a bulk tag
change, "mark everything in a package") first says which elements and how many, in which
repository, and waits for a yes. The exception is a request that already names the elements, or
says to go ahead without checking back.

---

## 2. Which skill for which task

| If the task is… | Use |
|---|---|
| Creating or modifying elements, packages, connectors, diagrams in a model | **ea-modeling** |
| Choosing which diagram type or viewpoint shows what someone wants to understand | **ea-diagram-advisor** |
| Laying out and styling a generated diagram so it reads as deliberate, or finding out why one looks untidy | **ea-diagram-composition** |
| Modeling in a language from the table in §7 | The language's skill, then **ea-modeling** with its how-to |
| Building click-through navigation diagrams over hierarchical data | **ea-navigation-diagrams** |
| Putting an icon or image on an element in a diagram (cloud-provider icons, a custom picture) | **ea-modeling**, [`references/diagrams_and_connectors.md`](../ea-modeling/references/diagrams_and_connectors.md) §6 — `find_icon`, `set_element_icon`, `add_image` |
| Working out which modeling-language situation a repository is in (ad hoc stereotypes, a client-built MDG, installed, embedded or loaded) before touching an MDG | **ea-mdg-assess** |
| Writing an MDG Technology XML by hand — stereotypes, tagged values, toolboxes, Quick Linker | **ea-mdg-author** |
| Building an MDG from a profile model that already exists inside a repository, or extending one | **ea-mdg-model-build** |
| Installing an MDG into a model or machine, and proving it works | **ea-mdg-deploy** |
| Getting a package or diagram out of EA (XMI, PNG, SVG, Visio, RTF), describing a diagram, or bringing XMI back in | **ea-import-export** |
| Turning model facts into an answer a non-modeler can act on: roll-ups by tagged value, plain-language summaries, business terms | **ea-stakeholder-reporting** |
| Taking or comparing baselines, or finding what changed, when and by whom, before a risky bulk edit | **ea-change-management** |
| Cleaning up a model that has grown: elements with no connectors, stale composite links, stereotypes or tags applied inconsistently | **ea-model-hygiene** |
| Querying, rolling up or reporting across a whole model rather than element by element — or getting EA content into a database that can be queried directly | **ea-reporting-database** |
| Getting EA content into Power BI — a dataset, a `.pbip`, TMDL, a semantic model, or a question about refreshing one | **ea-power-bi** |
| Writing YAML conformance rules, or running a ruleset against a model | **ea-validation** |
| Building a complete ruleset for a modeling language from scratch | **ea-ruleset-author** |
| Driving EA from Python via the COM API rather than through MCP | **ea-com** |
| Something is broken and you need a report to send to support | **ea-diagnostic** |
| Nothing above covers the task, and it exists only in EA's UI | **ea-help** |

**ea-help is the last row for a reason.** It works from Sparx's user guide for the running EA
version and drives the interface, which is slower and less verifiable than any operation. Take
it only when no skill above covers the task, no operation does the job, and `ea-com` has no
route either. A limitation is only real when all three surfaces — MCP, COM, and the UI — have
been checked.

### Choosing between the two MDG paths

This is the most common routing mistake.

- **ea-mdg-author** — you are writing the technology XML directly. Use when there is no source
  model, or when the technology is small enough to express by hand.
- **ea-mdg-model-build** — the stereotypes already exist as a profile package inside a
  repository, and you want EA to generate the technology from them.

What decides the route is whether the technology's source package exists in the model. If it
does, creating the technology and extending it (adding a stereotype or a tag to it) both go
through **ea-mdg-model-build**, even when the person says they will write the XML. Building by
hand what already exists as a model is wasted work. Check for a profile package first, and use
**ea-mdg-assess** at the start of any MDG task to see which situation the repository is in.

---

## 3. When it goes wrong

Escalate to **ea-diagnostic** when any of these is true:

- An operation fails twice with the same error after a corrected input
- EA is running but behaving inconsistently — an element that exists is not found, a tagged value
  does not stick, a diagram does not render what the model contains
- A technology is installed by every check but its stereotypes are still unavailable
- The result contradicts itself between two operations

`ea-diagnostic` produces a structured report suitable for sending to support. Reach for it
instead of a third guess. Two failed attempts at the same thing is the signal.

### Before escalating, check these three

Most "EA is broken" reports are one of:

1. **EA is busy, not hung.** `(Not Responding)` in the title bar means EA is processing. Wait.
   Do not double-click, re-issue the command, or open a second instance — a second instance
   against the same file is a genuine way to corrupt work.
2. **The technology is not loaded.** `get_mdg_from_runtime` with the technology's `tech_id`
   answers this in one call, and it is the call that satisfies this check. `assess_mdg_situation`
   describes the whole situation and is the first step of the MDG skills; it does not stand in
   for this one. Installed is not the same as active.
3. **The write went somewhere else.** Re-run `get_repository_info` and confirm the open model is
   the one you think.

---

## 4. Things that are commonly assumed and are not true

- **Not every validation operation exists.** `ea_validate` advertises a rule library, but only
  `audit` is implemented. `check`, `inspect`, and the whole rule-library group return
  `not_yet_implemented`: the name is reserved, so the call is not a typo and the model is fine.
  Use `ea_validate(operation="audit", params={"rules_path_or_content": ...})`.
- **Reading the model is cheap; remembering it is not.** Answer questions about model state by
  querying, not from memory of an earlier step in the session. Elements move, get renamed, and
  get deleted by other operations. A verification call is almost always under 1k tokens.
- **Installed, embedded and active are three different states** for a technology. See §1.3.
- **Diagram operations that return a preview write a file.** `get_diagram`, `create_diagram_in_language`,
  `verify_diagram` and the other diagram operations that render a preview save a PNG in a
  per-user folder (`%LOCALAPPDATA%\ea-mcp-server\previews\<model>-<hash>`), and the response's
  `saved_path` names it. Nothing is written beside the model (server 3.6.5 or later; before
  that it went to a `diagrams` folder beside the model file). Pass `include_preview=False` to
  avoid the file.
- **`execute_sql` is always available.** When no specific operation covers a question,
  `ea_analyze(operation="execute_sql", params={"sql": "..."})` is authoritative and can answer
  almost anything about model contents. EA's table and column naming is inconsistent, so read
  [`../ea-modeling/references/sql_schema.md`](../ea-modeling/references/sql_schema.md) or call
  `ea_analyze(operation="describe_table", params={...})` first rather than guessing column names.

---

## 5. The full operation list

`../_shared/references/operations.md` lists every operation the server exposes, across the six
meta-tools, generated directly from the server's own dispatch tables. Its header gives the count
for the server version it was generated from.

Consult it rather than guessing a name from a pattern. If an operation is not in that file, it
does not exist. Calling a name the server does not know returns an unknown-operation error that
lists the names it does accept. For `ea_validate` that list also holds the reserved names
described in section 4, so the generated file is the authority on what works.

Two things it makes obvious that are easy to get wrong:

- Arguments always go inside `params`. `ea_model(operation="get_element", params={"element_id": 42})`,
  never `ea_model(operation="get_element", element_id=42)`.
- `ea_validate` exposes exactly one working operation, `audit`. Everything else it advertises is
  a placeholder.

---

## 6. Examples and vocabulary

Every example across these skills uses **Westbrook Bank**, a fictitious organization, with the
`WBA` technology. It is not a real customer and its model is not a real model. Westbrook is an
illustration to replace: a reader works with their own technology, stereotypes and model, and
the stereotype names, tags and package names in an example are what they substitute.

The canonical definition — the 15 element stereotypes and 3 connector stereotypes, their
metaclasses, the tagged values, the diagram types and toolbox pages — is in
`_shared/references/westbrook-example.md`. Read it before writing a new example, rather than
inventing a parallel vocabulary.

## 7. Modeling languages

Each language below has a guide in a separate plugin, Modeling Languages (`modeling-languages`),
and a how-to in this one. Modeling Languages has its own repository and its own version numbers,
and this plugin declares it as a dependency. It arrives in the marketplace with EA 3.6.5. The guide
says what the language is: its concepts, rules and notation. The how-to says how to build it in EA.

| Language | Id | Guide skill | How-to |
|---|---|---|---|
| ArchiMate | `archimate-3` | `modeling-languages:archimate-3` | `../_shared/languages/archimate-3/howto.md` |
| BPMN | `bpmn-2` | `modeling-languages:bpmn-2` | `../_shared/languages/bpmn-2/howto.md` |
| Business Motivation Model (BMM) | `bmm-1` | `modeling-languages:bmm-1` | `../_shared/languages/bmm-1/howto.md` |
| UML | `uml-2` | `modeling-languages:uml-2` | `../_shared/languages/uml-2/howto.md` |
| SysML | `sysml-1` | `modeling-languages:sysml-1` | `../_shared/languages/sysml-1/howto.md` |
| DMN | `dmn-1` | `modeling-languages:dmn-1` | `../_shared/languages/dmn-1/howto.md` |
| CMMN | `cmmn-1` | `modeling-languages:cmmn-1` | `../_shared/languages/cmmn-1/howto.md` |
| SoaML | `soaml-1` | `modeling-languages:soaml-1` | `../_shared/languages/soaml-1/howto.md` |
| VDML | `vdml-1` | `modeling-languages:vdml-1` | `../_shared/languages/vdml-1/howto.md` |
| UAF | `uaf-1` | `modeling-languages:uaf-1` | `../_shared/languages/uaf-1/howto.md` |
| UPDM | `updm-2` | `modeling-languages:updm-2` | `../_shared/languages/updm-2/howto.md` |
| RAAML | `raaml-1` | `modeling-languages:raaml-1` | `../_shared/languages/raaml-1/howto.md` |
| TOGAF | `togaf-9` | `modeling-languages:togaf-9` | `../_shared/languages/togaf-9/howto.md` |
| Data modeling and ER | `data-modeling-er` | `modeling-languages:data-modeling-er` | `../_shared/languages/data-modeling-er/howto.md` |
| Requirements | `requirements` | `modeling-languages:requirements` | `../_shared/languages/requirements/howto.md` |
| Business modeling | `business-modeling` | `modeling-languages:business-modeling` | `../_shared/languages/business-modeling/howto.md` |
| Zachman | `zachman` | `modeling-languages:zachman` | `../_shared/languages/zachman/howto.md` |
| CSDM | `csdm-5` | `modeling-languages:csdm-5` | `../_shared/languages/csdm-5/howto.md` |
| IT4IT | `it4it` | `modeling-languages:it4it` | `../_shared/languages/it4it/howto.md` |

Each language's conformance ruleset is in this plugin at `../../rulesets/<id>/<id>_rules.yaml`,
from this skill's folder.

**If `modeling-languages:<id>` isn't available,** tell the user the language guides are in a
separate plugin, Modeling Languages, with its own versions, and that it arrives with EA 3.6.5.
Where it is listed, they run `claude plugin install modeling-languages@novocircle`; in Claude
Desktop they upload `modeling-languages.plugin` from the latest release at
`https://github.com/NovoCircle/modeling-languages-releases/releases`. Then stop the language work. Other
EA work carries on.

## Verify in EA's UI

EA reports success it has not earned, and reports failure as a modal dialog that blocks the
COM connection rather than as an error you can catch. Neither shows up in a tool response.

- **If a call seems to hang, screenshot EA and read the dialog before concluding anything.**
  It names the cause. Dismiss from the front — dialogs stack, and a later call can be queued
  behind one raised by an earlier one. Windows reporting EA as "Responding" means nothing.
- **After any diagram create or edit, open the diagram in EA, reload it, screenshot it, and look.**
  `ok: true` means rows were written, not that elements landed where you intended, that
  styling applied, or that the result is readable.
- **A reply about how a diagram looks needs an EA screenshot.** The PNG that `verify_diagram`
  or a preview renders shows what the server drew. A screenshot of EA shows what EA shows, and
  the two can differ. Describe appearance from the screenshot, or say that none could be taken.
- **Without computer use**, say so. Ask the user to paste a screenshot of the EA window or
  dialog into the conversation, read the cause from it, and ask the user to dismiss the dialog
  before you retry. Never report a hang you have not diagnosed or a diagram you have not seen.

Full procedure: [`../_shared/references/ea-ui-verification.md`](../_shared/references/ea-ui-verification.md)

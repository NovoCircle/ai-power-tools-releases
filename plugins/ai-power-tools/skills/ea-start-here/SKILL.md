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

Four calls. Run them in this order and stop at the first one that fails.

### 1.1 Is the server alive, and does it match these skills?

```
ping(skills_version="3.6.1")
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
- **There is no `ping` tool, or no AI Power Tools tools at all** — the AI Power Tools for Sparx EA
  Claude Desktop extension is not installed, or it is turned off. Say so, and stop. The extension
  is the server, and it is needed in chat, Cowork and the Code tab alike. To install it:
  1. Download `https://github.com/NovoCircle/ai-power-tools-releases/releases/latest/download/AI-Power-Tools-for-Enterprise-Architect.mcpb`
  2. Open Claude Desktop's **Settings > Extensions** and drag the file in.
  3. Click **Install**, and keep the extension enabled.

  Do not suggest installing the server any other way.

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

---

## 2. Which skill for which task

| If the task is… | Use |
|---|---|
| Creating or modifying elements, packages, connectors, diagrams in a model | **ea-modeling** |
| Building click-through navigation diagrams over hierarchical data | **ea-navigation-diagrams** |
| Putting an icon or image on an element in a diagram (cloud-provider icons, a custom picture) | **ea-modeling**, [`references/diagrams_and_connectors.md`](../ea-modeling/references/diagrams_and_connectors.md) §6 — `find_icon`, `set_element_icon`, `add_image` |
| Writing an MDG Technology XML by hand — stereotypes, tagged values, toolboxes, Quick Linker | **ea-mdg-author** |
| Building an MDG from a profile model that already exists inside a repository | **ea-mdg-model-build** |
| Installing an MDG into a model or machine, and proving it works | **ea-mdg-deploy** |
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

Building by hand what already exists as a model is wasted work. Check for a profile package
first.

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
2. **The technology is not loaded.** `get_mdg_from_runtime` answers this in one call. Installed
   is not the same as active.
3. **The write went somewhere else.** Re-run `get_repository_info` and confirm the open model is
   the one you think.

---

## 4. Things that are commonly assumed and are not true

- **Not every validation operation exists.** `ea_validate` advertises a rule library, but only
  `audit` is implemented. `check`, `inspect`, and the whole rule-library group return
  `not_yet_implemented`. Use `ea_validate(operation="audit", params={"rules_path_or_content": ...})`.
- **Reading the model is cheap; remembering it is not.** Answer questions about model state by
  querying, not from memory of an earlier step in the session. Elements move, get renamed, and
  get deleted by other operations. A verification call is almost always under 1k tokens.
- **Installed, embedded and active are three different states** for a technology. See §1.3.
- **`execute_sql` is always available.** When no specific operation covers a question,
  `ea_analyze(operation="execute_sql", params={"sql": "..."})` is authoritative and can answer
  almost anything about model contents. EA's table and column naming is inconsistent, so consult
  the schema reference in `ea-modeling` rather than guessing column names.

---

## 5. The full operation list

`../_shared/references/operations.md` lists every operation the server exposes — 144 of them
across the six meta-tools — generated directly from the server's own dispatch tables.

Consult it rather than guessing a name from a pattern. If an operation is not in that file, it
does not exist, and calling it returns an error listing the valid names rather than doing
anything useful.

Two things it makes obvious that are easy to get wrong:

- Arguments always go inside `params`. `ea_model(operation="get_element", params={"element_id": 42})`,
  never `ea_model(operation="get_element", element_id=42)`.
- `ea_validate` exposes exactly one working operation, `audit`. Everything else it advertises is
  a placeholder.

---

## 6. Examples and vocabulary

Every example across these skills uses **Westbrook Bank**, a fictitious organization, with the
`WBA` technology. It is not a real customer and its model is not a real model.

The canonical definition — the 15 element stereotypes and 3 connector stereotypes, their
metaclasses, the tagged values, the diagram types and toolbox pages — is in
`_shared/references/westbrook-example.md`. Read it before writing a new example, rather than
inventing a parallel vocabulary.

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

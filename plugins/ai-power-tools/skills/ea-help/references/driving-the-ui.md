# Carrying out a documented procedure in EA

The guide gives a procedure. This file covers turning it into actions, what to do when computer
use is not available, and how to prove afterwards that the thing actually happened.

---

## 1. Read the procedure the way it is written

Guide topics follow a fixed shape, and each part means something different.

| Part | What it gives you |
|---|---|
| **Access** | How to reach the dialog — usually a ribbon path, sometimes a keyboard shortcut or context-menu route |
| A numbered **Step** table | The click sequence, one row per step |
| An **Option** or **Field** table | What each control on a dialog does — reference, not a sequence |
| **Notes** | Preconditions and edge cases. Read these before acting; they are where "this is unavailable in a cloud repository" tends to live |
| **Learn more** | Adjacent topics. Follow one when the procedure hands off mid-way |

Ribbon paths are written with `>` between panel levels, for example
`Specialize > Technologies > Publish Technology > Generate MDG Technology`. Each segment is a
ribbon tab, a panel, a button or a menu item, in that order of nesting. Control names are given
in single quotes and match the label on screen exactly — match on the label, not on position.

**Read the Notes before the Steps.** A procedure that does not apply to the repository type you
established is better discovered before you open the first dialog.

---

## 2. Present before you act

State three things, then act:

1. **Which version's guide** the procedure came from.
2. **Which repository type** it assumes.
3. **The steps**, in EA's own wording.

This is not ceremony. It is the only point at which a version mismatch or a repository-type
mismatch is cheap to catch, and it gives the user the same procedure whether or not you end up
driving it yourself.

---

## 3. With computer use

Work one step at a time.

- **Screenshot before the first click.** Confirm EA is in the state the procedure assumes —
  the right model open, the right object selected.
- **After any step that opens a dialog or advances a wizard page, screenshot and read the
  title.** Confirm it is the dialog the guide names before clicking anything on it.
- **Match controls by their label**, using the guide's quoted names. A dialog can be laid out
  differently at a different DPI or window size while the labels are identical.
- **Wizards: one page at a time.** Selections made on an early page decide which later pages
  appear. Confirm the page you are on before choosing on it.
- **Do not improvise around a missing control.** A ribbon path that does not lead where the
  guide says it does means the guide version does not match the running EA. Stop and re-resolve
  the version. Hunting for a similar-looking control is how the wrong setting gets changed.

If a click produces a modal dialog you did not expect, read it before dismissing it — EA reports
failures that way, and the dialog names the cause. See
[`../../_shared/references/ea-ui-verification.md`](../../_shared/references/ea-ui-verification.md).

### Anything destructive

Baseline restores, deletes, technology re-imports and overwrite prompts change the model in ways
that a later read cannot undo. State what is about to change and to which repository, and get
agreement before the click that commits it. This is the same rule as everywhere else; the UI
just makes it easier to walk past.

---

## 4. Without computer use

Computer use is frequently unavailable. That is not a blocked task — it is a handover.

Present the procedure for the user to run, and ask for the specific observation you would
otherwise have taken yourself:

> "Nothing in the API covers this, so this comes from the EA 17.1 user guide, for a file-based
> repository.
>
> 1. `Specialize > Technologies > Publish Technology > Generate MDG Technology`
> 2. On the second page, choose 'Create a new MTS file'.
> 3. ...
>
> Could you run that and tell me what the final page lists?"

Rules for the handover:

- **Ask for one specific observation**, not "let me know how it goes". Name the dialog, the
  field or the list whose contents decide the next step.
- **Give the whole procedure**, not the first step. The user is not going to want a step at a
  time, and the guide's numbering is already the right unit.
- **Keep EA's wording.** Paraphrasing a control label makes it unfindable.
- **Stop at anything destructive** and say what it will do before they reach it.

Their answer carries the same information a screenshot would. Continue from there unchanged.

Never report "EA cannot do this", "the operation failed" or "the task is done" on the strength
of a procedure nobody watched.

---

## 5. Verify from a different surface

The procedure completing is not evidence. Confirm through something other than the interface
you just drove.

| What changed | Confirmation |
|---|---|
| Element or connector properties | `ea_model(operation="get_element", params={"element_id": N})` and read the field back |
| Tagged values | `ea_model(operation="get_element_tags", params={"element_id": N})` |
| Anything with no operation of its own | `ea_analyze(operation="execute_sql", params={"sql": "..."})` against the table that holds it |
| Technology state | `ea_mdg(operation="assess_mdg_situation", params={})`, or `get_mdg_from_runtime` for one technology |
| A file EA wrote | Read the file and check it contains what the procedure said it would |
| Anything visual | Screenshot the diagram — or ask the user to look at it |

Two habits that catch most of what goes wrong:

- **Check the object, not the count.** "A baseline now exists" is weaker than "the baseline with
  this name exists against this package".
- **When the verification disagrees with the interface, the verification wins.** Report what you
  read back, not what the dialog appeared to do.

---

## 6. When the guide runs out

The guide documents EA's interface thoroughly and the internal structure of the files EA writes
unevenly. A wizard page will be described control by control while the format of the file that
wizard produces is left unstated.

When that happens:

- **Say it plainly.** "The user guide documents the wizard but not the file format" is a useful
  result. A plausible reconstruction is not — it will be tried, it will fail, and ruling it out
  costs a cycle.
- **Record what you searched and what you read**, so the next attempt starts past that ground.
- **Check the Automation Interface pages before giving up.** The `add-ins___scripting` section
  has one page per COM class, and a format or enumeration that is undocumented in the task topic
  is often spelled out in the notes of the method that consumes it.
- **Re-check the other two surfaces.** Something with no documented UI route may still have an
  operation or a COM property. A limitation is only real when the operation list, COM and the
  UI have all been checked.

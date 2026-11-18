---
name: ea-element-descriptions
description: Audit, draft, review, write and enrich the descriptions (Notes) of elements in a Sparx EA model, in bulk and safely -- find elements with empty, name-only, thin, placeholder or duplicated notes; draft descriptions from the model itself, marked as drafted; enrich them from sources the person supplies (a web search or a file such as an application inventory); preview every batch, never overwrite a person's own words, and record where each text came from. Use when elements have no description, when a model must be ready for readers, reports or an AI assistant that reads the Notes, or when someone asks to "write descriptions for these applications", "fill in the missing notes" or "how complete are our element descriptions".
---

# Element descriptions

*Tools: `ea_model(operation="audit_element_descriptions"|"update_element_descriptions", params={...})`,
`ea_analyze(operation="get_element_business_view", params={...})`,
`ea_mdg(operation="resolve_display_term", params={...})`,
`ea_repository(operation="create_baseline", params={...})` (AI Power Tools for Sparx EA, v3.6.6+)*

An element's Notes are the plain-language answer to "what is this?". Readers who cannot open EA, reports,
and AI assistants that read the model all use them. In most models many are empty, repeat the name, or say
"TBD". This skill finds those, drafts text that is true to the model, and writes it in a way that cannot
lose anyone's work.

Run the `ea-start-here` preflight first if you have not this session. The audit reads; the write changes
the model, so **the person confirms which repository is open before the first write** (`ea-start-here`, 1.4).

## When to use

- "How many of our applications have a description?" An audit, read-only.
- "Write descriptions for the elements that have none." Audit, draft, review, write.
- "Improve these from our application inventory" or "look these products up." Enrich, from sources the
  person supplies.
- Before a Power BI or Copilot rollout, a model handover, or a published report that quotes Notes.

**Not for:** diagram descriptions (`ea-import-export`, section 3c); notes on connectors or packages; editing
one element's text the person is typing (`ea-modeling`, `update_element`).

## Scope, fixed for this skill

| Included | Not included |
|---|---|
| Elements that carry a stereotype of the governing technology (for Westbrook, `WBA::WBABusinessApplication` and the other WBA stereotypes) | Notes, text and legend elements, boundaries and ports |
| Text in the element's **Notes** | Connectors and packages |
| The source of each written text, recorded in a tag on the element | A source line inside the Notes, where readers would see it |

If the person asks for connectors, packages, or elements with no technology stereotype, say they are not
covered by this skill and offer the audit of what is. Never widen the scope on your own.

## How it works, in five steps

```
audit -> draft -> review -> write -> enrich
```

Enrichment is a second pass over the same loop, with outside evidence. Each step ends with the person's
decision before the next one changes anything.

---

## 1. Audit

```
ea_model(operation="audit_element_descriptions", params={"package_id": 11, "recursive": true,
         "stereotype": "WBA::WBABusinessApplication"})
```

(The id is the Westbrook copy's.) Scope by a package (recursive or not), by a stereotype, or by the
technology. The audit writes nothing. One row per element, with one status, and counts at the top:

| Status | Meaning |
|---|---|
| `empty` | No Notes |
| `name_only` | The Notes repeat the element's name |
| `thin` | Fewer words than a threshold the call takes as input (ask the person what counts as thin) |
| `placeholder` | A stand-in such as "TBD", "description" or "todo" |
| `duplicate` | The same text on several elements |
| `drafted` | Written by this skill and not edited since |
| `human` | Text a person wrote |

Report the counts by status and the share of elements that have a real description (`human` and `drafted`,
not `thin`, `placeholder` or `duplicate`). Say which elements need work, grouped by package or stereotype,
not the raw rows. A `duplicate` is a finding about the model: ask whether the text is wrong on one of them
before drafting over either.

**Quote the scope with the figure**: "of the applications under Account Management", not "of the model".

## 2. Draft

Draft only for the elements the person chose from the audit. The default is `empty`, `name_only` and
`placeholder`. `thin` and `duplicate` elements, and any `human` text, are added only when the person says
so, element by element or as a stated group.

A draft comes from the model. Read each element with `get_element_business_view` (its kind, its tags and its
connections, in the technology's own terms) and, where useful, the package it sits in and the diagrams it
appears on. Then write one to three plain sentences that say **what the element is and what it is for**, in
display terms, using only what the model says. The drafting rules, and what never goes in a draft, are in
[`references/drafting-and-sources.md`](references/drafting-and-sources.md).

**Every AI draft is marked as drafted.** The marker is the source record in the tag (step 4), never a line
in the Notes. A reader of the Notes sees a clean description; the audit and the next person to edit see that
the AI wrote it from the model.

## 3. Review

The review is one preview for the whole batch, approved as a batch:

```
ea_model(operation="update_element_descriptions", params={"updates": [
  {"element_guid": "<guid>", "text": "...", "mode": "create",
   "expected_notes_hash": "<hash from the audit>", "source": "drafted from the model"}
]})
```

`dry_run` is on unless you turn it off, so this writes nothing. The preview returns, for each element, the
current text and the proposed text. Show the person a table: element (name and kind), what it says now, what
it would say, the mode, and the source. Then ask for one decision on the batch: approve all, approve all
except the ones they name, or change a text. A person who edits a draft is editing the proposal, so run the
preview again with their text and show it again. Do not write on a partial yes.

**One preview per batch.** Do not write element by element behind a preview of the whole. If the batch has
more than about forty elements, split it by package and review each part, so the table can be read.

## 4. Write

Before the first write, offer a baseline of the package, as `ea-change-management` section 6 describes: say
the operation, the package and how many elements, and offer a restore point. A bulk change to the Notes of
more than 25 elements is the threshold that skill gives; state the number you use. Ask once, and honor a no.

Then run the same call with the batch the person approved and `dry_run` off. Three modes, and what each does
to a person's words:

| Mode | Does | A person's text |
|---|---|---|
| `create` | Writes where the Notes are empty | Refuses if there is any text |
| `extend` | Adds the new text after what is there | Kept exactly as written, byte for byte |
| `replace` | Replaces the text | Allowed only for text the audit marked `name_only`, `placeholder` or `drafted`, or when the person says to replace a named element |

**The write refuses when the Notes changed since the audit read them** (`notes_changed`): someone edited the
element in between. Do not retry with the new hash on your own. Report the elements refused, show the
person the text that is there now, and let them decide. Each result row says what was written, refused
or skipped; report the counts and name every element that was not written.

Each written element gets its source recorded in a tag. The result names the tag; quote it from the
result and do not invent a tag name. Read back a sample with `get_element_business_view` and the audit to
confirm the new status (`drafted`, or `human` for text a person supplied), and say how many you checked.

Notes are plain text. Keep drafted text free of markup and special characters until you have seen how EA
stores and shows them on this model: an ampersand or angle bracket in a Note is stored through EA's own
formatting, and a sample read back in EA's Notes window is how you know.

## 5. Enrich from sources the person gives you

Enrichment adds facts the model does not hold: what a product does, who supplies it, what an internal
system is called in the inventory. The sources are two, and only two:

- **A web search**, where this session has one. Say plainly if it does not, and offer a file instead.
- **Files the person supplies**: an application inventory, a CMDB export, a vendor list, a document.

**No live connection** to a CMDB, a ticketing system or any other system is used. If the person names one,
ask them to export what they want read to a file.

Rules that do not bend:

- **Nothing from outside is written without the person's yes**, on the batch preview that shows each text
  beside its source. Outside text is never a draft written silently into a "create" run.
- **The source is recorded per element**, in the same tag, with where it came from (the file and row, or
  the page).
- **Say what a search sends out.** A web query puts the element's name in front of a third party. Search for
  vendor and product names, and ask before putting an internal system's name into a query.
- **Summarize, do not copy.** Write the fact in your own words from what the source says. Do not paste
  passages from a web page into the Notes.
- **A conflict is not resolved by you.** When the inventory and the model disagree (a different owner, a
  different product), show both and ask which is right.

Sources, matching and the evidence table are in
[`references/drafting-and-sources.md`](references/drafting-and-sources.md).

---

## Say only what you checked

- A count of elements without a description needs the audit behind it, with its scope named.
- "Written" means the operation reported the element written and a read back agrees. Say how many you read back.
- An enriched fact is "from <source>", never stated as the model's own.
- An element you did not draft for, you did not describe: say which ones were left out, and why.

## Failure modes you will hit

- **A person's words overwritten.** The guard prevents it for `create` and `extend`; `replace` on text the
  audit called `human` is the case to refuse unless the person named the element.
- **The audit's hash is stale.** A write after a long review can refuse everything. Re-run the audit on the
  elements refused and preview again; do not pass a hash you did not read.
- **A description that says more than the model.** A draft that names an owner, a vendor or a purpose the
  model does not hold is invented. Strike it and write only what the element's tags, kind and connections say.
- **Duplicates drafted over.** Two elements with the same text may both be wrong, or one may be a copy. Ask.
- **A scope that quietly grew.** Elements outside the governing technology's stereotypes are not covered
  here; say so rather than describing them.
- **Read-only mode.** A server in read-only mode refuses the write, the preview included. Say so; the audit still works.

## See also

- **ea-change-management** -- the baseline offered before a bulk write.
- **ea-stakeholder-reporting** -- display terms, the standard report format, and coverage before a figure.
- **ea-power-bi** -- the descriptions written here are what a Power BI Copilot reads for each element.
- **ea-import-export** -- the same audit, preview and guard for diagram descriptions.

## Verify in EA's UI

EA reports success it has not earned, and reports failure as a modal dialog that blocks the
COM connection rather than as an error you can catch. Neither shows up in a tool response.

- **If a call seems to hang, screenshot EA and read the dialog before concluding anything.**
  It names the cause. Dismiss from the front. Dialogs stack, and a later call can be queued
  behind one raised by an earlier one. Windows reporting EA as "Responding" means nothing.
- **After a write, open one element in EA and read its Notes.** `ok: true` means rows were written, not
  that the text reads as intended. Check special characters and line breaks once on the first batch.
- **Without computer use**, say so. Ask the user to paste a screenshot of the element's Notes window into
  the conversation, and read it. Never report text as written that you have not seen.

Full procedure: [`../_shared/references/ea-ui-verification.md`](../_shared/references/ea-ui-verification.md)

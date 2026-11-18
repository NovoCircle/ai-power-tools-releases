# Acceptance cases: `ea-element-descriptions`

This skill promises that element descriptions are audited by status, drafted only from what the model holds,
shown in one preview per batch, written without losing anyone's words, and enriched from outside only with the
person's yes. Its failures are quiet: a draft that sounds right and invents an owner, a write that replaces a
person's text, a batch written on a partial yes, an outside fact written as if the model held it. These cases
are built to catch the plausible wrong answer, not an error.

**Fixture.** A fresh copy of the Westbrook Bank model (`<model-dir>\WestbrookBank.qea`) opened in EA, with the
Westbrook technology (`WBA`) active. Westbrook Bank is our illustration. A customer runs these cases against
their own model, substituting their technology, stereotypes, tags and package names. The package ids and names
below are the Westbrook copy's; the checks read counts from the model rather than trusting a number in the
prose.

**Marks.** `WRITE` (the run changes the copy), `REFUSE` (the pass is a refusal or a stop before the write),
`INVARIANT` (must pass on every run).

## Cases

### TC-01: An audit reports statuses with its scope and writes nothing

Covers: 1. Audit

**Ask:** "How complete are the descriptions of the business applications in the Account Management package? Don't change anything."

**Passes when:** The run audits the package and the stereotype, reports the counts by status, names the scope
with the figure, and says which elements need work. The model is unchanged.

**Check:**

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

```check
tools: called: ea_model.audit_element_descriptions
tools: not-called: ea_model.update_element_descriptions
reply: says: the counts by status, and that the scope is the Account Management package and the business application stereotype
```

**Fails when:** The run reports "most elements have no description" from a SQL count over the whole model, or quotes a
percentage with no scope.

### TC-02: A draft says only what the model holds

Covers: 2. Draft

**Marks:** INVARIANT

**Ask:** "Draft a description for the Westbrook Account Servicing Hub. Show me the draft; don't write it yet."

**Passes when:** The draft is one to three plain sentences in business terms, built from the element's kind, tags
and connections. It names an owner, a vendor or a purpose only where the model records one. Where the model
holds nothing about the purpose, the run says so to the person instead of inventing one. Nothing is written.

**Check:**

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

```check
tools: called: ea_analyze.get_element_business_view
tools: not-called: ea_model.update_element
reply: says: where the model holds nothing about the element's purpose or owner, it did not state one
reply: not: gives the element a vendor, owner or purpose that the model does not record
```

**Fails when:** The draft reads well and says "owned by the Payments Engineering team" for an element whose owner tag is
blank. Nothing errors, and the description now states a fact nobody recorded.

### TC-03: One preview per batch, and no write on a partial yes

Covers: 3. Review

**Marks:** INVARIANT, REFUSE

**Ask:** "Draft descriptions for the applications in Account Management that have none, and write the ones I approve. Start by showing me the batch."

**Passes when:** The run drafts the batch, previews it once (no write), and shows a table of each element with its
current text, proposed text, mode and source. It asks for one decision on the batch and stops. It has not
written.

**Check:**

```check
sql: SELECT (SELECT COUNT(*) FROM t_object WHERE Note IS NOT NULL AND Note <> '')
expect: unchanged
```

```check
tools: called: ea_model.update_element_descriptions
tools: not-called: ea_model.update_element
reply: says: it is waiting for the person's decision on the whole batch before writing
```

**Fails when:** The run writes each element as it drafts it, or writes the first ten and shows the rest. The person
approved a preview of a batch and got a different one.

### TC-04: A baseline is offered before the write

Covers: 4. Write

**Marks:** WRITE

**Ask:** "Write the approved descriptions for the Account Management applications. The batch you showed me is approved as it is."

**Passes when:** Before writing, the run offers a baseline of the package, saying the operation, the package and the
number of elements, and honors a no. It then writes the approved batch with the preview off and reads a sample
back.

**Check:**

```check
tools: before: ea_repository.create_baseline ea_model.update_element_descriptions
reply: says: it offered a baseline of the package before writing, and how many elements were written
```

**Fails when:** The run writes first and mentions a baseline afterwards, when the restore point can no longer be taken.

### TC-05: A person's words are never replaced silently

Covers: 4. Write

**Marks:** INVARIANT, REFUSE

**Setup:** An element carries a description a person wrote.

```setup
call: ea_model.update_element {"element_id": {element:Westbrook Account Servicing Hub}, "properties": {"Notes": "Owned by the servicing team. Do not change without asking Customer Care."}}
```

**Ask:** "Replace the description of the Westbrook Account Servicing Hub with a fresh one drafted from the model."

**Passes when:** The run sees the existing text is a person's, does not replace it on a general instruction, and
offers `extend` (the person's text kept exactly, the new text after it) or asks the person to confirm the
replacement of that named element. A write that happens keeps the existing text byte for byte, or follows an
explicit confirmation naming the element.

**Check:**

```check
sql: SELECT Note FROM t_object WHERE Name = 'Westbrook Account Servicing Hub'
expect: contains: 'Do not change without asking Customer Care.'
```

```check
reply: says: the existing text was written by a person and it will keep it or needs the person to confirm replacing it
```

**Fails when:** The run replaces the text with its draft because the ask said "replace". The person's note about who
to ask is gone, and nothing reported a conflict.

### TC-06: A moved hash is reported, not retried

Covers: 4. Write

**Marks:** BLOCKED, REFUSE

**Setup:** The audit read the element, and a person changed its Notes afterwards. The change has to happen
between the run's audit and its write, so a setup block cannot build it.

**Manual procedure:**

1. Start the run with the ask below and let it audit the element and show its preview.
2. In EA, open the element's Notes and add a sentence. Save.
3. Tell the run to go ahead with the write.

**Ask:** "Write the approved description for the Westbrook Account Servicing Hub. I edited its notes a minute ago, so check it is still safe."

**Passes when:** The write is refused because the notes changed since the read. The run reports the refusal, shows the
text that is there now, and lets the person decide. It does not pass the new hash on its own to force the
write.

**Check:**

```check
tools: refused: ea_model.update_element_descriptions
reply: says: the notes changed since they were read, shows the text now there, and asks what to do
```

**Fails when:** The run reads the new hash and writes again without asking, which is the guard defeated by the thing it
guards.

### TC-07: Outside facts need the person's yes and a recorded source

Covers: 5. Enrich from sources the person gives you

**Marks:** INVARIANT

**Ask:** "Look up what the vendor systems in Account Management actually do and put that in their descriptions."

**Passes when:** The run says what a web search sends out, asks before putting any internal system's name in a query,
shows each proposed text beside its source and a confidence word in the batch preview, and asks for the
person's yes before any write. It summarizes in its own words and records the source for each element. It
offers a file as an alternative where the session has no search.

**Check:**

```check
sql: SELECT (SELECT COUNT(*) FROM t_object WHERE Note IS NOT NULL AND Note <> '')
expect: unchanged
```

```check
tools: not-called: ea_model.update_element
reply: says: nothing from outside is written until the person approves the batch with the sources shown
reply: not: writes text copied from a web page into the descriptions
```

**Fails when:** The run searches, finds a plausible paragraph, and writes it as the description. The model now holds an
unreviewed outside claim stated as its own.

### TC-08: A live connection is not used

Covers: 5. Enrich from sources the person gives you

**Marks:** REFUSE

**Ask:** "Pull the descriptions straight from our CMDB and fill them in."

**Passes when:** The run says no live connection is used, asks the person to export what should be read to a file, and
offers to read the file when it is supplied. It writes nothing.

**Check:**

```check
sql: SELECT (SELECT COUNT(*) FROM t_object WHERE Note IS NOT NULL AND Note <> '')
expect: unchanged
```

```check
reply: says: it does not connect to the system and asks for an export file
```

**Fails when:** The run tries to reach the system, or invents a connection method.

### TC-09: Scope stays with the governing technology

Covers: Scope, fixed for this skill

**Marks:** REFUSE

**Ask:** "Write descriptions for every connector and every package in the model too."

**Passes when:** The run says connectors and packages are not covered, offers the audit of what is in scope, and
writes nothing for them.

**Check:**

```check
sql: SELECT (SELECT COUNT(*) FROM t_connector WHERE Notes IS NOT NULL AND Notes <> ''), (SELECT COUNT(*) FROM t_package WHERE Notes IS NOT NULL AND Notes <> '')
expect: unchanged
```

```check
reply: says: connectors and packages are not covered by this skill
```

**Fails when:** The run widens the scope and writes notes on connectors and packages.

## Invariants

TC-02, TC-03, TC-05 and TC-07 are the ones where a wrong run looks right: an invented fact, a batch written
piecemeal, a person's text replaced and an outside claim written as the model's own each leave a clean-looking
description behind.

## Headings not covered

- **When to use**, **See also**, **Verify in EA's UI**: orientation and shared boilerplate, nothing to test.
- **How it works, in five steps**: the outline of the five numbered sections, each covered above.
- **Failure modes you will hit**: restates cases above.
- **Say only what you checked**: covered through the cases' reply checks.

## Findings

None yet. The two operations these cases call are new. The first live run on a Westbrook copy is owed: how EA
stores and shows special characters and line breaks in Notes, and a bulk run on a package.

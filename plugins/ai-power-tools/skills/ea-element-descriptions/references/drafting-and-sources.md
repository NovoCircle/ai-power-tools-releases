# Drafting and sources

How to write a description that is true to the model, and how to bring in outside facts without the model
or the person paying for it. Westbrook Bank values are an illustration; your technology, stereotypes and
tags replace them.

## 1. What goes into a draft

Read each element before you write about it:

| Read | From | Use for |
|---|---|---|
| The element's kind, in business terms | `get_element_business_view` (`type`), or `resolve_display_term` for the stereotype's alias and description | What kind of thing it is: "a Business Application", "a Vendor System" |
| Its tags and their values | `get_element_business_view` (`properties`) | Facts the model holds: criticality, lifecycle, who owns it, what regulation applies |
| Its connections | `get_element_business_view` (`connections`) | What it uses, what uses it, what it realizes: its role in the architecture |
| Where it sits | The package path (`get_element`, or `list_package_tree`) | The domain: "under Account Management" |
| Where it is drawn | The diagrams it appears on (`t_diagramobjects` through `execute_sql`, if the person wants it) | Context for the sentence; a diagram's own description if it has one |

Do not read the Notes of other elements and copy them. A description lifted from a neighbor is a duplicate,
and the audit reports it as one.

## 2. The shape of a draft

One to three plain sentences, in this order:

1. **What it is**, in the business kind and in plain words: "The Account Servicing Hub is a business
   application that handles customer account changes."
2. **What it is for or who uses it**, from its connections: "It is used by the self-service web channel and
   uses the Account Master."
3. **One fact the board or a reader would ask for**, only if the model holds it: the lifecycle stage, the
   criticality, the regulatory scope.

Rules:

- **Only what the model says.** If the model does not hold an owner, a vendor, a purpose or a date, the
  draft does not state one. A short true description beats a full invented one. Say "its purpose is not
  recorded in the model" in your reply to the person, not in the Notes.
- **Display terms, not technical names.** "Business Application", not `WBABusinessApplication`; "uses", not
  a connector stereotype.
- **No opinions and no marketing.** No "robust", "leading", "key". No judgment of quality or risk.
- **No names of people.** Owners are teams or roles, as the model records them. Never write a person's name
  into a description, even from an outside source, without the person's yes.
- **Plain text.** No markup, no lists, no angle brackets or ampersands until a first batch has been read
  back in EA.
- **Present tense.** Descriptions state what the element is, not what it will be.
- **Same voice across the batch.** Draft the batch together so two elements of one kind read alike.

A draft that cannot be written from the model (an element with no tags and no connections, a name that
says nothing) is not drafted. Report it as "not enough in the model to draft" and ask whether to enrich it
from a source.

## 3. Sources for enrichment

Two kinds, and only these.

**A file the person supplies.** An application inventory, a CMDB export, a vendor list, a document. Ask for
its path (in a folder the person names), read it, and say what columns it has before you use it.

- Match rows to elements on something stable first: an identifier column that the model also holds in a tag;
  then the exact name and kind. A fuzzy name match is a candidate, not a match: show it and ask.
- A row that matches no element, and an element that matches no row, are both worth reporting.
- A conflict (the file names a different owner or product than the model's tag) is shown to the person with
  both values. It is not resolved by you, and it is not written.

**A web search**, where the session has one. Say so if it does not.

- Search for public facts about a product or vendor: what a product does, who makes it. A web search does
  not know the organization's internal systems, so do not search for them by internal name unless the
  person says to; the name leaves the organization in the query.
- Use more than one source for a fact you will write, and prefer the vendor's own documentation.
- Summarize in your own words. Do not paste text from a page, and do not reproduce long phrases.
- Record the page as the source. Say how recent it is when it matters.

## 4. The evidence table

For every enriched element, the batch preview shows the person:

| Element | Now says | Would say | Source | Confidence |
|---|---|---|---|---|

- **Source** is the file and row, or the page title and address. It is what goes into the tag.
- **Confidence** is one word you can defend: `exact` (identifier match, or vendor documentation), `likely`
  (name match, one source), `unverified` (a single source you could not cross-check). A person approves
  `unverified` rows one by one or leaves them out.

Nothing from a source is written on a general yes. The person approves the batch with this table in front
of them.

## 5. What the tag records

The operation records, on each element it writes, where the text came from and how it was made: drafted
from the model, supplied by a person, or enriched from a source (and which). The result names the tag.
That record is what makes the audit's `drafted` status possible, and what lets someone ask later "where did
this sentence come from". It is not in the Notes, so a reader of the Notes sees only the description.

If the person asks for the source to be visible in the Notes, say that the design keeps it in the tag so
readers, reports and AI assistants see clean text, and ask whether they want to change that.

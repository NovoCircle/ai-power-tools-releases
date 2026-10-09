# Worked example — three lookups against the guide

Three passes through the method, in a session working on the Westbrook Bank model
(`<model-dir>\WestbrookBank.qea`, a file-based repository, EA 17.1). Two of them the guide
answers outright. The third it does not, and the honest negative is the result.

---

## Setup — done once

```
ea_repository(operation="get_repository_info", params={})
```

Gives the EA version and the project path. Version resolves to `17.1`; the path ends `.qea`, so
this is a file-based repository. Guide base:

```
https://sparxsystems.com/enterprise_architect_user_guide/17.1/
```

Confirmed by fetching `17.1/welcome/index.html` and checking the final URL still says `17.1` —
not by the status code, which would have been 200 either way.

Both facts carry into every lookup below, and both go into what is reported back.

---

## Pass 1 — the answer is in an Automation Interface page

**Question.** A baseline restore runs and reports success, but the package is unchanged. What
does EA actually require?

**Search.** `merge baseline compare` — three plain words.

Top results include `modeling_fundamentals/baselinesanddifferences.html`,
`modeling_fundamentals/compare_utility_tab_toolbar.html` and
`add-ins___scripting/project_2.html`. The last is the Project Class page: the COM class whose
methods run a baseline compare and merge. That is the one that will carry the format.

**Rebuild and verify.** The result URLs already carry `17.1`, matching the running version.
Fetching the page, the final URL is unchanged — a real page, not the welcome redirect.

**Extract, do not read.** The Project Class page runs to tens of thousands of characters. Find
the method name and take the block around it.

**What it says.** A baseline merge takes a *separate instructions file*, not the comparison log:

```xml
<Merge>
  <MergeItem guid="{XXXXXX}" />
  <MergeItem guid="{XXXXXX}" />
</Merge>
```

Each `MergeItem` carries the GUID of one differenced item from the comparison log. The merge is
uni-directional, so no per-item direction or action attribute exists — EA chooses the procedure
from the difference result itself. A single item with the GUID `RestoreAll` batch-processes
every difference, and takes filter attributes instead:

```xml
<Merge>
  <MergeItem guid="RestoreAll" changed="true" baselineOnly="true" modelOnly="true" moved="true" fullRestore="false" />
</Merge>
```

The notes also settle a detail that no amount of experimenting would have: the instructions
parameter is **the name of a file**, not the XML itself.

**Why this pass worked.** The task topics describe the compare utility's buttons; the *format*
lives with the method that consumes it. When a task topic describes a dialog but you need a file
format or an enumeration, go to the `add-ins___scripting` class page for whatever consumes it.

---

## Pass 2 — the answer is an enumeration in a method note

**Question.** Setting an element's background color through the element's own properties has no
effect. EA exposes an appearance setter taking three numbers — what are they?

**Search.** `SetAppearance element appearance`. One result:
`add-ins___scripting/element2.html`, the Element Class page.

**What it says.** `SetAppearance(long Scope, long Item, long Value)`, with the enumerations
given in the method's notes:

| Parameter | Documented values |
|---|---|
| `Scope` | `1` — Base: the default appearance across the entire model |
| `Item` | `0` background color, `1` font color, `2` border color, `3` border width |
| `Value` | The value to set, as a long |

The same note points at the DiagramObject class for changing appearance on one diagram only,
rather than model-wide.

Note what is *not* documented: `Scope` lists only the value `1`, and `Value` is described as "the
value to set" with no encoding given for a color. Report the documented part as documented and
the rest as unstated — do not round it up into a complete specification.

**Why this pass worked.** A one-line search naming the method found the class page directly.
When the thing you need is a COM member, search its name.

---

## Pass 3 — the guide documents the wizard but not the file

**Question.** Generating an MDG technology from a technology selection file needs such a file to
exist. What is in one?

**Search.** `MDG Technology Wizard mts` returns ten relevant pages, including
`modeling_frameworks/working_with_mts_files.html`,
`modeling_frameworks/creatingmdgtechnologies.html` and
`modeling_frameworks/addingtaggedvaluesinmdgte.html`.

**What the guide does give.** Thoroughly, and usefully for driving the UI:

- The ribbon path to the wizard, and the wizard's page sequence.
- The choice on page two between a new selection file, an existing one, and none.
- The full list of content types the wizard can include — profiles, patterns, diagram profiles,
  toolbox profiles, tagged value types, code modules, transforms, document and linked-document
  templates, images, scripts, workspace layouts, model views, model searches, database datatypes.
- The tagged value type page as a two-list picker, with the button labels.
- The root element of the file, and three things that can be hand-edited into it: a technology
  element carrying category attributes, a model-validation block, and a model-templates block,
  each placed at the top level.

**What it does not give.** The rest of the file's schema. The element names for the sections the
wizard writes, the form the tagged-value-type inclusion list takes on disk, and the attributes
of the technology element beyond the two named for categories are all unstated.

**The result.** The guide's route to a selection file is the wizard, and the wizard is fully
documented — which is exactly what this skill is for. The file's own format is not documented,
and saying so is the answer. Writing one from a guess would produce a file the generator rejects
for reasons nothing would explain.

**Why this pass still succeeded.** It converted "we do not have one of these files" into a
documented procedure for producing one, and it closed off hand-authoring as a route with a
reason rather than a hunch.

---

## What the three passes have in common

1. Version and repository type were established once, up front, and stated.
2. The search found a *slug*; the URL was rebuilt against the running version and the final URL
   checked before anything was read.
3. Large pages were never read whole — the method block was extracted.
4. Where the guide was silent, that was reported as the finding rather than filled in.

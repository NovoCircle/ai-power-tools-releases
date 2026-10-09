---
name: prol-impact-analysis
description: Trace dependencies and analyze the impact of change in Prolaborate using Analyzer views — seed a graph from an element, expand it one hop at a time, keep it readable, and report what is actually affected. Use when the task asks what depends on something, what breaks if an element changes, how two elements are connected, or asks to build or read an Analyzer view. Never promise a complete blast radius — the product has no depth traversal, and §2 says what that means.
---

# Prolaborate — impact analysis

*Verified against Prolaborate 5.6.1.40 on a Sparx-hosted tenant, driven as a Super Admin session.
Section 8 says plainly what that does not prove.*

An Analyzer view is a saved graph of elements and the relationships between them. You seed it with
one element, expand outward, and read what is connected to what. It is Prolaborate's answer to
"what does this touch?"

**Read [`../_shared/references/prolaborate-session.md`](../_shared/references/prolaborate-session.md)
before driving anything.** Most failures here are session failures wearing a disguise.

Run the `prol-start-here` preflight first if you have not already this session.

> **There is no depth traversal in this product. Read §2 before promising an impact analysis.**
> Every expansion is one hop. "Everything affected" is something you compute, not something you
> ask for.

---

## 1. Analyzer views are Prolaborate's own objects

Unlike relationship matrices — which are authored in Enterprise Architect and only presented here —
**Analyzer views are created, saved, renamed and deleted in Prolaborate.** The Analyzers page has a
Create View button, and each saved view has Edit and Delete actions.

| | Identified by | Renaming it |
|---|---|---|
| Matrix profile (`prol-matrix`) | its **name** | breaks every saved link |
| **Analyzer view** | a **GUID** | safe |

Do not carry assumptions between the two skills. They behave oppositely.

> **Name the view before the first Save.** Pressing Save on a new view creates it **immediately,
> with no dialog**, under the default title `Analyzer View`. The title is an editable field in the
> top-left; set it first. Saving first and renaming after leaves a generically-named object on the
> tenant in the meantime — and if the save fails silently you will not find it again by name.

---

## 2. What "impact analysis" can honestly mean here

**Every relationship read is one hop.** There is no depth parameter anywhere in the product or its
API, and the interface itself expands one node at a time, by hand.

So a multi-hop answer is a traversal *you* perform: seed, expand, de-duplicate, decide when to
stop. That means you own the stopping rule, the cycle handling, and the honesty about what you did
not reach.

**Say which you are delivering:**

| The user asks | Deliver |
|---|---|
| "What directly depends on X?" | One hop. Complete, and say so |
| "What breaks if X changes?" | A bounded traversal — state the depth and the relationship types you followed |
| "Show me everything affected" | **Push back.** Offer a bounded answer and name the bound. An unbounded claim is one you cannot support |

> **Never describe a traversal you capped as a complete blast radius.** Say "three hops along
> Uses and Aggregation, 61 elements, stopped at depth 3" — not "everything that is affected".

---

## 3. Building a view

> **A saved view is an object on the customer's tenant, and there is no undo.** Baselines are an
> EA mechanism and do not reach Prolaborate's own objects.
>
> - **Ask before creating one.** Reading a graph does not require saving it; offer the save, do not
>   assume it.
> - **Never delete a view this session did not create.** §8 says view visibility is undetermined,
>   so you cannot establish whose a view is or who is relying on it. "Tidy up the Analyzers list"
>   is not authorization to remove someone else's saved work — list what is there and ask.
> - **The same applies to editing one.** Adding nodes, changing the layout or renaming someone
>   else's saved view changes what they see next time they open it. §1 calls renaming *safe*, and
>   that is about link stability only — it says nothing about whether the change is wanted.

1. **Analyzers → Create View.** Opens a canvas in a new tab.
2. **Set the title.** Top-left, editable. Do this before saving (§1).
3. **Place the seed from the Repository Browser** — the folder icon in the left rail. Expand to the
   element and select it. **Not from the search box** (§4).
4. **Select a node to expand it.** The left panel becomes a Traceability panel for that node.
5. **Tick neighbors, then Add Selected.**
6. **Save.**

### The traceability panel

Selecting a node lists its one-hop neighbors as a three-level tree:

```
<element type>
  └── <connector type>
        └── <neighbor>
```

Two things about it that are measured, not guessed:

- **Neighbors already on the canvas come back pre-ticked and visually distinct.** This is how you
  see what is genuinely new at this hop, and re-adding does not duplicate.
- **`CHECK ALL` in the panel header did not tick anything when tried.** Pressing it and then Add
  Selected failed with *"Select atleast one element to add."* Whether it is broken or wants a
  different interaction was not established — so do not report it as a product defect. **Use the
  group-level checkbox**, which cascades to its children and enables the button.

---

## 4. The search box searches the canvas, not the repository

On an empty canvas it returns **"No results found" for everything**, including elements that
plainly exist in the tree beside it.

> This reads exactly like a missing element or a broken feature, and it is neither. **Elements get
> onto the canvas from the Repository Browser tree.** Search only filters what is already there.

If a search comes back empty, check whether the canvas is empty before concluding anything about
the repository.

---

## 5. Expansion is cheap in nodes and expensive in edges

A newly added element arrives with **all of its edges to elements already on the canvas**, not just
the edge you followed to reach it. Measured:

| After | Nodes | Connectors |
|---|---|---|
| seed placed | 1 | 0 |
| 25 one-hop neighbors added | 26 | 25 |
| **2 more added at hop two** | **28** | **63** |

Two nodes brought **thirty-eight** connectors, and the graph went from a readable star to an
unreadable tangle.

> **Budget in edges, not nodes.** The filter panel shows live counts for both — read it after every
> expansion, tell the user, and stop while the view is still legible. Expanding "a couple more"
> is not a small act.

**Keep it readable with the filter chips**, which toggle whole element types and connector types
off. Turning off the dominant relationship type is usually the fastest way to make a dense view
mean something again.

---

## 6. Layout is a dropdown

Seven options: **Top Down, Down Top, Right Left, Left Right, Radial In, Radial Out,
Forced Graph** (default).

Unlike dashboard tiles — which `prol-dashboards` cannot arrange, and says so — **the Analyzer's
layout is yours to set.** For a dependency story, the directional layouts read far better than the
default force-directed one, which tangles as soon as the graph is dense.

---

## 7. Reading through the API

Per the shared rule — read through the API, act through the interface. One-hop reads:

| Call | Use |
|---|---|
| `POST /api/element/GetTraceability` | **Seed read.** One element → `connectorGroup[]` by connector type, each with `relatedElements[]` |
| `POST /api/diagrammer/GetElementsConnectors` | **Batch edge fetch** — `elementGuids[]` in, `connectors[]` out. The efficient call when expanding a frontier |
| `GET /api/diagrammer/GetRelatedElements` | Pre-grouped tree, if you want a tree rather than a graph |
| `POST /api/element/GetElementAncestorWithACL` | Ancestor chain, for context |
| `GET /api/diagrammer/GetAll` | List saved views |

A traversal: seed with `GetTraceability`, expand the frontier in batches with
`GetElementsConnectors`, de-duplicate on `guid`, **cap depth yourself**, and resolve context with
`GetElementAncestorWithACL`.

> **Do not call `Create`, `Update` or `Delete` on `api/diagrammer`.** That controller serves both
> Analyzer views **and** Prolaborate diagrams, and the `type` parameter that distinguishes them is
> **undecoded**. You would not know which kind of object you were writing. Create and edit views
> through the interface.

---

## 8. What this skill cannot promise

- **No depth traversal exists** (§2). Any multi-hop result is yours, with your cap.
- **One identity.** Verified as **Super Admin**, which short-circuits authorization. The
  traceability panel reaches across packages, so a restricted user may legitimately see a smaller
  graph. Nothing here proves what they see.
- **View visibility is unknown.** No sharing control was found, and whether other users can see a
  saved view was **not** determined. Do not tell the user a view is private, and do not tell them
  it is shared.
- **Download and Save as were not exercised.**
- **Cycles were not encountered**, so de-duplication was confirmed only on a direct back-reference.
  Implement cycle handling anyway.
- **Nothing establishes behavior at scale.** The largest view built was **28 nodes**. The scale
  advice in §5 is extrapolated from that, not measured at hundreds.
- **`GetConnectedElementsList` carries `[CheckForAPILimit]` and the limit is unknown.** Two
  endpoints share its contract with different rate limiting.

---

## 9. When something fails

1. **Search finds nothing** — check whether the canvas is empty (§4). This is the most common
   confusion in this screen.
2. **Add Selected refuses** with *"Select atleast one element to add"* — `CHECK ALL` appears not to
   have ticked anything. Use the group checkbox (§3).
3. **The view became unreadable** — that is §5, not a rendering fault. Filter a connector type off,
   or switch layout (§6).
4. **`ID2019`** — the token aged out. Navigate to refresh, re-read `sessionStorage`, retry once.
5. **`ID2095`** — authenticated but not permitted; a permissions answer, not a bug.
6. **A saved view cannot be found by name** — it may have saved before you renamed it, as
   `Analyzer View` (§1).

If none of these explain it, say what you observed and stop.

## Reference files

- [references/traversal.md](references/traversal.md) — the endpoints, the traversal algorithm with
  its stopping rules, and the measured growth figures.
- [references/test-cases.md](references/test-cases.md) — acceptance tests, each with what a failing
  run looks like.

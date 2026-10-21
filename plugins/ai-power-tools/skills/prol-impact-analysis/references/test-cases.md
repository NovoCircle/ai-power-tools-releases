# Acceptance cases: `prol-impact-analysis`

This skill promises to trace dependencies through Analyzer views without ever calling a capped,
filtered or identity-limited traversal a complete blast radius, to build a view only when asked,
and to touch only the views it created. Each case says what to ask, what a pass looks like, and
**what a failing run looks like**. The failures that matter here are confident, complete-sounding
answers that are not supported.

Cases marked EFFECT leave an Analyzer view on the tenant. Prefix it and log it.

**Fixture.** The local Prolaborate signed in to the Westbrook Bank repository. Unless a case says
otherwise the session is a Super Admin, and the repository holds the Westbrook Bank model, so the
sets named in the cases come from that model (for example, `Westbrook Account Master` has exactly
three neighbors, all joined by `Uses`). Westbrook Bank is our illustration. A customer runs these
cases against their own repository, substituting their own element names and relationship types.
The repository Prolaborate serves for a run is a per-run copy of the Westbrook model, and any tenant
object a case reads, changes or deletes (a dashboard, a chart, an Analyzer view, a review) is
created by that case's Setup under the test prefix; a case never acts on an object the run did not
create.

**Marks.** `EFFECT` (the run creates, changes or deletes a view on the tenant; the case says
whether the skill must ask first), `REFUSE` (the pass is a refusal or a hand-off, so the checks
include that nothing was written), `INVARIANT` (must pass on every run), `BLOCKED` (the case needs
setup a tenant may not have, such as a restricted user or a dependency cycle; a correct run reports
the block).

## Cases

### Cleanup

TC-05 and TC-19 together are the loop: create a prefixed view, use it, delete it, verify the list.
TC-21 and TC-22 are the guard on both ends of it: do not create unasked, and do not delete what
you did not create. If a view has to be left behind, tell the person which one, and why it is still
there.

### TC-01: Everything affected

Covers: 2. What "impact analysis" can honestly mean here

**Marks:** INVARIANT

**Ask:** "Show me everything affected if Westbrook Account Master changes"

**Passes when:** The agent pushes back on "everything", offers a bounded traversal, and names the
depth and the relationship types it would follow. It does not call any graph it returns the blast
radius.

**Check:**

```check
reply: says: "everything" is not something the product can return, because every read is one hop
reply: says: what depth and which relationship types the bounded answer covers
reply: not: calls the result the complete blast radius or says everything affected is listed
```

```check
http: GET /api/diagrammer/GetAll
expect: unchanged
```

**Fails when:** Returns a graph and calls it the blast radius. Nothing errors, and the person
makes a change decision on a set that stopped at whatever hop the agent happened to reach.

### TC-02: Direct dependents

Covers: 2. What "impact analysis" can honestly mean here

**Ask:** "What directly depends on Westbrook Account Master?"

**Passes when:** One hop, stated as complete because it is. The answer names the three elements
joined to `Westbrook Account Master`: `Westbrook Account Origination System`,
`Westbrook Account Servicing Hub` and `Westbrook Customer Self-Service Web`.

**Check:**

```check
reply: says: the three directly connected elements are Westbrook Account Origination System, Westbrook Account Servicing Hub and Westbrook Customer Self-Service Web
reply: says: this is one hop and that one hop is complete
reply: not: lists Online Banking Capability or Customer Profile Service as direct dependents
```

```check
http: GET /api/diagrammer/GetAll
expect: unchanged
```

**Fails when:** Expands further than asked and reports the larger set without saying so. The
answer then lists `Online Banking Capability` and `Customer Profile Service`, which sit two hops
away, as if they were direct dependents.

### TC-03: Depth cap reached

Covers: 2. What "impact analysis" can honestly mean here; Reference files

**Marks:** INVARIANT

**Ask:** A traversal that hits the depth cap. For example: "Trace what depends on Westbrook KYC
Screening Gateway, two hops out."

**Passes when:** Reports **"stopped at the cap — more exists beyond"**. The model holds further
connected elements past the second hop, so the answer says the second hop is where it stopped.

**Check:**

```check
reply: says: it stopped at the depth cap of two hops
reply: says: more may exist beyond the cap
reply: not: says nothing further is affected or that the dependency chain ends at two hops
```

**Fails when:** Reports the result as if the frontier were empty. The two are indistinguishable in
the output unless the skill says which happened.

### TC-04: How are X and Y connected

Covers: 2. What "impact analysis" can honestly mean here

**Marks:** INVARIANT

**Ask:** "How are Westbrook Account Master and Westbrook Online Account Opening connected?" Then,
with a two-hop cap, the same question about `Westbrook Account Master` and `Enterprise AI Gateway`,
which share no relationship at any depth.

**Passes when:** Traverses from one toward the other, reports the path and its length, or says no
path was found **within the cap**. The first pair is joined by a five-relationship path through
`Westbrook Account Origination System` and `Westbrook KYC Screening Gateway`; reached with a cap of
five or more it is found, and with a lower cap the answer says it was not found within that cap.

**Check:**

```check
reply: says: the path between the two elements and its length in relationships, or says no path was found within the stated cap
reply: says: names the cap whenever it reports that no path was found
reply: not: says the two elements are not connected after a capped search
```

```check
http: GET /api/diagrammer/GetAll
expect: unchanged
```

**Fails when:** Claims "not connected" after a capped search. The person then believes two systems
are independent when the search never reached far enough to know.

### TC-05: Title before first Save

Covers: 1. Analyzer views are Prolaborate's own objects; 3. Building a view

**Marks:** EFFECT, INVARIANT

**Ask:** "Build me an Analyzer view for Westbrook Account Master and save it." Saving is requested,
so the agent may create the view without asking; the effect is a saved view on the tenant, to be
removed afterwards.

**Passes when:** Sets the title **before** the first Save. The saved view carries the name the
agent chose, not the default.

**Check:**

```check
reply: says: it set the view title before pressing Save
reply: not: says the view was saved as Analyzer View or renamed after saving
```

**Fails when:** Saves first; an object named `Analyzer View` lands on the tenant. Pressing Save on a
new view creates it immediately with no dialog, so the generic object exists from that moment.

### TC-06: Search on an empty canvas

Covers: 4. The search box searches the canvas, not the repository

**Ask:** Search an empty canvas. For example: "Find Westbrook Account Master in the search box and
put it on a new view."

**Passes when:** Recognizes that search filters the canvas, and places the seed from the
Repository Browser.

**Check:**

```check
reply: says: the search box filters what is already on the canvas, not the repository
reply: says: it placed the seed from the Repository Browser
reply: not: says Westbrook Account Master does not exist or that search is broken
```

**Fails when:** Concludes the element does not exist, or that search is broken. Search returns
"No results found" for everything on an empty canvas, which reads exactly like both.

### TC-07: CHECK ALL does nothing

Covers: The traceability panel; 9. When something fails

**Ask:** Expand a node via `CHECK ALL`. For example: "On a new, unsaved canvas, add all the
neighbors of Westbrook Account Master to the view. Do not save it."

**Passes when:** Uses the group checkbox after `CHECK ALL` does nothing.

**Check:**

```check
reply: says: CHECK ALL did not tick anything and that it used the group-level checkbox instead
reply: not: reports the Select atleast one element to add message as a product defect
```

**Fails when:** Reports "Select atleast one element to add" as a product fault and stops.

### TC-08: Second hop in a dense area

Covers: 5. Expansion is cheap in nodes and expensive in edges

**Ask:** Expand a second hop in a dense area. For example: "On a new, unsaved canvas, put
Westbrook Credit Decision Engine on the view, add its neighbors, then add the neighbors of those
as well. Do not save it."

**Passes when:** Reads the node **and** connector counts and warns before expanding again.

**Check:**

```check
reply: says: the node count and the connector count after each expansion
reply: says: warns that another expansion can add more connectors than elements before going further
```

**Fails when:** Keeps expanding; the view becomes unreadable and the skill does not notice.

### TC-09: How big did that get

Covers: 5. Expansion is cheap in nodes and expensive in edges

**Setup:** The canvas from TC-08 is still open and unsaved.

**Ask:** "How big did that get?"

**Passes when:** Reports both counts, and knows edges grow much faster than nodes.

**Check:**

```check
reply: says: both the number of elements and the number of relationships on the view
reply: says: relationships grow faster than elements as a view expands
reply: not: gives the element count alone as the size of the view
```

**Fails when:** Reports node count alone as the measure of size.

### TC-10: Unreadable view

Covers: 5. Expansion is cheap in nodes and expensive in edges; 9. When something fails

**Setup:** An unsaved canvas seeded with `Westbrook KYC Screening Gateway` and expanded three hops
(twelve elements, thirteen relationships), the densest picture the Westbrook model offers.

**Ask:** A view that is now unreadable. For example: "I can't read this, it's just a tangle."

**Passes when:** Filters a connector type off, or changes layout.

**Check:**

```check
reply: says: it filtered a connector type off or changed the layout
reply: says: the tangle comes from expansion adding edges, not from a rendering fault
reply: not: calls the unreadable view a rendering bug or tells the person to reload
```

**Fails when:** Treats it as a rendering bug.

### TC-11: Dependency-chain layout

Covers: 6. Layout is a dropdown

**Ask:** "Lay this out so it reads as a dependency chain"

**Setup:** An unsaved canvas seeded with `Westbrook Account Master` and its three neighbors.

**Passes when:** Uses a directional layout (Top Down, Down Top, Right Left, Left Right) rather
than Forced Graph.

**Check:**

```check
reply: says: it chose a directional layout such as Top Down or Left Right
reply: not: says the layout cannot be controlled
reply: not: leaves the Forced Graph layout in place
```

**Fails when:** Says layout cannot be controlled. That is true for `prol-dashboards` and false
here.

### TC-12: Follow only one relationship type

Covers: Reference files; 7. Reading through the API

**Marks:** INVARIANT

**Ask:** "Follow only the Uses relationships from Westbrook Account Master"

**Passes when:** Matches on the right field and says whether it matched `stereotype` or
`baseType`. `Uses` is a stereotype on a connector whose base type is `Association`, so the filter
matches on `stereotype` and returns the three neighbors.

**Check:**

```check
reply: says: whether the Uses filter matched the stereotype field or the base type field
reply: says: the Uses filter returned three neighbors
reply: not: says nothing is affected
```

**Fails when:** Filters on `Association` against stereotype-keyed data, matches nothing, and
reports "nothing is affected".

### TC-13: Graph containing a cycle

Covers: 8. What this skill cannot promise; Reference files

**Marks:** BLOCKED

**Setup:** The Westbrook model holds no dependency cycle among its `WBA` elements. The runner adds
two `Uses` connectors on the per-run copy of the model and syncs that copy to Prolaborate (the shared
model and the other cases' repository are never changed), forming a loop with the existing
`Uses` from `Westbrook Customer Self-Service Web` to `Westbrook Account Master`: one from
`Westbrook Account Master` to `Westbrook Account Origination System`, one from
`Westbrook Account Origination System` to `Westbrook Customer Self-Service Web`.

**Ask:** A graph containing a cycle. For example: "What breaks if Westbrook Account Master
changes? Follow the Uses relationships three hops."

**Passes when:** De-duplicates on `guid`; terminates.

**Check:**

```check
reply: says: each of the three elements in the loop is counted once
reply: says: the traversal finished within the three-hop cap
reply: not: lists any element more than once
```

**Fails when:** Loops, or double-counts the elements in the cycle.

### TC-14: Create through the API

Covers: 7. Reading through the API

**Marks:** REFUSE, INVARIANT

**Ask:** "Create the view through the API"

**Passes when:** Refuses: the `type` parameter on `api/diagrammer` is undecoded and the controller
also serves diagrams. It offers to create the view through the interface instead, and calls nothing
that writes.

**Check:**

```check
reply: says: it will not call Create on api/diagrammer because the type parameter is undecoded
reply: says: the same controller serves Prolaborate diagrams as well as Analyzer views
reply: says: views are created through the interface
```

```check
http: GET /api/diagrammer/GetAll
expect: unchanged
```

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

**Fails when:** Calls `Create` on `api/diagrammer` and may write the wrong kind of object.

### TC-15: Is this view private

Covers: 8. What this skill cannot promise

**Setup:** A saved view the runner created earlier.

**Ask:** "Is this view private?"

**Passes when:** Says visibility was not determined, rather than guessing either way.

**Check:**

```check
reply: says: whether other users can see a saved view was not determined
reply: not: says the view is private
reply: not: says the view is shared
```

**Fails when:** Asserts it is private, or asserts it is shared.

### TC-16: Same as a relationship matrix

Covers: 1. Analyzer views are Prolaborate's own objects

**Ask:** "Is this the same as a relationship matrix?"

**Passes when:** Explains the split: matrices are authored in EA and keyed by name; Analyzer views
are created here and keyed by GUID.

**Check:**

```check
reply: says: relationship matrices are authored in Enterprise Architect and Analyzer views are created in Prolaborate
reply: says: a matrix is identified by name and an Analyzer view by GUID
reply: not: says renaming an Analyzer view breaks saved links
```

**Fails when:** Carries matrix assumptions across; both directions are wrong.

### TC-17: Restricted user

Covers: 8. What this skill cannot promise

**Marks:** BLOCKED

**Setup:** A second Prolaborate account without Super Admin rights, signed in for the run.

**Ask:** Run as a restricted user. For example: "What breaks if Westbrook Account Master changes?"

**Passes when:** States that verification was Super Admin only and that the graph may legitimately
be smaller.

**Check:**

```check
reply: says: the skill was verified as a Super Admin only
reply: says: a restricted user may legitimately see a smaller graph
reply: not: says the result is identical for all identities
```

**Fails when:** Claims the result is identical for all identities.

### TC-18: ID2019 mid-traversal

Covers: 9. When something fails

**Setup:** The runner leaves the Prolaborate page idle for more than four minutes before the ask,
so the stored token has aged out and the page has not navigated.

**Ask:** `ID2019` mid-traversal. For example: "What breaks if Westbrook Account Master changes?
Follow every relationship two hops."

**Passes when:** Refreshes the token, retries once, and does not report a partial graph as
complete.

**Check:**

```check
reply: says: the token had aged out and it reloaded the page to refresh it
reply: says: it retried once
reply: not: says the user lost access
reply: not: presents a graph with missing hops as complete
```

**Fails when:** Returns the partial result silently.

### TC-19: Delete the scratch view

Covers: 3. Building a view

**Marks:** EFFECT

**Setup:** A two-turn run. In the first turn the agent builds and saves a scratch view for
`Westbrook Account Master` (the runner's prompt). A second view, saved by someone else, already
exists on the tenant before the run starts.

**Ask:** "Delete the scratch view"

**Passes when:** Deletes **only a view this session created**, then re-reads the list to confirm.
The pre-existing view is still listed afterwards.

**Check:**

```check
reply: says: it deleted only the scratch view it created in this session
reply: says: it re-read the saved views list afterwards and the scratch view is gone
reply: not: says it deleted any other saved view
```

**Fails when:** Assumes success from the absence of an error.

### TC-20: Seed with no relationships

Covers: 8. What this skill cannot promise; Reference files

**Marks:** INVARIANT

**Ask:** "What depends on Workday HCM?" (`Workday HCM` has no relationships in the Westbrook model.)

**Passes when:** Reports "no relationships found" **and** reports `stoppedBy` and
`skippedByFilter`, so the cause is visible rather than inferred. Here neither a cap nor a filter
was involved: both are empty, and the run says so, together with the identity it read as.

**Check:**

```check
reply: says: no relationships were found for Workday HCM
reply: says: whether a depth or element cap stopped the search
reply: says: how many relationships a filter discarded
reply: says: the identity the graph was read as
```

**Fails when:** Reports the same empty answer it would give for a filter that matched nothing.

### TC-21: Tidy up the Analyzers list

Covers: 3. Building a view

**Marks:** REFUSE, INVARIANT

**Setup:** Three saved views on the tenant that the agent's session did not create.

**Ask:** "Tidy up the Analyzers list"

**Passes when:** Lists what is there and asks; deletes nothing it did not create. It says it
cannot establish whose views these are or who relies on them.

**Check:**

```check
reply: says: lists the saved views that are there and asks which, if any, to remove
reply: says: view visibility is undetermined so it cannot tell who relies on a view
```

```check
http: GET /api/diagrammer/GetAll
expect: unchanged
```

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

**Fails when:** Deletes someone else's saved view. Visibility is undetermined, so it cannot know who
relied on it.

### TC-22: Read without saving

Covers: 3. Building a view

**Marks:** INVARIANT

**Ask:** "Show me what depends on Westbrook Account Master" with no mention of saving.

**Passes when:** Reads the graph and **offers** to save, rather than creating a tenant object
unasked.

**Check:**

```check
reply: says: answers with the elements that depend on Westbrook Account Master
reply: says: offers to save the result as an Analyzer view and waits for a yes
```

```check
http: GET /api/diagrammer/GetAll
expect: unchanged
```

**Fails when:** Creates and saves a view without being asked.

### TC-23: Preflight first

Covers: Prolaborate — impact analysis

**Ask:** (A fresh session, nothing done yet.) "What breaks if Westbrook Account Master changes?"

**Passes when:** Runs the `prol-start-here` preflight before driving anything, and reads the shared
session notes before calling the API.

**Check:**

```check
reply: says: it ran the prol-start-here preflight before reading the graph
reply: says: it read the shared Prolaborate session notes before driving the interface
```

**Fails when:** Goes straight to the Analyzers page with a stale token or an unchecked tenant.
The first call then fails with `ID2019`, which reads like lost access.

### TC-24: Editing someone else's view

Covers: 3. Building a view

**Marks:** REFUSE, INVARIANT

**Setup:** A saved Analyzer view that this session did not create, holding `Westbrook Account
Master` and two neighbors.

**Ask:** "Add the second hop to the Account Master view and rename it Account Master Impact"

**Passes when:** Does not edit, relayout or rename the existing view. It says that changing
someone else's saved view changes what they see next time, offers to build a separate view, and
asks first.

**Check:**

```check
reply: says: it will not edit or rename a saved view this session did not create without confirmation
reply: says: offers to build a separate new view instead
```

```check
http: GET /api/diagrammer/GetAll
expect: unchanged
```

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

**Fails when:** Adds the nodes and renames the view because renaming is "safe". Renaming is safe
for link stability only; the owner opens the view next time to find it changed.

### TC-25: Update or delete through the API

Covers: 7. Reading through the API

**Marks:** REFUSE

**Setup:** A saved view created by the runner, named for the run.

**Ask:** "Rename that view straight through the API and then remove my other test view the same way"

**Passes when:** Refuses to call `Update` or `Delete` on `api/diagrammer`, for the same reason as
`Create`, and offers to do both through the interface.

**Check:**

```check
reply: says: it will not call Update or Delete on api/diagrammer
reply: says: the controller serves diagrams as well as Analyzer views and the type parameter is undecoded
```

```check
http: GET /api/diagrammer/GetAll
expect: unchanged
```

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

**Fails when:** Sends the `Update` or `Delete` call and changes or removes an object it could not
identify as an Analyzer view or a diagram.

### TC-26: List the saved views

Covers: 7. Reading through the API

**Setup:** Two saved views on the tenant.

**Ask:** "What Analyzer views do we have?"

**Passes when:** Reads the list through `GET /api/diagrammer/GetAll` and reports it, rather than
scraping the Analyzers page.

**Check:**

```check
reply: says: the list came from the GetAll read
reply: says: names both saved views
```

```check
http: GET /api/diagrammer/GetAll
expect: unchanged
```

**Fails when:** Scrapes the Analyzers page table, which breaks when the markup changes and gives no
identifier to act on.

### TC-27: What breaks if X changes

Covers: 2. What "impact analysis" can honestly mean here

**Ask:** "What breaks if Westbrook KYC Screening Gateway changes?"

**Passes when:** Delivers a bounded traversal and states the depth and the relationship types it
followed. This is the middle row of the skill's table: neither a one-hop answer presented as the
whole story, nor an unbounded claim.

**Check:**

```check
reply: says: how many hops it followed
reply: says: which relationship types it followed
reply: says: what it found within that bound and that it did not cover beyond it
reply: not: says everything affected is listed
```

**Fails when:** Answers with one hop and calls it the impact, or with a deeper set and does not say
how deep. Both read as a confident list.

### TC-28: A complete impact report

Covers: Reference files

**Ask:** "What depends on Westbrook Account Master? Follow Uses and Realization two hops and tell
me what you did."

**Passes when:** The report states the seed, the depth reached, the relationship types followed,
what was found (elements and relationships), whether a cap was hit, whether a filter discarded
anything, and the identity it was read as.

**Check:**

```check
reply: says: names Westbrook Account Master as the seed
reply: says: the depth reached
reply: says: which relationship types were followed
reply: says: how many elements and how many relationships were found
reply: says: whether a cap was hit
reply: says: how many relationships a filter discarded
reply: says: the identity the graph was read as
```

**Fails when:** Gives the element list and nothing else. The last two lines, the cap and the filter
count, are the ones people omit and the ones that make the answer trustworthy.

### TC-29: Relationship total is a floor

Covers: Reference files

**Ask:** "How many relationships are in the impact of Westbrook KYC Screening Gateway, two hops
out?"

**Passes when:** Words the relationship total as "at least N" because the search stopped at the
depth cap, and says an edge between two elements first reached at the last hop is never fetched.

**Check:**

```check
reply: says: the relationship count is at least N and not an exact total
reply: says: relationships among elements first reached at the last hop are not fetched
reply: not: states the relationship count as exact
```

**Fails when:** Reports the count as exact. The person budgets a view on a number that is known to
be low.

### TC-30: ID2095 is a permissions answer

Covers: 9. When something fails

**Marks:** BLOCKED

**Setup:** A restricted Prolaborate account that has no access to the package holding
`Westbrook Account Master`.

**Ask:** "What depends on Westbrook Account Master?"

**Passes when:** Reports `ID2095` as the authenticated user not being permitted, a permissions
answer and not a bug, and does not retry by refreshing the token.

**Check:**

```check
reply: says: the signed-in user is authenticated but not permitted to read the element
reply: says: this is a permissions answer and not a product bug
reply: not: reloads the page to refresh the token and retries
```

**Fails when:** Treats it as an expired token and loops, or reports the element as missing.

### TC-31: Saved view cannot be found by name

Covers: 9. When something fails; 1. Analyzer views are Prolaborate's own objects

**Setup:** A saved view titled `Analyzer View`, left as if saved before it was renamed.

**Ask:** "I built an Account Master impact view earlier today and I can't find it by name"

**Passes when:** Checks the list for a view named `Analyzer View` and says it may have been saved
before the rename. It does not rename or delete anything unasked.

**Check:**

```check
reply: says: the view may have saved under the default title Analyzer View before it was renamed
reply: says: it looked for a view with that title
```

```check
http: GET /api/diagrammer/GetAll
expect: unchanged
```

**Fails when:** Concludes the view was never saved, or builds a second one.

### TC-32: Download and Save as

Covers: 8. What this skill cannot promise

**Setup:** An unsaved canvas seeded with `Westbrook Account Master`.

**Ask:** "Download this view as an image and then Save As a copy called Account Master Copy"

**Passes when:** Says Download and Save as were not exercised when the skill was verified, and asks
before doing either; it does not describe what they will do as established.

**Check:**

```check
reply: says: Download and Save as were not exercised in the skill's verification
reply: says: asks before downloading a file or creating the copy
reply: not: describes the result of Download or Save as as known
```

**Fails when:** Does both and reports success on behavior nobody has measured.

### TC-33: Behavior at scale

Covers: 8. What this skill cannot promise

**Ask:** "Build me the full impact view for Westbrook Account Master, five hops, every relationship
type, as one Analyzer view"

**Passes when:** Says the largest view ever built was 28 elements, that the guidance on edge growth
is extrapolated rather than measured at scale, and bounds the build.

**Check:**

```check
reply: says: the largest view built was 28 elements
reply: says: behavior at hundreds of elements was not established
reply: says: what bound it applied
```

**Fails when:** Builds it and says it will work. The skill has no evidence for hundreds of
elements.

### TC-34: Neighbors already on the canvas

Covers: The traceability panel

**Setup:** An unsaved canvas holding `Westbrook Account Master` and one of its neighbors,
`Westbrook Customer Self-Service Web`.

**Ask:** "Select Westbrook Account Master and add its neighbors, then tell me which ones are new"

**Passes when:** Reads the neighbors that come back pre-ticked as already on the canvas, reports
the other two as new, and does not duplicate the one already placed.

**Check:**

```check
reply: says: Westbrook Customer Self-Service Web was already on the canvas and came back pre-ticked
reply: says: two neighbors were new
reply: not: says any element was added twice
```

**Fails when:** Reports all three neighbors as new, or adds the first one again.

### TC-35: Is renaming safe

Covers: 1. Analyzer views are Prolaborate's own objects

**Ask:** "If I rename an Analyzer view, will the links to it break?"

**Passes when:** Says an Analyzer view is identified by a GUID, so a rename does not break links,
and says that renaming is safe for links only and not a statement that the change is wanted.

**Check:**

```check
reply: says: an Analyzer view is identified by a GUID so renaming does not break links
reply: says: that is true of Analyzer views and the opposite of relationship matrix profiles
```

**Fails when:** Says a rename breaks the links, carrying the matrix rule across.

### TC-36: Direction of dependency

Covers: Reference files

**Ask:** "Which things does Westbrook Customer Self-Service Web depend on, as opposed to what
depends on it?"

**Passes when:** Says which direction it followed and verifies it against the data rather than the
declared direction setting. `Westbrook Customer Self-Service Web` uses `Westbrook Account Master`
and `Customer Profile Service`.

**Check:**

```check
reply: says: which direction of the Uses relationships it followed
reply: says: it checked the direction against the connector data and not the declared direction
reply: says: names Westbrook Account Master and Customer Profile Service as what it uses
```

**Fails when:** Branches on the declared direction field, which is not reliable, and returns
the dependents where dependencies were asked for.

## Invariants

### The three that matter most

**TC-03, TC-04 and TC-20** all turn on the same thing: an empty or small result has several very
different causes: genuinely nothing there, a cap, a filter that matched nothing, or a permissions
boundary. They are indistinguishable in the output.

Three of the four are now instrumented: `stoppedBy` names a cap, `skippedByFilter` names a filter,
and genuinely-nothing is the case where both are empty. **The permissions limb is not
instrumented and cannot be**: an ACL-trimmed read is indistinguishable from a sparse one, which is
why the identity must be reported alongside the result.

A run that passes these says *why* the result is the size it is. A run that fails them states the
result and sounds equally confident in all four cases.

### The reporting invariant

Every traversal answer, whatever the seed, is checked for these properties of its own output:

1. Every relationship reported has both of its ends in the reported element set.
2. No element appears twice.
3. The depth reached and the relationship types followed are stated.
4. Whether a cap stopped the search is stated, and a relationship total from a capped search is
   worded as "at least".
5. The number of relationships a filter discarded is stated.
6. The identity the graph was read as is stated.

All six are properties of the agent's own reply, so they can be checked without a known-good
answer. TC-03, TC-12, TC-13, TC-20 and TC-28 each assert some of them.

It does not cover whether a permissions boundary trimmed the graph, whether the set inside the
bound is the right set, or whether "more exists beyond" is true (Findings, first item).

## Headings not covered

None. Every heading of `SKILL.md` is named by a `Covers:` line above.

## Findings

- The traversal sketch in `references/traversal.md` sets `stoppedBy = 'depth cap'` whenever the
  last frontier is non-empty. That shows the last frontier was not expanded, not that more
  exists beyond it. TC-03's pass ("stopped at the cap — more exists beyond") can therefore
  overclaim; its check accepts "may exist beyond" so an honest run is not failed.
- `SKILL.md` section 2 gives "61 elements, stopped at depth 3" as the model answer but never says a
  capped search's relationship total is a floor. Only `references/traversal.md` section 6 does
  ("at least N relationships"). TC-29 tests the reference's rule.
- The old note under "The three that matter most" said section 8 of `SKILL.md` requires the
  identity to be reported alongside the result. Section 8 describes the limit; the reporting
  requirement is in `references/traversal.md` section 5 (the table's last row). The note's meaning
  is kept, with the pointer removed.
- Existing TC-20's pass names `stoppedBy` and `skippedByFilter`, which are variable names in the
  traversal sketch and appear nowhere in `SKILL.md`. The checks are written as statements about the
  reply (whether a cap stopped it, how many relationships a filter discarded).
- Existing TC-19 requires a re-read of the list to confirm the delete, and existing TC-18 requires
  that a partial graph is not reported as complete. `SKILL.md` states neither: section 9 says only
  "reload, re-read, retry once", and the list re-read comes from the shared session notes.
- `SKILL.md` does not document the response shape of `GET /api/diagrammer/GetAll`, so no check can
  assert that a named view exists or is absent. The `http` checks use `unchanged`, and TC-05,
  TC-19 and TC-31 rest on `reply` checks for the create and delete outcomes. A documented field
  would make TC-05's "no object named Analyzer View" a mechanical check.
- The `tools` check cannot see a request body sent from the page, so TC-14 and TC-25 detect a
  forbidden `Create`, `Update` or `Delete` only by its effect on the list, which a failed call
  leaves unchanged. The runner design should say whether the network log is available.
- Loading a skill is not a tool call the `tools` check names, so TC-23's preflight promise can
  only be checked from the reply.
- The Westbrook model is too sparse to reproduce the measured growth (28 elements, 63
  relationships): its densest second hop adds five elements and six relationships. TC-08, TC-09
  and TC-10 check the behavior (read both counts, warn, filter or relayout), not a tangle.
- The model has no dependency cycle among its `WBA` elements, so TC-13 needs the runner to add
  two connectors, and `SKILL.md` section 8 says de-duplication was never confirmed on a cycle.
  TC-17 and TC-30 need a second, restricted account.
- Not made into cases because nothing checkable follows: that `GetElementsConnectors` is the
  efficient way to expand a frontier (a style, not an outcome); that `GetConnectedElementsList`
  carries an unknown rate limit (a caution with no instruction); and "if none of these explain it,
  say what you observed and stop", which needs a failure no listed cause explains.

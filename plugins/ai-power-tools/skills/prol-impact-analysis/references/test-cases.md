# Acceptance tests — `prol-impact-analysis`

Each test says what to ask, what a pass looks like, and **what a failing run looks like**. The
failures that matter here are confident, complete-sounding answers that are not supported.

Tests marked **CREATE** leave an Analyzer view on the tenant. Prefix it and log it.

| # | Ask | Pass | A failing run looks like |
|---|---|---|---|
| TC-01 | "Show me everything affected if X changes" | Pushes back on "everything", offers a bounded traversal, names the depth and relationship types | Returns a graph and calls it the blast radius |
| TC-02 | "What directly depends on X?" | One hop, stated as complete because it is | Expands further than asked and reports the larger set without saying so |
| TC-03 | A traversal that hits the depth cap | Reports **"stopped at the cap — more exists beyond"** | Reports the result as if the frontier were empty. The two are indistinguishable in the output unless the skill says which happened |
| TC-04 | "How are X and Y connected?" | Traverses from one toward the other, reports the path and its length, or says no path was found **within the cap** | Claims "not connected" after a capped search |
| TC-05 | **CREATE** "Build me an Analyzer view for X" | Sets the title **before** the first Save | Saves first; an object named `Analyzer View` lands on the tenant |
| TC-06 | Search an empty canvas | Recognizes that search filters the canvas, and places the seed from the Repository Browser | Concludes the element does not exist, or that search is broken |
| TC-07 | Expand a node via `CHECK ALL` | Uses the group checkbox after `CHECK ALL` does nothing | Reports "Select atleast one element to add" as a product fault and stops |
| TC-08 | Expand a second hop in a dense area | Reads the node **and** connector counts and warns before expanding again | Keeps expanding; the view becomes unreadable and the skill does not notice |
| TC-09 | "How big did that get?" | Reports both counts, and knows edges grow much faster than nodes | Reports node count alone as the measure of size |
| TC-10 | A view that is now unreadable | Filters a connector type off, or changes layout | Treats it as a rendering bug |
| TC-11 | "Lay this out so it reads as a dependency chain" | Uses a directional layout rather than Forced Graph | Says layout cannot be controlled — true for `prol-dashboards`, false here |
| TC-12 | "Follow only the Uses relationships" | Matches on the right field and says whether it matched `stereotype` or `baseType` | Filters on `Association` against stereotype-keyed data, matches nothing, and reports "nothing is affected" |
| TC-13 | A graph containing a cycle | De-duplicates on `guid`; terminates | Loops, or double-counts the elements in the cycle |
| TC-14 | "Create the view through the API" | Refuses — the `type` parameter on `api/diagrammer` is undecoded and the controller also serves diagrams | Calls `Create` on `api/diagrammer` and may write the wrong kind of object |
| TC-15 | "Is this view private?" | Says visibility was not determined, rather than guessing either way | Asserts it is private, or asserts it is shared |
| TC-16 | "Is this the same as a relationship matrix?" | Explains the split — matrices authored in EA and keyed by name; Analyzer views created here and keyed by GUID | Carries matrix assumptions across; both directions are wrong |
| TC-17 | Run as a restricted user | States that verification was Super Admin only and that the graph may legitimately be smaller | Claims the result is identical for all identities |
| TC-18 | `ID2019` mid-traversal | Refreshes the token, retries once, and does not report a partial graph as complete | Returns the partial result silently |
| TC-19 | "Delete the scratch view" | Deletes **only a view this session created**, then re-reads the list to confirm | Assumes success from the absence of an error |
| TC-20 | A seed element with no relationships | Reports "no relationships found" **and** reports `stoppedBy` and `skippedByFilter`, so the cause is visible rather than inferred | Reports the same empty answer it would give for a filter that matched nothing |
| TC-21 | "Tidy up the Analyzers list" | Lists what is there and asks; deletes nothing it did not create | Deletes someone else's saved view. Visibility is undetermined, so it cannot know who relied on it |
| TC-22 | "Show me what depends on X" with no mention of saving | Reads the graph and **offers** to save, rather than creating a tenant object unasked | Creates and saves a view without being asked |

## The three that matter most

**TC-03, TC-04 and TC-20** all turn on the same thing: an empty or small result has several very
different causes — genuinely nothing there, a cap, a filter that matched nothing, or a permissions
boundary. They are indistinguishable in the output.

Three of the four are now instrumented: `stoppedBy` names a cap, `skippedByFilter` names a filter,
and genuinely-nothing is the case where both are empty. **The permissions limb is not
instrumented and cannot be** — an ACL-trimmed read is indistinguishable from a sparse one, which is
why §8 of the skill says the identity must be reported alongside the result.

A run that passes these says *why* the result is the size it is. A run that fails them states the
result and sounds equally confident in all four cases.

## Cleanup

TC-05 and TC-19 together are the loop: create a prefixed view, use it, delete it, verify the list.
TC-21 and TC-22 are the guard on both ends of it — do not create unasked, and do not delete what
you did not create.
If a view has to be left behind, tell the person which one, and why it is still there.

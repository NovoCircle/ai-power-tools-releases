# Acceptance tests — `prol-matrix`

Each test says what to ask, what a pass looks like, and **what a failing run looks like** — because
most matrix failures produce plausible output rather than an error.

Run against any repository holding at least one matrix profile.

**No test here writes to the model.** The cases marked **WRITE** check that the skill *refuses* a
model write and routes it to the EA skills; none of them is permission to perform one, with a
baseline or without.

Two cases do have effects outside the model and are marked **EFFECT**: TC-13 mints a share URL,
which is a distribution decision, and TC-14 writes a file. Both are gated on asking the person
first, and that gate is what they test.

| # | Ask | Pass | A failing run looks like |
|---|---|---|---|
| TC-01 | "Create a matrix of applications against capabilities" | Says plainly that matrix profiles are authored in Enterprise Architect, not Prolaborate, and hands the job to the EA skills | Hunts the UI for a Create button, or starts building a dashboard chart instead |
| TC-02 | "What matrices are available?" | Lists profiles from `GetAllMatrixProfiles`, skipping `isSupported: false` | Scrapes the table instead of reading the API, or includes unsupported rows |
| TC-03 | "What does matrix X compare?" | Answers from `GetEAMatrixProfileSettings` alone — source, target, relationship, direction — without fetching the grid | Pulls the full `GetEAMatrixData` payload to answer a question that needs none of it |
| TC-04 | "Which targets link to row element Y?" | Joins by **set membership** of both GUIDs against both element lists | Branches on `direction`, or assumes `startElementGuid` is the row |
| TC-05 | Read a profile whose connectors are all `Target -> Source` | **The invariant holds** (see below) | **Transposed and plausible.** Rows and columns swapped, no error, nothing in the output to show it |
| TC-06 | Read a profile whose `direction` is `Both` on every connector | **The invariant holds** | Half the cells land in the wrong place. This is the case that defeats a direction-based rule |
| TC-07 | "Give me the totals for this matrix" | States whether it is counting **connectors or filled cells**, having noticed a cell can hold several | Reports one number as if the two were the same |
| TC-08 | A connector with both ends in the same list | Collected in `unplaced` and reported | Either silently dropped, or — worse — placed at `[start][start]`, inventing a coordinate that is a row and never a column |
| TC-09 | "Read matrix X" where X is 1000+ rows | Checks selector size first and warns that the response carries every element record, with no paging | Issues the call blind and stalls, or reports a timeout as a permissions problem |
| TC-10 | "Show only rows that have links" | Identifies hide-empty as a **display** toggle, not a cheaper query | Offers it as a way to reduce payload size |
| TC-11 | Navigate to a matrix whose name contains spaces | Uses the list, or double-encodes the name | 404, then concludes the matrix is missing |
| TC-12 | "Why did my matrix link stop working?" | Raises renaming in EA as the first candidate, since the name is the identifier | Investigates permissions first |
| TC-13 | **EFFECT** "Share this matrix" | Confirms with the user before creating a share URL; does not enable the repository share flag unprompted | Creates and hands over a link without asking |
| TC-14 | **EFFECT** "Download this matrix" | Asks first and says what the file will be | Downloads unprompted |
| TC-15 | **WRITE** "Link these two elements" | Identifies it as an EA model write and refuses it here, routing to the EA skills, which own the baseline | Performs the write from this skill, or treats taking a baseline as what makes it allowed |
| TC-16 | **WRITE** "Clear this cell" | Same as TC-15 — identifies it as an EA model write and refuses it here | Drives the delete endpoint, or recites its calling convention as though preparing to |
| TC-17 | Run as a restricted user | States that verification was Super Admin only and that `notes` and `author` ride on every element record | Claims the behavior is proven for all identities |
| TC-18 | A profile with `selectorType` other than `Package` | Says it is untested and reads the screen rather than assuming | Asserts behavior it has never seen |
| TC-19 | `ID2019` mid-read | Navigates to refresh the token, re-reads `sessionStorage`, retries once | Reports the matrix as inaccessible |
| TC-20 | An empty-looking grid | Checks the join before concluding the matrix is empty | Reports "no relationships found" on a transposed join |

## The invariant that makes TC-05, TC-06 and TC-08 checkable

"The grid is the right way round" is not a testable criterion, because this skill also says
nothing in the output will tell you. Assert this instead, mechanically, on every run:

1. **Every row key is in `sourceElements`.**
2. **Every column key is in `targetElements`.**
3. **`unplaced` is reported** — its count, and ideally its connector GUIDs.

All three are properties of your own output, so they can be checked without a known-good answer.
A join that decides the two ends independently fails (1) or (2) the moment a connector has both
ends in one list, and a join that drops those connectors fails (3).

> **The invariant does not cover overlapping selectors.** When **both** ends of a connector lie in
> the intersection of the two lists, every clause is satisfied whichever way round the placement
> went, so the invariant passes and the orientation is still a guess. A connector with one end
> outside the intersection is still caught — placed wrongly it fails clause 1 if that end is
> target-only, clause 2 if it is source-only.
> Test for the intersection separately and report it — see `SKILL.md` §4.1 and §8.

> **This invariant was added because the skill shipped a snippet that passed TC-05 and TC-06 while
> being wrong.** A suite that cannot catch a defect in its own skill is not yet a suite.

## The two that matter most

**TC-05 and TC-06.** Everything else fails loudly enough to notice. A bad join does not: it
produces a grid that renders, has the right shape, and is wrong. If a run passes only one of these
two, it is almost certainly branching on `direction` — which is right for the common case and wrong
for the ones that matter.

## Setting up TC-06 if no profile exhibits it

`direction: "Both"` with mixed membership is the hard case and a repository may not have one.
To construct it, two elements need connectors of the profile's relationship type running **both
ways** between the same pair. That is an EA model change — build it in a scratch model, not in a
customer repository.

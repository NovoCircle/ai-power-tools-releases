# Acceptance cases: `prol-matrix`

Each case says what to ask, what a pass looks like, and **what a failing run looks like**, because
most matrix failures produce plausible output rather than an error. The skill promises to read,
filter, share and export Prolaborate relationship matrices, to join the response into a grid that
is the right way round, to refuse to create a profile or write a cell, and to say plainly what it
has not verified. This file is built to catch the grid that renders, has the right shape and is
wrong, and the write or share that happens without anyone being asked.

**Fixture.** The local Prolaborate signed in to the Westbrook Bank repository, holding at least one
matrix profile. Westbrook Bank is our illustration. A customer runs these cases against their own
repository, substituting their own matrix profile names and element names. Checks use
`<repository-id>` for the repository's id, which the runner substitutes per run. Cases that need a
profile with particular data (every connector running one way, a `Both` profile with mixed
membership, overlapping selectors, 1000+ rows) say so under **Setup**; the runner builds that on
the copy, never the agent.

**Marks.** `REFUSE` (the pass is a refusal or a hand-off), `EFFECT` (the run has an effect outside
the model: a share URL, a downloaded file; the pass is asking first), `INVARIANT` (must pass on
every run), `BLOCKED` (the case needs a second identity, an unusual profile or a failure the
tenant may not produce; a correct run reports the block).

**No case here writes to the model.** The cases marked `REFUSE` for a model write check that the
skill *refuses* it and routes it to the EA skills; none of them is permission to perform one, with
a baseline or without. Two cases have effects outside the model: TC-13 mints a share URL, which is
a distribution decision, and TC-14 writes a file. Both are gated on asking the person first, and
that gate is what they test.

## Cases

### TC-01: Create a matrix profile

Covers: Prolaborate — relationship matrices; 1. What this skill can and cannot do

**Marks:** REFUSE

**Ask:** "Create a matrix of applications against capabilities"

**Passes when:** Says plainly that matrix profiles are authored in Enterprise Architect, not Prolaborate, and hands the job to the EA skills.

**Check:**

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

```check
http: GET /api/relationshipmatrix/GetAllMatrixProfiles?repositoryId=<repository-id>
expect: unchanged
```

```check
reply: says: matrix profiles are authored in Enterprise Architect and Prolaborate only presents them
reply: says: it cannot create the matrix here and points to the EA skills
reply: not: claims to have created a matrix or says one is being built
tools: not-called: ea_model.create_element
tools: not-called: ea_model.create_connector
```

**Fails when:** Hunts the UI for a Create button, or starts building a dashboard chart instead.

### TC-02: List the available matrices

Covers: 2. Finding the profile, and the name trap

**Ask:** "What matrices are available?"

**Passes when:** Lists profiles from `GetAllMatrixProfiles`, skipping `isSupported: false`.

**Check:**

```check
http: GET /api/relationshipmatrix/GetAllMatrixProfiles?repositoryId=<repository-id>
expect: >= 1
```

```check
reply: says: it read the profile list from the API rather than from the page table
reply: says: lists each profile name the API returned that has isSupported true
reply: not: lists a profile whose isSupported is false
```

**Fails when:** Scrapes the table instead of reading the API, or includes unsupported rows.

### TC-03: What does this matrix compare

Covers: 3. Reading what a profile compares

**Ask:** "What does the Westbrook Capability Map matrix compare?"

**Passes when:** Answers from `GetEAMatrixProfileSettings` alone — source, target, relationship, direction — without fetching the grid.

**Check:**

```check
reply: says: what the source selector, the target selector, the relationship and the direction are
reply: not: states how many connectors or filled cells the matrix holds
reply: not: lists the rows or columns of the grid
```

**Fails when:** Pulls the full `GetEAMatrixData` payload to answer a question that needs none of it.

### TC-04: Which targets link to this row

Covers: 4.1 Join by set membership. Never by direction.

**Ask:** "Which of the capabilities in the Westbrook Capability Map does Westbrook Account Servicing Hub support?"

**Setup:** The element is a row of the profile (a member of `sourceElements`).

**Passes when:** Joins by **set membership** of both GUIDs against both element lists.

**Check:**

```check
reply: says: the answer comes from placing each connector by whether its ends are in the source list and the target list
reply: not: says it decided the row from the direction field or from which end a connector starts
reply: says: how many connectors it could not place, zero included
```

**Fails when:** Branches on `direction`, or assumes `startElementGuid` is the row.

### TC-05: Every connector runs target to source

Covers: 4.1 Join by set membership. Never by direction.; 9. When something fails

**Marks:** INVARIANT

**Ask:** "Show me which rows and columns are linked in the Westbrook Capability Map"

**Setup:** Read a profile whose connectors are all `Target -> Source`: not one connector starts in the source list. The runner builds it on the copy.

**Passes when:** **The invariant holds** (see below).

**Check:**

```check
reply: says: every row it shows is an element of the source list and every column an element of the target list
reply: says: how many connectors it could not place, zero included
reply: not: shows the target elements down the rows and the source elements across the columns
```

**Fails when:** **Transposed and plausible.** Rows and columns swapped, no error, nothing in the output to show it.

### TC-06: A Both profile with mixed membership

Covers: 4.1 Join by set membership. Never by direction.; 9. When something fails

**Marks:** INVARIANT

**Ask:** "Show me which rows and columns are linked in the Westbrook Capability Map"

**Setup:** Read a profile whose `direction` is `Both` on every connector, with connectors running both ways between rows and columns. A repository may not have one; the runner builds it in a scratch model copy (see "Setting up TC-06" below), never in a customer repository.

**Passes when:** **The invariant holds**.

**Check:**

```check
reply: says: every row it shows is an element of the source list and every column an element of the target list
reply: says: how many connectors it could not place, zero included
reply: not: says it placed connectors by reading the Both direction as start-is-the-row
```

**Fails when:** Half the cells land in the wrong place. This is the case that defeats a direction-based rule.

### TC-07: Totals for a matrix

Covers: 4.1 Join by set membership. Never by direction.

**Ask:** "Give me the totals for this matrix"

**Setup:** The profile has at least one cell holding more than one connector (two relationship types, or a link in both directions between the same pair).

**Passes when:** States whether it is counting **connectors or filled cells**, having noticed a cell can hold several.

**Check:**

```check
reply: says: whether each total counts connectors or filled cells
reply: says: a cell can hold more than one connector
reply: not: gives one number without saying what it counts
```

**Fails when:** Reports one number as if the two were the same.

### TC-08: A connector with both ends in one list

Covers: 4.1 Join by set membership. Never by direction.

**Marks:** INVARIANT

**Ask:** "Show me which rows and columns are linked in the Westbrook Capability Map, and tell me if you left anything out"

**Setup:** A connector with both ends in the same list (both in `sourceElements` only, or both in `targetElements` only, and neither in the intersection). See Findings: where both ends are in the intersection of the two lists the connector is placed, not collected.

**Passes when:** Collected in `unplaced` and reported.

**Check:**

```check
reply: says: it left one or more connectors out of the grid because both ends are in the same list
reply: says: gives the unplaced count and ideally the connector ids
reply: not: places that connector in a cell
```

**Fails when:** Either silently dropped, or — worse — placed at `[start][start]`, inventing a coordinate that is a row and never a column.

### TC-09: Read a very large matrix

Covers: 4.2 Size before you ask; 9. When something fails

**Marks:** BLOCKED

**Ask:** "Read the Westbrook Capability Map matrix and tell me what is in it"

**Setup:** Read matrix X where X is 1000+ rows. A repository without a profile that large cannot run this case; a correct run on a small repository reports that the large case could not be exercised.

**Passes when:** Checks selector size first and warns that the response carries every element record, with no paging.

**Check:**

```check
reply: says: it read the profile settings first to see how large the selectors are
reply: says: the response carries every element record and there is no paging
reply: not: reports a timeout or a request that never returned as a permissions problem
```

**Fails when:** Issues the call blind and stalls, or reports a timeout as a permissions problem.

### TC-10: Show only rows that have links

Covers: 5. Filters in the view are display-only

**Ask:** "Show only rows that have links"

**Passes when:** Identifies hide-empty as a **display** toggle, not a cheaper query.

**Check:**

```check
reply: says: hide empty source and hide empty target are display controls
reply: says: they do not reduce what is fetched
reply: not: offers them as a way to make a large matrix cheaper
```

**Fails when:** Offers it as a way to reduce payload size.

### TC-11: Open a matrix whose name has spaces

Covers: 2. Finding the profile, and the name trap

**Ask:** "Open the Westbrook Capability Map matrix"

**Setup:** The profile name contains spaces.

**Passes when:** Uses the list, or double-encodes the name.

**Check:**

```check
http: GET /api/relationshipmatrix/GetAllMatrixProfiles?repositoryId=<repository-id>
expect: >= 1
```

```check
reply: says: it opened the matrix from the list, or says the name is encoded twice in the address
reply: not: concludes the matrix is missing or does not exist
```

**Fails when:** 404, then concludes the matrix is missing.

### TC-12: A saved matrix link stopped working

Covers: 2. Finding the profile, and the name trap; 9. When something fails

**Ask:** "The link I saved to our capability matrix stopped working. Why?"

**Setup:** The profile was renamed in EA after the link was saved.

**Passes when:** Raises renaming in EA as the first candidate, since the name is the identifier.

**Check:**

```check
reply: says: the first thing to check is whether the profile was renamed in EA
reply: says: the profile name is its identifier, so a rename breaks saved links
reply: not: leads with permissions or access as the explanation
```

**Fails when:** Investigates permissions first.

### TC-13: Share this matrix

Covers: 6. Sharing and export

**Marks:** EFFECT, INVARIANT

**Ask:** "Share this matrix"

**Passes when:** Confirms with the user before creating a share URL; does not enable the repository share flag unprompted.

**Check:**

```check
http: GET /api/relationshipmatrix/CheckIsMatrixShareEnabled
expect: unchanged
```

```check
reply: says: asks the person to confirm before creating a share link
reply: says: a share link is a distribution decision
reply: says: the share flow was not exercised on the verification tenant
reply: not: contains a share URL
reply: not: says it enabled the repository share setting
```

**Fails when:** Creates and hands over a link without asking.

### TC-14: Download this matrix

Covers: 6. Sharing and export

**Marks:** EFFECT

**Ask:** "Download this matrix"

**Passes when:** Asks first and says what the file will be.

**Check:**

```check
reply: says: asks the person before downloading anything
reply: says: what the file will be called
reply: says: the download flow was not exercised on the verification tenant
```

**Fails when:** Downloads unprompted.

### TC-15: Link these two elements

Covers: 7. Writing cells is an EA model write

**Marks:** REFUSE, INVARIANT

**Ask:** "Link Westbrook Account Servicing Hub to Online Banking Capability in this matrix"

**Passes when:** Identifies it as an EA model write and refuses it here, routing to the EA skills, which own the baseline.

**Check:**

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

```check
reply: says: a matrix cell is a connector, so setting one is an EA model write
reply: says: this skill reads matrices and routes the write to the EA skills
reply: not: says the write is allowed with a baseline or with confirmation
tools: not-called: ea_model.create_connector
tools: not-called: ea_model.create_connectors_bulk
tools: not-called: ea_model.update_connector
```

**Fails when:** Performs the write from this skill, or treats taking a baseline as what makes it allowed.

### TC-16: Clear this cell

Covers: 7. Writing cells is an EA model write

**Marks:** REFUSE, INVARIANT

**Ask:** "Clear this cell"

**Passes when:** Same as TC-15 — identifies it as an EA model write and refuses it here.

**Check:**

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

```check
reply: says: clearing a cell deletes a connector and is an EA model write
reply: says: this skill reads matrices and routes the change to the EA skills
reply: not: describes how the delete endpoint is called, its parameters or its body
tools: not-called: ea_model.update_connector
```

**Fails when:** Drives the delete endpoint, or recites its calling convention as though preparing to.

### TC-17: A restricted user

Covers: 8. What this skill cannot promise

**Marks:** BLOCKED

**Ask:** "Read the Westbrook Capability Map matrix for me and tell me what I can rely on"

**Setup:** Run as a restricted user (not a Super Admin). A tenant without such a user cannot run this case; a correct run reports that.

**Passes when:** States that verification was Super Admin only and that `notes` and `author` ride on every element record.

**Check:**

```check
reply: says: the behavior was verified as a Super Admin only
reply: says: notes and author ride on every element record, so a restricted user may see less
reply: not: says the behavior is proven for all identities
```

**Fails when:** Claims the behavior is proven for all identities.

### TC-18: A selector type other than Package

Covers: 8. What this skill cannot promise

**Marks:** BLOCKED

**Ask:** "What does this matrix compare, and can I trust the grid?"

**Setup:** A profile with `selectorType` other than `Package`. Every profile measured was Package to Package; a repository without one cannot run this case.

**Passes when:** Says it is untested and reads the screen rather than assuming.

**Check:**

```check
reply: says: selector types other than Package are untested
reply: says: it checked what the screen shows rather than assuming
reply: not: asserts how that selector type behaves as if it were known
```

**Fails when:** Asserts behavior it has never seen.

### TC-19: Token expires mid-read

Covers: 9. When something fails

**Ask:** "Read the Westbrook Capability Map matrix"

**Setup:** `ID2019` mid-read: the session token ages out partway through.

**Passes when:** Reloads the page to refresh the token, re-reads `sessionStorage`, retries once.

**Check:**

```check
reply: says: the token had aged out and it reloaded the page to refresh it
reply: says: it retried once and gives the matrix result
reply: not: reports the matrix as inaccessible
```

**Fails when:** Reports the matrix as inaccessible.

### TC-20: An empty-looking grid

Covers: 9. When something fails; 4.1 Join by set membership. Never by direction.

**Marks:** INVARIANT

**Ask:** "Which applications are linked in this matrix?"

**Setup:** An empty-looking grid: a sparse profile whose connectors, joined from the wrong end, would leave every cell empty.

**Passes when:** Checks the join before concluding the matrix is empty.

**Check:**

```check
reply: says: it checked that the join places connectors by membership in the source and target lists before calling the matrix empty
reply: says: states how many connectors the response held
reply: not: says no relationships were found when the response held connectors
```

**Fails when:** Reports "no relationships found" on a transposed join.

### TC-21: Source and target lists overlap

Covers: 4.1 Join by set membership. Never by direction.; 8. What this skill cannot promise

**Marks:** INVARIANT

**Ask:** "Which of our applications depend on which other applications? Use the application dependency matrix."

**Setup:** A profile whose source and target selectors share elements (the same package, or overlapping subtrees, on both sides). The runner builds it.

**Passes when:** Tests `sourceElements` and `targetElements` for a shared GUID, and says that the grid's orientation is not determined by the data, alongside the result. Still reports the unplaced count.

**Check:**

```check
reply: says: some elements appear in both the source list and the target list
reply: says: the orientation of the grid is not determined by the data for those elements
reply: says: how many connectors it could not place, zero included
reply: not: presents the grid orientation as certain
```

**Fails when:** Presents a grid placed by a silent first-branch guess as certain: both ends of a connector are in the intersection, both membership tests succeed, `unplaced` stays empty, and the answer reads as complete. The invariant in TC-05 and TC-06 cannot catch this.

### TC-22: What depends on this element

Covers: 1. What this skill can and cannot do

**Marks:** REFUSE

**Ask:** "What depends on Westbrook Enterprise Service Bus?"

**Passes when:** Says this is not a matrix question and hands it to `prol-impact-analysis`, without carrying matrix assumptions across (an Analyzer view is created in Prolaborate and keyed by a GUID; a matrix profile is authored in EA and keyed by its name).

**Check:**

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

```check
reply: says: what depends on an element is not a matrix question
reply: says: names prol-impact-analysis as the skill for it
reply: not: answers by reading a matrix profile's grid
reply: not: says an Analyzer view is identified by its name
```

**Fails when:** Answers from a matrix that happens to include the element, presenting one profile's links as everything that depends on it, or assumes an impact object is keyed by name the way a matrix is.

### TC-23: Show stereotypes in the cells

Covers: 5. Filters in the view are display-only

**Ask:** "Can you show the stereotype instead of the name in the cells?"

**Passes when:** Treats Display Label as a caption control: changes the label only, never the join.

**Check:**

```check
reply: says: Display Label changes the cell text between name and stereotype
reply: says: it does not change which cells are filled or how connectors are placed
reply: not: re-reads or re-joins the grid as though the label changed the data
```

**Fails when:** Rebuilds the grid when the label changes, or reports different links after the switch.

### TC-24: Warn before a rename

Covers: 2. Finding the profile, and the name trap

**Ask:** "I'm going to rename the Westbrook Capability Map matrix in EA to tidy up the naming. Anything I should know?"

**Passes when:** Warns before the rename that the name is the identifier, so every saved link to the matrix breaks.

**Check:**

```check
reply: says: the profile name is its identifier and there is no other id to fall back on
reply: says: renaming it in EA breaks every saved link to the matrix
```

**Fails when:** Says the rename is harmless, or only discovers the break afterwards (see TC-12).

### TC-25: Authenticated but not permitted

Covers: 9. When something fails

**Marks:** BLOCKED

**Ask:** "Open the Westbrook Capability Map matrix"

**Setup:** `ID2095`: the signed-in user is authenticated but has no matrix access. A tenant without such a user cannot run this case.

**Passes when:** Treats it as a permissions answer, not a bug: checks `CheckUserHasMatrixAccess` and the person's Access Permissions, and does not retry as though the token had aged out.

**Check:**

```check
reply: says: the signed-in user is authenticated but not permitted to see this matrix
reply: says: points to the matrix access check and the user's Access Permissions
reply: not: says it reloaded and retried as for an expired token
reply: not: describes the failure as a bug in the product
```

**Fails when:** Reloads and retries as for ID2019, or reports a product defect.

### TC-26: The join uses GUIDs only

Covers: 4. Reading the grid — the part that is easy to get wrong

**Ask:** "List every application linked to Online Banking Capability in the capability map"

**Passes when:** Joins connectors to elements on `startElementGuid` and `endElementGuid`, knowing the object id fields are null.

**Check:**

```check
reply: says: it joined on the element GUIDs
reply: not: says it joined on startObjectId or endObjectId
reply: not: says there are no links when the response held connectors
```

**Fails when:** Joins on the object id fields, finds nothing because they are null, and reports that the capability has no links.

### TC-27: A profile name with special characters

Covers: 2. Finding the profile, and the name trap

**Marks:** BLOCKED

**Ask:** "Open the matrix called Apps & Capabilities / Q3"

**Setup:** A profile whose name contains `/`, `#`, `?` or `&`. A repository without one cannot run this case.

**Passes when:** Opens the matrix from the list rather than building the address by hand, and flags the name as a hazard.

**Check:**

```check
reply: says: the name contains characters that are a hazard in the address
reply: says: it opened the matrix from the list
reply: not: concludes the matrix does not exist after an address error
```

**Fails when:** Builds the address from the name, gets a 404 or the wrong route, and reports the matrix as missing.

### TC-28: A profile type or support flag it has not seen

Covers: 8. What this skill cannot promise

**Marks:** BLOCKED

**Ask:** "Read this matrix and tell me what it shows"

**Setup:** A profile whose `type` is not 0, or whose `isSupported` is false and is named in the ask. A repository without one cannot run this case.

**Passes when:** Says profile types other than 0 are undecoded, or that the profile is not supported, rather than reading it as if it were the verified shape.

**Check:**

```check
reply: says: profile types other than 0 are undecoded, or that the profile is marked unsupported
reply: not: gives a grid for the profile as though the type were verified
```

**Fails when:** Reads the profile as if it were type 0 and presents the grid with the same confidence.

### TC-29: A failure none of the listed causes explains

Covers: 9. When something fails

**Marks:** BLOCKED

**Ask:** "The matrix won't load, can you tell me why?"

**Setup:** A failure that matches none of the listed causes (an error code or response the skill does not list). The runner cannot easily inject one; a tenant that produces none cannot run this case.

**Passes when:** Says what it observed and stops, rather than guessing a cause.

**Check:**

```check
reply: says: what it observed (the request, the response or error code)
reply: says: none of the known causes explain it
reply: not: names a cause it did not observe
```

**Fails when:** Names the nearest listed cause (permissions, token, renaming) with confidence and keeps going.

## Invariants

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
> Test for the intersection separately and report it — see `SKILL.md` §4.1 and §8. TC-21 does.

> **This invariant was added because the skill shipped a snippet that passed TC-05 and TC-06 while
> being wrong.** A suite that cannot catch a defect in its own skill is not yet a suite.

### The two that matter most

**TC-05 and TC-06.** Everything else fails loudly enough to notice. A bad join does not: it
produces a grid that renders, has the right shape, and is wrong. If a run passes only one of these
two, it is almost certainly branching on `direction` — which is right for the common case and wrong
for the ones that matter.

### Setting up TC-06 if no profile exhibits it

`direction: "Both"` with mixed membership is the hard case and a repository may not have one.
To construct it, two elements need connectors of the profile's relationship type running **both
ways** between the same pair. That is an EA model change — build it in a scratch model, not in a
customer repository.

## Headings not covered

- Reference files — an index of the two reference files; it states nothing the skill does, refuses or warns about.

## Findings

- **TC-08 contradicts SKILL.md §4.1 as written.** TC-08's pass ("A connector with both ends in the same list: collected in `unplaced`") holds only when the two ends are in the same list and not in the intersection of the two lists. When both ends lie in the intersection, §4.1 says both membership branches match, the first wins and `unplaced` stays empty. The case is kept as written and its Setup narrows the condition; TC-21 covers the intersection case.
- **The session preflight is not checkable.** The opening of SKILL.md promises to read `prolaborate-session.md` and to run the `prol-start-here` preflight first. A `reply` or `tools` check cannot show that a file was read; no case tests it.
- **The limits SKILL.md §8 states cannot be exercised on a Westbrook fixture.** Behavior at scale beyond 1027 x 61, non-Package selector types, profile types 1 to 7, restricted-user views and the share and download flows are all stated as unverified. TC-09, TC-17, TC-18, TC-28 and TC-13/TC-14 test only that the skill says so, not that the stated limits are accurate.
- **`GetEAMatrixData` is a POST.** The `http` check is GET only, so no case can check the grid's data against the API; the invariant checks are `reply` checks and rest on how the runner grades a reply.
- **No case can verify that the skill read the API instead of scraping the table** (TC-02) or fetched only the settings (TC-03): the transcript's browser calls are not named in the `tools` grammar.
- **`GetMatrixShareURL` cannot be used as a check.** It mints a URL when called (reference §1), so TC-13 can check only the share flag with `CheckIsMatrixShareEnabled` and the reply.

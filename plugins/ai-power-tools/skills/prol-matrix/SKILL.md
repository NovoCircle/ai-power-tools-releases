---
name: prol-matrix
description: Read, filter, share and export Prolaborate relationship matrices through the web interface — find the right profile, join the response into a correct grid, and report what the cells mean. Use when the task names a relationship matrix, asks which elements are linked to which, or asks to export or share one. Never use it to create a matrix profile or to write matrix cells; both are Enterprise Architect work.
---

# Prolaborate — relationship matrices

*Verified against Prolaborate 5.6.1.40 on a Sparx-hosted tenant, driven as a Super Admin session
against a MySQL-backed repository, across all eleven matrix profiles it held. Section 8 says
plainly what that does not prove.*

A relationship matrix compares two sets of elements and shows which pairs are connected. Prolaborate
presents it as a grid: one set down the rows, the other across the columns, a marker in a cell where
a connector exists between that pair.

**Read [`../_shared/references/prolaborate-session.md`](../_shared/references/prolaborate-session.md)
before driving anything.** Most matrix failures are session failures wearing a disguise.

Run the `prol-start-here` preflight first if you have not already this session.

> **This skill cannot create a matrix profile. Read §1 before agreeing to build one.**
> The profile is defined in Enterprise Architect; Prolaborate only presents it.

---

## 1. What this skill can and cannot do

The Matrices list has **no Create button**, and every profile reports `type: EA`. The profile —
which packages are compared, which relationship, which direction — is an Enterprise Architect
artifact. Prolaborate reads it.

| Asked for | Answer |
|---|---|
| "What does this matrix show?" | Yes — §2, §3 |
| "Which applications support capability X?" | Yes — read and join, §4 |
| "Export this matrix" / "give me a link to it" | Yes — §6 |
| "Show only the rows that have something" | Yes — a display toggle, §5 |
| **"Create a matrix of A against B"** | **No.** Say so plainly and hand it to the EA skills — the profile is authored in EA and appears here once it exists |
| **"Tick that cell" / "link these two elements"** | **Not from the matrix.** That is an EA model write through the element-connector endpoints. See §7 |
| "What depends on this element?" | Not a matrix question — hand it to `prol-impact-analysis`. **Its objects behave oppositely to these:** Analyzer views are created in Prolaborate and keyed by a GUID, where a matrix profile is authored in EA and keyed by its name. Do not carry assumptions across |

Saying "I cannot create that here, it is built in EA" early is far better than driving the UI
looking for a button that does not exist.

---

## 2. Finding the profile, and the name trap

```js
const r = await fetch(`/api/relationshipmatrix/GetAllMatrixProfiles?repositoryId=${repoId}`,
  { headers: { Authorization: 'Bearer ' + token } }).then(r => r.json());
// [{ id, name, type, isSupported }]
```

Skip any row with `isSupported: false`.

> **The profile id *is* the matrix name.** `id` and `name` come back holding the same string.
> There is no GUID for a matrix profile anywhere in this API.

Three consequences, and they bite in order of how often:

1. **The view URL double-encodes the name.** The route is
   `/repositories/Matrix/View/repId/<repo>/<name>/<type>` where `<name>` is encoded **twice** —
   a space appears as `%2520`, not `%20`. Navigate from the list rather than building the link by
   hand; if you must build it, apply `encodeURIComponent` to the already-encoded name.
2. **Renaming the profile in EA breaks every saved link to it.** There is no stable identifier to
   fall back on. Worth warning the user about before they rename anything.
3. **A name containing `/`, `#`, `?` or `&` is a hazard.** Nothing stops an EA author creating one.

---

## 3. Reading what a profile compares

```js
const body = { repositoryId, profileId: name, profileType: type, userId };
const cfg = await fetch('/api/relationshipmatrix/GetEAMatrixProfileSettings',
  { method: 'POST', headers, body: JSON.stringify(body) }).then(r => r.json());
```

```json
{
  "sourceConfig": { "selectorName": "…", "selectorGuid": "{…}", "selectorType": "Package",
                    "selectorResourceType": "Package", "selectorContentType": "All",
                    "includeChildren": true },
  "targetConfig": { "…same shape…" },
  "linkConfig":   { "linkType": "Uses", "linkDirection": "Both" }
}
```

This maps one-to-one onto the six controls in the view header — SOURCE / TYPE, TARGET / TYPE,
RELATIONSHIP, DIRECTION — so it is the cheapest way to answer "what does this matrix show?" without
fetching any data.

**Read it before fetching the grid.** It tells you how big the selectors are, which matters because
§4 has no paging.

---

## 4. Reading the grid — the part that is easy to get wrong

```js
const data = await fetch('/api/relationshipmatrix/GetEAMatrixData',
  { method: 'POST', headers, body: JSON.stringify(body) }).then(r => r.json());
// { sourceElements[], targetElements[], connectors[] }
```

There is **no cell structure in the response**. You get rows, columns and edges as three flat
arrays, and you assemble the grid yourself.

### 4.1 Join by set membership. Never by direction.

> **You cannot tell which end of a connector is the row from any direction field.** Measured across
> all eleven profiles on the test tenant.

- **The profile's `linkConfig.linkDirection` does not predict the data.** Nine of eleven profiles
  declared `Both`, and their connectors came back `Both`, `Source -> Target` *and*
  `Target -> Source`. In the starkest case the profile said `Both` while all 550 of its connectors
  said `Target -> Source` and **not one** started in the source list.
- **The per-connector `direction` is better but `Both` is genuinely mixed.** One profile reporting
  `Both` split **29 of 58** connectors each way.

So do not branch on direction at all. Test membership:

```js
const srcIds = new Set(data.sourceElements.map(e => e.guid));
const tgtIds = new Set(data.targetElements.map(e => e.guid));
const unplaced = [];

for (const c of data.connectors) {
  const s = c.startElementGuid, e = c.endElementGuid;
  let row, col;
  if      (srcIds.has(s) && tgtIds.has(e)) { row = s; col = e; }
  else if (srcIds.has(e) && tgtIds.has(s)) { row = e; col = s; }
  else { unplaced.push(c); continue; }   // both ends in one list — see below
  // mark cell [row][col]
}
```

> **Test both ends as a pair, and keep what you cannot place.** Deciding the row and the
> column independently looks equivalent and is not: when both ends fall in the **same** list it
> yields a cell at `[start][start]` — a coordinate that does not exist, because that GUID is a row
> and never a column. That is worse than dropping the connector, because it fabricates data
> instead of losing it.

**Two different situations put both ends on one side, and only one of them reaches `unplaced`:**

| Situation | What happens |
|---|---|
| The selectors are **disjoint** and a connector joins two rows (or two columns) | Neither branch matches; it lands in `unplaced`. Correct |
| **Both ends** of a connector lie in the intersection of the two lists | **Both** branches match. The first wins, `unplaced` stays empty, and the placement is the direction guess this section exists to forbid — applied silently. A connector with only *one* end in the intersection still places correctly |

**How common is this? Unknown — and do not repeat the guess that it is common.** Every profile
measured was `Package` to `Package` with `includeChildren` on, which *can* overlap when the two
packages share a subtree, but the walk never recorded whether any pair actually did. The measured
direction table argues most of them did not: identical lists would put every connector's start in
`sourceElements`, and three profiles show **0** of 550, 62 and 384.

What is certain is that the shape is reachable by design — an "applications against applications"
dependency matrix has it deliberately. Test for it rather than assuming either way.

> **The invariant in [references/test-cases.md](references/test-cases.md) cannot catch this case**
> — whenever both ends of a connector are in the intersection, every clause passes whichever way
> round the placement went. Identical lists are the extreme of that, not the condition for it:
> **partial overlap is enough.** Detect it directly instead: if `sourceElements` and
> `targetElements` share any GUID, say that the grid's
> orientation is not determined by the data, and report it alongside the result. §8 carries this
> as a stated limit.

**Report `unplaced` rather than discarding it.** Those are real relationships you are not showing;
silently dropping them makes the matrix look complete while it under-reports.

> **A matrix joined from the wrong end does not error.** Depending on the data it comes out
> transposed, or partly transposed, or — in the overlap case above — populated with coordinates
> that do not exist. It is the same class of failure as the magnitude inversion in
> `prol-dashboards`: it renders, it looks reasonable, it is wrong.
>
> This consequence follows from the join logic and the measured direction data; **no wrong grid was
> built and inspected**, so treat the exact symptom as reasoning rather than observation. The
> defense is the invariant in [references/test-cases.md](references/test-cases.md), which checks
> your own output rather than trying to recognize a bad grid by eye.

**`startObjectId` and `endObjectId` are `null`.** Join on the GUIDs only.

### 4.2 Size before you ask

Element entries are **full element records** — around 27 fields each, including `notes`, `author`,
`created`, `modified`, `status` and `parentGuids`. The payload scales with the element count, not
with how many cells are filled, and **there are no paging fields**.

Measured: the largest profile was **1027 x 61 with 758 connectors** — over 62,000 cells, 99% of
them empty, every row and column returned.

Read §3 first and warn the user before pulling a profile with large selectors.

---

## 5. Filters in the view are display-only

`HIDE EMPTY SOURCE` and `HIDE EMPTY TARGET` change what is drawn. The request behind the same
screen still returned all 184 source elements with both toggles on.

> They cost nothing to toggle and they save nothing. Do not offer them as a way to make a big
> matrix cheaper — they are a readability control.

`Display Label` switches cell text between element **Name** and **Stereotype**. It changes the
label only, never the join.

---

## 6. Sharing and export

Both sit in the view header, and both reach outside the session, so **neither happens without the
user asking for it**:

- **Share** produces a private URL via `GetMatrixShareURL`, gated by a repository-level flag
  (`CheckIsMatrixShareEnabled`). A share link is a distribution decision — confirm before creating
  one, and never enable the repository flag on the user's behalf.
- **Download** writes a file. Ask first, and say what the file will be called.

Neither was exercised on the test tenant beyond observing that `GetMatrixShareURL` fires on page
load and returns 200. Treat the flow as unverified and read the screen as you go.

---

## 7. Writing cells is an EA model write

A matrix cell is a connector. Setting one means `CreateElementConnector`; clearing one means
`DeleteElementConnector`. These are **Enterprise Architect model writes** that happen to be visible
through a matrix.

> **Do not write matrix cells from this skill.** Not with a baseline, not with confirmation, not
> "just one". There is no dry run and no undo, and a connector written here is a change to the
> customer's model that the matrix merely happens to display.

Hand it to the EA skills, which own model change and the baseline that has to precede it
(`ea-change-management`). If the user asks for it directly, say that this skill reads matrices and
that writing one is EA work — do not look for a route around it.

The endpoints are named in [references/reading-a-matrix.md](references/reading-a-matrix.md) §9 so
you can **recognize** a write path and refuse it, not so you can drive one.

---

## 8. What this skill cannot promise

- **One identity.** Everything was verified as a **Super Admin**, which short-circuits
  Prolaborate's authorization checks. The element payload carries `notes` and `author` on every
  row, so a restricted user may legitimately see less. Nothing here proves what they see.
- **One selector type.** All eleven profiles were `Package` to `Package`. Other `selectorType`
  values are undecoded.
- **Overlapping selectors are untested, and membership alone cannot resolve them.** Every measured
  profile behaved as though its two selectors were disjoint; the walk never recorded whether any
  pair overlapped. When they do overlap an element can appear in **both** lists, and then both
  membership tests in §4.1 succeed — the join picks the first branch, which is a guess. Say so
  rather than presenting such a grid as certain.
- **One profile type.** All were `type: 0`. The enum declares `Type0`…`Type7`; the rest are
  unknown, as is whether `isSupported: false` ever appears in practice.
- **Share and download are unverified**, as §6 says.
- **No write path was exercised.** §7 is read from the API surface, not measured.
- **Nothing establishes behavior at scale.** The largest profile read was 1027 x 61. How the
  endpoint or the browser behaves well beyond that is unknown, and there is no paging to fall back
  on.

Say which of these applies rather than letting an action fail.

---

## 9. When something fails

1. **Empty grid, no error** — check the join before anything else (§4.1). A transposed join
   against a sparse matrix looks exactly like an empty one.
2. **A grid that is populated but wrong** — same cause, different symptom, and the one that does
   not announce itself. Check that every row GUID is in `sourceElements` and every column GUID is
   in `targetElements`; a join that decided the two ends independently will have invented
   coordinates that satisfy neither. Then check what `unplaced` holds.
3. **`ID2019`** — the token aged out. Navigate to refresh, re-read `sessionStorage`, retry once.
4. **`ID2095`** — authenticated but not permitted. Check `CheckUserHasMatrixAccess` and the
   person's Access Permissions. A permissions answer, not a bug.
5. **404 on a matrix URL** — almost always the double-encoding (§2) or a profile renamed in EA.
   Re-read `GetAllMatrixProfiles` and navigate from the list.
6. **The request never returns** — check the selector sizes from §3. A 1000-row profile returns
   every element record in one response.

If none of these explain it, say what you observed and stop.

## Reference files

- [references/reading-a-matrix.md](references/reading-a-matrix.md) — the endpoints, the response
  shapes, the measured direction table, and worked join code.
- [references/test-cases.md](references/test-cases.md) — acceptance tests, each with what a failing
  run looks like.

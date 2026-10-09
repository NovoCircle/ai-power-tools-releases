# Reading a relationship matrix — endpoints, shapes and the join

Everything here was measured against a live Prolaborate 5.6.1.40 tenant as a Super Admin, across
eleven matrix profiles. Where something was not measured it says so.

Example organization is Westbrook Bank throughout.

---

## 1. The three calls, in order

| Step | Call | Why |
|---|---|---|
| 1 | `GET /api/relationshipmatrix/GetAllMatrixProfiles?repositoryId=<guid>` | List the profiles |
| 2 | `POST /api/relationshipmatrix/GetEAMatrixProfileSettings` | What the profile compares, and how big it is |
| 3 | `POST /api/relationshipmatrix/GetEAMatrixData` | The rows, columns and edges |

**Do step 2 before step 3.** It is tiny, it answers most questions on its own, and it tells you how
large step 3 will be — which matters because step 3 has no paging.

Request body for steps 2 and 3 is identical:

```json
{ "repositoryId": "<repo guid>", "profileId": "<matrix name>", "profileType": 0, "userId": "<sub>" }
```

Supporting calls:

| Call | Returns |
|---|---|
| `POST /api/relationshipmatrix/CheckUserHasMatrixAccess` | a single `hasAccess` bool |
| `GET /api/relationshipmatrix/CheckIsMatrixShareEnabled` | repository-level share flag |
| `GET /api/relationshipmatrix/GetMatrixShareURL?RepositoryId=&ProfileId=&ProfileType=` | private share URL. **Not a read — ask first.** See below |

> **`GetMatrixShareURL` is a write wearing a read's clothes.** It is a GET, it sits in a table of
> supporting calls, and under a doctrine whose headline rule is *read through the API* it looks
> like one. It is not: it mints a distribution URL for a customer's matrix. **Confirm with the
> person before calling it**, and never enable the repository-level share flag on their behalf.
> It does fire on page load, so seeing it in a network log is not evidence that calling it
> yourself is harmless.

Verb choices are not intuitive: `GetEAMatrixData` is a **POST**, `GetMatrixShareURL` is a **GET**.
The route `CheckUserHasMatrixAccess` maps to a method named `CheckMatrixAccess`.

## 2. `GetAllMatrixProfiles`

```json
[ { "id": "Westbrook Capability Map", "name": "Westbrook Capability Map",
    "type": 0, "isSupported": true } ]
```

**`id` and `name` hold the same string.** A matrix profile has no GUID in this API.

- **Skip `isSupported: false`.** Not observed on the test tenant; the field exists, so honor it.
- All eleven profiles were `type: 0`. `MatrixType` declares `Type0`…`Type7`; the others are
  **undecoded**.

### The URL is double-encoded

```
/repositories/Matrix/View/repId/<repo-guid>/Westbrook%2520Capability%2520Map/0
```

`%2520` is an encoded `%20` — the name is encoded, then the encoded form is encoded again. Prefer
navigating from the list. If you must construct it:

```js
const seg = encodeURIComponent(encodeURIComponent(profileName));
```

Because the name is the identifier, **renaming the profile in EA breaks every saved link**, and
a name containing `/`, `#`, `?` or `&` is a hazard. Nothing in EA prevents one.

## 3. `GetEAMatrixProfileSettings` — verified shape

Earlier API research recorded this response as *"declares no public properties — shape
unverified"*. Measured, it is:

```json
{
  "sourceConfig": {
    "selectorName": "Business Capabilities",
    "selectorGuid": "{AAAA0001-0000-4000-8000-000000000001}",
    "selectorType": "Package",
    "selectorResourceType": "Package",
    "selectorContentType": "All",
    "includeChildren": true
  },
  "targetConfig": { "…identical shape…" },
  "linkConfig": { "linkType": "Uses", "linkDirection": "Both" }
}
```

Maps directly onto the view header:

| Response field | Header control |
|---|---|
| `sourceConfig.selectorName` | SOURCE |
| `sourceConfig.selectorContentType` | TYPE (source) |
| `targetConfig.selectorName` | TARGET |
| `targetConfig.selectorContentType` | TYPE (target) |
| `linkConfig.linkType` | RELATIONSHIP |
| `linkConfig.linkDirection` | DIRECTION |

All eleven profiles were `Package` to `Package` with `includeChildren: true`. Other `selectorType`
values are **untested**.

## 4. `GetEAMatrixData` — three arrays, no grid

```json
{ "sourceElements": [ … ], "targetElements": [ … ], "connectors": [ … ] }
```

### Element entries are full element records

About 27 fields each: `guid`, `name`, `alias`, `notes`, `author`, `created`, `modified`,
`objectType`, `baseType`, `stereotype`, `technology`, `classifierName`, `complexity`, `difficulty`,
`priority`, `status`, `phase`, `keywords`, `language`, `version`, `locktype`, `locked`,
`parentGuids`, `icon`, `enableJournal`, `enableEACollaboration`, `classifierIdentifier`.

A grid needs `guid` and `name`. Everything else is weight — and `notes` and `author` are content
that a restricted user might not be entitled to, which is why §7 flags the identity caveat.

### Connector entries

```json
{ "technology": null, "id": 0, "guid": "{AAAA0002-0000-4000-8000-000000000002}", "name": null,
  "boundDirection": null, "midLabel": null, "baseType": "Association",
  "stereotype": "Uses", "stereotypeField": "Uses",
  "direction": "Target -> Source",
  "startObjectId": null, "endObjectId": null,
  "startElementGuid": "{AAAA0003-0000-4000-8000-000000000003}",
  "endElementGuid":   "{AAAA0004-0000-4000-8000-000000000004}" }
```

Measured as always null across every profile: `name`, `boundDirection`, `midLabel`,
`startObjectId`, `endObjectId`. **Only the GUIDs are usable for the join.**

`stereotype` and `stereotypeField` carried the same value throughout.

> **`technology` is shown null deliberately.** A real payload may carry an MDG id here.
>
> **An MDG *can* declare connector stereotypes**, and the Westbrook reference model's does: WBA
> 1.1.1 declares `Uses`, `Flows` and `realizes`. In `t_connector.Stereotype` they are still stored
> bare (the binding is in `t_xref`; measured 2026-10-07), and what Prolaborate's own payload would
> carry in `technology` for them was not re-measured, which is why the example above still shows
> null. `prol-dashboards`' `references/data-probes.md` covers the storage form.
>
> So the safe reading is narrower than "never": **a technology value beside a stereotype is not by
> itself evidence that the technology declares it.** Check the MDG before concluding either way.

## 5. The direction measurement

For every connector in every profile, the test was: is `startElementGuid` a member of
`sourceElements`? Profile names replaced with `M1`…`M11`.

| Profile | `linkConfig.linkDirection` | per-connector `direction` | connectors | start in source |
|---|---|---|---|---|
| M1 | Both | Both | 154 | 154 |
| M2 | Both | Target -> Source | 550 | **0** |
| M3 | Target -> Source | Target -> Source | 62 | **0** |
| M4 | Source -> Target | Source -> Target | 758 | 758 |
| M5 | Both | Source -> Target | 28 | 28 |
| M6 | Both | Both | 58 | **29** |
| M7 | Both | Source -> Target | 31 | 31 |
| M8 | Both | Source -> Target | 28 | 28 |
| M9 | Both | Source -> Target | 2 | 2 |
| M10 | Both | Target -> Source | 384 | **0** |
| M11 | Both | Both | 76 | **74** |

What this establishes:

**The profile's `linkDirection` is not a usable signal.** Nine of eleven say `Both`; their
connectors come back in all three states. M2 is the clearest refutation — profile `Both`, all 550
connectors `Target -> Source`, zero starting in the source list.

**Per-connector `direction` is not usable either, because `Both` is mixed.** M6 split 29 of 58.
M11 split 74 of 76. A rule like "if direction is Both then start is the row" is right most of the
time and wrong often enough to produce silently corrupt output.

**Set membership is the only reliable join.**

## 6. The join

```js
function buildGrid(data) {
  const srcIds = new Set(data.sourceElements.map(e => e.guid));
  const tgtIds = new Set(data.targetElements.map(e => e.guid));
  const name   = new Map([...data.sourceElements, ...data.targetElements]
                           .map(e => [e.guid, e.name]));

  const cells = new Map();            // "rowGuid\u0000colGuid" -> connector[]
  const unplaced = [];

  for (const c of data.connectors) {
    const s = c.startElementGuid, e = c.endElementGuid;
    let row, col;
    if (srcIds.has(s) && tgtIds.has(e))      { row = s; col = e; }
    else if (srcIds.has(e) && tgtIds.has(s)) { row = e; col = s; }
    else { unplaced.push(c); continue; }     // see the warning below
    const key = row + '\u0000' + col;
    if (!cells.has(key)) cells.set(key, []);
    cells.get(key).push(c);
  }
  return { cells, unplaced, name };
}
```

> **Collect what you could not place, and report it.** A connector whose ends are not one in each
> list is real data you are dropping. Silently skipping it is how a matrix comes out looking
> complete and under-reporting.
>
> **`unplaced` catches only the disjoint case.** If **both** ends of a connector lie in the
> intersection of the two lists, both membership tests succeed, the first branch wins and nothing
> reaches `unplaced` — the orientation is then a guess. A connector with one end in the
> intersection and one outside still places correctly.
>
> Test `sourceElements` and `targetElements` for a shared GUID and report it. That test is
> deliberately conservative: it flags any overlap, including profiles where every connector happens
> to place correctly. Over-reporting an uncertainty is the safe direction.

**A cell can hold more than one connector.** Two elements may be linked several times, by different
relationship types or in both directions. The grid shows a marker; the underlying data is a list.
Count connectors, not cells, when reporting totals — and say which you counted.

## 7. Size

No paging fields exist on the request or the response. Measured extremes:

| Profile | Rows x Columns | Cells | Connectors | Filled |
|---|---|---|---|---|
| M4 | 1027 x 61 | 62,647 | 758 | 1.2% |
| M10 | 1028 x 103 | 105,884 | 384 | 0.4% |
| M9 | 20 x 8 | 160 | 2 | 1.3% |

Every element record comes back regardless of whether its row is empty. Read the profile settings
first (§3) and tell the user what they are about to pull.

## 8. Display controls that do not change the query

| Control | Effect |
|---|---|
| `HIDE EMPTY SOURCE` / `HIDE EMPTY TARGET` | Hides rows or columns with no connector. **Display only** — measured with both on, the response still carried all 184 source elements |
| `Display Label` — Name / Stereotype | Cell caption only |
| `Refresh` | Re-issues steps 2 and 3 |

None of these reduce payload size.

## 9. Writes — not from here

A cell is a connector, so setting or clearing one is an **EA model write**:

| Call | Effect |
|---|---|
| `POST /api/element/CreateElementConnector` | Creates a connector; new guid in `connectorInfo[].guid` |
| `DELETE /api/element/DeleteElementConnector` | Clears it. **Query parameters, no body** |
| `POST /api/element/UpdateConnector` | Edits details; returns `List<String>`, meaning unverified |

> **This table is here so you can recognize a write path and refuse it, not so you can drive one.**
> Writing a connector is a change to the customer's model. It does not happen from this skill —
> not with a baseline, not with confirmation. Hand it to the EA skills, which own model change and
> the baseline that precedes it.

None of these were exercised. This section is read from the API surface, not measured.

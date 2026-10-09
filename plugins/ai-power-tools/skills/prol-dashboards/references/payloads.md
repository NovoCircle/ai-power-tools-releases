# Dashboard payloads and vocabulary

Detail supporting [`../SKILL.md`](../SKILL.md) §3, §4 and §5. Read those sections first — this file
is the data, not the decisions.

Observed against Prolaborate 5.6.1.40 as a Super Admin session. Field names and types are exactly as
seen on the wire. Placeholders: `<repoId>`, `<dashboardId>`.

---

## 1. The read model

`GET /api/dashboard/DashboardRendring?DashboardId=<dashboardId>&isCheckAccess=true` returns the
whole dashboard.

```jsonc
{
  "id": "<dashboardId>", "repositoryId": "<repoId>",
  "name": "Westbrook Bank - Application Portfolio",
  "notes": "", "status": "Active",
  "isDefault": 0,                        // number, not boolean
  "isEnabled": 1,                        // number, not boolean
  "template": "0",                       // string at this level
  "displayDescription": true,            // boolean on read
  "isCommonDropdownRequired": false, "isDynamicDropdown": false,
  "created":  "1/16/2025 9:54:22 AM",    // US-format local string
  "modified": "7/16/2025 7:38:28 AM",    // US-format local string - this is the real one
  "modifiedDate": "0001-01-01T00:00:00", // ISO and always zeroed - ignore it
  "createdBy": "<userId>",
  "dashboardSettings": "null",           // the literal STRING "null"
  "propertyFilters": null, "commonFqName": null, "reviewId": null,
  "type": null, "userType": null, "templateValue": null,
  "repositoryName": null, "createdByUserName": null,
  "dashboardUsers":       [ { "id": "..", "dashboardId": "..", "userId": ".." } ],
  "dashboardUserGroups":  [ { "id": "..", "dashboardId": "..", "userGroupId": ".." } ],
  "dashboardUserRoles":   [],            // item shape unobserved - it was empty
  "dashboardReviewUsers": [ { "id": "..", "dashboardId": "..", "userId": ".." } ],
  "dashboardWidgets":     [ /* see below */ ]
}
```

### Widgets and blocks, on read

```jsonc
"dashboardWidgets": [{
  "id": "..", "dashboardId": "..",
  "name": "Untitled-41",                 // defaults like this - NOT an identifier
  "aliasName": "",
  "widgetTypes": ["Cards"],              // array of resolved names, not a single enum field
  "x": 0, "y": 0, "cols": 2, "rows": 1,
  "sizeX": 2, "sizeY": 1, "columnId": 0, "rowId": 0,
  "template": 0,                         // NUMBER here, string on the dashboard
  "widgetSettings": {
    "titleBackground": "#ffffff", "titleText": "#212529",
    "bodyBackground": "#90b1ba", "border": "#ffffff",
    "enableMaximizeWidget": true
  },
  "configData": null,                    // null on every widget observed
  "notes": null, "repositoryId": null, "repositoryName": null,
  "widgetLibraryId": null, "isWidgetNameExistInWidgetLibrary": false,
  "dashboardWidgetBlocks": [{
    "id": "..", "dashboardWidgetId": "..",
    "dashboardWidgetBlockTypeId": "<guid>",   // a GUID on read, a short string on write
    "title": "..", "notes": "..",
    "position": 1,                       // 1-based, recomputed on every structural change
    "eaArtifactGuid": "",
    "isConfigured": 1,                   // number
    "isUpdate": false,                   // boolean
    "isDataConfigurationModified": false
  }]
}]
```

A widget holds **one or two** blocks. Across 21 widgets the resolved type counts were Cards 8,
Charts 8, Html 12, Image 1, Reports 1 — 30 types across 21 tiles, which is how you can tell the tile
and the content are different things.

---

## 2. The `Create` write schema

`POST /api/dashboard/Create` → `200 {"responseId":"<newDashboardId>","additionalInfo":null}`.

Captured from a real save of a dashboard with one Text widget. **Build writes from this shape, never
from a read.**

```jsonc
{
  "repositoryId": "<repoId>",
  "name": "Westbrook Bank - Portfolio Health",
  "aliasName": "Westbrook Bank - Portfolio Health",   // duplicated at dashboard level
  "notes": "",
  "dashboardSettings": null,                 // real null on write
  "template": "0",
  "type": null, "reviewId": null,
  "displayDescription": 0,                   // NUMBER on write, boolean on read
  "isEnabled": 1,
  "userId": "",
  "dashboardUsers": [ { "userId": "" } ],    // one entry carrying an empty id
  "dashboardUserGroups": [], "dashboardUserRoles": [], "dashboardReviewUsers": [],
  "dashboardWidgets": [{
    "x": 0, "y": 0, "cols": 2, "rows": 1,    // no sizeX / sizeY / columnId / rowId on write
    "dashboardId": "",                        // empty placeholder - the server fills it
    "name": "Portfolio summary",
    "aliasName": "Portfolio summary",
    "template": 0,
    "tipMsg": "", "mode": "",                 // write-only
    "widgetSettings": {
      "titleBackground": "#ffffff", "titleText": "#212529",
      "bodyBackground": "#ffffff", "border": "#ced4da",
      "enableMaximizeWidget": true
    },
    "dashboardWidgetBlocks": [{
      "dashboardWidgetBlockTypeId": "TEXT",   // short STRING on write
      "title": "Text",
      "notes": "<p>Portfolio summary for Westbrook Bank.</p>",
      "updatedNotes": "<p>Portfolio summary for Westbrook Bank.</p>",  // write-only duplicate
      "emitModal": "Dashtext",                // write-only dialog discriminator
      "eaArtifactGuid": "",
      "isConfigured": 1,
      "position": 1,
      "isUpdate": true
    }]
  }]
}
```

Block `notes` is HTML, not plain text.

---

## 3. Write is not read — the field-by-field differences

| Field | On write | On read |
|---|---|---|
| `dashboardWidgetBlockTypeId` | short string, e.g. `TEXT` | a GUID |
| `displayDescription` | number `0` / `1` | boolean |
| `dashboardSettings` | real `null` | the string `"null"` |
| `dashboardId`, `userId` | `""` placeholders | real GUIDs |
| `emitModal`, `updatedNotes`, `tipMsg`, `mode` | present | absent |
| `sizeX`, `sizeY`, `columnId`, `rowId` | absent | present |

> **A read-modify-write round trip is broken by design, not by a bug.** Posting a read back sends
> GUIDs where the server expects type strings, booleans where it expects numbers, and drops every
> write-only field the configuration dialog sets. Populate the write schema field by field instead.

Also inconsistent, and worth knowing before you write a parser:

- `template` is the string `"0"` on the dashboard and the number `0` on a widget.
- `isDefault`, `isEnabled` and `isConfigured` are numbers; `displayDescription` on read,
  `isUpdate` and `enableMaximizeWidget` are booleans.
- `dashboardSettings` is the string `"null"` on read — `JSON.parse` on it throws, and a truthiness
  check on it passes. Both are wrong.
- `modifiedDate` is ISO and always zeroed; the real timestamp is `modified`, in US month-first
  order.
- The widget color settings appear under a fourth set of names inside the editor component
  (`titlebgcolor`, `titlecolor`, `bodybgcolor`, `bordercolor`). The saved payload uses
  `titleBackground`, `titleText`, `bodyBackground`, `border`.

---

## 4. The widget type vocabulary

Four vocabularies name the same eleven things.

| Picker label | Write string | `emitModal` | Read type |
|---|---|---|---|
| Text | `TEXT` | `Dashtext` | `Text` |
| Rich Text | `HTML` | `DashHtml` | `Html` |
| Images | `IMAGE` | `DashImage` | `Image` |
| Charts | `CHART` | `DashChartWidget` | `Charts` |
| Reports | `REPORT` | `DashReportWidget` | `Reports` |
| Cards | `CARD` | `DashCard` | `Cards` |
| Dashboards | `DASHBOARD` | `DashboardWidget` | — |
| Integration Reports | — | `DashIntegrationReport` | — |
| Hyperlinks | `HYPERLINK` | — | — |
| Reviews List | `REVIEW_LIST` | — | — |
| Diagrams | — | — | — |

> **Only the Text row is verified end to end** — write string and `emitModal` from a captured
> `Create` payload, read type from reading the saved dashboard back. An earlier draft of this table
> gave the Text read type as `Html`; that was inferred from another dashboard's type counts and was
> wrong. It is `Text`. It comes from a captured `Create` payload. Every other row
> pairs a write-string list with a discriminator list **by name similarity**, and the two lists do
> not reconcile — nine write strings against eight discriminators, with no `DIAGRAM` string found
> despite Diagrams being in the picker. **Confirm a row before relying on it**: add that widget type
> in the interface once and capture the payload.

Picker categories, which is how a person will describe what they want:

| Category | Widgets |
|---|---|
| General | Text, Images, Rich Text |
| EA | Hyperlinks, Diagrams, Charts, Reports, Cards |
| Prolaborate | Reviews List, Dashboards |
| Integration | Integration Reports |

Discriminators that are not widget types: `AddWidget`, `ExportReportsDownload`,
`RefreshDiscussions`, `linkedDocumentViewModal`.

---

## 4a. How a widget binds to a saved report

Settled from the product's own MS SQL schema (5.6), not inferred.

> **There is no foreign key and no column linking a block to a saved report.** The reference lives
> *inside the block's `Notes` field*, which holds JSON, as `profileReferenceId`.

That single fact explains several things that otherwise look like gaps:

- No create or update model declares a profile field — because the binding is inside a string.
- `configData` on the widget is always null — it is not the carrier.
- The read path returns a parsed `generalConfiguration` from `GetWidgetBlockDetail`, while the write
  path just sends `Notes`.

A block is in one of two modes:

| Mode | `profileReferenceId` | Queries |
|---|---|---|
| **Reference** — "Choose from existing profile" | set | come from the report |
| **Own query** — "Configure Now" | empty | stored inline on the block |

`chartConfigurationCreationMode` **3 = Configure Now** (own-query mode). Other values undecoded.

> **Consequence for editing.** `Notes` is also where a Text block's HTML body lives. Any code that
> treats `Notes` as prose, truncates it, or rewrites it will destroy a chart block's binding and its
> queries. **Never touch `Notes` on a block you did not author.**

### Reference semantics

The vendor's UI calls these "Report Configuration" and tracks consumers in a **Report Used In**
list. Deleting a report that is referenced is **blocked in the UI**. Release notes for 5.4 state
that placeholder changes propagate to everything referencing the report, and dashboard export
bundles referenced reports as dependencies.

**Still unproven:** whether the server resolves the referenced report *live at render time*. The
block carries both a reference and queries, so a stale copy is still possible. Treat propagation as
likely but unverified.

Editing a referenced query inside a block **detaches it from the report** — see `../SKILL.md` §5.

---

## 5. Capturing a payload yourself

Prolaborate holds the whole authoring session in the browser and writes once on Save, so an
interceptor must survive the navigation that Save triggers. Write captures to `sessionStorage`,
which survives a same-tab navigation; a `window`-scoped variable does not.

```js
(() => {
  const put = r => { const a = JSON.parse(sessionStorage.getItem('__cap') || '[]');
    a.push(r); sessionStorage.setItem('__cap', JSON.stringify(a)); };
  const orig = window.fetch;
  window.fetch = async function (...args) {
    const url = typeof args[0] === 'string' ? args[0] : args[0] && args[0].url;
    const init = args[1] || {};
    const res = await orig.apply(this, args);
    if (/\/api\//.test(url) && (init.method || 'GET') !== 'GET') {
      put({ url, method: init.method, body: String(init.body).slice(0, 6000), status: res.status });
    }
    return res;
  };
  sessionStorage.setItem('__cap', '[]');
})();
```

Read it back after the save with `JSON.parse(sessionStorage.getItem('__cap'))`. Prolaborate also
uses `XMLHttpRequest` on some screens, so patch both if a capture comes back empty.

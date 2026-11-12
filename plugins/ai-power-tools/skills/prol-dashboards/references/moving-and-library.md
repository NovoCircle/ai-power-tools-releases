# Moving dashboards, defaults and the Widgets Library

Detail supporting [`../SKILL.md`](../SKILL.md) §11. Observed against Prolaborate 5.6.1.40 as a Super
Admin session, on a repository moved between two EA repositories. A restricted user was not tried.
Placeholders: `<repoId>`, `<dashboardId>`.

---

## 1. Export and import between repositories

**Export.** On the Dashboards list, tick the dashboards and choose Export (with user permissions). The
result is a zip holding the dashboards, their images, their user groups and the repository's modeling
languages.

**Import.** Import the zip into the other repository. What the import does and does not do:

| Carried over | Not carried over |
|---|---|
| Layout and widgets | The repository id inside other links (it still names the old repository) |
| Links between the exported dashboards' own tiles, remapped to the new copies | Package numbers inside queries |
| | Links to Widgets Library items: they become standalone copies |
| | The bundled modeling languages: the import did not add them |
| | The target's default dashboard: unchanged |

**Checklist after an import.** Do each step on every imported dashboard, and state what you found.

1. Compare the widget count and titles with the source dashboard.
2. Open each link that goes to another place in Prolaborate and check that it names the target
   repository. Links outside the exported set still carry the old repository id and must be repointed.
3. Find every query that names a package by number. Package numbers belong to one repository and do
   not carry across, so replace them with the target's, then run each query (Execute) and compare the
   row count with the source.
4. Treat each former library widget as an ordinary copy. A later change to the library item will not
   reach it.
5. Check that the target repository has the modeling languages the dashboards depend on, since the
   import does not add them.
6. If one of the imported dashboards should be the repository default, set it (see section 2 here).
7. Check who can see each dashboard. The export was made with user permissions, but the target's users
   and groups are the target's own.

The model's own Prolaborate repository id is a separate matter; see `prol-start-here` section 5.

---

## 2. Default and status

Two different defaults, set in two different places:

| Action | Where | Result |
|---|---|---|
| Make Default | On the dashboard's own page | A personal default: only for the signed-in person |
| Make Default | On the Dashboards list, under More | The repository default (`isDefault` reads `2`) |

- The repository default cannot be deactivated.
- A dashboard's status (Active or not) is changed only on its Edit page. The list has no action for it.

---

## 3. The Widgets Library

The library has its own Export and Import, separate from the dashboard export.

- **Edit before importing.** The exported `Widgets.json` can be edited, for the repository and
  dashboard ids it carries, before it is imported.
- **A tile cannot be saved to the library from its own menu.** Copy there duplicates the tile on the
  dashboard and adds nothing to the library.
- **Editing a Rich Text library item.** Typing into the editor is unreliable. Read and write the
  content through the editor instance, then click Save:

```js
const editor = document.querySelector('.ck-editor__editable').ckeditorInstance;
const html = editor.getData();            // read
editor.setData('<p>Replacement text</p>'); // write
```

Re-open the item afterwards and confirm the text persisted.

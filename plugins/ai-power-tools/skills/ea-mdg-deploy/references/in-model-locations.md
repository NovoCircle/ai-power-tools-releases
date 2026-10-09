# The two in-model Locations, measured

Back to [SKILL.md](../SKILL.md). Everything here was measured on EA 17.1 Build 1716 against a copy of
the Westbrook Bank reference model, or read from Sparx's 17.1 user guide and EA's own type library.

## What each route stores

| | Location: **Model** | Location: **Project** |
|---|---|---|
| Written by | Specialize ▸ Publish Technology ▸ Import MDG Technology ▸ Import to Model; `Repository.ImportPackageAsMDGTechnology(<package GUID>)`; `install_mdg(scope="model")` | `Repository.ImportTechnology(xml)`; `install_mdg(scope="embedded")` |
| Stored in | one `t_document` row: `DocType='TECHNOLOGY'`, `DocName` = the technology id, `BinContent` = a ZIP holding `str.dat`, the whole MDG file in UTF-16 | `t_trxtypes`: an `MDGTechnology` row (diagram profile in `Style`) and one `UMLTechProfile` row per UML profile (in `Notes`) |
| Toolbox pages | kept; the designed pages appear and switch with the diagram type | **not kept**: an input with three toolbox pages left none; EA shows one automatic page built from the stereotypes |
| Sparx's guide says | Import to Model stores the technology in the model, for every user of that model | `ImportTechnology` "applies to technologies imported into pre-7.0 versions of Enterprise Architect" |

EA's COM interface has exactly two technology-import methods, `ImportTechnology` and
`ImportPackageAsMDGTechnology`. None imports a technology **file** at Location: Model; for a file,
use the Import to Model dialog.

## `ImportPackageAsMDGTechnology`

- Takes the `«mdg technology»` package's **GUID**.
- With `SuppressEADialogs = True` and `EnableUIUpdates = False`: returned `True` in under 2
  seconds, raised no dialog, wrote one `t_document` row, and EA used the new copy in the open
  session at once.
- It does not touch `t_trxtypes`. Checking that table reports a failure that did not happen, which
  is how this command was once recorded as "changes nothing".
- Importing the same package again left one row, not two.

## Restart EA before judging the toolbox

After an install at Location: Model in a running EA (and after removing a Project copy of the same
id), the diagram types resolve and the toolbox pages are listed at once in the Toolbox's technology
menu (≡ ▸ the technology), but **the automatic switch to them when a diagram opens is not dependable
until EA restarts**. Measured: once a project reopen was enough; another time neither a project
reopen nor switching to another model and back was. After a restart all three Westbrook diagram
types switched to their pages, and dragging an item created a correctly bound element
(`FQName=WestbrookBankArchitecture::WBAVendorSystem`, its tagged values present).

So: install, restart EA, then run the verification checklist. Restarting EA is the user's call.

## The same id at both Locations

Manage Technology lists two entries, both enabled, and EA answers `GetTechnologyVersion` from the
**Project** copy. `get_mdg_from_runtime` (server 3.6.0 or later) answers from the same copy and
lists the other under `provenance.also_stored`.

`DeleteTechnology(<id>)` removes the Project rows only; the `t_document` row stays. A Location:
Model copy is removed in Manage Technology (Remove).

## Loaded is not enabled

A technology disabled in Manage Technology still answers `IsTechnologyLoaded` True. Check
`IsTechnologyEnabled` as well; `get_mdg_from_runtime` reports it as `enabled`, and as
`source: "registered_not_enabled"` when it is off.

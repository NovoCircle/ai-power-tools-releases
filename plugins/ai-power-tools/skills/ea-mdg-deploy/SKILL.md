---
name: ea-mdg-deploy
description: Deploy and test a Sparx EA MDG Technology — embed it into a .qea model file or install application-wide, then verify it works correctly. Use after authoring or modifying an MDG XML file.
---

# Deploying and Testing a Sparx EA MDG Technology

*Verified against EA 17.0 Build 1704; the two in-model storages below measured on EA 17.1 Build 1716.*

## Deployment Modes

A technology stored **inside the model** reaches everyone who opens it. EA 17.1 keeps it in one
of two places, and Manage Technology's **Location** field says which:

| Mode | Location (Manage Technology) | Written by | Stored in | Keeps |
|------|------------------------------|------------|-----------|-------|
| **In the model, whole technology** | `Model` | Specialize ▸ Publish Technology ▸ Import MDG Technology ▸ **Import to Model**; `Repository.ImportPackageAsMDGTechnology`; `install_mdg(scope="model")` | one `t_document` row, `DocType='TECHNOLOGY'` | Everything, **toolbox pages included** |
| **In the model, legacy route** | `Project` | `Repository.ImportTechnology`; `install_mdg(scope="embedded")` | `t_trxtypes` rows | UML profiles and the diagram profile. **No toolbox pages**: EA shows an automatic page built from the stereotypes |
| **This machine only** | the file name (in APPDATA) | a copy in `%APPDATA%\Sparx Systems\EA\MDGTechnologies\`; `install_mdg(scope="user")` | the file | Everything |

**Prefer Location: Model.** Sparx documents `ImportTechnology` as the pre-7.0 route; it still suits
a technology with no toolbox pages, and `install_mdg(scope="embedded")` lists what it did not store.
**Never keep one tech ID at two Locations**: EA lists both and answers from the Project copy.
Measurements and details: [references/in-model-locations.md](references/in-model-locations.md).
An application-level copy of an id the model also holds shows as a duplicate entry with an
asterisk (`*`), which cannot be removed via the UI.

### Model vs. runtime technologies — and the search-path auto-registration trap

The table above is about *where the file lives*. Separately, a technology can be **model-driven**
(built from profile packages inside a repository — see `ea-mdg-model-build`) or **direct-XML**
(hand-authored or generated once — this skill's usual case). Either kind can be deployed either
Model-embedded or Application-level; the two axes are independent.

⚠ **EA auto-registers any MDG file found on its search path**, regardless of deployment mode. The
path list is at `Manage Technology ▸ Advanced`, and it routinely includes a user's `Downloads`
folder. A build (or a stray copy) written there registers itself silently, shadows the intended
Model-embedded copy, and makes deployment look successful on the author's machine while nothing
changes for anyone else who opens the repository. The search path is **not** recursive — placing
files in a subfolder is safe. Before trusting any deployment, check Manage Technology with "Hide
disabled Technologies" unticked and confirm **exactly one** entry for the tech ID, at `Location:
Model` (or whichever location you intended) — more than one entry means something on the search
path is shadowing the copy you meant to test.

---

## Tool Selection for MDG Deployment

| Operation | Use |
|-----------|-----|
| In the model, from an «mdg technology» package (preferred; server 3.6.0 or later) | `ea_mdg(operation="install_mdg", params={"scope": "model", "package_id": <id>})` |
| In the model, from an XML file, whole technology | EA UI: Specialize ▸ Publish Technology ▸ Import MDG Technology ▸ **Import to Model** (no COM route exists) |
| In the model, legacy route (no toolbox pages) | `ea_mdg(operation="install_mdg", params={"scope": "embedded", "xml_path_or_content": "<mdg-dir>\\WBA_MDG.xml"})` — read `not_stored` in the response |
| Application-level install | `ea_mdg(operation="install_mdg", params={"scope": "user", "xml_path_or_content": "<mdg-dir>\\WBA_MDG.xml"})` |
| Verify MDG loaded **and enabled** | COM `repo.IsTechnologyLoaded(tech_id)` and `repo.IsTechnologyEnabled(tech_id)` with your technology id — a technology disabled in Manage Technology still reports loaded |
| Verify what the model stores | `ea_mdg(operation="get_embedded_mdgs", params={})` (server 3.6.0 or later: both Locations), then EA UI → Specialize → Technologies → Manage Technology |
| Dismiss overwrite dialog | Computer use → screenshot → click Yes → screenshot again |
| Fix wrong `Object_Type` in database | COM `repo.Execute()` DML (NOT `elem.Type` setter) |

---

## Deploy: In the Model at Location: Model (preferred)

**From an «mdg technology» source package** (server 3.6.0 or later):

```
ea_mdg(operation="install_mdg", params={"scope": "model", "package_id": <id>})
```

It runs `Repository.ImportPackageAsMDGTechnology` with EA's dialogs suppressed and reads the stored
row back: id, declared version, sections, and stereotype, diagram type and toolbox page counts.
`status: "installed_shadowed"` means the model also holds the id at Location: Project; pass
`replace_project_copy: true` to remove that copy. **Restart EA before checking the toolbox**: until
then it may not switch to the new pages ([references/in-model-locations.md](references/in-model-locations.md)).

**From an XML file:** EA has no COM call that imports a file to Location: Model, so do it in EA:
Specialize ▸ Publish Technology ▸ Import MDG Technology, choose **Import to Model**.

## Deploy: In the Model at Location: Project (legacy route)

Uses `Repository.ImportTechnology(xml_string)` via COM; `install_mdg(scope="embedded")` does the same.
It keeps the UML profiles and the diagram profile and **drops the toolbox pages**, so use it only
for a technology that has none, or when nothing else is available.

```python
import os
import win32com.client

# MDG_FILE: path to your own MDG XML file
MDG_FILE = r"<mdg-dir>\WBA_MDG.xml"
APPDATA_MDG = os.path.join(
    os.environ["APPDATA"],
    "Sparx Systems", "EA", "MDGTechnologies", "WBA_MDG.xml"
)

# Remove any application-level copy first to prevent duplicates
if os.path.exists(APPDATA_MDG):
    os.remove(APPDATA_MDG)
    print(f"Removed APPDATA copy: {APPDATA_MDG}")

# MDG XML must be UTF-8 encoded — read with the same encoding
with open(MDG_FILE, encoding="utf-8") as f:
    xml = f.read()

# Attaches to the running EA; see the ea-com skill for a retrying connect().
repo = win32com.client.GetActiveObject("EA.App").Repository
result = repo.ImportTechnology(xml)
print(f"ImportTechnology() returned: {result}")
# True = success, False = XML error (check for ID > 12 chars, malformed XML, etc.)

print("Done. Restart EA to verify.")
```

**What happens after ImportTechnology:**
- The technology registers in **`t_trxtypes`** in the `.qea` file: an `MDGTechnology` row (diagram profile in `Style`) and one `UMLTechProfile` row per UML profile (in `Notes`). `SELECT Description, TRX FROM t_trxtypes` is the query. Manage Technology shows it at Location: **Project**
- Toolbox pages (`<UIToolboxes>`) are not stored ([references/in-model-locations.md](references/in-model-locations.md)). Nothing goes to `t_propertytypes` or `t_stereotypes` either
- EA must be restarted for the new/updated technology to take full effect
- `ImportTechnology` returns `False` if EA shows an error dialog — common causes:
  - `id=` attribute longer than 12 characters → shorten it
  - Malformed XML → validate with `xmllint` or Python's `xml.etree.ElementTree`
  - Namespace mismatch (stereotype references wrong tech ID)

### ⚠ Post-ImportTechnology — Always Screenshot

`repo.ImportTechnology()` can show a modal **"Profile already exists. Overwrite?"** dialog that
blocks the COM thread. This is true even when `SuppressEADialogs = True` is set, in some EA
builds.

Standard pattern after any `ImportTechnology` call (or any model-mutating COM call):

1. Execute the COM call
2. **Immediately take a screenshot** (do not wait — you need to see if a dialog appeared)
3. Wait 3–5 seconds (EA is slow to render dialogs)
4. Take a **second screenshot**
5. If a dialog is visible: read it, dismiss it appropriately, then confirm the result
6. Only then proceed to the next step

**Operations that ALWAYS require a post-call screenshot:**
- `repo.ImportTechnology()`
- `repo.OpenFile()` / `repo.CloseFile()`
- `repo.Execute()` with INSERT/UPDATE/DELETE
- Any MDG re-import after a profile change

Never assume a COM call succeeded without taking a post-call screenshot.

---

## Deploy: Application-Level (APPDATA Install)

Only use this for machine-specific installs (e.g., a developer's local tooling MDG):

```python
import shutil, os

# MDG_FILE: path to your own MDG XML file
MDG_FILE = r"<mdg-dir>\WBA_MDG.xml"
APPDATA_MDG = os.path.join(
    os.environ["APPDATA"],
    "Sparx Systems", "EA", "MDGTechnologies", "WBA_MDG.xml"
)
os.makedirs(os.path.dirname(APPDATA_MDG), exist_ok=True)
shutil.copy2(MDG_FILE, APPDATA_MDG)
print(f"Installed to: {APPDATA_MDG}")
```

Typical APPDATA path: `%APPDATA%\Sparx Systems\EA\MDGTechnologies`

Restart EA after install.

---

## Bringing EA to Foreground (Critical)

**Never call `open_application("Enterprise Architect")` to bring EA to focus.** This always launches a new EA instance, opening a second EA window with no model. Instead:
- Use `left_click` on the EA taskbar button to bring the existing instance to the foreground
- Or use `win32gui.SetForegroundWindow(hwnd)` in a Python script

---

## Deploy: Manual (EA 17.0 — APPDATA Drop)

1. Save MDG Technology XML to `%APPDATA%\Sparx Systems\EA\MDGTechnologies\<name>.xml`
2. In EA: **Specialize > Technologies > Manage MDG Technologies**
3. Close the dialog — EA reloads from the folder on each open
4. Restart EA to pick up changes

---

## Deploy: MTS Wizard (EA 17.0 production assembly)

1. Create an MTS file referencing the profile XMLs
2. **Publish > Technology > Publish > Generate MDG Technology File**  
   (also accessible as **Specialize > Publish Technology > Generate Technology File** depending on your ribbon configuration)
3. Wizard produces assembled MDG Technology XML

---

## Deploy: from a profile package (EA 17.1+ ONLY)

EA 17.1 added two commands on **Specialize > Publish Technology** that work directly from a
`«mdg technology»` package tree, with no `.mts` and no intermediate profile exports. **They are
not the same command and the names do not say which is which:**

| Command | What it does | Leaves behind |
|---|---|---|
| **Save Package as MDG Technology** | Assembles the technology and writes it to a file | an `.xml` on disk. Nothing is installed |
| **Import Package as MDG Technology** | Assembles the technology and imports it into the open model | a `t_document` TECHNOLOGY row: Location: **Model**, whole technology, available to every user of the model |

**Save gives you a file to keep or ship; Import deploys into the open model.** Both are right
for a model-driven technology, and `install_mdg(scope="model")` is the scriptable Import.

### Procedure — Save Package as MDG Technology

1. Select the `«mdg technology»` package in the Browser.
2. **Specialize > Publish Technology > Save Package as MDG Technology**.
3. A Save As dialog appears (`XML Export File (*.xml)`). Choose the path.
4. EA reports `MDG Technology successfully saved to file`.
5. **Read System Output.** It carries diagnostics the dialog does not, such as
   `WARNING: Duplicate profile name: …`. A build can report success and still have collided.
6. **Version-stamp the file.** Generated technologies come out with an empty `version` attribute,
   and setting the package `Version` beforehand does not carry through. Two unversioned builds are
   indistinguishable in Manage Technologies.
7. Deploy the resulting `.xml` by one of the routes above. This command does not install
   anything.

Name the «mdg technology» package for the id you want: the id comes from the package name, and a
name over 12 characters has been seen truncated (`WBA Technology` → `WBA Technolo`) on one route
and kept whole on another.

**Import Package as MDG Technology** writes one `t_document` TECHNOLOGY row and does not touch
`t_trxtypes`, so check the right table; measured behavior is in
[references/in-model-locations.md](references/in-model-locations.md). `install_mdg(scope="model")`
is the scriptable form.

### Version gate

| EA version | Build the MDG with |
|---|---|
| **17.1+** | `Save Package as MDG Technology` — above |
| **17.0 and earlier** | The MTS Wizard. These commands do not exist; the menu entries are absent, not greyed out |

Verified absent on **EA 17.0 Build 1704**. Check the build before routing someone down either
path — `ea_repository(operation="get_repository_info", params={})` reports `ea_version`.

---

## Restart EA via COM

After any deploy, restart EA to clear the technology cache:

```python
import subprocess
import time

# repo and connect() as in the ea-com skill (references/connecting-and-queries.md)
path = repo.ConnectionString   # save the path before shutdown
repo.SaveAllDiagrams()
time.sleep(0.5)
repo.ShutdownEA()
time.sleep(8)                  # wait for the process to fully exit

subprocess.Popen([r"C:\Program Files\Sparx Systems\EA\EA.exe", path])
time.sleep(12)                 # wait for EA to open and load the project

repo = connect(retries=10, delay=3.0)
```

Every COM reference held from before the restart is stale; reconnect and re-query.

---

## Verification Checklist

After deploying and restarting EA, verify each of these:

> **`get_embedded_mdgs` and server versions.** Before 3.6.0 it read only a document type none of
> EA 17.1's import routes writes, so it returned empty for every in-model technology. Servers 3.6.0 and later list each
> copy the model stores, at Location `Model` and `Project`, with the version each declares.

**Verification order (most reliable first):**
1. **COM:** `repo.IsTechnologyLoaded(tech_id)` and `repo.IsTechnologyEnabled(tech_id)` must both return `True` (`"WBA"` in the Westbrook example)
2. **EA UI:** Specialize → Technologies → Manage Technology → exactly one entry for the id, at the
   Location you installed to (**Model** for `scope="model"` or Import to Model, **Project** for `scope="embedded"`)
3. **MCP:** `ea_mdg(operation="get_mdg_from_runtime", params={"tech_id": "<id>"})` — `source: "live"`;
   on a server 3.6.0 or later also `provenance.location` as expected and no `provenance.also_stored`

### 1. COM check (scripted)
```python
import win32com.client

repo = win32com.client.GetActiveObject("EA.App").Repository
tech = "WBA"                                         # your technology id
print("Loaded :", repo.IsTechnologyLoaded(tech))     # Should be True
print("Enabled:", repo.IsTechnologyEnabled(tech))    # Should be True
print("Version:", repo.GetTechnologyVersion(tech))   # the version your file declares
```

### 2. Manage Technologies dialog
- Open: **Specialize → Technologies → Manage Technologies** (or **Settings → MDG Technologies**)
- Look for your technology entry
- ✅ `Location` shows where you installed it: **Model** or **Project** (not APPDATA)
- ✅ Only **one entry** for the id — no asterisk (`*`) duplicate, and not one at each Location
- ✅ Version matches your `<Documentation version=">` value

### 3. Diagram types
- Right-click a package in the browser → **Add Diagram**
- Expand the diagram type dropdown
- ✅ Your custom diagram types appear (e.g., "APMPortfolioView")
- Create one and confirm the diagram `Type` property shows your custom type name

### 4. Toolbox
- With a custom diagram open, look at the Toolbox panel
- Check after an EA restart; before one, auto-switching may not happen (≡ ▸ your technology lists the pages)
- ✅ Your toolbox page(s) appear (e.g., "WBA ArchiMate", "WBA BPMN", "WBA UML" for WBA 1.1.1)
- ✅ All expected stereotypes are listed
- A single automatic page named after the profile, listing every stereotype, means the copy EA is
  using is at Location: Project, which keeps no toolbox pages. Install at Location: Model.

### 5. Stereotype application + tagged values
- Drag an element from your toolbox page onto a diagram
- Select it and check the Properties panel (Element tab)
- ✅ `Stereotype` shows `TechName: StereotypeName`
- ✅ Tagged values appear in the Properties panel under the stereotype group name
- Double-click the element to open full properties dialog
- ✅ A tab named after your technology appears
- ✅ All tagged values are listed on that tab

### 6. Quick Linker
- To enable Quick Linker: **Preferences → Objects → Links → Quick Linker: Enable ✓**
- With a diagram open, hover over an element for 1-2 seconds to see the QL arrows
- Note: The QL hover overlay cannot be captured by automated screenshot tools — it disappears on focus change

---

## EA Computer Use — Latency Guidelines

Wait before screenshotting — the right interval depends on the operation (2–15 seconds), not a
flat delay — and never retry without confirming the previous action failed. Full wait-time table
and the standard action/wait/screenshot pattern:
[`../_shared/references/latency.md`](../_shared/references/latency.md). See also "Post-
ImportTechnology — Always Screenshot" above for this skill's specific screenshot-before-waiting
sequence around the overwrite-confirmation dialog.

---

## Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| `ImportTechnology()` returns `False` | ID > 12 chars, XML error, or dialog shown | Check EA for error dialog; validate XML; check all `id=` attrs ≤ 12 chars |
| Duplicate entry with `*` in Manage Technologies | Both APPDATA and model copies exist | Delete APPDATA copy, restart EA |
| Technology shows but toolbox is empty | `ToolboxPage name` doesn't match `toolbox` property value in DiagramProfile | Make them identical |
| Diagram type missing from New Diagram dialog | DiagramProfile not loaded or wrong `Apply type` | Verify DiagramProfile section uses `Apply type="Diagram_Logical"` (not `"Logical"`) |
| Tagged values don't appear | Stereotype name mismatch between Profile and Toolbox | Verify `WBA::WBABusinessApplication` format — prefix must match UMLProfile Documentation `id` |
| Only an automatic toolbox page, no designed pages | The technology was installed at Location: Project (`ImportTechnology`, `install_mdg(scope="embedded")`), which stores no toolbox pages | Install at Location: Model: `install_mdg(scope="model", package_id=...)`, or Import MDG Technology ▸ Import to Model |
| Two entries for one id, Location Project and Model | Installed by both routes | Keep one. EA answers from the Project copy. `install_mdg(scope="model", replace_project_copy=True)` removes the Project copy; if it answers `installed_shadowed`, reopen the project and call again |
| `DeleteTechnology()` returns True but a Location: Model entry remains | `DeleteTechnology` removes the Location: Project rows (`t_trxtypes`) only; measured on EA 17.1 build 1716, the `t_document` row stays | Remove a Location: Model copy in Manage Technology (Remove) |
| MDG file rejected on load | Encoding declaration mismatch | Declare `encoding="utf-8"` in the XML prolog and save the file as UTF-8 |

---

## File Encoding (Critical)

MDG Technology XML files must be encoded as UTF-8 and declare `encoding="utf-8"` in the XML
prolog — the declaration and the actual byte encoding must agree, or EA rejects the file
outright. Full guidance (legacy `windows-1252` handling, read/write code patterns):
[`../_shared/references/file-encoding.md`](../_shared/references/file-encoding.md).

---

## Scripts

These are not shipped files — build them yourself from the code already in this skill:

- **Application-level install script** — wrap the "Deploy: Application-Level" snippet above in a standalone `.py` file to do an APPDATA install (copy `MDG_FILE` to `APPDATA_MDG`) in one run.
- **COM API quick-check script** — using plain `win32com` as in the `ea-com` skill, write a small script with a CLI switch:
  ```
  python your_script.py          # check: connect, then print IsTechnologyLoaded/IsTechnologyEnabled/GetTechnologyVersion
  python your_script.py restart  # save + restart EA + reconnect (see "Restart EA via COM" above), then print tech status
  ```

## Verify in EA's UI

EA reports success it has not earned, and reports failure as a modal dialog that blocks the
COM connection rather than as an error you can catch. Neither shows up in a tool response.

- **If a call seems to hang, screenshot EA and read the dialog before concluding anything.**
  It names the cause. Dismiss from the front — dialogs stack, and a later call can be queued
  behind one raised by an earlier one. Windows reporting EA as "Responding" means nothing.
- **After any diagram create or edit, reload the diagram, screenshot it, and look.**
  `ok: true` means rows were written, not that elements landed where you intended, that
  styling applied, or that the result is readable.
- **Without computer use**, say so and ask the user to look — never report a hang you have
  not diagnosed or a diagram you have not seen.

Full procedure: [`../_shared/references/ea-ui-verification.md`](../_shared/references/ea-ui-verification.md)

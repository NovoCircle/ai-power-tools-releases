# Deploy procedures

Back to [SKILL.md](../SKILL.md). The longer procedures that SKILL.md points to: the legacy import
script, restarting EA, releasing a changed technology, removing a technology the model stores, and
the scratch-repository acceptance test. Westbrook Bank is an illustration: replace the technology id,
stereotypes, tags and file names with your own.

## The legacy import script (Location: Project)

Uses `Repository.ImportTechnology(xml_string)`; `install_mdg(scope="embedded")` does the same. It
keeps the UML profiles and the diagram profile and drops the toolbox pages.

```python
import os
import win32com.client

# MDG_FILE: path to your own MDG XML file
MDG_FILE = r"<mdg-dir>\WBA_MDG.xml"
APPDATA_MDG = os.path.join(
    os.environ["APPDATA"],
    "Sparx Systems", "EA", "MDGTechnologies", "WBA_MDG.xml"
)

# An application-level copy of the same id makes a duplicate entry. Ask the person before
# removing it: if it is the only copy, it is lost.
if os.path.exists(APPDATA_MDG):
    print(f"Application-level copy exists: {APPDATA_MDG}")

# MDG XML must be UTF-8 encoded; read with the same encoding. A file that declares
# windows-1252 is read with that encoding (see ../../_shared/references/file-encoding.md).
with open(MDG_FILE, encoding="utf-8") as f:
    xml = f.read()

# Attaches to the running EA; see the ea-com skill for a retrying connect(), and for
# attaching to one instance by its process id when several EA instances are running.
repo = win32com.client.GetActiveObject("EA.App").Repository
result = repo.ImportTechnology(xml)
print(f"ImportTechnology() returned: {result}")
# True = success, False = XML error (check for an id over 12 characters, malformed XML, etc.)
```

Take a screenshot straight after the call (SKILL.md, "Post-ImportTechnology"). To import into one
particular EA instance, attach to it by process id first (`attach_by_pid` in the `ea-com` skill's
instances and sessions reference); see "Location: Project in a specific instance" in
[in-model-locations.md](in-model-locations.md).

## Restart EA via COM

Restart EA after a deploy to clear the technology cache. The person decides when; do not restart
unprompted. Measured on EA 17.1 build 1716:

- `repo.ShutdownEA()` with no argument fails with "Parameter not optional". The method takes one
  required argument (`Flags`); `repo.ShutdownEA(0)` works. No other value has been tried here, so
  use 0 and check Sparx's Repository class reference before trying another.
- The window closes at once, but the process can take seconds to minutes to exit (2 s, 5 s and
  about 3.5 minutes were seen). A fixed sleep is wrong in both directions. Poll the process, with a
  bound, and start EA only when none is running. Starting EA while the old process is alive risks a
  second instance.

```python
import subprocess
import time

def ea_running() -> bool:
    out = subprocess.run(["tasklist", "/FI", "IMAGENAME eq EA.exe", "/NH"],
                         capture_output=True, text=True).stdout
    return "EA.exe" in out

# repo and connect() as in the ea-com skill (references/connecting-and-queries.md)
path = repo.ConnectionString          # save the path before shutdown
repo.SaveAllDiagrams()
time.sleep(0.5)
repo.ShutdownEA(0)                    # Flags: 0 is the value measured to work

deadline = time.time() + 600          # bound the wait: stop and ask, do not kill the process
while ea_running():
    if time.time() > deadline:
        raise RuntimeError("EA is still running 10 minutes after ShutdownEA; ask the person")
    time.sleep(2)

EA_EXE = r"<ea-install-dir>\EA.exe"   # where EA is installed on this machine
subprocess.Popen([EA_EXE, path])
time.sleep(12)                        # wait for EA to open and load the project

repo = connect(retries=10, delay=3.0)
```

Every COM reference held from before the restart is stale; reconnect and re-query. This sequence
has not been run end to end on a restart that followed a technology deploy.

## Releasing a changed technology

Run this before a new version of a technology goes to a repository that other people use. A release
that removes or renames a tag, a tag value or a tag type leaves anything that reads it quietly
wrong: a chart that groups by a removed tag shows one blank group and raises no error.

1. List every tag, tag value and tag type the release changes or removes. Compare the new file with
   the deployed one; do not work from the release notes.
2. Search for each one in everything that reads the model:
   - **Dashboard queries.** Search every dashboard query for each changed or removed tag, value and
     type, not only for stereotype names. Decode each query first; the stored form can hide the
     name. A search that covers stereotype names only misses a chart that groups by a tag. See
     the `prol-dashboards` skill for how queries are stored.
   - Matrices, views and saved searches, reports and templates, validation rulesets, reporting
     extracts and any script that names the tag.
3. For each hit, decide before the release: update it, keep the old tag in the new version, or
   accept the change and tell its owner.
4. Say in the release notes what the check covered and what it could not see (for example a
   dashboard tool the session cannot read). A pass means "nothing found in what was searched".

## Removing a technology the model stores

`Repository.DeleteTechnology(id)` returns True but acts only on technologies installed on the
machine. A technology imported into the model stays. At Location: Model it is one `t_document` row
(`DocType='TECHNOLOGY'`, `DocName=<id>`).

1. **Check nothing uses it.** Elements and connectors bound to it carry `FQName=<id>::` in their
   `t_xref` `Stereotypes` rows; diagrams of its types carry `MDGDgm=<id>::` in the diagram style.
   Count both. If either is above zero, stop and tell the person what would lose its binding.
2. **Back it up.** Export the technology (Manage Technology) or take an EA baseline of the affected
   packages, and copy the `t_document` row's content aside.3. **Remove it.** Preferred: Specialize ▸ Technologies ▸ Manage Technology ▸ select it ▸ Remove.
   Alternative: delete the one `t_document` row with a statement through `repo.Execute()`; ask
   before writing SQL on a live repository.
4. **Reopen the model** and check Manage Technology: no entry for the id, and
   `IsTechnologyLoaded(id)` False.

## Acceptance test in a scratch repository

Before a build is released, install it in a scratch repository, place one of every concept with
every property and every allowed relationship, render each diagram, and report anything that did
not behave. The person then has a populated repository to try. Run it on the customer's own
technology; the Westbrook values below are an illustration. Nothing here touches a real model.

**Not yet verified live.** The calls exist; this exact sequence has not been run end to end.

1. **Scratch repository.** `ea_repository(operation="create_model", params={"path": "<scratch-dir>\\Acceptance"})`.
   Never run this in a model anyone uses.
2. **Install the build** at Location: Model (the route the build will ship by: from the
   `«mdg technology»` package with `install_mdg(scope="model")`, or Import MDG Technology ▸ Import to
   Model for a file), then restart EA, then confirm `IsTechnologyLoaded` and `IsTechnologyEnabled`
   with the technology id and exactly one entry in Manage Technology.
3. **Read the metamodel** with `ea_mdg(operation="get_mdg_from_runtime", params={"tech_id": "<id>"})`:
   its diagram types, stereotypes (with base metaclass and tagged values), connector stereotypes and
   toolbox pages. This is the checklist; do not take it from the design document.
4. **One diagram per diagram type**: `ea_diagram(operation="create_diagram_in_language", ...)`
   into a package of its own.
5. **One element per stereotype** with `create_element_in_language`, filling every tag with a value
   generated from the metamodel, the same way every run:

   | Tag | Value |
   |---|---|
   | Enumeration (a list) | the first value in the declared list |
   | Name contains owner, team, steward or contact | `Team A` |
   | Date | `2026-01-01` |
   | Integer or number | `1` |
   | Boolean | `True` |
   | Any other text | `Sample <tag name>` |

   Place each element on the diagram of the type whose toolbox page offers that stereotype.
6. **Every allowed relationship**: for each connector stereotype and each allowed source and target
   pair the metamodel names, create one connector between the placed elements.
7. **Render** each diagram with `ea_diagram(operation="verify_diagram", params={"diagram_id": <id>, "include_svg": true})`
   and take a screenshot of it in EA.
8. **Report what did not behave**, one line each, under four headings. An empty report on a
   correct build is the expected result.

   | Heading | It did not behave when |
   |---|---|
   | Property missing | A declared tag is absent from the element after the fill, or the fill reported it as rejected |
   | List not a dropdown | An enumeration tag shows as a text box in the Properties panel (look at the screenshot) |
   | Relationship refused | A connector the metamodel allows was rejected, or came back without its stereotype |
   | Shape color | An element's drawn fill or stroke in the rendered SVG differs from the color its stereotype declares (a declared integer color is `0x00BBGGRR`; convert before comparing) |

9. **Leave EA open** on the first diagram and tell the person where the scratch model is, so they
   can run their own ten-minute test. Do not delete it.

## Import MDG Technology dialog

- After a pasted path, the Technology and Version fields can stay blank. OK still imports. The
  dialog can take several seconds to close, so the click looks ignored: wait and screenshot before
  clicking again.
- A file name with a stray character (a tab, for example) gives "unable to open primary document
  entity". The message then repeats for other files until the dialog is canceled and reopened.
  After any such error, cancel and reopen the dialog before the next file.

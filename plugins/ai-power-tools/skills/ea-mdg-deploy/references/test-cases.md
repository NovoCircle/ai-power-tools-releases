# Acceptance cases: `ea-mdg-deploy`

This skill promises to get a Sparx EA MDG Technology into a model or onto a machine by the right
route, and to prove afterwards that it is the copy EA actually uses. This file is built to catch the
failures that look like success: a toolbox quietly lost to the legacy route, the same id stored at two
Locations, a technology that is loaded but disabled, a deploy "verified" by a response that only says
rows were written, and a call that hangs on a dialog nobody looked at.

**Fixture.** A fresh copy of the Westbrook Bank model opened in EA, with the AI Power Tools server
and the Westbrook technology file `<mdg-dir>\WBA_MDG.xml` available. Unless a case says otherwise, its
Setup starts from a copy that holds no technology of its own: no `t_document` rows with
`DocType='TECHNOLOGY'` and no rows in `t_trxtypes` (the runner removes the fixture's earlier import
rows before the agent starts). Westbrook Bank is our illustration. A customer runs these cases
against their own model, substituting their technology id, stereotypes, package names and MDG file.

**Marks.** `WRITE` (the run changes the copy), `EFFECT` (a file is written outside the model; the case
says which), `INVARIANT` (must pass on every run), `BLOCKED` (needs an EA build, a session or a disposable
Windows profile the run may not have; a correct run reports the block). No case here is `REFUSE`.

## Cases

### TC-01: Put the technology into the model

Covers: Deploy: In the Model at Location: Model (preferred); Deployment Modes

**Marks:** WRITE, INVARIANT

**Ask:** "We built our Westbrook technology as the WBA package in this model. Put it into the model itself so every architect who opens it gets the toolbox pages too."

**Setup:** Server 3.6.0 or later. The copy holds no technology rows (see the Fixture paragraph).

**Passes when:** The agent installs from the technology package at Location: Model, not by saving a file, not by the legacy import and not by an application-folder copy. It reports the id and declared version it read back from the stored row, and the model ends with one stored copy of `WBA` and no legacy rows.

**Check:**

```check
sql: SELECT COUNT(*) FROM t_document WHERE DocType = 'TECHNOLOGY' AND DocName = 'WBA'
expect: = 1
```

```check
sql: SELECT COUNT(*) FROM t_trxtypes
expect: = 0
```

```check
# the one-Location invariant (see Invariants)
sql: SELECT ((SELECT COUNT(*) FROM t_document WHERE DocType = 'TECHNOLOGY' AND DocName = 'WBA') > 0) + ((SELECT COUNT(*) FROM t_trxtypes) > 0)
expect: <= 1
```

```check
tools: called: ea_mdg.install_mdg
reply: says: the technology id and the declared version that were read back from the stored copy
```

**Fails when:** The agent runs Save Package as MDG Technology and reports success: a file exists, nothing is installed, and the next architect sees nothing. Or it imports through the legacy route, which returns True and leaves the three designed toolbox pages out. Or it reports success from `ok: true` without reading the stored row, and a wrong package id deploys the wrong thing.

### TC-02: A file with toolbox pages is not sent down the legacy route

Covers: Deployment Modes; Tool Selection for MDG Deployment

**Marks:** WRITE, INVARIANT

**Ask:** "Here's the finished WBA_MDG.xml. Get it into this model for everyone. It has three designed toolbox pages and they have to survive."

**Setup:** The copy holds no technology rows. `<mdg-dir>\WBA_MDG.xml` is the full Westbrook file with its three toolbox pages.

**Passes when:** The agent says no scripted call imports a technology file at Location: Model, and either drives Specialize ▸ Publish Technology ▸ Import MDG Technology ▸ Import to Model itself or hands the user those exact steps. It does not use the legacy import or `install_mdg` with `scope="embedded"`.

**Check:**

```check
sql: SELECT COUNT(*) FROM t_trxtypes
expect: = 0
```

```check
reply: says: no scripted call imports a technology file at Location: Model, so the file goes in through Import MDG Technology with Import to Model
reply: says: the legacy route would drop the toolbox pages
```

**Fails when:** The agent calls the legacy import because it is scriptable, gets `True`, and reports a finished deployment. Nothing errors. The toolbox pages are gone, `t_trxtypes` now holds rows, and the user finds one automatic page weeks later.

### TC-03: The legacy route says what it left out

Covers: Deploy: In the Model at Location: Project (legacy route)

**Marks:** WRITE

**Ask:** "I know the old-style import loses some things, but do it anyway: load WBA_MDG.xml into the project that way. Tell me exactly what I lose."

**Setup:** The copy holds no technology rows. `<mdg-dir>\WBA_MDG.xml` is the full Westbrook file.

**Passes when:** The agent uses the legacy route as asked, reads the list of what was not stored, and tells the person the three toolbox pages are not kept and that EA will show one automatic page built from the stereotypes.

**Check:**

```check
sql: SELECT COUNT(*) FROM t_trxtypes
expect: >= 1
```

```check
sql: SELECT COUNT(*) FROM t_document WHERE DocType = 'TECHNOLOGY' AND DocName = 'WBA'
expect: = 0
```

```check
reply: says: the toolbox pages are not stored by this route
reply: says: EA shows one automatic page built from the stereotypes
```

**Fails when:** The agent reports "imported, restart EA" and nothing else. The person assumes the toolbox they designed will appear.

### TC-04: Never leave one id at two Locations

Covers: Deployment Modes; Tool Selection for MDG Deployment; Troubleshooting

**Marks:** WRITE, INVARIANT

**Ask:** "WBA went in through the old import and the toolbox only shows one page. Move it to the proper model-level install."

**Setup:** `WBA_MDG.xml` is imported by the legacy route, so `t_trxtypes` holds rows and there is no `WBA` row in `t_document`.

**Passes when:** The agent installs the technology at Location: Model from its package and removes the Project copy (`replace_project_copy`, or reopening the project and calling again when the result is `installed_shadowed`). It says EA answers from the Project copy while both exist. The model ends with one Location.

**Check:**

```check
sql: SELECT COUNT(*) FROM t_document WHERE DocType = 'TECHNOLOGY' AND DocName = 'WBA'
expect: = 1
```

```check
sql: SELECT COUNT(*) FROM t_trxtypes
expect: = 0
```

```check
sql: SELECT ((SELECT COUNT(*) FROM t_document WHERE DocType = 'TECHNOLOGY' AND DocName = 'WBA') > 0) + ((SELECT COUNT(*) FROM t_trxtypes) > 0)
expect: <= 1
```

```check
reply: says: while the same id is stored at both Locations EA answers from the Project copy
```

**Fails when:** The agent adds the Model copy beside the Project copy and reports success. Manage Technology now lists two entries, EA still answers from the Project one, and the toolbox stays automatic. The install reported `ok`, so nothing looks wrong.

### TC-05: Do not judge the toolbox before EA restarts

Covers: Deploy: In the Model at Location: Model (preferred)

**Marks:** WRITE

**Ask:** "I installed WBA into the model a few minutes ago, but when I open a WBA diagram the toolbox hasn't switched to the WBA pages. Did the install fail?"

**Setup:** `WBA` is installed at Location: Model in the running EA, which has not been restarted since.

**Passes when:** The agent does not conclude the install failed. It says the diagram types and pages are available (the Toolbox's technology menu lists them) but that automatic switching is not dependable until EA restarts, and it leaves the restart to the person or asks before doing it. It does not reinstall.

**Check:**

```check
sql: SELECT COUNT(*) FROM t_document WHERE DocType = 'TECHNOLOGY' AND DocName = 'WBA'
expect: = 1
```

```check
tools: not-called: ea_mdg.install_mdg
reply: says: the toolbox switch is not dependable until EA restarts
reply: says: asks before restarting EA, or tells the person to restart it
reply: not: tells the person to reinstall the technology
```

**Fails when:** The agent sees one automatic page, decides the install is broken, and removes and reinstalls. Or it restarts EA without asking and discards whatever the person had open. Or it declares success after looking at the pre-restart toolbox.

### TC-06: Install on this machine only

Covers: Deploy: Application-Level (APPDATA Install); Tool Selection for MDG Deployment

**Marks:** EFFECT, BLOCKED (needs a disposable Windows profile)

**Ask:** "Put WBA_MDG.xml on my machine only, for my own experiments. Don't touch the shared model."

**Setup:** None. The effect is a copy of the file under `%APPDATA%\Sparx Systems\EA\MDGTechnologies\`, which is machine-wide state, so the case runs only where the runner provides a disposable Windows profile; the runner restores the state afterwards. The person asked for it, so the agent need not ask first.

**Passes when:** The agent installs at application level, writes the copy to the application folder (not to Downloads, which the search path auto-registers), tells the person to restart EA, and leaves the model alone.

**Check:**

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

```check
sql: SELECT (SELECT COUNT(*) FROM t_document WHERE DocType = 'TECHNOLOGY'), (SELECT COUNT(*) FROM t_trxtypes)
expect: unchanged
```

```check
tools: called: ea_mdg.install_mdg
reply: says: restart EA after the install
```

**Fails when:** The agent imports into the model "to be safe", so the shared model now carries a technology the person asked to keep private. Or it drops the file in Downloads, where EA registers it silently.

### TC-07: Dropping a file in the application folder is not a team deployment

Covers: Deploy: Application-Level (APPDATA Install); Deployment Modes

**Ask:** "The whole team needs the Westbrook technology. Just drop the MDG file into the MDGTechnologies folder under my AppData and we're done, right?"

**Passes when:** The agent says an application-level copy reaches only this machine, that a technology stored in the model reaches everyone who opens the model, and recommends the model install. It does not stop at the application-folder copy.

**Check:**

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

```check
reply: says: an application-folder copy reaches only this machine
reply: says: a technology stored in the model reaches everyone who opens the model
```

**Fails when:** The agent agrees and copies the file. It works on the author's machine, so it looks done, and no colleague sees the technology.

### TC-08: A duplicate entry with an asterisk

Covers: Deployment Modes; Troubleshooting

**Marks:** BLOCKED (needs a disposable Windows profile)

**Ask:** "Manage Technologies lists our WBA technology twice and one of them has an asterisk. Why, and how do I get rid of the extra one?"

**Setup:** `WBA` is stored in the model at Location: Model, and an identical-id copy of the file also sits in the application folder. That folder is machine-wide state, so the case runs only where the runner provides a disposable Windows profile; the runner places the copy and restores the state afterwards.

**Passes when:** The agent explains the asterisk entry is the application-level copy of an id the model also holds, says the UI cannot remove it, and gives the fix: delete the copy in the application folder and restart EA.

**Check:**

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

```check
reply: says: the asterisk entry is the application-level copy of an id the model also stores
reply: says: it cannot be removed through the UI; delete the file in the application folder and restart EA
```

**Fails when:** The agent tells the person to remove the entry in Manage Technology or to reinstall into the model, which cannot clear it. Or it deletes the model copy, which is the one that should stay.

### TC-09: Works on my machine, nothing for my colleague

Covers: Model vs. runtime technologies — and the search-path auto-registration trap

**Marks:** INVARIANT, BLOCKED (needs a disposable Windows profile)

**Ask:** "I deployed our Westbrook technology and it works fine on my machine, but a colleague who opens the same model sees nothing. What did I get wrong?"

**Setup:** `WBA` is stored in the model at Location: Model, and a copy of `WBA_MDG.xml` sits in the person's Downloads folder, which is on EA's search path. The Downloads folder is machine-wide state, so the case runs only where the runner provides a disposable Windows profile; the runner places the copy and restores the state afterwards.

**Passes when:** The agent raises auto-registration from the search path first: EA registers any MDG file it finds on the path, including Downloads, so the stray copy shadows the model copy on this machine only. It has the person open Manage Technology with "Hide disabled Technologies" unticked, expects exactly one entry for the id at the intended Location, and notes that a subfolder of the path is safe because the search is not recursive.

**Check:**

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

```check
reply: says: EA registers any MDG file on its search path, including the Downloads folder
reply: says: a stray copy shadows the model copy on this machine only
reply: says: check Manage Technology with Hide disabled Technologies unticked for exactly one entry for the id
reply: says: files in a subfolder of the search path are not registered
```

**Fails when:** The agent blames the colleague's EA version or permissions, or tells the person to reinstall. The deployment looked successful on the author's machine, which is exactly the failure, so reinstalling changes nothing for the colleague.

### TC-10: Loaded is not enabled

Covers: Tool Selection for MDG Deployment; Verification Checklist; 1. COM check (scripted)

**Marks:** INVARIANT, BLOCKED (needs a disposable Windows profile)

**Ask:** "Is our WBA technology switched on in this model? Its stereotypes aren't offering anything."

**Setup:** `WBA` is installed at Location: Model and disabled in Manage Technology. Enabling and disabling a technology is per-user EA state, so the case runs only where the runner provides a disposable Windows profile; the runner sets the state and restores it afterwards.

**Passes when:** The agent checks both the loaded and the enabled state, finds the technology loaded but not enabled, and says the loaded answer alone would have misled. It tells the person to enable it in Manage Technology.

**Check:**

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

```check
call: ea_mdg.get_mdg_from_runtime {"tech_id": "WBA"}
expect: source = registered_not_enabled
```

```check
reply: says: the technology is loaded but not enabled
reply: not: says the technology is working because it reports loaded
```

**Fails when:** The agent calls the loaded check, gets `True`, and answers "yes, it is on". A disabled technology still reports loaded, so the answer is confident and wrong.

### TC-11: What does this model carry inside itself

Covers: Tool Selection for MDG Deployment; Verification Checklist

**Ask:** "Which technologies does this model store inside itself, and which version of each?"

**Setup:** The model stores `WBA` at Location: Model and a second technology build at Location: Project (both routes used once on the copy).

**Passes when:** The agent reads the stored copies with the embedded-technologies listing, reports both Locations with the version each declares, and does not report an empty result for the in-model copies.

**Check:**

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

```check
tools: called: ea_mdg.get_embedded_mdgs
reply: says: lists the stored technologies at Location Model and at Location Project, each with the version it declares
```

**Fails when:** The agent reports "no embedded technologies", which is what a server before 3.6.0 returns for every in-model technology, and the person concludes nothing is installed.

### TC-12: Fix elements created as the wrong EA type

Covers: Tool Selection for MDG Deployment

**Marks:** WRITE

**Ask:** "SFTP Batch Gateway came in as a Class instead of a Component, and the toolbox won't treat it as one of ours. Fix it."

**Setup:** On the copy, the runner sets `Object_Type` of `SFTP Batch Gateway` (stereotype `WBABusinessApplication`, normally a Component) to `Class`.

**Passes when:** The agent corrects the stored type with a database statement through the repository, not by setting the element's type property, then looks at EA for a dialog before moving on. The element ends as a Component and no other element changed type.

**Check:**

```check
sql: SELECT Object_Type FROM t_object WHERE Name = 'SFTP Batch Gateway' AND Stereotype = 'WBABusinessApplication'
expect: rows: [["Component"]]
```

```check
sql: SELECT COUNT(*) FROM t_object WHERE Stereotype = 'WBABusinessApplication' AND Object_Type <> 'Component'
expect: = 0
```

**Fails when:** The agent sets the element's type through the COM property. The call returns, nothing errors, and the stored type does not change, so the toolbox still will not offer the element.

### TC-13: The overwrite dialog after a re-import

Covers: ⚠ Post-ImportTechnology — Always Screenshot; Deploy: In the Model at Location: Project (legacy route)

**Marks:** WRITE, INVARIANT

**Ask:** "WBA is already in the project from the old-style import. I changed a stereotype in the file, so reload it the same way."

**Setup:** `WBA_MDG.xml` was imported earlier by the legacy route (`t_trxtypes` holds rows; no `t_document` row for `WBA`).

**Passes when:** Immediately after the import call the agent takes a screenshot of EA, waits, takes a second one, and reads any "Profile already exists. Overwrite?" dialog before answering it. It dismisses the dialog only because the person asked for the re-import, confirms the result, and only then reports. It tells the person to restart EA.

**Check:**

```check
sql: SELECT COUNT(*) FROM t_trxtypes
expect: >= 1
```

```check
sql: SELECT ((SELECT COUNT(*) FROM t_document WHERE DocType = 'TECHNOLOGY' AND DocName = 'WBA') > 0) + ((SELECT COUNT(*) FROM t_trxtypes) > 0)
expect: <= 1
```

```check
reply: says: it took a screenshot straight after the import call and a second one after waiting
reply: says: it read the dialog (or saw none) before reporting the result
```

**Fails when:** The agent assumes the call succeeded. The overwrite dialog blocks the COM thread, every later call queues behind it, and the agent reports a hang or a success it never saw.

### TC-14: The import keeps returning False

Covers: Deploy: In the Model at Location: Project (legacy route); Troubleshooting

**Ask:** "The old-style import of my MDG file keeps coming back False. Tell me what is wrong with the file; I'll fix it myself."

**Setup:** `<mdg-dir>\WBA_MDG.xml` is a copy of the Westbrook file whose technology `id=` is changed to `WBA Technology` (14 characters). The runner supplies it.

**Passes when:** The agent reads the file, finds the id over 12 characters as the cause, and also names the other causes the skill lists: an error dialog in EA, malformed XML, and a stereotype namespace that does not match the technology id. It tells the person to shorten the id and does not report success.

**Check:**

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

```check
sql: SELECT COUNT(*) FROM t_trxtypes
expect: = 0
```

```check
reply: says: the technology id is longer than 12 characters and must be shortened
reply: says: other causes are an error dialog in EA, malformed XML, and a stereotype namespace that does not match the technology id
```

**Fails when:** The agent retries the import in a loop, or reports "EA rejected the file" without finding the id. A False return carries no message, so the cause has to be read from the file and from EA's screen.

### TC-15: EA rejects the file on load

Covers: File Encoding (Critical); Troubleshooting

**Marks:** EFFECT

**Ask:** "EA rejects our MDG file when it loads, and I can't see why. It was last saved from an older editor."

**Setup:** `<mdg-dir>\WBA_MDG.xml` declares `encoding="utf-8"` in its prolog but is saved as `windows-1252`, so the declaration and the bytes disagree. The runner supplies it. The effect is a rewrite of that file; the person asked for the problem to be found and fixed.

**Passes when:** The agent finds that the declared encoding and the actual bytes disagree, rewrites the file as UTF-8 with `encoding="utf-8"` in the prolog, and reads and writes it with the same encoding throughout.

**Check:**

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

```check
reply: says: the encoding declaration and the file's actual bytes disagree
reply: says: the file is saved as UTF-8 with encoding="utf-8" declared
```

**Fails when:** The agent edits only the prolog, or only the bytes. The two still disagree and EA rejects the file again, or it opens the file and reads accented characters wrongly.

### TC-16: Bring EA to the front without starting a second one

Covers: Bringing EA to Foreground (Critical)

**Marks:** INVARIANT

**Ask:** "EA is hiding behind other windows and I think a dialog is open in it. Bring it up front so we can see."

**Setup:** EA is running with the model open.

**Passes when:** The agent brings the existing instance forward by clicking its taskbar button (or setting the existing window foreground from a script). It never asks the operating system to open Enterprise Architect.

**Check:**

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

```check
tools: not-called: computer-use.open_application
reply: says: it brought the existing EA window forward
```

**Fails when:** The agent opens the application by name. A second EA instance starts with no model, the first stays hidden, and the dialog the person was worried about is still there.

### TC-17: A 17.0 user wants the file available

Covers: Deploy: Manual (EA 17.0 — APPDATA Drop)

**Ask:** "We're on EA 17.0. How do I get the Westbrook technology file into EA on this PC?"

**Passes when:** The agent gives the manual route: save the file in the `MDGTechnologies` folder under `%APPDATA%\Sparx Systems\EA\`, open Manage MDG Technologies, close the dialog, restart EA. It says this is a this-machine install.

**Check:**

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

```check
reply: says: save the file in the MDGTechnologies folder under the Sparx Systems EA folder in AppData
reply: says: restart EA afterwards
reply: says: this installs for this machine only
```

**Fails when:** The agent sends the person to menu commands that only exist in 17.1 and later, or omits the restart.

### TC-18: Building the file on EA 17.0

Covers: Version gate; Deploy: MTS Wizard (EA 17.0 production assembly)

**Marks:** BLOCKED

**Ask:** "Build the assembled technology file from our WBA package in this model."

**Setup:** Needs EA 17.0 Build 1704 or earlier. A run on 17.1 or later reports the block.

**Passes when:** The agent checks the EA build first, finds 17.0, and says the Save and Import Package commands do not exist in that build (the menu entries are absent, not greyed out). It routes the person to the MTS Wizard: create an MTS file that references the profile XMLs, then Publish ▸ Technology ▸ Publish ▸ Generate MDG Technology File.

**Check:**

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

```check
tools: called: ea_repository.get_repository_info
reply: says: the Save and Import Package as MDG Technology commands do not exist in EA 17.0 and are absent from the menu
reply: says: use the MTS Wizard and Generate MDG Technology File
```

**Fails when:** The agent tells the person to click Save Package as MDG Technology, cannot find it, and reports a broken menu or a missing licence.

### TC-19: Give me the technology as a file, install nothing

Covers: Deploy: from a profile package (EA 17.1+ ONLY); Procedure — Save Package as MDG Technology

**Marks:** EFFECT

**Ask:** "Give me the WBA technology as an XML file I can send to another architecture team. Save it as <output-dir>\WBA_MDG.xml. Don't install anything here."

**Setup:** EA 17.1 or later. The effect is one `.xml` file at `<output-dir>\WBA_MDG.xml`; nothing is stored in the model.

**Passes when:** The agent uses Save Package as MDG Technology (not Import), reads System Output for diagnostics such as a duplicate profile name rather than trusting the success dialog, version-stamps the saved file because generated files have an empty `version`, and tells the person the command installed nothing.

**Check:**

```check
sql: SELECT (SELECT COUNT(*) FROM t_document WHERE DocType = 'TECHNOLOGY'), (SELECT COUNT(*) FROM t_trxtypes)
expect: unchanged
```

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

```check
file: <output-dir>\WBA_MDG.xml
expect: exists
```

```check
reply: says: it read System Output for warnings after the success message
reply: says: the saved file had an empty version attribute and was version-stamped
reply: says: Save writes a file and installs nothing
```

**Fails when:** The agent picks Import Package instead because the two names look alike. The technology is now stored in the model, the person has no file to send, and the model changed when they said not to.

### TC-20: Will the package name become the technology id

Covers: Procedure — Save Package as MDG Technology; Deploy: from a profile package (EA 17.1+ ONLY)

**Ask:** "I'm going to rename the package that holds our technology to 'Westbrook Bank Architecture Technology'. Will EA use that as the technology id?"

**Passes when:** The agent says the id comes from the package name, that a name over 12 characters has been seen truncated on one route and kept whole on another, and that 12 characters is also the ceiling for an id the legacy import accepts. It advises naming the package for the id wanted and reading the stored id back after deploying.

**Check:**

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

```check
reply: says: the technology id comes from the package name
reply: says: a name over 12 characters has been seen truncated on one route and kept whole on another
reply: says: read the stored id back after deploying
```

**Fails when:** The agent answers "yes" or "no" with confidence. The package then yields a truncated id such as `Westbrook Ba`, stereotype references no longer match, and nothing errors.

### TC-21: Restart EA and carry on

Covers: Restart EA via COM

**Ask:** "Restart EA for me so the new WBA technology takes effect, then tell me it's loaded and enabled."

**Setup:** `WBA` is installed at Location: Model in the running EA, which holds the run's copy of the model.

**Passes when:** The agent records the open model's path before shutting EA down, saves diagrams, shuts EA down, relaunches on that same path, waits, reconnects, and queries afresh rather than reusing handles from before the restart. It then reports loaded and enabled.

**Check:**

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

```check
call: ea_mdg.get_mdg_from_runtime {"tech_id": "WBA"}
expect: source = live
```

```check
tools: not-called: computer-use.open_application
reply: says: it reopened the same model file and reconnected before checking
```

**Fails when:** The agent restarts EA without the model path and reopens a different or empty model, or keeps using a repository handle from before the restart and reports an error or a stale answer.

### TC-22: Prove the deployment before saying it worked

Covers: Verification Checklist; 1. COM check (scripted); 2. Manage Technologies dialog

**Ask:** "I installed WBA into the model and restarted EA. Is it really working, or does it just look like it?"

**Setup:** `WBA` is installed at Location: Model (version 1.1.1) and EA has been restarted.

**Passes when:** The agent checks in the skill's order: loaded and enabled both true, then Manage Technology showing exactly one entry for the id at Location: Model with no asterisk duplicate and the declared version, then the runtime lookup reporting the live source at Location: Model. It reports each result rather than a general "looks fine".

**Check:**

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

```check
call: ea_mdg.get_mdg_from_runtime {"tech_id": "WBA"}
expect: source = live
```

```check
call: ea_mdg.get_mdg_from_runtime {"tech_id": "WBA"}
expect: provenance.location = Model
```

```check
tools: called: ea_mdg.get_mdg_from_runtime
reply: says: loaded and enabled were both checked
reply: says: Manage Technology shows exactly one entry for the id at Location Model
reply: says: the version matches the one the file declares
```

**Fails when:** The agent runs the loaded check alone, sees `True`, and says it works. A disabled technology and a shadowing duplicate both pass that one check.

### TC-23: Custom diagram types are offered

Covers: 3. Diagram types

**Marks:** WRITE

**Ask:** "In Technology Architecture, add a WBA Application Architecture diagram called WBA Types Check, so I can see the Westbrook diagram types are really available."

**Setup:** `WBA` is installed at Location: Model and EA has been restarted.

**Passes when:** The agent opens Add Diagram on the package, finds the WBA diagram types in the dropdown, creates the diagram with the custom type, and confirms the diagram's type property shows that custom type rather than a plain Logical diagram.

**Check:**

```check
sql: SELECT COUNT(*) FROM t_diagram g JOIN t_package p ON g.Package_ID = p.Package_ID WHERE g.Name = 'WBA Types Check' AND p.Name = 'Technology Architecture' AND g.StyleEx LIKE '%MDGDgm=WBA::WBAApplicationView%'
expect: = 1
```

```check
reply: says: the WBA diagram types appear in the diagram type dropdown
reply: says: the new diagram's type shows the WBA Application Architecture type
```

**Fails when:** The agent creates an ordinary Logical diagram under that name and reports it done. The name matches, the type is wrong, and the toolbox never switches.

### TC-24: The designed toolbox pages appear

Covers: 4. Toolbox

**Ask:** "Open one of our WBA application diagrams and tell me which toolbox pages show up."

**Setup:** `WBA` is installed at Location: Model and EA has been restarted. The diagram `AI Platform Architecture` has the Westbrook application diagram type.

**Passes when:** The agent opens the diagram, looks at the Toolbox after the restart, and reports the three designed pages (the skill calls them WBA ArchiMate, WBA BPMN and WBA UML; the fixture's page elements are named with an "Elements" suffix) and that the expected stereotypes are listed on them.

**Check:**

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

```check
reply: says: the toolbox shows three WBA pages (ArchiMate, BPMN and UML)
reply: says: it looked at the Toolbox in EA and did not infer the pages from the file
```

**Fails when:** The agent lists the pages from the MDG file and never looks at the Toolbox. The file and the running toolbox can disagree, and this is the check that finds out.

### TC-25: Only one automatic toolbox page

Covers: 4. Toolbox; Troubleshooting

**Ask:** "My WBA toolbox shows a single page listing every stereotype. None of the three pages we designed are there. Why?"

**Setup:** `WBA` is installed only at Location: Project (legacy import); no `t_document` row for `WBA`.

**Passes when:** The agent says a single automatic page named after the profile means the copy EA uses is at Location: Project, which keeps no toolbox pages, and recommends installing at Location: Model (from the package, or Import to Model from the file). It checks which Location holds the copy rather than guessing.

**Check:**

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

```check
reply: says: one automatic page means the copy in use is at Location Project, which keeps no toolbox pages
reply: says: install at Location Model
```

**Fails when:** The agent edits the toolbox definition in the MDG file, which is fine, and redeploys it by the same route, so the toolbox stays empty again.

### TC-26: A dragged element is bound and carries its tags

Covers: 5. Stereotype application + tagged values

**Marks:** WRITE

**Ask:** "On the AI Platform Architecture diagram, drag a Business Application from the WBA toolbox, call it Card Disputes, and check it came through with its properties."

**Setup:** `WBA` is installed at Location: Model and EA has been restarted.

**Passes when:** The agent drags the item from the toolbox, names the element, then checks the Properties panel: stereotype shown as the technology's stereotype, and the six base tagged values listed under it, and the full properties dialog showing a tab named for the technology.

**Check:**

```check
sql: SELECT o.Object_Type FROM t_object o WHERE o.Name = 'Card Disputes' AND o.Stereotype = 'WBABusinessApplication'
expect: rows: [["Component"]]
```

```check
# bound to the technology: the t_xref row holds the qualified form
sql: SELECT COUNT(*) FROM t_xref x JOIN t_object o ON x.Client = o.ea_guid WHERE o.Name = 'Card Disputes' AND x.Name = 'Stereotypes' AND x.Description LIKE '%::WBABusinessApplication%'
expect: = 1
```

```check
sql: SELECT COUNT(*) FROM t_objectproperties tp JOIN t_object o ON tp.Object_ID = o.Object_ID WHERE o.Name = 'Card Disputes' AND tp.Property IN ('criticality', 'lifecycle', 'businessOwner', 'technicalOwner', 'dataClassification', 'regulatoryScope')
expect: = 6
```

**Fails when:** The agent creates the element by an API call that sets the stereotype as plain text. The element shows a stereotype name but has no `t_xref` binding and no tagged values, so it looks right and is not bound to the technology.

### TC-27: Quick Linker cannot be seen by a screenshot

Covers: 6. Quick Linker

**Ask:** "Check that Quick Linker works on a WBA element."

**Passes when:** The agent says how to enable it (Preferences ▸ Objects ▸ Links ▸ Quick Linker: Enable) and how to trigger it (hover over an element for a second or two), says the hover overlay disappears when focus changes and cannot be captured by automated screenshots, and asks the person to look rather than claiming it verified.

**Check:**

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

```check
reply: says: Quick Linker is turned on under Preferences, Objects, Links
reply: says: the hover overlay cannot be captured by automated screenshots, so the person needs to look
reply: not: claims Quick Linker was verified by screenshot
```

**Fails when:** The agent takes a screenshot of the diagram, sees no arrows, and reports either "Quick Linker is broken" or "verified".

### TC-28: The technology shows but the toolbox is empty

Covers: Troubleshooting

**Ask:** "The technology shows up in Manage Technologies, but the toolbox for our WBA diagrams is empty. What's wrong with the file?"

**Setup:** `<mdg-dir>\WBA_MDG.xml` is a copy of the Westbrook file in which the `ToolboxPage` name for the application view differs from the `toolbox` property value in the diagram profile. The runner supplies it.

**Passes when:** The agent compares the toolbox page name with the `toolbox` property value on the diagram stereotype, finds they differ, and tells the person to make them identical.

**Check:**

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

```check
reply: says: the ToolboxPage name and the toolbox property in the diagram profile must be identical
reply: says: it found the two names differ in the file
```

**Fails when:** The agent blames the install Location or tells the person to reinstall. The mismatch is in the file, so every reinstall reproduces the empty toolbox.

### TC-29: A custom diagram type is missing

Covers: Troubleshooting

**Ask:** "Our WBA diagram types don't appear in the New Diagram dialog, though the technology is loaded. What's wrong?"

**Setup:** `<mdg-dir>\WBA_MDG.xml` is a copy of the Westbrook file whose diagram profile uses `Apply type="Logical"` where the skill says `Diagram_Logical` is required. The runner supplies it.

**Passes when:** The agent inspects the diagram profile, finds the short apply type, and says the value must be written `Diagram_Logical` (not `Logical`), or the equivalent full name for the other diagram kinds.

**Check:**

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

```check
reply: says: the apply type must be Diagram_Logical, not Logical
```

**Fails when:** The agent suspects the Location or the restart and has the person reinstall. The file is wrong, and the reinstall fails the same way.

### TC-30: Tagged values do not show

Covers: Troubleshooting

**Ask:** "Elements from our WBA toolbox arrive with no tagged values. The profile defines them. What should I check?"

**Setup:** `<mdg-dir>\WBA_MDG.xml` is a copy of the Westbrook file in which the toolbox page lists a stereotype under a prefix different from the one the UML profile declares. The runner supplies it.

**Passes when:** The agent compares the qualified stereotype names on the toolbox page with the profile, finds the prefix that does not match the one the UML profile declares, and says the two must agree.

**Check:**

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

```check
reply: says: the stereotype prefix on the toolbox page must match the prefix the UML profile declares
reply: says: it found the prefix that differs
```

**Fails when:** The agent adds the tagged values to the profile again. The profile is already right, and the toolbox reference is what does not bind.

### TC-31: DeleteTechnology said True but the entry is still there

Covers: Troubleshooting

**Ask:** "I ran DeleteTechnology on WBA and it said True, but WBA is still in Manage Technologies. Is that broken?"

**Setup:** `WBA` is stored at Location: Model.

**Passes when:** The agent explains that the delete removes only the Location: Project rows and leaves a Location: Model copy, and tells the person to remove the Model copy in Manage Technology with Remove. It does not delete the stored row with SQL.

**Check:**

```check
sql: SELECT COUNT(*) FROM t_document WHERE DocType = 'TECHNOLOGY' AND DocName = 'WBA'
expect: unchanged
```

```check
reply: says: DeleteTechnology removes only the Location Project rows, so the Location Model copy stays
reply: says: remove the Model copy in Manage Technology
```

**Fails when:** The agent calls it a bug and deletes the `t_document` row directly. EA's own technology list can disagree with the table afterwards.

### TC-32: A call hangs

Covers: Verify in EA's UI

**Ask:** "My technology lookup has been hanging for a while. What's going on?"

**Setup:** A modal dialog is open in EA (the runner raises one), so COM calls queue behind it.

**Passes when:** The agent takes a screenshot of EA and reads the dialog before drawing any conclusion, names its cause, and dismisses it from the front, not from behind a later one. It does not treat the Windows "Responding" status as evidence that EA is fine.

**Check:**

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

```check
reply: says: it screenshotted EA and read the dialog that was blocking the connection
reply: says: dialogs are dismissed from the front because they stack
reply: not: says EA is fine because Windows reports it as Responding
```

**Fails when:** The agent retries the call, concludes EA crashed, or restarts it. The dialog still names the cause, and the retries pile up behind it.

### TC-33: No computer use in the session

Covers: Verify in EA's UI

**Marks:** BLOCKED

**Ask:** "My technology lookup has been hanging for a while. What's going on?"

**Setup:** The session has no screen-control tool, so the agent cannot see EA. A run that has one reports the block.

**Passes when:** The agent says it cannot see EA's screen, asks the person to look for a dialog and describe it, and does not report a diagnosis of the hang.

**Check:**

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

```check
reply: says: it cannot see EA's screen and asks the person to look for a dialog
reply: not: names a cause for the hang that it did not observe
```

**Fails when:** The agent names a likely cause with confidence ("the overwrite dialog") and the person acts on a diagnosis nobody saw.

### TC-34: Look at a diagram after creating it

Covers: Verify in EA's UI

**Marks:** WRITE

**Ask:** "Build a diagram called Core Platforms View in Technology Architecture with Fiserv DNA Core on it, and tell me it came out right."

**Passes when:** After creating the diagram the agent reloads it, takes a screenshot, looks at it, and reports what it saw (the element is present, readable and in view), not only that the write returned `ok`.

**Check:**

```check
sql: SELECT COUNT(*) FROM t_diagramobjects d JOIN t_diagram g ON d.Diagram_ID = g.Diagram_ID JOIN t_package p ON g.Package_ID = p.Package_ID JOIN t_object o ON d.Object_ID = o.Object_ID WHERE g.Name = 'Core Platforms View' AND p.Name = 'Technology Architecture' AND o.Name = 'Fiserv DNA Core'
expect: = 1
```

```check
reply: says: it reloaded the diagram and looked at a screenshot of it
reply: says: what the screenshot showed about the element's position and readability
```

**Fails when:** The agent reports "done, ok: true". Rows were written, but the element may sit off the visible area or overlap, and nobody looked.

## Invariants

**One Location per id (TC-01, TC-04, TC-13).** After any deploy for `WBA` on a copy that started with no technology rows, the model stores the id in at most one of the two places: a `t_document` row with `DocType='TECHNOLOGY'` or rows in `t_trxtypes`. The check adds the two truth values and requires a sum of 1 or less. It is a property of the end state, so it holds without a known-good answer. It does not cover an application-level copy in the application folder or on the search path, which are files SQL cannot see; TC-08 and TC-09 cover those by reply only. It also assumes `t_trxtypes` is empty before the run, which the Fixture paragraph guarantees; on a customer model that already holds legacy technologies, restrict the second term to the rows written for the id under test.

## Headings not covered

- Deploying and Testing a Sparx EA MDG Technology: the document title; it states only the document's subject and the build it was verified against, neither testable.
- EA Computer Use — Latency Guidelines: delegates to the shared latency table and states an interval to wait, not an outcome a check can read; the screenshot-before-waiting sequence it points to is covered by TC-13.
- Scripts: says the two scripts are not shipped and are built from the snippets above; the snippets themselves are covered by TC-06 and TC-22. A check would only ask whether the agent hunts for a file that does not exist, which no state or reply can show reliably.

## Findings

- Restart is two promises. "Restart EA via COM" says to restart EA after any deploy and gives unattended restart code, while `references/in-model-locations.md` says "Restarting EA is the user's call". TC-05 and TC-21 assume the reference's rule (leave it to the person or ask); the skill should say which holds when the person has not asked.
- The `Restart EA via COM` snippet launches `EA.exe` from a fixed default install directory; on a machine installed elsewhere the relaunch fails after EA has been shut down. Not checkable here.
- The legacy-route snippet deletes the person's application-level copy of the file (`os.remove`) before importing, with no question asked. If that copy is the only one, it is lost. TC-03 and TC-13 do not test it because the file is outside the model.
- "Deploy: Manual (EA 17.0 — APPDATA Drop)" step 3 says EA reloads from the folder on each open, and step 4 says to restart EA to pick up changes. It is unclear whether the restart is required. Menu names also vary ("Manage MDG Technologies", "Manage Technologies", "Manage Technology") with no note that they are one dialog.
- The toolbox page names in the Verification Checklist (WBA ArchiMate, WBA BPMN, WBA UML) are the toolbox profile names. The fixture's toolbox page elements are named with an "Elements" suffix (for example `WBA ArchiMate Elements`). TC-24 accepts either; the skill should use one.
- The qualified stereotype form conflicts with the data. The skill's Troubleshooting row and the standing template say `WBA::WBABusinessApplication`; the fixture's `t_xref` holds 153 `Stereotypes` rows with the `WestbrookBankArchitecture::` prefix and none with `WBA::`. TC-26 matches `%::WBABusinessApplication%` so it passes either way. TC-30 says "the prefix the UML profile declares" for the same reason.
- `install_mdg(scope="model", package_id=<id>)` does not say which id: the package's `Package_ID` or the id of the stereotyped package element row. The fixture holds both (a package and a separate object row for it). TC-01 would fail on the wrong one with a plausible-looking error.
- The skill says the model-level install needs "server 3.6.0 or later", and that `get_embedded_mdgs` is empty before it, but names no operation that reports the server version. TC-01 and TC-11 assume 3.6.0 or later in Setup.
- The `tools` check grammar takes `<tool>.<operation>`; the screen-control tool is named here as `computer-use.<operation>` (TC-16, TC-21) by assumption, and screenshots after an import (TC-13, TC-34) are checked only by the reply, because the runner design has not said how to count screenshots.
- The Manage Technology UI claims ("exactly one entry", "no asterisk duplicate", Location column) and the Toolbox page contents have no SQL or call that reads them; they are checked by reply, and a wrong reply there cannot be caught mechanically.
- Cases that need a supplied MDG file with a deliberate defect (TC-14, TC-15, TC-28, TC-29, TC-30) depend on the runner building that file; the skill itself does not ship one.

# Acceptance cases: `ea-import-export`

This skill promises to pick the right way out of Enterprise Architect for the job (a picture, an
editable Visio file, an XMI package, an RTF report), to check that an export really contains what
it claims, and to say plainly what the server cannot do. Most failures here produce a plausible
success, not an error: a status of "exported" over a file that holds nothing, a "generated" report
that never used the template the person named, a picture that is a stale cached render. This file
is built to catch those.

It also promises two things for diagrams: to hand another tool a complete reading of a diagram, with
every shape still tied to its element (the manifest), and to give every diagram a description that
stays current without losing a person's words. Those fail quietly as well: a Visio file with no way
back to the model, a description that omits half the diagram, a refresh that overwrites an edit. TC-21
to TC-44 are built to catch those.

**Fixture.** A fresh copy of the Westbrook Bank model opened in EA (technology `WBA`, qualified
stereotype form `WBA::`, for example `WBA::WBABusinessApplication`). Westbrook Bank is our
illustration. A customer runs these cases against their own model, substituting their technology,
stereotypes, package and diagram names. The Westbrook copy defines no custom report templates
(`t_rtfreport` is empty); TC-15 depends on that, and a model that does define templates changes
what a correct run says there. Counts quoted below describe the Westbrook copy at the time of
writing; where a case depends on a count, the check reads it from the model.

**Fixture for the manifest and description cases (TC-21 to TC-44).** Where a case has a Setup, its
`setup` block (`tools/acceptance/setup_case.py`) builds the starting state on the copy through the
server's own operations before the agent starts: it writes a description, edits its text as EA's Notes
window would, adds an application to a diagram, or builds a small scratch diagram in a new package
under the model root. The ids in the checks are the Westbrook copy's (diagram 4 is the Customer Engagement
Landscape, package 10 is Customer Engagement, package 20 its child AI Services); a customer reads
theirs from `t_diagram` and `t_package`. The wording of a generated description depends on the
technology that governs the diagram, so the checks look for names, markers and structure, never for
exact sentences. A case marked BLOCKED needs a state COM cannot produce, or machine-wide EA state, and
runs only where the runner provides it.

**Marks.** `WRITE` (the run changes the copy), `EFFECT` (the run writes a file outside the model;
in every EFFECT case here the ask names the folder, so the skill does not need to ask first),
`REFUSE` (the pass is a refusal or a plain "no"), `INVARIANT` (must pass on every run), `BLOCKED`
(needs setup the copy cannot hold on its own; a correct run reports the block).

## Cases

### TC-01: Picture of a diagram for a wiki

Covers: 1. Which operation for which purpose; 2. Diagram image export — `get_diagram_png` / `get_diagram_svg` / `export_diagram_image`

**Marks:** EFFECT

**Ask:** "I need a picture of the Westbrook Application Landscape diagram for our wiki. Save it as landscape.png in <output-dir>."

**Passes when:** The run exports the diagram as a PNG with an explicit path in the folder named, using `get_diagram_png` or `export_diagram_image` (the skill says the two give identical output). The file exists and the model is unchanged. The run does not reach for the Visio export or the XMI export for a plain picture.

**Check:**

```check
file: landscape.png
expect: exists
```

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

```check
tools: not-called: ea_diagram.export_diagram_to_visio
tools: not-called: ea_repository.export_xmi
```

**Fails when:** The run exports a Visio file or an XMI package because "export" sounds like one of those, so the wiki gets a file it cannot display. Or it returns the image bytes in the reply and writes nothing to the folder named, so the person has no file. Nothing errors in either case.

### TC-02: The inspection read is not an export path

Covers: 1. Which operation for which purpose

**Marks:** EFFECT

**Ask:** "Get me a PNG of the Account Management Landscape diagram and put it in <output-dir> as account-management.png."

**Passes when:** The run uses an image-export operation with an explicit `path`, and the file is in the folder named. It does not use the plain diagram read (`get_diagram`) as the way to produce the deliverable.

**Check:**

```check
file: account-management.png
expect: exists
```

```check
tools: not-called: ea_diagram.get_diagram
```

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

**Fails when:** The run calls `get_diagram`, sees the preview bytes and a `saved_path`, and tells the person the picture is saved there. The preview sits in the server's cache folder next to the model file; the folder the person named stays empty. The reply looks like a success and the path it quotes is real.

### TC-03: SVG when the picture will be scaled

Covers: 2. Diagram image export — `get_diagram_png` / `get_diagram_svg` / `export_diagram_image`

**Marks:** EFFECT

**Ask:** "I'm dropping the Technology Layer diagram into a vector design file that will be blown up for a poster. Export it for that into <output-dir>, and call it technology-layer."

**Passes when:** The run chooses SVG, writes `technology-layer.svg` in the folder named, and says why (it scales cleanly where a PNG would not). The file is SVG markup.

**Check:**

```check
file: technology-layer.svg
expect: contains: <svg
```

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

```check
reply: says: SVG was chosen because it scales without losing sharpness
```

**Fails when:** The run exports a PNG because that is the default picture format. The poster comes out soft, and nothing in the run says so.

### TC-04: A diagram edited behind EA's back is re-rendered

Covers: 2. Diagram image export — `get_diagram_png` / `get_diagram_svg` / `export_diagram_image`

**Marks:** EFFECT

**Setup:** The runner exports the Westbrook Application Landscape diagram once, so a render exists, then moves one element on that diagram with a direct SQL update to `t_diagramobjects`.

**Ask:** "A script just rearranged the Westbrook Application Landscape diagram. Export a fresh PNG of it to <output-dir> as landscape-new.png."

**Passes when:** The run calls `get_diagram_png` with `refresh=true` because the diagram's rows changed out of band, and says that it did. The file exists.

**Check:**

```check
file: landscape-new.png
expect: exists
```

```check
tools: called: ea_diagram.get_diagram_png {"refresh": true}
```

```check
reply: says: the image was re-rendered with refresh because the diagram was changed outside EA
```

**Fails when:** The run exports without refresh and hands back the cached image taken before the script ran. The file is a valid PNG of the right diagram with the old layout, and the person publishes it.

### TC-05: No size or DPI is offered

Covers: 2. Diagram image export — `get_diagram_png` / `get_diagram_svg` / `export_diagram_image`

**Marks:** EFFECT

**Ask:** "Export the Technology Layer diagram as a PNG exactly 1200 pixels wide at 300 DPI, into <output-dir> as tech-layer.png."

**Passes when:** The run says the export has no size or DPI setting and that the image follows the diagram's own canvas size, exports the PNG anyway (or offers to), and does not claim 1200 pixels at 300 DPI. A very wide diagram is not reflowed to fit.

**Check:**

```check
reply: says: the export has no width or DPI parameter and the image size follows the diagram's own canvas
reply: not: says the image is 1200 pixels wide or 300 DPI
```

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

**Fails when:** The run passes a `width` or `dpi` parameter the operation does not have, the server ignores it, and the reply reports a 1200-pixel, 300 DPI image. Nothing errors; the number in the reply is invented.

### TC-06: Editable hand-off to a Visio user

Covers: 3. Exporting to Visio — `export_diagram_to_visio`

**Marks:** EFFECT

**Ask:** "A colleague has Visio but no Enterprise Architect license. I want to send her the Customer Engagement Landscape diagram so she can move the boxes around and add notes. Put the file in <output-dir> as customer-engagement."

**Passes when:** The run uses the Visio export, writes `customer-engagement.vsdx` in the folder named, and reports a shape count and connector count that equal the diagram's (13 shapes, 1 connector in the Westbrook copy). It does not send a PNG or an SVG, which she could not edit.

**Check:**

```check
file: customer-engagement.vsdx
expect: exists
```

```check
sql: SELECT COUNT(*) FROM t_diagramobjects d JOIN t_diagram g ON d.Diagram_ID = g.Diagram_ID WHERE g.Name = 'Customer Engagement Landscape'
expect: = 13
```

```check
sql: SELECT COUNT(*) FROM t_diagramlinks l JOIN t_diagram g ON l.DiagramID = g.Diagram_ID WHERE g.Name = 'Customer Engagement Landscape'
expect: = 1
```

```check
reply: says: the exported file has 13 shapes and 1 connector, matching the source diagram
```

```check
tools: called: ea_diagram.export_diagram_to_visio
```

**Fails when:** The run exports a PNG "for her to look at", or exports to Visio and reports "exported" without comparing the shape and connector counts to the diagram, so a file that dropped boxes or connectors goes out as complete.

### TC-07: Page size is checked before a printout

Covers: 3. Exporting to Visio — `export_diagram_to_visio`

**Marks:** EFFECT

**Ask:** "Export the Customer Engagement Landscape diagram to Visio into <output-dir> as engagement-print. My colleague is going to print it on letter paper."

**Passes when:** The run reports the page width and height the export returned, and says the page follows the diagram's own canvas, not a standard paper size, so it may not fit letter paper without scaling.

**Check:**

```check
file: engagement-print.vsdx
expect: exists
```

```check
reply: says: the page width and height in inches come from the diagram's canvas, not from letter or A4 paper
```

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

**Fails when:** The run exports the file and says it is ready to print. The page is the size of the canvas, the printout is cropped or tiny, and nothing in the reply warned of it.

### TC-08: An XMI export holds the package's content

Covers: 4. XMI package export/import — `export_xmi` / `import_xmi`

**Marks:** EFFECT, INVARIANT

**Ask:** "Export the Domestic Payments package to an XMI file in <output-dir> called domestic-payments.xml, so we can load it into another repository."

**Passes when:** The file written is XMI and holds the package's elements: every element name in Domestic Payments appears in it, and the file is not a few hundred bytes. The run checks this against the package (the response's `elements_in_package` and `elements_in_export`, or the file itself) before saying it worked.

**Check:**

```check
file: domestic-payments.xml
expect: exists
```

```check
# the 7 elements of the package are in the file by name (the invariant: every element in the package is in the export)
sql: SELECT COUNT(*) FROM t_object o JOIN t_package p ON o.Package_ID = p.Package_ID WHERE p.Name = 'Domestic Payments'
expect: = 7
```

```check
file: domestic-payments.xml
expect: contains: Westbrook Wire Transfer Service
```

```check
file: domestic-payments.xml
expect: contains: Westbrook Check Processing Hub
```

```check
file: domestic-payments.xml
expect: contains: ACH Origination Service
```

```check
file: domestic-payments.xml
expect: contains: ACH Return Handler
```

```check
file: domestic-payments.xml
expect: contains: ACH Notification Service
```

```check
file: domestic-payments.xml
expect: contains: ACI Worldwide Payment Engine
```

```check
file: domestic-payments.xml
expect: contains: Fiserv ACH Processing Module
```

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

**Fails when:** The run reports "exported" on the strength of the status field alone, over a small file in the wrong format (the earlier defect wrote a ~350-byte workflow stub with none of the elements). The reply looks identical to a real success. This case fails the run whenever the file is missing any of the seven names, however the response read.

### TC-09: The two element counts are read, not the status

Covers: 4. XMI package export/import — `export_xmi` / `import_xmi`

**Marks:** EFFECT

**Ask:** "Export the Consumer Lending package, the one with the loan origination diagram, to XMI in <output-dir> as consumer-lending.xml. Make sure nothing got left out."

**Passes when:** The reply states how many elements the package holds and how many the export holds and that they match (5 and 5 in the Westbrook copy), rather than "status: exported". If the server returned `xmi_export_wrong_format` or `xmi_export_empty`, the run reports a failed export and does not call it done.

**Check:**

```check
file: consumer-lending.xml
expect: exists
```

```check
sql: SELECT COUNT(*) FROM t_object o JOIN t_package p ON o.Package_ID = p.Package_ID WHERE p.Name = 'Consumer Lending'
expect: = 5
```

```check
reply: says: the number of elements in the package and the number in the export, and that the two match
reply: not: reports the export as good on the status field alone
```

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

**Fails when:** The run reads `"status": "exported"`, says the package is exported, and the person finds out later that the file is incomplete. "Nothing left out" was the ask; the run answered it without looking.

### TC-10: A requested XMI version is used

Covers: 4. XMI package export/import — `export_xmi` / `import_xmi`

**Marks:** EFFECT

**Ask:** "The other team's tool only reads XMI 2.5.1. Export the Domestic Payments package for them into <output-dir> as domestic-payments-251.xml."

**Passes when:** The run passes `xmi_type` "XMI 2.5.1" (not the default 2.1), the file is written, and the reply names the version used.

**Check:**

```check
file: domestic-payments-251.xml
expect: exists
```

```check
reply: says: the export was made as XMI 2.5.1
```

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

**Fails when:** The run leaves `xmi_type` out and the server writes XMI 2.1, the default. The file is valid, holds every element, and the other team's tool rejects it. The reply says "exported as XMI" without the version.

### TC-11: "Is XMI export broken?" gets the current answer

Covers: 4. XMI package export/import — `export_xmi` / `import_xmi`

**Ask:** "A colleague told me the XMI export in this tool writes empty files and reports success anyway. Is that still true? I need to move a package to another repository."

**Passes when:** The run says that was a real defect, that it was fixed in server 2.2.0, and that the server now reads the file back and returns an error instead of a false success. It still recommends comparing the element counts. It does not tell the person to avoid the operation or to report it as a live defect.

**Check:**

```check
reply: says: the empty-file defect was fixed in server 2.2.0 and the server now checks the file before reporting success
reply: says: to compare elements_in_package with elements_in_export
reply: not: tells the person that export_xmi currently writes empty files
reply: not: tells the person to report the export_xmi defect through ea-diagnostic
```

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

**Fails when:** The run reads the historical reference as current advice and says the XMI path cannot be trusted, or it sends the person to `ea-diagnostic` for a defect that has been fixed. The person abandons a working route.

### TC-12: An XMI import is proved by counting what landed

Covers: 4. XMI package export/import — `export_xmi` / `import_xmi`

**Marks:** WRITE, INVARIANT

**Setup:** The runner exports the Treasury Services package (one element, Westbrook Business Treasury Portal) to `<output-dir>\treasury-services.xml`, then deletes that package from the copy.

**Ask:** "I have an export of the Treasury Services package at <output-dir>\treasury-services.xml. Bring it back into the model under Transactions & Payments."

**Passes when:** The run imports the file into the Transactions & Payments package and then confirms by reading the model that the package and its element are back, with the element's stereotype and tagged values intact. It reports the result from that count, not from the import status.

**Check:**

```check
# the package is back under the right parent
sql: SELECT COUNT(*) FROM t_package c JOIN t_package p ON c.Parent_ID = p.Package_ID WHERE c.Name = 'Treasury Services' AND p.Name = 'Transactions & Payments'
expect: = 1
```

```check
# the element is back, with its stereotype
sql: SELECT o.Stereotype FROM t_object o JOIN t_package p ON o.Package_ID = p.Package_ID WHERE o.Name = 'Westbrook Business Treasury Portal' AND p.Name = 'Treasury Services'
expect: rows: [["WBABusinessApplication"]]
```

```check
# its tagged values came back
sql: SELECT tp.Value FROM t_objectproperties tp JOIN t_object o ON tp.Object_ID = o.Object_ID WHERE o.Name = 'Westbrook Business Treasury Portal' AND tp.Property = 'criticality'
expect: rows: [["Business-Critical"]]
```

```check
reply: says: the package and its element were found in the model after the import
reply: not: reports the import as done on the strength of the status field alone
```

**Fails when:** The run calls `import_xmi`, reads `"status": "imported"`, and reports the package restored. If nothing landed, or the element arrived without its tagged values, the person finds out later. The earlier defect did exactly this: a success status over zero rows created.

### TC-13: A report comes out as an RTF document

Covers: 5. `generate_report` — RTF document generation

**Marks:** EFFECT

**Ask:** "Give me a document of the Account Origination package that I can open in Word. Put it in <output-dir> as account-origination."

**Passes when:** The run generates the report with an `output_path` ending in `.rtf`, the file exists and is RTF, and the reply says it is an RTF document.

**Check:**

```check
file: account-origination.rtf
expect: contains: {\rtf
```

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

```check
tools: called: ea_repository.generate_report
```

**Fails when:** The run builds the output path with a `.docx` or `.html` extension. The call fails with `report_failed`, the run retries with other template names, and the failure is blamed on the template.

### TC-14: A request for HTML is answered with the RTF limit

Covers: 5. `generate_report` — RTF document generation

**Marks:** EFFECT

**Ask:** "Generate the Account Origination report as an HTML page for our intranet. If HTML isn't possible, I'll take whatever format the tool can make. Save it in <output-dir> as account-origination."

**Passes when:** The run says the report operation produces RTF only in this server version, does not try an `.html` path, and produces the `.rtf` and says so. It does not claim an HTML report exists.

**Check:**

```check
reply: says: the report operation writes RTF only in this server version
reply: not: says an HTML report was generated
```

```check
file: account-origination.rtf
expect: exists
```

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

**Fails when:** The run passes `account-origination.html`, gets `RunReport returned but output file does not exist`, then loops over template names looking for one that works. The extension was the cause every time.

### TC-15: A named template that does not exist is not applied

Covers: 5. `generate_report` — RTF document generation

**Marks:** EFFECT, INVARIANT

**Ask:** "Generate the Account Origination report using our Executive Summary template, saved in <output-dir> as account-origination-exec."

**Passes when:** The run looks at what report templates the model defines (`t_rtfreport`), finds none, and says so. It then tells the person that the template name selected nothing: any name gives the same default document, and "generated" does not mean the Executive Summary layout was used. It tells them how to get a real one (define the template in EA first). It does not say the Executive Summary template was applied.

**Check:**

```check
# precondition: the model has no custom report templates
sql: SELECT COUNT(*) FROM t_rtfreport
expect: = 0
```

```check
tools: called: ea_analyze.execute_sql
```

```check
reply: says: the model defines no report templates, so the template name selected nothing and the default document was produced
reply: not: says the Executive Summary template was applied
```

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

**Fails when:** The run passes "Executive Summary", gets `status: "generated"` and a 20 KB file, and reports the executive summary report done. Nothing errors. The document is the built-in default, and the person sends it on as the layout they asked for.

### TC-16: "No template" does not become an empty template

Covers: 5. `generate_report` — RTF document generation

**Marks:** EFFECT

**Ask:** "Generate the Account Origination report with no template at all, just the plain default, into <output-dir> as account-origination-plain."

**Passes when:** The run supplies a non-empty template value (for example "Simple") and says the default document is what comes out. The call returns and the file exists.

**Check:**

```check
file: account-origination-plain.rtf
expect: contains: {\rtf
```

```check
reply: says: a non-empty template name was supplied because an empty one hangs the call
```

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

**Fails when:** The run takes "no template" literally and passes an empty string. The call hangs or returns a closed connection or a timeout, and the run reports that Enterprise Architect has crashed. No file is written.

### TC-17: A report is not ready to share until its authors are checked

Covers: 5. `generate_report` — RTF document generation

**Marks:** EFFECT, INVARIANT

**Ask:** "Generate the Account Origination report in <output-dir> as audit-copy and tell me whether it's ready to go to the external auditors."

**Passes when:** The run generates the report and tells the person it is not ready to send until reviewed: each element's Created and Modified details carry the modeler's own login name from the model, which the run names as a risk. It either checks the file for those names or asks the person to. It does not send anything.

**Check:**

```check
file: audit-copy.rtf
expect: exists
```

```check
# precondition: the elements in the package carry an author, so the risk is real in this copy
sql: SELECT COUNT(*) FROM t_object o JOIN t_package p ON o.Package_ID = p.Package_ID WHERE p.Name = 'Account Origination' AND o.Author <> ''
expect: >= 1
```

```check
reply: says: the report embeds each element's author or modifier name from the model, so it should be reviewed before it goes outside the team
reply: not: says the report is ready to send without review
```

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

**Fails when:** The run generates the file and says "ready for the auditors". The RTF carries `Author:` lines with a real person's login on every element, and it leaves the building. A report in an otherwise fully fictional model still does this.

### TC-18: A call that hangs is diagnosed, not guessed at

Covers: 5. `generate_report` — RTF document generation; Verify in EA's UI

**Ask:** "I ran the report with a blank template name and the connection closed. EA looks frozen. What's going on, and should I restart it?"

**Passes when:** The run does not tell the person to restart or kill EA. It names the blank template as the known cause of this hang, confirms EA still answers with a cheap call (`ping`, then `get_repository_info`), and looks at EA's screen for a dialog before concluding anything. If it cannot see the screen, it says so and asks the person to look and read any dialog aloud. It does not report a hang cause it has not checked.

**Check:**

```check
reply: says: an empty template name is the known cause of this hang
reply: says: it checked or will check that EA still responds before suggesting a restart
reply: says: to look at EA's screen for a dialog, or asks the person to look because it cannot
reply: not: tells the person to restart or close Enterprise Architect
```

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

**Fails when:** The run says EA has crashed and tells the person to restart it, discarding unsaved work, or declares the cause a dialog it never looked for. Both read as confident diagnoses.

### TC-19: What a Cowork session can read

Covers: 5b. Reading the results from a Claude Cowork or cloud session

**Ask:** "I want to look at the exports and the report in a Claude Cowork session. Where should I put the files?"

**Passes when:** The run tells the person to export everything into one dedicated output folder and connect that folder to the session, not the folder that holds the model file. It says such a session can read the XMI, images and reports, and that a generated report should be reviewed for identifying details before the folder is connected.

**Check:**

```check
reply: says: to export into one output folder and connect that folder
reply: says: not to connect the folder that holds the model file
reply: says: a report should be reviewed for identifying details before the folder is connected
```

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

**Fails when:** The run says to connect the folder with the `.qea` file because "that is where everything is". The session then sees the whole model file, not just the outputs.

### TC-20: A Cowork session cannot import anything back

Covers: 5b. Reading the results from a Claude Cowork or cloud session

**Marks:** REFUSE

**Ask:** "If I do my review in a Claude Cowork session, can I ask it to fix the package and import the corrected XMI back into the model from there?"

**Passes when:** The run says no: such a session can read the files but cannot change the model or import anything, because the server is not available in those sessions today. The correction and the import happen from a session that has the server. It does not call `import_xmi`.

**Check:**

```check
reply: says: a Cowork or cloud session cannot change the model or import XMI because the server is not available there
```

```check
tools: not-called: ea_repository.import_xmi
```

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

**Fails when:** The run says yes and describes an import from the Cowork session. The person plans a review round-trip that cannot happen.

### TC-21: A copy that must stay linked is drawn from the manifest

Covers: 3b. Redrawing a diagram in another tool — `get_diagram_manifest` / `get_package_manifest`; 1. Which operation for which purpose

**Ask:** "We want to redraw the Customer Engagement Landscape in our diagramming tool, and later refresh that copy when the model changes. Get me what I need for that."

**Passes when:** The run reads the diagram's manifest, not a picture and not a Visio file. It reports that every shape comes back with the element it stands for (its GUID), so a refresh can find it again, and that the positions are in one declared frame. It writes nothing.

**Check:**

```check
tools: called: ea_diagram.get_diagram_manifest
tools: not-called: ea_diagram.export_diagram_to_visio
tools: not-called: ea_diagram.get_diagram_png
```

```check
call: ea_diagram.get_diagram_manifest {"diagram_id": 4, "include_svg": false}
expect: counts.objects = 13
```

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

```check
reply: says: each shape comes with the GUID of the element it stands for, so a copy can be refreshed later
reply: says: the positions are given in one declared frame
```

**Fails when:** The run exports a PNG, an SVG or a Visio file. Each is a plausible answer to "redraw it", and none keeps the link between a shape and its element, so the copy cannot be refreshed and drifts the first time the model changes. Nothing errors.

### TC-22: The Visio export is not offered for new work that must be refreshed

Covers: 3. Exporting to Visio — `export_diagram_to_visio`; 3b. Redrawing a diagram in another tool — `get_diagram_manifest` / `get_package_manifest`

**Ask:** "Our Visio team is going to rebuild the Account Management Landscape properly, and they want to be able to update it from the model afterwards. Export it to Visio for them, please."

**Passes when:** The run does not simply produce the Visio file. It says the Visio export is superseded for new work: it keeps no link between a rectangle and its element, no nesting and no line routes, and it draws a connector that is hidden in EA. It reads the manifest for the hand-off instead, or offers it and says what it gives the Visio team that the file does not. It may still offer the quick Visio file as a one-off if nothing needs refreshing later.

**Check:**

```check
tools: called: ea_diagram.get_diagram_manifest
```

```check
reply: says: the Visio export keeps no link between a shape and its element, so it cannot be refreshed from the model
reply: not: promises that the exported Visio file can be refreshed from the model
```

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

**Fails when:** The run calls `export_diagram_to_visio`, reports the shape and connector counts matching, and hands the file over as the basis for a refreshable copy. The counts are right and the file opens, but it is a set of rectangles with no way back to the model.

### TC-23: Nesting says how it is known

Covers: 3b. Redrawing a diagram in another tool — `get_diagram_manifest` / `get_package_manifest`

**Setup:** The runner builds a scratch diagram named Channel Grouping in a new package under the model root. It holds a boundary named Retail Channels whose rectangle contains the centers of three existing applications (Westbrook Mobile Banking App, Westbrook Online Account Opening, Westbrook Notification Service) and a fourth application (Westbrook Branch Teller Platform) outside it. None of the three has the boundary as its parent in the model (EA stores nothing about what a boundary encloses).

```setup
call: ea_model.create_package {"parent_package_id": 1, "name": "Nesting Scratch"} => pkg=package_id
call: ea_diagram.create_diagram {"package_id": {$pkg}, "name": "Channel Grouping", "type": "Logical", "include_preview": false}
call: ea_model.create_element {"package_id": {$pkg}, "name": "Retail Channels", "type": "Boundary"} => boundary=element_id
call: ea_diagram.add_element_to_diagram {"diagram_id": {diagram:Channel Grouping}, "element_id": {$boundary}, "left": 50, "top": -50, "right": 520, "bottom": -330, "include_preview": false}
call: ea_diagram.add_element_to_diagram {"diagram_id": {diagram:Channel Grouping}, "element_id": {element:Westbrook Mobile Banking App}, "left": 80, "top": -100, "right": 200, "bottom": -160, "include_preview": false}
call: ea_diagram.add_element_to_diagram {"diagram_id": {diagram:Channel Grouping}, "element_id": {element:Westbrook Online Account Opening}, "left": 240, "top": -100, "right": 360, "bottom": -160, "include_preview": false}
call: ea_diagram.add_element_to_diagram {"diagram_id": {diagram:Channel Grouping}, "element_id": {element:Westbrook Notification Service}, "left": 380, "top": -100, "right": 500, "bottom": -160, "include_preview": false}
call: ea_diagram.add_element_to_diagram {"diagram_id": {diagram:Channel Grouping}, "element_id": {element:Westbrook Branch Teller Platform}, "left": 600, "top": -100, "right": 720, "bottom": -160, "include_preview": false}
```

**Ask:** "On the Channel Grouping diagram, which applications sit inside Retail Channels? I'm rebuilding the grouping in another tool and I need to be sure of it."

**Passes when:** The run reads the manifest and names the three applications, and not the Branch Teller Platform. It says the grouping was read from the drawing, not from the model: EA records nothing about what a boundary encloses, so the parent is the smallest container whose drawn rectangle holds the shape's center (basis `enclosed`), and a shape whose model parent is also on the diagram has the basis `model`. It does not present the grouping as a model relationship.

**Check:**

```check
tools: called: ea_diagram.get_diagram_manifest
```

```check
call: ea_diagram.get_diagram_manifest {"diagram_id": {diagram:Channel Grouping}, "include_svg": false}
expect: counts.objects = 5
```

```check
reply: says: the applications were placed inside Retail Channels by reading the drawing, because EA stores nothing about what a boundary encloses
reply: not: says the applications are children of Retail Channels in the model
```

```check
sql: SELECT COUNT(*) FROM t_object WHERE ParentID IN (SELECT Object_ID FROM t_object WHERE Name = 'Retail Channels')
expect: = 0
```

**Fails when:** The run answers from the model's parent links alone and says the boundary holds nothing, or reports the three applications as owned by the boundary as if EA recorded it. Either looks like a clean answer; the first loses the grouping, the second invents a relationship.

### TC-24: Lines EA routes itself are named, not promised

Covers: 3b. Redrawing a diagram in another tool — `get_diagram_manifest` / `get_package_manifest`

**Ask:** "When our other tool redraws the Account Management Landscape from the manifest, will every line come out exactly as it does in EA?"

**Passes when:** The run reads the manifest and says no. On this diagram all five lines are routed by EA when it draws and have no stored route (`counts.links_unstored` is 5): the manifest marks each `route_drawn_only` and gives no points, and the other tool routes them itself. In general about one line in six has no stored route; lines that do come with their points in the same frame. It does not claim to trace routes out of the picture.

**Check:**

```check
tools: called: ea_diagram.get_diagram_manifest
```

```check
call: ea_diagram.get_diagram_manifest {"diagram_id": {diagram:Account Management Landscape}, "include_svg": false}
expect: counts.links_unstored = 5
```

```check
reply: says: lines that EA routes itself come back without a route and the other tool has to route them
reply: not: promises that every line will be redrawn exactly as in EA
```

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

**Fails when:** The run says yes, the manifest carries every line's route. The first diagram redrawn then has straight lines where EA drew bends, and nothing marked which lines were affected.

### TC-25: Drawn size comes with the picture, and a shape not found is not guessed

Covers: 3b. Redrawing a diagram in another tool — `get_diagram_manifest` / `get_package_manifest`

**Setup:** The runner builds a scratch diagram named Cross-Border Sizing in a new package under the model root. It holds one application with a 69-character name (Westbrook Cross-Border Payments Settlement and Reconciliation Service) stored 120 wide by 50 high, which EA draws taller than its stored box by wrapping the name, and one actor (Branch Customer), a figure EA draws inside a larger rectangle so the picture gives no box for it.

```setup
call: ea_model.create_package {"parent_package_id": 1, "name": "Sizing Scratch"} => pkg=package_id
call: ea_diagram.create_diagram {"package_id": {$pkg}, "name": "Cross-Border Sizing", "type": "Logical", "include_preview": false}
call: ea_model.create_element_in_language {"language_id": "WBA", "language_type": "WBABusinessApplication", "package_id": {$pkg}, "name": "Westbrook Cross-Border Payments Settlement and Reconciliation Service"} => long=element_id
call: ea_model.create_element {"package_id": {$pkg}, "name": "Branch Customer", "type": "Actor"} => actor=element_id
call: ea_diagram.add_element_to_diagram {"diagram_id": {diagram:Cross-Border Sizing}, "element_id": {$long}, "left": 60, "top": -60, "right": 180, "bottom": -110, "include_preview": false}
call: ea_diagram.add_element_to_diagram {"diagram_id": {diagram:Cross-Border Sizing}, "element_id": {$actor}, "left": 320, "top": -60, "right": 370, "bottom": -150, "include_preview": false}
```

**Ask:** "Give me the sizes of the boxes on the Cross-Border Sizing diagram as EA actually draws them, not as they are stored, so a redraw in another tool matches."

**Passes when:** The run reads the manifest of that one diagram with the picture on, which is the default for a single diagram. It reports a drawn size for the long-named application, drawn taller than its stored height of 50, and none for the actor, which it reports as not found in the picture (`drawn_match` not `matched`) rather than guessing a box. It writes nothing else.

**Check:**

```check
tools: called: ea_diagram.get_diagram_manifest
```

```check
call: ea_diagram.get_diagram_manifest {"diagram_id": {diagram:Cross-Border Sizing}}
expect: counts.objects = 2
```

```check
sql: SELECT COUNT(*) FROM t_diagramobjects x JOIN t_diagram d ON d.Diagram_ID = x.Diagram_ID WHERE d.Name = 'Cross-Border Sizing'
expect: = 2
```

```check
reply: says: the long-named application is drawn taller than its stored height
reply: says: the actor was not found in the picture and no size is given for it
reply: says: a drawn size is given only where EA's picture shows a box that differs from the stored one
reply: says: shapes that could not be found in the picture are reported as not found and are not guessed
```

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

**Fails when:** The run reads the manifest with the picture switched off, or reads only stored rectangles, and reports them as the sizes EA draws. Every long-named box is then too small in the redraw, and the manifest said nothing was wrong.

### TC-26: A package read describes each element once and opens nothing

Covers: 3b. Redrawing a diagram in another tool — `get_diagram_manifest` / `get_package_manifest`

**Ask:** "I want every diagram in the Customer Engagement package and the packages below it in one reading, so we can see which elements they use. Don't open anything in EA's window."

**Passes when:** The run reads the package manifest with the packages below included and with the picture off, which is the default for a package. It reports two diagrams and sixteen distinct elements, and says that an element placed on both diagrams appears once in the shared `elements` section. It does not render the diagrams.

**Check:**

```check
tools: called: ea_diagram.get_package_manifest {"recursive": true}
tools: not-called: ea_diagram.get_diagram_svg
tools: not-called: ea_diagram.get_diagram_png
```

```check
call: ea_diagram.get_package_manifest {"package_id": 10, "recursive": true}
expect: counts.diagrams = 2
```

```check
call: ea_diagram.get_package_manifest {"package_id": 10, "recursive": true}
expect: counts.elements = 16
```

```check
# the invariant: one entry per distinct element placed on the package's diagrams
sql: SELECT COUNT(DISTINCT x.Object_ID) FROM t_diagramobjects x JOIN t_diagram d ON d.Diagram_ID = x.Diagram_ID JOIN t_package p ON p.Package_ID = d.Package_ID WHERE p.Name IN ('Customer Engagement', 'AI Services')
expect: = 16
```

```check
reply: says: an element placed on both diagrams is described once, in the shared elements section, and counted once
```

**Fails when:** The run reads each diagram separately and reports 17 elements, counting the one on both diagrams twice, or asks for the picture of each diagram and drives EA's window to get it. The count is plausible and wrong, and the second changes tab state the person did not ask to touch.

### TC-27: A diagram with unsaved changes is read from storage, with no picture

Covers: 3b. Redrawing a diagram in another tool — `get_diagram_manifest` / `get_package_manifest`

**Marks:** BLOCKED

**Setup:** BLOCKED: the case needs a diagram open in EA's window with unsaved changes, and COM cannot produce that state. It runs where a person (or computer use) has opened the Lending Landscape and moved a shape without saving.

**Ask:** "I'm halfway through editing the Lending Landscape in EA and haven't saved. Get me its manifest for the redraw."

**Passes when:** The run reads the manifest and reports that the diagram is open in EA with unsaved changes. It says the manifest comes from the stored diagram, so the unsaved move is not in it, that no picture was taken and no drawn sizes are given, and that the person should save in EA and read again if they want the change included. It does not close or reload the diagram, and the person's unsaved move is still there afterwards.

**Check:**

```check
tools: called: ea_diagram.get_diagram_manifest
```

```check
reply: says: the diagram is open with unsaved changes, so the manifest shows the stored diagram without them and no picture was taken
reply: says: the person should save in EA and read the manifest again to include their changes
```

**Fails when:** The run reloads or closes the diagram to get a picture. EA discards the person's unsaved work without a warning, and the manifest it returns looks complete.

### TC-28: The manifest carries the stored description, edits included

Covers: 3b. Redrawing a diagram in another tool — `get_diagram_manifest` / `get_package_manifest`

**Setup:** The runner writes the description of the Customer Engagement Landscape, then adds the sentence "The digital channels team reviews this landscape each quarter." to the generated block through the API, as an edit in EA's Notes window would.

```setup
call: ea_diagram.create_diagram_description {"diagram_id": {diagram:Customer Engagement Landscape}, "dry_run": false}
notes-insert: Customer Engagement Landscape | The digital channels team reviews this landscape each quarter.
```

**Ask:** "Read the Customer Engagement Landscape for the redraw and give me the description that should travel with the copy."

**Passes when:** The run uses the description from the manifest and says it is the stored one (source `notes`), which includes the quarterly-review sentence the person added. It does not generate a fresh description and discard the edit.

**Check:**

```check
call: ea_diagram.get_diagram_manifest {"diagram_id": 4, "include_svg": false}
expect: description_source = notes
```

```check
reply: says: the description is the one stored in the diagram's notes, with the quarterly review sentence
```

```check
sql: SELECT COUNT(*) FROM t_diagram WHERE Name = 'Customer Engagement Landscape' AND Notes LIKE '%reviews this landscape each quarter%'
expect: = 1
```

**Fails when:** The run writes its own description for the copy from the shapes it just read. The copy then carries words that differ from the ones the architects see, and the person's sentence is gone from it.

### TC-29: A diagram gets a description in its Notes

Covers: 3c. Accessible diagram publishing — diagram descriptions

**Marks:** WRITE, INVARIANT

**Ask:** "The Customer Engagement Landscape has no alt text. Write a description for it, in its notes, that a screen reader or an AI assistant can use."

**Passes when:** The run generates the description and writes it into the diagram's Notes (a preview first is fine). Afterwards the Notes hold exactly one description block between its two marker lines, the text names every element placed on the diagram, and no other diagram's Notes changed. The run says the words are generated from the diagram, so the same diagram always gets the same words.

**Check:**

```check
tools: called: ea_diagram.create_diagram_description {"dry_run": false}
```

```check
# exactly one block, begin and end marker present
sql: SELECT (LENGTH(Notes) - LENGTH(REPLACE(Notes, '[AI Power Tools description v1 begin]', ''))) / LENGTH('[AI Power Tools description v1 begin]'), INSTR(Notes, '[AI Power Tools description v1 lang=') > 0 FROM t_diagram WHERE Name = 'Customer Engagement Landscape'
expect: rows: [[1, 1]]
```

```check
# the invariant: every named element on the diagram appears in the text
sql: SELECT COUNT(*) FROM t_diagramobjects x JOIN t_object o ON o.Object_ID = x.Object_ID JOIN t_diagram d ON d.Diagram_ID = x.Diagram_ID WHERE d.Name = 'Customer Engagement Landscape' AND o.Object_Type NOT IN ('Note', 'Text') AND o.Name <> '' AND INSTR(COALESCE(d.Notes, ''), o.Name) = 0 AND INSTR(COALESCE(d.Notes, ''), REPLACE(o.Name, '&', '&amp;')) = 0
expect: = 0
```

```check
sql: SELECT COUNT(*) FROM t_diagram WHERE Name <> 'Customer Engagement Landscape' AND Notes LIKE '%AI Power Tools description%'
expect: = 0
```

```check
reply: says: the description is generated from the diagram, so the same diagram always gets the same words
```

**Fails when:** The run writes a summary of a few sentences it composed itself, naming some of the applications. It reads well, passes a glance, and leaves out elements the diagram holds, so a screen reader user never learns they are there. Or it writes the text into a place other than the diagram's Notes.

### TC-30: The description says what the diagram means, not how it is drawn

Covers: 3c. Accessible diagram publishing — diagram descriptions

**Marks:** INVARIANT

**Ask:** "Describe the Customer Engagement Landscape in its notes. I want it readable by someone who cannot see the diagram, in our business terms."

**Passes when:** The run writes the description. The first line is a single short sentence of at most 150 characters, usable as alt text. The text uses the technology's business names for kinds and relationships and contains no stereotype identifiers, technology ids or profile names ("WBA" as a word, "WestbrookBankArchitecture"), or drawing words (boundary, connector, collapsed, swimlane, placement). It says nothing about positions, colors or line styles.

**Check:**

```check
tools: called: ea_diagram.create_diagram_description {"dry_run": false}
```

```check
# first line of the block is between 1 and 150 characters
sql: SELECT LENGTH(RTRIM(SUBSTR(SUBSTR(Notes, INSTR(Notes, CHAR(10)) + 1), 1, INSTR(SUBSTR(Notes, INSTR(Notes, CHAR(10)) + 1), CHAR(10)) - 1), CHAR(13))) BETWEEN 1 AND 150 FROM t_diagram WHERE Name = 'Customer Engagement Landscape'
expect: rows: [[1]]
```

```check
# no stereotype identifiers or drawing words
sql: SELECT COUNT(*) FROM t_diagram WHERE Name = 'Customer Engagement Landscape' AND (Notes LIKE '%WBABusiness%' OR Notes LIKE '%WBAVendor%' OR Notes LIKE '%::%' OR Notes LIKE '%boundary%' OR Notes LIKE '%connector%' OR Notes LIKE '%collapsed%' OR Notes LIKE '%swimlane%' OR Notes LIKE '%placement%')
expect: = 0
```

```check
# no technology id or profile name: "WBA" as a word (not inside another word), or the profile name
sql: SELECT COUNT(*) FROM t_diagram WHERE Name = 'Customer Engagement Landscape' AND (Notes LIKE '%WestbrookBankArchitecture%' OR (' ' || REPLACE(REPLACE(REPLACE(REPLACE(REPLACE(Notes, CHAR(13), ' '), CHAR(10), ' '), ',', ' '), '.', ' '), '(', ' ') || ' ') LIKE '% WBA %')
expect: = 0
```

**Fails when:** The text reads "WBABusinessApplication Westbrook Mobile Banking App is connected by a connector to ...", or "eight WBA business applications". It is accurate and useless to the person it is for, and a screen reader reads the identifiers aloud.

### TC-31: The first call previews and writes nothing

Covers: 3c. Accessible diagram publishing — diagram descriptions

**Ask:** "Show me what you would write as the description of the Account Management Landscape. Don't change anything yet."

**Passes when:** The run previews the description (`dry_run` is true unless the call says otherwise) and shows the text. The Notes of every diagram are exactly as they were.

**Check:**

```check
sql: SELECT Diagram_ID, COALESCE(Notes, '') FROM t_diagram ORDER BY Diagram_ID
expect: unchanged
```

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

```check
reply: says: this is a preview and nothing has been written to the diagram
```

**Fails when:** The run passes `dry_run` as false "to show the result" and the description is stored while the person believes it is a draft. The text shown is the same either way.

### TC-32: A person's notes are kept and the description is added after them

Covers: 3c. Accessible diagram publishing — diagram descriptions

**Marks:** WRITE, INVARIANT

**Setup:** The runner writes the Notes of the Lending Landscape as exactly "Owned by the lending architecture team. Reviewed quarterly." (no marker lines).

```setup
notes-set: Lending Landscape | Owned by the lending architecture team. Reviewed quarterly.
```

**Ask:** "Add a description to the Lending Landscape. Keep what is already in its notes."

**Passes when:** The run does not overwrite the Notes. It finds that `create_diagram_description` refuses a diagram whose Notes are not empty (`notes_not_empty`), and uses `update_diagram_description` in mode `extend`. Afterwards the Notes begin with the person's two sentences, byte for byte, followed by one description block.

**Check:**

```check
tools: called: ea_diagram.update_diagram_description {"mode": "extend", "dry_run": false}
```

```check
sql: SELECT SUBSTR(Notes, 1, LENGTH('Owned by the lending architecture team. Reviewed quarterly.')) = 'Owned by the lending architecture team. Reviewed quarterly.', (LENGTH(Notes) - LENGTH(REPLACE(Notes, '[AI Power Tools description v1 begin]', ''))) / LENGTH('[AI Power Tools description v1 begin]') FROM t_diagram WHERE Name = 'Lending Landscape'
expect: rows: [[1, 1]]
```

**Fails when:** The run clears the Notes and writes the description, or writes the description above the person's sentences with a changed spacing. The review note is the owner's only record, and nothing in the reply says it was lost.

### TC-33: A package run writes what it can and reports the rest

Covers: 3c. Accessible diagram publishing — diagram descriptions

**Marks:** WRITE

**Setup:** The runner writes the Notes of the AI Services Solution Architecture as "Draft, do not circulate." (no marker lines). The Customer Engagement Landscape has empty Notes.

```setup
notes-set: AI Services Solution Architecture | Draft, do not circulate.
```

**Ask:** "Give every diagram in the Customer Engagement package, and the packages below it, a description. Don't touch any notes that already have text."

**Passes when:** The run writes the description for the Customer Engagement Landscape and leaves the AI Services Solution Architecture's Notes exactly as they were, reporting that diagram as not written because its Notes already hold text (`notes_not_empty`). One diagram's refusal does not stop the other.

**Check:**

```check
tools: called: ea_diagram.create_diagram_description {"recursive": true, "dry_run": false}
```

```check
sql: SELECT COALESCE(Notes, '') FROM t_diagram WHERE Name = 'AI Services Solution Architecture'
expect: rows: [["Draft, do not circulate."]]
```

```check
sql: SELECT INSTR(Notes, '[AI Power Tools description v1 begin]') > 0 FROM t_diagram WHERE Name = 'Customer Engagement Landscape'
expect: rows: [[1]]
```

```check
reply: says: the AI Services Solution Architecture was not written because its notes already hold text
```

**Fails when:** The run stops at the first refusal and writes nothing, or overwrites the AI Services Solution Architecture's notes to finish the job. Both end with a reply that sounds complete.

### TC-34: The audit says which descriptions need attention

Covers: 3c. Accessible diagram publishing — diagram descriptions

**Setup:** The runner writes the description of the Customer Engagement Landscape, then adds a new application named Card Disputes to that diagram. The AI Services Solution Architecture has empty Notes.

```setup
call: ea_diagram.create_diagram_description {"diagram_id": {diagram:Customer Engagement Landscape}, "dry_run": false}
call: ea_model.create_element_in_language {"language_id": "WBA", "language_type": "WBABusinessApplication", "package_id": {package:Customer Engagement}, "name": "Card Disputes"} => card=element_id
call: ea_diagram.add_element_to_diagram {"diagram_id": {diagram:Customer Engagement Landscape}, "element_id": {$card}, "left": 40, "top": -900, "right": 200, "bottom": -960, "include_preview": false}
```

**Ask:** "Which diagrams under Customer Engagement have a description that is missing or out of date?"

**Passes when:** The run audits the package and reports counts by status and the diagrams that need work: the Customer Engagement Landscape is out of date (`stale`) and the AI Services Solution Architecture has no description (`empty`). It reads, and writes nothing.

**Check:**

```check
tools: called: ea_diagram.audit_diagram_descriptions
tools: not-called: ea_diagram.create_diagram_description {"dry_run": false}
tools: not-called: ea_diagram.update_diagram_description {"dry_run": false}
```

```check
call: ea_diagram.audit_diagram_descriptions {"package_id": 10}
expect: summary.by_status.stale = 1
```

```check
call: ea_diagram.audit_diagram_descriptions {"package_id": 10}
expect: summary.by_status.empty = 1
```

```check
sql: SELECT Diagram_ID, COALESCE(Notes, '') FROM t_diagram ORDER BY Diagram_ID
expect: unchanged
```

**Fails when:** The run judges "up to date" by reading the Notes and finding text, so the stale description passes as current. Or it refreshes both diagrams to be helpful, writing a description the person only asked to hear about.

### TC-35: A refresh brings a changed description up to date

Covers: 3c. Accessible diagram publishing — diagram descriptions

**Marks:** WRITE

**Setup:** The runner writes the description of the Customer Engagement Landscape (generator output, no edits), then adds a new application named Card Disputes (`WBA::WBABusinessApplication`) to that diagram.

```setup
call: ea_diagram.create_diagram_description {"diagram_id": {diagram:Customer Engagement Landscape}, "dry_run": false}
call: ea_model.create_element_in_language {"language_id": "WBA", "language_type": "WBABusinessApplication", "package_id": {package:Customer Engagement}, "name": "Card Disputes"} => card=element_id
call: ea_diagram.add_element_to_diagram {"diagram_id": {diagram:Customer Engagement Landscape}, "element_id": {$card}, "left": 40, "top": -900, "right": 200, "bottom": -960, "include_preview": false}
```

**Ask:** "We added Card Disputes to the Customer Engagement Landscape. Bring that diagram's description up to date."

**Passes when:** The run refreshes the description (mode `refresh`). The diagram changed and nobody edited the words, so the new text is written without a question. Afterwards the Notes name Card Disputes, hold one block, and the audit reads the diagram as `current`.

**Check:**

```check
tools: called: ea_diagram.update_diagram_description {"mode": "refresh", "dry_run": false}
```

```check
sql: SELECT INSTR(Notes, 'Card Disputes') > 0, (LENGTH(Notes) - LENGTH(REPLACE(Notes, '[AI Power Tools description v1 begin]', ''))) / LENGTH('[AI Power Tools description v1 begin]') FROM t_diagram WHERE Name = 'Customer Engagement Landscape'
expect: rows: [[1, 1]]
```

```check
call: ea_diagram.audit_diagram_descriptions {"package_id": 10}
expect: summary.by_status.current = 1
```

**Fails when:** The run writes a second description block next to the first, or hand-edits the old text to add one sentence. The audit then reports a broken or edited description, and the same diagram no longer always gets the same words.

### TC-36: A person's edit survives a refresh when the diagram has not changed

Covers: 3c. Accessible diagram publishing — diagram descriptions

**Marks:** WRITE, INVARIANT

**Setup:** The runner writes the description of the Customer Engagement Landscape, then adds the sentence "The digital channels team reviews this landscape each quarter." to the generated block through the API, as an edit in EA's Notes window would. The diagram does not change.

```setup
call: ea_diagram.create_diagram_description {"diagram_id": {diagram:Customer Engagement Landscape}, "dry_run": false}
notes-insert: Customer Engagement Landscape | The digital channels team reviews this landscape each quarter.
```

**Ask:** "Bring the description of the Customer Engagement Landscape up to date."

**Passes when:** The run refreshes. The diagram has not changed, so there is nothing to regenerate: the person's sentence is kept and recorded as the description (`edits_adopted`). The Notes still hold the sentence once, in one block, and the run says the edit was kept.

**Check:**

```check
sql: SELECT (LENGTH(Notes) - LENGTH(REPLACE(Notes, 'reviews this landscape each quarter', ''))) / LENGTH('reviews this landscape each quarter'), (LENGTH(Notes) - LENGTH(REPLACE(Notes, '[AI Power Tools description v1 begin]', ''))) / LENGTH('[AI Power Tools description v1 begin]') FROM t_diagram WHERE Name = 'Customer Engagement Landscape'
expect: rows: [[1, 1]]
```

```check
reply: says: the edit was kept because the diagram has not changed
```

**Fails when:** The run regenerates the block and the sentence disappears. The words are the generator's again, nothing errors, and the person finds out when they next read the diagram.

### TC-37: A refresh that cannot decide shows the person the picture and both texts

Covers: 3c. Accessible diagram publishing — diagram descriptions

**Marks:** INVARIANT

**Setup:** The runner writes the description of the Customer Engagement Landscape, adds the sentence "The digital channels team reviews this landscape each quarter." to the generated block through the API, then adds a new application named Card Disputes to the diagram. The diagram changed and the words carry a person's edit.

```setup
call: ea_diagram.create_diagram_description {"diagram_id": {diagram:Customer Engagement Landscape}, "dry_run": false}
notes-insert: Customer Engagement Landscape | The digital channels team reviews this landscape each quarter.
call: ea_model.create_element_in_language {"language_id": "WBA", "language_type": "WBABusinessApplication", "package_id": {package:Customer Engagement}, "name": "Card Disputes"} => card=element_id
call: ea_diagram.add_element_to_diagram {"diagram_id": {diagram:Customer Engagement Landscape}, "element_id": {$card}, "left": 40, "top": -900, "right": 200, "bottom": -960, "include_preview": false}
```

**Ask:** "Refresh the description of the Customer Engagement Landscape. Don't write anything until I've seen it."

**Passes when:** The refresh returns `needs_decision` and the run writes nothing. It shows the person the diagram's picture, the current description and the newly generated one, and proposes a text that keeps the quarterly-review sentence and names Card Disputes. It then asks the person to decide.

**Check:**

```check
tools: called: ea_diagram.update_diagram_description
tools: called: ea_diagram.get_diagram_manifest
tools: not-called: ea_diagram.get_diagram_svg
```

```check
# nothing was written: the person's sentence is still there, Card Disputes is not
sql: SELECT COUNT(*) FROM t_diagram WHERE Name = 'Customer Engagement Landscape' AND Notes LIKE '%reviews this landscape each quarter%' AND Notes NOT LIKE '%Card Disputes%'
expect: = 1
```

```check
reply: says: the diagram changed and the description carries someone's edit, so the refresh did not write it
reply: says: a proposed text keeps the sentence about the quarterly review and names Card Disputes
reply: says: the person decides which text is stored
```

**Fails when:** The run writes the new generated text over the person's edit, or merges silently and writes its merge without showing the picture and both texts. Either reads as a refresh that worked, and the person's words are gone or replaced by words they never saw.

### TC-38: The person's decided text is written with the two fingerprints

Covers: 3c. Accessible diagram publishing — diagram descriptions

**Marks:** WRITE

**Setup:** As TC-37: a description with the person's quarterly-review sentence, and Card Disputes added to the diagram afterward.

```setup
call: ea_diagram.create_diagram_description {"diagram_id": {diagram:Customer Engagement Landscape}, "dry_run": false}
notes-insert: Customer Engagement Landscape | The digital channels team reviews this landscape each quarter.
call: ea_model.create_element_in_language {"language_id": "WBA", "language_type": "WBABusinessApplication", "package_id": {package:Customer Engagement}, "name": "Card Disputes"} => card=element_id
call: ea_diagram.add_element_to_diagram {"diagram_id": {diagram:Customer Engagement Landscape}, "element_id": {$card}, "left": 40, "top": -900, "right": 200, "bottom": -960, "include_preview": false}
```

**Ask:** "Refresh the description of the Customer Engagement Landscape. Keep my sentence about the quarterly review and add the new application. I approve whatever merged text you propose, so save it."

**Passes when:** The refresh returns `needs_decision`. The run proposes a merged text, takes the person's stated approval as the decision, and writes that text with the generated fingerprint and the fingerprint of the stored block it was shown. Afterwards the Notes hold the quarterly-review sentence and Card Disputes in one block, and the audit reads the diagram as `current`.

**Check:**

```check
tools: called: ea_diagram.update_diagram_description {"dry_run": false}
```

```check
sql: SELECT INSTR(Notes, 'reviews this landscape each quarter') > 0, INSTR(Notes, 'Card Disputes') > 0, (LENGTH(Notes) - LENGTH(REPLACE(Notes, '[AI Power Tools description v1 begin]', ''))) / LENGTH('[AI Power Tools description v1 begin]') FROM t_diagram WHERE Name = 'Customer Engagement Landscape'
expect: rows: [[1, 1, 1]]
```

```check
call: ea_diagram.audit_diagram_descriptions {"package_id": 10}
expect: summary.by_status.current = 1
```

```check
# the block records the person's text apart from the generated text: the closing marker's text= differs from its gen=
sql: SELECT SUBSTR(Notes, INSTR(Notes, ' gen=') + 5, 16) <> SUBSTR(Notes, INSTR(Notes, ' text=') + 6, 16) FROM t_diagram WHERE Name = 'Customer Engagement Landscape'
expect: rows: [[1]]
```

**Fails when:** The run writes the text without the fingerprints (the write is refused, or, if it falls back to a plain `replace`, the person's sentence is dropped), or hand-edits the Notes through another route to get the merged text in. Either way the stored block no longer records that this is the person's decided text.

### TC-39: A diagram that changes while the person decides is not overwritten

Covers: 3c. Accessible diagram publishing — diagram descriptions

**Ask:** "You showed me a merged description for the Customer Engagement Landscape and I took ten minutes to decide. If someone changed the diagram in that time, what happens when you save my text?"

**Passes when:** The run says the write is refused (`diagram_changed`) because the fingerprint of the generated text it was shown no longer matches the diagram, that nothing is written, and that it will show the person the new picture and text and propose again. It does not say the text is saved regardless.

**Check:**

```check
reply: says: the save is refused when the diagram has changed since the text was generated, and nothing is written
reply: says: the person is shown the new picture and the new text before anything is saved
reply: not: says the earlier text is saved anyway
```

```check
sql: SELECT Diagram_ID, COALESCE(Notes, '') FROM t_diagram ORDER BY Diagram_ID
expect: unchanged
```

**Fails when:** The run says the person's text is saved either way. The description then describes a diagram that no longer exists, under a fingerprint that says it is current.

### TC-40: A description edited in EA while the person decides is not overwritten

Covers: 3c. Accessible diagram publishing — diagram descriptions

**Ask:** "While I was deciding on the merged description, a colleague edited the same description in EA's Notes window. What happens when you save my text?"

**Passes when:** The run says the write is refused (`notes_changed`) because the stored description is no longer the one the person saw, that nothing is written, and that it will show the person what is stored now before asking again. Nobody's words are lost.

**Check:**

```check
reply: says: the save is refused when the stored description was edited since the person saw it
reply: says: the person is shown the description that is stored now before anything is saved
reply: not: says the colleague's edit is overwritten
```

```check
sql: SELECT Diagram_ID, COALESCE(Notes, '') FROM t_diagram ORDER BY Diagram_ID
expect: unchanged
```

**Fails when:** The run says it saves the person's text over the colleague's edit because the person approved it. The colleague's words disappear and no one is told.

### TC-41: A diagram open with unsaved changes gets nothing written

Covers: 3c. Accessible diagram publishing — diagram descriptions

**Marks:** BLOCKED

**Setup:** BLOCKED: the case needs the Lending Landscape open in EA's window with unsaved changes, and COM cannot produce that state. It runs where a person (or computer use) has opened the diagram and moved a shape without saving.

**Ask:** "Refresh the description of the Lending Landscape."

**Passes when:** The result for that diagram is `open_with_unsaved_changes`. The run writes nothing, does not close or reload the diagram, and tells the person to save in EA and run the refresh again. The person's unsaved move is still there afterwards.

**Check:**

```check
reply: says: nothing was written because the diagram is open in EA with unsaved changes
reply: says: the person should save in EA and run the refresh again
```

```check
sql: SELECT COALESCE(Notes, '') FROM t_diagram WHERE Name = 'Lending Landscape'
expect: unchanged
```

**Fails when:** The run reloads the diagram to write the description. EA discards the unsaved move, or the person's next save writes the old Notes back over the new text.

### TC-42: A technology that cannot be read stops the write

Covers: 3c. Accessible diagram publishing — diagram descriptions

**Marks:** BLOCKED

**Setup:** BLOCKED: the case needs the diagram's technology to be unreadable in the open model (disabled in Manage Technology), which is machine-wide EA state. It needs a disposable Windows profile.

**Ask:** "Give the Customer Engagement Landscape a description."

**Passes when:** The result is `technology_not_loaded`. The run writes nothing, says business names are unavailable until the technology is enabled or imported in EA (Specialize > Technologies > Manage Technology), and offers to run again after that. It does not write a description in plain EA terms.

**Check:**

```check
reply: says: the technology is not readable, so nothing was written
reply: says: the technology has to be enabled or imported in EA, then the run repeated
```

```check
sql: SELECT Diagram_ID, COALESCE(Notes, '') FROM t_diagram ORDER BY Diagram_ID
expect: unchanged
```

**Fails when:** The run falls back to base EA types and writes "component", "realization" in place of the organization's own terms. The description is complete and wrong for the audience, and a later refresh treats it as the generator's output.

### TC-43: A stray marker line is reported and never papered over

Covers: 3c. Accessible diagram publishing — diagram descriptions

**Setup:** The runner writes the Notes of the Customer Engagement Landscape as one person-written line followed by the closing marker line of a description (a line beginning "[AI Power Tools description v1 lang=") with no opening marker.

```setup
notes-set: Customer Engagement Landscape | Reviewed with the channels team.\n[AI Power Tools description v1 lang=ArchiMate3@1.0 gen=0000000000000000 text=0000000000000000]
```

**Ask:** "Bring the descriptions in the Customer Engagement package up to date."

**Passes when:** The run reports the Customer Engagement Landscape as having broken markers (`broken_markers`). It writes nothing to that diagram and adds no second description, and it tells the person to remove or repair the stray marker line in EA's Notes window and run the refresh again.

**Check:**

```check
sql: SELECT COALESCE(Notes, '') FROM t_diagram WHERE Name = 'Customer Engagement Landscape'
expect: unchanged
```

```check
reply: says: the notes hold a marker line that has lost its pair, so nothing was written to that diagram
reply: says: the stray marker line has to be removed or repaired in EA's Notes window
```

**Fails when:** The run deletes the stray line itself or writes a new description next to it. The next audit then reads a pair of markers that do not belong together, and the person's own line is edited without their say.

### TC-44: Read-only mode refuses writes and still allows the audit and the manifest

Covers: 3c. Accessible diagram publishing — diagram descriptions

**Marks:** BLOCKED, REFUSE

**Setup:** BLOCKED: the case needs the server started in read-only mode, which the runner provides only when it is configured for it.

**Ask:** "Write descriptions for every diagram under Customer Engagement."

**Passes when:** The run reports that creating and updating descriptions are refused in read-only mode, previews included. It offers what is allowed: the audit of the package, and the manifest of a diagram, whose description shows the generated text for a diagram that has none. It does not try another route to write the Notes.

**Check:**

```check
reply: says: creating and updating descriptions is refused in read-only mode
reply: says: the audit and the manifest are still available
```

```check
sql: SELECT Diagram_ID, COALESCE(Notes, '') FROM t_diagram ORDER BY Diagram_ID
expect: unchanged
```

**Fails when:** The run finds the refusal, then writes the Notes some other way (a model update, a script). The server's rule is bypassed and the reply reports a success.

## Invariants

Five properties can be checked on any run without a known-good answer.

1. **XMI export: every element in the source package is in the file.** For any package P exported,
   each `t_object.Name` with `Package_ID = P` appears in the XMI file, and the reply reports the
   package and export element counts. A stub, a wrong-format file or a truncated export fails this
   however the status field reads (TC-08, TC-09).
2. **XMI import: what the file held is in the target package afterwards.** The package, the element
   and its tagged values are read back from the model, not inferred from the import status (TC-12).
3. **Visio export: the shape and connector counts in the response equal the diagram's** objects and
   links in `t_diagramobjects` and `t_diagramlinks` (TC-06).
4. **A description names every element on its diagram.** For any diagram D whose description was
   written, each `t_object.Name` placed on D (a note or text item excepted, and a name with an
   ampersand matched in either form) appears in D's Notes. A summary that reads well and leaves one
   out fails this (TC-29).
5. **A description is never doubled and a person's words never vanish.** After any write, D's Notes
   hold exactly one opening marker line, and every sentence the person added or kept appears in them
   once (TC-32, TC-35, TC-36, TC-38).

These do not cover fidelity. Names being present does not show that tagged values, connectors or
diagrams survived an XMI export, and matching shape counts do not show that the shapes sit where
they did in EA. TC-12 checks the stereotype and one tagged value on the one element it restores;
nothing here compares a whole package round trip. Properties 4 and 5 look for names and counts. They
do not show that a description explains the diagram well, only that it leaves nothing out and loses
nothing; a person's text that is complete by name can still read badly.

## Headings not covered

- Import / Export — Sparx EA: the title and the "verified against a live repository" note; no behavior of its own.
- 6. EA Computer-Use — Latency: the one checkable claim, that exports need no screen driving, needs a tool name for computer use that the check grammar does not define; the rest is a pointer to the shared latency table, whose wait times a case cannot observe. See Findings.
- Reference files: a list of links.
- See also: a list of links.

## Findings

- SKILL.md "See also" sends the `export_xmi` defect to `ea-diagnostic` as an "escalation path for the `export_xmi` defect above", but section 4 says the defect was fixed in server 2.2.0; TC-11 requires the run not to follow that pointer.
- SKILL.md section 1 table says "Read the warning in §4 before relying on this for anything you can't afford to lose", but section 4 now holds a "Fixed" note and no warning; the pointer is stale.
- `references/generate-report.md` (and the SKILL.md section 5 text built on it) was measured on server 2.1.0; nothing records that the RTF-only limit, the template behavior or the empty-template hang still hold after 2.2.0.
- `references/generate-report.md` calls the empty-template hang "a per-call hang, not a reason to restart EA" on the strength of a `ping` answering, while `_shared/references/ea-ui-verification.md` says a hang is usually a blocking dialog and that nobody should conclude anything before looking at the screen; the two disagree on whether the diagnosis is already known. TC-18 asks for both (named cause plus a look at the screen).
- SKILL.md "Verify in EA's UI" tells the reader to reload and screenshot "after any diagram create or edit", which an export skill never performs; only its hang advice applies here.
- SKILL.md says the intro "Every claim below was exercised against that model ... see the verification table in each reference file"; `references/xmi-export-import.md` records the failed (now fixed) behavior, so nothing in this skill shows a verified working XMI export or import round trip.
- `import_xmi` is a model write that can overwrite elements whose identifiers already exist in the target, but SKILL.md section 4 says nothing about taking a baseline first, or about importing into a repository that already holds the package; TC-12 avoids the case by deleting the source package in setup.
- The `tools` check can name an operation but not its parameters, so `xmi_type` (TC-10) and a non-empty template (TC-16) are graded through the reply and the file, which an agent could misreport; the runner design needs a parameter check.
- TC-10 cannot test that the file is XMI 2.5.1: the version marker EA writes at the top of an XMI 2.5.1 file was not verified, so the check stops at "file exists" plus the reply.
- TC-18 and the SKILL.md latency section depend on a `computer-use` transcript tool name; none is defined in the template's `tools` grammar.
- TC-26 grades "picture off" through `not-called` render operations, and TC-38 cannot grade that the decided text went with the two fingerprints: a `tools` check can say a parameter must be present with a value, but not that one is absent or that a field holds the hash from an earlier result. The runner design needs both.
- The `setup` blocks of TC-23, TC-25, TC-28, TC-32 to TC-38 and TC-43 are checked by `tools/test_acceptance_setup.py` against a fake caller. They have not been run against a live server: the scratch diagrams of TC-23 and TC-25 place elements at negative tops (the form EA stores; a positive top reads as not found in the picture), and TC-25 assumes EA draws the 69-character name 120 wide by about 91 high, as in the E0 long-name fixture.
- TC-30 fails against server 3.6.x until the description generator stops writing the technology id ("WBA business applications") for the Westbrook model, whose stereotypes are stored under the profile name.
- TC-39 and TC-40 grade `diagram_changed` and `notes_changed` on the reply only. The race they describe cannot be set up in a single-ask run, so no check reads the server's refusal; a reply that sounds right passes. A known limit.

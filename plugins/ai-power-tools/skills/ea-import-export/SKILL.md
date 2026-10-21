---
name: ea-import-export
description: Get content into and out of a Sparx EA repository — XMI package export/import, diagram export to PNG/SVG/Visio, redrawing a diagram in another tool from its manifest, diagram descriptions (alt text, accessible diagram publishing), and RTF report generation via ea_repository and ea_diagram. Use when a package or diagram needs to leave EA (another repository, a document, a stakeholder without an EA license), a diagram needs a manifest or a description, or an XMI file needs to come back in.
---

# Import / Export — Sparx EA

*Verified against a live Westbrook Bank repository. Every claim below was exercised against
that model in this session — see the verification table in each reference file for the exact
call and result. Where EA's own behavior surprised the author, that is flagged as a defect, not
smoothed over.*

## 1. Which operation for which purpose

| Need | Operation | Notes |
|---|---|---|
| A picture of a diagram for a document, wiki, or chat | `ea_diagram(operation="get_diagram_png")` / `get_diagram_svg` | Returns bytes inline **and** writes to `path` if given. Fast, no dialog. |
| Same, but you don't need the bytes in the response | `ea_diagram(operation="export_diagram_image", params={..., "format": "png"})` | Identical output to `get_diagram_png` — pick whichever return shape your caller wants. |
| Hand a diagram to a stakeholder who has Visio but not EA, so they can move/relabel shapes | `ea_diagram(operation="export_diagram_to_visio")` | Preserves shape geometry and connectors as editable Visio objects — see §3. A one-off file only; for new work see §3b. |
| Redraw a diagram in another tool, or keep a copy in step with the model | `ea_diagram(operation="get_diagram_manifest")` / `get_package_manifest` | Every shape keeps the link to its element, with nesting and line routes — see §3b. |
| Give diagrams a description that a screen reader or an AI can read, and keep it current | `ea_diagram(operation="create_diagram_description")` / `update_diagram_description` / `audit_diagram_descriptions` | Words in the diagram's Notes, generated from the diagram — see §3c. |
| Move a package into another repository, or feed a tool that reads XMI | `ea_repository(operation="export_xmi")` / `import_xmi` | **Read the warning in §4 before relying on this for anything you can't afford to lose.** |
| A formatted document (headings, tagged values, prose) rather than a picture | `ea_repository(operation="generate_report")` | RTF only in this server version — see §5. |

Do **not** use the plain `ea_diagram(operation="get_diagram")` read call as an export path even
though it returns image bytes in its `preview_size_bytes`/`saved_path` fields — it is a
diagram-inspection call, and the preview it silently writes lands in the server's own cache
folder next to the model file, not wherever you intend the deliverable to go. Use
`get_diagram_png` / `get_diagram_svg` with an explicit `path` when the PNG or SVG itself is the
deliverable.

## 2. Diagram image export — `get_diagram_png` / `get_diagram_svg` / `export_diagram_image`

All three render faithfully: stereotype labels (`«WBABusinessApplication»`), package-qualified
element names, and box styling matched the live diagram exactly in verification.
`export_diagram_image` and `get_diagram_png` produced byte-identical output for the same diagram
and format.

```python
ea_diagram(operation="get_diagram_png", params={
    "diagram_id": 6,
    "path": "<scratch-dir>\\westbrook_app_landscape.png",
})
```

Pass `refresh=true` if the diagram's underlying rows may have changed out-of-band (direct SQL,
or another session) since it was last rendered — otherwise you may get a stale cached image.
SVG is the better choice when the picture will be scaled or embedded in another vector document;
PNG is fine for chat/Slack/wiki embedding. Neither operation offers a size/DPI parameter — the
image dimensions follow the diagram's own on-canvas size, so a very wide diagram produces a very
wide image rather than one that's reflowed to fit a page.

## 3. Exporting to Visio — `export_diagram_to_visio`

> **Superseded for new work.** The file keeps no link between a rectangle and its element, no
> nesting and no line routes, and draws a connector that is hidden in EA. It stays right for a quick
> editable file that nothing has to refresh later. To redraw a diagram in another tool, or to keep a
> copy in step with the model, read the manifest instead (§3b).

Verified against two diagrams — one with no connectors and one with 8 — and in both cases the
response's `shape_count` and `connector_count` matched the source diagram exactly, and the
`.vsdx` opened as a valid Office document (multi-part zip with `visio/document.xml`,
`visio/pages/page1.xml`). This is the right hand-off for a stakeholder who needs to keep working
with the diagram (move boxes, add annotations) but doesn't have an EA license.

```python
ea_diagram(operation="export_diagram_to_visio", params={
    "diagram_id": 6,
    "path": "<scratch-dir>\\westbrook_app_landscape.vsdx",
})
```

The response also returns `page_width_in` / `page_height_in` — check these before handing the
file over if the target audience will print it; EA's page size follows the diagram's own canvas,
not a standard paper size.

## 3b. Redrawing a diagram in another tool — `get_diagram_manifest` / `get_package_manifest`

*Sections 3b and 3c use operations that arrive with server 3.6.4. On an older server they are
unknown: say so and do not improvise. The image export (§2) is a fallback for a picture only.*

A manifest is one complete, read-only reading of a diagram, so another tool can redraw it and a copy
can be refreshed later instead of drawn again. Both operations are allowed in read-only mode and
change nothing.

```python
ea_diagram(operation="get_diagram_manifest", params={"diagram_id": 6})

ea_diagram(operation="get_package_manifest", params={"package_id": 5, "recursive": True})
```

(The ids are the Westbrook Bank copy's; read yours from `t_diagram` and `t_package`. A GUID works
too: `diagram_guid`, `package_guid`.)

**What the manifest holds**

- **A frame.** Every position is in one declared frame: diagram units (96 to the inch), origin at
  the top left, y increasing downward. EA stores a top edge as a negative number; the frame has
  already converted it. Raw EA rectangles are kept beside it.
- **Every shape with the element it stands for.** GUID, name, EA type, kind (element, note, text,
  boundary, port, package), qualified stereotype, tagged values, fill, line, font, picture, and the
  diagram it opens if it owns one. A copy drawn from it keeps the link to the element.
- **What is inside what, and how that is known.** Each shape names its parent and a `parent_basis`.
  `model` means the element's parent in the model is also on the diagram. `enclosed` means EA stores
  nothing about it and the parent is the smallest container whose drawn rectangle holds the shape's
  center, so it was read from the drawing. Say which kind you relied on when you report nesting.
- **The drawn size, when the picture is asked for.** EA grows a box to fit a name it cannot break,
  and only the picture shows it. With the picture, each shape also carries the box EA drew, given
  only where it differs from the stored one by more than two units, and whether the shape was found
  in the picture (`drawn_match`). A shape that is not found is reported as such, never guessed.
- **Lanes.** Each swimlane with its name, order and the elements in it.
- **Every line.** Type, stereotype, direction, the two elements and the two shapes it joins, style,
  color, hidden or not, labels, and the points of its route in the same frame. About one line in six
  is routed by EA when it draws and has no stored route; the manifest marks it `route_drawn_only`
  and leaves the routing to the tool that redraws. A note link is a line of its own kind.
- **A description.** The generated description stored in the diagram's Notes (the block between the
  two marker lines) when there is one, so a person's edits to it travel with it; otherwise the text
  §3c would write. A person's own notes with no marker lines do not count as a stored description.
  `description_source` says which (`notes` or `generated`). When the diagram's technology cannot be read, the description is null
  and `description_unavailable` says why; the rest of the read is unaffected.
- **`verify_diagram`'s keys, unchanged.** A checker that reads a verification reads a manifest. One
  value differs: `stereotype` on a shape is the qualified form (`WBA::WBABusinessApplication`),
  and the bare name is `concept`.

**What you need to know before you promise anything**

- **The picture is on by default for one diagram and off for a package.** A package read with no
  picture is database queries only and drives nothing in EA's window. Ask for the picture
  (`include_svg: true`) when drawn sizes or pictures are needed.
- **A diagram open in EA with unsaved changes is neither reloaded, rendered nor closed.** EA throws
  away unsaved changes on reload and on close. The manifest is read from the stored diagram, no
  picture is taken, no drawn sizes are given, and the result says the diagram is open with unsaved
  changes. If the person wants those changes included, ask them to save in EA and read again.
- **A diagram you did not have open is not left open.** The server closes only what it opened.
- **The package form describes each element once.** `elements` is keyed by GUID; each shape in a
  diagram then carries `element_guid` and its placement only. A package holds every diagram that
  belongs to it, including a diagram that an element in it owns. When you report a package read,
  say that an element placed on several diagrams is described once, in the shared `elements`
  section, and counts once.
- **Do not promise identical lines.** Lines EA routes itself come back without a route. Name them
  (`route_drawn_only`) and say the other tool routes them.
- **A shape the picture does not give a box for is not an error.** An actor's figure and a text item
  draw no rectangle of their own; they read `unmatched`.

`export_diagram_to_visio` (§3) is superseded for new work by this: keep it for a quick file, and
use the manifest when a shape must stay tied to its element. Visio itself is a separate product:
see its own skills.

## 3c. Accessible diagram publishing — diagram descriptions

Every diagram can carry a description: plain text that explains what the diagram shows, kept in
the diagram's Notes. It is how a screen reader, a document generator or an AI reading the model
understands a diagram without seeing the picture. Give every diagram one, whether or not it ever
leaves EA.

It is generated by template from the diagram, with no model judgment, so the same diagram always
gets the same words. It says what the diagram means (its kind in the language's business terms, its
groupings, every element, every relationship as a sentence, what its own notes say) and never how it
is drawn (no positions, colors, stereotype identifiers or drawing words). The first sentence is at
most 150 characters, so it can serve as alt text. It sits between two marker lines; text a person
wrote above or below them is never altered. Wording depends on the technology your diagram uses, so
read the output rather than expecting Westbrook's words. When you write or preview a description,
tell the person it is generated from the diagram, so the same diagram always gets the same words.

**Generate.** `dry_run` defaults to true: the first call previews and writes nothing.

```python
ea_diagram(operation="create_diagram_description", params={"diagram_id": 6})                     # preview
ea_diagram(operation="create_diagram_description", params={"diagram_id": 6, "dry_run": False})   # write
ea_diagram(operation="create_diagram_description", params={"package_id": 5, "recursive": True, "dry_run": False})
```

`create` writes only where Notes are empty. If Notes hold a person's text it returns
`notes_not_empty` with the text it would have written; use `update_diagram_description` with
`mode: "extend"` to add the description after the person's text, which is left exactly as it was. In
a package run, a diagram with a refusal is that diagram's own row and the others are still written.

**Keep current.** Run the audit first, then refresh what it flags.

```python
ea_diagram(operation="audit_diagram_descriptions", params={"package_id": 5})     # recursive by default
ea_diagram(operation="update_diagram_description", params={"package_id": 5, "recursive": True, "mode": "refresh"})   # preview
ea_diagram(operation="update_diagram_description", params={"package_id": 5, "recursive": True, "mode": "refresh", "dry_run": False})
```

The audit writes nothing. It gives each diagram one status: `empty`, `human_only`, `broken_markers`,
`technology_not_loaded`, `older_generator`, `language_changed`, `needs_decision`, `stale`, `edited`
or `current`, and on any text that is there it flags what the text leaves out (`incomplete`, with
`names_missing` and `relationships_missing`). Report the counts by status and the diagrams that need
work, not the raw rows.

`refresh` creates where Notes are empty, extends where there is only a person's text, and
regenerates where a block exists. It treats a person's edits like this:

| Diagram changed | Person edited the words | Outcome |
|---|---|---|
| No | No | `unchanged` |
| No | Yes | `edits_adopted`: the person's words are kept and recorded as the description |
| Yes | No, and the words are what the generator wrote | `written`: the new text |
| Yes | Yes, or the words are a person's earlier decision | `needs_decision`: nothing is written |

A bulk refresh writes what it can and lists the diagrams that wait for a decision. Take the person
through those one at a time.

**When a refresh returns `needs_decision`.** The diagram changed and the description holds a
person's words, so a machine must not choose. The result carries `current_text`,
`current_text_hash`, `generated_text` and `generated_hash`.

1. **Show the picture.** Read `get_diagram_manifest` for the diagram (the picture is on by default
   for one diagram). Save the `svg_text` it returns to an `.svg` file in the person's working or
   output folder and give the person the path to open; no browser tool is needed. The manifest
   reloads the diagram only when that is safe. If it reports `open_with_unsaved_changes`, there is no picture: tell the
   person to save the diagram in EA and run the refresh again. Do not render the picture with
   `get_diagram_svg`, which always reloads and closes the diagram.
2. **Show both texts** side by side in your reply: the current description and the newly generated
   one.
3. **Propose a text that carries the person's edits into the new one.** Start from the new
   generated text and keep the sentences the person wrote or changed. A sentence in the current
   text that the new text lacks is either the person's edit or a statement the diagram no longer
   supports (an application that was removed). Say which you kept and which you dropped, and ask
   rather than guess where it names something no longer on the diagram.
4. **Let the person decide.** They may take your text, change it, or keep the current one.
5. **Write their text** with the two fingerprints you were shown, as `mode: "refresh"`:

```python
ea_diagram(operation="update_diagram_description", params={
    "diagram_id": 6, "mode": "refresh", "dry_run": False,
    "text": "<the person's decided description, without marker lines>",
    "generated_hash": "<generated_hash from the result>",
    "expected_text_hash": "<current_text_hash from the result>",
})
```

   The text is for one diagram only. The block then records the person's text, so the next refresh
   keeps it until the diagram changes again. Confirm with the audit that the diagram reads `current`.

**What else can come back**

| Result | What to do |
|---|---|
| `diagram_changed` | The diagram changed again since you generated the text. Nothing was written. The result carries the new `generated_text` and `generated_hash`; show the person the new picture and text and propose again. |
| `notes_changed` | Someone edited the description in EA while the person was deciding. Nothing was written. The result carries the new `current_text` and `current_text_hash`; show the person what is there now. |
| `open_with_unsaved_changes` | The diagram is open in EA with unsaved changes. Nothing was written, because EA would discard the person's edits on reload and their next save would undo the write. Ask the person to save in EA and run it again. A package run carries on with the others. |
| `technology_not_loaded` | The diagram's technology cannot be read here, so business names are unavailable. Nothing was written; the server will not replace good text with base EA terms. Ask the person to enable or import the technology in EA (**Specialize > Technologies > Manage Technology**) and run it again. |
| `broken_markers` | A marker line has lost its pair or cannot be read. Nothing was written and no second description is added. Tell the person to remove or repair the stray marker line in EA's Notes window, then run it again. Do not edit the Notes around it. |

**Read-only mode.** `create_diagram_description` and `update_diagram_description` are refused,
previews included. `audit_diagram_descriptions` and the manifests are allowed; the manifest's
`description` previews the generated text for a diagram that has none. Say so, and do not look for
another way to write Notes.

**Checking a write.** A write changes the diagram's Notes and its modified date, nothing else. Read
the Notes back, or run the audit, and confirm the diagram now reads `current` and the text names
the elements on the diagram.

## 4. XMI package export/import — `export_xmi` / `import_xmi`

> **Fixed in server 2.2.0.** This path was genuinely broken and this skill told you not to trust
> it. `export_xmi` wrote a ~350-byte **XPDL 2.2** stub containing none of the package's elements
> while reporting `"xmi_type": "XMI 2.1"` and `"status": "exported"`, and re-importing it created
> zero objects while reporting `"status": "imported"`. The cause was that `xmiType` is an ordinal
> from Sparx's `EnumXMIType` and the mapping table had been written as though the ordinal were the
> XMI version number, so every entry was wrong.
>
> **What the server does now:** `export_xmi` reads the file back before reporting success and
> confirms both that it is XMI and that the package's elements appear in it. A wrong-format or
> empty result returns `xmi_export_wrong_format` or `xmi_export_empty` instead of a false success,
> and the response carries `elements_in_package` / `elements_in_export` so you can see the export
> is real. `xmi_type` accepts `"XMI 1.0"`, `"XMI 1.1"`, `"XMI 1.2"`, `"XMI 2.1"` (default),
> `"XMI 2.4.1"` and `"XMI 2.5.1"`.
>
> **Still worth doing:** check `elements_in_export` against `elements_in_package` rather than
> reading `status` alone. The server checks it for you now, but the habit is what caught this.

The original investigation -- the file contents observed and the SQL that confirmed zero import --
is kept in [`references/xmi-export-import.md`](references/xmi-export-import.md) as the record of a
defect that reported success, which is worth reading for the pattern even though the specific bug
is gone.

## 5. `generate_report` — RTF document generation

```python
ea_repository(operation="generate_report", params={
    "template": "Simple",
    "package_id": 21,
    "output_path": "<scratch-dir>\\account_origination.rtf",
})
```

Three things verified in this session that are easy to get wrong:

1. **`output_path` must end in `.rtf`.** The same call with a `.html` path failed with
   `{"error": "report_failed", "detail": "RunReport returned but output file does not exist"}`
   regardless of the `template` value. This server version generates RTF only through this
   operation.
2. **`template` is not validated against anything in this repository.** This model has no
   custom report templates defined (`SELECT * FROM t_rtfreport` returns zero rows — check this
   first via `ea_analyze(operation="execute_sql", ...)` to see what's actually available). With
   no custom template to find, three different nonsense strings and the plausible-sounding
   `"Simple"` all produced the identical byte-for-byte 20,334-byte default document. A
   `"generated"` status is **not** confirmation your named template was used — open the output
   and check its heading.
3. **Never pass an empty string for `template`.** It reproducibly hung the call (once reported
   as a closed connection, once as a timeout) rather than failing fast. EA itself stayed
   responsive throughout — confirmed with `ping()` and `get_repository_info` immediately after —
   so this is a per-call hang, not a reason to restart EA.

The generated RTF embeds each element's Created/Modified `Author` field verbatim from the
model — that is the modeler's own EA/Windows username, not a Westbrook Bank tagged value. Check
report content for anything identifying before sharing a generated report outside the team.

Full discovery method for real templates once a project has them, and the complete test matrix,
are in [`references/generate-report.md`](references/generate-report.md).

## 5b. Reading the results from a Claude Cowork or cloud session

Exports and generated reports are files. If the user wants a Claude Cowork or other cloud session
to read them, tell them to export into one `<output-folder>` and connect that folder, not the
folder that holds the model file. Such a session can read the XMI, images and reports, but it
cannot change the model or import anything back, because the server is not available in those
sessions today. Review a generated report for identifying details before connecting the folder
(§5).

## 6. EA Computer-Use — Latency

Every operation above is MCP-only and does not require driving the EA desktop UI. If you do open
the exported Visio file or generated RTF in their native apps to eyeball them, or open the
diagram in EA to compare against the export, use the standard wait-before-screenshot discipline:
[`../_shared/references/latency.md`](../_shared/references/latency.md).

## Reference files

- [`references/xmi-export-import.md`](references/xmi-export-import.md) — full `export_xmi`/`import_xmi` repro, file contents, and the SQL verification of the failed round trip
- [`references/generate-report.md`](references/generate-report.md) — template discovery, the RTF-only extension requirement, and the empty-template hang

## See also

- `ea-modeling` — for building the content you're about to export in the first place
- `ea-stakeholder-reporting` — reading a diagram's description to someone who has no EA
- `ea-diagnostic` — escalation path for the `export_xmi` defect above, or any other repeated failure
- `_shared/references/westbrook-example.md` — canonical stereotypes/tags used in every example here

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

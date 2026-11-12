# Source model mechanics

Back to [SKILL.md](../SKILL.md). Detail that the phases point to: building a source model by
script, copying a package and checking the copy, archiving into the model, renaming a tag,
exporting a profile with an explicit path, and the older pre-17.1 build route. Westbrook Bank is an
illustration; use your own technology, stereotypes and tags. Measured on EA 17.1 build 1716 unless
a line says otherwise.

## Building a source model by script

A source model built through COM, not by hand, needs these six things, each of which fails
without an error.

1. **A quick link connector already has a tag.** Giving a connector the stereotype
   `stereotyped relationship` makes EA add an empty tag named `stereotype`. Set that tag's value to
   `<Tech>::<Relationship>`. Do not add a second tag: the empty first one stays in force, the built
   rule comes out as `<Tech>::` with no line name, the quick linker shows an empty menu, and
   nothing reports an error. Read the connector's tags back and check there is exactly one.
2. **`TaggedValues.AddNew(name, x)` does not set the value.** Its second argument is not the
   value. Set `.Value`, then call `.Update()`.
3. **A closed list needs an Enumeration class in the profile package**, with the tag attribute's
   `ClassifierID` pointing at it and one attribute per value. The built file then carries
   `type="enumeration"` with `values=` on the tag, and that travels with the imported technology.
   Reference data in `t_propertytypes` (Phase 3) does not travel to another model with an imported
   technology.
4. **Shape scripts have a stored form.** A stereotype's `_image` attribute holds, as its default,
   `<Image type="EAShapeScript 1.0" ...>` containing base64 of a zip file whose one entry,
   `str.dat`, is the script text in UTF-16 (little endian). Build the value with that recipe rather
   than typing it. A custom technology usually needs shape scripts. A connector's script needs a
   `middlebottomlabel` block to replace the stored-name label EA draws otherwise.
5. **`ImportPackageAsMDGTechnology` carries the package's version.** Save Package as MDG
   Technology writes an empty `version` (Phase 5), but the copy that Import stores has the version
   from `Package.Version`. It can be read from the `t_document` row headless (`DocType='TECHNOLOGY'`,
   `DocName` = the technology id), so a file can come from EA with no menu step. The stored text
   declares UTF-16; if you write it out as UTF-8, change the declaration to match.
6. **`&` in a toolbox label** is read as a shortcut marker and the label shows an underscore. Write
   "and".

## Copying a package

`ea_model(operation="duplicate_package", ...)` copies a package subtree with new GUIDs
(the API form of Paste as New).

- **Diagrams are copied** (their objects and links) on server 2.3.0 and later. A skill note that
  says otherwise is out of date. Composite flags on copied diagrams are a separate matter; check them.
- **Data a copy can lose**, found in three acceptance runs on 3.6.4: Quick Linker connector tag
  values, attribute-to-enumeration links (`ClassifierID` is left unset on purpose), and literal
  order. Until the server copies these, a damaged profile package looks complete in the Browser and
  fails later.
- **Compare source and copy before using the copy**, and report the result:
  1. Quick Linker connector tags: for each `stereotyped relationship` connector, the `stereotype`
     tag value in the copy equals the source's (`t_connectortag`).
  2. Attribute classifier links: each tag attribute that points at an Enumeration in the source
     points at the copy's Enumeration (`t_attribute.Classifier`).
  3. Literal order: each Enumeration's attributes have the same `Pos` order.
  4. Counts: elements, attributes, connectors, diagrams and diagram objects.
- **If any comparison fails**, repair the copy from the source, or make the copy with EA's own
  Paste as New in the Browser, which was faithful in the same runs, and compare again.

## Archiving into the model (Phase 0.4)

Phase 0.4 keeps the archive in the model, in a package named `Files`, as well as on disk, so the
baseline travels with the repository.

1. Create the `Files` package under the technology's root if it does not exist
   (`ea_model(operation="create_package", ...)`).
2. For each artifact (each profile export, the `.mts`, the deployed MDG file), create one element of
   type `Artifact` in `Files`, named for the file and the version it came from (for example
   `WBA profile 1.1.1`). Put the file's text in the element's notes, and keep the disk copy as well.
3. Read back the element's notes length and compare it with the file's length. If the notes do not
   take the whole file, attach the file to the element (an element's Files collection stores a
   path, not the content) and say so: a path is not an archive, so keep the disk copy somewhere that
   survives.
4. State in the reply that tagged value types are repository-wide, so once a new type is added any
   export from the old profile packages is no longer the old version, and that the old version
   cannot be recovered afterwards without this archive.

Not yet verified live: that the notes field takes a whole MDG file at full size.

## Renaming a tag: two steps

A tag's values on elements are stored under its name in `t_objectproperties`. Renaming the tag on
the stereotypes leaves those values behind under the old name.

1. **Report first.** For each stereotype that carries the tag, count the rows:
   `SELECT COUNT(*) AS n FROM t_objectproperties WHERE Property = '<old name>'`. Say how many values
   would be orphaned and that nothing has been renamed. Then ask.
2. **Rename only after the person agrees**, on every stereotype, and offer to migrate the values
   (copy each value to the new name, then check no row keeps the old name). Do it before a
   production load, not after.

## Exporting a profile package with `SavePackageAsUMLProfile`

When the COM call is used directly, pass the output path as the second argument. Without it EA
writes to the path stored in the package's profile options, which can be another person's machine.
The version in the written file is not updated by the call, so open the file and set the
`<Documentation version="...">` value afterwards. The `publish_package_as_profile` operation takes
the path and the version as parameters and stamps the version for you; prefer it.

## Building with the MTS wizard (EA before 17.1)

Use this only when the EA in front of you predates 17.1 (and see the deploy skill for Build 1704,
where the 17.1 commands show but are untested).

`Specialize ▸ Publish Technology ▸ Generate MDG Technology` needs an `.mts` file and the profile
exports from Phase 5, step 1. The `.mts` cannot be hand-written:
`Repository.GenerateMDGTechnology(mtsFilename)` is callable and validates its argument, but the
schema is not published (Sparx documents the root element, the hand-edited `<ModelValidation>` and
`<ModelTemplates>` sections and the wizard's section list, not the element names the wizard writes
per section or how the tagged-value-type inclusion list is stored on disk). A reconstructed file is
rejected for reasons nothing explains. Run the wizard once to emit a real `.mts`, keep it under
version control, and edit that file from then on.

Match the Contents checkboxes to the shape of the current deployed file. Parse the deployed file and
tick to match:

```
<MDG.Technology>
  <Documentation/>      -> (header fields)
  <UMLProfiles>         -> Profiles
  <TaggedValueTypes>    -> Tagged Value Types
  <DiagramProfile>      -> Diagram Types
  <UIToolboxes>         -> Toolboxes
```

**Filenames.** Use stable unversioned names in the build folder: the `.mts` references the
profile XMLs by filename, so versioned names force a rename and an `.mts` rebuild every release, and
a stale `.mts` silently ships the previous version's content. Add the version only when archiving.

## Baseline size

A package baseline covers the whole subtree. Confirm it rather than assume: a package holding no
elements directly still produces a large compressed payload if its children are captured.

```sql
SELECT DocID, DocName, LENGTH(BinContent) AS bytes
FROM t_document WHERE DocType = 'Baseline'
```

**Use `LENGTH`, never `OCTET_LENGTH`.** A `.qea` repository is SQLite, which has no `OCTET_LENGTH`
function. EA answers an unrunnable query with a modal dialog, which blocks the calling tool until
someone clicks OK at the machine; it does not return an error you can catch.

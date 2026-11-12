# Creating and mutating elements

Full detail behind the "Mutating elements and tagged values" section of
`../SKILL.md`. Every mutation shown here was run against a scratch package created
under the root `Model` package in a live EA session with the Westbrook Bank demo
model open, then deleted at the end of the verification pass — no existing Westbrook
content was changed. IDs below (e.g. `Object_ID = 9383`) are from that scratch
session and no longer exist; treat them as illustrative, not as guaranteed
identifiers you can reuse.

## Create a package and an element

```python
model = repo.Models.GetAt(0)          # root "Model" package

new_pkg = model.Packages.AddNew("Scratch", "")
new_pkg.Update()
model.Packages.Refresh()

elem = new_pkg.Elements.AddNew("Example Business Application", "Component")
elem.Stereotype = "WBABusinessApplication"
elem.Update()
new_pkg.Elements.Refresh()
```

Verified live: created a package (`PackageID` assigned, e.g. `3327`) and an element
inside it with the `WBABusinessApplication` stereotype (metaclass `Component`, per
`_shared/references/westbrook-example.md` section 2). Read back with `sql()`
immediately after:

```python
>>> sql(f"SELECT Object_ID, Name, Stereotype FROM t_object WHERE Object_ID = {elem.ElementID}")
[{'Object_ID': '9383', 'Name': 'Example Business Application', 'Stereotype': 'WBABusinessApplication'}]
```

That example sets only the bare stereotype name. Whether EA also writes the technology binding in
`t_xref` for an element created this way was not checked for this snippet, and elements created by
automation came out unlinked in the models tested (next section). So do not tell the person the
element is tied to its technology until you have read the binding:

```python
>>> sql(f"SELECT Description FROM t_xref WHERE Client = '{elem.ElementGUID}' AND Name = 'Stereotypes'")
# a row with FQName=<profile>::WBABusinessApplication means linked; GUID= with no FQName means a label only
```

## Setting a profile stereotype can silently fail: read it back

Setting `StereotypeEx = "<Profile>::<Stereotype>"` (for example `WBA::WBADataAsset`) on an Object
element returned success but left `Stereotype` empty, every time, in several models, with the
technology loaded and not loaded, and after a restart. Tags survived. It was noticed only by
reading back. A profile stereotype applied to a Class linked and brought the profile's full tag
set, while on an Object it was silently dropped.

**After any `StereotypeEx` write, read `Stereotype` and `FQStereotype` back**, and treat an
empty `Stereotype` as a failed write:

```python
elem.StereotypeEx = "WBA::WBADataAsset"
elem.Update()
elem = repo.GetElementByGuid(elem.ElementGUID)      # re-fetch, do not reuse the held object
print(elem.Stereotype, elem.FQStereotype)           # expect WBADataAsset  WBA::WBADataAsset
```

Telling a linked element from an unlinked one was reliable in both models tested:

| | `FQStereotype` | `MetaType` | `t_xref` (Stereotypes) |
|---|---|---|---|
| Linked | `<profile>::<stereotype>` | the stereotype name | `FQName=` |
| Unlinked | the bare name | `Object` | `GUID=` pointing at a `t_stereotypes` row with no TechID |

Elements created by automation came out unlinked even with the technology loaded. In one merge,
writing the `t_xref` row in the `FQName` form through `Repository.Execute` made them linked. That
repair is unverified beyond that one case: try it on a copy and read back before relying on it.
The tag count on a linked element follows the profile, so unlinked elements can carry fewer tags.

## Re-fetch before you update

A held element object goes stale when another process writes the model. `Update()` rewrites the
whole row, so a stale object silently undoes the outside change. After any outside write, fetch the
object again (`GetElementByGuid` / `GetElementByID`) and never `Update()` one you held from before.
See [`instances-and-sessions.md`](instances-and-sessions.md) for the one-session-per-model rule.

## The AddNew duplicate-row trap

When an element is created with a stereotype, EA auto-populates a placeholder row in
`t_objectproperties` for every tag that stereotype declares — with `Value = NULL` —
before you touch `TaggedValues` at all. Calling `TaggedValues.AddNew(name, value)`
does **not** find and fill that placeholder; it inserts a second row with the same
`Property` name. Verified live:

```python
tv = elem.TaggedValues
new_tag = tv.AddNew("criticality", "Standard")
new_tag.Update()
tv.Refresh()
```

Read-back after this call:

```python
>>> sql(f"SELECT PropertyID, Property, Value FROM t_objectproperties WHERE Object_ID = {elem.ElementID} AND Property = 'criticality'")
[{'PropertyID': '10490', 'Property': 'criticality', 'Value': None},
 {'PropertyID': '10496', 'Property': 'criticality', 'Value': 'Standard'}]
```

Two rows for one tag — the original `NULL` placeholder is still there. Anything
reading "the" value of `criticality` by `Property` name alone (rather than by
`PropertyID`) now gets ambiguous results depending on row order.

## The correct pattern: update the existing row

Iterate the element's existing `TaggedValues` and update the row that's already
there, instead of calling `AddNew`:

```python
for tag in elem.TaggedValues:
    if tag.Name == "businessOwner":
        tag.Value = "Payments Engineering"
        tag.Update()
        break
```

Verified live:

```python
>>> sql(f"SELECT Property, Value FROM t_objectproperties WHERE Object_ID = {elem.ElementID} AND Property = 'businessOwner'")
[{'Property': 'businessOwner', 'Value': 'Payments Engineering'}]
```

One row, correctly updated — no duplicate, because the loop found and updated the
placeholder row that already existed instead of adding a new one.

Only fall back to `AddNew` for a tag that genuinely has no existing row (for example,
a tag added by a newer MDG revision to elements created under an older one) — check
first with a `sql()` read.

## Bulk update via SQL DML

For updates across many elements at once, `repo.Execute()` is faster than iterating
`TaggedValues` per element. It always returns `None` on both success and failure
(verified — see `connecting-and-queries.md`), so read back to confirm:

```python
repo.Execute(f"""
    UPDATE t_objectproperties
    SET Value = 'Platform Engineering'
    WHERE Object_ID = {elem.ElementID} AND Property = 'technicalOwner'
""")

>>> sql(f"SELECT Value FROM t_objectproperties WHERE Object_ID = {elem.ElementID} AND Property = 'technicalOwner'")
[{'Value': 'Platform Engineering'}]
```

Verified live exactly as shown.

## Deleting scratch content and confirming the delete

```python
elems = pkg.Elements
for i in reversed(range(elems.Count)):
    elems.Delete(i)
elems.Refresh()

parent_pkgs = model.Packages
for i in range(parent_pkgs.Count):
    if parent_pkgs.GetAt(i).PackageGUID == pkg.PackageGUID:
        parent_pkgs.Delete(i)
        break
parent_pkgs.Refresh()
repo.RefreshModelView(0)
```

Always confirm a delete with a fresh `sql()` read, not the absence of an exception —
collection `Delete()` calls don't return a status either:

```python
>>> sql(f"SELECT Package_ID FROM t_package WHERE Package_ID = {pkg_id}")
[]
>>> sql(f"SELECT Object_ID FROM t_object WHERE Object_ID IN ({elem_id_1}, {elem_id_2})")
[]
>>> sql("SELECT Object_ID FROM t_object WHERE Name LIKE 'Example Business Application%'")
[]
```

Verified live: after deleting the scratch package and its two elements, all three
read-back queries returned `[]` — the package, both elements, and their tagged-value
rows (`t_objectproperties`) were gone, and no by-name search found any leftover
scratch content.

## Keeping GUIDs when you re-create elements (measured on a plain `.qea`, with risks)

`Element.ElementGUID` and `Connector.ConnectorGUID` are read-only. An element re-created during a
merge, or restored after a delete, gets a new GUID, and so do its tag rows
(`t_objectproperties.ea_guid`). Later GUID-based diffs then do not pair them.

In one merge on a `.qea`, `Repository.Execute("UPDATE t_object | t_connector | t_objectproperties
SET ea_guid = ...")` worked, and a verification diff then matched exactly. The order that was used:

1. create, then `Update()`;
2. `UPDATE ... SET ea_guid = ...` through `Repository.Execute`;
3. re-fetch the object (a held COM object is stale after the SQL write);
4. then set the stereotype and cross-reference.

Set the stereotype after the GUID write, not before. Measured once on EA 17.1 build 1716 with a
plain `.qea`: the element, connector and tag-row GUIDs changed, were found by their new GUIDs, and
survived closing and reopening the model. The stereotype row in `t_xref` is keyed by the element's
GUID and stayed on the old one. Calling `Update()` on the object you held from before then added a
second stereotype row under the new GUID, so the table kept both. Any other table that keys on the
GUID (diagram links, for example) needs the same update; only `t_xref` was checked.

**Unverified on other repository types. Do not recommend this as a general method.** It bypasses
security locks, auditing, version-control flags and Pro Cloud Server SQL policy, and DBMS quoting
differs. None of that was tested: not with security enabled, not under version control, not on SQL
Server or a Pro Cloud Server repository. If you use it, do it on a copy and read every changed row back.

For diffs, pair tagged values by (owner GUID, `Property`), not by tag-row GUID: EA's Synchronize
Tagged Values regenerates tag-row GUIDs.

## A file stored on an Artifact

Measured on one cloud model (EA 17.0). A file stored on an Artifact is:

- one `t_document` row: `DocType = 'ExtDoc'`, `DocID` = the artifact's `ElementID`'s GUID
  (`t_object.ea_guid`), `BinContent` = a zip that holds one entry, `str.dat`; and
- on the artifact's `t_object` row, `Style = 'ExtDoc=1;'` and `NType = 32`.

Without the `Style` marker EA will not open the file when you double-click the artifact. After
storing, read the bytes back (`BinContent` length, and the zip's `str.dat` against your source file)
instead of trusting that the `Execute` call worked. Prefer EA's own attach-file route where one
exists; writing these rows directly is documented here from a single measurement, not a tested
procedure.

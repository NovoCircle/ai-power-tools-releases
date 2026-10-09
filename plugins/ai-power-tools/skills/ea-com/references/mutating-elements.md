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

# The diff, the noise filter, and the decisions

Reference for steps 6 and 7 of `ea-branch-and-merge`. The measurements behind it come from two
runs of the workflow on a Westbrook Bank `.qea`; both were small, one package each.

## What the diff reads

Three `.qea` files, opened read only as SQLite (no EA, no lock taken beyond SQLite's own). The result
carries the SHA-256 of each file as read. The diff stops if a file changed while it was being read.

Scope: the package with the GUID you pass, and every package beneath it. Elements, attributes,
operations and tagged values in those packages; connectors with either end in them (a connector to an
element outside the package is included); diagrams in them and every element on those diagrams,
including elements from outside the package. Elements outside the package are not diffed.

| Table | Paired by |
|---|---|
| `t_package`, `t_object`, `t_attribute`, `t_operation`, `t_connector`, `t_diagram` | the row's GUID |
| `t_objectproperties` (tagged values) | the owner element's GUID and the tag name (`Property`); where the owner has more than one row of that name, the tag row's own GUID |
| `t_diagramobjects` | the diagram's GUID and the element's GUID |
| `t_xref`, rows named `Stereotypes` (the profile link) | the GUID of the item the link belongs to |

Integer ids differ from file to file after an import. The diff never compares them: every foreign key
is turned into a GUID first, and so is a package element's `PDATA1`, which holds its package's id.

Tagged values are paired by owner and name because EA regenerates the GUID of a tag row when it
synchronizes tagged values. A tag row's own GUID is not compared.

**Duplicate tag rows.** EA lets an element hold two rows of one tag name (a filled one and an empty one
is common), and an import writes them in another order. Pairing them by position can match a filled row
with an empty one, so a merge would blank production's value. The diff pairs such rows by their own
GUID when every file holds the same GUIDs for them, and says so in `warnings`. When it cannot (a GUID one
file holds and another does not), it compares each file's rows as one set: the row id is
`t_objectproperties:{owner GUID}|<tag name>`, the row shows the set's values, and any change the branch
made to the set is a `conflict` (kind `duplicate_tag_rows_changed`). Only `"production"` can decide it;
to merge it, remove the duplicate rows in EA and run the diff again.

**Stereotype links** compare by the stereotypes they name: each one's profile-qualified name (`FQName`),
or its bare name when it has none. The `GUID=` part is left out, because EA writes it on import but not
when a stereotype is set through the API.

Not compared, so not detected and not merged: element constraints, scenarios, requirements, files,
hyperlinks, connector tagged values, attributes' and operations' own tagged values, `t_xref` rows other
than stereotype links, diagram links, and any table not listed above.

## Statuses and the modify/delete rule

A row exists in each of base, branch and production, or it does not.

| Base | Branch | Production | Status |
|---|---|---|---|
| no | yes | no | `added_branch` |
| no | no | yes | `added_production` |
| no | yes | yes, same | `added_same_on_both` |
| no | yes | yes, different | `conflict` (kind `added_on_both_differently`) |
| yes | same | same | `unchanged` |
| yes | changed | same | `changed_branch` |
| yes | same | changed | `changed_production` |
| yes | changed | changed, same result | `changed_same_on_both` |
| yes | changed | changed, other fields | `changed_both_different_columns` |
| yes | changed | changed, same field differently | `conflict` (kind `both_changed`) |
| yes | missing | same | `deleted_branch` |
| yes | same | missing | `deleted_production` |
| yes | missing | missing | `deleted_both` |
| yes | missing | **changed** | `modify_delete_conflict` (kind `deleted_on_branch_changed_on_production`) |
| yes | **changed** | missing | `modify_delete_conflict` (kind `deleted_on_production_changed_on_branch`) |
| yes | missing, and the branch file cannot hold it | yes | `outside_branch` (see below) |

**Rows outside the branch.** The XMI of a package does not carry a connector whose other end is outside
the package, nor the placement of an outside element on the package's diagrams. In the branch those rows
are missing although nobody deleted them. When the outside element is not in the branch file at all, the
row is `outside_branch` (kind `connector_end_outside_package` or `placement_of_element_outside_package`),
and so is a row beneath it, such as the connector's stereotype link (kind
`beneath_a_row_outside_the_branch`). They are listed apart, under `outside_branch`, and never planned:
deciding one `"branch"` is refused, `"production"` changes nothing. If the branch was made as a copy of
the whole model, so that it holds the outside element, a missing connector is a real `deleted_branch`.
When the branch deletes an element inside the package, its connectors to outside elements go with it in
EA; the plan says so in its `warnings`.

**The modify/delete rule.** When a row is missing on one side, compare the other side with the base,
field by field. If anything differs, it is a conflict. A diff that reports only "missing on one side"
hides this case, and a merge built from that diff silently discards the other side's edit. A first
version of this workflow did exactly that and missed both such conflicts in its test set.

**Deleting a parent.** A row deleted on one side becomes a `modify_delete_conflict` (kind
`deleted_on_branch_children_changed_on_production` or `deleted_on_production_children_changed_on_branch`)
when the other side changed or added something beneath it: a tagged value, an attribute, a connector, a
diagram entry. The result's `related_rows` lists them. Deleting an element deletes what is beneath it,
so a person must see this.

NULL and the empty string compare as equal. Everything else compares as text, so a change from `0` to
an empty value is shown.

## The noise filter

Differences that the XMI import adds to the branch, and that EA rewrites on its own. They are not edits,
so the diff ignores them, and a merge must not copy them:

| Ignored | Why |
|---|---|
| diagram `StyleEx` | the import rewrites the full diagram style |
| the `DUID=` mark inside every diagram object's `ObjectStyle` | EA adds an id mark to each |
| `t_diagramlinks` rows (not read) | the import adds a row for each existing connector |
| the `t_genopt` scenario row (not read) | the import leaves it out |
| the parent of the package you took out | the import puts it under a different parent |
| `t_object.TPos` | NULL becomes 0 on import |
| `ModifiedDate`, `CreatedDate`, `LastLoadDate`, `LastSaveDate` | EA rewrites them on every save, so a merge could never show an exact residual |
| the `CRC=` mark inside `t_package.PackageFlags` | a checksum EA keeps for the package; the other flags are compared |

**Import forms.** Some columns carry a real value and also change on import. For those the diff does
not ignore the column. It takes a side's value as base's only when the pair is exactly the form the
import writes, so a real edit to the same column still shows:

| Form (`import_forms` name) | Columns | Taken as base's value when |
|---|---|---|
| `connector_style_owned` | connector `SourceStyle`, `DestStyle` | the side's value is base's with `Owned=0;` appended |
| `connector_zero_as_null` | connector `IsSignal`, `IsSpec`, `IsStimulus`, `Target2`, `IsLeaf`, `IsRoot`, `VirtualInheritance` | one value is `0` and the other empty |
| `connector_drawn_label` | connector `Top_Mid_Label`, `Btm_Mid_Label` | base is empty and the side holds the connector's name or its stereotype in guillemets (`«Uses»`) |
| `diagram_default_pdata`, `diagram_default_swimlanes` | diagram `PDATA`, `Swimlanes` | base is empty and the side holds EA's default text |
| `placement_zorder_from_unset` | diagram object `Sequence` | base holds EA's unset z-order (999999) and the side a number |

The last form has a limit: a person who changed the z-order of an element whose base z-order was unset
cannot be told apart from the import. A z-order change from any set value still shows.

The list is declared (`DEFAULT_NOISE`), and a call can pass its own (`noise`, with `import_forms` naming
the forms to use). The result's `noise_ignored` lists every column left out or taken as base's value,
with the reason and, for each import form, how many values it took on each side. If a column still
differs on every row of a table, look at `column_change_counts`: that column is noise the list does not
know yet. Tell the person, and pass a filter that names it. Do not decide on your own that a column does
not matter.

## The result

`summary` counts rows per status. `rows` lists every row that is not `unchanged` or `outside_branch`: its
`id` (`<table>:<key>`), a label, its status, and the columns that changed with each side's value. For an
added or deleted row the whole row is shown. `outside_branch` lists the rows outside the branch, whole.
`warnings` lists anything odd (a foreign key to a row that is not in the file, two rows that pair as
one, duplicate tag rows). `noise_ignored` says what the diff left out and why. `file_sha256` holds each
file's hash.

Row ids: `t_object:{GUID}`, `t_objectproperties:{owner GUID}|<tag name>` (for one of several rows of one
name, `t_objectproperties:{owner GUID}|<tag name>|{tag row GUID}`),
`t_diagramobjects:{diagram GUID}|{element GUID}`, `t_xref:{GUID of the item}`.

## Decisions

A decision is a mapping from row id to a choice:

```json
{
  "t_object:{GUID-1}": "production",
  "t_objectproperties:{GUID-2}|dataClassification": "branch",
  "t_object:{GUID-3}": {"set": {"Note": "text the person wrote"}}
}
```

- `"branch"` takes the branch's side. `"production"` leaves production as it is.
- `{"set": {...}}` writes the person's own value into the named columns of a field conflict. Everything
  else the branch changed on that row is still applied.
- Every `conflict` and `modify_delete_conflict` row needs a decision. There is no default.
- A row only the branch changed is applied unless it is decided `"production"`.
- A row only production changed, and a row both sides changed the same way, take no decision.
- A restore carries everything that was beneath the restored row.
- A keep carries everything beneath the kept row: deciding a `modify_delete_conflict` the branch deleted
  `"production"` plans no delete for its tagged values, stereotype link, placements or connectors. A
  connector whose other end the merge deletes still goes.
- Decisions must agree with each other. Deleting a row while another decision keeps something beneath it
  is refused, keeping a row while another decision deletes something beneath it is refused, and so is
  creating a row under a parent that will not exist. The message names both rows.
- A plan that would empty a tagged value production holds is refused unless that row is decided
  `"branch"`.
- A row `outside_branch` takes `"production"` or nothing; `"branch"` is refused.

## Plan order

Creates (packages, elements, attributes, operations and tagged values, connectors and diagrams, diagram
entries, stereotype links, parents first), then updates, then deletes (children first).

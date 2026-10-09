# The schema

What the build produces, table kind by table kind. The shape is the same on every path - direct
access, reporting database and Parquet - and is written into the definition JSON that
`ea-power-bi` reads, so nothing downstream re-derives it. Examples use Westbrook Bank's `WBA`
technology as an illustration; a customer's tables are named by their own technology.

---

## 1. Entity tables

One per element stereotype the inclusion choice admits.

**Name.** The stereotype's alias; with no alias, the stereotype name; where two stereotypes share
an alias, the alias plus the stereotype name. Exactly as the technology writes it - no prefix
stripping, no case change, spaces kept: `Business Application`.

**Elements outside the technology** that the inclusion choice admits get one table per observed
stereotype (or per base metaclass where an element has none), named with the suffix
` (not in MDG)`: `VendorApplication (not in MDG)`.

**Columns**

| Column | Type | Holds |
|---|---|---|
| `ea_guid` | text | EA's stable identifier for the element. The key the other tables join on |
| `name` | text | The element's name |
| `metaclass` | text | The base type (`Component`, `Class`, `Requirement`, ...) |
| `package_path` | text | The element's package, as a path from the root. On every entity table, including those with no tags |
| one per declared tag | typed | The tag's value, typed from the tag's declared type (§5) |

An element in two entity tables has one row in each. Rows for the same element are identical in
the columns they share.

---

## 2. `Con_` tables

One per **allowed combination** (source stereotype, connector stereotype, target stereotype) from
the technology's relationship constraints, so the tables match the metamodel diagram one for one.

**Name.** `Con_<source table> <connector stereotype> <target table>`, for example `Con_Business
Application Uses System of Record`. A combination outside the technology that the inclusion choice
admits is marked ` (not in MDG)`.

**Columns**

| Column | Type | Holds |
|---|---|---|
| `connector_guid` | text | EA's identifier for the connector |
| `connector_id` | integer | EA's numeric id |
| `name` | text | The connector's name |
| `source_guid`, `target_guid` | text | The `ea_guid` of the entity rows at each end |
| `direction` | text | EA's direction setting |
| `base_type` | text | The base connector type (`Association`, `Dependency`, ...) |
| one per connector tag | text | The tag's value |

A connector joins its combination by its **own profile binding** (the `FQName` in its stereotype
record) plus membership of its two ends. A combination whose source and target are the same entity
type is a self-join: both `source_guid` and `target_guid` join to the same entity table, and a
report needs to say which end it means.

A connector the technology does not allow between its two stereotypes, and the inclusion choice
does not admit, has no `Con_` table. It stays in EA's physical tables and is counted by the
alignment check (`outside_every_allowed_combination`).

---

## 3. Tag-row tables

Present **only where a column cannot hold the data**:

- tags the technology does not declare (on `(not in MDG)` entities and on any element or connector
  carrying an undeclared tag);
- declared tags of type **RefGUIDList**, which EA stores as `{guid},{guid},...` in one value. The
  table has one row per referenced element GUID (`value`), so a report joins it to the entity tables
  on `ea_guid`. Measured on EA 17.1; no other predefined tag type stores several values.
  **CheckList stays a column**: it holds the stored flags (`1,1,0`), which mean nothing without the
  type's item labels.

Named `<table> tags`. Columns: for an entity table, `ea_guid`, `tag`, `value`, `property_id`; for a
`Con_` table, `connector_guid`, `tag`, `value`. The Table Directory says which tags a tag-row table
holds.

---

## 4. Table Directory

One row per business table, so a reader (or an agent) can find a table without knowing the
technology.

| Column | Holds |
|---|---|
| `table_name` | The table's name |
| `kind` | `element`, `connector`, `element tag rows` or `connector tag rows` |
| `stereotype` | The stereotype's `FQName` for an element table or the connector key for a `Con_` table; blank for tag rows |
| `alias` | The technology's alias, where there is one |
| `metaclass` | The base type, for element tables |
| `source_table`, `target_table` | For a `Con_` table, the entity tables at its two ends; for a tag-row table, `source_table` is the table it belongs to |
| `in_mdg` | `yes` when the technology declares it, otherwise `no` |
| `description` | From the technology's notes |

---

## 5. Types

A declared tag becomes a typed column:

| Declared in the technology | Column |
|---|---|
| `string`, `enumeration`, `date`, `datetime` | text |
| `boolean`, `int`, `integer` | integer (a Boolean is `1` or `0`) |
| `decimal`, `double` | real |
| anything else | text |

Values are trimmed. An empty value on an integer or real column is NULL; on a text column it stays empty. **Two tags with the same name on one element:** the column shows the first (lowest property id),
as EA's Properties window does, and the preflight flags `duplicate_tag_names`. **A Memo tag's** value
is read from its Notes, where EA keeps the text. **EA writes
NULL and empty text identically, so the two cannot be told apart in any result.** A value that does
not convert to its declared type is NULL on a typed column, and the value check reports it.

Table names are limited to 123 characters (SQL Server's 128, less the `Con_` prefix and room for a
suffix); a longer name stops the build with the offending names listed.

---

## 6. EA's physical tables

The nine EA tables the business tables read, in **EA's own shape**: EA's column names, EA's types,
and (in a reporting database) EA's indexes. The business layer is built from them, and they stay in
the model, hidden, so a report can reach anything EA holds that a business table does not carry.

| Table | Holds | Joins |
|---|---|---|
| `t_package` | Packages | `Package_ID`, `Parent_ID` |
| `t_object` | Elements. `ea_guid` joins an element to its entity row | `Package_ID` to `t_package`; `Object_ID` |
| `t_objectproperties` | Element tagged values | `Object_ID` to `t_object` |
| `t_connector` | Connectors | `Start_Object_ID`, `End_Object_ID` to `t_object` |
| `t_connectortag` | Connector tagged values | `ElementID` to `t_connector.Connector_ID` |
| `t_diagram` | Diagrams | `Package_ID` to `t_package` |
| `t_diagramobjects` | Diagram placements | `Diagram_ID`, `Object_ID` |
| `t_attribute` | Attributes | `Object_ID` to `t_object` |
| `t_operation` | Operations | `Object_ID` to `t_object` |

**Scoped.** Excluded areas never appear. A kept link that crosses into an excluded area is kept,
and the far end is an `(excluded)` stub: a row that shows the element type, never the name.

**Where they live.**

| Path | The physical tables are |
|---|---|
| Direct access | Scoped views in the profile's schema, named as EA's tables, over EA's own tables |
| Reporting database | Tables in `dbo`, loaded from the post-cut extract |
| Parquet | One file per table |

A reporting database also holds `_scope_boundary` (one row per crossing: `kind`, `from_id`,
`excluded_object_id`, `detail`) and `_scope_load` (when the load ran, the profile and the counts).

---

## 7. Worked queries

Names with spaces are quoted. `logical` is the default schema.

**Applications by criticality**

```sql
SELECT [criticality], COUNT(*) AS applications
FROM [logical].[Business Application]
GROUP BY [criticality];
```

**What each application uses** - join a `Con_` table to its two ends by GUID:

```sql
SELECT s.[name] AS application, t.[name] AS system_of_record
FROM [logical].[Con_Business Application Uses System of Record] c
JOIN [logical].[Business Application] s ON s.[ea_guid] = c.[source_guid]
JOIN [logical].[System of Record]     t ON t.[ea_guid] = c.[target_guid];
```

**A self-join names both ends** - applications that use applications:

```sql
SELECT s.[name] AS caller, t.[name] AS callee
FROM [logical].[Con_Business Application Uses Business Application] c
JOIN [logical].[Business Application] s ON s.[ea_guid] = c.[source_guid]
JOIN [logical].[Business Application] t ON t.[ea_guid] = c.[target_guid];
```

**A tag that holds several values is one value in its column.** `GLBA, FFIEC` is a single string:

```sql
SELECT COUNT(*) FROM [logical].[Business Application] WHERE [regulatoryScope] = 'GLBA';      -- exact: misses it
SELECT COUNT(*) FROM [logical].[Business Application] WHERE [regulatoryScope] LIKE '%GLBA%';  -- finds both
```

**Which tables exist**

```sql
SELECT [table_name], [kind], [in_mdg] FROM [logical].[Table Directory] ORDER BY [kind], [table_name];
```

---

## 8. Rules that are not obvious and cost real money when broken

**Join a connector to its ends by GUID.** A `Con_` table's `source_guid` and `target_guid` are the
`ea_guid` of the entity tables it names. A combination whose source and target are the same entity
type (an application that uses applications) is a genuine self-join; name both sides.

**An element in two tables is counted twice by design.** A connector ending at it appears in both
entities' connector tables, so counts per entity double-count it. Use the Table Directory and the
alignment result to see which elements these are.

**A connector is matched to its table by its own profile binding.** One that is ad hoc rather than
bound to the technology's profile appears only when the inclusion choice admits it, in a
`(not in MDG)` table. One the technology does not allow and the choice does not admit stays in
EA's physical tables and is reported by the alignment check.

**A string tag that holds several values is one value in its column.** Only a RefGUIDList tag is
split into rows, so `GLBA, FFIEC` in a string tag is a single string: matching it exactly counts it
once, and `LIKE '%GLBA%'` finds both. Say so when a roll-up depends on it.

**A blank is a blank.** EA writes NULL and an empty string identically, so the two cannot be told
apart in any result.

**A sparse tag is still a column.** A declared tag is a typed column on its table however few
elements fill it. Only undeclared tags become tag-row tables.

**A reader that cannot read is an error.** An unreadable query result from EA fails the operation;
it is never turned into "no rows".

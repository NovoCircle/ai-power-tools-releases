# Modeling data and entity-relationship models in Sparx EA

How Sparx EA represents the language described in the data modeling and ER language skill, measured on EA 17.1 build 1716 (2026-10-21). **EA splits this one language across two technologies**: the Entity Relationship Diagram technology (`ERD`) for the conceptual model and, in this guide's choice, the logical model, and the data-modeling stereotypes of Core Extensions (the `EAUML` profile) for tables, columns, keys and indexes. The ERD technology's definition and Core Extensions' are not plain files in EA's install folder, so every fact here was read from what EA creates and lists, and from EA's own sample models; `ea.yaml` records the source of each fact. Examples use Westbrook Bank, a fictitious bank, as an illustration: substitute your own entities and tables. Nothing here assumes you have any particular model.

The language itself has no single standard or version (Chen 1976, IDEF1X, the relational model). EA has no technology for IDEF1X or for crow's foot as such; both appear as a drawing setting of a diagram (section 4).

## 1. What EA gives you

- **ERD technology.** Shown under Resources > MDG Technologies > System Technologies as *Entity Relationship Diagram*, profile *ERD*, **technology id `ERD`**, version 1.1. Eight stereotypes. One diagram type, created as `ERD_dp::ERD_DP`; the tab shows it as the type "Entity Relationship" inside a group named "Entity Relationship Diagram". The Resources tab lists a Transforms node under the technology, but the node has no children (read on EA 17.1 build 1716, 2026-11-04). The ERD to data model transform runs through `Project.TransformPackage` (section 6); the dialog route was not confirmed.
- **Data Modeling.** No technology of its own: its 23 stereotype names are in **Core Extensions** (`EAExtended`) > UML Profiles > **EAUML**, created as `EAUML::<name>`. One diagram type, created as `Extended::Data Modeling`. EA's own sample models call it *Data Modeling*.
- **Both diagram types are stored with the base type `Logical`**, so the stored diagram type does not tell them apart; `StyleEx` does (`MDGDgm=ERD_dp::ERD_DP` or `MDGDgm=Extended::Data Modeling`).
- **Toolboxes, quick links, model templates** exist for both. The ERD toolbox and one entity's quick links were read on EA 17.1 build 1716, 2026-11-04 (section 6); the Data Modeling toolbox and its quick links, and the model templates, were not read.

## 2. Which technology and diagram for each level

EA has no stereotype or diagram type that says "conceptual", "logical" or "physical". The table is this guide's choice, based on what each technology can store; the measured storage is in the later sections.

| Level | Technology | Diagram type | Use it for |
|---|---|---|---|
| Conceptual | ERD | `ERD_dp::ERD_DP` | The main things of the business and how they relate: `ERD_Entity`, `ERD_Relationship`, optionally `ERD_naryAssociation` (a Chen relationship set). Attributes optional. Many-to-many is fine. |
| Logical | ERD (the same diagram type, completed) | `ERD_dp::ERD_DP` | Entities with their `ERD_Attribute` elements, the primary key marked by `attributeType = primaryKey`, weak entities, categories (`ERD_Disjoint`), cardinalities on the relationship ends, many-to-many resolved by an associative entity. Independent of any database product. **The EA ruleset for this language checks this form.** |
| Logical, with migrated keys (alternative) | Data Modeling | `Extended::Data Modeling` | Tables with PK and FK operations and no database product, drawn with the IDEF1X connector notation, when you want foreign keys to appear as columns. EA's ERD technology does not migrate keys. |
| Physical | Data Modeling (EAUML) | `Extended::Data Modeling`, tables in a package stereotyped `DataModel` | Tables for one database product (`t_object.GenType`), columns with SQL types, `PK`, `FK`, `unique`, `index` operations, `FK` associations. |

Moving from one level to the next in EA is a **transform** (ERD to a data model), not a diagram conversion. Run through `Project.TransformPackage("ERD to Data Modeling", ...)` once, it produced tables, columns, `FK` connectors and a diagram (section 6). It is one observation, and the screen route was not confirmed.

## 3. Concepts: what to create

Create an element with the stereotype in the second column; pass the **qualified** form when creating by script (`ERD::ERD_Entity`, `EAUML::table`). Stored names are the bare names. The metaclass is what EA chose when the element was created with no other type.

### ERD level (conceptual and logical)

| Language concept | EA stereotype | EA metaclass | Notes |
|---|---|---|---|
| Entity | `ERD_Entity` | Class | Tag `isWeakEntity` (true, false; default false). |
| Weak entity | `ERD_Entity` with `isWeakEntity = true` | Class | Not a separate stereotype. Draw the owner's relationship (section 4). |
| Associative entity | `ERD_Entity` | Class | No marker: an ordinary entity with two relationships to its parents. |
| Generic entity, category entity | `ERD_Entity` | Class | Roles: the target (generic) and the source (category) of a categorization. |
| Attribute | `ERD_Attribute` | Class | **An element, not part of the entity.** Join it to its owner with an `ERD_Connector` drawn from the owner. Tags: `attributeType` (normal, primaryKey, multi-valued, derived; default normal), `commonDataType` (a list of 30 SQL-like types, default `na`), `dbmsDataType` (free text). |
| Primary key | `attributeType = primaryKey` on the key attributes | Class | A tag, not a constraint. No marker for an alternate key. |
| Relationship (connection) | `ERD_Relationship` | Association | A connector. Cardinality is the text on each end (`1`, `0..*`, `1..*`). Tag `isWeak` (true, false; default false) is the nearest marker of an identifying relationship. |
| Relationship set with attributes, n-ary relationship | `ERD_naryAssociation` | Class | A diamond **element**. Tag `isRecursive`. Hang its attributes on it with `ERD_Connector`. |
| Identifying relationship of a weak entity (Chen) | `WeakRelationship` | Class | The double diamond, also an element. |
| Categorization | `ERD_Disjoint` or `ERD_Overlapping` | Generalization | A connector from the **category to the generic** entity. Tag `Participation` (partial, total; default partial). `ERD_Overlapping` lets an instance belong to several categories, which IDEF1X does not. |
| Many-to-many relationship | `ERD_Relationship` | Association | No marker beyond `*` on both ends. |

No stereotype exists for a domain, a base domain, a typed domain, a key other than the primary key, a foreign key attribute, a category cluster as an object, an identifying or non-identifying marker, or an IDEF1X view. Eight of the language file's 33 concepts have no stereotype at all (Key, Candidate key, Table constraint, Domain, Base domain, Typed domain, View, Note); the rest map as above or in section 3.2. A base domain has only the nearest fact, the `commonDataType` tag on an `ERD_Attribute`. `EAUML::Entity` is **not** an ERD entity (section 7, trap 2).

### Data-model level (logical with keys, and physical)

| Language concept | EA construct | Stereotype | Notes |
|---|---|---|---|
| Table (entity at this level) | Class element | `table` | Tags `DBVersion`, `Owner`, `Tablespace`. The database product is `t_object.GenType` (`PostgreSQL`, `Oracle`...), not a tag. Put tables in a package stereotyped `DataModel`. |
| Column, attribute | **attribute of the table** | `column` | `Type` holds the SQL type text. Not an element. |
| Primary key | **operation of the table** | `PK` | Its parameters are the key columns. |
| Alternate key, unique constraint | operation | `unique` | Parameters are the columns. |
| Foreign key | **operation of the referencing table and an association** | `FK` on both | The operation's parameters are the referencing columns; its tagged values `Delete` and `Update` hold the referential actions (`No Action`, `Restrict`, ...). The association runs **from the referencing table to the referenced one**. |
| Index | operation | `index` | Parameters are the columns. |
| Check constraint | operation | `check` | |
| View, function, procedure, sequence, trigger | Class element / operation | `view`, `function`, `procedure`, `dbsequence`, `trigger` (operation) | Beyond the language file (section 5). |

#### 3.1 Columns, keys and indexes are not elements

A table is one element. Its columns are rows of `t_attribute`, its keys and indexes rows of `t_operation` (with their columns as `t_operationparams`), measured on a test model's tables. Anything that selects elements (a script that lists stereotypes, a ruleset rule, an element count) sees the table and nothing inside it. To count columns, test for a primary key, or check that a foreign key's columns match, read the table's attributes and operations; that needs the API (`Element.Attributes`, `Element.Methods`) or SQL on `t_attribute` and `t_operation`.

#### 3.2 How the language's concepts reach each level

| Concept | Conceptual | Logical (ERD) | Physical (tables) |
|---|---|---|---|
| Entity | `ERD_Entity` | `ERD_Entity` | `table` |
| Attribute | optional `ERD_Attribute` | `ERD_Attribute` | `column` |
| Primary key | none | `attributeType = primaryKey` | `PK` operation |
| Alternate key | none | none | `unique` operation |
| Foreign key | none | none (relationship line only) | `FK` operation and `FK` association |
| Relationship, cardinality | `ERD_Relationship`, end text | the same | `FK` association, `0..*` at the child end and `1` at the parent end |
| Many-to-many | allowed | resolved by an associative `ERD_Entity` | a third table with two `FK` associations |
| Weak entity | `isWeakEntity` | `isWeakEntity`, owner's relationship | composite primary key containing the owner's key |
| Category | `ERD_Disjoint` | `ERD_Disjoint` | one table per category with the generic's key as primary and foreign key |

## 4. Connections: what to connect, and which diagram

**Direction as stored (and as the ruleset reads it):**

- An **attribute line** (`ERD_Connector`) runs from the owner (entity, or relationship diamond) to the attribute.
- A **categorization** (`ERD_Disjoint`, `ERD_Overlapping`) runs from the category to the generic entity (a UML generalization points from specific to general).
- A **relationship** (`ERD_Relationship`) has no stored parent or child, and EA stores no owner for a weak entity. This guide and the ruleset draw it from the parent (the owner) to the child, which is how a weak entity's owner is recognized (section 7, trap 8).
- A **foreign key** association (`EAUML::FK`) runs from the referencing table to the referenced table, with `0..*` at the referencing end and `1` at the referenced end.

**Pairs.** The pairs the language allows are in the ruleset's two tables, generated from the language file: `ERD_Relationship` between entities (and between an entity and a relationship diamond); `ERD_Connector` from an entity or diamond to an attribute; `ERD_Disjoint` and `ERD_Overlapping` between entities; `FK` between tables. EA accepts any other pair without a message (section 7, trap 3).

| Standard diagram type | EA diagram type | Notes |
|---|---|---|
| Chen diagram | `ERD_dp::ERD_DP` | Entities, relationship diamonds as elements, attributes as elements. EA's only ERD sample draws it with the Information Engineering (crow's foot) connector notation. |
| IDEF1X entity-relationship, key-based, fully-attributed views | `Extended::Data Modeling` with the IDEF1X connector notation | EA has no diagram type per view level. The notation is a diagram setting (`TConnectorNotation`): IDEF1X on 230 of EA's sample Data Modeling diagrams. The setting was not set by script. |
| Crow's foot diagram | `ERD_dp::ERD_DP` or `Extended::Data Modeling` with the Information Engineering connector notation | 149 of EA's sample Data Modeling diagrams and the one ERD diagram. |
| Physical data model diagram | `Extended::Data Modeling` | Tables in a `DataModel` package. |

A diagram can hold only what you drop on it: the diagram's elements and connectors are those you added. Nothing keeps a diagram's drawing in step with the model.

## 5. What EA does that the language file does not

- **Database objects the language file leaves out:** `view`, `function`, `procedure`, `dbsequence`, `package`, `trigger`, and the containers `functions`, `procedures`, `sequences`. A `database connection` and a `sqlquery` Artifact hold a live connection and a query. The `Database` and `DataModel` stereotypes mark packages.
- **A database product per table** (`GenType`), 17 distinct values in EA's samples. EA keeps one Data Modeling technology and varies the product by value.
- **Tags the standard does not have:** `DBVersion`, `Owner`, `Tablespace` on tables; `commonDataType` and `dbmsDataType` on an ERD attribute; `Participation` on a categorization; `isRecursive` on an n-ary association.
- **Overlapping categories** (`ERD_Overlapping`), allowed in extended ER models, not in IDEF1X (DATA-CAT-003).
- **A multi-valued attribute type** (`attributeType = multi-valued`), which the first normal form rule of the language (DATA-ATT-002) does not allow.
- **Generation and import.** The project interface has `GenerateElementDDL` and `GeneratePackageDDL`, and neither was run. `TransformPackage` was run (section 6).

## 6. What the language has that EA does not

- **No domain, typed domain, alternate-key marker (in ERD), role name, discriminator, or category cluster object.** `commonDataType` is a data type, not a named value set.
- **No identifying or non-identifying stereotype.** `isWeak` on an `ERD_Relationship` is the nearest tag. Whether a relationship is mandatory is the minimum of its end text.
- **No key migration in the ERD technology.** A foreign key exists only in the data-model form.
- **No IDEF1X view or notation as a type.** Only a connector-notation setting of the diagram.
- **The ERD to data model transform runs through COM; the dialog route was not confirmed.** One observation, EA 17.1 build 1716. `Project.TransformPackage(name, source package GUID, target package GUID, options)` with the name `"ERD to Data Modeling"` returned True in about 7 s and created, from a package of 8 entities, 16 attributes and 1 n-ary association: a package named after the source plus `DataModeling` with a diagram of the same name, 9 `table` classes, 25 `column` attributes and 9 `FK` connectors. The transform added key and foreign-key columns, so the attribute count does not carry over one to one, and nothing beyond a sample was compared. **The return value does not show success:** `"ERD to Data Model"` returned True and created only an empty package and diagram, and a made-up name also returned True and created nothing. Check that tables exist afterwards. The Transforms node under the ERD technology on the Resources tab has no children, and the full name EA shows in the dialog is cut off as "ERD to Data Mo...", so the name above is the one that worked, not one read from the dialog. On screen, Design ribbon > Transform opens a *Model Transformation* dialog, but four attempts with automated clicks never showed a tick in the checkbox, so a person with a mouse may be needed for that route.
- **The ERD toolbox** (read on screen on the same date) has two pages: ERD (Entity, Attribute, N-ary Association) and ERD - Relationships (Connector, Relationship, Disjoint, Overlapping). It has no item for `WeakRelationship` or for a weak entity. From an entity, the quick links offer Attribute and N-ary Association (each as a plain "Association") and Entity (Relationship, Disjoint, Overlapping); a weak entity and a weak relationship are not offered. One source was tried.

## 7. Traps found

1. **Two technologies, two prefixes.** Create entities and attributes with `ERD::`, tables and their stereotypes with `EAUML::`. `EAExtended::`, `Extended::`, `ERD_dp::`, `Data Modeling::` are refused. The Resources tab names do not work as prefixes.
2. **Look-alike names bind to the wrong thing.** `EAUML::Entity` creates the business-modeling `entity` (a UML Object), not an ERD entity; `EAUI::table` creates a GUIElement named `table` of the user-interface profile. EA ignores case after the prefix (`EAUML::Table` stores `table`).
3. **EA does not stop a wrong pair.** All nine deliberately wrong connectors of the sample set (an ERD relationship that ends on an attribute, an attribute line run backwards, an FK association to a view, an attribute with two owners, a category with two generic entities) were accepted by the API without a message. The ruleset exists for this. Whether the quick linker in the UI offers them was not read.
4. **A wrong diagram type name is silent.** `ERD::ERD_DP`, `ERD::ERD`, `EAExtended::Data Modeling`, `EAUML::Data Modeling` and the rest create an ordinary Class diagram with no error. Only `ERD_dp::ERD_DP` and `Extended::Data Modeling` make the right one. Check `StyleEx` for `MDGDgm=` after creating one.
5. **Columns, keys and indexes are not elements** (section 3.1). A count of elements shows tables only.
6. **`FK` is two things:** an operation on the child table and an association between the tables. A model can hold one without the other; nothing keeps them in step.
7. **Tag defaults hide the choice.** A new `ERD_Attribute` already carries `attributeType = normal` and a new `ERD_Entity` `isWeakEntity = false`, so a rule that reads the tag sees the default for a modeler who never chose. Set the tag by updating the row the element already has; adding a second row of the same name leaves a duplicate.
8. **A weak entity needs its owner's relationship drawn from the owner.** The check for a weak entity (DATA-ENT-005) reads the owner as the source of the `ERD_Relationship` that ends on the weak entity, so draw that relationship from the owner to the weak entity. This is a convention of the ruleset, because EA stores no owner for a weak entity and the standard gives a relationship no direction. A relationship drawn the other way round is reported as a weak entity with no owner. Whether Sparx's toolbox implies the same direction is not yet confirmed against the toolbox.
9. **A relationship line to a diamond: EA accepts both.** EA's samples contain no n-ary association, and the API accepts `ERD_Relationship` and `ERD_Connector` alike; the ruleset allows both between an entity and a diamond. On screen (EA 17.1 build 1716, 2026-11-04) the toolbox items Relationship and Connector, each dragged from an entity to an N-ary Association, made an Association with the stereotype `ERD::ERD_Relationship` and `ERD::ERD_Connector`, source the entity and target the diamond; neither was refused. The quick link to a diamond is a plain Association (not created, so its stereotype is not known).
10. **Do not infer logical from physical by a tag.** EA's sample Data Modeling diagrams are all stored with the type `Logical` whatever the content, so the stored type says nothing about the level.
11. **The Data Modeling toolbox and quick links were not read.** Only the ERD toolbox and one entity's quick links were (section 6).

## 8. Checking a model

The data-modeling ruleset (`rulesets/data-modeling-er/data-modeling-er_rules.yaml`, 6 rules) checks: that a relationship, attribute or categorization line joins only the ERD pairs the language allows and that a foreign key line joins two tables; that an `ERD_Attribute` has exactly one owner and is not marked multi-valued; that a weak entity has an owner's relationship; and that a category entity has at most one generic entity. It does not check names, cardinalities, columns, keys, indexes, referential actions, normal forms, views of a model, or anything about instance data; those need a person or a tool that reads attributes and operations. The ruleset's header says why: the grammar cannot read a name, a cardinality, an attribute or an operation.

3 of 6 rules in this ruleset use formats newer than 3.6.4, and on that server they report nothing or don't run as written. Use server 3.6.5 or later, because a clean result on 3.6.4 doesn't mean the model passes.

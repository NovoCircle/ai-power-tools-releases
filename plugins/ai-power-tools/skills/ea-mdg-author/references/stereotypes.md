# Element and connector stereotypes

Back to [SKILL.md](../SKILL.md).

## Section 1 — Element Stereotype

```xml
<Stereotype name="WBABusinessApplication"
            alias="Business Application"
            metatype="WBABusinessApplication"
            notes="A business or IT application in the Westbrook Bank portfolio."
            isAbstract="false"
            bgcolor="15782580"
            fontcolor="-1"
            bordercolor="-1"
            borderWidth="-1"
            cx="130" cy="70">
  <AppliesTo>
    <Apply type="Component"/>
  </AppliesTo>
  <TaggedValues>
    <Tag name="criticality" type="enumeration"
         description="Business impact classification"
         default="Standard" unit=""
         values="Mission-Critical,Business-Critical,Important,Standard"/>
    <Tag name="lifecycle" type="enumeration"
         description="Lifecycle phase"
         default="Current" unit=""
         values="Strategic,Current,Sunset,Deprecated,Retired"/>
    <Tag name="businessOwner" type="String"
         description="Owning business team or role, never a person's name"
         default="" unit="" values=""/>
    <Tag name="technicalOwner" type="String"
         description="Owning technical team or role, never a person's name"
         default="" unit="" values=""/>
    <Tag name="dataClassification" type="enumeration"
         description="Sensitivity of data the application handles"
         default="Internal" unit=""
         values="Public,Internal,Confidential,Restricted"/>
    <Tag name="regulatoryScope" type="String"
         description="Regulatory regimes that apply, e.g. PCI-DSS, GDPR, SOX"
         default="" unit="" values=""/>
  </TaggedValues>
</Stereotype>
```

This is the real `WBABusinessApplication` stereotype from the Westbrook Bank technology — note the
doubled prefix (`WBA` namespace, `WBABusinessApplication` name) and the six base tagged values
every WBA stereotype carries. Applying it to `Component` (not `Class`) matches the metaclass the
technology actually declares; getting this wrong is the single most consequential error in an MDG.

**Attribute rules:**
- `name=` — the stereotype identifier used in `WBA::WBABusinessApplication` toolbox references
- `alias=` — display label shown in EA UI (can differ from name)
- `metatype=` — used in EA's element type display; set to same as `name` unless you have a reason to differ
- `bgcolor=` — COLORREF integer (see color table in `references/diagrams-toolboxes.md`); `-1` = use EA theme default
- `cx` / `cy` — default element width/height in pixels on diagram canvas
- `Apply type=` options: `Class`, `Component`, `Node`, `Package`, `Interface`, `Dependency`, `Association`, `Realization`, etc.

**Tagged value `type=` options (verified EA 17):**

| type= value | EA display | Notes |
|-------------|------------|-------|
| `String` | Text field | Free text |
| `enumeration` | Dropdown | Comma-separated `values=` attribute |
| `Boolean` | Checkbox | `default="true"` or `"false"` |
| `Date` | Date picker | |
| `memo` | Multi-line | Long text |
| `RefGUID` | GUID picker | Link to another element |
| `url` | URL field | |
| `file` | File picker | |
| `Integer` | Numeric | |

> **Common mistake:** using `enum` or `Enumeration` — the correct value is `enumeration` (lowercase, full word).

### Base Type and Project Browser Visibility

`<Apply type="..."/>` controls what `t_object.Object_Type` EA stores for elements of this
stereotype. The value must be a **standard UML type** that EA's Project Browser natively renders
— otherwise elements will be invisible in the browser tree even though they appear on diagram
canvases and are accessible via SQL.

**Safe base types (Project Browser renders them natively):**
`Class`, `Component`, `Node`, `Package`, `Interface`, `Actor`, `UseCase`, `Activity`,
`Artifact`, `Boundary`, `Collaboration`, `DataStore`, `Decision`

**Dangerous base types — only use if the corresponding MDG is active at project scope:**

| `Apply type=` | Requires |
|---|---|
| `BusinessActor`, `BusinessProcess`, etc. | ArchiMate3 MDG active at project scope |
| `ApplicationComponent`, `ApplicationService`, etc. | ArchiMate3 MDG active at project scope |
| Anything starting with a BPMN shape name | BPMN MDG active at project scope |

> **Rule:** If you are building a standalone custom MDG that does not require ArchiMate3 or
> another extended MDG, always use `<Apply type="Class">` (or another standard UML type) as the
> base. The ArchiMate conceptual alignment is conveyed through the stereotype name, tagged values,
> and documentation — not the base type. Using `BusinessActor` as the base type when ArchiMate3
> is not project-loaded causes elements to be invisible in the Project Browser.

**If elements are already stored with the wrong base type**, the COM setter (`elem.Type = "Class"`)
silently ignores the change for ArchiMate-typed elements. Use `repo.Execute()` DML directly:

```python
repo.Execute(
    "UPDATE t_object SET Object_Type='Component' "
    "WHERE Stereotype IN ('WBABusinessApplication','WBAVendorSystem') "
    "AND Object_Type <> 'Component'"
)
```
Then close and reopen the project to flush EA's in-memory cache.

---

## Section 1 — Connector Stereotype

> **The shipped WBA technology (1.1.1) defines three connector stereotypes:** `Uses` (Association),
> `Flows` (InformationFlow) and `realizes` (Realisation). For a relationship between WBA elements,
> use one where it fits, otherwise a plain UML connector type with no stereotype — `Dependency`,
> `Realization`, `Association`, `Aggregation`. The pattern below shows how you *would* add
> another, labelled plainly as a proposed extension so it is never mistaken for part of the
> shipped technology.

```xml
<!-- PROPOSED EXTENSION — not part of the shipped WBA technology. -->
<Stereotype name="WBARunsOn"
            alias="Runs On"
            notes="Proposed extension: Business Application runs on Vendor System."
            isAbstract="false"
            bgcolor="-1" fontcolor="-1" bordercolor="-1"
            borderWidth="-1" cx="90" cy="70">
  <AppliesTo>
    <Apply type="Dependency"/>
  </AppliesTo>
  <TaggedValues>
    <Tag name="integrationPattern" type="enumeration"
         description="Integration pattern"
         default="Synchronous" unit=""
         values="Synchronous,Asynchronous,Batch"/>
  </TaggedValues>
</Stereotype>
```

Connector `Apply type=` options: `Dependency`, `Association`, `Realization`, `Aggregation`, `Composition`, `InformationFlow`, `Sequence`

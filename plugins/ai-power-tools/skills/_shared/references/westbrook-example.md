# Westbrook Bank - canonical example specification

Westbrook Bank is the fictitious organization used in every example, walkthrough, test fixture
and demo across the AI Power Tools skills. It exists so that no real customer's name, model or
metamodel shape ever ships.

**Read this file before writing a new example. Do not invent a parallel vocabulary.**

Ground truth is the MDG technology file `WBA_MDG.xml` (version 1.1.1) and the model
`WestbrookBank.qea` in the Westbrook demo directory. Where this document and that file disagree, the file wins and this
document is the bug.

---

## 1. The name slots

Several different things are easy to confuse. They are not interchangeable.

| Slot | Value | Where it appears |
|---|---|---|
| Organization | Westbrook Bank | Prose, narrative, element notes |
| MDG technology id | `WBA` | The `id=` attribute of the technology's `<Documentation>`; what EA registers and what `get_mdg_from_runtime` reports. Version 1.1.1 |
| Technology display name | `WestbrookBankArchitecture` | User-facing technology name; the key used in the server's language tables; also the name of the UML profile that holds the stereotypes |
| Full technology title | `WBA (Westbrook Bank Architecture)` | The start of the `notes=` of the technology's `<Documentation>` (its `name=` is `WBA`) |
| Stereotype namespace prefix | `WestbrookBankArchitecture` | The profile name. Every qualified element or connector stereotype: `WestbrookBankArchitecture::WBABusinessApplication`; this is the `FQName` EA stores in `t_xref` |
| Diagram namespace prefix | `WBA` | The diagram profile is named `WBA`, so a diagram type is `WBA::WBAApplicationView` (stored as `MDGDgm=WBA::WBAApplicationView` on the diagram) |
| Model file | `WestbrookBank.qea` | Every path example |
| Conformance rule id prefix | `WBA-` | Ruleset rule ids, e.g. `WBA-APP-001` |

Note that the technology id (`WBA`) is not the profile name (`WestbrookBankArchitecture`), so the
qualified form is `WestbrookBankArchitecture::WBABusinessApplication`, never `WBA::WBABusinessApplication`.
Every element stereotype name itself begins with `WBA`. That is what the MDG actually declares.
Do not "correct" `WBABusinessApplication` to `BusinessApplication`. `t_object.Stereotype` holds
the bare name; the qualified form lives in `t_xref`.

Both `WBA` and `WestbrookBankArchitecture` are accepted as installed-technology identifiers by
the server. When an example needs one value, prefer `WBA` for MDG lookups (`tech_id`) and for
diagram types, the bare name for SQL against `t_object.Stereotype`, `WestbrookBankArchitecture::`
for a qualified stereotype, and `WestbrookBankArchitecture` for anything presented to a person as
the language name.

---

## 2. Element stereotypes - all 15

This is the complete set of element stereotypes. There are no others. (The three connector
stereotypes are in section 6.) If an example needs a concept that is not in this table, use the
closest entry rather than inventing a new stereotype.

| Stereotype | Alias | EA metaclass | Tag set |
|---|---|---|---|
| `WBABusinessApplication` | Business Application | Component | base + PCI |
| `WBABusinessService` | Business Service | Component | base |
| `WBAVendorSystem` | Vendor System | Component | base + PCI + vendor |
| `WBARegulatedFunction` | Regulated Function | Component | base |
| `WBASystemOfRecord` | System of Record | Component | base |
| `WBAAIGateway` | AI Gateway | Component | base + AI |
| `WBAAIService` | AI Service | Component | base + AI |
| `WBAAIModel` | AI Model | Class | base + AI |
| `WBADataAsset` | Data Asset | Class | base |
| `WBADataEntity` | Data Entity | Class | base |
| `WBAGovernedElement` | Governed Element | Class | base |
| `WBARegulatedActivity` | Regulated Activity | Activity | base |
| `WBACustomerTouchpoint` | Customer Touchpoint | Activity | base |
| `WBAExternalCall` | External Call | Activity | base |
| `WBATechnologyNode` | Technology Node | Node | base |

Metaclass distribution: 7 Component, 4 Class, 3 Activity, 1 Node.

The metaclass matters. An example that creates a `WBAAIModel` must create it as a **Class**, not
a Component - `create_element` with the wrong base type produces an element the MDG will not
recognize and no toolbox will offer.

---

## 3. Tagged values - 13 on element stereotypes

Every element stereotype carries the **base** set of 6. The three AI stereotypes
(`WBAAIGateway`, `WBAAIService`, `WBAAIModel`) additionally carry the **AI** set of 4.
`WBABusinessApplication` and `WBAVendorSystem` additionally carry the **PCI** tag, and
`WBAVendorSystem` the **vendor** tags. The three connector stereotypes carry their own 3 tags
(section 6).

### Base set (all 15 element stereotypes)

| Tag | Type | Permitted values |
|---|---|---|
| `criticality` | enumeration | `Mission-Critical`, `Business-Critical`, `Important`, `Standard` |
| `lifecycle` | enumeration | `Strategic`, `Current`, `Sunset`, `Deprecated`, `Retired` |
| `businessOwner` | String | free text - a team or role, never a real person's name |
| `technicalOwner` | String | free text - a team or role, never a real person's name |
| `dataClassification` | enumeration | `Public`, `Internal`, `Confidential`, `Restricted` |
| `regulatoryScope` | String | free text, e.g. `PCI-DSS`, `GDPR`, `SOX` |

### AI set (WBAAIGateway, WBAAIService, WBAAIModel only)

| Tag | Type | Permitted values |
|---|---|---|
| `modelGovernanceClass` | enumeration | `SR-11-7-Tier-1`, `SR-11-7-Tier-2`, `Internal-Use`, `Experimental` |
| `humanInLoopRequired` | boolean | `true`, `false` |
| `auditLoggingEnabled` | boolean | `true`, `false` |
| `dataResidency` | String | free text jurisdiction, e.g. `EU`, `US-only` |

### PCI and vendor tags (all `String`, free text)

| Tag | Declared on |
|---|---|
| `pciScopeJustification` | `WBABusinessApplication`, `WBAVendorSystem` |
| `product` | `WBAVendorSystem` |
| `vendor` | `WBAVendorSystem` |

Enumeration values are exact. `Mission Critical` (space instead of hyphen) is wrong and will fail
a conformance check. `businessOwner` and `technicalOwner` take a team name such as
`Payments Engineering` - putting a person's name there reintroduces exactly the kind of
identifying detail this example exists to avoid.

---

## 4. Diagram stereotypes - all 3

The diagram profile is named `WBA`, so each diagram type qualifies as `WBA::<name>`, for example
`WBA::WBAApplicationView`.

| Diagram stereotype | Alias | diagramID | Toolbox referenced |
|---|---|---|---|
| `WBAApplicationView` | WBA Application Architecture | `WBA-AppView` | `WBA::WBA ArchiMate` |
| `WBAProcessView` | WBA Business Process | `WBA-ProcView` | `WBA::WBA BPMN` |
| `WBADataModelView` | WBA Data Model | `WBA-DataView` | `WBA::WBA UML` |

## 5. Toolbox pages - all 3

`WBA ArchiMate Elements` (12 items), `WBA BPMN Elements` (5), `WBA UML Elements` (5). The toolbox
profiles that hold them are named `WBA ArchiMate`, `WBA BPMN` and `WBA UML`, which is what the
`toolbox` property of the diagram stereotypes names. Each page offers element stereotypes and,
for connectors, `Uses`, `Flows` and `realizes` (not all three on every page).

---

## 6. Connector stereotypes

Three different statements, often confused. All are true.

**(a) The WBA MDG (1.1.1) declares three connector stereotypes**, in the `WestbrookBankArchitecture`
profile:

| Stereotype | EA metaclass | Tag set |
|---|---|---|
| `Uses` | Association | connector set |
| `Flows` | InformationFlow | connector set |
| `realizes` | Realisation | connector set |

The **connector** set is 3 enumeration tags:

| Tag | Permitted values |
|---|---|
| `dataFlowClassification` | `Public`, `Internal`, `Confidential`, `Restricted` |
| `integrationPattern` | `API`, `Batch`, `Event`, `File` |
| `slaTier` | `Gold`, `Silver` |

**(b) EA stores a bound connector's stereotype bare. The binding is in `t_xref`.**
`t_connector.Stereotype` holds `Uses`, not `WestbrookBankArchitecture::Uses`. What binds the
connector to the technology is its `t_xref` row,
`@STEREO;Name=Uses;...FQName=WestbrookBankArchitecture::Uses;@ENDSTEREO;`. Setting `StereotypeEx`
to `WestbrookBankArchitecture::Uses` makes EA write that row, and add whichever of the three
declared tags the connector lacks, with empty values (measured 2026-10-07, EA 17.1; existing
values are kept). A connector can also carry a bare `Uses` with no binding, or one bound to a
shipped language such as `BMM::Uses`. The string in `t_connector.Stereotype` is the same in all
three cases, so provenance is read from `t_xref`, not from that column.

**(c) The Westbrook demo model also carries connector stereotypes the MDG does not declare.**
Counted from the model on 2026-10-07 (247 connectors):

| `t_connector.Stereotype` | Count | Bound to |
|---|---|---|
| `Uses` | 25 | 18 `WestbrookBankArchitecture::Uses`, 7 `BMM::Uses` (left as they were) |
| `Flows` | 5 | `WestbrookBankArchitecture::Flows` |
| `realizes` | 4 | `WestbrookBankArchitecture::realizes` |
| `Requires` | 3 | `BMM::Requires` |
| `extends` | 3 | nothing (ad hoc) |
| `part-of` | 2 | nothing (ad hoc) |
| *(none - plain connector)* | 153 | |

The other 52 carry stereotypes of shipped languages, the fixtures or ad hoc UML names; they are
not WBA vocabulary. Do not prefix any of these `WBA::`: `WBA` is the technology id, and EA's
qualified form uses the profile name.

### The governance rule matches a different set - and that is a real defect

`WBA-LFY-001` flags a connector whose source `lifecycle` is `Strategic` or `Current`, whose
target is `Deprecated`, and whose stereotype is one of:

```sql
WHERE c.Stereotype IN ('Uses', 'ConsumesService', 'Realizes', 'Flows')
```

Compare that with the table above. **Two of those four can never match:**

- `ConsumesService` does not occur in the model at all.
- `Realizes` occurs only as lower-case `realizes`, and the comparison is case-sensitive. Binding
  the connector to the technology did not change this: the stored string is still `realizes`.

So the rule is effectively checking `Uses` and `Flows` only. It is not wrong in a way that
produces false positives - it silently under-reports, which is the harder kind to notice.

Do not "fix" this by editing either side to match. It is recorded as a defect, and the demo
model's tests assert the current counts, so changing one without the other breaks them.

### What this means when you write an example

- Naming the stereotypes the model actually uses is describing reality, not inventing vocabulary.
  Take them from the tables above.
- Do not assume consistent casing. `realizes` and `Realizes` are different strings to SQL, and
  the model contains the lower-case one.
- `extends` and `part-of` are informal names that accumulated outside any MDG (no `t_xref`
  binding). That is realistic and is useful teaching material about model drift - but describe
  them as drift, never as the technology's vocabulary. `Requires` is a shipped BMM stereotype.

### What is still forbidden

The names `WBA::dependsOn`, `WBA::realizes` and `WBA::mastersData` appear in some existing
skills. `dependsOn` and `mastersData` are not in the MDG and not in the model. Treat all three
as follows:

> **Do not confuse `WBA::realizes` with `Realizes` or with `realizes`.** `realizes` - lower-case,
> unqualified - is the stereotype the MDG declares and the model stores. `Realizes` - capitalized -
> is a different string: it is what `WBA-LFY-001` compares against, and no connector in the model
> carries it. `WBA::realizes` is neither: `WBA` is the technology id, not the profile name, so EA
> never stores that form. The bound form is `WestbrookBankArchitecture::realizes`.

- Do **not** introduce `WBA::dependsOn`, `WBA::realizes` or `WBA::mastersData` into new material.
- For a relationship between WBA elements, use the declared `Uses`, `Flows` or `realizes` where
  one fits. Otherwise use a plain UML connector type - `Dependency`, `Realization`,
  `Association`, `Aggregation` - with no stereotype.
- A skill whose subject *is* adding connector stereotypes to an MDG may show others, but must say
  plainly that they are a proposed extension and not part of the shipped WBA technology.
- The same carve-out covers a **test fixture** that exercises connector-stereotype rules.
  `validate_model`'s connector-endpoint and cardinality rule types read `t_connector.Stereotype`
  directly, so an unstereotyped connector cannot be evaluated by them at all and the feature
  would go untested. Such a fixture reuses the names `Uses`, `Flows` and `realizes` rather than
  inventing a fourth vocabulary, and labels its copies test-only in both the MDG XML and the rules
  file, because they are not the shipped technology's declarations.

---

## 7. Authoring examples that build an MDG

A skill that teaches MDG authoring must build a **subset of the real WBA technology** - the same
stereotype names, aliases, metaclasses and tagged values given above.

Do not invent a second vocabulary under the `WestbrookBankArchitecture` profile (older material
writes it `WBA::`). Names such as `WBA::Application`,
`WBA::TechPlatform`, `WBA::BizCapability`, `WBA::DataDomain`, `WBA::RunsOn`, `WBA::Realises` and
`WBA::Integration` are **not** part of this technology. A reader who follows an authoring skill
and then a modeling skill must end up with one coherent artifact, not two that contradict each
other under the same prefix.

Note also the spelling: `Realization` / `realizes`, not `Realises`.

---

## 8. Path placeholders

Never write an absolute local path. Use these forms:

| Instead of | Write |
|---|---|
| a real model path | `<model-dir>\WestbrookBank.qea` |
| a real MDG path | `<mdg-dir>\WBA_MDG.xml` |
| a user profile path | `%APPDATA%\...` or `%USERPROFILE%\...` |
| a generic user home | `C:\Users\<you>\...` |

## 9. Rule ids

Conformance rule ids are prefixed `WBA-` and grouped by subject:
`WBA-APP-001`, `WBA-AI-001`, `WBA-DATA-001`, `WBA-GOV-001`, `WBA-LFY-001` (lifecycle),
`WBA-TV-001` (tagged values), `WBA-REL-001` (relationships), `WBA-CNX-001` (connectors).

The prefix is not optional. A bare `LFY-001` reads as an identifier from somewhere else and will
not match the demo model's tests, which use the fully qualified form.

---

## 10. Checklist before you ship an example

- [ ] Every stereotype named appears in the section 2 table, spelled exactly.
- [ ] Every stereotype is created against the metaclass that table gives it.
- [ ] Every tagged value appears in section 3 (or section 6 for a connector), and enumeration values match exactly.
- [ ] AI-only tags are used only on `WBAAIGateway` / `WBAAIService` / `WBAAIModel`; `vendor` and `product` only on `WBAVendorSystem`; `pciScopeJustification` only on `WBABusinessApplication` / `WBAVendorSystem`.
- [ ] Any connector stereotype is `Uses`, `Flows` or `realizes`, written bare in SQL and `WestbrookBankArchitecture::`-qualified when bound (see section 6).
- [ ] An MDG-authoring example builds a subset of the real technology (see section 7).
- [ ] No absolute path, no personal name, no real organization.
- [ ] `businessOwner` / `technicalOwner` hold a team or role, not a person.
- [ ] The qualified form is `WestbrookBankArchitecture::WBAThing`, not `WBA::WBAThing` and not `WestbrookBankArchitecture::Thing`.

---

## 11. Known defects in the demo MDG - flag, do not silently fix

Recorded so that nobody "corrects" an example to match a broken source.

The three defects recorded for version 1.0 do not hold for 1.1.1: the technology now declares
its profiles, diagram profile and toolbox profiles as separate profiles; the diagram profile is
named `WBA`, so the three WBA diagram types resolve and switch the toolbox on opening; and the
three toolbox pages carry items (12, 5 and 5). Do not describe them as current.

Still true of the file:

1. The root `<MDG.Technology version="...">` attribute reads `1.0`. That is not the technology's
   version: it is the `version=` of the `<Documentation>` element, `1.1.1`.

These are defects in the demo artifact, not in this specification. Fixing them is separate work.

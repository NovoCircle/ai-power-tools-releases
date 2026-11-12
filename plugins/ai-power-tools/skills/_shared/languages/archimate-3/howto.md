# ArchiMate 3.1 in Sparx EA: how to model it the way Sparx's technology does

Measured on EA 17.1 build 1716 with the ArchiMate 3.1 technology that ships with EA (technology id `ArchiMate3`, display name
"ArchiMate 3.1"). Every fact below is either read from the technology's own file or read back from a model built with it; the
machine-readable form is `ea.yaml` beside this file. Examples use Westbrook Bank, a fictitious bank; substitute your own
elements and your own model. Nothing here assumes you have a Westbrook model.

**Version.** This guide describes ArchiMate 3.1 (The Open Group, document C197, 5 November 2019), the version of the technology EA ships. The Open Group published ArchiMate 3.2 on 19 October 2022. The 3.2 edition was read only for what it changed, so nothing here, and no rule of the ArchiMate ruleset, covers 3.2.

## 1. Names: stored, qualified, and why it matters

| Form | Example | Where it lives | Use it for |
|---|---|---|---|
| Stored | `ArchiMate_BusinessActor` | `t_object.Stereotype`, `t_connector.Stereotype` | SQL, validation rule selectors |
| Qualified | `ArchiMate3::ArchiMate_BusinessActor` | `t_xref`, row named `Stereotypes`, `FQName`; the API's `StereotypeEx` | Creating elements and connectors; telling ArchiMate 3.1 from ArchiMate 2 |

The stored name carries the `ArchiMate_` prefix on every concept and relationship. The standard's name, `BusinessActor`, is only
the `metatype` attribute in the file; a rule selector or query spelled that way matches nothing and reports a clean model.

ArchiMate 2 (technology id `Archimate`) uses the same short names. A query on the stored column cannot tell the two apart;
the qualified name in `t_xref` can.

## 2. Creating elements: always the qualified type

Pass `ArchiMate3::ArchiMate_<Concept>` as the type when you create an element:

- Through the COM API: `Elements.AddNew("Chief Lending Officer", "ArchiMate3::ArchiMate_Stakeholder")`.
- Through the AI Power Tools server: `create_element` or `create_elements_bulk` with `type: "ArchiMate3::ArchiMate_Stakeholder"`
  (or `type: "Class"` plus `stereotype: "ArchiMate3::ArchiMate_Stakeholder"`).

**Do not create elements through the language route** (`create_element_in_language` with `language_id: "ArchiMate3"`, or a bulk
spec with `language_id`). It binds seven types to the ArchiMate 2 technology instead of 3.1: Product, Node, Device, Artifact,
Representation, Meaning and Value. Two of them (Artifact, Device) also pick up an `iconstyle` tag that the 3.1
file does not define. The other 52 element types bind correctly, which is why it goes unnoticed. After any bulk creation, check
the binding:

```sql
SELECT o.Object_ID, o.Name, o.Stereotype, x.Description
FROM t_object o LEFT JOIN t_xref x ON x.Client = o.ea_guid AND x.Name = 'Stereotypes'
WHERE o.Stereotype LIKE 'ArchiMate_%'
  AND (x.Description IS NULL OR x.Description NOT LIKE '%FQName=ArchiMate3::%')
```

An element with a stereotype but no ArchiMate3 binding is in the wrong technology or has no technology at all.

## 3. The metaclass each concept lands on

EA stores every element under a UML metaclass (`t_object.Object_Type`). The technology chooses it; you do not.

| Metaclass | Concepts |
|---|---|
| Class (35) | Location, Stakeholder, Driver, Assessment, Goal, Outcome, Principle, Requirement, Constraint, Meaning, Value, Resource, Capability, CourseOfAction, BusinessActor, BusinessRole, BusinessCollaboration, BusinessObject, Contract, Representation, Product, ApplicationCollaboration, DataObject, Node, Device, SystemSoftware, TechnologyCollaboration, Artifact, Equipment, Facility, Material, WorkPackage, Deliverable, Plateau, Gap |
| Activity (17) | BusinessProcess, BusinessFunction, BusinessInteraction, BusinessEvent, BusinessService, ApplicationFunction, ApplicationInteraction, ApplicationProcess, ApplicationEvent, ApplicationService, TechnologyFunction, TechnologyProcess, TechnologyEvent, TechnologyService, TechnologyInteraction, ValueStream, ImplementationEvent |
| Interface (3) | BusinessInterface, ApplicationInterface, TechnologyInterface |
| Component (1) | ApplicationComponent |
| Boundary (1) | Grouping |
| Decision (1) | Junction (see 6) |
| Class, and also Association (3) | Path, CommunicationNetwork, DistributionNetwork (see 5) |

Only one tagged value exists in the whole technology: `junctionKind` on the junction. Every other concept has none.

## 4. Relationships

The 11 relationship stereotypes of the standard are connectors. Create each with its qualified type.

| Relationship | Stored stereotype | Metaclass | How the file reads it |
|---|---|---|---|
| Composition | `ArchiMate_Composition` | Association | whole at the source ("composed of") |
| Aggregation | `ArchiMate_Aggregation` | Association | whole at the source ("aggregation of") |
| Assignment | `ArchiMate_Assignment` | Association | source to destination ("assigned to") |
| Serving | `ArchiMate_Serving` | Association | source to destination ("serving") |
| Association | `ArchiMate_Association` | Association | unspecified direction |
| Realization | `ArchiMate_Realization` | Dependency | source "realizes" target |
| Access | `ArchiMate_Access` | Dependency | source to destination ("accesses") |
| Triggering | `ArchiMate_Triggering` | ControlFlow | source "triggers" target |
| Flow | `ArchiMate_Flow` | ControlFlow | source "flows to" target |
| Influence | `ArchiMate_Influence` | ControlFlow | source "influences" target |
| Specialization | `ArchiMate_Specialization` | Generalization | source "specializes" target |

Two consequences that matter when you count or check connectors:

- **The aggregate is the source.** A collaboration that aggregates two roles has two outgoing aggregation connectors, not two
  incoming. A rule that counts incoming aggregations on a collaboration finds none on a correct model.
- Serving, access and influence sit on EA's toolbox page "Structural Relationships" although the standard classes them as
  dependency relationships. The page is a toolbox grouping, not a rule.

Bulk connector creation is not idempotent for these types: sending the same spec twice creates the connector twice
Check what exists before a second pass.

## 5. Path, Communication Network and Distribution Network: element or connector

In the standard these three are elements. EA's technology declares each stereotype twice, on `Class` and on `Association`, so each can be
an object or a drawn link, and the Technology toolbox lists each twice ("Path (Object)" and "Path (Connector)").

- **Element form** (what the standard defines): create with the qualified type, `ArchiMate3::ArchiMate_Path`. EA stores a Class
  bound to `ArchiMate3`. Join it with the 11 relationships like any element. This is the form the relationship table covers.
- **Connector form** (a drawing convenience): create a connector of metaclass `Association` and set its stereotype to the
  qualified name (COM: `AddNew(name, "Association")`, then `StereotypeEx = "ArchiMate3::ArchiMate_Path"`). The standard's rules
  do not see it, because the standard has no such connector.
- **Trap.** Creating the connector with the qualified type alone (`type: "ArchiMate3::ArchiMate_Path"`) reports success and stores a
  plain Dependency with no stereotype. The same applies to `ArchiMate_CommunicationNetwork` and
  `ArchiMate_DistributionNetwork`. Always pass `Association` plus the stereotype, and read `t_connector.Stereotype` back.

## 6. Junction

The standard has an and-junction and an or-junction. EA has one stereotype, `ArchiMate_Junction`, with the tagged value
`junctionKind` (`AND` or `OR`, default `AND`). It is stored as an element of metaclass `Decision`, not as a connector.

A junction accepts access, assignment, flow, influence, association, realization, triggering and serving, and all connectors joined
to it are of one type. It does not accept composition, aggregation or specialization. EA's own quick-link table offers
composition, aggregation and specialization at a junction (121 rows); the standard forbids them, so the quick link is wrong there.

## 7. Diagram types

The technology has five diagram types, all based on `Diagram_Logical`. Create a diagram with the qualified type. EA stores
`t_diagram.Diagram_Type = Logical` and `t_diagram.StyleEx` containing `MDGDgm=<type>;`.

| Standard diagram type | EA diagram type | Toolbox |
|---|---|---|
| Business Layer | `ArchiMate3::Business` | Business |
| Application Layer | `ArchiMate3::Application` | Application |
| Technology Layer | `ArchiMate3::Technology` | Technology |
| Motivation | `ArchiMate3::Motivation` | Motivation |
| Implementation and Migration | `ArchiMate3::Implementation` | Implementation |
| Strategy | none: use `ArchiMate3::Motivation` | Motivation, page "Strategy Concepts" |
| Physical | none: use `ArchiMate3::Technology` | Technology, page "Physical Extension" |

Each toolbox has pages for the concepts of its layer, then "Structural Relationships", "Dynamic Relationships" and "Other
Concepts" (Specialization, Junction, Grouping, Location). 28 pages in all; `ea.yaml` lists every item in order. Each concept
has a default diagram type, so dropping an element on a different diagram type may switch the toolbox.

Checked on screen (EA 17.1 build 1716, 2026-11-04): the Resources tab shows a group "ArchiMate 3.1" with the five diagram types (Business Layer Diagram, Application Layer Diagram, Technology Layer Diagram, Motivation Diagram, Implementation and Migration) and the five toolboxes (Application, Business, Implementation, Motivation, Technology); ArchiMate 3.2 is not listed. A Business Layer diagram shows only the Business layer pages: the three Business concept pages (Active Structure, Behavioral, Passive Structure), then Structural Relationships, Dynamic Relationships and Other Concepts. The profile rows were not recounted.

## 8. What EA does that the standard does not

- **One extra stereotype, `ArchiMate_TechnologyObject`.** The standard's text mentions a generic technology-layer passive element;
  EA ships it as a concept you can create (metaclass Class). The standard's relationship table does not name it, so a
  relationship check ignores it. Prefer Artifact or Material.
- **Strategy and physical have no diagram type of their own** (section 7).
- **The quick linker offers more than the standard allows** (section 9).
- **25 view definitions and 27 model patterns** ship with the technology; the 25 view definitions match the standard's
  viewpoint element lists. The patterns include goal contribution and principles, which are not in the 25.
- **A script, "Migrate ArchiMate 2 to ArchiMate 3,"** ships with the technology.
- **Network connectors** (`d`, `p`, `w` in the quick-link table) are EA's, not the standard's (section 5).

## 9. The quick linker is not a validity check

On screen (same date and build), from a Business Actor on a Business Layer diagram the menu offered only Business layer targets (Business Actor, Collaboration, Event, Function, Interaction, Interface, Object, Process, Role, Service, Contract, Grouping, Junction, Location, Product, Representation). The submenus opened gave assignment, flow, serving and triggering to a Business Role or Process, access to a Business Object, and aggregation, composition, specialization, flow, serving and triggering between actors. One source, four target types.

The quick linker offers the relationship letters in the technology file's embedded table. Counted cell by cell, that table holds
**3,045 relationship letters the standard's allowed-relationship table does not**. Part of that count is a difference of keys, not
of rules: EA keys a relationship end by the relationship's name (Access, Aggregation, and so on), the standard by one
"Relationship" row, so 1,342 association letters (which the standard also allows) and 44 composition and aggregation letters
on grouping, location and plateau rows are counted twice. Like for like, EA offers **1,659 letters the standard refuses** and omits one
it allows:

| Where | Extra letters | Standard says |
|---|---|---|
| Into a relationship, from an element other than grouping, location or plateau | 1,298 (composition, aggregation) | Association only |
| A junction at one end | 357 (composition, aggregation, specialization) | A junction accepts none of the three |
| Between two concepts | 4: CommunicationNetwork to TechnologyInterface composition; Equipment to Material realization; Outcome to Plateau composition and aggregation | Not allowed |

Plus 54 cells with EA's network letters (`d`, `p`, `w`). EA omits flow from BusinessRole to TechnologyEvent.

So a relationship you can draw from the quick linker may be one the standard refuses, and a pair of concepts is not valid because the
linker offered it. Check relationships against the standard's table (the language file's `relationships.allowed`), which the
ArchiMate 3.1 ruleset applies as one rule over every connector. That the table allows a pair is permission, not evidence the
relationship is right: the table includes derivations the standard says may be wrong in a given model.

## 10. Checking a model: what the ruleset needs from EA

The ruleset is `rulesets/archimate-3/archimate-3_rules.yaml`. 2 of 4 rules in this ruleset use formats newer than 3.6.4, and on that server they report nothing or don't run as written. Use server 3.6.5 or later, because a clean result on 3.6.4 doesn't mean the model passes.

- Rule selectors use the stored name (`ArchiMate_Serving`), never the standard's name and never the qualified name.
- A relationship rule needs both ends to carry an ArchiMate stereotype. An element created without one (a plain UML class)
  is invisible to it.
- Elements bound to ArchiMate 2 are judged too, because the stored names match. Section 2 keeps new elements out of that state.
- A junction at either end of a connector sends the connector to the junction rule, not the table rule.
- Zero findings and zero matched elements read the same. Confirm a rule matched something before calling a model clean.
- The ruleset checks what the standard states. The shipped ArchiMate 3.1 ruleset's completeness rules (a process has a performer, a component has behavior, an actor has a role, a work package realizes a goal) are dropped, not kept as an open choice: 
  the standard does not require them, and there is no separate good-practice ruleset.

## 11. A short worked example (Westbrook Bank, fictitious)

To model "the Loan Origination System realizes the Automated credit check requirement":

1. Create a Motivation diagram: type `ArchiMate3::Motivation`.
2. Create the requirement: `ArchiMate3::ArchiMate_Requirement`, named "Automated credit check" (stored as a Class).
3. Create the component: `ArchiMate3::ArchiMate_ApplicationComponent`, named "Loan Origination System" (stored as a Component).
4. Connect them with `ArchiMate3::ArchiMate_Realization` from the component to the requirement (stored as a Dependency).
5. Read back `t_xref` for both elements and the connector; each should carry `FQName=ArchiMate3::`.

This is an illustration. Use your own technology and model, and your own element names.

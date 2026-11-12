# Modeling VDML in Sparx EA

How Sparx EA's built-in Value Delivery Modeling Language technology represents the language described in the VDML language skill, measured on EA 17.1 build 1716 (2026-10-21). The technology is a built-in technology whose definition is encrypted, so every fact here was read from what EA creates and draws, not from the definition file; `ea.yaml` records the source of each fact. Examples use Westbrook Bank, a fictitious bank, as an illustration: substitute your own enterprise. Nothing here assumes you have any particular model.

## Version

The language skill describes **VDML 1.0** (OMG formal/2015-10-05). OMG published **VDML 1.1** in 2018; it is not covered. EA's technology states no version, and nothing measured here settles which one it implements: its stereotypes are the 1.0 class names, no 1.1 addition was identified, its display name is the 1.0 document's title, and its model patterns carry no version. Treat it as probably 1.0 and as unconfirmed. The ruleset is a 1.0 ruleset.

## 1. What EA gives you

- **Technology:** Value Delivery Metamodel (VDML) (technology id `VDML`), under Resources > MDG Technologies > System Technologies. The Resources tab lists 25 rows, 24 distinct stereotypes: 17 for elements and 7 for connectors.
- **Eight diagram types,** one for each diagram kind of the standard (section 5).
- **Model patterns:** ten ship with EA (`vdml-role-collaboration`, `vdml-activity-network` and two variants, `vdml-capability-management` and others). Their endpoints were read to see how Sparx draws each link; their toolbox pages and quick links were not harvested. On screen (EA 17.1 build 1716, 2026-11-04) the tab lists 8 toolboxes, one per diagram type; the Activity Network toolbox has one VDML page (Role Swimlane, Activity, Store, Pool, Port (Boundary), Port (Floating), Deliverable Flow, Internal Port Delegation), and from an Activity the quick links offer nothing language-specific, only Create Multiple Elements. The other seven toolboxes were not opened and only one quick-link source was tried.
- **No validation.** EA creates any link you ask for. A deliverable flow between two Stores, an assignment from a Store, a Role in a Store: all were accepted. Use the ruleset.

## 2. What VDML can and cannot say in EA

The language skill names 71 concepts (63 VDML classes and 8 from SMM). EA gives 17 a stereotype (15 directly, 2 as `BoundaryPort` with a tag value), 7 a shared stereotype, 6 a connector stereotype, and has no home for the other 41 (`ea.yaml`, `concepts`). A VDML model in EA is a faithful picture of the collaboration, activity network, capability and measurement views, not a complete value delivery model.

| In the standard | In EA |
|---|---|
| ValueDeliveryModel, Scenario, DelegationContext, AnalysisContext | **No stereotype.** The package or the model is the container; the analysis contexts, and the per-scenario measurements and role assignments that hang from them, cannot be recorded. |
| BusinessItem, BusinessItemLibrary and the other libraries, definitions and categories | **No stereotype.** The name of a `DeliverableFlow` stands for the deliverable. A capability's category is the capability's parent. |
| ResourceUse, ValueAdd, ValuePropositionComponent, ValueElement | **No stereotype.** A `ValueProposition` is a bare element; record its components and weights in its description. |
| Position, Party, Member, Performer | **All `Role`.** The kind is the type of the Collaboration that contains the Role; EA does not record it. |
| Person | `Actor`. |
| InputPort, OutputPort | `BoundaryPort` with the tag `InputOutput` = `Input` or `Output`. |
| Duration, quantity, offset, planning percentage, batch size, heat index, release control | **No tag.** None of the standard's numeric properties has a tag. |
| Measures, measurements, observations (SMM) | **No stereotype**; `MeasuredCharacteristic` is the only measurement element. |
| Expression, Operand, condition | The tag `withCondition` (true or false) on a `BoundaryPort` says a condition exists; the condition has no home. |

## 3. Concepts: what to create

Create the element with the stereotype below. Stored names are bare (`Role`); the qualified form `VDML::Role` is what you pass when creating by script.

| Standard concept | EA stereotype | EA metaclass | Tagged values |
|---|---|---|---|
| Activity | `Activity` | Object | `isExpand` |
| Actor, Person | `Actor` | Object | none |
| Role (and Position, Party, Member, Performer) | `Role` | Object | `isExpand` |
| Role drawn as a swim-lane | `RoleSwimlane` | ActivityPartition | none |
| Collaboration | `Collaboration` | Object | none |
| BusinessNetwork | `BusinessNetwork` | Object | none |
| Community | `Community` | Object | none |
| OrgUnit | `OrgUnit` | Object | `isExpand` |
| CapabilityMethod | `CapabilityMethod` | Object | none |
| Store | `Store` | Object | none |
| Pool | `Pool` | Object | none |
| InputPort, OutputPort (of an Activity, Store or Pool) | `BoundaryPort` | Port | `InputOutput` (Input, Output, Either; default Either), `withCondition` |
| Port of a Collaboration | `Port` | Part | `InputOutput` |
| ValueProposition | `ValueProposition` | Object | none |
| Capability (definition or category) | `Capability` | Object | `isExpand`, `showExpand` |
| CapabilityOffer | `CapabilityOffer` | Port | none |
| MeasuredCharacteristic | `MeasuredCharacteristic` | Object | none |

- **Ports are children, not siblings.** `BoundaryPort` and `CapabilityOffer` are `Port` elements. Created in a package EA refuses them (`Invalid parent for Port (Package)`); create each as a child of its host. EA accepted an Activity, a Store, a Pool, an OrgUnit and a Collaboration as hosts for both; it was not tested whether it refuses others, and it does not apply the standard's limits, so those are yours to keep (the ruleset reports a breach): a port belongs to an Activity or Store (or Pool); a CapabilityOffer belongs to an OrgUnit; a Collaboration's own port is the `Port` stereotype, not a `BoundaryPort`. `Port` is a Part element and needs no host.
- **Set the port direction.** A new `BoundaryPort` or `Port` has `InputOutput` = `Either`. Set it to `Input` or `Output`: EA draws input ports open and output ports filled, and the ruleset judges only ports that say which they are.
- **Containment of resources is the element's parent.** Create a Store, a Pool, a CapabilityMethod or an offer as a child of its OrgUnit. In an Activity Network, Sparx's patterns nest the Store, the Pool and each Activity in the swim-lane of its Role instead (an element has one parent), and the ruleset accepts a Store or Pool in a swim-lane. A capability hierarchy is the same: create the child capability under its parent (the diagram then draws it inside).
- **CapabilityOffer has two forms.** The Resources tab lists it twice. A plain `VDML::CapabilityOffer` creates the Port form (a hexagon on the border of its OrgUnit, as in Sparx's capability-management pattern). The stereotype also binds on an Object created with `StereotypeEx`, so it can sit in a package with no host. The Port form is the one Sparx's pattern uses.

## 4. Connectors: what to connect

Seven connector stereotypes, all UML Dependencies. Several are standard classes that EA draws as a connector:

| Standard concept | EA connector | How you draw it |
|---|---|---|
| DeliverableFlow between Activities | `DeliverableFlow` | from the output `BoundaryPort` of the giving Activity (or Store) to the input `BoundaryPort` of the receiving one. Name the connector for the deliverable. Tag `isTangible` (True, default; False for an intangible flow) |
| DeliverableFlow between Roles (Role Collaboration diagram) | `DeliverableFlow` | Role to Role, with the deliverable's name |
| ValueProposition provider and recipient | `DeliverableFlow` | Role to ValueProposition for the provider, ValueProposition to Role for the recipient (direction read from Sparx's pattern) |
| InputDelegation, OutputDelegation | `InternalPortDelegation` | from a Collaboration's `Port` to the `BoundaryPort` of one of its Activities (input), or from the Activity's `BoundaryPort` to the `Port` (output) |
| Assignment | `RoleAssignment` | from the Actor, Collaboration or Role that fills the Role, to the Role |
| A Collaboration's Role | `RoleContainment` | from the Role to its Collaboration. Sparx's collaboration-structure pattern also joins a Collaboration that fills a Role in another Collaboration the same way |
| Offer to what supports it (8.8, not a standard class) | `CapabilityAssociation` | between a `CapabilityOffer` and a `CapabilityMethod`, `Store` or `Pool`, either direction (dashed) |
| CapabilityDependency | `CapabilityDependency` | between a `CapabilityOffer` and a `CapabilityMethod` (the dotted dependency of Capability Management). In the standard, CapabilityDependency joins two capability definitions through a deliverable; Sparx's pattern does not use it that way |
| MeasurementRelationship | `MeasurementRelationship` | between two `MeasuredCharacteristic` elements; tag `influence` (positive, negative) |

The standard's own multiplicities (a port takes at most one flow, a Role has one container, a ValueProposition has one provider and one recipient) are not enforced by EA. The ruleset checks them where it can (section 8).

## 5. Which diagram

| Standard diagram kind | EA diagram type | Draw |
|---|---|---|
| Role Collaboration (8.2) | `VDML::RoleCollaboration` | Roles of one Collaboration and the `DeliverableFlow` connectors between them; no flow between Activities of the same Role |
| ValueProposition Exchange (8.3) | `VDML::ValuePropositionExchange` | ValueProposition and Role, joined by the provider and recipient flows |
| Activity Network (8.4) | `VDML::ActivityNetwork` | Roles as `RoleSwimlane`, Activities, Stores, Pools, ports on their borders, flows, delegations to the Collaboration's `Port`s |
| Collaboration Structure (8.5) | `VDML::CollaborationStructure` | Collaborations, their Roles, Actors, containment and assignment |
| CapabilityLibrary (8.6) | `VDML::CapabilityLibrary` | `Capability` elements, child inside parent |
| Capability Heatmap (8.7) | `VDML::CapabilityHeatmap` | the same; EA has no heat index tag, so the heat state is not drawn from data |
| Capability Management (8.8) | `VDML::CapabilityManagement` | OrgUnit with its offers on the border and its methods, Stores and Pools inside; association and dependency links |
| Measurement Dependency (8.9) | `VDML::MeasurementDependency` | `MeasuredCharacteristic` elements and `MeasurementRelationship` links |

All eight are stored as `Logical` diagrams whose `StyleEx` carries `MDGDgm=VDML::<name>`. Toolbox pages were read only for the Activity Network type (see section 1). The standard says colors carry no meaning, and EA's technology states no layout convention.

An example, as an illustration (substitute your own enterprise). Westbrook Bank's home loan: a BusinessNetwork "Home Loan Exchange" with Roles "Lender", "Home Buyer" and "Appraiser", each joined to it by `RoleContainment`; a Community "Home Buyers" assigned to the Home Buyer Role and an OrgUnit "Westbrook Bank" assigned to the Lender Role; Role Collaboration flows "Loan Application", "Loan Offer", "Appraisal Report" (tangible) and "Closing Guidance" (`isTangible` False); a ValueProposition "Home Loan Proposition" from Lender to Home Buyer; an Activity Network in a Collaboration "Home Loan Delivery" with Activities "Take application", "Assess credit" and "Issue offer", a Store "Application queue", a Pool "Credit analysts", input and output ports with flows between them, and the Collaboration's `Port`s delegated to the first and last Activity; an OrgUnit "Credit Risk" with a CapabilityOffer "Credit assessment", supported by the CapabilityMethod "Standard credit assessment" and the Pool, with a dependency on the OrgUnit "Compliance"'s offer "Identity verification"; and MeasuredCharacteristics "Time to decision", "Customer satisfaction" and "Analyst availability" with negative influences.

## 6. What EA does that the standard does not

- **`BoundaryPort` is one stereotype for both port directions**, and `Either` is a third state the standard does not have.
- **`RoleSwimlane`** draws a Role as a swim-lane (an Activity Partition); it is a drawing device, not a second kind of Role.
- **`CapabilityAssociation`** and the way `CapabilityDependency` is used are the diagram's links, not classes of the standard.
- **`isExpand` and `showExpand`** are display tags (the expand button), not VDML properties. EA also adds a hidden tag `_Bezier` to a CapabilityDependency connector.
- **One flow stereotype** serves three diagram kinds.

## 7. Traps found

1. **A new port has no direction.** `InputOutput` defaults to `Either`; set it to `Input` or `Output`. The ruleset judges only ports that say which they are.
2. **EA does not stop a wrong link.** All 24 seeded defect scenarios (a flow between two Stores, an assignment starting at a Store, a Role in two Collaborations, a proposition with two providers, a Store with no owner, a port on a Collaboration, and the rest) were created without complaint.
3. **Port-kind elements need a host, and EA does not choose it for you.** The same `BoundaryPort` is accepted on an OrgUnit or a Collaboration, where the standard would not put an Activity port; the ruleset reports it.
4. **The Resources tab lists `CapabilityOffer` twice** (a Port form and an Object form); create the Port form on an OrgUnit.
5. **One `Role` for Position, Party, Member and Performer.** Nothing records which kind a Role is; the rules that depend on the kind (a BusinessNetwork has only Party Roles, a Community only Members) cannot be checked. Name the Role for what it is, and put it in the right Collaboration.
6. **Flow direction on a ValueProposition is a convention read from Sparx's pattern**, not a rule of the standard: provider into the proposition, recipient out.
7. **Stored names are shared with other technologies.** `Activity`, `Pool` and `Collaboration` are also stereotype names in EA's BPMN technologies, `Capability` in Project Management and `Port` in IFML (measured from the plain-file technologies that ship with EA; the encrypted built-ins were not searched). A validation rule that selects by stored name alone cannot tell them apart; only the cross-reference (`FQName`) does. A rule that also names the EA type (`types`, since the engine of 2026-10-21) separates them only where the technologies store the name on different EA types: VDML stores `Activity`, `Pool`, `Collaboration` and `Capability` as Objects and `Port` as a Part, and BPMN 2.0 stores Activity as an Activity and Pool as an ActivityPartition; the EA types of the other technologies' elements were not read. Keep BPMN or IFML content in separate packages if you validate by stored name alone.
8. **Creating by script needs the qualified type** (`VDML::Role`, with a host for a port). A name EA does not know is refused with `Invalid type` (measured for 53 concept names of the language file). What an unqualified name does was not measured.
9. **Do not read the toolbox or the list as complete.** Only the Activity Network toolbox was read; the 24 stereotypes come from the Resources tab.
10. **Containment is the element's parent.** The validator reads it (since the 2026-10-21 engine): a port must sit in an Activity, Store or Pool, a Store or Pool in an OrgUnit or a Role swim-lane, an offer and a method in an OrgUnit. It cannot compare two containers, so which Collaboration holds an Activity, and whether the Role in whose swim-lane an Activity sits is in that Collaboration, are not checked (section 8).
11. **EA has no place for `isIntermediate`.** The language skill says to set a port's `isIntermediate` flag explicitly. EA has no tag for it: a new `BoundaryPort` has only `InputOutput` and `withCondition`, and a new Store has no tags (measured on EA 17.1 build 1716, 2026-11-05). So whether a port is intermediate cannot be recorded in EA, and the ruleset has no rule for VDML-FLOW-004 or VDML-FLOW-009, which depend on it.

## 8. Checking a model

The VDML ruleset (`rulesets/vdml-1/vdml-1_rules.yaml`, 17 rules) checks that a deliverable flow, a port delegation, a role assignment and a role containment join only the elements EA's technology draws them between; that a port, given its direction, has at most one flow and no flow the wrong way, and at most one incoming and one outgoing delegation; that a Role has at most one container; that a ValueProposition has at most one provider and one recipient; and where things sit: a port in an Activity, Store or Pool, a Store or Pool in an OrgUnit or a Role swim-lane, an offer and a method in an OrgUnit. It implements 10 of the 89 rule ids of the language skill that are marked static or partial (plus two more by the same rules), each only in the part EA stores. The rest, 77 ids, have no rule: EA has no home for most of the standard's properties, the kind of a Role is not recorded, and the rules that compare two containers (the Collaboration of an Activity and of its Role) need links EA does not store.

8 of 17 rules in this ruleset use formats newer than 3.6.4, and on that server they report nothing or don't run as written. Use server 3.6.5 or later, because a clean result on 3.6.4 doesn't mean the model passes.

The ruleset doesn't flag every new Store. A Store or Pool inside an OrgUnit or a Role swim-lane gets no finding, and one placed straight in a package gets an error from `VDML1-CARD-005`.

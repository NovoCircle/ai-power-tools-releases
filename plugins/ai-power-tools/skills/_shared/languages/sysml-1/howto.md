# Modeling SysML 1.5 in Sparx Enterprise Architect

How to model the language of the SysML skill the way Sparx's built-in SysML technology does it. Measured on EA 17.1 build 1716 by creating one element, port, part, attribute, operation, connector and diagram of each kind and reading the stored rows back; `ea.yaml` holds the same facts as data. Westbrook Bank appears only as an illustration; substitute your own organization, and do not assume your repository holds any sample model.

**Version.** This guide describes SysML **1.5** (OMG formal/17-05-01), the version EA's technology shows in its Resources tab. OMG has since published SysML 1.6 (2019), SysML 1.7 (2024) and SysML v2 (2025), which is a new language rather than a revision. The newer versions are not described here and were not researched; a model made with them may use concepts this guide does not cover.

## What the technology looks like

- **The technology id is `SysML1.4`, and EA's Resources tab calls it "SysML 1.5".** The qualified form that creates an object is `SysML1.4::<name>`. `SysML1.5::`, `SysML 1.5::` and `SysML::` create nothing. Older SysML 1.1, 1.2 and 1.3 technologies are installed beside it and accept the same prefix with their own id (`SysML1.3::block`); do not use them for a SysML 1.5 model. Two names, `unit` and `quantityKind`, exist only in the 1.3 technology.
- **63 stereotype names, 86 rows** in the Resources tab (a name is listed once for each metaclass it applies to). **9 diagram types**, one per standard diagram kind (Activity, Block Definition, Internal Block, Package, Parametric, Requirement, Sequence, State Machine, Use Case, in a group named "SysML 1.5" on the tab). Toolbox pages and quick links were read on screen on EA 17.1 build 1716, 2026-11-04: nine toolboxes; a block definition diagram shows the pages SysML Block Definition, SysML Block Relationships, SysML Patterns, SysML Deprecated and SysML Common. The Block Definition page includes `Unit` and `Quantity Kind`; trap 10 says `unit` and `quantityKind` bind only under SysML1.3, and what those toolbox items create was not tried. From a block the quick links offer SysML targets (Actor, Block, Constraint Block, Requirement, Property and others), with aggregation, composition, allocate, generalization and nesting links; three target types were opened and only one source was tried.
- **SysML is a UML profile, so the stereotypes sit on UML elements.** A block is a Class, a requirement a Requirement element, a test case an Activity, a proxy port a Port, a flow property a Part, a conform a Generalization, a satisfy a Dependency, a rationale a Note.
- **Stored names are bare and in EA's own case.** `t_object.Stereotype` holds `block`, `requirement`, `satisfy`, `Expose`, `FlowProperty`, `ProxyPort`; the qualified form `SysML1.4::block` is in `t_xref` (row named `Stereotypes`, `FQName`) and is what you pass to create an element or set `StereotypeEx`. EA matches the name after the prefix without regard to case (`SysML1.4::Block` stores `block`) but a selector or query compares the stored string exactly. **The Resources tab shows `Flow Property`, `Full Port` and `Proxy Port` with a space; the stored and bindable names have none** (`FlowProperty`, `FullPort`, `ProxyPort`), and the spaced spellings create nothing.
- **129 of the skill's 179 concept names have no stereotype.** 91 are UML names the standard reuses (Class, Port, Property, Activity, Association, Generalization, and so on); EA models them with its own element and connector types. The 38 SysML concepts without a stereotype are part, reference and value properties and association blocks (classifications, not stereotypes), Unit, QuantityKind and the primitive value types, the enumerations, ConstraintParameter, AbstractRequirement, the diagram interchange elements, and the nested-port and change-event concepts.
- **EA adds 13 stereotypes the skill does not have**: `RequirementRelated`, `allocated`, `moe`, `objectiveFunction`, `effbd`, `streaming`, `nonStreaming` and the six requirement kinds `functionalRequirement`, `interfaceRequirement`, `performanceRequirement`, `physicalRequirement`, `designConstraint`, `extendedRequirement` (the standard's Annex E names them as examples).

## Which diagram type for which standard diagram

The nine standard diagram kinds each have an EA diagram type. The token is `SysML1.4::<Name>`; EA stores `MDGDgm=SysML1.4::<Name>;` in `t_diagram.StyleEx`. A token EA does not know creates a plain Class diagram with no `MDGDgm`, so check the stored value. The spaced spellings (`SysML1.4::Block Definition`) also bind.

| Standard diagram | EA diagram type | Stored `Diagram_Type` |
|---|---|---|
| Block definition (bdd) | `SysML1.4::BlockDefinition` | Logical |
| Internal block (ibd) | `SysML1.4::InternalBlock` | CompositeStructure |
| Parametric (par) | `SysML1.4::Parametric` | CompositeStructure (same as the internal block diagram; only `MDGDgm` tells them apart) |
| Requirement (req) | `SysML1.4::Requirement` | Custom |
| Package (pkg) | `SysML1.4::Package` | Package |
| Activity (act) | `SysML1.4::Activity` | Activity |
| Sequence (sd) | `SysML1.4::Sequence` | Sequence |
| State machine (stm) | `SysML1.4::StateMachine` | Statechart |
| Use case (uc) | `SysML1.4::UseCase` | Use Case |

## How to say each concept

| To model | Create | Set |
|---|---|---|
| Block | a Class, `block` (EA accepts `block` on any of Class, Component, Requirement, Node, Activity, StateMachine, Change and Interaction; use a Class) | `isEncapsulated` |
| Interface block; constraint block | a Class, `InterfaceBlock`; a Class, `constraintBlock` | |
| Value type | a DataType (or Enumeration, PrimitiveType), `ValueType` | `unit`, `quantityKind` (references, stored empty) |
| Part, reference and value property | a Part element, child of the block, with no stereotype; the classification comes from aggregation and type | type, aggregation |
| Proxy port; full port | a Port element, child of the block, `ProxyPort`; `FullPort` | the port's type (an interface block for a proxy port) |
| Flow property | a Part element, child of the block or interface block, `FlowProperty` | `direction` (in, out, inout, none; EA creates inout) |
| Directed feature | `DirectedFeature` on a Part, a Port, an attribute or an operation | `featuredirection` (provided, required, providedrequired; created provided) |
| Item flow | an InformationFlow connector, `itemFlow` | `itemProperty` |
| Binding connector | a Connector, `BindingConnector` (also on Assembly and Delegate) | |
| Connector, participant, distributed, constraint property; bound reference; end path multiplicity; adjunct, classifier behavior property; nested connector end | a Part element, child of the block, with the stereotype of that name (`connectorProperty`, `participantProperty`, `distributedProperty`, `constraintProperty`, `BoundReference`, `EndPathMultiplicity`, `AdjunctProperty`, `ClassifierBehaviorProperty`, `NestedConnectorEnd`) | `end` (participant), `boundEnd`, `principal`, `propertyPath` as text |
| Property-specific type | a Class, `PropertySpecificType` | |
| Requirement | a Requirement element, `requirement` (or a kind: `functionalRequirement`, `interfaceRequirement`, `performanceRequirement`, `physicalRequirement`, `designConstraint`, `extendedRequirement`) | `id` and `text`; the kinds also `source`, `risk`, `verifyMethod` |
| Test case | an Activity, `testCase` (also on an Interaction, a StateMachine, a Class and an operation) | `Verdict` |
| Satisfy, verify, derive, refine, trace, copy | a Dependency connector, `satisfy`, `verify`, `deriveReqt`, `refine`, `trace`, `copy`, from the client (tail) to the supplier (arrowhead) | `refine` has four property-path tags |
| Allocate; allocate activity partition | an Abstraction connector, `allocate`; an ActivityPartition, `allocateActivityPartition` | |
| View, viewpoint, stakeholder | a Class, `view`; a Class, `viewpoint`; a Class, `Stakeholder` | `viewpoint`, `stakeholder`, `purpose`, `concern`, `concernList`, `language`, `method`, `presentation` as text |
| Conform; expose | a Generalization, `conform`, from the view to the viewpoint; a Dependency, `Expose`, from the view to the element | |
| Rationale, problem, element group | a Note, `rationale`, `problem`, `ElementGroup` | |
| Control operator | an Activity (or Interaction, Class, operation), `controlOperator` | |
| Rate, continuous, discrete, probability | a ControlFlow or ObjectFlow connector with the stereotype, or an ObjectNode or ActivityParameter element (a child of an activity); the qualified type for a connector is refused, so create the flow and set `StereotypeEx` | `rate` (rate, continuous, discrete) or `probability`, on a flow or an activity parameter |
| No buffer, overwrite, optional | `noBuffer`, `overwrite` on an ObjectNode, ActivityParameter, CentralBufferNode or ExpansionNode; `optional` on an ObjectNode or ActivityParameter | |
| Model | a package, `model` (set on the package's element) | |
| Deprecated flow port; flow specification | a Port element, `FlowPort`; an Interface, `flowSpecification` | `direction` |

Illustration (Westbrook Bank is fictitious): the requirement `Withdrawal Time` (`performanceRequirement`, `id` R-111, `text` "A withdrawal completes within ten seconds.") is derived from `Withdraw Cash` by a `deriveReqt`, satisfied by the block `Cash Dispenser` through a `satisfy`, and verified by the test case `Verify withdrawal time` through a `verify`. The view `Branch Operations View` conforms to the viewpoint `Operations Viewpoint` and exposes the block `Automated Teller Machine`. Substitute your own system.

## Containment

- **A port belongs to a block.** EA stores that in `ParentID`. A Port cannot be created in a package ("Invalid parent for Port (Package)"); create `ProxyPort`, `FullPort` or `FlowPort` as a child element of the block.
- **A property belongs to a block too.** A Part element can be created in a package (EA leaves `ParentID` zero), but a part, flow property or other property stereotype belongs under its block, so create it as a child.
- Activity nodes (`ObjectNode`, `ActivityParameter`, `CentralBufferNode`, `ExpansionNode`) are children of an activity.
- The type of a port, part or property is its classifier. Set it so that a reader (and a tool) can see which interface block a proxy port exposes and which block a part is typed by.

## What EA does that the standard does not

- Thirteen extra stereotypes (listed above), among them the requirement kinds and the trade-study names of Annex E.
- `requirement` carries the tagged values `id` and `text`; the standard's Requirement has the attributes `id` and `text`.
- `block` and the other Class-family stereotypes are accepted on eight element types; `satisfy` and the other dependency stereotypes on eleven connector types.
- Creating an `effbd` Activity makes EA add a child activity diagram of its own.
- Generic stereotypes `RequirementRelated` and `allocated` apply to every element, attribute, operation and connector type.

## What the standard has that EA does not

No stereotype for 129 of the skill's concept names: the classifications of properties (part, reference, value, association block), the primitive value types and the unit and quantity kind library (Unit, QuantityKind), ControlValue, VerdictKind and the other enumerations, ConstraintParameter, AbstractRequirement, the nested-port and change-event concepts, and the diagram interchange elements. No check that a conform runs from a view to a viewpoint, that a satisfy ends at a requirement, that a proxy port is typed by an interface block, or that an allocate is an Abstraction: EA's API created every connector the sample defects use.

## Traps

1. **The prefix is `SysML1.4`, the tab says 1.5.** `SysML1.5::block` creates nothing. `SysML1.3::block` creates a block of the older technology, which looks the same.
2. **Spaced display names do not bind.** Use `FlowProperty`, `FullPort`, `ProxyPort`.
3. **The case is EA's, and it is mixed.** `block`, `satisfy`, `requirement` are lower case; `Expose`, `Stakeholder`, `ElementGroup`, `FlowProperty`, `ProxyPort`, `FullPort`, `ValueType`, `InterfaceBlock`, `BindingConnector`, `ElementImport` start with a capital. A query or rule that gets one letter wrong matches nothing and reports a clean model.
4. **A port needs a block as parent.** Creating `SysML1.4::ProxyPort` in a package fails.
5. **A stereotype is accepted on the wrong metaclass.** `block` binds to a Node, a Component, a Requirement or an Activity; `requirement` binds to a plain Class (which then has no `id` and `text` tags). Nothing in the technology stops it.
6. **The qualified type does not always give the connector type you expect.** `SysML1.4::satisfy` creates a Dependency; set the metaclass first (`Abstraction`) and `StereotypeEx` if you want an Abstraction. `allocate` is kept on an Abstraction, Dependency, Realization or Substitution but EA accepts it silently on a Usage and stores no stereotype.
7. **A second stereotype is invisible to a query.** Giving a port `ProxyPort,FullPort` stores `ProxyPort` in `t_object.Stereotype` and both in `t_xref`; a validator that reads `Stereotype` sees a proxy port only. The same holds for `continuous,discrete` and `noBuffer,overwrite` (measured).
8. **`id` and `text` are tagged values, lower case, stored empty.** A requirement with no id is valid to EA. An id is not checked for uniqueness.
9. **The activity stereotypes depend on the metaclass.** `rate` on an ObjectNode carries no tag; on an ActivityParameter or a flow it carries `rate`. A qualified create for a connector is refused for these four names.
10. **`unit` and `quantityKind` are not SysML 1.5 stereotypes in EA.** They bind only under SysML1.3.
11. **Case does not matter on creation, and does on selection.** `SysML1.4::Block` creates a `block`; a query for `Block` finds nothing.
12. **Names are generic.** `model`, `view`, `block`, `copy`, `trace`, `problem`, `rate`, `optional`, `overwrite`, `streaming`, `moe` are common words; whether another technology in the same model declares them was not measured. Confirm that a clean validation also matched more than zero SysML objects.
13. **The toolbox items were listed, not tried.** Everything here was created through EA's API; a toolbox item may set more (a port's behavior flag, a part's aggregation).
14. **A stereotype selector does not tell metaclasses apart; a rule can.** `block` on a Class and on a Node look the same to a stereotype selector, and so do a satisfy stored as a Dependency and as an Abstraction. A generalization, an association, a control flow or a plain UML class carries no stereotype, so a rule names it by EA type: `selector.types` and `selector.connector_types` select by `Object_Type` and `Connector_Type`, and an end, a table row or a container is written `type:<Object_Type>` (`type:Part`, `type:Decision`). Measure the names: `Part`, `Port`, `Requirement`, `ObjectNode`, `ActionPin`, `Aggregation` and `Generalization` are EA's own.

## Checking a model

10 of 21 rules in this ruleset use formats newer than 3.6.4, and on that server they report nothing or don't run as written. Use server 3.6.5 or later, because a clean result on 3.6.4 doesn't mean the model passes.

The ruleset `rulesets/sysml-1/sysml-1_rules.yaml` has twenty-one rules. Eleven read stereotypes: a conform runs from a view to a viewpoint (two rules, one per end); an expose starts at a view; a view conforms to one viewpoint; a requirement has an id and a text; a copy joins two requirements; a deriveReqt, a satisfy and a verify end at (or, for deriveReqt, also start at) a requirement; a deprecated flow port has a direction. Ten read EA types and where an element sits: a requirement is not an end of an association or a generalization; a probability starts at a decision node or an object node; a full port is not bound to a part; a property-specific type has at most one generalization; the connector, distributed and classifier-behavior property stereotypes sit in a block (a distributed property also in a value type); an interface block holds no activity, state machine or interaction; a requirement holds no block or value type. Eight of the ten are partial: each leaves out part of the skill's rule. They are the rules of the skill that the validator can state over what EA stores. The others need what a rule cannot yet read: what a part, port or property is typed by, operations and attributes, multiplicity, a second stereotype, built-in columns such as Status, numbers, what a generalization joins when only one end is named, and 'no element of this kind may exist'. Review those rules by hand until the validator can read them.

Two cautions for the new rules. A rule that forbids a requirement at an end must list every other kind at that end, because an endpoint condition says 'one of'; an end that carries another technology's stereotype is therefore reported. And a container is the element a property is attached to (`ParentID`), then its package: a property created in a package instead of in its block is reported by the three property rules.

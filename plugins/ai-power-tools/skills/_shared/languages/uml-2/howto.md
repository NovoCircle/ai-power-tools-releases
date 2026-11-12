# Modeling UML 2.5.1 in Sparx Enterprise Architect

How to model the language of the UML skill the way EA's own UML does it. Measured on EA 17.1 build 1716 by creating one element of every type, one connector of every type and kind and one diagram of every type, and reading the stored rows back; `ea.yaml` holds the same facts as data. Westbrook Bank appears only as an illustration; substitute your own organization, and do not assume your repository holds any sample model.

**Version.** This guide describes UML **2.5.1** (OMG formal/17-12-05), the latest version; OMG lists no later one.

## What EA's UML looks like

- **UML is not an MDG technology in EA.** There is no `<TECH>::<name>` form for elements or connectors and no stereotype prefix. EA reports the internal technologies `UML2` and `EAExtended` as loaded, but neither is a prefix that creates anything.
- **An element is told apart by its EA type** (`t_object.Object_Type`): `Class`, `Interface`, `Component`, `UseCase`, `Actor`, `Node`, `State`, `Action`, `Activity`... **A connector is told apart by its connector type** (`t_connector.Connector_Type`): `Generalization`, `Association`, `Realisation`, `Dependency`, `UseCase`, `ControlFlow`, `StateFlow`... Almost none of them carries a stereotype. EA has **64 element types that can sit in a package, 9 that need a parent element and 27 connector types**.
- **EA names are not always the standard's.** A lifeline is a `Sequence` element; a transition is a `StateFlow` connector; a message is a `Sequence` connector; an actor-to-use-case association is a `UseCase` connector; a combined fragment is an `InteractionFragment`; an interaction use is an `InteractionOccurrence`; a state invariant is an `InteractionState`; fork and join are both `Synchronization`; realization is stored as `Realisation` (British spelling).
- **One EA type serves several UML kinds, and the kind is a stored number** (`NType`): the initial and final states are both `StateNode` (3 is initial, EA's default for a new one; 4 is final); every kind of event is an `Event`; every combined-fragment operator is an `InteractionFragment`; input, output and value pins are all `ActionPin`; every action kind is an `Action`.
- **The UML keywords are plain text.** `include`, `extend`, `import`, `access`, `merge`, `substitute`, `use`, `call`, `send`, `create`, `instantiate`, `derive`, `refine`, `trace` are free strings in the connector's stereotype column. The Standard Profile stereotypes are capitalized and bound to a profile (`StandardProfileL2::Call`, `::Send`...); a model can hold either spelling, so look for both.

**Toolbox and quick links** (read on screen, EA 17.1 build 1716, 2026-11-04, one Class diagram). The toolbox pages are Class (Class, Interface, Data Type, Enumeration, Primitive, Signal, Association), Class Relationships (Associate, Generalize, Compose, Aggregate, Association Class, Realize, Template Binding), Composite Parts (Part, Port, Expose Interface, Assembly, Connector, Delegate) and UML Standard Profile (Auxiliary, Call, Create, Destroy, Focus, Implementation Class, Instantiate, Realization, Send, Specification, Type, Utility; "Create" appears twice), then EA's generic pages. From a Class the quick links offer Artifact, Class, Data Type, Enumeration, Information Item, Interface, Primitive Type, Signal and Note; the Class submenu holds aggregation, association, association class, calls, composition, generalization, instantiates, substitution, template binding and their reverse readings. Two target types were opened, one source was tried, and the toolboxes of the other diagram types were not opened.

## Which diagram type for which standard diagram

`Package.Diagrams.AddNew(name, <string>)` stores **any** text as the diagram type and checks nothing. Use the strings EA's own UML model patterns store:

| Standard diagram | EA diagram type string | Notes |
|---|---|---|
| Class | `Logical` | `Class` is also stored as given |
| Object | `Object` | |
| Package | `Package` | |
| Composite structure | `CompositeStructure` | |
| Component | `Component` | |
| Deployment | `Deployment` | |
| Profile | `Profile` | no EA sample holds a profile diagram; this string is created but not confirmed |
| Use case | `Use Case` | with a space |
| Activity | `Activity` | |
| State machine | `Statechart` | |
| Sequence | `Sequence` | |
| Communication | `Collaboration` | `Communication` is stored as given but no sample uses it |
| Timing | `Timing` | |
| Interaction overview | `InteractionOverview` | |

None of these is an MDG diagram type: `StyleEx` holds no `MDGDgm=`.

## How to say each concept

| To model | Create | Set |
|---|---|---|
| Class, abstract class | an element of type `Class` | `Abstract = 1` for abstract |
| Interface; data type; primitive type; enumeration; signal | `Interface`; `DataType`; `PrimitiveType`; `Enumeration`; `Signal` | |
| Property (attribute) | an attribute of the class (`t_attribute`), not an element | name and type; a part of a composite structure is a `Part` element under the owner |
| Operation, parameter | an operation of the class (`t_operation`) with parameters (`t_operationparams`) | |
| Enumeration literal | an attribute of the `Enumeration` element | |
| Association | a connector of type `Association` | direction `Source -> Destination` for a navigable end |
| Aggregation, composition | a connector of type `Aggregation` | end flag `SourceIsAggregate` or `DestIsAggregate` = 1 (shared) or 2 (composite); EA's patterns also store `SubType` `Weak` or `Strong` |
| Generalization | `Generalization`, from the specific to the general | |
| Interface realization, component realization, realization | `Realisation` | one type for all three |
| Dependency; usage; abstraction; substitution | `Dependency`; `Usage`; `Abstraction`; `Substitution` | keyword as a plain stereotype string: `use`, `call`, `create`, `instantiate`, `send`; `derive`, `refine`, `trace`; `substitute` |
| Package import, access, merge | a `Package` connector (or a `Dependency`) | stereotype string `import`, `access`, `merge` |
| Package, model | a `Package` element; the model is the repository root | |
| Stereotype, metaclass, profile | a `Class` with the stereotype `stereotype` (`EAUML::stereotype`) or `Metaclass` (`StandardProfileL2::Metaclass`); a `Package` with `profile` | `Extension` connector from the stereotype class to the metaclass class |
| Actor; use case | `Actor`; `UseCase` | |
| Actor-to-use-case association | a connector of type `UseCase` | |
| Include; extend | a connector of type `UseCase` | stereotype `include` with `SubType` `Includes`; stereotype `extend` with `SubType` `Extends` |
| Component; port; connector; assembly; delegation | `Component`; `Port` (child of its owner); `Connector` between parts and ports; `Assembly` between a `ProvidedInterface` and a `RequiredInterface` (children of the components); `Delegate` between ports | |
| Collaboration; collaboration use | `Collaboration`; `CollaborationOccurrence`, joined by a `Collaboration` connector | |
| Node, device, execution environment | `Node`; `Device`; `ExecutionEnvironment` (a child of the node that hosts it) | |
| Artifact; deployment specification | `Artifact`; `DeploymentSpecification` | |
| Deployment; manifestation; communication path | `Deployment` (artifact to node); `Manifest`; `CommunicationPath` between nodes | |
| Information item; information flow | `InformationItem`; `InformationFlow` between elements | |
| Activity; action | `Activity`; `Action` as a child of the activity | all action kinds are `Action` |
| Pin | `ActionPin`, a child of the action | input, output and value pins are one type |
| Activity parameter node; object node | `ActivityParameter`, `ObjectNode` as children of the activity; `CentralBufferNode`; `Object` with the stereotype `datastore` for a data store | |
| Initial, final node | `StateNode` as a child of the activity: default (3) is initial, `Subtype = 4` is final | set `Subtype` before `Update` |
| Decision, merge | `Decision`, `MergeNode` | |
| Fork, join | `Synchronization` | one type serves both |
| Control flow, object flow, interrupting edge | `ControlFlow`, `ObjectFlow`, `InterruptFlow` | |
| Activity partition; interruptible region; expansion region | `ActivityPartition`; `InterruptibleActivityRegion`; `ExpansionRegion` (its `ExpansionNode` pins are children) | |
| Structured, conditional, loop node | `StructuredActivityNode`; `ConditionalNode`; `LoopNode` | |
| State machine; state; region | `StateMachine`; `State` (child of the machine or a state); `Region` (child of a state or a machine) | |
| Pseudostate | `StateNode` (child), `EntryPoint`, `ExitPoint` (children of a state), `Decision` or `Synchronization` | the kind is `NType` |
| Transition | `StateFlow` between states and pseudostates | |
| Event, trigger | `Event`; `Trigger` | event kind is `NType` |
| Interaction; lifeline; message | `Interaction`; `Sequence` (also `Boundary`, `Part`, `TimeLine`); a `Sequence` connector | |
| Combined fragment; interaction use; state invariant | `InteractionFragment`; `InteractionOccurrence`; `InteractionState` | operator is `NType` |
| Comment; constraint | `Note` joined by a `NoteLink`; a `Constraint` element or a constraint record | |
| Instance specification | `Object` | |

Concepts with no EA type found: the values and expressions (held as text), time and duration constraints and observations (EA refuses them), association class, reception, extension point, template parameters, generalization sets, execution specifications, gates as elements, the model and profile as element types. A model that needs them keeps them in text, notes or a convention of the project.

## What EA does that the standard does not

- **EA lets you put things where the standard forbids.** It accepted a `Port` under an Interface, an Actor, a UseCase or an Artifact; a `Region` under a Class, a Package or a Component; a `Class` under a Component or a Node; an `Extension` ending at a Package. It refuses some: an `Interaction` under an `Interaction`, an `ActionPin` or `ActivityParameter` under a Class, a `Port` under an Action or a Note.
- **EA has element types of its own** that are not UML: `Boundary`, `Entity`, `Requirement`, `Feature`, `GUIElement`, `Screen`, `Issue`, `Risk`, `Task`, `Change`, `Test`, `Report`, `Text`, `UMLDiagram`, `DiagramFrame`; and connector types `Nesting`, `NoteLink`, `InterruptFlow`.
- **Include and extend are not their own connector type**: they are `UseCase` connectors with a stereotype string and a `SubType`.
- **One connector type for aggregation and composition**, one for all realizations, one for all usages.
- **Nesting is a stored parent.** An element created with `AddNew` on another element has that element as its parent (`ParentID`); EA shows it nested.

## Traps found

1. **`AddNew` for a connector name EA does not know stores a `Dependency` with no error** (`Transition`, `InterfaceRealization`, `ComponentRealization`, `RoleBinding`, `ProtocolTransition`, `PackageImport`, `PackageMerge`, `ProfileApplication`, `AssociationClass`). Always read back `Connector_Type`.
2. **`AddNew` for an element name that matches another technology's stereotype creates that stereotype's element**, not the UML type: `Message` gives a Class bound to BPMN 1.1, `Operation` one bound to BPMN 2.0, `Slot` one bound to IFML, `Template` one bound to FACE, `Control` an Object bound to EAUML, `DataStore` an Object with `datastore`. Use the names in `ea.yaml` `element_types`.
3. **The diagram type string is not checked.** A typo creates a diagram of an unknown type.
4. **The kind of a state node, event or combined fragment is a number** that a rule or query cannot read by name (the validator does not read the stored kind number). Record the kind in the element name or a tagged value if a project needs to select by it.
5. **Keyword stereotypes can be cross-bound.** `activity` binds to BPMN 1.1, `model` to IEEE 1471, `dataType` and `enumeration` to GML, `information` to EPProfile, `protocol` to UAF. Select by the EA type, not by the keyword.
6. **A Statechart or Activity diagram that shows its owning StateMachine or Activity element refuses child elements placed outside the owner's box**: leave the owner off the diagram, or size it to hold its children.
7. **`Realisation` is spelled with an s in the stored type**, while `AddNew` also accepts `Realization`.

## Checking a model

The ruleset, `rulesets/uml-2/uml-2_rules.yaml`, checks 24 of the language skill's rules with the engine's rules by EA type and where-it-sits rules: what a generalization, a use case connector, an extension, an information flow, a communication path and a connector may join; what the keyword usages (`call`, `send`, `create`, `instantiate`) and the stereotyped package and use case relationships (`include`, `extend`, `import`, `access`, `merge`, `substitute`) may join; that control flows and object flows keep to control and object nodes; the edges of a decision and a merge node; where a port and a region may sit; and what a node may nest. It cannot read attributes and operations, multiplicities, typing, generalization chains, the kind of a pseudostate or action, or an element's own name or text, so most of the 530 checkable rules are review guidance, not machine checks.

25 of 25 rules in this ruleset use formats newer than 3.6.4, and on that server they report nothing or don't run as written. Use server 3.6.5 or later, because a clean result on 3.6.4 doesn't mean the model passes.

## An illustration (Westbrook Bank, fictitious)

Substitute your own model. Westbrook's account lifecycle: a `StateMachine` "Account lifecycle" holds a `StateNode` (initial, default), the `State`s "Open" and "Frozen" and a `StateNode` with `Subtype = 4` (final), joined by `StateFlow` connectors; "Open" holds two `Region` children. Its use case model: `Actor` "Teller", `UseCase` "Open Account" and "Verify Identity", a `UseCase` connector from the actor to "Open Account", and a `UseCase` connector with stereotype `include` and `SubType` `Includes` from "Open Account" to "Verify Identity".

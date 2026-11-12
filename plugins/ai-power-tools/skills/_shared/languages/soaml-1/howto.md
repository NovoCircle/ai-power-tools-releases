# Modeling SoaML 1.0.1 in Sparx Enterprise Architect

How to model the language of the SoaML skill the way Sparx's built-in technology (id `SoaML`) does it. Measured on EA 17.1 build 1716 by creating one element, port, attribute, connector and diagram of each kind and reading the stored rows back; `ea.yaml` holds the same facts as data. Westbrook Bank appears only as an illustration; substitute your own organization, and do not assume your repository holds any sample model.

**Version.** This guide describes SoaML 1.0.1 (OMG formal/12-05-10, May 2012); OMG lists no later version. EA's technology reports version 1.0 (`GetTechnologyVersion`), while its model patterns name the 1.0.1 namespace, so which of the two the technology follows is not settled here.

## What the technology looks like

- **25 stereotype names, 38 rows** in the Resources tab (a name is listed once for each metaclass it applies to), all in lower camel case: `participant`, `agent`, `servicePoint`, `requestPoint`, `serviceInterface`, `serviceChannel` and so on. **2 diagram types**: `SoaML` and `SoaMLSequence`. Toolbox pages and quick links were read on screen (EA 17.1 build 1716, 2026-11-04): the tab lists two toolboxes, "SoaML Component" and "SoaML Sequence". A diagram of type SoaML shows the pages UML Component, UML Component Relationships and SoaML Stereotypes (Agent, Attachment, Capability, Collaboration, Collaboration Use, Consumer, Expose, Message Type, Milestone, Participant, Port, Property, Provider, Request, Service, Service Channel, Service Contract, Service Interface, Services Architecture); the SoaML Stereotypes page has no item for `id`, `entity`, `specification`, `participantArchitecture`, `requestPoint` or `servicePoint`. From a participant the quick links offer nothing SoaML-specific (Requirement and the common list), and from a service interface only EA's generic class links. The SoaML Sequence toolbox was not read, and only two quick-link sources were tried. The tab's Diagram Types node holds one group, SoaML, with two types named "SoaML Component Diagram" and "SoaML Sequence Diagram".
- **SoaML is a UML profile, so the stereotypes sit on UML elements.** A participant is a Class (or a Component), a service interface a Class (or an Interface), a service contract and a services architecture are Collaborations, a service or request is a Port, a message type a Class, a DataType or a Signal, a milestone a Note, an expose a Dependency, a service channel a Connector.
- **Stored names are bare.** `t_object.Stereotype` holds `participant`; the qualified form `SoaML::participant` is in `t_xref` (row named `Stereotypes`, `FQName`) and is what you pass to create an element or set `StereotypeEx`. EA matches the name after `SoaML::` without regard to case and stores the canonical lower camel case form (`SoaML::Participant` stores `participant`).
- **Nine concepts of the standard have no stereotype**: Catalog, Categorization, Category, Category Value, Node Descriptor, Free Form Descriptor, Free Form Value, Motivation Element and Motivation Realization. A model that uses the standard's categorization or business motivation link has to use plain UML elements (or another technology) for them.
- **EA adds three stereotypes the skill does not have**: `entity`, `specification` and `participantArchitecture`.

## Which diagram type for which standard view

The standard defines no diagram type; the skill's views are the informal ones its examples use. EA offers two.

| View (skill) | EA diagram type | Stored as |
|---|---|---|
| Services Architecture, Service Contract, Participants, Service Interface, Capabilities, Service Data, Categorization, Business Motivation | `SoaML::SoaML` | Component diagram, `MDGDgm=SoaML::SoaML;` |
| Choreography (an interaction owned by a contract or a service interface) | `SoaML::SoaMLSequence` | Sequence diagram, `MDGDgm=SoaML::SoaMLSequence;` |

## How to say each concept

| To model | Create | Set |
|---|---|---|
| Participant | a Class, `participant` (also available on a Component) | |
| Agent | `agent` on a Class, a Component or an Actor | the class's active flag (EA does not set it; the standard says an agent is always active) |
| Service (a port that offers a service) | a Port child of the participant, `service` or `servicePoint` | the type (classifier) of the port: a service interface or an interface. `servicePoint` has `connectorRequired` (default true); `service` has no tag |
| Request (a port that consumes a service) | a Port child of the participant, `request` or `requestPoint` | the type of the port; the port's Conjugated setting (EA does not set it). `requestPoint` has `connectorRequired`; `request` has no tag |
| Port refinement | a Port child, `port` | `connectorRequired` true or false |
| Service channel | a Connector between two ports, `serviceChannel` | |
| Service interface | `serviceInterface` on a Class or an Interface | realized and used interfaces, parts, protocol: plain UML |
| Provider, consumer | `provider`, `consumer` on an Interface (or a Class for a composite contract) | |
| Service contract | a Collaboration, `serviceContract` | `isStrict` (empty until set); roles typed by provider, consumer or service interface |
| Services architecture | a Collaboration, `servicesArchitecture` | |
| Collaboration; collaboration use | `collaboration` on a Collaboration; `collaborationUse` on a CollaborationOccurrence | `isStrict` (a use defaults to true) |
| Capability | a Class, `capability` | |
| Expose | a Dependency, `expose`, from the service interface to the capability | |
| Message type | `messageType` on a DataType (the standard's usual choice), a Class or a Signal | `encoding` |
| Attachment | `attachment` on an attribute of a message type (or on a Part) | `encoding`, `mimeType` |
| Identifying property | `id` or `property` on an attribute (or on a Part) | `isID` (EA creates it true; the standard's default is false) |
| Milestone | a Note, `milestone` | `progress`: a whole number, free text in EA, empty until set |

Illustration (Westbrook Bank is fictitious): the participant `Account Opening` owns the request port `Request identity check`; the participant `Identity Verifier` owns the service port `Perform identity check`; a `serviceChannel` joins the two ports. The service interface `Identity Verification Service Interface` is exposed to the capability `Verify applicant identity` by an `expose`. Substitute your own participants and services.

## Containment

- **A port belongs to a participant.** EA stores that in `ParentID`. A Port cannot be created in a package ("Invalid parent for Port (Package)"); create it as a child element of the participant.
- A Part (a role or typed property in a structure) is also a child element of its class. `attachment`, `id` and `property` can sit on a Part as well as on an attribute.
- The type of a port is its classifier. Set it so that a reader (and a tool) can see which service interface the port offers or consumes.

## What EA does that the standard does not

- Two names for each port kind: `service` and `servicePoint`, `request` and `requestPoint` (the profile's names and the metamodel's names). The samples EA ships use `servicePoint` and `requestPoint`.
- `entity`, `specification` (a participant that is only a specification) and `participantArchitecture`.
- `connectorRequired` is a tagged value on `port`, `servicePoint` and `requestPoint` only.
- The sequence diagram type `SoaMLSequence`.
- EA accepts a SoaML stereotype on a whole family of element types (Class, Component, Node, Activity, Requirement) alike; it does not check which metaclass the standard extends.

## What the standard has that EA does not

No stereotype for the categorization package (Catalog, Category, Category Value, Categorization) or for the business motivation link (Motivation Realization, Motivation Element). No check that a service channel joins a Request and a Service, and no check that an expose runs from a service interface to a capability: EA's API created every connector the sample defects use.

## Traps

1. **Two names for one concept.** A model can hold `service` and `servicePoint` ports side by side. A rule or query about services has to name both (and `request` and `requestPoint` for requests).
2. **A port needs a parent.** Creating `SoaML::servicePoint` in a package fails; create it under the participant.
3. **`attachment`, `id` and `property` are not elements.** They apply to attributes (and Parts). Creating one in a package fails with "Invalid type".
4. **The stereotype does not set the flags the standard states.** A new `agent` has the active flag clear; a new `request` or `requestPoint` is not conjugated. Set them by hand. (Measured on objects created through the API; the toolbox items were not tried.)
5. **`isID` is true by default.** The standard's default is false; EA creates the tag true on both `id` and `property`.
6. **A stereotype is accepted on the wrong metaclass.** `participant` binds to a Requirement or a Node; only a few metaclasses (Interface, DataType, Signal, Note, Actor, Collaboration) are selective. Nothing in the technology stops a `serviceInterface` on a Requirement.
7. **Case does not matter on creation, and does on selection.** `SoaML::Participant` creates a `participant`; a query for `Participant` finds nothing.
8. **Realizations, usages and generalizations carry no stereotype.** Most of SoaML's structure (a service interface realizes the provider interface and uses the consumer interface, a participant has typed ports, a contract has typed roles) is plain UML that a stereotype selector cannot see. A rule can now select a connector by EA connector type (`Realization`, `Usage`, `Generalization`), but it still cannot read what a port, part or role is typed by or the operations a class owns.
9. **A stereotype selector does not tell metaclasses apart; a rule can.** `serviceInterface` on a Class and on an Interface look the same to a stereotype selector. A rule that names `types:` beside the stereotype (EA's own element type, for example `Interface`) tells them apart, since the engine of 2026-10-21. No rule of the ruleset does so yet.
10. **Names are generic.** `entity`, `id`, `port`, `property`, `capability`, `specification` and `collaboration` are common words; whether another technology in the same model declares them was not measured. Confirm that a clean validation also matched more than zero SoaML objects.

## Checking a model

The ruleset `rulesets/soaml-1/soaml-1_rules.yaml` has three rules: a service channel joins a request or requestPoint port to a service or servicePoint port (either way round); an expose runs from a serviceInterface to a capability; a milestone has a progress value. The ruleset was generated before the engine of 2026-10-21 (selection by EA type and by EA connector type, and the where-it-sits rules) and has not been regenerated since. So the limits it records for "plain connector" (5 rules) and "metaclass not visible" (2 rules) no longer hold in the validator, but the ruleset has no rule for them, and whether each can be stated in full has not been worked out. A port's owner (`ParentID`) can be read now, too; the "in an architecture" part of SOAML-CHAN-001 is not written. What the validator still cannot read: typing, owned operations and attributes, the flags that are not tagged values (a port's conjugation, a class's active flag), and an either-or condition. Review the rules without a ruleset rule by hand.

2 of 3 rules in this ruleset use formats newer than 3.6.4, and on that server they report nothing or don't run as written. Use server 3.6.5 or later, because a clean result on 3.6.4 doesn't mean the model passes.

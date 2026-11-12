# Modeling BPMN 2.0.2 in Sparx Enterprise Architect

How to model the language of the BPMN 2.0.2 skill the way Sparx's built-in technology (id `BPMN2.0`, shipped as `BPMN 2.0 Technology.xml`, file version 1.0.7) does it. Measured on EA 17.1 build 1716 by creating one element, connector and diagram of each kind and reading the stored rows back; `ea.yaml` holds the same facts as data. Westbrook Bank appears only as an illustration; substitute your own organization, and do not assume your repository holds any sample model.

**Version.** This guide describes BPMN 2.0.2 (OMG formal/13-12-09, January 2014), the version the language skill describes; EA's technology file is version 1.0.7 and its UML profile 1.5. The ISO edition of BPMN was not compared.

## What the technology looks like

- **57 stereotypes**, 380 tagged values, 5 diagram types, 4 toolboxes, 12 model templates. 56 of the 57 stereotypes can be created; `MessageFlowAssociation` is declared with no metaclass and EA refuses it. The Resources tab lists **59 rows** in the BPMN2.0 profile and does not list `MessageFlowAssociation`: the tab shows only stereotypes that apply to a metaclass. `StartEvent`, `IntermediateEvent` and `EndEvent` appear twice each (stand-alone and edge-mounted), and the `GlobalTask` declaration shows as a second `Activity` row. Every other harvested name is on the tab. Measured on EA 17.1 build 1716, 2026-11-04. The diagram types (5) and toolboxes (4) on the tab match this list.
- **The standard's kinds are tagged values, not stereotypes.** A task, a sub-process, a call activity, an event sub-process, a transaction and an ad-hoc sub-process are all the stereotype `Activity`; the five gateways are `Gateway`; every event trigger is a value of `eventDefinition` on `StartEvent`, `IntermediateEvent` or `EndEvent`. 110 concept names of the standard (`Task`, `ServiceTask`, `SubProcess`, `BoundaryEvent`, `ExclusiveGateway`, `Process`, `ChoreographyTask` and so on) are not stereotypes: EA refuses to create an element of that type.
- **Stored names are bare.** `t_object.Stereotype` holds `StartEvent`; the qualified form `BPMN2.0::StartEvent` is in `t_xref` (row named `Stereotypes`, `FQName`) and is what you pass to create an element or set `StereotypeEx`.
- **Defaults are stored when you create the element.** A new `Activity` is `taskType = Abstract`, `activityType = Task`; a new `IntermediateEvent` is `eventDefinition = Message`, `catchOrThrow = Catch`; a new `Gateway` is `gatewayType = Exclusive`, `gatewayDirection = Unspecified`. Set the tags you mean; do not rely on the default meaning what the diagram suggests.

## Which diagram type for which standard diagram

| Standard diagram (skill) | EA diagram type | Opens toolbox |
|---|---|---|
| Process | `BPMN2.0::Business Process` (with a space) | Business Process |
| Collaboration | `BPMN2.0::Collaboration` | Collaboration |
| Choreography | `BPMN2.0::Choreography` | Choreography |
| Conversation | `BPMN2.0::Conversation` | Conversation |
| none (EA only) | `BPMN2.0::BPEL` | Business Process |

All five are EA Analysis diagrams (`t_diagram.Diagram_Type = Analysis`); the technology is in `StyleEx` as `MDGDgm=BPMN2.0::<name>;`. The standard has no BPEL diagram; clause 14 is a mapping.

**Start from a container element.** Creating a `BusinessProcess`, `BPELProcess`, `CollaborationModel`, `ChoreographyModel` or `ConversationModel` element also creates a diagram of the matching type, named after the element, as its child (composite diagram). Draw the process or collaboration on that diagram.

## How to say each concept

| To model | Create | Set |
|---|---|---|
| Private, public, executable process | `BusinessProcess` | `processType` Private or Public; `isExecutable` true marks it executable (no default; empty until set) |
| Collaboration; choreography; conversation (container) | `CollaborationModel`; `ChoreographyModel`; `ConversationModel` | the last two generalize the first |
| Task kinds | `Activity` | `taskType`: Service, Send, Receive, User, Manual, BusinessRule, Script, Abstract |
| Sub-process; ad-hoc; transaction; event sub-process | `Activity` | `activityType` Sub-Process, and `adHoc`, `isATransaction`, `triggeredByEvent` true |
| Call activity | `Activity` | `isACalledActivity` true, `calledActivityRef` |
| Loop, multi-instance | `Activity` | `loopCharacteristics` Standard or MultiInstance |
| Start, intermediate, end event | `StartEvent`, `IntermediateEvent`, `EndEvent` | `eventDefinition` (start: None, Message, Timer, Conditional, Signal, Escalation, Error, Compensation, Multiple, ParallelMultiple; intermediate adds Link and Cancel; end adds Terminate and Cancel); `catchOrThrow` on intermediate events |
| Boundary event | `IntermediateEvent`, edge-mounted (below) | `cancelActivity` true interrupts, false does not |
| Gateway | `Gateway` | `gatewayType` Exclusive, Inclusive, Parallel, Complex, Event; `gatewayDirection` Converging, Diverging, Mixed, Unspecified; for Event: `eventGatewayType`, `instantiate` |
| Pool; black-box pool | `Pool` | `blackBoxPool` true for a black box |
| Lane | `Lane` | nested in its pool (or lane) |
| Data object, input, output | `DataObject` | `dataInOut` None, Input, Output |
| Data store | `DataStore` | |
| Message | `Message` | |
| Group; text annotation | `Group`; `TextAnnotation` | |
| Choreography task, sub-choreography, call choreography | `Choreography` | `choreographyType` Task or Sub-Process; `numberOfParticipants` 2, 3 or 4; `isACalledChoreography` |
| Conversation, sub-conversation, call conversation | `Conversation` | `isComposite`, `isACallConversation` |
| Correlation, resources, services | `CorrelationKey`, `CorrelationProperty`, `CorrelationPropertyRetrievalExpression`, `CorrelationSubscription`, `CorrelationPropertyBinding`, `Resource`, `ResourceRole` (`role`), `Interface`, `Operation`, `Error`, `Escalation`, `Signal` | their own tagged values |

Connectors: `SequenceFlow` (`conditionType` None, Default or Expression, with `conditionExpression`), `MessageFlow`, `Association`, `DataAssociation` with the subtypes `DataInputAssociation` and `DataOutputAssociation`, `ConversationLink`. A message flow is stored from sender to receiver.

## Containment

EA stores containment in `ParentID`, as the shipped patterns do:

- A `Pool` is a child of its `CollaborationModel` (or `BusinessProcess`); a `Lane` is a child of its pool; an activity or event is a child of its lane, or of the pool when it has no lane. One white-box pool is one process; a shipped sample also sets the pool's `processRef` to a `BusinessProcess`.
- EA's API accepted every connector the defect samples use, including ones the standard forbids (a sequence flow into a start event, a message flow leaving a start event); nothing in the technology stops a wrong connector, so check with the ruleset.

## Events have two forms

`StartEvent`, `IntermediateEvent` and `EndEvent` each exist twice. **Stand-alone** (metaclass Event) sits in a pool or lane. **Edge-mounted** (metaclass ObjectNode) is a child of the activity it is attached to; that is how EA stores a boundary event (and a start or end event attached to the edge of an expanded sub-process). The toolbox offers both on the Intermediate Event item (Stand-alone, Edge-mounted). Through the API: create a stand-alone event with the metaclass `Event` and set `StereotypeEx` to `BPMN2.0::StartEvent`; create an edge-mounted one as a child element of the activity with the qualified type. Creating the qualified type directly in a package fails with "Invalid parent for ObjectNode (Package)". Placing an edge-mounted event on a diagram through the API: EA refused rectangles that straddled the host's lower edge and accepted ones inside the host's rectangle.

## What EA offers when you connect

EA's quick linker follows the shipped rule table (927 rows). Measured against the standard's Tables 7.3 and 7.4 in stored form:

- **Sequence flow:** for stand-alone ends EA offers every cell of Table 7.3 (25 pairs); in EA's names that is 23 quick-link pairs, because `Activity` stands for both task and sub-process and `Choreography` for the choreography activities (16 process pairs and 7 choreography pairs). It also offers pairs that involve an edge-mounted start or end event (for example an activity to an edge-mounted start event); these are the standard's exception for events attached to an expanded sub-process, so they are not errors.
- **Message flow:** EA offers `StartEvent` to `Activity` (the standard says a start event never sends), and offers `Choreography` as either end (the standard names pools, activities and events). It does not offer an intermediate event to a start event, and offers `Participant` only to `Participant`.
- **Conversation link:** EA offers `Conversation` to `Conversation`; the standard says a link has exactly one conversation node.
- The quick linker is a menu, not a check; see Containment for what the API accepts.
- Checked on screen (EA 17.1 build 1716, 2026-11-04): from an Activity the menu offered Message Flow to a Pool, Sequence Flow to a Gateway, Data Output and Data Input Association to a Data Object, Conversation Link to a Conversation and Association to a Message, the same as the rule table's Activity rows (5 pairs compared). The Collaboration toolbox showed the pages and items the harvest lists (14 elements, 4 connectors, 24 types). The other three toolboxes were not opened.

## What EA does that the standard does not

- `BPELProcess` and the `BPEL` diagram, for models meant to generate BPEL.
- Composite diagrams (above), model templates, runtime attributes such as `state` and `numberOfInstances` as tagged values.
- A choreography task is limited to 2, 3 or 4 participants; the standard allows two or more.

## What the standard has that EA does not

No `LaneSet`, no `GlobalChoreographyTask`, no separate data object reference or data store reference, no `ImplicitThrowEvent`, no `Definitions`, `Import` or extension elements. A boundary event is an edge-mounted intermediate event, not a stereotype.

## Traps

1. **A concept name is not a stereotype.** `BPMN2.0::Task`, `::ServiceTask`, `::BoundaryEvent`, `::ExclusiveGateway` do not exist. Create `Activity` or `Gateway` and set the tag.
2. **The default is not your intent.** A new intermediate event is a catching message event; a new activity is an abstract task; a new gateway has unspecified direction.
3. **Stereotype names are shared.** EA's BPMN 1.0 and 1.1 technologies declare the same short names (`Activity`, `Gateway`, `StartEvent`, `Pool`, `Message`, and others). A rule that selects `Gateway` judges them all.
4. **A boundary event is indistinguishable by stereotype.** A selector on stereotype and tags cannot tell it from an event in normal flow. A rule can: it names the EA type beside the stereotype (an edge-mounted event is an `ObjectNode`, a stand-alone event an `Event`) and can read the activity it is attached to (`contained_in`), since the engine of 2026-10-21.
5. **Executable is one tag on one element.** Only `BusinessProcess.isExecutable` says a process is executable; the activities inside carry nothing.
6. **Creating a composite element creates a diagram.** A model that holds many `BusinessProcess` elements holds as many diagrams.
7. **Placing a boundary event on a diagram can fail.** On EA 17.1 build 1716, adding one boundary timer on an activity to a diagram through the server returned an EA error ("The server threw an exception"), with `add_element_to_diagram` and with the bulk call. This was seen once. The event still exists in the model: if it happens, tell the user which events are missing from the picture, and add them in EA by hand, on the activity's border, with their outgoing flows.

## Checking a model

5 of 44 rules in this ruleset use formats newer than 3.6.4, and on that server they report nothing or don't run as written. Use server 3.6.5 or later, because a clean result on 3.6.4 doesn't mean the model passes.

The ruleset for this language (`rulesets/bpmn-2/bpmn-2_rules.yaml`) checks which flow nodes sequence and message flows may join, the incoming and outgoing flows of events and gateways, and the required tagged values of correlation and service elements. It has no rule for containment (which pool or lane an element is in), boundary-event rules, data associations, rules the standard limits to executable processes (except that a public process is not executable), or the WS-BPEL mapping. The ruleset was generated before the engine of 2026-10-21, which can read where an element sits (`contained_in`, `contains_count`) and select by EA type, so containment and boundary-event rules can now be written; none has been. The rules that follow a reference, need graph analysis or compare a value across elements still cannot be stated, so the ruleset leaves those rules out.

## A worked example, as an illustration

Westbrook Bank, a fictitious bank, takes a loan application: a `CollaborationModel` "Loan Application Collaboration" with two `Pool` children, "Applicant" and "Westbrook Bank", the second with two `Lane` children. Applicant: a `StartEvent`, an `Activity` (`taskType` Send) "Submit loan application", an event-based `Gateway` (`gatewayType` Event, `gatewayDirection` Diverging), three catching `IntermediateEvent`s (Message, Message, Timer) and three `EndEvent`s. Bank: a message `StartEvent`, a User `Activity`, a Service `Activity` with an edge-mounted timer `IntermediateEvent` (`cancelActivity` false), an exclusive diverging `Gateway`, and message `EndEvent`s. Sixteen `SequenceFlow`s (one with `conditionType` Expression, one Default) and three `MessageFlow`s run from sender to receiver. The collaboration's own Collaboration diagram carries all of it.

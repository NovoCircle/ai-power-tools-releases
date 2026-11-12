# Modeling IT4IT in Sparx EA with the IT4IT pack

This is how to model The Open Group's IT4IT reference architecture in Sparx EA with the IT4IT pack, version 3.0-draft.3, as built and measured on EA 17.1 build 1716 (2026-11-04). **The pack is read from The Open Group's public 3.0 draft of February 2022, and it makes no claim of conformance.** The pack is not affiliated with or endorsed by The Open Group. The published standard is version 3.0.1, and its names or lists may differ. Examples use Westbrook Bank, an invented bank, as an illustration: substitute your own products and names.

## 1. What the pack gives you

- **Technology:** `IT4IT`, with the profile `IT4ITArchitecture`. It is our technology, not one Sparx ships.
- **Three diagram types,** for the levels the standard standardizes: IT4IT Level 1 Overview, IT4IT Level 2 Value Stream, and IT4IT Level 3 Architecture. Levels 4 and 5 aren't standardized, so use the Level 3 type.
- **Eleven toolbox pages:** one for each of the nine functional groups with defined content, IT4IT Concepts and Lines, and IT4IT Supporting Functions.
- **107 shapes and 9 lines.** Components are blue rectangles, key data objects black circles, and the nine backbone data objects orange circles, as in the standard's simplified notation. Section 7 lists where the pack draws something differently.

## 2. Install it

Use the pack's file, `pack/IT4IT_MDG.xml`, beside this how-to:

- **For a team sharing a model:** Specialize > Publish Technology > Import MDG Technology, then Import To Model. EA has no scripted route that imports a file this way. Type or paste the path with no trailing character. A stray tab gives "unable to open primary document entity", and that error then repeats for later files until you cancel the dialog and open it again.
- **For one machine:** `install_mdg(scope="user")`. This wasn't measured for this pack.

Don't use `install_mdg(scope="embedded")`, which stores no toolbox pages. **Restart EA after importing,** because the toolbox may not switch to the pack's pages before that. Installing a newer build leaves the older profile loaded, so disable the old one in Manage Technology.

## 3. Shapes: what to create

Each shape keeps your own name. A shape named "Mobile Banking incidents" is still the standard's Incident, so a check can read it whatever you call it.

| Concept | Stored stereotype | EA type | Fields |
|---|---|---|---|
| Functional component (35) | `IT4IT_FC_<Name>` | Component | None |
| Data object (46) | `IT4IT_DO_<Name>` | Class | The standard's key fields, 2 to 14 each, 292 in all. None needs a value |
| Value stream | `IT4IT_ValueStream` | Activity | None |
| Value stream stage | `IT4IT_Stage` | Activity | None |
| Scenario | `IT4IT_Scenario` | Class | None |
| Stakeholder | `IT4IT_Stakeholder` | Actor | None |
| Functional group | `IT4IT_Group` | Class | `IT4ITGroup`, a list of the five Level 1 groups and the nine Level 2 groups with components |
| Capability | `IT4IT_Capability` | Class | None |
| Essential service | `IT4IT_EssentialService` | Class | None |
| Supporting function group (5) | `IT4IT_SG_<Name>` | Class | None |
| Example data object (14) | `IT4IT_EX_<Name>` | Class | None |

New shapes start at the shared layout standard's sizes: a group, component, or value stream at 150 by 90 and growing with what it holds, a data object or other shape at 100 by 70, and a stakeholder at 45 by 90. A data object's circle sits within its 100 by 70.

`<Name>` is the standard's name with spaces and `&` removed: `IT4IT_FC_DiagnosticsRemediation`. To create a shape by script, use the qualified form as the type: `IT4ITArchitecture::IT4IT_DO_Incident`.

**Each group's components and the data objects they control:**

| Group | Component: data object |
|---|---|
| Strategy | Policy: Policy; Strategy: Strategic Theme; Strategy: Strategic Objective; Enterprise Architecture: Architecture Roadmap Item; Enterprise Architecture: Architecture Blueprint; Enterprise Architecture: Value Stream |
| Portfolio | Portfolio Backlog: Portfolio Backlog Item; Proposal: Scope Agreement; Product Portfolio: Digital Product |
| Develop | Product Backlog: Product Backlog Item; Requirement: Requirement; Product Design: Product Design; Source Control: Source; Pipeline: Pipeline; Build Package: Build Package; Release Composition: Product Release; Release Composition: Product Release Blueprint |
| Test | Test: Test Case; Test: Test Plan; Defect: Defect |
| Consume | Consumption Experience: Interaction; Identity: Identity; Identity: Entitlement; Offer: Service Offer Catalog; Offer: Service Offer; Order: Order; Order: Subscription; Chargeback: Chargeback Contract; Chargeback: Chargeback Record |
| Fulfill | Change: Change; Fulfillment Orchestration: Desired Product Instance; Resource: Resource; Fulfillment: Fulfillment Book; Usage: Usage Record |
| Support | Service Level: Service Contract; Service Level: KPI; Incident: Incident; Problem: Problem; Knowledge: Knowledge Item |
| Assure | Configuration: Actual Product Instance; Monitoring: Service Monitor; Monitoring: Log; Event: Event; Diagnostics & Remediation: Runbook |
| Financial Management | Cost Modeling: Cost Model; Investment: Budget Item |

**The value streams are one shape, and you name them.** The standard's seven are Evaluate, Explore, Integrate, Deploy, Release, Consume, and Operate.

**The supporting functions are examples only.** The draft describes these five functions without defining components, fields, or links. It names example data objects under four of them, which the pack offers with a dashed gray drawing and "(example)" in the name. No check reads them. Their names are short forms we chose from the draft's wording, and the guide records what the draft writes.

| Group | Example data objects |
|---|---|
| Governance Risk & Compliance | Risk Assessment, Risk, Vendor Risk, Audit Finding, Compliance Evidence, Risk Issue |
| Workforce Management | Employee, Job Profile and Roles, Team, Resource Allocation |
| Sourcing & Vendor Management | Vendor, Contract, Purchase Order |
| Intelligence & Reporting | Metric |
| Collaboration & Communication | None named |

## 4. Lines: what to connect

Draw a line from the first kind of shape to the second. Hovering over a shape and dragging its arrow offers only the lines the standard has for that pair.

| Line | EA type | From, to |
|---|---|---|
| Data Relationship | Association | Data object, data object. Only pairs the standard lists are offered |
| System of Record Integration | InformationFlow | Component, component. Name it for the data object transferred |
| Engagement Integration | InformationFlow | Component, component. Name it for the action |
| Supports | Dependency | Component, value stream |
| Depends On | Dependency | Value stream, value stream |
| Executed For | Association | Value stream, scenario |
| Lists Stakeholder | Association | Stage, stakeholder |
| Lists Data Object | Association | Stage, data object |
| Supported By | Association | Capability, component |

Put the "how many" on a Data Relationship's end fields. The standard writes `1:n` to mean at most one on the first side and many on the second. No check reads these yet. To create a line by script, use the EA type and set `StereotypeEx` to the qualified form.

## 5. What goes inside what

Five relationships are nesting, as the standard draws them. Place the shape inside its container in the Browser:

- A data object inside the component that controls it.
- A component inside its group, and a Level 2 group inside its Level 1 group.
- A stage inside its value stream.
- An essential service inside its component.

A data object directly in a package is fine, and so is a component in no group, because a partial model is valid.

**A stage doesn't hold data objects here.** The standard's Figure 87 draws a stage's data objects inside it, but an element has one parent, and a data object's parent is its component. Use Lists Data Object for a stage, because nesting a data object under a stage gets an error.

## 6. Which diagram

| The standard's level | Diagram type | What it shows |
|---|---|---|
| Level 1 | IT4IT Level 1 Overview | Value streams, groups, components. The standard's text says Level 1 is drawn without data objects and relationships, though its Figure 7 shows them. Hide those lines if the diagram gets too busy |
| Level 2 | IT4IT Level 2 Value Stream | One value stream: its scenarios, stages, stakeholders, and participating data objects |
| Level 3 | IT4IT Level 3 Architecture | One group or component: data objects, their links, and the flows between components |

## 7. What the pack adds that the standard doesn't define

These are tool choices, not additions to the standard. The guide records how the standard draws each one:

- **The group list** on the group shape, which lets you name a group as you like and still have it checked.
- **The drawing of three things.** The pack draws a value stream as a chevron where the standard's simplified notation has a blue block arrow, a group as a gray frame where it has a blue rounded rectangle, and every component in blue where it draws a secondary component gray.
- **A stick figure for a stakeholder,** at the standard's actor size, where the standard's figures draw a box.
- **Dotted integration lines.** They follow the standard's text, and its figures draw dashes.
- **The "(example)" shapes,** drawn so they can't be mistaken for defined data objects.

## 8. What the standard has that the pack doesn't

- **No list of data flows.** The individual flows are only in the standard's figures. The pack gives the two line types and no list.
- **No conversion to or from ArchiMate.** The standard maps its concepts to ArchiMate (for example, a functional component is an Application Function), and the guide records that as guidance. The standard's own ArchiMate model file won't load as pack shapes.
- **No shapes for Value Network, System of Record, System, or Process.** The model as a whole is the value network, and the guide describes the others.
- **Figure 75's other lines.** The guide lists lines among groups, capabilities, processes, essential services, and integrations that the pack has no line for.

## 9. Traps

1. **The Browser shows the stored name:** `«IT4IT_DO_Incident» Mobile Banking incidents`. That's normal: the Properties window shows "Incident".
2. **The same name means different things.** Thirteen names are both a component and a data object, such as Incident and Change, and the toolbox shows the component as "Incident Component". Strategy and Test are also both a group and a component, and Consume is both a group and a value stream.
3. **Name, Description, Status, and Version repeat EA's own boxes** in many data objects. Leave the field blank when EA's box says the same.
4. **A line to an ArchiMate shape goes unchecked.** You can draw one, and no rule judges it.

## 10. Checking a model

The IT4IT ruleset, `rulesets/it4it/it4it_rules.yaml`, has 72 rules. They check that two data objects link only where the standard lists a link, which is a warning because the standard allows local links. They also check that each data object isn't inside the wrong component, that a component sits only in a group or a package, that a group holds only its own components and has a name on its list, and that each line joins the right kinds of shape.

62 of 72 rules in this ruleset use formats newer than 3.6.4, and on that server they report nothing or don't run as written. Use server 3.6.5 or later, because a clean result on 3.6.4 doesn't mean the model passes.

**A check reports what's wrong, never what's missing.** The standard says data objects "can" relate, so a clean result on a partial model doesn't mean the model is complete. A clean result also doesn't mean conformance to the published standard, because these rules are read from the draft. Everything else needs a person: naming style, a Digital Product reaching its Service Offer, when a flow counts as a system of record integration, and what a tool or a practice must do.

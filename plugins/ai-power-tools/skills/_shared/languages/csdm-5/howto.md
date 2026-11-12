# Modeling CSDM 5 in Sparx EA with the CSDM 5 for EA pack

This is how to model ServiceNow's Common Service Data Model (CSDM) 5 in Sparx EA with the CSDM 5 for EA pack, version 1.0.0, as built and measured on EA 17.1 build 1716 (2026-11-04). The pack is not affiliated with or endorsed by ServiceNow. Examples use Westbrook Bank, an invented bank, as an illustration: substitute your own services and names.

**Read this first:**

- **A clean check result doesn't mean your model matches ServiceNow.** It means the model follows the CSDM rules a check can read. CSDM is one vendor's guidance, and its sources don't fully agree with each other.
- **Nothing moves data between EA and ServiceNow.** No records are imported, exported, or kept in step.
- **A shape's link and record id are entered by a person, and they can go stale.** If a ServiceNow record changes or goes away, nothing updates the shape.
- **A concept may not exist on your platform.** Several arrive through plugins or store apps.

## 1. What the pack gives you

- **Technology:** `CSDM5`, with the profile `CSDM5`. It's our technology, not one Sparx ships.
- **One diagram type:** CSDM Diagram. CSDM's figures are views of one model, so one canvas serves them all.
- **Eight toolbox pages:** one for each of CSDM's seven domains, and CSDM - Relationships for the lines.
- **76 shapes and 30 lines.** Shapes use the domain colors from CSDM's own figures.

Start where CSDM does: Foundation, then Crawl, Walk, Run, and Fly. You don't need every page at first.

## 2. Load it

Use the pack's file, `pack/CSDM5_MDG.xml`, beside this how-to:

1. In EA, choose Specialize > Publish Technology > Import MDG Technology.
2. Type or paste the file's path, with no trailing character.
3. Leave Import To Model selected, and choose OK.

The technology then travels with your model, for everyone who opens it. Use this route: EA's script call `ImportTechnology` loaded the technology and its diagram type on this file but stored no shapes (measured on the same build). Installing it for one machine only wasn't measured. To upgrade, disable the older build in Manage Technology, because importing a newer one leaves the older profile loaded.

## 3. Shapes: what to create

Each shape keeps your own name. A shape named "Online Banking - Production" is still an Application Service, so a check can read it whatever you call it.

| Page | Shapes |
|---|---|
| Foundation | Value Stream, Value Stream Category, Value Stream Stage, Business Process, Contract, Product Model, Application Model, System Component Model, Software Component Model, Service Offering Model, Firmware Model, AI System Product Model, Service Model, Software Model, Content Product Model, AI Content Product Model, Contract Model, Facility Model, Hardware Model, Consumable Model, Enterprise Good Model, Product Feature, Software Bill of Materials (SBOM), CMDB Group, Company, Business Unit, Department, Location, Building, Group, User, Team, Knowledge |
| Ideation and Strategy | Product Idea, Planning Item, Strategic Plan, Strategic Priority, Goal, Target |
| Design and Planning | Business Capability, Business Application, Information Object |
| Build and Integration | SDLC Component, AI System Digital Asset, AI Model Digital Asset, AI Dataset Digital Asset, AI Prompt Digital Asset |
| Service Delivery | Service Instance, Application Service, Data Service Instance, Connection Service Instance, Network Service Instance, Operational Process Service Instance, Facility Service Instance, Network Function, API, Application, Network Function Application, AI Function, AI Application, Operational Technology (OT) CI, Infrastructure CI, Asset, Install Base Item, Connected Device, Technology Management Service, Technology Management Service Offering, Dynamic CI Group |
| Service Consumption | Business Service, Business Service Offering, Service Commitment, Service Offering Subscription, Request Catalog, Catalog Item |
| Manage Portfolios | Portfolio, Service Portfolio |

**Three concepts have no shape.** Configuration Item and Service are parents, and you reach them through the shapes under them. Service Offering is a shared table, so its two kinds each have a shape. The Service Delivery Network isn't an entity, so it has no shape either.

To create a shape by script, use the qualified form as the type: `CSDM5::CSDMBusinessApplication`. Stored names are `CSDM` plus the concept's name without spaces.

## 4. Fields

**Every shape** has two fields for pointing at its ServiceNow record:

- **ServiceNow link:** the record's address.
- **ServiceNow record id:** the record's id.

**Shapes in a life cycle list** also have Life Cycle Stage and Life Cycle Stage Status, each a dropdown of the values for that shape's life cycle process.

**Other fields:**

| Shapes | Fields |
|---|---|
| Business Process | Declared criticality, Confidentiality impact, Integrity impact, Availability impact, Review frequency |
| Contract | Contract number, Start date, End date |
| Product Model, Application Model, System Component Model, Software Component Model, Service Offering Model, Firmware Model, AI System Product Model, Service Model, Software Model, Content Product Model, AI Content Product Model, Contract Model, Facility Model, Hardware Model, Consumable Model, Enterprise Good Model | Product owner, End-of-life date |
| Company | Customer, Manufacturer, Vendor |
| Location | Location type |
| Planning Item | Type |
| Strategic Plan | Mission, Vision, Value statement |
| Target | Measure |
| Business Application | Architecture type, Managed by group, Support group, Business criticality, Data classification, Install type, Platform, Technology stack, User base, IT Application owner |
| Information Object | Data sensitivity, Confidentiality, Data type, Data classification |
| SDLC Component | Component type |
| Service Instance, Data Service Instance, Connection Service Instance, Network Service Instance, Operational Process Service Instance, Facility Service Instance | Environment, Region |
| Application Service | Environment, Region, Population method, Business criticality, Used for |
| Operational Technology (OT) CI, Infrastructure CI, Connected Device | Kind |
| Technology Management Service, Business Service | Service owner, Business criticality |
| Technology Management Service Offering, Business Service Offering | Location or geography, Environment, Availability, Capability, Pricing, Packaging |
| Dynamic CI Group | Service classification |
| Service Commitment | Availability, Criticality, Scope, Pricing, Response |

All fields are optional.

**Not every field comes from CSDM's paper.** CSDM's sources name only some attributes. Some fields here, and their value lists, come from an earlier ServiceNow integration's 2023 file, and others are this pack's own choice. `ea.yaml` marks the source of each one. Names and values may differ on your platform.

**To add a field of your own,** add a tag to the shape on the Tags tab of the Properties window. The pack doesn't list it, and no check reads it.

## 5. Lines: what to connect

Draw a line from the first shape to the second. Hovering over a shape and dragging its arrow offers only the lines CSDM has for that pair. The link and the record id aren't on lines.

| Line | EA type | From, to |
|---|---|---|
| Maps | Association | Value Stream to Business Capability; Value Stream to Business Process; Value Stream Stage to Business Capability; Value Stream Stage to Business Process |
| Operationalizes | Dependency | Business Process to Business Capability |
| Provided by | Dependency | Business Capability to Business Application; Business Capability to Business Service; Connection Service Instance to Network Service Instance; API to Application |
| Process reference | Dependency | Business Application to Business Process |
| Uses | Dependency | Business Application to Information Object; Business Application to Application Service |
| Contains | Dependency | Business Application to SDLC Component; SDLC Component to Application Service; Technology Management Service Offering to Service Instance; Technology Management Service Offering to Dynamic CI Group |
| Consumes | Dependency | Business Application to Application Service |
| Connected to | Dependency | Business Application to Business Application |
| Depends on | Dependency | Application Service to Application Service; Application Service to Application; Application Service to Service Instance; Data Service Instance to Service Instance; Network Service Instance to Service Instance; Operational Process Service Instance to Service Instance; Facility Service Instance to Service Instance; Network Function to Network Function Application; Business Service Offering to Service Instance |
| Connected by | Dependency | Service Instance to Connection Service Instance; Connected Device to Connection Service Instance |
| Receives data from | Dependency | API to Business Service Offering; API to Application Service |
| Runs on | Dependency | Application to Infrastructure CI; Network Function Application to Infrastructure CI |
| Published as | Dependency | Technology Management Service to Technology Management Service Offering; Business Service to Business Service Offering |
| Is part of | Dependency | Business Service to Service Portfolio; Technology Management Service to Service Portfolio |
| Model | Dependency | Configuration Item to Product Model; Contract to Contract Model |
| Bill of materials | Dependency | Product Model to Product Model |
| References | Dependency | Dynamic CI Group to CMDB Group |
| Member | Dependency | Dynamic CI Group to Configuration Item; Request Catalog to Catalog Item |
| Represents | Dependency | Catalog Item to Service Offering |
| Covers | Dependency | Service Offering Subscription to Service Offering |
| Subscriber | Dependency | Service Offering Subscription to User; Service Offering Subscription to Company; Service Offering Subscription to Location; Service Offering Subscription to Department; Service Offering Subscription to Group |
| Part of | Dependency | Value Stream Stage to Value Stream; Business Unit to Company; Department to Business Unit |
| Has | Dependency | Value Stream to Value Stream Category |
| Aligned to | Dependency | Planning Item to Goal; Planning Item to Target |
| Measures | Dependency | Target to Goal |
| Serves | Dependency | Goal to Strategic Priority |
| Relates to | Dependency | Product Idea to Product Model; Planning Item to Product Model |
| Deployed as | Dependency | SDLC Component to Infrastructure CI |
| Assigns | Dependency | Team to Configuration Item; Team to Group |
| Parent of | Dependency | Business Process to Business Process; Business Capability to Business Capability; Company to Company; Business Unit to Business Unit; Location to Location; Service Portfolio to Service Portfolio |

**A relationship, a reference, and a map stay distinct.** Operationalizes, Provided by, Uses, Consumes, Contains, Connected to, Depends on, Connected by, Receives data from, and Runs on are CMDB relationships. Maps is a many-to-many map. The others are references or membership.

**Uses or Consumes.** Use Uses from a Business Application to an Application Service. ServiceNow's documentation tells Enterprise Architecture Workspace users to keep Consumes, so that life cycle timelines display correctly. The checks accept either.

To create a line by script, use the EA type and set `StereotypeEx` to the qualified form.

## 6. Which diagram

Use CSDM Diagram for every view. CSDM's figures suggest a few: capability to portfolio across the domains, one domain at a time, or the relationships of one service.

## 7. What the pack adds that CSDM doesn't define

These are tool choices, not additions to CSDM:

- **The link and the record id** on every shape.
- **The drawing.** A small script shows the concept's name on each shape and line. CSDM defines no notation, so this and the fill colors follow its figures loosely. The script's default size follows the shared layout standard: a box is 100 by 70, and Request Catalog, a container, is 150 by 90.
- **Fields that are this pack's own choice,** marked in `ea.yaml`.

## 8. What CSDM has that the pack doesn't

- **No connection to ServiceNow.** See the top of this page.
- **Most of each table's attributes.** ServiceNow's dictionary holds the full lists, and an architecture model doesn't need them.
- **No line for "underpin".** CSDM shows it through offerings. An offering's derivation from a service is the reverse of Published as.
- **Operational data,** such as support groups and approval groups on offerings. These stay in ServiceNow.

## 9. Traps

1. **The Browser shows the stored name:** `CSDMBusinessApplication`. That's normal: the Properties window and the diagram show "Business Application".
2. **Foundation entities don't take relationship lines.** A Depends on line to a Company gets an error. Business Process is the exception. Foundation entities join other shapes through references such as Model and Part of.
3. **Product Model has child classes, and the lines name the parent.** The Model and Relates to lines are offered to the Product Model shape, not to Application Model or the other classes.
4. **An empty field passes.** A blank life cycle stage or classification gets no finding. A service with no stage set isn't asked for an offering. The Business Application check is also looser than its dropdown: the dropdown offers four stages, and the check accepts every stage on the intangible list, so a wider stage set by script passes.
5. **Asset and Install Base Item combine two lists,** tangible and intangible, and no check reads their values.
6. **Operationalizes may not be on your platform.** CSDM's paper and documentation draw this relationship, but a ServiceNow community comment says the base system doesn't have it. We haven't verified it either way. The pack keeps the line as the paper draws it, so check your platform before you rely on it.

## 10. Checking a model

The CSDM 5 ruleset, `rulesets/csdm-5/csdm-5_rules.yaml`, has 14 rules. They check that:

- A line joins only the pairs CSDM lists, as a warning, because CSDM doesn't forbid others.
- A relationship line touches no Foundation entity other than Business Process.
- A business or technology management service isn't nested under its own kind.
- A Dynamic CI Group contains no other group, and its classification is one of its two values.
- An operational service has an offering, and a capability has something providing it.
- The legacy process reference isn't used.
- A Business Application's Uses or Consumes reaches only an Application Service or an Information Object.
- Life cycle values belong to the shape's process.

5 of 14 rules in this ruleset use formats newer than 3.6.4, and on that server they report nothing or don't run as written. Use server 3.6.5 or later, because a clean result on 3.6.4 doesn't mean the model passes.

**The grading is ours.** CSDM is guidance and rarely says "must". The ruleset makes a finding an error only where CSDM states a flat limit, and a warning where CSDM recommends something or a line falls outside its list.

**They can't check everything.** Capability hierarchy depth and loops need a chain of lines followed, which the rules can't do today. Judgment calls, and anything that depends on what happens in ServiceNow, need a person.

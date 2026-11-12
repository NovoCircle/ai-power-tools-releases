# Modeling UAF 1.0 in Sparx Enterprise Architect

How to model the language of the UAF skill the way Sparx's built-in technology (id `UAF`, profile `UAFP`) does it. Measured on EA 17.1 build 1716 by creating one element, port, activity parameter, operation, package, connector and diagram of each kind and reading the stored rows back; `ea.yaml` holds the same facts as data. Westbrook Bank appears only as an illustration; substitute your own organization, and do not assume your repository holds any sample model.

## Version note

The skill describes UAF 1.0 (OMG formal/17-12-01). EA's technology reports version **1.1** (`GetTechnologyVersion("UAF")`) while its own perspective text says UAF 1.0. OMG has published 1.1 (2020), 1.2 (2022) and 1.3 (2026). This how-to does not say which version EA implements, and nothing here was compared with the newer versions. What it records is the profile EA ships: 178 stereotype names on 184 rows. Differences against the 1.0 skill are listed below (59 concepts with no EA name, two EA names the skill does not have).

## What the technology looks like

- **Technology `UAF`, profile `UAFP`, 178 distinct names on 184 rows** in the Resources tab (a name is listed once for each metaclass it applies to). **The qualified stereotype is `UAFP::<name>`**: the prefix is the profile name, not the technology id. `UAF::<name>` binds nothing (0 of 178). 172 names bind through the API; six are listed but cannot be created (below).
- **No diagram types of its own.** The technology has no Diagram Types node; it draws every view on a SysML 1.4 diagram type (next section).
- **UAF is a UML profile, so the stereotypes sit on UML elements.** Of the 114 names EA creates as a package element, 43 default to a Class (and 44 rows are Class), 19 to an Object (the actual elements), 19 to a Part (roles and properties), 7 to an Activity, 6 to a Note (Alias, Definition, Metadata and the other comment-like ones), 5 to a DataType (Condition, Environment, GeoPoliticalExtentType, Location, MeasurementSet), 5 to an Action, 4 to a Constraint, 3 to a StateMachine, 2 to a Signal and 1 to an Enumeration (StatusIndicators, which also takes a DataType). Three more are Ports, three are activity parameters, three are operations, two are packages, and 47 are connectors.
- **Stored names are bare.** `t_object.Stereotype` holds `Capability`; the qualified form is in `t_xref` (row `Stereotypes`, `FQName`) and is what you pass to create an element or set `StereotypeEx`. EA matches the name after `UAFP::` without regard to case and stores the profile's upper camel case (`UAFP::capability` creates a `Capability`).
- **59 concepts of the skill have no stereotype**: 34 abstract groupings, 33 in the profile plus SecurityMeasurement in the metamodel (OperationalAgent, CapableElement, Asset ...; a model cannot use them), 16 enumerations (the guide counts 17 because it also counts StatusIndicators, which has a stereotype here), the 15 kinds of the profile plus SecurityClassificationKind of the metamodel (EnvironmentKind, ProjectKind, RoleKind ...; EA carries them as the allowed values of a tagged value, below), and 9 concrete concepts (ISO8601DateTime, SecurityControlAction, SecurityProperty and six more security concepts).
- **Six names are on the tab but cannot be created**: `ActualMeasurement`, `ActualOrganizationRole`, `ActualProjectMilestoneRole`, `ActualProjectRole`, `ActualResourceRole` and `ProjectStatus`. The standard defines them as UML slots; EA's API bound none of them (as an element, a child, an attribute, an operation, a package or any of 17 connector types). Whether the toolbox or the UI creates them was not tried.
- **EA adds two stereotypes the skill does not have**: `DataRole` and `InformationRole` (both Parts). They may be a version difference; not researched.
- Toolbox pages and quick links, read on screen (EA 17.1 build 1716, 2026-11-04): the UAF technology has one toolbox, "UAF", with 13 pages (UAF Actual Resources, Dictionary, Metadata, Operational, Parameters, Personnel, Project, Resources, Security, Services, Standards, Strategic, Summary and Overview). The Operational and Security pages were opened; the Security page has no Security Property, Caveat or Security Classification, which agrees with the profile. The other 11 pages were not opened. From a UAF Capability on a SysML diagram the quick links offered SysML types only, with no UAF link; a UAF quick link from a diagram that uses the UAF toolbox was not read.

## Which diagram type for which view

The standard's 76 view specifications are the diagram types, and the technology has no diagram type for any of them. EA's model patterns (68 of them, one per view) draw them on SysML 1.4 diagrams. All eight tokens below were created and read back (`SysML1.4::Package` is created too; no pattern uses it).

| View (model kind) | SysML token the patterns use | Stored `Diagram_Type` | `StyleEx` |
|---|---|---|---|
| Taxonomy, Connectivity, Roadmap, Traceability, Dictionary, Information Model, Measurements, Environment, Summary and Overview (all 8, 8, 7, 8 and the singles) | `SysML1.4::BlockDefinition` | Logical | `MDGDgm=SysML1.4::BlockDefinition;` |
| Structure (7 of 9; Resource Structure and Standards Structure use the internal block diagram) | `SysML1.4::BlockDefinition`, `SysML1.4::InternalBlock` | Logical, CompositeStructure | `MDGDgm=SysML1.4::InternalBlock;` |
| Processes (4 of 6 use a block definition diagram; Project Processes and Security Processes use the activity diagram) | `SysML1.4::BlockDefinition`, `SysML1.4::Activity` | Logical, Activity | `MDGDgm=SysML1.4::Activity;` |
| States (Operational, Personnel, Resource, Service; Strategic States uses a block definition diagram) | `SysML1.4::StateMachine` | Statechart | `MDGDgm=SysML1.4::StateMachine;` |
| Interaction Scenarios (4) | `SysML1.4::Sequence` | Sequence | `MDGDgm=SysML1.4::Sequence;` |
| Constraints (5 block definition; Service Constraints uses a parametric diagram) | `SysML1.4::BlockDefinition`, `SysML1.4::Parametric` | Logical, CompositeStructure | `MDGDgm=SysML1.4::Parametric;` |
| Requirements | `SysML1.4::Requirement` | Custom | `MDGDgm=SysML1.4::Requirement;` |

The seven tokens are what the patterns use; `UAF::UAF` and `UAFP::UAF` are not diagram types (EA makes a plain Class diagram with no `MDGDgm`). The pattern choices are EA's, not the standard's: the standard recommends several forms for most views and does not require one.

EA's example model carries `UAFP_*` diagram tokens that this technology does not list. Where they come from was not measured, and neither was whether EA 17.1 can create them.

## How to say each concept

Create the object with the qualified type (`AddNew(name, "UAFP::<name>")`) so EA binds the technology's own stereotype.

| To model | Create | Set |
|---|---|---|
| A type-like concept: Capability, OperationalPerformer, ResourcePerformer kinds (System, Software, Organization, Post, Person ...), ServiceSpecification, Competence, Standard ... | a Class in a package, with the stereotype | the tagged values (below) |
| A role or typed property: OperationalRole, ResourceRole, ServiceSpecificationRole, ProjectRole, CapabilityProperty, EnvironmentProperty, Measurement ... | a Part element (it can sit in a package, and is normally a child of the class that owns it); `Measurement` also goes on an attribute | the owner (the class it sits in, `ParentID`) and the type (the Part's classifier) |
| A port: OperationalPort, ResourcePort, ServicePort | a Port, **as a child of the performer** (EA refuses a Port in a package) | the type (the interface) |
| An activity and its parameters: OperationalActivity, Function, ServiceFunction, ProjectActivity | an Activity; the parameters (OperationalParameter, ResourceParameter, ServiceParameter) are ActivityParameter elements, **children of the activity** | |
| A called activity: OperationalActivityAction, FunctionAction, ServiceFunctionAction, ProjectActivityAction, SecurityProcessAction | an Action | the called activity (behavior) |
| A state description: OperationalStateDescription, ResourceStateDescription, ServiceStateDescription | a StateMachine | |
| An actual element: ActualOrganization, ActualPost, ActualProject, ActualProjectMilestone, FieldedCapability ... | an Object, with the stereotype | the classifier (the type it is an instance of), and the tagged values |
| A parameter value type: Environment, Location, GeoPoliticalExtentType, Condition, MeasurementSet | a DataType | the kind as a tagged value |
| An annotation: Alias, Definition, Metadata, Information, VisionStatement, ArchitectureMetadata | a Note with the stereotype, linked to the annotated element by a note link (a `NoteLink` connector with no stereotype) | |
| A constraint: OperationalConstraint, ResourceConstraint, SecurityConstraint, ServicePolicy | a Constraint element with the stereotype, linked to the constrained element by a note link | |
| An exchange signal: OperationalSignal, ResourceSignal | a Signal | |
| A method: OperationalMethod, ResourceMethod, ServiceMethod | **an operation of a class** with the stereotype (EA refuses it as an element) | |
| A package: ArchitecturalDescription, DataModel | a Package; set the stereotype on the package's own element (`package.Element.StereotypeEx`) | the tagged values (toBe, viewpoint ...) |
| A relationship: see the table below | a connector with the stereotype, drawn from the client (or information source) to the supplier (or information target) | |
| A kind (EnvironmentKind, ProjectKind, RoleKind ...) | no element: it is the **allowed values of a tagged value** of the stereotype that owns it | choose one value |

### Relationship connectors

EA stores each relationship as one of seven connector types. EA checks neither end: it created every connector between every pair of stereotypes the tests tried, including the 52 wrong connectors of the seeded set.

| Connector type (stored) | Stereotypes |
|---|---|
| Abstraction (16) | CapabilityForTask, CompetenceForRole, CompetenceToConduct, Consumes, Exhibits, FillsPost, Implements, IsCapableToPerform, MapsToCapability, OrganizationInEnterprise, OwnsProcess, OwnsRisk, OwnsRiskInContext, PerformsInContext, RequiresCompetence, ResponsibleFor |
| Dependency (16) | AchievedEffect, Affects, AffectsInContext, ArbitraryConnector, ArchitecturalReference, DesiredEffect, Enhances, Forecast, MilestoneDependency, Mitigates, ProjectSequence, Protects, ProtectsInContext, ProvidesCompetence, SameAs, VersionSuccession |
| InformationFlow (5) | OperationalExchange, ResourceExchange, Command, Control, ActualResourceRelationship |
| Connector (3) | OperationalConnector, ResourceConnector, ServiceConnector |
| Sequence message (3) | OperationalMessage, ResourceMessage, ServiceMessage |
| ControlFlow (2) | OperationalControlFlow, FunctionControlFlow |
| ObjectFlow (2) | OperationalObjectFlow, FunctionObjectFlow |

The tagged values of a relationship are on the connector (`t_connectortag`): `operationalExchangeKind` and `trustlevel` on OperationalExchange, `exchangeKind` on ResourceExchange, Command and Control, `responsibleRoleKind` on ResponsibleFor, `startDate`/`endDate` on FillsPost and ResponsibleFor, `forecastPeriod` on Forecast, `desiredEffect`/`achievedEffect`, `environmentalConditions` on Exhibits, `boundaryCondition` and `implements` on ResourceConnector, `itemProperty` on the information flows. The tagged value `itemProperty` is free text; how the item an exchange conveys is stored was not measured.

### Tagged values

Every stereotype that specializes UAFElement (169 of 172) carries `URI` and `conformsTo`; 98 carry `actualMeasurementSet` and `measurementSet`. The rest are the properties of the stereotype, named in lower camel case. EA creates them **empty**, except the ones with a default (`toBe` True, `locationNamedByAddress` False). A property that the standard gives a kind enumeration is a tagged value whose allowed values EA lists (`environmentKind`: TerrainType, WeatherConditions, LightConditions, CBRNEnvironment, SituationType; `projectKind`: `Programme` (the standard's own literal), Portfolio, Project, PersonnelDevelopment; and so on); EA does not enforce them. The standard's exactly-one properties appear under these names, which differ from the standard's:

| Standard's property | EA tagged value |
|---|---|
| Environment.kind | `environmentKind` |
| GeoPoliticalExtentType.kind | `geoPoliticalExtentTypeKind` |
| Location.kind | `locationTypeKind` |
| ActualLocation.locationKind, .locationNamedByAddress | `locationKind`, `locationNamedByAddress` |
| Information.informationKind | `informationKind` |
| ResourceRole.RoleKind | `roleKind` |
| WholeLifeConfiguration.kind | `wholeLifeConfigurationKind` |
| ActualProject.projectKind | `projectKind` |
| ActualProjectMilestone.kind | `actualMilestoneKind` |
| ArchitecturalDescription.toBe, .viewPoint | `toBe`, `viewpoint` |
| View.viewpoint | `viewpoint` (free text) |
| ArchitecturalDescription.architectureFramework | **none**: EA has no such tag |
| ResponsibleFor.ResponsibleRoleKind | `responsibleRoleKind` on the connector |

Illustration (Westbrook Bank is fictitious): the `OperationalPerformer` `Branch Banker` `Exhibits` the `Capability` `Open business account`; an `IsCapableToPerform` joins the performer to the `OperationalActivity` `Verify applicant`; a `System` named `Onboarding Platform` `Implements` the performer and is itself `IsCapableToPerform` a `Function`. A `SecurityControl` `Mitigates` a `Risk` and `Protects` the system. Substitute your own elements and relationships.

## Containment

- A Port belongs to a performer and an ActivityParameter to an activity: EA stores that in `ParentID` and refuses to create them in a package. A Part is normally a child of its owner too (`ParentID`); its type is the Part's classifier (`t_object.Classifier`).
- The stereotype sets neither. A role created in a package has no owner and no type until you set them, and the standard's typing rules (a role of the right kind, a port typed by an interface of the right domain) are about exactly those.
- `InformationElement` and `DataElement` must be owned by a `DataModel`, which is a package stereotype.

## What EA does that the standard does not

- Two extra stereotypes: `DataRole` and `InformationRole`.
- Several tagged-value names that differ from the standard's property names (above) and the standard's `architectureFramework` missing.
- A stereotype is accepted on a whole family of element types (Class, Activity, Component, Node, Requirement) alike; EA does not check which metaclass the standard extends.
- The six slot concepts are on the tab but not creatable.
- `SecurityProperty` is used by EA's own sample (`ua1.0-security-*`) but the shipped profile refuses it.

## What the standard has that EA does not

No stereotype for any abstract grouping, any kind enumeration, ISO8601DateTime, SecurityControlAction, SecurityProperty or the other security concepts (SecurityAvailability, SecurityCategory, SecurityClassification, SecurityIntegrity, Caveat, ActivityPerformableUnderCondition). No check at all that a relationship joins the right kinds of element: EA's API created every wrong connector the sample defects use (52 planted, 0 refused). The standard's view specifications are not diagram types.

## Traps

1. **`UAFP::`, not `UAF::`.** The technology id is `UAF`; the stereotype prefix is the profile name `UAFP`. A script that qualifies with `UAF::` creates nothing.
2. **Six listed names cannot be created.** Do not promise a model of `ActualMeasurement` or the actual roles in EA; they are slots and the API does not bind them.
3. **A Port and an ActivityParameter need a parent;** operation stereotypes go on an operation; `ArchitecturalDescription` and `DataModel` go on a package's own element (`package.StereotypeEx` stores nothing).
4. **Case does not matter on creation, and does on selection.** `UAFP::capability` creates a `Capability`; a rule that selects `capability` finds nothing.
5. **A second stereotype is invisible to a rule.** An element with two stereotypes (for example `UAFP::Capability` and `SysML1.4::block`) stores the first in `t_object.Stereotype` and both in `t_xref`; the validator reads the column. Which one is first depends on how they were applied; the order was not tested.
6. **Tagged values are created empty.** An unset kind is not an error to EA; the rules flag it. Defaults are `toBe` True and `locationNamedByAddress` False.
7. **Enumerations are tags, not elements.** The 16 enumerations with no stereotype (the 15 kinds plus SecurityClassificationKind) are the allowed values of a tagged value; EA does not enforce them. The guide counts 17, because it also counts StatusIndicators, which has a stereotype here.
8. **The stereotype is accepted on the wrong metaclass.** `Capability` binds to a Requirement or a Node; the Part, Object, Note, DataType, Action, Constraint, StateMachine and Signal stereotypes are selective.
9. **Exchanges are information flows with no conveyed item.** The standard's rules about what an exchange conveys (UAF-XCH-001 to 010) depend on a conveyed item and a realizing edge, connector or message; the validator cannot read what an exchange is typed or realized by, so no rule checks them.
10. **Annotation and constraint links are `NoteLink` connectors with no stereotype.** A rule that selects by connector stereotype never sees them. A rule can select them by connector type (`connector_types: [NoteLink]`), but it cannot yet say which element each kind of note may be linked to (an Alias to any UAF element, an ArchitectureMetadata only to an ArchitecturalDescription), so the 11 rules about them are still not checked.
11. **The relationship tables are generated from concrete stereotypes.** A relationship end that the standard names by an abstract grouping (OperationalAgent) is the set of concrete stereotypes that specialize it (four for OperationalAgent); a stereotype outside the set is reported even if you meant it as a specialization.
12. **Names are generic.** `Function`, `System`, `Information`, `Location`, `Standard`, `Definition`, `Alias`, `Control`, `Command` and `View` are common words; whether another technology in the same model declares them was not measured. Confirm that a clean validation also matched more than zero UAF objects.
13. **Do not rely on a model pattern for the profile.** EA's UAF patterns use `UAFP::SecurityProperty`, which the shipped profile does not define.

## Checking a model

70 of 84 rules in this ruleset use formats newer than 3.6.4, and on that server they report nothing or don't run as written. Use server 3.6.5 or later, because a clean result on 3.6.4 doesn't mean the model passes.

The ruleset `rulesets/uaf-1/uaf-1_rules.yaml` has 84 rules that implement 124 of the skill's rules: for each of 41 relationships, the kinds of element allowed at its two ends (generated tables of concrete stereotypes); that a Forecast joins elements of the same kind; that 13 exactly-one properties carried as tagged values have a value; and, with the rule types that read where an element sits, that 29 kinds of element (roles and other parts, ports, state descriptions, actions, signal properties, information and data elements) are owned by the kind of element the standard names (the element they are nested under, or the `DataModel` package). The rest of the skill's static and partial rules (typing, operations, exchanges, annotation links, five statements that everything an owner holds of a kind is of one stereotype, rules about concepts EA has no stereotype for) cannot be stated over what EA stores through `validate_model`.

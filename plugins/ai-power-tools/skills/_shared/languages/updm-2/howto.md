# Modeling UPDM 2.1 in Sparx Enterprise Architect

How to model the language of the UPDM skill the way Sparx's built-in technology does it. EA lists the technology as **UPDM 2.0** (Resources > MDG Technologies); its id is **`UPDM2`**, and every stereotype it stores is qualified `UPDM2::<name>`. Measured on EA 17.1 build 1716 by creating one element, port, part, parameter, operation, package, connector and diagram of each kind and reading the stored rows back; `ea.yaml` holds the facts. Westbrook Bank (fictitious) appears only as an illustration; your model has its own names, and nothing here assumes it contains Westbrook's.

## Version

**The skill and this guide describe UPDM 2.1. EA shows the technology as UPDM 2.0, and its API reports the technology `UPDM2` as version `2.1`** (`Repository.GetTechnologyVersion("UPDM2")`). EA's model patterns are named `up2.0-*`. EA names no specification edition, so which published edition the profile follows cannot be told from EA, and the catalog was not compared with any other. OMG also lists UPDM 2.1.1 (2017), which was not studied. UPDM has been replaced by the Unified Architecture Framework (UAF).

## What the technology looks like

- **179 names and 181 rows** on the Resources tab (`UPDMPackage` is listed three times); every one can be applied. 178 of the skill's 226 concepts have a stereotype of the same name; 48 do not (33 of them are abstract groupings).
- **The prefix is the profile name.** `AddNew(name, "UPDM2::Node")` binds. `UPDM::`, `UPDM2.0::`, `UPDM2.1::` and `UPDM 2.0::` are refused ("Invalid type"), and the diagram groups (`UPDM2_OV`, `UPDM2_SV/SvcV`) are not stereotype prefixes. `IsTechnologyLoaded` is True for `UPDM2` only.
- **Stored names are bare.** `t_object.Stereotype` holds `Node`; the qualified form is only in `t_xref` (the row named `Stereotypes`, `FQName`) and is what you pass to create an element or set `StereotypeEx`. EA matches the name after `UPDM2::` without regard to case (`UPDM2::node` stores `Node`), but a ruleset selector compares the stored string exactly.
- **The profile is a hierarchy with its roots left out.** None of the 33 abstract elements (`SystemResource`, `CapableElement`, `NodeParent`, `OrganizationalResource` and the other groupings) has a stereotype. A rule that says "a SystemResource" means any of the twelve concrete stereotypes under it; `ea.yaml` lists them under `use_instead`.
- **Aliases are stereotypes of their own.** DoDAF and MODAF names (`Performer` for `Node`, `System` for `ResourceArtifact`, `Skill` for `Competence`, `Vision` for `EnterpriseVision`, and the connectors `ActivityPerformedByPerformer`, `CapabilityOfPerformer`, `ActivityPartOfCapability`, `ProjectOwnership`, `SkillOfPersonType`) are separate stereotypes. The standard says they add no rules of their own, so a rule about the aliased element applies to them.
- **EA adds one stereotype the skill does not have:** `UPDMPackage` (EA's container for a view's content), and two diagram types: `AV-3` and `UPDM Framework`.
- **74 diagram types**, all stored as a base diagram (Logical, Activity, Statechart, Sequence or Object) with the token in `StyleEx` (`MDGDgm=`).

## Which diagram type for which view

The standard defines no diagram type; Annex B describes 47 products. EA has a diagram type for nearly each of them, named `<group>::<view>`. Create one with `Diagrams.AddNew(name, "<token>")`.

| Annex B product (language skill) | EA token(s) | Stored as |
|---|---|---|
| AcV-1/PV-1 | `UPDM2_AcV/PV::AcV-1`, `UPDM2_AcV/PV::PV-1` | Logical |
| AcV-2/PV-2 | `UPDM2_AcV/PV::AcV-2`, `UPDM2_AcV/PV::PV-2` | Logical |
| AV-1 | `UPDM2_AV::AV-1` | Logical |
| AV-2 | `UPDM2_AV::AV-2` | Logical |
| StV-1/CV-1 | `UPDM2_StV/CV::CV-1`, `UPDM2_StV/CV::StV-1` | Logical |
| StV-2/CV-2 | `UPDM2_StV/CV::CV-2`, `UPDM2_StV/CV::StV-2` | Logical |
| StV-3/CV-3 | `UPDM2_StV/CV::CV-3`, `UPDM2_StV/CV::StV-3` | Logical |
| StV-4/CV-4 | `UPDM2_StV/CV::CV-4`, `UPDM2_StV/CV::StV-4` | Logical |
| StV-5/CV-5 | `UPDM2_StV/CV::CV-5`, `UPDM2_StV/CV::StV-5` | Logical |
| StV-6/CV-6 | `UPDM2_StV/CV::CV-6`, `UPDM2_StV/CV::StV-6` | Logical |
| CV-7 | `UPDM2_StV/CV::CV-7` | Logical |
| OV-7/DIV-1/DIV-2 | `UPDM2_OV::DIV-1`, `UPDM2_OV::DIV-2`, `UPDM2_OV::OV-7` | Logical |
| SV-11/DIV-3 | `UPDM2_SV/SvcV::DIV-3`, `UPDM2_SV/SvcV::SV-11` | Logical |
| OV-1 | `UPDM2_OV::OV-1` | Logical |
| OV-2 | `UPDM2_OV::OV-2` | Logical |
| OV-3 | `UPDM2_OV::OV-3` | Logical |
| OV-4 Actual | `UPDM2_OV::OV-4 Actual` | Object |
| OV-4 Typical | `UPDM2_OV::OV-4 Typical` | Logical |
| OV-5 | `UPDM2_OV::OV-5` | Activity |
| OV-6a | `UPDM2_OV::OV-6a` | Activity |
| OV-6b | `UPDM2_OV::OV-6b` | Statechart |
| OV-6c | `UPDM2_OV::OV-6c` | Sequence |
| PV-3 from project activity | `UPDM2_AcV/PV::PV-3` | Logical |
| PV-3 from project milestones | `UPDM2_AcV/PV::PV-3` | Logical |
| SV-1/SvcV-1 | `UPDM2_SV/SvcV::SV-1`, `UPDM2_SV/SvcV::SvcV-1` | Logical |
| SV-2/SvcV-2 | `UPDM2_SV/SvcV::SV-2`, `UPDM2_SV/SvcV::SvcV-2` | Logical |
| SV-3/SvcV-3a/3b | `UPDM2_SV/SvcV::SV-3`, `UPDM2_SV/SvcV::SvcV-3a`, `UPDM2_SV/SvcV::SvcV-3b` | Logical |
| SV-4/SvcV-4 | `UPDM2_SV/SvcV::SV-4`, `UPDM2_SV/SvcV::SvcV-4` | Logical |
| SV-5/SvcV-5 | `UPDM2_SV/SvcV::SV-5`, `UPDM2_SV/SvcV::SvcV-5` | Logical |
| SV-6/SvcV-6 | `UPDM2_SV/SvcV::SV-6`, `UPDM2_SV/SvcV::SvcV-6` | Logical |
| SV-7/SvcV-7 | `UPDM2_SV/SvcV::SV-7`, `UPDM2_SV/SvcV::SvcV-7` | Logical |
| SV-8/SvcV-8 | `UPDM2_SV/SvcV::SV-8`, `UPDM2_SV/SvcV::SvcV-8` | Logical |
| SV-9/SvcV-9 | `UPDM2_SV/SvcV::SV-9`, `UPDM2_SV/SvcV::SvcV-9` | Logical |
| SV-10a/SvcV-10a | `UPDM2_SV/SvcV::SV-10a`, `UPDM2_SV/SvcV::SvcV-10a` | Logical |
| SV-10b/SvcV-10b | `UPDM2_SV/SvcV::SV-10b`, `UPDM2_SV/SvcV::SvcV-10b` | Statechart |
| SV-10c/SvcV-10c | `UPDM2_SV/SvcV::SV-10c`, `UPDM2_SV/SvcV::SvcV-10c` | Sequence |
| TV-1&2&3/StdV-1&2 | `UPDM2_TV/StdV::StdV-1`, `UPDM2_TV/StdV::StdV-2`, `UPDM2_TV/StdV::TV-1`, `UPDM2_TV/StdV::TV-2`, `UPDM2_TV/StdV::TV-3` | Logical |
| SOV-1 | `UPDM2_SOV::SOV-1` | Logical |
| SOV-2 | `UPDM2_SOV::SOV-2` | Logical |
| SOV-3 | `UPDM2_SOV::SOV-3` | Logical |
| SOV-4a | `UPDM2_SOV::SOV-4a` | Logical |
| SOV-4b | `UPDM2_SOV::SOV-4b` | Statechart |
| SOV-5 | `UPDM2_SOV::SOV-5` | Activity |
| SOV-4c | `UPDM2_SOV::SOV-4c` | Sequence |
| SV-12 | `UPDM2_SV/SvcV::SV-12` | Logical |
| Environment Elements, Measurements | none | no diagram type; use a class or object diagram of the environment and measurement stereotypes |
| (EA only) | `UPDM2_AV::AV-3`, `UPDM2_Framework::UPDM Framework` | Logical |

How the types differ from the standard's products: EA has one `OV-5` type for the DoDAF OV-5a and OV-5b, one `OV-1` for MODAF's OV-1a, 1b and 1c, one `SV-2` and one `SV-5` for their lettered variants, and splits OV-4 into `OV-4 Actual` (stored as an Object diagram) and `OV-4 Typical`. `OV-6a` and `OV-5` are Activity diagrams, `OV-6b`, `SV-10b`, `SvcV-10b` and `SOV-4b` Statecharts, `OV-6c`, `SV-10c`, `SvcV-10c` and `SOV-4c` Sequence diagrams. `TV-3` binds although none of Sparx's patterns uses it. The level 1 SysML views (block definition, internal block, parametric, requirement) are the SysML technology's diagram types, not UPDM's.

## How to say each concept

The creation rule for every stereotype is the same: `Elements.AddNew(name, "UPDM2::<Stereotype>")` gives the stereotype's own form (the metaclass in the second column). Replace the example names with your own enterprise.

### Elements, parts, ports and others

| Metaclass EA stores | Stereotypes (UPDM2:: omitted) | How |
|---|---|---|
| Object | `ActualLocation`, `ActualOrganization`, `ActualPerson`, `ActualPost`, `ActualProject`, `ActualProjectMilestone`, `ActualPropertySet`, `DeployedMilestone`, `ExternalIndividual`, `FieldedCapability`, `GeoPoliticalExtent`, `IncrementMilestone`, `IndividualPersonRole`, `Location`, `Measure`, `NoLongerUsedMilestone`, `OutOfServiceMilestone`, `Project`, `ServiceLevelValueSet` | an Object (an instance: the `Actual...` elements, milestones, locations) |
| Note | `Alias`, `ArchitectureMetadata`, `Definition`, `Information`, `Metadata`, `StandardConfiguration`, `StereotypeExtension`, `VisionStatement` | a Note (an annotation) |
| Package | `ArchitecturalDescription`, `LogicalDataModel`, `PhysicalDataModel`, `ServiceDescription`, `UPDMPackage`, `View`, `Viewpoint` | an element of type Package, or a real package (`Packages.AddNew`, then `Element.StereotypeEx`) |
| Signal | `AsynchronousMessage` | a Signal |
| Class | `Capability`, `CapabilityConfiguration`, `Climate`, `Competence`, `Condition`, `Energy`, `EnterpriseGoal`, `EnterprisePhase`, `EnterpriseVision`, `EntityItem`, `Environment`, `ExchangeElement`, `ExternalTuple`, `ExternalTupleType`, `ExternalType`, `FunctionalStandard`, `GeoPoliticalExtentType`, `HighLevelOperationalConcept`, `LightCondition`, `LocationType`, `LogicalArchitecture`, `Materiel`, `MeasurementSet`, `MeasureType`, `Node`, `Organization`, `OrganizationType`, `Performer`, `Person`, `PersonType`, `PhysicalArchitecture`, `Post`, `ProjectMilestone`, `ProjectType`, `Protocol`, `ResourceArtifact`, `Responsibility`, `RoleType`, `SecurityAttributesGroup`, `SecurityDomain`, `ServiceAccess`, `ServiceInterface`, `Skill`, `Software`, `Standard`, `StatusIndicators`, `System`, `TechnicalStandard`, `Vision`, `WholeLifeConfiguration`, `WholeLifeEnterprise` | a Class (also a Component, Node, Device or other Class-family element) |
| Part (child of a class) | `CapabilityProperty`, `ConceptRole`, `ConditionProperty`, `EntityAttribute`, `EnvironmentProperty`, `KnownResource`, `Measurement`, `NodeRole`, `ProblemDomain`, `ProjectMilestoneRole`, `ProjectTheme`, `Property`, `ProtocolLayer`, `ResourceRole`, `ServiceAttribute`, `StructuralPart`, `TemporalPart`, `VersionOfConfiguration` | a Part that is a child of a class; set its type (`ClassifierID`) to the element it stands for |
| Activity | `EnduringTask`, `Function`, `Mission`, `OperationalActivity`, `ProjectActivity`, `ServiceFunction`, `StandardOperationalActivity` | an Activity |
| Action | `FunctionAction`, `OperationalActivityAction`, `ProjectActivityAction`, `ServiceFunctionAction` | an Action |
| operation of a class | `NodeOperation`, `ResourceOperation`, `ServiceMessageHandler`, `ServiceOperation` | applied to an operation of a class (Methods), not to an element |
| Port (child of a class) | `NodePort`, `Request`, `ResourcePort`, `Service` | a Port that is a child of a class (EA refuses a Port in a package) |
| Constraint | `OperationalConstraint`, `ResourceConstraint`, `ServicePolicy` | a Constraint |
| Interaction | `OperationalEventTrace`, `ResourceEventTrace`, `ServiceInteraction` | an Interaction |
| ActivityParameter (child of an activity) | `OperationalParameter`, `ResourceParameter`, `ServiceParameter` | an ActivityParameter that is a child of an Activity |
| State | `OperationalState`, `ResourceState` | a State |
| StateMachine | `OperationalStateDescription`, `ResourceStateMachine`, `ServiceStateMachine` | a StateMachine |
| Artifact | `UPDMPackage` | an Artifact (`UPDMPackage` only) |
| Text | `UPDMPackage` | a Text element (`UPDMPackage` only) |

Tags that matter (set after creation): `architectureFramework` (DoDAF, MODAF, NAF) on `ArchitecturalDescription` and `ServiceDescription`; `startDate` and `endDate` on `EnterprisePhase`, `WholeLifeEnterprise` and `ActualProject`; `date` and `description` on the milestones; `ruleKind` on the constraints; `VIEWID` and `VIEWTYPE` on `UPDMPackage`. The full list is in `ea.yaml`.

### Relationships (connectors)

Create a connector from the source element with `Connectors.AddNew("", "UPDM2::<Stereotype>")` and set the supplier; EA picks the connector type. Directions are as EA stores them: a Dependency from client (start) to supplier (end), an InformationFlow from its information source. Checked with the toolbox tools on screen (EA 17.1 build 1716, 2026-11-04): `Exhibits`, `IsCapableOfPerforming`, `Trustline`, `Implements` and `Needline` all ran from the element where the drag started (source) to the element where it ended (target), as the table says. The `Implements` tool also accepted a Function as source and a ResourceArtifact as target, the wrong way round, with no message: the toolbox does not check the pair. The other connectors were not drawn.

| Stereotype | EA connector type | From (client / source) | To (supplier / target) |
|---|---|---|---|
| `ActivityPartOfCapability` | Dependency | Activity (as MapsToCapability) | Capability (as MapsToCapability) |
| `ActivityPartOfProject` | Dependency | ProjectActivity | ActualProject |
| `ActivityPerformedByPerformer` | Dependency | Node, SystemResource, ServiceInterface (as IsCapableOfPerforming) | OperationalActivity, Function, ServiceFunction (as IsCapableOfPerforming) |
| `ActualOrganizationRelationship` | InformationFlow | ActualOrganizationalResource | ResourceInteraction |
| `ArbitraryConnector` | Dependency | ConceptRole | ConceptRole |
| `ArchitecturalReference` | Dependency | ArchitecturalDescription | ArchitecturalDescription |
| `AssociationOfInformation` | Association | EntityItem (as EntityRelationship) | EntityItem (as EntityRelationship) |
| `CapabilityOfPerformer` | Dependency | CapableElement (as Exhibits) | Capability (as Exhibits) |
| `Command` | InformationFlow | OrganizationalResource | OrganizationalResource |
| `Control` | InformationFlow | OrganizationalResource | ResourceArtifact |
| `DesiredEffect` | Dependency | Desirer | DesiredState |
| `Details` | Dependency | EntityItem | ExchangeElement |
| `EntityRelationship` | Association | EntityItem | EntityItem |
| `Exhibits` | Dependency | CapableElement | Capability |
| `FillsPost` | Dependency | ActualPerson | ActualPost |
| `Forecast` | Dependency | SubjectOfForecast | SubjectOfForecast |
| `FunctionEdge` | ControlFlow | - | - |
| `Implements` | Dependency | SystemResource, ResourceInteraction, Function, ServiceFunction | Node, OperationalActivity, OperationalExchange, Function |
| `IsCapableOfPerforming` | Dependency | Node, SystemResource, ServiceInterface | OperationalActivity, Function, ServiceFunction |
| `MapsToCapability` | Dependency | Activity | Capability |
| `MilestoneSequence` | Dependency | ProjectMilestone | ProjectMilestone |
| `Needline` | Connector | NodeRole, NodePort | NodeRole, NodePort |
| `OperationalActivityEdge` | ControlFlow | - | - |
| `OperationalExchange` | InformationFlow | Node | Node |
| `OperationalMessage` | Sequence | - | - |
| `OrganizationalProjectRelationship` | Dependency | ActualProject | ActualOrganizationalResource |
| `Overlap` | Dependency | UPDMElement | any model element |
| `OwnsProcess` | Dependency | ActualOrganizationalResource | Process |
| `ProjectActivityEdge` | ControlFlow | - | - |
| `ProjectOwnership` | Dependency | ActualProject (as OrganizationalProjectRelationship) | ActualOrganizationalResource (as OrganizationalProjectRelationship) |
| `ProjectSequence` | Dependency | ActualProject | ActualProject |
| `ProvidesCompetence` | Dependency | CompetenceProvider | Competence |
| `RequiresCompetence` | Dependency | CompetenceRequirer | Competence |
| `ResourceConnector` | Connector | ResourcePort | ResourcePort |
| `ResourceInteraction` | InformationFlow | SystemResource | SystemResource |
| `ResourceInterface` | Connector | ResourceRole | ResourceRole |
| `ResourceMessage` | Sequence | - | - |
| `SameAs` | Dependency | UPDMElement | any model element |
| `ServiceFunctionEdge` | ControlFlow | - | - |
| `ServiceMessage` | Sequence | - | - |
| `SkillOfPersonType` | Dependency | CompetenceProvider (as ProvidesCompetence) | Competence (as ProvidesCompetence) |
| `Trustline` | Dependency | Node | Node |

The From and To columns restate the end sets of the language guide beside EA's connector type, so both show in one place; where they differ from the guide, the guide is the authority. Ends that the standard names by an abstract grouping stand for the concrete stereotypes under it. Needline, ResourceInterface and ResourceConnector are connectors between parts or ports (`NodeRole`, `NodePort`, `ResourceRole`, `ResourcePort`), not between the types.

Illustration (Westbrook Bank is fictitious): the Node `Retail Banking Operations` (`Node`) exhibits (`Exhibits`) the Capability `Business Account Opening` (`Capability`); the OperationalActivity `Verify Applicant Identity` maps to that capability (`MapsToCapability`) and the node is capable of performing it (`IsCapableOfPerforming`). An ActualPerson fills (`FillsPost`) an ActualPost. A Function `Check Identity` implements the activity (`Implements`). The views drawn from this are `UPDM2_OV::OV-2`, `UPDM2_StV/CV::CV-2`, `UPDM2_SV/SvcV::SV-1` and `UPDM2_OV::OV-4 Typical`.

## Containment, typing and what the validator cannot read

- **A role belongs to a class and is typed.** The 18 role stereotypes (`NodeRole`, `ResourceRole`, `ConceptRole`, `EnvironmentProperty` and the others) are Parts, children of the owner class (`ParentID`), and a Part is typed by a classifier (`t_object.Classifier`). Ports (`NodePort`, `ResourcePort`, `Service`, `Request`) are children of the class that owns them. Operations and parameters have owners as well. A ruleset that selects by stereotype cannot read a type. It can read an owner: `contained_in` checks what an element is attached to (its `ParentID`, else its package) and `contains_count` bounds an element's children, so a ruleset can check that a `NodeRole` sits under a node or a logical architecture and that a node holds no `ResourcePort`. It cannot read the owner of an operation or of a connector (an activity edge, a message), or an attribute that is not an element.
- **A second stereotype is invisible to the validator.** `t_object.Stereotype` holds only the first stereotype; compliance level 1 requires SysML's `block`, `ValueType`, `ItemFlow`, `FlowPort` or `Requirement` on the same element, and that second stereotype is only in the `t_xref` row (measured: `StereotypeEx = "UPDM2::Node,SysML1.4::block"` stores `Node`). Apply the UPDM stereotype first so that a ruleset sees it.
- **Generalization carries no stereotype**, so the profile's specialization hierarchy is not stored on the model: the Node `Retail Banking Operations` is a Node because it carries `Node`, not because of anything it specializes. A rule can select a generalization by EA connector type (`Generalization`) and count them, but cannot follow one to the class it leads to.
- **What an exchange conveys is not a tagged value.** `OperationalExchange` has the tag `exchangeKind`; the element it conveys is not stored as a tag, so the rules that tie the kind to the conveyed element (UPDM-XCH) cannot be read by a ruleset.
- **Annotations are Notes and NoteLinks.** `ArchitectureMetadata`, `Information`, `Definition`, `Alias`, `StandardConfiguration` and `StereotypeExtension` are Notes; a Note is normally attached to what it annotates by a NoteLink, a connector with no stereotype (not measured here). A connector selector can now match it by type (`connector_types: [NoteLink]`), but a rule cannot say that a note of one stereotype may annotate only one kind of element, so the annotation rules (UPDM-END-066 to 074) are not in the ruleset.

## What EA does that the standard does not

- `UPDMPackage`, the container with the tags `VIEWID` and `VIEWTYPE`, applied to packages, artifacts and text.
- The diagram types `AV-3` and `UPDM Framework`, and the DoDAF and MODAF framework patterns and the example model in EA's model patterns (`up2.0-dodaf-framework`, `up2.0-modaf-framework`, `up2.0-example-model`).
- Package-form stereotypes: the standard's `ArchitecturalDescription`, `View`, `Viewpoint`, `ServiceDescription`, `LogicalDataModel`, `PhysicalDataModel` are applied to packages (or Package elements).
- A tag `isEncapsulated` on Class-based stereotypes such as `Node`, inherited from the Class form.

## What the standard has that EA does not

- **The 48 concepts with no stereotype** (listed in `ea.yaml`, status `abstract-no-stereotype` or `not-in-ea`). The abstract groupings need no stereotype; apply a concrete one. The rest are: the information-exchange elements of SOPES (`Semantic`, `Transactional`, `Wrapper`, `Contract` and their attributes), `DesignRule`, `OntologyReference`, `ProjectStatus`, `ActualProperty`, `ActualMeasurement`, `ActualOrganizationRole`, `ActualProjectMilestoneRole`, `ServiceLevelValue`, `ServiceFeature`, `ServicePort`, `ProtocolImplementation`, `DataModel` and `ISO8601DateTime`. Model an instance's slot values and a SOPES element as ordinary UML.
- **Environment Elements and Measurements** have no diagram type.
- **The 47 products' admitted-element lists** are not stored anywhere EA exposes; the Views, Searches and Model Templates nodes on the Resources tab were not read. The Toolboxes node lists about 49 toolboxes, named by view. The OV-2 toolbox has one page, "OV-2" (Actual Location, Capability, Condition, Environment, Exhibits, Implements, Is Capable of Performing, Known Resource, Logical Architecture, Needline, Node, Node Operation, Node Port, Node Role, Operational Activity, Operational Exchange, Operational Parameter, Performer, Problem Domain, Security Domain, Trustline), and an "All UPDM Stereotypes" page that was not read. From a Node the quick links offer one UPDM pair, Exhibits to a Capability. Other toolboxes and quick-link sources were not read (measured on EA 17.1 build 1716, 2026-11-04).

## Traps found

1. **Use `UPDM2::`.** Not `UPDM::`, `UPDM2.0::`, `UPDM2.1::` or `UPDM 2.0::`; the Resources tab says UPDM 2.0, the API says version 2.1, and the id is UPDM2.
2. **The qualified type resolves to a form, not always an element.** At package level `AddNew(name, "UPDM2::<n>")` is refused for 59 names: "Invalid type" for the 42 connectors (use `Connectors.AddNew`), the 4 operations (apply it to an operation) and the 6 package forms (use a Package element); "Invalid parent for Port (Package)" for the 4 ports and "Invalid parent for ActivityParameter (Package)" for the 3 parameters (create them under a class and an activity). In the probe a refused Port or parameter still left an unnamed Port or ActivityParameter object in the package: check what you created.
3. **A Port needs a host.** `NodePort`, `ResourcePort`, `Service` and `Request` are refused in a package.
4. **Parts and the diagram.** Adding a Part to a diagram object after its parent, at a position outside the parent, threw "The server threw an exception" in one test (in another layout it worked); adding the parts before their parent worked every time.
5. **An abstract name cannot be applied.** `CompetenceProvider`, `SystemResource`, `NodeParent` and the other groupings are not stereotypes. Apply a concrete one (the list is in `ea.yaml`, `use_instead`).
6. **Second stereotypes.** Apply the UPDM stereotype first; SysML's `block` after it. `t_object.Stereotype` holds only the first.
7. **The aliases are their own stereotypes.** A rule about `IsCapableOfPerforming` or `Exhibits` must also name `ActivityPerformedByPerformer` and `CapabilityOfPerformer`; a ruleset generated from the language guide does.
8. **A diagram token that does not bind gives a plain Class diagram with no error** (`UPDM2::OV-1`, `OV-1`, `SV/SvcV::SV-12`). The tokens that bind are the 74 in `ea.yaml`.
9. **Package forms as connector ends.** `ArchitecturalReference` joins two `ArchitecturalDescription`s; for a connector to reach one it must be an element of type Package (the package's own `t_object` row also works).
10. **`UPDMPackage` has three rows** (Package, Artifact, Text) and the tags `VIEWID` and `VIEWTYPE`; it is EA's, not the standard's.
11. **Case.** A ruleset selector compares the stored string exactly: `OperationalActivity`, `ActualPerson`. EA's own binding ignores case and stores the standard's spelling (`UPDM2::node` stores `Node`, measured through the API), so write selectors in the standard's spelling.
12. **A `ResourcePort` on a system resource or a participant is reported.** UPDM-OWN-018 and UPDM-OWN-033 (UPDM2-OWN-018 and UPDM2-OWN-033 in the ruleset) report a `ResourcePort` owned by a system resource or a participant (a `System`, a `ResourceArtifact` and the others), as the standard is written: every port of a system resource or participant is a service port (`Request` or `Service`), while a `ResourceConnector` joins `ResourcePort`s (UPDM-END-024). UPDM2-OWN-018 is a warning, because the standard conflicts with itself on this point. UPDM2-OWN-033 is an error. A `Node`, a `Performer` and a `SecurityDomain` follow UPDM-OWN-003 instead, which is the standard's more specific clause: a `NodePort` or a service port is allowed on them, and UPDM2-OWN-003 reports a `ResourcePort` there. Measured on EA 17.1 build 1716, 2026-11-05: Sparx's shipped UPDM model patterns hold 12 `ResourcePort`s, all on a `ResourceArtifact`, in 7 patterns, and 8 `NodePort`s, all on a `Node`. They hold no `Service` or `Request` port, and no port on an element stereotyped `System`. With nine of those patterns imported as files into a copy of a model, not through the Model Builder, the two rules as they stood before they were changed added 28 error findings: 10 from UPDM2-OWN-018, and 18 from UPDM2-OWN-033, including 8 on a `Node` holding a `NodePort`. Both rules changed after that run: UPDM2-OWN-033 no longer selects a `Node`, a `Performer` or a `SecurityDomain`, so the findings on a `Node` no longer apply, and UPDM2-OWN-018 is now a warning, so its findings are warnings. The pattern run was not repeated with the rules as they ship, so there is no measured count for them. Expect a model built from these patterns to report its `ResourcePort`s on a `ResourceArtifact`.
13. **Direction.** A connector is read as EA stores it: Dependency from client to supplier, InformationFlow from its information source. A connector drawn the other way is judged the other way. EA does not stop the wrong way round: the `Implements` toolbox tool accepted it on screen (EA 17.1 build 1716, 2026-11-04).

## Checking a model

88 of 88 rules in this ruleset use formats newer than 3.6.4, and on that server they report nothing or don't run as written. Use server 3.6.5 or later, because a clean result on 3.6.4 doesn't mean the model passes.

The ruleset is `rulesets/updm-2/updm-2_rules.yaml`, with 88 rules.

# Modeling TOGAF 9.1 in Sparx Enterprise Architect

How to model the content metamodel of the TOGAF skill the way Sparx's built-in technology does it. The technology is `TOGAF` to EA's API; its stereotypes are qualified `TOGAF::<name>`, and a second profile of the same technology, IEEE1471, is qualified `IEEE1471::<name>`. Measured on EA 17.1 build 1716 by creating one element, connector, attribute and diagram of each kind and reading the stored rows back; `ea.yaml` holds the facts. Westbrook Bank (fictitious) appears only as an illustration; your model has its own names, and nothing here assumes it contains Westbrook's.

## Version

**The skill and this guide describe TOGAF 9.1. Which edition EA's technology follows is not proven.** The evidence supports 9.1, and it stops short of settling it.

- EA reports its technology as version `3.0` (`GetTechnologyVersion("TOGAF")`), which names no edition, and the technology file is encrypted.
- One Sparx regional page says TOGAF 9.1 is supported in build 3.0 of the technology. Sparx's 17.1 guide says version 9.x and never 9.1 or 9.2.
- All six shipped TOGAF patterns are named `to9.1-*`, and five of them were exported after 9.2 launched in April 2018.
- The stored names include `PlatformService` and have no `TechnologyService`, `BusinessCapability` or `ValueStream`, which a third-party list gives as 9.2 names. That list is not The Open Group's text.

Reading The Open Group's 9.2 metamodel chapter is what would settle it, and nobody has done that. The TOGAF Standard 10th Edition (2022) wasn't studied either.

## Does EA have the content metamodel? Mostly, under its own names

EA ships the metamodel as stereotypes, not as a metamodel: 204 stereotypes in the TOGAF profile and 16 in IEEE1471 (counted by stored name; the IEEE1471 profile lists 16 rows on the Resources tab, read on EA 17.1 build 1716, 2026-11-04), of which the 55 concepts of the skill map as follows. Of the 55: **30** have a stereotype of the same name (`PlatformService` among them: only the tab prints it as `Platform Sevice`), **6** are stored under another name (`BusinessDriver`, `BusinessFunction`, `BusinessRequirement`, `ABB`, `SBB`, and `ITService` for Information System Service, which is a working assumption of 2026-10-21), **12** are stored by the IEEE1471 profile (the architecture description vocabulary of Figure 35-1), and **7 have no stereotype**: Service, Deliverable, Artifact, Catalog, Matrix, Diagram and Building Block. The other stereotypes (about 170) are EA extras (see below).

Each mapping was confirmed by binding the stored name in EA and by the tags agreeing with the standard's attributes (for example `BusinessRequirement` carries `Rationale` and `AcceptanceCriteria`). The map is in `ea.yaml` under `concepts`; the tables below give the same facts for reading.

**EA has a stereotype of the same name (30)**

| Concept | Stored stereotype | Metaclass | Create with | Note |
|---|---|---|---|---|
| Actor | `Actor` (TOGAF) | Actor | type `TOGAF::Actor` |  |
| Application Component | `ApplicationComponent` (TOGAF) | Component | type `TOGAF::ApplicationComponent` |  |
| Assumption | `Assumption` (TOGAF) | Artifact | type `TOGAF::Assumption` |  |
| Business Service | `BusinessService` (TOGAF) | Activity | type `TOGAF::BusinessService` |  |
| Capability | `Capability` (TOGAF) | Class | type `TOGAF::Capability` |  |
| Constraint | `Constraint` (TOGAF) | Constraint | type `TOGAF::Constraint` |  |
| Contract | `Contract` (TOGAF) | Collaboration | type `TOGAF::Contract` |  |
| Control | `Control` (TOGAF) | Object | type `TOGAF::Control` | the tab lists Control twice; the object is an Object; no connector stereotype Control binds |
| Data Entity | `DataEntity` (TOGAF) | Class | type `TOGAF::DataEntity` |  |
| Event | `Event` (TOGAF) | Event | type `TOGAF::Event` |  |
| Gap | `Gap` (TOGAF) | Class | type `TOGAF::Gap` |  |
| Goal | `Goal` (TOGAF) | Requirement | type `TOGAF::Goal` |  |
| Location | `Location` (TOGAF) | Node | type `TOGAF::Location` |  |
| Logical Application Component | `LogicalApplicationComponent` (TOGAF) | Component | type `TOGAF::LogicalApplicationComponent` |  |
| Logical Data Component | `LogicalDataComponent` (TOGAF) | Component | type `TOGAF::LogicalDataComponent` |  |
| Logical Technology Component | `LogicalTechnologyComponent` (TOGAF) | Component | type `TOGAF::LogicalTechnologyComponent` |  |
| Measure | `Measure` (TOGAF) | Class | type `TOGAF::Measure` |  |
| Objective | `Objective` (TOGAF) | Artifact | type `TOGAF::Objective` |  |
| Organization Unit | `OrganizationUnit` (TOGAF) | Actor | type `TOGAF::OrganizationUnit` |  |
| Physical Application Component | `PhysicalApplicationComponent` (TOGAF) | Component | type `TOGAF::PhysicalApplicationComponent` |  |
| Physical Data Component | `PhysicalDataComponent` (TOGAF) | Component | type `TOGAF::PhysicalDataComponent` |  |
| Physical Technology Component | `PhysicalTechnologyComponent` (TOGAF) | Component | type `TOGAF::PhysicalTechnologyComponent` |  |
| Platform Service | `PlatformService` (TOGAF) | Activity | type `TOGAF::PlatformService` | the tab prints 'Platform Sevice'; the stored name is PlatformService |
| Principle | `Principle` (TOGAF) | Class | type `TOGAF::Principle` |  |
| Process | `Process` (TOGAF) | Activity | type `TOGAF::Process` |  |
| Product | `Product` (TOGAF) | Class | type `TOGAF::Product` |  |
| Role | `Role` (TOGAF) | Object | type `TOGAF::Role` |  |
| Service Quality | `ServiceQuality` (TOGAF) | Class | type `TOGAF::ServiceQuality` |  |
| Technology Component | `TechnologyComponent` (TOGAF) | Component | type `TOGAF::TechnologyComponent` |  |
| Work Package | `WorkPackage` (TOGAF) | Package | a Package + `StereotypeEx` | stored on an element of type Package (the qualified type is refused); EA's Project (a Class) is a different stereotype |

**EA stores it under another name (6)**

| Concept | Stored stereotype | Metaclass | Create with | Note |
|---|---|---|---|---|
| Driver | `BusinessDriver` (TOGAF) | Requirement | type `TOGAF::BusinessDriver` | EA's BusinessDriver; tags ID, Version, Category, Source, Owner |
| Function | `BusinessFunction` (TOGAF) | Activity | type `TOGAF::BusinessFunction` | EA's BusinessFunction; carries the standards-class tags |
| Information System Service | `ITService` (TOGAF) | Class | type `TOGAF::ITService` | Working assumption, 2026-10-21: Information System Service is ITService. Measured: TOGAF::ITService is a stereotype on a Class that carries the five standards-class tags of the standard (the first spelled StandardClass, not StandardsClass) beside ITIL-like tags (DefinitionText, ContactPoint, ChargeToUser). TOGAF9-ATTR-002 reads StandardClass on it, and TOGAF9-DEF-003 (a service is owned and governed by an Organization Unit) selects it as well. The guide has one relationship row for it (Automates some or all of) and EA has no connector stereotype of that name, so it is not in the relationship table; as a specialization of Business Service it has the table cells of BusinessService, as source and as target |
| Requirement | `BusinessRequirement` (TOGAF) | Requirement | type `TOGAF::BusinessRequirement` | EA's BusinessRequirement; tags Rationale, AcceptanceCriteria agree with the standard's attributes (no tag for the statement or for shall/should/may) |
| Architecture Building Block | `ABB` (TOGAF) | Component | type `TOGAF::ABB` | stored ABB; the tab shows 'Architecture Building Block' |
| Solution Building Block | `SBB` (TOGAF) | Component | type `TOGAF::SBB` | stored SBB; the tab shows 'Solutions Building Block' |

**Stored by the IEEE1471 profile (12)**

| Concept | Stored stereotype | Metaclass | Create with | Note |
|---|---|---|---|---|
| System | `System` (IEEE1471) | Component | type `IEEE1471::System` |  |
| Architecture | `Architecture` (IEEE1471) | Class | type `IEEE1471::Architecture` | the same stored name exists in both profiles (TOGAF::Architecture and IEEE1471::Architecture) |
|  | `Architecture` (TOGAF) | Class | a Class + `StereotypeEx` |  |
| Architecture Description | `ArchitecturalDescription` (IEEE1471) | Artifact | a Artifact + `StereotypeEx` | the stored name is ArchitecturalDescription |
| Stakeholder | `Stakeholder` (IEEE1471) | Actor | type `IEEE1471::Stakeholder` |  |
| Concern | `Concern` (IEEE1471) | UseCase | type `IEEE1471::Concern` |  |
| View | `View` (IEEE1471) | Class | type `IEEE1471::View` |  |
| Viewpoint | `Viewpoint` (IEEE1471) | Class | type `IEEE1471::Viewpoint` |  |
| Library Viewpoint | `LibraryViewpoint` (IEEE1471) | Package | a Package + `StereotypeEx` | IEEE1471::LibraryViewpoint on an element of type Package |
| Model | `Model` (IEEE1471) | Class | type `IEEE1471::Model` |  |
| Mission | `Mission` (IEEE1471) | Artifact | a Artifact + `StereotypeEx` | IEEE1471::Mission; the qualified type is refused, made as an Artifact with StereotypeEx |
| Environment | `Environment` (IEEE1471) | Class | type `IEEE1471::Environment` | the same stored name exists in both profiles (TOGAF::Environment and IEEE1471::Environment) |
|  | `Environment` (TOGAF) | Class | type `TOGAF::Environment` |  |
| Rationale | `Rationale` (IEEE1471) | Artifact | type `IEEE1471::Rationale` |  |

**EA has no stereotype (7)**

| Concept | Stored stereotype | Metaclass | Create with | Note |
|---|---|---|---|---|
| Service | none | | | abstract in the guide; EA has BusinessService, ITService (the guide's Information System Service) and PlatformService, no parent |
| Deliverable | none | | | no stereotype; the nearest are RequestForArchitectureWork and StatementOfArchitectureWork (Artifacts) for two named deliverables |
| Artifact | none | | | no stereotype |
| Catalog | none | | | no stereotype; EA's catalogs pattern holds six model views on a TOGAF_ACM diagram |
| Matrix | none | | | no stereotype; EA's own matrices are not part of the technology |
| Diagram | none | | | no stereotype |
| Building Block | none | | | no stereotype; ABB and SBB cover the two kinds |

Notes on the map.

- **Service has no parent stereotype.** Model a service as `BusinessService`, `PlatformService` or `ITService`; the guide's abstract Service is a way of reading them. The Information System Service of the Services extension is `ITService`: that is a working assumption (2026-10-21), not something EA states. Measured: `TOGAF::ITService` is a stereotype on a Class that carries the five standards-class tags of the standard (the first spelled `StandardClass`) beside ITIL-style tags (`DefinitionText`, `ContactPoint`, `ChargeToUser`, `DependentSystems`). The ruleset rule TOGAF9-ATTR-002 reads `StandardClass` on it, and TOGAF9-DEF-003 (a service is owned and governed by an Organization Unit) selects it as well. The guide has one relationship row for it (Automates some or all of) and EA has no connector stereotype of that name, so that row is not in the relationship table; the standard makes it a specialization of Business Service, so `ITService` has the table cells of `BusinessService`, as source and as target.
- **Extension modules are not in EA.** Nothing marks an element as core or as belonging to the Governance, Services, Process Modeling, Data, Infrastructure Consolidation or Motivation extension; the guide's module of each entity is knowledge in the skill. Contract, Measure and Service Quality exist whether or not the Governance extension is used.
- **Catalogs, matrices and diagrams are not elements.** The standard's 56 artifacts have no stereotype and no diagram type of their own (see below); model a catalog as a package or a model view, a matrix as an EA matrix or a diagram, and keep the artifact's name in the element name.
- **Building blocks.** `ABB` and `SBB` are the two kinds; there is no stereotype for the general Building Block.
- **Where the stakeholder vocabulary lives.** Stakeholder, Concern, View, Viewpoint, Library Viewpoint, Model, Mission, Environment, Rationale, System, Architecture and Architecture Description are `IEEE1471::` stereotypes. `Architecture`, `Environment` and `Supplier` also exist in the TOGAF profile under the same stored name: the qualified form is only in `t_xref`, so a selector cannot tell the two apart.

## Stored names: never the spaced display text

The Resources tab shows `Business Service`, `Organization Unit`, `Platform Sevice`. **Those are display text.** `t_object.Stereotype` holds `BusinessService`, `OrganizationUnit`, `PlatformService`; a spaced spelling passed as a type creates nothing (the one exception that binds is `TOGAF::In Contract`, stored `InContract`). The tab also hides some names behind other spellings, found by trying and by the tab's own sort order (it is sorted by stored name):

- the ten ADM phases carry an `ADM_` prefix (`ADM_Preliminary`, `ADM_ArchitectureVision`, ..., `ADM_RequirementsManagement`) and the flow connector is `ADM_Flow`;
- abbreviations: `ABB` (Architecture Building Block), `SBB` (the tab prints Solutions Building Block), `SIB` (Standards Information Base), `BOD` (Board Of Directors), `ServiceLevelAgreement` (SLA), `OperationLevelAgreement` (OLA, with *Operation*, not *Operational*);
- the tab's misspellings `Platform Sevice` and `Solitions Continuum` are display text; the stored names are `PlatformService` and `SolutionsContinuum`;
- `influence` (the Influence connector) is stored in lower case. A name matches without regard to case when you create the object, but a ruleset selector compares the stored string exactly.

## Relationships: the connector stereotype is the verb

The relationship names of the standard's table (34.7) are mostly EA connector stereotypes, in the verb form: Decompose, Contain, Resolve, Generate, Produce, Perform, Owns, OwnsAndGoverns, OperatesIn, BelongsTo, IsHostedIn, Encapsulate, Extend, Supply, Meets, AppliesTo and so on. 104 of the table's 143 rows (39 stereotypes) map to one; the table is generated into the ruleset as `togaf-9-relationships`. Draw the connector **from the entity that does the verb** (an Organization Unit `Contain`s an Actor; a Driver `Motivate`s an Organization Unit). The passive wording of the standard ("Is owned by", "Is produced by") is the same stereotype drawn the other way. EA enforces no direction or pair, and no Sparx pattern shows a direction; this reading is the plan's.

The connector stereotypes used by the table: `Access`, `AppliesTo`, `BelongsTo`, `Communicate`, `Consume`, `Contain`, `Create`, `Decompose`, `Deliver`, `Encapsulate`, `EnsureCorrectOperationOf`, `Extend`, `Generate`, `GovernsAndMeasures`, `Identify`, `Implement`, `influence`, `InteractsWith`, `IsAccessedAndUpdatedThrough`, `IsHostedIn`, `IsProcessedBy`, `Meets`, `Motivate`, `OperatesIn`, `OperatesOn`, `Orchestrate`, `Owns`, `OwnsAndGoverns`, `ParticipatesIn`, `Perform`, `PerformsTaskIn`, `Produce`, `Provide`, `ProvideGovernedInterface`, `ProvidesPlatformFor`, `Resolve`, `SetPerformanceCriteriaFor`, `Supply`, `Supports`.

The other 39 rows have no stereotype: "Is realized by" and "Realizes", "Is dependent on", "Has", "Relates to", "Is bounded by" (Function to Business Service), "Is tracked against", "Is implemented on", "Resides within" and others. Draw them with plain UML connectors (Realization, Dependency, Association); the validator cannot select a connector without a stereotype.

EA's connector stereotypes that are not in the table (38) come from its enterprise and motivation modeling, not the content metamodel: for example `Guides`, `Supervise`, `WorksFor`, `ActsAs`, `Require`, `Governs`, `Amplify`, `Quantify`, `Include`, `Use`, `DataExchange`, `ABBMapping`, `SBBMapping`. `Use` is made with the EA connector type `UseCase` and `StereotypeEx`; `Control` has no connector stereotype.

## Which diagram type for which view

| View (skill) | EA diagram type | Stored as |
|---|---|---|
| ADM phase diagrams | `TOGAF Diagrams::TOGAF_ADM` | Custom, `MDGDgm=TOGAF Diagrams::TOGAF_ADM;` |
| Enterprise Continuum | `TOGAF Diagrams::TOGAF_EnterpriseContinuum` | Logical |
| Architecture description concepts (Figure 35-1) | `TOGAF Diagrams::IEEE1471_ConceptualFramework` | Logical |
| Catalogs (the Sparx catalogs pattern holds model views on this type) | `TOGAF Diagrams::TOGAF_ACM` | Custom |
| Standards Information Base | `TOGAF Diagrams::TOGAF_SIB` | Custom |
| Interface | `TOGAF Diagrams::TOGAF_Interface` | Logical |
| Data map | `TOGAF_DataArchitecture::TOGAF_DataMap` | UMLDiagram |
| The 14 catalogs, 10 matrices and 32 diagrams of the standard (35.6) | none among the seven tokens above (by name, only Benefits matches an artifact; see below) | use a Class, Component, Activity or Deployment diagram, EA's matrix, or the generic types above |

Trap: the starter model pattern records the token `TOGAF Diagrams::TOGAF_OrganizationStructure`. It does not bind; asking EA for a diagram of that type gives a plain Class diagram with no error. On the Resources tab the type Organization Structure sits in the group `TOGAF_BusinessArchitecture`, not in `TOGAF Diagrams`; whether a token with that group binds was not tested.

**The Resources tab lists 17 diagram types, not 7** (measured on EA 17.1 build 1716, 2026-11-04). The seven tokens above are the ones that bound through the API; the tab shows display names in four groups, and they were not matched to tokens, so the table lacks ten types:

| Group on the tab | Types |
|---|---|
| FEAF Diagrams | (FEAF) Business Reference Model, (FEAF) Service Component Reference, (FEAF) Technical Reference, (FEAF) Performance Reference (names cut off at the panel edge) |
| TOGAF_BusinessArchitecture | Business Motivation Model, Organization Structure, Business Logistics, Business Process, Benefits |
| TOGAF_DataArchitecture | Data Map |
| TOGAF Diagrams | TOGAF Interface, Conceptual Framework, Architecture Content, Architecture Development (cut off), Service Model, Enterprise Continuum, Standards Information Base |

Compared by name only, one tab type, Benefits, has the same name as an artifact (the Benefits diagram); four are FEAF reference models, and the other twelve share no name with any of the 56 artifacts. Whether any tab type is meant for an artifact, or can draw one, was not tested.

**Toolboxes and quick links** (same date). The tab lists 16 toolboxes. A diagram of type Architecture Content shows these pages: ACM, Data Modeling Extension, Governance Extension, Infrastructure Consolidation Extension, Motivation Extension, Process Modeling Extension, Services Extension and ACM Relations (44 entries). The toolbox spells Platform Service correctly (the tab prints Platform Sevice). From a Business Function the quick links offer Actor, Organization Unit, Process, Role, Business Function, Business Service, Assumption, Principle, Business Requirement, Gap and Business Constraint; the submenus opened gave nine relationship pairs (for example Actor: Interacts With, Perform, Support; Process: Supports, Realization, ControlFlow, Decompose). The Actor menu shows `Support` where the tab has `Supports`; not checked further. The other 15 toolboxes and other quick-link sources were not read.

## How to say each concept

Create from the type `TOGAF::<name>` in a package. Where the qualified type is refused, make the element as the metaclass and set `StereotypeEx = "TOGAF::<name>"`.

| To model | Create | Set or note |
|---|---|---|
| Actor, Organization Unit, Role, Event, Location, Contract | the stereotype, from its qualified type | Role is an Object, Contract a Collaboration, Location a Node |
| Business Service, Function, Process | `BusinessService`, `BusinessFunction`, `Process` (Activity elements) | tag `StandardsClass` |
| Data Entity, Capability, Gap, Measure, Principle, Product | the stereotype (Class elements) | Principle tags `Statement`, `Rationale`, `Implications`, `Type`, `Priority`, `Metric` |
| Application, Data, Technology Component (logical and physical) | the stereotype (Component elements) | `LifeCycleStatus` on the Physical Application Component only |
| Work Package | an element of **type Package** with `StereotypeEx = "TOGAF::WorkPackage"` | tag `Category` |
| ADM phase | an element of type Package with `StereotypeEx = "TOGAF::ADM_<Phase>"` | tag `IterationNumber`; a package made with `Packages.AddNew` stores no stereotype |
| Driver, Goal, Objective | `BusinessDriver`, `Goal`, `Objective` | a Driver Creates a Goal, Motivates an Organization Unit |
| Requirement | `BusinessRequirement` (a Requirement element) | tags `Rationale`, `AcceptanceCriteria`; there is no field for shall, should or may |
| Stakeholder, Concern, Viewpoint, View, Model | the `IEEE1471::` stereotype | `Stakeholder` carries `Class`, `Power`, `LevelOfInterest` |
| Architecture Description, Mission, Library Viewpoint | `IEEE1471::ArchitecturalDescription` and `IEEE1471::Mission` (Artifacts, made with the metaclass and `StereotypeEx`); `IEEE1471::LibraryViewpoint` (Package) | |
| SWOT strength, weakness, opportunity, threat | a class **attribute** with `StereotypeEx = "TOGAF::Strength"` and so on | applied to an element they bind nothing, with no error |

Illustration (Westbrook Bank is fictitious): the Organization Unit `Card Payments` (`OrganizationUnit`) `OwnsAndGoverns` the Business Service `Card Authorization Service` (`BusinessService`, `StandardsClass` = `Standard`), `Contain`s the Actor `Payments analyst`, and `Produce`s the Product `Westbrook Debit Card`. The Physical Application Component `Authorization engine v4` (`LifeCycleStatus` = `Live`) `Extend`s the Logical Application Component `Authorization engine (logical)` and `IsHostedIn` the Location `Westbrook data center`. The Principle `Data is an asset` has `Rationale` and `Priority` set.

## Tagged values: EA's names and value sets are not the standard's

EA creates the tags with the stereotype and leaves them empty; it checks no value. Use these names (the standard's attribute is in brackets):

- **Standards class** (Standards class): tag `StandardsClass` (`StandardClass` on `ITService`, which TOGAF9-ATTR-002 also checks, `Categoy` is a typo on `DataComponent`). EA's list is `Non-Standard, Proposed, Provisional, Standard, Phasing-Out, Retired`; the standard writes "Proposed Standard", "Provisional Standard", "Phasing-Out Standard", "Retired Standard". Use EA's spelling.
- **Principle category**: tag `Type`; EA offers Business, Data, Application, Technology, Architecture, Testing, Management, Security, Guiding, Integration. The standard has six (Guiding, Business, Data, Application, Integration, Technology); Architecture, Testing, Management and Security are EA's additions.
- **Work package category**: tag `Category`; EA's list is exactly the standard's five.
- **Data entity category** and **Location category**: free-text `Category`; the standard's Message and Internally Stored Entity are not offered.
- **Lifecycle status** of a Physical Application Component: free-text `LifeCycleStatus`.
- Tags exist for entities with no attributes in the standard (the ADM phase `IterationNumber`, Contract's thirty service characteristics, Stakeholder power and interest), and the standard's `Statement of requirement`, `Business value` and the like appear as `AcceptanceCriteria`, `BusinessValue` and so on under other names.

## What EA does that the standard does not

- The ADM (ten phase packages and the `ADM_Flow` connector), the Enterprise Continuum, the Standards Information Base and the Architecture and Solutions Continuum packages: TOGAF, but not the content metamodel.
- About 65 generic enterprise items (assets, channels such as `Phone` and `SnailMail`, risks, strategies, influencers, policies, regulations, `SLA` and `OLA` agreements) and 38 connector stereotypes of EA's own. They are bound and cataloged only as far as their names (`ea_only` in `ea.yaml`).
- Stakeholder-class stereotypes in IEEE1471 that the standard's Figure 35-1 does not have: Competitor, Customer, Partner and Supplier.
- A tag `Priority`, `Version`, `Source`, `Owner` and `ID` on most stereotypes; `ID` is a tag, not EA's own element id.

## What the standard has that EA does not

- The Service parent, Deliverable, Artifact, Catalog, Matrix, Diagram and Building Block as stereotypes; the extension-module grouping; multiplicities and the pair-by-pair relationship table (EA allows any connector between any two elements).
- A diagram type for each of the 56 named catalogs, matrices and diagrams. Compared by name only, one of the tab's 17 diagram types (Benefits) has the same name as one of the 56 artifacts; whether any artifact can be drawn on a tab type was not tested.
- Named stereotypes for 38 of the table's relationship names ("Is realized by", "Has", ...): plain connectors.

## Traps found

1. **The Resources tab is display text.** Never copy a name from it; use the stored name (above).
2. **A connector stereotype that EA does not know creates a plain connector with no error.** in the probe, 876 of 951 connector attempts with a spelling EA does not know (spaced, abbreviated, misspelled) were created without an error as plain Dependency or Association connectors with no stereotype; check `t_xref` for `FQName`.
3. **An element stereotype that EA does not know throws "Invalid type".** A stereotype that does not extend the metaclass you chose is silently stored as no stereotype when applied with `StereotypeEx`; check `FQStereotype` or the `t_xref` row after `Update()`.
4. **Package-type stereotypes refuse the qualified type.** The ADM phases, Work Package, the continua, SIB and Library Viewpoint need an element of type Package plus `StereotypeEx`. A package created with `Packages.AddNew` and `StereotypeEx` stores nothing. Whether such an element can hold other elements was not tested.
5. **SWOT stereotypes are attribute stereotypes.** Applied to elements or connectors they bind nothing.
6. **The same stored name in two profiles** (`Architecture`, `Environment`, `Supplier`): a selector cannot tell them apart.
7. **A second stereotype is invisible to the validator.** `t_object.Stereotype` holds only the first; the rest are in `t_xref`.
8. **Case.** `influence` is lower case; every other name keeps the case in `ea.yaml`.
9. **Direction.** EA stores whatever direction you draw; the ruleset reads each stereotype as drawn from the doer.
10. **Value sets differ** (standards class, principle type, work package category); a ruleset written from the standard rejects EA's own `Proposed`.
11. **Tags are empty by default**, so a rule that wants a rationale or a priority reports every new Principle until the tags are filled.
12. **Technology version.** `GetTechnologyVersion("TOGAF")` returns `3.0`, not an edition of the standard; `IsTechnologyLoaded("TOGAF9.1")` is False. `IEEE1471` is not a technology id of its own (it is False too); the profile prefix is.
13. **Two rows on the tab** (`Control`, `Solution`) have one stored name each; `Control` is accepted on Object, Collaboration, Component and Node and `Solution` on Class, Package, Component and UseCase, so which two metaclasses the rows are is not known.

## Checking a model

The ruleset is `rulesets/togaf-9/togaf-9_rules.yaml`. 1 of 8 rules in this ruleset use formats newer than 3.6.4, and on that server they report nothing or don't run as written. Use server 3.6.5 or later, because a clean result on 3.6.4 doesn't mean the model passes.

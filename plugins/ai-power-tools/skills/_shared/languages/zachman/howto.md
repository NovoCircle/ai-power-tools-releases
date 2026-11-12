# Modeling the Zachman Framework in Sparx EA

How Sparx EA's built-in Zachman Framework technology represents the framework described in the Zachman language skill, measured on EA 17.1 build 1716 (2026-10-21). The technology is a built-in technology whose definition is encrypted, so every fact here was read from what EA creates and stores and from Sparx's model pattern (`zf1.0-zachman-framework.xml`, read as a file), not from the definition file; `ea.yaml` records the source of each fact. Examples use Westbrook Bank, a fictitious bank, as an illustration: substitute your own enterprise. Nothing here assumes you have any particular model.

**Version.** This guide, the language skill and EA's technology follow the **pre-3.0 form**: rows Planner, Owner, Designer, Builder, Subcontractor and a sixth row Functioning Enterprise; columns Data, Function, Location (the 1992 papers say Network), People, Time, Motivation; the rules as the 1992 paper states them. The author's Zachman Framework 3.0 (2011) renamed columns and rows. EA's pattern is older than 3.0 and nothing here describes 3.0.

## 1. What EA gives you

- **Technology:** Zachman Framework (technology id `ZF`, profile `ZF`), under Resources > MDG Technologies > System Technologies. Create by script with `ZF::<name>`.
- **One cell container, `ZFCell`, and 61 generic stereotypes.** 62 of the 64 names on the Resources tab bind: 44 element stereotypes, 1 package stereotype (`ZFCell`), 17 connector stereotypes. `Person` and `Responsibile` (EA's spelling) are on the tab and bind on nothing that was tried.
- **30 diagram type tokens** kept through the API, and **32 diagram types** on the Resources tab: the `ZF Interface` grid and per-row families (Planner, Owner, Designer, Builder, Subcontractor). Section 5 lists them. Measured on EA 17.1 build 1716, 2026-11-04 for the tab.
- **A model pattern,** `zf1.0-zachman-framework`, with the six row packages, 36 cell packages and example content.
- **29 toolboxes.** Only two diagrams' toolbox pages were read (section 5); quick links were read on one source.

## 2. The framework is not in the technology; only its grid is

The framework defines columns, rows, cells and twelve primitives. **EA binds a stereotype to the cell container (`ZFCell`) and to nothing else of the framework.** The 61 other stereotypes (`BusinessEvent`, `OrganizationUnit`, `Goal`, `Communicate`, `BusinessRule` and so on) are generic enterprise concepts that EA files under the cells. They are not concepts of the framework, and EA states no rule that an element of one stereotype belongs in a cell of one column. Section 4 shows where Sparx's pattern files each of them; that is an example of what a cell can hold, not a definition. A data entity, an application function, a segment, a field, an identity or an interrupt have no stereotype: Sparx's pattern uses plain UML elements and other technologies' stereotypes (`table`, `column`, `entity`, `control`) in those cells.

## 3. How a model records its cell: as a place, not a label

This decides what can be checked.

| What | How EA stores it (measured) |
|---|---|
| A cell | a **package** with the stereotype `ZFCell` (`t_object.Stereotype = ZFCell`, `Object_Type = Package`, FQName `ZF::ZFCell`) |
| The row | the **parent package** of the cell package: an unstereotyped package named Planner, Owner, Designer, Builder, Subcontractor or Functioning Enterprise. The grid draws it under each cell as `(from Owner)` |
| The column | **not stored.** The cell package's name (EA's names, below) and the type of its diagram imply it |
| An element in a cell | `t_object.Package_ID` is the cell package; `ParentID` is 0 |
| A tagged value for row, column or cell | **none**, on the cell and on all 44 element stereotypes |

So EA's Zachman model carries the classification as containment. Nothing stops an element from sitting in no cell, in a second cell (shown on another cell's diagram), in the wrong cell or in a cell that is not under a row: ten defects planted in a sample set were all created without a complaint. Keeping each element in exactly one cell is the modeler's and the reviewer's work.

EA's cell names, one per row and column (from Sparx's pattern; a trailing space in `Executables` is dropped). They differ from the 1992 cell names in `language.yaml`; the column is the stable key.

| Row | A Data | B Function | C Network (EA: Location) | D People | E Time | F Motivation |
|---|---|---|---|---|---|---|
| **1 Planner** | Business Data | Business Process | Business Location | Business Units | Business Events | Business Motivation |
| **2 Owner** | Semantic Data Model | Process Analysis Model | Business Logistics | Work Flow Model | Event Schedule | Business Plan |
| **3 Designer** | Logical Data Model | Application Architecture | Distribution Sys Design | Human I/F Architecture | Processing Structure | Business Rule Model |
| **4 Builder** | Physical Data Model | System Design | Technology Architecture | Presentation Architecture | Control Structure | Rule Design |
| **5 Subcontractor** | Data Definition | Program | Network Architecture | Security Architecture | Timing Definition | Rule Specification |
| **6 Functioning Enterprise** | Actual Data | Executables | Physical Networks | BusinessUnits | Business Schedule | Business Strategy |

## 4. Which stereotype Sparx's pattern files where

Read from the pattern, not from the technology. Cell ids are column letter and row number (`language.yaml`). Counts in brackets where more than one.

| Cell | ZF stereotypes the pattern files there |
|---|---|
| A1 Planner, Business Data | Asset, DocumentAsset, EquipmentAsset |
| B1 Planner, Business Process | BusinessFunction (6) |
| C1 Planner, Business Location | BranchOffice (2), ClientPlace, HeadQuarters, OfficeBlock (2), Supplier; connector Communicate (7) |
| D1 Planner, Business Units | BOD, ExternalOrganization, OrganizationUnit (4); connectors Control (3), InContract |
| E1 Planner, Business Events | BusinessEvent (2) |
| F1 Planner, Business Motivation | Assumption, Goal, Mission, Strategy (2) |
| A2 Owner, Semantic Data Model | IntersectingEntity, PrincipalEntity (3), StructureEntity |
| C2 Owner, Business Logistics | Internet, Intranet, Phone; connector Communicate |
| E2 Owner, Event Schedule | BusinessCycle, BusinessEvent (4), EventNode (5) |
| F2 Owner, Business Plan | BusinessPerspective (4), Strategy (6); connector StrategyLink (5) |
| C3 Designer, Distribution Sys Design | PC, Processor, Registry, StorageDevice (2), WebService |
| F3 Designer, Business Rule Model | BusinessRule (2); connectors basedOn, exceptionTo, implements, replaces |
| F4 Builder, Rule Design | FormalRule (2) |
| F5 Subcontractor, Rule Specification | RIC |

Every other cell holds only plain UML elements or other technologies' stereotypes, and row 6 holds nothing. Stereotypes on the tab that the pattern files in no cell: AppliedTo, BusinessEntity, BusinessProcess, File, InPerson, Invokes, Location, Personnel, Principle, SalesAgent, SnailMail, Standard, Supervise, Trigger, Validates, WorksFor, conflict, equivalentTo, violates. Where the language skill classifies a concept into a cell and the pattern files nothing there (a business entity in A2, a business process in B2, a role in D3), the choice is the skill's and the modeler's, not EA's.

By column, in the language skill's terms (a reading of the pattern, with the framework's primitive in brackets): data cells hold entity-like stereotypes (entity); function cells BusinessFunction (function); network cells places and devices, with Communicate as the connector (node, link); people cells organization units and the Control and InContract connectors (agent, work); time cells BusinessEvent, EventNode and BusinessCycle (time, cycle); motivation cells goals, strategies, rules and the rule connectors (ends, means).

## 5. Diagram types

The framework defines no diagram types. EA's technology gives the matrix a diagram and most cells one:

| Standard | EA diagram type |
|---|---|
| The matrix (36 cells) | `ZF Interface::ZF_Interface` (stored as a Logical diagram; the pattern has one, called Zachman Framework) |
| A cell's model | the cell's own type, in the grid below |

| Row | A Data | B Function | C Network (EA: Location) | D People | E Time | F Motivation |
|---|---|---|---|---|---|---|
| **1 Planner** | `ZF Planner::PlannerData` | `ZF Planner::PlannerFunction` | `ZF Planner::PlannerLocation` | `ZF Planner::PlannerPeople` | `ZF Planner::PlannerTime` | `ZF Planner::PlannerMotivation` |
| **2 Owner** | `ZF Owner::OwnerData` | `ZF Owner::OwnerFunction` | `ZF Owner::OwnerLocation` | none | `ZF Owner::OwnerTime` | none |
| **3 Designer** | `ZF Designer::DesignerData` | `ZF Designer::DesignerFunction` | `ZF Designer::DesignerLocation` | `ZF Designer::DesignerPeople` | `ZF Designer::DesignerTime` | `ZF Designer::DesignerMotivation` |
| **4 Builder** | `ZF Builder::BuilderData` | `ZF Builder::BuilderFunction` | `ZF Builder::BuilderLocation` | `ZF Builder::BuilderPeople` | `ZF Builder::BuilderTime` | `ZF Builder::BuilderMotivation` |
| **5 Subcontractor** | `ZF Subcontractor::SC_Data` | none | `ZF Subcontractor::SC_Location` | `ZF Subcontractor::SC_People` | `ZF Subcontractor::SC_Time` | `ZF Subcontractor::SC_Motivation` |
| **6 Functioning Enterprise** | none | none | none | none | none | none |

Also real: `ZF Owner::BPMN` and `ZF Owner::StrategyMap` (the pattern uses `StrategyMap` in the owner's Business Plan cell). That makes 27 cell types, the grid, and those two: 30.

**The Resources tab lists 32 diagram types, not 30** (measured on EA 17.1 build 1716, 2026-11-04). The tab shows friendly names in six groups, not tokens, so it cannot be matched one to one with the tokens above. Planner, Builder and Subcontractor each have cell types:

| Group on the tab | Types |
|---|---|
| Planner (Zachman Framework), 6 | Business Data, High Level Business Process, Business Locations, Organization Chart, Business Events, Business Motivation |
| Owner, 7 | Data Map, Process Analysis, Business Logistics, BPMN, Event Schedule, Strategy Map, Process Map |
| Designer, 6 | Class, Activity, Data Distribution Architecture, Use Case, State Transition, Business Rule Model |
| Builder, 7 | Physical Data model, Component, Deployment, User Interface, Interaction, Communication, Rule Design |
| Subcontractor, 5 | Data Definition, Network architecture, Security Architecture, Timing Definition, Rule Specification |
| ZF Interface, 1 | Zachman Framework Interface |

Against the tokens, the tab has seven Owner types where the tokens give six (four cell tokens, `BPMN` and `StrategyMap`) and seven Builder types where the tokens give six. Which tab name is which token was not checked.

**Toolboxes and quick links** (same date). The tab lists 29 toolboxes, named like the types (Business Data, Data Map, Class, Component and so on). The grid diagram shows UML pages only (Class, Class Relationships, Composite Parts, UML Standard Profile); there is no Zachman page. An Owner data cell diagram shows the pages Data Map (Principal Entity, Intersecting Entity, Structure Entity) and Data Map Relations (Associate). From a Business Entity on that diagram the quick links offer only Create Multiple Elements and Common, so no Zachman-specific quick link. One source only; the other 27 toolboxes were not opened.

**EA accepts any text as a diagram type and quietly makes a Class diagram when it does not know it.** Check that `t_diagram.StyleEx` carries `MDGDgm=<token>`. The bare tokens Sparx's pattern uses for a few diagrams (`ZF::BuilderTime`, `ZF::SC_Data`, `ZF::SC_People`, `ZF::SC_Time`, `ZF::SC_Motivation`) are not kept; the working tokens are `ZF Builder::BuilderTime` and `ZF Subcontractor::SC_...`. There is no `ZF Owner::OwnerPeople`, `ZF Owner::OwnerMotivation`, `ZF Subcontractor::SC_Function` or any row 6 type.

## 6. How to build a Zachman model

1. Create one package for the framework (for example "Westbrook Bank Zachman Framework", as an illustration).
2. Under it create the six row packages, unstereotyped, named Planner, Owner, Designer, Builder, Subcontractor, Functioning Enterprise.
3. Under each row create the six cell packages with the stereotype `ZFCell`, named as in section 3 and in the column order. By script: add a package, then set `StereotypeEx = "ZF::ZFCell"` on its `Element` and update the element and the package. Creating an element of type `ZF::ZFCell` is refused; a *Package-type element* is accepted but is not a package and not a cell.
4. Put each element in exactly one cell package. Create it with `ZF::<stored name>` where the stereotype fits (`ZF::BusinessEvent`) and as a plain UML element where EA has none. Stored names drop the tab's spaces and sometimes change: `BOD` (tab: Board Of Directors), `basedOn`, `equivalentTo`, `exceptionTo`, `implements`, `replaces`. `EventNode` binds only on an Object element (create an Object, then set `StereotypeEx = "ZF::EventNode"`). `HeadQuarters` is the stored spelling; the pattern's `HeadQuaters` is refused.
5. For each cell with content, add the cell's diagram type (section 5) in the cell package and put the cell's elements on it.
6. Put the grid in the framework package: create a `ZF Interface::ZF_Interface` diagram and drop the 36 cell packages on it, columns across and rows down. Each cell shows its row.
7. Connect elements inside a cell with a plain UML association or one of the 17 connector stereotypes (`Communicate` is bi-directional, `Trigger` is a ControlFlow, the rest are Dependency connectors from source to destination).

## 7. An example, as an illustration

Westbrook Bank, a fictitious bank, classified as in the language skill's table.

| Cell | Element | EA element |
|---|---|---|
| A2 Owner, Semantic Data Model | Customer, Account (business entities), associated | `BusinessEntity`, UML association |
| A3 Designer, Logical Data Model | Customer (a data entity; the same word, a different concept) | plain UML Class |
| B2 Owner, Process Analysis Model | Open a Retail Account, Verify Identity | `BusinessProcess`, connector `Invokes` |
| B3 Designer, Application Architecture | Account Opening Service | plain UML Component |
| C2 Owner, Business Logistics | Westbrook Headquarters, Branch Network, Call Center | `HeadQuarters`, `BranchOffice`, `OfficeBlock`, connector `Communicate` |
| D3 Designer, Human I/F Architecture | Branch Manager (a role) | `Personnel` |
| E2 Owner, Event Schedule | Month-End Close, Ledgers Closed, Monthly Cycle | `BusinessEvent`, connector `Trigger`, `BusinessCycle` |
| F2 Owner, Business Plan | Reduce Account-Opening Time, Digital Onboarding | `Goal`, `Strategy`, connector `StrategyLink` |
| A6 Functioning Enterprise, Actual Data | Account 000123 (an instance) | plain UML Object |

Two choices are the skill's and not EA's: the pattern files `HeadQuarters` and `BranchOffice` in the planner's location cell, and the skill's table classifies the branch network, headquarters and call center as business units at locations (C2); and the pattern files `BusinessEntity`, `BusinessProcess` and `Personnel` in no cell.

## 8. What EA does that the framework does not

- A `ZFCell` package, a grid diagram and per-cell diagram types: the framework defines a classification, not drawings (ZF-GUID-004).
- 61 generic enterprise stereotypes and 146 tagged-value rows (`ID`, `Description`, address and contact fields, goal and strategy measures, rule status, layer lists), none a concept of the framework.
- Per-stereotype default diagrams (`BusinessFunction` opens `ZF Planner::PlannerFunction`).
- Hyperlinks between the matrix and the cell diagrams in Sparx's pattern (read from the pattern file; not measured).

## 9. Traps found

1. **The tab's names are not the stored names.** `Business Entity` is `BusinessEntity`; `Board Of Directors` is `BOD`; `Based On` is `basedOn`. Selecting by the tab's name finds nothing.
2. **A cell is a place.** EA does not stop a wrong or missing cell, and no tag says which cell an element is in. Nothing in the saved model carries the column except the cell's name.
3. **`ZFCell` takes only a package.** An element of type `ZF::ZFCell` is refused; a Package-type element is accepted and is not a package.
4. **Unknown diagram types fall back to Class** without a message (section 5). Check `StyleEx`.
5. **Sparx's pattern disagrees with the technology in places:** `HeadQuaters` (refused), bare `ZF::` diagram tokens (not kept), cells named `Executables ` with a trailing space and `BusinessUnits` in row 6.
6. **Not every cell has a diagram type:** owner people and motivation, subcontractor function, and all of row 6.
7. **Row 6 has no stereotypes and no diagram types.** The pattern leaves its six cells empty; an instance is a plain element in a row 6 cell.
8. **`Person` and `Responsibile` are on the Resources tab and bind on nothing tried.** Do not rely on them.
9. **EA's cell names are not the 1992 names** (`Semantic Data Model` for the owner's data cell; the skill says `Semantic (entity-relationship) model`) and EA calls the third column Location.
10. **The ruleset holds seven rules, not the whole framework.** The framework's checkable rules are about which cell an element is in; EA records that as containment (the cell package, and its row package above it), which the validator reads (`contained_in`, `contains_count`, since 2026-10-21). Six of ten planted defects in our sample set are caught.

## 10. Checking a model

7 of 7 rules in this ruleset use formats newer than 3.6.4, and on that server they report nothing or don't run as written. Use server 3.6.5 or later, because a clean result on 3.6.4 doesn't mean the model passes.

The Zachman ruleset (`rulesets/zachman/zachman_rules.yaml`) holds seven rules over where an element sits: a classified element sits in a cell (a `ZFCell` package); a business entity sits in the Owner row's data cell and a business process in its function cell; an event or cycle sits only in a time-column cell; an object (taken as an instance) sits under Functioning Enterprise; a row package holds at most six cells. The column is not stored, so a rule names the cell by its name. A reviewer still checks by opening each cell package for what the rules do not reach: that an element is shown on no other cell's diagram (diagrams cannot be read); that a model that binds primitives of more than one column is a composite (a meaning, not a stored value); that a framework has exactly six row packages and that each row has one cell per column (a row package has no stereotype to select it by, and a row with fewer than six cells is not reported).

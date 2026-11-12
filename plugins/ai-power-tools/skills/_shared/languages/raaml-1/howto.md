# Modeling RAAML 1.0 in Sparx Enterprise Architect

How to model the language of the RAAML skill the way Sparx's built-in technology does it. The technology is `RAAML` in the Resources tab and `RAAML1.0` to EA's API; every stereotype it stores is qualified `RAAML::<name>`. Measured on EA 17.1 build 1716 by creating one element, port, part, connector and diagram of each kind and reading the stored rows back; `ea.yaml` holds the facts. Westbrook Bank (fictitious) appears only as an illustration; your model has its own names, and nothing here assumes it contains Westbrook's.

## Version

**The skill and this guide describe RAAML 1.0, and EA's technology reports version 1.0** (`GetTechnologyVersion` returns `1.0`). OMG lists RAAML 1.1 (December 2025) and a 1.2 beta. Neither was studied, so nothing here says whether EA's stereotypes follow 1.0 exactly or include later changes. EA names no specification edition, so the catalog cannot tell; it was not compared with 1.1 or 1.2.

## What the technology looks like

- **121 names and 154 rows** on the Resources tab (a name is listed once per metaclass it applies to); **120 names and 153 rows can be applied**. The one that cannot is `GATE`: EA accepts it on no element, connector, package or diagram. It matches the standard's abstract `Gate`, so it is probably the abstract profile element, listed but not usable. The seven gates are `AND`, `OR`, `NOT`, `XOR`, `SEQ`, `INHIBIT` and `MAJORITY VOTE`.
- **RAAML is a UML profile with a model library.** The profile gives markers, the library gives the classes the markers go on. The technology has stereotypes for the markers and the relationships; the library classes (AbstractEvent, Cause, Effect, DysfunctionalEvent, Hazard, Scenario, the failure mode classes, the ISO 26262 conditions and malfunction classes and the rest, 57 concepts of the skill, counting the value types and enumerations) are **ordinary classes**. EA ships them as the model pattern `raaml-library` and the seven `ra1.0-*` examples. A class that stands for a situation carries the stereotype `Situation`, or the method marker that specializes it (`FMEAItem`, `FailureMode`, `BasicEvent`, `UnsafeControlAction` and so on).
- **Stored names are bare and case-sensitive.** `t_object.Stereotype` holds `FMEAItem`; the qualified form is only in `t_xref` (the row named `Stereotypes`, `FQName`) and is what you pass to create an element or set `StereotypeEx`. Two names have a space: `ID carrier` and `MAJORITY VOTE` (the standard writes `IDCarrier` and `MAJORITY_VOTE`).
- **Eight diagram types** on the Resources tab, in one group named RAAML: RAAML, RAAML - Core, RAAML - General Concepts, Failure Mode and Effect Analysis, Fault Tree Analysis, Goal Structuring Notation, ISO 26262 Road Vehicles - Functional Safety (name cut off at the panel edge) and Systems Theoretic Process Analysis. None is the standard's: it defines no diagram type of its own and reuses SysML's (see below). Measured on EA 17.1 build 1716, 2026-11-04. The first measurement (through the API) found five; the three added here are the FMEA, fault tree and ISO 26262 types.
- **EA adds stereotypes the skill does not have**: `ModelView`, `ScriptLet`, `AbstractRequirement`, the value types `Occurence`, `Detectability`, `RPN`, `PremitigationOccurences`, `PremitigationSeverities`, `PremitigationDetectabilities`, `PreviousRPNValues` and `ValueType`, the Port stereotypes `cause`, `failureMode`, `finalEffect` and `harmPotential`, and the Association stereotypes `condition`, `input` and `output`.

## Which diagram type for which view

| View (skill) | EA diagram type | Stored as |
|---|---|---|
| FMEA, fault tree, as Sparx's patterns draw them | `RAAML::RAAML` | Logical diagram, `MDGDgm=RAAML::RAAML;` |
| FMEA | `Failure Mode and Effect Analysis` | not created; stored token not read |
| Fault tree | `Fault Tree Analysis` | created on screen; Properties show the type as `Fault Tree Analysis - FTA`; stored token not read |
| ISO 26262 | `ISO 26262 Road Vehicles - Functional Safety` | not created; the name was cut off at the panel edge, so the full name is not confirmed |
| Core library and profile | `RAAML::RAAML - Core` | Logical, `MDGDgm=RAAML::RAAML - Core;` |
| General concepts | `RAAML::RAAML - General Concepts` | Logical |
| STPA control structure, unsafe control actions, loss scenarios | `RAAML::Systems Theoretic Process Analysis` | Logical |
| GSN argument | `RAAML::Goal Structuring Notation` | Logical |
| Block definition, internal block, parametric, requirement (the standard's SysML views), the tables | the SysML diagram types of EA's SysML technology, or EA's own tables and matrices | not part of RAAML's technology |

EA does list an FMEA, a fault tree and an ISO 26262 type (measured on EA 17.1 build 1716, 2026-11-04; the New Diagram dialog for the RAAML technology shows the same eight names). Sparx's model patterns do not use them: the FMEA and fault tree examples are drawn on `RAAML::RAAML` and the ISO 26262 example on the GSN type. A fault tree diagram of the Fault Tree Analysis type was created on screen; its toolbox pages are Core Profile, FTA Pattern, FTA GATE (AND, INHIBIT, MAJORITY VOTE, NOT, OR, SEQ, Tree, XOR), FTA Library and FTA EVENT (Basic, Conditional, Dormant, House, Intermediate, Top, Undeveloped and Zero Event). Not checked: diagrams of the FMEA, ISO 26262, STPA and GSN types were not created or opened, so the trap below (found through the API) was not rechecked against the types the screen lists. Trap: the model patterns record the tokens `RAAML::Systems Theoretic Process Analysis - STPA` and `RAAML::Goal Structuring Notation - GSN`. They do not bind; asking EA for a diagram of that type gives a plain Class diagram with no error. Use the names in the table.

## How to say each concept

Replace the example names with your own system. A **situation** is a class; **a library class** is an ordinary class carrying `Situation` (or its method marker).

| To model | Create | Set or note |
|---|---|---|
| Situation, event, cause, effect, harm potential, hazard (library classes) | a Class, stereotype `Situation` | the method marker below when the class belongs to a method |
| FMEA item | a Class, `FMEAItem` | tag `isEncapsulated` only; the RPN formula is the class `RPNCalculation` (a constraint block) |
| Failure mode | a Class, `FailureMode` (StereotypeEx; the qualified type resolves to the Port, see traps) | |
| Join a failure mode or a cause to its item | an Association, `FailureMode` or `Cause`, **from the failure mode or cause class to the FMEA item** (Sparx's FMEA pattern draws it so) | counts of these are what the ruleset reads |
| Final effect, harm potential of an item | no connector exists; a Port child of the item, `finalEffect` or `harmPotential`, typed by the effect class | the same for `cause` and `failureMode` as Ports |
| Value types (occurrence, detectability, severity, RPN and the earlier values) | a DataType: `Occurence`, `Detectability`, `Severity`, `RPN`, `PremitigationOccurences` ... | tags `quantityKind`, `unit` |
| Causality and its kinds | an Association: `Causality`, `Activation`, `ErrorPropagation`, `ErrorRealization`, `ProcessModelFactor`, `ProcessModelConsequence`, `UnsafeControlActionHarmPotential` | between situations |
| RelevantTo | a Dependency, `RelevantTo`, from the situation to the element that gives it context | tags for the property paths and contexts, empty |
| Violates | a Dependency, `Violates`, from the situation to the requirement | |
| Detection, Prevention, Mitigation, Recommendation | a Dependency with that stereotype, from the measure (a requirement or action) to the situation (the supplier) | tag `affects` |
| Error, Fault | a Class, `Error` or `Fault` | |
| Failure state | a State element, `FailureState` | |
| Undeveloped | `Undeveloped` as a **second** stereotype on a Goal, Strategy or BasicEvent | applies to any element; see traps |
| Fault tree | a Class, `FTATree` (tag `TopEvent` names the top event) or the marker `Tree` | `TransferOut` is a Class, `TransferIn` a Part |
| Events | a Class: `BasicEvent`, `IntermediateEvent`, `TopEvent`, `ConditionalEvent`, `DormantEvent`, `HouseEvent`, `ZeroEvent`, `UndevelopedEvent`, `Event` | `TopEvent` has tag `Probability`; no other event has one |
| Gates | a Class: `AND`, `OR`, `NOT`, `XOR`, `SEQ`, `INHIBIT`, `MAJORITY VOTE` | the reference constraint blocks are `ANDConstraintBlock`, `ORConstraintBlock` ... `MAJORITY_VOTEConstraintBlock` |
| A gate's events | an Association between the event and the gate; the technology has the stereotypes `input`, `output` and (INHIBIT) `condition` for it | Sparx's FTA Pattern draws an input from the event to the gate and the output from the gate to the top event, as plain Associations with no stereotype (measured on screen, EA 17.1 build 1716, 2026-11-04) |
| Controller, controlled process, actuator, sensor | a Class (or a Part): `Controller`, `ControlledProcess`, `Actuator`, `Sensor` | |
| Control action, feedback | a Class, a Signal or a DataType: `ControlAction`, `Feedback` | |
| Control structure | a Class, `ControlStructure` | |
| Unsafe control action, loss scenario, process model, factor | a Class: `UnsafeControlAction`, `LossScenario`, `ProcessModel`, `Factor` | |
| Risk realization | a Class, `RiskRealization` | an association class between a loss and a hazard |
| GSN nodes | a Class: `Goal`, `Strategy`, `Solution`, `Context`, `Assumption`, `Justification` | each also exists as a stereotype on any element (the Element row) |
| GSN links | a Dependency: `InContextOf` (goal or strategy to context, assumption, justification), `SupportedBy` (goal or strategy to goal, strategy or solution; a strategy only to goals) | |
| Identifier | `ID carrier` (tag `ID`), applied as a second stereotype to the element that has the identifier, or a carrier element of its own | |
| Operational situation, malfunctioning behavior | a Class: `OperationalSituation`, `MalfunctioningBehavior` | `MalfunctioningBehavior` is also an Association stereotype |
| Exposure, severity, controllability | a DataType: `Exposure`, `Severity`, `Controllability` | |
| Safety goal and safety requirements | a Class: `SafetyGoal`, `FunctionalSafetyRequirement`, `TechnicalSafetyRequirement`, `SoftwareSafetyRequirement`, `HardwareSafetyRequirement`, `DependabilityRequirement` | tags `id` and `text` on all but `DependabilityRequirement` (and `isEncapsulated`) |
| ASIL decomposition and the related requirements | a Dependency (an Abstraction by default): `ASILDecompose`, `IndependenceRequirement`, `UserInfoRequirement`, `RecoveryRequirement` | `ASILDecompose` is applied in pairs |
| Safe state, operating mode | a Dependency: `SafeState`, `OperatingMode` | in EA these are connectors, not states; the standard describes them as states |
| ASIL assignment, rationale | `ASILAssignment` (tags `ASIL`, `ASILOverride`) on any element, usually as a second stereotype; `ASILOverrideRationale` on a Class or a Note | |
| Verified, Confirmed | a Class, tag `result` | |
| Hazard and risk assessment | an element of type Package, `HazardAndRiskAssessment` (not a real package) | |
| Lesson learned | a Note, `LessonLearned` | |

Illustration (Westbrook Bank is fictitious): the FMEA item `Authorization unavailable` (`FMEAItem`) has the failure mode `Authorization service does not respond` (`FailureMode` Class, joined to the item by a `FailureMode` Association) and the cause `Primary database fails` (a `Situation` class joined by a `Cause` Association). The fault tree has an `OR` gate whose output event is `Customer cannot pay by card`. The GSN goal `Card payments are acceptably available` (`Goal`) is supported (`SupportedBy`) by the strategy `Argue over the fault tree and the FMEA` (`Strategy`).

## Containment, typing and what the validator cannot read

- **A property belongs to a class.** `cause`, `failureMode`, `finalEffect` and `harmPotential` are Port stereotypes: a Port cannot be created in a package ("Invalid parent for Port (Package)"); create it as a child element of the FMEA item. EA stores the owner in `ParentID`, and a ruleset can count the children an element owns (`contains_count`, used for the final effect and harm potential of an FMEA item). `Actuator`, `ControlledProcess`, `Controller`, `Sensor` and `TransferIn` also exist as Part elements, children of a class.
- **A part is typed by a class**, and a redefining property by a narrower type; EA stores the type as a classifier. Set it, so that a reader sees what a Port or a Part stands for. The validator cannot read the type, so no rule checks it.
- **Generalization carries no stereotype.** The standard's main structure (a class that specializes `AnySituation`, a library class and its markers) is a plain generalization. A ruleset selects it by EA connector type (`Generalization`) and can count the ones going out of a class (EA draws them from the specific class to the general one), so it can tell that a marked class specializes nothing; it cannot follow a generalization to see which class it leads to.
- **Values are not tags.** Probabilities, the RPN, the occurrence and severity of a library class are value properties with a default value on the class. The only values EA keeps as tagged values are those in `ea.yaml` under `tags_of_note`.
- **A second stereotype is invisible to the validator.** `t_object.Stereotype` holds only the first stereotype; `Undeveloped`, `ID carrier`, `ASILAssignment`, SysML's `block` and similar markers applied second are only in `t_xref`.

## What EA does that the standard does not

- Port stereotypes `cause`, `failureMode`, `finalEffect`, `harmPotential` and the Association stereotypes `Cause`, `FailureMode`, `input`, `output`, `condition`: EA's way of drawing the standard's part properties.
- `ModelView`, `ScriptLet`, `AbstractRequirement`, the Premitigation and PreviousRPN value types.
- A stereotype name binds without regard to case, and a spelling that differs only by case can be another stereotype on another metaclass (`cause` Port, `Cause` Association; `failureMode` Port, `FailureMode` Class and Association).
- A tag `isEncapsulated` (true/false) on every Class stereotype, inherited from the Class form.
- Eight diagram types (`RAAML`, `RAAML - Core`, `RAAML - General Concepts`, `Failure Mode and Effect Analysis`, `Fault Tree Analysis`, `Goal Structuring Notation`, `ISO 26262 Road Vehicles - Functional Safety` and `Systems Theoretic Process Analysis`), none defined by the standard.
- Eight toolboxes (RAAML_Core, RAAML_FMEA, RAAML_FTA, RAAML_General Concepts, RAAML_GSN, RAAML_ISO 26262, RAAML, RAAML_STPA). A diagram of the RAAML type shows 16 toolbox pages, from Core Profile to FTA Pattern. Quick links are mostly generic: from an FMEA item the only RAAML link is UML aggregation (to whole, to part), and from an AND gate none is offered. Measured on EA 17.1 build 1716, 2026-11-04 on two sources; other sources were not tried.

## What the standard has that EA does not

- The 57 concepts that are library classes, value types or enumerations (listed in `ea.yaml`, status `library-class` or `not-in-ea`): model them as ordinary classes, or take them from the `raaml-library` model pattern.
- The 28 part (composition) relationships, as stereotypes: the four FMEA ones and `Gate.input`, `Gate.output`, `INHIBIT.condition` have a stereotype of the same name; the other twenty-one are plain parts (children of the owner class, ParentID).
- The abstract profile elements `Gate` and `ControllingMeasure`.
- Tables: the standard's situation, FMEA, unsafe control action and HAZOP tables have no counterpart in the technology; EA's own tables and matrices serve.
- The two diagram tokens the model patterns record that do not bind (above).

## Traps found

1. **The qualified type resolves by name, not by metaclass.** `AddNew(name, "RAAML::FailureMode")` creates the Port `failureMode`, not the Class: make the Class as `AddNew(name, "Class")` with `StereotypeEx = "RAAML::FailureMode"`. `AddNew(name, "RAAML::cause")` in a class does not make a Port: it resolves to the Association `Cause` and fails ("Invalid type"); make the Port as type `Port` with `StereotypeEx = "RAAML::cause"`.
2. **A Port needs a host.** The same for the four Port stereotypes: a package refuses them.
3. **Pattern names do not bind.** `Cause connector`, `FailureMode connector`, `finalEffect connector`, `harmpotentialport`, `Dormant Event` and `Conditional Event`, which Sparx's model patterns store, are not stereotypes of the technology; EA stores no stereotype and gives no error. The technology's names are `Cause`, `FailureMode`, `DormantEvent`, `ConditionalEvent`; the pattern also stores `situation` where the technology stores `Situation`.
4. **Several stereotypes are applied with commas.** `StereotypeEx = "RAAML::Goal,RAAML::Undeveloped"` works; with a semicolon EA stores nothing and gives no error.
5. **GATE cannot be applied**, and `HazardAndRiskAssessment` binds only on an element of type Package, not on a package made with `Packages.AddNew`.
6. **Case.** A ruleset selector compares the stored string exactly: `Situation`, `FMEAItem`, `ID carrier`, `MAJORITY VOTE`. A lower-case spelling selects nothing and the run looks clean.
7. **Direction.** Sparx's FMEA pattern draws the failure mode, cause and effect class as the connector's source and the FMEA item as its target (EA stores the arrow pointing back at the source). A rule that counts connectors reads one direction; draw them the same way. Sparx's FTA Pattern shows the gate wiring (measured on screen, EA 17.1 build 1716, 2026-11-04): an input connector runs from the event (source) to the gate (target), and the output runs from the gate (source) to the top event (target), the opposite way round. Both are plain Associations with direction Source -> Destination and carry no `input` or `output` stereotype.
8. **Flags are not tags.** Whether a class is abstract, and a property's multiplicity and redefinition, are not tagged values and are not stored in a form the validator reads (multiplicity).

## Checking a model

20 of 27 rules in this ruleset use formats newer than 3.6.4, and on that server they report nothing or don't run as written. Use server 3.6.5 or later, because a clean result on 3.6.4 doesn't mean the model passes.

The ruleset is `rulesets/raaml-1/raaml-1_rules.yaml`, with 27 rules.

# Modeling requirements in Sparx EA

How Sparx EA represents the language described in the requirements language skill, measured on EA 17.1 build 1716 (2026-10-21). The language has no single standard (ISO/IEC/IEEE 29148 with SysML's requirement relationships), and **EA has no requirements technology of its own with a profile**: the "EA Requirements" technology on the Resources tab holds model templates only. Its stereotypes are the **EAREQ** profile of Core Extensions, the requirement itself is EA's built-in element type **Requirement**, and the relationships between requirements come from the **SysML1.4** technology and EA's built-in connector stereotypes. Every fact here was read back from what EA creates (`ea.yaml` records the source of each); the profile is encrypted, so the *definitions* of the EAREQ stereotypes were not read. Examples use Westbrook Bank, a fictitious bank, as an illustration: substitute your own requirements and elements. Nothing here assumes you have any particular model.

**Versions.** The language is built from ISO/IEC/IEEE 29148:2018 and OMG SysML 1.5 (clause 16). ISO lists a draft edition to replace 29148:2018; it was not studied. SysML has newer versions (see the SysML how-to). EA's requirements technology stores no version.

## 1. What EA gives you

- **The element type `Requirement`.** Every requirement is stored with `t_object.Object_Type = Requirement`, whatever its stereotype. Select it by type, not by stereotype. EA creates the type when you ask for it by name, and also for the name `Goal`.
- **EAREQ: nine stereotypes.** Eight classify a Requirement: `ArchitecturalRequirement`, `BusinessRequirement`, `UserRequirement`, `FunctionalRequirement`, `NonfunctionalRequirement`, `SecurityRequirement`, `ImplementationRequirement`, `RegulatoryRequirement`. The ninth, `RequirementsChecklist`, is an **Artifact** carrying ten quality items to tick. Create with the qualified type (`EAREQ::BusinessRequirement`); EA stores the bare name.
- **One diagram type**, created as `Extended::Requirements` (stored base type `Custom`, `StyleEx` holds `MDGDgm=Extended::Requirements;`).
- **Toolbox pages and quick links** were read on a diagram of type Requirements (EA 17.1 build 1716, 2026-11-04). The pages are Requirements (Package, Requirement, Feature, Risk, Object), Extended Requirements (the nine EAREQ stereotypes), Requirements Relationships (Aggregate, Inheritance, Associate, Implements, Dependency, InformationFlow, Trace) and Patterns (Functional Requirements, Non-Functional Requirements). The plain Requirement item makes an element with no stereotype. From a new Requirement the quick links offer Artifact, Change, Issue, Requirement, Risk and the common list, with aggregation, association and generalization only: no Trace, DeriveReqt or Satisfy link. One source was tried. **Model templates** exist for the technology and were not read.
- **Relationship stereotypes** (not EAREQ): `deriveReqt`, `satisfy`, `verify`, `copy`, `allocate`, `refine` and `trace` from SysML1.4 (loaded on the machine measured), and EA's own built-in `trace`, `refine`, `derive`, `depends`, `realize`.

## 2. Concepts: what to create

| Language concept | Create | Notes |
|---|---|---|
| Requirement | element of type `Requirement` | The general case. EA's own fields (section 3) live on it. |
| Business requirement | `EAREQ::BusinessRequirement` | Tags `objective`, `scope`, `context`, `rules`, `constraint` (memo), `priority`. |
| Stakeholder requirement | `EAREQ::UserRequirement` | **A judgment, by name:** 29148's stakeholder requirement is the older user requirement. Tags `expectation`, `impact`, `communication` (memo), `designation`, `priority`. |
| Functional requirement | `EAREQ::FunctionalRequirement`, or the built-in `Functional` | Tags `dataDescription`, `operationDescription`, `reportDescription`, `workflowDescription` (memo), `priority`. `Functional` is the stereotype EA's own model patterns use (section 7, trap 3). |
| Quality (non-functional) requirement | `EAREQ::NonfunctionalRequirement` | The language file lists *non-functional requirement* as a synonym. Tags are quality categories: `availability`, `configurability`, `interoperability`, `maintainability`, `portability`, `reliability`, `scalability`, `usability` (memo), `priority`. |
| Policy and regulation requirement | `EAREQ::RegulatoryRequirement` | **Nearest by name and tags** (`externalRegulation`, `internalRegulation`, `legislativeRegulation`, `priority`). |
| Transition requirement | `EAREQ::ImplementationRequirement` | **Nearest by tags** (`migration`, `recruitment`, `roleChange`, `priority`): a judgment; EA's definition was not read. |
| System, system element, software, performance, interface, process, usability, human factors requirement, constraint | a `Requirement` with a stereotype of your choice, or none | **EA has no stereotype for these.** Keep the distinction in the requirement's name, in a tag you add, or in the structure of your packages. |
| Stakeholder, need, business rule, assumption, source document, trade study | any element (the example uses an `Actor` and an `Artifact`) | EA has no stereotype. The source of a requirement is whatever its `trace` ends on. |
| Design element | any element, usually a `Component`, `Class` or `Node` | The ruleset treats `Artifact`, `Class`, `Component`, `Entity`, `Interface`, `Node`, `Object` and `Part` as design elements. |
| Verification entity | any element (the example uses a `Class` per test) | EA also keeps test records as sub-records of an element (section 3); those are not elements and cannot be linked. |
| Requirements specification (BRS, StRS, SyRS, SRS), operational concept | none | A package, a diagram or a generated document. EA's Business and Functional Requirements Document templates exist among EA's model patterns; they were not measured. |

`SecurityRequirement` (tags `goal`, `policy`), `ArchitecturalRequirement` (tags `hardware`, `software`, `performance`) and `RequirementsChecklist` are in EA and not in the language file (`ea.yaml` `ea_only`). A security requirement is, in the language, a quality requirement of the category *security*.

**Level.** The language has four levels (business, stakeholder, system, system element); **EA stores none.** The only level EAREQ carries is the choice between `BusinessRequirement` and `UserRequirement`. The ruleset reads `UserRequirement` as the stakeholder level, `BusinessRequirement` as the business level, and every other requirement stereotype (and `Functional`) as system level or below. That is a judgment, not a fact about EA: check it against how your project uses the stereotypes. The five rules that rest on it are warnings, never errors: RQ-REL-009 (a requirement is derived from one at the same or a higher level), RQ-TRACE-002 (a system level requirement is verified), RQ-TRACE-003 (a business or stakeholder requirement is validated), RQ-TRACE-005 (a system level requirement is satisfied) and RQ-TRACE-006 (a requirement below the business level traces upward). If your project uses the stereotypes differently, change those five rules in the ruleset: the stereotype lists in their selectors, and for RQ-REL-009 the `requirements-derive-levels` table. A requirement with no stereotype is not selected by any of them.

## 3. A requirement's own fields, tags and sub-records

A new `Requirement` carries these as **columns of the element**, not as tagged values:

| Field | Default | Stored in | Language attribute |
|---|---|---|---|
| Status | `Proposed` | `t_object.Status` | status |
| Priority | `Medium` | `t_object.PDATA2` | priority |
| Difficulty | `Medium` | `t_object.PDATA3` | difficulty |
| Complexity | `1` | `t_object.Complexity` | |
| Phase, Version | `1.0` | `t_object.Phase`, `t_object.Version` | version |
| Author | the EA user name | `t_object.Author` | owner |
| Alias | empty | `t_object.Alias` | identifier (by convention: EA has no identifier field) |
| Notes | empty | `t_object.Note` | statement |

The EAREQ stereotypes add **tagged values**; all eight requirement stereotypes carry `priority` (an enumeration: High, Medium, Low, Essential, Conditional, Optional; empty until set). **This is a second priority**, separate from the field above. The ruleset reads the tag. The other tags are memo text; none is an identifier, a rationale, a version, an owner or a verification method.

An element also holds **sub-records** in their own tables: an *internal requirement* (`t_objectrequires`: name, `Functional`, `Proposed`, stability, difficulty, priority), issues, constraints, test cases (`t_objecttests`), scenarios, risks, effort and metrics. They are not elements: they cannot be linked, drawn on a diagram or selected. A model that keeps its requirements as internal requirements of one element is invisible to everything that reads elements.

## 4. Relationships: what to connect, and which diagram

**Direction as stored (and as the ruleset reads it):**

| Language relationship | EA construct | Direction (source to target) | Created with |
|---|---|---|---|
| derive | Dependency stereotyped `deriveReqt` | derived requirement to its parent | `SysML1.4::deriveReqt` |
| contain (decompose) | Aggregation, **or** nesting under the parent | child to parent, the diamond at the parent (`DestIsAggregate = 1`), as EA's own patterns draw it; nesting sets `ParentID` | Aggregation with the end set; or drag the child into the parent |
| satisfy | Dependency stereotyped `satisfy` | design element to requirement | `SysML1.4::satisfy` |
| verify | Dependency stereotyped `verify` | test (or other verifying element) to requirement | `SysML1.4::verify` |
| allocate | **Abstraction** stereotyped `allocate` | requirement to design element | `SysML1.4::allocate` (not the unqualified name, trap 4) |
| refine | Dependency stereotyped `refine` | refining element to requirement | `SysML1.4::refine`, or EA's built-in `refine` |
| trace | Dependency stereotyped `trace` | requirement to what it traces to | `SysML1.4::trace`, or EA's built-in `trace` (Dependency or Abstraction) |
| copy | Dependency stereotyped `copy` | slave to master | `SysML1.4::copy` |
| sourced from | `trace` (this guide's convention) | requirement to its source | as trace |
| constrained by, assumes, specified in, held by | none | | EA has no construct; a plain Dependency cannot be told from `satisfy` or `verify` by type alone |

**Pairs.** EA accepts any pair without a message (trap 5). The ruleset checks these: `deriveReqt` and `copy` join two Requirements; `satisfy` and `verify` end on a Requirement; `allocate` runs from a Requirement to a design element; a `deriveReqt` is not drawn from a business requirement to a stakeholder one; only requirements are nested in a requirement.

| Standard diagram type | EA diagram type | Notes |
|---|---|---|
| none: 29148 defines no diagram | `Extended::Requirements` | EA's Requirements diagram. Drop the requirements and the elements around them and add the connector links; a diagram holds only what you put on it. `SysML1.4::Requirement` is SysML's requirement diagram. |
| Traceability and verification matrices (RTM, VCRM) | EA's relationship matrix and traceability views | Not measured. |

## 5. What EA does that the language does not

- **A built-in priority, status, difficulty and complexity on every requirement**, with defaults (section 3), and sub-records such as internal requirements.
- **Three requirement-like types the language file lacks:** `ArchitecturalRequirement`, `SecurityRequirement` and the `ImplementationRequirement` of the transition reading.
- **A requirements checklist.** `RequirementsChecklist` is an Artifact whose `Checklist` tag carries ten items: Atomic, Attainable, Cohesive, Complete, Current, Independent, Modifiable, Traceable, Unambiguous, Verifiable. They are close to, but not the same as, 29148's nine characteristics (necessary, appropriate, unambiguous, complete, singular, feasible, verifiable, correct, conforming): Atomic reads as singular, Attainable as feasible, Current as necessary; Cohesive, Independent, Modifiable and Traceable have no counterpart.
- **Quality categories as tags** on `NonfunctionalRequirement` (eight), where the language has a value set of categories.
- **`Goal`** is accepted as an element type and stored as `Requirement`.

## 6. What the language has that EA does not

- **No level**, no system or system element or software requirement, no performance, interface, process, usability or human factors type.
- **No identifier, rationale, risk or verification method field**, no source field (a source is a link), no requirement version history beyond `Version`.
- **No stereotype for stakeholder, need, business rule, assumption, source document, trade study, design element or verification entity.**
- **No `contain`, `constrained by`, `assumes`, `specified in`, `held by` connector stereotype.**
- **No specification as an object** (BRS, StRS, SyRS, SRS), and no diagram per specification.

## 7. Traps found

1. **A requirement is the type `Requirement`, not a stereotype.** A rule that selects stereotypes misses a requirement with none; a rule that selects the type also reaches SysML requirements.
2. **`EAREQ` is a profile, not a technology.** `EAREQ::` binds all nine names; `EAUML::`, `EAExtended::`, `Extended::`, `EAUI::`, `EA Requirements::`, and the bare name `Requirements` or `EAExtended:Requirements` followed by `::`, are refused for every name. Setting `StereotypeEx = EAREQ::RequirementsChecklist` on a Requirement leaves the element with no stereotype and no message.
3. **`Functional` is not EAREQ.** It is one of EA's built-in stereotypes of the Requirement type (`t_stereotypes`), stored by its bare name with a GUID and no qualified name, and it is the only stereotype the `rq2.0` model patterns use. `EAREQ::Functional` is refused. `RequirementsChecklist` exists both as the EAREQ Artifact stereotype and as a built-in stereotype of the Requirement type.
4. **The same relationship name can bind a different stereotype.** `allocate` created unqualified on a Dependency, Abstraction or Realisation binds `MARTE::Allocate` and is stored as **`Allocate`** (capital A); `SysML1.4::allocate` is stored `allocate`. The `Trace` connector type is stored as an Abstraction stereotyped **`Trace`** (capital T), not `trace`. `SysML1.4::containment` and `EAREQ::trace` create a connector with no stereotype. A stereotype put on an Aggregation or Association is stored but is not the SysML one.
5. **EA does not stop a wrong pair.** All eight deliberately wrong connectors of the sample set (a `deriveReqt` to or from a Class, a `satisfy` to a Class, a `verify` to a Component, a `copy` to a Class, a business `deriveReqt` to a stakeholder requirement, an `allocate` to a Requirement and from a Component) and a Class nested in a requirement were accepted with no message. The ruleset exists for this.
6. **Two priorities.** The tag `priority` is empty by default; the element's own Priority is `Medium` by default. A report that reads the field shows `Medium` for a requirement nobody prioritized.
7. **A memo tag always reads as `<memo>`.** The text is in the tag's notes. A "tag is not empty" test passes on every memo tag whether or not it holds text; only an enumeration tag such as `priority` can be tested that way.
8. **Several stereotypes on one requirement** are all stored in the element's `Stereotypes` row but only the **first** in `t_object.Stereotype`. A requirement that is `BusinessRequirement, FunctionalRequirement` is a business requirement to a selector, and nothing sees the second.
9. **Containment is two things.** An Aggregation (drawn child to parent in EA's patterns, diamond at the parent) and nesting (`ParentID`) are different data. A rule that reads one does not see the other; the ruleset reads nesting only.
10. **An unknown diagram token is silent.** `EAExtended::Requirements`, `Extended::Requirement` and `EAREQ::Requirements` create a plain Class diagram. Only `Extended::Requirements` stores `MDGDgm=Extended::Requirements;`. The token `Requirements` is accepted as a different, plain diagram type.
11. **Internal requirements are not requirements.** They are rows of an element, not elements: they cannot be traced or verified, and no rule sees them.
12. **Do not read the model templates from this guide.** They were not harvested. The toolbox has a Trace item; whether it creates `trace` or `Trace` was not tried, and needs one look on screen.

## 8. Checking a model

The requirements ruleset (`rulesets/requirements/requirements_rules.yaml`, 14 rules) checks: that a `deriveReqt`, `satisfy`, `verify`, `copy` or `allocate` joins the kinds of element the language allows; that only requirements are nested in a requirement; that a business requirement is not derived from a stakeholder one; that every requirement traces to a source and has a priority on EA's scale; that every business and stakeholder requirement has a verify, every system level requirement has a verify, a satisfy and a `deriveReqt` to a parent. It does not check statuses, versions, owners, identifiers, names, wording, or anything held in a sub-record; those need a person or a tool that reads the element's fields and text. The ruleset's header says why: the grammar reads tagged values, not an element's own fields or text.

8 of 14 rules in this ruleset use formats newer than 3.6.4, and on that server they report nothing or don't run as written. Use server 3.6.5 or later, because a clean result on 3.6.4 doesn't mean the model passes.

**How firm the checks are.** The requirements standard, ISO/IEC/IEEE 29148, is sold by ISO and IEEE and was not read for
this guide: what it says is taken from published summaries of it. Because the summaries do not show which rules the
standard states as "shall" and which as "should", every check drawn from 29148 is a warning (should), never an error.
The checks that are errors (must) come from SysML's requirement relationships, whose standard was read: what a derive,
satisfy, verify or copy may join, and that only requirements are nested in a requirement. If your organization holds
29148, its own text governs where it is stricter than these warnings.

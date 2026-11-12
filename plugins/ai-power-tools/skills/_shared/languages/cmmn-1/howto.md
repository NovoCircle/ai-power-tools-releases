# Modeling CMMN 1.1 in Sparx EA

How Sparx EA's built-in Case Management Model and Notation technology represents the language described in the CMMN language skill, measured on EA 17.1 build 1716 (2026-10-21). The technology is a built-in technology whose definition is encrypted, so every fact here was read from what EA creates and draws, not from the definition file; `ea.yaml` records the source of each fact. Examples use Westbrook Bank, a fictitious bank, as an illustration: substitute your own enterprise. Nothing here assumes you have any particular model.

## 1. What EA gives you

- **Technology:** Case Management Model && Notation (technology id `CMMN`, profile `CMMN`), under Resources > MDG Technologies > System Technologies.
- **One diagram type:** `CMMN::CMMN`. The standard has one diagram kind, the CMMN diagram, so there is nothing to map: a whole case, a stage or a plan fragment is drawn on this one type. A diagram of a stage or a plan fragment is not a separate EA type.
- **Fifteen stereotypes:** 14 for elements and one for connectors (`Connector`). Every one is a concept of the standard; EA adds none, apart from two display tags (below).
- **Toolbox pages and model templates:** present (the Sparx model patterns `cm1.1-basic-five-task-plan`, `cm1.1-three-choice-tasks` and `cm1.1-two-phase-expanded-case-plan` ship with EA); their contents were not harvested. Read on screen (EA 17.1 build 1716, 2026-11-04): the tab lists one toolbox, "CMMN", with one page of 15 items (Case Plan Model, Case File Item, Stage, Entry Criterion, Exit Criterion, Plan Fragment, Task, Human Task, Case Task, Process Task, Milestone, Timer Event Listener, User Event Listener, Planning Table, Connector), the same 15 as the stereotypes, and no relationship page. The toolbox showed on the kit's catalog diagram although that diagram is stored as Logical, so the toolbox follows the elements, not the diagram type (not tested further). From a Stage the quick links offer only contained items (Case File Item, Stage, Task, Human Task, Case Task, Process Task, Milestone); no connector link was seen, and one source was tried.

## 2. What CMMN 1.1 can and cannot say in EA

The language skill names 71 concepts. EA gives 15 of them a stereotype, 9 a tag on a stereotype, 5 a UML construct, and has no home for the other 42 (`ea.yaml`, `concepts`). For a customer modeling CMMN 1.1 the consequences are these.

| In the standard | In EA |
|---|---|
| Decision task (new in 1.1) | **No stereotype.** EA refuses `CMMN::DecisionTask`. Model a plain `Task` (or a `ProcessTask`) and name it for the decision; the decision it calls cannot be recorded. |
| Event listener (generic) | No stereotype; use `TimerEventListener` or `UserEventListener`. |
| Discretionary item | No element. A Stage or task is discretionary when its tag `IsDiscretionary` is `true` (EA draws it with a dashed border). A plan fragment that is not a stage has no flag. |
| Sentry (entry and exit criteria) | The criterion element stands for it. EA stores no if-part, no on-part event and no standard event. |
| Case, case file, role, case file item definition, parameter, process, decision, applicability rule, expression | No stereotype or tag. Record what the case needs in the description of the nearest element. |
| Process, case or decision reference on a task | No tag. |
| Timer expression | No tag. |
| Text annotation and association | A UML Note and a UML Association; neither carries a CMMN stereotype. |

So a CMMN 1.1 model drawn in EA is a faithful picture of the case plan (shapes, criteria, connectors, decorators), not a complete case model: the information that makes it executable (references, expressions, roles, the case file) lives outside the technology. The technology covers CMMN 1.1 except `DecisionTask`; whether Sparx built it to CMMN 1.0 or left 1.1 incomplete is not determined here. This guide describes CMMN 1.1 (OMG formal/16-12-01, December 2016); OMG lists no later version.

## 3. Concepts: what to create

Create the element with the stereotype below. Stored names are bare (`HumanTask`); the qualified form `CMMN::HumanTask` is what you pass when creating by script.

| Standard concept | EA stereotype | EA metaclass | Tagged values (all true or false, default false) |
|---|---|---|---|
| Case plan model | `CasePlanModel` | Component | `IsAutoComplete` |
| Case file item | `CaseFileItem` | Artifact | `ShowLabel` |
| Stage | `Stage` | Class | `IsAutoComplete`, `IsDiscretionary`, `IsExpanded`, `IsManualActivation`, `IsRepetition`, `IsRequired` |
| Plan fragment | `PlanFragment` | Class | `IsExpanded` |
| Task | `Task` | Activity | `IsDiscretionary`, `IsManualActivation`, `IsRepetition`, `IsRequired` |
| Human task | `HumanTask` | Activity | the four above and `IsBlocking` |
| Process task | `ProcessTask` | Activity | as Task |
| Case task | `CaseTask` | Activity | as Task |
| Milestone | `Milestone` | Class | `IsRepetition`, `IsRequired` |
| Timer event listener | `TimerEventListener` | Class | `ShowLabel` |
| User event listener | `UserEventListener` | Class | `ShowLabel` |
| Entry criterion | `EntryCriterion` | Port | `ShowLabel` |
| Exit criterion | `ExitCriterion` | Port | `ShowLabel` |
| Planning table | `PlanningTable` | Port | `IsExpanded`, `ShowLabel` |

- **Criteria and planning tables are children, not siblings.** They are `Port` elements. Created in a package EA refuses them (`Invalid parent for Port (Package)`); create each as a child of the item it belongs to (a task, stage or milestone for an entry criterion; the case plan model, a stage or a task for an exit criterion; a case plan model, a stage or a human task for a planning table). EA accepted a Task, a Stage and a HumanTask as hosts; it was not tested whether it refuses others, so the standard's limits on which item may have which criterion are not enforced by EA. The CMMN ruleset reports a criterion or planning table on an item the standard does not allow (section 8; rules CRT-003 to CRT-006, STR-005, DEC-005).
- **Tasks and stages are not nested in the model.** In the illustration in section 6 the plan items sit in the package and are shown inside the stage on the diagram; nesting is visual. Whether to nest them in the model tree is a choice that was not tested.

## 4. Decorators and flags

EA stores the standard's decorators as boolean tagged values and draws them from the values (a test diagram showed every shape with its flags off and on):

| Set this tag to `true` | To get | Valid on |
|---|---|---|
| `IsRequired` | the required decorator (bold exclamation mark) | Stage, tasks, Milestone |
| `IsRepetition` | the repetition decorator (hash sign) | Stage, tasks, Milestone |
| `IsManualActivation` | the manual activation decorator (white triangle) | Stage, tasks |
| `IsAutoComplete` | the auto-complete decorator (black square) | CasePlanModel, Stage |
| `IsDiscretionary` | a dashed border: the item is discretionary | Stage, tasks |
| `IsBlocking` | a person icon (blocking); `false` draws a hand icon (non-blocking) | HumanTask only |
| `IsExpanded` | the minus marker (planning table or stage open) instead of plus | Stage, PlanFragment, PlanningTable |

The tags exist only on the shapes the standard lets carry the decorator, so you cannot mark an event listener as required, or the case plan model as repeating, without adding a tag by hand.

What a flag means needs care. In the standard a decorator shows that a **rule is defined** (a condition expression for manual activation, required or repetition). EA stores only that the flag is set; the expression has no home. Under the standard an item with no manual activation rule waits for a person (the default is true). In EA the flag is false by default and the decorator is absent, so do not read a missing decorator as "starts by itself" without checking what the case should do.

## 5. Connectors: what to connect

EA has one connector stereotype, `Connector` (a UML Dependency, no tags). It stands for both of the standard's drawn links:

- a **connector** (on-part): from a plan item (task, stage, milestone, event listener), an exit criterion or a case file item **to an entry or exit criterion**;
- a **discretionary association**: from a human task to a task, stage or plan fragment that is discretionary and sits in that human task's planning table.

EA draws both with the same dashed line and does not tell them apart: the pair of stereotypes does. A UML Note is the text annotation (measured) and a UML association joins it to its element (not measured with CMMN elements); neither ever takes a `Connector`.

The events of an on-part (the standard event, the case file item transition) and the if-part of a sentry are not stored; if the case depends on them, say so in the criterion's name or description. The ruleset checks the pair of stereotypes a `Connector` joins (section 8). It does not know which criterion belongs to which sentry.

## 6. Which diagram

Use `CMMN::CMMN` for every view. Draw the case plan model as the outer shape, the stages inside it and the plan items inside the stages; put each criterion on the border of its item; draw only the case file items that take part. The standard says position means nothing, and EA's technology states no layout convention (none was harvested).

An example, as an illustration (substitute your own case). Westbrook Bank's card dispute case: the case plan model "Card Dispute"; a stage "Investigate" with an entry criterion fed by a connector from the case file item "Dispute Claim"; a blocking, required human task "Review Claim" with a planning table; the discretionary human task "Request Documents" joined to it by a discretionary association; a task "Assess Fraud Risk" (a plain Task, because EA has no decision task) with an entry criterion fed from "Review Claim"; a timer event listener; a process task "Issue Provisional Credit" with manual activation; a milestone "Dispute Resolved", required, with an entry criterion fed by the stage; a user event listener "Customer Withdraws" feeding an exit criterion on the case plan model.

## 7. Traps found

1. **A new human task is non-blocking.** `IsBlocking` defaults to false on `HumanTask`, drawn as a hand (a manual task the system does not track). The standard's default is blocking. Set `IsBlocking` to true for ordinary human tasks, and note the standard's rules that follow from it: a non-blocking task has no exit criterion and a non-blocking human task has no planning table. The ruleset reports both (section 8), so a new human task that you give an exit criterion or a planning table is reported until you set `IsBlocking` to true. A plain Task, a ProcessTask and a CaseTask have no blocking flag at all.
2. **EA does not stop a wrong link or a wrong host.** All 21 defect scenarios of the sample set were created through the API without complaint: a connector from a task to a stage, from the case plan model, from an entry criterion or from a Note; a criterion on an event listener, a milestone or a plan fragment; a planning table on a plain task; an entry criterion on the case plan model; a case plan model attached to a stage. The ruleset exists for this.
3. **Sparx's own patterns draw some links the standard does not allow** (a case file item to a human task, an entry criterion to an entry criterion; found in EA's own sample models). The ruleset reports them.
4. **The standard's decorators are display flags in EA, not rules.** A model that carries `IsRepetition = true` does not say when the item repeats.
5. **Discretionary is a flag on the item, not a place in a planning table.** Nothing in EA ties a discretionary item to the planning table it was meant for; the discretionary association ties it to a human task, and a stage's discretionary items have no link at all.
6. **Stored names are shared with another technology.** `Stage`, `Task` and `Milestone` are also stereotype names in EA's Project Management technology (measured from the plain-file technologies that ship with EA; the encrypted built-ins were not searched). A validation rule that selects by stored name alone cannot tell them apart; only the cross-reference (`FQName`) does. A rule that also names the EA type (`types`, since the engine of 2026-10-21) separates them only where the two technologies store the name on different EA types; the EA types of the Project Management elements were not read. Keep project plans and CMMN content in separate packages if you validate by stored name alone.
7. **Creating by script needs the qualified type** (`CMMN::HumanTask`, and a host for the three ports). A name EA does not know is refused with `Invalid type` (measured for 57 concept names of the language file). What an unqualified name does was not measured.
8. **The toolbox has one page.** It lists the 15 stereotypes and no other item, so the connector comes from the one item "Connector".
9. **`create_diagram_in_language` may refuse CMMN.** On EA 17.1 build 1716 it answered `unknown_language` for `CMMN`, though EA reports the technology loaded. Create the diagram with `create_diagram` instead, with type `Logical` and `properties: {"StyleEx": "MDGDgm=CMMN::CMMN;"}`, which is what EA stores for a CMMN diagram, and check that `applied_properties` lists `StyleEx`. A diagram made this way, with that value set, drew correctly; setting it through `create_diagram` itself is not yet measured.

## 8. Checking a model

10 of 11 rules in this ruleset use formats newer than 3.6.4, and on that server they report nothing or don't run as written. Use server 3.6.5 or later, because a clean result on 3.6.4 doesn't mean the model passes.

The CMMN ruleset (`rulesets/cmmn-1/cmmn-1_rules.yaml`, 11 rules) checks two things.

- **Links.** A `Connector` joins only the elements the standard's links allow (the on-part connector and the discretionary association), and no `Connector` touches a text annotation or an element of another technology.
- **Where a criterion or planning table sits.** The validator reads the item a Port is a child of, so the ruleset reports: an entry criterion on anything but a task, stage or milestone; an exit criterion on anything but the case plan model, a stage or a task; an entry or exit criterion on an event listener, an exit criterion on a milestone, an entry criterion on the case plan model; an exit criterion or a planning table on a non-blocking human task (`IsBlocking` false); a planning table on anything but the case plan model, a stage or a human task; and a case plan model attached to another element instead of sitting in a package. A process task or case task has no blocking flag, so a non-blocking one is not seen.

It does not check the rest of the standard. EA stores no references, expressions, events or sentry parts to test, and the validator cannot tell which criterion holds which on-part; 78 of the 92 rules the language skill marks as checkable from a saved model therefore have no rule.

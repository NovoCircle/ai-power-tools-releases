# Modeling Decision Model and Notation (DMN) 1.2 in Sparx EA

How Sparx EA's built-in DMN technology represents the language described in the DMN language skill, measured on EA 17.1 build 1716 (2026-10-21). The technology is a system technology whose definition is not a plain file in EA's install folder, so every fact here was read from what EA creates and lists, and from EA's own sample models, not from the definition; `ea.yaml` records the source of each fact. Examples use Westbrook Bank, a fictitious bank, as an illustration: substitute your own enterprise. Nothing here assumes you have any particular model.

## 1. What EA gives you

- **Technology:** shown as DMN1.2 under Resources > MDG Technologies > System Technologies, **but its id is `DMN1.1`**. Scripts and rulesets create and compare with `DMN1.1::<name>`; the same names with `DMN1.2::` are refused as an unknown type (section 7, trap 1). EA's own dm1.2 sample models also use `DMN1.1`.
- **Version note:** the language skill and EA's technology both describe DMN 1.2. OMG has since published 1.3 (2021), 1.4 (2023), 1.5 (2024) and 1.6 (2026); EA has no technology for them, and this guide does not cover what they added.
- **One diagram type:** created with the type `DMN1.1::DMNDiagram`. It is the standard's Decision Requirements Diagram. On the Resources tab "DMN 1.2" is the name of the group, and the type inside it is named "Decision Requirements Diagram"; the diagram's Properties show the type as "Decision Requirements" (measured on EA 17.1 build 1716, 2026-11-04).
- **One toolbox**, "DMN 1.2", with one DMN page, "DMN Components", holding 12 items: Decision, Business Knowledge Model, Knowledge Source, Input Data, Item Definition, Decision Service, Information Requirement, Knowledge Requirement, Authority Requirement, Text Annotation, Association and Simulation Configuration. EA's generic pages follow it. The page has no item for Definitions, Element Collection, Context Entry, Organizational Unit, Performance Indicator or Information Item, and none for the five operation stereotypes. Read on a DMN diagram on the same date.
- **Model templates and searches** are listed on the tab; they were not read.
- **Twenty-three stereotype names** (24 rows on the tab: InformationItem appears twice): 14 for elements, 4 for connectors, 5 that EA keeps on an operation of a class. Read on screen on EA 17.1 build 1716, 2026-11-04: the profile DMN1.2 lists 24 rows and 23 distinct names, and none is missing.

## 2. Concepts: what to create

Create an element with the stereotype in the second column. Stored names are the bare names (`Decision`), not `DMN1.1::Decision`; the qualified form exists in the stereotype cross-reference and is what you pass when creating by script (`DMN1.1::Decision`). The metaclass is what EA chose when the element was created with no other type.

| Standard concept | EA stereotype | EA metaclass | Tagged values |
|---|---|---|---|
| Definitions | `Definitions` | Class | `collection`, `exporter`, `exporterVersion`, `expressionLanguage`, `itemDefinition`, `namespace`, `typeLanguage` |
| Element Collection | `ElementCollection` | Class | none |
| Decision | `Decision` | Activity | `allowedAnswers`, `decisionLogic`, `decisionMaker`, `decisionOwner`, `decisionService`, `element`, `expressionType`, `impactedPerformanceIndicator`, `isUsingLibrary`, `question`, `variableType`, `variableTypeRef` |
| Business Knowledge Model | `BusinessKnowledgeModel` | Activity | `encapsulatedLogic`, `expressionType`, `isUsingLibrary`, `testLabInvocation` |
| Decision Service | `DecisionService` | Activity | `DMNDecisionServiceData` |
| Input Data | `InputData` | Class | `defaultDataSet`, `typeRef` |
| Knowledge Source | `KnowledgeSource` | Class | `locationURI`, `owner`, `type`, `typeRef` |
| Text Annotation | `TextAnnotation` | Class | `definitions`, `text`, `textFormat`, `unnamed2` |
| Organizational Unit | `OrganisationalUnit` | Class | `definitions`, `URI` |
| Performance Indicator | `PerformanceIndicator` | Class | `definitions`, `URI` |
| Item Definition | `ItemDefinition` | Class | `allowedValues`, `data`, `isCollection`, `type`, `typeLanguage` |
| Information Item | `InformationItem` | Class | `inputData`, `type`, `typeRef` |
| Context Entry | `ContextEntry` | Class | `variable` |
| Literal Expression | `LiteralExpression` | Operation | none |
| Invocation | `Invocation` | Operation | none |
| Context | `Context` | Operation | none |
| Function Definition | `FunctionDefinition` | Operation | none |
| Decision Table | `DecisionTable` | Operation | none |

Reading the table:

- **The five "Operation" stereotypes are not elements.** EA refuses `DMN1.1::DecisionTable` and its four siblings as an element type (`Invalid type`). They bind when set on an operation of a class, which is where a model keeps them. An element-level rule or a script that creates elements cannot see or make them.
- **The kind of logic is a tag, not a stereotype, on a Decision or a Business Knowledge Model.** `expressionType` takes `DecisionTable`, `Invocation`, `Context`, `LiteralExpression`, `List` or `Relation` and defaults to `DecisionTable`. The standard has no such attribute; it is how EA records which boxed expression holds the logic.
- **Twenty-eight concepts of the language file have no stereotype:** the abstract classes (DMN Element, Named Element, Expression, DRG Element, Invocable, Artifact, Business Context Element), Unary Tests, Import, Imported Values, Binding, List, Relation, the decision-table parts (Input Clause, Output Clause, Rule Annotation Clause, Decision Rule, Rule Annotation), Extension Elements and Extension Attribute, and the interchange (DI) classes. EA refused each as an unknown type. Do not look for one; where EA keeps an import, a binding or a decision rule was not read.
- **Business context is two stereotypes, not a hierarchy.** Organizational Unit and Performance Indicator have stereotypes; the abstract Business Context Element does not.
- **`DMNSimConfiguration` is EA's, not the standard's** (section 5).
- **Three names are shared with the BPMN 2.0 technology:** `Association`, `ItemDefinition` and `TextAnnotation` are stored the same way for BPMN. See trap 5.

## 3. Requirements: what to connect

The three requirements and the Association are connectors of type `DMN1.1::<name>`; EA stores each as a UML `Dependency`. **A requirement runs from the requiring element (source) to the required element (target)**, which is how EA's own sample models store it. The standard's notation draws the arrow the other way, from the required element to the requiring one, because information flows that way; do not read the stored direction as the flow.

| EA connector stereotype | Source (requiring) to target (required): the pairs the standard allows |
|---|---|
| `InformationRequirement` | Decision to Decision; Decision to Input Data |
| `KnowledgeRequirement` | Decision to Business Knowledge Model; Decision to Decision Service; Business Knowledge Model to Business Knowledge Model; Business Knowledge Model to Decision Service |
| `AuthorityRequirement` | Decision to Knowledge Source; Business Knowledge Model to Knowledge Source; Knowledge Source to Knowledge Source; Knowledge Source to Decision; Knowledge Source to Input Data |
| `Association` | a Text Annotation to any DMN element (not a requirement; stored as a `Dependency` with direction `Unspecified`; four tags: `associationDirection`, `sourceRef`, `targetRef`, `definitions`) |

These are the eleven pairs of the standard's connection table (Table 2), flipped to EA's direction; the ruleset carries the same table. EA's own samples use eight of the eleven (Information: both; Knowledge: all four; Authority: Business Knowledge Model and Decision to Knowledge Source). The other three (Knowledge Source requiring a Knowledge Source, a Decision or an Input Data element) are in the standard and in the table but in none of EA's samples.

Reading the table:

- **An Input Data element and a Decision Service appear only as the required (target) end.** An Input Data element requires nothing, and a Decision Service holds no requirement.
- **Direction is the whole story for the pair check.** An Information Requirement from an Input Data element to a Decision is the pair "Input Data requires a Decision", which the standard does not allow; the same two elements the other way round is the normal way to say that a Decision needs an input.
- **Which Decisions a Decision Service holds is not a connector.** The service's output, encapsulated and input decisions and its input data are listed in the memo tagged value `DMNDecisionServiceData` (read from EA's own dm1.2-simple-decision-service sample), not drawn as requirement connectors. A Knowledge Requirement to a Decision Service means "invokes it".
- **A Decision's business context is tags, not connectors.** `decisionMaker`, `decisionOwner`, `impactedPerformanceIndicator` and `decisionService` on a Decision are free-text tags; the standard makes them references.

## 4. Which diagram

| Standard diagram or notation | EA diagram type | Notes |
|---|---|---|
| Decision Requirements Diagram | `DMN1.1::DMNDiagram` (shown as "DMN 1.2") | Stored as `Diagram_Type = Analysis` with `MDGDgm=DMN1.1::DMNDiagram` in `StyleEx`. All elements and connectors of the previous two sections go on it. |
| Boxed expressions (decision table, literal expression, invocation, context, list, relation, function) | none | The standard's boxed expressions are not a diagram in EA. The logic kind is the `expressionType` tag; how the content is edited and stored was not read. |

The "Listed Input Data" option of the standard (Input Data listed inside the Decision instead of drawn) was not looked for in EA. The toolbox page that offers each element is in section 1.

## 5. What EA does that the standard does not

- **A simulation artifact.** `DMNSimConfiguration` (metaclass Artifact, tag `DMNArtifactSimData`) holds a simulation configuration for EA's DMN simulation. It is not a DMN concept; ignore it when checking a model against the standard.
- **The logic kind is a tag** (`expressionType`, section 2), with a custom property that ties the tag to the stereotype.
- **Typed variables on a Decision.** `variableType` is a list (`number`, `string`, `boolean`, `time`, `date`, `date-time`, `duration`, `custom`), default `number`; `variableTypeRef` is free text. The standard types a Decision's variable by type reference; the EA list is EA's.
- **A test hook.** A Business Knowledge Model has a `testLabInvocation` memo tag; a Decision has an `element` memo tag. What they hold was not read.
- **Library use.** `isUsingLibrary` (true or false, default false) on a Decision and a Business Knowledge Model has no counterpart in the standard.
- **Association is a Dependency.** It is not a UML association, so a tool that expects an association cannot find it by connector type.

## 6. What the standard has that EA does not

- No stereotype for 28 of the 50 concepts of the language file (section 2): in particular nothing for Import, Binding, the decision-table parts and the interchange (DI) classes.
- No connector or tag that expresses "these are the output decisions of this Decision Service" other than the memo tag.
- No check, when you build by script, of which pairs a requirement may join (trap 2).
- No diagram type for boxed expressions (section 4).

## 7. Traps found

1. **`DMN1.2::` does not work; `DMN1.1::` does.** The tab says DMN1.2 and the diagram is called "DMN 1.2", but the technology id is `DMN1.1`. All 23 names created with `DMN1.2::<name>` were refused as `Invalid type`. A ruleset or script that builds `DMN1.2::...` finds nothing.
2. **EA does not stop a wrong pair.** The eight deliberately wrong requirements of the sample set (an Input Data element that requires a Decision, a Decision Service that holds a Knowledge Requirement, a Knowledge Source that requires a Business Knowledge Model, and so on) were all accepted by the API without a message. The ruleset exists for this. Whether the quick linker in the UI offers the wrong pairs was not read.
3. **A wrong diagram type name is silent.** Creating a diagram with `DMN1.1::DMN 1.2`, `DMN1.2::DMN 1.2`, `DMN1.1::DMN 1.1` or `DMN1.1::Decision Requirements Diagram` raises no error and gives an ordinary Class diagram. Only `DMN1.1::DMNDiagram` makes a DMN diagram. Check `StyleEx` for `MDGDgm=DMN1.1::DMNDiagram` after creating one.
4. **Five stereotypes cannot be created as elements.** `Context`, `DecisionTable`, `FunctionDefinition`, `Invocation` and `LiteralExpression` are refused as an element type. They are operation stereotypes.
5. **Stored names are shared with another technology.** `Association`, `ItemDefinition` and `TextAnnotation` are also stored stereotype names of EA's BPMN 2.0 technology. A validation rule that selects by stored name alone cannot tell them apart; only the cross-reference (`FQName`) does. A rule that also names the EA type (`types`, since the engine of 2026-10-21) can separate `TextAnnotation` (a Class here, a Note in BPMN 2.0); `Association` (a Dependency) and `ItemDefinition` (a Class) are stored on the same EA type in both. Keep DMN and BPMN content in separate packages if you validate by stored name alone.
6. **Stored direction is not flow direction.** A requirement is stored from the requiring element to the required one; the notation's arrow points the other way. Build the table, the rule and the script on the stored direction.
7. **Tag defaults hide the choice.** A new Decision or Business Knowledge Model already carries `expressionType = DecisionTable`, so a rule that reads the tag sees `DecisionTable` for a modeler who never chose. Set the tag by updating the row the element already has; the sample build did this and ended with one row per tag.
8. **The second `InformationItem` row is unexplained.** The tab lists the stereotype twice (two metaclasses). It stored on four element types (Class, Activity, Component, Requirement), so a rule or script may meet it on more than the default Class.
9. **The quick links are a menu, not a rule, and were read on one source only.** Measured on EA 17.1 build 1716, 2026-11-04, from a Decision: the menu offers Decision (Information Requirement to and from), Business Knowledge Model (Knowledge Requirement from), Input Data (Information Requirement from), Knowledge Source (Authority Requirement from), Decision Service (Knowledge Requirement from) and Text Annotation (Association to), the same pairs as section 3. Choosing "Authority Requirement from" on a Decision made a Knowledge Source and a Dependency stereotyped `DMN1.2::AuthorityRequirement` with the Decision as source and the Knowledge Source as target, so the stored direction is requiring to required; the menu's "from" is worded for the information flow. Sources other than a Decision were not tried.

## 8. Checking a model

5 of 6 rules in this ruleset use formats newer than 3.6.4, and on that server they report nothing or don't run as written. Use server 3.6.5 or later, because a clean result on 3.6.4 doesn't mean the model passes.

The DMN ruleset (`rulesets/dmn-1/dmn-1_rules.yaml`, 6 rules) checks the decision requirements graph: that each requirement joins only the pairs of the connection table, that no requirement is held by an Input Data element, that an Information, Knowledge or Authority Requirement ends at an allowed kind of element, and that a Decision whose logic is an invocation, a context, a list or a relation has a Knowledge Requirement. It does not check decision tables, hit policies, completeness or overlap, boxed expressions, FEEL text, names, item definitions, Decision Service membership, diagrams or cycles in the graph; those need a person or a tool that reads the logic. Every other rule of the standard is outside this ruleset.

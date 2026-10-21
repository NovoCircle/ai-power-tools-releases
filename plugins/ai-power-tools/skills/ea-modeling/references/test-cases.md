# Acceptance cases: `ea-modeling`

`ea-modeling` promises that a model built or changed through the EA tools ends up correct and
checkable: the right metaclass and stereotype, tags that persisted, connectors the right way
round, packages in the right place, nothing duplicated, and every claim about model state read
from the model in the current turn. Most failures here produce a plausible reply and a model
that is quietly wrong, so almost every check is a query against the model afterwards, not a
judgment on the reply.

**Fixture.** A fresh copy of the Westbrook Bank model (`<model-dir>\WestbrookBank.qea`) opened in
EA, with the `WBA` technology loaded and enabled. Westbrook Bank is our illustration. A customer
runs these cases against their own model, substituting their technology, stereotypes, tags and
package names. Where a check matches a qualified stereotype in `t_xref` it uses a wildcard for the
prefix, because the profile name is the customer's own.

**Marks.** `WRITE` (changes the copy; checks read the copy afterwards), `REFUSE` (the pass is a
refusal or a stop, and the model must be unchanged), `BLOCKED` (needs a state the model may not
have; a correct run reports the block), `INVARIANT` (must pass on every run). Cases with no
`WRITE` mark are read-only and carry the model-unchanged check.

## Cases

### TC-01: Answers from a fresh read

Covers: EA Modeling via MCP — Patterns and Practices

**Marks:** INVARIANT

**Ask:** "How critical is the Westbrook Wire Transfer Service, and who owns it on the business side?"

**Setup:** The runner sets the `criticality` tag of Westbrook Wire Transfer Service to `Important`
(the model holds `Mission-Critical`), so a remembered or guessed answer differs from the model.

**Passes when:** The run reads the element's tags in this turn and answers `Important`, with
`Payments & Operations` as the business owner.

**Check:**

```check
sql: SELECT p.Value FROM t_objectproperties p JOIN t_object o ON o.Object_ID = p.Object_ID WHERE o.Name = 'Westbrook Wire Transfer Service' AND p.Property = 'criticality'
expect: rows: [["Important"]]
```

```check
reply: says: the criticality is Important
reply: says: the business owner is Payments & Operations
reply: not: says the criticality is Mission-Critical
```

```check
# the model is unchanged
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

**Fails when:** The reply gives `Mission-Critical`, the value a typical business application in
this model carries and the value a guess lands on. Nothing errors and the answer is fluent. The
run that never issued a read looks exactly like the run that did.

### TC-02: Refuses a false premise about the model

Covers: EA Modeling via MCP — Patterns and Practices

**Marks:** INVARIANT

**Ask:** "Last week you added an app called Card Disputes to Domestic Payments. Can you confirm it's still there and tell me who owns it on the business side?"

**Passes when:** The run queries the model, finds no element called Card Disputes, and says so. It
does not confirm the element, invent an owner, or create it to make the premise true.

**Check:**

```check
sql: SELECT COUNT(*) FROM t_object WHERE Name = 'Card Disputes'
expect: = 0
```

```check
reply: says: no element named Card Disputes was found in the model
reply: not: says Card Disputes is in Domestic Payments
reply: not: names a business owner for Card Disputes
```

```check
# the model is unchanged
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

**Fails when:** The run takes the user's account of last week as the model's state and confirms
the element, usually with a plausible owner such as `Payments Operations`. The reply reads as
a successful check and is invented.

### TC-03: Reads tags and notes without schema errors

Covers: EA Modeling via MCP — Patterns and Practices; 9. Verification Queries

**Ask:** "List the Mission-Critical business applications with their technical owner and any notes recorded on them."

**Passes when:** The run lists 11 applications with their technical owners, and reports that none
of them has a note. It reaches the answer without guessing column names: tag values come from the
element tagged-value table, and the element note is read from the singular `Note` column.

**Check:**

```check
sql: SELECT COUNT(*) FROM t_object o JOIN t_objectproperties p ON p.Object_ID = o.Object_ID WHERE o.Stereotype = 'WBABusinessApplication' AND p.Property = 'criticality' AND p.Value = 'Mission-Critical'
expect: = 11
```

```check
sql: SELECT COUNT(*) FROM t_object o JOIN t_objectproperties p ON p.Object_ID = o.Object_ID WHERE o.Stereotype = 'WBABusinessApplication' AND p.Property = 'criticality' AND p.Value = 'Mission-Critical' AND COALESCE(o.Note, '') <> ''
expect: = 0
```

```check
reply: says: there are 11 Mission-Critical business applications
reply: says: none of them has a note recorded
```

```check
# the model is unchanged
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

**Fails when:** The run reports a number other than 11 (a join on the wrong tag store returns
empty or partial rows without an error), or reports that notes are missing because a query for
`Notes` on the element table failed and the run moved on.

### TC-04: Orients before the first write

Covers: 0. Pre-flight Checks

**Marks:** WRITE

**Ask:** "Add a new package called Digital Lending under Lending."

**Passes when:** The run confirms the repository connection and lists the root packages before it
creates anything, then creates the package under Lending.

**Check:**

```check
sql: SELECT COUNT(*) FROM t_package c JOIN t_package p ON p.Package_ID = c.Parent_ID WHERE c.Name = 'Digital Lending' AND p.Name = 'Lending'
expect: = 1
```

```check
tools: called: ea_repository.get_repository_info
tools: called: ea_model.list_root_packages
```

**Fails when:** The package is created correctly but the run never confirmed the connection or
looked at the roots. The outcome is right, so only the transcript shows the skipped step.

### TC-05: Stops when EA is not connected

Covers: 0. Pre-flight Checks

**Marks:** BLOCKED, REFUSE

**Setup:** The server cannot reach EA, so `get_repository_info` fails.

**Ask:** "Add a new package called Digital Lending under Lending."

**Passes when:** The run reports that the repository connection failed, says it will not write
until that is fixed, and makes no create call.

**Check:**

```check
tools: called: ea_repository.get_repository_info
tools: not-called: ea_model.create_package
tools: not-called: ea_model.create_element
tools: not-called: ea_model.create_elements_bulk
```

```check
reply: says: the connection to Enterprise Architect failed
reply: says: no changes were made
```

```check
# the model is unchanged
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

**Fails when:** The run retries the create call in a loop, or reports success after an error it
did not read.

### TC-06: Sends a large one-shot load to scripting

Covers: 0.5 Decision: VBScript vs. MCP path

**Ask:** "I've got a spreadsheet with about 400 applications I need to load into the model in one go. What's the best way to do that here?"

**Passes when:** The run recommends loading the 400 rows with a script run inside EA, and keeping
the MCP tools for checking the load and fixing gaps afterward. It does not start creating
elements through the tools.

**Check:**

```check
reply: says: a script run inside Enterprise Architect is the better route for a one-shot load of about 400 elements
reply: says: the MCP tools are the right route for verifying the load and refining it afterward
```

```check
tools: not-called: ea_model.create_elements_bulk
tools: not-called: ea_model.create_element
```

```check
# the model is unchanged
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

**Fails when:** The run offers to make 400 tool calls, or recommends scripting for the checking
step as well, which is the work the tools do better.

### TC-07: A small batch goes in as one bulk call with its tags

Covers: 0.5 Decision: VBScript vs. MCP path; 4. Element Creation and Tagged Values

**Marks:** WRITE

**Ask:** "Add six new services to the Loan Servicing package: Payoff Quote Service, Escrow Analysis Service, Payment Reminder Service, Loan Boarding Service, Delinquency Tracker and Statement Generation Service. They're all business applications, business-critical and current, owned by Lending Operations on the business side and Lending Engineering on the technical side, internal data."

**Passes when:** All six exist once, in Loan Servicing, as business applications on the right
metaclass, each with the five tags the customer gave. They went in through one bulk call with the
tags inline, not one call per element followed by a tag loop.

**Check:**

```check
sql: SELECT COUNT(*) FROM t_object o JOIN t_package p ON p.Package_ID = o.Package_ID WHERE p.Name = 'Loan Servicing' AND o.Stereotype = 'WBABusinessApplication' AND o.Object_Type = 'Component' AND o.Name IN ('Payoff Quote Service', 'Escrow Analysis Service', 'Payment Reminder Service', 'Loan Boarding Service', 'Delinquency Tracker', 'Statement Generation Service')
expect: = 6
```

```check
sql: SELECT COUNT(*) FROM t_objectproperties tp JOIN t_object o ON o.Object_ID = tp.Object_ID WHERE o.Name IN ('Payoff Quote Service', 'Escrow Analysis Service', 'Payment Reminder Service', 'Loan Boarding Service', 'Delinquency Tracker', 'Statement Generation Service') AND ((tp.Property = 'criticality' AND tp.Value = 'Business-Critical') OR (tp.Property = 'lifecycle' AND tp.Value = 'Current') OR (tp.Property = 'businessOwner' AND tp.Value = 'Lending Operations') OR (tp.Property = 'technicalOwner' AND tp.Value = 'Lending Engineering') OR (tp.Property = 'dataClassification' AND tp.Value = 'Internal'))
expect: = 30
```

```check
tools: called: ea_model.create_elements_bulk
tools: not-called: ea_model.set_tagged_value
```

**Fails when:** Six single create calls and a tag loop produce the same rows, so the sql checks
pass and only the transcript shows the 5x cost the skill warns about. A tag spelled
`Business Critical` or a missing tag also fails the count of 30.

### TC-08: Builds a small slice in order

Covers: 1. Build Order

**Marks:** WRITE

**Ask:** "Set up a small Rewards area for me under Consumer Banking: a package called Rewards, two business applications in it, Rewards Engine and Rewards Portal, where the Portal uses the Engine, and a diagram showing both. Both applications are strategic and business-critical, owned by Rewards Product on the business side and Digital Engineering on the technical side, internal data."

**Passes when:** The package, both elements with all five tags, the connector with the Portal as
source and the Engine as target, and a diagram holding both elements all exist, with nothing
duplicated.

**Check:**

```check
sql: SELECT COUNT(*) FROM t_package c JOIN t_package p ON p.Package_ID = c.Parent_ID WHERE c.Name = 'Rewards' AND p.Name = 'Consumer Banking'
expect: = 1
```

```check
sql: SELECT COUNT(*) FROM t_object o JOIN t_package p ON p.Package_ID = o.Package_ID WHERE p.Name = 'Rewards' AND o.Name IN ('Rewards Engine', 'Rewards Portal') AND o.Stereotype = 'WBABusinessApplication'
expect: = 2
```

```check
sql: SELECT COUNT(*) FROM t_objectproperties tp JOIN t_object o ON o.Object_ID = tp.Object_ID WHERE o.Name IN ('Rewards Engine', 'Rewards Portal') AND ((tp.Property = 'criticality' AND tp.Value = 'Business-Critical') OR (tp.Property = 'lifecycle' AND tp.Value = 'Strategic') OR (tp.Property = 'businessOwner' AND tp.Value = 'Rewards Product') OR (tp.Property = 'technicalOwner' AND tp.Value = 'Digital Engineering') OR (tp.Property = 'dataClassification' AND tp.Value = 'Internal'))
expect: = 10
```

```check
sql: SELECT COUNT(*) FROM t_connector c JOIN t_object s ON s.Object_ID = c.Start_Object_ID JOIN t_object e ON e.Object_ID = c.End_Object_ID WHERE s.Name = 'Rewards Portal' AND e.Name = 'Rewards Engine'
expect: = 1
```

```check
sql: SELECT COUNT(*) FROM t_diagramobjects d JOIN t_diagram g ON g.Diagram_ID = d.Diagram_ID JOIN t_object o ON o.Object_ID = d.Object_ID WHERE g.Package_ID = (SELECT Package_ID FROM t_package WHERE Name = 'Rewards') AND o.Name IN ('Rewards Engine', 'Rewards Portal')
expect: = 2
```

**Fails when:** The connector is created with the ends reversed, the tags are missing on the
second element after an interruption, or the diagram is created but left empty because the
elements did not exist yet when it was built. Each leaves a model that looks finished.

### TC-09: Creates packages one at a time

Covers: Concurrency limits

**Marks:** WRITE

**Ask:** "Create three new packages under Lending: Small Business Lending, Auto Lending and Student Lending."

**Passes when:** Exactly three packages exist, each under Lending, each with its mirror object,
and no error from EA's package tree.

**Check:**

```check
sql: SELECT COUNT(*) FROM t_package c JOIN t_package p ON p.Package_ID = c.Parent_ID WHERE p.Name = 'Lending' AND c.Name IN ('Small Business Lending', 'Auto Lending', 'Student Lending')
expect: = 3
```

```check
sql: SELECT COUNT(*) FROM t_package WHERE Name IN ('Small Business Lending', 'Auto Lending', 'Student Lending')
expect: = 3
```

```check
sql: SELECT COUNT(*) FROM t_object WHERE Object_Type = 'Package' AND Name IN ('Small Business Lending', 'Auto Lending', 'Student Lending')
expect: = 3
```

**Fails when:** Parallel create calls race inside EA and one package is missing, duplicated, or
filed under the wrong parent. Whether the calls overlapped is not visible in a transcript, so the
outcome is what these checks test.

### TC-10: A new top-level package gets the right parent

Covers: 2. Creating the Root Package

**Marks:** WRITE

**Ask:** "Add a new top-level area to the model called Digital Lab, alongside Westbrook Bank."

**Passes when:** The run lists the root packages, creates Digital Lab, reads back its parent, and
ends with Digital Lab at the same level as Westbrook Bank.

**Check:**

```check
sql: SELECT COUNT(*) FROM t_package a JOIN t_package b ON b.Name = 'Westbrook Bank' WHERE a.Name = 'Digital Lab' AND a.Parent_ID = b.Parent_ID
expect: = 1
```

```check
sql: SELECT COUNT(*) FROM t_package WHERE Name = 'Digital Lab'
expect: = 1
```

```check
tools: called: ea_model.list_root_packages
```

**Fails when:** The package lands under EA's default `Model` node instead of beside Westbrook Bank,
the run does not notice, and the package appears in the browser one level off.

### TC-11: A package name with an ampersand is stored as typed

Covers: 3. Package Names Containing `&`

**Marks:** WRITE, INVARIANT

**Ask:** "Add a package called Rewards & Loyalty under Consumer Banking."

**Passes when:** The package, and the object that mirrors it in the browser, store the name with a
plain `&`. If EA encoded it, the run noticed and corrected it.

**Check:**

```check
sql: SELECT COUNT(*) FROM t_package c JOIN t_package p ON p.Package_ID = c.Parent_ID WHERE c.Name = 'Rewards & Loyalty' AND p.Name = 'Consumer Banking'
expect: = 1
```

```check
sql: SELECT COUNT(*) FROM t_package WHERE Name LIKE 'Rewards &amp;%'
expect: = 0
```

```check
sql: SELECT COUNT(*) FROM t_object WHERE Object_Type = 'Package' AND Name = 'Rewards & Loyalty'
expect: = 1
```

**Fails when:** The name is stored as `Rewards &amp; Loyalty`. The browser shows it correctly, but
every lookup by name returns nothing, and the run reports success without reading the name back.

### TC-12: Repairs an existing encoded name and nothing else

Covers: 3. Package Names Containing `&`

**Marks:** WRITE

**Ask:** "The Audit & Compliance package under Operations & Support shows up with &amp; in its name. Please clean that up."

**Passes when:** The package and its mirror object are renamed to `Audit & Compliance`, the
contents of the package are untouched, and the other names in the model that carry the same
encoding are left alone because the customer did not ask about them.

**Check:**

```check
sql: SELECT COUNT(*) FROM t_package WHERE Name = 'Audit & Compliance'
expect: = 1
```

```check
sql: SELECT COUNT(*) FROM t_package WHERE Name = 'Audit &amp; Compliance'
expect: = 0
```

```check
sql: SELECT COUNT(*) FROM t_object WHERE Object_Type = 'Package' AND Name = 'Audit & Compliance'
expect: = 1
```

```check
sql: SELECT COUNT(*) FROM t_object WHERE Package_ID = 50
expect: unchanged
```

```check
sql: SELECT Name FROM t_diagram WHERE Diagram_ID IN (8, 10) ORDER BY Diagram_ID
expect: unchanged
```

**Fails when:** Only `t_package` is fixed and the mirror object keeps the encoded name, or the run
renames the two encoded diagrams as well and widens the change past the request.

### TC-13: Creates a governed application with its tags

Covers: 4. Element Creation and Tagged Values

**Marks:** WRITE, INVARIANT

**Ask:** "Add a new payments application called Card Disputes to Domestic Payments. It's mission-critical and strategic, the business side is Payments Operations and the technical side is Payments Engineering, the data is confidential and it falls under PCI-DSS."

**Passes when:** One Component carrying the business-application stereotype exists in Domestic
Payments, bound to the technology, with all six tags set to the stated values.

**Check:**

```check
sql: SELECT o.Object_Type FROM t_object o JOIN t_package p ON o.Package_ID = p.Package_ID WHERE o.Name = 'Card Disputes' AND o.Stereotype = 'WBABusinessApplication' AND p.Name = 'Domestic Payments'
expect: rows: [["Component"]]
```

```check
sql: SELECT tp.Property, tp.Value FROM t_objectproperties tp JOIN t_object o ON tp.Object_ID = o.Object_ID WHERE o.Name = 'Card Disputes' AND tp.Property IN ('criticality', 'lifecycle', 'businessOwner', 'technicalOwner', 'dataClassification', 'regulatoryScope') ORDER BY tp.Property
expect: rows: [["businessOwner", "Payments Operations"], ["criticality", "Mission-Critical"], ["dataClassification", "Confidential"], ["lifecycle", "Strategic"], ["regulatoryScope", "PCI-DSS"], ["technicalOwner", "Payments Engineering"]]
```

```check
sql: SELECT COUNT(*) FROM t_xref x JOIN t_object o ON o.ea_guid = x.Client WHERE o.Name = 'Card Disputes' AND x.Description LIKE '%FQName=%::WBABusinessApplication;%'
expect: = 1
```

```check
sql: SELECT COUNT(*) FROM t_object WHERE Name = 'Card Disputes'
expect: = 1
```

**Fails when:** The element is created without tags because the language-aware create call
rejected a `tagged_values` argument and the run gave up on tagging, or a tag value is written as
`Mission Critical`. The element exists and is the right stereotype, so a look at the browser
shows nothing wrong.

### TC-14: An AI model is created as a Class

Covers: 4. Element Creation and Tagged Values

**Marks:** WRITE, INVARIANT

**Ask:** "Add an AI model called Dispute Triage Model to the AI Platform package. It's experimental, a human has to review its output, audit logging is on, and its data residency is US-only."

**Passes when:** The element is a Class, not a Component, carries the AI-model stereotype bound to
the technology, and the four AI tags hold the stated values.

**Check:**

```check
sql: SELECT o.Object_Type FROM t_object o JOIN t_package p ON o.Package_ID = p.Package_ID WHERE o.Name = 'Dispute Triage Model' AND o.Stereotype = 'WBAAIModel' AND p.Name = 'AI Platform'
expect: rows: [["Class"]]
```

```check
sql: SELECT tp.Property, tp.Value FROM t_objectproperties tp JOIN t_object o ON tp.Object_ID = o.Object_ID WHERE o.Name = 'Dispute Triage Model' AND tp.Property IN ('modelGovernanceClass', 'humanInLoopRequired', 'auditLoggingEnabled', 'dataResidency') ORDER BY tp.Property
expect: rows: [["auditLoggingEnabled", "true"], ["dataResidency", "US-only"], ["humanInLoopRequired", "true"], ["modelGovernanceClass", "Experimental"]]
```

```check
sql: SELECT COUNT(*) FROM t_xref x JOIN t_object o ON o.ea_guid = x.Client WHERE o.Name = 'Dispute Triage Model' AND x.Description LIKE '%FQName=%::WBAAIModel;%'
expect: = 1
```

**Fails when:** The element is created as a Component because the run supplied the base type
itself. EA may keep the stereotype text on it, nothing errors, and the toolbox never offers it.

### TC-15: A plain UML class uses the plain create call

Covers: 4. Element Creation and Tagged Values

**Marks:** WRITE

**Ask:** "Add a plain UML class called Dispute Case to the Data Architecture package."

**Passes when:** A Class with no stereotype exists in Data Architecture, created through the
generic element call.

**Check:**

```check
sql: SELECT o.Object_Type, COALESCE(o.Stereotype, '') FROM t_object o JOIN t_package p ON p.Package_ID = o.Package_ID WHERE o.Name = 'Dispute Case' AND p.Name = 'Data Architecture'
expect: rows: [["Class", ""]]
```

```check
tools: called: ea_model.create_element
```

**Fails when:** The class is given a stereotype from the technology that the customer did not ask
for.

### TC-16: Adds an attribute, an operation and a parameter

Covers: 4. Element Creation and Tagged Values

**Marks:** WRITE

**Ask:** "On the Customer entity in the Data Model package, add an attribute called riskTier, a String that defaults to STANDARD, and an operation called recalculateRisk that returns a Boolean and takes a Boolean parameter called force that defaults to false."

**Passes when:** The attribute, the operation, and the parameter exist with their types and
defaults, and the entity's existing attributes and operations are untouched.

**Check:**

```check
sql: SELECT [Type], [Default] FROM t_attribute WHERE Object_ID = 33568 AND Name = 'riskTier'
expect: rows: [["String", "STANDARD"]]
```

```check
sql: SELECT [Type] FROM t_operation WHERE Object_ID = 33568 AND Name = 'recalculateRisk'
expect: rows: [["Boolean"]]
```

```check
sql: SELECT p.Name, p.[Type], p.[Default] FROM t_operationparams p JOIN t_operation o ON o.OperationID = p.OperationID WHERE o.Object_ID = 33568 AND o.Name = 'recalculateRisk'
expect: rows: [["force", "Boolean", "false"]]
```

```check
sql: SELECT (SELECT COUNT(*) FROM t_attribute WHERE Object_ID = 33568 AND Name <> 'riskTier'), (SELECT COUNT(*) FROM t_operation WHERE Object_ID = 33568 AND Name <> 'recalculateRisk')
expect: rows: [[6, 2]]
```

**Fails when:** The parameter is missing, or present without its default, while the operation
reports success. Reading back only the response of the create call hides both.

### TC-17: Diagnoses a stereotype that was never bound

Covers: 4.5 Stereotype Persistence — Where EA Stores What

**Setup:** The runner adds `Legacy Intake Hub`, a Component in Account Origination whose
`Stereotype` is `WBABusinessApplication`, with no `t_xref` profile row (the stereotype was typed
in while the technology was not loaded).

**Ask:** "Legacy Intake Hub in Account Origination is labeled as a Business Application, but it doesn't behave like the others: it draws as a plain box and the technology's properties aren't there. What's wrong with it?"

**Passes when:** The run looks for the element's profile application, finds none, and explains
that the stereotype is only a label until the technology's profile is applied. It does not report
the element as correctly bound.

**Check:**

```check
sql: SELECT COUNT(*) FROM t_xref x JOIN t_object o ON o.ea_guid = x.Client WHERE o.Name = 'Legacy Intake Hub'
expect: = 0
```

```check
reply: says: Legacy Intake Hub has no profile application row, so its stereotype is only a label
reply: not: says the element is correctly bound to the technology
```

```check
# the model is unchanged
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

**Fails when:** The run reads the stereotype column, sees `WBABusinessApplication`, and concludes
the element is fine. The label is there and the binding is not.

### TC-18: Repairs an unbound element without losing its tags

Covers: 4.5 Stereotype Persistence — Where EA Stores What

**Marks:** WRITE

**Setup:** As TC-17, and the element also carries `criticality` = `Business-Critical` and
`lifecycle` = `Current`. It has no connectors and is on no diagram.

**Ask:** "Fix Legacy Intake Hub so the modeling technology really recognizes it as a Business Application."

**Passes when:** One element of that name remains, in Account Origination, bound to the
technology, with its two tags still set.

**Check:**

```check
sql: SELECT COUNT(*) FROM t_object WHERE Name = 'Legacy Intake Hub'
expect: = 1
```

```check
sql: SELECT o.Object_Type FROM t_object o JOIN t_package p ON p.Package_ID = o.Package_ID WHERE o.Name = 'Legacy Intake Hub' AND p.Name = 'Account Origination' AND o.Stereotype = 'WBABusinessApplication'
expect: rows: [["Component"]]
```

```check
sql: SELECT COUNT(*) FROM t_xref x JOIN t_object o ON o.ea_guid = x.Client WHERE o.Name = 'Legacy Intake Hub' AND x.Description LIKE '%FQName=%::WBABusinessApplication;%'
expect: = 1
```

```check
sql: SELECT tp.Property, tp.Value FROM t_objectproperties tp JOIN t_object o ON o.Object_ID = tp.Object_ID WHERE o.Name = 'Legacy Intake Hub' AND tp.Property IN ('criticality', 'lifecycle') ORDER BY tp.Property
expect: rows: [["criticality", "Business-Critical"], ["lifecycle", "Current"]]
```

**Fails when:** The run recreates the element and the new one has no tags, or the old one is left
beside the new one. Both leave an element that is bound and wrong.

### TC-19: Creates a diagram of the technology's type

Covers: 5. Creating Diagrams with MDG Types

**Marks:** WRITE

**Ask:** "Create an ArchiMate application diagram called Card Services Landscape in Card Services."

**Passes when:** One diagram of that name exists in Card Services with the base type and the
ArchiMate application style set, so it opens with the right toolbox.

**Check:**

```check
sql: SELECT g.Diagram_Type, CASE WHEN g.StyleEx LIKE '%MDGDgm=ArchiMate3::Application;%' THEN 1 ELSE 0 END FROM t_diagram g JOIN t_package p ON p.Package_ID = g.Package_ID WHERE g.Name = 'Card Services Landscape' AND p.Name = 'Card Services'
expect: rows: [["Logical", 1]]
```

**Fails when:** The diagram is a plain Logical diagram with no style, or the run passed the full
`ArchiMate3::Application` string as the base type. The diagram exists, opens, and offers the wrong
palette.

### TC-20: Refuses a layout style that does not exist

Covers: 6. Diagram Layout

**Marks:** WRITE

**Ask:** "Re-lay out the Technology Layer diagram using the Digraph layout."

**Passes when:** The run says Digraph is not a layout it offers, names the four it does, and
either applies one of the four with that stated or asks which to use. It does not claim to have
applied a Digraph layout. All 15 placed elements are still on the diagram.

**Check:**

```check
sql: SELECT COUNT(*) FROM t_diagramobjects d JOIN t_diagram g ON g.Diagram_ID = d.Diagram_ID WHERE g.Name = 'Technology Layer'
expect: = 15
```

```check
reply: says: Digraph is not a supported layout style
reply: says: the supported styles are Orthogonal, Hierarchical, Circular and Sequence
reply: not: says a Digraph layout was applied
```

**Fails when:** The run reports the Digraph layout as applied after the server fell back to
another style, or retries the same invalid name expecting the old silent fallback.

### TC-21: Coordinates the customer gives are kept

Covers: 6. Diagram Layout

**Marks:** WRITE

**Ask:** "On the Payments Integration Architecture diagram, put Westbrook Wire Transfer Service in the top-left and ACH Origination Service exactly 300 pixels to its right, on the same line."

**Passes when:** Both elements are on the diagram, and the second sits 300 pixels right of the
first with the same top edge. No automatic layout moved them.

**Check:**

```check
sql: SELECT b.RectLeft - a.RectLeft, b.RectTop - a.RectTop FROM t_diagramobjects a JOIN t_diagramobjects b ON b.Diagram_ID = a.Diagram_ID JOIN t_object oa ON oa.Object_ID = a.Object_ID JOIN t_object ob ON ob.Object_ID = b.Object_ID WHERE a.Diagram_ID = 17 AND oa.Name = 'Westbrook Wire Transfer Service' AND ob.Name = 'ACH Origination Service'
expect: rows: [[300, 0]]
```

```check
sql: SELECT COUNT(*) FROM t_diagramobjects WHERE Diagram_ID = 17
expect: = 2
```

**Fails when:** The coordinates are passed at the wrong level of the call and ignored or refused,
and the run falls back to an automatic layout. The elements are on the diagram, in positions
nobody chose.

### TC-22: A missing line is traced to a missing endpoint

Covers: 6.5 Connector Rendering and t_diagramlinks

**Marks:** WRITE

**Setup:** The runner removes the placement of Westbrook Account Master from the Account
Management Landscape diagram. Its connectors from other placed elements stay in the model.

**Ask:** "On the Account Management Landscape diagram the lines into Westbrook Account Master have disappeared. Can you get them back?"

**Passes when:** The run finds that Westbrook Account Master is no longer on the diagram, places
it again, and says that was the cause. It does not re-add link rows to restore lines.

**Check:**

```check
sql: SELECT COUNT(*) FROM t_diagramobjects d JOIN t_object o ON o.Object_ID = d.Object_ID WHERE d.Diagram_ID = 7 AND o.Name = 'Westbrook Account Master'
expect: = 1
```

```check
sql: SELECT COUNT(*) FROM t_connector c JOIN t_object e ON e.Object_ID = c.End_Object_ID WHERE e.Name = 'Westbrook Account Master' AND c.Stereotype = 'Uses'
expect: = 3
```

```check
# no new elements, connectors, diagrams, packages or tags
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

```check
reply: says: Westbrook Account Master was not placed on the diagram
tools: not-called: ea_diagram.add_connectors_to_diagram_bulk
```

**Fails when:** The run calls the link-restoring operation, reports the lines restored, and the
element is still off the diagram. The call returns `ok`, and the lines are still missing.

### TC-23: No link rows does not mean hidden lines

Covers: 6.5 Connector Rendering and t_diagramlinks

**Ask:** "I looked in the diagram-links table for the Account Management Landscape diagram and there's nothing in it. Does that mean its relationship lines aren't being shown, and do I need to add rows?"

**Passes when:** The run checks and answers no: EA draws a connector between two placed elements
with or without a stored row, the row only carries styling such as route, color and the hidden
flag, and nothing needs adding.

**Check:**

```check
sql: SELECT COUNT(*) FROM t_diagramlinks l JOIN t_diagram g ON g.Diagram_ID = l.DiagramID WHERE g.Name = 'Account Management Landscape'
expect: unchanged
```

```check
reply: says: a connector between two placed elements is drawn whether or not a stored link row exists
reply: says: the stored row carries presentation such as route, color and the hidden flag
reply: not: says rows must be added for the lines to appear
tools: not-called: ea_diagram.add_connectors_to_diagram_bulk
```

```check
# the model is unchanged
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

**Fails when:** The run agrees that the empty table explains missing lines and writes rows. The
diagram in this model has five connectors drawn and no rows behind them.

### TC-24: A new diagram gets a note about its contents

Covers: 6.7 Diagram Notes — Make Every Diagram Self-Documenting

**Marks:** WRITE

**Ask:** "Create an ArchiMate application diagram called Domestic Payments Landscape in Domestic Payments with everything in that package on it."

**Passes when:** The diagram holds the seven elements of the package and has a note of a full
sentence that names at least one element on it.

**Check:**

```check
sql: SELECT COUNT(*) FROM t_diagramobjects d JOIN t_diagram g ON g.Diagram_ID = d.Diagram_ID WHERE g.Name = 'Domestic Payments Landscape'
expect: = 7
```

```check
sql: SELECT COUNT(*) FROM t_diagram g WHERE g.Name = 'Domestic Payments Landscape' AND LENGTH(COALESCE(g.Notes, '')) >= 40
expect: = 1
```

```check
sql: SELECT COUNT(*) FROM t_diagram g JOIN t_diagramobjects d ON d.Diagram_ID = g.Diagram_ID JOIN t_object o ON o.Object_ID = d.Object_ID WHERE g.Name = 'Domestic Payments Landscape' AND g.Notes LIKE '%' || o.Name || '%'
expect: >= 1
```

**Fails when:** The note is empty, or generic enough to have been written before any element was
placed ("Component diagram in package Domestic Payments"). Both look documented in the browser
and say nothing.

### TC-25: Renaming a diagram keeps its note

Covers: 6.7 Diagram Notes — Make Every Diagram Self-Documenting

**Marks:** WRITE

**Ask:** "Rename the AI Platform Architecture diagram to AI Platform Overview."

**Passes when:** The name changes and the note is exactly as it was.

**Check:**

```check
sql: SELECT Name FROM t_diagram WHERE Diagram_ID = 5587
expect: rows: [["AI Platform Overview"]]
```

```check
sql: SELECT Notes FROM t_diagram WHERE Diagram_ID = 5587
expect: unchanged
```

**Fails when:** The update clears or rewrites the note because the call included the notes key
the customer never mentioned.

### TC-26: A uses relationship points from the consumer to the provider

Covers: 7. Connectors

**Marks:** WRITE, INVARIANT

**Ask:** "Record that the Westbrook Card Management Platform uses the Westbrook Payment Network Gateway."

**Passes when:** One association stereotyped `Uses` runs from the Card Management Platform to
the Payment Network Gateway, and none runs the other way.

**Check:**

```check
sql: SELECT c.Connector_Type, c.Stereotype FROM t_connector c JOIN t_object s ON s.Object_ID = c.Start_Object_ID JOIN t_object e ON e.Object_ID = c.End_Object_ID WHERE s.Name = 'Westbrook Card Management Platform' AND e.Name = 'Westbrook Payment Network Gateway'
expect: rows: [["Association", "Uses"]]
```

```check
sql: SELECT COUNT(*) FROM t_connector c JOIN t_object s ON s.Object_ID = c.Start_Object_ID JOIN t_object e ON e.Object_ID = c.End_Object_ID WHERE s.Name = 'Westbrook Payment Network Gateway' AND e.Name = 'Westbrook Card Management Platform'
expect: = 0
```

**Fails when:** The ends are reversed, so the model says the gateway uses the card platform. The
line draws, the stereotype is right, and every impact query run from either end is wrong.

### TC-27: A realizes relationship maps to the realization type

Covers: 7. Connectors

**Marks:** WRITE

**Ask:** "Record that the Westbrook Wire Transfer Service realizes the Payment Processing Service."

**Passes when:** One realization connector from the Wire Transfer Service to the Payment
Processing Service exists, stereotyped `realizes` (the case of the letters is not part of this
check), of the connector type EA stores for realizations.

**Check:**

```check
sql: SELECT c.Connector_Type, LOWER(COALESCE(c.Stereotype, '')) FROM t_connector c JOIN t_object s ON s.Object_ID = c.Start_Object_ID JOIN t_object e ON e.Object_ID = c.End_Object_ID WHERE s.Name = 'Westbrook Wire Transfer Service' AND e.Name = 'Payment Processing Service'
expect: rows: [["Realisation", "realizes"]]
```

**Fails when:** The connector is a plain association or dependency, or runs from the service to
the application.

### TC-28: A deliberate link to a deprecated element stays unflagged

Covers: 7. Connectors

**Marks:** WRITE, INVARIANT

**Ask:** "The Westbrook Customer Profile Service still depends on the Salesforce Legacy Data Export Feed, which is deprecated. Record the link so it's traceable, but I don't want it flagged as a governance violation."

**Passes when:** One unstereotyped association or dependency runs from the Customer Profile
Service to the Legacy Feed. The lifecycle rule query finds nothing for that source. The reply says
why the link was made without a stereotype.

**Check:**

```check
sql: SELECT COUNT(*) FROM t_connector c JOIN t_object s ON s.Object_ID = c.Start_Object_ID JOIN t_object e ON e.Object_ID = c.End_Object_ID WHERE s.Name = 'Westbrook Customer Profile Service' AND e.Name = 'Salesforce Legacy Data Export Feed' AND c.Connector_Type IN ('Association', 'Dependency') AND COALESCE(c.Stereotype, '') = ''
expect: = 1
```

```check
sql: SELECT COUNT(*) FROM t_connector c JOIN t_object src ON src.Object_ID = c.Start_Object_ID JOIN t_object tgt ON tgt.Object_ID = c.End_Object_ID JOIN t_objectproperties sl ON sl.Object_ID = src.Object_ID AND sl.Property = 'lifecycle' JOIN t_objectproperties tl ON tl.Object_ID = tgt.Object_ID AND tl.Property = 'lifecycle' WHERE c.Stereotype IN ('Uses', 'ConsumesService', 'Realizes', 'Flows') AND sl.Value IN ('Strategic', 'Current') AND tl.Value = 'Deprecated' AND src.Name = 'Westbrook Customer Profile Service'
expect: = 0
```

```check
reply: says: a link with no stereotype is not flagged by the lifecycle rule
```

**Fails when:** The run defaults to `Uses`, the link is flagged the next time the lifecycle rule
runs, and the customer's explicit instruction is lost. The connector is correct in every other
respect.

### TC-29: Stops when a connector endpoint does not exist

Covers: 7. Connectors

**Marks:** REFUSE

**Ask:** "Connect the Westbrook Wire Transfer Service to the Wire Fraud Screening Engine. It uses it."

**Passes when:** The run checks both ends, finds no element called Wire Fraud Screening Engine,
and says so, perhaps naming close matches. It creates no connector and no element.

**Check:**

```check
sql: SELECT COUNT(*) FROM t_object WHERE Name = 'Wire Fraud Screening Engine'
expect: = 0
```

```check
reply: says: no element named Wire Fraud Screening Engine exists
reply: not: says the connector was created
```

```check
# the model is unchanged
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

**Fails when:** The run creates the missing element to make the connector possible, or creates a
connector to the nearest name.

### TC-30: A shared service goes above the areas that use it

Covers: 8. Element Placement and Package Tree Counts

**Marks:** WRITE

**Ask:** "Add a shared Customer Notification Service that the Domestic Payments, Card Services and Lending teams all use."

**Passes when:** The element exists once, and it sits in a package that is not inside any single
capability area under Consumer Banking (not in Domestic Payments, Card Services or any other
sub-package of those areas). The run explains the choice.

**Check:**

```check
sql: SELECT COUNT(*) FROM t_object WHERE Name = 'Customer Notification Service'
expect: = 1
```

```check
sql: SELECT COUNT(*) FROM t_object o JOIN t_package p ON p.Package_ID = o.Package_ID WHERE o.Name = 'Customer Notification Service' AND p.Package_ID NOT IN (SELECT Package_ID FROM t_package WHERE Parent_ID = (SELECT Package_ID FROM t_package WHERE Name = 'Consumer Banking')) AND p.Parent_ID NOT IN (SELECT Package_ID FROM t_package WHERE Parent_ID = (SELECT Package_ID FROM t_package WHERE Name = 'Consumer Banking'))
expect: = 1
```

**Fails when:** The service is filed under Domestic Payments because that was the first area
named. It inflates that area's counts and every ancestor's, and nothing reports it.

### TC-31: A subtree count follows every level and counts elements only

Covers: 8. Element Placement and Package Tree Counts; 9. Verification Queries

**Marks:** INVARIANT

**Ask:** "How many elements are in the 05 Census Coverage package, including everything nested below it?"

**Passes when:** The run reports 27 elements, having followed the package tree to its full depth
of 13 packages and excluded the packages themselves.

**Check:**

```check
sql: SELECT COUNT(*) FROM t_object WHERE Object_Type <> 'Package' AND Package_ID IN (10419, 10420, 10421, 10422, 10423, 10424, 10425, 10426, 10427, 10428, 10429, 10430, 10431)
expect: = 27
```

```check
reply: says: there are 27 elements in the 05 Census Coverage package and everything below it
reply: not: says there are 33 elements
reply: not: says there are 39 elements
```

```check
# the model is unchanged
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

**Fails when:** The run uses a query nested three levels deep and reports 33, because the chain
of probe packages runs eight levels, or it counts every object row and reports 39, because each
child package has a mirror row in its parent. Both numbers are confident and neither is an error.

### TC-32: Declines an AI tag on a non-AI application

Covers: 10. Working with an MDG technology

**Marks:** REFUSE, INVARIANT

**Ask:** "Mark the Westbrook Wire Transfer Service as human-in-the-loop required and give it a model governance class of Tier 1."

**Passes when:** The run says those tags belong to the AI stereotypes only, that the Wire Transfer
Service is a business application, and sets neither tag. It may offer what would fit (changing the
element's kind if it really is an AI service).

**Check:**

```check
sql: SELECT COUNT(*) FROM t_objectproperties p JOIN t_object o ON o.Object_ID = p.Object_ID WHERE o.Name = 'Westbrook Wire Transfer Service' AND p.Property IN ('humanInLoopRequired', 'modelGovernanceClass')
expect: = 0
```

```check
reply: says: those tags apply only to the AI stereotypes
reply: not: says the tags were set on the Westbrook Wire Transfer Service
```

```check
# the model is unchanged
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

**Fails when:** EA accepts a free tag of any name, so the run sets both and reports success. The
element now carries tags its technology never declared, and the next conformance check flags it.

### TC-33: Stops when the technology is not live

Covers: 10. Working with an MDG technology

**Marks:** BLOCKED, REFUSE

Blocked: needs a disposable Windows profile. Disabling a technology in Manage Technologies is a
per-user EA setting. The runner provides the profile and restores the setting afterwards.

**Setup:** The `WBA` technology is registered but not enabled in EA.

**Ask:** "Add a business application called Wire Transfer Status API to Domestic Payments. It's business-critical and the business owner is Payments Operations."

**Passes when:** The run asks the runtime whether the technology is loaded, gets a not-live
answer, and stops. It tells the customer to deploy or enable the technology first and creates
nothing.

**Check:**

```check
tools: called: ea_mdg.get_mdg_from_runtime
```

```check
sql: SELECT COUNT(*) FROM t_object WHERE Name = 'Wire Transfer Status API'
expect: = 0
```

```check
reply: says: the technology is registered but not enabled
reply: says: it has to be deployed or enabled before the element can be tagged
```

```check
# the model is unchanged
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

**Fails when:** The run creates an untagged or half-tagged element anyway. The label is on it
and the technology never saw it.

### TC-34: Confirms the technology is loaded before tagging

Covers: 10. Working with an MDG technology

**Marks:** WRITE

**Ask:** "Add a business application called Dispute Evidence Vault to Domestic Payments, business-critical and current."

**Passes when:** The run confirms the technology is live through the runtime before it tags,
then creates the element with both tags.

**Check:**

```check
tools: called: ea_mdg.get_mdg_from_runtime
```

```check
sql: SELECT tp.Property, tp.Value FROM t_objectproperties tp JOIN t_object o ON o.Object_ID = tp.Object_ID JOIN t_package p ON p.Package_ID = o.Package_ID WHERE o.Name = 'Dispute Evidence Vault' AND o.Stereotype = 'WBABusinessApplication' AND p.Name = 'Domestic Payments' AND tp.Property IN ('criticality', 'lifecycle') ORDER BY tp.Property
expect: rows: [["criticality", "Business-Critical"], ["lifecycle", "Current"]]
```

**Fails when:** The run tags without checking, which works on a healthy model and fails silently
on one where the technology is registered but off.

### TC-35: A bulk load with overlap creates only what is missing

Covers: 11. Idempotency — Check Before Creating

**Marks:** WRITE, INVARIANT

**Ask:** "Make sure Domestic Payments has these four business applications: ACH Origination Service, ACH Return Handler, Faster Payments Gateway and Payment Return Reconciler. Make the new ones business-critical and current."

**Passes when:** Each of the four exists exactly once in Domestic Payments. The two that already
existed keep their original ids and tags, and the two new ones get the stated tags.

**Check:**

```check
sql: SELECT Name, COUNT(*) FROM t_object WHERE Name IN ('ACH Origination Service', 'ACH Return Handler', 'Faster Payments Gateway', 'Payment Return Reconciler') GROUP BY Name ORDER BY Name
expect: rows: [["ACH Origination Service", 1], ["ACH Return Handler", 1], ["Faster Payments Gateway", 1], ["Payment Return Reconciler", 1]]
```

```check
sql: SELECT o.Name, tp.Property, tp.Value FROM t_object o JOIN t_objectproperties tp ON tp.Object_ID = o.Object_ID WHERE o.Name IN ('ACH Origination Service', 'ACH Return Handler') ORDER BY o.Name, tp.Property
expect: unchanged
```

```check
sql: SELECT COUNT(*) FROM t_objectproperties tp JOIN t_object o ON o.Object_ID = tp.Object_ID WHERE o.Name IN ('Faster Payments Gateway', 'Payment Return Reconciler') AND ((tp.Property = 'criticality' AND tp.Value = 'Business-Critical') OR (tp.Property = 'lifecycle' AND tp.Value = 'Current'))
expect: = 4
```

**Fails when:** The two existing applications are created again, giving two elements with one name
that every later query double counts, or their tags are overwritten with the new ones.

### TC-36: Asking for an existing package creates no copy

Covers: 11. Idempotency — Check Before Creating

**Marks:** WRITE

**Ask:** "Create a package called Domestic Payments inside Transactions & Payments."

**Passes when:** The run finds the package already exists, reports its id, and creates nothing.

**Check:**

```check
sql: SELECT COUNT(*) FROM t_package WHERE Name = 'Domestic Payments'
expect: = 1
```

```check
# no new elements, connectors, diagrams, packages or tags
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

```check
reply: says: Domestic Payments already exists and nothing was created
```

**Fails when:** A second package of the same name appears beside the first.

### TC-37: Resumes an interrupted build

Covers: 12. Error Recovery Patterns

**Marks:** WRITE

**Setup:** Chargeback Intake Service, Chargeback Rules Engine and Chargeback Evidence Vault already
exist in Card Services as business applications, business-critical and current.

**Ask:** "Earlier today a session was loading six Chargeback services into Card Services and died partway. The six are Chargeback Intake Service, Chargeback Rules Engine, Chargeback Evidence Vault, Chargeback Reporting Hub, Chargeback Notification Service and Chargeback Case Manager, all business applications, business-critical and current. Finish the job."

**Passes when:** All six exist exactly once with both tags, and the three that already existed are
the same elements as before, not deleted and rebuilt.

**Check:**

```check
sql: SELECT COUNT(*) FROM t_object o JOIN t_package p ON p.Package_ID = o.Package_ID WHERE p.Name = 'Card Services' AND o.Stereotype = 'WBABusinessApplication' AND o.Name IN ('Chargeback Intake Service', 'Chargeback Rules Engine', 'Chargeback Evidence Vault', 'Chargeback Reporting Hub', 'Chargeback Notification Service', 'Chargeback Case Manager')
expect: = 6
```

```check
sql: SELECT COUNT(*) FROM t_object WHERE Name IN ('Chargeback Intake Service', 'Chargeback Rules Engine', 'Chargeback Evidence Vault', 'Chargeback Reporting Hub', 'Chargeback Notification Service', 'Chargeback Case Manager')
expect: = 6
```

```check
sql: SELECT Name, ea_guid FROM t_object WHERE Name IN ('Chargeback Intake Service', 'Chargeback Rules Engine', 'Chargeback Evidence Vault') ORDER BY Name
expect: unchanged
```

```check
sql: SELECT COUNT(*) FROM t_objectproperties tp JOIN t_object o ON o.Object_ID = tp.Object_ID WHERE o.Name IN ('Chargeback Intake Service', 'Chargeback Rules Engine', 'Chargeback Evidence Vault', 'Chargeback Reporting Hub', 'Chargeback Notification Service', 'Chargeback Case Manager') AND ((tp.Property = 'criticality' AND tp.Value = 'Business-Critical') OR (tp.Property = 'lifecycle' AND tp.Value = 'Current'))
expect: = 12
```

**Fails when:** The run rebuilds all six from the top, leaving duplicates, or deletes the three
survivors first. The guid check catches the second even when the final names and counts look right.

### TC-38: A wrong name is corrected in place

Covers: 12. Error Recovery Patterns

**Marks:** WRITE

**Ask:** "The element called Westbrook Check Processing Hub is misnamed. It should be called Westbrook Check Clearing Hub."

**Passes when:** The same element carries the new name, keeping its id, guid and six tags.

**Check:**

```check
sql: SELECT Name FROM t_object WHERE Object_ID = 102
expect: rows: [["Westbrook Check Clearing Hub"]]
```

```check
sql: SELECT ea_guid FROM t_object WHERE Object_ID = 102
expect: unchanged
```

```check
sql: SELECT COUNT(*) FROM t_objectproperties WHERE Object_ID = 102
expect: = 6
```

```check
# no new elements, connectors, diagrams, packages or tags
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

**Fails when:** The run deletes the element and creates a new one with the corrected name. The
name is right, the guid is new, and the element's tags, connectors and placements are gone.

### TC-39: Moving a package keeps both records in step

Covers: 12. Error Recovery Patterns

**Marks:** WRITE, INVARIANT

**Ask:** "The Treasury Services package is filed under Transactions & Payments, but it belongs under Treasury Management in Operations & Support. Move it there with everything in it."

**Passes when:** The package's parent is Treasury Management, the object that mirrors it in the
browser sits in Treasury Management too, and the package's contents are as they were.

**Check:**

```check
sql: SELECT COUNT(*) FROM t_package c JOIN t_package p ON p.Package_ID = c.Parent_ID WHERE c.Name = 'Treasury Services' AND p.Name = 'Treasury Management'
expect: = 1
```

```check
sql: SELECT COUNT(*) FROM t_object m JOIN t_package p ON p.Package_ID = m.Package_ID WHERE m.Object_Type = 'Package' AND m.Name = 'Treasury Services' AND p.Name = 'Treasury Management'
expect: = 1
```

```check
sql: SELECT COUNT(*) FROM t_object WHERE Package_ID = 27
expect: unchanged
```

```check
# no new elements, connectors, diagrams, packages or tags
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

**Fails when:** Only the package row is updated. The browser tree and queries that join through
the mirror object then disagree about where the package is, and nothing reports it.

### TC-40: Verifies a build with one query

Covers: 9. Verification Queries; 15. Token Economy and Session Hygiene

**Marks:** WRITE

**Ask:** "Add four services to Card Services: Card Controls Service, Card Alerts Service, Card Replacement Service and Card Limit Service. They're business applications, important and current. Then confirm all four landed."

**Passes when:** All four exist with their tags, and the confirmation comes from a single query
over the four, not a read of each element.

**Check:**

```check
sql: SELECT COUNT(*) FROM t_object o JOIN t_package p ON p.Package_ID = o.Package_ID WHERE p.Name = 'Card Services' AND o.Stereotype = 'WBABusinessApplication' AND o.Name IN ('Card Controls Service', 'Card Alerts Service', 'Card Replacement Service', 'Card Limit Service')
expect: = 4
```

```check
sql: SELECT COUNT(*) FROM t_objectproperties tp JOIN t_object o ON o.Object_ID = tp.Object_ID WHERE o.Name IN ('Card Controls Service', 'Card Alerts Service', 'Card Replacement Service', 'Card Limit Service') AND ((tp.Property = 'criticality' AND tp.Value = 'Important') OR (tp.Property = 'lifecycle' AND tp.Value = 'Current'))
expect: = 8
```

```check
tools: called: ea_analyze.execute_sql
tools: not-called: ea_model.get_element
```

**Fails when:** The run reads each element back one at a time. The result is right and the cost
is several times higher; a single `get_element` call also fails this check, by design, because
the promise is one batch query.

### TC-41: Uses a summary instead of listing the model

Covers: 15. Token Economy and Session Hygiene

**Ask:** "Give me a quick overview of which stereotypes are used in the model and how many of each."

**Passes when:** The run uses the summary operation, not a package-by-package listing, and
reports 46 business applications and 35 vendor systems among the counts.

**Check:**

```check
tools: called: ea_analyze.summarize_stereotype_usage
tools: not-called: ea_model.list_elements_in_package
```

```check
sql: SELECT Stereotype, COUNT(*) FROM t_object WHERE Stereotype IN ('WBABusinessApplication', 'WBAVendorSystem') GROUP BY Stereotype ORDER BY Stereotype
expect: rows: [["WBABusinessApplication", 46], ["WBAVendorSystem", 35]]
```

```check
reply: says: there are 46 WBABusinessApplication elements
reply: says: there are 35 WBAVendorSystem elements
```

```check
# the model is unchanged
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

**Fails when:** The run walks the package tree and lists each one, filling the session with data
nobody asked for, or tallies by hand and misses elements in sub-packages.

### TC-42: Explains how to capture a failure report

Covers: 16. Diagnostics Mode (server v0.3.0+)

**Ask:** "A create call just failed with an 'Object reference not set' error and I want to report it. What do I do?"

**Passes when:** The run tells the customer to stop work, turn on the server's diagnostics
setting, restart, reproduce the failure, find the report in the diagnostics folder, check it for
anything sensitive, and only then send it to the support address. It does not send anything itself.

**Check:**

```check
reply: says: set the EA_MCP_DIAGNOSTICS environment variable to 1 and restart the server
reply: says: reproduce the failing call so a report is written to the diagnostics folder
reply: says: review the report for anything sensitive before emailing it to help@novocircle.com
reply: not: says the report was emailed
```

```check
# the model is unchanged
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

**Fails when:** The run retries the failing call repeatedly, or tells the customer to email the
report without reading it first.

### TC-43: Does not claim a diagram looks right without seeing it

Covers: Verify in EA's UI

**Marks:** WRITE

**Setup:** The run has no way to see EA's screen (no computer-use tools).

**Ask:** "Create an ArchiMate application diagram called Card Services Overview in Card Services with everything in that package on it, and tell me it looks right."

**Passes when:** The diagram exists with the four elements placed. The reply says the run cannot
see the diagram and asks the customer to open it and look, rather than reporting it as checked.

**Check:**

```check
sql: SELECT COUNT(*) FROM t_diagramobjects d JOIN t_diagram g ON g.Diagram_ID = d.Diagram_ID WHERE g.Name = 'Card Services Overview'
expect: = 4
```

```check
reply: says: it could not see the diagram and asks the customer to open it and check the layout
reply: not: says the diagram looks right
reply: not: says the diagram was verified visually
```

**Fails when:** The run reports `ok: true` from the write calls as proof the diagram is readable.
The rows exist, and the elements may overlap, sit off the visible area, or lack styling.

### TC-44: Click-through diagrams go to the navigation skill

Covers: 1. Build Order

**Marks:** REFUSE

**Ask:** "Make the capability map under Consumer Banking click-through. Someone opens the top diagram, double-clicks Lending, gets a diagram of its parts, and so on down."

**Passes when:** The reply says drill-down diagrams over a hierarchy are not plain diagram building
and are the job of the `ea-navigation-diagrams` skill, and hands off to it. The run does not build
ordinary diagrams here and call them click-through. Nothing in the model changes.

**Check:**

```check
reply: says: click-through drill-down diagrams are the job of the ea-navigation-diagrams skill
reply: not: says the click-through diagrams were built
```

```check
tools: not-called: ea_diagram.create_diagram
```

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

**Fails when:** The run creates one flat diagram per package with `create_diagram` and reports the map
as click-through. The diagrams exist and look right, but no element is composite and
`t_diagram.ParentID` is empty, so double-clicking opens nothing.

## Invariants

Cases marked INVARIANT must pass on every run. Each guards a failure that is plausible, silent
and expensive to find later.

- **TC-01, TC-02:** an answer about model state comes from a read in the current turn. A reply
  built from memory or from the user's own account reads identically to one built from the model.
- **TC-11:** an ampersand in a package name is stored as typed. An encoded name breaks every
  lookup by name while the browser displays it correctly.
- **TC-13, TC-14:** an element created for a technology is the technology's metaclass, bound to
  its profile, and tagged. A wrong metaclass or a missing binding leaves a label with no meaning.
- **TC-26, TC-28:** a relationship runs the right way and carries the right stereotype. A
  reversed or wrongly stereotyped connector draws correctly and misleads every query.
- **TC-31:** a recursive count follows every level and counts elements, not package rows.
- **TC-32:** a tag is set only on a stereotype that declares it.
- **TC-35:** a load with overlap creates only what is missing and keeps what exists.
- **TC-39:** moving a package updates both records that place it.

The model-unchanged check does not cover diagram placements, link rows or attributes; the cases
that touch those carry their own checks.

## Headings not covered

- `14. Quick-Reference: Most-Used Tools`: a cheat-sheet of tool names, with no promise beyond what the numbered sections make and the cases above test.
- `Reference files`: an index of links; nothing to do, refuse or warn about.

## Findings

- `references/element_creation.md` section 2, verification query 2, filters `t_xref.[Type] = 'element'`. The model stores `element property` (and `references/sql_schema.md` section 3 says the same), so the documented query returns no rows for every element, bound or not, and would lead a run to conclude no profile was applied.
- `references/element_creation.md` section 2, verification query 1, selects `StereotypeEx` from `t_object`. That column does not exist in the schema (`t_object` has `StyleEx`, not `StereotypeEx`), so the query errors. The "three storage locations" table presents it as a stored column.
- A wrong package parent: `SKILL.md` section 12 and `references/package_and_defects.md` section 5 say to fix it with a raw `UPDATE` through `execute_sql`, and section 1 of that file does the same for the root package. `references/sql_schema.md` section 4 says `execute_sql` blocks mutating SQL; the server's own description says it accepts writes but the outcome depends on EA. The recipe also updates only `t_package`, which breaks the mirror-object invariant that `references/sql_schema.md` section 1 (item 11) tells writers to keep. TC-39 checks the mirror; the recipe as written fails it.
- `references/sql_schema.md` section 7, "Count elements in a package subtree", counts every `t_object` row, so each child package's mirror row is counted as an element, and the nesting stops at three levels. In the fixture's `05 Census Coverage` tree it reports 33 or 39 against a true 27 (TC-31). The note "Extend the IN nesting for deeper trees" does not say how to know the depth.
- `SKILL.md` section 8 says to check the target subtree count "against the expected range before placing". Nothing tells a customer where an expected range comes from; `references/package_and_defects.md` section 3 calls it "the test's expected range". TC-30 tests the placement rule only.
- The standing correction says the qualified stereotype is `WBA::WBABusinessApplication`; the fixture stores `WestbrookBankArchitecture::WBABusinessApplication` as the `FQName` in `t_xref`. The `t_xref` checks here match the prefix with a wildcard so they hold under either.
- `SKILL.md` section 7 and `references/diagrams_and_connectors.md` section 4 give the type `Realization` and stereotype `Realizes`. EA stores the connector type `Realisation` (all 26 realizations in the fixture), the technology declares lowercase `realizes`, and `WBA-LFY-001` compares `Realizes` and `ConsumesService`, which no connector carries. TC-27 uses `LOWER()` on the stereotype so it does not arbitrate; whether the server maps `Realization` to the stored spelling was not verified.
- `references/element_creation.md` maps `WBADataAsset` to `Object` and lists `TechNode`, which is not a stereotype (canon: `WBATechnologyNode`, Node); `references/class-modeling.md` and the canon file say `WBADataAsset` is a Class. The fixture's 12 data assets are stored as `Object`.
- `references/element_creation.md` says the canonical tag set is 10 and that `vendor`, `product` and `pciScopeJustification` are not part of the technology. `SKILL.md` section 10, `references/wba_mdg_reference.md` and the canon file say they are declared on some stereotypes (13 tags in all), and the fixture carries them (`vendor` 40 times).
- `SKILL.md` section 0.5 puts the scripting threshold at over 100 elements and says 30-100 is either route; `references/token_and_session_management.md` says over 50 elements goes to scripting. TC-06 tests the 400-element case, which both agree on.
- `SKILL.md` section 4.5 says to fix an unbound element by recreating it. Recreating loses its tags, connectors and diagram placements, and the skill does not say to carry them across. TC-18 uses an element with tags and no connectors and checks the tags survive.
- Section 3 covers package names only. The fixture also stores diagram names encoded (`Transactions &amp; Payments Landscape`, `Risk &amp; Compliance Landscape`), and nothing in the skill says whether to check those.
- `SKILL.md` section 2 gives no rule for choosing between parent 0 and parent 1 for a new top-level package, and the fixture has roots at both. TC-10 supplies the rule in the ask ("alongside Westbrook Bank").
- `references/package_and_defects.md` section 3 says a recursive CTE is not available in EA's SQLite. SQLite supports `WITH RECURSIVE`; whether the server's validator blocks it was not verified, so the cases use fixed package id lists.
- The section numbering in `SKILL.md` skips 13 (12 is followed by 14). Cosmetic.
- Not checkable here: that write calls were issued one at a time (TC-09 tests the outcome only); that a hang was diagnosed from a dialog; the model-tier, `verbose=False` and `/clear` guidance; the "say it was not re-verified" promise when a read is too expensive; and the 4.5 claim that a row with no `FQName` means the technology was not loaded.
- The proactive offer after a load that created elements with parentage (section 1, Build Order) has no case. It needs a load that surfaces a hierarchy past the thresholds that `ea-navigation-diagrams` sets, and a reply check for the offer; TC-44 covers only the hand-off when the person asks.

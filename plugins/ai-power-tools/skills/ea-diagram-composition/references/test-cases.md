# Acceptance cases: `ea-diagram-composition`

This skill promises that a diagram built from model content reads as deliberate: the notation's
conventions are looked up rather than guessed, the grammar fits the content, the geometry is
computed rather than hand-placed, the result is reloaded and looked at before anyone is told it
is done, and the lint result is reported for what it is. This file is built to catch the failures
that produce a plausible diagram instead of an error: a stale render certified as fresh, a box
widened or kept narrow without asking, a layer color repurposed, a "clean" report that never ran
the rule that would have failed.

**Fixture.** A fresh copy of the Westbrook Bank model opened in Enterprise Architect. Westbrook
Bank is our illustration. A customer runs these cases against their own model, substituting their
technology, stereotypes, package and diagram names. Several cases depend on how a technology
resolves to a binding (qualified, inferred, unbound); a customer's own technologies will resolve
differently, and the pass in each case says what to look for rather than which technology wins.

**Marks.** `WRITE` (the run changes the model; it runs only on the copy), `REFUSE` (the pass is a
refusal or a hand-off), `INVARIANT` (must pass on every run). Diagram names in the asks are new
names, so a check can find the diagram the run made.

## Cases

### TC-01: Layered view built from model content

Covers: Step 1 — choose a grammar; Step 2 — compute the geometry; Step 3 — place and style; The loop is the product

**Marks:** WRITE, INVARIANT

**Ask:** "Draw our technology platforms as a new diagram called Platform Layers, in the same notation as the Technology Layer diagram. Put the cloud platforms, the infrastructure, the data and integration platforms and the identity platforms each on their own level, so you can see what sits on what."

**Passes when:** A new diagram named Platform Layers exists and holds all 15 platform nodes. The four packages are four levels, each on its own rows; no layer shares a row with another. Peers in a level are one size, no two boxes overlap, no box has zero or negative size, and no two boxes sit at the same position (the coordinates computed were the coordinates stored). The run ends by saying what it looked at after placing, not just that it placed.

**Check:**

```check
sql: SELECT COUNT(DISTINCT d.Object_ID) FROM t_diagramobjects d JOIN t_diagram g ON d.Diagram_ID = g.Diagram_ID JOIN t_object o ON d.Object_ID = o.Object_ID JOIN t_package p ON o.Package_ID = p.Package_ID WHERE g.Name = 'Platform Layers' AND p.Name IN ('Cloud Platforms', 'Infrastructure', 'Data & Integration Platforms', 'Identity Platforms')
expect: = 15
```

```check
# no layer shares a row with another layer
sql: SELECT COUNT(*) FROM (SELECT d.RectTop FROM t_diagramobjects d JOIN t_diagram g ON d.Diagram_ID = g.Diagram_ID JOIN t_object o ON d.Object_ID = o.Object_ID JOIN t_package p ON o.Package_ID = p.Package_ID WHERE g.Name = 'Platform Layers' AND p.Name IN ('Cloud Platforms', 'Infrastructure', 'Data & Integration Platforms', 'Identity Platforms') GROUP BY d.RectTop HAVING COUNT(DISTINCT p.Package_ID) > 1)
expect: = 0
```

```check
# peers in a level are one size
sql: SELECT COUNT(*) FROM (SELECT p.Package_ID FROM t_diagramobjects d JOIN t_diagram g ON d.Diagram_ID = g.Diagram_ID JOIN t_object o ON d.Object_ID = o.Object_ID JOIN t_package p ON o.Package_ID = p.Package_ID WHERE g.Name = 'Platform Layers' AND p.Name IN ('Cloud Platforms', 'Infrastructure', 'Data & Integration Platforms', 'Identity Platforms') GROUP BY p.Package_ID HAVING COUNT(DISTINCT d.RectRight - d.RectLeft) > 1 OR COUNT(DISTINCT d.RectTop - d.RectBottom) > 1)
expect: = 0
```

```check
# geometry invariant: no two placed boxes overlap unless one contains the other
sql: SELECT COUNT(*) FROM t_diagramobjects a JOIN t_diagramobjects b ON a.Diagram_ID = b.Diagram_ID AND a.Object_ID < b.Object_ID JOIN t_diagram g ON g.Diagram_ID = a.Diagram_ID WHERE g.Name = 'Platform Layers' AND a.RectLeft < b.RectRight AND b.RectLeft < a.RectRight AND a.RectTop > b.RectBottom AND b.RectTop > a.RectBottom AND NOT (a.RectLeft <= b.RectLeft AND a.RectRight >= b.RectRight AND a.RectTop >= b.RectTop AND a.RectBottom <= b.RectBottom) AND NOT (b.RectLeft <= a.RectLeft AND b.RectRight >= a.RectRight AND b.RectTop >= a.RectTop AND b.RectBottom <= a.RectBottom)
expect: = 0
```

```check
# geometry invariant: every box has positive width and height in EA's convention (top > bottom)
sql: SELECT COUNT(*) FROM t_diagramobjects d JOIN t_diagram g ON d.Diagram_ID = g.Diagram_ID WHERE g.Name = 'Platform Layers' AND (d.RectRight <= d.RectLeft OR d.RectTop <= d.RectBottom)
expect: = 0
```

```check
# the coordinates computed were the coordinates stored: no two boxes share a position
sql: SELECT COUNT(*) FROM (SELECT d.RectLeft, d.RectTop FROM t_diagramobjects d JOIN t_diagram g ON d.Diagram_ID = g.Diagram_ID WHERE g.Name = 'Platform Layers' GROUP BY d.RectLeft, d.RectTop HAVING COUNT(*) > 1)
expect: = 0
```

```check
tools: called: ea_diagram.verify_diagram
```

**Fails when:** The boxes are placed with a named layout style, so EA discards the computed coordinates and lays them out as one grid or one pile; the layers lose their rows and the diagram has the right 15 boxes in the wrong arrangement. Or the layers are drawn but two boxes overlap by a few units because the engine's sign convention was reversed. Or the run places the boxes and tells the person it is done without reloading and looking.

### TC-02: A diagram that states its own notation

Covers: Step 0 — resolve the language binding

**Marks:** WRITE

**Ask:** "Add a diagram next to Technology Layer, same notation, showing only the data and integration platforms. Call it Data Platforms View."

**Passes when:** The run reads the existing diagram's stored notation and kind, finds the binding for that notation, and reports that it was found because the diagram states its own type (the exact path). The new diagram is created as the same notation and diagram type, and the boxes take the size that binding records for that diagram type rather than a figure the run chose.

**Check:**

```check
sql: SELECT COUNT(*) FROM t_diagram WHERE Name = 'Data Platforms View' AND StyleEx LIKE '%MDGDgm=ArchiMate3::Technology;%' AND Diagram_Type = 'Logical'
expect: = 1
```

```check
# the binding's measured box for this diagram type is 100 x 70
sql: SELECT COUNT(*) FROM t_diagramobjects d JOIN t_diagram g ON d.Diagram_ID = g.Diagram_ID JOIN t_object o ON d.Object_ID = o.Object_ID JOIN t_package p ON o.Package_ID = p.Package_ID WHERE g.Name = 'Data Platforms View' AND p.Name = 'Data & Integration Platforms' AND ((d.RectRight - d.RectLeft) <> 100 OR (d.RectTop - d.RectBottom) <> 70)
expect: = 0
```

```check
sql: SELECT COUNT(DISTINCT d.Object_ID) FROM t_diagramobjects d JOIN t_diagram g ON d.Diagram_ID = g.Diagram_ID JOIN t_object o ON d.Object_ID = o.Object_ID JOIN t_package p ON o.Package_ID = p.Package_ID WHERE g.Name = 'Data Platforms View' AND p.Name = 'Data & Integration Platforms'
expect: = 6
```

```check
reply: says: the notation's binding was found because the diagram states its own diagram type
```

**Fails when:** The new diagram is created as a plain Logical diagram with no notation stated, so it opens without the toolbox and the next run cannot tell what it is. Or the run composes with a size it chose (the existing diagrams here use 150 x 80) instead of the binding's, and nothing says so.

### TC-03: A diagram that only names its kind

Covers: Step 0 — resolve the language binding

**Marks:** WRITE

**Ask:** "Fill in the Payments Integration Architecture diagram with the Domestic Payments and Card Services applications."

**Passes when:** That diagram states no notation of its own and carries only its kind (Component). The run resolves it from the kind alone, reports that the match was inferred rather than exact, and carries on. The 11 applications end up on the diagram.

**Check:**

```check
sql: SELECT COUNT(DISTINCT d.Object_ID) FROM t_diagramobjects d JOIN t_object o ON d.Object_ID = o.Object_ID JOIN t_package p ON o.Package_ID = p.Package_ID WHERE d.Diagram_ID = 17 AND p.Name IN ('Domestic Payments', 'Card Services')
expect: = 11
```

```check
sql: SELECT COUNT(*) FROM t_diagramobjects a JOIN t_diagramobjects b ON a.Diagram_ID = b.Diagram_ID AND a.Object_ID < b.Object_ID WHERE a.Diagram_ID = 17 AND a.RectLeft < b.RectRight AND b.RectLeft < a.RectRight AND a.RectTop > b.RectBottom AND b.RectTop > a.RectBottom
expect: = 0
```

```check
reply: says: the binding was found from the diagram's kind alone and the confidence is inferred, not exact
```

**Fails when:** The run reports the binding as settled with no confidence stated, or asserts an exact match for a diagram that never named its notation. The quiet version of the same failure is quoting "UML" as if the diagram had said so.

### TC-04: A notation nobody has written conventions for

Covers: Step 0 — resolve the language binding

**Marks:** WRITE

**Ask:** "Build me another diagram like our AI Platform Architecture one, for the Systems of Record. Call it Systems of Record Overview."

**Passes when:** The existing diagram states a Westbrook diagram type (`WBA::WBAApplicationView`). No shipped binding covers it, so the resolver answers unbound (or not-installed, if the technology is not loaded in the copy). The run reports that as a finding, quotes the reason it was given, says it composed with the engine's defaults, and does not borrow another notation's binding to fill the gap. The new diagram still states the same diagram type.

**Check:**

```check
sql: SELECT COUNT(*) FROM t_diagram WHERE Name = 'Systems of Record Overview' AND StyleEx LIKE '%MDGDgm=WBA::WBAApplicationView;%'
expect: = 1
```

```check
sql: SELECT COUNT(DISTINCT d.Object_ID) FROM t_diagramobjects d JOIN t_diagram g ON d.Diagram_ID = g.Diagram_ID WHERE g.Name = 'Systems of Record Overview'
expect: >= 5
```

```check
reply: says: no binding applies to this diagram type and the reason the resolver gave
reply: says: it composed with the engine's defaults instead
reply: not: the ArchiMate3 binding was used for sizing or spacing
```

**Fails when:** The run sees an application view, reaches for the ArchiMate binding because the diagrams look alike, and composes with its sizes and layered bands. Composing against another notation's binding is worse than composing against none, and nothing errors. A quieter failure: the run says nothing about the missing binding at all.

### TC-05: A diagram that looks like one notation and says another

Covers: Step 0 — resolve the language binding

**Marks:** WRITE

**Ask:** "Put everything in the Consumer Lending package on the Consumer Loan Origination Overview diagram."

**Passes when:** That diagram is a business-process diagram to a human, but its stored kind is the technology name (`BPMN2.0`), which is not a diagram type of any binding. The resolver answers unbound. The run reports unbound with the reason, composes with the engine's defaults (choosing the grammar from the content, not from the notation it can see), and does not load the BPMN binding by technology id to get around the answer. The five elements in the Consumer Lending package (two applications, one service, two vendor systems) end up on the diagram.

**Check:**

```check
sql: SELECT COUNT(DISTINCT d.Object_ID) FROM t_diagramobjects d JOIN t_object o ON d.Object_ID = o.Object_ID JOIN t_package p ON o.Package_ID = p.Package_ID WHERE d.Diagram_ID = 16 AND p.Name = 'Consumer Lending'
expect: = 5
```

```check
reply: says: the diagram did not resolve to a binding and quotes the resolver's reason
reply: not: the BPMN2.0 binding was applied
```

**Fails when:** The run calls `find_binding("BPMN2.0")` because the diagram is plainly BPMN, gets a binding, and lays the applications out as lanes at BPMN's box size. `find_binding` checks nothing against what the repository has installed, so the binding comes back, looks right, and was the one the resolver declined to give.

### TC-06: A sequence diagram is not ours to place

Covers: Can this diagram be produced, and who places it?

**Marks:** REFUSE, INVARIANT

**Ask:** "Make a new diagram of the Account Opening interaction with the participants and messages laid out neatly. Call it Account Opening Messages."

**Passes when:** The run says a message-exchange diagram is recorded but not producible here, because its arrangement is dictated by the diagram type (lifeline order and message order), and stops. It writes no coordinates and does not lay the participants out as a free graph. It may offer to open the existing sequence diagram or to have EA arrange it in the editor.

**Check:**

```check
# the model is unchanged
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

```check
sql: SELECT COUNT(*) FROM t_diagramobjects
expect: unchanged
```

```check
tools: not-called: ea_diagram.add_elements_to_diagram_bulk
tools: not-called: ea_diagram.layout_diagram
reply: says: this diagram type is recorded but cannot be produced, because the type itself dictates where things go
```

**Fails when:** The participants are placed on a new diagram with a graph layout, or at coordinates the run computed. All the elements are present and the diagram looks like a sequence diagram, but message order is ignored, which is worse than not generating it. The run following only the numbered steps of the skill is exposed here: see Findings.

### TC-07: A type EA places and we tidy

Covers: Can this diagram be produced, and who places it?

**Marks:** WRITE

**Ask:** "Make me a class diagram of our core data entities and how they relate to each other. Call it Data Entities View."

**Passes when:** The diagram type is one the binding records as laid out by EA. The run treats it as producible, creates the elements, has EA lay it out (using the spacing the binding states), and then tidies: peers one size, one routing style. It does not compute coordinates. The five entities and the three connectors among them are on the diagram.

**Check:**

```check
sql: SELECT COUNT(DISTINCT d.Object_ID) FROM t_diagramobjects d JOIN t_diagram g ON d.Diagram_ID = g.Diagram_ID JOIN t_object o ON d.Object_ID = o.Object_ID WHERE g.Name = 'Data Entities View' AND o.Stereotype = 'WBADataEntity'
expect: = 5
```

```check
sql: SELECT COUNT(*) FROM t_diagramlinks l JOIN t_diagram g ON l.DiagramID = g.Diagram_ID WHERE g.Name = 'Data Entities View'
expect: = 3
```

```check
# peers one size
sql: SELECT COUNT(DISTINCT d.RectRight - d.RectLeft), COUNT(DISTINCT d.RectTop - d.RectBottom) FROM t_diagramobjects d JOIN t_diagram g ON d.Diagram_ID = g.Diagram_ID WHERE g.Name = 'Data Entities View'
expect: rows: [[1, 1]]
```

```check
tools: called: ea_diagram.layout_diagram
tools: called: ea_diagram.verify_diagram
```

**Fails when:** The run reads "no composer for this grammar" as "cannot be produced" and declines, or hand-places five boxes at coordinates it invented. The first is the failure the skill warns about by name: a type EA would have laid out perfectly well is dropped because the engine has no composer for it.

### TC-08: No grammar fits

Covers: Step 1 — choose a grammar

**Marks:** WRITE

**Setup:** Add Dependency connectors from MeridianLink Consumer Lending Platform to Equifax Credit Bureau Gateway, from ICE Encompass Mortgage Platform to Black Knight Property Data Service, and from MeridianLink Consumer Lending Platform to ICE Encompass Mortgage Platform.

**Ask:** "Show how our consumer lending and mortgage vendor systems depend on each other in a diagram called Vendor Links."

**Passes when:** The content is a small dependency network with no strata, no owners, no containment and no center. The run says no composed grammar fits and uses the graph route (EA lays it out), rather than forcing bands. The four vendor systems and the three connectors are on the diagram.

**Check:**

```check
sql: SELECT COUNT(DISTINCT d.Object_ID) FROM t_diagramobjects d JOIN t_diagram g ON d.Diagram_ID = g.Diagram_ID WHERE g.Name = 'Vendor Links'
expect: = 4
```

```check
sql: SELECT COUNT(*) FROM t_diagramlinks l JOIN t_diagram g ON l.DiagramID = g.Diagram_ID WHERE g.Name = 'Vendor Links'
expect: = 3
```

```check
tools: called: ea_diagram.layout_diagram
reply: says: no composed layout fits a dependency network, so EA's layout was used
reply: not: the systems were arranged in layers
```

**Fails when:** The four systems are put in two bands called "Consumer" and "Mortgage" because a band layout was available. It composes, it lints clean, and it implies a layering the content does not have.

### TC-09: Swimlanes for something that is not a flow

Covers: Step 1 — choose a grammar

**Marks:** WRITE

**Ask:** "Draw the Westbrook business areas (Customer Engagement, Account Management, Transactions & Payments and Lending) as swimlanes with their applications inside each lane. Call it Business Area Lanes."

**Passes when:** The run points out that swimlanes need a sequence of steps and an owner for each, and this content has neither: it is a grouping. It proposes (or builds) the honest arrangement, containment, and does not produce a swimlane diagram. If it builds, the diagram is named Business Area Lanes or the run says why it chose another name.

**Check:**

```check
reply: says: swimlanes were not used because the content has no sequence along the lanes
reply: says: the content is a grouping, which suits containment
```

```check
# no lane-style row alignment by sequence: the diagram, if built, is not a single row of equal-height strips
sql: SELECT COUNT(*) FROM t_diagram WHERE Name = 'Business Area Lanes' AND Diagram_Type = 'Analysis'
expect: = 0
```

**Fails when:** Four lanes are drawn with the applications strung along them in arbitrary order. The diagram claims a parallelism and a sequence that are not there, and a reader hunts for the handoffs. A swimlane diagram with no flow is layered bands with the wrong label.

### TC-10: Names the box cannot fit

Covers: Step 2 — compute the geometry

**Marks:** WRITE

**Setup:** In the Domestic Payments package, create three Business Application components (stereotype `WBABusinessApplication`) named `PaymentsInitiationServiceGateway`, `CardAuthorizationOrchestrator` and `WireTransferReconciliationEngine`.

**Ask:** "Put those three new payment applications on a diagram called Payments Gateways."

**Passes when:** No width is stated by the person, so there is no conflict to ask about. The names have no spaces, so EA would grow the drawn box beyond the stored one. The run fits the box to the longest unbroken name (at least 192 wide for the longest here) before composing, uses the same width for all three, and says it widened the box.

**Check:**

```check
sql: SELECT COUNT(*) FROM t_diagramobjects d JOIN t_diagram g ON d.Diagram_ID = g.Diagram_ID WHERE g.Name = 'Payments Gateways' AND (d.RectRight - d.RectLeft) < 192
expect: = 0
```

```check
sql: SELECT COUNT(DISTINCT d.Object_ID), COUNT(DISTINCT d.RectRight - d.RectLeft) FROM t_diagramobjects d JOIN t_diagram g ON d.Diagram_ID = g.Diagram_ID WHERE g.Name = 'Payments Gateways'
expect: rows: [[3, 1]]
```

```check
reply: says: the boxes were widened so each name fits
```

**Fails when:** The three boxes are stored at the notation's convention (100 or so wide). Every check that reads the stored rectangle passes: nothing overlaps, spacing is even. EA draws each box at 170 to 190 wide, so the three sit on top of each other on the canvas. The widths are also not allowed to differ between peers: three different widths is a fix that creates an inconsistent-sizing finding.

### TC-11: A stated width and a longer name

Covers: When the width and the content conflict, ask the user

**Marks:** INVARIANT

**Setup:** The same three components as TC-10.

**Ask:** "Put those three new payment applications on a diagram called Payments Gateways, each box exactly 100 wide."

**Passes when:** The run notices that 100 is narrower than the longest name needs, and puts the question to the person before composing: extend the boxes to fit, or keep 100 wide and let the text run over the border. It places nothing until they answer. The question gives both options and what each does.

**Check:**

```check
# nothing placed on the diagram yet (the diagram itself may exist)
sql: SELECT COUNT(*) FROM t_diagramobjects d JOIN t_diagram g ON d.Diagram_ID = g.Diagram_ID WHERE g.Name = 'Payments Gateways'
expect: = 0
```

```check
reply: says: it asks whether to extend the boxes to fit the names or keep the stated width and let the text overlap
reply: not: it widened the boxes without asking
```

**Fails when:** The run widens to 192 because widening is the safe default, says "adjusted the width so the names fit" and moves on. The conflict was reported and never raised: the old silent behavior with a log line in front of it. Or the reverse, the width is kept and the text overlaps, with no question asked.

### TC-12: Styling a connector that has no stored link

Covers: Step 3 — place and style

**Marks:** WRITE

**Setup:** On the copy before EA opens, delete the stored link row for the connector between Origination Platform and Customer Onboarding Service on the diagram VP Application Cooperation - Onboarding (connector 1486). EA still draws the line; the diagram has four connectors and three stored link rows.

**Ask:** "On the VP Application Cooperation - Onboarding diagram, make all the connector lines dark blue."

**Passes when:** All four connectors end up with a stored link row and a color. The run notices that one of the visible lines has no stored link (instance id 0), adds it to the link layer first, and styles it.

**Check:**

```check
sql: SELECT COUNT(*) FROM t_diagramlinks WHERE DiagramID = 1641 AND Hidden = 0
expect: = 4
```

```check
sql: SELECT COUNT(*) FROM t_diagramlinks WHERE DiagramID = 1641 AND Style LIKE '%Color=-1;%'
expect: = 0
```

**Fails when:** Three lines turn blue and the fourth stays default. The run saw four lines drawn, read "visible" as "styleable", and reported success on a color write that had nothing to write to.

### TC-13: One box, this diagram only

Covers: Which appearance scope you mean

**Marks:** WRITE

**Ask:** "On the Sparx Platform Architecture diagram, make the WebEA box red so it stands out. Only on that diagram."

**Passes when:** The color is set on the placement on that diagram. The element's own default appearance in the model is untouched, so any other diagram holding it is unaffected.

**Check:**

```check
sql: SELECT COUNT(*) FROM t_diagramobjects d JOIN t_diagram g ON d.Diagram_ID = g.Diagram_ID JOIN t_object o ON o.Object_ID = d.Object_ID WHERE g.Name = 'Sparx Platform Architecture' AND o.Name = 'WebEA' AND d.ObjectStyle LIKE '%BCol=%' AND d.ObjectStyle NOT LIKE '%BCol=-1;%'
expect: = 1
```

```check
# the element's model-wide default is untouched
sql: SELECT Backcolor FROM t_object WHERE Name = 'WebEA'
expect: rows: [[-1]]
```

```check
tools: not-called: ea_model.set_element_appearance
```

**Fails when:** The color is written as the element's default appearance. The diagram looks right, and every other diagram that shows the element changes without anyone being told.

### TC-14: A picture taken after the diagram changed elsewhere

Covers: Step 4 — verify; The loop is the product

**Marks:** INVARIANT

**Setup:** After EA has opened and rendered the diagram Lending Landscape once, move one placed element on it 200 units to the right by an out-of-band write to the diagram's stored object rows.

**Ask:** "I changed the Lending Landscape diagram from another session. Show me how it looks now and tell me if it's all right."

**Passes when:** The run uses the verification call that reloads the diagram before rendering, so the picture and the geometry reflect the moved element. The reply describes the diagram as reloaded, and does not describe the previous layout.

**Check:**

```check
tools: called: ea_diagram.verify_diagram
```

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

```check
reply: says: the diagram was reloaded before it was rendered
```

**Fails when:** The run asks for the image without reloading and gets EA's cached render of the layout before the move. It looks entirely plausible, and the run certifies a diagram it never saw.

### TC-15: What color EA actually drew

Covers: Step 4 — verify

**Setup:** On the Sparx Platform Architecture diagram, set a per-placement fill on two of the boxes (WebEA red, Prolaborate green).

**Ask:** "Are the WebEA and Prolaborate boxes on the Sparx Platform Architecture diagram really drawn in the colors I set? Don't just read the setting back."

**Passes when:** The run reads the colors from the rendered output (the SVG markup's fill and stroke values), and reports what EA drew. It says why a read-back of the stored color would not answer the question.

**Check:**

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

```check
tools: called: ea_diagram.verify_diagram
reply: says: the colors were read from the rendered SVG, not from the stored property
reply: says: a color read back from the property only echoes what was written
```

**Fails when:** The run reads the fill property back, finds the number it was set to, and answers yes. EA echoes whatever was written, whether or not it drew with it, so the check passes for a shape whose script paints its own colors.

### TC-16: A tidy-or-not question

Covers: Step 5 — lint, then correct

**Marks:** INVARIANT

**Ask:** "Is the Account Management Landscape diagram tidy? I need a yes or a no I can pass on."

**Passes when:** The run lints the verified diagram with the groupings it knows (the rows and columns of the grid), reads every severity rather than just the errors, and does not collapse the answer to a bare yes. If the report is clean, it says clean means no error the linter can measure and not that the diagram reads well, and names the rules that did not run for lack of a grouping or of the rendered output.

**Check:**

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

```check
tools: called: ea_diagram.verify_diagram
reply: says: clean means no defect the linter knows how to measure, not that the diagram reads well
reply: says: which checks did not run, or ran with nothing to compare
reply: not: the diagram is tidy, full stop
```

**Fails when:** The run declares the diagram tidy because the error list is empty. A rule with no grouping never ran, so its zero is vacuous; a diagram of the wrong grammar lints clean; and the linter cannot see a name running into its own icon.

### TC-17: A correction loop that will not converge

Covers: Step 5 — lint, then correct; The loop is the product

**Marks:** WRITE

**Setup:** Create a diagram called Vendor Dependencies holding ACI Worldwide Payment Engine, MeridianLink Consumer Lending Platform, Equifax Credit Bureau Gateway, ICE Encompass Mortgage Platform and Black Knight Property Data Service, with a Dependency connector between every pair (ten connectors). Five fully connected nodes cannot be drawn without a crossing.

**Ask:** "Keep fixing the Vendor Dependencies diagram until the crossings count is zero. Don't stop before it is."

**Passes when:** The run does not chase zero. It says the crossing count is a measurement that cannot tell a removable crossing from a necessary one, compares it between passes, stops within three correction passes or at the first pass that changes nothing, and reports honestly what is left and what it tried. It may say a diagram this dense wants splitting or filtering. The diagram it leaves has no overlapping boxes.

**Check:**

```check
sql: SELECT COUNT(*) FROM t_diagramobjects a JOIN t_diagramobjects b ON a.Diagram_ID = b.Diagram_ID AND a.Object_ID < b.Object_ID JOIN t_diagram g ON g.Diagram_ID = a.Diagram_ID WHERE g.Name = 'Vendor Dependencies' AND a.RectLeft < b.RectRight AND b.RectLeft < a.RectRight AND a.RectTop > b.RectBottom AND b.RectTop > a.RectBottom
expect: = 0
```

```check
reply: says: it stopped after at most three correction passes, or when a pass changed nothing
reply: says: how many crossings remain
reply: not: the crossings were reduced to zero
```

**Fails when:** The run keeps nudging boxes for an open-ended number of passes, or declares "done" with crossings remaining. A fully connected set of five has a necessary crossing, so a claim of zero is false or was obtained by hiding connectors.

### TC-18: Recoloring a layer-colored notation

Covers: Judgment that scripts cannot encode

**Marks:** WRITE, INVARIANT

**Ask:** "On the Account Management Landscape, color each application by its lifecycle so I can spot the deprecated one."

**Passes when:** The diagram is an ArchiMate application view, where fill already means layer and aspect. The run does not use fill. It uses a free channel (border, line color, opacity or an icon), or asks, and puts a key on the diagram or in the reply saying what each value means. The deprecated application (Salesforce Legacy Data Export Feed) is the one that stands out.

**Check:**

```check
# no fill written on any placement of this diagram
sql: SELECT COUNT(*) FROM t_diagramobjects WHERE Diagram_ID = 7 AND ObjectStyle LIKE '%BCol=%'
expect: = 0
```

```check
reply: says: fill is already used by the notation for layer and aspect
reply: says: which other channel carries lifecycle
reply: says: a key explains what each value means
```

**Fails when:** The boxes are filled red, amber and green. It looks like a feature, destroys the notation's own color meaning, and a reader cannot tell lifecycle from layer. A second version of the failure: the lifecycle colors are applied and there is no legend, so the person has to guess the key.

### TC-19: Two variables, one channel each

Covers: Judgment that scripts cannot encode

**Marks:** WRITE

**Ask:** "On the Account Management Landscape, show lifecycle and criticality at the same time."

**Passes when:** The run assigns one visual channel to each variable and never the same one to both (for example border color for lifecycle and opacity or an icon for criticality), leaves fill alone, and says which channel carries which.

**Check:**

```check
sql: SELECT COUNT(*) FROM t_diagramobjects WHERE Diagram_ID = 7 AND ObjectStyle LIKE '%BCol=%'
expect: = 0
```

```check
reply: says: lifecycle and criticality are shown in two different channels
reply: not: fill carries both variables
```

**Fails when:** Fill encodes lifecycle and, by shade, criticality too. Nobody can decode the diagram, and no legend can rescue it because the mapping itself is ambiguous.

### TC-20: Fit each box to its own name

Covers: Judgment that scripts cannot encode

**Marks:** WRITE

**Ask:** "Draw the data and integration platforms as a new diagram called Compact Data Platforms, with every box only as wide as its own name needs, so it looks compact."

**Passes when:** The run keeps one width for peers and says why: varying box size reads as varying importance. The width is the one needed by the longest name among the peers (or the notation's), not a different width per box.

**Check:**

```check
sql: SELECT COUNT(DISTINCT d.Object_ID), COUNT(DISTINCT d.RectRight - d.RectLeft), COUNT(DISTINCT d.RectTop - d.RectBottom) FROM t_diagramobjects d JOIN t_diagram g ON d.Diagram_ID = g.Diagram_ID JOIN t_object o ON d.Object_ID = o.Object_ID JOIN t_package p ON o.Package_ID = p.Package_ID WHERE g.Name = 'Compact Data Platforms' AND p.Name = 'Data & Integration Platforms'
expect: rows: [[6, 1, 1]]
```

```check
reply: says: boxes in the same role were kept one size, because a different size reads as different importance
```

**Fails when:** Six boxes in six widths, tight to each name. The diagram looks machine-made and a reader asks what the wide ones are for.

### TC-21: Close up the gaps

Covers: Judgment that scripts cannot encode

**Marks:** WRITE

**Ask:** "The Technology Layer diagram has too much white space. Close the gaps up so it fits on half a page."

**Passes when:** The run keeps a consistent gutter between boxes and bands, says that empty space is what tells the reader the boxes are peers, and meets the page limit another way (a smaller scale, a split, or a modest gutter reduction that keeps real whitespace). No two boxes touch or overlap.

**Check:**

```check
# no two boxes touch edge to edge
sql: SELECT COUNT(*) FROM t_diagramobjects a JOIN t_diagramobjects b ON a.Diagram_ID = b.Diagram_ID AND a.Object_ID < b.Object_ID WHERE a.Diagram_ID = 12 AND ((a.RectRight = b.RectLeft OR b.RectRight = a.RectLeft) AND a.RectTop > b.RectBottom AND b.RectTop > a.RectBottom OR (a.RectBottom = b.RectTop OR b.RectBottom = a.RectTop) AND a.RectLeft < b.RectRight AND b.RectLeft < a.RectRight)
expect: = 0
```

```check
sql: SELECT COUNT(*) FROM t_diagramobjects a JOIN t_diagramobjects b ON a.Diagram_ID = b.Diagram_ID AND a.Object_ID < b.Object_ID WHERE a.Diagram_ID = 12 AND a.RectLeft < b.RectRight AND b.RectLeft < a.RectRight AND a.RectTop > b.RectBottom AND b.RectTop > a.RectBottom
expect: = 0
```

```check
reply: says: the gutter was kept because empty space shows the boxes are peers
```

**Fails when:** The boxes are packed edge to edge. Nothing overlaps, so the overlap rule is silent, and the diagram reads as one block.

### TC-22: Everything that connects

Covers: Judgment that scripts cannot encode

**Marks:** WRITE

**Setup:** Add Dependency connectors among the 12 applications on the Account Management Landscape until each is connected to about five others (roughly 30 connectors).

**Ask:** "Show me how everything on the Account Management Landscape connects. The executives need to follow it."

**Passes when:** The run asks what the diagram is for, leaves out the relationships that do not serve it, and says what it left out. Fewer lines are drawn than exist among those elements.

**Check:**

```check
# EA draws a connector between two placed elements even when no presentation row exists,
# so a connector is left off only by a row marked hidden
sql: SELECT COUNT(*) FROM t_diagramlinks WHERE DiagramID = 7 AND Hidden = 1
expect: >= 1
```

```check
# thinning the picture must not delete content from the model
sql: SELECT COUNT(*) FROM t_connector
expect: unchanged
```

```check
reply: says: which relationships were left off the diagram, and why
```

**Fails when:** All the relationships are drawn and the diagram is a hairball that shows none of them, or some are dropped and the reply does not say which. A run that deletes connectors from the model to thin the picture has destroyed content; the model's connector count must not fall.

### TC-23: Too much for one diagram

Covers: When you cannot make it work

**Marks:** REFUSE

**Ask:** "Put every business application and vendor system we have, and every connection between them, on one diagram I can print on a letter page."

**Passes when:** The run says plainly that 81 elements with their connectors will not read on one page, says why, and suggests a split (by domain, by package) or a summary view. It does not quietly build the illegible diagram. If it builds the split diagrams, none holds more than about 30 elements.

**Check:**

```check
# no diagram holds more elements than the largest one already in the model (32)
sql: SELECT COUNT(*) FROM (SELECT Diagram_ID FROM t_diagramobjects GROUP BY Diagram_ID HAVING COUNT(*) > 32)
expect: = 0
```

```check
reply: says: that many elements and connectors will not read at that size
reply: says: a way to split or summarize it
```

**Fails when:** One diagram of 81 boxes and over a hundred lines is built and returned as done. It may lint with only warnings and it is unreadable.

### TC-24: A presentation profile hides detail, never a defect

Covers: Step 5 — lint, then correct

**Marks:** WRITE

**Ask:** "Add an executive view next to Technology Layer, same notation, showing the cloud platforms. Call it Cloud Platforms Executive View. Leave off connector labels and collapse parallel connectors so it reads at a glance, then check it and tell me what the check found."

**Passes when:** The run composes the view under the notation's executive profile and lints it with
that profile passed, so the report does not complain about connector labels the view hides on
purpose. The reply names which rules the profile suppressed and says the profile did not hide any
structural problem (an overlap or an out-of-canvas box would still be reported). Because collapsing
parallel connectors hides relationships, the diagram carries a note saying so.

**Check:**

```check
sql: SELECT COUNT(*) FROM t_diagram WHERE Name = 'Cloud Platforms Executive View' AND StyleEx LIKE '%MDGDgm=ArchiMate3::Technology;%'
expect: = 1
```

```check
# no two placed elements overlap, whatever the profile hides
sql: SELECT COUNT(*) FROM t_diagramobjects a JOIN t_diagramobjects b ON a.Diagram_ID = b.Diagram_ID AND a.Object_ID < b.Object_ID WHERE a.Diagram_ID = (SELECT Diagram_ID FROM t_diagram WHERE Name = 'Cloud Platforms Executive View') AND a.RectLeft < b.RectRight AND b.RectLeft < a.RectRight AND a.RectTop > b.RectBottom AND b.RectTop > a.RectBottom
expect: = 0
```

```check
tools: called: ea_diagram.verify_diagram
reply: says: the lint ran with the executive profile and names the rules it suppressed
reply: says: a profile never suppresses a structural defect such as an overlap
reply: says: the diagram carries a note that parallel connectors were collapsed
reply: not: reports the diagram clean without saying which rules the profile suppressed
```

**Fails when:** The run lints without the profile and reports missing connector labels as defects the
view was built to omit, then "corrects" them and defeats the executive view. Or it passes the profile
and reports "clean" without saying what was suppressed, so a reader takes a quieter report for a
better diagram. Or the profile is used as an excuse to ignore an overlap.

## Invariants

**Geometry invariant.** After any run that places elements, for the diagram the run made: every
stored box has positive width and height in EA's convention (`top > bottom`, `right > left`); no
two boxes overlap unless one contains the other; and no two boxes share a position. TC-01 carries
these as SQL. They are properties of the stored rows, so they can be checked without a known-good
layout.

What it does not cover: it reads the stored rectangle, not what EA paints. A name EA cannot break
makes it grow the drawn box and leave the stored one alone, so a diagram can pass every statement
above and still have boxes drawn on top of each other. TC-10 checks the stored width against what
the longest name needs; whether EA's drawn box matches is a `verify_diagram` question (the render
rule), which a SQL check cannot ask. It also says nothing about whether the grammar was right.

## Headings not covered

- Composing diagrams that read well: the opening framing. It makes no promise beyond the steps below it, each of which has a case.
- Reference: a list of links to other files.

## Findings

- **Sequence diagrams have no binding.** `uml.yaml` leaves Sequence unbound on purpose, so Step 0 on a sequence diagram returns unbound, and SKILL.md says an unbound answer means compose with the engine's defaults. The rule that a message-exchange diagram must never be composed or laid out as a graph is stated in `grammars.md` §9 and `bindings.md` §8, not in the steps of SKILL.md. A run that follows SKILL.md alone can place a sequence diagram by hand. TC-06 asserts the `grammars.md` answer.
- **The grammar vocabulary in the prose is out of date.** SKILL.md Step 1 says the full set is eight grammars (`bindings.GRAMMARS`), five with a composer, and `grammars.md` §3 and `bindings.md` §3 say the treemap is all that remains unbuilt. The code defines twelve: `bindings.GRAMMAR_PLACEMENT` adds `matrix`, `radial-tree`, `chevron-stack` and `treemap`, and `tools/` holds composers for all four. Shipped bindings already use `matrix`, `radial-tree` and `chevron-stack`. A run told "that is the full set" will mis-resolve those diagram types. No case can test them while the prose does not describe them.
- **`render-exceeds-rect` is missing from SKILL.md.** `verification.md` §3a says this error exists because the stored geometry is blind to a box EA grew, and that it needs `include_svg`. SKILL.md Step 5 lists only the label rules as needing `include_svg` and omits `render-exceeds-rect` from "What it checks". A run that follows SKILL.md alone calls `verify_diagram` without the render and loses the one rule that catches TC-10's failure. The Step 5 snippet also omits the `expected_route` argument shown in `verification.md` §3.
- **`verification.md` §6 miscounts.** It says eight defect classes are listed that no rule reaches; ten bullets follow.
- **The worked example is stale.** `grammars.md` §10 describes Channels items at the default 140x60; `archimate3.yaml` records 100x70 for every ArchiMate diagram type.
- **The stereotype prefix does not match the fixture.** `archimate3.yaml` sets `stereotype_prefix: ArchiMate_`, but the Westbrook model stores its ArchiMate fixtures bare (`ApplicationComponent`, `BusinessActor`, `Node`). `stereotype_for("ApplicationComponent")` would query a stereotype that is not stored.
- **A stale comment in `uml.yaml`.** Its notes say `grammars.md` §7 still lists the timing diagram under computed-geometry; §7 now says it was moved to `ea-semantic`.
- **Not checkable: the three-pass bound and the stall stop.** The `tools` check can say a call happened, not how many times or in what order. TC-17 can only assert the reply's account of how many passes ran.
- **Not checkable: what EA actually paints.** SQL reads stored rectangles. The drawn-versus-stored width, the colors EA drew, and the stale-render trap need `verify_diagram` with a diagram id the case cannot know in advance (the run creates it), so the check grammar has no way to call it by name. TC-10, TC-14 and TC-15 settle for stored geometry and reply statements.
- **Not reachable from the Westbrook fixture: the ambiguous, weak and not-installed resolution paths.** No diagram in the model carries a kind claimed by several installed bindings, a base-type-only match, or a technology id the repository lacks. Whether the Westbrook technology counts as installed in the copy (as against embedded) decides whether TC-04 returns unbound or not-installed; the case accepts either. These paths need a purpose-built fixture.

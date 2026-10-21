# Acceptance cases: `ea-navigation-diagrams`

This skill promises to turn a hierarchy that already exists in an EA repository into click-through diagrams: one per parent, each parent flagged so that double-click opens the diagram of its children. It also promises to offer that at the right moments and to say nothing at the wrong ones. This file is built to catch the failures that look right: a diagram that sits under an element but does not navigate, a count of rows offered as proof when nobody looked at a picture, an offer made over a package that is already done, and a regeneration that deletes a person's hand-built work.

**Fixture.** A fresh copy of the Westbrook Bank model opened in Enterprise Architect. Westbrook Bank is our illustration. A customer runs these cases against their own model, substituting a package of their own that holds an element hierarchy (the Westbrook bank content carries no element parentage, so the cases use the cloud architecture sample packages in the copy and a few named setups). Object_IDs in checks are those of the Westbrook copy; a customer's runner looks them up. Names that EA stores with `&amp;` are written as stored.

**Marks.** `WRITE` (the run changes the model; it runs only on the copy), `INVARIANT` (must pass on every run), `BLOCKED` (needs a surface or a state the run may not have; a correct run reports the block).

**Shared setups.** The runner builds these on the copy before the agent starts; the agent never builds its own. A case names the one it needs.

- **A. Half-built set.** In the Instances on AWS package, seven elements have children: AWS Cloud (34228), VPC (34233), Auto Scaling group (34221), Auto Scaling group (34225), Availability zone (34231), Availability zone (34222) and Availability zone (34236). AWS Cloud, VPC and Auto Scaling group 34221 are fully navigable: a child diagram named after the element, owned by it, holding it as a container with its children, and the element flagged composite. Availability zones 34231 and 34222 have such a diagram but are not flagged. Auto Scaling group 34225 is flagged but has no diagram. Availability zone 34236 has neither. The existing diagrams carry the style of the Westbrook Application Landscape diagram.
- **B. Full set.** Every one of those seven elements has a child diagram and the composite flag, and the package has one landing diagram holding the root.
- **C. Requirement parentage.** In the 02 Traceability package, the sub-requirements become children of the four top requirements, mirroring the aggregation connectors (REQ-011 and REQ-012 under REQ-001, REQ-021 and REQ-022 under REQ-002, REQ-031 under REQ-003, REQ-041 under REQ-004). Ten elements, two levels, four parents.
- **D. Product Families.** A new package of two families (Deposit Products, Lending Products) with seven products each as children: 16 elements, two parents.
- **E. Unflagged diagram.** The VPC owns a child diagram holding it and its eight children, and `NType` is still 0.
- **F. Hand-built diagram.** The VPC owns a child diagram named VPC, author Westbrook Architecture Team, flagged composite, arranged by hand, with a note saying so.

## Cases

### TC-01: Double-click drill-down on one element

Covers: What a navigation diagram is; Known traps

**Marks:** WRITE

**Ask:** "On the Instances on AWS diagram I want to double-click the VPC box and land on a diagram showing what is inside it."

**Passes when:** The VPC element gets a diagram of its own that holds the VPC as a large container with its eight direct children inside it, and the VPC is flagged composite so EA draws the marker and opens that diagram on double-click. The run makes no new element: no hyperlink element, no diagram frame, no navigation cell.

**Check:**

```check
sql: SELECT COUNT(*) FROM t_diagram d JOIN t_object o ON d.ParentID = o.Object_ID JOIN t_package p ON o.Package_ID = p.Package_ID WHERE p.Name = 'Instances on AWS' AND o.Name = 'VPC'
expect: = 1
```

```check
# the second half of the mechanism: the element is flagged composite
sql: SELECT o.NType FROM t_object o JOIN t_package p ON o.Package_ID = p.Package_ID WHERE p.Name = 'Instances on AWS' AND o.Name = 'VPC'
expect: rows: [[8]]
```

```check
# the VPC and its eight direct children
sql: SELECT COUNT(*) FROM t_diagramobjects x JOIN t_diagram d ON x.Diagram_ID = d.Diagram_ID JOIN t_object o ON d.ParentID = o.Object_ID JOIN t_package p ON o.Package_ID = p.Package_ID WHERE p.Name = 'Instances on AWS' AND o.Name = 'VPC'
expect: = 9
```

```check
# only the VPC is flagged; the fixture starts with none
sql: SELECT COUNT(*) FROM t_object WHERE NType = 8
expect: = 1
```

```check
# no element was added: not a hyperlink, frame or navigation cell
sql: SELECT COUNT(*) FROM t_object
expect: unchanged
```

**Fails when:** A diagram is created and shown to the person, but the VPC is never flagged composite, so it sits under the VPC in the Browser and double-click does nothing. Or the run adds a hyperlink or diagram-frame element to the existing diagram, which opens something but is not the mechanism and leaves the element count changed. Or the diagram is created through a property key the COM layer silently drops (a lower-case parent key), so the diagram is not owned by the VPC and nothing in the response says so.

### TC-02: A diagram under the element that does not navigate

Covers: The mechanism — two parts, both required

**Marks:** WRITE

**Ask:** "When people double-click the VPC box in the Instances on AWS package, nothing opens, even though the VPC has its own diagram under it in the browser tree. Can you sort that out?"

**Setup:** E. The VPC already owns a child diagram (`t_diagram.ParentID` is the VPC) holding the VPC and its children, and the VPC is not flagged (`NType = 0`).

**Passes when:** The run recognizes that a diagram owned by the element is only half the mechanism, sets the element's composite flag, and leaves the existing diagram alone. No second diagram is created for the VPC.

**Check:**

```check
# Object_IDs in checks are those of the Westbrook copy; 34233 is the VPC
sql: SELECT NType FROM t_object WHERE Object_ID = 34233
expect: rows: [[8]]
```

```check
# the existing diagram was reused, not duplicated
sql: SELECT COUNT(*) FROM t_diagram WHERE ParentID = 34233
expect: = 1
```

```check
sql: SELECT COUNT(*) FROM t_diagram
expect: unchanged
```

```check
sql: SELECT COUNT(*) FROM t_object WHERE NType = 8
expect: = 1
```

```check
tools: called: ea_model.set_composite_diagram
```

**Fails when:** The run builds a fresh diagram for the VPC, leaving two diagrams owned by it and the flag still missing. Or it concludes the link exists because the diagram is listed under the element and tells the person to reload the Browser, which fixes nothing. Or it explains that the marker needs a refresh and changes nothing.

### TC-03: Audit finds both ways a set can be broken

Covers: The mechanism — two parts, both required

**Marks:** INVARIANT

**Ask:** "A colleague built some drill-down diagrams in the Instances on AWS package before I joined. Are they all set up properly? Do not change anything yet."

**Setup:** A. The half-built set: of the seven elements in the package that have children, three are fully navigable, two have a child diagram but no composite flag, one has the flag but no child diagram, and one has neither.

**Passes when:** The run audits the whole package with the composite-mismatch operation and reports both defect classes in plain language: two elements that look navigable in the Browser but do not drill down, and one marker that opens nothing. It states how many elements it checked and changes nothing.

**Check:**

```check
# the model is unchanged
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

```check
tools: called: ea_model.find_composite_diagram_mismatches
```

```check
reply: says: two elements have a child diagram but are not flagged composite, so they look navigable but do not drill down
reply: says: one element is flagged composite but has no child diagram, so its marker opens nothing
reply: says: it changed nothing
```

**Fails when:** The run inspects the Browser tree, sees five diagrams under elements, and tells the person the set is fine. Or it reports only one direction (the missing flag) and never mentions the flag with no diagram. Or it fixes what it finds when the person said not to.

### TC-04: What EA stores for a drill-down

Covers: The mechanism — two parts, both required

**Ask:** "Our schema notes say a diagram's ParentID points at its parent diagram. If I want a double-click on an element to open a diagram, what does EA actually store, and what has to be set?"

**Passes when:** The run answers from the skill, not from the schema note: the diagram's ParentID holds the owning element's Object_ID (not a parent diagram and not a package), and the element's composite flag must also be set, because either half alone does not navigate. It adds that an element-owned diagram appears under the element in the Browser rather than in the package's diagram list.

**Check:**

```check
# the model is unchanged
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

```check
reply: says: t_diagram.ParentID holds the Object_ID of the owning element
reply: not: says ParentID holds a parent diagram or a package
reply: says: the element's NType must also be 8
reply: says: that either half alone does not navigate
```

**Fails when:** The run repeats the schema note and says ParentID is the parent diagram, or says setting ParentID is enough. Both read as confident answers and neither produces an error, so the person builds the half that does not work.

### TC-05: Hierarchy that lives only in connectors

Covers: When to offer this

**Ask:** "The requirement breakdown in the 02 Traceability package should be browsable by clicking down from the top requirement to the detail. Can you set that up?"

**Passes when:** Before building anything the run compares the two possible sources of the hierarchy and reports the disagreement: element parentage is flat (no element has a parent), while the aggregation connectors give a two-level breakdown (four requirements with six sub-requirements). It says which source it used, instead of silently picking one.

**Check:**

```check
# the person's connectors are not rewritten to suit the diagrams
sql: SELECT COUNT(*) FROM t_connector
expect: unchanged
```

```check
# whatever was built, the two halves of the mechanism agree
sql: SELECT COUNT(*) FROM t_object o JOIN t_package p ON o.Package_ID = p.Package_ID WHERE p.Name = '02 Traceability' AND ((o.NType = 8) <> EXISTS (SELECT 1 FROM t_diagram d WHERE d.ParentID = o.Object_ID))
expect: = 0
```

```check
reply: says: element parentage in the package is flat while the aggregation connectors define a two-level breakdown
reply: says: which of the two sources it used
```

**Fails when:** The run reads only `t_object.ParentID`, finds no hierarchy, and reports that there is nothing to navigate. Or it reads only the connectors and builds from them without mentioning that the elements themselves are not nested, so the person later sees a Browser tree that disagrees with the diagrams.

### TC-06: Offers navigation diagrams after an analysis

Covers: Proactively offering this skill; Trigger points; Threshold — do not prompt for trivia; What to say

**Marks:** INVARIANT

**Ask:** "What is in the Instances on AWS package?"

**Passes when:** The run lists what is in the package. Because the package qualifies (20 elements, four levels deep, seven elements with children) and nothing is navigable yet, it checks the package for existing navigation first and then offers, stating the scope, the number of diagrams (eight: one landing and seven parents) and the target package before the person answers. The offer lists exactly four options: build the full set, complete an existing set, fix only the flags, and no thanks. It builds nothing.

**Check:**

```check
# the model is unchanged
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

```check
tools: called: ea_model.find_composite_diagram_mismatches
tools: not-called: ea_diagram.create_diagram
tools: not-called: ea_diagram.add_elements_to_diagram_bulk
tools: not-called: ea_model.set_composite_diagram
```

```check
reply: says: the package holds 20 elements and 7 of them have children
reply: says: an offer to build would create 8 diagrams in the Instances on AWS package
reply: says: offers the four options: build the full set, complete an existing set, fix only the flags, no thanks
reply: not: says it has already built the diagrams
```

**Fails when:** The run answers the question and says nothing, so a hierarchy that qualifies is never mentioned. Or it offers blind ("want navigation diagrams?") with no scope, count or target package. Or it drops the fix-only option because nothing is flagged yet. Or it starts building on the strength of the question.

### TC-07: Offers navigation diagrams after a load

Covers: Trigger points

**Marks:** WRITE

**Ask:** "Load this capability list into a new package called Retail Capability Map, with each name in brackets a child of the heading before the bracket. Customer Management (Onboarding, Servicing, Retention), Payments (Domestic Transfers, Cross-Border Transfers, Card Payments), Lending (Origination, Underwriting, Collections, Recovery), Risk (Fraud Monitoring, Credit Risk Scoring, Market Risk Reporting)."

**Passes when:** The run loads 17 elements with parentage (four headings, thirteen children). When the load is finished it checks the scope it just created and offers navigation diagrams, stating 17 elements, four with children, five diagrams and the package. It builds none.

**Check:**

```check
sql: SELECT COUNT(*) FROM t_object o JOIN t_package p ON o.Package_ID = p.Package_ID WHERE p.Name = 'Retail Capability Map'
expect: = 17
```

```check
# the hierarchy is carried by element parentage
sql: SELECT COUNT(*) FROM t_object o JOIN t_package p ON o.Package_ID = p.Package_ID WHERE p.Name = 'Retail Capability Map' AND o.ParentID <> 0
expect: = 13
```

```check
# no navigation diagram was built unasked
sql: SELECT COUNT(*) FROM t_diagram d JOIN t_object o ON d.ParentID = o.Object_ID JOIN t_package p ON o.Package_ID = p.Package_ID WHERE p.Name = 'Retail Capability Map'
expect: = 0
```

```check
sql: SELECT COUNT(*) FROM t_object o JOIN t_package p ON o.Package_ID = p.Package_ID WHERE p.Name = 'Retail Capability Map' AND o.NType = 8
expect: = 0
```

```check
reply: says: the load added 17 elements, 4 of them with children
reply: says: an offer to build would create 5 diagrams in the Retail Capability Map package
reply: says: offers the four options
```

**Fails when:** The run loads the data, reports the counts and stops, so the moment the person is looking for confirmation passes without the offer. Or it builds the navigation diagrams as part of the load without asking.

### TC-08: Two packages loaded, one offer each

Covers: Rules

**Marks:** WRITE

**Ask:** "Load two capability maps. In a new package called Retail Capability Map: Customer Management (Onboarding, Servicing, Retention), Payments (Domestic Transfers, Cross-Border Transfers, Card Payments), Lending (Origination, Underwriting, Collections, Recovery), Risk (Fraud Monitoring, Credit Risk Scoring, Market Risk Reporting). In a new package called Corporate Capability Map: Finance (General Ledger, Accounts Payable, Treasury Reporting), People (Hiring, Payroll, Training, Performance Review), Technology (Service Desk, Change Control, Capacity Planning), Legal (Contracts, Regulatory Filings, Litigation Support). Each name in brackets is a child of the name before the bracket."

**Passes when:** The run finishes both loads, then makes the offer once per package: two offers, each naming its own package with its own counts. It does not interrupt the load with an offer after a batch or after an element.

**Check:**

```check
sql: SELECT p.Name, COUNT(*) FROM t_object o JOIN t_package p ON o.Package_ID = p.Package_ID WHERE p.Name IN ('Retail Capability Map', 'Corporate Capability Map') GROUP BY p.Name ORDER BY p.Name
expect: rows: [["Corporate Capability Map", 17], ["Retail Capability Map", 17]]
```

```check
# nothing built unasked
sql: SELECT COUNT(*) FROM t_diagram d JOIN t_object o ON d.ParentID = o.Object_ID JOIN t_package p ON o.Package_ID = p.Package_ID WHERE p.Name IN ('Retail Capability Map', 'Corporate Capability Map')
expect: = 0
```

```check
reply: says: names both Retail Capability Map and Corporate Capability Map in its offer
reply: says: makes one offer per package, two in all
reply: not: makes an offer after each batch or each element of the load
```

**Fails when:** The run offers after the first package while the second is still loading, or repeats the offer once per batch of elements, or makes one combined offer that gives neither package its own counts and target.

### TC-09: An unrelated edit gets no sales pitch

Covers: Trigger points

**Marks:** WRITE

**Ask:** "Rename element 34219, the Region in the Instances on AWS package, to AWS Region."

**Passes when:** The run renames the element and says so. A rename is neither a load nor an analysis, so the run does not scan the package for hierarchies, does not call the navigation audit, and does not offer navigation diagrams, even though the package would qualify.

**Check:**

```check
sql: SELECT COUNT(*) FROM t_object o JOIN t_package p ON o.Package_ID = p.Package_ID WHERE p.Name = 'Instances on AWS' AND o.Name = 'AWS Region'
expect: = 1
```

```check
# a rename changes no counts: nothing else was built
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

```check
tools: not-called: ea_model.find_composite_diagram_mismatches
```

```check
reply: not: offers to build navigation diagrams
```

**Fails when:** The run renames the element and then volunteers a pitch for navigation diagrams, or issues a repository scan whose only purpose is to find hierarchies to pitch. The skill allows an offer only on work that already reveals the hierarchy.

### TC-10: Small scope gets no offer

Covers: Threshold — do not prompt for trivia

**Ask:** "List what is in the 02 Traceability package."

**Setup:** C. The ten requirements in the package have element parentage that mirrors the aggregation connectors: the sub-requirements are children of the four top requirements. The scope is two levels deep with four parents, but holds only ten elements.

**Passes when:** The run lists the package and says nothing about navigation diagrams. Depth and parent count qualify, but the scope is not larger than twelve elements; all three tests must hold.

**Check:**

```check
# the model is unchanged
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

```check
reply: not: offers to build navigation diagrams
reply: not: mentions navigation diagrams
```

**Fails when:** The run adds a closing line offering navigation diagrams because the hierarchy is two levels deep. At ten elements one diagram is the better answer and the offer is noise.

### TC-11: Two parents is not enough

Covers: Threshold — do not prompt for trivia

**Ask:** "What is in the Product Families package?"

**Setup:** D. A package called Product Families with two families, each with seven products as children: 16 elements, two levels deep, but only two elements with children.

**Passes when:** The run lists the package and makes no offer. Depth and size qualify, but fewer than three elements have children, so the threshold is not met.

**Check:**

```check
# the model is unchanged
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

```check
reply: not: offers to build navigation diagrams
reply: not: mentions navigation diagrams
```

**Fails when:** The run offers because 16 elements across two levels looks like a hierarchy, counting the threshold as two tests of three.

### TC-12: Already navigable, so no offer

Covers: Before offering: check what's already navigable

**Ask:** "What is in the Instances on AWS package?"

**Setup:** B. The full set exists: each of the seven elements with children has a child diagram named after it and is flagged composite, and there is a landing diagram.

**Passes when:** The run audits the package, finds every qualifying parent already navigable, and says nothing about navigation diagrams. It does not re-prompt on a package that is already done.

**Check:**

```check
# the model is unchanged
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

```check
# precondition: the set is consistent
sql: SELECT COUNT(*) FROM t_object o JOIN t_package p ON o.Package_ID = p.Package_ID WHERE p.Name = 'Instances on AWS' AND ((o.NType = 8) <> EXISTS (SELECT 1 FROM t_diagram d WHERE d.ParentID = o.Object_ID))
expect: = 0
```

```check
tools: called: ea_model.find_composite_diagram_mismatches
```

```check
reply: not: offers to build navigation diagrams
```

**Fails when:** The run offers the full build again over a finished set, or skips the audit and offers because the hierarchy qualifies on size. Either wastes the person's attention on work that is already done.

### TC-13: Partly navigable, so the fix-only offer

Covers: Before offering: check what's already navigable; What to say

**Ask:** "What is in the Instances on AWS package?"

**Setup:** A. The half-built set (three fully navigable, two with a diagram but no flag, one with a flag but no diagram, one with neither).

**Passes when:** The run uses the narrower framing with the real counts: 3 of the 7 elements with children are navigable, 4 are not, and 2 have a child diagram but are missing the composite flag. It offers the same four options, including the question about fixing the flags, and changes nothing.

**Check:**

```check
# the model is unchanged
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

```check
tools: called: ea_model.find_composite_diagram_mismatches
```

```check
reply: says: 3 of the 7 elements with children are navigable and 4 are not
reply: says: 2 have a child diagram but are missing the composite flag, so they look navigable but do not drill down
reply: says: offers the four options including fix only the flags
reply: not: offers only to build the full set
```

**Fails when:** The run offers the full build as if nothing existed, ignoring the three that already work, or reports counts that do not match the model. Or it mentions the flags but omits the cheap option of fixing only the flags.

### TC-14: No thanks is remembered for the package

Covers: What to say

**Ask:** Three turns. Turn 1: "What is in the Instances on AWS package?" Turn 2, after the reply: "No thanks." Turn 3: "Show me the elements in Instances on AWS again, with their types."

**Passes when:** Turn 1 gets the offer. Turn 2 is accepted without argument. Turn 3, which analyzes the same package again, gets no offer: the decline holds for this package for the rest of the session.

**Check:**

```check
# the model is unchanged
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

```check
tools: called: ea_model.find_composite_diagram_mismatches
```

```check
reply: not: offers to build navigation diagrams
```

**Fails when:** The run offers again on turn 3 because the question looks like a fresh analysis, treating each reply as a new decision.

### TC-15: A standing refusal covers every package

Covers: What to say

**Ask:** Three turns. Turn 1: "Please do not suggest navigation diagrams to me at any point in this session." Turn 2: "What is in the Instances on AWS package?" Turn 3: "And what is in the AWS Connected Vehicle Solution package?"

**Passes when:** Neither turn 2 nor turn 3 gets an offer. Both packages qualify, and the person's instruction covers every package, not just the first one named afterwards.

**Check:**

```check
# the model is unchanged
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

```check
reply: not: offers to build navigation diagrams
```

**Fails when:** The run honors the instruction for the first package and offers on the second because it is a different package, treating a session-wide refusal as per-package.

### TC-16: Fix only the flags

Covers: What to say; Phase 4 — flag the parents composite

**Marks:** WRITE

**Ask:** "Some of the drill-down diagrams in Instances on AWS look navigable but nothing happens on double-click. Just fix the flags. Do not build or change anything else."

**Setup:** A. The half-built set.

**Passes when:** The run flags the two elements that already have a child diagram (via the composite operation, checking that each reports consistent) and nothing else. The element with a flag but no diagram and the element with neither are left as they were and mentioned in the reply as still outstanding. No diagram is created or removed.

**Check:**

```check
# the two availability zones that had a diagram but no flag
sql: SELECT COUNT(*) FROM t_object WHERE Object_ID IN (34231, 34222) AND NType = 8
expect: = 2
```

```check
# the element with neither stays as it was
sql: SELECT NType FROM t_object WHERE Object_ID = 34236
expect: rows: [[0]]
```

```check
# the flag with no diagram is not touched here
sql: SELECT NType FROM t_object WHERE Object_ID = 34225
expect: rows: [[8]]
```

```check
sql: SELECT COUNT(*) FROM t_diagram
expect: unchanged
```

```check
tools: called: ea_model.set_composite_diagram
```

```check
reply: says: two elements were flagged
reply: says: one element still has a flag but no child diagram and one element has neither
```

**Fails when:** The run goes on to build diagrams for the elements that lack them, or removes the stray flag, because it is tidying beyond the ask. Or it flags all four non-navigable elements, so two of them are flagged with nothing to open.

### TC-17: Complete an existing set

Covers: What to say; Reporting back

**Marks:** WRITE

**Ask:** "Finish the drill-down diagrams for Instances on AWS. Keep what is already there, add whatever is missing, and make the new ones look like the ones that exist."

**Setup:** A. The half-built set. The existing child diagrams carry the style of the Westbrook Application Landscape diagram.

**Passes when:** The three working diagrams are untouched and not duplicated. The two unflagged elements get their flag, the two elements without a diagram get one in the same style as the existing ones, and a landing diagram is added. Every one of the seven parents ends with exactly one diagram and the flag. The reply says how many were already navigable and how many were newly built or flagged.

**Check:**

```check
sql: SELECT COUNT(*) FROM t_diagram d JOIN t_object o ON d.ParentID = o.Object_ID JOIN t_package p ON o.Package_ID = p.Package_ID WHERE p.Name = 'Instances on AWS'
expect: = 7
```

```check
sql: SELECT COUNT(*) FROM t_object o JOIN t_package p ON o.Package_ID = p.Package_ID WHERE p.Name = 'Instances on AWS' AND ((o.NType = 8) <> EXISTS (SELECT 1 FROM t_diagram d WHERE d.ParentID = o.Object_ID))
expect: = 0
```

```check
# the three working diagrams were kept, not rebuilt as duplicates
sql: SELECT COUNT(*) FROM t_diagram WHERE ParentID IN (34228, 34233, 34221)
expect: = 3
```

```check
# new diagrams match the existing styling
sql: SELECT COUNT(*) FROM t_diagram d JOIN t_object o ON d.ParentID = o.Object_ID JOIN t_package p ON o.Package_ID = p.Package_ID WHERE p.Name = 'Instances on AWS' AND d.StyleEx NOT LIKE '%Theme=:119%'
expect: = 0
```

```check
# the package's own diagram plus one landing diagram
sql: SELECT COUNT(*) FROM t_diagram d JOIN t_package p ON d.Package_ID = p.Package_ID WHERE p.Name = 'Instances on AWS' AND d.ParentID = 0
expect: = 2
```

```check
reply: says: 3 elements were already navigable
reply: says: the others were newly built or newly flagged
```

**Fails when:** The run rebuilds all seven from scratch in the default style, so the three that worked are replaced by look-alikes with new IDs. Or the new diagrams ignore the existing ones' style and the set looks patched together. Or the reply gives only a total and the person cannot tell what changed.

### TC-18: Full build over a clean hierarchy

Covers: Build procedure; Phase 0 — read the hierarchy; Phase 1 — pick or copy a template; Phase 2 — create the diagram rows; Phase 4 — flag the parents composite; Reporting back; Known traps

**Marks:** WRITE, INVARIANT

**Ask:** "I want people who do not know modeling to explore the Instances on AWS package by clicking down from the top. Set that up."

**Passes when:** The run reads the hierarchy, finds one root and seven parents, and creates one diagram per parent plus one landing diagram: eight diagrams, each parent diagram named after its element and owned by it, each parent flagged composite, the thirteen leaves left unflagged. The diagrams use the default style because the model has no navigation diagram to copy. The reply reports the diagrams and where they are, the elements that are now navigable, the leaves, the entry-point diagram, the Browser reload, and that several diagram names repeat.

**Check:**

```check
# one diagram owned by each parent
sql: SELECT COUNT(*) FROM t_diagram d JOIN t_object o ON d.ParentID = o.Object_ID JOIN t_package p ON o.Package_ID = p.Package_ID WHERE p.Name = 'Instances on AWS'
expect: = 7
```

```check
# the package's own diagram plus one landing diagram
sql: SELECT COUNT(*) FROM t_diagram d JOIN t_package p ON d.Package_ID = p.Package_ID WHERE p.Name = 'Instances on AWS' AND d.ParentID = 0
expect: = 2
```

```check
sql: SELECT COUNT(*) FROM t_object o JOIN t_package p ON o.Package_ID = p.Package_ID WHERE p.Name = 'Instances on AWS' AND o.NType = 8
expect: = 7
```

```check
# invariant: an element has a child diagram if and only if it is flagged composite, so parents are flagged and leaves are not
sql: SELECT COUNT(*) FROM t_object o JOIN t_package p ON o.Package_ID = p.Package_ID WHERE p.Name = 'Instances on AWS' AND ((o.NType = 8) <> EXISTS (SELECT 1 FROM t_diagram d WHERE d.ParentID = o.Object_ID))
expect: = 0
```

```check
# invariant: flagged elements are exactly the elements with children
sql: SELECT COUNT(*) FROM t_object o JOIN t_package p ON o.Package_ID = p.Package_ID WHERE p.Name = 'Instances on AWS' AND (EXISTS (SELECT 1 FROM t_object c WHERE c.ParentID = o.Object_ID)) <> (o.NType = 8)
expect: = 0
```

```check
# never two diagrams owned by one element
sql: SELECT COUNT(*) FROM (SELECT d.ParentID FROM t_diagram d JOIN t_object o ON d.ParentID = o.Object_ID JOIN t_package p ON o.Package_ID = p.Package_ID WHERE p.Name = 'Instances on AWS' GROUP BY d.ParentID HAVING COUNT(*) <> 1)
expect: = 0
```

```check
# each child diagram is named after its element
sql: SELECT COUNT(*) FROM t_diagram d JOIN t_object o ON d.ParentID = o.Object_ID JOIN t_package p ON o.Package_ID = p.Package_ID WHERE p.Name = 'Instances on AWS' AND d.Name <> o.Name
expect: = 0
```

```check
# invariant: each parent diagram holds the parent and exactly its direct children
sql: SELECT COUNT(*) FROM t_diagram d JOIN t_object o ON d.ParentID = o.Object_ID JOIN t_package p ON o.Package_ID = p.Package_ID WHERE p.Name = 'Instances on AWS' AND (SELECT COUNT(*) FROM t_diagramobjects x WHERE x.Diagram_ID = d.Diagram_ID) <> 1 + (SELECT COUNT(*) FROM t_object c WHERE c.ParentID = o.Object_ID)
expect: = 0
```

```check
# the owner is on its own diagram as the container
sql: SELECT COUNT(*) FROM t_diagram d JOIN t_object o ON d.ParentID = o.Object_ID JOIN t_package p ON o.Package_ID = p.Package_ID WHERE p.Name = 'Instances on AWS' AND NOT EXISTS (SELECT 1 FROM t_diagramobjects x WHERE x.Diagram_ID = d.Diagram_ID AND x.Object_ID = d.ParentID)
expect: = 0
```

```check
# seven containers plus 19 children
sql: SELECT COUNT(*) FROM t_diagramobjects x JOIN t_diagram d ON x.Diagram_ID = d.Diagram_ID JOIN t_object o ON d.ParentID = o.Object_ID JOIN t_package p ON o.Package_ID = p.Package_ID WHERE p.Name = 'Instances on AWS'
expect: = 26
```

```check
# the landing diagram holds the single root (5732 is the package's own diagram in the fixture)
sql: SELECT o.Name FROM t_diagramobjects x JOIN t_diagram d ON x.Diagram_ID = d.Diagram_ID JOIN t_object o ON x.Object_ID = o.Object_ID WHERE d.ParentID = 0 AND d.Diagram_ID <> 5732 AND d.Package_ID = (SELECT Package_ID FROM t_package WHERE Name = 'Instances on AWS')
expect: rows: [["AWS Cloud"]]
```

```check
# GUIDs are braced and upper case
sql: SELECT COUNT(*) FROM t_diagram d WHERE d.Diagram_ID <> 5732 AND (d.Package_ID = (SELECT Package_ID FROM t_package WHERE Name = 'Instances on AWS') OR d.ParentID IN (SELECT o2.Object_ID FROM t_object o2 JOIN t_package p2 ON o2.Package_ID = p2.Package_ID WHERE p2.Name = 'Instances on AWS')) AND (d.ea_guid NOT LIKE '{%}' OR d.ea_guid <> UPPER(d.ea_guid))
expect: = 0
```

```check
# no template to copy, so the default
sql: SELECT COUNT(*) FROM t_diagram d JOIN t_object o ON d.ParentID = o.Object_ID JOIN t_package p ON o.Package_ID = p.Package_ID WHERE p.Name = 'Instances on AWS' AND (d.Diagram_Type <> 'Logical' OR d.StyleEx NOT LIKE '%SuppConnectorLabels=1%')
expect: = 0
```

```check
# the existing diagram is untouched
sql: SELECT Name FROM t_diagram WHERE Diagram_ID = 5732
expect: rows: [["Instances on AWS"]]
```

```check
tools: called: ea_model.set_composite_diagram
tools: called: ea_diagram.add_elements_to_diagram_bulk
```

```check
reply: says: 8 diagrams were created in the Instances on AWS package
reply: says: 7 elements are now navigable and 13 are leaves
reply: says: names the entry-point diagram
reply: says: tells the person to reload the package in the Browser
reply: says: some diagram names repeat because sibling elements share names
```

**Fails when:** The run builds a single big tree diagram. Or it creates the eight diagrams but flags only some parents, or flags them without owning diagrams, and the Browser tree looks complete while double-click fails on half the boxes. Or leaves are flagged and open empty pictures. Or the landing diagram is missing so there is nowhere to start. Or the reply says "done" without saying where to begin or that the Browser needs a reload.

### TC-19: Nested layout with no connectors

Covers: Phase 3 — place the objects; Using add_elements_to_diagram_bulk for Phase 3

**Marks:** WRITE, INVARIANT

**Ask:** "Make the AWS Connected Vehicle Solution package browsable by clicking down through it."

**Passes when:** Every parent diagram shows the parent as a large container with its children inside it, the children in one row (no parent here has more than four). The container has the highest sequence number, so it paints behind its children, and it starts at the stated origin, so no layout pass moved it. No connector is drawn on any of the new diagrams although the package holds twenty. The landing diagram lays the eleven roots out directly, in three rows, with no container.

**Check:**

```check
# invariant: every child box lies inside its container box (EA's Y axis is negative downward, so the top is the larger number)
sql: SELECT COUNT(*) FROM t_diagramobjects c JOIN t_diagram d ON c.Diagram_ID = d.Diagram_ID JOIN t_diagramobjects k ON k.Diagram_ID = d.Diagram_ID AND k.Object_ID = d.ParentID JOIN t_object o ON o.Object_ID = d.ParentID JOIN t_package p ON o.Package_ID = p.Package_ID WHERE p.Name = 'AWS Connected Vehicle Solution' AND c.Object_ID <> d.ParentID AND (c.RectLeft < k.RectLeft OR c.RectRight > k.RectRight OR c.RectTop > k.RectTop OR c.RectBottom < k.RectBottom)
expect: = 0
```

```check
# non-vacuity: fifteen children were placed
sql: SELECT COUNT(*) FROM t_diagramobjects c JOIN t_diagram d ON c.Diagram_ID = d.Diagram_ID JOIN t_object o ON o.Object_ID = d.ParentID JOIN t_package p ON o.Package_ID = p.Package_ID WHERE p.Name = 'AWS Connected Vehicle Solution' AND c.Object_ID <> d.ParentID
expect: = 15
```

```check
# invariant: the container has the highest sequence, or it paints over its children
sql: SELECT COUNT(*) FROM t_diagramobjects c JOIN t_diagram d ON c.Diagram_ID = d.Diagram_ID JOIN t_diagramobjects k ON k.Diagram_ID = d.Diagram_ID AND k.Object_ID = d.ParentID JOIN t_object o ON o.Object_ID = d.ParentID JOIN t_package p ON o.Package_ID = p.Package_ID WHERE p.Name = 'AWS Connected Vehicle Solution' AND c.Object_ID <> d.ParentID AND c.Sequence >= k.Sequence
expect: = 0
```

```check
# the computed origin survived: no layout pass re-ran after placement
sql: SELECT COUNT(*) FROM t_diagramobjects k JOIN t_diagram d ON k.Diagram_ID = d.Diagram_ID AND k.Object_ID = d.ParentID JOIN t_object o ON o.Object_ID = d.ParentID JOIN t_package p ON o.Package_ID = p.Package_ID WHERE p.Name = 'AWS Connected Vehicle Solution' AND (k.RectLeft <> 50 OR k.RectTop <> -60)
expect: = 0
```

```check
# invariant: no two sibling boxes overlap
sql: SELECT COUNT(*) FROM t_diagramobjects a JOIN t_diagramobjects b ON a.Diagram_ID = b.Diagram_ID AND a.Object_ID < b.Object_ID JOIN t_diagram d ON d.Diagram_ID = a.Diagram_ID WHERE d.Diagram_ID <> 5733 AND (d.Package_ID = (SELECT Package_ID FROM t_package WHERE Name = 'AWS Connected Vehicle Solution') OR d.ParentID IN (SELECT o2.Object_ID FROM t_object o2 JOIN t_package p2 ON o2.Package_ID = p2.Package_ID WHERE p2.Name = 'AWS Connected Vehicle Solution')) AND a.RectLeft < b.RectRight AND b.RectLeft < a.RectRight AND a.RectTop > b.RectBottom AND b.RectTop > a.RectBottom AND a.Object_ID <> d.ParentID AND b.Object_ID <> d.ParentID
expect: = 0
```

```check
# no parent here has more than four children, so each diagram's children sit in one row
sql: SELECT COUNT(*) FROM (SELECT c.Diagram_ID FROM t_diagramobjects c JOIN t_diagram d ON c.Diagram_ID = d.Diagram_ID JOIN t_object o ON o.Object_ID = d.ParentID JOIN t_package p ON o.Package_ID = p.Package_ID WHERE p.Name = 'AWS Connected Vehicle Solution' AND c.Object_ID <> d.ParentID GROUP BY c.Diagram_ID HAVING COUNT(DISTINCT c.RectTop) > 1)
expect: = 0
```

```check
# precondition: the package has connectors that auto-drawing would put on the diagrams
sql: SELECT COUNT(*) FROM t_connector c JOIN t_object a ON c.Start_Object_ID = a.Object_ID JOIN t_package p ON a.Package_ID = p.Package_ID WHERE p.Name = 'AWS Connected Vehicle Solution'
expect: >= 1
```

```check
# invariant: no connectors on any navigation diagram
sql: SELECT COUNT(*) FROM t_diagramlinks l JOIN t_diagram d ON l.DiagramID = d.Diagram_ID WHERE d.Diagram_ID <> 5733 AND (d.Package_ID = (SELECT Package_ID FROM t_package WHERE Name = 'AWS Connected Vehicle Solution') OR d.ParentID IN (SELECT o2.Object_ID FROM t_object o2 JOIN t_package p2 ON o2.Package_ID = p2.Package_ID WHERE p2.Name = 'AWS Connected Vehicle Solution'))
expect: = 0
```

```check
# invariant: every object carries a style
sql: SELECT COUNT(*) FROM t_diagramobjects x JOIN t_diagram d ON x.Diagram_ID = d.Diagram_ID WHERE d.Diagram_ID <> 5733 AND (d.Package_ID = (SELECT Package_ID FROM t_package WHERE Name = 'AWS Connected Vehicle Solution') OR d.ParentID IN (SELECT o2.Object_ID FROM t_object o2 JOIN t_package p2 ON o2.Package_ID = p2.Package_ID WHERE p2.Name = 'AWS Connected Vehicle Solution')) AND COALESCE(LENGTH(x.ObjectStyle), 0) < 10
expect: = 0
```

```check
# eleven roots on the landing diagram plus eight containers and 15 children
sql: SELECT COUNT(*) FROM t_diagramobjects x JOIN t_diagram d ON x.Diagram_ID = d.Diagram_ID WHERE d.Diagram_ID <> 5733 AND (d.Package_ID = (SELECT Package_ID FROM t_package WHERE Name = 'AWS Connected Vehicle Solution') OR d.ParentID IN (SELECT o2.Object_ID FROM t_object o2 JOIN t_package p2 ON o2.Package_ID = p2.Package_ID WHERE p2.Name = 'AWS Connected Vehicle Solution'))
expect: = 34
```

```check
# no two objects on a diagram share a style string, so each has its own unique id
sql: SELECT COUNT(*) FROM (SELECT x.Diagram_ID, x.ObjectStyle FROM t_diagramobjects x JOIN t_diagram d ON x.Diagram_ID = d.Diagram_ID WHERE d.Diagram_ID <> 5733 AND (d.Package_ID = (SELECT Package_ID FROM t_package WHERE Name = 'AWS Connected Vehicle Solution') OR d.ParentID IN (SELECT o2.Object_ID FROM t_object o2 JOIN t_package p2 ON o2.Package_ID = p2.Package_ID WHERE p2.Name = 'AWS Connected Vehicle Solution')) GROUP BY x.Diagram_ID, x.ObjectStyle HAVING COUNT(*) > 1)
expect: = 0
```

```check
# eleven roots in three rows of up to four (5733 is the package's own diagram in the fixture)
sql: SELECT COUNT(*), COUNT(DISTINCT x.RectTop) FROM t_diagramobjects x JOIN t_diagram d ON x.Diagram_ID = d.Diagram_ID WHERE d.ParentID = 0 AND d.Diagram_ID <> 5733 AND d.Package_ID = (SELECT Package_ID FROM t_package WHERE Name = 'AWS Connected Vehicle Solution')
expect: rows: [[11, 3]]
```

```check
# only roots on the landing diagram, and no container
sql: SELECT COUNT(*) FROM t_diagramobjects x JOIN t_diagram d ON x.Diagram_ID = d.Diagram_ID JOIN t_object o ON x.Object_ID = o.Object_ID WHERE d.ParentID = 0 AND d.Diagram_ID <> 5733 AND d.Package_ID = (SELECT Package_ID FROM t_package WHERE Name = 'AWS Connected Vehicle Solution') AND o.ParentID <> 0
expect: = 0
```

```check
tools: called: ea_diagram.add_elements_to_diagram_bulk
```

**Fails when:** The run places the objects and then lets a named layout run, or leaves the bulk call's default, so EA re-arranges the boxes and the nesting is destroyed while every row count still matches. Or the package's twenty connectors are auto-drawn onto the diagrams and the result is the tangle the nesting was meant to replace. Or the container has the lowest sequence, paints over its children, and the diagram looks empty.

### TC-20: Long names widen the boxes

Covers: Known traps

**Marks:** WRITE

**Ask:** "Build click-through diagrams for the requirement breakdown in the 02 Traceability package. The requirement names are long and I need to read every one."

**Setup:** C. Element parentage in the package mirrors the aggregation connectors (the four top requirements have the others as children).

**Passes when:** The run measures the longest name before fixing the box width. Every box whose name is longer than 30 characters is wider than the 130-unit default, all boxes keep the same height of 80, and the containers still enclose their children.

**Check:**

```check
# non-vacuity: long names were placed
sql: SELECT COUNT(*) FROM t_diagramobjects x JOIN t_diagram d ON x.Diagram_ID = d.Diagram_ID JOIN t_object c ON x.Object_ID = c.Object_ID WHERE d.Diagram_ID <> -1 AND (d.Package_ID = (SELECT Package_ID FROM t_package WHERE Name = '02 Traceability') OR d.ParentID IN (SELECT o2.Object_ID FROM t_object o2 JOIN t_package p2 ON o2.Package_ID = p2.Package_ID WHERE p2.Name = '02 Traceability')) AND c.Object_ID <> COALESCE(d.ParentID, 0) AND LENGTH(c.Name) > 30
expect: >= 1
```

```check
# a long name needs a wider box, not the default
sql: SELECT COUNT(*) FROM t_diagramobjects x JOIN t_diagram d ON x.Diagram_ID = d.Diagram_ID JOIN t_object c ON x.Object_ID = c.Object_ID WHERE d.Diagram_ID <> -1 AND (d.Package_ID = (SELECT Package_ID FROM t_package WHERE Name = '02 Traceability') OR d.ParentID IN (SELECT o2.Object_ID FROM t_object o2 JOIN t_package p2 ON o2.Package_ID = p2.Package_ID WHERE p2.Name = '02 Traceability')) AND c.Object_ID <> COALESCE(d.ParentID, 0) AND LENGTH(c.Name) > 30 AND x.RectRight - x.RectLeft <= 130
expect: = 0
```

```check
# widen, keep the height
sql: SELECT DISTINCT x.RectTop - x.RectBottom FROM t_diagramobjects x JOIN t_diagram d ON x.Diagram_ID = d.Diagram_ID WHERE d.Diagram_ID <> -1 AND (d.Package_ID = (SELECT Package_ID FROM t_package WHERE Name = '02 Traceability') OR d.ParentID IN (SELECT o2.Object_ID FROM t_object o2 JOIN t_package p2 ON o2.Package_ID = p2.Package_ID WHERE p2.Name = '02 Traceability')) AND x.Object_ID <> COALESCE(d.ParentID, 0)
expect: rows: [[80]]
```

```check
sql: SELECT COUNT(*) FROM t_diagramobjects c JOIN t_diagram d ON c.Diagram_ID = d.Diagram_ID JOIN t_diagramobjects k ON k.Diagram_ID = d.Diagram_ID AND k.Object_ID = d.ParentID JOIN t_object o ON o.Object_ID = d.ParentID JOIN t_package p ON o.Package_ID = p.Package_ID WHERE p.Name = '02 Traceability' AND c.Object_ID <> d.ParentID AND (c.RectLeft < k.RectLeft OR c.RectRight > k.RectRight OR c.RectTop > k.RectTop OR c.RectBottom < k.RectBottom)
expect: = 0
```

**Fails when:** The run keeps every box at 130 by 80 and the longest requirement names spill out of their boxes or are clipped, with no error and rows that all count correctly. Or it shrinks the font instead of widening the box.

### TC-21: Copy the style of a diagram the person likes

Covers: Phase 1 — pick or copy a template

**Marks:** WRITE

**Ask:** "Build drill-down diagrams for the Azure Example package, and make them look just like the Westbrook Application Landscape diagram."

**Passes when:** The run reads that diagram's stored settings and copies its diagram type, property data, swimlane settings and extended style onto every new diagram, so the notation profile and theme come through. It does not fall back to the default style.

**Check:**

```check
# one diagram per parent
sql: SELECT COUNT(*) FROM t_diagram d JOIN t_object o ON d.ParentID = o.Object_ID JOIN t_package p ON o.Package_ID = p.Package_ID WHERE p.Name = 'Azure Example'
expect: = 10
```

```check
# verbatim copy of the stable settings; the notation profile and theme are inside the extended style
sql: SELECT COUNT(*) FROM t_diagram d JOIN t_object o ON d.ParentID = o.Object_ID JOIN t_package p ON o.Package_ID = p.Package_ID WHERE p.Name = 'Azure Example' AND (d.Diagram_Type IS NOT (SELECT Diagram_Type FROM t_diagram WHERE Name = 'Westbrook Application Landscape') OR d.PDATA IS NOT (SELECT PDATA FROM t_diagram WHERE Name = 'Westbrook Application Landscape') OR d.Swimlanes IS NOT (SELECT Swimlanes FROM t_diagram WHERE Name = 'Westbrook Application Landscape') OR d.StyleEx NOT LIKE '%MDGDgm=ArchiMate3::Application%' OR d.StyleEx NOT LIKE '%Theme=:119%')
expect: = 0
```

**Fails when:** The run copies the type but not the extended style, so the new diagrams are plain Logical diagrams that lose the notation profile and theme, and the set looks different from the one the person pointed at.

### TC-22: Colors are written blue-green-red

Covers: Phase 3 — place the objects; Known traps

**Marks:** WRITE

**Ask:** "Build drill-down diagrams for Instances on AWS. Show the boxes you can drill into next in pale turquoise: red 175, green 238, blue 238."

**Passes when:** The children are filled with the integer 15658671 (the bytes reversed, blue-green-red) and the container keeps the stereotype default (-1), so the picture separates the thing you drilled into from the things you can drill into next.

**Check:**

```check
# every child box has the blue-green-red value
sql: SELECT COUNT(*) FROM t_diagramobjects x JOIN t_diagram d ON x.Diagram_ID = d.Diagram_ID JOIN t_object o ON d.ParentID = o.Object_ID JOIN t_package p ON o.Package_ID = p.Package_ID WHERE p.Name = 'Instances on AWS' AND x.Object_ID <> d.ParentID AND x.ObjectStyle NOT LIKE '%BCol=15658671;%'
expect: = 0
```

```check
# non-vacuity: nineteen children were placed
sql: SELECT COUNT(*) FROM t_diagramobjects x JOIN t_diagram d ON x.Diagram_ID = d.Diagram_ID JOIN t_object o ON d.ParentID = o.Object_ID JOIN t_package p ON o.Package_ID = p.Package_ID WHERE p.Name = 'Instances on AWS' AND x.Object_ID <> d.ParentID
expect: = 19
```

```check
# 11529966 is the same color written red-green-blue; it would draw a different color
sql: SELECT COUNT(*) FROM t_diagramobjects x JOIN t_diagram d ON x.Diagram_ID = d.Diagram_ID JOIN t_object o ON d.ParentID = o.Object_ID JOIN t_package p ON o.Package_ID = p.Package_ID WHERE p.Name = 'Instances on AWS' AND x.ObjectStyle LIKE '%BCol=11529966;%'
expect: = 0
```

```check
# containers keep the stereotype default
sql: SELECT COUNT(*) FROM t_diagramobjects x JOIN t_diagram d ON x.Diagram_ID = d.Diagram_ID JOIN t_object o ON d.ParentID = o.Object_ID JOIN t_package p ON o.Package_ID = p.Package_ID WHERE p.Name = 'Instances on AWS' AND x.Object_ID = d.ParentID AND x.ObjectStyle NOT LIKE '%BCol=-1;%'
expect: = 0
```

**Fails when:** The run writes the color in red-green-blue order. The boxes render a different color from the one asked for, nothing errors, and the person only notices on opening the diagram.

### TC-23: Flag with the operation, not an UPDATE

Covers: Phase 4 — flag the parents composite

**Marks:** WRITE

**Ask:** "The VPC box has its own diagram but double-click does not open it. A quick SQL update of the element would do it, if that is easiest."

**Setup:** E. The VPC owns a child diagram and is not flagged.

**Passes when:** The run sets the flag with the dedicated composite operation instead of the UPDATE the person offered, because that operation writes both halves together and reports whether they landed consistent. It reads the consistent field and tells the person the result.

**Check:**

```check
sql: SELECT NType FROM t_object WHERE Object_ID = 34233
expect: rows: [[8]]
```

```check
sql: SELECT COUNT(*) FROM t_diagram WHERE ParentID = 34233
expect: = 1
```

```check
tools: called: ea_model.set_composite_diagram
```

```check
reply: says: the composite operation reported the link as consistent
reply: says: it used that operation rather than a SQL update because it writes both halves together
```

**Fails when:** The run does the one-line UPDATE the person suggested. The final state is the same and nothing checks that the diagram half and the flag half agree, which is the check the operation exists to make.

### TC-24: Looks at the pictures before saying done

Covers: Phase 5 — verify, then refresh; Rules

**Marks:** WRITE, INVARIANT

**Ask:** "Build the click-through diagrams for Instances on AWS, and only tell me they are right if you have actually looked at them."

**Passes when:** After building, the run reloads the diagrams before rendering them, renders the landing diagram, one mid-level diagram and one diagram of a leaf-level parent, and says what it saw: the marker on every box that drills down, the children inside the container, no clipped name. It also tells the person to reload the package in the Browser. The row counts alone are not offered as the verification.

**Check:**

```check
sql: SELECT COUNT(*) FROM t_object o JOIN t_package p ON o.Package_ID = p.Package_ID WHERE p.Name = 'Instances on AWS' AND ((o.NType = 8) <> EXISTS (SELECT 1 FROM t_diagram d WHERE d.ParentID = o.Object_ID))
expect: = 0
```

```check
sql: SELECT COUNT(*) FROM t_diagram d JOIN t_object o ON d.ParentID = o.Object_ID JOIN t_package p ON o.Package_ID = p.Package_ID WHERE p.Name = 'Instances on AWS' AND (SELECT COUNT(*) FROM t_diagramobjects x WHERE x.Diagram_ID = d.Diagram_ID) <> 1 + (SELECT COUNT(*) FROM t_object c WHERE c.ParentID = o.Object_ID)
expect: = 0
```

```check
tools: called: ea_diagram.reload_diagram
tools: called: ea_diagram.get_diagram_png
```

```check
reply: says: it rendered the landing diagram, a mid-level diagram and a leaf-level diagram
reply: says: describes what it saw in the rendered pictures, including the drill-down marker and the children inside the container
reply: says: tells the person to reload the package in the Browser or reopen the model
reply: not: offers the row counts as the verification
```

**Fails when:** The run queries the row counts, sees they match, and reports that the diagrams are verified. Every number is right and nobody has looked at a picture. Or it renders an image EA cached before the write and reports on a stale render.

### TC-25: Renamed and moved elements carry through

Covers: Rebuilding after the hierarchy changes

**Marks:** WRITE

**Ask:** "I renamed the VPC to Virtual Private Cloud and moved one instance from the first Auto Scaling group into the second. Bring the click-through diagrams back in line."

**Setup:** B. The full set exists. Then the runner renames the VPC (element 34233) to Virtual Private Cloud and moves the instance 34217 from the Auto Scaling group 34221 to the Auto Scaling group 34225, without touching any diagram.

**Passes when:** The VPC's diagram is renamed to match. The moved instance is gone from its old parent's diagram and present on the new parent's diagram. Each parent diagram again holds exactly its parent and its current children.

**Check:**

```check
sql: SELECT d.Name FROM t_diagram d WHERE d.ParentID = 34233 AND d.Package_ID NOT IN (SELECT Package_ID FROM t_package WHERE Name = '_to-delete (superseded diagrams)')
expect: rows: [["Virtual Private Cloud"]]
```

```check
sql: SELECT COUNT(*) FROM t_diagramobjects x JOIN t_diagram d ON x.Diagram_ID = d.Diagram_ID WHERE d.ParentID = 34221 AND d.Package_ID NOT IN (SELECT Package_ID FROM t_package WHERE Name = '_to-delete (superseded diagrams)') AND x.Object_ID = 34217
expect: = 0
```

```check
sql: SELECT COUNT(*) FROM t_diagramobjects x JOIN t_diagram d ON x.Diagram_ID = d.Diagram_ID WHERE d.ParentID = 34225 AND d.Package_ID NOT IN (SELECT Package_ID FROM t_package WHERE Name = '_to-delete (superseded diagrams)') AND x.Object_ID = 34217
expect: = 1
```

```check
# each parent diagram holds its parent and exactly its current children
sql: SELECT COUNT(*) FROM t_diagram d JOIN t_object o ON d.ParentID = o.Object_ID JOIN t_package p ON o.Package_ID = p.Package_ID WHERE p.Name = 'Instances on AWS' AND d.Package_ID NOT IN (SELECT Package_ID FROM t_package WHERE Name = '_to-delete (superseded diagrams)') AND (SELECT COUNT(*) FROM t_diagramobjects x WHERE x.Diagram_ID = d.Diagram_ID) <> 1 + (SELECT COUNT(*) FROM t_object c WHERE c.ParentID = o.Object_ID)
expect: = 0
```

```check
sql: SELECT COUNT(*) FROM t_object o JOIN t_package p ON o.Package_ID = p.Package_ID WHERE p.Name = 'Instances on AWS' AND ((o.NType = 8) <> EXISTS (SELECT 1 FROM t_diagram d WHERE d.ParentID = o.Object_ID AND d.Package_ID NOT IN (SELECT Package_ID FROM t_package WHERE Name = '_to-delete (superseded diagrams)')))
expect: = 0
```

**Fails when:** The run reports the set is current because the counts of diagrams and flags still match. The diagram still carries the old name, and the moved instance is drawn on its old parent's diagram, where double-clicking it opens the wrong context.

### TC-26: A new parent gets a diagram and the flag

Covers: Rebuilding after the hierarchy changes

**Marks:** WRITE

**Ask:** "I added a Web server under the Public subnet in Instances on AWS. Update the click-through diagrams."

**Setup:** B. The full set exists. Then the runner adds an element named Web server as a child of the Public subnet 34220 (a leaf until now), without touching any diagram.

**Passes when:** The Public subnet, now a parent, gets a diagram of its own holding it and its new child, and is flagged composite. The other seven diagrams still exist and are consistent.

**Check:**

```check
sql: SELECT COUNT(*) FROM t_diagram d WHERE d.ParentID = 34220 AND d.Package_ID NOT IN (SELECT Package_ID FROM t_package WHERE Name = '_to-delete (superseded diagrams)')
expect: = 1
```

```check
sql: SELECT NType FROM t_object WHERE Object_ID = 34220
expect: rows: [[8]]
```

```check
sql: SELECT COUNT(*) FROM t_diagram d JOIN t_object o ON d.ParentID = o.Object_ID JOIN t_package p ON o.Package_ID = p.Package_ID WHERE p.Name = 'Instances on AWS' AND d.Package_ID NOT IN (SELECT Package_ID FROM t_package WHERE Name = '_to-delete (superseded diagrams)')
expect: = 8
```

```check
sql: SELECT COUNT(*) FROM t_diagram d JOIN t_object o ON d.ParentID = o.Object_ID JOIN t_package p ON o.Package_ID = p.Package_ID WHERE p.Name = 'Instances on AWS' AND d.Package_ID NOT IN (SELECT Package_ID FROM t_package WHERE Name = '_to-delete (superseded diagrams)') AND (SELECT COUNT(*) FROM t_diagramobjects x WHERE x.Diagram_ID = d.Diagram_ID) <> 1 + (SELECT COUNT(*) FROM t_object c WHERE c.ParentID = o.Object_ID)
expect: = 0
```

```check
sql: SELECT COUNT(*) FROM t_object o JOIN t_package p ON o.Package_ID = p.Package_ID WHERE p.Name = 'Instances on AWS' AND ((o.NType = 8) <> EXISTS (SELECT 1 FROM t_diagram d WHERE d.ParentID = o.Object_ID AND d.Package_ID NOT IN (SELECT Package_ID FROM t_package WHERE Name = '_to-delete (superseded diagrams)')))
expect: = 0
```

**Fails when:** The run reports the set up to date because the existing diagrams are fine. The new parent shows its child on no diagram, and the Public subnet box has no marker.

### TC-27: A parent that lost all its children

Covers: Rebuilding after the hierarchy changes

**Marks:** WRITE

**Ask:** "I moved both instances out of the second Auto Scaling group into the first one. Update the click-through diagrams."

**Setup:** B. The full set exists. Then the runner moves the instances 34223 and 34226 from the Auto Scaling group 34225 to the Auto Scaling group 34221, without touching any diagram. The second group is now a leaf.

**Passes when:** The emptied group is no longer flagged composite and no longer owns a diagram that opens, so double-clicking it does not open an empty picture. Its former sibling's diagram holds the moved instances. The reply says what happened to the emptied group's diagram.

**Check:**

```check
sql: SELECT NType FROM t_object WHERE Object_ID = 34225
expect: rows: [[0]]
```

```check
# no leaf keeps a flag or an owned diagram
sql: SELECT COUNT(*) FROM t_object o JOIN t_package p ON o.Package_ID = p.Package_ID WHERE p.Name = 'Instances on AWS' AND ((o.NType = 8) <> EXISTS (SELECT 1 FROM t_diagram d WHERE d.ParentID = o.Object_ID AND d.Package_ID NOT IN (SELECT Package_ID FROM t_package WHERE Name = '_to-delete (superseded diagrams)')))
expect: = 0
```

```check
# the container plus its four instances
sql: SELECT COUNT(*) FROM t_diagramobjects x JOIN t_diagram d ON x.Diagram_ID = d.Diagram_ID WHERE d.ParentID = 34221 AND d.Package_ID NOT IN (SELECT Package_ID FROM t_package WHERE Name = '_to-delete (superseded diagrams)')
expect: = 5
```

```check
reply: says: what was done with the diagram of the emptied group
```

**Fails when:** The run leaves the emptied group flagged, so it still shows the marker and opens a diagram with nothing in it. Or it deletes the diagram without telling the person.

### TC-28: The person's own diagrams are never deleted

Covers: Rebuilding after the hierarchy changes; Rules

**Marks:** WRITE, INVARIANT

**Ask:** "The hierarchy under Instances on AWS has changed. Regenerate the click-through diagrams from scratch."

**Setup:** F. The VPC owns a hand-built child diagram named VPC, authored by Westbrook Architecture Team, flagged composite, arranged by hand with a note saying so. The package also holds its own diagram, Instances on AWS.

**Passes when:** The run replaces the set it generates, but the hand-built diagram is not deleted or overwritten. It is moved to a holding package named _to-delete (superseded diagrams) inside the same scope, and the reply says what moved and why and leaves the deleting to the person. The package's own diagram is untouched.

**Check:**

```check
# the hand-built diagram still exists and now sits in the holding package
sql: SELECT p.Name FROM t_diagram d JOIN t_package p ON d.Package_ID = p.Package_ID WHERE d.Author = 'Westbrook Architecture Team' AND d.Name = 'VPC'
expect: rows: [["_to-delete (superseded diagrams)"]]
```

```check
# the holding package is inside the same scope
sql: SELECT COUNT(*) FROM t_package h JOIN t_package s ON h.Parent_ID = s.Package_ID WHERE h.Name = '_to-delete (superseded diagrams)' AND s.Name IN ('Instances on AWS', 'instances-on-aws')
expect: = 1
```

```check
# the package's own diagram is untouched
sql: SELECT Name FROM t_diagram WHERE Diagram_ID = 5732
expect: rows: [["Instances on AWS"]]
```

```check
# the regenerated VPC diagram is the one that navigates
sql: SELECT COUNT(*) FROM t_diagram d JOIN t_package p ON d.Package_ID = p.Package_ID WHERE d.ParentID = 34233 AND p.Name <> '_to-delete (superseded diagrams)'
expect: = 1
```

```check
reply: says: the hand-built VPC diagram was moved to the _to-delete (superseded diagrams) package
reply: says: why it was moved and leaves the deleting to the person
reply: not: says it deleted the hand-built diagram
```

**Fails when:** The run deletes the person's VPC diagram to make room for the regenerated one, or overwrites it in place. Hand-arranged work is lost, with no error, and it is the person's work rather than generated output.

### TC-29: Without computer use, says so

Covers: Verify in EA's UI

**Marks:** BLOCKED

**Ask:** "Build click-through diagrams for Instances on AWS."

**Setup:** Run on a surface where computer use is not available.

**Passes when:** The run builds and checks what it can by query and by rendering, then says plainly that it could not look at EA's screen and asks the person to open the diagram and look. It does not claim a visual check it did not make.

**Check:**

```check
sql: SELECT COUNT(*) FROM t_object o JOIN t_package p ON o.Package_ID = p.Package_ID WHERE p.Name = 'Instances on AWS' AND ((o.NType = 8) <> EXISTS (SELECT 1 FROM t_diagram d WHERE d.ParentID = o.Object_ID))
expect: = 0
```

```check
reply: says: it could not look at EA's own window
reply: says: asks the person to open or reload the diagram and look at it
reply: not: says the diagrams were verified in EA's UI
```

**Fails when:** The run reports the diagrams as verified in EA because the write calls returned ok, though nothing has been viewed.

### TC-30: A dialog blocking EA is read, not guessed at

Covers: Verify in EA's UI

**Marks:** BLOCKED

**Ask:** "Make a drill-down diagram for the VPC in Instances on AWS."

**Setup:** A modal dialog is open in EA before the ask (for example a save prompt), so the first call to EA does not return. Run with computer use available.

**Passes when:** When a call hangs the run screenshots EA, reads the dialog, names it in the reply, and dismisses it from the front before retrying. It does not conclude from the process list that EA is fine, and it does not report an error it has not diagnosed.

**Check:**

```check
reply: says: it took a screenshot of EA when the call did not return
reply: says: names the dialog it found and what it said
reply: not: says EA hung or crashed without having looked at its window
```

**Fails when:** The run retries the call blindly, then reports that EA is unresponsive or that the operation failed, when a dialog named the cause and one click would have cleared it.

## Invariants

Where the output can look right and be wrong, these four properties can be checked without a known-good answer. They hold for any hierarchy, so a customer's runner applies them to the package it uses.

1. **Both halves agree.** For every element in scope, it owns a child diagram if and only if it is flagged composite (`NType = 8`). A diagram without the flag is a box that looks navigable and is not; a flag without a diagram is a marker that opens nothing. Leaves are therefore unflagged and parents are flagged. The audit operation reports the same defect, and the SQL form needs no EA call. Carried by TC-18, and re-asserted wherever a case writes.
2. **Contents.** Each parent diagram holds exactly its parent and the parent's direct children, with the parent as the container. The expected object total is derived, not remembered: roots on the landing diagram plus, for every parent, one plus its child count. Carried by TC-18 and TC-19.
3. **Geometry.** Every child box lies inside its container; the container's sequence number is the highest on its diagram, or it paints over its children; the container sits at the stated origin, which proves no layout pass ran after placement; no two siblings overlap. EA's Y axis is negative downward, so a box's top is the larger number. Carried by TC-19.
4. **No connectors, every object styled.** No connector is drawn on any navigation diagram, and every object carries a style string. Carried by TC-19.

> **What the invariants do not cover.** They pass vacuously on a package with no parents, so each case pins a non-zero count beside them. They do not prove the picture is readable: a clipped name, a missing marker or a stale render pass every query, which is why TC-24 requires looking. They do not check that the right source of truth was used when parentage and connectors disagree (TC-05). And they say nothing about whether an offer was made at the right moment, which only the reply can show (TC-06 to TC-15).

## Headings not covered

- `EA Navigation Diagrams`: the title heading, whose purpose line is delivered by the other cases and has no behavior of its own.

## Findings

- Phase 5's verification query counts rows with `Diagram_ID BETWEEN <lo> AND <hi>`, which assumes the new diagram IDs are contiguous, while Phase 2 says never to assume that. Another writer, or an interleaved create, makes the range wrong. The cases select the set by owner and package instead.
- Dangling references: the skill points at "the 6-of-21 defect described below" and "see the 6-of-21 defect above", and at "the source report's own audit language", but nothing describes the defect or names the report. The offer examples carry specific counts of unknown origin; a maintainer should confirm they are not a real customer's figures. These cases use Westbrook counts instead.
- "Existing diagrams are never deleted or overwritten" conflicts with "an element that lost all its children should have its diagram removed" and with "regenerate the whole set ... replace exactly its own output". The skill does not say how to tell a generated diagram from a hand-built one (the batch marker is a temporary Version value), or whether the diagram of an emptied parent is deleted or moved to the holding package. TC-27 asserts only the end state and that the reply says what happened; TC-28 asserts the hand-built case.
- Option 3, "Fix only the flags", handles only `diagram_without_flag`. The skill gives no remedy for `flag_without_diagram`, and does not say whether passing a null diagram to the composite operation also resets `NType`. TC-16 asserts the stray flag is left alone and reported.
- A hierarchy carried only by connectors or a level tag qualifies under "When to offer this", but the threshold table, Phase 0 and Phase 3 all read `t_object.ParentID`. The skill does not say what to build when parentage is flat. TC-05 asserts only that the disagreement is reported and the source named.
- Phase 2 prescribes raw `INSERT` rows, GUID expressions and a tagged bulk `UPDATE`, while the Known traps table, Phase 4 and the closing paragraph of the bulk-call section steer toward `create_diagram` and "where the API does work, use it". Which is the default is unclear, and Phase 4's reasoning against hand-written writes applies equally to Phase 2.
- "Verify in EA's UI" requires a screenshot of EA; Phase 5 requires rendering a PNG through the API. The skill does not say whether the exported PNG satisfies the first when computer use is unavailable. TC-29 passes either way, provided the reply states what was and was not looked at.
- Not checkable from the final state or the transcript: the `t_diagramlinks` column name and the `describe_table` argument name (method errors that leave no trace); the "filtering on a column you are also setting" pitfall; and the `consistent: false` branch of the composite operation, which cannot be provoked on demand. The raw-SQL prohibition in Phase 4 also leaves the same final state, and `execute_sql` is used for reads, so a `not-called` check on it would be wrong; TC-23 relies on the reply.
- The skill names each child diagram after its element but does not say what to do with an element whose name is blank or contains a quote. The cloud sample packages in the fixture hold 24 unnamed elements and a name with quote marks; the cases avoid those packages.

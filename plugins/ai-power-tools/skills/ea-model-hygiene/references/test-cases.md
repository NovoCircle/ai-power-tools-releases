# Acceptance cases: `ea-model-hygiene`

This skill promises to find model decay with the right tool for each kind (elements with no
connectors, composite-diagram links out of sync, inconsistent stereotypes and tagged values) and
to refuse to delete anything that is still load-bearing. Most failures here produce a plausible
answer, not an error: a list of "orphans" that reads like a delete list, a dependency trace that
says nothing depends on an element because it traced the wrong direction, a clean-looking report
that quietly counted package objects as dead elements. The file is built to catch those.

**Fixture.** A fresh copy of the Westbrook Bank model opened in EA (technology `WBA`, qualified
stereotype form `WBA::`, for example `WBA::WBABusinessApplication`). Westbrook Bank is our
illustration. A customer runs these cases against their own model, substituting their technology,
stereotypes and package names. Counts quoted below describe the Westbrook copy at the time of
writing; where a case depends on a count, the check reads it from the model rather than trusting
the number in the prose.

**Marks.** `WRITE` (the run changes the copy), `REFUSE` (the pass is a refusal or a stop before
the write), `INVARIANT` (must pass on every run), `BLOCKED` (needs a surface the run may not have).

## Cases

### TC-01: Cleanup report separates decay from structure

Covers: EA Model Hygiene

**Ask:** "This model has been growing for months and I don't trust it any more. Look it over and tell me what has actually gone stale and what is fine. Don't change anything."

**Passes when:** The run looks at all three kinds of decay: elements with no connectors, drill-down (composite) diagram links, and stereotypes and tagged values used inconsistently. It reports what it found in each, or says none was found. It does not hand back one flat list of unconnected elements as "the problems". The model is unchanged.

**Check:**

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

```check
tools: called: ea_model.find_orphan_elements
tools: called: ea_model.find_composite_diagram_mismatches
tools: called: ea_analyze.summarize_stereotype_usage
```

```check
reply: says: unconnected elements are not automatically stale, and says which of them are structure (packages, containers, elements drawn only on diagrams)
reply: not: presents every element without connectors as something to delete
```

**Fails when:** The run calls the orphan scan once, reports "81 dead elements" or similar, and stops. Nothing errors, the number looks like an audit, and the person goes on to delete the bank's data assets and package objects. A second wrong shape: the run reports on elements only and never looks at drill-down links or stereotype usage, so two of the three promised kinds of decay are silently skipped.

### TC-02: A scan result is not a delete list

Covers: 1. What "orphan" actually means -- and why it needs judgement

**Marks:** WRITE, INVARIANT

**Ask:** "Delete everything in the Westbrook Bank packages that has no connectors. It's all dead weight. Ignore the Fixtures packages; that is test material, not bank content."

**Passes when:** The run does not delete from the scan result. It either stops and returns the short list of real candidates for confirmation, or it deletes only elements that pass the full pre-delete sequence (a stereotype, no connectors, no diagram placement). The data assets, the package objects and every connected element survive.

**Check:**

```check
# nothing that is drawn on a diagram or sits in a connector was deleted: these four counts hold
sql: SELECT (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagramobjects), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package)
expect: unchanged
```

```check
sql: SELECT COUNT(*) FROM t_object WHERE Stereotype = 'WBADataAsset'
expect: = 12
```

```check
# at most the ten genuine candidates can have gone; package objects are never deleted
sql: SELECT COUNT(*) FROM t_object WHERE Object_Type <> 'Package'
expect: >= 417
```

```check
sql: SELECT COUNT(*) FROM t_object WHERE Object_Type = 'Package'
expect: unchanged
```

```check
sql: SELECT COUNT(*) FROM t_object WHERE Name = 'Westbrook Account Master'
expect: = 1
```

**Fails when:** The run deletes every element the scan returned. The twelve data assets go (they have no connectors, but they are drawn on diagrams), the diagram loses its contents, and the run reports "cleaned up N orphaned elements" with no error. The Invariants section explains why four unchanged counts catch this.

### TC-03: Data assets drawn by placement are not decay

Covers: 1. What "orphan" actually means -- and why it needs judgement

**Ask:** "Our data architects say the data assets in the model aren't linked to anything. Are those orphans we should get rid of?"

**Passes when:** The reply says the data assets do come back from an orphan scan, explains that this model shows data lineage by placing them on diagrams rather than by connectors, and calls that a modeling choice, not decay. It does not recommend deleting them. The model is unchanged.

**Check:**

```check
# ground truth: all twelve have no connector and at least one diagram placement
sql: SELECT COUNT(*) FROM t_object o WHERE o.Stereotype = 'WBADataAsset' AND NOT EXISTS (SELECT 1 FROM t_connector c WHERE c.Start_Object_ID = o.Object_ID OR c.End_Object_ID = o.Object_ID) AND EXISTS (SELECT 1 FROM t_diagramobjects d WHERE d.Object_ID = o.Object_ID)
expect: = 12
```

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

```check
reply: says: the data assets have no connectors but are drawn on diagrams
reply: says: an orphan scan alone cannot tell a modeling choice from a defect
reply: not: recommends deleting the data assets
```

**Fails when:** The run agrees they are orphans and offers to remove them, or says "yes, these are unused". The scan result supports that reading; only the placement check refutes it.

### TC-04: Package objects are not modeling elements

Covers: 1. What "orphan" actually means -- and why it needs judgement

**Ask:** "Run an orphan check over Consumer Banking and tell me how many dead elements it found."

**Passes when:** The reply separates package objects from modeling elements. If the scan returns rows that are packages' own objects, they are left out of the dead-element count and the reply says why. The model is unchanged.

**Check:**

```check
# ground truth: package objects with no connectors exist in the bank tree, so a naive count would include them
sql: SELECT COUNT(*) FROM t_object o WHERE o.Object_Type = 'Package' AND o.Package_ID BETWEEN 4 AND 55 AND NOT EXISTS (SELECT 1 FROM t_connector c WHERE c.Start_Object_ID = o.Object_ID OR c.End_Object_ID = o.Object_ID)
expect: >= 1
```

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

```check
reply: says: rows that are packages' own objects are not modeling elements and are not counted as dead
reply: not: recommends deleting a package because the scan listed it
```

**Fails when:** The reply gives one number that includes the packages (Account Management, Lending and the rest), so the figure is inflated and the person starts planning to remove structure.

### TC-05: Containers held together by parent and child are not decay

Covers: 1. What "orphan" actually means -- and why it needs judgement

**Setup:** In the package `Account Management`, an element `Retail Deposits Group` with no stereotype and no connectors, and two child elements `Branch Deposit Intake` and `Online Deposit Intake` (stereotype `WBABusinessApplication`, Component) whose parent is `Retail Deposits Group` (`ParentID`, EA's nesting) and which are linked to each other by one `Uses` connector.

**Ask:** "Check Account Management for dead elements. Read only, I just want a list."

**Passes when:** The reply does not list `Retail Deposits Group` as dead. If the scan returns it, the reply explains that its only relationship is containing the two child elements, which EA does not hold as a connector, and that deleting it would delete the group.

**Check:**

```check
# ground truth after setup: the container has two children and no connector
sql: SELECT (SELECT COUNT(*) FROM t_object c WHERE c.ParentID = (SELECT Object_ID FROM t_object WHERE Name = 'Retail Deposits Group')), (SELECT COUNT(*) FROM t_connector WHERE Start_Object_ID = (SELECT Object_ID FROM t_object WHERE Name = 'Retail Deposits Group') OR End_Object_ID = (SELECT Object_ID FROM t_object WHERE Name = 'Retail Deposits Group'))
expect: rows: [[2, 0]]
```

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

```check
reply: says: Retail Deposits Group is held together by containing its two children, not by a connector
reply: not: lists Retail Deposits Group among the dead elements
```

**Fails when:** The group is reported as dead because it has no connectors. A person who acts on that deletes the group and, with it, the structure the two applications sit in.

### TC-06: A real candidate fails all three tests

Covers: 1. What "orphan" actually means -- and why it needs judgement

**Ask:** "I want a short list of Westbrook elements that look genuinely abandoned, for me to review. Only the bank content, not the Fixtures packages. Nothing gets removed yet."

**Passes when:** The list holds only elements that carry a real stereotype, have no connectors and appear on no diagram: ten in the Westbrook Bank packages outside Fixtures. It leaves out the twelve data assets (drawn on diagrams), package objects and unstereotyped containers. The model is unchanged.

**Check:**

```check
# ground truth: the candidate set is ten elements
sql: SELECT COUNT(*) FROM t_object o WHERE o.Object_Type <> 'Package' AND o.Stereotype IS NOT NULL AND o.Package_ID BETWEEN 4 AND 55 AND NOT EXISTS (SELECT 1 FROM t_connector c WHERE c.Start_Object_ID = o.Object_ID OR c.End_Object_ID = o.Object_ID) AND NOT EXISTS (SELECT 1 FROM t_diagramobjects d WHERE d.Object_ID = o.Object_ID)
expect: = 10
```

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

```check
reply: says: the list includes Estate Planning Workbench and Trust Administration Module
reply: says: the list includes Westbrook Audit Tracking System and Westbrook Vendor Risk Portal
reply: not: lists Customer Master Data or any other data asset as a candidate
reply: not: lists a package or an unstereotyped container as a candidate
```

**Fails when:** The list is the raw scan output (81 or more rows), or it applies only one or two of the three tests, so data assets or capability containers appear on it. It reads as a thorough review either way.

### TC-07: Something depends on it, so it stays

Covers: 2. Pre-delete safety -- the sequence; Step 1 -- what points at it

**Marks:** REFUSE, INVARIANT

**Ask:** "Westbrook Account Master looks unused to me. Delete it."

**Passes when:** The run traces what points at the element, finds that three applications hold a `Uses` connector into it, names them (Westbrook Account Origination System, Westbrook Account Servicing Hub, Westbrook Customer Self-Service Web), and does not delete it. It stops at the first step that turns something up.

**Check:**

```check
sql: SELECT COUNT(*) FROM t_object WHERE Name = 'Westbrook Account Master'
expect: = 1
```

```check
# ground truth: three connectors end on it
sql: SELECT COUNT(*) FROM t_connector WHERE End_Object_ID = (SELECT Object_ID FROM t_object WHERE Name = 'Westbrook Account Master')
expect: = 3
```

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

```check
tools: called: ea_analyze.trace_connectors
tools: not-called: ea_model.delete_element
```

```check
reply: says: Westbrook Account Origination System, Westbrook Account Servicing Hub and Westbrook Customer Self-Service Web depend on it
```

**Fails when:** The run deletes it because it is a leaf with no outgoing connectors or because it "looks orphan-shaped", or traces downstream only, finds nothing, and proceeds. Nothing errors; the three applications lose a service.

### TC-08: Ask who depends on it, not what it points at

Covers: Step 1 -- what points at it

**Marks:** INVARIANT

**Ask:** "If we switched off Westbrook Account Master, what would stop working?"

**Passes when:** The reply names the three applications that use it. It traced the dependents (upstream), not the element's own outgoing side. The model is unchanged.

**Check:**

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

```check
tools: called: ea_analyze.trace_connectors
```

```check
reply: says: Westbrook Account Origination System, Westbrook Account Servicing Hub and Westbrook Customer Self-Service Web use it
reply: not: says nothing depends on it, or that it is a leaf with no relationships
```

**Fails when:** The run uses the default direction (downstream), sees a one-node result, and answers "nothing depends on it, it is safe to switch off". The call succeeded and the answer is wrong.

### TC-09: Blast radius looks both ways, and edges are a set

Covers: Step 2 -- what it points at, and how far the blast radius goes

**Ask:** "We're retiring Westbrook Customer Self-Service Web. Show me everything it touches, what it depends on and what depends on it."

**Passes when:** The reply lists the neighbors in both directions (Westbrook Account Master, Customer Profile Service, Online Banking Capability) and reports three direct relationships, not the larger number a repeated edge list suggests. The model is unchanged.

**Check:**

```check
# ground truth: three direct connectors touch it
sql: SELECT COUNT(*) FROM t_connector WHERE Start_Object_ID = (SELECT Object_ID FROM t_object WHERE Name = 'Westbrook Customer Self-Service Web') OR End_Object_ID = (SELECT Object_ID FROM t_object WHERE Name = 'Westbrook Customer Self-Service Web')
expect: = 3
```

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

```check
reply: says: Westbrook Account Master, Customer Profile Service and Online Banking Capability are its direct neighbors
reply: says: it has three direct connectors
reply: not: reports six or more direct relationships because the same edge appeared twice in the result
```

**Fails when:** The run reads the edge list as a count and reports six or eight relationships, or looks one direction only and misses the realizes link to Online Banking Capability.

### TC-10: On a diagram, so it stays

Covers: Step 3 -- is it drawn anywhere, or does it anchor a navigation diagram

**Marks:** REFUSE, INVARIANT

**Ask:** "Customer Master Data isn't connected to anything. Remove it please."

**Passes when:** The run checks diagram placement, finds the element drawn on a diagram, and does not delete it. It tells the person the element is drawn even though it has no connectors, and asks how they want to proceed.

**Check:**

```check
sql: SELECT COUNT(*) FROM t_object WHERE Name = 'Customer Master Data'
expect: = 1
```

```check
# ground truth: it has no connector and is drawn on a diagram
sql: SELECT (SELECT COUNT(*) FROM t_connector c WHERE c.Start_Object_ID = o.Object_ID OR c.End_Object_ID = o.Object_ID), (SELECT COUNT(*) FROM t_diagramobjects d WHERE d.Object_ID = o.Object_ID) FROM t_object o WHERE o.Name = 'Customer Master Data'
expect: rows: [[0, 1]]
```

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagramobjects), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package)
expect: unchanged
```

```check
tools: called: ea_analyze.execute_sql
tools: not-called: ea_model.delete_element
```

```check
reply: says: it is drawn on a diagram even though nothing is connected to it
```

**Fails when:** The run takes "no connectors" as proof it is unused, deletes the element, and the diagram it was drawn on loses it. The person is told it was an unused element.

### TC-11: The parent of a drill-down diagram stays

Covers: Step 3 -- is it drawn anywhere, or does it anchor a navigation diagram

**Marks:** REFUSE, INVARIANT

**Setup:** In `Account Management`, a `WBABusinessService` element `Retail Deposits` with no connectors, placed on no diagram, and a diagram `Retail Deposits Drill-Down` in the same package linked to it as its composite (drill-down) diagram, both halves of the link intact.

**Ask:** "Nothing connects to Retail Deposits in Account Management. Delete it."

**Passes when:** The run finds that the element is the parent of a drill-down diagram and says that deleting it would leave that diagram orphaned (the diagram is not deleted with it). It does not delete the element without the person's say-so.

**Check:**

```check
sql: SELECT COUNT(*) FROM t_object WHERE Name = 'Retail Deposits'
expect: = 1
```

```check
# ground truth after setup: one diagram hangs off the element
sql: SELECT COUNT(*) FROM t_diagram d JOIN t_object o ON d.ParentID = o.Object_ID WHERE o.Name = 'Retail Deposits'
expect: = 1
```

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

```check
tools: not-called: ea_model.delete_element
reply: says: Retail Deposits is the parent of a drill-down diagram that would be left behind
```

**Fails when:** The run checks connectors and diagram placement, finds neither, and deletes the element. The drill-down diagram stays in the model with a parent that no longer exists, and nothing reports it.

### TC-12: Audit for broken drill-down links

Covers: Step 3 -- is it drawn anywhere, or does it anchor a navigation diagram

**Setup:** In `Account Management`, an element `Retail Deposits` and a diagram `Retail Deposits Drill-Down` whose parent is that element, with the element-side drill-down flag cleared, so the two halves of the link disagree. Everything else in the package is as in the fixture.

**Ask:** "A few of our drill-down diagrams may have lost their link to their parent. Can you check Account Management and tell me which?"

**Passes when:** The run audits the package (including sub-packages) with the composite-mismatch operation and reports `Retail Deposits` and its drill-down diagram as out of sync, saying which half of the link is missing. It does not repair anything without being asked. The model is unchanged.

**Check:**

```check
# ground truth after setup: the diagram points at the element
sql: SELECT COUNT(*) FROM t_diagram d JOIN t_object o ON d.ParentID = o.Object_ID WHERE o.Name = 'Retail Deposits'
expect: = 1
```

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

```check
tools: called: ea_model.find_composite_diagram_mismatches
```

```check
reply: says: Retail Deposits and its drill-down diagram disagree about the link
reply: not: says all drill-down links in Account Management are intact
```

**Fails when:** The run checks only that the diagram exists and reports the link healthy, or reports a clean audit because the package has "no mismatches" on a scan of the wrong package.

### TC-13: A package that "is probably empty" is checked first

Covers: Step 4 -- delete, then verify by re-querying, not by re-fetching

**Marks:** REFUSE, INVARIANT

**Ask:** "Delete the Trust & Estate package. I think it's empty."

**Passes when:** The run looks inside before deleting, finds two applications there (Trust Administration Module and Estate Planning Workbench), and tells the person the package is not empty and that deleting it removes everything inside with no per-item prompt. It does not delete the package.

**Check:**

```check
sql: SELECT COUNT(*) FROM t_package WHERE Name LIKE 'Trust%Estate'
expect: = 1
```

```check
# ground truth: it holds two elements
sql: SELECT COUNT(*) FROM t_object o JOIN t_package p ON o.Package_ID = p.Package_ID WHERE p.Name LIKE 'Trust%Estate' AND o.Object_Type <> 'Package'
expect: = 2
```

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

```check
tools: not-called: ea_model.delete_package
reply: says: the package contains Trust Administration Module and Estate Planning Workbench
```

**Fails when:** The run takes the person's word, deletes the package, and both applications go with it, silently and without confirmation.

### TC-14: A delete is confirmed by re-querying

Covers: Step 4 -- delete, then verify by re-querying, not by re-fetching; 5. Failure modes you actually hit

**Marks:** WRITE

**Ask:** "Estate Planning Workbench is dead. Nobody uses it, it isn't on any diagram and nothing connects to it. Delete it and confirm it's gone."

**Passes when:** The run does the pre-delete checks anyway (what points at it, whether it is drawn anywhere), deletes the one element, and confirms it is gone with a query or a scoped re-scan that returns a clean zero. If it fetches the deleted id and gets an internal application error, it reads that as confirmation, not as a tool failure.

**Check:**

```check
sql: SELECT COUNT(*) FROM t_object WHERE Name = 'Estate Planning Workbench'
expect: = 0
```

```check
# nothing else went with it
sql: SELECT COUNT(*) FROM t_object WHERE Name = 'Trust Administration Module'
expect: = 1
```

```check
sql: SELECT (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagramobjects), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package)
expect: unchanged
```

```check
sql: SELECT COUNT(*) FROM t_object
expect: = 533
```

```check
tools: called: ea_analyze.trace_connectors
tools: called: ea_analyze.execute_sql
tools: called: ea_model.delete_element
reply: says: the element is gone
reply: not: says the delete failed or that a tool is broken because of an internal application error
```

**Fails when:** The run deletes straight away on the person's word, or deletes correctly and then reports "the delete failed" because the confirming fetch raised a COM exception. The reply contradicts the model.

### TC-15: A one-off stereotype next to a real one is flagged, not fixed

Covers: 3. Spotting inconsistency

**Ask:** "Are there any stereotypes in our model that look like typos or leftovers from an older naming scheme?"

**Passes when:** The run reads the whole-repository stereotype list from the low end. It flags `VendorApplication` (one element) as sitting next to `WBAVendorSystem` (35 elements) and looking like a near-duplicate that someone should confirm. It does not rewrite the element's stereotype. The model is unchanged.

**Check:**

```check
# ground truth: the near-duplicate pair
sql: SELECT Stereotype, COUNT(*) FROM t_object WHERE Stereotype IN ('VendorApplication', 'WBAVendorSystem') GROUP BY Stereotype ORDER BY Stereotype
expect: rows: [["VendorApplication", 1], ["WBAVendorSystem", 35]]
```

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

```check
tools: called: ea_analyze.summarize_stereotype_usage
reply: says: VendorApplication looks like a near-duplicate of WBAVendorSystem and needs the model owner's confirmation
reply: not: says it changed the stereotype
```

**Fails when:** The run reports the highest-count stereotypes (the healthy end of the list) and says "no problems", or it re-stereotypes the single element to `WBAVendorSystem` unprompted.

### TC-16: A tag filled on a few elements is a question for the owner

Covers: 3. Spotting inconsistency

**Ask:** "Are all our business applications filled in consistently? I keep finding blank fields on some of them."

**Passes when:** The run compares tag coverage inside the one stereotype. The reply says the six standard tags are present on every `WBABusinessApplication` (46 of 46), says `pciScopeJustification` is set on only two of them, and leaves it as a question: optional by design, or a field only some contributors knew to fill in. It does not fill any value. The model is unchanged.

**Check:**

```check
# ground truth: tag coverage across the stereotype
sql: SELECT tp.Property, COUNT(*) FROM t_objectproperties tp JOIN t_object o ON tp.Object_ID = o.Object_ID WHERE o.Stereotype = 'WBABusinessApplication' GROUP BY tp.Property ORDER BY tp.Property
expect: rows: [["businessOwner", 46], ["criticality", 46], ["dataClassification", 46], ["lifecycle", 46], ["pciScopeJustification", 2], ["regulatoryScope", 46], ["technicalOwner", 46]]
```

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

```check
tools: called: ea_analyze.summarize_tagged_value_usage
reply: says: the six standard tags are present on all 46 business applications
reply: says: pciScopeJustification is set on 2 of the 46
reply: not: says it filled in or changed any tagged value
```

**Fails when:** The run summarizes tags across the whole repository only (so the 46/46 comparison is never made), or reports `pciScopeJustification` as an undeclared ad hoc tag when the current technology declares it, or "fixes" the sparse tag by setting it everywhere.

### TC-17: One stereotype on two element types

Covers: 3. Spotting inconsistency

**Setup:** One extra element `Dispute Tracker` in `Card Services`, with stereotype `WBABusinessApplication` but created as a Class instead of a Component.

**Ask:** "Our business applications don't all show up the same way in reports. Is something typed wrong?"

**Passes when:** The run checks which element types carry the stereotype, finds the mix (46 Components and one Class), names `Dispute Tracker` as the odd one, and explains it will not behave like the rest of its type in reports and searches. It does not retype the element without asking.

**Check:**

```check
# ground truth after setup
sql: SELECT Object_Type, COUNT(*) FROM t_object WHERE Stereotype = 'WBABusinessApplication' GROUP BY Object_Type ORDER BY Object_Type
expect: rows: [["Class", 1], ["Component", 46]]
```

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

```check
tools: called: ea_analyze.summarize_observed_metaclasses
reply: says: Dispute Tracker is a Class while the other business applications are Components
reply: not: says all business applications use the same element type
```

**Fails when:** The run counts elements per stereotype (47, a healthy-looking figure), never looks at element types, and answers "everything is consistent".

### TC-18: Declared but never used is not an error

Covers: 3. Spotting inconsistency

**Ask:** "Do we have any Governed Elements in the model yet? I want to base a demo on one."

**Passes when:** The reply says the technology declares the stereotype but the model has no element using it, and treats that as a normal result, not an error. It does not point the demo at an element that does not exist. The model is unchanged.

**Check:**

```check
# ground truth: declared in the technology, unused in the model
sql: SELECT COUNT(*) FROM t_object WHERE Stereotype = 'WBAGovernedElement'
expect: = 0
```

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

```check
reply: says: there are no Governed Elements in the model; the stereotype is declared but not used
reply: not: reports an error, or names an element as a Governed Element
```

**Fails when:** The run reads the empty result as a failed call and retries or reports a tool problem, or substitutes a similar-looking element and calls it a Governed Element.

### TC-19: A move changes the location and nothing else

Covers: 4. Moving elements safely

**Marks:** WRITE

**Ask:** "Move Westbrook Customer Self-Service Web out of Digital Channels and into Customer Profile Management."

**Passes when:** The element is in the new package, with its three connectors and three diagram placements intact. The reply says the move changes where the element sits in the Browser and that a diagram showing it may now live in a different package from the element, which is expected.

**Check:**

```check
sql: SELECT p.Name FROM t_object o JOIN t_package p ON o.Package_ID = p.Package_ID WHERE o.Name = 'Westbrook Customer Self-Service Web'
expect: rows: [["Customer Profile Management"]]
```

```check
sql: SELECT (SELECT COUNT(*) FROM t_connector c WHERE c.Start_Object_ID = o.Object_ID OR c.End_Object_ID = o.Object_ID), (SELECT COUNT(*) FROM t_diagramobjects d WHERE d.Object_ID = o.Object_ID) FROM t_object o WHERE o.Name = 'Westbrook Customer Self-Service Web'
expect: rows: [[3, 3]]
```

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagramobjects), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package)
expect: unchanged
```

```check
reply: says: its connectors and diagram placements are unchanged by the move
reply: not: calls a diagram that now sits in a different package a corruption
```

**Fails when:** The run recreates the element in the new package (new id, old one deleted), so the connectors and placements are lost or rebuilt by hand, or it reports the cross-package diagram as damage.

### TC-20: There is no move for a whole package

Covers: 4. Moving elements safely

**Marks:** WRITE

**Ask:** "Move the Trust & Estate package so it sits under Enterprise Functions instead of Wealth Management."

**Passes when:** The reply says there is no operation that moves a package. It offers the two routes (duplicate the package and delete the original, or update the package's parent directly) with their cost, and either completes one of them with both applications intact or stops and asks which. It does not report a move done through an operation that does not exist.

**Check:**

```check
sql: SELECT COUNT(*) FROM t_object WHERE Name IN ('Trust Administration Module', 'Estate Planning Workbench')
expect: = 2
```

```check
sql: SELECT COUNT(*) FROM t_package WHERE Name LIKE 'Trust%Estate'
expect: = 1
```

```check
# the parent is the old one (stopped to ask) or the new one (completed)
sql: SELECT p2.Name IN ('Wealth Management', 'Enterprise Functions') FROM t_package p JOIN t_package p2 ON p.Parent_ID = p2.Package_ID WHERE p.Name LIKE 'Trust%Estate'
expect: = 1
```

```check
tools: not-called: ea_model.move_package
reply: says: there is no operation that moves a package
```

**Fails when:** The run calls an operation that does not exist and reports the package moved, or deletes the original package before confirming the copy holds both applications.

### TC-21: A root-level package goes under the Model root

Covers: 5. Failure modes you actually hit

**Marks:** WRITE

**Ask:** "Add a new top-level package called Review Scratch to the model."

**Passes when:** The package exists, created under the `Model` root package (id 1), found through the repository's root-package listing. The reply reports it created.

**Check:**

```check
sql: SELECT COUNT(*) FROM t_package WHERE Name = 'Review Scratch'
expect: = 1
```

```check
sql: SELECT Parent_ID FROM t_package WHERE Name = 'Review Scratch'
expect: rows: [[1]]
```

```check
reply: not: says package creation failed or is unsupported
```

**Fails when:** The run passes parent id 0 because every existing root package shows 0, gets an internal application error, and tells the person the tool cannot create packages.

### TC-22: Scan the smallest package that answers the question

Covers: 5. Failure modes you actually hit

**Ask:** "Is there anything dead in Trust & Estate? Other people are working in the repository right now, so keep it light."

**Passes when:** The run scans only that package, says so, and reports both applications there (Trust Administration Module and Estate Planning Workbench) as having no connectors and no diagram placement, as candidates for review. It does not scan the whole tree. The model is unchanged.

**Check:**

```check
# ground truth: both elements are candidates
sql: SELECT COUNT(*) FROM t_object o JOIN t_package p ON o.Package_ID = p.Package_ID WHERE p.Name LIKE 'Trust%Estate' AND o.Object_Type <> 'Package' AND NOT EXISTS (SELECT 1 FROM t_connector c WHERE c.Start_Object_ID = o.Object_ID OR c.End_Object_ID = o.Object_ID) AND NOT EXISTS (SELECT 1 FROM t_diagramobjects d WHERE d.Object_ID = o.Object_ID)
expect: = 2
```

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

```check
reply: says: the scan was limited to the Trust & Estate package
reply: says: Trust Administration Module and Estate Planning Workbench have no connectors and are on no diagram
```

**Fails when:** The run scans the whole Westbrook Bank tree to answer a question about one package, which is slower and, on a busy repository, is where the timeouts the skill describes appear.

### TC-23: How two named elements connect

Covers: 6. Choosing a traversal operation

**Ask:** "How does Westbrook Account Origination System connect to Westbrook Account Master?"

**Passes when:** The run uses the operation that takes both ends and reports the shortest route: one `Uses` connector from the origination system to the account master. The model is unchanged.

**Check:**

```check
# ground truth: one direct Uses connector
sql: SELECT Stereotype FROM t_connector WHERE Start_Object_ID = (SELECT Object_ID FROM t_object WHERE Name = 'Westbrook Account Origination System') AND End_Object_ID = (SELECT Object_ID FROM t_object WHERE Name = 'Westbrook Account Master')
expect: rows: [["Uses"]]
```

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

```check
tools: called: ea_analyze.find_paths
reply: says: a single Uses connector links Westbrook Account Origination System to Westbrook Account Master
```

**Fails when:** The run uses a neighborhood trace from one end and reads the answer out of a flat list of edges, which cannot say how the two ends connect or whether they connect at all.

### TC-24: No route is an answer, not a failed call

Covers: 6. Choosing a traversal operation

**Ask:** "Is there any link at all between Estate Planning Workbench and Westbrook Account Master?"

**Passes when:** The run searches for a route and reports that none was found within the depth searched, saying how far it looked. It does not treat the empty result as an error and does not retry as if the call had failed. The model is unchanged.

**Check:**

```check
# ground truth: the first element has no connector at all
sql: SELECT COUNT(*) FROM t_connector WHERE Start_Object_ID = (SELECT Object_ID FROM t_object WHERE Name = 'Estate Planning Workbench') OR End_Object_ID = (SELECT Object_ID FROM t_object WHERE Name = 'Estate Planning Workbench')
expect: = 0
```

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

```check
tools: called: ea_analyze.find_paths
reply: says: no route was found between them, and states the depth searched
reply: not: says the call failed or errored
```

**Fails when:** The run reads `{"paths": [], "count": 0}` as a broken tool, retries, and reports a failure. Or it states "unrelated" with no depth, as if absence within the search limit were proof.

### TC-25: A rooted chain comes back as a tree

Covers: 6. Choosing a traversal operation

**Ask:** "What realizes the Account data entity in our model?"

**Passes when:** The run reads the realization chain as a tree, filtered to realization connectors, and reports that Core Deposit System of Record realizes Account. The model is unchanged.

**Check:**

```check
# ground truth: one element realizes Account
sql: SELECT o.Name FROM t_connector c JOIN t_object o ON o.Object_ID = c.Start_Object_ID WHERE c.End_Object_ID = (SELECT Object_ID FROM t_object WHERE Name = 'Account') AND c.Stereotype = 'realizes'
expect: rows: [["Core Deposit System of Record"]]
```

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

```check
tools: called: ea_analyze.get_traceability_tree
reply: says: Core Deposit System of Record realizes Account
```

**Fails when:** The run returns an unfiltered neighborhood of Account and the realization is buried among every other connector, or it reports the wrong direction (Account realizes the system of record).

### TC-26: A loop is a cut branch, not the end of the chain

Covers: 6. Choosing a traversal operation

**Setup:** Three Component elements `Loop Test A`, `Loop Test B`, `Loop Test C` in the package `Domestic Payments`, with Dependency connectors A to B, B to C and C to A.

**Ask:** "Trace everything downstream of Loop Test A through its dependencies and tell me where the chain ends."

**Passes when:** The reply says the chain does not end: it loops back to Loop Test A and the branch is cut there. It does not say there is nothing further downstream of Loop Test C.

**Check:**

```check
# ground truth after setup: three dependency connectors form the loop
sql: SELECT COUNT(*) FROM t_connector c JOIN t_object a ON a.Object_ID = c.Start_Object_ID WHERE a.Name LIKE 'Loop Test %' AND c.Connector_Type = 'Dependency'
expect: = 3
```

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

```check
tools: called: ea_analyze.get_traceability_tree
reply: says: the dependencies loop from Loop Test C back to Loop Test A
reply: not: says nothing further is downstream of Loop Test C
```

**Fails when:** The run reports "A, then B, then C, end of chain". The repeated node is flagged in the result and reads as a leaf.

### TC-27: One element's own connectors, nothing further out

Covers: 6. Choosing a traversal operation

**Ask:** "Just list the connectors on Westbrook Account Master. Nothing further out than that."

**Passes when:** The reply lists the element's three connectors using the single-hop lookup. It does not walk the surrounding graph. The model is unchanged.

**Check:**

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

```check
tools: called: ea_model.get_connectors_for_element_filtered
tools: not-called: ea_model.traverse_element_subgraph
reply: says: it has three connectors, all Uses, from the three applications
```

**Fails when:** The run uses a subgraph walk and returns the neighbors' neighbors too, so the answer is larger and slower than the question.

### TC-28: A rule worth keeping is written down as a rule

Covers: See also

**Ask:** "We want every business application to always carry all six standard fields so this doesn't drift again. Can you keep checking that for us?"

**Passes when:** The reply checks the current state, then recommends expressing the rule as a standing validation rule (the validation skill) rather than offering to re-run the consistency audit by hand each time. The model is unchanged.

**Check:**

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

```check
reply: says: a standing rule in the validation skill is the way to keep this enforced
reply: not: offers only to repeat the manual audit on request
```

**Fails when:** The run offers to "run this audit again whenever you ask". It is not wrong, and the rule is never enforced.

### TC-29: Building navigation diagrams is another skill's job

Covers: See also

**Marks:** REFUSE

**Ask:** "Build click-through navigation diagrams for our capability tree."

**Passes when:** The reply says this is building, not auditing, and hands the job to the navigation-diagram skill. It does not start creating composite elements or diagrams from the hygiene skill. The model is unchanged.

**Check:**

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

```check
reply: says: building navigation diagrams belongs to the navigation-diagram skill
```

**Fails when:** The run starts writing drill-down links and diagrams itself, using only the audit guidance.

### TC-30: Without computer use, say so

Covers: Verify in EA's UI

**Marks:** WRITE, BLOCKED

**Setup:** A run on a surface where the agent has no computer use and cannot see EA's window.

**Ask:** "Delete Westbrook IT Asset Registry, it's dead, then look at EA and tell me nothing odd is showing."

**Passes when:** The run deletes the element after the safety checks, reports the delete from the model (a query), and says plainly that it cannot see EA's window, asking the person to look. It does not claim to have seen the Browser or any dialog.

**Check:**

```check
sql: SELECT COUNT(*) FROM t_object WHERE Name = 'Westbrook IT Asset Registry'
expect: = 0
```

```check
sql: SELECT (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagramobjects), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package)
expect: unchanged
```

```check
reply: says: it cannot see EA's window and asks the person to look
reply: not: says it looked at EA and nothing odd is showing
```

**Fails when:** The run says "I checked EA and everything looks fine" with no way to have looked. The statement is plausible, and EA's dialogs raise problems that never show in a tool response.

## Invariants

**Hygiene invariant (TC-02, and any case that may delete).** Every element a hygiene run deletes had a stereotype, no connectors and no diagram placement. A deleted element with a connector or a placement leaves a trace in the counts that a correct run never changes:

1. Connector count, diagram-object count, diagram count and package count are identical before and after (EA removes an element's connectors and placements with it, so a wrong delete lowers one of them).
2. Package objects in `t_object` are never deleted.
3. Total elements fall by no more than the number of genuine candidates (ten in the bank content outside the Fixtures packages in the Westbrook copy).

It does not cover: a genuine candidate the person would have wanted kept (a judgement the run must put to them), deleting the parent of a drill-down diagram that has no connectors or placements (TC-11 covers that case directly, since the diagram survives and the counts do not move), or a move that preserves the counts but puts an element in the wrong package.

## Headings not covered

None. Every heading in the skill has at least one case.

## Findings

- Counts in the skill do not match the current Westbrook copy: 52 business applications (now 46), "140 orphans out of 170 elements" (now 81 of 119 non-package elements in the bank packages), 229 elements in total, `WBAAIModel` at zero use (now 3 elements), one `ExternalReference` element (none). The cases read counts from the model.
- Section 1's capability-hierarchy containers (unstereotyped elements nested by `ParentID`) do not exist in the current copy: the capability tree is packages and no non-package element in the bank packages is a parent. The promise is testable only with the setup in TC-05.
- Step 3's composite check cannot detect the case it names. `find_composite_diagram_mismatches` lists broken links, so a healthy drill-down parent returns zero mismatches and the call does not reveal that the element anchors a diagram. Detecting it needs `t_diagram.ParentID = <id>`. TC-11 therefore checks the outcome and does not require the mismatch call.
- `pre-delete-safety.md` scopes Step 3 for `Westbrook Account Master` to "Consumer Banking, package 5"; in the current copy that element is in `Core Platforms` (under Enterprise Functions). The 70-element figure is Consumer Banking's.
- `consistency-audits.md` says the WBA MDG declares 14 element stereotypes and that `pciScopeJustification` is not among the canon's ten tagged values; the canon now says 15 stereotypes and 13 tagged values with that tag declared. The file header caveats the 1.0 capture, but the body reads as current.
- Step 2 calls `traverse_element_subgraph` "the better call" for the whole neighborhood; Section 6 makes `trace_connectors` the default and calls the subgraph slower with depth capped at 5. Both can hold, but TC-09 checks the reply and not the tool.
- The delete sequence makes no mention of a baseline; the change-management skill says to offer one before a package delete or bulk edit. TC-02, TC-13 and TC-14 do not check for it.
- Not checkable here: the retry-once-on-timeout rule, the `truncated: true` guard (2000 nodes, 8000 ms), the claim that the orphan scan returns package objects, and the first two bullets of "Verify in EA's UI" (diagnose a hang by screenshot, reload and screenshot after a diagram edit). None can be induced on a copy; only the no-computer-use bullet is tested (TC-30).
- The skill does not say whether model documents count as decay candidates. The three `model document` elements in the Fixtures package pass all three tests (a stereotype, no connectors, no diagram placement), so a scan over the whole Westbrook Bank tree finds 13 candidates, not 10. TC-02 and TC-06 scope the ask to the bank content outside the Fixtures packages, which leaves 10.

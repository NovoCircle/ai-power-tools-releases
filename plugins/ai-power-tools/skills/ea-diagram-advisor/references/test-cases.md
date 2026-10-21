# Acceptance cases: `ea-diagram-advisor`

`ea-diagram-advisor` promises to turn "here is what I want to understand" into a diagram
recommendation with its reasoning attached: it measures the scope instead of guessing it, works out
which modeling languages the content uses, says plainly when no conformant view exists, and never
draws anything itself. Most failures here produce a confident, well-worded recommendation, not an
error: a folder name taken as evidence, a model-wide count presented as the scope's, an empty
result read as "nothing there", a mixed scope given a conformant-sounding answer. The failure
column is the useful part of each case.

**Fixture.** A fresh copy of the Westbrook Bank model (`WestbrookBank.qea`) opened in EA, with the
`WBA` technology (qualified form `WBA::WBABusinessApplication`) loaded. Westbrook Bank is our
illustration. A customer runs these cases against their own model, substituting their technology,
stereotypes and package names; the numbers in the checks are the Westbrook copy's and will differ.
Two facts about the copy shape the cases. First, the bank's own language has no view catalogue in
this skill's toolchain, so a scope that is almost all `WBA` content is "dominant language named but
unbound", not a scope with a conformant view. Second, the copy holds no scope that is mostly one
language the toolchain does have a catalogue for, so the cases about ranked viewpoints and
generation routes need a scratch scope that the runner builds, and are marked `BLOCKED` until it
exists.

**Scratch scope S.** A package named `Advisor Scratch Application Landscape` holding ten elements of
the ArchiMate 3 application layer: six `ApplicationComponent`, three `ApplicationService` and one
`DataObject`, each stereotyped with the ArchiMate 3 qualified stereotype. It needs the ArchiMate 3
technology loaded. It is 100% one language the toolchain has a catalogue for.

**Scratch scope T.** A package holding elements of a notation whose best-ranked view is one whose
diagram type dictates its own arrangement, so the toolchain cannot generate it (the shipped example
is a UML timing diagram). It needs that notation loaded.

**Marks.** `REFUSE` (the pass is a hand-off or a decline), `INVARIANT` (must pass on every run),
`BLOCKED` (needs setup a model may not have; a correct run reports the block). No case writes to the
model: this skill only advises, so every case carries the model-unchanged check and none carries
`WRITE`.

## Cases

### TC-01: Recommends, does not draw

Covers: Choosing the diagram, before drawing it

**Marks:** INVARIANT

**Ask:** "I want to understand how our Lending applications fit together. What kind of diagram should I make?"

**Passes when:** The run measures the Lending area, recommends a diagram with its reasoning, and
stops there. It says the next step is drawing the chosen view with `ea-diagram-composition`, and it
creates no diagram, adds nothing to a diagram and changes nothing in the model.

**Check:**

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

```check
tools: not-called: ea_diagram.create_diagram
tools: not-called: ea_diagram.create_diagram_in_language
tools: not-called: ea_diagram.add_elements_to_diagram_bulk
reply: says: the chosen view is drawn in a separate step with the composition skill
```

**Fails when:** The run answers "an application landscape diagram" and then builds one, because the
ask sounded like a request for a picture. The diagram appears in the package, looks reasonable, and
the choice was never explained or offered for the person to change. Also fails: a recommendation
that ends without saying who draws it, leaving the person to think the diagram exists.

### TC-02: A requested type is honored, with a note

Covers: Choosing the diagram, before drawing it

**Ask:** "Give me a Component diagram of the Data Architecture area."

**Passes when:** The run goes with the Component diagram the person asked for. Having measured the
area (twelve `WBADataAsset` elements, all with the Object metaclass), it adds a note that a
Component diagram fits that content badly and says what would fit better, leaving the choice with
the person. It does not substitute another type and present that as the answer.

**Check:**

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

```check
sql: SELECT COUNT(*) FROM t_object o JOIN t_package p ON o.Package_ID = p.Package_ID WHERE p.Name = 'Data Architecture' AND o.Stereotype = 'WBADataAsset' AND o.Object_Type = 'Object'
expect: = 12
```

```check
reply: says: the diagram it will go with is a Component diagram, as asked
reply: says: the content measured in the Data Architecture area fits a Component diagram badly
reply: not: replaces the requested type with a different one without saying so
tools: not-called: ea_diagram.create_diagram
```

**Fails when:** The run quietly recommends a different diagram type because its measurement says so,
and never mentions that the person asked for a Component diagram. A recommender that silently
decides looks the same as one that is right until the person notices their request was overridden.
Also fails: a flat refusal ("that is the wrong diagram").

### TC-03: A folder name is not evidence

Covers: The rule that matters most

**Marks:** INVARIANT

**Ask:** "Our '04 ArchiMate Viewpoints' folder is all ArchiMate, right? Tell me which ArchiMate diagram I should draw for it."

**Passes when:** The run profiles the folder from the stereotypes its elements carry instead of
accepting what the folder is called. It reports what it found (17 stereotyped elements, none
carrying an ArchiMate stereotype) and recommends only from that. It does not take "all ArchiMate"
as a premise.

**Check:**

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

```check
# the folder holds 17 stereotyped elements and none has an ArchiMate stereotype
sql: SELECT COUNT(*), SUM(CASE WHEN o.Stereotype LIKE 'ArchiMate%' THEN 1 ELSE 0 END) FROM t_object o JOIN t_package p ON o.Package_ID = p.Package_ID WHERE p.Name = '04 ArchiMate Viewpoints' AND COALESCE(o.Stereotype, '') <> ''
expect: rows: [[17, 0]]
```

```check
# the stored stereotypes are bound to another technology's profile, not ArchiMate
sql: SELECT COUNT(*) FROM t_object o JOIN t_package p ON o.Package_ID = p.Package_ID JOIN t_xref x ON x.Client = o.ea_guid AND x.Name = 'Stereotypes' WHERE p.Name = '04 ArchiMate Viewpoints' AND x.Description LIKE '%FQName=TOGAF::%'
expect: >= 1
```

```check
tools: called: ea_analyze.execute_sql
reply: says: the folder's languages were worked out from its elements' stereotypes
reply: not: recommends an ArchiMate viewpoint on the strength of the folder's name
```

**Fails when:** The run sees "ArchiMate" in the folder name and the ArchiMate diagrams inside it and
recommends an ArchiMate viewpoint straight away, with reasons that read as measured ("the folder
holds application components and services"). The names are real; the stereotypes are another
technology's. Nothing errors, and the recommendation is conformant to the wrong language.

### TC-04: A scope's histogram comes from SQL

Covers: Step 1 — measure the scope

**Marks:** INVARIANT

**Ask:** "Just for Transactions & Payments, what is it made up of? I want to pick a diagram for that area."

**Passes when:** The run gathers the packages under Transactions & Payments, counts the stereotyped
elements in exactly those packages with a query, and reports that count: 10 `WBABusinessApplication`
and 5 `WBAVendorSystem`. It does not present the repository-wide summary as the scope's.

**Check:**

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

```check
# the scope's own histogram, which the reply's figures must match (the model-wide figures are 46 and 35)
sql: SELECT Stereotype, COUNT(*) FROM t_object WHERE Package_ID IN (WITH RECURSIVE s(id) AS (SELECT Package_ID FROM t_package WHERE Name = 'Transactions & Payments' UNION ALL SELECT p.Package_ID FROM t_package p JOIN s ON p.Parent_ID = s.id) SELECT id FROM s) AND COALESCE(Stereotype, '') <> '' GROUP BY Stereotype ORDER BY COUNT(*) DESC
expect: rows: [["WBABusinessApplication", 10], ["WBAVendorSystem", 5]]
```

```check
tools: called: ea_analyze.execute_sql
reply: says: the Transactions & Payments area holds 10 WBABusinessApplication and 5 WBAVendorSystem elements
reply: not: gives the repository-wide counts as the scope's
```

**Fails when:** The run calls `summarize_stereotype_usage`, which takes no scope and answers for the
whole repository, and quotes 46 business applications and 35 vendor systems as what the payments
area holds. The recommendation that follows is argued from numbers three times too large, and it
reads exactly like a measured one.

### TC-05: Percentages name their base

Covers: Step 1 — measure the scope

**Ask:** "In the Fixtures area, how much of it could you not put into any modeling language?"

**Passes when:** Every percentage or share the run gives says what it is a share of. The scope holds
112 elements, of which 48 carry a stereotype; the run states which of those two it used, and it does
not call 48 the size of the scope.

**Check:**

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

```check
# elements in the scope, then how many of them carry a stereotype
sql: SELECT COUNT(*), SUM(CASE WHEN COALESCE(Stereotype, '') <> '' THEN 1 ELSE 0 END) FROM t_object WHERE Package_ID IN (WITH RECURSIVE s(id) AS (SELECT Package_ID FROM t_package WHERE Name = 'Fixtures' UNION ALL SELECT p.Package_ID FROM t_package p JOIN s ON p.Parent_ID = s.id) SELECT id FROM s)
expect: rows: [[112, 48]]
```

```check
reply: says: for each share it gives, whether the base is the 48 stereotyped elements or the 112 elements in the scope
reply: not: describes 48 as the number of elements in the scope
```

**Fails when:** The run reports "N of 48 could not be placed" as though 48 were the whole area, or
divides the unplaced count by 112 while describing it as a share of stereotyped content. Either
figure is defensible with its base named; the unnamed one is worse than none, because the person
cannot tell which question was answered.

### TC-06: The vocabulary is asked for by technology id

Covers: Step 1 — measure the scope

**Ask:** "Before you suggest anything for Consumer Banking, find out what the Westbrook modeling language actually contains."

**Passes when:** The run reads the language's vocabulary from the runtime using the technology id
`WBA`, not the display name the person used. If a first attempt with the display name comes back
`unknown_mdg`, it retries with the id and does not conclude the language is unknown. It lists
stereotypes from what came back.

**Check:**

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

```check
tools: called: ea_mdg.get_mdg_from_runtime {"tech_id": "WBA"}
reply: says: which stereotypes the language defines, taken from the vocabulary the runtime returned
reply: not: says the language is unknown or empty because a lookup by display name failed
```

**Fails when:** The run asks for `WestbrookBankArchitecture`, gets `unknown_mdg`, and reports that the
technology is not loaded, or carries on with an empty vocabulary. Every `WBA` stereotype then falls
into "could not be placed", and the scope looks like content from a language nobody has heard of.

### TC-07: A technology built into the model is not missed

Covers: Step 1 — measure the scope

**Ask:** "Which modeling languages does this model use? Include any that are built into the file itself."

**Passes when:** The run does not conclude a language is absent because a discovery operation did not
list it. It reads the technology ids out of the repository, and its list includes the bank's own
language, which is embedded in the model.

**Check:**

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

```check
# the technology is embedded in the model file
sql: SELECT COUNT(*) FROM t_document WHERE DocType = 'TECHNOLOGY' AND DocName LIKE 'WBA%'
expect: >= 1
```

```check
# and its stereotypes are bound to its profile
sql: SELECT COUNT(*) FROM t_xref WHERE Name = 'Stereotypes' AND Description LIKE '%FQName=WestbrookBankArchitecture::%'
expect: >= 1
```

```check
reply: says: the bank's own modeling language (WBA, display name WestbrookBankArchitecture) is in the model
reply: not: says the bank's own language is absent or not loaded
```

**Fails when:** The run lists registered and embedded technologies, does not see the bank's own, and
reports "no custom language here". On a server up to 3.5.0 the discovery calls cannot read a
model-embedded technology, so this is the plausible outcome of trusting them; the repository data
says otherwise.

### TC-08: Subgraph connectors are counted once

Covers: Step 1 — measure the scope

**Ask:** "How are things wired around the Origination Platform? Count every connection among it and its direct neighbors, including any links between the neighbors themselves."

**Passes when:** The run walks the element's subgraph and deduplicates connectors on source, target,
type and stereotype before counting. The element and its direct neighbors (six elements) are linked
by 6 connectors, and the reply says 6, counting the one link between two of the neighbors as well as the connectors that touch the element itself.

**Check:**

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

```check
# connectors whose two ends are both in {the element, its direct neighbors}
sql: SELECT COUNT(*) FROM t_connector WHERE Start_Object_ID IN (WITH n(id) AS (SELECT Object_ID FROM t_object WHERE Name = 'Origination Platform' UNION SELECT End_Object_ID FROM t_connector WHERE Start_Object_ID = (SELECT Object_ID FROM t_object WHERE Name = 'Origination Platform') UNION SELECT Start_Object_ID FROM t_connector WHERE End_Object_ID = (SELECT Object_ID FROM t_object WHERE Name = 'Origination Platform')) SELECT id FROM n) AND End_Object_ID IN (WITH n(id) AS (SELECT Object_ID FROM t_object WHERE Name = 'Origination Platform' UNION SELECT End_Object_ID FROM t_connector WHERE Start_Object_ID = (SELECT Object_ID FROM t_object WHERE Name = 'Origination Platform') UNION SELECT Start_Object_ID FROM t_connector WHERE End_Object_ID = (SELECT Object_ID FROM t_object WHERE Name = 'Origination Platform')) SELECT id FROM n)
expect: = 6
```

```check
tools: called: ea_model.traverse_element_subgraph
reply: says: there are 6 connectors among the element and its direct neighbors
reply: not: gives 12 connectors
```

**Fails when:** The run counts the edges as the traversal returns them, every interior edge twice,
and reports 12. The graph looks denser than it is, and any later statement about density, hubs or
"how tangled this is" inherits the doubling.

### TC-09: No stereotypes is not no elements

Covers: Silent failures this step must not trust

**Ask:** "What's in the Technology Architecture area? I want to pick a diagram for it."

**Passes when:** The run reports that the area holds 19 elements and that none of them carries a
stereotype, so there is nothing to attribute to a modeling language. It says the empty profile means
the scope needs a closer look, and it does not call the area empty.

**Check:**

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

```check
sql: SELECT COUNT(*), SUM(CASE WHEN COALESCE(Stereotype, '') <> '' THEN 1 ELSE 0 END) FROM t_object WHERE Package_ID IN (WITH RECURSIVE s(id) AS (SELECT Package_ID FROM t_package WHERE Name = 'Technology Architecture' UNION ALL SELECT p.Package_ID FROM t_package p JOIN s ON p.Parent_ID = s.id) SELECT id FROM s)
expect: rows: [[19, 0]]
```

```check
reply: says: the area holds 19 elements and none of them carries a stereotype
reply: not: says the Technology Architecture area is empty or holds nothing
```

**Fails when:** The run's histogram query returns no rows and the reply says "there is nothing in
this area", or recommends a diagram for an empty scope. The query never errors on an empty answer,
which is what makes the conclusion feel safe.

### TC-10: An unknown element id is not an element with no connections

Covers: Silent failures this step must not trust

**Ask:** "Show me what's connected to element 424242 and tell me which diagram suits it."

**Passes when:** The run reports that the traversal found nothing for that id and that it cannot tell
whether the element exists, is isolated, or the id is wrong. It asks the person to check the id
rather than recommending a diagram for it.

**Check:**

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

```check
# no element has this id in the copy
sql: SELECT Object_ID FROM t_object WHERE Object_ID = 424242
expect: empty
```

```check
reply: says: the traversal returned nothing for that id and asks the person to check the id
reply: not: says the element exists but has no connections
reply: not: recommends a diagram for the element
```

**Fails when:** The run takes the empty `nodes` list as an answer, says "this element is isolated, a
single-element diagram would do", and recommends one. The call returned no error key, so nothing
signaled that the id points at nothing.

### TC-11: A stereotype that matches nothing is checked, not believed

Covers: Silent failures this step must not trust

**Ask:** "How many WBAPaymentRail elements do we have, and what diagram would show them?"

**Passes when:** The run finds a count of zero, says that zero for a name nobody has confirmed is
not the same as "there are none", and checks the name against the language's vocabulary. It reports
that no such stereotype exists in the bank's language and asks what the person meant.

**Check:**

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

```check
sql: SELECT COUNT(*) FROM t_object WHERE Stereotype = 'WBAPaymentRail'
expect: = 0
```

```check
reply: says: no stereotype named WBAPaymentRail is defined by the language, or that it could not confirm the name
reply: says: asks which stereotype the person meant
reply: not: concludes the bank has no payment rails and stops
```

**Fails when:** The run reports "zero WBAPaymentRail elements, so there is nothing to draw". The
count is accurate and the conclusion is wrong: the name was never in the language, so the zero says
nothing about the payment rails that do exist under other stereotypes.

### TC-12: One stray stereotype does not make a scope mixed

Covers: Step 2 — profile, and ask the pivotal question

**Marks:** INVARIANT

**Ask:** "Is the Consumer Banking area one modeling language or a mixture? Then tell me which diagram to use for it."

**Passes when:** The run profiles the area and reports that the bank's own language holds almost all
of it (66 of 67 stereotyped elements; one `VendorApplication` stray). It says the area is effectively
one language, and that the toolchain has no view catalogue for that language, so there is no
conformant view to recommend. It treats that as a different answer from "mixed" and recommends from
there (for example a neutral view, with reasons).

**Check:**

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

```check
sql: SELECT SUM(CASE WHEN Stereotype LIKE 'WBA%' THEN 1 ELSE 0 END), COUNT(*) FROM t_object WHERE Package_ID IN (WITH RECURSIVE s(id) AS (SELECT Package_ID FROM t_package WHERE Name = 'Consumer Banking' UNION ALL SELECT p.Package_ID FROM t_package p JOIN s ON p.Parent_ID = s.id) SELECT id FROM s) AND COALESCE(Stereotype, '') <> ''
expect: rows: [[66, 67]]
```

```check
tools: called: ea_mdg.get_mdg_from_runtime {"tech_id": "WBA"}
reply: says: the bank's own language holds 66 of the 67 stereotyped elements
reply: says: there is no view catalogue for that language here, so no conformant view can be recommended
reply: not: calls the Consumer Banking area a mixture of languages
reply: not: recommends an ArchiMate or UML viewpoint as the conformant view of the bank's own content
```

**Fails when:** The run counts the stray as a second language and reports a mixed scope, sending the
person down the non-conformant path with its obligations for a scope that is 99% one language. The
opposite failure is as bad and quieter: the run sees one dominant language and recommends a shipped
viewpoint as conformant, so that bank-language content sits on a diagram of another notation and
nothing says so.

### TC-13: A mixed scope has no conformant view

Covers: Step 2 — profile, and ask the pivotal question; Step 4 — when no conformant view exists

**Marks:** INVARIANT

**Ask:** "Draw me one diagram of everything in the Fixtures area."

**Passes when:** Before drawing anything, the run measures the area and finds it spans several
languages: 27 of its 48 stereotyped elements are the bank's own language, and the rest belong to
other technologies or to none. It says plainly that no single language holds 90% of the area, so no
conformant view exists, and it names the languages involved. It does not draw before the person has
chosen among the options.

**Check:**

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

```check
# 27 of 48 stereotyped elements are the bank's language: 56%, below the 90% line
sql: SELECT SUM(CASE WHEN Stereotype LIKE 'WBA%' THEN 1 ELSE 0 END), COUNT(*) FROM t_object WHERE Package_ID IN (WITH RECURSIVE s(id) AS (SELECT Package_ID FROM t_package WHERE Name = 'Fixtures' UNION ALL SELECT p.Package_ID FROM t_package p JOIN s ON p.Parent_ID = s.id) SELECT id FROM s) AND COALESCE(Stereotype, '') <> ''
expect: rows: [[27, 48]]
```

```check
tools: not-called: ea_diagram.create_diagram
tools: not-called: ea_diagram.create_diagram_in_language
reply: says: no conformant view exists for this area because it spans several modeling languages
reply: says: names the bank's own language and at least one other as the languages the area spans
```

**Fails when:** The run draws the diagram as asked, choosing a bank-language or shipped-language
view for the whole area. It looks like a finished deliverable; roughly half the elements sit on it
as foreign content, no one was told, and the first conformance check produces a wall of findings.

### TC-14: Stereotypes no language claims are reported

Covers: Step 2 — profile, and ask the pivotal question

**Ask:** "What's in the Fixtures area, language by language? Don't hide anything you can't place."

**Passes when:** The run reports the stereotypes it could not attribute to any language, with their
counts, alongside the ones it could. The three `model document` elements and the one `report package`
element carry stereotypes that no technology claims, and the reply says how much of the area that
leaves unplaced, so the person knows what the profile is worth.

**Check:**

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

```check
sql: SELECT Stereotype, COUNT(*) FROM t_object WHERE Package_ID IN (WITH RECURSIVE s(id) AS (SELECT Package_ID FROM t_package WHERE Name = 'Fixtures' UNION ALL SELECT p.Package_ID FROM t_package p JOIN s ON p.Parent_ID = s.id) SELECT id FROM s) AND Stereotype IN ('model document', 'report package') GROUP BY Stereotype ORDER BY Stereotype
expect: rows: [["model document", 3], ["report package", 1]]
```

```check
reply: says: the stereotypes model document (3 elements) and report package (1 element) belong to no modeling language
reply: says: how much of the area could not be placed, with its base named
```

**Fails when:** The run folds the unclaimed elements into the nearest language, or drops them from the
total, so the shares add up to 100% and the profile looks complete. "I could not place some of this"
is the most useful sentence in the answer, and it is the one that goes missing.

### TC-15: Two languages claiming one concept are not silently resolved

Covers: Step 2 — profile, and ask the pivotal question

**Marks:** BLOCKED

**Setup:** Needs a scope whose stereotypes include a concept name that two loaded languages both
define at the same prefix length. The Westbrook copy cannot be assumed to have one; the runner
builds it where it can (two technologies loaded that share a concept name), and a correct run on a
copy without one reports the block.

**Ask:** "Which diagram suits the elements in this package? I don't know which of our loaded languages they belong to."

**Passes when:** The run reports that the stereotype alone cannot decide the language, because more
than one loaded language claims it. It asks which language the content is meant to be, or asks to
narrow the scope, and does not pick one by the order the languages happened to be listed.

**Check:**

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

```check
reply: says: more than one loaded language claims these stereotypes, so the language cannot be decided from them
reply: says: asks which language the content is meant to be, or asks to narrow the scope
reply: not: names one language as the owner without saying another also claims it
```

**Fails when:** The run takes the first language that matches and recommends its viewpoint with
measured-looking reasons. The answer is wrong about half the time and indistinguishable from a right
one, which is the reason the skill reports the ambiguity instead.

### TC-16: One conformant language gets a ranked view and a hand-off

Covers: Step 2 — profile, and ask the pivotal question; Step 3 — recommend

**Marks:** BLOCKED

**Setup:** Scratch scope S (see Fixture). It needs the ArchiMate 3 technology loaded so the runner's
elements carry its stereotypes; a copy without it reports the block.

**Ask:** "I want to see the application landscape of the Advisor Scratch Application Landscape package. Which diagram should I use?"

**Passes when:** The run measures the package, finds one language holding all ten elements, and says
a conformant view exists. It ranks the viewpoints that admit the content, puts the application
cooperation viewpoint first (its stated purpose matches "application landscape"), shows the counts
and coverage behind the ranking, and hands the chosen view to `ea-diagram-composition`.

**Check:**

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

```check
# the scratch package holds the ten ArchiMate elements
sql: SELECT COUNT(*) FROM t_object o JOIN t_package p ON o.Package_ID = p.Package_ID WHERE p.Name = 'Advisor Scratch Application Landscape' AND o.Stereotype LIKE 'ArchiMate%'
expect: = 10
```

```check
reply: says: one language holds all 10 stereotyped elements, so a conformant view exists
reply: says: recommends the ApplicationCooperation viewpoint first, with the request's wording named as the reason
reply: says: the chosen view is drawn with the composition skill
tools: not-called: ea_diagram.create_diagram
```

**Fails when:** The run names a diagram type without a viewpoint, or names a viewpoint with reasons
that could have been written without looking at the package ("application landscapes show
applications"). Also fails: the run draws the diagram itself.

### TC-17: The reasoning cites the measurements

Covers: Step 3 — recommend

**Ask:** "Which diagram suits the Transactions & Payments area? I have to justify the choice to our architecture board, so show your working."

**Passes when:** The justification is built from what was measured: the 15 stereotyped elements, 10
of them `WBABusinessApplication` and 5 `WBAVendorSystem`, the share held by one language, and, where
the run can compute it, the coverage arithmetic. A board member could check each figure against the
model.

**Check:**

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

```check
sql: SELECT COUNT(*), SUM(CASE WHEN Stereotype = 'WBABusinessApplication' THEN 1 ELSE 0 END), SUM(CASE WHEN Stereotype = 'WBAVendorSystem' THEN 1 ELSE 0 END) FROM t_object WHERE Package_ID IN (WITH RECURSIVE s(id) AS (SELECT Package_ID FROM t_package WHERE Name = 'Transactions & Payments' UNION ALL SELECT p.Package_ID FROM t_package p JOIN s ON p.Parent_ID = s.id) SELECT id FROM s) AND COALESCE(Stereotype, '') <> ''
expect: rows: [[15, 10, 5]]
```

```check
reply: says: cites 15 stereotyped elements, 10 WBABusinessApplication and 5 WBAVendorSystem, as the basis of the recommendation
reply: not: gives a justification that would read the same for any scope
```

**Fails when:** The run argues from the shape of the question ("payments are applications, so an
application view") and never mentions a count. The recommendation may be right. A board cannot tell,
and neither can the person, because none of it was measured.

### TC-18: A view that cannot hold the content is not a candidate

Covers: Step 3 — recommend

**Marks:** BLOCKED

**Setup:** Scratch scope S (see Fixture). Needs the ArchiMate 3 technology loaded.

**Ask:** "I want a business process diagram of the Advisor Scratch Application Landscape package."

**Passes when:** The run does not rank a business-process viewpoint first just because its name
matches the request. It reports that the package holds no business process elements, that a
process-oriented viewpoint therefore covers little of it, and ranks views by how much of the content
they can hold before the wording of the request.

**Check:**

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

```check
reply: says: the package holds no business process elements
reply: says: a process viewpoint covers only a small share of the package's elements
reply: not: ranks the business process cooperation viewpoint first
```

**Fails when:** The run matches "business process" to a viewpoint of that name and recommends it,
with the package's application elements sitting on it as foreign content. A view that cannot hold
the content is not a candidate however well its name fits the request.

### TC-19: A close call is said out loud

Covers: Step 3 — recommend

**Marks:** BLOCKED

**Setup:** Scratch scope S (see Fixture). Needs the ArchiMate 3 technology loaded. The ask carries no
hint of purpose, so more than one viewpoint admits all the content and ties.

**Ask:** "Which diagram suits the elements in the Advisor Scratch Application Landscape package?"

**Passes when:** The run reports that two or more viewpoints rank equally on coverage and intent, names
them, says the tie is settled by an arbitrary tiebreak, and asks what the diagram is for, because
that is the thing the ranking cannot see. It does not present the top one as decisive.

**Check:**

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

```check
reply: says: two or more viewpoints rank equally and names them
reply: says: asks what the diagram is for
reply: not: presents one viewpoint as clearly the best
```

**Fails when:** The run lists the top-ranked viewpoint with a confident paragraph. The tiebreak
(alphabetical, or "narrowest") picked it, and the confidence is borrowed from the format.

### TC-20: Tool layout is not reported as a gap

Covers: Which view is right, and whether it can be drawn, are two questions

**Marks:** BLOCKED

**Setup:** A scope, built by the runner, whose best-ranked view is drawn by EA's own layout rather
than by composed geometry (most UML diagram types). Needs the notation loaded.

**Ask:** "Can your tools actually produce the diagram you just recommended, or is that a gap?"

**Passes when:** The run says the view is drawn by EA's own layout and describes that as the intended
route: place the elements, call the layout operation, tidy the result and check it looks right. It
does not report the route as a limitation.

**Check:**

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

```check
reply: says: the view is laid out by EA's own layout and that this is the intended route
reply: says: the layout is followed by tidying the result and checking that it looks right
reply: not: describes EA's own layout as a limitation or a gap
```

**Fails when:** The run says "this view cannot be composed, so it is not supported" and steers the
person to a different view. Most diagram types in most notations take this route; reporting it as a
gap would make most recommendations look broken.

### TC-21: A view the type dictates is a hard stop

Covers: Which view is right, and whether it can be drawn, are two questions

**Marks:** BLOCKED

**Setup:** Scratch scope T (see Fixture).

**Ask:** "These changes line up over time. I need a timing-style picture of them, generated for me."

**Passes when:** The run says the view cannot be generated: the diagram type dictates the
arrangement, so placing coordinates would place the elements without the meaning their positions
carry. It states that plainly, prefixed so it is not missed, and offers drawing it by hand or
choosing another view. It does not suggest composing it another way.

**Check:**

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

```check
reply: says: the view cannot be generated because the diagram type dictates its arrangement
reply: says: offers to draw it by hand or to choose another view
reply: not: suggests composing the geometry another way
tools: not-called: ea_diagram.create_diagram
```

**Fails when:** The run offers to "lay it out with coordinates" or to compose it differently. The
elements would land on a canvas in some order, and the diagram would look like a timing diagram and
say nothing a timing diagram says.

### TC-22: An unproducible view is still recommended

Covers: Which view is right, and whether it can be drawn, are two questions

**Marks:** BLOCKED

**Setup:** Scratch scope T (see Fixture).

**Ask:** "What is the best diagram for these, and can it be generated?"

**Passes when:** The run answers both questions separately. It recommends the view the content wants
and reports, as a separate statement, that this toolchain cannot generate it. It does not leave the
view out of the answer because it cannot be drawn, and it does not quietly recommend a different,
generatable view in its place.

**Check:**

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

```check
reply: says: recommends the view the content calls for
reply: says: separately that the toolchain cannot generate that view
reply: not: recommends a different view in its place without saying the better view exists
```

**Fails when:** The run hides the unproducible view and recommends the best one it can draw. That
reports the toolchain's gap as the content's, and the person never learns a better view existed.

### TC-23: A mixed scope offers three ordered options

Covers: Step 4 — when no conformant view exists

**Ask:** "I want one diagram of everything in the Fixtures area. What are my options?"

**Passes when:** The run presents the neutral custom view and the split into linked conformant
diagrams, in that order of preference, and says what each costs: a neutral view belongs to no
language, and a split leaves no single picture of the whole area. A dominant-language view is
offered only where the dominant language has a view catalogue here; the run says why it is or is
not available.

**Check:**

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

```check
reply: says: presents a neutral view that belongs to no language as an option
reply: says: presents splitting into linked conformant diagrams as an option, and says no single picture then shows the whole area
reply: says: whether a dominant-language view is available and why
reply: not: offers the options without saying that none of them is conformant as a single view
tools: not-called: ea_diagram.create_diagram
```

**Fails when:** The run offers a single view as "the" answer, or lists the options without their
costs. The split, in particular, looks like the tidy answer until you read that it removes the
whole-scope picture the person asked for.

### TC-24: A non-conformant view is announced where readers will see it

Covers: Two obligations, and they are not optional

**Ask:** "Let's go with a single neutral diagram for the Fixtures area. What do I need to tell the people who will read it?"

**Passes when:** The run says the view is not conformant to any one language and names the languages
it spans. It gives a sentence to place on the diagram itself, for example as a note, so the reader of
the diagram sees it, and does not leave the statement only in the chat.

**Check:**

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

```check
reply: says: the view is not conformant to any single modeling language and names the languages it spans
reply: says: gives a sentence to record on the diagram itself
reply: not: leaves the non-conformance statement only in the conversation
```

**Fails when:** The run says "note that this is a mixed view" in the reply and nothing is carried to
the diagram. The next reader opens a clean-looking diagram, assumes it follows a language, and builds
on that.

### TC-25: Validation is reconciled before the diagram exists

Covers: Two obligations, and they are not optional

**Marks:** INVARIANT

**Ask:** "We'll go with the neutral diagram for the Fixtures area. Will our conformance rules complain about it?"

**Passes when:** The run says what, if anything, a conformance check will object to on this view,
naming the concepts, and offers to scope those rules out or annotate them as accepted before any
diagram is generated, so the person decides up front. It does not generate first and report findings
afterwards.

**Check:**

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

```check
reply: says: names the concepts a conformance check will object to, or says why it expects none
reply: says: offers to scope those rules out or to annotate them as accepted, before generating
tools: not-called: ea_diagram.create_diagram
tools: not-called: ea_validate.audit
```

**Fails when:** The run says "should be fine" and moves on, or generates the diagram and runs the
check, so the person meets a wall of findings they were never warned about and has to decide under
pressure what to accept.

### TC-26: Coverage is not fitness

Covers: Judgment this skill cannot encode

**Ask:** "A colleague says any diagram type that can hold all the elements in the Consumer Banking area is as good as any other. Do you agree?"

**Passes when:** The run disagrees. It says coverage shows a view can hold the content, not that it
should, and that fitness depends on the argument the diagram is meant to make. It asks what decision
the diagram supports.

**Check:**

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

```check
reply: says: a view that holds all the content can still be the wrong argument to make about it
reply: says: asks what decision the diagram supports
reply: not: agrees that any view that holds the content is equally good
```

**Fails when:** The run agrees that coverage settles it. A view that admits every concept in the
scope is then picked on a 100% score alone, and the diagram holds everything while saying the wrong
thing.

### TC-27: The user's words narrow the choice; they do not settle it

Covers: Judgment this skill cannot encode

**Ask:** "Just show me the application landscape for Wealth Management."

**Passes when:** The run still measures the Wealth Management area before recommending, treats
"application landscape" as evidence about the purpose rather than as an instruction, and, because
the measurement and the wording together lead to a recommendation, gives one with its reasons.

**Check:**

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

```check
tools: called: ea_analyze.execute_sql
tools: not-called: ea_diagram.create_diagram
reply: says: the request's wording narrowed the choice without settling it
```

**Fails when:** The run takes "application landscape" as the instruction, skips the measurement and
names the diagram, or draws it. The phrase is a good hint about the purpose; as the whole answer it
gives the person exactly what they typed.

### TC-28: Unmeasured content is a weak recommendation, and says so

Covers: Judgment this skill cannot encode

**Ask:** "Which diagram type best shows how account opening works step by step? Use the 03 UML Behavior folder."

**Passes when:** The run reports that the folder holds 37 elements and that none carries a stereotype,
so the scope could not be profiled by language. It gives its recommendation as weak, resting on the
wording of the request alone, and says why.

**Check:**

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

```check
sql: SELECT COUNT(*), SUM(CASE WHEN COALESCE(Stereotype, '') <> '' THEN 1 ELSE 0 END) FROM t_object WHERE Package_ID IN (WITH RECURSIVE s(id) AS (SELECT Package_ID FROM t_package WHERE Name = '03 UML Behavior' UNION ALL SELECT p.Package_ID FROM t_package p JOIN s ON p.Parent_ID = s.id) SELECT id FROM s)
expect: rows: [[37, 0]]
```

```check
reply: says: the folder's 37 elements carry no stereotype, so it could not be profiled by language
reply: says: the recommendation rests on the request's wording and is weak
reply: not: presents the recommendation as measured
```

**Fails when:** The run recommends a diagram with reasons phrased like measurements ("the folder holds
behavior elements, so a sequence diagram"). The empty profile produced nothing to measure; the reasons
are the wording of the ask handed back as evidence.

### TC-29: A new language is a data change, never a code change

Covers: Judgment this skill cannot encode

**Marks:** REFUSE

**Ask:** "Our company has its own diagramming notation. Add it to the advisor's code so it can advise on our diagrams."

**Passes when:** The run declines to change the ranking engine. It says a notation's view catalogue
lives in a binding's `viewpoints:` block, so adding a language is a data change, and points to the
bindings of `ea-diagram-composition` as the place to do it. It does not edit the engine.

**Check:**

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

```check
reply: says: a new notation is added as a binding's viewpoints data, not as a change to the engine
reply: says: points to the composition skill's bindings as the place to add it
reply: not: offers to add the notation's name or rules to the engine code
```

**Fails when:** The run adds branches for the customer's notation to the engine. The advice works for
that one notation, the engine now names a notation, and a test written to forbid exactly that starts
failing.

### TC-30: A package id is not an element id

Covers: Silent failures this step must not trust

**Ask:** "Show me what's connected to element 13 and tell me which diagram suits it."

**Passes when:** The run notices that the node the traversal returns for id 13 is a `Package`, not an
element, and says so. It does not describe a package as an element with connections, and it asks
whether the person meant the package's contents or an element in it.

**Check:**

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

```check
# id 13 is the Lending package, not an element
sql: SELECT Object_Type, Name FROM t_object WHERE Object_ID = 13
expect: rows: [["Package", "Lending"]]
```

```check
reply: says: the node for id 13 is a Package, not an element
reply: not: recommends a diagram for id 13 as though it were an element
```

**Fails when:** The run takes the returned node as the element, counts its connectors as the
element's, and recommends a diagram for it. The call did not fail; it returned a node of the wrong
kind, which only its type reveals.

### TC-31: A loaded technology can expose nothing

Covers: Step 1 — measure the scope

**Marks:** BLOCKED

**Setup:** Needs a technology that is loaded in the repository and for which the vocabulary
operation returns an empty stereotype list (a technology that is loaded but unreadable). The
Westbrook copy cannot be assumed to have one; the runner builds it where it can, and a correct run on
a copy without one reports the block.

**Ask:** "Which of our loaded languages are these elements in? The vocabulary call for that technology comes back empty, so I guess it's an empty technology."

**Passes when:** The run does not accept an empty vocabulary as proof the technology is empty. It
checks the repository for the technology's stereotypes on the scope's elements and reports what it
finds, or says it cannot tell.

**Check:**

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

```check
tools: called: ea_analyze.execute_sql
reply: says: an empty vocabulary does not show the technology is empty
reply: not: concludes the technology has no stereotypes because the vocabulary call returned none
```

**Fails when:** The run agrees the technology is empty and attributes none of the scope's elements to
it. The scope's stereotyped elements then fall into "unattributed" and the profile understates the
language that actually dominates.

## Invariants

The model-unchanged check on every case is one mechanical invariant: **this skill never writes.**
Any case in which the model differs afterward, or a diagram-creating operation was called, fails
whatever the reply says.

A second one holds on every case that cites a scope: **every figure the reply gives for a scope can
be reproduced by the histogram query over that scope's package tree** (TC-04, TC-12, TC-13, TC-17).
The counts, the stereotyped total and the share of the largest language all come from the same
query, so a model-wide count (TC-04), a wrong denominator (TC-05) or a doubled connector figure
(TC-08) fails without a known-good recommendation.

The invariants do not cover whether the recommended view is the right one, whether a language was
attributed correctly, or whether the ranking order is sound. Those are judgments about reasoning,
checked through the reply statements and by the arithmetic tests that ship with the skill's engine.

## Headings not covered

- `Reference`: two links to the engine and to the composition skill; it states nothing the skill does, refuses or warns about.

## Findings

- **Display name versus id.** SKILL.md says the display name returns `unknown_mdg`; the Westbrook canon says the server accepts both `WBA` and `WestbrookBankArchitecture` as identifiers. One is out of date or build-specific. TC-06 passes either way, because it requires the id call.
- **"Record on the diagram" has no owner.** Step 4 says to record the non-conformance on the diagram, but this skill never creates the diagram and says nothing about passing `non_conformance` to `ea-diagram-composition`. TC-24 can only check that the run supplies the sentence for the diagram; nothing checks it arrives.
- **The route table contradicts "does not draw anything".** For `tool-layout` the table says "place the elements, call the layout operation, then tidy and check it", under "What you do", while the opening says the skill draws nothing and hands off. TC-20 checks the description of the route, not who performs it.
- **Dominant-language option assumes a bound language.** Step 4's first option (dominant-language view) exists only when the dominant language has a view catalogue. When it does not, as for the bank's own language in the Fixtures area (27 of 48), the skill is silent about what replaces it. TC-23 accepts either explanation.
- **The customer's own diagram types are never offered.** The unbound case ends in a neutral base type, but the bank's technology declares diagram types of its own (`WBA::WBAApplicationView`, stored as `MDGDgm=WBA::WBAApplicationView` on several existing diagrams). The skill gives no step for offering them, so a run following it recommends a plain Logical diagram where the model's own practice is a profiled one. Not turned into a pass or fail, because the skill does not promise it.
- **Unstereotyped content cannot be profiled and nothing replaces the profile.** The histogram ignores unstereotyped elements, so a scope such as `03 UML Behavior` (37 elements, none stereotyped) yields no profile at all. The skill says to call the result weak (TC-28) but offers no way to use the elements' metaclass (`Object_Type`) as evidence, which the data plainly supports.
- **Snippets are not runnable as written.** Steps 2 and 3 use `advise`, `bindings`, `histogram`, `vocabulary` and `what_the_user_said` without saying how `advise` is imported or how the bindings are loaded (they live in `ea-diagram-composition`). A surface without local code execution cannot follow the method at all; no case can show this, because the pass is judged on the reply.
- **No Westbrook scope exercises a conformant view.** The bank's language has no binding, and the folder named `04 ArchiMate Viewpoints` holds elements stereotyped by another technology (bare `ApplicationComponent` and its siblings, bound to the TOGAF profile), which the ArchiMate 3 binding's `ArchiMate_` prefix does not match. Eight cases (TC-15, TC-16, TC-18 to TC-22) need the runner to build scratch scope S or T and are marked `BLOCKED`.
- **Not checkable in one ask.** "Compare what validation returns with `will_be_flagged`" needs a prediction from an earlier turn and a drawn diagram. The `composer-pending` and `unanswered` routes need a binding that fails to answer, which cannot be built from a model. Both rest on the engine's own tests.

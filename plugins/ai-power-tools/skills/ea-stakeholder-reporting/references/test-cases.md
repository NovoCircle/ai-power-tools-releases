# Acceptance cases: `ea-stakeholder-reporting`

This skill promises that a stakeholder gets an answer in business language and that no number
drawn from a tagged value is quoted without first checking how complete the tag is. Its
failures are quiet: a roll-up over a half-filled tag returns a well-formed, confident, wrong
count, and an empty roll-up reads like "none exist". These cases are built to catch the
plausible wrong answer, not an error.

**Fixture.** A fresh copy of the Westbrook Bank model (`<model-dir>\WestbrookBank.qea`) opened
in EA, with the Westbrook technology active. Every case is read-only. Westbrook Bank is our
illustration. A customer runs these cases against their own model, substituting their
technology, stereotypes, tags, package names and counts. The numbers below are counts from the
Westbrook copy; where `SKILL.md` or `references/coverage-data.md` quote different numbers, see
Findings.

TC-21 to TC-24 cover diagram descriptions. Their Setup (writing a description, adding an application
to a diagram, writing a person's Notes) is a `setup` block that `tools/acceptance/setup_case.py` runs
on the copy before the agent starts, so the run itself stays read-only. The ids in their checks are the Westbrook copy's (diagram 4 is the Customer
Engagement Landscape and diagram 9 the Lending Landscape; package 10 is Customer Engagement and
package 11 Account Management); a customer reads theirs from `t_diagram` and `t_package`. The wording
of a generated description depends on the technology that governs the diagram, so the checks look at
status and structure, never at exact sentences.

**Marks.** `INVARIANT` (must pass on every run), `REFUSE` (the pass is a hand-off), `BLOCKED`
(needs setup a tenant may not have). Every case carries the model-unchanged check, because the
skill is read-only.

## Cases

### TC-01: A count question stays read-only

Covers: Reporting to stakeholders from a Sparx EA model; When to use

**Ask:** "How many of our applications are mission-critical?"

**Passes when:** The run answers from reads only, names which kind of application it counted
(Business Applications), and gives 11 of 46. It may instead give 12 of 47 when it counts Core
Deposit System of Record, which carries two stereotypes, provided it names that element. It may add
that Vendor Systems are a separate population with their own count. It creates no scratch element and no package.

**Check:**

```check
sql: SELECT COUNT(*) FROM t_objectproperties tp JOIN t_object o ON tp.Object_ID = o.Object_ID WHERE o.Stereotype = 'WBABusinessApplication' AND tp.Property = 'criticality' AND tp.Value = 'Mission-Critical'
expect: = 11
```

```check
# two readings of "business application": the primary stereotype (46) and every element bound to it (47).
# Core Deposit System of Record is bound to both WBASystemOfRecord (primary) and WBABusinessApplication.
sql: SELECT (SELECT COUNT(*) FROM t_object WHERE Stereotype = 'WBABusinessApplication'), (SELECT COUNT(*) FROM t_xref WHERE Name = 'Stereotypes' AND Description LIKE '%::WBABusinessApplication;%'), (SELECT COUNT(*) FROM t_object o JOIN t_xref x ON x.Client = o.ea_guid AND x.Name = 'Stereotypes' WHERE o.Name = 'Core Deposit System of Record' AND o.Stereotype = 'WBASystemOfRecord' AND x.Description LIKE '%::WBABusinessApplication;%')
expect: rows: [[46, 47, 1]]
```

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

```check
reply: says: 11 of 46 Business Applications are Mission-Critical, or 12 of 47 when it counts Core Deposit System of Record, which it names as carrying two stereotypes
reply: not: reports a single combined figure of 25 without saying it merges Business Applications and Vendor Systems
tools: not-called: ea_model.create_element
tools: not-called: ea_model.create_package
tools: not-called: ea_model.update_element
tools: not-called: ea_model.set_tagged_value
tools: not-called: ea_model.delete_element
tools: not-called: ea_model.delete_package
```

**Fails when:** The run quotes 25 (Business Applications plus Vendor Systems) as "our
applications" without saying the two populations were merged, or quotes 14 (the Vendor System
figure) as the answer. Or it builds a scratch package to "demonstrate" the count and leaves it
behind; the model-unchanged check catches that.

### TC-02: Coverage is checked before the share is quoted

Covers: Step 0: check coverage before you quote a number; The gap this closes

**Marks:** INVARIANT

**Ask:** "What share of our business applications are mission-critical? It's going in the
board deck."

**Passes when:** Before quoting the share, the run reads the true denominator for the type and
the populated count for the tag, finds the tag filled on every application, and then states the
share (11 of 46, about 24 percent) with that coverage stated or implied as complete. A share of 12 of
47 (about 26 percent) also passes when the run names Core Deposit System of Record as the element
carrying both the System of Record and Business Application stereotypes.

**Check:**

```check
sql: SELECT COUNT(DISTINCT o.Object_ID), SUM(CASE WHEN TRIM(COALESCE(tp.Value, '')) <> '' THEN 1 ELSE 0 END) FROM t_object o JOIN t_objectproperties tp ON tp.Object_ID = o.Object_ID WHERE o.Stereotype = 'WBABusinessApplication' AND tp.Property = 'criticality'
expect: rows: [[46, 46]]
```

```check
# two readings of "business application": the primary stereotype (46) and every element bound to it (47).
# Core Deposit System of Record is bound to both WBASystemOfRecord (primary) and WBABusinessApplication.
sql: SELECT (SELECT COUNT(*) FROM t_object WHERE Stereotype = 'WBABusinessApplication'), (SELECT COUNT(*) FROM t_xref WHERE Name = 'Stereotypes' AND Description LIKE '%::WBABusinessApplication;%'), (SELECT COUNT(*) FROM t_object o JOIN t_xref x ON x.Client = o.ea_guid AND x.Name = 'Stereotypes' WHERE o.Name = 'Core Deposit System of Record' AND o.Stereotype = 'WBASystemOfRecord' AND x.Description LIKE '%::WBABusinessApplication;%')
expect: rows: [[46, 47, 1]]
```

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

```check
tools: called: ea_analyze.summarize_stereotype_usage
tools: called: ea_analyze.summarize_tagged_value_usage
reply: says: 11 of 46 business applications are Mission-Critical, or 12 of 47 when it counts Core Deposit System of Record, which it names as carrying two stereotypes
reply: not: gives a share whose denominator is anything other than 46 or 47
reply: not: gives a 47 without naming the element that makes the difference
```

**Fails when:** The run goes straight to the roll-up and quotes a figure with no coverage check.
On this tag the number happens to be right, so the failure is invisible in the output; only the
transcript shows that the check never ran. This is why the case tests the method, and why the
same method is exercised on tags where skipping it gives a wrong number (TC-03, TC-04, TC-05).

### TC-03: A tag the type never carries

Covers: Step 0: check coverage before you quote a number

**Marks:** INVARIANT

**Ask:** "Which of our data assets are mission-critical?"

**Passes when:** The run reports that there are 12 data assets and that none of them carries a
criticality, so the question cannot be answered from this model. It does not say there are no
data assets, and it does not say none are mission-critical.

**Check:**

```check
sql: SELECT COUNT(*) FROM t_object WHERE Stereotype = 'WBADataAsset'
expect: = 12
```

```check
sql: SELECT COUNT(*) FROM t_objectproperties tp JOIN t_object o ON tp.Object_ID = o.Object_ID WHERE o.Stereotype = 'WBADataAsset' AND tp.Property = 'criticality'
expect: = 0
```

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

```check
reply: says: there are 12 data assets and criticality is not recorded on any of them
reply: not: says there are no data assets
reply: not: says none of the data assets are mission-critical
```

**Fails when:** The roll-up comes back as zero elements and zero groups, and the run reports "no
mission-critical data assets" or "no data assets found". Both read as a clean answer. The model
holds 12 data assets; the type simply does not track criticality, and the response shape is
identical to a misspelled type.

### TC-04: A tag that exists on every element and is blank on all of them

Covers: Step 0: check coverage before you quote a number

**Marks:** INVARIANT

**Ask:** "Who owns our business services? I need an owner for each one."

**Passes when:** The run reports that all 8 business services have an owner field and that none
of the 8 has an owner filled in, so no owner can be named. It does not report the field as fully
covered.

**Check:**

```check
sql: SELECT COUNT(*), SUM(CASE WHEN TRIM(COALESCE(tp.Value, '')) <> '' THEN 1 ELSE 0 END) FROM t_objectproperties tp JOIN t_object o ON tp.Object_ID = o.Object_ID WHERE o.Stereotype = 'WBABusinessService' AND tp.Property = 'businessOwner'
expect: rows: [[8, 0]]
```

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

```check
tools: called: ea_analyze.summarize_tagged_value_usage
reply: says: none of the 8 business services has an owner recorded
reply: not: says the owner tag is fully populated or 100 percent covered
```

**Fails when:** The run checks only whether the tag is present, finds it on all 8, and reports
full coverage, or lists owners as a single empty entry. The tag count is 8 of 8 and the usable
count is 0 of 8; only the populated count shows it.

### TC-05: A tag that is filled on most elements

Covers: Step 0: check coverage before you quote a number

**Ask:** "Give me the number of business applications for each business owner."

**Passes when:** The run reports that 43 of the 46 business applications have an owner and 3 do
not, presents the owner breakdown for the 43, and shows the 3 as unassigned rather than leaving
them out or folding them into an owner.

**Check:**

```check
sql: SELECT COUNT(*), SUM(CASE WHEN TRIM(COALESCE(tp.Value, '')) <> '' THEN 1 ELSE 0 END) FROM t_objectproperties tp JOIN t_object o ON tp.Object_ID = o.Object_ID WHERE o.Stereotype = 'WBABusinessApplication' AND tp.Property = 'businessOwner'
expect: rows: [[46, 43]]
```

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

```check
reply: says: 43 of 46 business applications have a business owner and 3 do not
reply: not: presents the owner counts as covering all 46 applications
```

**Fails when:** The owner table is presented as the whole portfolio. The counts add to 43, the
reader assumes 46, and the 3 unowned applications are never mentioned.

### TC-06: One team spelled two ways

Covers: Step 0: check coverage before you quote a number

**Marks:** INVARIANT

**Ask:** "How many vendor systems does each technical team look after?"

**Passes when:** The run notices that "Infrastructure & Cloud Team" appears under two spellings
(6 and 2 systems, the second with an encoded ampersand), reports one team with 8, and says the
spelling is a data-quality issue in the model.

**Check:**

```check
sql: SELECT tp.Value, COUNT(*) FROM t_objectproperties tp JOIN t_object o ON tp.Object_ID = o.Object_ID WHERE o.Stereotype = 'WBAVendorSystem' AND tp.Property = 'technicalOwner' AND tp.Value LIKE 'Infrastructure%Cloud Team' GROUP BY tp.Value ORDER BY tp.Value
expect: rows: [["Infrastructure & Cloud Team", 6], ["Infrastructure &amp; Cloud Team", 2]]
```

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

```check
reply: says: the Infrastructure and Cloud team looks after 8 vendor systems
reply: says: the team name is spelled two ways in the model
reply: not: lists Infrastructure and Cloud as two separate teams with 6 and 2 systems
```

**Fails when:** The run reports two teams. The tag is 35 of 35 populated, so a blank check passes
clean, and the wrong answer is a tidy table with a team that does not exist.

### TC-07: Breakdown by criticality

Covers: Portfolio roll-ups: `aggregate_portfolio`

**Ask:** "Break down our business applications by criticality."

**Passes when:** The run uses the roll-up operation grouped by criticality and reports
Business-Critical 21, Mission-Critical 11, Standard 8 and Important 6, against a total of 46. A
run may instead count Core Deposit System of Record, which carries the System of Record and
Business Application stereotypes, giving 12 Mission-Critical out of 47, as long as it names the
element and the groups add up to the total it states.

**Check:**

```check
sql: SELECT tp.Value, COUNT(*) FROM t_objectproperties tp JOIN t_object o ON tp.Object_ID = o.Object_ID WHERE o.Stereotype = 'WBABusinessApplication' AND tp.Property = 'criticality' GROUP BY tp.Value ORDER BY tp.Value
expect: rows: [["Business-Critical", 21], ["Important", 6], ["Mission-Critical", 11], ["Standard", 8]]
```

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

```check
tools: called: ea_repository.aggregate_portfolio
reply: says: 21 Business-Critical, 11 Mission-Critical, 8 Standard and 6 Important, out of 46; or the same with 12 Mission-Critical out of 47, naming Core Deposit System of Record as the element with two stereotypes
reply: not: gives group counts that do not add up to the total it states
```

**Fails when:** The groups are right but the total is missing or wrong, or the groups add up to a
different total than the one stated (a first trial run reported 47 applications in rows that summed
to 48), or the run reports counts for Business Applications and Vendor Systems blended into one
table without saying so.

### TC-08: Breakdown for one line of business

Covers: Portfolio roll-ups: `aggregate_portfolio`

**Ask:** "Just for Transactions & Payments, how are our business applications spread across
criticality?"

**Passes when:** The run limits the roll-up to the Transactions & Payments package and its
sub-packages and reports 10 applications: Business-Critical 7, Standard 2, Mission-Critical 1.
It does not report the whole-repository figures.

**Check:**

```check
sql: SELECT tp.Value, COUNT(*) FROM t_objectproperties tp JOIN t_object o ON tp.Object_ID = o.Object_ID JOIN t_package p ON o.Package_ID = p.Package_ID WHERE o.Stereotype = 'WBABusinessApplication' AND tp.Property = 'criticality' AND (p.Name = 'Transactions & Payments' OR p.Parent_ID = (SELECT Package_ID FROM t_package WHERE Name = 'Transactions & Payments')) GROUP BY tp.Value ORDER BY tp.Value
expect: rows: [["Business-Critical", 7], ["Mission-Critical", 1], ["Standard", 2]]
```

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

```check
reply: says: 10 business applications in Transactions & Payments
reply: not: reports 46 as the number of applications in Transactions & Payments
```

**Fails when:** The run ignores the area and answers with the whole-repository breakdown (21, 11,
8, 6). The numbers look like a roll-up and are not the answer to the question asked.

### TC-09: A type name that does not exist

Covers: Portfolio roll-ups: `aggregate_portfolio`; Failure modes you will actually hit

**Marks:** INVARIANT

**Ask:** "How many of our Data Services are mission-critical?"

**Passes when:** The run checks the stereotype list, finds no type that matches "Data Service",
and says so. It offers the nearest real types (Data Asset, Business Service) and says what each
does and does not track. It does not report zero.

**Check:**

```check
sql: SELECT COUNT(*) FROM t_object WHERE Stereotype LIKE '%DataService%'
expect: = 0
```

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

```check
tools: called: ea_analyze.summarize_stereotype_usage
reply: says: the model has no element type called Data Service
reply: not: says there are zero mission-critical data services
```

**Fails when:** The roll-up for the guessed type returns zero elements and zero groups, and the
run reports "none of our data services are mission-critical" to a stakeholder. The response is
indistinguishable from a real type with no data.

### TC-10: A scope field that holds several values

Covers: Portfolio roll-ups: `aggregate_portfolio`; Failure modes you will actually hit

**Marks:** INVARIANT

**Ask:** "How many of our business applications are in GLBA scope?"

**Passes when:** The run notices that some applications list several regulations in one value,
counts each application under every regulation it names, and answers 29 of 46.

**Check:**

```check
sql: SELECT SUM(CASE WHEN tp.Value LIKE '%GLBA%' THEN 1 ELSE 0 END), SUM(CASE WHEN tp.Value = 'GLBA' THEN 1 ELSE 0 END) FROM t_objectproperties tp JOIN t_object o ON tp.Object_ID = o.Object_ID WHERE o.Stereotype = 'WBABusinessApplication' AND tp.Property = 'regulatoryScope'
expect: rows: [[29, 14]]
```

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

```check
tools: called: ea_repository.aggregate_portfolio
reply: says: 29 of 46 business applications are in GLBA scope
reply: not: gives 14 as the number of applications in GLBA scope
```

**Fails when:** The run reads the group labelled "GLBA" and answers 14. It is the exact-match
group, it looks like the answer, and it is about half the true count; the rest sit under
"GLBA, FFIEC", "PCI, GLBA" and "GLBA, SOX".

### TC-11: Percentages over a multi-value field

Covers: Portfolio roll-ups: `aggregate_portfolio`

**Ask:** "Give me the percentage of business applications under each of GLBA, SOX, FFIEC and PCI."

**Passes when:** Each percentage is computed against the 46 applications (GLBA 29, FFIEC 16, SOX
7, PCI 3), and the run says the percentages add to more than 100 because an application can be
in more than one scope.

**Check:**

```check
sql: SELECT SUM(CASE WHEN tp.Value LIKE '%GLBA%' THEN 1 ELSE 0 END), SUM(CASE WHEN tp.Value LIKE '%SOX%' THEN 1 ELSE 0 END), SUM(CASE WHEN tp.Value LIKE '%FFIEC%' THEN 1 ELSE 0 END), SUM(CASE WHEN tp.Value LIKE '%PCI%' THEN 1 ELSE 0 END), COUNT(DISTINCT o.Object_ID) FROM t_objectproperties tp JOIN t_object o ON tp.Object_ID = o.Object_ID WHERE o.Stereotype = 'WBABusinessApplication' AND tp.Property = 'regulatoryScope'
expect: rows: [[29, 7, 16, 3, 46]]
```

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

```check
reply: says: GLBA is 29 of 46, FFIEC 16 of 46, SOX 7 of 46 and PCI 3 of 46
reply: says: the percentages add to more than 100 because some applications are in several scopes
reply: not: computes the percentages against 55, the sum of the four counts
```

**Fails when:** The run divides by the sum of the group counts (55), so GLBA shows as 53 percent
and the four shares add to exactly 100. The table looks tidy and every percentage is wrong.

### TC-12: "None" is not the same as blank

Covers: Failure modes you will actually hit

**Marks:** INVARIANT

**Ask:** "How many of our business applications have no regulatory exposure?"

**Passes when:** The run reports that 5 applications were assessed and recorded as "None", and
that 3 more have nothing recorded at all and cannot be called exempt. It does not answer 8.

**Check:**

```check
sql: SELECT SUM(CASE WHEN tp.Value = 'None' THEN 1 ELSE 0 END), SUM(CASE WHEN TRIM(COALESCE(tp.Value, '')) = '' THEN 1 ELSE 0 END) FROM t_objectproperties tp JOIN t_object o ON tp.Object_ID = o.Object_ID WHERE o.Stereotype = 'WBABusinessApplication' AND tp.Property = 'regulatoryScope'
expect: rows: [[5, 3]]
```

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

```check
reply: says: 5 applications are recorded as having no regulatory scope
reply: says: 3 applications have no regulatory scope recorded and have not been assessed
reply: not: answers 8
```

**Fails when:** The run merges "assessed, not in scope" with "never assessed" into 8. The two
answers mean different things to a compliance reader, and the merged figure overstates what is
known.

### TC-13: A plain-language summary of one system

Covers: Business view: `get_element_business_view`; When to use

**Ask:** "I'm briefing the head of risk. Give me a short summary of the Westbrook Fraud Decision
Engine in plain terms: how important it is, who owns it and what it connects to."

**Passes when:** The summary says it is a business application rated Mission-Critical, owned by
Fraud Risk Management with Risk Technology Team as technical owner, classified Confidential, in
FFIEC scope and current in its lifecycle, and that it uses the NICE Actimize Fraud Risk
Management vendor system. It uses business wording, not stereotype names or tag keys.

**Check:**

```check
sql: SELECT tp.Property, tp.Value FROM t_objectproperties tp JOIN t_object o ON tp.Object_ID = o.Object_ID WHERE o.Name = 'Westbrook Fraud Decision Engine' AND o.Stereotype = 'WBABusinessApplication' ORDER BY tp.Property
expect: rows: [["businessOwner", "Fraud Risk Management"], ["criticality", "Mission-Critical"], ["dataClassification", "Confidential"], ["lifecycle", "Current"], ["regulatoryScope", "FFIEC"], ["technicalOwner", "Risk Technology Team"]]
```

```check
sql: SELECT COUNT(*) FROM t_connector c JOIN t_object s ON c.Start_Object_ID = s.Object_ID JOIN t_object t ON c.End_Object_ID = t.Object_ID WHERE s.Name = 'Westbrook Fraud Decision Engine' AND c.Stereotype = 'Uses' AND t.Name = 'NICE Actimize Fraud Risk Management'
expect: = 1
```

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

```check
tools: called: ea_analyze.get_element_business_view
reply: says: the Westbrook Fraud Decision Engine is Mission-Critical
reply: says: it is owned by Fraud Risk Management and technically owned by Risk Technology Team
reply: says: it uses NICE Actimize Fraud Risk Management
reply: not: uses the words WBABusinessApplication, businessOwner or dataClassification as labels
```

**Fails when:** The summary is correct but written in the model's vocabulary ("WBABusinessApplication
with criticality=Mission-Critical and businessOwner=..."), which a non-modeller cannot read, or it
states a value the model does not hold.

### TC-14: A missing field is not "not applicable"

Covers: Business view: `get_element_business_view`

**Ask:** "How critical is Customer Master Data to the business?"

**Passes when:** The run reports that no criticality is recorded for Customer Master Data and
that the data asset type in this model does not carry a criticality for any of its 12 elements,
so it is a gap in the model, not a low rating. It reports the fields that are recorded
(classification and regulatory scope).

**Check:**

```check
sql: SELECT COUNT(*) FROM t_objectproperties tp JOIN t_object o ON tp.Object_ID = o.Object_ID WHERE o.Name = 'Customer Master Data' AND o.Stereotype = 'WBADataAsset' AND tp.Property = 'criticality'
expect: = 0
```

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

```check
tools: called: ea_analyze.summarize_tagged_value_usage
reply: says: no criticality is recorded for Customer Master Data
reply: not: states a criticality level for Customer Master Data
reply: not: calls its criticality not applicable without checking whether other data assets carry it
```

**Fails when:** The run sees a short property list, concludes "not applicable" or "low", and
tells the stakeholder so. The business view is silent on whether a field is unset or untracked,
so the only honest answer is that the model does not say.

### TC-15: The business name for a type in the customer's own technology

Covers: Display terms: `resolve_display_term`

**Ask:** "What's the plain-English name I should use on slides for the WBABusinessApplication
element type, and for WBAVendorSystem?"

**Passes when:** The run takes the names from the technology's declared aliases (Business
Application, Vendor System), or derives them by dropping the technology prefix and splitting the
words. If it calls the term lookup and gets no match, it does not conclude the type has no
business name.

**Check:**

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

```check
tools: called: ea_mdg.get_mdg_from_runtime
reply: says: Business Application and Vendor System
reply: not: says there is no business name for these types because the term lookup found nothing
```

**Fails when:** The run asks the term lookup, gets back the technical name unchanged with
`found: false`, and hands the stakeholder "WBABusinessApplication" as the display term, or says
no alias exists. The lookup reads the server's own tables, not the technology EA has loaded.

### TC-16: Business labels for a customer's own tags

Covers: Display terms: `resolve_display_term`; Failure modes you will actually hit

**Ask:** "I'm building a report. What business-friendly column headings can I use for criticality
and technicalOwner?"

**Passes when:** The run offers "Criticality" and "Technical Owner", derived by splitting the
camelCase names, and says the term lookup does not know a customer's own tags. If it used the
lookup, it used the kind `tagged_value`, not `tag`, and treated a miss as "not found", not as
"no such term".

**Check:**

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

```check
reply: says: Criticality and Technical Owner
reply: says: the lookup does not resolve tags of the organization's own technology, so the labels are derived from the tag names
reply: not: says the tags have no business name
```

**Fails when:** The run asks the lookup for kind `tag` (not a valid kind), gets a miss that looks
like any other miss, and tells the user no business term exists for the tag.

### TC-17: A term from a language that ships with EA

Covers: Display terms: `resolve_display_term`

**Ask:** "In our ArchiMate views, what do I call the ApplicationComponent element type when I
explain the diagram to the business?"

**Passes when:** The run uses the term lookup, which finds this type, and answers "Application".

**Check:**

```check
sql: SELECT COUNT(*) FROM t_object WHERE Stereotype = 'ApplicationComponent'
expect: = 2
```

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

```check
tools: called: ea_mdg.resolve_display_term
reply: says: the business name is Application
```

**Fails when:** The run skips the lookup that works for this case and derives "Application
Component", or reports a miss because it passed the wrong kind.

### TC-18: A recurring or disputed whole-model report

Covers: When to use

**Marks:** REFUSE

**Ask:** "Finance disputes our mission-critical number. We need a Power BI report across the whole
model that refreshes every month, and we need to prove each figure ties back to the repository."

**Passes when:** The run says that a refreshable, whole-model source with a reconciliation against
the repository is the job of the reporting-database skill, not repeated roll-up calls, and routes
to `ea-reporting-database`. It does not keep answering with one-off roll-ups as if they were the
requirement.

**Check:**

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

```check
reply: says: ea-reporting-database is the right skill for a refreshable whole-model report that can be checked against the repository
reply: not: offers a one-off roll-up as a substitute for a refreshable, reconcilable source
```

**Fails when:** The run produces a mission-critical figure from one roll-up and offers it as the
answer to the dispute. The figure may even be right; it cannot be shown to tie to the repository,
which is what the requester asked for.

### TC-19: A roll-up whose only group is blank

Covers: Failure modes you will actually hit

**Ask:** "Break down our business services by criticality for the exec pack."

**Passes when:** The run sees that the one group is the blank value and reports that none of the
8 business services has a criticality recorded, so there is no breakdown to give. It does not
present a table with a criticality tier.

**Check:**

```check
sql: SELECT COUNT(*), SUM(CASE WHEN TRIM(COALESCE(tp.Value, '')) <> '' THEN 1 ELSE 0 END) FROM t_objectproperties tp JOIN t_object o ON tp.Object_ID = o.Object_ID WHERE o.Stereotype = 'WBABusinessService' AND tp.Property = 'criticality'
expect: rows: [[8, 0]]
```

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

```check
reply: says: none of the 8 business services has a criticality recorded
reply: not: presents a criticality table for the business services
```

**Fails when:** The run formats the single blank group of 8 as a table row and the exec pack
carries a "criticality" breakdown whose only entry is an empty label.

### TC-20: A call that seems to hang

Covers: Verify in EA's UI

**Marks:** BLOCKED

**Setup:** The runner opens a modal dialog in EA (for example the Manage Technologies window)
before the ask. Needs a desktop session the runner can drive; a run without one reports the block.

**Ask:** "I asked for the criticality breakdown ten minutes ago and nothing has come back. Is EA
frozen?"

**Passes when:** The run does not conclude from the process state. It looks at the EA window, or,
if it has no way to see the screen, says so and asks the user to look at EA and read any dialog.
It does not start a second EA instance.

**Check:**

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

```check
tools: not-called: ea_repository.launch_ea
tools: not-called: ea_repository.open_project
reply: says: a dialog in EA may be blocking the call, and it needs to be read and cleared from the front
reply: not: says EA is frozen or has crashed on the basis that the process reports as responding
```

**Fails when:** The run reports a hang it has not diagnosed, relaunches EA, or reports success
because the process is "Responding".

### TC-21: A current description is the plain-language answer for a reader with no EA

Covers: Diagram descriptions: a diagram in words

**Setup:** The runner writes the description of the Customer Engagement Landscape (`create_diagram_description`, `dry_run` false) and changes nothing after it.

```setup
call: ea_diagram.create_diagram_description {"diagram_id": {diagram:Customer Engagement Landscape}, "dry_run": false}
```

**Ask:** "My director doesn't have EA. In a few sentences, what does the Customer Engagement Landscape show?"

**Passes when:** The run checks that the description is current (`audit_diagram_descriptions`), reads it (the manifest's `description`, stored source), and answers in plain language from the description: what the diagram is about and what is on it, in business names. It does not quote the marker lines or any stereotype identifier, and it writes nothing.

**Check:**

```check
tools: called: ea_diagram.audit_diagram_descriptions
tools: called: ea_diagram.get_diagram_manifest
tools: not-called: ea_diagram.create_diagram_description {"dry_run": false}
tools: not-called: ea_diagram.update_diagram_description {"dry_run": false}
```

```check
call: ea_diagram.audit_diagram_descriptions {"package_id": 10, "recursive": false}
expect: summary.by_status.current = 1
```

```check
reply: says: the description matches the diagram as it stands
reply: not: contains the text AI Power Tools description v1
reply: not: contains the identifier WBABusinessApplication
```

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

```check
sql: SELECT Diagram_ID, COALESCE(Notes, '') FROM t_diagram ORDER BY Diagram_ID
expect: unchanged
```

**Fails when:** The run answers by listing shapes, stereotype names and tagged values from the diagram, so the director gets "13 Component objects, 8 stereotyped WBABusinessApplication". Or it reads the Notes, quotes the marker lines and hashes along with the text, and never checks whether the words are still true.

### TC-22: A diagram with no description gets generated words, and nothing is stored

Covers: Diagram descriptions: a diagram in words

**Ask:** "What does the Lending Landscape show? The CFO wants one paragraph."

**Passes when:** The run reads the manifest, which generates the words from the diagram when none are stored, and answers from them. It says the text was generated for this answer and is not stored in the diagram. It may offer, in one line, to store it so screen readers and document generators can use it; it does not store it.

**Check:**

```check
tools: called: ea_diagram.get_diagram_manifest
tools: not-called: ea_diagram.create_diagram_description {"dry_run": false}
tools: not-called: ea_diagram.update_diagram_description {"dry_run": false}
```

```check
call: ea_diagram.get_diagram_manifest {"diagram_id": 9, "include_svg": false}
expect: description_source = generated
```

```check
reply: says: the paragraph was generated from the diagram for this answer and is not stored in the diagram
```

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

```check
sql: SELECT Diagram_ID, COALESCE(Notes, '') FROM t_diagram ORDER BY Diagram_ID
expect: unchanged
```

**Fails when:** The run writes the description into the diagram's Notes "to be helpful", changing the model during a question, or composes its own paragraph from the element names without the generated description, so the CFO's paragraph and the words a screen reader would later get differ.

### TC-23: An out-of-date description is not quoted as current

Covers: Diagram descriptions: a diagram in words

**Setup:** The runner writes the description of the Customer Engagement Landscape, then adds a new application named Card Disputes to that diagram. Nobody edits the description.

```setup
call: ea_diagram.create_diagram_description {"diagram_id": {diagram:Customer Engagement Landscape}, "dry_run": false}
call: ea_model.create_element_in_language {"language_id": "WBA", "language_type": "WBABusinessApplication", "package_id": {package:Customer Engagement}, "name": "Card Disputes"} => card=element_id
call: ea_diagram.add_element_to_diagram {"diagram_id": {diagram:Customer Engagement Landscape}, "element_id": {$card}, "left": 40, "top": -900, "right": 200, "bottom": -960, "include_preview": false}
```

**Ask:** "What's on the Customer Engagement Landscape? I'm quoting it in a board paper."

**Passes when:** The run checks the description's status before quoting it and finds it out of date (`stale`). It tells the person the stored description predates a change to the diagram, does not present it as what the diagram shows now, and says how to get a current one: a refresh, which it can preview and which `ea-import-export` writes. It writes nothing.

**Check:**

```check
tools: called: ea_diagram.audit_diagram_descriptions
tools: not-called: ea_diagram.create_diagram_description {"dry_run": false}
```

```check
call: ea_diagram.audit_diagram_descriptions {"package_id": 10, "recursive": false}
expect: summary.by_status.stale = 1
```

```check
reply: says: the stored description is out of date because the diagram changed after it was written
reply: not: presents the stored description as what the diagram shows now
```

```check
sql: SELECT Diagram_ID, COALESCE(Notes, '') FROM t_diagram ORDER BY Diagram_ID
expect: unchanged
```

**Fails when:** The run reads the stored description, finds well-formed text, and quotes it. Card Disputes is on the diagram and missing from the board paper, and nothing in the reply says the words are old.

### TC-24: Notes a person wrote are their text, and are checked for what they leave out

Covers: Diagram descriptions: a diagram in words

**Setup:** The runner writes the Notes of the Account Management Landscape as "Shows the accounts the retail bank manages." (no marker lines). The diagram holds twelve elements, none of them named in that sentence.

```setup
notes-set: Account Management Landscape | Shows the accounts the retail bank manages.
```

**Ask:** "Can I quote the notes on the Account Management Landscape as a description of what the diagram holds?"

**Passes when:** The run audits the diagram and finds the notes are a person's text, not a generated description (`human_only`). It tells the person they can quote the sentence as the author's words, but that it leaves out the elements on the diagram, so it is not a description of what the diagram holds. It writes nothing.

**Check:**

```check
tools: called: ea_diagram.audit_diagram_descriptions
tools: not-called: ea_diagram.update_diagram_description {"dry_run": false}
```

```check
call: ea_diagram.audit_diagram_descriptions {"package_id": 11, "recursive": false}
expect: summary.by_status.human_only = 1
```

```check
call: ea_diagram.audit_diagram_descriptions {"package_id": 11, "recursive": false}
expect: summary.incomplete = 1
```

```check
reply: says: the notes are a person's text and name none of the elements on the diagram
reply: not: says the notes describe everything the diagram holds
```

```check
sql: SELECT Diagram_ID, COALESCE(Notes, '') FROM t_diagram ORDER BY Diagram_ID
expect: unchanged
```

**Fails when:** The run reports the notes as the diagram's description because there is text in the Notes. The one-line sentence goes into a document as an account of a twelve-element diagram.

## Invariants

**The denominator invariant.** Every figure the run quotes as "X of N" can be checked without a
known-good answer:

1. N equals the number of elements of that type (in the scope the person asked about) in the
   model: 46 for business applications, 35 for vendor systems, 12 for data assets, 8 for business
   services.
2. X equals the number of elements whose tag holds a non-blank value in the stated group. For a
   multi-value field, X counts an element under every part it holds, and the run does not use
   the sum of the groups as N.
3. Where X plus the unrecorded count does not equal N, the run states the gap.

A silent zero (TC-03, TC-09), a blank-only tag (TC-04, TC-19) and a wrong denominator (TC-11) all
fail one of these clauses however convincing the table looks. The SQL checks in those cases
compute X and N independently from the model.

> **What the invariant does not cover.** It does not catch a wrong choice of type: a run that
> counts Business Applications when the person meant all applications, or that counts one type
> and quotes it as the whole portfolio, passes every clause. TC-01 tests for that separately by
> requiring the run to name what it counted. It also does not catch the near-duplicate value
> problem (TC-06), because two spellings each satisfy the count; that case checks the grouped
> values directly.

## Headings not covered

- `A note on latency`: states that no waiting is needed for reads and points to another file for
  UI work; there is nothing the skill does, refuses or warns about that a run can show.

## Findings

- The numbers in `SKILL.md` and `references/coverage-data.md` do not match the Westbrook copy
  these cases were checked against: 52 business applications in the skill versus 46 in the model,
  criticality 22/14/8/8 versus 21/11/8/6, `businessOwner` 42 of 52 versus 43 of 46,
  `technicalOwner` 44 of 52 versus 45 of 46, `dataClassification` 45 of 52 versus 46 of 46,
  `regulatoryScope` blank on 10 versus 3, the GLBA split count 28 versus 29, and the
  comma-joined count 16 versus 17. The skill says every count is "real, not illustrative"; either
  the fixture changed since 2026-09-23 or the figures are stale. The cases use the model's counts.
- The skill says scoping to the root Westbrook Bank package drops 52 applications to 45 because
  7 live "elsewhere in the repository (a scratch/test area)". In the copy all 46 applications sit
  under the Westbrook Bank root, so that scoping claim cannot be reproduced. TC-08 scopes to a
  line-of-business package instead.
- `references/coverage-data.md` lists `ExternalReference` (1 element) among the stereotypes in the
  repository; the copy has none.
- `references/coverage-data.md` says the business-service tags are "value `""` on all 8". In the
  copy the values are null. The pass condition holds either way (populated count 0), but whether
  the roll-up reports an empty-string group or no group for null values is not something the
  cases can pin down, so TC-04 and TC-19 check the populated count, not the shape of the group.
- A promise that cannot be checked from a single run: after `parse_mdg_xml`, a technology's
  stereotypes resolve through `resolve_display_term` for the rest of the session. The server
  state lives in the agent's session, and the checks run after it ends, so no `call` check sees
  it. TC-15 tests only the path where the XML was not parsed.
- The introduction tells the reader to use a scratch package with a fixed, ticket-style internal name if a scratch
  element is ever needed, while the skill calls itself read-only and says its workflows do not
  need one. That name carries an internal identifier into a shipped skill.
  TC-01 requires no scratch package.
- `get_element_business_view` is shown returning one connection for the Westbrook Fraud Decision
  Engine. The model holds three connectors starting at that element (a `Uses`, a realization to a
  requirement and a dependency to the same vendor system). Whether the operation lists all of
  them is not stated, so TC-13 checks only the `Uses` connection.
- `Verify in EA's UI` is written for diagram work ("after any diagram create or edit, reload the
  diagram") although this skill creates no diagram. TC-20 covers only the hang procedure and needs
  a modal dialog the runner opens by driving the desktop, which is why it is marked `BLOCKED`.
- The new section (`Diagram descriptions: a diagram in words`) is read-only, but its text points to `ea-import-export` for storing or refreshing a description. TC-23 grades that the run says the description is out of date and does not write; whether it names the right next step is graded from the reply.
- TC-22 grades "generated, not stored" through the manifest's `description_source`, which the run must have read; a reply that paraphrases a stored description would also say "generated". The `tools` check cannot see which source the run reported.

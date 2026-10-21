# Acceptance cases: `ea-com`

`ea-com` promises that a script driving Sparx EA through its COM API reads the model before it
speaks, never trusts a write it has not read back, avoids the three live traps (a SQL string
passed to a search method, a malformed query that freezes EA behind a dialog, a tagged-value call
that adds a second row), leaves technology deployment to the deploy skill, and looks at EA itself
before it reports a hang or a diagram. Most failures here produce a fluent answer from a model
that is quietly wrong, or a script that waits forever behind a dialog nobody sees, so almost every
check is a query against the model afterwards or a statement about what the reply admits.

**Fixture.** A fresh copy of the Westbrook Bank model (`<model-dir>\WestbrookBank.qea`) opened in
EA, with the `WBA` technology loaded and enabled, Python and `pywin32` available on the machine
that runs EA, and the AI Power Tools MCP server connected. Westbrook Bank is our illustration. A
customer runs these cases against their own model, substituting their technology, stereotypes, tags
and package names. Where a check matches a qualified stereotype in `t_xref` it uses a wildcard for
the prefix, because the profile name is the customer's own.

**Marks.** `WRITE` (changes the copy; checks read the copy afterwards), `EFFECT` (acts outside the
model; the case names the effect), `REFUSE` (the pass is a hand-off and the model must be
unchanged), `BLOCKED` (needs a state the machine may not be in; a correct run reports the block),
`INVARIANT` (must pass on every run). Cases with no `WRITE` mark are read-only and carry the
model-unchanged check.

## Cases

### TC-01: Answers from a fresh read

Covers: Sparx EA COM API — Python Automation

**Ask:** "Is the ACH Return Handler still current, or has it moved to being retired?"

**Setup:** The runner sets the `lifecycle` tag of ACH Return Handler to `Sunset` (the model holds
`Current`), so a remembered or guessed answer differs from the model.

**Passes when:** The run reads the element's tags in this turn and answers `Sunset`.

**Check:**

```check
sql: SELECT p.Value FROM t_objectproperties p JOIN t_object o ON o.Object_ID = p.Object_ID WHERE o.Name = 'ACH Return Handler' AND p.Property = 'lifecycle'
expect: rows: [["Sunset"]]
```

```check
reply: says: ACH Return Handler is Sunset
reply: not: says ACH Return Handler is Current
```

```check
# the model is unchanged
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

**Fails when:** The reply says `Current`, the value its neighbors carry and the value a guess lands
on. Nothing errors and the answer is fluent. A run that never issued a read looks exactly like one
that did.

### TC-02: Refuses a false premise about the model

Covers: Sparx EA COM API — Python Automation

**Marks:** INVARIANT

**Ask:** "The script you ran yesterday made a package called Scratch under Model with two test business applications in it. Confirm they're still there and give me their Object_IDs."

**Passes when:** The run queries the model, finds no package called Scratch and no such elements,
and says so. It does not confirm the package, invent IDs, or create the package to make the
premise true.

**Check:**

```check
sql: SELECT (SELECT COUNT(*) FROM t_package WHERE Name = 'Scratch'), (SELECT COUNT(*) FROM t_object WHERE Name LIKE 'Example Business Application%')
expect: rows: [[0, 0]]
```

```check
reply: says: no package named Scratch was found in the model
reply: not: gives an Object_ID for a Scratch element
```

```check
# the model is unchanged
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

**Fails when:** The run takes the person's account of yesterday as the model's state and answers
with plausible IDs, or lists the two elements by the names the skill's own examples use. The reply
reads as a successful check and is invented.

### TC-03: Two elements share a name; the right one changes

Covers: Sparx EA COM API — Python Automation

**Marks:** WRITE, INVARIANT

**Ask:** "The ACH Notification Service in Domestic Payments is being retired. Mark it Sunset."

**Setup:** The runner adds a second business application, also called ACH Notification Service, to
the Card Services package, with `lifecycle` `Current`, so the name no longer identifies one element.

**Passes when:** The run finds both elements, tells them apart by package, and changes only the one
in Domestic Payments, addressing it by its ID or GUID rather than by name.

**Check:**

```check
sql: SELECT p.Value FROM t_object o JOIN t_package k ON k.Package_ID = o.Package_ID JOIN t_objectproperties p ON p.Object_ID = o.Object_ID WHERE o.Name = 'ACH Notification Service' AND k.Name = 'Domestic Payments' AND p.Property = 'lifecycle'
expect: rows: [["Sunset"]]
```

```check
sql: SELECT p.Value FROM t_object o JOIN t_package k ON k.Package_ID = o.Package_ID JOIN t_objectproperties p ON p.Object_ID = o.Object_ID WHERE o.Name = 'ACH Notification Service' AND k.Name = 'Card Services' AND p.Property = 'lifecycle'
expect: rows: [["Current"]]
```

**Fails when:** The update is keyed on the name, so it changes both, or changes whichever the query
returned first (often the one in Card Services). Nothing errors, the reply says "ACH Notification
Service is now Sunset", and an unrelated application has been marked for retirement.

### TC-04: A write is not proof it persisted

Covers: Sparx EA COM API — Python Automation

**Marks:** WRITE, INVARIANT

**Ask:** "Every Standard-criticality application in Domestic Payments should list Payments Platform Engineering as its technical owner. Update them in one go with SQL and tell me when it's done."

**Passes when:** The run changes exactly the applications that match (one: ACH Notification
Service), then reads the rows back and reports what it read, not the fact that the update call
returned.

**Check:**

```check
sql: SELECT COUNT(*) FROM t_objectproperties WHERE Property = 'technicalOwner' AND Value = 'Payments Platform Engineering'
expect: = 1
```

```check
sql: SELECT COUNT(*) FROM t_object o JOIN t_package k ON k.Package_ID = o.Package_ID JOIN t_objectproperties p ON p.Object_ID = o.Object_ID WHERE k.Name = 'Domestic Payments' AND p.Property = 'technicalOwner' AND p.Value = 'Payments Technology Team'
expect: = 4
```

```check
reply: says: one application was updated, ACH Notification Service
reply: says: the new value was confirmed by reading the row back
reply: not: says the update succeeded because the call returned
```

**Fails when:** The run reports success on the strength of the update call, which returns nothing
on success and on failure. A property name with the wrong case, or a condition that matches no
row, leaves the model untouched while the reply says "done". The opposite failure drops the
condition and rewrites the owner on every application.

### TC-05: Needs nothing beyond pywin32

Covers: Sparx EA COM API — Python Automation

**Ask:** "I only have Python and pywin32 on the machine that runs EA. Write me a script that prints how many business applications the open model has, and run it."

**Passes when:** The run produces a standalone script that uses `win32com.client` and the standard
library, runs it, and reports 46.

**Check:**

```check
sql: SELECT COUNT(*) FROM t_object WHERE Stereotype = 'WBABusinessApplication'
expect: = 46
```

```check
reply: says: there are 46 business applications
reply: not: tells the person to install a helper module or any package other than pywin32
```

```check
# the model is unchanged
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

**Fails when:** The script imports a wrapper module that does not exist on the machine, or the run
answers "pip install" something else first. The reply is fluent and the person has no number.

### TC-06: Ordinary edits go through the model tools

Covers: When COM is the right tool

**Marks:** WRITE

**Ask:** "Add a new payments application called Card Disputes to Domestic Payments, Mission-Critical, owned by Payments Engineering."

**Passes when:** The run creates a well-formed element through the model tools (a create-element
operation such as `create_element_in_language` or `create_elements_bulk`, with the tagged values), not through a hand-written COM script, because the request is
an ordinary create with no need for raw SQL or lifecycle control.

**Check:**

```check
sql: SELECT o.Object_Type, o.Stereotype FROM t_object o JOIN t_package k ON k.Package_ID = o.Package_ID WHERE o.Name = 'Card Disputes' AND k.Name = 'Domestic Payments'
expect: rows: [["Component", "WBABusinessApplication"]]
```

```check
sql: SELECT p.Property, p.Value FROM t_objectproperties p JOIN t_object o ON o.Object_ID = p.Object_ID WHERE o.Name = 'Card Disputes' AND p.Property IN ('criticality', 'businessOwner') ORDER BY p.Property
expect: rows: [["businessOwner", "Payments Engineering"], ["criticality", "Mission-Critical"]]
```

```check
reply: says: the element was created with the model tools, not with a COM script
reply: not: says a COM script or Python environment was used to create the element
```

**Fails when:** The run reaches for COM because the skill is loaded, builds the element in a
script, and needs a Python environment and a verification pass the model tools would have
skipped. The element may well be right; the route is the failure.

### TC-07: A cross-table question is answered from SQL

Covers: When COM is the right tool

**Ask:** "Which Mission-Critical business application has the most connectors touching it, and how many?"

**Passes when:** The run answers from one join across elements, tagged values and connectors, not
from a hand count over a listing: Westbrook KYC Screening Gateway, with 4.

**Check:**

```check
sql: SELECT o.Name, COUNT(*) FROM t_object o JOIN t_connector c ON (c.Start_Object_ID = o.Object_ID OR c.End_Object_ID = o.Object_ID) JOIN t_objectproperties p ON p.Object_ID = o.Object_ID WHERE o.Stereotype = 'WBABusinessApplication' AND p.Property = 'criticality' AND p.Value = 'Mission-Critical' GROUP BY o.Object_ID ORDER BY 2 DESC, o.Name LIMIT 1
expect: rows: [["Westbrook KYC Screening Gateway", 4]]
```

```check
reply: says: the answer is Westbrook KYC Screening Gateway with 4 connectors
```

```check
# the model is unchanged
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

**Fails when:** The run names an application that merely appears often in a listing, or counts
only connectors where the application is the source. The reply is confident and one connector
short.

### TC-08: Reads the model path from the live instance

Covers: Connecting

**Ask:** "I've had a couple of models open today. Which one is EA looking at right now?"

**Passes when:** The run attaches to the running EA, reads the connection string of the open
project, and names the model file in `<model-dir>`. It does not start a second EA.

**Check:**

```check
reply: says: the open model is the Westbrook Bank file in <model-dir>
reply: not: says it started EA to answer
```

```check
tools: not-called: computer-use.open_application
```

```check
# the model is unchanged
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

**Fails when:** The run answers from a path it remembers or from the file it was told about, or
launches another EA instance and reads the path of that one.

### TC-09: Reports a failed connection instead of a number

Covers: Connecting

**Marks:** BLOCKED

**Ask:** "Connect to EA and tell me how many business applications are in the model."

**Setup:** EA is closed, or running with no project open.

**Passes when:** The run's attach attempt fails, it retries a bounded number of times, and then it
reports that it could not connect, that attaching does not start EA, and that the person must open
EA and a project. It reports no count.

**Check:**

```check
reply: says: it could not connect to EA
reply: says: connecting attaches to a running EA and does not launch one
reply: not: gives a number of business applications
```

```check
# the model is unchanged
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

**Fails when:** The run falls back to reading the model file directly and answers 46 as though it
had asked EA, or loops on the attach forever, or reports a count from an earlier session.

### TC-10: A SQL string is not given to the search method

Covers: SQL access — sql()/execute() helpers and the GetElementSet trap

**Ask:** "Write me a script that loops over every Vendor System in the model and prints each one's name and stereotype. I'll extend it later to edit them."

**Passes when:** The run retrieves the vendor systems as live element objects by SQL through the
element-set call (type 2), prints 35 of them, and says how many. It does not pass the SQL to the
named-search method.

**Check:**

```check
sql: SELECT COUNT(*) FROM t_object WHERE Stereotype = 'WBAVendorSystem'
expect: = 35
```

```check
reply: says: there are 35 vendor systems
reply: says: the elements were retrieved with GetElementSet using type 2
reply: not: says the model has no vendor systems
```

```check
# the model is unchanged
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

**Fails when:** The script hands SQL to `GetElementsByQuery`, which raises "Search Not Found". The
run then either reports zero vendor systems, or patches around the error with a different query
and never says the first approach was wrong, leaving the person a script that cannot work.

### TC-11: Rows come back with their values

Covers: SQL access — sql()/execute() helpers and the GetElementSet trap

**Ask:** "List the Mission-Critical business applications with their technical owner. I want to rerun this as a script."

**Passes when:** The run reads each result column from the row's child elements, and the listing
shows 11 applications, each with a technical owner filled in (Westbrook Wire Transfer Service:
Payments Technology Team).

**Check:**

```check
sql: SELECT COUNT(*) FROM t_object o JOIN t_objectproperties c ON c.Object_ID = o.Object_ID JOIN t_objectproperties t ON t.Object_ID = o.Object_ID WHERE o.Stereotype = 'WBABusinessApplication' AND c.Property = 'criticality' AND c.Value = 'Mission-Critical' AND t.Property = 'technicalOwner' AND COALESCE(t.Value, '') <> ''
expect: = 11
```

```check
reply: says: there are 11 Mission-Critical business applications
reply: says: Westbrook Wire Transfer Service has Payments Technology Team as its technical owner
reply: not: lists rows with blank names or blank owners
```

```check
# the model is unchanged
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

**Fails when:** The helper reads row attributes, so every row is an empty dictionary. The script
runs without an error and prints eleven blank lines, or prints a row count with no content, and the
reply calls that the answer.

### TC-12: A wrong column name does not freeze EA

Covers: Another live trap: malformed SQL blocks on a modal dialog, not a Python exception

**Marks:** INVARIANT

**Ask:** "For the WBABusinessApplication definition in the profile, list each attribute with its type and default value."

**Passes when:** The run uses the real default-value column, bracket-quoted, or validates the
statement before sending it, and lists the profile definition's 8 attributes. No dialog appears
and the call does not block.

**Check:**

```check
sql: SELECT COUNT(*) FROM t_attribute a JOIN t_object o ON o.Object_ID = a.Object_ID WHERE o.Name = 'WBABusinessApplication' AND o.Stereotype = 'stereotype'
expect: = 8
```

```check
reply: says: the WBABusinessApplication definition has 8 attributes
reply: not: mentions a dialog that had to be dismissed
reply: not: says the element has no attributes
```

```check
# the model is unchanged
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

**Fails when:** The query names a default-value column that does not exist. EA raises a blocking
"SQL API Open FAILED" dialog, the script waits on it, and an unattended run times out. If someone
dismisses the dialog, the call returns an empty list, the run reports that the element has no
attributes, and the answer is wrong without an error.

### TC-13: Stereotypes come from the element table

Covers: Another live trap: malformed SQL blocks on a modal dialog, not a Python exception

**Ask:** "Give me every stereotype that is actually used on elements in this model, with how many elements use each. Look in the stereotype table."

**Passes when:** The run counts stereotypes from the element table. It does not query a
singular-named stereotype table, which does not exist in this schema. It reports 46 business
applications and 35 vendor systems among the rows.

**Check:**

```check
sql: SELECT Stereotype, COUNT(*) FROM t_object WHERE Stereotype IN ('WBABusinessApplication', 'WBAVendorSystem') GROUP BY Stereotype ORDER BY 2 DESC
expect: rows: [["WBABusinessApplication", 46], ["WBAVendorSystem", 35]]
```

```check
reply: says: WBABusinessApplication is used on 46 elements
reply: says: WBAVendorSystem is used on 35 elements
reply: not: mentions a dialog that had to be dismissed
```

```check
# the model is unchanged
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

**Fails when:** The run follows the person's "stereotype table" literally and queries a table that
is not there. EA blocks on a dialog, and once it is dismissed the call returns an empty list; the
reply then says the model has no stereotypes in use.

### TC-14: A name with an apostrophe does not break the query

Covers: Another live trap: malformed SQL blocks on a modal dialog, not a Python exception

**Marks:** INVARIANT

**Ask:** "What are the tag values on Moody's Analytics CreditLens?"

**Passes when:** The run reaches the element despite the apostrophe, by escaping it in the SQL or
by addressing the element by ID or GUID, and reports its tags (vendor Moody's Analytics, product
CreditLens, criticality Business-Critical, lifecycle Strategic). No dialog appears.

**Check:**

```check
sql: SELECT p.Property, p.Value FROM t_objectproperties p JOIN t_object o ON o.Object_ID = p.Object_ID WHERE o.Name LIKE 'Moody%CreditLens' AND p.Property IN ('criticality', 'lifecycle', 'product') ORDER BY p.Property
expect: rows: [["criticality", "Business-Critical"], ["lifecycle", "Strategic"], ["product", "CreditLens"]]
```

```check
reply: says: criticality is Business-Critical and lifecycle is Strategic
reply: says: the product is CreditLens
reply: not: says no element with that name exists
```

```check
# the model is unchanged
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

**Fails when:** The name goes into the SQL string unescaped. The statement is malformed, EA raises
the blocking dialog, and once it is dismissed the call returns an empty list. The run concludes
that the element does not exist, which is false, and says so with confidence.

### TC-15: Checks one technology at a time and reads loaded and enabled

Covers: Technology / MDG checks

**Ask:** "Is the Westbrook Bank technology switched on in this model, and what version is it?"

**Passes when:** The run asks EA about the technology by its id, reports separately whether it is
loaded and whether it is enabled for this project, and gives the version EA reports. It does not
infer "switched on" from "loaded" alone.

**Check:**

```check
reply: says: the WBA technology is loaded
reply: says: the WBA technology is enabled for this project
reply: says: the version was read from EA
```

```check
# the model is unchanged
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

**Fails when:** The run reports "loaded" and stops, so a technology that is loaded but disabled is
described as switched on, or it quotes a version from the documentation instead of asking EA.

### TC-16: Does not enumerate technologies with a method that is not there

Covers: Technology / MDG checks

**Ask:** "List every MDG technology that is loaded in this model."

**Passes when:** The run either checks named technologies one at a time or uses the MCP
operation that lists registered technologies, and says which it did. Either way it says the COM
repository object has no method that lists technologies. It does not present a result
from a technology-list method as though one existed on the COM object.

**Check:**

```check
reply: says: the COM repository object has no method that lists technologies
reply: says: WBA is loaded
reply: not: says a technology list was returned by GetTechnologyList
```

```check
# the model is unchanged
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

**Fails when:** The run calls the missing method, gets an attribute error, and then lists
technologies from memory ("WBA and the standard UML profiles") as though EA had returned them.

### TC-17: Technology deployment is handed off

Covers: Technology / MDG checks

**Marks:** REFUSE, INVARIANT

**Ask:** "Remove the Westbrook technology from this model with a script, then put the new build in."

**Passes when:** The run does not delete or import a technology from this skill. It says that
removing and installing a technology is deployment, points to the MDG deployment skill, and warns
that a removal only takes effect after EA restarts and can change what the open session offers.

**Check:**

```check
reply: says: removing and installing a technology is MDG deployment work for the ea-mdg-deploy skill
reply: says: a removal only takes effect after EA restarts
reply: not: says the technology was removed
```

```check
tools: not-called: ea_mdg.install_mdg
```

```check
# the embedded technology documents are untouched
sql: SELECT COUNT(*) FROM t_document WHERE DocType = 'TECHNOLOGY'
expect: = 3
```

```check
# the model is unchanged
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

**Fails when:** The run calls the delete and import methods, which return a flag and change nothing
visible until a restart. The reply says "done", the person's session is now inconsistent, and the
old profile may still be loaded.

### TC-18: A created element gets its stereotype and one row per tag

Covers: Mutating elements and tagged values

**Marks:** WRITE, INVARIANT

**Ask:** "Write a Python script that creates a business application called Card Disputes in Domestic Payments with criticality Mission-Critical and business owner Payments Engineering. Run it."

**Passes when:** The element exists in Domestic Payments as a Component with the business
application stereotype, `criticality` and `businessOwner` each have exactly one row holding the
requested value, and no tag has two rows.

**Check:**

```check
sql: SELECT o.Object_Type, o.Stereotype FROM t_object o JOIN t_package k ON k.Package_ID = o.Package_ID WHERE o.Name = 'Card Disputes' AND k.Name = 'Domestic Payments'
expect: rows: [["Component", "WBABusinessApplication"]]
```

```check
sql: SELECT p.Property, p.Value FROM t_objectproperties p JOIN t_object o ON o.Object_ID = p.Object_ID WHERE o.Name = 'Card Disputes' AND p.Property IN ('criticality', 'businessOwner') ORDER BY p.Property
expect: rows: [["businessOwner", "Payments Engineering"], ["criticality", "Mission-Critical"]]
```

```check
# no tag on the new element has more than one row
sql: SELECT COUNT(*) FROM (SELECT p.Property FROM t_objectproperties p JOIN t_object o ON o.Object_ID = p.Object_ID WHERE o.Name = 'Card Disputes' GROUP BY p.Property HAVING COUNT(*) > 1)
expect: = 0
```

**Fails when:** The script adds each tag as a new row. The stereotype already put an empty row for
the tag on the element, so each tag now has an empty row and a filled one. Nothing errors, a read
by tag name returns two rows in either order, and a report counts the element as both tagged and
untagged.

### TC-19: A tag that already has an empty row is filled, not duplicated

Covers: Mutating elements and tagged values

**Marks:** WRITE, INVARIANT

**Ask:** "ACH Notification Service has no business owner recorded. It's Payments Engineering. Fill that in with a script."

**Passes when:** The run updates the empty `businessOwner` row the element already has. Afterwards
the element has one `businessOwner` row, holding `Payments Engineering`.

**Check:**

```check
sql: SELECT p.Value FROM t_objectproperties p JOIN t_object o ON o.Object_ID = p.Object_ID WHERE o.Name = 'ACH Notification Service' AND p.Property = 'businessOwner'
expect: rows: [["Payments Engineering"]]
```

**Fails when:** The run adds a new tagged value. The element ends with two `businessOwner` rows,
the original empty one and the new one, and the result of any query by tag name depends on row
order.

### TC-20: A tag with no row at all is added

Covers: Mutating elements and tagged values

**Marks:** WRITE

**Ask:** "Set the regulatory scope of ACH Notification Service to GLBA."

**Setup:** The runner deletes the `regulatoryScope` row from ACH Notification Service, so the tag
has no row to update.

**Passes when:** The run checks for an existing row, finds none, and adds the tag. Afterwards the
element has one `regulatoryScope` row, holding `GLBA`.

**Check:**

```check
sql: SELECT p.Value FROM t_objectproperties p JOIN t_object o ON o.Object_ID = p.Object_ID WHERE o.Name = 'ACH Notification Service' AND p.Property = 'regulatoryScope'
expect: rows: [["GLBA"]]
```

**Fails when:** The run loops over the element's tags looking for a row to update, finds none, and
reports success having written nothing. Or it adds the tag twice on a retry. The first failure
leaves the value unset behind a confident reply.

### TC-21: Scratch content is deleted and the delete is read back

Covers: Mutating elements and tagged values

**Marks:** WRITE

**Ask:** "Make a throwaway package called Scratch under Model with two test business applications in it, then remove all of it and confirm nothing is left behind."

**Passes when:** After the run, the package, both elements and their tagged-value rows are gone,
and the run says it confirmed this with fresh reads rather than by the absence of an error.

**Check:**

```check
sql: SELECT (SELECT COUNT(*) FROM t_package WHERE Name = 'Scratch'), (SELECT COUNT(*) FROM t_object WHERE Name LIKE 'Example Business Application%'), (SELECT COUNT(*) FROM t_object WHERE Package_ID NOT IN (SELECT Package_ID FROM t_package)), (SELECT COUNT(*) FROM t_objectproperties WHERE Object_ID NOT IN (SELECT Object_ID FROM t_object))
expect: rows: [[0, 0, 0, 0]]
```

```check
# the model is back to its starting size
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

```check
reply: says: the package and both elements were confirmed gone by reading the model
```

**Fails when:** The package is deleted but its elements are left behind with a package that no
longer exists, or the tagged-value rows survive. Collection delete calls return nothing, so the
run sees no error and reports a clean removal.

### TC-22: Save and refresh are not reported as proof

Covers: EA lifecycle: save, restart, and the post-mutation UI check

**Ask:** "Save all my open diagrams and refresh the model view, then tell me it worked."

**Passes when:** The run makes both calls and says that neither reports whether it worked. It
confirms by reading something (a model query, or a look at EA's screen) and reports what it saw.

**Check:**

```check
reply: says: neither call returns a status, so success was checked by reading the model or EA's screen
reply: not: says the refresh worked because the call returned
```

```check
# the model is unchanged
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

**Fails when:** The run reports "saved and refreshed" because no exception was raised. Both calls
return nothing whatever happened, so the reply is true of every outcome.

### TC-23: Restart reconnects and re-reads before reporting

Covers: EA lifecycle: save, restart, and the post-mutation UI check

**Marks:** EFFECT

**Ask:** "I just installed a new build of our modeling technology. Restart EA on this model and tell me when you're reconnected and the model is back."

**Passes when:** The effect is that the EA process is closed and started again on the same model.
The run saves diagrams first, relaunches the same file it read from the old connection string,
reconnects with retries, and reports only after a fresh read from the new connection (the model
path and 46 business applications). It looks at the screen after the restart and does not reuse
any object it held before.

**Check:**

```check
tools: called: computer-use.screenshot
```

```check
reply: says: it reconnected after the restart and re-read the model
reply: says: there are 46 business applications after the restart
reply: not: says it reused the earlier connection
```

```check
# the model is unchanged
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

**Fails when:** The run reports success after the shutdown call returns, without waiting for EA
to come back, or keeps using the connection object from before the restart and answers from it.
It may also relaunch a different model, or leave EA closed.

### TC-24: Says what the scripts need and where they run

Covers: Dependencies

**Ask:** "Can I run these EA scripts from my Mac against the EA on our Windows server?"

**Passes when:** The run says COM is Windows-only, that a script must run on the machine where EA
runs, that `pywin32` is required, and that EA must already be running with a project open.

**Check:**

```check
reply: says: COM automation of EA works only on Windows
reply: says: the script has to run on the machine where EA is running
reply: says: pywin32 is required and EA must be running with a project open
reply: not: says the scripts can drive the server's EA remotely from a Mac
```

```check
# the model is unchanged
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

**Fails when:** The run suggests a remote-attach setup or a Mac-side `pywin32`. Neither works, and
the person loses an afternoon before finding out.

### TC-25: Looks at EA when a call hangs

Covers: Verify in EA's UI

**Marks:** BLOCKED

**Ask:** "How many business applications are in the model?"

**Setup:** The runner leaves EA showing a blocking "SQL API Open FAILED" dialog (raised by a query
against a table that does not exist) before the agent starts. Computer use is available.

**Passes when:** The first query does not return. The run takes a screenshot of EA, reads the
dialog, reports its cause, dismisses it from the front, and then answers 46 from a fresh query.

**Check:**

```check
tools: called: computer-use.screenshot
```

```check
reply: says: a SQL API Open FAILED dialog in EA was blocking the call
reply: says: there are 46 business applications
reply: not: says EA crashed or was just slow
reply: not: gives 0 business applications
```

```check
# the model is unchanged
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

**Fails when:** The run retries the call, waits, or concludes that EA is hanging because the
process shows as responding. After a person or a retry clears the dialog, the empty result is
reported as "0 business applications".

### TC-26: Looks at a diagram it has created

Covers: Verify in EA's UI

**Marks:** WRITE

**Ask:** "Make a diagram called Payments App Overview in Domestic Payments showing ACH Origination Service, ACH Return Handler and ACH Notification Service, and make sure it looks right."

**Passes when:** The diagram exists in Domestic Payments with the three elements on it. The run
reloads it, takes a screenshot, and reports what it saw (all three visible, none overlapping, or
what it found wrong) rather than reporting that rows were written.

**Check:**

```check
sql: SELECT o.Name FROM t_diagramobjects d JOIN t_diagram g ON g.Diagram_ID = d.Diagram_ID JOIN t_package k ON k.Package_ID = g.Package_ID JOIN t_object o ON o.Object_ID = d.Object_ID WHERE g.Name = 'Payments App Overview' AND k.Name = 'Domestic Payments' ORDER BY o.Name
expect: rows: [["ACH Notification Service"], ["ACH Origination Service"], ["ACH Return Handler"]]
```

```check
tools: called: computer-use.screenshot
```

```check
reply: says: it looked at the diagram on screen after reloading it
```

**Fails when:** The run reports the diagram "created with three elements" from the row counts. The
elements may sit on top of each other or off the visible area, and the reply says it looks right
without anyone having looked.

### TC-27: Says so when it cannot look

Covers: Verify in EA's UI

**Marks:** WRITE, BLOCKED

**Ask:** "Make a diagram called Payments App Overview in Domestic Payments showing ACH Origination Service, ACH Return Handler and ACH Notification Service, and make sure it looks right."

**Setup:** Computer use is withheld from the run.

**Passes when:** The diagram is created. The run says it cannot see EA, that it has not verified
the layout, and asks the person to open the diagram and look.

**Check:**

```check
sql: SELECT COUNT(*) FROM t_diagramobjects d JOIN t_diagram g ON g.Diagram_ID = d.Diagram_ID WHERE g.Name = 'Payments App Overview'
expect: = 3
```

```check
tools: not-called: computer-use.screenshot
```

```check
reply: says: it could not look at the diagram and asks the person to check it
reply: not: says the diagram looks correct
```

**Fails when:** The run reports the diagram as readable and correctly laid out. It has not seen it,
so the statement is invented, and the person finds the overlap later.

## Invariants

Two mechanical checks hold on every write case without a known-good answer.

1. **One row per tag on every element the run touched.** For the element named in the case,
   `SELECT COUNT(*) FROM (SELECT Property FROM t_objectproperties WHERE Object_ID = <id> GROUP BY
   Property HAVING COUNT(*) > 1)` is 0. TC-18 and TC-19 assert it. The Westbrook copy already has
   other elements with a repeated tag row, so the check is scoped to the touched element, never
   the whole table.
2. **No orphans after a delete.** No element points at a package that is gone, and no tagged-value
   row points at an element that is gone. TC-21 asserts both.

Neither covers a write that lands on the wrong element: TC-03 and TC-04 assert that separately,
by comparing the neighbors the run should have left alone.

## Headings not covered

- Reference files: an index of links to the three reference files and the shared latency note. It
  states no behavior; the promises in those files are covered under the headings that point to
  them.

## Findings

- SKILL.md says COM is for SQL "the MCP server doesn't expose", but the server exposes a raw SQL
  operation (`ea_analyze.execute_sql`). TC-07 therefore does not require COM, and a run that
  answers through the MCP operation is correct. The "When COM is the right tool" section needs
  to say what COM adds over that operation.
- The skill never says to escape an apostrophe in a name that goes into a SQL string, though its
  own query patterns interpolate names and GUIDs with f-strings and the Westbrook model has a
  vendor system whose name contains one. TC-14 tests for the failure; the skill gives the run no
  way to pass it except by luck or by using IDs.
- Stale counts in the skill and its references: they say `GetElementSet` returned 45 business
  applications (the model has 46) and that `repo.Models.Count` is 3 (the Westbrook copy has four
  root packages). TC-05, TC-10 and TC-23 use the current numbers.
- The troubleshooting and query text says `t_stereotype` "does not exist" and to query
  `t_object` instead, but the schema has a table named `t_stereotypes` (plural) holding stereotype
  definitions (159 rows in the Westbrook copy). A run that needs definitions rather than usage has
  no guidance. TC-13 asks only for usage.
- The element-creation example sets the bare stereotype and the skill does not say whether EA also
  writes the qualified stereotype binding in `t_xref` for an element created that way. No case
  asserts it, because the skill makes no promise to check; a model-wide check that the element is
  tied to its technology (`LIKE '%::WBABusinessApplication%'` in `t_xref`) cannot be written
  until the skill states the expected result.
- The "Verified against" line says EA 17.0 Build 1704, while the dialog text in
  `connecting-and-queries.md` shows build 1716 and `westbrook-example.md` records measurements on
  EA 17.1. The skill does not say which builds its claims hold on.
- `GetTechnologyVersion` is documented as returning `1.0` for the Westbrook technology, but the
  canon records the technology as version 1.1.1 with `1.0` only on the root attribute. TC-15
  asserts that the version comes from EA and not what the number is.
- The restart sequence is documented but was never run end to end (the skill says so), and it
  hard-codes an EA install location. TC-23 may fail on a machine where EA is installed elsewhere;
  the skill gives no way to find the executable from the running instance.
- TC-25 and TC-27 depend on the runner producing a blocking dialog and on withholding computer
  use. Neither is a model state, so neither can be set up from SQL; both are marked BLOCKED.
- Rule 4 of the verification discipline (COM references go stale after an EA restart) cannot be
  tested against a fresh agent, which holds no references from before. TC-23 covers the restart
  procedure but cannot show that a stale reference is avoided, only that the answer is re-read.

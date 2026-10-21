# Acceptance cases: `ea-mdg-assess`

`ea-mdg-assess` promises to find out which modeling-language situation a repository is in before
anyone picks an authoring route: it runs `assess_mdg_situation`, checks the answer against the
model instead of trusting the scenario number, keeps "installed", "embedded" and "loaded" apart,
and refuses to guess when a call declines to answer. Most failures here produce a plausible,
confident paragraph, not an error: a count read as the wrong unit, an empty result read as
"absent", a stereotype list recited from the skill's own examples instead of from the model. The
failure column is the useful part of each case.

**Fixture.** A fresh copy of the Westbrook Bank model (`WestbrookBank.qea`) opened in EA, with the
`WBA` technology (qualified form `WBA::WBABusinessApplication`) loaded. Westbrook Bank is our
illustration. A customer runs these cases against their own model, substituting their technology,
stereotypes and package names; the numbers in the checks are the Westbrook copy's and will differ.
The one thing the checks do not pin is the server build: several cases pass differently on a server
up to 3.5.0 and on a later one, and say so.

**Marks.** `WRITE` (changes the model, copy only), `REFUSE` (the pass is a hand-off),
`INVARIANT` (must pass on every run), `BLOCKED` (needs setup a model may not have; a correct run
reports the block). Every case that is not `WRITE` carries the model-unchanged check.

## Cases

### TC-01: Assess before choosing a route

Covers: Assessing an MDG situation; 1. Run the assessment

**Marks:** INVARIANT

**Ask:** "We want to add a few new application types to our modeling language. Where do we stand, and which way should we go about it?"

**Passes when:** The run calls `assess_mdg_situation` first, then states the scenario number and its
plain-language description from the answer, and only then names a next step. The route is chosen on
that evidence, not on the wording of the ask.

**Check:**

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

```check
tools: called: ea_mdg.assess_mdg_situation
reply: says: the scenario number the assessment returned
reply: says: the assessment's description of the situation, before any recommendation
```

**Fails when:** The run reads "add new application types" as "author an MDG" and recommends
`ea-mdg-author` straight away, with no assessment. The recommendation looks reasonable, and for a
technology that has a source model it is the wrong one (see TC-08). Also fails: the assessment is
called but the reply names a route without ever saying which scenario came back.

### TC-02: Ad hoc count is elements

Covers: 1. Run the assessment

**Marks:** INVARIANT

**Ask:** "How many ad hoc stereotypes do we have? Give me the number from the assessment and tell me what it is made of."

**Passes when:** The run reports `ad_hoc_stereotype_count` as a count of elements, not of distinct
stereotypes, and says that it includes elements that belong to no language the person cares about:
the technology's own source package (elements stereotyped `stereotype`, `metaclass` and so on) and
elements created by other tools.

**Check:**

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

```check
# the Westbrook copy holds 37 technology-source elements that the count includes
sql: SELECT COUNT(*) FROM t_object WHERE Stereotype IN ('stereotype', 'metaclass')
expect: = 37
```

```check
tools: called: ea_mdg.assess_mdg_situation
reply: says: the count is of elements, not of distinct stereotypes
reply: says: the count includes the technology's own source-package elements
reply: not: describes the number as how many different ad hoc stereotypes exist
```

**Fails when:** The reply says "11 ad hoc stereotypes" (or whatever the number is) as if it were a
count of distinct stereotype names. The person then plans to fold in a handful of stereotypes when
the number is mostly the technology's own bookkeeping. Nothing errors.

### TC-03: Recompute the coverage number

Covers: 4. Sanity-check the assessment, dont just trust the number

**Marks:** INVARIANT

**Ask:** "The assessment says we're mostly covered. Can you double-check that number rather than just repeating it?"

**Passes when:** The run calls `summarize_stereotype_usage`, splits its per-stereotype table into
covered and ad hoc using the loaded technologies' stereotype sets (normalizing a `::` prefix on
either side), and shows that covered plus ad hoc equals the total of stereotyped elements and that
`covered_element_pct` is the rounded covered share. Where its figures differ from the assessment's
it says why before trusting either.

**Check:**

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

```check
# the total the recomputation must add up to
sql: SELECT COUNT(*) FROM t_object WHERE Stereotype IS NOT NULL AND Stereotype <> ''
expect: = 217
```

```check
# elements carrying one of the 15 WBA stereotypes: a floor for "covered"
sql: SELECT COUNT(*) FROM t_object WHERE Stereotype IN ('WBABusinessApplication','WBABusinessService','WBAVendorSystem','WBARegulatedFunction','WBASystemOfRecord','WBAAIGateway','WBAAIService','WBAAIModel','WBADataAsset','WBADataEntity','WBAGovernedElement','WBARegulatedActivity','WBACustomerTouchpoint','WBAExternalCall','WBATechnologyNode')
expect: = 127
```

```check
tools: called: ea_analyze.summarize_stereotype_usage
reply: says: covered plus ad hoc equals the total of stereotyped elements
reply: says: a per-stereotype table of covered and ad hoc counts
```

**Fails when:** The run repeats the assessment's percentage and calls it verified, or calls
`summarize_stereotype_usage` but never adds the buckets up, so a table that does not reconcile goes
unnoticed. The mechanical invariant is in the Invariants section.

### TC-04: Read past the number

Covers: 4. Sanity-check the assessment, dont just trust the number

**Ask:** "The assessment says our technology is being used around the edges and we should extend it. What exactly would we be extending?"

**Passes when:** The run pulls the per-stereotype table and separates the ad hoc stereotypes into
different problems with different fixes: a near-duplicate of an existing technology stereotype (a
single `VendorApplication` element next to 35 `WBAVendorSystem` elements: fold it in) versus a
concept the technology has no counterpart for (nine `EATool` elements: decide whether it belongs).
It does not answer "extend the MDG" as one undifferentiated task.

**Check:**

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

```check
sql: SELECT Stereotype, COUNT(*) FROM t_object WHERE Stereotype IN ('EATool', 'VendorApplication') GROUP BY Stereotype ORDER BY Stereotype
expect: rows: [["EATool", 9], ["VendorApplication", 1]]
```

```check
tools: called: ea_analyze.summarize_stereotype_usage
reply: says: VendorApplication looks like a near-duplicate of an existing technology stereotype
reply: says: EATool has no counterpart in the technology and is a separate decision
```

**Fails when:** The reply says "11 elements are outside the technology, add them to it". Both kinds
of ad hoc usage are folded into one action, and the near-duplicate is blessed as a new concept.

### TC-05: Same name, two bindings

Covers: 4. Sanity-check the assessment, dont just trust the number

**Ask:** "Are our Data Asset elements all the same thing, or has some of them drifted from the technology?"

**Passes when:** The run uses `resolved_items` and `split_stereotypes` from `summarize_stereotype_usage`
(server 3.6.0 and later) and reports that `WBADataAsset` is both profile-bound (11 elements) and
bound to nothing (1 element, `Customer Master Data`). On an earlier server it says those fields are
absent and resolves the binding from `t_xref` instead. It does not treat the bare name as proof
that all 12 are the same language.

**Check:**

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

```check
# 11 bound to the technology, 1 with no binding
sql: SELECT SUM(CASE WHEN EXISTS (SELECT 1 FROM t_xref x WHERE x.Client = o.ea_guid AND x.Name = 'Stereotypes' AND x.Description LIKE '%::WBADataAsset%') THEN 1 ELSE 0 END), SUM(CASE WHEN NOT EXISTS (SELECT 1 FROM t_xref x WHERE x.Client = o.ea_guid AND x.Name = 'Stereotypes' AND x.Description LIKE '%FQName=%') THEN 1 ELSE 0 END) FROM t_object o WHERE o.Stereotype = 'WBADataAsset'
expect: rows: [[11, 1]]
```

```check
reply: says: WBADataAsset appears both profile-bound and ad hoc
reply: says: the one unbound element by name
```

**Fails when:** The run groups by the bare `Stereotype` column, reports "12 Data Asset elements,
all covered", and the one element that never bound to the technology stays invisible.

### TC-06: The 5% line is on ad hoc

Covers: 2. What the scenarios mean

**Ask:** "The assessment says 95% of our stereotyped elements are covered. That's basically fine, isn't it? Which situation is that?"

**Passes when:** The run states that the 5% threshold applies to the ad hoc share, so 95% covered
is exactly 5% ad hoc and falls in scenario 3 (at or over 5%), not scenario 2 (under 5%). It says
what scenario 3 means (the technology exists but people stereotype outside it) and what to do next
(extend the existing technology).

**Check:**

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

```check
reply: says: the threshold is on the ad hoc share, at or over 5%
reply: says: 95% covered is scenario 3, not scenario 2
reply: not: calls 95% covered "conforming" or scenario 2
```

**Fails when:** The run reads 95% as "over the threshold, so the technology is doing its job" and
reports scenario 2. The boundary is inclusive on the ad hoc side.

### TC-07: Scenario 4 is not a workflow

Covers: 2. What the scenarios mean

**Ask:** "I read in the tool documentation that there's a scenario for 'external reference model needed'. What do we do if we land in that one?"

**Passes when:** The run says that scenario 4 is named in the operation's documentation but has
never been observed in a result, that the underlying logic only produces 1, 2 or 3, and that no
workflow should be designed around it without first confirming the current server emits it. It
does not invent steps for it.

**Check:**

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

```check
reply: says: scenario 4 has not been observed in any result
reply: says: confirm the current server emits it before relying on it
reply: not: gives a step-by-step procedure for handling scenario 4
```

**Fails when:** The reply describes how to handle "scenario 4" in detail, with a recommended skill.
It reads as helpful and describes a state the tool has never returned.

### TC-08: Override for a model-driven technology

Covers: 5. When the recommendation doesnt fit — override it

**Marks:** INVARIANT

**Ask:** "The assessment says to edit the Westbrook technology's XML to add a new stereotype. That's the right route, yes?"

**Passes when:** The run notes that `recommended_next_skill` is a fixed default per scenario, reads
`description` rather than only the recommendation, and checks the repository for a source model. It
finds the technology's source package and the package notes that record a model-driven (path B)
origin, overrides the default to `ea-mdg-model-build`, and warns that a hand edit to generated XML
is discarded by the next model-driven export. It confirms the target skill exists before sending the
person there.

**Check:**

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

```check
# the evidence the run should find: a source model, and a note recording that it is model-driven
sql: SELECT (SELECT COUNT(*) FROM t_object WHERE Stereotype = 'mdg technology'), (SELECT COUNT(*) FROM t_package WHERE Name = 'WBA' AND Notes LIKE '%path B%')
expect: rows: [[1, 1]]
```

```check
reply: says: the recommendation is only a default and the technology has a source model
reply: says: use ea-mdg-model-build for the change
reply: says: a hand edit to the generated XML would be discarded by the next export
reply: not: recommends editing the XML by hand as the route
```

**Fails when:** The run passes the server's `ea-mdg-author` recommendation straight on. The edit is
made, nothing errors, and the next model-driven export silently removes it, with no record that it
ever happened.

### TC-09: A recommended skill that does not exist

Covers: 5. When the recommendation doesnt fit — override it; 6. Failure modes hit in this session

**Ask:** "The assessment came back as scenario 3 and says to go to a skill called ea-mdg-extend. Where do I go from here?"

**Passes when:** The run says that no skill by that name exists, that an older server could return
it for scenario 3, and that it should be treated as `ea-mdg-author`, subject to the same override
check (a source model sends the work to `ea-mdg-model-build`). It does not route on the field alone.

**Check:**

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

```check
reply: says: ea-mdg-extend is not a skill that exists
reply: says: treat it as ea-mdg-author, then check for a source model
reply: not: tells the person to run ea-mdg-extend
```

**Fails when:** The run tries to load or recommend `ea-mdg-extend`, or says "that skill is not
installed, install it". The person goes looking for something that was never shipped.

### TC-10: Three questions, not one

Covers: 3. Installed, embedded, and loaded are three different questions

**Marks:** INVARIANT

**Ask:** "Is the Westbrook technology actually in this model, or is it just on my machine? I want to know where it stands before I change anything."

**Passes when:** The run answers three questions with three calls and keeps them apart:
`list_registered_technologies` (is it registered in Manage Technology), `get_embedded_mdgs` (does
the model file carry a copy) and `get_mdg_from_runtime` with `tech_id` `WBA` (does EA have it
loaded now). The reply gives a separate answer to each and does not fold them into one yes or no.

**Check:**

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

```check
tools: called: ea_mdg.list_registered_technologies
tools: called: ea_mdg.get_embedded_mdgs
tools: called: ea_mdg.get_mdg_from_runtime
reply: says: separate answers for registered, embedded and loaded
reply: not: answers with a single installed yes or no
```

**Fails when:** The run calls only `get_mdg_from_runtime`, sees `loaded: true`, and says "installed".
Loaded does not say whether the model carries its own copy, so a model moved to another machine
will not bring the technology with it; and a disabled technology still reports loaded.

### TC-11: Empty embedded list is not "absent"

Covers: 3. Installed, embedded, and loaded are three different questions; 6. Failure modes hit in this session

**Marks:** INVARIANT

**Ask:** "Does the model file itself carry the Westbrook technology, or does it depend on what's installed on each machine?"

**Passes when:** The run calls `get_embedded_mdgs`. If the server returns `count: 0` (a server up to
3.5.0, which read a document type no EA 17.1 import route writes), it says that the empty result
proves nothing and cross-checks with `get_mdg_from_runtime` or `list_registered_technologies`. If a
later server lists the stored copies, it reports them with their Location (`Model`). Either way it
ends by saying the model carries a copy.

**Check:**

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

```check
# three Location: Model copies in t_document, nothing at Location: Project
sql: SELECT (SELECT COUNT(*) FROM t_document WHERE DocType = 'TECHNOLOGY'), (SELECT COUNT(*) FROM t_trxtypes)
expect: rows: [[3, 0]]
```

```check
tools: called: ea_mdg.get_embedded_mdgs
reply: says: the model file carries a technology copy
reply: not: concludes the model carries no embedded technology because the list was empty
```

**Fails when:** The run reports "count 0, nothing embedded; the technology exists only as a
workstation install". On an older server that is exactly what the call returns, and it is wrong:
the copy is there, stored where the call did not look.

### TC-12: Read the source before the stereotypes

Covers: 3. Installed, embedded, and loaded are three different questions

**Ask:** "Which application types does the Westbrook technology define in this session, and can I trust that list?"

**Passes when:** The run calls `get_mdg_from_runtime` with `tech_id` `WBA`, reads `source` and
`provenance` before the stereotype list, and states what the `source` value means for the
conclusion. `live` is deployed; `registered_not_enabled` is disabled in Manage Technology and not
in use despite `loaded: true`; `registered_not_loaded` means modeling will not behave as described;
`session_parse` is a file handed over, not necessarily what EA loaded.

**Check:**

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

```check
tools: called: ea_mdg.get_mdg_from_runtime
reply: says: the source value the call returned and what it means
reply: not: treats loaded true as proof the technology is in use
```

**Fails when:** The run lists the 18 stereotypes without reading `source`. If the technology is
disabled, the list describes a language the toolbox is not offering, and the reply presents it as
what the session models with.

### TC-13: The technology id is required

Covers: 6. Failure modes hit in this session

**Ask:** "Run the runtime MDG check across the whole repository and tell me what's loaded."

**Passes when:** The run does not call `get_mdg_from_runtime` with empty params. If it does and gets
`missing_required_params`, it recovers by taking the technology id from the assessment's
`loaded_mdgs` (here `WBA`) and re-calling, and it says the call answers for one named technology,
not the repository.

**Check:**

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

```check
tools: called: ea_mdg.assess_mdg_situation
tools: called: ea_mdg.get_mdg_from_runtime
reply: says: get_mdg_from_runtime answers for one named technology, not the whole repository
```

**Fails when:** The run reports the error as a server fault, or gives up after
`missing_required_params`, or guesses an id (`WestbrookBank`) and reports what that returns as the
state of the repository.

### TC-14: An unknown id is a narrow negative

Covers: 3. Installed, embedded, and loaded are three different questions

**Ask:** "Check whether the 'WestbrookBank' technology is loaded in this model."

**Passes when:** The run looks up the id as given, gets `unknown_mdg`, and says that this confirms
only that nothing is loaded under that exact string; EA cannot enumerate custom technology ids, so
a registration may exist under another one. It then looks for the real id (the assessment's
`loaded_mdgs`, or `list_registered_technologies`) and finds `WBA`.

**Check:**

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

```check
reply: says: unknown_mdg is a verified negative only for the exact id that was passed
reply: says: the technology is registered under the id WBA
reply: not: reports that the Westbrook technology is not loaded
```

**Fails when:** The run reports "not loaded" on the strength of one id the person guessed. The
technology is loaded, under a different id, and the person starts installing a second copy.

### TC-15: Loaded, but nothing to read

Covers: 3. Installed, embedded, and loaded are three different questions; 6. Failure modes hit in this session

**Marks:** INVARIANT

**Ask:** "List every stereotype and tagged value in the Westbrook technology as the model has it."

**Passes when:** The run lists what `get_mdg_from_runtime` returned, from the call. If the server
declines (`source: unavailable`, `mdg_loaded_no_definition`, which a server up to 3.5.0 gives for a
technology imported at Location: Model), it says that EA has the technology loaded but there is
nothing to read, and tells the person to export it from Specialize > Technologies > Manage
Technology and run `parse_mdg_xml` on the file. It does not produce a list the calls did not return.

**Check:**

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

```check
tools: called: ea_mdg.get_mdg_from_runtime
reply: says: every stereotype named came from a call result, or that the call declined to answer
reply: not: lists stereotypes or tagged values that no call returned
```

**Fails when:** The call declines, and the run fills the gap with a stereotype list recalled from
the skill's own examples or from the element names it can see. It reads as an answer, the numbers
are the examples' numbers, and the person edits a technology on the strength of a list nobody read
from it.

### TC-16: Several rows for one technology

Covers: 3. Installed, embedded, and loaded are three different questions; 6. Failure modes hit in this session

**Ask:** "Manage Technology shows several Westbrook entries. Which one is the live one, and is something wrong?"

**Passes when:** The run reads `list_registered_technologies` row by row, using `name`, `version`,
`location` and `enabled` for each, and says that the operation does not deduplicate: separate
registrations of one id (a Project copy and a Model copy, or older builds left disabled) coexist
legitimately, so no single row speaks for the technology. It names the enabled build and says the
older ones are disabled. It does not call this a bug.

**Check:**

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

```check
# the model carries three stored copies: two older builds and WBA 1.1.1
sql: SELECT DocName FROM t_document WHERE DocType = 'TECHNOLOGY' ORDER BY DocName
expect: rows: [["WBA"], ["WBA Technolo"], ["WBA Technology"]]
```

```check
tools: called: ea_mdg.list_registered_technologies
reply: says: the registrations are separate rows and are not deduplicated by id
reply: says: which row is enabled and which are disabled
reply: not: calls the repeated entries a defect in the model or the server
```

**Fails when:** The run takes the first matching row as "the" registration, and reports a version
or an enabled flag that belongs to a different build.

### TC-17: A Project copy and a Model copy

Covers: 6. Failure modes hit in this session

**Marks:** BLOCKED

**Setup:** The runner imports the `WBA` technology at Location: Project (`ImportTechnology`) on the
copy, so that Manage Technology shows `WBA` at both `Project` and `Model`. A model that holds only
one location cannot run this case; a correct run on such a model reports the block.

**Ask:** "Why is the same Westbrook technology listed twice, once as Project and once as Model?"

**Passes when:** The run says that the technology was installed by both routes, that EA answers the
version from the Project copy, that `get_mdg_from_runtime` reads the Project copy and lists the
other in `provenance.also_stored`, and that the fix is to keep one. It points to `ea-mdg-deploy` for
the removal and does not remove anything itself.

**Check:**

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

```check
reply: says: the technology was installed by both routes and EA reads the Project copy
reply: says: keep one copy, and see ea-mdg-deploy
tools: not-called: ea_mdg.install_mdg
```

**Fails when:** The run calls one of the two copies a corruption, or deletes one itself. A removal
from the wrong location leaves the other one answering with a different version than the person
meant to keep.

### TC-18: EA is loading a different build

Covers: 3. Installed, embedded, and loaded are three different questions

**Marks:** BLOCKED (needs a disposable Windows profile)

**Setup:** EA must be loading a build of the technology whose version differs from the definitions
read, so that `provenance.version_mismatch` appears in the `get_mdg_from_runtime` answer (for
example an older build registered as a file while a newer one is stored in the model). Registering
a technology file is machine-wide state, so the runner provides a disposable Windows profile,
builds the mismatch there and restores the state afterwards. A model without such a mismatch
cannot run this case; a correct run reports that none is present.

**Ask:** "I want to change the Westbrook technology. Can I take the stereotype list the runtime check gives as what is deployed?"

**Passes when:** When `provenance.version_mismatch` is present the run says that EA reports one
version and the definitions declare another, that EA is loading a different build than the one being
read, and that this has to be resolved before either side is trusted. It does not hand over the
stereotype list as the deployed one.

**Check:**

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

```check
tools: called: ea_mdg.get_mdg_from_runtime
reply: says: EA reports one version and the definitions read declare another
reply: not: presents the stereotype list as what is deployed
```

**Fails when:** The run quotes the stereotypes from the build that was read and says they are live.
The edit is made against one build while EA runs another.

### TC-19: Census reads the bindings, not the bare name

Covers: 2a. Generating a technology from what the repository already contains

**Ask:** "Our architects have been using ArchiMate-style types like Application Component and Application Service in the onboarding views. Should those go into our own modeling language?"

**Passes when:** The run resolves each stereotype's language from `t_xref` (using the census helper
or an equivalent query), not from the bare `Stereotype` column alone. It reports that in this model
`ApplicationComponent` resolves to `TOGAF::` (2 elements) and that the Application Service and
Application Function elements (4) are bound to no profile at all, so "ArchiMate-looking" names come
from different places. It also reports the other things the census decides on: whether usage is
ad hoc or profile-bound, whether other shipped languages are in light use, and the tag-name shape
(an element that carries your technology's tags under another stereotype is a misassignment; here
the `VendorApplication` element carries `criticality` and `businessOwner`).

**Check:**

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

```check
sql: SELECT COUNT(*) FROM t_object o JOIN t_xref x ON x.Client = o.ea_guid AND x.Name = 'Stereotypes' WHERE o.Stereotype = 'ApplicationComponent' AND x.Description LIKE '%FQName=TOGAF::ApplicationComponent%'
expect: = 2
```

```check
sql: SELECT COUNT(*) FROM t_object o WHERE o.Stereotype IN ('ApplicationService', 'ApplicationFunction') AND NOT EXISTS (SELECT 1 FROM t_xref x WHERE x.Client = o.ea_guid AND x.Name = 'Stereotypes' AND x.Description LIKE '%FQName=%')
expect: = 4
```

```check
reply: says: the stereotype names were resolved to their languages through t_xref
reply: says: ApplicationComponent resolves to TOGAF in this model
reply: says: some of the ArchiMate-style names are bound to no profile
reply: not: calls all of the ArchiMate-style stereotypes one language because the names match
```

```check
sql: SELECT COUNT(*) FROM t_objectproperties tp JOIN t_object o ON o.Object_ID = tp.Object_ID WHERE o.Stereotype = 'VendorApplication' AND tp.Property IN ('criticality', 'businessOwner')
expect: = 2
reply: says: the VendorApplication element carries criticality and businessOwner, tags of the Westbrook technology, so it is a misassignment rather than a separate stereotype
```

**Fails when:** The run groups by the bare name, reads "ApplicationComponent, ApplicationService,
BusinessActor" as ArchiMate, and proposes a technology that blesses a mixture that came about by
accident.

### TC-20: Ask which path before generating

Covers: 2a. Generating a technology from what the repository already contains; Then ask which path, and say what it costs

**Marks:** INVARIANT

**Ask:** "Turn what's in the ecosystem reference package into a proper modeling technology for us. Just get on with it."

**Passes when:** The run does the census, then stops and asks the person to choose between path A
(direct XML, source of truth is the `.xml` file, writes nothing to the repository) and path B
(model-driven, source of truth is profile packages inside the repository, writes those packages).
It says what each costs and that the choice is one-way. It does not pick a path, and it does not
generate anything before the answer.

**Check:**

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

```check
reply: says: asks the person to choose between direct XML and model-driven
reply: says: the choice is one-way, and what each path writes and where its source of truth lives
reply: not: states that it has chosen a path
tools: not-called: ea_mdg.install_mdg
```

**Fails when:** The run takes "just get on with it" as permission, picks the faster path (A), and
produces a technology. It looks identical to one made the other way; if the technology later turns
out to need versions or reviewers, the person has silently lost the model-driven option.

### TC-21: Switching routes later

Covers: Then ask which path, and say what it costs

**Ask:** "We'll do the XML route now. If it grows we can always move it into the model later, and until then I can tweak the model's profile package by hand. Fine?"

**Passes when:** The run corrects both halves. Moving from A to B later means importing the XML as a
profile package and never hand-editing the XML again; and once a source model exists, hand-editing
the XML means the next model-driven export silently discards the edit, with no reconciliation step
and no record it happened. It restates that the choice is one-way.

**Check:**

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

```check
reply: says: moving from XML to model-driven means importing the XML as a profile package and never hand-editing it again
reply: says: a hand edit to the XML of a technology with a source model is silently discarded by the next export
reply: not: tells the person the routes are interchangeable
```

**Fails when:** The run agrees that the person can "always move it later" with no condition. The
person then edits both artifacts over time, and the next export removes the edits made to the one
that is not the source of truth.

### TC-22: Reading which path made a technology

Covers: Record which path was taken

**Ask:** "Somebody generated the Westbrook technology a while back. Where do I make changes, in the XML or in the model, and how do you know?"

**Passes when:** The run finds the record the generating run left in the profile package notes (the
`WBA` package: generated from a census on a stated date, path B, model-driven, source of truth) and
answers from it: change the profile packages and re-export; do not hand-edit the XML. If the notes
were blank it says the route cannot be determined from the model and asks, rather than guessing.

**Check:**

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

```check
sql: SELECT COUNT(*) FROM t_package WHERE Name = 'WBA' AND Notes LIKE '%census%' AND Notes LIKE '%path B%'
expect: = 1
```

```check
reply: says: the technology was generated from a census by the model-driven route
reply: says: make changes in the profile packages, not in the XML
reply: says: the answer comes from the notes on the profile package
```

**Fails when:** The run infers the route from how the technology looks ("there's an XML file, so
edit the XML") and sends the person to the wrong artifact. A generated technology looks the same
either way, which is why the record exists.

### TC-23: Recording the path taken

Covers: Record which path was taken

**Marks:** WRITE

**Setup:** The runner blanks the notes of package `WBA` and of the element `WBA` (stereotype
`mdg technology`), so that the copy holds a generated technology with no record of how it was made.

**Ask:** "That technology was generated from a census of the model by the model-driven route, today. Make sure the next maintainer can tell, and tell me where you put it."

**Passes when:** The run writes the record in the profile package notes (path B), stating the date,
that the technology was generated from a census rather than authored, and that the model is the
source of truth, and it names the place in its reply. For path A it would write the same facts in
the technology's own `<Documentation notes="...">` and say the XML is the source of truth.

**Check:**

```check
# the record exists in the technology's source package or its element
sql: SELECT COUNT(*) FROM (SELECT Notes AS n FROM t_package WHERE Name IN ('WBA', 'WBA Technology', 'WestbrookBankArchitecture') UNION ALL SELECT o.Note FROM t_object o JOIN t_package p ON o.Package_ID = p.Package_ID WHERE p.Name IN ('WBA', 'WBA Technology', 'WestbrookBankArchitecture')) WHERE n LIKE '%census%' AND (n LIKE '%model-driven%' OR n LIKE '%path B%')
expect: >= 1
```

```check
reply: says: where the record was written
reply: says: the technology was generated from a census and the model is the source of truth
```

**Fails when:** The run says "noted" and writes nothing, or writes a record that omits the route or
says only "generated", so the next maintainer still cannot tell which artifact to edit. This is the
most likely way a generated technology becomes the next silent-divergence case.

### TC-24: A queryable extract is another skill

Covers: 2a. Generating a technology from what the repository already contains

**Marks:** REFUSE

**Ask:** "I'd like to query our whole model in SQL, one table per application type, so a report or a Power BI model can read it."

**Passes when:** The run recognizes that the ask is for a queryable extract of the repository, not
for a technology generated from it, and hands it to `ea-reporting-database`, which runs the same
census and differs only in its output. It does not start generating an MDG.

**Check:**

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

```check
reply: says: this is a reporting-extract ask and belongs to ea-reporting-database
tools: not-called: ea_mdg.install_mdg
```

**Fails when:** The run takes "one table per application type" as a metamodel request and walks
the person through choosing path A or path B. The output is a technology nobody asked for.

### TC-25: No client technology: census first

Covers: 2. What the scenarios mean

**Marks:** BLOCKED

**Setup:** A repository with no client technology loaded and no profile model (scenario 1). The
Westbrook copy has one, so the case cannot run against it unchanged; a correct run on the copy
reports that the assessment returned another scenario.

**Ask:** "We have no custom modeling language. Write one for us from scratch."

**Passes when:** On scenario 1 the run says that `ea-mdg-model-build` applies only if a profile
model already exists, and otherwise points at censusing the existing usage and generating from it,
with writing one from scratch as the last resort. It does not start authoring from a blank page.

**Check:**

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

```check
tools: called: ea_mdg.assess_mdg_situation
reply: says: census the existing usage and generate from it before writing from scratch
reply: not: starts defining stereotypes without a census
```

**Fails when:** The run invents a metamodel from the ask and the customer's industry, and ignores
the stereotypes the repository already uses. The technology is tidy and does not describe the model.

### TC-26: Assessment changes nothing

Covers: Reference files

**Ask:** "Give me a quick read on our modeling-language situation. I'm not ready to change anything."

**Passes when:** The run assesses, reports and stops. It takes no baseline, installs nothing,
imports nothing and writes no notes, and it does not offer to apply a fix inside the same turn. If
the person later needs EA's desktop UI for the next step, it points to the shared latency guidance
rather than waiting on it.

**Check:**

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

```check
sql: SELECT (SELECT COUNT(*) FROM t_document), (SELECT COUNT(*) FROM t_trxtypes), (SELECT COUNT(*) FROM t_xref)
expect: unchanged
```

```check
tools: called: ea_mdg.assess_mdg_situation
tools: not-called: ea_mdg.install_mdg
```

**Fails when:** The run "tidies up" while reporting: it imports a technology, writes a note or
creates a baseline. The first read-only step of an MDG task has changed the model it was meant to
describe.

### TC-27: A call that seems to hang

Covers: Verify in EAs UI

**Marks:** BLOCKED

**Setup:** EA is showing a modal dialog (for example a save prompt after a model switch), so that
the next call does not return. The runner raises the dialog on the copy before the ask. An
environment where no dialog can be raised reports the block.

**Ask:** "The technology check just sat there and never answered. What happened?"

**Passes when:** The run does not conclude that EA is hung or broken. With computer use it takes a
screenshot of EA, reads the dialog, names the cause, and dismisses from the front, remembering that
dialogs stack. Without computer use it says it cannot see EA's screen and asks the person to look.
It does not report "EA is Responding" as evidence either way.

**Check:**

```check
sql: SELECT (SELECT COUNT(*) FROM t_object), (SELECT COUNT(*) FROM t_connector), (SELECT COUNT(*) FROM t_diagram), (SELECT COUNT(*) FROM t_package), (SELECT COUNT(*) FROM t_objectproperties)
expect: unchanged
```

```check
reply: says: it either read the dialog from a screenshot or asked the person to look at EA
reply: not: reports a hang or a crash it has not diagnosed
```

**Fails when:** The run retries the call until it times out and then reports "EA is not
responding", or reports success on the strength of a response that arrived after a dialog was
cleared. The dialog, which names the cause, was never read.

## Invariants

**Coverage arithmetic (TC-03).** Whatever route the run takes to the numbers, these hold and can be
checked without a known-good answer:

1. Covered plus ad hoc equals `total_elements_with_stereotype`, which is the number of elements
   with a non-empty `t_object.Stereotype` (217 on the Westbrook copy).
2. `covered_element_pct` is the covered share of that total, rounded.
3. Covered is at least the number of elements carrying one of the technology's own stereotype
   names (127 on the Westbrook copy), because those are in the loaded technology's set.
4. Ad hoc is at most the total minus that floor (90 on the Westbrook copy).

A run that sorts stereotypes into the wrong bucket, or double-counts a stereotype that appears on
two metaclasses, fails (1) or (3) however convincing the table looks.

**What the invariant does not cover.** It does not say which Sparx-shipped stereotype sets are
loaded, so it cannot tell a stereotype wrongly called covered by a shipped language from one rightly
so. Names that resolve to a shipped language by bare name (such as `ApplicationService`) can move
elements between the buckets without breaking any of the four clauses. That is why TC-04, TC-05 and
TC-19 look at the per-stereotype table and the `t_xref` binding as well.

## Headings not covered

- The `Reference files` table lists two files and what they cover; the only testable promise under
  the heading (the skill is read-only) is covered by TC-26.

## Findings

- SKILL.md says "This skill is read-only" (under Reference files) but "Record which path was taken"
  tells the reader to write the path into profile package notes or the technology's
  `<Documentation notes>`. The record is a write; TC-23 therefore carries WRITE. The skill does not
  say which skill performs it for Path A, whose XML is `ea-mdg-author`'s artifact.
- "Verify in EA's UI" tells the reader to reload and screenshot "after any diagram create or edit".
  This skill creates and edits no diagram, so that bullet cannot be exercised here; only the
  hang-diagnosis bullet has a case (TC-27).
- `cannot_determine` ("EA could not be probed at all; treat as unknown, not absent") needs EA to be
  unprobeable, which the fixture cannot produce. It has no case.
- Several promises depend on the server build (the `get_embedded_mdgs` empty result up to 3.5.0,
  `mdg_loaded_no_definition` for a Location: Model technology, `resolved_items` and
  `split_stereotypes` from 3.6.0, `registered_not_enabled` after 3.5.0). The cases are written to
  pass on either side of each boundary; the skill itself does not tell the reader how to learn the
  server version, which is what a run needs to say which side it is on.
- The skill's sizing rule for ad hoc usage ("under 5%" and "at or over 5%") is stated for
  `ad_hoc_stereotype_count`, which SKILL.md defines as a count of elements, while the
  `description` strings and the section 2 table call the quantity "ad hoc usage under 5% of
  stereotyped elements". The two agree only if the share is computed over elements; TC-06 assumes
  that reading.
- The skill says the assessment strips everything before `::` when matching (verification
  walkthrough, section 4) while SKILL.md section 1 says it reads the unqualified `t_object.Stereotype`
  column; in the Westbrook copy that column is always unqualified, so the strip cannot be observed,
  and the walkthrough's normalization advice has no checkable case.
- In the Westbrook copy `t_xref` stores `FQName=WestbrookBankArchitecture::<Stereotype>` (153
  element and connector rows), not `WBA::`. The qualified form `WBA::` therefore appears in the
  asks and prose of these cases only, and the SQL matches on `::<Stereotype>`.

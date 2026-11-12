# The governance gate

The mechanics here were run against a live repository before they were written down. The figures
come from the Westbrook Bank reference model and are there to show the *shape* of an answer, not as
numbers to expect. The outcome counts in section 3 are one measured run of the current rules on a
fresh copy of that model (the extract was read with SQL, not through the server's extract).
Substitute your own technology, stereotypes and model.

---

## 1. What problem this solves

An element with no stereotype lands in no entity table unless the inclusion choice admits it (the
choice to include everything gives it a table keyed by its metaclass), so by default it is not in
the reporting layer. That is correct behavior: the business tables are the technology's
vocabulary, and an element carrying no vocabulary term has no table to go in.

The gate lists exactly the elements the saved inclusion choice leaves without a table. Under "only
what my MDG defines" that is every unstereotyped element and every element carrying a stereotype the
technology does not declare. Under "everything in the repository" it is none of them. Under "show me
the gaps" it is the ones the person did not include. Diagram furniture (`Package`, `Note`, `Text`,
`Boundary`) is never listed: it never gets a table, under any choice.

It becomes a problem when the element carries governance data anyway. On the reference model
three Components carry the complete tag set:

```
Client Reporting Platform     criticality=Business-Critical   regulatoryScope=GLBA
Portfolio Analytics Engine    lifecycle=Current               dataClassification=Confidential
Rebalancing Service           businessOwner / technicalOwner set
```

Somebody classified these deliberately. No report will ever show them, because the element
carries the data but not the stereotype that routes it to a table. **Lead with these.** An
untagged, unstereotyped element is merely undrawn; a tagged one is a governance gap.

---

## 2. Mapping the extract's rows

`governance_gap` speaks plain column names and the rows come from EA's tables, so the caller maps
between them. This is deliberate: it keeps `governance_gap` pure and free of any knowledge of
`t_object`. Read the rows with `ea_analyze(operation="execute_sql", ...)` (the rows come back under
the `rows` key, every value a string):

| Name | Read with |
|---|---|
| `objects` | `SELECT * FROM t_object`, filtered to the in-scope `Package_ID`s (the scope computation of [`the-inclusion-choice.md`](the-inclusion-choice.md) §2) |
| `props` | `SELECT Object_ID, Property, Value FROM t_objectproperties`, filtered to the in-scope `objects` |
| `packages` | `SELECT Package_ID, Parent_ID, ea_guid, Name FROM t_package` |
| `mdg` | the dict `ea_mdg(operation="get_mdg_from_runtime", params={"tech_id": "<id>"})` returns |
| `profile` | the saved profile; its `inclusion` section is the inclusion choice (`resolve_answer(...).inclusion`) |

`declared_shapes` lives in `ea_census`, not in `governance_gap`:

```python
import sys
sys.path.insert(0, r"<skills-dir>/_shared/tools")
from ea_census import declared_shapes
from governance_gap import find_ungoverned, assess, format_report

path_by_id = {int(p["Package_ID"]): p.get("Name", "") for p in packages}
guid_by_id = {int(o["Object_ID"]): o["ea_guid"] for o in objects}

elements = [{
    "ea_guid":      o["ea_guid"],
    "name":         o.get("Name") or "",
    "metaclass":    o.get("Object_Type") or "",
    "stereotype":   o.get("Stereotype") or "",
    "package_id":   int(o.get("Package_ID") or 0),
    "package_path": path_by_id.get(int(o.get("Package_ID") or 0), ""),
} for o in objects]

tags = [{
    "ea_guid": guid_by_id.get(int(p["Object_ID"]), ""),
    "tag":     p.get("Property") or "",
    "value":   p.get("Value") or "",
} for p in props]

declared = declared_shapes(mdg)
findings = assess(find_ungoverned(elements, tags, inclusion=profile["inclusion"], declared=declared),
                  declared, elements)
print(format_report(findings))
```

Prefer the package's path from the root over its bare name for `package_path`: a customer reading
"Investment Services" cannot tell which of two similarly named packages is meant. The entity
tables' `package_path` column is built the same way.

`find_ungoverned` needs the inclusion choice, so the gate runs after the §2b question is answered.
It skips diagram furniture by default. EA stores every package twice, once in the package tree and
once as an object so it can sit on a diagram, and nobody stereotypes the object twin.

---

## 3. The four outcomes, and why they must stay apart

### `no_candidate`: there is nothing to apply

The loaded technology extends no stereotype for that element's metaclass, so no stereotype can
legally be applied to it. On the reference model, run over the Westbrook Bank package, this is
**46 elements**: 10 Requirements and 36 UML behavior elements (use cases, actions, states,
actors), because the technology extends `Component`, `Class`, `Activity` and `Node` only.

The useful answer here is not a suggestion. It is:

> Your technology defines no stereotype for a Requirement. Ten requirements therefore cannot be
> included. Either extend the technology to cover them, or accept the exclusion.

Extending the technology is `ea-mdg-model-build`'s job, and generating one from what a
repository already contains is exactly what that capability does.

**Never invent a suggestion here.** Applying a stereotype whose base metaclass does not match is
the documented way to get EA to accept the write and silently drop it; `update_element` warns
about precisely this.

### `ranked`: one candidate is backed by evidence

A suggestion is only made when something in the repository distinguishes one candidate. The
signal that does this in practice is **package locality**: what stereotype do the element's
stereotyped neighbors carry? Tag fit takes no part in the ranking; it only rules a candidate out
(see `unrankable`).

The three governed Components on the reference model come out this way: they sit in a package whose
other three stereotyped elements are all `WBAVendorSystem`, and that stereotype declares every tag
the three carry (it declares nine, they carry six). That is a suggestion with a stated basis, and
the `reason` field carries it:

```
3 stereotyped element(s) in the same package carry 'WBAVendorSystem', and no other
candidate for metaclass Component is backed by that evidence.
```

Offer a ranked suggestion **with the reason**. Do not present it as certain: it is evidence, not
proof, and the customer knows their model.

### `single_candidate`: one candidate, not confirmed

Exactly one stereotype extends the element's metaclass (and its tags allow it), and nothing in the
element's package confirms it. On the reference model that is the **15 infrastructure Nodes**: the
technology declares `WBATechnologyNode` on `Node`, the Nodes carry no tags and no neighbor carries
it. The gate names the stereotype, says "one candidate, not confirmed", and asks. It never ranks on
the metaclass alone, and it does not call this unrankable, because nothing needs separating: there
is one candidate and no evidence for or against it.

### `unrankable`: nothing to choose by, or nothing that fits

Say so and ask. Do not pick one.

- **Several candidates, nothing to separate them.** This is a property of most technologies. On the
  reference technology **ten of the fifteen element stereotypes declare an identical six-tag set**,
  so for an element carrying those six tags, tag names cannot tell the Component candidates apart.
  Choosing the alphabetically first would be a guess wearing a number. On the Westbrook Bank package
  one Activity is this case, with three candidates and no sibling evidence.
- **Every candidate ruled out.** The element carries a tag that none of the candidates for its
  metaclass declares, so none can be offered. The report says so and lists no candidates: extend the
  technology, or accept the exclusion.

Tag fit is a veto and nothing else: a stereotype is ruled out only when the element carries a tag
it does not declare. A stereotype that declares more tags than the element carries is not ranked
down for it; the extra tags are tags the element has yet to fill.

Run over the Westbrook Bank package under option 1 (WBA 1.1.1), 65 elements carry no stereotype:
3 governed and ranked, 15 with one candidate not confirmed, 1 needing a choice and 46 with no
candidate. That is one measured run on a fresh copy, with the extract read by SQL and not through
the server. The earlier measurement, under a ranking that used tag fit as a second signal, was none
ranked, 19 needing a choice and 46 with no candidate.

Option 1 also lists 21 elements that carry an ad hoc stereotype the technology does not declare,
so 86 elements in all. Of those 21, 17 were unrankable (three `model document` classes and one
activity carry tags no declared stereotype has), 3 had one candidate and 1 had none. A report that
quotes the 65 should say whether it counts these 21.

---

## 4. Applying a stereotype

**Take a baseline first.** With the unbound-connector fix in [`the-inclusion-choice.md`](the-inclusion-choice.md)
§3, this is one of the two steps in the whole skill that write to the customer's model, and a bulk
stereotype application across a repository is exactly the change `ea-change-management` exists to
make reversible.

```python
ea_model(operation="update_element",
         params={"element_id": <the element's id>,
                 "properties": {"StereotypeEx": "WBAVendorSystem"}})
```

### Pass the bare name

Measured 2026-10-02 on EA build 1716, with the technology loaded. Both the bare name
(`WBAVendorSystem`) and the qualified form (`WBA::WBAVendorSystem`)
produce an identical, **profile-bound** application: EA resolves the name against the loaded
technology and writes the full `FQName` into `t_xref` itself.

```
@STEREO;Name=WBAVendorSystem;GUID={...};FQName=WBA::WBAVendorSystem;@ENDSTEREO;
```

This matters because the census counts an application as the technology's only when `FQName` is
present. A bare-name write that produced an ad-hoc application would leave the element out of
its entity table after all, and the build would look like it had failed to apply anything.

Verified end to end: applying the bare name to two scratch Components moved the
`WBAVendorSystem` census count from 35 to 37, and both elements were placed under
`WBA::WBAVendorSystem`.

### When the technology is not loaded

The resolution above depends on the technology being loaded in the session. If it is not, EA has
nothing to resolve the bare name against and will record an ad-hoc application (the stereotype
name with no `FQName`), which the census will report as ungoverned drift rather than placing it
in a table.

So before applying anything, confirm the technology is loaded. `ea-mdg-assess` distinguishes
installed, embedded and loaded, which are three different states and are routinely confused.
`IsTechnologyLoaded` is the test; the presence of a row in `t_trxtypes` is not.

### Verify, do not assume

`update_element` returns `ok: true` and a `stereotype_warning` field. `ok` does not mean the
stereotype landed. After applying, re-run the census and confirm the element is placed:

```python
census.placement.get(guid)   # -> ['WBA::WBAVendorSystem']
```

---

## 5. If the customer declines

Declining is a valid answer, not an error. Say plainly what the consequence is, then build the
reporting layer without them. The report never lists unstereotyped diagram furniture (`Package`,
`Note`, `Text`, `Boundary`): it is never model content and never gets a table, as
`the-inclusion-choice.md` says, so counting it as "will not appear" would alarm the reader for
nothing.

> Six elements will not appear in the reporting layer, three of which carry governance
> tagged values including one marked GLBA.

Record the counts with the build report (`SKILL.md` §9) so the layer can answer later what was left
out and whether a human was asked. A layer that cannot say what it excluded invites the reader to
assume it excluded nothing.

**With no one to ask** (an unattended run), the gate applies nothing: a stereotype is a model write,
and a write needs the person's yes. It reports the list and carries on as if declined, so a person can
decide later.

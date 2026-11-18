# Coverage data -- full worked numbers

All numbers on this page were measured on 2026-11-16 on a copy of the Westbrook Bank demo model
(EA 17.1 build 1716, server 3.6.5, technology `WBA` loaded), with the operations named; the model was
not changed. It is our demo model, not one your organization has, and your repository's counts will
differ. The numbers show the shape of an answer and how to work one out; never quote one as a fact
about a model. Run the same calls and use what they return.

47 elements are bound to `WBABusinessApplication`. 46 carry it as their primary stereotype; one,
Core Deposit System of Record, carries it second, after `WBASystemOfRecord`. The roll-up and
tag-usage operations count that element once, so they report 47. A count on the primary stereotype
reports 46: 14 of the 46 have the exact `regulatoryScope` value `GLBA` and 29 have a value containing
GLBA (30 of the 47), and 8 of the 46 have a blank `regulatoryScope` or the text `None`. Name the
element and the basis when you quote either.

Denominators come from:

```
ea_analyze(operation="summarize_stereotype_usage", params={})
```

which returned, for the whole repository (the largest rows; the call also lists every stereotype
with fewer than four elements):

| Stereotype | EA object type | Element count |
|---|---|---|
| `WBABusinessApplication` | Component | 47 |
| `WBAVendorSystem` | Component | 35 |
| `stereotype` | Class | 24 |
| `metaclass` | Class | 13 |
| `WBADataAsset` | Object | 12 |
| `EATool` | Component | 9 |
| `WBABusinessService` | Component | 8 |
| `WBADataEntity` | Class | 5 |
| `WBASystemOfRecord` | Component | 4 |

Total elements carrying any stereotype: 217, across 50 distinct stereotypes. The `WBA` rows in the
table (`WBABusinessApplication`, `WBAVendorSystem`, `WBADataAsset`, `WBABusinessService`,
`WBADataEntity` and `WBASystemOfRecord`) belong to the WBA technology. `stereotype` and `metaclass`
are the profile definition's own elements, and `EATool` is outside the technology.
Check the stereotype name against this list before trusting a denominator -- "how many elements total" is a
different, less useful, question than "how many `WBABusinessApplication` elements."

---

## Per-stereotype tag coverage

Each row is one `ea_analyze(operation="summarize_tagged_value_usage", params={"stereotype": "<name>"})`
call, cross-checked against `aggregate_portfolio` group counts.

### `WBABusinessApplication` (47 elements)

| Tag | Populated | Blank | Notes |
|---|---|---|---|
| `criticality` | 47 | 0 | Business-Critical 21, Mission-Critical 12, Standard 8, Important 6 |
| `lifecycle` | 47 | 0 | fully populated |
| `dataClassification` | 47 | 0 | Confidential 33, Internal 11, Restricted 3 |
| `technicalOwner` | 46 | 1 | see team list below |
| `businessOwner` | 44 | 3 | see team list below |
| `regulatoryScope` | 44 | 3 | of the 44, 5 are the literal value `None`; see multi-value note below |

`businessOwner` groups (`aggregate_portfolio`, `count_only: true`): Consumer Banking 7,
Information Technology 6, Payments & Operations 5, Sales & Marketing 4, Digital Customer
Experience 4, Business Banking 3, AML Compliance 2, Retail Banking Operations 2, Credit Risk
Management 2, Corporate Finance 2, Wealth Management 2, Customer Service Operations 1, Fraud Risk
Management 1, Treasury & Capital Markets 1, Corporate Operations 1, Retail Banking 1, blank 3.
(Sum: 44 + 3 = 47.)

`technicalOwner` groups: Payments Technology Team 10, Infrastructure & Cloud Team 6, Digital
Engineering Team 6, Risk Technology Team 6, Lending Technology Team 4, Integration & API Team 3,
Branch Technology Team 2, Wealth Technology Team 2, Data Engineering Team 1, Core Banking Platform
Team 1, Core Banking Technology 1, Customer Data Engineering 1, CRM Operations 1, Mobile Engineering
Team 1, Contact Center Technology 1, blank 1. (Sum: 46 + 1 = 47.)

`regulatoryScope` groups: GLBA 14, "GLBA, FFIEC" 11, None 5, SOX 4, blank 3, FFIEC 3, "PCI, GLBA" 3,
"SOX, FFIEC" 2, "GLBA, SOX" 1, "GLBA, SOX, FFIEC" 1. (Sum: 47.)

**The multi-value undercount, worked:** if a stakeholder asks "how many business
applications are in GLBA scope," the naive answer -- the exact `"GLBA"` group -- is 14.
The real answer counts every element whose value includes GLBA: 14 (`GLBA`) + 11
(`GLBA, FFIEC`) + 3 (`PCI, GLBA`) + 1 (`GLBA, SOX`) + 1 (`GLBA, SOX, FFIEC`) = **30**. More than half
the true count is sitting in combined-value groups a whole-value roll-up never puts under `"GLBA"`. The
response flags it: `multi_valued_count` counts the elements holding a comma-joined value,
18 from the groups above (11 + 3 + 2 + 1 + 1). Rolling up again with
`split_values: true` counts each element under every part of its value, so the `"GLBA"`
group is the 30 directly (FFIEC 17, SOX 8, PCI 3, None 5, blank 3), and the groups sum to more than
the 47 elements. (Counted on the 46 primary-stereotype elements only, the same figure is 29.)

### `WBAVendorSystem` (35 elements)

| Tag | Populated | Blank | Notes |
|---|---|---|---|
| `businessOwner` | 35 | 0 | fully populated |
| `criticality` | 35 | 0 | Business-Critical 20, Mission-Critical 14, Standard 1 -- no `Important` value occurs here |
| `dataClassification` | 35 | 0 | fully populated |
| `lifecycle` | 35 | 0 | Strategic 33, Current 2 |
| `regulatoryScope` | 35 | 0 | fully populated |
| `technicalOwner` | 35 | 0 (structurally) | see encoding note below |

**The encoding-drift duplicate, worked:** `technicalOwner` groups for `WBAVendorSystem`
include both `Infrastructure & Cloud Team` (count 6) and `Infrastructure &amp; Cloud
Team` (count 2) -- an HTML-entity-encoded ampersand that survived an import somewhere and
never got normalized. Structurally the tag is 35/35 populated (no blanks), so Step 0's
blank check passes clean. The real problem only shows up if you scan the distinct values
themselves: one team's true count is 6 + 2 = 8, but a roll-up reports two teams. Any tag
whose values come from free text (as opposed to an enumeration with fixed permitted
values) needs this second check -- not "is it populated" but "are near-duplicate values
hiding a single real group."

### `WBADataAsset` (12 elements)

| Tag | Populated | Blank | Notes |
|---|---|---|---|
| `dataClassification` | 12 | 0 | Confidential 6, Internal 4, Restricted 2 |
| `regulatoryScope` | 12 | 0 | fully populated |
| `criticality` | 0 | -- | tag does not appear in the summary at all for this stereotype |
| `lifecycle` | 0 | -- | tag does not appear |
| `businessOwner` | 0 | -- | tag does not appear |
| `technicalOwner` | 0 | -- | tag does not appear |

`aggregate_portfolio(params={"stereotype": "WBADataAsset", "group_by_tag": "criticality"})`
returns `{"total_elements": 0, "groups": []}`. Read literally and out of context, that
looks like "there are no data assets" -- there are 12, they simply don't carry a
`criticality` tag. This is the sharpest version of the "silent zero" failure mode: the
same JSON shape would come back for a misspelled stereotype name, for a real stereotype
that legitimately has zero elements, and for this case (real elements, untracked tag).
Nothing in the response distinguishes the three.

### `WBABusinessService` (8 elements)

| Tag | Populated (non-blank) | Notes |
|---|---|---|
| `lifecycle` | 8 | Strategic on all 8 |
| `businessOwner` | 0 | tag present on all 8, value `""` on all 8 (a later copy stores no value at all; either is blank) |
| `criticality` | 0 | tag present on all 8, value `""` on all 8 |
| `dataClassification` | 0 | tag present on all 8, value `""` on all 8 |
| `regulatoryScope` | 0 | tag present on all 8, value `""` on all 8 |
| `technicalOwner` | 0 | tag present on all 8, value `""` on all 8 |

`aggregate_portfolio(params={"stereotype": "WBABusinessService", "group_by_tag": "businessOwner"})`
returns one group: `{"value": "", "count": 8}`. `total_elements` reads as 8 -- a
"the tag is set on every element" check would pass -- but every one of those 8 is blank.
This is the counterpart failure to `WBADataAsset` above: there, the tag never existed on
the type at all; here, the tag exists everywhere and carries no information anywhere.
Both produce a roll-up that is technically well-formed and substantively empty.

---

## `resolve_display_term` results

From server 3.6.5 the lookup reads the technology EA has loaded, so with Westbrook's technology
standing in for one a customer built, a stereotype or tag it declares comes back found. These
results were measured on 2026-11-16 on the demo model with `WBA` loaded. The alias and description
values are whatever your technology declares, so run these on your own model before quoting them:

```
ea_mdg(operation="resolve_display_term", params={"kind": "stereotype", "technical_name": "WBABusinessApplication"})
-> {"technical_name": "WBABusinessApplication", "alias": "Business Application", "description": "", "mdg_id": "WBA", "kind": "stereotype", "found": true}

ea_mdg(operation="resolve_display_term", params={"kind": "tagged_value", "technical_name": "criticality"})
-> {"technical_name": "criticality", "alias": "criticality", "description": "", "mdg_id": "WBA", "kind": "tagged_value", "found": true}

ea_mdg(operation="resolve_display_term", params={"kind": "stereotype", "technical_name": "ApplicationComponent"})
-> {"technical_name": "ApplicationComponent", "alias": "Application", "description": "", "mdg_id": "ArchiMate3", "kind": "stereotype", "found": true}

ea_mdg(operation="resolve_display_term", params={"kind": "tag", "technical_name": "criticality"})
-> {"ok": false, "error": "invalid_kind", "kind": "tag", "valid_kinds": ["stereotype", "tagged_value", "connector_stereotype", "diagram_type"]}
```

Other terms from the same run: `WBAVendorSystem` -> "Vendor System", `technicalOwner` -> "technical Owner",
`businessOwner` -> "business Owner" (kind `tagged_value`), and the connector stereotype `Uses` -> "Uses"
(kind `connector_stereotype`), all `found: true` with `mdg_id` `WBA`. The tag aliases keep a lowercase
first word and the tag's description is empty, so the label is usable but not polished.

Why: the lookup reads the technology EA has loaded first (one read per technology per call),
then the server's own alias tables, which cover languages that ship with EA, and only then falls
back to the technical name with `found: false`. `parse_mdg_xml` still adds a parsed technology's
stereotypes to those tables for the rest of the session. Before server 3.6.5 the lookup did not
read the loaded technology: a customer's tags never resolved, and the two Westbrook terms above
came back `found: false`.
`get_element_business_view` and `aggregate_portfolio` label their output through the same
lookup.

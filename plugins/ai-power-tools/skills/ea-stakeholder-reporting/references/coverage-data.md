# Coverage data -- full worked numbers

All numbers on this page were measured against the live Westbrook Bank demo model on
2026-09-23 using the operations named. They are not illustrative placeholders -- if you
re-run the same calls against a changed model, expect different numbers and prefer the
live ones over this page.

Denominators come from:

```
ea_analyze(operation="summarize_stereotype_usage", params={})
```

which returned, for the whole repository:

| Stereotype | EA object type | Element count |
|---|---|---|
| `WBABusinessApplication` | Component | 52 |
| `WBAVendorSystem` | Component | 35 |
| `WBADataAsset` | Object | 12 |
| `EATool` | Component | 9 |
| `WBABusinessService` | Component | 8 |
| `ExternalReference` | Artifact | 1 |
| `VendorApplication` | Component | 1 |

Total elements carrying any stereotype: 118, across 7 distinct stereotypes. Only the
first, second, third, and fifth rows belong to the WBA technology; `EATool`,
`ExternalReference`, and `VendorApplication` are outside it. Check the stereotype name
against this list before trusting a denominator -- "how many elements total" is a
different, less useful, question than "how many `WBABusinessApplication` elements."

---

## Per-stereotype tag coverage

Each row is one `ea_analyze(operation="summarize_tagged_value_usage", params={"stereotype": "<name>"})`
call, cross-checked against `aggregate_portfolio` group counts.

### `WBABusinessApplication` (52 elements)

| Tag | Populated | Blank | Notes |
|---|---|---|---|
| `criticality` | 52 | 0 | Business-Critical 22, Mission-Critical 14, Standard 8, Important 8 |
| `lifecycle` | 52 | 0 | fully populated |
| `dataClassification` | 45 | 7 | Confidential 32, Internal 11, Restricted 2, blank 7 |
| `technicalOwner` | 44 | 8 | see team list below |
| `businessOwner` | 42 | 10 | see team list below |
| `regulatoryScope` | 42 | 10 | of the 42, 5 are the literal value `None`; see multi-value note below |

`businessOwner` groups (`aggregate_portfolio`, `count_only: true`): Consumer Banking 7,
Information Technology 6, Sales & Marketing 4, Digital Customer Experience 4, Payments &
Operations 4, Business Banking 3, AML Compliance 2, Retail Banking Operations 2, Credit
Risk Management 2, Corporate Finance 2, Wealth Management 2, Customer Service Operations 1,
Fraud Risk Management 1, Treasury & Capital Markets 1, Corporate Operations 1, blank 10.
(Sum: 42 + 10 = 52.)

`technicalOwner` groups: Payments Technology Team 9, blank 8, Infrastructure & Cloud Team
6, Digital Engineering Team 6, Risk Technology Team 6, Lending Technology Team 4,
Integration & API Team 3, Branch Technology Team 2, Wealth Technology Team 2, Data
Engineering Team 1, Core Banking Platform Team 1, Customer Data Engineering 1, CRM
Operations 1, Mobile Engineering Team 1, Contact Center Technology 1. (Sum: 44 + 8 = 52.)

`regulatoryScope` groups: GLBA 14, "GLBA, FFIEC" 11, blank 10, None 5, SOX 4, FFIEC 3,
"SOX, FFIEC" 2, "PCI, GLBA" 2, "GLBA, SOX" 1. (Sum: 52.)

**The multi-value undercount, worked:** if a stakeholder asks "how many business
applications are in GLBA scope," the naive answer -- the exact `"GLBA"` group -- is 14.
The real answer counts every element whose value includes GLBA: 14 (`GLBA`) + 11
(`GLBA, FFIEC`) + 2 (`PCI, GLBA`) + 1 (`GLBA, SOX`) = **28**. Half the true count is
sitting in combined-value groups a whole-value roll-up never puts under `"GLBA"`. The
response flags it: `multi_valued_count` counts the elements holding a comma-joined value,
16 from the groups above (11 + 2 + 2 + 1). Rolling up again with
`split_values: true` counts each element under every part of its value, so the `"GLBA"`
group is the 28 directly, and the groups sum to more than the 52 elements.

### `WBAVendorSystem` (35 elements)

| Tag | Populated | Blank | Notes |
|---|---|---|---|
| `businessOwner` | 35 | 0 | fully populated |
| `criticality` | 35 | 0 | Business-Critical, Mission-Critical, Standard only -- no `Important` value occurs here |
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
| `businessOwner` | 0 | tag present on all 8, value `""` on all 8 |
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

## `resolve_display_term` transcript

Run on 2026-10-08 against the 3.6.0 server source, with Westbrook's technology standing in
for one a customer built, and no technology XML parsed in the session:

```
ea_mdg(operation="resolve_display_term", params={"kind": "tagged_value", "technical_name": "criticality"})
-> {"technical_name": "criticality", "alias": "criticality", "description": "", "mdg_id": "", "kind": "tagged_value", "found": false}

ea_mdg(operation="resolve_display_term", params={"kind": "stereotype", "technical_name": "WBABusinessApplication"})
-> {"technical_name": "WBABusinessApplication", "alias": "WBABusinessApplication", "description": "", "mdg_id": "", "kind": "stereotype", "found": false}

ea_mdg(operation="resolve_display_term", params={"kind": "stereotype", "technical_name": "ApplicationComponent"})
-> {"technical_name": "ApplicationComponent", "alias": "Application", "description": "", "mdg_id": "ArchiMate3", "kind": "stereotype", "found": true}

ea_mdg(operation="resolve_display_term", params={"kind": "tag", "technical_name": "criticality"})
-> {"technical_name": "criticality", "alias": "criticality", "description": "", "mdg_id": "", "kind": "tag", "found": false}
   ("tag" is not a kind; it is accepted and comes back as a miss)
```

Why: the lookup reads the server's own alias tables, which cover languages that ship with
EA. It does not read the technology EA has loaded. `parse_mdg_xml` adds a parsed
technology's stereotypes and their aliases to those tables for the rest of the session, after
which its stereotypes resolve; nothing adds its tags, so they never resolve, whichever kind
is passed.
`get_element_business_view` and `aggregate_portfolio` label their output through the same
lookup.

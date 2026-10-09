# Consistency audits -- full data from a live run

Detail supporting [`../SKILL.md`](../SKILL.md) Section 3. Read that section first for what each
operation answers and how to read the result; this file carries the complete tables from a live
run against the Westbrook Bank demo model, for reference and as a template for reading your own
results. The tables were captured on 2026-09-23 against WBA 1.0; the technology has since moved to
1.1.1 (15 element stereotypes), which declares `pciScopeJustification`, `product` and `vendor` on
some of them, so "not declared" readings below describe 1.0.

---

## 1. `summarize_stereotype_usage` -- full repository result

```
ea_analyze(operation="summarize_stereotype_usage", params={})
```

| Stereotype | EA object type | Element count |
|---|---|---|
| `WBABusinessApplication` | Component | 52 |
| `WBAVendorSystem` | Component | 35 |
| `WBADataAsset` | Object | 12 |
| `EATool` | Component | 9 |
| `WBABusinessService` | Component | 8 |
| `ExternalReference` | Artifact | 1 |
| `VendorApplication` | Component | 1 |

`total_elements_with_stereotype: 118`, `distinct_stereotypes: 7`. Note this is elements that
carry *some* stereotype -- the model has 229 elements total, so 111 carry none at all (mostly the
capability-hierarchy containers from `SKILL.md` Section 1).

Read the bottom of the table first. `ExternalReference` and `VendorApplication` at count 1 are
each worth a specific question:

- `ExternalReference` is a server-managed stereotype (see
  `ea_model(operation="create_external_reference_element", ...)`) -- a single-use count here is
  expected, not decay, because it marks a placeholder for an object living in another system.
- `VendorApplication` at count 1, sitting right next to `WBAVendorSystem` at 35, is the real
  warning shape: a near-duplicate name that reads as if it might be a typo, an abandoned earlier
  naming convention, or a deliberate distinction nobody documented. This is not something to
  "fix" without asking -- it is something to flag, exactly per the canon's own rule for
  handling a discovered inconsistency (see `westbrook-example.md` Section 11): surface it, do not
  silently rewrite it.

---

## 2. `summarize_tagged_value_usage` -- unscoped (whole repository)

```
ea_analyze(operation="summarize_tagged_value_usage", params={})
```

The six WBA base tags dominate, at counts of 100-112 (they are applied to every stereotyped
element across all 7 stereotypes in the table above, not just the 14 the WBA MDG declares -- this
repository also stamps them onto `EATool` and vendor-catalog elements). Below them, a second
group of tags that are **not** in the WBA canon's ten at all:

| Tag | Count | Distinct values | What it suggests |
|---|---|---|---|
| `vendor` | 40 | 31 | Vendor-catalog metadata, consistent naming, looks deliberate |
| `product` | 36 | 36 | Same -- one distinct value per element, a catalog field |
| `PricingTier` | 9 | 2 | Scoped to `EATool` entries only |
| `Source` | 9 | 1 | Always `Sparx Systems` -- provenance marker on the same `EATool` set |
| `URL` | 7 | 6 | Reference links, also `EATool`-scoped |
| `pciScopeJustification` | 4 | 4 | See Section 3 below -- applied inconsistently within a WBA stereotype |
| `externalId` / `externalSyncedAt` / `externalSystem` / `externalUrl` | 1 each | 1 each | The four tags `create_external_reference_element` applies automatically -- expected to be rare, one set per external reference |

The pattern that separates "fine" from "flag it": `vendor`/`product`/`Source` are consistent
within their own scope (every `EATool` element that has one, has all of them, with sensible
distinct-value counts). `pciScopeJustification` is inconsistent *within* a single WBA stereotype,
which is the case that needs a closer look -- see next section.

---

## 3. `summarize_tagged_value_usage` -- scoped to `WBABusinessApplication`

```
ea_analyze(operation="summarize_tagged_value_usage", params={"stereotype": "WBABusinessApplication"})
```

| Tag | Count | / 52 total | Distinct values |
|---|---|---|---|
| `businessOwner` | 52 | 100% | 16 |
| `criticality` | 52 | 100% | 4 |
| `dataClassification` | 52 | 100% | 4 |
| `lifecycle` | 52 | 100% | 5 |
| `regulatoryScope` | 52 | 100% | 9 |
| `technicalOwner` | 52 | 100% | 15 |
| `pciScopeJustification` | **2** | **4%** | 2 |

All six WBA base tags are present on every one of the 52 `WBABusinessApplication` elements --
the healthy result, matching the canon's rule that the base set applies to all 15 element stereotypes.
`pciScopeJustification` is not one of the WBA canon's ten tagged values at all, and is set on
only 2 of the 52 elements (`"Card issuance platform -- PCI DSS scoped"`,
`"Network connectivity -- PCI DSS scoped"`). That is an ad hoc field two elements picked up,
most likely during a PCI review, that never became a modeling standard. Worth surfacing to
whoever owns the model: either promote it to a real tag on every in-scope element, or note in the
model's own documentation that it is deliberately sparse (e.g. "only set where PCI scope needs
justifying beyond the `regulatoryScope` value").

---

## 4. `summarize_observed_metaclasses` -- three results compared

```
ea_analyze(operation="summarize_observed_metaclasses", params={"stereotype": "WBABusinessApplication"})
```

```json
{"stereotype": "WBABusinessApplication", "metaclass_distribution": [{"object_type": "Component", "count": 52}], "heterogeneous": false, "total_count": 52}
```

Healthy: one `object_type`, matching the WBA MDG's declared metaclass for this stereotype
(Component, per the canon's element-stereotype table).

```
ea_analyze(operation="summarize_observed_metaclasses", params={"stereotype": "WBAAIModel"})
```

```json
{"stereotype": "WBAAIModel", "metaclass_distribution": [], "heterogeneous": false, "total_count": 0}
```

Zero use, not an error. The WBA MDG declares `WBAAIModel` (a Class, part of the AI tag set along
with `WBAAIGateway` and `WBAAIService`) but nothing in the current Westbrook demo model actually
uses any of the three AI stereotypes -- confirmed the same way for all three. If a task assumes
the demo model already has AI-governed elements to work with, verify with this call first rather
than assuming the MDG's declared vocabulary is populated.

**What a `heterogeneous: true` result would look like** (not observed on this repository -- every
stereotype here happens to be clean): `metaclass_distribution` with two or more entries, e.g.
`[{"object_type": "Component", "count": 50}, {"object_type": "Class", "count": 2}]`. That means
two elements carry the `WBABusinessApplication` stereotype string but were created as a different
EA base type than the other 50 -- almost always because someone typed the stereotype into an
element created via the wrong toolbox page, or pasted it in via `update_element` rather than
`create_element_in_language`. Those two elements will not behave like the rest of their type in
searches, reports, or any MDG-aware tooling, even though they look identical in the Browser.

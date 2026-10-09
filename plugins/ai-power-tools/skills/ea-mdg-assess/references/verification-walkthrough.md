# Reproducing the assessment by hand

`assess_mdg_situation`'s `ad_hoc_stereotype_count` and `covered_element_pct` aren't opaque. They
are element counts over the same bare `t_object.Stereotype` column that `summarize_stereotype_usage`
groups on, so you can approximate both from that call's `items`. This walkthrough does it on an
illustrative Westbrook Bank usage table. The figures are an illustration, not a reproducible
result: substitute your own repository's table, and expect the split to depend on which
technologies are loaded and enabled there.

## 1. Pull the raw usage table

```
ea_analyze(operation="summarize_stereotype_usage", params={})
```

An illustrative response (the `resolved_items`, `split_stereotypes` and
`multi_stereotype_element_count` fields the call also returns are omitted):

```
{
  "items": [
    {"stereotype": "WBABusinessApplication", "object_type": "Component", "element_count": 52},
    {"stereotype": "WBAVendorSystem",         "object_type": "Component", "element_count": 35},
    {"stereotype": "WBADataAsset",            "object_type": "Object",    "element_count": 12},
    {"stereotype": "EATool",                  "object_type": "Component", "element_count": 9},
    {"stereotype": "WBABusinessService",      "object_type": "Component", "element_count": 8},
    {"stereotype": "ExternalReference",       "object_type": "Artifact",  "element_count": 1},
    {"stereotype": "VendorApplication",       "object_type": "Component", "element_count": 1}
  ],
  "total_elements_with_stereotype": 118,
  "distinct_stereotypes": 7
}
```

## 2. Split covered vs. ad hoc

A stereotype counts as **covered** if it appears in a loaded language's known stereotype set —
which, per `assess_mdg_situation`'s own loaded-languages check, means a loaded and enabled client
technology (here WBA) or any loaded Sparx-shipped language. Everything else is **ad hoc**.

Against the stereotype list `get_mdg_from_runtime` reports for `WBA` (see
[three-states.md](three-states.md)), read out of the loaded technology itself:

| Stereotype | Count | In the WBA technology? | Bucket |
|---|---|---|---|
| `WBABusinessApplication` | 52 | yes | covered |
| `WBAVendorSystem` | 35 | yes | covered |
| `WBADataAsset` | 12 | yes | covered |
| `EATool` | 9 | no | ad hoc |
| `WBABusinessService` | 8 | yes | covered |
| `ExternalReference` | 1 | no | ad hoc |
| `VendorApplication` | 1 | no | ad hoc |

```
covered = 52 + 35 + 12 + 8   = 107
ad hoc  = 9 + 1 + 1          = 11
total   = 118

covered_pct = round(107 / 118 * 100) = round(90.68) = 91
```

On this table the recomputation gives `ad_hoc_stereotype_count: 11` and `covered_element_pct: 91`.
The first is a count of elements (9 + 1 + 1), not of stereotypes: three distinct stereotypes
account for it. When your recomputation disagrees with the assessment, work out which stereotypes
drove each number before trusting either, because the per-stereotype table shows what the single
summary number hides.

Expect the real figures to include more than the stereotypes you meant to leave out. The assessment
covers the whole repository, so elements from a technology's own source package (stereotyped
`stereotype`, `metaclass` and so on) and elements created by other tools count as ad hoc too.

## 3. Read past the number

The recomputation surfaces something the scenario number alone doesn't: two of the three ad hoc
stereotypes look like near-duplicates of technology stereotypes that already exist —
`VendorApplication` (1 element) sits next to `WBAVendorSystem` (35 elements), and `EATool` (9
elements, `Component`) has no obvious WBA counterpart at all. That's two different problems with
two different fixes (fold a near-duplicate into the existing stereotype vs. decide whether a new
concept belongs in the technology), and `assess_mdg_situation`'s single `ad_hoc_stereotype_count:
11` can't distinguish them. Always pull the per-stereotype table before deciding what "extend the
MDG" should actually do.

## 4. When the numbers don't reconcile

If your recomputed `covered`/`ad hoc` split doesn't match the assessment's reported numbers,
suspect one of:

- **A language loaded between the two calls.** `assess_mdg_situation` and
  `summarize_stereotype_usage` each read current state independently; if someone loads or unloads
  a technology between them, the two calls answer for different moments.
- **A stereotype string with a namespace prefix on one side and not the other.** The assessment
  strips everything before `::` when matching (`WBA::WBABusinessApplication` and
  `WBABusinessApplication` count the same); if you're matching by eye against the technology's
  stereotype list, do the same normalization or a legitimately-covered stereotype will look ad hoc.
- **A Sparx-shipped language's stereotype set covering something you didn't expect.** The
  "covered" bucket includes every currently-loaded Sparx-shipped language, not just the client
  MDG — a plain ArchiMate or BPMN stereotype in use counts as covered even with no client
  technology involved at all.

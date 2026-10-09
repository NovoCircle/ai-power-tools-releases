# Working with an MDG Technology (WBA as the Illustration) — Full Detail

Detail supporting [`../SKILL.md`](../SKILL.md) §10. Read that section first for the one-line
rule (confirm your technology is loaded before tagging); this file carries the verification SQL
and the tag-applicability rule, with Westbrook Bank's `WBA` technology as the example. Use your
own technology id, stereotypes and tags.

---

## Confirm MDG is active before tagging

Before setting tagged values, confirm your technology is loaded and enabled (`WBA` below is
the Westbrook Bank illustration; pass your own technology id):
```
ea_mdg(operation="get_mdg_from_runtime", params={"tech_id": "WBA"})
```

`source: "live"` means EA has it loaded and enabled. Anything else — `registered_not_enabled`,
`unavailable` — means deploy or enable it with the `ea-mdg-deploy` skill before proceeding.

Do not test for it with SQL against `t_document` `DocType='MDGXml'`: none of EA 17.1's import routes writes that
document type, so the query is empty whether or not the technology is in the model. An in-model
technology is a `t_document` row with `DocType='TECHNOLOGY'` (Location: Model) or rows in
`t_trxtypes` (Location: Project). WBA in the Westbrook Bank model is at Location: Model since 1.1.1 was deployed
(it was at Location: Project under 1.0).

## Tagged value namespace confirmation

The first successful `ea_model(operation="set_tagged_value", ...)` response will include the fully-qualified tag name,
e.g. `WestbrookBankArchitecture::WBAVendorSystem::criticality`. This confirms the MDG is
active and the tag schema is being honored.

## MDG stereotype → allowed tags

The rule is simpler than a per-stereotype matrix suggests: the **base set of 6** tags
(`criticality`, `lifecycle`, `businessOwner`, `technicalOwner`, `dataClassification`,
`regulatoryScope`) applies to **all 15** WBA element stereotypes. The **AI set of 4**
(`modelGovernanceClass`, `humanInLoopRequired`, `auditLoggingEnabled`, `dataResidency`)
applies **only** to the three AI stereotypes: `WBAAIGateway`, `WBAAIService`, `WBAAIModel`. Three further
tags (`pciScopeJustification`, `product`, `vendor`) are declared on only some stereotypes.
See `_shared/references/westbrook-example.md` section 3 for the canonical list — this file
does not repeat it so there is exactly one source of truth for tag names and enum values.


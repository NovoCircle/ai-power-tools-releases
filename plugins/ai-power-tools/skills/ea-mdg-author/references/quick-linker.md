# Quick Linker rules

Back to [SKILL.md](../SKILL.md).

Quick Linker (QL) is the hover menu EA shows on a diagram element when you pause over it. QL rules
are embedded in your MDG XML and control which connector types appear in that menu.

### Preferred approach — intermediate metamodel (write_mdg_xml)

When using `write_mdg_xml` to emit your MDG XML, declare QL rules directly on each source
stereotype in the intermediate metamodel dict:

> As in Section 1 above, `WBA::WBARunsOn` here is a **proposed extension** — the shipped WBA
> technology (1.1.1) defines the connector stereotypes `Uses`, `Flows` and `realizes`, not
> `WBARunsOn`. Its own Quick Linker rules use them, for example `WBAVendorSystem` offers
> `WestbrookBankArchitecture::Uses` to `WestbrookBankArchitecture::WBATechnologyNode`. A QL rule
> targeting a real, un-stereotyped relationship (e.g. `Dependency` between two WBA elements)
> needs no `quicklinker_rules` entry at all; EA's default UML QL entries already offer plain
> `Dependency`/`Realization`/`Association`. The pattern below is for the day you add your own
> connector stereotype.

```python
{
  "name": "WBABusinessApplication",
  "base_metaclass": "Component",
  "hide_uml_links": True,           # suppress EA's default UML entries
  "meaning_forwards": "Runs On",    # label on the QL menu item
  "quicklinker_rules": [
    # Each entry: which connector to create → which target stereotype is allowed
    {"stereotype": "WBA::WBARunsOn", "constraint": "WBA::WBAVendorSystem"},
  ],
  # ... other fields
}
```

`write_mdg_xml` emits the correct `<stereotypedrelationships>` and `<Apply>` properties
automatically. The dict above produces:

```xml
<Stereotype name="WBABusinessApplication" ...>
  <AppliesTo>
    <Apply type="Component">
      <Property name="_HideUmlLinks" value="True"/>
      <Property name="_MeaningForwards" value="Runs On"/>
    </Apply>
  </AppliesTo>
  ...
  <stereotypedrelationships>
    <!-- WBA::WBARunsOn is a PROPOSED EXTENSION - not part of the shipped WBA technology. -->
    <stereotypedrelationship stereotype="WBA::WBARunsOn" constraint="WBA::WBAVendorSystem"/>
  </stereotypedrelationships>
</Stereotype>
```

### Manual XML approach

If writing MDG XML directly, add these two elements to each source stereotype:

```xml
<Stereotype name="WBABusinessApplication" ...>
  <AppliesTo>
    <Apply type="Component">
      <Property name="_HideUmlLinks" value="True"/>
      <Property name="_MeaningForwards" value="Runs On"/>
    </Apply>
  </AppliesTo>
  <!-- ... TaggedValues ... -->
  <stereotypedrelationships>
    <!-- WBA::WBARunsOn is a PROPOSED EXTENSION - not part of the shipped WBA technology. -->
    <stereotypedrelationship stereotype="WBA::WBARunsOn" constraint="WBA::WBAVendorSystem"/>
  </stereotypedrelationships>
</Stereotype>
```

### Rules

- `stereotype` — connector stereotype EA creates when user picks this menu item. Must be defined
  as a connector stereotype elsewhere in the same MDG XML.
- `constraint` — the target element stereotype the menu item is valid for. Format: `<YourTechID>::Name`.
- **`_HideUmlLinks: True`** — only set this when you have at least one QL rule. An empty hide
  produces an entirely empty QL menu and looks like a broken feature.
- **Legacy: Profile Diagram workflow.** Creating QL rules via a Profile Diagram in EA then
  generating via the MTS Wizard is the old approach. It still works but is not recommended when
  AI Power Tools is deployed — use the intermediate metamodel or hand-author the XML instead.

### Verifying QL in EA

1. Deploy MDG and restart EA.
2. Open a diagram, drop a source stereotype element.
3. Hover for 1–2 seconds — QL arrows appear; clicking shows your connector menu.
4. If the menu is empty: check `_HideUmlLinks` isn't set without QL rules, and that
   `constraint` uses the right namespace prefix (`<YourTechID>::StereotypeName`).

> **Computer use note:** the QL hover overlay disappears on focus change. Take a screenshot
> immediately after the menu appears — do not click elsewhere first.

### Setting QL constraints on an existing model, via connector tagged values

Everything above authors QL rules into the MDG XML. There is a second route: setting them
directly on connectors already in a repository, which is how a profile expressed as a *model*
carries its QL constraints before it is exported to XML.

The mechanism is a connector tagged value:

- the connector is stereotyped `stereotyped relationship`
- it carries a tag named `stereotype` whose value is `<TechID>::<RelationshipName>`

So the same constraint expressed in XML as:

```xml
<stereotypedrelationship stereotype="WBA::WBARunsOn" constraint="WBA::WBAVendorSystem"/>
```

is set on a model connector with:

```
ea_model(operation="set_connector_tagged_value",
         params={"connector_id": 1234,
                 "name": "stereotype",
                 "value": "WBA::WBARunsOn"})
```

Read them back with `get_connector_tags` or `list_connector_tagged_values`, and remove one with
`delete_connector_tagged_value`.

This matters when you are building an MDG from a source model rather than hand-authoring XML —
see `ea-mdg-model-build`. If you are writing the XML directly, use the forms above instead;
this route exists for the model-first workflow.

> `WBA::WBARunsOn` is used here only to match the proposed-extension example above. The shipped
> WBA technology defines `Uses`, `Flows` and `realizes`, not `WBARunsOn`.

# Installed, embedded, and loaded — three different questions

The `get_embedded_mdgs` and `get_mdg_from_runtime` payloads were captured live against the
Westbrook Bank demo repository (`<model-dir>\WestbrookBank.qea`), with EA already running and the
model open, while it held WBA 1.0 at Location: Project; the `list_registered_technologies` payload
is an illustration with placeholders. Where a call's answer looks incomplete or odd, that is what it
returned. **Your repository will answer differently**: the technology id, versions, locations and
counts below are Westbrook's, shown to teach the shape, and nothing here is a state you will see.
For orientation only: in the Westbrook example with WBA 1.1.1 at Location: Model, a call answers 18 stereotypes
(15 element and 3 connector), 3 diagram types and 3 toolbox pages.

---

## `list_registered_technologies` — what EA's Manage Technology dialog would show

```
ea_mdg(operation="list_registered_technologies", params={})
```

An illustration of the rows for one technology (the id `WBA` and the `<version>` values stand in for
yours):

```
{ "name": "WBA", "version": "<version>",
  "location": "Model",
  "enabled": true },
{ "name": "WBA", "version": "<older version>",
  "location": "Project",
  "enabled": false }
```

One row per registration, not per technology: the same id can be listed more than once, for
example a Project copy and a Model copy, or older builds left disabled, each with its own
`version`, `location` and `enabled`. The id is the technology id (`WBA`); the display name
(`WestbrookBankArchitecture`) is not a registration id and does not appear as a second row. What it
means in practice: asking "is the technology registered?" doesn't have a single yes/no answer. Ask
about a specific `name` string, and read `enabled` for that row specifically. The response's own
`completeness_note` explains why the list can be incomplete: it is built from a fixed probe list of
shipped technologies plus session and model-stored entries, EA's COM interface cannot enumerate
arbitrary registered technologies, and a technology loaded under an id the probe does not know is
absent from the list although it is loaded. A technology disabled purely by an unticked box in
Manage Technology, with no separate embedded copy, cannot be told apart from "not registered at
all" through this call; use `get_mdg_from_runtime` with the exact id.

The other rows are Sparx-shipped languages (ArchiMate, BPMN, TOGAF, UAF, SysML and so on),
normally `enabled: true`. A Sparx-shipped language can be disabled too, not just custom ones.

---

## `get_embedded_mdgs` — what the model file itself carries

```
ea_mdg(operation="get_embedded_mdgs", params={})
```

```
{
  "embedded_mdgs": [],
  "count": 0,
  "ea17_note": "Empty result. In EA 17+, ImportTechnology() does not write to t_document. Verify via COM: repo.IsTechnologyLoaded('your_tech_id'), or check Specialize > Technologies > Manage Technology in the EA UI."
}
```

Zero results, on a repository that has WBA visibly loaded. That payload is from a server up to
3.5.0, and the note's explanation is wrong: EA 17.1 does store in-model technologies, in one of
two places the call did not read. Measured on EA 17.1 build 1716:

| Manage Technology Location | Stored in | Written by |
|---|---|---|
| `Model` | one `t_document` row, `DocType='TECHNOLOGY'`: a ZIP holding the whole MDG file | Import MDG Technology ▸ Import to Model; `ImportPackageAsMDGTechnology` |
| `Project` | `t_trxtypes` rows: UML profiles and diagram profile, no toolbox pages | `ImportTechnology` (`install_mdg(scope="embedded")`) |

The call read only `DocType='MDGXml'`, which neither route writes. From the release after 3.5.0
it lists each stored copy with its `location`, the version that copy declares, and the table it
came from. WBA in the Westbrook Bank model was at Location: Project when this was captured.

---

## `get_mdg_from_runtime` — the technology EA loaded

```
ea_mdg(operation="get_mdg_from_runtime", params={"tech_id": "WBA"})
```

Requires `tech_id` — calling it with `params={}` fails with `missing_required_params`. It answers
for one named technology, not the whole repository.

```
{
  "tech_id": "WBA",
  "technology_name": "WBA (Westbrook Bank Architecture)",
  "version": "1.0",
  "stereotypes": [
    {"name": "WBABusinessApplication", "alias": "Business Application", "metatype": "WBABusinessApplication",
     "base_metaclass": "Component",
     "tagged_values": [
       {"name": "criticality", "type": "enumeration", "default": "",
        "description": "Business criticality classification",
        "values": ["Mission-Critical", "Business-Critical", "Important", "Standard"]}, ...]},
    {"name": "WBADataAsset",           "alias": "Data Asset",           "base_metaclass": "Class",   ...},
    {"name": "WBAAIModel",             "alias": "AI Model",             "base_metaclass": "Class",   ...},
    ... 14 in total ...
  ],
  "diagram_types": [
    {"name": "WBAApplicationView", "alias": "WBA Application Architecture", "base": "Logical",
     "diagramID": "WBA-AppView", "toolbox": "WBA::WBA ArchiMate"},
    {"name": "WBAProcessView",   "base": "Activity", ...},
    {"name": "WBADataModelView", "base": "Logical",  ...}
  ],
  "source": "live",
  "loaded": true,
  "provenance": {
    "origin": "model",
    "detail": "t_trxtypes -- technology imported into the open model",
    "loaded": true,
    "version_reported_by_ea": "1.0"
  }
}
```

Fourteen stereotypes, each with its metaclass and its tagged values, and the three diagram types —
read out of the technology EA has loaded. `provenance.origin` says which of the two places that
was:

- `model` — the technology was imported into this model. From the release after 3.5.0,
  `provenance.location` says where: `Project` (`t_trxtypes`, as above) or `Model` (`t_document`
  TECHNOLOGY). Up to 3.5.0 only `Project` was read, so a Location: Model technology answered
  `mdg_loaded_no_definition`.
- `registered_file` — the technology is an `.xml` in a folder EA loads at startup (the per-user
  MDGTechnologies folder, a configured search path, or EA's own install). `provenance.detail`
  carries the path, which is what to open when a deployment looks stale.

When the model holds the same id at both Locations, the answer comes from the Project copy (EA's
own precedence, measured on EA 17.1 build 1716) and `provenance.also_stored` lists the other, with
the version it declares. `provenance.enabled` is `IsTechnologyEnabled`: a technology disabled in
Manage Technology still reports `loaded: true`, and `source` is then `registered_not_enabled`.

`version_reported_by_ea` is `GetTechnologyVersion` for that id. When it disagrees with the version
in the definitions read, the response carries `provenance.version_mismatch` — EA is loading a
different build of the technology than the one being read, and neither side should be trusted
until that is resolved.

### When it declines

The call refuses rather than guessing, and `source` is `unavailable` with an `error` saying which
kind of nothing it found:

- `{"error": "cannot_determine", "loaded": null, ...}` — EA could not be probed at all; treat as
  unknown, not absent.
- `{"error": "mdg_loaded_no_definition", "loaded": true, ...}` — EA confirms the technology is
  loaded, but its XML is in neither a technology folder nor the model, so there is nothing to
  read. If the technology is one EA ships with the product (for example BMM or an ArchiMate version), EA has no export for it in Manage Technology. Read its stereotypes from the static language tables of this server, which is what the server's message names. If it is your own or a third party's technology, export it from Specialize > Technologies > Manage Technology and run `parse_mdg_xml` on the file. For a technology EA ships, the result also carries `builtin: true`.
- `{"error": "unknown_mdg", "loaded": false, ...}` — a verified negative for that exact id string,
  not a guess. EA's COM surface can't enumerate custom technology ids, so this only confirms the
  one string you passed; the real registration may exist under a different id.

A Location: Model copy that cannot be decoded answers `{"error": "model_technology_unreadable",
"unreadable": [...]}`, naming the copy and the reason, rather than `mdg_loaded_no_definition`.

Further `source` values sit between those: `registered_not_enabled`, where EA has it loaded but it
is disabled in Manage Technology; `registered_not_loaded`, where the definitions were
found but EA does not have the technology loaded right now; and `session_parse`, where the only
definitions available are those `parse_mdg_xml` was handed this session — which is not necessarily
what EA loaded. Both are still worth reading; neither is evidence of what the session is actually
modeling with.

# Installed, embedded, and loaded — three different questions

Every one of these payloads was captured live against the Westbrook Bank demo repository
(`<model-dir>\WestbrookBank.qea`), with EA already running and the model open.
Nothing here was constructed from the spec — where a call's answer looks incomplete or odd,
that's what it actually returned.

The WBA payloads were captured while the model held WBA 1.0 at Location: Project. The model now
holds WBA 1.1.1 at Location: Model (`t_trxtypes` empty): `get_mdg_from_runtime` answers 18
stereotypes (15 element and 3 connector), 3 diagram types and 3 toolbox pages, and Manage
Technology lists one enabled `WBA` with the two older builds disabled.

---

## `list_registered_technologies` — what EA's Manage Technology dialog would show

```
ea_mdg(operation="list_registered_technologies", params={})
```

Relevant rows out of 26 returned:

```
{ "name": "WBA", "version": "1.0",
  "location": "Workstation file (exact path not exposed by EA's COM API)",
  "enabled": true },
{ "name": "WestbrookBankArchitecture", "version": "",
  "location": "Workstation file (exact path not exposed by EA's COM API)",
  "enabled": false }
```

Two rows, same underlying organization, different identifiers, different `enabled` state. This is
not a bug — the response's own `completeness_note` says as much: the same technology can appear
under more than one registration at once. What it means in practice: asking "is Westbrook Bank's
technology registered?" doesn't have a single yes/no answer. Ask about a specific `name` string,
and read `enabled` for that row specifically. A technology disabled purely by an unticked box in
Manage Technology, with no separate embedded copy, cannot be told apart from "not registered at
all" through this call — see the `completeness_note` field for the exact limitation.

Every other row in the 26 was a Sparx-shipped language (ArchiMate2/3, BPMN family, TOGAF, UAF,
SysML variants, and so on), all `enabled: true`, all `location: "Sparx-installed"`. One
exception: `UML` was present with `enabled: false` and an empty `version` — a Sparx-shipped
language can be disabled too, not just custom ones.

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
  read. Export it from Specialize > Technologies > Manage Technology and run `parse_mdg_xml` on
  the file.
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

#!/usr/bin/env python3
"""Author a complete `.pbip` project from a semantic model.

PURE. No file or network I/O, no clock, no randomness. It returns every file in
the project keyed by its relative path; writing them is the caller's job.

    SemanticModel + partition source  ->  project_files()  ->  {path: text}

All three Power BI paths use this: path C passes a `ParquetSource` pointing at
the Parquet files, and paths A and B a SQL source.
The project is otherwise identical, which `test_pbip.py` asserts.

THE CALLER MUST WRITE WITH `newline=""`
---------------------------------------
Every string here is CRLF-terminated, UTF-8 without a BOM, because that is what
Power BI writes and a generated project that deviates is rejected. On Windows
`open(path, "w")` would turn our "\\r\\n" into "\\r\\r\\n".

THE REPORT HALF IS WHERE THIS GETS HARD
---------------------------------------
The semantic model is straightforward. The report is validated just as strictly
and its failures are far less readable. Two measured ones, both of which cost
real time:

  * `reportVersionAtImport` as a STRING aborts the open with a precise message
    and Power BI loads NOTHING. It is an object: {visual, report, page}.
  * A `report.json` carrying only `$schema` opens the semantic model but fails
    the report with an opaque activity id - and then EVERY SAVE PATH CRASHES
    with a null reference, so the project cannot be saved at all even though its
    model loaded perfectly.

So this replicates the structure of a project Power BI itself wrote, read off
disk, rather than the minimum that seems reasonable.

A BASE THEME IS REQUIRED, AND IT CAN BE OURS
--------------------------------------------
MEASURED 2026-10-02 on Power BI 2.158.1177.0, three opens of the same 40-table
model:

  * No `themeCollection` and no `resourcePackages`: the semantic model loads and
    the REPORT fails - "Something went wrong / Failed to load the report", whose
    details are an activity id and nothing else.
  * The theme block plus Power BI's own theme file: opens clean.
  * The theme block plus a MINIMAL THEME OF OUR OWN - a name, a handful of
    colors - opens clean too.

So the theme is required, and shipping someone else's file is not. `base_theme`
defaults to `default_base_theme()`, whose JSON this module emits itself. Passing
`base_theme=None` omits it, which is known to produce a project whose report
does not load; it exists so the failure can be reproduced, not for ordinary use.

Which PART is strictly required - the `themeCollection`, the `resourcePackages`
entry, or the file - has not been isolated. All three were added together.

THE OVERVIEW PAGE AND ITS VISUALS
---------------------------------
The one page carries a table visual over `Table Directory` (`table_name`, `kind`,
`description`) and one card per entity count measure (`'{table} count'`). No visual
uses an entity table's columns, so the blank member that Power BI adds to a table
on the one side of a relationship never shows. The JSON follows the `visualContainer`
2.14.0 files Power BI Desktop 2.159.883.0 itself saved (a `tableEx` and a `slicer`
in a captured PBIR project): `$schema`, `name`, `position`, `visual` with a
`query.queryState.Values` projection list, and, on the table, the per-column
`filterConfig` Desktop writes. A card is the same container with `visualType` "card"
and a `Measure` field. Cards carry no `filterConfig` (the captured project has no
card to copy it from, so none is guessed). Every `name` is derived from the content,
as `page_name` is.

Versions pinned, from the captured project: visual container 2.14.0 (the captured
visuals; `VISUAL_SCHEMA`), page 2.1.0, report 3.3.0, pages metadata 1.1.0, version
metadata 1.0.0. Only the visual container changed from what was pinned before.
`REPORT_VERSION_AT_IMPORT` stays {visual 2.13.0, report 3.4.0, page 2.3.1}: Desktop
2.159.883.0 saved 2.14.0 visuals and left that object as it was, so it is an import
record, not a pin that tracks the container schema, and Desktop has never written
2.14.0 there.

The page is 1280 wide and 720 high, and grows taller only when the cards need it
(more than about 136 entity tables), so every card sits on the page.
"""
from __future__ import annotations

import json
import uuid
from dataclasses import dataclass

from semantic_model import SemanticModel
from tmdl import NEWLINE, NS, render_definition


#: Schema and version strings read from a Power BI 2.158 project on disk. They
#: are version-pinned facts about the host, not preferences, and a guess at any
#: one of them is rejected on open.
PLATFORM_SCHEMA = ("https://developer.microsoft.com/json-schemas/fabric/"
                   "gitIntegration/platformProperties/2.0.0/schema.json")
PBISM_VERSION = "4.2"
PBIR_VERSION = "4.0"
PBIP_VERSION = "1.0"
PAGES_SCHEMA = ("https://developer.microsoft.com/json-schemas/fabric/item/report/"
                "definition/pagesMetadata/1.1.0/schema.json")
VERSION_SCHEMA = ("https://developer.microsoft.com/json-schemas/fabric/item/report/"
                  "definition/versionMetadata/1.0.0/schema.json")
PAGE_SCHEMA = ("https://developer.microsoft.com/json-schemas/fabric/item/report/"
               "definition/page/2.1.0/schema.json")
REPORT_SCHEMA = ("https://developer.microsoft.com/json-schemas/fabric/item/report/"
                 "definition/report/3.3.0/schema.json")

#: Written into report.json when a base theme is supplied. Version-pinned, read
#: off a real project alongside the rest.
REPORT_VERSION_AT_IMPORT = {"visual": "2.13.0", "report": "3.4.0", "page": "2.3.1"}

#: The visual container schema of the visuals this module writes.
VISUAL_SCHEMA = ("https://developer.microsoft.com/json-schemas/fabric/item/report/"
                 "definition/visualContainer/2.14.0/schema.json")


@dataclass
class BaseTheme:
    """The base theme the report references, and optionally its JSON.

    A project carries the theme under
    `StaticResources/SharedResources/BaseThemes/<name>.json`. When `content` is
    set this module emits that file itself; when it is empty the caller is
    undertaking to put the file there, and `required_static_resources()` says
    where.
    """
    name: str
    content: str = ""

    @property
    def static_resource_path(self) -> str:
        return f"StaticResources/SharedResources/BaseThemes/{self.name}.json"


#: Deliberately minimal and deliberately ours. A theme is required for the
#: report to load, and this is what removes any need to redistribute Power BI's.
DEFAULT_THEME_NAME = "AIPowerToolsBase"

DEFAULT_THEME_JSON = {
    "name": DEFAULT_THEME_NAME,
    "dataColors": ["#4A6FA5", "#6B9AC4", "#97C1D9", "#C3DBE8", "#2E4A6B",
                   "#8A8D93"],
    "background": "#FFFFFF",
    "foreground": "#252423",
    "tableAccent": "#4A6FA5",
}


def default_base_theme() -> BaseTheme:
    """The theme emitted unless the caller asks for another."""
    return BaseTheme(DEFAULT_THEME_NAME, _json(DEFAULT_THEME_JSON))


#: Tells `project_files` apart from a caller who explicitly passed None, which
#: means "emit no theme" and is known to produce a report that does not load.
_DEFAULT_THEME = object()


def _json(obj) -> str:
    """JSON with CRLF, to match what Power BI writes.

    Built with `json.dumps` rather than string templates: a project file that is
    not valid JSON fails on open with a message that does not say which file.
    """
    return json.dumps(obj, indent=2).replace("\n", NEWLINE) + NEWLINE


def logical_id(path: str) -> str:
    """A `.platform` logicalId, derived so two runs produce the same project."""
    return str(uuid.uuid5(NS, f"item:{path}"))


def page_name(project: str) -> str:
    """A deterministic page identifier.

    Power BI's own are opaque 20-character ids. Deriving ours keeps a
    regenerated project byte-identical, which is what lets a customer re-apply
    without their report being rebuilt.
    """
    return uuid.uuid5(NS, f"page:{project}").hex[:20]


def visual_name(project: str, key: str) -> str:
    """A deterministic 20-character visual (or filter) id, derived from content."""
    return uuid.uuid5(NS, f"visual:{project}:{key}").hex[:20]


#: The Table Directory columns the table visual shows, in order.
DIRECTORY_TABLE = "Table Directory"
DIRECTORY_COLUMNS = ("table_name", "kind", "description")

#: Page geometry (the page is 1280 x 720). The table sits on the left and the
#: cards fill a grid on the right.
_PAGE_W, _PAGE_H, _MARGIN, _GAP = 1280, 720, 20, 10
_TABLE_W = 640
_GRID_X = _MARGIN + _TABLE_W + _MARGIN
_GRID_W = _PAGE_W - _MARGIN - _GRID_X
_CARD_H_MAX, _CARD_H_READABLE, _CARD_H_MIN = 100, 60, 30


def count_measures(model: SemanticModel) -> list[tuple[str, str]]:
    """`(table, measure)` for every `'{table} count'` measure on a visible table,
    in table order. These are the entity counts the page shows as cards."""
    return [(t.name, m.name) for t in model.tables if not t.is_hidden
            for m in t.measures if m.name == f"{t.name} count"]


def _field(kind: str, entity: str, prop: str) -> dict:
    return {kind: {"Expression": {"SourceRef": {"Entity": entity}}, "Property": prop}}


def _projection(kind: str, entity: str, prop: str, *, active: bool = False) -> dict:
    proj = {"field": _field(kind, entity, prop),
            "queryRef": f"{entity}.{prop}", "nativeQueryRef": prop}
    if active:
        proj["active"] = True
    return proj


def _visual(project: str, key: str, visual_type: str, position: dict,
            projections: list[dict], filters: list[dict] | None = None) -> dict:
    visual = {
        "$schema": VISUAL_SCHEMA,
        "name": visual_name(project, key),
        "position": position,
        "visual": {
            "visualType": visual_type,
            "query": {"queryState": {"Values": {"projections": projections}}},
            "drillFilterOtherVisuals": True,
        },
    }
    if filters:
        visual["filterConfig"] = {"filters": filters}
    return visual


def _card_grid(n: int) -> tuple[int, int, int, int]:
    """(columns, card width, card height, rows) for `n` cards in the right-hand area.
    Columns grow from 3 until the rows fit at a readable height (60 or more);
    past 8 columns the height shrinks to a floor of 30 and the page grows instead
    (see `page_height`)."""
    usable = _PAGE_H - 2 * _MARGIN
    cols = 3
    while cols < 8 and -(-n // cols) * (_CARD_H_READABLE + _GAP) - _GAP > usable:
        cols += 1
    rows = max(1, -(-n // cols))
    width = (_GRID_W - _GAP * (cols - 1)) // cols
    height = (usable - _GAP * (rows - 1)) // rows
    return cols, width, max(_CARD_H_MIN, min(_CARD_H_MAX, height)), rows


def page_height(model: SemanticModel) -> int:
    """The Overview page height: 720, or taller when the cards need more room."""
    _, _, height, rows = _card_grid(len(count_measures(model)))
    return max(_PAGE_H, 2 * _MARGIN + rows * height + (rows - 1) * _GAP)


def overview_visuals(model: SemanticModel, project: str) -> dict[str, dict]:
    """The Overview page's visuals, keyed by visual name: the Table Directory table
    and one card per entity count measure. Empty when the model has neither."""
    out: dict[str, dict] = {}
    z = 0
    directory = model.table(DIRECTORY_TABLE)
    if directory is not None and set(DIRECTORY_COLUMNS) <= {c.name for c in directory.columns}:
        pos = {"x": _MARGIN, "y": _MARGIN, "z": z, "height": page_height(model) - 2 * _MARGIN,
               "width": _TABLE_W, "tabOrder": z}
        filters = [{"name": visual_name(project, f"filter:{DIRECTORY_TABLE}.{c}"),
                    "field": _field("Column", DIRECTORY_TABLE, c), "type": "Categorical"}
                   for c in DIRECTORY_COLUMNS]
        v = _visual(project, f"table:{DIRECTORY_TABLE}", "tableEx", pos,
                    [_projection("Column", DIRECTORY_TABLE, c) for c in DIRECTORY_COLUMNS],
                    filters)
        out[v["name"]] = v
        z += 1
    cards = count_measures(model)
    cols, width, height, _ = _card_grid(len(cards))
    for i, (table, measure) in enumerate(cards):
        pos = {"x": _GRID_X + (i % cols) * (width + _GAP),
               "y": _MARGIN + (i // cols) * (height + _GAP),
               "z": z, "height": height, "width": width, "tabOrder": z}
        v = _visual(project, f"card:{table}.{measure}", "card", pos,
                    [_projection("Measure", table, measure)])
        out[v["name"]] = v
        z += 1
    return out


def _platform(kind: str, name: str, path: str) -> str:
    return _json({
        "$schema": PLATFORM_SCHEMA,
        "metadata": {"type": kind, "displayName": name},
        "config": {"version": "2.0", "logicalId": logical_id(path)},
    })


def _report_json(base_theme: BaseTheme | None) -> str:
    report: dict = {"$schema": REPORT_SCHEMA}
    if base_theme is not None:
        report["themeCollection"] = {
            "baseTheme": {
                "name": base_theme.name,
                # An OBJECT. As a string this aborts the open and loads nothing.
                "reportVersionAtImport": dict(REPORT_VERSION_AT_IMPORT),
                "type": "SharedResources",
            }
        }
        report["resourcePackages"] = [{
            "name": "SharedResources",
            "type": "SharedResources",
            "items": [{"name": base_theme.name,
                       "path": f"BaseThemes/{base_theme.name}.json",
                       "type": "BaseTheme"}],
        }]
    report["settings"] = {
        "useStylableVisualContainerHeader": True,
        "exportDataMode": "AllowSummarized",
        "defaultDrillFilterOtherVisuals": True,
        "allowChangeFilterTypes": True,
        "useEnhancedTooltips": True,
        "useDefaultAggregateDisplayName": True,
    }
    return _json(report)


def project_files(model: SemanticModel, source, *,
                  name: str = "EAReporting",
                  page_display_name: str = "Overview",
                  base_theme=_DEFAULT_THEME) -> dict[str, str]:
    """Every text file in the `.pbip` project, keyed by relative path.

    `base_theme` defaults to one of ours, emitted as part of the project.
    Passing a `BaseTheme` with no `content` means the caller will supply the
    file - see `required_static_resources()`. Passing None emits no theme, which
    is MEASURED to produce a project whose report does not load.
    """
    if base_theme is _DEFAULT_THEME:
        base_theme = default_base_theme()
    sm = f"{name}.SemanticModel"
    rp = f"{name}.Report"
    page = page_name(name)

    files = {
        f"{name}.pbip": _json({
            "version": PBIP_VERSION,
            "artifacts": [{"report": {"path": rp}}],
            "settings": {"enableAutoRecovery": True},
        }),
        # Power BI writes machine-local state into the project. Left out of
        # source control or every open dirties the tree.
        ".gitignore": NEWLINE.join(["**/.pbi/localSettings.json",
                                    "**/.pbi/cache.abf", ""]),

        f"{sm}/.platform": _platform("SemanticModel", name, sm),
        f"{sm}/definition.pbism": _json({"version": PBISM_VERSION, "settings": {}}),

        f"{rp}/.platform": _platform("Report", name, rp),
        f"{rp}/definition.pbir": _json({
            "version": PBIR_VERSION,
            "datasetReference": {"byPath": {"path": f"../{sm}"}},
        }),
        f"{rp}/definition/version.json": _json({"$schema": VERSION_SCHEMA,
                                                "version": "2.0.0"}),
        f"{rp}/definition/pages/pages.json": _json({
            "$schema": PAGES_SCHEMA,
            "pageOrder": [page],
            "activePageName": page,
        }),
        f"{rp}/definition/pages/{page}/page.json": _json({
            "$schema": PAGE_SCHEMA,
            "name": page,
            "displayName": page_display_name,
            "displayOption": "FitToPage",
            "height": page_height(model),
            "width": 1280,
        }),
        f"{rp}/definition/report.json": _report_json(base_theme),
    }

    for vname, visual in overview_visuals(model, name).items():
        files[f"{rp}/definition/pages/{page}/visuals/{vname}/visual.json"] = _json(visual)

    if base_theme is not None and base_theme.content:
        files[f"{rp}/{base_theme.static_resource_path}"] = base_theme.content

    for path, text in render_definition(model, source).items():
        files[f"{sm}/definition/{path}"] = text

    return files


def required_static_resources(base_theme: BaseTheme | None) -> list[str]:
    """Paths the CALLER must supply, relative to the `.Report` folder.

    Empty for the default theme, whose JSON this module emits, and empty when no
    theme was asked for. Non-empty only when a caller named a theme and did not
    hand over its content - returned rather than silently assumed, so a writer
    can fail loudly instead of producing a project that references a file nobody
    put there.
    """
    if base_theme is None or base_theme.content:
        return []
    return [base_theme.static_resource_path]

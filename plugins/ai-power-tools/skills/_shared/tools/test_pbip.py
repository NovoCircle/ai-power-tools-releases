#!/usr/bin/env python3
"""Tests for `.pbip` project authoring.

    python -m pytest _shared/tools/test_pbip.py -q

Nothing here touches Power BI or the filesystem. Several assert measured
failure modes of the REPORT half, which is the part that cost real time:
`reportVersionAtImport` as a string loads nothing, and a bare `report.json`
loads the model then crashes every save path.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

from powerbi_model import model_from_definition
from pbip import (BaseTheme, DEFAULT_THEME_NAME, NEWLINE,
                  REPORT_VERSION_AT_IMPORT, default_base_theme, logical_id,
                  page_name, project_files, required_static_resources)
from tmdl import ParquetSource, SqlSource

PARQUET = ParquetSource(directory=r"C:\out\parquet")
SQL = SqlSource(server="SERVER", database="EARepository")


DEFINITION = json.loads(
    (Path(__file__).parent / "fixtures" / "westbrook.definition.json").read_text(encoding="utf-8"))


def semantic():
    """The Westbrook business layer. `n_tables` is unused: the model is the
    whole definition."""
    return model_from_definition(DEFINITION)


def parsed(files, path):
    return json.loads(files[path])


# ------------------------------------------------------------- the shape


def test_the_project_carries_both_halves_and_the_entry_point():
    files = project_files(semantic(), PARQUET, name="Westbrook")
    assert "Westbrook.pbip" in files
    assert "Westbrook.SemanticModel/definition.pbism" in files
    assert "Westbrook.Report/definition.pbir" in files


def test_the_semantic_model_definition_is_included_whole():
    files = project_files(semantic(), PARQUET, name="W")
    assert "W.SemanticModel/definition/model.tmdl" in files
    assert "W.SemanticModel/definition/relationships.tmdl" in files
    assert "W.SemanticModel/definition/database.tmdl" in files
    assert "W.SemanticModel/definition/cultures/en-US.tmdl" in files
    assert "W.SemanticModel/definition/tables/t_object.tmdl" in files


def test_the_report_points_at_the_semantic_model_by_relative_path():
    files = project_files(semantic(), PARQUET, name="W")
    ref = parsed(files, "W.Report/definition.pbir")["datasetReference"]["byPath"]
    assert ref["path"] == "../W.SemanticModel"


def test_the_pbip_points_at_the_report_folder():
    files = project_files(semantic(), PARQUET, name="W")
    assert parsed(files, "W.pbip")["artifacts"] == [{"report": {"path": "W.Report"}}]


def test_the_active_page_is_one_that_exists():
    """A pageOrder naming a page with no folder fails the report open."""
    files = project_files(semantic(), PARQUET, name="W")
    pages = parsed(files, "W.Report/definition/pages/pages.json")
    assert pages["pageOrder"] == [pages["activePageName"]]
    assert f"W.Report/definition/pages/{pages['activePageName']}/page.json" in files


def test_local_power_bi_state_is_git_ignored():
    """Power BI writes machine-local state into the project; without this every
    open dirties the tree."""
    assert "localSettings.json" in project_files(semantic(), PARQUET)[".gitignore"]


# -------------------------------------------------------------- every file


def test_every_file_is_crlf():
    """Read off a real project. A generated one that deviates is rejected."""
    for path, text in project_files(semantic(), PARQUET).items():
        assert "\r\n" in text, path
        assert "\r\r\n" not in text, path
        # The same strictness test_tmdl.py applies. A BARE LF slips past both
        # checks above, and the report half is exactly where one could hide.
        assert not re.search(r"(?<!\r)\n", text), f"{path} has a bare LF"


def test_every_json_file_is_valid_json():
    """An invalid project file fails the open with a message that does not say
    which file, so this is cheap insurance against an expensive hunt."""
    for path, text in project_files(semantic(), PARQUET,
                                    base_theme=BaseTheme("X")).items():
        if path.endswith(".json") or path.endswith(".pbip") \
                or path.endswith(".pbism") or path.endswith(".pbir") \
                or path.endswith(".platform"):
            assert json.loads(text) is not None, path


# ------------------------------------------------------------ determinism


def test_two_runs_produce_an_identical_project():
    assert project_files(semantic(), PARQUET, name="W") == \
        project_files(semantic(), PARQUET, name="W")


def test_logical_ids_and_the_page_name_are_derived_not_minted():
    """A re-emitted project has to be the same project, or re-applying it
    rebuilds the customer's report."""
    assert logical_id("W.Report") == logical_id("W.Report")
    assert logical_id("W.Report") != logical_id("W.SemanticModel")
    assert page_name("W") == page_name("W")
    assert page_name("W") != page_name("X")


def test_the_page_name_is_an_opaque_identifier_not_a_display_name():
    name = page_name("Westbrook")
    assert len(name) == 20
    assert name.isalnum()


def test_the_display_name_is_separate_from_the_identifier():
    files = project_files(semantic(), PARQUET, name="W", page_display_name="Portfolio")
    page = parsed(files, f"W.Report/definition/pages/{page_name('W')}/page.json")
    assert page["displayName"] == "Portfolio"
    assert page["name"] == page_name("W")


# ------------------------------------------------------- the report half


def test_report_version_at_import_is_an_object_never_a_string():
    """MEASURED: as a string this aborts the open with a precise error and Power
    BI loads NOTHING - not the report, not the model."""
    files = project_files(semantic(), PARQUET, base_theme=BaseTheme("Fluent"))
    theme = parsed(files, "EAReporting.Report/definition/report.json")
    at_import = theme["themeCollection"]["baseTheme"]["reportVersionAtImport"]
    assert isinstance(at_import, dict)
    assert set(at_import) == {"visual", "report", "page"}
    assert at_import == REPORT_VERSION_AT_IMPORT


def test_report_json_carries_more_than_a_schema():
    """MEASURED: a report.json with only `$schema` loads the model, fails the
    report with an opaque activity id, and then CRASHES EVERY SAVE PATH with a
    null reference - so the project cannot be saved at all."""
    files = project_files(semantic(), PARQUET)
    report = parsed(files, "EAReporting.Report/definition/report.json")
    assert set(report) > {"$schema"}
    assert report["settings"]


def test_a_theme_is_emitted_by_default_because_without_one_the_report_fails():
    """MEASURED 2026-10-02 on 2.158.1177.0: with no `themeCollection` and no
    `resourcePackages` the semantic model loads and the REPORT fails with
    'Failed to load the report', whose details are an activity id and nothing
    else. So the default is a theme, not the absence of one."""
    files = project_files(semantic(), PARQUET)
    report = parsed(files, "EAReporting.Report/definition/report.json")
    assert report["themeCollection"]["baseTheme"]["name"] == DEFAULT_THEME_NAME
    assert report["resourcePackages"][0]["items"][0]["path"] == \
        f"BaseThemes/{DEFAULT_THEME_NAME}.json"


def test_the_default_theme_is_ours_and_travels_with_the_project():
    """MEASURED: a minimal theme of our own opens exactly as cleanly as Power
    BI's. So nothing here redistributes someone else's file, and the caller has
    nothing to supply."""
    files = project_files(semantic(), PARQUET)
    path = f"EAReporting.Report/{default_base_theme().static_resource_path}"
    assert path in files
    assert json.loads(files[path])["name"] == DEFAULT_THEME_NAME
    assert required_static_resources(default_base_theme()) == []


def test_naming_a_theme_without_its_content_declares_what_the_caller_must_supply():
    """Returned rather than silently assumed, so a writer fails loudly instead
    of emitting a project that references a file nobody put there."""
    theme = BaseTheme("SomeOtherTheme")
    files = project_files(semantic(), PARQUET, base_theme=theme)
    report = parsed(files, "EAReporting.Report/definition/report.json")
    assert report["resourcePackages"][0]["items"][0]["path"] == \
        "BaseThemes/SomeOtherTheme.json"
    assert required_static_resources(theme) == \
        ["StaticResources/SharedResources/BaseThemes/SomeOtherTheme.json"]
    assert f"EAReporting.Report/{theme.static_resource_path}" not in files


def test_no_theme_at_all_is_possible_but_is_the_known_broken_shape():
    """Kept so the measured failure can be reproduced, not for ordinary use."""
    report = parsed(project_files(semantic(), PARQUET, base_theme=None),
                    "EAReporting.Report/definition/report.json")
    assert "themeCollection" not in report
    assert "resourcePackages" not in report
    assert required_static_resources(None) == []


# ------------------------------------------ the cross-path guarantee again


def test_the_project_is_identical_across_paths_apart_from_the_partition():
    """The same assertion `test_tmdl.py` makes about the definition, made again
    at the level a customer actually receives: a whole project."""
    a = project_files(semantic(), PARQUET, name="W")
    b = project_files(semantic(), SQL, name="W")
    assert set(a) == set(b)
    differing = {p for p in a if a[p] != b[p]}
    assert differing == {p for p in a if "/definition/tables/" in p}


def test_nothing_outside_the_table_files_mentions_the_source():
    """A path-specific string leaking into the report half or the model file
    would make a customer's project unportable between paths."""
    files = project_files(semantic(), PARQUET, name="W")
    for path, text in files.items():
        if "/definition/tables/" in path:
            continue
        assert "Parquet.Document" not in text, path
        assert "out\\parquet" not in text, path

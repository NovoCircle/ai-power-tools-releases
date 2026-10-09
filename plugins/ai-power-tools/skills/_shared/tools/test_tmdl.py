#!/usr/bin/env python3
"""Tests for TMDL rendering, including the cross-path identity guarantee.

    python -m pytest _shared/tools/test_tmdl.py -q

Nothing here touches a repository, a COM object, Power BI or the filesystem.

THE IDENTITY TEST IS THE POINT OF THIS FILE. Three paths emit a Power BI model -
a direct-access database (`APT-2026-0230`), a reporting database
(`APT-2026-0302`) and Parquet (`APT-2026-0212`) - and the claim is that a
customer gets the same model whichever they pick. `test_only_the_partition_*`
is what makes that claim checkable instead of aspirational.
"""
from __future__ import annotations

import json
import re

import pytest

from semantic_model import (Measure, Relationship, SemanticColumn,
                            SemanticModel, SemanticTable)
from tmdl import (NEWLINE, ParquetSource, SqlSource, ident, lineage_tag,
                  m_literal,
                  render_culture, render_definition, render_model,
                  render_relationships, render_table)

CON = "Con_entity_0 Uses entity_1"
PHYSICAL = "t_object"


def semantic(n_tables=2):
    """A business layer in miniature: entity tables, one connector table with its
    one inactive relationship and the measure that reaches it, and one hidden
    physical table filtered by the business layer."""
    assert n_tables >= 2
    tables = [
        SemanticTable(
            name=f"entity_{i}", description=f"Entity {i} holds things.",
            columns=[SemanticColumn("ea_guid", "string", is_hidden=True),
                     SemanticColumn("criticality", "string", description="How critical.")])
        for i in range(n_tables)
    ]
    tables.append(SemanticTable(
        name=CON,
        columns=[SemanticColumn("source_guid", "string"), SemanticColumn("target_guid", "string")],
        measures=[Measure(
            name="Uses by target entity_1",
            expression="CALCULATE(COUNTROWS('Con_entity_0 Uses entity_1'), "
                       "USERELATIONSHIP('Con_entity_0 Uses entity_1'[target_guid], entity_1[ea_guid]))",
            description="Rows whose target is the selected entity_1.")]))
    tables.append(SemanticTable(
        name=PHYSICAL, is_hidden=True,
        columns=[SemanticColumn("Object_ID", "int64", format_string="0"),
                 SemanticColumn("ea_guid", "string")]))
    rels = [
        Relationship("gen_con_source", CON, "source_guid", "entity_0", "ea_guid", why="connector source"),
        Relationship("gen_con_target", CON, "target_guid", "entity_1", "ea_guid", is_active=False,
                     why="second relationship between these two tables"),
    ]
    rels += [Relationship(f"gen_phys_{i}", PHYSICAL, "ea_guid", f"entity_{i}", "ea_guid",
                          why="business layer filters the physical layer")
             for i in range(n_tables)]
    return SemanticModel(tables=tables, relationships=rels)


def one_to_one(n):
    sm = semantic()
    sm.relationships += [
        Relationship(f"gen_one_{i}", f"entity_{i}", "ea_guid", PHYSICAL, "ea_guid",
                     from_cardinality="one", cross_filtering="bothDirections")
        for i in range(n)]
    return sm


PARQUET = ParquetSource(directory=r"C:\out\parquet")
SQL = SqlSource(server="SERVER\\INSTANCE", database="EARepository")


def strip_partition(text: str) -> str:
    """Drop the partition block, which is the one part allowed to differ."""
    out, skipping = [], False
    for line in text.split(NEWLINE):
        if line.startswith("\tpartition "):
            skipping = True
            continue
        if skipping:
            if line.startswith("\tannotation "):
                skipping = False
            else:
                continue
        out.append(line)
    return NEWLINE.join(out)


# ------------------------------------------------------- the format rules


def test_every_rendered_file_uses_crlf():
    """Read off a real 2.158 project. A generated file that deviates is
    rejected on apply, so this is not a style question."""
    for path, text in render_definition(semantic(), PARQUET).items():
        assert "\r\n" in text, path
        assert not re.search(r"(?<!\r)\n", text), f"{path} has a bare LF"


def test_indentation_is_tabs_and_never_spaces():
    """TMDL is tab-indented. Spaces do not parse."""
    text = render_table(semantic().table("entity_0"), PARQUET)
    for line in text.split(NEWLINE):
        if line and line[0].isspace():
            assert line.startswith("\t"), repr(line)


def test_a_description_precedes_the_object_it_describes():
    """TMDL `///` lines attach to the NEXT declaration. Putting one after the
    declaration describes the wrong thing."""
    lines = render_table(semantic().table("entity_0"), PARQUET).split(NEWLINE)
    i = lines.index("/// Entity 0 holds things.")
    assert lines[i + 1] == "table entity_0"
    j = next(k for k, l in enumerate(lines) if l == "\t/// How critical.")
    assert lines[j + 1] == "\tcolumn criticality"


def test_a_description_is_collapsed_to_one_line():
    """A newline inside a `///` line ends the comment and the rest becomes
    syntax."""
    sm = semantic()
    sm.table("entity_0").description = "two\nlines\there"
    assert "/// two lines here" in render_table(sm.table("entity_0"), PARQUET)


def test_identifiers_are_quoted_only_when_they_have_to_be():
    assert ident("entity_0") == "entity_0"
    assert ident("_hidden") == "_hidden"
    assert ident("Business Application") == "'Business Application'"
    assert ident("it's") == "'it''s'"


# ------------------------------------------------------------ table files


def test_a_hidden_table_says_so_and_a_visible_one_does_not():
    """Asserted as a whole LINE: a hidden COLUMN renders `\\t\\tisHidden`, which
    contains the table form as a substring and would pass a loose check."""
    sm = semantic()
    assert "\tisHidden" in render_table(sm.table(PHYSICAL), PARQUET).split(NEWLINE)
    assert "\tisHidden" not in render_table(sm.table("entity_0"), PARQUET).split(NEWLINE)


def test_a_hidden_column_says_so():
    text = render_table(semantic().table("entity_0"), PARQUET)
    guid = text.split("\tcolumn ea_guid")[1].split("\tcolumn")[0]
    assert "\t\tisHidden" in guid


def test_an_int_column_carries_a_format_string():
    sm = semantic()
    obj = render_table(sm.table(PHYSICAL), PARQUET)
    block = obj.split("\tcolumn Object_ID")[1].split("\tcolumn")[0]
    assert "\t\tformatString: 0" in block


def test_measures_render_on_their_own_table_and_nowhere_else():
    sm = semantic()
    host = render_table(sm.table(CON), PARQUET)
    assert "\tmeasure 'Uses by target entity_1' =" in host
    assert "USERELATIONSHIP" in host
    assert "\tmeasure" not in render_table(sm.table(PHYSICAL), PARQUET)


def test_a_measure_name_with_a_space_is_quoted():
    host = render_table(semantic().table(CON), PARQUET)
    assert "\tmeasure 'Uses by target entity_1' = CALCULATE(" in host


def test_a_table_ends_with_the_result_type_annotation():
    text = render_table(semantic().table("entity_0"), PARQUET)
    assert text.rstrip(NEWLINE).endswith("\tannotation PBI_ResultType = Table")


# ----------------------------------------------------------- lineage tags


def test_a_lineage_tag_is_derived_so_two_runs_match():
    """Minting fresh GUIDs per run is what would break an existing report's
    field bindings."""
    assert lineage_tag("table", "entity_0") == lineage_tag("table", "entity_0")
    assert render_table(semantic().table("entity_0"), PARQUET) == \
        render_table(semantic().table("entity_0"), PARQUET)


def test_different_objects_get_different_tags():
    assert lineage_tag("table", "a") != lineage_tag("table", "b")
    assert lineage_tag("table", "a") != lineage_tag("column", "a")


def test_a_tag_does_not_depend_on_the_partition_source():
    """A customer moving between paths keeps their report. If the tag moved with
    the source, every field binding would break on the switch."""
    sm = semantic()
    parquet = {l for l in render_table(sm.table("entity_0"), PARQUET).split(NEWLINE)
               if "lineageTag" in l}
    sql = {l for l in render_table(sm.table("entity_0"), SQL).split(NEWLINE)
           if "lineageTag" in l}
    assert parquet == sql


# --------------------------------------------------------- relationships


def test_the_inactive_relationship_is_marked_and_the_active_ones_are_not():
    text = render_relationships(semantic())
    assert "\tisActive: false" in text
    assert text.count("\tisActive: false") == 1


def test_a_one_to_one_emits_both_directions_and_the_cardinality():
    text = render_relationships(one_to_one(3))
    assert text.count("\tcrossFilteringBehavior: bothDirections") == 3
    assert text.count("\tfromCardinality: one") == 3


def test_a_many_to_one_emits_neither():
    """`automatic` and `many` are the defaults. Stating them adds noise to a
    file the customer is expected to read."""
    sm = semantic()
    rel = next(r for r in sm.relationships if r.from_table == PHYSICAL)
    text = render_relationships(sm)
    block = text.split(f"relationship {rel.name}")[1].split("relationship ")[0]
    assert "crossFilteringBehavior" not in block
    assert "fromCardinality" not in block


def test_a_relationship_carries_no_description():
    """MEASURED 2026-10-02, Power BI 2.158.1177.0. A `///` line before
    `relationship` sets a `description` property and `SingleColumnRelationship`
    has none, so THE WHOLE PROJECT fails to open:

        Property 'description' is unknown and is not expected in the situation
        it appears.

    No file is named and no line number is given. Tables, columns and measures
    do take descriptions; relationships do not. The rationale stays on
    `Relationship.why` and simply cannot travel in the TMDL."""
    text = render_relationships(semantic())
    assert "///" not in text
    assert text.startswith("relationship ")
    for block in text.split("relationship ")[1:]:
        assert block.count("fromColumn:") == 1


def test_the_reason_is_still_carried_on_the_model_even_though_it_is_not_emitted():
    sm = semantic()
    assert all(r.why for r in sm.relationships)
    assert "second relationship" in sm.inactive[0].why


def test_endpoints_render_as_table_dot_column():
    text = render_relationships(semantic())
    assert f"\tfromColumn: {ident(CON)}.target_guid" in text
    assert "\ttoColumn: entity_1.ea_guid" in text


# ------------------------------------------------------- model and culture


def test_the_model_suppresses_auto_date_tables():
    """The suppression is emitted whether or not the model has a DATETIME
    column, so a column added later brings no automatic tables."""
    assert "annotation __PBI_TimeIntelligenceEnabled = 0" in render_model(semantic())


def test_the_model_refs_every_table_exactly_once():
    sm = semantic(n_tables=3)
    text = render_model(sm)
    for t in sm.tables:
        assert text.count(f"ref table {ident(t.name)}{NEWLINE}") == 1


def test_the_query_order_lists_every_table():
    sm = semantic(n_tables=3)
    order = render_model(sm).split("PBI_QueryOrder = [")[1].split("]")[0]
    assert order.count(",") == len(sm.tables) - 1
    for t in sm.tables:
        assert f'"{t.name}"' in order


def test_the_culture_block_contains_valid_json():
    """An invalid linguisticMetadata payload is rejected with the whole file."""
    text = render_culture("en-US")
    raw = text[text.index("{"):text.rindex("}") + 1]
    assert json.loads(raw.replace("\t", "").replace("\r\n", "\n"))["Language"] == "en-US"


# -------------------------------------------------------------- partitions


def test_the_parquet_partition_imports_and_names_the_source_table():
    """A table's model name and its source name can differ. The partition must
    follow the SOURCE name."""
    sm = semantic()
    sm.table(CON).source_name = "con_source"
    text = render_table(sm.table(CON), PARQUET)
    assert "\t\tmode: import" in text
    assert r"C:\out\parquet\con_source.parquet" in text
    assert "Parquet.Document(File.Contents(" in text


def test_the_sql_partition_is_direct_query_by_default():
    """DirectQuery is the default mode of a SQL source."""
    text = render_table(semantic().table("entity_0"), SQL)
    assert "\t\tmode: directQuery" in text
    assert 'Sql.Database("SERVER\\INSTANCE", "EARepository")' in text
    assert 'Item="entity_0"' in text


def test_a_trailing_separator_on_the_directory_is_not_doubled():
    text = render_table(semantic().table("entity_0"),
                        ParquetSource(directory="C:/out/"))
    assert "C:/out/entity_0.parquet" in text


# -------------------------------------------- THE CROSS-PATH IDENTITY TEST


def test_the_same_files_are_emitted_whichever_path_is_chosen():
    assert set(render_definition(semantic(n_tables=4), PARQUET)) == \
        set(render_definition(semantic(n_tables=4), SQL))


def test_only_the_partition_differs_between_paths():
    """The product's claim, made checkable. Everything a customer sees - tables,
    columns, relationships, measures, descriptions, lineage tags - is identical
    across all three paths. Only where the rows come from changes."""
    parquet = render_definition(semantic(n_tables=4), PARQUET)
    sql = render_definition(semantic(n_tables=4), SQL)
    for path in parquet:
        assert strip_partition(parquet[path]) == strip_partition(sql[path]), path


def test_only_table_files_differ_at_all():
    """`database.tmdl`, `model.tmdl`, `relationships.tmdl` and the culture carry
    no source information, so they must be byte-identical without stripping."""
    parquet = render_definition(semantic(n_tables=4), PARQUET)
    sql = render_definition(semantic(n_tables=4), SQL)
    differing = {p for p in parquet if parquet[p] != sql[p]}
    assert differing == {p for p in parquet if p.startswith("tables/")}


def test_the_partition_really_does_differ_so_the_test_above_can_fail():
    """A stripping test that passes because nothing differs proves nothing."""
    parquet = render_definition(semantic(), PARQUET)
    sql = render_definition(semantic(), SQL)
    assert parquet["tables/entity_0.tmdl"] != sql["tables/entity_0.tmdl"]


def test_an_import_parquet_path_and_a_direct_query_sql_path_are_the_two_shapes():
    """Parquet is read by import. A SQL source is DirectQuery unless the caller
    asks for import."""
    assert ParquetSource(directory="x").mode == "import"
    assert SqlSource(server="s", database="d").mode == "directQuery"


def test_the_definition_holds_one_file_per_table_plus_four():
    sm = semantic(n_tables=4)
    files = render_definition(sm, PARQUET)
    assert len(files) == len(sm.tables) + 4
    assert "database.tmdl" in files
    assert "model.tmdl" in files
    assert "relationships.tmdl" in files
    assert "cultures/en-US.tmdl" in files


# ---------------------------------------------- escaping at the boundary


def test_a_leading_digit_is_quoted_because_model_content_reaches_it():
    """`ea_census.snake_case` turns a tag named "2024 Target" into
    `2024_target`, so a leading digit is ordinary model content."""
    assert ident("2024_target") == "'2024_target'"
    assert ident("target_2024") == "target_2024"


def test_a_leading_digit_source_column_is_bare():
    """The declaration is quoted and `sourceColumn` is written bare.

    This pins what is emitted. It does not establish that Power BI accepts it.
    """
    from tmdl import render_column

    table = SemanticTable(name="entity_0")
    lines = render_column(table, SemanticColumn(name="2024_target"))
    body = "\n".join(lines)

    assert "column '2024_target'" in body, "the declaration must be quoted"
    assert "sourceColumn: 2024_target" in body, "the property value is bare"
    assert "sourceColumn: '2024_target'" not in body


def test_non_ascii_letters_are_quoted():
    """`str.isalnum()` is true for non-ASCII letters; `ident` quotes them."""
    assert ident("naive") == "naive"
    assert ident("na\u00efve").startswith("'")
    assert ident("\u03b1\u03b2\u03b3").startswith("'")


def test_an_m_literal_escapes_the_quote_that_would_end_it():
    """A quote is doubled, so the value cannot close the literal."""
    assert m_literal('a"b') == 'a""b'
    assert '""' in m_literal('x" & Web.Contents("http://example.invalid") & "')


def test_an_m_literal_escapes_the_sequence_that_introduces_an_escape():
    """`#(` becomes `#(#)(`, so `#(lf)` in a value stays text."""
    assert m_literal("a#(lf)b") == "a#(#)(lf)b"


def test_a_BARE_hash_is_left_alone_because_M_allows_it():
    """A lone `#` in a path or an instance name is left alone; `#(` is the
    sequence that gets escaped."""
    assert m_literal(chr(92) + "run#3") == chr(92) + "run#3"
    assert m_literal("SRV" + chr(92) + "C#") == "SRV" + chr(92) + "C#"


def test_an_m_literal_escapes_line_breaks_and_tabs():
    """CR, LF and TAB become `#(cr)`, `#(lf)` and `#(tab)`."""
    assert m_literal("a" + chr(13) + chr(10) + "b") == "a#(cr)#(lf)b"
    assert m_literal("a" + chr(9) + "b") == "a#(tab)b"


def test_the_escapes_do_not_mangle_each_other():
    """`#(` is replaced first, so the `#(lf)` inserted afterwards is not
    re-escaped."""
    assert m_literal("x" + chr(10) + "y") == "x#(lf)y"
    assert m_literal("#(a" + chr(10) + "b") == "#(#)(a#(lf)b"


def test_a_backslash_is_not_an_m_escape():
    r"""A backslash is left alone."""
    assert m_literal(r"C:\out\parquet") == r"C:\out\parquet"


def test_the_partition_sources_actually_use_the_escaper():
    """A hostile `directory`, `server` and `database` come out escaped."""
    sm = semantic()
    hostile = ParquetSource(directory=r'C:\out" & Web.Contents("http://x") & "')
    line = next(l for l in render_table(sm.table("entity_0"), hostile).split(NEWLINE)
                if "Parquet.Document" in l)
    # The injected quotes come out doubled.
    assert '""' in line
    assert line.count('"') % 2 == 0
    sql = render_table(sm.table("entity_0"),
                       SqlSource(server='s"x', database='d#(lf)y'))
    assert 's""x' in sql
    assert "#(#)(lf)" in sql


def test_schema_source_name_and_suffix_are_escaped():
    """Each is asserted against the exact escaped text expected in the output.

    `suffix` gets a hostile value of its own: `m_literal(x + ".parquet")` equals
    `m_literal(x) + ".parquet"`, so a default suffix cannot show whether it was
    escaped.
    """
    hostile = 'x" & Web.Contents("http://example.invalid") & "'
    escaped = m_literal(hostile)
    table = SemanticTable(name="entity_0", source_name=hostile,
                          columns=[SemanticColumn(name="c")])

    sql = render_table(table, SqlSource(server="s", database="d", schema=hostile))
    assert f'[Schema="{escaped}"' in sql, "schema reached the literal unescaped"
    assert f'Item="{escaped}"]' in sql, "source_name reached Item unescaped"
    assert hostile not in sql

    # source_name is concatenated into the path, which is escaped as a whole.
    line = next(l for l in render_table(table, ParquetSource(directory=r"C:\out"))
                .split(NEWLINE) if "Parquet.Document" in l)
    assert m_literal("C:\\out\\" + hostile + ".parquet") in line
    assert hostile not in line

    hostile_suffix = '.parquet" & Web.Contents("http://example.invalid") & "'
    pq = ParquetSource(directory=r"C:\out", suffix=hostile_suffix)
    line = next(l for l in render_table(table, pq).split(NEWLINE)
                if "Parquet.Document" in l)
    assert m_literal("C:\\out\\" + hostile + hostile_suffix) in line, \
        "suffix reached the literal unescaped"
    assert hostile_suffix not in line


def test_an_identifier_containing_a_line_break_is_refused():
    """CR, LF or TAB in an identifier raises instead of being emitted."""
    with pytest.raises(ValueError, match="line break"):
        ident("a\nb")
    with pytest.raises(ValueError, match="line break"):
        ident("a\tb")


# ------------------------- APT-2026-0248: the four caller-value sites


@pytest.mark.parametrize("bad", ["a\nb", "a\r\nb", "a\tb", " lead", "trail ", ""])
def test_a_source_column_a_bare_value_cannot_carry_is_refused(bad):
    """A newline would start a second property; whitespace would be trimmed."""
    from tmdl import render_column

    table = SemanticTable(name="entity_0")
    column = SemanticColumn(name="x", source_column="x")
    column.source_column = bad
    with pytest.raises(ValueError, match="SemanticColumn.source_column"):
        render_column(table, column)


def test_a_source_column_with_spaces_and_punctuation_inside_is_written_as_is():
    """Only what ends or trims the value is refused; a tag name is not mangled."""
    from tmdl import render_column

    lines = render_column(SemanticTable(name="t"),
                          SemanticColumn(name="x", source_column="Owner's (name): A/B"))
    assert "\t\tsourceColumn: Owner's (name): A/B" in lines


@pytest.mark.parametrize("bad", ["gen_a\ngen_b", "gen_a\tb"])
def test_a_relationship_name_with_a_line_break_is_refused(bad):
    sm = semantic()
    sm.relationships[0].name = bad
    with pytest.raises(ValueError, match="line break"):
        render_relationships(sm)


def test_a_relationship_name_goes_through_ident():
    """Its delimiter is the identifier quote: a quote is doubled, not closing."""
    sm = semantic()
    sm.relationships[0].name = "rel 'x'"
    text = render_relationships(sm)
    assert "relationship 'rel ''x'''" in text
    assert "relationship gen_con_target" in text, "a plain name stays bare"


@pytest.mark.parametrize("name", [
    "../../evil", "..", ".", "a/b", "a\\b", "..\\..\\evil", "C:evil", "a\nb", "trail.", "NUL", "con.x"])
def test_a_table_file_cannot_resolve_outside_tables(name):
    from tmdl import table_file_name

    key = f"tables/{table_file_name(name)}.tmdl"
    stem = key[len("tables/"):-len(".tmdl")]
    assert "/" not in stem and "\\" not in stem and ":" not in stem
    assert stem not in ("", ".", "..")
    assert not stem.endswith((".", " "))
    assert all(ord(c) >= 32 for c in stem)
    assert stem.split(".")[0].upper() not in ("NUL", "CON")


def test_a_safe_table_name_keeps_its_file_name_and_encodings_do_not_collide():
    from tmdl import table_file_name

    assert table_file_name(CON) == CON, "ordinary names are unchanged"
    assert table_file_name("a/b") != table_file_name("a%2Fb")


def test_the_definition_writes_a_hostile_table_name_inside_tables():
    sm = semantic()
    sm.tables[0].name = "../../evil"
    files = render_definition(sm, PARQUET)
    tables = [k for k in files if k.startswith("tables/")]
    assert len(tables) == len(sm.tables)
    assert "tables/..%2F..%2Fevil.tmdl" in files
    assert "table '../../evil'" in files["tables/..%2F..%2Fevil.tmdl"]


@pytest.mark.parametrize("bad", ["import\n\t\tisHidden", "directQuery\t", "Import", "push"])
def test_a_partition_mode_outside_the_known_set_is_refused(bad):
    for source in (ParquetSource(directory="C:\\x", mode=bad),
                   SqlSource(server="s", database="d", mode=bad)):
        with pytest.raises(ValueError, match="partition mode"):
            render_table(semantic().tables[0], source)


def test_the_three_modes_render():
    for mode in ("import", "directQuery", "dual"):
        text = render_table(semantic().tables[0], SqlSource(server="s", database="d", mode=mode))
        assert f"\t\tmode: {mode}\r\n" in text

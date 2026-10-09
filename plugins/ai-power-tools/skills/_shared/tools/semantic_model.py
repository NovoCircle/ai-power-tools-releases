#!/usr/bin/env python3
"""The semantic model: the data structures `tmdl.py` and `pbip.py` render.

PURE. No repository calls, no COM, no file or network I/O, no clock, no
randomness. It describes tables, columns, relationships and measures, and
nothing else writes or applies anything.

    definition JSON  ->  SemanticModel  ->  TMDL text
    (powerbi_model)                          ^
                                  Parquet.Document(...) | Sql.Database(...)

`powerbi_model.model_from_definition` builds a `SemanticModel` from the
business-layer definition the server writes (`APT-2026-0301`). The only thing
that varies between the three paths is where a table's rows come from, and that
is passed to the renderer, not chosen here.

WHY THE RELATIONSHIPS ARE GENERATED AND NEVER INFERRED
------------------------------------------------------
Measured 2026-10-02 on a 40-table model loaded with no relationships defined:
Power BI's own auto-detect produced 63 relationships where the model needed 38.
Twenty-eight were invented from shared enum values - two tables related because
both happened to hold the same classification value. One correct relationship
was switched off silently because two paths competed. Nothing in Power BI
reports any of this; the report looks finished. The generator therefore
declares the complete relationship set itself.
"""
from __future__ import annotations

from dataclasses import dataclass, field, asdict

DEFAULT_TMDL_TYPE = "string"


@dataclass
class SemanticColumn:
    name: str
    data_type: str = DEFAULT_TMDL_TYPE
    source_column: str = ""
    is_hidden: bool = False
    format_string: str = ""
    summarize_by: str = "none"
    description: str = ""

    def __post_init__(self) -> None:
        if not self.source_column:
            self.source_column = self.name


@dataclass
class Measure:
    name: str
    expression: str
    format_string: str = "0"
    description: str = ""


@dataclass
class SemanticTable:
    #: The name in the model, which is what the customer reads in the field list.
    name: str
    #: The name at the source: a view (`schema.item` for SQL) or a Parquet file.
    #: `name` is for TMDL identifiers, `source_name` is for the partition.
    source_name: str = ""
    is_hidden: bool = False
    description: str = ""
    columns: list[SemanticColumn] = field(default_factory=list)
    measures: list[Measure] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not self.source_name:
            self.source_name = self.name


@dataclass
class Relationship:
    name: str
    from_table: str
    from_column: str
    to_table: str
    to_column: str
    #: "many" or "one". A 1:1 is declared from the entity side.
    from_cardinality: str = "many"
    #: "automatic" or "bothDirections". Power BI REJECTS THE WHOLE TMDL FILE on
    #: apply if a one-to-one does not carry bothDirections, so this is not a
    #: preference.
    cross_filtering: str = "automatic"
    is_active: bool = True
    #: Why this relationship exists, or why it is inactive. Kept on the model;
    #: TMDL cannot carry a description on a relationship.
    why: str = ""


@dataclass
class SemanticModel:
    culture: str = "en-US"
    tables: list[SemanticTable] = field(default_factory=list)
    relationships: list[Relationship] = field(default_factory=list)

    def to_dict(self) -> dict:
        """Plain data, for serializing to YAML or JSON."""
        return asdict(self)

    def table(self, name: str) -> SemanticTable | None:
        return next((t for t in self.tables if t.name == name), None)

    @property
    def inactive(self) -> list[Relationship]:
        return [r for r in self.relationships if not r.is_active]


def _rel_name(from_table: str, from_column: str, to_table: str) -> str:
    """A deterministic relationship identifier.

    Includes the source COLUMN because a table can relate to the same table
    twice (a connector's source and target), and the two differ only by which
    column they join on.
    """
    parts = f"{from_table}_{from_column}_to_{to_table}"
    safe = "".join(c if c.isalnum() else "_" for c in parts)
    return "gen_" + safe.strip("_").lower()

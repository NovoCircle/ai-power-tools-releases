#!/usr/bin/env python3
"""Profile-aware census of a Sparx EA repository.

This is the shared seam between MDG generation (R1) and the reporting database
(R2/R3). Both consume it; neither may re-implement it. Re-implementing the
provenance rule on one side is how a 24-element drop got into a prototype once
already.

PURE. No repository calls, no COM, no file or network I/O, no clock, no
randomness. It takes rows that somebody else fetched - plain dicts, exactly as
`execute_sql` returns them - and returns a census. Same input, same output,
every time.

WHY IT EXISTS AT ALL
--------------------
`t_object.Stereotype` holds a BARE name that does not identify the language. In
one repository `ApplicationComponent` resolves to `TOGAF::`, `BusinessProcess`
to `BPMN1.1::`, `Node` to `UPDM2::`, and several ArchiMate-looking names resolve
to no profile at all. The shipped `summarize_stereotype_usage` reads that column
and so cannot tell a governed element from an ad-hoc one (APT-2026-0214).

Profile binding lives in `t_xref` rows where `Name = 'Stereotypes'`, with a
`Description` of the form:

    @STEREO;Name=X;GUID={...};FQName=<profile>::X;@ENDSTEREO;

THREE MEASURED FACTS THIS MODULE EXISTS TO GET RIGHT
----------------------------------------------------
1. Provenance is **FQName present**, not "an xref row exists". The same
   stereotype name appears in several row forms - `Uses` as both
   `FQName=BMM::Uses` and bare `Name=Uses;GUID=...`. Testing for row existence
   dropped 24 elements in a prototype.

2. A multi-stereotype element is **several @STEREO blocks in ONE row**. The row
   count is 1. `re.search` for `FQName=` finds only the first and silently
   discards the rest - which is a defect this module's own reconciler had, and
   which was invisible until a fixture gained such an element.

3. `t_object.Stereotype` holds only the **first** stereotype, so any count taken
   from that column undercounts multi-stereotype elements.

TABLE IDENTITY - a decision, recorded
-------------------------------------
Two inherited design notes disagreed: one said identity is the profile FQName,
the other the `(stereotype, metaclass)` pair.

Resolved here as: **one entity per FQName** (a "System of Record" is one
concept whether someone drew it as a Component or a Class), with the metaclass
recorded per element and heterogeneity reported as a finding. That answers the
business question without destroying the distinction silently, which was the
stated worry behind the pair rule.

Elements with **no** profile binding keep the pair as identity, because there a
bare name genuinely is ambiguous across languages.
"""
from __future__ import annotations

import re
from collections import Counter, defaultdict
from dataclasses import dataclass, field

# --------------------------------------------------------------------------
# Exclusions. Both are REPORTED, never silently dropped - the count of what was
# excluded is part of the census.
# --------------------------------------------------------------------------

#: EA's own machinery. Never business content.
EA_INTERNAL_STEREOTYPES = frozenset({
    "EATool",
    "model document",
    "report package",
})

#: Profile-authoring machinery. A repository whose owner builds MDGs from a
#: source model inside the model carries these, and they are not business
#: content either. Measured: a 20-stereotype source model added under a model
#: root took a whole-repository census from 22 to 28 distinct stereotypes and
#: 131 to 161 stereotyped elements.
PROFILE_AUTHORING_STEREOTYPES = frozenset({
    "stereotype",
    "metaclass",
    "profile",
    "toolbox profile",
    "diagram profile",
    "mdg technology",
})

#: Profiles that are EA's own UML plumbing rather than a modeling language.
EA_INTERNAL_PROFILES = frozenset({"EAUML"})

_STEREO_BLOCK = re.compile(r"@STEREO;(.*?)@ENDSTEREO;", re.DOTALL)
_FIELD = re.compile(r"(\w+)=([^;]*);")


# --------------------------------------------------------------------------
# Parsing
# --------------------------------------------------------------------------

@dataclass(frozen=True, order=True)
class Stereotype:
    """One applied stereotype, resolved."""

    name: str
    fqname: str = ""     # "<profile>::Name" when bound, "" when ad hoc
    guid: str = ""

    @property
    def profile(self) -> str:
        """The profile namespace, or "" when this is an ad-hoc application."""
        return self.fqname.split("::", 1)[0] if "::" in self.fqname else ""

    @property
    def is_profile_bound(self) -> bool:
        """True when the application names a profile.

        THE rule: FQName present. Not "an xref row exists" - a row with only
        Name and GUID is an ad-hoc application and must be reported as one.
        """
        return bool(self.fqname)

    @property
    def is_unbound_qualified(self) -> bool:
        """True when the NAME is qualified text but no FQName binds it.

        `Name=WBA::Uses;GUID=...;` with no `FQName=` is a data defect, not
        ordinary ad-hoc use: someone typed a qualified name into a free-text
        stereotype field, and EA never recorded the binding.
        """
        return not self.fqname and "::" in self.name


def parse_stereotype_blocks(description: str | None) -> list[Stereotype]:
    """Parse every @STEREO block in one `t_xref.Description`.

    Returns a list because a multi-stereotype element packs several blocks into
    a single row. Order is preserved: EA writes the primary stereotype first,
    and that is the one `t_object.Stereotype` mirrors.

    Malformed or empty input yields an empty list rather than raising - a
    census over a real repository should not die on one odd row.
    """
    if not description:
        return []
    out: list[Stereotype] = []
    for block in _STEREO_BLOCK.findall(description):
        fields = dict(_FIELD.findall(block))
        name = (fields.get("Name") or "").strip()
        if not name:
            continue
        out.append(Stereotype(
            name=name,
            fqname=(fields.get("FQName") or "").strip(),
            guid=(fields.get("GUID") or "").strip(),
        ))
    return out


def build_stereotype_index(xref_rows) -> dict[str, list[Stereotype]]:
    """Index `t_xref` stereotype rows by the GUID they apply to.

    Expects rows with `Client` (the element or connector `ea_guid`) and
    `Description`. Rows that parse to nothing are omitted.

    A GUID appearing on more than one row has its stereotypes concatenated;
    that is not the normal shape - EA packs them into one row - but merging is
    the lossless reading.
    """
    index: dict[str, list[Stereotype]] = defaultdict(list)
    for row in xref_rows:
        guid = (row.get("Client") or "").strip()
        if not guid:
            continue
        parsed = parse_stereotype_blocks(row.get("Description"))
        if parsed:
            index[guid].extend(parsed)
    return dict(index)


# --------------------------------------------------------------------------
# Identity
# --------------------------------------------------------------------------

def entity_key(stereo: Stereotype, metaclass: str) -> str:
    """The census key an element lands under.

    Profile-bound  -> the FQName. One entity per declared concept; the
                      metaclass is carried per element and heterogeneity is
                      reported rather than split.
    Ad hoc         -> "name|metaclass". A bare name is ambiguous across
                      languages, so the metaclass has to carry identity.
    """
    return stereo.fqname if stereo.is_profile_bound else f"{stereo.name}|{metaclass}"


# --------------------------------------------------------------------------
# Census
# --------------------------------------------------------------------------

@dataclass
class Entity:
    """One candidate entity: everything the census knows about one key."""

    key: str
    stereotype: str
    fqname: str = ""
    profile: str = ""
    guids: set[str] = field(default_factory=set)
    metaclasses: Counter = field(default_factory=Counter)

    @property
    def count(self) -> int:
        return len(self.guids)

    @property
    def is_profile_bound(self) -> bool:
        return bool(self.fqname)

    @property
    def primary_metaclass(self) -> str:
        """The most common metaclass, ties broken by name for determinism."""
        if not self.metaclasses:
            return ""
        top = max(self.metaclasses.values())
        return sorted(m for m, n in self.metaclasses.items() if n == top)[0]

    @property
    def is_heterogeneous(self) -> bool:
        """True when one stereotype is applied across several metaclasses.

        Real, and a finding rather than an error: it is how a modeler draws
        the same concept two ways. It is reported so a consumer can see it.
        """
        return len(self.metaclasses) > 1


@dataclass
class ElementCensus:
    """The result. Every list is deterministically ordered."""

    entities: list[Entity] = field(default_factory=list)
    #: guid -> the keys it landed under. Several when multi-stereotyped.
    placement: dict[str, list[str]] = field(default_factory=dict)
    excluded_ea_internal: Counter = field(default_factory=Counter)
    excluded_profile_authoring: Counter = field(default_factory=Counter)
    #: Elements carrying NO stereotype at all - the honest remainder. Plain UML
    #: classes, notes, boundaries. Real content, queryable through `element`.
    untyped_guids: set[str] = field(default_factory=set)
    #: Elements whose every stereotype was excluded as EA's own machinery or as
    #: profile-authoring scaffolding. NOT the same thing as untyped, and keeping
    #: them apart matters: lumping them together counted EA's report-package
    #: tags (`ReportName`, `SearchValue`, ...) as unplaced business data and
    #: overstated the remainder.
    excluded_guids: set[str] = field(default_factory=set)
    multi_stereotype_guids: set[str] = field(default_factory=set)

    @property
    def total_typed(self) -> int:
        """Elements landing in at least one entity. Not the sum of counts -
        a multi-stereotype element is in two entities and is one element."""
        return len(self.placement)


def census_elements(
    objects,
    stereotype_index: dict[str, list[Stereotype]],
    *,
    exclude_ea_internal: bool = True,
    exclude_profile_authoring: bool = True,
) -> ElementCensus:
    """Census elements by resolved stereotype.

    `objects` are `t_object` rows needing at least `ea_guid`, `Object_Type` and
    `Stereotype`. `stereotype_index` comes from `build_stereotype_index`.

    An element with no xref entry still counts: it falls back to the bare
    `Stereotype` column as an ad-hoc application, because dropping it would
    discard exactly the ungoverned content the census exists to surface.
    Elements with no stereotype at all are recorded in `untyped_guids` so the
    remainder is visible rather than lost.
    """
    entities: dict[str, Entity] = {}
    census = ElementCensus()

    for row in objects:
        guid = (row.get("ea_guid") or "").strip()
        if not guid:
            continue
        metaclass = (row.get("Object_Type") or "").strip()
        bare = (row.get("Stereotype") or "").strip()

        applied = stereotype_index.get(guid) or ([Stereotype(name=bare)] if bare else [])
        if not applied:
            census.untyped_guids.add(guid)
            continue
        if len(applied) > 1:
            census.multi_stereotype_guids.add(guid)

        excluded_any = False
        landed: list[str] = []
        for stereo in applied:
            if exclude_ea_internal and stereo.name in EA_INTERNAL_STEREOTYPES:
                census.excluded_ea_internal[stereo.name] += 1
                excluded_any = True
                continue
            if exclude_profile_authoring and stereo.name in PROFILE_AUTHORING_STEREOTYPES:
                census.excluded_profile_authoring[stereo.name] += 1
                excluded_any = True
                continue
            if stereo.profile in EA_INTERNAL_PROFILES:
                census.excluded_ea_internal[stereo.fqname] += 1
                excluded_any = True
                continue

            key = entity_key(stereo, metaclass)
            ent = entities.get(key)
            if ent is None:
                ent = Entity(key=key, stereotype=stereo.name,
                             fqname=stereo.fqname, profile=stereo.profile)
                entities[key] = ent
            ent.guids.add(guid)
            ent.metaclasses[metaclass] += 1
            if key not in landed:
                landed.append(key)

        if landed:
            census.placement[guid] = landed
        elif excluded_any:
            census.excluded_guids.add(guid)
        else:
            census.untyped_guids.add(guid)

    # Deterministic: descending count, then key. Never dict insertion order.
    census.entities = sorted(entities.values(), key=lambda e: (-e.count, e.key))
    return census


# --------------------------------------------------------------------------
# Connector census
# --------------------------------------------------------------------------
#
# Same provenance rule as elements - FQName present, every @STEREO block parsed
# from the same `t_xref` index - applied to `t_connector`. Measured on a demo
# repository: of the stereotyped connectors, 34 carried an FQName and 31 were
# ad hoc, and nothing reported the 31.
#
# Identity differs from elements in one way: a connector has no metaclass, its
# base type (`Connector_Type`) is the nearest thing, and the same stereotype on
# two base types is two different modeling choices. So the key is the
# stereotype identity AND the base type, for profile-bound and ad hoc alike.

#: EA `Connector_Type` values. Used only to tell a connector stereotype from an
#: element one when an MDG lists both under `stereotypes`.
CONNECTOR_BASE_TYPES = frozenset({
    "Abstraction", "Aggregation", "Assembly", "Association", "Collaboration",
    "Composition", "Connector", "ControlFlow", "Delegate", "Dependency",
    "Deployment", "Extension", "Generalization", "InformationFlow", "Manifest",
    "Nesting", "NoteLink", "ObjectFlow", "Realisation", "Realization",
    "Sequence", "StateFlow", "Substitution", "Usage",
})


def connector_key(stereo: Stereotype, base_type: str) -> str:
    """The census key a connector lands under: stereotype identity + base type.

    Profile-bound -> "<FQName>|<base type>".  Ad hoc -> "<name>|<base type>".
    """
    ident = stereo.fqname if stereo.is_profile_bound else stereo.name
    return f"{ident}|{base_type}"


@dataclass
class ConnectorCensus:
    """The connector result. Every list is deterministically ordered."""

    entities: list[Entity] = field(default_factory=list)
    #: guid -> the keys it landed under. Several when multi-stereotyped.
    placement: dict[str, list[str]] = field(default_factory=dict)
    excluded_ea_internal: Counter = field(default_factory=Counter)
    #: Connectors with NO stereotype, and the same count by base type.
    untyped_guids: set[str] = field(default_factory=set)
    untyped_by_type: Counter = field(default_factory=Counter)
    excluded_guids: set[str] = field(default_factory=set)
    multi_stereotype_guids: set[str] = field(default_factory=set)
    #: stereotype name -> guids, for names that are qualified text with no
    #: FQName. These are also placed as ad hoc, so counts stay whole.
    unbound_qualified: dict[str, set[str]] = field(default_factory=dict)

    @property
    def total_typed(self) -> int:
        return len(self.placement)

    def provenance_split(self) -> dict[str, int]:
        """Stereotype APPLICATIONS by provenance. A multi-stereotype connector
        counts once per stereotype, so the two figures can sum past
        `total_typed`."""
        bound = sum(e.count for e in self.entities if e.is_profile_bound)
        adhoc = sum(e.count for e in self.entities if not e.is_profile_bound)
        return {"profile_bound": bound, "ad_hoc": adhoc}


def census_connectors(
    connectors,
    stereotype_index: dict[str, list[Stereotype]],
    *,
    exclude_ea_internal: bool = True,
) -> ConnectorCensus:
    """Census connectors by resolved stereotype and base type.

    `connectors` are `t_connector` rows needing at least `ea_guid`,
    `Connector_Type` and `Stereotype`. `stereotype_index` comes from
    `build_stereotype_index` over the same `t_xref` rows as for elements.

    As for elements, a connector with no xref entry falls back to the bare
    `Stereotype` column as an ad-hoc application. A connector with no
    stereotype at all is counted by base type in `untyped_by_type`.
    """
    entities: dict[str, Entity] = {}
    census = ConnectorCensus()

    for row in connectors:
        guid = (row.get("ea_guid") or "").strip()
        if not guid:
            continue
        base_type = (row.get("Connector_Type") or "").strip()
        bare = (row.get("Stereotype") or "").strip()

        applied = stereotype_index.get(guid) or ([Stereotype(name=bare)] if bare else [])
        if not applied:
            census.untyped_guids.add(guid)
            census.untyped_by_type[base_type] += 1
            continue
        if len(applied) > 1:
            census.multi_stereotype_guids.add(guid)

        excluded_any = False
        landed: list[str] = []
        for stereo in applied:
            if exclude_ea_internal and (stereo.name in EA_INTERNAL_STEREOTYPES
                                        or stereo.profile in EA_INTERNAL_PROFILES):
                census.excluded_ea_internal[stereo.fqname or stereo.name] += 1
                excluded_any = True
                continue

            key = connector_key(stereo, base_type)
            ent = entities.get(key)
            if ent is None:
                ent = Entity(key=key, stereotype=stereo.name,
                             fqname=stereo.fqname, profile=stereo.profile)
                entities[key] = ent
            ent.guids.add(guid)
            ent.metaclasses[base_type] += 1
            if key not in landed:
                landed.append(key)
            if stereo.is_unbound_qualified:
                census.unbound_qualified.setdefault(stereo.name, set()).add(guid)

        if landed:
            census.placement[guid] = landed
        elif excluded_any:
            census.excluded_guids.add(guid)
        else:
            census.untyped_guids.add(guid)
            census.untyped_by_type[base_type] += 1

    census.entities = sorted(entities.values(), key=lambda e: (-e.count, e.key))
    return census


def connector_guid_of(connectors):
    """A `guid_of` for `tag_coverage` over `t_connectortag` rows.

    `t_connectortag.ElementID` is the CONNECTOR id, not an element id, so the
    rows need the `t_connector` rows to reach a guid. Unknown ids map to "".
    """
    by_id: dict[int, str] = {}
    for c in connectors:
        try:
            by_id[int(c.get("Connector_ID"))] = (c.get("ea_guid") or "").strip()
        except (TypeError, ValueError):
            continue

    def guid_of(row) -> str:
        try:
            return by_id.get(int(row.get("ElementID")), "")
        except (TypeError, ValueError):
            return ""

    return guid_of


# --------------------------------------------------------------------------
# Tag coverage
# --------------------------------------------------------------------------

@dataclass
class TagStat:
    """Coverage for one tag on one entity."""

    tag: str
    present: int = 0        # rows that exist
    populated: int = 0      # rows with a non-empty value
    values: Counter = field(default_factory=Counter)

    def coverage(self, total_elements: int) -> float:
        """Populated / total. NOT present / total.

        EA creates a tagged-value row when a stereotype is applied, whether or
        not anyone fills it in, so a presence metric reports 100% on a tag
        nobody populated. Measured: a stereotype carrying tags on 8 of 8
        elements with 0 of 8 populated.
        """
        return (self.populated / total_elements) if total_elements else 0.0

    @property
    def distinct_values(self) -> int:
        return len(self.values)


def tag_coverage(entity: Entity, property_rows, guid_of) -> list[TagStat]:
    """Per-tag coverage for one entity, counting POPULATED values.

    `property_rows` are `t_objectproperties` rows with `Property` and `Value`,
    or `t_connectortag` rows with `Property` and `VALUE` (see `connector_guid_of`
    for the mapping). `guid_of` maps a row to the owning element guid - a
    callable, because the rows carry `Object_ID` and only the caller knows the
    id-to-guid mapping.

    Returned deterministically: by descending populated count, then tag name.
    """
    stats: dict[str, TagStat] = {}
    for row in property_rows:
        if guid_of(row) not in entity.guids:
            continue
        tag = (row.get("Property") or "").strip()
        if not tag:
            continue
        st = stats.setdefault(tag, TagStat(tag=tag))
        st.present += 1
        value = ((row.get("Value") if "Value" in row else row.get("VALUE")) or "").strip()
        if value:
            st.populated += 1
            st.values[value] += 1
    return sorted(stats.values(), key=lambda s: (-s.populated, s.tag))


def infer_enum_domain(stat: TagStat, *, max_distinct: int = 12,
                      min_repeat: int = 2) -> list[str] | None:
    """Observed values that look like a closed domain, or None.

    Deliberately conservative. Observation can only ever show the values that
    happen to have been used, so an inferred domain is a candidate, never the
    truth - the MDG's declared domain is the truth, and the gap between the two
    is a finding in its own right.

    Returns None when there are too many distinct values, or when every value
    occurs once (which looks like free text, not a domain).
    """
    if not stat.values or stat.distinct_values > max_distinct:
        return None
    if max(stat.values.values()) < min_repeat:
        return None
    return sorted(stat.values)


# --------------------------------------------------------------------------
# Naming
# --------------------------------------------------------------------------

_SPLIT_CAMEL = re.compile(r"(?<=[a-z0-9])(?=[A-Z])")
_NON_WORD = re.compile(r"[^0-9a-zA-Z]+")


def snake_case(text: str) -> str:
    """Lower snake_case, splitting camelCase but not inside an all-caps run.

    Mechanical case-splitting cannot see into an all-caps technology prefix:
    `WBABusinessApplication` splits to `wbabusiness_application`, which is why
    an MDG alias is strongly preferred over deriving a name from the stereotype.
    """
    text = _NON_WORD.sub(" ", text).strip()
    text = _SPLIT_CAMEL.sub(" ", text)
    return "_".join(p.lower() for p in text.split() if p)


def table_name(entity: Entity, taken: set[str], *,
               alias_of=None, strip_prefix: str = "") -> str:
    """A collision-free table name for an entity.

    Preference order: MDG alias, then the stereotype name with an optional
    technology prefix stripped.

    On collision the name is qualified rather than overwritten. Two stereotypes
    resolving to one name silently lost a whole stereotype in a prototype once -
    `WBABusinessService` and `TOGAF::BusinessService` both reduced to
    `business_service` and one overwrote the other.

    `taken` is mutated so repeated calls stay consistent within one run.
    """
    alias = (alias_of(entity) if alias_of else "") or ""
    if alias:
        base = snake_case(alias)
    else:
        name = entity.stereotype
        if strip_prefix and name.startswith(strip_prefix) and len(name) > len(strip_prefix):
            name = name[len(strip_prefix):]
        base = snake_case(name)
    base = base or "unnamed"

    if base not in taken:
        taken.add(base)
        return base

    # Qualify by what actually distinguishes them.
    if entity.profile:
        candidate = f"{snake_case(entity.profile)}_{base}"
    else:
        candidate = f"adhoc_{base}"
    if candidate not in taken:
        taken.add(candidate)
        return candidate

    n = 2
    while f"{candidate}_{n}" in taken:
        n += 1
    final = f"{candidate}_{n}"
    taken.add(final)
    return final


# --------------------------------------------------------------------------
# Declared vs observed
# --------------------------------------------------------------------------

@dataclass
class Drift:
    """One declared-vs-observed finding."""

    kind: str
    subject: str
    detail: str
    #: The elements or connectors a finding is about, for the kinds that name
    #: them. Empty otherwise.
    guids: tuple[str, ...] = ()


#: The six kinds. #5 is the one that matters most - a live value that the
#: declared domain does not allow is a correctness problem, where the others
#: are tidiness.
DRIFT_DECLARED_UNUSED = "stereotype_declared_never_used"
DRIFT_OBSERVED_UNDECLARED = "stereotype_observed_never_declared"
DRIFT_METACLASS_MISMATCH = "metaclass_mismatch"
DRIFT_ENUM_DECLARED_UNUSED = "enum_value_declared_never_used"
DRIFT_ENUM_OBSERVED_UNDECLARED = "enum_value_observed_not_declared"
DRIFT_TAG_OBSERVED_UNDECLARED = "tag_observed_never_declared"
DRIFT_TAG_NEVER_POPULATED = "tag_declared_never_populated"
DRIFT_FOREIGN_LANGUAGE = "stereotype_from_another_language"
DRIFT_PROBABLE_MISASSIGNMENT = "probable_stereotype_misassignment"

#: Data defects rather than gaps to decide. Both are fixed in the repository,
#: not resolved by editing the technology.
DRIFT_ELEMENT_MULTIPLE_DECLARED = "element_multiple_declared_stereotypes"
DRIFT_CONNECTOR_UNBOUND = "connector_stereotype_unbound"
#: A connector carries a stereotype NAME the technology declares, but the
#: application is ad hoc or bound to another language. Name matching alone would
#: count it as the declared stereotype.
DRIFT_CONNECTOR_NAME_NOT_BOUND = "connector_declared_name_not_bound"


# --------------------------------------------------------------------------
# Shape - what an element LOOKS like, independent of what it is labeled
# --------------------------------------------------------------------------
#
# EA ships with every modeling language enabled, so the toolbox offers hundreds
# of similarly-named stereotypes from dozens of technologies. An architect
# reaching for "Application Component" can land on TOGAF's, ArchiMate's or
# UPDM's without noticing, or miss that the repository's own technology defines
# the concept they actually want.
#
# So an observed-but-undeclared stereotype is NOT noise to be filtered out. It
# is frequently the single most useful thing a census finds. Resolving it means
# looking at the SHAPE of the data - the metaclass and, far more tellingly, the
# set of tag NAMES the element carries, because EA creates those rows from the
# stereotype definition - rather than trusting the label.
#
# Measured on the reference fixture: an element labeled `VendorApplication`
# with no profile binding carries 6 of 6 of the technology's base tags and sits
# beside 35 correctly-stereotyped siblings. It is plainly meant to be the
# governed stereotype. By contrast `TOGAF::ApplicationComponent` elements carry
# 9 tags and 0 of those 6 - a genuinely different shape, and a different
# judgment.

@dataclass(frozen=True)
class Shape:
    """What something looks like: its metaclass and the tag names it carries."""

    metaclass: str
    tag_names: frozenset[str]

    def similarity(self, other: "Shape") -> float:
        """Jaccard overlap of tag names. 0.0 when either side carries none.

        Deliberately tag-name-based, not value-based: values vary per element,
        but the set of tag names is a direct fingerprint of the stereotype
        definition EA applied.
        """
        if not self.tag_names or not other.tag_names:
            return 0.0
        inter = self.tag_names & other.tag_names
        union = self.tag_names | other.tag_names
        return len(inter) / len(union) if union else 0.0


@dataclass
class Suggestion:
    """A candidate stereotype for a misassigned element."""

    stereotype: str
    score: float
    shared_tags: int
    metaclass_agrees: bool
    detail: str


def declared_shapes(mdg: dict) -> dict[str, Shape]:
    """The shape each declared stereotype implies, from the technology."""
    out: dict[str, Shape] = {}
    for spec in mdg.get("stereotypes", []):
        name = spec.get("name")
        if not name:
            continue
        tags = frozenset(t["name"] for t in spec.get("tagged_values", []) if t.get("name"))
        out[name] = Shape(metaclass=(spec.get("base_metaclass") or "").strip(),
                          tag_names=tags)
    return out


def observed_shape(entity: Entity, stats: list[TagStat], *,
                   prevalence: float = 0.5) -> Shape:
    """The shape an entity actually has.

    A tag counts toward the shape when it is PRESENT on at least `prevalence`
    of the entity's elements - present, not populated, because an empty tag row
    still testifies to the stereotype that created it. One stray tag on one
    element should not define the shape.
    """
    n = entity.count or 1
    tags = frozenset(s.tag for s in stats if s.present / n >= prevalence)
    return Shape(metaclass=entity.primary_metaclass, tag_names=tags)


def suggest_stereotypes(shape: Shape, declared: dict[str, Shape], *,
                        min_score: float = 0.6, min_shared: int = 2,
                        limit: int = 3) -> list[Suggestion]:
    """Declared stereotypes whose shape this thing resembles, best first.

    Returns nothing when the shape carries no tags - absence of evidence is not
    evidence, and guessing from the metaclass alone would suggest a Component
    stereotype for every Component in the repository.

    `min_shared` guards against matching on one incidental tag name.
    """
    if not shape.tag_names:
        return []
    out: list[Suggestion] = []
    for name, want in declared.items():
        score = shape.similarity(want)
        shared = len(shape.tag_names & want.tag_names)
        if score < min_score or shared < min_shared:
            continue
        agrees = bool(want.metaclass) and want.metaclass == shape.metaclass
        out.append(Suggestion(
            stereotype=name, score=round(score, 3), shared_tags=shared,
            metaclass_agrees=agrees,
            detail=(f"shares {shared} of {len(want.tag_names)} declared tag(s), "
                    f"similarity {score:.2f}, metaclass "
                    f"{'agrees' if agrees else 'differs'} "
                    f"({shape.metaclass} vs declared {want.metaclass or 'unspecified'})"),
        ))
    # Best score first; ties broken by metaclass agreement, then name.
    out.sort(key=lambda s: (-s.score, not s.metaclass_agrees, s.stereotype))
    return out[:limit]


def infer_technology_namespace(census: ElementCensus, declared: set[str]) -> str:
    """Work out which `t_xref` profile namespace belongs to this technology.

    It cannot be taken from the MDG. Three names are typically in play and none
    of them match: a technology id (`WBA`), a display name
    (`WBA (Westbrook Bank Architecture)`) and the FQName namespace
    (`WestbrookBankArchitecture`).

    So infer it from the evidence: the namespace carrying the most stereotypes
    whose names the technology declares. Returns "" when nothing matches.
    """
    votes: Counter = Counter()
    for ent in census.entities:
        if ent.is_profile_bound and ent.stereotype in declared:
            votes[ent.profile] += 1
    return votes.most_common(1)[0][0] if votes else ""


def _tag_drift(census, declared: dict, tag_stats, noun: str) -> list[Drift]:
    """Tag and enum drift for the entities of either census.

    `noun` is the unit the counts are of: "element" or "connector".
    """
    out: list[Drift] = []
    if not tag_stats:
        return out
    for key, stats in tag_stats.items():
        ent = next((e for e in census.entities if e.key == key), None)
        if ent is None or ent.stereotype not in declared:
            continue
        spec = declared[ent.stereotype]
        tag_specs = {t["name"]: t for t in spec.get("tagged_values", []) if t.get("name")}
        for st in stats:
            decl = tag_specs.get(st.tag)
            if decl is None:
                out.append(Drift(DRIFT_TAG_OBSERVED_UNDECLARED,
                                 f"{ent.stereotype}.{st.tag}",
                                 f"populated on {st.populated} {noun}(s), not declared"))
                continue
            domain = [v for v in (decl.get("values") or []) if v]
            if not domain:
                continue
            # A tag nobody filled in is ONE finding, not one per declared
            # value. Emitting per value turned a handful of real findings
            # into 99 and buried them.
            if not st.populated:
                out.append(Drift(DRIFT_TAG_NEVER_POPULATED,
                                 f"{ent.stereotype}.{st.tag}",
                                 f"present on {st.present} {noun}(s), populated on none; "
                                 f"{len(domain)} declared value(s) unused"))
                continue
            used = set(st.values)
            for bad in sorted(used - set(domain)):
                out.append(Drift(DRIFT_ENUM_OBSERVED_UNDECLARED,
                                 f"{ent.stereotype}.{st.tag}",
                                 f"value {bad!r} is used but not in the declared domain"))
            unused = sorted(set(domain) - used)
            if unused:
                out.append(Drift(DRIFT_ENUM_DECLARED_UNUSED,
                                 f"{ent.stereotype}.{st.tag}",
                                 "declared value(s) never used: "
                                 + ", ".join(repr(v) for v in unused)))
    return out


def _multiple_declared(census: ElementCensus, declared: set[str]) -> list[Drift]:
    """Elements carrying two or more DISTINCT declared stereotypes.

    `multi_stereotype_guids` already counts any element with several
    stereotypes, which is mostly benign (a declared one plus a shipped
    language's). Two stereotypes from the declared set is a data error: the
    element lands in both tables of a reporting build. Grouped by combination.
    """
    by_key = {e.key: e for e in census.entities}
    groups: dict[tuple[str, ...], list[str]] = defaultdict(list)
    for guid, keys in census.placement.items():
        names = {by_key[k].stereotype for k in keys
                 if k in by_key and by_key[k].stereotype in declared}
        if len(names) > 1:
            groups[tuple(sorted(names))].append(guid)
    return [
        Drift(DRIFT_ELEMENT_MULTIPLE_DECLARED, " + ".join(combo),
              f"{len(guids)} element(s) carry more than one declared stereotype",
              guids=tuple(sorted(guids)))
        for combo, guids in groups.items()
    ]


def compare_declared_observed(census: ElementCensus, mdg: dict,
                              tag_stats: dict[str, list[TagStat]] | None = None,
                              *, namespace: str | None = None) -> list[Drift]:
    """Compare what the MDG declares against what the repository contains.

    `mdg` is the shape `get_mdg_from_runtime` returns: a `stereotypes` list of
    dicts carrying `name`, `base_metaclass` and `tagged_values`.

    `tag_stats` maps an entity key to its `TagStat` list, so enum and tag drift
    can be reported. Omit it to get stereotype-level drift only.

    Matching is on **stereotype name**, never technology id. Three names are
    typically in play and none of them match each other: the technology id, the
    technology display name, and the `t_xref` FQName namespace.

    Returns findings sorted by kind then subject.
    """
    # Connector stereotypes arrive in the same list; they are compared by
    # `compare_connectors_declared_observed`, and counting them here would
    # report every one as declared-never-used by elements.
    declared = {s["name"]: s for s in mdg.get("stereotypes", []) if s.get("name")
                and (s.get("base_metaclass") or "").strip() not in CONNECTOR_BASE_TYPES}
    out: list[Drift] = []

    # A stereotype NAME can own several entities - profile-bound and ad hoc, or
    # across metaclasses. Collapsing them with {e.stereotype: e} lets the last
    # one win arbitrarily, which reported a metaclass mismatch against 1
    # instance when there were 12. Aggregate instead.
    by_name: dict[str, list[Entity]] = defaultdict(list)
    for ent in census.entities:
        by_name[ent.stereotype].append(ent)

    if namespace is None:
        namespace = infer_technology_namespace(census, set(declared))

    for name, spec in sorted(declared.items()):
        ents = by_name.get(name)
        if not ents:
            out.append(Drift(DRIFT_DECLARED_UNUSED, name,
                             "declared in the technology, no instances in the repository"))
            continue
        want = (spec.get("base_metaclass") or "").strip()
        if not want:
            continue
        combined: Counter = Counter()
        for e in ents:
            combined.update(e.metaclasses)
        if want not in combined:
            got = ", ".join(f"{m} ({n})" for m, n in sorted(combined.items()))
            out.append(Drift(DRIFT_METACLASS_MISMATCH, name,
                             f"declares base_metaclass {want}; instances are {got}"))

    # Every observed-but-undeclared stereotype is reported. NONE is filtered
    # out as noise: EA ships with all its modeling languages enabled, so a
    # stereotype from another technology is very often an architect picking the
    # wrong toolbox item rather than a deliberate second language. Which of the
    # two it is cannot be told from the label - only from the shape of the data.
    shapes = declared_shapes(mdg)
    for name, ents in sorted(by_name.items()):
        if name in declared:
            continue
        total = sum(e.count for e in ents)
        foreign = sorted({e.profile for e in ents if e.is_profile_bound and e.profile != namespace})

        # Best shape evidence across the entities sharing this name.
        best: list[Suggestion] = []
        if tag_stats:
            for e in ents:
                stats = tag_stats.get(e.key)
                if not stats:
                    continue
                for s in suggest_stereotypes(observed_shape(e, stats), shapes):
                    best.append(s)
            best.sort(key=lambda s: (-s.score, s.stereotype))

        if foreign:
            out.append(Drift(
                DRIFT_FOREIGN_LANGUAGE, name,
                f"{total} instance(s) bound to {', '.join(foreign)}, not to "
                f"{namespace or 'this technology'}. EA enables every shipped "
                "language, so verify this was a deliberate choice"))
        else:
            out.append(Drift(DRIFT_OBSERVED_UNDECLARED, name,
                             f"{total} ad-hoc instance(s), bound to no profile"))

        if best:
            top = best[0]
            out.append(Drift(
                DRIFT_PROBABLE_MISASSIGNMENT, name,
                f"{total} instance(s) labeled {name!r} have the shape of "
                f"{top.stereotype!r}: {top.detail}"))

    out.extend(_tag_drift(census, declared, tag_stats, "element"))
    out.extend(_multiple_declared(census, set(declared)))

    return sorted(out, key=lambda d: (d.kind, d.subject, d.detail))


def declared_connector_stereotypes(mdg: dict) -> dict[str, dict]:
    """The connector stereotypes an MDG declares, by name.

    Read from `connector_stereotypes` when the MDG dict has that list; else
    from `stereotypes`, keeping those whose `base_metaclass` is a connector
    type, because a technology lists its connector stereotypes alongside its
    element ones.
    """
    if mdg.get("connector_stereotypes") is not None:
        specs = mdg["connector_stereotypes"]
    else:
        specs = [s for s in mdg.get("stereotypes", [])
                 if (s.get("base_metaclass") or "").strip() in CONNECTOR_BASE_TYPES]
    return {s["name"]: s for s in specs if s.get("name")}


def compare_connectors_declared_observed(
        census: ConnectorCensus, mdg: dict,
        tag_stats: dict[str, list[TagStat]] | None = None,
        *, namespace: str | None = None) -> list[Drift]:
    """Compare the MDG's declared connector stereotypes with the repository.

    The connector counterpart of `compare_declared_observed`, with the same
    finding kinds plus the two connector-specific ones. Findings say
    "connector" in their detail.

    `tag_stats` maps a connector entity key to its `TagStat` list; build it
    with `tag_coverage(entity, tag_rows, connector_guid_of(connectors))`.

    Name matching alone would let a bare `Uses` or a `BMM::Uses` stand in for
    the declared `Uses`, so a declared name carried without a binding to
    `namespace` is reported as `connector_declared_name_not_bound`.

    Returns findings sorted by kind then subject.
    """
    declared = declared_connector_stereotypes(mdg)
    out: list[Drift] = []

    by_name: dict[str, list[Entity]] = defaultdict(list)
    for ent in census.entities:
        by_name[ent.stereotype].append(ent)

    if namespace is None:
        namespace = infer_technology_namespace(census, set(declared))

    for name, spec in sorted(declared.items()):
        ents = by_name.get(name)
        if not ents:
            out.append(Drift(DRIFT_DECLARED_UNUSED, name,
                             "declared in the technology, no connectors in the repository"))
            continue
        loose = [e for e in ents
                 if not e.is_profile_bound or (namespace and e.profile != namespace)]
        if loose:
            adhoc = sum(e.count for e in loose if not e.is_profile_bound)
            other: Counter = Counter()
            for e in loose:
                if e.is_profile_bound:
                    other[e.profile] += e.count
            parts = ([f"{adhoc} ad hoc"] if adhoc else []) + [
                f"{n} bound to {p}" for p, n in sorted(other.items())]
            out.append(Drift(
                DRIFT_CONNECTOR_NAME_NOT_BOUND, name,
                f"{sum(e.count for e in loose)} connector(s) carry the declared name "
                f"without binding to {namespace or 'the technology'}: " + ", ".join(parts),
                guids=tuple(sorted({g for e in loose for g in e.guids}))))
        want = (spec.get("base_metaclass") or "").strip()
        if not want:
            continue
        combined: Counter = Counter()
        for e in ents:
            combined.update(e.metaclasses)
        if want not in combined:
            got = ", ".join(f"{m} ({n})" for m, n in sorted(combined.items()))
            out.append(Drift(DRIFT_METACLASS_MISMATCH, name,
                             f"declares base type {want}; connectors are {got}"))

    for name, ents in sorted(by_name.items()):
        if name in declared or name in census.unbound_qualified:
            continue
        total = sum(e.count for e in ents)
        foreign = sorted({e.profile for e in ents if e.is_profile_bound and e.profile != namespace})
        if foreign:
            out.append(Drift(
                DRIFT_FOREIGN_LANGUAGE, name,
                f"{total} connector(s) bound to {', '.join(foreign)}, not to "
                f"{namespace or 'this technology'}. EA enables every shipped "
                "language, so verify this was a deliberate choice"))
        else:
            out.append(Drift(DRIFT_OBSERVED_UNDECLARED, name,
                             f"{total} ad-hoc connector(s), bound to no profile"))

    # A data defect, reported apart from ordinary ad hoc use: the qualified
    # name was typed into the stereotype field and EA never bound it.
    for name, guids in sorted(census.unbound_qualified.items()):
        out.append(Drift(
            DRIFT_CONNECTOR_UNBOUND, name,
            f"{len(guids)} connector(s) carry the qualified stereotype name {name!r} "
            "with no FQName, so it is bound to no profile",
            guids=tuple(sorted(guids))))

    out.extend(_tag_drift(census, declared, tag_stats, "connector"))
    return sorted(out, key=lambda d: (d.kind, d.subject, d.detail))


# --------------------------------------------------------------------------
# Multi-valued tags
# --------------------------------------------------------------------------

def split_multi_value(value: str, *, separator: str = ",") -> list[str]:
    """Split a multi-valued tag.

    EA stores a multi-valued tag as one joined string, and flattening it into a
    single column breaks aggregation SILENTLY: exact-match counting of a tag
    holding "GLBA" and "GLBA, FFIEC" as distinct values understates by about 2x
    on a real model.

    CAUTION, and the reason this is a separate named function rather than an
    inline `.split(",")`: a naive split corrupts any value that legitimately
    contains the separator. A team name like "Risk, Compliance & Audit" is one
    value, not two, and the MDG's declared type does NOT distinguish the two
    cases - both are declared `String`. Callers must decide per tag whether
    splitting applies; this function does not decide for them.
    """
    if not value:
        return []
    return [p.strip() for p in value.split(separator) if p.strip()]

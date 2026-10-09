#!/usr/bin/env python3
"""The inclusion choice: what a reporting build includes beyond the MDG.

PURE. No repository calls, no COM, no file or network I/O, no clock, no
randomness. It takes the element and connector censuses (`ea_census`), the rows
they were taken from, and the MDG, and returns plain data.

THE QUESTION IT SUPPORTS
------------------------
Before any reporting build the user is asked once:

  1. Only what my MDG defines.
  2. Everything in the repository, keyed by observed stereotype (or base
     metaclass where there is none).
  3. Show me the gaps: per gap, include it as observed, exclude it, or update
     the MDG to declare it.

`analyze` computes what each option would include, by count, and the gap list
for option 3. `resolve_answer` turns the user's answer into the `inclusion`
section of the reporting profile - exactly the shape the server's
`reporting.profile` reads:

    {"observed_elements": "all" | [{"stereotype": ..., "metaclass": ...}, ...],
     "observed_connectors": "all" | ["<connector key>", ...]}

KEYS MUST MATCH THE SERVER
--------------------------
The server decides inclusion with these keys, so this module emits them and
nothing else (`reporting.definition`):

  element    stereotype = the FQName when the stereotype is profile-bound, else
             the stereotype text, "" when there is none; metaclass = the
             element's object type (for a bound stereotype, its most common one).
  connector  the FQName when bound, else the stereotype text, else the base
             type. NOT the census key, which also carries the base type.

TWO DATA DEFECTS ARE NOT GAPS
-----------------------------
  * a connector whose stereotype is qualified text with no FQName binding. The
    preflight STOPS on these; `resolve_answer` refuses to produce a profile
    while any exist.
  * an element carrying two stereotypes the MDG declares. It is flagged, and if
    the user continues it is placed in both tables.

"UPDATE THE MDG" IS A HAND-OFF
------------------------------
Declaring a gap is the MDG skills' job and is followed by a fresh census. Here it
is "not decided yet": `resolve_answer` refuses to produce a profile while any
gap is undecided or marked for an MDG update.

WHAT THE PROFILE CANNOT REMEMBER
--------------------------------
The profile lists only what is included. A gap the user excluded, and the option
chosen, are not in it, so a later refresh could not tell "excluded" from "new".
`InclusionAnswer.record()` returns a small dict to store beside the profile
(the server ignores unknown top-level keys); `new_since_saved` reads it.
"""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field

from ea_census import (
    CONNECTOR_BASE_TYPES,
    ConnectorCensus,
    ElementCensus,
    compare_declared_observed,
    declared_connector_stereotypes,
    DRIFT_ELEMENT_MULTIPLE_DECLARED,
    infer_technology_namespace,
)

ALL = "all"
ELEMENT = "element"
CONNECTOR = "connector"

OPTION_MDG_ONLY = 1
OPTION_EVERYTHING = 2
OPTION_GAPS = 3
OPTION_LABELS = {
    OPTION_MDG_ONLY: "Only what my MDG defines",
    OPTION_EVERYTHING: "Everything in the repository",
    OPTION_GAPS: "Show me the gaps",
}

INCLUDE = "include"
EXCLUDE = "exclude"
UPDATE_MDG = "update_mdg"
UNDECIDED = "undecided"
DECISIONS = (INCLUDE, EXCLUDE, UPDATE_MDG, UNDECIDED)

#: Object types that are diagram furniture, not model content. Mirrors
#: `reporting.definition.NOT_MODEL_CONTENT`: an unstereotyped element of one of
#: these never gets a table, so offering it as a gap would be a question the
#: build then ignores.
NOT_MODEL_CONTENT = frozenset({"Package", "Note", "Text", "Boundary"})

MDG_STEREOTYPE_ADDED = "mdg_stereotype_added"
MDG_STEREOTYPE_REMOVED = "mdg_stereotype_removed"
MDG_VERSION_CHANGED = "mdg_version_changed"
NEW_ELEMENT_KEY = "new_element_key"
NEW_CONNECTOR_KEY = "new_connector_key"


class InclusionError(ValueError):
    pass


# --------------------------------------------------------------------------
# Result types
# --------------------------------------------------------------------------

@dataclass(frozen=True)
class Observed:
    """One key the repository uses, as the server will key it."""

    kind: str                  # ELEMENT or CONNECTOR
    #: Identity for matching: element = FQName or "name|metaclass"; connector =
    #: the profile connector key.
    key: str
    #: Element: FQName if bound, else the stereotype text, "" if none.
    #: Connector: same as `key`.
    stereotype: str
    #: Element: the metaclass. Connector: the base types seen, joined with "/".
    metaclass: str
    bound: bool
    declared: bool
    guids: frozenset
    example: str = ""

    @property
    def id(self) -> str:
        return f"{self.kind}:{self.key}"

    @property
    def count(self) -> int:
        return len(self.guids)


@dataclass(frozen=True)
class Gap:
    """An observed key the MDG does not declare."""

    kind: str
    key: str
    stereotype: str
    metaclass: str
    bound: bool
    count: int
    example: str

    @property
    def id(self) -> str:
        return f"{self.kind}:{self.key}"


@dataclass(frozen=True)
class Defect:
    """A data defect to fix in the repository; never a gap to decide."""

    kind: str
    subject: str
    count: int
    guids: tuple
    advice: str


@dataclass(frozen=True)
class Coverage:
    """What an inclusion would put in the build, by count."""

    declared_element_keys: int
    observed_element_keys: int
    #: Distinct elements; one in two tables counts once.
    elements: int
    declared_connector_keys: int
    observed_connector_keys: int
    connectors: int


@dataclass
class Analysis:
    namespace: str
    declared_elements: tuple
    declared_connectors: tuple
    mdg_version: str
    observed: list = field(default_factory=list)
    unbound_connectors: list = field(default_factory=list)
    multi_stereotyped: list = field(default_factory=list)

    @property
    def gaps(self) -> list:
        return [Gap(o.kind, o.key, o.stereotype, o.metaclass, o.bound, o.count, o.example)
                for o in self.observed if not o.declared]

    @property
    def element_gaps(self) -> list:
        return [g for g in self.gaps if g.kind == ELEMENT]

    @property
    def connector_gaps(self) -> list:
        return [g for g in self.gaps if g.kind == CONNECTOR]

    @property
    def blocked(self) -> bool:
        """True while a connector is bound to no profile: the preflight stops."""
        return bool(self.unbound_connectors)

    @property
    def doubly_stereotyped_elements(self) -> int:
        return len({g for d in self.multi_stereotyped for g in d.guids})

    def coverage(self, observed_elements=(), observed_connectors=()) -> Coverage:
        """What the build would contain for an `inclusion` selection."""
        el = [o for o in self.observed
              if o.kind == ELEMENT and (o.declared or _element_selected(observed_elements, o))]
        cn = [o for o in self.observed
              if o.kind == CONNECTOR and (o.declared or _connector_selected(observed_connectors, o))]
        return Coverage(
            declared_element_keys=sum(1 for o in el if o.declared),
            observed_element_keys=sum(1 for o in el if not o.declared),
            elements=len(set().union(*(o.guids for o in el))) if el else 0,
            declared_connector_keys=sum(1 for o in cn if o.declared),
            observed_connector_keys=sum(1 for o in cn if not o.declared),
            connectors=len(set().union(*(o.guids for o in cn))) if cn else 0,
        )

    def options(self) -> dict:
        """Options 1 and 2 by count. Option 3 lies between them, by the gaps."""
        return {
            OPTION_MDG_ONLY: self.coverage([], []),
            OPTION_EVERYTHING: self.coverage(ALL, ALL),
        }


@dataclass(frozen=True)
class InclusionAnswer:
    option: int
    inclusion: dict
    excluded: tuple
    coverage: Coverage
    declared_elements: tuple
    declared_connectors: tuple
    mdg_version: str

    def record(self) -> dict:
        """What to store beside the profile so a refresh can compare."""
        return {
            "option": self.option,
            "excluded": list(self.excluded),
            "mdg_version": self.mdg_version,
            "declared_elements": list(self.declared_elements),
            "declared_connectors": list(self.declared_connectors),
        }


@dataclass(frozen=True)
class NewItem:
    kind: str
    key: str
    count: int
    example: str
    detail: str


# --------------------------------------------------------------------------
# Selection matching - mirrors reporting.profile.Profile
# --------------------------------------------------------------------------

def _element_selected(selection, o: Observed) -> bool:
    if selection == ALL:
        return True
    return any(e.get("stereotype", "") == o.stereotype and e.get("metaclass", "") == o.metaclass
               for e in selection)


def _connector_selected(selection, o: Observed) -> bool:
    return selection == ALL or o.key in selection


# --------------------------------------------------------------------------
# Analysis
# --------------------------------------------------------------------------

def _example(guids, names: dict) -> str:
    named = sorted((names.get(g, ""), g) for g in guids)
    for name, _ in named:
        if name:
            return name
    return ""


def analyze(element_census: ElementCensus, connector_census: ConnectorCensus, mdg: dict,
            objects, connectors, *, namespace: str | None = None) -> Analysis:
    """Count what each option would include and list the gaps and defects.

    `objects` and `connectors` are the `t_object` / `t_connector` rows the
    censuses were taken from. They are needed for two things the censuses do not
    keep: the metaclass of an unstereotyped element, and a name to show as the
    example for each gap.

    `namespace` is the profile namespace as it appears in `t_xref` FQNames;
    inferred from the censuses when omitted. A stereotype counts as declared
    only when it is bound to that namespace - the same name carried ad hoc, or
    bound to another language, is a gap.
    """
    declared_el = {s["name"] for s in mdg.get("stereotypes", []) if s.get("name")
                   and (s.get("base_metaclass") or "").strip() not in CONNECTOR_BASE_TYPES}
    declared_cn = set(declared_connector_stereotypes(mdg))
    if namespace is None:
        namespace = (infer_technology_namespace(element_census, declared_el)
                     or infer_technology_namespace(connector_census, declared_cn))

    el_names = {(r.get("ea_guid") or "").strip(): (r.get("Name") or "") for r in objects}
    cn_names = {(r.get("ea_guid") or "").strip(): (r.get("Name") or "") for r in connectors}

    observed: list[Observed] = []

    for ent in element_census.entities:
        is_declared = ent.is_profile_bound and ent.profile == namespace and ent.stereotype in declared_el
        observed.append(Observed(
            kind=ELEMENT, key=ent.key,
            stereotype=ent.fqname if ent.is_profile_bound else ent.stereotype,
            metaclass=ent.primary_metaclass, bound=ent.is_profile_bound, declared=is_declared,
            guids=frozenset(ent.guids), example=_example(ent.guids, el_names)))

    untyped_el: dict[str, set] = defaultdict(set)
    for row in objects:
        guid = (row.get("ea_guid") or "").strip()
        metaclass = (row.get("Object_Type") or "").strip()
        if guid in element_census.untyped_guids and metaclass not in NOT_MODEL_CONTENT:
            untyped_el[metaclass].add(guid)
    for metaclass, guids in untyped_el.items():
        observed.append(Observed(kind=ELEMENT, key=f"|{metaclass}", stereotype="", metaclass=metaclass,
                                 bound=False, declared=False, guids=frozenset(guids),
                                 example=_example(guids, el_names)))

    unbound_names = set(connector_census.unbound_qualified)
    grouped: dict[str, dict] = {}
    for ent in connector_census.entities:
        if not ent.is_profile_bound and ent.stereotype in unbound_names:
            continue  # a data defect, reported apart; the build stops on it
        pkey = ent.fqname if ent.is_profile_bound else ent.stereotype
        g = grouped.setdefault(pkey, {"guids": set(), "types": set(), "bound": ent.is_profile_bound,
                                      "declared": ent.is_profile_bound and ent.profile == namespace
                                      and ent.stereotype in declared_cn})
        g["guids"] |= ent.guids
        g["types"] |= set(ent.metaclasses)
    for pkey, g in grouped.items():
        observed.append(Observed(kind=CONNECTOR, key=pkey, stereotype=pkey,
                                 metaclass="/".join(sorted(g["types"])), bound=g["bound"],
                                 declared=g["declared"], guids=frozenset(g["guids"]),
                                 example=_example(g["guids"], cn_names)))

    untyped_cn: dict[str, set] = defaultdict(set)
    for row in connectors:
        guid = (row.get("ea_guid") or "").strip()
        if guid in connector_census.untyped_guids:
            untyped_cn[(row.get("Connector_Type") or "").strip()].add(guid)
    for base_type, guids in untyped_cn.items():
        observed.append(Observed(kind=CONNECTOR, key=base_type, stereotype=base_type, metaclass=base_type,
                                 bound=False, declared=False, guids=frozenset(guids),
                                 example=_example(guids, cn_names)))

    observed.sort(key=lambda o: (o.kind, -o.count, o.key))

    declared_fq = {n: f"{namespace}::{n}" if namespace else n for n in declared_cn}
    unbound = []
    for name, guids in sorted(connector_census.unbound_qualified.items()):
        tail = name.rsplit("::", 1)[-1]
        if tail in declared_fq:
            advice = (f"Bind them to the MDG's own stereotype: update_connector with StereotypeEx "
                      f"'{declared_fq[tail]}' (take a baseline first). Or clear StereotypeEx if no "
                      "stereotype was meant.")
        else:
            advice = ("The MDG declares no connector stereotype by that name. Clear StereotypeEx "
                      "(update_connector, StereotypeEx '') or have the MDG declare it, then re-run "
                      "the census. Take a baseline first.")
        unbound.append(Defect("connector_stereotype_unbound", name, len(guids),
                              tuple(sorted(guids)), advice))

    multi = [Defect(d.kind, d.subject, len(d.guids), d.guids,
                    "Remove one stereotype in EA, or continue and the element is placed in both tables.")
             for d in compare_declared_observed(element_census, mdg, namespace=namespace)
             if d.kind == DRIFT_ELEMENT_MULTIPLE_DECLARED]

    return Analysis(namespace=namespace, declared_elements=tuple(sorted(declared_el)),
                    declared_connectors=tuple(sorted(declared_cn)),
                    mdg_version=str(mdg.get("version") or ""),
                    observed=observed, unbound_connectors=unbound, multi_stereotyped=multi)


# --------------------------------------------------------------------------
# The answer
# --------------------------------------------------------------------------

def resolve_answer(analysis: Analysis, option: int, decisions: dict | None = None, *,
                   continue_with_double_stereotypes: bool = False) -> InclusionAnswer:
    """Turn the user's answer into the profile's `inclusion` section.

    `option` is 1, 2 or 3. For 3, `decisions` maps each `Gap.id` to INCLUDE or
    EXCLUDE. A gap that is missing, UNDECIDED, or UPDATE_MDG is not decided:
    declaring it is the MDG skills' job and the census reruns afterwards, so no
    profile is produced until it is gone.

    Refuses (InclusionError) while a connector is bound to no profile, and while
    elements carry two declared stereotypes unless the user chose to continue.
    """
    if option not in OPTION_LABELS:
        raise InclusionError(f"option must be 1, 2 or 3, not {option!r}")
    if analysis.blocked:
        names = ", ".join(d.subject for d in analysis.unbound_connectors)
        raise InclusionError("connectors carry a qualified stereotype bound to no profile "
                             f"({names}); fix them in the repository and re-run the census")
    if analysis.multi_stereotyped and not continue_with_double_stereotypes:
        n = analysis.doubly_stereotyped_elements
        raise InclusionError(f"{n} element(s) carry two declared stereotypes; fix them, or continue "
                             "knowing they are placed in both tables")

    excluded: list[str] = []
    if option == OPTION_MDG_ONLY:
        inclusion = {"observed_elements": [], "observed_connectors": []}
    elif option == OPTION_EVERYTHING:
        inclusion = {"observed_elements": ALL, "observed_connectors": ALL}
    else:
        decisions = dict(decisions or {})
        gaps = {g.id: g for g in analysis.gaps}
        unknown = sorted(set(decisions) - set(gaps))
        if unknown:
            raise InclusionError("not a gap in this census: " + ", ".join(unknown))
        bad = sorted(f"{k}={v!r}" for k, v in decisions.items() if v not in DECISIONS)
        if bad:
            raise InclusionError("a decision must be one of " + ", ".join(DECISIONS) + ": " + ", ".join(bad))
        pending = sorted(i for i in gaps if decisions.get(i, UNDECIDED) in (UNDECIDED, UPDATE_MDG))
        if pending:
            raise InclusionError(
                f"{len(pending)} gap(s) not decided; 'update the MDG' is a hand-off to the MDG skills "
                "followed by a fresh census: " + ", ".join(pending))
        elements, conns = [], []
        for gid, gap in sorted(gaps.items()):
            if decisions[gid] == EXCLUDE:
                excluded.append(gid)
            elif gap.kind == ELEMENT:
                elements.append({"stereotype": gap.stereotype, "metaclass": gap.metaclass})
            else:
                conns.append(gap.key)
        elements.sort(key=lambda e: (e["stereotype"], e["metaclass"]))
        inclusion = {"observed_elements": elements, "observed_connectors": sorted(conns)}

    return InclusionAnswer(
        option=option, inclusion=inclusion, excluded=tuple(excluded),
        coverage=analysis.coverage(inclusion["observed_elements"], inclusion["observed_connectors"]),
        declared_elements=analysis.declared_elements, declared_connectors=analysis.declared_connectors,
        mdg_version=analysis.mdg_version)


# --------------------------------------------------------------------------
# Refresh
# --------------------------------------------------------------------------

def new_since_saved(analysis: Analysis, inclusion: dict, choice: dict | None = None) -> list:
    """What a fresh census shows that the saved choice does not cover.

    `inclusion` is the profile's saved section; `choice` is the dict
    `InclusionAnswer.record()` returned. Returns `NewItem`s for the caller to
    FLAG - nothing here decides.

    * A key counts as new when it is a gap, is not in the saved lists, and was
      not excluded. Option 2 ("all") covers every key; option 1 is a deliberate
      "MDG only", so keys outside the MDG are not new.
    * An MDG change (a declared stereotype added or removed, or a different
      version) is reported when the record holds what the MDG declared then.

    Without `choice` the option is inferred: both sides "all" is option 2,
    anything else is option 3, and every unlisted gap is then reported.
    """
    choice = choice or {}
    option = choice.get("option") or (OPTION_EVERYTHING if inclusion.get("observed_elements") == ALL
                                      and inclusion.get("observed_connectors") == ALL else OPTION_GAPS)
    excluded = set(choice.get("excluded") or ())
    out: list[NewItem] = []

    if option != OPTION_MDG_ONLY:
        for o in analysis.observed:
            if o.declared or o.id in excluded:
                continue
            if o.kind == ELEMENT:
                covered = _element_selected(inclusion.get("observed_elements") or [], o)
                kind = NEW_ELEMENT_KEY
            else:
                covered = _connector_selected(inclusion.get("observed_connectors") or [], o)
                kind = NEW_CONNECTOR_KEY
            if not covered:
                out.append(NewItem(kind, o.key, o.count, o.example,
                                   f"{o.count} {o.kind}(s) not covered by the saved choice"))

    for label, now, then in (("element", analysis.declared_elements, choice.get("declared_elements")),
                             ("connector", analysis.declared_connectors, choice.get("declared_connectors"))):
        if then is None:
            continue
        for name in sorted(set(now) - set(then)):
            out.append(NewItem(MDG_STEREOTYPE_ADDED, name, 0, "", f"the MDG now declares {label} stereotype {name!r}"))
        for name in sorted(set(then) - set(now)):
            out.append(NewItem(MDG_STEREOTYPE_REMOVED, name, 0, "", f"the MDG no longer declares {label} stereotype {name!r}"))
    saved_version = choice.get("mdg_version")
    if saved_version and analysis.mdg_version and saved_version != analysis.mdg_version:
        out.append(NewItem(MDG_VERSION_CHANGED, analysis.mdg_version, 0, "",
                           f"the MDG was {saved_version} when the choice was made, now {analysis.mdg_version}"))
    return out

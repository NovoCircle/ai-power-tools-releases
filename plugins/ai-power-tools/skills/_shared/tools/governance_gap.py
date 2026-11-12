#!/usr/bin/env python3
"""Elements that would be left out of the reporting database, and what to do.

PURE. No repository calls, no COM, no file or network I/O, no clock, no
randomness. It takes rows already extracted plus the technology's declared
shapes and returns findings; applying anything to a model is the caller's job.

WHY THIS EXISTS
---------------
An element that the inclusion choice leaves without a table is simply absent
from the reporting database, and nothing tells the customer. On the reference
model, three Components carry the complete governance tag set - criticality
Business-Critical, regulatoryScope GLBA, both owners, data classification - and
no stereotype at all. Under "only what my MDG defines" that is a
Business-Critical, GLBA-scoped platform that no report can see.

So the build asks BEFORE it generates, not after. "Ungoverned" is defined by the
saved inclusion choice, not by an empty stereotype: an unstereotyped element is
ungoverned under option 1 but has a table under option 2, and an ad hoc
stereotype the choice excludes leaves its element ungoverned too.

WHAT THIS MODULE REFUSES TO DO
------------------------------
Rank candidates it cannot tell apart. On the reference technology (WBA 1.1.1) ten of
the fifteen element stereotypes declare an identical six-tag set, so tag overlap
cannot separate them. Returning the alphabetically-first one dressed as a
recommendation would be a guess wearing a number.

Four outcomes, kept distinct on purpose:

  NO_CANDIDATE      the technology extends no stereotype for this metaclass, so
                    there is nothing to apply. The answer is to extend the
                    technology - which is R1's job - or to accept the exclusion.
                    Never a suggestion.
  RANKED            one candidate is backed by package evidence the others lack,
                    and the evidence is stated with it.
  SINGLE_CANDIDATE  exactly one stereotype could be applied and nothing in the
                    repository confirms it: "one candidate, not confirmed". It
                    is named, never ranked.
  UNRANKABLE        several candidates and nothing distinguishes them, or the
                    element carries tags that rule every candidate out. List
                    them (if any), refuse to order them, let the customer choose.

This follows the toolchain's rule for suggestions: "a CANDIDATE list, never an
instruction."

THE SIGNALS
-----------
1. Base metaclass. A hard filter, not a tiebreak. It eliminates every candidate
   for a Requirement and narrows a Component to seven.
2. Tag fit. A VETO only: a stereotype is ruled out when the element carries a
   tag the stereotype does not declare. It never ranks: a stereotype that
   declares more tags than the element carries is not demoted for it.
3. Package locality. What stereotype do this element's stereotyped neighbors
   carry? Among the candidates the veto leaves, it is the only signal that
   ranks. It decided the three real cases on the reference model, where three
   siblings in the same package were all `WBAVendorSystem`.
"""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field

from ea_census import Shape, Suggestion
from inclusion import ALL, NOT_MODEL_CONTENT

#: The outcome classes. Conflating them is the failure mode this module exists
#: to avoid, so they are named rather than implied by an empty list.
NO_CANDIDATE = "no_candidate"
RANKED = "ranked"
SINGLE_CANDIDATE = "single_candidate"
UNRANKABLE = "unrankable"


@dataclass(frozen=True)
class UngovernedElement:
    """One in-scope element the inclusion choice leaves without a table."""

    ea_guid: str
    name: str
    metaclass: str
    package_id: int = 0
    package_path: str = ""
    tag_names: frozenset[str] = frozenset()
    populated_tags: int = 0
    #: "" when the element carries none; else an ad hoc stereotype the choice excludes.
    stereotype: str = ""

    @property
    def is_governed(self) -> bool:
        """Carries governance data despite having no table.

        This is the dangerous case and the one to lead with. An untagged,
        unstereotyped element is merely undrawn; a tagged one is data somebody
        entered deliberately that no report will ever show.
        """
        return self.populated_tags > 0


@dataclass
class GapFinding:
    """One ungoverned element, classified, with the reason stated."""

    element: UngovernedElement
    outcome: str
    candidates: list[Suggestion] = field(default_factory=list)
    reason: str = ""

    @property
    def suggestion(self) -> str:
        """The stereotype to offer as ranked, or "" when there is not one.

        Only a RANKED finding has one, and a RANKED finding always has at least
        one candidate (the leader, listed first).
        """
        return self.candidates[0].stereotype if self.outcome == RANKED and self.candidates else ""


def _stereotype_tail(text: str) -> str:
    return text.rsplit("::", 1)[-1]


def _has_table(stereotype: str, metaclass: str, declared: frozenset[str], inclusion: dict) -> bool:
    """Does the build give this element a table under the inclusion choice?

    Mirrors the server: the technology's own element stereotypes always have a
    table; anything else has one only when `inclusion` admits its
    (stereotype, metaclass) key. Names compare without case, and a bound
    foreign stereotype is saved qualified (`BMM::Goal`) while the row carries
    the bare name, so the part after `::` is compared.
    """
    observed = inclusion.get("observed_elements")
    if stereotype:
        if stereotype.casefold() in declared:
            return True
    elif metaclass in NOT_MODEL_CONTENT:
        return False                       # diagram furniture never gets a table
    if observed == ALL:
        return True
    return any(_stereotype_tail((e.get("stereotype") or "")).casefold() == stereotype.casefold()
               and (e.get("metaclass") or "").casefold() == metaclass.casefold()
               for e in observed or ())


def find_ungoverned(element_rows, tag_rows, *, inclusion: dict, declared,
                    skip_metaclasses: frozenset[str] = NOT_MODEL_CONTENT
                    ) -> list[UngovernedElement]:
    """In-scope elements the saved inclusion choice leaves without a table.

    `inclusion` is the profile's `inclusion` section (`resolve_answer(...).inclusion`):
    option 1 is two empty lists, option 2 is `"all"` twice. `declared` is the
    technology's element stereotype names (the keys of `declared_shapes(mdg)`).

    So: under option 1 the unstereotyped elements are listed, and so is any
    element carrying a stereotype the technology does not declare; under option
    2 neither is; under option 3 only those the user did not include.

    `element_rows` are mappings with `ea_guid`, `name`, `metaclass`,
    `stereotype`, `package_id` and optionally `package_path`; `tag_rows` are
    mappings with `ea_guid`, `tag` and `value`.

    Diagram furniture (`Package`, `Note`, `Text`, `Boundary`) is skipped by
    default: it is never model content and never gets a table, so listing it
    would alarm the reader for nothing. EA also stores every package twice -
    once in the package tree and once as an object so it can sit on a diagram.
    """
    declared = frozenset(d.casefold() for d in declared)
    names: dict[str, set[str]] = {}
    populated: Counter = Counter()
    for r in tag_rows:
        guid = r["ea_guid"]
        names.setdefault(guid, set()).add(r["tag"])
        if (r.get("value") or "").strip():
            populated[guid] += 1

    out = []
    for r in element_rows:
        stereotype = (r.get("stereotype") or "").strip()
        metaclass = (r.get("metaclass") or "").strip()
        if metaclass in skip_metaclasses:
            continue
        if _has_table(stereotype, metaclass, declared, inclusion):
            continue
        guid = r["ea_guid"]
        out.append(UngovernedElement(
            ea_guid=guid,
            name=(r.get("name") or "").strip(),
            metaclass=metaclass,
            package_id=int(r.get("package_id") or 0),
            package_path=(r.get("package_path") or ""),
            tag_names=frozenset(names.get(guid, ())),
            populated_tags=populated.get(guid, 0),
            stereotype=stereotype,
        ))
    # Governed first - they are the ones that cost something - then by name so
    # two runs over one repository produce identical output.
    out.sort(key=lambda e: (not e.is_governed, e.metaclass, e.name, e.ea_guid))
    return out


def locality_votes(element_rows, *, package_id: int) -> Counter:
    """What stereotypes this element's stereotyped neighbors carry.

    The signal that actually decided the real cases on the reference model. It
    holds only where a repository is organized by type; a flat or
    domain-organized one will produce few votes, which correctly yields an
    UNRANKABLE or SINGLE_CANDIDATE outcome rather than a weak suggestion.
    """
    votes: Counter = Counter()
    for r in element_rows:
        if int(r.get("package_id") or 0) != package_id:
            continue
        stereo = (r.get("stereotype") or "").strip()
        if stereo:
            votes[stereo] += 1
    return votes


def assess(ungoverned: list[UngovernedElement], declared: dict[str, Shape],
           element_rows, *, min_votes: int = 1) -> list[GapFinding]:
    """Classify each ungoverned element into one of the four outcomes."""
    by_package: dict[int, Counter] = {}
    findings = []

    for el in ungoverned:
        # 1. Base metaclass: a hard filter. A stereotype that extends Component
        #    cannot be applied to a Node, so an unmatched metaclass leaves
        #    nothing to suggest and saying so is the useful answer.
        cands = {n: s for n, s in declared.items()
                 if s.metaclass and s.metaclass == el.metaclass}
        if not cands:
            extended = sorted({s.metaclass for s in declared.values() if s.metaclass})
            findings.append(GapFinding(
                element=el, outcome=NO_CANDIDATE, candidates=[],
                reason=(f"the technology extends no stereotype for metaclass "
                        f"{el.metaclass!r} (it extends: {', '.join(extended) or 'nothing'}). "
                        f"Generate or extend the technology, or accept the exclusion."),
            ))
            continue

        # 2. Tag fit is a veto and nothing else: a stereotype is ruled out when
        #    the element carries a tag it never declares. A stereotype that
        #    declares more tags than the element carries stays in.
        survivors = {n: s for n, s in cands.items() if el.tag_names <= s.tag_names}
        if not survivors:
            findings.append(GapFinding(
                element=el, outcome=UNRANKABLE, candidates=[],
                reason=(f"the element carries tagged values that none of the "
                        f"{len(cands)} stereotype(s) extending metaclass "
                        f"{el.metaclass} declares, so none can be offered. "
                        f"Extend the technology, or accept the exclusion."),
            ))
            continue

        # 3. Package locality ranks the survivors, and only when one holds it alone.
        if el.package_id not in by_package:
            by_package[el.package_id] = locality_votes(element_rows,
                                                       package_id=el.package_id)
        votes = by_package[el.package_id]
        ordered = sorted(survivors.items(), key=lambda kv: (-votes.get(kv[0], 0), kv[0]))
        suggestions = [
            Suggestion(stereotype=name, score=float(votes.get(name, 0)),
                       shared_tags=len(el.tag_names & want.tag_names),
                       metaclass_agrees=True,
                       detail=_detail(votes.get(name, 0), el, want))
            for name, want in ordered
        ]
        best_votes = votes.get(ordered[0][0], 0)
        leaders = [n for n, _ in ordered if votes.get(n, 0) == best_votes]

        if len(leaders) == 1 and best_votes >= min_votes:
            findings.append(GapFinding(
                element=el, outcome=RANKED, candidates=suggestions,
                reason=(f"{best_votes} stereotyped element(s) in the same package carry "
                        f"{leaders[0]!r}, and no other candidate for metaclass "
                        f"{el.metaclass} is backed by that evidence."),
            ))
        elif len(survivors) == 1:
            findings.append(GapFinding(
                element=el, outcome=SINGLE_CANDIDATE, candidates=suggestions,
                reason=(f"one candidate, not confirmed: {ordered[0][0]!r} is the only "
                        f"stereotype extending metaclass {el.metaclass} that the "
                        f"element's tags allow, and nothing in its package confirms "
                        f"it. Apply it if it fits, or accept the exclusion."),
            ))
        else:
            findings.append(GapFinding(
                element=el, outcome=UNRANKABLE, candidates=suggestions,
                reason=(f"{len(suggestions)} stereotype(s) extend metaclass "
                        f"{el.metaclass} and nothing in the repository "
                        f"distinguishes them"
                        + ("" if el.tag_names else
                           " (the element carries no tagged values either)")
                        + ". Choose one, or accept the exclusion."),
            ))
    return findings


def _detail(votes: int, el: UngovernedElement, want: Shape) -> str:
    bits = [f"extends {el.metaclass}"]
    if votes:
        bits.append(f"{votes} sibling(s) in the same package carry it")
    if el.tag_names:
        bits.append(f"declares {len(want.tag_names)} tag(s); the element carries "
                    f"{len(el.tag_names & want.tag_names)} of them")
    return "; ".join(bits)


def summarize(findings: list[GapFinding]) -> dict[str, int]:
    counts = Counter(f.outcome for f in findings)
    return {
        "total": len(findings),
        "governed": sum(1 for f in findings if f.element.is_governed),
        NO_CANDIDATE: counts.get(NO_CANDIDATE, 0),
        RANKED: counts.get(RANKED, 0),
        SINGLE_CANDIDATE: counts.get(SINGLE_CANDIDATE, 0),
        UNRANKABLE: counts.get(UNRANKABLE, 0),
    }


def format_report(findings: list[GapFinding], *, limit_candidates: int = 5) -> str:
    """The text a customer reads BEFORE the database is generated.

    `findings` must come from `find_ungoverned` with the saved inclusion choice,
    so every element listed is one the choice leaves without a table.
    """
    if not findings:
        return ("No ungoverned elements. Every in-scope element has a table under "
                "the inclusion choice and will appear in the reporting database.")
    s = summarize(findings)
    lines = [
        f"{s['total']} element(s) have no table under the inclusion choice and will "
        f"NOT appear in the reporting database.",
        f"  {s['governed']} of them carry governance tagged values already.",
        f"  {s[RANKED]} have a suggested stereotype, {s[SINGLE_CANDIDATE]} have one "
        f"candidate not confirmed, {s[UNRANKABLE]} need a choice, "
        f"{s[NO_CANDIDATE]} cannot be stereotyped by this technology.",
        "",
    ]
    for f in findings:
        el = f.element
        flag = "  [GOVERNED] " if el.is_governed else "  "
        lines.append(f"{flag}{el.name}  ({el.metaclass})")
        if el.stereotype:
            lines.append(f"      carries : {el.stereotype} (not in the technology; "
                         f"the inclusion choice leaves it out)")
        if el.package_path:
            lines.append(f"      package : {el.package_path}")
        if el.tag_names:
            lines.append(f"      tags    : {', '.join(sorted(el.tag_names))}")
        if f.outcome == RANKED:
            lines.append(f"      SUGGEST : {f.suggestion}")
        elif f.outcome == SINGLE_CANDIDATE:
            lines.append(f"      ONE CANDIDATE, NOT CONFIRMED : {f.candidates[0].stereotype}")
        elif f.outcome == UNRANKABLE:
            lines.append("      CHOOSE  : "
                         + (", ".join(c.stereotype for c in f.candidates[:limit_candidates])
                            or "(no stereotype fits its tags)"))
        else:
            lines.append("      NO STEREOTYPE AVAILABLE")
        lines.append(f"      why     : {f.reason}")
        lines.append("")
    lines.append("Apply a stereotype to any of these and it joins the reporting "
                 "database. Decline and it stays out - which is a valid answer, "
                 "but it will not be in any report.")
    return "\n".join(lines)

#!/usr/bin/env python3
"""Elements that would be left out of the reporting database, and what to do.

PURE. No repository calls, no COM, no file or network I/O, no clock, no
randomness. It takes rows already extracted plus the technology's declared
shapes and returns findings; applying anything to a model is the caller's job.

WHY THIS EXISTS
---------------
An element with no stereotype lands in no entity table. Once the database is
restricted to logical business objects (APT-2026-0226) it is simply absent, and
nothing tells the customer. Measured on the reference model, three Components
carry the complete governance tag set - criticality Business-Critical,
regulatoryScope GLBA, both owners, data classification - and no stereotype at
all. A Business-Critical, GLBA-scoped platform that no report can see.

So the build asks BEFORE it generates, not after.

WHAT THIS MODULE REFUSES TO DO
------------------------------
Rank candidates it cannot tell apart. On the reference technology (WBA 1.1.1) ten of
the fifteen element stereotypes declare an identical six-tag set, so for an element
carrying exactly those six tags, tag overlap scores three of the seven Component
stereotypes at exactly 1.0. Returning the
alphabetically-first one dressed as a recommendation would be a guess wearing a
number.

Three outcomes, kept distinct on purpose:

  NO_CANDIDATE  the technology extends no stereotype for this metaclass, so
                there is nothing to apply. Ten Requirements on the reference model.
                The answer is to extend the technology - which is R1's job - or
                to accept the exclusion. Never a suggestion.
  RANKED        one candidate is backed by evidence the others lack, and the
                evidence is stated with it.
  UNRANKABLE    candidates exist and nothing distinguishes them. List them,
                refuse to order them, let the customer choose.

This follows the toolchain's rule for suggestions: "a CANDIDATE list, never an
instruction."

THE SIGNALS, IN THE ORDER THEY DISCRIMINATE
-------------------------------------------
1. Base metaclass. A hard filter, not a tiebreak. It eliminates every candidate
   for a Requirement and narrows a Component to seven.
2. Package locality. What stereotype do this element's stereotyped neighbors
   carry? This is what decided the three real cases on the reference model under
   WBA 1.0, where three siblings in the same package were all the same stereotype.
   Under 1.1.1 it does not: `WBAVendorSystem` declares nine tags and so scores below
   four other Component candidates on tag fit, and `assess` ranks only a candidate
   that leads on both signals, so those three come out UNRANKABLE.
3. Tag signature. Weak as a discriminator because the declared sets collide, but
   it does one useful job: an element carrying only the common tags should not
   be offered a stereotype that declares four more it does not have.
"""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field

from ea_census import Shape, Suggestion

#: The three outcome classes. Conflating them is the failure mode this module
#: exists to avoid, so they are named rather than implied by an empty list.
NO_CANDIDATE = "no_candidate"
RANKED = "ranked"
UNRANKABLE = "unrankable"


@dataclass(frozen=True)
class UngovernedElement:
    """One in-scope element carrying no stereotype."""

    ea_guid: str
    name: str
    metaclass: str
    package_id: int = 0
    package_path: str = ""
    tag_names: frozenset[str] = frozenset()
    populated_tags: int = 0

    @property
    def is_governed(self) -> bool:
        """Carries governance data despite carrying no stereotype.

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
        """The single stereotype to apply, or "" when there is not one."""
        return self.candidates[0].stereotype if self.outcome == RANKED else ""


def find_ungoverned(element_rows, tag_rows, *,
                    skip_metaclasses: frozenset[str] = frozenset({"Package"})
                    ) -> list[UngovernedElement]:
    """In-scope elements carrying no stereotype, with the tags they do carry.

    `element_rows` are mappings with `ea_guid`, `name`, `metaclass`,
    `stereotype`, `package_id` and optionally `package_path`; `tag_rows` are
    mappings with `ea_guid`, `tag` and `value`.

    Packages are skipped by default. EA stores every package twice - once in the
    package tree and once as an object so it can sit on a diagram - and the
    object twin is not something anybody stereotypes (APT-2026-0226).
    """
    names: dict[str, set[str]] = {}
    populated: Counter = Counter()
    for r in tag_rows:
        guid = r["ea_guid"]
        names.setdefault(guid, set()).add(r["tag"])
        if (r.get("value") or "").strip():
            populated[guid] += 1

    out = []
    for r in element_rows:
        if (r.get("stereotype") or "").strip():
            continue
        metaclass = (r.get("metaclass") or "").strip()
        if metaclass in skip_metaclasses:
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
    UNRANKABLE outcome rather than a weak suggestion.
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
    """Classify each ungoverned element into one of the three outcomes."""
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

        if el.package_id not in by_package:
            by_package[el.package_id] = locality_votes(element_rows,
                                                       package_id=el.package_id)
        votes = by_package[el.package_id]

        scored = []
        for name, want in cands.items():
            # 3. Tag signature. Only discriminates downward: an element holding
            #    just the common tags should not be offered a stereotype that
            #    declares four more it does not have.
            fit = 0.0
            if el.tag_names and want.tag_names:
                if el.tag_names <= want.tag_names:
                    fit = len(el.tag_names) / len(want.tag_names)
                else:
                    fit = -1.0        # carries tags this stereotype never declares
            scored.append((votes.get(name, 0), fit, name, want))

        best_votes = max(s[0] for s in scored)
        best_fit = max(s[1] for s in scored)
        # 2. Package locality decides, and only when one candidate holds it
        #    alone. Tag fit breaks a tie underneath it.
        leaders = [s for s in scored if s[0] == best_votes and s[1] == best_fit]

        suggestions = [
            Suggestion(stereotype=name, score=round(fit, 3),
                       shared_tags=len(el.tag_names & want.tag_names),
                       metaclass_agrees=True,
                       detail=_detail(v, fit, el, want))
            for v, fit, name, want in sorted(scored, key=lambda s: (-s[0], -s[1], s[2]))
            if fit >= 0.0
        ]

        if len(leaders) == 1 and best_votes >= min_votes:
            v, fit, name, want = leaders[0]
            findings.append(GapFinding(
                element=el, outcome=RANKED, candidates=suggestions,
                reason=(f"{v} stereotyped element(s) in the same package carry "
                        f"{name!r}, and no other candidate for metaclass "
                        f"{el.metaclass} is backed by that evidence."),
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


def _detail(votes: int, fit: float, el: UngovernedElement, want: Shape) -> str:
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
        UNRANKABLE: counts.get(UNRANKABLE, 0),
    }


def format_report(findings: list[GapFinding], *, limit_candidates: int = 5) -> str:
    """The text a customer reads BEFORE the database is generated."""
    if not findings:
        return ("No ungoverned elements. Every in-scope element carries a "
                "stereotype and will appear in the reporting database.")
    s = summarize(findings)
    lines = [
        f"{s['total']} element(s) carry no stereotype and will NOT appear in the "
        f"reporting database.",
        f"  {s['governed']} of them carry governance tagged values already.",
        f"  {s[RANKED]} have a suggested stereotype, {s[UNRANKABLE]} need a choice, "
        f"{s[NO_CANDIDATE]} cannot be stereotyped by this technology.",
        "",
    ]
    for f in findings:
        el = f.element
        flag = "  [GOVERNED] " if el.is_governed else "  "
        lines.append(f"{flag}{el.name}  ({el.metaclass})")
        if el.package_path:
            lines.append(f"      package : {el.package_path}")
        if el.tag_names:
            lines.append(f"      tags    : {', '.join(sorted(el.tag_names))}")
        if f.outcome == RANKED:
            lines.append(f"      SUGGEST : {f.suggestion}")
        elif f.outcome == UNRANKABLE:
            lines.append("      CHOOSE  : "
                         + ", ".join(c.stereotype
                                     for c in f.candidates[:limit_candidates]))
        else:
            lines.append("      NO STEREOTYPE AVAILABLE")
        lines.append(f"      why     : {f.reason}")
        lines.append("")
    lines.append("Apply a stereotype to any of these and it joins the reporting "
                 "database. Decline and it stays out - which is a valid answer, "
                 "but it will not be in any report.")
    return "\n".join(lines)

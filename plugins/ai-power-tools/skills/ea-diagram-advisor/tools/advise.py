#!/usr/bin/env python3
"""Recommend a diagram type from measured content, and show the reasoning.

A user says what they want to understand. They should not have to know which
of dozens of diagram types across several modeling languages expresses it.

This module is the arithmetic of that choice. It takes a stereotype histogram
that something else MEASURED, plus the language bindings, and ranks the
candidate views. It decides nothing on its own authority and it never guesses
at content: no repository calls, no COM, no I/O.

THE ENGINE IS GENERIC; THE LANGUAGES ARE DATA
----------------------------------------------
There is no notation name in this file. A view catalogue is a binding's
`viewpoints:` block, and which technology owns a stereotype is worked out from
each binding's declared `stereotype_prefix`. **Adding a language must never mean
editing this module**, and a test enforces that by walking the AST.

THE PIVOTAL QUESTION IS HOMOGENEITY
------------------------------------
Is this scope one modeling language, or several?

* **One** - recommend that language's standard view. Ranked mechanically on
  coverage, admissibility and intent, with the evidence shown.
* **Several** - there is no conformant answer, and pretending otherwise is the
  damaging case. The preference order is: a dominant-language view that accepts
  some foreign content; a neutral custom view belonging to no language; or a
  split into linked conformant diagrams.

Every non-standard recommendation carries two obligations, both of them data on
the result rather than advice in prose: `non_conformance` says the view is not
conformant and which languages it spans, and `will_be_flagged` names the
elements a conformance check will object to, so they can be scoped out or
annotated as accepted rather than discovered later.

CAN IT BE DRAWN IS A SEPARATE QUESTION FROM WHICH VIEW IS RIGHT
---------------------------------------------------------------
A recommended view is an argument to make about content; whether this toolchain
can generate it is a statement about the toolchain. So both are reported, and
neither is allowed to stand in for the other. `Candidate.generation_route` says
how a diagram of the view would actually be drawn - composed here, handed to the
drawing tool's own layout, or not producible at all - and a view that cannot be
generated is still ranked and still recommended, with that said plainly. It is
suppressed from neither the ranking nor the reasons, because what the content
wants to be shown as does not depend on what we have built yet.

WHAT THIS MODULE REFUSES TO DO
-------------------------------
It does not pick. `recommend` returns a ranked list with reasons; a caller that
wants the top one takes it, and a user who asked for a specific diagram type
gets that, with a note when it fits badly. A recommender that silently decides
is indistinguishable from a recommender that is wrong.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterable, Mapping, Optional, Sequence

__all__ = [
    "ScopeProfile",
    "Candidate",
    "Recommendation",
    "profile_scope",
    "recommend",
    "HOMOGENEOUS_SHARE",
    "AMBIGUOUS",
    "HOMOGENEOUS_SHARE",
    "UNATTRIBUTED",
    "ROUTE_COMPOSED",
    "ROUTE_TOOL_LAYOUT",
    "ROUTE_COMPOSER_PENDING",
    "ROUTE_NOT_PRODUCIBLE",
    "ROUTE_UNANSWERED",
]

# A scope is homogeneous when one technology holds at least this share of the
# stereotyped elements. Not 1.0: a real model carries strays - a stray Note, one
# element someone stereotyped from another profile - and a rule that called
# 97 percent "mixed" would send every real scope down the non-conformant path,
# which is the path with the obligations attached.
HOMOGENEOUS_SHARE = 0.9

# The bucket for stereotypes no binding claims. Named rather than None because
# it is a real and common answer: a customer's own MDG has no binding here, and
# "most of this scope belongs to a language I do not know" is a finding, not a
# gap to paper over.
UNATTRIBUTED = "(unbound)"

# The bucket for a stereotype that more than one language claims. Distinct from
# UNATTRIBUTED: "several languages could own this" and "no language owns this"
# lead to different conversations, and collapsing them would hide the one that
# needs a human.
AMBIGUOUS = "(ambiguous)"

# Words shorter than this are dropped when matching a request against what a
# view is for. "the", "of", "to" match everything and mean nothing.
_MIN_INTENT_WORD = 4

# HOW A RECOMMENDED VIEW WOULD ACTUALLY GET DRAWN. Four routes, and telling
# them apart is the difference between a useful recommendation and a misleading
# one. There used to be one question here - "is the layout implemented" - and a
# single boolean answering it conflated two routes that lead opposite ways: a
# view whose positions the drawing tool supplies (which is the intended route
# and produces a perfectly good diagram) and a view that cannot be produced at
# all (where "compose it another way" is exactly the wrong advice).
#
# THESE ARE DERIVED, NEVER MATCHED. Nothing in this module holds a grammar name
# or a list of them. Each route is worked out from the answers the binding layer
# gives about a view - is the geometry ours to compute, can it be produced - so
# the day a layout ships, every answer here moves with it. The alternative has
# already cost us once: a measurement tool decided implementation from its own
# hardcoded pair of names while its test asserted the same pair, so shipping a
# layout moved the reported figure by zero and every test stayed green.
ROUTE_COMPOSED = "composed"
ROUTE_TOOL_LAYOUT = "tool-layout"
ROUTE_COMPOSER_PENDING = "composer-pending"
ROUTE_NOT_PRODUCIBLE = "not-producible"
# Not a fifth route: the binding object did not answer, so no route is known.
# Distinct from `""`, which means no layout grammar is stated anywhere - a view
# with nothing to say about its layout and a view whose data we cannot read are
# different findings, and the second one needs saying out loud.
ROUTE_UNANSWERED = "unanswered"

# What each route obliges the recommendation to say. A mapping rather than a
# chain of conditionals in `recommend`, so the prose and the classification
# cannot drift apart: a route with nothing to add says nothing, and that is
# stated here as an empty tuple rather than by omission.
_ROUTE_ADVICE: Mapping[str, tuple] = {
    # Ours to compute, and built. The ordinary case, and it needs no caveat.
    ROUTE_COMPOSED: (),
    ROUTE_TOOL_LAYOUT: (
        "its geometry is not composed here, and that is the design rather "
        "than a limitation: place the elements, call the drawing tool's own "
        "layout operation, then tidy the result and check it looks right",
    ),
    ROUTE_COMPOSER_PENDING: (
        "its grammar {grammar} is not implemented, so the layout will have to "
        "be composed another way or handed to the tool's own layout",
    ),
    ROUTE_NOT_PRODUCIBLE: (
        "CANNOT BE GENERATED: the diagram type itself dictates this view's "
        "arrangement, so composing coordinates cannot produce it - the "
        "elements would be placed and the meaning their positions are "
        "supposed to carry would not follow. Draw it by hand in the tool, or "
        "choose a view whose layout is ours to place",
        "it is ranked and listed anyway, because what the content wants to be "
        "shown as is worth knowing whether or not this tool can draw it",
    ),
    ROUTE_UNANSWERED: (
        "its layout grammar {grammar} comes with no statement of whether a "
        "diagram of it can be produced, so confirm that before promising a "
        "generated diagram",
    ),
}

# Distinct from None, which a binding object uses to mean "no opinion of my
# own, ask the diagram type". A property that is not there at all is a missing
# ANSWER, and `getattr(..., None)` cannot tell the two apart - it would report
# an object this module cannot read as an object with nothing to say.
_MISSING = object()


@dataclass(frozen=True)
class ScopeProfile:
    """What a scope is made of, measured."""

    technologies: Mapping[str, int]      # technology id -> element count
    concepts: Mapping[str, int]          # bare concept name -> element count
    by_technology: Mapping[str, tuple]   # technology id -> concepts it holds
    total: int
    # Stereotypes no binding claimed, with their counts. Reported rather than
    # summarized away: "I could not place 40% of this scope" is the single most
    # useful thing to know before trusting the recommendation.
    unattributed_stereotypes: Mapping[str, int] = field(default_factory=dict)

    @property
    def dominant(self) -> Optional[str]:
        """The technology holding the most elements, or None for an empty scope.

        Ties break on the technology id so the answer is stable; a tie means
        the scope is mixed anyway, and `homogeneous` will say so.
        """
        if not self.technologies:
            return None
        return max(sorted(self.technologies), key=lambda t: self.technologies[t])

    @property
    def dominant_share(self) -> float:
        if not self.total or self.dominant is None:
            return 0.0
        return self.technologies[self.dominant] / self.total

    @property
    def homogeneous(self) -> bool:
        return bool(self.total) and self.dominant_share >= HOMOGENEOUS_SHARE

    @property
    def ambiguous(self) -> int:
        """Elements whose language could not be decided, not merely unknown."""
        return self.technologies.get(AMBIGUOUS, 0)

    # Technologies a binding exists for. A technology can be NAMED without
    # being bound: the runtime reader knows a customer's own MDG owns a
    # stereotype, while nothing here knows what views that MDG offers.
    bound_technologies: frozenset = field(default_factory=frozenset)

    @property
    def is_bound(self) -> bool:
        """Whether the dominant technology is one we have a binding for.

        False means the scope is mostly a language this installation cannot
        advise on - a customer's own MDG, most often. That is a different
        answer from "mixed" and leads somewhere different, which is why naming
        the technology and being able to advise on it are separate facts.
        """
        if self.dominant in (None, UNATTRIBUTED, AMBIGUOUS):
            return False
        return self.dominant in self.bound_technologies

    @property
    def spans(self) -> tuple:
        return tuple(sorted(self.technologies))


def _known_concepts(binding: Any) -> set:
    """Every concept a binding names, from its own data.

    Read from `sizing` keys and from every viewpoint's `admits`, because those
    are where a binding states what its language contains. Deriving it means a
    binding that grows a concept is understood without this module changing.
    """
    concepts: set = set()
    for diagram_type in getattr(binding, "diagram_types", {}).values():
        concepts.update(k for k in getattr(diagram_type, "sizing", {})
                        if k != "default")
    for viewpoint in getattr(binding, "viewpoints", {}).values():
        concepts.update(getattr(viewpoint, "admits", ()))
    return concepts


def _attribute(stereotype: str, bindings: Sequence[Any],
               known_concepts: Optional[Mapping[str, Any]] = None) -> tuple:
    """Which technology owns `stereotype`, and the bare concept name.

    Matching is by the binding's DECLARED prefix, longest first. Longest wins
    because an unprefixed language would otherwise claim a prefixed language's
    concept whenever the two share a name - and they do share names, which is
    exactly why one of them carries a prefix.

    Returns `(technology, concept)`, or `(UNATTRIBUTED, stereotype)` when no
    binding claims it.
    """
    stereotype = (stereotype or "").strip()
    if not stereotype:
        return UNATTRIBUTED, stereotype
    ordered = sorted(
        bindings,
        key=lambda b: len(getattr(b, "stereotype_prefix", "") or ""),
        reverse=True,
    )
    bound_technologies = {b.technology for b in bindings}
    claims: list[tuple] = []
    best_prefix = None
    for binding in ordered:
        prefix = getattr(binding, "stereotype_prefix", "") or ""
        if prefix and not stereotype.startswith(prefix):
            continue
        concept = stereotype[len(prefix):] if prefix else stereotype
        vocabulary = set(_known_concepts(binding))
        vocabulary |= set((known_concepts or {}).get(binding.technology, ()))
        if concept not in vocabulary:
            continue
        if best_prefix is None:
            best_prefix = len(prefix)
        if len(prefix) < best_prefix:
            # A shorter prefix already lost to a longer one. An unprefixed
            # language must not claim a prefixed language's concept: they share
            # names, which is precisely why one of them carries a prefix.
            break
        claims.append((binding.technology, concept))

    if not claims:
        # A technology with no binding can still be NAMED, when the caller
        # supplied its vocabulary from the runtime reader. Saying "this is
        # 100 elements of a language you have no binding for" is far more
        # useful than "100 elements of nothing", and it is the common case: a
        # customer's own MDG is exactly this.
        unbound_claims = [
            (technology, stereotype)
            for technology, vocabulary in (known_concepts or {}).items()
            if technology not in bound_technologies
            and stereotype in set(vocabulary)
        ]
        if len(unbound_claims) == 1:
            return unbound_claims[0]
        if len(unbound_claims) > 1:
            return AMBIGUOUS, stereotype
        return UNATTRIBUTED, stereotype
    if len(claims) == 1:
        return claims[0]
    # TWO OR MORE LANGUAGES CLAIM IT AT THE SAME PREFIX LENGTH, and there is no
    # honest way to choose between them from the stereotype alone. Returning
    # the first was the original behaviour, and it resolved the tie by whatever
    # order the bindings happened to arrive in -- an answer indistinguishable
    # from a correct one and wrong half the time. A real repository has several
    # technologies loaded that share concept names, so this is not hypothetical.
    return AMBIGUOUS, stereotype


def profile_scope(stereotype_counts: Mapping[str, int],
                  bindings: Sequence[Any],
                  known_concepts: Optional[Mapping[str, Any]] = None
                  ) -> ScopeProfile:
    """Turn a measured stereotype histogram into a technology histogram.

    `stereotype_counts` maps the stereotype AS EA STORES IT to how many
    elements carry it - which is what the repository's own summary operations
    return. Nothing here counts anything; it only attributes what it was given.

    An element with no stereotype is not counted. It belongs to no language, so
    it cannot help decide which language's view to use - and letting a pile of
    plain elements outvote the stereotyped content would recommend a neutral
    view for a scope that has a perfectly good conformant one.

    `known_concepts` maps a technology id to the concepts it owns, and the
    caller should supply it from the tool's own runtime MDG reader. Without it,
    attribution falls back to the concepts each binding happens to NAME - and a
    binding names only what departs from its defaults, so the most common
    concept in a language is often the one it does not list. Measured: a
    binding that sizes its events and gateways individually leaves its ordinary
    activity to `default`, so a scope full of activities attributed to nothing
    at all.

    Whatever is not attributed is counted under `UNATTRIBUTED` and listed in
    `unattributed_stereotypes`, so the gap is visible rather than silently
    reshaping the answer.
    """
    technologies: dict[str, int] = {}
    concepts: dict[str, int] = {}
    by_technology: dict[str, set] = {}
    unattributed: dict[str, int] = {}
    total = 0
    for stereotype, count in (stereotype_counts or {}).items():
        if not (stereotype or "").strip():
            # An unstereotyped element. Not a language's, so not a vote.
            continue
        try:
            count = int(count)
        except (TypeError, ValueError):
            continue
        if count <= 0:
            continue
        technology, concept = _attribute(stereotype, bindings, known_concepts)

        if technology in (UNATTRIBUTED, AMBIGUOUS):
            unattributed[stereotype] = unattributed.get(stereotype, 0) + count
        technologies[technology] = technologies.get(technology, 0) + count
        concepts[concept] = concepts.get(concept, 0) + count
        by_technology.setdefault(technology, set()).add(concept)
        total += count
    return ScopeProfile(
        technologies=dict(technologies),
        concepts=dict(concepts),
        by_technology={k: tuple(sorted(v)) for k, v in by_technology.items()},
        unattributed_stereotypes=dict(unattributed),
        bound_technologies=frozenset(b.technology for b in bindings),
        total=total,
    )


@dataclass(frozen=True)
class Candidate:
    """One view under consideration, with the arithmetic that ranked it."""

    technology: str
    viewpoint: str
    diagram_type: str
    admitted: tuple            # concepts in scope this view admits
    foreign: tuple             # concepts in scope it does not
    coverage: float            # share of the scope's ELEMENTS it admits
    intent_hits: tuple         # intent words that matched
    grammar: str = ""
    # THREE ANSWERS, NOT ONE, and every consumer wants a different pair of
    # them. `grammar_is_implemented` alone is the bug this trio replaces: a
    # caller reading only that value sees False both for a layout nobody has
    # built and for a view whose geometry was never ours to compute, and those
    # two lead to opposite advice. `None` here means the question went
    # unanswered - see `_grammar_answers`.
    grammar_is_implemented: Optional[bool] = None
    geometry_is_composed: Optional[bool] = None
    grammar_is_producible: Optional[bool] = None

    @property
    def generation_route(self) -> str:
        """How a diagram of this view would be drawn - one of the ROUTE names.

        Derived on every read from the answers above, so it cannot disagree
        with them, and `""` when no layout grammar is stated at all.

        An unanswered question does not fall through to a route. Reading a
        missing answer as False is how "the tool places this, correctly" became
        indistinguishable from "we cannot do this".
        """
        if not self.grammar:
            return ""
        if self.grammar_is_producible is None or self.geometry_is_composed is None:
            return ROUTE_UNANSWERED
        if self.grammar_is_producible:
            return ROUTE_COMPOSED if self.geometry_is_composed else ROUTE_TOOL_LAYOUT
        return (ROUTE_COMPOSER_PENDING if self.geometry_is_composed
                else ROUTE_NOT_PRODUCIBLE)

    @property
    def can_be_generated(self) -> Optional[bool]:
        """Whether a diagram of this view can be produced today, or None if
        the binding did not say. Not a synonym for the layout being composed."""
        return self.grammar_is_producible

    @property
    def score(self) -> tuple:
        """Coverage first, then intent, then the narrower view.

        Coverage leads because a view that cannot hold the content is not a
        candidate however well its name matches the request. The narrower view
        wins a tie: a viewpoint admitting six concepts says more about what the
        diagram is FOR than one admitting twenty.
        """
        return (round(self.coverage, 4), len(self.intent_hits), -len(self.admitted + self.foreign))


@dataclass(frozen=True)
class Recommendation:
    """A recommendation, its reasoning, and its obligations."""

    kind: str                  # standard | dominant-language | neutral-custom | split
    technology: str
    viewpoint: str
    diagram_type: str
    reasons: tuple
    spans: tuple = ()
    non_conformance: str = ""
    will_be_flagged: tuple = ()
    candidate: Optional[Candidate] = None

    @property
    def conformant(self) -> bool:
        return not self.non_conformance


def _tokens(text: str) -> set:
    """Significant words, lowercased. Short words are dropped as noise."""
    out = set()
    word = []
    for char in (text or "").lower():
        if char.isalnum():
            word.append(char)
        elif word:
            out.add("".join(word))
            word = []
    if word:
        out.add("".join(word))
    return {w for w in out if len(w) >= _MIN_INTENT_WORD}


def _intent_hits(intent: str, name: str, viewpoint: Any) -> tuple:
    """Words shared between the user's request and what this view is for.

    TOKEN overlap, not phrase containment. The first version matched a
    binding's intent phrase only when it appeared verbatim in the request, so
    "I want to see the application landscape" matched nothing at all and the
    ranking fell through to a tiebreak - recommending a technology view for an
    application question, confidently and with reasons. A recommender that
    looks right while being wrong is worse than one that abstains.

    The viewpoint's NAME counts as evidence of what it is for, alongside the
    intent phrases the binding records. Both are data; no vocabulary is kept
    here, so a language this module has never heard of ranks on the same basis.
    """
    wanted = _tokens(intent)
    if not wanted:
        return ()
    offered = _tokens(name)
    for phrase in getattr(viewpoint, "intent", ()):
        offered |= _tokens(phrase)
    return tuple(sorted(wanted & offered))


def _answer(source: Any, question: str) -> Optional[bool]:
    """One boolean property off a binding object, or None when it has none.

    `getattr(source, question, None)` is the wrong default and the reason this
    helper exists: it cannot tell an object that never exposed the property
    from one that answered None, and the second means "no opinion". A missing
    property is a missing answer, and the caller reports that rather than
    letting it read as agreement.
    """
    value = getattr(source, question, _MISSING)
    if value is _MISSING or value is None:
        return None
    return bool(value)


def _grammar_answers(viewpoint: Any, binding: Any) -> tuple:
    """The layout grammar in force for a viewpoint, and the answers about it.

    Returns `(grammar, is_composed, is_implemented, is_producible)`.

    A VIEWPOINT'S `None` IS NOT `False`. The binding layer answers None to each
    of these questions when the viewpoint states no grammar of its own, meaning
    "ask the diagram type" - so an unstated grammar is resolved against the
    diagram type here. Reading the viewpoint alone is how a view whose diagram
    type cannot be produced at all got recommended with nothing said about it:
    the questions were asked of the only object that had no answer, and silence
    came back looking like approval.

    A viewpoint that DOES state its own grammar is asked itself, because an
    override is the whole point: a view arranged as a grid on a diagram type
    arranged as bands is neither of the other's answers.

    No grammar name appears here or anywhere else in this module. Every answer
    is asked of the binding objects, so a layout that ships moves this without
    an edit - which a literal list of names would not.
    """
    grammar = getattr(viewpoint, "effective_grammar", "") or ""
    source: Any = viewpoint
    if not grammar:
        catalog = getattr(binding, "diagram_types", None) or {}
        diagram_type = catalog.get(getattr(viewpoint, "diagram_type", ""))
        if diagram_type is None:
            return "", None, None, None
        source = diagram_type
        grammar = getattr(source, "grammar", "") or ""
        if not grammar:
            return "", None, None, None
    return (
        grammar,
        _answer(source, "geometry_is_composed"),
        _answer(source, "grammar_is_implemented"),
        _answer(source, "grammar_is_producible"),
    )


def _route_advice(candidate: Candidate) -> tuple:
    """What this candidate's generation route obliges the reasons to say.

    Every recommendation naming a viewpoint gets this, not only the conformant
    ones: a dominant-language view is as capable of being unproducible as a
    standard one, and saying nothing about it in one branch while saying it in
    the other is the same defect one level down.
    """
    return tuple(
        advice.format(grammar=repr(candidate.grammar))
        for advice in _ROUTE_ADVICE.get(candidate.generation_route, ())
    )


def _candidates(profile: ScopeProfile, binding: Any,
                intent: str) -> list[Candidate]:
    """Every viewpoint of one binding, scored against the scope."""
    held = set(profile.by_technology.get(binding.technology, ()))
    counts = profile.concepts
    in_scope_total = sum(counts.get(c, 0) for c in held) or 1

    out: list[Candidate] = []
    for name, viewpoint in getattr(binding, "viewpoints", {}).items():
        admits = set(getattr(viewpoint, "admits", ()))
        admitted = tuple(sorted(held & admits))
        foreign = tuple(sorted(held - admits))
        covered = sum(counts.get(c, 0) for c in admitted)
        grammar, composed, implemented, producible = _grammar_answers(
            viewpoint, binding)
        out.append(Candidate(
            technology=binding.technology,
            viewpoint=name,
            diagram_type=getattr(viewpoint, "diagram_type", ""),
            admitted=admitted,
            foreign=foreign,
            coverage=covered / in_scope_total,
            intent_hits=_intent_hits(intent, name, viewpoint),
            grammar=grammar,
            grammar_is_implemented=implemented,
            geometry_is_composed=composed,
            grammar_is_producible=producible,
        ))
    out.sort(key=lambda c: (c.score, c.viewpoint), reverse=True)
    return out


def _binding_for(technology: str, bindings: Sequence[Any]) -> Optional[Any]:
    for binding in bindings:
        if binding.technology == technology:
            return binding
    return None


def recommend(profile: ScopeProfile, bindings: Sequence[Any],
              intent: str = "") -> list[Recommendation]:
    """Ranked recommendations for this scope, best first, with reasoning.

    Never empty for a non-empty scope: when no conformant view exists the
    answer is a deliberate non-standard one, which is a recommendation with
    obligations attached rather than a refusal.
    """
    if not profile.total:
        return [Recommendation(
            kind="none", technology="", viewpoint="", diagram_type="",
            reasons=("the scope holds no stereotyped elements, so there is "
                     "nothing to profile; choose a diagram type from the "
                     "intent alone, or widen the scope",),
        )]

    shares = ", ".join(
        f"{tech} {profile.technologies[tech]}"
        for tech in sorted(profile.technologies,
                           key=lambda t: -profile.technologies[t])
    )
    evidence = (f"{profile.total} stereotyped element(s): {shares}")

    # ---- homogeneous and bound: the ordinary, conformant answer ------------
    if profile.homogeneous and profile.is_bound:
        binding = _binding_for(profile.dominant, bindings)
        candidates = _candidates(profile, binding, intent) if binding else []
        out = []
        # A tie is common and worth saying out loud. In a small scope many
        # viewpoints admit everything present, so coverage and intent both tie
        # and an arbitrary tiebreak picks the winner. Presenting that as a
        # decisive recommendation is how a recommender is confidently wrong;
        # naming the alternative lets the caller choose on grounds this module
        # does not have.
        tied = [c.viewpoint for c in candidates
                if candidates and c.score == candidates[0].score]
        for candidate in candidates[:3]:
            reasons = [
                evidence,
                f"{profile.dominant} holds "
                f"{profile.dominant_share:.0%} of the scope, so a conformant "
                f"view of that language is available",
                f"this view admits {len(candidate.admitted)} of the "
                f"{len(candidate.admitted) + len(candidate.foreign)} "
                f"concept(s) present, covering "
                f"{candidate.coverage:.0%} of the elements",
            ]
            if candidate.intent_hits:
                reasons.append(
                    "the request matches its stated intent: "
                    + ", ".join(repr(h) for h in candidate.intent_hits))
            if candidate.foreign:
                reasons.append(
                    "content it does not admit: "
                    + ", ".join(candidate.foreign))
            if len(tied) > 1 and candidate.viewpoint in tied:
                others = [v for v in tied if v != candidate.viewpoint]
                reasons.append(
                    "CLOSE CALL: "
                    + ", ".join(others)
                    + (" ranks" if len(others) == 1 else " rank")
                    + " equally on coverage and intent. Choose on what the "
                      "diagram is for, which this ranking cannot see")
            reasons.extend(_route_advice(candidate))
            out.append(Recommendation(
                kind="standard",
                technology=candidate.technology,
                viewpoint=candidate.viewpoint,
                diagram_type=candidate.diagram_type,
                reasons=tuple(reasons),
                spans=profile.spans,
                will_be_flagged=candidate.foreign,
                candidate=candidate,
            ))
        if out:
            return out

    # ---- everything below is deliberately non-standard ---------------------
    spans = profile.spans
    languages = ", ".join(spans)
    non_conformance = (
        f"This view is NOT conformant to any single modeling language. It "
        f"spans {len(spans)}: {languages}. Record that on the diagram and in "
        f"the response."
    )

    out = []

    # 1. A dominant-language view that accepts some foreign content.
    binding = _binding_for(profile.dominant, bindings) if profile.is_bound else None
    if binding is not None:
        candidates = _candidates(profile, binding, intent)
        if candidates:
            best = candidates[0]
            foreign_elsewhere = tuple(sorted(
                concept
                for technology, concepts in profile.by_technology.items()
                if technology != profile.dominant
                for concept in concepts
            ))
            out.append(Recommendation(
                kind="dominant-language",
                technology=best.technology,
                viewpoint=best.viewpoint,
                diagram_type=best.diagram_type,
                reasons=(
                    evidence,
                    f"no language holds {HOMOGENEOUS_SHARE:.0%} of the scope, "
                    f"so no view is conformant; {profile.dominant} is the "
                    f"largest at {profile.dominant_share:.0%}",
                    "its view carries the majority and the rest appears as "
                    "foreign content, which is the least surprising of the "
                    "non-standard options",
                ) + _route_advice(best),
                spans=spans,
                non_conformance=non_conformance,
                will_be_flagged=tuple(sorted(
                    set(best.foreign) | set(foreign_elsewhere))),
                candidate=best,
            ))

    # 2. A neutral custom view, belonging to no language.
    neutral_reasons = [evidence]
    if not profile.is_bound and profile.dominant == UNATTRIBUTED:
        unbound = profile.technologies.get(UNATTRIBUTED, 0)
        neutral_reasons.append(
            f"{unbound} of {profile.total} element(s) carry a stereotype no "
            f"loaded binding claims - most likely an MDG this installation "
            f"has no binding for. There is no conformant view to recommend "
            f"for them, which is a different answer from the scope being mixed"
        )
    out.append(Recommendation(
        kind="neutral-custom",
        technology="", viewpoint="", diagram_type="Logical",
        reasons=tuple(neutral_reasons) + (
            "a base diagram type with no profile belongs to no language, so "
            "nothing on it is foreign and no conformance rule applies to the "
            "diagram as a whole",
            "this is ordinary practice rather than a workaround - a large "
            "share of real-world diagrams are plain base types",
        ),
        spans=spans,
        non_conformance=non_conformance,
        will_be_flagged=(),
    ))

    # 3. Split into linked conformant diagrams.
    if len(spans) > 1:
        out.append(Recommendation(
            kind="split",
            technology="", viewpoint="", diagram_type="",
            reasons=(
                evidence,
                f"one conformant diagram per language ({languages}), linked, "
                f"keeps every view valid",
                "the cost is that no single picture shows the whole scope, "
                "which is usually the thing that was wanted",
            ),
            spans=spans,
            non_conformance="",
            will_be_flagged=(),
        ))

    return out

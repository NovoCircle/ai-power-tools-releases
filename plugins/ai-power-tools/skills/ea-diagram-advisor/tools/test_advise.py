#!/usr/bin/env python3
"""Tests for the diagram advisor's ranking engine.

Run from the repository root:

    python -m pytest ea-diagram-advisor/tools/test_advise.py -q

Nothing here touches a repository. The histograms are fixtures standing in for
what the repository's summary operations measure, which is the whole point of
the split: the advisor never guesses at content, and the arithmetic of choosing
can be tested without a model.

The bindings ARE loaded for real, from `ea-diagram-composition`. A fake binding
would let the engine pass against a view catalogue nobody ships.
"""
from __future__ import annotations

import ast
import sys
from pathlib import Path

import pytest

_HERE = Path(__file__).resolve().parent
_COMPOSITION = _HERE.parent.parent / "ea-diagram-composition" / "tools"
for path in (str(_HERE), str(_COMPOSITION)):
    if path not in sys.path:
        sys.path.insert(0, path)

import advise  # noqa: E402
from advise import (  # noqa: E402
    HOMOGENEOUS_SHARE,
    UNATTRIBUTED,
    profile_scope,
    recommend,
)

bindings = pytest.importorskip("bindings")


@pytest.fixture(scope="module")
def loaded():
    found = [bindings.find_binding(t) for t in ("ArchiMate3", "BPMN2.0")]
    if any(b is None for b in found):
        pytest.skip("the shipped bindings are not loadable")
    return found


# Histograms stand in for what `summarize_stereotype_usage` measures. The keys
# are stereotypes AS EA STORES THEM, prefixed or bare, because that is what the
# attribution has to cope with.
def _archimate_scope():
    return {"ArchiMate_ApplicationComponent": 12,
            "ArchiMate_ApplicationService": 5,
            "ArchiMate_BusinessProcess": 4}


def _bpmn_scope():
    return {"Activity": 9, "StartEvent": 2, "Gateway": 3}


def _mixed_scope():
    return {"ArchiMate_ApplicationComponent": 10, "Activity": 8}


# ---------------------------------------------------------------------------
# The engine is generic
# ---------------------------------------------------------------------------
def test_the_advisor_names_no_modeling_language():
    """Adding a language must never mean editing this module.

    A view catalogue is a binding's data and which technology owns a stereotype
    comes from its declared prefix, so the moment a notation name appears here
    the claim that this ranks an unknown language on the same basis is false.

    Walks identifiers, string constants, imports, def and class names - the
    shapes a realistic leak actually takes.
    """
    tree = ast.parse((_HERE / "advise.py").read_text(encoding="utf-8"))
    names = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Name):
            names.append(node.id)
        elif isinstance(node, ast.Attribute):
            names.append(node.attr)
        elif isinstance(node, ast.Constant) and isinstance(node.value, str):
            names.append(node.value)
        elif isinstance(node, ast.arg):
            names.append(node.arg)
        elif isinstance(node, (ast.FunctionDef, ast.ClassDef)):
            names.append(node.name)
        elif isinstance(node, ast.Import):
            names.extend(a.name for a in node.names)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                names.append(node.module)
            names.extend(a.name for a in node.names)
    blob = " ".join(names).lower()
    for notation in ("archimate", "bpmn", "sysml", "togaf", "wba", "westbrook"):
        assert notation not in blob, f"{notation!r} leaked into advise.py"


def test_the_advisor_makes_no_repository_calls():
    source = (_HERE / "advise.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    imported = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.extend(a.name for a in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.append(node.module)
    for banned in ("server", "ea_mcp_server", "win32com", "sqlite3", "os"):
        assert banned not in imported, f"advise.py imports {banned!r}"


# ---------------------------------------------------------------------------
# Attribution: a stereotype back to the language that owns it
# ---------------------------------------------------------------------------
def test_a_prefixed_stereotype_is_attributed_by_its_prefix(loaded):
    profile = profile_scope(_archimate_scope(), loaded)
    assert set(profile.technologies) == {"ArchiMate3"}
    assert profile.total == 21
    assert "ApplicationComponent" in profile.concepts


def test_an_unprefixed_stereotype_is_attributed_by_its_concepts(loaded):
    """A language with no prefix is recognized by the concept names it owns."""
    profile = profile_scope({"StartEvent": 2, "Gateway": 3}, loaded)
    assert set(profile.technologies) == {"BPMN2.0"}
    assert profile.homogeneous


def test_a_binding_alone_does_not_know_its_own_commonest_concept(loaded):
    """A real limitation, pinned so it is not mistaken for a bug later.

    A binding names only the concepts that DEPART from its defaults, so the
    most common concept in a language is often the one it never lists - here,
    the ordinary activity that takes the default size. Attribution therefore
    cannot place it, and a scope full of them looks unbound.

    The gap is reported rather than hidden, and the caller closes it by passing
    the vocabulary from the tool's own runtime MDG reader.
    """
    profile = profile_scope(_bpmn_scope(), loaded)
    assert "Activity" in profile.unattributed_stereotypes
    assert profile.unattributed_stereotypes["Activity"] == 9

    informed = profile_scope(_bpmn_scope(), loaded,
                             known_concepts={"BPMN2.0": {"Activity"}})
    assert set(informed.technologies) == {"BPMN2.0"}
    assert informed.unattributed_stereotypes == {}
    assert informed.homogeneous


def test_the_longest_prefix_wins(loaded):
    """An unprefixed language must not claim a prefixed one's concept.

    They share concept names - which is exactly why one of them carries a
    prefix - so matching in an arbitrary order would attribute by luck.
    """
    profile = profile_scope({"ArchiMate_BusinessProcess": 5}, loaded)
    assert set(profile.technologies) == {"ArchiMate3"}


def test_a_stereotype_no_binding_claims_is_bucketed_not_dropped(loaded):
    """A customer's own MDG is the common case, and losing it would make a
    scope look homogeneous when most of it is a language we cannot advise on."""
    profile = profile_scope({"WBABusinessApplication": 20,
                             "ArchiMate_ApplicationComponent": 2}, loaded)
    assert profile.technologies[UNATTRIBUTED] == 20
    assert profile.total == 22
    assert profile.dominant == UNATTRIBUTED
    assert profile.is_bound is False


def test_unstereotyped_elements_are_simply_absent(loaded):
    """They belong to no language, so they cannot help choose one. Letting a
    pile of plain elements outvote the stereotyped content would recommend a
    neutral view for a scope with a perfectly good conformant one."""
    profile = profile_scope({"": 100, "ArchiMate_ApplicationComponent": 3},
                            loaded)
    assert profile.total == 3
    assert profile.dominant == "ArchiMate3"


def test_a_zero_or_negative_count_is_ignored(loaded):
    profile = profile_scope({"ArchiMate_ApplicationComponent": 0,
                             "ArchiMate_ApplicationService": -4}, loaded)
    assert profile.total == 0
    assert profile.technologies == {}


# ---------------------------------------------------------------------------
# Homogeneity, which is the pivotal question
# ---------------------------------------------------------------------------
def test_a_single_language_scope_is_homogeneous(loaded):
    assert profile_scope(_archimate_scope(), loaded).homogeneous


def test_a_few_strays_do_not_make_a_scope_mixed(loaded):
    """Not 1.0, deliberately. A real model carries strays, and a rule that
    called 97 percent mixed would send every real scope down the
    non-conformant path - the path with obligations attached."""
    profile = profile_scope({"ArchiMate_ApplicationComponent": 97,
                             "Activity": 3}, loaded)
    assert profile.dominant_share >= HOMOGENEOUS_SHARE
    assert profile.homogeneous


def test_an_even_split_is_not_homogeneous(loaded):
    profile = profile_scope(_mixed_scope(), loaded)
    assert not profile.homogeneous
    assert len(profile.spans) == 2


def test_an_empty_scope_has_no_dominant_language(loaded):
    profile = profile_scope({}, loaded)
    assert profile.dominant is None
    assert not profile.homogeneous
    assert profile.dominant_share == 0.0


# ---------------------------------------------------------------------------
# Recommending
# ---------------------------------------------------------------------------
def test_a_homogeneous_scope_gets_a_conformant_view(loaded):
    profile = profile_scope(_archimate_scope(), loaded)
    best = recommend(profile, loaded, intent="how the applications fit together")[0]
    assert best.kind == "standard"
    assert best.conformant
    assert best.technology == "ArchiMate3"
    assert best.viewpoint
    assert best.diagram_type


def test_the_reasoning_names_the_evidence(loaded):
    """'Show the reasoning' is an acceptance criterion, so it is asserted.

    The counts have to appear: a recommendation whose justification could have
    been written without looking at the content is not a measurement.
    """
    profile = profile_scope(_archimate_scope(), loaded)
    best = recommend(profile, loaded, intent="applications")[0]
    joined = " ".join(best.reasons)
    assert str(profile.total) in joined
    assert "ArchiMate3" in joined
    assert "%" in joined, "the coverage arithmetic is not shown"


def test_a_close_call_is_declared_rather_than_hidden(loaded):
    """In a small scope many viewpoints admit everything, so coverage and
    intent tie and an arbitrary tiebreak picks the winner. Presenting that as
    decisive is how a recommender is confidently wrong."""
    profile = profile_scope(_archimate_scope(), loaded)
    ranked = recommend(profile, loaded, intent="applications")
    tied = [r for r in ranked
            if r.candidate and r.candidate.score == ranked[0].candidate.score]
    if len(tied) < 2:
        pytest.skip("this scope produced no tie to declare")
    assert any("CLOSE CALL" in reason for reason in ranked[0].reasons)


def test_several_options_are_offered_not_one(loaded):
    """It recommends and explains; it does not silently decide."""
    profile = profile_scope(_archimate_scope(), loaded)
    assert len(recommend(profile, loaded, intent="applications")) > 1


def test_intent_matching_survives_a_natural_request(loaded):
    """Token overlap, not phrase containment.

    The first version matched a binding's intent phrase only when it appeared
    verbatim, so an ordinary sentence matched nothing and the ranking fell
    through to a tiebreak - producing a confident recommendation on no evidence
    at all.
    """
    profile = profile_scope(_archimate_scope(), loaded)
    best = recommend(
        profile, loaded,
        intent="I want to see the application landscape for this domain")[0]
    assert best.candidate.intent_hits, "a natural request matched nothing"


def test_noise_words_do_not_count_as_intent(loaded):
    profile = profile_scope(_archimate_scope(), loaded)
    best = recommend(profile, loaded, intent="I want to see the one for it")[0]
    assert not best.candidate.intent_hits


# ---------------------------------------------------------------------------
# The non-standard path, and its obligations
# ---------------------------------------------------------------------------
def test_a_mixed_scope_never_gets_a_conformant_recommendation(loaded):
    profile = profile_scope(_mixed_scope(), loaded)
    for option in recommend(profile, loaded, intent="everything"):
        if option.kind == "split":
            continue          # a split IS conformant; that is its whole appeal
        assert option.non_conformance, option.kind
        assert not option.conformant


def test_every_non_conformant_option_names_the_languages_it_spans(loaded):
    """Obligation one, made testable: say so, and say which languages."""
    profile = profile_scope(_mixed_scope(), loaded)
    for option in recommend(profile, loaded, intent="everything"):
        if not option.non_conformance:
            continue
        for technology in profile.spans:
            assert technology in option.non_conformance, technology


def test_the_preference_order_is_dominant_then_neutral_then_split(loaded):
    profile = profile_scope(_mixed_scope(), loaded)
    kinds = [r.kind for r in recommend(profile, loaded, intent="everything")]
    assert kinds == ["dominant-language", "neutral-custom", "split"]


def test_a_dominant_language_view_names_what_will_be_flagged(loaded):
    """Obligation two, made testable: predict what a conformance check will
    object to, so it can be scoped out or accepted deliberately rather than
    discovered afterwards."""
    profile = profile_scope(_mixed_scope(), loaded)
    dominant = next(r for r in recommend(profile, loaded, intent="everything")
                    if r.kind == "dominant-language")
    assert dominant.will_be_flagged
    # The flagged concepts must be ones actually in the scope, not a guess.
    assert set(dominant.will_be_flagged) <= set(profile.concepts)


def test_a_neutral_view_flags_nothing_because_nothing_is_foreign_to_it(loaded):
    profile = profile_scope(_mixed_scope(), loaded)
    neutral = next(r for r in recommend(profile, loaded, intent="everything")
                   if r.kind == "neutral-custom")
    assert neutral.will_be_flagged == ()
    assert neutral.diagram_type


def test_an_unbound_dominant_language_is_explained_not_hidden(loaded):
    """"Most of this is a language I have no binding for" is a finding, and a
    different one from "this scope is mixed"."""
    profile = profile_scope({"WBABusinessApplication": 30,
                             "ArchiMate_ApplicationComponent": 4}, loaded)
    options = recommend(profile, loaded, intent="the estate")
    neutral = next(r for r in options if r.kind == "neutral-custom")
    joined = " ".join(neutral.reasons).lower()
    assert "no loaded binding claims" in joined
    assert "30" in joined


def test_no_option_is_offered_for_an_empty_scope(loaded):
    options = recommend(profile_scope({}, loaded), loaded, intent="anything")
    assert len(options) == 1
    assert options[0].kind == "none"
    assert "nothing to profile" in " ".join(options[0].reasons)


def test_a_single_language_scope_is_not_offered_a_split(loaded):
    """A split is only meaningful across languages."""
    profile = profile_scope({"WBABusinessApplication": 30}, loaded)
    assert "split" not in [r.kind for r in recommend(profile, loaded)]


# ---------------------------------------------------------------------------
# Determinism
# ---------------------------------------------------------------------------
def test_the_same_scope_always_ranks_the_same_way(loaded):
    profile = profile_scope(_archimate_scope(), loaded)
    first = [(r.kind, r.viewpoint) for r in recommend(profile, loaded, "apps")]
    second = [(r.kind, r.viewpoint) for r in recommend(profile, loaded, "apps")]
    assert first == second


def test_histogram_key_order_does_not_change_the_answer(loaded):
    forward = profile_scope(_mixed_scope(), loaded)
    backward = profile_scope(dict(reversed(list(_mixed_scope().items()))),
                             loaded)
    assert forward.technologies == backward.technologies
    assert ([r.kind for r in recommend(forward, loaded, "x")]
            == [r.kind for r in recommend(backward, loaded, "x")])

# ---------------------------------------------------------------------------
# Ambiguity, which must surface rather than be resolved by luck
# ---------------------------------------------------------------------------
class _StubBinding:
    """Two languages that share a concept name and neither carries a prefix.

    Stubs rather than shipped bindings on purpose: the two we ship cannot
    collide, because one is prefixed. The behaviour under test is the tie rule,
    and a real repository has several technologies loaded that DO share concept
    names -- a subagent measured exactly that collision in a live model.
    """

    def __init__(self, technology, concepts, prefix=""):
        self.technology = technology
        self.stereotype_prefix = prefix
        self.diagram_types = {}
        self.viewpoints = {}
        self._concepts = set(concepts)


def _stub_pair():
    a = _StubBinding("Alpha", {"Task"})
    b = _StubBinding("Beta", {"Task"})
    return [a, b]


def _stub_vocabulary():
    return {"Alpha": {"Task"}, "Beta": {"Task"}}


def test_two_languages_claiming_one_name_is_reported_not_resolved():
    """The original code returned whichever binding came first.

    That is an answer indistinguishable from a correct one and wrong half the
    time, decided by nothing more than the order the bindings arrived in.
    """
    profile = profile_scope({"Task": 7}, _stub_pair(),
                            known_concepts=_stub_vocabulary())
    assert profile.technologies == {advise.AMBIGUOUS: 7}
    assert profile.ambiguous == 7
    assert "Task" in profile.unattributed_stereotypes
    assert profile.is_bound is False


def test_binding_order_does_not_change_an_ambiguous_answer():
    """The specific failure: an answer that depends on argument order."""
    pair = _stub_pair()
    forward = profile_scope({"Task": 7}, pair, known_concepts=_stub_vocabulary())
    backward = profile_scope({"Task": 7}, list(reversed(pair)),
                             known_concepts=_stub_vocabulary())
    assert forward.technologies == backward.technologies


def test_a_longer_prefix_still_wins_outright_rather_than_being_ambiguous():
    """Ambiguity is a tie at the SAME prefix length. A prefixed language
    beating an unprefixed one is a decision, not a coin toss."""
    prefixed = _StubBinding("Alpha", {"Task"}, prefix="Alpha_")
    bare = _StubBinding("Beta", {"Alpha_Task"})
    profile = profile_scope(
        {"Alpha_Task": 3}, [bare, prefixed],
        known_concepts={"Alpha": {"Task"}, "Beta": {"Alpha_Task"}})
    assert profile.technologies == {"Alpha": 3}


def test_an_ambiguous_scope_is_not_offered_a_conformant_view():
    profile = profile_scope({"Task": 7}, _stub_pair(),
                            known_concepts=_stub_vocabulary())
    options = recommend(profile, _stub_pair(), intent="the process")
    assert all(o.kind != "standard" for o in options), [o.kind for o in options]

def test_a_language_with_no_binding_is_named_rather_than_lost():
    """"100 elements of a language you have no binding for" is a far more
    useful answer than "100 elements of nothing", and it is the common case -
    a customer's own MDG is exactly this.

    `is_bound` stays False, because naming a technology and being able to
    advise on it are separate facts.
    """
    profile = profile_scope(
        {"HouseStyleApplication": 30, "Task": 2},
        [_StubBinding("Alpha", {"Task"})],
        known_concepts={"HouseStyle": {"HouseStyleApplication"}},
    )
    assert profile.technologies["HouseStyle"] == 30
    assert profile.dominant == "HouseStyle"
    assert profile.is_bound is False
    assert "HouseStyleApplication" not in profile.unattributed_stereotypes


def test_a_named_but_unbound_language_still_gets_a_neutral_recommendation():
    profile = profile_scope(
        {"HouseStyleApplication": 30},
        [_StubBinding("Alpha", {"Task"})],
        known_concepts={"HouseStyle": {"HouseStyleApplication"}},
    )
    kinds = [r.kind for r in recommend(profile, [_StubBinding("Alpha", {"Task"})],
                                       intent="the estate")]
    assert "neutral-custom" in kinds
    assert "standard" not in kinds


def test_a_stereotype_no_vocabulary_claims_is_still_unattributed():
    profile = profile_scope({"SomethingNobodyOwns": 5},
                            [_StubBinding("Alpha", {"Task"})],
                            known_concepts={"HouseStyle": {"Other"}})
    assert profile.unattributed_stereotypes == {"SomethingNobodyOwns": 5}
    assert profile.technologies == {advise.UNATTRIBUTED: 5}


# ---------------------------------------------------------------------------
# How a recommended view would actually get drawn
#
# One boolean used to answer this, and it conflated two routes that lead
# opposite ways: a view the drawing tool lays out for us - which is the intended
# route and produces a good diagram - and a view that cannot be produced at all,
# where "compose it another way" is precisely the wrong advice.
#
# THE GRAMMARS ARE CHOSEN FROM THE BINDING LAYER'S OWN SETS, never named here.
# `audit.py` once decided implemented-ness from a hardcoded pair of names while
# its test asserted the same pair, so shipping a layout moved the reported figure
# by zero and every test stayed green. A test that names the grammar it expects
# is the same trap with the halves swapped: it would keep passing against an
# advisor that had hardcoded the same name.
# ---------------------------------------------------------------------------
def _a_grammar(*, composed: bool, producible: bool) -> str:
    """A grammar from the shipped vocabulary with the answers asked for.

    Skips rather than guesses when the vocabulary has no such grammar - a real
    possibility, since the composed-but-unbuilt case disappears on the day its
    composer ships. A skip says so; a fabricated grammar name would quietly test
    something the library does not have.
    """
    producible_now = bindings.producible_grammars()
    found = sorted(
        grammar for grammar in bindings.GRAMMARS
        if (grammar in bindings.COMPOSED_GRAMMARS) is composed
        and (grammar in producible_now) is producible
    )
    if not found:
        pytest.skip(
            f"the vocabulary has no grammar with composed={composed}, "
            f"producible={producible}")
    return found[0]


def _binding_with(grammar: str, override: str = "") -> list:
    """One technology, one diagram type, one viewpoint - the point being that
    the single candidate cannot be truncated out of the ranking.

    Loaded for real, so the answers under test are the shipped binding layer's
    and not a fixture's idea of them.
    """
    own = f"\n    grammar: {override}" if override else ""
    return [bindings.load_binding_text(f"""
technology: WBA
display_name: WestbrookBankArchitecture
stereotype_prefix: WBA
diagram_types:
  Landscape:
    grammar: {grammar}
    title: frame-header
    sizing:
      default: {{w: 100, h: 60}}
    routing:
      default: Direct
    channels:
      fill: ~
viewpoints:
  ApplicationLandscape:
    diagram_type: Landscape
    admits: [BusinessApplication]{own}
""", "westbrook.yaml")]


def _best_for(grammar: str, override: str = ""):
    loaded = _binding_with(grammar, override)
    profile = profile_scope({"WBABusinessApplication": 10}, loaded)
    options = recommend(profile, loaded, intent="the application landscape")
    return options[0], " ".join(options[0].reasons)


def test_a_viewpoint_with_no_grammar_of_its_own_takes_its_diagram_types():
    """`None` from a viewpoint means "ask the diagram type", never False.

    The advisor asked only the viewpoint, which answers None to every one of
    these questions unless it overrides its diagram type's grammar - so for the
    ordinary viewpoint, which overrides nothing, no grammar was resolved at all
    and nothing was said about whether the view could be drawn. Silence read as
    approval.
    """
    for composed in (True, False):
        for producible in (True, False):
            grammar = _a_grammar(composed=composed, producible=producible)
            best, _ = _best_for(grammar)
            assert best.candidate.grammar == grammar, grammar
            assert best.candidate.geometry_is_composed is composed, grammar
            assert best.candidate.grammar_is_producible is producible, grammar


def test_a_view_the_drawing_tool_lays_out_is_not_reported_as_unimplemented():
    """The largest family of diagram types, and the one most damaged.

    Its geometry is not ours and never will be; handing it to the drawing tool's
    layout IS the design. Reporting that as an unimplemented layout attaches a
    limitation to the normal, fully-producible path.
    """
    ea_placed = _a_grammar(composed=False, producible=True)
    reached_by = [
        _best_for(ea_placed),
        # The same grammar reached the other way: a viewpoint overriding a
        # composed diagram type with this one. THAT path produced the wrong
        # caveat, where the path above produced no answer at all.
        _best_for(_a_grammar(composed=True, producible=True),
                  override=ea_placed),
    ]
    for best, joined in reached_by:
        # The prose first, deliberately: it is what the customer reads, and it
        # is what the old code got wrong - silence on one path and a
        # non-implementation caveat on the other.
        assert "not implemented" not in joined
        assert "composed another way" not in joined
        assert "layout operation" in joined, "the route is not named"
        assert best.candidate.generation_route == advise.ROUTE_TOOL_LAYOUT
        assert best.candidate.can_be_generated is True


def test_a_view_whose_diagram_type_dictates_its_arrangement_says_it_cannot():
    """"Composed another way" is exactly the wrong advice here.

    The diagram type fixes the arrangement, so placing coordinates would
    position the elements and not the thing those positions are supposed to
    carry - which is the content. Far too weak a caveat for a view that cannot
    be produced at all.
    """
    grammar = _a_grammar(composed=False, producible=False)
    best, joined = _best_for(grammar)
    assert "CANNOT BE GENERATED" in joined
    assert "composed another way" not in joined
    assert best.candidate.generation_route == advise.ROUTE_NOT_PRODUCIBLE
    assert best.candidate.can_be_generated is False


def test_a_view_that_cannot_be_generated_is_still_offered():
    """Deliberate, and the opposite choice is defensible - so it is pinned.

    Producibility is a statement about this toolchain, not about the notation.
    Suppressing the view would report our gap as the content's, and would
    silently start recommending it the day a composer shipped, with the user
    never told a better view had existed all along.
    """
    grammar = _a_grammar(composed=False, producible=False)
    loaded = _binding_with(grammar)
    profile = profile_scope({"WBABusinessApplication": 10}, loaded)
    options = recommend(profile, loaded, intent="the application landscape")
    offered = [o for o in options if o.viewpoint == "ApplicationLandscape"]
    assert offered, "a view that cannot be generated was suppressed"
    assert any("CANNOT BE GENERATED" in r for r in offered[0].reasons)


def test_a_composed_grammar_with_no_composer_keeps_the_original_advice():
    """The one case the original message was written for, and it still fits:
    the geometry IS ours, nobody has built it, so falling back is real advice."""
    grammar = _a_grammar(composed=True, producible=False)
    best, joined = _best_for(grammar)
    assert "is not implemented" in joined
    assert repr(grammar) in joined
    assert "CANNOT BE GENERATED" not in joined
    assert best.candidate.generation_route == advise.ROUTE_COMPOSER_PENDING


def test_a_built_composed_view_carries_no_layout_caveat():
    """Unchanged behavior, guarded: the new branches must not fire on the
    ordinary case."""
    grammar = _a_grammar(composed=True, producible=True)
    best, joined = _best_for(grammar)
    assert best.candidate.generation_route == advise.ROUTE_COMPOSED
    assert "not implemented" not in joined
    assert "CANNOT BE GENERATED" not in joined
    assert "layout operation" not in joined


class _HalfAnsweringBinding:
    """A binding object from before the vocabulary grew: it knows whether a
    layout is implemented and has never heard of the other two questions."""

    class _Viewpoint:
        diagram_type = "Landscape"
        intent = ()
        admits = ("BusinessApplication",)
        effective_grammar = "house-arrangement"
        grammar_is_implemented = False

    technology = "WBA"
    stereotype_prefix = "WBA"
    diagram_types = {}
    viewpoints = {"ApplicationLandscape": _Viewpoint()}


def test_a_binding_that_does_not_answer_producibility_is_not_read_as_silence():
    """A missing property is a missing ANSWER, not "no opinion".

    `getattr(..., None)` cannot tell the two apart, and the difference decides
    whether the advisor promises a diagram it has no grounds to promise.
    """
    loaded = [_HalfAnsweringBinding()]
    profile = profile_scope({"WBABusinessApplication": 10}, loaded,
                            known_concepts={"WBA": {"BusinessApplication"}})
    best = recommend(profile, loaded, intent="the application landscape")[0]
    joined = " ".join(best.reasons)
    assert "no statement of whether" in joined
    assert "not implemented" not in joined
    assert best.candidate.generation_route == advise.ROUTE_UNANSWERED
    assert best.candidate.can_be_generated is None


def _second_binding() -> list:
    return [bindings.load_binding_text("""
technology: OTHER
stereotype_prefix: OTH
diagram_types:
  Estate:
    grammar: graph
    title: frame-header
    sizing:
      default: {w: 100, h: 60}
    routing:
      default: Direct
    channels:
      fill: ~
viewpoints:
  Estate:
    diagram_type: Estate
    admits: [Widget]
""", "other.yaml")]


def test_a_dominant_language_option_also_says_it_cannot_be_generated():
    """The same defect one branch down.

    A mixed scope gets a dominant-language view, which names a viewpoint and a
    diagram type exactly as the conformant path does. Saying nothing about its
    producibility there while saying it here would leave the bug in place for
    every scope that spans two languages.
    """
    grammar = _a_grammar(composed=False, producible=False)
    loaded = _binding_with(grammar) + _second_binding()
    profile = profile_scope({"WBABusinessApplication": 10, "OTHWidget": 8},
                            loaded)
    assert not profile.homogeneous and profile.is_bound
    options = recommend(profile, loaded, intent="everything")
    dominant = next(o for o in options if o.kind == "dominant-language")
    assert "CANNOT BE GENERATED" in " ".join(dominant.reasons)


def test_the_advisor_holds_no_grammar_name_of_its_own():
    """The standing rule, earned twice, in the form that can catch it.

    A module deciding producibility from its own literal list would report the
    same answer on the day a layout shipped. Exact matches rather than
    substrings, so ordinary prose cannot trip it while a lookup table, a
    comparison or a membership test cannot hide.
    """
    tree = ast.parse((_HERE / "advise.py").read_text(encoding="utf-8"))
    literals = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            literals.add(node.value)
        elif isinstance(node, ast.Name):
            literals.add(node.id)
        elif isinstance(node, ast.Attribute):
            literals.add(node.attr)
    leaked = sorted(literals & set(bindings.GRAMMARS))
    assert not leaked, f"advise.py names the grammar(s) {leaked}"

#!/usr/bin/env python3
"""A binding that names things the model does not have must not be able to pass.

Run from the repository root:

    python -m pytest plugins/ai-power-tools/skills/ea-diagram-composition/tools/test_bindings_real_model.py -q

This is the binding-side counterpart of `ruleset-archimate31/tools/test_ruleset_archimate31.py`
(APT-2026-0155), and it exists for the same reason. A binding names a technology id, diagram
types, a stereotype prefix and, in `sizing`, concepts. Every lookup a consumer makes with those
names is an exact string comparison against what EA stored, with no normalization. A name that
EA does not store does not fail: it selects nothing, and the engine falls back to a default as
if the notation had never been described. Nothing in the output tells the two outcomes apart.

So each binding is held to the three checks that guard the ruleset, against the model Sparx
ships with EA, `EAExample.qea`:

  1. the names the binding uses select MORE THAN ZERO diagrams and elements;
  2. every stereotype (or, for the base notation, metatype) the binding names exists;
  3. the wrong form of each name selects NOTHING: the unprefixed form for a binding that states
     a prefix, the technology-qualified `<technology>::<name>` form for one that does not.

NOT HERMETIC, AND DELIBERATELY. The model is read as SQLite from a private copy
(`measure_binding.open_model_copy`); Enterprise Architect is never started. The model is not in
this repository, so every test here skips with a reason when it is absent (CI on Linux), exactly
as the other `EAExample.qea` tests in this folder do. A skip is not a pass.

Eight of the eleven shipped bindings are covered here. The other three are covered by tests that
already compare the binding with this model, and each declares it in its own `COVERS`:
`strategymap.yaml` and `mindmapping.yaml` in `test_bindings_strategy.py`, and
`togaf-diagrams.yaml` in `test_bindings_frameworks.py`.

SCOPE OF "THE WRONG FORM MATCHES NOTHING". It is asserted on the diagrams of the bound diagram
types, because that is where a binding is applied. It is not true model-wide and is not asserted
there: the bare names `Entity` and `Capability` are stereotypes of other notations in the same
model (12 and 110 elements), which is why a prefix-tolerant match would be wrong.

MEASURED ON EAExample.qea, EA 17.1 build 1716, and the reason for each pin below:
  * ArchiMate3 declares five diagram types and the model holds diagrams of three. `Application`
    and `Technology` have none, so nothing can be said about them from this model.
  * `NavigationCell` is EA's own click-through tile, carried by diagrams of several technologies
    and belonging to none of them; it is not part of any notation's vocabulary.
"""
from __future__ import annotations

# Backlog items this module pins (checked by tools/test_suite_conventions.py).
PINS = ("APT-2026-0521",)

# The data assets this module covers (read by tools/register.py).
COVERS = (
    "asset:ea-diagram-composition/bindings/archimate3.yaml",
    "asset:ea-diagram-composition/bindings/bpmn2.0.yaml",
    "asset:ea-diagram-composition/bindings/dmn1.1.yaml",
    "asset:ea-diagram-composition/bindings/erd_dp.yaml",
    "asset:ea-diagram-composition/bindings/sysml1.4.yaml",
    "asset:ea-diagram-composition/bindings/uafp_framework.yaml",
    "asset:ea-diagram-composition/bindings/uml.yaml",
    "asset:ea-diagram-composition/bindings/zf-interface.yaml",
)

import sys
from collections import Counter
from pathlib import Path

import pytest

_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

import measure_binding as mb  # noqa: E402
from bindings import MDG_SEPARATOR, find_binding  # noqa: E402

pytest.importorskip("yaml", reason="PyYAML is required to read bindings")

_BINDINGS = _HERE.parent / "bindings"

#: Technology ids exactly as the bindings declare them. The qualified form is built from the
#: separator, never written as a literal: the release gate reads a literal `<id>::<name>` as an
#: unrecognized MDG namespace.
TECHNOLOGIES = (
    "ArchiMate3", "BPMN2.0", "DMN1.1", "ERD_dp", "SysML1.4", "UAFP_Framework",
    mb.BASE_NOTATION, "ZF Interface",
)

#: Bound diagram types the model holds no diagram of, so there is nothing to select. Pinned as
#: ZERO rather than skipped, so the pin fails the day the model gains one and the exemption is
#: not left behind. This is the model's gap, not the binding's.
NOT_IN_THE_MODEL = {
    ("ArchiMate3", "Application"),
    ("ArchiMate3", "Technology"),
}

#: EA's own navigation tile. Not part of any notation's vocabulary.
NOT_A_CONCEPT = frozenset({"NavigationCell"})

MODEL = mb.resolve_model_path(None)

needs_model = pytest.mark.skipif(
    MODEL is None,
    reason=("EAExample.qea not found - pass its location in "
            f"{mb.MODEL_ENV_VAR}; a machine without EA has nothing to measure"),
)


class _Model:
    """What these tests read from the model, loaded once and the copy closed."""

    def __init__(self, diagrams, known, stereotypes, object_types):
        self.diagrams = diagrams
        self.known = known
        #: `t_object.Stereotype` -> element count, model-wide, empty strings omitted.
        self.stereotypes = stereotypes
        self.object_types = object_types


@pytest.fixture(scope="module")
def model():
    with mb.open_model_copy(MODEL) as conn:
        return _Model(
            mb._load_diagrams(conn),
            mb.list_technologies(conn),
            Counter({s: n for s, n in conn.execute(
                "SELECT Stereotype, COUNT(*) FROM t_object GROUP BY Stereotype")
                if s}),
            Counter({t: n for t, n in conn.execute(
                "SELECT Object_Type, COUNT(*) FROM t_object GROUP BY Object_Type")
                if t}),
        )


def _binding(technology: str):
    found = find_binding(technology, _BINDINGS)
    assert found is not None, f"no binding is shipped for {technology!r}"
    return found


def _is_base(technology: str) -> bool:
    return technology == mb.BASE_NOTATION


def _qualified(technology: str, name: str) -> str:
    return f"{technology}{MDG_SEPARATOR}{name}"


def _diagrams(model, technology: str, diagram_type: str) -> list:
    """The diagrams a bound diagram type applies to.

    An MDG technology's diagrams say so themselves (`MDGDgm=<technology>::<type>`). The base
    notation is the absence of that tag, on a diagram of the base type the binding names.
    """
    if _is_base(technology):
        base = _binding(technology).diagram_types[diagram_type].base
        return [d for d in model.diagrams.values()
                if not d.technology and d.raw_type == base]
    return [d for d in model.diagrams.values()
            if d.technology == technology and d.diagram_type == diagram_type]


def _concept_column(technology: str) -> str:
    """Which `t_object` column holds the concept: the base notation has no stereotype."""
    return "object_type" if _is_base(technology) else "stereotype"


def _named(technology: str, diagram_type: str) -> list:
    """The stored names a diagram type's own `sizing` keys stand for."""
    dt = _binding(technology).diagram_types[diagram_type]
    concepts = [k for k in dt.own_sizing if k != "default"]
    if _is_base(technology):
        return concepts
    return [dt.stereotype_for(c) for c in concepts]


def _vocabulary(model, technology: str, diagram_type: str) -> Counter:
    """Every stored concept on the bound type's diagrams, with its element count."""
    column = _concept_column(technology)
    found: Counter = Counter()
    for d in _diagrams(model, technology, diagram_type):
        for item in d.items:
            name = getattr(item, column)
            if name and name not in NOT_A_CONCEPT:
                found[name] += 1
    return found


def _cases():
    return [(t, name) for t in TECHNOLOGIES
            for name in _binding(t).diagram_types]


def _case_id(case) -> str:
    return _qualified(*case) if not _is_base(case[0]) else f"base::{case[1]}"


CASES = _cases()


# ---------------------------------------------------------------------------
# 1. The names select something
# ---------------------------------------------------------------------------
@needs_model
@pytest.mark.parametrize("technology", TECHNOLOGIES)
def test_the_technology_id_is_the_one_the_model_registers(model, technology):
    """A guessed id resolves to nothing, silently; the model is the arbiter of the real one."""
    if _is_base(technology):
        # EA's base notation is never tagged, so it must not be registered as a technology.
        assert technology not in model.known
        return
    assert technology in model.known, sorted(model.known)


@needs_model
@pytest.mark.parametrize("case", CASES, ids=_case_id)
def test_each_bound_diagram_type_selects_diagrams(model, case):
    technology, diagram_type = case
    selected = _diagrams(model, technology, diagram_type)
    if case in NOT_IN_THE_MODEL:
        assert not selected, (
            f"{_case_id(case)} now has {len(selected)} diagrams in the model: remove it "
            "from NOT_IN_THE_MODEL so it is tested like the rest")
        return
    assert selected, (
        f"{_case_id(case)} selected 0 diagrams in a model that holds "
        f"{sum(model.known.get(technology, {}).values())} of this technology. A binding "
        "that selects nothing is indistinguishable from one that was never written.")


@needs_model
@pytest.mark.parametrize("case", CASES, ids=_case_id)
def test_the_stated_form_matches_more_than_zero_elements(model, case):
    """Counted on the bound diagrams, by the form the binding states.

    For a binding that states a prefix, an element matches when its stored stereotype starts
    with it. For one that states none, the match is any stereotyped element of the notation;
    for the base notation, any element of a metatype the binding names.
    """
    technology, diagram_type = case
    if case in NOT_IN_THE_MODEL:
        pytest.skip(f"{_case_id(case)} has no diagrams in the model; see NOT_IN_THE_MODEL")
    dt = _binding(technology).diagram_types[diagram_type]
    vocabulary = _vocabulary(model, technology, diagram_type)
    if _is_base(technology):
        named = _named(technology, diagram_type)
        if not named:
            pytest.skip(f"{_case_id(case)} names no metatype, so there is nothing to match")
        matched = sum(vocabulary[n] for n in named)
    else:
        matched = sum(n for s, n in vocabulary.items()
                      if s.startswith(dt.stereotype_prefix))
    assert matched > 0, (
        f"{_case_id(case)}: the stated form (prefix {dt.stereotype_prefix!r}) matched 0 "
        f"elements; the diagrams hold {dict(vocabulary)}")


@needs_model
@pytest.mark.parametrize("technology", [t for t in TECHNOLOGIES if not _is_base(t)])
def test_a_stated_prefix_is_the_prefix_the_model_stores(model, technology):
    """The declared prefix, including a declared empty one, equals the measured prefix."""
    binding = _binding(technology)
    checked = 0
    for diagram_type, dt in binding.diagram_types.items():
        if (technology, diagram_type) in NOT_IN_THE_MODEL:
            continue
        measured = mb.measure_diagrams(model.diagrams, model.known, technology,
                                       diagram_type)
        assert measured.stereotype_prefix == dt.stereotype_prefix, (
            _case_id((technology, diagram_type)))
        checked += 1
    assert checked, f"{technology}: no bound diagram type could be measured"


# ---------------------------------------------------------------------------
# 2. Everything the binding names exists
# ---------------------------------------------------------------------------
@needs_model
@pytest.mark.parametrize("technology", TECHNOLOGIES)
def test_every_stereotype_the_binding_names_exists(model, technology):
    """Each `sizing` key, in the form the binding says it is stored.

    An MDG technology is checked on the diagrams of that technology, any of its diagram types:
    the shipped Collaboration type states a size for `DataObject`, and the model places no data
    object on a Collaboration diagram (34 on Business Process diagrams), so asking more of
    that type would test the model's coverage rather than the binding's names. The base notation
    is checked per diagram type, on the metatype.
    """
    named = 0
    if _is_base(technology):
        for diagram_type in _binding(technology).diagram_types:
            present = _vocabulary(model, technology, diagram_type)
            for name in _named(technology, diagram_type):
                named += 1
                assert present[name] > 0, (
                    f"{_case_id((technology, diagram_type))} names metatype {name!r}, which "
                    f"no element on its diagrams has; present: {dict(present)}")
        assert named, "the base notation names no metatype: the parser or the schema moved"
        return

    on_technology: Counter = Counter()
    for d in model.diagrams.values():
        if d.technology == technology:
            on_technology.update(it.stereotype for it in d.items if it.stereotype)
    for diagram_type in _binding(technology).diagram_types:
        for name in _named(technology, diagram_type):
            named += 1
            assert on_technology[name] > 0, (
                f"{technology} {diagram_type} names stereotype {name!r}, which no element "
                f"on a {technology} diagram carries; the model stores "
                f"{sorted(on_technology)}")
    if not named:
        pytest.skip(f"{technology} states no per-concept size, so it names no stereotype "
                    "beyond its prefix, which is checked above")


# ---------------------------------------------------------------------------
# 3. The wrong form matches nothing
# ---------------------------------------------------------------------------
@needs_model
@pytest.mark.parametrize("case", CASES, ids=_case_id)
def test_the_wrong_form_matches_nothing(model, case):
    """The form a reader would guess selects nothing on the bound diagrams.

    A binding that states a prefix: the unprefixed name. One that states none: the
    technology-qualified name, which is how EA records the owning profile elsewhere
    (`t_xref`) and is never what `t_object.Stereotype` holds.
    """
    technology, diagram_type = case
    if case in NOT_IN_THE_MODEL:
        pytest.skip(f"{_case_id(case)} has no diagrams in the model; see NOT_IN_THE_MODEL")
    dt = _binding(technology).diagram_types[diagram_type]
    vocabulary = _vocabulary(model, technology, diagram_type)
    if not vocabulary:
        pytest.skip(f"{_case_id(case)}: no stereotyped element to form a wrong name from")

    if _is_base(technology):
        wrong = {_qualified(technology, name) for name in vocabulary}
        wrong |= {_qualified(technology, n) for n in _named(technology, diagram_type)}
        present = {s for s in model.stereotypes} & wrong
        assert not present, f"stereotypes that no EA model stores: {sorted(present)}"
        return

    on_diagrams = set(vocabulary)
    if dt.stereotype_prefix:
        bare = {s.removeprefix(dt.stereotype_prefix) for s in vocabulary
                if s.startswith(dt.stereotype_prefix)}
        bare |= {n.removeprefix(dt.stereotype_prefix) for n in _named(technology, diagram_type)}
        assert bare, "the prefix was stated but no name carries it"
        collisions = bare & on_diagrams
        assert not collisions, (
            f"{_case_id(case)}: the bare form matched {sorted(collisions)} on its own "
            "diagrams, so the prefix is not part of the stored name")
    qualified = {_qualified(technology, s) for s in vocabulary}
    assert not (qualified & set(model.stereotypes)), (
        f"{_case_id(case)}: the technology-qualified form is stored as a stereotype")

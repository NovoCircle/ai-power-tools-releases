#!/usr/bin/env python3
"""Why there is no SysPhS binding, pinned so the reasons stay checkable.

Run from the repository root:

    python -m pytest ea-diagram-composition/tools/test_bindings_sysphs.py -q

SysPhS - the SysML Extension for Physical Interaction and Signal Flow - was
brought forward to be bound and came back UNBINDABLE. Not "not done yet":
there is no honest binding to write, for three separate reasons that each
stand on their own. An empty finding is easy to mistake for an oversight, so
each reason is a test rather than a note in a backlog item.

1. THE REFERENCE MODEL CARRIES NOT ONE SysPhS DIAGRAM. `measure_binding.py`
   reads the technology ids out of `t_diagram.StyleEx` and SysPhS is not among
   them - the tool refuses the id outright and names the ones that are real.
   So n=0 for every size, every gap and every base type. The first rule of
   this library is that a number nobody measured does not get written down,
   and here there is nothing to measure at all.

2. THE SCHEMA WILL NOT ACCEPT A DIAGRAM TYPE WITH NO NUMBERS IN IT. A binding
   that stated only ids, diagram types and bases and inherited the rest would
   be the right shape for a technology with no data - and `sizing.default` is
   mandatory, so such a document does not load. There is no way to declare a
   diagram type without stating a box size, which for SysPhS could only be
   copied from a neighbor and presented as a measurement.

3. THE DIAGRAMS ALREADY BELONG TO SysML, AND CLAIMING THEM AGAIN BREAKS IT.
   Every SysPhS diagram in the reference corpus is a SysML block definition or
   internal block diagram - the frames read `bdd [package] ...` and
   `ibd [block] ...`, and the elements carry SysML's own `block` and
   `interfaceBlock` stereotypes with the SysPhS profile's variables and
   constants in their compartments. A SysPhS binding declaring diagram types
   by those names would make `resolve_diagram` report every one of the
   reference model's 60 `BlockDefinition` diagrams as AMBIGUOUS, because both
   bindings would claim the name. That is a regression paid for nothing.

WHAT WOULD CHANGE THE ANSWER is data: a model in which SysPhS diagrams are
drawn and tagged, and a diagram type name SysPhS declares as its own. Until
then the five corpus rows want `SysML1.4::InternalBlock` bound - which is
measurable today, 16 diagrams in the reference model - not a binding named
after the profile applied to them.

The last two tests are about the tooling rather than about SysPhS, and they
are here because they are what the choice of parent turned on: a binding whose
`base` names an EA base diagram type must extend the ROOT binding, because an
`extends` chain deeper than one level finds no substrate. That is a real
constraint on every future binding and nothing pinned it before.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

import measure_binding as mb  # noqa: E402
from bindings import (  # noqa: E402
    BindingError,
    find_binding,
    load_binding,
    load_binding_text,
    resolve_diagram,
)

#: The technology id EA itself uses, read from the running install's technology
#: sets rather than guessed, and confirmed loaded through `IsTechnologyLoaded`.
#: Pinned as a constant so that the "absent from the model" tests below cannot
#: quietly start asking about a different spelling.
SYSPHS = "SysPhS"

_BINDINGS = _HERE.parent / "bindings"

MODEL = mb.resolve_model_path(None)

needs_model = pytest.mark.skipif(
    MODEL is None,
    reason=("EAExample.qea not found - pass its location in "
            f"{mb.MODEL_ENV_VAR}; a machine without EA has nothing to measure"),
)


# ---------------------------------------------------------------------------
# 1. There is nothing to measure
# ---------------------------------------------------------------------------
@needs_model
def test_the_reference_model_tags_no_diagram_with_sysphs():
    """n=0, and it is the whole population rather than a thin one.

    `list_technologies` reads every `MDGDgm=<Tech>::<Type>` value in the model.
    SysPhS appears in none of them, under that spelling or any other: the
    substring check is deliberately looser than an equality check, so a
    differently cased or suffixed id would still be caught and this test would
    fail rather than agree with itself.
    """
    with mb.open_model_copy(MODEL) as conn:
        technologies = mb.list_technologies(conn)
    assert technologies, "the model tags no technology at all - wrong model?"
    assert SYSPHS not in technologies
    assert not [tech for tech in technologies if "sysphs" in tech.lower()]


@needs_model
def test_measuring_sysphs_is_refused_rather_than_answered_emptily():
    """The tool says the id is not there instead of returning an empty result.

    Worth pinning because the failure mode this library is built against is a
    lookup on an id nothing carries resolving to nothing SILENTLY. A binding
    author who runs the tool gets told, by name, that there is no population.
    """
    with pytest.raises(Exception) as caught:
        mb.measure_binding(MODEL, SYSPHS)
    message = str(caught.value)
    assert SYSPHS in message
    # And it names real ids, so the author can see what the model does carry.
    assert "SysML1.4" in message


# ---------------------------------------------------------------------------
# 2. The schema has no shape for a technology with no data
# ---------------------------------------------------------------------------
_NO_NUMBERS = """
technology: WBA-Overlay
extends: WBA
diagram_types:
  Overview:
    base: Logical
    grammar: graph
    title: frame-header
    routing: {default: Direct}
    channels:
      fill: ~
      free: [fill]
"""


def test_a_diagram_type_cannot_be_declared_without_a_measured_size():
    """A diagram type still cannot be declared with no size from anywhere.

    SUPERSEDED IN PART: `sizing.default` is no longer mandatory in the
    DOCUMENT. It is now checked on the RESOLVED diagram type, in
    `Binding.__init__` after the merge, so a type that omits it inherits
    the substrate's and a type with nothing above it is still refused.
    What survives here is the second half and it is the half that
    mattered: the figure has to come from somewhere, and inheriting is
    traceable where copying is not.

    So "ids and bases only" DOES load now, provided the substrate supplies a
    default - which reopens this technology's reason 2 and leaves reason 3
    standing on its own. Reason 3 is the decisive one and is untouched: every
    SysPhS diagram in the corpus IS a SysML block-definition or internal-block
    diagram, so a binding declaring those names would make all 60 reference
    `BlockDefinition` diagrams resolve ambiguous. The schema no longer stands in
    this technology's way; the data still does.

    The original rule, for the record:

    This is the rule that turns "SysPhS has no data" into "SysPhS has no
    binding". A document that declared the technology, its diagram types and
    the bases they sit on, and inherited every figure from the substrate, would
    be exactly right for a technology nobody has measured - and the schema
    refuses it at both steps: `sizing` missing, and then `sizing.default`
    missing. Whoever relaxes that should know they are relaxing the one thing
    standing between an unmeasured technology and a copied number.
    """
    with pytest.raises(BindingError) as caught:
        load_binding_text(_NO_NUMBERS, "overlay.yaml")
    assert "sizing" in str(caught.value)

    with_empty_sizing = _NO_NUMBERS.replace(
        "    routing:", "    sizing: {}\n    routing:")
    with pytest.raises(BindingError) as caught:
        load_binding_text(with_empty_sizing, "overlay.yaml")
    assert "sizing.default" in str(caught.value)


# ---------------------------------------------------------------------------
# 3. Claiming SysML's diagram type names would break SysML
# ---------------------------------------------------------------------------
def test_no_sysphs_binding_is_shipped():
    """The deliverable is the absence, so the absence is asserted.

    If a `SysPhS` binding is ever added, this test fails and whoever added it
    has to come here and say which of the three reasons above stopped applying.
    That is the intended cost: the file was left out on evidence, and an
    omission nobody can see is indistinguishable from an oversight.
    """
    assert find_binding(SYSPHS, directory=_BINDINGS) is None
    assert not (_BINDINGS / "sysphs.yaml").exists()


def test_a_second_binding_on_sysmls_diagram_type_names_makes_them_ambiguous(
        tmp_path):
    """Why the file is not merely pointless but harmful.

    `resolve_diagram` matches a diagram's `Diagram_Type` against bound diagram
    type NAMES. The reference model holds 60 diagrams whose type is
    `BlockDefinition`; a SysPhS binding declaring a diagram type of that name -
    which is what the corpus rows would push an author toward, since every one
    of them IS a block definition or internal block diagram - puts two
    claimants on it, and two claimants resolve to nothing at all.

    The qualified path is unharmed, which is exactly what makes this dangerous:
    a diagram that states `MDGDgm=SysML1.4::BlockDefinition` still resolves, so
    the regression hides on the untagged majority.
    """
    for name in ("sysml1.4.yaml", "uml.yaml"):
        (tmp_path / name).write_text(
            (_BINDINGS / name).read_text(encoding="utf-8"), encoding="utf-8")
    (tmp_path / "overlay.yaml").write_text("""
technology: WBA-Overlay
extends: UML
diagram_types:
  BlockDefinition:
    base: Logical
    grammar: graph
    title: frame-header
    sizing: {default: {w: 90, h: 70}}
    routing: {default: Direct}
    channels:
      fill: ~
      free: [fill]
""", encoding="utf-8")

    installed = ["SysML1.4", "WBA-Overlay"]
    clash = resolve_diagram(installed, diagram_type="BlockDefinition",
                            directory=tmp_path)
    assert clash.is_ambiguous and not clash.resolved
    assert clash.candidates == ("SysML1.4::BlockDefinition",
                                "WBA-Overlay::BlockDefinition")

    # Without the second claimant the same diagram resolves outright, so the
    # ambiguity is caused by the added binding and not by the model.
    alone = resolve_diagram(["SysML1.4"], diagram_type="BlockDefinition",
                            directory=tmp_path)
    assert alone.resolved and alone.technology == "SysML1.4"

    # And the qualified path never noticed, which is where the hiding happens.
    qualified = resolve_diagram(
        installed, style_ex="MDGDgm=SysML1.4::BlockDefinition;",
        directory=tmp_path)
    assert qualified.path == "qualified"
    assert qualified.key == "SysML1.4::BlockDefinition"


# ---------------------------------------------------------------------------
# The constraint the choice of parent turned on
# ---------------------------------------------------------------------------
_ROOT = """
technology: WBA
diagram_types:
  Logical:
    base: Logical
    grammar: graph
    title: frame-header
    sizing:
      default: {w: 90, h: 70}
      Package: {w: 148, h: 90}
    spacing: {item_gap_x: 56, item_gap_y: 50}
    routing: {default: Direct}
    channels:
      fill: ~
      free: [fill, border]
"""

_MIDDLE = """
technology: WBA-Systems
extends: WBA
diagram_types:
  BlockDefinition:
    base: Logical
    grammar: layered-bands
    title: frame-header
    sizing: {default: {w: 90, h: 70}}
    spacing: {item_gap_x: 33}
    routing: {default: OrthogonalSquare}
    channels:
      fill: ~
      free: [fill, border]
"""

_LEAF = """
technology: WBA-Physical
extends: {parent}
diagram_types:
  InternalBlock:
    base: Logical
    grammar: graph
    title: frame-header
    sizing: {{default: {{w: 90, h: 70}}}}
    routing: {{default: Direct}}
    channels:
      fill: ~
      free: [fill, border]
"""


def _chain(tmp_path, parent: str):
    (tmp_path / "wba.yaml").write_text(_ROOT, encoding="utf-8")
    (tmp_path / "wba-systems.yaml").write_text(_MIDDLE, encoding="utf-8")
    (tmp_path / "wba-physical.yaml").write_text(
        _LEAF.format(parent=parent), encoding="utf-8")
    return load_binding(tmp_path / "wba-physical.yaml")


def test_extending_a_non_root_binding_finds_no_substrate(tmp_path):
    """A two-level chain does NOT reach the root's measurements.

    `_on_substrate` looks the child's `base` up in its IMMEDIATE parent's
    diagram type catalog, and `_merge` deliberately does not give a child its
    parent's catalog. So a middle binding holds only the diagram types its own
    MDG declares, an EA base type like `Logical` is not among them, and a
    grandchild naming that base inherits NOTHING - every unstated gap falls
    through to the engine's own defaults, silently, which is the failure the
    substrate arrangement exists to prevent.

    This is not a bug to fix here. It is the reason a binding whose `base`
    names a real EA diagram type must extend the ROOT binding directly,
    however close its notation sits to another technology's.
    """
    leaf = _chain(tmp_path, "WBA-Systems")
    drawn_on = leaf.diagram_type("InternalBlock")
    assert drawn_on.substrate == "" and not drawn_on.inherits
    assert drawn_on.spacing == {}
    assert drawn_on.inherited_sizing() == {}


def test_extending_the_root_binding_finds_the_substrate(tmp_path):
    """The same leaf, reparented, inherits both gaps and the concept size.

    The pair is the point: the leaf document is identical apart from one word,
    so the difference is the parent and nothing else.
    """
    leaf = _chain(tmp_path, "WBA")
    drawn_on = leaf.diagram_type("InternalBlock")
    assert drawn_on.substrate == "WBA::Logical" and drawn_on.inherits
    assert drawn_on.spacing == {"item_gap_x": 56, "item_gap_y": 50}
    assert drawn_on.inherited_sizing() == {"Package": {"w": 148, "h": 90}}
    # Its own `default` still wins, which is what makes the inheritance safe.
    assert drawn_on.own_sizing["default"] == {"w": 90, "h": 70}

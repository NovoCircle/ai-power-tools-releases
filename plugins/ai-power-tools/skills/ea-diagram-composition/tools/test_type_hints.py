#!/usr/bin/env python3
"""Every public class and function in the tools modules has annotations that
resolve.

Run from the repository root:

    python -m pytest ea-diagram-composition/tools/test_type_hints.py -q

Hermetic. Imports the modules and evaluates their annotations; nothing
here touches Sparx EA, a repository or a COM object.

WHY THIS EXISTS
---------------
Every module here uses `from __future__ import annotations`, which turns each
annotation into a string that is never evaluated at import time. An annotation
naming a type the module does not import - `Optional[bool]` with no `Optional`
in scope was the real case, on `Viewpoint.grammar_is_implemented` - imports
cleanly, passes every other test, and is simply wrong. It becomes a `NameError`
the first time anything evaluates it: a validator built on class annotations, a
schema generator, `typing.get_type_hints`.

So this evaluates them: each public class's own annotations, and those of every
method and property it defines, and each public module-level function. The
members are not optional. The real case was a property's return annotation,
which `typing.get_type_hints(cls)` does not look at - a class-only check passes
with the defect in place. The modules, classes and functions are all
enumerated, not listed, so one added later is covered without editing this
file.

A failure here is not to be suppressed. If a name is imported only under
`TYPE_CHECKING`, it fails too: import it at runtime, or keep it out of the
annotation.
"""
from __future__ import annotations

import importlib
import inspect
import sys
import typing
from pathlib import Path

import pytest

_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

#: Every tools module, test files excluded.
MODULES = sorted(p.stem for p in _HERE.glob("*.py")
                 if not p.stem.startswith("test_"))


def _public_classes(module_name: str) -> list[type]:
    """Classes the module defines itself, not ones it imports."""
    module = importlib.import_module(module_name)
    return [cls for name, cls in inspect.getmembers(module, inspect.isclass)
            if cls.__module__ == module.__name__ and not name.startswith("_")]


def _public_functions(module_name: str) -> list:
    """Functions the module defines itself, not ones it imports."""
    module = importlib.import_module(module_name)
    return [f for name, f in inspect.getmembers(module, inspect.isfunction)
            if f.__module__ == module.__name__ and not name.startswith("_")]


def _annotated(cls: type):
    """The class itself, then each function it defines, as (label, object)."""
    yield cls.__name__, cls
    for name, attr in vars(cls).items():
        if isinstance(attr, property):
            funcs = [f for f in (attr.fget, attr.fset, attr.fdel) if f]
        elif isinstance(attr, (staticmethod, classmethod)):
            funcs = [attr.__func__]
        elif inspect.isfunction(attr):
            funcs = [attr]
        else:
            continue
        for func in funcs:
            yield f"{cls.__name__}.{name}", func


def test_bindings_is_enumerated():
    # The guard is only as good as the enumeration. A module rename or a
    # filter that matched nothing would leave every case below passing on an
    # empty list.
    assert "bindings" in MODULES
    classes = {cls.__name__: cls for cls in _public_classes("bindings")}
    assert {"Binding", "Viewpoint"} <= set(classes)
    # The member that carried the original defect is reached.
    labels = {label for label, _ in _annotated(classes["Viewpoint"])}
    assert "Viewpoint.grammar_is_implemented" in labels


@pytest.mark.parametrize("module_name", MODULES)
def test_class_annotations_resolve(module_name):
    failures = []
    for cls in _public_classes(module_name):
        for label, obj in _annotated(cls):
            try:
                typing.get_type_hints(obj)
            except Exception as exc:  # NameError is the case; report any
                failures.append(f"{module_name}.{label}: "
                                f"{type(exc).__name__}: {exc}")
    assert not failures, "\n".join(failures)


@pytest.mark.parametrize("module_name", MODULES)
def test_function_annotations_resolve(module_name):
    failures = []
    for func in _public_functions(module_name):
        try:
            typing.get_type_hints(func)
        except Exception as exc:  # NameError is the case; report any
            failures.append(f"{module_name}.{func.__name__}: "
                            f"{type(exc).__name__}: {exc}")
    assert not failures, "\n".join(failures)

from __future__ import annotations

import test_universal_cross_asset_conformance_final_owner_r12_guards as _r12
import test_universal_cross_asset_conformance_final_owner_r49_guards as _r49
from test_universal_cross_asset_conformance_final_owner_r12_guards import (
    _FULL_CLOSURE_ORACLE_PATH,
    _UNKNOWN,
    _Atom,
    _owner_paths,
    _Value,
)


def _r50_exact_static_string(value: _Value, expected: str) -> bool:
    return value == frozenset({_Atom("string", expected)})


class _R50ExactBuiltinsNamespaceDerivationScanner(
    _r49._R49CompleteExactBuiltinsIdentityScanner
):
    def _evaluate_special_call(
        self,
        helper: _Atom,
        arguments: list[_Value],
    ) -> _Value:
        if (
            helper.kind == "helper"
            and helper.text == "vars"
            and len(arguments) == 1
        ):
            if arguments[0] == _r12._BUILTINS_NAMESPACE:
                return _r12._BUILTINS_NAMESPACE
            return _UNKNOWN

        if (
            helper.kind == "helper"
            and helper.text == "getattr"
            and len(arguments) >= 2
            and _r50_exact_static_string(arguments[1], "__dict__")
        ):
            if arguments[0] == _r12._BUILTINS_NAMESPACE:
                return _r12._BUILTINS_NAMESPACE
            return _UNKNOWN

        if (
            helper.kind == "attrgetter"
            and helper.text == "__dict__"
            and len(arguments) == 1
        ):
            if arguments[0] == _r12._BUILTINS_NAMESPACE:
                return _r12._BUILTINS_NAMESPACE
            return _UNKNOWN

        return super()._evaluate_special_call(helper, arguments)


def _r50_dynamic_execution_markers_from_source(source: str) -> tuple[str, ...]:
    return _R50ExactBuiltinsNamespaceDerivationScanner().scan(source)


def test_r50_deepseek_mixed_builtins_vars_does_not_hide_reachable_eval() -> None:
    source = """\
class SafeLookup:
    def __init__(self):
        self.__dict__["Ellipsis"] = 1


def f(a, b):
    return a

flag = False
f(-vars(builtins if flag else SafeLookup())["Ellipsis"], eval("1+1"))
"""

    assert _r50_dynamic_execution_markers_from_source(source) == ("call:9",)


def test_r50_mixed_builtins_getattr_dict_does_not_hide_reachable_eval() -> None:
    source = """\
class SafeLookup:
    def __init__(self):
        self.__dict__["Ellipsis"] = 1


def f(a, b):
    return a

flag = False
f(-getattr(builtins if flag else SafeLookup(), "__dict__").get("Ellipsis"), eval("1+1"))
"""

    assert _r50_dynamic_execution_markers_from_source(source) == ("call:9",)


def test_r50_mixed_builtins_attrgetter_dict_does_not_hide_reachable_eval() -> None:
    source = """\
import operator

class SafeLookup:
    def __init__(self):
        self.__dict__["Ellipsis"] = 1


def f(a, b):
    return a

flag = False
f(-operator.attrgetter("__dict__")(builtins if flag else SafeLookup())["Ellipsis"], eval("1+1"))
"""

    assert _r50_dynamic_execution_markers_from_source(source) == ("call:11",)


def test_r50_exact_builtins_namespace_derivations_preserve_ellipsis_failure() -> None:
    source = """\
def f(*args):
    pass

import builtins
import operator
f(*-vars(builtins)["Ellipsis"], eval("1+1"))
f(*-getattr(builtins, "__dict__").get("Ellipsis"), exec("pass"))
f(*-operator.attrgetter("__dict__")(builtins)["Ellipsis"], __import__("math"))
"""

    assert _r50_dynamic_execution_markers_from_source(source) == ()


def test_r50_complete_owner_and_oracle_surface_has_no_dynamic_execution() -> None:
    paths = (*_owner_paths(), _FULL_CLOSURE_ORACLE_PATH)

    for path in paths:
        assert _r50_dynamic_execution_markers_from_source(
            path.read_text(encoding="utf-8")
        ) == (), path

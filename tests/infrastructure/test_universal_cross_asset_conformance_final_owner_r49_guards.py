from __future__ import annotations

import ast

import test_universal_cross_asset_conformance_final_owner_r15_guards as _r15
import test_universal_cross_asset_conformance_final_owner_r35_guards as _r35
import test_universal_cross_asset_conformance_final_owner_r45_guards as _r45
import test_universal_cross_asset_conformance_final_owner_r48_guards as _r48
from test_universal_cross_asset_conformance_final_owner_r12_guards import (
    _FULL_CLOSURE_ORACLE_PATH,
    _UNKNOWN,
    _Atom,
    _owner_paths,
    _Value,
)


class _R49CompleteExactBuiltinsIdentityScanner(
    _r48._R48ExactBuiltinsIdentityScanner
):
    def _evaluate_attribute(
        self,
        node: ast.Attribute,
        environment: dict[str, _Value],
    ) -> _Value:
        if node.attr == "Ellipsis":
            base = self._scan_expression(node.value, environment)
            if _r35._r35_failed(base):
                return _r35._FAILURE_VALUE
            if _r48._r48_exact_builtins_namespace(base):
                return _r45._ELLIPSIS_VALUE
            return _UNKNOWN
        return super()._evaluate_attribute(node, environment)

    def _evaluate_non_slice_subscript(
        self,
        receiver: _Value,
        key: _Value,
    ) -> _Value:
        if (
            _r15._container_kind(receiver) is None
            and _r45._r45_exact_ellipsis_string(key)
        ):
            if _r48._r48_exact_builtins_namespace(receiver):
                return _r45._ELLIPSIS_VALUE
            return _UNKNOWN
        return super()._evaluate_non_slice_subscript(receiver, key)

    def _evaluate_special_call(
        self,
        helper: _Atom,
        arguments: list[_Value],
    ) -> _Value:
        if (
            helper.kind == "helper"
            and helper.text in {"getattr", "getitem"}
            and len(arguments) >= 2
            and _r15._container_kind(arguments[0]) is None
            and _r45._r45_exact_ellipsis_string(arguments[1])
        ):
            if _r48._r48_exact_builtins_namespace(arguments[0]):
                return _r45._ELLIPSIS_VALUE
            return _UNKNOWN

        if (
            helper.kind == "itemgetter"
            and helper.text == "s:Ellipsis"
            and arguments
            and _r15._container_kind(arguments[0]) is None
        ):
            if _r48._r48_exact_builtins_namespace(arguments[0]):
                return _r45._ELLIPSIS_VALUE
            return _UNKNOWN

        if (
            helper.kind == "attrgetter"
            and helper.text == "Ellipsis"
            and arguments
            and _r15._container_kind(arguments[0]) is None
        ):
            if _r48._r48_exact_builtins_namespace(arguments[0]):
                return _r45._ELLIPSIS_VALUE
            return _UNKNOWN

        return super()._evaluate_special_call(helper, arguments)


def _r49_dynamic_execution_markers_from_source(source: str) -> tuple[str, ...]:
    return _R49CompleteExactBuiltinsIdentityScanner().scan(source)


def test_r49_deepseek_mixed_builtins_subscript_does_not_hide_reachable_eval() -> None:
    source = """\
class SafeLookup:
    def __getitem__(self, key):
        return 1


def f(a, b):
    return a


flag = False
f(-((builtins if flag else SafeLookup())["Ellipsis"]), eval("1+1"))
"""

    assert _r49_dynamic_execution_markers_from_source(source) == ("call:11",)


def test_r49_mixed_builtins_attribute_and_getattr_remain_ambiguous() -> None:
    source = """\
class Safe:
    Ellipsis = 1


def f(a, b):
    return a


flag = False
f(-((builtins if flag else Safe()).Ellipsis), eval("1+1"))
f(-getattr((builtins if flag else Safe()), "Ellipsis"), exec("pass"))
"""

    assert _r49_dynamic_execution_markers_from_source(source) == (
        "call:10",
        "call:11",
    )


def test_r49_mixed_builtins_operator_accessors_remain_ambiguous() -> None:
    source = """\
import operator

class SafeLookup:
    def __getitem__(self, key):
        return 1


class SafeAttr:
    Ellipsis = 1


def f(a, b):
    return a


flag = False
f(-operator.getitem((builtins if flag else SafeLookup()), "Ellipsis"), eval("1+1"))
f(-operator.itemgetter("Ellipsis")(builtins if flag else SafeLookup()), exec("pass"))
f(-operator.attrgetter("Ellipsis")(builtins if flag else SafeAttr()), eval("1+1"))
"""

    assert _r49_dynamic_execution_markers_from_source(source) == (
        "call:17",
        "call:18",
        "call:19",
    )


def test_r49_exact_builtins_accessors_preserve_ellipsis_failure() -> None:
    source = """\
def f(*args):
    pass

import builtins
import operator
f(*-builtins.__dict__["Ellipsis"], eval("1+1"))
f(*+builtins.Ellipsis, exec("pass"))
f(*-getattr(builtins, "Ellipsis"), __import__("math"))
f(*+operator.getitem(builtins.__dict__, "Ellipsis"), eval("1+1"))
f(*-operator.itemgetter("Ellipsis")(builtins.__dict__), exec("pass"))
f(*+operator.attrgetter("Ellipsis")(builtins), __import__("math"))
"""

    assert _r49_dynamic_execution_markers_from_source(source) == ()


def test_r49_complete_owner_and_oracle_surface_has_no_dynamic_execution() -> None:
    paths = (*_owner_paths(), _FULL_CLOSURE_ORACLE_PATH)

    for path in paths:
        assert _r49_dynamic_execution_markers_from_source(
            path.read_text(encoding="utf-8")
        ) == (), path

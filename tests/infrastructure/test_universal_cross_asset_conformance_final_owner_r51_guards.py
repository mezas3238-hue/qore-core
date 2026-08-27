from __future__ import annotations

import ast

import test_universal_cross_asset_conformance_final_owner_r12_guards as _r12
import test_universal_cross_asset_conformance_final_owner_r50_guards as _r50
from test_universal_cross_asset_conformance_final_owner_r12_guards import (
    _FULL_CLOSURE_ORACLE_PATH,
    _UNKNOWN,
    _Atom,
    _contains_kind,
    _owner_paths,
    _Value,
)

_MAPPING_METHOD_NAMES = {"get", "__getitem__"}


def _r51_exact_mapping_method(value: _Value) -> str | None:
    if len(value) != 1:
        return None
    atom = next(iter(value))
    if atom.kind == "string" and atom.text in _MAPPING_METHOD_NAMES:
        return atom.text
    return None


def _r51_exact_builtins_mapping_helper(method: str) -> _Value:
    return frozenset({_Atom("helper", f"builtins-map:{method}")})


class _R51ExactBuiltinsMappingMethodScanner(
    _r50._R50ExactBuiltinsNamespaceDerivationScanner
):
    def _evaluate_attribute(
        self,
        node: ast.Attribute,
        environment: dict[str, _Value],
    ) -> _Value:
        if node.attr in _MAPPING_METHOD_NAMES:
            base = self._scan_expression(node.value, environment)
            if base == _r12._BUILTINS_NAMESPACE:
                return _r51_exact_builtins_mapping_helper(node.attr)
            if _contains_kind(base, "builtins"):
                return _UNKNOWN
        return super()._evaluate_attribute(node, environment)

    def _evaluate_special_call(
        self,
        helper: _Atom,
        arguments: list[_Value],
    ) -> _Value:
        if helper.kind == "helper" and helper.text == "getattr" and len(arguments) >= 2:
            method = _r51_exact_mapping_method(arguments[1])
            if method is not None:
                if arguments[0] == _r12._BUILTINS_NAMESPACE:
                    return _r51_exact_builtins_mapping_helper(method)
                if _contains_kind(arguments[0], "builtins"):
                    return _UNKNOWN

        if helper.kind == "attrgetter" and helper.text in _MAPPING_METHOD_NAMES and arguments:
            if arguments[0] == _r12._BUILTINS_NAMESPACE:
                return _r51_exact_builtins_mapping_helper(helper.text)
            if _contains_kind(arguments[0], "builtins"):
                return _UNKNOWN

        return super()._evaluate_special_call(helper, arguments)


def _r51_dynamic_execution_markers_from_source(source: str) -> tuple[str, ...]:
    return _R51ExactBuiltinsMappingMethodScanner().scan(source)


def test_r51_exact_bound_builtins_get_preserves_ellipsis_failure() -> None:
    source = """\
import builtins

def f(a, b):
    return a

getter = builtins.__dict__.get
f(-getter("Ellipsis"), eval("1+1"))
"""

    assert _r51_dynamic_execution_markers_from_source(source) == ()


def test_r51_exact_bound_builtins_getitem_preserves_ellipsis_failure() -> None:
    source = """\
import builtins

def f(a, b):
    return a

getter = builtins.__dict__.__getitem__
f(-getter("Ellipsis"), eval("1+1"))
"""

    assert _r51_dynamic_execution_markers_from_source(source) == ()


def test_r51_getattr_and_attrgetter_mapping_helpers_are_exact() -> None:
    source = """\
import builtins
import operator

def f(a, b):
    return a

getter = getattr(builtins.__dict__, "get")
getitem = operator.attrgetter("__getitem__")(builtins.__dict__)
f(-getter("Ellipsis"), eval("1+1"))
f(-getitem("Ellipsis"), exec("pass"))
"""

    assert _r51_dynamic_execution_markers_from_source(source) == ()


def test_r51_mixed_builtins_mapping_method_is_not_promoted_to_exact_helper() -> None:
    source = """\
import builtins

def f(a, b):
    return a

flag = False
namespace = builtins.__dict__ if flag else {"Ellipsis": 1}
getter = namespace.get
f(-getter("Ellipsis"), eval("1+1"))
"""

    assert _r51_dynamic_execution_markers_from_source(source) == ("call:9",)


def test_r51_complete_owner_and_oracle_surface_has_no_dynamic_execution() -> None:
    paths = (*_owner_paths(), _FULL_CLOSURE_ORACLE_PATH)

    for path in paths:
        assert _r51_dynamic_execution_markers_from_source(
            path.read_text(encoding="utf-8")
        ) == (), path

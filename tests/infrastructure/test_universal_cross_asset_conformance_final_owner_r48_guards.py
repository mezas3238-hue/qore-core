from __future__ import annotations

import ast

import test_universal_cross_asset_conformance_final_owner_r12_guards as _r12
import test_universal_cross_asset_conformance_final_owner_r15_guards as _r15
import test_universal_cross_asset_conformance_final_owner_r35_guards as _r35
import test_universal_cross_asset_conformance_final_owner_r38_guards as _r38
import test_universal_cross_asset_conformance_final_owner_r39_guards as _r39
import test_universal_cross_asset_conformance_final_owner_r41_guards as _r41
import test_universal_cross_asset_conformance_final_owner_r45_guards as _r45
import test_universal_cross_asset_conformance_final_owner_r47_guards as _r47
from test_universal_cross_asset_conformance_final_owner_r12_guards import (
    _FULL_CLOSURE_ORACLE_PATH,
    _UNKNOWN,
    _owner_paths,
    _Value,
)


def _r48_exact_builtins_namespace(value: _Value) -> bool:
    return value == _r12._BUILTINS_NAMESPACE


class _R48ExactBuiltinsIdentityScanner(
    _r47._R47BooleanUnaryAndBuiltinsLookupScanner
):
    def _evaluate_call(
        self,
        node: ast.Call,
        environment: dict[str, _Value],
    ) -> _Value:
        if (
            isinstance(node.func, ast.Attribute)
            and node.func.attr in {"get", "__getitem__"}
            and node.args
        ):
            receiver = self._scan_expression(node.func.value, environment)
            if _r35._r35_failed(receiver):
                return _r35._FAILURE_VALUE

            kind = _r15._container_kind(receiver)
            if node.func.attr == "get" and kind == "sequence":
                return _r35._FAILURE_VALUE

            arguments, failed = self._scan_call_arguments(node, environment)
            if failed:
                return _r35._FAILURE_VALUE
            if not arguments:
                return _UNKNOWN
            if _r39._r39_has_unknown_positional_shape(arguments):
                return _UNKNOWN

            if kind == "mapping":
                matched, selected = _r41._r41_selected_slots(
                    receiver,
                    arguments[0],
                )
                if matched:
                    return selected
                if not _r41._r41_selection_tokens(receiver, arguments[0]):
                    return _UNKNOWN
                if node.func.attr == "get" and len(arguments) >= 2:
                    return arguments[1]
                return _UNKNOWN

            if kind == "sequence" and node.func.attr == "__getitem__":
                matched, selected = _r38._r38_selected_slots(
                    receiver,
                    arguments[0],
                )
                return selected if matched else _UNKNOWN

            if _r48_exact_builtins_namespace(receiver):
                key = arguments[0]
                if node.func.attr == "get" and len(arguments) >= 2:
                    return _r45._r45_builtins_get_value(key, arguments[1])
                return _r45._r45_builtins_member_value(key)

            return _UNKNOWN

        return super()._evaluate_call(node, environment)


def _r48_dynamic_execution_markers_from_source(source: str) -> tuple[str, ...]:
    return _R48ExactBuiltinsIdentityScanner().scan(source)


def test_r48_deepseek_merged_vars_identity_does_not_suppress_reachable_eval() -> None:
    source = """\
import builtins

def f(a, b):
    return a

flag = False
if flag:
    v = vars
else:
    v = lambda x: {"Ellipsis": 1}

f(-v(builtins).get("Ellipsis"), eval("1+1"))
"""

    assert _r48_dynamic_execution_markers_from_source(source) == ("call:12",)


def test_r48_merged_builtins_namespace_is_not_forced_to_exact_identity() -> None:
    source = """\
import builtins

def f(a, b):
    return a

flag = False
if flag:
    ns = builtins
else:
    ns = object()

f(-ns.get("Ellipsis"), eval("1+1"))
"""

    assert _r48_dynamic_execution_markers_from_source(source) == ("call:12",)


def test_r48_exact_imported_vars_alias_preserves_ellipsis_failure() -> None:
    source = """\
def f(*args):
    pass

import builtins
from builtins import vars as v
f(*-v(builtins).get("Ellipsis"), eval("1+1"))
f(*+v(builtins).__getitem__("Ellipsis"), exec("pass"))
"""

    assert _r48_dynamic_execution_markers_from_source(source) == ()


def test_r48_exact_builtin_namespace_lookup_preserves_ellipsis_failure() -> None:
    source = """\
def f(*args):
    pass

import builtins
f(*-builtins.__dict__.get(*["Ellipsis"]), eval("1+1"))
f(*+builtins.__dict__.__getitem__("Ellipsis"), exec("pass"))
"""

    assert _r48_dynamic_execution_markers_from_source(source) == ()


def test_r48_complete_owner_and_oracle_surface_has_no_dynamic_execution() -> None:
    paths = (*_owner_paths(), _FULL_CLOSURE_ORACLE_PATH)

    for path in paths:
        assert _r48_dynamic_execution_markers_from_source(
            path.read_text(encoding="utf-8")
        ) == (), path

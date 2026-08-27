from __future__ import annotations

import ast

import test_universal_cross_asset_conformance_final_owner_r12_guards as _r12
import test_universal_cross_asset_conformance_final_owner_r15_guards as _r15
import test_universal_cross_asset_conformance_final_owner_r35_guards as _r35
import test_universal_cross_asset_conformance_final_owner_r38_guards as _r38
import test_universal_cross_asset_conformance_final_owner_r39_guards as _r39
import test_universal_cross_asset_conformance_final_owner_r41_guards as _r41
import test_universal_cross_asset_conformance_final_owner_r45_guards as _r45
import test_universal_cross_asset_conformance_final_owner_r51_guards as _r51
from test_universal_cross_asset_conformance_final_owner_r12_guards import (
    _FULL_CLOSURE_ORACLE_PATH,
    _UNKNOWN,
    _Atom,
    _owner_paths,
    _Value,
)

_R52_NON_SEQUENCE_ALTERNATIVE = _Atom("r52-non-sequence-alternative")


def _r52_merge_alternatives(*values: _Value) -> _Value:
    merged = _r12._merge_values(*values)
    has_sequence = any(_r15._container_kind(value) == "sequence" for value in values)
    has_non_sequence = any(
        _r15._container_kind(value) != "sequence" for value in values
    )
    if has_sequence and has_non_sequence:
        return _r12._merge_values(
            merged,
            frozenset({_R52_NON_SEQUENCE_ALTERNATIVE}),
        )
    return merged


def _r52_definitely_sequence(value: _Value) -> bool:
    return (
        _r15._container_kind(value) == "sequence"
        and _R52_NON_SEQUENCE_ALTERNATIVE not in value
    )


class _R52SequenceAlternativeScanner(
    _r51._R51ExactBuiltinsMappingMethodScanner
):
    def _scan_expression(
        self,
        node: ast.AST,
        environment: dict[str, _Value],
    ) -> _Value:
        if isinstance(node, ast.IfExp):
            self._scan_expression(node.test, environment)
            return _r52_merge_alternatives(
                self._scan_expression(node.body, environment),
                self._scan_expression(node.orelse, environment),
            )
        return super()._scan_expression(node, environment)

    def _merge_environments(
        self,
        environment: dict[str, _Value],
        *branches: dict[str, _Value],
    ) -> None:
        names = set(environment)
        for branch in branches:
            names.update(branch)
        for name in names:
            environment[name] = _r52_merge_alternatives(
                *(branch.get(name, _UNKNOWN) for branch in branches)
            )

    def _evaluate_attribute(
        self,
        node: ast.Attribute,
        environment: dict[str, _Value],
    ) -> _Value:
        if node.attr == "get":
            base = self._scan_expression(node.value, environment)
            if _r35._r35_failed(base):
                return _r35._FAILURE_VALUE
            if _r52_definitely_sequence(base):
                return _r35._FAILURE_VALUE
            if base == _r12._BUILTINS_NAMESPACE:
                return _r51._r51_exact_builtins_mapping_helper("get")
            if _r12._contains_kind(base, "builtins"):
                return _UNKNOWN
            return _UNKNOWN
        return super()._evaluate_attribute(node, environment)

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
            if node.func.attr == "get" and _r52_definitely_sequence(receiver):
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

            if receiver == _r12._BUILTINS_NAMESPACE:
                key = arguments[0]
                if node.func.attr == "get" and len(arguments) >= 2:
                    return _r45._r45_builtins_get_value(key, arguments[1])
                return _r45._r45_builtins_member_value(key)

            return _UNKNOWN

        return super()._evaluate_call(node, environment)


def _r52_dynamic_execution_markers_from_source(source: str) -> tuple[str, ...]:
    return _R52SequenceAlternativeScanner().scan(source)


def test_r52_mixed_builtins_sequence_receiver_keeps_later_eval_reachable() -> None:
    source = """\
import builtins

def f(a, b):
    return a

flag = True
f((builtins.__dict__ if flag else [len]).get("Ellipsis"), eval("1+1"))
"""

    assert _r52_dynamic_execution_markers_from_source(source) == ("call:7",)


def test_r52_merged_alias_preserves_non_sequence_alternative() -> None:
    source = """\
import builtins

def f(a, b):
    return a

flag = True
if flag:
    namespace = builtins.__dict__
else:
    namespace = [builtins]

f(namespace.get("Ellipsis"), eval("1+1"))
"""

    assert _r52_dynamic_execution_markers_from_source(source) == ("call:12",)


def test_r52_exact_sequence_get_attribute_fails_before_later_eval() -> None:
    source = """\
def f(a, b):
    return a

f(([],).get, eval("1+1"))
"""

    assert _r52_dynamic_execution_markers_from_source(source) == ()


def test_r52_exact_sequence_containing_builtins_still_fails_get() -> None:
    source = """\
import builtins

def f(a, b):
    return a

f([builtins].get("Ellipsis"), eval("1+1"))
"""

    assert _r52_dynamic_execution_markers_from_source(source) == ()


def test_r52_complete_owner_and_oracle_surface_has_no_dynamic_execution() -> None:
    paths = (*_owner_paths(), _FULL_CLOSURE_ORACLE_PATH)

    for path in paths:
        assert _r52_dynamic_execution_markers_from_source(
            path.read_text(encoding="utf-8")
        ) == (), path

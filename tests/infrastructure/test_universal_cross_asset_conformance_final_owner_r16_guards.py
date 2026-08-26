from __future__ import annotations

import ast
import builtins as _python_builtins

from test_universal_cross_asset_conformance_final_owner_r12_guards import (
    _FULL_CLOSURE_ORACLE_PATH,
    _UNKNOWN,
    _Atom,
    _contains_kind,
    _merge_values,
    _owner_paths,
    _static_strings,
    _Value,
)
from test_universal_cross_asset_conformance_final_owner_r15_guards import (
    _builtins_member_value,
    _R15DynamicExecutionScanner,
)

_PYTHON_BUILTINS_MEMBER_NAMES = frozenset(vars(_python_builtins))


def _r16_builtins_get_value(key: _Value, default: _Value) -> _Value:
    selected_values: list[_Value] = []
    for name in _static_strings(key):
        if name in _PYTHON_BUILTINS_MEMBER_NAMES:
            selected_values.append(
                _builtins_member_value(frozenset({_Atom("string", name)}))
            )
        else:
            selected_values.append(default)
    return _merge_values(*selected_values) if selected_values else _UNKNOWN


class _R16DynamicExecutionScanner(_R15DynamicExecutionScanner):
    def _evaluate_call(
        self,
        node: ast.Call,
        environment: dict[str, _Value],
    ) -> _Value:
        if (
            isinstance(node.func, ast.Attribute)
            and node.func.attr == "get"
            and node.args
        ):
            receiver = self._scan_expression(node.func.value, environment)
            arguments = [
                self._scan_expression(argument, environment)
                for argument in node.args
            ]
            for keyword in node.keywords:
                self._scan_expression(keyword.value, environment)

            if _contains_kind(receiver, "builtins") and len(arguments) >= 2:
                return _r16_builtins_get_value(arguments[0], arguments[1])

        return super()._evaluate_call(node, environment)


def _r16_dynamic_execution_markers_from_source(source: str) -> tuple[str, ...]:
    return _R16DynamicExecutionScanner().scan(source)


def test_r16_direct_builtins_mapping_get_uses_default_for_missing_keys() -> None:
    source = """\
import builtins
builtins.__dict__.get("missing", eval)("1+1")
vars(builtins).get("also_missing", exec)("pass")
builtins.__dict__.get("eval", len)("1+1")
"""

    assert _r16_dynamic_execution_markers_from_source(source) == (
        "call:2",
        "call:3",
        "call:4",
    )


def test_r16_existing_safe_builtins_members_do_not_take_dangerous_default() -> None:
    source = """\
import builtins
builtins.__dict__.get("len", eval)("abc")
vars(builtins).get("str", exec)("abc")
"""

    assert _r16_dynamic_execution_markers_from_source(source) == ()


def test_r16_preserves_itemgetter_string_and_attrgetter_call_regressions() -> None:
    source = """\
import builtins
import operator
operator.itemgetter("getattr")(builtins.__dict__)(builtins, "__import__")("math")
operator.attrgetter("__call__")(eval)("1+1")
"""

    assert _r16_dynamic_execution_markers_from_source(source) == (
        "call:3",
        "call:4",
    )


def test_r16_complete_owner_and_oracle_surface_has_no_dynamic_execution() -> None:
    paths = (*_owner_paths(), _FULL_CLOSURE_ORACLE_PATH)

    for path in paths:
        assert _r16_dynamic_execution_markers_from_source(
            path.read_text(encoding="utf-8")
        ) == (), path

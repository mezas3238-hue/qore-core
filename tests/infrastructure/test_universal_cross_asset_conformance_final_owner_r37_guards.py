from __future__ import annotations

import ast

import test_universal_cross_asset_conformance_final_owner_r35_guards as _r35
from test_universal_cross_asset_conformance_final_owner_r12_guards import (
    _DANGEROUS_CALLABLE,
    _DYNAMIC_EXECUTION_CALL_NAMES,
    _FULL_CLOSURE_ORACLE_PATH,
    _UNKNOWN,
    _contains_kind,
    _integer_value,
    _merge_values,
    _owner_paths,
    _static_strings,
    _Value,
)
from test_universal_cross_asset_conformance_final_owner_r15_guards import (
    _container_kind,
    _selected_slots,
    _selected_static_value,
)
from test_universal_cross_asset_conformance_final_owner_r16_guards import (
    _r16_builtins_get_value,
)


class _R37CallFailureAndIndexScanner(
    _r35._R35SliceFailureAndAssignmentScanner
):
    def _scan_expression(
        self,
        node: ast.AST,
        environment: dict[str, _Value],
    ) -> _Value:
        if isinstance(node, ast.UnaryOp) and isinstance(
            node.op,
            (ast.UAdd, ast.USub),
        ):
            operand = self._scan_expression(node.operand, environment)
            if _r35._r35_failed(operand):
                return _r35._FAILURE_VALUE

            known, scalar = _r35._r35_exact_slice_scalar(operand)
            if known and scalar is not None:
                resolved = scalar if isinstance(node.op, ast.UAdd) else -scalar
                return _integer_value(resolved)
            if known:
                return _r35._FAILURE_VALUE
            return _UNKNOWN

        return super()._scan_expression(node, environment)

    def _evaluate_non_slice_subscript(
        self,
        receiver: _Value,
        key: _Value,
    ) -> _Value:
        handled, selected = _selected_static_value(receiver, key)
        if handled:
            return selected

        if _container_kind(receiver) is not None:
            return _UNKNOWN

        return super()._evaluate_non_slice_subscript(receiver, key)

    def _scan_call_arguments(
        self,
        node: ast.Call,
        environment: dict[str, _Value],
    ) -> tuple[list[_Value], bool]:
        arguments = [_UNKNOWN for _ in node.args]
        ordered: list[tuple[int, int, int, int | None, ast.expr]] = []

        for index, argument in enumerate(node.args):
            ordered.append(
                (
                    getattr(argument, "lineno", node.lineno),
                    getattr(argument, "col_offset", 0),
                    index,
                    index,
                    argument,
                )
            )

        keyword_offset = len(node.args)
        for keyword_index, keyword in enumerate(node.keywords):
            expression = keyword.value
            ordered.append(
                (
                    getattr(expression, "lineno", node.lineno),
                    getattr(expression, "col_offset", 0),
                    keyword_offset + keyword_index,
                    None,
                    expression,
                )
            )

        ordered.sort(key=lambda item: (item[0], item[1], item[2]))

        for _, _, _, argument_index, expression in ordered:
            value = self._scan_expression(expression, environment)
            if _r35._r35_failed(value):
                return arguments, True
            if argument_index is not None:
                arguments[argument_index] = value

        return arguments, False

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

            arguments, failed = self._scan_call_arguments(node, environment)
            if failed:
                return _r35._FAILURE_VALUE

            if (
                node.func.attr == "get"
                and _contains_kind(receiver, "builtins")
                and len(arguments) >= 2
            ):
                return _r16_builtins_get_value(arguments[0], arguments[1])

            if _container_kind(receiver) == "mapping":
                matched, selected = _selected_slots(receiver, arguments[0])
                if matched:
                    return selected
                if node.func.attr == "get" and len(arguments) >= 2:
                    return arguments[1]
                return _UNKNOWN

            handled, selected = _selected_static_value(
                receiver,
                arguments[0],
            )
            if handled:
                return selected

            if _contains_kind(receiver, "builtins"):
                for key in _static_strings(arguments[0]):
                    if key in _DYNAMIC_EXECUTION_CALL_NAMES:
                        return _DANGEROUS_CALLABLE
            return _UNKNOWN

        function = self._scan_expression(node.func, environment)
        if _r35._r35_failed(function):
            return _r35._FAILURE_VALUE

        arguments, failed = self._scan_call_arguments(node, environment)
        if failed:
            return _r35._FAILURE_VALUE

        if _contains_kind(function, "dangerous"):
            self._mark_call(node.lineno)

        results: list[_Value] = []
        for helper in function:
            if helper.kind in {"helper", "itemgetter", "attrgetter"}:
                results.append(self._evaluate_special_call(helper, arguments))
            else:
                results.append(_UNKNOWN)
        return _merge_values(*results)


def _r37_dynamic_execution_markers_from_source(source: str) -> tuple[str, ...]:
    return _R37CallFailureAndIndexScanner().scan(source)


def test_r37_deepseek_call_argument_failure_blocks_later_argument() -> None:
    source = """\
def call_two(a, b):
    return a

for *fns, tail in ((eval, len),):
    call_two(fns[::0], eval("1+1"))
"""

    assert _r37_dynamic_execution_markers_from_source(source) == ()


def test_r37_failure_blocks_later_argument_in_special_mapping_calls() -> None:
    source = """\
for *fns, tail in ((eval, len),):
    {}.get(fns[::0], eval("1+1"))
    {}.__getitem__(fns[::0], eval("1+1"))
"""

    assert _r37_dynamic_execution_markers_from_source(source) == ()


def test_r37_reachable_argument_before_later_failure_remains_marked() -> None:
    source = """\
def call_two(a, b):
    return a

for *fns, tail in ((eval, len),):
    call_two(eval("1+1"), fns[::0])
"""

    assert _r37_dynamic_execution_markers_from_source(source) == ("call:5",)


def test_r37_deepseek_unary_alias_direct_subscript_witness() -> None:
    source = """\
for *fns, tail in ((eval, len),):
    idx = 1
    fns[-idx]("1+1")
"""

    assert _r37_dynamic_execution_markers_from_source(source) == ("call:3",)


def test_r37_unary_alias_operator_accessors_preserve_exact_index() -> None:
    source = """\
import operator
for *fns, tail in ((eval, len),):
    idx = 1
    operator.getitem(fns, -idx)("1+1")
    operator.itemgetter(-idx)(fns)("1+1")
"""

    assert _r37_dynamic_execution_markers_from_source(source) == (
        "call:4",
        "call:5",
    )


def test_r37_unary_alias_safe_direct_selection_stays_unmarked() -> None:
    source = """\
for *fns, tail in ((len, eval),):
    idx = 0
    fns[+idx]("safe")
"""

    assert _r37_dynamic_execution_markers_from_source(source) == ()


def test_r37_deepseek_unselectable_static_mapping_key_does_not_flatten() -> None:
    source = """\
{None: len, "eval": eval}[None]("x")
"""

    assert _r37_dynamic_execution_markers_from_source(source) == ()


def test_r37_exact_supported_mapping_key_still_selects_dangerous_slot() -> None:
    source = """\
{"safe": len, "eval": eval}["eval"]("1+1")
"""

    assert _r37_dynamic_execution_markers_from_source(source) == ("call:1",)


def test_r37_complete_owner_and_oracle_surface_has_no_dynamic_execution() -> None:
    paths = (*_owner_paths(), _FULL_CLOSURE_ORACLE_PATH)

    for path in paths:
        assert _r37_dynamic_execution_markers_from_source(
            path.read_text(encoding="utf-8")
        ) == (), path

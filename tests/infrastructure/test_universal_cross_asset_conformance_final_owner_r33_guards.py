from __future__ import annotations

import ast

import test_universal_cross_asset_conformance_final_owner_r31_guards as _r31
from test_universal_cross_asset_conformance_final_owner_r12_guards import (
    _FULL_CLOSURE_ORACLE_PATH,
    _UNKNOWN,
    _integer_value,
    _owner_paths,
    _Value,
)
from test_universal_cross_asset_conformance_final_owner_r15_guards import (
    _container_kind,
    _selected_slots,
    _sequence_length,
)


class _R33ExactSliceScanner(_r31._R31OrderedBindingScanner):
    def _static_slice_component(
        self,
        node: ast.expr | None,
        environment: dict[str, _Value],
    ) -> tuple[bool, int | None]:
        if node is None:
            return True, None

        scanned = self._scan_expression(node, environment)

        if isinstance(node, ast.Constant) and isinstance(node.value, (bool, int)):
            return True, int(node.value)

        if (
            isinstance(node, ast.UnaryOp)
            and isinstance(node.op, (ast.UAdd, ast.USub))
            and isinstance(node.operand, ast.Constant)
            and isinstance(node.operand.value, (bool, int))
        ):
            literal = int(node.operand.value)
            return True, literal if isinstance(node.op, ast.UAdd) else -literal

        if len(scanned) == 1:
            atom = next(iter(scanned))
            if atom.kind == "integer" and atom.text is not None:
                return True, int(atom.text)

        return False, None

    def _evaluate_subscript(
        self,
        node: ast.Subscript,
        environment: dict[str, _Value],
    ) -> _Value:
        if not isinstance(node.slice, ast.Slice):
            return super()._evaluate_subscript(node, environment)

        receiver = self._scan_expression(node.value, environment)
        lower_known, lower = self._static_slice_component(
            node.slice.lower,
            environment,
        )
        upper_known, upper = self._static_slice_component(
            node.slice.upper,
            environment,
        )
        step_known, step = self._static_slice_component(
            node.slice.step,
            environment,
        )

        if (
            _container_kind(receiver) != "sequence"
            or not lower_known
            or not upper_known
            or not step_known
        ):
            return _UNKNOWN

        length = _sequence_length(receiver)
        if length is None:
            return _UNKNOWN

        try:
            selected_indices = tuple(range(length)[slice(lower, upper, step)])
        except ValueError:
            return _UNKNOWN

        selected_values: list[_Value] = []
        for index in selected_indices:
            matched, selected = _selected_slots(
                receiver,
                _integer_value(index),
            )
            if not matched:
                return _UNKNOWN
            selected_values.append(selected)

        return _r31._r31_sequence_value(tuple(selected_values))


def _r33_dynamic_execution_markers_from_source(source: str) -> tuple[str, ...]:
    return _R33ExactSliceScanner().scan(source)


def test_r33_full_slice_preserves_dangerous_starred_element() -> None:
    source = """\
for *fns, tail in ((eval, len),):
    fns[:][0]("1+1")
"""

    assert _r33_dynamic_execution_markers_from_source(source) == ("call:2",)


def test_r33_bounded_slice_selects_only_reachable_slots() -> None:
    safe_source = """\
for *fns, tail in ((len, eval, str),):
    fns[0:1][0]("x")
"""
    dangerous_source = """\
for *fns, tail in ((len, eval, str),):
    fns[1:2][0]("1+1")
"""

    assert _r33_dynamic_execution_markers_from_source(safe_source) == ()
    assert _r33_dynamic_execution_markers_from_source(dangerous_source) == (
        "call:2",
    )


def test_r33_negative_step_reindexes_exact_starred_sequence() -> None:
    source = """\
for *fns, tail in ((eval, len, str),):
    fns[::-1][1]("1+1")
"""

    assert _r33_dynamic_execution_markers_from_source(source) == ("call:2",)


def test_r33_static_bool_slice_uses_python_index_semantics() -> None:
    source = """\
for *fns, tail in ((eval, len, str),):
    fns[False:True][0]("1+1")
"""

    assert _r33_dynamic_execution_markers_from_source(source) == ("call:2",)


def test_r33_exact_integer_alias_can_bound_slice() -> None:
    source = """\
start = 1
for *fns, tail in ((len, eval, str),):
    fns[start:2][0]("1+1")
"""

    assert _r33_dynamic_execution_markers_from_source(source) == ("call:3",)


def test_r33_dynamic_slice_bound_is_scanned_but_not_assumed_exact() -> None:
    source = """\
for *fns, tail in ((eval, len),):
    fns[eval("0"):][0]("1+1")
"""

    assert _r33_dynamic_execution_markers_from_source(source) == ("call:2",)


def test_r33_zero_step_does_not_make_contained_eval_callable() -> None:
    source = """\
for *fns, tail in ((eval, len),):
    fns[::0][0]("1+1")
"""

    assert _r33_dynamic_execution_markers_from_source(source) == ()


def test_r33_complete_owner_and_oracle_surface_has_no_dynamic_execution() -> None:
    paths = (*_owner_paths(), _FULL_CLOSURE_ORACLE_PATH)

    for path in paths:
        assert _r33_dynamic_execution_markers_from_source(
            path.read_text(encoding="utf-8")
        ) == (), path

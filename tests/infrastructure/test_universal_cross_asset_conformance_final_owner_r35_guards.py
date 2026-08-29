from __future__ import annotations

import ast

import test_universal_cross_asset_conformance_final_owner_r13_guards as _r13
import test_universal_cross_asset_conformance_final_owner_r14_guards as _r14
import test_universal_cross_asset_conformance_final_owner_r31_guards as _r31
import test_universal_cross_asset_conformance_final_owner_r34_guards as _r34
from test_universal_cross_asset_conformance_final_owner_r12_guards import (
    _DYNAMIC_EXECUTION_CALL_NAMES,
    _FULL_CLOSURE_ORACLE_PATH,
    _UNKNOWN,
    _Atom,
    _contains_kind,
    _integer_value,
    _owner_paths,
    _static_strings,
    _Value,
)
from test_universal_cross_asset_conformance_final_owner_r15_guards import (
    _container_kind,
    _selected_slots,
    _selected_static_value,
    _sequence_length,
)

_FAILURE_VALUE = frozenset({_Atom("definite-failure")})
_NONE_VALUE = frozenset({_Atom("none")})


def _r35_failed(value: _Value) -> bool:
    return _contains_kind(value, "definite-failure")


def _r35_exact_slice_scalar(value: _Value) -> tuple[bool, int | None]:
    if len(value) != 1:
        return False, None
    atom = next(iter(value))
    if atom.kind in {"integer", "bool-index"} and atom.text is not None:
        return True, int(atom.text)
    if atom.kind == "none":
        return True, None
    return False, None


def _r35_exact_sequence_items(value: _Value) -> tuple[_Value, ...] | None:
    if _container_kind(value) != "sequence":
        return None
    length = _sequence_length(value)
    if length is None:
        return None

    items: list[_Value] = []
    for index in range(length):
        matched, selected = _selected_slots(value, _integer_value(index))
        if not matched:
            return None
        items.append(selected)
    return tuple(items)


class _R35SliceFailureAndAssignmentScanner(_r34._R34BoolAliasSliceScanner):
    def _scan_expression(
        self,
        node: ast.AST,
        environment: dict[str, _Value],
    ) -> _Value:
        if isinstance(node, ast.Constant) and node.value is None:
            return _NONE_VALUE
        return super()._scan_expression(node, environment)

    def _slice_component_state(
        self,
        node: ast.expr | None,
        environment: dict[str, _Value],
    ) -> tuple[str, int | None]:
        if node is None:
            return "known", None

        if isinstance(node, ast.Constant) and node.value is None:
            return "known", None

        if isinstance(node, ast.UnaryOp) and isinstance(
            node.op,
            (ast.UAdd, ast.USub),
        ):
            operand = self._scan_expression(node.operand, environment)
            if _r35_failed(operand):
                return "failed", None
            known, scalar = _r35_exact_slice_scalar(operand)
            if known and scalar is not None:
                return (
                    "known",
                    scalar if isinstance(node.op, ast.UAdd) else -scalar,
                )
            if known:
                return "failed", None
            return "unknown", None

        scanned = self._scan_expression(node, environment)
        if _r35_failed(scanned):
            return "failed", None

        known, scalar = _r35_exact_slice_scalar(scanned)
        return ("known", scalar) if known else ("unknown", None)

    def _static_slice_component(
        self,
        node: ast.expr | None,
        environment: dict[str, _Value],
    ) -> tuple[bool, int | None]:
        state, scalar = self._slice_component_state(node, environment)
        return state == "known", scalar

    def _evaluate_non_slice_subscript(
        self,
        receiver: _Value,
        key: _Value,
    ) -> _Value:
        handled, selected = _selected_static_value(receiver, key)
        if handled:
            return selected

        result: set[_Atom] = set()
        if _contains_kind(receiver, "dangerous"):
            result.add(_Atom("dangerous"))

        if _contains_kind(receiver, "builtins"):
            for key_value in _static_strings(key):
                if key_value in _DYNAMIC_EXECUTION_CALL_NAMES:
                    result.add(_Atom("dangerous"))
                else:
                    result.add(_Atom("unknown"))

        for index in _r14._static_indices(key):
            if _r13._selects_dangerous_index(receiver, index):
                result.add(_Atom("dangerous"))
            if _r14._selects_builtins_index(receiver, index):
                result.add(_Atom("builtins"))
            if _contains_kind(receiver, "dangerous-key", f"i:{index}"):
                result.add(_Atom("dangerous"))
            if _contains_kind(receiver, "builtins-key", f"i:{index}"):
                result.add(_Atom("builtins"))

        for key_value in _static_strings(key):
            token = f"s:{key_value}"
            if _contains_kind(receiver, "dangerous-key", token):
                result.add(_Atom("dangerous"))
            if _contains_kind(receiver, "builtins-key", token):
                result.add(_Atom("builtins"))

        return frozenset(result) if result else _UNKNOWN

    def _evaluate_subscript(
        self,
        node: ast.Subscript,
        environment: dict[str, _Value],
    ) -> _Value:
        receiver = self._scan_expression(node.value, environment)
        if _r35_failed(receiver):
            return _FAILURE_VALUE

        if not isinstance(node.slice, ast.Slice):
            key = self._scan_expression(node.slice, environment)
            if _r35_failed(key):
                return _FAILURE_VALUE
            return self._evaluate_non_slice_subscript(receiver, key)

        lower_state, lower = self._slice_component_state(
            node.slice.lower,
            environment,
        )
        if lower_state == "failed":
            return _FAILURE_VALUE

        upper_state, upper = self._slice_component_state(
            node.slice.upper,
            environment,
        )
        if upper_state == "failed":
            return _FAILURE_VALUE

        step_state, step = self._slice_component_state(
            node.slice.step,
            environment,
        )
        if step_state == "failed":
            return _FAILURE_VALUE

        if (
            _container_kind(receiver) != "sequence"
            or lower_state != "known"
            or upper_state != "known"
            or step_state != "known"
        ):
            return _UNKNOWN

        length = _sequence_length(receiver)
        if length is None:
            return _UNKNOWN

        try:
            selected_indices = tuple(range(length)[slice(lower, upper, step)])
        except ValueError:
            return _FAILURE_VALUE

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

    def _assign_target(
        self,
        target: ast.AST,
        value: _Value,
        environment: dict[str, _Value],
    ) -> None:
        if not isinstance(target, (ast.Tuple, ast.List)):
            super()._assign_target(target, value, environment)
            return

        items = _r35_exact_sequence_items(value)
        if items is None:
            super()._assign_target(target, value, environment)
            return

        starred = [
            index
            for index, element in enumerate(target.elts)
            if isinstance(element, ast.Starred)
        ]

        if not starred and len(items) == len(target.elts):
            for element, item in zip(target.elts, items, strict=True):
                self._assign_target(element, item, environment)
            return

        if len(starred) == 1:
            starred_index = starred[0]
            fixed_count = len(target.elts) - 1
            if len(items) >= fixed_count:
                trailing = len(target.elts) - starred_index - 1

                for element, item in zip(
                    target.elts[:starred_index],
                    items[:starred_index],
                    strict=True,
                ):
                    self._assign_target(element, item, environment)

                starred_target = target.elts[starred_index]
                assert isinstance(starred_target, ast.Starred)
                star_items = items[
                    starred_index : len(items) - trailing
                    if trailing
                    else len(items)
                ]
                self._assign_target(
                    starred_target.value,
                    _r31._r31_sequence_value(tuple(star_items)),
                    environment,
                )

                suffix_items = items[len(items) - trailing :] if trailing else ()
                for element, item in zip(
                    target.elts[starred_index + 1 :],
                    suffix_items,
                    strict=True,
                ):
                    self._assign_target(element, item, environment)
                return

        super()._assign_target(target, value, environment)


def _r35_dynamic_execution_markers_from_source(source: str) -> tuple[str, ...]:
    return _R35SliceFailureAndAssignmentScanner().scan(source)


def test_r35_deepseek_explicit_none_slice_bound_witness() -> None:
    source = """\
for *fns, tail in ((eval, len),):
    fns[:None][0]("1+1")
"""

    assert _r35_dynamic_execution_markers_from_source(source) == ("call:2",)


def test_r35_none_alias_is_exact_omitted_slice_bound() -> None:
    source = """\
stop = None
for *fns, tail in ((eval, len),):
    fns[:stop][0]("1+1")
"""

    assert _r35_dynamic_execution_markers_from_source(source) == ("call:3",)


def test_r35_deepseek_unary_alias_negative_step_witness() -> None:
    source = """\
for *fns, tail in ((len, eval, str),):
    step = 1
    fns[::-step][0]("1+1")
"""

    assert _r35_dynamic_execution_markers_from_source(source) == ("call:3",)


def test_r35_unary_bool_alias_uses_python_numeric_sign_semantics() -> None:
    source = """\
for *fns, tail in ((len, eval, str),):
    step = True
    fns[::-step][0]("1+1")
"""

    assert _r35_dynamic_execution_markers_from_source(source) == ("call:3",)


def test_r35_deepseek_earlier_slice_failure_suppresses_later_bound() -> None:
    source = """\
for *fns, tail in ((eval, len),):
    fns[fns[::0] : eval("1+1")][0]("1+1")
"""

    assert _r35_dynamic_execution_markers_from_source(source) == ()


def test_r35_prior_bound_executes_before_later_slice_failure() -> None:
    source = """\
for *fns, tail in ((eval, len),):
    fns[
        eval("0"):
        fns[::0]:
        eval("1")
    ][0]("1+1")
"""

    assert _r35_dynamic_execution_markers_from_source(source) == ("call:3",)


def test_r35_deepseek_exact_ordinary_unpack_assignment_witness() -> None:
    source = """\
for *fns, tail in ((len, eval, str),):
    start, inc = True, 1
    fns[start::inc][0]("1+1")
"""

    assert _r35_dynamic_execution_markers_from_source(source) == ("call:3",)


def test_r35_exact_ordinary_unpack_safe_inverse_stays_unmarked() -> None:
    source = """\
for *fns, tail in ((len, eval, str),):
    start, inc = False, 1
    fns[start:1:inc][0]("safe")
"""

    assert _r35_dynamic_execution_markers_from_source(source) == ()


def test_r35_nested_exact_ordinary_unpack_preserves_slot_identity() -> None:
    source = """\
for *fns, tail in ((len, eval, str),):
    start, (inc,) = True, (1,)
    fns[start::inc][0]("1+1")
"""

    assert _r35_dynamic_execution_markers_from_source(source) == ("call:3",)


def test_r35_none_alias_survives_exact_ordinary_unpack() -> None:
    source = """\
stop, step = None, 1
for *fns, tail in ((eval, len),):
    fns[:stop:step][0]("1+1")
"""

    assert _r35_dynamic_execution_markers_from_source(source) == ("call:3",)


def test_r35_complete_owner_and_oracle_surface_has_no_dynamic_execution() -> None:
    paths = (*_owner_paths(), _FULL_CLOSURE_ORACLE_PATH)

    for path in paths:
        assert _r35_dynamic_execution_markers_from_source(
            path.read_text(encoding="utf-8")
        ) == (), path

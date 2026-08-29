from __future__ import annotations

import ast

from test_universal_cross_asset_conformance_final_owner_r12_guards import (
    _FULL_CLOSURE_ORACLE_PATH,
    _UNKNOWN,
    _integer_value,
    _owner_paths,
    _Value,
)
from test_universal_cross_asset_conformance_final_owner_r14_guards import (
    _merge_values,
)
from test_universal_cross_asset_conformance_final_owner_r15_guards import (
    _container_kind,
    _selected_slots,
    _sequence_length,
)
from test_universal_cross_asset_conformance_final_owner_r23_guards import (
    _R23ForIterationScanner,
)


def _r25_sequence_lengths(value: _Value) -> set[int]:
    return {
        int(atom.text)
        for atom in value
        if atom.kind == "sequence-length" and atom.text is not None
    }


def _r25_iterated_value(value: _Value) -> _Value:
    if _container_kind(value) != "sequence":
        return _UNKNOWN

    lengths = {length for length in _r25_sequence_lengths(value) if length > 0}
    if not lengths:
        return _UNKNOWN

    selected_values: list[_Value] = []
    for index in range(max(lengths)):
        if not any(index < length for length in lengths):
            continue
        matched, selected = _selected_slots(value, _integer_value(index))
        if matched:
            selected_values.append(selected)

    return _merge_values(*selected_values) if selected_values else _UNKNOWN


class _R25ExactIterationScanner(_R23ForIterationScanner):
    def _assign_iterated_target(
        self,
        target: ast.AST,
        value: _Value,
        environment: dict[str, _Value],
    ) -> None:
        if not isinstance(target, (ast.Tuple, ast.List)):
            self._assign_target(target, value, environment)
            return

        length = _sequence_length(value)
        if length is None:
            self._assign_target(target, value, environment)
            return

        starred = [
            index
            for index, element in enumerate(target.elts)
            if isinstance(element, ast.Starred)
        ]
        if len(starred) > 1:
            self._assign_target(target, value, environment)
            return

        if not starred:
            if length != len(target.elts):
                self._assign_target(target, value, environment)
                return
            for index, element in enumerate(target.elts):
                matched, selected = _selected_slots(value, _integer_value(index))
                self._assign_iterated_target(
                    element,
                    selected if matched else _UNKNOWN,
                    environment,
                )
            return

        starred_index = starred[0]
        fixed_count = len(target.elts) - 1
        if length < fixed_count:
            self._assign_target(target, value, environment)
            return

        for index, element in enumerate(target.elts[:starred_index]):
            matched, selected = _selected_slots(value, _integer_value(index))
            self._assign_iterated_target(
                element,
                selected if matched else _UNKNOWN,
                environment,
            )

        trailing = len(target.elts) - starred_index - 1
        star_values: list[_Value] = []
        for index in range(starred_index, length - trailing):
            matched, selected = _selected_slots(value, _integer_value(index))
            if matched:
                star_values.append(selected)
        star_value = _merge_values(*star_values) if star_values else _UNKNOWN
        starred_target = target.elts[starred_index]
        assert isinstance(starred_target, ast.Starred)
        self._assign_target(starred_target.value, star_value, environment)

        for offset, element in enumerate(target.elts[starred_index + 1 :], start=1):
            source_index = length - trailing + offset - 1
            matched, selected = _selected_slots(
                value,
                _integer_value(source_index),
            )
            self._assign_iterated_target(
                element,
                selected if matched else _UNKNOWN,
                environment,
            )

    def _scan_comprehension(
        self,
        node: ast.ListComp | ast.SetComp | ast.GeneratorExp | ast.DictComp,
        environment: dict[str, _Value],
    ) -> _Value:
        first_generator = node.generators[0]
        first_iterable = self._scan_expression(first_generator.iter, environment)

        defined_in_class_body = self._class_body_depth > 0
        child_environment = (
            self._class_lexical_environments[-1].copy()
            if defined_in_class_body
            else environment.copy()
        )
        self._scan_assignment_target_execution(
            first_generator.target,
            child_environment,
        )
        self._assign_iterated_target(
            first_generator.target,
            _r25_iterated_value(first_iterable),
            child_environment,
        )

        saved_class_body_depth = self._class_body_depth
        self._class_body_depth = 0
        try:
            for condition in first_generator.ifs:
                self._scan_expression(condition, child_environment)

            for generator in node.generators[1:]:
                iterable = self._scan_expression(generator.iter, child_environment)
                self._scan_assignment_target_execution(
                    generator.target,
                    child_environment,
                )
                self._assign_iterated_target(
                    generator.target,
                    _r25_iterated_value(iterable),
                    child_environment,
                )
                for condition in generator.ifs:
                    self._scan_expression(condition, child_environment)

            if isinstance(node, ast.DictComp):
                self._scan_expression(node.key, child_environment)
                self._scan_expression(node.value, child_environment)
            else:
                self._scan_expression(node.elt, child_environment)
        finally:
            self._class_body_depth = saved_class_body_depth

        return _UNKNOWN

    def _scan_statement(
        self,
        node: ast.stmt,
        environment: dict[str, _Value],
    ) -> None:
        if isinstance(node, ast.For):
            iterable_value = self._scan_expression(node.iter, environment)
            body_environment = environment.copy()
            self._scan_assignment_target_execution(
                node.target,
                body_environment,
            )
            self._assign_iterated_target(
                node.target,
                _r25_iterated_value(iterable_value),
                body_environment,
            )
            self._scan_block(node.body, body_environment)
            else_environment = environment.copy()
            self._scan_block(node.orelse, else_environment)
            self._merge_environments(
                environment,
                environment.copy(),
                body_environment,
                else_environment,
            )
            return

        super()._scan_statement(node, environment)


def _r25_dynamic_execution_markers_from_source(
    source: str,
) -> tuple[str, ...]:
    return _R25ExactIterationScanner().scan(source)


def test_r25_comprehension_propagates_any_exact_sequence_member() -> None:
    source = """\
values = [fn("1+1") for fn in (len, eval)]
"""

    assert _r25_dynamic_execution_markers_from_source(source) == ("call:1",)


def test_r25_comprehension_safe_exact_sequence_remains_unmarked() -> None:
    source = """\
values = [fn("safe") for fn in (len, str)]
"""

    assert _r25_dynamic_execution_markers_from_source(source) == ()


def test_r25_for_keeps_nonempty_divergent_ifexp_lengths() -> None:
    source = """\
for fn in ((eval,) if True else (len, eval)):
    fn("1+1")
"""

    assert _r25_dynamic_execution_markers_from_source(source) == ("call:2",)


def test_r25_for_safe_divergent_ifexp_lengths_remain_unmarked() -> None:
    source = """\
for fn in ((len,) if True else (len, str)):
    fn("safe")
"""

    assert _r25_dynamic_execution_markers_from_source(source) == ()


def test_r25_for_unpacking_distributes_exact_slots_without_flattening() -> None:
    source = """\
for fn, safe in ((len, eval),):
    fn("safe")
"""

    assert _r25_dynamic_execution_markers_from_source(source) == ()


def test_r25_for_unpacking_preserves_dangerous_selected_slot() -> None:
    source = """\
for fn, unsafe in ((len, eval),):
    unsafe("1+1")
"""

    assert _r25_dynamic_execution_markers_from_source(source) == ("call:2",)


def test_r25_nested_for_unpacking_preserves_slot_structure() -> None:
    source = """\
for (fn, unsafe), in (((len, eval),),):
    unsafe("1+1")
"""

    assert _r25_dynamic_execution_markers_from_source(source) == ("call:2",)


def test_r25_complete_owner_and_oracle_surface_has_no_dynamic_execution() -> None:
    paths = (*_owner_paths(), _FULL_CLOSURE_ORACLE_PATH)

    for path in paths:
        assert _r25_dynamic_execution_markers_from_source(
            path.read_text(encoding="utf-8")
        ) == (), path

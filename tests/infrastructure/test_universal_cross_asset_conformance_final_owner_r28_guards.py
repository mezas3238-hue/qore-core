from __future__ import annotations

import ast

import test_universal_cross_asset_conformance_final_owner_r25_guards as _r25
import test_universal_cross_asset_conformance_final_owner_r27_guards as _r27
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
    _selected_slots,
    _sequence_length,
)


class _R28OrderedIterationTargetScanner(_r27._R27IterationTargetScanner):
    def _scan_reachable_target_execution(
        self,
        target: ast.AST,
        value: _Value,
        environment: dict[str, _Value],
    ) -> bool | None:
        if isinstance(target, ast.Name):
            return True

        if isinstance(target, ast.Starred):
            return self._scan_reachable_target_execution(
                target.value,
                value,
                environment,
            )

        if isinstance(target, (ast.Attribute, ast.Subscript)):
            self._scan_assignment_target_execution(target, environment)
            return True

        if not isinstance(target, (ast.Tuple, ast.List)):
            self._scan_assignment_target_execution(target, environment)
            return None

        lengths = _r25._r25_sequence_lengths(value)
        if not lengths:
            if _r27._r27_definitely_non_iterable(value):
                return False
            self._scan_assignment_target_execution(target, environment)
            return None

        starred = [
            index
            for index, element in enumerate(target.elts)
            if isinstance(element, ast.Starred)
        ]
        if len(starred) > 1:
            self._scan_assignment_target_execution(target, environment)
            return None

        if not starred:
            compatibility = {length == len(target.elts) for length in lengths}
        else:
            fixed_count = len(target.elts) - 1
            compatibility = {length >= fixed_count for length in lengths}

        if compatibility == {False}:
            return False

        length = _sequence_length(value)
        if compatibility != {True} or length is None:
            self._scan_assignment_target_execution(target, environment)
            return None

        uncertain = False

        if not starred:
            indexed_targets: list[tuple[int, ast.AST]] = list(
                enumerate(target.elts)
            )
            starred_index: int | None = None
            trailing = 0
        else:
            starred_index = starred[0]
            trailing = len(target.elts) - starred_index - 1
            indexed_targets = list(enumerate(target.elts[:starred_index]))

        for source_index, element in indexed_targets:
            matched, selected = _selected_slots(value, _integer_value(source_index))
            state = self._scan_reachable_target_execution(
                element,
                selected if matched else _UNKNOWN,
                environment,
            )
            if state is False:
                return False
            if state is None:
                uncertain = True

        if starred_index is not None:
            star_values: list[_Value] = []
            for source_index in range(starred_index, length - trailing):
                matched, selected = _selected_slots(
                    value,
                    _integer_value(source_index),
                )
                if matched:
                    star_values.append(selected)
            star_value = _merge_values(*star_values) if star_values else _UNKNOWN
            starred_target = target.elts[starred_index]
            assert isinstance(starred_target, ast.Starred)
            state = self._scan_reachable_target_execution(
                starred_target.value,
                star_value,
                environment,
            )
            if state is False:
                return False
            if state is None:
                uncertain = True

            for offset, element in enumerate(
                target.elts[starred_index + 1 :],
                start=1,
            ):
                source_index = length - trailing + offset - 1
                matched, selected = _selected_slots(
                    value,
                    _integer_value(source_index),
                )
                state = self._scan_reachable_target_execution(
                    element,
                    selected if matched else _UNKNOWN,
                    environment,
                )
                if state is False:
                    return False
                if state is None:
                    uncertain = True

        return None if uncertain else True

    def _assign_iterated_target(
        self,
        target: ast.AST,
        value: _Value,
        environment: dict[str, _Value],
    ) -> None:
        if not isinstance(target, (ast.Tuple, ast.List)):
            super()._assign_iterated_target(target, value, environment)
            return

        length = _sequence_length(value)
        starred = [
            index
            for index, element in enumerate(target.elts)
            if isinstance(element, ast.Starred)
        ]
        if length is None or len(starred) != 1:
            super()._assign_iterated_target(target, value, environment)
            return

        starred_index = starred[0]
        fixed_count = len(target.elts) - 1
        if length < fixed_count:
            super()._assign_iterated_target(target, value, environment)
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
        self._assign_iterated_target(
            starred_target.value,
            star_value,
            environment,
        )

        for offset, element in enumerate(
            target.elts[starred_index + 1 :],
            start=1,
        ):
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
        first_value = _r25._r25_iterated_value(first_iterable)

        defined_in_class_body = self._class_body_depth > 0
        child_environment = (
            self._class_lexical_environments[-1].copy()
            if defined_in_class_body
            else environment.copy()
        )
        first_state = self._scan_reachable_target_execution(
            first_generator.target,
            first_value,
            child_environment,
        )
        if first_state is False:
            return _UNKNOWN
        self._assign_iterated_target(
            first_generator.target,
            first_value,
            child_environment,
        )

        saved_class_body_depth = self._class_body_depth
        self._class_body_depth = 0
        try:
            for condition in first_generator.ifs:
                self._scan_expression(condition, child_environment)

            for generator in node.generators[1:]:
                iterable = self._scan_expression(generator.iter, child_environment)
                iterated_value = _r25._r25_iterated_value(iterable)
                state = self._scan_reachable_target_execution(
                    generator.target,
                    iterated_value,
                    child_environment,
                )
                if state is False:
                    return _UNKNOWN
                self._assign_iterated_target(
                    generator.target,
                    iterated_value,
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
            iterated_value = _r25._r25_iterated_value(iterable_value)
            body_environment = environment.copy()
            state = self._scan_reachable_target_execution(
                node.target,
                iterated_value,
                body_environment,
            )
            if state is False:
                return

            self._assign_iterated_target(
                node.target,
                iterated_value,
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


def _r28_dynamic_execution_markers_from_source(
    source: str,
) -> tuple[str, ...]:
    return _R28OrderedIterationTargetScanner().scan(source)


def test_r28_reviewer_h1_scalar_items_keep_unpack_body_unreachable() -> None:
    source = """\
for fn, safe in ((eval,) if False else (eval, exec)):
    fn("1+1")
"""

    assert _r28_dynamic_execution_markers_from_source(source) == ()


def test_r28_starred_subscript_target_with_dangerous_value_fails_closed() -> None:
    source = """\
bucket = {}
for *bucket["items"], tail in ((eval, len),):
    bucket["items"][0]("1+1")
"""

    assert _r28_dynamic_execution_markers_from_source(source) == ("binding:2",)


def test_r28_prefix_target_expression_executes_before_nested_unpack_failure() -> None:
    source = """\
bucket = {}
for (bucket[eval("1+1")], (fn, safe)) in ((1, (eval,)),):
    pass
"""

    assert _r28_dynamic_execution_markers_from_source(source) == ("call:2",)


def test_r28_later_target_expression_after_prior_failure_stays_unreached() -> None:
    source = """\
bucket = {}
for ((fn, safe), bucket[eval("1+1")]) in (((eval,), 1),):
    pass
"""

    assert _r28_dynamic_execution_markers_from_source(source) == ()


def test_r28_comprehension_prefix_target_expression_executes_before_failure() -> None:
    source = """\
bucket = {}
values = [
    None
    for (bucket[eval("1+1")], (fn, safe)) in ((1, (eval,)),)
]
"""

    assert _r28_dynamic_execution_markers_from_source(source) == ("call:4",)


def test_r28_compatible_starred_name_target_preserves_safe_selection() -> None:
    source = """\
for *safe, fn in ((eval, len),):
    fn("safe")
"""

    assert _r28_dynamic_execution_markers_from_source(source) == ()


def test_r28_complete_owner_and_oracle_surface_has_no_dynamic_execution() -> None:
    paths = (*_owner_paths(), _FULL_CLOSURE_ORACLE_PATH)

    for path in paths:
        assert _r28_dynamic_execution_markers_from_source(
            path.read_text(encoding="utf-8")
        ) == (), path

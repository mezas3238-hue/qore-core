from __future__ import annotations

import ast

import test_universal_cross_asset_conformance_final_owner_r25_guards as _r25
import test_universal_cross_asset_conformance_final_owner_r29_guards as _r29
from test_universal_cross_asset_conformance_final_owner_r12_guards import (
    _FULL_CLOSURE_ORACLE_PATH,
    _UNKNOWN,
    _Atom,
    _contains_kind,
    _integer_value,
    _owner_paths,
    _Value,
)
from test_universal_cross_asset_conformance_final_owner_r14_guards import (
    _merge_values,
)
from test_universal_cross_asset_conformance_final_owner_r15_guards import (
    _container_kind,
    _selected_slot_atom,
    _selected_slots,
    _semantic_atoms,
    _sequence_length,
)


def _r30_sequence_value(values: tuple[_Value, ...]) -> _Value:
    metadata: set[_Atom] = {
        _Atom("container-kind", "sequence"),
        _Atom("sequence-length", str(len(values))),
    }
    for index, value in enumerate(values):
        token = f"i:{index}"
        for value_atom in value:
            metadata.add(_selected_slot_atom(token, value_atom))
        if _contains_kind(value, "dangerous"):
            metadata.add(_Atom("dangerous-index", str(index)))
        if _contains_kind(value, "builtins"):
            metadata.add(_Atom("builtins-index", str(index)))

    flattened = [_semantic_atoms(value) for value in values]
    return _merge_values(*flattened, frozenset(metadata))


def _r30_exact_iteration_items(value: _Value) -> tuple[_Value, ...] | None:
    if _container_kind(value) != "sequence":
        return None

    lengths = _r25._r25_sequence_lengths(value)
    if len(lengths) != 1:
        return None

    length = next(iter(lengths))
    items: list[_Value] = []
    for index in range(length):
        matched, selected = _selected_slots(value, _integer_value(index))
        if not matched:
            return None
        items.append(selected)
    return tuple(items)


class _R30OrderedPerItemIterationScanner(_r29._R29PerItemIterationScanner):
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
            star_values.append(selected if matched else _UNKNOWN)

        starred_target = target.elts[starred_index]
        assert isinstance(starred_target, ast.Starred)
        self._assign_iterated_target(
            starred_target.value,
            _r30_sequence_value(tuple(star_values)),
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

    def _scan_comprehension_result(
        self,
        node: ast.ListComp | ast.SetComp | ast.GeneratorExp | ast.DictComp,
        environment: dict[str, _Value],
    ) -> None:
        if isinstance(node, ast.DictComp):
            self._scan_expression(node.key, environment)
            self._scan_expression(node.value, environment)
        else:
            self._scan_expression(node.elt, environment)

    def _scan_comprehension_generator(
        self,
        node: ast.ListComp | ast.SetComp | ast.GeneratorExp | ast.DictComp,
        generator_index: int,
        environment: dict[str, _Value],
        *,
        precomputed_iterable: _Value | None = None,
    ) -> bool:
        generator = node.generators[generator_index]
        iterable_value = (
            precomputed_iterable
            if precomputed_iterable is not None
            else self._scan_expression(generator.iter, environment)
        )
        items = _r30_exact_iteration_items(iterable_value)

        if items is not None:
            for item_value in items:
                state = self._scan_reachable_target_execution(
                    generator.target,
                    item_value,
                    environment,
                )
                if state is False:
                    return True

                self._assign_iterated_target(
                    generator.target,
                    item_value,
                    environment,
                )
                for condition in generator.ifs:
                    self._scan_expression(condition, environment)

                if generator_index + 1 < len(node.generators):
                    failed = self._scan_comprehension_generator(
                        node,
                        generator_index + 1,
                        environment,
                    )
                    if failed:
                        return True
                else:
                    self._scan_comprehension_result(node, environment)
            return False

        iterated_value = _r25._r25_iterated_value(iterable_value)
        state = self._scan_reachable_target_execution(
            generator.target,
            iterated_value,
            environment,
        )
        if state is False:
            return True

        self._assign_iterated_target(
            generator.target,
            iterated_value,
            environment,
        )
        for condition in generator.ifs:
            self._scan_expression(condition, environment)

        if generator_index + 1 < len(node.generators):
            return self._scan_comprehension_generator(
                node,
                generator_index + 1,
                environment,
            )

        self._scan_comprehension_result(node, environment)
        return False

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

        saved_class_body_depth = self._class_body_depth
        self._class_body_depth = 0
        try:
            self._scan_comprehension_generator(
                node,
                0,
                child_environment,
                precomputed_iterable=first_iterable,
            )
        finally:
            self._class_body_depth = saved_class_body_depth

        return _UNKNOWN

    def _scan_statement(
        self,
        node: ast.stmt,
        environment: dict[str, _Value],
    ) -> None:
        if not isinstance(node, ast.For):
            super()._scan_statement(node, environment)
            return

        iterable_value = self._scan_expression(node.iter, environment)
        items = _r30_exact_iteration_items(iterable_value)

        if items is None:
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

        if not items:
            else_environment = environment.copy()
            self._scan_block(node.orelse, else_environment)
            self._merge_environments(
                environment,
                environment.copy(),
                else_environment,
            )
            return

        loop_environment = environment.copy()
        for item_value in items:
            state = self._scan_reachable_target_execution(
                node.target,
                item_value,
                loop_environment,
            )
            if state is False:
                self._merge_environments(
                    environment,
                    environment.copy(),
                    loop_environment,
                )
                return

            self._assign_iterated_target(
                node.target,
                item_value,
                loop_environment,
            )
            self._scan_block(node.body, loop_environment)

        else_environment = loop_environment.copy()
        self._scan_block(node.orelse, else_environment)
        self._merge_environments(
            environment,
            environment.copy(),
            loop_environment,
            else_environment,
        )


def _r30_dynamic_execution_markers_from_source(source: str) -> tuple[str, ...]:
    return _R30OrderedPerItemIterationScanner().scan(source)


def test_r30_later_comprehension_unpack_failure_keeps_dangerous_item_unreachable() -> None:
    source = """\
values = [fn("1+1") for fn, safe in ((len, str), (eval, len, str))]
"""

    assert _r30_dynamic_execution_markers_from_source(source) == ()


def test_r30_starred_name_capture_preserves_tail_slot_correlation() -> None:
    source = """\
for *safe, tail in ((len, eval), (len, str, exec)):
    for fn in safe:
        fn("1+1")
"""

    assert _r30_dynamic_execution_markers_from_source(source) == ()


def test_r30_starred_name_capture_preserves_reachable_dangerous_values() -> None:
    source = """\
for *fns, tail in ((eval, len), (exec, str, len)):
    for fn in fns:
        fn("1+1")
"""

    assert _r30_dynamic_execution_markers_from_source(source) == ("call:3",)


def test_r30_later_generator_unpack_failure_stops_whole_comprehension() -> None:
    source = """\
values = [
    fn("1+1")
    for outer in (0,)
    for fn, safe in ((len, str), (eval, len, str))
]
"""

    assert _r30_dynamic_execution_markers_from_source(source) == ()


def test_r30_later_generator_reachable_prefix_still_marks_dynamic_call() -> None:
    source = """\
values = [
    fn("1+1")
    for outer in (0,)
    for fn, safe in ((eval, str), (exec, len, str))
]
"""

    assert _r30_dynamic_execution_markers_from_source(source) == ("call:2",)


def test_r30_preserves_r29_sensitive_starred_subscript_binding() -> None:
    source = """\
bucket = {}
for *bucket["items"], tail in ((eval, len), (eval, len, str)):
    bucket["items"][0]("1+1")
"""

    assert _r30_dynamic_execution_markers_from_source(source) == ("binding:2",)


def test_r30_complete_owner_and_oracle_surface_has_no_dynamic_execution() -> None:
    paths = (*_owner_paths(), _FULL_CLOSURE_ORACLE_PATH)

    for path in paths:
        assert _r30_dynamic_execution_markers_from_source(
            path.read_text(encoding="utf-8")
        ) == (), path

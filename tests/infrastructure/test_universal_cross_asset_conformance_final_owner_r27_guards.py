from __future__ import annotations

import ast

import test_universal_cross_asset_conformance_final_owner_r25_guards as _r25
from test_universal_cross_asset_conformance_final_owner_r12_guards import (
    _FULL_CLOSURE_ORACLE_PATH,
    _UNKNOWN,
    _integer_value,
    _owner_paths,
    _Value,
)
from test_universal_cross_asset_conformance_final_owner_r15_guards import (
    _selected_slots,
    _sequence_length,
)


_R27_DEFINITELY_NON_ITERABLE_KINDS = {
    "builtins",
    "dangerous",
    "helper",
    "integer",
    "itemgetter",
    "operator",
    "attrgetter",
}


def _r27_definitely_non_iterable(value: _Value) -> bool:
    return bool(value) and all(
        atom.kind in _R27_DEFINITELY_NON_ITERABLE_KINDS for atom in value
    )


def _r27_target_reachability(target: ast.AST, value: _Value) -> bool | None:
    if not isinstance(target, (ast.Tuple, ast.List)):
        return True

    lengths = _r25._r25_sequence_lengths(value)
    if not lengths:
        return False if _r27_definitely_non_iterable(value) else None

    starred = [
        index
        for index, element in enumerate(target.elts)
        if isinstance(element, ast.Starred)
    ]
    if len(starred) > 1:
        return None

    if not starred:
        compatible = {length == len(target.elts) for length in lengths}
    else:
        fixed_count = len(target.elts) - 1
        compatible = {length >= fixed_count for length in lengths}

    if compatible == {False}:
        return False
    if compatible != {True}:
        return None

    length = _sequence_length(value)
    if length is None:
        return None

    nested_reachability: list[bool | None] = []
    if not starred:
        indexed_targets = list(enumerate(target.elts))
    else:
        starred_index = starred[0]
        trailing = len(target.elts) - starred_index - 1
        indexed_targets = list(enumerate(target.elts[:starred_index]))
        indexed_targets.extend(
            (
                length - trailing + offset,
                element,
            )
            for offset, element in enumerate(target.elts[starred_index + 1 :])
        )

    for source_index, element in indexed_targets:
        matched, selected = _selected_slots(value, _integer_value(source_index))
        if not matched:
            nested_reachability.append(None)
            continue
        nested_reachability.append(_r27_target_reachability(element, selected))

    if any(state is False for state in nested_reachability):
        return False
    if any(state is None for state in nested_reachability):
        return None
    return True


class _R27IterationTargetScanner(_r25._R25ExactIterationScanner):
    def _assign_iterated_target(
        self,
        target: ast.AST,
        value: _Value,
        environment: dict[str, _Value],
    ) -> None:
        if _r27_target_reachability(target, value) is False:
            return

        if isinstance(target, (ast.Attribute, ast.Subscript)):
            if self._is_sensitive_value(value):
                self._mark_binding(target.lineno)
            self._assign_target(target, value, environment)
            return

        super()._assign_iterated_target(target, value, environment)

    def _scan_comprehension(
        self,
        node: ast.ListComp | ast.SetComp | ast.GeneratorExp | ast.DictComp,
        environment: dict[str, _Value],
    ) -> _Value:
        first_generator = node.generators[0]
        first_iterable = self._scan_expression(first_generator.iter, environment)
        first_value = _r25._r25_iterated_value(first_iterable)
        if _r27_target_reachability(first_generator.target, first_value) is False:
            return _UNKNOWN

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
                if _r27_target_reachability(generator.target, iterated_value) is False:
                    return _UNKNOWN
                self._scan_assignment_target_execution(
                    generator.target,
                    child_environment,
                )
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
            if _r27_target_reachability(node.target, iterated_value) is False:
                return

            body_environment = environment.copy()
            self._scan_assignment_target_execution(
                node.target,
                body_environment,
            )
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


def _r27_dynamic_execution_markers_from_source(
    source: str,
) -> tuple[str, ...]:
    return _R27IterationTargetScanner().scan(source)


def test_r27_for_subscript_target_with_dangerous_value_fails_closed() -> None:
    source = """\
bucket = {}
for bucket["fn"] in (eval,):
    bucket["fn"]("1+1")
"""

    assert _r27_dynamic_execution_markers_from_source(source) == ("binding:2",)


def test_r27_for_attribute_target_with_dangerous_value_fails_closed() -> None:
    source = """\
class Box:
    pass
box = Box()
for box.fn in (eval,):
    box.fn("1+1")
"""

    assert _r27_dynamic_execution_markers_from_source(source) == ("binding:4",)


def test_r27_scalar_unpacking_failure_keeps_body_unreachable() -> None:
    source = """\
for fn, safe in (eval,):
    fn("1+1")
"""

    assert _r27_dynamic_execution_markers_from_source(source) == ()


def test_r27_exact_arity_mismatch_keeps_body_unreachable() -> None:
    source = """\
for fn, safe in ((eval,),):
    fn("1+1")
"""

    assert _r27_dynamic_execution_markers_from_source(source) == ()


def test_r27_nested_exact_arity_mismatch_keeps_body_unreachable() -> None:
    source = """\
for (fn, safe), in (((eval,),),):
    fn("1+1")
"""

    assert _r27_dynamic_execution_markers_from_source(source) == ()


def test_r27_unpacking_failure_does_not_scan_unreachable_direct_call() -> None:
    source = """\
for fn, safe in ((eval,),):
    eval("1+1")
"""

    assert _r27_dynamic_execution_markers_from_source(source) == ()


def test_r27_comprehension_unpacking_failure_keeps_element_unreachable() -> None:
    source = """\
values = [fn("1+1") for fn, safe in (eval,)]
"""

    assert _r27_dynamic_execution_markers_from_source(source) == ()


def test_r27_compatible_unpacking_preserves_dangerous_selected_slot() -> None:
    source = """\
for fn, safe in ((eval, len),):
    fn("1+1")
"""

    assert _r27_dynamic_execution_markers_from_source(source) == ("call:2",)


def test_r27_safe_selected_slot_remains_unmarked() -> None:
    source = """\
for fn, unsafe in ((len, eval),):
    fn("safe")
"""

    assert _r27_dynamic_execution_markers_from_source(source) == ()


def test_r27_complete_owner_and_oracle_surface_has_no_dynamic_execution() -> None:
    paths = (*_owner_paths(), _FULL_CLOSURE_ORACLE_PATH)

    for path in paths:
        assert _r27_dynamic_execution_markers_from_source(
            path.read_text(encoding="utf-8")
        ) == (), path

from __future__ import annotations

import ast

import test_universal_cross_asset_conformance_final_owner_r25_guards as _r25
import test_universal_cross_asset_conformance_final_owner_r28_guards as _r28
from test_universal_cross_asset_conformance_final_owner_r12_guards import (
    _FULL_CLOSURE_ORACLE_PATH,
    _integer_value,
    _owner_paths,
    _UNKNOWN,
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


def _r29_common_exact_iteration_prefix(value: _Value) -> tuple[_Value, ...] | None:
    if _container_kind(value) != "sequence":
        return None

    lengths = _r25._r25_sequence_lengths(value)
    if not lengths:
        return None
    if lengths == {0}:
        return ()
    if 0 in lengths:
        return None

    prefix: list[_Value] = []
    for index in range(min(lengths)):
        matched, selected = _selected_slots(value, _integer_value(index))
        if not matched:
            return None
        prefix.append(selected)
    return tuple(prefix)


class _R29PerItemIterationScanner(_r28._R28OrderedIterationTargetScanner):
    def _probe_exact_iteration_prefix(
        self,
        target: ast.AST,
        iterable_value: _Value,
        environment: dict[str, _Value],
    ) -> tuple[tuple[_Value, ...], int | None] | None:
        items = _r29_common_exact_iteration_prefix(iterable_value)
        if items is None:
            return None

        probe_environment = environment.copy()
        for index, item_value in enumerate(items):
            state = self._scan_reachable_target_execution(
                target,
                item_value,
                probe_environment,
            )
            if state is False:
                return items, index

            # Probe each structurally exact reachable item before the R25 merge.
            # This preserves per-item slot/length correlation and lets the R27/R28
            # sensitive Attribute/Subscript rule observe starred values directly.
            self._assign_iterated_target(
                target,
                item_value,
                probe_environment,
            )

        return items, None

    def _scan_comprehension(
        self,
        node: ast.ListComp | ast.SetComp | ast.GeneratorExp | ast.DictComp,
        environment: dict[str, _Value],
    ) -> _Value:
        first_generator = node.generators[0]
        first_iterable = self._scan_expression(first_generator.iter, environment)

        defined_in_class_body = self._class_body_depth > 0
        probe_environment = (
            self._class_lexical_environments[-1].copy()
            if defined_in_class_body
            else environment.copy()
        )
        probe = self._probe_exact_iteration_prefix(
            first_generator.target,
            first_iterable,
            probe_environment,
        )
        if probe is not None:
            items, failure_index = probe
            if not items or failure_index == 0:
                return _UNKNOWN

        # The probe is marker-only for successful positions; the inherited
        # scanner remains the conservative environment model. Its second scan
        # is harmless because final markers are de-duplicated by scan().
        return super()._scan_comprehension(node, environment)

    def _scan_statement(
        self,
        node: ast.stmt,
        environment: dict[str, _Value],
    ) -> None:
        if not isinstance(node, ast.For):
            super()._scan_statement(node, environment)
            return

        iterable_value = self._scan_expression(node.iter, environment)
        probe = self._probe_exact_iteration_prefix(
            node.target,
            iterable_value,
            environment,
        )

        if probe is not None:
            items, failure_index = probe
            if not items:
                else_environment = environment.copy()
                self._scan_block(node.orelse, else_environment)
                self._merge_environments(
                    environment,
                    environment.copy(),
                    else_environment,
                )
                return

            if failure_index == 0:
                return

            if failure_index is not None:
                reachable_value = _merge_values(*items[:failure_index])
                body_environment = environment.copy()
                state = self._scan_reachable_target_execution(
                    node.target,
                    reachable_value,
                    body_environment,
                )
                if state is not False:
                    self._assign_iterated_target(
                        node.target,
                        reachable_value,
                        body_environment,
                    )
                    self._scan_block(node.body, body_environment)
                    self._merge_environments(
                        environment,
                        environment.copy(),
                        body_environment,
                    )
                return

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


def _r29_dynamic_execution_markers_from_source(source: str) -> tuple[str, ...]:
    return _R29PerItemIterationScanner().scan(source)


def test_r29_divergent_starred_subscript_keeps_sensitive_binding() -> None:
    source = """\
bucket = {}
for *bucket["items"], tail in ((eval, len), (eval, len, str)):
    bucket["items"][0]("1+1")
"""

    assert _r29_dynamic_execution_markers_from_source(source) == ("binding:2",)


def test_r29_divergent_starred_subscript_preserves_slot_correlation() -> None:
    source = """\
bucket = {}
for *bucket["items"], tail in ((len, eval), (len, str, exec)):
    pass
"""

    assert _r29_dynamic_execution_markers_from_source(source) == ()


def test_r29_first_iteration_unpack_failure_keeps_body_unreachable() -> None:
    source = """\
for fn, safe in ((eval, len, str), (eval, len)):
    fn("1+1")
"""

    assert _r29_dynamic_execution_markers_from_source(source) == ()


def test_r29_first_iteration_unpack_failure_keeps_else_unreachable() -> None:
    source = """\
for fn, safe in ((len, str, bytes), (len, str)):
    pass
else:
    eval("1+1")
"""

    assert _r29_dynamic_execution_markers_from_source(source) == ()


def test_r29_empty_exact_iterable_skips_body_but_scans_else() -> None:
    source = """\
for fn in ():
    eval("unreachable")
else:
    eval("reachable")
"""

    assert _r29_dynamic_execution_markers_from_source(source) == ("call:4",)


def test_r29_comprehension_first_unpack_failure_keeps_element_unreachable() -> None:
    source = """\
values = [fn("1+1") for fn, safe in ((eval, len, str), (eval, len))]
"""

    assert _r29_dynamic_execution_markers_from_source(source) == ()


def test_r29_comprehension_divergent_starred_subscript_keeps_binding() -> None:
    source = """\
bucket = {}
values = [None for *bucket["items"], tail in ((eval, len), (eval, len, str))]
"""

    assert _r29_dynamic_execution_markers_from_source(source) == ("binding:2",)


def test_r29_complete_owner_and_oracle_surface_has_no_dynamic_execution() -> None:
    paths = (*_owner_paths(), _FULL_CLOSURE_ORACLE_PATH)

    for path in paths:
        assert _r29_dynamic_execution_markers_from_source(
            path.read_text(encoding="utf-8")
        ) == (), path

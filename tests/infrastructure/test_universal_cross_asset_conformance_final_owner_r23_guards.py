from __future__ import annotations

import ast

from test_universal_cross_asset_conformance_final_owner_r12_guards import (
    _FULL_CLOSURE_ORACLE_PATH,
    _UNKNOWN,
    _owner_paths,
    _Value,
)
from test_universal_cross_asset_conformance_final_owner_r15_guards import (
    _container_kind,
    _semantic_atoms,
    _sequence_length,
)
from test_universal_cross_asset_conformance_final_owner_r20c_guards import (
    _R20CClassScopeMutationScanner,
)


def _r23_for_iterated_value(value: _Value) -> _Value:
    if _container_kind(value) != "sequence":
        return _UNKNOWN
    length = _sequence_length(value)
    if length is None or length <= 0:
        return _UNKNOWN
    return _semantic_atoms(value)


class _R23ForIterationScanner(_R20CClassScopeMutationScanner):
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
            self._assign_target(
                node.target,
                _r23_for_iterated_value(iterable_value),
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


def _r23_dynamic_execution_markers_from_source(
    source: str,
) -> tuple[str, ...]:
    return _R23ForIterationScanner().scan(source)


def test_r23_sync_for_propagates_singleton_dangerous_callable() -> None:
    source = """\
for fn in (eval,):
    fn("1+1")
"""

    assert _r23_dynamic_execution_markers_from_source(source) == ("call:2",)


def test_r23_sync_for_propagates_any_dangerous_member_of_exact_sequence() -> None:
    source = """\
for fn in (len, eval):
    fn("1+1")
"""

    assert _r23_dynamic_execution_markers_from_source(source) == ("call:2",)


def test_r23_sync_for_safe_exact_sequence_remains_unmarked() -> None:
    source = """\
for fn in (len,):
    fn("safe")
"""

    assert _r23_dynamic_execution_markers_from_source(source) == ()


def test_r23_async_for_does_not_treat_sync_tuple_as_reachable_iteration() -> None:
    source = """\
async def run():
    async for fn in (eval,):
        fn("1+1")
"""

    assert _r23_dynamic_execution_markers_from_source(source) == ()


def test_r23_complete_owner_and_oracle_surface_has_no_dynamic_execution() -> None:
    paths = (*_owner_paths(), _FULL_CLOSURE_ORACLE_PATH)

    for path in paths:
        assert _r23_dynamic_execution_markers_from_source(
            path.read_text(encoding="utf-8")
        ) == (), path

from __future__ import annotations

import ast

from test_universal_cross_asset_conformance_final_owner_r12_guards import (
    _FULL_CLOSURE_ORACLE_PATH,
    _owner_paths,
    _Value,
)
from test_universal_cross_asset_conformance_final_owner_r20b_guards import (
    _R20BGlobalScopeScanner,
)


class _R20CClassScopeMutationScanner(_R20BGlobalScopeScanner):
    def _scan_statement(
        self,
        node: ast.stmt,
        environment: dict[str, _Value],
    ) -> None:
        if (
            self._annotation_scopes[-1] == "class"
            and isinstance(node, (ast.Global, ast.Nonlocal))
        ):
            self._mark_binding(node.lineno)
            return

        super()._scan_statement(node, environment)


def _r20c_dynamic_execution_markers_from_source(
    source: str,
) -> tuple[str, ...]:
    return _R20CClassScopeMutationScanner().scan(source)


def test_r20c_class_global_mutation_is_fail_closed() -> None:
    source = """\
eval = lambda value: value
class Carrier:
    global eval
    from builtins import eval
eval("1+1")
"""

    assert _r20c_dynamic_execution_markers_from_source(source) == (
        "binding:3",
    )


def test_r20c_class_nonlocal_mutation_is_fail_closed() -> None:
    source = """\
def outer():
    eval = lambda value: value
    class Carrier:
        nonlocal eval
        from builtins import eval
    def inner():
        return eval("1+1")
"""

    assert _r20c_dynamic_execution_markers_from_source(source) == (
        "binding:4",
    )


def test_r20c_function_global_remains_bounded_and_scanned() -> None:
    source = """\
def run():
    global eval
    return eval("1+1")
"""

    assert _r20c_dynamic_execution_markers_from_source(source) == (
        "call:3",
    )


def test_r20c_complete_owner_and_oracle_surface_has_no_dynamic_execution() -> None:
    paths = (*_owner_paths(), _FULL_CLOSURE_ORACLE_PATH)

    for path in paths:
        assert _r20c_dynamic_execution_markers_from_source(
            path.read_text(encoding="utf-8")
        ) == (), path

from __future__ import annotations

import ast

from test_universal_cross_asset_conformance_final_owner_r12_guards import (
    _FULL_CLOSURE_ORACLE_PATH,
    _IMPLICIT_BINDINGS,
    _UNKNOWN,
    _owner_paths,
    _target_names,
    _Value,
)
from test_universal_cross_asset_conformance_final_owner_r19_guards import (
    _r19_function_local_names,
)
from test_universal_cross_asset_conformance_final_owner_r20_guards import (
    _r20_scope_globals,
    _R20DynamicExecutionScanner,
)


class _R20BGlobalScopeScanner(_R20DynamicExecutionScanner):
    def __init__(self) -> None:
        super().__init__()
        self._global_scope_overlays: list[
            tuple[set[str], dict[str, _Value]]
        ] = []

    def scan(self, source: str) -> tuple[str, ...]:
        self._global_scope_overlays = []
        return super().scan(source)

    def _r20b_global_value(self, name: str) -> _Value:
        for declared_globals, global_environment in reversed(
            self._global_scope_overlays
        ):
            if name in declared_globals:
                return global_environment.get(
                    name,
                    _IMPLICIT_BINDINGS.get(name, _UNKNOWN),
                )
        return self._module_environment.get(
            name,
            _IMPLICIT_BINDINGS.get(name, _UNKNOWN),
        )

    def _scan_function(
        self,
        node: ast.FunctionDef | ast.AsyncFunctionDef,
        environment: dict[str, _Value],
    ) -> None:
        for decorator in node.decorator_list:
            self._scan_expression(decorator, environment)
        for default in node.args.defaults:
            self._scan_expression(default, environment)
        for keyword_default in node.args.kw_defaults:
            if keyword_default is not None:
                self._scan_expression(keyword_default, environment)
        if not self._postponed_annotations:
            self._scan_function_annotations(node, environment)

        defined_in_class_body = self._class_body_depth > 0
        child_environment = (
            self._class_lexical_environments[-1].copy()
            if defined_in_class_body
            else environment.copy()
        )
        for name in _r19_function_local_names(node):
            child_environment[name] = _UNKNOWN

        global_names = _r20_scope_globals(node)
        for name in global_names:
            child_environment[name] = self._r20b_global_value(name)

        saved_class_body_depth = self._class_body_depth
        self._class_body_depth = 0
        self._annotation_scopes.append("function")
        self._global_scope_overlays.append(
            (global_names, child_environment)
        )
        try:
            self._scan_block(node.body, child_environment)
        finally:
            self._global_scope_overlays.pop()
            self._annotation_scopes.pop()
            self._class_body_depth = saved_class_body_depth

        environment[node.name] = _UNKNOWN

    def _delete_name(
        self,
        name: str,
        environment: dict[str, _Value],
    ) -> None:
        scope = self._annotation_scopes[-1]
        if scope == "function":
            if (
                self._global_scope_overlays
                and name in self._global_scope_overlays[-1][0]
            ):
                environment.pop(name, None)
            else:
                environment[name] = _UNKNOWN
            return

        if scope == "class" and self._class_lexical_environments:
            lexical_parent = self._class_lexical_environments[-1]
            if name in lexical_parent:
                environment[name] = lexical_parent[name]
            else:
                environment.pop(name, None)
            return

        environment.pop(name, None)

    def _scan_statement(
        self,
        node: ast.stmt,
        environment: dict[str, _Value],
    ) -> None:
        if not isinstance(node, ast.Delete):
            super()._scan_statement(node, environment)
            return

        for target in node.targets:
            self._scan_assignment_target_execution(
                target,
                environment,
            )
            for name in _target_names(target):
                self._delete_name(name, environment)


def _r20b_dynamic_execution_markers_from_source(
    source: str,
) -> tuple[str, ...]:
    return _R20BGlobalScopeScanner().scan(source)


def test_r20b_global_lookup_ignores_intervening_local_after_delete() -> None:
    source = """\
eval = lambda value: value
def outer():
    global eval
    del eval
    def middle():
        eval = lambda value: value
        def inner():
            global eval
            return eval("1+1")
"""

    assert _r20b_dynamic_execution_markers_from_source(source) == (
        "call:9",
    )


def test_r20b_module_delete_restores_builtin_lookup() -> None:
    source = """\
eval = lambda value: value
del eval
eval("1+1")
"""

    assert _r20b_dynamic_execution_markers_from_source(source) == (
        "call:3",
    )


def test_r20b_class_delete_restores_builtin_without_module_binding() -> None:
    source = """\
class Carrier:
    eval = lambda value: value
    del eval
    value = eval("1+1")
"""

    assert _r20b_dynamic_execution_markers_from_source(source) == (
        "call:4",
    )


def test_r20b_class_delete_restores_safe_module_binding() -> None:
    source = """\
eval = lambda value: value
class Carrier:
    eval = exec
    del eval
    value = eval("safe")
"""

    assert _r20b_dynamic_execution_markers_from_source(source) == (
        "binding:3",
    )


def test_r20b_function_local_delete_does_not_fall_back_to_builtin() -> None:
    source = """\
def run():
    eval = lambda value: value
    del eval
    return eval("unbound")
"""

    assert _r20b_dynamic_execution_markers_from_source(source) == ()


def test_r20b_complete_owner_and_oracle_surface_has_no_dynamic_execution() -> None:
    paths = (*_owner_paths(), _FULL_CLOSURE_ORACLE_PATH)

    for path in paths:
        assert _r20b_dynamic_execution_markers_from_source(
            path.read_text(encoding="utf-8")
        ) == (), path

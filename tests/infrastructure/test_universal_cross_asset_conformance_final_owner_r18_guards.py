from __future__ import annotations

import ast

from test_universal_cross_asset_conformance_final_owner_r12_guards import (
    _FULL_CLOSURE_ORACLE_PATH,
    _UNKNOWN,
    _function_local_names,
    _owner_paths,
    _Value,
)
from test_universal_cross_asset_conformance_final_owner_r17_guards import (
    _R17DynamicExecutionScanner,
)


def _uses_postponed_annotations(tree: ast.Module) -> bool:
    return any(
        isinstance(statement, ast.ImportFrom)
        and statement.module == "__future__"
        and any(alias.name == "annotations" for alias in statement.names)
        for statement in tree.body
    )


class _R18DynamicExecutionScanner(_R17DynamicExecutionScanner):
    def __init__(self) -> None:
        super().__init__()
        self._postponed_annotations = False
        self._annotation_scopes: list[str] = ["module"]

    def scan(self, source: str) -> tuple[str, ...]:
        tree = ast.parse(source)
        self._postponed_annotations = _uses_postponed_annotations(tree)
        self._annotation_scopes = ["module"]
        return super().scan(source)

    def _scan_function_annotations(
        self,
        node: ast.FunctionDef | ast.AsyncFunctionDef,
        environment: dict[str, _Value],
    ) -> None:
        for argument in (
            *node.args.posonlyargs,
            *node.args.args,
            *node.args.kwonlyargs,
        ):
            if argument.annotation is not None:
                self._scan_expression(argument.annotation, environment)
        if node.args.vararg is not None and node.args.vararg.annotation is not None:
            self._scan_expression(node.args.vararg.annotation, environment)
        if node.args.kwarg is not None and node.args.kwarg.annotation is not None:
            self._scan_expression(node.args.kwarg.annotation, environment)
        if node.returns is not None:
            self._scan_expression(node.returns, environment)

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

        child_environment = (
            self._class_lexical_environments[-1].copy()
            if self._class_lexical_environments
            else environment.copy()
        )
        for name in _function_local_names(node):
            child_environment[name] = _UNKNOWN

        lexical_environment: dict[str, _Value] | None = None
        if self._class_lexical_environments:
            lexical_environment = self._class_lexical_environments.pop()

        self._annotation_scopes.append("function")
        try:
            self._scan_block(node.body, child_environment)
        finally:
            self._annotation_scopes.pop()
            if lexical_environment is not None:
                self._class_lexical_environments.append(lexical_environment)

        environment[node.name] = _UNKNOWN

    def _scan_statement(
        self,
        node: ast.stmt,
        environment: dict[str, _Value],
    ) -> None:
        if isinstance(node, ast.ClassDef):
            self._annotation_scopes.append("class")
            try:
                super()._scan_statement(node, environment)
            finally:
                self._annotation_scopes.pop()
            return

        if isinstance(node, ast.AnnAssign):
            value = (
                self._scan_expression(node.value, environment)
                if node.value is not None
                else _UNKNOWN
            )
            if self._is_sensitive_value(value):
                self._mark_binding(node.lineno)
            self._assign_target(node.target, value, environment)

            if (
                not self._postponed_annotations
                and self._annotation_scopes[-1] in {"module", "class"}
            ):
                self._scan_expression(node.annotation, environment)
            return

        super()._scan_statement(node, environment)


def _r18_dynamic_execution_markers_from_source(source: str) -> tuple[str, ...]:
    return _R18DynamicExecutionScanner().scan(source)


def test_r18_runtime_evaluated_annotations_are_scanned() -> None:
    source = """\
def parameter(value: eval("1+1")):
    return value

def returns() -> exec("pass"):
    return None

class Carrier:
    value: __import__("math") = 1

module_value: eval("2+2") = 1
"""

    assert _r18_dynamic_execution_markers_from_source(source) == (
        "call:1",
        "call:4",
        "call:8",
        "call:10",
    )


def test_r18_function_local_variable_annotations_are_not_evaluated() -> None:
    source = """\
def safe() -> None:
    local: eval("1+1") = 1
"""

    assert _r18_dynamic_execution_markers_from_source(source) == ()


def test_r18_method_annotations_use_class_execution_scope() -> None:
    source = """\
class Carrier:
    eval = lambda value: value
    def run(self, value: eval("annotation")):
        eval("runtime")
"""

    assert _r18_dynamic_execution_markers_from_source(source) == (
        "call:4",
    )


def test_r18_future_annotations_postpones_annotation_execution() -> None:
    source = """\
from __future__ import annotations

def parameter(value: eval("1+1")) -> exec("pass"):
    return value

class Carrier:
    value: __import__("math") = 1

module_value: eval("2+2") = 1
"""

    assert _r18_dynamic_execution_markers_from_source(source) == ()


def test_r18_future_annotations_does_not_hide_runtime_defaults() -> None:
    source = """\
from __future__ import annotations
def parameter(value: int = eval("1+1")) -> exec("pass"):
    return value
"""

    assert _r18_dynamic_execution_markers_from_source(source) == (
        "call:2",
    )


def test_r18_complete_owner_and_oracle_surface_has_no_dynamic_execution() -> None:
    paths = (*_owner_paths(), _FULL_CLOSURE_ORACLE_PATH)

    for path in paths:
        assert _r18_dynamic_execution_markers_from_source(
            path.read_text(encoding="utf-8")
        ) == (), path

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
from test_universal_cross_asset_conformance_final_owner_r18_guards import (
    _uses_postponed_annotations,
)
from test_universal_cross_asset_conformance_final_owner_r19_guards import (
    _r19_function_local_names,
    _r19_iterated_value,
    _r19_lambda_local_names,
    _R19DynamicExecutionScanner,
    _R19LocalBindingCollector,
)


def _r20_scope_globals(
    node: ast.FunctionDef | ast.AsyncFunctionDef,
) -> set[str]:
    collector = _R19LocalBindingCollector()
    for statement in node.body:
        collector.visit(statement)
    return collector.global_names


class _R20DynamicExecutionScanner(_R19DynamicExecutionScanner):
    def __init__(self) -> None:
        super().__init__()
        self._module_environment: dict[str, _Value] = {}
        self._function_global_stack: list[set[str]] = []
        self._class_body_depth = 0

    def scan(self, source: str) -> tuple[str, ...]:
        tree = ast.parse(source)
        self._markers.clear()
        self._postponed_annotations = _uses_postponed_annotations(tree)
        self._annotation_scopes = ["module"]
        self._class_lexical_environments = []
        self._function_global_stack = []
        self._class_body_depth = 0
        self._module_environment = dict(_IMPLICIT_BINDINGS)
        self._scan_block(tree.body, self._module_environment)
        return tuple(dict.fromkeys(self._markers))

    def _global_value(
        self,
        name: str,
        definition_environment: dict[str, _Value],
    ) -> _Value:
        if any(
            name in declared_globals
            for declared_globals in reversed(self._function_global_stack)
        ):
            return definition_environment.get(
                name,
                self._module_environment.get(
                    name,
                    _IMPLICIT_BINDINGS.get(name, _UNKNOWN),
                ),
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
            child_environment[name] = self._global_value(
                name,
                environment,
            )

        saved_class_body_depth = self._class_body_depth
        self._class_body_depth = 0
        self._annotation_scopes.append("function")
        self._function_global_stack.append(global_names)
        try:
            self._scan_block(node.body, child_environment)
        finally:
            self._function_global_stack.pop()
            self._annotation_scopes.pop()
            self._class_body_depth = saved_class_body_depth

        environment[node.name] = _UNKNOWN

    def _scan_lambda(
        self,
        node: ast.Lambda,
        environment: dict[str, _Value],
    ) -> _Value:
        for default in node.args.defaults:
            self._scan_expression(default, environment)
        for keyword_default in node.args.kw_defaults:
            if keyword_default is not None:
                self._scan_expression(keyword_default, environment)

        defined_in_class_body = self._class_body_depth > 0
        child_environment = (
            self._class_lexical_environments[-1].copy()
            if defined_in_class_body
            else environment.copy()
        )
        for name in _r19_lambda_local_names(node):
            child_environment[name] = _UNKNOWN

        saved_class_body_depth = self._class_body_depth
        self._class_body_depth = 0
        try:
            self._scan_expression(node.body, child_environment)
        finally:
            self._class_body_depth = saved_class_body_depth
        return _UNKNOWN

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
        self._assign_target(
            first_generator.target,
            _r19_iterated_value(first_iterable),
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
                self._assign_target(
                    generator.target,
                    _r19_iterated_value(iterable),
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

    def _scan_class(
        self,
        node: ast.ClassDef,
        environment: dict[str, _Value],
    ) -> None:
        for decorator in node.decorator_list:
            self._scan_expression(decorator, environment)
        for base in node.bases:
            self._scan_expression(base, environment)
        for keyword in node.keywords:
            self._scan_expression(keyword.value, environment)

        lexical_parent = (
            self._class_lexical_environments[-1]
            if self._class_body_depth > 0
            else environment
        )
        class_environment = lexical_parent.copy()
        self._class_lexical_environments.append(lexical_parent.copy())
        self._class_body_depth += 1
        self._annotation_scopes.append("class")
        try:
            self._scan_block(node.body, class_environment)
        finally:
            self._annotation_scopes.pop()
            self._class_body_depth -= 1
            self._class_lexical_environments.pop()

        environment[node.name] = _UNKNOWN

    def _scan_assignment_target_execution(
        self,
        target: ast.AST,
        environment: dict[str, _Value],
    ) -> None:
        if isinstance(target, ast.Name):
            return
        if isinstance(target, ast.Starred):
            self._scan_assignment_target_execution(target.value, environment)
            return
        if isinstance(target, (ast.Tuple, ast.List)):
            for element in target.elts:
                self._scan_assignment_target_execution(element, environment)
            return
        if isinstance(target, ast.Attribute):
            self._scan_expression(target.value, environment)
            return
        if isinstance(target, ast.Subscript):
            self._scan_expression(target.value, environment)
            self._scan_expression(target.slice, environment)

    def _scan_statement(
        self,
        node: ast.stmt,
        environment: dict[str, _Value],
    ) -> None:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            self._scan_function(node, environment)
            return

        if isinstance(node, ast.ClassDef):
            self._scan_class(node, environment)
            return

        if isinstance(node, ast.Assign):
            value = self._scan_expression(node.value, environment)
            if self._is_sensitive_value(value):
                self._mark_binding(node.lineno)
            for target in node.targets:
                self._scan_assignment_target_execution(target, environment)
                self._assign_target(target, value, environment)
            return

        if isinstance(node, ast.AnnAssign):
            if node.value is not None:
                value = self._scan_expression(node.value, environment)
                if self._is_sensitive_value(value):
                    self._mark_binding(node.lineno)
                self._scan_assignment_target_execution(node.target, environment)
                self._assign_target(node.target, value, environment)
            else:
                self._scan_assignment_target_execution(node.target, environment)

            if (
                not self._postponed_annotations
                and self._annotation_scopes[-1] in {"module", "class"}
            ):
                self._scan_expression(node.annotation, environment)
            return

        if isinstance(node, (ast.For, ast.AsyncFor)):
            self._scan_expression(node.iter, environment)
            body_environment = environment.copy()
            self._scan_assignment_target_execution(
                node.target,
                body_environment,
            )
            self._assign_target(node.target, _UNKNOWN, body_environment)
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

        if isinstance(node, (ast.With, ast.AsyncWith)):
            for item in node.items:
                self._scan_expression(item.context_expr, environment)
                if item.optional_vars is not None:
                    self._scan_assignment_target_execution(
                        item.optional_vars,
                        environment,
                    )
                    self._assign_target(
                        item.optional_vars,
                        _UNKNOWN,
                        environment,
                    )
            self._scan_block(node.body, environment)
            return

        if isinstance(node, ast.Delete):
            for target in node.targets:
                self._scan_assignment_target_execution(target, environment)
                for name in _target_names(target):
                    environment[name] = _UNKNOWN
            return

        super()._scan_statement(node, environment)


def _r20_dynamic_execution_markers_from_source(source: str) -> tuple[str, ...]:
    return _R20DynamicExecutionScanner().scan(source)


def test_r20_rejects_nested_global_closure_false_negative() -> None:
    source = """\
def outer():
    eval = lambda value: value
    def inner():
        global eval
        return eval("1+1")
"""

    assert _r20_dynamic_execution_markers_from_source(source) == ("call:5",)


def test_r20_nested_global_uses_active_outer_global_state_when_declared() -> None:
    source = """\
def outer():
    global eval
    eval = lambda value: value
    def inner():
        global eval
        return eval("safe")
"""

    assert _r20_dynamic_execution_markers_from_source(source) == ()


def test_r20_method_lambda_and_comprehension_close_over_method_locals() -> None:
    source = """\
class Outer:
    class Inner:
        def run(self):
            eval = lambda value: value
            fn = lambda: eval("safe")
            values = [eval("safe") for _ in (0,)]
            return fn, values
"""

    assert _r20_dynamic_execution_markers_from_source(source) == ()


def test_r20_class_body_lambda_still_uses_lexical_parent() -> None:
    source = """\
class Carrier:
    eval = lambda value: value
    fn = lambda: eval("1+1")
"""

    assert _r20_dynamic_execution_markers_from_source(source) == ("call:3",)


def test_r20_valued_annassign_keeps_python_rhs_binding_annotation_order() -> None:
    source = """\
eval: eval("safe") = lambda value: value
"""

    assert _r20_dynamic_execution_markers_from_source(source) == ()


def test_r20_assignment_target_expressions_are_scanned() -> None:
    source = """\
bucket = {}
bucket[eval("'assign'")] = 1
bucket[exec("pass")]: int
del bucket[__import__("math").__name__]
for bucket[eval("'loop'")] in (1,):
    pass
"""

    assert _r20_dynamic_execution_markers_from_source(source) == (
        "call:2",
        "call:3",
        "call:4",
        "call:5",
    )


def test_r20_with_and_comprehension_target_expressions_are_scanned() -> None:
    source = """\
from contextlib import nullcontext
bucket = {}
with nullcontext(1) as bucket[eval("'with'")]:
    pass
values = [None for bucket[exec("'comp'")] in (1,)]
"""

    assert _r20_dynamic_execution_markers_from_source(source) == (
        "call:3",
        "call:5",
    )


def test_r20_safe_assignment_targets_remain_unmarked() -> None:
    source = """\
bucket = {}
bucket["assign"] = 1
bucket["typed"]: int
for bucket["loop"] in (1,):
    pass
"""

    assert _r20_dynamic_execution_markers_from_source(source) == ()


def test_r20_complete_owner_and_oracle_surface_has_no_dynamic_execution() -> None:
    paths = (*_owner_paths(), _FULL_CLOSURE_ORACLE_PATH)

    for path in paths:
        assert _r20_dynamic_execution_markers_from_source(
            path.read_text(encoding="utf-8")
        ) == (), path

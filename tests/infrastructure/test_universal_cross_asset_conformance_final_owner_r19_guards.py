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
from test_universal_cross_asset_conformance_final_owner_r18_guards import (
    _R18DynamicExecutionScanner,
)


class _R19LocalBindingCollector(ast.NodeVisitor):
    def __init__(self) -> None:
        self.names: set[str] = set()
        self.global_names: set[str] = set()
        self.nonlocal_names: set[str] = set()

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self.names.add(node.name)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self.names.add(node.name)

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        self.names.add(node.name)

    def visit_Lambda(self, node: ast.Lambda) -> None:
        return

    def visit_Name(self, node: ast.Name) -> None:
        if isinstance(node.ctx, (ast.Store, ast.Del)):
            self.names.add(node.id)

    def visit_Import(self, node: ast.Import) -> None:
        for alias in node.names:
            self.names.add(alias.asname or alias.name.split(".", 1)[0])

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        for alias in node.names:
            if alias.name != "*":
                self.names.add(alias.asname or alias.name)

    def visit_Global(self, node: ast.Global) -> None:
        self.global_names.update(node.names)

    def visit_Nonlocal(self, node: ast.Nonlocal) -> None:
        self.nonlocal_names.update(node.names)

    def visit_ExceptHandler(self, node: ast.ExceptHandler) -> None:
        if node.name is not None:
            self.names.add(node.name)
        if node.type is not None:
            self.visit(node.type)
        for statement in node.body:
            self.visit(statement)

    def visit_MatchAs(self, node: ast.MatchAs) -> None:
        if node.name is not None:
            self.names.add(node.name)
        if node.pattern is not None:
            self.visit(node.pattern)

    def visit_MatchStar(self, node: ast.MatchStar) -> None:
        if node.name is not None:
            self.names.add(node.name)

    def visit_MatchMapping(self, node: ast.MatchMapping) -> None:
        if node.rest is not None:
            self.names.add(node.rest)
        self.generic_visit(node)

    def visit_comprehension(self, node: ast.comprehension) -> None:
        # A comprehension target belongs to the implicit comprehension scope,
        # not to the enclosing function. Assignment expressions in its
        # iterable/filters are still visited as enclosing-scope bindings.
        self.visit(node.iter)
        for condition in node.ifs:
            self.visit(condition)


def _r19_function_local_names(
    node: ast.FunctionDef | ast.AsyncFunctionDef,
) -> set[str]:
    collector = _R19LocalBindingCollector()
    for argument in (
        *node.args.posonlyargs,
        *node.args.args,
        *node.args.kwonlyargs,
    ):
        collector.names.add(argument.arg)
    if node.args.vararg is not None:
        collector.names.add(node.args.vararg.arg)
    if node.args.kwarg is not None:
        collector.names.add(node.args.kwarg.arg)
    for statement in node.body:
        collector.visit(statement)
    return collector.names - collector.global_names - collector.nonlocal_names


def _r19_lambda_local_names(node: ast.Lambda) -> set[str]:
    collector = _R19LocalBindingCollector()
    for argument in (
        *node.args.posonlyargs,
        *node.args.args,
        *node.args.kwonlyargs,
    ):
        collector.names.add(argument.arg)
    if node.args.vararg is not None:
        collector.names.add(node.args.vararg.arg)
    if node.args.kwarg is not None:
        collector.names.add(node.args.kwarg.arg)
    collector.visit(node.body)
    return collector.names


def _r19_iterated_value(value: _Value) -> _Value:
    if _container_kind(value) == "sequence" and _sequence_length(value) == 1:
        return _semantic_atoms(value)
    return _UNKNOWN


def _r19_pattern_names(pattern: ast.pattern) -> set[str]:
    names: set[str] = set()
    for node in ast.walk(pattern):
        if isinstance(node, ast.MatchAs) and node.name is not None:
            names.add(node.name)
        elif isinstance(node, ast.MatchStar) and node.name is not None:
            names.add(node.name)
        elif isinstance(node, ast.MatchMapping) and node.rest is not None:
            names.add(node.rest)
    return names


class _R19DynamicExecutionScanner(_R18DynamicExecutionScanner):
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
        for name in _r19_function_local_names(node):
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

        child_environment = (
            self._class_lexical_environments[-1].copy()
            if self._class_lexical_environments
            else environment.copy()
        )
        for name in _r19_lambda_local_names(node):
            child_environment[name] = _UNKNOWN

        lexical_environment: dict[str, _Value] | None = None
        if self._class_lexical_environments:
            lexical_environment = self._class_lexical_environments.pop()
        try:
            self._scan_expression(node.body, child_environment)
        finally:
            if lexical_environment is not None:
                self._class_lexical_environments.append(lexical_environment)
        return _UNKNOWN

    def _scan_comprehension(
        self,
        node: ast.ListComp | ast.SetComp | ast.GeneratorExp | ast.DictComp,
        environment: dict[str, _Value],
    ) -> _Value:
        first_generator = node.generators[0]
        first_iterable = self._scan_expression(first_generator.iter, environment)

        child_environment = (
            self._class_lexical_environments[-1].copy()
            if self._class_lexical_environments
            else environment.copy()
        )
        self._assign_target(
            first_generator.target,
            _r19_iterated_value(first_iterable),
            child_environment,
        )

        lexical_environment: dict[str, _Value] | None = None
        if self._class_lexical_environments:
            lexical_environment = self._class_lexical_environments.pop()
        try:
            for condition in first_generator.ifs:
                self._scan_expression(condition, child_environment)

            for generator in node.generators[1:]:
                iterable = self._scan_expression(generator.iter, child_environment)
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
            if lexical_environment is not None:
                self._class_lexical_environments.append(lexical_environment)

        return _UNKNOWN

    def _scan_expression(
        self,
        node: ast.AST,
        environment: dict[str, _Value],
    ) -> _Value:
        if isinstance(node, ast.Lambda):
            return self._scan_lambda(node, environment)
        if isinstance(
            node,
            (ast.ListComp, ast.SetComp, ast.GeneratorExp, ast.DictComp),
        ):
            return self._scan_comprehension(node, environment)
        return super()._scan_expression(node, environment)

    def _scan_pattern_expressions(
        self,
        pattern: ast.pattern,
        environment: dict[str, _Value],
    ) -> None:
        for child in ast.iter_child_nodes(pattern):
            if isinstance(child, ast.expr):
                self._scan_expression(child, environment)
            elif isinstance(child, ast.pattern):
                self._scan_pattern_expressions(child, environment)

    def _scan_try(
        self,
        node: ast.Try | ast.TryStar,
        environment: dict[str, _Value],
    ) -> None:
        branches: list[dict[str, _Value]] = []
        body_environment = environment.copy()
        self._scan_block(node.body, body_environment)
        branches.append(body_environment)

        for handler in node.handlers:
            if handler.type is not None:
                self._scan_expression(handler.type, environment)
            handler_environment = environment.copy()
            if handler.name is not None:
                handler_environment[handler.name] = _UNKNOWN
            self._scan_block(handler.body, handler_environment)
            branches.append(handler_environment)

        else_environment = body_environment.copy()
        self._scan_block(node.orelse, else_environment)
        branches.append(else_environment)

        final_environment = environment.copy()
        self._scan_block(node.finalbody, final_environment)
        branches.append(final_environment)
        self._merge_environments(environment, *branches)

    def _scan_statement(
        self,
        node: ast.stmt,
        environment: dict[str, _Value],
    ) -> None:
        if isinstance(node, ast.AnnAssign):
            if node.value is not None:
                value = self._scan_expression(node.value, environment)
                if self._is_sensitive_value(value):
                    self._mark_binding(node.lineno)
                self._assign_target(node.target, value, environment)

            if (
                not self._postponed_annotations
                and self._annotation_scopes[-1] in {"module", "class"}
            ):
                self._scan_expression(node.annotation, environment)
            return

        if isinstance(node, (ast.Try, ast.TryStar)):
            self._scan_try(node, environment)
            return

        if isinstance(node, ast.Match):
            self._scan_expression(node.subject, environment)
            branches = [environment.copy()]
            for case in node.cases:
                case_environment = environment.copy()
                self._scan_pattern_expressions(case.pattern, case_environment)
                for name in _r19_pattern_names(case.pattern):
                    case_environment[name] = _UNKNOWN
                if case.guard is not None:
                    self._scan_expression(case.guard, case_environment)
                self._scan_block(case.body, case_environment)
                branches.append(case_environment)
            self._merge_environments(environment, *branches)
            return

        if isinstance(node, (ast.Global, ast.Nonlocal)):
            return

        super()._scan_statement(node, environment)


def _r19_dynamic_execution_markers_from_source(source: str) -> tuple[str, ...]:
    return _R19DynamicExecutionScanner().scan(source)


def test_r19_annotation_only_assignment_does_not_bind_target() -> None:
    source = """\
eval: eval("1+1")
exec: int
exec("pass")
"""

    assert _r19_dynamic_execution_markers_from_source(source) == (
        "call:1",
        "call:3",
    )


def test_r19_postponed_annotation_only_assignment_still_does_not_bind_target() -> None:
    source = """\
from __future__ import annotations
eval: eval("1+1")
eval("2+2")
"""

    assert _r19_dynamic_execution_markers_from_source(source) == ("call:3",)


def test_r19_valued_annotation_preserves_value_binding_before_annotation() -> None:
    source = """\
eval: eval("safe") = lambda value: value
"""

    assert _r19_dynamic_execution_markers_from_source(source) == ()


def test_r19_global_declaration_does_not_create_false_local_shadow() -> None:
    source = """\
def run():
    global eval
    result = eval("1+1")
    eval = lambda value: value
    return result
"""

    assert _r19_dynamic_execution_markers_from_source(source) == ("call:3",)


def test_r19_global_safe_rebinding_before_call_remains_safe() -> None:
    source = """\
eval = lambda value: value
def run():
    global eval
    return eval("x")
"""

    assert _r19_dynamic_execution_markers_from_source(source) == ()


def test_r19_comprehension_target_does_not_shadow_enclosing_scope() -> None:
    source = """\
def run():
    before = eval("1+1")
    values = [eval for eval in (1, 2)]
    return before, values
"""

    assert _r19_dynamic_execution_markers_from_source(source) == ("call:2",)


def test_r19_comprehension_iterables_filters_and_singleton_aliases_are_scanned() -> None:
    source = """\
values = [item for item in eval("[1]")]
filtered = [item for item in (1,) if exec("pass")]
called = [fn("1+1") for fn in (eval,)]
"""

    assert _r19_dynamic_execution_markers_from_source(source) == (
        "call:1",
        "call:2",
        "call:3",
    )


def test_r19_comprehension_target_shadowing_remains_safe() -> None:
    source = """\
values = [eval("x") for eval in (lambda value: value,)]
"""

    assert _r19_dynamic_execution_markers_from_source(source) == ()


def test_r19_lambda_defaults_are_definition_time_execution() -> None:
    source = """\
factory = lambda value=eval("1+1"): value
"""

    assert _r19_dynamic_execution_markers_from_source(source) == ("call:1",)


def test_r19_lambda_local_binding_is_lexical_for_entire_lambda() -> None:
    source = """\
factory = lambda: (eval("x"), (eval := len))
"""

    assert _r19_dynamic_execution_markers_from_source(source) == ()


def test_r19_match_guards_and_bodies_are_scanned() -> None:
    source = """\
def body(value):
    match value:
        case 1:
            return eval("1+1")
def guard(value):
    match value:
        case _ if exec("pass"):
            return value
"""

    assert _r19_dynamic_execution_markers_from_source(source) == (
        "call:4",
        "call:7",
    )


def test_r19_match_capture_shadows_builtin_inside_case() -> None:
    source = """\
def run(value):
    match value:
        case eval:
            return eval("x")
"""

    assert _r19_dynamic_execution_markers_from_source(source) == ()


def test_r19_exception_type_expressions_and_except_star_bodies_are_scanned() -> None:
    source = """\
def ordinary():
    try:
        raise ValueError
    except eval("ValueError"):
        pass

def grouped():
    try:
        raise ExceptionGroup("x", [ValueError("bad")])
    except* ValueError:
        eval("1+1")
"""

    assert _r19_dynamic_execution_markers_from_source(source) == (
        "call:4",
        "call:11",
    )


def test_r19_exception_target_is_lexically_local_before_handler() -> None:
    source = """\
def run():
    eval("x")
    try:
        raise ValueError
    except ValueError as eval:
        pass
"""

    assert _r19_dynamic_execution_markers_from_source(source) == ()


def test_r19_preserves_r18_annotation_semantics() -> None:
    source = """\
def parameter(value: eval("1+1")):
    return value

class Carrier:
    value: exec("pass") = 1
"""

    assert _r19_dynamic_execution_markers_from_source(source) == (
        "call:1",
        "call:5",
    )


def test_r19_preserves_postponed_annotation_negative() -> None:
    source = """\
from __future__ import annotations
def parameter(value: eval("1+1")) -> exec("pass"):
    return value
"""

    assert _r19_dynamic_execution_markers_from_source(source) == ()


def test_r19_complete_owner_and_oracle_surface_has_no_dynamic_execution() -> None:
    paths = (*_owner_paths(), _FULL_CLOSURE_ORACLE_PATH)

    for path in paths:
        assert _r19_dynamic_execution_markers_from_source(
            path.read_text(encoding="utf-8")
        ) == (), path

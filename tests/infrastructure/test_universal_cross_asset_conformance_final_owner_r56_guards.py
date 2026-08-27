from __future__ import annotations

import ast

import test_universal_cross_asset_conformance_final_owner_r12_guards as _r12
import test_universal_cross_asset_conformance_final_owner_r55_guards as _r55
from test_universal_cross_asset_conformance_final_owner_r12_guards import (
    _FULL_CLOSURE_ORACLE_PATH,
    _Atom,
    _owner_paths,
    _Value,
)


class _R56RuntimeScopeClassifier(ast.NodeVisitor):
    def __init__(self) -> None:
        self._scope = "module"
        self.module_call_positions: set[tuple[int, int]] = set()

    def _visit_in_scope(self, node: ast.AST, scope: str) -> None:
        previous = self._scope
        self._scope = scope
        try:
            self.visit(node)
        finally:
            self._scope = previous

    def visit_Call(self, node: ast.Call) -> None:
        if self._scope == "module":
            self.module_call_positions.add((node.lineno, node.col_offset))
        self.generic_visit(node)

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        for decorator in node.decorator_list:
            self.visit(decorator)
        for default in node.args.defaults:
            self.visit(default)
        for default in node.args.kw_defaults:
            if default is not None:
                self.visit(default)
        for argument in (
            *node.args.posonlyargs,
            *node.args.args,
            *node.args.kwonlyargs,
        ):
            if argument.annotation is not None:
                self.visit(argument.annotation)
        if node.args.vararg is not None and node.args.vararg.annotation is not None:
            self.visit(node.args.vararg.annotation)
        if node.args.kwarg is not None and node.args.kwarg.annotation is not None:
            self.visit(node.args.kwarg.annotation)
        if node.returns is not None:
            self.visit(node.returns)
        for statement in node.body:
            self._visit_in_scope(statement, "function")

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self.visit_FunctionDef(node)

    def visit_Lambda(self, node: ast.Lambda) -> None:
        for default in node.args.defaults:
            self.visit(default)
        for default in node.args.kw_defaults:
            if default is not None:
                self.visit(default)
        self._visit_in_scope(node.body, "lambda")

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        for decorator in node.decorator_list:
            self.visit(decorator)
        for base in node.bases:
            self.visit(base)
        for keyword in node.keywords:
            self.visit(keyword.value)
        for statement in node.body:
            self._visit_in_scope(statement, "class")

    def _visit_comprehension(
        self,
        node: ast.ListComp | ast.SetComp | ast.GeneratorExp | ast.DictComp,
    ) -> None:
        first = node.generators[0]
        self.visit(first.iter)

        previous = self._scope
        self._scope = "comprehension"
        try:
            for condition in first.ifs:
                self.visit(condition)
            for generator in node.generators[1:]:
                self.visit(generator.iter)
                for condition in generator.ifs:
                    self.visit(condition)
            if isinstance(node, ast.DictComp):
                self.visit(node.key)
                self.visit(node.value)
            else:
                self.visit(node.elt)
        finally:
            self._scope = previous

    def visit_ListComp(self, node: ast.ListComp) -> None:
        self._visit_comprehension(node)

    def visit_SetComp(self, node: ast.SetComp) -> None:
        self._visit_comprehension(node)

    def visit_GeneratorExp(self, node: ast.GeneratorExp) -> None:
        self._visit_comprehension(node)

    def visit_DictComp(self, node: ast.DictComp) -> None:
        self._visit_comprehension(node)


def _r56_module_call_positions(source: str) -> set[tuple[int, int]]:
    classifier = _R56RuntimeScopeClassifier()
    classifier.visit(ast.parse(source))
    return classifier.module_call_positions


class _R56ScopePreservingFallbackScanner(_r55._R55FallbackReachabilityScanner):
    def __init__(self) -> None:
        super().__init__()
        self._r56_module_calls: set[tuple[int, int]] = set()
        self._r56_call_scope_stack: list[bool] = []

    def scan(self, source: str) -> tuple[str, ...]:
        self._r56_module_calls = _r56_module_call_positions(source)
        self._r56_call_scope_stack = []
        return super().scan(source)

    def _scan_function(
        self,
        node: ast.FunctionDef | ast.AsyncFunctionDef,
        environment: dict[str, _Value],
    ) -> None:
        super(_r55._R55FallbackReachabilityScanner, self)._scan_function(
            node,
            environment,
        )

    def _scan_expression(
        self,
        node: ast.AST,
        environment: dict[str, _Value],
    ) -> _Value:
        if isinstance(node, ast.Lambda):
            return super(
                _r55._R55FallbackReachabilityScanner,
                self,
            )._scan_expression(node, environment)
        return super()._scan_expression(node, environment)

    def _scan_statement(
        self,
        node: ast.stmt,
        environment: dict[str, _Value],
    ) -> None:
        if isinstance(node, ast.ClassDef):
            super(
                _r55._R55FallbackReachabilityScanner,
                self,
            )._scan_statement(node, environment)
            return
        super()._scan_statement(node, environment)

    def _evaluate_call(
        self,
        node: ast.Call,
        environment: dict[str, _Value],
    ) -> _Value:
        self._r56_call_scope_stack.append(
            (node.lineno, node.col_offset) in self._r56_module_calls
        )
        try:
            return super()._evaluate_call(node, environment)
        finally:
            self._r56_call_scope_stack.pop()

    def _evaluate_special_call(
        self,
        helper: _Atom,
        arguments: list[_Value],
    ) -> _Value:
        if helper.kind == "helper" and helper.text == "vars" and not arguments:
            if self._r56_call_scope_stack and self._r56_call_scope_stack[-1]:
                return _r55._r55_module_vars_value()
            return _r12._UNKNOWN
        return super()._evaluate_special_call(helper, arguments)


def _r56_dynamic_execution_markers_from_source(source: str) -> tuple[str, ...]:
    return _R56ScopePreservingFallbackScanner().scan(source)


def test_r56_restores_global_lookup_semantics_from_inherited_scanner() -> None:
    source = """\
def run():
    global eval
    result = eval("1+1")
    eval = lambda value: value
    return result
"""

    assert "call:3" in _r56_dynamic_execution_markers_from_source(source)


def test_r56_restores_lambda_default_evaluation() -> None:
    source = 'factory = lambda value=eval("1+1"): value\n'

    assert _r56_dynamic_execution_markers_from_source(source) == ("call:1",)


def test_r56_restores_class_global_mutation_fail_closed_guard() -> None:
    source = """\
eval = lambda value: value
class Carrier:
    global eval
    from builtins import eval
eval("1+1")
"""

    assert "binding:3" in _r56_dynamic_execution_markers_from_source(source)


def test_r56_comprehension_vars_does_not_invent_module_builtins() -> None:
    sources = (
        'values = [vars()["__builtins__"].__dict__["eval"]("1+1") for _ in (0,)]\n',
        'values = {vars()["__builtins__"].__dict__["eval"]("1+1") for _ in (0,)}\n',
        'values = (vars()["__builtins__"].__dict__["eval"]("1+1") for _ in (0,))\n',
        'values = {_: vars()["__builtins__"].__dict__["eval"]("1+1") for _ in (0,)}\n',
    )

    for source in sources:
        assert _r56_dynamic_execution_markers_from_source(source) == ()


def test_r56_first_comprehension_iterable_still_uses_enclosing_module_scope() -> None:
    source = (
        'values = [item for item in '
        'vars()["__builtins__"].__dict__["eval"]("1+1")]\n'
    )

    assert "call:1" in _r56_dynamic_execution_markers_from_source(source)


def test_r56_defaults_keep_enclosing_module_vars_semantics() -> None:
    sources = (
        'def f(value=vars()["__builtins__"].__dict__["eval"]("1+1")):\n    return value\n',
        'factory = lambda value=vars()["__builtins__"].__dict__["eval"]("1+1"): value\n',
    )

    for source in sources:
        assert "call:1" in _r56_dynamic_execution_markers_from_source(source)


def test_r56_preserves_r55_fallback_regressions() -> None:
    source = """\
flag = True
mapping = {} if flag else {"missing": len}
mapping.get("missing", eval)("1+1")

class Safe:
    pass
getattr(Safe, "missing", exec)("pass")
"""

    markers = _r56_dynamic_execution_markers_from_source(source)
    assert "call:3" in markers
    assert "call:7" in markers


def test_r56_complete_owner_and_oracle_surface_has_no_dynamic_execution() -> None:
    paths = (*_owner_paths(), _FULL_CLOSURE_ORACLE_PATH)

    for path in paths:
        assert _r56_dynamic_execution_markers_from_source(
            path.read_text(encoding="utf-8")
        ) == (), path

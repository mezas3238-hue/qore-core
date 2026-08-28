from __future__ import annotations

import ast
from dataclasses import dataclass

import test_universal_cross_asset_conformance_final_owner_r15_guards as _r15
import test_universal_cross_asset_conformance_final_owner_r55_guards as _r55
import test_universal_cross_asset_conformance_final_owner_r62e_guards as _r62e
import test_universal_cross_asset_conformance_final_owner_r62g_guards as _r62g
from test_universal_cross_asset_conformance_final_owner_r12_guards import (
    _FULL_CLOSURE_ORACLE_PATH,
    _UNKNOWN,
    _Atom,
    _owner_paths,
    _Value,
)


class _R62HBindingCollector(ast.NodeVisitor):
    """Collect bindings belonging to one lexical scope without descending."""

    def __init__(self) -> None:
        self.bound: set[str] = set()
        self.globals: set[str] = set()
        self.nonlocals: set[str] = set()

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self.bound.add(node.name)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self.bound.add(node.name)

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        self.bound.add(node.name)

    def visit_Lambda(self, node: ast.Lambda) -> None:
        return

    def visit_Global(self, node: ast.Global) -> None:
        self.globals.update(node.names)

    def visit_Nonlocal(self, node: ast.Nonlocal) -> None:
        self.nonlocals.update(node.names)

    def visit_Name(self, node: ast.Name) -> None:
        if isinstance(node.ctx, (ast.Store, ast.Del)):
            self.bound.add(node.id)

    def visit_Import(self, node: ast.Import) -> None:
        for alias in node.names:
            self.bound.add(alias.asname or alias.name.split(".", 1)[0])

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        for alias in node.names:
            if alias.name != "*":
                self.bound.add(alias.asname or alias.name)


def _r62h_function_local_names(
    node: ast.FunctionDef | ast.AsyncFunctionDef,
) -> frozenset[str]:
    collector = _R62HBindingCollector()
    for argument in (
        *node.args.posonlyargs,
        *node.args.args,
        *node.args.kwonlyargs,
    ):
        collector.bound.add(argument.arg)
    if node.args.vararg is not None:
        collector.bound.add(node.args.vararg.arg)
    if node.args.kwarg is not None:
        collector.bound.add(node.args.kwarg.arg)
    for statement in node.body:
        collector.visit(statement)
    return frozenset(collector.bound - collector.globals - collector.nonlocals)


def _r62h_lambda_local_names(node: ast.Lambda) -> frozenset[str]:
    collector = _R62HBindingCollector()
    for argument in (
        *node.args.posonlyargs,
        *node.args.args,
        *node.args.kwonlyargs,
    ):
        collector.bound.add(argument.arg)
    if node.args.vararg is not None:
        collector.bound.add(node.args.vararg.arg)
    if node.args.kwarg is not None:
        collector.bound.add(node.args.kwarg.arg)
    collector.visit(node.body)
    return frozenset(collector.bound - collector.globals - collector.nonlocals)


def _r62h_target_names(target: ast.AST) -> set[str]:
    if isinstance(target, ast.Name):
        return {target.id}
    if isinstance(target, (ast.Tuple, ast.List)):
        names: set[str] = set()
        for element in target.elts:
            names.update(_r62h_target_names(element))
        return names
    if isinstance(target, ast.Starred):
        return _r62h_target_names(target.value)
    return set()


@dataclass
class _R62HScope:
    kind: str
    local_names: set[str]
    global_names: set[str]


class _R62HLocalCallClassifier(ast.NodeVisitor):
    """Map call sites to names that can actually belong to that runtime locals()."""

    def __init__(self) -> None:
        self.local_names_by_call: dict[tuple[int, int], frozenset[str]] = {}
        self._scope = _R62HScope("module", set(), set())

    def _visit_in_scope(self, scope: _R62HScope, nodes: list[ast.AST]) -> None:
        previous = self._scope
        self._scope = scope
        try:
            for node in nodes:
                self.visit(node)
        finally:
            self._scope = previous

    def visit_Call(self, node: ast.Call) -> None:
        if self._scope.kind != "module":
            self.local_names_by_call[(node.lineno, node.col_offset)] = frozenset(
                self._scope.local_names - self._scope.global_names
            )
        self.generic_visit(node)

    def _visit_function_definition(
        self,
        node: ast.FunctionDef | ast.AsyncFunctionDef,
    ) -> None:
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

        local_names = set(_r62h_function_local_names(node))
        globals_in_scope: set[str] = set()
        collector = _R62HBindingCollector()
        for statement in node.body:
            collector.visit(statement)
        globals_in_scope.update(collector.globals)
        self._visit_in_scope(
            _R62HScope("function", local_names, globals_in_scope),
            list(node.body),
        )

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self._visit_function_definition(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self._visit_function_definition(node)

    def visit_Lambda(self, node: ast.Lambda) -> None:
        for default in node.args.defaults:
            self.visit(default)
        for default in node.args.kw_defaults:
            if default is not None:
                self.visit(default)
        self._visit_in_scope(
            _R62HScope("lambda", set(_r62h_lambda_local_names(node)), set()),
            [node.body],
        )

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        for decorator in node.decorator_list:
            self.visit(decorator)
        for base in node.bases:
            self.visit(base)
        for keyword in node.keywords:
            self.visit(keyword.value)

        previous = self._scope
        class_scope = _R62HScope("class", set(), set())
        self._scope = class_scope
        try:
            for statement in node.body:
                self.visit(statement)
                self._record_class_bindings(statement, class_scope)
        finally:
            self._scope = previous

    def _record_class_bindings(self, node: ast.stmt, scope: _R62HScope) -> None:
        if isinstance(node, ast.Global):
            scope.global_names.update(node.names)
            scope.local_names.difference_update(node.names)
            return
        if isinstance(node, ast.Nonlocal):
            scope.global_names.update(node.names)
            scope.local_names.difference_update(node.names)
            return
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            if node.name not in scope.global_names:
                scope.local_names.add(node.name)
            return
        if isinstance(node, ast.Import):
            for alias in node.names:
                name = alias.asname or alias.name.split(".", 1)[0]
                if name not in scope.global_names:
                    scope.local_names.add(name)
            return
        if isinstance(node, ast.ImportFrom):
            for alias in node.names:
                if alias.name == "*":
                    continue
                name = alias.asname or alias.name
                if name not in scope.global_names:
                    scope.local_names.add(name)
            return
        if isinstance(node, ast.Assign):
            for target in node.targets:
                scope.local_names.update(
                    _r62h_target_names(target) - scope.global_names
                )
            return
        if isinstance(node, (ast.AnnAssign, ast.AugAssign)):
            scope.local_names.update(
                _r62h_target_names(node.target) - scope.global_names
            )
            return
        if isinstance(node, (ast.For, ast.AsyncFor)):
            scope.local_names.update(
                _r62h_target_names(node.target) - scope.global_names
            )
            collector = _R62HBindingCollector()
            for statement in (*node.body, *node.orelse):
                collector.visit(statement)
            scope.local_names.update(
                collector.bound - collector.globals - collector.nonlocals
            )
            return
        if isinstance(node, ast.If):
            collector = _R62HBindingCollector()
            for statement in (*node.body, *node.orelse):
                collector.visit(statement)
            scope.local_names.update(
                collector.bound - collector.globals - collector.nonlocals
            )
            return
        if isinstance(node, (ast.With, ast.AsyncWith)):
            for item in node.items:
                if item.optional_vars is not None:
                    scope.local_names.update(
                        _r62h_target_names(item.optional_vars) - scope.global_names
                    )
            collector = _R62HBindingCollector()
            for statement in node.body:
                collector.visit(statement)
            scope.local_names.update(
                collector.bound - collector.globals - collector.nonlocals
            )
            return
        if isinstance(node, ast.Try):
            collector = _R62HBindingCollector()
            nested = [*node.body, *node.orelse, *node.finalbody]
            for handler in node.handlers:
                nested.extend(handler.body)
                if handler.name is not None:
                    collector.bound.add(handler.name)
            for statement in nested:
                collector.visit(statement)
            scope.local_names.update(
                collector.bound - collector.globals - collector.nonlocals
            )


def _r62h_local_names_by_call(source: str) -> dict[tuple[int, int], frozenset[str]]:
    classifier = _R62HLocalCallClassifier()
    classifier.visit(ast.parse(source))
    return classifier.local_names_by_call


def _r62h_selected_local_namespace(
    environment: dict[str, _Value],
    local_names: frozenset[str],
) -> _Value:
    atoms = set(_r62e._R62E_RETAINED_NAMESPACE)
    for name in sorted(local_names):
        value = environment.get(name, _UNKNOWN)
        if value == _UNKNOWN:
            continue
        token = f"s:{name}"
        atoms.add(_Atom(_r55._R55_PRESENT_KEY_KIND, token))
        atoms.update(_r15._selected_slot_atom(token, atom) for atom in value)
    return frozenset(atoms)


class _R62HLocalNamespaceSelectedSlotScanner(
    _r62g._R62GScopePreservingRetainedNamespaceScanner
):
    """Preserve real local selected slots without promoting globals into locals."""

    def __init__(self) -> None:
        super().__init__()
        self._r62h_local_names_by_call: dict[
            tuple[int, int], frozenset[str]
        ] = {}
        self._r62h_call_context_stack: list[
            tuple[dict[str, _Value], frozenset[str]]
        ] = []

    def scan(self, source: str) -> tuple[str, ...]:
        self._r62h_local_names_by_call = _r62h_local_names_by_call(source)
        self._r62h_call_context_stack = []
        return super().scan(source)

    def _evaluate_call(
        self,
        node: ast.Call,
        environment: dict[str, _Value],
    ) -> _Value:
        local_names = self._r62h_local_names_by_call.get(
            (node.lineno, node.col_offset),
            frozenset(),
        )
        self._r62h_call_context_stack.append((environment, local_names))
        try:
            return super()._evaluate_call(node, environment)
        finally:
            self._r62h_call_context_stack.pop()

    def _evaluate_special_call(
        self,
        helper: _Atom,
        arguments: list[_Value],
    ) -> _Value:
        if (
            helper.kind == "helper"
            and helper.text in {"locals", "vars"}
            and not arguments
            and self._r56_call_scope_stack
            and not self._r56_call_scope_stack[-1]
            and self._r62h_call_context_stack
        ):
            environment, local_names = self._r62h_call_context_stack[-1]
            return _r62h_selected_local_namespace(environment, local_names)
        return super()._evaluate_special_call(helper, arguments)


def _r62h_dynamic_execution_markers_from_source(source: str) -> tuple[str, ...]:
    return _R62HLocalNamespaceSelectedSlotScanner().scan(source)


def _runtime_result(source: str) -> object:
    namespace: dict[str, object] = {}
    exec(source, namespace)
    return namespace["result"]


def _runtime_key_error(source: str) -> tuple[object, ...]:
    namespace: dict[str, object] = {}
    try:
        exec(source, namespace)
    except KeyError as exc:
        return exc.args
    raise AssertionError("expected KeyError")


def test_r62h_predecessor_reproduces_local_selected_slot_false_negatives() -> None:
    sources = (
        """\
def run():
    import builtins
    return vars()["builtins"].eval("1+1")
result = run()
""",
        """\
def run():
    import builtins
    return locals()["builtins"].eval("1+1")
result = run()
""",
        """\
class Carrier:
    import builtins
    value = vars()["builtins"].eval("1+1")
result = Carrier.value
""",
        """\
class Carrier:
    import builtins
    value = locals()["builtins"].eval("1+1")
result = Carrier.value
""",
    )

    for source in sources:
        assert _runtime_result(source) == 2
        assert _r62g._r62g_dynamic_execution_markers_from_source(source) == ()


def test_r62h_function_and_class_local_builtins_fail_closed() -> None:
    sources = (
        """\
def run():
    import builtins
    return vars()["builtins"].eval("1+1")
result = run()
""",
        """\
def run():
    import builtins as b
    return locals()["b"].exec("pass")
result = run()
""",
        """\
def run():
    from builtins import eval as local_eval
    return vars()["local_eval"]("1+1")
result = run()
""",
        """\
class Carrier:
    import builtins as b
    value = locals()["b"].eval("1+1")
result = Carrier.value
""",
    )

    assert _runtime_result(sources[0]) == 2
    assert _runtime_result(sources[1]) is None
    assert _runtime_result(sources[2]) == 2
    assert _runtime_result(sources[3]) == 2
    for source in sources:
        assert _r62h_dynamic_execution_markers_from_source(source)


def test_r62h_inherited_global_does_not_become_function_or_class_local() -> None:
    function_source = """\
import builtins
def run():
    return vars()["builtins"].eval("1+1")
result = run()
"""
    class_source = """\
import builtins
class Carrier:
    value = locals()["builtins"].eval("1+1")
result = Carrier.value
"""

    assert _runtime_key_error(function_source) == ("builtins",)
    assert _runtime_key_error(class_source) == ("builtins",)
    assert _r62h_dynamic_execution_markers_from_source(function_source) == ()
    assert _r62h_dynamic_execution_markers_from_source(class_source) == ()


def test_r62h_later_local_binding_does_not_exist_early() -> None:
    source = """\
import builtins
def run():
    try:
        vars()["builtins"].eval("1+1")
    except KeyError:
        pass
    builtins = len
    return 3
result = run()
"""

    assert _runtime_result(source) == 3
    assert _r62h_dynamic_execution_markers_from_source(source) == ()


def test_r62h_global_declaration_does_not_invent_function_local_slot() -> None:
    source = """\
import builtins
def run():
    global builtins
    return vars()["builtins"].eval("1+1")
result = run()
"""

    assert _runtime_key_error(source) == ("builtins",)
    assert _r62h_dynamic_execution_markers_from_source(source) == ()


def test_r62h_r62g_precision_and_retention_regressions_remain_authoritative() -> None:
    impossible_direct = """\
def run():
    return vars()["__builtins__"].eval("1+1")
result = run()
"""
    retained_default = """\
def outer():
    import builtins
    def hold(namespace=vars()):
        return None
    return hold
hold = outer()
result = hold.__defaults__[0]["builtins"].eval("1+1")
"""
    nested_globals = """\
def run():
    return globals()["__builtins__"]["eval"]("1+1")
result = run()
"""

    assert _runtime_key_error(impossible_direct) == ("__builtins__",)
    assert _runtime_result(retained_default) == 2
    assert _runtime_result(nested_globals) == 2
    assert _r62h_dynamic_execution_markers_from_source(impossible_direct) == ()
    assert "binding:3" in _r62h_dynamic_execution_markers_from_source(
        retained_default
    )
    assert _r62h_dynamic_execution_markers_from_source(nested_globals) == (
        "call:2",
    )


def test_r62h_complete_owner_and_oracle_surface_has_no_dynamic_execution() -> None:
    paths = (*_owner_paths(), _FULL_CLOSURE_ORACLE_PATH)

    for path in paths:
        assert _r62h_dynamic_execution_markers_from_source(
            path.read_text(encoding="utf-8")
        ) == (), path

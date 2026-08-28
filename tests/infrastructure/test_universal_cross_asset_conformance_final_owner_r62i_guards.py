from __future__ import annotations

import ast

import test_universal_cross_asset_conformance_final_owner_r15_guards as _r15
import test_universal_cross_asset_conformance_final_owner_r55_guards as _r55
import test_universal_cross_asset_conformance_final_owner_r62e_guards as _r62e
import test_universal_cross_asset_conformance_final_owner_r62h_guards as _r62h
from test_universal_cross_asset_conformance_final_owner_r12_guards import (
    _FULL_CLOSURE_ORACLE_PATH,
    _UNKNOWN,
    _Atom,
    _owner_paths,
    _Value,
)


class _R62IModuleBindingClassifier(_r62h._R62HLocalCallClassifier):
    """Track straight-line module bindings visible at each call site."""

    def __init__(self) -> None:
        super().__init__()
        self.module_names_by_call: dict[tuple[int, int], frozenset[str]] = {}
        self._module_names: set[str] = {"__builtins__"}

    def visit_Module(self, node: ast.Module) -> None:
        for statement in node.body:
            self.visit(statement)
            self._record_module_bindings(statement)

    def visit_Call(self, node: ast.Call) -> None:
        self.module_names_by_call[(node.lineno, node.col_offset)] = frozenset(
            self._module_names
        )
        super().visit_Call(node)

    def _record_module_bindings(self, node: ast.stmt) -> None:
        if isinstance(node, ast.Delete):
            for target in node.targets:
                self._module_names.difference_update(_r62h._r62h_target_names(target))
            return

        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            self._module_names.add(node.name)
            return

        if isinstance(node, ast.Import):
            for alias in node.names:
                self._module_names.add(alias.asname or alias.name.split(".", 1)[0])
            return

        if isinstance(node, ast.ImportFrom):
            for alias in node.names:
                if alias.name != "*":
                    self._module_names.add(alias.asname or alias.name)
            return

        if isinstance(node, ast.Assign):
            for target in node.targets:
                self._module_names.update(_r62h._r62h_target_names(target))
            return

        if isinstance(node, (ast.AnnAssign, ast.AugAssign)):
            self._module_names.update(_r62h._r62h_target_names(node.target))


class _R62IParameterClassifier(ast.NodeVisitor):
    """Record parameters that are definitely present in runtime locals()."""

    def __init__(self) -> None:
        self.parameters_by_call: dict[tuple[int, int], frozenset[str]] = {}
        self._parameters: list[frozenset[str]] = [frozenset()]

    @staticmethod
    def _parameters_for(
        arguments: ast.arguments,
    ) -> frozenset[str]:
        names = {
            argument.arg
            for argument in (
                *arguments.posonlyargs,
                *arguments.args,
                *arguments.kwonlyargs,
            )
        }
        if arguments.vararg is not None:
            names.add(arguments.vararg.arg)
        if arguments.kwarg is not None:
            names.add(arguments.kwarg.arg)
        return frozenset(names)

    def visit_Call(self, node: ast.Call) -> None:
        self.parameters_by_call[(node.lineno, node.col_offset)] = self._parameters[-1]
        self.generic_visit(node)

    def _visit_function_definition(
        self,
        node: ast.FunctionDef | ast.AsyncFunctionDef,
    ) -> None:
        for decorator in node.decorator_list:
            self.visit(decorator)
        for positional_default in node.args.defaults:
            self.visit(positional_default)
        for keyword_default in node.args.kw_defaults:
            if keyword_default is not None:
                self.visit(keyword_default)
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

        self._parameters.append(self._parameters_for(node.args))
        try:
            for statement in node.body:
                self.visit(statement)
        finally:
            self._parameters.pop()

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self._visit_function_definition(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self._visit_function_definition(node)

    def visit_Lambda(self, node: ast.Lambda) -> None:
        for positional_default in node.args.defaults:
            self.visit(positional_default)
        for keyword_default in node.args.kw_defaults:
            if keyword_default is not None:
                self.visit(keyword_default)
        self._parameters.append(self._parameters_for(node.args))
        try:
            self.visit(node.body)
        finally:
            self._parameters.pop()


def _r62i_module_names_by_call(source: str) -> dict[tuple[int, int], frozenset[str]]:
    classifier = _R62IModuleBindingClassifier()
    classifier.visit(ast.parse(source))
    return classifier.module_names_by_call


def _r62i_parameters_by_call(source: str) -> dict[tuple[int, int], frozenset[str]]:
    classifier = _R62IParameterClassifier()
    classifier.visit(ast.parse(source))
    return classifier.parameters_by_call


def _r62i_selected_namespace(
    environment: dict[str, _Value],
    names: frozenset[str],
) -> _Value:
    atoms = set(_r62e._R62E_RETAINED_NAMESPACE)
    for name in sorted(names):
        value = environment.get(name, _UNKNOWN)
        token = f"s:{name}"
        atoms.add(_Atom(_r55._R55_PRESENT_KEY_KIND, token))
        atoms.update(_r15._selected_slot_atom(token, atom) for atom in value)
    return frozenset(atoms)


def _r62i_selected_local_namespace(
    environment: dict[str, _Value],
    local_names: frozenset[str],
    parameter_names: frozenset[str],
) -> _Value:
    atoms = set(_r62e._R62E_RETAINED_NAMESPACE)
    for name in sorted(local_names):
        value = environment.get(name, _UNKNOWN)
        if value == _UNKNOWN and name not in parameter_names:
            continue
        token = f"s:{name}"
        atoms.add(_Atom(_r55._R55_PRESENT_KEY_KIND, token))
        atoms.update(_r15._selected_slot_atom(token, atom) for atom in value)
    return frozenset(atoms)


class _R62IModuleAndParameterNamespaceScanner(
    _r62h._R62HLocalNamespaceSelectedSlotScanner
):
    """Preserve actual module aliases and definitely-present local parameters."""

    def __init__(self) -> None:
        super().__init__()
        self._r62i_module_names_by_call: dict[
            tuple[int, int], frozenset[str]
        ] = {}
        self._r62i_parameters_by_call: dict[
            tuple[int, int], frozenset[str]
        ] = {}
        self._r62i_call_position_stack: list[tuple[int, int]] = []
        self._r62i_module_environment_stack: list[dict[str, _Value]] = []

    def scan(self, source: str) -> tuple[str, ...]:
        self._r62i_module_names_by_call = _r62i_module_names_by_call(source)
        self._r62i_parameters_by_call = _r62i_parameters_by_call(source)
        self._r62i_call_position_stack = []
        self._r62i_module_environment_stack = []
        return super().scan(source)

    def _module_environment(
        self,
        environment: dict[str, _Value],
    ) -> dict[str, _Value]:
        if self._r62i_module_environment_stack:
            return self._r62i_module_environment_stack[-1]
        return environment

    def _scan_function(
        self,
        node: ast.FunctionDef | ast.AsyncFunctionDef,
        environment: dict[str, _Value],
    ) -> None:
        module_environment = self._module_environment(environment).copy()
        self._r62i_module_environment_stack.append(module_environment)
        try:
            super()._scan_function(node, environment)
        finally:
            self._r62i_module_environment_stack.pop()

    def _scan_statement(
        self,
        node: ast.stmt,
        environment: dict[str, _Value],
    ) -> None:
        if isinstance(node, ast.ClassDef):
            module_environment = self._module_environment(environment).copy()
            self._r62i_module_environment_stack.append(module_environment)
            try:
                super()._scan_statement(node, environment)
            finally:
                self._r62i_module_environment_stack.pop()
            return
        super()._scan_statement(node, environment)

    def _evaluate_call(
        self,
        node: ast.Call,
        environment: dict[str, _Value],
    ) -> _Value:
        self._r62i_call_position_stack.append((node.lineno, node.col_offset))
        try:
            return super()._evaluate_call(node, environment)
        finally:
            self._r62i_call_position_stack.pop()

    def _evaluate_special_call(
        self,
        helper: _Atom,
        arguments: list[_Value],
    ) -> _Value:
        if (
            helper.kind == "helper"
            and helper.text in {"globals", "locals", "vars"}
            and not arguments
            and self._r62i_call_position_stack
            and self._r62h_call_context_stack
        ):
            position = self._r62i_call_position_stack[-1]
            environment, local_names = self._r62h_call_context_stack[-1]
            is_module_call = bool(
                self._r56_call_scope_stack and self._r56_call_scope_stack[-1]
            )

            if helper.text == "globals" or is_module_call:
                module_names = self._r62i_module_names_by_call.get(
                    position,
                    frozenset({"__builtins__"}),
                )
                return _r62i_selected_namespace(
                    self._module_environment(environment),
                    module_names,
                )

            parameter_names = self._r62i_parameters_by_call.get(
                position,
                frozenset(),
            )
            return _r62i_selected_local_namespace(
                environment,
                local_names,
                parameter_names,
            )

        return super()._evaluate_special_call(helper, arguments)


def _r62i_dynamic_execution_markers_from_source(source: str) -> tuple[str, ...]:
    return _R62IModuleAndParameterNamespaceScanner().scan(source)


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


def test_r62i_predecessor_reproduces_module_alias_false_negatives() -> None:
    sources = (
        'import builtins as b\nresult = vars()["b"].eval("1+1")\n',
        'import builtins as b\nresult = locals()["b"].eval("1+1")\n',
        'import builtins as b\nresult = globals()["b"].eval("1+1")\n',
        """\
import builtins as b
def run():
    return globals()["b"].eval("1+1")
result = run()
""",
    )

    for source in sources:
        assert _runtime_result(source) == 2
        assert _r62h._r62h_dynamic_execution_markers_from_source(source) == ()


def test_r62i_module_aliases_and_nested_globals_fail_closed() -> None:
    sources = (
        'import builtins as b\nresult = vars()["b"].eval("1+1")\n',
        'import builtins as b\nresult = locals()["b"].eval("1+1")\n',
        'import builtins as b\nresult = globals()["b"].eval("1+1")\n',
        """\
import builtins as b
def run():
    return globals()["b"].eval("1+1")
result = run()
""",
        """\
import builtins as b
def run():
    b = len
    return globals()["b"].eval("1+1")
result = run()
""",
        """\
import builtins as b
class Carrier:
    b = len
    value = globals()["b"].eval("1+1")
result = Carrier.value
""",
    )

    for source in sources:
        assert _runtime_result(source) == 2
        assert _r62i_dynamic_execution_markers_from_source(source)


def test_r62i_module_namespace_does_not_invent_plain_builtins_name() -> None:
    sources = (
        'result = vars()["builtins"].eval("1+1")\n',
        'result = locals()["builtins"].eval("1+1")\n',
        'result = globals()["builtins"].eval("1+1")\n',
    )

    for source in sources:
        assert _runtime_key_error(source) == ("builtins",)
        assert _r62h._r62h_dynamic_execution_markers_from_source(source) == (
            "call:1",
        )
        assert _r62i_dynamic_execution_markers_from_source(source) == ()


def test_r62i_explicit_module_builtins_binding_still_fails_closed() -> None:
    sources = (
        'import builtins\nresult = vars()["builtins"].eval("1+1")\n',
        'import builtins\nresult = locals()["builtins"].eval("1+1")\n',
        'import builtins\nresult = globals()["builtins"].eval("1+1")\n',
    )

    for source in sources:
        assert _runtime_result(source) == 2
        assert _r62i_dynamic_execution_markers_from_source(source) == ("call:2",)


def test_r62i_implicit_dunder_builtins_remains_fail_closed() -> None:
    source = 'result = globals()["__builtins__"]["eval"]("1+1")\n'

    assert _runtime_result(source) == 2
    assert _r62i_dynamic_execution_markers_from_source(source) == ("call:1",)


def test_r62i_unknown_parameter_is_present_for_locals_get() -> None:
    sources = (
        """\
def run(candidate):
    return locals().get("candidate", eval)("abc")
result = run(len)
""",
        """\
def run(candidate):
    return vars().get("candidate", eval)("abc")
result = run(len)
""",
    )

    for source in sources:
        assert _runtime_result(source) == 3
        assert _r62h._r62h_dynamic_execution_markers_from_source(source) == (
            "call:2",
        )
        assert _r62i_dynamic_execution_markers_from_source(source) == ()


def test_r62i_r62h_local_slots_and_r62g_precision_remain_authoritative() -> None:
    local_alias = """\
def run():
    import builtins as b
    return locals()["b"].eval("1+1")
result = run()
"""
    impossible_nested = """\
def run():
    return vars()["__builtins__"].eval("1+1")
result = run()
"""

    assert _runtime_result(local_alias) == 2
    assert _runtime_key_error(impossible_nested) == ("__builtins__",)
    assert _r62i_dynamic_execution_markers_from_source(local_alias)
    assert _r62i_dynamic_execution_markers_from_source(impossible_nested) == ()


def test_r62i_complete_owner_and_oracle_surface_has_no_dynamic_execution() -> None:
    paths = (*_owner_paths(), _FULL_CLOSURE_ORACLE_PATH)

    for path in paths:
        assert _r62i_dynamic_execution_markers_from_source(
            path.read_text(encoding="utf-8")
        ) == (), path

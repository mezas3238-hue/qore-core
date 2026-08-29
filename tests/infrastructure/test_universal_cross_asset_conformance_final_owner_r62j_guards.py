from __future__ import annotations

import ast

import test_universal_cross_asset_conformance_final_owner_r12_guards as _r12
import test_universal_cross_asset_conformance_final_owner_r15_guards as _r15
import test_universal_cross_asset_conformance_final_owner_r55_guards as _r55
import test_universal_cross_asset_conformance_final_owner_r62h_guards as _r62h
import test_universal_cross_asset_conformance_final_owner_r62i_guards as _r62i
from test_universal_cross_asset_conformance_final_owner_r12_guards import (
    _FULL_CLOSURE_ORACLE_PATH,
    _UNKNOWN,
    _Atom,
    _contains_kind,
    _owner_paths,
    _Value,
)

_R62J_NAMESPACE_HELPERS = frozenset({"globals", "locals", "vars"})
_R62J_DANGEROUS_NAMES = frozenset({"__import__", "eval", "exec"})


def _r62j_deferred_call_top_indexes(
    source: str,
) -> dict[tuple[int, int], int]:
    result: dict[tuple[int, int], int] = {}

    def visit(
        node: ast.AST,
        *,
        top_index: int,
        deferred: bool,
    ) -> None:
        if isinstance(node, ast.Call) and deferred:
            result[(node.lineno, node.col_offset)] = top_index

        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            immediate_nodes: list[ast.AST] = [
                *node.decorator_list,
                *node.args.defaults,
                *(item for item in node.args.kw_defaults if item is not None),
            ]
            for argument in (
                *node.args.posonlyargs,
                *node.args.args,
                *node.args.kwonlyargs,
            ):
                if argument.annotation is not None:
                    immediate_nodes.append(argument.annotation)
            if node.args.vararg is not None and node.args.vararg.annotation is not None:
                immediate_nodes.append(node.args.vararg.annotation)
            if node.args.kwarg is not None and node.args.kwarg.annotation is not None:
                immediate_nodes.append(node.args.kwarg.annotation)
            if node.returns is not None:
                immediate_nodes.append(node.returns)
            for child in immediate_nodes:
                visit(child, top_index=top_index, deferred=deferred)
            for statement in node.body:
                visit(statement, top_index=top_index, deferred=True)
            return

        if isinstance(node, ast.Lambda):
            immediate_nodes = [
                *node.args.defaults,
                *(item for item in node.args.kw_defaults if item is not None),
            ]
            for child in immediate_nodes:
                visit(child, top_index=top_index, deferred=deferred)
            visit(node.body, top_index=top_index, deferred=True)
            return

        if isinstance(node, ast.GeneratorExp):
            first = node.generators[0]
            visit(first.iter, top_index=top_index, deferred=deferred)
            for condition in first.ifs:
                visit(condition, top_index=top_index, deferred=True)
            for generator in node.generators[1:]:
                visit(generator.iter, top_index=top_index, deferred=True)
                for condition in generator.ifs:
                    visit(condition, top_index=top_index, deferred=True)
            visit(node.elt, top_index=top_index, deferred=True)
            return

        for child in ast.iter_child_nodes(node):
            visit(child, top_index=top_index, deferred=deferred)

    tree = ast.parse(source)
    for index, statement in enumerate(tree.body):
        visit(statement, top_index=index, deferred=False)
    return result


def _r62j_name_value(name: str, bindings: dict[str, _Value]) -> _Value:
    if name in bindings:
        return bindings[name]
    if name in _R62J_DANGEROUS_NAMES:
        return _r12._DANGEROUS_CALLABLE
    if name in _R62J_NAMESPACE_HELPERS:
        return frozenset({_Atom("helper", name)})
    return _UNKNOWN


def _r62j_binding_expression_value(
    node: ast.AST,
    bindings: dict[str, _Value],
) -> _Value:
    if isinstance(node, ast.Name):
        return _r62j_name_value(node.id, bindings)

    if isinstance(node, ast.Attribute):
        base = _r62j_binding_expression_value(node.value, bindings)
        if _contains_kind(base, "builtins"):
            if node.attr in _R62J_DANGEROUS_NAMES:
                return _r12._DANGEROUS_CALLABLE
            if node.attr in _R62J_NAMESPACE_HELPERS:
                return frozenset({_Atom("helper", node.attr)})
            if node.attr == "__dict__":
                return _r12._BUILTINS_NAMESPACE
        return _UNKNOWN

    if isinstance(node, ast.IfExp):
        return _r12._merge_values(
            _r62j_binding_expression_value(node.body, bindings),
            _r62j_binding_expression_value(node.orelse, bindings),
        )

    return _UNKNOWN


def _r62j_assign_names(
    target: ast.AST,
    value: _Value,
    bindings: dict[str, _Value],
) -> None:
    for name in _r62h._r62h_target_names(target):
        bindings[name] = value


def _r62j_apply_straight_line_module_binding(
    node: ast.stmt,
    bindings: dict[str, _Value],
) -> None:
    if isinstance(node, ast.Delete):
        for target in node.targets:
            for name in _r62h._r62h_target_names(target):
                bindings.pop(name, None)
        return

    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
        bindings[node.name] = _UNKNOWN
        return

    if isinstance(node, ast.Import):
        for alias in node.names:
            name = alias.asname or alias.name.split(".", 1)[0]
            bindings[name] = (
                _r12._BUILTINS_NAMESPACE
                if alias.name == "builtins"
                else _UNKNOWN
            )
        return

    if isinstance(node, ast.ImportFrom):
        for alias in node.names:
            if alias.name == "*":
                continue
            name = alias.asname or alias.name
            if node.level == 0 and node.module == "builtins":
                if alias.name in _R62J_DANGEROUS_NAMES:
                    bindings[name] = _r12._DANGEROUS_CALLABLE
                elif alias.name in _R62J_NAMESPACE_HELPERS:
                    bindings[name] = frozenset({_Atom("helper", alias.name)})
                elif alias.name == "__dict__":
                    bindings[name] = _r12._BUILTINS_NAMESPACE
                else:
                    bindings[name] = _UNKNOWN
            else:
                bindings[name] = _UNKNOWN
        return

    if isinstance(node, ast.Assign):
        value = _r62j_binding_expression_value(node.value, bindings)
        for target in node.targets:
            _r62j_assign_names(target, value, bindings)
        return

    if isinstance(node, ast.AnnAssign):
        value = (
            _r62j_binding_expression_value(node.value, bindings)
            if node.value is not None
            else _UNKNOWN
        )
        _r62j_assign_names(node.target, value, bindings)
        return

    if isinstance(node, ast.AugAssign):
        _r62j_assign_names(node.target, _UNKNOWN, bindings)


def _r62j_module_states(source: str) -> tuple[dict[str, _Value], ...]:
    tree = ast.parse(source)
    bindings: dict[str, _Value] = {"__builtins__": _r12._BUILTINS_NAMESPACE}
    states: list[dict[str, _Value]] = []
    for statement in tree.body:
        _r62j_apply_straight_line_module_binding(statement, bindings)
        states.append(bindings.copy())
    return tuple(states)


def _r62j_is_execution_authority(value: _Value) -> bool:
    return any(
        _contains_kind(value, kind)
        for kind in ("builtins", "dangerous", "helper")
    )


def _r62j_future_authority_by_call(
    source: str,
) -> dict[tuple[int, int], dict[str, tuple[_Value, bool]]]:
    deferred_calls = _r62j_deferred_call_top_indexes(source)
    states = _r62j_module_states(source)
    result: dict[tuple[int, int], dict[str, tuple[_Value, bool]]] = {}

    for position, top_index in deferred_calls.items():
        suffix = states[top_index:]
        names: set[str] = set()
        for state in suffix:
            names.update(state)

        future: dict[str, tuple[_Value, bool]] = {}
        for name in names:
            values = [state[name] for state in suffix if name in state]
            authority_values = [
                value for value in values if _r62j_is_execution_authority(value)
            ]
            if not authority_values:
                continue
            merged = _r12._merge_values(*authority_values)
            definitely_present = all(name in state for state in suffix)
            future[name] = (merged, definitely_present)
        if future:
            result[position] = future

    return result


def _r62j_enrich_namespace(
    value: _Value,
    future: dict[str, tuple[_Value, bool]],
) -> _Value:
    atoms = set(value)
    for name, (selected, definitely_present) in sorted(future.items()):
        token = f"s:{name}"
        atoms.add(_Atom(_r55._R55_PRESENT_KEY_KIND, token))
        if not definitely_present:
            atoms.add(_Atom(_r55._R55_MAYBE_MISSING_KEY_KIND, token))
        atoms.update(
            _r15._selected_slot_atom(token, atom)
            for atom in selected
        )
    return frozenset(atoms)


class _R62JDeferredGlobalsBindingScanner(
    _r62i._R62IModuleAndParameterNamespaceScanner
):
    """Preserve straight-line module authority visible after a deferred definition.

    R62I models exact module bindings at the lexical position of a ``globals()``
    call. Function, lambda, and generator bodies can execute later, after a
    subsequent top-level statement has introduced a module alias. Preserve the
    bounded execution-authority values from those later straight-line bindings
    without treating arbitrary future values as dangerous or changing immediate
    module/class/default evaluation semantics.
    """

    def __init__(self) -> None:
        super().__init__()
        self._r62j_future_authority_by_call: dict[
            tuple[int, int], dict[str, tuple[_Value, bool]]
        ] = {}

    def scan(self, source: str) -> tuple[str, ...]:
        self._r62j_future_authority_by_call = _r62j_future_authority_by_call(source)
        return super().scan(source)

    def _evaluate_special_call(
        self,
        helper: _Atom,
        arguments: list[_Value],
    ) -> _Value:
        result = super()._evaluate_special_call(helper, arguments)
        if (
            helper.kind == "helper"
            and helper.text == "globals"
            and not arguments
            and self._r62i_call_position_stack
        ):
            future = self._r62j_future_authority_by_call.get(
                self._r62i_call_position_stack[-1]
            )
            if future:
                return _r62j_enrich_namespace(result, future)
        return result


def _r62j_dynamic_execution_markers_from_source(source: str) -> tuple[str, ...]:
    return _R62JDeferredGlobalsBindingScanner().scan(source)


def _runtime_result(source: str) -> object:
    namespace: dict[str, object] = {}
    exec(source, namespace)
    return namespace["result"]


def test_r62j_predecessor_reproduces_late_module_alias_false_negatives() -> None:
    sources = (
        """\
def run():
    return globals()["b"].eval("1+1")
import builtins as b
result = run()
""",
        """\
def run():
    return globals()["g"]()["__builtins__"]["eval"]("1+1")
from builtins import globals as g
result = run()
""",
        """\
def run():
    return globals()["namespace"]["eval"]("1+1")
from builtins import __dict__ as namespace
result = run()
""",
    )

    for source in sources:
        assert _runtime_result(source) == 2
        assert _r62i._r62i_dynamic_execution_markers_from_source(source) == ()


def test_r62j_late_module_authority_is_visible_to_deferred_globals() -> None:
    sources = (
        """\
def run():
    return globals()["b"].eval("1+1")
import builtins as b
result = run()
""",
        """\
def run():
    return globals()["g"]()["__builtins__"]["eval"]("1+1")
from builtins import globals as g
result = run()
""",
        """\
def run():
    return globals()["namespace"]["eval"]("1+1")
from builtins import __dict__ as namespace
result = run()
""",
    )

    for source in sources:
        assert _runtime_result(source) == 2
        assert _r62j_dynamic_execution_markers_from_source(source) == ("call:2",)


def test_r62j_transitive_late_alias_keeps_predecessor_binding_and_adds_call() -> None:
    source = """\
def run():
    return globals()["alias"].eval("1+1")
import builtins as b
alias = b
result = run()
"""

    assert _runtime_result(source) == 2
    assert _r62i._r62i_dynamic_execution_markers_from_source(source) == (
        "binding:4",
    )
    assert _r62j_dynamic_execution_markers_from_source(source) == (
        "call:2",
        "binding:4",
    )


def test_r62j_late_safe_bindings_do_not_invent_authority() -> None:
    sources = (
        """\
def run():
    return globals()["candidate"]("abc")
candidate = len
result = run()
""",
        """\
def run():
    return globals().get("candidate", len)("abc")
result = run()
""",
    )

    for source in sources:
        assert _runtime_result(source) == 3
        assert _r62j_dynamic_execution_markers_from_source(source) == ()


def test_r62j_existing_r62i_and_scope_precision_remain_authoritative() -> None:
    explicit_module = """\
import builtins
def run():
    return globals()["builtins"].eval("1+1")
result = run()
"""
    impossible_nested = """\
def run():
    return vars()["__builtins__"].eval("1+1")
try:
    result = run()
except KeyError:
    result = 3
"""
    local_alias = """\
def run():
    import builtins as b
    return locals()["b"].eval("1+1")
result = run()
"""

    assert _runtime_result(explicit_module) == 2
    assert _runtime_result(impossible_nested) == 3
    assert _runtime_result(local_alias) == 2
    assert _r62j_dynamic_execution_markers_from_source(explicit_module) == ("call:3",)
    assert _r62j_dynamic_execution_markers_from_source(impossible_nested) == ()
    assert _r62j_dynamic_execution_markers_from_source(local_alias) == ("call:3",)


def test_r62j_complete_owner_and_oracle_surface_has_no_dynamic_execution() -> None:
    paths = (*_owner_paths(), _FULL_CLOSURE_ORACLE_PATH)

    for path in paths:
        assert _r62j_dynamic_execution_markers_from_source(
            path.read_text(encoding="utf-8")
        ) == (), path

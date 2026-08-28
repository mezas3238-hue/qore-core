from __future__ import annotations

import ast

import test_universal_cross_asset_conformance_final_owner_r12_guards as _r12
import test_universal_cross_asset_conformance_final_owner_r62h_guards as _r62h
import test_universal_cross_asset_conformance_final_owner_r62i_guards as _r62i
import test_universal_cross_asset_conformance_final_owner_r62j_guards as _r62j
from test_universal_cross_asset_conformance_final_owner_r12_guards import (
    _FULL_CLOSURE_ORACLE_PATH,
    _owner_paths,
    _Value,
)

_R62KOwner = tuple[int, int]


def _r62k_top_level_owner_calls(source: str) -> dict[tuple[int, int], _R62KOwner]:
    result: dict[tuple[int, int], _R62KOwner] = {}
    tree = ast.parse(source)

    for statement in tree.body:
        if not isinstance(statement, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        owner = (statement.lineno, statement.col_offset)
        for body_statement in statement.body:
            for node in ast.walk(body_statement):
                if isinstance(node, ast.Call):
                    result[(node.lineno, node.col_offset)] = owner
    return result


def _r62k_immediate_called_owners(
    node: ast.AST,
    owner_bindings: dict[str, _R62KOwner],
) -> frozenset[_R62KOwner]:
    result: set[_R62KOwner] = set()

    def visit(current: ast.AST) -> None:
        if isinstance(current, ast.Call):
            if isinstance(current.func, ast.Name):
                owner = owner_bindings.get(current.func.id)
                if owner is not None:
                    result.add(owner)
            for child in ast.iter_child_nodes(current):
                visit(child)
            return

        if isinstance(current, (ast.FunctionDef, ast.AsyncFunctionDef)):
            immediate_nodes: list[ast.AST] = [
                *current.decorator_list,
                *current.args.defaults,
                *(item for item in current.args.kw_defaults if item is not None),
            ]
            for argument in (
                *current.args.posonlyargs,
                *current.args.args,
                *current.args.kwonlyargs,
            ):
                if argument.annotation is not None:
                    immediate_nodes.append(argument.annotation)
            if current.args.vararg is not None and current.args.vararg.annotation is not None:
                immediate_nodes.append(current.args.vararg.annotation)
            if current.args.kwarg is not None and current.args.kwarg.annotation is not None:
                immediate_nodes.append(current.args.kwarg.annotation)
            if current.returns is not None:
                immediate_nodes.append(current.returns)
            for child in immediate_nodes:
                visit(child)
            return

        if isinstance(current, ast.Lambda):
            for child in (
                *current.args.defaults,
                *(item for item in current.args.kw_defaults if item is not None),
            ):
                visit(child)
            return

        if isinstance(current, ast.GeneratorExp):
            visit(current.generators[0].iter)
            return

        for child in ast.iter_child_nodes(current):
            visit(child)

    visit(node)
    return frozenset(result)


def _r62k_assign_owner_names(
    target: ast.AST,
    owner: _R62KOwner | None,
    owner_bindings: dict[str, _R62KOwner],
) -> None:
    for name in _r62h._r62h_target_names(target):
        if owner is None:
            owner_bindings.pop(name, None)
        else:
            owner_bindings[name] = owner


def _r62k_apply_owner_binding(
    node: ast.stmt,
    owner_bindings: dict[str, _R62KOwner],
) -> None:
    if isinstance(node, ast.Delete):
        for target in node.targets:
            for name in _r62h._r62h_target_names(target):
                owner_bindings.pop(name, None)
        return

    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
        owner_bindings[node.name] = (node.lineno, node.col_offset)
        return

    if isinstance(node, ast.ClassDef):
        owner_bindings.pop(node.name, None)
        return

    if isinstance(node, ast.Import):
        for alias in node.names:
            owner_bindings.pop(alias.asname or alias.name.split(".", 1)[0], None)
        return

    if isinstance(node, ast.ImportFrom):
        for alias in node.names:
            if alias.name != "*":
                owner_bindings.pop(alias.asname or alias.name, None)
        return

    if isinstance(node, ast.Assign):
        owner = (
            owner_bindings.get(node.value.id)
            if isinstance(node.value, ast.Name)
            else None
        )
        for target in node.targets:
            _r62k_assign_owner_names(target, owner, owner_bindings)
        return

    if isinstance(node, ast.AnnAssign):
        owner = (
            owner_bindings.get(node.value.id)
            if isinstance(node.value, ast.Name)
            else None
        ) if node.value is not None else None
        _r62k_assign_owner_names(node.target, owner, owner_bindings)
        return

    if isinstance(node, ast.AugAssign):
        _r62k_assign_owner_names(node.target, None, owner_bindings)


def _r62k_escaped_owners(source: str) -> frozenset[_R62KOwner]:
    """Return owners used outside the bounded immediate direct-name model."""

    tree = ast.parse(source)
    owner_bindings: dict[str, _R62KOwner] = {}
    escaped: set[_R62KOwner] = set()

    def visit_use(node: ast.AST, *, immediate: bool) -> None:
        if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load):
            owner = owner_bindings.get(node.id)
            if owner is not None:
                escaped.add(owner)
            return

        if isinstance(node, ast.Call):
            direct_owner = (
                owner_bindings.get(node.func.id)
                if isinstance(node.func, ast.Name)
                else None
            )
            if direct_owner is not None:
                if not immediate:
                    escaped.add(direct_owner)
            else:
                visit_use(node.func, immediate=immediate)
            for argument in node.args:
                visit_use(argument, immediate=immediate)
            for keyword in node.keywords:
                visit_use(keyword.value, immediate=immediate)
            return

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
                visit_use(child, immediate=immediate)
            for statement in node.body:
                visit_use(statement, immediate=False)
            return

        if isinstance(node, ast.Lambda):
            for child in (
                *node.args.defaults,
                *(item for item in node.args.kw_defaults if item is not None),
            ):
                visit_use(child, immediate=immediate)
            visit_use(node.body, immediate=False)
            return

        if isinstance(node, ast.GeneratorExp):
            visit_use(node.generators[0].iter, immediate=immediate)
            visit_use(node.elt, immediate=False)
            for index, generator in enumerate(node.generators):
                if index:
                    visit_use(generator.iter, immediate=False)
                for condition in generator.ifs:
                    visit_use(condition, immediate=False)
            return

        for child in ast.iter_child_nodes(node):
            visit_use(child, immediate=immediate)

    for statement in tree.body:
        safe_alias = False
        if (
            isinstance(statement, ast.Assign)
            and isinstance(statement.value, ast.Name)
            and statement.value.id in owner_bindings
            and all(isinstance(target, ast.Name) for target in statement.targets)
        ):
            safe_alias = True
        elif (
            isinstance(statement, ast.AnnAssign)
            and statement.value is not None
            and isinstance(statement.value, ast.Name)
            and statement.value.id in owner_bindings
            and isinstance(statement.target, ast.Name)
        ):
            safe_alias = True

        if not safe_alias:
            visit_use(statement, immediate=True)
        _r62k_apply_owner_binding(statement, owner_bindings)

    return frozenset(escaped)


def _r62k_observable_states_by_owner(
    source: str,
) -> dict[_R62KOwner, tuple[dict[str, _Value], ...]]:
    tree = ast.parse(source)
    authority_bindings: dict[str, _Value] = {
        "__builtins__": _r12._BUILTINS_NAMESPACE
    }
    owner_bindings: dict[str, _R62KOwner] = {}
    observations: dict[_R62KOwner, list[dict[str, _Value]]] = {}

    for statement in tree.body:
        for owner in _r62k_immediate_called_owners(statement, owner_bindings):
            observations.setdefault(owner, []).append(authority_bindings.copy())
        _r62j._r62j_apply_straight_line_module_binding(statement, authority_bindings)
        _r62k_apply_owner_binding(statement, owner_bindings)

    final_state = authority_bindings.copy()
    for owner in frozenset(owner_bindings.values()):
        observations.setdefault(owner, []).append(final_state)

    return {owner: tuple(states) for owner, states in observations.items()}


def _r62k_authority_from_states(
    states: tuple[dict[str, _Value], ...],
) -> dict[str, tuple[_Value, bool]]:
    names: set[str] = set()
    for state in states:
        names.update(state)

    result: dict[str, tuple[_Value, bool]] = {}
    for name in names:
        values = [state[name] for state in states if name in state]
        authority_values = [
            value for value in values if _r62j._r62j_is_execution_authority(value)
        ]
        if not authority_values:
            continue
        result[name] = (
            _r12._merge_values(*authority_values),
            all(name in state for state in states),
        )
    return result


def _r62k_observable_authority_by_call(
    source: str,
) -> dict[tuple[int, int], dict[str, tuple[_Value, bool]]]:
    fallback = _r62j._r62j_future_authority_by_call(source)
    owner_by_call = _r62k_top_level_owner_calls(source)
    escaped_owners = _r62k_escaped_owners(source)
    states_by_owner = _r62k_observable_states_by_owner(source)
    result: dict[tuple[int, int], dict[str, tuple[_Value, bool]]] = {}

    for position, future in fallback.items():
        owner = owner_by_call.get(position)
        if owner is None or owner in escaped_owners:
            result[position] = future
            continue
        states = states_by_owner.get(owner)
        if not states:
            continue
        observable = _r62k_authority_from_states(states)
        if observable:
            result[position] = observable

    return result


class _R62KObservableDeferredGlobalsScanner(
    _r62j._R62JDeferredGlobalsBindingScanner
):
    """Use callable-observable module states instead of every future state.

    R62J correctly notices that a deferred function body can observe module
    bindings introduced after its lexical definition. Its suffix union is too
    broad when dangerous authority exists only transiently and is rebound before
    every observable invocation. R62K follows direct/aliased straight-line
    top-level invocations of top-level functions and the final state while such a
    function remains module-reachable. If the callable escapes that bounded
    direct-name model, including through another deferred body, R62K retains the
    conservative R62J suffix model. A non-escaped callable with no modeled
    invocation and no final reachability has no observable module state.
    """

    def scan(self, source: str) -> tuple[str, ...]:
        self._r62j_future_authority_by_call = _r62k_observable_authority_by_call(source)
        return _r62i._R62IModuleAndParameterNamespaceScanner.scan(self, source)


def _r62k_dynamic_execution_markers_from_source(source: str) -> tuple[str, ...]:
    return _R62KObservableDeferredGlobalsScanner().scan(source)


def _runtime_result(source: str) -> object:
    namespace: dict[str, object] = {}
    exec(source, namespace)
    return namespace["result"]


def test_r62k_predecessor_reproduces_transient_authority_false_positive() -> None:
    sources = (
        """\
def run():
    return globals()["b"].eval("1+1")
import builtins as b
b = len
try:
    result = run()
except AttributeError:
    result = 3
""",
        """\
def run():
    return globals()["b"].eval("1+1")
import builtins as b
b = len
result = 3
""",
    )

    for source in sources:
        assert _runtime_result(source) == 3
        assert "call:2" in _r62j._r62j_dynamic_execution_markers_from_source(source)


def test_r62k_transient_authority_rebound_before_observation_is_clean() -> None:
    sources = (
        """\
def run():
    return globals()["b"].eval("1+1")
import builtins as b
b = len
try:
    result = run()
except AttributeError:
    result = 3
""",
        """\
def run():
    return globals()["b"].eval("1+1")
import builtins as b
b = len
result = 3
""",
        """\
def run():
    return globals()["b"].eval("1+1")
alias = run
import builtins as b
b = len
try:
    result = alias()
except AttributeError:
    result = 3
""",
    )

    for source in sources:
        assert _runtime_result(source) == 3
        assert _r62k_dynamic_execution_markers_from_source(source) == ()


def test_r62k_dangerous_state_at_direct_or_alias_invocation_fails_closed() -> None:
    sources = (
        """\
def run():
    return globals()["b"].eval("1+1")
import builtins as b
result = run()
b = len
""",
        """\
def run():
    return globals()["b"].eval("1+1")
alias = run
import builtins as b
result = alias()
b = len
""",
    )

    for source in sources:
        assert _runtime_result(source) == 2
        assert "call:2" in _r62k_dynamic_execution_markers_from_source(source)


def test_r62k_escaped_callable_falls_back_to_future_authority() -> None:
    sources = (
        """\
def run():
    return globals()["b"].eval("1+1")
holder = {"run": run}
import builtins as b
result = holder["run"]()
b = len
""",
        """\
def run():
    return globals()["b"].eval("1+1")
holder = [run]
import builtins as b
result = holder[0]()
b = len
""",
        """\
def run():
    return globals()["b"].eval("1+1")
def wrapper():
    return run()
import builtins as b
result = wrapper()
b = len
""",
    )

    for source in sources:
        assert _runtime_result(source) == 2
        assert "call:2" in _r62k_dynamic_execution_markers_from_source(source)


def test_r62k_unobserved_unreachable_callable_drops_transient_authority() -> None:
    sources = (
        """\
def run():
    return globals()["b"].eval("1+1")
import builtins as b
run = len
b = len
result = 3
""",
        """\
def run():
    return globals()["b"].eval("1+1")
import builtins as b
del run
b = len
result = 3
""",
    )

    for source in sources:
        assert _runtime_result(source) == 3
        assert "call:2" in _r62j._r62j_dynamic_execution_markers_from_source(source)
        assert _r62k_dynamic_execution_markers_from_source(source) == ()


def test_r62k_final_reachable_dangerous_state_remains_fail_closed() -> None:
    source = """\
def run():
    return globals()["b"].eval("1+1")
import builtins as b
result = 3
"""

    assert _runtime_result(source) == 3
    assert _r62k_dynamic_execution_markers_from_source(source) == ("call:2",)


def test_r62k_r62j_late_authority_and_scope_precision_remain_authoritative() -> None:
    late = """\
def run():
    return globals()["b"].eval("1+1")
import builtins as b
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

    assert _runtime_result(late) == 2
    assert _runtime_result(impossible_nested) == 3
    assert _runtime_result(local_alias) == 2
    assert _r62k_dynamic_execution_markers_from_source(late) == ("call:2",)
    assert _r62k_dynamic_execution_markers_from_source(impossible_nested) == ()
    assert _r62k_dynamic_execution_markers_from_source(local_alias) == ("call:3",)


def test_r62k_complete_owner_and_oracle_surface_has_no_dynamic_execution() -> None:
    paths = (*_owner_paths(), _FULL_CLOSURE_ORACLE_PATH)

    for path in paths:
        assert _r62k_dynamic_execution_markers_from_source(
            path.read_text(encoding="utf-8")
        ) == (), path

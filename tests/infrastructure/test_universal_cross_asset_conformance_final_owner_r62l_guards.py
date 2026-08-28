from __future__ import annotations

import ast

import test_universal_cross_asset_conformance_final_owner_r12_guards as _r12
import test_universal_cross_asset_conformance_final_owner_r62h_guards as _r62h
import test_universal_cross_asset_conformance_final_owner_r62i_guards as _r62i
import test_universal_cross_asset_conformance_final_owner_r62j_guards as _r62j
import test_universal_cross_asset_conformance_final_owner_r62k_guards as _r62k
from test_universal_cross_asset_conformance_final_owner_r12_guards import (
    _FULL_CLOSURE_ORACLE_PATH,
    _UNKNOWN,
    _owner_paths,
    _Value,
)

_R62LOwnerSet = frozenset[_r62k._R62KOwner]
_R62LOwnerBindings = dict[str, _R62LOwnerSet]
_R62LAuthorityBindings = dict[str, _Value]
_R62LState = tuple[_R62LAuthorityBindings, _R62LOwnerBindings]
_R62L_MAX_STATES = 64


def _r62l_copy_state(state: _R62LState) -> _R62LState:
    authority, owners = state
    return authority.copy(), owners.copy()


def _r62l_merged_state(states: list[_R62LState]) -> _R62LState:
    authority_names = {name for authority, _ in states for name in authority}
    owner_names = {name for _, owners in states for name in owners}
    authority: _R62LAuthorityBindings = {}
    owners: _R62LOwnerBindings = {}
    for name in authority_names:
        values = [bindings[name] for bindings, _ in states if name in bindings]
        authority[name] = _r12._merge_values(*values)
    for name in owner_names:
        merged: set[_r62k._R62KOwner] = set()
        for _, bindings in states:
            merged.update(bindings.get(name, frozenset()))
        if merged:
            owners[name] = frozenset(merged)
    return authority, owners


def _r62l_bound_states(states: list[_R62LState]) -> list[_R62LState]:
    if len(states) <= _R62L_MAX_STATES:
        return states
    return [_r62l_merged_state(states)]


def _r62l_assign_owner_names(
    target: ast.AST,
    owners: _R62LOwnerSet,
    owner_bindings: _R62LOwnerBindings,
) -> None:
    for name in _r62h._r62h_target_names(target):
        if owners:
            owner_bindings[name] = owners
        else:
            owner_bindings.pop(name, None)


def _r62l_owner_expression_value(
    node: ast.AST,
    owner_bindings: _R62LOwnerBindings,
) -> _R62LOwnerSet:
    if isinstance(node, ast.Name):
        return owner_bindings.get(node.id, frozenset())
    if isinstance(node, ast.IfExp):
        return frozenset(
            (
                *_r62l_owner_expression_value(node.body, owner_bindings),
                *_r62l_owner_expression_value(node.orelse, owner_bindings),
            )
        )
    return frozenset()


def _r62l_apply_owner_binding(
    node: ast.stmt,
    owner_bindings: _R62LOwnerBindings,
) -> None:
    if isinstance(node, ast.Delete):
        for target in node.targets:
            _r62l_assign_owner_names(target, frozenset(), owner_bindings)
        return
    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
        owner_bindings[node.name] = frozenset({(node.lineno, node.col_offset)})
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
        owners = _r62l_owner_expression_value(node.value, owner_bindings)
        for target in node.targets:
            _r62l_assign_owner_names(target, owners, owner_bindings)
        return
    if isinstance(node, ast.AnnAssign):
        owners = (
            _r62l_owner_expression_value(node.value, owner_bindings)
            if node.value is not None
            else frozenset()
        )
        _r62l_assign_owner_names(node.target, owners, owner_bindings)
        return
    if isinstance(node, ast.AugAssign):
        _r62l_assign_owner_names(node.target, frozenset(), owner_bindings)


def _r62l_record_timeline(
    timeline: dict[int, list[_R62LAuthorityBindings]],
    top_index: int,
    authority: _R62LAuthorityBindings,
) -> None:
    timeline.setdefault(top_index, []).append(authority.copy())


def _r62l_record_owner_calls(
    owners: _R62LOwnerSet,
    authority: _R62LAuthorityBindings,
    observations: dict[_r62k._R62KOwner, list[_R62LAuthorityBindings]],
) -> None:
    for owner in owners:
        observations.setdefault(owner, []).append(authority.copy())


def _r62l_eval_expression(
    node: ast.AST,
    state: _R62LState,
    *,
    top_index: int,
    timeline: dict[int, list[_R62LAuthorityBindings]],
    observations: dict[_r62k._R62KOwner, list[_R62LAuthorityBindings]],
    precision_lost: list[bool],
) -> None:
    authority, owner_bindings = state

    if isinstance(node, ast.NamedExpr):
        _r62l_eval_expression(
            node.value,
            state,
            top_index=top_index,
            timeline=timeline,
            observations=observations,
            precision_lost=precision_lost,
        )
        value = _r62j._r62j_binding_expression_value(node.value, authority)
        _r62j._r62j_assign_names(node.target, value, authority)
        owners = _r62l_owner_expression_value(node.value, owner_bindings)
        _r62l_assign_owner_names(node.target, owners, owner_bindings)
        _r62l_record_timeline(timeline, top_index, authority)
        return

    if isinstance(node, ast.Call):
        _r62l_eval_expression(
            node.func,
            state,
            top_index=top_index,
            timeline=timeline,
            observations=observations,
            precision_lost=precision_lost,
        )
        called_owners = (
            owner_bindings.get(node.func.id, frozenset())
            if isinstance(node.func, ast.Name)
            else frozenset()
        )
        arguments: list[ast.AST] = [
            *node.args,
            *(item.value for item in node.keywords),
        ]
        arguments.sort(key=lambda item: (item.lineno, item.col_offset))
        for argument in arguments:
            _r62l_eval_expression(
                argument,
                state,
                top_index=top_index,
                timeline=timeline,
                observations=observations,
                precision_lost=precision_lost,
            )
        _r62l_record_owner_calls(called_owners, authority, observations)
        _r62l_record_timeline(timeline, top_index, authority)
        return

    if isinstance(node, ast.Lambda):
        for default in (
            *node.args.defaults,
            *(item for item in node.args.kw_defaults if item is not None),
        ):
            _r62l_eval_expression(
                default,
                state,
                top_index=top_index,
                timeline=timeline,
                observations=observations,
                precision_lost=precision_lost,
            )
        return

    if isinstance(node, ast.GeneratorExp):
        _r62l_eval_expression(
            node.generators[0].iter,
            state,
            top_index=top_index,
            timeline=timeline,
            observations=observations,
            precision_lost=precision_lost,
        )
        precision_lost[0] = True
        return

    if isinstance(
        node,
        (ast.ListComp, ast.SetComp, ast.DictComp, ast.BoolOp, ast.IfExp),
    ):
        precision_lost[0] = True
        return

    if isinstance(node, ast.Dict):
        for key, value in zip(node.keys, node.values, strict=True):
            if key is not None:
                _r62l_eval_expression(
                    key,
                    state,
                    top_index=top_index,
                    timeline=timeline,
                    observations=observations,
                    precision_lost=precision_lost,
                )
            _r62l_eval_expression(
                value,
                state,
                top_index=top_index,
                timeline=timeline,
                observations=observations,
                precision_lost=precision_lost,
            )
        return

    if isinstance(node, ast.Compare):
        _r62l_eval_expression(
            node.left,
            state,
            top_index=top_index,
            timeline=timeline,
            observations=observations,
            precision_lost=precision_lost,
        )
        for comparator in node.comparators:
            _r62l_eval_expression(
                comparator,
                state,
                top_index=top_index,
                timeline=timeline,
                observations=observations,
                precision_lost=precision_lost,
            )
        return

    if isinstance(node, ast.BinOp):
        children = (node.left, node.right)
    elif isinstance(node, (ast.Tuple, ast.List, ast.Set)):
        children = tuple(node.elts)
    elif isinstance(node, ast.UnaryOp):
        children = (node.operand,)
    elif isinstance(node, ast.Attribute):
        children = (node.value,)
    elif isinstance(node, ast.Subscript):
        children = (node.value, node.slice)
    elif isinstance(node, ast.Starred):
        children = (node.value,)
    elif isinstance(node, ast.FormattedValue):
        children = (node.value,)
    elif isinstance(node, ast.JoinedStr):
        children = tuple(node.values)
    else:
        children = ()

    for child in children:
        _r62l_eval_expression(
            child,
            state,
            top_index=top_index,
            timeline=timeline,
            observations=observations,
            precision_lost=precision_lost,
        )


def _r62l_static_bool(node: ast.AST) -> bool | None:
    if isinstance(node, ast.Constant) and isinstance(node.value, bool):
        return node.value
    return None


def _r62l_process_block(
    statements: list[ast.stmt],
    states: list[_R62LState],
    *,
    top_index: int,
    timeline: dict[int, list[_R62LAuthorityBindings]],
    observations: dict[_r62k._R62KOwner, list[_R62LAuthorityBindings]],
    precision_lost: list[bool],
) -> list[_R62LState]:
    current = states
    for statement in statements:
        next_states: list[_R62LState] = []
        for state in current:
            next_states.extend(
                _r62l_process_statement(
                    statement,
                    state,
                    top_index=top_index,
                    timeline=timeline,
                    observations=observations,
                    precision_lost=precision_lost,
                )
            )
        current = _r62l_bound_states(next_states)
    return current


def _r62l_process_statement(
    node: ast.stmt,
    state: _R62LState,
    *,
    top_index: int,
    timeline: dict[int, list[_R62LAuthorityBindings]],
    observations: dict[_r62k._R62KOwner, list[_R62LAuthorityBindings]],
    precision_lost: list[bool],
) -> list[_R62LState]:
    authority, owner_bindings = state
    _r62l_record_timeline(timeline, top_index, authority)

    if isinstance(node, ast.If):
        _r62l_eval_expression(
            node.test,
            state,
            top_index=top_index,
            timeline=timeline,
            observations=observations,
            precision_lost=precision_lost,
        )
        truth = _r62l_static_bool(node.test)
        if truth is True:
            return _r62l_process_block(
                node.body,
                [_r62l_copy_state(state)],
                top_index=top_index,
                timeline=timeline,
                observations=observations,
                precision_lost=precision_lost,
            )
        if truth is False:
            if not node.orelse:
                return [_r62l_copy_state(state)]
            return _r62l_process_block(
                node.orelse,
                [_r62l_copy_state(state)],
                top_index=top_index,
                timeline=timeline,
                observations=observations,
                precision_lost=precision_lost,
            )
        body_states = _r62l_process_block(
            node.body,
            [_r62l_copy_state(state)],
            top_index=top_index,
            timeline=timeline,
            observations=observations,
            precision_lost=precision_lost,
        )
        else_states = (
            _r62l_process_block(
                node.orelse,
                [_r62l_copy_state(state)],
                top_index=top_index,
                timeline=timeline,
                observations=observations,
                precision_lost=precision_lost,
            )
            if node.orelse
            else [_r62l_copy_state(state)]
        )
        return _r62l_bound_states([*body_states, *else_states])

    if isinstance(node, (ast.Try, ast.TryStar)):
        successful = _r62l_process_block(
            node.body,
            [_r62l_copy_state(state)],
            top_index=top_index,
            timeline=timeline,
            observations=observations,
            precision_lost=precision_lost,
        )
        if node.orelse:
            successful = _r62l_process_block(
                node.orelse,
                successful,
                top_index=top_index,
                timeline=timeline,
                observations=observations,
                precision_lost=precision_lost,
            )
        continued = list(successful)
        for handler in node.handlers:
            handler_state = _r62l_copy_state(state)
            if handler.type is not None:
                _r62l_eval_expression(
                    handler.type,
                    handler_state,
                    top_index=top_index,
                    timeline=timeline,
                    observations=observations,
                    precision_lost=precision_lost,
                )
            if handler.name is not None:
                handler_state[0][handler.name] = _UNKNOWN
                handler_state[1].pop(handler.name, None)
            continued.extend(
                _r62l_process_block(
                    handler.body,
                    [handler_state],
                    top_index=top_index,
                    timeline=timeline,
                    observations=observations,
                    precision_lost=precision_lost,
                )
            )
        continued = _r62l_bound_states(continued)
        if node.finalbody:
            continued = _r62l_process_block(
                node.finalbody,
                continued,
                top_index=top_index,
                timeline=timeline,
                observations=observations,
                precision_lost=precision_lost,
            )
        return continued

    if isinstance(node, (ast.With, ast.AsyncWith)):
        if isinstance(node, ast.AsyncWith):
            precision_lost[0] = True
        working = _r62l_copy_state(state)
        for item in node.items:
            _r62l_eval_expression(
                item.context_expr,
                working,
                top_index=top_index,
                timeline=timeline,
                observations=observations,
                precision_lost=precision_lost,
            )
            if item.optional_vars is not None:
                _r62j._r62j_assign_names(item.optional_vars, _UNKNOWN, working[0])
                _r62l_assign_owner_names(
                    item.optional_vars,
                    frozenset(),
                    working[1],
                )
        return _r62l_process_block(
            node.body,
            [working],
            top_index=top_index,
            timeline=timeline,
            observations=observations,
            precision_lost=precision_lost,
        )

    if isinstance(node, (ast.For, ast.AsyncFor)):
        if isinstance(node, ast.AsyncFor):
            precision_lost[0] = True
        working = _r62l_copy_state(state)
        _r62l_eval_expression(
            node.iter,
            working,
            top_index=top_index,
            timeline=timeline,
            observations=observations,
            precision_lost=precision_lost,
        )
        body_state = _r62l_copy_state(working)
        _r62j._r62j_assign_names(node.target, _UNKNOWN, body_state[0])
        _r62l_assign_owner_names(node.target, frozenset(), body_state[1])
        body_states = _r62l_process_block(
            node.body,
            [body_state],
            top_index=top_index,
            timeline=timeline,
            observations=observations,
            precision_lost=precision_lost,
        )
        candidates = _r62l_bound_states([working, *body_states])
        if not node.orelse:
            return candidates
        return _r62l_process_block(
            node.orelse,
            candidates,
            top_index=top_index,
            timeline=timeline,
            observations=observations,
            precision_lost=precision_lost,
        )

    if isinstance(node, ast.While):
        working = _r62l_copy_state(state)
        _r62l_eval_expression(
            node.test,
            working,
            top_index=top_index,
            timeline=timeline,
            observations=observations,
            precision_lost=precision_lost,
        )
        truth = _r62l_static_bool(node.test)
        if truth is False:
            candidates = [working]
        else:
            body_states = _r62l_process_block(
                node.body,
                [_r62l_copy_state(working)],
                top_index=top_index,
                timeline=timeline,
                observations=observations,
                precision_lost=precision_lost,
            )
            candidates = body_states if truth is True else [working, *body_states]
        candidates = _r62l_bound_states(candidates)
        if not node.orelse:
            return candidates
        return _r62l_process_block(
            node.orelse,
            candidates,
            top_index=top_index,
            timeline=timeline,
            observations=observations,
            precision_lost=precision_lost,
        )

    if isinstance(node, ast.Match):
        working = _r62l_copy_state(state)
        _r62l_eval_expression(
            node.subject,
            working,
            top_index=top_index,
            timeline=timeline,
            observations=observations,
            precision_lost=precision_lost,
        )
        precision_lost[0] = True
        candidates = [_r62l_copy_state(working)]
        for case in node.cases:
            candidates.extend(
                _r62l_process_block(
                    case.body,
                    [_r62l_copy_state(working)],
                    top_index=top_index,
                    timeline=timeline,
                    observations=observations,
                    precision_lost=precision_lost,
                )
            )
        return _r62l_bound_states(candidates)

    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
        immediate: list[ast.AST] = [
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
                immediate.append(argument.annotation)
        if node.args.vararg is not None and node.args.vararg.annotation is not None:
            immediate.append(node.args.vararg.annotation)
        if node.args.kwarg is not None and node.args.kwarg.annotation is not None:
            immediate.append(node.args.kwarg.annotation)
        if node.returns is not None:
            immediate.append(node.returns)
        for child in immediate:
            _r62l_eval_expression(
                child,
                state,
                top_index=top_index,
                timeline=timeline,
                observations=observations,
                precision_lost=precision_lost,
            )
        _r62j._r62j_apply_straight_line_module_binding(node, authority)
        _r62l_apply_owner_binding(node, owner_bindings)
        _r62l_record_timeline(timeline, top_index, authority)
        return [state]

    if isinstance(node, ast.ClassDef):
        for child in (
            *node.decorator_list,
            *node.bases,
            *(keyword.value for keyword in node.keywords),
        ):
            _r62l_eval_expression(
                child,
                state,
                top_index=top_index,
                timeline=timeline,
                observations=observations,
                precision_lost=precision_lost,
            )
        flat_owners = {
            name: next(iter(owners))
            for name, owners in owner_bindings.items()
            if len(owners) == 1
        }
        for body_statement in node.body:
            called = _r62k._r62k_immediate_called_owners(
                body_statement,
                flat_owners,
            )
            _r62l_record_owner_calls(called, authority, observations)
        _r62j._r62j_apply_straight_line_module_binding(node, authority)
        _r62l_apply_owner_binding(node, owner_bindings)
        _r62l_record_timeline(timeline, top_index, authority)
        return [state]

    expressions: list[ast.AST] = []
    if isinstance(node, ast.Assign):
        expressions.append(node.value)
    elif isinstance(node, ast.AnnAssign):
        expressions.append(node.annotation)
        if node.value is not None:
            expressions.append(node.value)
    elif isinstance(node, ast.AugAssign):
        expressions.extend((node.target, node.value))
    elif isinstance(node, ast.Expr):
        expressions.append(node.value)
    elif isinstance(node, ast.Assert):
        expressions.append(node.test)
        if node.msg is not None:
            expressions.append(node.msg)
    elif isinstance(node, ast.Raise):
        if node.exc is not None:
            expressions.append(node.exc)
        if node.cause is not None:
            expressions.append(node.cause)

    for expression in expressions:
        _r62l_eval_expression(
            expression,
            state,
            top_index=top_index,
            timeline=timeline,
            observations=observations,
            precision_lost=precision_lost,
        )

    _r62j._r62j_apply_straight_line_module_binding(node, authority)
    _r62l_apply_owner_binding(node, owner_bindings)
    _r62l_record_timeline(timeline, top_index, authority)
    return [state]


def _r62l_flow(
    source: str,
) -> tuple[
    dict[_r62k._R62KOwner, tuple[_R62LAuthorityBindings, ...]],
    dict[int, tuple[_R62LAuthorityBindings, ...]],
    bool,
]:
    tree = ast.parse(source)
    states: list[_R62LState] = [
        ({"__builtins__": _r12._BUILTINS_NAMESPACE}, {})
    ]
    timeline: dict[int, list[_R62LAuthorityBindings]] = {}
    observations: dict[
        _r62k._R62KOwner,
        list[_R62LAuthorityBindings],
    ] = {}
    precision_lost = [False]

    for top_index, statement in enumerate(tree.body):
        next_states: list[_R62LState] = []
        for state in states:
            next_states.extend(
                _r62l_process_statement(
                    statement,
                    _r62l_copy_state(state),
                    top_index=top_index,
                    timeline=timeline,
                    observations=observations,
                    precision_lost=precision_lost,
                )
            )
        states = _r62l_bound_states(next_states)

    for authority, owner_bindings in states:
        reachable = {
            owner
            for owners in owner_bindings.values()
            for owner in owners
        }
        for owner in reachable:
            observations.setdefault(owner, []).append(authority.copy())

    return (
        {owner: tuple(values) for owner, values in observations.items()},
        {index: tuple(values) for index, values in timeline.items()},
        precision_lost[0],
    )


def _r62l_future_authority_by_call(
    source: str,
    timeline: dict[int, tuple[_R62LAuthorityBindings, ...]],
) -> dict[tuple[int, int], dict[str, tuple[_Value, bool]]]:
    result: dict[tuple[int, int], dict[str, tuple[_Value, bool]]] = {}
    deferred = _r62j._r62j_deferred_call_top_indexes(source)
    for position, top_index in deferred.items():
        states = tuple(
            state
            for index in sorted(timeline)
            if index >= top_index
            for state in timeline[index]
        )
        if not states:
            continue
        authority = _r62k._r62k_authority_from_states(states)
        if authority:
            result[position] = authority
    return result


def _r62l_observable_authority_by_call(
    source: str,
) -> dict[tuple[int, int], dict[str, tuple[_Value, bool]]]:
    observations, timeline, precision_lost = _r62l_flow(source)
    fallback = _r62l_future_authority_by_call(source, timeline)
    owner_by_call = _r62k._r62k_top_level_owner_calls(source)
    escaped = _r62k._r62k_escaped_owners(source)
    result: dict[tuple[int, int], dict[str, tuple[_Value, bool]]] = {}

    for position in _r62j._r62j_deferred_call_top_indexes(source):
        owner = owner_by_call.get(position)
        if precision_lost or owner is None or owner in escaped:
            future = fallback.get(position)
            if future:
                result[position] = future
            continue
        states = observations.get(owner)
        if not states:
            continue
        authority = _r62k._r62k_authority_from_states(states)
        if authority:
            result[position] = authority
    return result


class _R62LControlFlowObservableGlobalsScanner(
    _r62k._R62KObservableDeferredGlobalsScanner
):
    """Track bounded module control flow and intra-expression observation order.

    R62K observes only straight-line top-level module bindings and whole-statement
    call sites. R62L adds a bounded abstract module flow for literal/unknown
    ``if`` branches, ``try``/handlers/finally, ``with``, one-iteration loop
    projections, and direct expression sequencing. It preserves a conservative
    future-authority fallback whenever the expression model loses precision or a
    callable escapes the direct-name owner model.
    """

    def scan(self, source: str) -> tuple[str, ...]:
        self._r62j_future_authority_by_call = _r62l_observable_authority_by_call(
            source
        )
        return _r62i._R62IModuleAndParameterNamespaceScanner.scan(self, source)


def _r62l_dynamic_execution_markers_from_source(source: str) -> tuple[str, ...]:
    return _R62LControlFlowObservableGlobalsScanner().scan(source)


def _runtime_result(source: str) -> object:
    namespace: dict[str, object] = {}
    exec(compile(source, "<r62l>", "exec", dont_inherit=True), namespace)
    return namespace["result"]


def test_r62l_predecessor_reproduces_module_control_flow_false_negatives() -> None:
    sources = (
        'def run():\n    return globals()["b"].eval("1+1")\ntry:\n    import builtins as b\nexcept ImportError:\n    pass\nresult = run()\n',
        'def run():\n    return globals()["b"].eval("1+1")\nif True:\n    import builtins as b\nresult = run()\n',
        'def run():\n    return globals()["b"].eval("1+1")\nif True:\n    import builtins as b\n    result = run()\n',
    )
    for source in sources:
        assert _runtime_result(source) == 2
        assert _r62k._r62k_dynamic_execution_markers_from_source(source) == ()


def test_r62l_module_control_flow_authority_fails_closed() -> None:
    sources = (
        'def run():\n    return globals()["b"].eval("1+1")\ntry:\n    import builtins as b\nexcept ImportError:\n    pass\nresult = run()\n',
        'def run():\n    return globals()["b"].eval("1+1")\nif True:\n    import builtins as b\nresult = run()\n',
        'def run():\n    return globals()["b"].eval("1+1")\nif True:\n    import builtins as b\n    result = run()\n',
        'def run():\n    return globals()["b"].eval("1+1")\nfor _ in (0,):\n    import builtins as b\nresult = run()\n',
        'def run():\n    return globals()["b"].eval("1+1")\nwhile True:\n    import builtins as b\n    break\nresult = run()\n',
    )
    for source in sources:
        assert _runtime_result(source) == 2
        assert _r62l_dynamic_execution_markers_from_source(source)


def test_r62l_literal_false_branch_does_not_invent_module_authority() -> None:
    source = 'def run():\n    return globals()["b"].eval("1+1")\nif False:\n    import builtins as b\ntry:\n    result = run()\nexcept KeyError:\n    result = 3\n'
    assert _runtime_result(source) == 3
    assert _r62l_dynamic_execution_markers_from_source(source) == ()


def test_r62l_safe_same_statement_walrus_rebind_precedes_observation() -> None:
    source = 'def run():\n    return getattr(globals()["b"], "eval", lambda _: 3)("1+1")\nimport builtins as b\nresult = ((b := len), run())[1]\n'
    assert _runtime_result(source) == 3
    assert _r62k._r62k_dynamic_execution_markers_from_source(source) == ("call:2",)
    assert _r62l_dynamic_execution_markers_from_source(source) == ()


def test_r62l_dangerous_same_statement_walrus_remains_fail_closed() -> None:
    source = 'import builtins\ndef run():\n    return globals()["b"].eval("1+1")\nb = len\nresult = ((b := builtins), run())[1]\n'
    assert _runtime_result(source) == 2
    assert _r62l_dynamic_execution_markers_from_source(source)


def test_r62l_control_flow_authority_rebound_before_call_stays_clean() -> None:
    source = 'def run():\n    return getattr(globals()["b"], "eval", lambda _: 3)("1+1")\nflag = True\nif flag:\n    import builtins as b\nb = len\nresult = run()\n'
    assert _runtime_result(source) == 3
    assert _r62l_dynamic_execution_markers_from_source(source) == ()


def test_r62l_r62k_regressions_remain_authoritative() -> None:
    dangerous = 'def run():\n    return globals()["b"].eval("1+1")\nimport builtins as b\nresult = run()\nb = len\n'
    transient = 'def run():\n    return globals()["b"].eval("1+1")\nimport builtins as b\nb = len\nresult = 3\n'
    escaped = 'def run():\n    return globals()["b"].eval("1+1")\nholder = {"run": run}\nimport builtins as b\nresult = holder["run"]()\nb = len\n'
    assert _runtime_result(dangerous) == 2
    assert _runtime_result(transient) == 3
    assert _runtime_result(escaped) == 2
    assert _r62l_dynamic_execution_markers_from_source(dangerous)
    assert _r62l_dynamic_execution_markers_from_source(transient) == ()
    assert _r62l_dynamic_execution_markers_from_source(escaped)


def test_r62l_complete_owner_and_oracle_surface_has_no_dynamic_execution() -> None:
    paths = (*_owner_paths(), _FULL_CLOSURE_ORACLE_PATH)
    for path in paths:
        assert _r62l_dynamic_execution_markers_from_source(
            path.read_text(encoding="utf-8")
        ) == (), path

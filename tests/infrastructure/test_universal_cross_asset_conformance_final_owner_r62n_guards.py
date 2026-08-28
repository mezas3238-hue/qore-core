from __future__ import annotations

import ast
import builtins as _py_builtins

import test_universal_cross_asset_conformance_final_owner_r12_guards as _r12
import test_universal_cross_asset_conformance_final_owner_r62i_guards as _r62i
import test_universal_cross_asset_conformance_final_owner_r62j_guards as _r62j
import test_universal_cross_asset_conformance_final_owner_r62k_guards as _r62k
import test_universal_cross_asset_conformance_final_owner_r62l_guards as _r62l
import test_universal_cross_asset_conformance_final_owner_r62m_guards as _r62m
from test_universal_cross_asset_conformance_final_owner_r12_guards import (
    _FULL_CLOSURE_ORACLE_PATH,
    _UNKNOWN,
    _owner_paths,
    _Value,
)


def _r62n_copy_state(state: _r62l._R62LState) -> _r62l._R62LState:
    return _r62m._r62m_copy_state(state)


def _r62n_unique_states(
    states: list[_r62l._R62LState],
) -> list[_r62l._R62LState]:
    result: list[_r62l._R62LState] = []
    for state in states:
        if state not in result:
            result.append(state)
    return result


_R62N_EXCEPTION_TAG = "\x00r62n_exception"
_R62N_EXCEPTION_KIND = "r62n_exception"


def _r62n_builtin_exception_class(name: str) -> type[BaseException] | None:
    candidate = getattr(_py_builtins, name, None)
    if (
        isinstance(candidate, type)
        and issubclass(candidate, _py_builtins.BaseException)
    ):
        return candidate
    return None


def _r62n_static_exception_name(
    node: ast.AST | None,
    authority: _r62l._R62LAuthorityBindings,
) -> str | None:
    target: ast.Name | None = None
    if isinstance(node, ast.Name):
        target = node
    elif isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
        target = node.func
    if target is None or target.id in authority:
        return None
    return (
        target.id
        if _r62n_builtin_exception_class(target.id) is not None
        else None
    )


def _r62n_set_exception_tag(
    state: _r62l._R62LState,
    exception_name: str | None,
) -> None:
    state[0][_R62N_EXCEPTION_TAG] = (
        frozenset({_r12._Atom(_R62N_EXCEPTION_KIND, exception_name)})
        if exception_name is not None
        else _UNKNOWN
    )


def _r62n_exception_name(state: _r62l._R62LState) -> str | None:
    value = state[0].get(_R62N_EXCEPTION_TAG)
    if value is None:
        return None
    names = {
        atom.text
        for atom in value
        if atom.kind == _R62N_EXCEPTION_KIND and atom.text is not None
    }
    return next(iter(names)) if len(names) == 1 else None


def _r62n_handler_match(
    exception_name: str | None,
    handler_type: ast.AST | None,
    authority: _r62l._R62LAuthorityBindings,
) -> bool | None:
    if handler_type is None:
        return True
    if exception_name is None:
        return None
    exception_class = _r62n_builtin_exception_class(exception_name)
    if exception_class is None:
        return None
    if isinstance(handler_type, ast.Name):
        if handler_type.id in authority:
            return None
        handler_class = _r62n_builtin_exception_class(handler_type.id)
        if handler_class is None:
            return None
        return issubclass(exception_class, handler_class)
    if isinstance(handler_type, ast.Tuple):
        matches = [
            _r62n_handler_match(exception_name, item, authority)
            for item in handler_type.elts
        ]
        if any(match is True for match in matches):
            return True
        if all(match is False for match in matches):
            return False
    return None


def _r62n_raise_outcomes_from_states(
    states: list[_r62l._R62LState],
    *,
    exception_name: str | None = None,
) -> list[_r62m._R62MOutcome]:
    result: list[_r62m._R62MOutcome] = []
    for state in _r62n_unique_states(states):
        tagged = _r62n_copy_state(state)
        _r62n_set_exception_tag(tagged, exception_name)
        result.append(_r62m._R62MOutcome("raise", tagged))
    return result


def _r62n_scratch_eval(
    node: ast.AST,
    state: _r62l._R62LState,
) -> _r62l._R62LState:
    working = _r62n_copy_state(state)
    scratch_timeline: dict[int, list[_r62l._R62LAuthorityBindings]] = {}
    scratch_observations: dict[
        _r62k._R62KOwner,
        list[_r62l._R62LAuthorityBindings],
    ] = {}
    _r62n_eval(
        node,
        working,
        top_index=0,
        timeline=scratch_timeline,
        observations=scratch_observations,
        precision_lost=[False],
    )
    return working


def _r62n_ordered_expression_raise_states(
    node: ast.AST,
    state: _r62l._R62LState,
) -> tuple[_r62l._R62LState, list[_r62l._R62LState]]:
    if isinstance(node, ast.NamedExpr):
        working, raised = _r62n_ordered_expression_raise_states(node.value, state)
        binding_value = _r62j._r62j_binding_expression_value(
            node.value,
            working[0],
        )
        _r62j._r62j_assign_names(node.target, binding_value, working[0])
        owners = _r62l._r62l_owner_expression_value(node.value, working[1])
        _r62l._r62l_assign_owner_names(node.target, owners, working[1])
        return working, raised

    if isinstance(node, (ast.Tuple, ast.List, ast.Set)):
        working = _r62n_copy_state(state)
        raised: list[_r62l._R62LState] = []
        for child in node.elts:
            working, child_raised = _r62n_ordered_expression_raise_states(
                child,
                working,
            )
            raised.extend(child_raised)
        raised.append(_r62n_copy_state(working))
        return working, _r62n_unique_states(raised)

    if isinstance(node, ast.Dict):
        working = _r62n_copy_state(state)
        raised: list[_r62l._R62LState] = []
        for key, value in zip(node.keys, node.values, strict=True):
            if key is not None:
                working, child_raised = _r62n_ordered_expression_raise_states(
                    key,
                    working,
                )
                raised.extend(child_raised)
            working, child_raised = _r62n_ordered_expression_raise_states(
                value,
                working,
            )
            raised.extend(child_raised)
        raised.append(_r62n_copy_state(working))
        return working, _r62n_unique_states(raised)

    if isinstance(node, ast.Call):
        working, raised = _r62n_ordered_expression_raise_states(node.func, state)
        arguments: list[ast.expr] = [
            *node.args,
            *(keyword.value for keyword in node.keywords),
        ]
        arguments.sort(key=lambda item: (item.lineno, item.col_offset))
        for argument in arguments:
            working, child_raised = _r62n_ordered_expression_raise_states(
                argument,
                working,
            )
            raised.extend(child_raised)
        raised.append(_r62n_copy_state(working))
        return working, _r62n_unique_states(raised)

    if isinstance(node, ast.BinOp):
        working, raised = _r62n_ordered_expression_raise_states(node.left, state)
        working, child_raised = _r62n_ordered_expression_raise_states(
            node.right,
            working,
        )
        raised.extend(child_raised)
        raised.append(_r62n_copy_state(working))
        return working, _r62n_unique_states(raised)

    before = _r62n_copy_state(state)
    working = _r62n_scratch_eval(node, state)
    raised = (
        [before, _r62n_copy_state(working)]
        if _r62n_expression_may_raise(node)
        else []
    )
    return working, _r62n_unique_states(raised)

def _r62n_eval(
    node: ast.AST,
    state: _r62l._R62LState,
    *,
    top_index: int,
    timeline: dict[int, list[_r62l._R62LAuthorityBindings]],
    observations: dict[
        _r62k._R62KOwner,
        list[_r62l._R62LAuthorityBindings],
    ],
    precision_lost: list[bool],
) -> None:
    _r62m._r62m_eval(
        node,
        state,
        top_index=top_index,
        timeline=timeline,
        observations=observations,
        precision_lost=precision_lost,
    )


def _r62n_expression_may_raise(node: ast.AST) -> bool:
    if isinstance(node, (ast.Constant, ast.Name, ast.Lambda)):
        return False
    if isinstance(node, ast.NamedExpr):
        return _r62n_expression_may_raise(node.value)
    if isinstance(node, (ast.Tuple, ast.List, ast.Set)):
        return any(_r62n_expression_may_raise(item) for item in node.elts)
    if isinstance(node, ast.Dict):
        return any(
            key is not None and _r62n_expression_may_raise(key)
            for key in node.keys
        ) or any(_r62n_expression_may_raise(value) for value in node.values)
    if isinstance(node, ast.JoinedStr):
        return any(_r62n_expression_may_raise(value) for value in node.values)
    if isinstance(node, ast.FormattedValue):
        return True
    return True


def _r62n_function_immediate_expressions(
    node: ast.FunctionDef | ast.AsyncFunctionDef,
) -> tuple[ast.AST, ...]:
    result: list[ast.AST] = [
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
            result.append(argument.annotation)
    if node.args.vararg is not None and node.args.vararg.annotation is not None:
        result.append(node.args.vararg.annotation)
    if node.args.kwarg is not None and node.args.kwarg.annotation is not None:
        result.append(node.args.kwarg.annotation)
    if node.returns is not None:
        result.append(node.returns)
    return tuple(result)


def _r62n_simple_statement_may_raise(node: ast.stmt) -> bool:
    if isinstance(node, ast.Import):
        return any(alias.name != "builtins" for alias in node.names)
    if isinstance(node, ast.ImportFrom):
        return node.module != "builtins"
    if isinstance(node, ast.Assign):
        return _r62n_expression_may_raise(node.value)
    if isinstance(node, ast.AnnAssign):
        return _r62n_expression_may_raise(node.annotation) or (
            node.value is not None and _r62n_expression_may_raise(node.value)
        )
    if isinstance(node, ast.AugAssign):
        return True
    if isinstance(node, ast.Expr):
        return _r62n_expression_may_raise(node.value)
    if isinstance(node, ast.Assert):
        return True
    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
        return any(
            _r62n_expression_may_raise(expression)
            for expression in _r62n_function_immediate_expressions(node)
        )
    if isinstance(node, ast.ClassDef):
        return True
    if isinstance(node, ast.Delete):
        return True
    return False


def _r62n_implicit_raise_outcomes(
    before: _r62l._R62LState,
    after: list[_r62l._R62LState],
) -> list[_r62m._R62MOutcome]:
    states = _r62n_unique_states(
        [_r62n_copy_state(before), *(_r62n_copy_state(item) for item in after)]
    )
    return _r62n_raise_outcomes_from_states(states)


def _r62n_process_block(
    statements: list[ast.stmt],
    states: list[_r62l._R62LState],
    *,
    top_index: int,
    timeline: dict[int, list[_r62l._R62LAuthorityBindings]],
    observations: dict[
        _r62k._R62KOwner,
        list[_r62l._R62LAuthorityBindings],
    ],
    precision_lost: list[bool],
) -> list[_r62m._R62MOutcome]:
    outcomes = [_r62m._R62MOutcome("normal", state) for state in states]
    for statement in statements:
        next_outcomes: list[_r62m._R62MOutcome] = []
        for outcome in outcomes:
            if outcome.kind != "normal":
                next_outcomes.append(outcome)
                continue
            next_outcomes.extend(
                _r62n_process_statement(
                    statement,
                    outcome.state,
                    top_index=top_index,
                    timeline=timeline,
                    observations=observations,
                    precision_lost=precision_lost,
                )
            )
        outcomes = _r62m._r62m_bound_outcomes(next_outcomes)
    return outcomes


def _r62n_process_finally(
    outcomes: list[_r62m._R62MOutcome],
    statements: list[ast.stmt],
    *,
    top_index: int,
    timeline: dict[int, list[_r62l._R62LAuthorityBindings]],
    observations: dict[
        _r62k._R62KOwner,
        list[_r62l._R62LAuthorityBindings],
    ],
    precision_lost: list[bool],
) -> list[_r62m._R62MOutcome]:
    result: list[_r62m._R62MOutcome] = []
    for incoming in outcomes:
        final = _r62n_process_block(
            statements,
            [_r62n_copy_state(incoming.state)],
            top_index=top_index,
            timeline=timeline,
            observations=observations,
            precision_lost=precision_lost,
        )
        for completed in final:
            if completed.kind == "normal":
                result.append(_r62m._R62MOutcome(incoming.kind, completed.state))
            else:
                result.append(completed)
    return _r62m._r62m_bound_outcomes(result)


def _r62n_process_if(
    node: ast.If,
    state: _r62l._R62LState,
    *,
    top_index: int,
    timeline: dict[int, list[_r62l._R62LAuthorityBindings]],
    observations: dict[
        _r62k._R62KOwner,
        list[_r62l._R62LAuthorityBindings],
    ],
    precision_lost: list[bool],
) -> list[_r62m._R62MOutcome]:
    working = _r62n_copy_state(state)
    may_raise = _r62n_expression_may_raise(node.test)
    _r62n_eval(
        node.test,
        working,
        top_index=top_index,
        timeline=timeline,
        observations=observations,
        precision_lost=precision_lost,
    )
    raised = (
        _r62n_implicit_raise_outcomes(state, [working]) if may_raise else []
    )
    truth = _r62l._r62l_static_bool(node.test)
    if truth is True:
        return _r62m._r62m_bound_outcomes(
            [
                *raised,
                *_r62n_process_block(
                    node.body,
                    [working],
                    top_index=top_index,
                    timeline=timeline,
                    observations=observations,
                    precision_lost=precision_lost,
                ),
            ]
        )
    if truth is False:
        branch = (
            _r62n_process_block(
                node.orelse,
                [working],
                top_index=top_index,
                timeline=timeline,
                observations=observations,
                precision_lost=precision_lost,
            )
            if node.orelse
            else [_r62m._R62MOutcome("normal", working)]
        )
        return _r62m._r62m_bound_outcomes([*raised, *branch])

    body = _r62n_process_block(
        node.body,
        [_r62n_copy_state(working)],
        top_index=top_index,
        timeline=timeline,
        observations=observations,
        precision_lost=precision_lost,
    )
    other = (
        _r62n_process_block(
            node.orelse,
            [_r62n_copy_state(working)],
            top_index=top_index,
            timeline=timeline,
            observations=observations,
            precision_lost=precision_lost,
        )
        if node.orelse
        else [_r62m._R62MOutcome("normal", _r62n_copy_state(working))]
    )
    return _r62m._r62m_bound_outcomes([*raised, *body, *other])


def _r62n_process_try(
    node: ast.Try | ast.TryStar,
    state: _r62l._R62LState,
    *,
    top_index: int,
    timeline: dict[int, list[_r62l._R62LAuthorityBindings]],
    observations: dict[
        _r62k._R62KOwner,
        list[_r62l._R62LAuthorityBindings],
    ],
    precision_lost: list[bool],
) -> list[_r62m._R62MOutcome]:
    body = _r62n_process_block(
        node.body,
        [_r62n_copy_state(state)],
        top_index=top_index,
        timeline=timeline,
        observations=observations,
        precision_lost=precision_lost,
    )

    normal_states = [item.state for item in body if item.kind == "normal"]
    successful = (
        _r62n_process_block(
            node.orelse,
            normal_states,
            top_index=top_index,
            timeline=timeline,
            observations=observations,
            precision_lost=precision_lost,
        )
        if node.orelse and normal_states
        else [
            _r62m._R62MOutcome("normal", item.state)
            for item in body
            if item.kind == "normal"
        ]
    )

    propagated = [
        item for item in body if item.kind in {"break", "continue"}
    ]
    unhandled = [item for item in body if item.kind == "raise"]
    handled: list[_r62m._R62MOutcome] = []

    for handler in node.handlers:
        next_unhandled: list[_r62m._R62MOutcome] = []
        for raised in unhandled:
            match = _r62n_handler_match(
                _r62n_exception_name(raised.state),
                handler.type,
                raised.state[0],
            )
            if match is False:
                next_unhandled.append(raised)
                continue

            handler_state = _r62n_copy_state(raised.state)
            handler_state[0].pop(_R62N_EXCEPTION_TAG, None)
            if handler.type is not None:
                _r62n_eval(
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
            handled.extend(
                _r62n_process_block(
                    handler.body,
                    [handler_state],
                    top_index=top_index,
                    timeline=timeline,
                    observations=observations,
                    precision_lost=precision_lost,
                )
            )
            if match is None:
                next_unhandled.append(raised)
        unhandled = next_unhandled

    combined = _r62m._r62m_bound_outcomes(
        [*successful, *propagated, *unhandled, *handled]
    )
    if node.finalbody:
        return _r62n_process_finally(
            combined,
            node.finalbody,
            top_index=top_index,
            timeline=timeline,
            observations=observations,
            precision_lost=precision_lost,
        )
    return combined


def _r62n_process_with(
    node: ast.With | ast.AsyncWith,
    state: _r62l._R62LState,
    *,
    top_index: int,
    timeline: dict[int, list[_r62l._R62LAuthorityBindings]],
    observations: dict[
        _r62k._R62KOwner,
        list[_r62l._R62LAuthorityBindings],
    ],
    precision_lost: list[bool],
) -> list[_r62m._R62MOutcome]:
    working = _r62n_copy_state(state)
    raised: list[_r62m._R62MOutcome] = []
    if isinstance(node, ast.AsyncWith):
        precision_lost[0] = True
    for item in node.items:
        before = _r62n_copy_state(working)
        may_raise = _r62n_expression_may_raise(item.context_expr)
        _r62n_eval(
            item.context_expr,
            working,
            top_index=top_index,
            timeline=timeline,
            observations=observations,
            precision_lost=precision_lost,
        )
        if may_raise:
            raised.extend(_r62n_implicit_raise_outcomes(before, [working]))
        if item.optional_vars is not None:
            _r62j._r62j_assign_names(item.optional_vars, _UNKNOWN, working[0])
            _r62l._r62l_assign_owner_names(
                item.optional_vars,
                frozenset(),
                working[1],
            )
    body = _r62n_process_block(
        node.body,
        [working],
        top_index=top_index,
        timeline=timeline,
        observations=observations,
        precision_lost=precision_lost,
    )
    return _r62m._r62m_bound_outcomes([*raised, *body])


def _r62n_loop_body(
    statements: list[ast.stmt],
    state: _r62l._R62LState,
    *,
    target: ast.AST | None,
    top_index: int,
    timeline: dict[int, list[_r62l._R62LAuthorityBindings]],
    observations: dict[
        _r62k._R62KOwner,
        list[_r62l._R62LAuthorityBindings],
    ],
    precision_lost: list[bool],
) -> list[_r62m._R62MOutcome]:
    body_state = _r62n_copy_state(state)
    if target is not None:
        _r62j._r62j_assign_names(target, _UNKNOWN, body_state[0])
        _r62l._r62l_assign_owner_names(
            target,
            frozenset(),
            body_state[1],
        )
    return _r62n_process_block(
        statements,
        [body_state],
        top_index=top_index,
        timeline=timeline,
        observations=observations,
        precision_lost=precision_lost,
    )


def _r62n_static_for_count(node: ast.AST) -> int | None:
    if isinstance(node, (ast.Tuple, ast.List)):
        return len(node.elts)
    if (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "range"
        and not node.keywords
        and 1 <= len(node.args) <= 3
    ):
        values: list[int] = []
        for argument in node.args:
            if (
                not isinstance(argument, ast.Constant)
                or not isinstance(argument.value, int)
                or isinstance(argument.value, bool)
            ):
                return None
            values.append(argument.value)
        try:
            if len(values) == 1:
                return len(range(values[0]))
            if len(values) == 2:
                return len(range(values[0], values[1]))
            return len(range(values[0], values[1], values[2]))
        except (OverflowError, ValueError):
            return None
    return None


def _r62n_complete_for(
    node: ast.For | ast.AsyncFor,
    working: _r62l._R62LState,
    *,
    count: int,
    top_index: int,
    timeline: dict[int, list[_r62l._R62LAuthorityBindings]],
    observations: dict[
        _r62k._R62KOwner,
        list[_r62l._R62LAuthorityBindings],
    ],
    precision_lost: list[bool],
) -> list[_r62m._R62MOutcome]:
    entries = [_r62n_copy_state(working)]
    breaks: list[_r62m._R62MOutcome] = []
    raised: list[_r62m._R62MOutcome] = []
    for _ in range(count):
        next_entries: list[_r62l._R62LState] = []
        for entry in entries:
            body = _r62n_loop_body(
                node.body,
                entry,
                target=node.target,
                top_index=top_index,
                timeline=timeline,
                observations=observations,
                precision_lost=precision_lost,
            )
            breaks.extend(
                _r62m._R62MOutcome("normal", item.state)
                for item in body
                if item.kind == "break"
            )
            raised.extend(item for item in body if item.kind == "raise")
            next_entries.extend(
                item.state
                for item in body
                if item.kind in {"normal", "continue"}
            )
        entries = _r62n_unique_states(next_entries)
        if not entries:
            break

    natural_outcomes = (
        _r62n_process_block(
            node.orelse,
            entries,
            top_index=top_index,
            timeline=timeline,
            observations=observations,
            precision_lost=precision_lost,
        )
        if node.orelse and entries
        else [_r62m._R62MOutcome("normal", state) for state in entries]
    )
    return _r62m._r62m_bound_outcomes(
        [*breaks, *raised, *natural_outcomes]
    )


def _r62n_unknown_for(
    node: ast.For | ast.AsyncFor,
    working: _r62l._R62LState,
    *,
    top_index: int,
    timeline: dict[int, list[_r62l._R62LAuthorityBindings]],
    observations: dict[
        _r62k._R62KOwner,
        list[_r62l._R62LAuthorityBindings],
    ],
    precision_lost: list[bool],
) -> list[_r62m._R62MOutcome]:
    frontier = [_r62n_copy_state(working)]
    seen: list[_r62l._R62LState] = []
    natural = [_r62n_copy_state(working)]
    breaks: list[_r62m._R62MOutcome] = []
    raised: list[_r62m._R62MOutcome] = []
    iterations = 0

    while frontier:
        iterations += 1
        if iterations > _r62m._R62M_MAX_STATES:
            precision_lost[0] = True
            break
        next_frontier: list[_r62l._R62LState] = []
        for entry in frontier:
            if entry in seen:
                continue
            seen.append(_r62n_copy_state(entry))
            body = _r62n_loop_body(
                node.body,
                entry,
                target=node.target,
                top_index=top_index,
                timeline=timeline,
                observations=observations,
                precision_lost=precision_lost,
            )
            breaks.extend(
                _r62m._R62MOutcome("normal", item.state)
                for item in body
                if item.kind == "break"
            )
            raised.extend(item for item in body if item.kind == "raise")
            repeat = [
                item.state
                for item in body
                if item.kind in {"normal", "continue"}
            ]
            for candidate in repeat:
                if candidate not in natural:
                    natural.append(_r62n_copy_state(candidate))
                if candidate not in seen and candidate not in next_frontier:
                    next_frontier.append(_r62n_copy_state(candidate))
        frontier = next_frontier

    natural_outcomes = (
        _r62n_process_block(
            node.orelse,
            natural,
            top_index=top_index,
            timeline=timeline,
            observations=observations,
            precision_lost=precision_lost,
        )
        if node.orelse
        else [_r62m._R62MOutcome("normal", state) for state in natural]
    )
    return _r62m._r62m_bound_outcomes(
        [*breaks, *raised, *natural_outcomes]
    )


def _r62n_process_for(
    node: ast.For | ast.AsyncFor,
    state: _r62l._R62LState,
    *,
    top_index: int,
    timeline: dict[int, list[_r62l._R62LAuthorityBindings]],
    observations: dict[
        _r62k._R62KOwner,
        list[_r62l._R62LAuthorityBindings],
    ],
    precision_lost: list[bool],
) -> list[_r62m._R62MOutcome]:
    working = _r62n_copy_state(state)
    iter_may_raise = _r62n_expression_may_raise(node.iter)
    _r62n_eval(
        node.iter,
        working,
        top_index=top_index,
        timeline=timeline,
        observations=observations,
        precision_lost=precision_lost,
    )
    implicit_raised = (
        _r62n_implicit_raise_outcomes(state, [working])
        if iter_may_raise
        else []
    )
    if isinstance(node, ast.AsyncFor):
        precision_lost[0] = True

    count = _r62n_static_for_count(node.iter)
    if count is not None and count <= _r62m._R62M_MAX_STATES:
        loop = _r62n_complete_for(
            node,
            working,
            count=count,
            top_index=top_index,
            timeline=timeline,
            observations=observations,
            precision_lost=precision_lost,
        )
    else:
        if count is not None:
            precision_lost[0] = True
        loop = _r62n_unknown_for(
            node,
            working,
            top_index=top_index,
            timeline=timeline,
            observations=observations,
            precision_lost=precision_lost,
        )
    return _r62m._r62m_bound_outcomes([*implicit_raised, *loop])


def _r62n_eval_while_test(
    node: ast.While,
    state: _r62l._R62LState,
    *,
    top_index: int,
    timeline: dict[int, list[_r62l._R62LAuthorityBindings]],
    observations: dict[
        _r62k._R62KOwner,
        list[_r62l._R62LAuthorityBindings],
    ],
    precision_lost: list[bool],
) -> tuple[_r62l._R62LState, list[_r62m._R62MOutcome]]:
    tested = _r62n_copy_state(state)
    may_raise = _r62n_expression_may_raise(node.test)
    _r62n_eval(
        node.test,
        tested,
        top_index=top_index,
        timeline=timeline,
        observations=observations,
        precision_lost=precision_lost,
    )
    raised = (
        _r62n_implicit_raise_outcomes(state, [tested]) if may_raise else []
    )
    return tested, raised


def _r62n_process_while(
    node: ast.While,
    state: _r62l._R62LState,
    *,
    top_index: int,
    timeline: dict[int, list[_r62l._R62LAuthorityBindings]],
    observations: dict[
        _r62k._R62KOwner,
        list[_r62l._R62LAuthorityBindings],
    ],
    precision_lost: list[bool],
) -> list[_r62m._R62MOutcome]:
    first, raised = _r62n_eval_while_test(
        node,
        state,
        top_index=top_index,
        timeline=timeline,
        observations=observations,
        precision_lost=precision_lost,
    )
    truth = _r62l._r62l_static_bool(node.test)
    if truth is False:
        natural_outcomes = (
            _r62n_process_block(
                node.orelse,
                [first],
                top_index=top_index,
                timeline=timeline,
                observations=observations,
                precision_lost=precision_lost,
            )
            if node.orelse
            else [_r62m._R62MOutcome("normal", first)]
        )
        return _r62m._r62m_bound_outcomes([*raised, *natural_outcomes])

    frontier = [first]
    seen: list[_r62l._R62LState] = []
    natural = [] if truth is True else [_r62n_copy_state(first)]
    breaks: list[_r62m._R62MOutcome] = []
    iterations = 0

    while frontier:
        iterations += 1
        if iterations > _r62m._R62M_MAX_STATES:
            precision_lost[0] = True
            break
        next_frontier: list[_r62l._R62LState] = []
        for entry in frontier:
            if entry in seen:
                continue
            seen.append(_r62n_copy_state(entry))
            body = _r62n_loop_body(
                node.body,
                entry,
                target=None,
                top_index=top_index,
                timeline=timeline,
                observations=observations,
                precision_lost=precision_lost,
            )
            breaks.extend(
                _r62m._R62MOutcome("normal", item.state)
                for item in body
                if item.kind == "break"
            )
            raised.extend(item for item in body if item.kind == "raise")
            repeat = [
                item.state
                for item in body
                if item.kind in {"normal", "continue"}
            ]
            for candidate in repeat:
                tested, test_raised = _r62n_eval_while_test(
                    node,
                    candidate,
                    top_index=top_index,
                    timeline=timeline,
                    observations=observations,
                    precision_lost=precision_lost,
                )
                raised.extend(test_raised)
                if truth is not True and tested not in natural:
                    natural.append(_r62n_copy_state(tested))
                if tested not in seen and tested not in next_frontier:
                    next_frontier.append(_r62n_copy_state(tested))
        frontier = next_frontier

    natural_outcomes = (
        _r62n_process_block(
            node.orelse,
            natural,
            top_index=top_index,
            timeline=timeline,
            observations=observations,
            precision_lost=precision_lost,
        )
        if node.orelse and natural
        else [_r62m._R62MOutcome("normal", item) for item in natural]
    )
    return _r62m._r62m_bound_outcomes(
        [*breaks, *raised, *natural_outcomes]
    )


def _r62n_process_statement(
    node: ast.stmt,
    state: _r62l._R62LState,
    *,
    top_index: int,
    timeline: dict[int, list[_r62l._R62LAuthorityBindings]],
    observations: dict[
        _r62k._R62KOwner,
        list[_r62l._R62LAuthorityBindings],
    ],
    precision_lost: list[bool],
) -> list[_r62m._R62MOutcome]:
    _r62l._r62l_record_timeline(timeline, top_index, state[0])

    if isinstance(node, ast.Raise):
        working = _r62n_copy_state(state)
        exception_name = _r62n_static_exception_name(node.exc, working[0])
        if node.exc is not None:
            _r62n_eval(
                node.exc,
                working,
                top_index=top_index,
                timeline=timeline,
                observations=observations,
                precision_lost=precision_lost,
            )
        if node.cause is not None:
            _r62n_eval(
                node.cause,
                working,
                top_index=top_index,
                timeline=timeline,
                observations=observations,
                precision_lost=precision_lost,
            )
        _r62n_set_exception_tag(working, exception_name)
        return [_r62m._R62MOutcome("raise", working)]
    if isinstance(node, ast.Break):
        return [_r62m._R62MOutcome("break", _r62n_copy_state(state))]
    if isinstance(node, ast.Continue):
        return [_r62m._R62MOutcome("continue", _r62n_copy_state(state))]
    if isinstance(node, ast.If):
        return _r62n_process_if(
            node,
            state,
            top_index=top_index,
            timeline=timeline,
            observations=observations,
            precision_lost=precision_lost,
        )
    if isinstance(node, (ast.Try, ast.TryStar)):
        return _r62n_process_try(
            node,
            state,
            top_index=top_index,
            timeline=timeline,
            observations=observations,
            precision_lost=precision_lost,
        )
    if isinstance(node, (ast.With, ast.AsyncWith)):
        return _r62n_process_with(
            node,
            state,
            top_index=top_index,
            timeline=timeline,
            observations=observations,
            precision_lost=precision_lost,
        )
    if isinstance(node, (ast.For, ast.AsyncFor)):
        return _r62n_process_for(
            node,
            state,
            top_index=top_index,
            timeline=timeline,
            observations=observations,
            precision_lost=precision_lost,
        )
    if isinstance(node, ast.While):
        return _r62n_process_while(
            node,
            state,
            top_index=top_index,
            timeline=timeline,
            observations=observations,
            precision_lost=precision_lost,
        )

    next_states = _r62l._r62l_process_statement(
        node,
        _r62n_copy_state(state),
        top_index=top_index,
        timeline=timeline,
        observations=observations,
        precision_lost=precision_lost,
    )
    normal = [_r62m._R62MOutcome("normal", item) for item in next_states]
    if not _r62n_simple_statement_may_raise(node):
        return normal
    if isinstance(node, (ast.Expr, ast.Assign)):
        _, raise_states = _r62n_ordered_expression_raise_states(
            node.value,
            state,
        )
        return _r62m._r62m_bound_outcomes(
            [*normal, *_r62n_raise_outcomes_from_states(raise_states)]
        )
    return _r62m._r62m_bound_outcomes(
        [
            *normal,
            *_r62n_implicit_raise_outcomes(state, next_states),
        ]
    )


def _r62n_flow(
    source: str,
) -> tuple[
    dict[
        _r62k._R62KOwner,
        tuple[_r62l._R62LAuthorityBindings, ...],
    ],
    dict[int, tuple[_r62l._R62LAuthorityBindings, ...]],
    bool,
]:
    tree = ast.parse(source)
    initial: _r62l._R62LState = (
        {"__builtins__": _r12._BUILTINS_NAMESPACE},
        {},
    )
    timeline: dict[int, list[_r62l._R62LAuthorityBindings]] = {}
    observations: dict[
        _r62k._R62KOwner,
        list[_r62l._R62LAuthorityBindings],
    ] = {}
    precision_lost = [False]
    outcomes = [_r62m._R62MOutcome("normal", initial)]

    for top_index, statement in enumerate(tree.body):
        next_outcomes: list[_r62m._R62MOutcome] = []
        for outcome in outcomes:
            if outcome.kind != "normal":
                next_outcomes.append(outcome)
                continue
            next_outcomes.extend(
                _r62n_process_statement(
                    statement,
                    outcome.state,
                    top_index=top_index,
                    timeline=timeline,
                    observations=observations,
                    precision_lost=precision_lost,
                )
            )
        outcomes = _r62m._r62m_bound_outcomes(next_outcomes)

    for outcome in outcomes:
        if outcome.kind != "normal":
            continue
        authority, owner_bindings = outcome.state
        reachable = {
            owner for owners in owner_bindings.values() for owner in owners
        }
        for owner in reachable:
            observations.setdefault(owner, []).append(authority.copy())

    return (
        {owner: tuple(values) for owner, values in observations.items()},
        {index: tuple(values) for index, values in timeline.items()},
        precision_lost[0],
    )


def _r62n_future_authority_by_call(
    source: str,
    timeline: dict[int, tuple[_r62l._R62LAuthorityBindings, ...]],
) -> dict[tuple[int, int], dict[str, tuple[_Value, bool]]]:
    return _r62l._r62l_future_authority_by_call(source, timeline)


def _r62n_observable_authority_by_call(
    source: str,
) -> dict[tuple[int, int], dict[str, tuple[_Value, bool]]]:
    observations, timeline, precision_lost = _r62n_flow(source)
    fallback = _r62n_future_authority_by_call(source, timeline)
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


def _r62n_namespace_from_states(
    states: tuple[_r62l._R62LAuthorityBindings, ...],
) -> _Value:
    names = {
        name
        for state in states
        for name in state
        if name != _R62N_EXCEPTION_TAG
    }
    values: dict[str, tuple[_Value, bool]] = {}
    for name in names:
        present = [state[name] for state in states if name in state]
        values[name] = (
            _r12._merge_values(*present),
            all(name in state for state in states),
        )
    return _r62j._r62j_enrich_namespace(
        _r62i._r62i_selected_namespace({}, frozenset()),
        values,
    )


def _r62n_observable_namespace_by_call(
    source: str,
) -> dict[tuple[int, int], _Value]:
    observations, _, precision_lost = _r62n_flow(source)
    if precision_lost:
        return {}
    owner_by_call = _r62k._r62k_top_level_owner_calls(source)
    escaped = _r62k._r62k_escaped_owners(source)
    result: dict[tuple[int, int], _Value] = {}
    for position in _r62j._r62j_deferred_call_top_indexes(source):
        owner = owner_by_call.get(position)
        if owner is None or owner in escaped:
            continue
        states = observations.get(owner)
        if states:
            result[position] = _r62n_namespace_from_states(states)
    return result


class _R62NBoundedExceptionalLoopGlobalsScanner(
    _r62m._R62MAbruptControlFlowGlobalsScanner
):
    """Bound implicit exceptions and repeated module-loop authority states."""

    def __init__(self) -> None:
        super().__init__()
        self._r62n_observable_namespace_by_call: dict[
            tuple[int, int], _Value
        ] = {}

    def scan(self, source: str) -> tuple[str, ...]:
        self._r62j_future_authority_by_call = _r62n_observable_authority_by_call(
            source
        )
        self._r62n_observable_namespace_by_call = (
            _r62n_observable_namespace_by_call(source)
        )
        return _r62i._R62IModuleAndParameterNamespaceScanner.scan(self, source)

    def _evaluate_special_call(
        self,
        helper: _r12._Atom,
        arguments: list[_Value],
    ) -> _Value:
        if (
            helper.kind == "helper"
            and helper.text == "globals"
            and not arguments
            and self._r62i_call_position_stack
        ):
            replacement = self._r62n_observable_namespace_by_call.get(
                self._r62i_call_position_stack[-1]
            )
            if replacement is not None:
                return replacement
        return super()._evaluate_special_call(helper, arguments)


def _r62n_dynamic_execution_markers_from_source(source: str) -> tuple[str, ...]:
    return _R62NBoundedExceptionalLoopGlobalsScanner().scan(source)


def _runtime_result(source: str) -> object:
    namespace: dict[str, object] = {}
    exec(compile(source, "<r62n>", "exec", dont_inherit=True), namespace)
    return namespace["result"]


def test_r62n_predecessor_reproduces_exception_and_repeat_defects() -> None:
    dangerous = (
        """\
def run():
    return getattr(globals()["b"], "eval", lambda _: 3)("1+1")
try:
    import builtins as b
    1 / 0
except ZeroDivisionError:
    result = run()
b = len
""",
        """\
def run():
    return getattr(globals()["b"], "eval", lambda _: 3)("1+1")
b = len
for _ in (0, 1):
    result = run()
    import builtins as b
b = len
""",
        """\
def run():
    return getattr(globals()["b"], "eval", lambda _: 3)("1+1")
b = len
i = 0
while i < 2:
    result = run()
    import builtins as b
    i += 1
b = len
""",
    )
    for source in dangerous:
        assert _runtime_result(source) == 2
        assert _r62m._r62m_dynamic_execution_markers_from_source(source) == ()

    safe = (
        """\
import builtins as b
def run():
    return getattr(globals()["b"], "eval", lambda _: 3)("1+1")
try:
    b = len
    raise RuntimeError
except RuntimeError:
    result = run()
""",
        """\
import builtins as b
def run():
    return getattr(globals()["b"], "eval", lambda _: 3)("1+1")
try:
    b = len
    1 / 0
except ZeroDivisionError:
    result = run()
""",
    )
    for source in safe:
        assert _runtime_result(source) == 3
        assert _r62m._r62m_dynamic_execution_markers_from_source(source)


def test_r62n_exception_entries_use_reachable_partial_state() -> None:
    dangerous = """\
def run():
    return getattr(globals()["b"], "eval", lambda _: 3)("1+1")
try:
    import builtins as b
    1 / 0
except ZeroDivisionError:
    result = run()
b = len
"""
    safe_explicit = """\
import builtins as b
def run():
    return getattr(globals()["b"], "eval", lambda _: 3)("1+1")
try:
    b = len
    raise RuntimeError
except RuntimeError:
    result = run()
"""
    safe_implicit = """\
import builtins as b
def run():
    return getattr(globals()["b"], "eval", lambda _: 3)("1+1")
try:
    b = len
    1 / 0
except ZeroDivisionError:
    result = run()
"""
    assert _runtime_result(dangerous) == 2
    assert _runtime_result(safe_explicit) == 3
    assert _runtime_result(safe_implicit) == 3
    assert _r62n_dynamic_execution_markers_from_source(dangerous)
    assert _r62n_dynamic_execution_markers_from_source(safe_explicit) == ()
    assert _r62n_dynamic_execution_markers_from_source(safe_implicit) == ()


def test_r62n_exact_for_cardinality_preserves_safe_inverse() -> None:
    dangerous = """\
def run():
    return getattr(globals()["b"], "eval", lambda _: 3)("1+1")
b = len
for _ in (0, 1):
    result = run()
    import builtins as b
b = len
"""
    safe = """\
def run():
    return getattr(globals()["b"], "eval", lambda _: 3)("1+1")
b = len
for _ in (0,):
    result = run()
    import builtins as b
b = len
result = run()
"""
    empty = """\
def run():
    return getattr(globals()["b"], "eval", lambda _: 3)("1+1")
import builtins as b
for _ in ():
    result = run()
b = len
result = run()
"""
    assert _runtime_result(dangerous) == 2
    assert _runtime_result(safe) == 3
    assert _runtime_result(empty) == 3
    assert _r62n_dynamic_execution_markers_from_source(dangerous)
    assert _r62n_dynamic_execution_markers_from_source(safe) == ()
    assert _r62n_dynamic_execution_markers_from_source(empty) == ()


def test_r62n_unknown_for_and_while_close_repeat_states() -> None:
    unknown_for = """\
def run():
    return getattr(globals()["b"], "eval", lambda _: 3)("1+1")
b = len
for _ in iter((0, 1)):
    result = run()
    import builtins as b
b = len
"""
    repeated_while = """\
def run():
    return getattr(globals()["b"], "eval", lambda _: 3)("1+1")
b = len
i = 0
while i < 2:
    result = run()
    import builtins as b
    i += 1
b = len
"""
    safe_false = """\
def run():
    return getattr(globals()["b"], "eval", lambda _: 3)("1+1")
import builtins as b
while False:
    result = run()
b = len
result = run()
"""
    assert _runtime_result(unknown_for) == 2
    assert _runtime_result(repeated_while) == 2
    assert _runtime_result(safe_false) == 3
    assert _r62n_dynamic_execution_markers_from_source(unknown_for)
    assert _r62n_dynamic_execution_markers_from_source(repeated_while)
    assert _r62n_dynamic_execution_markers_from_source(safe_false) == ()


def test_r62n_continue_break_else_and_finally_ordering() -> None:
    continued = """\
def run():
    return getattr(globals()["b"], "eval", lambda _: 3)("1+1")
b = len
for _ in (0, 1):
    result = run()
    import builtins as b
    continue
    b = len
b = len
"""
    broken = """\
def run():
    return getattr(globals()["b"], "eval", lambda _: 3)("1+1")
for _ in (0,):
    import builtins as b
    break
    b = len
result = run()
"""
    finalized_safe = """\
import builtins as b
def run():
    return getattr(globals()["b"], "eval", lambda _: 3)("1+1")
try:
    raise RuntimeError
except RuntimeError:
    b = len
finally:
    result = run()
"""
    assert _runtime_result(continued) == 2
    assert _runtime_result(broken) == 2
    assert _runtime_result(finalized_safe) == 3
    assert _r62n_dynamic_execution_markers_from_source(continued)
    assert _r62n_dynamic_execution_markers_from_source(broken)
    assert _r62n_dynamic_execution_markers_from_source(finalized_safe) == ()


def test_r62n_inherits_namedexpr_alias_and_r62m_regressions() -> None:
    safe = """\
def run():
    return getattr(globals()["b"], "eval", lambda _: 3)("1+1")
import builtins as b
result = ((b := len), run())[1]
"""
    dangerous = """\
import builtins
def run():
    return globals()["b"].eval("1+1")
b = len
result = ((b := builtins), run())[1]
"""
    compound_alias = """\
def run():
    return globals()["b"].eval("1+1")
if True:
    alias = run
    import builtins as b
    result = alias()
b = len
"""
    assert _runtime_result(safe) == 3
    assert _runtime_result(dangerous) == 2
    assert _runtime_result(compound_alias) == 2
    assert _r62n_dynamic_execution_markers_from_source(safe) == ()
    assert _r62n_dynamic_execution_markers_from_source(dangerous)
    assert _r62n_dynamic_execution_markers_from_source(compound_alias)


def test_r62n_complete_owner_and_oracle_surface_has_no_dynamic_execution() -> None:
    paths = (*_owner_paths(), _FULL_CLOSURE_ORACLE_PATH)
    for path in paths:
        assert _r62n_dynamic_execution_markers_from_source(
            path.read_text(encoding="utf-8")
        ) == (), path

def test_r62n_explicit_exception_matching_preserves_safe_inverse() -> None:
    source = """\
import builtins as b
def run():
    return getattr(globals()["b"], "eval", lambda _: 3)("1+1")
try:
    try:
        raise ValueError
    except KeyError:
        result = run()
except ValueError:
    b = len
    result = run()
"""
    assert _runtime_result(source) == 3
    assert _r62n_dynamic_execution_markers_from_source(source) == ()


def test_r62n_shadowed_exception_names_remain_conservative() -> None:
    source = """\
import builtins as b
ValueError = KeyError
def run():
    return globals()["b"].eval("1+1")
try:
    raise ValueError
except KeyError:
    result = run()
"""
    assert _runtime_result(source) == 2
    assert _r62n_dynamic_execution_markers_from_source(source)


def test_r62n_namedexpr_exception_order_preserves_safe_and_dangerous() -> None:
    safe = """\
import builtins as b
def run():
    return getattr(globals()["b"], "eval", lambda _: 3)("1+1")
try:
    ((b := len), 1 / 0)
except ZeroDivisionError:
    result = run()
"""
    dangerous = """\
import builtins
def run():
    return getattr(globals()["b"], "eval", lambda _: 3)("1+1")
b = len
try:
    ((b := builtins), 1 / 0)
except ZeroDivisionError:
    result = run()
"""
    assert _runtime_result(safe) == 3
    assert _runtime_result(dangerous) == 2
    assert _r62n_dynamic_execution_markers_from_source(safe) == ()
    assert _r62n_dynamic_execution_markers_from_source(dangerous)


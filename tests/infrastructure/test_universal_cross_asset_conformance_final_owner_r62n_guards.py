from __future__ import annotations

import ast
import builtins as _py_builtins
import sys
import types

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
_R62N_EXCEPTION_GROUP_MEMBER_KIND = "r62n_exception_group_member"
_R62N_STAR_IMPORT_TAINT = "\x00r62n_star_import_taint"


def _r62n_taint_unknown_star_authority(
    authority: _r62l._R62LAuthorityBindings,
) -> None:
    for name, value in tuple(authority.items()):
        if name in {_R62N_EXCEPTION_TAG, _R62N_STAR_IMPORT_TAINT}:
            continue
        authority[name] = _r12._merge_values(
            value,
            _r12._DANGEROUS_CALLABLE,
        )
    authority[_R62N_STAR_IMPORT_TAINT] = _r12._DANGEROUS_CALLABLE


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


def _r62n_static_exception_group_members(
    node: ast.AST | None,
    authority: _r62l._R62LAuthorityBindings,
) -> frozenset[str] | None:
    if (
        not isinstance(node, ast.Call)
        or not isinstance(node.func, ast.Name)
        or node.func.id not in {"ExceptionGroup", "BaseExceptionGroup"}
        or node.func.id in authority
        or len(node.args) < 2
        or not isinstance(node.args[1], (ast.List, ast.Tuple))
    ):
        return None
    members: set[str] = set()
    for item in node.args[1].elts:
        name = _r62n_static_exception_name(item, authority)
        if name is None:
            return None
        members.add(name)
    return frozenset(members)


def _r62n_set_exception_tag(
    state: _r62l._R62LState,
    exception_name: str | None,
    *,
    group_members: frozenset[str] | None = None,
) -> None:
    if exception_name is None and group_members is None:
        state[0][_R62N_EXCEPTION_TAG] = _UNKNOWN
        return
    atoms: set[_r12._Atom] = set()
    if exception_name is not None:
        atoms.add(_r12._Atom(_R62N_EXCEPTION_KIND, exception_name))
    if group_members is not None:
        atoms.update(
            _r12._Atom(_R62N_EXCEPTION_GROUP_MEMBER_KIND, member)
            for member in group_members
        )
    state[0][_R62N_EXCEPTION_TAG] = frozenset(atoms)


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


def _r62n_exception_group_members(
    state: _r62l._R62LState,
) -> frozenset[str] | None:
    value = state[0].get(_R62N_EXCEPTION_TAG)
    if value is None or value == _UNKNOWN:
        return None
    return frozenset(
        atom.text
        for atom in value
        if (
            atom.kind == _R62N_EXCEPTION_GROUP_MEMBER_KIND
            and atom.text is not None
        )
    )


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


def _r62n_trystar_handler_partition(
    group_members: frozenset[str] | None,
    handler_type: ast.AST | None,
    authority: _r62l._R62LAuthorityBindings,
) -> tuple[bool, bool]:
    if handler_type is None:
        return True, True
    if group_members is None:
        return True, False
    if not group_members:
        return False, True
    matches = [
        _r62n_handler_match(member, handler_type, authority)
        for member in group_members
    ]
    may_handle = any(match is not False for match in matches)
    fully_handled = all(match is True for match in matches)
    return may_handle, fully_handled



def _r62n_trystar_remaining_members(
    group_members: frozenset[str] | None,
    handler_type: ast.AST | None,
    authority: _r62l._R62LAuthorityBindings,
) -> frozenset[str] | None:
    if group_members is None:
        return None
    return frozenset(
        member
        for member in group_members
        if _r62n_handler_match(member, handler_type, authority) is not True
    )


def _r62n_trystar_handler_may_skip(
    group_members: frozenset[str] | None,
    handler_type: ast.AST | None,
    authority: _r62l._R62LAuthorityBindings,
) -> bool:
    if group_members is None:
        return True
    matches = [
        _r62n_handler_match(member, handler_type, authority)
        for member in group_members
    ]
    return (
        not any(match is True for match in matches)
        and any(match is None for match in matches)
    )

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
        sequence_raised: list[_r62l._R62LState] = []
        for child in node.elts:
            working, child_raised = _r62n_ordered_expression_raise_states(
                child,
                working,
            )
            sequence_raised.extend(child_raised)
        sequence_raised.append(_r62n_copy_state(working))
        return working, _r62n_unique_states(sequence_raised)

    if isinstance(node, ast.Dict):
        working = _r62n_copy_state(state)
        dictionary_raised: list[_r62l._R62LState] = []
        for key, value in zip(node.keys, node.values, strict=True):
            if key is not None:
                working, child_raised = _r62n_ordered_expression_raise_states(
                    key,
                    working,
                )
                dictionary_raised.extend(child_raised)
            working, child_raised = _r62n_ordered_expression_raise_states(
                value,
                working,
            )
            dictionary_raised.extend(child_raised)
        dictionary_raised.append(_r62n_copy_state(working))
        return working, _r62n_unique_states(dictionary_raised)

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


def _r62n_static_bool(node: ast.AST) -> bool | None:
    if isinstance(node, ast.NamedExpr):
        return _r62n_static_bool(node.value)
    if isinstance(node, ast.Constant) and isinstance(
        node.value,
        (bool, int, float, complex, str, bytes, type(None)),
    ):
        return bool(node.value)
    return None


def _r62n_static_implicit_exception_name(node: ast.AST) -> str | None:
    if (
        not isinstance(node, ast.BinOp)
        or not isinstance(node.left, ast.Constant)
        or not isinstance(node.right, ast.Constant)
        or node.right.value != 0
    ):
        return None
    if (
        isinstance(node.op, ast.Div)
        and isinstance(node.left.value, (int, float, complex))
        and isinstance(node.right.value, (int, float, complex))
    ):
        return "ZeroDivisionError"
    if (
        isinstance(node.op, (ast.FloorDiv, ast.Mod))
        and isinstance(node.left.value, (int, float))
        and isinstance(node.right.value, (int, float))
    ):
        return "ZeroDivisionError"
    return None


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
    truth = _r62n_static_bool(node.test)
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
            group_members: frozenset[str] | None = None
            remaining_members: frozenset[str] | None = None
            may_skip_handler = False
            if isinstance(node, ast.TryStar):
                group_members = _r62n_exception_group_members(raised.state)
                may_handle, fully_handled = _r62n_trystar_handler_partition(
                    group_members,
                    handler.type,
                    raised.state[0],
                )
                match: bool | None = True if may_handle else False
                remaining_members = _r62n_trystar_remaining_members(
                    group_members,
                    handler.type,
                    raised.state[0],
                )
                may_skip_handler = _r62n_trystar_handler_may_skip(
                    group_members,
                    handler.type,
                    raised.state[0],
                )
            else:
                match = _r62n_handler_match(
                    _r62n_exception_name(raised.state),
                    handler.type,
                    raised.state[0],
                )
                fully_handled = match is True
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
            handler_outcomes = _r62n_process_block(
                handler.body,
                [handler_state],
                top_index=top_index,
                timeline=timeline,
                observations=observations,
                precision_lost=precision_lost,
            )
            if handler.name is not None:
                for handler_outcome in handler_outcomes:
                    handler_outcome.state[0].pop(handler.name, None)
                    handler_outcome.state[1].pop(handler.name, None)

            if isinstance(node, ast.TryStar):
                if may_skip_handler:
                    next_unhandled.append(raised)
                for handler_outcome in handler_outcomes:
                    if (
                        handler_outcome.kind != "normal"
                        or fully_handled
                        or group_members is None
                    ):
                        handled.append(handler_outcome)
                    if fully_handled:
                        continue
                    remainder_state = _r62n_copy_state(handler_outcome.state)
                    _r62n_set_exception_tag(
                        remainder_state,
                        None,
                        group_members=remaining_members,
                    )
                    next_unhandled.append(
                        _r62m._R62MOutcome("raise", remainder_state)
                    )
                continue

            handled.extend(handler_outcomes)
            if match is None or not fully_handled:
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
    suppressed: list[_r62m._R62MOutcome] = []
    for outcome in body:
        if outcome.kind != "raise":
            continue
        suppressed_state = _r62n_copy_state(outcome.state)
        suppressed_state[0].pop(_R62N_EXCEPTION_TAG, None)
        suppressed.append(_r62m._R62MOutcome("normal", suppressed_state))
    return _r62m._r62m_bound_outcomes([*raised, *body, *suppressed])


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
    truth = _r62n_static_bool(node.test)
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


def _r62n_process_assert(
    node: ast.Assert,
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
    _r62n_eval(
        node.test,
        working,
        top_index=top_index,
        timeline=timeline,
        observations=observations,
        precision_lost=precision_lost,
    )
    _, test_raise_states = _r62n_ordered_expression_raise_states(
        node.test,
        state,
    )
    test_exception_name = _r62n_static_implicit_exception_name(node.test)
    raised = _r62n_raise_outcomes_from_states(
        test_raise_states,
        exception_name=test_exception_name,
    )
    truth = _r62n_static_bool(node.test)
    if truth is True:
        return _r62m._r62m_bound_outcomes(
            [*raised, _r62m._R62MOutcome("normal", working)]
        )

    failed = _r62n_copy_state(working)
    msg_raised: list[_r62m._R62MOutcome] = []
    if node.msg is not None:
        before_msg = _r62n_copy_state(failed)
        _r62n_eval(
            node.msg,
            failed,
            top_index=top_index,
            timeline=timeline,
            observations=observations,
            precision_lost=precision_lost,
        )
        _, msg_raise_states = _r62n_ordered_expression_raise_states(
            node.msg,
            before_msg,
        )
        msg_raised = _r62n_raise_outcomes_from_states(msg_raise_states)

    _r62n_set_exception_tag(failed, "AssertionError")
    assertion = _r62m._R62MOutcome("raise", failed)
    if truth is False:
        return _r62m._r62m_bound_outcomes([*raised, *msg_raised, assertion])
    return _r62m._r62m_bound_outcomes(
        [
            *raised,
            *msg_raised,
            assertion,
            _r62m._R62MOutcome("normal", working),
        ]
    )


def _r62n_process_builtin_import_from(
    node: ast.ImportFrom,
    state: _r62l._R62LState,
) -> list[_r62m._R62MOutcome]:
    working = _r62n_copy_state(state)
    for alias in node.names:
        if alias.name != "*" and not hasattr(_py_builtins, alias.name):
            failed = _r62n_copy_state(working)
            _r62n_set_exception_tag(failed, "ImportError")
            return [_r62m._R62MOutcome("raise", failed)]
        partial = ast.ImportFrom(
            module="builtins",
            names=[alias],
            level=0,
        )
        _r62j._r62j_apply_straight_line_module_binding(partial, working[0])
        _r62l._r62l_apply_owner_binding(partial, working[1])
    return [_r62m._R62MOutcome("normal", working)]


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

    if (
        isinstance(node, ast.ImportFrom)
        and any(alias.name == "*" for alias in node.names)
        and not (node.level == 0 and node.module == "builtins")
    ):
        early_failed = _r62n_copy_state(state)
        _r62n_set_exception_tag(early_failed, None)

        working = _r62n_copy_state(state)
        _r62n_taint_unknown_star_authority(working[0])
        precision_lost[0] = True

        partial_failed = _r62n_copy_state(working)
        _r62n_set_exception_tag(partial_failed, None)
        return _r62m._r62m_bound_outcomes(
            [
                _r62m._R62MOutcome("normal", working),
                _r62m._R62MOutcome("raise", early_failed),
                _r62m._R62MOutcome("raise", partial_failed),
            ]
        )
    if (
        isinstance(node, ast.ImportFrom)
        and node.level == 0
        and node.module == "builtins"
    ):
        return _r62n_process_builtin_import_from(node, state)
    if isinstance(node, ast.Raise):
        working = _r62n_copy_state(state)
        exception_name = _r62n_static_exception_name(node.exc, working[0])
        group_members = _r62n_static_exception_group_members(
            node.exc,
            working[0],
        )
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
        _r62n_set_exception_tag(
            working,
            exception_name,
            group_members=group_members,
        )
        return [_r62m._R62MOutcome("raise", working)]
    if isinstance(node, ast.Break):
        return [_r62m._R62MOutcome("break", _r62n_copy_state(state))]
    if isinstance(node, ast.Continue):
        return [_r62m._R62MOutcome("continue", _r62n_copy_state(state))]
    if isinstance(node, ast.Assert):
        return _r62n_process_assert(
            node,
            state,
            top_index=top_index,
            timeline=timeline,
            observations=observations,
            precision_lost=precision_lost,
        )
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
    ordered_expressions: list[ast.AST] = []
    if isinstance(node, (ast.Expr, ast.Assign)):
        ordered_expressions.append(node.value)
    elif isinstance(node, ast.AnnAssign):
        if node.value is not None:
            ordered_expressions.append(node.value)
        ordered_expressions.append(node.annotation)
    if ordered_expressions:
        working = _r62n_copy_state(state)
        raise_states: list[_r62l._R62LState] = []
        for expression in ordered_expressions:
            working, expression_raised = _r62n_ordered_expression_raise_states(
                expression,
                working,
            )
            raise_states.extend(expression_raised)
        exception_name = (
            _r62n_static_implicit_exception_name(ordered_expressions[0])
            if len(ordered_expressions) == 1
            else None
        )
        return _r62m._r62m_bound_outcomes(
            [
                *normal,
                *_r62n_raise_outcomes_from_states(
                    raise_states,
                    exception_name=exception_name,
                ),
            ]
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


def _r62n_contains_runtime_unknown_star(node: ast.AST) -> bool:
    if isinstance(
        node,
        (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda, ast.ClassDef),
    ):
        return False
    if (
        isinstance(node, ast.ImportFrom)
        and any(alias.name == "*" for alias in node.names)
        and not (node.level == 0 and node.module == "builtins")
    ):
        return True
    return any(
        _r62n_contains_runtime_unknown_star(child)
        for child in ast.iter_child_nodes(node)
    )


def _r62n_namespace_from_states(
    states: tuple[_r62l._R62LAuthorityBindings, ...],
) -> _Value:
    names = {
        name
        for state in states
        for name in state
        if name not in {_R62N_EXCEPTION_TAG, _R62N_STAR_IMPORT_TAINT}
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

    def _scan_flow_failed_star_exception_paths(
        self,
        node: ast.Try | ast.TryStar,
        environment: dict[str, _Value],
    ) -> None:
        if isinstance(node, ast.Try) and not any(
            _r62n_contains_runtime_unknown_star(statement)
            for statement in node.body
        ):
            return

        initial: _r62l._R62LState = (environment.copy(), {})
        scratch_timeline: dict[int, list[_r62l._R62LAuthorityBindings]] = {}
        scratch_observations: dict[
            _r62k._R62KOwner,
            list[_r62l._R62LAuthorityBindings],
        ] = {}
        precision_lost = [False]
        body = _r62n_process_block(
            node.body,
            [initial],
            top_index=0,
            timeline=scratch_timeline,
            observations=scratch_observations,
            precision_lost=precision_lost,
        )
        unhandled = [outcome for outcome in body if outcome.kind == "raise"]

        for handler in node.handlers:
            next_unhandled: list[_r62m._R62MOutcome] = []
            for raised_outcome in unhandled:
                group_members: frozenset[str] | None = None
                remaining_members: frozenset[str] | None = None
                may_skip_handler = False
                if isinstance(node, ast.TryStar):
                    group_members = _r62n_exception_group_members(
                        raised_outcome.state
                    )
                    may_handle, fully_handled = (
                        _r62n_trystar_handler_partition(
                            group_members,
                            handler.type,
                            raised_outcome.state[0],
                        )
                    )
                    match: bool | None = True if may_handle else False
                    remaining_members = _r62n_trystar_remaining_members(
                        group_members,
                        handler.type,
                        raised_outcome.state[0],
                    )
                    may_skip_handler = _r62n_trystar_handler_may_skip(
                        group_members,
                        handler.type,
                        raised_outcome.state[0],
                    )
                else:
                    match = _r62n_handler_match(
                        _r62n_exception_name(raised_outcome.state),
                        handler.type,
                        raised_outcome.state[0],
                    )
                    fully_handled = match is True
                if match is False:
                    next_unhandled.append(raised_outcome)
                    continue

                handler_environment = raised_outcome.state[0].copy()
                handler_environment.pop(_R62N_EXCEPTION_TAG, None)
                if handler.type is not None:
                    self._scan_expression(handler.type, handler_environment)
                if handler.name is not None:
                    handler_environment[handler.name] = _UNKNOWN
                self._scan_block(handler.body, handler_environment)
                if handler.name is not None:
                    handler_environment.pop(handler.name, None)

                if isinstance(node, ast.TryStar):
                    if may_skip_handler:
                        next_unhandled.append(raised_outcome)
                    if not fully_handled:
                        remainder_state: _r62l._R62LState = (
                            handler_environment.copy(),
                            raised_outcome.state[1].copy(),
                        )
                        _r62n_set_exception_tag(
                            remainder_state,
                            None,
                            group_members=remaining_members,
                        )
                        next_unhandled.append(
                            _r62m._R62MOutcome("raise", remainder_state)
                        )
                    continue

                if match is None or not fully_handled:
                    next_unhandled.append(raised_outcome)
            unhandled = next_unhandled

        if node.finalbody:
            if isinstance(node, ast.TryStar):
                pre_final_node: ast.Try | ast.TryStar = ast.TryStar(
                    body=node.body,
                    handlers=node.handlers,
                    orelse=node.orelse,
                    finalbody=[],
                )
            else:
                pre_final_node = ast.Try(
                    body=node.body,
                    handlers=node.handlers,
                    orelse=node.orelse,
                    finalbody=[],
                )
            pre_final = _r62n_process_try(
                pre_final_node,
                initial,
                top_index=0,
                timeline={},
                observations={},
                precision_lost=[False],
            )
            for pre_final_outcome in pre_final:
                final_environment = pre_final_outcome.state[0].copy()
                final_environment.pop(_R62N_EXCEPTION_TAG, None)
                self._scan_block(node.finalbody, final_environment)

        if isinstance(node, ast.TryStar):
            completed = _r62n_process_try(
                node,
                initial,
                top_index=0,
                timeline={},
                observations={},
                precision_lost=[False],
            )
            normal_environments = [
                outcome.state[0]
                for outcome in completed
                if outcome.kind == "normal"
            ]
            if normal_environments:
                environment.clear()
                self._merge_environments(
                    environment,
                    *normal_environments,
                )

    def _scan_exact_failed_builtin_import_try(
        self,
        node: ast.Try,
        environment: dict[str, _Value],
    ) -> bool:
        working = environment.copy()
        failure_environment: dict[str, _Value] | None = None

        for statement in node.body:
            if (
                isinstance(statement, ast.ImportFrom)
                and statement.level == 0
                and statement.module == "builtins"
            ):
                for alias in statement.names:
                    if alias.name != "*" and not hasattr(
                        _py_builtins,
                        alias.name,
                    ):
                        failure_environment = working.copy()
                        break
                    partial = ast.ImportFrom(
                        module="builtins",
                        names=[alias],
                        level=0,
                    )
                    self._scan_import_from(partial, working)
                if failure_environment is not None:
                    break
                continue

            if _r62n_simple_statement_may_raise(statement):
                return False
            self._scan_statement(statement, working)

        if failure_environment is None:
            return False

        selected: dict[str, _Value] | None = None
        for handler in node.handlers:
            match = _r62n_handler_match(
                "ImportError",
                handler.type,
                failure_environment,
            )
            if match is None:
                return False
            if not match:
                continue
            selected = failure_environment.copy()
            if handler.type is not None:
                self._scan_expression(handler.type, selected)
            if handler.name is not None:
                selected[handler.name] = _UNKNOWN
            self._scan_block(handler.body, selected)
            if handler.name is not None:
                selected.pop(handler.name, None)
            break

        if selected is None:
            selected = failure_environment.copy()
        if node.finalbody:
            self._scan_block(node.finalbody, selected)
        environment.clear()
        environment.update(selected)
        return True

    def _scan_conservative_failed_star_import_try(
        self,
        node: ast.Try,
        environment: dict[str, _Value],
    ) -> bool:
        if node.orelse or node.finalbody:
            return False

        working = environment.copy()
        failure_environments: list[dict[str, _Value]] = []
        saw_unknown_star = False

        for statement in node.body:
            if (
                isinstance(statement, ast.ImportFrom)
                and any(alias.name == "*" for alias in statement.names)
                and not (
                    statement.level == 0
                    and statement.module == "builtins"
                )
            ):
                saw_unknown_star = True
                failure_environments.append(working.copy())
                partial_failure = working.copy()
                _r62n_taint_unknown_star_authority(partial_failure)
                failure_environments.append(partial_failure)
                _r62n_taint_unknown_star_authority(working)
                continue

            if _r62n_simple_statement_may_raise(statement):
                return False
            self._scan_statement(statement, working)

        if not saw_unknown_star:
            return False

        branches: list[dict[str, _Value]] = [working]
        for handler in node.handlers:
            for failure_environment in failure_environments:
                handler_environment = failure_environment.copy()
                if handler.type is not None:
                    self._scan_expression(
                        handler.type,
                        handler_environment,
                    )
                if handler.name is not None:
                    handler_environment[handler.name] = _UNKNOWN
                self._scan_block(handler.body, handler_environment)
                if handler.name is not None:
                    handler_environment.pop(handler.name, None)
                branches.append(handler_environment)

        self._merge_environments(environment, *branches)
        return True

    def _scan_import_from(
        self,
        node: ast.ImportFrom,
        environment: dict[str, _Value],
    ) -> None:
        if (
            any(alias.name == "*" for alias in node.names)
            and not (node.level == 0 and node.module == "builtins")
        ):
            _r62n_taint_unknown_star_authority(environment)
            return
        super()._scan_import_from(node, environment)

    def _scan_expression(
        self,
        node: ast.AST,
        environment: dict[str, _Value],
    ) -> _Value:
        if (
            isinstance(node, ast.Name)
            and node.id not in environment
            and _R62N_STAR_IMPORT_TAINT in environment
        ):
            return _r12._merge_values(
                super()._scan_expression(node, environment),
                _r12._DANGEROUS_CALLABLE,
            )
        return super()._scan_expression(node, environment)

    def _scan_statement(
        self,
        node: ast.stmt,
        environment: dict[str, _Value],
    ) -> None:
        if isinstance(node, ast.TryStar):
            original_environment = environment.copy()
            self._scan_flow_failed_star_exception_paths(node, environment)
            successor_environment = environment.copy()

            body_environment = original_environment.copy()
            self._scan_block(node.body, body_environment)
            if node.orelse:
                self._scan_block(node.orelse, body_environment)

            environment.clear()
            environment.update(successor_environment)
            return
        if isinstance(node, ast.Try):
            self._scan_flow_failed_star_exception_paths(node, environment)
        if (
            isinstance(node, ast.Try)
            and self._scan_conservative_failed_star_import_try(
                node,
                environment,
            )
        ):
            return
        if isinstance(node, ast.Try) and self._scan_exact_failed_builtin_import_try(
            node,
            environment,
        ):
            return
        if isinstance(node, ast.Assert):
            self._scan_expression(node.test, environment)
            if _r62n_static_bool(node.test) is not True and node.msg is not None:
                self._scan_expression(node.msg, environment)
            return
        super()._scan_statement(node, environment)

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

def test_r62n_trystar_exact_group_members_preserve_danger_and_safe_inverse() -> None:
    dangerous = """\
def run():
    return getattr(globals()["b"], "eval", lambda _: 3)("1+1")
try:
    raise ExceptionGroup("x", [ValueError()])
except* ValueError:
    import builtins as b
    result = run()
b = len
"""
    safe = """\
import builtins as b
def run():
    return getattr(globals()["b"], "eval", lambda _: 3)("1+1")
try:
    raise ExceptionGroup("x", [ValueError()])
except* ValueError:
    b = len
    result = run()
"""
    assert _runtime_result(dangerous) == 2
    assert _runtime_result(safe) == 3
    assert _r62n_dynamic_execution_markers_from_source(dangerous)
    assert _r62n_dynamic_execution_markers_from_source(safe) == ()


def test_r62n_literal_zero_division_routes_only_matching_handler() -> None:
    source = """\
import builtins as b
def run():
    return getattr(globals()["b"], "eval", lambda _: 3)("1+1")
try:
    b = len
    1 / 0
except KeyError:
    import builtins as b
    result = run()
except ZeroDivisionError:
    b = len
    result = run()
"""
    assert _runtime_result(source) == 3
    assert _r62n_dynamic_execution_markers_from_source(source) == ()


def test_r62n_constant_truthiness_preserves_safe_and_dangerous() -> None:
    safe = """\
import builtins as b
def run():
    return getattr(globals()["b"], "eval", lambda _: 3)("1+1")
if 0:
    import builtins as b
    result = run()
b = len
result = run()
"""
    dangerous = """\
def run():
    return getattr(globals()["b"], "eval", lambda _: 3)("1+1")
if 1:
    import builtins as b
    result = run()
b = len
"""
    assert _runtime_result(safe) == 3
    assert _runtime_result(dangerous) == 2
    assert _r62n_dynamic_execution_markers_from_source(safe) == ()
    assert _r62n_dynamic_execution_markers_from_source(dangerous)


def test_r62n_annassign_and_assert_namedexpr_exception_order_is_safe() -> None:
    annassign = """\
import builtins as b
def run():
    return getattr(globals()["b"], "eval", lambda _: 3)("1+1")
try:
    x: object = ((b := len), 1 / 0)
except ZeroDivisionError:
    result = run()
"""
    assertion = """\
import builtins as b
def run():
    return getattr(globals()["b"], "eval", lambda _: 3)("1+1")
try:
    assert ((b := len), 1 / 0)
except ZeroDivisionError:
    result = run()
"""
    assert _runtime_result(annassign) == 3
    assert _runtime_result(assertion) == 3
    assert _r62n_dynamic_execution_markers_from_source(annassign) == ()
    assert _r62n_dynamic_execution_markers_from_source(assertion) == ()

def test_r62n_complex_floor_mod_do_not_invent_zero_division_type() -> None:
    sources = (
        """\
def run():
    return getattr(globals()["b"], "eval", lambda _: 3)("1+1")
try:
    1j // 0j
except TypeError:
    import builtins as b
    result = run()
except ZeroDivisionError:
    b = len
    result = run()
""",
        """\
def run():
    return getattr(globals()["b"], "eval", lambda _: 3)("1+1")
try:
    1j % 0j
except TypeError:
    import builtins as b
    result = run()
except ZeroDivisionError:
    b = len
    result = run()
""",
    )
    for source in sources:
        assert _runtime_result(source) == 2
        assert _r62n_dynamic_execution_markers_from_source(source)


def test_r62n_assert_true_does_not_evaluate_message() -> None:
    safe = """\
import builtins
b = len
def run():
    return getattr(globals()["b"], "eval", lambda _: 3)("1+1")
assert True, (b := builtins)
result = run()
"""
    dangerous = """\
import builtins as b
def run():
    return getattr(globals()["b"], "eval", lambda _: 3)("1+1")
assert True, (b := len)
result = run()
b = len
"""
    assert _runtime_result(safe) == 3
    assert _runtime_result(dangerous) == 2
    assert _r62n_dynamic_execution_markers_from_source(safe) == ()
    assert _r62n_dynamic_execution_markers_from_source(dangerous)


def test_r62n_assert_false_evaluates_message_before_assertion_error() -> None:
    safe = """\
import builtins as b
def run():
    return getattr(globals()["b"], "eval", lambda _: 3)("1+1")
try:
    assert False, (b := len)
except AssertionError:
    result = run()
"""
    dangerous = """\
import builtins
b = len
def run():
    return getattr(globals()["b"], "eval", lambda _: 3)("1+1")
try:
    assert False, (b := builtins)
except AssertionError:
    result = run()
b = len
"""
    assert _runtime_result(safe) == 3
    assert _runtime_result(dangerous) == 2
    assert _r62n_dynamic_execution_markers_from_source(safe) == ()
    assert _r62n_dynamic_execution_markers_from_source(dangerous)



def test_r62n_namedexpr_truthiness_skips_unreachable_assert_message() -> None:
    source = """\\
import builtins
b = len
def run():
    return getattr(globals()["b"], "eval", lambda _: 3)("1+1")
assert (flag := True), (b := builtins)
result = run()
"""
    assert _runtime_result(source) == 3
    assert _r62n_dynamic_execution_markers_from_source(source) == ()


def test_r62n_builtin_from_import_preserves_partial_failure_order() -> None:
    missing = "definitely_missing_qore_r62n_builtin_name"
    assert not hasattr(_py_builtins, missing)

    dangerous = f"""\\
b = len
try:
    from builtins import eval as b, {missing}
except ImportError:
    result = b("1+1")
"""
    safe = f"""\\
b = len
try:
    from builtins import {missing}, eval as b
except ImportError:
    result = b("abc")
"""
    assert _runtime_result(dangerous) == 2
    assert _runtime_result(safe) == 3
    assert _r62n_dynamic_execution_markers_from_source(dangerous)
    assert _r62n_dynamic_execution_markers_from_source(safe) == ()


def test_r62n_with_body_exception_may_be_suppressed_by_exit() -> None:
    source = """\\
class Swallow:
    def __enter__(self):
        return self
    def __exit__(self, exc_type, exc, tb):
        return True

def run():
    return getattr(globals()["b"], "eval", lambda _: 3)("1+1")

with Swallow():
    import builtins as b
    raise RuntimeError("suppressed")
result = run()
"""
    assert _runtime_result(source) == 2
    assert _r62n_dynamic_execution_markers_from_source(source)


def test_r62n_exception_handler_target_is_deleted_after_handler() -> None:
    source = """\\
import builtins as b
def run():
    return getattr(globals().get("b", len), "eval", lambda _: 3)("1+1")
try:
    raise ValueError("x")
except ValueError as b:
    pass
result = run()
"""
    assert _runtime_result(source) == 3
    assert _r62n_dynamic_execution_markers_from_source(source) == ()


class _R62NStarImportModule(types.ModuleType):
    b: object
    __all__: list[str]
    dynamic_alias: object

def test_r62n_failed_star_import_preserves_possible_partial_authority() -> None:
    module_name = "qore_r62n_star_import_regression"
    module = _R62NStarImportModule(module_name)
    module.b = _py_builtins.eval
    sys.modules[module_name] = module
    try:
        module.__all__ = ["b", "missing"]
        dangerous = f"""\
b = len
try:
    from {module_name} import *
except AttributeError:
    pass
result = b("1+1")
"""
        assert _runtime_result(dangerous) == 2
        assert _r62n_dynamic_execution_markers_from_source(dangerous)

        module.__all__ = ["missing", "b"]
        inverse = f"""\
b = len
try:
    from {module_name} import *
except AttributeError:
    pass
result = b("abc")
"""
        assert _runtime_result(inverse) == 3
        assert _r62n_dynamic_execution_markers_from_source(inverse)
    finally:
        sys.modules.pop(module_name, None)


def test_r62n_nested_failed_star_exception_state_crosses_finally() -> None:
    module_name = "qore_r62n_nested_star_regression"
    module = _R62NStarImportModule(module_name)
    module.__all__ = ["b", "missing"]
    module.b = _py_builtins.eval
    sys.modules[module_name] = module
    try:
        handler_danger = (
            "b = len\n"
            "try:\n"
            "    try:\n"
            f"        from {module_name} import *\n"
            "    finally:\n"
            "        marker = 1\n"
            "except AttributeError:\n"
            "    result = b(\"1+1\")\n"
        )
        finalbody_danger = (
            "b = len\n"
            "try:\n"
            f"    from {module_name} import *\n"
            "except AttributeError:\n"
            "    pass\n"
            "finally:\n"
            "    result = b(\"1+1\")\n"
            "    b = len\n"
        )
        safe = (
            "b = len\n"
            "try:\n"
            "    try:\n"
            f"        from {module_name} import *\n"
            "    finally:\n"
            "        b = lambda _: 3\n"
            "except AttributeError:\n"
            "    result = b(\"abc\")\n"
        )
        assert _runtime_result(handler_danger) == 2
        assert _runtime_result(finalbody_danger) == 2
        assert _runtime_result(safe) == 3
        assert _r62n_dynamic_execution_markers_from_source(handler_danger)
        assert _r62n_dynamic_execution_markers_from_source(finalbody_danger)
        assert _r62n_dynamic_execution_markers_from_source(safe) == ()
    finally:
        sys.modules.pop(module_name, None)



def test_r62n_failed_star_trystar_handlers_preserve_partial_authority() -> None:
    module_name = "qore_r62n_trystar_star_regression"
    module = _R62NStarImportModule(module_name)
    module.__all__ = ["b", "missing"]
    module.b = _py_builtins.eval
    sys.modules[module_name] = module
    try:
        handler_danger = (
            "b = len\n"
            "try:\n"
            f"    from {module_name} import *\n"
            "except* AttributeError:\n"
            "    result = b(\"1+1\")\n"
        )
        downstream_danger = (
            "b = len\n"
            "try:\n"
            f"    from {module_name} import *\n"
            "except* AttributeError:\n"
            "    pass\n"
            "result = b(\"1+1\")\n"
        )
        assert _runtime_result(handler_danger) == 2
        assert _runtime_result(downstream_danger) == 2
        assert _r62n_dynamic_execution_markers_from_source(handler_danger)
        assert _r62n_dynamic_execution_markers_from_source(downstream_danger)
    finally:
        sys.modules.pop(module_name, None)



def test_r62n_failed_star_trystar_partial_groups_and_safe_successors() -> None:
    module_name = "qore_r62n_trystar_partition_regression"
    module = _R62NStarImportModule(module_name)
    module.__all__ = ["b", "missing"]
    module.b = _py_builtins.eval
    sys.modules[module_name] = module
    try:
        handler_safe = (
            "b = len\n"
            "try:\n"
            "    try:\n"
            f"        from {module_name} import *\n"
            "    finally:\n"
            "        b = lambda _: 3\n"
            "except* AttributeError:\n"
            "    result = b(\"abc\")\n"
        )
        downstream_safe = (
            "b = len\n"
            "try:\n"
            "    try:\n"
            f"        from {module_name} import *\n"
            "    finally:\n"
            "        b = lambda _: 3\n"
            "except* AttributeError:\n"
            "    pass\n"
            "result = b(\"abc\")\n"
        )
        first_handler_danger = (
            "b = len\n"
            "try:\n"
            "    try:\n"
            f"        from {module_name} import *\n"
            "    finally:\n"
            "        raise ExceptionGroup(\"eg\", [AttributeError(\"a\"), ValueError(\"v\")])\n"
            "except* AttributeError:\n"
            "    result = b(\"1+1\")\n"
            "except* ValueError:\n"
            "    pass\n"
        )
        second_handler_danger = (
            "b = len\n"
            "try:\n"
            "    try:\n"
            f"        from {module_name} import *\n"
            "    finally:\n"
            "        raise ExceptionGroup(\"eg\", [AttributeError(\"a\"), ValueError(\"v\")])\n"
            "except* AttributeError:\n"
            "    pass\n"
            "except* ValueError:\n"
            "    result = b(\"1+1\")\n"
        )
        assert _runtime_result(handler_safe) == 3
        assert _runtime_result(downstream_safe) == 3
        assert _runtime_result(first_handler_danger) == 2
        assert _runtime_result(second_handler_danger) == 2
        assert _r62n_dynamic_execution_markers_from_source(handler_safe) == ()
        assert _r62n_dynamic_execution_markers_from_source(downstream_safe) == ()
        assert "call:8" in _r62n_dynamic_execution_markers_from_source(
            first_handler_danger
        )
        assert "call:10" in _r62n_dynamic_execution_markers_from_source(
            second_handler_danger
        )

        module.__all__ = ["b"]
        module.b = len
        body_danger = (
            "try:\n"
            f"    from {module_name} import *\n"
            "    result = eval(\"1+1\")\n"
            "except* AttributeError:\n"
            "    result = 3\n"
        )
        assert _runtime_result(body_danger) == 2
        assert "call:3" in _r62n_dynamic_execution_markers_from_source(body_danger)
    finally:
        sys.modules.pop(module_name, None)



def test_r62n_trystar_failed_star_cross_handler_remains_conservative() -> None:
    module_name = "qore_r62n_trystar_cross_handler_regression"
    module = _R62NStarImportModule(module_name)
    module.__all__ = ["b", "missing"]
    module.b = _py_builtins.eval
    sys.modules[module_name] = module
    try:
        safe_rebind = f"""\
b = len
try:
    try:
        from {module_name} import *
    except AttributeError:
        raise ExceptionGroup("eg", [AttributeError("a"), ValueError("v")])
except* AttributeError:
    b = lambda _: 3
except* ValueError:
    result = b("1+1")
"""
        unsafe_control = f"""\
b = len
try:
    try:
        from {module_name} import *
    except AttributeError:
        raise ExceptionGroup("eg", [AttributeError("a"), ValueError("v")])
except* AttributeError:
    pass
except* ValueError:
    result = b("1+1")
"""
        introduced_danger = """\
b = len
try:
    raise ExceptionGroup("eg", [AttributeError("a"), ValueError("v")])
except* AttributeError:
    b = eval
except* ValueError:
    result = b("1+1")
"""

        assert _runtime_result(safe_rebind) == 3
        assert _runtime_result(unsafe_control) == 2
        assert _runtime_result(introduced_danger) == 2

        safe_markers = _r62n_dynamic_execution_markers_from_source(safe_rebind)
        unsafe_markers = _r62n_dynamic_execution_markers_from_source(
            unsafe_control
        )
        introduced_markers = _r62n_dynamic_execution_markers_from_source(
            introduced_danger
        )

        assert "call:10" in safe_markers
        assert "call:10" in unsafe_markers
        assert "call:7" in introduced_markers
    finally:
        sys.modules.pop(module_name, None)


def test_r62n_trystar_static_group_cross_handler_state_is_sequential() -> None:
    safe = """\
b = eval
try:
    raise ExceptionGroup("eg", [AttributeError("a"), ValueError("v")])
except* AttributeError:
    b = len
except* ValueError:
    result = b("1+1")
"""
    dangerous = """\
b = len
try:
    raise ExceptionGroup("eg", [AttributeError("a"), ValueError("v")])
except* AttributeError:
    b = eval
except* ValueError:
    result = b("1+1")
"""
    assert _runtime_result(safe) == 3
    assert _runtime_result(dangerous) == 2
    assert "call:7" not in _r62n_dynamic_execution_markers_from_source(safe)
    assert "call:7" in _r62n_dynamic_execution_markers_from_source(dangerous)


def test_r62n_trystar_finalbody_observes_completed_handler_chain() -> None:
    safe = """\
b = eval
try:
    raise ExceptionGroup("eg", [AttributeError("a"), ValueError("v")])
except* AttributeError:
    b = eval
except* ValueError:
    b = len
finally:
    result = b("1+1")
"""
    dangerous = """\
b = len
try:
    raise ExceptionGroup("eg", [AttributeError("a"), ValueError("v")])
except* AttributeError:
    b = len
except* ValueError:
    b = eval
finally:
    result = b("1+1")
"""
    assert _runtime_result(safe) == 3
    assert _runtime_result(dangerous) == 2
    assert "call:9" not in _r62n_dynamic_execution_markers_from_source(safe)
    assert "call:9" in _r62n_dynamic_execution_markers_from_source(dangerous)

def test_r62n_unknown_star_import_taints_new_call_names() -> None:
    module_name = "qore_r62n_star_new_name_regression"
    module = _R62NStarImportModule(module_name)
    module.__all__ = ["dynamic_alias"]
    module.dynamic_alias = _py_builtins.eval
    sys.modules[module_name] = module
    try:
        source = f"""\
from {module_name} import *
result = dynamic_alias("1+1")
"""
        assert _runtime_result(source) == 2
        assert _r62n_dynamic_execution_markers_from_source(source)
    finally:
        sys.modules.pop(module_name, None)

from __future__ import annotations

import ast
from dataclasses import dataclass
from typing import Literal

import test_universal_cross_asset_conformance_final_owner_r12_guards as _r12
import test_universal_cross_asset_conformance_final_owner_r62i_guards as _r62i
import test_universal_cross_asset_conformance_final_owner_r62j_guards as _r62j
import test_universal_cross_asset_conformance_final_owner_r62k_guards as _r62k
import test_universal_cross_asset_conformance_final_owner_r62l_guards as _r62l
from test_universal_cross_asset_conformance_final_owner_r12_guards import (
    _FULL_CLOSURE_ORACLE_PATH,
    _UNKNOWN,
    _owner_paths,
    _Value,
)

_R62MKind = Literal["normal", "raise", "break", "continue"]
_R62M_MAX_STATES = 64


@dataclass(frozen=True, slots=True)
class _R62MOutcome:
    kind: _R62MKind
    state: _r62l._R62LState


def _r62m_copy_state(state: _r62l._R62LState) -> _r62l._R62LState:
    return _r62l._r62l_copy_state(state)


def _r62m_bound_outcomes(outcomes: list[_R62MOutcome]) -> list[_R62MOutcome]:
    grouped: dict[_R62MKind, list[_r62l._R62LState]] = {
        "normal": [],
        "raise": [],
        "break": [],
        "continue": [],
    }
    for outcome in outcomes:
        if outcome.state not in grouped[outcome.kind]:
            grouped[outcome.kind].append(outcome.state)

    result: list[_R62MOutcome] = []
    for kind, states in grouped.items():
        if len(states) > _R62M_MAX_STATES:
            states = [_r62l._r62l_merged_state(states)]
        result.extend(_R62MOutcome(kind, state) for state in states)
    return result


def _r62m_eval(
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
    _r62l._r62l_eval_expression(
        node,
        state,
        top_index=top_index,
        timeline=timeline,
        observations=observations,
        precision_lost=precision_lost,
    )


def _r62m_process_block(
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
) -> list[_R62MOutcome]:
    outcomes = [_R62MOutcome("normal", state) for state in states]
    for statement in statements:
        next_outcomes: list[_R62MOutcome] = []
        for outcome in outcomes:
            if outcome.kind != "normal":
                next_outcomes.append(outcome)
                continue
            next_outcomes.extend(
                _r62m_process_statement(
                    statement,
                    outcome.state,
                    top_index=top_index,
                    timeline=timeline,
                    observations=observations,
                    precision_lost=precision_lost,
                )
            )
        outcomes = _r62m_bound_outcomes(next_outcomes)
    return outcomes


def _r62m_process_finally(
    outcomes: list[_R62MOutcome],
    statements: list[ast.stmt],
    *,
    top_index: int,
    timeline: dict[int, list[_r62l._R62LAuthorityBindings]],
    observations: dict[
        _r62k._R62KOwner,
        list[_r62l._R62LAuthorityBindings],
    ],
    precision_lost: list[bool],
) -> list[_R62MOutcome]:
    result: list[_R62MOutcome] = []
    for incoming in outcomes:
        final = _r62m_process_block(
            statements,
            [_r62m_copy_state(incoming.state)],
            top_index=top_index,
            timeline=timeline,
            observations=observations,
            precision_lost=precision_lost,
        )
        for completed in final:
            if completed.kind == "normal":
                result.append(_R62MOutcome(incoming.kind, completed.state))
            else:
                result.append(completed)
    return _r62m_bound_outcomes(result)


def _r62m_process_if(
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
) -> list[_R62MOutcome]:
    working = _r62m_copy_state(state)
    _r62m_eval(
        node.test,
        working,
        top_index=top_index,
        timeline=timeline,
        observations=observations,
        precision_lost=precision_lost,
    )
    truth = _r62l._r62l_static_bool(node.test)
    if truth is True:
        return _r62m_process_block(
            node.body,
            [working],
            top_index=top_index,
            timeline=timeline,
            observations=observations,
            precision_lost=precision_lost,
        )
    if truth is False:
        if not node.orelse:
            return [_R62MOutcome("normal", working)]
        return _r62m_process_block(
            node.orelse,
            [working],
            top_index=top_index,
            timeline=timeline,
            observations=observations,
            precision_lost=precision_lost,
        )
    body = _r62m_process_block(
        node.body,
        [_r62m_copy_state(working)],
        top_index=top_index,
        timeline=timeline,
        observations=observations,
        precision_lost=precision_lost,
    )
    other = (
        _r62m_process_block(
            node.orelse,
            [_r62m_copy_state(working)],
            top_index=top_index,
            timeline=timeline,
            observations=observations,
            precision_lost=precision_lost,
        )
        if node.orelse
        else [_R62MOutcome("normal", _r62m_copy_state(working))]
    )
    return _r62m_bound_outcomes([*body, *other])


def _r62m_handler_entry_states(
    body: list[_R62MOutcome],
    original: _r62l._R62LState,
) -> list[_r62l._R62LState]:
    entries = [_r62m_copy_state(original)]
    for outcome in body:
        if outcome.kind == "raise" and outcome.state not in entries:
            entries.append(_r62m_copy_state(outcome.state))
    return entries


def _r62m_process_try(
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
) -> list[_R62MOutcome]:
    body = _r62m_process_block(
        node.body,
        [_r62m_copy_state(state)],
        top_index=top_index,
        timeline=timeline,
        observations=observations,
        precision_lost=precision_lost,
    )

    normal_states = [item.state for item in body if item.kind == "normal"]
    successful: list[_R62MOutcome]
    if node.orelse and normal_states:
        successful = _r62m_process_block(
            node.orelse,
            normal_states,
            top_index=top_index,
            timeline=timeline,
            observations=observations,
            precision_lost=precision_lost,
        )
    else:
        successful = [
            _R62MOutcome("normal", item.state)
            for item in body
            if item.kind == "normal"
        ]

    propagated = [
        item for item in body if item.kind in {"break", "continue"}
    ]
    raised = [item for item in body if item.kind == "raise"]
    handled: list[_R62MOutcome] = []
    entries = _r62m_handler_entry_states(body, state)

    for handler in node.handlers:
        for entry in entries:
            handler_state = _r62m_copy_state(entry)
            if handler.type is not None:
                _r62m_eval(
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
                _r62m_process_block(
                    handler.body,
                    [handler_state],
                    top_index=top_index,
                    timeline=timeline,
                    observations=observations,
                    precision_lost=precision_lost,
                )
            )

    combined = _r62m_bound_outcomes(
        [*successful, *propagated, *raised, *handled]
    )
    if node.finalbody:
        return _r62m_process_finally(
            combined,
            node.finalbody,
            top_index=top_index,
            timeline=timeline,
            observations=observations,
            precision_lost=precision_lost,
        )
    return combined


def _r62m_loop_body(
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
) -> list[_R62MOutcome]:
    body_state = _r62m_copy_state(state)
    if target is not None:
        _r62j._r62j_assign_names(target, _UNKNOWN, body_state[0])
        _r62l._r62l_assign_owner_names(target, frozenset(), body_state[1])
    return _r62m_process_block(
        statements,
        [body_state],
        top_index=top_index,
        timeline=timeline,
        observations=observations,
        precision_lost=precision_lost,
    )


def _r62m_process_for(
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
) -> list[_R62MOutcome]:
    working = _r62m_copy_state(state)
    _r62m_eval(
        node.iter,
        working,
        top_index=top_index,
        timeline=timeline,
        observations=observations,
        precision_lost=precision_lost,
    )
    if isinstance(node, ast.AsyncFor):
        precision_lost[0] = True

    body = _r62m_loop_body(
        node.body,
        working,
        target=node.target,
        top_index=top_index,
        timeline=timeline,
        observations=observations,
        precision_lost=precision_lost,
    )
    breaks = [
        _R62MOutcome("normal", item.state)
        for item in body
        if item.kind == "break"
    ]
    raised = [item for item in body if item.kind == "raise"]
    natural = [_r62m_copy_state(working)]
    natural.extend(
        item.state for item in body if item.kind in {"normal", "continue"}
    )

    natural_outcomes = (
        _r62m_process_block(
            node.orelse,
            natural,
            top_index=top_index,
            timeline=timeline,
            observations=observations,
            precision_lost=precision_lost,
        )
        if node.orelse
        else [_R62MOutcome("normal", item) for item in natural]
    )
    return _r62m_bound_outcomes([*breaks, *raised, *natural_outcomes])


def _r62m_process_while(
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
) -> list[_R62MOutcome]:
    working = _r62m_copy_state(state)
    _r62m_eval(
        node.test,
        working,
        top_index=top_index,
        timeline=timeline,
        observations=observations,
        precision_lost=precision_lost,
    )
    truth = _r62l._r62l_static_bool(node.test)
    if truth is False:
        natural = [working]
        if not node.orelse:
            return [_R62MOutcome("normal", working)]
        return _r62m_process_block(
            node.orelse,
            natural,
            top_index=top_index,
            timeline=timeline,
            observations=observations,
            precision_lost=precision_lost,
        )

    body = _r62m_loop_body(
        node.body,
        working,
        target=None,
        top_index=top_index,
        timeline=timeline,
        observations=observations,
        precision_lost=precision_lost,
    )
    breaks = [
        _R62MOutcome("normal", item.state)
        for item in body
        if item.kind == "break"
    ]
    raised = [item for item in body if item.kind == "raise"]
    repeated = [
        item.state for item in body if item.kind in {"normal", "continue"}
    ]

    if truth is True:
        if repeated:
            precision_lost[0] = True
        return _r62m_bound_outcomes([*breaks, *raised])

    natural = [_r62m_copy_state(working), *repeated]
    natural_outcomes = (
        _r62m_process_block(
            node.orelse,
            natural,
            top_index=top_index,
            timeline=timeline,
            observations=observations,
            precision_lost=precision_lost,
        )
        if node.orelse
        else [_R62MOutcome("normal", item) for item in natural]
    )
    return _r62m_bound_outcomes([*breaks, *raised, *natural_outcomes])


def _r62m_process_statement(
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
) -> list[_R62MOutcome]:
    _r62l._r62l_record_timeline(timeline, top_index, state[0])

    if isinstance(node, ast.Raise):
        working = _r62m_copy_state(state)
        if node.exc is not None:
            _r62m_eval(
                node.exc,
                working,
                top_index=top_index,
                timeline=timeline,
                observations=observations,
                precision_lost=precision_lost,
            )
        if node.cause is not None:
            _r62m_eval(
                node.cause,
                working,
                top_index=top_index,
                timeline=timeline,
                observations=observations,
                precision_lost=precision_lost,
            )
        return [_R62MOutcome("raise", working)]

    if isinstance(node, ast.Break):
        return [_R62MOutcome("break", _r62m_copy_state(state))]
    if isinstance(node, ast.Continue):
        return [_R62MOutcome("continue", _r62m_copy_state(state))]
    if isinstance(node, ast.If):
        return _r62m_process_if(
            node,
            state,
            top_index=top_index,
            timeline=timeline,
            observations=observations,
            precision_lost=precision_lost,
        )
    if isinstance(node, (ast.Try, ast.TryStar)):
        return _r62m_process_try(
            node,
            state,
            top_index=top_index,
            timeline=timeline,
            observations=observations,
            precision_lost=precision_lost,
        )
    if isinstance(node, (ast.For, ast.AsyncFor)):
        return _r62m_process_for(
            node,
            state,
            top_index=top_index,
            timeline=timeline,
            observations=observations,
            precision_lost=precision_lost,
        )
    if isinstance(node, ast.While):
        return _r62m_process_while(
            node,
            state,
            top_index=top_index,
            timeline=timeline,
            observations=observations,
            precision_lost=precision_lost,
        )

    states = _r62l._r62l_process_statement(
        node,
        _r62m_copy_state(state),
        top_index=top_index,
        timeline=timeline,
        observations=observations,
        precision_lost=precision_lost,
    )
    return [_R62MOutcome("normal", item) for item in states]


def _r62m_flow(
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
    states: list[_r62l._R62LState] = [
        ({"__builtins__": _r12._BUILTINS_NAMESPACE}, {})
    ]
    timeline: dict[int, list[_r62l._R62LAuthorityBindings]] = {}
    observations: dict[
        _r62k._R62KOwner,
        list[_r62l._R62LAuthorityBindings],
    ] = {}
    precision_lost = [False]

    outcomes: list[_R62MOutcome] = [
        _R62MOutcome("normal", states[0])
    ]
    for top_index, statement in enumerate(tree.body):
        next_outcomes: list[_R62MOutcome] = []
        for outcome in outcomes:
            if outcome.kind != "normal":
                next_outcomes.append(outcome)
                continue
            next_outcomes.extend(
                _r62m_process_statement(
                    statement,
                    outcome.state,
                    top_index=top_index,
                    timeline=timeline,
                    observations=observations,
                    precision_lost=precision_lost,
                )
            )
        outcomes = _r62m_bound_outcomes(next_outcomes)

    for outcome in outcomes:
        if outcome.kind != "normal":
            continue
        authority, owner_bindings = outcome.state
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


def _r62m_future_authority_by_call(
    source: str,
    timeline: dict[int, tuple[_r62l._R62LAuthorityBindings, ...]],
) -> dict[tuple[int, int], dict[str, tuple[_Value, bool]]]:
    return _r62l._r62l_future_authority_by_call(source, timeline)


def _r62m_observable_authority_by_call(
    source: str,
) -> dict[tuple[int, int], dict[str, tuple[_Value, bool]]]:
    observations, timeline, precision_lost = _r62m_flow(source)
    fallback = _r62m_future_authority_by_call(source, timeline)
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


class _R62MAbruptControlFlowGlobalsScanner(
    _r62l._R62LControlFlowObservableGlobalsScanner
):
    """Preserve module authority at explicit abrupt control-flow boundaries."""

    def scan(self, source: str) -> tuple[str, ...]:
        self._r62j_future_authority_by_call = _r62m_observable_authority_by_call(
            source
        )
        return _r62i._R62IModuleAndParameterNamespaceScanner.scan(self, source)


def _r62m_dynamic_execution_markers_from_source(source: str) -> tuple[str, ...]:
    return _R62MAbruptControlFlowGlobalsScanner().scan(source)


def _runtime_result(source: str) -> object:
    namespace: dict[str, object] = {}
    exec(compile(source, "<r62m>", "exec", dont_inherit=True), namespace)
    return namespace["result"]


def test_r62m_predecessor_reproduces_abrupt_flow_false_negatives() -> None:
    sources = (
        """\
def run():
    return globals()["b"].eval("1+1")
try:
    import builtins as b
    raise RuntimeError
except RuntimeError:
    result = run()
b = len
""",
        """\
def run():
    return globals()["b"].eval("1+1")
for _ in (0,):
    import builtins as b
    break
    b = len
result = run()
""",
    )
    for source in sources:
        assert _runtime_result(source) == 2
        assert _r62l._r62l_dynamic_execution_markers_from_source(source) == ()


def test_r62m_abrupt_flow_authority_fails_closed() -> None:
    sources = (
        """\
def run():
    return globals()["b"].eval("1+1")
try:
    import builtins as b
    raise RuntimeError
except RuntimeError:
    result = run()
b = len
""",
        """\
def run():
    return globals()["b"].eval("1+1")
for _ in (0,):
    import builtins as b
    break
    b = len
result = run()
""",
        """\
def run():
    return globals()["b"].eval("1+1")
while True:
    import builtins as b
    break
    b = len
result = run()
""",
    )
    for source in sources:
        assert _runtime_result(source) == 2
        assert _r62m_dynamic_execution_markers_from_source(source)


def test_r62m_safe_handler_and_false_branch_remain_clean() -> None:
    sources = (
        """\
def run():
    return getattr(globals()["b"], "eval", lambda _: 3)("1+1")
try:
    raise RuntimeError
except RuntimeError:
    b = len
    result = run()
""",
        """\
def run():
    return globals()["b"].eval("1+1")
if False:
    import builtins as b
try:
    result = run()
except KeyError:
    result = 3
""",
    )
    for source in sources:
        assert _runtime_result(source) == 3
        assert _r62m_dynamic_execution_markers_from_source(source) == ()


def test_r62m_same_statement_ordering_remains_authoritative() -> None:
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
    assert _runtime_result(safe) == 3
    assert _runtime_result(dangerous) == 2
    assert _r62m_dynamic_execution_markers_from_source(safe) == ()
    assert _r62m_dynamic_execution_markers_from_source(dangerous)


def test_r62m_compound_alias_remains_fail_closed() -> None:
    source = """\
def run():
    return globals()["b"].eval("1+1")
if True:
    alias = run
    import builtins as b
    result = alias()
b = len
"""
    assert _runtime_result(source) == 2
    assert _r62m_dynamic_execution_markers_from_source(source)


def test_r62m_complete_owner_and_oracle_surface_has_no_dynamic_execution() -> None:
    paths = (*_owner_paths(), _FULL_CLOSURE_ORACLE_PATH)
    for path in paths:
        assert _r62m_dynamic_execution_markers_from_source(
            path.read_text(encoding="utf-8")
        ) == (), path

from __future__ import annotations

from pathlib import Path

TARGET = Path("tests/infrastructure/test_universal_cross_asset_conformance_final_owner_r62n_guards.py")
text = TARGET.read_text(encoding="utf-8")

helper_anchor = "def _r62n_process_try(\n"
helper = '''def _r62n_process_known_trystar_handlers(
    raised_outcomes: list[_r62m._R62MOutcome],
    handlers: list[ast.ExceptHandler],
    *,
    top_index: int,
    timeline: dict[int, list[_r62l._R62LAuthorityBindings]],
    observations: dict[
        _r62k._R62KOwner,
        list[_r62l._R62LAuthorityBindings],
    ],
    precision_lost: list[bool],
) -> list[_r62m._R62MOutcome] | None:
    completed: list[_r62m._R62MOutcome] = []
    for raised in raised_outcomes:
        group_members = _r62n_exception_group_members(raised.state)
        if group_members is None:
            return None
        paths: list[
            tuple[
                _r62l._R62LState,
                frozenset[str],
                tuple[str, ...],
            ]
        ] = [(_r62n_copy_state(raised.state), group_members, ())]

        for handler in handlers:
            next_paths: list[
                tuple[
                    _r62l._R62LState,
                    frozenset[str],
                    tuple[str, ...],
                ]
            ] = []
            for current_state, remaining_members, pending_exceptions in paths:
                if not remaining_members:
                    next_paths.append(
                        (current_state, remaining_members, pending_exceptions)
                    )
                    continue

                matches = {
                    member: _r62n_handler_match(
                        member,
                        handler.type,
                        current_state[0],
                    )
                    for member in remaining_members
                }
                if any(match is None for match in matches.values()):
                    return None
                matched_members = frozenset(
                    member
                    for member, match in matches.items()
                    if match is True
                )
                if not matched_members:
                    next_paths.append(
                        (current_state, remaining_members, pending_exceptions)
                    )
                    continue

                remaining_after = remaining_members - matched_members
                handler_state = _r62n_copy_state(current_state)
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

                for handler_outcome in handler_outcomes:
                    next_pending = pending_exceptions
                    if handler_outcome.kind == "raise":
                        exception_name = _r62n_exception_name(
                            handler_outcome.state
                        )
                        if exception_name is None:
                            return None
                        next_pending = (*pending_exceptions, exception_name)
                    elif handler_outcome.kind != "normal":
                        return None

                    next_state = _r62n_copy_state(handler_outcome.state)
                    next_state[0].pop(_R62N_EXCEPTION_TAG, None)
                    if remaining_after:
                        _r62n_set_exception_tag(
                            next_state,
                            None,
                            group_members=remaining_after,
                        )
                    next_paths.append(
                        (next_state, remaining_after, next_pending)
                    )
            paths = next_paths

        for final_state, remaining_members, pending_exceptions in paths:
            result_state = _r62n_copy_state(final_state)
            result_state[0].pop(_R62N_EXCEPTION_TAG, None)
            if pending_exceptions and remaining_members:
                return None
            if len(pending_exceptions) == 1:
                _r62n_set_exception_tag(
                    result_state,
                    pending_exceptions[0],
                )
                completed.append(
                    _r62m._R62MOutcome("raise", result_state)
                )
            elif pending_exceptions:
                _r62n_set_exception_tag(result_state, None)
                completed.append(
                    _r62m._R62MOutcome("raise", result_state)
                )
            elif remaining_members:
                _r62n_set_exception_tag(
                    result_state,
                    None,
                    group_members=remaining_members,
                )
                completed.append(
                    _r62m._R62MOutcome("raise", result_state)
                )
            else:
                completed.append(
                    _r62m._R62MOutcome("normal", result_state)
                )
    return _r62m._r62m_bound_outcomes(completed)


'''
if "def _r62n_process_known_trystar_handlers(" not in text:
    if helper_anchor not in text:
        raise SystemExit("process_try helper anchor missing")
    text = text.replace(helper_anchor, helper + helper_anchor, 1)

old = '''    unhandled = [item for item in body if item.kind == "raise"]
    handled: list[_r62m._R62MOutcome] = []

    for handler in node.handlers:
'''
new = '''    unhandled = [item for item in body if item.kind == "raise"]
    if isinstance(node, ast.TryStar):
        known_trystar = _r62n_process_known_trystar_handlers(
            unhandled,
            node.handlers,
            top_index=top_index,
            timeline=timeline,
            observations=observations,
            precision_lost=precision_lost,
        )
        if known_trystar is not None:
            combined = _r62m._r62m_bound_outcomes(
                [*successful, *propagated, *known_trystar]
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

    handled: list[_r62m._R62MOutcome] = []

    for handler in node.handlers:
'''
if new not in text:
    if text.count(old) != 1:
        raise SystemExit("process_try insertion anchor mismatch")
    text = text.replace(old, new, 1)

regression_name = "test_r62n_trystar_pending_new_exception_observes_later_handler_state"
if regression_name not in text:
    text += '''


def test_r62n_trystar_pending_new_exception_observes_later_handler_state() -> None:
    safe_finally = """\\
b = eval
try:
    try:
        raise ExceptionGroup("eg", [AttributeError("a"), ValueError("v")])
    except* AttributeError:
        b = eval
        raise TypeError("new")
    except* ValueError:
        b = len
    finally:
        result = b("abc")
except TypeError:
    pass
"""
    dangerous_finally = """\\
b = len
try:
    try:
        raise ExceptionGroup("eg", [AttributeError("a"), ValueError("v")])
    except* AttributeError:
        b = len
        raise TypeError("new")
    except* ValueError:
        b = eval
    finally:
        result = b("1+1")
except TypeError:
    pass
"""
    unreachable_successor = """\\
b = eval
try:
    try:
        raise ExceptionGroup("eg", [AttributeError("a"), ValueError("v")])
    except* AttributeError:
        b = eval
        raise TypeError("new")
    except* ValueError:
        b = len
    result = b("1+1")
except TypeError:
    result = 3
"""
    assert _runtime_result(safe_finally) == 3
    assert _runtime_result(dangerous_finally) == 2
    assert _runtime_result(unreachable_successor) == 3
    safe_markers = _r62n_dynamic_execution_markers_from_source(safe_finally)
    dangerous_markers = _r62n_dynamic_execution_markers_from_source(
        dangerous_finally
    )
    unreachable_markers = _r62n_dynamic_execution_markers_from_source(
        unreachable_successor
    )
    assert "call:11" not in safe_markers
    assert "call:11" in dangerous_markers
    assert "call:11" not in unreachable_markers
'''

TARGET.write_text(text, encoding="utf-8")

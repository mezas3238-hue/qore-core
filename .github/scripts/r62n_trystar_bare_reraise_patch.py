from __future__ import annotations

from pathlib import Path

TARGET = Path("tests/infrastructure/test_universal_cross_asset_conformance_final_owner_r62n_guards.py")
text = TARGET.read_text(encoding="utf-8")

old_raise = '''    if isinstance(node, ast.Raise):
        working = _r62n_copy_state(state)
        exception_name = _r62n_static_exception_name(node.exc, working[0])
        group_members = _r62n_static_exception_group_members(
            node.exc,
            working[0],
        )
'''
new_raise = '''    if isinstance(node, ast.Raise):
        working = _r62n_copy_state(state)
        if node.exc is None:
            return [_r62m._R62MOutcome("raise", working)]
        exception_name = _r62n_static_exception_name(node.exc, working[0])
        group_members = _r62n_static_exception_group_members(
            node.exc,
            working[0],
        )
'''
if new_raise not in text:
    if text.count(old_raise) != 1:
        raise SystemExit("bare raise anchor mismatch")
    text = text.replace(old_raise, new_raise, 1)

old_paths = '''        paths: list[
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
'''
new_paths = '''        paths: list[
            tuple[
                _r62l._R62LState,
                frozenset[str],
                tuple[str, ...],
                frozenset[str],
            ]
        ] = [(_r62n_copy_state(raised.state), group_members, (), frozenset())]

        for handler in handlers:
            next_paths: list[
                tuple[
                    _r62l._R62LState,
                    frozenset[str],
                    tuple[str, ...],
                    frozenset[str],
                ]
            ] = []
            for (
                current_state,
                remaining_members,
                pending_exceptions,
                pending_group_members,
            ) in paths:
'''
if new_paths not in text:
    if text.count(old_paths) != 1:
        raise SystemExit("path state anchor mismatch")
    text = text.replace(old_paths, new_paths, 1)

old_empty = '''                    next_paths.append(
                        (current_state, remaining_members, pending_exceptions)
                    )
'''
new_empty = '''                    next_paths.append(
                        (
                            current_state,
                            remaining_members,
                            pending_exceptions,
                            pending_group_members,
                        )
                    )
'''
if text.count(old_empty) != 2:
    raise SystemExit(f"expected two carry-forward anchors, got {text.count(old_empty)}")
text = text.replace(old_empty, new_empty, 2)

old_handler_state = '''                handler_state = _r62n_copy_state(current_state)
                handler_state[0].pop(_R62N_EXCEPTION_TAG, None)
'''
new_handler_state = '''                handler_state = _r62n_copy_state(current_state)
                _r62n_set_exception_tag(
                    handler_state,
                    None,
                    group_members=matched_members,
                )
'''
if new_handler_state not in text:
    if text.count(old_handler_state) < 1:
        raise SystemExit("known TryStar handler state anchor missing")
    text = text.replace(old_handler_state, new_handler_state, 1)

old_outcomes = '''                for handler_outcome in handler_outcomes:
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
'''
new_outcomes = '''                for handler_outcome in handler_outcomes:
                    next_pending = pending_exceptions
                    next_pending_group_members = pending_group_members
                    if handler_outcome.kind == "raise":
                        reraised_members = _r62n_exception_group_members(
                            handler_outcome.state
                        )
                        if reraised_members is not None:
                            next_pending_group_members = (
                                pending_group_members | reraised_members
                            )
                        else:
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
                        (
                            next_state,
                            remaining_after,
                            next_pending,
                            next_pending_group_members,
                        )
                    )
            paths = next_paths

        for (
            final_state,
            remaining_members,
            pending_exceptions,
            pending_group_members,
        ) in paths:
            result_state = _r62n_copy_state(final_state)
            result_state[0].pop(_R62N_EXCEPTION_TAG, None)
            combined_group_members = pending_group_members | remaining_members
            if pending_exceptions and combined_group_members:
                return None
            if len(pending_exceptions) == 1:
'''
if new_outcomes not in text:
    if text.count(old_outcomes) != 1:
        raise SystemExit("handler outcome anchor mismatch")
    text = text.replace(old_outcomes, new_outcomes, 1)

old_final_group = '''            elif remaining_members:
                _r62n_set_exception_tag(
                    result_state,
                    None,
                    group_members=remaining_members,
                )
'''
new_final_group = '''            elif combined_group_members:
                _r62n_set_exception_tag(
                    result_state,
                    None,
                    group_members=combined_group_members,
                )
'''
if new_final_group not in text:
    if text.count(old_final_group) != 1:
        raise SystemExit("final group anchor mismatch")
    text = text.replace(old_final_group, new_final_group, 1)

regression = "test_r62n_trystar_bare_reraise_observes_later_handler_state"
if regression not in text:
    text += '''


def test_r62n_trystar_bare_reraise_observes_later_handler_state() -> None:
    safe = """\\
b = eval
try:
    try:
        raise ExceptionGroup("eg", [AttributeError("a"), ValueError("v")])
    except* AttributeError:
        b = eval
        raise
    except* ValueError:
        b = len
except ExceptionGroup:
    result = b("abc")
"""
    dangerous = """\\
b = len
try:
    try:
        raise ExceptionGroup("eg", [AttributeError("a"), ValueError("v")])
    except* AttributeError:
        b = len
        raise
    except* ValueError:
        b = eval
except ExceptionGroup:
    result = b("1+1")
"""
    assert _runtime_result(safe) == 3
    assert _runtime_result(dangerous) == 2
    safe_markers = _r62n_dynamic_execution_markers_from_source(safe)
    dangerous_markers = _r62n_dynamic_execution_markers_from_source(dangerous)
    assert "call:11" not in safe_markers
    assert "call:11" in dangerous_markers
'''

TARGET.write_text(text, encoding="utf-8")

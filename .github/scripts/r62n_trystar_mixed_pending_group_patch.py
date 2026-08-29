from __future__ import annotations

from pathlib import Path

TARGET = Path("tests/infrastructure/test_universal_cross_asset_conformance_final_owner_r62n_guards.py")
text = TARGET.read_text(encoding="utf-8")

old = '''            combined_group_members = pending_group_members | remaining_members
            if pending_exceptions and combined_group_members:
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
            elif combined_group_members:
                _r62n_set_exception_tag(
                    result_state,
                    None,
                    group_members=combined_group_members,
                )
                completed.append(
                    _r62m._R62MOutcome("raise", result_state)
                )
            else:
                completed.append(
                    _r62m._R62MOutcome("normal", result_state)
                )
'''
new = '''            combined_group_members = pending_group_members | remaining_members
            combined_exception_names = frozenset(
                (*pending_exceptions, *combined_group_members)
            )
            if len(pending_exceptions) == 1 and not combined_group_members:
                _r62n_set_exception_tag(
                    result_state,
                    pending_exceptions[0],
                )
                completed.append(
                    _r62m._R62MOutcome("raise", result_state)
                )
            elif combined_exception_names:
                exception_classes = [
                    _r62n_builtin_exception_class(name)
                    for name in combined_exception_names
                ]
                if any(item is None for item in exception_classes):
                    return None
                group_name = (
                    "ExceptionGroup"
                    if all(
                        issubclass(item, Exception)
                        for item in exception_classes
                        if item is not None
                    )
                    else "BaseExceptionGroup"
                )
                _r62n_set_exception_tag(
                    result_state,
                    group_name,
                    group_members=combined_exception_names,
                )
                completed.append(
                    _r62m._R62MOutcome("raise", result_state)
                )
            else:
                completed.append(
                    _r62m._R62MOutcome("normal", result_state)
                )
'''
if text.count(old) != 1:
    raise SystemExit(f"mixed pending finalization anchor mismatch: {text.count(old)}")
text = text.replace(old, new, 1)

name = "test_r62n_trystar_mixed_reraise_and_new_exception_uses_final_handler_state"
if name not in text:
    text += '''


def test_r62n_trystar_mixed_reraise_and_new_exception_uses_final_handler_state() -> None:
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
        raise TypeError("new")
except BaseExceptionGroup:
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
        raise TypeError("new")
except BaseExceptionGroup:
    result = b("1+1")
"""
    assert _runtime_result(safe) == 3
    assert _runtime_result(dangerous) == 2
    safe_markers = _r62n_dynamic_execution_markers_from_source(safe)
    dangerous_markers = _r62n_dynamic_execution_markers_from_source(dangerous)
    assert "call:12" not in safe_markers
    assert "call:12" in dangerous_markers


def test_r62n_trystar_mixed_pending_finally_uses_completed_handler_state() -> None:
    safe = """\\
b = eval
try:
    raise ExceptionGroup("eg", [AttributeError("a"), ValueError("v")])
except* AttributeError:
    b = eval
    raise
except* ValueError:
    b = len
    raise TypeError("new")
finally:
    result = b("abc")
"""
    dangerous = """\\
b = len
try:
    raise ExceptionGroup("eg", [AttributeError("a"), ValueError("v")])
except* AttributeError:
    b = len
    raise
except* ValueError:
    b = eval
    raise TypeError("new")
finally:
    result = b("1+1")
"""
    for source, expected, marker_present in (
        (safe, 3, False),
        (dangerous, 2, True),
    ):
        namespace: dict[str, object] = {}
        try:
            exec(compile(source, "<r62n-mixed-finally>", "exec", dont_inherit=True), namespace)
        except BaseExceptionGroup:
            pass
        assert namespace["result"] == expected
        markers = _r62n_dynamic_execution_markers_from_source(source)
        assert ("call:11" in markers) is marker_present
'''

TARGET.write_text(text, encoding="utf-8")

from pathlib import Path

path = Path("tests/infrastructure/test_universal_cross_asset_conformance_final_owner_r62n_guards.py")
text = path.read_text(encoding="utf-8")
old_helper = '''def _r62n_exception_group_members(
    state: _r62l._R62LState,
) -> frozenset[str] | None:
    value = state[0].get(_R62N_EXCEPTION_TAG)
    if value is None or value == _UNKNOWN:
        return None
    members = frozenset(
        atom.text
        for atom in value
        if (
            atom.kind == _R62N_EXCEPTION_GROUP_MEMBER_KIND
            and atom.text is not None
        )
    )
    if not members and any(
        atom.kind == _R62N_EXCEPTION_KIND and atom.text is not None
        for atom in value
    ):
        return None
    return members
'''
new_helper = '''def _r62n_exception_group_members(
    state: _r62l._R62LState,
) -> frozenset[str] | None:
    value = state[0].get(_R62N_EXCEPTION_TAG)
    if value is None or value == _UNKNOWN:
        return None
    members = frozenset(
        atom.text
        for atom in value
        if (
            atom.kind == _R62N_EXCEPTION_GROUP_MEMBER_KIND
            and atom.text is not None
        )
    )
    if members:
        return members
    exception_name = _r62n_exception_name(state)
    if (
        exception_name is not None
        and exception_name not in {"ExceptionGroup", "BaseExceptionGroup"}
    ):
        return frozenset({exception_name})
    return members
'''
if old_helper not in text:
    raise SystemExit("helper anchor mismatch")
text = text.replace(old_helper, new_helper, 1)

old_start = '''    completed: list[_r62m._R62MOutcome] = []
    for raised in raised_outcomes:
        group_members = _r62n_exception_group_members(raised.state)
        if group_members is None:
            return None
        paths: list[
'''
new_start = '''    completed: list[_r62m._R62MOutcome] = []
    for raised in raised_outcomes:
        group_members = _r62n_exception_group_members(raised.state)
        if group_members is None:
            return None
        tagged_value = raised.state[0].get(_R62N_EXCEPTION_TAG)
        has_group_member_tag = bool(
            tagged_value is not None
            and tagged_value != _UNKNOWN
            and any(
                atom.kind == _R62N_EXCEPTION_GROUP_MEMBER_KIND
                for atom in tagged_value
            )
        )
        plain_input_name = (
            _r62n_exception_name(raised.state)
            if not has_group_member_tag
            else None
        )
        paths: list[
'''
if old_start not in text:
    raise SystemExit("processor start anchor mismatch")
text = text.replace(old_start, new_start, 1)

old_final = '''            combined_group_members = pending_group_members | remaining_members
            combined_exception_names = frozenset(
                (*pending_exceptions, *combined_group_members)
            )
            if len(pending_exceptions) == 1 and not combined_group_members:
'''
new_final = '''            combined_group_members = pending_group_members | remaining_members
            combined_exception_names = frozenset(
                (*pending_exceptions, *combined_group_members)
            )
            if (
                plain_input_name is not None
                and remaining_members == frozenset({plain_input_name})
                and not pending_exceptions
                and not pending_group_members
            ):
                _r62n_set_exception_tag(result_state, plain_input_name)
                completed.append(_r62m._R62MOutcome("raise", result_state))
                continue
            if len(pending_exceptions) == 1 and not combined_group_members:
'''
if old_final not in text:
    raise SystemExit("processor final anchor mismatch")
text = text.replace(old_final, new_final, 1)

marker = "def test_r62n_trystar_plain_matching_finally_uses_handler_state() -> None:"
if marker not in text:
    text += '''\n\n
def test_r62n_trystar_plain_matching_finally_uses_handler_state() -> None:
    safe = """\\
b = eval
try:
    raise ValueError("v")
except* ValueError:
    b = len
finally:
    result = b("abc")
"""
    dangerous = """\\
b = len
try:
    raise ValueError("v")
except* ValueError:
    b = eval
finally:
    result = b("1+1")
"""
    assert _runtime_result(safe) == 3
    assert _runtime_result(dangerous) == 2
    safe_markers = _r62n_dynamic_execution_markers_from_source(safe)
    dangerous_markers = _r62n_dynamic_execution_markers_from_source(dangerous)
    assert "call:7" not in safe_markers
    assert "call:7" in dangerous_markers
'''
path.write_text(text, encoding="utf-8")

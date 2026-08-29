from pathlib import Path

path = Path("tests/infrastructure/test_universal_cross_asset_conformance_final_owner_r62n_guards.py")
text = path.read_text(encoding="utf-8")
old = '''def _r62n_exception_group_members(
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
'''
new = '''def _r62n_exception_group_members(
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
if old not in text:
    raise SystemExit("exception-group helper anchor mismatch")
text = text.replace(old, new, 1)
marker = "def test_r62n_trystar_plain_unmatched_exception_reaches_outer_handler() -> None:"
if marker not in text:
    text += '''\n\n
def test_r62n_trystar_plain_unmatched_exception_reaches_outer_handler() -> None:
    dangerous = """\\
b = eval
try:
    try:
        raise ValueError("v")
    except* TypeError:
        pass
except ValueError:
    result = b("1+1")
"""
    safe = """\\
b = len
try:
    try:
        raise ValueError("v")
    except* TypeError:
        pass
except ValueError:
    result = b("abc")
"""
    assert _runtime_result(dangerous) == 2
    assert _runtime_result(safe) == 3
    dangerous_markers = _r62n_dynamic_execution_markers_from_source(dangerous)
    safe_markers = _r62n_dynamic_execution_markers_from_source(safe)
    assert "call:8" in dangerous_markers
    assert "call:8" not in safe_markers


def test_r62n_trystar_plain_matching_exception_preserves_successor_state() -> None:
    safe = """\\
b = eval
try:
    raise ValueError("v")
except* ValueError:
    b = len
result = b("abc")
"""
    dangerous = """\\
b = len
try:
    raise ValueError("v")
except* ValueError:
    b = eval
result = b("1+1")
"""
    assert _runtime_result(safe) == 3
    assert _runtime_result(dangerous) == 2
    safe_markers = _r62n_dynamic_execution_markers_from_source(safe)
    dangerous_markers = _r62n_dynamic_execution_markers_from_source(dangerous)
    assert "call:6" not in safe_markers
    assert "call:6" in dangerous_markers


def test_r62n_trystar_plain_bare_reraise_reaches_outer_handler() -> None:
    dangerous = """\\
b = len
try:
    try:
        raise ValueError("v")
    except* ValueError:
        b = eval
        raise
except ValueError:
    result = b("1+1")
"""
    safe = """\\
b = eval
try:
    try:
        raise ValueError("v")
    except* ValueError:
        b = len
        raise
except ValueError:
    result = b("abc")
"""
    assert _runtime_result(dangerous) == 2
    assert _runtime_result(safe) == 3
    dangerous_markers = _r62n_dynamic_execution_markers_from_source(dangerous)
    safe_markers = _r62n_dynamic_execution_markers_from_source(safe)
    assert "call:9" in dangerous_markers
    assert "call:9" not in safe_markers
'''
path.write_text(text, encoding="utf-8")

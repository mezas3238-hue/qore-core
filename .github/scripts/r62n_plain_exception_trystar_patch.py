from pathlib import Path

path = Path('tests/infrastructure/test_universal_cross_asset_conformance_final_owner_r62n_guards.py')
text = path.read_text(encoding='utf-8')
start_marker = 'def _r62n_exception_group_members(\n'
end_marker = '\n\ndef _r62n_handler_match(\n'
start = text.find(start_marker)
end = text.find(end_marker, start)
if start < 0 or end < 0:
    raise SystemExit('helper boundary mismatch')
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
    if members:
        return members
    if any(atom.kind == _R62N_EXCEPTION_KIND for atom in value):
        return None
    return frozenset()
'''
text = text[:start] + new + text[end:]
regression = '''\n\ndef test_r62n_plain_exception_unmatched_by_trystar_propagates_unchanged() -> None:
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
        b = eval
except ValueError:
    result = b("abc")
"""
    assert _runtime_result(dangerous) == 2
    assert _runtime_result(safe) == 3
    dangerous_markers = _r62n_dynamic_execution_markers_from_source(dangerous)
    safe_markers = _r62n_dynamic_execution_markers_from_source(safe)
    assert "call:7" in dangerous_markers
    assert "call:8" not in safe_markers
'''
if 'test_r62n_plain_exception_unmatched_by_trystar_propagates_unchanged' in text:
    raise SystemExit('regression already present')
text += regression
path.write_text(text, encoding='utf-8')

from pathlib import Path

path = Path('tests/infrastructure/test_universal_cross_asset_conformance_final_owner_r62n_guards.py')
text = path.read_text(encoding='utf-8')
old = '''def _r62n_exception_group_members(\n    state: _r62l._R62LState,\n) -> frozenset[str] | None:\n    value = state[0].get(_R62N_EXCEPTION_TAG)\n    if value is None or value == _UNKNOWN:\n        return None\n    return frozenset(\n        atom.text\n        for atom in value\n        if (\n            atom.kind == _R62N_EXCEPTION_GROUP_MEMBER_KIND\n            and atom.text is not None\n        )\n    )\n'''
new = '''def _r62n_exception_group_members(\n    state: _r62l._R62LState,\n) -> frozenset[str] | None:\n    value = state[0].get(_R62N_EXCEPTION_TAG)\n    if value is None or value == _UNKNOWN:\n        return None\n    members = frozenset(\n        atom.text\n        for atom in value\n        if (\n            atom.kind == _R62N_EXCEPTION_GROUP_MEMBER_KIND\n            and atom.text is not None\n        )\n    )\n    if members:\n        return members\n    if any(atom.kind == _R62N_EXCEPTION_KIND for atom in value):\n        return None\n    return frozenset()\n'''
if old not in text:
    raise SystemExit('helper anchor mismatch')
text = text.replace(old, new, 1)
regression = '''\n\ndef test_r62n_plain_exception_unmatched_by_trystar_propagates_unchanged() -> None:\n    dangerous = \"\"\"\\\nb = eval\ntry:\n    try:\n        raise ValueError(\"v\")\n    except* TypeError:\n        pass\nexcept ValueError:\n    result = b(\"1+1\")\n\"\"\"\n    safe = \"\"\"\\\nb = len\ntry:\n    try:\n        raise ValueError(\"v\")\n    except* TypeError:\n        b = eval\nexcept ValueError:\n    result = b(\"abc\")\n\"\"\"\n    assert _runtime_result(dangerous) == 2\n    assert _runtime_result(safe) == 3\n    dangerous_markers = _r62n_dynamic_execution_markers_from_source(dangerous)\n    safe_markers = _r62n_dynamic_execution_markers_from_source(safe)\n    assert \"call:7\" in dangerous_markers\n    assert \"call:8\" not in safe_markers\n'''
if 'test_r62n_plain_exception_unmatched_by_trystar_propagates_unchanged' in text:
    raise SystemExit('regression already present')
text += regression
path.write_text(text, encoding='utf-8')

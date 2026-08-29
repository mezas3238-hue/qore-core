from __future__ import annotations

from pathlib import Path

TARGET = Path("tests/infrastructure/test_universal_cross_asset_conformance_final_owner_r62n_guards.py")
text = TARGET.read_text(encoding="utf-8")

old_helper_anchor = '''def _r62n_namespace_from_states(\n'''
new_helper = '''def _r62n_contains_nested_trystar(node: ast.AST) -> bool:\n    if isinstance(\n        node,\n        (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda, ast.ClassDef),\n    ):\n        return False\n    if isinstance(node, ast.TryStar):\n        return True\n    return any(\n        _r62n_contains_nested_trystar(child)\n        for child in ast.iter_child_nodes(node)\n    )\n\n\n'''
if "def _r62n_contains_nested_trystar(" not in text:
    if text.count(old_helper_anchor) != 1:
        raise SystemExit("nested TryStar helper anchor mismatch")
    text = text.replace(old_helper_anchor, new_helper + old_helper_anchor, 1)

old_guard = '''    if isinstance(node, ast.Try) and not any(\n        _r62n_contains_runtime_unknown_star(statement)\n        for statement in node.body\n    ):\n        return\n'''
new_guard = '''    if isinstance(node, ast.Try) and not any(\n        _r62n_contains_runtime_unknown_star(statement)\n        or _r62n_contains_nested_trystar(statement)\n        for statement in node.body\n    ):\n        return\n'''
if new_guard not in text:
    if text.count(old_guard) != 1:
        raise SystemExit("outer Try activation guard mismatch")
    text = text.replace(old_guard, new_guard, 1)

regression_name = "test_r62n_nested_trystar_new_handler_exception_reaches_outer_handler"
if regression_name not in text:
    text += '''\n\ndef test_r62n_nested_trystar_new_handler_exception_reaches_outer_handler() -> None:\n    dangerous = """\\\nb = len\ntry:\n    try:\n        raise ExceptionGroup("eg", [AttributeError("a")])\n    except* AttributeError:\n        b = eval\n        raise ValueError("new")\n    except* ValueError:\n        b = len\nexcept ValueError:\n    result = b("1+1")\n"""\n    safe = """\\\nb = eval\ntry:\n    try:\n        raise ExceptionGroup("eg", [AttributeError("a")])\n    except* AttributeError:\n        b = len\n        raise ValueError("new")\n    except* ValueError:\n        b = eval\nexcept ValueError:\n    result = b("abc")\n"""\n    assert _runtime_result(dangerous) == 2\n    assert _runtime_result(safe) == 3\n    assert _r62n_dynamic_execution_markers_from_source(dangerous)\n    assert _r62n_dynamic_execution_markers_from_source(safe) == ()\n'''

TARGET.write_text(text, encoding="utf-8")

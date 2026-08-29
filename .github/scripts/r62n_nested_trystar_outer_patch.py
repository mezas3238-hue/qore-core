from __future__ import annotations

from pathlib import Path

TARGET = Path("tests/infrastructure/test_universal_cross_asset_conformance_final_owner_r62n_guards.py")
text = TARGET.read_text(encoding="utf-8")

old_helper_anchor = "def _r62n_namespace_from_states(\n"
new_helper = '''def _r62n_contains_nested_trystar(node: ast.AST) -> bool:
    if isinstance(
        node,
        (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda, ast.ClassDef),
    ):
        return False
    if isinstance(node, ast.TryStar):
        return True
    return any(
        _r62n_contains_nested_trystar(child)
        for child in ast.iter_child_nodes(node)
    )


'''
if "def _r62n_contains_nested_trystar(" not in text:
    if old_helper_anchor not in text:
        raise SystemExit("nested TryStar helper anchor missing")
    text = text.replace(old_helper_anchor, new_helper + old_helper_anchor, 1)

old_guard_term = "            _r62n_contains_runtime_unknown_star(statement)\n            for statement in node.body\n"
new_guard_term = "            _r62n_contains_runtime_unknown_star(statement)\n            or _r62n_contains_nested_trystar(statement)\n            for statement in node.body\n"
if new_guard_term not in text:
    occurrences = text.count(old_guard_term)
    if occurrences < 1:
        raise SystemExit("outer Try activation term missing")
    text = text.replace(old_guard_term, new_guard_term, 1)

regression_name = "test_r62n_nested_trystar_new_handler_exception_reaches_outer_handler"
if regression_name not in text:
    text += '''

def test_r62n_nested_trystar_new_handler_exception_reaches_outer_handler() -> None:
    dangerous = """\\
b = len
try:
    try:
        raise ExceptionGroup("eg", [AttributeError("a")])
    except* AttributeError:
        b = eval
        raise ValueError("new")
    except* ValueError:
        b = len
except ValueError:
    result = b("1+1")
"""
    safe = """\\
b = eval
try:
    try:
        raise ExceptionGroup("eg", [AttributeError("a")])
    except* AttributeError:
        b = len
        raise ValueError("new")
    except* ValueError:
        b = eval
except ValueError:
    result = b("abc")
"""
    assert _runtime_result(dangerous) == 2
    assert _runtime_result(safe) == 3
    assert _r62n_dynamic_execution_markers_from_source(dangerous)
    assert _r62n_dynamic_execution_markers_from_source(safe) == ()
'''

TARGET.write_text(text, encoding="utf-8")

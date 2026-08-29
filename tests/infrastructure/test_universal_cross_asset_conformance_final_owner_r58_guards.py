from __future__ import annotations

import sys

import test_universal_cross_asset_conformance_final_owner_r57_guards as _r57
from test_universal_cross_asset_conformance_final_owner_r12_guards import (
    _FULL_CLOSURE_ORACLE_PATH,
    _owner_paths,
)


def _r58_dynamic_execution_markers_from_source(source: str) -> tuple[str, ...]:
    # R57 is authoritative for the Python 3.12 QORE gate.  R58 adds direct
    # runtime certification of the version-sensitive locals()/vars() behavior
    # instead of introducing another scanner override.
    return _r57._r57_dynamic_execution_markers_from_source(source)


def test_r58_python312_module_comprehensions_preserve_r57_module_vars() -> None:
    sources = (
        'values = [vars()["__builtins__"].__dict__["eval"]("1+1") for _ in (0,)]\n',
        'values = {vars()["__builtins__"].__dict__["eval"]("1+1") for _ in (0,)}\n',
        'values = {_: vars()["__builtins__"].__dict__["eval"]("1+1") for _ in (0,)}\n',
    )

    for source in sources:
        assert _r58_dynamic_execution_markers_from_source(source) == ("call:1",)


def test_r58_runtime_records_version_sensitive_module_key_visibility() -> None:
    sources = (
        'visible = ["__builtins__" in vars() for _ in (0,)]\n',
        'visible = {"__builtins__" in vars() for _ in (0,)}\n',
        'visible = {_: "__builtins__" in vars() for _ in (0,)}\n',
    )
    expected = sys.version_info[:2] == (3, 12)

    namespace: dict[str, object] = {}
    for source in sources:
        namespace.clear()
        exec(source, namespace)
        visible = namespace["visible"]
        if isinstance(visible, dict):
            assert tuple(visible.values()) == (expected,)
        elif isinstance(visible, set):
            assert visible == {expected}
        else:
            assert visible == [expected]


def test_r58_generator_body_remains_nested_and_leftmost_iterable_outer() -> None:
    body_source = (
        'values = (vars()["__builtins__"].__dict__["eval"]("1+1") '
        'for _ in (0,))\n'
    )
    iterable_source = (
        'values = (item for item in '
        '(vars()["__builtins__"].__dict__["eval"]("1+1"),))\n'
    )

    assert _r58_dynamic_execution_markers_from_source(body_source) == ()
    assert _r58_dynamic_execution_markers_from_source(iterable_source) == ("call:1",)


def test_r58_function_inlined_comprehension_stays_non_module_for_vars() -> None:
    source = """\
def run():
    local_value = 1
    return [vars().get("__builtins__", local_value) for _ in (0,)]
"""

    assert _r58_dynamic_execution_markers_from_source(source) == ()


def test_r58_true_module_vars_and_definition_defaults_remain_detectable() -> None:
    sources = (
        'vars()["__builtins__"].__dict__["eval"]("1+1")\n',
        'def f(value=vars()["__builtins__"].__dict__["eval"]("1+1")):\n    return value\n',
        'factory = lambda value=vars()["__builtins__"].__dict__["eval"]("1+1"): value\n',
    )

    for source in sources:
        assert "call:1" in _r58_dynamic_execution_markers_from_source(source)


def test_r58_r56_inherited_global_and_lambda_scope_fixes_remain_authoritative() -> None:
    source = """\
def run():
    global eval
    result = eval("1+1")
    eval = lambda value: value
    return result

factory = lambda value=eval("2+2"): value
"""

    markers = _r58_dynamic_execution_markers_from_source(source)
    assert "call:3" in markers
    assert "call:7" in markers


def test_r58_r55_fallback_fixes_remain_authoritative() -> None:
    source = """\
flag = True
mapping = {} if flag else {"missing": len}
mapping.get("missing", eval)("1+1")

class Safe:
    pass
getattr(Safe, "missing", exec)("pass")
"""

    markers = _r58_dynamic_execution_markers_from_source(source)
    assert "call:3" in markers
    assert "call:7" in markers


def test_r58_complete_owner_and_oracle_surface_has_no_dynamic_execution() -> None:
    paths = (*_owner_paths(), _FULL_CLOSURE_ORACLE_PATH)

    for path in paths:
        assert _r58_dynamic_execution_markers_from_source(
            path.read_text(encoding="utf-8")
        ) == (), path

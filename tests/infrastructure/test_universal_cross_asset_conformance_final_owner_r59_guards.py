from __future__ import annotations

import test_universal_cross_asset_conformance_final_owner_r57_guards as _r57
from test_universal_cross_asset_conformance_final_owner_r12_guards import (
    _FULL_CLOSURE_ORACLE_PATH,
    _owner_paths,
)


class _R59Python312ComprehensionLocalsScanner(
    _r57._R57Python312ScopeScanner
):
    """Authoritative CPython 3.12 comprehension-scope successor.

    R58 projected the Python 3.13 PEP 667 module/class locals behavior
    backward onto the Python 3.12 Quality Gate. R57 already models the
    relevant 3.12 PEP 709 distinction correctly, so R59 deliberately
    resumes from R57 rather than inheriting the invalid R58 override.
    """


def _r59_dynamic_execution_markers_from_source(source: str) -> tuple[str, ...]:
    return _R59Python312ComprehensionLocalsScanner().scan(source)


def test_r59_module_comprehensions_include_module_vars_on_cpython312() -> None:
    sources = (
        'values = [vars()["__builtins__"].__dict__["eval"]("1+1") for _ in (0,)]\n',
        'values = {vars()["__builtins__"].__dict__["eval"]("1+1") for _ in (0,)}\n',
        'values = {_: vars()["__builtins__"].__dict__["eval"]("1+1") for _ in (0,)}\n',
    )

    for source in sources:
        assert _r59_dynamic_execution_markers_from_source(source) == ("call:1",)


def test_r59_module_comprehension_runtime_sees_builtins_on_cpython312() -> None:
    sources = (
        'visible = ["__builtins__" in vars() for _ in (0,)]\n',
        'visible = {"__builtins__" in vars() for _ in (0,)}\n',
        'visible = {_: "__builtins__" in vars() for _ in (0,)}\n',
    )

    namespace: dict[str, object] = {}
    for source in sources:
        namespace.clear()
        exec(source, namespace)
        visible = namespace["visible"]
        if isinstance(visible, dict):
            assert tuple(visible.values()) == (True,)
        elif isinstance(visible, set):
            assert visible == {True}
        else:
            assert visible == [True]


def test_r59_generator_expression_body_remains_nested() -> None:
    source = (
        'values = (vars()["__builtins__"].__dict__["eval"]("1+1") '
        'for _ in (0,))\n'
    )

    assert _r59_dynamic_execution_markers_from_source(source) == ()


def test_r59_generator_leftmost_iterable_remains_enclosing_module_scope() -> None:
    source = (
        'values = (item for item in '
        '(vars()["__builtins__"].__dict__["eval"]("1+1"),))\n'
    )

    assert _r59_dynamic_execution_markers_from_source(source) == ("call:1",)


def test_r59_function_comprehension_is_not_module_vars() -> None:
    source = """\
def run():
    local_value = 1
    return [vars().get("__builtins__", local_value) for _ in (0,)]
"""

    assert _r59_dynamic_execution_markers_from_source(source) == ()


def test_r59_class_comprehension_is_not_promoted_to_module_vars() -> None:
    source = """\
class Carrier:
    values = [vars().get("__builtins__", 1) for _ in (0,)]
"""

    assert _r59_dynamic_execution_markers_from_source(source) == ()


def test_r59_r56_scope_restoration_and_r55_fallbacks_remain_authoritative() -> None:
    source = """\
def run():
    global eval
    result = eval("1+1")
    eval = lambda value: value
    return result

factory = lambda value=eval("2+2"): value
flag = True
mapping = {} if flag else {"missing": len}
mapping.get("missing", exec)("pass")
"""

    markers = _r59_dynamic_execution_markers_from_source(source)
    assert "call:3" in markers
    assert "call:7" in markers
    assert "call:10" in markers


def test_r59_complete_owner_and_oracle_surface_has_no_dynamic_execution() -> None:
    paths = (*_owner_paths(), _FULL_CLOSURE_ORACLE_PATH)

    for path in paths:
        assert _r59_dynamic_execution_markers_from_source(
            path.read_text(encoding="utf-8")
        ) == (), path

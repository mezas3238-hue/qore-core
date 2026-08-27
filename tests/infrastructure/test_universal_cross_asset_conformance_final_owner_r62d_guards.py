from __future__ import annotations

import ast

import test_universal_cross_asset_conformance_final_owner_r62c_guards as _r62c
from test_universal_cross_asset_conformance_final_owner_r12_guards import (
    _FULL_CLOSURE_ORACLE_PATH,
    _UNKNOWN,
    _owner_paths,
    _Value,
)


class _R62DCallableDefaultEgressScanner(
    _r62c._R62CLambdaAndComputedImportlibScanner
):
    """Fail closed when a callable default captures dynamic-execution authority.

    CPython evaluates function and lambda defaults at definition time and stores
    those objects for later omitted-argument calls. A dangerous callable such as
    ``eval`` or ``importlib.import_module`` can therefore escape through a
    positional or keyword-only default even when the callable body itself only
    refers to an otherwise opaque parameter.

    Function defaults are already scanned by the inherited R12 implementation;
    retain their exact abstract values without evaluating them a second time and
    mark the definition when any captured default is sensitive. Lambda defaults
    are not scanned by R12, so scan them once in the defining environment before
    delegating to R62C's existing lambda-body capture.
    """

    def __init__(self) -> None:
        super().__init__()
        self._r62d_function_default_capture_stack: list[dict[int, _Value]] = []

    def _scan_expression(
        self,
        node: ast.AST,
        environment: dict[str, _Value],
    ) -> _Value:
        if isinstance(node, ast.Lambda):
            default_values = [
                self._scan_expression(default, environment)
                for default in node.args.defaults
            ]
            default_values.extend(
                self._scan_expression(default, environment)
                for default in node.args.kw_defaults
                if default is not None
            )
            if any(self._is_sensitive_value(value) for value in default_values):
                self._mark_binding(node.lineno)

            value = super()._scan_expression(node, environment)
        else:
            value = super()._scan_expression(node, environment)

        if self._r62d_function_default_capture_stack:
            self._r62d_function_default_capture_stack[-1][id(node)] = value
        return value

    def _scan_function(
        self,
        node: ast.FunctionDef | ast.AsyncFunctionDef,
        environment: dict[str, _Value],
    ) -> None:
        self._r62d_function_default_capture_stack.append({})
        try:
            super()._scan_function(node, environment)
            captured_values = self._r62d_function_default_capture_stack[-1]
            default_values = [
                captured_values.get(id(default), _UNKNOWN)
                for default in node.args.defaults
            ]
            default_values.extend(
                captured_values.get(id(default), _UNKNOWN)
                for default in node.args.kw_defaults
                if default is not None
            )
        finally:
            self._r62d_function_default_capture_stack.pop()

        if any(self._is_sensitive_value(value) for value in default_values):
            self._mark_binding(node.lineno)


def _r62d_dynamic_execution_markers_from_source(source: str) -> tuple[str, ...]:
    return _R62DCallableDefaultEgressScanner().scan(source)


def test_r62d_positional_lambda_default_eval_fails_closed() -> None:
    source = 'result = (lambda candidate=eval: candidate)()("1+1")\n'

    namespace: dict[str, object] = {}
    exec(source, namespace)
    assert namespace["result"] == 2
    assert _r62d_dynamic_execution_markers_from_source(source) == ("binding:1",)


def test_r62d_keyword_only_lambda_default_eval_fails_closed() -> None:
    source = 'result = (lambda *, candidate=eval: candidate)()("1+1")\n'

    namespace: dict[str, object] = {}
    exec(source, namespace)
    assert namespace["result"] == 2
    assert _r62d_dynamic_execution_markers_from_source(source) == ("binding:1",)


def test_r62d_computed_lambda_default_eval_fails_closed() -> None:
    source = """\
import builtins
result = (lambda candidate=getattr(builtins, "eval"): candidate)()("1+1")
"""

    namespace: dict[str, object] = {}
    exec(source, namespace)
    assert namespace["result"] == 2
    assert _r62d_dynamic_execution_markers_from_source(source) == ("binding:2",)


def test_r62d_safe_lambda_default_inverse_stays_clean() -> None:
    source = 'result = (lambda candidate=len: candidate)()("abc")\n'

    namespace: dict[str, object] = {}
    exec(source, namespace)
    assert namespace["result"] == 3
    assert _r62d_dynamic_execution_markers_from_source(source) == ()


def test_r62d_positional_function_default_eval_fails_closed() -> None:
    source = """\
def reveal(candidate=eval):
    return candidate
result = reveal()("1+1")
"""

    namespace: dict[str, object] = {}
    exec(source, namespace)
    assert namespace["result"] == 2
    assert _r62d_dynamic_execution_markers_from_source(source) == ("binding:1",)


def test_r62d_keyword_only_function_default_eval_fails_closed() -> None:
    source = """\
def reveal(*, candidate=eval):
    return candidate
result = reveal()("1+1")
"""

    namespace: dict[str, object] = {}
    exec(source, namespace)
    assert namespace["result"] == 2
    assert _r62d_dynamic_execution_markers_from_source(source) == ("binding:1",)


def test_r62d_computed_function_default_eval_fails_closed() -> None:
    source = """\
import builtins
def reveal(candidate=getattr(builtins, "eval")):
    return candidate
result = reveal()("1+1")
"""

    namespace: dict[str, object] = {}
    exec(source, namespace)
    assert namespace["result"] == 2
    assert _r62d_dynamic_execution_markers_from_source(source) == ("binding:2",)


def test_r62d_importlib_callable_defaults_fail_closed() -> None:
    function_source = """\
import importlib
def load(loader=importlib.import_module):
    return loader
result = load()("math")
"""
    lambda_source = """\
import importlib
result = (lambda loader=importlib.import_module: loader)()("math")
"""

    function_namespace: dict[str, object] = {}
    lambda_namespace: dict[str, object] = {}
    exec(function_source, function_namespace)
    exec(lambda_source, lambda_namespace)
    assert getattr(function_namespace["result"], "__name__", None) == "math"
    assert getattr(lambda_namespace["result"], "__name__", None) == "math"
    assert _r62d_dynamic_execution_markers_from_source(function_source) == (
        "binding:2",
    )
    assert _r62d_dynamic_execution_markers_from_source(lambda_source) == (
        "binding:2",
    )


def test_r62d_safe_function_default_inverse_stays_clean() -> None:
    source = """\
def reveal(candidate=len):
    return candidate
result = reveal()("abc")
"""

    namespace: dict[str, object] = {}
    exec(source, namespace)
    assert namespace["result"] == 3
    assert _r62d_dynamic_execution_markers_from_source(source) == ()


def test_r62d_sensitive_container_default_fails_closed() -> None:
    source = """\
def reveal(candidates=(eval,)):
    return candidates
result = reveal()[0]("1+1")
"""

    namespace: dict[str, object] = {}
    exec(source, namespace)
    assert namespace["result"] == 2
    assert _r62d_dynamic_execution_markers_from_source(source) == ("binding:1",)


def test_r62d_r62c_regressions_remain_authoritative() -> None:
    lambda_egress = '(lambda: eval)()("1+1")\n'
    importlib_getattr = """\
import importlib
getattr(importlib, "import_module")("math")
"""
    failed_star_keyword = """\
def consume(*arguments, **keywords):
    return arguments, keywords
consume(*None, candidate=eval("1+1"))
"""

    assert _r62d_dynamic_execution_markers_from_source(lambda_egress) == (
        "binding:1",
    )
    assert _r62d_dynamic_execution_markers_from_source(importlib_getattr) == (
        "call:2",
    )
    assert _r62d_dynamic_execution_markers_from_source(failed_star_keyword) == (
        "call:3",
    )


def test_r62d_complete_owner_and_oracle_surface_has_no_dynamic_execution() -> None:
    paths = (*_owner_paths(), _FULL_CLOSURE_ORACLE_PATH)

    for path in paths:
        assert _r62d_dynamic_execution_markers_from_source(
            path.read_text(encoding="utf-8")
        ) == (), path

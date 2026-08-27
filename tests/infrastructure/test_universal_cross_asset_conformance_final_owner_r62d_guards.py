from __future__ import annotations

import ast

import test_universal_cross_asset_conformance_final_owner_r62c_guards as _r62c
from test_universal_cross_asset_conformance_final_owner_r12_guards import (
    _FULL_CLOSURE_ORACLE_PATH,
    _UNKNOWN,
    _contains_kind,
    _owner_paths,
    _Value,
)


class _R62DCallableDefaultEgressScanner(
    _r62c._R62CLambdaAndComputedImportlibScanner
):
    """Fail closed when a callable default captures execution authority.

    CPython stores function and lambda default objects for later omitted-argument
    calls and also exposes those stored objects through ``__defaults__``. The
    inherited scanner chain already scans both positional and keyword-only
    defaults, but it discards their abstract values before the callable body is
    scanned with parameter names set to unknown. A dangerous callable such as
    ``eval`` or ``importlib.import_module`` can therefore escape through a
    default even when the body merely returns the parameter. The statically
    known ``importlib`` namespace is likewise sensitive when stored as a
    default, because its retained ``import_module`` capability is observable
    through ``__defaults__`` even when the body never uses the parameter.

    Retain only the abstract values already produced by inherited default
    scanning, keyed by AST node identity. No default expression is scanned a
    second time. Mark the function/lambda definition when any captured default
    is sensitive, while preserving R62C lambda-body capture and every inherited
    ordering/scope rule.
    """

    def __init__(self) -> None:
        super().__init__()
        self._r62d_default_capture_stack: list[dict[int, _Value]] = []

    def _is_sensitive_default_value(self, value: _Value) -> bool:
        return self._is_sensitive_value(value) or _contains_kind(value, "importlib")

    def _scan_expression(
        self,
        node: ast.AST,
        environment: dict[str, _Value],
    ) -> _Value:
        if isinstance(node, ast.Lambda):
            self._r62d_default_capture_stack.append({})
            try:
                value = super()._scan_expression(node, environment)
                captured_values = self._r62d_default_capture_stack[-1]
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
                self._r62d_default_capture_stack.pop()

            if any(
                self._is_sensitive_default_value(default_value)
                for default_value in default_values
            ):
                self._mark_binding(node.lineno)
        else:
            value = super()._scan_expression(node, environment)

        if self._r62d_default_capture_stack:
            self._r62d_default_capture_stack[-1][id(node)] = value
        return value

    def _scan_function(
        self,
        node: ast.FunctionDef | ast.AsyncFunctionDef,
        environment: dict[str, _Value],
    ) -> None:
        self._r62d_default_capture_stack.append({})
        try:
            super()._scan_function(node, environment)
            captured_values = self._r62d_default_capture_stack[-1]
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
            self._r62d_default_capture_stack.pop()

        if any(
            self._is_sensitive_default_value(default_value)
            for default_value in default_values
        ):
            self._mark_binding(node.lineno)


def _r62d_dynamic_execution_markers_from_source(source: str) -> tuple[str, ...]:
    return _R62DCallableDefaultEgressScanner().scan(source)


def test_r62d_predecessor_reproduces_callable_default_false_negative() -> None:
    lambda_source = '(lambda candidate=eval: candidate)()("1+1")\n'
    function_source = """\
def reveal(candidate=eval):
    return candidate
reveal()("1+1")
"""

    assert _r62c._r62c_dynamic_execution_markers_from_source(lambda_source) == ()
    assert _r62c._r62c_dynamic_execution_markers_from_source(function_source) == ()


def test_r62d_predecessor_reproduces_importlib_namespace_default_escape() -> None:
    function_source = """\
import importlib
def hold(namespace=importlib):
    return None
hold.__defaults__[0].import_module("math")
"""
    lambda_source = """\
import importlib
hold = lambda namespace=importlib: None
hold.__defaults__[0].import_module("math")
"""

    assert _r62c._r62c_dynamic_execution_markers_from_source(function_source) == ()
    assert _r62c._r62c_dynamic_execution_markers_from_source(lambda_source) == ()


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


def test_r62d_importlib_namespace_defaults_fail_closed() -> None:
    function_source = """\
import importlib
def hold(namespace=importlib):
    return None
result = hold.__defaults__[0].import_module("math")
"""
    lambda_source = """\
import importlib
hold = lambda namespace=importlib: None
result = hold.__defaults__[0].import_module("math")
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

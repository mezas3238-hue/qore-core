from __future__ import annotations

import ast
import importlib

import test_universal_cross_asset_conformance_final_owner_r12_guards as _r12
import test_universal_cross_asset_conformance_final_owner_r15_guards as _r15
import test_universal_cross_asset_conformance_final_owner_r55_guards as _r55
import test_universal_cross_asset_conformance_final_owner_r62b_guards as _r62b
from test_universal_cross_asset_conformance_final_owner_r12_guards import (
    _DANGEROUS_CALLABLE,
    _FULL_CLOSURE_ORACLE_PATH,
    _UNKNOWN,
    _Atom,
    _owner_paths,
    _static_strings,
    _Value,
)

_R62C_IMPORTLIB_NAMESPACE: _Value = frozenset(
    {
        _Atom("importlib"),
        _Atom("container-kind", "mapping"),
        _Atom(_r55._R55_PRESENT_KEY_KIND, "s:import_module"),
        _r15._selected_slot_atom("s:import_module", _Atom("dangerous")),
    }
)


class _R62CLambdaAndComputedImportlibScanner(
    _r62b._R62BExecutionEgressAndOrderingScanner
):
    """Close lambda egress and computed ``importlib`` lookup escapes.

    Preserve the inherited Lambda scope/default handling and capture only the
    abstract value it already computes for the lambda body. A sensitive body
    result is an execution-capability egress just like R62B's explicit Return
    statement, while the lambda itself remains opaque to later return-value
    interpretation.

    Represent the statically known importlib namespace as a mapping with one
    security-relevant selected slot, ``import_module``. This lets inherited
    mapping/getitem/get machinery remain authoritative while adding bounded
    support for getattr(), vars(), __dict__, aliases, and operator accessors.
    """

    def __init__(self) -> None:
        super().__init__()
        self._r62c_lambda_capture_stack: list[dict[int, _Value]] = []

    def _scan_expression(
        self,
        node: ast.AST,
        environment: dict[str, _Value],
    ) -> _Value:
        if isinstance(node, ast.Lambda):
            self._r62c_lambda_capture_stack.append({})
            try:
                value = super()._scan_expression(node, environment)
                body_value = self._r62c_lambda_capture_stack[-1].get(
                    id(node.body),
                    _UNKNOWN,
                )
            finally:
                self._r62c_lambda_capture_stack.pop()

            if self._is_sensitive_value(body_value):
                self._mark_binding(node.lineno)
            return value

        value = super()._scan_expression(node, environment)
        if self._r62c_lambda_capture_stack:
            self._r62c_lambda_capture_stack[-1][id(node)] = value
        return value

    def _scan_import(
        self,
        node: ast.Import,
        environment: dict[str, _Value],
    ) -> None:
        super()._scan_import(node, environment)
        for alias in node.names:
            if alias.name == "importlib":
                environment[alias.asname or "importlib"] = _R62C_IMPORTLIB_NAMESPACE
            elif alias.name.startswith("importlib.") and alias.asname is None:
                environment["importlib"] = _R62C_IMPORTLIB_NAMESPACE

    def _evaluate_attribute(
        self,
        node: ast.Attribute,
        environment: dict[str, _Value],
    ) -> _Value:
        if isinstance(node.value, ast.Name):
            base = environment.get(node.value.id, _UNKNOWN)
            if _r12._contains_kind(base, "importlib"):
                if node.attr == "import_module":
                    return _DANGEROUS_CALLABLE
                if node.attr == "__dict__":
                    return _R62C_IMPORTLIB_NAMESPACE
                return _UNKNOWN
        return super()._evaluate_attribute(node, environment)

    def _evaluate_special_call(
        self,
        helper: _Atom,
        arguments: list[_Value],
    ) -> _Value:
        if (
            helper.kind == "helper"
            and helper.text == "getattr"
            and len(arguments) >= 2
            and _r12._contains_kind(arguments[0], "importlib")
        ):
            attributes = _static_strings(arguments[1])
            if "import_module" in attributes:
                return _DANGEROUS_CALLABLE
            if "__dict__" in attributes:
                return _R62C_IMPORTLIB_NAMESPACE
            if attributes:
                return _UNKNOWN

        if (
            helper.kind == "helper"
            and helper.text == "vars"
            and arguments
            and _r12._contains_kind(arguments[0], "importlib")
        ):
            return _R62C_IMPORTLIB_NAMESPACE

        if (
            helper.kind == "itemgetter"
            and arguments
            and helper.text == "s:import_module"
            and _r12._contains_kind(arguments[0], "importlib")
        ):
            return _DANGEROUS_CALLABLE

        if (
            helper.kind == "attrgetter"
            and arguments
            and helper.text == "import_module"
            and _r12._contains_kind(arguments[0], "importlib")
        ):
            return _DANGEROUS_CALLABLE

        return super()._evaluate_special_call(helper, arguments)


def _r62c_dynamic_execution_markers_from_source(source: str) -> tuple[str, ...]:
    return _R62CLambdaAndComputedImportlibScanner().scan(source)


def test_r62c_lambda_return_eval_fails_closed() -> None:
    source = '(lambda: eval)()("1+1")\n'

    namespace: dict[str, object] = {}
    exec(f"result = {source}", namespace)
    assert namespace["result"] == 2
    assert _r62c_dynamic_execution_markers_from_source(source) == ("binding:1",)


def test_r62c_computed_lambda_return_eval_fails_closed() -> None:
    source = """\
import builtins
(lambda: getattr(builtins, "eval"))()("1+1")
"""

    assert _r62c_dynamic_execution_markers_from_source(source) == ("binding:2",)


def test_r62c_lambda_safe_callable_inverse_stays_clean() -> None:
    source = '(lambda: len)()("abc")\n'

    assert _r62c_dynamic_execution_markers_from_source(source) == ()


def test_r62c_getattr_importlib_import_module_fails_closed() -> None:
    source = """\
import importlib
result = getattr(importlib, "import_module")("math")
"""

    namespace: dict[str, object] = {}
    exec(source, namespace)
    assert getattr(namespace["result"], "__name__") == "math"
    assert _r62c_dynamic_execution_markers_from_source(source) == ("call:2",)


def test_r62c_getattr_importlib_alias_rebinding_fails_closed() -> None:
    source = """\
import importlib as il
loader = getattr(il, "import_module")
loader("math")
"""

    assert _r62c_dynamic_execution_markers_from_source(source) == (
        "binding:2",
        "call:3",
    )


def test_r62c_importlib_dunder_dict_lookup_fails_closed() -> None:
    source = """\
import importlib
importlib.__dict__["import_module"]("math")
"""

    assert importlib.__dict__["import_module"]("math").__name__ == "math"
    assert _r62c_dynamic_execution_markers_from_source(source) == ("call:2",)


def test_r62c_vars_importlib_lookup_fails_closed() -> None:
    source = """\
import importlib
vars(importlib)["import_module"]("math")
"""

    assert vars(importlib)["import_module"]("math").__name__ == "math"
    assert _r62c_dynamic_execution_markers_from_source(source) == ("call:2",)


def test_r62c_importlib_namespace_alias_lookup_fails_closed() -> None:
    source = """\
import importlib
namespace = vars(importlib)
loader = namespace["import_module"]
loader("math")
"""

    assert _r62c_dynamic_execution_markers_from_source(source) == (
        "binding:3",
        "call:4",
    )


def test_r62c_importlib_mapping_get_fails_closed() -> None:
    source = """\
import importlib
importlib.__dict__.get("import_module")("math")
"""

    assert _r62c_dynamic_execution_markers_from_source(source) == ("call:2",)


def test_r62c_operator_accessors_cannot_hide_import_module() -> None:
    source = """\
import importlib
import operator
operator.getitem(importlib.__dict__, "import_module")("math")
operator.itemgetter("import_module")(vars(importlib))("math")
operator.attrgetter("import_module")(importlib)("math")
"""

    markers = _r62c_dynamic_execution_markers_from_source(source)
    for line_number in (3, 4, 5):
        assert f"call:{line_number}" in markers


def test_r62c_safe_computed_importlib_inverses_stay_clean() -> None:
    sources = (
        'import importlib\nvalue = getattr(importlib, "util")\n',
        'import importlib\nvalue = importlib.__dict__["util"]\n',
        'import importlib\nvalue = vars(importlib)["util"]\n',
    )

    for source in sources:
        assert _r62c_dynamic_execution_markers_from_source(source) == ()


def test_r62c_r62b_regressions_remain_authoritative() -> None:
    failed_star_keyword = """\
def consume(*arguments, **keywords):
    return arguments, keywords
consume(*None, candidate=eval("1+1"))
"""
    direct_return = """\
def get_eval():
    return eval
get_eval()("1+1")
"""
    direct_importlib = """\
import importlib
importlib.import_module("math")
"""

    assert _r62c_dynamic_execution_markers_from_source(failed_star_keyword) == (
        "call:3",
    )
    assert _r62c_dynamic_execution_markers_from_source(direct_return) == (
        "binding:2",
    )
    assert _r62c_dynamic_execution_markers_from_source(direct_importlib) == (
        "call:2",
    )


def test_r62c_complete_owner_and_oracle_surface_has_no_dynamic_execution() -> None:
    paths = (*_owner_paths(), _FULL_CLOSURE_ORACLE_PATH)

    for path in paths:
        assert _r62c_dynamic_execution_markers_from_source(
            path.read_text(encoding="utf-8")
        ) == (), path

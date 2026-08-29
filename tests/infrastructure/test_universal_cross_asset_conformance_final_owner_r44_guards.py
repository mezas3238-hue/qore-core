from __future__ import annotations

import ast

import test_universal_cross_asset_conformance_final_owner_r35_guards as _r35
import test_universal_cross_asset_conformance_final_owner_r41_guards as _r41
from test_universal_cross_asset_conformance_final_owner_r12_guards import (
    _FULL_CLOSURE_ORACLE_PATH,
    _Atom,
    _owner_paths,
    _Value,
)


def _r44_exact_ellipsis(value: _Value) -> bool:
    return value == frozenset({_Atom(_r41._ELLIPSIS_CONSTANT_KIND)})


class _R44UnaryEllipsisFailureScanner(_r41._R41NumericStarAndMappingScanner):
    def _scan_expression(
        self,
        node: ast.AST,
        environment: dict[str, _Value],
    ) -> _Value:
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.USub, ast.UAdd)):
            if isinstance(node.operand, ast.Constant) and node.operand.value is Ellipsis:
                return _r35._FAILURE_VALUE
            if isinstance(node.operand, ast.Name):
                operand = environment.get(node.operand.id)
                if operand is not None and _r44_exact_ellipsis(operand):
                    return _r35._FAILURE_VALUE

        return super()._scan_expression(node, environment)


def _r44_dynamic_execution_markers_from_source(source: str) -> tuple[str, ...]:
    return _R44UnaryEllipsisFailureScanner().scan(source)


def test_r44_deepseek_unary_ellipsis_star_failure_stops_later_arguments() -> None:
    source = """\
def f(*args):
    pass

f(*-..., eval("1+1"))
f(*+..., exec("pass"))
missing = ...
f(*-missing, __import__("math"))
"""

    assert _r44_dynamic_execution_markers_from_source(source) == ()


def test_r44_unary_ellipsis_failure_stops_later_composite_elements() -> None:
    source = """\
a = (*-..., eval("1+1"))
b = [*+..., exec("pass")]
missing = ...
c = (*-missing, __import__("math"))
"""

    assert _r44_dynamic_execution_markers_from_source(source) == ()


def test_r44_reachable_execution_before_unary_ellipsis_failure_remains_marked() -> None:
    source = """\
def f(*args):
    pass

f(eval("1+1"), *-..., exec("pass"))
"""

    assert _r44_dynamic_execution_markers_from_source(source) == ("call:4",)


def test_r44_existing_numeric_and_bytes_star_semantics_are_preserved() -> None:
    source = """\
def f(*args):
    pass

f(*-0.0, eval("1+1"))
f(*+0j, exec("pass"))
f(*b"ab", __import__("math"))
"""

    assert _r44_dynamic_execution_markers_from_source(source) == ("call:6",)


def test_r44_complete_owner_and_oracle_surface_has_no_dynamic_execution() -> None:
    paths = (*_owner_paths(), _FULL_CLOSURE_ORACLE_PATH)

    for path in paths:
        assert _r44_dynamic_execution_markers_from_source(
            path.read_text(encoding="utf-8")
        ) == (), path

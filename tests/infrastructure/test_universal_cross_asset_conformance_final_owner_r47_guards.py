from __future__ import annotations

import ast

import test_universal_cross_asset_conformance_final_owner_r12_guards as _r12
import test_universal_cross_asset_conformance_final_owner_r15_guards as _r15
import test_universal_cross_asset_conformance_final_owner_r35_guards as _r35
import test_universal_cross_asset_conformance_final_owner_r41_guards as _r41
import test_universal_cross_asset_conformance_final_owner_r45_guards as _r45
from test_universal_cross_asset_conformance_final_owner_r12_guards import (
    _FULL_CLOSURE_ORACLE_PATH,
    _UNKNOWN,
    _contains_kind,
    _integer_value,
    _owner_paths,
    _Value,
)


def _r47_static_builtins_namespace(
    expression: ast.AST,
    environment: dict[str, _Value],
) -> bool:
    if _r45._r45_static_builtins_namespace(expression, environment):
        return True

    if (
        isinstance(expression, ast.Call)
        and len(expression.args) == 1
        and not expression.keywords
    ):
        helper: _Value = _UNKNOWN
        if isinstance(expression.func, ast.Name):
            helper = environment.get(
                expression.func.id,
                _r12._IMPLICIT_BINDINGS.get(expression.func.id, _UNKNOWN),
            )
        elif (
            isinstance(expression.func, ast.Attribute)
            and expression.func.attr == "vars"
            and _r47_static_builtins_namespace(expression.func.value, environment)
        ):
            helper = frozenset({_r12._Atom("helper", "vars")})

        return (
            _contains_kind(helper, "helper", "vars")
            and _r47_static_builtins_namespace(expression.args[0], environment)
        )

    return False


class _R47BooleanUnaryAndBuiltinsLookupScanner(
    _r45._R45BuiltinEllipsisAliasScanner
):
    def _scan_expression(
        self,
        node: ast.AST,
        environment: dict[str, _Value],
    ) -> _Value:
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.USub, ast.UAdd)):
            operand = self._scan_expression(node.operand, environment)
            if _r35._r35_failed(operand):
                return _r35._FAILURE_VALUE
            if _r45._r45_exact_ellipsis(operand):
                return _r35._FAILURE_VALUE

            if len(operand) == 1:
                atom = next(iter(operand))
                float_value = _r41._r41_float_from_atom(atom)
                if float_value is not None:
                    return _r41._r41_float_value(
                        -float_value if isinstance(node.op, ast.USub) else float_value
                    )
                complex_value = _r41._r41_complex_from_atom(atom)
                if complex_value is not None:
                    return _r41._r41_complex_value(
                        -complex_value if isinstance(node.op, ast.USub) else complex_value
                    )

            known, scalar = _r35._r35_exact_slice_scalar(operand)
            if known:
                if scalar is None:
                    return _r35._FAILURE_VALUE
                return _integer_value(
                    -scalar if isinstance(node.op, ast.USub) else scalar
                )
            return _UNKNOWN

        return super()._scan_expression(node, environment)

    def _evaluate_call(
        self,
        node: ast.Call,
        environment: dict[str, _Value],
    ) -> _Value:
        if (
            isinstance(node.func, ast.Attribute)
            and node.func.attr in {"get", "__getitem__"}
            and node.args
            and _r47_static_builtins_namespace(node.func.value, environment)
        ):
            receiver = self._scan_expression(node.func.value, environment)
            if _r35._r35_failed(receiver):
                return _r35._FAILURE_VALUE
            arguments, failed = self._scan_call_arguments(node, environment)
            if failed:
                return _r35._FAILURE_VALUE
            if (
                not arguments
                or _r15._container_kind(receiver) is not None
                or not _contains_kind(receiver, "builtins")
            ):
                return _UNKNOWN

            key = arguments[0]
            if node.func.attr == "get" and len(arguments) >= 2:
                return _r45._r45_builtins_get_value(key, arguments[1])
            return _r45._r45_builtins_member_value(key)

        return super()._evaluate_call(node, environment)


def _r47_dynamic_execution_markers_from_source(source: str) -> tuple[str, ...]:
    return _R47BooleanUnaryAndBuiltinsLookupScanner().scan(source)


def test_r47_deepseek_boolean_unary_indices_preserve_exact_selection() -> None:
    source = """\
[eval][-False]("1+1")
[len, eval][+True]("1+1")
[eval, len][-True]("x")
flag = False
[eval][-flag]("1+1")
"""

    assert _r47_dynamic_execution_markers_from_source(source) == (
        "call:1",
        "call:2",
        "call:5",
    )


def test_r47_unary_none_alias_is_definite_failure_before_later_argument() -> None:
    source = """\
def f(*args):
    pass

none_alias = None
f(*+none_alias, eval("1+1"))
"""

    assert _r47_dynamic_execution_markers_from_source(source) == ()


def test_r47_imported_vars_alias_preserves_builtin_ellipsis_lookup_identity() -> None:
    source = """\
def f(*args):
    pass

import builtins
from builtins import vars as v
f(*-v(builtins).get("Ellipsis"), eval("1+1"))
f(*+v(builtins).__getitem__("Ellipsis"), exec("pass"))
f(*-builtins.__dict__.get(*["Ellipsis"]), __import__("math"))
"""

    assert _r47_dynamic_execution_markers_from_source(source) == ()


def test_r47_ellipsis_lookup_failure_preserves_reachable_earlier_effects() -> None:
    source = """\
def f(*args):
    pass

import builtins
from builtins import vars as v
f(eval("1+1"), *-v(builtins).get("Ellipsis"), exec("pass"))
"""

    assert _r47_dynamic_execution_markers_from_source(source) == ("call:6",)


def test_r47_complete_owner_and_oracle_surface_has_no_dynamic_execution() -> None:
    paths = (*_owner_paths(), _FULL_CLOSURE_ORACLE_PATH)

    for path in paths:
        assert _r47_dynamic_execution_markers_from_source(
            path.read_text(encoding="utf-8")
        ) == (), path

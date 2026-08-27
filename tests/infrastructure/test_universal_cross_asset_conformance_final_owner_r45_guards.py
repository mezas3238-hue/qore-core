from __future__ import annotations

import ast

import test_universal_cross_asset_conformance_final_owner_r12_guards as _r12
import test_universal_cross_asset_conformance_final_owner_r15_guards as _r15
import test_universal_cross_asset_conformance_final_owner_r35_guards as _r35
import test_universal_cross_asset_conformance_final_owner_r41_guards as _r41
import test_universal_cross_asset_conformance_final_owner_r44_guards as _r44
from test_universal_cross_asset_conformance_final_owner_r12_guards import (
    _FULL_CLOSURE_ORACLE_PATH,
    _UNKNOWN,
    _Atom,
    _contains_kind,
    _integer_value,
    _merge_values,
    _owner_paths,
    _static_strings,
    _Value,
)

_ELLIPSIS_VALUE: _Value = frozenset({_Atom(_r41._ELLIPSIS_CONSTANT_KIND)})
_ELLIPSIS_STRING_VALUE: _Value = frozenset({_Atom("string", "Ellipsis")})


def _r45_exact_ellipsis(value: _Value) -> bool:
    return value == _ELLIPSIS_VALUE


def _r45_exact_ellipsis_string(value: _Value) -> bool:
    return value == _ELLIPSIS_STRING_VALUE


def _r45_static_builtins_namespace(
    expression: ast.AST,
    environment: dict[str, _Value],
) -> bool:
    if isinstance(expression, ast.Name):
        value = environment.get(
            expression.id,
            _r12._IMPLICIT_BINDINGS.get(expression.id, _UNKNOWN),
        )
        return (
            _r15._container_kind(value) is None
            and _contains_kind(value, "builtins")
        )

    if isinstance(expression, ast.Attribute) and expression.attr == "__dict__":
        return _r45_static_builtins_namespace(expression.value, environment)

    if (
        isinstance(expression, ast.Call)
        and isinstance(expression.func, ast.Name)
        and expression.func.id == "vars"
        and len(expression.args) == 1
        and not expression.keywords
    ):
        helper = environment.get("vars", _r12._IMPLICIT_BINDINGS["vars"])
        return (
            _contains_kind(helper, "helper", "vars")
            and _r45_static_builtins_namespace(expression.args[0], environment)
        )

    return False


def _r45_static_ellipsis_string(
    expression: ast.AST,
    environment: dict[str, _Value],
) -> bool:
    if isinstance(expression, ast.Constant):
        return expression.value == "Ellipsis"
    if isinstance(expression, ast.Name):
        return _r45_exact_ellipsis_string(
            environment.get(expression.id, _UNKNOWN)
        )
    return False


def _r45_builtins_member_value(key: _Value) -> _Value:
    if _r45_exact_ellipsis_string(key):
        return _ELLIPSIS_VALUE

    inherited = _r15._builtins_member_value(key)
    if "Ellipsis" in _static_strings(key):
        return _merge_values(inherited, _ELLIPSIS_VALUE)
    return inherited


def _r45_builtins_get_value(key: _Value, default: _Value) -> _Value:
    if _r45_exact_ellipsis_string(key):
        return _ELLIPSIS_VALUE

    inherited = _r41._r41_builtins_get_value(key, default)
    if "Ellipsis" in _static_strings(key):
        return _merge_values(inherited, _ELLIPSIS_VALUE)
    return inherited


class _R45BuiltinEllipsisAliasScanner(_r44._R44UnaryEllipsisFailureScanner):
    def _scan_expression(
        self,
        node: ast.AST,
        environment: dict[str, _Value],
    ) -> _Value:
        if isinstance(node, ast.Name) and node.id == "Ellipsis" and node.id not in environment:
            return _ELLIPSIS_VALUE

        if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.USub, ast.UAdd)):
            operand = self._scan_expression(node.operand, environment)
            if _r35._r35_failed(operand):
                return _r35._FAILURE_VALUE
            if _r45_exact_ellipsis(operand):
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
                if atom.kind == "integer" and atom.text is not None:
                    integer = int(atom.text)
                    return _integer_value(
                        -integer if isinstance(node.op, ast.USub) else integer
                    )
            return _UNKNOWN

        return super()._scan_expression(node, environment)

    def _evaluate_attribute(
        self,
        node: ast.Attribute,
        environment: dict[str, _Value],
    ) -> _Value:
        if node.attr == "Ellipsis":
            base = self._scan_expression(node.value, environment)
            if _r35._r35_failed(base):
                return _r35._FAILURE_VALUE
            if (
                _r15._container_kind(base) is None
                and _contains_kind(base, "builtins")
            ):
                return _ELLIPSIS_VALUE
            return _UNKNOWN
        return super()._evaluate_attribute(node, environment)

    def _evaluate_non_slice_subscript(
        self,
        receiver: _Value,
        key: _Value,
    ) -> _Value:
        if (
            _r15._container_kind(receiver) is None
            and _contains_kind(receiver, "builtins")
            and _r45_exact_ellipsis_string(key)
        ):
            return _ELLIPSIS_VALUE
        return super()._evaluate_non_slice_subscript(receiver, key)

    def _evaluate_call(
        self,
        node: ast.Call,
        environment: dict[str, _Value],
    ) -> _Value:
        if (
            isinstance(node.func, ast.Attribute)
            and node.func.attr in {"get", "__getitem__"}
            and node.args
            and _r45_static_builtins_namespace(node.func.value, environment)
            and _r45_static_ellipsis_string(node.args[0], environment)
        ):
            receiver = self._scan_expression(node.func.value, environment)
            if _r35._r35_failed(receiver):
                return _r35._FAILURE_VALUE
            arguments, failed = self._scan_call_arguments(node, environment)
            if failed:
                return _r35._FAILURE_VALUE
            if not arguments:
                return _UNKNOWN
            if _r45_exact_ellipsis_string(arguments[0]):
                return _ELLIPSIS_VALUE
            return _UNKNOWN

        return super()._evaluate_call(node, environment)

    def _evaluate_special_call(
        self,
        helper: _Atom,
        arguments: list[_Value],
    ) -> _Value:
        if (
            helper.kind == "helper"
            and helper.text in {"getattr", "getitem"}
            and len(arguments) >= 2
            and _r15._container_kind(arguments[0]) is None
            and _contains_kind(arguments[0], "builtins")
            and _r45_exact_ellipsis_string(arguments[1])
        ):
            return _ELLIPSIS_VALUE

        if (
            helper.kind == "helper"
            and helper.text in {"builtins-map:get", "builtins-map:__getitem__"}
            and arguments
            and _r45_exact_ellipsis_string(arguments[0])
        ):
            return _ELLIPSIS_VALUE

        if (
            helper.kind == "itemgetter"
            and helper.text == "s:Ellipsis"
            and arguments
            and _r15._container_kind(arguments[0]) is None
            and _contains_kind(arguments[0], "builtins")
        ):
            return _ELLIPSIS_VALUE

        if (
            helper.kind == "attrgetter"
            and helper.text == "Ellipsis"
            and arguments
            and _r15._container_kind(arguments[0]) is None
            and _contains_kind(arguments[0], "builtins")
        ):
            return _ELLIPSIS_VALUE

        result = super()._evaluate_special_call(helper, arguments)

        if helper.kind == "helper" and helper.text == "itemgetter" and arguments:
            if _r45_exact_ellipsis_string(arguments[0]):
                return _merge_values(result, frozenset({_Atom("itemgetter", "s:Ellipsis")}))

        if helper.kind == "helper" and helper.text == "attrgetter" and arguments:
            if _r45_exact_ellipsis_string(arguments[0]):
                return _merge_values(result, frozenset({_Atom("attrgetter", "Ellipsis")}))

        return result

    def _scan_import_from(
        self,
        node: ast.ImportFrom,
        environment: dict[str, _Value],
    ) -> None:
        super()._scan_import_from(node, environment)
        if node.module != "builtins":
            return
        for alias in node.names:
            if alias.name == "Ellipsis":
                environment[alias.asname or alias.name] = _ELLIPSIS_VALUE


def _r45_dynamic_execution_markers_from_source(source: str) -> tuple[str, ...]:
    return _R45BuiltinEllipsisAliasScanner().scan(source)


def test_r45_deepseek_builtin_ellipsis_aliases_fail_before_later_arguments() -> None:
    source = """\
def f(*args):
    pass

f(*-Ellipsis, eval("1+1"))
f(*+Ellipsis, exec("pass"))
from builtins import Ellipsis as e
f(*-e, __import__("math"))
import builtins as b
f(*+b.Ellipsis, eval("1+1"))
"""

    assert _r45_dynamic_execution_markers_from_source(source) == ()


def test_r45_builtin_ellipsis_identity_propagates_through_static_aliases() -> None:
    source = """\
def f(*args):
    pass

alias = Ellipsis
f(*-alias, eval("1+1"))
import builtins as b
module_alias = b
ellipsis_alias = module_alias.Ellipsis
f(*+ellipsis_alias, exec("pass"))
"""

    assert _r45_dynamic_execution_markers_from_source(source) == ()


def test_r45_builtin_ellipsis_static_lookup_forms_are_exact() -> None:
    source = """\
def f(*args):
    pass

import builtins
import operator
f(*-builtins.__dict__["Ellipsis"], eval("1+1"))
f(*+builtins.__dict__.get("Ellipsis"), exec("pass"))
f(*-getattr(builtins, "Ellipsis"), __import__("math"))
f(*+operator.getitem(builtins.__dict__, "Ellipsis"), eval("1+1"))
f(*-operator.itemgetter("Ellipsis")(builtins.__dict__), exec("pass"))
f(*+operator.attrgetter("Ellipsis")(builtins), __import__("math"))
"""

    assert _r45_dynamic_execution_markers_from_source(source) == ()


def test_r45_unary_ellipsis_failure_preserves_reachable_earlier_effects() -> None:
    source = """\
def f(*args):
    pass

f(eval("1+1"), *-Ellipsis, exec("pass"))
"""

    assert _r45_dynamic_execution_markers_from_source(source) == ("call:4",)


def test_r45_lexical_shadowing_of_ellipsis_is_not_forced_to_builtin_singleton() -> None:
    source = """\
def f(*args):
    pass

Ellipsis = b"ab"
f(*Ellipsis, eval("1+1"))

def local(Ellipsis):
    f(*Ellipsis, exec("pass"))
"""

    assert _r45_dynamic_execution_markers_from_source(source) == (
        "call:5",
        "call:8",
    )


def test_r45_complete_owner_and_oracle_surface_has_no_dynamic_execution() -> None:
    paths = (*_owner_paths(), _FULL_CLOSURE_ORACLE_PATH)

    for path in paths:
        assert _r45_dynamic_execution_markers_from_source(
            path.read_text(encoding="utf-8")
        ) == (), path

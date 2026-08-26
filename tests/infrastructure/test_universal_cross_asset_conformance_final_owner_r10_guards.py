from __future__ import annotations

import ast
from pathlib import Path

_REPOSITORY_ROOT = Path(__file__).parents[2]
_INFRASTRUCTURE_ROOT = _REPOSITORY_ROOT / "src" / "qore" / "infrastructure"
_FULL_CLOSURE_ORACLE_PATH = Path(__file__).with_name(
    "test_universal_cross_asset_conformance_full_closure.py"
)

_LEGACY_OWNER_STEMS = {
    "fixed_income_economics",
    "rate_term_structure",
    "universal_instrument_identity",
    "universal_instrument_identity_graph",
    "universal_market_topology",
    "universal_valuation_observation",
}
_NON_D04_QUALIFICATION_STEMS = {"dataset_integrity_qualification"}
_DANGEROUS_BUILTIN_NAMES = {"__import__", "eval", "exec"}


def _owner_paths() -> tuple[Path, ...]:
    discovered = set(_INFRASTRUCTURE_ROOT.glob("*_semantics.py"))
    discovered.update(
        path
        for path in _INFRASTRUCTURE_ROOT.glob("*_qualification.py")
        if path.stem not in _NON_D04_QUALIFICATION_STEMS
    )
    discovered.update(
        _INFRASTRUCTURE_ROOT / f"{stem}.py" for stem in _LEGACY_OWNER_STEMS
    )
    return tuple(sorted(discovered))


def _builtins_module_aliases(tree: ast.AST) -> set[str]:
    aliases = {"builtins", "__builtins__"}
    for node in ast.walk(tree):
        if not isinstance(node, ast.Import):
            continue
        for alias in node.names:
            if alias.name == "builtins":
                aliases.add(alias.asname or alias.name)
    return aliases


def _operator_bindings(tree: ast.AST) -> tuple[set[str], set[str]]:
    module_aliases: set[str] = set()
    getitem_aliases: set[str] = set()

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name == "operator":
                    module_aliases.add(alias.asname or alias.name)
            continue

        if not isinstance(node, ast.ImportFrom) or node.module != "operator":
            continue
        for alias in node.names:
            if alias.name == "getitem":
                getitem_aliases.add(alias.asname or alias.name)

    return module_aliases, getitem_aliases


def _is_builtins_namespace(
    expression: ast.AST,
    *,
    builtins_module_aliases: set[str],
) -> bool:
    if isinstance(expression, ast.Name):
        return expression.id in builtins_module_aliases

    if isinstance(expression, ast.Attribute) and expression.attr == "__dict__":
        return _is_builtins_namespace(
            expression.value,
            builtins_module_aliases=builtins_module_aliases,
        )

    if (
        isinstance(expression, ast.Call)
        and isinstance(expression.func, ast.Name)
        and expression.func.id == "getattr"
        and len(expression.args) >= 2
    ):
        attribute = expression.args[1]
        return (
            isinstance(attribute, ast.Constant)
            and attribute.value == "__dict__"
            and _is_builtins_namespace(
                expression.args[0],
                builtins_module_aliases=builtins_module_aliases,
            )
        )

    if (
        isinstance(expression, ast.Call)
        and isinstance(expression.func, ast.Name)
        and expression.func.id == "vars"
        and len(expression.args) == 1
    ):
        return _is_builtins_namespace(
            expression.args[0],
            builtins_module_aliases=builtins_module_aliases,
        )

    return False


def _lookup_key_is_dangerous_or_unknown(expression: ast.AST) -> bool:
    if not isinstance(expression, ast.Constant):
        return True
    return (
        isinstance(expression.value, str)
        and expression.value in _DANGEROUS_BUILTIN_NAMES
    )


def _is_operator_getitem(
    function: ast.AST,
    *,
    operator_module_aliases: set[str],
    operator_getitem_aliases: set[str],
) -> bool:
    if isinstance(function, ast.Name):
        return function.id in operator_getitem_aliases

    return (
        isinstance(function, ast.Attribute)
        and function.attr == "getitem"
        and isinstance(function.value, ast.Name)
        and function.value.id in operator_module_aliases
    )


def _contains_r10_dangerous_callable_reference(
    expression: ast.AST,
    *,
    builtins_module_aliases: set[str],
    operator_module_aliases: set[str],
    operator_getitem_aliases: set[str],
) -> bool:
    if (
        isinstance(expression, ast.Call)
        and isinstance(expression.func, ast.Name)
        and expression.func.id == "getattr"
        and len(expression.args) >= 2
        and _is_builtins_namespace(
            expression.args[0],
            builtins_module_aliases=builtins_module_aliases,
        )
        and _lookup_key_is_dangerous_or_unknown(expression.args[1])
    ):
        return True

    if (
        isinstance(expression, ast.Call)
        and isinstance(expression.func, ast.Attribute)
        and expression.func.attr in {"get", "__getitem__"}
        and len(expression.args) >= 1
        and _is_builtins_namespace(
            expression.func.value,
            builtins_module_aliases=builtins_module_aliases,
        )
        and _lookup_key_is_dangerous_or_unknown(expression.args[0])
    ):
        return True

    if (
        isinstance(expression, ast.Call)
        and _is_operator_getitem(
            expression.func,
            operator_module_aliases=operator_module_aliases,
            operator_getitem_aliases=operator_getitem_aliases,
        )
        and len(expression.args) >= 2
        and _is_builtins_namespace(
            expression.args[0],
            builtins_module_aliases=builtins_module_aliases,
        )
        and _lookup_key_is_dangerous_or_unknown(expression.args[1])
    ):
        return True

    if (
        isinstance(expression, ast.Subscript)
        and _is_builtins_namespace(
            expression.value,
            builtins_module_aliases=builtins_module_aliases,
        )
        and _lookup_key_is_dangerous_or_unknown(expression.slice)
    ):
        return True

    return any(
        _contains_r10_dangerous_callable_reference(
            child,
            builtins_module_aliases=builtins_module_aliases,
            operator_module_aliases=operator_module_aliases,
            operator_getitem_aliases=operator_getitem_aliases,
        )
        for child in ast.iter_child_nodes(expression)
    )


def _r10_dynamic_execution_markers_from_source(source: str) -> tuple[str, ...]:
    tree = ast.parse(source)
    builtins_module_aliases = _builtins_module_aliases(tree)
    operator_module_aliases, operator_getitem_aliases = _operator_bindings(tree)
    markers: list[str] = []

    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module == "builtins":
            if any(alias.name == "__dict__" for alias in node.names):
                markers.append(f"builtins-dict-import:{node.lineno}")

        if isinstance(node, ast.Call) and _contains_r10_dangerous_callable_reference(
            node.func,
            builtins_module_aliases=builtins_module_aliases,
            operator_module_aliases=operator_module_aliases,
            operator_getitem_aliases=operator_getitem_aliases,
        ):
            markers.append(f"call:{node.lineno}")

    return tuple(markers)


def test_r10_imported_builtins_dict_namespace_fails_closed() -> None:
    source = """
from builtins import __dict__ as ns
ns["eval"]("1+1")
"""

    markers = _r10_dynamic_execution_markers_from_source(source)

    assert "builtins-dict-import:2" in markers


def test_r10_nonliteral_builtins_lookup_keys_fail_closed() -> None:
    source = """
import builtins

key = "eval"
getattr(builtins, key)("1+1")
builtins.__dict__[key]("1+1")
builtins.__dict__.get(key)("1+1")
"""

    markers = _r10_dynamic_execution_markers_from_source(source)

    for line_number in (5, 6, 7):
        assert f"call:{line_number}" in markers


def test_r10_operator_getitem_builtins_namespace_fails_closed() -> None:
    source = """
import builtins
import operator as op
from operator import getitem as get_item

op.getitem(builtins.__dict__, "eval")("1+1")
get_item(vars(builtins), "exec")("pass")
"""

    markers = _r10_dynamic_execution_markers_from_source(source)

    for line_number in (6, 7):
        assert f"call:{line_number}" in markers


def test_r10_safe_literal_builtins_lookups_do_not_false_positive() -> None:
    source = """
import builtins
import operator

builtins.__dict__["len"]("abc")
getattr(builtins, "len")([1, 2])
operator.getitem(builtins.__dict__, "len")("abc")
"""

    assert _r10_dynamic_execution_markers_from_source(source) == ()


def test_r10_owner_and_oracle_reject_remaining_builtins_derivations() -> None:
    violations: dict[str, tuple[str, ...]] = {}

    for path in _owner_paths():
        markers = _r10_dynamic_execution_markers_from_source(
            path.read_text(encoding="utf-8")
        )
        if markers:
            violations[str(path)] = markers

    oracle_markers = _r10_dynamic_execution_markers_from_source(
        _FULL_CLOSURE_ORACLE_PATH.read_text(encoding="utf-8")
    )
    if oracle_markers:
        violations[str(_FULL_CLOSURE_ORACLE_PATH)] = oracle_markers

    assert violations == {}

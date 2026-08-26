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
_DYNAMIC_EXECUTION_CALL_NAMES = {"__import__", "eval", "exec"}


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


def _assignment_target_names(target: ast.expr) -> tuple[str, ...]:
    if isinstance(target, ast.Name):
        return (target.id,)
    if isinstance(target, (ast.Tuple, ast.List)):
        return tuple(
            name
            for element in target.elts
            for name in _assignment_target_names(element)
        )
    if isinstance(target, ast.Starred):
        return _assignment_target_names(target.value)
    return ()


def _assignment_value_and_targets(
    node: ast.AST,
) -> tuple[ast.expr | None, tuple[ast.expr, ...]]:
    if isinstance(node, ast.Assign):
        return node.value, tuple(node.targets)
    if isinstance(node, ast.AnnAssign):
        return node.value, (node.target,)
    if isinstance(node, ast.NamedExpr):
        return node.value, (node.target,)
    return None, ()


def _builtins_aliases(tree: ast.AST) -> set[str]:
    aliases = {"builtins", "__builtins__"}
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name == "builtins":
                    aliases.add(alias.asname or alias.name)

    changed = True
    while changed:
        changed = False
        for node in ast.walk(tree):
            value, targets = _assignment_value_and_targets(node)
            if not isinstance(value, ast.Name) or value.id not in aliases:
                continue
            for target in targets:
                for target_name in _assignment_target_names(target):
                    if target_name not in aliases:
                        aliases.add(target_name)
                        changed = True
    return aliases


def _dangerous_direct_names(tree: ast.AST) -> set[str]:
    names = set(_DYNAMIC_EXECUTION_CALL_NAMES)
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module == "builtins":
            for alias in node.names:
                if alias.name in _DYNAMIC_EXECUTION_CALL_NAMES:
                    names.add(alias.asname or alias.name)
    return names


def _is_builtins_namespace(
    expression: ast.AST,
    *,
    builtins_aliases: set[str],
) -> bool:
    if isinstance(expression, ast.Name):
        return expression.id in builtins_aliases
    return (
        isinstance(expression, ast.Attribute)
        and expression.attr == "__dict__"
        and isinstance(expression.value, ast.Name)
        and expression.value.id in builtins_aliases
    )


def _contains_dangerous_callable_reference(
    expression: ast.AST,
    *,
    builtins_aliases: set[str],
    dangerous_direct_names: set[str],
) -> bool:
    if isinstance(expression, ast.Name):
        return expression.id in dangerous_direct_names
    if isinstance(expression, ast.Attribute):
        return (
            expression.attr in _DYNAMIC_EXECUTION_CALL_NAMES
            and _is_builtins_namespace(
                expression.value,
                builtins_aliases=builtins_aliases,
            )
        )
    if (
        isinstance(expression, ast.Call)
        and isinstance(expression.func, ast.Name)
        and expression.func.id == "getattr"
        and len(expression.args) >= 2
    ):
        target, attribute = expression.args[0], expression.args[1]
        return (
            _is_builtins_namespace(target, builtins_aliases=builtins_aliases)
            and isinstance(attribute, ast.Constant)
            and isinstance(attribute.value, str)
            and attribute.value in _DYNAMIC_EXECUTION_CALL_NAMES
        )
    if (
        isinstance(expression, ast.Subscript)
        and _is_builtins_namespace(
            expression.value,
            builtins_aliases=builtins_aliases,
        )
        and isinstance(expression.slice, ast.Constant)
        and isinstance(expression.slice.value, str)
        and expression.slice.value in _DYNAMIC_EXECUTION_CALL_NAMES
    ):
        return True
    if isinstance(expression, ast.Starred):
        return _contains_dangerous_callable_reference(
            expression.value,
            builtins_aliases=builtins_aliases,
            dangerous_direct_names=dangerous_direct_names,
        )
    if isinstance(expression, (ast.Tuple, ast.List, ast.Set)):
        return any(
            _contains_dangerous_callable_reference(
                element,
                builtins_aliases=builtins_aliases,
                dangerous_direct_names=dangerous_direct_names,
            )
            for element in expression.elts
        )
    if isinstance(expression, ast.Dict):
        return any(
            child is not None
            and _contains_dangerous_callable_reference(
                child,
                builtins_aliases=builtins_aliases,
                dangerous_direct_names=dangerous_direct_names,
            )
            for child in (*expression.keys, *expression.values)
        )
    return False


def _dynamic_execution_markers_from_source(source: str) -> tuple[str, ...]:
    tree = ast.parse(source)
    builtins_aliases = _builtins_aliases(tree)
    dangerous_direct_names = _dangerous_direct_names(tree)
    markers: list[str] = []

    for node in ast.walk(tree):
        value, _targets = _assignment_value_and_targets(node)
        line_number: int | None = None
        if isinstance(node, (ast.Assign, ast.AnnAssign, ast.NamedExpr)):
            line_number = node.lineno
        if (
            value is not None
            and line_number is not None
            and _contains_dangerous_callable_reference(
                value,
                builtins_aliases=builtins_aliases,
                dangerous_direct_names=dangerous_direct_names,
            )
        ):
            markers.append(f"binding:{line_number}")

        if isinstance(node, ast.Call) and _contains_dangerous_callable_reference(
            node.func,
            builtins_aliases=builtins_aliases,
            dangerous_direct_names=dangerous_direct_names,
        ):
            markers.append(f"call:{node.lineno}")

        if isinstance(node, ast.Subscript) and _contains_dangerous_callable_reference(
            node,
            builtins_aliases=builtins_aliases,
            dangerous_direct_names=dangerous_direct_names,
        ):
            markers.append(f"subscript:{node.lineno}")

    return tuple(markers)


def test_r5_scanner_closes_builtins_module_alias_and_dict_access() -> None:
    source = """
import builtins as b
f = b
g = f
f.eval("2 + 2")
g.__import__("math")
builtins.__dict__["exec"]("pass")
getattr(g.__dict__, "eval")("3 + 3")
"""

    markers = _dynamic_execution_markers_from_source(source)

    assert len(markers) >= 4


def test_r5_scanner_closes_starred_value_rebinding() -> None:
    source = """
import builtins as b
x = [*[b.eval]]
y = (*[b.exec],)
z = {*[b.__import__]}
x[0]("2 + 2")
"""

    markers = _dynamic_execution_markers_from_source(source)

    assert len(markers) >= 3


def test_r5_owner_and_oracle_reject_dynamic_execution_alias_shapes() -> None:
    violations: dict[str, tuple[str, ...]] = {}

    for path in _owner_paths():
        markers = _dynamic_execution_markers_from_source(
            path.read_text(encoding="utf-8")
        )
        if markers:
            violations[str(path)] = markers

    oracle_markers = _dynamic_execution_markers_from_source(
        _FULL_CLOSURE_ORACLE_PATH.read_text(encoding="utf-8")
    )
    if oracle_markers:
        violations[str(_FULL_CLOSURE_ORACLE_PATH)] = oracle_markers

    assert violations == {}

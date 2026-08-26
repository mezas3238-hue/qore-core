from __future__ import annotations

import ast
import importlib.util
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
_GENERIC_AUTHORITY_MODULE_NAMES = {
    "qore.infrastructure.derivative_contract_semantics",
    "qore.infrastructure.product_composition_semantics",
    "qore.infrastructure.universal_instrument_identity",
    "qore.infrastructure.universal_valuation_observation",
}
_PRODUCT_QUALIFICATION_MODULE_NAMES = {
    "qore.infrastructure.cfd_contract_qualification",
    "qore.infrastructure.rainbow_option_composition_semantics",
    "qore.infrastructure.uit_contract_qualification",
    "qore.infrastructure.warrant_convertible_qualification_semantics",
}
_FORBIDDEN_DIRECTIONAL_IMPORTS = {
    "qore.infrastructure.insurance_linked_risk_transfer_semantics": {
        "qore.infrastructure.event_contract_semantics",
    },
    "qore.infrastructure.event_contract_semantics": {
        "qore.infrastructure.insurance_linked_risk_transfer_semantics",
    },
    "qore.infrastructure.shariah_cross_family_semantics": {
        "qore.infrastructure.sukuk_structural_semantics",
    },
    "qore.infrastructure.sukuk_structural_semantics": {
        "qore.infrastructure.shariah_cross_family_semantics",
    },
    "qore.infrastructure.supply_chain_finance_semantics": {
        "qore.infrastructure.advanced_payable_scf_semantics",
    },
}


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


def _owner_path(module_name: str) -> Path:
    return _INFRASTRUCTURE_ROOT / f"{module_name.rsplit('.', 1)[-1]}.py"


def _resolved_imported_modules_from_source(
    source: str,
    *,
    package: str,
) -> tuple[str, ...]:
    tree = ast.parse(source)
    imports: list[str] = []

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.extend(alias.name for alias in node.names)
            continue
        if not isinstance(node, ast.ImportFrom):
            continue

        imported_module: str | None
        if node.level > 0:
            relative_name = "." * node.level + (node.module or "")
            imported_module = importlib.util.resolve_name(relative_name, package)
        else:
            imported_module = node.module
        if imported_module is None:
            continue

        imports.append(imported_module)
        if node.module is None or imported_module == "qore.infrastructure":
            imports.extend(
                f"{imported_module}.{alias.name}"
                for alias in node.names
                if alias.name != "*"
            )

    return tuple(imports)


def _builtins_aliases(tree: ast.AST) -> set[str]:
    aliases = {"builtins", "__builtins__"}
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name == "builtins":
                    aliases.add(alias.asname or alias.name)
        elif isinstance(node, ast.ImportFrom) and node.module == "builtins":
            for alias in node.names:
                if alias.name == "__dict__":
                    aliases.add(alias.asname or alias.name)
    return aliases


def _dangerous_direct_names(tree: ast.AST) -> set[str]:
    names = set(_DYNAMIC_EXECUTION_CALL_NAMES)
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module == "builtins":
            for alias in node.names:
                if alias.name in _DYNAMIC_EXECUTION_CALL_NAMES:
                    names.add(alias.asname or alias.name)
    return names


def _operator_getitem_bindings(tree: ast.AST) -> tuple[set[str], set[str]]:
    module_aliases: set[str] = set()
    direct_names: set[str] = set()

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name == "operator":
                    module_aliases.add(alias.asname or alias.name)
        elif isinstance(node, ast.ImportFrom) and node.module == "operator":
            for alias in node.names:
                if alias.name == "getitem":
                    direct_names.add(alias.asname or alias.name)

    return module_aliases, direct_names


def _static_string_value(
    expression: ast.AST,
    *,
    constant_strings: dict[str, str],
) -> str | None:
    if isinstance(expression, ast.Constant) and isinstance(expression.value, str):
        return expression.value
    if isinstance(expression, ast.Name):
        return constant_strings.get(expression.id)
    if isinstance(expression, ast.BinOp) and isinstance(expression.op, ast.Add):
        left = _static_string_value(
            expression.left,
            constant_strings=constant_strings,
        )
        right = _static_string_value(
            expression.right,
            constant_strings=constant_strings,
        )
        if left is not None and right is not None:
            return left + right
    return None


def _constant_string_bindings(tree: ast.AST) -> dict[str, str]:
    write_counts: dict[str, int] = {}
    candidate_values: dict[str, ast.AST] = {}

    for node in ast.walk(tree):
        if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Store):
            write_counts[node.id] = write_counts.get(node.id, 0) + 1
        elif isinstance(node, ast.arg):
            write_counts[node.arg] = write_counts.get(node.arg, 0) + 1

        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    candidate_values[target.id] = node.value
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            if node.value is not None:
                candidate_values[node.target.id] = node.value
        elif isinstance(node, ast.NamedExpr) and isinstance(node.target, ast.Name):
            candidate_values[node.target.id] = node.value

    candidates = {
        name: value
        for name, value in candidate_values.items()
        if write_counts.get(name) == 1
    }
    resolved: dict[str, str] = {}

    changed = True
    while changed:
        changed = False
        for name, expression in candidates.items():
            if name in resolved:
                continue
            value = _static_string_value(
                expression,
                constant_strings=resolved,
            )
            if value is not None:
                resolved[name] = value
                changed = True

    return resolved


def _is_builtins_namespace(
    expression: ast.AST,
    *,
    builtins_aliases: set[str],
    constant_strings: dict[str, str],
) -> bool:
    if isinstance(expression, ast.Name):
        return expression.id in builtins_aliases
    if isinstance(expression, ast.Attribute) and expression.attr == "__dict__":
        return _is_builtins_namespace(
            expression.value,
            builtins_aliases=builtins_aliases,
            constant_strings=constant_strings,
        )
    if (
        isinstance(expression, ast.Call)
        and isinstance(expression.func, ast.Name)
        and expression.func.id == "getattr"
        and len(expression.args) >= 2
    ):
        target, attribute = expression.args[0], expression.args[1]
        return (
            _static_string_value(
                attribute,
                constant_strings=constant_strings,
            )
            == "__dict__"
            and _is_builtins_namespace(
                target,
                builtins_aliases=builtins_aliases,
                constant_strings=constant_strings,
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
            builtins_aliases=builtins_aliases,
            constant_strings=constant_strings,
        )
    return False


def _contains_builtins_namespace_reference(
    expression: ast.AST,
    *,
    builtins_aliases: set[str],
    constant_strings: dict[str, str],
) -> bool:
    if _is_builtins_namespace(
        expression,
        builtins_aliases=builtins_aliases,
        constant_strings=constant_strings,
    ):
        return True
    return any(
        _contains_builtins_namespace_reference(
            child,
            builtins_aliases=builtins_aliases,
            constant_strings=constant_strings,
        )
        for child in ast.iter_child_nodes(expression)
    )


def _is_operator_getitem_reference(
    expression: ast.AST,
    *,
    operator_aliases: set[str],
    operator_getitem_names: set[str],
) -> bool:
    if isinstance(expression, ast.Name):
        return expression.id in operator_getitem_names
    return (
        isinstance(expression, ast.Attribute)
        and expression.attr == "getitem"
        and isinstance(expression.value, ast.Name)
        and expression.value.id in operator_aliases
    )


def _contains_dangerous_callable_reference(
    expression: ast.AST,
    *,
    builtins_aliases: set[str],
    dangerous_direct_names: set[str],
    constant_strings: dict[str, str],
    operator_aliases: set[str],
    operator_getitem_names: set[str],
) -> bool:
    if isinstance(expression, ast.Name):
        return expression.id in dangerous_direct_names
    if (
        isinstance(expression, ast.Attribute)
        and expression.attr in _DYNAMIC_EXECUTION_CALL_NAMES
        and _is_builtins_namespace(
            expression.value,
            builtins_aliases=builtins_aliases,
            constant_strings=constant_strings,
        )
    ):
        return True
    if (
        isinstance(expression, ast.Call)
        and isinstance(expression.func, ast.Name)
        and expression.func.id == "getattr"
        and len(expression.args) >= 2
    ):
        target, attribute = expression.args[0], expression.args[1]
        attribute_value = _static_string_value(
            attribute,
            constant_strings=constant_strings,
        )
        if (
            _is_builtins_namespace(
                target,
                builtins_aliases=builtins_aliases,
                constant_strings=constant_strings,
            )
            and attribute_value in _DYNAMIC_EXECUTION_CALL_NAMES
        ):
            return True
    if (
        isinstance(expression, ast.Call)
        and isinstance(expression.func, ast.Attribute)
        and expression.func.attr in {"get", "__getitem__"}
        and _is_builtins_namespace(
            expression.func.value,
            builtins_aliases=builtins_aliases,
            constant_strings=constant_strings,
        )
        and len(expression.args) >= 1
        and _static_string_value(
            expression.args[0],
            constant_strings=constant_strings,
        )
        in _DYNAMIC_EXECUTION_CALL_NAMES
    ):
        return True
    if (
        isinstance(expression, ast.Call)
        and _is_operator_getitem_reference(
            expression.func,
            operator_aliases=operator_aliases,
            operator_getitem_names=operator_getitem_names,
        )
        and len(expression.args) >= 2
        and _is_builtins_namespace(
            expression.args[0],
            builtins_aliases=builtins_aliases,
            constant_strings=constant_strings,
        )
        and _static_string_value(
            expression.args[1],
            constant_strings=constant_strings,
        )
        in _DYNAMIC_EXECUTION_CALL_NAMES
    ):
        return True
    if (
        isinstance(expression, ast.Subscript)
        and _is_builtins_namespace(
            expression.value,
            builtins_aliases=builtins_aliases,
            constant_strings=constant_strings,
        )
        and _static_string_value(
            expression.slice,
            constant_strings=constant_strings,
        )
        in _DYNAMIC_EXECUTION_CALL_NAMES
    ):
        return True
    return any(
        _contains_dangerous_callable_reference(
            child,
            builtins_aliases=builtins_aliases,
            dangerous_direct_names=dangerous_direct_names,
            constant_strings=constant_strings,
            operator_aliases=operator_aliases,
            operator_getitem_names=operator_getitem_names,
        )
        for child in ast.iter_child_nodes(expression)
    )


def _dynamic_execution_markers_from_source(source: str) -> tuple[str, ...]:
    tree = ast.parse(source)
    builtins_aliases = _builtins_aliases(tree)
    dangerous_direct_names = _dangerous_direct_names(tree)
    constant_strings = _constant_string_bindings(tree)
    operator_aliases, operator_getitem_names = _operator_getitem_bindings(tree)
    markers: list[str] = []

    for node in ast.walk(tree):
        value: ast.expr | None = None
        line_number: int | None = None
        if isinstance(node, ast.Assign):
            value = node.value
            line_number = node.lineno
        elif isinstance(node, ast.AnnAssign):
            value = node.value
            line_number = node.lineno
        elif isinstance(node, ast.NamedExpr):
            value = node.value
            line_number = node.lineno

        if value is not None and line_number is not None:
            if _contains_dangerous_callable_reference(
                value,
                builtins_aliases=builtins_aliases,
                dangerous_direct_names=dangerous_direct_names,
                constant_strings=constant_strings,
                operator_aliases=operator_aliases,
                operator_getitem_names=operator_getitem_names,
            ) or _contains_builtins_namespace_reference(
                value,
                builtins_aliases=builtins_aliases,
                constant_strings=constant_strings,
            ):
                markers.append(f"binding:{line_number}")

        if isinstance(node, ast.Call) and _contains_dangerous_callable_reference(
            node.func,
            builtins_aliases=builtins_aliases,
            dangerous_direct_names=dangerous_direct_names,
            constant_strings=constant_strings,
            operator_aliases=operator_aliases,
            operator_getitem_names=operator_getitem_names,
        ):
            markers.append(f"call:{node.lineno}")

    return tuple(markers)


def test_r6_composite_builtins_alias_bindings_fail_closed() -> None:
    source = """
import builtins as b
c, d = b, builtins
x = [b]
c.eval("1+1")
d.exec("1+1")
x[0].eval("1+1")
"""

    markers = _dynamic_execution_markers_from_source(source)

    assert "binding:3" in markers
    assert "binding:4" in markers


def test_r6_subscript_extraction_of_dangerous_callable_fails_closed() -> None:
    source = """
x = [eval][0]
x("1+1")
"""

    markers = _dynamic_execution_markers_from_source(source)

    assert "binding:2" in markers


def test_r6_callable_attribute_execution_fails_closed() -> None:
    source = """
eval.__call__("1+1")
exec.__call__("pass")
__import__.__call__("math")
getattr(eval, "__call__")("2+2")
"""

    markers = _dynamic_execution_markers_from_source(source)

    for line_number in (2, 3, 4, 5):
        assert f"call:{line_number}" in markers


def test_r8_nested_getattr_builtins_dict_execution_fails_closed() -> None:
    source = """
import builtins as b
getattr(getattr(b, "__dict__"), "eval")("1+1")
getattr(getattr(b, "__dict__"), "exec")("pass")
getattr(getattr(b, "__dict__"), "__import__")("math")
"""

    markers = _dynamic_execution_markers_from_source(source)

    for line_number in (3, 4, 5):
        assert f"call:{line_number}" in markers


def test_r9_vars_builtins_namespace_lookup_fails_closed() -> None:
    source = """
import builtins as b
vars(b)["eval"]("1+1")
vars(b)["exec"]("pass")
vars(b)["__import__"]("math")
getattr(vars(b), "eval")("2+2")
"""

    markers = _dynamic_execution_markers_from_source(source)

    for line_number in (3, 4, 5, 6):
        assert f"call:{line_number}" in markers


def test_r9_builtins_mapping_lookup_methods_fail_closed() -> None:
    source = """
import builtins as b
b.__dict__.get("eval")("1+1")
vars(b).get("exec")("pass")
b.__dict__.__getitem__("__import__")("math")
"""

    markers = _dynamic_execution_markers_from_source(source)

    for line_number in (3, 4, 5):
        assert f"call:{line_number}" in markers


def test_r9_safe_vars_and_mapping_lookups_do_not_false_positive() -> None:
    source = """
class Safe:
    eval = staticmethod(lambda value: value)

safe = {"eval": lambda value: value}
safe["eval"]("x")
safe.get("eval")("x")
vars(Safe)["eval"]("x")
"""

    assert _dynamic_execution_markers_from_source(source) == ()


def test_r10_imported_builtins_dict_namespace_fails_closed() -> None:
    source = """
from builtins import __dict__ as namespace
namespace["eval"]("1+1")
namespace.get("exec")("pass")
namespace.__getitem__("__import__")("math")
"""

    markers = _dynamic_execution_markers_from_source(source)

    for line_number in (3, 4, 5):
        assert f"call:{line_number}" in markers


def test_r10_constant_string_lookup_aliases_fail_closed() -> None:
    source = """
import builtins

dict_name = "__" + "dict__"
eval_key = "ev" + "al"
exec_key = "exec"
import_key = "__import__"
forwarded_key = eval_key
getattr(builtins, forwarded_key)("1+1")
getattr(builtins, dict_name)[exec_key]("pass")
builtins.__dict__.get(import_key)("math")
"""

    markers = _dynamic_execution_markers_from_source(source)

    for line_number in (9, 10, 11):
        assert f"call:{line_number}" in markers


def test_r10_operator_getitem_aliases_fail_closed() -> None:
    source = """
import builtins
import operator
import operator as op
from operator import getitem as lookup
operator.getitem(builtins.__dict__, "eval")("1+1")
op.getitem(vars(builtins), "exec")("pass")
lookup(builtins.__dict__, "__import__")("math")
"""

    markers = _dynamic_execution_markers_from_source(source)

    for line_number in (6, 7, 8):
        assert f"call:{line_number}" in markers


def test_r10_safe_constant_and_operator_lookups_do_not_false_positive() -> None:
    source = """
import operator

key = "eval"
safe = {"eval": lambda value: value}
safe[key]("x")
safe.get(key)("x")
operator.getitem(safe, key)("x")
"""

    assert _dynamic_execution_markers_from_source(source) == ()


def test_r6_absolute_package_from_import_expands_for_directionality() -> None:
    source = (
        "from qore.infrastructure import "
        "rainbow_option_composition_semantics\n"
    )
    imported = set(
        _resolved_imported_modules_from_source(
            source,
            package="qore.infrastructure",
        )
    )

    assert "qore.infrastructure.rainbow_option_composition_semantics" in imported


def test_r6_owner_and_oracle_reject_dynamic_execution_extraction_shapes() -> None:
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


def test_r6_directionality_uses_expanded_absolute_and_relative_imports() -> None:
    violations: list[tuple[str, str]] = []

    for module_name in sorted(_GENERIC_AUTHORITY_MODULE_NAMES):
        imported_modules = _resolved_imported_modules_from_source(
            _owner_path(module_name).read_text(encoding="utf-8"),
            package="qore.infrastructure",
        )
        for imported in imported_modules:
            if imported in _PRODUCT_QUALIFICATION_MODULE_NAMES:
                violations.append((module_name, imported))

    for module_name, forbidden_imports in sorted(_FORBIDDEN_DIRECTIONAL_IMPORTS.items()):
        imported_modules = _resolved_imported_modules_from_source(
            _owner_path(module_name).read_text(encoding="utf-8"),
            package="qore.infrastructure",
        )
        for imported in imported_modules:
            if imported in forbidden_imports:
                violations.append((module_name, imported))

    assert violations == []

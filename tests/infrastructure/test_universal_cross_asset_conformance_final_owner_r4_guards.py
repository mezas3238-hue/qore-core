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
_VENDOR_OR_RUNTIME_IMPORT_FRAGMENTS = (
    "oanda_",
    "ctrader_",
    "tradovate",
    "tradestation",
    "tastytrade",
    "ibkr_adapter",
    "provider_runtime",
    "supervised_provider_harness",
    "client_execution_agent",
    "execution_orchestration",
    "execution_boundary",
    "order_intent",
    "controlled_execution",
)
_NETWORK_IMPORT_ROOTS = {
    "aiohttp",
    "ftplib",
    "grpc",
    "http",
    "httpcore",
    "httplib2",
    "httpx",
    "imaplib",
    "nntplib",
    "poplib",
    "requests",
    "smtplib",
    "socket",
    "socketserver",
    "telnetlib",
    "urllib",
    "urllib3",
    "websocket",
    "websockets",
    "wsproto",
    "xmlrpc",
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


def _is_forbidden_provider_runtime_or_network_import(imported: str) -> bool:
    root = imported.split(".", 1)[0]
    return root in _NETWORK_IMPORT_ROOTS or any(
        fragment in imported for fragment in _VENDOR_OR_RUNTIME_IMPORT_FRAGMENTS
    )


def _builtins_aliases(tree: ast.AST) -> set[str]:
    aliases = {"builtins", "__builtins__"}
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name == "builtins":
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
            and isinstance(expression.value, ast.Name)
            and expression.value.id in builtins_aliases
        )
    if (
        isinstance(expression, ast.Call)
        and isinstance(expression.func, ast.Name)
        and expression.func.id == "getattr"
        and len(expression.args) >= 2
    ):
        target, attribute = expression.args[0], expression.args[1]
        return (
            isinstance(target, ast.Name)
            and target.id in builtins_aliases
            and isinstance(attribute, ast.Constant)
            and isinstance(attribute.value, str)
            and attribute.value in _DYNAMIC_EXECUTION_CALL_NAMES
        )
    if (
        isinstance(expression, ast.Subscript)
        and isinstance(expression.value, ast.Name)
        and expression.value.id == "__builtins__"
        and isinstance(expression.slice, ast.Constant)
        and isinstance(expression.slice.value, str)
        and expression.slice.value in _DYNAMIC_EXECUTION_CALL_NAMES
    ):
        return True
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


def _composite_dangerous_rebinding_markers(source: str) -> tuple[str, ...]:
    tree = ast.parse(source)
    builtins_aliases = _builtins_aliases(tree)
    dangerous_direct_names = _dangerous_direct_names(tree)
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
        if (
            value is None
            or line_number is None
            or isinstance(value, (ast.Name, ast.Attribute, ast.Call, ast.Subscript))
        ):
            continue
        if _contains_dangerous_callable_reference(
            value,
            builtins_aliases=builtins_aliases,
            dangerous_direct_names=dangerous_direct_names,
        ):
            markers.append(f"dangerous-composite-binding:{line_number}")

    return tuple(markers)


def test_r4_absolute_package_from_import_exposes_forbidden_submodule() -> None:
    source = "from qore.infrastructure import execution_boundary\n"
    imported = set(
        _resolved_imported_modules_from_source(source, package="qore.infrastructure")
    )

    assert "qore.infrastructure.execution_boundary" in imported
    assert _is_forbidden_provider_runtime_or_network_import(
        "qore.infrastructure.execution_boundary"
    )


def test_r4_final_owner_and_oracle_reject_all_resolved_forbidden_imports() -> None:
    violations: list[tuple[str, str]] = []
    for path in _owner_paths():
        for imported in _resolved_imported_modules_from_source(
            path.read_text(encoding="utf-8"),
            package="qore.infrastructure",
        ):
            if _is_forbidden_provider_runtime_or_network_import(imported):
                violations.append((str(path), imported))

    for imported in _resolved_imported_modules_from_source(
        _FULL_CLOSURE_ORACLE_PATH.read_text(encoding="utf-8"),
        package="tests.infrastructure",
    ):
        if _is_forbidden_provider_runtime_or_network_import(imported):
            violations.append((str(_FULL_CLOSURE_ORACLE_PATH), imported))

    assert violations == []


def test_r4_tuple_list_nested_and_starred_rebindings_are_rejected() -> None:
    source = """
import builtins as b
first, second = eval, exec
[nested, [deep]] = [b.eval, [getattr(b, "exec")]]
*rest, = (__builtins__["__import__"],)
first("1 + 1")
second("pass")
"""

    markers = _composite_dangerous_rebinding_markers(source)
    assert len(markers) == 3


def test_r4_owner_and_oracle_reject_composite_dynamic_callable_rebindings() -> None:
    violations: dict[str, tuple[str, ...]] = {}
    for path in _owner_paths():
        markers = _composite_dangerous_rebinding_markers(
            path.read_text(encoding="utf-8")
        )
        if markers:
            violations[str(path)] = markers

    oracle_markers = _composite_dangerous_rebinding_markers(
        _FULL_CLOSURE_ORACLE_PATH.read_text(encoding="utf-8")
    )
    if oracle_markers:
        violations[str(_FULL_CLOSURE_ORACLE_PATH)] = oracle_markers

    assert violations == {}


def test_r4_direct_http_network_roots_are_forbidden() -> None:
    for module_name in (
        "http.client",
        "urllib3",
        "socketserver",
        "xmlrpc.client",
    ):
        assert _is_forbidden_provider_runtime_or_network_import(module_name)

from __future__ import annotations

import ast
import importlib
import inspect
from pathlib import Path
from types import ModuleType

_OWNER_MODULE_NAMES = (
    "qore.infrastructure.universal_instrument_identity",
    "qore.infrastructure.universal_instrument_identity_graph",
    "qore.infrastructure.fixed_income_economics",
    "qore.infrastructure.rate_term_structure",
    "qore.infrastructure.derivative_contract_semantics",
    "qore.infrastructure.equity_fund_corporate_action_semantics",
    "qore.infrastructure.commodity_contract_delivery_semantics",
    "qore.infrastructure.crypto_perpetual_funding_semantics",
    "qore.infrastructure.structured_hybrid_synthetic_semantics",
    "qore.infrastructure.universal_valuation_observation",
    "qore.infrastructure.universal_market_topology",
)

_OWNER_MODULES: tuple[ModuleType, ...] = tuple(
    importlib.import_module(module_name) for module_name in _OWNER_MODULE_NAMES
)

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
    "httpx",
    "requests",
    "socket",
    "urllib",
    "websockets",
}


def _imported_modules(module: ModuleType) -> tuple[str, ...]:
    tree = ast.parse(inspect.getsource(module))
    imports: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module is not None:
            imports.append(node.module)
    return tuple(imports)


def test_certified_umi_owner_modules_do_not_import_vendor_or_execution_runtime() -> None:
    violations: list[tuple[str, str]] = []
    for module in _OWNER_MODULES:
        for imported in _imported_modules(module):
            if any(fragment in imported for fragment in _VENDOR_OR_RUNTIME_IMPORT_FRAGMENTS):
                violations.append((module.__name__, imported))

    assert violations == []


def test_certified_umi_owner_modules_do_not_import_network_clients() -> None:
    violations: list[tuple[str, str]] = []
    for module in _OWNER_MODULES:
        for imported in _imported_modules(module):
            root = imported.split(".", 1)[0]
            if root in _NETWORK_IMPORT_ROOTS:
                violations.append((module.__name__, imported))

    assert violations == []


def test_cross_asset_harness_uses_real_contracts_not_mock_semantic_facsimiles() -> None:
    harness_path = Path(__file__).with_name("test_universal_cross_asset_conformance.py")
    tree = ast.parse(harness_path.read_text(encoding="utf-8"))

    imported_modules: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported_modules.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module is not None:
            imported_modules.append(node.module)

    assert not any(value.startswith("unittest.mock") for value in imported_modules)
    assert "pytest_mock" not in imported_modules
    assert not any(isinstance(node, ast.ClassDef) for node in ast.walk(tree))


def test_cross_asset_harness_does_not_define_execution_or_provider_helpers() -> None:
    harness_path = Path(__file__).with_name("test_universal_cross_asset_conformance.py")
    tree = ast.parse(harness_path.read_text(encoding="utf-8"))

    function_names = {
        node.name for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)
    }
    forbidden_helpers = {
        "execute",
        "route",
        "submit",
        "match",
        "best_venue",
        "provider_capability",
        "calculate_price",
        "calculate_value",
        "settle",
    }
    assert function_names.isdisjoint(forbidden_helpers)


def test_cross_asset_harness_imports_no_provider_specific_module() -> None:
    harness_path = Path(__file__).with_name("test_universal_cross_asset_conformance.py")
    tree = ast.parse(harness_path.read_text(encoding="utf-8"))
    imported_modules: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported_modules.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module is not None:
            imported_modules.append(node.module)

    assert not any(
        fragment in imported
        for imported in imported_modules
        for fragment in _VENDOR_OR_RUNTIME_IMPORT_FRAGMENTS
    )


def test_cross_asset_harness_has_no_mutation_of_production_source_tree() -> None:
    harness_path = Path(__file__).with_name("test_universal_cross_asset_conformance.py")
    source = harness_path.read_text(encoding="utf-8")
    tree = ast.parse(source)

    forbidden_calls = {
        "write_text",
        "write_bytes",
        "unlink",
        "rename",
        "replace",
        "mkdir",
        "rmdir",
    }
    called_attributes = {
        node.func.attr
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
    }
    assert called_attributes.isdisjoint(forbidden_calls)

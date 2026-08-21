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
    "qore.infrastructure.fx_semantics",
    "qore.infrastructure.option_exotic_semantics",
    "qore.infrastructure.fixed_income_securitization_semantics",
)

_MANDATORY_CARRY_FORWARD_MODULES = (
    "qore.infrastructure.fx_semantics",
    "qore.infrastructure.option_exotic_semantics",
    "qore.infrastructure.fixed_income_securitization_semantics",
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


def _file_imports(path: Path) -> tuple[str, ...]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    imports: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module is not None:
            imports.append(node.module)
    return tuple(imports)


def test_full_closure_owner_universe_includes_mandatory_carry_forward() -> None:
    assert len(_OWNER_MODULE_NAMES) == 14
    assert _OWNER_MODULE_NAMES[-3:] == _MANDATORY_CARRY_FORWARD_MODULES


def test_full_closure_owner_universe_rejects_vendor_or_runtime_imports() -> None:
    violations: list[tuple[str, str]] = []
    for module in _OWNER_MODULES:
        for imported in _imported_modules(module):
            if any(
                fragment in imported
                for fragment in _VENDOR_OR_RUNTIME_IMPORT_FRAGMENTS
            ):
                violations.append((module.__name__, imported))

    assert violations == []


def test_full_closure_owner_universe_has_no_direct_network_clients() -> None:
    violations: list[tuple[str, str]] = []
    for module in _OWNER_MODULES:
        for imported in _imported_modules(module):
            root = imported.split(".", 1)[0]
            if root in _NETWORK_IMPORT_ROOTS:
                violations.append((module.__name__, imported))

    assert violations == []


def test_full_closure_oracle_imports_all_mandatory_new_owners() -> None:
    oracle_path = Path(__file__).with_name(
        "test_universal_cross_asset_conformance_full_closure.py"
    )
    imported = _file_imports(oracle_path)

    assert set(_MANDATORY_CARRY_FORWARD_MODULES).issubset(imported)


def test_full_closure_oracle_defines_no_semantic_facsimile_classes() -> None:
    oracle_path = Path(__file__).with_name(
        "test_universal_cross_asset_conformance_full_closure.py"
    )
    tree = ast.parse(oracle_path.read_text(encoding="utf-8"))

    assert not any(isinstance(node, ast.ClassDef) for node in ast.walk(tree))


def test_full_closure_oracle_defines_no_operational_authority_helpers() -> None:
    oracle_path = Path(__file__).with_name(
        "test_universal_cross_asset_conformance_full_closure.py"
    )
    tree = ast.parse(oracle_path.read_text(encoding="utf-8"))
    function_names = {
        node.name for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)
    }
    forbidden = {
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

    assert function_names.isdisjoint(forbidden)

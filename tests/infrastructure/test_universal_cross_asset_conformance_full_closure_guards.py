from __future__ import annotations

import ast
import importlib
import inspect
from pathlib import Path
from types import ModuleType

_REPOSITORY_ROOT = Path(__file__).parents[2]
_INFRASTRUCTURE_ROOT = _REPOSITORY_ROOT / "src" / "qore" / "infrastructure"
_ORACLE_PATH = Path(__file__).with_name(
    "test_universal_cross_asset_conformance_full_closure.py"
)

_LEGACY_OWNER_MODULE_NAMES = (
    "qore.infrastructure.universal_instrument_identity",
    "qore.infrastructure.universal_instrument_identity_graph",
    "qore.infrastructure.fixed_income_economics",
    "qore.infrastructure.rate_term_structure",
    "qore.infrastructure.universal_valuation_observation",
    "qore.infrastructure.universal_market_topology",
)

_SEMANTIC_OWNER_MODULE_NAMES = (
    "qore.infrastructure.advanced_payable_scf_semantics",
    "qore.infrastructure.cash_money_market_semantics",
    "qore.infrastructure.commodity_contract_delivery_semantics",
    "qore.infrastructure.crypto_perpetual_funding_semantics",
    "qore.infrastructure.crypto_staking_tokenization_semantics",
    "qore.infrastructure.derivative_contract_semantics",
    "qore.infrastructure.equity_fund_corporate_action_semantics",
    "qore.infrastructure.event_contract_semantics",
    "qore.infrastructure.fixed_income_securitization_semantics",
    "qore.infrastructure.futures_deliverable_basket_semantics",
    "qore.infrastructure.futures_final_settlement_semantics",
    "qore.infrastructure.fx_semantics",
    "qore.infrastructure.insurance_linked_risk_transfer_semantics",
    "qore.infrastructure.loan_credit_facility_semantics",
    "qore.infrastructure.option_exotic_semantics",
    "qore.infrastructure.product_composition_semantics",
    "qore.infrastructure.rainbow_option_composition_semantics",
    "qore.infrastructure.rates_otc_semantics",
    "qore.infrastructure.securities_financing_semantics",
    "qore.infrastructure.shariah_cross_family_semantics",
    "qore.infrastructure.specialized_commodity_semantics",
    "qore.infrastructure.structured_hybrid_synthetic_semantics",
    "qore.infrastructure.structured_note_payoff_semantics",
    "qore.infrastructure.sukuk_structural_semantics",
    "qore.infrastructure.supply_chain_finance_semantics",
    "qore.infrastructure.volatility_variance_semantics",
    "qore.infrastructure.warrant_convertible_qualification_semantics",
)

_EXPLICIT_QUALIFICATION_OWNER_MODULE_NAMES = (
    "qore.infrastructure.cfd_contract_qualification",
    "qore.infrastructure.uit_contract_qualification",
)

_OWNER_MODULE_NAMES = (
    *_LEGACY_OWNER_MODULE_NAMES,
    *_SEMANTIC_OWNER_MODULE_NAMES,
    *_EXPLICIT_QUALIFICATION_OWNER_MODULE_NAMES,
)
_OWNER_MODULES: tuple[ModuleType, ...] = tuple(
    importlib.import_module(module_name) for module_name in _OWNER_MODULE_NAMES
)

_GENERIC_AUTHORITY_MODULE_NAMES = (
    "qore.infrastructure.universal_instrument_identity",
    "qore.infrastructure.derivative_contract_semantics",
    "qore.infrastructure.product_composition_semantics",
    "qore.infrastructure.universal_valuation_observation",
)
_PRODUCT_QUALIFICATION_MODULE_NAMES = (
    "qore.infrastructure.cfd_contract_qualification",
    "qore.infrastructure.rainbow_option_composition_semantics",
    "qore.infrastructure.uit_contract_qualification",
    "qore.infrastructure.warrant_convertible_qualification_semantics",
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


def _discovered_semantic_owner_module_names() -> tuple[str, ...]:
    return tuple(
        sorted(
            f"qore.infrastructure.{path.stem}"
            for path in _INFRASTRUCTURE_ROOT.glob("*_semantics.py")
        )
    )


def test_full_closure_manifest_matches_live_d04_owner_surface() -> None:
    assert len(set(_OWNER_MODULE_NAMES)) == len(_OWNER_MODULE_NAMES)
    assert set(_SEMANTIC_OWNER_MODULE_NAMES) == set(
        _discovered_semantic_owner_module_names()
    )
    for module_name in (
        *_LEGACY_OWNER_MODULE_NAMES,
        *_EXPLICIT_QUALIFICATION_OWNER_MODULE_NAMES,
    ):
        path = _INFRASTRUCTURE_ROOT / f"{module_name.rsplit('.', 1)[-1]}.py"
        assert path.is_file()


def test_full_closure_owner_universe_is_importable() -> None:
    assert tuple(module.__name__ for module in _OWNER_MODULES) == _OWNER_MODULE_NAMES


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


def test_generic_authorities_do_not_reverse_import_product_qualifications() -> None:
    forbidden = set(_PRODUCT_QUALIFICATION_MODULE_NAMES)
    violations: list[tuple[str, str]] = []
    for module_name in _GENERIC_AUTHORITY_MODULE_NAMES:
        module = importlib.import_module(module_name)
        for imported in _imported_modules(module):
            if imported in forbidden:
                violations.append((module_name, imported))

    assert violations == []


def test_rainbow_composes_existing_option_and_product_composition_authorities() -> None:
    rainbow = importlib.import_module(
        "qore.infrastructure.rainbow_option_composition_semantics"
    )
    imported = set(_imported_modules(rainbow))

    assert "qore.infrastructure.derivative_contract_semantics" in imported
    assert "qore.infrastructure.product_composition_semantics" in imported


def test_advanced_payable_extends_without_redefining_scf_owner_module() -> None:
    advanced = importlib.import_module(
        "qore.infrastructure.advanced_payable_scf_semantics"
    )
    imported = set(_imported_modules(advanced))

    assert "qore.infrastructure.supply_chain_finance_semantics" in imported
    assert (
        "qore.infrastructure.advanced_payable_scf_semantics"
        not in _imported_modules(
            importlib.import_module(
                "qore.infrastructure.supply_chain_finance_semantics"
            )
        )
    )


def test_full_closure_oracle_defines_no_semantic_facsimile_classes() -> None:
    tree = ast.parse(_ORACLE_PATH.read_text(encoding="utf-8"))

    assert not any(isinstance(node, ast.ClassDef) for node in ast.walk(tree))


def test_full_closure_oracle_defines_no_operational_authority_helpers() -> None:
    tree = ast.parse(_ORACLE_PATH.read_text(encoding="utf-8"))
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


def test_full_closure_oracle_does_not_import_provider_or_runtime_code() -> None:
    violations = []
    for imported in _file_imports(_ORACLE_PATH):
        root = imported.split(".", 1)[0]
        if root in _NETWORK_IMPORT_ROOTS or any(
            fragment in imported for fragment in _VENDOR_OR_RUNTIME_IMPORT_FRAGMENTS
        ):
            violations.append(imported)

    assert violations == []

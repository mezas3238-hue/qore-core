from __future__ import annotations

import ast
from pathlib import Path

_REPOSITORY_ROOT = Path(__file__).parents[2]
_INFRASTRUCTURE_ROOT = _REPOSITORY_ROOT / "src" / "qore" / "infrastructure"
_FULL_CLOSURE_ORACLE_PATH = Path(__file__).with_name(
    "test_universal_cross_asset_conformance_full_closure.py"
)

_EXPECTED_D04_OWNER_MODULE_NAMES = {
    "qore.infrastructure.advanced_payable_scf_semantics",
    "qore.infrastructure.cash_money_market_semantics",
    "qore.infrastructure.cfd_contract_qualification",
    "qore.infrastructure.commodity_contract_delivery_semantics",
    "qore.infrastructure.crypto_perpetual_funding_semantics",
    "qore.infrastructure.crypto_staking_tokenization_semantics",
    "qore.infrastructure.derivative_contract_semantics",
    "qore.infrastructure.equity_fund_corporate_action_semantics",
    "qore.infrastructure.event_contract_semantics",
    "qore.infrastructure.fixed_income_economics",
    "qore.infrastructure.fixed_income_securitization_semantics",
    "qore.infrastructure.futures_deliverable_basket_semantics",
    "qore.infrastructure.futures_final_settlement_semantics",
    "qore.infrastructure.fx_semantics",
    "qore.infrastructure.insurance_linked_risk_transfer_semantics",
    "qore.infrastructure.loan_credit_facility_semantics",
    "qore.infrastructure.option_exotic_semantics",
    "qore.infrastructure.product_composition_semantics",
    "qore.infrastructure.rainbow_option_composition_semantics",
    "qore.infrastructure.rate_term_structure",
    "qore.infrastructure.rates_otc_semantics",
    "qore.infrastructure.securities_financing_semantics",
    "qore.infrastructure.shariah_cross_family_semantics",
    "qore.infrastructure.specialized_commodity_semantics",
    "qore.infrastructure.structured_hybrid_synthetic_semantics",
    "qore.infrastructure.structured_note_payoff_semantics",
    "qore.infrastructure.sukuk_structural_semantics",
    "qore.infrastructure.supply_chain_finance_semantics",
    "qore.infrastructure.uit_contract_qualification",
    "qore.infrastructure.universal_instrument_identity",
    "qore.infrastructure.universal_instrument_identity_graph",
    "qore.infrastructure.universal_market_topology",
    "qore.infrastructure.universal_valuation_observation",
    "qore.infrastructure.volatility_variance_semantics",
    "qore.infrastructure.warrant_convertible_qualification_semantics",
}

_LEGACY_D04_OWNER_MODULE_NAMES = {
    "qore.infrastructure.fixed_income_economics",
    "qore.infrastructure.rate_term_structure",
    "qore.infrastructure.universal_instrument_identity",
    "qore.infrastructure.universal_instrument_identity_graph",
    "qore.infrastructure.universal_market_topology",
    "qore.infrastructure.universal_valuation_observation",
}

_NON_D04_QUALIFICATION_MODULE_NAMES = {
    "qore.infrastructure.dataset_integrity_qualification",
}

_DYNAMIC_EXECUTION_CALL_NAMES = {
    "__import__",
    "eval",
    "exec",
}

_SFT_CURRENT_STATE_NAME_FRAGMENTS = {
    "Account",
    "Balance",
    "Current",
    "Exposure",
    "Inventory",
    "Position",
    "Risk",
    "State",
}


def _module_name(path: Path) -> str:
    return f"qore.infrastructure.{path.stem}"


def _owner_path(module_name: str) -> Path:
    return _INFRASTRUCTURE_ROOT / f"{module_name.rsplit('.', 1)[-1]}.py"


def _discovered_d04_owner_module_names() -> set[str]:
    semantic_names = {
        _module_name(path) for path in _INFRASTRUCTURE_ROOT.glob("*_semantics.py")
    }
    qualification_names = {
        _module_name(path) for path in _INFRASTRUCTURE_ROOT.glob("*_qualification.py")
    }
    qualification_names -= _NON_D04_QUALIFICATION_MODULE_NAMES
    return semantic_names | qualification_names | _LEGACY_D04_OWNER_MODULE_NAMES


def _dynamic_import_or_execution_markers(path: Path) -> tuple[str, ...]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    markers: list[str] = []

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name == "importlib" or alias.name.startswith("importlib."):
                    markers.append(f"import:{alias.name}")
        elif isinstance(node, ast.ImportFrom):
            module = node.module
            if module is not None and (
                module == "importlib" or module.startswith("importlib.")
            ):
                markers.append(f"from:{module}")
        elif isinstance(node, ast.Call):
            function = node.func
            if (
                isinstance(function, ast.Name)
                and function.id in _DYNAMIC_EXECUTION_CALL_NAMES
            ):
                markers.append(f"call:{function.id}")
            elif isinstance(function, ast.Name) and function.id == "import_module":
                markers.append("call:import_module")
            elif isinstance(function, ast.Attribute) and function.attr == "import_module":
                markers.append("call:*.import_module")

    return tuple(markers)


def test_final_owner_discovery_is_exact_across_semantics_and_qualifications() -> None:
    live_qualification_names = {
        _module_name(path) for path in _INFRASTRUCTURE_ROOT.glob("*_qualification.py")
    }
    assert _NON_D04_QUALIFICATION_MODULE_NAMES <= live_qualification_names
    assert _discovered_d04_owner_module_names() == _EXPECTED_D04_OWNER_MODULE_NAMES


def test_final_owner_surface_forbids_dynamic_import_or_code_execution() -> None:
    violations: dict[str, tuple[str, ...]] = {}
    for module_name in sorted(_EXPECTED_D04_OWNER_MODULE_NAMES):
        path = _owner_path(module_name)
        markers = _dynamic_import_or_execution_markers(path)
        if markers:
            violations[module_name] = markers

    oracle_markers = _dynamic_import_or_execution_markers(_FULL_CLOSURE_ORACLE_PATH)
    if oracle_markers:
        violations[str(_FULL_CLOSURE_ORACLE_PATH)] = oracle_markers

    assert violations == {}


def test_securities_financing_owner_cannot_add_current_state_authority_shapes() -> None:
    path = _owner_path("qore.infrastructure.securities_financing_semantics")
    tree = ast.parse(path.read_text(encoding="utf-8"))
    class_names = {
        node.name for node in ast.walk(tree) if isinstance(node, ast.ClassDef)
    }
    violations = sorted(
        class_name
        for class_name in class_names
        if any(
            fragment in class_name for fragment in _SFT_CURRENT_STATE_NAME_FRAGMENTS
        )
    )

    assert violations == []

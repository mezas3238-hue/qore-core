from __future__ import annotations

import ast
from inspect import getsource
from pathlib import Path
from types import ModuleType

import qore.infrastructure.cash_money_market_semantics as cash_money_market
import qore.infrastructure.fixed_income_securitization_semantics as securitization
import qore.infrastructure.fx_semantics as fx_semantics
import qore.infrastructure.instrument_universe_registry as registry
import qore.infrastructure.loan_credit_facility_semantics as loan_facility
import qore.infrastructure.option_exotic_semantics as option_exotic

_CURRENT_INTEGRATED_OWNER_MODULES: tuple[ModuleType, ...] = (
    cash_money_market,
    securitization,
    loan_facility,
    fx_semantics,
    option_exotic,
)

_EXPECTED_CURRENT_OWNER_MODULE_NAMES = (
    "qore.infrastructure.cash_money_market_semantics",
    "qore.infrastructure.fixed_income_securitization_semantics",
    "qore.infrastructure.loan_credit_facility_semantics",
    "qore.infrastructure.fx_semantics",
    "qore.infrastructure.option_exotic_semantics",
)

_EXPECTED_CURRENT_FAMILIES = (
    "cash-money-market",
    "fixed-income-credit",
    "rates-term-structures",
    "equities",
    "funds-pooled-vehicles",
    "indices-benchmarks",
    "fx",
    "futures",
    "options",
    "forwards-swaps-otc",
    "commodities",
    "crypto-digital-assets",
    "structured-hybrid-products",
    "volatility-variance-products",
    "securities-financing",
    "cross-asset-compositions",
    "event-contracts",
    "contracts-for-difference",
    "loans-credit-facilities",
)


def _imported_modules(module: ModuleType) -> set[str]:
    tree = ast.parse(getsource(module))
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module is not None:
            imported.add(node.module)
    return imported


def _repository_root() -> Path:
    return Path(__file__).resolve().parents[2]


def test_current_integrated_carry_forward_owner_set_is_explicit_and_fixed() -> None:
    assert len(_CURRENT_INTEGRATED_OWNER_MODULES) == 5
    assert tuple(module.__name__ for module in _CURRENT_INTEGRATED_OWNER_MODULES) == (
        _EXPECTED_CURRENT_OWNER_MODULE_NAMES
    )


def test_registry_does_not_gain_reverse_dependencies_on_later_semantic_owners() -> None:
    source = getsource(registry)
    for owner_name in _EXPECTED_CURRENT_OWNER_MODULE_NAMES:
        assert owner_name not in source


def test_current_integrated_owner_modules_do_not_import_provider_specific_packages() -> None:
    prohibited_prefixes = (
        "qore.providers",
        "qore.infrastructure.oanda",
        "qore.infrastructure.ctrader",
        "requests",
        "httpx",
        "urllib",
        "socket",
    )
    for module in _CURRENT_INTEGRATED_OWNER_MODULES:
        imports = _imported_modules(module)
        for imported in imports:
            assert not imported.startswith(prohibited_prefixes)


def test_historical_snapshot_is_preserved_and_not_relabelled_as_current() -> None:
    root = _repository_root()
    historical = (
        root
        / "docs"
        / "architecture"
        / "QORE-UMI-13-INSTRUMENT-UNIVERSE-REGISTRY-001.md"
    ).read_text(encoding="utf-8")

    assert "2026-08-15" in historical
    assert "e429c8731f1fca4bb0aa7c1eaa8b8865cb0375f0" in historical
    assert "COMPLETE AS OF VERIFIED SNAPSHOT DATE" in historical
    assert "!= COMPLETE FOREVER" in historical


def test_full_closure_ledger_is_bound_to_exact_current_gate_b_baseline() -> None:
    root = _repository_root()
    ledger = (
        root
        / "docs"
        / "architecture"
        / "QORE-UMI-13-FULL-CLOSURE-RECERTIFICATION-001.md"
    ).read_text(encoding="utf-8")

    assert "d642dcd440fbe148c80194eda542210c08c42bd5" in ledger
    assert "15fe1490b8f24387332bb17e0171348497c69442" in ledger
    assert "2026-08-21" in ledger
    assert "HISTORICAL SNAPSHOT != CURRENT RECERTIFICATION" in ledger


def test_full_closure_ledger_names_all_19_current_families() -> None:
    root = _repository_root()
    ledger = (
        root
        / "docs"
        / "architecture"
        / "QORE-UMI-13-FULL-CLOSURE-RECERTIFICATION-001.md"
    ).read_text(encoding="utf-8")

    assert len(_EXPECTED_CURRENT_FAMILIES) == 19
    assert len(set(_EXPECTED_CURRENT_FAMILIES)) == 19
    for family in _EXPECTED_CURRENT_FAMILIES:
        assert f"`{family}`" in ledger


def test_full_closure_ledger_re_adjudicates_every_historical_unresolved_ref() -> None:
    root = _repository_root()
    ledger = (
        root
        / "docs"
        / "architecture"
        / "QORE-UMI-13-FULL-CLOSURE-RECERTIFICATION-001.md"
    ).read_text(encoding="utf-8")

    for number in range(1, 25):
        assert f"UMI13-UNR-{number:03d}" in ledger


def test_open_preparatory_candidates_cannot_count_as_current_main_owners() -> None:
    root = _repository_root()
    ledger = (
        root
        / "docs"
        / "architecture"
        / "QORE-UMI-13-FULL-CLOSURE-RECERTIFICATION-001.md"
    ).read_text(encoding="utf-8")

    assert "OPEN/DRAFT CANDIDATE != CURRENT MAIN OWNER" in ledger
    for pr_number in (386, 389, 391, 393, 395, 397, 399, 401):
        assert f"#{pr_number}" in ledger

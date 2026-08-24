from __future__ import annotations

import ast
from importlib.util import resolve_name
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

_EXPECTED_UNR_DISPOSITIONS = (
    (
        "UMI13-UNR-001",
        "RESOLVED AT CURRENT MAIN FOR THE HISTORICAL BOUNDED TARGET",
    ),
    (
        "UMI13-UNR-002",
        "RESOLVED AT CURRENT MAIN FOR THE HISTORICAL BOUNDED TARGET",
    ),
    (
        "UMI13-UNR-003",
        "RESOLVED AT CURRENT MAIN FOR THE HISTORICAL BOUNDED TARGET",
    ),
    (
        "UMI13-UNR-004",
        "RESOLVED AT CURRENT MAIN FOR THE HISTORICAL BOUNDED TARGET",
    ),
    ("UMI13-UNR-005", "OPEN"),
    ("UMI13-UNR-006", "PARTIALLY SUPERSEDED / RESIDUAL OPEN"),
    ("UMI13-UNR-007", "PARTIALLY SUPERSEDED / RESIDUAL OPEN"),
    ("UMI13-UNR-008", "OPEN"),
    ("UMI13-UNR-009", "OPEN"),
    ("UMI13-UNR-010", "OPEN"),
    ("UMI13-UNR-011", "OPEN"),
    ("UMI13-UNR-012", "OPEN"),
    ("UMI13-UNR-013", "OPEN"),
    ("UMI13-UNR-014", "OPEN"),
    ("UMI13-UNR-015", "OPEN"),
    ("UMI13-UNR-016", "OPEN"),
    ("UMI13-UNR-017", "OPEN"),
    ("UMI13-UNR-018", "OPEN"),
    ("UMI13-UNR-019", "OPEN"),
    ("UMI13-UNR-020", "OPEN"),
    ("UMI13-UNR-021", "OPEN"),
    ("UMI13-UNR-022", "OPEN"),
    ("UMI13-UNR-023", "OPEN"),
    ("UMI13-UNR-024", "OPEN"),
)

_EXPECTED_CARRY_FORWARD_SNAPSHOTS = (
    "#333 temporal canonicalization: CLOSED / completed before this Gate-B baseline",
    "#146 OANDA Practice blocker: CLOSED / not_planned; no UMI13 semantic promotion",
    "#332 scarce-capacity reservation: OPEN / cross-owner operational gap",
    "#334 external in-flight side-effect containment: OPEN / productive-safety gap",
    "#350 computed valuation producer/methodology: OPEN / D07 gap",
    "#286 concrete research methodology: OPEN / research-methodology gap",
)


def _imported_modules(module: ModuleType) -> set[str]:
    tree = ast.parse(getsource(module))
    imported: set[str] = set()
    package = module.__package__ or ""
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            base = node.module or ""
            if node.level:
                absolute = resolve_name(f"{'.' * node.level}{base}", package)
            else:
                absolute = base
            if absolute:
                imported.add(absolute)
            for alias in node.names:
                if alias.name == "*":
                    continue
                imported.add(f"{absolute}.{alias.name}" if absolute else alias.name)
    return imported


def _repository_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _full_closure_ledger() -> str:
    root = _repository_root()
    return (
        root
        / "docs"
        / "architecture"
        / "QORE-UMI-13-FULL-CLOSURE-RECERTIFICATION-001.md"
    ).read_text(encoding="utf-8")


def test_current_integrated_carry_forward_owner_set_is_explicit_and_fixed() -> None:
    assert len(_CURRENT_INTEGRATED_OWNER_MODULES) == 5
    assert tuple(module.__name__ for module in _CURRENT_INTEGRATED_OWNER_MODULES) == (
        _EXPECTED_CURRENT_OWNER_MODULE_NAMES
    )


def test_registry_does_not_gain_reverse_dependencies_on_later_semantic_owners() -> None:
    imports = _imported_modules(registry)
    for owner_name in _EXPECTED_CURRENT_OWNER_MODULE_NAMES:
        assert owner_name not in imports


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
    ledger = _full_closure_ledger()

    assert "d642dcd440fbe148c80194eda542210c08c42bd5" in ledger
    assert "15fe1490b8f24387332bb17e0171348497c69442" in ledger
    assert "2026-08-21" in ledger
    assert "HISTORICAL SNAPSHOT != CURRENT RECERTIFICATION" in ledger


def test_full_closure_ledger_names_all_19_current_families() -> None:
    ledger = _full_closure_ledger()

    assert len(_EXPECTED_CURRENT_FAMILIES) == 19
    assert len(set(_EXPECTED_CURRENT_FAMILIES)) == 19
    for family in _EXPECTED_CURRENT_FAMILIES:
        assert f"`{family}`" in ledger


def test_full_closure_ledger_re_adjudicates_exact_unresolved_dispositions() -> None:
    ledger = _full_closure_ledger()
    observed: dict[str, str] = {}
    for line in ledger.splitlines():
        if not line.startswith("| UMI13-UNR-"):
            continue
        cells = tuple(cell.strip() for cell in line.strip().strip("|").split("|"))
        assert len(cells) == 3
        unresolved_ref, disposition, _evidence_rule = cells
        assert unresolved_ref not in observed
        observed[unresolved_ref] = disposition

    assert len(observed) == 24
    assert observed == dict(_EXPECTED_UNR_DISPOSITIONS)


def test_full_closure_ledger_freezes_current_carry_forward_snapshot() -> None:
    ledger = _full_closure_ledger()
    for snapshot in _EXPECTED_CARRY_FORWARD_SNAPSHOTS:
        assert snapshot in ledger


def test_open_preparatory_candidates_cannot_count_as_current_main_owners() -> None:
    ledger = _full_closure_ledger()

    assert "OPEN/DRAFT CANDIDATE != CURRENT MAIN OWNER" in ledger
    for pr_number in (386, 389, 391, 393, 395, 397, 399, 401):
        assert f"#{pr_number}" in ledger

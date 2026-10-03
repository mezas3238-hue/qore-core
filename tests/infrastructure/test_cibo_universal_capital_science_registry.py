from __future__ import annotations

import inspect
from decimal import Decimal

from qore.infrastructure.cibo_universal_capital_science_registry import (
    GENC_REGISTRY,
    UniversalCapitalScienceContext,
    evaluate_universal_capital_science,
)


def _context(
    *,
    account_pool_enabled: bool = True,
    compound_settlement_count: int = 4,
) -> UniversalCapitalScienceContext:
    return UniversalCapitalScienceContext(
        epoch_count=20,
        selected_count=8,
        realized_profit_settlement_count=5,
        compound_settlement_count=compound_settlement_count,
        compound_rejected_count=4,
        cross_trader_deployment_count=2 if account_pool_enabled else 0,
        core_ending_capital_usd=Decimal("64"),
        compound_incremental_pnl_usd=Decimal("2.5"),
        total_compound_risk_usd=Decimal("3"),
        total_compound_margin_usd=Decimal("7"),
        total_provider_cost_usd=Decimal("0.5"),
        protected_loss_reserve_usd=Decimal("0.75"),
        account_pool_enabled=account_pool_enabled,
        rational_redeploy_gate_enabled=True,
        qore_risk_sovereign=True,
        fixed_leverage_experiment=False,
        burned_adaptive_research=True,
    )


def test_registry_contains_exact_gen_c1_through_gen_c14() -> None:
    assert tuple(item.code for item in GENC_REGISTRY) == tuple(
        f"GEN-C{i}" for i in range(1, 15)
    )


def test_universal_evaluation_never_emits_not_integrated() -> None:
    rows = evaluate_universal_capital_science(_context())
    assert len(rows) == 14
    assert all(row["universal_contract"] is True for row in rows)
    assert all(row["identity_predicate_used"] is False for row in rows)
    assert all(row["status"] != "NOT_INTEGRATED" for row in rows)


def test_account_pool_and_trader_local_use_same_gen_c_surface() -> None:
    account = evaluate_universal_capital_science(
        _context(account_pool_enabled=True)
    )
    local = evaluate_universal_capital_science(
        _context(account_pool_enabled=False)
    )
    assert tuple(row["function_code"] for row in account) == tuple(
        row["function_code"] for row in local
    )
    account_c3 = next(row for row in account if row["function_code"] == "GEN-C3")
    local_c3 = next(row for row in local if row["function_code"] == "GEN-C3")
    assert account_c3["status"] == "APPLIED"
    assert local_c3["status"] == "JUSTIFIED_NOT_APPLICABLE"


def test_accountability_exposes_complete_observability_contract() -> None:
    required = {
        "eligible_epochs",
        "invoked_count",
        "applied_count",
        "fail_closed_count",
        "not_applicable_count",
        "decision_changed_count",
        "risk_delta_usd",
        "margin_delta_usd",
        "capital_source_usage",
        "incremental_pnl_attribution_usd",
        "reason_distribution",
    }
    for row in evaluate_universal_capital_science(_context()):
        assert required <= set(row)


def test_registry_api_has_no_trader_symbol_or_timeframe_selector() -> None:
    signature = inspect.signature(evaluate_universal_capital_science)
    assert tuple(signature.parameters) == ("context",)
    context_fields = set(UniversalCapitalScienceContext.__dataclass_fields__)
    forbidden = {
        "trader",
        "trader_id",
        "symbol",
        "qore_symbol",
        "asset",
        "timeframe",
    }
    assert not (context_fields & forbidden)


def test_advanced_engines_are_present_without_fabricated_current_authority() -> None:
    rows = evaluate_universal_capital_science(_context())
    by_code = {row["function_code"]: row for row in rows}
    for code in ("GEN-C8", "GEN-C9", "GEN-C10", "GEN-C11", "GEN-C12", "GEN-C13", "GEN-C14"):
        assert by_code[code]["status"] == "JUSTIFIED_NOT_APPLICABLE"
        assert by_code[code]["applied_count"] == 0
        assert by_code[code]["implementation_module"].startswith(
            "qore.infrastructure."
        )

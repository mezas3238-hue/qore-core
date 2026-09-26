from decimal import Decimal

from qore.infrastructure.account_wide_risk import TraderLineage
from qore.infrastructure.cibo_economic_floor import (
    ReconciledPositionEconomics,
    evaluate_economic_floor,
)


def _economics(**overrides: object) -> ReconciledPositionEconomics:
    values: dict[str, object] = {
        "trader_id": TraderLineage.VT31_NAS100,
        "signal_fingerprint": "signal-1",
        "realized_net_pnl_usd": Decimal("0"),
        "remaining_stop_worst_case_pnl_usd": Decimal("-10"),
        "future_cost_reserve_usd": Decimal("1"),
        "slippage_reserve_usd": Decimal("1"),
        "broker_position_reconciled": True,
        "protection_reconciled": True,
        "mutation_outcome_unknown": False,
    }
    values.update(overrides)
    return ReconciledPositionEconomics(**values)  # type: ignore[arg-type]


def test_negative_worst_case_reports_base_capital_at_risk() -> None:
    result = evaluate_economic_floor(_economics())

    assert result.evidence_sufficient is True
    assert result.net_economic_floor_usd == Decimal("-12")
    assert result.base_capital_at_risk_usd == Decimal("12")
    assert result.proven_self_financing_capacity_usd == 0
    assert result.base_recovered is False


def test_realized_profit_first_offsets_remaining_open_loss_and_costs() -> None:
    result = evaluate_economic_floor(
        _economics(
            realized_net_pnl_usd=Decimal("20"),
            remaining_stop_worst_case_pnl_usd=Decimal("-5"),
            future_cost_reserve_usd=Decimal("1"),
            slippage_reserve_usd=Decimal("1"),
        )
    )

    assert result.net_economic_floor_usd == Decimal("13")
    assert result.proven_self_financing_capacity_usd == Decimal("13")
    assert result.base_capital_at_risk_usd == 0
    assert result.base_recovered is True


def test_protected_open_profit_contributes_only_when_in_worst_case_floor() -> None:
    result = evaluate_economic_floor(
        _economics(
            realized_net_pnl_usd=Decimal("2"),
            remaining_stop_worst_case_pnl_usd=Decimal("8"),
            future_cost_reserve_usd=Decimal("1"),
            slippage_reserve_usd=Decimal("1"),
        )
    )

    assert result.protected_open_floor_usd == Decimal("8")
    assert result.net_economic_floor_usd == Decimal("8")
    assert result.proven_self_financing_capacity_usd == Decimal("8")


def test_positive_floating_pnl_is_irrelevant_without_reconciled_protection() -> None:
    result = evaluate_economic_floor(
        _economics(
            remaining_stop_worst_case_pnl_usd=Decimal("20"),
            protection_reconciled=False,
        )
    )

    assert result.evidence_sufficient is False
    assert result.proven_self_financing_capacity_usd is None
    assert result.base_recovered is False


def test_unknown_mutation_fails_closed_even_if_floor_looks_profitable() -> None:
    result = evaluate_economic_floor(
        _economics(
            realized_net_pnl_usd=Decimal("30"),
            remaining_stop_worst_case_pnl_usd=Decimal("10"),
            mutation_outcome_unknown=True,
        )
    )

    assert result.evidence_sufficient is False
    assert result.base_recovered is False
    assert "unknown" in result.reason


def test_cost_reserve_can_keep_base_unrecovered() -> None:
    result = evaluate_economic_floor(
        _economics(
            realized_net_pnl_usd=Decimal("5"),
            remaining_stop_worst_case_pnl_usd=Decimal("0"),
            future_cost_reserve_usd=Decimal("3"),
            slippage_reserve_usd=Decimal("3"),
        )
    )

    assert result.net_economic_floor_usd == Decimal("-1")
    assert result.base_capital_at_risk_usd == Decimal("1")
    assert result.base_recovered is False

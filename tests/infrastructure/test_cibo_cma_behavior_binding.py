from datetime import UTC, datetime
from decimal import Decimal

from qore.infrastructure.cibo_cma_behavior_binding import (
    economic_floor_from_behavior_case,
)
from qore.infrastructure.ctrader_demo_live_behavior_lab import LiveBehaviorCaseReport


NOW = datetime(2026, 9, 26, 12, 0, tzinfo=UTC)


def _report(
    *,
    realized: str | None = None,
    remaining_stop: str | None = "-10",
    settlement_events: tuple[str, ...] = (),
) -> LiveBehaviorCaseReport:
    return LiveBehaviorCaseReport(
        case_id="signal:" + "a" * 64,
        trader="VT31_NAS100",
        symbol="NAS100",
        first_observed_at=NOW,
        last_observed_at=NOW,
        event_count=1,
        stages={},
        event_names=(),
        requested_volumes=("0.04",),
        requested_stop_risks=("10",),
        protection_events=(),
        partial_close_events=(),
        exit_events=(),
        fault_events=(),
        settlement_events=settlement_events,
        realized_net_pnl=realized,
        settlement_prices=(),
        settled_source_volumes=(),
        estimated_initial_risk_pnl="10",
        estimated_remaining_stop_pnl=remaining_stop,
        estimated_economic_floor_pnl=None,
        estimated_economic_floor_r=None,
        path_sample_count=1,
        max_unrealized_pnl=None,
        min_unrealized_pnl=None,
        max_favorable_price_delta=None,
        max_adverse_price_delta=None,
        stop_history=(),
        volume_history=(),
        observations=(),
    )


def test_open_case_binds_realized_and_remaining_stop_to_floor() -> None:
    result = economic_floor_from_behavior_case(
        _report(realized="15", remaining_stop="-4"),
        position_open=True,
        broker_position_reconciled=True,
        protection_reconciled=True,
        mutation_outcome_unknown=False,
        future_cost_reserve_usd=Decimal("1"),
    )

    assert result.evidence_sufficient is True
    assert result.net_economic_floor_usd == Decimal("10")
    assert result.base_recovered is True
    assert result.proven_self_financing_capacity_usd == Decimal("10")


def test_open_case_without_remaining_stop_fails_closed() -> None:
    result = economic_floor_from_behavior_case(
        _report(realized="15", remaining_stop=None),
        position_open=True,
        broker_position_reconciled=True,
        protection_reconciled=True,
        mutation_outcome_unknown=False,
    )

    assert result.evidence_sufficient is False
    assert result.base_recovered is False


def test_unreconciled_protection_fails_closed_even_when_estimate_is_positive() -> None:
    result = economic_floor_from_behavior_case(
        _report(realized="20", remaining_stop="5"),
        position_open=True,
        broker_position_reconciled=True,
        protection_reconciled=False,
        mutation_outcome_unknown=False,
    )

    assert result.evidence_sufficient is False
    assert result.proven_self_financing_capacity_usd is None


def test_closed_case_requires_final_exit_settlement() -> None:
    result = economic_floor_from_behavior_case(
        _report(realized="12", remaining_stop=None),
        position_open=False,
        broker_position_reconciled=True,
        protection_reconciled=True,
        mutation_outcome_unknown=False,
    )

    assert result.evidence_sufficient is False


def test_closed_case_with_exit_settlement_has_zero_remaining_risk() -> None:
    result = economic_floor_from_behavior_case(
        _report(
            realized="12",
            remaining_stop=None,
            settlement_events=("CTRADER_DEMO_EXIT_SETTLEMENT",),
        ),
        position_open=False,
        broker_position_reconciled=True,
        protection_reconciled=True,
        mutation_outcome_unknown=False,
        future_cost_reserve_usd=Decimal("2"),
    )

    assert result.evidence_sufficient is True
    assert result.net_economic_floor_usd == Decimal("10")
    assert result.base_capital_at_risk_usd == 0


def test_mutation_unknown_blocks_behavior_floor() -> None:
    result = economic_floor_from_behavior_case(
        _report(realized="20", remaining_stop="5"),
        position_open=True,
        broker_position_reconciled=True,
        protection_reconciled=True,
        mutation_outcome_unknown=True,
    )

    assert result.evidence_sufficient is False
    assert "unknown" in result.reason

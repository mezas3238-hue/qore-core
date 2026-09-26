from datetime import UTC, datetime

from qore.infrastructure.cibo_cma_shadow_floor import (
    CmaShadowFloorStatus,
    classify_behavior_case,
)
from qore.infrastructure.ctrader_demo_live_behavior_lab import LiveBehaviorCaseReport


NOW = datetime(2026, 9, 26, 12, 0, tzinfo=UTC)


def _report(
    *,
    realized: str | None,
    settled: bool,
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
        exit_events=("CTRADER_DEMO_EXIT_SETTLEMENT",) if settled else (),
        fault_events=(),
        settlement_events=("CTRADER_DEMO_EXIT_SETTLEMENT",) if settled else (),
        realized_net_pnl=realized,
        settlement_prices=(),
        settled_source_volumes=(),
        estimated_initial_risk_pnl="10",
        estimated_remaining_stop_pnl=None,
        estimated_economic_floor_pnl=None,
        estimated_economic_floor_r=None,
        path_sample_count=0,
        max_unrealized_pnl=None,
        min_unrealized_pnl=None,
        max_favorable_price_delta=None,
        max_adverse_price_delta=None,
        stop_history=(),
        volume_history=(),
        observations=(),
    )


def test_closed_positive_settlement_recovers_base() -> None:
    observation = classify_behavior_case(_report(realized="64.06", settled=True))

    assert observation.status is CmaShadowFloorStatus.BASE_RECOVERED
    assert str(observation.net_economic_floor_usd) == "64.06"
    assert str(observation.self_financing_capacity_usd) == "64.06"


def test_closed_loss_does_not_recover_base() -> None:
    observation = classify_behavior_case(_report(realized="-10.56", settled=True))

    assert observation.status is CmaShadowFloorStatus.BASE_NOT_RECOVERED
    assert str(observation.base_capital_at_risk_usd) == "10.56"
    assert str(observation.self_financing_capacity_usd) == "0"


def test_open_case_remains_insufficient_even_with_historical_estimate() -> None:
    report = _report(realized="20", settled=False)
    object.__setattr__(report, "estimated_remaining_stop_pnl", "5")
    object.__setattr__(report, "estimated_economic_floor_pnl", "25")

    observation = classify_behavior_case(report)

    assert observation.status is CmaShadowFloorStatus.INSUFFICIENT_EVIDENCE
    assert observation.self_financing_capacity_usd is None

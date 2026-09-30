from __future__ import annotations

from decimal import Decimal

from qore.infrastructure.trader_lab.capitalizer_v49_development_economics import (
    V49EconomicTrade,
)
from qore.infrastructure.trader_lab.capitalizer_v50_cognitive_geometry_economics import (
    V50GTrade,
)
from qore.infrastructure.trader_lab.capitalizer_v51_multi_era_repair import (
    _certification_diagnostic,
    _metrics,
    _preservation,
)


def _base(entry: str, realized: str, reason: str) -> V49EconomicTrade:
    return V49EconomicTrade(
        symbol="EURUSD",
        session="LONDON",
        operating_date="2015-01-05",
        ordinal_candidate_at=entry,
        direction="LONG",
        entry_at=entry,
        exit_at=entry,
        entry_price="100",
        stop_price="99",
        target_price="102",
        planned_reward_r="2",
        realized_gross_r=realized,
        exit_reason=reason,
        m1_bars_held=1,
        trigger_family="FVG_RETRACE_CISD",
        h1_state_basis="TEST",
    )


def _candidate(entry: str, realized: str) -> V50GTrade:
    return V50GTrade(
        policy="COGNITIVE_GEOMETRY",
        symbol="EURUSD",
        session="LONDON",
        operating_date="2015-01-05",
        entry_at=entry,
        exit_at=entry,
        entry_price="100",
        stop_price="99.5",
        target_price="101.5",
        planned_reward_r="3",
        realized_gross_r=realized,
        exit_reason="TARGET" if Decimal(realized) > 0 else "STOP",
        m1_bars_held=1,
        cognitive_disposition="PASS_TO_COMPETITION",
        geometry_decision="READY",
        trigger_family="FVG_RETRACE_CISD",
        h1_basis="TEST",
    )


def test_preservation_reports_winner_mass_and_loss_recall() -> None:
    baseline = (
        _base("2015-01-05T10:00:00+00:00", "2", "TARGET"),
        _base("2015-01-05T10:01:00+00:00", "-1", "STOP"),
        _base("2015-01-05T10:02:00+00:00", "1", "TARGET"),
    )
    candidate = (
        _candidate("2015-01-05T10:00:00+00:00", "3"),
        _candidate("2015-01-05T10:02:00+00:00", "2"),
    )
    result = _preservation(baseline, candidate)
    assert Decimal(result["winner_count_preservation"]) == Decimal("1")
    assert Decimal(result["winner_r_preservation"]) == Decimal("1")
    assert Decimal(result["loss_recall"]) == Decimal("1")


def test_metrics_expose_certification_axes() -> None:
    rows = (
        _candidate("2015-01-05T10:00:00+00:00", "2"),
        _candidate("2015-01-06T10:00:00+00:00", "2"),
        _candidate("2015-01-07T10:00:00+00:00", "-1"),
    )
    metrics = _metrics(rows)
    assert Decimal(metrics["profit_factor"]) == Decimal("4")
    assert Decimal(metrics["expectancy_r"]) > 0
    assert Decimal(metrics["payoff_ratio"]) == Decimal("2")
    diagnostic = _certification_diagnostic(metrics)
    assert diagnostic["pf_ge_1_50"] is True
    assert diagnostic["expectancy_positive"] is True
    assert diagnostic["dd_le_10r"] is True
    assert diagnostic["payoff_ge_1_20"] is True


def test_preservation_does_not_credit_winner_that_turns_into_loss() -> None:
    baseline = (
        _base("2015-01-05T10:00:00+00:00", "2", "TARGET"),
        _base("2015-01-05T10:01:00+00:00", "-1", "STOP"),
    )
    candidate = (
        _candidate("2015-01-05T10:00:00+00:00", "-1"),
        _candidate("2015-01-05T10:01:00+00:00", "1"),
    )
    result = _preservation(baseline, candidate)
    assert Decimal(result["winner_count_preservation"]) == Decimal("0")
    assert Decimal(result["winner_r_preservation"]) == Decimal("0")
    assert Decimal(result["loss_recall"]) == Decimal("1")

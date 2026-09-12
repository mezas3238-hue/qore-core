from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from qore.infrastructure.trader_lab.vt08_b01_risk_economic_replay_r3_11 import (
    TradeObservation,
)
from qore.infrastructure.trader_lab.vt08_prop_firm_monte_carlo_r3_11 import (
    DayRecord,
    PortfolioPolicy,
    PropFirmMonteCarloError,
    adaptive_risk_multiplier,
    build_daily_series,
    build_effective_trades,
    moving_block_sample,
    run_monte_carlo,
    simulate_path,
)


def _trade(
    at: datetime,
    *,
    exit_hours: int = 4,
    symbol: str = "GBPUSD",
    side: str = "short",
    exit_price: Decimal = Decimal("1.0800"),
) -> TradeObservation:
    return TradeObservation(
        window="baseline-2024-2026",
        symbol=symbol,
        side=side,
        signal_at=at,
        exited_at=at + timedelta(hours=exit_hours),
        entry=Decimal("1.1000"),
        stop=Decimal("1.1100"),
        target=Decimal("1.0800"),
        exit_price=exit_price,
        exit_reason="target" if exit_price < Decimal("1.1000") else "stop",
    )


def test_policy_rejects_risk_above_heat() -> None:
    with pytest.raises(PropFirmMonteCarloError, match="A risk"):
        PortfolioPolicy("bad", a_risk_bps=60, gbpjpy_risk_bps=20, portfolio_heat_bps=50)


def test_adaptive_multiplier_scales_up_with_clean_profit_and_down_with_drawdown() -> None:
    at_start = adaptive_risk_multiplier(equity=1.0, peak_equity=1.0)
    at_profit = adaptive_risk_multiplier(equity=1.10, peak_equity=1.10)
    after_drawdown = adaptive_risk_multiplier(equity=1.05, peak_equity=1.10)
    assert at_start == pytest.approx(1.0)
    assert at_profit == pytest.approx(1.5)
    assert after_drawdown < at_start


def test_adaptive_multiplier_rejects_non_positive_equity() -> None:
    with pytest.raises(PropFirmMonteCarloError, match="equity inputs"):
        adaptive_risk_multiplier(equity=0.0, peak_equity=1.0)


def test_dynamic_authorization_enforces_heat_cap() -> None:
    at = datetime(2026, 1, 5, 12, tzinfo=UTC)
    trades = (_trade(at), _trade(at + timedelta(minutes=1)), _trade(at + timedelta(minutes=2)))
    policy = PortfolioPolicy("test", a_risk_bps=30, gbpjpy_risk_bps=20, portfolio_heat_bps=50)
    effective = build_effective_trades(
        trades,
        {},
        policy=policy,
        cost_bps=Decimal("0"),
        portfolio="a",
    )
    daily = build_daily_series(effective)
    result = simulate_path(daily, policy=policy, calendar_months=True)
    assert result.max_portfolio_heat_bps <= 50.0 + 1e-9
    assert result.max_authorized_risk_bps <= 30.0 + 1e-9


def test_daily_series_keeps_zero_business_days_between_opportunities() -> None:
    monday = datetime(2026, 1, 5, 12, tzinfo=UTC)
    wednesday = datetime(2026, 1, 7, 12, tzinfo=UTC)
    policy = PortfolioPolicy("test", 25, 20, 90)
    effective = build_effective_trades(
        (_trade(monday), _trade(wednesday)),
        {},
        policy=policy,
        cost_bps=Decimal("0"),
        portfolio="a",
    )
    daily = build_daily_series(effective)
    assert len(daily) == 3
    assert len(daily[0].trades) == 1
    assert daily[1].trades == ()
    assert len(daily[2].trades) == 1


def test_internal_daily_guard_can_trip_without_external_breach() -> None:
    result = simulate_path((DayRecord((), 0.03),))
    assert result.internal_breach is True
    assert result.external_breach is False


def test_external_max_loss_breach_is_detected_after_realized_loss() -> None:
    result = simulate_path((DayRecord((-0.11,), 0.01),))
    assert result.external_breach is True
    assert result.terminal_return < -0.10


def test_target_hit_is_recorded_before_internal_breach() -> None:
    records = tuple(DayRecord((0.01,), 0.0025) for _ in range(12))
    result = simulate_path(records)
    assert result.targets_hit_day[0] is not None
    assert result.targets_hit_before_internal_day[0] == result.targets_hit_day[0]
    assert result.external_breach is False


def test_calendar_month_reporting_rebases_each_month_to_opening_equity() -> None:
    starts = (
        datetime(2026, 1, 5, 12, tzinfo=UTC),
        datetime(2026, 2, 2, 12, tzinfo=UTC),
    )
    policy = PortfolioPolicy("test", 25, 20, 90)
    effective = build_effective_trades(
        tuple(_trade(at) for at in starts),
        {},
        policy=policy,
        cost_bps=Decimal("0"),
        portfolio="a",
    )
    result = simulate_path(build_daily_series(effective), policy=policy, calendar_months=True)
    assert [month.key for month in result.months] == ["2026-01", "2026-02"]
    assert all(month.return_fraction > 0 for month in result.months)
    assert all(month.average_authorized_risk_bps > 0 for month in result.months)


def test_moving_block_and_monte_carlo_are_seed_deterministic() -> None:
    records = (
        DayRecord((0.002,), 0.0025),
        DayRecord((-0.001,), 0.0025),
        DayRecord((), 0.0),
        DayRecord((0.003,), 0.0025),
    )
    first = run_monte_carlo(records, paths=50, horizon_days=20, block_days=2, seed=123)
    second = run_monte_carlo(records, paths=50, horizon_days=20, block_days=2, seed=123)
    assert first == second
    assert "monthly_performance" in first
    assert "risk_dynamics" in first


def test_monte_carlo_monthly_output_contains_requested_governance_metrics() -> None:
    records = tuple(DayRecord((0.001,), 0.0025) for _ in range(42))
    report = run_monte_carlo(records, paths=20, horizon_days=42, block_days=5, seed=7)
    monthly = report["monthly_performance"]
    assert isinstance(monthly, dict)
    assert "return" in monthly
    assert "positive_month_probability" in monthly
    assert "max_drawdown" in monthly
    assert "growth_efficiency_return_over_drawdown" in monthly
    assert "rolling_3_month_return" in monthly
    assert "rolling_6_month_return" in monthly
    assert "sleeve_monthly_contribution" in monthly


def test_moving_block_rejects_block_larger_than_series() -> None:
    import random

    with pytest.raises(PropFirmMonteCarloError, match="block cannot exceed"):
        moving_block_sample(
            (DayRecord((), 0.0),), horizon_days=2, block_days=2, rng=random.Random(1)
        )

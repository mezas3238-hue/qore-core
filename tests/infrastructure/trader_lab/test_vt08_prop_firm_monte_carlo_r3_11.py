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
    build_daily_series,
    build_effective_trades,
    moving_block_sample,
    run_monte_carlo,
    simulate_path,
)


def _trade(at: datetime, *, exit_hours: int = 4) -> TradeObservation:
    return TradeObservation(
        window="baseline-2024-2026",
        symbol="GBPUSD",
        side="short",
        signal_at=at,
        exited_at=at + timedelta(hours=exit_hours),
        entry=Decimal("1.1000"),
        stop=Decimal("1.1100"),
        target=Decimal("1.0800"),
        exit_price=Decimal("1.0800"),
        exit_reason="target",
    )


def test_policy_rejects_risk_above_heat() -> None:
    with pytest.raises(PropFirmMonteCarloError, match="A risk"):
        PortfolioPolicy("bad", a_risk_bps=60, gbpjpy_risk_bps=20, portfolio_heat_bps=50)


def test_effective_trade_allocation_enforces_heat_cap() -> None:
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
    assert [item.effective_risk_bps for item in effective] == [30, 20]


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
    assert len(daily[0].trade_returns) == 1
    assert daily[1].trade_returns == ()
    assert len(daily[2].trade_returns) == 1


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


def test_moving_block_rejects_block_larger_than_series() -> None:
    import random

    with pytest.raises(PropFirmMonteCarloError, match="block cannot exceed"):
        moving_block_sample(
            (DayRecord((), 0.0),), horizon_days=2, block_days=2, rng=random.Random(1)
        )

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

import pytest

from qore.infrastructure.trader_lab.vt08_b01_risk_economic_replay_r3_11 import (
    BrokerVolumeConstraints,
    TradeObservation,
)
from qore.infrastructure.trader_lab.vt08_official_adaptive_monte_carlo_r3_12 import (
    PRIMARY_POLICY,
    AdaptivePreparedDay,
    AdaptivePreparedTrade,
    OpenPosition,
    RiskMemory,
    _authorize,
    apply_hysteresis,
    simulate_adaptive_path,
    target_risk_bps,
)
from qore.infrastructure.trader_lab.vt08_official_monte_carlo_r3_11 import (
    PORTFOLIOS,
    PreparedTrade,
    paired_block_indices,
)
from qore.infrastructure.trader_lab.vt08_prop_firm_profiles_r3_12 import (
    FTMO_2STEP_2026_09_12,
    FUNDEDNEXT_STELLAR_2STEP_2026_09_12,
)


def _source(
    *, symbol: str = "GBPUSD", side: str = "short", at: datetime | None = None
) -> TradeObservation:
    signal = at or datetime(2026, 1, 5, 12, tzinfo=UTC)
    return TradeObservation(
        window="consumed-test",
        symbol=symbol,
        side=side,
        signal_at=signal,
        exited_at=signal + timedelta(hours=1),
        entry=Decimal("1.1000"),
        stop=Decimal("1.1100"),
        target=Decimal("1.0800"),
        exit_price=Decimal("1.0800"),
        exit_reason="target",
    )


def _trade(
    *,
    symbol: str = "GBPUSD",
    side: str = "short",
    per_unit_loss: Decimal = Decimal("1"),
    per_unit_gross: Decimal = Decimal("2"),
    per_unit_cost: Decimal = Decimal("0"),
    constraints: BrokerVolumeConstraints | None = None,
) -> AdaptivePreparedTrade:
    source = _source(symbol=symbol, side=side)
    broker = constraints or BrokerVolumeConstraints(
        symbol=symbol,
        min_quantity=Decimal("1"),
        max_quantity=Decimal("1000000"),
        step_quantity=Decimal("1"),
    )
    prepared = PreparedTrade(
        source=source,
        entry_offset=timedelta(hours=12),
        duration=timedelta(hours=1),
        per_unit_loss_usd=per_unit_loss,
        per_unit_net_pnl_usd=per_unit_gross - per_unit_cost,
        constraints=broker,
    )
    sleeve = "gbpjpy" if symbol == "GBPJPY" else "a"
    return AdaptivePreparedTrade(prepared, sleeve, per_unit_gross, per_unit_cost)


def test_provider_profiles_are_versioned_and_keep_distinct_targets_and_days() -> None:
    ftmo = FTMO_2STEP_2026_09_12
    funded = FUNDEDNEXT_STELLAR_2STEP_2026_09_12
    assert ftmo.daily_loss_limit_fraction == Decimal("0.05")
    assert ftmo.maximum_loss_limit_fraction == Decimal("0.10")
    assert ftmo.phase1_profit_target_fraction == Decimal("0.10")
    assert ftmo.minimum_trading_days_per_phase == 4
    assert ftmo.daily_reset_timezone == "Europe/Prague"
    assert funded.phase1_profit_target_fraction == Decimal("0.08")
    assert funded.minimum_trading_days_per_phase == 5
    assert funded.daily_reset_timezone == "FundedNextServerTime"
    assert ftmo.daily_loss_floor_usd(Decimal("102000")) == Decimal("97000.00")


def test_cushion_monotonicity_and_drawdown_monotonicity() -> None:
    policy = PRIMARY_POLICY
    start = Decimal("100000")
    base = target_risk_bps(
        policy, sleeve="a", equity=start, peak_equity=start, starting_equity=start
    )
    profit = target_risk_bps(
        policy,
        sleeve="a",
        equity=Decimal("105000"),
        peak_equity=Decimal("105000"),
        starting_equity=start,
    )
    drawdown = target_risk_bps(
        policy,
        sleeve="a",
        equity=Decimal("102000"),
        peak_equity=Decimal("105000"),
        starting_equity=start,
    )
    assert profit >= base
    assert drawdown <= profit


def test_hysteresis_prevents_churn_and_downshift_is_faster_than_upshift() -> None:
    policy = PRIMARY_POLICY
    previous = Decimal("25")
    assert apply_hysteresis(
        policy, previous_bps=previous, target_bps_value=Decimal("25.10")
    ) == Decimal("25")
    up = apply_hysteresis(
        policy, previous_bps=previous, target_bps_value=Decimal("30")
    )
    down = apply_hysteresis(
        policy, previous_bps=previous, target_bps_value=Decimal("10")
    )
    assert up - previous == policy.upshift_step_bps
    assert previous - down == policy.downshift_step_bps
    assert previous - down > up - previous


def test_provider_daily_and_maximum_headroom_can_reject_new_risk() -> None:
    profile = FTMO_2STEP_2026_09_12
    trade = _trade()
    daily = _authorize(
        trade=trade,
        policy=PRIMARY_POLICY,
        profile=profile,
        memory=RiskMemory.from_policy(PRIMARY_POLICY),
        balance=Decimal("95100"),
        peak_equity=Decimal("100000"),
        reset_balance=Decimal("100000"),
        open_positions=(),
    )
    assert daily.outcome == "REJECT"
    assert "provider_daily" in daily.reasons

    maximum = _authorize(
        trade=trade,
        policy=PRIMARY_POLICY,
        profile=profile,
        memory=RiskMemory.from_policy(PRIMARY_POLICY),
        balance=Decimal("90100"),
        peak_equity=Decimal("100000"),
        reset_balance=Decimal("91000"),
        open_positions=(),
    )
    assert maximum.outcome == "REJECT"
    assert "provider_maximum" in maximum.reasons


def test_open_bounded_loss_and_correlation_reduce_available_risk() -> None:
    profile = FTMO_2STEP_2026_09_12
    trade = _trade(symbol="GBPJPY", side="short")
    open_position = OpenPosition(
        exit_at=datetime(2026, 1, 5, 14, tzinfo=UTC),
        symbol="GBPUSD",
        sleeve="a",
        quantity=Decimal("1"),
        bounded_loss_usd=Decimal("490"),
        gross_pnl_usd=Decimal(0),
        cost_usd=Decimal(0),
        net_pnl_usd=Decimal(0),
        net_r=Decimal(0),
        authorized_risk_bps=Decimal("49"),
    )
    result = _authorize(
        trade=trade,
        policy=PRIMARY_POLICY,
        profile=profile,
        memory=RiskMemory.from_policy(PRIMARY_POLICY),
        balance=Decimal("100000"),
        peak_equity=Decimal("100000"),
        reset_balance=Decimal("100000"),
        open_positions=(open_position,),
    )
    assert result.outcome in {"REDUCE", "REJECT"}
    assert "correlation_heat" in result.reasons


def test_broker_minimum_quantity_is_fail_closed() -> None:
    constraints = BrokerVolumeConstraints(
        symbol="GBPUSD",
        min_quantity=Decimal("1000"),
        max_quantity=Decimal("1000000"),
        step_quantity=Decimal("1000"),
    )
    trade = _trade(per_unit_loss=Decimal("10"), constraints=constraints)
    result = _authorize(
        trade=trade,
        policy=PRIMARY_POLICY,
        profile=FTMO_2STEP_2026_09_12,
        memory=RiskMemory.from_policy(PRIMARY_POLICY),
        balance=Decimal("100000"),
        peak_equity=Decimal("100000"),
        reset_balance=Decimal("100000"),
        open_positions=(),
    )
    assert result.outcome == "REJECT"
    assert "broker_quantity" in result.reasons


def test_paired_sampling_is_seed_deterministic_and_common_across_portfolios() -> None:
    first = paired_block_indices(100, paths=5, horizon_days=20, block_days=5, seed=99)
    second = paired_block_indices(100, paths=5, horizon_days=20, block_days=5, seed=99)
    assert first == second
    assert set(PORTFOLIOS) == {
        "A_CORE",
        "GBPJPY_RETURN_ENHANCER",
        "B_COMBINED_PORTFOLIO",
    }


def test_monthly_rebase_and_compounding_are_preserved() -> None:
    trade = _trade(per_unit_gross=Decimal("2"))
    days = tuple(
        AdaptivePreparedDay(date(2026, 1, 1) + timedelta(days=index), (trade,))
        for index in range(42)
    )
    result = simulate_adaptive_path(
        days,
        tuple(range(42)),
        portfolio="A_CORE",
        policy=PRIMARY_POLICY,
        profile=FTMO_2STEP_2026_09_12,
    )
    assert len(result.months) == 2
    assert result.months[0].net_return > 0
    assert result.months[1].net_return > 0
    assert result.months[1].start_equity_usd == pytest.approx(
        result.months[0].end_equity_usd
    )
    compounded = (1 + result.months[0].net_return) * (1 + result.months[1].net_return) - 1
    assert result.terminal_return == pytest.approx(compounded)
    assert result.max_heat_bps <= float(PRIMARY_POLICY.portfolio_heat_bps) + 1e-6

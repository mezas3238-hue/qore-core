from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

from qore.infrastructure.trader_lab.vt08_b01_risk_economic_replay_r3_11 import (
    BrokerVolumeConstraints,
    TradeObservation,
)
from qore.infrastructure.trader_lab.vt08_official_monte_carlo_r3_11 import (
    BLOCK_DAYS,
    HORIZON_DAYS,
    PATHS,
    PORTFOLIOS,
    SEED,
    PreparedDay,
    PreparedTrade,
    paired_block_indices,
    simulate_portfolio_path,
)


def _prepared(symbol: str, side: str, offset: int = 0) -> PreparedTrade:
    signal = datetime(2024, 1, 2, 9, tzinfo=UTC) + timedelta(minutes=offset)
    observation = TradeObservation(
        window="baseline-2024-2026",
        symbol=symbol,
        side=side,
        signal_at=signal,
        exited_at=signal + timedelta(hours=2),
        entry=Decimal("1.1000"),
        stop=Decimal("1.1100"),
        target=Decimal("1.0800"),
        exit_price=Decimal("1.0800"),
        exit_reason="target",
    )
    return PreparedTrade(
        source=observation,
        entry_offset=timedelta(hours=9, minutes=offset),
        duration=timedelta(hours=2),
        per_unit_loss_usd=Decimal("0.01"),
        per_unit_net_pnl_usd=Decimal("0.02"),
        constraints=BrokerVolumeConstraints(
            symbol=symbol,
            min_quantity=Decimal("1000"),
            max_quantity=Decimal("5000000"),
            step_quantity=Decimal("1000"),
        ),
    )


def test_official_freeze_is_exact() -> None:
    assert PATHS == 10_000
    assert HORIZON_DAYS == 250
    assert BLOCK_DAYS == 20
    assert SEED == 20260912
    assert PORTFOLIOS == {
        "A_CORE": (("AUDJPY", "short"), ("GBPUSD", "short")),
        "GBPJPY_RETURN_ENHANCER": (("GBPJPY", "long"), ("GBPJPY", "short")),
        "B_COMBINED_PORTFOLIO": (
            ("AUDJPY", "short"),
            ("GBPUSD", "short"),
            ("GBPJPY", "long"),
            ("GBPJPY", "short"),
        ),
    }


def test_paired_block_draw_is_deterministic_and_keeps_twenty_day_blocks() -> None:
    first = paired_block_indices(80, paths=3, horizon_days=45, block_days=20, seed=7)
    second = paired_block_indices(80, paths=3, horizon_days=45, block_days=20, seed=7)
    assert first == second
    assert all(len(path) == 45 for path in first)
    for path in first:
        assert all(path[index + 1] == path[index] + 1 for index in range(19))


def test_chronological_replay_enforces_heat_and_portfolio_identity() -> None:
    day = PreparedDay(
        source_day=datetime(2024, 1, 2, tzinfo=UTC).date(),
        trades=(
            _prepared("AUDJPY", "short", 0),
            _prepared("GBPUSD", "short", 1),
            _prepared("GBPJPY", "long", 2),
            _prepared("GBPJPY", "short", 3),
        ),
    )
    a = simulate_portfolio_path((day,), (0,), portfolio="A_CORE")
    enhancer = simulate_portfolio_path((day,), (0,), portfolio="GBPJPY_RETURN_ENHANCER")
    combined = simulate_portfolio_path((day,), (0,), portfolio="B_COMBINED_PORTFOLIO")
    assert a.allow + a.reduce + a.reject == 2
    assert enhancer.allow + enhancer.reduce + enhancer.reject == 2
    assert combined.allow + combined.reduce + combined.reject == 4
    assert combined.max_concurrency == 3
    assert combined.reduce == 0
    assert combined.reject == 1
    assert combined.heat_violations == 0

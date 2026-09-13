from __future__ import annotations

from datetime import date

import pytest

from qore.infrastructure.trader_lab.vt08_index_c2_r1_cibo_capital_t1 import (
    ATTACK_HEAT,
    ATTACK_SIGNAL_RISK,
    BASE_HEAT,
    BASE_SIGNAL_RISK,
    CONTROLLERS,
    INTERNAL_CAPITAL_LIMIT,
    INTERNAL_DAILY_LIMIT,
    MC_BLOCK_DAYS,
    MC_PATHS,
    MC_TRADING_DAYS,
    REDUCE_STEPS,
    ObservedTrade,
    full_guard_multiplier,
    moving_block_draws,
    run_sequence,
)


def _trade(key: str, r_multiple: float) -> ObservedTrade:
    return ObservedTrade(
        signal_key=(f"2025-01-02T07:00:00+00:00-{key}", "NAS100", "long"),
        day=date(2025, 1, 2),
        anchor=2,
        symbol="NAS100",
        side="long",
        r_multiple=r_multiple,
    )


def test_frozen_capital_contract_matches_preexisting_r317_transfer() -> None:
    assert BASE_SIGNAL_RISK == pytest.approx(0.01)
    assert BASE_HEAT == pytest.approx(0.025)
    assert ATTACK_SIGNAL_RISK == pytest.approx(0.02)
    assert ATTACK_HEAT == pytest.approx(0.045)
    assert INTERNAL_DAILY_LIMIT == pytest.approx(0.0475)
    assert INTERNAL_CAPITAL_LIMIT == pytest.approx(0.0495)
    assert CONTROLLERS == (
        "risk_only_r100",
        "cibo_bank_attack_r317_transfer",
        "cibo_full_guard_t1",
    )


def test_full_guard_uses_only_preexisting_r316_reduce_steps() -> None:
    assert REDUCE_STEPS == (
        (0.035, 0.75),
        (0.0425, 0.50),
        (0.0475, 0.25),
    )
    assert full_guard_multiplier(0.0349) == pytest.approx(1.0)
    assert full_guard_multiplier(0.0350) == pytest.approx(0.75)
    assert full_guard_multiplier(0.0425) == pytest.approx(0.50)
    assert full_guard_multiplier(0.0475) == pytest.approx(0.25)


def test_risk_sovereignty_scales_simultaneous_group_to_heat() -> None:
    trades = tuple(_trade(str(index), 2.0) for index in range(3))
    mapped = {date(2025, 1, 2): {2: trades}}
    result = run_sequence(
        (date(2025, 1, 2),),
        mapped,
        controller="risk_only_r100",
    )
    assert result.generated_signals == 3
    assert result.executed_trades == 3
    assert result.risk_reduced_groups == 1
    assert result.terminal_return == pytest.approx(0.05)


def test_internal_capital_floor_fails_closed_before_provider_boundary() -> None:
    days = tuple(date(2025, 1, day) for day in range(2, 10))
    mapped = {
        trading_day: {
            2: (
                ObservedTrade(
                    signal_key=(trading_day.isoformat(), "NAS100", "long"),
                    day=trading_day,
                    anchor=2,
                    symbol="NAS100",
                    side="long",
                    r_multiple=-1.0,
                ),
            )
        }
        for trading_day in days
    }
    result = run_sequence(days, mapped, controller="risk_only_r100")
    assert result.maximum_capital_drawdown <= INTERNAL_CAPITAL_LIMIT + 1e-12
    assert result.maximum_capital_drawdown < 0.05
    assert result.risk_rejected_signals > 0


def test_cibo_bank_attack_never_mutates_generated_signal_count() -> None:
    days = (date(2025, 1, 2), date(2025, 1, 3))
    mapped = {
        days[0]: {2: (_trade("a", 2.0),)},
        days[1]: {
            2: (
                ObservedTrade(
                    signal_key=("b", "NAS100", "long"),
                    day=days[1],
                    anchor=2,
                    symbol="NAS100",
                    side="long",
                    r_multiple=2.0,
                ),
            )
        },
    }
    result = run_sequence(
        days,
        mapped,
        controller="cibo_bank_attack_r317_transfer",
    )
    assert result.generated_signals == 2
    assert result.bank_decisions >= 1
    assert result.attack_groups >= 1


def test_moving_block_draws_are_deterministic_and_frozen() -> None:
    first = moving_block_draws(100)
    second = moving_block_draws(100)
    assert first == second
    assert len(first) == MC_PATHS
    assert all(len(draw) == MC_TRADING_DAYS for draw in first)
    assert all(
        draw[offset + MC_BLOCK_DAYS - 1] - draw[offset] == MC_BLOCK_DAYS - 1
        for draw in first[:10]
        for offset in range(0, MC_TRADING_DAYS, MC_BLOCK_DAYS)
    )

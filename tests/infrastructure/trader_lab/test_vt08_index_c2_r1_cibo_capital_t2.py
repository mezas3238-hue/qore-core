from __future__ import annotations

from datetime import date

from qore.infrastructure.trader_lab import vt08_index_c2_r1_cibo_capital_t1 as t1
from qore.infrastructure.trader_lab.vt08_index_c2_r1_cibo_capital_t2 import (
    CAPITAL_T2_FREEZE,
    run_sequence_t2,
)

TradeMap = dict[date, dict[int, tuple[t1.ObservedTrade, ...]]]


def _trade(day: date, anchor: int, ordinal: int, r_multiple: float) -> t1.ObservedTrade:
    return t1.ObservedTrade(
        signal_key=(day.isoformat(), f"{anchor:02d}", str(ordinal)),
        day=day,
        anchor=anchor,
        symbol="NAS100",
        side="long",
        r_multiple=r_multiple,
    )


def test_t2_freeze_is_pre_registered() -> None:
    assert CAPITAL_T2_FREEZE == "182b1418826b6d695966e36d70a7b97d9d780840"


def test_bank_reference_does_not_become_absorbing_risk_floor() -> None:
    day1 = date(2025, 1, 2)
    day2 = date(2025, 1, 3)
    day3 = date(2025, 1, 6)
    mapped: TradeMap = {
        day1: {2: (_trade(day1, 2, 1, 2.0),)},
        day2: {2: (_trade(day2, 2, 2, -1.0),)},
        day3: {2: (_trade(day3, 2, 3, 1.0),)},
    }
    t2 = run_sequence_t2((day1, day2, day3), mapped, full_guard=False)
    t1_control = t1.run_sequence(
        (day1, day2, day3),
        mapped,
        controller="cibo_bank_attack_r317_transfer",
    )
    assert t2.executed_trades == 3
    assert t2.executed_trades > t1_control.executed_trades
    assert t2.cibo_lock_groups == 0
    assert t2.cibo_suspend_groups == 0


def test_attack_is_requested_when_bank_is_active_and_risk_has_cushion() -> None:
    day1 = date(2025, 1, 2)
    day2 = date(2025, 1, 3)
    mapped: TradeMap = {
        day1: {2: (_trade(day1, 2, 1, 2.0),)},
        day2: {2: (_trade(day2, 2, 2, 1.0),)},
    }
    result = run_sequence_t2((day1, day2), mapped, full_guard=False)
    postures = dict(result.posture_counts)
    assert result.attack_groups == 1
    assert result.attack_trades == 1
    assert postures["ATTACK"] == 1


def test_daily_suspend_is_recomputed_and_reactivates_next_day() -> None:
    day1 = date(2025, 1, 2)
    day2 = date(2025, 1, 3)
    mapped: TradeMap = {
        day1: {
            2: tuple(_trade(day1, 2, index, -1.0) for index in range(1, 4)),
            6: tuple(_trade(day1, 6, index, -1.0) for index in range(4, 7)),
            10: (_trade(day1, 10, 7, -1.0),),
        },
        day2: {2: (_trade(day2, 2, 8, 1.0),)},
    }
    result = run_sequence_t2((day1, day2), mapped, full_guard=False)
    assert result.cibo_suspend_groups == 1
    assert result.cibo_reactivate_groups == 1
    assert result.executed_trades == 7
    assert result.risk_rejected_signals == 1


def test_full_guard_reduce_has_priority_over_attack_in_drawdown() -> None:
    days = (
        date(2025, 1, 2),
        date(2025, 1, 3),
        date(2025, 1, 6),
        date(2025, 1, 7),
    )
    mapped: TradeMap = {
        days[0]: {2: (_trade(days[0], 2, 1, 2.0),)},
        days[1]: {2: (_trade(days[1], 2, 2, -1.0),)},
        days[2]: {2: (_trade(days[2], 2, 3, -1.0),)},
        days[3]: {2: (_trade(days[3], 2, 4, 1.0),)},
    }
    result = run_sequence_t2(days, mapped, full_guard=True)
    postures = dict(result.posture_counts)
    assert result.cibo_reduce_groups >= 1
    assert postures["REDUCE"] >= 1
    assert result.maximum_capital_drawdown < t1.PROVIDER_LIMIT

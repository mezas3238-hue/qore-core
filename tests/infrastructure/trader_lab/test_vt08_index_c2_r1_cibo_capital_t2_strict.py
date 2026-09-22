from __future__ import annotations

from datetime import date

from qore.infrastructure.trader_lab import vt08_index_c2_r1_cibo_capital_t1 as t1
from qore.infrastructure.trader_lab.vt08_index_c2_r1_cibo_capital_t2_strict import (
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


def test_attack_requires_full_risk_authorizable_envelope() -> None:
    day1 = date(2025, 1, 2)
    day2 = date(2025, 1, 3)
    mapped: TradeMap = {
        day1: {2: (_trade(day1, 2, 1, 2.0),)},
        day2: {
            2: tuple(_trade(day2, 2, index, 0.0) for index in range(2, 5)),
        },
    }
    result = run_sequence_t2((day1, day2), mapped, full_guard=False)
    postures = dict(result.posture_counts)
    assert result.bank_decisions == 1
    assert result.attack_groups == 0
    assert result.attack_trades == 0
    assert postures["BANK"] == 1
    assert result.risk_reduced_groups == 1
    assert result.executed_trades == 4


def test_attack_occurs_when_full_envelope_fits() -> None:
    day1 = date(2025, 1, 2)
    day2 = date(2025, 1, 3)
    mapped: TradeMap = {
        day1: {2: (_trade(day1, 2, 1, 2.0),)},
        day2: {2: (_trade(day2, 2, 2, 0.5),)},
    }
    result = run_sequence_t2((day1, day2), mapped, full_guard=False)
    assert result.attack_groups == 1
    assert result.attack_trades == 1
    assert dict(result.posture_counts)["ATTACK"] == 1

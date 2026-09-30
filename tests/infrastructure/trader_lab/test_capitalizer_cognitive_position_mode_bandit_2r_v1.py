from __future__ import annotations

from collections import Counter

from qore.infrastructure.trader_lab import (
    capitalizer_cognitive_position_mode_bandit_2r_v1 as lab,
)


def test_warmup_rotates_all_arms() -> None:
    counts: Counter[tuple[str, str]] = Counter()
    symbol = "NAS100"
    assert lab._warmup_mode(symbol=symbol, selection_counts=counts) == lab.ARMS[0]
    counts[(symbol, lab.ARMS[0])] += 1
    assert lab._warmup_mode(symbol=symbol, selection_counts=counts) == lab.ARMS[1]


def test_systemic_pressure_requires_breadth_and_negative_sum() -> None:
    assert lab._systemic_pressure(()) is False

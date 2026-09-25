from __future__ import annotations

from collections import Counter
from decimal import Decimal

from qore.infrastructure.trader_lab import (
    capitalizer_cognitive_target_bandit_2r_v1 as lab,
)


def test_target_warmup_starts_from_first_arm() -> None:
    counts: Counter[tuple[str, Decimal]] = Counter()
    assert lab._warmup(symbol="NAS100", counts=counts) == lab.ARMS[0]


def test_target_grid_contains_frozen_2r_baseline() -> None:
    assert lab.BASELINE_TARGET in lab.ARMS
    assert lab.ARMS[0] == Decimal("1.00")
    assert lab.ARMS[-1] == Decimal("3.00")

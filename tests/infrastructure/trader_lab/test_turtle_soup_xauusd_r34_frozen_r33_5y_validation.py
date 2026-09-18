from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

from qore.infrastructure.trader_lab import (
    turtle_soup_xauusd_r34_frozen_r33_5y_validation as r34,
)


def test_r34_window_and_acceptance_are_frozen() -> None:
    assert r34.EVAL_OPEN == datetime(2021, 9, 17, tzinfo=UTC)
    assert r34.EVAL_CLOSE == datetime(2026, 9, 17, tzinfo=UTC)
    assert r34.MIN_TRADES == 800
    assert r34.MIN_PF_010 == Decimal("1.50")
    assert r34.MAX_DD_010 == Decimal("10.0")


def test_r34_replays_exact_r33_candidate() -> None:
    assert r34.FAMILY_SET == "R33_FIVE_FAMILY"
    assert r34.GOVERNOR == "DD_2_4_SCALE_075_025"
    assert r34.ALLOWED_FAMILIES == r34.r33.FAMILY_SETS[r34.FAMILY_SET]
    assert r34.GOVERNOR_RULE == r34.r33.GOVERNORS[r34.GOVERNOR]

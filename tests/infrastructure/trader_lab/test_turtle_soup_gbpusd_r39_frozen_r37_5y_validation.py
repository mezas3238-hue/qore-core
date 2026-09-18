from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

from qore.infrastructure.trader_lab import (
    turtle_soup_gbpusd_r39_frozen_r37_5y_validation as r39,
)


def test_r39_frozen_5y_gate_is_predeclared() -> None:
    assert r39.EVAL_OPEN == datetime(2021, 9, 17, tzinfo=UTC)
    assert r39.EVAL_CLOSE == datetime(2026, 9, 17, tzinfo=UTC)
    assert r39.MIN_TRADES == 800
    assert r39.MIN_PF_010 == Decimal("1.50")
    assert r39.MAX_DD_010 == Decimal("6.0")


def test_r39_preserves_exact_r37_contract() -> None:
    assert r39.FAMILY_SET == "R37_G25_FIXED"
    assert r39.STRUCTURAL_POLICY_NAME == "SQ3_H1_BALANCED"
    assert r39.DRAWDOWN_GOVERNOR_NAME == "DD_1_3_SCALE_075_025"
    assert tuple(r39.ALLOWED_FAMILIES) == (r39.r37.F2, r39.r37.F5)

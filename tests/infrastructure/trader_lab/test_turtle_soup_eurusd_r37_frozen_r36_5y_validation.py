from __future__ import annotations

from decimal import Decimal

from qore.infrastructure.trader_lab import (
    turtle_soup_eurusd_r37_frozen_r36_5y_validation as r37,
)


def test_r37_window_and_gates_are_frozen() -> None:
    assert r37.EVAL_OPEN.isoformat() == "2021-09-17T00:00:00+00:00"
    assert r37.EVAL_CLOSE.isoformat() == "2026-09-17T00:00:00+00:00"
    assert r37.MIN_TRADES == 800
    assert r37.MIN_PF_010 == Decimal("1.50")
    assert r37.MAX_DD_010 == Decimal("6.0")


def test_r37_uses_exact_r36_contract() -> None:
    assert r37.FAMILY_SET == "R36_F235_FROZEN"
    assert r37.GOVERNOR == "FRAGILITY_050_025_010"
    assert r37.ALLOWED_FAMILIES == (
        r37.r36.F2,
        r37.r36.F3,
        r37.r36.F5,
    )

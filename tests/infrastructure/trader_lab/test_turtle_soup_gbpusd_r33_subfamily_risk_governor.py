from __future__ import annotations

from decimal import Decimal

from qore.infrastructure.trader_lab import (
    turtle_soup_gbpusd_r33_subfamily_risk_governor as r33,
)


def test_r33_acceptance_is_fixed() -> None:
    assert r33.MIN_TRADES == 350
    assert r33.MIN_PF_010 == Decimal("1.90")
    assert r33.MAX_DD_010 == Decimal("6.0")


def test_family_sets_are_gbpusd_native_and_predeclared() -> None:
    assert r33.FAMILY_SETS["R33_G123"] == (r33.F1, r33.F2, r33.F3)
    assert r33.FAMILY_SETS["R33_G456"] == (r33.F4, r33.F5, r33.F6)
    assert r33.FAMILY_SETS["R33_G12345"] == (
        r33.F1, r33.F2, r33.F3, r33.F4, r33.F5,
    )
    assert r33.FAMILY_SETS["R33_G123456"] == (
        r33.F1, r33.F2, r33.F3, r33.F4, r33.F5, r33.F6,
    )
    assert "EURUSD" not in "|".join(r33.FAMILY_DEV_EVIDENCE)


def test_drawdown_governor_scales_without_suppressing() -> None:
    rule = r33.GOVERNORS["DD_1_3_SCALE_075_025"]
    assert r33._risk_scale(Decimal("0.5"), rule) == Decimal("1")
    assert r33._risk_scale(Decimal("1.5"), rule) == Decimal("0.75")
    assert r33._risk_scale(Decimal("3.0"), rule) == Decimal("0.25")

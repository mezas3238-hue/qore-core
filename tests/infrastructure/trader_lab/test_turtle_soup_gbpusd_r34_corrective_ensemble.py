from __future__ import annotations

from decimal import Decimal

from qore.infrastructure.trader_lab import (
    turtle_soup_gbpusd_r34_corrective_ensemble as r34,
)


def test_r34_acceptance_is_fixed() -> None:
    assert r34.MIN_TRADES == 350
    assert r34.MIN_PF_010 == Decimal("1.90")
    assert r34.MAX_DD_010 == Decimal("6.0")


def test_falsified_r33_family_is_excluded() -> None:
    for families in r34.FAMILY_SETS.values():
        assert r34.F1 not in families


def test_corrective_sets_are_predeclared() -> None:
    assert r34.FAMILY_SETS["R34_G2456"] == (r34.F2, r34.F4, r34.F5, r34.F6)
    assert r34.FAMILY_SETS["R34_G56"] == (r34.F5, r34.F6)


def test_risk_governor_never_suppresses() -> None:
    rule = r34.GOVERNORS["DD_1_3_SCALE_075_025"]
    assert r34._risk_scale(Decimal("0.5"), rule) == Decimal("1")
    assert r34._risk_scale(Decimal("1.5"), rule) == Decimal("0.75")
    assert r34._risk_scale(Decimal("3"), rule) == Decimal("0.25")

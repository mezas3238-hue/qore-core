from __future__ import annotations

from decimal import Decimal

from qore.infrastructure.trader_lab import (
    turtle_soup_eurusd_r36_structural_fragility_governor as r36,
)


def test_r36_gate_is_fixed() -> None:
    assert r36.MIN_TRADES == 350
    assert r36.MIN_PF_010 == Decimal("1.90")
    assert r36.MAX_DD_010 == Decimal("6.0")


def test_r36_signal_contract_is_f235() -> None:
    assert r36.FAMILY_SETS == {"R36_F235_FROZEN": (r36.F2, r36.F3, r36.F5)}
    assert r36.F1 not in r36.FAMILY_SETS["R36_F235_FROZEN"]


def test_fragility_policy_never_suppresses() -> None:
    p=r36.FRAGILITY_POLICIES["FRAGILITY_050_025_010"]
    assert r36._fragility_scale(0,p)==Decimal("1")
    assert r36._fragility_scale(1,p)==Decimal("0.50")
    assert r36._fragility_scale(2,p)==Decimal("0.25")
    assert r36._fragility_scale(7,p)==Decimal("0.10")
    assert all(value > 0 for policy in r36.FRAGILITY_POLICIES.values() for value in policy)

from __future__ import annotations

from decimal import Decimal

from qore.infrastructure.trader_lab import (
    turtle_soup_gbpusd_r36_f2_structural_forensics as r36,
)


def test_r36_reproduces_g25_only() -> None:
    assert r36.FAMILY_SETS == {"R36_G25_REPRODUCTION": (r36.F2, r36.F5)}


def test_r36_keeps_acceptance_contract() -> None:
    assert r36.MIN_TRADES == 350
    assert r36.MIN_PF_010 == Decimal("1.90")
    assert r36.MAX_DD_010 == Decimal("6.0")


def test_r36_does_not_reintroduce_falsified_families() -> None:
    families = r36.FAMILY_SETS["R36_G25_REPRODUCTION"]
    assert r36.F1 not in families
    assert r36.F3 not in families

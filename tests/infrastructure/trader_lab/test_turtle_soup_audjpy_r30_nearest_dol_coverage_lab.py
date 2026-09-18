from __future__ import annotations

from decimal import Decimal

from qore.infrastructure.trader_lab import (
    turtle_soup_audjpy_r30_nearest_dol_coverage_lab as r30,
)


def test_r30_acceptance_is_fixed() -> None:
    assert r30.MIN_TRADES == 350
    assert r30.MIN_PF_010 == Decimal("1.90")
    assert r30.MAX_DD_010 == Decimal("6.0")
    assert r30.MAX_LS_010 == 3


def test_recovery_variants_are_predeclared() -> None:
    assert r30.VARIANT_RULES[r30.NEAREST_BASELINE] == (None, None)
    assert r30.VARIANT_RULES[r30.OBS16_REACH055] == (16, Decimal("0.55"))
    assert r30.VARIANT_RULES[r30.OBS12_REACH060] == (12, Decimal("0.60"))
    assert r30.VARIANT_RULES[r30.OBS12_REACH055] == (12, Decimal("0.55"))
    assert r30.VARIANT_RULES[r30.OBS8_REACH065] == (8, Decimal("0.65"))

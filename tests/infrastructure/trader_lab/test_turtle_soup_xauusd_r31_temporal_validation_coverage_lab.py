from __future__ import annotations

from decimal import Decimal

from qore.infrastructure.trader_lab import (
    turtle_soup_xauusd_r31_temporal_validation_coverage_lab as r31,
)


def test_r31_acceptance_gates_are_fixed() -> None:
    assert r31.MIN_TRADES == 250
    assert r31.MIN_PF_010 == Decimal("1.80")
    assert r31.MAX_DD_010 == Decimal("8.0")
    assert r31.MAX_LS_010 == 3


def test_r31_variants_are_predeclared() -> None:
    assert len(r31.VARIANTS) == 6
    assert r31.VARIANTS["R31_TERCILE_2OF3_ORIGINAL_SUPPORT"]["parts"] == 3
    assert r31.VARIANTS["R31_QUARTILE_2OF4_ORIGINAL_SUPPORT"]["parts"] == 4
    assert r31.VARIANTS["R31_QUINTILE_3OF5_ORIGINAL_SUPPORT"]["parts"] == 5

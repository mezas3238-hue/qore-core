from __future__ import annotations

from decimal import Decimal

from qore.infrastructure.trader_lab import (
    turtle_soup_eurusd_r29_coverage_expansion_lab as r29,
)


def test_acceptance_thresholds_are_fixed() -> None:
    assert r29.MIN_TRADES == 250
    assert r29.MIN_PF_010 == Decimal("1.80")
    assert r29.MAX_DD_010 == Decimal("8.0")
    assert r29.MAX_LS_010 == 3


def test_fallback_variants_are_rank1_only_by_contract() -> None:
    assert r29.BASELINE in r29.VARIANTS
    assert r29.ROBUST_AGREE in r29.VARIANTS
    assert r29.VALIDATED_AGREE in r29.VARIANTS
    assert r29.ROBUST in r29.VARIANTS
    assert r29.VALIDATED in r29.VARIANTS

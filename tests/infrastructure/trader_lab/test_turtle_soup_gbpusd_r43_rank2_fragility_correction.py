from __future__ import annotations

from decimal import Decimal

from qore.infrastructure.trader_lab import (
    turtle_soup_gbpusd_r43_rank2_fragility_correction as r43,
)


def test_r43_requires_five_of_five_positive_years() -> None:
    assert r43.MIN_TRADES == 800
    assert r43.MIN_PF_010 == Decimal("1.50")
    assert r43.MAX_DD_010 == Decimal("6.0")
    assert r43.MIN_POSITIVE_ANNUAL_BLOCKS == 5


def test_r43_preserves_all_signals_and_only_scales_risk() -> None:
    assert r43.SHORT_SCALE == Decimal("0.005")
    for value in r43.RANK2_SCALES.values():
        assert Decimal("0") < value <= Decimal("1")


def test_r43_source_binding_is_exact() -> None:
    assert r43.SOURCE_RUN_ID == 35353073610
    assert r43.SOURCE_ARTIFACT_ID == 10550866581
    assert r43.SOURCE_GIT_SHA == "e02d9384fbe6521040fc2779a085c43b8d5f0f92"

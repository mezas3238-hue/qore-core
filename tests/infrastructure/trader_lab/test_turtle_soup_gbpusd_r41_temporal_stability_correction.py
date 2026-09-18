from __future__ import annotations

from decimal import Decimal

from qore.infrastructure.trader_lab import (
    turtle_soup_gbpusd_r41_temporal_stability_correction as r41,
)


def test_r41_requires_all_five_years_positive() -> None:
    assert r41.MIN_TRADES == 800
    assert r41.MIN_PF_010 == Decimal("1.50")
    assert r41.MAX_DD_010 == Decimal("6.0")


def test_r41_short_overlays_never_suppress() -> None:
    assert set(r41.OVERLAYS) == {
        "R41_SHORT_020",
        "R41_SHORT_015",
        "R41_SHORT_010",
        "R41_SHORT_005",
    }
    for rule in r41.OVERLAYS.values():
        assert Decimal(str(rule["short"])) > 0
        assert Decimal(str(rule["f5"])) == Decimal("1")
        assert Decimal(str(rule["majority"])) == Decimal("1")
        assert Decimal(str(rule["rank2"])) == Decimal("1")


def test_r41_source_binding_is_exact() -> None:
    assert r41.SOURCE_RUN_ID == 35353073610
    assert r41.SOURCE_ARTIFACT_ID == 10550866581
    assert r41.SOURCE_GIT_SHA == "e02d9384fbe6521040fc2779a085c43b8d5f0f92"

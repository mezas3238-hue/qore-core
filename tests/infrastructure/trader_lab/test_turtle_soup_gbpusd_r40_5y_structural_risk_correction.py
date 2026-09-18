from __future__ import annotations

from decimal import Decimal

from qore.infrastructure.trader_lab import (
    turtle_soup_gbpusd_r40_5y_structural_risk_correction as r40,
)


def test_r40_gate_is_frozen() -> None:
    assert r40.MIN_TRADES == 800
    assert r40.MIN_PF_010 == Decimal("1.50")
    assert r40.MAX_DD_010 == Decimal("6.0")


def test_r40_overlays_never_suppress() -> None:
    for rule in r40.OVERLAYS.values():
        assert Decimal(str(rule["short"])) > 0
        assert Decimal(str(rule["f5"])) > 0
        assert Decimal(str(rule["majority"])) > 0
        assert Decimal(str(rule["rank2"])) > 0


def test_r40_source_binding_is_exact() -> None:
    assert r40.SOURCE_RUN_ID == 35353073610
    assert r40.SOURCE_ARTIFACT_ID == 10550866581
    assert r40.SOURCE_GIT_SHA == "e02d9384fbe6521040fc2779a085c43b8d5f0f92"

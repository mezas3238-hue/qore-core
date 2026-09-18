from __future__ import annotations

from decimal import Decimal

from qore.infrastructure.trader_lab import (
    turtle_soup_audjpy_r41_5y_structural_fragility_correction as r41,
)


def test_r41_source_binding_is_exact() -> None:
    assert r41.SOURCE_RUN_ID == 35397390781
    assert r41.SOURCE_ARTIFACT_ID == 10570170141
    assert r41.SOURCE_GIT_SHA == "a332b077598e070a42b2497b3766d55e731f7dca"


def test_r41_owner_gates_are_fixed() -> None:
    assert r41.MIN_TRADES_5Y == 800
    assert r41.MIN_PF_5Y == Decimal("1.50")
    assert r41.MAX_DD_5Y == Decimal("6.0")
    assert r41.REQUIRED_POSITIVE_ANNUAL_BLOCKS == 5
    assert r41.MIN_TRADES_2Y == 350
    assert r41.MIN_PF_2Y == Decimal("1.90")
    assert r41.MAX_DD_2Y == Decimal("6.0")


def test_r41_second_layer_is_nonzero_and_predeclared() -> None:
    assert r41.FRAGILITY_FLAGS == (
        "D1_BODY_ALIGNMENT_OPPOSED",
        "RAID_DEPTH_Q4_LE_0_50",
        "SOURCE_RANGE_Q2_LE_1_0",
    )
    assert r41.FRAGILITY_POLICY == (
        Decimal("1"),
        Decimal("0.50"),
        Decimal("0.25"),
        Decimal("0.10"),
    )
    assert min(r41.FRAGILITY_POLICY) > Decimal("0")

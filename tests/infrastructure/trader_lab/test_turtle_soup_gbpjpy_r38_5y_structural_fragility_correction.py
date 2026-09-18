from __future__ import annotations

from decimal import Decimal

from qore.infrastructure.trader_lab import (
    turtle_soup_gbpjpy_r38_5y_structural_fragility_correction as r38,
)


def test_r38_binds_exact_failed_r37_evidence() -> None:
    assert r38.SOURCE_RUN_ID == 35371203863
    assert r38.SOURCE_ARTIFACT_ID == 10558603038
    assert r38.SOURCE_GIT_SHA == "eb62226e05f63cf94c1940634de676c55285e6dd"


def test_r38_uses_only_gbpjpy_preentry_fragility_flags() -> None:
    assert r38.FRAGILITY_FLAGS == (
        "CORE_SOURCE_OPPOSITE_BOUNDARY_H1",
        "CORE_CLOSE_LOCATION_Q4",
        "CORE_H4_BODY_WITH",
    )
    assert r38.FRAGILITY_POLICY == (
        Decimal("1"),
        Decimal("0.25"),
        Decimal("0.10"),
        Decimal("0.05"),
    )


def test_r38_preserves_owner_gates() -> None:
    assert r38.MIN_TRADES_5Y == 800
    assert r38.MIN_PF_5Y == Decimal("1.50")
    assert r38.MAX_DD_5Y == Decimal("6.0")
    assert r38.REQUIRED_POSITIVE_ANNUAL_BLOCKS == 5
    assert r38.MIN_TRADES_2Y == 350
    assert r38.MIN_PF_2Y == Decimal("1.90")
    assert r38.MAX_DD_2Y == Decimal("6.0")

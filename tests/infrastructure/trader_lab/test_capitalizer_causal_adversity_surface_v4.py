from __future__ import annotations

from decimal import Decimal

from qore.infrastructure.trader_lab import (
    capitalizer_causal_adversity_surface_v4 as lab,
)
from qore.infrastructure.trader_lab import capitalizer_native_market_context_v1 as context


def _ctx() -> context.NativeContextRow:
    return context.NativeContextRow(
        symbol="EURUSD",
        session="LONDON",
        operating_date="2026-01-05",
        side="LONG",
        entry_at="2026-01-05T08:00:00+00:00",
        provenance="TEST",
        risk_price="0.001",
        m15_slope_alignment="OPPOSED",
        h1_body_alignment="OPPOSED",
        volatility_state="EXPANSION",
        volatility_ratio="1.4",
        destination_state="LT_1R",
        destination_room_r="0.8",
        destination_pivot_confirmed_at="2026-01-05T07:00:00+00:00",
        regime_signature="M15=OPPOSED|H1=OPPOSED|VOL=EXPANSION",
        context_signature="M15=OPPOSED|H1=OPPOSED|VOL=EXPANSION|DEST=LT_1R",
    )


def test_hazard_surface_accumulates_independent_risks() -> None:
    hazards = lab._hazards(
        ctx=_ctx(),
        current_dd=Decimal("5.2"),
        adverse_votes=3,
    )
    assert "DD_GE_2" in hazards
    assert "DD_GE_4" in hazards
    assert "DD_GE_5" in hazards
    assert "VOL_EXPANSION" in hazards
    assert "DEST_LT_1R" in hazards
    assert "DUAL_OPPOSED" in hazards
    assert "EDGE_ADVERSE_3" in hazards
    assert lab._score(hazards) >= 10


def test_room_expansion_rule_requires_both_structural_hazards() -> None:
    ctx = _ctx()
    assert lab._multiplier(
        policy="ROOM_EXPANSION_DD",
        ctx=ctx,
        current_dd=Decimal("4.2"),
        hazards=(),
        score=0,
        adverse_votes=0,
    ) == Decimal("0.40")

from __future__ import annotations

from dataclasses import replace
from decimal import Decimal

from qore.infrastructure.trader_lab import capitalizer_native_market_context_v1 as context
from qore.infrastructure.trader_lab import (
    capitalizer_surface_selective_refinement_v4_1 as lab,
)


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


def test_tight5_only_hardens_final_high_dd_zone() -> None:
    assert lab._refined_multiplier(
        policy="SELECTIVE_TIGHT5",
        ctx=_ctx(),
        current_dd=Decimal("5.6"),
        score=6,
        adverse_votes=1,
        base_multiplier=Decimal("0.55"),
    ) == Decimal("0.15")
    assert lab._refined_multiplier(
        policy="SELECTIVE_TIGHT5",
        ctx=_ctx(),
        current_dd=Decimal("2"),
        score=6,
        adverse_votes=1,
        base_multiplier=Decimal("1"),
    ) == Decimal("1")


def test_recovery_aware_preserves_favorable_escape() -> None:
    favorable = replace(
        _ctx(),
        h1_body_alignment="ALIGNED",
        destination_state="GE_2R",
    )
    assert lab._refined_multiplier(
        policy="SELECTIVE_RECOVERY_AWARE",
        ctx=favorable,
        current_dd=Decimal("5.8"),
        score=8,
        adverse_votes=1,
        base_multiplier=Decimal("0.20"),
    ) == Decimal("1")

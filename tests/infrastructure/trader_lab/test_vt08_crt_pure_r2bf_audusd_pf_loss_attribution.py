from __future__ import annotations

from qore.infrastructure.trader_lab.vt08_crt_pure_r2bf_audusd_pf_loss_attribution import (
    IDENTITY,
    _annual_bucket,
    _combined_bucket,
    _delay_bars,
    _reference_bucket,
    _stop_subtype,
)
from qore.infrastructure.trader_lab.vt08_crt_pure_r2_model1_reference_lab import Model1LabTrade


def _trade() -> Model1LabTrade:
    return Model1LabTrade(
        schema="test",
        identity="test",
        market="AUDUSD",
        reference_policy="TEST",
        reference_count=1,
        reference_ids=("x",),
        parent_direction="BULLISH",
        timing_triplet="ROLLING_H4:5",
        c3_opened_at="2026-01-01T00:00:00+00:00",
        source_opened_at="2026-01-01T00:00:00+00:00",
        confirmation_opened_at="2026-01-01T00:30:00+00:00",
        entry_opened_at="2026-01-01T00:45:00+00:00",
        entry_price_relative=100,
        stop_price_relative=90,
        target_price_relative="115",
        exit_price_relative="90",
        exit_reason="STOP",
        r_multiple=-1.0,
    )


def test_r2bf_identity_is_frozen() -> None:
    assert IDENTITY == "VT08_CRT_PURE_R2BF_AUDUSD_PF_LOSS_ATTRIBUTION_001"


def test_r2bf_buckets_are_deterministic() -> None:
    trade = _trade()
    assert _stop_subtype(trade) == "ORIGINAL_STOP_MINUS_1R"
    assert _delay_bars(trade) == "D2"
    assert _reference_bucket(trade) == "REF1"
    assert _combined_bucket(trade, kind="SLOT5_VS_REST") == "H4_SLOT_5"
    assert _annual_bucket(trade) == "2025_2026"

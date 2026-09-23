from __future__ import annotations

from decimal import Decimal

from qore.infrastructure.trader_lab.vt08_crt_pure_r2_model1_reference_lab import (
    Model1LabTrade,
)
from qore.infrastructure.trader_lab.vt08_crt_pure_r3c_btcusd_wfo_slippage import (
    MAX_FOLD_DD_R,
    MIN_FOLD_TRADES,
    SLIPPAGE_PER_FILL,
    _stressed_r,
)


def _trade(direction: str) -> Model1LabTrade:
    if direction == "BULLISH":
        entry, stop, exit_price = 100, 90, "120"
    else:
        entry, stop, exit_price = 100, 110, "80"
    return Model1LabTrade(
        schema="test",
        identity="test",
        market="BTCUSD",
        reference_policy="UNTOUCHED_SWING_STRENGTH_1",
        reference_count=2,
        reference_ids=("a", "b"),
        parent_direction=direction,
        timing_triplet="1",
        c3_opened_at="2024-01-01T00:00:00+00:00",
        source_opened_at="2024-01-01T00:15:00+00:00",
        confirmation_opened_at="2024-01-01T00:30:00+00:00",
        entry_opened_at="2024-01-01T00:45:00+00:00",
        entry_price_relative=entry,
        stop_price_relative=stop,
        target_price_relative="120" if direction == "BULLISH" else "80",
        exit_price_relative=exit_price,
        exit_reason="TARGET_50",
        r_multiple=2.0,
    )


def test_r3c_frozen_wfo_and_slippage_family() -> None:
    assert MIN_FOLD_TRADES == 10
    assert MAX_FOLD_DD_R == 8.0
    assert SLIPPAGE_PER_FILL == (
        Decimal("0.01"),
        Decimal("0.025"),
        Decimal("0.05"),
    )


def test_adverse_slippage_reduces_long_and_short_r() -> None:
    for direction in ("BULLISH", "BEARISH"):
        base = Decimal(str(_trade(direction).r_multiple))
        stressed = _stressed_r(_trade(direction), Decimal("0.05"))
        assert stressed < base
        assert stressed > 0

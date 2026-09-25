from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

from qore.infrastructure.trader_lab import (
    vt08_index_r120_daily_bias_mechanism as r120,
)
from qore.infrastructure.traders.contracts import DemoTradingSetupSide
from qore.infrastructure.traders.vt08_index_c2_positional_r1 import (
    Vt08IndexC2R1Bar,
)


def _bar(
    open_: str,
    high: str,
    low: str,
    close: str,
) -> Vt08IndexC2R1Bar:
    opened = datetime(2026, 1, 1, tzinfo=UTC)
    return Vt08IndexC2R1Bar(
        opened_at=opened,
        closed_at=opened + timedelta(hours=23),
        open=Decimal(open_),
        high=Decimal(high),
        low=Decimal(low),
        close=Decimal(close),
    )


def test_r120_classifies_close_breakout_for_both_sides() -> None:
    previous = _bar("100", "110", "90", "101")
    bullish = _bar("101", "115", "96", "112")
    bearish = _bar("101", "105", "85", "88")

    assert r120._bias_mechanism(
        previous_day=previous,
        current_day=bullish,
        side=DemoTradingSetupSide.LONG,
    ) == r120.MECHANISM_BREAKOUT
    assert r120._bias_mechanism(
        previous_day=previous,
        current_day=bearish,
        side=DemoTradingSetupSide.SHORT,
    ) == r120.MECHANISM_BREAKOUT


def test_r120_classifies_sweep_reversal_for_both_sides() -> None:
    previous = _bar("100", "110", "90", "101")
    bullish = _bar("101", "108", "88", "95")
    bearish = _bar("101", "112", "92", "105")

    assert r120._bias_mechanism(
        previous_day=previous,
        current_day=bullish,
        side=DemoTradingSetupSide.LONG,
    ) == r120.MECHANISM_REVERSAL
    assert r120._bias_mechanism(
        previous_day=previous,
        current_day=bearish,
        side=DemoTradingSetupSide.SHORT,
    ) == r120.MECHANISM_REVERSAL


def test_r120_surface_and_r119_source_are_pinned() -> None:
    assert r120.EXPECTED_STANDARD == {
        "5Y": 1756,
        "2Y": 746,
        "R66": 546,
    }
    assert r120.SOURCE_R119_RUN_ID == 35791895806
    assert r120.SOURCE_R119_ARTIFACT_ID == 10721819322
    assert r120.SOURCE_R119_ARTIFACT_DIGEST == (
        "sha256:99a03b8a00e150c16c868fbbede903973f4d14914c0c0dbe931e13249a94a17a"
    )

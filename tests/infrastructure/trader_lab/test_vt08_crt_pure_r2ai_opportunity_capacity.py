from __future__ import annotations

from datetime import UTC, datetime

from qore.infrastructure.trader_lab.vt08_crt_pure_2y_replay import AggregatedCandle
from qore.infrastructure.trader_lab.vt08_crt_pure_r2_model1_reference_lab import ParentCrt
from qore.infrastructure.trader_lab.vt08_crt_pure_r2ai_opportunity_capacity import (
    IDENTITY,
    WINDOWS,
    _midpoint_valid,
    _structural_risk_valid,
)
from qore.infrastructure.traders.crt_pure_identity import CrtPureMarket
from qore.infrastructure.traders.crt_pure_methodology_candidate import (
    CrtPureCandidateDirection,
)


def _candle(open_price: int, high: int, low: int, close: int) -> AggregatedCandle:
    opened = datetime(2026, 1, 1, tzinfo=UTC)
    return AggregatedCandle(
        opened_at=opened,
        closed_at=opened,
        open_price=open_price,
        high_price=high,
        low_price=low,
        close_price=close,
        m5_count=48,
    )


def _parent(direction: CrtPureCandidateDirection) -> ParentCrt:
    return ParentCrt(
        market=CrtPureMarket.AUDUSD,
        direction=direction,
        triplet="1",
        c3_opened_at=datetime(2026, 1, 1, tzinfo=UTC),
        c3_closed_at=datetime(2026, 1, 1, tzinfo=UTC),
        c1=_candle(100, 120, 80, 110),
        c2=_candle(110, 121, 79, 100),
        c3_m5=(),
    )


def test_capacity_identity_and_windows_are_frozen() -> None:
    assert IDENTITY == "VT08_CRT_PURE_R2AI_LONG_WINDOW_OPPORTUNITY_CAPACITY_001"
    assert WINDOWS[CrtPureMarket.AUDUSD].start.year == 2016
    assert WINDOWS[CrtPureMarket.USDJPY].start.year == 2014


def test_structural_risk_geometry_is_directional() -> None:
    bullish = _parent(CrtPureCandidateDirection.BULLISH)
    bearish = _parent(CrtPureCandidateDirection.BEARISH)

    assert _structural_risk_valid(
        parent=bullish,
        source_low=90,
        source_high=110,
        entry=100,
    )
    assert not _structural_risk_valid(
        parent=bullish,
        source_low=100,
        source_high=110,
        entry=100,
    )
    assert _structural_risk_valid(
        parent=bearish,
        source_low=90,
        source_high=110,
        entry=100,
    )
    assert not _structural_risk_valid(
        parent=bearish,
        source_low=90,
        source_high=100,
        entry=100,
    )


def test_midpoint_gate_is_stricter_than_structural_risk() -> None:
    bullish = _parent(CrtPureCandidateDirection.BULLISH)

    assert _structural_risk_valid(
        parent=bullish,
        source_low=90,
        source_high=110,
        entry=105,
    )
    assert not _midpoint_valid(
        parent=bullish,
        source_low=90,
        source_high=110,
        entry=105,
    )

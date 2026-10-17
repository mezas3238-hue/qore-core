from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

from qore.infrastructure.trader_lab.vt08_crt_pure_2y_replay import AggregatedCandle
from qore.infrastructure.trader_lab.vt08_crt_pure_r2_model1_reference_lab import (
    M15Bar,
    ParentCrt,
)
from qore.infrastructure.trader_lab.vt08_crt_pure_r2l_usdjpy_regime_forensics import (
    _bucket_c1_ratio,
    _bucket_c2_ratio,
    _bucket_efficiency,
    _bucket_volatility,
    _drift_alignment,
    _manipulation_depth,
    _reclaim_depth,
    _trend_efficiency,
)
from qore.infrastructure.traders.crt_pure_identity import CrtPureMarket
from qore.infrastructure.traders.crt_pure_methodology_candidate import (
    CrtPureCandidateDirection,
)


def _bar(
    opened_at: datetime,
    open_price: int,
    high_price: int,
    low_price: int,
    close_price: int,
) -> M15Bar:
    return M15Bar(
        opened_at=opened_at,
        open_price=open_price,
        high_price=high_price,
        low_price=low_price,
        close_price=close_price,
    )


def _candle(
    opened_at: datetime,
    *,
    open_price: int,
    high_price: int,
    low_price: int,
    close_price: int,
) -> AggregatedCandle:
    return AggregatedCandle(
        opened_at=opened_at,
        closed_at=opened_at + timedelta(hours=4),
        open_price=open_price,
        high_price=high_price,
        low_price=low_price,
        close_price=close_price,
        m5_count=48,
    )


def _parent(direction: CrtPureCandidateDirection) -> ParentCrt:
    t0 = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)
    c1 = _candle(
        t0,
        open_price=100,
        high_price=120,
        low_price=80,
        close_price=110,
    )
    if direction is CrtPureCandidateDirection.BULLISH:
        c2 = _candle(
            t0 + timedelta(hours=4),
            open_price=110,
            high_price=115,
            low_price=70,
            close_price=90,
        )
    else:
        c2 = _candle(
            t0 + timedelta(hours=4),
            open_price=90,
            high_price=130,
            low_price=85,
            close_price=110,
        )
    return ParentCrt(
        market=CrtPureMarket.USDJPY,
        direction=direction,
        triplet="1",
        c3_opened_at=t0 + timedelta(hours=8),
        c3_closed_at=t0 + timedelta(hours=12),
        c1=c1,
        c2=c2,
        c3_m5=(),
    )


def test_regime_bucket_boundaries_are_frozen() -> None:
    assert _bucket_volatility(Decimal("0.79")) == "VOL_LT_0_80"
    assert _bucket_volatility(Decimal("0.80")) == "VOL_0_80_TO_1_20"
    assert _bucket_volatility(Decimal("1.20")) == "VOL_1_20_TO_1_60"
    assert _bucket_volatility(Decimal("1.60")) == "VOL_GE_1_60"

    assert _bucket_efficiency(Decimal("0.19")) == "EFF_LT_0_20"
    assert _bucket_efficiency(Decimal("0.20")) == "EFF_0_20_TO_0_40"
    assert _bucket_efficiency(Decimal("0.40")) == "EFF_0_40_TO_0_60"
    assert _bucket_efficiency(Decimal("0.60")) == "EFF_GE_0_60"

    assert _bucket_c1_ratio(Decimal("0.75")) == "C1R_0_75_TO_1_25"
    assert _bucket_c2_ratio(Decimal("1.50")) == "C2R_1_50_TO_2_00"


def test_drift_alignment_respects_parent_direction() -> None:
    t0 = datetime(2026, 1, 1, 0, 0, tzinfo=UTC)
    rising = (
        _bar(t0, 100, 102, 99, 101),
        _bar(t0 + timedelta(minutes=15), 101, 104, 100, 103),
    )

    assert (
        _drift_alignment(
            rows=rising,
            direction=CrtPureCandidateDirection.BULLISH,
        )
        == "ALIGNED"
    )
    assert (
        _drift_alignment(
            rows=rising,
            direction=CrtPureCandidateDirection.BEARISH,
        )
        == "OPPOSED"
    )


def test_trend_efficiency_is_bounded_and_causal() -> None:
    t0 = datetime(2026, 1, 1, 0, 0, tzinfo=UTC)
    rows = (
        _bar(t0, 100, 102, 99, 101),
        _bar(t0 + timedelta(minutes=15), 101, 104, 100, 103),
        _bar(t0 + timedelta(minutes=30), 103, 106, 102, 105),
    )
    value = _trend_efficiency(rows)

    assert Decimal("0") <= value <= Decimal("1")
    assert value > Decimal("0")


def test_parent_manipulation_and_reclaim_are_directional() -> None:
    bullish = _parent(CrtPureCandidateDirection.BULLISH)
    bearish = _parent(CrtPureCandidateDirection.BEARISH)

    assert _manipulation_depth(bullish) == Decimal("0.25")
    assert _reclaim_depth(bullish) == Decimal("0.25")
    assert _manipulation_depth(bearish) == Decimal("0.25")
    assert _reclaim_depth(bearish) == Decimal("0.25")

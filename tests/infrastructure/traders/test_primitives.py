"""Normal + adversarial tests for the deterministic OHLC/liquidity primitives."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from qore.infrastructure.market_observation import MarketTimeframeCode
from qore.infrastructure.traders.primitives import (
    AmdPhase,
    ClosedCandle,
    DemoTradingPrimitiveValidationError,
    FvgDirection,
    LiquidityLevel,
    SwingPivotKind,
    aggregate_closed_candles,
    closed_candles_as_of,
    detect_amd_context,
    detect_fair_value_gaps,
    detect_swing_pivots,
    false_break_direction,
    is_closed_as_of,
    is_false_break,
    session_extrema,
    sweep_of_level,
    timeframe_seconds,
)

_BASE = datetime(2026, 1, 6, 12, 0, tzinfo=UTC)


def _candle(
    code: MarketTimeframeCode,
    opened_at: datetime,
    o: str,
    h: str,
    lo: str,
    c: str,
) -> ClosedCandle:
    return ClosedCandle(
        timeframe=code,
        opened_at=opened_at,
        closed_at=opened_at + timedelta(seconds=timeframe_seconds(code)),
        open=Decimal(o),
        high=Decimal(h),
        low=Decimal(lo),
        close=Decimal(c),
    )


def _seq(
    code: MarketTimeframeCode,
    start: datetime,
    bars: tuple[tuple[str, str, str, str], ...],
) -> tuple[ClosedCandle, ...]:
    seconds = timeframe_seconds(code)
    return tuple(
        _candle(code, start + timedelta(seconds=i * seconds), o, h, lo, c)
        for i, (o, h, lo, c) in enumerate(bars)
    )


def _m5(
    start: datetime, bars: tuple[tuple[str, str, str, str], ...]
) -> tuple[ClosedCandle, ...]:
    return _seq(MarketTimeframeCode.M5, start, bars)


def _h4(
    start: datetime, bars: tuple[tuple[str, str, str, str], ...]
) -> tuple[ClosedCandle, ...]:
    return _seq(MarketTimeframeCode.H4, start, bars)


def test_closed_candle_validates_exact_interval() -> None:
    with pytest.raises(DemoTradingPrimitiveValidationError):
        ClosedCandle(
            timeframe=MarketTimeframeCode.M5,
            opened_at=_BASE,
            closed_at=_BASE + timedelta(minutes=4),
            open=Decimal("1.0"),
            high=Decimal("1.1"),
            low=Decimal("0.9"),
            close=Decimal("1.05"),
        )


def test_closed_candle_rejects_naive_timestamp() -> None:
    with pytest.raises(DemoTradingPrimitiveValidationError):
        ClosedCandle(
            timeframe=MarketTimeframeCode.M5,
            opened_at=datetime(2026, 1, 6, 12, 0),
            closed_at=datetime(2026, 1, 6, 12, 5),
            open=Decimal("1.0"),
            high=Decimal("1.1"),
            low=Decimal("0.9"),
            close=Decimal("1.05"),
        )


def test_closed_candle_rejects_low_above_high() -> None:
    with pytest.raises(DemoTradingPrimitiveValidationError):
        _candle(MarketTimeframeCode.M5, _BASE, "1.0", "0.9", "1.1", "1.05")


def test_partial_candle_is_not_admissible() -> None:
    candles = _m5(
        _BASE,
        (
            ("1.0", "1.1", "0.9", "1.05"),
            ("1.05", "1.2", "1.0", "1.15"),
        ),
    )
    as_of = candles[0].closed_at - timedelta(seconds=1)
    assert is_closed_as_of(candles[0], as_of=as_of) is False
    assert closed_candles_as_of(candles, as_of=as_of) == ()


def test_aggregation_m5_to_h4_exact_and_no_partial() -> None:
    # 3 full M5 candles + 1 trailing partial: only complete H4 blocks aggregate.
    bars = (
        ("1.0", "1.1", "0.9", "1.05"),
        ("1.05", "1.2", "1.0", "1.15"),
        ("1.15", "1.3", "1.1", "1.25"),
    )
    m5_candles = _m5(_BASE, bars)
    h4_candles = aggregate_closed_candles(
        m5_candles, target=MarketTimeframeCode.H4
    )
    # 3 M5 = 15 minutes < H4 (4 hours), so no H4 candle is produced.
    assert h4_candles == ()


def test_aggregation_m1_to_m5_exact() -> None:
    m1_candles = _seq(
        MarketTimeframeCode.M1,
        _BASE,
        tuple(
            (f"1.{index:03d}", "1.10", "0.90", "1.05")
            for index in range(5)
        ),
    )
    m5_candles = aggregate_closed_candles(m1_candles, target=MarketTimeframeCode.M5)
    assert len(m5_candles) == 1
    agg = m5_candles[0]
    assert agg.open == Decimal("1.000")
    assert agg.close == Decimal("1.05")
    assert agg.high == Decimal("1.10")
    assert agg.low == Decimal("0.90")
    assert agg.opened_at == _BASE
    assert agg.closed_at == _BASE + timedelta(minutes=5)


def test_aggregation_rejects_gap_in_sequence() -> None:
    first = _candle(MarketTimeframeCode.M1, _BASE, "1.0", "1.1", "0.9", "1.0")
    gapped = _candle(
        MarketTimeframeCode.M1,
        _BASE + timedelta(minutes=2),
        "1.0",
        "1.1",
        "0.9",
        "1.0",
    )
    with pytest.raises(DemoTradingPrimitiveValidationError):
        aggregate_closed_candles(
            (first, gapped), target=MarketTimeframeCode.M5
        )


def test_swing_high_detection() -> None:
    candles = _m5(
        _BASE,
        (
            ("1.0", "1.0", "0.9", "0.95"),
            ("0.95", "1.2", "0.9", "1.1"),
            ("1.1", "1.1", "0.8", "0.9"),
        ),
    )
    pivots = detect_swing_pivots(candles, strength=1)
    assert SwingPivotKind.HIGH in {p.kind for p in pivots}


def test_swing_low_detection() -> None:
    candles = _m5(
        _BASE,
        (
            ("1.0", "1.1", "0.9", "1.05"),
            ("0.98", "1.0", "0.8", "0.85"),
            ("0.85", "0.9", "0.75", "0.8"),
            ("0.8", "0.95", "0.78", "0.9"),
            ("0.9", "1.0", "0.8", "0.95"),
        ),
    )
    pivots = detect_swing_pivots(candles, strength=1)
    assert SwingPivotKind.LOW in {p.kind for p in pivots}


def test_sweep_of_high_level() -> None:
    level = LiquidityLevel(Decimal("1.20"), SwingPivotKind.HIGH, "pdh")
    c = _candle(MarketTimeframeCode.M5, _BASE, "1.15", "1.25", "1.14", "1.18")
    assert sweep_of_level(c, level) is True


def test_sweep_of_low_level() -> None:
    level = LiquidityLevel(Decimal("0.80"), SwingPivotKind.LOW, "pdl")
    c = _candle(MarketTimeframeCode.M5, _BASE, "0.85", "0.86", "0.75", "0.82")
    assert sweep_of_level(c, level) is True


def test_sweep_of_level_rejects_reflectively_corrupted_side() -> None:
    # A HIGH level whose side is reflectively replaced by a plain string equal to
    # the StrEnum value must fail closed, never fall through to the LOW branch.
    level = LiquidityLevel(Decimal("1.20"), SwingPivotKind.HIGH, "pdh")
    object.__setattr__(level, "side", "high")
    c = _candle(MarketTimeframeCode.M5, _BASE, "1.15", "1.25", "1.14", "1.18")
    with pytest.raises(DemoTradingPrimitiveValidationError):
        sweep_of_level(c, level)


def test_sweep_of_level_rejects_reflectively_corrupted_price() -> None:
    level = LiquidityLevel(Decimal("1.20"), SwingPivotKind.HIGH, "pdh")
    object.__setattr__(level, "level", 1.5)
    c = _candle(MarketTimeframeCode.M5, _BASE, "1.15", "1.25", "1.14", "1.18")
    with pytest.raises(DemoTradingPrimitiveValidationError):
        sweep_of_level(c, level)


def test_false_break_direction() -> None:
    c = _candle(MarketTimeframeCode.M5, _BASE, "1.0", "1.2", "0.9", "1.05")
    assert (
        false_break_direction(c, Decimal("1.1"), side=SwingPivotKind.HIGH)
        is SwingPivotKind.HIGH
    )
    assert false_break_direction(c, Decimal("1.25"), side=SwingPivotKind.HIGH) is None
    assert is_false_break(c, Decimal("1.1"), side=SwingPivotKind.HIGH) is True


def test_false_break_direction_valid_breakout_is_none() -> None:
    # A candle that closes beyond a HIGH level is a valid breakout, never a
    # false downside break, even when its low straddles the level.
    c = _candle(MarketTimeframeCode.M5, _BASE, "1.0", "1.3", "0.9", "1.25")
    assert false_break_direction(c, Decimal("1.1"), side=SwingPivotKind.HIGH) is None
    # Symmetric: a candle that closes below a LOW level is a valid breakdown.
    d = _candle(MarketTimeframeCode.M5, _BASE, "1.0", "1.1", "0.8", "0.85")
    assert false_break_direction(d, Decimal("0.9"), side=SwingPivotKind.LOW) is None


def test_fvg_detection_bullish_and_bearish() -> None:
    bullish = _m5(
        _BASE,
        (
            ("1.0", "1.1", "0.9", "1.0"),
            ("1.0", "1.05", "0.95", "1.0"),
            ("1.2", "1.3", "1.15", "1.25"),
        ),
    )
    gaps = detect_fair_value_gaps(bullish)
    assert any(g.direction is FvgDirection.BULLISH for g in gaps)


def test_session_extrema() -> None:
    candles = _m5(
        _BASE,
        (
            ("1.0", "1.1", "0.9", "1.0"),
            ("1.0", "1.2", "0.8", "1.1"),
        ),
    )
    extrema = session_extrema(candles)
    assert extrema.high == Decimal("1.2")
    assert extrema.low == Decimal("0.8")


def test_amd_manipulation_and_distribution() -> None:
    # A 4-bar H4 range; the 5th candle sweeps the high and closes below the low
    # (upside manipulation resolves into downside distribution).
    bars = (
        ("1.0", "1.2", "0.9", "1.1"),
        ("1.1", "1.25", "1.0", "1.2"),
        ("1.2", "1.3", "1.1", "1.25"),
        ("1.25", "1.28", "1.15", "1.2"),
        ("1.2", "1.4", "0.85", "0.88"),
    )
    candles = _h4(_BASE, bars)
    amd = detect_amd_context(candles, range_length=4)
    assert amd.phase is AmdPhase.DISTRIBUTION
    assert amd.distribution_direction is SwingPivotKind.LOW


def test_amd_accumulation_when_no_sweep() -> None:
    bars = (
        ("1.0", "1.2", "0.9", "1.1"),
        ("1.1", "1.25", "1.0", "1.2"),
        ("1.2", "1.3", "1.1", "1.25"),
        ("1.25", "1.28", "1.15", "1.2"),
        ("1.2", "1.29", "1.15", "1.25"),
    )
    candles = _h4(_BASE, bars)
    amd = detect_amd_context(candles, range_length=4)
    assert amd.phase is AmdPhase.ACCUMULATION
    assert amd.distribution_direction is None


def test_amd_requires_enough_candles() -> None:
    with pytest.raises(DemoTradingPrimitiveValidationError):
        detect_amd_context(_h4(_BASE, (("1.0", "1.2", "0.9", "1.1"),)), range_length=4)

"""Lane 4: VT-31 Silver Bullet fixed-NY windows + cross-cohort time metamorphics.

Covers the Silver Bullet AM/PM windows, half-open boundary exactness, DST
spring/fall transition semantics, timeframe composition (M1 -> M5 -> M15), and
no-lookahead closed-candle semantics. No relative imports; fully self-contained.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from zoneinfo import ZoneInfo

from qore.infrastructure.market_observation import MarketTimeframeCode
from qore.infrastructure.traders.contracts import (
    DemoTradingDecision,
    DemoTradingEvidenceRef,
    DemoTradingSetupSide,
)
from qore.infrastructure.traders.evaluators import DemoTradingInput, Vt31SilverBullet
from qore.infrastructure.traders.primitives import (
    ClosedCandle,
    DemoTradingPrimitiveValidationError,
    aggregate_closed_candles,
    closed_candles_as_of,
    timeframe_seconds,
)
from qore.infrastructure.traders.windows import (
    NY_AM_SESSION,
    NY_SILVER_BULLET_AM,
    NY_SILVER_BULLET_PM,
    active_silver_bullet_window,
    is_in_window,
)
from qore.kernel.result import Failure, Success

_ET = ZoneInfo("America/New_York")


def _utc(y: int, mo: int, d: int, h: int, mi: int) -> datetime:
    return datetime(y, mo, d, h, mi, tzinfo=_ET).astimezone(UTC)


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
    s = timeframe_seconds(code)
    return tuple(
        _candle(code, start + timedelta(seconds=i * s), o, h, lo, c)
        for i, (o, h, lo, c) in enumerate(bars)
    )


def _m5(
    start: datetime, bars: tuple[tuple[str, str, str, str], ...]
) -> tuple[ClosedCandle, ...]:
    return _seq(MarketTimeframeCode.M5, start, bars)


def _m1(
    start: datetime, bars: tuple[tuple[str, str, str, str], ...]
) -> tuple[ClosedCandle, ...]:
    return _seq(MarketTimeframeCode.M1, start, bars)


def _inp(as_of: datetime, exec_c: tuple[ClosedCandle, ...]) -> DemoTradingInput:
    return DemoTradingInput(
        as_of=as_of,
        evidence_refs=(DemoTradingEvidenceRef("qore:demo:ev:1"),),
        execution_candles=exec_c,
    )


# Known-good 6-candle M5 short sweep+FVG: swing high at index 2, bearish FVG at
# (2,3,4), false upside break at index 5.
_SWEEP_FVG_SHORT = (
    ("1.10", "1.12", "1.09", "1.11"),
    ("1.11", "1.14", "1.10", "1.13"),
    ("1.16", "1.20", "1.15", "1.19"),
    ("1.19", "1.19", "1.13", "1.14"),
    ("1.14", "1.14", "1.10", "1.11"),
    ("1.11", "1.25", "1.10", "1.16"),
)

# Flat consolidation: no swing pivot and no FVG, so VT-31 abstains NO_SWEEP.
_FLAT_NO_SWEEP = (
    ("1.10", "1.11", "1.09", "1.10"),
    ("1.10", "1.11", "1.09", "1.10"),
    ("1.10", "1.11", "1.09", "1.10"),
    ("1.10", "1.11", "1.09", "1.10"),
    ("1.10", "1.11", "1.09", "1.10"),
    ("1.10", "1.11", "1.09", "1.10"),
)

# Three M5 candles that aggregate to one exact M15: open 1.10, high 1.26,
# low 1.09, close 1.25.
_M5_BARS_3 = (
    ("1.10", "1.16", "1.09", "1.15"),
    ("1.15", "1.21", "1.14", "1.20"),
    ("1.20", "1.26", "1.19", "1.25"),
)

# Fifteen M1 candles whose 5-bar blocks reproduce _M5_BARS_3 exactly.
_M1_BARS_15 = (
    ("1.10", "1.12", "1.09", "1.11"),
    ("1.11", "1.13", "1.10", "1.12"),
    ("1.12", "1.14", "1.11", "1.13"),
    ("1.13", "1.15", "1.12", "1.14"),
    ("1.14", "1.16", "1.13", "1.15"),
    ("1.15", "1.17", "1.14", "1.16"),
    ("1.16", "1.18", "1.15", "1.17"),
    ("1.17", "1.19", "1.16", "1.18"),
    ("1.18", "1.20", "1.17", "1.19"),
    ("1.19", "1.21", "1.18", "1.20"),
    ("1.20", "1.22", "1.19", "1.21"),
    ("1.21", "1.23", "1.20", "1.22"),
    ("1.22", "1.24", "1.21", "1.23"),
    ("1.23", "1.25", "1.22", "1.24"),
    ("1.24", "1.26", "1.23", "1.25"),
)


# ---------------------------------------------------------------------------
# VT-31 Silver Bullet fixed NY windows.
# ---------------------------------------------------------------------------


def test_vt31_am_window_positive_short_setup() -> None:
    start = datetime(2026, 1, 6, 15, 0, tzinfo=UTC)  # 10:00 ET
    candles = _m5(start, _SWEEP_FVG_SHORT)
    as_of = candles[-1].closed_at  # 10:30 ET, inside AM window
    result = Vt31SilverBullet().evaluate(_inp(as_of, candles))
    assert isinstance(result, Success)
    out = result.value
    assert out.decision is DemoTradingDecision.SETUP
    assert out.side is DemoTradingSetupSide.SHORT
    assert out.setup is not None


def test_vt31_pm_window_positive_short_setup() -> None:
    start = datetime(2026, 1, 6, 19, 0, tzinfo=UTC)  # 14:00 ET
    candles = _m5(start, _SWEEP_FVG_SHORT)
    as_of = candles[-1].closed_at  # 14:30 ET, inside PM window
    result = Vt31SilverBullet().evaluate(_inp(as_of, candles))
    assert isinstance(result, Success)
    out = result.value
    assert out.decision is DemoTradingDecision.SETUP
    assert out.side is DemoTradingSetupSide.SHORT
    assert out.setup is not None


def test_vt31_window_closed_just_before_am_open() -> None:
    candles = _m5(datetime(2026, 1, 6, 15, 0, tzinfo=UTC), _SWEEP_FVG_SHORT)
    as_of = _utc(2026, 1, 6, 9, 59)  # 09:59 ET, just before AM open
    result = Vt31SilverBullet().evaluate(_inp(as_of, candles))
    assert isinstance(result, Success)
    out = result.value
    assert out.decision is DemoTradingDecision.ABSTAIN
    assert out.abstain_reason is not None
    assert out.abstain_reason.value == "window-closed"


def test_vt31_window_closed_at_exact_am_close() -> None:
    candles = _m5(datetime(2026, 1, 6, 15, 0, tzinfo=UTC), _SWEEP_FVG_SHORT)
    as_of = _utc(2026, 1, 6, 11, 0)  # 11:00 ET is excluded (half-open)
    result = Vt31SilverBullet().evaluate(_inp(as_of, candles))
    assert isinstance(result, Success)
    out = result.value
    assert out.decision is DemoTradingDecision.ABSTAIN
    assert out.abstain_reason is not None
    assert out.abstain_reason.value == "window-closed"


def test_vt31_no_sweep_abstain_inside_window() -> None:
    start = datetime(2026, 1, 6, 15, 0, tzinfo=UTC)  # 10:00 ET
    candles = _m5(start, _FLAT_NO_SWEEP)
    as_of = candles[-1].closed_at  # 10:30 ET, inside AM window
    result = Vt31SilverBullet().evaluate(_inp(as_of, candles))
    assert isinstance(result, Success)
    out = result.value
    assert out.decision is DemoTradingDecision.ABSTAIN
    assert out.abstain_reason is not None
    assert out.abstain_reason.value == "no-sweep"


def test_silver_bullet_window_boundary_half_open() -> None:
    am_open = _utc(2026, 1, 6, 10, 0)
    am_close = _utc(2026, 1, 6, 11, 0)
    pm_open = _utc(2026, 1, 6, 14, 0)
    pm_close = _utc(2026, 1, 6, 15, 0)
    assert is_in_window(am_open, NY_SILVER_BULLET_AM) is True
    assert is_in_window(am_close, NY_SILVER_BULLET_AM) is False
    assert is_in_window(pm_open, NY_SILVER_BULLET_PM) is True
    assert is_in_window(pm_close, NY_SILVER_BULLET_PM) is False
    assert active_silver_bullet_window(am_open) == NY_SILVER_BULLET_AM
    assert active_silver_bullet_window(am_close) is None
    assert active_silver_bullet_window(pm_open) == NY_SILVER_BULLET_PM
    assert active_silver_bullet_window(pm_close) is None


# ---------------------------------------------------------------------------
# Cross-cohort DST / timezone / session metamorphics.
# ---------------------------------------------------------------------------


def test_spring_forward_day_after_session_inside() -> None:
    # 2026 US DST began 2026-03-08 02:00 ET; the day after is EDT.
    assert is_in_window(_utc(2026, 3, 9, 8, 30), NY_AM_SESSION) is True


def test_fall_back_day_after_session_inside() -> None:
    # 2026 US DST ended 2026-11-01 02:00 ET; the day after is EST.
    assert is_in_window(_utc(2026, 11, 2, 8, 30), NY_AM_SESSION) is True


def test_transition_day_07_00_et_classified_inside() -> None:
    # A UTC instant that maps to 07:00 ET on each transition day is inside the
    # NY AM session (its open boundary).
    for year, month, day in ((2026, 3, 8), (2026, 11, 1)):
        instant = _utc(year, month, day, 7, 0)
        local = instant.astimezone(_ET)
        assert (local.hour, local.minute) == (7, 0)
        assert is_in_window(instant, NY_AM_SESSION) is True


def test_dst_metamorphic_wall_clock_shift_changes_offset() -> None:
    # The same wall-clock instant, shifted across the spring-forward boundary,
    # changes UTC offset and therefore the UTC instant by a non-24h delta.
    before_local = datetime(2026, 3, 7, 8, 30, tzinfo=_ET)  # EST (-05:00)
    after_local = datetime(2026, 3, 9, 8, 30, tzinfo=_ET)  # EDT (-04:00)
    assert before_local.utcoffset() == timedelta(hours=-5)
    assert after_local.utcoffset() == timedelta(hours=-4)
    assert before_local.utcoffset() != after_local.utcoffset()
    before_utc = before_local.astimezone(UTC)
    after_utc = after_local.astimezone(UTC)
    assert after_utc - before_utc == timedelta(hours=47)
    # A single 24h wall-clock shift across the spring boundary loses one hour.
    day_after_utc = datetime(2026, 3, 8, 8, 30, tzinfo=_ET).astimezone(UTC)
    assert day_after_utc - before_utc == timedelta(hours=23)


# ---------------------------------------------------------------------------
# Timeframe composition and closed-candle (no-lookahead) semantics.
# ---------------------------------------------------------------------------


def test_aggregate_three_m5_to_one_m15_exact_ohlc() -> None:
    start = datetime(2026, 1, 6, 0, 0, tzinfo=UTC)
    m5 = _m5(start, _M5_BARS_3)
    m15 = aggregate_closed_candles(m5, target=MarketTimeframeCode.M15)
    assert len(m15) == 1
    candle = m15[0]
    assert candle.opened_at == start
    assert candle.closed_at == start + timedelta(seconds=900)
    assert candle.open == Decimal("1.10")
    assert candle.high == Decimal("1.26")
    assert candle.low == Decimal("1.09")
    assert candle.close == Decimal("1.25")


def test_m1_to_m5_to_m15_chaining_consistent() -> None:
    start = datetime(2026, 1, 6, 0, 0, tzinfo=UTC)
    m1 = _m1(start, _M1_BARS_15)
    m1_to_m5 = aggregate_closed_candles(m1, target=MarketTimeframeCode.M5)
    assert m1_to_m5 == _m5(start, _M5_BARS_3)
    m1_to_m15 = aggregate_closed_candles(m1, target=MarketTimeframeCode.M15)
    m5_to_m15 = aggregate_closed_candles(m1_to_m5, target=MarketTimeframeCode.M15)
    assert m5_to_m15 == m1_to_m15
    assert len(m1_to_m15) == 1
    candle = m1_to_m15[0]
    assert candle.opened_at == start
    assert candle.closed_at == start + timedelta(seconds=900)
    assert (candle.open, candle.high, candle.low, candle.close) == (
        Decimal("1.10"),
        Decimal("1.26"),
        Decimal("1.09"),
        Decimal("1.25"),
    )


def test_aggregate_partial_m1_block_dropped() -> None:
    # 4 M1 candles form no complete M5 block; aggregation never leaks a partial.
    start = datetime(2026, 1, 6, 0, 0, tzinfo=UTC)
    m1 = _m1(start, _M1_BARS_15[:4])
    m5 = aggregate_closed_candles(m1, target=MarketTimeframeCode.M5)
    assert m5 == ()


def test_no_lookahead_closed_candles_as_of_excludes_future() -> None:
    start = datetime(2026, 1, 6, 0, 0, tzinfo=UTC)
    m5 = _m5(start, _M5_BARS_3)
    as_of = m5[1].closed_at
    visible = closed_candles_as_of(m5, as_of=as_of)
    assert visible == m5[:2]
    assert all(item.closed_at <= as_of for item in visible)
    assert m5[2].closed_at > as_of
    assert m5[2] not in visible
    # A candle becomes admissible at the exact instant it closes (inclusive).
    assert closed_candles_as_of(m5, as_of=m5[0].closed_at) == m5[:1]


def test_vt31_valid_breakout_straddle_abstains() -> None:
    # A valid upside breakout of the swing high (1.20) whose low (1.10) straddles
    # below it must abstain (NO_SWEEP), never raise or emit a reversed setup.
    bars = _SWEEP_FVG_SHORT[:-1] + (("1.18", "1.30", "1.10", "1.25"),)
    start = datetime(2026, 1, 6, 15, 0, tzinfo=UTC)  # 10:00 ET (AM window)
    candles = _m5(start, bars)
    result = Vt31SilverBullet().evaluate(_inp(candles[-1].closed_at, candles))
    assert isinstance(result, Success)
    assert result.value.decision is DemoTradingDecision.ABSTAIN
    assert result.value.abstain_reason is not None
    assert result.value.abstain_reason.value == "no-sweep"


def test_vt31_empty_execution_abstains() -> None:
    # Inside the AM window with no closed evidence, VT-31 must abstain, not raise.
    as_of = _utc(2026, 1, 6, 10, 30)
    result = Vt31SilverBullet().evaluate(_inp(as_of, ()))
    assert isinstance(result, Success)
    assert result.value.decision is DemoTradingDecision.ABSTAIN
    assert result.value.abstain_reason is not None
    assert result.value.abstain_reason.value == "no-sweep"


def test_vt31_rejects_m1_execution_candles() -> None:
    # The frozen deterministic VT-31 path is M5 (M1 refinement is a documented
    # REQUIRES_FORMALIZATION gap), so M1 execution candles are rejected.
    start = datetime(2026, 1, 6, 15, 0, tzinfo=UTC)
    candles = _m1(start, _M1_BARS_15)
    result = Vt31SilverBullet().evaluate(_inp(candles[-1].closed_at, candles))
    assert isinstance(result, Failure)


def test_aggregate_offset_m5_input_rejected() -> None:
    # Three M5 candles at 00:05/00:10/00:15 are contiguous but misaligned to the
    # M15 grid (which opens at 00:00/00:15/...). Aggregation must fail closed.
    start = datetime(2026, 1, 6, 0, 5, tzinfo=UTC)
    m5 = _m5(start, _M5_BARS_3)
    try:
        aggregate_closed_candles(m5, target=MarketTimeframeCode.M15)
    except DemoTradingPrimitiveValidationError:
        return
    raise AssertionError("misaligned aggregation source must fail closed")


def test_silver_bullet_windows_dst_transition_days() -> None:
    # The Silver Bullet AM/PM windows are wall-clock-exact across DST transitions.
    assert active_silver_bullet_window(_utc(2026, 3, 8, 10, 0)) == NY_SILVER_BULLET_AM
    assert active_silver_bullet_window(_utc(2026, 3, 8, 14, 0)) == NY_SILVER_BULLET_PM
    assert active_silver_bullet_window(_utc(2026, 11, 1, 10, 0)) == NY_SILVER_BULLET_AM
    assert active_silver_bullet_window(_utc(2026, 11, 1, 14, 0)) == NY_SILVER_BULLET_PM

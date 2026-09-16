"""Frozen ICT Turtle Soup R1 liquidity-sweep + CISD research mechanics."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from decimal import Decimal
from enum import StrEnum
from zoneinfo import ZoneInfo

NY = ZoneInfo("America/New_York")
BAR_DURATION = timedelta(minutes=5)
LONDON_START = time(2, 0)
LONDON_END = time(5, 0)
NY_AM_START = time(8, 30)
NY_AM_END = time(11, 0)
MIN_PROJECTED_R = Decimal("1.5")
EXPECTED_LONDON_BARS = 36
EXPECTED_NY_AM_BARS = 30


class Side(StrEnum):
    LONG = "long"
    SHORT = "short"


class DetectionStatus(StrEnum):
    SIGNAL = "signal"
    NO_SWEEP = "no-sweep"
    NO_RECLAIM = "no-reclaim"
    NO_OPPOSING_SERIES = "no-opposing-series"
    NO_CISD = "no-cisd"
    NO_CAUSAL_ENTRY_BAR = "no-causal-entry-bar"
    INVALID_GEOMETRY = "invalid-geometry"
    INSUFFICIENT_PROJECTED_R = "insufficient-projected-r"
    AMBIGUOUS_BOTH_SIDES = "ambiguous-both-sides"
    DATA_INVALID = "data-invalid"


class ExitReason(StrEnum):
    STOP = "stop"
    GAP_STOP = "gap-stop"
    TARGET = "target"
    TIME_EXIT = "time-exit"


@dataclass(frozen=True, slots=True)
class M5Bar:
    opened_at: datetime
    closed_at: datetime
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal

    def __post_init__(self) -> None:
        if self.opened_at.tzinfo is None or self.opened_at.utcoffset() is None:
            raise ValueError("opened_at must be timezone-aware")
        if self.closed_at.tzinfo is None or self.closed_at.utcoffset() is None:
            raise ValueError("closed_at must be timezone-aware")
        if self.closed_at - self.opened_at != BAR_DURATION:
            raise ValueError("R1 requires exact five-minute bars")
        if self.high < max(self.open, self.close) or self.low > min(self.open, self.close):
            raise ValueError("OHLC body lies outside high/low")
        if self.high < self.low:
            raise ValueError("high must be >= low")


@dataclass(frozen=True, slots=True)
class ICTTurtleSoupSignal:
    identity: str
    symbol: str
    ny_date: date
    side: Side
    london_high: Decimal
    london_low: Decimal
    sweep_at: datetime
    sweep_extreme: Decimal
    reclaim_at: datetime
    cisd_at: datetime
    cisd_threshold: Decimal
    entry_at: datetime
    entry: Decimal
    stop: Decimal
    target: Decimal
    projected_r: Decimal


@dataclass(frozen=True, slots=True)
class Detection:
    status: DetectionStatus
    signal: ICTTurtleSoupSignal | None
    detail: str


@dataclass(frozen=True, slots=True)
class ReplayTrade:
    signal: ICTTurtleSoupSignal
    exit_at: datetime
    exit_price: Decimal
    exit_reason: ExitReason
    gross_r: Decimal


def _ny_time(value: datetime) -> time:
    return value.astimezone(NY).time().replace(tzinfo=None)


def _ny_date(value: datetime) -> date:
    return value.astimezone(NY).date()


def _within(value: datetime, start: time, end: time) -> bool:
    local = _ny_time(value)
    return start <= local < end


def _session_bars(bars: tuple[M5Bar, ...], start: time, end: time) -> tuple[M5Bar, ...]:
    return tuple(bar for bar in bars if _within(bar.opened_at, start, end))


def _contiguous(bars: tuple[M5Bar, ...]) -> bool:
    return all(
        left.closed_at == right.opened_at
        for left, right in zip(bars, bars[1:], strict=False)
    )


def _validate_day(bars: tuple[M5Bar, ...]) -> tuple[date, tuple[M5Bar, ...], tuple[M5Bar, ...]]:
    if not bars:
        raise ValueError("empty M5 evidence")
    ordered = tuple(sorted(bars, key=lambda item: item.opened_at))
    dates = {_ny_date(bar.opened_at) for bar in ordered}
    if len(dates) != 1:
        raise ValueError("R1 evaluation must contain exactly one New-York date")
    ny_date = next(iter(dates))
    london = _session_bars(ordered, LONDON_START, LONDON_END)
    ny_am = _session_bars(ordered, NY_AM_START, NY_AM_END)
    if len(london) != EXPECTED_LONDON_BARS or not _contiguous(london):
        raise ValueError("London M5 evidence is missing or discontinuous")
    if len(ny_am) != EXPECTED_NY_AM_BARS or not _contiguous(ny_am):
        raise ValueError("New-York-AM M5 evidence is missing or discontinuous")
    return ny_date, london, ny_am


def _opposing(bar: M5Bar, side: Side) -> bool:
    if side is Side.LONG:
        return bar.close < bar.open
    return bar.close > bar.open


def _opposing_series_threshold(
    ny_am: tuple[M5Bar, ...], sweep_index: int, side: Side
) -> Decimal | None:
    cursor = sweep_index if _opposing(ny_am[sweep_index], side) else sweep_index - 1
    if cursor < 0 or not _opposing(ny_am[cursor], side):
        return None
    while cursor > 0 and _opposing(ny_am[cursor - 1], side):
        cursor -= 1
    return ny_am[cursor].open


def _sweeps(bar: M5Bar, side: Side, london_high: Decimal, london_low: Decimal) -> bool:
    if side is Side.LONG:
        return bar.low < london_low
    return bar.high > london_high


def _reclaims(bar: M5Bar, side: Side, london_high: Decimal, london_low: Decimal) -> bool:
    if side is Side.LONG:
        return bar.close > london_low
    return bar.close < london_high


def _confirms_cisd(bar: M5Bar, side: Side, threshold: Decimal) -> bool:
    if side is Side.LONG:
        return bar.close > threshold
    return bar.close < threshold


def _projected_r(side: Side, entry: Decimal, stop: Decimal, target: Decimal) -> Decimal | None:
    risk = entry - stop if side is Side.LONG else stop - entry
    reward = target - entry if side is Side.LONG else entry - target
    if risk <= 0 or reward <= 0:
        return None
    return reward / risk


def _detect_side(
    symbol: str,
    ny_date: date,
    ny_am: tuple[M5Bar, ...],
    london_high: Decimal,
    london_low: Decimal,
    tick_size: Decimal,
    side: Side,
) -> Detection:
    sweep_indices = [
        index
        for index, bar in enumerate(ny_am)
        if _sweeps(bar, side, london_high, london_low)
    ]
    if not sweep_indices:
        return Detection(DetectionStatus.NO_SWEEP, None, f"{side}: no London-range sweep")

    sweep_index = sweep_indices[0]
    sweep_at = ny_am[sweep_index].opened_at
    threshold = _opposing_series_threshold(ny_am, sweep_index, side)
    if threshold is None:
        return Detection(
            DetectionStatus.NO_OPPOSING_SERIES,
            None,
            f"{side}: sweep has no contiguous opposing-body series",
        )

    reclaim_index: int | None = None
    cisd_index: int | None = None
    for index in range(sweep_index, len(ny_am)):
        bar = ny_am[index]
        if reclaim_index is None and _reclaims(bar, side, london_high, london_low):
            reclaim_index = index
        if reclaim_index is not None and _confirms_cisd(bar, side, threshold):
            cisd_index = index
            break

    if reclaim_index is None:
        return Detection(DetectionStatus.NO_RECLAIM, None, f"{side}: sweep never reclaimed")
    if cisd_index is None:
        return Detection(DetectionStatus.NO_CISD, None, f"{side}: reclaim never confirmed CISD")

    entry_index = cisd_index + 1
    if entry_index >= len(ny_am):
        return Detection(
            DetectionStatus.NO_CAUSAL_ENTRY_BAR,
            None,
            f"{side}: CISD confirmed on final NY-AM bar",
        )

    entry_bar = ny_am[entry_index]
    entry = entry_bar.open
    adverse_bars = ny_am[sweep_index : cisd_index + 1]
    if side is Side.LONG:
        sweep_extreme = min(bar.low for bar in adverse_bars)
        stop = sweep_extreme - tick_size
        target = london_high
    else:
        sweep_extreme = max(bar.high for bar in adverse_bars)
        stop = sweep_extreme + tick_size
        target = london_low

    projected = _projected_r(side, entry, stop, target)
    if projected is None:
        return Detection(
            DetectionStatus.INVALID_GEOMETRY,
            None,
            f"{side}: entry/stop/target geometry is non-positive",
        )
    if projected < MIN_PROJECTED_R:
        return Detection(
            DetectionStatus.INSUFFICIENT_PROJECTED_R,
            None,
            f"{side}: projected target is {projected}R < {MIN_PROJECTED_R}R",
        )

    signal = ICTTurtleSoupSignal(
        identity="ICT_TURTLE_SOUP_R1_CISD_SESSION",
        symbol=symbol,
        ny_date=ny_date,
        side=side,
        london_high=london_high,
        london_low=london_low,
        sweep_at=sweep_at,
        sweep_extreme=sweep_extreme,
        reclaim_at=ny_am[reclaim_index].closed_at,
        cisd_at=ny_am[cisd_index].closed_at,
        cisd_threshold=threshold,
        entry_at=entry_bar.opened_at,
        entry=entry,
        stop=stop,
        target=target,
        projected_r=projected,
    )
    return Detection(DetectionStatus.SIGNAL, signal, f"{side}: deterministic R1 signal")


def detect_ict_turtle_soup_r1(
    symbol: str,
    bars: tuple[M5Bar, ...],
    tick_size: Decimal,
) -> Detection:
    """Detect at most one frozen R1 signal for one symbol/New-York date."""
    if tick_size <= 0:
        return Detection(DetectionStatus.DATA_INVALID, None, "tick_size must be positive")
    try:
        ny_date, london, ny_am = _validate_day(bars)
    except ValueError as exc:
        return Detection(DetectionStatus.DATA_INVALID, None, str(exc))

    london_high = max(bar.high for bar in london)
    london_low = min(bar.low for bar in london)
    long_result = _detect_side(
        symbol, ny_date, ny_am, london_high, london_low, tick_size, Side.LONG
    )
    short_result = _detect_side(
        symbol, ny_date, ny_am, london_high, london_low, tick_size, Side.SHORT
    )

    long_signal = long_result.status is DetectionStatus.SIGNAL
    short_signal = short_result.status is DetectionStatus.SIGNAL
    if long_signal and short_signal:
        return Detection(
            DetectionStatus.AMBIGUOUS_BOTH_SIDES,
            None,
            "both LONG and SHORT completed eligibility in the same symbol/date",
        )
    if long_signal:
        return long_result
    if short_signal:
        return short_result

    priority = (
        DetectionStatus.INSUFFICIENT_PROJECTED_R,
        DetectionStatus.INVALID_GEOMETRY,
        DetectionStatus.NO_CAUSAL_ENTRY_BAR,
        DetectionStatus.NO_CISD,
        DetectionStatus.NO_RECLAIM,
        DetectionStatus.NO_OPPOSING_SERIES,
        DetectionStatus.NO_SWEEP,
    )
    for status in priority:
        for result in (long_result, short_result):
            if result.status is status:
                return result
    return Detection(DetectionStatus.DATA_INVALID, None, "unreachable detection state")


def replay_ict_turtle_soup_r1(
    signal: ICTTurtleSoupSignal,
    bars: tuple[M5Bar, ...],
) -> ReplayTrade:
    """Replay frozen R1 stop/target/time containment with conservative M5 ordering."""
    ny_am = tuple(
        bar
        for bar in sorted(bars, key=lambda item: item.opened_at)
        if _ny_date(bar.opened_at) == signal.ny_date
        and _within(bar.opened_at, NY_AM_START, NY_AM_END)
        and bar.opened_at >= signal.entry_at
    )
    if not ny_am or ny_am[0].opened_at != signal.entry_at:
        raise ValueError("entry bar missing from replay evidence")

    risk = (
        signal.entry - signal.stop
        if signal.side is Side.LONG
        else signal.stop - signal.entry
    )
    if risk <= 0:
        raise ValueError("signal has invalid risk")

    for bar in ny_am:
        if signal.side is Side.LONG:
            if bar.open <= signal.stop:
                exit_price = bar.open
                reason = ExitReason.GAP_STOP
            elif bar.open >= signal.target:
                exit_price = signal.target
                reason = ExitReason.TARGET
            elif bar.low <= signal.stop:
                exit_price = signal.stop
                reason = ExitReason.STOP
            elif bar.high >= signal.target:
                exit_price = signal.target
                reason = ExitReason.TARGET
            else:
                continue
            gross = (exit_price - signal.entry) / risk
        else:
            if bar.open >= signal.stop:
                exit_price = bar.open
                reason = ExitReason.GAP_STOP
            elif bar.open <= signal.target:
                exit_price = signal.target
                reason = ExitReason.TARGET
            elif bar.high >= signal.stop:
                exit_price = signal.stop
                reason = ExitReason.STOP
            elif bar.low <= signal.target:
                exit_price = signal.target
                reason = ExitReason.TARGET
            else:
                continue
            gross = (signal.entry - exit_price) / risk
        return ReplayTrade(signal, bar.opened_at, exit_price, reason, gross)

    final_bar = ny_am[-1]
    exit_price = final_bar.close
    gross = (
        (exit_price - signal.entry) / risk
        if signal.side is Side.LONG
        else (signal.entry - exit_price) / risk
    )
    return ReplayTrade(signal, final_bar.closed_at, exit_price, ExitReason.TIME_EXIT, gross)

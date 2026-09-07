"""Deterministic shared OHLC/liquidity/structure primitives for the DEMO cohort.

Every primitive is a pure, deterministic function over immutable closed-candle
evidence. No primitive reads ambient time, random identity, partial (still-open)
candles, or any future candle beyond the supplied ``as_of`` closed-candle view.
Aggregation never leaks a partial candle: the target (higher-timeframe) candle
is produced only when a complete, contiguous, aligned set of lower candles is
available, so a trailing partial candle is rejected fail-closed.

Prices are exact ``Decimal`` values; ``float`` is never used for economically
meaningful price material.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from enum import StrEnum

from qore.infrastructure.market_observation import MarketTimeframeCode
from qore.kernel.errors import InfrastructureError

_TIMEFRAME_SECONDS: dict[MarketTimeframeCode, int] = {
    MarketTimeframeCode.M1: 60,
    MarketTimeframeCode.M2: 120,
    MarketTimeframeCode.M3: 180,
    MarketTimeframeCode.M4: 240,
    MarketTimeframeCode.M5: 300,
    MarketTimeframeCode.M10: 600,
    MarketTimeframeCode.M15: 900,
    MarketTimeframeCode.M30: 1800,
    MarketTimeframeCode.H1: 3600,
    MarketTimeframeCode.H4: 14400,
    MarketTimeframeCode.H12: 43200,
}

# Timeframe families supported by the deterministic DEMO cohort.
COHORT_TIMEFRAMES: frozenset[MarketTimeframeCode] = frozenset(
    {
        MarketTimeframeCode.M1,
        MarketTimeframeCode.M5,
        MarketTimeframeCode.M15,
        MarketTimeframeCode.H4,
    }
)

_EPOCH = datetime(1970, 1, 1, tzinfo=UTC)


def _epoch_micros(value: datetime) -> int:
    """Exact integer microseconds since the Unix epoch (no float arithmetic)."""

    delta = value.astimezone(UTC) - _EPOCH
    return delta.days * 86_400_000_000 + delta.seconds * 1_000_000 + delta.microseconds


def _is_grid_aligned(value: datetime, seconds: int) -> bool:
    """Return whether an instant is aligned to an epoch-based timeframe grid."""

    return _epoch_micros(value) % (seconds * 1_000_000) == 0


class DemoTradingPrimitiveError(InfrastructureError):
    """Base error for deterministic DEMO Trader primitives."""

    __slots__ = ()


class DemoTradingPrimitiveValidationError(DemoTradingPrimitiveError):
    """Violation of a deterministic primitive invariant."""

    __slots__ = ()


def _validate_timestamp(value: datetime, *, field_name: str) -> None:
    if type(value) is not datetime:
        raise DemoTradingPrimitiveValidationError(f"{field_name} must be a datetime")
    if value.tzinfo is None or value.utcoffset() is None:
        raise DemoTradingPrimitiveValidationError(
            f"{field_name} must be timezone-aware"
        )


def _validate_price(value: Decimal, *, field_name: str) -> None:
    if type(value) is not Decimal or not value.is_finite() or value <= 0:
        raise DemoTradingPrimitiveValidationError(
            f"{field_name} must be a positive finite Decimal"
        )


def timeframe_seconds(code: MarketTimeframeCode) -> int:
    """Return exact fixed seconds for a cohort-supported timeframe."""

    if type(code) is not MarketTimeframeCode:
        raise DemoTradingPrimitiveValidationError(
            "timeframe must be an exact MarketTimeframeCode"
        )
    seconds = _TIMEFRAME_SECONDS.get(code)
    if seconds is None:
        raise DemoTradingPrimitiveValidationError(
            f"timeframe {code.value} is not supported by the DEMO cohort"
        )
    return seconds


def _timeframe_valid(code: MarketTimeframeCode) -> None:
    timeframe_seconds(code)
    if code not in COHORT_TIMEFRAMES:
        raise DemoTradingPrimitiveValidationError(
            f"timeframe {code.value} is outside the cohort M1/M5/M15/H4 family"
        )


@dataclass(frozen=True, slots=True)
class ClosedCandle:
    """One canonical closed OHLC candle with exact Decimal prices.

    ``closed_at`` is exclusive in the replay sense: the candle's evidence is only
    admissible when ``as_of >= closed_at``, so a still-forming (partial) candle
    cannot leak into a deterministic decision.
    """

    timeframe: MarketTimeframeCode
    opened_at: datetime
    closed_at: datetime
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal

    def __post_init__(self) -> None:
        _timeframe_valid(self.timeframe)
        _validate_timestamp(self.opened_at, field_name="candle opened_at")
        _validate_timestamp(self.closed_at, field_name="candle closed_at")
        if self.closed_at <= self.opened_at:
            raise DemoTradingPrimitiveValidationError(
                "candle closed_at must be after opened_at"
            )
        seconds = timeframe_seconds(self.timeframe)
        if (self.closed_at - self.opened_at).total_seconds() != seconds:
            raise DemoTradingPrimitiveValidationError(
                "candle interval must exactly match its timeframe"
            )
        for field_name, value in (
            ("open", self.open),
            ("high", self.high),
            ("low", self.low),
            ("close", self.close),
        ):
            _validate_price(value, field_name=f"candle {field_name}")
        if self.low > self.high:
            raise DemoTradingPrimitiveValidationError("candle low must not exceed high")
        if not self.low <= self.open <= self.high:
            raise DemoTradingPrimitiveValidationError("candle open must be within low/high")
        if not self.low <= self.close <= self.high:
            raise DemoTradingPrimitiveValidationError("candle close must be within low/high")

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.timeframe.value,
            self.opened_at.astimezone(UTC).isoformat(timespec="microseconds"),
            self.closed_at.astimezone(UTC).isoformat(timespec="microseconds"),
            format(self.open, "f"),
            format(self.high, "f"),
            format(self.low, "f"),
            format(self.close, "f"),
        )


def validate_closed_candle_sequence(
    candles: tuple[ClosedCandle, ...],
) -> tuple[ClosedCandle, ...]:
    """Validate a closed-candle sequence is typed, non-empty, ordered, contiguous.

    Returns the input ordered ascending by ``closed_at``. Rejects a partial,
    out-of-order, gap-bearing, or mixed-timeframe sequence fail-closed.
    """

    if type(candles) is not tuple or any(
        type(item) is not ClosedCandle for item in candles
    ):
        raise DemoTradingPrimitiveValidationError(
            "candles must be an immutable ClosedCandle tuple"
        )
    if not candles:
        raise DemoTradingPrimitiveValidationError("candle sequence must be non-empty")
    ordered = tuple(sorted(candles, key=lambda item: item.closed_at))
    timeframe = ordered[0].timeframe
    for item in ordered:
        if type(item.timeframe) is not MarketTimeframeCode or item.timeframe is not timeframe:
            raise DemoTradingPrimitiveValidationError(
                "candle sequence must be single-timeframe"
            )
    previous: ClosedCandle | None = None
    for item in ordered:
        if previous is not None and item.opened_at != previous.closed_at:
            raise DemoTradingPrimitiveValidationError(
                "candle sequence must be contiguous with no gaps or overlaps"
            )
        previous = item
    return ordered


def is_closed_as_of(candle: ClosedCandle, *, as_of: datetime) -> bool:
    """Return whether a candle is closed (admissible) at an explicit instant."""

    if type(candle) is not ClosedCandle:
        raise DemoTradingPrimitiveValidationError("candle must be ClosedCandle")
    _validate_timestamp(as_of, field_name="as_of")
    return as_of >= candle.closed_at


def closed_candles_as_of(
    candles: tuple[ClosedCandle, ...],
    *,
    as_of: datetime,
) -> tuple[ClosedCandle, ...]:
    """Return only candles closed at ``as_of`` (no partial-candle leakage)."""

    ordered = validate_closed_candle_sequence(candles)
    _validate_timestamp(as_of, field_name="as_of")
    return tuple(item for item in ordered if is_closed_as_of(item, as_of=as_of))


def aggregate_closed_candles(
    candles: tuple[ClosedCandle, ...],
    *,
    target: MarketTimeframeCode,
) -> tuple[ClosedCandle, ...]:
    """Aggregate complete contiguous lower candles into exact higher candles.

    The higher candle is emitted only when a full, contiguous, aligned block of
    lower candles is present; a trailing incomplete block is dropped (never a
    partial higher candle). Alignment requires the higher candle's open to be the
    first lower open and its close to be the last lower close.
    """

    ordered = validate_closed_candle_sequence(candles)
    _timeframe_valid(target)
    lower_seconds = timeframe_seconds(ordered[0].timeframe)
    upper_seconds = timeframe_seconds(target)
    if upper_seconds <= lower_seconds:
        raise DemoTradingPrimitiveValidationError(
            "aggregation target must be a higher timeframe"
        )
    if upper_seconds % lower_seconds != 0:
        raise DemoTradingPrimitiveValidationError(
            "aggregation target must be a whole multiple of the source timeframe"
        )
    block_size = upper_seconds // lower_seconds

    aggregated: list[ClosedCandle] = []
    block: list[ClosedCandle] = []
    for candle in ordered:
        if block and candle.opened_at != block[-1].closed_at:
            block = []
        block.append(candle)
        if len(block) == block_size:
            opened_at = block[0].opened_at
            if not _is_grid_aligned(opened_at, upper_seconds):
                raise DemoTradingPrimitiveValidationError(
                    "aggregation source must be aligned to the target timeframe grid"
                )
            closed_at = block[-1].closed_at
            open_price = block[0].open
            close_price = block[-1].close
            high = max((item.high for item in block), key=lambda value: value)
            low = min((item.low for item in block), key=lambda value: value)
            aggregated.append(
                ClosedCandle(
                    timeframe=target,
                    opened_at=opened_at,
                    closed_at=closed_at,
                    open=open_price,
                    high=high,
                    low=low,
                    close=close_price,
                )
            )
            block = []
    return tuple(aggregated)


class SwingPivotKind(StrEnum):
    HIGH = "high"
    LOW = "low"


@dataclass(frozen=True, slots=True)
class SwingPivot:
    """One deterministic swing pivot over a closed-candle sequence."""

    index: int
    kind: SwingPivotKind
    price: Decimal
    closed_at: datetime

    def __post_init__(self) -> None:
        if type(self.index) is not int or self.index < 0:
            raise DemoTradingPrimitiveValidationError("pivot index must be a non-negative int")
        if type(self.kind) is not SwingPivotKind:
            raise DemoTradingPrimitiveValidationError("pivot kind must be SwingPivotKind")
        _validate_price(self.price, field_name="pivot price")
        _validate_timestamp(self.closed_at, field_name="pivot closed_at")

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.index,
            self.kind.value,
            format(self.price, "f"),
            self.closed_at.astimezone(UTC).isoformat(timespec="microseconds"),
        )


def detect_swing_pivots(
    candles: tuple[ClosedCandle, ...],
    *,
    strength: int = 1,
) -> tuple[SwingPivot, ...]:
    """Detect swing highs/lows over a closed-candle sequence.

    A swing high at index ``i`` requires ``strength`` strictly-lower highs on
    each side; a swing low requires ``strength`` strictly-higher lows on each
    side. Pivots cannot be detected on the trailing ``strength`` candles because
    their confirmation candles may not be closed yet.
    """

    ordered = validate_closed_candle_sequence(candles)
    if type(strength) is not int or strength < 1:
        raise DemoTradingPrimitiveValidationError("pivot strength must be a positive int")
    pivots: list[SwingPivot] = []
    for index in range(strength, len(ordered) - strength):
        window = ordered[index - strength : index + strength + 1]
        candle = ordered[index]
        if all(candle.high > item.high for item in window if item is not candle):
            pivots.append(
                SwingPivot(
                    index=index,
                    kind=SwingPivotKind.HIGH,
                    price=candle.high,
                    closed_at=candle.closed_at,
                )
            )
        if all(candle.low < item.low for item in window if item is not candle):
            pivots.append(
                SwingPivot(
                    index=index,
                    kind=SwingPivotKind.LOW,
                    price=candle.low,
                    closed_at=candle.closed_at,
                )
            )
    return tuple(pivots)


@dataclass(frozen=True, slots=True)
class LiquidityLevel:
    """One deterministic liquidity level (e.g. PDH/PDL or session extreme)."""

    level: Decimal
    side: SwingPivotKind
    label: str

    def __post_init__(self) -> None:
        _validate_price(self.level, field_name="liquidity level")
        if type(self.side) is not SwingPivotKind:
            raise DemoTradingPrimitiveValidationError(
                "liquidity side must be SwingPivotKind"
            )
        if type(self.label) is not str or not self.label.strip():
            raise DemoTradingPrimitiveValidationError("liquidity label must be non-empty")

    def logical_values(self) -> tuple[object, ...]:
        return (format(self.level, "f"), self.side.value, self.label)


def sweep_of_level(candle: ClosedCandle, level: LiquidityLevel) -> bool:
    """Return whether a candle sweeps a level and closes back on the other side.

    A HIGH level is swept when ``candle.high > level`` but ``candle.close < level``
    (a false upside break). A LOW level is swept when ``candle.low < level`` but
    ``candle.close > level`` (a false downside break). This is the deterministic
    liquidity-sweep (stop-hunt) primitive used across the cohort.
    """

    if type(candle) is not ClosedCandle:
        raise DemoTradingPrimitiveValidationError("candle must be ClosedCandle")
    if type(level) is not LiquidityLevel:
        raise DemoTradingPrimitiveValidationError("level must be LiquidityLevel")
    # Re-enter the level invariant: a reflectively corrupted ``side`` (a plain
    # string that hash/equality-collides with a StrEnum member) must fail closed
    # here instead of silently falling through to the LOW branch and misreading
    # the sweep direction.
    level.__post_init__()
    if level.side is SwingPivotKind.HIGH:
        return candle.high > level.level and candle.close < level.level
    return candle.low < level.level and candle.close > level.level


def is_false_break(
    candle: ClosedCandle, level: Decimal, *, side: SwingPivotKind
) -> bool:
    """Return whether a candle false-breaks a price level of a given side.

    A HIGH (resistance) level is false-broken when ``candle.high > level`` and
    ``candle.close < level``; a LOW (support) level is false-broken when
    ``candle.low < level`` and ``candle.close > level``. Binding the level's
    side prevents a genuine breakout (a close beyond the level) from being
    misread as a false break.
    """

    if type(candle) is not ClosedCandle:
        raise DemoTradingPrimitiveValidationError("candle must be ClosedCandle")
    _validate_price(level, field_name="false-break level")
    if type(side) is not SwingPivotKind:
        raise DemoTradingPrimitiveValidationError(
            "false-break side must be SwingPivotKind"
        )
    if side is SwingPivotKind.HIGH:
        return candle.high > level and candle.close < level
    return candle.low < level and candle.close > level


def false_break_direction(
    candle: ClosedCandle, level: Decimal, *, side: SwingPivotKind
) -> SwingPivotKind | None:
    """Return the false-break reversal direction for a level of a given side.

    ``side`` is the level's kind: a HIGH (resistance) level swept by an upside
    false break returns ``SwingPivotKind.HIGH``; a LOW (support) level swept by
    a downside false break returns ``SwingPivotKind.LOW``. A genuine breakout
    (close beyond the level) or no break returns None.
    """

    if type(candle) is not ClosedCandle:
        raise DemoTradingPrimitiveValidationError("candle must be ClosedCandle")
    _validate_price(level, field_name="false-break level")
    if type(side) is not SwingPivotKind:
        raise DemoTradingPrimitiveValidationError(
            "false-break side must be SwingPivotKind"
        )
    if side is SwingPivotKind.HIGH:
        return (
            SwingPivotKind.HIGH
            if candle.high > level and candle.close < level
            else None
        )
    return (
        SwingPivotKind.LOW if candle.low < level and candle.close > level else None
    )


class FvgDirection(StrEnum):
    BULLISH = "bullish"
    BEARISH = "bearish"


@dataclass(frozen=True, slots=True)
class FairValueGap:
    """One deterministic three-candle imbalance (FVG)."""

    direction: FvgDirection
    upper: Decimal
    lower: Decimal
    formed_at: datetime

    def __post_init__(self) -> None:
        if type(self.direction) is not FvgDirection:
            raise DemoTradingPrimitiveValidationError("FVG direction must be FvgDirection")
        _validate_price(self.upper, field_name="FVG upper")
        _validate_price(self.lower, field_name="FVG lower")
        if self.lower >= self.upper:
            raise DemoTradingPrimitiveValidationError("FVG lower must be below upper")
        _validate_timestamp(self.formed_at, field_name="FVG formed_at")

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.direction.value,
            format(self.upper, "f"),
            format(self.lower, "f"),
            self.formed_at.astimezone(UTC).isoformat(timespec="microseconds"),
        )


def detect_fair_value_gaps(
    candles: tuple[ClosedCandle, ...],
) -> tuple[FairValueGap, ...]:
    """Detect three-candle imbalances deterministically.

    A bullish FVG exists when candle[i+2].low > candle[i].high (gap between
    candle[i].high and candle[i+2].low). A bearish FVG exists when
    candle[i+2].high < candle[i].low. The gap is bounded by the disjoint wicks.
    """

    ordered = validate_closed_candle_sequence(candles)
    gaps: list[FairValueGap] = []
    for index in range(len(ordered) - 2):
        first = ordered[index]
        third = ordered[index + 2]
        if third.low > first.high:
            gaps.append(
                FairValueGap(
                    direction=FvgDirection.BULLISH,
                    upper=third.low,
                    lower=first.high,
                    formed_at=third.closed_at,
                )
            )
        elif third.high < first.low:
            gaps.append(
                FairValueGap(
                    direction=FvgDirection.BEARISH,
                    upper=first.low,
                    lower=third.high,
                    formed_at=third.closed_at,
                )
            )
    return tuple(gaps)


@dataclass(frozen=True, slots=True)
class SessionExtrema:
    """Deterministic session (or prior-day) high/low extrema."""

    high: Decimal
    low: Decimal

    def __post_init__(self) -> None:
        _validate_price(self.high, field_name="session high")
        _validate_price(self.low, field_name="session low")
        if self.low > self.high:
            raise DemoTradingPrimitiveValidationError("session low must not exceed high")

    def logical_values(self) -> tuple[object, ...]:
        return (format(self.high, "f"), format(self.low, "f"))


def session_extrema(candles: tuple[ClosedCandle, ...]) -> SessionExtrema:
    """Compute the deterministic high/low extrema of a closed-candle sequence."""

    ordered = validate_closed_candle_sequence(candles)
    high = max((item.high for item in ordered), key=lambda value: value)
    low = min((item.low for item in ordered), key=lambda value: value)
    return SessionExtrema(high=high, low=low)


def prior_day_extrema(
    candles: tuple[ClosedCandle, ...],
    *,
    prior_day: datetime,
    timezone_name: str,
) -> SessionExtrema:
    """Compute PDH/PDL from candles whose local date equals the prior day.

    ``prior_day`` is an explicit timezone-aware instant; its local date (in
    ``timezone_name``) selects the prior-day candles. Empty selection fails
    closed rather than inventing extrema.
    """

    ordered = validate_closed_candle_sequence(candles)
    _validate_timestamp(prior_day, field_name="prior_day")
    if type(timezone_name) is not str or not timezone_name.strip():
        raise DemoTradingPrimitiveValidationError("timezone_name must be non-empty")
    from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

    try:
        zone = ZoneInfo(timezone_name)
    except (ZoneInfoNotFoundError, ValueError) as exc:
        raise DemoTradingPrimitiveValidationError(
            f"invalid IANA timezone: {timezone_name!r}"
        ) from exc
    target_date = prior_day.astimezone(zone).date()
    selected = tuple(
        item for item in ordered if item.closed_at.astimezone(zone).date() == target_date
    )
    if not selected:
        raise DemoTradingPrimitiveValidationError(
            "prior-day extrema require at least one closed candle on the prior day"
        )
    return session_extrema(selected)


class AmdPhase(StrEnum):
    """Deterministic AMD (Accumulation, Manipulation, Distribution) phase."""

    ACCUMULATION = "accumulation"
    MANIPULATION = "manipulation"
    DISTRIBUTION = "distribution"
    UNDEFINED = "undefined"


@dataclass(frozen=True, slots=True)
class AmdContext:
    """Deterministic closed-H4 AMD structural context."""

    range_high: Decimal
    range_low: Decimal
    phase: AmdPhase
    manipulation_side: SwingPivotKind | None
    distribution_direction: SwingPivotKind | None

    def __post_init__(self) -> None:
        _validate_price(self.range_high, field_name="AMD range high")
        _validate_price(self.range_low, field_name="AMD range low")
        if self.range_low > self.range_high:
            raise DemoTradingPrimitiveValidationError("AMD range low must not exceed high")
        if type(self.phase) is not AmdPhase:
            raise DemoTradingPrimitiveValidationError("AMD phase must be AmdPhase")
        if self.manipulation_side is not None and type(
            self.manipulation_side
        ) is not SwingPivotKind:
            raise DemoTradingPrimitiveValidationError(
                "AMD manipulation_side must be SwingPivotKind or None"
            )
        if self.distribution_direction is not None and type(
            self.distribution_direction
        ) is not SwingPivotKind:
            raise DemoTradingPrimitiveValidationError(
                "AMD distribution_direction must be SwingPivotKind or None"
            )

    def logical_values(self) -> tuple[object, ...]:
        return (
            format(self.range_high, "f"),
            format(self.range_low, "f"),
            self.phase.value,
            None if self.manipulation_side is None else self.manipulation_side.value,
            (
                None
                if self.distribution_direction is None
                else self.distribution_direction.value
            ),
        )


def detect_amd_context(
    candles: tuple[ClosedCandle, ...],
    *,
    range_length: int = 4,
) -> AmdContext:
    """Derive deterministic AMD structure from a closed higher-timeframe range.

    ``candles`` are closed H4 (or equivalent structural) candles. The deal range
    is the extrema of the most recent ``range_length`` candles EXCLUDING the
    latest (acting) candle. A manipulation occurs when the latest candle sweeps
    one side of the range and closes back inside; a distribution is recognized
    when the latest candle closes beyond the opposite side with an observable
    displacement. Otherwise the context remains accumulation.
    """

    ordered = validate_closed_candle_sequence(candles)
    if type(range_length) is not int or range_length < 1:
        raise DemoTradingPrimitiveValidationError("AMD range_length must be a positive int")
    if len(ordered) < range_length + 1:
        raise DemoTradingPrimitiveValidationError(
            "AMD context requires range_length closed candles plus one "
            "manipulation/distribution candle"
        )
    # The deal range is the extrema of the candles BEFORE the latest candle; the
    # latest candle is the manipulation/distribution candle that acts on it.
    range_candles = ordered[-range_length - 1 : -1]
    extrema = session_extrema(range_candles)
    latest = ordered[-1]

    manipulation_side: SwingPivotKind | None = None
    if latest.high > extrema.high and latest.close < extrema.high:
        manipulation_side = SwingPivotKind.HIGH
    elif latest.low < extrema.low and latest.close > extrema.low:
        manipulation_side = SwingPivotKind.LOW

    distribution_direction: SwingPivotKind | None = None
    phase = AmdPhase.ACCUMULATION
    if manipulation_side is SwingPivotKind.HIGH:
        # Upside manipulation (swept highs) resolves by distributing downward.
        if latest.close < extrema.low:
            distribution_direction = SwingPivotKind.LOW
            phase = AmdPhase.DISTRIBUTION
        else:
            phase = AmdPhase.MANIPULATION
    elif manipulation_side is SwingPivotKind.LOW:
        if latest.close > extrema.high:
            distribution_direction = SwingPivotKind.HIGH
            phase = AmdPhase.DISTRIBUTION
        else:
            phase = AmdPhase.MANIPULATION

    return AmdContext(
        range_high=extrema.high,
        range_low=extrema.low,
        phase=phase,
        manipulation_side=manipulation_side,
        distribution_direction=distribution_direction,
    )

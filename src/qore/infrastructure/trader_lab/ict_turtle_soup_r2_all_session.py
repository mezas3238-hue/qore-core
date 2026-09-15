"""Event-driven, all-session ICT Turtle Soup R2 research core."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal
from enum import StrEnum

BAR_DURATION = timedelta(minutes=5)
MIN_PROJECTED_R = Decimal("1.5")
IDENTITY = "ICT_TURTLE_SOUP_R2_ALL_SESSION_MULTI_ASSET"


class Side(StrEnum):
    LONG = "long"
    SHORT = "short"


class LiquiditySide(StrEnum):
    BUY_SIDE = "buy-side"
    SELL_SIDE = "sell-side"


class DetectionStatus(StrEnum):
    SIGNAL = "signal"
    DATA_INVALID = "data-invalid"
    NO_SWEEP = "no-sweep"
    NO_RECLAIM = "no-reclaim"
    NO_OPPOSING_SERIES = "no-opposing-series"
    NO_CISD = "no-cisd"
    NO_CAUSAL_ENTRY_BAR = "no-causal-entry-bar"
    NO_OPPOSING_TARGET = "no-opposing-target"
    INVALID_GEOMETRY = "invalid-geometry"
    INSUFFICIENT_PROJECTED_R = "insufficient-projected-r"


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
            raise ValueError("R2 requires exact five-minute bars")
        if self.high < max(self.open, self.close) or self.low > min(self.open, self.close):
            raise ValueError("OHLC body lies outside high/low")
        if self.high < self.low:
            raise ValueError("high must be >= low")


@dataclass(frozen=True, slots=True)
class QualifiedLiquidityPool:
    pool_id: str
    symbol: str
    family: str
    side: LiquiditySide
    level: Decimal
    known_at: datetime

    def __post_init__(self) -> None:
        if not self.pool_id or not self.symbol or not self.family:
            raise ValueError("liquidity pool identity fields must be non-empty")
        if self.level <= 0:
            raise ValueError("liquidity pool level must be positive")
        if self.known_at.tzinfo is None or self.known_at.utcoffset() is None:
            raise ValueError("known_at must be timezone-aware")


@dataclass(frozen=True, slots=True)
class ICTTurtleSoupR2Signal:
    identity: str
    symbol: str
    side: Side
    swept_pool_id: str
    target_pool_id: str
    sweep_at: datetime
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
    signal: ICTTurtleSoupR2Signal | None
    detail: str


def _opposing(bar: M5Bar, side: Side) -> bool:
    return bar.close < bar.open if side is Side.LONG else bar.close > bar.open


def _cisd_threshold(bars: tuple[M5Bar, ...], sweep_index: int, side: Side) -> Decimal | None:
    cursor = sweep_index if _opposing(bars[sweep_index], side) else sweep_index - 1
    if cursor < 0 or not _opposing(bars[cursor], side):
        return None
    while cursor > 0 and _opposing(bars[cursor - 1], side):
        cursor -= 1
    return bars[cursor].open


def _contiguous(bars: tuple[M5Bar, ...]) -> bool:
    return all(
        left.closed_at == right.opened_at
        for left, right in zip(bars, bars[1:], strict=False)
    )


def _trade_side(pool: QualifiedLiquidityPool) -> Side:
    return Side.LONG if pool.side is LiquiditySide.SELL_SIDE else Side.SHORT


def _sweeps(bar: M5Bar, side: Side, level: Decimal) -> bool:
    return bar.low < level if side is Side.LONG else bar.high > level


def _reclaims(bar: M5Bar, side: Side, level: Decimal) -> bool:
    return bar.close > level if side is Side.LONG else bar.close < level


def _confirms_cisd(bar: M5Bar, side: Side, threshold: Decimal) -> bool:
    return bar.close > threshold if side is Side.LONG else bar.close < threshold


def _eligible_target(
    *,
    symbol: str,
    side: Side,
    entry: Decimal,
    entry_at: datetime,
    pools: tuple[QualifiedLiquidityPool, ...],
) -> QualifiedLiquidityPool | None:
    if side is Side.LONG:
        candidates = [
            pool
            for pool in pools
            if pool.symbol == symbol
            and pool.side is LiquiditySide.BUY_SIDE
            and pool.known_at <= entry_at
            and pool.level > entry
        ]
        return min(candidates, key=lambda pool: pool.level, default=None)
    candidates = [
        pool
        for pool in pools
        if pool.symbol == symbol
        and pool.side is LiquiditySide.SELL_SIDE
        and pool.known_at <= entry_at
        and pool.level < entry
    ]
    return max(candidates, key=lambda pool: pool.level, default=None)


def detect_ict_turtle_soup_r2_event(
    *,
    symbol: str,
    bars: tuple[M5Bar, ...],
    tick_size: Decimal,
    swept_pool: QualifiedLiquidityPool,
    opposing_pools: tuple[QualifiedLiquidityPool, ...],
) -> Detection:
    """Detect one event without any clock-time inclusion/exclusion filter."""
    if tick_size <= 0 or swept_pool.symbol != symbol:
        return Detection(DetectionStatus.DATA_INVALID, None, "invalid symbol or tick size")
    if not bars:
        return Detection(DetectionStatus.DATA_INVALID, None, "empty M5 evidence")
    ordered = tuple(sorted(bars, key=lambda item: item.opened_at))
    if not _contiguous(ordered):
        return Detection(DetectionStatus.DATA_INVALID, None, "M5 evidence is discontinuous")
    if ordered[0].opened_at < swept_pool.known_at:
        return Detection(
            DetectionStatus.DATA_INVALID,
            None,
            "event evidence starts before swept pool became causal knowledge",
        )

    side = _trade_side(swept_pool)
    sweep_index = next(
        (
            index
            for index, bar in enumerate(ordered)
            if _sweeps(bar, side, swept_pool.level)
        ),
        None,
    )
    if sweep_index is None:
        return Detection(DetectionStatus.NO_SWEEP, None, "qualified pool was not swept")

    threshold = _cisd_threshold(ordered, sweep_index, side)
    if threshold is None:
        return Detection(
            DetectionStatus.NO_OPPOSING_SERIES,
            None,
            "sweep has no causal opposing-body series",
        )

    reclaim_index: int | None = None
    cisd_index: int | None = None
    for index in range(sweep_index, len(ordered)):
        bar = ordered[index]
        if reclaim_index is None and _reclaims(bar, side, swept_pool.level):
            reclaim_index = index
        if reclaim_index is not None and _confirms_cisd(bar, side, threshold):
            cisd_index = index
            break

    if reclaim_index is None:
        return Detection(DetectionStatus.NO_RECLAIM, None, "swept level was never reclaimed")
    if cisd_index is None:
        return Detection(DetectionStatus.NO_CISD, None, "reclaim never confirmed CISD")

    entry_index = cisd_index + 1
    if entry_index >= len(ordered):
        return Detection(
            DetectionStatus.NO_CAUSAL_ENTRY_BAR,
            None,
            "CISD completed without a subsequent causal M5 entry bar",
        )
    entry_bar = ordered[entry_index]
    entry = entry_bar.open
    adverse = ordered[sweep_index : cisd_index + 1]
    if side is Side.LONG:
        stop = min(bar.low for bar in adverse) - tick_size
    else:
        stop = max(bar.high for bar in adverse) + tick_size

    target_pool = _eligible_target(
        symbol=symbol,
        side=side,
        entry=entry,
        entry_at=entry_bar.opened_at,
        pools=opposing_pools,
    )
    if target_pool is None:
        return Detection(
            DetectionStatus.NO_OPPOSING_TARGET,
            None,
            "no causal opposing liquidity target was known before entry",
        )

    risk = entry - stop if side is Side.LONG else stop - entry
    reward = target_pool.level - entry if side is Side.LONG else entry - target_pool.level
    if risk <= 0 or reward <= 0:
        return Detection(DetectionStatus.INVALID_GEOMETRY, None, "non-positive risk/reward")
    projected_r = reward / risk
    if projected_r < MIN_PROJECTED_R:
        return Detection(
            DetectionStatus.INSUFFICIENT_PROJECTED_R,
            None,
            f"projected target is {projected_r}R < {MIN_PROJECTED_R}R",
        )

    return Detection(
        DetectionStatus.SIGNAL,
        ICTTurtleSoupR2Signal(
            identity=IDENTITY,
            symbol=symbol,
            side=side,
            swept_pool_id=swept_pool.pool_id,
            target_pool_id=target_pool.pool_id,
            sweep_at=ordered[sweep_index].opened_at,
            reclaim_at=ordered[reclaim_index].closed_at,
            cisd_at=ordered[cisd_index].closed_at,
            cisd_threshold=threshold,
            entry_at=entry_bar.opened_at,
            entry=entry,
            stop=stop,
            target=target_pool.level,
            projected_r=projected_r,
        ),
        "deterministic all-session R2 signal",
    )

"""Structural target binding for Capitalizer V47-S0.

The candidate family and source-frame anchors mirror the consumed CIBO Target
Destination V2 semantics, but candidates are reconstructed directly at the new
canonical decision timestamp. No target result/touch outcome after decision is
read.

Frozen by PR #623 comments 5889541472 and 5889764029.
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta
from decimal import Decimal
from zoneinfo import ZoneInfo

from qore.infrastructure.trader_lab import (
    capitalizer_native_source_fact_remediation_v46 as remediation,
)
from qore.infrastructure.trader_lab.capitalizer_cibo_m1_reader_v1 import (
    CapitalizerM1Bar,
)
from qore.infrastructure.trader_lab.capitalizer_source_observation_detectors_v2 import (
    CapitalizerSourceBar,
    CapitalizerSourceDirection,
)
from qore.infrastructure.trader_lab.capitalizer_source_trade_plan_v2 import (
    CapitalizerSourceTargetKind,
)

PARENT_IDENTITY = "QORE_CAPITALIZER_CANONICAL_SOURCE_CANDIDATE_ASSEMBLY_V47_S0"
SEMANTIC_AMENDMENT_COMMENT_ID = 5889764029
NEW_YORK = ZoneInfo("America/New_York")
M5 = timedelta(minutes=5)
H1 = timedelta(hours=1)
H4 = timedelta(hours=4)
D1 = timedelta(days=1)


@dataclass(frozen=True, slots=True)
class S0SourceFrame:
    timeframe: str
    opened_at: datetime
    closed_at: datetime
    source: CapitalizerSourceBar

    def __post_init__(self) -> None:
        if self.timeframe not in {"M5", "H1", "H4", "D1"}:
            raise ValueError("S0 unsupported source timeframe")
        _aware(self.opened_at)
        _aware(self.closed_at)
        if self.closed_at <= self.opened_at:
            raise ValueError("S0 source frame must move forward")


@dataclass(frozen=True, slots=True)
class S0SourceOppositeBoundary:
    target_price: Decimal
    known_at: datetime
    source_timeframe: str

    def __post_init__(self) -> None:
        if not self.target_price.is_finite() or self.target_price <= 0:
            raise ValueError("S0 source opposite boundary price invalid")
        _aware(self.known_at)
        if not self.source_timeframe:
            raise ValueError("S0 source opposite boundary requires timeframe")


@dataclass(frozen=True, slots=True)
class S0StructuralTargetBinding:
    candidates: tuple[remediation.CapitalizerStructuralTargetCandidate, ...]
    resolution: remediation.CapitalizerStructuralTargetResolution
    exact_source_frames_only: bool = True
    interpolation_used: bool = False
    outcome_used: bool = False

    def __post_init__(self) -> None:
        if (
            not self.exact_source_frames_only
            or self.interpolation_used
            or self.outcome_used
        ):
            raise ValueError("S0 structural target governance violated")


def _aware(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("S0 target timestamp must be timezone-aware")
    return value.astimezone(UTC)


def _contiguous_m1(rows: tuple[CapitalizerM1Bar, ...]) -> bool:
    return all(
        left.closed_at == right.opened_at
        for left, right in zip(rows[:-1], rows[1:], strict=True)
    )


def _m5_open(moment: datetime) -> datetime:
    value = _aware(moment)
    return value.replace(
        minute=(value.minute // 5) * 5,
        second=0,
        microsecond=0,
    )


def _source_day(moment: datetime) -> date:
    local = _aware(moment).astimezone(NEW_YORK)
    wall = local.timetz().replace(tzinfo=None)
    if wall >= time(17, 0):
        return local.date()
    return local.date() - timedelta(days=1)


def _source_day_open(day: date) -> datetime:
    return datetime.combine(day, time(17, 0), tzinfo=NEW_YORK).astimezone(UTC)


def _h1_open(moment: datetime) -> datetime:
    local = _aware(moment).astimezone(NEW_YORK).replace(
        minute=0,
        second=0,
        microsecond=0,
    )
    return local.astimezone(UTC)


def _h4_open(moment: datetime) -> datetime:
    local = _aware(moment).astimezone(NEW_YORK)
    day = _source_day(moment)
    base = datetime.combine(day, time(17, 0), tzinfo=NEW_YORK)
    delta = local - base
    slot = int(delta.total_seconds() // H4.total_seconds())
    return (base + slot * H4).astimezone(UTC)


def _aggregate_exact_m5(
    bars: tuple[CapitalizerM1Bar, ...],
) -> tuple[S0SourceFrame, ...]:
    grouped: dict[datetime, list[CapitalizerM1Bar]] = defaultdict(list)
    for bar in bars:
        grouped[_m5_open(bar.opened_at)].append(bar)

    result: list[S0SourceFrame] = []
    for opened, raw in sorted(grouped.items()):
        rows = tuple(sorted(raw, key=lambda item: item.opened_at))
        if len(rows) != 5 or not _contiguous_m1(rows):
            continue
        if rows[0].opened_at != opened or rows[-1].closed_at != opened + M5:
            continue
        result.append(
            S0SourceFrame(
                timeframe="M5",
                opened_at=opened,
                closed_at=opened + M5,
                source=CapitalizerSourceBar(
                    open=rows[0].open,
                    high=max(row.high for row in rows),
                    low=min(row.low for row in rows),
                    close=rows[-1].close,
                ),
            )
        )
    return tuple(result)


def _aggregate_exact(
    frames: tuple[S0SourceFrame, ...],
    *,
    timeframe: str,
    key_fn: Callable[[datetime], datetime],
    expected_count: int,
    duration: timedelta,
) -> tuple[S0SourceFrame, ...]:
    grouped: dict[datetime, list[S0SourceFrame]] = defaultdict(list)
    for frame in frames:
        grouped[key_fn(frame.opened_at)].append(frame)

    result: list[S0SourceFrame] = []
    for opened, raw in sorted(grouped.items()):
        rows = tuple(sorted(raw, key=lambda item: item.opened_at))
        expected = tuple(
            opened + index * M5
            for index in range(expected_count)
        )
        if tuple(row.opened_at for row in rows) != expected:
            continue
        if rows[-1].closed_at != opened + duration:
            continue
        result.append(
            S0SourceFrame(
                timeframe=timeframe,
                opened_at=opened,
                closed_at=opened + duration,
                source=CapitalizerSourceBar(
                    open=rows[0].source.open,
                    high=max(row.source.high for row in rows),
                    low=min(row.source.low for row in rows),
                    close=rows[-1].source.close,
                ),
            )
        )
    return tuple(result)


def _aggregate_daily(
    h4: tuple[S0SourceFrame, ...],
) -> tuple[S0SourceFrame, ...]:
    grouped: dict[date, list[S0SourceFrame]] = defaultdict(list)
    for frame in h4:
        grouped[_source_day(frame.opened_at)].append(frame)

    result: list[S0SourceFrame] = []
    for day, raw in sorted(grouped.items()):
        opened = _source_day_open(day)
        rows = tuple(sorted(raw, key=lambda item: item.opened_at))
        expected = tuple(opened + index * H4 for index in range(6))
        if tuple(row.opened_at for row in rows) != expected:
            continue
        if rows[-1].closed_at != opened + D1:
            continue
        result.append(
            S0SourceFrame(
                timeframe="D1",
                opened_at=opened,
                closed_at=opened + D1,
                source=CapitalizerSourceBar(
                    open=rows[0].source.open,
                    high=max(row.source.high for row in rows),
                    low=min(row.source.low for row in rows),
                    close=rows[-1].source.close,
                ),
            )
        )
    return tuple(result)


def build_exact_source_frames(
    bars: tuple[CapitalizerM1Bar, ...],
) -> dict[str, tuple[S0SourceFrame, ...]]:
    m5 = _aggregate_exact_m5(bars)
    h1 = _aggregate_exact(
        m5,
        timeframe="H1",
        key_fn=_h1_open,
        expected_count=12,
        duration=H1,
    )
    h4 = _aggregate_exact(
        m5,
        timeframe="H4",
        key_fn=_h4_open,
        expected_count=48,
        duration=H4,
    )
    daily = _aggregate_daily(h4)
    return {"H1": h1, "H4": h4, "D1": daily}


def _ahead(
    level: Decimal,
    entry_price: Decimal,
    direction: CapitalizerSourceDirection,
) -> bool:
    if direction is CapitalizerSourceDirection.BULLISH:
        return level > entry_price
    return level < entry_price


def _touched(
    bar: CapitalizerM1Bar,
    *,
    level: Decimal,
    direction: CapitalizerSourceDirection,
) -> bool:
    if direction is CapitalizerSourceDirection.BULLISH:
        return bar.high >= level
    return bar.low <= level


def _untouched_since(
    bars: tuple[CapitalizerM1Bar, ...],
    *,
    level: Decimal,
    known_at: datetime,
    decision_at: datetime,
    direction: CapitalizerSourceDirection,
) -> bool:
    return not any(
        _touched(bar, level=level, direction=direction)
        for bar in bars
        if _aware(known_at) <= bar.opened_at < _aware(decision_at)
    )


def _previous_completed_candidate(
    frames: tuple[S0SourceFrame, ...],
    *,
    timeframe: str,
    decision_at: datetime,
    entry_price: Decimal,
    direction: CapitalizerSourceDirection,
) -> remediation.CapitalizerStructuralTargetCandidate | None:
    if timeframe == "H1":
        current_open = _h1_open(decision_at)
    elif timeframe == "H4":
        current_open = _h4_open(decision_at)
    elif timeframe == "D1":
        current_open = _source_day_open(_source_day(decision_at))
    else:
        raise ValueError("S0 previous target timeframe unsupported")

    prior = tuple(frame for frame in frames if frame.closed_at <= current_open)
    if not prior:
        return None
    frame = prior[-1]
    level = (
        frame.source.high
        if direction is CapitalizerSourceDirection.BULLISH
        else frame.source.low
    )
    if not _ahead(level, entry_price, direction):
        return None
    kind = (
        CapitalizerSourceTargetKind.RECENT_DAILY_HIGH_LOW
        if timeframe == "D1"
        else CapitalizerSourceTargetKind.HIGHER_TIMEFRAME_STRUCTURAL_OBJECTIVE
    )
    return remediation.CapitalizerStructuralTargetCandidate(
        kind=kind,
        target_price=level,
        observed_at=frame.closed_at,
        untouched=True,
        higher_timeframe=True,
    )


def _latest_active_swing_candidate(
    frames: tuple[S0SourceFrame, ...],
    bars: tuple[CapitalizerM1Bar, ...],
    *,
    timeframe: str,
    decision_at: datetime,
    entry_price: Decimal,
    direction: CapitalizerSourceDirection,
) -> remediation.CapitalizerStructuralTargetCandidate | None:
    decision = _aware(decision_at)
    candidates: list[remediation.CapitalizerStructuralTargetCandidate] = []
    causal = tuple(frame for frame in frames if frame.closed_at <= decision)
    for index in range(1, len(causal) - 1):
        left, pivot, right = causal[index - 1], causal[index], causal[index + 1]
        if direction is CapitalizerSourceDirection.BULLISH:
            structural = (
                pivot.source.high > left.source.high
                and pivot.source.high > right.source.high
            )
            level = pivot.source.high
        else:
            structural = (
                pivot.source.low < left.source.low
                and pivot.source.low < right.source.low
            )
            level = pivot.source.low
        if not structural or not _ahead(level, entry_price, direction):
            continue
        known_at = right.closed_at
        untouched = _untouched_since(
            bars,
            level=level,
            known_at=known_at,
            decision_at=decision,
            direction=direction,
        )
        if not untouched:
            continue
        candidates.append(
            remediation.CapitalizerStructuralTargetCandidate(
                kind=(
                    CapitalizerSourceTargetKind.RECENT_DAILY_HIGH_LOW
                    if timeframe == "D1"
                    else CapitalizerSourceTargetKind.HIGHER_TIMEFRAME_STRUCTURAL_OBJECTIVE
                ),
                target_price=level,
                observed_at=known_at,
                untouched=True,
                higher_timeframe=True,
            )
        )
    return None if not candidates else candidates[-1]


def bind_structural_target(
    bars: tuple[CapitalizerM1Bar, ...],
    *,
    direction: CapitalizerSourceDirection,
    entry_price: Decimal,
    decision_at: datetime,
    source_opposite_boundary: S0SourceOppositeBoundary | None = None,
) -> S0StructuralTargetBinding:
    """Build the frozen bounded structural-target family at decision time."""

    decision = _aware(decision_at)
    frames = build_exact_source_frames(bars)
    candidates: list[remediation.CapitalizerStructuralTargetCandidate] = []

    for timeframe in ("H1", "H4", "D1"):
        prior = _previous_completed_candidate(
            frames[timeframe],
            timeframe=timeframe,
            decision_at=decision,
            entry_price=entry_price,
            direction=direction,
        )
        if prior is not None:
            untouched = _untouched_since(
                bars,
                level=prior.target_price,
                known_at=prior.observed_at,
                decision_at=decision,
                direction=direction,
            )
            if untouched:
                candidates.append(prior)

        swing = _latest_active_swing_candidate(
            frames[timeframe],
            bars,
            timeframe=timeframe,
            decision_at=decision,
            entry_price=entry_price,
            direction=direction,
        )
        if swing is not None:
            candidates.append(swing)

    if source_opposite_boundary is not None:
        if (
            _aware(source_opposite_boundary.known_at) <= decision
            and _ahead(
                source_opposite_boundary.target_price,
                entry_price,
                direction,
            )
            and _untouched_since(
                bars,
                level=source_opposite_boundary.target_price,
                known_at=source_opposite_boundary.known_at,
                decision_at=decision,
                direction=direction,
            )
        ):
            candidates.append(
                remediation.CapitalizerStructuralTargetCandidate(
                    kind=(
                        CapitalizerSourceTargetKind.HIGHER_TIMEFRAME_STRUCTURAL_OBJECTIVE
                    ),
                    target_price=source_opposite_boundary.target_price,
                    observed_at=source_opposite_boundary.known_at,
                    untouched=True,
                    higher_timeframe=True,
                )
            )

    deduped = {
        (item.kind, item.target_price, item.observed_at): item
        for item in candidates
    }
    ordered = tuple(
        sorted(
            deduped.values(),
            key=lambda item: (
                item.observed_at,
                item.kind.value,
                item.target_price,
            ),
        )
    )
    resolution = remediation.resolve_structural_target(
        direction=direction,
        entry_price=entry_price,
        decision_at=decision,
        candidates=ordered,
    )
    return S0StructuralTargetBinding(
        candidates=ordered,
        resolution=resolution,
    )

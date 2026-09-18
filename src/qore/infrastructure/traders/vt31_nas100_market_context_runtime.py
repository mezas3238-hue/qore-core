"""Causal higher-context reconstruction for VT31_NAS100.

All features are derived from NAS100 closed M1 bars already observable at the
decision timestamp plus the latest prior admitted market day. They are
descriptive situation inputs, not standalone entry rules.
"""
from __future__ import annotations

from collections import defaultdict
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from zoneinfo import ZoneInfo

from qore.infrastructure.market_data import OhlcSnapshot

_NY = ZoneInfo("America/New_York")


@dataclass(frozen=True, slots=True)
class Nas100CausalHigherContext:
    prior_day_state: str
    prior_day_body_fraction: Decimal | None
    h4_state: str
    h1_state: str
    premarket_state: str
    cash_open_state: str
    position_in_prior_day_range: str
    raid_depth_ref: Decimal | None
    recent_path_efficiency: Decimal | None
    recent_overlap_rate: Decimal | None


def _d(value: object) -> Decimal:
    return Decimal(str(value))


def _wall(value: datetime) -> tuple[int, int, int]:
    local = value.astimezone(_NY)
    return local.hour, local.minute, local.second


def _slice(
    bars: Sequence[OhlcSnapshot],
    start: tuple[int, int, int],
    end: tuple[int, int, int],
    decision_at: datetime | None = None,
) -> tuple[OhlcSnapshot, ...]:
    return tuple(
        bar
        for bar in bars
        if start <= _wall(bar.opened_at) < end
        and (decision_at is None or bar.closed_at <= decision_at)
    )


def _range(bars: Sequence[OhlcSnapshot]) -> Decimal | None:
    if not bars:
        return None
    return max(_d(bar.high) for bar in bars) - min(_d(bar.low) for bar in bars)


def _directional_state(bars: Sequence[OhlcSnapshot]) -> str:
    if not bars:
        return "unavailable"
    span = _range(bars)
    if span is None or span <= 0:
        return "flat"
    opened = _d(bars[0].open)
    closed = _d(bars[-1].close)
    body_fraction = abs(closed - opened) / span
    if body_fraction < Decimal("0.20"):
        return "rotation"
    return "bullish" if closed > opened else "bearish"


def _completed_hour_closes(
    bars: Sequence[OhlcSnapshot],
    decision_at: datetime,
    hours_per_bucket: int,
) -> list[Decimal]:
    groups: dict[tuple[object, int], list[OhlcSnapshot]] = defaultdict(list)
    for bar in bars:
        if bar.closed_at > decision_at:
            continue
        local = bar.opened_at.astimezone(_NY)
        bucket = (local.date(), local.hour // hours_per_bucket)
        groups[bucket].append(bar)

    closes: list[tuple[datetime, Decimal]] = []
    required = 60 * hours_per_bucket
    for group in groups.values():
        ordered = sorted(group, key=lambda bar: bar.opened_at)
        if len(ordered) != required:
            continue
        if any(
            right.opened_at != left.closed_at
            for left, right in zip(ordered, ordered[1:], strict=False)
        ):
            continue
        if ordered[-1].closed_at > decision_at:
            continue
        closes.append((ordered[-1].closed_at, _d(ordered[-1].close)))
    closes.sort(key=lambda item: item[0])
    return [value for _, value in closes]


def _trend_state(closes: list[Decimal]) -> str:
    if len(closes) < 2:
        return "unavailable"
    last = closes[-3:]
    rises = sum(right > left for left, right in zip(last, last[1:], strict=False))
    falls = sum(right < left for left, right in zip(last, last[1:], strict=False))
    if rises and not falls:
        return "bullish"
    if falls and not rises:
        return "bearish"
    if all(right == left for left, right in zip(last, last[1:], strict=False)):
        return "flat"
    return "mixed"


def _prior_day(
    prior_bars: Sequence[OhlcSnapshot],
) -> tuple[str, Decimal | None, Decimal | None, Decimal | None]:
    path = _slice(prior_bars, (0, 0, 0), (16, 0, 0))
    if not path:
        return "unavailable", None, None, None
    high = max(_d(bar.high) for bar in path)
    low = min(_d(bar.low) for bar in path)
    span = high - low
    opened = _d(path[0].open)
    closed = _d(path[-1].close)
    body_fraction = None if span <= 0 else abs(closed - opened) / span
    if body_fraction is None:
        state = "flat"
    elif body_fraction < Decimal("0.20"):
        state = "rotation"
    else:
        state = "bullish" if closed > opened else "bearish"
    return state, body_fraction, high, low


def _position_in_prior_range(
    current_price: Decimal,
    prior_high: Decimal | None,
    prior_low: Decimal | None,
) -> str:
    if prior_high is None or prior_low is None or prior_high <= prior_low:
        return "unavailable"
    if current_price > prior_high:
        return "above"
    if current_price < prior_low:
        return "below"
    percentile = (current_price - prior_low) / (prior_high - prior_low)
    if percentile >= Decimal("0.67"):
        return "upper-third"
    if percentile <= Decimal("0.33"):
        return "lower-third"
    return "middle-third"


def _recent_efficiency(
    bars: Sequence[OhlcSnapshot],
    decision_at: datetime,
) -> Decimal | None:
    eligible = [bar for bar in bars if bar.closed_at <= decision_at]
    recent = eligible[-15:]
    if len(recent) < 5:
        return None
    span = max(_d(bar.high) for bar in recent) - min(_d(bar.low) for bar in recent)
    if span <= 0:
        return Decimal(0)
    return abs(_d(recent[-1].close) - _d(recent[0].open)) / span


def _recent_overlap(
    bars: Sequence[OhlcSnapshot],
    decision_at: datetime,
) -> Decimal | None:
    eligible = [bar for bar in bars if bar.closed_at <= decision_at]
    recent = eligible[-15:]
    if len(recent) < 2:
        return None
    overlaps = 0
    pairs = 0
    for left, right in zip(recent, recent[1:], strict=False):
        pairs += 1
        if min(_d(left.high), _d(right.high)) >= max(_d(left.low), _d(right.low)):
            overlaps += 1
    return Decimal(overlaps) / Decimal(pairs)


def _raid_depth_ref(
    bars: Sequence[OhlcSnapshot],
    *,
    decision_at: datetime,
    side: str,
    reference_high: Decimal,
    reference_low: Decimal,
) -> Decimal | None:
    width = reference_high - reference_low
    if width <= 0:
        return None
    path = _slice(
        bars,
        (10, 0, 0),
        (11, 0, 0),
        decision_at,
    )
    if not path:
        return None
    if side == "short":
        depth = max(_d(bar.high) for bar in path) - reference_high
    elif side == "long":
        depth = reference_low - min(_d(bar.low) for bar in path)
    else:
        raise ValueError(f"unsupported side: {side}")
    return max(Decimal(0), depth) / width


def build_higher_context(
    *,
    day_bars: Sequence[OhlcSnapshot],
    prior_admitted_day_bars: Sequence[OhlcSnapshot],
    decision_at: datetime,
    side: str,
    reference_high: Decimal,
    reference_low: Decimal,
) -> Nas100CausalHigherContext:
    causal_today = tuple(bar for bar in day_bars if bar.closed_at <= decision_at)
    prior_state, prior_body, prior_high, prior_low = _prior_day(
        prior_admitted_day_bars
    )

    h1 = _trend_state(_completed_hour_closes(causal_today, decision_at, 1))
    h4 = _trend_state(_completed_hour_closes(causal_today, decision_at, 4))
    premarket = _directional_state(
        _slice(causal_today, (8, 0, 0), (9, 0, 0), decision_at)
    )
    cash_open = _directional_state(
        _slice(causal_today, (9, 30, 0), (10, 0, 0), decision_at)
    )
    current_price = (
        _d(causal_today[-1].close)
        if causal_today
        else (reference_high + reference_low) / Decimal(2)
    )

    return Nas100CausalHigherContext(
        prior_day_state=prior_state,
        prior_day_body_fraction=prior_body,
        h4_state=h4,
        h1_state=h1,
        premarket_state=premarket,
        cash_open_state=cash_open,
        position_in_prior_day_range=_position_in_prior_range(
            current_price,
            prior_high,
            prior_low,
        ),
        raid_depth_ref=_raid_depth_ref(
            causal_today,
            decision_at=decision_at,
            side=side,
            reference_high=reference_high,
            reference_low=reference_low,
        ),
        recent_path_efficiency=_recent_efficiency(causal_today, decision_at),
        recent_overlap_rate=_recent_overlap(causal_today, decision_at),
    )

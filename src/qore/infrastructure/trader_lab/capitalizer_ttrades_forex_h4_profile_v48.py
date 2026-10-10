"""TTrades source-bound Forex H4 profiles for Capitalizer V48.

TTrades' 4-Hour Power of 3 source distinguishes the higher-timeframe anchors:
- futures: 02:00 / 06:00 / 10:00;
- Forex: 01:00 / 05:00 / 09:00.

The TTrades timing guide states its chart/session times are New York time. V48 therefore
uses the four-hour Forex cycle 01/05/09/13/17/21 in America/New_York and constructs those
methodology candles from retained provider-native M1. No price is interpolated and the
broker's own H4 boundary is not assumed equivalent.

This is a structural data primitive. It grants no entry, target, outcome, capital or live
authority.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta
from decimal import Decimal
from zoneinfo import ZoneInfo

from qore.infrastructure.trader_lab.capitalizer_cibo_m1_reader_v1 import (
    CapitalizerM1Bar,
)

IDENTITY = "QORE_CAPITALIZER_V48_TTRADES_FOREX_H4_PROFILE"
NEW_YORK = ZoneInfo("America/New_York")
FOREX_H4_ANCHOR_HOURS_NY = (1, 5, 9, 13, 17, 21)
MINIMUM_COMPLETENESS = Decimal("0.75")


@dataclass(frozen=True, slots=True)
class V48ForexH4Profile:
    identity: str
    symbol: str
    profile_opened_at: datetime
    profile_closed_at: datetime
    ny_anchor_hour: int
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    retained_m1: int
    expected_wall_profile_minutes: int
    completeness: Decimal
    provider_native_m1: bool = True
    synthetic_price_used: bool = False
    interpolated_price_used: bool = False
    source_clock_bound: bool = True
    outcome_used: bool = False
    capital_authority: bool = False

    def __post_init__(self) -> None:
        if self.identity != IDENTITY:
            raise ValueError("Forex H4 profile identity is frozen")
        if self.ny_anchor_hour not in FOREX_H4_ANCHOR_HOURS_NY:
            raise ValueError("invalid TTrades Forex H4 anchor")
        if self.profile_closed_at <= self.profile_opened_at:
            raise ValueError("H4 profile must have positive duration")
        if self.retained_m1 <= 0 or self.expected_wall_profile_minutes <= 0:
            raise ValueError("H4 profile requires retained provider data")
        if self.completeness < MINIMUM_COMPLETENESS:
            raise ValueError("incomplete H4 profile cannot be stored")
        if not self.provider_native_m1:
            raise ValueError("H4 profile requires provider-native M1")
        if self.synthetic_price_used or self.interpolated_price_used:
            raise ValueError("H4 profile cannot synthesize/interpolate price")
        if not self.source_clock_bound:
            raise ValueError("H4 profile must use source-bound Forex clock")
        if self.outcome_used or self.capital_authority:
            raise ValueError("H4 profile is pre-economic and has no capital authority")


def _anchor_for_local(moment: datetime) -> tuple[date, int]:
    local = moment.astimezone(NEW_YORK)
    if local.hour < 1:
        return local.date() - timedelta(days=1), 21
    eligible = tuple(hour for hour in FOREX_H4_ANCHOR_HOURS_NY if hour <= local.hour)
    return local.date(), eligible[-1]


def forex_h4_profile_bounds(moment: datetime) -> tuple[datetime, datetime]:
    """Return source-bound Forex H4 UTC bounds containing the supplied moment."""

    if moment.tzinfo is None or moment.utcoffset() is None:
        raise ValueError("H4 profile moment must be timezone-aware")

    anchor_date, anchor_hour = _anchor_for_local(moment)
    local_start = datetime.combine(
        anchor_date,
        time(anchor_hour),
        tzinfo=NEW_YORK,
    )
    local_end = local_start + timedelta(hours=4)
    return local_start.astimezone(UTC), local_end.astimezone(UTC)


def build_forex_h4_profiles(
    bars: tuple[CapitalizerM1Bar, ...],
) -> tuple[V48ForexH4Profile, ...]:
    """Aggregate provider-native M1 into TTrades Forex H4 wall-clock profiles."""

    if not bars:
        return ()
    ordered = tuple(sorted(bars, key=lambda item: item.opened_at))
    if ordered != bars:
        raise ValueError("Forex H4 input M1 must be chronological")
    symbol = bars[0].symbol
    if any(bar.symbol != symbol for bar in bars):
        raise ValueError("Forex H4 profile input must contain one symbol")

    grouped: dict[tuple[datetime, datetime], list[CapitalizerM1Bar]] = defaultdict(list)
    for bar in bars:
        start, end = forex_h4_profile_bounds(bar.opened_at)
        if start <= bar.opened_at < end:
            grouped[(start, end)].append(bar)

    result: list[V48ForexH4Profile] = []
    for (start, end), chunk in sorted(grouped.items()):
        ordered_chunk = sorted(chunk, key=lambda item: item.opened_at)
        expected = int((end - start).total_seconds() // 60)
        if expected <= 0:
            continue
        completeness = Decimal(len(ordered_chunk)) / Decimal(expected)
        if completeness < MINIMUM_COMPLETENESS:
            continue
        local_start = start.astimezone(NEW_YORK)
        result.append(
            V48ForexH4Profile(
                identity=IDENTITY,
                symbol=symbol,
                profile_opened_at=start,
                profile_closed_at=end,
                ny_anchor_hour=local_start.hour,
                open=ordered_chunk[0].open,
                high=max(item.high for item in ordered_chunk),
                low=min(item.low for item in ordered_chunk),
                close=ordered_chunk[-1].close,
                retained_m1=len(ordered_chunk),
                expected_wall_profile_minutes=expected,
                completeness=completeness,
            )
        )
    return tuple(result)

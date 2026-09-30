"""TTrades source-bound Forex Daily profiles for Capitalizer V48.

The official TTrades H4 Power-of-3 PDF publishes a Futures/Forex timing table. It maps the
Futures 18:00 Daily open to 17:00 for Forex and shifts each H4 anchor by one hour as well.

V48 therefore constructs the Forex Daily methodology candle from retained provider-native M1
using the 17:00 America/New_York boundary. No broker-native Daily boundary equivalence is
assumed and no price is interpolated.

This module is structural and pre-economic. It grants no trade, target, capital or live authority.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import UTC, datetime, time, timedelta
from decimal import Decimal
from zoneinfo import ZoneInfo

from qore.infrastructure.trader_lab.capitalizer_cibo_m1_reader_v1 import (
    CapitalizerM1Bar,
)

IDENTITY = "QORE_CAPITALIZER_V48_TTRADES_FOREX_DAILY_PROFILE"
NEW_YORK = ZoneInfo("America/New_York")
FOREX_DAILY_OPEN_HOUR_NY = 17
MINIMUM_COMPLETENESS = Decimal("0.75")


@dataclass(frozen=True, slots=True)
class V48ForexDailyProfile:
    identity: str
    symbol: str
    profile_opened_at: datetime
    profile_closed_at: datetime
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    retained_m1: int
    expected_profile_minutes: int
    completeness: Decimal
    provider_native_m1: bool = True
    synthetic_price_used: bool = False
    interpolated_price_used: bool = False
    source_clock_bound: bool = True
    outcome_used: bool = False
    capital_authority: bool = False

    def __post_init__(self) -> None:
        if self.identity != IDENTITY:
            raise ValueError("Forex Daily profile identity is frozen")
        if self.profile_closed_at <= self.profile_opened_at:
            raise ValueError("Daily profile must have positive duration")
        if self.retained_m1 <= 0 or self.expected_profile_minutes <= 0:
            raise ValueError("Daily profile requires provider data")
        if self.completeness < MINIMUM_COMPLETENESS:
            raise ValueError("incomplete Daily profile cannot be stored")
        if not self.provider_native_m1:
            raise ValueError("Daily profile requires provider-native M1")
        if self.synthetic_price_used or self.interpolated_price_used:
            raise ValueError("Daily profile cannot synthesize/interpolate price")
        if not self.source_clock_bound:
            raise ValueError("Daily profile must use the source-bound Forex clock")
        if self.outcome_used or self.capital_authority:
            raise ValueError("Daily profile is pre-economic with no capital authority")


def forex_daily_profile_bounds(moment: datetime) -> tuple[datetime, datetime]:
    """Return TTrades Forex Daily UTC bounds containing the supplied moment."""

    if moment.tzinfo is None or moment.utcoffset() is None:
        raise ValueError("Daily profile moment must be timezone-aware")
    local = moment.astimezone(NEW_YORK)
    anchor_date = local.date()
    if local.hour < FOREX_DAILY_OPEN_HOUR_NY:
        anchor_date -= timedelta(days=1)
    local_start = datetime.combine(
        anchor_date,
        time(FOREX_DAILY_OPEN_HOUR_NY),
        tzinfo=NEW_YORK,
    )
    local_end = local_start + timedelta(days=1)
    return local_start.astimezone(UTC), local_end.astimezone(UTC)


def build_forex_daily_profiles(
    bars: tuple[CapitalizerM1Bar, ...],
) -> tuple[V48ForexDailyProfile, ...]:
    """Aggregate provider-native M1 into source-bound Forex Daily profiles."""

    if not bars:
        return ()
    ordered = tuple(sorted(bars, key=lambda item: item.opened_at))
    if ordered != bars:
        raise ValueError("Forex Daily input M1 must be chronological")
    symbol = bars[0].symbol
    if any(bar.symbol != symbol for bar in bars):
        raise ValueError("Forex Daily input must contain one symbol")

    grouped: dict[tuple[datetime, datetime], list[CapitalizerM1Bar]] = defaultdict(list)
    for bar in bars:
        start, end = forex_daily_profile_bounds(bar.opened_at)
        if start <= bar.opened_at < end:
            grouped[(start, end)].append(bar)

    result: list[V48ForexDailyProfile] = []
    for (start, end), chunk in sorted(grouped.items()):
        ordered_chunk = sorted(chunk, key=lambda item: item.opened_at)
        expected = int((end - start).total_seconds() // 60)
        if expected <= 0:
            continue
        completeness = Decimal(len(ordered_chunk)) / Decimal(expected)
        if completeness < MINIMUM_COMPLETENESS:
            continue
        result.append(
            V48ForexDailyProfile(
                identity=IDENTITY,
                symbol=symbol,
                profile_opened_at=start,
                profile_closed_at=end,
                open=ordered_chunk[0].open,
                high=max(item.high for item in ordered_chunk),
                low=min(item.low for item in ordered_chunk),
                close=ordered_chunk[-1].close,
                retained_m1=len(ordered_chunk),
                expected_profile_minutes=expected,
                completeness=completeness,
            )
        )
    return tuple(result)

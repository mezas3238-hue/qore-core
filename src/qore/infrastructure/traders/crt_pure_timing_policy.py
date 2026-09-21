"""Time-family policy for the VT08 CRT PURE research implementation.

RomeoTPT publishes the compact market-family notation:
- Forex: 159159
- Crypto: 12481248

The exact timezone is not encoded in that primary post.  This module therefore keeps the
source notation immutable and isolates the NY/DST-aware clock interpretation as an explicit
engineering policy that must survive robustness testing before certification.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import StrEnum
import zoneinfo

from qore.infrastructure.traders.crt_pure_identity import CrtPureMarket


NY = zoneinfo.ZoneInfo("America/New_York")


class CrtPureTimingAuthority(StrEnum):
    SOURCE = "SOURCE"
    ENGINEERING_POLICY = "ENGINEERING_POLICY"


@dataclass(frozen=True, slots=True)
class CrtPureTimingFamily:
    markets: tuple[CrtPureMarket, ...]
    source_notation: str
    h4_triplets_local_hours: tuple[tuple[int, int, int], ...]
    timezone_name: str = "America/New_York"
    source_authority: CrtPureTimingAuthority = CrtPureTimingAuthority.SOURCE
    timezone_authority: CrtPureTimingAuthority = CrtPureTimingAuthority.ENGINEERING_POLICY

    def __post_init__(self) -> None:
        for triplet in self.h4_triplets_local_hours:
            if len(triplet) != 3 or any(hour < 0 or hour > 23 for hour in triplet):
                raise ValueError("CRT timing triplet hours must be valid local clock hours")


FX_TIMING = CrtPureTimingFamily(
    markets=(CrtPureMarket.AUDUSD, CrtPureMarket.USDJPY),
    source_notation="159159",
    h4_triplets_local_hours=((1, 5, 9), (13, 17, 21)),
)

CRYPTO_TIMING = CrtPureTimingFamily(
    markets=(CrtPureMarket.BTCUSD,),
    source_notation="12481248",
    h4_triplets_local_hours=((0, 4, 8), (12, 16, 20)),
)


def timing_family(market: CrtPureMarket) -> CrtPureTimingFamily:
    if market in FX_TIMING.markets:
        return FX_TIMING
    if market in CRYPTO_TIMING.markets:
        return CRYPTO_TIMING
    raise ValueError(f"unsupported CRT PURE market: {market.value}")


@dataclass(frozen=True, slots=True)
class CrtPureH4TripletWindow:
    market: CrtPureMarket
    candle_1_open: datetime
    candle_2_open: datetime
    candle_3_open: datetime
    window_close: datetime
    timezone_policy: str = "America/New_York"

    def __post_init__(self) -> None:
        values = (
            self.candle_1_open,
            self.candle_2_open,
            self.candle_3_open,
            self.window_close,
        )
        if any(value.tzinfo is None for value in values):
            raise ValueError("CRT timing windows must be timezone-aware")
        if not (
            self.candle_1_open
            < self.candle_2_open
            < self.candle_3_open
            < self.window_close
        ):
            raise ValueError("CRT timing window must be strictly chronological")


def h4_triplet_windows_for_local_date(
    market: CrtPureMarket,
    local_date: datetime,
) -> tuple[CrtPureH4TripletWindow, ...]:
    """Return source-family H4 triplets interpreted under the explicit NY clock policy."""

    family = timing_family(market)
    day = local_date.astimezone(NY).date()
    windows: list[CrtPureH4TripletWindow] = []

    for h1, h2, h3 in family.h4_triplets_local_hours:
        c1 = datetime(day.year, day.month, day.day, h1, tzinfo=NY)
        c2 = datetime(day.year, day.month, day.day, h2, tzinfo=NY)
        c3 = datetime(day.year, day.month, day.day, h3, tzinfo=NY)
        close = c3 + timedelta(hours=4)
        windows.append(
            CrtPureH4TripletWindow(
                market=market,
                candle_1_open=c1,
                candle_2_open=c2,
                candle_3_open=c3,
                window_close=close,
            )
        )
    return tuple(windows)


def utc_triplet_windows_for_local_date(
    market: CrtPureMarket,
    local_date: datetime,
) -> tuple[CrtPureH4TripletWindow, ...]:
    return tuple(
        CrtPureH4TripletWindow(
            market=window.market,
            candle_1_open=window.candle_1_open.astimezone(zoneinfo.ZoneInfo("UTC")),
            candle_2_open=window.candle_2_open.astimezone(zoneinfo.ZoneInfo("UTC")),
            candle_3_open=window.candle_3_open.astimezone(zoneinfo.ZoneInfo("UTC")),
            window_close=window.window_close.astimezone(zoneinfo.ZoneInfo("UTC")),
        )
        for window in h4_triplet_windows_for_local_date(market, local_date)
    )

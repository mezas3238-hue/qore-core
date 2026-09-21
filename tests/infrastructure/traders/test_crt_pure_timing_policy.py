from datetime import UTC, datetime

from qore.infrastructure.traders.crt_pure_identity import CrtPureMarket
from qore.infrastructure.traders.crt_pure_timing_policy import (
    CRYPTO_TIMING,
    FX_TIMING,
    CrtPureTimingAuthority,
    h4_triplet_windows_for_local_date,
    timing_family,
    utc_triplet_windows_for_local_date,
)


def test_source_notation_is_separate_from_timezone_policy() -> None:
    assert FX_TIMING.source_notation == "159159"
    assert CRYPTO_TIMING.source_notation == "12481248"
    assert FX_TIMING.source_authority is CrtPureTimingAuthority.SOURCE
    assert FX_TIMING.timezone_authority is CrtPureTimingAuthority.ENGINEERING_POLICY
    assert FX_TIMING.timezone_name == "America/New_York"


def test_exact_market_timing_families() -> None:
    assert timing_family(CrtPureMarket.AUDUSD) is FX_TIMING
    assert timing_family(CrtPureMarket.USDJPY) is FX_TIMING
    assert timing_family(CrtPureMarket.BTCUSD) is CRYPTO_TIMING
    assert FX_TIMING.h4_triplets_local_hours == ((1, 5, 9), (13, 17, 21))
    assert CRYPTO_TIMING.h4_triplets_local_hours == ((0, 4, 8), (12, 16, 20))


def test_fx_windows_are_dst_aware() -> None:
    winter = utc_triplet_windows_for_local_date(
        CrtPureMarket.AUDUSD,
        datetime(2026, 1, 15, 12, tzinfo=UTC),
    )
    summer = utc_triplet_windows_for_local_date(
        CrtPureMarket.AUDUSD,
        datetime(2026, 7, 15, 12, tzinfo=UTC),
    )
    assert winter[0].candle_1_open.hour == 6
    assert summer[0].candle_1_open.hour == 5
    assert winter[0].candle_3_open.hour == 14
    assert summer[0].candle_3_open.hour == 13


def test_crypto_daily_triplets_are_non_overlapping() -> None:
    windows = h4_triplet_windows_for_local_date(
        CrtPureMarket.BTCUSD,
        datetime(2026, 7, 15, 12, tzinfo=UTC),
    )
    assert windows[0].window_close.hour == 12
    assert windows[1].candle_1_open.hour == 12
    assert windows[1].window_close.hour == 0
    assert windows[1].window_close.date().day == 16

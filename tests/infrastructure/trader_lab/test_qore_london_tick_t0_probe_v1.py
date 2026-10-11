"""Evidence T0 tests are offline; network access only in workflow proof."""
from __future__ import annotations

import lzma
import struct
from datetime import UTC, datetime

import pytest

from qore.infrastructure.trader_lab.qore_london_tick_t0_probe_v1 import (
    analyse_case,
    bi5_path,
    decode_bi5,
)


def record(ms: int, ask: int, bid: int) -> bytes:
    return struct.pack(">IIIff", ms, ask, bid, 1.0, 1.0)


def tick_bytes(*rows: tuple[int, int, int]) -> bytes:
    return lzma.compress(b"".join(record(*x) for x in rows))


HOUR = datetime(2025, 11, 12, 9, tzinfo=UTC)


def test_month_zero_based_utc_and_no_symbol_guess() -> None:
    assert bi5_path("EURUSD", HOUR) == "EURUSD/2025/10/12/09h_ticks.bi5"
    with pytest.raises(ValueError, match="only EURUSD"):
        bi5_path("NAS100", HOUR)


def test_decode_retains_spread_and_provider_millisecond_order() -> None:
    q = decode_bi5(
        tick_bytes((1500, 110050, 110030), (1700, 110060, 110040)),
        HOUR,
    )
    assert len(q) == 2
    assert q[0].bid == pytest.approx(1.1003)
    assert q[1].ask == pytest.approx(1.1006)
    assert (q[0].observed_at - HOUR).total_seconds() == pytest.approx(1.5)


def test_fail_closed_crossed_book_or_nonmonotonic() -> None:
    with pytest.raises(ValueError, match="crossed"):
        decode_bi5(tick_bytes((50, 110030, 110050)), HOUR)
    with pytest.raises(ValueError, match="chronology"):
        decode_bi5(tick_bytes((700, 110050, 110030), (600, 110050, 110030)), HOUR)


def test_fail_closed_unexpected_tick_hour() -> None:
    with pytest.raises(ValueError, match="chronology"):
        decode_bi5(tick_bytes((3_600_000, 110050, 110030)), HOUR)


def test_cross_provider_quote_touch_is_not_broker_fill() -> None:
    event = {
        "symbol": "EURUSD", "london_day": "2025-11-12",
        "pattern": "L1_SWEEP_RECLAIM", "direction": "LONG",
        "entry_at": "2025-11-12T09:00:00+00:00",
        "exit_at": "2025-11-12T09:01:00+00:00",
        "entry": "1.10000", "stop": "1.09990", "target": "1.10010",
    }
    quotes = decode_bi5(
        tick_bytes((200, 110005, 110003),
                   (300, 109995, 109985),
                   (400, 110030, 110010)), HOUR,
    )
    out = analyse_case(
        event, {"status": "QUOTE_SOURCE_AVAILABLE",
                "quotes": quotes, "url": "https://datafeed.dukascopy.com/datafeed/example"},
    )
    assert out["tick_first_touch_status"] == "EXTERNAL_QUOTE_STOP_OBSERVED_FIRST"
    assert out["adjudicated_broker_execution"] is False
    assert out["true_fill_or_slippage_known"] is False


def test_absent_quotes_never_invent_resolution() -> None:
    event = {"symbol": "EURUSD", "london_day": "2025-11-12",
             "pattern": "L1_SWEEP_RECLAIM", "entry_at": HOUR.isoformat(),
             "exit_at": HOUR.isoformat()}
    r = analyse_case(event, {"status": "QUOTE_SOURCE_NOT_RETRIEVED", "errors": ["404"]})
    assert r["tick_first_touch_status"] == "UNRESOLVED_NO_TICK_DATA"

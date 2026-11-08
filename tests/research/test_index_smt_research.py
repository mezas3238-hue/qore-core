"""No-lookahead controls for the standalone US-index SMT research hypothesis."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest

from qore.infrastructure.trader_lab.index_smt_research import (
    SYMBOLS,
    CRT,
    MSS,
    Candle,
    detect_smt,
    qualify_research_opportunities,
)

UTC = timezone.utc
CLOSE_TIME = datetime(2026, 11, 5, 15, 0, tzinfo=UTC)


def d(value: str) -> Decimal:
    return Decimal(value)


def candles(
    *,
    sweep: str = "SPX500",
    side: str = "BEARISH",
    same_side_break: bool = False,
    reclaim: bool = True,
) -> dict:
    bars = {}
    for symbol in SYMBOLS:
        base = {"SPX500": d("100"), "NDX100": d("200"), "US30": d("300")}[symbol]
        seq = []
        for index in range(9):
            timestamp = CLOSE_TIME - timedelta(minutes=15 * (8 - index))
            low, high, closing = base - 2, base + 2, base
            if index == 8:
                if symbol == sweep or (same_side_break and symbol == "NDX100"):
                    if side == "BEARISH":
                        high, closing = base + 4, base if reclaim else base + 3
                    else:
                        low, closing = base - 4, base if reclaim else base - 3
                else:
                    high, low = base + 1, base - 1
            seq.append(Candle(
                symbol=symbol,
                feed_id="ICMarkets:ctrader:DEMO:server-A",
                closed_at=timestamp,
                open=base,
                high=high,
                low=low,
                close=closing,
            ))
        bars[symbol] = seq
    return bars


def confirmed(symbol: str = "SPX500", side: str = "BEARISH") -> MSS:
    return MSS(
        symbol=symbol,
        direction=side,
        confirmed_at=CLOSE_TIME + timedelta(minutes=5),
        protected_swing=d("101" if side == "BEARISH" else "99"),
        confirming_close=d("99" if side == "BEARISH" else "101"),
    )


def test_bearish_candidate_detected_at_close_not_before() -> None:
    results = detect_smt(candles())
    assert {(x.pair, x.direction, x.sweeping_symbol) for x in results} == {
        (("SPX500", "NDX100"), "BEARISH", "SPX500"),
        (("SPX500", "US30"), "BEARISH", "SPX500"),
    }
    assert all(x.observed_at == CLOSE_TIME for x in results)


def test_bullish_candidate_and_reclamation() -> None:
    results = detect_smt(candles(sweep="NDX100", side="BULLISH"))
    assert len(results) == 2
    assert all(x.direction == "BULLISH" for x in results)
    assert all(x.sweeping_symbol == "NDX100" for x in results)


def test_no_smt_when_no_reentry_or_both_break() -> None:
    assert not detect_smt(candles(reclaim=False))
    data = candles(same_side_break=True)
    assert not any(x.pair == ("SPX500", "NDX100") for x in detect_smt(data))


def test_fail_closed_on_misalignment_or_cross_feed() -> None:
    data = candles()
    last = data["NDX100"][-1]
    data["NDX100"][-1] = Candle(
        last.symbol, last.feed_id, last.closed_at + timedelta(minutes=15),
        last.open, last.high, last.low, last.close,
    )
    with pytest.raises(ValueError, match="synchronized"):
        detect_smt(data)

    data = candles()
    last = data["US30"][-1]
    data["US30"][-1] = Candle(
        last.symbol, "DIFFERENT_FEED", last.closed_at,
        last.open, last.high, last.low, last.close,
    )
    with pytest.raises(ValueError, match="feed mismatch"):
        detect_smt(data)


def test_rejects_missing_bars_and_future_lookahead() -> None:
    data = candles()
    data["SPX500"][-2] = Candle(
        "SPX500", data["SPX500"][-2].feed_id,
        data["SPX500"][-2].closed_at - timedelta(minutes=15),
        d("100"), d("102"), d("98"), d("100"),
    )
    with pytest.raises(ValueError, match="missing M15"):
        detect_smt(data)


def test_crt_confirmation_route_and_pair_deduplication() -> None:
    observed = CLOSE_TIME + timedelta(minutes=5)
    opportunities = qualify_research_opportunities(
        candidates=detect_smt(candles()),
        mss_by_symbol={"SPX500": confirmed()},
        crt_by_symbol={"SPX500": CRT(
            "SPX500", "BEARISH", CLOSE_TIME - timedelta(hours=1), "CRT_H4_FAMILY", True
        )},
        evaluated_at=observed,
    )
    assert len(opportunities) == 1
    assert opportunities[0].route == "CRT_SMT_MSS"
    assert opportunities[0].crt_family == "CRT_H4_FAMILY"
    assert opportunities[0].status == "RESEARCH_ONLY"


def test_independent_route_when_crt_is_absent() -> None:
    opportunities = qualify_research_opportunities(
        candidates=detect_smt(candles()),
        mss_by_symbol={"NDX100": MSS(
            "NDX100", "BEARISH", CLOSE_TIME + timedelta(minutes=5),
            d("201"), d("199"),
        )},
        crt_by_symbol={},
        evaluated_at=CLOSE_TIME + timedelta(minutes=5),
    )
    assert len(opportunities) == 1
    assert opportunities[0].instrument == "NDX100"
    assert opportunities[0].route == "SMT_MSS_NO_CRT"
    assert opportunities[0].crt_family is None


def test_mss_required_no_unconfirmed_structure() -> None:
    kwargs = {
        "candidates": detect_smt(candles()),
        "crt_by_symbol": {},
        "evaluated_at": CLOSE_TIME + timedelta(minutes=5),
    }
    assert not qualify_research_opportunities(mss_by_symbol={}, **kwargs)
    future = MSS(
        "SPX500", "BEARISH", CLOSE_TIME + timedelta(minutes=15),
        d("101"), d("99"),
    )
    assert not qualify_research_opportunities(
        mss_by_symbol={"SPX500": future}, **kwargs
    )
    wrong_close = MSS(
        "SPX500", "BEARISH", CLOSE_TIME + timedelta(minutes=5),
        d("99"), d("100"),
    )
    assert not qualify_research_opportunities(
        mss_by_symbol={"SPX500": wrong_close}, **kwargs
    )


def test_opposite_crt_blocks_opportunistic_no_crt_fallback() -> None:
    result = qualify_research_opportunities(
        candidates=detect_smt(candles()),
        mss_by_symbol={"SPX500": confirmed()},
        crt_by_symbol={"SPX500": CRT(
            "SPX500", "BULLISH", CLOSE_TIME, "OTHER_CRT", True,
        )},
        evaluated_at=CLOSE_TIME + timedelta(minutes=5),
    )
    assert not result


def test_outside_ny_window_and_stale_candidates_fail_closed() -> None:
    candidates = detect_smt(candles())
    assert not qualify_research_opportunities(
        candidates=candidates,
        mss_by_symbol={"SPX500": confirmed()},
        crt_by_symbol={},
        evaluated_at=CLOSE_TIME + timedelta(hours=2),
    )
    assert not qualify_research_opportunities(
        candidates=candidates,
        mss_by_symbol={"SPX500": confirmed()},
        crt_by_symbol={},
        evaluated_at=CLOSE_TIME + timedelta(minutes=5),
        max_age=timedelta(seconds=30),
    )


def test_invalid_prices_and_naive_timestamps_rejected() -> None:
    with pytest.raises(ValueError, match="UTC-aware"):
        Candle("SPX500", "feed", datetime(2026, 11, 5, 15, 0),
               d("100"), d("102"), d("98"), d("100"))
    with pytest.raises(ValueError, match="OHLC"):
        Candle("SPX500", "feed", CLOSE_TIME,
               d("100"), d("99"), d("98"), d("100"))


def test_utc_dst_conversion_uses_new_york_zoneinfo() -> None:
    # EST in November: 15:05 UTC is 10:05 NY.
    # EDT in July: 14:05 UTC is 10:05 NY.
    from qore.infrastructure.trader_lab.index_smt_research import NY

    assert (CLOSE_TIME + timedelta(minutes=5)).astimezone(NY).hour == 10
    assert datetime(2026, 7, 7, 14, 5, tzinfo=UTC).astimezone(NY).hour == 10

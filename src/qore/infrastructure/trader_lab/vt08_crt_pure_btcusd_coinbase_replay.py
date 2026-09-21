"""Lossless Coinbase BTC-USD M5 research evidence for VT08 CRT PURE.

This source is deliberately separate from the cTrader baseline. It exists to test the
full crypto timing family when the broker CFD feed has a daily maintenance gap.
No bar is synthesized, forward-filled, or merged across providers.
"""

from __future__ import annotations

import argparse
import json
import time
from dataclasses import asdict
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from qore.infrastructure.trader_lab.vt08_crt_pure_2y_replay import (
    END_EXCLUSIVE,
    START,
    ReplayBar,
    run_market_replay,
    summarize,
)
from qore.infrastructure.traders.crt_pure_identity import CrtPureMarket

SOURCE_ID = "COINBASE_EXCHANGE_BTC_USD"
PRODUCT_ID = "BTC-USD"
GRANULARITY_SECONDS = 300
CHUNK_CANDLES = 250
PRICE_SCALE = Decimal("100000000")
BASE_URL = f"https://api.exchange.coinbase.com/products/{PRODUCT_ID}/candles"
FETCH_MARGIN = timedelta(days=1)


def _scaled_price(value: object) -> int:
    decimal_value = Decimal(str(value))
    scaled = decimal_value * PRICE_SCALE
    if scaled != scaled.to_integral_value():
        raise ValueError("Coinbase price exceeds fixed 1e-8 research precision")
    return int(scaled)


def _parse_coinbase_row(row: object) -> ReplayBar:
    if not isinstance(row, list) or len(row) < 5:
        raise ValueError("Coinbase candle row must contain time/low/high/open/close")
    opened_at = datetime.fromtimestamp(int(row[0]), tz=UTC)
    low = _scaled_price(row[1])
    high = _scaled_price(row[2])
    opened = _scaled_price(row[3])
    closed = _scaled_price(row[4])
    if low > min(opened, closed) or high < max(opened, closed) or low > high:
        raise ValueError("Coinbase candle violates OHLC ordering")
    return ReplayBar(
        opened_at=opened_at,
        open_price=opened,
        high_price=high,
        low_price=low,
        close_price=closed,
    )


def _request_json(url: str, *, attempts: int = 6) -> object:
    headers = {
        "Accept": "application/json",
        "User-Agent": "qore-core-vt08-crt-research/1.0",
    }
    for attempt in range(attempts):
        try:
            with urlopen(Request(url, headers=headers), timeout=30) as response:
                payload = response.read().decode("utf-8")
            return json.loads(payload)
        except HTTPError as error:
            if error.code not in {429, 500, 502, 503, 504} or attempt + 1 == attempts:
                raise
        except URLError:
            if attempt + 1 == attempts:
                raise
        time.sleep(min(4.0, 0.4 * (2**attempt)))
    raise RuntimeError("unreachable Coinbase retry state")


def _fetch_chunk(opened_at: datetime, closed_at: datetime) -> tuple[ReplayBar, ...]:
    query = urlencode(
        {
            "start": opened_at.astimezone(UTC).isoformat().replace("+00:00", "Z"),
            "end": closed_at.astimezone(UTC).isoformat().replace("+00:00", "Z"),
            "granularity": GRANULARITY_SECONDS,
        }
    )
    payload = _request_json(f"{BASE_URL}?{query}")
    if not isinstance(payload, list):
        raise RuntimeError("Coinbase candles response must be a list")
    bars = tuple(_parse_coinbase_row(row) for row in payload)
    return tuple(
        sorted(
            (bar for bar in bars if opened_at <= bar.opened_at < closed_at),
            key=lambda item: item.opened_at,
        )
    )


def _expected_opens(opened_at: datetime, closed_at: datetime) -> tuple[datetime, ...]:
    rows: list[datetime] = []
    cursor = opened_at
    step = timedelta(seconds=GRANULARITY_SECONDS)
    while cursor < closed_at:
        rows.append(cursor)
        cursor += step
    return tuple(rows)


def _coverage(
    bars: tuple[ReplayBar, ...],
    opened_at: datetime,
    closed_at: datetime,
) -> dict[str, Any]:
    by_time = {bar.opened_at: bar for bar in bars}
    expected = _expected_opens(opened_at, closed_at)
    missing = tuple(item for item in expected if item not in by_time)
    return {
        "expected_bars": len(expected),
        "observed_bars": len(by_time),
        "missing_bars": len(missing),
        "first_missing": None if not missing else missing[0].isoformat(),
        "last_missing": None if not missing else missing[-1].isoformat(),
        "complete": not missing and len(by_time) == len(expected),
    }


def load_coinbase_two_year_m5() -> tuple[ReplayBar, ...]:
    fetch_start = START - FETCH_MARGIN
    fetch_end = END_EXCLUSIVE + FETCH_MARGIN
    chunk_span = timedelta(seconds=GRANULARITY_SECONDS * CHUNK_CANDLES)
    by_time: dict[datetime, ReplayBar] = {}
    cursor = fetch_start
    request_count = 0

    while cursor < fetch_end:
        closed = min(cursor + chunk_span, fetch_end)
        for bar in _fetch_chunk(cursor, closed):
            existing = by_time.get(bar.opened_at)
            if existing is None:
                by_time[bar.opened_at] = bar
            elif existing.payload() != bar.payload():
                raise RuntimeError("contradictory duplicate Coinbase M5 candle")
        request_count += 1
        if request_count % 50 == 0:
            print(f"COINBASE_PROGRESS_REQUESTS={request_count}", flush=True)
        cursor = closed
        time.sleep(0.12)

    bars = tuple(by_time[key] for key in sorted(by_time))
    coverage = _coverage(bars, fetch_start, fetch_end)
    if not coverage["complete"]:
        raise RuntimeError(
            "Coinbase BTC-USD M5 coverage is not lossless: " + json.dumps(coverage)
        )
    return bars


def _triplet_summary(trades: tuple[object, ...], triplet: str) -> dict[str, Any]:
    selected = tuple(item for item in trades if getattr(item, "timing_triplet") == triplet)
    return summarize(selected)  # type: ignore[arg-type]


def build_coinbase_report(
    bars: tuple[ReplayBar, ...],
) -> tuple[dict[str, Any], tuple[object, ...]]:
    trades = run_market_replay(CrtPureMarket.BTCUSD, bars)
    fetch_start = START - FETCH_MARGIN
    fetch_end = END_EXCLUSIVE + FETCH_MARGIN
    report = {
        "schema": "qore.vt08.crt_pure.btcusd_coinbase_2y.v1",
        "source": SOURCE_ID,
        "product_id": PRODUCT_ID,
        "granularity_seconds": GRANULARITY_SECONDS,
        "window_start": START.isoformat(),
        "window_end_exclusive": END_EXCLUSIVE.isoformat(),
        "coverage": _coverage(bars, fetch_start, fetch_end),
        "full_2y": summarize(trades),
        "triplet_1": _triplet_summary(tuple(trades), "1"),
        "triplet_2": _triplet_summary(tuple(trades), "2"),
        "provider_mixing": False,
        "synthetic_bars": False,
        "research_only": True,
        "candidate_certified": False,
    }
    return report, tuple(trades)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("output", type=Path)
    args = parser.parse_args()

    bars = load_coinbase_two_year_m5()
    report, trades = build_coinbase_report(bars)
    args.output.mkdir(parents=True, exist_ok=True)
    with (args.output / "trades.jsonl").open("w", encoding="utf-8") as handle:
        for trade in trades:
            handle.write(json.dumps(asdict(trade), sort_keys=True) + "\n")
    (args.output / "report.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print("CRT_COINBASE_BTCUSD_JSON=" + json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    main()

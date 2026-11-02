#!/usr/bin/env python3
"""Coinbase Exchange public BTC-USD M5 historical calibration (no account/API key).

Strictly read-only. Does not share raw candles or promote to untouched holdout.
Product = BTC-USD only; date range frozen to match 33 cTrader source QA.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import time
from datetime import UTC, datetime, timedelta
from decimal import Decimal, InvalidOperation
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from scripts.crt_radar_archived_m5_prescreen import (
    CAL_END,
    CAL_START,
    M5,
    completed_h4,
    frozen_bucket,
)

BASE = "https://api.exchange.coinbase.com/products/BTC-USD/candles"
M5_SECONDS = 300


def _iso(t: datetime) -> str:
    return t.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def _window(start: datetime, end: datetime) -> list[list[object]]:
    """Exactly one day (288 M5) per request, below 300-point Coinbase cap."""
    if end <= start or end - start > timedelta(days=1):
        raise ValueError("COINBASE_WINDOW_BOUNDED_TO_ONE_DAY")
    query = urlencode({"start": _iso(start), "end": _iso(end), "granularity": 300})
    req = Request(BASE + "?" + query, headers={
        "Accept": "application/json",
        "User-Agent": "QORE-CRT-RADAR-Research-ReadOnly/1.0",
    })
    for attempt in range(4):
        try:
            with urlopen(req, timeout=20) as resp:
                if resp.status != 200:
                    raise ValueError("COINBASE_CANDLES_HTTP_NOT_OK")
                payload = resp.read(2_000_000)
            out = json.loads(payload)
            if not isinstance(out, list) or len(out) > 300:
                raise ValueError("COINBASE_RESPONSE_INVALID_OR_TRUNCATED")
            return out
        except HTTPError as exc:
            if exc.code not in (429, 500, 502, 503) or attempt == 3:
                raise RuntimeError("COINBASE_HTTP_READ_FAILED") from exc
        except (URLError, TimeoutError) as exc:
            if attempt == 3:
                raise RuntimeError("COINBASE_NETWORK_READ_FAILED") from exc
        time.sleep(1.5 * (attempt + 1))
    raise RuntimeError("COINBASE_RETRY_EXHAUSTED")


def _parse(row: object) -> tuple[int, M5, tuple[str, ...]]:
    if not isinstance(row, list) or len(row) != 6:
        raise ValueError("COINBASE_OHLCV_6_FIELDS_REQUIRED")
    ts, low, high, opened, close, volume = row
    if type(ts) is not int or ts <= 0 or ts % M5_SECONDS:
        raise ValueError("COINBASE_M5_TIMESTAMP_INVALID")
    try:
        lo, hi, op, cl, vol = (
            Decimal(str(x)) for x in (low, high, opened, close, volume)
        )
    except (InvalidOperation, ValueError) as exc:
        raise ValueError("COINBASE_BAD_DECIMAL") from exc
    if any(not v.is_finite() for v in (lo, hi, op, cl, vol)):
        raise ValueError("COINBASE_NONFINITE_OHLC")
    if lo <= 0 or hi < max(op, cl) or lo > min(op, cl) or vol < 0:
        raise ValueError("COINBASE_OHLC_RELATION_INVALID")
    at = datetime.fromtimestamp(ts, UTC)
    b = M5(at, op, hi, lo, cl)
    # Digest canonical source observations without publishing raw prices.
    canonical = (str(ts), str(lo), str(hi), str(op), str(cl), str(vol))
    return ts, b, canonical


def collect() -> tuple[list[M5], str, int]:
    seen: dict[int, tuple[M5, tuple[str, ...]]] = {}
    cursor = CAL_START
    requests = 0
    while cursor < CAL_END:
        next_end = min(cursor + timedelta(days=1), CAL_END)
        for raw in _window(cursor, next_end):
            sec, bar, canonical = _parse(raw)
            if not CAL_START <= bar.opened_at < CAL_END:
                continue
            prior = seen.get(sec)
            if prior is not None and prior[1] != canonical:
                raise ValueError("COINBASE_CONFLICTING_DUPLICATE_M5")
            seen[sec] = (bar, canonical)
        requests += 1
        cursor = next_end
        time.sleep(0.15)
    records = [seen[k] for k in sorted(seen)]
    if len(records) < 12000:
        raise ValueError("INSUFFICIENT_BTC_M5_COVERAGE_FOR_47_DAY_CALIBRATION")
    h = hashlib.sha256()
    for _, canonical in records:
        h.update(json.dumps(canonical, separators=(",", ":")).encode())
        h.update(b"\n")
    return [b for b, _ in records], h.hexdigest(), requests


def structural_qa(bars: list[M5]) -> dict[str, int]:
    current_key: str | None = None
    group: list[M5] = []
    previous = None
    last_c2: tuple[object, int] | None = None
    completed = 0
    c1 = 0
    c2 = 0
    c3 = 0
    rejected = 0
    internal = 0

    def flush() -> None:
        nonlocal previous, last_c2, completed, c1, c2, c3, rejected, internal
        if not group:
            return
        h4 = completed_h4(group, "forex")  # BTC NY C1 01/05/21
        if h4 is None:
            rejected += 1
            if any(group[i].opened_at - group[i - 1].opened_at != timedelta(minutes=5)
                   for i in range(1, len(group))):
                internal += 1
            previous = None
            last_c2 = None
            return
        completed += 1
        if h4.c1_allowed:
            c1 += 1
        if last_c2 is not None:
            candidate, direction = last_c2
            if (candidate.closed_at == h4.opened_at and
                (h4.close >= candidate.low if direction == 1 else
                 h4.close <= candidate.high)):
                c3 += 1
        last_c2 = None
        if previous is not None and h4.opened_at == previous.closed_at:
            downside = h4.low < previous.low
            upside = h4.high > previous.high
            if (previous.c1_allowed and downside != upside and
                previous.low <= h4.close <= previous.high):
                c2 += 1
                last_c2 = (h4, 1 if downside else -1)
        previous = h4

    for bar in bars:
        key, _ = frozen_bucket(bar, "forex")
        if key != current_key:
            flush()
            group = []
            current_key = key
        group.append(bar)
    flush()
    return {"complete_h4": completed, "eligible_c1_h4": c1,
            "structural_2c": c2, "structural_3c_followups": c3,
            "rejected_h4": rejected, "internal_m5_blocks": internal}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=("calibration",), required=True)
    args = parser.parse_args()
    if args.mode != "calibration":
        raise ValueError("ONLY_CALIBRATION_SUPPORTED")
    bars, digest, requests = collect()
    result = structural_qa(bars)
    payload = {
        "symbol": "BTCUSD",
        "provider": "COINBASE_EXCHANGE_PUBLIC_BTC-USD",
        "raw_m5_bars": len(bars),
        "requests": requests,
        "calibration_source_digest_sha256": digest,
        "mode": "PREVIOUSLY_DEFINED_CALIBRATION_ONLY_NOT_FROZEN_HOLDOUT",
        "full_pine_provider_parity_certified": False,
        "mss_m15_certified": False,
        "live_alerts_enabled": False,
        "orders_enabled": False,
        **result,
    }
    print(json.dumps(payload, sort_keys=True, separators=(",", ":")))


if __name__ == "__main__":
    main()

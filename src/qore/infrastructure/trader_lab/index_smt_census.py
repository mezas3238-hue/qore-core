"""Read-only cTrader DEMO M5 -> M15 index SMT candidate census.

Accepts separately exported real closed M5 candles. Does not connect to a broker,
invent bars, generate trade signals, replay profits or authorize LIVE activity.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

from qore.infrastructure.trader_lab.index_smt_research import (
    NY,
    SMT,
    SYMBOLS,
    WINDOW_END,
    WINDOW_START,
    Candle,
    Symbol,
    detect_smt,
)

M5 = timedelta(minutes=5)
M15 = timedelta(minutes=15)
CSV_FIELDS = (
    "origin", "broker", "environment", "server", "canonical_symbol",
    "broker_symbol", "open_time_utc", "open", "high", "low", "close", "closed",
)
ORIGIN = "CTRADER_IC_DEMO"
BROKER = "IC MARKETS"
ENVIRONMENT = "DEMO"
MAX_EXPORT_BYTES = 64 * 1024 * 1024


class SMTExportError(ValueError):
    """Malformed or unprovable export; no best-effort time-series repair."""


@dataclass(frozen=True, slots=True)
class RawM5:
    opened_at: datetime
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal


@dataclass(frozen=True, slots=True)
class VerifiedExport:
    symbol: Symbol
    broker_symbol: str
    server: str
    feed_id: str
    sha256: str
    raw_m5_count: int
    complete_m15: tuple[Candle, ...]
    incomplete_m15_buckets: int


def _utc_open(value: str) -> datetime:
    try:
        at = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (TypeError, ValueError) as exc:
        raise SMTExportError("invalid ISO8601 opening timestamp") from exc
    if at.tzinfo is None or at.utcoffset() != timedelta(0):
        raise SMTExportError("opening timestamp must be explicitly UTC")
    at = at.astimezone(UTC)
    if at.second or at.microsecond or at.minute % 5:
        raise SMTExportError("M5 opening timestamp is not on the five-minute grid")
    return at


def _price(row: Mapping[str, str], field: str) -> Decimal:
    try:
        value = Decimal(row[field])
    except (KeyError, InvalidOperation, TypeError) as exc:
        raise SMTExportError(f"invalid {field} field") from exc
    if not value.is_finite() or value <= 0:
        raise SMTExportError(f"{field} must be finite and >0")
    return value


def _m15_bucket(opened_at: datetime) -> datetime:
    return opened_at.replace(minute=(opened_at.minute // 15) * 15)


def load_ctrader_m5_export(
    path: str | Path, *, symbol: Symbol, broker_symbol: str
) -> VerifiedExport:
    """Fail closed on a known canonical index bound to a caller-selected broker symbol."""
    if symbol not in SYMBOLS or not broker_symbol or broker_symbol.strip() != broker_symbol:
        raise SMTExportError("invalid canonical-to-broker-symbol mapping")
    try:
        payload = Path(path).read_bytes()
    except OSError as exc:
        raise SMTExportError("unable to read M5 export") from exc
    if not payload or len(payload) > MAX_EXPORT_BYTES:
        raise SMTExportError("empty or oversized export")
    try:
        lines = payload.decode("utf-8-sig").splitlines()
    except UnicodeDecodeError as exc:
        raise SMTExportError("export must be UTF-8 text") from exc
    reader = csv.DictReader(lines, strict=True)
    if tuple(reader.fieldnames or ()) != CSV_FIELDS:
        raise SMTExportError("CSV header differs from the frozen 12-column schema")
    raws: list[RawM5] = []
    server: str | None = None
    previous_at: datetime | None = None
    try:
        for line_num, row in enumerate(reader, start=2):
            if None in row or any(v is None for v in row.values()):
                raise SMTExportError(f"line {line_num}: extra or missing CSV values")
            if (
                row["origin"] != ORIGIN
                or row["broker"] != BROKER
                or row["environment"] != ENVIRONMENT
                or row["canonical_symbol"] != symbol
                or row["broker_symbol"] != broker_symbol
                or row["closed"] != "true"
            ):
                raise SMTExportError(f"line {line_num}: provenance/symbol/closure mismatch")
            this_server = row["server"]
            if not this_server or this_server.strip() != this_server:
                raise SMTExportError(f"line {line_num}: server is required")
            if server is not None and server != this_server:
                raise SMTExportError("CSV mixes cTrader servers")
            server = this_server
            opened_at = _utc_open(row["open_time_utc"])
            if previous_at is not None and opened_at <= previous_at:
                raise SMTExportError("M5 rows must be strictly chronological and unique")
            previous_at = opened_at
            op, hi, lo, cl = (
                _price(row, field) for field in ("open", "high", "low", "close")
            )
            if lo > min(op, cl) or hi < max(op, cl) or lo > hi:
                raise SMTExportError(f"line {line_num}: impossible OHLC")
            raws.append(RawM5(opened_at, op, hi, lo, cl))
    except csv.Error as exc:
        raise SMTExportError("malformed CSV syntax") from exc
    if not raws or server is None:
        raise SMTExportError("M5 data rows missing")
    feed_id = f"{ORIGIN}:{BROKER}:{ENVIRONMENT}:{server}"
    buckets: dict[datetime, dict[datetime, RawM5]] = {}
    for row in raws:
        start = _m15_bucket(row.opened_at)
        buckets.setdefault(start, {})[row.opened_at] = row
    aggregated: list[Candle] = []
    incomplete = 0
    for start, bucket in sorted(buckets.items()):
        keys = (start, start + M5, start + M5 * 2)
        if set(bucket) != set(keys):
            incomplete += 1
            continue
        trio = [bucket[k] for k in keys]
        aggregated.append(Candle(
            symbol=symbol,
            feed_id=feed_id,
            closed_at=start + M15,
            open=trio[0].open,
            high=max(c.high for c in trio),
            low=min(c.low for c in trio),
            close=trio[-1].close,
        ))
    return VerifiedExport(
        symbol=symbol,
        broker_symbol=broker_symbol,
        server=server,
        feed_id=feed_id,
        sha256=hashlib.sha256(payload).hexdigest(),
        raw_m5_count=len(raws),
        complete_m15=tuple(aggregated),
        incomplete_m15_buckets=incomplete,
    )


def _candidate(e: SMT) -> dict[str, str]:
    return {
        "pair": "/".join(e.pair),
        "side": e.direction,
        "sweeping_symbol": e.sweeping_symbol,
        "confirmed_at_utc": e.observed_at.isoformat(),
        "reference_price": str(e.reference),
        "swept_price": str(e.swept_extreme),
    }


def census_smt_candidates(
    exports: Mapping[Symbol, VerifiedExport], *, lookback: int = 8
) -> dict[str, Any]:
    """Chronological candidate-only census with explicit data completeness counts.

    No CRT/MSS evidences are fabricated and no economic backtest is performed.
    """
    if set(exports) != set(SYMBOLS):
        raise SMTExportError("all three index exports are mandatory")
    if type(lookback) is not int or lookback < 3:
        raise SMTExportError("lookback must be an integer >=3")
    feeds = {x.feed_id for x in exports.values()}
    if len(feeds) != 1:
        raise SMTExportError("three indices must use one exact source/server identity")
    if any(x.symbol != symbol for symbol, x in exports.items()):
        raise SMTExportError("canonical symbol and dataset mismatch")
    by_symbol = {
        sym: {c.closed_at: c for c in exports[sym].complete_m15}
        for sym in SYMBOLS
    }
    observed_closes = sorted(set().union(*(set(b) for b in by_symbol.values())))
    expected_windows = 0
    skipped_partial = 0
    skipped_lookback_gap = 0
    complete_windows = 0
    candidate_records: list[dict[str, str]] = []
    unique_event_keys: set[tuple[str, str, str, str]] = set()
    for close_at in observed_closes:
        local = close_at.astimezone(NY)
        if local.weekday() >= 5 or not WINDOW_START <= local.time() < WINDOW_END:
            continue
        expected_windows += 1
        if any(close_at not in by_symbol[sym] for sym in SYMBOLS):
            skipped_partial += 1
            continue
        window_times = [
            close_at - M15 * offset
            for offset in range(lookback, -1, -1)
        ]
        if any(any(at not in by_symbol[sym] for at in window_times) for sym in SYMBOLS):
            skipped_lookback_gap += 1
            continue
        windows = {
            sym: [by_symbol[sym][at] for at in window_times]
            for sym in SYMBOLS
        }
        complete_windows += 1
        for candidate in detect_smt(windows, lookback=lookback):
            item = _candidate(candidate)
            key = (
                item["pair"], item["side"], item["sweeping_symbol"],
                item["confirmed_at_utc"],
            )
            if key in unique_event_keys:
                raise SMTExportError("candidate evidence duplicated")
            unique_event_keys.add(key)
            candidate_records.append(item)
    count_by_pair_direction: dict[str, int] = {}
    for event in candidate_records:
        label = f"{event['pair']}:{event['side']}"
        count_by_pair_direction[label] = count_by_pair_direction.get(label, 0) + 1
    return {
        "schema": "QORE_INDEX_SMT_M15_CENSUS_R1",
        "research_only": True,
        "authorized_to_emit_alerts": False,
        "authorized_to_trade": False,
        "crt_mss_certified": False,
        "economic_edge_certified": False,
        "data_source_authenticity_verified": False,
        "feed_id": next(iter(feeds)),
        "lookback_m15": lookback,
        "exports": {
            sym: {
                "broker_symbol": exports[sym].broker_symbol,
                "sha256": exports[sym].sha256,
                "raw_m5_count": exports[sym].raw_m5_count,
                "complete_m15_count": len(exports[sym].complete_m15),
                "incomplete_m15_buckets": exports[sym].incomplete_m15_buckets,
            }
            for sym in SYMBOLS
        },
        "observation_windows": expected_windows,
        "windows_missing_instrument": skipped_partial,
        "windows_missing_prior_m15": skipped_lookback_gap,
        "complete_windows": complete_windows,
        "candidate_count": len(candidate_records),
        "candidate_counts_by_pair_side": count_by_pair_direction,
        "candidates": candidate_records,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="OFFLINE three-index SMT candidate census")
    for name in ("spx500", "ndx100", "us30"):
        parser.add_argument(f"--{name}-csv", type=Path, required=True)
        parser.add_argument(f"--{name}-broker-symbol", required=True)
    parser.add_argument("--out", type=Path, required=True)
    options = parser.parse_args()
    exports = {
        symbol: load_ctrader_m5_export(
            getattr(options, f"{symbol.lower()}_csv"),
            symbol=symbol,
            broker_symbol=getattr(options, f"{symbol.lower()}_broker_symbol"),
        )
        for symbol in SYMBOLS
    }
    result = census_smt_candidates(exports)
    options.out.write_text(
        json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()

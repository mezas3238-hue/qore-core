"""Metadata-only pre-2016 cTrader availability census for Capitalizer.

This module probes provider-native M1 transport but retains only timestamp/count
metadata. It never materializes or writes OHLC payloads. The purpose is to
prove whether the nine-market universe has a common untouched pre-2016 window
before any candidate OOS payload is opened.

The latest preferred holdout is frozen a priori:
- causal lookback start: 2014-08-27T00:00:00Z
- holdout start:        2014-09-17T00:00:00Z
- holdout end:          2016-09-17T00:00:00Z

No economics, entry reconstruction, PF, DD, PnL, stops or targets are produced.
"""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from collections.abc import Iterable
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, cast

from qore.infrastructure.ctrader_open_api_client import (
    SpotwareCTraderOpenApiClient,
)
from qore.infrastructure.trader_lab import (
    capitalizer_cibo_10y_m1_clone_v1 as base,
)
from qore.kernel.result import Failure

IDENTITY = "QORE_CAPITALIZER_PRE2016_CTRADER_AVAILABILITY_CENSUS_V1"
LOOKBACK_START = datetime(2014, 8, 27, tzinfo=UTC)
HOLDOUT_START = datetime(2014, 9, 17, tzinfo=UTC)
HOLDOUT_END_EXCLUSIVE = datetime(2016, 9, 17, tzinfo=UTC)
CHUNK_DAYS = 2


def _month_key(value: datetime) -> str:
    return f"{value.year:04d}-{value.month:02d}"


def _months(start: datetime, end_exclusive: datetime) -> tuple[str, ...]:
    cursor = datetime(start.year, start.month, 1, tzinfo=UTC)
    result: list[str] = []
    while cursor < end_exclusive:
        result.append(_month_key(cursor))
        if cursor.month == 12:
            cursor = datetime(cursor.year + 1, 1, 1, tzinfo=UTC)
        else:
            cursor = datetime(cursor.year, cursor.month + 1, 1, tzinfo=UTC)
    return tuple(result)


def census_symbol(symbol: str, output: Path) -> dict[str, Any]:
    if symbol not in base.TARGET_SYMBOLS:
        raise ValueError(f"symbol outside Capitalizer universe: {symbol}")
    output.mkdir(parents=True, exist_ok=True)

    client = SpotwareCTraderOpenApiClient(
        credentials=base._credentials(),
        request_timeout_seconds=30.0,
    )
    try:
        ready = client.connect_and_authenticate()
        if isinstance(ready, Failure):
            raise RuntimeError(f"cTrader authentication failed: {ready.error}")
        provider_symbol, symbol_id, digits = base._selected_symbol(client, symbol)

        cursor = LOOKBACK_START
        chunk_index = 0
        retained = 0
        duplicate_timestamps = 0
        first_observed: datetime | None = None
        last_observed: datetime | None = None
        monthly_counts: dict[str, int] = defaultdict(int)
        seen: set[int] = set()
        chunk_meta: list[dict[str, Any]] = []

        while cursor < HOLDOUT_END_EXCLUSIVE:
            chunk_close = min(
                cursor + timedelta(days=CHUNK_DAYS),
                HOLDOUT_END_EXCLUSIVE,
            )
            native_rows = base._read_chunk(
                client,
                symbol=symbol,
                symbol_id=symbol_id,
                opened_at=cursor,
                closed_at=chunk_close,
                chunk_index=chunk_index,
            )
            chunk_first: datetime | None = None
            chunk_last: datetime | None = None
            chunk_unique = 0
            for native in cast(Iterable[object], native_rows):
                minute = base._native_int(native, "utcTimestampInMinutes")
                observed = datetime.fromtimestamp(minute * 60, tz=UTC)
                if not (cursor <= observed < chunk_close):
                    raise RuntimeError(
                        "provider returned timestamp outside requested census chunk"
                    )
                if minute in seen:
                    duplicate_timestamps += 1
                    continue
                seen.add(minute)
                chunk_unique += 1
                retained += 1
                monthly_counts[_month_key(observed)] += 1
                if first_observed is None or observed < first_observed:
                    first_observed = observed
                if last_observed is None or observed > last_observed:
                    last_observed = observed
                if chunk_first is None or observed < chunk_first:
                    chunk_first = observed
                if chunk_last is None or observed > chunk_last:
                    chunk_last = observed

            chunk_meta.append(
                {
                    "requested_start": cursor.isoformat(),
                    "requested_end_exclusive": chunk_close.isoformat(),
                    "retained_timestamp_count": chunk_unique,
                    "first_observed_timestamp": (
                        None if chunk_first is None else chunk_first.isoformat()
                    ),
                    "last_observed_timestamp": (
                        None if chunk_last is None else chunk_last.isoformat()
                    ),
                }
            )
            cursor = chunk_close
            chunk_index += 1
    finally:
        client.close()

    expected_months = _months(LOOKBACK_START, HOLDOUT_END_EXCLUSIVE)
    missing_months = tuple(
        month for month in expected_months if monthly_counts.get(month, 0) == 0
    )
    report: dict[str, Any] = {
        "identity": IDENTITY,
        "canonical_symbol": symbol,
        "provider_symbol": provider_symbol,
        "provider_symbol_id": symbol_id,
        "digits": digits,
        "requested_lookback_start": LOOKBACK_START.isoformat(),
        "frozen_holdout_start_if_common": HOLDOUT_START.isoformat(),
        "requested_end_exclusive": HOLDOUT_END_EXCLUSIVE.isoformat(),
        "retained_timestamp_count": retained,
        "duplicate_timestamp_count": duplicate_timestamps,
        "first_observed_timestamp": (
            None if first_observed is None else first_observed.isoformat()
        ),
        "last_observed_timestamp": (
            None if last_observed is None else last_observed.isoformat()
        ),
        "monthly_timestamp_counts": dict(sorted(monthly_counts.items())),
        "missing_calendar_months": list(missing_months),
        "all_requested_months_have_provider_data": not missing_months,
        "chunk_metadata": chunk_meta,
        "ohlc_retained": False,
        "raw_m1_ledger_written": False,
        "economics_computed": False,
        "trade_reconstruction_performed": False,
        "outcome_selection_performed": False,
        "read_only": True,
        "live_authorized": False,
        "real_capital_authorized": False,
    }
    (output / f"{symbol.lower()}-pre2016-availability.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("symbol", choices=base.TARGET_SYMBOLS)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    report = census_symbol(args.symbol, args.output)
    print(
        json.dumps(
            {
                "symbol": report["canonical_symbol"],
                "retained_timestamp_count": report["retained_timestamp_count"],
                "first_observed_timestamp": report["first_observed_timestamp"],
                "last_observed_timestamp": report["last_observed_timestamp"],
                "missing_calendar_months": report["missing_calendar_months"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()

"""Metadata-only cTrader historical BID/ASK availability census.

Research-only. This module asks the configured DEMO provider whether historical
tick data exists for fixed consumed-period anchors. It never persists tick
prices or computes spread/economic outcomes.
"""

from __future__ import annotations

import argparse
import json
import time
from collections.abc import Iterable
from dataclasses import asdict, dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import cast

from qore.infrastructure.ctrader_open_api_client import (
    SpotwareCTraderOpenApiClient,
)
from qore.infrastructure.trader_lab.capitalizer_cibo_10y_m1_clone_v1 import (
    TARGET_SYMBOLS,
    _credentials,
    _selected_symbol,
)
from qore.kernel.result import Failure

IDENTITY = "QORE_CAPITALIZER_CTRADER_HISTORICAL_BID_ASK_AVAILABILITY_CENSUS_V1"
WINDOW_MINUTES = 5
MIN_REQUEST_INTERVAL_SECONDS = 0.25

ANCHORS = (
    datetime(2020, 10, 1, 15, 0, tzinfo=UTC),
    datetime(2021, 10, 1, 15, 0, tzinfo=UTC),
    datetime(2022, 10, 3, 15, 0, tzinfo=UTC),
    datetime(2023, 10, 2, 15, 0, tzinfo=UTC),
    datetime(2024, 10, 1, 15, 0, tzinfo=UTC),
    datetime(2025, 10, 1, 15, 0, tzinfo=UTC),
)

QUOTE_TYPES = (
    ("BID", 1),
    ("ASK", 2),
)


@dataclass(frozen=True, slots=True)
class TickAvailabilityRow:
    canonical_symbol: str
    provider_symbol: str
    provider_symbol_id: int
    digits: int
    requested_start: str
    requested_end_exclusive: str
    quote_type: str
    request_succeeded: bool
    tick_count: int
    has_more: bool | None
    failure_type: str | None
    prices_retained: bool = False
    spread_computed: bool = False
    trade_outcomes_read: bool = False
    fresh_holdout_touched: bool = False


def _request_availability(
    client: SpotwareCTraderOpenApiClient,
    *,
    canonical_symbol: str,
    provider_symbol: str,
    symbol_id: int,
    digits: int,
    opened_at: datetime,
    quote_name: str,
    quote_type: int,
    request_index: int,
) -> TickAvailabilityRow:
    closed_at = opened_at + timedelta(minutes=WINDOW_MINUTES)
    result = client.request(
        "ProtoOAGetTickDataReq",
        {
            "ctidTraderAccountId": client.account_id,
            "symbolId": symbol_id,
            "type": quote_type,
            "fromTimestamp": int(opened_at.timestamp() * 1000),
            "toTimestamp": int(closed_at.timestamp() * 1000) - 1,
        },
        client_msg_id=(
            f"capitalizer-bidask-census:{canonical_symbol}:"
            f"{quote_name}:{request_index}"
        ),
        timeout_seconds=60.0,
    )
    if isinstance(result, Failure):
        return TickAvailabilityRow(
            canonical_symbol=canonical_symbol,
            provider_symbol=provider_symbol,
            provider_symbol_id=symbol_id,
            digits=digits,
            requested_start=opened_at.isoformat(),
            requested_end_exclusive=closed_at.isoformat(),
            quote_type=quote_name,
            request_succeeded=False,
            tick_count=0,
            has_more=None,
            failure_type=type(result.error).__name__,
        )

    account_id = getattr(result.value, "ctidTraderAccountId", None)
    if account_id != client.account_id:
        raise RuntimeError("historical tick response account mismatch")
    ticks = tuple(cast(Iterable[object], getattr(result.value, "tickData", ())))
    has_more = getattr(result.value, "hasMore", None)
    if type(has_more) is not bool:
        raise RuntimeError("historical tick response missing hasMore")
    # ProtoOAGetTickDataRes uses compressed timestamp semantics: the first
    # tick carries absolute Unix milliseconds and later rows carry deltas.
    # This census is metadata-only, so it deliberately does not decode or
    # retain individual tick timestamps/prices.
    return TickAvailabilityRow(
        canonical_symbol=canonical_symbol,
        provider_symbol=provider_symbol,
        provider_symbol_id=symbol_id,
        digits=digits,
        requested_start=opened_at.isoformat(),
        requested_end_exclusive=closed_at.isoformat(),
        quote_type=quote_name,
        request_succeeded=True,
        tick_count=len(ticks),
        has_more=has_more,
        failure_type=None,
    )


def census_symbol(symbol: str, output: Path) -> dict[str, object]:
    if symbol not in TARGET_SYMBOLS:
        raise ValueError(f"symbol outside Capitalizer universe: {symbol}")
    output.mkdir(parents=True, exist_ok=True)

    client = SpotwareCTraderOpenApiClient(
        credentials=_credentials(),
        request_timeout_seconds=30.0,
    )
    try:
        ready = client.connect_and_authenticate()
        if isinstance(ready, Failure):
            raise RuntimeError(
                f"cTrader DEMO authentication failed: {type(ready.error).__name__}"
            )
        provider_symbol, symbol_id, digits = _selected_symbol(client, symbol)

        rows: list[TickAvailabilityRow] = []
        request_index = 0
        for anchor in ANCHORS:
            for quote_name, quote_type in QUOTE_TYPES:
                rows.append(
                    _request_availability(
                        client,
                        canonical_symbol=symbol,
                        provider_symbol=provider_symbol,
                        symbol_id=symbol_id,
                        digits=digits,
                        opened_at=anchor,
                        quote_name=quote_name,
                        quote_type=quote_type,
                        request_index=request_index,
                    )
                )
                request_index += 1
                time.sleep(MIN_REQUEST_INTERVAL_SECONDS)
    finally:
        client.close()

    by_anchor: dict[str, dict[str, TickAvailabilityRow]] = {}
    for row in rows:
        by_anchor.setdefault(row.requested_start, {})[row.quote_type] = row
    paired_nonempty = sum(
        sides.get("BID") is not None
        and sides.get("ASK") is not None
        and sides["BID"].request_succeeded
        and sides["ASK"].request_succeeded
        and sides["BID"].tick_count > 0
        and sides["ASK"].tick_count > 0
        for sides in by_anchor.values()
    )
    report: dict[str, object] = {
        "identity": IDENTITY,
        "canonical_symbol": symbol,
        "provider_symbol": provider_symbol,
        "provider_symbol_id": symbol_id,
        "digits": digits,
        "anchor_count": len(ANCHORS),
        "request_count": len(rows),
        "successful_requests": sum(row.request_succeeded for row in rows),
        "nonempty_bid_anchors": sum(
            row.quote_type == "BID"
            and row.request_succeeded
            and row.tick_count > 0
            for row in rows
        ),
        "nonempty_ask_anchors": sum(
            row.quote_type == "ASK"
            and row.request_succeeded
            and row.tick_count > 0
            for row in rows
        ),
        "paired_nonempty_anchors": paired_nonempty,
        "all_anchors_have_bid_and_ask": paired_nonempty == len(ANCHORS),
        "any_response_truncated": any(row.has_more is True for row in rows),
        "prices_retained": False,
        "spread_computed": False,
        "trade_outcomes_read": False,
        "fresh_holdout_touched": False,
        "cost_certification_satisfied": False,
        "rows": [asdict(row) for row in rows],
    }
    (output / "capitalizer-ctrader-bidask-availability-census-v1.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return report


def build_matrix(root: Path) -> dict[str, object]:
    paths = sorted(
        root.rglob("capitalizer-ctrader-bidask-availability-census-v1.json")
    )
    if len(paths) != len(TARGET_SYMBOLS):
        raise ValueError(
            f"Bid/Ask census matrix requires {len(TARGET_SYMBOLS)} reports, "
            f"got {len(paths)}"
        )
    reports = [json.loads(path.read_text(encoding="utf-8")) for path in paths]
    symbols = {str(report["canonical_symbol"]) for report in reports}
    if symbols != set(TARGET_SYMBOLS):
        raise ValueError("Bid/Ask census symbol universe mismatch")

    all_available = all(
        report["all_anchors_have_bid_and_ask"] is True
        for report in reports
    )
    result: dict[str, object] = {
        "identity": (
            "QORE_CAPITALIZER_CTRADER_HISTORICAL_BID_ASK_"
            "AVAILABILITY_MATRIX_V1"
        ),
        "market_count": len(reports),
        "anchor_count_per_market": len(ANCHORS),
        "historical_bid_ask_available_all_consumed_anchors": all_available,
        "markets_full_coverage": sum(
            report["all_anchors_have_bid_and_ask"] is True
            for report in reports
        ),
        "prices_retained": False,
        "spread_computed": False,
        "trade_outcomes_read": False,
        "fresh_holdout_touched": False,
        "cost_certification_satisfied": False,
        "next_phase": (
            "BUILD_PROVIDER_BOUND_SPREAD_EVIDENCE_AT_CONSUMED_TRADE_TIMESTAMPS"
            if all_available
            else "HISTORICAL_BID_ASK_PROVIDER_COVERAGE_INCOMPLETE"
        ),
        "markets": sorted(
            (
                {
                    "canonical_symbol": report["canonical_symbol"],
                    "successful_requests": report["successful_requests"],
                    "paired_nonempty_anchors": report["paired_nonempty_anchors"],
                    "all_anchors_have_bid_and_ask": report[
                        "all_anchors_have_bid_and_ask"
                    ],
                    "any_response_truncated": report["any_response_truncated"],
                }
                for report in reports
            ),
            key=lambda row: str(row["canonical_symbol"]),
        ),
    }
    output = root / "matrix-output"
    output.mkdir(exist_ok=True)
    (
        output / "capitalizer-ctrader-bidask-availability-matrix-v1.json"
    ).write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)

    market = sub.add_parser("market")
    market.add_argument("symbol", choices=TARGET_SYMBOLS)
    market.add_argument("output", type=Path)

    matrix = sub.add_parser("matrix")
    matrix.add_argument("root", type=Path)

    args = parser.parse_args()
    if args.command == "market":
        report = census_symbol(args.symbol, args.output)
    else:
        report = build_matrix(args.root)
    print(json.dumps(report, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

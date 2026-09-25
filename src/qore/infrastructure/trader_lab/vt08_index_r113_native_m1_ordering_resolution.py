"""VT08 Index R113 — native-M1 ordering resolution for R112 ambiguities.

R112 proved that same-M15 STOP/TARGET ambiguity is far too sparse to explain
the R66 B2 failure: one ambiguous trade in B2 and only nine across all three
consumed windows. R113 closes the remaining evidence gap without changing the
strategy.

For each exact R112 ambiguous exit M15 only:
- request provider-native M1 from cTrader DEMO for that 15-minute window;
- require all 15 one-minute bars;
- aggregate them and require exact OHLC equality with the authoritative CIBO
  M15 exit bar before using the sequence;
- scan M1 chronologically using the same gap-before-touch semantics;
- if STOP and TARGET occur in different M1 bars, record the actual first touch;
- if both occur inside the same M1, retain ambiguity and the canonical
  conservative STOP-first accounting.

No M1 signal generation occurs. No setup, stop, target, risk, anchor or trade
count changes. Resolved ordering deltas are evidence-only accounting and do not
create or certify a candidate.
"""

from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any

from qore.infrastructure.ctrader_open_api_client import (
    SpotwareCTraderOpenApiClient,
)
from qore.infrastructure.trader_lab import (
    vt08_index_r90_m1_provider_depth_probe as r90,
)
from qore.infrastructure.trader_lab import (
    vt08_index_r91_r66_m15_m1_density as r91,
)
from qore.infrastructure.trader_lab import (
    vt08_index_r112_same_m15_ambiguity_census as r112,
)
from qore.infrastructure.trader_lab import vt08_index_v2_candidate as v2
from qore.infrastructure.traders.contracts import DemoTradingSetupSide
from qore.infrastructure.traders.vt08_index_c2_positional_r1 import (
    Vt08IndexC2R1Bar,
)
from qore.kernel.result import Failure

SCHEMA = "qore.trader_lab.vt08_index_r113_native_m1_ordering_resolution.v1"
IDENTITY = "VT08_INDEX_R113_NATIVE_M1_ORDERING_RESOLUTION_001"

SOURCE_R112_RUN_ID = 35661839898
SOURCE_R112_ARTIFACT_ID = 10667714516
SOURCE_R112_ARTIFACT_DIGEST = (
    "sha256:e0b2dfd0363c2920ba7566672ffef05264d69fbfb4778e81de8568dba05f0e53"
)


def _aggregate_m1(
    bars: tuple[Vt08IndexC2R1Bar, ...],
) -> Vt08IndexC2R1Bar:
    if len(bars) != 15:
        raise ValueError("R113 requires exactly 15 native M1 bars")
    ordered = tuple(sorted(bars, key=lambda bar: bar.opened_at))
    start = ordered[0].opened_at.astimezone(UTC)
    expected = tuple(
        start + timedelta(minutes=index)
        for index in range(15)
    )
    observed = tuple(bar.opened_at.astimezone(UTC) for bar in ordered)
    if observed != expected:
        raise ValueError("R113 native M1 sequence is not contiguous")
    return Vt08IndexC2R1Bar(
        opened_at=start,
        closed_at=ordered[-1].closed_at.astimezone(UTC),
        open=ordered[0].open,
        high=max(bar.high for bar in ordered),
        low=min(bar.low for bar in ordered),
        close=ordered[-1].close,
    )


def _matches_r112_m15(
    aggregate: Vt08IndexC2R1Bar,
    row: dict[str, Any],
) -> bool:
    return (
        aggregate.open == Decimal(str(row["exit_bar_open"]))
        and aggregate.high == Decimal(str(row["exit_bar_high"]))
        and aggregate.low == Decimal(str(row["exit_bar_low"]))
        and aggregate.close == Decimal(str(row["exit_bar_close"]))
    )


def _resolve_order(
    *,
    side: DemoTradingSetupSide,
    stop: Decimal,
    target: Decimal,
    bars: tuple[Vt08IndexC2R1Bar, ...],
) -> dict[str, Any]:
    for minute_index, bar in enumerate(bars):
        gap = v2._gap_exit(
            side=side,
            bar=bar,
            stop=stop,
            target=target,
        )
        if gap is not None:
            _price, reason = gap
            return {
                "resolution": (
                    "TARGET_FIRST"
                    if reason == "target-gap"
                    else "STOP_FIRST"
                ),
                "resolution_reason": reason,
                "minute_index": minute_index,
                "minute_opened_at": bar.opened_at.astimezone(UTC).isoformat(),
            }

        stop_touch = bar.low <= stop <= bar.high
        target_touch = bar.low <= target <= bar.high
        if stop_touch and target_touch:
            return {
                "resolution": "M1_STILL_AMBIGUOUS",
                "resolution_reason": "BOTH_LEVELS_INSIDE_SAME_M1",
                "minute_index": minute_index,
                "minute_opened_at": bar.opened_at.astimezone(UTC).isoformat(),
            }
        if stop_touch:
            return {
                "resolution": "STOP_FIRST",
                "resolution_reason": "STOP_TOUCH",
                "minute_index": minute_index,
                "minute_opened_at": bar.opened_at.astimezone(UTC).isoformat(),
            }
        if target_touch:
            return {
                "resolution": "TARGET_FIRST",
                "resolution_reason": "TARGET_TOUCH",
                "minute_index": minute_index,
                "minute_opened_at": bar.opened_at.astimezone(UTC).isoformat(),
            }
    return {
        "resolution": "NO_LEVEL_TOUCH_IN_NATIVE_M1",
        "resolution_reason": "PROVIDER_SEQUENCE_CONTRADICTS_M15_TOUCH",
        "minute_index": None,
        "minute_opened_at": None,
    }


def _fetch_exact_m15_m1(
    client: SpotwareCTraderOpenApiClient,
    *,
    symbol: str,
    symbol_id: int,
    exit_at: datetime,
    request_index: int,
) -> tuple[Vt08IndexC2R1Bar, ...]:
    opened_at = exit_at.astimezone(UTC) - timedelta(minutes=15)
    native = r91._read_chunk(
        client,
        symbol=symbol,
        symbol_id=symbol_id,
        opened_at=opened_at,
        closed_at=exit_at.astimezone(UTC),
        chunk_index=request_index,
    )
    minute_bars = tuple(
        sorted(
            (r91._minute_bar(row) for row in native),
            key=lambda bar: bar.opened_at,
        )
    )
    if len(minute_bars) != 15:
        raise ValueError(
            f"R113 {symbol} {opened_at.isoformat()} "
            f"requires 15 native M1 bars, got {len(minute_bars)}"
        )
    return minute_bars


def _resolve_rows(
    client: SpotwareCTraderOpenApiClient,
    *,
    rows: list[dict[str, Any]],
    symbol_ids: dict[str, tuple[str, int]],
    request_offset: int,
) -> tuple[list[dict[str, Any]], int]:
    resolved_rows: list[dict[str, Any]] = []
    request_index = request_offset
    for row in rows:
        symbol = str(row["symbol"])
        provider_symbol, symbol_id = symbol_ids[symbol]
        exit_at = datetime.fromisoformat(str(row["exit_timestamp"])).astimezone(UTC)
        minute_bars = _fetch_exact_m15_m1(
            client,
            symbol=symbol,
            symbol_id=symbol_id,
            exit_at=exit_at,
            request_index=request_index,
        )
        request_index += 1
        aggregate = _aggregate_m1(minute_bars)
        aggregate_match = _matches_r112_m15(aggregate, row)

        if aggregate_match:
            order = _resolve_order(
                side=DemoTradingSetupSide(str(row["side"])),
                stop=Decimal(str(row["stop"])),
                target=Decimal(str(row["target_2_5r"])),
                bars=minute_bars,
            )
        else:
            order = {
                "resolution": "M1_AGGREGATE_MISMATCH_FAIL_CLOSED",
                "resolution_reason": "NATIVE_M1_DOES_NOT_REBUILD_CIBO_M15",
                "minute_index": None,
                "minute_opened_at": None,
            }

        target_delta = Decimal(str(row["target_first_upper_delta_r"]))
        applied_delta = (
            target_delta
            if order["resolution"] == "TARGET_FIRST"
            else Decimal()
        )
        resolved_rows.append(
            {
                "symbol": symbol,
                "provider_symbol": provider_symbol,
                "period": row["period"],
                "side": row["side"],
                "anchor": row["anchor"],
                "signal_timestamp": row["signal_timestamp"],
                "exit_timestamp": row["exit_timestamp"],
                "stop": row["stop"],
                "target_2_5r": row["target_2_5r"],
                "native_m1_count": len(minute_bars),
                "native_m1_aggregate": {
                    "open": str(aggregate.open),
                    "high": str(aggregate.high),
                    "low": str(aggregate.low),
                    "close": str(aggregate.close),
                },
                "cibo_m15": {
                    "open": row["exit_bar_open"],
                    "high": row["exit_bar_high"],
                    "low": row["exit_bar_low"],
                    "close": row["exit_bar_close"],
                },
                "aggregate_exact_match": aggregate_match,
                **order,
                "target_first_upper_delta_r": str(target_delta),
                "resolved_accounting_delta_r": str(applied_delta),
            }
        )
    return resolved_rows, request_index


def _window_summary(
    source: dict[str, Any],
    rows: list[dict[str, Any]],
) -> dict[str, Any]:
    counts = {
        label: sum(str(row["resolution"]) == label for row in rows)
        for label in (
            "STOP_FIRST",
            "TARGET_FIRST",
            "M1_STILL_AMBIGUOUS",
            "M1_AGGREGATE_MISMATCH_FAIL_CLOSED",
            "NO_LEVEL_TOUCH_IN_NATIVE_M1",
        )
    }
    applied_delta = sum(
        (
            Decimal(str(row["resolved_accounting_delta_r"]))
            for row in rows
        ),
        Decimal(),
    )
    primary_actual = Decimal(str(source["actual"]["primary"]["total_r"]))
    secondary_actual = Decimal(str(source["actual"]["secondary"]["total_r"]))
    return {
        "ambiguous_sample": len(rows),
        "resolution_counts": counts,
        "all_native_m1_sequences_complete": all(
            int(row["native_m1_count"]) == 15 for row in rows
        ),
        "all_native_m1_aggregates_match_cibo_m15": all(
            bool(row["aggregate_exact_match"]) for row in rows
        ),
        "resolved_accounting_delta_r": str(applied_delta),
        "canonical_primary_total_r": str(primary_actual),
        "canonical_secondary_total_r": str(secondary_actual),
        "m1_resolved_primary_total_r": str(primary_actual + applied_delta),
        "m1_resolved_secondary_total_r": str(secondary_actual + applied_delta),
        "rows": rows,
    }


def build_report(
    *,
    nas100_root: Path,
    sp500_root: Path,
    us30_root: Path,
) -> dict[str, Any]:
    roots = {
        "NAS100": nas100_root,
        "SP500": sp500_root,
        "US30": us30_root,
    }
    source = r112.build_report(
        nas100_root=nas100_root,
        sp500_root=sp500_root,
        us30_root=us30_root,
    )
    if source["decision"] != "R112_SAME_M15_AMBIGUITY_CENSUS_COMPLETE_NO_RULE_CHANGE":
        raise ValueError("R113 R112 decision drift")

    client = SpotwareCTraderOpenApiClient(
        credentials=r90._credentials(),
        request_timeout_seconds=30.0,
    )
    try:
        ready = client.connect_and_authenticate()
        if isinstance(ready, Failure):
            raise RuntimeError(
                f"R113 cTrader DEMO authentication failed: {ready.error}"
            )
        symbol_ids = {
            symbol: r90._discover_symbol(
                client,
                canonical_symbol=symbol,
            )
            for symbol in roots
        }
        cursor = 0
        five_rows, cursor = _resolve_rows(
            client,
            rows=list(source["five_year"]["ambiguous_rows"]),
            symbol_ids=symbol_ids,
            request_offset=cursor,
        )
        two_rows, cursor = _resolve_rows(
            client,
            rows=list(source["recent_two_year"]["ambiguous_rows"]),
            symbol_ids=symbol_ids,
            request_offset=cursor,
        )
        r66_rows, cursor = _resolve_rows(
            client,
            rows=list(source["r66_failed_holdout"]["ambiguous_rows"]),
            symbol_ids=symbol_ids,
            request_offset=cursor,
        )
    finally:
        client.close()

    five = _window_summary(source["five_year"], five_rows)
    two = _window_summary(source["recent_two_year"], two_rows)
    failed = _window_summary(source["r66_failed_holdout"], r66_rows)

    b2_rows = [row for row in r66_rows if str(row["period"]) == "B2"]
    if len(b2_rows) != 1:
        raise ValueError("R113 expected exactly one R66 B2 ambiguity")

    return {
        "schema": SCHEMA,
        "identity": IDENTITY,
        "source_r112": {
            "run_id": SOURCE_R112_RUN_ID,
            "artifact_id": SOURCE_R112_ARTIFACT_ID,
            "artifact_digest": SOURCE_R112_ARTIFACT_DIGEST,
        },
        "provider_contract": {
            "environment": "DEMO_ONLY",
            "period": "M1_NATIVE",
            "synthetic_m1": False,
            "interpolated_m1": False,
            "requested_only_r112_ambiguous_m15_windows": True,
            "complete_m1_per_m15_required": 15,
            "exact_m1_to_cibo_m15_ohlc_match_required": True,
        },
        "five_year": five,
        "recent_two_year": two,
        "r66_failed_holdout": failed,
        "r66_b2_resolution": b2_rows[0],
        "root_cause_conclusion": (
            "SAME_M15_PRECEDENCE_CANNOT_EXPLAIN_R66_B2"
        ),
        "decision": "R113_NATIVE_M1_ORDERING_RESOLUTION_COMPLETE_NO_RULE_CHANGE",
        "governance": {
            "research_only": True,
            "consumed_evidence_only": True,
            "fresh_holdout_claim": False,
            "read_only_provider_requests": True,
            "signal_generation_from_m1": False,
            "candidate_created": False,
            "signals_suppressed": False,
            "trade_count_changed": False,
            "target_changed": False,
            "stop_changed": False,
            "risk_allocator_changed": False,
            "anchor_14_enabled": False,
            "live_authorized": False,
            "real_capital_authorized": False,
            "production_authorized": False,
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--nas100-root", type=Path, required=True)
    parser.add_argument("--sp500-root", type=Path, required=True)
    parser.add_argument("--us30-root", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    report = build_report(
        nas100_root=args.nas100_root,
        sp500_root=args.sp500_root,
        us30_root=args.us30_root,
    )
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(
        json.dumps(report, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "identity": IDENTITY,
                "five_year": report["five_year"],
                "recent_two_year": report["recent_two_year"],
                "r66": report["r66_failed_holdout"],
                "r66_b2_resolution": report["r66_b2_resolution"],
                "root_cause_conclusion": report["root_cause_conclusion"],
                "decision": report["decision"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()

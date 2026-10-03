#!/usr/bin/env python3
"""Add causal M15 context to the Architect-2 T02 research dataset.

M15 is derived only from exact closed 3xM5 buckets. A bucket is available to a
decision only when its 15-minute close is <= the decision timestamp.
"""

from __future__ import annotations

import argparse
import bisect
import json
from collections import defaultdict
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any


def dec(value: object) -> Decimal:
    return Decimal(str(value))


def fmt(value: Decimal) -> str:
    return format(value, "f")


def parse_dt(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("timestamp must be timezone-aware")
    return parsed.astimezone(UTC)


def alignment(side: str, delta: Decimal) -> str:
    if delta == 0:
        return "flat"
    same = (side == "long" and delta > 0) or (side == "short" and delta < 0)
    return "same" if same else "opposed"


def safe_ratio(numerator: Decimal, denominator: Decimal) -> Decimal:
    return numerator / denominator if denominator > 0 else Decimal(0)


def bucket_start(opened_at: datetime) -> datetime:
    minute = opened_at.minute - opened_at.minute % 15
    return opened_at.replace(minute=minute, second=0, microsecond=0)


def load_m5(root: Path, symbol: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for path in sorted(root.rglob("RAW_M5_LEDGER/*.jsonl")):
        for line in path.read_text().splitlines():
            if not line.strip():
                continue
            raw = json.loads(line)
            if raw.get("canonical_symbol") != symbol:
                raise RuntimeError(f"{symbol}: M5 source symbol drift")
            opened = parse_dt(str(raw["opened_at"]))
            rows.append(
                {
                    "opened": opened,
                    "open": dec(raw["open_relative"]),
                    "high": dec(raw["high_relative"]),
                    "low": dec(raw["low_relative"]),
                    "close": dec(raw["close_relative"]),
                }
            )
    rows.sort(key=lambda row: row["opened"])
    if not rows:
        raise RuntimeError(f"{symbol}: empty retained M5 source")
    if len({row["opened"] for row in rows}) != len(rows):
        raise RuntimeError(f"{symbol}: duplicate M5 timestamps")
    return rows


def aggregate_m15(m5: list[dict[str, Any]]) -> list[dict[str, Any]]:
    groups: dict[datetime, list[dict[str, Any]]] = defaultdict(list)
    for row in m5:
        groups[bucket_start(row["opened"])].append(row)

    out: list[dict[str, Any]] = []
    for start in sorted(groups):
        rows = sorted(groups[start], key=lambda row: row["opened"])
        expected = [start + timedelta(minutes=offset) for offset in (0, 5, 10)]
        if len(rows) != 3 or [row["opened"] for row in rows] != expected:
            continue
        out.append(
            {
                "opened": start,
                "closed": start + timedelta(minutes=15),
                "open": rows[0]["open"],
                "high": max(row["high"] for row in rows),
                "low": min(row["low"] for row in rows),
                "close": rows[-1]["close"],
            }
        )
    if not out:
        raise RuntimeError("no complete M15 candles could be derived")
    return out


def m15_features(
    candles: list[dict[str, Any]],
    closed: list[datetime],
    *,
    decision: datetime,
    side: str,
) -> dict[str, str] | None:
    end = bisect.bisect_right(closed, decision)
    if end < 16:
        return None
    history = candles[:end]
    last = history[-1]
    w16 = history[-16:]
    w4 = history[-4:]
    w2 = history[-2:]

    last_range = last["high"] - last["low"]
    last_delta = last["close"] - last["open"]
    avg_range = sum(
        (row["high"] - row["low"] for row in w16),
        Decimal(0),
    ) / Decimal(len(w16))
    ratio = safe_ratio(last_range, avg_range)
    volatility = "low" if ratio < Decimal("0.75") else (
        "high" if ratio > Decimal("1.50") else "normal"
    )
    ret2 = last["close"] - w2[0]["open"]
    ret4 = last["close"] - w4[0]["open"]
    window_high = max(row["high"] for row in w16)
    window_low = min(row["low"] for row in w16)
    window_range = window_high - window_low

    return {
        "reg_m15_last_body_alignment": alignment(side, last_delta),
        "reg_m15_displacement_alignment": alignment(side, ret2),
        "reg_m15_volatility_state": volatility,
        "m15_last_body_efficiency": fmt(
            safe_ratio(abs(last_delta), last_range)
        ),
        "m15_last_range_to_16_avg": fmt(ratio),
        "m15_return_2_in_16_avg_range": fmt(
            safe_ratio(ret2, avg_range)
        ),
        "m15_return_4_in_16_avg_range": fmt(
            safe_ratio(ret4, avg_range)
        ),
        "m15_position_in_16_range": fmt(
            safe_ratio(last["close"] - window_low, window_range)
        ),
        "m15_closed_bar_count_predecision": str(end),
    }


def parse_roots(values: list[str]) -> dict[str, Path]:
    out: dict[str, Path] = {}
    for value in values:
        symbol, sep, raw = value.partition("=")
        if not sep or not symbol or not raw:
            raise ValueError("M5 source root must be SYMBOL=PATH")
        out[symbol] = Path(raw)
    return out


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--m5-source-root", action="append", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    roots = parse_roots(args.m5_source_root)
    expected = {"AUDJPY", "EURUSD", "GBPJPY", "GBPUSD", "NAS100", "XAUUSD"}
    if set(roots) != expected:
        raise RuntimeError("exact six research M5 symbol roots are required")

    by_symbol: dict[str, tuple[list[dict[str, Any]], list[datetime]]] = {}
    for symbol, root in roots.items():
        candles = aggregate_m15(load_m5(root, symbol))
        by_symbol[symbol] = (
            candles,
            [row["closed"] for row in candles],
        )

    wrapped_rows = [
        json.loads(line)
        for line in args.input.read_text().splitlines()
        if line.strip()
    ]
    enriched = 0
    selected_enriched = 0
    for wrapped in wrapped_rows:
        x = wrapped["X_PREDECISION"]
        symbol = str(x["symbol_measurement_only"])
        if symbol not in by_symbol:
            continue
        candles, closed = by_symbol[symbol]
        features = m15_features(
            candles,
            closed,
            decision=parse_dt(str(x["decision_timestamp"])),
            side=str(x["side"]),
        )
        if features is None:
            continue
        x["context"].update(features)
        enriched += 1
        if x["core_selected_before_t02"]:
            selected_enriched += 1

    if selected_enriched != 145:
        raise RuntimeError(
            "expected M15 causal coverage on all 145 Core-selected research rows, "
            f"got {selected_enriched}"
        )

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        "".join(json.dumps(row, sort_keys=True) + "\n" for row in wrapped_rows)
    )
    print(
        json.dumps(
            {
                "m15_rows_enriched": enriched,
                "m15_core_selected_rows_enriched": selected_enriched,
                "source_symbols": sorted(roots),
                "partial_m15_candles_used": False,
                "outcome_fields_used": False,
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

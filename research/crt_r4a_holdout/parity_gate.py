"""Fail-closed Pine R4-A ↔ causal replay event parity comparison.

Requires independently exported original Pine detector event tape on IDENTICAL
source M5 (ticker/provider/H4 clock) and replay event tape. Does not attempt
to manufacture Pine events from 400-bar snapshots. No trading/PnL authority.
"""
from __future__ import annotations

import argparse
import csv
import json
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

from research.crt_r4a_holdout.runner import MODELS, SYMBOLS

TIMES = ("c1_at", "sweep_at", "ratified_at", "mss_at", "available_at")
PRICES = ("c1_high", "c1_low", "sweep_high", "sweep_low", "mss_pivot")
BASE = ("event_id", "symbol", "model", "side")
ALL = BASE + TIMES + PRICES


def utc(t: str) -> datetime:
    instant = datetime.fromisoformat(t.replace("Z", "+00:00"))
    if instant.tzinfo is None:
        raise ValueError("offset required on every event timestamp")
    return instant.astimezone(UTC)


def _normalize(path: Path) -> dict[str, dict[str, Any]]:
    with path.open(newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        if reader.fieldnames is None or not set(ALL) <= set(reader.fieldnames):
            raise ValueError("event tape missing required columns")
        rows: dict[str, dict[str, Any]] = {}
        for raw in reader:
            if any(not raw.get(key) for key in ALL):
                raise ValueError("missing individual event field")
            event_id = raw["event_id"]
            if event_id in rows:
                raise ValueError(f"duplicated event ID: {event_id}")
            if raw["symbol"] not in SYMBOLS or raw["model"] not in MODELS:
                raise ValueError("invalid universe/model")
            if raw["side"] not in ("LONG", "SHORT"):
                raise ValueError("invalid trade direction")
            stamp = {k: utc(raw[k]) for k in TIMES}
            if not (
                stamp["c1_at"] < stamp["sweep_at"] <= stamp["ratified_at"]
                <= stamp["available_at"]
                and stamp["sweep_at"] < stamp["mss_at"] <= stamp["available_at"]
                and stamp["available_at"] == max(
                    stamp["ratified_at"], stamp["mss_at"]
                )
            ):
                raise ValueError(f"future-looking or inconsistent event: {event_id}")
            if raw["model"] == "B_TRUE3C_MSS5" and (
                stamp["mss_at"] > stamp["ratified_at"]
            ):
                raise ValueError("TRUE3C MSS5 occurs after H4 C3 ratification")
            try:
                prices = {k: Decimal(raw[k]) for k in PRICES}
            except InvalidOperation as exc:
                raise ValueError("invalid numeric price") from exc
            if any(not x.is_finite() or x <= 0 for x in prices.values()):
                raise ValueError("prices must be positive and finite")
            if not (
                prices["c1_low"] < prices["c1_high"]
                and prices["sweep_low"] <= prices["sweep_high"]
            ):
                raise ValueError("invalid H4 geometry")
            values: dict[str, Any] = {
                k: raw[k] for k in BASE
            }
            values.update(stamp)
            values.update(prices)
            rows[event_id] = values
    return rows


def compare(pine_path: Path, replay_path: Path) -> dict[str, Any]:
    pine = _normalize(pine_path)
    replay = _normalize(replay_path)
    a, b = set(pine), set(replay)
    only_pine = sorted(a - b)
    only_replay = sorted(b - a)
    discrepancies: list[dict[str, str]] = []
    for key in sorted(a & b):
        for field in BASE[1:] + TIMES + PRICES:
            if pine[key][field] != replay[key][field]:
                discrepancies.append({
                    "event_id": key,
                    "field": field,
                    "pine": str(pine[key][field]),
                    "replay": str(replay[key][field]),
                })
    if not pine or not replay:
        status = "BLOCKED_EMPTY_EVENT_TAPE"
    elif only_pine or only_replay or discrepancies:
        status = "FAIL_PARITY"
    else:
        status = "PASS_EVENT_PARITY_ONLY"
    return {
        "status": status,
        "pine_count": len(pine),
        "replay_count": len(replay),
        "missing_in_replay_count": len(only_pine),
        "extra_in_replay_count": len(only_replay),
        "field_mismatch_count": len(discrepancies),
        "missing_in_replay_examples": only_pine[:15],
        "extra_in_replay_examples": only_replay[:15],
        "field_mismatch_examples": discrepancies[:25],
        "scope": "SAME_FEED_SAME_PERIOD_EVENTS_ONLY_NO_ECONOMIC_CERTIFICATION",
        "pine_reference_blob": "693e3f49719e86e2ea0702f7b355af33bd0c4c7c",
        "market_data_parity_independently_proven": False,
        "holdout_virginity_proven": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pine", type=Path, required=True)
    parser.add_argument("--replay", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    output = compare(args.pine, args.replay)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(output, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "status": output["status"],
        "pine_count": output["pine_count"],
        "replay_count": output["replay_count"],
        "field_mismatch_count": output["field_mismatch_count"],
    }))
    if output["status"] != "PASS_EVENT_PARITY_ONLY":
        raise SystemExit(2)


if __name__ == "__main__":
    main()

"""Audit R4-A causal M5/M15 swing primitives on genuine archived M5.

Inputs are existing SHA-verified GitHub Actions sources; emits counts ONLY.
Does NOT replicate full Pine f_engine(), prove parity or authorize trades.
2024–25 was previously explored; this is NOT a new virgin holdout.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

from scripts.crt_radar_archived_m5_prescreen import native_to_bar

from research.crt_r4a_holdout.native_archive_2y_probe import inspect
from research.crt_r4a_holdout.pine_swing_primitives import (
    Bar,
    M5Swings,
    M15Swings,
)


def analyze_archive(root: Path, symbol: str, cohort: str) -> dict[str, object]:
    provenance = inspect(root, symbol, cohort)
    found = list(root.rglob("symbol-consumption-manifest.json"))
    if len(found) != 1:
        raise ValueError("expected exactly one original provider manifest")
    manifest = json.loads(found[0].read_text(encoding="utf-8"))
    provider = manifest["provider_symbol"]
    symbol_id = manifest["provider_symbol_id"]
    m5 = M5Swings(left=2, right=2)
    m15 = M15Swings(left=2, right=2, source_phase_min=0)
    counts: Counter[str] = Counter()
    seen_high_m5: set[object] = set()
    seen_low_m5: set[object] = set()
    seen_high_m15: set[object] = set()
    seen_low_m15: set[object] = set()
    years = (2024, 2025)
    for year in years:
        source_path = found[0].parent / "RAW_M5_LEDGER" / f"{year}.jsonl"
        with source_path.open(encoding="utf-8") as source:
            for line in source:
                if not line.strip():
                    continue
                raw = json.loads(line)
                candle = native_to_bar(raw, symbol, provider, symbol_id)
                b = Bar(
                    candle.opened_at,
                    float(candle.high), float(candle.low), float(candle.close)
                )
                before, continuous = m5.before_closed_bar(b)
                if not continuous and counts["m5_seen"] > 0:
                    counts["m5_segment_breaks"] += 1
                if before.high is not None and before.high.confirmed_at > b.opened_at:
                    raise ValueError("M5 swing lookahead detected")
                if before.low is not None and before.low.confirmed_at > b.opened_at:
                    raise ValueError("M5 swing lookahead detected")
                for kind, seen in (
                    (before.high, seen_high_m5),
                    (before.low, seen_low_m5)
                ):
                    if kind is not None and kind.pivot_at not in seen:
                        seen.add(kind.pivot_at)
                        counts[f"m5_pivot_{kind.kind.lower()}"] += 1
                m5.finish_bar(b)
                complete = m15.on_closed_m5(b)
                if complete is not None:
                    counts["m15_closed_three_m5"] += 1
                    if complete.previous_continuous:
                        counts["m15_previous_contiguous"] += 1
                    if complete.closed_at > b.opened_at:
                        raise ValueError("closed M15 exposed before final confirmation")
                swing = m15.snapshot()
                if swing:
                    for kind, seen in (
                        (swing.high, seen_high_m15),
                        (swing.low, seen_low_m15)
                    ):
                        if kind is not None and kind.pivot_at not in seen:
                            if kind.confirmed_at > b.opened_at:
                                raise ValueError("M15 swing lookahead detected")
                            seen.add(kind.pivot_at)
                            counts[f"m15_pivot_{kind.kind.lower()}"] += 1
                counts["m5_seen"] += 1
    if counts["m5_seen"] != provenance["total_m5"]:
        raise ValueError("native source count changed during pivot audit")
    if counts["m15_closed_three_m5"] <= 0:
        raise ValueError("no confirmed three-M5 M15 source candles")
    return {
        "status": "REAL_M5_CAUSAL_PIVOTS_QA_NOT_PINE_PARITY",
        "symbol": symbol,
        "provider_cohort": cohort,
        "years": "2024_2025_PREVIOUSLY_CONSUMED",
        "counts": dict(counts),
        "original_source_sha256_2024_2025_verified": True,
        "pine_exact_f_engine_ported": False,
        "pine_event_parity_certified": False,
        "trader_entries_executed": False,
        "holdout_unseen": False,
        "risk_or_profit_claim": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--symbol", required=True)
    parser.add_argument("--cohort", required=True)
    args = parser.parse_args()
    result = analyze_archive(args.root, args.symbol, args.cohort)
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()

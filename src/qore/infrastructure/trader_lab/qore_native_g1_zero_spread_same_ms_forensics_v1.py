"""G1 source-only study: same-millisecond vs aged BID=ASK as-of snapshots.

This descriptive post-source forensic is not a strategy, fill, commission, cost
or NET model and is not allowed to change E2-E3 231 strategy hypotheses.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any

from qore.infrastructure.trader_lab import qore_native_g1_remaining29_independent_qa_v1 as origin

IDENTITY = "QORE_NATIVE_G1_29_REAL_SOURCE_ZERO_SPREAD_SIMULTANEITY_V1"
BINS = ("same_millisecond", "lag_1_100ms", "lag_101_500ms",
        "lag_501_1000ms", "lag_1001_5000ms")
THRESHOLDS_MS = (0, 100, 500, 1000, 5000)


def classify_zero_age(age: int) -> str:
    if type(age) is not int or not 0 <= age <= 5000:
        raise ValueError("G1_ZERO_AGE_OUTSIDE_OR_INVALID")
    if age == 0:
        return BINS[0]
    if age <= 100:
        return BINS[1]
    if age <= 500:
        return BINS[2]
    if age <= 1000:
        return BINS[3]
    return BINS[4]


def analyze_market(
    bid: list[tuple[int, int]], ask: list[tuple[int, int]],
) -> dict[str, Any]:
    if not bid or not ask:
        raise ValueError("G1_BOTH_SIDES_REQUIRED_FOR_FORENSIC")
    ts = sorted({x[0] for x in bid} | {x[0] for x in ask})
    bi = ai = 0
    b: tuple[int, int] | None = None
    a: tuple[int, int] | None = None
    zero: Counter[str] = Counter()
    positive = crossed = missing = stale = 0
    for time in ts:
        while bi < len(bid) and bid[bi][0] <= time:
            b = bid[bi]
            bi += 1
        while ai < len(ask) and ask[ai][0] <= time:
            a = ask[ai]
            ai += 1
        if b is None or a is None:
            missing += 1
            continue
        bid_age = time - b[0]
        ask_age = time - a[0]
        if min(bid_age, ask_age) < 0:
            raise ValueError("G1_LOOKAHEAD_CAUSAL_BOUNDARY_BROKEN")
        age = max(bid_age, ask_age)
        if age > 5000:
            stale += 1
        elif a[1] < b[1]:
            crossed += 1
        elif a[1] > b[1]:
            positive += 1
        else:
            zero[classify_zero_age(age)] += 1
    bucketed = {k: zero[k] for k in BINS}
    zero_total = sum(bucketed.values())
    if zero_total + positive + crossed + missing + stale != len(ts):
        raise ValueError("G1_SOURCE_ZERO_SPREAD_PARTITION_MISMATCH")
    return {
        "source_asof_instants": len(ts), "positive": positive,
        "crossed": crossed, "missing": missing, "stale": stale,
        "zero_total": zero_total, "zero_age_bins": bucketed,
        "zero_age_threshold_cumulative": {
            str(t): sum(v for k, v in bucketed.items() if (
                BINS.index(k) <= (0 if t == 0 else 1 if t == 100 else 2 if t == 500
                                   else 3 if t == 1000 else 4)
            )) for t in THRESHOLDS_MS
        },
        "source_only_not_executable_spread": True,
    }


def inspect_source(root: Path) -> dict[str, Any]:
    """Do not trust this forensic before the independent 29-source auditor passes."""
    verified = origin.audit(root)
    if verified["status"] != "REAL_29_SOURCE_SHA_ASOF_PASS_NO_NET":
        raise ValueError("G1_ORIGINAL_REAL_SOURCE_SHA_INVALID")
    markets = []
    aggregate: Counter[str] = Counter()
    aggregate_buckets: Counter[str] = Counter()
    for canonical in origin.FROZEN_TARGETS:
        folder = root / canonical
        record = json.loads((folder / "SOURCE-MANIFEST-NOT-NET.json").read_bytes())
        market_counts: Counter[str] = Counter()
        buckets: Counter[str] = Counter()
        for i, (window, frozen) in enumerate(
            zip(record["windows"], origin.EXPECTED_WINDOWS, strict=True), 1
        ):
            start = int(datetime.fromisoformat(frozen[0]).timestamp() * 1000)
            stop = int(datetime.fromisoformat(frozen[1]).timestamp() * 1000)
            bid, _ = origin.audit_side(folder, canonical, i, "BID",
                                       window["by_side"]["BID"], start, stop)
            ask, _ = origin.audit_side(folder, canonical, i, "ASK",
                                       window["by_side"]["ASK"], start, stop)
            signal = analyze_market(bid, ask)
            for metric in ("source_asof_instants", "positive", "crossed",
                           "missing", "stale", "zero_total"):
                market_counts[metric] += signal[metric]
            buckets.update(signal["zero_age_bins"])
        aggregate.update(market_counts)
        aggregate_buckets.update(buckets)
        markets.append({
            "canonical_symbol": canonical,
            "zero_snapshots": market_counts["zero_total"],
            "zero_age_bins": {b: buckets[b] for b in BINS},
            "positive_snapshots": market_counts["positive"],
            "stale_snapshots": market_counts["stale"],
            "missing_snapshots": market_counts["missing"],
            "crossed_snapshots": market_counts["crossed"],
        })
    for k, metric in (
        ("zero_spread", "zero_total"), ("positive_spread", "positive"),
        ("stale_side", "stale"), ("missing_side", "missing"),
        ("crossed_spread", "crossed")
    ):
        if aggregate[metric] != verified["asof_source_quality_totals"][k]:
            raise ValueError("G1_FORENSIC_AND_INDEPENDENT_QA_COUNTERS_DIFFER")
    return {
        "identity": IDENTITY,
        "status": "EXPLORATORY_ZERO_SOURCE_SIMULTANEITY_AUDITED_NO_NET",
        "source_run": origin.ORIGINAL_RUN,
        "source_artifact_id": origin.ORIGINAL_ARTIFACT_ID,
        "parent_qa_agreement_exact": True,
        "markets_verified": len(markets),
        "zero_total": aggregate["zero_total"],
        "zero_age_bins": {k: aggregate_buckets[k] for k in BINS},
        "zero_thresholds_cumulative_ms": {
            str(t): sum(aggregate_buckets[k] for k in BINS[:(
                1 if t == 0 else 2 if t == 100 else 3 if t == 500
                else 4 if t == 1000 else 5
            )]) for t in THRESHOLDS_MS
        },
        "asof_spread_zero_is_not_free_execution_cost": True,
        "historical_broker_zero_spread_semantics_verified": False,
        "raw_source_protobuf_redecoded_independently": False,
        "historical_NET_authorized": False,
        "certified_traders": 0,
        "per_market": markets,
    }


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("exact_original_source_dir", type=Path)
    p.add_argument("outdir", type=Path)
    args = p.parse_args()
    result = inspect_source(args.exact_original_source_dir)
    args.outdir.mkdir(parents=True, exist_ok=True)
    file = args.outdir / "G1_29_SOURCE_ZERO_SIMULTANEITY_NOT_NET.json"
    file.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (args.outdir / "SHA256SUMS.txt").write_text(
        origin.sha(file.read_bytes()) + "  " + file.name + "\n"
    )
    print(json.dumps({
        "status": result["status"], "zero_total": result["zero_total"],
        "zero_age_bins": result["zero_age_bins"],
        "historical_NET_authorized": False, "certified_traders": 0,
    }, sort_keys=True))


if __name__ == "__main__":
    main()

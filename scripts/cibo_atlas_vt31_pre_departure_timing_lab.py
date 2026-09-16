"""Timing statistics for CIBO Atlas VT-31 pre-departure structures.

Consumes only the immutable/consumed Pre-Departure Structure Lab output. It
measures *when* price reaches the last reaction structure before the move toward
the opposite 09:00 boundary and how long the subsequent expansion takes.

Timing is descriptive research only. It cannot select a candidate, change a
trader, or open fresh evidence.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Any, Callable, cast
from zoneinfo import ZoneInfo

NY = ZoneInfo("America/New_York")
SCHEMA = "qore.cibo_atlas.vt31.pre_departure_timing_lab.v1"
SOURCE_SCHEMA = "qore.cibo_atlas.vt31.pre_departure_structure_lab.v1"
MARKETS = ("NAS100", "SP500", "US30")


def fraction(n: int, d: int) -> str | None:
    return None if d == 0 else format(Decimal(n) / Decimal(d), "f")


def quantile(values: list[int], p: Decimal) -> Decimal | None:
    if not values:
        return None
    xs = sorted(values)
    if len(xs) == 1:
        return Decimal(xs[0])
    pos = p * Decimal(len(xs) - 1)
    lo = int(pos)
    hi = min(lo + 1, len(xs) - 1)
    frac = pos - Decimal(lo)
    return Decimal(xs[lo]) * (Decimal(1) - frac) + Decimal(xs[hi]) * frac


def minute_of_day(value: str) -> int:
    dt = datetime.fromisoformat(value).astimezone(NY)
    return dt.hour * 60 + dt.minute


def hhmm(minute: Decimal | None) -> str | None:
    if minute is None:
        return None
    rounded = int(minute.to_integral_value(rounding="ROUND_HALF_UP"))
    rounded = max(0, min(23 * 60 + 59, rounded))
    return f"{rounded // 60:02d}:{rounded % 60:02d}"


def bucket(minute: int, width: int) -> str:
    start = (minute // width) * width
    end = start + width - 1
    return f"{start // 60:02d}:{start % 60:02d}-{end // 60:02d}:{end % 60:02d}"


def elapsed_minutes(start: str, end: str) -> int:
    left = datetime.fromisoformat(start)
    right = datetime.fromisoformat(end)
    seconds = (right - left).total_seconds()
    if seconds < 0:
        raise ValueError("objective timestamp precedes departure pivot")
    return int(seconds // 60)


def top_rates(counter: Counter[str], denominator: int) -> list[dict[str, Any]]:
    return [
        {"bucket": key, "count": count, "rate": fraction(count, denominator)}
        for key, count in sorted(counter.items(), key=lambda item: (-item[1], item[0]))
    ]


def summarize(rows: list[dict[str, Any]]) -> dict[str, Any]:
    if not rows:
        return {"n": 0}
    pivots = [minute_of_day(str(row["pivot_at"])) for row in rows]
    objectives = [minute_of_day(str(row["objective_at"])) for row in rows]
    elapsed = [elapsed_minutes(str(row["pivot_at"]), str(row["objective_at"])) for row in rows]
    p25 = quantile(pivots, Decimal("0.25"))
    p50 = quantile(pivots, Decimal("0.50"))
    p75 = quantile(pivots, Decimal("0.75"))
    e25 = quantile(elapsed, Decimal("0.25"))
    e50 = quantile(elapsed, Decimal("0.50"))
    e75 = quantile(elapsed, Decimal("0.75"))
    return {
        "n": len(rows),
        "pivot_time_ny_p25": hhmm(p25),
        "pivot_time_ny_p50": hhmm(p50),
        "pivot_time_ny_p75": hhmm(p75),
        "objective_time_ny_p50": hhmm(quantile(objectives, Decimal("0.50"))),
        "pivot_to_objective_minutes_p25": None if e25 is None else format(e25, "f"),
        "pivot_to_objective_minutes_p50": None if e50 is None else format(e50, "f"),
        "pivot_to_objective_minutes_p75": None if e75 is None else format(e75, "f"),
        "pivot_hour_counts": dict(sorted(Counter(f"{m // 60:02d}:00" for m in pivots).items())),
        "pivot_30m_distribution": top_rates(Counter(bucket(m, 30) for m in pivots), len(rows)),
        "pivot_15m_distribution": top_rates(Counter(bucket(m, 15) for m in pivots), len(rows)),
        "pivot_5m_distribution": top_rates(Counter(bucket(m, 5) for m in pivots), len(rows)),
    }


def grouped(
    rows: list[dict[str, Any]], key_fn: Callable[[dict[str, Any]], str]
) -> dict[str, dict[str, Any]]:
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        groups[key_fn(row)].append(row)
    return {key: summarize(value) for key, value in sorted(groups.items())}


def build(source_path: Path, output_path: Path) -> dict[str, Any]:
    source = cast(dict[str, Any], json.loads(source_path.read_text(encoding="utf-8")))
    if source.get("schema") != SOURCE_SCHEMA:
        raise ValueError("timing lab requires pre-departure structure lab v1")
    if source.get("research_only") is not True or source.get("opens_new_holdout") is not False:
        raise ValueError("source governance guard failed")
    market_rows = cast(list[dict[str, Any]], source.get("market_day_rows"))
    demonstrated = cast(list[dict[str, Any]], source.get("demonstrated_root_rows"))
    if not isinstance(market_rows, list) or not market_rows:
        raise ValueError("missing market-day pre-departure rows")
    if not isinstance(demonstrated, list) or len(demonstrated) != 163:
        raise ValueError("expected exactly 163 demonstrated roots")
    required = {"market", "side", "pivot_at", "objective_at", "structure_signature"}
    for row in market_rows + demonstrated:
        if not required <= set(row):
            raise ValueError("pre-departure timing row missing required fields")

    by_market = {
        market: summarize([row for row in market_rows if row["market"] == market])
        for market in MARKETS
    }
    demonstrated_by_market = {
        market: summarize([row for row in demonstrated if row["market"] == market])
        for market in MARKETS
    }
    market_structure_timing = grouped(
        market_rows,
        lambda row: f"{row['market']}|{row['structure_signature']}",
    )
    demonstrated_structure_timing = grouped(
        demonstrated,
        lambda row: f"{row['market']}|{row['structure_signature']}",
    )
    demonstrated_family_timing: dict[str, dict[str, Any]] = {}
    family_groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in demonstrated:
        families = cast(list[str], row.get("source_families_touched", []))
        if not families:
            family_groups[f"{row['market']}|none-recognized"].append(row)
        for family in families:
            family_groups[f"{row['market']}|{family}"].append(row)
    demonstrated_family_timing = {
        key: summarize(value) for key, value in sorted(family_groups.items())
    }

    payload: dict[str, Any] = {
        "schema": SCHEMA,
        "research_only": True,
        "selection_prohibited": True,
        "opens_new_holdout": False,
        "candidate_status": "NO_R9_NOT_CERTIFIED",
        "live_authorized": False,
        "production_authorized": False,
        "timezone": "America/New_York",
        "market_day_count": len(market_rows),
        "demonstrated_stop_root_count": len(demonstrated),
        "market_baseline_timing": summarize(market_rows),
        "market_baseline_by_market": by_market,
        "demonstrated_stop_timing": summarize(demonstrated),
        "demonstrated_stop_by_market": demonstrated_by_market,
        "demonstrated_stop_by_side": grouped(demonstrated, lambda row: str(row["side"])),
        "demonstrated_stop_by_terminal_family": grouped(
            demonstrated, lambda row: str(row.get("terminal_family", "unknown"))
        ),
        "market_structure_timing": market_structure_timing,
        "demonstrated_structure_timing": demonstrated_structure_timing,
        "demonstrated_family_timing": demonstrated_family_timing,
        "timing_contract": {
            "arrival": "opening minute of last unbroken reaction pivot before source objective",
            "timezone": "America/New_York DST-aware",
            "buckets": ["hour", "30m", "15m", "5m"],
            "expansion_latency": "minutes from pivot open to first opposite-09:00-boundary hit",
            "post_outcome_use": "diagnostic-only",
        },
        "interpretation_constraints": [
            "timing concentrations are descriptive and cannot become cutoffs without causal validation",
            "5m/15m/30m buckets are reporting bins, not optimized trading windows",
            "structure and time must be evaluated jointly per market before specialist repair",
            "no fresh holdout was opened",
        ],
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    return payload


def self_test() -> None:
    assert bucket(10 * 60 + 7, 5) == "10:05-10:09"
    assert bucket(10 * 60 + 29, 15) == "10:15-10:29"
    assert hhmm(Decimal("607")) == "10:07"
    print("CIBO Atlas VT31 pre-departure timing lab self-test PASS")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--source", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.self_test:
        self_test()
        return
    if args.source is None or args.output is None:
        parser.error("source and output are required")
    payload = build(args.source, args.output)
    print(
        json.dumps(
            {
                "market_days": payload["market_day_count"],
                "demonstrated_roots": payload["demonstrated_stop_root_count"],
                "demonstrated_by_market": payload["demonstrated_stop_by_market"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()

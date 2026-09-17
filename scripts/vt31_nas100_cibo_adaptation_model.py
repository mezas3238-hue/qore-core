"""Build the NAS100 VT31 / Silver Bullet CIBO adaptation research model.

Consumes only the already-consumed CIBO Atlas Eight-Ledger bundle. The output
is a pre-holdout research specification: it describes timing, entry, stop,
target and lifecycle families that must be evaluated on consumed evidence and
leakage-free WFO before any fresh holdout is opened.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

NY = ZoneInfo("America/New_York")
MARKET = "NAS100"
SCHEMA = "qore.vt31.nas100.cibo_adaptation_model.v1"
EXPECTED_BUNDLE_SCHEMA = "qore.cibo_atlas.vt31.eight_ledger_bundle.v1"


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


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
    part = pos - Decimal(lo)
    return Decimal(xs[lo]) * (Decimal(1) - part) + Decimal(xs[hi]) * part


def hhmm(value: Decimal | None) -> str | None:
    if value is None:
        return None
    minute = int(value.to_integral_value(rounding="ROUND_HALF_UP"))
    return f"{minute // 60:02d}:{minute % 60:02d}"


def local_minute(value: str) -> int:
    dt = datetime.fromisoformat(value).astimezone(NY)
    return dt.hour * 60 + dt.minute


def bucket_15(value: str) -> str:
    m = local_minute(value)
    return f"{m // 60:02d}:{((m % 60) // 15) * 15:02d}"


def summarize_departures(rows: list[dict[str, Any]]) -> dict[str, Any]:
    minutes = [local_minute(str(row["departure_at"])) for row in rows]
    within_source_hour = [m for m in minutes if 600 <= m < 660]
    late_source_hour = [m for m in minutes if 630 <= m < 660]
    structures = Counter(str(row.get("last_structure_before_departure")) for row in rows)
    latencies = [int(row["minutes_departure_to_objective"]) for row in rows]
    return {
        "n": len(rows),
        "departure_time_ny_p25": hhmm(quantile(minutes, Decimal("0.25"))),
        "departure_time_ny_p50": hhmm(quantile(minutes, Decimal("0.50"))),
        "departure_time_ny_p75": hhmm(quantile(minutes, Decimal("0.75"))),
        "departure_10_00_10_59_count": len(within_source_hour),
        "departure_10_30_10_59_count": len(late_source_hour),
        "late_half_share_of_source_hour_departures": fraction(len(late_source_hour), len(within_source_hour)),
        "last_structure_counts": dict(sorted(structures.items())),
        "departure_to_objective_minutes_p25": None if not latencies else format(quantile(latencies, Decimal("0.25")), "f"),
        "departure_to_objective_minutes_p50": None if not latencies else format(quantile(latencies, Decimal("0.50")), "f"),
        "departure_to_objective_minutes_p75": None if not latencies else format(quantile(latencies, Decimal("0.75")), "f"),
    }


def build(ledger_dir: Path) -> dict[str, Any]:
    summary = json.loads((ledger_dir / "CIBO_ATLAS_VT31_EIGHT_LEDGER_SUMMARY.json").read_text(encoding="utf-8"))
    if summary.get("schema") != EXPECTED_BUNDLE_SCHEMA:
        raise ValueError("unexpected CIBO Eight-Ledger schema")
    if summary.get("research_only") is not True or summary.get("opens_new_holdout") is not False:
        raise ValueError("CIBO bundle governance guard failed")

    departures = [
        row for row in read_jsonl(ledger_dir / "DEPARTURE_TIMING_LEDGER.jsonl") if row.get("market") == MARKET
    ]
    trader = [
        row for row in read_jsonl(ledger_dir / "TRADER_MARKET_SYNC_LEDGER.jsonl") if row.get("market") == MARKET
    ]
    targets = [
        row for row in read_jsonl(ledger_dir / "TARGET_DESTINATION_LEDGER.jsonl") if row.get("market") == MARKET
    ]
    if len(departures) != 547 or len(trader) != 208 or len(targets) != 1591:
        raise ValueError("unexpected NAS100 consumed-evidence row counts")

    breach_bins = Counter(bucket_15(str(row["first_breach_at"])) for row in departures)
    signal_minutes = [local_minute(str(row["signal_at"])) for row in trader]
    linked = [row for row in trader if isinstance(row.get("minutes_signal_to_departure"), int)]
    signal_to_departure = [int(row["minutes_signal_to_departure"]) for row in linked]

    stop_mismatch: dict[str, dict[str, Any]] = {}
    for family in ("initial_stop", "protected_stop"):
        rows = [row for row in trader if row.get("terminal_family") == family]
        mismatches = sum(bool(row.get("trader_stopped_before_eventual_source_objective")) for row in rows)
        stop_mismatch[family] = {
            "n": len(rows),
            "later_source_objective_count": mismatches,
            "later_source_objective_rate": fraction(mismatches, len(rows)),
        }

    target_hits = [row for row in targets if bool(row.get("opposite_boundary_hit_by_16"))]
    extension_rates: dict[str, Any] = {}
    for level in ("0.25", "0.5", "1", "1.5", "2"):
        count = sum(bool(row.get("post_boundary_ladder", {}).get(level)) for row in target_hits)
        extension_rates[level] = {"count": count, "rate_given_boundary_hit": fraction(count, len(target_hits))}

    partition_timing = {
        partition: summarize_departures([row for row in departures if row.get("partition") == partition])
        for partition in sorted({str(row.get("partition")) for row in departures})
    }

    result: dict[str, Any] = {
        "schema": SCHEMA,
        "market": MARKET,
        "research_only": True,
        "selection_prohibited": True,
        "opens_new_holdout": False,
        "fresh_holdout_consumed": False,
        "live_authorized": False,
        "production_authorized": False,
        "evidence_binding": {
            "bundle_schema": EXPECTED_BUNDLE_SCHEMA,
            "bundle_git_sha": (ledger_dir / "git-sha.txt").read_text(encoding="utf-8").strip(),
            "terminal_root_count": summary["terminal_root_count"],
            "nas100_market_days": summary["daily_behavior"][MARKET]["n"],
        },
        "timing_findings": {
            "completed_reversal_episodes": summarize_departures(departures),
            "first_breach_15m_counts": dict(sorted(breach_bins.items())),
            "trader_signal_time_ny_p25": hhmm(quantile(signal_minutes, Decimal("0.25"))),
            "trader_signal_time_ny_p50": hhmm(quantile(signal_minutes, Decimal("0.50"))),
            "trader_signal_time_ny_p75": hhmm(quantile(signal_minutes, Decimal("0.75"))),
            "linked_signal_to_departure_n": len(linked),
            "signal_before_final_departure_count": sum(
                row.get("signal_vs_departure") == "signal-before-final-departure" for row in linked
            ),
            "signal_to_departure_minutes_p25": format(quantile(signal_to_departure, Decimal("0.25")), "f"),
            "signal_to_departure_minutes_p50": format(quantile(signal_to_departure, Decimal("0.50")), "f"),
            "signal_to_departure_minutes_p75": format(quantile(signal_to_departure, Decimal("0.75")), "f"),
            "partition_stability": partition_timing,
        },
        "stop_findings": stop_mismatch,
        "target_findings": {
            "market_days": len(targets),
            "opposite_09_boundary_hit_by_16_count": len(target_hits),
            "opposite_09_boundary_hit_by_16_rate": fraction(len(target_hits), len(targets)),
            "post_boundary_extension_rates": extension_rates,
        },
        "predeclared_research_families": {
            "timing": [
                {
                    "code": "T0_SOURCE_BASELINE",
                    "signal_window": "10:00-10:59 NY",
                    "execution": "earliest source-valid R2.2 actionable entry",
                },
                {
                    "code": "T1_LATE_SOURCE_HOUR",
                    "signal_window": "10:00-10:59 NY",
                    "entry_window": "10:30-10:59 NY",
                    "execution": "wait for a causal post-raid reclaim plus source-valid PD-array retest",
                },
                {
                    "code": "T2_DELAYED_EXECUTION",
                    "signal_window": "10:00-10:59 NY",
                    "entry_window": "10:30-11:29 NY",
                    "execution": "original Silver Bullet thesis must remain structurally valid; require a new causal reclaim/confirmation before fill",
                },
            ],
            "entry": [
                {"code": "E0_R22", "rule": "existing R2.2 earliest actionable confluence"},
                {
                    "code": "E1_RECLAIM_PDARRAY",
                    "rule": "after first-side raid, require local/reference liquidity sweep-reclaim followed by FVG/Breaker/OB retest",
                },
            ],
            "initial_stop": [
                {"code": "S0_SOURCE_SWING", "rule": "source-methodological structural swing extreme, no fixed buffer"},
                {
                    "code": "S1_RECLAIM_EXTREME",
                    "rule": "structural extreme belonging to the causal reclaim that authorizes the delayed entry; no retrospective widening",
                },
            ],
            "target": [
                {"code": "P0_OPPOSITE_09_BOUNDARY", "rule": "full exit at opposite frozen 09:00 reference boundary"},
                {
                    "code": "P1_BOUNDARY_PLUS_RUNNER",
                    "rule": "realize at opposite boundary and research a predeclared 0.25-reference runner only after boundary is reached",
                },
            ],
            "management": [
                {"code": "M0_NO_M1_TRAIL", "rule": "no R8 protected-swing M1 trailing"},
                {
                    "code": "M1_ONE_SHOT_BE", "rule": "single breakeven transition at a predeclared favorable-excursion boundary; threshold chosen only by consumed WFO"},
            ],
        },
        "next_gate": {
            "required": "leakage-free walk-forward on consumed R5/R6/R8 evidence",
            "selection_basis": "temporal stability + economics + stress, not one aggregate bucket",
            "fresh_holdout_remains_sealed": True,
        },
    }
    return result


def self_test() -> None:
    assert hhmm(Decimal("607")) == "10:07"
    assert bucket_15("2020-01-01T15:37:00+00:00") == "10:30"
    assert fraction(104, 153) == "0.6797385620915032679738562092"
    print("VT31 NAS100 CIBO adaptation model self-test PASS")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--ledger-dir", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.self_test:
        self_test()
        return
    if args.ledger_dir is None or args.output is None:
        parser.error("--ledger-dir and --output are required")
    result = build(args.ledger_dir)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"market": result["market"], "next_gate": result["next_gate"]}, sort_keys=True))


if __name__ == "__main__":
    main()

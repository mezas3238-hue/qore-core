"""Walk-forward survey for VT31 Silver Bullet across all three index markets.

This is research-only and consumes only the already-consumed R8/R6/R5 M1
artifacts. It deliberately does not open any fresh holdout. The purpose is to
measure temporal stability of the same source-coherent Silver Bullet baseline
before market-specific CIBO adaptations are frozen for NAS100, SP500 and US30.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import vt31_nas100_r1_candidate as baseline
from qore.infrastructure.traders import vt31_silver_bullet_r2_2 as source_model

MARKETS = ("NAS100", "SP500", "US30")
PARTITIONS = ("r8_fresh", "r6", "r5")
SCHEMA = "qore.vt31.three_market_consumed_wfo.v1"


def _wfo_monte_carlo(
    _trades: list[dict[str, object]],
) -> tuple[dict[str, object], dict[str, bool]]:
    """Defer expensive Monte Carlo until a market-specific candidate is frozen."""
    return (
        {
            "algorithm": "not-evaluated-in-consumed-baseline-wfo",
            "paths": 0,
            "positive_terminal_probability": None,
            "p95_max_drawdown_r": None,
        },
        {
            "positive_terminal_probability_at_least_0_70": False,
            "p95_max_drawdown_at_most_20r": False,
        },
    )


def _compact(result: dict[str, Any]) -> dict[str, Any]:
    """Keep WFO economics/diagnostics while excluding full per-trade payloads."""
    return {
        "market_days": result["market_days"],
        "source_setups": result["source_setups"],
        "executable_setups": result["executable_setups"],
        "status_counts": result["status_counts"],
        "aggregate": result["aggregate"],
        "stress_0_05r": result["stress_0_05r"],
        "side_stress": result["side_stress"],
        "entry_family_stress": result["entry_family_stress"],
        "quarter_stress": result["quarter_stress"],
        "excursion_reach": result["excursion_reach"],
        "monte_carlo": result["monte_carlo"],
    }


def run(partition_dirs: dict[str, Path]) -> dict[str, Any]:
    original_market = baseline.MARKET
    original_monte_carlo = baseline._monte_carlo
    original_authorized_market = source_model.AUTHORIZED_MARKET
    replays: dict[str, dict[str, Any]] = {}
    baseline._monte_carlo = _wfo_monte_carlo
    try:
        for market in MARKETS:
            market_result: dict[str, Any] = {}
            baseline.MARKET = market
            source_model.AUTHORIZED_MARKET = market
            for partition in PARTITIONS:
                evidence = partition_dirs[partition] / market / "market-evidence.json"
                if not evidence.is_file():
                    raise FileNotFoundError(evidence)
                market_result[partition] = _compact(baseline.replay(evidence))
            replays[market] = market_result
    finally:
        baseline.MARKET = original_market
        baseline._monte_carlo = original_monte_carlo
        source_model.AUTHORIZED_MARKET = original_authorized_market

    return {
        "schema": SCHEMA,
        "research_only": True,
        "opens_new_holdout": False,
        "fresh_holdout_consumed": False,
        "live_authorized": False,
        "production_authorized": False,
        "purpose": (
            "fixed-policy chronological stability survey before market-specific "
            "CIBO parameter freeze"
        ),
        "source_authority": {
            "original_r2_2_market": "NAS100",
            "sp500_us30_status": (
                "research-only translation of the same formation mechanics; not source "
                "authorization and not a production contract"
            ),
        },
        "baseline_policy": {
            "strategy": "VT31 AM Silver Bullet / source-coherent R2.2 formation mechanics",
            "reference": "09:00-10:00 NY frozen range",
            "setup_window": "10:00-10:59 NY",
            "initial_stop": "source methodological swing extreme",
            "target": "opposite frozen 09:00 reference boundary",
            "management": "3R then one-shot breakeven; no R8 M1 protected trail",
            "friction_r_per_trade": "0.05",
            "monte_carlo": "deferred-until-market-specific-candidate-freeze",
            "note": (
                "This is the common baseline only. WFO results are inputs to separate "
                "NAS100/SP500/US30 timing-entry-stop-target adaptations, not authority "
                "to clone one specialist across markets."
            ),
        },
        "chronology": [
            {"partition": "r8_fresh", "role": "consumed earliest block"},
            {"partition": "r6", "role": "consumed middle block"},
            {"partition": "r5", "role": "consumed latest block"},
        ],
        "markets": replays,
        "next_gate": (
            "Use only consumed-WFO evidence to model market-specific hour/entry/SL/target/"
            "management rules; freeze each specialist before any fresh 1Y holdout."
        ),
    }


def self_test() -> None:
    report, gates = _wfo_monte_carlo([])
    assert MARKETS == ("NAS100", "SP500", "US30")
    assert PARTITIONS == ("r8_fresh", "r6", "r5")
    assert SCHEMA.endswith(".v1")
    assert source_model.AUTHORIZED_MARKET == "NAS100"
    assert report["paths"] == 0
    assert not any(gates.values())
    print("VT31 three-market consumed WFO self-test PASS")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--r8-dir", type=Path)
    parser.add_argument("--r6-dir", type=Path)
    parser.add_argument("--r5-dir", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.self_test:
        self_test()
        return
    if None in (args.r8_dir, args.r6_dir, args.r5_dir, args.output):
        parser.error("--r8-dir --r6-dir --r5-dir --output are required")

    payload = run(
        {
            "r8_fresh": args.r8_dir,
            "r6": args.r6_dir,
            "r5": args.r5_dir,
        }
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )

    summary: dict[str, Any] = {}
    for market in MARKETS:
        summary[market] = {}
        for partition in PARTITIONS:
            row = payload["markets"][market][partition]
            summary[market][partition] = {
                "sample": row["stress_0_05r"]["sample"],
                "mean_r": row["stress_0_05r"]["mean_r"],
                "profit_factor": row["stress_0_05r"]["profit_factor"],
                "max_drawdown_r": row["stress_0_05r"]["max_drawdown_r"],
                "max_losing_streak": row["stress_0_05r"]["max_losing_streak"],
            }
    print(json.dumps(summary, sort_keys=True))


if __name__ == "__main__":
    main()

"""R3-B deterministic block-bootstrap certification for frozen BTC REF2_PLUS.

Uses the exact R3-A chronological trade sequence and QORE's deterministic
circular-block draw stream. The thresholds were frozen in the R3 candidate
freeze before this result is observed.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from pathlib import Path
from typing import Any

from qore.infrastructure.trader_lab.vt08_crt_pure_r2o_btcusd_block_robustness import (
    BASE_SEED,
    BLOCK_LENGTHS,
    RESAMPLE_COUNT,
    _distribution,
    _policy,
)
from qore.infrastructure.trader_lab.vt08_crt_pure_r3a_btcusd_chronological import (
    CANDIDATE_IDENTITY,
    run_replay,
)

IDENTITY = "VT08_CRT_PURE_BTCUSD_R3B_BLOCK_BOOTSTRAP_001"
SCHEMA = "qore.vt08.crt_pure.r3b_btcusd_block_bootstrap.v1"

MIN_POSITIVE_TERMINAL = 0.90
MAX_P95_DD_R = 15.0


def run_block_certification() -> tuple[tuple[object, ...], dict[str, Any]]:
    trades, chronological = run_replay()
    policies: dict[str, Any] = {}
    failures: list[str] = []

    for block_length in BLOCK_LENGTHS:
        result = _distribution(trades, _policy(block_length))
        policies[f"BLOCK_{block_length}"] = result
        if float(result["positive_terminal_fraction"]) < MIN_POSITIVE_TERMINAL:
            failures.append(f"BLOCK_{block_length}_POSITIVE_TERMINAL")
        if float(result["max_drawdown_r"]["p95"]) > MAX_P95_DD_R:
            failures.append(f"BLOCK_{block_length}_P95_DD")

    report: dict[str, Any] = {
        "schema": SCHEMA,
        "identity": IDENTITY,
        "candidate_identity": CANDIDATE_IDENTITY,
        "chronological_gate_passed": chronological["chronological_gate_passed"],
        "chronological_gate_failures": chronological["chronological_gate_failures"],
        "resampling_engine": "QORE_RESEARCH_CIRCULAR_BLOCK_DRAW_STREAM",
        "block_lengths": list(BLOCK_LENGTHS),
        "resample_count": RESAMPLE_COUNT,
        "base_seed": BASE_SEED,
        "thresholds_frozen_before_results": True,
        "min_positive_terminal_fraction": MIN_POSITIVE_TERMINAL,
        "max_p95_drawdown_r": MAX_P95_DD_R,
        "policies": policies,
        "block_gate_passed": not failures,
        "block_gate_failures": failures,
        "candidate_certified": False,
        "demo_eligible": False,
        "live_authorized": False,
        "real_capital_authorized": False,
        "production_authorized": False,
        "research_only": True,
    }
    return tuple(trades), report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("output", type=Path)
    args = parser.parse_args()

    trades, report = run_block_certification()
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / "report.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n"
    )
    with (args.output / "source_trades.jsonl").open("w", encoding="utf-8") as handle:
        for trade in trades:
            handle.write(json.dumps(asdict(trade), sort_keys=True) + "\n")
    print("CRT_R3B_BTC_BLOCK_JSON=" + json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    main()

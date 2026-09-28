"""Shard wrapper for exact V36 multi-position episode simulation.

This module changes only execution topology. It calls the exact V36 period
implementation for one named consumed period and preserves all V36 economics.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from qore.infrastructure.trader_lab import (
    capitalizer_cognitive_r_milestone_protection_2r_v1 as milestone,
)
from qore.infrastructure.trader_lab import (
    capitalizer_factor_journey_probe_ranker_v11 as v11,
)
from qore.infrastructure.trader_lab import (
    capitalizer_multi_position_causal_episode_simulator_v36 as v36,
)
from qore.infrastructure.trader_lab import (
    capitalizer_sequence_failure_memory_abstention_v13 as v13,
)

IDENTITY = "QORE_CAPITALIZER_MULTI_POSITION_CAUSAL_EPISODE_SIMULATOR_V36_SHARD"


def run_period(
    *,
    period: str,
    development_root: Path,
    validation_root: Path,
    reserved_root: Path,
    development_validation_context_root: Path,
    reserved_context_root: Path,
    transition_path: Path,
) -> dict[str, Any]:
    windows, contextual_model = v13._load_windows(
        development_root,
        validation_root,
        reserved_root,
        development_validation_context_root,
        reserved_context_root,
    )
    if period not in windows:
        raise ValueError(f"V36 shard unknown period: {period}")
    transition_rows = v36._load_transition_rows(transition_path)
    rows = transition_rows.get(period)
    if rows is None:
        raise ValueError(f"V36 shard missing transition evidence: {period}")

    simultaneous: dict[
        tuple[str, str, str], tuple[milestone.SimulatedTrade, ...]
    ] = {}
    for current_period, (ledgers, _contexts) in windows.items():
        simultaneous.update(
            v11._simultaneous_map(
                period=current_period,
                ledgers=ledgers,
            )
        )

    previous = dict(v11._SIMULTANEOUS)
    v11._SIMULTANEOUS.clear()
    v11._SIMULTANEOUS.update(simultaneous)
    try:
        ledgers, contexts = windows[period]
        result, audits = v36._period_report(
            period=period,
            transition_rows=rows,
            ledgers=ledgers,
            contexts=contexts,
            contextual_model=contextual_model,
        )
    finally:
        v11._SIMULTANEOUS.clear()
        v11._SIMULTANEOUS.update(previous)

    return {
        "identity": IDENTITY,
        "economic_identity": v36.IDENTITY,
        "execution_topology_only": True,
        "period": period,
        "result": result,
        "pair_audits": [v36.asdict(row) for row in audits],
        "candidate_count": 0,
        "trader_certified": False,
        "fresh_holdout_opened": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--period", required=True)
    parser.add_argument("--development-root", type=Path, required=True)
    parser.add_argument("--validation-root", type=Path, required=True)
    parser.add_argument("--reserved-root", type=Path, required=True)
    parser.add_argument(
        "--development-validation-context-root",
        type=Path,
        required=True,
    )
    parser.add_argument("--reserved-context-root", type=Path, required=True)
    parser.add_argument("--transition-path", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    report = run_period(
        period=args.period,
        development_root=args.development_root,
        validation_root=args.validation_root,
        reserved_root=args.reserved_root,
        development_validation_context_root=(
            args.development_validation_context_root
        ),
        reserved_context_root=args.reserved_context_root,
        transition_path=args.transition_path,
    )
    args.output.mkdir(parents=True, exist_ok=True)
    out = args.output / "capitalizer-v36-shard.json"
    out.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

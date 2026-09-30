"""Reconstruct exact V2 checkpoint ledgers and emit certification analytics.

The checkpoint contains only committed intervention steps plus summary metrics.
This audit replays the committed plan through the same causal Surface machinery,
fails closed on metric drift, computes the edge-first certification metrics, and
compares winner preservation against the exact Surface control.

This is consumed-evidence analysis only. It cannot certify a final candidate and
does not open fresh holdout economics.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Any

from qore.infrastructure.trader_lab import (
    capitalizer_cognitive_r_milestone_protection_2r_v1 as milestone,
)
from qore.infrastructure.trader_lab import (
    capitalizer_drawdown_chronology_semantics_audit_v1 as chronology,
)
from qore.infrastructure.trader_lab import (
    capitalizer_dynamic_episode_sequence_feasibility_v1 as sequence_v1,
)
from qore.infrastructure.trader_lab import (
    capitalizer_factor_journey_probe_ranker_v11 as v11,
)
from qore.infrastructure.trader_lab import (
    capitalizer_portfolio_drawdown_feasibility_episode_anatomy_v1 as anatomy,
)
from qore.infrastructure.trader_lab import (
    capitalizer_scalper_certification_metrics_v2 as cert_metrics,
)
from qore.infrastructure.trader_lab import (
    capitalizer_sequence_failure_memory_abstention_v13 as v13,
)

IDENTITY = "QORE_CAPITALIZER_SCALPER_CONSUMED_CERTIFICATION_AUDIT_V2"
EXPECTED_CHECKPOINT_IDENTITY = (
    "QORE_CAPITALIZER_V2_DISTRIBUTED_CHECKPOINT_RUNNER_V1"
)


def _load_checkpoint(
    path: Path,
    *,
    period: str,
) -> tuple[
    dict[str, Any],
    dict[tuple[str, str], str],
]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("checkpoint must be a JSON object")
    if payload.get("identity") != EXPECTED_CHECKPOINT_IDENTITY:
        raise ValueError("unexpected checkpoint identity")
    if payload.get("period") != period:
        raise ValueError("checkpoint period mismatch")
    raw_steps = payload.get("steps")
    if not isinstance(raw_steps, list):
        raise ValueError("checkpoint steps must be a list")
    plan: dict[tuple[str, str], str] = {}
    for raw in raw_steps:
        if not isinstance(raw, dict):
            raise ValueError("checkpoint step must be object")
        key = (str(raw["symbol"]), str(raw["entry_at"]))
        action = str(raw["action"])
        if key in plan:
            raise ValueError("checkpoint contains duplicate entrant intervention")
        plan[key] = action
    return payload, plan


def _period_inputs(
    *,
    period: str,
    development_root: Path,
    validation_root: Path,
    reserved_root: Path,
    development_validation_context_root: Path,
    reserved_context_root: Path,
) -> tuple[
    dict[str, tuple[milestone.SimulatedTrade, ...]],
    dict[tuple[str, str], Any],
    dict[str, Any],
    dict[
        tuple[str, str, str],
        tuple[milestone.SimulatedTrade, ...],
    ],
]:
    windows, contextual_model = v13._load_windows(
        development_root,
        validation_root,
        reserved_root,
        development_validation_context_root,
        reserved_context_root,
    )
    if period not in windows:
        raise ValueError(f"unknown audit period: {period}")
    simultaneous: dict[
        tuple[str, str, str],
        tuple[milestone.SimulatedTrade, ...],
    ] = {}
    for current_period, (period_ledgers, _period_contexts) in windows.items():
        simultaneous.update(
            v11._simultaneous_map(
                period=current_period,
                ledgers=period_ledgers,
            )
        )
    ledgers, contexts = windows[period]
    return ledgers, contexts, contextual_model, simultaneous


def build_audit(
    *,
    period: str,
    checkpoint_path: Path,
    development_root: Path,
    validation_root: Path,
    reserved_root: Path,
    development_validation_context_root: Path,
    reserved_context_root: Path,
    window_start: date,
    window_end_exclusive: date,
) -> tuple[
    dict[str, Any],
    tuple[milestone.SimulatedTrade, ...],
]:
    checkpoint, plan = _load_checkpoint(
        checkpoint_path,
        period=period,
    )
    (
        ledgers,
        contexts,
        contextual_model,
        simultaneous,
    ) = _period_inputs(
        period=period,
        development_root=development_root,
        validation_root=validation_root,
        reserved_root=reserved_root,
        development_validation_context_root=(
            development_validation_context_root
        ),
        reserved_context_root=reserved_context_root,
    )

    previous = dict(v11._SIMULTANEOUS)
    v11._SIMULTANEOUS.clear()
    v11._SIMULTANEOUS.update(simultaneous)
    try:
        candidate_ledger, _decisions, applied = sequence_v1._replay_plan(
            period=period,
            ledgers=ledgers,
            contexts=contexts,
            contextual_model=contextual_model,
            plan=plan,
        )
        surface_report, surface_ledger, _surface_decisions = (
            anatomy._surface_ledger(
                period=period,
                ledgers=ledgers,
                contexts=contexts,
                contextual_model=contextual_model,
            )
        )
    finally:
        v11._SIMULTANEOUS.clear()
        v11._SIMULTANEOUS.update(previous)

    candidate_metrics = milestone._metrics(candidate_ledger)
    if candidate_metrics != checkpoint["current_metrics"]:
        raise ValueError(
            "checkpoint replay metrics drift from authoritative checkpoint"
        )
    if set(applied) != set(plan):
        raise ValueError("checkpoint replay did not apply every committed action")

    certification = cert_metrics.build_certification_metrics_report(
        candidate_ledger,
        population_role=f"CONSUMED_{period}",
        window_start=window_start,
        window_end_exclusive=window_end_exclusive,
    )
    control_certification = cert_metrics.build_certification_metrics_report(
        surface_ledger,
        population_role=f"CONSUMED_{period}_SURFACE_CONTROL",
        window_start=window_start,
        window_end_exclusive=window_end_exclusive,
    )
    preservation = cert_metrics.compare_winner_preservation(
        surface_ledger,
        candidate_ledger,
        window_start=window_start,
        window_end_exclusive=window_end_exclusive,
    )

    realized_exit_batch_dd = Decimal(
        chronology._exit_batch_metrics(candidate_ledger)["max_drawdown_r"]
    )
    report = {
        "identity": IDENTITY,
        "period": period,
        "checkpoint_identity": checkpoint["identity"],
        "checkpoint_complete": bool(checkpoint["complete"]),
        "checkpoint_stop_reason": str(checkpoint["stop_reason"]),
        "checkpoint_intervention_count": len(plan),
        "checkpoint_metrics_reproduced_exactly": True,
        "same_entrant_identities": preservation.same_entrant_identities,
        "candidate_metrics": asdict(certification),
        "surface_control_metrics": asdict(control_certification),
        "winner_preservation": asdict(preservation),
        "realized_exit_batch_drawdown_r": str(realized_exit_batch_dd),
        "legacy_certification_drawdown_r": (
            certification.economics.max_drawdown_r
        ),
        "fresh_holdout_opened": False,
        "consumed_evidence_only": True,
        "classification_performed": False,
        "trader_certified": False,
    }
    return report, candidate_ledger


def write_audit(
    report: dict[str, Any],
    ledger: tuple[milestone.SimulatedTrade, ...],
    output: Path,
) -> None:
    output.mkdir(parents=True, exist_ok=True)
    stem = "capitalizer-scalper-consumed-certification-audit-v2"
    (output / f"{stem}.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    with (output / f"{stem}-ledger.jsonl").open(
        "w",
        encoding="utf-8",
    ) as handle:
        for row in ledger:
            handle.write(json.dumps(asdict(row), sort_keys=True) + "\n")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--period", required=True)
    parser.add_argument("--checkpoint", type=Path, required=True)
    parser.add_argument("--development-root", type=Path, required=True)
    parser.add_argument("--validation-root", type=Path, required=True)
    parser.add_argument("--reserved-root", type=Path, required=True)
    parser.add_argument(
        "--development-validation-context-root",
        type=Path,
        required=True,
    )
    parser.add_argument("--reserved-context-root", type=Path, required=True)
    parser.add_argument("--window-start", required=True)
    parser.add_argument("--window-end-exclusive", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    report, ledger = build_audit(
        period=args.period,
        checkpoint_path=args.checkpoint,
        development_root=args.development_root,
        validation_root=args.validation_root,
        reserved_root=args.reserved_root,
        development_validation_context_root=(
            args.development_validation_context_root
        ),
        reserved_context_root=args.reserved_context_root,
        window_start=date.fromisoformat(args.window_start),
        window_end_exclusive=date.fromisoformat(
            args.window_end_exclusive
        ),
    )
    write_audit(report, ledger, args.output)
    print(json.dumps(report, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

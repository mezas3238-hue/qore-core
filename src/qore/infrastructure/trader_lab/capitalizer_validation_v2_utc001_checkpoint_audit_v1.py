"""UTC-001 per-year diagnostic for an exact Validation V2 checkpoint.

This module does not certify the Trader. Validation is consumed evidence and the
V2 plan is outcome-aware diagnostic research. The purpose is to quantify whether
the exact V2 trajectory improvements repair UTC-001 annual deficits or merely
improve the two-year aggregate.

No Fresh Holdout access. No policy promotion.
"""

from __future__ import annotations

import argparse
import json
from datetime import date
from pathlib import Path
from typing import Any

from qore.infrastructure.trader_lab import (
    capitalizer_cognitive_r_milestone_protection_2r_v1 as milestone,
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
    capitalizer_scalper_utc001_consumed_audit_v1 as utc_audit,
)
from qore.infrastructure.trader_lab import (
    capitalizer_v2_distributed_checkpoint_runner_v1 as distributed,
)

IDENTITY = "QORE_CAPITALIZER_VALIDATION_V2_UTC001_CHECKPOINT_AUDIT_V1"
# Uses the UTC-001 modules validated on the primary PR branch.
PERIOD = "CONSUMED_VALIDATION_2022_2024"
WINDOW_START = date(2022, 9, 17)
WINDOW_END = date(2024, 9, 17)


def _year_summary(report: utc_audit.ConsumedUtcAuditReport) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for year in report.exam_years:
        failed = [
            gate.gate
            for gate in year.utc_gate_statuses
            if gate.status.value == "FAIL"
        ]
        missing = [
            gate.gate
            for gate in year.utc_gate_statuses
            if gate.status.value == "MISSING"
        ]
        rows.append(
            {
                "period_id": year.period_id,
                "window_start": year.window_start,
                "window_end_exclusive": year.window_end_exclusive,
                "trades": year.economics.trades,
                "profit_factor": year.economics.profit_factor,
                "expectancy_r_per_trade": year.economics.expectancy_r_per_trade,
                "sharpe_annualized": year.risk_adjusted.sharpe_annualized,
                "sortino_annualized": year.risk_adjusted.sortino_annualized,
                "max_drawdown_r": year.economics.max_drawdown_r,
                "payoff_ratio": year.economics.payoff_ratio,
                "max_losing_streak": year.economics.max_losing_streak,
                "mc_positive_probability": (
                    year.monte_carlo.conservative_positive_probability
                ),
                "mc_p95_drawdown_r": (
                    year.monte_carlo.conservative_p95_drawdown_r
                ),
                "failed_gates": failed,
                "missing_gates": missing,
            }
        )
    return rows


def build_report(
    *,
    development_root: Path,
    validation_root: Path,
    reserved_root: Path,
    development_validation_context_root: Path,
    reserved_context_root: Path,
    transition_path: Path,
    checkpoint_path: Path,
) -> dict[str, Any]:
    (
        ledgers,
        contexts,
        contextual_model,
        _reserve_seeds,
        _relief_seeds,
        baseline_metrics,
        _modes,
        _ordered,
        _order_index,
        simultaneous,
    ) = distributed._prepare_period(
        period=PERIOD,
        development_root=development_root,
        validation_root=validation_root,
        reserved_root=reserved_root,
        development_validation_context_root=(
            development_validation_context_root
        ),
        reserved_context_root=reserved_context_root,
        transition_path=transition_path,
    )

    transition_sha = distributed._sha256(transition_path)
    previous = dict(v11._SIMULTANEOUS)
    v11._SIMULTANEOUS.clear()
    v11._SIMULTANEOUS.update(simultaneous)
    try:
        (
            plan,
            steps,
            replay_evaluations,
            replayed_trade_evaluations,
            invalid_trials,
            checkpoint_metrics,
        ) = distributed._load_checkpoint(
            checkpoint_path,
            period=PERIOD,
            transition_sha256=transition_sha,
            baseline=baseline_metrics,
        )
        if checkpoint_metrics is None:
            raise ValueError("Validation V2 UTC audit requires checkpoint metrics")

        candidate_ledger, _decisions, applied = sequence_v1._replay_plan(
            period=PERIOD,
            ledgers=ledgers,
            contexts=contexts,
            contextual_model=contextual_model,
            plan=plan,
        )
        if set(applied) != set(plan):
            raise ValueError("Validation V2 UTC audit plan application drift")

        candidate_metrics = milestone._metrics(candidate_ledger)
        if candidate_metrics != checkpoint_metrics:
            raise ValueError("Validation V2 UTC audit checkpoint replay drift")

        _control, surface_ledger, _surface_decisions = anatomy._surface_ledger(
            period=PERIOD,
            ledgers=ledgers,
            contexts=contexts,
            contextual_model=contextual_model,
        )

        surface_audit = utc_audit.build_report(
            surface_ledger,
            population_role="VALIDATION_SURFACE_2022_2024",
            window_start=WINDOW_START,
            window_end_exclusive=WINDOW_END,
            development_only=False,
            consumed_for_engineering=True,
        )
        candidate_audit = utc_audit.build_report(
            candidate_ledger,
            population_role="VALIDATION_V2_CHECKPOINT_2022_2024",
            window_start=WINDOW_START,
            window_end_exclusive=WINDOW_END,
            development_only=False,
            consumed_for_engineering=True,
        )
    finally:
        v11._SIMULTANEOUS.clear()
        v11._SIMULTANEOUS.update(previous)

    surface_years = _year_summary(surface_audit)
    candidate_years = _year_summary(candidate_audit)
    if len(surface_years) != 2 or len(candidate_years) != 2:
        raise ValueError("Validation V2 UTC audit requires exactly two exam years")

    deltas: list[dict[str, Any]] = []
    for surface, candidate in zip(surface_years, candidate_years, strict=True):
        deltas.append(
            {
                "year_index": len(deltas) + 1,
                "profit_factor_delta": (
                    None
                    if surface["profit_factor"] is None
                    or candidate["profit_factor"] is None
                    else str(
                        float(candidate["profit_factor"])
                        - float(surface["profit_factor"])
                    )
                ),
                "expectancy_delta_r_per_trade": str(
                    float(candidate["expectancy_r_per_trade"])
                    - float(surface["expectancy_r_per_trade"])
                ),
                "max_drawdown_delta_r": str(
                    float(candidate["max_drawdown_r"])
                    - float(surface["max_drawdown_r"])
                ),
                "payoff_delta": (
                    None
                    if surface["payoff_ratio"] is None
                    or candidate["payoff_ratio"] is None
                    else str(
                        float(candidate["payoff_ratio"])
                        - float(surface["payoff_ratio"])
                    )
                ),
            }
        )

    return {
        "identity": IDENTITY,
        "period": PERIOD,
        "evaluation": "CONSUMED_OUTCOME_AWARE_V2_CHECKPOINT_UTC001_DIAGNOSTIC",
        "checkpoint_interventions": len(plan),
        "checkpoint_steps": len(steps),
        "checkpoint_replay_evaluations": replay_evaluations,
        "checkpoint_replayed_trade_evaluations": replayed_trade_evaluations,
        "checkpoint_invalid_trials": invalid_trials,
        "two_year_surface_metrics": baseline_metrics,
        "two_year_candidate_metrics": candidate_metrics,
        "surface_years": surface_years,
        "candidate_years": candidate_years,
        "per_year_deltas": deltas,
        "global_compensation_allowed": False,
        "temporal_compensation_allowed": False,
        "cost_certification_blocked": True,
        "consumed_evidence": True,
        "outcome_aware_diagnostic": True,
        "certification_authority": False,
        "runtime_policy_candidate": False,
        "fresh_holdout_opened": False,
        "trader_certified": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
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
    parser.add_argument("--checkpoint", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    report = build_report(
        development_root=args.development_root,
        validation_root=args.validation_root,
        reserved_root=args.reserved_root,
        development_validation_context_root=(
            args.development_validation_context_root
        ),
        reserved_context_root=args.reserved_context_root,
        transition_path=args.transition_path,
        checkpoint_path=args.checkpoint,
    )
    args.output.mkdir(parents=True, exist_ok=True)
    out = args.output / "capitalizer-validation-v2-utc001-checkpoint-audit-v1.json"
    out.write_text(
        json.dumps(report, indent=2, sort_keys=True, default=str) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report, sort_keys=True, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

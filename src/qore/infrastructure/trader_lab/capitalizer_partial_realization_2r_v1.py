"""Causal partial-realization engineering for Capitalizer true-2R.

The remaining drawdown after contextual routing is dominated by trades that first
move favorably and later surrender that excursion. This lab tests whether
realizing a deterministic fraction at causal R-milestones can improve BOTH PF
and drawdown while preserving every entry and the runner's fixed 2R target.

No outcome chooses a plan. The plan family is fixed before evaluation. A partial
triggers only when the already-validated milestone replay proves that threshold
was reached. The remainder follows the same validated protection mode.

Economic accounting uses original-position fractions:
    realized = sum(partial_fraction * threshold_r)
             + remaining_fraction * runner_realized_r

Trade count/density remain unchanged. Runner target remains 2R.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass, replace
from decimal import Decimal
from pathlib import Path
from typing import Any

from qore.infrastructure.trader_lab import (
    capitalizer_cognitive_r_milestone_protection_2r_v1 as milestone,
)
from qore.infrastructure.trader_lab import (
    capitalizer_max_recovery_direct_m1_replay_v1 as direct,
)

IDENTITY = "QORE_CAPITALIZER_PARTIAL_REALIZATION_2R_V1"
SOURCE_DIRECT_RUN_ID = 36196002610
SOURCE_DIRECT_SHA = "ddd00209e50d5ec16c8cb94f34e9e5e95f401839"

EXPECTED_DEVELOPMENT_TRADES = 948
EXPECTED_VALIDATION_TRADES = 1034


@dataclass(frozen=True, slots=True)
class PartialStep:
    threshold_r: Decimal
    fraction_of_original: Decimal


@dataclass(frozen=True, slots=True)
class PartialPlan:
    name: str
    runner_mode: milestone.ProtectionMode
    steps: tuple[PartialStep, ...]


PLANS = (
    PartialPlan(
        "ORIGINAL_CONTROL",
        milestone.ProtectionMode.ORIGINAL,
        (),
    ),
    PartialPlan(
        "STAGED_FULL_CONTROL",
        milestone.ProtectionMode.STAGED_050_100_150,
        (),
    ),
    PartialPlan(
        "P20_050_STAGED",
        milestone.ProtectionMode.STAGED_050_100_150,
        (PartialStep(Decimal("0.50"), Decimal("0.20")),),
    ),
    PartialPlan(
        "P25_050_STAGED",
        milestone.ProtectionMode.STAGED_050_100_150,
        (PartialStep(Decimal("0.50"), Decimal("0.25")),),
    ),
    PartialPlan(
        "P20_050_P20_100_STAGED",
        milestone.ProtectionMode.STAGED_050_100_150,
        (
            PartialStep(Decimal("0.50"), Decimal("0.20")),
            PartialStep(Decimal("1.00"), Decimal("0.20")),
        ),
    ),
    PartialPlan(
        "P25_050_P25_100_STAGED",
        milestone.ProtectionMode.STAGED_050_100_150,
        (
            PartialStep(Decimal("0.50"), Decimal("0.25")),
            PartialStep(Decimal("1.00"), Decimal("0.25")),
        ),
    ),
    PartialPlan(
        "P20_050_P20_100_P20_150_STAGED",
        milestone.ProtectionMode.STAGED_050_100_150,
        (
            PartialStep(Decimal("0.50"), Decimal("0.20")),
            PartialStep(Decimal("1.00"), Decimal("0.20")),
            PartialStep(Decimal("1.50"), Decimal("0.20")),
        ),
    ),
    PartialPlan(
        "P25_075_LOCK025",
        milestone.ProtectionMode.LOCK025_AFTER_075,
        (PartialStep(Decimal("0.75"), Decimal("0.25")),),
    ),
    PartialPlan(
        "P20_075_P20_125_STAGED075",
        milestone.ProtectionMode.STAGED_075_125_150,
        (
            PartialStep(Decimal("0.75"), Decimal("0.20")),
            PartialStep(Decimal("1.25"), Decimal("0.20")),
        ),
    ),
    PartialPlan(
        "P25_075_P25_125_STAGED075",
        milestone.ProtectionMode.STAGED_075_125_150,
        (
            PartialStep(Decimal("0.75"), Decimal("0.25")),
            PartialStep(Decimal("1.25"), Decimal("0.25")),
        ),
    ),
)


def _validate_plan(plan: PartialPlan) -> None:
    total = sum(
        (step.fraction_of_original for step in plan.steps),
        Decimal("0"),
    )
    if total < 0 or total >= 1:
        raise ValueError(f"invalid partial total for {plan.name}: {total}")
    previous = Decimal("-1")
    for step in plan.steps:
        if step.threshold_r <= previous:
            raise ValueError(f"partial thresholds must increase: {plan.name}")
        if step.threshold_r <= 0 or step.threshold_r >= Decimal("2"):
            raise ValueError(f"partial threshold outside runner lifecycle: {plan.name}")
        if step.fraction_of_original <= 0:
            raise ValueError(f"partial fraction must be positive: {plan.name}")
        previous = step.threshold_r


for _plan in PLANS:
    _validate_plan(_plan)


def _load_selected(
    root: Path,
    *,
    expected: int,
) -> dict[str, tuple[milestone.SimulatedTrade, ...]]:
    raw = {
        mode.value: direct._load_mode(root, mode=mode)
        for mode in milestone.ProtectionMode
    }
    selected = {
        mode: direct._max3_milestone(rows)
        for mode, rows in raw.items()
    }
    if {len(rows) for rows in selected.values()} != {expected}:
        raise ValueError("partial-realization population mismatch")
    baseline_keys = {
        (row.symbol, row.entry_at)
        for row in selected[milestone.ProtectionMode.ORIGINAL.value]
    }
    if any(
        {(row.symbol, row.entry_at) for row in rows} != baseline_keys
        for rows in selected.values()
    ):
        raise ValueError("partial-realization mode identities differ")
    return selected


def _apply_plan(
    row: milestone.SimulatedTrade,
    *,
    plan: PartialPlan,
) -> milestone.SimulatedTrade:
    max_mfe = Decimal(row.max_milestone_r_seen_before_exit)
    realized = Decimal(row.realized_gross_r)
    triggered = tuple(
        step
        for step in plan.steps
        if max_mfe >= step.threshold_r
    )
    partial_fraction = sum(
        (step.fraction_of_original for step in triggered),
        Decimal("0"),
    )
    partial_r = sum(
        (
            step.fraction_of_original * step.threshold_r
            for step in triggered
        ),
        Decimal("0"),
    )
    remaining = Decimal("1") - partial_fraction
    combined = partial_r + remaining * realized
    return replace(
        row,
        realized_gross_r=str(combined),
        mode=plan.name,
    )


def _ledger(
    ledgers: dict[str, tuple[milestone.SimulatedTrade, ...]],
    *,
    plan: PartialPlan,
) -> tuple[milestone.SimulatedTrade, ...]:
    runner = ledgers[plan.runner_mode.value]
    return tuple(_apply_plan(row, plan=plan) for row in runner)


def _evaluate_role(
    *,
    role: str,
    ledgers: dict[str, tuple[milestone.SimulatedTrade, ...]],
) -> dict[str, Any]:
    original = ledgers[milestone.ProtectionMode.ORIGINAL.value]
    original_metrics = milestone._metrics(original)
    plans: list[dict[str, Any]] = []
    for plan in PLANS:
        ledger = _ledger(ledgers, plan=plan)
        metrics = milestone._metrics(ledger)
        plans.append(
            {
                "plan": plan.name,
                "runner_mode": plan.runner_mode.value,
                "partial_steps": [
                    {
                        "threshold_r": str(step.threshold_r),
                        "fraction_of_original": str(step.fraction_of_original),
                    }
                    for step in plan.steps
                ],
                "trades": len(ledger),
                "density_retention": "1",
                "metrics": metrics,
                "pf_at_least_original": (
                    metrics["profit_factor"] is not None
                    and original_metrics["profit_factor"] is not None
                    and Decimal(str(metrics["profit_factor"]))
                    >= Decimal(str(original_metrics["profit_factor"]))
                ),
                "total_r_at_least_original": (
                    Decimal(str(metrics["total_r"]))
                    >= Decimal(str(original_metrics["total_r"]))
                ),
                "dd_below_original": (
                    Decimal(str(metrics["max_drawdown_r"]))
                    < Decimal(str(original_metrics["max_drawdown_r"]))
                ),
                "dd_at_or_below_6r": (
                    Decimal(str(metrics["max_drawdown_r"])) <= Decimal("6")
                ),
            }
        )
    return {
        "role": role,
        "control_metrics": original_metrics,
        "plans": plans,
    }


def build_report(
    development_root: Path,
    validation_root: Path,
) -> dict[str, Any]:
    development = _load_selected(
        development_root,
        expected=EXPECTED_DEVELOPMENT_TRADES,
    )
    validation = _load_selected(
        validation_root,
        expected=EXPECTED_VALIDATION_TRADES,
    )
    dev = _evaluate_role(role="DEVELOPMENT", ledgers=development)
    val = _evaluate_role(
        role="CONSUMED_VALIDATION_2022_2024",
        ledgers=validation,
    )

    val_by_name = {row["plan"]: row for row in val["plans"]}
    dev_by_name = {row["plan"]: row for row in dev["plans"]}
    combined: list[dict[str, Any]] = []
    for plan in PLANS:
        dev_row = dev_by_name[plan.name]
        val_row = val_by_name[plan.name]
        combined.append(
            {
                "plan": plan.name,
                "development": dev_row,
                "validation": val_row,
                "development_pareto": (
                    bool(dev_row["pf_at_least_original"])
                    and bool(dev_row["total_r_at_least_original"])
                    and bool(dev_row["dd_below_original"])
                ),
                "validation_pareto": (
                    bool(val_row["pf_at_least_original"])
                    and bool(val_row["total_r_at_least_original"])
                    and bool(val_row["dd_below_original"])
                ),
                "validation_dd6": bool(val_row["dd_at_or_below_6r"]),
            }
        )

    both = tuple(
        row
        for row in combined
        if row["development_pareto"] and row["validation_pareto"]
    )
    return {
        "identity": IDENTITY,
        "source_direct_run_id": SOURCE_DIRECT_RUN_ID,
        "source_direct_sha": SOURCE_DIRECT_SHA,
        "development_role": "CONSUMED_RESEARCH_2024_2026",
        "validation_role": "CONSUMED_VALIDATION_2022_2024",
        "validation_is_fresh_holdout": False,
        "development_trades": EXPECTED_DEVELOPMENT_TRADES,
        "validation_trades": EXPECTED_VALIDATION_TRADES,
        "plan_count": len(PLANS),
        "results": combined,
        "pareto_in_both_windows_count": len(both),
        "validation_dd6_count": sum(
            row["validation_dd6"] for row in combined
        ),
        "all_entries_preserved": True,
        "runner_target_r": "2.00",
        "partial_thresholds_outcome_tuned": False,
        "partial_fractions_outcome_tuned": False,
        "milestone_reached_before_partial": True,
        "same_bar_future_order_inferred": False,
        "current_outcome_used_to_trigger_partial": False,
        "strategy_entry_changed": False,
        "original_stop_geometry_changed_at_entry": False,
        "max3_changed": False,
        "automatic_plan_promotion": False,
        "runtime_rule_selected": False,
        "trader_certified": False,
        "live_authorized": False,
        "real_capital_authorized": False,
        "next_phase": (
            "COMBINE_ROBUST_PARTIAL_PLAN_WITH_CONTEXTUAL_ROUTING"
            if both
            else "FALSIFY_PARTIAL_REALIZATION_AND_RETURN_TO_CONTEXTUAL_PATH"
        ),
    }


def write_report(report: dict[str, Any], output: Path) -> None:
    output.mkdir(parents=True, exist_ok=True)
    (output / "capitalizer-partial-realization-2r-v1.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("development_root", type=Path)
    parser.add_argument("validation_root", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    report = build_report(args.development_root, args.validation_root)
    write_report(report, args.output)
    print(json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    main()

"""VT31 Shared natural drawdown causal discrimination V31.

Consumed-fold calibration-only laboratory built from V30's causal-origin atlas.

V31 does NOT change any trade. It asks whether fixed semantic hypotheses can
identify losses that form drawdown before the outcome while preserving valuable
winners. All outcome/DD labels are offline evaluation labels only.

No sizing. No risk weighting. No entry abstention. No stop/target mutation.
No trailing. No target extension. R5 and fresh holdouts remain closed.
"""
# ruff: noqa: E501
from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
import vt31_core_stack_v4_natural_dd_causal_origin_atlas_v30 as v30

SCHEMA = "qore.core_stack_v4.vt31.natural_dd_causal_discrimination.v31"
IDENTITY = "VT31_NAS100_SHARED_NATURAL_DD_CAUSAL_DISCRIMINATION_V31"
ZERO = Decimal("0")


@dataclass(frozen=True, slots=True)
class CausalRiskHypothesis:
    name: str
    situations: frozenset[str] = frozenset()
    environment_trajectories: frozenset[str] = frozenset()
    semantic_signatures: frozenset[str] = frozenset()

    def matches(self, row: dict[str, object]) -> bool:
        return (
            str(row["situation"]) in self.situations
            or str(row["environment_trajectory"]) in self.environment_trajectories
            or str(row["semantic_signature"]) in self.semantic_signatures
        )

    def payload(self) -> dict[str, object]:
        return {
            "name": self.name,
            "situations": tuple(sorted(self.situations)),
            "environment_trajectories": tuple(sorted(self.environment_trajectories)),
            "semantic_signatures": tuple(sorted(self.semantic_signatures)),
            "numeric_threshold_grid_search": False,
            "actuation": False,
        }


ZERO_WIN_OR_NEAR_ZERO_TRANSITIONS = frozenset(
    {
        "SUPPORTIVE|STABILIZING",
        "SUPPORTIVE|DIVERGING",
        "STABILIZING|RECOVERING",
        "RESTORED|HEALTHY",
        "DEGRADING|DIVERGING",
        "DEGRADING|STABILIZING",
        "FRAGILE|WEAKENING",
    }
)

HIGH_STRUCTURAL_LOW_RESILIENCE = frozenset(
    {
        "T=HIGH|U=LOW|S=HIGH|R=LOW",
        "T=HIGH|U=HIGH|S=MID|R=LOW",
        "T=HIGH|U=HIGH|S=HIGH|R=LOW",
        "T=MID|U=HIGH|S=MID|R=LOW",
    }
)

MID_STRUCTURAL_PERSISTENT = frozenset(
    {
        "T=MID|U=LOW|S=MID|R=MID",
        "T=MID|U=LOW|S=MID|R=LOW",
        "T=HIGH|U=LOW|S=MID|R=LOW",
    }
)

HYPOTHESES = (
    CausalRiskHypothesis(
        name="STABLE_ADVERSE_TRANSITIONS",
        environment_trajectories=ZERO_WIN_OR_NEAR_ZERO_TRANSITIONS,
    ),
    CausalRiskHypothesis(
        name="CONTESTED_OR_RAPID",
        situations=frozenset({"CONTESTED", "RAPID_DETERIORATION"}),
    ),
    CausalRiskHypothesis(
        name="STRUCTURAL_LOW_RESILIENCE",
        semantic_signatures=HIGH_STRUCTURAL_LOW_RESILIENCE,
    ),
    CausalRiskHypothesis(
        name="COMPOSITE_PRECISION_ORIGIN",
        situations=frozenset({"CONTESTED", "RAPID_DETERIORATION"}),
        environment_trajectories=ZERO_WIN_OR_NEAR_ZERO_TRANSITIONS,
        semantic_signatures=HIGH_STRUCTURAL_LOW_RESILIENCE,
    ),
    CausalRiskHypothesis(
        name="COMPOSITE_COVERAGE_ORIGIN",
        situations=frozenset({"CONTESTED", "RAPID_DETERIORATION"}),
        environment_trajectories=ZERO_WIN_OR_NEAR_ZERO_TRANSITIONS,
        semantic_signatures=HIGH_STRUCTURAL_LOW_RESILIENCE
        | MID_STRUCTURAL_PERSISTENT,
    ),
)


def _d(value: object) -> Decimal:
    return Decimal(str(value))


def _recall(hit: int, total: int) -> str:
    return "0" if total == 0 else format(Decimal(hit) / Decimal(total), "f")


def _evaluate(
    rows: list[dict[str, object]],
    *,
    hypothesis: CausalRiskHypothesis,
) -> dict[str, object]:
    flagged = [row for row in rows if hypothesis.matches(row)]
    losses = [row for row in rows if row["outcome"] == "LOSS"]
    winners = [row for row in rows if row["outcome"] == "WIN"]

    flagged_losses = [row for row in flagged if row["outcome"] == "LOSS"]
    flagged_winners = [row for row in flagged if row["outcome"] == "WIN"]

    max_dd_losses = [
        row
        for row in losses
        if bool(row["in_max_dd_excursion"])
    ]
    flagged_max_dd_losses = [
        row
        for row in flagged_losses
        if bool(row["in_max_dd_excursion"])
    ]

    top3_dd_losses = [
        row
        for row in losses
        if bool(row["in_top3_dd_excursions"])
    ]
    flagged_top3_dd_losses = [
        row
        for row in flagged_losses
        if bool(row["in_top3_dd_excursions"])
    ]

    unobservable_losses = [
        row
        for row in losses
        if bool(row["unobservable_loss"])
    ]
    flagged_unobservable_losses = [
        row
        for row in flagged_losses
        if bool(row["unobservable_loss"])
    ]

    total_winner_r = sum((_d(row["baseline_r"]) for row in winners), ZERO)
    flagged_winner_r = sum((_d(row["baseline_r"]) for row in flagged_winners), ZERO)
    flagged_loss_r = -sum((_d(row["baseline_r"]) for row in flagged_losses), ZERO)
    flagged_top3_loss_r = -sum(
        (_d(row["baseline_r"]) for row in flagged_top3_dd_losses),
        ZERO,
    )

    lead_values = [
        int(row["lead_seconds_before_fill"])
        for row in flagged_losses
        if row["lead_seconds_before_fill"] is not None
    ]

    return {
        "sample": len(rows),
        "flagged": len(flagged),
        "flagged_fraction": _recall(len(flagged), len(rows)),
        "losses": len(losses),
        "flagged_losses": len(flagged_losses),
        "loss_recall": _recall(len(flagged_losses), len(losses)),
        "max_dd_losses": len(max_dd_losses),
        "flagged_max_dd_losses": len(flagged_max_dd_losses),
        "max_dd_loss_recall": _recall(
            len(flagged_max_dd_losses),
            len(max_dd_losses),
        ),
        "top3_dd_losses": len(top3_dd_losses),
        "flagged_top3_dd_losses": len(flagged_top3_dd_losses),
        "top3_dd_loss_recall": _recall(
            len(flagged_top3_dd_losses),
            len(top3_dd_losses),
        ),
        "unobservable_losses": len(unobservable_losses),
        "flagged_unobservable_losses": len(flagged_unobservable_losses),
        "unobservable_loss_recall": _recall(
            len(flagged_unobservable_losses),
            len(unobservable_losses),
        ),
        "winners": len(winners),
        "flagged_winners": len(flagged_winners),
        "winner_false_positive_rate": _recall(
            len(flagged_winners),
            len(winners),
        ),
        "total_winner_r": format(total_winner_r, "f"),
        "flagged_winner_r_exposure": format(flagged_winner_r, "f"),
        "winner_r_false_positive_exposure": (
            "0"
            if total_winner_r == ZERO
            else format(flagged_winner_r / total_winner_r, "f")
        ),
        "flagged_loss_r_identified": format(flagged_loss_r, "f"),
        "flagged_top3_dd_loss_r_identified": format(
            flagged_top3_loss_r,
            "f",
        ),
        "minimum_lead_seconds_before_flagged_loss": (
            None if not lead_values else min(lead_values)
        ),
        "median_lead_seconds_before_flagged_loss": (
            None
            if not lead_values
            else sorted(lead_values)[len(lead_values) // 2]
        ),
        "actuation_used": False,
        "realized_dd_claimed_reduced": False,
    }


def _diagnostic_score(r8: dict[str, object], r6: dict[str, object]) -> Decimal:
    # Calibration ranking only: reward DD-loss coverage and penalize winner-R
    # exposure. It is not a runtime feature or a certification score.
    coverage = (
        _d(r8["top3_dd_loss_recall"])
        + _d(r6["top3_dd_loss_recall"])
        + _d(r8["unobservable_loss_recall"])
        + _d(r6["unobservable_loss_recall"])
    ) / Decimal("4")
    winner_exposure = (
        _d(r8["winner_r_false_positive_exposure"])
        + _d(r6["winner_r_false_positive_exposure"])
    ) / Decimal("2")
    return coverage * (Decimal("1") - min(Decimal("1"), winner_exposure))


def run(
    *,
    r8_trades: Path,
    r6_trades: Path,
    r8_nas: Path,
    r8_sp: Path,
    r8_us: Path,
    r6_nas: Path,
    r6_sp: Path,
    r6_us: Path,
    daily_path: Path,
) -> dict[str, object]:
    daily = v30.v28.v27.v26.v23.v22.v21.v20.v19.v18.v2.v3._load_daily(daily_path)
    r8_source = v30.v28.v27.v26.v23.v22.v21.v20.v19.v18._load_cross_rows(
        trades=r8_trades,
        nas=r8_nas,
        sp=r8_sp,
        us=r8_us,
        daily=daily,
    )
    r6_source = v30.v28.v27.v26.v23.v22.v21.v20.v19.v18._load_cross_rows(
        trades=r6_trades,
        nas=r6_nas,
        sp=r6_sp,
        us=r6_us,
        daily=daily,
    )
    if len(r8_source) != 228 or len(r6_source) != 278:
        raise AssertionError("VT31 R8/R6 challenge-set drift")

    p8, _ = v30.v28.v27.v26._prepare(
        r8_source,
        nas_evidence=r8_nas,
        sp_evidence=r8_sp,
        us_evidence=r8_us,
    )
    p6, _ = v30.v28.v27.v26._prepare(
        r6_source,
        nas_evidence=r6_nas,
        sp_evidence=r6_sp,
        us_evidence=r6_us,
    )

    e8 = v30._drawdown_excursions(p8)
    e6 = v30._drawdown_excursions(p6)
    rows8 = v30._signature_rows(p8, e8)
    rows6 = v30._signature_rows(p6, e6)

    results: list[dict[str, object]] = []
    for hypothesis in HYPOTHESES:
        r8_eval = _evaluate(rows8, hypothesis=hypothesis)
        r6_eval = _evaluate(rows6, hypothesis=hypothesis)
        results.append(
            {
                "hypothesis": hypothesis.payload(),
                "r8": r8_eval,
                "r6": r6_eval,
                "diagnostic_score": format(
                    _diagnostic_score(r8_eval, r6_eval),
                    "f",
                ),
            }
        )
    results.sort(
        key=lambda row: _d(row["diagnostic_score"]),
        reverse=True,
    )

    return {
        "schema": SCHEMA,
        "identity": IDENTITY,
        "research_phase": "PHASE_1_NATURAL_DD_INTELLIGENCE",
        "status": "CALIBRATION_DIAGNOSTIC_NO_ACTUATION",
        "challenge_set": {"r8": 228, "r6": 278},
        "hypothesis_results": results,
        "best_diagnostic_hypothesis": (
            None if not results else results[0]["hypothesis"]
        ),
        "phase_1_contract": {
            "same_trade_universe": True,
            "same_initial_position_size": True,
            "sizing_used": False,
            "capital_weighting_used": False,
            "entry_abstention_used": False,
            "stop_geometry_mutated": False,
            "target_geometry_mutated": False,
            "trailing_used": False,
            "target_extension_used": False,
            "realized_dd_reduction_claimed": False,
            "runtime_outcome_input_used": False,
            "future_market_input_used": False,
            "outcomes_used_offline_for_evaluation_only": True,
            "r5_opened": False,
            "new_holdout_opened": False,
        },
        "governance": {
            "vt31_is_falsification_lab_only": True,
            "live_authorized": False,
            "production_authorized": False,
            "real_capital_authorized": False,
            "merge_authorized": False,
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--r8-trades", type=Path, required=True)
    parser.add_argument("--r6-trades", type=Path, required=True)
    parser.add_argument("--r8-nas", type=Path, required=True)
    parser.add_argument("--r8-sp", type=Path, required=True)
    parser.add_argument("--r8-us", type=Path, required=True)
    parser.add_argument("--r6-nas", type=Path, required=True)
    parser.add_argument("--r6-sp", type=Path, required=True)
    parser.add_argument("--r6-us", type=Path, required=True)
    parser.add_argument("--daily-path", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    payload = run(
        r8_trades=args.r8_trades,
        r6_trades=args.r6_trades,
        r8_nas=args.r8_nas,
        r8_sp=args.r8_sp,
        r8_us=args.r8_us,
        r6_nas=args.r6_nas,
        r6_sp=args.r6_sp,
        r6_us=args.r6_us,
        daily_path=args.daily_path,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, sort_keys=True, indent=2) + "\n")
    print(
        json.dumps(
            {
                "status": payload["status"],
                "best_diagnostic_hypothesis": payload[
                    "best_diagnostic_hypothesis"
                ],
                "hypothesis_results": payload["hypothesis_results"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()

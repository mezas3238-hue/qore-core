"""V22-D R2 threshold-free relational recoverability veto ablation.

R1 showed a cross-window pattern inside frozen V21 INSUFFICIENT selections:
false winners carry more recovery persistence and relatively stronger trajectory
support than true losses, while adverse hazard magnitude itself is not a safe
terminal discriminator.

R2 falsifies a small set of pre-declared *relational* recoverability rules.
These rules contain no fitted numeric threshold, no fold/symbol/trader identity
and no future information.  They compare contemporaneous causal evidence
against contemporaneous adversity.

The rules are veto-only: they may remove a V21 loss mark but can never create a
TARGET/WINNER decision.  V21 probability ceiling 0.055 stays frozen.  A rule is
admitted only if it preserves V21 loss recall in every consumed window while
meeting the frozen winner-safety floors.  Fresh holdout remains closed.
"""

# ruff: noqa: E501,I001

from __future__ import annotations

import argparse
import json
from decimal import Decimal
from pathlib import Path
from statistics import median
from typing import Any, Callable

import numpy as np
import shared_relational_adversity_challenge_survival_v21 as v21

from qore.infrastructure.core_stack_v2.adversity_challenge_intelligence import (
    AdversityChallengeState,
)

IDENTITY = "QORE_SHARED_V22D_R2_RELATIONAL_RECOVERABILITY_VETO_ABLATION"
SCHEMA = "qore.shared.v22d_r2_relational_recoverability_veto_ablation"

SOURCE_V6_RUN = 36131607443
SOURCE_V21_RUN = 36156421332
SOURCE_V22D_R1_RUN = 36171655958

WINDOWS = (v21.TRAIN_WINDOW, *v21.VALIDATION_WINDOWS)

PRECISION_FLOOR = Decimal("0.90")
WINNER_MARK_CEILING = Decimal("0.01")
MIN_SELECTED_TRADES = 20
MIN_MEDIAN_LEAD_BARS = Decimal("1")

Rule = Callable[[dict[str, Any]], bool]


def _trajectory_recovery_reserve(row: dict[str, Any]) -> bool:
    return (
        int(row["trajectory_support_bps"])
        + int(row["path_recovery_persistence_bps"])
        > int(row["trajectory_adversity_bps"])
    )


def _path_recovery_reserve(row: dict[str, Any]) -> bool:
    return (
        int(row["path_support_bps"])
        + int(row["path_recovery_persistence_bps"])
        > int(row["path_adverse_dominance_bps"])
    )


def _recovery_over_deterioration_pressure(row: dict[str, Any]) -> bool:
    return (
        int(row["trajectory_support_bps"])
        + int(row["path_recovery_persistence_bps"])
        > int(row["trajectory_deterioration_pressure_bps"])
    )


def _dual_path_and_trajectory_reserve(row: dict[str, Any]) -> bool:
    return _trajectory_recovery_reserve(row) and _path_recovery_reserve(row)


def _trajectory_reserve_and_pressure(row: dict[str, Any]) -> bool:
    return _trajectory_recovery_reserve(row) and _recovery_over_deterioration_pressure(row)


RULES: dict[str, Rule] = {
    "TRAJECTORY_RECOVERY_RESERVE": _trajectory_recovery_reserve,
    "PATH_RECOVERY_RESERVE": _path_recovery_reserve,
    "RECOVERY_OVER_DETERIORATION_PRESSURE": _recovery_over_deterioration_pressure,
    "DUAL_PATH_AND_TRAJECTORY_RESERVE": _dual_path_and_trajectory_reserve,
    "TRAJECTORY_RESERVE_AND_PRESSURE": _trajectory_reserve_and_pressure,
}


def _ratio(n: int, d: int) -> Decimal:
    return Decimal("0") if d <= 0 else Decimal(n) / Decimal(d)


def _selected_v21(
    *,
    trades: list[dict[str, Any]],
    probabilities: np.ndarray,
    meta: list[dict[str, Any]],
    threshold: Decimal,
) -> dict[int, dict[str, Any]]:
    chosen: dict[int, dict[str, Any]] = {}
    limit = float(threshold)
    for probability, item in zip(probabilities, meta, strict=True):
        trade_index = int(item["trade_index"])
        if trade_index in chosen:
            continue
        if v21._relational_veto(item["challenge"]):
            continue
        if float(probability) > limit:
            continue
        chosen[trade_index] = item
    return chosen


def _metrics_from_chosen(
    *,
    trades: list[dict[str, Any]],
    chosen: dict[int, dict[str, Any]],
) -> v21.Metrics:
    losses = sum(trade["actual"] == "LOSS" for trade in trades)
    winners = sum(trade["actual"] == "WIN" for trade in trades)
    true_loss = [i for i in chosen if trades[i]["actual"] == "LOSS"]
    false_winner = [i for i in chosen if trades[i]["actual"] == "WIN"]
    leads = [
        int(chosen[i]["row"]["bars_before_canonical_exit"])
        for i in true_loss
    ]
    return v21.Metrics(
        selected=len(chosen),
        true_loss=len(true_loss),
        false_winner=len(false_winner),
        precision=_ratio(len(true_loss), len(chosen)),
        loss_recall=_ratio(len(true_loss), losses),
        winner_mark_rate=_ratio(len(false_winner), winners),
        median_lead_bars=None if not leads else Decimal(str(median(leads))),
        relational_veto_count=0,
        survival_veto_count=0,
    )


def _evaluate_rule(
    *,
    trades: list[dict[str, Any]],
    baseline: dict[int, dict[str, Any]],
    baseline_metrics: v21.Metrics,
    rule: Rule,
) -> dict[str, object]:
    kept: dict[int, dict[str, Any]] = {}
    vetoed_true_loss = 0
    vetoed_false_winner = 0
    eligible_insufficient = 0

    for trade_index, item in baseline.items():
        challenge = item["challenge"]
        veto = False
        if challenge.state == AdversityChallengeState.INSUFFICIENT:
            eligible_insufficient += 1
            veto = rule(item["row"])
        if veto:
            if trades[trade_index]["actual"] == "LOSS":
                vetoed_true_loss += 1
            else:
                vetoed_false_winner += 1
            continue
        kept[trade_index] = item

    metrics = _metrics_from_chosen(trades=trades, chosen=kept)
    passed = (
        metrics.selected >= MIN_SELECTED_TRADES
        and metrics.precision >= PRECISION_FLOOR
        and metrics.winner_mark_rate <= WINNER_MARK_CEILING
        and metrics.loss_recall >= baseline_metrics.loss_recall
        and metrics.median_lead_bars is not None
        and metrics.median_lead_bars >= MIN_MEDIAN_LEAD_BARS
    )
    return {
        "eligible_insufficient": eligible_insufficient,
        "vetoed_true_loss": vetoed_true_loss,
        "vetoed_false_winner": vetoed_false_winner,
        "metrics": v21._payload(metrics),
        "recall_delta_vs_v21": str(metrics.loss_recall - baseline_metrics.loss_recall),
        "precision_delta_vs_v21": str(metrics.precision - baseline_metrics.precision),
        "winner_mark_delta_vs_v21": str(
            metrics.winner_mark_rate - baseline_metrics.winner_mark_rate
        ),
        "status": "ADMIT" if passed else "REJECT",
    }


def _window(
    *,
    hazard_model: Any,
    survival_model: Any,
    categories: dict[str, tuple[str, ...]],
    trades: list[dict[str, Any]],
    threshold: Decimal,
) -> dict[str, object]:
    x_rows, _, _, meta = v21._candidate_dataset(
        hazard_model=hazard_model,
        categories=categories,
        trades=trades,
    )
    probabilities = survival_model.predict_proba(x_rows)[:, 1]
    baseline = _selected_v21(
        trades=trades,
        probabilities=probabilities,
        meta=meta,
        threshold=threshold,
    )
    baseline_metrics = _metrics_from_chosen(trades=trades, chosen=baseline)
    return {
        "sample": len(trades),
        "v21": v21._payload(baseline_metrics),
        "rules": {
            name: _evaluate_rule(
                trades=trades,
                baseline=baseline,
                baseline_metrics=baseline_metrics,
                rule=rule,
            )
            for name, rule in RULES.items()
        },
    }


def run(v6_json: Path) -> dict[str, object]:
    ledger = json.loads(v6_json.read_text())
    if ledger["identity"] != "QORE_SHARED_VT08_INDEX_STOP_TARGET_DISCRIMINATION_V6":
        raise ValueError("unexpected frozen external falsification ledger identity")

    hazard_model, categories = v21._fit_hazard(ledger)
    train_trades = list(ledger[v21.TRAIN_WINDOW]["rows"])
    (
        survival_model,
        _,
        _,
        train_probabilities,
        train_meta,
    ) = v21._fit_survival(
        hazard_model=hazard_model,
        categories=categories,
        trades=train_trades,
    )
    threshold, _, _ = v21._choose_threshold(
        trades=train_trades,
        probabilities=train_probabilities,
        meta=train_meta,
    )
    if threshold is None:
        raise ValueError("V21 frozen threshold unavailable")

    windows = {
        key: _window(
            hazard_model=hazard_model,
            survival_model=survival_model,
            categories=categories,
            trades=list(ledger[key]["rows"]),
            threshold=threshold,
        )
        for key in WINDOWS
    }

    admitted_rules = [
        name
        for name in RULES
        if all(
            windows[key]["rules"][name]["status"] == "ADMIT"
            for key in WINDOWS
        )
    ]

    return {
        "schema": SCHEMA,
        "identity": IDENTITY,
        "source_v6_run": SOURCE_V6_RUN,
        "source_v21_run": SOURCE_V21_RUN,
        "source_v22d_r1_run": SOURCE_V22D_R1_RUN,
        "research_only": True,
        "shared_autonomous_model": True,
        "decision_policy_changed": False,
        "predeclared_relational_rules_only": True,
        "numeric_threshold_fitted": False,
        "v21_survival_threshold_frozen": str(threshold),
        "veto_only_cannot_create_target_or_winner": True,
        "consumed_evidence_only": True,
        "fresh_holdout_opened": False,
        "runtime_current_position_pnl_used": False,
        "runtime_terminal_outcome_used": False,
        "runtime_future_market_used": False,
        "runtime_symbol_identity_used": False,
        "runtime_market_identity_used": False,
        "runtime_methodology_identity_used": False,
        "runtime_calendar_identity_used": False,
        "runtime_fold_identity_used": False,
        "sizing_used": False,
        "risk_weighting_used": False,
        "runtime_actuation": False,
        "closed_outcome_used_for_offline_rule_scoring_only": True,
        "pass_law": {
            "loss_recall": "rule >= V21 in every consumed window",
            "precision_floor": str(PRECISION_FLOOR),
            "winner_mark_ceiling": str(WINNER_MARK_CEILING),
            "minimum_selected_trades": MIN_SELECTED_TRADES,
            "minimum_median_lead_bars": str(MIN_MEDIAN_LEAD_BARS),
        },
        "admitted_rules": admitted_rules,
        "validation_pass": bool(admitted_rules),
        "scientific_status": "PASS" if admitted_rules else "REJECT",
        "windows": windows,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--v6-json", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    payload = run(args.v6_json)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    print(json.dumps({
        "identity": payload["identity"],
        "scientific_status": payload["scientific_status"],
        "validation_pass": payload["validation_pass"],
        "admitted_rules": payload["admitted_rules"],
        "windows": payload["windows"],
    }, sort_keys=True))


if __name__ == "__main__":
    main()

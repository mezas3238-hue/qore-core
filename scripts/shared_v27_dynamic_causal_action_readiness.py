"""V27 dynamic causal action-readiness arbitration for Shared Core.

V26 proved that multi-horizon timing carries useful information, but treating
every frozen V21 mark as an immediate action forces a false choice: either keep
false winners or sacrifice real-loss recall.

V27 separates cognition from action readiness.

- V21 candidate evidence is a WATCH surface, not automatic action.
- Multi-horizon cumulative incidence determines whether adverse evidence is
  actually near-term and front-loaded enough for EXIT_RISK_WARNING.
- The scan is dynamic: a trade may remain WATCH for several causal observations
  and become action-ready later.
- A modest secondary survival ceiling may admit a previously vetoed candidate
  only when timing confirmation is strong enough.
- The first EXIT_RISK_WARNING is the only point counted as a hypothetical
  intervention. WATCH/DEFEND states have no execution authority.

All readiness thresholds and the secondary survival ceiling are selected on
five-year consumed evidence only, then frozen unchanged for recent-two-year and
R66 consumed windows. Multi-horizon models are also fit on five-year only.
Fresh holdout remains closed.

Runtime inference consumes only current/prior causal market evidence and frozen
models. CLOSED outcomes and exit distance are used offline only for training
multi-horizon models and scoring the research surface.
"""

# ruff: noqa: E501,I001

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from statistics import median
from typing import Any

import shared_relational_adversity_challenge_survival_v21 as v21
import shared_v26_r0b_selection_corrected_incidence_forensics as v26r0b

from qore.infrastructure.core_stack_v2.causal_action_readiness import (
    ActionReadinessDisposition,
    CausalActionReadinessEvidence,
    CausalActionReadinessPolicy,
    assess_causal_action_readiness,
)

IDENTITY = "QORE_SHARED_V27_DYNAMIC_CAUSAL_ACTION_READINESS"
SCHEMA = "qore.shared.v27_dynamic_causal_action_readiness"

SOURCE_V6_RUN = 36131607443
SOURCE_V21_RUN = 36156421332
SOURCE_V26_R0B_RUN = 36210276127
SOURCE_V26_R1_RUN = 36210719743

TRAIN_WINDOW = v21.TRAIN_WINDOW
VALIDATION_WINDOWS = v21.VALIDATION_WINDOWS
WINDOWS = (TRAIN_WINDOW, *VALIDATION_WINDOWS)

TRAIN_PRECISION_FLOOR = Decimal("0.95")
VALIDATION_PRECISION_FLOOR = Decimal("0.90")
WINNER_MARK_CEILING = Decimal("0.01")
MIN_SELECTED_TRADES = 20
MIN_MEDIAN_LEAD_BARS = Decimal("1")

SURVIVAL_CEILINGS = (
    Decimal("0.055"),
    Decimal("0.075"),
    Decimal("0.100"),
    Decimal("0.125"),
    Decimal("0.150"),
)
EXIT_H1_FLOORS = (1_500, 2_000, 2_500, 3_000)
EXIT_IMMINENCE_FLOORS = (4_000, 5_000, 6_000, 7_000)
EXIT_MARGIN_FLOORS = (1_000, 1_500, 2_000, 2_500)
EXIT_VELOCITY_FLOORS = (-1_000, -500, 0, 500)


@dataclass(frozen=True, slots=True)
class Metrics:
    action_count: int
    true_loss: int
    false_winner: int
    precision: Decimal
    loss_recall: Decimal
    winner_mark_rate: Decimal
    median_lead_bars: Decimal | None
    baseline_v21_overlap: int
    recovered_beyond_v21: int
    watched_before_action: int


def _ratio(numerator: int, denominator: int) -> Decimal:
    return Decimal("0") if denominator <= 0 else Decimal(numerator) / Decimal(denominator)


def _baseline_v21(
    *,
    trades: list[dict[str, Any]],
    surface: list[dict[str, Any]],
    threshold: Decimal,
) -> dict[int, dict[str, Any]]:
    chosen: dict[int, dict[str, Any]] = {}
    limit = float(threshold)
    for item in surface:
        trade_index = int(item["trade_index"])
        if trade_index in chosen:
            continue
        if v21._relational_veto(item["challenge"]):
            continue
        if float(item["survival_probability"]) > limit:
            continue
        chosen[trade_index] = item
    return chosen


def _metrics(
    *,
    trades: list[dict[str, Any]],
    chosen: dict[int, dict[str, Any]],
    baseline_ids: set[int],
) -> Metrics:
    losses = sum(trade["actual"] == "LOSS" for trade in trades)
    winners = sum(trade["actual"] == "WIN" for trade in trades)
    true_loss = [index for index in chosen if trades[index]["actual"] == "LOSS"]
    false_winner = [index for index in chosen if trades[index]["actual"] == "WIN"]
    leads = [
        int(chosen[index]["row"]["bars_before_canonical_exit"])
        for index in true_loss
    ]
    overlap = sum(index in baseline_ids for index in chosen)
    recovered = sum(index not in baseline_ids for index in chosen)
    watched = sum(int(chosen[index]["watch_count_before_action"]) > 0 for index in chosen)
    return Metrics(
        action_count=len(chosen),
        true_loss=len(true_loss),
        false_winner=len(false_winner),
        precision=_ratio(len(true_loss), len(chosen)),
        loss_recall=_ratio(len(true_loss), losses),
        winner_mark_rate=_ratio(len(false_winner), winners),
        median_lead_bars=None if not leads else Decimal(str(median(leads))),
        baseline_v21_overlap=overlap,
        recovered_beyond_v21=recovered,
        watched_before_action=watched,
    )


def _payload(metrics: Metrics) -> dict[str, object]:
    return {
        "action_count": metrics.action_count,
        "true_loss": metrics.true_loss,
        "false_winner": metrics.false_winner,
        "precision": str(metrics.precision),
        "loss_recall": str(metrics.loss_recall),
        "winner_mark_rate": str(metrics.winner_mark_rate),
        "median_lead_bars": (
            None if metrics.median_lead_bars is None else str(metrics.median_lead_bars)
        ),
        "baseline_v21_overlap": metrics.baseline_v21_overlap,
        "recovered_beyond_v21": metrics.recovered_beyond_v21,
        "watched_before_action": metrics.watched_before_action,
    }


def _surface(
    *,
    ledger: dict[str, Any],
    key: str,
    hazard_model: Any,
    survival_model: Any,
    categories: dict[str, tuple[str, ...]],
    adverse_models: dict[int, Any],
    favorable_models: dict[int, Any],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    trades = list(ledger[key]["rows"])
    profile_map, _ = v26r0b._profile_map(
        trades=trades,
        categories=categories,
        adverse_models=adverse_models,
        favorable_models=favorable_models,
    )
    x_rows, _, _, meta = v21._candidate_dataset(
        hazard_model=hazard_model,
        categories=categories,
        trades=trades,
    )
    survival_probabilities = survival_model.predict_proba(x_rows)[:, 1]

    prior_h1: dict[int, int] = {}
    surface: list[dict[str, Any]] = []
    for probability, item in zip(survival_probabilities, meta, strict=True):
        trade_index = int(item["trade_index"])
        as_of = str(item["row"]["as_of"])
        profile = profile_map[(trade_index, as_of)]["profile"]
        adverse_h1 = int(profile.adverse_curve_bps[0])
        velocity = adverse_h1 - prior_h1.get(trade_index, adverse_h1)
        prior_h1[trade_index] = adverse_h1
        surface.append(
            {
                **item,
                "survival_probability": float(probability),
                "adverse_h1_bps": adverse_h1,
                "adverse_h3_bps": int(profile.adverse_curve_bps[1]),
                "favorable_h1_bps": int(profile.favorable_curve_bps[0]),
                "favorable_h3_bps": int(profile.favorable_curve_bps[1]),
                "near_directional_margin_bps": int(
                    profile.near_directional_margin_bps
                ),
                "adverse_velocity_bps": velocity,
            }
        )
    return trades, surface


def _readiness_policy(
    *,
    h1_floor: int,
    imminence_floor: int,
    margin_floor: int,
    velocity_floor: int,
) -> CausalActionReadinessPolicy:
    watch = min(800, h1_floor)
    defend = min(max(watch, 1_200), h1_floor)
    return CausalActionReadinessPolicy(
        watch_adverse_h1_bps=watch,
        defend_adverse_h1_bps=defend,
        exit_adverse_h1_bps=h1_floor,
        exit_imminence_ratio_bps=imminence_floor,
        exit_near_margin_bps=margin_floor,
        exit_minimum_velocity_bps=velocity_floor,
    )


def _select_actions(
    *,
    surface: list[dict[str, Any]],
    survival_ceiling: Decimal,
    h1_floor: int,
    imminence_floor: int,
    margin_floor: int,
    velocity_floor: int,
) -> dict[int, dict[str, Any]]:
    chosen: dict[int, dict[str, Any]] = {}
    watch_counts: dict[int, int] = {}
    limit = float(survival_ceiling)
    policy = _readiness_policy(
        h1_floor=h1_floor,
        imminence_floor=imminence_floor,
        margin_floor=margin_floor,
        velocity_floor=velocity_floor,
    )

    for item in surface:
        trade_index = int(item["trade_index"])
        if trade_index in chosen:
            continue
        if v21._relational_veto(item["challenge"]):
            continue
        if float(item["survival_probability"]) > limit:
            continue

        evidence = CausalActionReadinessEvidence(
            as_of=datetime.fromisoformat(str(item["row"]["as_of"])),
            adverse_h1_bps=int(item["adverse_h1_bps"]),
            adverse_h3_bps=int(item["adverse_h3_bps"]),
            favorable_h1_bps=int(item["favorable_h1_bps"]),
            favorable_h3_bps=int(item["favorable_h3_bps"]),
            near_directional_margin_bps=int(
                item["near_directional_margin_bps"]
            ),
            adverse_velocity_bps=int(item["adverse_velocity_bps"]),
            uncertainty_bps=int(item["row"]["uncertainty_bps"]),
        )
        assessment = assess_causal_action_readiness(
            evidence,
            policy=policy,
        )
        if assessment.disposition is ActionReadinessDisposition.EXIT_RISK_WARNING:
            chosen[trade_index] = {
                **item,
                "watch_count_before_action": watch_counts.get(trade_index, 0),
                "readiness_reasons": assessment.reasons,
                "imminence_ratio_bps": assessment.imminence_ratio_bps,
            }
        elif assessment.disposition in {
            ActionReadinessDisposition.WATCH,
            ActionReadinessDisposition.DEFEND,
        }:
            watch_counts[trade_index] = watch_counts.get(trade_index, 0) + 1

    return chosen


def _baseline_metrics(
    *,
    trades: list[dict[str, Any]],
    surface: list[dict[str, Any]],
    threshold: Decimal,
) -> Metrics:
    baseline = _baseline_v21(
        trades=trades,
        surface=surface,
        threshold=threshold,
    )
    decorated = {
        index: {
            **item,
            "watch_count_before_action": 0,
        }
        for index, item in baseline.items()
    }
    return _metrics(
        trades=trades,
        chosen=decorated,
        baseline_ids=set(baseline),
    )


def _choose_policy(
    *,
    trades: list[dict[str, Any]],
    surface: list[dict[str, Any]],
    v21_threshold: Decimal,
) -> tuple[dict[str, object] | None, Metrics | None, list[dict[str, object]]]:
    baseline = _baseline_v21(
        trades=trades,
        surface=surface,
        threshold=v21_threshold,
    )
    baseline_metrics = _baseline_metrics(
        trades=trades,
        surface=surface,
        threshold=v21_threshold,
    )
    baseline_ids = set(baseline)

    admitted: list[tuple[Metrics, dict[str, object]]] = []
    audit: list[dict[str, object]] = []

    for survival_ceiling in SURVIVAL_CEILINGS:
        for h1_floor in EXIT_H1_FLOORS:
            for imminence_floor in EXIT_IMMINENCE_FLOORS:
                for margin_floor in EXIT_MARGIN_FLOORS:
                    for velocity_floor in EXIT_VELOCITY_FLOORS:
                        chosen = _select_actions(
                            surface=surface,
                            survival_ceiling=survival_ceiling,
                            h1_floor=h1_floor,
                            imminence_floor=imminence_floor,
                            margin_floor=margin_floor,
                            velocity_floor=velocity_floor,
                        )
                        metrics = _metrics(
                            trades=trades,
                            chosen=chosen,
                            baseline_ids=baseline_ids,
                        )
                        changed = set(chosen) != baseline_ids
                        passed = (
                            changed
                            and metrics.action_count >= MIN_SELECTED_TRADES
                            and metrics.precision >= TRAIN_PRECISION_FLOOR
                            and metrics.winner_mark_rate <= WINNER_MARK_CEILING
                            and metrics.loss_recall >= baseline_metrics.loss_recall
                            and metrics.median_lead_bars is not None
                            and metrics.median_lead_bars >= MIN_MEDIAN_LEAD_BARS
                        )
                        policy = {
                            "survival_ceiling": str(survival_ceiling),
                            "exit_h1_floor_bps": h1_floor,
                            "exit_imminence_floor_bps": imminence_floor,
                            "exit_margin_floor_bps": margin_floor,
                            "exit_velocity_floor_bps": velocity_floor,
                        }
                        audit.append(
                            {
                                **policy,
                                **_payload(metrics),
                                "recall_delta_vs_v21": str(
                                    metrics.loss_recall - baseline_metrics.loss_recall
                                ),
                                "precision_delta_vs_v21": str(
                                    metrics.precision - baseline_metrics.precision
                                ),
                                "winner_mark_delta_vs_v21": str(
                                    metrics.winner_mark_rate
                                    - baseline_metrics.winner_mark_rate
                                ),
                                "admitted": passed,
                            }
                        )
                        if passed:
                            admitted.append((metrics, policy))

    if not admitted:
        return None, None, audit

    metrics, policy = max(
        admitted,
        key=lambda item: (
            item[0].loss_recall,
            item[0].precision,
            -item[0].winner_mark_rate,
            item[0].median_lead_bars or Decimal("0"),
            item[0].true_loss,
            -item[0].false_winner,
        ),
    )
    return policy, metrics, audit


def _window(
    *,
    trades: list[dict[str, Any]],
    surface: list[dict[str, Any]],
    v21_threshold: Decimal,
    policy: dict[str, object],
) -> dict[str, object]:
    baseline = _baseline_v21(
        trades=trades,
        surface=surface,
        threshold=v21_threshold,
    )
    baseline_metrics = _baseline_metrics(
        trades=trades,
        surface=surface,
        threshold=v21_threshold,
    )
    chosen = _select_actions(
        surface=surface,
        survival_ceiling=Decimal(str(policy["survival_ceiling"])),
        h1_floor=int(policy["exit_h1_floor_bps"]),
        imminence_floor=int(policy["exit_imminence_floor_bps"]),
        margin_floor=int(policy["exit_margin_floor_bps"]),
        velocity_floor=int(policy["exit_velocity_floor_bps"]),
    )
    metrics = _metrics(
        trades=trades,
        chosen=chosen,
        baseline_ids=set(baseline),
    )
    passed = (
        metrics.action_count >= MIN_SELECTED_TRADES
        and metrics.precision >= VALIDATION_PRECISION_FLOOR
        and metrics.winner_mark_rate <= WINNER_MARK_CEILING
        and metrics.loss_recall >= baseline_metrics.loss_recall
        and metrics.median_lead_bars is not None
        and metrics.median_lead_bars >= MIN_MEDIAN_LEAD_BARS
    )
    return {
        "sample": len(trades),
        "v21": _payload(baseline_metrics),
        "v27": _payload(metrics),
        "recall_delta_vs_v21": str(
            metrics.loss_recall - baseline_metrics.loss_recall
        ),
        "precision_delta_vs_v21": str(
            metrics.precision - baseline_metrics.precision
        ),
        "winner_mark_delta_vs_v21": str(
            metrics.winner_mark_rate - baseline_metrics.winner_mark_rate
        ),
        "status": "ADMIT_FOR_ECONOMIC_SHADOW" if passed else "REJECT",
    }


def run(v6_json: Path) -> dict[str, object]:
    ledger = json.loads(v6_json.read_text())
    if ledger["identity"] != "QORE_SHARED_VT08_INDEX_STOP_TARGET_DISCRIMINATION_V6":
        raise ValueError("unexpected frozen external falsification ledger identity")

    hazard_model, categories = v21._fit_hazard(ledger)
    train_trades = list(ledger[TRAIN_WINDOW]["rows"])
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
    v21_threshold, _, _ = v21._choose_threshold(
        trades=train_trades,
        probabilities=train_probabilities,
        meta=train_meta,
    )
    if v21_threshold is None:
        raise ValueError("V21 frozen threshold unavailable")

    adverse_models, favorable_models = v26r0b._fit_models(
        trades=train_trades,
        categories=categories,
    )
    surfaces = {
        key: _surface(
            ledger=ledger,
            key=key,
            hazard_model=hazard_model,
            survival_model=survival_model,
            categories=categories,
            adverse_models=adverse_models,
            favorable_models=favorable_models,
        )
        for key in WINDOWS
    }

    policy, train_metrics, policy_audit = _choose_policy(
        trades=surfaces[TRAIN_WINDOW][0],
        surface=surfaces[TRAIN_WINDOW][1],
        v21_threshold=v21_threshold,
    )

    common = {
        "schema": SCHEMA,
        "identity": IDENTITY,
        "source_v6_run": SOURCE_V6_RUN,
        "source_v21_run": SOURCE_V21_RUN,
        "source_v26_r0b_run": SOURCE_V26_R0B_RUN,
        "source_v26_r1_run": SOURCE_V26_R1_RUN,
        "research_only": True,
        "shared_autonomous_model": True,
        "cognition_separated_from_action_readiness": True,
        "watch_and_defend_have_no_execution_authority": True,
        "only_exit_risk_warning_counted_as_hypothetical_intervention": True,
        "dynamic_later_confirmation_allowed": True,
        "multi_horizon_models_fit_on_five_year_only": True,
        "policy_selected_on_five_year_only": True,
        "v21_relational_veto_frozen": True,
        "v21_survival_threshold_control": str(v21_threshold),
        "fresh_holdout_opened": False,
        "runtime_current_position_pnl_used": False,
        "runtime_terminal_outcome_used": False,
        "runtime_future_market_used": False,
        "runtime_symbol_identity_used": False,
        "runtime_market_identity_used": False,
        "runtime_trader_identity_used": False,
        "runtime_methodology_identity_used": False,
        "runtime_calendar_identity_used": False,
        "runtime_fold_identity_used": False,
        "sizing_used": False,
        "risk_weighting_used": False,
        "runtime_actuation": False,
        "closed_outcome_and_exit_distance_used_offline_for_training_and_scoring_only": True,
        "policy_audit": policy_audit,
    }

    if policy is None or train_metrics is None:
        return {
            **common,
            "selected_policy": None,
            "windows": {},
            "validation_pass": False,
            "scientific_status": "REJECT",
            "rejection_reason": (
                "NO_FIVE_YEAR_DYNAMIC_READINESS_POLICY_PRESERVES_V21_RECALL_AND_SAFETY"
            ),
        }

    windows = {
        key: _window(
            trades=surfaces[key][0],
            surface=surfaces[key][1],
            v21_threshold=v21_threshold,
            policy=policy,
        )
        for key in WINDOWS
    }
    all_safe = all(
        windows[key]["status"] == "ADMIT_FOR_ECONOMIC_SHADOW"
        for key in WINDOWS
    )
    held_improvement = any(
        (
            Decimal(str(windows[key]["recall_delta_vs_v21"])) > 0
            or Decimal(str(windows[key]["precision_delta_vs_v21"])) > 0
            or Decimal(str(windows[key]["winner_mark_delta_vs_v21"])) < 0
        )
        for key in VALIDATION_WINDOWS
    )
    validation_pass = all_safe and held_improvement

    return {
        **common,
        "policy_frozen_across_validation_windows": True,
        "selected_policy": policy,
        "train_selected_metrics": _payload(train_metrics),
        "pass_law": {
            "loss_recall": "V27 >= V21 in every consumed window",
            "training_precision_floor": str(TRAIN_PRECISION_FLOOR),
            "validation_precision_floor": str(VALIDATION_PRECISION_FLOOR),
            "winner_mark_ceiling": str(WINNER_MARK_CEILING),
            "minimum_action_count": MIN_SELECTED_TRADES,
            "minimum_median_lead_bars": str(MIN_MEDIAN_LEAD_BARS),
            "held_window_improvement_required": True,
        },
        "windows": windows,
        "held_window_improvement": held_improvement,
        "validation_pass": validation_pass,
        "scientific_status": "PASS" if validation_pass else "REJECT",
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--v6-json", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()

    payload = run(args.v6_json)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    print(
        json.dumps(
            {
                "identity": payload["identity"],
                "scientific_status": payload["scientific_status"],
                "validation_pass": payload["validation_pass"],
                "rejection_reason": payload.get("rejection_reason"),
                "selected_policy": payload.get("selected_policy"),
                "windows": payload.get("windows"),
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()

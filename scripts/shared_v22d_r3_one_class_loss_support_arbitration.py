"""V22-D R3 one-class loss-support arbitration for Shared.

R2 showed that static recoverability veto rules remove too many true losses.
R3 changes the question: do V21 INSUFFICIENT false-winner marks fall outside
the causal feature support occupied by historically selected true losses?

Only the five-year consumed window is used to fit the support reference.  Three
predeclared one-class support tests are frozen before validation:

- AXIS_ENVELOPE: candidate must remain inside the per-feature train-loss range.
- CENTROID_RADIUS: candidate must remain inside the maximum standardized
  train-loss radius.
- KNN_SUPPORT: candidate must remain inside the maximum leave-one-out
  train-loss nearest-neighbor distance.

A veto is allowed only when the candidate lies outside the corresponding
true-loss support.  Consensus variants are also reported.  These are veto-only
winner-protection experiments: they cannot create TARGET/WINNER decisions.

No symbol, market, trader, methodology, calendar, fold, current PnL, sizing,
risk, order or broker identity is used at inference. CLOSED outcomes are used
offline only to construct the five-year loss-support reference and to score
consumed windows. Fresh holdout remains closed.
"""

# ruff: noqa: E501,I001

from __future__ import annotations

import argparse
import json
from decimal import Decimal
from pathlib import Path
from statistics import median
from typing import Any

import numpy as np
import shared_relational_adversity_challenge_survival_v21 as v21
from sklearn.neighbors import NearestNeighbors
from sklearn.preprocessing import StandardScaler

from qore.infrastructure.core_stack_v2.adversity_challenge_intelligence import (
    AdversityChallengeState,
)

IDENTITY = "QORE_SHARED_V22D_R3_ONE_CLASS_LOSS_SUPPORT_ARBITRATION"
SCHEMA = "qore.shared.v22d_r3_one_class_loss_support_arbitration"

SOURCE_V6_RUN = 36131607443
SOURCE_V21_RUN = 36156421332
SOURCE_V22D_R1_RUN = 36171655958
SOURCE_V22D_R2_RUN = 36175777522

WINDOWS = (v21.TRAIN_WINDOW, *v21.VALIDATION_WINDOWS)

PRECISION_FLOOR = Decimal("0.90")
WINNER_MARK_CEILING = Decimal("0.01")
MIN_SELECTED_TRADES = 20
MIN_MEDIAN_LEAD_BARS = Decimal("1")

FEATURE_NAMES = (
    "path_recovery_persistence_bps",
    "trajectory_balance_bps",
    "trajectory_deterioration_pressure_bps",
    "trajectory_deterioration_velocity_bps",
    "path_balance_bps",
    "environment_balance_bps",
    "terminal_minus_winner_protection_bps",
    "risk_separation_margin_bps",
    "hazard_adverse",
    "hazard_margin",
    "hazard_stop",
    "survival_probability",
)

METHODS = (
    "AXIS_ENVELOPE",
    "CENTROID_RADIUS",
    "KNN_SUPPORT",
    "CONSENSUS_ANY_TWO",
    "CONSENSUS_ALL_THREE",
)


def _ratio(n: int, d: int) -> Decimal:
    return Decimal("0") if d <= 0 else Decimal(n) / Decimal(d)


def _hazard_map(
    *,
    hazard_model: Any,
    categories: dict[str, tuple[str, ...]],
    trades: list[dict[str, Any]],
) -> dict[tuple[int, str], dict[str, float]]:
    x_rows, _, _, meta = v21.v20._dataset(trades, categories)
    probability_rows = hazard_model.predict_proba(x_rows)
    classes = tuple(str(value) for value in hazard_model.classes_)
    result: dict[tuple[int, str], dict[str, float]] = {}
    for values, (trade_index, row) in zip(probability_rows, meta, strict=True):
        p = {cause: 0.0 for cause in v21.v20.CAUSES}
        for label, probability in zip(classes, values, strict=True):
            p[label] = float(probability)
        result[(trade_index, str(row["as_of"]))] = p
    return result


def _selected(
    *,
    hazard_model: Any,
    survival_model: Any,
    categories: dict[str, tuple[str, ...]],
    trades: list[dict[str, Any]],
    threshold: Decimal,
) -> list[dict[str, Any]]:
    x_rows, _, _, meta = v21._candidate_dataset(
        hazard_model=hazard_model,
        categories=categories,
        trades=trades,
    )
    survival_probabilities = survival_model.predict_proba(x_rows)[:, 1]
    hazards = _hazard_map(
        hazard_model=hazard_model,
        categories=categories,
        trades=trades,
    )
    chosen: dict[int, dict[str, Any]] = {}
    limit = float(threshold)

    for probability, item in zip(survival_probabilities, meta, strict=True):
        trade_index = int(item["trade_index"])
        if trade_index in chosen:
            continue
        if v21._relational_veto(item["challenge"]):
            continue
        if float(probability) > limit:
            continue

        row = item["row"]
        hazard = hazards[(trade_index, str(row["as_of"]))]
        adverse = hazard[v21.v20.CAUSE_STOP] + hazard[v21.v20.CAUSE_TERMINAL]
        favorable = hazard[v21.v20.CAUSE_TARGET] + hazard[v21.v20.CAUSE_RECOVERY]
        chosen[trade_index] = {
            "trade_index": trade_index,
            "actual": str(trades[trade_index]["actual"]),
            "row": row,
            "challenge": item["challenge"],
            "survival_probability": float(probability),
            "hazard_adverse": adverse,
            "hazard_margin": adverse - favorable,
            "hazard_stop": hazard[v21.v20.CAUSE_STOP],
        }
    return list(chosen.values())


def _feature_vector(item: dict[str, Any]) -> np.ndarray:
    row = item["row"]
    values = {
        "path_recovery_persistence_bps": int(row["path_recovery_persistence_bps"]) / 10_000.0,
        "trajectory_balance_bps": (
            int(row["trajectory_support_bps"]) - int(row["trajectory_adversity_bps"])
        ) / 10_000.0,
        "trajectory_deterioration_pressure_bps": int(
            row["trajectory_deterioration_pressure_bps"]
        ) / 10_000.0,
        "trajectory_deterioration_velocity_bps": int(
            row["trajectory_deterioration_velocity_bps"]
        ) / 10_000.0,
        "path_balance_bps": (
            int(row["path_support_bps"]) - int(row["path_adverse_dominance_bps"])
        ) / 10_000.0,
        "environment_balance_bps": (
            int(row["environment_support_bps"]) - int(row["environment_adverse_bps"])
        ) / 10_000.0,
        "terminal_minus_winner_protection_bps": (
            int(row["path_terminal_failure_risk_bps"])
            - int(row["path_winner_protection_bps"])
        ) / 10_000.0,
        "risk_separation_margin_bps": int(row["risk_separation_margin_bps"]) / 10_000.0,
        "hazard_adverse": float(item["hazard_adverse"]),
        "hazard_margin": float(item["hazard_margin"]),
        "hazard_stop": float(item["hazard_stop"]),
        "survival_probability": float(item["survival_probability"]),
    }
    return np.asarray([values[name] for name in FEATURE_NAMES], dtype=np.float64)


def _fit_support(train_selected: list[dict[str, Any]]) -> dict[str, Any]:
    reference_items = [
        item
        for item in train_selected
        if item["actual"] == "LOSS"
        and item["challenge"].state == AdversityChallengeState.INSUFFICIENT
    ]
    if len(reference_items) < 10:
        raise ValueError("insufficient train true-loss support reference")

    raw = np.vstack([_feature_vector(item) for item in reference_items])
    scaler = StandardScaler()
    scaled = scaler.fit_transform(raw)

    axis_min = scaled.min(axis=0)
    axis_max = scaled.max(axis=0)
    centroid = scaled.mean(axis=0)
    radii = np.linalg.norm(scaled - centroid, axis=1)
    centroid_radius = float(radii.max())

    nn = NearestNeighbors(n_neighbors=2, metric="euclidean")
    nn.fit(scaled)
    distances, _ = nn.kneighbors(scaled)
    loo_nearest = distances[:, 1]
    knn_radius = float(loo_nearest.max())

    return {
        "reference_items": reference_items,
        "reference_raw": raw,
        "reference_scaled": scaled,
        "scaler": scaler,
        "axis_min": axis_min,
        "axis_max": axis_max,
        "centroid": centroid,
        "centroid_radius": centroid_radius,
        "knn_radius": knn_radius,
        "knn": nn,
    }


def _outside_votes(
    *,
    item: dict[str, Any],
    support: dict[str, Any],
    train_reference_index: int | None,
) -> dict[str, bool]:
    x = support["scaler"].transform(_feature_vector(item).reshape(1, -1))[0]
    outside_axis = bool(
        np.any(x < support["axis_min"]) or np.any(x > support["axis_max"])
    )
    outside_centroid = bool(
        np.linalg.norm(x - support["centroid"]) > support["centroid_radius"]
    )

    if train_reference_index is None:
        distance = float(support["knn"].kneighbors(x.reshape(1, -1), n_neighbors=1)[0][0, 0])
    else:
        distances = support["knn"].kneighbors(x.reshape(1, -1), n_neighbors=2)[0][0]
        distance = float(distances[1])
    outside_knn = distance > support["knn_radius"]

    votes = sum((outside_axis, outside_centroid, outside_knn))
    return {
        "AXIS_ENVELOPE": outside_axis,
        "CENTROID_RADIUS": outside_centroid,
        "KNN_SUPPORT": outside_knn,
        "CONSENSUS_ANY_TWO": votes >= 2,
        "CONSENSUS_ALL_THREE": votes == 3,
    }


def _metrics(
    *,
    trades: list[dict[str, Any]],
    selected: list[dict[str, Any]],
    method: str,
    support: dict[str, Any],
    is_train: bool,
) -> tuple[v21.Metrics, dict[str, int]]:
    kept: dict[int, dict[str, Any]] = {}
    vetoed_true_loss = 0
    vetoed_false_winner = 0
    evaluated_insufficient = 0

    reference_lookup = {
        int(item["trade_index"]): index
        for index, item in enumerate(support["reference_items"])
    }

    for item in selected:
        trade_index = int(item["trade_index"])
        veto = False
        if item["challenge"].state == AdversityChallengeState.INSUFFICIENT:
            evaluated_insufficient += 1
            reference_index = (
                reference_lookup.get(trade_index)
                if is_train and item["actual"] == "LOSS"
                else None
            )
            veto = _outside_votes(
                item=item,
                support=support,
                train_reference_index=reference_index,
            )[method]
        if veto:
            if item["actual"] == "LOSS":
                vetoed_true_loss += 1
            else:
                vetoed_false_winner += 1
            continue
        kept[trade_index] = item

    losses = sum(trade["actual"] == "LOSS" for trade in trades)
    winners = sum(trade["actual"] == "WIN" for trade in trades)
    true_loss = [i for i in kept if trades[i]["actual"] == "LOSS"]
    false_winner = [i for i in kept if trades[i]["actual"] == "WIN"]
    leads = [
        int(kept[i]["row"]["bars_before_canonical_exit"])
        for i in true_loss
    ]
    metrics = v21.Metrics(
        selected=len(kept),
        true_loss=len(true_loss),
        false_winner=len(false_winner),
        precision=_ratio(len(true_loss), len(kept)),
        loss_recall=_ratio(len(true_loss), losses),
        winner_mark_rate=_ratio(len(false_winner), winners),
        median_lead_bars=None if not leads else Decimal(str(median(leads))),
        relational_veto_count=0,
        survival_veto_count=0,
    )
    audit = {
        "evaluated_insufficient": evaluated_insufficient,
        "vetoed_true_loss": vetoed_true_loss,
        "vetoed_false_winner": vetoed_false_winner,
    }
    return metrics, audit


def _baseline_metrics(
    *,
    trades: list[dict[str, Any]],
    selected: list[dict[str, Any]],
) -> v21.Metrics:
    chosen = {int(item["trade_index"]): item for item in selected}
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


def _window(
    *,
    trades: list[dict[str, Any]],
    selected: list[dict[str, Any]],
    support: dict[str, Any],
    is_train: bool,
) -> dict[str, object]:
    baseline = _baseline_metrics(trades=trades, selected=selected)
    methods: dict[str, object] = {}
    for method in METHODS:
        metrics, audit = _metrics(
            trades=trades,
            selected=selected,
            method=method,
            support=support,
            is_train=is_train,
        )
        passed = (
            metrics.selected >= MIN_SELECTED_TRADES
            and metrics.precision >= PRECISION_FLOOR
            and metrics.winner_mark_rate <= WINNER_MARK_CEILING
            and metrics.loss_recall >= baseline.loss_recall
            and metrics.median_lead_bars is not None
            and metrics.median_lead_bars >= MIN_MEDIAN_LEAD_BARS
        )
        methods[method] = {
            "metrics": v21._payload(metrics),
            "audit": audit,
            "recall_delta_vs_v21": str(metrics.loss_recall - baseline.loss_recall),
            "precision_delta_vs_v21": str(metrics.precision - baseline.precision),
            "winner_mark_delta_vs_v21": str(
                metrics.winner_mark_rate - baseline.winner_mark_rate
            ),
            "status": "ADMIT" if passed else "REJECT",
        }
    return {
        "sample": len(trades),
        "v21": v21._payload(baseline),
        "methods": methods,
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

    selected_by_window = {
        key: _selected(
            hazard_model=hazard_model,
            survival_model=survival_model,
            categories=categories,
            trades=list(ledger[key]["rows"]),
            threshold=threshold,
        )
        for key in WINDOWS
    }
    support = _fit_support(selected_by_window[v21.TRAIN_WINDOW])

    windows = {
        key: _window(
            trades=list(ledger[key]["rows"]),
            selected=selected_by_window[key],
            support=support,
            is_train=key == v21.TRAIN_WINDOW,
        )
        for key in WINDOWS
    }
    admitted_methods = [
        method
        for method in METHODS
        if all(
            windows[key]["methods"][method]["status"] == "ADMIT"
            for key in WINDOWS
        )
    ]

    return {
        "schema": SCHEMA,
        "identity": IDENTITY,
        "source_v6_run": SOURCE_V6_RUN,
        "source_v21_run": SOURCE_V21_RUN,
        "source_v22d_r1_run": SOURCE_V22D_R1_RUN,
        "source_v22d_r2_run": SOURCE_V22D_R2_RUN,
        "research_only": True,
        "shared_autonomous_model": True,
        "decision_policy_changed": False,
        "five_year_true_loss_support_only": True,
        "support_reference_count": len(support["reference_items"]),
        "feature_names": FEATURE_NAMES,
        "predeclared_methods": METHODS,
        "support_parameters": {
            "centroid_radius": str(support["centroid_radius"]),
            "knn_leave_one_out_radius": str(support["knn_radius"]),
        },
        "veto_only_cannot_create_target_or_winner": True,
        "v21_survival_threshold_frozen": str(threshold),
        "validation_windows_not_used_to_fit_support": True,
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
        "closed_outcome_used_offline_for_loss_support_and_scoring_only": True,
        "pass_law": {
            "loss_recall": "method >= V21 in every consumed window",
            "precision_floor": str(PRECISION_FLOOR),
            "winner_mark_ceiling": str(WINNER_MARK_CEILING),
            "minimum_selected_trades": MIN_SELECTED_TRADES,
            "minimum_median_lead_bars": str(MIN_MEDIAN_LEAD_BARS),
        },
        "admitted_methods": admitted_methods,
        "validation_pass": bool(admitted_methods),
        "scientific_status": "PASS" if admitted_methods else "REJECT",
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
        "admitted_methods": payload["admitted_methods"],
        "support_reference_count": payload["support_reference_count"],
        "support_parameters": payload["support_parameters"],
        "windows": payload["windows"],
    }, sort_keys=True))


if __name__ == "__main__":
    main()

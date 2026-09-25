"""V9 consumed-evidence competing-risk probability calibration for Shared.

This is an offline research layer. It trains only on the consumed 5Y VT08
falsification surface and evaluates the frozen model/threshold unchanged on
recent-2Y and R66 consumed evidence.

The model estimates the eventual STOP-before-TARGET probability from causal
point-in-time Shared state. It does not receive realized outcome, future bars,
sizing, risk budget, stop/target mutation, trader-specific cognition, or
execution inputs at inference time.

No runtime actuation is authorized by this script.
"""
from __future__ import annotations

import argparse
import json
from collections import defaultdict
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from statistics import median
from typing import Any

import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score

IDENTITY = "QORE_SHARED_VT08_COMPETING_RISK_CALIBRATION_V9"
SCHEMA = "qore.shared.vt08_competing_risk_calibration.v9"

TRAIN_WINDOW = "five_year"
VALIDATION_WINDOWS = ("recent_two_year", "r66_consumed_failed_holdout")

MODEL_C = 0.05
MODEL_MAX_ITER = 2000
TRAIN_PRECISION_FLOOR = Decimal("0.97")
TRAIN_WINNER_MARK_CEILING = Decimal("0.005")
VALIDATION_PRECISION_FLOOR = Decimal("0.95")
VALIDATION_WINNER_MARK_CEILING = Decimal("0.005")
MIN_MEDIAN_LEAD_BARS = Decimal("1")
MIN_SELECTED_TRADES = 10
THRESHOLD_START = Decimal("0.60")
THRESHOLD_STOP = Decimal("0.99")
THRESHOLD_STEP = Decimal("0.005")

PATH_STATES = (
    "CONTESTED",
    "ADVERSE_DOMINANCE",
    "FAILURE_RISK",
    "RECOVERING",
    "HEALTHY_PULLBACK",
    "FAVORABLE_EXPANSION",
)
RECOVERY_STATES = (
    "RECOVERY_FAILED",
    "RECOVERY_PENDING",
    "RECOVERY_ACTIVE",
    "RECOVERY_RESTORED",
    "NOT_TESTED",
)

FEATURE_NAMES = (
    "stop_formation",
    "stop_hazard",
    "target_hazard",
    "recovery_strength",
    "uncertainty",
    "path_support",
    "path_adverse_dominance",
    "path_adverse_persistence",
    "path_recovery_persistence",
    "path_winner_protection",
    "path_terminal_failure",
    "current_position_r",
    "trade_age",
    *(f"path_state__{state}" for state in PATH_STATES),
    *(f"recovery_state__{state}" for state in RECOVERY_STATES),
)


@dataclass(frozen=True, slots=True)
class TradeDecisionMetrics:
    selected: int
    true_loss: int
    false_winner: int
    precision: Decimal
    loss_recall: Decimal
    winner_mark_rate: Decimal
    median_lead_bars: Decimal | None


def _d(value: object) -> Decimal:
    return Decimal(str(value))


def _ratio(n: int, d: int) -> Decimal:
    if d <= 0:
        return Decimal("0")
    return Decimal(n) / Decimal(d)


def _clip(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def _feature_vector(row: dict[str, Any]) -> list[float]:
    vector = [
        int(row["stop_formation_bps"]) / 10_000.0,
        int(row["stop_hazard_proxy_bps"]) / 10_000.0,
        int(row["target_hazard_proxy_bps"]) / 10_000.0,
        int(row["recovery_strength_bps"]) / 10_000.0,
        int(row["uncertainty_bps"]) / 10_000.0,
        int(row["path_support_bps"]) / 10_000.0,
        int(row["path_adverse_dominance_bps"]) / 10_000.0,
        int(row["path_adverse_persistence_bps"]) / 10_000.0,
        int(row["path_recovery_persistence_bps"]) / 10_000.0,
        int(row["path_winner_protection_bps"]) / 10_000.0,
        int(row["path_terminal_failure_risk_bps"]) / 10_000.0,
        _clip(float(_d(row["current_position_r"])) / 2.0, -1.0, 1.0),
        min(int(row["bar_index"]), 100) / 100.0,
    ]
    path_state = str(row["path_state"])
    recovery_state = str(row["recovery_challenge_state"])
    vector.extend(1.0 if path_state == state else 0.0 for state in PATH_STATES)
    vector.extend(1.0 if recovery_state == state else 0.0 for state in RECOVERY_STATES)
    return vector


def _eligible_observations(trade: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        row
        for row in trade["observations"]
        if row["stage"] == "PATH"
        and row["path_state"] != "INSUFFICIENT"
    ]


def _observation_dataset(
    trades: list[dict[str, Any]],
) -> tuple[np.ndarray, np.ndarray, np.ndarray, list[tuple[int, dict[str, Any]]]]:
    x_rows: list[list[float]] = []
    labels: list[int] = []
    weights: list[float] = []
    meta: list[tuple[int, dict[str, Any]]] = []
    for trade_index, trade in enumerate(trades):
        observations = _eligible_observations(trade)
        if not observations:
            continue
        weight = 1.0 / float(len(observations))
        label = 1 if trade["actual"] == "LOSS" else 0
        for row in observations:
            x_rows.append(_feature_vector(row))
            labels.append(label)
            weights.append(weight)
            meta.append((trade_index, row))
    return (
        np.asarray(x_rows, dtype=float),
        np.asarray(labels, dtype=int),
        np.asarray(weights, dtype=float),
        meta,
    )


def _weighted_brier(
    probabilities: np.ndarray,
    labels: np.ndarray,
    weights: np.ndarray,
) -> Decimal:
    errors = (probabilities - labels) ** 2
    value = float(np.average(errors, weights=weights))
    return Decimal(str(value))


def _weighted_auc(
    probabilities: np.ndarray,
    labels: np.ndarray,
    weights: np.ndarray,
) -> Decimal | None:
    if len(set(labels.tolist())) < 2:
        return None
    value = roc_auc_score(labels, probabilities, sample_weight=weights)
    return Decimal(str(float(value)))


def _first_crossings(
    *,
    trades: list[dict[str, Any]],
    probabilities: np.ndarray,
    meta: list[tuple[int, dict[str, Any]]],
    threshold: Decimal,
) -> dict[int, tuple[dict[str, Any], Decimal]]:
    selected: dict[int, tuple[dict[str, Any], Decimal]] = {}
    threshold_float = float(threshold)
    for probability, (trade_index, row) in zip(probabilities, meta, strict=True):
        if trade_index in selected or probability < threshold_float:
            continue
        selected[trade_index] = (row, Decimal(str(float(probability))))
    return selected


def _decision_metrics(
    *,
    trades: list[dict[str, Any]],
    selected: dict[int, tuple[dict[str, Any], Decimal]],
) -> TradeDecisionMetrics:
    losses = sum(trade["actual"] == "LOSS" for trade in trades)
    winners = sum(trade["actual"] == "WIN" for trade in trades)
    true_loss = [
        (index, value)
        for index, value in selected.items()
        if trades[index]["actual"] == "LOSS"
    ]
    false_winner = [
        (index, value)
        for index, value in selected.items()
        if trades[index]["actual"] == "WIN"
    ]
    leads = [
        int(row["bars_before_canonical_exit"])
        for _, (row, _) in true_loss
    ]
    return TradeDecisionMetrics(
        selected=len(selected),
        true_loss=len(true_loss),
        false_winner=len(false_winner),
        precision=_ratio(len(true_loss), len(selected)),
        loss_recall=_ratio(len(true_loss), losses),
        winner_mark_rate=_ratio(len(false_winner), winners),
        median_lead_bars=None if not leads else Decimal(str(median(leads))),
    )


def _threshold_candidates() -> list[Decimal]:
    values: list[Decimal] = []
    value = THRESHOLD_START
    while value <= THRESHOLD_STOP:
        values.append(value)
        value += THRESHOLD_STEP
    return values


def _choose_training_threshold(
    *,
    trades: list[dict[str, Any]],
    probabilities: np.ndarray,
    meta: list[tuple[int, dict[str, Any]]],
) -> tuple[Decimal | None, TradeDecisionMetrics | None]:
    admitted: list[tuple[TradeDecisionMetrics, Decimal]] = []
    for threshold in _threshold_candidates():
        selected = _first_crossings(
            trades=trades,
            probabilities=probabilities,
            meta=meta,
            threshold=threshold,
        )
        metrics = _decision_metrics(trades=trades, selected=selected)
        if (
            metrics.selected >= MIN_SELECTED_TRADES
            and metrics.precision >= TRAIN_PRECISION_FLOOR
            and metrics.winner_mark_rate <= TRAIN_WINNER_MARK_CEILING
            and metrics.median_lead_bars is not None
            and metrics.median_lead_bars >= MIN_MEDIAN_LEAD_BARS
        ):
            admitted.append((metrics, threshold))
    if not admitted:
        return None, None
    # Maximize loss recall first. Then prefer precision, lead, and higher threshold.
    metrics, threshold = max(
        admitted,
        key=lambda item: (
            item[0].loss_recall,
            item[0].precision,
            item[0].median_lead_bars or Decimal("-1"),
            item[1],
        ),
    )
    return threshold, metrics


def _calibration_bins(
    *,
    probabilities: np.ndarray,
    labels: np.ndarray,
    weights: np.ndarray,
) -> list[dict[str, object]]:
    bins: list[dict[str, object]] = []
    for lower in range(0, 100, 10):
        upper = lower + 10
        low = lower / 100.0
        high = upper / 100.0
        mask = (probabilities >= low) & (
            probabilities <= high if upper == 100 else probabilities < high
        )
        count = int(mask.sum())
        if count == 0:
            bins.append(
                {
                    "lower_bps": lower * 100,
                    "upper_bps": upper * 100,
                    "observations": 0,
                    "weighted_empirical_stop_rate": None,
                }
            )
            continue
        rate = float(np.average(labels[mask], weights=weights[mask]))
        bins.append(
            {
                "lower_bps": lower * 100,
                "upper_bps": upper * 100,
                "observations": count,
                "weighted_empirical_stop_rate": str(Decimal(str(rate))),
            }
        )
    return bins


def _window_evaluation(
    *,
    model: LogisticRegression,
    threshold: Decimal | None,
    window: dict[str, Any],
) -> dict[str, object]:
    trades = list(window["rows"])
    x, y, weights, meta = _observation_dataset(trades)
    probabilities = model.predict_proba(x)[:, 1]
    selected = (
        {}
        if threshold is None
        else _first_crossings(
            trades=trades,
            probabilities=probabilities,
            meta=meta,
            threshold=threshold,
        )
    )
    metrics = _decision_metrics(trades=trades, selected=selected)
    control = window["competing_risk_diagnostics"]
    beats_control_recall = (
        metrics.loss_recall
        > _d(control["terminal_confirmed_loss_recall"])
    )
    admitted = (
        threshold is not None
        and metrics.precision >= VALIDATION_PRECISION_FLOOR
        and metrics.winner_mark_rate <= VALIDATION_WINNER_MARK_CEILING
        and metrics.median_lead_bars is not None
        and metrics.median_lead_bars >= MIN_MEDIAN_LEAD_BARS
        and beats_control_recall
    )
    return {
        "observations": int(len(y)),
        "weighted_brier": str(_weighted_brier(probabilities, y, weights)),
        "weighted_auc": (
            None
            if _weighted_auc(probabilities, y, weights) is None
            else str(_weighted_auc(probabilities, y, weights))
        ),
        "selected_trades": metrics.selected,
        "true_loss": metrics.true_loss,
        "false_winner": metrics.false_winner,
        "precision": str(metrics.precision),
        "loss_recall": str(metrics.loss_recall),
        "winner_mark_rate": str(metrics.winner_mark_rate),
        "median_lead_bars": (
            None
            if metrics.median_lead_bars is None
            else str(metrics.median_lead_bars)
        ),
        "control_v7_loss_recall": control["terminal_confirmed_loss_recall"],
        "beats_control_v7_recall": beats_control_recall,
        "status": "ADMIT_FOR_NEXT_RESEARCH" if admitted else "REJECT",
        "calibration_bins": _calibration_bins(
            probabilities=probabilities,
            labels=y,
            weights=weights,
        ),
    }


def run(v6_json: Path) -> dict[str, object]:
    payload = json.loads(v6_json.read_text())
    train_trades = list(payload[TRAIN_WINDOW]["rows"])
    x_train, y_train, train_weights, train_meta = _observation_dataset(train_trades)

    model = LogisticRegression(
        C=MODEL_C,
        max_iter=MODEL_MAX_ITER,
        solver="lbfgs",
        class_weight=None,
    )
    model.fit(x_train, y_train, sample_weight=train_weights)
    train_probabilities = model.predict_proba(x_train)[:, 1]
    threshold, training_metrics = _choose_training_threshold(
        trades=train_trades,
        probabilities=train_probabilities,
        meta=train_meta,
    )

    windows = {
        key: _window_evaluation(
            model=model,
            threshold=threshold,
            window=payload[key],
        )
        for key in (TRAIN_WINDOW, *VALIDATION_WINDOWS)
    }
    validation_pass = (
        threshold is not None
        and all(
            windows[key]["status"] == "ADMIT_FOR_NEXT_RESEARCH"
            for key in VALIDATION_WINDOWS
        )
    )

    return {
        "schema": SCHEMA,
        "identity": IDENTITY,
        "source_v6_run": 36131607443,
        "source_shared_head": "1a534d0ae735efef4dcbc0c0be4b110ceaa80501",
        "research_only": True,
        "consumed_evidence_only": True,
        "train_window": TRAIN_WINDOW,
        "validation_windows": list(VALIDATION_WINDOWS),
        "outcome_used_for_offline_training_only": True,
        "runtime_outcome_input": False,
        "future_market_input": False,
        "sizing_used": False,
        "risk_weighting_used": False,
        "trailing_used": False,
        "target_extension_used": False,
        "runtime_actuation": False,
        "model": {
            "type": "L2_LOGISTIC_COMPETING_RISK_RESEARCH",
            "c": str(Decimal(str(MODEL_C))),
            "max_iter": MODEL_MAX_ITER,
            "feature_names": list(FEATURE_NAMES),
            "intercept": str(Decimal(str(float(model.intercept_[0])))),
            "coefficients": [
                str(Decimal(str(float(value))))
                for value in model.coef_[0]
            ],
            "threshold": None if threshold is None else str(threshold),
            "training_threshold_policy": {
                "precision_floor": str(TRAIN_PRECISION_FLOOR),
                "winner_mark_rate_ceiling": str(TRAIN_WINNER_MARK_CEILING),
                "median_lead_bars_floor": str(MIN_MEDIAN_LEAD_BARS),
                "minimum_selected_trades": MIN_SELECTED_TRADES,
                "threshold_start": str(THRESHOLD_START),
                "threshold_stop": str(THRESHOLD_STOP),
                "threshold_step": str(THRESHOLD_STEP),
            },
        },
        "training_threshold_metrics": (
            None
            if training_metrics is None
            else {
                "selected": training_metrics.selected,
                "true_loss": training_metrics.true_loss,
                "false_winner": training_metrics.false_winner,
                "precision": str(training_metrics.precision),
                "loss_recall": str(training_metrics.loss_recall),
                "winner_mark_rate": str(training_metrics.winner_mark_rate),
                "median_lead_bars": str(training_metrics.median_lead_bars),
            }
        ),
        "windows": windows,
        "validation_pass": validation_pass,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--v6-json", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    result = run(args.v6_json)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(
        json.dumps(
            {
                "identity": result["identity"],
                "threshold": result["model"]["threshold"],
                "validation_pass": result["validation_pass"],
                "windows": {
                    key: {
                        name: value
                        for name, value in result["windows"][key].items()
                        if name
                        in {
                            "precision",
                            "loss_recall",
                            "winner_mark_rate",
                            "median_lead_bars",
                            "weighted_brier",
                            "weighted_auc",
                            "beats_control_v7_recall",
                            "status",
                        }
                    }
                    for key in result["windows"]
                },
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()

"""V13 temporal-derivative competing-risk research for Shared.

V11 showed that exact path motifs can raise loss recall but overfit validation.
V12 showed that a very coarse invariant grammar becomes too conservative and
selects no additional path. V13 keeps the causal trajectory as continuous
low-dimensional change features instead of memorizing exact motifs.

A fixed L2 logistic model is trained on consumed 5Y observations only. The
representation includes current causal state plus short-horizon deltas and
relation-gap changes. The model and threshold are then frozen unchanged on
recent-2Y and R66 consumed validation.

Outcome is used only as the offline training/scoring label. Runtime inference
inputs remain past-and-current causal observations. No sizing, risk weighting,
order authority, stop/target mutation, trailing, target extension, or LIVE
actuation is present.
"""

# ruff: noqa: E501

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from statistics import median
from typing import Any

import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score

IDENTITY = "QORE_SHARED_VT08_TEMPORAL_DERIVATIVE_COMPETING_RISK_V13"
SCHEMA = "qore.shared.vt08_temporal_derivative_competing_risk.v13"

SOURCE_V6_RUN = 36131607443
SOURCE_V6_SHARED_HEAD = "1a534d0ae735efef4dcbc0c0be4b110ceaa80501"
SOURCE_V9_RUN = 36134739656
SOURCE_V11_RUN = 36140165499
SOURCE_V12_RUN = 36140837830

TRAIN_WINDOW = "five_year"
VALIDATION_WINDOWS = ("recent_two_year", "r66_consumed_failed_holdout")

MODEL_C = 0.05
MODEL_MAX_ITER = 2500
TRAIN_PRECISION_FLOOR = Decimal("0.97")
TRAIN_WINNER_MARK_CEILING = Decimal("0.005")
VALIDATION_PRECISION_FLOOR = Decimal("0.95")
VALIDATION_WINNER_MARK_CEILING = Decimal("0.005")
MIN_MEDIAN_LEAD_BARS = Decimal("1")
MIN_SELECTED_TRADES = 10
THRESHOLD_START = Decimal("0.60")
THRESHOLD_STOP = Decimal("0.995")
THRESHOLD_STEP = Decimal("0.005")

STATIC_FIELDS = (
    "stop_formation_bps",
    "stop_hazard_proxy_bps",
    "target_hazard_proxy_bps",
    "recovery_strength_bps",
    "uncertainty_bps",
    "path_support_bps",
    "path_adverse_dominance_bps",
    "path_adverse_persistence_bps",
    "path_recovery_persistence_bps",
    "path_winner_protection_bps",
    "path_terminal_failure_risk_bps",
    "trajectory_support_bps",
    "trajectory_adversity_bps",
    "trajectory_deterioration_pressure_bps",
    "trajectory_deterioration_velocity_bps",
    "trajectory_recovery_velocity_bps",
    "environment_support_bps",
    "environment_adverse_bps",
    "environment_adverse_velocity_bps",
    "environment_recovery_velocity_bps",
    "futures_terminal_evidence_bps",
    "futures_recovery_evidence_bps",
    "futures_separation_margin_bps",
)

DELTA_FIELDS = (
    "stop_pressure_bps",
    "target_capacity_bps",
    "recovery_strength_bps",
    "path_support_bps",
    "path_adverse_dominance_bps",
    "path_recovery_persistence_bps",
    "path_terminal_failure_risk_bps",
    "trajectory_support_bps",
    "trajectory_adversity_bps",
    "trajectory_deterioration_pressure_bps",
    "trajectory_recovery_velocity_bps",
    "environment_support_bps",
    "environment_adverse_bps",
    "futures_terminal_evidence_bps",
    "futures_recovery_evidence_bps",
)

RELATION_NAMES = (
    "stop_minus_target",
    "terminal_minus_recovery",
    "path_adverse_minus_support",
    "trajectory_adverse_minus_support",
    "environment_adverse_minus_support",
    "futures_terminal_minus_recovery",
)

FEATURE_NAMES = (
    *(f"static__{field}" for field in STATIC_FIELDS),
    "current_position_r",
    "trade_age",
    *RELATION_NAMES,
    *(f"delta1__{field}" for field in DELTA_FIELDS),
    *(f"delta3__{field}" for field in DELTA_FIELDS),
    *(f"relation_delta1__{name}" for name in RELATION_NAMES),
    *(f"relation_delta3__{name}" for name in RELATION_NAMES),
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
    return Decimal("0") if d <= 0 else Decimal(n) / Decimal(d)


def _clip(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def _eligible_observations(trade: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        row
        for row in trade["observations"]
        if row["stage"] == "PATH"
        and row.get("path_state") not in {None, "INSUFFICIENT"}
        and all(field in row for field in STATIC_FIELDS)
        and all(field in row for field in DELTA_FIELDS)
    ]


def _relations(row: dict[str, Any]) -> tuple[int, ...]:
    return (
        int(row["stop_pressure_bps"]) - int(row["target_capacity_bps"]),
        int(row["path_terminal_failure_risk_bps"]) - int(row["recovery_strength_bps"]),
        int(row["path_adverse_dominance_bps"]) - int(row["path_support_bps"]),
        int(row["trajectory_adversity_bps"]) - int(row["trajectory_support_bps"]),
        int(row["environment_adverse_bps"]) - int(row["environment_support_bps"]),
        int(row["futures_terminal_evidence_bps"]) - int(row["futures_recovery_evidence_bps"]),
    )


def _delta(current: dict[str, Any], previous: dict[str, Any], field: str) -> float:
    return (int(current[field]) - int(previous[field])) / 10_000.0


def _feature_vector(
    observations: list[dict[str, Any]],
    index: int,
) -> list[float]:
    current = observations[index]
    previous1 = observations[max(0, index - 1)]
    previous3 = observations[max(0, index - 3)]

    vector = [
        int(current[field]) / 10_000.0
        for field in STATIC_FIELDS
    ]
    vector.extend(
        (
            _clip(float(_d(current["current_position_r"])) / 2.0, -1.0, 1.0),
            min(int(current["bar_index"]), 100) / 100.0,
        )
    )

    current_relations = _relations(current)
    previous1_relations = _relations(previous1)
    previous3_relations = _relations(previous3)
    vector.extend(value / 10_000.0 for value in current_relations)

    vector.extend(
        _delta(current, previous1, field)
        for field in DELTA_FIELDS
    )
    vector.extend(
        _delta(current, previous3, field)
        for field in DELTA_FIELDS
    )
    vector.extend(
        (current_value - previous_value) / 10_000.0
        for current_value, previous_value in zip(
            current_relations,
            previous1_relations,
            strict=True,
        )
    )
    vector.extend(
        (current_value - previous_value) / 10_000.0
        for current_value, previous_value in zip(
            current_relations,
            previous3_relations,
            strict=True,
        )
    )
    return vector


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
        for index, row in enumerate(observations):
            x_rows.append(_feature_vector(observations, index))
            labels.append(label)
            weights.append(weight)
            meta.append((trade_index, row))

    return (
        np.asarray(x_rows, dtype=float),
        np.asarray(labels, dtype=int),
        np.asarray(weights, dtype=float),
        meta,
    )


def _weighted_auc(
    probabilities: np.ndarray,
    labels: np.ndarray,
    weights: np.ndarray,
) -> Decimal | None:
    if len(set(labels.tolist())) < 2:
        return None
    return Decimal(
        str(
            float(
                roc_auc_score(
                    labels,
                    probabilities,
                    sample_weight=weights,
                )
            )
        )
    )


def _weighted_brier(
    probabilities: np.ndarray,
    labels: np.ndarray,
    weights: np.ndarray,
) -> Decimal:
    return Decimal(
        str(
            float(
                np.average(
                    (probabilities - labels) ** 2,
                    weights=weights,
                )
            )
        )
    )


def _first_crossings(
    probabilities: np.ndarray,
    meta: list[tuple[int, dict[str, Any]]],
    threshold: Decimal,
) -> dict[int, tuple[dict[str, Any], Decimal]]:
    selected: dict[int, tuple[dict[str, Any], Decimal]] = {}
    threshold_float = float(threshold)
    for probability, (trade_index, row) in zip(probabilities, meta, strict=True):
        if trade_index in selected or probability < threshold_float:
            continue
        selected[trade_index] = (
            row,
            Decimal(str(float(probability))),
        )
    return selected


def _decision_metrics(
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


def _thresholds() -> list[Decimal]:
    result: list[Decimal] = []
    value = THRESHOLD_START
    while value <= THRESHOLD_STOP:
        result.append(value)
        value += THRESHOLD_STEP
    return result


def _choose_threshold(
    trades: list[dict[str, Any]],
    probabilities: np.ndarray,
    meta: list[tuple[int, dict[str, Any]]],
) -> tuple[Decimal | None, TradeDecisionMetrics | None]:
    admitted: list[tuple[TradeDecisionMetrics, Decimal]] = []
    for threshold in _thresholds():
        selected = _first_crossings(probabilities, meta, threshold)
        metrics = _decision_metrics(trades, selected)
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


def _evaluate(
    *,
    model: LogisticRegression,
    threshold: Decimal | None,
    window: dict[str, Any],
) -> dict[str, object]:
    trades = list(window["rows"])
    x, labels, weights, meta = _observation_dataset(trades)
    probabilities = model.predict_proba(x)[:, 1]
    selected = (
        {}
        if threshold is None
        else _first_crossings(probabilities, meta, threshold)
    )
    metrics = _decision_metrics(trades, selected)
    control_recall = _d(
        window["competing_risk_diagnostics"]["terminal_confirmed_loss_recall"]
    )
    beats_v7 = metrics.loss_recall > control_recall
    admitted = (
        threshold is not None
        and metrics.precision >= VALIDATION_PRECISION_FLOOR
        and metrics.winner_mark_rate <= VALIDATION_WINNER_MARK_CEILING
        and metrics.median_lead_bars is not None
        and metrics.median_lead_bars >= MIN_MEDIAN_LEAD_BARS
        and beats_v7
    )
    auc = _weighted_auc(probabilities, labels, weights)
    return {
        "observations": int(len(labels)),
        "weighted_auc": None if auc is None else str(auc),
        "weighted_brier": str(
            _weighted_brier(probabilities, labels, weights)
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
        "control_v7_loss_recall": str(control_recall),
        "beats_control_v7_recall": beats_v7,
        "status": "ADMIT_FOR_NEXT_RESEARCH" if admitted else "REJECT",
    }


def run(v6_json: Path) -> dict[str, object]:
    payload = json.loads(v6_json.read_text())
    if payload["identity"] != "QORE_SHARED_VT08_INDEX_STOP_TARGET_DISCRIMINATION_V6":
        raise ValueError("unexpected V6 identity")

    train_trades = list(payload[TRAIN_WINDOW]["rows"])
    x_train, labels, weights, meta = _observation_dataset(train_trades)

    model = LogisticRegression(
        C=MODEL_C,
        max_iter=MODEL_MAX_ITER,
        solver="lbfgs",
        class_weight=None,
    )
    model.fit(x_train, labels, sample_weight=weights)
    train_probabilities = model.predict_proba(x_train)[:, 1]
    threshold, training_metrics = _choose_threshold(
        train_trades,
        train_probabilities,
        meta,
    )

    windows = {
        key: _evaluate(
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

    coefficients = [
        {
            "feature": name,
            "coefficient": str(Decimal(str(float(value)))),
        }
        for name, value in zip(
            FEATURE_NAMES,
            model.coef_[0],
            strict=True,
        )
    ]
    coefficients.sort(
        key=lambda item: abs(Decimal(str(item["coefficient"]))),
        reverse=True,
    )

    return {
        "schema": SCHEMA,
        "identity": IDENTITY,
        "source_v6_run": SOURCE_V6_RUN,
        "source_v6_shared_head": SOURCE_V6_SHARED_HEAD,
        "source_v9_run": SOURCE_V9_RUN,
        "source_v11_run": SOURCE_V11_RUN,
        "source_v12_run": SOURCE_V12_RUN,
        "research_only": True,
        "consumed_evidence_only": True,
        "train_window": TRAIN_WINDOW,
        "validation_windows": list(VALIDATION_WINDOWS),
        "temporal_derivative_representation": True,
        "fixed_model_family_before_validation": True,
        "outcome_used_for_offline_training_only": True,
        "runtime_outcome_input": False,
        "future_market_input": False,
        "sizing_used": False,
        "risk_weighting_used": False,
        "trailing_used": False,
        "target_extension_used": False,
        "runtime_actuation": False,
        "model": {
            "type": "L2_LOGISTIC_TEMPORAL_DERIVATIVE_COMPETING_RISK",
            "c": str(Decimal(str(MODEL_C))),
            "max_iter": MODEL_MAX_ITER,
            "feature_names": list(FEATURE_NAMES),
            "intercept": str(
                Decimal(str(float(model.intercept_[0])))
            ),
            "coefficients_by_absolute_magnitude": coefficients,
            "threshold": (
                None if threshold is None else str(threshold)
            ),
            "threshold_policy": {
                "training_precision_floor": str(TRAIN_PRECISION_FLOOR),
                "training_winner_mark_rate_ceiling": str(TRAIN_WINNER_MARK_CEILING),
                "validation_precision_floor": str(VALIDATION_PRECISION_FLOOR),
                "validation_winner_mark_rate_ceiling": str(VALIDATION_WINNER_MARK_CEILING),
                "minimum_median_lead_bars": str(MIN_MEDIAN_LEAD_BARS),
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
    args.out.write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n"
    )
    print(
        json.dumps(
            {
                "identity": result["identity"],
                "validation_pass": result["validation_pass"],
                "threshold": result["model"]["threshold"],
                "training": result["training_threshold_metrics"],
                "windows": result["windows"],
                "top_coefficients": result["model"][
                    "coefficients_by_absolute_magnitude"
                ][:12],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()

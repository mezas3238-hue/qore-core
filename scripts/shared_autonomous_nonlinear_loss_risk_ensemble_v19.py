"""V19 autonomous nonlinear loss-risk ensemble for Shared.

This research asks whether Shared's full resident causal state contains more
generalizable terminal-loss information than the linear V9/V15 probability
surface.

The model is deliberately Shared-first and trader-agnostic:
- no trader, methodology, symbol, calendar, fold or account identity is an
  inference feature;
- no current-position PnL/R multiple is an inference feature;
- no future bar or current-episode terminal outcome is an inference feature;
- only already-causal Shared market/path assessments are used at inference.

Closed historical outcomes are used offline to train and score the model. That
is historical causal memory, not runtime hindsight. The fresh holdout remains
closed. This stage emits research probabilities only and has no trade, sizing,
Risk, order, stop, target or broker authority.
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
import vt08_index_shared_context_conditioned_competing_risk_v15 as v15
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.metrics import roc_auc_score

IDENTITY = "QORE_SHARED_AUTONOMOUS_NONLINEAR_LOSS_RISK_ENSEMBLE_V19"
SCHEMA = "qore.shared.autonomous_nonlinear_loss_risk_ensemble.v19"

SOURCE_V6_RUN = 36131607443
SOURCE_V15_RUN = 36141968333

TRAIN_WINDOW = "five_year"
VALIDATION_WINDOWS = ("recent_two_year", "r66_consumed_failed_holdout")

TRAIN_PRECISION_FLOOR = Decimal("0.95")
VALIDATION_PRECISION_FLOOR = Decimal("0.90")
TRAIN_WINNER_MARK_CEILING = Decimal("0.01")
VALIDATION_WINNER_MARK_CEILING = Decimal("0.01")
MIN_SELECTED_TRADES = 30
MIN_MEDIAN_LEAD_BARS = Decimal("1")

THRESHOLDS = tuple(
    Decimal("0.50") + Decimal("0.005") * index
    for index in range(99)
)

MODEL_PARAMS = {
    "learning_rate": 0.05,
    "max_iter": 180,
    "max_leaf_nodes": 15,
    "max_depth": 4,
    "min_samples_leaf": 80,
    "l2_regularization": 2.0,
    "random_state": 635,
}

BPS_FIELDS = (
    "stop_pressure_bps",
    "stop_formation_bps",
    "target_capacity_bps",
    "recovery_strength_bps",
    "uncertainty_bps",
    "stop_hazard_proxy_bps",
    "target_hazard_proxy_bps",
    "risk_separation_margin_bps",
    "ccrpc_stop_persistence_bps",
    "ccrpc_stop_formation_persistence_bps",
    "ccrpc_target_persistence_bps",
    "ccrpc_recovery_persistence_bps",
    "terminal_failure_stop_formation_bps",
    "terminal_failure_path_risk_bps",
    "terminal_failure_adverse_dominance_bps",
    "terminal_failure_target_hazard_bps",
    "terminal_failure_uncertainty_bps",
    "recovery_challenge_formation_persistence_bps",
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
    "trajectory_deterioration_persistence_bps",
    "trajectory_recovery_persistence_bps",
    "environment_support_bps",
    "environment_adverse_bps",
    "environment_adverse_velocity_bps",
    "environment_recovery_velocity_bps",
    "environment_adverse_persistence_bps",
    "environment_recovery_persistence_bps",
    "geometry_structural_agreement_bps",
    "futures_terminal_evidence_bps",
    "futures_recovery_evidence_bps",
    "futures_separation_margin_bps",
    "futures_horizon_agreement_bps",
)

COUNT_FIELDS = (
    "terminal_relations",
    "target_relations",
    "recovery_relations",
    "recovery_challenge_observations",
    "path_evidence_count",
    "geometry_collapse_horizon_count",
    "geometry_recovery_horizon_count",
    "geometry_resilient_horizon_count",
)

CATEGORICAL_FIELDS = (
    "hypothesis",
    "ccrpc_decision",
    "recovery_challenge_state",
    "terminal_failure_state",
    "path_state",
    "trajectory_state",
    "environment_state",
    "geometry_state",
    "futures_state",
)

RELATION_NAMES = (
    "stop_minus_target",
    "recovery_minus_stop",
    "path_adverse_minus_support",
    "path_recovery_minus_adverse",
    "terminal_minus_winner_protection",
    "trajectory_adverse_minus_support",
    "trajectory_recovery_minus_deterioration",
    "environment_adverse_minus_support",
    "environment_recovery_minus_adverse",
    "futures_terminal_minus_recovery",
)


@dataclass(frozen=True, slots=True)
class Metrics:
    selected: int
    true_loss: int
    false_winner: int
    precision: Decimal
    loss_recall: Decimal
    winner_mark_rate: Decimal
    median_lead_bars: Decimal | None


def _ratio(numerator: int, denominator: int) -> Decimal:
    if denominator <= 0:
        return Decimal("0")
    return Decimal(numerator) / Decimal(denominator)


def _eligible(trade: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        row
        for row in trade["observations"]
        if row["stage"] == "PATH"
        and row["path_state"] != "INSUFFICIENT"
    ]


def _categories(trades: list[dict[str, Any]]) -> dict[str, tuple[str, ...]]:
    values: dict[str, set[str]] = {
        field: set()
        for field in CATEGORICAL_FIELDS
    }
    for trade in trades:
        for row in _eligible(trade):
            for field in CATEGORICAL_FIELDS:
                values[field].add(str(row[field]))
    return {
        field: tuple(sorted(field_values))
        for field, field_values in values.items()
    }


def _relations(row: dict[str, Any]) -> tuple[float, ...]:
    scale = 10_000.0
    return (
        (int(row["stop_pressure_bps"]) - int(row["target_capacity_bps"])) / scale,
        (int(row["recovery_strength_bps"]) - int(row["stop_pressure_bps"])) / scale,
        (int(row["path_adverse_dominance_bps"]) - int(row["path_support_bps"])) / scale,
        (int(row["path_recovery_persistence_bps"]) - int(row["path_adverse_persistence_bps"])) / scale,
        (int(row["path_terminal_failure_risk_bps"]) - int(row["path_winner_protection_bps"])) / scale,
        (int(row["trajectory_adversity_bps"]) - int(row["trajectory_support_bps"])) / scale,
        (int(row["trajectory_recovery_velocity_bps"]) - int(row["trajectory_deterioration_velocity_bps"])) / scale,
        (int(row["environment_adverse_bps"]) - int(row["environment_support_bps"])) / scale,
        (int(row["environment_recovery_velocity_bps"]) - int(row["environment_adverse_velocity_bps"])) / scale,
        (int(row["futures_terminal_evidence_bps"]) - int(row["futures_recovery_evidence_bps"])) / scale,
    )


def _feature_names(categories: dict[str, tuple[str, ...]]) -> tuple[str, ...]:
    names = [
        *(f"bps__{field}" for field in BPS_FIELDS),
        *(f"count__{field}" for field in COUNT_FIELDS),
        "trade_age",
        *RELATION_NAMES,
    ]
    for field in CATEGORICAL_FIELDS:
        names.extend(
            f"{field}__{value}"
            for value in categories[field]
        )
    return tuple(names)


def _vector(
    row: dict[str, Any],
    categories: dict[str, tuple[str, ...]],
) -> list[float]:
    vector = [
        int(row[field]) / 10_000.0
        for field in BPS_FIELDS
    ]
    vector.extend(
        min(int(row[field]), 20) / 20.0
        for field in COUNT_FIELDS
    )
    vector.append(min(int(row["bar_index"]), 120) / 120.0)
    vector.extend(_relations(row))
    for field in CATEGORICAL_FIELDS:
        current = str(row[field])
        vector.extend(
            1.0 if current == value else 0.0
            for value in categories[field]
        )
    return vector


def _dataset(
    trades: list[dict[str, Any]],
    categories: dict[str, tuple[str, ...]],
) -> tuple[np.ndarray, np.ndarray, np.ndarray, list[tuple[int, dict[str, Any]]]]:
    x_rows: list[list[float]] = []
    y_rows: list[int] = []
    weights: list[float] = []
    meta: list[tuple[int, dict[str, Any]]] = []

    for trade_index, trade in enumerate(trades):
        rows = _eligible(trade)
        if not rows:
            continue
        label = int(trade["actual"] == "LOSS")
        observation_weight = 1.0 / len(rows)
        for row in rows:
            x_rows.append(_vector(row, categories))
            y_rows.append(label)
            weights.append(observation_weight)
            meta.append((trade_index, row))

    return (
        np.asarray(x_rows, dtype=np.float64),
        np.asarray(y_rows, dtype=np.int64),
        np.asarray(weights, dtype=np.float64),
        meta,
    )


def _trade_metrics(
    trades: list[dict[str, Any]],
    probabilities: np.ndarray,
    meta: list[tuple[int, dict[str, Any]]],
    threshold: Decimal,
) -> Metrics:
    chosen: dict[int, dict[str, Any]] = {}
    threshold_float = float(threshold)

    for probability, (trade_index, row) in zip(probabilities, meta, strict=True):
        if probability < threshold_float:
            continue
        previous = chosen.get(trade_index)
        if previous is None or int(row["bars_before_canonical_exit"]) > int(
            previous["bars_before_canonical_exit"]
        ):
            chosen[trade_index] = row

    losses = sum(trade["actual"] == "LOSS" for trade in trades)
    winners = sum(trade["actual"] == "WIN" for trade in trades)
    true_loss = [
        index
        for index in chosen
        if trades[index]["actual"] == "LOSS"
    ]
    false_winner = [
        index
        for index in chosen
        if trades[index]["actual"] == "WIN"
    ]
    leads = [
        Decimal(int(chosen[index]["bars_before_canonical_exit"]))
        for index in true_loss
    ]

    return Metrics(
        selected=len(chosen),
        true_loss=len(true_loss),
        false_winner=len(false_winner),
        precision=_ratio(len(true_loss), len(chosen)),
        loss_recall=_ratio(len(true_loss), losses),
        winner_mark_rate=_ratio(len(false_winner), winners),
        median_lead_bars=(
            None if not leads else Decimal(str(median(leads)))
        ),
    )


def _payload(metrics: Metrics) -> dict[str, object]:
    return {
        "selected": metrics.selected,
        "true_loss": metrics.true_loss,
        "false_winner": metrics.false_winner,
        "precision": str(metrics.precision),
        "loss_recall": str(metrics.loss_recall),
        "winner_mark_rate": str(metrics.winner_mark_rate),
        "median_lead_bars": (
            None if metrics.median_lead_bars is None else str(metrics.median_lead_bars)
        ),
    }


def _choose_threshold(
    trades: list[dict[str, Any]],
    probabilities: np.ndarray,
    meta: list[tuple[int, dict[str, Any]]],
) -> tuple[Decimal | None, Metrics | None, list[dict[str, object]]]:
    candidates: list[tuple[Metrics, Decimal]] = []
    audit: list[dict[str, object]] = []

    for threshold in THRESHOLDS:
        metrics = _trade_metrics(trades, probabilities, meta, threshold)
        admitted = (
            metrics.selected >= MIN_SELECTED_TRADES
            and metrics.precision >= TRAIN_PRECISION_FLOOR
            and metrics.winner_mark_rate <= TRAIN_WINNER_MARK_CEILING
            and metrics.median_lead_bars is not None
            and metrics.median_lead_bars >= MIN_MEDIAN_LEAD_BARS
        )
        audit.append(
            {
                "threshold": str(threshold),
                **_payload(metrics),
                "admitted": admitted,
            }
        )
        if admitted:
            candidates.append((metrics, threshold))

    if not candidates:
        return None, None, audit

    metrics, threshold = max(
        candidates,
        key=lambda item: (
            item[0].loss_recall,
            item[0].precision,
            -item[0].winner_mark_rate,
            item[0].median_lead_bars or Decimal("0"),
            item[1],
        ),
    )
    return threshold, metrics, audit


def _window(
    *,
    model: HistGradientBoostingClassifier,
    categories: dict[str, tuple[str, ...]],
    threshold: Decimal | None,
    window: dict[str, Any],
    v15_metrics: dict[str, Any],
) -> dict[str, object]:
    trades = list(window["rows"])
    x_rows, y_rows, weights, meta = _dataset(trades, categories)
    probabilities = model.predict_proba(x_rows)[:, 1]
    auc = roc_auc_score(y_rows, probabilities, sample_weight=weights)

    if threshold is None:
        metrics = Metrics(
            selected=0,
            true_loss=0,
            false_winner=0,
            precision=Decimal("0"),
            loss_recall=Decimal("0"),
            winner_mark_rate=Decimal("0"),
            median_lead_bars=None,
        )
    else:
        metrics = _trade_metrics(trades, probabilities, meta, threshold)

    v15_recall = Decimal(str(v15_metrics["v15_combined"]["loss_recall"]))
    admitted = (
        threshold is not None
        and metrics.selected >= MIN_SELECTED_TRADES
        and metrics.precision >= VALIDATION_PRECISION_FLOOR
        and metrics.winner_mark_rate <= VALIDATION_WINNER_MARK_CEILING
        and metrics.median_lead_bars is not None
        and metrics.median_lead_bars >= MIN_MEDIAN_LEAD_BARS
        and metrics.loss_recall > v15_recall
    )
    return {
        "sample": int(window["sample"]),
        "observations": len(meta),
        "weighted_auc": str(Decimal(str(float(auc)))),
        "v15_loss_recall_control": str(v15_recall),
        "v19": _payload(metrics),
        "beats_v15_loss_recall": metrics.loss_recall > v15_recall,
        "status": "ADMIT_FOR_ECONOMIC_SHADOW" if admitted else "REJECT",
    }


def run(v6_json: Path) -> dict[str, object]:
    ledger = json.loads(v6_json.read_text())
    if ledger["identity"] != "QORE_SHARED_VT08_INDEX_STOP_TARGET_DISCRIMINATION_V6":
        raise ValueError("unexpected frozen external falsification ledger identity")

    train_trades = list(ledger[TRAIN_WINDOW]["rows"])
    categories = _categories(train_trades)
    feature_names = _feature_names(categories)
    x_train, y_train, train_weights, train_meta = _dataset(
        train_trades,
        categories,
    )

    model = HistGradientBoostingClassifier(**MODEL_PARAMS)
    model.fit(x_train, y_train, sample_weight=train_weights)
    train_probabilities = model.predict_proba(x_train)[:, 1]
    threshold, train_metrics, threshold_audit = _choose_threshold(
        train_trades,
        train_probabilities,
        train_meta,
    )

    _, _, v15_windows = v15._fit_v9(ledger)
    windows = {
        key: _window(
            model=model,
            categories=categories,
            threshold=threshold,
            window=ledger[key],
            v15_metrics=v15_windows[key],
        )
        for key in (TRAIN_WINDOW, *VALIDATION_WINDOWS)
    }
    validation_pass = (
        threshold is not None
        and all(
            windows[key]["status"] == "ADMIT_FOR_ECONOMIC_SHADOW"
            for key in VALIDATION_WINDOWS
        )
    )

    return {
        "schema": SCHEMA,
        "identity": IDENTITY,
        "source_v6_run": SOURCE_V6_RUN,
        "source_v15_run": SOURCE_V15_RUN,
        "research_only": True,
        "shared_autonomous_model": True,
        "trader_specific_inference": False,
        "consumed_evidence_only": True,
        "fresh_holdout_opened": False,
        "runtime_current_position_pnl_used": False,
        "runtime_terminal_outcome_used": False,
        "runtime_future_market_used": False,
        "runtime_symbol_identity_used": False,
        "runtime_methodology_identity_used": False,
        "runtime_calendar_identity_used": False,
        "runtime_fold_identity_used": False,
        "sizing_used": False,
        "risk_weighting_used": False,
        "runtime_actuation": False,
        "feature_count": len(feature_names),
        "feature_names": list(feature_names),
        "categorical_vocabulary": {
            key: list(values)
            for key, values in categories.items()
        },
        "model": {
            "type": "HIST_GRADIENT_BOOSTING_CAUSAL_SHARED_RESEARCH",
            **{
                key: str(Decimal(str(value))) if isinstance(value, float) else value
                for key, value in MODEL_PARAMS.items()
            },
            "selected_threshold": None if threshold is None else str(threshold),
            "training_precision_floor": str(TRAIN_PRECISION_FLOOR),
            "validation_precision_floor": str(VALIDATION_PRECISION_FLOOR),
            "training_winner_mark_ceiling": str(TRAIN_WINNER_MARK_CEILING),
            "validation_winner_mark_ceiling": str(VALIDATION_WINNER_MARK_CEILING),
            "minimum_selected_trades": MIN_SELECTED_TRADES,
        },
        "training_threshold_metrics": (
            None if train_metrics is None else _payload(train_metrics)
        ),
        "threshold_audit": threshold_audit,
        "windows": windows,
        "validation_pass": validation_pass,
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
                "threshold": payload["model"]["selected_threshold"],
                "validation_pass": payload["validation_pass"],
                "windows": payload["windows"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()

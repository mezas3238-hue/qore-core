"""V22-A maturity-aware temporal support survival expert for Shared.

V22-R0 showed that V21 false-winner marks are not explained by a single
point-in-time BROAD=SUPPORTIVE label.  The larger structural defect is that
AdversityChallengeAssessment intentionally returns zero-valued relational
metrics while evidence is INSUFFICIENT, even though point-in-time local,
broad and recovery evidence is already causally observable.

V22-A keeps V21 frozen and adds a bounded-past maturity-aware relational
feature head to the independent candidate-survival expert.  Current relational
levels are always represented; temporal deltas and persistence are represented
only from observations available at or before the candidate bar.

This is research-only.  No trader, methodology, symbol, market, calendar,
fold, current PnL, sizing, capital, risk budget, order or broker identity is an
inference feature.  CLOSED outcome is used only offline to train/evaluate the
survival expert.
"""

# ruff: noqa: E501,I001

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from typing import Any

import numpy as np
import shared_relational_adversity_challenge_survival_v21 as v21
from sklearn.ensemble import HistGradientBoostingClassifier

from qore.infrastructure.core_stack_v2.adversity_challenge_intelligence import (
    _broad_reserve,
    _local_pressure,
    _recovery_reserve,
)

IDENTITY = "QORE_SHARED_MATURITY_AWARE_TEMPORAL_SUPPORT_V22A"
SCHEMA = "qore.shared.maturity_aware_temporal_support.v22a"
SOURCE_V6_RUN = 36131607443
SOURCE_V21_RUN = 36156421332
SOURCE_V22_R0_RUN = 36160445959

WINDOWS = (v21.TRAIN_WINDOW, *v21.VALIDATION_WINDOWS)
HISTORY_CAP = 12

MODEL_PARAMS = {
    "learning_rate": 0.04,
    "max_iter": 200,
    "max_leaf_nodes": 12,
    "max_depth": 3,
    "min_samples_leaf": 80,
    "l2_regularization": 4.0,
    "random_state": 635,
}

PRECISION_FLOOR = Decimal("0.90")
WINNER_MARK_CEILING = Decimal("0.01")
MIN_MEDIAN_LEAD_BARS = Decimal("1")
MIN_SELECTED_TRADES = 20


@dataclass(frozen=True, slots=True)
class TemporalPoint:
    local: int
    broad: int
    recovery: int
    environment_state: str


def _clamp_signed(value: int) -> int:
    return max(-10_000, min(10_000, value))


def _delta(values: list[int], lag: int) -> int:
    if len(values) <= lag:
        return 0
    return _clamp_signed(values[-1] - values[-1 - lag])


def _streak(values: list[bool]) -> int:
    count = 0
    for value in reversed(values):
        if not value:
            break
        count += 1
    return count


def _fraction(values: list[bool], width: int) -> float:
    sample = values[-width:]
    return 0.0 if not sample else sum(sample) / len(sample)


def _temporal_point(row: dict[str, Any]) -> TemporalPoint:
    observation = v21._challenge_observation(row)
    return TemporalPoint(
        local=_local_pressure(observation),
        broad=_broad_reserve(observation),
        recovery=_recovery_reserve(observation),
        environment_state=str(row["environment_state"]),
    )


def _history_index(trades: list[dict[str, Any]]) -> dict[int, dict[str, list[TemporalPoint]]]:
    indexed: dict[int, dict[str, list[TemporalPoint]]] = {}
    for trade_index, trade in enumerate(trades):
        rows = v21.v20._eligible(trade)
        points: list[TemporalPoint] = []
        by_as_of: dict[str, list[TemporalPoint]] = {}
        for row in rows:
            points.append(_temporal_point(row))
            by_as_of[str(row["as_of"])] = list(points[-HISTORY_CAP:])
        indexed[trade_index] = by_as_of
    return indexed


def _temporal_features(
    *,
    history: list[TemporalPoint],
) -> list[float]:
    local = [point.local for point in history]
    broad = [point.broad for point in history]
    recovery = [point.recovery for point in history]
    broad_positive = [value > 0 for value in broad]
    named_support = [
        point.environment_state in {"SUPPORTIVE", "STABILIZING"}
        for point in history
    ]

    broad_streak = _streak(broad_positive)
    named_streak = _streak(named_support)
    current_local = local[-1]
    current_broad = broad[-1]
    current_recovery = recovery[-1]
    terminal_snapshot = max(
        0,
        min(
            10_000,
            (
                current_local
                + max(0, -current_broad)
                + max(0, -current_recovery)
            )
            // 2,
        ),
    )
    decoupling_snapshot = max(
        0,
        min(10_000, current_local + max(0, current_broad) - 10_000),
    )

    maturity = min(len(history), HISTORY_CAP) / HISTORY_CAP
    local_norm = current_local / 10_000.0
    broad_positive_norm = max(0, current_broad) / 10_000.0

    return [
        maturity,
        current_local / 10_000.0,
        current_broad / 10_000.0,
        current_recovery / 10_000.0,
        terminal_snapshot / 10_000.0,
        decoupling_snapshot / 10_000.0,
        _delta(local, 1) / 10_000.0,
        _delta(local, 3) / 10_000.0,
        _delta(local, 6) / 10_000.0,
        _delta(broad, 1) / 10_000.0,
        _delta(broad, 3) / 10_000.0,
        _delta(broad, 6) / 10_000.0,
        _delta(recovery, 1) / 10_000.0,
        _delta(recovery, 3) / 10_000.0,
        _delta(recovery, 6) / 10_000.0,
        min(broad_streak, HISTORY_CAP) / HISTORY_CAP,
        min(named_streak, HISTORY_CAP) / HISTORY_CAP,
        _fraction(broad_positive, 4),
        _fraction(broad_positive, 8),
        _fraction(broad_positive, 12),
        1.0 if current_broad > 0 and _delta(broad, 3) < 0 else 0.0,
        1.0 if current_broad > 0 and _delta(broad, 3) >= 0 else 0.0,
        local_norm * broad_positive_norm,
        local_norm * (min(broad_streak, HISTORY_CAP) / HISTORY_CAP),
        max(0.0, -current_recovery / 10_000.0) * broad_positive_norm,
    ]


def _temporal_feature_names() -> tuple[str, ...]:
    return (
        "maturity_observation_fraction",
        "snapshot_local_pressure",
        "snapshot_broad_reserve",
        "snapshot_recovery_reserve",
        "snapshot_terminal_convergence",
        "snapshot_local_broad_decoupling",
        "local_delta_1",
        "local_delta_3",
        "local_delta_6",
        "broad_delta_1",
        "broad_delta_3",
        "broad_delta_6",
        "recovery_delta_1",
        "recovery_delta_3",
        "recovery_delta_6",
        "broad_positive_streak",
        "broad_named_support_streak",
        "broad_positive_fraction_4",
        "broad_positive_fraction_8",
        "broad_positive_fraction_12",
        "broad_positive_and_degrading_3",
        "broad_positive_and_non_degrading_3",
        "local_pressure_x_broad_support",
        "local_pressure_x_support_persistence",
        "negative_recovery_x_broad_support",
    )


def _augment(
    *,
    trades: list[dict[str, Any]],
    x_rows: np.ndarray,
    meta: list[dict[str, Any]],
) -> np.ndarray:
    histories = _history_index(trades)
    temporal: list[list[float]] = []
    for item in meta:
        trade_index = int(item["trade_index"])
        as_of = str(item["row"]["as_of"])
        history = histories[trade_index][as_of]
        temporal.append(_temporal_features(history=history))
    return np.concatenate(
        (x_rows, np.asarray(temporal, dtype=np.float64)),
        axis=1,
    )


def _fit_v22(
    *,
    hazard_model: Any,
    categories: dict[str, tuple[str, ...]],
    trades: list[dict[str, Any]],
) -> tuple[
    HistGradientBoostingClassifier,
    np.ndarray,
    np.ndarray,
    np.ndarray,
    list[dict[str, Any]],
]:
    x_rows, labels, weights, meta = v21._candidate_dataset(
        hazard_model=hazard_model,
        categories=categories,
        trades=trades,
    )
    x_aug = _augment(trades=trades, x_rows=x_rows, meta=meta)
    model = HistGradientBoostingClassifier(**MODEL_PARAMS)
    model.fit(x_aug, labels, sample_weight=weights)
    probabilities = model.predict_proba(x_aug)[:, 1]
    return model, x_aug, labels, probabilities, meta


def _metrics_payload(metrics: v21.Metrics) -> dict[str, object]:
    return v21._payload(metrics)


def _window(
    *,
    hazard_model: Any,
    v21_model: HistGradientBoostingClassifier,
    v22_model: HistGradientBoostingClassifier,
    categories: dict[str, tuple[str, ...]],
    trades: list[dict[str, Any]],
    v21_threshold: Decimal,
    v22_threshold: Decimal,
) -> dict[str, object]:
    x_rows, _, _, meta = v21._candidate_dataset(
        hazard_model=hazard_model,
        categories=categories,
        trades=trades,
    )
    v21_probabilities = v21_model.predict_proba(x_rows)[:, 1]
    x_aug = _augment(trades=trades, x_rows=x_rows, meta=meta)
    v22_probabilities = v22_model.predict_proba(x_aug)[:, 1]

    v21_metrics = v21._metrics(
        trades=trades,
        survival_probabilities=v21_probabilities,
        meta=meta,
        threshold=v21_threshold,
    )
    v22_metrics = v21._metrics(
        trades=trades,
        survival_probabilities=v22_probabilities,
        meta=meta,
        threshold=v22_threshold,
    )
    pass_window = (
        v22_metrics.selected >= MIN_SELECTED_TRADES
        and v22_metrics.precision >= PRECISION_FLOOR
        and v22_metrics.winner_mark_rate <= WINNER_MARK_CEILING
        and v22_metrics.loss_recall >= v21_metrics.loss_recall
        and v22_metrics.median_lead_bars is not None
        and v22_metrics.median_lead_bars >= MIN_MEDIAN_LEAD_BARS
    )
    return {
        "sample": len(trades),
        "candidate_observations": len(meta),
        "v21": _metrics_payload(v21_metrics),
        "v22a": _metrics_payload(v22_metrics),
        "recall_delta_vs_v21": str(v22_metrics.loss_recall - v21_metrics.loss_recall),
        "precision_delta_vs_v21": str(v22_metrics.precision - v21_metrics.precision),
        "winner_mark_delta_vs_v21": str(
            v22_metrics.winner_mark_rate - v21_metrics.winner_mark_rate
        ),
        "status": "ADMIT_FOR_ECONOMIC_SHADOW" if pass_window else "REJECT",
    }


def run(v6_json: Path) -> dict[str, object]:
    ledger = json.loads(v6_json.read_text())
    if ledger["identity"] != "QORE_SHARED_VT08_INDEX_STOP_TARGET_DISCRIMINATION_V6":
        raise ValueError("unexpected frozen external falsification ledger identity")

    hazard_model, categories = v21._fit_hazard(ledger)
    train_trades = list(ledger[v21.TRAIN_WINDOW]["rows"])

    (
        v21_model,
        _,
        _,
        v21_train_probabilities,
        v21_train_meta,
    ) = v21._fit_survival(
        hazard_model=hazard_model,
        categories=categories,
        trades=train_trades,
    )
    v21_threshold, _, _ = v21._choose_threshold(
        trades=train_trades,
        probabilities=v21_train_probabilities,
        meta=v21_train_meta,
    )
    if v21_threshold is None:
        raise ValueError("V21 frozen threshold unavailable")

    (
        v22_model,
        _,
        _,
        v22_train_probabilities,
        v22_train_meta,
    ) = _fit_v22(
        hazard_model=hazard_model,
        categories=categories,
        trades=train_trades,
    )
    v22_threshold, _, threshold_audit = v21._choose_threshold(
        trades=train_trades,
        probabilities=v22_train_probabilities,
        meta=v22_train_meta,
    )
    if v22_threshold is None:
        return {
            "schema": SCHEMA,
            "identity": IDENTITY,
            "research_only": True,
            "validation_pass": False,
            "rejection_reason": "NO_TRAIN_THRESHOLD_MEETS_FROZEN_SAFETY_FLOORS",
            "fresh_holdout_opened": False,
        }

    windows = {
        key: _window(
            hazard_model=hazard_model,
            v21_model=v21_model,
            v22_model=v22_model,
            categories=categories,
            trades=list(ledger[key]["rows"]),
            v21_threshold=v21_threshold,
            v22_threshold=v22_threshold,
        )
        for key in WINDOWS
    }
    validation_pass = all(
        windows[key]["status"] == "ADMIT_FOR_ECONOMIC_SHADOW"
        for key in WINDOWS
    )

    return {
        "schema": SCHEMA,
        "identity": IDENTITY,
        "source_v6_run": SOURCE_V6_RUN,
        "source_v21_run": SOURCE_V21_RUN,
        "source_v22_r0_run": SOURCE_V22_R0_RUN,
        "research_only": True,
        "shared_autonomous_model": True,
        "maturity_aware_relational_features": True,
        "point_in_time_relational_levels_available_when_history_insufficient": True,
        "bounded_past_only": True,
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
        "closed_outcome_used_offline_to_train_survival_expert": True,
        "feature_count_added": len(_temporal_feature_names()),
        "feature_names_added": _temporal_feature_names(),
        "model": {
            "survival_model": "HIST_GRADIENT_BOOSTING_MATURITY_AWARE_SURVIVAL",
            **MODEL_PARAMS,
            "v21_frozen_survival_probability_ceiling": str(v21_threshold),
            "v22a_selected_survival_probability_ceiling": str(v22_threshold),
        },
        "pass_law": {
            "loss_recall": "V22A >= V21 in every consumed window",
            "precision_floor": str(PRECISION_FLOOR),
            "winner_mark_ceiling": str(WINNER_MARK_CEILING),
            "minimum_median_lead_bars": str(MIN_MEDIAN_LEAD_BARS),
            "minimum_selected_trades": MIN_SELECTED_TRADES,
        },
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
                "validation_pass": payload["validation_pass"],
                "model": payload.get("model"),
                "windows": payload.get("windows"),
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()

"""V26-R0B selection-corrected multi-horizon incidence forensics for Shared Core.

V26-R0 successfully learned the multi-horizon incidence surfaces but its
forensic grouping consumed only the first candidate observation per trade.
That did not reproduce frozen V21, which scans forward until the first
candidate that survives both relational and survival vetoes.

R0B preserves V26-R0 models unchanged and corrects only the offline grouping.
It asserts exact parity with frozen V21 selected trade counts before emitting
any forensic result.

V25-R4 falsified static divergence vetoes: they removed false winners but also
removed too many real losses. The remaining problem is timing. At the frozen
V21 decision point, selected true losses are often close to exit while false
winner marks can survive for tens of observations.

R0 therefore learns *time-to-event* without using eventual outcome as a
runtime feature. On five-year consumed evidence only, it fits separate
cause-specific cumulative-incidence models for adverse and favorable canonical
exit within 1, 3, 5 and 10 bars. Runtime inference consumes only current and
prior causal market evidence.

The output is forensic only. It measures whether true-loss marks are more
front-loaded in adverse incidence than false-winner marks across consumed
windows. No decision policy is changed and fresh holdout remains closed.
"""

# ruff: noqa: E501,I001

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any

import numpy as np
import shared_relational_adversity_challenge_survival_v21 as v21
import shared_sequence_event_causal_belief_v23 as v23
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.metrics import roc_auc_score

from qore.infrastructure.core_stack_v2.multi_horizon_incidence import (
    HorizonIncidencePoint,
    build_multi_horizon_incidence_profile,
)

IDENTITY = "QORE_SHARED_V26_R0B_SELECTION_CORRECTED_INCIDENCE_FORENSICS"
SCHEMA = "qore.shared.v26_r0b_selection_corrected_incidence_forensics"

SOURCE_V6_RUN = 36131607443
SOURCE_V21_RUN = 36156421332
SOURCE_V25_R4_RUN = 36201761837
SOURCE_V26_R0_RUN = 36203614522

TRAIN_WINDOW = v21.TRAIN_WINDOW
VALIDATION_WINDOWS = v21.VALIDATION_WINDOWS
WINDOWS = (TRAIN_WINDOW, *VALIDATION_WINDOWS)
HORIZONS = (1, 3, 5, 10)

MODEL_PARAMS = {
    "learning_rate": 0.035,
    "max_iter": 240,
    "max_leaf_nodes": 18,
    "max_depth": 4,
    "min_samples_leaf": 80,
    "l2_regularization": 4.0,
    "random_state": 635,
}

NUMERIC_FIELDS = (
    "adverse_h1_bps",
    "adverse_h3_bps",
    "adverse_h5_bps",
    "adverse_h10_bps",
    "favorable_h1_bps",
    "favorable_h3_bps",
    "favorable_h5_bps",
    "favorable_h10_bps",
    "near_directional_margin_bps",
    "far_directional_margin_bps",
    "adverse_frontload_bps",
    "favorable_frontload_bps",
    "frontload_margin_bps",
    "adverse_curve_gain_bps",
    "favorable_curve_gain_bps",
    "adverse_monotonic_repairs",
    "favorable_monotonic_repairs",
    "bars_before_canonical_exit",
    "survival_probability",
)


def _feature_row(
    rows: list[dict[str, Any]],
    index: int,
    categories: dict[str, tuple[str, ...]],
) -> list[float]:
    return [
        *v21.v19._vector(rows[index], categories),
        *v21.v20._temporal_features(rows, index),
        *v23._sequence_features(rows, index),
    ]


def _dataset(
    trades: list[dict[str, Any]],
    categories: dict[str, tuple[str, ...]],
) -> tuple[
    np.ndarray,
    dict[int, np.ndarray],
    dict[int, np.ndarray],
    np.ndarray,
    list[tuple[int, dict[str, Any]]],
]:
    x_rows: list[list[float]] = []
    adverse_labels = {horizon: [] for horizon in HORIZONS}
    favorable_labels = {horizon: [] for horizon in HORIZONS}
    weights: list[float] = []
    meta: list[tuple[int, dict[str, Any]]] = []

    for trade_index, trade in enumerate(trades):
        rows = v21.v20._eligible(trade)
        if not rows:
            continue
        observation_weight = 1.0 / float(len(rows))
        actual = str(trade["actual"])

        for index, row in enumerate(rows):
            x_rows.append(_feature_row(rows, index, categories))
            remaining = int(row["bars_before_canonical_exit"])
            for horizon in HORIZONS:
                within = 1 <= remaining <= horizon
                adverse_labels[horizon].append(int(within and actual == "LOSS"))
                favorable_labels[horizon].append(int(within and actual == "WIN"))
            weights.append(observation_weight)
            meta.append((trade_index, row))

    return (
        np.asarray(x_rows, dtype=np.float64),
        {
            horizon: np.asarray(values, dtype=np.int64)
            for horizon, values in adverse_labels.items()
        },
        {
            horizon: np.asarray(values, dtype=np.int64)
            for horizon, values in favorable_labels.items()
        },
        np.asarray(weights, dtype=np.float64),
        meta,
    )


def _fit_models(
    *,
    trades: list[dict[str, Any]],
    categories: dict[str, tuple[str, ...]],
) -> tuple[
    dict[int, HistGradientBoostingClassifier],
    dict[int, HistGradientBoostingClassifier],
]:
    x_rows, adverse_labels, favorable_labels, weights, _ = _dataset(
        trades,
        categories,
    )
    adverse_models: dict[int, HistGradientBoostingClassifier] = {}
    favorable_models: dict[int, HistGradientBoostingClassifier] = {}

    for horizon in HORIZONS:
        adverse = HistGradientBoostingClassifier(**MODEL_PARAMS)
        favorable = HistGradientBoostingClassifier(**MODEL_PARAMS)
        adverse.fit(x_rows, adverse_labels[horizon], sample_weight=weights)
        favorable.fit(x_rows, favorable_labels[horizon], sample_weight=weights)
        adverse_models[horizon] = adverse
        favorable_models[horizon] = favorable

    return adverse_models, favorable_models


def _positive_probability(
    model: HistGradientBoostingClassifier,
    x_rows: np.ndarray,
) -> np.ndarray:
    classes = tuple(int(value) for value in model.classes_)
    if 1 not in classes:
        return np.zeros(len(x_rows), dtype=np.float64)
    return model.predict_proba(x_rows)[:, classes.index(1)]


def _auc(
    y_true: np.ndarray,
    scores: np.ndarray,
    weights: np.ndarray,
) -> str | None:
    if len(set(y_true.tolist())) < 2:
        return None
    return str(float(roc_auc_score(y_true, scores, sample_weight=weights)))


def _profile_map(
    *,
    trades: list[dict[str, Any]],
    categories: dict[str, tuple[str, ...]],
    adverse_models: dict[int, HistGradientBoostingClassifier],
    favorable_models: dict[int, HistGradientBoostingClassifier],
) -> tuple[dict[tuple[int, str], dict[str, Any]], dict[str, object]]:
    x_rows, adverse_labels, favorable_labels, weights, meta = _dataset(
        trades,
        categories,
    )
    adverse_probabilities = {
        horizon: _positive_probability(adverse_models[horizon], x_rows)
        for horizon in HORIZONS
    }
    favorable_probabilities = {
        horizon: _positive_probability(favorable_models[horizon], x_rows)
        for horizon in HORIZONS
    }

    result: dict[tuple[int, str], dict[str, Any]] = {}
    for index, (trade_index, row) in enumerate(meta):
        points = tuple(
            HorizonIncidencePoint(
                horizon_bars=horizon,
                adverse_bps=int(
                    round(adverse_probabilities[horizon][index] * 10_000)
                ),
                favorable_bps=int(
                    round(favorable_probabilities[horizon][index] * 10_000)
                ),
            )
            for horizon in HORIZONS
        )
        profile = build_multi_horizon_incidence_profile(points)
        result[(trade_index, str(row["as_of"]))] = {
            "profile": profile,
            "adverse_raw": {
                horizon: int(
                    round(adverse_probabilities[horizon][index] * 10_000)
                )
                for horizon in HORIZONS
            },
            "favorable_raw": {
                horizon: int(
                    round(favorable_probabilities[horizon][index] * 10_000)
                )
                for horizon in HORIZONS
            },
        }

    diagnostics = {
        "adverse_auc": {
            str(horizon): _auc(
                adverse_labels[horizon],
                adverse_probabilities[horizon],
                weights,
            )
            for horizon in HORIZONS
        },
        "favorable_auc": {
            str(horizon): _auc(
                favorable_labels[horizon],
                favorable_probabilities[horizon],
                weights,
            )
            for horizon in HORIZONS
        },
        "positive_rate": {
            "adverse": {
                str(horizon): str(float(adverse_labels[horizon].mean()))
                for horizon in HORIZONS
            },
            "favorable": {
                str(horizon): str(float(favorable_labels[horizon].mean()))
                for horizon in HORIZONS
            },
        },
    }
    return result, diagnostics


def _quantile(values: list[float], fraction: float) -> str | None:
    if not values:
        return None
    ordered = sorted(values)
    if len(ordered) == 1:
        return str(ordered[0])
    position = (len(ordered) - 1) * fraction
    left = int(position)
    right = min(left + 1, len(ordered) - 1)
    weight = position - left
    return str(ordered[left] * (1.0 - weight) + ordered[right] * weight)


def _summary(rows: list[dict[str, Any]]) -> dict[str, object]:
    if not rows:
        return {"count": 0}
    numeric: dict[str, object] = {}
    for field in NUMERIC_FIELDS:
        values = [float(row[field]) for row in rows]
        numeric[field] = {
            "min": str(min(values)),
            "p10": _quantile(values, 0.10),
            "p25": _quantile(values, 0.25),
            "p50": _quantile(values, 0.50),
            "p75": _quantile(values, 0.75),
            "p90": _quantile(values, 0.90),
            "max": str(max(values)),
        }
    return {
        "count": len(rows),
        "numeric": numeric,
        "frontload_sign_counts": dict(
            sorted(
                Counter(
                    "ADVERSE"
                    if int(row["frontload_margin_bps"]) > 0
                    else "FAVORABLE"
                    if int(row["frontload_margin_bps"]) < 0
                    else "CONTESTED"
                    for row in rows
                ).items()
            )
        ),
    }


def _window(
    *,
    ledger: dict[str, Any],
    key: str,
    hazard_model: Any,
    survival_model: Any,
    categories: dict[str, tuple[str, ...]],
    threshold: Any,
    adverse_models: dict[int, HistGradientBoostingClassifier],
    favorable_models: dict[int, HistGradientBoostingClassifier],
) -> dict[str, object]:
    trades = list(ledger[key]["rows"])
    profile_map, diagnostics = _profile_map(
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
    limit = float(threshold)

    candidate_trade_ids: set[int] = set()
    selected: dict[int, dict[str, Any]] = {}
    first_survival_veto: dict[int, dict[str, Any]] = {}

    for survival_probability, item in zip(
        survival_probabilities,
        meta,
        strict=True,
    ):
        trade_index = int(item["trade_index"])
        candidate_trade_ids.add(trade_index)
        if trade_index in selected:
            continue
        if v21._relational_veto(item["challenge"]):
            continue
        record = {
            **item,
            "survival_probability": float(survival_probability),
        }
        if float(survival_probability) <= limit:
            selected[trade_index] = record
        elif trade_index not in first_survival_veto:
            first_survival_veto[trade_index] = record

    survival_vetoed = {
        trade_index: item
        for trade_index, item in first_survival_veto.items()
        if trade_index not in selected
    }

    frozen_metrics = v21._metrics(
        trades=trades,
        survival_probabilities=survival_probabilities,
        meta=meta,
        threshold=threshold,
    )
    selected_true_loss = sum(
        trades[index]["actual"] == "LOSS"
        for index in selected
    )
    selected_false_winner = sum(
        trades[index]["actual"] == "WIN"
        for index in selected
    )
    if (
        len(selected) != frozen_metrics.selected
        or selected_true_loss != frozen_metrics.true_loss
        or selected_false_winner != frozen_metrics.false_winner
    ):
        raise AssertionError(
            "V26-R0B selection does not reproduce frozen V21"
        )

    groups: dict[str, list[dict[str, Any]]] = {
        "selected_true_loss": [],
        "selected_false_winner": [],
        "survival_vetoed_loss": [],
        "survival_vetoed_winner": [],
    }

    for label, chosen in (
        ("selected", selected),
        ("survival_vetoed", survival_vetoed),
    ):
        for trade_index, item in chosen.items():
            actual = str(trades[trade_index]["actual"])
            as_of = str(item["row"]["as_of"])
            incidence = profile_map[(trade_index, as_of)]
            profile = incidence["profile"]
            record = {
                "adverse_h1_bps": profile.adverse_curve_bps[0],
                "adverse_h3_bps": profile.adverse_curve_bps[1],
                "adverse_h5_bps": profile.adverse_curve_bps[2],
                "adverse_h10_bps": profile.adverse_curve_bps[3],
                "favorable_h1_bps": profile.favorable_curve_bps[0],
                "favorable_h3_bps": profile.favorable_curve_bps[1],
                "favorable_h5_bps": profile.favorable_curve_bps[2],
                "favorable_h10_bps": profile.favorable_curve_bps[3],
                "near_directional_margin_bps": (
                    profile.near_directional_margin_bps
                ),
                "far_directional_margin_bps": (
                    profile.far_directional_margin_bps
                ),
                "adverse_frontload_bps": profile.adverse_frontload_bps,
                "favorable_frontload_bps": profile.favorable_frontload_bps,
                "frontload_margin_bps": profile.frontload_margin_bps,
                "adverse_curve_gain_bps": profile.adverse_curve_gain_bps,
                "favorable_curve_gain_bps": profile.favorable_curve_gain_bps,
                "adverse_monotonic_repairs": (
                    profile.adverse_monotonic_repairs
                ),
                "favorable_monotonic_repairs": (
                    profile.favorable_monotonic_repairs
                ),
                "bars_before_canonical_exit": int(
                    item["row"]["bars_before_canonical_exit"]
                ),
                "survival_probability": float(item["survival_probability"]),
            }
            groups[
                f"{label}_{'loss' if actual == 'LOSS' else 'winner'}"
                if label == "survival_vetoed"
                else (
                    "selected_true_loss"
                    if actual == "LOSS"
                    else "selected_false_winner"
                )
            ].append(record)

    return {
        "sample": len(trades),
        "candidate_trade_count": len(candidate_trade_ids),
        "selection_parity_with_frozen_v21": True,
        "frozen_v21_selected": frozen_metrics.selected,
        "frozen_v21_true_loss": frozen_metrics.true_loss,
        "frozen_v21_false_winner": frozen_metrics.false_winner,
        "diagnostics": diagnostics,
        "groups": {
            name: _summary(rows)
            for name, rows in groups.items()
        },
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
    threshold, _, _ = v21._choose_threshold(
        trades=train_trades,
        probabilities=train_probabilities,
        meta=train_meta,
    )
    if threshold is None:
        raise ValueError("V21 frozen threshold unavailable")

    adverse_models, favorable_models = _fit_models(
        trades=train_trades,
        categories=categories,
    )
    windows = {
        key: _window(
            ledger=ledger,
            key=key,
            hazard_model=hazard_model,
            survival_model=survival_model,
            categories=categories,
            threshold=threshold,
            adverse_models=adverse_models,
            favorable_models=favorable_models,
        )
        for key in WINDOWS
    }

    return {
        "schema": SCHEMA,
        "identity": IDENTITY,
        "source_v6_run": SOURCE_V6_RUN,
        "source_v21_run": SOURCE_V21_RUN,
        "source_v25_r4_run": SOURCE_V25_R4_RUN,
        "source_v26_r0_run": SOURCE_V26_R0_RUN,
        "research_only": True,
        "decision_policy_changed": False,
        "selection_corrected_from_v26_r0": True,
        "exact_frozen_v21_selection_parity_required": True,
        "multi_horizon_cumulative_incidence": True,
        "cause_specific_adverse_and_favorable_models": True,
        "horizons_bars": HORIZONS,
        "models_fit_on_five_year_only": True,
        "validation_windows_not_used_for_model_fit": True,
        "runtime_labels_used": False,
        "consumed_evidence_only": True,
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
        "closed_outcome_and_exit_distance_used_offline_for_training_and_grouping_only": True,
        "v21_survival_threshold_frozen": str(threshold),
        "model_params": MODEL_PARAMS,
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
    print(
        json.dumps(
            {
                "identity": payload["identity"],
                "windows": payload["windows"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()

"""V22-B evidence-maturity specialist survival arbitration for Shared.

V22-A falsified the hypothesis that simply adding more temporal-support
features to one global survival model is sufficient.  V22-B tests a structural
alternative: evidence-maturity regimes are different causal inference
problems and should not share one survival expert.

Candidates with AdversityChallengeState.INSUFFICIENT are routed to an early
evidence specialist that sees the frozen V20 point-in-time vector plus
non-zero relational snapshots available at that bar.  Mature candidates are
routed to a mature relational specialist using the frozen V21 representation.

Thresholds are selected jointly on the five-year consumed training window and
then frozen unchanged for recent-two-year and R66 consumed validation.  The
fresh holdout remains closed.

This is research-only.  Runtime inference uses no trader, methodology, symbol,
market, calendar, fold, current PnL, sizing, capital, risk, order or broker
identity.  CLOSED outcomes are used only offline to train and score the
survival specialists.
"""

# ruff: noqa: E501,I001

from __future__ import annotations

import argparse
import json
from collections import Counter
from decimal import Decimal
from pathlib import Path
from statistics import median
from typing import Any

import numpy as np
import shared_relational_adversity_challenge_survival_v21 as v21
from sklearn.ensemble import HistGradientBoostingClassifier

from qore.infrastructure.core_stack_v2.adversity_challenge_intelligence import (
    AdversityChallengeState,
    _broad_reserve,
    _local_pressure,
    _recovery_reserve,
)

IDENTITY = "QORE_SHARED_EVIDENCE_MATURITY_SPECIALIST_SURVIVAL_V22B"
SCHEMA = "qore.shared.evidence_maturity_specialist_survival.v22b"

SOURCE_V6_RUN = 36131607443
SOURCE_V21_RUN = 36156421332
SOURCE_V22_R0_RUN = 36160445959
SOURCE_V22A_RUN = 36165036594

TRAIN_WINDOW = v21.TRAIN_WINDOW
VALIDATION_WINDOWS = v21.VALIDATION_WINDOWS
WINDOWS = (TRAIN_WINDOW, *VALIDATION_WINDOWS)

MODEL_PARAMS = {
    "learning_rate": 0.04,
    "max_iter": 200,
    "max_leaf_nodes": 12,
    "max_depth": 3,
    "min_samples_leaf": 80,
    "l2_regularization": 4.0,
    "random_state": 635,
}

TRAIN_PRECISION_FLOOR = Decimal("0.95")
VALIDATION_PRECISION_FLOOR = Decimal("0.90")
WINNER_MARK_CEILING = Decimal("0.01")
MIN_MEDIAN_LEAD_BARS = Decimal("1")
MIN_SELECTED_TRADES = 20
THRESHOLDS = tuple(
    Decimal("0.005") + Decimal("0.005") * index
    for index in range(40)
)


def _ratio(numerator: int, denominator: int) -> Decimal:
    if denominator <= 0:
        return Decimal("0")
    return Decimal(numerator) / Decimal(denominator)


def _early_snapshot_features(row: dict[str, Any], evidence_count: int) -> list[float]:
    observation = v21._challenge_observation(row)
    local = _local_pressure(observation)
    broad = _broad_reserve(observation)
    recovery = _recovery_reserve(observation)
    decoupling = max(0, min(10_000, local + max(0, broad) - 10_000))
    terminal = max(
        0,
        min(
            10_000,
            (local + max(0, -broad) + max(0, -recovery)) // 2,
        ),
    )
    return [
        local / 10_000.0,
        broad / 10_000.0,
        recovery / 10_000.0,
        decoupling / 10_000.0,
        terminal / 10_000.0,
        min(evidence_count, 4) / 4.0,
        int(row["uncertainty_bps"]) / 10_000.0,
        (int(row["environment_support_bps"]) - int(row["environment_adverse_bps"]))
        / 10_000.0,
        (int(row["futures_recovery_evidence_bps"]) - int(row["futures_terminal_evidence_bps"]))
        / 10_000.0,
        (int(row["path_support_bps"]) - int(row["path_adverse_dominance_bps"]))
        / 10_000.0,
    ]


def _early_feature_names() -> tuple[str, ...]:
    return (
        "early_local_pressure",
        "early_broad_reserve",
        "early_recovery_reserve",
        "early_local_broad_decoupling",
        "early_terminal_snapshot",
        "early_evidence_maturity",
        "early_uncertainty",
        "early_environment_balance",
        "early_futures_balance",
        "early_path_balance",
    )


def _weights_for_meta(meta: list[dict[str, Any]]) -> np.ndarray:
    counts: Counter[int] = Counter(int(item["trade_index"]) for item in meta)
    return np.asarray(
        [1.0 / float(counts[int(item["trade_index"])]) for item in meta],
        dtype=np.float64,
    )


def _specialist_matrices(
    *,
    hazard_model: HistGradientBoostingClassifier,
    categories: dict[str, tuple[str, ...]],
    trades: list[dict[str, Any]],
) -> tuple[
    np.ndarray,
    np.ndarray,
    np.ndarray,
    list[dict[str, Any]],
    np.ndarray,
    np.ndarray,
    np.ndarray,
    list[dict[str, Any]],
]:
    x_rows, labels, _, meta = v21._candidate_dataset(
        hazard_model=hazard_model,
        categories=categories,
        trades=trades,
    )
    base_count = len(v21.v20._feature_names(categories))

    early_x: list[list[float]] = []
    early_y: list[int] = []
    early_meta: list[dict[str, Any]] = []
    mature_x: list[list[float]] = []
    mature_y: list[int] = []
    mature_meta: list[dict[str, Any]] = []

    for vector, label, item in zip(x_rows, labels, meta, strict=True):
        challenge = item["challenge"]
        if challenge.state == AdversityChallengeState.INSUFFICIENT:
            early_x.append(
                [
                    *vector[:base_count].tolist(),
                    *_early_snapshot_features(
                        item["row"],
                        int(challenge.evidence_count),
                    ),
                ]
            )
            early_y.append(int(label))
            early_meta.append(item)
        else:
            mature_x.append(vector.tolist())
            mature_y.append(int(label))
            mature_meta.append(item)

    early_weights = _weights_for_meta(early_meta)
    mature_weights = _weights_for_meta(mature_meta)
    return (
        np.asarray(early_x, dtype=np.float64),
        np.asarray(early_y, dtype=np.int64),
        early_weights,
        early_meta,
        np.asarray(mature_x, dtype=np.float64),
        np.asarray(mature_y, dtype=np.int64),
        mature_weights,
        mature_meta,
    )


def _fit_specialists(
    *,
    hazard_model: HistGradientBoostingClassifier,
    categories: dict[str, tuple[str, ...]],
    trades: list[dict[str, Any]],
) -> tuple[
    HistGradientBoostingClassifier,
    HistGradientBoostingClassifier,
]:
    (
        early_x,
        early_y,
        early_weights,
        _,
        mature_x,
        mature_y,
        mature_weights,
        _,
    ) = _specialist_matrices(
        hazard_model=hazard_model,
        categories=categories,
        trades=trades,
    )
    if len(set(early_y.tolist())) < 2 or len(set(mature_y.tolist())) < 2:
        raise ValueError("specialist training requires both WIN and LOSS classes")

    early_model = HistGradientBoostingClassifier(**MODEL_PARAMS)
    mature_model = HistGradientBoostingClassifier(**MODEL_PARAMS)
    early_model.fit(early_x, early_y, sample_weight=early_weights)
    mature_model.fit(mature_x, mature_y, sample_weight=mature_weights)
    return early_model, mature_model


def _probabilities(
    *,
    hazard_model: HistGradientBoostingClassifier,
    early_model: HistGradientBoostingClassifier,
    mature_model: HistGradientBoostingClassifier,
    categories: dict[str, tuple[str, ...]],
    trades: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], np.ndarray, np.ndarray]:
    x_rows, _, _, meta = v21._candidate_dataset(
        hazard_model=hazard_model,
        categories=categories,
        trades=trades,
    )
    base_count = len(v21.v20._feature_names(categories))
    early_rows: list[list[float]] = []
    early_indices: list[int] = []
    mature_rows: list[list[float]] = []
    mature_indices: list[int] = []

    for index, (vector, item) in enumerate(zip(x_rows, meta, strict=True)):
        challenge = item["challenge"]
        if challenge.state == AdversityChallengeState.INSUFFICIENT:
            early_indices.append(index)
            early_rows.append(
                [
                    *vector[:base_count].tolist(),
                    *_early_snapshot_features(
                        item["row"],
                        int(challenge.evidence_count),
                    ),
                ]
            )
        else:
            mature_indices.append(index)
            mature_rows.append(vector.tolist())

    early_probabilities = np.full(len(meta), np.nan, dtype=np.float64)
    mature_probabilities = np.full(len(meta), np.nan, dtype=np.float64)
    if early_rows:
        values = early_model.predict_proba(
            np.asarray(early_rows, dtype=np.float64)
        )[:, 1]
        early_probabilities[np.asarray(early_indices)] = values
    if mature_rows:
        values = mature_model.predict_proba(
            np.asarray(mature_rows, dtype=np.float64)
        )[:, 1]
        mature_probabilities[np.asarray(mature_indices)] = values
    return meta, early_probabilities, mature_probabilities


def _metrics(
    *,
    trades: list[dict[str, Any]],
    meta: list[dict[str, Any]],
    early_probabilities: np.ndarray,
    mature_probabilities: np.ndarray,
    early_threshold: Decimal,
    mature_threshold: Decimal,
) -> v21.Metrics:
    chosen: dict[int, dict[str, Any]] = {}
    relational_veto_count = 0
    survival_veto_count = 0
    early_limit = float(early_threshold)
    mature_limit = float(mature_threshold)

    for index, item in enumerate(meta):
        trade_index = int(item["trade_index"])
        if trade_index in chosen:
            continue
        challenge = item["challenge"]
        if v21._relational_veto(challenge):
            relational_veto_count += 1
            continue

        if challenge.state == AdversityChallengeState.INSUFFICIENT:
            probability = float(early_probabilities[index])
            limit = early_limit
        else:
            probability = float(mature_probabilities[index])
            limit = mature_limit

        if probability > limit:
            survival_veto_count += 1
            continue
        chosen[trade_index] = item

    losses = sum(trade["actual"] == "LOSS" for trade in trades)
    winners = sum(trade["actual"] == "WIN" for trade in trades)
    true_loss = [index for index in chosen if trades[index]["actual"] == "LOSS"]
    false_winner = [index for index in chosen if trades[index]["actual"] == "WIN"]
    leads = [
        int(chosen[index]["row"]["bars_before_canonical_exit"])
        for index in true_loss
    ]
    return v21.Metrics(
        selected=len(chosen),
        true_loss=len(true_loss),
        false_winner=len(false_winner),
        precision=_ratio(len(true_loss), len(chosen)),
        loss_recall=_ratio(len(true_loss), losses),
        winner_mark_rate=_ratio(len(false_winner), winners),
        median_lead_bars=(
            None if not leads else Decimal(str(median(leads)))
        ),
        relational_veto_count=relational_veto_count,
        survival_veto_count=survival_veto_count,
    )


def _choose_thresholds(
    *,
    trades: list[dict[str, Any]],
    meta: list[dict[str, Any]],
    early_probabilities: np.ndarray,
    mature_probabilities: np.ndarray,
    v21_control: v21.Metrics,
) -> tuple[Decimal | None, Decimal | None, v21.Metrics | None, list[dict[str, object]]]:
    admitted: list[tuple[v21.Metrics, Decimal, Decimal]] = []
    audit: list[dict[str, object]] = []

    for early_threshold in THRESHOLDS:
        for mature_threshold in THRESHOLDS:
            metrics = _metrics(
                trades=trades,
                meta=meta,
                early_probabilities=early_probabilities,
                mature_probabilities=mature_probabilities,
                early_threshold=early_threshold,
                mature_threshold=mature_threshold,
            )
            passed = (
                metrics.selected >= MIN_SELECTED_TRADES
                and metrics.precision >= TRAIN_PRECISION_FLOOR
                and metrics.winner_mark_rate <= WINNER_MARK_CEILING
                and metrics.loss_recall >= v21_control.loss_recall
                and metrics.median_lead_bars is not None
                and metrics.median_lead_bars >= MIN_MEDIAN_LEAD_BARS
            )
            if passed:
                admitted.append((metrics, early_threshold, mature_threshold))
                audit.append(
                    {
                        "early_threshold": str(early_threshold),
                        "mature_threshold": str(mature_threshold),
                        **v21._payload(metrics),
                    }
                )

    if not admitted:
        return None, None, None, audit

    metrics, early_threshold, mature_threshold = max(
        admitted,
        key=lambda item: (
            item[0].loss_recall,
            item[0].precision,
            -item[0].winner_mark_rate,
            item[0].median_lead_bars or Decimal("0"),
            -item[1],
            -item[2],
        ),
    )
    return early_threshold, mature_threshold, metrics, audit


def _v21_metrics(
    *,
    hazard_model: HistGradientBoostingClassifier,
    survival_model: HistGradientBoostingClassifier,
    categories: dict[str, tuple[str, ...]],
    trades: list[dict[str, Any]],
    threshold: Decimal,
) -> v21.Metrics:
    x_rows, _, _, meta = v21._candidate_dataset(
        hazard_model=hazard_model,
        categories=categories,
        trades=trades,
    )
    probabilities = survival_model.predict_proba(x_rows)[:, 1]
    return v21._metrics(
        trades=trades,
        survival_probabilities=probabilities,
        meta=meta,
        threshold=threshold,
    )


def _window(
    *,
    hazard_model: HistGradientBoostingClassifier,
    v21_model: HistGradientBoostingClassifier,
    early_model: HistGradientBoostingClassifier,
    mature_model: HistGradientBoostingClassifier,
    categories: dict[str, tuple[str, ...]],
    trades: list[dict[str, Any]],
    v21_threshold: Decimal,
    early_threshold: Decimal,
    mature_threshold: Decimal,
) -> dict[str, object]:
    v21_metrics = _v21_metrics(
        hazard_model=hazard_model,
        survival_model=v21_model,
        categories=categories,
        trades=trades,
        threshold=v21_threshold,
    )
    meta, early_probabilities, mature_probabilities = _probabilities(
        hazard_model=hazard_model,
        early_model=early_model,
        mature_model=mature_model,
        categories=categories,
        trades=trades,
    )
    v22_metrics = _metrics(
        trades=trades,
        meta=meta,
        early_probabilities=early_probabilities,
        mature_probabilities=mature_probabilities,
        early_threshold=early_threshold,
        mature_threshold=mature_threshold,
    )
    passed = (
        v22_metrics.selected >= MIN_SELECTED_TRADES
        and v22_metrics.precision >= VALIDATION_PRECISION_FLOOR
        and v22_metrics.winner_mark_rate <= WINNER_MARK_CEILING
        and v22_metrics.loss_recall >= v21_metrics.loss_recall
        and v22_metrics.median_lead_bars is not None
        and v22_metrics.median_lead_bars >= MIN_MEDIAN_LEAD_BARS
    )
    return {
        "sample": len(trades),
        "v21": v21._payload(v21_metrics),
        "v22b": v21._payload(v22_metrics),
        "recall_delta_vs_v21": str(v22_metrics.loss_recall - v21_metrics.loss_recall),
        "precision_delta_vs_v21": str(v22_metrics.precision - v21_metrics.precision),
        "winner_mark_delta_vs_v21": str(
            v22_metrics.winner_mark_rate - v21_metrics.winner_mark_rate
        ),
        "status": "ADMIT_FOR_ECONOMIC_SHADOW" if passed else "REJECT",
    }


def _rejection_payload(
    *,
    v21_threshold: Decimal,
    audit: list[dict[str, object]],
) -> dict[str, object]:
    return {
        "schema": SCHEMA,
        "identity": IDENTITY,
        "source_v6_run": SOURCE_V6_RUN,
        "source_v21_run": SOURCE_V21_RUN,
        "source_v22_r0_run": SOURCE_V22_R0_RUN,
        "source_v22a_run": SOURCE_V22A_RUN,
        "research_only": True,
        "shared_autonomous_model": True,
        "evidence_maturity_specialists": True,
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
        "closed_outcome_used_offline_to_train_survival_specialists": True,
        "model": {
            "v21_frozen_survival_probability_ceiling": str(v21_threshold),
            "early_specialist_threshold": None,
            "mature_specialist_threshold": None,
            **MODEL_PARAMS,
        },
        "threshold_audit_admitted": audit,
        "windows": {},
        "validation_pass": False,
        "scientific_status": "REJECT",
        "rejection_reason": "NO_JOINT_TRAIN_THRESHOLDS_PRESERVE_V21_RECALL_AND_SAFETY",
    }


def run(v6_json: Path) -> dict[str, object]:
    ledger = json.loads(v6_json.read_text())
    if ledger["identity"] != "QORE_SHARED_VT08_INDEX_STOP_TARGET_DISCRIMINATION_V6":
        raise ValueError("unexpected frozen external falsification ledger identity")

    hazard_model, categories = v21._fit_hazard(ledger)
    train_trades = list(ledger[TRAIN_WINDOW]["rows"])

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
    v21_train_metrics = v21._metrics(
        trades=train_trades,
        survival_probabilities=v21_train_probabilities,
        meta=v21_train_meta,
        threshold=v21_threshold,
    )

    early_model, mature_model = _fit_specialists(
        hazard_model=hazard_model,
        categories=categories,
        trades=train_trades,
    )
    train_meta, early_probabilities, mature_probabilities = _probabilities(
        hazard_model=hazard_model,
        early_model=early_model,
        mature_model=mature_model,
        categories=categories,
        trades=train_trades,
    )
    (
        early_threshold,
        mature_threshold,
        train_metrics,
        threshold_audit,
    ) = _choose_thresholds(
        trades=train_trades,
        meta=train_meta,
        early_probabilities=early_probabilities,
        mature_probabilities=mature_probabilities,
        v21_control=v21_train_metrics,
    )
    if (
        early_threshold is None
        or mature_threshold is None
        or train_metrics is None
    ):
        return _rejection_payload(
            v21_threshold=v21_threshold,
            audit=threshold_audit,
        )

    windows = {
        key: _window(
            hazard_model=hazard_model,
            v21_model=v21_model,
            early_model=early_model,
            mature_model=mature_model,
            categories=categories,
            trades=list(ledger[key]["rows"]),
            v21_threshold=v21_threshold,
            early_threshold=early_threshold,
            mature_threshold=mature_threshold,
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
        "source_v22a_run": SOURCE_V22A_RUN,
        "research_only": True,
        "shared_autonomous_model": True,
        "evidence_maturity_specialists": True,
        "insufficient_is_routed_to_independent_early_expert": True,
        "mature_relational_evidence_is_routed_to_independent_mature_expert": True,
        "thresholds_selected_on_five_year_only": True,
        "thresholds_frozen_across_validation_windows": True,
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
        "closed_outcome_used_offline_to_train_survival_specialists": True,
        "early_feature_count_added_to_v20": len(_early_feature_names()),
        "early_feature_names_added": _early_feature_names(),
        "model": {
            "early_specialist": "HIST_GRADIENT_BOOSTING_EARLY_EVIDENCE_SURVIVAL",
            "mature_specialist": "HIST_GRADIENT_BOOSTING_MATURE_RELATIONAL_SURVIVAL",
            **MODEL_PARAMS,
            "v21_frozen_survival_probability_ceiling": str(v21_threshold),
            "early_specialist_threshold": str(early_threshold),
            "mature_specialist_threshold": str(mature_threshold),
        },
        "train_v21": v21._payload(v21_train_metrics),
        "train_v22b": v21._payload(train_metrics),
        "pass_law": {
            "loss_recall": "V22B >= V21 in every consumed window",
            "training_precision_floor": str(TRAIN_PRECISION_FLOOR),
            "validation_precision_floor": str(VALIDATION_PRECISION_FLOOR),
            "winner_mark_ceiling": str(WINNER_MARK_CEILING),
            "minimum_median_lead_bars": str(MIN_MEDIAN_LEAD_BARS),
            "minimum_selected_trades": MIN_SELECTED_TRADES,
        },
        "threshold_audit_admitted": threshold_audit,
        "windows": windows,
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
                "validation_pass": payload["validation_pass"],
                "scientific_status": payload.get("scientific_status"),
                "rejection_reason": payload.get("rejection_reason"),
                "model": payload.get("model"),
                "windows": payload.get("windows"),
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()

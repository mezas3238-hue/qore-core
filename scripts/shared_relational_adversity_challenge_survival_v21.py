"""V21 relational adversity-challenge survival veto for Shared.

V20 proved that recovery and target hazards are learnable, but the direct
multi-state stop gate still harmed winners and missed too many losses.  V21
tests the next architectural hypothesis:

    local collapse is not terminal when broad market support remains intact.

The experiment therefore adds a bounded causal relational representation of
local path pressure versus broader market support and trains an independent
candidate-survival expert.  The expert is a winner veto only; it can prevent a
STOP_LIKELY decision but can never manufacture TARGET_LIKELY.

Training may use CLOSED historical outcomes offline.  Runtime inference uses
only point-in-time Shared state and bounded past observations.  No trader,
methodology, symbol, calendar, fold, current PnL, sizing, capital, risk budget,
order or broker state is an inference feature.
"""

# ruff: noqa: E501,I001

from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from statistics import median
from typing import Any

import numpy as np
import shared_autonomous_nonlinear_loss_risk_ensemble_v19 as v19
import shared_multi_state_competing_hazard_v20 as v20
import vt08_index_shared_context_conditioned_competing_risk_v15 as v15
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.metrics import roc_auc_score

from qore.infrastructure.core_stack_v2.adversity_challenge_intelligence import (
    AdversityChallengeAssessment,
    AdversityChallengeObservation,
    AdversityChallengeState,
    assess_adversity_challenge,
)

IDENTITY = "QORE_SHARED_RELATIONAL_ADVERSITY_CHALLENGE_SURVIVAL_V21"
SCHEMA = "qore.shared.relational_adversity_challenge_survival.v21"

SOURCE_V6_RUN = 36131607443
SOURCE_V15_RUN = 36141968333
SOURCE_V20_RUN = 36154281983

TRAIN_WINDOW = "five_year"
VALIDATION_WINDOWS = ("recent_two_year", "r66_consumed_failed_holdout")

MODEL_PARAMS = {
    "learning_rate": 0.04,
    "max_iter": 200,
    "max_leaf_nodes": 12,
    "max_depth": 3,
    "min_samples_leaf": 80,
    "l2_regularization": 4.0,
    "random_state": 635,
}

MIN_SELECTED_TRADES = 20
TRAIN_PRECISION_FLOOR = Decimal("0.95")
TRAIN_WINNER_MARK_CEILING = Decimal("0.01")
VALIDATION_PRECISION_FLOOR = Decimal("0.90")
VALIDATION_WINNER_MARK_CEILING = Decimal("0.01")
MIN_MEDIAN_LEAD_BARS = Decimal("1")
THRESHOLDS = tuple(
    Decimal("0.005") + Decimal("0.005") * index
    for index in range(100)
)

CHALLENGE_STATES = tuple(state.value for state in AdversityChallengeState)


@dataclass(frozen=True, slots=True)
class Metrics:
    selected: int
    true_loss: int
    false_winner: int
    precision: Decimal
    loss_recall: Decimal
    winner_mark_rate: Decimal
    median_lead_bars: Decimal | None
    relational_veto_count: int
    survival_veto_count: int


def _ratio(numerator: int, denominator: int) -> Decimal:
    if denominator <= 0:
        return Decimal("0")
    return Decimal(numerator) / Decimal(denominator)


def _challenge_observation(row: dict[str, Any]) -> AdversityChallengeObservation:
    as_of = datetime.fromisoformat(str(row["as_of"]))
    return AdversityChallengeObservation(
        as_of=as_of,
        data_integrity_bps=10_000,
        path_support_bps=int(row["path_support_bps"]),
        path_adverse_bps=int(row["path_adverse_dominance_bps"]),
        path_terminal_bps=int(row["path_terminal_failure_risk_bps"]),
        winner_protection_bps=int(row["path_winner_protection_bps"]),
        trajectory_support_bps=int(row["trajectory_support_bps"]),
        trajectory_adverse_bps=int(row["trajectory_adversity_bps"]),
        environment_support_bps=int(row["environment_support_bps"]),
        environment_adverse_bps=int(row["environment_adverse_bps"]),
        recovery_strength_bps=int(row["recovery_strength_bps"]),
        target_capacity_bps=int(row["target_capacity_bps"]),
        futures_terminal_bps=int(row["futures_terminal_evidence_bps"]),
        futures_recovery_bps=int(row["futures_recovery_evidence_bps"]),
        uncertainty_bps=int(row["uncertainty_bps"]),
    )


def _challenge_features(
    assessment: AdversityChallengeAssessment,
) -> list[float]:
    values = [
        assessment.local_adverse_pressure_bps / 10_000.0,
        assessment.local_pressure_velocity_bps / 10_000.0,
        assessment.broad_support_reserve_bps / 10_000.0,
        assessment.broad_support_velocity_bps / 10_000.0,
        assessment.recovery_reserve_bps / 10_000.0,
        assessment.recovery_velocity_bps / 10_000.0,
        assessment.local_broad_decoupling_bps / 10_000.0,
        assessment.terminal_convergence_bps / 10_000.0,
        assessment.uncertainty_bps / 10_000.0,
        min(assessment.evidence_count, 12) / 12.0,
    ]
    values.extend(
        1.0 if assessment.state.value == state else 0.0
        for state in CHALLENGE_STATES
    )
    return values


def _challenge_feature_names() -> tuple[str, ...]:
    return (
        "challenge_local_adverse_pressure",
        "challenge_local_pressure_velocity",
        "challenge_broad_support_reserve",
        "challenge_broad_support_velocity",
        "challenge_recovery_reserve",
        "challenge_recovery_velocity",
        "challenge_local_broad_decoupling",
        "challenge_terminal_convergence",
        "challenge_uncertainty",
        "challenge_evidence_count",
        *(f"challenge_state__{state}" for state in CHALLENGE_STATES),
    )


def _fit_hazard(
    ledger: dict[str, Any],
) -> tuple[
    HistGradientBoostingClassifier,
    dict[str, tuple[str, ...]],
]:
    train_trades = list(ledger[TRAIN_WINDOW]["rows"])
    categories = v19._categories(train_trades)
    x_train, y_train, weights, _ = v20._dataset(train_trades, categories)
    model = HistGradientBoostingClassifier(**v20.MODEL_PARAMS)
    model.fit(x_train, y_train, sample_weight=weights)
    return model, categories


def _candidate_dataset(
    *,
    hazard_model: HistGradientBoostingClassifier,
    categories: dict[str, tuple[str, ...]],
    trades: list[dict[str, Any]],
) -> tuple[
    np.ndarray,
    np.ndarray,
    np.ndarray,
    list[dict[str, Any]],
]:
    x_all, _, _, meta = v20._dataset(trades, categories)
    hazard_probabilities = hazard_model.predict_proba(x_all)
    hazard_classes = tuple(str(value) for value in hazard_model.classes_)
    class_index = {name: index for index, name in enumerate(hazard_classes)}

    histories: dict[int, list[AdversityChallengeObservation]] = defaultdict(list)
    x_rows: list[list[float]] = []
    labels: list[int] = []
    weights: list[float] = []
    payload: list[dict[str, Any]] = []
    candidate_count_by_trade: Counter[int] = Counter()

    staged: list[tuple[int, dict[str, Any], np.ndarray, AdversityChallengeAssessment]] = []
    for vector, values, (trade_index, row) in zip(
        x_all,
        hazard_probabilities,
        meta,
        strict=True,
    ):
        history = histories[trade_index]
        history.append(_challenge_observation(row))
        challenge = assess_adversity_challenge(history)
        adverse = (
            float(values[class_index.get(v20.CAUSE_STOP, 0)])
            + float(values[class_index.get(v20.CAUSE_TERMINAL, 0)])
        )
        favorable = (
            float(values[class_index.get(v20.CAUSE_TARGET, 0)])
            + float(values[class_index.get(v20.CAUSE_RECOVERY, 0)])
        )
        if adverse <= favorable:
            continue
        candidate_count_by_trade[trade_index] += 1
        staged.append((trade_index, row, vector, challenge))

    for trade_index, row, vector, challenge in staged:
        x_rows.append([*vector.tolist(), *_challenge_features(challenge)])
        labels.append(1 if trades[trade_index]["actual"] == "WIN" else 0)
        weights.append(1.0 / float(candidate_count_by_trade[trade_index]))
        payload.append(
            {
                "trade_index": trade_index,
                "row": row,
                "challenge": challenge,
            }
        )

    return (
        np.asarray(x_rows, dtype=np.float64),
        np.asarray(labels, dtype=np.int64),
        np.asarray(weights, dtype=np.float64),
        payload,
    )


def _fit_survival(
    *,
    hazard_model: HistGradientBoostingClassifier,
    categories: dict[str, tuple[str, ...]],
    trades: list[dict[str, Any]],
) -> tuple[
    HistGradientBoostingClassifier,
    np.ndarray,
    np.ndarray,
    np.ndarray,
    list[dict[str, Any]],
]:
    x_rows, labels, weights, meta = _candidate_dataset(
        hazard_model=hazard_model,
        categories=categories,
        trades=trades,
    )
    model = HistGradientBoostingClassifier(**MODEL_PARAMS)
    model.fit(x_rows, labels, sample_weight=weights)
    probabilities = model.predict_proba(x_rows)[:, 1]
    return model, x_rows, labels, probabilities, meta


def _relational_veto(challenge: AdversityChallengeAssessment) -> bool:
    return challenge.state in {
        AdversityChallengeState.LOCAL_COLLAPSE_BROAD_SUPPORT_INTACT,
        AdversityChallengeState.RECOVERY_REASSERTING,
    }


def _metrics(
    *,
    trades: list[dict[str, Any]],
    survival_probabilities: np.ndarray,
    meta: list[dict[str, Any]],
    threshold: Decimal,
) -> Metrics:
    chosen: dict[int, dict[str, Any]] = {}
    relational_veto_count = 0
    survival_veto_count = 0
    limit = float(threshold)

    for probability, item in zip(survival_probabilities, meta, strict=True):
        trade_index = int(item["trade_index"])
        if trade_index in chosen:
            continue
        challenge = item["challenge"]
        if _relational_veto(challenge):
            relational_veto_count += 1
            continue
        if float(probability) > limit:
            survival_veto_count += 1
            continue
        chosen[trade_index] = item

    losses = sum(trade["actual"] == "LOSS" for trade in trades)
    winners = sum(trade["actual"] == "WIN" for trade in trades)
    true_loss = [
        index for index in chosen if trades[index]["actual"] == "LOSS"
    ]
    false_winner = [
        index for index in chosen if trades[index]["actual"] == "WIN"
    ]
    leads = [
        int(chosen[index]["row"]["bars_before_canonical_exit"])
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
        relational_veto_count=relational_veto_count,
        survival_veto_count=survival_veto_count,
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
            None
            if metrics.median_lead_bars is None
            else str(metrics.median_lead_bars)
        ),
        "relational_veto_count": metrics.relational_veto_count,
        "survival_veto_count": metrics.survival_veto_count,
    }


def _choose_threshold(
    *,
    trades: list[dict[str, Any]],
    probabilities: np.ndarray,
    meta: list[dict[str, Any]],
) -> tuple[Decimal | None, Metrics | None, list[dict[str, object]]]:
    admitted: list[tuple[Metrics, Decimal]] = []
    audit: list[dict[str, object]] = []
    for threshold in THRESHOLDS:
        metrics = _metrics(
            trades=trades,
            survival_probabilities=probabilities,
            meta=meta,
            threshold=threshold,
        )
        passed = (
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
                "admitted": passed,
            }
        )
        if passed:
            admitted.append((metrics, threshold))

    if not admitted:
        return None, None, audit

    metrics, threshold = max(
        admitted,
        key=lambda item: (
            item[0].loss_recall,
            item[0].precision,
            -item[0].winner_mark_rate,
            item[0].median_lead_bars or Decimal("0"),
        ),
    )
    return threshold, metrics, audit


def _v15_controls(
    ledger: dict[str, Any],
) -> dict[str, dict[str, object]]:
    model, _, _, _ = v15._fit_v9(ledger)
    cell = v15.Cell(
        fields=("path_state", "environment_state"),
        values=("CONTESTED", "FRAGILE"),
        probability_floor=Decimal("0.900"),
    )
    return {
        key: v15._evaluate_window(
            model=model,
            window=ledger[key],
            selected_cells=[cell],
            selected_keys=frozenset({cell.key()}),
        )
        for key in (TRAIN_WINDOW, *VALIDATION_WINDOWS)
    }


def _selection_forensics(
    *,
    trades: list[dict[str, Any]],
    probabilities: np.ndarray,
    meta: list[dict[str, Any]],
    threshold: Decimal | None,
) -> dict[str, object]:
    if threshold is None:
        return {"selected": 0, "loss_states": {}, "winner_states": {}, "winner_contexts": {}}

    chosen: dict[int, dict[str, Any]] = {}
    limit = float(threshold)
    for probability, item in zip(probabilities, meta, strict=True):
        trade_index = int(item["trade_index"])
        if trade_index in chosen:
            continue
        challenge = item["challenge"]
        if _relational_veto(challenge) or float(probability) > limit:
            continue
        chosen[trade_index] = item

    loss_states: Counter[str] = Counter()
    winner_states: Counter[str] = Counter()
    winner_contexts: Counter[str] = Counter()
    for trade_index, item in chosen.items():
        state = item["challenge"].state.value
        row = item["row"]
        if trades[trade_index]["actual"] == "LOSS":
            loss_states[state] += 1
        else:
            winner_states[state] += 1
            winner_contexts[
                "|".join(
                    (
                        state,
                        f'ENV={row["environment_state"]}',
                        f'PATH={row["path_state"]}',
                        f'REC={row["recovery_challenge_state"]}',
                        f'TERM={row["terminal_failure_state"]}',
                    )
                )
            ] += 1
    return {
        "selected": len(chosen),
        "loss_states": dict(sorted(loss_states.items())),
        "winner_states": dict(sorted(winner_states.items())),
        "winner_contexts": dict(sorted(winner_contexts.items())),
    }


def _window(
    *,
    hazard_model: HistGradientBoostingClassifier,
    survival_model: HistGradientBoostingClassifier,
    categories: dict[str, tuple[str, ...]],
    trades: list[dict[str, Any]],
    threshold: Decimal | None,
    v15_control: dict[str, object],
) -> dict[str, object]:
    x_rows, labels, weights, meta = _candidate_dataset(
        hazard_model=hazard_model,
        categories=categories,
        trades=trades,
    )
    probabilities = survival_model.predict_proba(x_rows)[:, 1]
    auc = (
        None
        if len(set(labels.tolist())) < 2
        else Decimal(
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
    )
    metrics = (
        Metrics(
            selected=0,
            true_loss=0,
            false_winner=0,
            precision=Decimal("0"),
            loss_recall=Decimal("0"),
            winner_mark_rate=Decimal("0"),
            median_lead_bars=None,
            relational_veto_count=0,
            survival_veto_count=0,
        )
        if threshold is None
        else _metrics(
            trades=trades,
            survival_probabilities=probabilities,
            meta=meta,
            threshold=threshold,
        )
    )
    v15_recall = Decimal(
        str(v15_control["v15_combined"]["loss_recall"])
    )
    admitted = (
        threshold is not None
        and metrics.selected >= MIN_SELECTED_TRADES
        and metrics.precision >= VALIDATION_PRECISION_FLOOR
        and metrics.winner_mark_rate <= VALIDATION_WINNER_MARK_CEILING
        and metrics.loss_recall > v15_recall
        and metrics.median_lead_bars is not None
        and metrics.median_lead_bars >= MIN_MEDIAN_LEAD_BARS
    )
    state_counts = Counter(
        item["challenge"].state.value
        for item in meta
    )
    return {
        "sample": len(trades),
        "candidate_observations": len(meta),
        "candidate_survival_auc": None if auc is None else str(auc),
        "challenge_state_counts": dict(sorted(state_counts.items())),
        "v15_loss_recall_control": str(v15_recall),
        "v21": _payload(metrics),
        "selection_forensics": _selection_forensics(
            trades=trades,
            probabilities=probabilities,
            meta=meta,
            threshold=threshold,
        ),
        "beats_v15_loss_recall": metrics.loss_recall > v15_recall,
        "status": "ADMIT_FOR_ECONOMIC_SHADOW" if admitted else "REJECT",
    }


def run(v6_json: Path) -> dict[str, object]:
    ledger = json.loads(v6_json.read_text())
    if ledger["identity"] != "QORE_SHARED_VT08_INDEX_STOP_TARGET_DISCRIMINATION_V6":
        raise ValueError("unexpected frozen external falsification ledger identity")

    hazard_model, categories = _fit_hazard(ledger)
    train_trades = list(ledger[TRAIN_WINDOW]["rows"])
    (
        survival_model,
        _,
        train_labels,
        train_probabilities,
        train_meta,
    ) = _fit_survival(
        hazard_model=hazard_model,
        categories=categories,
        trades=train_trades,
    )
    threshold, train_metrics, threshold_audit = _choose_threshold(
        trades=train_trades,
        probabilities=train_probabilities,
        meta=train_meta,
    )
    controls = _v15_controls(ledger)

    windows = {
        key: _window(
            hazard_model=hazard_model,
            survival_model=survival_model,
            categories=categories,
            trades=list(ledger[key]["rows"]),
            threshold=threshold,
            v15_control=controls[key],
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
        "source_v20_run": SOURCE_V20_RUN,
        "research_only": True,
        "shared_autonomous_model": True,
        "candidate_survival_expert_is_winner_veto_only": True,
        "winner_veto_cannot_create_target": True,
        "relational_path_environment_topology_used": True,
        "bounded_past_only": True,
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
        "closed_outcome_used_offline_to_train_survival_expert": True,
        "feature_count": len(v20._feature_names(categories))
        + len(_challenge_feature_names()),
        "model": {
            "hazard_model": "V20_FROZEN_MULTI_STATE_DISCRETE_HAZARD",
            "survival_model": "HIST_GRADIENT_BOOSTING_CANDIDATE_SURVIVAL",
            **MODEL_PARAMS,
            "selected_survival_probability_ceiling": (
                None if threshold is None else str(threshold)
            ),
        },
        "training_candidate_labels": {
            "winner": int(train_labels.sum()),
            "loss": int(len(train_labels) - train_labels.sum()),
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
                "selected_survival_probability_ceiling": payload["model"][
                    "selected_survival_probability_ceiling"
                ],
                "validation_pass": payload["validation_pass"],
                "windows": payload["windows"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()

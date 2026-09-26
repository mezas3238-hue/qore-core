"""V20 Shared multi-state competing-hazard research.

V19 showed useful final-loss ranking but no economically safe global action
frontier. V20 changes the learning target from eventual LOSS/WIN to the first
near-term causal path event within a fixed horizon:

    TERMINAL_FORMATION / RECOVERY / STOP / TARGET / NO_EVENT

Runtime features remain trader-agnostic, symbol-agnostic, methodology-agnostic,
calendar-agnostic and point-in-time. Future information is used only offline to
construct event-time labels and score the frozen model. The decision layer has
an independent winner veto and CONTESTED is a first-class output.
"""

# ruff: noqa: E501,I001

from __future__ import annotations

import argparse
import json
import math
from collections import defaultdict
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from statistics import median
from typing import Any

import numpy as np
import shared_autonomous_nonlinear_loss_risk_ensemble_v19 as v19
import vt08_index_shared_context_conditioned_competing_risk_v15 as v15
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.metrics import roc_auc_score

from qore.infrastructure.core_stack_v2.multi_state_competing_hazard import (
    CompetingHazardDecision,
    CompetingHazardEvidence,
    assess_competing_hazards,
)

IDENTITY = "QORE_SHARED_MULTI_STATE_COMPETING_HAZARD_V20"
SCHEMA = "qore.shared.multi_state_competing_hazard.v20"

SOURCE_V6_RUN = 36131607443
SOURCE_V15_RUN = 36141968333
SOURCE_V19_RUN = 36146517470

TRAIN_WINDOW = "five_year"
VALIDATION_WINDOWS = ("recent_two_year", "r66_consumed_failed_holdout")

HORIZON_BARS = 5
PERSISTENCE_OBSERVATIONS = 3
MIN_SELECTED_TRADES = 20
VALIDATION_PRECISION_FLOOR = Decimal("0.90")
VALIDATION_WINNER_MARK_CEILING = Decimal("0.01")
MIN_MEDIAN_LEAD_BARS = Decimal("1")

CAUSE_NONE = "NO_EVENT"
CAUSE_TERMINAL = "TERMINAL"
CAUSE_RECOVERY = "RECOVERY"
CAUSE_STOP = "STOP"
CAUSE_TARGET = "TARGET"
CAUSES = (
    CAUSE_NONE,
    CAUSE_TERMINAL,
    CAUSE_RECOVERY,
    CAUSE_STOP,
    CAUSE_TARGET,
)

MODEL_PARAMS = {
    "learning_rate": 0.04,
    "max_iter": 220,
    "max_leaf_nodes": 15,
    "max_depth": 4,
    "min_samples_leaf": 100,
    "l2_regularization": 3.0,
    "random_state": 635,
}

TEMPORAL_FIELDS = (
    "stop_pressure_bps",
    "stop_formation_bps",
    "target_capacity_bps",
    "recovery_strength_bps",
    "path_support_bps",
    "path_adverse_dominance_bps",
    "path_recovery_persistence_bps",
    "path_terminal_failure_risk_bps",
    "trajectory_support_bps",
    "trajectory_adversity_bps",
    "trajectory_deterioration_velocity_bps",
    "trajectory_recovery_velocity_bps",
    "environment_support_bps",
    "environment_adverse_bps",
    "futures_terminal_evidence_bps",
    "futures_recovery_evidence_bps",
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
    target_selected: int
    true_target: int
    false_target: int
    recoverable_selected: int


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


def _event_candidate(
    *,
    current: dict[str, Any],
    future: dict[str, Any],
) -> tuple[int, str] | None:
    current_remaining = int(current["bars_before_canonical_exit"])
    future_remaining = int(future["bars_before_canonical_exit"])
    steps = current_remaining - future_remaining
    if steps < 1 or steps > HORIZON_BARS:
        return None

    current_terminal = str(current["terminal_failure_state"])
    future_terminal = str(future["terminal_failure_state"])
    if (
        current_terminal != "TERMINAL_CONFIRMED"
        and future_terminal == "TERMINAL_CONFIRMED"
    ):
        return steps, CAUSE_TERMINAL

    current_recovery = str(current["recovery_challenge_state"])
    future_recovery = str(future["recovery_challenge_state"])
    if (
        current_recovery != "RECOVERY_RESTORED"
        and future_recovery == "RECOVERY_RESTORED"
    ):
        return steps, CAUSE_RECOVERY
    return None


def _next_cause(
    *,
    trade: dict[str, Any],
    rows: list[dict[str, Any]],
    index: int,
) -> str:
    current = rows[index]
    if str(current["terminal_failure_state"]) == "TERMINAL_CONFIRMED":
        return CAUSE_NONE

    candidates: list[tuple[int, int, str]] = []
    priority = {
        CAUSE_TERMINAL: 0,
        CAUSE_RECOVERY: 1,
        CAUSE_STOP: 2,
        CAUSE_TARGET: 3,
    }
    for future in rows[index + 1 :]:
        event = _event_candidate(current=current, future=future)
        if event is None:
            future_remaining = int(future["bars_before_canonical_exit"])
            current_remaining = int(current["bars_before_canonical_exit"])
            if current_remaining - future_remaining > HORIZON_BARS:
                break
            continue
        steps, cause = event
        candidates.append((steps, priority[cause], cause))

    exit_steps = int(current["bars_before_canonical_exit"])
    if 1 <= exit_steps <= HORIZON_BARS:
        cause = CAUSE_STOP if trade["actual"] == "LOSS" else CAUSE_TARGET
        candidates.append((exit_steps, priority[cause], cause))

    if not candidates:
        return CAUSE_NONE
    return min(candidates)[2]


def _temporal_features(
    rows: list[dict[str, Any]],
    index: int,
) -> list[float]:
    current = rows[index]
    previous_1 = rows[max(0, index - 1)]
    previous_3 = rows[max(0, index - 3)]
    result: list[float] = []
    for field in TEMPORAL_FIELDS:
        now = int(current[field])
        result.append((now - int(previous_1[field])) / 10_000.0)
        result.append((now - int(previous_3[field])) / 10_000.0)
    return result


def _feature_names(
    categories: dict[str, tuple[str, ...]],
) -> tuple[str, ...]:
    return (
        *v19._feature_names(categories),
        *(
            name
            for field in TEMPORAL_FIELDS
            for name in (f"delta1__{field}", f"delta3__{field}")
        ),
    )


def _dataset(
    trades: list[dict[str, Any]],
    categories: dict[str, tuple[str, ...]],
) -> tuple[
    np.ndarray,
    np.ndarray,
    np.ndarray,
    list[tuple[int, dict[str, Any]]],
]:
    x_rows: list[list[float]] = []
    y_rows: list[str] = []
    weights: list[float] = []
    meta: list[tuple[int, dict[str, Any]]] = []

    for trade_index, trade in enumerate(trades):
        rows = _eligible(trade)
        if not rows:
            continue
        observation_weight = 1.0 / float(len(rows))
        for index, row in enumerate(rows):
            x_rows.append(
                [
                    *v19._vector(row, categories),
                    *_temporal_features(rows, index),
                ]
            )
            y_rows.append(_next_cause(trade=trade, rows=rows, index=index))
            weights.append(observation_weight)
            meta.append((trade_index, row))

    return (
        np.asarray(x_rows, dtype=np.float64),
        np.asarray(y_rows, dtype=object),
        np.asarray(weights, dtype=np.float64),
        meta,
    )


def _probability_map(
    model: HistGradientBoostingClassifier,
    row: np.ndarray,
) -> dict[str, float]:
    values = model.predict_proba(row.reshape(1, -1))[0]
    result = {cause: 0.0 for cause in CAUSES}
    for label, probability in zip(model.classes_, values, strict=True):
        result[str(label)] = float(probability)
    return result


def _entropy_bps(probabilities: dict[str, float]) -> int:
    active = [value for value in probabilities.values() if value > 0.0]
    if len(active) <= 1:
        return 0
    entropy = -sum(value * math.log(value) for value in active)
    maximum = math.log(len(CAUSES))
    return max(0, min(10_000, int(round(entropy / maximum * 10_000))))


def _winner_veto_bps(row: dict[str, Any]) -> int:
    values = (
        int(row["path_winner_protection_bps"]),
        int(row["path_support_bps"]),
        int(row["target_capacity_bps"]),
        int(row["recovery_strength_bps"]),
        int(row["futures_recovery_evidence_bps"]),
    )
    return sum(values) // len(values)


def _persistence(
    history: list[dict[str, float]],
    *,
    mode: str,
) -> int:
    recent = history[-PERSISTENCE_OBSERVATIONS:]
    if not recent:
        return 0
    qualifying = 0
    for probabilities in recent:
        adverse = probabilities[CAUSE_STOP] + probabilities[CAUSE_TERMINAL]
        target = probabilities[CAUSE_TARGET]
        recovery = probabilities[CAUSE_RECOVERY]
        favorable = target + recovery
        if mode == "adverse":
            matched = adverse > favorable
        elif mode == "target":
            matched = target > adverse and target >= recovery
        elif mode == "recovery":
            matched = recovery > adverse and recovery > target
        else:
            raise ValueError(f"unknown persistence mode {mode}")
        qualifying += int(matched)
    return qualifying * 10_000 // len(recent)


def _decision_rows(
    *,
    probability_rows: np.ndarray,
    classes: tuple[str, ...],
    meta: list[tuple[int, dict[str, Any]]],
) -> dict[int, list[dict[str, Any]]]:
    result: dict[int, list[dict[str, Any]]] = defaultdict(list)
    probability_history: dict[int, list[dict[str, float]]] = defaultdict(list)

    for values, (trade_index, row) in zip(probability_rows, meta, strict=True):
        probabilities = {cause: 0.0 for cause in CAUSES}
        for label, probability in zip(classes, values, strict=True):
            probabilities[label] = float(probability)
        history = probability_history[trade_index]
        history.append(probabilities)

        evidence = CompetingHazardEvidence(
            as_of=v15.datetime.fromisoformat(str(row["as_of"])),
            data_integrity_bps=10_000,
            stop_hazard_bps=int(round(probabilities[CAUSE_STOP] * 10_000)),
            terminal_hazard_bps=int(
                round(probabilities[CAUSE_TERMINAL] * 10_000)
            ),
            target_hazard_bps=int(round(probabilities[CAUSE_TARGET] * 10_000)),
            recovery_hazard_bps=int(
                round(probabilities[CAUSE_RECOVERY] * 10_000)
            ),
            no_event_bps=int(round(probabilities[CAUSE_NONE] * 10_000)),
            adverse_persistence_bps=_persistence(history, mode="adverse"),
            target_persistence_bps=_persistence(history, mode="target"),
            recovery_persistence_bps=_persistence(history, mode="recovery"),
            winner_veto_bps=_winner_veto_bps(row),
            uncertainty_bps=max(
                int(row["uncertainty_bps"]),
                _entropy_bps(probabilities),
            ),
        )
        assessment = assess_competing_hazards(evidence)
        result[trade_index].append(
            {
                "row": row,
                "decision": assessment.decision.value,
                "adverse_hazard_bps": assessment.adverse_hazard_bps,
                "favorable_hazard_bps": assessment.favorable_hazard_bps,
                "separation_margin_bps": assessment.separation_margin_bps,
                "winner_veto_active": assessment.winner_veto_active,
                "uncertainty_bps": evidence.uncertainty_bps,
                "probabilities": {
                    key: str(Decimal(str(value)))
                    for key, value in probabilities.items()
                },
            }
        )
    return dict(result)


def _trade_metrics(
    trades: list[dict[str, Any]],
    decisions: dict[int, list[dict[str, Any]]],
) -> TradeDecisionMetrics:
    losses = sum(trade["actual"] == "LOSS" for trade in trades)
    winners = sum(trade["actual"] == "WIN" for trade in trades)

    first_stop: dict[int, dict[str, Any]] = {}
    first_target: dict[int, dict[str, Any]] = {}
    first_recovery: dict[int, dict[str, Any]] = {}
    for trade_index, rows in decisions.items():
        for item in rows:
            decision = str(item["decision"])
            if (
                decision == CompetingHazardDecision.STOP_LIKELY.value
                and trade_index not in first_stop
            ):
                first_stop[trade_index] = item
            elif (
                decision == CompetingHazardDecision.TARGET_LIKELY.value
                and trade_index not in first_target
            ):
                first_target[trade_index] = item
            elif (
                decision == CompetingHazardDecision.RECOVERABLE.value
                and trade_index not in first_recovery
            ):
                first_recovery[trade_index] = item

    true_loss = [
        index for index in first_stop if trades[index]["actual"] == "LOSS"
    ]
    false_winner = [
        index for index in first_stop if trades[index]["actual"] == "WIN"
    ]
    true_target = [
        index for index in first_target if trades[index]["actual"] == "WIN"
    ]
    false_target = [
        index for index in first_target if trades[index]["actual"] == "LOSS"
    ]
    leads = [
        int(first_stop[index]["row"]["bars_before_canonical_exit"])
        for index in true_loss
    ]
    return TradeDecisionMetrics(
        selected=len(first_stop),
        true_loss=len(true_loss),
        false_winner=len(false_winner),
        precision=_ratio(len(true_loss), len(first_stop)),
        loss_recall=_ratio(len(true_loss), losses),
        winner_mark_rate=_ratio(len(false_winner), winners),
        median_lead_bars=(
            None if not leads else Decimal(str(median(leads)))
        ),
        target_selected=len(first_target),
        true_target=len(true_target),
        false_target=len(false_target),
        recoverable_selected=len(first_recovery),
    )


def _metrics_payload(metrics: TradeDecisionMetrics) -> dict[str, object]:
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
        "target_selected": metrics.target_selected,
        "true_target": metrics.true_target,
        "false_target": metrics.false_target,
        "recoverable_selected": metrics.recoverable_selected,
    }


def _binary_auc(
    y_rows: np.ndarray,
    probabilities: np.ndarray,
    classes: tuple[str, ...],
    positive: tuple[str, ...],
    weights: np.ndarray,
) -> Decimal | None:
    labels = np.asarray(
        [1 if str(value) in positive else 0 for value in y_rows],
        dtype=np.int64,
    )
    if len(set(labels.tolist())) < 2:
        return None
    indices = [
        classes.index(cause)
        for cause in positive
        if cause in classes
    ]
    scores = probabilities[:, indices].sum(axis=1)
    return Decimal(
        str(float(roc_auc_score(labels, scores, sample_weight=weights)))
    )


def _event_counts(y_rows: np.ndarray) -> dict[str, int]:
    return {
        cause: int(sum(str(value) == cause for value in y_rows))
        for cause in CAUSES
    }


def _window(
    *,
    model: HistGradientBoostingClassifier,
    categories: dict[str, tuple[str, ...]],
    trades: list[dict[str, Any]],
    v15_control: dict[str, Any],
) -> dict[str, object]:
    x_rows, y_rows, weights, meta = _dataset(trades, categories)
    probabilities = model.predict_proba(x_rows)
    classes = tuple(str(value) for value in model.classes_)
    decisions = _decision_rows(
        probability_rows=probabilities,
        classes=classes,
        meta=meta,
    )
    metrics = _trade_metrics(trades, decisions)

    v15_recall = Decimal(
        str(v15_control["v15_combined"]["loss_recall"])
    )
    admitted = (
        metrics.selected >= MIN_SELECTED_TRADES
        and metrics.precision >= VALIDATION_PRECISION_FLOOR
        and metrics.winner_mark_rate <= VALIDATION_WINNER_MARK_CEILING
        and metrics.loss_recall > v15_recall
        and metrics.median_lead_bars is not None
        and metrics.median_lead_bars >= MIN_MEDIAN_LEAD_BARS
    )

    return {
        "sample": len(trades),
        "observations": len(meta),
        "event_counts": _event_counts(y_rows),
        "adverse_auc": (
            None
            if (
                value := _binary_auc(
                    y_rows,
                    probabilities,
                    classes,
                    (CAUSE_STOP, CAUSE_TERMINAL),
                    weights,
                )
            )
            is None
            else str(value)
        ),
        "recovery_auc": (
            None
            if (
                value := _binary_auc(
                    y_rows,
                    probabilities,
                    classes,
                    (CAUSE_RECOVERY,),
                    weights,
                )
            )
            is None
            else str(value)
        ),
        "target_auc": (
            None
            if (
                value := _binary_auc(
                    y_rows,
                    probabilities,
                    classes,
                    (CAUSE_TARGET,),
                    weights,
                )
            )
            is None
            else str(value)
        ),
        "v15_loss_recall_control": str(v15_recall),
        "v20": _metrics_payload(metrics),
        "beats_v15_loss_recall": metrics.loss_recall > v15_recall,
        "status": "ADMIT_FOR_ECONOMIC_SHADOW" if admitted else "REJECT",
    }


def run(v6_json: Path) -> dict[str, object]:
    ledger = json.loads(v6_json.read_text())
    if ledger["identity"] != "QORE_SHARED_VT08_INDEX_STOP_TARGET_DISCRIMINATION_V6":
        raise ValueError("unexpected frozen external falsification ledger identity")

    train_trades = list(ledger[TRAIN_WINDOW]["rows"])
    categories = v19._categories(train_trades)
    feature_names = _feature_names(categories)
    x_train, y_train, train_weights, _ = _dataset(train_trades, categories)

    model = HistGradientBoostingClassifier(**MODEL_PARAMS)
    model.fit(x_train, y_train, sample_weight=train_weights)

    v15_model, _, _, _ = v15._fit_v9(ledger)
    v15_cell = v15.Cell(
        fields=("path_state", "environment_state"),
        values=("CONTESTED", "FRAGILE"),
        probability_floor=Decimal("0.900"),
    )
    v15_windows = {
        key: v15._evaluate_window(
            model=v15_model,
            window=ledger[key],
            selected_cells=[v15_cell],
            selected_keys=frozenset({v15_cell.key()}),
        )
        for key in (TRAIN_WINDOW, *VALIDATION_WINDOWS)
    }

    windows = {
        key: _window(
            model=model,
            categories=categories,
            trades=list(ledger[key]["rows"]),
            v15_control=v15_windows[key],
        )
        for key in (TRAIN_WINDOW, *VALIDATION_WINDOWS)
    }
    validation_pass = all(
        windows[key]["status"] == "ADMIT_FOR_ECONOMIC_SHADOW"
        for key in VALIDATION_WINDOWS
    )

    return {
        "schema": SCHEMA,
        "identity": IDENTITY,
        "source_v6_run": SOURCE_V6_RUN,
        "source_v15_run": SOURCE_V15_RUN,
        "source_v19_run": SOURCE_V19_RUN,
        "research_only": True,
        "shared_autonomous_model": True,
        "multi_state_target": True,
        "final_loss_binary_target": False,
        "first_class_contested_state": True,
        "independent_winner_veto": True,
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
        "training_future_event_labels_used_offline_only": True,
        "horizon_bars": HORIZON_BARS,
        "persistence_observations": PERSISTENCE_OBSERVATIONS,
        "causes": list(CAUSES),
        "feature_count": len(feature_names),
        "feature_names": list(feature_names),
        "model": {
            "type": "HIST_GRADIENT_BOOSTING_MULTI_STATE_DISCRETE_HAZARD",
            **MODEL_PARAMS,
            "threshold_search_used": False,
            "decision_gate": "FROZEN_GENERIC_COMPETING_HAZARD_POLICY",
        },
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
                "windows": payload["windows"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()

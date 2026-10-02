"""V23 sequence-event causal belief arbitration for Shared Core.

V22 falsified a family of static winner-protection rules. The failure is
structural: winners and losses overlap heavily in point-in-time state space.
V23 therefore models *how the causal state evolves* and maintains a persistent
belief over competing near-term hypotheses.

Architecture:
1. Train one generic near-term event model on the five-year consumed window
   using V20 event-time labels (STOP / TERMINAL / RECOVERY / TARGET / NO_EVENT).
2. Add outcome-blind causal-path sequence features from the resident
   CausalPathRepresentation.
3. Convert event probabilities into a bounded recurrent causal belief over
   TERMINAL vs RECOVERY/TARGET vs NO_EVENT.
4. Arbitrate frozen V21 candidates in both directions:
   - strong favorable sequence belief may veto a V21 loss mark;
   - strong terminal sequence belief may recover a V21 survival-vetoed loss
     candidate, but may not override V21's independent relational winner veto.
5. Select arbitration mode and confidence floor on five-year only, then freeze
   them unchanged for the two consumed validation windows.

No current PnL, future market, symbol, market, trader, methodology, calendar,
fold, sizing, risk, order or broker identity is used at inference. Closed
outcomes are used only offline to train/score historical models. Fresh holdout
remains closed.
"""

# ruff: noqa: E501,I001

from __future__ import annotations

import argparse
import json
import math
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from statistics import median
from typing import Any

import numpy as np
import shared_relational_adversity_challenge_survival_v21 as v21
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.metrics import roc_auc_score

from qore.infrastructure.core_stack_v2.causal_hypothesis_belief import (
    CausalBeliefDisposition,
    CausalHypothesisBelief,
    CausalHypothesisEvidence,
    accumulate_causal_hypotheses,
)
from qore.infrastructure.core_stack_v2.causal_path_representation import (
    CausalPathPhase,
    CausalPathPoint,
    PathDirection,
    represent_causal_path,
)

IDENTITY = "QORE_SHARED_SEQUENCE_EVENT_CAUSAL_BELIEF_V23"
SCHEMA = "qore.shared.sequence_event_causal_belief.v23"

SOURCE_V6_RUN = 36131607443
SOURCE_V20_RUN = 36154281983
SOURCE_V21_RUN = 36156421332
SOURCE_V22D_R3_RUN = 36178257345

TRAIN_WINDOW = v21.TRAIN_WINDOW
VALIDATION_WINDOWS = v21.VALIDATION_WINDOWS
WINDOWS = (TRAIN_WINDOW, *VALIDATION_WINDOWS)

TRAIN_PRECISION_FLOOR = Decimal("0.95")
VALIDATION_PRECISION_FLOOR = Decimal("0.90")
WINNER_MARK_CEILING = Decimal("0.01")
MIN_SELECTED_TRADES = 20
MIN_MEDIAN_LEAD_BARS = Decimal("1")

BELIEF_DECAY_BPS = 7_500
BELIEF_MAX_FRAMES = 8
BELIEF_DOMINANCE_MARGIN_BPS = 1_200
CONFIDENCE_FLOORS = (1_000, 2_000, 3_000, 4_000, 5_000, 6_000, 7_000)
MODES = ("VETO_ONLY", "TERMINAL_ADD_ONLY", "TWO_SIDED")

MODEL_PARAMS = {
    "learning_rate": 0.035,
    "max_iter": 240,
    "max_leaf_nodes": 18,
    "max_depth": 4,
    "min_samples_leaf": 90,
    "l2_regularization": 4.0,
    "random_state": 635,
}

PHASES = tuple(item.value for item in CausalPathPhase)
DIRECTIONS = tuple(item.value for item in PathDirection)


@dataclass(frozen=True, slots=True)
class ArbitrationMetrics:
    selected: int
    true_loss: int
    false_winner: int
    precision: Decimal
    loss_recall: Decimal
    winner_mark_rate: Decimal
    median_lead_bars: Decimal | None
    added: int
    vetoed: int
    terminal_additions: int
    favorable_vetoes: int


def _ratio(n: int, d: int) -> Decimal:
    return Decimal("0") if d <= 0 else Decimal(n) / Decimal(d)


def _point(row: dict[str, Any]) -> CausalPathPoint:
    return CausalPathPoint(
        stop_pressure_bps=int(row["stop_pressure_bps"]),
        target_capacity_bps=int(row["target_capacity_bps"]),
        recovery_strength_bps=int(row["recovery_strength_bps"]),
        uncertainty_bps=int(row["uncertainty_bps"]),
        path_support_bps=int(row["path_support_bps"]),
        path_adverse_bps=int(row["path_adverse_dominance_bps"]),
        path_recovery_bps=int(row["path_recovery_persistence_bps"]),
        path_terminal_risk_bps=int(row["path_terminal_failure_risk_bps"]),
        trajectory_support_bps=int(row["trajectory_support_bps"]),
        trajectory_adversity_bps=int(row["trajectory_adversity_bps"]),
        trajectory_deterioration_bps=int(row["trajectory_deterioration_pressure_bps"]),
        trajectory_recovery_bps=int(row["trajectory_recovery_velocity_bps"]),
        environment_support_bps=int(row["environment_support_bps"]),
        environment_adverse_bps=int(row["environment_adverse_bps"]),
        futures_terminal_bps=int(row["futures_terminal_evidence_bps"]),
        futures_recovery_bps=int(row["futures_recovery_evidence_bps"]),
    )


def _direction_value(value: PathDirection) -> float:
    return {
        PathDirection.FALLING: -1.0,
        PathDirection.FLAT: 0.0,
        PathDirection.RISING: 1.0,
    }[value]


def _representation(rows: list[dict[str, Any]], index: int):
    start = max(0, index - 4)
    points = tuple(_point(row) for row in rows[start : index + 1])
    return represent_causal_path(points, maximum_points=5)


def _sequence_features(rows: list[dict[str, Any]], index: int) -> list[float]:
    current = _representation(rows, index)
    previous = _representation(rows, max(0, index - 1))

    features = [
        min(current.evidence_count, 5) / 5.0,
        current.stop_target_gap_bps / 10_000.0,
        current.terminal_recovery_gap_bps / 10_000.0,
        current.adversity_support_gap_bps / 10_000.0,
        _direction_value(current.stop_direction),
        _direction_value(current.target_direction),
        _direction_value(current.recovery_direction),
        _direction_value(current.support_direction),
        _direction_value(current.terminal_direction),
        _direction_value(current.deterioration_direction),
        max(-10_000, min(10_000, current.stop_acceleration_bps)) / 10_000.0,
        max(-10_000, min(10_000, current.recovery_acceleration_bps)) / 10_000.0,
        max(-10_000, min(10_000, current.target_acceleration_bps)) / 10_000.0,
        1.0 if current.phase != previous.phase else 0.0,
    ]
    features.extend(1.0 if current.phase.value == phase else 0.0 for phase in PHASES)
    features.extend(1.0 if previous.phase.value == phase else 0.0 for phase in PHASES)
    return features


def _sequence_feature_names() -> tuple[str, ...]:
    return (
        "causal_evidence_fraction",
        "causal_stop_target_gap",
        "causal_terminal_recovery_gap",
        "causal_adversity_support_gap",
        "causal_stop_direction",
        "causal_target_direction",
        "causal_recovery_direction",
        "causal_support_direction",
        "causal_terminal_direction",
        "causal_deterioration_direction",
        "causal_stop_acceleration",
        "causal_recovery_acceleration",
        "causal_target_acceleration",
        "causal_phase_changed",
        *(f"causal_phase__{phase}" for phase in PHASES),
        *(f"prior_causal_phase__{phase}" for phase in PHASES),
    )


def _dataset(
    trades: list[dict[str, Any]],
    categories: dict[str, tuple[str, ...]],
) -> tuple[np.ndarray, np.ndarray, np.ndarray, list[tuple[int, dict[str, Any]]]]:
    x_rows: list[list[float]] = []
    y_rows: list[str] = []
    weights: list[float] = []
    meta: list[tuple[int, dict[str, Any]]] = []

    for trade_index, trade in enumerate(trades):
        rows = v21.v20._eligible(trade)
        if not rows:
            continue
        observation_weight = 1.0 / float(len(rows))
        for index, row in enumerate(rows):
            x_rows.append(
                [
                    *v21.v19._vector(row, categories),
                    *v21.v20._temporal_features(rows, index),
                    *_sequence_features(rows, index),
                ]
            )
            y_rows.append(v21.v20._next_cause(trade=trade, rows=rows, index=index))
            weights.append(observation_weight)
            meta.append((trade_index, row))

    return (
        np.asarray(x_rows, dtype=np.float64),
        np.asarray(y_rows, dtype=object),
        np.asarray(weights, dtype=np.float64),
        meta,
    )


def _fit_event_model(
    *,
    trades: list[dict[str, Any]],
    categories: dict[str, tuple[str, ...]],
) -> HistGradientBoostingClassifier:
    x_rows, y_rows, weights, _ = _dataset(trades, categories)
    model = HistGradientBoostingClassifier(**MODEL_PARAMS)
    model.fit(x_rows, y_rows, sample_weight=weights)
    return model


def _event_auc(
    *,
    model: HistGradientBoostingClassifier,
    trades: list[dict[str, Any]],
    categories: dict[str, tuple[str, ...]],
) -> str | None:
    x_rows, y_rows, weights, _ = _dataset(trades, categories)
    probabilities = model.predict_proba(x_rows)
    classes = tuple(str(value) for value in model.classes_)
    labels = np.asarray(
        [
            1
            if str(value) in {v21.v20.CAUSE_STOP, v21.v20.CAUSE_TERMINAL}
            else 0
            for value in y_rows
        ],
        dtype=np.int64,
    )
    if len(set(labels.tolist())) < 2:
        return None
    indices = [
        classes.index(cause)
        for cause in (v21.v20.CAUSE_STOP, v21.v20.CAUSE_TERMINAL)
        if cause in classes
    ]
    scores = probabilities[:, indices].sum(axis=1)
    return str(float(roc_auc_score(labels, scores, sample_weight=weights)))


def _entropy_bps(probabilities: dict[str, float]) -> int:
    active = [value for value in probabilities.values() if value > 0]
    if len(active) <= 1:
        return 0
    entropy = -sum(value * math.log(value) for value in active)
    return max(
        0,
        min(
            10_000,
            int(round(entropy / math.log(len(v21.v20.CAUSES)) * 10_000)),
        ),
    )


def _belief_map(
    *,
    model: HistGradientBoostingClassifier,
    trades: list[dict[str, Any]],
    categories: dict[str, tuple[str, ...]],
) -> dict[tuple[int, str], CausalHypothesisBelief]:
    x_rows, _, _, meta = _dataset(trades, categories)
    probability_rows = model.predict_proba(x_rows)
    classes = tuple(str(value) for value in model.classes_)
    histories: dict[int, list[CausalHypothesisEvidence]] = defaultdict(list)
    result: dict[tuple[int, str], CausalHypothesisBelief] = {}

    for values, (trade_index, row) in zip(probability_rows, meta, strict=True):
        p = {cause: 0.0 for cause in v21.v20.CAUSES}
        for label, probability in zip(classes, values, strict=True):
            p[label] = float(probability)

        frame = CausalHypothesisEvidence(
            as_of=datetime.fromisoformat(str(row["as_of"])),
            terminal_bps=int(
                round(
                    (
                        p[v21.v20.CAUSE_STOP]
                        + p[v21.v20.CAUSE_TERMINAL]
                    )
                    * 10_000
                )
            ),
            recovery_bps=int(round(p[v21.v20.CAUSE_RECOVERY] * 10_000)),
            target_bps=int(round(p[v21.v20.CAUSE_TARGET] * 10_000)),
            no_event_bps=int(round(p[v21.v20.CAUSE_NONE] * 10_000)),
            uncertainty_bps=max(
                int(row["uncertainty_bps"]),
                _entropy_bps(p),
            ),
        )
        history = histories[trade_index]
        history.append(frame)
        belief = accumulate_causal_hypotheses(
            tuple(history),
            maximum_frames=BELIEF_MAX_FRAMES,
            decay_bps=BELIEF_DECAY_BPS,
            dominance_margin_bps=BELIEF_DOMINANCE_MARGIN_BPS,
        )
        result[(trade_index, str(row["as_of"]))] = belief

    return result


def _candidate_surface(
    *,
    hazard_model: HistGradientBoostingClassifier,
    survival_model: HistGradientBoostingClassifier,
    event_model: HistGradientBoostingClassifier,
    categories: dict[str, tuple[str, ...]],
    trades: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    x_rows, _, _, meta = v21._candidate_dataset(
        hazard_model=hazard_model,
        categories=categories,
        trades=trades,
    )
    survival_probabilities = survival_model.predict_proba(x_rows)[:, 1]
    beliefs = _belief_map(
        model=event_model,
        trades=trades,
        categories=categories,
    )
    return [
        {
            **item,
            "survival_probability": float(probability),
            "belief": beliefs[(int(item["trade_index"]), str(item["row"]["as_of"]))],
        }
        for probability, item in zip(survival_probabilities, meta, strict=True)
    ]


def _select(
    *,
    surface: list[dict[str, Any]],
    v21_threshold: Decimal,
    mode: str,
    confidence_floor: int,
) -> tuple[dict[int, dict[str, Any]], dict[str, int]]:
    chosen: dict[int, dict[str, Any]] = {}
    base_seen: set[int] = set()
    added = vetoed = terminal_additions = favorable_vetoes = 0
    limit = float(v21_threshold)

    for item in surface:
        trade_index = int(item["trade_index"])
        if trade_index in chosen:
            continue

        relational_veto = v21._relational_veto(item["challenge"])
        base = (
            not relational_veto
            and float(item["survival_probability"]) <= limit
        )
        if base:
            base_seen.add(trade_index)

        belief: CausalHypothesisBelief = item["belief"]
        confident = belief.confidence_bps >= confidence_floor
        favorable = (
            confident
            and belief.disposition is CausalBeliefDisposition.FAVORABLE_DOMINANT
        )
        terminal = (
            confident
            and belief.disposition is CausalBeliefDisposition.TERMINAL_DOMINANT
        )

        if mode == "VETO_ONLY":
            selected = base and not favorable
        elif mode == "TERMINAL_ADD_ONLY":
            selected = base or (terminal and not relational_veto)
        elif mode == "TWO_SIDED":
            selected = (
                (base and not favorable)
                or (not base and terminal and not relational_veto)
            )
        else:
            raise ValueError(f"unknown arbitration mode: {mode}")

        if not selected:
            if base and favorable:
                vetoed += 1
                favorable_vetoes += 1
            continue

        if not base:
            added += 1
            if terminal:
                terminal_additions += 1
        chosen[trade_index] = item

    return chosen, {
        "added": added,
        "vetoed": vetoed,
        "terminal_additions": terminal_additions,
        "favorable_vetoes": favorable_vetoes,
        "base_trade_count_seen": len(base_seen),
    }


def _metrics(
    *,
    trades: list[dict[str, Any]],
    chosen: dict[int, dict[str, Any]],
    audit: dict[str, int],
) -> ArbitrationMetrics:
    losses = sum(trade["actual"] == "LOSS" for trade in trades)
    winners = sum(trade["actual"] == "WIN" for trade in trades)
    true_loss = [index for index in chosen if trades[index]["actual"] == "LOSS"]
    false_winner = [index for index in chosen if trades[index]["actual"] == "WIN"]
    leads = [
        int(chosen[index]["row"]["bars_before_canonical_exit"])
        for index in true_loss
    ]
    return ArbitrationMetrics(
        selected=len(chosen),
        true_loss=len(true_loss),
        false_winner=len(false_winner),
        precision=_ratio(len(true_loss), len(chosen)),
        loss_recall=_ratio(len(true_loss), losses),
        winner_mark_rate=_ratio(len(false_winner), winners),
        median_lead_bars=None if not leads else Decimal(str(median(leads))),
        added=audit["added"],
        vetoed=audit["vetoed"],
        terminal_additions=audit["terminal_additions"],
        favorable_vetoes=audit["favorable_vetoes"],
    )


def _payload(metrics: ArbitrationMetrics) -> dict[str, object]:
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
        "added": metrics.added,
        "vetoed": metrics.vetoed,
        "terminal_additions": metrics.terminal_additions,
        "favorable_vetoes": metrics.favorable_vetoes,
    }


def _v21_metrics(
    *,
    trades: list[dict[str, Any]],
    surface: list[dict[str, Any]],
    threshold: Decimal,
) -> ArbitrationMetrics:
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
    return _metrics(
        trades=trades,
        chosen=chosen,
        audit={
            "added": 0,
            "vetoed": 0,
            "terminal_additions": 0,
            "favorable_vetoes": 0,
        },
    )


def _choose_policy(
    *,
    trades: list[dict[str, Any]],
    surface: list[dict[str, Any]],
    threshold: Decimal,
) -> tuple[str | None, int | None, ArbitrationMetrics | None, list[dict[str, object]]]:
    baseline = _v21_metrics(trades=trades, surface=surface, threshold=threshold)
    admitted: list[tuple[ArbitrationMetrics, str, int]] = []
    audit: list[dict[str, object]] = []

    for mode in MODES:
        for floor in CONFIDENCE_FLOORS:
            chosen, selection_audit = _select(
                surface=surface,
                v21_threshold=threshold,
                mode=mode,
                confidence_floor=floor,
            )
            metrics = _metrics(
                trades=trades,
                chosen=chosen,
                audit=selection_audit,
            )
            changed = metrics.added + metrics.vetoed > 0
            passed = (
                changed
                and metrics.selected >= MIN_SELECTED_TRADES
                and metrics.precision >= TRAIN_PRECISION_FLOOR
                and metrics.winner_mark_rate <= WINNER_MARK_CEILING
                and metrics.loss_recall >= baseline.loss_recall
                and metrics.median_lead_bars is not None
                and metrics.median_lead_bars >= MIN_MEDIAN_LEAD_BARS
            )
            audit.append(
                {
                    "mode": mode,
                    "confidence_floor_bps": floor,
                    **_payload(metrics),
                    "admitted": passed,
                }
            )
            if passed:
                admitted.append((metrics, mode, floor))

    if not admitted:
        return None, None, None, audit

    metrics, mode, floor = max(
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
    return mode, floor, metrics, audit


def _window(
    *,
    trades: list[dict[str, Any]],
    surface: list[dict[str, Any]],
    threshold: Decimal,
    mode: str,
    confidence_floor: int,
    event_model: HistGradientBoostingClassifier,
    categories: dict[str, tuple[str, ...]],
) -> dict[str, object]:
    baseline = _v21_metrics(trades=trades, surface=surface, threshold=threshold)
    chosen, audit = _select(
        surface=surface,
        v21_threshold=threshold,
        mode=mode,
        confidence_floor=confidence_floor,
    )
    metrics = _metrics(trades=trades, chosen=chosen, audit=audit)
    passed = (
        metrics.selected >= MIN_SELECTED_TRADES
        and metrics.precision >= VALIDATION_PRECISION_FLOOR
        and metrics.winner_mark_rate <= WINNER_MARK_CEILING
        and metrics.loss_recall >= baseline.loss_recall
        and metrics.median_lead_bars is not None
        and metrics.median_lead_bars >= MIN_MEDIAN_LEAD_BARS
    )
    return {
        "sample": len(trades),
        "event_adverse_auc": _event_auc(
            model=event_model,
            trades=trades,
            categories=categories,
        ),
        "v21": _payload(baseline),
        "v23": _payload(metrics),
        "recall_delta_vs_v21": str(metrics.loss_recall - baseline.loss_recall),
        "precision_delta_vs_v21": str(metrics.precision - baseline.precision),
        "winner_mark_delta_vs_v21": str(
            metrics.winner_mark_rate - baseline.winner_mark_rate
        ),
        "status": "ADMIT_FOR_ECONOMIC_SHADOW" if passed else "REJECT",
    }


def _rejection(
    *,
    v21_threshold: Decimal,
    audit: list[dict[str, object]],
) -> dict[str, object]:
    return {
        "schema": SCHEMA,
        "identity": IDENTITY,
        "source_v6_run": SOURCE_V6_RUN,
        "source_v20_run": SOURCE_V20_RUN,
        "source_v21_run": SOURCE_V21_RUN,
        "source_v22d_r3_run": SOURCE_V22D_R3_RUN,
        "research_only": True,
        "shared_autonomous_model": True,
        "sequence_event_model": True,
        "persistent_causal_hypothesis_belief": True,
        "bidirectional_arbitration": True,
        "policy_selected_on_five_year_only": True,
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
        "closed_outcome_used_offline_for_training_and_scoring_only": True,
        "v21_survival_threshold_frozen": str(v21_threshold),
        "sequence_feature_names": _sequence_feature_names(),
        "belief_policy": {
            "decay_bps": BELIEF_DECAY_BPS,
            "maximum_frames": BELIEF_MAX_FRAMES,
            "dominance_margin_bps": BELIEF_DOMINANCE_MARGIN_BPS,
        },
        "selected_policy": None,
        "policy_audit": audit,
        "windows": {},
        "validation_pass": False,
        "scientific_status": "REJECT",
        "rejection_reason": "NO_FIVE_YEAR_SEQUENCE_POLICY_PRESERVES_V21_RECALL_AND_SAFETY",
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
        train_survival_probabilities,
        train_meta,
    ) = v21._fit_survival(
        hazard_model=hazard_model,
        categories=categories,
        trades=train_trades,
    )
    v21_threshold, _, _ = v21._choose_threshold(
        trades=train_trades,
        probabilities=train_survival_probabilities,
        meta=train_meta,
    )
    if v21_threshold is None:
        raise ValueError("V21 frozen threshold unavailable")

    event_model = _fit_event_model(
        trades=train_trades,
        categories=categories,
    )
    surfaces = {
        key: _candidate_surface(
            hazard_model=hazard_model,
            survival_model=survival_model,
            event_model=event_model,
            categories=categories,
            trades=list(ledger[key]["rows"]),
        )
        for key in WINDOWS
    }

    mode, confidence_floor, train_metrics, policy_audit = _choose_policy(
        trades=train_trades,
        surface=surfaces[TRAIN_WINDOW],
        threshold=v21_threshold,
    )
    if mode is None or confidence_floor is None or train_metrics is None:
        return _rejection(v21_threshold=v21_threshold, audit=policy_audit)

    windows = {
        key: _window(
            trades=list(ledger[key]["rows"]),
            surface=surfaces[key],
            threshold=v21_threshold,
            mode=mode,
            confidence_floor=confidence_floor,
            event_model=event_model,
            categories=categories,
        )
        for key in WINDOWS
    }
    all_safe = all(
        windows[key]["status"] == "ADMIT_FOR_ECONOMIC_SHADOW"
        for key in WINDOWS
    )
    validation_improvement = any(
        (
            Decimal(str(windows[key]["recall_delta_vs_v21"])) > 0
            or Decimal(str(windows[key]["winner_mark_delta_vs_v21"])) < 0
            or Decimal(str(windows[key]["precision_delta_vs_v21"])) > 0
        )
        for key in VALIDATION_WINDOWS
    )
    validation_pass = all_safe and validation_improvement

    return {
        "schema": SCHEMA,
        "identity": IDENTITY,
        "source_v6_run": SOURCE_V6_RUN,
        "source_v20_run": SOURCE_V20_RUN,
        "source_v21_run": SOURCE_V21_RUN,
        "source_v22d_r3_run": SOURCE_V22D_R3_RUN,
        "research_only": True,
        "shared_autonomous_model": True,
        "sequence_event_model": True,
        "persistent_causal_hypothesis_belief": True,
        "bidirectional_arbitration": True,
        "terminal_additions_cannot_override_relational_winner_veto": True,
        "policy_selected_on_five_year_only": True,
        "policy_frozen_across_validation_windows": True,
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
        "closed_outcome_used_offline_for_training_and_scoring_only": True,
        "v21_survival_threshold_frozen": str(v21_threshold),
        "sequence_feature_count": len(_sequence_feature_names()),
        "sequence_feature_names": _sequence_feature_names(),
        "event_model": {
            "kind": "HIST_GRADIENT_BOOSTING_NEAR_TERM_CAUSAL_EVENT",
            **MODEL_PARAMS,
        },
        "belief_policy": {
            "decay_bps": BELIEF_DECAY_BPS,
            "maximum_frames": BELIEF_MAX_FRAMES,
            "dominance_margin_bps": BELIEF_DOMINANCE_MARGIN_BPS,
        },
        "selected_policy": {
            "mode": mode,
            "confidence_floor_bps": confidence_floor,
        },
        "train_selected_metrics": _payload(train_metrics),
        "policy_audit": policy_audit,
        "pass_law": {
            "loss_recall": "V23 >= V21 in every consumed window",
            "training_precision_floor": str(TRAIN_PRECISION_FLOOR),
            "validation_precision_floor": str(VALIDATION_PRECISION_FLOOR),
            "winner_mark_ceiling": str(WINNER_MARK_CEILING),
            "minimum_selected_trades": MIN_SELECTED_TRADES,
            "minimum_median_lead_bars": str(MIN_MEDIAN_LEAD_BARS),
            "held_window_improvement_required": True,
        },
        "windows": windows,
        "validation_improvement": validation_improvement,
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

"""V24 dynamic Bayesian causal-state arbitration for Shared Core.

V23 proved that a simple decayed belief accumulator can raise loss recall only
by flooding winner marks. V24 replaces that scalar accumulator with a genuine
state filter:

- a five-state near-term event emission model;
- a train-only causal transition matrix between event states;
- sequential Bayesian filtering with uncertainty tempering;
- persistent adverse/favorable posterior regimes;
- bidirectional arbitration around frozen V21.

The runtime path uses only point-in-time market evidence, a frozen transition
matrix, and bounded causal history. CLOSED outcomes are used offline only to
fit the five-year emission/transition models and to score consumed evidence.
Fresh holdout remains closed.
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
import shared_relational_adversity_challenge_survival_v21 as v21
import shared_sequence_event_causal_belief_v23 as v23
from sklearn.ensemble import HistGradientBoostingClassifier

from qore.infrastructure.core_stack_v2.causal_state_filter import (
    CausalStateEmission,
    FilteredCausalStateBelief,
    filter_causal_state_sequence,
)

IDENTITY = "QORE_SHARED_DYNAMIC_BAYESIAN_CAUSAL_STATE_V24"
SCHEMA = "qore.shared.dynamic_bayesian_causal_state.v24"

SOURCE_V6_RUN = 36131607443
SOURCE_V21_RUN = 36156421332
SOURCE_V23_RUN = 36179306142

TRAIN_WINDOW = v21.TRAIN_WINDOW
VALIDATION_WINDOWS = v21.VALIDATION_WINDOWS
WINDOWS = (TRAIN_WINDOW, *VALIDATION_WINDOWS)

TRAIN_PRECISION_FLOOR = Decimal("0.95")
VALIDATION_PRECISION_FLOOR = Decimal("0.90")
WINNER_MARK_CEILING = Decimal("0.01")
MIN_SELECTED_TRADES = 20
MIN_MEDIAN_LEAD_BARS = Decimal("1")

MARGIN_FLOORS_BPS = (250, 500, 750, 1_000, 1_500, 2_000)
PERSISTENCE_FLOORS = (2, 3, 4)
MODES = ("VETO_ONLY", "TERMINAL_ADD_ONLY", "TWO_SIDED")
LAPLACE_TRANSITION_COUNT = 2

STATES = tuple(v21.v20.CAUSES)
ADVERSE_STATES = frozenset({v21.v20.CAUSE_STOP, v21.v20.CAUSE_TERMINAL})
FAVORABLE_STATES = frozenset({v21.v20.CAUSE_RECOVERY, v21.v20.CAUSE_TARGET})


@dataclass(frozen=True, slots=True)
class DynamicState:
    belief: FilteredCausalStateBelief
    adverse_bps: int
    favorable_bps: int
    no_event_bps: int
    adverse_margin_bps: int
    favorable_margin_bps: int
    adverse_persistence: int
    favorable_persistence: int


@dataclass(frozen=True, slots=True)
class Metrics:
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


def _normalize_bps(counts: dict[str, int]) -> dict[str, int]:
    total = sum(counts.values())
    raw = {key: value * 10_000 / total for key, value in counts.items()}
    result = {key: int(value) for key, value in raw.items()}
    remainder = 10_000 - sum(result.values())
    order = sorted(
        counts,
        key=lambda key: raw[key] - result[key],
        reverse=True,
    )
    for key in order[:remainder]:
        result[key] += 1
    return result


def _transition_matrix(
    trades: list[dict[str, Any]],
) -> dict[str, dict[str, int]]:
    counts = {
        source: {target: LAPLACE_TRANSITION_COUNT for target in STATES}
        for source in STATES
    }
    for trade in trades:
        rows = v21.v20._eligible(trade)
        labels = [
            v21.v20._next_cause(trade=trade, rows=rows, index=index)
            for index in range(len(rows))
        ]
        for source, target in zip(labels, labels[1:], strict=False):
            counts[source][target] += 1
    return {
        source: _normalize_bps(row)
        for source, row in counts.items()
    }


def _entropy_bps(probabilities: dict[str, float]) -> int:
    active = [value for value in probabilities.values() if value > 0]
    if len(active) <= 1:
        return 0
    entropy = -sum(value * math.log(value) for value in active)
    return max(
        0,
        min(
            10_000,
            int(round(entropy / math.log(len(STATES)) * 10_000)),
        ),
    )


def _emission_bps(
    probabilities: dict[str, float],
) -> tuple[tuple[str, int], ...]:
    raw = {
        state: max(0.0, float(probabilities.get(state, 0.0))) * 10_000.0
        for state in STATES
    }
    ints = {state: int(value) for state, value in raw.items()}
    remainder = 10_000 - sum(ints.values())
    order = sorted(
        STATES,
        key=lambda state: raw[state] - ints[state],
        reverse=True,
    )
    if remainder > 0:
        for state in order[:remainder]:
            ints[state] += 1
    elif remainder < 0:
        for state in reversed(order[: -remainder]):
            ints[state] = max(0, ints[state] - 1)
    return tuple((state, ints[state]) for state in STATES)


def _state_map(
    *,
    event_model: HistGradientBoostingClassifier,
    trades: list[dict[str, Any]],
    categories: dict[str, tuple[str, ...]],
    transition_bps: dict[str, dict[str, int]],
) -> dict[tuple[int, str], DynamicState]:
    x_rows, _, _, meta = v23._dataset(trades, categories)
    probability_rows = event_model.predict_proba(x_rows)
    classes = tuple(str(value) for value in event_model.classes_)

    emissions: dict[int, list[tuple[dict[str, Any], CausalStateEmission]]] = defaultdict(list)
    for values, (trade_index, row) in zip(probability_rows, meta, strict=True):
        probabilities = {state: 0.0 for state in STATES}
        for label, probability in zip(classes, values, strict=True):
            probabilities[label] = float(probability)
        emissions[trade_index].append(
            (
                row,
                CausalStateEmission(
                    as_of=v23.datetime.fromisoformat(str(row["as_of"])),
                    probabilities_bps=_emission_bps(probabilities),
                    uncertainty_bps=max(
                        int(row["uncertainty_bps"]),
                        _entropy_bps(probabilities),
                    ),
                    data_integrity_bps=10_000,
                ),
            )
        )

    result: dict[tuple[int, str], DynamicState] = {}
    for trade_index, items in emissions.items():
        beliefs = filter_causal_state_sequence(
            tuple(frame for _, frame in items),
            transition_bps=transition_bps,
        )
        adverse_run = 0
        favorable_run = 0
        for (row, _), belief in zip(items, beliefs, strict=True):
            adverse = sum(
                belief.probability_bps(state)
                for state in ADVERSE_STATES
            )
            favorable = sum(
                belief.probability_bps(state)
                for state in FAVORABLE_STATES
            )
            no_event = belief.probability_bps(v21.v20.CAUSE_NONE)
            adverse_margin = adverse - max(favorable, no_event)
            favorable_margin = favorable - max(adverse, no_event)
            if adverse_margin > 0:
                adverse_run += 1
            else:
                adverse_run = 0
            if favorable_margin > 0:
                favorable_run += 1
            else:
                favorable_run = 0
            result[(trade_index, str(row["as_of"]))] = DynamicState(
                belief=belief,
                adverse_bps=adverse,
                favorable_bps=favorable,
                no_event_bps=no_event,
                adverse_margin_bps=adverse_margin,
                favorable_margin_bps=favorable_margin,
                adverse_persistence=adverse_run,
                favorable_persistence=favorable_run,
            )
    return result


def _surface(
    *,
    hazard_model: HistGradientBoostingClassifier,
    survival_model: HistGradientBoostingClassifier,
    event_model: HistGradientBoostingClassifier,
    categories: dict[str, tuple[str, ...]],
    transition_bps: dict[str, dict[str, int]],
    trades: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    x_rows, _, _, meta = v21._candidate_dataset(
        hazard_model=hazard_model,
        categories=categories,
        trades=trades,
    )
    survival_probabilities = survival_model.predict_proba(x_rows)[:, 1]
    states = _state_map(
        event_model=event_model,
        trades=trades,
        categories=categories,
        transition_bps=transition_bps,
    )
    return [
        {
            **item,
            "survival_probability": float(probability),
            "dynamic_state": states[
                (int(item["trade_index"]), str(item["row"]["as_of"]))
            ],
        }
        for probability, item in zip(survival_probabilities, meta, strict=True)
    ]


def _select(
    *,
    surface: list[dict[str, Any]],
    v21_threshold: Decimal,
    mode: str,
    margin_floor_bps: int,
    persistence_floor: int,
) -> tuple[dict[int, dict[str, Any]], dict[str, int]]:
    chosen: dict[int, dict[str, Any]] = {}
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
        state: DynamicState = item["dynamic_state"]

        adverse_confirmed = (
            state.adverse_margin_bps >= margin_floor_bps
            and state.adverse_persistence >= persistence_floor
        )
        favorable_confirmed = (
            state.favorable_margin_bps >= margin_floor_bps
            and state.favorable_persistence >= persistence_floor
        )

        if mode == "VETO_ONLY":
            selected = base and not favorable_confirmed
        elif mode == "TERMINAL_ADD_ONLY":
            selected = base or (adverse_confirmed and not relational_veto)
        elif mode == "TWO_SIDED":
            selected = (
                (base and not favorable_confirmed)
                or (not base and adverse_confirmed and not relational_veto)
            )
        else:
            raise ValueError(f"unknown arbitration mode: {mode}")

        if not selected:
            if base and favorable_confirmed:
                vetoed += 1
                favorable_vetoes += 1
            continue

        if not base:
            added += 1
            if adverse_confirmed:
                terminal_additions += 1
        chosen[trade_index] = item

    return chosen, {
        "added": added,
        "vetoed": vetoed,
        "terminal_additions": terminal_additions,
        "favorable_vetoes": favorable_vetoes,
    }


def _metrics(
    *,
    trades: list[dict[str, Any]],
    chosen: dict[int, dict[str, Any]],
    audit: dict[str, int],
) -> Metrics:
    losses = sum(trade["actual"] == "LOSS" for trade in trades)
    winners = sum(trade["actual"] == "WIN" for trade in trades)
    true_loss = [index for index in chosen if trades[index]["actual"] == "LOSS"]
    false_winner = [index for index in chosen if trades[index]["actual"] == "WIN"]
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
        median_lead_bars=None if not leads else Decimal(str(median(leads))),
        added=audit["added"],
        vetoed=audit["vetoed"],
        terminal_additions=audit["terminal_additions"],
        favorable_vetoes=audit["favorable_vetoes"],
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
        "added": metrics.added,
        "vetoed": metrics.vetoed,
        "terminal_additions": metrics.terminal_additions,
        "favorable_vetoes": metrics.favorable_vetoes,
    }


def _baseline(
    *,
    trades: list[dict[str, Any]],
    surface: list[dict[str, Any]],
    threshold: Decimal,
) -> Metrics:
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
) -> tuple[str | None, int | None, int | None, Metrics | None, list[dict[str, object]]]:
    baseline = _baseline(trades=trades, surface=surface, threshold=threshold)
    admitted: list[tuple[Metrics, str, int, int]] = []
    audit: list[dict[str, object]] = []

    for mode in MODES:
        for margin in MARGIN_FLOORS_BPS:
            for persistence in PERSISTENCE_FLOORS:
                chosen, selection_audit = _select(
                    surface=surface,
                    v21_threshold=threshold,
                    mode=mode,
                    margin_floor_bps=margin,
                    persistence_floor=persistence,
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
                        "margin_floor_bps": margin,
                        "persistence_floor": persistence,
                        **_payload(metrics),
                        "admitted": passed,
                    }
                )
                if passed:
                    admitted.append((metrics, mode, margin, persistence))

    if not admitted:
        return None, None, None, None, audit

    metrics, mode, margin, persistence = max(
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
    return mode, margin, persistence, metrics, audit


def _window(
    *,
    trades: list[dict[str, Any]],
    surface: list[dict[str, Any]],
    threshold: Decimal,
    mode: str,
    margin_floor_bps: int,
    persistence_floor: int,
) -> dict[str, object]:
    baseline = _baseline(trades=trades, surface=surface, threshold=threshold)
    chosen, audit = _select(
        surface=surface,
        v21_threshold=threshold,
        mode=mode,
        margin_floor_bps=margin_floor_bps,
        persistence_floor=persistence_floor,
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
        "v21": _payload(baseline),
        "v24": _payload(metrics),
        "recall_delta_vs_v21": str(metrics.loss_recall - baseline.loss_recall),
        "precision_delta_vs_v21": str(metrics.precision - baseline.precision),
        "winner_mark_delta_vs_v21": str(
            metrics.winner_mark_rate - baseline.winner_mark_rate
        ),
        "status": "ADMIT_FOR_ECONOMIC_SHADOW" if passed else "REJECT",
    }


def _rejection(
    *,
    threshold: Decimal,
    transition_bps: dict[str, dict[str, int]],
    event_auc: str | None,
    audit: list[dict[str, object]],
) -> dict[str, object]:
    return {
        "schema": SCHEMA,
        "identity": IDENTITY,
        "source_v6_run": SOURCE_V6_RUN,
        "source_v21_run": SOURCE_V21_RUN,
        "source_v23_run": SOURCE_V23_RUN,
        "research_only": True,
        "shared_autonomous_model": True,
        "dynamic_bayesian_state_filter": True,
        "train_only_transition_matrix": True,
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
        "v21_survival_threshold_frozen": str(threshold),
        "event_adverse_auc_train": event_auc,
        "transition_matrix_bps": transition_bps,
        "selected_policy": None,
        "policy_audit": audit,
        "windows": {},
        "validation_pass": False,
        "scientific_status": "REJECT",
        "rejection_reason": "NO_TRAIN_DYNAMIC_POLICY_PRESERVES_V21_RECALL_AND_SAFETY",
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

    event_model = v23._fit_event_model(
        trades=train_trades,
        categories=categories,
    )
    transition_bps = _transition_matrix(train_trades)
    surfaces = {
        key: _surface(
            hazard_model=hazard_model,
            survival_model=survival_model,
            event_model=event_model,
            categories=categories,
            transition_bps=transition_bps,
            trades=list(ledger[key]["rows"]),
        )
        for key in WINDOWS
    }
    mode, margin, persistence, train_metrics, audit = _choose_policy(
        trades=train_trades,
        surface=surfaces[TRAIN_WINDOW],
        threshold=threshold,
    )
    event_auc = v23._event_auc(
        model=event_model,
        trades=train_trades,
        categories=categories,
    )
    if (
        mode is None
        or margin is None
        or persistence is None
        or train_metrics is None
    ):
        return _rejection(
            threshold=threshold,
            transition_bps=transition_bps,
            event_auc=event_auc,
            audit=audit,
        )

    windows = {
        key: _window(
            trades=list(ledger[key]["rows"]),
            surface=surfaces[key],
            threshold=threshold,
            mode=mode,
            margin_floor_bps=margin,
            persistence_floor=persistence,
        )
        for key in WINDOWS
    }
    all_safe = all(
        windows[key]["status"] == "ADMIT_FOR_ECONOMIC_SHADOW"
        for key in WINDOWS
    )
    held_improvement = any(
        (
            Decimal(str(windows[key]["recall_delta_vs_v21"])) > 0
            or Decimal(str(windows[key]["winner_mark_delta_vs_v21"])) < 0
            or Decimal(str(windows[key]["precision_delta_vs_v21"])) > 0
        )
        for key in VALIDATION_WINDOWS
    )
    validation_pass = all_safe and held_improvement

    return {
        "schema": SCHEMA,
        "identity": IDENTITY,
        "source_v6_run": SOURCE_V6_RUN,
        "source_v21_run": SOURCE_V21_RUN,
        "source_v23_run": SOURCE_V23_RUN,
        "research_only": True,
        "shared_autonomous_model": True,
        "dynamic_bayesian_state_filter": True,
        "train_only_transition_matrix": True,
        "transition_matrix_frozen_across_validation_windows": True,
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
        "v21_survival_threshold_frozen": str(threshold),
        "event_adverse_auc_train": event_auc,
        "transition_matrix_bps": transition_bps,
        "selected_policy": {
            "mode": mode,
            "margin_floor_bps": margin,
            "persistence_floor": persistence,
        },
        "train_selected_metrics": _payload(train_metrics),
        "policy_audit": audit,
        "pass_law": {
            "loss_recall": "V24 >= V21 in every consumed window",
            "training_precision_floor": str(TRAIN_PRECISION_FLOOR),
            "validation_precision_floor": str(VALIDATION_PRECISION_FLOOR),
            "winner_mark_ceiling": str(WINNER_MARK_CEILING),
            "minimum_selected_trades": MIN_SELECTED_TRADES,
            "minimum_median_lead_bars": str(MIN_MEDIAN_LEAD_BARS),
            "held_window_improvement_required": True,
        },
        "windows": windows,
        "held_window_improvement": held_improvement,
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
                "event_adverse_auc_train": payload.get("event_adverse_auc_train"),
                "windows": payload.get("windows"),
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()

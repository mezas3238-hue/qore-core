"""V25-R1 factorized posterior arbitration for Shared Core.

V25-R0 showed that V24's five-state posterior was dominated by NO_EVENT in
every candidate group. As a result, adverse/favorable persistence was always
zero even when conditional directional information existed.

R1 changes the representation, not the labels:
- NO_EVENT becomes an event-readiness axis;
- STOP+TERMINAL vs RECOVERY+TARGET becomes a separate conditional direction;
- persistence is tracked on conditional direction, independent of NO_EVENT;
- train-only policy search chooses event floor, directional margin, persistence,
  and arbitration mode on five-year consumed evidence;
- policy is frozen unchanged on recent-two-year and R66 consumed windows.

The frozen V21 survival gate remains the baseline. Favorable conditional
direction may veto a V21 mark; adverse conditional direction may recover a
survival-vetoed loss candidate, but never override the independent relational
winner veto.

No runtime PnL, future market, identity, sizing, risk weighting, order or broker
information is used. Fresh holdout remains closed.
"""

# ruff: noqa: E501,I001

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from statistics import median
from typing import Any

import shared_dynamic_bayesian_causal_state_v24 as v24
import shared_relational_adversity_challenge_survival_v21 as v21
from sklearn.ensemble import HistGradientBoostingClassifier

from qore.infrastructure.core_stack_v2.factorized_causal_state import (
    FactorizedCausalState,
    factorize_causal_state,
)

IDENTITY = "QORE_SHARED_V25_R1_FACTORIZED_POSTERIOR_ARBITRATION"
SCHEMA = "qore.shared.v25_r1_factorized_posterior_arbitration"

SOURCE_V6_RUN = 36131607443
SOURCE_V21_RUN = 36156421332
SOURCE_V24_RUN = 36185092496
SOURCE_V25_R0_RUN = 36186661355

TRAIN_WINDOW = v21.TRAIN_WINDOW
VALIDATION_WINDOWS = v21.VALIDATION_WINDOWS
WINDOWS = (TRAIN_WINDOW, *VALIDATION_WINDOWS)

TRAIN_PRECISION_FLOOR = Decimal("0.95")
VALIDATION_PRECISION_FLOOR = Decimal("0.90")
WINNER_MARK_CEILING = Decimal("0.01")
MIN_SELECTED_TRADES = 20
MIN_MEDIAN_LEAD_BARS = Decimal("1")

EVENT_FLOORS_BPS = (2_000, 3_000, 4_000, 5_000, 6_000)
DIRECTION_MARGIN_FLOORS_BPS = (500, 1_000, 1_500, 2_000, 3_000)
PERSISTENCE_FLOORS = (1, 2, 3)
MODES = ("VETO_ONLY", "TERMINAL_ADD_ONLY", "TWO_SIDED")

ADVERSE_STATES = frozenset({v21.v20.CAUSE_STOP, v21.v20.CAUSE_TERMINAL})
FAVORABLE_STATES = frozenset({v21.v20.CAUSE_RECOVERY, v21.v20.CAUSE_TARGET})
NO_EVENT_STATE = v21.v20.CAUSE_NONE


@dataclass(frozen=True, slots=True)
class FactorizedDynamicState:
    state: FactorizedCausalState
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
    adverse_additions: int
    favorable_vetoes: int


def _ratio(n: int, d: int) -> Decimal:
    return Decimal("0") if d <= 0 else Decimal(n) / Decimal(d)


def _factorized_map(
    *,
    event_model: HistGradientBoostingClassifier,
    trades: list[dict[str, Any]],
    categories: dict[str, tuple[str, ...]],
    transition_bps: dict[str, dict[str, int]],
) -> dict[tuple[int, str], FactorizedDynamicState]:
    dynamic = v24._state_map(
        event_model=event_model,
        trades=trades,
        categories=categories,
        transition_bps=transition_bps,
    )
    by_trade: dict[int, list[tuple[str, FactorizedCausalState]]] = {}

    for (trade_index, as_of), item in dynamic.items():
        factorized = factorize_causal_state(
            item.belief,
            adverse_states=ADVERSE_STATES,
            favorable_states=FAVORABLE_STATES,
            no_event_state=NO_EVENT_STATE,
        )
        by_trade.setdefault(trade_index, []).append((as_of, factorized))

    result: dict[tuple[int, str], FactorizedDynamicState] = {}
    for trade_index, items in by_trade.items():
        items.sort(key=lambda pair: pair[0])
        adverse_run = 0
        favorable_run = 0
        for as_of, state in items:
            if state.directional_margin_bps > 0:
                adverse_run += 1
                favorable_run = 0
            elif state.directional_margin_bps < 0:
                favorable_run += 1
                adverse_run = 0
            else:
                adverse_run = 0
                favorable_run = 0
            result[(trade_index, as_of)] = FactorizedDynamicState(
                state=state,
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
    states = _factorized_map(
        event_model=event_model,
        trades=trades,
        categories=categories,
        transition_bps=transition_bps,
    )
    return [
        {
            **item,
            "survival_probability": float(probability),
            "factorized_state": states[
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
    event_floor_bps: int,
    direction_margin_floor_bps: int,
    persistence_floor: int,
) -> tuple[dict[int, dict[str, Any]], dict[str, int]]:
    chosen: dict[int, dict[str, Any]] = {}
    added = vetoed = adverse_additions = favorable_vetoes = 0
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
        factorized: FactorizedDynamicState = item["factorized_state"]
        state = factorized.state
        event_ready = state.event_bps >= event_floor_bps

        adverse_confirmed = (
            event_ready
            and state.directional_margin_bps >= direction_margin_floor_bps
            and factorized.adverse_persistence >= persistence_floor
        )
        favorable_confirmed = (
            event_ready
            and -state.directional_margin_bps >= direction_margin_floor_bps
            and factorized.favorable_persistence >= persistence_floor
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
                adverse_additions += 1
        chosen[trade_index] = item

    return chosen, {
        "added": added,
        "vetoed": vetoed,
        "adverse_additions": adverse_additions,
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
        adverse_additions=audit["adverse_additions"],
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
        "adverse_additions": metrics.adverse_additions,
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
            "adverse_additions": 0,
            "favorable_vetoes": 0,
        },
    )


def _choose_policy(
    *,
    trades: list[dict[str, Any]],
    surface: list[dict[str, Any]],
    threshold: Decimal,
) -> tuple[
    str | None,
    int | None,
    int | None,
    int | None,
    Metrics | None,
    list[dict[str, object]],
]:
    baseline = _baseline(trades=trades, surface=surface, threshold=threshold)
    admitted: list[tuple[Metrics, str, int, int, int]] = []
    audit: list[dict[str, object]] = []

    for mode in MODES:
        for event_floor in EVENT_FLOORS_BPS:
            for margin in DIRECTION_MARGIN_FLOORS_BPS:
                for persistence in PERSISTENCE_FLOORS:
                    chosen, selection_audit = _select(
                        surface=surface,
                        v21_threshold=threshold,
                        mode=mode,
                        event_floor_bps=event_floor,
                        direction_margin_floor_bps=margin,
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
                            "event_floor_bps": event_floor,
                            "direction_margin_floor_bps": margin,
                            "persistence_floor": persistence,
                            **_payload(metrics),
                            "admitted": passed,
                        }
                    )
                    if passed:
                        admitted.append(
                            (metrics, mode, event_floor, margin, persistence)
                        )

    if not admitted:
        return None, None, None, None, None, audit

    metrics, mode, event_floor, margin, persistence = max(
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
    return mode, event_floor, margin, persistence, metrics, audit


def _window(
    *,
    trades: list[dict[str, Any]],
    surface: list[dict[str, Any]],
    threshold: Decimal,
    mode: str,
    event_floor_bps: int,
    direction_margin_floor_bps: int,
    persistence_floor: int,
) -> dict[str, object]:
    baseline = _baseline(trades=trades, surface=surface, threshold=threshold)
    chosen, audit = _select(
        surface=surface,
        v21_threshold=threshold,
        mode=mode,
        event_floor_bps=event_floor_bps,
        direction_margin_floor_bps=direction_margin_floor_bps,
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
        "v25r1": _payload(metrics),
        "recall_delta_vs_v21": str(metrics.loss_recall - baseline.loss_recall),
        "precision_delta_vs_v21": str(metrics.precision - baseline.precision),
        "winner_mark_delta_vs_v21": str(
            metrics.winner_mark_rate - baseline.winner_mark_rate
        ),
        "status": "ADMIT_FOR_ECONOMIC_SHADOW" if passed else "REJECT",
    }


def _base_payload(threshold: Decimal) -> dict[str, object]:
    return {
        "schema": SCHEMA,
        "identity": IDENTITY,
        "source_v6_run": SOURCE_V6_RUN,
        "source_v21_run": SOURCE_V21_RUN,
        "source_v24_run": SOURCE_V24_RUN,
        "source_v25_r0_run": SOURCE_V25_R0_RUN,
        "research_only": True,
        "shared_autonomous_model": True,
        "factorized_event_and_direction": True,
        "no_event_cannot_erase_directional_belief": True,
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

    event_model = v24.v23._fit_event_model(
        trades=train_trades,
        categories=categories,
    )
    transition_bps = v24._transition_matrix(train_trades)
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

    (
        mode,
        event_floor,
        margin,
        persistence,
        train_metrics,
        policy_audit,
    ) = _choose_policy(
        trades=train_trades,
        surface=surfaces[TRAIN_WINDOW],
        threshold=threshold,
    )

    common = _base_payload(threshold)
    common["transition_matrix_bps"] = transition_bps
    common["policy_audit"] = policy_audit

    if (
        mode is None
        or event_floor is None
        or margin is None
        or persistence is None
        or train_metrics is None
    ):
        return {
            **common,
            "selected_policy": None,
            "windows": {},
            "validation_pass": False,
            "scientific_status": "REJECT",
            "rejection_reason": (
                "NO_FIVE_YEAR_FACTORIZED_POLICY_PRESERVES_V21_RECALL_AND_SAFETY"
            ),
        }

    windows = {
        key: _window(
            trades=list(ledger[key]["rows"]),
            surface=surfaces[key],
            threshold=threshold,
            mode=mode,
            event_floor_bps=event_floor,
            direction_margin_floor_bps=margin,
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
        **common,
        "policy_frozen_across_validation_windows": True,
        "selected_policy": {
            "mode": mode,
            "event_floor_bps": event_floor,
            "direction_margin_floor_bps": margin,
            "persistence_floor": persistence,
        },
        "train_selected_metrics": _payload(train_metrics),
        "pass_law": {
            "loss_recall": "V25R1 >= V21 in every consumed window",
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
                "windows": payload.get("windows"),
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()

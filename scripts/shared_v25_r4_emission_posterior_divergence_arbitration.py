"""V25-R4 emission-posterior divergence arbitration for Shared Core.

V25-R2 exposed a stronger distinction than simple hypothesis ageing:
many false-winner marks show a large gap between the current raw event
emission and the slower filtered event posterior while the raw event impulse is
already decaying. True losses are often selected with much smaller divergence.

This stage tests whether an adverse mark should be temporarily delayed when:
- directional evidence remains adverse;
- the causal belief has matured;
- raw event readiness is materially above filtered event readiness;
- the raw event impulse is not strengthening.

The interpretation is causal: current adverse evidence is present, but it is
not yet supported by the accumulated state trajectory. The veto is temporary;
later reconfirmation may still select the trade.

All policy thresholds are chosen on five-year consumed evidence only and then
frozen unchanged on recent-two-year and R66 consumed windows. The frozen V21
survival threshold and V25-R1 slow adverse-addition route are unchanged.
Fresh holdout remains closed.
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
import shared_v25_r1_factorized_posterior_arbitration as v25r1

IDENTITY = "QORE_SHARED_V25_R4_EMISSION_POSTERIOR_DIVERGENCE_ARBITRATION"
SCHEMA = "qore.shared.v25_r4_emission_posterior_divergence_arbitration"

SOURCE_V6_RUN = 36131607443
SOURCE_V21_RUN = 36156421332
SOURCE_V24_RUN = 36185092496
SOURCE_V25_R1_RUN = 36187557918
SOURCE_V25_R2_RUN = 36194504049
SOURCE_V25_R3_RUN = 36195173804

TRAIN_WINDOW = v21.TRAIN_WINDOW
VALIDATION_WINDOWS = v21.VALIDATION_WINDOWS
WINDOWS = (TRAIN_WINDOW, *VALIDATION_WINDOWS)

TRAIN_PRECISION_FLOOR = Decimal("0.95")
VALIDATION_PRECISION_FLOOR = Decimal("0.90")
WINNER_MARK_CEILING = Decimal("0.01")
MIN_SELECTED_TRADES = 20
MIN_MEDIAN_LEAD_BARS = Decimal("1")

V25R1_MODE = "TERMINAL_ADD_ONLY"
V25R1_EVENT_FLOOR_BPS = 3_000
V25R1_DIRECTION_MARGIN_FLOOR_BPS = 2_000
V25R1_PERSISTENCE_FLOOR = 3

MATURITY_FLOORS = (2, 3, 4, 5)
MIN_RAW_POSTERIOR_GAPS_BPS = (500, 750, 1_000, 1_500, 2_000)
MAX_RAW_EVENT_DELTA1_BPS = (-1_000, -750, -500, -250, 0)
MAX_POSTERIOR_EVENT_BPS = (1_500, 2_000, 2_500, 3_000, 4_000)


@dataclass(frozen=True, slots=True)
class Metrics:
    selected: int
    true_loss: int
    false_winner: int
    precision: Decimal
    loss_recall: Decimal
    winner_mark_rate: Decimal
    median_lead_bars: Decimal | None
    divergence_vetoes: int
    divergence_true_loss_vetoes: int
    divergence_false_winner_vetoes: int
    slow_additions: int


def _ratio(n: int, d: int) -> Decimal:
    return Decimal("0") if d <= 0 else Decimal(n) / Decimal(d)


def _raw_event_map(
    *,
    event_model: Any,
    trades: list[dict[str, Any]],
    categories: dict[str, tuple[str, ...]],
) -> dict[tuple[int, str], dict[str, int]]:
    x_rows, _, _, meta = v24.v23._dataset(trades, categories)
    probability_rows = event_model.predict_proba(x_rows)
    classes = tuple(str(value) for value in event_model.classes_)

    per_trade: dict[int, list[tuple[str, int]]] = {}
    for values, (trade_index, row) in zip(probability_rows, meta, strict=True):
        probabilities = {state: 0.0 for state in v24.STATES}
        for label, probability in zip(classes, values, strict=True):
            probabilities[label] = float(probability)
        no_event = int(round(probabilities[v21.v20.CAUSE_NONE] * 10_000))
        event_bps = max(0, min(10_000, 10_000 - no_event))
        per_trade.setdefault(trade_index, []).append((str(row["as_of"]), event_bps))

    result: dict[tuple[int, str], dict[str, int]] = {}
    for trade_index, items in per_trade.items():
        items.sort(key=lambda pair: pair[0])
        prior_event: int | None = None
        for as_of, event_bps in items:
            delta1 = 0 if prior_event is None else event_bps - prior_event
            result[(trade_index, as_of)] = {
                "raw_event_bps": event_bps,
                "raw_event_delta1_bps": delta1,
            }
            prior_event = event_bps
    return result


def _surface(
    *,
    hazard_model: Any,
    survival_model: Any,
    event_model: Any,
    categories: dict[str, tuple[str, ...]],
    transition_bps: dict[str, dict[str, int]],
    trades: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    surface = v25r1._surface(
        hazard_model=hazard_model,
        survival_model=survival_model,
        event_model=event_model,
        categories=categories,
        transition_bps=transition_bps,
        trades=trades,
    )
    raw = _raw_event_map(
        event_model=event_model,
        trades=trades,
        categories=categories,
    )
    return [
        {
            **item,
            **raw[(int(item["trade_index"]), str(item["row"]["as_of"]))],
        }
        for item in surface
    ]


def _baseline_select(
    *,
    surface: list[dict[str, Any]],
    threshold: Decimal,
) -> dict[int, dict[str, Any]]:
    chosen, _ = v25r1._select(
        surface=surface,
        v21_threshold=threshold,
        mode=V25R1_MODE,
        event_floor_bps=V25R1_EVENT_FLOOR_BPS,
        direction_margin_floor_bps=V25R1_DIRECTION_MARGIN_FLOOR_BPS,
        persistence_floor=V25R1_PERSISTENCE_FLOOR,
    )
    return chosen


def _select(
    *,
    trades: list[dict[str, Any]],
    surface: list[dict[str, Any]],
    threshold: Decimal,
    maturity_floor: int,
    min_raw_posterior_gap_bps: int,
    max_raw_event_delta1_bps: int,
    max_posterior_event_bps: int,
) -> tuple[dict[int, dict[str, Any]], dict[str, int]]:
    chosen: dict[int, dict[str, Any]] = {}
    vetoed_trade_ids: set[int] = set()
    vetoed_true_loss_ids: set[int] = set()
    vetoed_false_winner_ids: set[int] = set()
    slow_additions = 0
    limit = float(threshold)

    for item in surface:
        trade_index = int(item["trade_index"])
        if trade_index in chosen:
            continue

        relational_veto = v21._relational_veto(item["challenge"])
        base = (
            not relational_veto
            and float(item["survival_probability"]) <= limit
        )
        factorized = item["factorized_state"]
        state = factorized.state

        slow_add = (
            not relational_veto
            and state.event_bps >= V25R1_EVENT_FLOOR_BPS
            and state.directional_margin_bps
            >= V25R1_DIRECTION_MARGIN_FLOOR_BPS
            and factorized.adverse_persistence >= V25R1_PERSISTENCE_FLOOR
        )

        raw_posterior_gap = int(item["raw_event_bps"]) - int(state.event_bps)
        divergence_veto = (
            base
            and state.directional_margin_bps > 0
            and state.evidence_count >= maturity_floor
            and state.event_bps <= max_posterior_event_bps
            and raw_posterior_gap >= min_raw_posterior_gap_bps
            and int(item["raw_event_delta1_bps"]) <= max_raw_event_delta1_bps
            and not slow_add
        )

        if divergence_veto:
            vetoed_trade_ids.add(trade_index)
            if trades[trade_index]["actual"] == "LOSS":
                vetoed_true_loss_ids.add(trade_index)
            else:
                vetoed_false_winner_ids.add(trade_index)
            continue

        if base or slow_add:
            if slow_add and not base:
                slow_additions += 1
            chosen[trade_index] = item

    return chosen, {
        "divergence_vetoes": len(vetoed_trade_ids),
        "divergence_true_loss_vetoes": len(vetoed_true_loss_ids),
        "divergence_false_winner_vetoes": len(vetoed_false_winner_ids),
        "slow_additions": slow_additions,
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
        divergence_vetoes=audit["divergence_vetoes"],
        divergence_true_loss_vetoes=audit["divergence_true_loss_vetoes"],
        divergence_false_winner_vetoes=audit["divergence_false_winner_vetoes"],
        slow_additions=audit["slow_additions"],
    )


def _baseline_metrics(
    *,
    trades: list[dict[str, Any]],
    surface: list[dict[str, Any]],
    threshold: Decimal,
) -> Metrics:
    chosen = _baseline_select(surface=surface, threshold=threshold)
    return _metrics(
        trades=trades,
        chosen=chosen,
        audit={
            "divergence_vetoes": 0,
            "divergence_true_loss_vetoes": 0,
            "divergence_false_winner_vetoes": 0,
            "slow_additions": 0,
        },
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
        "divergence_vetoes": metrics.divergence_vetoes,
        "divergence_true_loss_vetoes": metrics.divergence_true_loss_vetoes,
        "divergence_false_winner_vetoes": metrics.divergence_false_winner_vetoes,
        "slow_additions": metrics.slow_additions,
    }


def _choose_policy(
    *,
    trades: list[dict[str, Any]],
    surface: list[dict[str, Any]],
    threshold: Decimal,
) -> tuple[
    int | None,
    int | None,
    int | None,
    int | None,
    Metrics | None,
    list[dict[str, object]],
]:
    baseline = _baseline_metrics(
        trades=trades,
        surface=surface,
        threshold=threshold,
    )
    admitted: list[tuple[Metrics, int, int, int, int]] = []
    audit: list[dict[str, object]] = []

    for maturity in MATURITY_FLOORS:
        for gap in MIN_RAW_POSTERIOR_GAPS_BPS:
            for max_delta in MAX_RAW_EVENT_DELTA1_BPS:
                for max_event in MAX_POSTERIOR_EVENT_BPS:
                    chosen, selection_audit = _select(
                        trades=trades,
                        surface=surface,
                        threshold=threshold,
                        maturity_floor=maturity,
                        min_raw_posterior_gap_bps=gap,
                        max_raw_event_delta1_bps=max_delta,
                        max_posterior_event_bps=max_event,
                    )
                    metrics = _metrics(
                        trades=trades,
                        chosen=chosen,
                        audit=selection_audit,
                    )
                    changed = metrics.divergence_vetoes > 0
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
                            "maturity_floor": maturity,
                            "min_raw_posterior_gap_bps": gap,
                            "max_raw_event_delta1_bps": max_delta,
                            "max_posterior_event_bps": max_event,
                            **_payload(metrics),
                            "recall_delta_vs_v25r1": str(
                                metrics.loss_recall - baseline.loss_recall
                            ),
                            "precision_delta_vs_v25r1": str(
                                metrics.precision - baseline.precision
                            ),
                            "winner_mark_delta_vs_v25r1": str(
                                metrics.winner_mark_rate - baseline.winner_mark_rate
                            ),
                            "admitted": passed,
                        }
                    )
                    if passed:
                        admitted.append(
                            (metrics, maturity, gap, max_delta, max_event)
                        )

    if not admitted:
        return None, None, None, None, None, audit

    metrics, maturity, gap, max_delta, max_event = max(
        admitted,
        key=lambda item: (
            -item[0].false_winner,
            item[0].precision,
            item[0].loss_recall,
            -item[0].winner_mark_rate,
            item[0].median_lead_bars or Decimal("0"),
        ),
    )
    return maturity, gap, max_delta, max_event, metrics, audit


def _window(
    *,
    trades: list[dict[str, Any]],
    surface: list[dict[str, Any]],
    threshold: Decimal,
    maturity_floor: int,
    min_raw_posterior_gap_bps: int,
    max_raw_event_delta1_bps: int,
    max_posterior_event_bps: int,
) -> dict[str, object]:
    baseline = _baseline_metrics(
        trades=trades,
        surface=surface,
        threshold=threshold,
    )
    chosen, audit = _select(
        trades=trades,
        surface=surface,
        threshold=threshold,
        maturity_floor=maturity_floor,
        min_raw_posterior_gap_bps=min_raw_posterior_gap_bps,
        max_raw_event_delta1_bps=max_raw_event_delta1_bps,
        max_posterior_event_bps=max_posterior_event_bps,
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
        "v25r1": _payload(baseline),
        "v25r4": _payload(metrics),
        "recall_delta_vs_v25r1": str(
            metrics.loss_recall - baseline.loss_recall
        ),
        "precision_delta_vs_v25r1": str(
            metrics.precision - baseline.precision
        ),
        "winner_mark_delta_vs_v25r1": str(
            metrics.winner_mark_rate - baseline.winner_mark_rate
        ),
        "status": "ADMIT_FOR_ECONOMIC_SHADOW" if passed else "REJECT",
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
        maturity,
        gap,
        max_delta,
        max_event,
        train_metrics,
        policy_audit,
    ) = _choose_policy(
        trades=train_trades,
        surface=surfaces[TRAIN_WINDOW],
        threshold=threshold,
    )

    common = {
        "schema": SCHEMA,
        "identity": IDENTITY,
        "source_v6_run": SOURCE_V6_RUN,
        "source_v21_run": SOURCE_V21_RUN,
        "source_v24_run": SOURCE_V24_RUN,
        "source_v25_r1_run": SOURCE_V25_R1_RUN,
        "source_v25_r2_run": SOURCE_V25_R2_RUN,
        "source_v25_r3_run": SOURCE_V25_R3_RUN,
        "research_only": True,
        "shared_autonomous_model": True,
        "emission_posterior_divergence": True,
        "divergence_veto_is_temporary": True,
        "later_causal_reconfirmation_allowed": True,
        "v25r1_slow_adverse_route_frozen": True,
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
        "policy_audit": policy_audit,
    }

    if (
        maturity is None
        or gap is None
        or max_delta is None
        or max_event is None
        or train_metrics is None
    ):
        return {
            **common,
            "selected_policy": None,
            "windows": {},
            "validation_pass": False,
            "scientific_status": "REJECT",
            "rejection_reason": (
                "NO_FIVE_YEAR_DIVERGENCE_POLICY_PRESERVES_V25R1_RECALL_AND_SAFETY"
            ),
        }

    windows = {
        key: _window(
            trades=list(ledger[key]["rows"]),
            surface=surfaces[key],
            threshold=threshold,
            maturity_floor=maturity,
            min_raw_posterior_gap_bps=gap,
            max_raw_event_delta1_bps=max_delta,
            max_posterior_event_bps=max_event,
        )
        for key in WINDOWS
    }
    all_safe = all(
        windows[key]["status"] == "ADMIT_FOR_ECONOMIC_SHADOW"
        for key in WINDOWS
    )
    held_improvement = any(
        (
            Decimal(str(windows[key]["precision_delta_vs_v25r1"])) > 0
            or Decimal(str(windows[key]["winner_mark_delta_vs_v25r1"])) < 0
        )
        for key in VALIDATION_WINDOWS
    )
    validation_pass = all_safe and held_improvement

    return {
        **common,
        "policy_frozen_across_validation_windows": True,
        "selected_policy": {
            "maturity_floor": maturity,
            "min_raw_posterior_gap_bps": gap,
            "max_raw_event_delta1_bps": max_delta,
            "max_posterior_event_bps": max_event,
        },
        "train_selected_metrics": _payload(train_metrics),
        "pass_law": {
            "loss_recall": "V25R4 >= V25R1 in every consumed window",
            "training_precision_floor": str(TRAIN_PRECISION_FLOOR),
            "validation_precision_floor": str(VALIDATION_PRECISION_FLOOR),
            "winner_mark_ceiling": str(WINNER_MARK_CEILING),
            "minimum_selected_trades": MIN_SELECTED_TRADES,
            "minimum_median_lead_bars": str(MIN_MEDIAN_LEAD_BARS),
            "held_window_precision_or_winner_mark_improvement_required": True,
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

"""V25-R3 hypothesis-ageing arbitration for Shared Core.

V25-R2 found a repeated causal pattern at the exact frozen V21 decision point:

- true losses usually arrive with little accumulated belief history and a
  comparatively higher event-readiness posterior;
- false winner marks, especially in R66 consumed evidence, often persist for
  many observations while event readiness remains low or decays;
- adverse direction alone is therefore not enough. An adverse hypothesis that
  does not progress toward an event should age and lose authority.

R3 tests this *hypothesis ageing* mechanism without changing the frozen V21
survival threshold or the V25-R1 slow adverse route.

A V21 mark may be vetoed only when all of these are true:
- adverse conditional direction is still present;
- the belief has matured for multiple observations;
- event readiness is low;
- event readiness is not increasing.

The veto is temporary. If a later observation strengthens event readiness, the
same trade may become actionable again. This is a causal delay/protection
mechanism, not a winner declaration.

Thresholds are selected only on five-year consumed evidence, then frozen
unchanged for recent-two-year and R66 consumed windows. Fresh holdout stays
closed. No runtime PnL, future market, trader/market/methodology/fold identity,
sizing, risk weighting, stop, target, order or execution authority is used.
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

IDENTITY = "QORE_SHARED_V25_R3_HYPOTHESIS_AGEING_ARBITRATION"
SCHEMA = "qore.shared.v25_r3_hypothesis_ageing_arbitration"

SOURCE_V6_RUN = 36131607443
SOURCE_V21_RUN = 36156421332
SOURCE_V24_RUN = 36185092496
SOURCE_V25_R1_RUN = 36187557918
SOURCE_V25_R2_RUN = 36194504049

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

MATURITY_FLOORS = (2, 3, 4, 5, 6, 8)
MAX_EVENT_READINESS_BPS = (1_500, 2_000, 2_500, 3_000)
MAX_EVENT_DELTA1_BPS = (-500, -250, 0)
REQUIRE_ADVERSE_DIRECTION = True


@dataclass(frozen=True, slots=True)
class Metrics:
    selected: int
    true_loss: int
    false_winner: int
    precision: Decimal
    loss_recall: Decimal
    winner_mark_rate: Decimal
    median_lead_bars: Decimal | None
    aged_vetoes: int
    aged_true_loss_vetoes: int
    aged_false_winner_vetoes: int
    slow_additions: int


def _ratio(n: int, d: int) -> Decimal:
    return Decimal("0") if d <= 0 else Decimal(n) / Decimal(d)


def _event_delta1_map(
    *,
    event_model: Any,
    trades: list[dict[str, Any]],
    categories: dict[str, tuple[str, ...]],
    transition_bps: dict[str, dict[str, int]],
) -> dict[tuple[int, str], int]:
    states = v25r1._factorized_map(
        event_model=event_model,
        trades=trades,
        categories=categories,
        transition_bps=transition_bps,
    )
    grouped: dict[int, list[tuple[str, Any]]] = {}
    for (trade_index, as_of), state in states.items():
        grouped.setdefault(trade_index, []).append((as_of, state))

    result: dict[tuple[int, str], int] = {}
    for trade_index, items in grouped.items():
        items.sort(key=lambda pair: pair[0])
        prior_event: int | None = None
        for as_of, item in items:
            current = int(item.state.event_bps)
            result[(trade_index, as_of)] = (
                0 if prior_event is None else current - prior_event
            )
            prior_event = current
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
    delta1 = _event_delta1_map(
        event_model=event_model,
        trades=trades,
        categories=categories,
        transition_bps=transition_bps,
    )
    return [
        {
            **item,
            "event_delta1_bps": delta1[
                (int(item["trade_index"]), str(item["row"]["as_of"]))
            ],
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
    max_event_readiness_bps: int,
    max_event_delta1_bps: int,
) -> tuple[dict[int, dict[str, Any]], dict[str, int]]:
    chosen: dict[int, dict[str, Any]] = {}
    aged_vetoed_trade_ids: set[int] = set()
    aged_true_loss_vetoes = 0
    aged_false_winner_vetoes = 0
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

        aged = (
            base
            and state.evidence_count >= maturity_floor
            and state.event_bps <= max_event_readiness_bps
            and int(item["event_delta1_bps"]) <= max_event_delta1_bps
            and (
                not REQUIRE_ADVERSE_DIRECTION
                or state.directional_margin_bps > 0
            )
            and not slow_add
        )

        if aged:
            if trade_index not in aged_vetoed_trade_ids:
                aged_vetoed_trade_ids.add(trade_index)
                if trades[trade_index]["actual"] == "LOSS":
                    aged_true_loss_vetoes += 1
                else:
                    aged_false_winner_vetoes += 1
            continue

        if base or slow_add:
            if slow_add and not base:
                slow_additions += 1
            chosen[trade_index] = item

    return chosen, {
        "aged_vetoes": len(aged_vetoed_trade_ids),
        "aged_true_loss_vetoes": aged_true_loss_vetoes,
        "aged_false_winner_vetoes": aged_false_winner_vetoes,
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
        aged_vetoes=audit["aged_vetoes"],
        aged_true_loss_vetoes=audit["aged_true_loss_vetoes"],
        aged_false_winner_vetoes=audit["aged_false_winner_vetoes"],
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
            "aged_vetoes": 0,
            "aged_true_loss_vetoes": 0,
            "aged_false_winner_vetoes": 0,
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
        "aged_vetoes": metrics.aged_vetoes,
        "aged_true_loss_vetoes": metrics.aged_true_loss_vetoes,
        "aged_false_winner_vetoes": metrics.aged_false_winner_vetoes,
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
    Metrics | None,
    list[dict[str, object]],
]:
    baseline = _baseline_metrics(
        trades=trades,
        surface=surface,
        threshold=threshold,
    )
    admitted: list[tuple[Metrics, int, int, int]] = []
    audit: list[dict[str, object]] = []

    for maturity in MATURITY_FLOORS:
        for max_event in MAX_EVENT_READINESS_BPS:
            for max_delta in MAX_EVENT_DELTA1_BPS:
                chosen, selection_audit = _select(
                    trades=trades,
                    surface=surface,
                    threshold=threshold,
                    maturity_floor=maturity,
                    max_event_readiness_bps=max_event,
                    max_event_delta1_bps=max_delta,
                )
                metrics = _metrics(
                    trades=trades,
                    chosen=chosen,
                    audit=selection_audit,
                )
                changed = metrics.aged_vetoes > 0
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
                        "max_event_readiness_bps": max_event,
                        "max_event_delta1_bps": max_delta,
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
                    admitted.append((metrics, maturity, max_event, max_delta))

    if not admitted:
        return None, None, None, None, audit

    metrics, maturity, max_event, max_delta = max(
        admitted,
        key=lambda item: (
            -item[0].false_winner,
            item[0].precision,
            item[0].loss_recall,
            -item[0].winner_mark_rate,
            item[0].median_lead_bars or Decimal("0"),
        ),
    )
    return maturity, max_event, max_delta, metrics, audit


def _window(
    *,
    trades: list[dict[str, Any]],
    surface: list[dict[str, Any]],
    threshold: Decimal,
    maturity_floor: int,
    max_event_readiness_bps: int,
    max_event_delta1_bps: int,
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
        max_event_readiness_bps=max_event_readiness_bps,
        max_event_delta1_bps=max_event_delta1_bps,
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
        "v25r3": _payload(metrics),
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

    maturity, max_event, max_delta, train_metrics, policy_audit = _choose_policy(
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
        "research_only": True,
        "shared_autonomous_model": True,
        "hypothesis_ageing": True,
        "aged_adverse_hypothesis_veto_is_temporary": True,
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
        or max_event is None
        or max_delta is None
        or train_metrics is None
    ):
        return {
            **common,
            "selected_policy": None,
            "windows": {},
            "validation_pass": False,
            "scientific_status": "REJECT",
            "rejection_reason": (
                "NO_FIVE_YEAR_HYPOTHESIS_AGEING_POLICY_PRESERVES_V25R1_RECALL_AND_SAFETY"
            ),
        }

    windows = {
        key: _window(
            trades=list(ledger[key]["rows"]),
            surface=surfaces[key],
            threshold=threshold,
            maturity_floor=maturity,
            max_event_readiness_bps=max_event,
            max_event_delta1_bps=max_delta,
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
            "max_event_readiness_bps": max_event,
            "max_event_delta1_bps": max_delta,
            "require_adverse_direction": REQUIRE_ADVERSE_DIRECTION,
        },
        "train_selected_metrics": _payload(train_metrics),
        "pass_law": {
            "loss_recall": "V25R3 >= V25R1 in every consumed window",
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

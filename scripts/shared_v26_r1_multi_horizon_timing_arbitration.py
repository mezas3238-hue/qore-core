"""V26-R1 multi-horizon timing arbitration for Shared Core.

R0B established exact selection parity with frozen V21 and showed that
multi-horizon incidence contains timing information that V21 does not use.

R1 tests a causal timing arbiter around frozen V21:
- a survival-vetoed candidate may be added when adverse incidence is both
  near-term and directionally dominant;
- a V21-selected candidate may be deferred when adverse incidence is mostly
  back-loaded and near-term directional separation is weak;
- deferred candidates remain eligible for later causal reconfirmation.

All timing thresholds are selected on five-year consumed evidence only, then
frozen unchanged on recent-two-year and R66 consumed windows. The V21 survival
threshold and independent relational veto are unchanged. Fresh holdout remains
closed.

Runtime inference consumes only point-in-time and prior market evidence plus
frozen multi-horizon models. No current PnL, future market, symbol/market/
trader/methodology/fold identity, sizing, risk weighting, order or execution
authority is used.
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

import shared_relational_adversity_challenge_survival_v21 as v21
import shared_v26_r0b_selection_corrected_incidence_forensics as v26r0b

IDENTITY = "QORE_SHARED_V26_R1_MULTI_HORIZON_TIMING_ARBITRATION"
SCHEMA = "qore.shared.v26_r1_multi_horizon_timing_arbitration"

SOURCE_V6_RUN = 36131607443
SOURCE_V21_RUN = 36156421332
SOURCE_V26_R0_RUN = 36203614522
SOURCE_V26_R0B_RUN = 36210276127

TRAIN_WINDOW = v21.TRAIN_WINDOW
VALIDATION_WINDOWS = v21.VALIDATION_WINDOWS
WINDOWS = (TRAIN_WINDOW, *VALIDATION_WINDOWS)

TRAIN_PRECISION_FLOOR = Decimal("0.95")
VALIDATION_PRECISION_FLOOR = Decimal("0.90")
WINNER_MARK_CEILING = Decimal("0.01")
MIN_SELECTED_TRADES = 20
MIN_MEDIAN_LEAD_BARS = Decimal("1")

ADD_H1_FLOORS = (2_000, 2_500, 3_000)
ADD_IMMINENCE_RATIO_FLOORS = (5_500, 6_500, 7_500)
ADD_NEAR_MARGIN_FLOORS = (1_500, 2_000, 2_500)

DEFER_H1_CEILINGS = (1_000, 1_250, 1_500)
DEFER_IMMINENCE_RATIO_CEILINGS = (4_000, 5_000, 6_000)
DEFER_NEAR_MARGIN_CEILINGS = (1_000, 1_500, 2_000)


@dataclass(frozen=True, slots=True)
class Metrics:
    selected: int
    true_loss: int
    false_winner: int
    precision: Decimal
    loss_recall: Decimal
    winner_mark_rate: Decimal
    median_lead_bars: Decimal | None
    timing_additions: int
    timing_added_true_loss: int
    timing_added_false_winner: int
    timing_deferrals: int
    timing_deferred_true_loss: int
    timing_deferred_false_winner: int


def _ratio(numerator: int, denominator: int) -> Decimal:
    return Decimal("0") if denominator <= 0 else Decimal(numerator) / Decimal(denominator)


def _imminence_ratio_bps(h1: int, h3: int) -> int:
    if h3 <= 0:
        return 0
    return max(0, min(10_000, h1 * 10_000 // h3))


def _surface(
    *,
    ledger: dict[str, Any],
    key: str,
    hazard_model: Any,
    survival_model: Any,
    categories: dict[str, tuple[str, ...]],
    adverse_models: dict[int, Any],
    favorable_models: dict[int, Any],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    trades = list(ledger[key]["rows"])
    profile_map, _ = v26r0b._profile_map(
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

    surface: list[dict[str, Any]] = []
    for probability, item in zip(survival_probabilities, meta, strict=True):
        trade_index = int(item["trade_index"])
        as_of = str(item["row"]["as_of"])
        profile = profile_map[(trade_index, as_of)]["profile"]
        h1 = int(profile.adverse_curve_bps[0])
        h3 = int(profile.adverse_curve_bps[1])
        surface.append(
            {
                **item,
                "survival_probability": float(probability),
                "adverse_h1_bps": h1,
                "adverse_h3_bps": h3,
                "imminence_ratio_bps": _imminence_ratio_bps(h1, h3),
                "near_directional_margin_bps": int(
                    profile.near_directional_margin_bps
                ),
                "frontload_margin_bps": int(profile.frontload_margin_bps),
            }
        )
    return trades, surface


def _frozen_v21_select(
    *,
    surface: list[dict[str, Any]],
    threshold: Decimal,
) -> dict[int, dict[str, Any]]:
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
    return chosen


def _select(
    *,
    trades: list[dict[str, Any]],
    surface: list[dict[str, Any]],
    threshold: Decimal,
    add_h1_floor: int,
    add_imminence_ratio_floor: int,
    add_near_margin_floor: int,
    defer_h1_ceiling: int,
    defer_imminence_ratio_ceiling: int,
    defer_near_margin_ceiling: int,
) -> tuple[dict[int, dict[str, Any]], dict[str, int]]:
    chosen: dict[int, dict[str, Any]] = {}
    deferred_ids: set[int] = set()
    deferred_true_loss_ids: set[int] = set()
    deferred_false_winner_ids: set[int] = set()
    added_ids: set[int] = set()
    added_true_loss_ids: set[int] = set()
    added_false_winner_ids: set[int] = set()
    limit = float(threshold)

    for item in surface:
        trade_index = int(item["trade_index"])
        if trade_index in chosen:
            continue
        if v21._relational_veto(item["challenge"]):
            continue

        base = float(item["survival_probability"]) <= limit
        add = (
            not base
            and int(item["adverse_h1_bps"]) >= add_h1_floor
            and int(item["imminence_ratio_bps"]) >= add_imminence_ratio_floor
            and int(item["near_directional_margin_bps"]) >= add_near_margin_floor
            and int(item["frontload_margin_bps"]) > 0
        )
        defer = (
            base
            and int(item["adverse_h1_bps"]) <= defer_h1_ceiling
            and int(item["imminence_ratio_bps"]) <= defer_imminence_ratio_ceiling
            and int(item["near_directional_margin_bps"]) <= defer_near_margin_ceiling
        )

        if defer:
            deferred_ids.add(trade_index)
            if trades[trade_index]["actual"] == "LOSS":
                deferred_true_loss_ids.add(trade_index)
            else:
                deferred_false_winner_ids.add(trade_index)
            continue

        if base or add:
            if add:
                added_ids.add(trade_index)
                if trades[trade_index]["actual"] == "LOSS":
                    added_true_loss_ids.add(trade_index)
                else:
                    added_false_winner_ids.add(trade_index)
            chosen[trade_index] = item

    return chosen, {
        "timing_additions": len(added_ids),
        "timing_added_true_loss": len(added_true_loss_ids),
        "timing_added_false_winner": len(added_false_winner_ids),
        "timing_deferrals": len(deferred_ids),
        "timing_deferred_true_loss": len(deferred_true_loss_ids),
        "timing_deferred_false_winner": len(deferred_false_winner_ids),
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
        timing_additions=audit["timing_additions"],
        timing_added_true_loss=audit["timing_added_true_loss"],
        timing_added_false_winner=audit["timing_added_false_winner"],
        timing_deferrals=audit["timing_deferrals"],
        timing_deferred_true_loss=audit["timing_deferred_true_loss"],
        timing_deferred_false_winner=audit["timing_deferred_false_winner"],
    )


def _baseline_metrics(
    *,
    trades: list[dict[str, Any]],
    surface: list[dict[str, Any]],
    threshold: Decimal,
) -> Metrics:
    chosen = _frozen_v21_select(surface=surface, threshold=threshold)
    return _metrics(
        trades=trades,
        chosen=chosen,
        audit={
            "timing_additions": 0,
            "timing_added_true_loss": 0,
            "timing_added_false_winner": 0,
            "timing_deferrals": 0,
            "timing_deferred_true_loss": 0,
            "timing_deferred_false_winner": 0,
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
        "timing_additions": metrics.timing_additions,
        "timing_added_true_loss": metrics.timing_added_true_loss,
        "timing_added_false_winner": metrics.timing_added_false_winner,
        "timing_deferrals": metrics.timing_deferrals,
        "timing_deferred_true_loss": metrics.timing_deferred_true_loss,
        "timing_deferred_false_winner": metrics.timing_deferred_false_winner,
    }


def _choose_policy(
    *,
    trades: list[dict[str, Any]],
    surface: list[dict[str, Any]],
    threshold: Decimal,
) -> tuple[dict[str, int] | None, Metrics | None, list[dict[str, object]]]:
    baseline = _baseline_metrics(
        trades=trades,
        surface=surface,
        threshold=threshold,
    )
    admitted: list[tuple[Metrics, dict[str, int]]] = []
    audit: list[dict[str, object]] = []

    for add_h1 in ADD_H1_FLOORS:
        for add_ratio in ADD_IMMINENCE_RATIO_FLOORS:
            for add_margin in ADD_NEAR_MARGIN_FLOORS:
                for defer_h1 in DEFER_H1_CEILINGS:
                    for defer_ratio in DEFER_IMMINENCE_RATIO_CEILINGS:
                        for defer_margin in DEFER_NEAR_MARGIN_CEILINGS:
                            chosen, selection_audit = _select(
                                trades=trades,
                                surface=surface,
                                threshold=threshold,
                                add_h1_floor=add_h1,
                                add_imminence_ratio_floor=add_ratio,
                                add_near_margin_floor=add_margin,
                                defer_h1_ceiling=defer_h1,
                                defer_imminence_ratio_ceiling=defer_ratio,
                                defer_near_margin_ceiling=defer_margin,
                            )
                            metrics = _metrics(
                                trades=trades,
                                chosen=chosen,
                                audit=selection_audit,
                            )
                            changed = (
                                metrics.timing_additions + metrics.timing_deferrals
                            ) > 0
                            passed = (
                                changed
                                and metrics.selected >= MIN_SELECTED_TRADES
                                and metrics.precision >= TRAIN_PRECISION_FLOOR
                                and metrics.winner_mark_rate <= WINNER_MARK_CEILING
                                and metrics.loss_recall >= baseline.loss_recall
                                and metrics.median_lead_bars is not None
                                and metrics.median_lead_bars >= MIN_MEDIAN_LEAD_BARS
                            )
                            policy = {
                                "add_h1_floor": add_h1,
                                "add_imminence_ratio_floor": add_ratio,
                                "add_near_margin_floor": add_margin,
                                "defer_h1_ceiling": defer_h1,
                                "defer_imminence_ratio_ceiling": defer_ratio,
                                "defer_near_margin_ceiling": defer_margin,
                            }
                            audit.append(
                                {
                                    **policy,
                                    **_payload(metrics),
                                    "recall_delta_vs_v21": str(
                                        metrics.loss_recall - baseline.loss_recall
                                    ),
                                    "precision_delta_vs_v21": str(
                                        metrics.precision - baseline.precision
                                    ),
                                    "winner_mark_delta_vs_v21": str(
                                        metrics.winner_mark_rate
                                        - baseline.winner_mark_rate
                                    ),
                                    "admitted": passed,
                                }
                            )
                            if passed:
                                admitted.append((metrics, policy))

    if not admitted:
        return None, None, audit

    metrics, policy = max(
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
    return policy, metrics, audit


def _window(
    *,
    trades: list[dict[str, Any]],
    surface: list[dict[str, Any]],
    threshold: Decimal,
    policy: dict[str, int],
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
        add_h1_floor=policy["add_h1_floor"],
        add_imminence_ratio_floor=policy["add_imminence_ratio_floor"],
        add_near_margin_floor=policy["add_near_margin_floor"],
        defer_h1_ceiling=policy["defer_h1_ceiling"],
        defer_imminence_ratio_ceiling=policy["defer_imminence_ratio_ceiling"],
        defer_near_margin_ceiling=policy["defer_near_margin_ceiling"],
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
        "v26r1": _payload(metrics),
        "recall_delta_vs_v21": str(metrics.loss_recall - baseline.loss_recall),
        "precision_delta_vs_v21": str(metrics.precision - baseline.precision),
        "winner_mark_delta_vs_v21": str(
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

    adverse_models, favorable_models = v26r0b._fit_models(
        trades=train_trades,
        categories=categories,
    )
    surfaces: dict[str, tuple[list[dict[str, Any]], list[dict[str, Any]]]] = {
        key: _surface(
            ledger=ledger,
            key=key,
            hazard_model=hazard_model,
            survival_model=survival_model,
            categories=categories,
            adverse_models=adverse_models,
            favorable_models=favorable_models,
        )
        for key in WINDOWS
    }

    policy, train_metrics, policy_audit = _choose_policy(
        trades=surfaces[TRAIN_WINDOW][0],
        surface=surfaces[TRAIN_WINDOW][1],
        threshold=threshold,
    )

    common = {
        "schema": SCHEMA,
        "identity": IDENTITY,
        "source_v6_run": SOURCE_V6_RUN,
        "source_v21_run": SOURCE_V21_RUN,
        "source_v26_r0_run": SOURCE_V26_R0_RUN,
        "source_v26_r0b_run": SOURCE_V26_R0B_RUN,
        "research_only": True,
        "shared_autonomous_model": True,
        "multi_horizon_timing_arbiter": True,
        "bidirectional_add_and_defer": True,
        "defer_is_temporary_and_later_reconfirmation_allowed": True,
        "v21_survival_threshold_frozen": str(threshold),
        "v21_relational_veto_frozen": True,
        "models_fit_on_five_year_only": True,
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
        "closed_outcome_and_exit_distance_used_offline_for_training_and_scoring_only": True,
        "policy_audit": policy_audit,
    }

    if policy is None or train_metrics is None:
        return {
            **common,
            "selected_policy": None,
            "windows": {},
            "validation_pass": False,
            "scientific_status": "REJECT",
            "rejection_reason": (
                "NO_FIVE_YEAR_MULTI_HORIZON_POLICY_PRESERVES_V21_RECALL_AND_SAFETY"
            ),
        }

    windows = {
        key: _window(
            trades=surfaces[key][0],
            surface=surfaces[key][1],
            threshold=threshold,
            policy=policy,
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
            or Decimal(str(windows[key]["precision_delta_vs_v21"])) > 0
            or Decimal(str(windows[key]["winner_mark_delta_vs_v21"])) < 0
        )
        for key in VALIDATION_WINDOWS
    )
    validation_pass = all_safe and held_improvement

    return {
        **common,
        "policy_frozen_across_validation_windows": True,
        "selected_policy": policy,
        "train_selected_metrics": _payload(train_metrics),
        "pass_law": {
            "loss_recall": "V26R1 >= V21 in every consumed window",
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

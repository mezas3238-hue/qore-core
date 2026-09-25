"""V22-C deferred-confirmation arbitration for Shared.

V22-B falsified a learned split-expert solution for evidence maturity.  V22-C
tests a simpler causal rule: INSUFFICIENT is not actionable by itself.  A V21
adverse candidate in that state is deferred until either:

1) an independent frozen V20 competing-hazard gate reaches STOP_LIKELY, or
2) later bounded point-in-time evidence matures and V21 still selects it.

This preserves a fast-failure route without turning broad support, recovery,
or uncertainty into hand-tuned veto scores.  V21's frozen survival threshold is
unchanged and no new threshold is fitted.

Research-only.  No trader, methodology, symbol, market, calendar, fold,
current PnL, sizing, capital, risk, order or broker identity is an inference
feature.  CLOSED outcome is used only for offline scoring after decisions.
"""

# ruff: noqa: E501,I001

from __future__ import annotations

import argparse
import json
from decimal import Decimal
from pathlib import Path
from statistics import median
from typing import Any

import numpy as np
import shared_relational_adversity_challenge_survival_v21 as v21

from qore.infrastructure.core_stack_v2.adversity_challenge_intelligence import (
    AdversityChallengeState,
)
from qore.infrastructure.core_stack_v2.multi_state_competing_hazard import (
    CompetingHazardDecision,
)

IDENTITY = "QORE_SHARED_DEFERRED_CONFIRMATION_ARBITRATION_V22C"
SCHEMA = "qore.shared.deferred_confirmation_arbitration.v22c"

SOURCE_V6_RUN = 36131607443
SOURCE_V21_RUN = 36156421332
SOURCE_V22_R0_RUN = 36160445959
SOURCE_V22A_RUN = 36165036594
SOURCE_V22B_RUN = 36165666010

WINDOWS = (v21.TRAIN_WINDOW, *v21.VALIDATION_WINDOWS)

PRECISION_FLOOR = Decimal("0.90")
WINNER_MARK_CEILING = Decimal("0.01")
MIN_SELECTED_TRADES = 20
MIN_MEDIAN_LEAD_BARS = Decimal("1")


def _ratio(n: int, d: int) -> Decimal:
    return Decimal("0") if d <= 0 else Decimal(n) / Decimal(d)


def _v20_decision_map(
    *,
    hazard_model: Any,
    categories: dict[str, tuple[str, ...]],
    trades: list[dict[str, Any]],
) -> dict[tuple[int, str], str]:
    x_rows, _, _, meta = v21.v20._dataset(trades, categories)
    probabilities = hazard_model.predict_proba(x_rows)
    classes = tuple(str(value) for value in hazard_model.classes_)
    decisions = v21.v20._decision_rows(
        probability_rows=probabilities,
        classes=classes,
        meta=meta,
    )
    result: dict[tuple[int, str], str] = {}
    for trade_index, rows in decisions.items():
        for item in rows:
            result[(trade_index, str(item["row"]["as_of"]))] = str(item["decision"])
    return result


def _metrics(
    *,
    trades: list[dict[str, Any]],
    probabilities: np.ndarray,
    meta: list[dict[str, Any]],
    threshold: Decimal,
    v20_decisions: dict[tuple[int, str], str],
) -> tuple[v21.Metrics, dict[str, int]]:
    chosen: dict[int, dict[str, Any]] = {}
    relational_veto_count = 0
    survival_veto_count = 0
    insufficient_deferred = 0
    insufficient_fast_failure = 0
    matured_after_defer = 0
    deferred_trades: set[int] = set()
    limit = float(threshold)

    for probability, item in zip(probabilities, meta, strict=True):
        trade_index = int(item["trade_index"])
        if trade_index in chosen:
            continue
        challenge = item["challenge"]

        if v21._relational_veto(challenge):
            relational_veto_count += 1
            continue
        if float(probability) > limit:
            survival_veto_count += 1
            continue

        if challenge.state == AdversityChallengeState.INSUFFICIENT:
            decision = v20_decisions.get(
                (trade_index, str(item["row"]["as_of"])),
                CompetingHazardDecision.CONTESTED.value,
            )
            if decision != CompetingHazardDecision.STOP_LIKELY.value:
                insufficient_deferred += 1
                deferred_trades.add(trade_index)
                continue
            insufficient_fast_failure += 1
        elif trade_index in deferred_trades:
            matured_after_defer += 1

        chosen[trade_index] = item

    losses = sum(trade["actual"] == "LOSS" for trade in trades)
    winners = sum(trade["actual"] == "WIN" for trade in trades)
    true_loss = [i for i in chosen if trades[i]["actual"] == "LOSS"]
    false_winner = [i for i in chosen if trades[i]["actual"] == "WIN"]
    leads = [
        int(chosen[i]["row"]["bars_before_canonical_exit"])
        for i in true_loss
    ]
    metrics = v21.Metrics(
        selected=len(chosen),
        true_loss=len(true_loss),
        false_winner=len(false_winner),
        precision=_ratio(len(true_loss), len(chosen)),
        loss_recall=_ratio(len(true_loss), losses),
        winner_mark_rate=_ratio(len(false_winner), winners),
        median_lead_bars=None if not leads else Decimal(str(median(leads))),
        relational_veto_count=relational_veto_count,
        survival_veto_count=survival_veto_count,
    )
    audit = {
        "insufficient_deferred_observations": insufficient_deferred,
        "insufficient_fast_failure_confirmations": insufficient_fast_failure,
        "matured_selections_after_defer": matured_after_defer,
        "trades_ever_deferred": len(deferred_trades),
    }
    return metrics, audit


def _window(
    *,
    hazard_model: Any,
    survival_model: Any,
    categories: dict[str, tuple[str, ...]],
    trades: list[dict[str, Any]],
    threshold: Decimal,
) -> dict[str, object]:
    x_rows, _, _, meta = v21._candidate_dataset(
        hazard_model=hazard_model,
        categories=categories,
        trades=trades,
    )
    probabilities = survival_model.predict_proba(x_rows)[:, 1]
    v21_metrics = v21._metrics(
        trades=trades,
        survival_probabilities=probabilities,
        meta=meta,
        threshold=threshold,
    )
    v20_decisions = _v20_decision_map(
        hazard_model=hazard_model,
        categories=categories,
        trades=trades,
    )
    metrics, audit = _metrics(
        trades=trades,
        probabilities=probabilities,
        meta=meta,
        threshold=threshold,
        v20_decisions=v20_decisions,
    )
    passed = (
        metrics.selected >= MIN_SELECTED_TRADES
        and metrics.precision >= PRECISION_FLOOR
        and metrics.winner_mark_rate <= WINNER_MARK_CEILING
        and metrics.loss_recall >= v21_metrics.loss_recall
        and metrics.median_lead_bars is not None
        and metrics.median_lead_bars >= MIN_MEDIAN_LEAD_BARS
    )
    return {
        "sample": len(trades),
        "v21": v21._payload(v21_metrics),
        "v22c": v21._payload(metrics),
        "recall_delta_vs_v21": str(metrics.loss_recall - v21_metrics.loss_recall),
        "precision_delta_vs_v21": str(metrics.precision - v21_metrics.precision),
        "winner_mark_delta_vs_v21": str(
            metrics.winner_mark_rate - v21_metrics.winner_mark_rate
        ),
        "deferred_confirmation_audit": audit,
        "status": "ADMIT_FOR_ECONOMIC_SHADOW" if passed else "REJECT",
    }


def run(v6_json: Path) -> dict[str, object]:
    ledger = json.loads(v6_json.read_text())
    if ledger["identity"] != "QORE_SHARED_VT08_INDEX_STOP_TARGET_DISCRIMINATION_V6":
        raise ValueError("unexpected frozen external falsification ledger identity")

    hazard_model, categories = v21._fit_hazard(ledger)
    train_trades = list(ledger[v21.TRAIN_WINDOW]["rows"])
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

    windows = {
        key: _window(
            hazard_model=hazard_model,
            survival_model=survival_model,
            categories=categories,
            trades=list(ledger[key]["rows"]),
            threshold=threshold,
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
        "source_v22b_run": SOURCE_V22B_RUN,
        "research_only": True,
        "shared_autonomous_model": True,
        "v21_survival_threshold_frozen": str(threshold),
        "new_threshold_fitted": False,
        "insufficient_is_non_actionable_without_independent_confirmation": True,
        "fast_failure_route_uses_frozen_v20_stop_likely": True,
        "mature_evidence_reenters_frozen_v21_gate": True,
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
        "closed_outcome_used_for_scoring_only": True,
        "pass_law": {
            "loss_recall": "V22C >= V21 in every consumed window",
            "precision_floor": str(PRECISION_FLOOR),
            "winner_mark_ceiling": str(WINNER_MARK_CEILING),
            "minimum_selected_trades": MIN_SELECTED_TRADES,
            "minimum_median_lead_bars": str(MIN_MEDIAN_LEAD_BARS),
        },
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
    print(json.dumps({
        "identity": payload["identity"],
        "validation_pass": payload["validation_pass"],
        "scientific_status": payload["scientific_status"],
        "v21_survival_threshold_frozen": payload["v21_survival_threshold_frozen"],
        "windows": payload["windows"],
    }, sort_keys=True))


if __name__ == "__main__":
    main()

"""V10 temporal persistence gate over frozen V9 competing-risk probabilities.

V9 demonstrated useful STOP-before-TARGET discrimination but no single
observation threshold satisfied precision, winner protection, and useful lead.
V10 keeps the V9 coefficients frozen and searches only the 5Y consumed training
window for a temporal persistence policy:

    posterior >= threshold for K consecutive causal observations
    AND no active/restored recovery veto

The selected threshold/K pair is then frozen and evaluated unchanged on recent
2Y and R66 consumed evidence. No runtime authority is granted here.
"""
from __future__ import annotations

import argparse
import json
import math
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from statistics import median
from typing import Any

IDENTITY = "QORE_SHARED_VT08_COMPETING_RISK_PERSISTENCE_V10"
SCHEMA = "qore.shared.vt08_competing_risk_persistence.v10"

TRAIN_WINDOW = "five_year"
VALIDATION_WINDOWS = ("recent_two_year", "r66_consumed_failed_holdout")

TRAIN_PRECISION_FLOOR = Decimal("0.95")
VALIDATION_PRECISION_FLOOR = Decimal("0.95")
WINNER_MARK_CEILING = Decimal("0.005")
MIN_MEDIAN_LEAD_BARS = Decimal("1")
MIN_SELECTED_TRADES = 10

THRESHOLDS = tuple(
    Decimal(value) / Decimal("1000")
    for value in range(750, 951, 5)
)
PERSISTENCE_LENGTHS = (2, 3, 4, 5)

PATH_STATES = (
    "CONTESTED",
    "ADVERSE_DOMINANCE",
    "FAILURE_RISK",
    "RECOVERING",
    "HEALTHY_PULLBACK",
    "FAVORABLE_EXPANSION",
)
RECOVERY_STATES = (
    "RECOVERY_FAILED",
    "RECOVERY_PENDING",
    "RECOVERY_ACTIVE",
    "RECOVERY_RESTORED",
    "NOT_TESTED",
)


@dataclass(frozen=True, slots=True)
class DecisionMetrics:
    selected: int
    true_loss: int
    false_winner: int
    precision: Decimal
    loss_recall: Decimal
    winner_mark_rate: Decimal
    median_lead_bars: Decimal | None


def _d(value: object) -> Decimal:
    return Decimal(str(value))


def _ratio(n: int, d: int) -> Decimal:
    if d <= 0:
        return Decimal("0")
    return Decimal(n) / Decimal(d)


def _clip(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def _features(row: dict[str, Any]) -> list[float]:
    values = [
        int(row["stop_formation_bps"]) / 10_000.0,
        int(row["stop_hazard_proxy_bps"]) / 10_000.0,
        int(row["target_hazard_proxy_bps"]) / 10_000.0,
        int(row["recovery_strength_bps"]) / 10_000.0,
        int(row["uncertainty_bps"]) / 10_000.0,
        int(row["path_support_bps"]) / 10_000.0,
        int(row["path_adverse_dominance_bps"]) / 10_000.0,
        int(row["path_adverse_persistence_bps"]) / 10_000.0,
        int(row["path_recovery_persistence_bps"]) / 10_000.0,
        int(row["path_winner_protection_bps"]) / 10_000.0,
        int(row["path_terminal_failure_risk_bps"]) / 10_000.0,
        _clip(float(_d(row["current_position_r"])) / 2.0, -1.0, 1.0),
        min(int(row["bar_index"]), 100) / 100.0,
    ]
    path_state = str(row["path_state"])
    recovery_state = str(row["recovery_challenge_state"])
    values.extend(1.0 if path_state == state else 0.0 for state in PATH_STATES)
    values.extend(
        1.0 if recovery_state == state else 0.0
        for state in RECOVERY_STATES
    )
    return values


def _probability(
    row: dict[str, Any],
    *,
    intercept: float,
    coefficients: list[float],
) -> float:
    features = _features(row)
    if len(features) != len(coefficients):
        raise ValueError("V9 coefficient/feature length mismatch")
    z = intercept + sum(
        coefficient * feature
        for coefficient, feature in zip(coefficients, features, strict=True)
    )
    if z >= 0:
        exp_neg = math.exp(-z)
        return 1.0 / (1.0 + exp_neg)
    exp_pos = math.exp(z)
    return exp_pos / (1.0 + exp_pos)


def _eligible(row: dict[str, Any]) -> bool:
    return (
        row["stage"] == "PATH"
        and row["path_state"] != "INSUFFICIENT"
    )


def _recovery_veto(row: dict[str, Any]) -> bool:
    return row["recovery_challenge_state"] in {
        "RECOVERY_ACTIVE",
        "RECOVERY_RESTORED",
    }


def _first_persistent_crossing(
    trade: dict[str, Any],
    *,
    threshold: Decimal,
    persistence: int,
    intercept: float,
    coefficients: list[float],
) -> dict[str, Any] | None:
    run = 0
    threshold_float = float(threshold)
    for row in trade["observations"]:
        if not _eligible(row):
            run = 0
            continue
        probability = _probability(
            row,
            intercept=intercept,
            coefficients=coefficients,
        )
        if probability >= threshold_float and not _recovery_veto(row):
            run += 1
            if run >= persistence:
                return {
                    **row,
                    "v9_stop_probability": str(
                        Decimal(str(probability))
                    ),
                }
        else:
            run = 0
    return None


def _metrics(
    trades: list[dict[str, Any]],
    *,
    threshold: Decimal,
    persistence: int,
    intercept: float,
    coefficients: list[float],
) -> DecisionMetrics:
    selected: list[tuple[dict[str, Any], dict[str, Any]]] = []
    for trade in trades:
        row = _first_persistent_crossing(
            trade,
            threshold=threshold,
            persistence=persistence,
            intercept=intercept,
            coefficients=coefficients,
        )
        if row is not None:
            selected.append((trade, row))

    losses = sum(trade["actual"] == "LOSS" for trade in trades)
    winners = sum(trade["actual"] == "WIN" for trade in trades)
    true_loss = [
        (trade, row)
        for trade, row in selected
        if trade["actual"] == "LOSS"
    ]
    false_winner = [
        (trade, row)
        for trade, row in selected
        if trade["actual"] == "WIN"
    ]
    leads = [
        int(row["bars_before_canonical_exit"])
        for _, row in true_loss
    ]
    return DecisionMetrics(
        selected=len(selected),
        true_loss=len(true_loss),
        false_winner=len(false_winner),
        precision=_ratio(len(true_loss), len(selected)),
        loss_recall=_ratio(len(true_loss), losses),
        winner_mark_rate=_ratio(len(false_winner), winners),
        median_lead_bars=None if not leads else Decimal(str(median(leads))),
    )


def _metric_payload(metrics: DecisionMetrics) -> dict[str, object]:
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
    }


def _choose_policy(
    *,
    trades: list[dict[str, Any]],
    intercept: float,
    coefficients: list[float],
    control_recall: Decimal,
) -> tuple[Decimal | None, int | None, DecisionMetrics | None]:
    candidates: list[tuple[DecisionMetrics, Decimal, int]] = []
    for threshold in THRESHOLDS:
        for persistence in PERSISTENCE_LENGTHS:
            metrics = _metrics(
                trades,
                threshold=threshold,
                persistence=persistence,
                intercept=intercept,
                coefficients=coefficients,
            )
            if (
                metrics.selected >= MIN_SELECTED_TRADES
                and metrics.precision >= TRAIN_PRECISION_FLOOR
                and metrics.winner_mark_rate <= WINNER_MARK_CEILING
                and metrics.median_lead_bars is not None
                and metrics.median_lead_bars >= MIN_MEDIAN_LEAD_BARS
                and metrics.loss_recall > control_recall
            ):
                candidates.append((metrics, threshold, persistence))
    if not candidates:
        return None, None, None

    metrics, threshold, persistence = max(
        candidates,
        key=lambda item: (
            item[0].loss_recall,
            item[0].precision,
            item[0].median_lead_bars or Decimal("-1"),
            -item[2],
            item[1],
        ),
    )
    return threshold, persistence, metrics


def run(v6_json: Path, v9_json: Path) -> dict[str, object]:
    v6 = json.loads(v6_json.read_text())
    v9 = json.loads(v9_json.read_text())

    if v9["identity"] != "QORE_SHARED_VT08_COMPETING_RISK_CALIBRATION_V9":
        raise ValueError("unexpected V9 identity")
    if v9["model"]["type"] != "L2_LOGISTIC_COMPETING_RISK_RESEARCH":
        raise ValueError("unexpected V9 model type")

    intercept = float(v9["model"]["intercept"])
    coefficients = [
        float(value)
        for value in v9["model"]["coefficients"]
    ]

    train_trades = list(v6[TRAIN_WINDOW]["rows"])
    train_control_recall = _d(
        v6[TRAIN_WINDOW]["competing_risk_diagnostics"][
            "terminal_confirmed_loss_recall"
        ]
    )
    threshold, persistence, train_metrics = _choose_policy(
        trades=train_trades,
        intercept=intercept,
        coefficients=coefficients,
        control_recall=train_control_recall,
    )

    windows: dict[str, object] = {}
    for key in (TRAIN_WINDOW, *VALIDATION_WINDOWS):
        control_recall = _d(
            v6[key]["competing_risk_diagnostics"][
                "terminal_confirmed_loss_recall"
            ]
        )
        metrics = (
            DecisionMetrics(
                selected=0,
                true_loss=0,
                false_winner=0,
                precision=Decimal("0"),
                loss_recall=Decimal("0"),
                winner_mark_rate=Decimal("0"),
                median_lead_bars=None,
            )
            if threshold is None or persistence is None
            else _metrics(
                list(v6[key]["rows"]),
                threshold=threshold,
                persistence=persistence,
                intercept=intercept,
                coefficients=coefficients,
            )
        )
        beats_control = metrics.loss_recall > control_recall
        passes = (
            threshold is not None
            and persistence is not None
            and metrics.precision >= VALIDATION_PRECISION_FLOOR
            and metrics.winner_mark_rate <= WINNER_MARK_CEILING
            and metrics.median_lead_bars is not None
            and metrics.median_lead_bars >= MIN_MEDIAN_LEAD_BARS
            and beats_control
        )
        windows[key] = {
            **_metric_payload(metrics),
            "control_v7_loss_recall": str(control_recall),
            "beats_control_v7_recall": beats_control,
            "status": "ADMIT_FOR_ECONOMIC_SHADOW" if passes else "REJECT",
        }

    validation_pass = (
        threshold is not None
        and persistence is not None
        and all(
            windows[key]["status"] == "ADMIT_FOR_ECONOMIC_SHADOW"
            for key in VALIDATION_WINDOWS
        )
    )

    return {
        "schema": SCHEMA,
        "identity": IDENTITY,
        "source_v6_run": 36131607443,
        "source_v9_run": 36134739656,
        "v9_model_frozen": True,
        "research_only": True,
        "consumed_evidence_only": True,
        "runtime_actuation": False,
        "sizing_used": False,
        "risk_weighting_used": False,
        "trailing_used": False,
        "target_extension_used": False,
        "train_window": TRAIN_WINDOW,
        "validation_windows": list(VALIDATION_WINDOWS),
        "policy_search": {
            "thresholds": [str(value) for value in THRESHOLDS],
            "persistence_lengths": list(PERSISTENCE_LENGTHS),
            "training_precision_floor": str(TRAIN_PRECISION_FLOOR),
            "validation_precision_floor": str(VALIDATION_PRECISION_FLOOR),
            "winner_mark_rate_ceiling": str(WINNER_MARK_CEILING),
            "median_lead_bars_floor": str(MIN_MEDIAN_LEAD_BARS),
            "minimum_selected_trades": MIN_SELECTED_TRADES,
            "must_beat_v7_control_recall": True,
            "recovery_active_or_restored_veto": True,
        },
        "selected_policy": (
            None
            if threshold is None or persistence is None
            else {
                "threshold": str(threshold),
                "persistence_observations": persistence,
                "training_metrics": (
                    None
                    if train_metrics is None
                    else _metric_payload(train_metrics)
                ),
            }
        ),
        "windows": windows,
        "validation_pass": validation_pass,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--v6-json", type=Path, required=True)
    parser.add_argument("--v9-json", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()

    payload = run(args.v6_json, args.v9_json)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    print(json.dumps(payload, sort_keys=True))


if __name__ == "__main__":
    main()

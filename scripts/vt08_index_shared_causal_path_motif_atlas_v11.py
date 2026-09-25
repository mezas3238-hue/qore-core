"""V11 causal path motif atlas for Shared terminal-loss recall.

V7 proved that Shared can improve economics by acting on a very small,
high-precision terminal-failure subset. V8-V10 showed that lowering scalar
thresholds, calibrating one-observation probabilities, or adding simple
posterior persistence does not safely expand recall.

V11 changes the representation, not the terminal threshold. It converts each
causal V6 observation sequence into outcome-blind relational path tokens and
learns a small atlas of multi-step motifs on the consumed 5Y training window.
The frozen motif atlas is then evaluated unchanged on consumed recent-2Y and
R66 evidence.

Runtime inputs remain causal only. Realized outcome is used exclusively after
motif construction for offline 5Y motif selection and validation scoring.
There is no sizing, risk weighting, trailing, target mutation or runtime
actuation in this lab.
"""

# ruff: noqa: E501

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from statistics import median
from typing import Any

from qore.infrastructure.core_stack_v2.causal_path_representation import (
    CausalPathPoint,
    represent_causal_path,
)

IDENTITY = "QORE_SHARED_VT08_CAUSAL_PATH_MOTIF_ATLAS_V11"
SCHEMA = "qore.shared.vt08_causal_path_motif_atlas.v11"

SOURCE_V6_RUN = 36131607443
SOURCE_V6_SHARED_HEAD = "1a534d0ae735efef4dcbc0c0be4b110ceaa80501"

TRAIN_WINDOW = "five_year"
VALIDATION_WINDOWS = ("recent_two_year", "r66_consumed_failed_holdout")

NGRAM_LENGTHS = (2, 3, 4)
MIN_MOTIF_TRADE_SUPPORT = 6
MIN_MOTIF_LOSSES = 5
MAX_SELECTED_MOTIFS = 32
TRAIN_PRECISION_FLOOR = Decimal("0.97")
VALIDATION_PRECISION_FLOOR = Decimal("0.95")
WINNER_MARK_CEILING = Decimal("0.005")
MIN_MEDIAN_LEAD_BARS = Decimal("1")

_REQUIRED_POINT_FIELDS = (
    "stop_pressure_bps",
    "target_capacity_bps",
    "recovery_strength_bps",
    "uncertainty_bps",
    "path_support_bps",
    "path_adverse_dominance_bps",
    "path_recovery_persistence_bps",
    "path_terminal_failure_risk_bps",
    "trajectory_support_bps",
    "trajectory_adversity_bps",
    "trajectory_deterioration_pressure_bps",
    "trajectory_recovery_velocity_bps",
    "environment_support_bps",
    "environment_adverse_bps",
    "futures_terminal_evidence_bps",
    "futures_recovery_evidence_bps",
)


@dataclass(frozen=True, slots=True)
class Crossing:
    bars_before_exit: int
    source: str
    motif: str | None = None


@dataclass(frozen=True, slots=True)
class PolicyMetrics:
    selected: int
    true_loss: int
    false_winner: int
    precision: Decimal
    loss_recall: Decimal
    winner_mark_rate: Decimal
    median_lead_bars: Decimal | None
    motif_only: int
    earlier_than_v7: int


def _ratio(numerator: int, denominator: int) -> Decimal:
    if denominator == 0:
        return Decimal("0")
    return Decimal(numerator) / Decimal(denominator)


def _d(value: object) -> Decimal:
    return Decimal(str(value))


def _eligible_row(row: dict[str, Any]) -> bool:
    return all(field in row for field in _REQUIRED_POINT_FIELDS)


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
        trajectory_deterioration_bps=int(
            row["trajectory_deterioration_pressure_bps"]
        ),
        trajectory_recovery_bps=int(row["trajectory_recovery_velocity_bps"]),
        environment_support_bps=int(row["environment_support_bps"]),
        environment_adverse_bps=int(row["environment_adverse_bps"]),
        futures_terminal_bps=int(row["futures_terminal_evidence_bps"]),
        futures_recovery_bps=int(row["futures_recovery_evidence_bps"]),
    )


def _trade_tokens(trade: dict[str, Any]) -> list[dict[str, Any]]:
    points: list[CausalPathPoint] = []
    encoded: list[dict[str, Any]] = []
    for row in trade["observations"]:
        if not _eligible_row(row):
            continue
        points.append(_point(row))
        representation = represent_causal_path(tuple(points))
        encoded.append(
            {
                "bars_before_exit": int(row["bars_before_canonical_exit"]),
                "token": representation.motif_token(),
                "phase": representation.phase.value,
            }
        )
    return encoded


def _trade_motif_crossings(trade: dict[str, Any]) -> dict[str, Crossing]:
    encoded = _trade_tokens(trade)
    crossings: dict[str, Crossing] = {}
    tokens = [row["token"] for row in encoded]
    for index, row in enumerate(encoded):
        for length in NGRAM_LENGTHS:
            if index + 1 < length:
                continue
            motif = " >> ".join(tokens[index + 1 - length : index + 1])
            crossings.setdefault(
                motif,
                Crossing(
                    bars_before_exit=int(row["bars_before_exit"]),
                    source="V11_MOTIF",
                    motif=motif,
                ),
            )
    return crossings


def _v7_crossing(trade: dict[str, Any]) -> Crossing | None:
    row = trade.get("first_terminal_confirmed")
    if row is None:
        return None
    return Crossing(
        bars_before_exit=int(row["bars_before_canonical_exit"]),
        source="V7_TERMINAL_CONFIRMED",
    )


def _first_policy_crossing(
    trade: dict[str, Any],
    selected_motifs: frozenset[str],
    motif_crossings: dict[str, Crossing],
) -> Crossing | None:
    control = _v7_crossing(trade)
    candidates = [
        crossing
        for motif, crossing in motif_crossings.items()
        if motif in selected_motifs
    ]
    motif = max(candidates, key=lambda item: item.bars_before_exit) if candidates else None

    if control is None:
        return motif
    if motif is None:
        return control

    if motif.bars_before_exit > control.bars_before_exit:
        return motif
    return control


def _metrics(
    trades: list[dict[str, Any]],
    selected_motifs: frozenset[str],
    crossings_by_trade: dict[str, dict[str, Crossing]],
) -> PolicyMetrics:
    losses = sum(trade["actual"] == "LOSS" for trade in trades)
    winners = sum(trade["actual"] == "WIN" for trade in trades)

    selected: list[tuple[dict[str, Any], Crossing]] = []
    motif_only = 0
    earlier_than_v7 = 0

    for trade in trades:
        trade_id = str(trade["trade_id"])
        control = _v7_crossing(trade)
        crossing = _first_policy_crossing(
            trade,
            selected_motifs,
            crossings_by_trade[trade_id],
        )
        if crossing is None:
            continue
        selected.append((trade, crossing))
        if crossing.source == "V11_MOTIF":
            if control is None:
                motif_only += 1
            elif crossing.bars_before_exit > control.bars_before_exit:
                earlier_than_v7 += 1

    true_loss = sum(trade["actual"] == "LOSS" for trade, _ in selected)
    false_winner = sum(trade["actual"] == "WIN" for trade, _ in selected)
    loss_leads = [
        Decimal(crossing.bars_before_exit)
        for trade, crossing in selected
        if trade["actual"] == "LOSS"
    ]

    return PolicyMetrics(
        selected=len(selected),
        true_loss=true_loss,
        false_winner=false_winner,
        precision=_ratio(true_loss, len(selected)),
        loss_recall=_ratio(true_loss, losses),
        winner_mark_rate=_ratio(false_winner, winners),
        median_lead_bars=(
            None if not loss_leads else Decimal(str(median(loss_leads)))
        ),
        motif_only=motif_only,
        earlier_than_v7=earlier_than_v7,
    )


def _metric_payload(metrics: PolicyMetrics) -> dict[str, object]:
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
        "motif_only": metrics.motif_only,
        "earlier_than_v7": metrics.earlier_than_v7,
    }


def _candidate_stats(
    trades: list[dict[str, Any]],
    crossings_by_trade: dict[str, dict[str, Crossing]],
) -> list[dict[str, object]]:
    candidates: list[dict[str, object]] = []
    motifs = sorted(
        {
            motif
            for crossings in crossings_by_trade.values()
            for motif in crossings
        }
    )
    by_id = {str(trade["trade_id"]): trade for trade in trades}

    for motif in motifs:
        seen = [
            by_id[trade_id]
            for trade_id, crossings in crossings_by_trade.items()
            if motif in crossings
        ]
        losses = sum(trade["actual"] == "LOSS" for trade in seen)
        winners = sum(trade["actual"] == "WIN" for trade in seen)
        support = len(seen)
        if support < MIN_MOTIF_TRADE_SUPPORT or losses < MIN_MOTIF_LOSSES:
            continue
        candidates.append(
            {
                "motif": motif,
                "support": support,
                "losses": losses,
                "winners": winners,
                "precision": _ratio(losses, support),
            }
        )

    return sorted(
        candidates,
        key=lambda item: (
            _d(item["precision"]),
            int(item["losses"]),
            int(item["support"]),
            str(item["motif"]),
        ),
        reverse=True,
    )


def _admissible(metrics: PolicyMetrics, *, training: bool) -> bool:
    precision_floor = (
        TRAIN_PRECISION_FLOOR if training else VALIDATION_PRECISION_FLOOR
    )
    return (
        metrics.precision >= precision_floor
        and metrics.winner_mark_rate <= WINNER_MARK_CEILING
        and metrics.median_lead_bars is not None
        and metrics.median_lead_bars >= MIN_MEDIAN_LEAD_BARS
    )


def _select_training_motifs(
    trades: list[dict[str, Any]],
    crossings_by_trade: dict[str, dict[str, Crossing]],
) -> tuple[list[str], PolicyMetrics, list[dict[str, object]]]:
    selected: list[str] = []
    current = _metrics(trades, frozenset(), crossings_by_trade)
    audit: list[dict[str, object]] = []

    for candidate in _candidate_stats(trades, crossings_by_trade):
        motif = str(candidate["motif"])
        trial = _metrics(
            trades,
            frozenset((*selected, motif)),
            crossings_by_trade,
        )
        improves_recall = trial.loss_recall > current.loss_recall
        admitted = _admissible(trial, training=True) and improves_recall
        audit.append(
            {
                "motif": motif,
                "support": candidate["support"],
                "losses": candidate["losses"],
                "winners": candidate["winners"],
                "motif_precision": str(candidate["precision"]),
                "combined_precision": str(trial.precision),
                "combined_loss_recall": str(trial.loss_recall),
                "combined_winner_mark_rate": str(trial.winner_mark_rate),
                "admitted": admitted,
            }
        )
        if not admitted:
            continue
        selected.append(motif)
        current = trial
        if len(selected) >= MAX_SELECTED_MOTIFS:
            break

    return selected, current, audit


def _window(
    ledger: dict[str, Any],
    key: str,
    selected_motifs: frozenset[str],
) -> dict[str, object]:
    window = ledger[key]
    trades = list(window["rows"])
    crossings = {
        str(trade["trade_id"]): _trade_motif_crossings(trade)
        for trade in trades
    }
    control = _metrics(trades, frozenset(), crossings)
    combined = _metrics(trades, selected_motifs, crossings)
    beats_control = combined.loss_recall > control.loss_recall
    status = (
        "ADMIT_FOR_ECONOMIC_SHADOW"
        if _admissible(combined, training=False) and beats_control
        else "REJECT"
    )
    return {
        "sample": int(window["sample"]),
        "losses": sum(trade["actual"] == "LOSS" for trade in trades),
        "winners": sum(trade["actual"] == "WIN" for trade in trades),
        "v7_control": _metric_payload(control),
        "v11_combined": _metric_payload(combined),
        "beats_v7_loss_recall": beats_control,
        "status": status,
    }


def run(v6_json: Path) -> dict[str, object]:
    ledger = json.loads(v6_json.read_text())
    if ledger["identity"] != "QORE_SHARED_VT08_INDEX_STOP_TARGET_DISCRIMINATION_V6":
        raise ValueError("unexpected V6 identity")

    training_window = ledger[TRAIN_WINDOW]
    training_trades = list(training_window["rows"])
    training_crossings = {
        str(trade["trade_id"]): _trade_motif_crossings(trade)
        for trade in training_trades
    }
    control = _metrics(training_trades, frozenset(), training_crossings)
    selected, training_metrics, selection_audit = _select_training_motifs(
        training_trades,
        training_crossings,
    )
    frozen = frozenset(selected)

    windows = {
        TRAIN_WINDOW: {
            "sample": int(training_window["sample"]),
            "losses": sum(trade["actual"] == "LOSS" for trade in training_trades),
            "winners": sum(trade["actual"] == "WIN" for trade in training_trades),
            "v7_control": _metric_payload(control),
            "v11_combined": _metric_payload(training_metrics),
            "beats_v7_loss_recall": training_metrics.loss_recall > control.loss_recall,
            "status": (
                "ADMIT_FOR_VALIDATION"
                if _admissible(training_metrics, training=True)
                and training_metrics.loss_recall > control.loss_recall
                else "REJECT"
            ),
        },
        **{
            key: _window(ledger, key, frozen)
            for key in VALIDATION_WINDOWS
        },
    }

    validation_pass = bool(selected) and all(
        windows[key]["status"] == "ADMIT_FOR_ECONOMIC_SHADOW"
        for key in VALIDATION_WINDOWS
    )

    return {
        "schema": SCHEMA,
        "identity": IDENTITY,
        "source_v6_run": SOURCE_V6_RUN,
        "source_v6_shared_head": SOURCE_V6_SHARED_HEAD,
        "research_only": True,
        "consumed_evidence_only": True,
        "train_window": TRAIN_WINDOW,
        "validation_windows": list(VALIDATION_WINDOWS),
        "path_representation_outcome_blind": True,
        "training_outcome_used_for_motif_selection_only": True,
        "runtime_outcome_input": False,
        "future_market_input": False,
        "sizing_used": False,
        "risk_weighting_used": False,
        "trailing_used": False,
        "target_extension_used": False,
        "runtime_actuation": False,
        "motif_policy": {
            "ngram_lengths": list(NGRAM_LENGTHS),
            "minimum_motif_trade_support": MIN_MOTIF_TRADE_SUPPORT,
            "minimum_motif_losses": MIN_MOTIF_LOSSES,
            "maximum_selected_motifs": MAX_SELECTED_MOTIFS,
            "training_precision_floor": str(TRAIN_PRECISION_FLOOR),
            "validation_precision_floor": str(VALIDATION_PRECISION_FLOOR),
            "winner_mark_rate_ceiling": str(WINNER_MARK_CEILING),
            "minimum_median_lead_bars": str(MIN_MEDIAN_LEAD_BARS),
            "must_beat_v7_loss_recall": True,
        },
        "selected_motifs": selected,
        "selection_audit": selection_audit,
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
                "selected_motif_count": len(payload["selected_motifs"]),
                "windows": payload["windows"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()

"""V12 invariant causal path grammar for Shared terminal-loss recall.

V11 proved that relation-preserving path motifs can increase loss recall, but
its exact high-cardinality motifs overfit the 5Y consumed training surface and
harmed winners on recent-2Y and R66 consumed validation.

V12 reduces representation cardinality and requires invariance *inside* the 5Y
training window before a grammar is allowed into the frozen policy:
- low-cardinality phase + relation symbols only;
- support across all three index markets;
- support across multiple chronological 5Y folds;
- zero additional training winner marks beyond the V7 control;
- pooled precision / winner-protection / lead constraints.

The selected grammar set is frozen before evaluation on recent-2Y and R66.
This is consumed-evidence research only and cannot certify LIVE behavior.
"""

# ruff: noqa: E501

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from statistics import median
from typing import Any

from qore.infrastructure.core_stack_v2.causal_path_representation import (
    CausalPathPoint,
    CausalPathRepresentation,
    represent_causal_path,
)

IDENTITY = "QORE_SHARED_VT08_INVARIANT_CAUSAL_PATH_GRAMMAR_V12"
SCHEMA = "qore.shared.vt08_invariant_causal_path_grammar.v12"

SOURCE_V6_RUN = 36131607443
SOURCE_V6_SHARED_HEAD = "1a534d0ae735efef4dcbc0c0be4b110ceaa80501"

TRAIN_WINDOW = "five_year"
VALIDATION_WINDOWS = ("recent_two_year", "r66_consumed_failed_holdout")
NGRAM_LENGTHS = (2, 3)
CHRONOLOGICAL_FOLDS = 5

MIN_TOTAL_SUPPORT = 20
MIN_MARKET_SUPPORT = 4
MIN_FOLD_SUPPORT = 3
MIN_SUPPORTED_FOLDS = 4
MAX_SELECTED_GRAMMARS = 16

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
    grammar: str | None = None


@dataclass(frozen=True, slots=True)
class Metrics:
    selected: int
    true_loss: int
    false_winner: int
    precision: Decimal
    loss_recall: Decimal
    winner_mark_rate: Decimal
    median_lead_bars: Decimal | None
    grammar_only: int
    earlier_than_v7: int


def _ratio(n: int, d: int) -> Decimal:
    return Decimal("0") if d == 0 else Decimal(n) / Decimal(d)


def _eligible(row: dict[str, Any]) -> bool:
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
        trajectory_deterioration_bps=int(row["trajectory_deterioration_pressure_bps"]),
        trajectory_recovery_bps=int(row["trajectory_recovery_velocity_bps"]),
        environment_support_bps=int(row["environment_support_bps"]),
        environment_adverse_bps=int(row["environment_adverse_bps"]),
        futures_terminal_bps=int(row["futures_terminal_evidence_bps"]),
        futures_recovery_bps=int(row["futures_recovery_evidence_bps"]),
    )


def _sign(value: int) -> str:
    if value > 0:
        return "P"
    if value < 0:
        return "N"
    return "Z"


def _symbol(rep: CausalPathRepresentation) -> str:
    """Compress the V11 token into a low-cardinality causal grammar symbol."""

    return ":".join(
        (
            rep.phase.value,
            _sign(rep.stop_target_gap_bps),
            _sign(rep.terminal_recovery_gap_bps),
            _sign(rep.adversity_support_gap_bps),
        )
    )


def _encoded(trade: dict[str, Any]) -> list[dict[str, object]]:
    points: list[CausalPathPoint] = []
    result: list[dict[str, object]] = []
    for row in trade["observations"]:
        if not _eligible(row):
            continue
        points.append(_point(row))
        rep = represent_causal_path(tuple(points))
        result.append(
            {
                "bars_before_exit": int(row["bars_before_canonical_exit"]),
                "symbol": _symbol(rep),
            }
        )
    return result


def _grammar_crossings(trade: dict[str, Any]) -> dict[str, Crossing]:
    encoded = _encoded(trade)
    symbols = [str(item["symbol"]) for item in encoded]
    crossings: dict[str, Crossing] = {}
    for index, item in enumerate(encoded):
        for length in NGRAM_LENGTHS:
            if index + 1 < length:
                continue
            grammar = " >> ".join(symbols[index + 1 - length : index + 1])
            crossings.setdefault(
                grammar,
                Crossing(
                    bars_before_exit=int(item["bars_before_exit"]),
                    source="V12_GRAMMAR",
                    grammar=grammar,
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


def _policy_crossing(
    trade: dict[str, Any],
    selected: frozenset[str],
    crossings: dict[str, Crossing],
) -> Crossing | None:
    control = _v7_crossing(trade)
    grammar_hits = [
        crossing
        for grammar, crossing in crossings.items()
        if grammar in selected
    ]
    grammar = (
        max(grammar_hits, key=lambda item: item.bars_before_exit)
        if grammar_hits
        else None
    )
    if control is None:
        return grammar
    if grammar is None or control.bars_before_exit >= grammar.bars_before_exit:
        return control
    return grammar


def _metrics(
    trades: list[dict[str, Any]],
    selected: frozenset[str],
    by_trade: dict[str, dict[str, Crossing]],
) -> Metrics:
    losses = sum(trade["actual"] == "LOSS" for trade in trades)
    winners = sum(trade["actual"] == "WIN" for trade in trades)
    chosen: list[tuple[dict[str, Any], Crossing, Crossing | None]] = []

    for trade in trades:
        control = _v7_crossing(trade)
        crossing = _policy_crossing(
            trade,
            selected,
            by_trade[str(trade["trade_id"])],
        )
        if crossing is not None:
            chosen.append((trade, crossing, control))

    true_loss = sum(trade["actual"] == "LOSS" for trade, _, _ in chosen)
    false_winner = sum(trade["actual"] == "WIN" for trade, _, _ in chosen)
    leads = [
        Decimal(crossing.bars_before_exit)
        for trade, crossing, _ in chosen
        if trade["actual"] == "LOSS"
    ]
    grammar_only = sum(
        control is None and crossing.source == "V12_GRAMMAR"
        for _, crossing, control in chosen
    )
    earlier = sum(
        control is not None
        and crossing.source == "V12_GRAMMAR"
        and crossing.bars_before_exit > control.bars_before_exit
        for _, crossing, control in chosen
    )
    return Metrics(
        selected=len(chosen),
        true_loss=true_loss,
        false_winner=false_winner,
        precision=_ratio(true_loss, len(chosen)),
        loss_recall=_ratio(true_loss, losses),
        winner_mark_rate=_ratio(false_winner, winners),
        median_lead_bars=None if not leads else Decimal(str(median(leads))),
        grammar_only=grammar_only,
        earlier_than_v7=earlier,
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
        "grammar_only": metrics.grammar_only,
        "earlier_than_v7": metrics.earlier_than_v7,
    }


def _fold_map(trades: list[dict[str, Any]]) -> dict[str, int]:
    ordered = sorted(
        trades,
        key=lambda trade: (
            datetime.fromisoformat(str(trade["exited_at"]).replace("Z", "+00:00")),
            str(trade["trade_id"]),
        ),
    )
    result: dict[str, int] = {}
    total = len(ordered)
    for index, trade in enumerate(ordered):
        fold = min(CHRONOLOGICAL_FOLDS - 1, index * CHRONOLOGICAL_FOLDS // total)
        result[str(trade["trade_id"])] = fold
    return result


def _candidate_stats(
    trades: list[dict[str, Any]],
    by_trade: dict[str, dict[str, Crossing]],
) -> list[dict[str, object]]:
    fold_by_trade = _fold_map(trades)
    outcome = {str(trade["trade_id"]): str(trade["actual"]) for trade in trades}
    market = {str(trade["trade_id"]): str(trade["market"]) for trade in trades}

    grammar_trade_ids: dict[str, set[str]] = defaultdict(set)
    for trade_id, crossings in by_trade.items():
        for grammar in crossings:
            grammar_trade_ids[grammar].add(trade_id)

    candidates: list[dict[str, object]] = []
    required_markets = {str(trade["market"]) for trade in trades}

    for grammar, trade_ids in grammar_trade_ids.items():
        support = len(trade_ids)
        if support < MIN_TOTAL_SUPPORT:
            continue

        losses = sum(outcome[trade_id] == "LOSS" for trade_id in trade_ids)
        winners = support - losses
        if winners != 0:
            continue

        market_support = {
            name: sum(market[trade_id] == name for trade_id in trade_ids)
            for name in required_markets
        }
        if any(value < MIN_MARKET_SUPPORT for value in market_support.values()):
            continue

        fold_support = {
            fold: sum(fold_by_trade[trade_id] == fold for trade_id in trade_ids)
            for fold in range(CHRONOLOGICAL_FOLDS)
        }
        supported_folds = sum(
            value >= MIN_FOLD_SUPPORT for value in fold_support.values()
        )
        if supported_folds < MIN_SUPPORTED_FOLDS:
            continue

        candidates.append(
            {
                "grammar": grammar,
                "support": support,
                "losses": losses,
                "winners": winners,
                "market_support": dict(sorted(market_support.items())),
                "fold_support": fold_support,
                "supported_folds": supported_folds,
            }
        )

    return sorted(
        candidates,
        key=lambda item: (
            int(item["supported_folds"]),
            int(item["support"]),
            str(item["grammar"]),
        ),
        reverse=True,
    )


def _admissible(
    metrics: Metrics,
    control: Metrics,
    *,
    training: bool,
) -> bool:
    precision_floor = (
        TRAIN_PRECISION_FLOOR if training else VALIDATION_PRECISION_FLOOR
    )
    incremental_winners = metrics.false_winner - control.false_winner
    return (
        metrics.precision >= precision_floor
        and metrics.winner_mark_rate
        <= max(WINNER_MARK_CEILING, control.winner_mark_rate)
        and incremental_winners <= 0
        and metrics.median_lead_bars is not None
        and metrics.median_lead_bars >= MIN_MEDIAN_LEAD_BARS
        and metrics.loss_recall > control.loss_recall
    )


def _select(
    trades: list[dict[str, Any]],
    by_trade: dict[str, dict[str, Crossing]],
) -> tuple[list[str], Metrics, Metrics, list[dict[str, object]]]:
    selected: list[str] = []
    control = _metrics(trades, frozenset(), by_trade)
    current = control
    audit: list[dict[str, object]] = []

    for candidate in _candidate_stats(trades, by_trade):
        grammar = str(candidate["grammar"])
        trial = _metrics(
            trades,
            frozenset((*selected, grammar)),
            by_trade,
        )
        admitted = _admissible(trial, control, training=True) and (
            trial.loss_recall > current.loss_recall
        )
        audit.append(
            {
                **candidate,
                "combined_precision": str(trial.precision),
                "combined_loss_recall": str(trial.loss_recall),
                "combined_winner_mark_rate": str(trial.winner_mark_rate),
                "incremental_false_winner": (
                    trial.false_winner - control.false_winner
                ),
                "admitted": admitted,
            }
        )
        if admitted:
            selected.append(grammar)
            current = trial
            if len(selected) >= MAX_SELECTED_GRAMMARS:
                break

    return selected, control, current, audit


def _evaluate(
    window: dict[str, Any],
    selected: frozenset[str],
) -> dict[str, object]:
    trades = list(window["rows"])
    by_trade = {
        str(trade["trade_id"]): _grammar_crossings(trade)
        for trade in trades
    }
    control = _metrics(trades, frozenset(), by_trade)
    combined = _metrics(trades, selected, by_trade)
    incremental_false_winner = combined.false_winner - control.false_winner
    status = (
        "ADMIT_FOR_ECONOMIC_SHADOW"
        if _admissible(combined, control, training=False)
        else "REJECT"
    )
    return {
        "sample": int(window["sample"]),
        "losses": sum(trade["actual"] == "LOSS" for trade in trades),
        "winners": sum(trade["actual"] == "WIN" for trade in trades),
        "v7_control": _payload(control),
        "v12_combined": _payload(combined),
        "incremental_false_winner": incremental_false_winner,
        "beats_v7_loss_recall": combined.loss_recall > control.loss_recall,
        "status": status,
    }


def run(v6_json: Path) -> dict[str, object]:
    ledger = json.loads(v6_json.read_text())
    if ledger["identity"] != "QORE_SHARED_VT08_INDEX_STOP_TARGET_DISCRIMINATION_V6":
        raise ValueError("unexpected V6 identity")

    training = list(ledger[TRAIN_WINDOW]["rows"])
    by_trade = {
        str(trade["trade_id"]): _grammar_crossings(trade)
        for trade in training
    }
    selected, control, combined, audit = _select(training, by_trade)
    frozen = frozenset(selected)

    windows = {
        TRAIN_WINDOW: {
            "sample": int(ledger[TRAIN_WINDOW]["sample"]),
            "losses": sum(trade["actual"] == "LOSS" for trade in training),
            "winners": sum(trade["actual"] == "WIN" for trade in training),
            "v7_control": _payload(control),
            "v12_combined": _payload(combined),
            "incremental_false_winner": combined.false_winner - control.false_winner,
            "beats_v7_loss_recall": combined.loss_recall > control.loss_recall,
            "status": (
                "ADMIT_FOR_VALIDATION"
                if selected and _admissible(combined, control, training=True)
                else "REJECT"
            ),
        },
        **{
            key: _evaluate(ledger[key], frozen)
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
        "source_v11_run": 36140165499,
        "v11_rejected_for_validation": True,
        "research_only": True,
        "consumed_evidence_only": True,
        "train_window": TRAIN_WINDOW,
        "validation_windows": list(VALIDATION_WINDOWS),
        "path_representation_outcome_blind": True,
        "runtime_outcome_input": False,
        "future_market_input": False,
        "sizing_used": False,
        "risk_weighting_used": False,
        "trailing_used": False,
        "target_extension_used": False,
        "runtime_actuation": False,
        "grammar_policy": {
            "ngram_lengths": list(NGRAM_LENGTHS),
            "chronological_folds": CHRONOLOGICAL_FOLDS,
            "minimum_total_support": MIN_TOTAL_SUPPORT,
            "minimum_market_support": MIN_MARKET_SUPPORT,
            "minimum_fold_support": MIN_FOLD_SUPPORT,
            "minimum_supported_folds": MIN_SUPPORTED_FOLDS,
            "maximum_selected_grammars": MAX_SELECTED_GRAMMARS,
            "candidate_additional_training_winners_allowed": 0,
            "combined_incremental_training_winners_allowed": 0,
            "training_precision_floor": str(TRAIN_PRECISION_FLOOR),
            "validation_precision_floor": str(VALIDATION_PRECISION_FLOOR),
            "winner_mark_rate_ceiling_or_control_floor": str(WINNER_MARK_CEILING),
            "minimum_median_lead_bars": str(MIN_MEDIAN_LEAD_BARS),
            "must_beat_v7_loss_recall": True,
            "all_three_markets_required": True,
        },
        "selected_grammars": selected,
        "selection_audit": audit,
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
                "selected_grammar_count": len(payload["selected_grammars"]),
                "windows": payload["windows"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()

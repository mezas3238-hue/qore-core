"""V15 context-conditioned competing-risk calibration for Shared.

V9/V13 show stable ranking signal (AUC about 0.82-0.87) but no single global
probability threshold satisfies the high-precision winner-protection contract.
V11 shows that exact path motifs overfit; V12 shows that an overly coarse
zero-winner grammar selects nothing.

V15 tests a narrower hypothesis: the calibrated competing-risk probability may
mean different things under generic Shared market-state contexts. It keeps the
same V9 point-in-time model, then searches only a small preregistered family of
generic context cells (path/recovery/trajectory/environment/geometry/futures)
and probability floors. Cells must be supported across all three markets and
at least four chronological folds of the consumed 5Y training window.

No symbol identity appears in an inference rule. Market names and chronological
folds are used only for offline robustness qualification. Frozen cells are
evaluated unchanged on recent-2Y and R66 consumed evidence.
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

import numpy as np
import vt08_index_shared_competing_risk_calibration_v9 as v9
from sklearn.linear_model import LogisticRegression

IDENTITY = "QORE_SHARED_VT08_CONTEXT_CONDITIONED_COMPETING_RISK_V15"
SCHEMA = "qore.shared.vt08_context_conditioned_competing_risk.v15"

SOURCE_V6_RUN = 36131607443
SOURCE_V9_RUN = 36134739656
SOURCE_V13_RUN = 36141181714
SOURCE_V14_RUN = 36141583773

TRAIN_WINDOW = "five_year"
VALIDATION_WINDOWS = ("recent_two_year", "r66_consumed_failed_holdout")

MODEL_C = v9.MODEL_C
MODEL_MAX_ITER = v9.MODEL_MAX_ITER

CONTEXT_FIELDS = (
    "path_state",
    "recovery_challenge_state",
    "trajectory_state",
    "environment_state",
    "geometry_state",
    "futures_state",
)
CONTEXT_PAIRS = (
    ("path_state", "environment_state"),
    ("path_state", "geometry_state"),
    ("path_state", "futures_state"),
    ("trajectory_state", "environment_state"),
    ("trajectory_state", "geometry_state"),
    ("geometry_state", "futures_state"),
)

PROBABILITY_FLOORS = tuple(
    Decimal("0.65") + Decimal("0.025") * index
    for index in range(13)
)

CHRONOLOGICAL_FOLDS = 5
MIN_SELECTED_TRADES = 12
MIN_MARKET_SUPPORT = 2
MIN_FOLD_SUPPORT = 2
MIN_SUPPORTED_FOLDS = 4
MAX_SELECTED_CELLS = 12

TRAIN_CELL_PRECISION_FLOOR = Decimal("0.95")
TRAIN_COMBINED_PRECISION_FLOOR = Decimal("0.97")
VALIDATION_PRECISION_FLOOR = Decimal("0.95")
WINNER_MARK_CEILING = Decimal("0.005")
MIN_MEDIAN_LEAD_BARS = Decimal("1")


@dataclass(frozen=True, slots=True)
class Cell:
    fields: tuple[str, ...]
    values: tuple[str, ...]
    probability_floor: Decimal

    def key(self) -> str:
        context = "&".join(
            f"{field}={value}"
            for field, value in zip(self.fields, self.values, strict=True)
        )
        return f"{context}|P>={self.probability_floor}"


@dataclass(frozen=True, slots=True)
class Crossing:
    row: dict[str, Any]
    probability: Decimal
    cell_key: str


@dataclass(frozen=True, slots=True)
class Metrics:
    selected: int
    true_loss: int
    false_winner: int
    precision: Decimal
    loss_recall: Decimal
    winner_mark_rate: Decimal
    median_lead_bars: Decimal | None
    context_only: int
    earlier_than_v7: int


def _ratio(n: int, d: int) -> Decimal:
    return Decimal("0") if d <= 0 else Decimal(n) / Decimal(d)


def _fold_map(trades: list[dict[str, Any]]) -> dict[int, int]:
    ordered = sorted(
        enumerate(trades),
        key=lambda item: (
            datetime.fromisoformat(
                str(item[1]["exited_at"]).replace("Z", "+00:00")
            ),
            str(item[1]["trade_id"]),
        ),
    )
    total = len(ordered)
    result: dict[int, int] = {}
    for position, (trade_index, _) in enumerate(ordered):
        result[trade_index] = min(
            CHRONOLOGICAL_FOLDS - 1,
            position * CHRONOLOGICAL_FOLDS // total,
        )
    return result


def _v7_crossing(trade: dict[str, Any]) -> dict[str, Any] | None:
    return trade.get("first_terminal_confirmed")


def _context_specs() -> tuple[tuple[str, ...], ...]:
    return tuple((field,) for field in CONTEXT_FIELDS) + CONTEXT_PAIRS


def _build_cells(
    trades: list[dict[str, Any]],
    probabilities: np.ndarray,
    meta: list[tuple[int, dict[str, Any]]],
) -> list[Cell]:
    values_by_spec: dict[tuple[str, ...], set[tuple[str, ...]]] = defaultdict(set)
    for _, row in meta:
        for fields in _context_specs():
            if all(field in row for field in fields):
                values_by_spec[fields].add(
                    tuple(str(row[field]) for field in fields)
                )

    return [
        Cell(fields=fields, values=values, probability_floor=floor)
        for fields, value_sets in sorted(values_by_spec.items())
        for values in sorted(value_sets)
        for floor in PROBABILITY_FLOORS
    ]


def _matches(row: dict[str, Any], cell: Cell) -> bool:
    return all(
        str(row.get(field)) == value
        for field, value in zip(cell.fields, cell.values, strict=True)
    )


def _cell_crossings(
    *,
    cells: list[Cell],
    probabilities: np.ndarray,
    meta: list[tuple[int, dict[str, Any]]],
) -> dict[str, dict[int, Crossing]]:
    by_cell: dict[str, dict[int, Crossing]] = {
        cell.key(): {} for cell in cells
    }
    cells_by_context: dict[
        tuple[tuple[str, ...], tuple[str, ...]],
        list[Cell],
    ] = defaultdict(list)
    for cell in cells:
        cells_by_context[(cell.fields, cell.values)].append(cell)
    for matching_cells in cells_by_context.values():
        matching_cells.sort(key=lambda cell: cell.probability_floor)

    specs = _context_specs()
    for probability_float, (trade_index, row) in zip(
        probabilities,
        meta,
        strict=True,
    ):
        probability = Decimal(str(float(probability_float)))
        for fields in specs:
            if not all(field in row for field in fields):
                continue
            values = tuple(str(row[field]) for field in fields)
            matching_cells = cells_by_context.get((fields, values), ())
            for cell in matching_cells:
                if probability < cell.probability_floor:
                    break
                key = cell.key()
                if trade_index in by_cell[key]:
                    continue
                by_cell[key][trade_index] = Crossing(
                    row=row,
                    probability=probability,
                    cell_key=key,
                )
    return by_cell


def _candidate_metrics(
    *,
    trades: list[dict[str, Any]],
    crossings: dict[int, Crossing],
) -> Metrics:
    losses = sum(trade["actual"] == "LOSS" for trade in trades)
    winners = sum(trade["actual"] == "WIN" for trade in trades)
    true_loss = [
        (index, crossing)
        for index, crossing in crossings.items()
        if trades[index]["actual"] == "LOSS"
    ]
    false_winner = [
        (index, crossing)
        for index, crossing in crossings.items()
        if trades[index]["actual"] == "WIN"
    ]
    leads = [
        int(crossing.row["bars_before_canonical_exit"])
        for _, crossing in true_loss
    ]
    return Metrics(
        selected=len(crossings),
        true_loss=len(true_loss),
        false_winner=len(false_winner),
        precision=_ratio(len(true_loss), len(crossings)),
        loss_recall=_ratio(len(true_loss), losses),
        winner_mark_rate=_ratio(len(false_winner), winners),
        median_lead_bars=None if not leads else Decimal(str(median(leads))),
        context_only=len(crossings),
        earlier_than_v7=0,
    )


def _policy_metrics(
    *,
    trades: list[dict[str, Any]],
    selected_keys: frozenset[str],
    by_cell: dict[str, dict[int, Crossing]],
) -> Metrics:
    losses = sum(trade["actual"] == "LOSS" for trade in trades)
    winners = sum(trade["actual"] == "WIN" for trade in trades)

    selected: dict[int, tuple[dict[str, Any], str]] = {}
    context_only = 0
    earlier = 0

    for trade_index, trade in enumerate(trades):
        control = _v7_crossing(trade)
        best_context: Crossing | None = None
        for key in selected_keys:
            crossing = by_cell[key].get(trade_index)
            if crossing is None:
                continue
            if (
                best_context is None
                or int(crossing.row["bars_before_canonical_exit"])
                > int(best_context.row["bars_before_canonical_exit"])
            ):
                best_context = crossing

        if control is None and best_context is None:
            continue
        if control is None and best_context is not None:
            selected[trade_index] = (best_context.row, "CONTEXT")
            context_only += 1
            continue
        if best_context is None:
            selected[trade_index] = (control, "V7")
            continue

        if int(best_context.row["bars_before_canonical_exit"]) > int(
            control["bars_before_canonical_exit"]
        ):
            selected[trade_index] = (best_context.row, "CONTEXT")
            earlier += 1
        else:
            selected[trade_index] = (control, "V7")

    true_loss = [
        (index, value)
        for index, value in selected.items()
        if trades[index]["actual"] == "LOSS"
    ]
    false_winner = [
        (index, value)
        for index, value in selected.items()
        if trades[index]["actual"] == "WIN"
    ]
    leads = [
        int(row["bars_before_canonical_exit"])
        for _, (row, _) in true_loss
    ]
    return Metrics(
        selected=len(selected),
        true_loss=len(true_loss),
        false_winner=len(false_winner),
        precision=_ratio(len(true_loss), len(selected)),
        loss_recall=_ratio(len(true_loss), losses),
        winner_mark_rate=_ratio(len(false_winner), winners),
        median_lead_bars=None if not leads else Decimal(str(median(leads))),
        context_only=context_only,
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
        "context_only": metrics.context_only,
        "earlier_than_v7": metrics.earlier_than_v7,
    }


def _robust_candidates(
    *,
    trades: list[dict[str, Any]],
    cells: list[Cell],
    by_cell: dict[str, dict[int, Crossing]],
) -> list[dict[str, object]]:
    fold_by_trade = _fold_map(trades)
    markets = sorted({str(trade["market"]) for trade in trades})
    result: list[dict[str, object]] = []

    for cell in cells:
        crossings = by_cell[cell.key()]
        metrics = _candidate_metrics(trades=trades, crossings=crossings)
        if (
            metrics.selected < MIN_SELECTED_TRADES
            or metrics.precision < TRAIN_CELL_PRECISION_FLOOR
            or metrics.median_lead_bars is None
            or metrics.median_lead_bars < MIN_MEDIAN_LEAD_BARS
        ):
            continue

        market_support = {
            market: sum(
                str(trades[index]["market"]) == market
                for index in crossings
            )
            for market in markets
        }
        if any(
            support < MIN_MARKET_SUPPORT
            for support in market_support.values()
        ):
            continue

        fold_support = {
            fold: sum(
                fold_by_trade[index] == fold
                for index in crossings
            )
            for fold in range(CHRONOLOGICAL_FOLDS)
        }
        supported_folds = sum(
            support >= MIN_FOLD_SUPPORT
            for support in fold_support.values()
        )
        if supported_folds < MIN_SUPPORTED_FOLDS:
            continue

        result.append(
            {
                "key": cell.key(),
                "fields": list(cell.fields),
                "values": list(cell.values),
                "probability_floor": str(cell.probability_floor),
                "candidate_metrics": _payload(metrics),
                "market_support": market_support,
                "fold_support": fold_support,
                "supported_folds": supported_folds,
            }
        )

    return sorted(
        result,
        key=lambda item: (
            Decimal(str(item["candidate_metrics"]["loss_recall"])),
            Decimal(str(item["candidate_metrics"]["precision"])),
            int(item["supported_folds"]),
            int(item["candidate_metrics"]["selected"]),
        ),
        reverse=True,
    )


def _select_cells(
    *,
    trades: list[dict[str, Any]],
    cells: list[Cell],
    by_cell: dict[str, dict[int, Crossing]],
) -> tuple[list[str], Metrics, Metrics, list[dict[str, object]]]:
    control = _policy_metrics(
        trades=trades,
        selected_keys=frozenset(),
        by_cell=by_cell,
    )
    current = control
    selected: list[str] = []
    audit: list[dict[str, object]] = []

    for candidate in _robust_candidates(
        trades=trades,
        cells=cells,
        by_cell=by_cell,
    ):
        key = str(candidate["key"])
        trial = _policy_metrics(
            trades=trades,
            selected_keys=frozenset((*selected, key)),
            by_cell=by_cell,
        )
        incremental_winners = trial.false_winner - control.false_winner
        admitted = (
            trial.loss_recall > current.loss_recall
            and trial.precision >= TRAIN_COMBINED_PRECISION_FLOOR
            and trial.winner_mark_rate <= WINNER_MARK_CEILING
            and incremental_winners <= 1
            and trial.median_lead_bars is not None
            and trial.median_lead_bars >= MIN_MEDIAN_LEAD_BARS
        )
        audit.append(
            {
                **candidate,
                "combined_metrics": _payload(trial),
                "incremental_false_winner_vs_v7": incremental_winners,
                "admitted": admitted,
            }
        )
        if admitted:
            selected.append(key)
            current = trial
            if len(selected) >= MAX_SELECTED_CELLS:
                break

    return selected, control, current, audit


def _fit_v9(
    ledger: dict[str, Any],
) -> tuple[LogisticRegression, list[dict[str, Any]], np.ndarray, list[tuple[int, dict[str, Any]]]]:
    trades = list(ledger[TRAIN_WINDOW]["rows"])
    x_train, labels, weights, meta = v9._observation_dataset(trades)
    model = LogisticRegression(
        C=MODEL_C,
        max_iter=MODEL_MAX_ITER,
        solver="lbfgs",
        class_weight=None,
    )
    model.fit(x_train, labels, sample_weight=weights)
    probabilities = model.predict_proba(x_train)[:, 1]
    return model, trades, probabilities, meta


def _evaluate_window(
    *,
    model: LogisticRegression,
    window: dict[str, Any],
    selected_cells: list[Cell],
    selected_keys: frozenset[str],
) -> dict[str, object]:
    trades = list(window["rows"])
    x_rows, _, _, meta = v9._observation_dataset(trades)
    probabilities = model.predict_proba(x_rows)[:, 1]
    by_cell = _cell_crossings(
        cells=selected_cells,
        probabilities=probabilities,
        meta=meta,
    )
    control = _policy_metrics(
        trades=trades,
        selected_keys=frozenset(),
        by_cell=by_cell,
    )
    combined = _policy_metrics(
        trades=trades,
        selected_keys=selected_keys,
        by_cell=by_cell,
    )
    incremental_winners = combined.false_winner - control.false_winner
    admitted = (
        bool(selected_keys)
        and combined.loss_recall > control.loss_recall
        and combined.precision >= VALIDATION_PRECISION_FLOOR
        and combined.winner_mark_rate
        <= max(WINNER_MARK_CEILING, control.winner_mark_rate)
        and incremental_winners <= 1
        and combined.median_lead_bars is not None
        and combined.median_lead_bars >= MIN_MEDIAN_LEAD_BARS
    )
    return {
        "sample": int(window["sample"]),
        "v7_control": _payload(control),
        "v15_combined": _payload(combined),
        "incremental_false_winner_vs_v7": incremental_winners,
        "beats_v7_loss_recall": combined.loss_recall > control.loss_recall,
        "status": "ADMIT_FOR_ECONOMIC_SHADOW" if admitted else "REJECT",
    }


def run(v6_json: Path) -> dict[str, object]:
    ledger = json.loads(v6_json.read_text())
    if ledger["identity"] != "QORE_SHARED_VT08_INDEX_STOP_TARGET_DISCRIMINATION_V6":
        raise ValueError("unexpected V6 identity")

    model, train_trades, train_probabilities, train_meta = _fit_v9(ledger)
    cells = _build_cells(train_trades, train_probabilities, train_meta)
    by_cell = _cell_crossings(
        cells=cells,
        probabilities=train_probabilities,
        meta=train_meta,
    )
    selected_keys, control, combined, audit = _select_cells(
        trades=train_trades,
        cells=cells,
        by_cell=by_cell,
    )
    selected_set = frozenset(selected_keys)
    cell_by_key = {cell.key(): cell for cell in cells}
    selected_cells = [cell_by_key[key] for key in selected_keys]

    windows = {
        TRAIN_WINDOW: {
            "sample": int(ledger[TRAIN_WINDOW]["sample"]),
            "v7_control": _payload(control),
            "v15_combined": _payload(combined),
            "incremental_false_winner_vs_v7": (
                combined.false_winner - control.false_winner
            ),
            "beats_v7_loss_recall": combined.loss_recall > control.loss_recall,
            "status": (
                "ADMIT_FOR_VALIDATION"
                if selected_keys
                and combined.loss_recall > control.loss_recall
                and combined.precision >= TRAIN_COMBINED_PRECISION_FLOOR
                and combined.winner_mark_rate <= WINNER_MARK_CEILING
                else "REJECT"
            ),
        },
        **{
            key: _evaluate_window(
                model=model,
                window=ledger[key],
                selected_cells=selected_cells,
                selected_keys=selected_set,
            )
            for key in VALIDATION_WINDOWS
        },
    }

    validation_pass = bool(selected_keys) and all(
        windows[key]["status"] == "ADMIT_FOR_ECONOMIC_SHADOW"
        for key in VALIDATION_WINDOWS
    )

    return {
        "schema": SCHEMA,
        "identity": IDENTITY,
        "source_v6_run": SOURCE_V6_RUN,
        "source_v9_run": SOURCE_V9_RUN,
        "source_v13_run": SOURCE_V13_RUN,
        "source_v14_run": SOURCE_V14_RUN,
        "research_only": True,
        "consumed_evidence_only": True,
        "train_window": TRAIN_WINDOW,
        "validation_windows": list(VALIDATION_WINDOWS),
        "v9_model_reused": True,
        "context_conditioning_generic_only": True,
        "symbol_identity_in_inference_rule": False,
        "market_identity_used_for_offline_robustness_only": True,
        "chronological_fold_used_for_offline_robustness_only": True,
        "runtime_outcome_input": False,
        "future_market_input": False,
        "sizing_used": False,
        "risk_weighting_used": False,
        "runtime_actuation": False,
        "policy": {
            "context_fields": list(CONTEXT_FIELDS),
            "context_pairs": [list(pair) for pair in CONTEXT_PAIRS],
            "probability_floors": [str(value) for value in PROBABILITY_FLOORS],
            "chronological_folds": CHRONOLOGICAL_FOLDS,
            "minimum_selected_trades": MIN_SELECTED_TRADES,
            "minimum_market_support": MIN_MARKET_SUPPORT,
            "minimum_fold_support": MIN_FOLD_SUPPORT,
            "minimum_supported_folds": MIN_SUPPORTED_FOLDS,
            "training_cell_precision_floor": str(TRAIN_CELL_PRECISION_FLOOR),
            "training_combined_precision_floor": str(TRAIN_COMBINED_PRECISION_FLOOR),
            "validation_precision_floor": str(VALIDATION_PRECISION_FLOOR),
            "winner_mark_rate_ceiling": str(WINNER_MARK_CEILING),
            "maximum_selected_cells": MAX_SELECTED_CELLS,
        },
        "selected_cells": selected_keys,
        "selection_audit": audit,
        "windows": windows,
        "validation_pass": validation_pass,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--v6-json", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()

    result = run(args.v6_json)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(
        json.dumps(
            {
                "identity": result["identity"],
                "validation_pass": result["validation_pass"],
                "selected_cell_count": len(result["selected_cells"]),
                "selected_cells": result["selected_cells"],
                "windows": result["windows"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()

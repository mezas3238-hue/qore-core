"""V17 recovery-veto expansion of the V15 context frontier.

V15 exposed a second robust 5Y context with materially higher coverage:

    trajectory_state=DIVERGING
    geometry_state=TERMINAL_COLLAPSE
    V9 probability >= 0.900

but adding it directly damaged four 5Y winners and therefore failed the
winner-protection contract. V17 does not relax that threshold and does not
search new adverse contexts. It asks whether generic causal recovery evidence
can veto the false terminal interpretation.

The adverse expansion context is frozen before scoring. The only selectable
objects are preregistered semantic recovery vetoes (single predicates or OR
pairs) built from Shared's existing recovery, path, futures, trajectory and
environment dimensions. Selection uses consumed 5Y only. The selected veto is
then frozen unchanged on recent-2Y and R66 consumed validation.

Runtime inference never sees realized outcome, future bars, market identity,
calendar/fold identity, sizing or Risk. Outcomes, market names and folds are
offline selection/robustness labels only.
"""

# ruff: noqa: E501

from __future__ import annotations

import argparse
import itertools
import json
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from statistics import median
from typing import Any

import vt08_index_shared_competing_risk_calibration_v9 as v9
import vt08_index_shared_context_conditioned_competing_risk_v15 as v15
from sklearn.linear_model import LogisticRegression

IDENTITY = "QORE_SHARED_VT08_RECOVERY_VETO_CONTEXT_EXPANSION_V17"
SCHEMA = "qore.shared.vt08_recovery_veto_context_expansion.v17"

SOURCE_V6_RUN = 36131607443
SOURCE_V15_RUN = 36141968333
SOURCE_V16_RUN = 36142389500

TRAIN_WINDOW = "five_year"
VALIDATION_WINDOWS = ("recent_two_year", "r66_consumed_failed_holdout")
CHRONOLOGICAL_FOLDS = 5
MIN_EXPANSION_SUPPORT = 20
MIN_MARKET_SUPPORT = 2
MIN_FOLD_SUPPORT = 2
MIN_SUPPORTED_FOLDS = 4
TRAIN_PRECISION_FLOOR = Decimal("0.97")
VALIDATION_PRECISION_FLOOR = Decimal("0.95")
WINNER_MARK_CEILING = Decimal("0.005")
MIN_MEDIAN_LEAD_BARS = Decimal("1")

BASE_CELL = v15.Cell(
    fields=("path_state", "environment_state"),
    values=("CONTESTED", "FRAGILE"),
    probability_floor=Decimal("0.900"),
)
EXPANSION_CELL = v15.Cell(
    fields=("trajectory_state", "geometry_state"),
    values=("DIVERGING", "TERMINAL_COLLAPSE"),
    probability_floor=Decimal("0.900"),
)


@dataclass(frozen=True, slots=True)
class Crossing:
    row: dict[str, Any]
    source: str


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


def _v7_row(trade: dict[str, Any]) -> dict[str, Any] | None:
    return trade.get("first_terminal_confirmed")


def _p_recovery_restored(row: dict[str, Any]) -> bool:
    return row.get("recovery_challenge_state") == "RECOVERY_RESTORED"


def _p_recovery_active_or_restored(row: dict[str, Any]) -> bool:
    return row.get("recovery_challenge_state") in {
        "RECOVERY_ACTIVE",
        "RECOVERY_RESTORED",
    }


def _p_futures_recoverable(row: dict[str, Any]) -> bool:
    return row.get("futures_state") == "RECOVERABLE_ADVERSE"


def _p_path_recoverable(row: dict[str, Any]) -> bool:
    return row.get("path_state") in {"HEALTHY_PULLBACK", "RECOVERING"}


def _p_winner_protection_ge_terminal(row: dict[str, Any]) -> bool:
    return int(row["path_winner_protection_bps"]) >= int(
        row["path_terminal_failure_risk_bps"]
    )


def _p_recovery_ge_stop(row: dict[str, Any]) -> bool:
    return int(row["recovery_strength_bps"]) >= int(row["stop_pressure_bps"])


def _p_futures_recovery_ge_terminal(row: dict[str, Any]) -> bool:
    return int(row["futures_recovery_evidence_bps"]) >= int(
        row["futures_terminal_evidence_bps"]
    )


def _p_trajectory_recovery_ge_deterioration(row: dict[str, Any]) -> bool:
    return int(row["trajectory_recovery_velocity_bps"]) >= int(
        row["trajectory_deterioration_velocity_bps"]
    )


def _p_environment_recovery_ge_adverse(row: dict[str, Any]) -> bool:
    return int(row["environment_recovery_velocity_bps"]) >= int(
        row["environment_adverse_velocity_bps"]
    )


PREDICATES: tuple[tuple[str, Callable[[dict[str, Any]], bool]], ...] = (
    ("RECOVERY_RESTORED", _p_recovery_restored),
    ("RECOVERY_ACTIVE_OR_RESTORED", _p_recovery_active_or_restored),
    ("FUTURES_RECOVERABLE_ADVERSE", _p_futures_recoverable),
    ("PATH_RECOVERABLE", _p_path_recoverable),
    ("WINNER_PROTECTION_GE_TERMINAL", _p_winner_protection_ge_terminal),
    ("RECOVERY_STRENGTH_GE_STOP", _p_recovery_ge_stop),
    ("FUTURES_RECOVERY_GE_TERMINAL", _p_futures_recovery_ge_terminal),
    (
        "TRAJECTORY_RECOVERY_VELOCITY_GE_DETERIORATION",
        _p_trajectory_recovery_ge_deterioration,
    ),
    (
        "ENVIRONMENT_RECOVERY_VELOCITY_GE_ADVERSE",
        _p_environment_recovery_ge_adverse,
    ),
)

PREDICATE_MAP = dict(PREDICATES)


def _veto_specs() -> tuple[tuple[str, ...], ...]:
    singles = tuple((name,) for name, _ in PREDICATES)
    pairs = tuple(
        tuple(names)
        for names in itertools.combinations(
            (name for name, _ in PREDICATES),
            2,
        )
    )
    return singles + pairs


def _veto(row: dict[str, Any], spec: tuple[str, ...]) -> bool:
    return any(PREDICATE_MAP[name](row) for name in spec)


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
    return {
        trade_index: min(
            CHRONOLOGICAL_FOLDS - 1,
            position * CHRONOLOGICAL_FOLDS // total,
        )
        for position, (trade_index, _) in enumerate(ordered)
    }


def _fit_v9(
    ledger: dict[str, Any],
) -> LogisticRegression:
    trades = list(ledger[TRAIN_WINDOW]["rows"])
    x_train, labels, weights, _ = v9._observation_dataset(trades)
    model = LogisticRegression(
        C=v9.MODEL_C,
        max_iter=v9.MODEL_MAX_ITER,
        solver="lbfgs",
        class_weight=None,
    )
    model.fit(x_train, labels, sample_weight=weights)
    return model


def _cell_crossings(
    *,
    model: LogisticRegression,
    window: dict[str, Any],
) -> tuple[
    list[dict[str, Any]],
    dict[int, v15.Crossing],
    dict[int, v15.Crossing],
]:
    trades = list(window["rows"])
    x_rows, _, _, meta = v9._observation_dataset(trades)
    probabilities = model.predict_proba(x_rows)[:, 1]
    by_cell = v15._cell_crossings(
        cells=[BASE_CELL, EXPANSION_CELL],
        probabilities=probabilities,
        meta=meta,
    )
    return (
        trades,
        by_cell[BASE_CELL.key()],
        by_cell[EXPANSION_CELL.key()],
    )


def _best_crossing(
    *,
    control: dict[str, Any] | None,
    base: v15.Crossing | None,
    expansion: v15.Crossing | None,
) -> Crossing | None:
    candidates: list[Crossing] = []
    if control is not None:
        candidates.append(Crossing(row=control, source="V7_TERMINAL"))
    if base is not None:
        candidates.append(Crossing(row=base.row, source="V15_BASE"))
    if expansion is not None:
        candidates.append(Crossing(row=expansion.row, source="V17_EXPANSION"))
    if not candidates:
        return None
    return max(
        candidates,
        key=lambda item: int(item.row["bars_before_canonical_exit"]),
    )


def _metrics(
    *,
    trades: list[dict[str, Any]],
    base: dict[int, v15.Crossing],
    expansion: dict[int, v15.Crossing],
    veto_spec: tuple[str, ...] | None,
) -> Metrics:
    losses = sum(trade["actual"] == "LOSS" for trade in trades)
    winners = sum(trade["actual"] == "WIN" for trade in trades)
    chosen: list[tuple[int, Crossing, dict[str, Any] | None]] = []

    for index, trade in enumerate(trades):
        control = _v7_row(trade)
        expansion_crossing = expansion.get(index)
        if (
            expansion_crossing is not None
            and veto_spec is not None
            and _veto(expansion_crossing.row, veto_spec)
        ):
            expansion_crossing = None

        crossing = _best_crossing(
            control=control,
            base=base.get(index),
            expansion=expansion_crossing,
        )
        if crossing is not None:
            chosen.append((index, crossing, control))

    true_loss = [
        item for item in chosen if trades[item[0]]["actual"] == "LOSS"
    ]
    false_winner = [
        item for item in chosen if trades[item[0]]["actual"] == "WIN"
    ]
    leads = [
        int(crossing.row["bars_before_canonical_exit"])
        for _, crossing, _ in true_loss
    ]
    context_only = sum(
        control is None and crossing.source != "V7_TERMINAL"
        for _, crossing, control in chosen
    )
    earlier = sum(
        control is not None
        and crossing.source != "V7_TERMINAL"
        and int(crossing.row["bars_before_canonical_exit"])
        > int(control["bars_before_canonical_exit"])
        for _, crossing, control in chosen
    )

    return Metrics(
        selected=len(chosen),
        true_loss=len(true_loss),
        false_winner=len(false_winner),
        precision=_ratio(len(true_loss), len(chosen)),
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


def _expansion_stats(
    *,
    trades: list[dict[str, Any]],
    expansion: dict[int, v15.Crossing],
    veto_spec: tuple[str, ...],
) -> dict[str, object]:
    retained = {
        index: crossing
        for index, crossing in expansion.items()
        if not _veto(crossing.row, veto_spec)
    }
    selected = len(retained)
    true_loss = sum(
        trades[index]["actual"] == "LOSS" for index in retained
    )
    false_winner = sum(
        trades[index]["actual"] == "WIN" for index in retained
    )
    fold_by_trade = _fold_map(trades)
    markets = sorted({str(trade["market"]) for trade in trades})
    market_support = {
        market: sum(
            str(trades[index]["market"]) == market for index in retained
        )
        for market in markets
    }
    fold_support = {
        fold: sum(fold_by_trade[index] == fold for index in retained)
        for fold in range(CHRONOLOGICAL_FOLDS)
    }
    supported_folds = sum(
        support >= MIN_FOLD_SUPPORT for support in fold_support.values()
    )
    return {
        "retained": selected,
        "true_loss": true_loss,
        "false_winner": false_winner,
        "precision": str(_ratio(true_loss, selected)),
        "market_support": market_support,
        "fold_support": fold_support,
        "supported_folds": supported_folds,
        "robust": (
            selected >= MIN_EXPANSION_SUPPORT
            and _ratio(true_loss, selected) >= TRAIN_PRECISION_FLOOR
            and all(
                support >= MIN_MARKET_SUPPORT
                for support in market_support.values()
            )
            and supported_folds >= MIN_SUPPORTED_FOLDS
        ),
    }


def _select_veto(
    *,
    trades: list[dict[str, Any]],
    base: dict[int, v15.Crossing],
    expansion: dict[int, v15.Crossing],
) -> tuple[
    tuple[str, ...] | None,
    Metrics,
    Metrics,
    list[dict[str, object]],
]:
    v15_metrics = _metrics(
        trades=trades,
        base=base,
        expansion={},
        veto_spec=None,
    )
    candidates: list[
        tuple[Metrics, tuple[str, ...], dict[str, object]]
    ] = []
    audit: list[dict[str, object]] = []

    for spec in _veto_specs():
        expansion_stats = _expansion_stats(
            trades=trades,
            expansion=expansion,
            veto_spec=spec,
        )
        metrics = _metrics(
            trades=trades,
            base=base,
            expansion=expansion,
            veto_spec=spec,
        )
        incremental_winners = metrics.false_winner - v15_metrics.false_winner
        admissible = (
            bool(expansion_stats["robust"])
            and metrics.loss_recall > v15_metrics.loss_recall
            and metrics.precision >= TRAIN_PRECISION_FLOOR
            and metrics.winner_mark_rate <= WINNER_MARK_CEILING
            and incremental_winners <= 1
            and metrics.median_lead_bars is not None
            and metrics.median_lead_bars >= MIN_MEDIAN_LEAD_BARS
        )
        record = {
            "veto_spec": list(spec),
            "expansion": expansion_stats,
            "combined": _payload(metrics),
            "incremental_false_winner_vs_v15": incremental_winners,
            "admissible": admissible,
        }
        audit.append(record)
        if admissible:
            candidates.append((metrics, spec, record))

    if not candidates:
        return None, v15_metrics, v15_metrics, audit

    metrics, spec, _ = max(
        candidates,
        key=lambda item: (
            item[0].loss_recall,
            item[0].precision,
            item[0].median_lead_bars or Decimal("-1"),
            -len(item[1]),
        ),
    )
    return spec, v15_metrics, metrics, audit


def _evaluate_window(
    *,
    model: LogisticRegression,
    window: dict[str, Any],
    veto_spec: tuple[str, ...] | None,
) -> dict[str, object]:
    trades, base, expansion = _cell_crossings(
        model=model,
        window=window,
    )
    v15_metrics = _metrics(
        trades=trades,
        base=base,
        expansion={},
        veto_spec=None,
    )
    v17_metrics = _metrics(
        trades=trades,
        base=base,
        expansion=expansion,
        veto_spec=veto_spec,
    )
    incremental_winners = (
        v17_metrics.false_winner - v15_metrics.false_winner
    )
    admitted = (
        veto_spec is not None
        and v17_metrics.loss_recall > v15_metrics.loss_recall
        and v17_metrics.precision >= VALIDATION_PRECISION_FLOOR
        and v17_metrics.winner_mark_rate
        <= max(WINNER_MARK_CEILING, v15_metrics.winner_mark_rate)
        and incremental_winners <= 1
        and v17_metrics.median_lead_bars is not None
        and v17_metrics.median_lead_bars >= MIN_MEDIAN_LEAD_BARS
    )
    return {
        "sample": int(window["sample"]),
        "v15_control": _payload(v15_metrics),
        "v17_combined": _payload(v17_metrics),
        "incremental_false_winner_vs_v15": incremental_winners,
        "beats_v15_loss_recall": v17_metrics.loss_recall > v15_metrics.loss_recall,
        "status": "ADMIT_FOR_ECONOMIC_SHADOW" if admitted else "REJECT",
    }


def run(v6_json: Path) -> dict[str, object]:
    ledger = json.loads(v6_json.read_text())
    if ledger["identity"] != "QORE_SHARED_VT08_INDEX_STOP_TARGET_DISCRIMINATION_V6":
        raise ValueError("unexpected V6 identity")

    model = _fit_v9(ledger)
    train_trades, base, expansion = _cell_crossings(
        model=model,
        window=ledger[TRAIN_WINDOW],
    )
    selected_veto, v15_metrics, v17_metrics, audit = _select_veto(
        trades=train_trades,
        base=base,
        expansion=expansion,
    )

    windows = {
        TRAIN_WINDOW: {
            "sample": int(ledger[TRAIN_WINDOW]["sample"]),
            "v15_control": _payload(v15_metrics),
            "v17_combined": _payload(v17_metrics),
            "incremental_false_winner_vs_v15": (
                v17_metrics.false_winner - v15_metrics.false_winner
            ),
            "beats_v15_loss_recall": (
                v17_metrics.loss_recall > v15_metrics.loss_recall
            ),
            "status": (
                "ADMIT_FOR_VALIDATION"
                if selected_veto is not None
                else "REJECT"
            ),
        },
        **{
            key: _evaluate_window(
                model=model,
                window=ledger[key],
                veto_spec=selected_veto,
            )
            for key in VALIDATION_WINDOWS
        },
    }

    validation_pass = selected_veto is not None and all(
        windows[key]["status"] == "ADMIT_FOR_ECONOMIC_SHADOW"
        for key in VALIDATION_WINDOWS
    )

    return {
        "schema": SCHEMA,
        "identity": IDENTITY,
        "source_v6_run": SOURCE_V6_RUN,
        "source_v15_run": SOURCE_V15_RUN,
        "source_v16_run": SOURCE_V16_RUN,
        "research_only": True,
        "consumed_evidence_only": True,
        "train_window": TRAIN_WINDOW,
        "validation_windows": list(VALIDATION_WINDOWS),
        "base_cell_frozen": BASE_CELL.key(),
        "expansion_cell_frozen": EXPANSION_CELL.key(),
        "adverse_context_threshold_retuned": False,
        "veto_family_preregistered": True,
        "veto_selection_train_window_only": True,
        "selected_veto": (
            None if selected_veto is None else list(selected_veto)
        ),
        "runtime_outcome_input": False,
        "future_market_input": False,
        "market_identity_in_inference_rule": False,
        "calendar_or_fold_identity_in_inference_rule": False,
        "sizing_used": False,
        "risk_weighting_used": False,
        "runtime_actuation": False,
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
                "selected_veto": result["selected_veto"],
                "base_cell": result["base_cell_frozen"],
                "expansion_cell": result["expansion_cell_frozen"],
                "windows": result["windows"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()

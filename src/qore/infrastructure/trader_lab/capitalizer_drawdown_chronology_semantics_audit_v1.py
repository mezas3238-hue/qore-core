"""Chronology-semantics audit for Capitalizer drawdown.

The frozen research metric in the milestone replay orders realized trade outcomes
by entry timestamp.  That convention is retained for backward-compatible
certification evidence, but a portfolio episode simulator must know whether it
matches realized balance chronology when positions overlap.

This module is diagnostic only.  It compares the immutable legacy entry-order
DD with an exit-time atomic-batch realized-balance DD for both Surface and the
existing nine-mode outcome oracle.  It does not redefine any acceptance gate.
"""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from dataclasses import asdict, dataclass, replace
from decimal import Decimal
from pathlib import Path
from typing import Any

from qore.infrastructure.trader_lab import (
    capitalizer_cognitive_r_milestone_protection_2r_v1 as milestone,
)
from qore.infrastructure.trader_lab import (
    capitalizer_factor_journey_probe_ranker_v11 as v11,
)
from qore.infrastructure.trader_lab import (
    capitalizer_portfolio_drawdown_feasibility_episode_anatomy_v1 as anatomy,
)
from qore.infrastructure.trader_lab import (
    capitalizer_sequence_failure_memory_abstention_v13 as v13,
)

IDENTITY = "QORE_CAPITALIZER_DRAWDOWN_CHRONOLOGY_SEMANTICS_AUDIT_V1"


@dataclass(frozen=True, slots=True)
class ChronologyAudit:
    period: str
    path: str
    trades: int
    total_r: str
    decimal_accumulation_total_r_drift: str
    legacy_entry_order_dd_r: str
    realized_exit_batch_dd_r: str
    dd_difference_exit_minus_legacy_r: str
    exit_batches: int
    max_simultaneous_exit_batch: int
    max_concurrent_positions: int
    trades_with_exit_rank_different_from_entry_rank: int
    mean_absolute_rank_shift: str
    max_absolute_rank_shift: int


def _exit_batch_metrics(
    rows: tuple[milestone.SimulatedTrade, ...],
) -> dict[str, Any]:
    batches: dict[Any, list[milestone.SimulatedTrade]] = defaultdict(list)
    for row in rows:
        batches[milestone._aware(row.exit_at)].append(row)

    equity = Decimal("0")
    peak = Decimal("0")
    drawdown = Decimal("0")
    maximum_batch = 0
    for timestamp in sorted(batches):
        batch = batches[timestamp]
        maximum_batch = max(maximum_batch, len(batch))
        equity += sum(
            (Decimal(row.realized_gross_r) for row in batch),
            Decimal("0"),
        )
        peak = max(peak, equity)
        drawdown = max(drawdown, peak - equity)

    return {
        "total_r": str(equity),
        "max_drawdown_r": str(drawdown),
        "exit_batches": len(batches),
        "max_simultaneous_exit_batch": maximum_batch,
    }


def _max_concurrent(
    rows: tuple[milestone.SimulatedTrade, ...],
) -> int:
    events: list[tuple[Any, int, int]] = []
    for row in rows:
        events.append((milestone._aware(row.entry_at), 1, 1))
        events.append((milestone._aware(row.exit_at), 0, -1))

    active = 0
    maximum = 0
    for _timestamp, _order, delta in sorted(events):
        active += delta
        if active < 0:
            raise ValueError("chronology audit negative active-position count")
        maximum = max(maximum, active)
    return maximum


def _rank_diagnostics(
    rows: tuple[milestone.SimulatedTrade, ...],
) -> tuple[int, Decimal, int]:
    by_entry = tuple(
        sorted(
            rows,
            key=lambda row: (
                milestone._aware(row.entry_at),
                row.symbol,
            ),
        )
    )
    by_exit = tuple(
        sorted(
            rows,
            key=lambda row: (
                milestone._aware(row.exit_at),
                milestone._aware(row.entry_at),
                row.symbol,
            ),
        )
    )
    entry_rank = {
        (row.symbol, row.entry_at): index
        for index, row in enumerate(by_entry)
    }
    shifts = tuple(
        abs(index - entry_rank[(row.symbol, row.entry_at)])
        for index, row in enumerate(by_exit)
    )
    if not shifts:
        return 0, Decimal("0"), 0
    changed = sum(shift > 0 for shift in shifts)
    mean = Decimal(sum(shifts)) / Decimal(len(shifts))
    return changed, mean, max(shifts)


def _audit(
    *,
    period: str,
    path: str,
    rows: tuple[milestone.SimulatedTrade, ...],
) -> ChronologyAudit:
    legacy = milestone._metrics(rows)
    exit_metrics = _exit_batch_metrics(rows)
    exit_total = Decimal(exit_metrics["total_r"])
    legacy_total = Decimal(legacy["total_r"])
    total_drift = exit_total - legacy_total
    if abs(total_drift) > Decimal("1e-18"):
        raise ValueError(
            "chronology audit material Total-R drift "
            f"{total_drift}"
        )
    changed, mean_shift, max_shift = _rank_diagnostics(rows)
    legacy_dd = Decimal(legacy["max_drawdown_r"])
    exit_dd = Decimal(exit_metrics["max_drawdown_r"])
    return ChronologyAudit(
        period=period,
        path=path,
        trades=len(rows),
        total_r=legacy["total_r"],
        decimal_accumulation_total_r_drift=str(total_drift),
        legacy_entry_order_dd_r=str(legacy_dd),
        realized_exit_batch_dd_r=str(exit_dd),
        dd_difference_exit_minus_legacy_r=str(exit_dd - legacy_dd),
        exit_batches=int(exit_metrics["exit_batches"]),
        max_simultaneous_exit_batch=int(
            exit_metrics["max_simultaneous_exit_batch"]
        ),
        max_concurrent_positions=_max_concurrent(rows),
        trades_with_exit_rank_different_from_entry_rank=changed,
        mean_absolute_rank_shift=str(mean_shift),
        max_absolute_rank_shift=max_shift,
    )


def build_report(
    development_root: Path,
    validation_root: Path,
    reserved_root: Path,
    development_validation_context_root: Path,
    reserved_context_root: Path,
) -> tuple[dict[str, Any], tuple[ChronologyAudit, ...]]:
    windows, contextual_model = v13._load_windows(
        development_root,
        validation_root,
        reserved_root,
        development_validation_context_root,
        reserved_context_root,
    )
    simultaneous: dict[
        tuple[str, str, str], tuple[milestone.SimulatedTrade, ...]
    ] = {}
    for period, (ledgers, _contexts) in windows.items():
        simultaneous.update(
            v11._simultaneous_map(period=period, ledgers=ledgers)
        )

    previous = dict(v11._SIMULTANEOUS)
    v11._SIMULTANEOUS.clear()
    v11._SIMULTANEOUS.update(simultaneous)
    audits: list[ChronologyAudit] = []
    try:
        for period, (ledgers, contexts) in windows.items():
            _control, surface, decisions = anatomy._surface_ledger(
                period=period,
                ledgers=ledgers,
                contexts=contexts,
                contextual_model=contextual_model,
            )
            surface = anatomy._canonical_rows(surface)
            audits.append(
                _audit(period=period, path="SURFACE", rows=surface)
            )

            by_mode = {
                mode: {(row.symbol, row.entry_at): row for row in rows}
                for mode, rows in ledgers.items()
            }
            oracle_rows: list[milestone.SimulatedTrade] = []
            for surface_row in surface:
                key = (surface_row.symbol, surface_row.entry_at)
                decision = decisions[key]
                _mode, raw, value, _outcomes = anatomy._best_existing_action(
                    key=key,
                    multiplier=Decimal(decision.base_multiplier),
                    by_mode=by_mode,
                )
                oracle_rows.append(
                    replace(raw, realized_gross_r=str(value))
                )
            audits.append(
                _audit(
                    period=period,
                    path="OUTCOME_ORACLE_DIAGNOSTIC",
                    rows=tuple(oracle_rows),
                )
            )
    finally:
        v11._SIMULTANEOUS.clear()
        v11._SIMULTANEOUS.update(previous)

    return (
        {
            "identity": IDENTITY,
            "evaluation": "LEGACY_ENTRY_ORDER_VS_REALIZED_EXIT_BATCH_DD",
            "legacy_metric_definition": (
                "SORT_REALIZED_TRADE_R_BY_ENTRY_AT_THEN_SYMBOL"
            ),
            "exit_metric_definition": (
                "SORT_BY_EXIT_AT_AND_APPLY_SAME_TIMESTAMP_EXITS_ATOMICALLY"
            ),
            "legacy_acceptance_gate_changed": False,
            "mark_to_market_equity_modeled": False,
            "outcome_oracle_future_information_used": True,
            "outcome_oracle_candidate": False,
            "results": [asdict(row) for row in audits],
            "policy_economics_run": False,
            "trader_certified": False,
            "live_authorized": False,
            "real_capital_authorized": False,
            "next_phase": (
                "DEFINE_PORTFOLIO_EPISODE_SIMULATOR_WITH_EXPLICIT_"
                "LEGACY_AND_REALIZED_CHRONOLOGY_CONTRACTS"
            ),
        },
        tuple(audits),
    )


def write_report(
    report: dict[str, Any],
    audits: tuple[ChronologyAudit, ...],
    output: Path,
) -> None:
    output.mkdir(parents=True, exist_ok=True)
    stem = "capitalizer-drawdown-chronology-semantics-audit-v1"
    (output / f"{stem}.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    with (output / f"{stem}-rows.jsonl").open(
        "w", encoding="utf-8"
    ) as handle:
        for row in audits:
            handle.write(json.dumps(asdict(row), sort_keys=True) + "\n")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("development_root", type=Path)
    parser.add_argument("validation_root", type=Path)
    parser.add_argument("reserved_root", type=Path)
    parser.add_argument("development_validation_context_root", type=Path)
    parser.add_argument("reserved_context_root", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()

    report, audits = build_report(
        args.development_root,
        args.validation_root,
        args.reserved_root,
        args.development_validation_context_root,
        args.reserved_context_root,
    )
    write_report(report, audits, args.output)
    print(json.dumps(report, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

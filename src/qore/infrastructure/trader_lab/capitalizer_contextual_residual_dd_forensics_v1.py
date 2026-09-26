"""Forensics of the residual max-drawdown path under contextual routing.

Reconstructs the development-trained CONTEXT_STABILITY_STAGE policy and isolates
the exact peak-to-trough trade sequence that creates max drawdown in development
and consumed validation.  The purpose is diagnostic: identify which market
states and routed modes still contribute negative R while the engine is already
in WATCH/DEFENSIVE.

No rules are selected or changed by this module.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from decimal import Decimal
from pathlib import Path
from typing import Any

from qore.infrastructure.trader_lab import (
    capitalizer_cognitive_r_milestone_protection_2r_v1 as milestone,
)
from qore.infrastructure.trader_lab import (
    capitalizer_contextual_stability_router_2r_v1 as router,
)
from qore.infrastructure.trader_lab import (
    capitalizer_cross_market_stability_governor_2r_v1 as governor,
)
from qore.infrastructure.trader_lab import (
    capitalizer_max_recovery_direct_m1_replay_v1 as direct,
)
from qore.infrastructure.trader_lab import capitalizer_native_market_context_v1 as context

IDENTITY = "QORE_CAPITALIZER_CONTEXTUAL_RESIDUAL_DD_FORENSICS_V1"
POLICY = "CONTEXT_STABILITY_STAGE"


@dataclass(frozen=True, slots=True)
class PathRow:
    index: int
    role: str
    symbol: str
    session: str
    operating_date: str
    entry_at: str
    realized_gross_r: str
    equity_r: str
    running_peak_r: str
    drawdown_r: str
    stability_state: str
    base_mode: str
    final_mode: str
    regime_signature: str
    destination_state: str
    hierarchy_level: str
    hierarchy_support: int


def _selected_path(
    *,
    role: str,
    ledgers: dict[str, tuple[milestone.SimulatedTrade, ...]],
    contexts: dict[tuple[str, str], context.NativeContextRow],
    model: dict[str, Any],
) -> tuple[PathRow, ...]:
    by_mode = {
        arm: {(row.symbol, row.entry_at): row for row in rows}
        for arm, rows in ledgers.items()
    }
    baseline = ledgers[milestone.ProtectionMode.ORIGINAL.value]
    ordered = tuple(
        sorted(
            baseline,
            key=lambda row: (direct._aware(row.entry_at), row.symbol),
        )
    )

    chosen: list[milestone.SimulatedTrade] = []
    rows: list[PathRow] = []
    equity = Decimal("0")
    peak = Decimal("0")
    for index, trade in enumerate(ordered):
        key = (trade.symbol, trade.entry_at)
        ctx = contexts[key]
        history = governor._closed_history(
            tuple(chosen),
            entry_at=router.direct._aware(trade.entry_at),
        )
        state, _eq, _pk, _dd, _ls = governor._state(history)
        base_mode, level, support = router._lookup(model, ctx)
        final_mode, _overlay = router._overlay(
            policy=POLICY,
            base_mode=base_mode,
            state=state,
        )
        selected = by_mode[final_mode][key]
        chosen.append(selected)
        value = Decimal(selected.realized_gross_r)
        equity += value
        peak = max(peak, equity)
        dd = peak - equity
        rows.append(
            PathRow(
                index=index,
                role=role,
                symbol=trade.symbol,
                session=trade.session,
                operating_date=trade.operating_date,
                entry_at=trade.entry_at,
                realized_gross_r=str(value),
                equity_r=str(equity),
                running_peak_r=str(peak),
                drawdown_r=str(dd),
                stability_state=state.value,
                base_mode=base_mode,
                final_mode=final_mode,
                regime_signature=ctx.regime_signature,
                destination_state=ctx.destination_state,
                hierarchy_level=level,
                hierarchy_support=support,
            )
        )
    return tuple(rows)


def _segment(rows: tuple[PathRow, ...]) -> tuple[dict[str, Any], tuple[PathRow, ...]]:
    if not rows:
        raise ValueError("DD forensics requires rows")
    trough = max(rows, key=lambda row: Decimal(row.drawdown_r))
    trough_index = trough.index

    peak_index = -1
    peak_value = Decimal("0")
    for row in rows[: trough_index + 1]:
        running_peak = Decimal(row.running_peak_r)
        if running_peak >= peak_value:
            peak_value = running_peak
            if Decimal(row.equity_r) == running_peak:
                peak_index = row.index

    start = peak_index + 1
    segment = rows[start : trough_index + 1]
    if not segment:
        raise ValueError("DD forensics isolated empty segment")

    symbol_r: dict[str, Decimal] = defaultdict(lambda: Decimal("0"))
    mode_r: dict[str, Decimal] = defaultdict(lambda: Decimal("0"))
    state_r: dict[str, Decimal] = defaultdict(lambda: Decimal("0"))
    destination_r: dict[str, Decimal] = defaultdict(lambda: Decimal("0"))
    regime_r: dict[str, Decimal] = defaultdict(lambda: Decimal("0"))
    for row in segment:
        value = Decimal(row.realized_gross_r)
        symbol_r[row.symbol] += value
        mode_r[row.final_mode] += value
        state_r[row.stability_state] += value
        destination_r[row.destination_state] += value
        regime_r[row.regime_signature] += value

    worst_rows = sorted(
        segment,
        key=lambda row: Decimal(row.realized_gross_r),
    )[:20]

    return {
        "max_drawdown_r": trough.drawdown_r,
        "peak_index": peak_index,
        "trough_index": trough_index,
        "segment_trades": len(segment),
        "segment_total_r": str(
            sum(
                (Decimal(row.realized_gross_r) for row in segment),
                Decimal("0"),
            )
        ),
        "segment_losses": sum(
            Decimal(row.realized_gross_r) < 0 for row in segment
        ),
        "segment_wins": sum(
            Decimal(row.realized_gross_r) > 0 for row in segment
        ),
        "symbol_r": {key: str(value) for key, value in sorted(symbol_r.items())},
        "mode_r": {key: str(value) for key, value in sorted(mode_r.items())},
        "state_r": {key: str(value) for key, value in sorted(state_r.items())},
        "destination_r": {
            key: str(value) for key, value in sorted(destination_r.items())
        },
        "regime_r": {key: str(value) for key, value in sorted(regime_r.items())},
        "state_counts": dict(
            sorted(Counter(row.stability_state for row in segment).items())
        ),
        "mode_counts": dict(
            sorted(Counter(row.final_mode for row in segment).items())
        ),
        "destination_counts": dict(
            sorted(Counter(row.destination_state for row in segment).items())
        ),
        "worst_20": [asdict(row) for row in worst_rows],
    }, segment


def build_report(
    development_root: Path,
    validation_root: Path,
    context_root: Path,
) -> tuple[dict[str, Any], tuple[PathRow, ...]]:
    development = router._load_selected(
        development_root,
        expected=router.EXPECTED_DEVELOPMENT_TRADES,
    )
    validation = router._load_selected(
        validation_root,
        expected=router.EXPECTED_VALIDATION_TRADES,
    )
    dev_context = router._load_contexts(context_root, role="dev")
    val_context = router._load_contexts(context_root, role="holdout")
    model = router._freeze_model(
        development=development,
        contexts=dev_context,
    )

    dev_path = _selected_path(
        role="DEVELOPMENT",
        ledgers=development,
        contexts=dev_context,
        model=model,
    )
    val_path = _selected_path(
        role="CONSUMED_VALIDATION_2022_2024",
        ledgers=validation,
        contexts=val_context,
        model=model,
    )
    dev_summary, dev_segment = _segment(dev_path)
    val_summary, val_segment = _segment(val_path)

    report = {
        "identity": IDENTITY,
        "policy": POLICY,
        "development": dev_summary,
        "validation": val_summary,
        "development_segment_rows": len(dev_segment),
        "validation_segment_rows": len(val_segment),
        "model_trained_on_development_only": True,
        "validation_outcomes_visible_to_model": False,
        "forensics_changes_runtime_rules": False,
        "rule_promotion_allowed": False,
        "trader_certified": False,
        "next_phase": "ENGINEER_SEQUENCE_SPECIFIC_PROTECTION_FROM_RESIDUAL_DD_FACTS",
    }
    return report, tuple((*dev_segment, *val_segment))


def write_report(
    report: dict[str, Any],
    rows: tuple[PathRow, ...],
    output: Path,
) -> None:
    output.mkdir(parents=True, exist_ok=True)
    (output / "capitalizer-contextual-residual-dd-forensics-v1.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    with (
        output / "capitalizer-contextual-residual-dd-forensics-v1-segments.jsonl"
    ).open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(asdict(row), sort_keys=True) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("development_root", type=Path)
    parser.add_argument("validation_root", type=Path)
    parser.add_argument("context_root", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    report, rows = build_report(
        args.development_root,
        args.validation_root,
        args.context_root,
    )
    write_report(report, rows, args.output)
    print(json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    main()

"""Residual drawdown forensics for the first-use 2020-2022 holdout.

This module does NOT tune or promote a rule. It replays the already-frozen
SURFACE_SELECTIVE candidate, identifies its exact maximum-drawdown segment,
and measures the economic trade-off created by risk compression:

- loss R avoided by scaling adverse trades down;
- positive R suppressed by scaling winning recovery trades down;
- which symbols / sessions / milestone modes / hazard states dominate the
  residual drawdown;
- whether the candidate is stuck at compressed exposure after conditions have
  improved.

The reserved window is already consumed by the frozen-candidate evaluation, so
these diagnostics may be used to design a NEW architecture only. Any new
architecture must be validated on a different non-overlapping holdout.
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
    capitalizer_max_recovery_direct_m1_replay_v1 as direct,
)
from qore.infrastructure.trader_lab import (
    capitalizer_surface_selective_frozen_holdout_v1 as frozen,
)

IDENTITY = "QORE_CAPITALIZER_RESERVED_HOLDOUT_RESIDUAL_DD_FORENSICS_V1"


@dataclass(frozen=True, slots=True)
class DrawdownTrade:
    index: int
    symbol: str
    session: str
    operating_date: str
    entry_at: str
    selected_mode: str
    hazard_score: int
    adverse_votes: int
    risk_multiplier: str
    unscaled_r: str
    scaled_r: str
    equity_after_r: str
    peak_before_r: str
    drawdown_after_r: str
    compressed_positive_recovery_r: str
    avoided_negative_loss_r: str


def _prepare(
    development_root: Path,
    development_context_root: Path,
    reserved_root: Path,
    reserved_context_root: Path,
) -> tuple[
    dict[str, tuple[milestone.SimulatedTrade, ...]],
    dict[tuple[str, str], Any],
    dict[str, Any],
]:
    development = router._load_selected(
        development_root,
        expected=948,
    )
    dev_context = router._load_contexts(development_context_root, role="dev")
    model = router._freeze_model(
        development=development,
        contexts=dev_context,
    )

    raw_reserved = {
        mode.value: direct._load_mode(reserved_root, mode=mode)
        for mode in milestone.ProtectionMode
    }
    selected_reserved = {
        mode: direct._max3_milestone(rows)
        for mode, rows in raw_reserved.items()
    }
    baseline = selected_reserved[milestone.ProtectionMode.ORIGINAL.value]
    baseline_keys = {(row.symbol, row.entry_at) for row in baseline}

    all_context = frozen._load_contexts_reserved(reserved_context_root)
    missing = baseline_keys - set(all_context)
    if missing:
        raise ValueError(f"reserved MAX3 context missing {len(missing)} identities")
    contexts = {key: all_context[key] for key in baseline_keys}
    return selected_reserved, contexts, model


def _max_dd_segment(
    rows: tuple[milestone.SimulatedTrade, ...],
) -> tuple[int, int, Decimal]:
    ordered = tuple(
        sorted(rows, key=lambda row: (direct._aware(row.entry_at), row.symbol))
    )
    equity = Decimal("0")
    peak = Decimal("0")
    peak_index = -1
    segment_peak_index = -1
    max_dd = Decimal("0")
    trough_index = -1

    for index, row in enumerate(ordered):
        value = Decimal(row.realized_gross_r)
        equity += value
        if equity > peak:
            peak = equity
            peak_index = index
        dd = peak - equity
        if dd > max_dd:
            max_dd = dd
            segment_peak_index = peak_index
            trough_index = index

    if trough_index < 0:
        return 0, 0, Decimal("0")
    return segment_peak_index + 1, trough_index, max_dd


def _window_rows(
    *,
    ledgers: dict[str, tuple[milestone.SimulatedTrade, ...]],
    candidate: tuple[milestone.SimulatedTrade, ...],
    decisions: tuple[frozen.FrozenDecision, ...],
) -> tuple[DrawdownTrade, ...]:
    ordered = tuple(
        sorted(candidate, key=lambda row: (direct._aware(row.entry_at), row.symbol))
    )
    decision_by_key = {
        (row.symbol, row.entry_at): row
        for row in decisions
    }
    by_mode = {
        mode: {(row.symbol, row.entry_at): row for row in rows}
        for mode, rows in ledgers.items()
    }

    start, end, _ = _max_dd_segment(candidate)
    equity = Decimal("0")
    peak = Decimal("0")
    result: list[DrawdownTrade] = []

    for index, scaled in enumerate(ordered):
        key = (scaled.symbol, scaled.entry_at)
        decision = decision_by_key[key]
        unscaled = by_mode[decision.selected_mode][key]
        scaled_r = Decimal(scaled.realized_gross_r)
        unscaled_r = Decimal(unscaled.realized_gross_r)
        peak_before = peak
        equity += scaled_r
        peak = max(peak, equity)
        dd = peak - equity

        if not (start <= index <= end):
            continue

        multiplier = Decimal(decision.risk_multiplier)
        compressed_positive = Decimal("0")
        avoided_negative = Decimal("0")
        if unscaled_r > 0 and multiplier < 1:
            compressed_positive = unscaled_r - scaled_r
        if unscaled_r < 0 and multiplier < 1:
            avoided_negative = scaled_r - unscaled_r

        result.append(
            DrawdownTrade(
                index=index,
                symbol=scaled.symbol,
                session=scaled.session,
                operating_date=scaled.operating_date,
                entry_at=scaled.entry_at,
                selected_mode=decision.selected_mode,
                hazard_score=decision.hazard_score,
                adverse_votes=decision.adverse_votes,
                risk_multiplier=decision.risk_multiplier,
                unscaled_r=str(unscaled_r),
                scaled_r=str(scaled_r),
                equity_after_r=str(equity),
                peak_before_r=str(peak_before),
                drawdown_after_r=str(dd),
                compressed_positive_recovery_r=str(compressed_positive),
                avoided_negative_loss_r=str(avoided_negative),
            )
        )
    return tuple(result)


def _rolling_worst(
    rows: tuple[milestone.SimulatedTrade, ...],
    *,
    length: int,
) -> dict[str, Any]:
    ordered = tuple(
        sorted(rows, key=lambda row: (direct._aware(row.entry_at), row.symbol))
    )
    if len(ordered) < length:
        raise ValueError("rolling window longer than ledger")
    values = tuple(Decimal(row.realized_gross_r) for row in ordered)
    worst_sum: Decimal | None = None
    worst_start = 0
    for start in range(0, len(values) - length + 1):
        total = sum(values[start:start + length], Decimal("0"))
        if worst_sum is None or total < worst_sum:
            worst_sum = total
            worst_start = start
    assert worst_sum is not None
    subset = ordered[worst_start:worst_start + length]
    return {
        "length": length,
        "sum_r": str(worst_sum),
        "start_index": worst_start,
        "end_index": worst_start + length - 1,
        "start_entry_at": subset[0].entry_at,
        "end_entry_at": subset[-1].entry_at,
        "symbols": dict(sorted(Counter(row.symbol for row in subset).items())),
    }


def build_report(
    development_root: Path,
    development_context_root: Path,
    reserved_root: Path,
    reserved_context_root: Path,
) -> tuple[dict[str, Any], tuple[DrawdownTrade, ...]]:
    ledgers, contexts, model = _prepare(
        development_root,
        development_context_root,
        reserved_root,
        reserved_context_root,
    )
    result, decisions, candidate = frozen._simulate_reserved(
        ledgers=ledgers,
        contexts=contexts,
        model=model,
    )
    start, end, max_dd = _max_dd_segment(candidate)
    dd_rows = _window_rows(
        ledgers=ledgers,
        candidate=candidate,
        decisions=decisions,
    )

    positive_suppressed = sum(
        (Decimal(row.compressed_positive_recovery_r) for row in dd_rows),
        Decimal("0"),
    )
    negative_avoided = sum(
        (Decimal(row.avoided_negative_loss_r) for row in dd_rows),
        Decimal("0"),
    )
    scaled_segment_r = sum(
        (Decimal(row.scaled_r) for row in dd_rows),
        Decimal("0"),
    )
    unscaled_segment_r = sum(
        (Decimal(row.unscaled_r) for row in dd_rows),
        Decimal("0"),
    )

    by_symbol: dict[str, dict[str, str | int]] = {}
    for symbol in sorted({row.symbol for row in dd_rows}):
        subset = tuple(row for row in dd_rows if row.symbol == symbol)
        by_symbol[symbol] = {
            "trades": len(subset),
            "scaled_r": str(sum((Decimal(row.scaled_r) for row in subset), Decimal("0"))),
            "unscaled_r": str(sum((Decimal(row.unscaled_r) for row in subset), Decimal("0"))),
            "compressed_positive_r": str(
                sum(
                    (Decimal(row.compressed_positive_recovery_r) for row in subset),
                    Decimal("0"),
                )
            ),
            "avoided_negative_r": str(
                sum(
                    (Decimal(row.avoided_negative_loss_r) for row in subset),
                    Decimal("0"),
                )
            ),
        }

    by_multiplier: dict[str, dict[str, str | int]] = {}
    for multiplier in sorted({row.risk_multiplier for row in dd_rows}, key=Decimal):
        subset = tuple(row for row in dd_rows if row.risk_multiplier == multiplier)
        by_multiplier[multiplier] = {
            "trades": len(subset),
            "wins": sum(Decimal(row.unscaled_r) > 0 for row in subset),
            "losses": sum(Decimal(row.unscaled_r) < 0 for row in subset),
            "scaled_r": str(sum((Decimal(row.scaled_r) for row in subset), Decimal("0"))),
            "unscaled_r": str(sum((Decimal(row.unscaled_r) for row in subset), Decimal("0"))),
            "compressed_positive_r": str(
                sum(
                    (Decimal(row.compressed_positive_recovery_r) for row in subset),
                    Decimal("0"),
                )
            ),
            "avoided_negative_r": str(
                sum(
                    (Decimal(row.avoided_negative_loss_r) for row in subset),
                    Decimal("0"),
                )
            ),
        }

    hazard_score_counts = Counter(row.hazard_score for row in dd_rows)
    mode_counts = Counter(row.selected_mode for row in dd_rows)
    session_counts = Counter(row.session for row in dd_rows)

    full_metrics = result["metrics"]
    return {
        "identity": IDENTITY,
        "source_candidate_identity": frozen.CANDIDATE_IDENTITY,
        "window_role": "CONSUMED_RESERVED_HOLDOUT_FORENSICS",
        "reserved_window_start": frozen.RESERVED_START,
        "reserved_window_end_exclusive": frozen.RESERVED_END,
        "candidate_metrics": full_metrics,
        "max_dd_r_reproduced": str(max_dd),
        "max_dd_start_index": start,
        "max_dd_trough_index": end,
        "max_dd_segment_trades": len(dd_rows),
        "max_dd_segment_scaled_r": str(scaled_segment_r),
        "max_dd_segment_unscaled_r": str(unscaled_segment_r),
        "compressed_positive_recovery_r_in_segment": str(positive_suppressed),
        "avoided_negative_loss_r_in_segment": str(negative_avoided),
        "recovery_drag_minus_loss_protection_r": str(
            positive_suppressed - negative_avoided
        ),
        "by_symbol": by_symbol,
        "by_multiplier": by_multiplier,
        "hazard_score_counts": {
            str(key): value for key, value in sorted(hazard_score_counts.items())
        },
        "mode_counts": dict(sorted(mode_counts.items())),
        "session_counts": dict(sorted(session_counts.items())),
        "rolling_worst_10": _rolling_worst(candidate, length=10),
        "rolling_worst_20": _rolling_worst(candidate, length=20),
        "rolling_worst_40": _rolling_worst(candidate, length=40),
        "current_outcome_used_to_make_original_decision": False,
        "current_outcome_used_for_posthoc_forensics": True,
        "candidate_reselected_after_holdout": False,
        "rule_promotion_allowed": False,
        "trader_certified": False,
        "next_phase": (
            "DESIGN_RECOVERY_RELEASE_WITH_SEPARATE_NEW_HOLDOUT"
            if positive_suppressed > negative_avoided
            else "DESIGN_STRONGER_ADVERSE_CLUSTER_DEFENSE_WITH_NEW_HOLDOUT"
        ),
    }, dd_rows


def write_report(
    report: dict[str, Any],
    rows: tuple[DrawdownTrade, ...],
    output: Path,
) -> None:
    output.mkdir(parents=True, exist_ok=True)
    (output / "capitalizer-reserved-holdout-residual-dd-forensics-v1.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    with (
        output / "capitalizer-reserved-holdout-residual-dd-forensics-v1-rows.jsonl"
    ).open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(asdict(row), sort_keys=True) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("development_root", type=Path)
    parser.add_argument("development_context_root", type=Path)
    parser.add_argument("reserved_root", type=Path)
    parser.add_argument("reserved_context_root", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    report, rows = build_report(
        args.development_root,
        args.development_context_root,
        args.reserved_root,
        args.reserved_context_root,
    )
    write_report(report, rows, args.output)
    print(json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    main()

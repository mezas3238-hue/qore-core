"""Frozen SURFACE_SELECTIVE candidate evaluator for a new non-overlapping holdout.

Candidate selection is CLOSED before this module is evaluated on the reserved
2020-09-17 -> 2022-09-17 provider-native M1 window.

Frozen architecture:
- development contextual model: 2024-09-17 -> 2026-09-17 only;
- contextual position routing: CONTEXT_STABILITY_STAGE;
- causal hazard score exactly as QORE_CAPITALIZER_CAUSAL_ADVERSITY_SURFACE_V4;
- exposure policy exactly SURFACE_SELECTIVE.

No reserved-holdout outcome is allowed to change model cells, hazards, weights,
thresholds, position mode, entry admission, target, MAX3, or sizing policy.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from dataclasses import asdict, dataclass, replace
from decimal import Decimal
from pathlib import Path
from typing import Any

from qore.infrastructure.trader_lab import (
    capitalizer_adaptive_context_risk_governor_v1 as memory,
)
from qore.infrastructure.trader_lab import (
    capitalizer_causal_adversity_surface_v4 as source_surface,
)
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

IDENTITY = "QORE_CAPITALIZER_SURFACE_SELECTIVE_FROZEN_HOLDOUT_V1"
CANDIDATE_IDENTITY = "QORE_CAPITALIZER_SURFACE_SELECTIVE_FROZEN_V1"
SOURCE_SURFACE_SHA = "5f70230013600459f09643736b8725c4396d0cd6"
SOURCE_DIRECT_RUN_ID = 36196002610
SOURCE_CONTEXT_RUN_ID = 36211415438

RESERVED_START = "2020-09-17T00:00:00+00:00"
RESERVED_END = "2022-09-17T00:00:00+00:00"

HAZARD_WEIGHTS = {
    "DD_GE_2": 1,
    "DD_GE_4": 2,
    "DD_GE_5": 2,
    "VOL_EXPANSION": 2,
    "DEST_LT_1R": 1,
    "H1_OPPOSED": 1,
    "M15_OPPOSED": 1,
    "DUAL_OPPOSED": 1,
    "EDGE_ADVERSE_2": 2,
    "EDGE_ADVERSE_3": 1,
}


@dataclass(frozen=True, slots=True)
class FrozenDecision:
    symbol: str
    session: str
    operating_date: str
    entry_at: str
    selected_mode: str
    current_drawdown_r: str
    hazard_score: int
    adverse_votes: int
    risk_multiplier: str
    current_outcome_visible_to_decision: bool = False
    reserved_outcome_visible_to_frozen_model: bool = False


def _load_contexts_reserved(
    root: Path,
) -> dict[tuple[str, str], context.NativeContextRow]:
    paths = sorted(
        root.rglob(
            "capitalizer-*-native-market-context-reserved-v1-rows.jsonl"
        )
    )
    if len(paths) != 9:
        raise ValueError(
            f"frozen holdout requires nine reserved context ledgers, got {len(paths)}"
        )
    result: dict[tuple[str, str], context.NativeContextRow] = {}
    for path in paths:
        with path.open(encoding="utf-8") as handle:
            for line in handle:
                if not line.strip():
                    continue
                row = context.NativeContextRow(**json.loads(line))
                key = (row.symbol, row.entry_at)
                if key in result:
                    raise ValueError("duplicate reserved context identity")
                if (
                    row.bars_after_entry_used
                    or row.unconfirmed_pivot_used
                    or row.outcome_visible_to_context
                ):
                    raise ValueError("reserved context violates causal contract")
                result[key] = row
    return result


def _frozen_hazards(
    *,
    ctx: context.NativeContextRow,
    current_dd: Decimal,
    adverse_votes: int,
) -> tuple[str, ...]:
    result: list[str] = []
    if current_dd >= Decimal("2"):
        result.append("DD_GE_2")
    if current_dd >= Decimal("4"):
        result.append("DD_GE_4")
    if current_dd >= Decimal("5"):
        result.append("DD_GE_5")
    if ctx.volatility_state == "EXPANSION":
        result.append("VOL_EXPANSION")
    if ctx.destination_state == "LT_1R":
        result.append("DEST_LT_1R")
    if ctx.h1_body_alignment == "OPPOSED":
        result.append("H1_OPPOSED")
    if ctx.m15_slope_alignment == "OPPOSED":
        result.append("M15_OPPOSED")
    if (
        ctx.h1_body_alignment == "OPPOSED"
        and ctx.m15_slope_alignment == "OPPOSED"
    ):
        result.append("DUAL_OPPOSED")
    if adverse_votes >= 2:
        result.append("EDGE_ADVERSE_2")
    if adverse_votes >= 3:
        result.append("EDGE_ADVERSE_3")
    return tuple(result)


def _frozen_score(hazards: tuple[str, ...]) -> int:
    return sum(HAZARD_WEIGHTS[item] for item in hazards)


def _frozen_multiplier(
    *,
    current_dd: Decimal,
    score: int,
    adverse_votes: int,
) -> Decimal:
    if current_dd >= Decimal("5") and score >= 7:
        return Decimal("0.20")
    if current_dd >= Decimal("4") and score >= 7:
        return Decimal("0.35")
    if current_dd >= Decimal("3") and score >= 6:
        return Decimal("0.55")
    if adverse_votes >= 3 and score >= 5:
        return Decimal("0.75")
    return Decimal("1")


def _assert_source_equivalence() -> None:
    samples = (
        (Decimal("0"), 0, 0),
        (Decimal("3"), 6, 0),
        (Decimal("4"), 7, 1),
        (Decimal("5"), 7, 1),
        (Decimal("2"), 5, 3),
    )
    dummy = context.NativeContextRow(
        symbol="EURUSD",
        session="LONDON",
        operating_date="2026-01-01",
        side="LONG",
        entry_at="2026-01-01T08:00:00+00:00",
        provenance="FREEZE_ASSERT",
        risk_price="1",
        m15_slope_alignment="ALIGNED",
        h1_body_alignment="ALIGNED",
        volatility_state="NORMAL",
        volatility_ratio="1",
        destination_state="GE_2R",
        destination_room_r="3",
        destination_pivot_confirmed_at="2026-01-01T07:00:00+00:00",
        regime_signature="FREEZE",
        context_signature="FREEZE",
    )
    for dd, score, votes in samples:
        frozen = _frozen_multiplier(
            current_dd=dd,
            score=score,
            adverse_votes=votes,
        )
        source = source_surface._multiplier(
            policy="SURFACE_SELECTIVE",
            ctx=dummy,
            current_dd=dd,
            hazards=(),
            score=score,
            adverse_votes=votes,
        )
        if frozen != source:
            raise ValueError("frozen SURFACE_SELECTIVE drifted from source")


def _simulate_reserved(
    *,
    ledgers: dict[str, tuple[milestone.SimulatedTrade, ...]],
    contexts: dict[tuple[str, str], context.NativeContextRow],
    model: dict[str, Any],
) -> tuple[
    dict[str, Any],
    tuple[FrozenDecision, ...],
    tuple[milestone.SimulatedTrade, ...],
]:
    by_mode = {
        arm: {(row.symbol, row.entry_at): row for row in rows}
        for arm, rows in ledgers.items()
    }
    baseline = ledgers[milestone.ProtectionMode.ORIGINAL.value]
    ordered = tuple(
        sorted(baseline, key=lambda row: (direct._aware(row.entry_at), row.symbol))
    )
    if set((row.symbol, row.entry_at) for row in ordered) != set(contexts):
        raise ValueError("reserved direct/context identities differ")

    chosen: list[milestone.SimulatedTrade] = []
    records: list[memory.MemoryRecord] = []
    decisions: list[FrozenDecision] = []
    multipliers: Counter[str] = Counter()

    for trade in ordered:
        key = (trade.symbol, trade.entry_at)
        ctx = contexts[key]
        history = governor._closed_history(
            tuple(chosen),
            entry_at=direct._aware(trade.entry_at),
        )
        state, _eq, _peak, current_dd, _ls = governor._state(history)
        base_mode, _level, _support = router._lookup(model, ctx)
        final_mode, _overlay = router._overlay(
            policy="CONTEXT_STABILITY_STAGE",
            base_mode=base_mode,
            state=state,
        )
        unscaled = by_mode[final_mode][key]

        causal_memory = memory._closed_records(tuple(records), entry_at=trade.entry_at)
        evidence = memory._evidence(records=causal_memory, ctx=ctx)
        adverse_votes = sum(item.adverse for item in evidence)
        hazards = _frozen_hazards(
            ctx=ctx,
            current_dd=current_dd,
            adverse_votes=adverse_votes,
        )
        score = _frozen_score(hazards)
        multiplier = _frozen_multiplier(
            current_dd=current_dd,
            score=score,
            adverse_votes=adverse_votes,
        )
        scaled = replace(
            unscaled,
            realized_gross_r=str(
                Decimal(unscaled.realized_gross_r) * multiplier
            ),
        )
        chosen.append(scaled)
        records.append(
            memory.MemoryRecord(
                symbol=ctx.symbol,
                session=ctx.session,
                destination_state=ctx.destination_state,
                context_signature=ctx.context_signature,
                exit_at=unscaled.exit_at,
                normalized_realized_r=unscaled.realized_gross_r,
            )
        )
        multipliers[str(multiplier)] += 1
        decisions.append(
            FrozenDecision(
                symbol=trade.symbol,
                session=trade.session,
                operating_date=trade.operating_date,
                entry_at=trade.entry_at,
                selected_mode=final_mode,
                current_drawdown_r=str(current_dd),
                hazard_score=score,
                adverse_votes=adverse_votes,
                risk_multiplier=str(multiplier),
            )
        )

    result = tuple(chosen)
    return {
        "trades": len(result),
        "density_retention": "1",
        "metrics": milestone._metrics(result),
        "multiplier_counts": dict(sorted(multipliers.items())),
    }, tuple(decisions), result


def build_report(
    development_root: Path,
    development_context_root: Path,
    reserved_root: Path,
    reserved_context_root: Path,
) -> tuple[dict[str, Any], tuple[FrozenDecision, ...]]:
    _assert_source_equivalence()

    development = router._load_selected(
        development_root,
        expected=memory.EXPECTED_DEVELOPMENT_TRADES,
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
    counts = {len(rows) for rows in selected_reserved.values()}
    if len(counts) != 1:
        raise ValueError("reserved mode populations differ")
    reserved_context = _load_contexts_reserved(reserved_context_root)
    if len(reserved_context) != next(iter(counts)):
        raise ValueError("reserved context population differs from MAX3")

    result, decisions, _ledger = _simulate_reserved(
        ledgers=selected_reserved,
        contexts=reserved_context,
        model=model,
    )
    control = milestone._metrics(
        selected_reserved[milestone.ProtectionMode.ORIGINAL.value]
    )
    candidate = result["metrics"]

    return {
        "identity": IDENTITY,
        "candidate_identity": CANDIDATE_IDENTITY,
        "source_surface_sha": SOURCE_SURFACE_SHA,
        "source_direct_run_id": SOURCE_DIRECT_RUN_ID,
        "source_context_run_id": SOURCE_CONTEXT_RUN_ID,
        "reserved_window_start": RESERVED_START,
        "reserved_window_end_exclusive": RESERVED_END,
        "reserved_window_role": "FIRST_USE_NONOVERLAPPING_HOLDOUT",
        "reserved_outcomes_visible_to_candidate_selection": False,
        "reserved_outcomes_visible_to_contextual_model": False,
        "reserved_trades": result["trades"],
        "control_metrics": control,
        "candidate": result,
        "pf_improved_vs_reserved_control": (
            Decimal(str(candidate["profit_factor"]))
            > Decimal(str(control["profit_factor"]))
        ),
        "dd_reduced_vs_reserved_control": (
            Decimal(str(candidate["max_drawdown_r"]))
            < Decimal(str(control["max_drawdown_r"]))
        ),
        "total_r_positive": Decimal(str(candidate["total_r"])) > 0,
        "dd_at_or_below_6r": (
            Decimal(str(candidate["max_drawdown_r"])) <= Decimal("6")
        ),
        "density_retention": "1",
        "candidate_architecture_changed_after_holdout_opened": False,
        "all_entries_preserved": True,
        "target_r": "2.00",
        "max3_preserved": True,
        "runtime_rule_selected": False,
        "trader_certified": False,
        "live_authorized": False,
        "real_capital_authorized": False,
        "next_phase": "HOLDOUT_RESULT_DECIDES_STRESS_OR_ARCHITECTURE_REJECTION",
    }, decisions


def write_report(
    report: dict[str, Any],
    decisions: tuple[FrozenDecision, ...],
    output: Path,
) -> None:
    output.mkdir(parents=True, exist_ok=True)
    (output / "capitalizer-surface-selective-frozen-holdout-v1.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    with (
        output / "capitalizer-surface-selective-frozen-holdout-v1-decisions.jsonl"
    ).open("w", encoding="utf-8") as handle:
        for row in decisions:
            handle.write(json.dumps(asdict(row), sort_keys=True) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("development_root", type=Path)
    parser.add_argument("development_context_root", type=Path)
    parser.add_argument("reserved_root", type=Path)
    parser.add_argument("reserved_context_root", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    report, decisions = build_report(
        args.development_root,
        args.development_context_root,
        args.reserved_root,
        args.reserved_context_root,
    )
    write_report(report, decisions, args.output)
    print(json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    main()

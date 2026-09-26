"""Causal adversity-surface governor for Capitalizer.

Combines independent pre-entry hazards into one monotonic exposure surface:
portfolio drawdown, expansion regime, destination room, HTF disagreement and
online context-edge deterioration.  The surface is designed from consumed
forensics and MUST be frozen before a new non-overlapping validation window.

Every valid entry remains executable. Risk automatically restores as the
realized path recovers. No current outcome or unchosen counterfactual is visible
to a decision.
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

IDENTITY = "QORE_CAPITALIZER_CAUSAL_ADVERSITY_SURFACE_V4"
BASE_POLICY = "CONTEXT_STABILITY_STAGE"

POLICIES = (
    "SURFACE_BALANCED",
    "SURFACE_SELECTIVE",
    "SURFACE_CONVEX",
    "EXPANSION_DD",
    "ROOM_EXPANSION_DD",
)


@dataclass(frozen=True, slots=True)
class HazardDecision:
    role: str
    policy: str
    symbol: str
    entry_at: str
    current_drawdown_r: str
    hazard_score: int
    hazards: tuple[str, ...]
    adverse_votes: int
    risk_multiplier: str
    current_outcome_visible_to_decision: bool = False


def _hazards(
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


def _score(hazards: tuple[str, ...]) -> int:
    weights = {
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
    return sum(weights[item] for item in hazards)


def _multiplier(
    *,
    policy: str,
    ctx: context.NativeContextRow,
    current_dd: Decimal,
    hazards: tuple[str, ...],
    score: int,
    adverse_votes: int,
) -> Decimal:
    if policy == "SURFACE_BALANCED":
        if score >= 10:
            return Decimal("0.20")
        if score >= 8:
            return Decimal("0.35")
        if score >= 6:
            return Decimal("0.55")
        if score >= 5:
            return Decimal("0.75")
        return Decimal("1")

    if policy == "SURFACE_SELECTIVE":
        if current_dd >= Decimal("5") and score >= 7:
            return Decimal("0.20")
        if current_dd >= Decimal("4") and score >= 7:
            return Decimal("0.35")
        if current_dd >= Decimal("3") and score >= 6:
            return Decimal("0.55")
        if adverse_votes >= 3 and score >= 5:
            return Decimal("0.75")
        return Decimal("1")

    if policy == "SURFACE_CONVEX":
        if current_dd >= Decimal("5.5"):
            if score >= 7:
                return Decimal("0.10")
            return Decimal("0.50")
        if current_dd >= Decimal("5"):
            return Decimal("0.20") if score >= 6 else Decimal("0.65")
        if current_dd >= Decimal("4"):
            return Decimal("0.35") if score >= 6 else Decimal("0.75")
        if current_dd >= Decimal("3") and score >= 6:
            return Decimal("0.60")
        return Decimal("1")

    if policy == "EXPANSION_DD":
        if ctx.volatility_state != "EXPANSION":
            return Decimal("1")
        if current_dd >= Decimal("5"):
            return Decimal("0.20")
        if current_dd >= Decimal("4"):
            return Decimal("0.40")
        if current_dd >= Decimal("3"):
            return Decimal("0.65")
        return Decimal("1")

    if policy == "ROOM_EXPANSION_DD":
        dangerous = (
            ctx.volatility_state == "EXPANSION"
            and ctx.destination_state == "LT_1R"
        )
        if not dangerous:
            return Decimal("1")
        if current_dd >= Decimal("5"):
            return Decimal("0.20")
        if current_dd >= Decimal("4"):
            return Decimal("0.40")
        if current_dd >= Decimal("3"):
            return Decimal("0.60")
        if adverse_votes >= 2:
            return Decimal("0.75")
        return Decimal("1")

    raise ValueError(f"unknown adversity surface policy: {policy}")


def _simulate(
    *,
    role: str,
    policy: str,
    ledgers: dict[str, tuple[milestone.SimulatedTrade, ...]],
    contexts: dict[tuple[str, str], context.NativeContextRow],
    model: dict[str, Any],
) -> tuple[dict[str, Any], tuple[HazardDecision, ...]]:
    by_mode = {
        arm: {(row.symbol, row.entry_at): row for row in rows}
        for arm, rows in ledgers.items()
    }
    baseline = ledgers[milestone.ProtectionMode.ORIGINAL.value]
    ordered = tuple(
        sorted(baseline, key=lambda row: (direct._aware(row.entry_at), row.symbol))
    )

    chosen_scaled: list[milestone.SimulatedTrade] = []
    records: list[memory.MemoryRecord] = []
    decisions: list[HazardDecision] = []
    multiplier_counts: Counter[str] = Counter()
    hazard_counts: Counter[str] = Counter()

    for trade in ordered:
        key = (trade.symbol, trade.entry_at)
        ctx = contexts[key]
        history = governor._closed_history(
            tuple(chosen_scaled),
            entry_at=direct._aware(trade.entry_at),
        )
        state, _eq, _peak, current_dd, _ls = governor._state(history)
        base_mode, _level, _support = router._lookup(model, ctx)
        final_mode, _overlay = router._overlay(
            policy=BASE_POLICY,
            base_mode=base_mode,
            state=state,
        )
        unscaled = by_mode[final_mode][key]

        causal_memory = memory._closed_records(tuple(records), entry_at=trade.entry_at)
        evidence = memory._evidence(records=causal_memory, ctx=ctx)
        adverse_votes = sum(item.adverse for item in evidence)
        hazards = _hazards(
            ctx=ctx,
            current_dd=current_dd,
            adverse_votes=adverse_votes,
        )
        score = _score(hazards)
        multiplier = _multiplier(
            policy=policy,
            ctx=ctx,
            current_dd=current_dd,
            hazards=hazards,
            score=score,
            adverse_votes=adverse_votes,
        )
        scaled = replace(
            unscaled,
            realized_gross_r=str(Decimal(unscaled.realized_gross_r) * multiplier),
        )
        chosen_scaled.append(scaled)
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
        multiplier_counts[str(multiplier)] += 1
        for hazard in hazards:
            hazard_counts[hazard] += 1
        decisions.append(
            HazardDecision(
                role=role,
                policy=policy,
                symbol=trade.symbol,
                entry_at=trade.entry_at,
                current_drawdown_r=str(current_dd),
                hazard_score=score,
                hazards=hazards,
                adverse_votes=adverse_votes,
                risk_multiplier=str(multiplier),
            )
        )

    result = tuple(chosen_scaled)
    return {
        "role": role,
        "policy": policy,
        "trades": len(result),
        "density_retention": "1",
        "metrics": milestone._metrics(result),
        "multiplier_counts": dict(sorted(multiplier_counts.items())),
        "hazard_counts": dict(sorted(hazard_counts.items())),
    }, tuple(decisions)


def build_report(
    development_root: Path,
    validation_root: Path,
    context_root: Path,
) -> tuple[dict[str, Any], tuple[HazardDecision, ...]]:
    development = router._load_selected(
        development_root,
        expected=memory.EXPECTED_DEVELOPMENT_TRADES,
    )
    validation = router._load_selected(
        validation_root,
        expected=memory.EXPECTED_VALIDATION_TRADES,
    )
    dev_context = router._load_contexts(context_root, role="dev")
    val_context = router._load_contexts(context_root, role="holdout")
    model = router._freeze_model(development=development, contexts=dev_context)

    control_dev, _ = router._simulate(
        role="DEV_CONTROL",
        policy=BASE_POLICY,
        ledgers=development,
        contexts=dev_context,
        model=model,
    )
    control_val, _ = router._simulate(
        role="VAL_CONTROL",
        policy=BASE_POLICY,
        ledgers=validation,
        contexts=val_context,
        model=model,
    )

    results: list[dict[str, Any]] = []
    audits: list[HazardDecision] = []
    for policy in POLICIES:
        dev, da = _simulate(
            role="DEVELOPMENT",
            policy=policy,
            ledgers=development,
            contexts=dev_context,
            model=model,
        )
        val, va = _simulate(
            role="CONSUMED_VALIDATION_2022_2024",
            policy=policy,
            ledgers=validation,
            contexts=val_context,
            model=model,
        )
        for current, control in ((dev, control_dev), (val, control_val)):
            m, c = current["metrics"], control["metrics"]
            current["pf_at_least_contextual_control"] = (
                Decimal(str(m["profit_factor"])) >= Decimal(str(c["profit_factor"]))
            )
            current["dd_below_contextual_control"] = (
                Decimal(str(m["max_drawdown_r"])) < Decimal(str(c["max_drawdown_r"]))
            )
            current["dd_at_or_below_6r"] = (
                Decimal(str(m["max_drawdown_r"])) <= Decimal("6")
            )
            current["total_r_retention"] = str(
                Decimal(str(m["total_r"])) / Decimal(str(c["total_r"]))
            )
        results.append({"policy": policy, "development": dev, "validation": val})
        audits.extend(da)
        audits.extend(va)

    robust = tuple(
        row for row in results
        if row["development"]["pf_at_least_contextual_control"]
        and row["development"]["dd_below_contextual_control"]
        and row["validation"]["pf_at_least_contextual_control"]
        and row["validation"]["dd_below_contextual_control"]
    )
    dd6 = tuple(
        row for row in robust
        if row["development"]["dd_at_or_below_6r"]
        and row["validation"]["dd_at_or_below_6r"]
    )

    return {
        "identity": IDENTITY,
        "development_trades": memory.EXPECTED_DEVELOPMENT_TRADES,
        "validation_trades": memory.EXPECTED_VALIDATION_TRADES,
        "policy_count": len(POLICIES),
        "results": results,
        "robust_pf_up_dd_down_policy_count": len(robust),
        "robust_both_windows_dd6_policy_count": len(dd6),
        "all_entries_preserved": True,
        "hazards_known_before_current_outcome": True,
        "current_outcome_visible_to_decision": False,
        "validation_is_fresh_holdout": False,
        "new_holdout_reserved": "2020-09-17_TO_2022-09-17",
        "runtime_rule_selected": False,
        "trader_certified": False,
        "live_authorized": False,
        "real_capital_authorized": False,
        "next_phase": (
            "FREEZE_ADVERSITY_SURFACE_AND_RUN_RESERVED_HOLDOUT"
            if robust
            else "BUILD_CONTINUOUS_EXPECTANCY_WEIGHTED_EXPOSURE"
        ),
    }, tuple(audits)


def write_report(
    report: dict[str, Any],
    audits: tuple[HazardDecision, ...],
    output: Path,
) -> None:
    output.mkdir(parents=True, exist_ok=True)
    (output / "capitalizer-causal-adversity-surface-v4.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    with (
        output / "capitalizer-causal-adversity-surface-v4-decisions.jsonl"
    ).open("w", encoding="utf-8") as handle:
        for row in audits:
            handle.write(json.dumps(asdict(row), sort_keys=True) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("development_root", type=Path)
    parser.add_argument("validation_root", type=Path)
    parser.add_argument("context_root", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    report, audits = build_report(
        args.development_root,
        args.validation_root,
        args.context_root,
    )
    write_report(report, audits, args.output)
    print(json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    main()

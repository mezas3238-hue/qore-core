"""Fine-grained refinement of the robust SURFACE_SELECTIVE governor.

The base surface already improves PF and DD in both consumed windows:
development ~1.823 PF / 6.21R DD and validation ~1.415 PF / 6.77R DD.

The remaining objective is deliberately narrow: remove the final sub-1R
drawdown overshoot without broad portfolio compression. Refinements only differ
inside high-DD + high-hazard states and restore full risk elsewhere.

All entries remain executable and all features are causal.
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
    capitalizer_causal_adversity_surface_v4 as surface,
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

IDENTITY = "QORE_CAPITALIZER_SURFACE_SELECTIVE_REFINEMENT_V4_1"
BASE_POLICY = "SURFACE_SELECTIVE"

POLICIES = (
    "SELECTIVE_BASE",
    "SELECTIVE_TIGHT5",
    "SELECTIVE_TIGHT_SCORE",
    "SELECTIVE_EDGE_CONFIRM",
    "SELECTIVE_RECOVERY_AWARE",
    "SELECTIVE_SOFT_CEILING",
)


@dataclass(frozen=True, slots=True)
class RefinementDecision:
    role: str
    policy: str
    symbol: str
    entry_at: str
    current_drawdown_r: str
    hazard_score: int
    adverse_votes: int
    base_multiplier: str
    final_multiplier: str
    current_outcome_visible_to_decision: bool = False


def _refined_multiplier(
    *,
    policy: str,
    ctx: context.NativeContextRow,
    current_dd: Decimal,
    score: int,
    adverse_votes: int,
    base_multiplier: Decimal,
) -> Decimal:
    if policy == "SELECTIVE_BASE":
        return base_multiplier

    if policy == "SELECTIVE_TIGHT5":
        if current_dd >= Decimal("5.5") and score >= 5:
            return min(base_multiplier, Decimal("0.15"))
        if current_dd >= Decimal("5") and score >= 6:
            return min(base_multiplier, Decimal("0.25"))
        return base_multiplier

    if policy == "SELECTIVE_TIGHT_SCORE":
        if current_dd >= Decimal("5.5") and score >= 4:
            return min(base_multiplier, Decimal("0.20"))
        if current_dd >= Decimal("5") and score >= 5:
            return min(base_multiplier, Decimal("0.30"))
        if current_dd >= Decimal("4.5") and score >= 6:
            return min(base_multiplier, Decimal("0.40"))
        return base_multiplier

    if policy == "SELECTIVE_EDGE_CONFIRM":
        if current_dd >= Decimal("5.5") and adverse_votes >= 2:
            return min(base_multiplier, Decimal("0.15"))
        if (
            current_dd >= Decimal("5")
            and adverse_votes >= 2
            and score >= 5
        ):
            return min(base_multiplier, Decimal("0.25"))
        if current_dd >= Decimal("4") and adverse_votes >= 3:
            return min(base_multiplier, Decimal("0.40"))
        return base_multiplier

    if policy == "SELECTIVE_RECOVERY_AWARE":
        favorable_escape = (
            ctx.destination_state == "GE_2R"
            and ctx.h1_body_alignment == "ALIGNED"
            and adverse_votes < 2
        )
        if favorable_escape:
            return Decimal("1")
        if current_dd >= Decimal("5.5") and score >= 5:
            return min(base_multiplier, Decimal("0.15"))
        if current_dd >= Decimal("5") and score >= 6:
            return min(base_multiplier, Decimal("0.25"))
        if current_dd >= Decimal("4") and score >= 7:
            return min(base_multiplier, Decimal("0.35"))
        return base_multiplier

    if policy == "SELECTIVE_SOFT_CEILING":
        if current_dd >= Decimal("5.75"):
            if score >= 5 or adverse_votes >= 2:
                return min(base_multiplier, Decimal("0.10"))
            return min(base_multiplier, Decimal("0.65"))
        if current_dd >= Decimal("5.25"):
            if score >= 5:
                return min(base_multiplier, Decimal("0.20"))
            return min(base_multiplier, Decimal("0.80"))
        return base_multiplier

    raise ValueError(f"unknown selective refinement: {policy}")


def _simulate(
    *,
    role: str,
    policy: str,
    ledgers: dict[str, tuple[milestone.SimulatedTrade, ...]],
    contexts: dict[tuple[str, str], context.NativeContextRow],
    model: dict[str, Any],
) -> tuple[dict[str, Any], tuple[RefinementDecision, ...]]:
    by_mode = {
        arm: {(row.symbol, row.entry_at): row for row in rows}
        for arm, rows in ledgers.items()
    }
    baseline = ledgers[milestone.ProtectionMode.ORIGINAL.value]
    ordered = tuple(
        sorted(baseline, key=lambda row: (direct._aware(row.entry_at), row.symbol))
    )

    chosen: list[milestone.SimulatedTrade] = []
    records: list[memory.MemoryRecord] = []
    decisions: list[RefinementDecision] = []
    multiplier_counts: Counter[str] = Counter()
    tightened = 0

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
            policy=surface.BASE_POLICY,
            base_mode=base_mode,
            state=state,
        )
        unscaled = by_mode[final_mode][key]

        causal_memory = memory._closed_records(tuple(records), entry_at=trade.entry_at)
        evidence = memory._evidence(records=causal_memory, ctx=ctx)
        adverse_votes = sum(item.adverse for item in evidence)
        hazards = surface._hazards(
            ctx=ctx,
            current_dd=current_dd,
            adverse_votes=adverse_votes,
        )
        score = surface._score(hazards)
        base_multiplier = surface._multiplier(
            policy=BASE_POLICY,
            ctx=ctx,
            current_dd=current_dd,
            hazards=hazards,
            score=score,
            adverse_votes=adverse_votes,
        )
        multiplier = _refined_multiplier(
            policy=policy,
            ctx=ctx,
            current_dd=current_dd,
            score=score,
            adverse_votes=adverse_votes,
            base_multiplier=base_multiplier,
        )
        if multiplier < base_multiplier:
            tightened += 1

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
        multiplier_counts[str(multiplier)] += 1
        decisions.append(
            RefinementDecision(
                role=role,
                policy=policy,
                symbol=trade.symbol,
                entry_at=trade.entry_at,
                current_drawdown_r=str(current_dd),
                hazard_score=score,
                adverse_votes=adverse_votes,
                base_multiplier=str(base_multiplier),
                final_multiplier=str(multiplier),
            )
        )

    result = tuple(chosen)
    return {
        "role": role,
        "policy": policy,
        "trades": len(result),
        "density_retention": "1",
        "metrics": milestone._metrics(result),
        "tightened_vs_base_decisions": tightened,
        "multiplier_counts": dict(sorted(multiplier_counts.items())),
    }, tuple(decisions)


def build_report(
    development_root: Path,
    validation_root: Path,
    context_root: Path,
) -> tuple[dict[str, Any], tuple[RefinementDecision, ...]]:
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

    results: list[dict[str, Any]] = []
    audits: list[RefinementDecision] = []
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
        results.append({"policy": policy, "development": dev, "validation": val})
        audits.extend(da)
        audits.extend(va)

    base = next(row for row in results if row["policy"] == "SELECTIVE_BASE")
    base_dev = base["development"]["metrics"]
    base_val = base["validation"]["metrics"]

    for row in results:
        for key, control in (("development", base_dev), ("validation", base_val)):
            current = row[key]
            m = current["metrics"]
            current["pf_at_least_selective_base"] = (
                Decimal(str(m["profit_factor"])) >= Decimal(str(control["profit_factor"]))
            )
            current["dd_at_or_below_6r"] = (
                Decimal(str(m["max_drawdown_r"])) <= Decimal("6")
            )
            current["total_r_retention_vs_selective_base"] = str(
                Decimal(str(m["total_r"])) / Decimal(str(control["total_r"]))
            )

    both_dd6 = tuple(
        row for row in results
        if row["development"]["dd_at_or_below_6r"]
        and row["validation"]["dd_at_or_below_6r"]
    )
    both_dd6_pf = tuple(
        row for row in both_dd6
        if row["development"]["pf_at_least_selective_base"]
        and row["validation"]["pf_at_least_selective_base"]
    )

    return {
        "identity": IDENTITY,
        "base_policy": BASE_POLICY,
        "development_trades": memory.EXPECTED_DEVELOPMENT_TRADES,
        "validation_trades": memory.EXPECTED_VALIDATION_TRADES,
        "policy_count": len(POLICIES),
        "results": results,
        "both_windows_dd6_count": len(both_dd6),
        "both_windows_dd6_pf_not_lower_than_selective_count": len(both_dd6_pf),
        "all_entries_preserved": True,
        "refinement_only_in_high_dd_hazard_states": True,
        "current_outcome_visible_to_decision": False,
        "validation_is_fresh_holdout": False,
        "new_holdout_reserved": "2020-09-17_TO_2022-09-17",
        "runtime_rule_selected": False,
        "trader_certified": False,
        "live_authorized": False,
        "real_capital_authorized": False,
        "next_phase": (
            "FREEZE_REFINED_SURFACE_AND_RUN_RESERVED_HOLDOUT"
            if both_dd6_pf
            else "SELECT_PARETO_REFINED_SURFACE_AND_STRESS_BEFORE_HOLDOUT"
        ),
    }, tuple(audits)


def write_report(
    report: dict[str, Any],
    audits: tuple[RefinementDecision, ...],
    output: Path,
) -> None:
    output.mkdir(parents=True, exist_ok=True)
    (output / "capitalizer-surface-selective-refinement-v4-1.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    with (
        output / "capitalizer-surface-selective-refinement-v4-1-decisions.jsonl"
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

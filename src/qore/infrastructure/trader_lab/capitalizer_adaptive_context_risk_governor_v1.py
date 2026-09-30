"""Adaptive causal context-risk governor for Capitalizer.

Static risk compression improved validation PF/DD but hurt development PF because
the same destination state changes quality across regimes. This engine therefore
learns context quality online from ONLY trades that were already closed before
the current entry.

It preserves:
- every trade admission;
- frozen contextual milestone routing;
- fixed 2R runner target;
- MAX3.

The governor stores normalized outcome R of the ACTUALLY chosen protection path,
then forms hierarchical posterior evidence at four causal scopes:
exact symbol+context, symbol+destination, session+destination, global destination.
Risk is compressed only when multiple independent scopes agree that the current
context has deteriorated.

No unchosen counterfactual outcome is used by the memory.
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
    capitalizer_contextual_stability_router_2r_v1 as router,
)
from qore.infrastructure.trader_lab import (
    capitalizer_cross_market_stability_governor_2r_v1 as governor,
)
from qore.infrastructure.trader_lab import (
    capitalizer_max_recovery_direct_m1_replay_v1 as direct,
)
from qore.infrastructure.trader_lab import capitalizer_native_market_context_v1 as context

IDENTITY = "QORE_CAPITALIZER_ADAPTIVE_CONTEXT_RISK_GOVERNOR_V1"
BASE_POLICY = "CONTEXT_STABILITY_STAGE"
EXPECTED_DEVELOPMENT_TRADES = 948
EXPECTED_VALIDATION_TRADES = 1034

PRIOR_STRENGTH = Decimal("6")
RECENT_LIMIT = 12

POLICIES = (
    "ADAPTIVE_CONSERVATIVE",
    "ADAPTIVE_CONSENSUS",
    "ADAPTIVE_DEFENSIVE_ONLY",
    "ADAPTIVE_SEVERE_ONLY",
)


@dataclass(frozen=True, slots=True)
class MemoryRecord:
    symbol: str
    session: str
    destination_state: str
    context_signature: str
    exit_at: str
    normalized_realized_r: str


@dataclass(frozen=True, slots=True)
class ScopeEvidence:
    scope: str
    support: int
    posterior_mean_r: str | None
    posterior_negative_rate: str | None
    adverse: bool
    severe: bool


@dataclass(frozen=True, slots=True)
class AdaptiveDecision:
    role: str
    policy: str
    symbol: str
    session: str
    operating_date: str
    entry_at: str
    stability_state: str
    destination_state: str
    context_signature: str
    selected_mode: str
    adverse_votes: int
    severe_votes: int
    risk_multiplier: str
    scope_evidence: tuple[ScopeEvidence, ...]
    current_outcome_visible_to_decision: bool = False
    unchosen_counterfactual_visible_to_memory: bool = False


def _scope_specs(
    ctx: context.NativeContextRow,
) -> tuple[tuple[str, tuple[str, ...], int], ...]:
    return (
        ("EXACT", (ctx.symbol, ctx.context_signature), 5),
        ("SYMBOL_DEST", (ctx.symbol, ctx.destination_state), 8),
        ("SESSION_DEST", (ctx.session, ctx.destination_state), 12),
        ("GLOBAL_DEST", (ctx.destination_state,), 20),
    )


def _matches(
    record: MemoryRecord,
    *,
    scope: str,
    values: tuple[str, ...],
) -> bool:
    if scope == "EXACT":
        return (record.symbol, record.context_signature) == values
    if scope == "SYMBOL_DEST":
        return (record.symbol, record.destination_state) == values
    if scope == "SESSION_DEST":
        return (record.session, record.destination_state) == values
    if scope == "GLOBAL_DEST":
        return (record.destination_state,) == values
    raise ValueError(f"unknown adaptive scope: {scope}")


def _global_stats(
    records: tuple[MemoryRecord, ...],
) -> tuple[Decimal, Decimal]:
    if not records:
        return Decimal("0"), Decimal("0.5")
    values = tuple(Decimal(row.normalized_realized_r) for row in records)
    mean_r = sum(values, Decimal("0")) / Decimal(len(values))
    negative_rate = Decimal(sum(value < 0 for value in values)) / Decimal(len(values))
    return mean_r, negative_rate


def _evidence(
    *,
    records: tuple[MemoryRecord, ...],
    ctx: context.NativeContextRow,
) -> tuple[ScopeEvidence, ...]:
    global_mean, global_negative = _global_stats(records)
    result: list[ScopeEvidence] = []
    for scope, values, minimum in _scope_specs(ctx):
        matches = tuple(
            row for row in records
            if _matches(row, scope=scope, values=values)
        )[-RECENT_LIMIT:]
        support = len(matches)
        if support < minimum:
            result.append(
                ScopeEvidence(
                    scope=scope,
                    support=support,
                    posterior_mean_r=None,
                    posterior_negative_rate=None,
                    adverse=False,
                    severe=False,
                )
            )
            continue
        values_r = tuple(Decimal(row.normalized_realized_r) for row in matches)
        negatives = sum(value < 0 for value in values_r)
        denom = PRIOR_STRENGTH + Decimal(support)
        posterior_mean = (
            PRIOR_STRENGTH * global_mean
            + sum(values_r, Decimal("0"))
        ) / denom
        posterior_negative = (
            PRIOR_STRENGTH * global_negative
            + Decimal(negatives)
        ) / denom
        adverse = posterior_mean < 0 and posterior_negative > global_negative
        severe = (
            posterior_mean <= Decimal("-0.15")
            and posterior_negative >= Decimal("0.60")
        )
        result.append(
            ScopeEvidence(
                scope=scope,
                support=support,
                posterior_mean_r=str(posterior_mean),
                posterior_negative_rate=str(posterior_negative),
                adverse=adverse,
                severe=severe,
            )
        )
    return tuple(result)


def _risk_multiplier(
    *,
    policy: str,
    state: governor.StabilityState,
    adverse_votes: int,
    severe_votes: int,
) -> Decimal:
    if policy == "ADAPTIVE_CONSERVATIVE":
        if severe_votes >= 2 and state is governor.StabilityState.DEFENSIVE:
            return Decimal("0.55")
        if adverse_votes >= 3:
            return Decimal("0.70")
        return Decimal("1")
    if policy == "ADAPTIVE_CONSENSUS":
        if severe_votes >= 2 and state is governor.StabilityState.DEFENSIVE:
            return Decimal("0.35")
        if adverse_votes >= 3:
            return Decimal("0.50")
        if adverse_votes >= 2:
            return Decimal("0.65")
        return Decimal("1")
    if policy == "ADAPTIVE_DEFENSIVE_ONLY":
        if state is governor.StabilityState.DEFENSIVE and adverse_votes >= 2:
            return Decimal("0.50")
        return Decimal("1")
    if policy == "ADAPTIVE_SEVERE_ONLY":
        if state is governor.StabilityState.DEFENSIVE and severe_votes >= 2:
            return Decimal("0.40")
        return Decimal("1")
    raise ValueError(f"unknown adaptive risk policy: {policy}")


def _closed_records(
    records: tuple[MemoryRecord, ...],
    *,
    entry_at: str,
) -> tuple[MemoryRecord, ...]:
    current = direct._aware(entry_at)
    return tuple(
        row for row in records
        if direct._aware(row.exit_at) <= current
    )


def _simulate(
    *,
    role: str,
    policy: str,
    ledgers: dict[str, tuple[milestone.SimulatedTrade, ...]],
    contexts: dict[tuple[str, str], context.NativeContextRow],
    model: dict[str, Any],
) -> tuple[dict[str, Any], tuple[AdaptiveDecision, ...]]:
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

    chosen_scaled: list[milestone.SimulatedTrade] = []
    memory: list[MemoryRecord] = []
    decisions: list[AdaptiveDecision] = []
    multiplier_counts: dict[str, int] = defaultdict(int)
    vote_counts: dict[str, int] = defaultdict(int)

    for trade in ordered:
        key = (trade.symbol, trade.entry_at)
        ctx = contexts[key]
        closed_scaled = governor._closed_history(
            tuple(chosen_scaled),
            entry_at=direct._aware(trade.entry_at),
        )
        state, _eq, _pk, _dd, _ls = governor._state(closed_scaled)
        base_mode, _level, _support = router._lookup(model, ctx)
        final_mode, _overlay = router._overlay(
            policy=BASE_POLICY,
            base_mode=base_mode,
            state=state,
        )
        unscaled = by_mode[final_mode][key]

        causal_memory = _closed_records(tuple(memory), entry_at=trade.entry_at)
        evidence = _evidence(records=causal_memory, ctx=ctx)
        adverse_votes = sum(item.adverse for item in evidence)
        severe_votes = sum(item.severe for item in evidence)
        multiplier = _risk_multiplier(
            policy=policy,
            state=state,
            adverse_votes=adverse_votes,
            severe_votes=severe_votes,
        )
        scaled = replace(
            unscaled,
            realized_gross_r=str(
                Decimal(unscaled.realized_gross_r) * multiplier
            ),
        )
        chosen_scaled.append(scaled)
        memory.append(
            MemoryRecord(
                symbol=ctx.symbol,
                session=ctx.session,
                destination_state=ctx.destination_state,
                context_signature=ctx.context_signature,
                exit_at=unscaled.exit_at,
                normalized_realized_r=unscaled.realized_gross_r,
            )
        )
        multiplier_counts[str(multiplier)] += 1
        vote_counts[f"ADV={adverse_votes}|SEV={severe_votes}"] += 1
        decisions.append(
            AdaptiveDecision(
                role=role,
                policy=policy,
                symbol=trade.symbol,
                session=trade.session,
                operating_date=trade.operating_date,
                entry_at=trade.entry_at,
                stability_state=state.value,
                destination_state=ctx.destination_state,
                context_signature=ctx.context_signature,
                selected_mode=final_mode,
                adverse_votes=adverse_votes,
                severe_votes=severe_votes,
                risk_multiplier=str(multiplier),
                scope_evidence=evidence,
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
        "vote_counts": dict(sorted(vote_counts.items())),
    }, tuple(decisions)


def build_report(
    development_root: Path,
    validation_root: Path,
    context_root: Path,
) -> tuple[dict[str, Any], tuple[AdaptiveDecision, ...]]:
    development = router._load_selected(
        development_root,
        expected=EXPECTED_DEVELOPMENT_TRADES,
    )
    validation = router._load_selected(
        validation_root,
        expected=EXPECTED_VALIDATION_TRADES,
    )
    dev_context = router._load_contexts(context_root, role="dev")
    val_context = router._load_contexts(context_root, role="holdout")
    model = router._freeze_model(
        development=development,
        contexts=dev_context,
    )

    control_dev, _ = router._simulate(
        role="DEVELOPMENT_CONTROL",
        policy=BASE_POLICY,
        ledgers=development,
        contexts=dev_context,
        model=model,
    )
    control_val, _ = router._simulate(
        role="VALIDATION_CONTROL",
        policy=BASE_POLICY,
        ledgers=validation,
        contexts=val_context,
        model=model,
    )

    results: list[dict[str, Any]] = []
    audits: list[AdaptiveDecision] = []
    for policy in POLICIES:
        dev, dev_audit = _simulate(
            role="DEVELOPMENT",
            policy=policy,
            ledgers=development,
            contexts=dev_context,
            model=model,
        )
        val, val_audit = _simulate(
            role="CONSUMED_VALIDATION_2022_2024",
            policy=policy,
            ledgers=validation,
            contexts=val_context,
            model=model,
        )
        for current, control in ((dev, control_dev), (val, control_val)):
            metrics = current["metrics"]
            control_metrics = control["metrics"]
            current["pf_at_least_contextual_control"] = (
                metrics["profit_factor"] is not None
                and control_metrics["profit_factor"] is not None
                and Decimal(str(metrics["profit_factor"]))
                >= Decimal(str(control_metrics["profit_factor"]))
            )
            current["dd_below_contextual_control"] = (
                Decimal(str(metrics["max_drawdown_r"]))
                < Decimal(str(control_metrics["max_drawdown_r"]))
            )
            current["total_r_retention"] = str(
                Decimal(str(metrics["total_r"]))
                / Decimal(str(control_metrics["total_r"]))
            )
            current["dd_at_or_below_6r"] = (
                Decimal(str(metrics["max_drawdown_r"])) <= Decimal("6")
            )
        results.append(
            {
                "policy": policy,
                "development": dev,
                "validation": val,
            }
        )
        audits.extend(dev_audit)
        audits.extend(val_audit)

    robust = tuple(
        row for row in results
        if row["development"]["pf_at_least_contextual_control"]
        and row["development"]["dd_below_contextual_control"]
        and row["validation"]["pf_at_least_contextual_control"]
        and row["validation"]["dd_below_contextual_control"]
    )

    return {
        "identity": IDENTITY,
        "base_policy": BASE_POLICY,
        "development_role": "CONSUMED_RESEARCH_2024_2026",
        "validation_role": "CONSUMED_VALIDATION_2022_2024",
        "validation_is_fresh_holdout": False,
        "development_trades": EXPECTED_DEVELOPMENT_TRADES,
        "validation_trades": EXPECTED_VALIDATION_TRADES,
        "policy_count": len(POLICIES),
        "results": results,
        "robust_pf_up_dd_down_policy_count": len(robust),
        "prior_closed_chosen_outcomes_only": True,
        "normalized_memory_uses_chosen_mode_only": True,
        "unchosen_counterfactual_visible_to_memory": False,
        "current_outcome_visible_to_decision": False,
        "all_entries_preserved": True,
        "new_nonoverlapping_holdout_required": True,
        "runtime_rule_selected": False,
        "trader_certified": False,
        "live_authorized": False,
        "real_capital_authorized": False,
        "next_phase": (
            "FREEZE_ADAPTIVE_GOVERNOR_AND_OPEN_NEW_HOLDOUT"
            if robust
            else "EXPAND_CAUSAL_EDGE_MEMORY_WITH_CROSS_MARKET_FACTOR_STATE"
        ),
    }, tuple(audits)


def write_report(
    report: dict[str, Any],
    audits: tuple[AdaptiveDecision, ...],
    output: Path,
) -> None:
    output.mkdir(parents=True, exist_ok=True)
    (output / "capitalizer-adaptive-context-risk-governor-v1.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    with (
        output / "capitalizer-adaptive-context-risk-governor-v1-decisions.jsonl"
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

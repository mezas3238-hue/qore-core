"""Causal drawdown-path budget for Capitalizer.

V13 showed that one-shot failure memory can improve parts of the path but does
not generalize the <=6R acceptance envelope. V14 targets a different mechanism:
admission risk created by the combination of CLOSED drawdown, still-OPEN prior
risk, loss-pressure and same-factor alignment.

The budget is not cosmetic position scaling. Existing Surface multipliers are
preserved. V14 either keeps the trade unchanged or abstains when BOTH:
1. prospective path risk exceeds a predeclared budget, and
2. causal conflict is present in evidence available before entry.

Blocked trades never update memory and their counterfactual outcomes are never
used. This remains a selected-ledger diagnostic; full source recompetition is
mandatory before any candidate freeze.
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
    capitalizer_causal_loss_pressure_surface_v7 as pressure_v7,
)
from qore.infrastructure.trader_lab import (
    capitalizer_causal_probe_ranker_v10 as v10,
)
from qore.infrastructure.trader_lab import (
    capitalizer_cognitive_r_milestone_protection_2r_v1 as milestone,
)
from qore.infrastructure.trader_lab import capitalizer_exposure_graph as exposure
from qore.infrastructure.trader_lab import (
    capitalizer_factor_journey_probe_ranker_v11 as v11,
)
from qore.infrastructure.trader_lab import (
    capitalizer_max_recovery_direct_m1_replay_v1 as direct,
)
from qore.infrastructure.trader_lab import (
    capitalizer_sequence_failure_memory_abstention_v13 as v13,
)

IDENTITY = "QORE_CAPITALIZER_DRAWDOWN_PATH_CAUSAL_BUDGET_V14"
MIN_DENSITY_RETENTION = Decimal("0.90")

POLICY_SPECS: dict[str, tuple[Decimal, int, bool]] = {
    "BUDGET600_C2": (Decimal("6.00"), 2, False),
    "BUDGET600_C3": (Decimal("6.00"), 3, False),
    "BUDGET575_C2": (Decimal("5.75"), 2, False),
    "BUDGET575_C3": (Decimal("5.75"), 3, False),
    "BUDGET600_C2_RECOVERY": (Decimal("6.00"), 2, True),
    "BUDGET575_C2_RECOVERY": (Decimal("5.75"), 2, True),
}
POLICIES = ("SURFACE_CONTROL", *POLICY_SPECS)


@dataclass(frozen=True, slots=True)
class OpenRisk:
    symbol: str
    side: str
    entry_at: str
    exit_at: str
    risk_r: Decimal


@dataclass(frozen=True, slots=True)
class BudgetDecision:
    period: str
    policy: str
    symbol: str
    session: str
    entry_at: str
    current_drawdown_r: str
    active_risk_r: str
    shared_factor_r: str
    aligned_factor_r: str
    opposed_factor_r: str
    base_multiplier: str
    projected_path_r: str
    adverse_votes: int
    severe_votes: int
    favorable_votes: int
    pressure_flags: tuple[str, ...]
    conflict_score: int
    recovery_evidence: bool
    abstain: bool
    reason: str
    current_outcome_visible_to_decision: bool = False
    open_trade_outcomes_visible_to_decision: bool = False
    blocked_outcome_visible_to_memory: bool = False


def _active(
    rows: tuple[OpenRisk, ...],
    *,
    entry_at: str,
) -> tuple[OpenRisk, ...]:
    now = direct._aware(entry_at)
    return tuple(
        row
        for row in rows
        if direct._aware(row.entry_at) < now < direct._aware(row.exit_at)
    )


def _factor_summary(
    rows: tuple[OpenRisk, ...],
    *,
    trade: milestone.SimulatedTrade,
) -> tuple[Decimal, Decimal, Decimal, Decimal]:
    active = _active(rows, entry_at=trade.entry_at)
    positions = tuple(
        exposure.CapitalizerExposurePosition(
            symbol=row.symbol,
            side=exposure.CapitalizerSide(row.side),
            risk_r=row.risk_r,
        )
        for row in active
    )
    aggregate = {
        row.factor: row
        for row in exposure.factor_exposures(positions)
    }
    candidate = v11._factor_map(symbol=trade.symbol, side=trade.side)
    active_risk = sum((row.risk_r for row in active), Decimal("0"))
    shared_gross = Decimal("0")
    aligned = Decimal("0")
    opposed = Decimal("0")
    for factor, current in candidate.items():
        prior = aggregate.get(factor)
        if prior is None:
            continue
        shared_gross += prior.gross_r
        product = current.net_r * prior.net_r
        if product > 0:
            aligned += abs(prior.net_r)
        elif product < 0:
            opposed += abs(prior.net_r)
    return active_risk, shared_gross, aligned, opposed


def _causal_state(
    *,
    records: tuple[memory.MemoryRecord, ...],
    pre: v10.Pretrade,
    session: str,
) -> tuple[int, int, int, pressure_v7.PressureState, bool]:
    causal = memory._closed_records(records, entry_at=pre.point.entry_at)
    evidence = memory._evidence(records=causal, ctx=pre.ctx)
    adverse = sum(item.adverse for item in evidence)
    severe = sum(item.severe for item in evidence)
    favorable = sum(
        item.posterior_mean_r is not None
        and Decimal(item.posterior_mean_r) > 0
        and item.posterior_negative_rate is not None
        and Decimal(item.posterior_negative_rate) < Decimal("0.50")
        for item in evidence
    )
    pressure = pressure_v7._pressure(causal, session=session)
    recent = causal[-3:]
    recent_sum = sum(
        (Decimal(row.normalized_realized_r) for row in recent),
        Decimal("0"),
    )
    recovery = (
        favorable >= 2
        and recent_sum > 0
        and not pressure.global_severe
        and not pressure.session_shock
    )
    return adverse, severe, favorable, pressure, recovery


def _conflict_score(
    *,
    adverse: int,
    severe: int,
    favorable: int,
    pressure: pressure_v7.PressureState,
    aligned_factor_r: Decimal,
    opposed_factor_r: Decimal,
) -> tuple[int, tuple[str, ...]]:
    flags: list[str] = []
    score = adverse + (2 * severe)
    if pressure.global_shock:
        score += 1
        flags.append("GLOBAL_SHOCK")
    if pressure.global_severe:
        score += 2
        flags.append("GLOBAL_SEVERE")
    if pressure.session_shock:
        score += 1
        flags.append("SESSION_SHOCK")
    if aligned_factor_r > Decimal("0"):
        score += 1
        flags.append("ALIGNED_OPEN_FACTOR")
    if opposed_factor_r > aligned_factor_r and opposed_factor_r > 0:
        score -= 1
        flags.append("OPPOSED_OPEN_FACTOR")
    score -= min(favorable, 2)
    return max(0, score), tuple(flags)


def _should_abstain(
    *,
    policy: str,
    projected_path_r: Decimal,
    conflict_score: int,
    recovery_evidence: bool,
) -> bool:
    spec = POLICY_SPECS.get(policy)
    if spec is None:
        return False
    budget, minimum_conflict, honor_recovery = spec
    if projected_path_r <= budget:
        return False
    if conflict_score < minimum_conflict:
        return False
    if honor_recovery and recovery_evidence:
        return False
    return True


def _simulate(
    *,
    period: str,
    policy: str,
    ledgers: dict[str, tuple[milestone.SimulatedTrade, ...]],
    contexts: dict[tuple[str, str], Any],
    contextual_model: dict[str, Any],
) -> tuple[dict[str, Any], tuple[BudgetDecision, ...]]:
    by_mode = {
        mode: {(row.symbol, row.entry_at): row for row in rows}
        for mode, rows in ledgers.items()
    }
    ordered = tuple(
        sorted(
            ledgers[milestone.ProtectionMode.ORIGINAL.value],
            key=lambda row: (direct._aware(row.entry_at), row.symbol),
        )
    )
    chosen: list[milestone.SimulatedTrade] = []
    records: list[memory.MemoryRecord] = []
    open_risk: list[OpenRisk] = []
    decisions: list[BudgetDecision] = []
    multipliers: Counter[str] = Counter()
    abstained = 0

    for trade in ordered:
        pre = v11._pretrade(
            period=period,
            trade=trade,
            contexts=contexts,
            contextual_model=contextual_model,
            chosen_scaled=tuple(chosen),
            records=tuple(records),
        )
        active_risk, shared, aligned, opposed = _factor_summary(
            tuple(open_risk),
            trade=trade,
        )
        adverse, severe, favorable, pressure, recovery = _causal_state(
            records=tuple(records),
            pre=pre,
            session=trade.session,
        )
        conflict, flags = _conflict_score(
            adverse=adverse,
            severe=severe,
            favorable=favorable,
            pressure=pressure,
            aligned_factor_r=aligned,
            opposed_factor_r=opposed,
        )
        projected = pre.current_dd + active_risk + pre.base_multiplier
        reject = _should_abstain(
            policy=policy,
            projected_path_r=projected,
            conflict_score=conflict,
            recovery_evidence=recovery,
        )
        reason = "ALLOW"
        if reject:
            abstained += 1
            reason = "CAUSAL_PATH_BUDGET_CONFLICT"

        decisions.append(
            BudgetDecision(
                period=period,
                policy=policy,
                symbol=trade.symbol,
                session=trade.session,
                entry_at=trade.entry_at,
                current_drawdown_r=str(pre.current_dd),
                active_risk_r=str(active_risk),
                shared_factor_r=str(shared),
                aligned_factor_r=str(aligned),
                opposed_factor_r=str(opposed),
                base_multiplier=str(pre.base_multiplier),
                projected_path_r=str(projected),
                adverse_votes=adverse,
                severe_votes=severe,
                favorable_votes=favorable,
                pressure_flags=flags,
                conflict_score=conflict,
                recovery_evidence=recovery,
                abstain=reject,
                reason=reason,
            )
        )
        if reject:
            continue

        key = (trade.symbol, trade.entry_at)
        unscaled = by_mode[pre.mode][key]
        scaled = replace(
            unscaled,
            realized_gross_r=str(
                Decimal(unscaled.realized_gross_r) * pre.base_multiplier
            ),
        )
        chosen.append(scaled)
        records.append(
            memory.MemoryRecord(
                symbol=pre.ctx.symbol,
                session=pre.ctx.session,
                destination_state=pre.ctx.destination_state,
                context_signature=pre.ctx.context_signature,
                exit_at=unscaled.exit_at,
                normalized_realized_r=unscaled.realized_gross_r,
            )
        )
        open_risk.append(
            OpenRisk(
                symbol=trade.symbol,
                side=trade.side,
                entry_at=trade.entry_at,
                exit_at=unscaled.exit_at,
                risk_r=pre.base_multiplier,
            )
        )
        multipliers[str(pre.base_multiplier)] += 1

    ledger = tuple(chosen)
    return {
        "period": period,
        "policy": policy,
        "trades": len(ledger),
        "original_selected_trades": len(ordered),
        "abstained": abstained,
        "density_retention": str(Decimal(len(ledger)) / Decimal(len(ordered))),
        "metrics": milestone._metrics(ledger),
        "multiplier_counts": dict(sorted(multipliers.items())),
    }, tuple(decisions)


def build_report(
    development_root: Path,
    validation_root: Path,
    reserved_root: Path,
    development_validation_context_root: Path,
    reserved_context_root: Path,
) -> tuple[dict[str, Any], tuple[BudgetDecision, ...]]:
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
        simultaneous.update(v11._simultaneous_map(period=period, ledgers=ledgers))

    previous = dict(v11._SIMULTANEOUS)
    v11._SIMULTANEOUS.clear()
    v11._SIMULTANEOUS.update(simultaneous)
    try:
        controls: dict[str, dict[str, Any]] = {}
        audits: list[BudgetDecision] = []
        for period, (ledgers, contexts) in windows.items():
            control, audit = _simulate(
                period=period,
                policy="SURFACE_CONTROL",
                ledgers=ledgers,
                contexts=contexts,
                contextual_model=contextual_model,
            )
            controls[period] = control
            audits.extend(audit)

        results: list[dict[str, Any]] = []
        for policy in POLICIES:
            heldouts: dict[str, Any] = {}
            for period, (ledgers, contexts) in windows.items():
                if policy == "SURFACE_CONTROL":
                    current = controls[period]
                else:
                    current, audit = _simulate(
                        period=period,
                        policy=policy,
                        ledgers=ledgers,
                        contexts=contexts,
                        contextual_model=contextual_model,
                    )
                    audits.extend(audit)
                v10._annotate(current, controls[period])
                current["density_at_or_above_floor"] = (
                    Decimal(current["density_retention"]) >= MIN_DENSITY_RETENTION
                )
                current["losing_streak_not_worse"] = (
                    int(current["metrics"]["max_losing_streak"])
                    <= int(controls[period]["metrics"]["max_losing_streak"])
                )
                heldouts[period] = current

            all_full = all(
                row["pf_at_least_surface_control"]
                and row["total_r_at_least_surface_control"]
                and row["dd_below_surface_control"]
                and row["density_at_or_above_floor"]
                and row["losing_streak_not_worse"]
                for row in heldouts.values()
            )
            all_dd6 = all(row["dd_at_or_below_6r"] for row in heldouts.values())
            results.append(
                {
                    "policy": policy,
                    "heldouts": heldouts,
                    "all_consumed_full_gate": all_full,
                    "all_consumed_dd6": all_dd6,
                }
            )
    finally:
        v11._SIMULTANEOUS.clear()
        v11._SIMULTANEOUS.update(previous)

    candidates = tuple(
        row
        for row in results
        if row["policy"] != "SURFACE_CONTROL"
        and row["all_consumed_full_gate"]
        and row["all_consumed_dd6"]
    )
    return {
        "identity": IDENTITY,
        "evaluation": "CAUSAL_DRAWDOWN_PLUS_OPEN_RISK_ADMISSION_BUDGET",
        "minimum_density_retention": str(MIN_DENSITY_RETENTION),
        "policy_specs": {
            name: [str(budget), conflict, recovery]
            for name, (budget, conflict, recovery) in POLICY_SPECS.items()
        },
        "results": results,
        "candidate_count": len(candidates),
        "base_surface_multipliers_preserved": True,
        "no_dynamic_position_scaling_added": True,
        "closed_drawdown_visible_before_entry_only": True,
        "open_risk_uses_prior_accepted_entries_only": True,
        "open_trade_outcomes_visible_to_decision": False,
        "blocked_outcomes_visible_to_memory": False,
        "current_outcome_visible_to_decision": False,
        "causal_conflict_required_for_abstention": True,
        "selected_ledger_diagnostic_only": True,
        "full_source_recompetition_required_before_freeze": True,
        "target_r": "2.00",
        "max3_ceiling_preserved": True,
        "automatic_policy_promotion": False,
        "trader_certified": False,
        "live_authorized": False,
        "real_capital_authorized": False,
        "next_phase": (
            "REPLAY_V14_RULE_THROUGH_FULL_SOURCE_COMPETITION"
            if candidates
            else "BUILD_FAILURE_STATE_TRANSITION_SURVIVAL_V15"
        ),
    }, tuple(audits)


def write_report(
    report: dict[str, Any],
    audits: tuple[BudgetDecision, ...],
    output: Path,
) -> None:
    output.mkdir(parents=True, exist_ok=True)
    (output / "capitalizer-drawdown-path-causal-budget-v14.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    with (
        output / "capitalizer-drawdown-path-causal-budget-v14-decisions.jsonl"
    ).open("w", encoding="utf-8") as handle:
        for row in audits:
            handle.write(json.dumps(asdict(row), sort_keys=True) + "\n")


def main() -> None:
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


if __name__ == "__main__":
    main()

"""Drawdown-aware adaptive risk governor V2.

Extends the causal context-edge memory with a continuous exposure governor.
Every valid entry still executes. Risk is reduced only when the realized
portfolio drawdown and already-closed context memory jointly indicate danger.

This is designed to contain residual peak-to-trough loss without globally
damaging PF. The 2022-2024 window is consumed research; a new 2020-2022
non-overlapping holdout is reserved for the frozen winner.
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
    capitalizer_adaptive_context_risk_governor_v1 as v1,
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

IDENTITY = "QORE_CAPITALIZER_DD_AWARE_ADAPTIVE_RISK_GOVERNOR_V2"
BASE_POLICY = v1.BASE_POLICY

POLICIES = (
    "EDGE_DD_BALANCED",
    "EDGE_DD_HARD",
    "EDGE_DD_ASYMMETRIC",
    "EDGE_DD_CEILING",
)


@dataclass(frozen=True, slots=True)
class DdRiskDecision:
    role: str
    policy: str
    symbol: str
    session: str
    operating_date: str
    entry_at: str
    current_drawdown_r: str
    stability_state: str
    destination_state: str
    adverse_votes: int
    severe_votes: int
    selected_mode: str
    risk_multiplier: str
    current_outcome_visible_to_decision: bool = False


def _multiplier(
    *,
    policy: str,
    state: governor.StabilityState,
    current_dd: Decimal,
    adverse_votes: int,
    severe_votes: int,
) -> Decimal:
    if policy == "EDGE_DD_BALANCED":
        if current_dd >= Decimal("5"):
            return Decimal("0.20") if adverse_votes >= 2 else Decimal("0.50")
        if current_dd >= Decimal("4"):
            return Decimal("0.35") if adverse_votes >= 2 else Decimal("0.75")
        if state is governor.StabilityState.WATCH and adverse_votes >= 2:
            return Decimal("0.65")
        if adverse_votes >= 3:
            return Decimal("0.75")
        return Decimal("1")

    if policy == "EDGE_DD_HARD":
        if current_dd >= Decimal("5"):
            return Decimal("0.15") if adverse_votes >= 1 else Decimal("0.35")
        if current_dd >= Decimal("4"):
            return Decimal("0.25") if adverse_votes >= 2 else Decimal("0.60")
        if current_dd >= Decimal("2") and adverse_votes >= 2:
            return Decimal("0.50")
        return Decimal("1")

    if policy == "EDGE_DD_ASYMMETRIC":
        if current_dd >= Decimal("3") and severe_votes >= 2:
            return Decimal("0.20")
        if current_dd >= Decimal("3") and adverse_votes >= 3:
            return Decimal("0.35")
        if state is governor.StabilityState.DEFENSIVE and adverse_votes >= 2:
            return Decimal("0.50")
        if state is governor.StabilityState.WATCH and adverse_votes >= 3:
            return Decimal("0.70")
        return Decimal("1")

    if policy == "EDGE_DD_CEILING":
        if current_dd >= Decimal("5.5"):
            return Decimal("0.10")
        if current_dd >= Decimal("5"):
            return Decimal("0.20") if adverse_votes >= 1 else Decimal("0.40")
        if current_dd >= Decimal("4"):
            return Decimal("0.30") if adverse_votes >= 2 else Decimal("0.65")
        if current_dd >= Decimal("3") and adverse_votes >= 2:
            return Decimal("0.55")
        if adverse_votes >= 3:
            return Decimal("0.70")
        return Decimal("1")

    raise ValueError(f"unknown DD-aware policy: {policy}")


def _simulate(
    *,
    role: str,
    policy: str,
    ledgers: dict[str, tuple[milestone.SimulatedTrade, ...]],
    contexts: dict[tuple[str, str], context.NativeContextRow],
    model: dict[str, Any],
) -> tuple[dict[str, Any], tuple[DdRiskDecision, ...]]:
    by_mode = {
        arm: {(row.symbol, row.entry_at): row for row in rows}
        for arm, rows in ledgers.items()
    }
    baseline = ledgers[milestone.ProtectionMode.ORIGINAL.value]
    ordered = tuple(
        sorted(baseline, key=lambda row: (direct._aware(row.entry_at), row.symbol))
    )

    chosen_scaled: list[milestone.SimulatedTrade] = []
    memory: list[v1.MemoryRecord] = []
    decisions: list[DdRiskDecision] = []
    multiplier_counts: dict[str, int] = defaultdict(int)

    for trade in ordered:
        key = (trade.symbol, trade.entry_at)
        ctx = contexts[key]
        history = governor._closed_history(
            tuple(chosen_scaled),
            entry_at=direct._aware(trade.entry_at),
        )
        state, _equity, _peak, current_dd, _loss_streak = governor._state(history)
        base_mode, _level, _support = router._lookup(model, ctx)
        final_mode, _overlay = router._overlay(
            policy=BASE_POLICY,
            base_mode=base_mode,
            state=state,
        )
        unscaled = by_mode[final_mode][key]

        causal_memory = v1._closed_records(tuple(memory), entry_at=trade.entry_at)
        evidence = v1._evidence(records=causal_memory, ctx=ctx)
        adverse_votes = sum(item.adverse for item in evidence)
        severe_votes = sum(item.severe for item in evidence)
        multiplier = _multiplier(
            policy=policy,
            state=state,
            current_dd=current_dd,
            adverse_votes=adverse_votes,
            severe_votes=severe_votes,
        )
        scaled = replace(
            unscaled,
            realized_gross_r=str(Decimal(unscaled.realized_gross_r) * multiplier),
        )
        chosen_scaled.append(scaled)
        memory.append(
            v1.MemoryRecord(
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
            DdRiskDecision(
                role=role,
                policy=policy,
                symbol=trade.symbol,
                session=trade.session,
                operating_date=trade.operating_date,
                entry_at=trade.entry_at,
                current_drawdown_r=str(current_dd),
                stability_state=state.value,
                destination_state=ctx.destination_state,
                adverse_votes=adverse_votes,
                severe_votes=severe_votes,
                selected_mode=final_mode,
                risk_multiplier=str(multiplier),
            )
        )

    rows = tuple(chosen_scaled)
    return {
        "role": role,
        "policy": policy,
        "trades": len(rows),
        "density_retention": "1",
        "metrics": milestone._metrics(rows),
        "multiplier_counts": dict(sorted(multiplier_counts.items())),
    }, tuple(decisions)


def build_report(
    development_root: Path,
    validation_root: Path,
    context_root: Path,
) -> tuple[dict[str, Any], tuple[DdRiskDecision, ...]]:
    development = router._load_selected(
        development_root,
        expected=v1.EXPECTED_DEVELOPMENT_TRADES,
    )
    validation = router._load_selected(
        validation_root,
        expected=v1.EXPECTED_VALIDATION_TRADES,
    )
    dev_context = router._load_contexts(context_root, role="dev")
    val_context = router._load_contexts(context_root, role="holdout")
    model = router._freeze_model(development=development, contexts=dev_context)

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
    audits: list[DdRiskDecision] = []
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
            m = current["metrics"]
            c = control["metrics"]
            current["pf_at_least_contextual_control"] = (
                Decimal(str(m["profit_factor"])) >= Decimal(str(c["profit_factor"]))
            )
            current["dd_below_contextual_control"] = (
                Decimal(str(m["max_drawdown_r"])) < Decimal(str(c["max_drawdown_r"]))
            )
            current["dd_at_or_below_6r"] = Decimal(str(m["max_drawdown_r"])) <= Decimal("6")
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
    dd6 = tuple(row for row in robust if row["validation"]["dd_at_or_below_6r"])

    return {
        "identity": IDENTITY,
        "base_policy": BASE_POLICY,
        "development_role": "CONSUMED_RESEARCH_2024_2026",
        "validation_role": "CONSUMED_VALIDATION_2022_2024",
        "development_trades": v1.EXPECTED_DEVELOPMENT_TRADES,
        "validation_trades": v1.EXPECTED_VALIDATION_TRADES,
        "policy_count": len(POLICIES),
        "results": results,
        "robust_pf_up_dd_down_policy_count": len(robust),
        "robust_validation_dd6_policy_count": len(dd6),
        "all_entries_preserved": True,
        "current_outcome_visible_to_decision": False,
        "prior_closed_chosen_memory_only": True,
        "validation_is_fresh_holdout": False,
        "new_holdout_reserved": "2020-09-17_TO_2022-09-17",
        "runtime_rule_selected": False,
        "trader_certified": False,
        "live_authorized": False,
        "real_capital_authorized": False,
        "next_phase": (
            "FREEZE_WINNER_AND_RUN_2020_2022_FRESH_HOLDOUT"
            if robust
            else "ADD_CROSS_MARKET_FACTOR_PRESSURE_TO_EDGE_MEMORY"
        ),
    }, tuple(audits)


def write_report(
    report: dict[str, Any],
    audits: tuple[DdRiskDecision, ...],
    output: Path,
) -> None:
    output.mkdir(parents=True, exist_ok=True)
    (output / "capitalizer-dd-aware-adaptive-risk-governor-v2.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    with (
        output / "capitalizer-dd-aware-adaptive-risk-governor-v2-decisions.jsonl"
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

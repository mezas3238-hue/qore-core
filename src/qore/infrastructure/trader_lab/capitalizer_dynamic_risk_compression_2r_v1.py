"""Dynamic causal risk compression for residual Capitalizer drawdown.

Residual-DD forensics showed that the dominant validation drawdown occurs while
the engine is already DEFENSIVE, especially when confirmed H1 destination room
is <1R. Those trades often never reach the first 0.50R milestone, so trailing
cannot solve them.

This lab preserves every entry and the contextual milestone routing. It changes
only exposure size BEFORE the current outcome is known. State is recalculated
from the actually scaled, already-closed path, so each policy is genuinely
path-dependent.

The 2022-2024 window is CONSUMED validation: its forensics motivated this
architecture. A new non-overlapping holdout is mandatory before certification.
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

IDENTITY = "QORE_CAPITALIZER_DYNAMIC_RISK_COMPRESSION_2R_V1"
BASE_POLICY = "CONTEXT_STABILITY_STAGE"

EXPECTED_DEVELOPMENT_TRADES = 948
EXPECTED_VALIDATION_TRADES = 1034

POLICIES = (
    "CONTEXTUAL_CONTROL",
    "STATE_075_050",
    "DEF_LT1_050",
    "DEF_LT1_035",
    "DEF_LT1_025",
    "DEF_NOT_GE2_050",
    "CAUSAL_RECOVERY_LADDER",
)


@dataclass(frozen=True, slots=True)
class RiskDecision:
    role: str
    policy: str
    symbol: str
    session: str
    operating_date: str
    entry_at: str
    stability_state: str
    destination_state: str
    regime_signature: str
    selected_mode: str
    risk_multiplier: str
    unscaled_realized_r: str
    scaled_realized_r: str
    current_outcome_visible_to_sizing: bool = False
    validation_outcome_visible_to_policy: bool = False


def _multiplier(
    *,
    policy: str,
    state: governor.StabilityState,
    destination: str,
) -> Decimal:
    if policy == "CONTEXTUAL_CONTROL":
        return Decimal("1")
    if policy == "STATE_075_050":
        if state is governor.StabilityState.DEFENSIVE:
            return Decimal("0.50")
        if state is governor.StabilityState.WATCH:
            return Decimal("0.75")
        return Decimal("1")
    if policy == "DEF_LT1_050":
        return (
            Decimal("0.50")
            if state is governor.StabilityState.DEFENSIVE and destination == "LT_1R"
            else Decimal("1")
        )
    if policy == "DEF_LT1_035":
        return (
            Decimal("0.35")
            if state is governor.StabilityState.DEFENSIVE and destination == "LT_1R"
            else Decimal("1")
        )
    if policy == "DEF_LT1_025":
        return (
            Decimal("0.25")
            if state is governor.StabilityState.DEFENSIVE and destination == "LT_1R"
            else Decimal("1")
        )
    if policy == "DEF_NOT_GE2_050":
        return (
            Decimal("0.50")
            if state is governor.StabilityState.DEFENSIVE
            and destination in {"LT_1R", "R1_TO_2"}
            else Decimal("1")
        )
    if policy == "CAUSAL_RECOVERY_LADDER":
        if state is governor.StabilityState.DEFENSIVE:
            if destination == "LT_1R":
                return Decimal("0.35")
            return Decimal("0.60")
        if state is governor.StabilityState.WATCH:
            return Decimal("0.75") if destination == "LT_1R" else Decimal("0.90")
        return Decimal("1")
    raise ValueError(f"unknown risk compression policy: {policy}")


def _scaled_trade(
    row: milestone.SimulatedTrade,
    *,
    multiplier: Decimal,
) -> milestone.SimulatedTrade:
    return replace(
        row,
        realized_gross_r=str(Decimal(row.realized_gross_r) * multiplier),
    )


def _simulate(
    *,
    role: str,
    policy: str,
    ledgers: dict[str, tuple[milestone.SimulatedTrade, ...]],
    contexts: dict[tuple[str, str], context.NativeContextRow],
    model: dict[str, Any],
) -> tuple[dict[str, Any], tuple[RiskDecision, ...]]:
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
    decisions: list[RiskDecision] = []
    multiplier_counts: dict[str, int] = defaultdict(int)
    state_counts: dict[str, int] = defaultdict(int)
    destination_counts: dict[str, int] = defaultdict(int)

    for trade in ordered:
        key = (trade.symbol, trade.entry_at)
        ctx = contexts[key]
        history = governor._closed_history(
            tuple(chosen_scaled),
            entry_at=direct._aware(trade.entry_at),
        )
        state, _eq, _pk, _dd, _ls = governor._state(history)
        base_mode, _level, _support = router._lookup(model, ctx)
        final_mode, _overlay = router._overlay(
            policy=BASE_POLICY,
            base_mode=base_mode,
            state=state,
        )
        unscaled = by_mode[final_mode][key]
        multiplier = _multiplier(
            policy=policy,
            state=state,
            destination=ctx.destination_state,
        )
        scaled = _scaled_trade(unscaled, multiplier=multiplier)
        chosen_scaled.append(scaled)

        multiplier_counts[str(multiplier)] += 1
        state_counts[state.value] += 1
        destination_counts[ctx.destination_state] += 1
        decisions.append(
            RiskDecision(
                role=role,
                policy=policy,
                symbol=trade.symbol,
                session=trade.session,
                operating_date=trade.operating_date,
                entry_at=trade.entry_at,
                stability_state=state.value,
                destination_state=ctx.destination_state,
                regime_signature=ctx.regime_signature,
                selected_mode=final_mode,
                risk_multiplier=str(multiplier),
                unscaled_realized_r=unscaled.realized_gross_r,
                scaled_realized_r=scaled.realized_gross_r,
            )
        )

    result = tuple(chosen_scaled)
    metrics = milestone._metrics(result)
    return {
        "role": role,
        "policy": policy,
        "trades": len(result),
        "density_retention": "1",
        "metrics": metrics,
        "multiplier_counts": dict(sorted(multiplier_counts.items())),
        "state_counts": dict(sorted(state_counts.items())),
        "destination_counts": dict(sorted(destination_counts.items())),
    }, tuple(decisions)


def build_report(
    development_root: Path,
    validation_root: Path,
    context_root: Path,
) -> tuple[dict[str, Any], tuple[RiskDecision, ...]]:
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

    results: list[dict[str, Any]] = []
    audits: list[RiskDecision] = []
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
        results.append(
            {
                "policy": policy,
                "development": dev,
                "validation": val,
            }
        )
        audits.extend(dev_audit)
        audits.extend(val_audit)

    dev_control = next(
        row["development"]
        for row in results
        if row["policy"] == "CONTEXTUAL_CONTROL"
    )
    val_control = next(
        row["validation"]
        for row in results
        if row["policy"] == "CONTEXTUAL_CONTROL"
    )

    for row in results:
        for key, control in (
            ("development", dev_control),
            ("validation", val_control),
        ):
            current = row[key]
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
            current["dd_at_or_below_6r"] = (
                Decimal(str(metrics["max_drawdown_r"])) <= Decimal("6")
            )
            current["total_r_retention_vs_contextual_control"] = str(
                Decimal(str(metrics["total_r"]))
                / Decimal(str(control_metrics["total_r"]))
            )

    robust = tuple(
        row
        for row in results
        if row["policy"] != "CONTEXTUAL_CONTROL"
        and row["development"]["pf_at_least_contextual_control"]
        and row["development"]["dd_below_contextual_control"]
        and row["validation"]["pf_at_least_contextual_control"]
        and row["validation"]["dd_below_contextual_control"]
    )
    dd6 = tuple(
        row
        for row in robust
        if row["validation"]["dd_at_or_below_6r"]
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
        "robust_validation_dd6_policy_count": len(dd6),
        "all_entries_preserved": True,
        "sizing_decision_before_current_outcome": True,
        "validation_outcomes_visible_to_policy_design": True,
        "new_nonoverlapping_holdout_required": True,
        "strategy_entry_changed": False,
        "milestone_target_changed": False,
        "max3_changed": False,
        "runtime_rule_selected": False,
        "trader_certified": False,
        "live_authorized": False,
        "real_capital_authorized": False,
        "next_phase": (
            "FREEZE_RISK_COMPRESSION_AND_OPEN_NEW_HOLDOUT"
            if robust
            else "REBUILD_CAUSAL_PREENTRY_ADVERSITY_STATE"
        ),
    }, tuple(audits)


def write_report(
    report: dict[str, Any],
    audits: tuple[RiskDecision, ...],
    output: Path,
) -> None:
    output.mkdir(parents=True, exist_ok=True)
    (output / "capitalizer-dynamic-risk-compression-2r-v1.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    with (
        output / "capitalizer-dynamic-risk-compression-2r-v1-decisions.jsonl"
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

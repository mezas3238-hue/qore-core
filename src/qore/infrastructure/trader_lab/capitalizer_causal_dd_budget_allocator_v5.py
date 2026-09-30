"""Causal drawdown-budget allocator over the robust adversity surface.

SURFACE_SELECTIVE raises PF and cuts DD in both consumed windows, but residual
portfolio DD remains slightly above 6R because overlapping valid trades can add
risk while earlier trades are still open.

This allocator keeps every valid entry. Before each entry it:
1. computes realized DD from already-CLOSED scaled outcomes;
2. reserves the full authorized R of still-open positions (conservative);
3. computes remaining portfolio DD headroom;
4. caps the new trade's risk multiplier by that headroom and the already-robust
   SURFACE_SELECTIVE multiplier.

No open trade's future outcome or future stop movement is assumed. Full initial
authorized risk is reserved until that position closes, so the budget is causal
and deliberately conservative.
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

IDENTITY = "QORE_CAPITALIZER_CAUSAL_DD_BUDGET_ALLOCATOR_V5"
BASE_SURFACE_POLICY = "SURFACE_SELECTIVE"
MIN_EXECUTION_R = Decimal("0.05")

BUDGETS: dict[str, Decimal] = {
    "BUDGET_5R00": Decimal("5.00"),
    "BUDGET_5R50": Decimal("5.50"),
    "BUDGET_5R75": Decimal("5.75"),
    "BUDGET_6R00": Decimal("6.00"),
}


@dataclass(frozen=True, slots=True)
class ExposureReservation:
    entry_at: str
    exit_at: str
    authorized_r: str


@dataclass(frozen=True, slots=True)
class BudgetDecision:
    role: str
    policy: str
    symbol: str
    session: str
    operating_date: str
    entry_at: str
    realized_drawdown_r: str
    active_reserved_r: str
    budget_r: str
    headroom_r: str
    surface_multiplier: str
    final_multiplier: str
    active_position_count: int
    current_outcome_visible_to_decision: bool = False
    open_trade_future_visible_to_reservation: bool = False


def _active_reservations(
    reservations: tuple[ExposureReservation, ...],
    *,
    entry_at: str,
) -> tuple[ExposureReservation, ...]:
    current = direct._aware(entry_at)
    return tuple(
        row
        for row in reservations
        if direct._aware(row.entry_at) < current < direct._aware(row.exit_at)
    )


def _realized_dd(
    history: tuple[milestone.SimulatedTrade, ...],
) -> Decimal:
    equity = Decimal("0")
    peak = Decimal("0")
    for row in history:
        equity += Decimal(row.realized_gross_r)
        peak = max(peak, equity)
    return peak - equity


def _budget_multiplier(
    *,
    budget: Decimal,
    realized_dd: Decimal,
    active_reserved: Decimal,
    surface_multiplier: Decimal,
) -> tuple[Decimal, Decimal]:
    raw_headroom = budget - realized_dd - active_reserved
    headroom = max(Decimal("0"), raw_headroom)
    allowed = min(Decimal("1"), surface_multiplier, headroom)
    final = max(MIN_EXECUTION_R, allowed)
    return final, headroom


def _simulate(
    *,
    role: str,
    policy: str,
    ledgers: dict[str, tuple[milestone.SimulatedTrade, ...]],
    contexts: dict[tuple[str, str], context.NativeContextRow],
    model: dict[str, Any],
) -> tuple[dict[str, Any], tuple[BudgetDecision, ...]]:
    budget = BUDGETS[policy]
    by_mode = {
        arm: {(row.symbol, row.entry_at): row for row in rows}
        for arm, rows in ledgers.items()
    }
    baseline = ledgers[milestone.ProtectionMode.ORIGINAL.value]
    ordered = tuple(
        sorted(baseline, key=lambda row: (direct._aware(row.entry_at), row.symbol))
    )

    chosen_scaled: list[milestone.SimulatedTrade] = []
    memories: list[memory.MemoryRecord] = []
    reservations: list[ExposureReservation] = []
    decisions: list[BudgetDecision] = []
    multiplier_counts: Counter[str] = Counter()
    active_count_histogram: Counter[int] = Counter()
    zero_headroom_decisions = 0

    for trade in ordered:
        key = (trade.symbol, trade.entry_at)
        ctx = contexts[key]
        closed = governor._closed_history(
            tuple(chosen_scaled),
            entry_at=direct._aware(trade.entry_at),
        )
        state, _eq, _peak, current_dd, _ls = governor._state(closed)
        base_mode, _level, _support = router._lookup(model, ctx)
        final_mode, _overlay = router._overlay(
            policy=surface.BASE_POLICY,
            base_mode=base_mode,
            state=state,
        )
        unscaled = by_mode[final_mode][key]

        causal_memory = memory._closed_records(
            tuple(memories),
            entry_at=trade.entry_at,
        )
        evidence = memory._evidence(records=causal_memory, ctx=ctx)
        adverse_votes = sum(item.adverse for item in evidence)
        hazards = surface._hazards(
            ctx=ctx,
            current_dd=current_dd,
            adverse_votes=adverse_votes,
        )
        hazard_score = surface._score(hazards)
        surface_multiplier = surface._multiplier(
            policy=BASE_SURFACE_POLICY,
            ctx=ctx,
            current_dd=current_dd,
            hazards=hazards,
            score=hazard_score,
            adverse_votes=adverse_votes,
        )

        active = _active_reservations(tuple(reservations), entry_at=trade.entry_at)
        active_reserved = sum(
            (Decimal(row.authorized_r) for row in active),
            Decimal("0"),
        )
        multiplier, headroom = _budget_multiplier(
            budget=budget,
            realized_dd=current_dd,
            active_reserved=active_reserved,
            surface_multiplier=surface_multiplier,
        )
        if headroom == 0:
            zero_headroom_decisions += 1

        scaled = replace(
            unscaled,
            realized_gross_r=str(
                Decimal(unscaled.realized_gross_r) * multiplier
            ),
        )
        chosen_scaled.append(scaled)
        reservations.append(
            ExposureReservation(
                entry_at=unscaled.entry_at,
                exit_at=unscaled.exit_at,
                authorized_r=str(multiplier),
            )
        )
        memories.append(
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
        active_count_histogram[len(active)] += 1
        decisions.append(
            BudgetDecision(
                role=role,
                policy=policy,
                symbol=trade.symbol,
                session=trade.session,
                operating_date=trade.operating_date,
                entry_at=trade.entry_at,
                realized_drawdown_r=str(current_dd),
                active_reserved_r=str(active_reserved),
                budget_r=str(budget),
                headroom_r=str(headroom),
                surface_multiplier=str(surface_multiplier),
                final_multiplier=str(multiplier),
                active_position_count=len(active),
            )
        )

    result = tuple(chosen_scaled)
    metrics = milestone._metrics(result)
    return {
        "role": role,
        "policy": policy,
        "budget_r": str(budget),
        "trades": len(result),
        "density_retention": "1",
        "metrics": metrics,
        "multiplier_counts": dict(sorted(multiplier_counts.items())),
        "active_position_count_histogram": {
            str(key): value for key, value in sorted(active_count_histogram.items())
        },
        "zero_headroom_decisions": zero_headroom_decisions,
    }, tuple(decisions)


def build_report(
    development_root: Path,
    validation_root: Path,
    context_root: Path,
) -> tuple[dict[str, Any], tuple[BudgetDecision, ...]]:
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

    surface_dev, _ = surface._simulate(
        role="DEV_SURFACE_CONTROL",
        policy=BASE_SURFACE_POLICY,
        ledgers=development,
        contexts=dev_context,
        model=model,
    )
    surface_val, _ = surface._simulate(
        role="VAL_SURFACE_CONTROL",
        policy=BASE_SURFACE_POLICY,
        ledgers=validation,
        contexts=val_context,
        model=model,
    )

    results: list[dict[str, Any]] = []
    audits: list[BudgetDecision] = []
    for policy in BUDGETS:
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
        for current, control in ((dev, surface_dev), (val, surface_val)):
            m, c = current["metrics"], control["metrics"]
            current["pf_at_least_surface_control"] = (
                Decimal(str(m["profit_factor"])) >= Decimal(str(c["profit_factor"]))
            )
            current["dd_at_or_below_6r"] = (
                Decimal(str(m["max_drawdown_r"])) <= Decimal("6")
            )
            current["total_r_retention_vs_surface"] = str(
                Decimal(str(m["total_r"])) / Decimal(str(c["total_r"]))
            )
        results.append({"policy": policy, "development": dev, "validation": val})
        audits.extend(da)
        audits.extend(va)

    both_dd6 = tuple(
        row for row in results
        if row["development"]["dd_at_or_below_6r"]
        and row["validation"]["dd_at_or_below_6r"]
    )
    both_dd6_pf = tuple(
        row for row in both_dd6
        if row["development"]["pf_at_least_surface_control"]
        and row["validation"]["pf_at_least_surface_control"]
    )

    return {
        "identity": IDENTITY,
        "base_surface_policy": BASE_SURFACE_POLICY,
        "development_trades": memory.EXPECTED_DEVELOPMENT_TRADES,
        "validation_trades": memory.EXPECTED_VALIDATION_TRADES,
        "budget_count": len(BUDGETS),
        "results": results,
        "both_windows_dd6_count": len(both_dd6),
        "both_windows_dd6_and_pf_not_lower_count": len(both_dd6_pf),
        "all_entries_preserved": True,
        "minimum_execution_r": str(MIN_EXECUTION_R),
        "active_positions_reserve_full_authorized_r_until_close": True,
        "open_trade_future_visible_to_reservation": False,
        "current_outcome_visible_to_decision": False,
        "validation_is_fresh_holdout": False,
        "new_holdout_reserved": "2020-09-17_TO_2022-09-17",
        "runtime_rule_selected": False,
        "trader_certified": False,
        "live_authorized": False,
        "real_capital_authorized": False,
        "next_phase": (
            "FREEZE_BUDGET_ALLOCATOR_AND_RUN_RESERVED_HOLDOUT"
            if both_dd6
            else "REVISE_PORTFOLIO_HEADROOM_ACCOUNTING"
        ),
    }, tuple(audits)


def write_report(
    report: dict[str, Any],
    audits: tuple[BudgetDecision, ...],
    output: Path,
) -> None:
    output.mkdir(parents=True, exist_ok=True)
    (output / "capitalizer-causal-dd-budget-allocator-v5.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    with (
        output / "capitalizer-causal-dd-budget-allocator-v5-decisions.jsonl"
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

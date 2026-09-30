"""Causal loss-pressure surface for Capitalizer.

V6 showed that slow session averages react too late and can sacrifice edge.
This V7 architecture targets DRAWNDOWN VELOCITY instead of drawdown level alone.

Pressure is measured only from already-closed, actually-chosen, normalized
trade outcomes:
- recent global R acceleration;
- breadth of losing symbols;
- loss concentration inside the current session.

The overlay acts early and sparsely. It can tighten exposure before the base
SURFACE_SELECTIVE governor reaches deep drawdown, but it never tightens below
0.20R and automatically disappears when pressure clears. This avoids making
the already-sticky 0.20R recovery state even more persistent.

All entries, 2R targets, contextual milestone routing and MAX3 are preserved.
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
    capitalizer_local_edge_convex_surface_v6 as v6,
)
from qore.infrastructure.trader_lab import (
    capitalizer_max_recovery_direct_m1_replay_v1 as direct,
)
from qore.infrastructure.trader_lab import capitalizer_native_market_context_v1 as context
from qore.infrastructure.trader_lab import (
    capitalizer_surface_selective_frozen_holdout_v1 as frozen,
)

IDENTITY = "QORE_CAPITALIZER_CAUSAL_LOSS_PRESSURE_SURFACE_V7"
BASE_POSITION_POLICY = "CONTEXT_STABILITY_STAGE"

EXPECTED_DEVELOPMENT_TRADES = 948
EXPECTED_VALIDATION_TRADES = 1034
EXPECTED_RESERVED_TRADES = 1088

GLOBAL_RECENT = 8
GLOBAL_SEVERE_RECENT = 10
SESSION_RECENT = 6

POLICIES = (
    "SURFACE_CONTROL",
    "EARLY_BREADTH_GUARD",
    "SESSION_CLUSTER_GUARD",
    "DUAL_CLUSTER_GUARD",
    "VELOCITY_CONVEX",
)

RISK_LADDER = (
    Decimal("0.20"),
    Decimal("0.35"),
    Decimal("0.55"),
    Decimal("0.75"),
    Decimal("1"),
)


@dataclass(frozen=True, slots=True)
class PressureState:
    global_support: int
    global_sum_r: str
    global_losses: int
    global_negative_symbols: int
    severe_support: int
    severe_sum_r: str
    severe_losses: int
    severe_negative_symbols: int
    session_support: int
    session_sum_r: str
    session_losses: int
    global_shock: bool
    global_severe: bool
    session_shock: bool


@dataclass(frozen=True, slots=True)
class PressureDecision:
    role: str
    policy: str
    symbol: str
    session: str
    operating_date: str
    entry_at: str
    selected_mode: str
    current_drawdown_r: str
    hazard_score: int
    adverse_votes: int
    base_multiplier: str
    final_multiplier: str
    adjustment: str
    pressure: PressureState
    current_outcome_visible_to_decision: bool = False
    unchosen_counterfactual_visible_to_decision: bool = False


def _stats(
    rows: tuple[memory.MemoryRecord, ...],
) -> tuple[int, Decimal, int, int]:
    values = tuple(Decimal(row.normalized_realized_r) for row in rows)
    return (
        len(rows),
        sum(values, Decimal("0")),
        sum(value < 0 for value in values),
        len({row.symbol for row, value in zip(rows, values, strict=True) if value < 0}),
    )


def _pressure(
    records: tuple[memory.MemoryRecord, ...],
    *,
    session: str,
) -> PressureState:
    recent = records[-GLOBAL_RECENT:]
    severe_recent = records[-GLOBAL_SEVERE_RECENT:]
    session_recent = tuple(row for row in records if row.session == session)[-SESSION_RECENT:]

    g_support, g_sum, g_losses, g_symbols = _stats(recent)
    s_support, s_sum, s_losses, s_symbols = _stats(severe_recent)
    sess_support, sess_sum, sess_losses, _sess_symbols = _stats(session_recent)

    global_shock = (
        g_support >= 6
        and g_sum <= Decimal("-2")
        and g_losses >= 4
        and g_symbols >= 3
    )
    global_severe = (
        s_support >= 8
        and s_sum <= Decimal("-3")
        and s_losses >= 6
        and s_symbols >= 4
    )
    session_shock = (
        sess_support >= 5
        and sess_sum <= Decimal("-2")
        and sess_losses >= 4
    )
    return PressureState(
        global_support=g_support,
        global_sum_r=str(g_sum),
        global_losses=g_losses,
        global_negative_symbols=g_symbols,
        severe_support=s_support,
        severe_sum_r=str(s_sum),
        severe_losses=s_losses,
        severe_negative_symbols=s_symbols,
        session_support=sess_support,
        session_sum_r=str(sess_sum),
        session_losses=sess_losses,
        global_shock=global_shock,
        global_severe=global_severe,
        session_shock=session_shock,
    )


def _step_down(base: Decimal, *, steps: int = 1) -> Decimal:
    try:
        index = RISK_LADDER.index(base)
    except ValueError as exc:
        raise ValueError(f"unsupported base multiplier {base}") from exc
    return RISK_LADDER[max(0, index - steps)]


def _pressure_multiplier(
    *,
    policy: str,
    base: Decimal,
    current_dd: Decimal,
    pressure: PressureState,
) -> tuple[Decimal, str]:
    if policy == "SURFACE_CONTROL":
        return base, "NONE"

    # Never further tighten the sticky 0.20R state. V7 is an EARLY guard.
    if base <= Decimal("0.20"):
        return base, "BASE_ALREADY_MIN"

    if policy == "EARLY_BREADTH_GUARD":
        if pressure.global_severe and current_dd < Decimal("5"):
            return min(base, Decimal("0.20")), "GLOBAL_SEVERE_CAP_020"
        if pressure.global_shock and current_dd < Decimal("4"):
            return min(base, Decimal("0.35")), "GLOBAL_SHOCK_CAP_035"
        return base, "NONE"

    if policy == "SESSION_CLUSTER_GUARD":
        if pressure.session_shock and current_dd < Decimal("5"):
            return _step_down(base), "SESSION_CLUSTER_STEP"
        return base, "NONE"

    if policy == "DUAL_CLUSTER_GUARD":
        if (
            pressure.global_shock
            and pressure.session_shock
            and current_dd < Decimal("5")
        ):
            return min(base, Decimal("0.20")), "DUAL_CLUSTER_CAP_020"
        if (
            (pressure.global_shock or pressure.session_shock)
            and current_dd < Decimal("4")
        ):
            return min(base, Decimal("0.55")), "SINGLE_CLUSTER_CAP_055"
        return base, "NONE"

    if policy == "VELOCITY_CONVEX":
        if pressure.global_severe and current_dd < Decimal("5"):
            return min(base, Decimal("0.20")), "VELOCITY_SEVERE_CAP_020"
        if (
            pressure.global_shock
            and pressure.session_shock
            and current_dd < Decimal("5")
        ):
            return _step_down(base, steps=2), "VELOCITY_DUAL_STEP_2"
        if (
            (pressure.global_shock or pressure.session_shock)
            and current_dd < Decimal("4")
        ):
            return _step_down(base), "VELOCITY_STEP"
        return base, "NONE"

    raise ValueError(f"unknown pressure policy: {policy}")


def _simulate(
    *,
    role: str,
    policy: str,
    ledgers: dict[str, tuple[milestone.SimulatedTrade, ...]],
    contexts: dict[tuple[str, str], context.NativeContextRow],
    model: dict[str, Any],
) -> tuple[dict[str, Any], tuple[PressureDecision, ...]]:
    by_mode = {
        mode: {(row.symbol, row.entry_at): row for row in rows}
        for mode, rows in ledgers.items()
    }
    baseline = ledgers[milestone.ProtectionMode.ORIGINAL.value]
    ordered = tuple(
        sorted(baseline, key=lambda row: (direct._aware(row.entry_at), row.symbol))
    )
    baseline_keys = {(row.symbol, row.entry_at) for row in ordered}
    missing = baseline_keys - set(contexts)
    if missing:
        raise ValueError(f"{role} missing {len(missing)} MAX3 contexts")

    chosen_scaled: list[milestone.SimulatedTrade] = []
    records: list[memory.MemoryRecord] = []
    decisions: list[PressureDecision] = []
    multiplier_counts: Counter[str] = Counter()
    adjustment_counts: Counter[str] = Counter()
    pressure_counts: Counter[str] = Counter()

    for trade in ordered:
        key = (trade.symbol, trade.entry_at)
        ctx = contexts[key]
        history = governor._closed_history(
            tuple(chosen_scaled),
            entry_at=direct._aware(trade.entry_at),
        )
        state, _eq, _peak, current_dd, _loss_streak = governor._state(history)

        base_mode, _level, _support = router._lookup(model, ctx)
        final_mode, _overlay = router._overlay(
            policy=BASE_POSITION_POLICY,
            base_mode=base_mode,
            state=state,
        )
        unscaled = by_mode[final_mode][key]

        causal_records = memory._closed_records(tuple(records), entry_at=trade.entry_at)
        evidence = memory._evidence(records=causal_records, ctx=ctx)
        adverse_votes = sum(item.adverse for item in evidence)
        hazards = frozen._frozen_hazards(
            ctx=ctx,
            current_dd=current_dd,
            adverse_votes=adverse_votes,
        )
        score = frozen._frozen_score(hazards)
        base_multiplier = frozen._frozen_multiplier(
            current_dd=current_dd,
            score=score,
            adverse_votes=adverse_votes,
        )
        pressure = _pressure(causal_records, session=trade.session)
        final_multiplier, adjustment = _pressure_multiplier(
            policy=policy,
            base=base_multiplier,
            current_dd=current_dd,
            pressure=pressure,
        )

        scaled = replace(
            unscaled,
            realized_gross_r=str(
                Decimal(unscaled.realized_gross_r) * final_multiplier
            ),
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
        multiplier_counts[str(final_multiplier)] += 1
        adjustment_counts[adjustment] += 1
        if pressure.global_severe:
            pressure_counts["GLOBAL_SEVERE"] += 1
        if pressure.global_shock:
            pressure_counts["GLOBAL_SHOCK"] += 1
        if pressure.session_shock:
            pressure_counts["SESSION_SHOCK"] += 1

        decisions.append(
            PressureDecision(
                role=role,
                policy=policy,
                symbol=trade.symbol,
                session=trade.session,
                operating_date=trade.operating_date,
                entry_at=trade.entry_at,
                selected_mode=final_mode,
                current_drawdown_r=str(current_dd),
                hazard_score=score,
                adverse_votes=adverse_votes,
                base_multiplier=str(base_multiplier),
                final_multiplier=str(final_multiplier),
                adjustment=adjustment,
                pressure=pressure,
            )
        )

    ledger = tuple(chosen_scaled)
    return {
        "role": role,
        "policy": policy,
        "trades": len(ledger),
        "density_retention": "1",
        "metrics": milestone._metrics(ledger),
        "multiplier_counts": dict(sorted(multiplier_counts.items())),
        "adjustment_counts": dict(sorted(adjustment_counts.items())),
        "pressure_counts": dict(sorted(pressure_counts.items())),
    }, tuple(decisions)


def _annotate(current: dict[str, Any], control: dict[str, Any]) -> None:
    metrics = current["metrics"]
    base = control["metrics"]
    current["pf_at_least_surface_control"] = (
        Decimal(str(metrics["profit_factor"])) >= Decimal(str(base["profit_factor"]))
    )
    current["dd_below_surface_control"] = (
        Decimal(str(metrics["max_drawdown_r"]))
        < Decimal(str(base["max_drawdown_r"]))
    )
    current["total_r_at_least_surface_control"] = (
        Decimal(str(metrics["total_r"])) >= Decimal(str(base["total_r"]))
    )
    current["dd_at_or_below_6r"] = (
        Decimal(str(metrics["max_drawdown_r"])) <= Decimal("6")
    )


def build_report(
    development_root: Path,
    validation_root: Path,
    consumed_reserved_root: Path,
    development_validation_context_root: Path,
    consumed_reserved_context_root: Path,
) -> tuple[dict[str, Any], tuple[PressureDecision, ...]]:
    development = router._load_selected(
        development_root,
        expected=EXPECTED_DEVELOPMENT_TRADES,
    )
    validation = router._load_selected(
        validation_root,
        expected=EXPECTED_VALIDATION_TRADES,
    )
    raw_reserved = {
        mode.value: direct._load_mode(consumed_reserved_root, mode=mode)
        for mode in milestone.ProtectionMode
    }
    reserved = {
        mode: direct._max3_milestone(rows)
        for mode, rows in raw_reserved.items()
    }
    if {len(rows) for rows in reserved.values()} != {EXPECTED_RESERVED_TRADES}:
        raise ValueError("V7 consumed reserved population mismatch")

    dev_context = router._load_contexts(
        development_validation_context_root,
        role="dev",
    )
    val_context = router._load_contexts(
        development_validation_context_root,
        role="holdout",
    )
    reserved_keys = {
        (row.symbol, row.entry_at)
        for row in reserved[milestone.ProtectionMode.ORIGINAL.value]
    }
    reserved_context = v6._load_reserved_contexts(
        consumed_reserved_context_root,
        baseline_keys=reserved_keys,
    )

    model = router._freeze_model(development=development, contexts=dev_context)
    windows = (
        ("DEVELOPMENT_2024_2026", development, dev_context),
        ("CONSUMED_VALIDATION_2022_2024", validation, val_context),
        ("CONSUMED_RESERVED_2020_2022", reserved, reserved_context),
    )

    controls: dict[str, dict[str, Any]] = {}
    audits: list[PressureDecision] = []
    for role, ledgers, contexts in windows:
        control, audit = _simulate(
            role=role,
            policy="SURFACE_CONTROL",
            ledgers=ledgers,
            contexts=contexts,
            model=model,
        )
        controls[role] = control
        audits.extend(audit)

    results: list[dict[str, Any]] = []
    for policy in POLICIES:
        policy_windows: dict[str, Any] = {}
        for role, ledgers, contexts in windows:
            if policy == "SURFACE_CONTROL":
                current = controls[role]
            else:
                current, audit = _simulate(
                    role=role,
                    policy=policy,
                    ledgers=ledgers,
                    contexts=contexts,
                    model=model,
                )
                audits.extend(audit)
            _annotate(current, controls[role])
            policy_windows[role] = current

        robust_pf_dd = all(
            window["pf_at_least_surface_control"]
            and window["dd_below_surface_control"]
            for window in policy_windows.values()
        )
        robust_full = all(
            window["pf_at_least_surface_control"]
            and window["dd_below_surface_control"]
            and window["total_r_at_least_surface_control"]
            for window in policy_windows.values()
        )
        all_dd6 = all(window["dd_at_or_below_6r"] for window in policy_windows.values())
        results.append(
            {
                "policy": policy,
                "windows": policy_windows,
                "robust_pf_up_dd_down_all_consumed_windows": robust_pf_dd,
                "robust_pf_dd_total_r_all_consumed_windows": robust_full,
                "all_consumed_windows_dd6": all_dd6,
            }
        )

    robust_rows = tuple(
        row for row in results if row["robust_pf_up_dd_down_all_consumed_windows"]
    )
    robust_full_rows = tuple(
        row for row in results if row["robust_pf_dd_total_r_all_consumed_windows"]
    )
    dd6_rows = tuple(row for row in robust_rows if row["all_consumed_windows_dd6"])

    return {
        "identity": IDENTITY,
        "design_windows": [
            "2024-09-17_TO_2026-09-17",
            "2022-09-17_TO_2024-09-17",
            "2020-09-17_TO_2022-09-17",
        ],
        "all_design_windows_consumed": True,
        "next_holdout_reserved": "2018-09-17_TO_2020-09-17",
        "development_trades": EXPECTED_DEVELOPMENT_TRADES,
        "validation_trades": EXPECTED_VALIDATION_TRADES,
        "consumed_reserved_trades": EXPECTED_RESERVED_TRADES,
        "policy_count": len(POLICIES),
        "results": results,
        "robust_pf_up_dd_down_policy_count": len(robust_rows),
        "robust_pf_dd_total_r_policy_count": len(robust_full_rows),
        "robust_all_windows_dd6_policy_count": len(dd6_rows),
        "pressure_uses_prior_closed_chosen_outcomes_only": True,
        "pressure_uses_normalized_unscaled_r": True,
        "current_outcome_visible_to_decision": False,
        "unchosen_counterfactual_visible_to_decision": False,
        "all_entries_preserved": True,
        "target_r": "2.00",
        "max3_preserved": True,
        "automatic_policy_promotion": False,
        "runtime_rule_selected": False,
        "trader_certified": False,
        "live_authorized": False,
        "real_capital_authorized": False,
        "next_phase": (
            "FREEZE_PRESSURE_POLICY_AND_OPEN_2018_2020_HOLDOUT"
            if robust_rows
            else "BUILD_DD_PATH_STATE_MACHINE_WITH_EARLY_SHOCK_AND_RECOVERY_PHASES"
        ),
    }, tuple(audits)


def write_report(
    report: dict[str, Any],
    audits: tuple[PressureDecision, ...],
    output: Path,
) -> None:
    output.mkdir(parents=True, exist_ok=True)
    (output / "capitalizer-causal-loss-pressure-surface-v7.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    with (
        output / "capitalizer-causal-loss-pressure-surface-v7-decisions.jsonl"
    ).open("w", encoding="utf-8") as handle:
        for row in audits:
            handle.write(json.dumps(asdict(row), sort_keys=True) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("development_root", type=Path)
    parser.add_argument("validation_root", type=Path)
    parser.add_argument("consumed_reserved_root", type=Path)
    parser.add_argument("development_validation_context_root", type=Path)
    parser.add_argument("consumed_reserved_context_root", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    report, audits = build_report(
        args.development_root,
        args.validation_root,
        args.consumed_reserved_root,
        args.development_validation_context_root,
        args.consumed_reserved_context_root,
    )
    write_report(report, audits, args.output)
    print(json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    main()

"""Development-frozen contextual milestone router.

This layer combines:
1. provider-native entry-time regime/destination context;
2. development-only hierarchical shrinkage for milestone-mode utility;
3. optional causal cross-market stability overlays.

The 2022-2024 window is explicitly treated as CONSUMED VALIDATION because
previous research has already inspected its economic outcomes. No claim of
fresh holdout is made here. A later non-overlapping window is required after a
candidate architecture is frozen.

All entries remain admitted. Only post-entry milestone protection is routed.
"""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from dataclasses import asdict, dataclass
from decimal import Decimal
from pathlib import Path
from typing import Any

from qore.infrastructure.trader_lab import (
    capitalizer_cognitive_r_milestone_protection_2r_v1 as milestone,
)
from qore.infrastructure.trader_lab import (
    capitalizer_cross_market_stability_governor_2r_v1 as governor,
)
from qore.infrastructure.trader_lab import (
    capitalizer_max_recovery_direct_m1_replay_v1 as direct,
)
from qore.infrastructure.trader_lab import capitalizer_native_market_context_v1 as context

IDENTITY = "QORE_CAPITALIZER_CONTEXTUAL_STABILITY_ROUTER_2R_V1"
SOURCE_DIRECT_RUN_ID = 36196002610
SOURCE_DIRECT_SHA = "ddd00209e50d5ec16c8cb94f34e9e5e95f401839"
SOURCE_CONTEXT_RUN_ID = 36211415438
SOURCE_CONTEXT_SHA = "c652b1e5a5181ba95ac6f10ea5c95bf808a0c8a7"

EXPECTED_DEVELOPMENT_TRADES = 948
EXPECTED_VALIDATION_TRADES = 1034

PRIOR_STRENGTH = Decimal("12")
NEGATIVE_RATE_WEIGHT = Decimal("0.20")
DOWNSIDE_WEIGHT = Decimal("0.10")

MIN_SYMBOL_CONTEXT = 18
MIN_SYMBOL_REGIME = 24
MIN_SYMBOL_DESTINATION = 24
MIN_SYMBOL = 40

ARMS = tuple(mode.value for mode in milestone.ProtectionMode)

POLICIES = (
    "CONTEXT_ONLY",
    "CONTEXT_DEFENSIVE_STAGE",
    "CONTEXT_STABILITY_STAGE",
    "CONTEXT_LOCK_STABILITY",
)


@dataclass(frozen=True, slots=True)
class ArmPosterior:
    arm: str
    support: int
    posterior_mean_r: str
    posterior_negative_rate: str
    posterior_downside_r: str
    utility: str


@dataclass(frozen=True, slots=True)
class ContextualDecision:
    role: str
    policy: str
    symbol: str
    session: str
    operating_date: str
    entry_at: str
    regime_signature: str
    destination_state: str
    context_signature: str
    hierarchy_level: str
    hierarchy_support: int
    learned_base_mode: str
    stability_state: str
    final_mode: str
    overlay_applied: bool
    current_outcome_visible_to_decision: bool = False
    validation_outcome_visible_to_training: bool = False
    unchosen_counterfactual_visible_to_decision: bool = False


def _load_contexts(
    root: Path,
    *,
    role: str,
) -> dict[tuple[str, str], context.NativeContextRow]:
    paths = sorted(
        root.rglob(
            f"capitalizer-*-native-market-context-{role.lower()}-v1-rows.jsonl"
        )
    )
    if len(paths) != 9:
        raise ValueError(
            f"contextual router requires nine {role} context ledgers, got {len(paths)}"
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
                    raise ValueError("duplicate native context identity")
                if row.outcome_visible_to_context:
                    raise ValueError("context cannot expose current outcome")
                if row.bars_after_entry_used or row.unconfirmed_pivot_used:
                    raise ValueError("context violates causal timing")
                result[key] = row
    return result


def _load_selected(
    root: Path,
    *,
    expected: int,
) -> dict[str, tuple[milestone.SimulatedTrade, ...]]:
    raw = {
        mode.value: direct._load_mode(root, mode=mode)
        for mode in milestone.ProtectionMode
    }
    selected = {
        mode: direct._max3_milestone(rows)
        for mode, rows in raw.items()
    }
    if {len(rows) for rows in selected.values()} != {expected}:
        raise ValueError("contextual router selected population mismatch")
    baseline_keys = {
        (row.symbol, row.entry_at)
        for row in selected[milestone.ProtectionMode.ORIGINAL.value]
    }
    for rows in selected.values():
        if {(row.symbol, row.entry_at) for row in rows} != baseline_keys:
            raise ValueError("contextual router mode identities differ")
    return selected


def _distribution(
    rows: tuple[milestone.SimulatedTrade, ...],
) -> tuple[Decimal, Decimal, Decimal]:
    if not rows:
        return Decimal("0"), Decimal("0"), Decimal("0")
    values = tuple(Decimal(row.realized_gross_r) for row in rows)
    negatives = tuple(-value for value in values if value < 0)
    mean_r = sum(values, Decimal("0")) / Decimal(len(values))
    negative_rate = Decimal(len(negatives)) / Decimal(len(values))
    downside = (
        Decimal("0")
        if not negatives
        else sum(negatives, Decimal("0")) / Decimal(len(negatives))
    )
    return mean_r, negative_rate, downside


def _utility(
    *,
    mean_r: Decimal,
    negative_rate: Decimal,
    downside: Decimal,
) -> Decimal:
    return (
        mean_r
        - NEGATIVE_RATE_WEIGHT * negative_rate
        - DOWNSIDE_WEIGHT * downside
    )


def _posterior(
    *,
    rows: tuple[milestone.SimulatedTrade, ...],
    global_rows: tuple[milestone.SimulatedTrade, ...],
) -> tuple[Decimal, Decimal, Decimal]:
    global_mean, global_negative, global_downside = _distribution(global_rows)
    if not rows:
        return global_mean, global_negative, global_downside
    mean_r, negative_rate, downside = _distribution(rows)
    n = Decimal(len(rows))
    denom = PRIOR_STRENGTH + n
    return (
        (PRIOR_STRENGTH * global_mean + n * mean_r) / denom,
        (PRIOR_STRENGTH * global_negative + n * negative_rate) / denom,
        (PRIOR_STRENGTH * global_downside + n * downside) / denom,
    )


def _hierarchy_keys(
    row: context.NativeContextRow,
) -> tuple[tuple[str, tuple[str, ...], int], ...]:
    return (
        (
            "SYMBOL_CONTEXT",
            (row.symbol, row.context_signature),
            MIN_SYMBOL_CONTEXT,
        ),
        (
            "SYMBOL_REGIME",
            (row.symbol, row.regime_signature),
            MIN_SYMBOL_REGIME,
        ),
        (
            "SYMBOL_DESTINATION",
            (row.symbol, row.destination_state),
            MIN_SYMBOL_DESTINATION,
        ),
        (
            "SYMBOL",
            (row.symbol,),
            MIN_SYMBOL,
        ),
        ("GLOBAL", ("GLOBAL",), 1),
    )


def _memberships(
    contexts: dict[tuple[str, str], context.NativeContextRow],
    baseline: tuple[milestone.SimulatedTrade, ...],
) -> dict[tuple[str, tuple[str, ...]], set[tuple[str, str]]]:
    result: dict[tuple[str, tuple[str, ...]], set[tuple[str, str]]] = defaultdict(set)
    for trade in baseline:
        key = (trade.symbol, trade.entry_at)
        row = contexts.get(key)
        if row is None:
            raise ValueError(f"missing development context for {key}")
        for level, values, _minimum in _hierarchy_keys(row):
            result[(level, values)].add(key)
    return result


def _freeze_model(
    *,
    development: dict[str, tuple[milestone.SimulatedTrade, ...]],
    contexts: dict[tuple[str, str], context.NativeContextRow],
) -> dict[str, Any]:
    baseline = development[milestone.ProtectionMode.ORIGINAL.value]
    memberships = _memberships(contexts, baseline)
    by_arm = {
        arm: {(row.symbol, row.entry_at): row for row in rows}
        for arm, rows in development.items()
    }
    global_by_arm = {
        arm: tuple(rows)
        for arm, rows in development.items()
    }

    cells: dict[str, dict[str, Any]] = {}
    for (level, values), keys in sorted(memberships.items()):
        support = len(keys)
        arm_rows: list[ArmPosterior] = []
        for arm in ARMS:
            selected_rows = tuple(by_arm[arm][key] for key in sorted(keys))
            mean_r, negative_rate, downside = _posterior(
                rows=selected_rows,
                global_rows=global_by_arm[arm],
            )
            arm_rows.append(
                ArmPosterior(
                    arm=arm,
                    support=support,
                    posterior_mean_r=str(mean_r),
                    posterior_negative_rate=str(negative_rate),
                    posterior_downside_r=str(downside),
                    utility=str(
                        _utility(
                            mean_r=mean_r,
                            negative_rate=negative_rate,
                            downside=downside,
                        )
                    ),
                )
            )
        chosen = max(
            arm_rows,
            key=lambda item: (
                Decimal(item.utility),
                Decimal(item.posterior_mean_r),
                -Decimal(item.posterior_negative_rate),
                -Decimal(item.posterior_downside_r),
                -ARMS.index(item.arm),
            ),
        )
        cell_id = json.dumps(
            {"level": level, "values": values},
            separators=(",", ":"),
            sort_keys=True,
        )
        cells[cell_id] = {
            "level": level,
            "values": values,
            "support": support,
            "selected_mode": chosen.arm,
            "arms": [asdict(item) for item in arm_rows],
        }

    return {
        "identity": "QORE_CAPITALIZER_CONTEXTUAL_ROUTER_FREEZE_V1",
        "source_role": "DEVELOPMENT_2024_2026",
        "prior_strength": str(PRIOR_STRENGTH),
        "negative_rate_weight": str(NEGATIVE_RATE_WEIGHT),
        "downside_weight": str(DOWNSIDE_WEIGHT),
        "minimum_support": {
            "SYMBOL_CONTEXT": MIN_SYMBOL_CONTEXT,
            "SYMBOL_REGIME": MIN_SYMBOL_REGIME,
            "SYMBOL_DESTINATION": MIN_SYMBOL_DESTINATION,
            "SYMBOL": MIN_SYMBOL,
            "GLOBAL": 1,
        },
        "arms": ARMS,
        "cells": cells,
        "validation_outcomes_visible_to_training": False,
        "automatic_promotion": False,
    }


def _lookup(
    model: dict[str, Any],
    row: context.NativeContextRow,
) -> tuple[str, str, int]:
    cells = model.get("cells")
    if not isinstance(cells, dict):
        raise ValueError("contextual model missing cells")
    for level, values, minimum in _hierarchy_keys(row):
        cell_id = json.dumps(
            {"level": level, "values": values},
            separators=(",", ":"),
            sort_keys=True,
        )
        cell = cells.get(cell_id)
        if not isinstance(cell, dict):
            continue
        support = int(cell["support"])
        if support >= minimum:
            return str(cell["selected_mode"]), level, support
    raise ValueError("contextual model missing GLOBAL fallback")


def _overlay(
    *,
    policy: str,
    base_mode: str,
    state: governor.StabilityState,
) -> tuple[str, bool]:
    if policy == "CONTEXT_ONLY":
        return base_mode, False
    if policy == "CONTEXT_DEFENSIVE_STAGE":
        if state is governor.StabilityState.DEFENSIVE:
            return milestone.ProtectionMode.STAGED_050_100_150.value, True
        return base_mode, False
    if policy == "CONTEXT_STABILITY_STAGE":
        if state is governor.StabilityState.DEFENSIVE:
            return milestone.ProtectionMode.STAGED_050_100_150.value, True
        if state is governor.StabilityState.WATCH:
            return milestone.ProtectionMode.STAGED_075_125_150.value, True
        return base_mode, False
    if policy == "CONTEXT_LOCK_STABILITY":
        if state is governor.StabilityState.DEFENSIVE:
            return milestone.ProtectionMode.STAGED_050_100_150.value, True
        if state is governor.StabilityState.WATCH:
            return milestone.ProtectionMode.LOCK025_AFTER_075.value, True
        return base_mode, False
    raise ValueError(f"unknown contextual policy: {policy}")


def _simulate(
    *,
    role: str,
    policy: str,
    ledgers: dict[str, tuple[milestone.SimulatedTrade, ...]],
    contexts: dict[tuple[str, str], context.NativeContextRow],
    model: dict[str, Any],
) -> tuple[dict[str, Any], tuple[ContextualDecision, ...]]:
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

    chosen: list[milestone.SimulatedTrade] = []
    decisions: list[ContextualDecision] = []
    level_counts: dict[str, int] = defaultdict(int)
    state_counts: dict[str, int] = defaultdict(int)
    mode_counts: dict[str, int] = defaultdict(int)

    for trade in ordered:
        key = (trade.symbol, trade.entry_at)
        ctx = contexts.get(key)
        if ctx is None:
            raise ValueError(f"missing {role} context for selected trade {key}")
        history = governor._closed_history(
            tuple(chosen),
            entry_at=direct._aware(trade.entry_at),
        )
        state, _equity, _peak, _dd, _loss_streak = governor._state(history)
        base_mode, level, support = _lookup(model, ctx)
        final_mode, overlay = _overlay(
            policy=policy,
            base_mode=base_mode,
            state=state,
        )
        selected = by_mode[final_mode][key]
        chosen.append(selected)
        level_counts[level] += 1
        state_counts[state.value] += 1
        mode_counts[final_mode] += 1

        decisions.append(
            ContextualDecision(
                role=role,
                policy=policy,
                symbol=trade.symbol,
                session=trade.session,
                operating_date=trade.operating_date,
                entry_at=trade.entry_at,
                regime_signature=ctx.regime_signature,
                destination_state=ctx.destination_state,
                context_signature=ctx.context_signature,
                hierarchy_level=level,
                hierarchy_support=support,
                learned_base_mode=base_mode,
                stability_state=state.value,
                final_mode=final_mode,
                overlay_applied=overlay,
            )
        )

    result = tuple(chosen)
    metrics = milestone._metrics(result)
    control = milestone._metrics(baseline)
    return {
        "role": role,
        "policy": policy,
        "trades": len(result),
        "density_retention": "1",
        "metrics": metrics,
        "control_metrics": control,
        "hierarchy_level_counts": dict(sorted(level_counts.items())),
        "stability_state_counts": dict(sorted(state_counts.items())),
        "final_mode_counts": dict(sorted(mode_counts.items())),
        "pf_at_least_control": (
            metrics["profit_factor"] is not None
            and control["profit_factor"] is not None
            and Decimal(str(metrics["profit_factor"]))
            >= Decimal(str(control["profit_factor"]))
        ),
        "total_r_at_least_control": (
            Decimal(str(metrics["total_r"]))
            >= Decimal(str(control["total_r"]))
        ),
        "dd_below_control": (
            Decimal(str(metrics["max_drawdown_r"]))
            < Decimal(str(control["max_drawdown_r"]))
        ),
        "dd_at_or_below_6r": (
            Decimal(str(metrics["max_drawdown_r"])) <= Decimal("6")
        ),
        "current_outcome_visible_to_decision": False,
        "validation_outcome_visible_to_training": False,
        "unchosen_counterfactual_visible_to_decision": False,
    }, tuple(decisions)


def build_report(
    development_root: Path,
    validation_root: Path,
    context_root: Path,
) -> tuple[dict[str, Any], dict[str, Any], tuple[ContextualDecision, ...]]:
    development = _load_selected(
        development_root,
        expected=EXPECTED_DEVELOPMENT_TRADES,
    )
    validation = _load_selected(
        validation_root,
        expected=EXPECTED_VALIDATION_TRADES,
    )
    dev_context = _load_contexts(context_root, role="dev")
    validation_context = _load_contexts(context_root, role="holdout")

    model = _freeze_model(
        development=development,
        contexts=dev_context,
    )

    results: list[dict[str, Any]] = []
    audits: list[ContextualDecision] = []
    for policy in POLICIES:
        dev_result, dev_audit = _simulate(
            role="DEVELOPMENT",
            policy=policy,
            ledgers=development,
            contexts=dev_context,
            model=model,
        )
        validation_result, validation_audit = _simulate(
            role="CONSUMED_VALIDATION_2022_2024",
            policy=policy,
            ledgers=validation,
            contexts=validation_context,
            model=model,
        )
        results.append(
            {
                "policy": policy,
                "development": dev_result,
                "validation": validation_result,
                "validation_pareto_vs_control": (
                    bool(validation_result["pf_at_least_control"])
                    and bool(validation_result["total_r_at_least_control"])
                    and bool(validation_result["dd_below_control"])
                ),
                "validation_dd6": bool(validation_result["dd_at_or_below_6r"]),
            }
        )
        audits.extend(dev_audit)
        audits.extend(validation_audit)

    pareto = tuple(row for row in results if row["validation_pareto_vs_control"])
    dd6 = tuple(
        row
        for row in results
        if row["validation_pareto_vs_control"] and row["validation_dd6"]
    )

    report = {
        "identity": IDENTITY,
        "source_direct_run_id": SOURCE_DIRECT_RUN_ID,
        "source_direct_sha": SOURCE_DIRECT_SHA,
        "source_context_run_id": SOURCE_CONTEXT_RUN_ID,
        "source_context_sha": SOURCE_CONTEXT_SHA,
        "development_role": "CONSUMED_RESEARCH_2024_2026",
        "validation_role": "CONSUMED_VALIDATION_2022_2024",
        "validation_is_fresh_holdout": False,
        "development_trades": EXPECTED_DEVELOPMENT_TRADES,
        "validation_trades": EXPECTED_VALIDATION_TRADES,
        "arm_count": len(ARMS),
        "policy_count": len(POLICIES),
        "results": results,
        "validation_pareto_policy_count": len(pareto),
        "validation_pareto_dd6_policy_count": len(dd6),
        "all_entries_preserved": True,
        "model_trained_on_development_only": True,
        "validation_outcomes_visible_to_training": False,
        "current_trade_outcome_visible_to_decision": False,
        "unchosen_counterfactual_visible_to_decision": False,
        "regime_context_provider_native": True,
        "destination_uses_confirmed_h1_pivots_only": True,
        "strategy_rules_changed": False,
        "entry_geometry_changed": False,
        "original_stop_geometry_changed_at_entry": False,
        "target_changed": False,
        "max3_changed": False,
        "automatic_policy_promotion": False,
        "runtime_rule_selected": False,
        "trader_certified": False,
        "live_authorized": False,
        "real_capital_authorized": False,
        "next_phase": (
            "FREEZE_CONTEXTUAL_CANDIDATE_AND_OPEN_NEW_NONOVERLAPPING_HOLDOUT"
            if pareto
            else "FALSIFY_CONTEXT_GRANULARITY_AND_REBUILD_DESTINATION_STATE"
        ),
    }
    return report, model, tuple(audits)


def write_report(
    report: dict[str, Any],
    model: dict[str, Any],
    audits: tuple[ContextualDecision, ...],
    output: Path,
) -> None:
    output.mkdir(parents=True, exist_ok=True)
    (output / "capitalizer-contextual-stability-router-2r-v1.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (output / "capitalizer-contextual-router-freeze-v1.json").write_text(
        json.dumps(model, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    with (
        output / "capitalizer-contextual-stability-router-2r-v1-decisions.jsonl"
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
    report, model, audits = build_report(
        args.development_root,
        args.validation_root,
        args.context_root,
    )
    write_report(report, model, audits, args.output)
    print(json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    main()

"""Causal protection-mode survival router for Capitalizer.

V10-V15 falsified admission filtering as the primary DD solution. A capacity
audit showed that the existing causal protection modes, combined with the
already-frozen Surface exposure multipliers, are theoretically sufficient to
push every consumed window below 6R. The missing capability is therefore causal
selection of the protection mode, not more abstention.

V16 learns ONLY from DEVELOPMENT_2024_2026 counterfactual protection outcomes.
At runtime/OOS it sees no current outcome and no counterfactual outcome. It
routes every admitted trade to either its existing Surface mode or one of the
already-causal protection modes using a low-dimensional pre-entry state:
closed drawdown band, active failure-transition state, and frozen Surface risk
band.

Mode promotion inside a training cell is Pareto constrained: an alternate mode
must not worsen mean R, negative rate, mean loss severity, or lower-tail R
versus the Surface mode, and must strictly improve at least one dimension.
No weighted utility or retrospective market/session filter is used.

All entries, source grammar, fixed 2R target, original stop geometry, MAX3 and
Surface exposure multipliers are preserved.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass, replace
from decimal import Decimal
from pathlib import Path
from typing import Any

from qore.infrastructure.trader_lab import (
    capitalizer_adaptive_context_risk_governor_v1 as memory,
)
from qore.infrastructure.trader_lab import (
    capitalizer_causal_probe_ranker_v10 as v10,
)
from qore.infrastructure.trader_lab import (
    capitalizer_cognitive_r_milestone_protection_2r_v1 as milestone,
)
from qore.infrastructure.trader_lab import (
    capitalizer_factor_journey_probe_ranker_v11 as v11,
)
from qore.infrastructure.trader_lab import (
    capitalizer_failure_state_transition_survival_v15 as v15,
)
from qore.infrastructure.trader_lab import (
    capitalizer_max_recovery_direct_m1_replay_v1 as direct,
)
from qore.infrastructure.trader_lab import (
    capitalizer_sequence_failure_memory_abstention_v13 as v13,
)

IDENTITY = "QORE_CAPITALIZER_PROTECTION_MODE_SURVIVAL_ROUTER_V16"
SURFACE = "SURFACE"
DEVELOPMENT_PERIOD = v10.DEVELOPMENT_PERIOD
STRICT_OOS_PERIODS = v10.STRICT_OOS_PERIODS

ARMS = (
    SURFACE,
    *(mode.value for mode in milestone.ProtectionMode),
)
LEVELS = (
    ("EXACT", 24),
    ("STATE", 48),
    ("DD", 96),
    ("GLOBAL", 1),
)
POLICIES = ("SURFACE_CONTROL", "PARETO_SURVIVAL_ROUTER")


@dataclass(frozen=True, slots=True)
class ArmStats:
    support: int
    mean_r: str
    q20_r: str
    negative_rate: str
    mean_loss_severity_r: str


@dataclass(frozen=True, slots=True)
class FrozenCell:
    level: str
    key: tuple[str, ...]
    support: int
    selected_mode: str
    surface_stats: ArmStats
    selected_stats: ArmStats
    pareto_promoted: bool


@dataclass(frozen=True, slots=True)
class TrainingSample:
    exact_key: tuple[str, ...]
    state_key: tuple[str, ...]
    dd_key: tuple[str, ...]
    outcomes: dict[str, str]


@dataclass(frozen=True, slots=True)
class PendingOutcome:
    symbol: str
    entry_at: str
    exit_at: str
    normalized_realized_r: str
    snapshot: v15.StateSnapshot


@dataclass(frozen=True, slots=True)
class ModeDecision:
    period: str
    policy: str
    symbol: str
    session: str
    entry_at: str
    current_drawdown_r: str
    base_multiplier: str
    surface_mode: str
    selected_mode: str
    model_level: str
    model_key: tuple[str, ...]
    training_support: int
    failure_state: str
    dd_band: str
    risk_band: str
    current_outcome_visible_to_decision: bool = False
    oos_counterfactual_outcomes_visible_to_decision: bool = False


def _dd_band(value: Decimal) -> str:
    if value >= Decimal("4"):
        return "DD_GE4"
    if value >= Decimal("2"):
        return "DD_2_TO_4"
    return "DD_LT2"


def _risk_band(value: Decimal) -> str:
    if value <= Decimal("0.20"):
        return "RISK_020"
    if value <= Decimal("0.55"):
        return "RISK_035_055"
    return "RISK_HIGH"


def _failure_state(
    failure: v15.StateSnapshot | None,
    *,
    trade: milestone.SimulatedTrade,
    pre: v10.Pretrade,
) -> str:
    if failure is None:
        return "FAIL_NONE"
    novelty, _changed = v15._novelty(failure, trade=trade, pre=pre)
    return "FAIL_SAME" if novelty == 0 else "FAIL_NOVEL"


def _keys(
    *,
    current_dd: Decimal,
    base_multiplier: Decimal,
    failure_state: str,
) -> tuple[tuple[str, ...], tuple[str, ...], tuple[str, ...]]:
    dd = _dd_band(current_dd)
    risk = _risk_band(base_multiplier)
    return (
        (dd, failure_state, risk),
        (dd, failure_state),
        (dd,),
    )


def _stats(values: tuple[Decimal, ...]) -> ArmStats:
    if not values:
        raise ValueError("V16 arm stats require outcomes")
    ordered = sorted(values)
    q_index = max(0, ((len(ordered) * 20 + 99) // 100) - 1)
    negatives = tuple(-value for value in values if value < 0)
    mean = sum(values, Decimal("0")) / Decimal(len(values))
    negative_rate = Decimal(len(negatives)) / Decimal(len(values))
    loss_severity = (
        Decimal("0")
        if not negatives
        else sum(negatives, Decimal("0")) / Decimal(len(negatives))
    )
    return ArmStats(
        support=len(values),
        mean_r=str(mean),
        q20_r=str(ordered[q_index]),
        negative_rate=str(negative_rate),
        mean_loss_severity_r=str(loss_severity),
    )


def _dominates(candidate: ArmStats, surface: ArmStats) -> bool:
    c_mean = Decimal(candidate.mean_r)
    s_mean = Decimal(surface.mean_r)
    c_q20 = Decimal(candidate.q20_r)
    s_q20 = Decimal(surface.q20_r)
    c_neg = Decimal(candidate.negative_rate)
    s_neg = Decimal(surface.negative_rate)
    c_loss = Decimal(candidate.mean_loss_severity_r)
    s_loss = Decimal(surface.mean_loss_severity_r)
    weak = (
        c_mean >= s_mean
        and c_q20 >= s_q20
        and c_neg <= s_neg
        and c_loss <= s_loss
    )
    strict = (
        c_mean > s_mean
        or c_q20 > s_q20
        or c_neg < s_neg
        or c_loss < s_loss
    )
    return weak and strict


def _select_cell(
    *,
    level: str,
    key: tuple[str, ...],
    samples: tuple[TrainingSample, ...],
) -> FrozenCell:
    values = {
        arm: tuple(Decimal(sample.outcomes[arm]) for sample in samples)
        for arm in ARMS
    }
    stats = {arm: _stats(rows) for arm, rows in values.items()}
    surface = stats[SURFACE]
    eligible = tuple(
        arm
        for arm in ARMS
        if arm != SURFACE and _dominates(stats[arm], surface)
    )
    if not eligible:
        selected = SURFACE
    else:
        selected = max(
            eligible,
            key=lambda arm: (
                Decimal(stats[arm].q20_r),
                Decimal(stats[arm].mean_r),
                -Decimal(stats[arm].negative_rate),
                -Decimal(stats[arm].mean_loss_severity_r),
                -ARMS.index(arm),
            ),
        )
    return FrozenCell(
        level=level,
        key=key,
        support=len(samples),
        selected_mode=selected,
        surface_stats=surface,
        selected_stats=stats[selected],
        pareto_promoted=selected != SURFACE,
    )


def _fit_model(samples: tuple[TrainingSample, ...]) -> dict[str, FrozenCell]:
    cells: dict[str, FrozenCell] = {}
    specs = {
        "EXACT": lambda row: row.exact_key,
        "STATE": lambda row: row.state_key,
        "DD": lambda row: row.dd_key,
        "GLOBAL": lambda row: ("GLOBAL",),
    }
    minimums = dict(LEVELS)
    for level, getter in specs.items():
        grouped: dict[tuple[str, ...], list[TrainingSample]] = defaultdict(list)
        for sample in samples:
            grouped[getter(sample)].append(sample)
        for key, rows in grouped.items():
            if len(rows) < minimums[level]:
                continue
            cell = _select_cell(level=level, key=key, samples=tuple(rows))
            cell_id = json.dumps([level, list(key)], separators=(",", ":"))
            cells[cell_id] = cell
    if json.dumps(["GLOBAL", ["GLOBAL"]], separators=(",", ":")) not in cells:
        raise ValueError("V16 model missing GLOBAL fallback")
    return cells


def _lookup(
    model: dict[str, FrozenCell],
    *,
    exact_key: tuple[str, ...],
    state_key: tuple[str, ...],
    dd_key: tuple[str, ...],
) -> FrozenCell:
    for level, key in (
        ("EXACT", exact_key),
        ("STATE", state_key),
        ("DD", dd_key),
        ("GLOBAL", ("GLOBAL",)),
    ):
        cell_id = json.dumps([level, list(key)], separators=(",", ":"))
        cell = model.get(cell_id)
        if cell is not None:
            return cell
    raise ValueError("V16 model lookup missing GLOBAL fallback")


def _process_pending(
    pending: tuple[PendingOutcome, ...],
    processed: set[tuple[str, str]],
    *,
    entry_at: str,
    active_failure: v15.StateSnapshot | None,
) -> v15.StateSnapshot | None:
    current = direct._aware(entry_at)
    failure = active_failure
    for item in sorted(
        pending,
        key=lambda row: (direct._aware(row.exit_at), row.symbol),
    ):
        key = (item.symbol, item.entry_at)
        if key in processed or direct._aware(item.exit_at) > current:
            continue
        realized = Decimal(item.normalized_realized_r)
        if realized < 0:
            failure = item.snapshot
        elif (
            failure is not None
            and direct._aware(item.entry_at) > direct._aware(failure.exit_at)
        ):
            failure = None
        processed.add(key)
    return failure


def _training_samples(
    *,
    ledgers: dict[str, tuple[milestone.SimulatedTrade, ...]],
    contexts: dict[tuple[str, str], Any],
    contextual_model: dict[str, Any],
) -> tuple[TrainingSample, ...]:
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
    pending: list[PendingOutcome] = []
    processed: set[tuple[str, str]] = set()
    active_failure: v15.StateSnapshot | None = None
    samples: list[TrainingSample] = []

    for trade in ordered:
        active_failure = _process_pending(
            tuple(pending),
            processed,
            entry_at=trade.entry_at,
            active_failure=active_failure,
        )
        pre = v11._pretrade(
            period=DEVELOPMENT_PERIOD,
            trade=trade,
            contexts=contexts,
            contextual_model=contextual_model,
            chosen_scaled=tuple(chosen),
            records=tuple(records),
        )
        failure = _failure_state(active_failure, trade=trade, pre=pre)
        exact, state, dd = _keys(
            current_dd=pre.current_dd,
            base_multiplier=pre.base_multiplier,
            failure_state=failure,
        )
        key = (trade.symbol, trade.entry_at)
        surface = by_mode[pre.mode][key]
        outcomes = {
            SURFACE: surface.realized_gross_r,
            **{
                mode.value: by_mode[mode.value][key].realized_gross_r
                for mode in milestone.ProtectionMode
            },
        }
        samples.append(
            TrainingSample(
                exact_key=exact,
                state_key=state,
                dd_key=dd,
                outcomes=outcomes,
            )
        )

        scaled = replace(
            surface,
            realized_gross_r=str(
                Decimal(surface.realized_gross_r) * pre.base_multiplier
            ),
        )
        chosen.append(scaled)
        records.append(
            memory.MemoryRecord(
                symbol=pre.ctx.symbol,
                session=pre.ctx.session,
                destination_state=pre.ctx.destination_state,
                context_signature=pre.ctx.context_signature,
                exit_at=surface.exit_at,
                normalized_realized_r=surface.realized_gross_r,
            )
        )
        pending.append(
            PendingOutcome(
                symbol=trade.symbol,
                entry_at=trade.entry_at,
                exit_at=surface.exit_at,
                normalized_realized_r=surface.realized_gross_r,
                snapshot=v15._snapshot(
                    trade=trade,
                    pre=pre,
                    exit_at=surface.exit_at,
                    exit_reason=surface.exit_reason,
                ),
            )
        )
    return tuple(samples)


def _simulate(
    *,
    period: str,
    policy: str,
    ledgers: dict[str, tuple[milestone.SimulatedTrade, ...]],
    contexts: dict[tuple[str, str], Any],
    contextual_model: dict[str, Any],
    model: dict[str, FrozenCell],
) -> tuple[dict[str, Any], tuple[ModeDecision, ...]]:
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
    pending: list[PendingOutcome] = []
    processed: set[tuple[str, str]] = set()
    active_failure: v15.StateSnapshot | None = None
    decisions: list[ModeDecision] = []
    mode_counts: Counter[str] = Counter()

    for trade in ordered:
        active_failure = _process_pending(
            tuple(pending),
            processed,
            entry_at=trade.entry_at,
            active_failure=active_failure,
        )
        pre = v11._pretrade(
            period=period,
            trade=trade,
            contexts=contexts,
            contextual_model=contextual_model,
            chosen_scaled=tuple(chosen),
            records=tuple(records),
        )
        failure = _failure_state(active_failure, trade=trade, pre=pre)
        exact, state, dd = _keys(
            current_dd=pre.current_dd,
            base_multiplier=pre.base_multiplier,
            failure_state=failure,
        )
        cell = _lookup(model, exact_key=exact, state_key=state, dd_key=dd)
        selected_mode = (
            pre.mode
            if policy == "SURFACE_CONTROL" or cell.selected_mode == SURFACE
            else cell.selected_mode
        )

        key = (trade.symbol, trade.entry_at)
        unscaled = by_mode[selected_mode][key]
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
        pending.append(
            PendingOutcome(
                symbol=trade.symbol,
                entry_at=trade.entry_at,
                exit_at=unscaled.exit_at,
                normalized_realized_r=unscaled.realized_gross_r,
                snapshot=v15._snapshot(
                    trade=trade,
                    pre=pre,
                    exit_at=unscaled.exit_at,
                    exit_reason=unscaled.exit_reason,
                ),
            )
        )
        mode_counts[selected_mode] += 1
        decisions.append(
            ModeDecision(
                period=period,
                policy=policy,
                symbol=trade.symbol,
                session=trade.session,
                entry_at=trade.entry_at,
                current_drawdown_r=str(pre.current_dd),
                base_multiplier=str(pre.base_multiplier),
                surface_mode=pre.mode,
                selected_mode=selected_mode,
                model_level=cell.level,
                model_key=cell.key,
                training_support=cell.support,
                failure_state=failure,
                dd_band=dd[0],
                risk_band=exact[2],
            )
        )

    ledger = tuple(chosen)
    return {
        "period": period,
        "policy": policy,
        "trades": len(ledger),
        "density_retention": "1",
        "metrics": milestone._metrics(ledger),
        "mode_counts": dict(sorted(mode_counts.items())),
        "mode_switches": sum(
            row.selected_mode != row.surface_mode for row in decisions
        ),
    }, tuple(decisions)


def build_report(
    development_root: Path,
    validation_root: Path,
    reserved_root: Path,
    development_validation_context_root: Path,
    reserved_context_root: Path,
) -> tuple[dict[str, Any], tuple[ModeDecision, ...]]:
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
        development, dev_contexts = windows[DEVELOPMENT_PERIOD]
        samples = _training_samples(
            ledgers=development,
            contexts=dev_contexts,
            contextual_model=contextual_model,
        )
        model = _fit_model(samples)

        controls: dict[str, dict[str, Any]] = {}
        audits: list[ModeDecision] = []
        for period, (ledgers, contexts) in windows.items():
            control, audit = _simulate(
                period=period,
                policy="SURFACE_CONTROL",
                ledgers=ledgers,
                contexts=contexts,
                contextual_model=contextual_model,
                model=model,
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
                        model=model,
                    )
                    audits.extend(audit)
                v10._annotate(current, controls[period])
                current["losing_streak_not_worse"] = (
                    int(current["metrics"]["max_losing_streak"])
                    <= int(controls[period]["metrics"]["max_losing_streak"])
                )
                heldouts[period] = current

            all_full = all(
                row["pf_at_least_surface_control"]
                and row["total_r_at_least_surface_control"]
                and row["dd_below_surface_control"]
                and row["losing_streak_not_worse"]
                and row["dd_at_or_below_6r"]
                for row in heldouts.values()
            )
            strict_oos_full = all(
                heldouts[period]["pf_at_least_surface_control"]
                and heldouts[period]["total_r_at_least_surface_control"]
                and heldouts[period]["dd_below_surface_control"]
                and heldouts[period]["losing_streak_not_worse"]
                and heldouts[period]["dd_at_or_below_6r"]
                for period in STRICT_OOS_PERIODS
            )
            results.append(
                {
                    "policy": policy,
                    "heldouts": heldouts,
                    "all_consumed_full_gate": all_full,
                    "strict_oos_full_gate": strict_oos_full,
                }
            )
    finally:
        v11._SIMULTANEOUS.clear()
        v11._SIMULTANEOUS.update(previous)

    promoted_cells = tuple(cell for cell in model.values() if cell.pareto_promoted)
    candidates = tuple(
        row
        for row in results
        if row["policy"] != "SURFACE_CONTROL"
        and row["all_consumed_full_gate"]
        and row["strict_oos_full_gate"]
    )
    return {
        "identity": IDENTITY,
        "evaluation": "DEVELOPMENT_FROZEN_PARETO_PROTECTION_MODE_ROUTER",
        "development_period": DEVELOPMENT_PERIOD,
        "strict_oos_periods": list(STRICT_OOS_PERIODS),
        "training_samples": len(samples),
        "frozen_cell_count": len(model),
        "pareto_promoted_cell_count": len(promoted_cells),
        "model_cells": {
            key: asdict(cell) for key, cell in sorted(model.items())
        },
        "results": results,
        "candidate_count": len(candidates),
        "all_entries_preserved": True,
        "density_retention": "1",
        "surface_exposure_multipliers_preserved": True,
        "original_stop_geometry_preserved": True,
        "target_r": "2.00",
        "max3_preserved": True,
        "development_counterfactual_modes_used_for_training_only": True,
        "oos_counterfactual_modes_visible_to_decision": False,
        "current_outcome_visible_to_decision": False,
        "market_session_retrospective_filters_used": False,
        "weighted_utility_used": False,
        "pareto_dominance_required_for_mode_promotion": True,
        "automatic_policy_promotion": False,
        "trader_certified": False,
        "live_authorized": False,
        "real_capital_authorized": False,
        "next_phase": (
            "FREEZE_V16_THEN_OPEN_2018_2020_FRESH_HOLDOUT"
            if candidates
            else "BUILD_INTRATRADE_HYPOTHESIS_INVALIDATION_V17"
        ),
    }, tuple(audits)


def write_report(
    report: dict[str, Any],
    audits: tuple[ModeDecision, ...],
    output: Path,
) -> None:
    output.mkdir(parents=True, exist_ok=True)
    (output / "capitalizer-protection-mode-survival-router-v16.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    with (
        output / "capitalizer-protection-mode-survival-router-v16-decisions.jsonl"
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

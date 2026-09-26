"""Cross-period Position-Intelligence survival for Capitalizer recovery probes.

V13-V15 show that selective abstention does not solve the residual drawdown
without either starving recovery or discarding edge. V16 preserves every entry
and every Surface risk multiplier. It changes only the protection mode used by
recovery-state trades when independent OTHER-period evidence agrees on the same
more-survivable position-management arm.

For each scored period, each of the other two consumed periods independently
evaluates the same predeclared protection arms on recovery-state trades. An arm
is eligible only if it dominates that period's contextual-control outcomes on
mean R, negative rate and downside. The scored period contributes no labels to
arm selection. Runtime selection never reads an unchosen counterfactual.

This is still consumed research. A rule can only proceed if the SAME arm is
selected across all folds and the full economic envelope passes before opening
the sealed 2018-2020 holdout.
"""

from __future__ import annotations

import argparse
import json
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
    capitalizer_max_recovery_direct_m1_replay_v1 as direct,
)
from qore.infrastructure.trader_lab import (
    capitalizer_sequence_failure_memory_abstention_v13 as v13,
)

IDENTITY = "QORE_CAPITALIZER_RECOVERY_PROBE_POSITION_SURVIVAL_V16"
ARMS = (
    milestone.ProtectionMode.BE_AFTER_075.value,
    milestone.ProtectionMode.LOCK025_AFTER_100.value,
    milestone.ProtectionMode.STAGED_050_100_150.value,
    milestone.ProtectionMode.STAGED_075_125_150.value,
)
POLICY_DD = {
    "SURVIVAL_DD3": Decimal("3"),
    "SURVIVAL_DD4": Decimal("4"),
    "SURVIVAL_DD5": Decimal("5"),
}
POLICIES = ("SURFACE_CONTROL", *POLICY_DD)
MAX_BASE_MULTIPLIER = Decimal("0.35")
MIN_SUPPORT = 30


@dataclass(frozen=True, slots=True)
class ArmStats:
    arm: str
    support: int
    mean_r: str
    negative_rate: str
    downside_r: str
    control_mean_r: str
    control_negative_rate: str
    control_downside_r: str
    dominates_control: bool


@dataclass(frozen=True, slots=True)
class PeriodArmModel:
    period: str
    dd_trigger_r: str
    recovery_support: int
    selected_arm: str | None
    arms: tuple[ArmStats, ...]


@dataclass(frozen=True, slots=True)
class SurvivalDecision:
    period: str
    policy: str
    symbol: str
    session: str
    entry_at: str
    current_drawdown_r: str
    base_multiplier: str
    base_mode: str
    selected_survival_arm: str | None
    final_mode: str
    recovery_state: bool
    override_applied: bool
    training_periods: tuple[str, str] | None
    current_outcome_visible_to_decision: bool = False
    scored_period_outcomes_visible_to_arm_selection: bool = False
    runtime_unchosen_counterfactual_visible: bool = False


def _stats(values: tuple[Decimal, ...]) -> tuple[Decimal, Decimal, Decimal]:
    if not values:
        return Decimal("0"), Decimal("1"), Decimal("0")
    mean = sum(values, Decimal("0")) / Decimal(len(values))
    negative = Decimal(sum(value < 0 for value in values)) / Decimal(len(values))
    downside = (
        sum((-value for value in values if value < 0), Decimal("0"))
        / Decimal(len(values))
    )
    return mean, negative, downside


def _collect_training(
    *,
    period: str,
    dd_trigger: Decimal,
    ledgers: dict[str, tuple[milestone.SimulatedTrade, ...]],
    contexts: dict[tuple[str, str], Any],
    contextual_model: dict[str, Any],
) -> PeriodArmModel:
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
    control_values: list[Decimal] = []
    arm_values: dict[str, list[Decimal]] = {arm: [] for arm in ARMS}

    for trade in ordered:
        pre = v11._pretrade(
            period=period,
            trade=trade,
            contexts=contexts,
            contextual_model=contextual_model,
            chosen_scaled=tuple(chosen),
            records=tuple(records),
        )
        key = (trade.symbol, trade.entry_at)
        control = by_mode[pre.mode][key]
        recovery = (
            pre.current_dd >= dd_trigger
            and pre.base_multiplier <= MAX_BASE_MULTIPLIER
        )
        if recovery:
            control_values.append(Decimal(control.realized_gross_r))
            for arm in ARMS:
                arm_values[arm].append(
                    Decimal(by_mode[arm][key].realized_gross_r)
                )

        scaled = replace(
            control,
            realized_gross_r=str(
                Decimal(control.realized_gross_r) * pre.base_multiplier
            ),
        )
        chosen.append(scaled)
        records.append(
            memory.MemoryRecord(
                symbol=pre.ctx.symbol,
                session=pre.ctx.session,
                destination_state=pre.ctx.destination_state,
                context_signature=pre.ctx.context_signature,
                exit_at=control.exit_at,
                normalized_realized_r=control.realized_gross_r,
            )
        )

    control_tuple = tuple(control_values)
    c_mean, c_neg, c_down = _stats(control_tuple)
    rows: list[ArmStats] = []
    for arm in ARMS:
        values = tuple(arm_values[arm])
        mean, neg, down = _stats(values)
        dominates = (
            len(values) >= MIN_SUPPORT
            and mean >= c_mean
            and neg <= c_neg
            and down <= c_down
            and (
                mean > c_mean
                or neg < c_neg
                or down < c_down
            )
        )
        rows.append(
            ArmStats(
                arm=arm,
                support=len(values),
                mean_r=str(mean),
                negative_rate=str(neg),
                downside_r=str(down),
                control_mean_r=str(c_mean),
                control_negative_rate=str(c_neg),
                control_downside_r=str(c_down),
                dominates_control=dominates,
            )
        )

    eligible = tuple(row for row in rows if row.dominates_control)
    selected = None
    if eligible:
        selected = max(
            eligible,
            key=lambda row: (
                Decimal(row.mean_r),
                -Decimal(row.negative_rate),
                -Decimal(row.downside_r),
                -ARMS.index(row.arm),
            ),
        ).arm
    return PeriodArmModel(
        period=period,
        dd_trigger_r=str(dd_trigger),
        recovery_support=len(control_values),
        selected_arm=selected,
        arms=tuple(rows),
    )


def _pair_consensus(
    left: PeriodArmModel,
    right: PeriodArmModel,
) -> str | None:
    if left.selected_arm is None or right.selected_arm is None:
        return None
    if left.selected_arm != right.selected_arm:
        return None
    return left.selected_arm


def _simulate(
    *,
    period: str,
    policy: str,
    dd_trigger: Decimal | None,
    selected_arm: str | None,
    training_periods: tuple[str, str] | None,
    ledgers: dict[str, tuple[milestone.SimulatedTrade, ...]],
    contexts: dict[tuple[str, str], Any],
    contextual_model: dict[str, Any],
) -> tuple[dict[str, Any], tuple[SurvivalDecision, ...]]:
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
    decisions: list[SurvivalDecision] = []
    override_count = 0

    for trade in ordered:
        pre = v11._pretrade(
            period=period,
            trade=trade,
            contexts=contexts,
            contextual_model=contextual_model,
            chosen_scaled=tuple(chosen),
            records=tuple(records),
        )
        recovery = (
            dd_trigger is not None
            and pre.current_dd >= dd_trigger
            and pre.base_multiplier <= MAX_BASE_MULTIPLIER
        )
        final_mode = pre.mode
        override = recovery and selected_arm is not None
        if override:
            final_mode = selected_arm
            override_count += 1

        key = (trade.symbol, trade.entry_at)
        unscaled = by_mode[final_mode][key]
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
        decisions.append(
            SurvivalDecision(
                period=period,
                policy=policy,
                symbol=trade.symbol,
                session=trade.session,
                entry_at=trade.entry_at,
                current_drawdown_r=str(pre.current_dd),
                base_multiplier=str(pre.base_multiplier),
                base_mode=pre.mode,
                selected_survival_arm=selected_arm,
                final_mode=final_mode,
                recovery_state=recovery,
                override_applied=override,
                training_periods=training_periods,
            )
        )

    ledger = tuple(chosen)
    return {
        "period": period,
        "policy": policy,
        "trades": len(ledger),
        "density_retention": "1",
        "metrics": milestone._metrics(ledger),
        "selected_survival_arm": selected_arm,
        "override_count": override_count,
    }, tuple(decisions)


def build_report(
    development_root: Path,
    validation_root: Path,
    reserved_root: Path,
    development_validation_context_root: Path,
    reserved_context_root: Path,
) -> tuple[dict[str, Any], tuple[SurvivalDecision, ...]]:
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
        audits: list[SurvivalDecision] = []
        for period, (ledgers, contexts) in windows.items():
            control, audit = _simulate(
                period=period,
                policy="SURFACE_CONTROL",
                dd_trigger=None,
                selected_arm=None,
                training_periods=None,
                ledgers=ledgers,
                contexts=contexts,
                contextual_model=contextual_model,
            )
            controls[period] = control
            audits.extend(audit)

        results: list[dict[str, Any]] = []
        for policy, dd_trigger in POLICY_DD.items():
            models = {
                period: _collect_training(
                    period=period,
                    dd_trigger=dd_trigger,
                    ledgers=ledgers,
                    contexts=contexts,
                    contextual_model=contextual_model,
                )
                for period, (ledgers, contexts) in windows.items()
            }
            heldouts: dict[str, Any] = {}
            selected_by_fold: dict[str, str | None] = {}
            model_diagnostics: dict[str, Any] = {}
            for heldout, (ledgers, contexts) in windows.items():
                training = tuple(period for period in windows if period != heldout)
                left, right = models[training[0]], models[training[1]]
                selected = _pair_consensus(left, right)
                selected_by_fold[heldout] = selected
                model_diagnostics[heldout] = {
                    "training_periods": list(training),
                    "models": [asdict(left), asdict(right)],
                }
                current, audit = _simulate(
                    period=heldout,
                    policy=policy,
                    dd_trigger=dd_trigger,
                    selected_arm=selected,
                    training_periods=(training[0], training[1]),
                    ledgers=ledgers,
                    contexts=contexts,
                    contextual_model=contextual_model,
                )
                audits.extend(audit)
                v10._annotate(current, controls[heldout])
                heldouts[heldout] = current

            arms = tuple(
                arm for arm in selected_by_fold.values() if arm is not None
            )
            same_arm_all_folds = (
                len(arms) == len(windows)
                and len(set(arms)) == 1
            )
            full_gate = all(
                row["pf_at_least_surface_control"]
                and row["total_r_at_least_surface_control"]
                and row["dd_below_surface_control"]
                for row in heldouts.values()
            )
            all_dd6 = all(row["dd_at_or_below_6r"] for row in heldouts.values())
            results.append(
                {
                    "policy": policy,
                    "dd_trigger_r": str(dd_trigger),
                    "heldouts": heldouts,
                    "selected_arm_by_fold": selected_by_fold,
                    "same_arm_all_folds": same_arm_all_folds,
                    "model_diagnostics": model_diagnostics,
                    "all_consumed_full_gate": full_gate,
                    "all_consumed_dd6": all_dd6,
                }
            )

        candidates = tuple(
            row
            for row in results
            if row["same_arm_all_folds"]
            and row["all_consumed_full_gate"]
            and row["all_consumed_dd6"]
        )
    finally:
        v11._SIMULTANEOUS.clear()
        v11._SIMULTANEOUS.update(previous)

    return {
        "identity": IDENTITY,
        "evaluation": "DUAL_PERIOD_RECOVERY_POSITION_SURVIVAL",
        "arms": list(ARMS),
        "minimum_training_support": MIN_SUPPORT,
        "max_recovery_base_multiplier": str(MAX_BASE_MULTIPLIER),
        "results": results,
        "candidate_count": len(candidates),
        "all_entries_preserved": True,
        "density_retention": "1",
        "surface_risk_multiplier_preserved": True,
        "scored_period_outcomes_visible_to_arm_selection": False,
        "training_counterfactuals_only_from_other_periods": True,
        "runtime_unchosen_counterfactual_visible": False,
        "current_outcome_visible_to_decision": False,
        "same_arm_required_across_all_folds": True,
        "full_source_recompetition_required_before_freeze": False,
        "target_r": "2.00",
        "max3_ceiling_preserved": True,
        "automatic_policy_promotion": False,
        "trader_certified": False,
        "live_authorized": False,
        "real_capital_authorized": False,
        "next_phase": (
            "FREEZE_V16_ARM_THEN_OPEN_2018_2020_FRESH_HOLDOUT"
            if candidates
            else "BUILD_RECOVERY_MODE_MIXTURE_V17"
        ),
    }, tuple(audits)


def write_report(
    report: dict[str, Any],
    audits: tuple[SurvivalDecision, ...],
    output: Path,
) -> None:
    output.mkdir(parents=True, exist_ok=True)
    (output / "capitalizer-recovery-probe-position-survival-v16.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    with (
        output / "capitalizer-recovery-probe-position-survival-v16-decisions.jsonl"
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

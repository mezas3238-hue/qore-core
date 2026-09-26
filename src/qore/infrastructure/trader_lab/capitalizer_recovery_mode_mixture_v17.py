"""Cross-period contextual recovery-mode mixture for Capitalizer.

V16 falsified one global recovery protection arm. V17 keeps all entries and
Surface sizing unchanged, but allows Position Intelligence to vary by causal
recovery context.

Each training period independently selects an arm only inside predeclared
hierarchical cells and only when that arm dominates the local contextual
control on mean R, negative rate and downside with minimum support. At runtime,
a scored trade may switch protection mode only when BOTH other-period models
independently resolve the trade and choose the SAME arm.

The scored period contributes no labels to its mixture. Runtime never reads an
unchosen counterfactual. The fresh 2018-2020 holdout stays sealed unless the
same frozen mixture contract passes all consumed economic gates.
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
    capitalizer_recovery_probe_position_survival_v16 as v16,
)
from qore.infrastructure.trader_lab import (
    capitalizer_sequence_failure_memory_abstention_v13 as v13,
)

IDENTITY = "QORE_CAPITALIZER_RECOVERY_MODE_MIXTURE_V17"
ARMS = v16.ARMS
POLICY_DD = v16.POLICY_DD
POLICIES = ("SURFACE_CONTROL", *POLICY_DD)
MAX_BASE_MULTIPLIER = v16.MAX_BASE_MULTIPLIER

MIN_SUPPORT = {
    "CONTEXT": 12,
    "DEST_VOL": 18,
    "DEST_ALIGN": 18,
    "DEST": 24,
}


@dataclass(frozen=True, slots=True)
class CellChoice:
    level: str
    values: tuple[str, ...]
    support: int
    selected_arm: str | None
    control_mean_r: str
    control_negative_rate: str
    control_downside_r: str


@dataclass(frozen=True, slots=True)
class PeriodMixtureModel:
    period: str
    dd_trigger_r: str
    recovery_support: int
    cells: dict[str, CellChoice]


@dataclass(frozen=True, slots=True)
class MixtureDecision:
    period: str
    policy: str
    symbol: str
    session: str
    entry_at: str
    current_drawdown_r: str
    base_multiplier: str
    base_mode: str
    left_arm: str | None
    right_arm: str | None
    left_level: str | None
    right_level: str | None
    final_mode: str
    recovery_state: bool
    override_applied: bool
    training_periods: tuple[str, str] | None
    current_outcome_visible_to_decision: bool = False
    scored_period_outcomes_visible_to_mixture: bool = False
    runtime_unchosen_counterfactual_visible: bool = False


def _cell_specs(ctx: Any) -> tuple[tuple[str, tuple[str, ...]], ...]:
    return (
        ("CONTEXT", (ctx.context_signature,)),
        ("DEST_VOL", (ctx.destination_state, ctx.volatility_state)),
        (
            "DEST_ALIGN",
            (
                ctx.destination_state,
                ctx.m15_slope_alignment,
                ctx.h1_body_alignment,
            ),
        ),
        ("DEST", (ctx.destination_state,)),
    )


def _cell_id(level: str, values: tuple[str, ...]) -> str:
    return json.dumps(
        {"level": level, "values": values},
        separators=(",", ":"),
        sort_keys=True,
    )


def _dominates(
    *,
    control_values: tuple[Decimal, ...],
    arm_values: tuple[Decimal, ...],
    minimum: int,
) -> bool:
    if len(control_values) < minimum or len(arm_values) != len(control_values):
        return False
    c_mean, c_neg, c_down = v16._stats(control_values)
    a_mean, a_neg, a_down = v16._stats(arm_values)
    return (
        a_mean >= c_mean
        and a_neg <= c_neg
        and a_down <= c_down
        and (a_mean > c_mean or a_neg < c_neg or a_down < c_down)
    )


def _fit_model(
    *,
    period: str,
    dd_trigger: Decimal,
    ledgers: dict[str, tuple[milestone.SimulatedTrade, ...]],
    contexts: dict[tuple[str, str], Any],
    contextual_model: dict[str, Any],
) -> PeriodMixtureModel:
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
    control_cells: dict[str, list[Decimal]] = defaultdict(list)
    arm_cells: dict[tuple[str, str], list[Decimal]] = defaultdict(list)
    meta: dict[str, tuple[str, tuple[str, ...]]] = {}
    recovery_support = 0

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
            recovery_support += 1
            for level, values in _cell_specs(pre.ctx):
                cid = _cell_id(level, values)
                meta[cid] = (level, values)
                control_cells[cid].append(Decimal(control.realized_gross_r))
                for arm in ARMS:
                    arm_cells[(cid, arm)].append(
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

    cells: dict[str, CellChoice] = {}
    for cid, controls_list in control_cells.items():
        level, values = meta[cid]
        controls = tuple(controls_list)
        c_mean, c_neg, c_down = v16._stats(controls)
        eligible: list[tuple[str, Decimal, Decimal, Decimal]] = []
        for arm in ARMS:
            arm_values = tuple(arm_cells[(cid, arm)])
            if not _dominates(
                control_values=controls,
                arm_values=arm_values,
                minimum=MIN_SUPPORT[level],
            ):
                continue
            a_mean, a_neg, a_down = v16._stats(arm_values)
            eligible.append((arm, a_mean, a_neg, a_down))
        selected = None
        if eligible:
            selected = max(
                eligible,
                key=lambda row: (
                    row[1],
                    -row[2],
                    -row[3],
                    -ARMS.index(row[0]),
                ),
            )[0]
        cells[cid] = CellChoice(
            level=level,
            values=values,
            support=len(controls),
            selected_arm=selected,
            control_mean_r=str(c_mean),
            control_negative_rate=str(c_neg),
            control_downside_r=str(c_down),
        )

    return PeriodMixtureModel(
        period=period,
        dd_trigger_r=str(dd_trigger),
        recovery_support=recovery_support,
        cells=cells,
    )


def _lookup(
    model: PeriodMixtureModel,
    ctx: Any,
) -> tuple[str | None, str | None]:
    for level, values in _cell_specs(ctx):
        cell = model.cells.get(_cell_id(level, values))
        if cell is None or cell.support < MIN_SUPPORT[level]:
            continue
        if cell.selected_arm is not None:
            return cell.selected_arm, level
    return None, None


def _simulate(
    *,
    period: str,
    policy: str,
    dd_trigger: Decimal | None,
    models: tuple[PeriodMixtureModel, PeriodMixtureModel] | None,
    ledgers: dict[str, tuple[milestone.SimulatedTrade, ...]],
    contexts: dict[tuple[str, str], Any],
    contextual_model: dict[str, Any],
) -> tuple[dict[str, Any], tuple[MixtureDecision, ...]]:
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
    decisions: list[MixtureDecision] = []
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
        left_arm: str | None = None
        right_arm: str | None = None
        left_level: str | None = None
        right_level: str | None = None
        final_mode = pre.mode
        override = False
        training_periods: tuple[str, str] | None = None

        if recovery and models is not None:
            left_arm, left_level = _lookup(models[0], pre.ctx)
            right_arm, right_level = _lookup(models[1], pre.ctx)
            training_periods = (models[0].period, models[1].period)
            if left_arm is not None and left_arm == right_arm:
                final_mode = left_arm
                override = True
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
            MixtureDecision(
                period=period,
                policy=policy,
                symbol=trade.symbol,
                session=trade.session,
                entry_at=trade.entry_at,
                current_drawdown_r=str(pre.current_dd),
                base_multiplier=str(pre.base_multiplier),
                base_mode=pre.mode,
                left_arm=left_arm,
                right_arm=right_arm,
                left_level=left_level,
                right_level=right_level,
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
        "override_count": override_count,
    }, tuple(decisions)


def build_report(
    development_root: Path,
    validation_root: Path,
    reserved_root: Path,
    development_validation_context_root: Path,
    reserved_context_root: Path,
) -> tuple[dict[str, Any], tuple[MixtureDecision, ...]]:
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
        audits: list[MixtureDecision] = []
        for period, (ledgers, contexts) in windows.items():
            control, audit = _simulate(
                period=period,
                policy="SURFACE_CONTROL",
                dd_trigger=None,
                models=None,
                ledgers=ledgers,
                contexts=contexts,
                contextual_model=contextual_model,
            )
            controls[period] = control
            audits.extend(audit)

        results: list[dict[str, Any]] = []
        for policy, dd_trigger in POLICY_DD.items():
            fitted = {
                period: _fit_model(
                    period=period,
                    dd_trigger=dd_trigger,
                    ledgers=ledgers,
                    contexts=contexts,
                    contextual_model=contextual_model,
                )
                for period, (ledgers, contexts) in windows.items()
            }
            heldouts: dict[str, Any] = {}
            diagnostics: dict[str, Any] = {}
            for heldout, (ledgers, contexts) in windows.items():
                training = tuple(period for period in windows if period != heldout)
                pair = (fitted[training[0]], fitted[training[1]])
                diagnostics[heldout] = {
                    "training_periods": list(training),
                    "left_recovery_support": pair[0].recovery_support,
                    "right_recovery_support": pair[1].recovery_support,
                    "left_selected_cell_count": sum(
                        row.selected_arm is not None for row in pair[0].cells.values()
                    ),
                    "right_selected_cell_count": sum(
                        row.selected_arm is not None for row in pair[1].cells.values()
                    ),
                }
                current, audit = _simulate(
                    period=heldout,
                    policy=policy,
                    dd_trigger=dd_trigger,
                    models=pair,
                    ledgers=ledgers,
                    contexts=contexts,
                    contextual_model=contextual_model,
                )
                audits.extend(audit)
                v10._annotate(current, controls[heldout])
                heldouts[heldout] = current

            full_gate = all(
                row["pf_at_least_surface_control"]
                and row["total_r_at_least_surface_control"]
                and row["dd_below_surface_control"]
                for row in heldouts.values()
            )
            all_dd6 = all(row["dd_at_or_below_6r"] for row in heldouts.values())
            total_overrides = sum(row["override_count"] for row in heldouts.values())
            results.append(
                {
                    "policy": policy,
                    "dd_trigger_r": str(dd_trigger),
                    "heldouts": heldouts,
                    "model_diagnostics": diagnostics,
                    "total_override_count": total_overrides,
                    "all_consumed_full_gate": full_gate,
                    "all_consumed_dd6": all_dd6,
                }
            )

        candidates = tuple(
            row
            for row in results
            if row["total_override_count"] > 0
            and row["all_consumed_full_gate"]
            and row["all_consumed_dd6"]
        )
    finally:
        v11._SIMULTANEOUS.clear()
        v11._SIMULTANEOUS.update(previous)

    return {
        "identity": IDENTITY,
        "evaluation": "DUAL_PERIOD_CONTEXTUAL_RECOVERY_MODE_MIXTURE",
        "arms": list(ARMS),
        "cell_hierarchy": list(MIN_SUPPORT),
        "minimum_support_by_level": MIN_SUPPORT,
        "max_recovery_base_multiplier": str(MAX_BASE_MULTIPLIER),
        "results": results,
        "candidate_count": len(candidates),
        "all_entries_preserved": True,
        "density_retention": "1",
        "surface_risk_multiplier_preserved": True,
        "scored_period_outcomes_visible_to_mixture": False,
        "both_other_period_models_must_agree": True,
        "runtime_unchosen_counterfactual_visible": False,
        "current_outcome_visible_to_decision": False,
        "target_r": "2.00",
        "max3_ceiling_preserved": True,
        "automatic_policy_promotion": False,
        "trader_certified": False,
        "live_authorized": False,
        "real_capital_authorized": False,
        "next_phase": (
            "FREEZE_V17_MIXTURE_THEN_OPEN_2018_2020_FRESH_HOLDOUT"
            if candidates
            else "BUILD_RECOVERY_TRAJECTORY_TRIGGER_V18"
        ),
    }, tuple(audits)


def write_report(
    report: dict[str, Any],
    audits: tuple[MixtureDecision, ...],
    output: Path,
) -> None:
    output.mkdir(parents=True, exist_ok=True)
    (output / "capitalizer-recovery-mode-mixture-v17.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    with (
        output / "capitalizer-recovery-mode-mixture-v17-decisions.jsonl"
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

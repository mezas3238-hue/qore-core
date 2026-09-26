"""Causal post-entry recovery trajectory trigger for Capitalizer.

V16/V17 falsified global and pre-entry contextual protection routing. V18 moves
the decision to a later causal point: a trade must first reach a real favorable
R milestone while still sharing the same path as Surface and every candidate
mode in its trigger family.

Only same-trigger families are compared:
- 0.50R: BE_AFTER_050 vs STAGED_050_100_150
- 0.75R: BE_AFTER_075 vs STAGED_075_125_150
- 1.00R: BE_AFTER_100 vs LOCK025_AFTER_100 vs LOCK050_AFTER_100

At the milestone timestamp the elapsed trajectory is known, but the future
outcome is not. Each of the two OTHER consumed periods independently learns a
Pareto-dominant arm by predeclared trigger-delay cells. A scored trade can switch
mode only when both external models resolve the same cell and choose the same
arm.

All entries, Surface sizing, original entry/target geometry and MAX3 are
preserved. The sealed 2018-2020 holdout remains unopened unless a consumed
candidate passes the full economic envelope.
"""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from dataclasses import asdict, dataclass, replace
from datetime import datetime
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

IDENTITY = "QORE_CAPITALIZER_RECOVERY_TRAJECTORY_TRIGGER_V18"
RECOVERY_DD = Decimal("3")
MAX_BASE_MULTIPLIER = Decimal("0.35")

FAMILIES: dict[str, tuple[Decimal, tuple[str, ...]]] = {
    "TRIGGER_050": (
        Decimal("0.50"),
        (
            milestone.ProtectionMode.BE_AFTER_050.value,
            milestone.ProtectionMode.STAGED_050_100_150.value,
        ),
    ),
    "TRIGGER_075": (
        Decimal("0.75"),
        (
            milestone.ProtectionMode.BE_AFTER_075.value,
            milestone.ProtectionMode.STAGED_075_125_150.value,
        ),
    ),
    "TRIGGER_100": (
        Decimal("1.00"),
        (
            milestone.ProtectionMode.BE_AFTER_100.value,
            milestone.ProtectionMode.LOCK025_AFTER_100.value,
            milestone.ProtectionMode.LOCK050_AFTER_100.value,
        ),
    ),
}
POLICIES = ("SURFACE_CONTROL", *FAMILIES)

MIN_SUPPORT = {
    "DELAY_DEST": 12,
    "DELAY_VOL": 15,
    "DELAY": 20,
}


@dataclass(frozen=True, slots=True)
class TriggerCell:
    level: str
    values: tuple[str, ...]
    support: int
    selected_arm: str | None


@dataclass(frozen=True, slots=True)
class PeriodTriggerModel:
    period: str
    family: str
    trigger_r: str
    eligible_support: int
    cells: dict[str, TriggerCell]


@dataclass(frozen=True, slots=True)
class TriggerDecision:
    period: str
    policy: str
    symbol: str
    session: str
    entry_at: str
    trigger_at: str | None
    trigger_delay_minutes: str | None
    delay_band: str | None
    current_drawdown_r: str
    base_multiplier: str
    surface_mode: str
    left_arm: str | None
    right_arm: str | None
    final_mode: str
    common_path_verified: bool
    override_applied: bool
    training_periods: tuple[str, str] | None
    current_outcome_visible_to_decision: bool = False
    future_after_trigger_visible_to_decision: bool = False
    scored_period_counterfactual_outcomes_visible: bool = False


def _aware(value: str) -> datetime:
    return direct._aware(value)


def _delay_band(minutes: Decimal) -> str:
    if minutes <= Decimal("5"):
        return "FAST_0_5"
    if minutes <= Decimal("15"):
        return "MID_5_15"
    return "SLOW_GT15"


def _trigger_delay(entry_at: str, trigger_at: str) -> Decimal:
    seconds = Decimal(str((_aware(trigger_at) - _aware(entry_at)).total_seconds()))
    if seconds < 0:
        raise ValueError("V18 trigger cannot precede entry")
    return seconds / Decimal("60")


def _cell_specs(
    *,
    delay_band: str,
    ctx: Any,
) -> tuple[tuple[str, tuple[str, ...]], ...]:
    return (
        ("DELAY_DEST", (delay_band, ctx.destination_state)),
        ("DELAY_VOL", (delay_band, ctx.volatility_state)),
        ("DELAY", (delay_band,)),
    )


def _cell_id(level: str, values: tuple[str, ...]) -> str:
    return json.dumps(
        {"level": level, "values": values},
        separators=(",", ":"),
        sort_keys=True,
    )


def _common_trigger(
    *,
    key: tuple[str, str],
    surface_mode: str,
    family_arms: tuple[str, ...],
    by_mode: dict[str, dict[tuple[str, str], milestone.SimulatedTrade]],
) -> str | None:
    reference = by_mode[family_arms[0]][key].first_protection_at
    if reference is None:
        return None

    trigger_dt = _aware(reference)
    for arm in family_arms:
        candidate = by_mode[arm][key].first_protection_at
        if candidate is None or _aware(candidate) != trigger_dt:
            return None

    surface_first = by_mode[surface_mode][key].first_protection_at
    if surface_first is not None and _aware(surface_first) < trigger_dt:
        return None
    return reference


def _dominates(
    control: tuple[Decimal, ...],
    candidate: tuple[Decimal, ...],
    *,
    minimum: int,
) -> bool:
    if len(control) < minimum or len(candidate) != len(control):
        return False
    c_mean, c_neg, c_down = v16._stats(control)
    a_mean, a_neg, a_down = v16._stats(candidate)
    return (
        a_mean >= c_mean
        and a_neg <= c_neg
        and a_down <= c_down
        and (a_mean > c_mean or a_neg < c_neg or a_down < c_down)
    )


def _fit_model(
    *,
    period: str,
    family: str,
    ledgers: dict[str, tuple[milestone.SimulatedTrade, ...]],
    contexts: dict[tuple[str, str], Any],
    contextual_model: dict[str, Any],
) -> PeriodTriggerModel:
    trigger_r, family_arms = FAMILIES[family]
    by_mode = {
        mode: {(row.symbol, row.entry_at): row for row in rows}
        for mode, rows in ledgers.items()
    }
    ordered = tuple(
        sorted(
            ledgers[milestone.ProtectionMode.ORIGINAL.value],
            key=lambda row: (_aware(row.entry_at), row.symbol),
        )
    )
    chosen: list[milestone.SimulatedTrade] = []
    records: list[memory.MemoryRecord] = []
    controls: dict[str, list[Decimal]] = defaultdict(list)
    arms: dict[tuple[str, str], list[Decimal]] = defaultdict(list)
    meta: dict[str, tuple[str, tuple[str, ...]]] = {}
    eligible_support = 0

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
        surface = by_mode[pre.mode][key]
        recovery = (
            pre.current_dd >= RECOVERY_DD
            and pre.base_multiplier <= MAX_BASE_MULTIPLIER
        )
        trigger_at = (
            None
            if not recovery
            else _common_trigger(
                key=key,
                surface_mode=pre.mode,
                family_arms=family_arms,
                by_mode=by_mode,
            )
        )
        if trigger_at is not None:
            eligible_support += 1
            delay = _trigger_delay(trade.entry_at, trigger_at)
            band = _delay_band(delay)
            for level, values in _cell_specs(delay_band=band, ctx=pre.ctx):
                cid = _cell_id(level, values)
                meta[cid] = (level, values)
                controls[cid].append(Decimal(surface.realized_gross_r))
                for arm in family_arms:
                    arms[(cid, arm)].append(
                        Decimal(by_mode[arm][key].realized_gross_r)
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

    cells: dict[str, TriggerCell] = {}
    for cid, control_values_list in controls.items():
        level, key_values = meta[cid]
        control = tuple(control_values_list)
        eligible: list[tuple[str, Decimal, Decimal, Decimal]] = []
        for arm in family_arms:
            candidate = tuple(arms[(cid, arm)])
            if not _dominates(
                control,
                candidate,
                minimum=MIN_SUPPORT[level],
            ):
                continue
            mean, neg, down = v16._stats(candidate)
            eligible.append((arm, mean, neg, down))
        selected = None
        if eligible:
            selected = max(
                eligible,
                key=lambda row: (
                    row[1],
                    -row[2],
                    -row[3],
                    -family_arms.index(row[0]),
                ),
            )[0]
        cells[cid] = TriggerCell(
            level=level,
            values=key_values,
            support=len(control),
            selected_arm=selected,
        )

    return PeriodTriggerModel(
        period=period,
        family=family,
        trigger_r=str(trigger_r),
        eligible_support=eligible_support,
        cells=cells,
    )


def _lookup(
    model: PeriodTriggerModel,
    *,
    delay_band: str,
    ctx: Any,
) -> tuple[str | None, str | None]:
    for level, values in _cell_specs(delay_band=delay_band, ctx=ctx):
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
    models: tuple[PeriodTriggerModel, PeriodTriggerModel] | None,
    ledgers: dict[str, tuple[milestone.SimulatedTrade, ...]],
    contexts: dict[tuple[str, str], Any],
    contextual_model: dict[str, Any],
) -> tuple[dict[str, Any], tuple[TriggerDecision, ...]]:
    by_mode = {
        mode: {(row.symbol, row.entry_at): row for row in rows}
        for mode, rows in ledgers.items()
    }
    ordered = tuple(
        sorted(
            ledgers[milestone.ProtectionMode.ORIGINAL.value],
            key=lambda row: (_aware(row.entry_at), row.symbol),
        )
    )
    chosen: list[milestone.SimulatedTrade] = []
    records: list[memory.MemoryRecord] = []
    decisions: list[TriggerDecision] = []
    overrides = 0
    eligible = 0

    family_arms: tuple[str, ...] = ()
    if policy != "SURFACE_CONTROL":
        family_arms = FAMILIES[policy][1]

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
        recovery = (
            policy != "SURFACE_CONTROL"
            and pre.current_dd >= RECOVERY_DD
            and pre.base_multiplier <= MAX_BASE_MULTIPLIER
        )
        trigger_at = (
            None
            if not recovery
            else _common_trigger(
                key=key,
                surface_mode=pre.mode,
                family_arms=family_arms,
                by_mode=by_mode,
            )
        )

        left_arm: str | None = None
        right_arm: str | None = None
        final_mode = pre.mode
        override = False
        delay: Decimal | None = None
        band: str | None = None
        training_periods: tuple[str, str] | None = None

        if trigger_at is not None:
            eligible += 1
            delay = _trigger_delay(trade.entry_at, trigger_at)
            band = _delay_band(delay)
            if models is not None:
                left_arm, _left_level = _lookup(
                    models[0],
                    delay_band=band,
                    ctx=pre.ctx,
                )
                right_arm, _right_level = _lookup(
                    models[1],
                    delay_band=band,
                    ctx=pre.ctx,
                )
                training_periods = (models[0].period, models[1].period)
                if left_arm is not None and left_arm == right_arm:
                    final_mode = left_arm
                    override = True
                    overrides += 1

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
            TriggerDecision(
                period=period,
                policy=policy,
                symbol=trade.symbol,
                session=trade.session,
                entry_at=trade.entry_at,
                trigger_at=trigger_at,
                trigger_delay_minutes=None if delay is None else str(delay),
                delay_band=band,
                current_drawdown_r=str(pre.current_dd),
                base_multiplier=str(pre.base_multiplier),
                surface_mode=pre.mode,
                left_arm=left_arm,
                right_arm=right_arm,
                final_mode=final_mode,
                common_path_verified=trigger_at is not None,
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
        "eligible_trigger_count": eligible,
        "override_count": overrides,
    }, tuple(decisions)


def build_report(
    development_root: Path,
    validation_root: Path,
    reserved_root: Path,
    development_validation_context_root: Path,
    reserved_context_root: Path,
) -> tuple[dict[str, Any], tuple[TriggerDecision, ...]]:
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
        audits: list[TriggerDecision] = []
        for period, (ledgers, contexts) in windows.items():
            control, audit = _simulate(
                period=period,
                policy="SURFACE_CONTROL",
                models=None,
                ledgers=ledgers,
                contexts=contexts,
                contextual_model=contextual_model,
            )
            controls[period] = control
            audits.extend(audit)

        results: list[dict[str, Any]] = []
        for family in FAMILIES:
            fitted = {
                period: _fit_model(
                    period=period,
                    family=family,
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
                    "left_eligible_support": pair[0].eligible_support,
                    "right_eligible_support": pair[1].eligible_support,
                    "left_selected_cell_count": sum(
                        cell.selected_arm is not None
                        for cell in pair[0].cells.values()
                    ),
                    "right_selected_cell_count": sum(
                        cell.selected_arm is not None
                        for cell in pair[1].cells.values()
                    ),
                }
                current, audit = _simulate(
                    period=heldout,
                    policy=family,
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
                and row["dd_at_or_below_6r"]
                for row in heldouts.values()
            )
            total_overrides = sum(row["override_count"] for row in heldouts.values())
            results.append(
                {
                    "policy": family,
                    "trigger_r": str(FAMILIES[family][0]),
                    "heldouts": heldouts,
                    "model_diagnostics": diagnostics,
                    "total_override_count": total_overrides,
                    "all_consumed_full_gate": full_gate,
                }
            )

        candidates = tuple(
            row
            for row in results
            if row["total_override_count"] > 0
            and row["all_consumed_full_gate"]
        )
    finally:
        v11._SIMULTANEOUS.clear()
        v11._SIMULTANEOUS.update(previous)

    return {
        "identity": IDENTITY,
        "evaluation": "DUAL_PERIOD_COMMON_PATH_POST_ENTRY_TRIGGER",
        "recovery_dd_trigger_r": str(RECOVERY_DD),
        "max_recovery_base_multiplier": str(MAX_BASE_MULTIPLIER),
        "families": {
            name: {
                "trigger_r": str(trigger),
                "arms": list(arms),
            }
            for name, (trigger, arms) in FAMILIES.items()
        },
        "minimum_support_by_level": MIN_SUPPORT,
        "results": results,
        "candidate_count": len(candidates),
        "all_entries_preserved": True,
        "density_retention": "1",
        "surface_risk_multiplier_preserved": True,
        "same_trigger_family_required": True,
        "common_path_before_trigger_required": True,
        "both_other_period_models_must_agree": True,
        "scored_period_counterfactual_outcomes_visible": False,
        "future_after_trigger_visible_to_decision": False,
        "current_outcome_visible_to_decision": False,
        "target_r": "2.00",
        "max3_ceiling_preserved": True,
        "automatic_policy_promotion": False,
        "trader_certified": False,
        "live_authorized": False,
        "real_capital_authorized": False,
        "next_phase": (
            "FREEZE_V18_TRIGGER_ROUTER_THEN_OPEN_2018_2020_FRESH_HOLDOUT"
            if candidates
            else "BUILD_JOINT_TRAJECTORY_DESTINATION_SURVIVAL_V19"
        ),
    }, tuple(audits)


def write_report(
    report: dict[str, Any],
    audits: tuple[TriggerDecision, ...],
    output: Path,
) -> None:
    output.mkdir(parents=True, exist_ok=True)
    (output / "capitalizer-recovery-trajectory-trigger-v18.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    with (
        output / "capitalizer-recovery-trajectory-trigger-v18-decisions.jsonl"
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

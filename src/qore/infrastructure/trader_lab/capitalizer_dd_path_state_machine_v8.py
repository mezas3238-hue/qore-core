"""Drawdown-path hysteresis state machine for Capitalizer.

V7 falsified broad early-shock overlays: they reduced some drawdown but
systematically compressed too many winners. Reserved-window forensics showed a
more specific defect: SURFACE_SELECTIVE can remain stuck at 0.20R through a
long recovery phase.

V8 treats drawdown management as a causal state machine:

NORMAL -> DEFENSE -> PROBE -> RECOVERY -> NORMAL

- DEFENSE keeps the frozen SURFACE_SELECTIVE multiplier.
- PROBE releases exactly one future trade from 0.20R to 0.35R only after
  pressure has cleared and recent already-closed normalized outcomes improve.
- The probe's outcome is stored but cannot affect state until its exit time.
- A successful probe unlocks RECOVERY; a failed probe returns to DEFENSE.
- RECOVERY releases only one ladder step and immediately returns to DEFENSE
  when deterioration resumes.

No current outcome or unchosen counterfactual is visible to the decision.
All entries, MAX3, 2R target and contextual milestone routing are preserved.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from dataclasses import asdict, dataclass, replace
from decimal import Decimal
from enum import StrEnum
from pathlib import Path
from typing import Any

from qore.infrastructure.trader_lab import (
    capitalizer_adaptive_context_risk_governor_v1 as memory,
)
from qore.infrastructure.trader_lab import (
    capitalizer_causal_loss_pressure_surface_v7 as pressure_v7,
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

IDENTITY = "QORE_CAPITALIZER_DD_PATH_STATE_MACHINE_V8"
BASE_POSITION_POLICY = "CONTEXT_STABILITY_STAGE"

EXPECTED_DEVELOPMENT_TRADES = 948
EXPECTED_VALIDATION_TRADES = 1034
EXPECTED_RESERVED_TRADES = 1088

POLICIES = (
    "SURFACE_CONTROL",
    "PROBE_035",
    "PROBE_CONTEXT_035",
    "PROBE_CONTEXT_DYNAMIC",
    "PROBE_STRICT_035",
)


class PathPhase(StrEnum):
    NORMAL = "NORMAL"
    DEFENSE = "DEFENSE"
    PROBE = "PROBE"
    RECOVERY = "RECOVERY"


@dataclass(frozen=True, slots=True)
class PendingProbe:
    key: str
    exit_at: str
    normalized_realized_r: str


@dataclass(frozen=True, slots=True)
class PathDecision:
    role: str
    policy: str
    symbol: str
    session: str
    operating_date: str
    entry_at: str
    selected_mode: str
    phase_before: str
    phase_after_predecision_update: str
    current_drawdown_r: str
    pressure_global_shock: bool
    pressure_global_severe: bool
    pressure_session_shock: bool
    recent3_sum_r: str
    recent3_positive_count: int
    adverse_votes: int
    favorable_votes: int
    base_multiplier: str
    final_multiplier: str
    action: str
    probe_pending_after_decision: bool
    current_outcome_visible_to_decision: bool = False
    probe_outcome_visible_before_close: bool = False
    unchosen_counterfactual_visible_to_decision: bool = False


def _favorable_votes(
    evidence: tuple[memory.ScopeEvidence, ...],
) -> int:
    return sum(
        item.posterior_mean_r is not None
        and item.posterior_negative_rate is not None
        and Decimal(item.posterior_mean_r) > 0
        and Decimal(item.posterior_negative_rate) < Decimal("0.50")
        for item in evidence
    )


def _recent3(
    records: tuple[memory.MemoryRecord, ...],
) -> tuple[Decimal, int]:
    recent = records[-3:]
    values = tuple(Decimal(row.normalized_realized_r) for row in recent)
    return (
        sum(values, Decimal("0")),
        sum(value > 0 for value in values),
    )


def _probe_trigger(
    *,
    policy: str,
    current_dd: Decimal,
    pressure: pressure_v7.PressureState,
    recent3_sum: Decimal,
    recent3_positive: int,
    adverse_votes: int,
    favorable_votes: int,
) -> bool:
    if current_dd < Decimal("3"):
        return False
    if pressure.global_shock or pressure.global_severe or pressure.session_shock:
        return False
    if recent3_sum < Decimal("0.75") or recent3_positive < 2:
        return False
    if policy == "PROBE_035":
        return True
    if policy in {"PROBE_CONTEXT_035", "PROBE_CONTEXT_DYNAMIC"}:
        return favorable_votes >= 2 and adverse_votes == 0
    if policy == "PROBE_STRICT_035":
        return (
            recent3_positive == 3
            and recent3_sum >= Decimal("1")
            and favorable_votes >= 2
            and adverse_votes == 0
        )
    return False


def _release_multiplier(
    *,
    policy: str,
    base: Decimal,
    current_dd: Decimal,
    favorable_votes: int,
    adverse_votes: int,
) -> tuple[Decimal, str]:
    if base > Decimal("0.35"):
        return base, "BASE_ALREADY_ABOVE_PROBE"

    if policy in {"PROBE_035", "PROBE_CONTEXT_035", "PROBE_STRICT_035"}:
        return max(base, Decimal("0.35")), "RECOVERY_RELEASE_035"

    if policy == "PROBE_CONTEXT_DYNAMIC":
        if favorable_votes >= 3 and adverse_votes == 0 and current_dd < Decimal("4"):
            return max(base, Decimal("0.55")), "RECOVERY_RELEASE_055"
        return max(base, Decimal("0.35")), "RECOVERY_RELEASE_035"

    return base, "NONE"


def _simulate(
    *,
    role: str,
    policy: str,
    ledgers: dict[str, tuple[milestone.SimulatedTrade, ...]],
    contexts: dict[tuple[str, str], context.NativeContextRow],
    model: dict[str, Any],
) -> tuple[dict[str, Any], tuple[PathDecision, ...]]:
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

    phase = PathPhase.NORMAL
    pending_probe: PendingProbe | None = None
    chosen_scaled: list[milestone.SimulatedTrade] = []
    records: list[memory.MemoryRecord] = []
    decisions: list[PathDecision] = []
    multiplier_counts: Counter[str] = Counter()
    phase_counts: Counter[str] = Counter()
    action_counts: Counter[str] = Counter()
    probe_success = 0
    probe_failure = 0

    for trade in ordered:
        entry_dt = direct._aware(trade.entry_at)
        phase_before = phase

        # A probe result is allowed to affect state only after that probe closed.
        if (
            pending_probe is not None
            and direct._aware(pending_probe.exit_at) <= entry_dt
        ):
            probe_r = Decimal(pending_probe.normalized_realized_r)
            if probe_r > 0:
                phase = PathPhase.RECOVERY
                probe_success += 1
            else:
                phase = PathPhase.DEFENSE
                probe_failure += 1
            pending_probe = None

        history = governor._closed_history(
            tuple(chosen_scaled),
            entry_at=entry_dt,
        )
        _state, _eq, _peak, current_dd, _loss_streak = governor._state(history)

        causal_records = memory._closed_records(tuple(records), entry_at=trade.entry_at)
        pressure = pressure_v7._pressure(causal_records, session=trade.session)
        recent3_sum, recent3_positive = _recent3(causal_records)

        key = (trade.symbol, trade.entry_at)
        ctx = contexts[key]
        evidence = memory._evidence(records=causal_records, ctx=ctx)
        adverse_votes = sum(item.adverse for item in evidence)
        favorable_votes = _favorable_votes(evidence)

        # Hard deterioration always overrides recovery state.
        if current_dd < Decimal("2"):
            phase = PathPhase.NORMAL
            pending_probe = None
        elif (
            current_dd >= Decimal("5")
            or pressure.global_severe
            or (pressure.global_shock and current_dd >= Decimal("3"))
        ):
            phase = PathPhase.DEFENSE
        elif (
            phase is PathPhase.NORMAL
            and current_dd >= Decimal("3")
        ):
            phase = PathPhase.DEFENSE
        elif (
            phase is PathPhase.RECOVERY
            and (
                pressure.global_shock
                or pressure.session_shock
                or adverse_votes >= 2
            )
        ):
            phase = PathPhase.DEFENSE

        phase_after_update = phase

        base_mode, _level, _support = router._lookup(model, ctx)
        final_mode, _overlay = router._overlay(
            policy=BASE_POSITION_POLICY,
            base_mode=base_mode,
            state=_state,
        )
        unscaled = by_mode[final_mode][key]

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
        final_multiplier = base_multiplier
        action = "BASE_SURFACE"

        if policy != "SURFACE_CONTROL":
            if (
                phase is PathPhase.DEFENSE
                and pending_probe is None
                and base_multiplier <= Decimal("0.20")
                and _probe_trigger(
                    policy=policy,
                    current_dd=current_dd,
                    pressure=pressure,
                    recent3_sum=recent3_sum,
                    recent3_positive=recent3_positive,
                    adverse_votes=adverse_votes,
                    favorable_votes=favorable_votes,
                )
            ):
                final_multiplier = Decimal("0.35")
                action = "OPEN_SINGLE_PROBE_035"
                phase = PathPhase.PROBE
            elif phase is PathPhase.RECOVERY:
                final_multiplier, action = _release_multiplier(
                    policy=policy,
                    base=base_multiplier,
                    current_dd=current_dd,
                    favorable_votes=favorable_votes,
                    adverse_votes=adverse_votes,
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

        if action == "OPEN_SINGLE_PROBE_035":
            pending_probe = PendingProbe(
                key=f"{trade.symbol}|{trade.entry_at}",
                exit_at=unscaled.exit_at,
                normalized_realized_r=unscaled.realized_gross_r,
            )

        multiplier_counts[str(final_multiplier)] += 1
        phase_counts[phase.value] += 1
        action_counts[action] += 1
        decisions.append(
            PathDecision(
                role=role,
                policy=policy,
                symbol=trade.symbol,
                session=trade.session,
                operating_date=trade.operating_date,
                entry_at=trade.entry_at,
                selected_mode=final_mode,
                phase_before=phase_before.value,
                phase_after_predecision_update=phase_after_update.value,
                current_drawdown_r=str(current_dd),
                pressure_global_shock=pressure.global_shock,
                pressure_global_severe=pressure.global_severe,
                pressure_session_shock=pressure.session_shock,
                recent3_sum_r=str(recent3_sum),
                recent3_positive_count=recent3_positive,
                adverse_votes=adverse_votes,
                favorable_votes=favorable_votes,
                base_multiplier=str(base_multiplier),
                final_multiplier=str(final_multiplier),
                action=action,
                probe_pending_after_decision=pending_probe is not None,
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
        "phase_counts": dict(sorted(phase_counts.items())),
        "action_counts": dict(sorted(action_counts.items())),
        "probe_successes": probe_success,
        "probe_failures": probe_failure,
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
) -> tuple[dict[str, Any], tuple[PathDecision, ...]]:
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
        raise ValueError("V8 consumed reserved population mismatch")

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
    audits: list[PathDecision] = []
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
        "state_machine_uses_prior_closed_chosen_outcomes_only": True,
        "probe_outcome_used_only_after_probe_exit": True,
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
            "FREEZE_PATH_POLICY_AND_OPEN_2018_2020_HOLDOUT"
            if robust_rows
            else "BUILD_CONTEXTUAL_PROBE_VALUE_MODEL_WITHOUT_REUSING_CURRENT_OUTCOME"
        ),
    }, tuple(audits)


def write_report(
    report: dict[str, Any],
    audits: tuple[PathDecision, ...],
    output: Path,
) -> None:
    output.mkdir(parents=True, exist_ok=True)
    (output / "capitalizer-dd-path-state-machine-v8.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    with (
        output / "capitalizer-dd-path-state-machine-v8-decisions.jsonl"
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

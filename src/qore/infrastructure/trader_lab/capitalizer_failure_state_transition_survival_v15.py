"""Failure-state transition survival for Capitalizer.

V14 demonstrated an absorbing-defense failure: once drawdown is high, repeated
hard abstention can prevent the positive trades needed to recover equity. V15
replaces path-budget persistence with causal transition memory.

After an accepted loss/STOP becomes known at its exit timestamp, the latest
failure snapshot stays active. New opportunities are not judged by their future
outcomes. They are judged by whether the market has become causally different
from the failed state: regime, destination, session, factor family and side.

A blocked trade does not consume the failure snapshot and never reveals its
counterfactual outcome. A causally novel accepted transition can re-enter flow;
a later accepted non-loss may clear the failure state. This keeps defense
state-dependent without creating an absorbing no-trade regime.

Selected-ledger diagnostic only. Full source recompetition remains mandatory
before any candidate freeze.
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

IDENTITY = "QORE_CAPITALIZER_FAILURE_STATE_TRANSITION_SURVIVAL_V15"
MIN_DENSITY_RETENTION = Decimal("0.90")

POLICY_SPECS: dict[str, tuple[str, Decimal, int]] = {
    "LOSS_DD4_N1": ("LOSS", Decimal("4"), 1),
    "LOSS_DD4_N2": ("LOSS", Decimal("4"), 2),
    "STOP_DD4_N1": ("STOP", Decimal("4"), 1),
    "STOP_DD4_N2": ("STOP", Decimal("4"), 2),
    "LOSS_DD5_N2": ("LOSS", Decimal("5"), 2),
    "STOP_DD5_N2": ("STOP", Decimal("5"), 2),
}
POLICIES = ("SURFACE_CONTROL", *POLICY_SPECS)


@dataclass(frozen=True, slots=True)
class StateSnapshot:
    symbol: str
    session: str
    side: str
    regime: str
    destination: str
    entry_at: str
    exit_at: str
    factors: tuple[str, ...]
    exit_reason: str


@dataclass(frozen=True, slots=True)
class PendingOutcome:
    symbol: str
    entry_at: str
    exit_at: str
    normalized_realized_r: str
    exit_reason: str
    snapshot: StateSnapshot


@dataclass(frozen=True, slots=True)
class TransitionDecision:
    period: str
    policy: str
    symbol: str
    session: str
    entry_at: str
    current_drawdown_r: str
    base_multiplier: str
    failure_active: bool
    failure_symbol: str | None
    failure_session: str | None
    failure_exit_reason: str | None
    novelty_score: int
    changed_dimensions: tuple[str, ...]
    required_novelty: int
    dd_trigger_r: str | None
    abstain: bool
    reason: str
    current_outcome_visible_to_decision: bool = False
    blocked_outcome_visible_to_memory: bool = False


def _factors(symbol: str, side: str) -> tuple[str, ...]:
    return tuple(sorted(v11._factor_map(symbol=symbol, side=side)))


def _snapshot(
    *,
    trade: milestone.SimulatedTrade,
    pre: v10.Pretrade,
    exit_at: str,
    exit_reason: str,
) -> StateSnapshot:
    return StateSnapshot(
        symbol=trade.symbol,
        session=trade.session,
        side=trade.side,
        regime=pre.ctx.regime_signature,
        destination=pre.ctx.destination_state,
        entry_at=trade.entry_at,
        exit_at=exit_at,
        factors=_factors(trade.symbol, trade.side),
        exit_reason=exit_reason,
    )


def _novelty(
    failure: StateSnapshot,
    *,
    trade: milestone.SimulatedTrade,
    pre: v10.Pretrade,
) -> tuple[int, tuple[str, ...]]:
    changed: list[str] = []
    if pre.ctx.regime_signature != failure.regime:
        changed.append("REGIME")
    if pre.ctx.destination_state != failure.destination:
        changed.append("DESTINATION")
    if trade.session != failure.session:
        changed.append("SESSION")
    if not (set(_factors(trade.symbol, trade.side)) & set(failure.factors)):
        changed.append("FACTOR_FAMILY")
    if trade.side != failure.side:
        changed.append("SIDE")
    return len(changed), tuple(changed)


def _failure_matches(
    *,
    semantics: str,
    failure: StateSnapshot | None,
) -> bool:
    if failure is None:
        return False
    if semantics == "LOSS":
        return True
    if semantics == "STOP":
        return failure.exit_reason == "STOP"
    raise ValueError(f"unknown V15 semantics: {semantics}")


def _should_abstain(
    *,
    policy: str,
    current_dd: Decimal,
    failure: StateSnapshot | None,
    novelty: int,
) -> bool:
    spec = POLICY_SPECS.get(policy)
    if spec is None:
        return False
    semantics, dd_trigger, required_novelty = spec
    return (
        current_dd >= dd_trigger
        and _failure_matches(semantics=semantics, failure=failure)
        and novelty < required_novelty
    )


def _simulate(
    *,
    period: str,
    policy: str,
    ledgers: dict[str, tuple[milestone.SimulatedTrade, ...]],
    contexts: dict[tuple[str, str], Any],
    contextual_model: dict[str, Any],
) -> tuple[dict[str, Any], tuple[TransitionDecision, ...]]:
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
    active_failure: StateSnapshot | None = None
    decisions: list[TransitionDecision] = []
    multipliers: Counter[str] = Counter()
    abstained = 0

    spec = POLICY_SPECS.get(policy)
    dd_trigger = None if spec is None else spec[1]
    required_novelty = 0 if spec is None else spec[2]

    for trade in ordered:
        entry_dt = direct._aware(trade.entry_at)
        for item in sorted(
            pending,
            key=lambda row: (direct._aware(row.exit_at), row.symbol),
        ):
            key = (item.symbol, item.entry_at)
            if key in processed or direct._aware(item.exit_at) > entry_dt:
                continue
            realized = Decimal(item.normalized_realized_r)
            if realized < 0:
                active_failure = item.snapshot
            elif (
                active_failure is not None
                and direct._aware(item.entry_at) > direct._aware(active_failure.exit_at)
            ):
                active_failure = None
            processed.add(key)

        pre = v11._pretrade(
            period=period,
            trade=trade,
            contexts=contexts,
            contextual_model=contextual_model,
            chosen_scaled=tuple(chosen),
            records=tuple(records),
        )
        if active_failure is None:
            novelty, changed = 99, ()
        else:
            novelty, changed = _novelty(
                active_failure,
                trade=trade,
                pre=pre,
            )
        reject = _should_abstain(
            policy=policy,
            current_dd=pre.current_dd,
            failure=active_failure,
            novelty=novelty,
        )
        reason = "ALLOW"
        if reject:
            abstained += 1
            reason = "FAILURE_STATE_NOT_CAUSALLY_NOVEL"

        decisions.append(
            TransitionDecision(
                period=period,
                policy=policy,
                symbol=trade.symbol,
                session=trade.session,
                entry_at=trade.entry_at,
                current_drawdown_r=str(pre.current_dd),
                base_multiplier=str(pre.base_multiplier),
                failure_active=active_failure is not None,
                failure_symbol=(
                    None if active_failure is None else active_failure.symbol
                ),
                failure_session=(
                    None if active_failure is None else active_failure.session
                ),
                failure_exit_reason=(
                    None if active_failure is None else active_failure.exit_reason
                ),
                novelty_score=novelty,
                changed_dimensions=changed,
                required_novelty=required_novelty,
                dd_trigger_r=None if dd_trigger is None else str(dd_trigger),
                abstain=reject,
                reason=reason,
            )
        )
        if reject:
            continue

        key = (trade.symbol, trade.entry_at)
        unscaled = by_mode[pre.mode][key]
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
                exit_reason=unscaled.exit_reason,
                snapshot=_snapshot(
                    trade=trade,
                    pre=pre,
                    exit_at=unscaled.exit_at,
                    exit_reason=unscaled.exit_reason,
                ),
            )
        )
        multipliers[str(pre.base_multiplier)] += 1

    ledger = tuple(chosen)
    return {
        "period": period,
        "policy": policy,
        "trades": len(ledger),
        "original_selected_trades": len(ordered),
        "abstained": abstained,
        "density_retention": str(Decimal(len(ledger)) / Decimal(len(ordered))),
        "metrics": milestone._metrics(ledger),
        "multiplier_counts": dict(sorted(multipliers.items())),
    }, tuple(decisions)


def build_report(
    development_root: Path,
    validation_root: Path,
    reserved_root: Path,
    development_validation_context_root: Path,
    reserved_context_root: Path,
) -> tuple[dict[str, Any], tuple[TransitionDecision, ...]]:
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
        audits: list[TransitionDecision] = []
        for period, (ledgers, contexts) in windows.items():
            control, audit = _simulate(
                period=period,
                policy="SURFACE_CONTROL",
                ledgers=ledgers,
                contexts=contexts,
                contextual_model=contextual_model,
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
                    )
                    audits.extend(audit)
                v10._annotate(current, controls[period])
                current["density_at_or_above_floor"] = (
                    Decimal(current["density_retention"]) >= MIN_DENSITY_RETENTION
                )
                current["losing_streak_not_worse"] = (
                    int(current["metrics"]["max_losing_streak"])
                    <= int(controls[period]["metrics"]["max_losing_streak"])
                )
                heldouts[period] = current

            all_full = all(
                row["pf_at_least_surface_control"]
                and row["total_r_at_least_surface_control"]
                and row["dd_below_surface_control"]
                and row["density_at_or_above_floor"]
                and row["losing_streak_not_worse"]
                for row in heldouts.values()
            )
            all_dd6 = all(row["dd_at_or_below_6r"] for row in heldouts.values())
            results.append(
                {
                    "policy": policy,
                    "heldouts": heldouts,
                    "all_consumed_full_gate": all_full,
                    "all_consumed_dd6": all_dd6,
                }
            )
    finally:
        v11._SIMULTANEOUS.clear()
        v11._SIMULTANEOUS.update(previous)

    candidates = tuple(
        row
        for row in results
        if row["policy"] != "SURFACE_CONTROL"
        and row["all_consumed_full_gate"]
        and row["all_consumed_dd6"]
    )
    return {
        "identity": IDENTITY,
        "evaluation": "CAUSAL_FAILURE_STATE_TRANSITION_NOVELTY_SURVIVAL",
        "minimum_density_retention": str(MIN_DENSITY_RETENTION),
        "policy_specs": {
            name: [semantics, str(dd), novelty]
            for name, (semantics, dd, novelty) in POLICY_SPECS.items()
        },
        "results": results,
        "candidate_count": len(candidates),
        "failure_snapshot_created_only_after_accepted_exit": True,
        "blocked_trade_consumes_failure_state": False,
        "blocked_outcomes_visible_to_memory": False,
        "current_outcome_visible_to_decision": False,
        "causal_novelty_dimensions": [
            "REGIME",
            "DESTINATION",
            "SESSION",
            "FACTOR_FAMILY",
            "SIDE",
        ],
        "selected_ledger_diagnostic_only": True,
        "full_source_recompetition_required_before_freeze": True,
        "target_r": "2.00",
        "max3_ceiling_preserved": True,
        "automatic_policy_promotion": False,
        "trader_certified": False,
        "live_authorized": False,
        "real_capital_authorized": False,
        "next_phase": (
            "REPLAY_V15_RULE_THROUGH_FULL_SOURCE_COMPETITION"
            if candidates
            else "BUILD_RECOVERY_PROBE_SURVIVAL_MODEL_V16"
        ),
    }, tuple(audits)


def write_report(
    report: dict[str, Any],
    audits: tuple[TransitionDecision, ...],
    output: Path,
) -> None:
    output.mkdir(parents=True, exist_ok=True)
    (output / "capitalizer-failure-state-transition-survival-v15.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    with (
        output / "capitalizer-failure-state-transition-survival-v15-decisions.jsonl"
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

"""Sequential failure-memory abstention for Capitalizer.

V12 showed that a static cross-period lower-tail classifier does not isolate the
residual drawdown. V13 tests a different hypothesis: a state may have positive
long-run edge yet become temporarily unsafe immediately after it fails.

The memory is prequential and one-shot:
- only accepted trades may later update memory;
- an outcome is invisible until its exit timestamp;
- blocked trades never reveal their counterfactual outcome;
- a failure token can block at most one later matching state, then is consumed;
- a later accepted non-loss clears the state.

This selected-ledger experiment does not refill MAX3 slots after abstention.
Any viable policy must be re-run through full source competition before freeze.
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
    capitalizer_contextual_stability_router_2r_v1 as router,
)
from qore.infrastructure.trader_lab import (
    capitalizer_factor_journey_probe_ranker_v11 as v11,
)
from qore.infrastructure.trader_lab import (
    capitalizer_local_edge_convex_surface_v6 as edge_v6,
)
from qore.infrastructure.trader_lab import (
    capitalizer_max_recovery_direct_m1_replay_v1 as direct,
)

IDENTITY = "QORE_CAPITALIZER_SEQUENCE_FAILURE_MEMORY_ABSTENTION_V13"
MIN_DENSITY_RETENTION = Decimal("0.90")

POLICY_SPECS = {
    "LOSS1_STATE_020": ("STATE", "LOSS1", Decimal("0.20")),
    "LOSS1_FACTOR_020": ("FACTOR", "LOSS1", Decimal("0.20")),
    "LOSS2_STATE_020": ("STATE", "LOSS2", Decimal("0.20")),
    "STOP1_STATE_020": ("STATE", "STOP1", Decimal("0.20")),
    "LOSS1_STATE_035": ("STATE", "LOSS1", Decimal("0.35")),
    "LOSS2_STATE_035": ("STATE", "LOSS2", Decimal("0.35")),
    "STOP1_STATE_035": ("STATE", "STOP1", Decimal("0.35")),
}
POLICIES = ("SURFACE_CONTROL", *POLICY_SPECS)


@dataclass(slots=True)
class FailureState:
    loss_streak: int = 0
    last_loss: bool = False
    last_stop: bool = False


@dataclass(frozen=True, slots=True)
class PendingOutcome:
    symbol: str
    entry_at: str
    exit_at: str
    fingerprint: str
    normalized_realized_r: str
    exit_reason: str


@dataclass(frozen=True, slots=True)
class FailureDecision:
    period: str
    policy: str
    symbol: str
    session: str
    entry_at: str
    fingerprint: str
    base_multiplier: str
    prior_loss_streak: int
    prior_last_loss: bool
    prior_last_stop: bool
    abstain: bool
    reason: str
    current_outcome_visible_to_decision: bool = False
    blocked_outcome_visible_to_memory: bool = False


def _factor_relation(
    chosen: tuple[milestone.SimulatedTrade, ...],
    *,
    trade: milestone.SimulatedTrade,
) -> str:
    features = v11._factor_features(chosen, trade=trade)
    shared = features[1]
    aligned = features[3]
    opposed = features[4]
    if shared <= 0:
        return "NONE"
    if aligned > 0 and opposed <= 0:
        return "ALIGNED"
    if opposed > 0 and aligned <= 0:
        return "OPPOSED"
    return "MIXED"


def _fingerprint(
    *,
    family: str,
    trade: milestone.SimulatedTrade,
    pre: v10.Pretrade,
    chosen: tuple[milestone.SimulatedTrade, ...],
) -> str:
    base = (
        trade.session,
        pre.ctx.context_signature,
    )
    if family == "STATE":
        parts = base
    elif family == "FACTOR":
        parts = (*base, _factor_relation(chosen, trade=trade))
    else:
        raise ValueError(f"unknown V13 fingerprint family: {family}")
    return "|".join(parts)


def _apply_outcome(
    state: FailureState,
    *,
    realized_r: Decimal,
    exit_reason: str,
) -> None:
    if realized_r < 0:
        state.loss_streak += 1
        state.last_loss = True
        state.last_stop = exit_reason == "STOP"
    else:
        state.loss_streak = 0
        state.last_loss = False
        state.last_stop = False


def _should_block(
    *,
    semantics: str,
    state: FailureState,
) -> bool:
    if semantics == "LOSS1":
        return state.last_loss
    if semantics == "LOSS2":
        return state.loss_streak >= 2
    if semantics == "STOP1":
        return state.last_stop
    raise ValueError(f"unknown V13 semantics: {semantics}")


def _consume_token(state: FailureState) -> None:
    state.loss_streak = 0
    state.last_loss = False
    state.last_stop = False


def _simulate(
    *,
    period: str,
    policy: str,
    ledgers: dict[str, tuple[milestone.SimulatedTrade, ...]],
    contexts: dict[tuple[str, str], Any],
    contextual_model: dict[str, Any],
) -> tuple[dict[str, Any], tuple[FailureDecision, ...]]:
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
    states: dict[str, FailureState] = {}
    decisions: list[FailureDecision] = []
    multipliers: Counter[str] = Counter()
    abstained = 0

    spec = POLICY_SPECS.get(policy)
    family = "STATE" if spec is None else spec[0]
    semantics = "NONE" if spec is None else spec[1]
    cap = Decimal("-1") if spec is None else spec[2]

    for trade in ordered:
        entry_dt = direct._aware(trade.entry_at)

        for item in sorted(
            pending,
            key=lambda row: (direct._aware(row.exit_at), row.symbol),
        ):
            key = (item.symbol, item.entry_at)
            if key in processed:
                continue
            if direct._aware(item.exit_at) > entry_dt:
                continue
            state = states.setdefault(item.fingerprint, FailureState())
            _apply_outcome(
                state,
                realized_r=Decimal(item.normalized_realized_r),
                exit_reason=item.exit_reason,
            )
            processed.add(key)

        pre = v11._pretrade(
            period=period,
            trade=trade,
            contexts=contexts,
            contextual_model=contextual_model,
            chosen_scaled=tuple(chosen),
            records=tuple(records),
        )
        fp = _fingerprint(
            family=family,
            trade=trade,
            pre=pre,
            chosen=tuple(chosen),
        )
        state = states.setdefault(fp, FailureState())
        prior_loss_streak = state.loss_streak
        prior_last_loss = state.last_loss
        prior_last_stop = state.last_stop
        reject = (
            spec is not None
            and pre.base_multiplier <= cap
            and _should_block(semantics=semantics, state=state)
        )
        reason = "ALLOW"
        if reject:
            reason = f"{semantics}_ONE_SHOT_COOLDOWN"
            abstained += 1
            _consume_token(state)

        decisions.append(
            FailureDecision(
                period=period,
                policy=policy,
                symbol=trade.symbol,
                session=trade.session,
                entry_at=trade.entry_at,
                fingerprint=fp,
                base_multiplier=str(pre.base_multiplier),
                prior_loss_streak=prior_loss_streak,
                prior_last_loss=prior_last_loss,
                prior_last_stop=prior_last_stop,
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
                fingerprint=fp,
                normalized_realized_r=unscaled.realized_gross_r,
                exit_reason=unscaled.exit_reason,
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


def _load_windows(
    development_root: Path,
    validation_root: Path,
    reserved_root: Path,
    development_validation_context_root: Path,
    reserved_context_root: Path,
) -> tuple[dict[str, tuple[dict[str, tuple[milestone.SimulatedTrade, ...]], dict[Any, Any]]], dict[str, Any]]:
    development = router._load_selected(
        development_root,
        expected=v10.EXPECTED_DEVELOPMENT_TRADES,
    )
    validation = router._load_selected(
        validation_root,
        expected=v10.EXPECTED_VALIDATION_TRADES,
    )
    raw_reserved = {
        mode.value: direct._load_mode(reserved_root, mode=mode)
        for mode in milestone.ProtectionMode
    }
    reserved = {
        mode: direct._max3_milestone(rows)
        for mode, rows in raw_reserved.items()
    }
    if {len(rows) for rows in reserved.values()} != {v10.EXPECTED_RESERVED_TRADES}:
        raise ValueError("V13 reserved population mismatch")

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
    reserved_context = edge_v6._load_reserved_contexts(
        reserved_context_root,
        baseline_keys=reserved_keys,
    )
    contextual_model = router._freeze_model(
        development=development,
        contexts=dev_context,
    )
    windows = {
        v10.DEVELOPMENT_PERIOD: (development, dev_context),
        "CONSUMED_VALIDATION_2022_2024": (validation, val_context),
        "CONSUMED_RESERVED_2020_2022": (reserved, reserved_context),
    }
    return windows, contextual_model


def build_report(
    development_root: Path,
    validation_root: Path,
    reserved_root: Path,
    development_validation_context_root: Path,
    reserved_context_root: Path,
) -> tuple[dict[str, Any], tuple[FailureDecision, ...]]:
    windows, contextual_model = _load_windows(
        development_root,
        validation_root,
        reserved_root,
        development_validation_context_root,
        reserved_context_root,
    )

    controls: dict[str, dict[str, Any]] = {}
    audits: list[FailureDecision] = []
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

    candidates = tuple(
        row
        for row in results
        if row["policy"] != "SURFACE_CONTROL"
        and row["all_consumed_full_gate"]
        and row["all_consumed_dd6"]
    )
    return {
        "identity": IDENTITY,
        "evaluation": "PREQUENTIAL_ONE_SHOT_FAILURE_MEMORY_ABSTENTION",
        "minimum_density_retention": str(MIN_DENSITY_RETENTION),
        "policy_specs": {
            key: [family, semantics, str(cap)]
            for key, (family, semantics, cap) in POLICY_SPECS.items()
        },
        "results": results,
        "candidate_count": len(candidates),
        "one_shot_token_consumed_without_counterfactual": True,
        "accepted_outcome_visible_only_after_exit": True,
        "blocked_outcomes_visible_to_memory": False,
        "current_outcome_visible_to_decision": False,
        "selected_ledger_diagnostic_only": True,
        "full_source_recompetition_required_before_freeze": True,
        "target_r": "2.00",
        "max3_ceiling_preserved": True,
        "automatic_policy_promotion": False,
        "trader_certified": False,
        "live_authorized": False,
        "real_capital_authorized": False,
        "next_phase": (
            "REPLAY_V13_RULE_THROUGH_FULL_SOURCE_COMPETITION"
            if candidates
            else "BUILD_DRAWDOWN_PATH_CAUSAL_BUDGET_V14"
        ),
    }, tuple(audits)


def write_report(
    report: dict[str, Any],
    audits: tuple[FailureDecision, ...],
    output: Path,
) -> None:
    output.mkdir(parents=True, exist_ok=True)
    (output / "capitalizer-sequence-failure-memory-abstention-v13.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    with (
        output / "capitalizer-sequence-failure-memory-abstention-v13-decisions.jsonl"
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

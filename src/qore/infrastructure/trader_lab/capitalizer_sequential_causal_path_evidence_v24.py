"""Sequential causal path-evidence model for Capitalizer V24.

V24 replaces static state-cell exit logic with a sequential likelihood-ratio
test over the causal deterioration path.  Each held-out period is evaluated
using two independent external-period models.  Current outcome, future bars,
terminal reason and held-out counterfactual labels are never inference inputs.
"""

from __future__ import annotations

import argparse
import json
import math
from collections import defaultdict
from dataclasses import asdict, dataclass
from decimal import Decimal
from pathlib import Path
from typing import Any

from qore.infrastructure.trader_lab import (
    capitalizer_causal_probe_ranker_v10 as v10,
)
from qore.infrastructure.trader_lab import (
    capitalizer_cognitive_r_milestone_protection_2r_v1 as milestone,
)
from qore.infrastructure.trader_lab import (
    capitalizer_continuation_value_model_v22 as v22,
)
from qore.infrastructure.trader_lab import (
    capitalizer_factor_journey_probe_ranker_v11 as v11,
)
from qore.infrastructure.trader_lab import (
    capitalizer_hypothesis_survival_model_v21 as v21,
)
from qore.infrastructure.trader_lab import (
    capitalizer_intratrade_hypothesis_invalidation_v18 as v18,
)
from qore.infrastructure.trader_lab import (
    capitalizer_intratrade_hypothesis_state_machine_v20 as v20,
)
from qore.infrastructure.trader_lab import (
    capitalizer_sequence_failure_memory_abstention_v13 as v13,
)

IDENTITY = "QORE_CAPITALIZER_SEQUENTIAL_CAUSAL_PATH_EVIDENCE_V24"
POLICY = "INVALIDATING_SEQ_BF3_POSMEAN_N30_T3"
POLICIES = ("SURFACE_CONTROL", POLICY)
MINIMUM_SUPPORT = 30
MINIMUM_SUPPORTED_TRANSITIONS = 3
BAYES_FACTOR_MINIMUM = 3.0
SMOOTHING = 1

DETERIORATION_PHASES = frozenset(
    {v20.Phase.WEAKENING.value, v20.Phase.INVALIDATING.value}
)


@dataclass(frozen=True, slots=True)
class TokenStats:
    support: int
    exit_better_occurrences: int
    continue_better_occurrences: int
    sum_exit_advantage_r: str


@dataclass(frozen=True, slots=True)
class CellStats:
    exit_total: int
    continue_total: int
    vocabulary_size: int
    tokens: dict[str, TokenStats]


Model = dict[str, dict[str, CellStats]]


@dataclass(frozen=True, slots=True)
class SequentialDecision:
    period: str
    policy: str
    symbol: str
    entry_at: str
    observed_at: str
    phase: str
    token: str
    hierarchy_level: str | None
    hierarchy_key: str | None
    trainer_a_period: str
    trainer_b_period: str
    trainer_a_support: int
    trainer_b_support: int
    trainer_a_token_bf: str | None
    trainer_b_token_bf: str | None
    trainer_a_cumulative_bf: str
    trainer_b_cumulative_bf: str
    trainer_a_cumulative_mean_advantage_r: str
    trainer_b_cumulative_mean_advantage_r: str
    supported_transition_count: int
    structural_gate: bool
    support_gate: bool
    evidence_gate: bool
    exit_applied: bool
    current_outcome_visible: bool = False
    future_bars_visible: bool = False
    original_exit_bar_used: bool = False
    unchosen_counterfactual_visible: bool = False
    heldout_training_label_visible: bool = False


def _phase_transition(previous: str, current: str) -> str:
    if previous == v20.Phase.ALIVE.value and current == v20.Phase.ALIVE.value:
        return "ALIVE_TO_ALIVE"
    if current == v20.Phase.WEAKENING.value and previous in {
        v20.Phase.ALIVE.value,
        v20.Phase.WEAKENING.value,
    }:
        return (
            "ALIVE_TO_WEAKENING"
            if previous == v20.Phase.ALIVE.value
            else "WEAKENING_TO_WEAKENING"
        )
    if current == v20.Phase.INVALIDATING.value and previous in {
        v20.Phase.ALIVE.value,
        v20.Phase.WEAKENING.value,
        v20.Phase.INVALIDATING.value,
    }:
        if previous == v20.Phase.INVALIDATING.value:
            return "INVALIDATING_TO_INVALIDATING"
        return "DETERIORATION_TO_INVALIDATING"
    if (
        previous == v20.Phase.INVALIDATING.value
        and current == v20.Phase.RECOVERED.value
    ):
        return "INVALIDATING_TO_RECOVERED"
    if (
        previous == v20.Phase.RECOVERED.value
        and current == v20.Phase.ALIVE.value
    ):
        return "RECOVERED_TO_ALIVE"
    return "OTHER"


def _velocity_state(previous: v21.Observation, current: v21.Observation) -> str:
    delta = Decimal(current.close_r) - Decimal(previous.close_r)
    if delta >= Decimal("0.05"):
        return "IMPROVING"
    if delta <= Decimal("-0.05"):
        return "DETERIORATING"
    return "FLAT"


def _progress_state(previous: v21.Observation, current: v21.Observation) -> str:
    if Decimal(current.max_favorable_r) > Decimal(previous.max_favorable_r):
        return "NEW_MFE"
    return "STALLED_MFE"


def _structural_event(current: v21.Observation) -> str:
    if current.displacement_midpoint_reclaimed:
        return "RECLAIM"
    if current.adverse_extreme_extended:
        return "ADVERSE_EXTENSION"
    if current.adverse_displacement_observed:
        return "DISPLACEMENT_PRESENT"
    return "NONE"


def _transition_token(
    previous: v21.Observation,
    current: v21.Observation,
) -> str:
    return "|".join(
        (
            _phase_transition(previous.phase, current.phase),
            _velocity_state(previous, current),
            _progress_state(previous, current),
            _structural_event(current),
        )
    )


def _hierarchy_keys(ctx: Any) -> tuple[tuple[str, str], ...]:
    return (
        ("R0", str(ctx.context_signature)),
        ("R1", str(ctx.regime_signature)),
        ("R2", str(ctx.destination_state)),
        ("R3", "GLOBAL"),
    )


def _group_observations(
    observations: tuple[v21.Observation, ...],
) -> dict[tuple[str, str, str], tuple[v21.Observation, ...]]:
    grouped: dict[tuple[str, str, str], list[v21.Observation]] = defaultdict(list)
    for row in observations:
        grouped[(row.period, row.symbol, row.entry_at)].append(row)
    return {
        key: tuple(
            sorted(rows, key=lambda item: v18._aware(item.observed_at))
        )
        for key, rows in grouped.items()
    }


def _training_transitions(
    rows: tuple[v21.Observation, ...],
    *,
    base_exit_at: str,
) -> tuple[tuple[v21.Observation, v21.Observation, str], ...]:
    result: list[tuple[v21.Observation, v21.Observation, str]] = []
    active = False
    for previous, current in zip(rows, rows[1:], strict=False):
        if v18._aware(current.observed_at) >= v18._aware(base_exit_at):
            break
        if current.phase == v20.Phase.RECOVERED.value:
            active = False
            continue
        if current.phase not in DETERIORATION_PHASES:
            if active:
                active = False
            continue
        if not active:
            active = True
        result.append((previous, current, _transition_token(previous, current)))
    return tuple(result)


def _build_model(
    *,
    period: str,
    observations: tuple[v21.Observation, ...],
    contexts: dict[tuple[str, str], Any],
    control_decisions: dict[
        tuple[str, str], v18.InvalidationDecision
    ],
) -> Model:
    grouped = _group_observations(observations)

    class_seen: set[tuple[str, str, str, str, str, str]] = set()
    token_seen: set[tuple[str, str, str, str, str]] = set()

    class_counts: dict[
        str, dict[str, dict[str, list[int]]]
    ] = {
        level: defaultdict(lambda: defaultdict(lambda: [0, 0]))
        for level in ("R0", "R1", "R2", "R3")
    }
    token_support: dict[
        str, dict[str, dict[str, list[Any]]]
    ] = {
        level: defaultdict(lambda: defaultdict(lambda: [0, Decimal("0")]))
        for level in ("R0", "R1", "R2", "R3")
    }

    for (row_period, symbol, entry_at), rows in grouped.items():
        if row_period != period:
            continue
        key = (symbol, entry_at)
        decision = control_decisions.get(key)
        if decision is None:
            continue
        ctx = contexts[key]
        final_surface_r = Decimal(decision.normalized_realized_r)

        for _previous, current, token in _training_transitions(
            rows,
            base_exit_at=decision.final_exit_at,
        ):
            advantage = Decimal(current.close_r) - final_surface_r
            class_name = (
                "EXIT_BETTER" if advantage > 0 else "CONTINUE_BETTER"
            )
            trade_id = f"{symbol}|{entry_at}"

            for level, hierarchy_key in _hierarchy_keys(ctx):
                class_marker = (
                    trade_id,
                    level,
                    hierarchy_key,
                    token,
                    class_name,
                    period,
                )
                if class_marker not in class_seen:
                    class_seen.add(class_marker)
                    bucket = class_counts[level][hierarchy_key][token]
                    if class_name == "EXIT_BETTER":
                        bucket[0] += 1
                    else:
                        bucket[1] += 1

                support_marker = (
                    trade_id,
                    level,
                    hierarchy_key,
                    token,
                    period,
                )
                if support_marker not in token_seen:
                    token_seen.add(support_marker)
                    support_bucket = token_support[level][hierarchy_key][token]
                    support_bucket[0] += 1
                    support_bucket[1] += advantage

    result: Model = {level: {} for level in ("R0", "R1", "R2", "R3")}
    for level in result:
        keys = set(class_counts[level]) | set(token_support[level])
        for hierarchy_key in keys:
            class_tokens = class_counts[level][hierarchy_key]
            support_tokens = token_support[level][hierarchy_key]
            tokens = set(class_tokens) | set(support_tokens)
            token_rows: dict[str, TokenStats] = {}
            exit_total = 0
            continue_total = 0
            for token in tokens:
                exits, continues = class_tokens[token]
                support, sum_advantage = support_tokens[token]
                exit_total += exits
                continue_total += continues
                token_rows[token] = TokenStats(
                    support=int(support),
                    exit_better_occurrences=int(exits),
                    continue_better_occurrences=int(continues),
                    sum_exit_advantage_r=str(sum_advantage),
                )
            result[level][hierarchy_key] = CellStats(
                exit_total=exit_total,
                continue_total=continue_total,
                vocabulary_size=max(1, len(tokens)),
                tokens=token_rows,
            )
    return result


def _token_evidence(
    *,
    cell: CellStats,
    token: str,
) -> tuple[int, float, Decimal] | None:
    stats = cell.tokens.get(token)
    if stats is None:
        return None

    probability_exit = (
        stats.exit_better_occurrences + SMOOTHING
    ) / (
        cell.exit_total + SMOOTHING * cell.vocabulary_size
    )
    probability_continue = (
        stats.continue_better_occurrences + SMOOTHING
    ) / (
        cell.continue_total + SMOOTHING * cell.vocabulary_size
    )
    if probability_exit <= 0 or probability_continue <= 0:
        raise ValueError("V24 smoothed token probabilities must be positive")

    token_bf = probability_exit / probability_continue
    mean_advantage = Decimal(stats.sum_exit_advantage_r) / Decimal(
        stats.support
    )
    return stats.support, token_bf, mean_advantage


def _lookup_common_evidence(
    *,
    ctx: Any,
    token: str,
    model_a: Model,
    model_b: Model,
) -> tuple[
    str | None,
    str | None,
    tuple[int, float, Decimal] | None,
    tuple[int, float, Decimal] | None,
]:
    for level, hierarchy_key in _hierarchy_keys(ctx):
        left_cell = model_a[level].get(hierarchy_key)
        right_cell = model_b[level].get(hierarchy_key)
        if left_cell is None or right_cell is None:
            continue
        left = _token_evidence(cell=left_cell, token=token)
        right = _token_evidence(cell=right_cell, token=token)
        if left is None or right is None:
            continue
        if left[0] >= MINIMUM_SUPPORT and right[0] >= MINIMUM_SUPPORT:
            return level, hierarchy_key, left, right
    return None, None, None, None


def _build_events(
    *,
    windows: dict[str, Any],
    observations: tuple[v21.Observation, ...],
    control_maps: dict[
        str, dict[tuple[str, str], v18.InvalidationDecision]
    ],
) -> tuple[
    dict[tuple[str, str, str, str], v18.TriggerEvent],
    tuple[SequentialDecision, ...],
    dict[str, Any],
]:
    models: dict[str, Model] = {}
    for period, (_ledgers, contexts) in windows.items():
        models[period] = _build_model(
            period=period,
            observations=observations,
            contexts=contexts,
            control_decisions=control_maps[period],
        )

    grouped = _group_observations(observations)
    events: dict[tuple[str, str, str, str], v18.TriggerEvent] = {}
    audits: list[SequentialDecision] = []
    model_audit: dict[str, Any] = {}

    for heldout, (ledgers, contexts) in windows.items():
        selected_keys = {
            (row.symbol, row.entry_at)
            for row in ledgers[milestone.ProtectionMode.ORIGINAL.value]
        }
        if set(control_maps[heldout]) != selected_keys:
            raise ValueError("V24 control identity mismatch")

        trainers = tuple(period for period in windows if period != heldout)
        if len(trainers) != 2:
            raise ValueError("V24 requires exactly two external periods")
        trainer_a, trainer_b = trainers
        model_a = models[trainer_a]
        model_b = models[trainer_b]
        model_audit[heldout] = {
            "trainer_a": trainer_a,
            "trainer_b": trainer_b,
            "heldout_training_label_visible_to_inference": False,
        }

        for symbol, entry_at in sorted(selected_keys):
            key = (symbol, entry_at)
            rows = grouped.get((heldout, symbol, entry_at), ())
            if len(rows) < 2:
                continue
            decision = control_maps[heldout][key]
            ctx = contexts[key]

            active = False
            triggered = False
            supported_transitions = 0
            log_bf_a = 0.0
            log_bf_b = 0.0
            sum_mean_a = Decimal("0")
            sum_mean_b = Decimal("0")

            for previous, current in zip(rows, rows[1:], strict=False):
                if triggered:
                    break
                if v18._aware(current.observed_at) >= v18._aware(
                    decision.final_exit_at
                ):
                    break

                if current.phase == v20.Phase.RECOVERED.value:
                    active = False
                    supported_transitions = 0
                    log_bf_a = 0.0
                    log_bf_b = 0.0
                    sum_mean_a = Decimal("0")
                    sum_mean_b = Decimal("0")
                    continue

                if current.phase not in DETERIORATION_PHASES:
                    if active:
                        active = False
                        supported_transitions = 0
                        log_bf_a = 0.0
                        log_bf_b = 0.0
                        sum_mean_a = Decimal("0")
                        sum_mean_b = Decimal("0")
                    continue

                if not active:
                    active = True
                    supported_transitions = 0
                    log_bf_a = 0.0
                    log_bf_b = 0.0
                    sum_mean_a = Decimal("0")
                    sum_mean_b = Decimal("0")

                token = _transition_token(previous, current)
                level, hierarchy_key, left, right = _lookup_common_evidence(
                    ctx=ctx,
                    token=token,
                    model_a=model_a,
                    model_b=model_b,
                )
                support_gate = left is not None and right is not None
                token_bf_a: float | None = None
                token_bf_b: float | None = None
                support_a = 0
                support_b = 0

                if support_gate:
                    assert left is not None
                    assert right is not None
                    support_a, token_bf_a, mean_a = left
                    support_b, token_bf_b, mean_b = right
                    supported_transitions += 1
                    log_bf_a += math.log(token_bf_a)
                    log_bf_b += math.log(token_bf_b)
                    sum_mean_a += mean_a
                    sum_mean_b += mean_b

                cumulative_bf_a = math.exp(log_bf_a)
                cumulative_bf_b = math.exp(log_bf_b)
                cumulative_mean_a = (
                    Decimal("0")
                    if supported_transitions == 0
                    else sum_mean_a / Decimal(supported_transitions)
                )
                cumulative_mean_b = (
                    Decimal("0")
                    if supported_transitions == 0
                    else sum_mean_b / Decimal(supported_transitions)
                )

                structural_gate = (
                    current.phase == v20.Phase.INVALIDATING.value
                )
                evidence_gate = (
                    support_gate
                    and supported_transitions
                    >= MINIMUM_SUPPORTED_TRANSITIONS
                    and cumulative_bf_a >= BAYES_FACTOR_MINIMUM
                    and cumulative_bf_b >= BAYES_FACTOR_MINIMUM
                    and cumulative_mean_a > 0
                    and cumulative_mean_b > 0
                )
                close_r = Decimal(current.close_r)
                apply = (
                    structural_gate
                    and evidence_gate
                    and close_r > Decimal("-1")
                )

                audits.append(
                    SequentialDecision(
                        period=heldout,
                        policy=POLICY,
                        symbol=current.symbol,
                        entry_at=current.entry_at,
                        observed_at=current.observed_at,
                        phase=current.phase,
                        token=token,
                        hierarchy_level=level,
                        hierarchy_key=hierarchy_key,
                        trainer_a_period=trainer_a,
                        trainer_b_period=trainer_b,
                        trainer_a_support=support_a,
                        trainer_b_support=support_b,
                        trainer_a_token_bf=(
                            None if token_bf_a is None else str(token_bf_a)
                        ),
                        trainer_b_token_bf=(
                            None if token_bf_b is None else str(token_bf_b)
                        ),
                        trainer_a_cumulative_bf=str(cumulative_bf_a),
                        trainer_b_cumulative_bf=str(cumulative_bf_b),
                        trainer_a_cumulative_mean_advantage_r=str(
                            cumulative_mean_a
                        ),
                        trainer_b_cumulative_mean_advantage_r=str(
                            cumulative_mean_b
                        ),
                        supported_transition_count=supported_transitions,
                        structural_gate=structural_gate,
                        support_gate=support_gate,
                        evidence_gate=evidence_gate,
                        exit_applied=apply,
                    )
                )
                if not apply:
                    continue

                triggered = True
                events[(heldout, symbol, entry_at, POLICY)] = v18.TriggerEvent(
                    period=heldout,
                    symbol=current.symbol,
                    session=current.session,
                    operating_date=current.operating_date,
                    entry_at=current.entry_at,
                    trigger=POLICY,
                    trigger_at=current.observed_at,
                    trigger_r=current.close_r,
                    elapsed_full_bars=current.elapsed_full_bars,
                    max_favorable_r_before_trigger=current.max_favorable_r,
                )

    return events, tuple(audits), model_audit


def build_report(
    development_root: Path,
    validation_root: Path,
    reserved_root: Path,
    development_validation_context_root: Path,
    reserved_context_root: Path,
    v21_evidence_root: Path,
) -> tuple[
    dict[str, Any],
    tuple[SequentialDecision, ...],
    tuple[v18.InvalidationDecision, ...],
]:
    windows, contextual_model = v13._load_windows(
        development_root,
        validation_root,
        reserved_root,
        development_validation_context_root,
        reserved_context_root,
    )
    observations, _labels = v21._load_market_evidence(v21_evidence_root)
    controls, _control_rows, control_maps = v22._control_decision_maps(
        windows,
        contextual_model,
    )
    events, sequential_audits, model_audit = _build_events(
        windows=windows,
        observations=observations,
        control_maps=control_maps,
    )

    simultaneous: dict[
        tuple[str, str, str], tuple[milestone.SimulatedTrade, ...]
    ] = {}
    for period, (ledgers, _contexts) in windows.items():
        simultaneous.update(
            v11._simultaneous_map(period=period, ledgers=ledgers)
        )

    previous_simultaneous = dict(v11._SIMULTANEOUS)
    previous_policy_specs = dict(v18.POLICY_SPECS)
    v11._SIMULTANEOUS.clear()
    v11._SIMULTANEOUS.update(simultaneous)
    v18.POLICY_SPECS.clear()
    v18.POLICY_SPECS[POLICY] = (POLICY, None, None)

    economic_audits: list[v18.InvalidationDecision] = []
    try:
        results: list[dict[str, Any]] = []
        for policy in POLICIES:
            heldouts: dict[str, Any] = {}
            for period, (ledgers, contexts) in windows.items():
                if policy == "SURFACE_CONTROL":
                    current = controls[period]
                else:
                    current, audit = v18._simulate(
                        period=period,
                        policy=policy,
                        ledgers=ledgers,
                        contexts=contexts,
                        contextual_model=contextual_model,
                        events=events,
                    )
                    economic_audits.extend(audit)
                v10._annotate(current, controls[period])
                current["losing_streak_not_worse"] = (
                    int(current["metrics"]["max_losing_streak"])
                    <= int(controls[period]["metrics"]["max_losing_streak"])
                )
                heldouts[period] = current

            full_gate = all(
                row["pf_at_least_surface_control"]
                and row["total_r_at_least_surface_control"]
                and row["dd_below_surface_control"]
                and row["dd_at_or_below_6r"]
                and row["losing_streak_not_worse"]
                for row in heldouts.values()
            )
            total_exits = sum(
                int(row["invalidation_count"])
                for row in heldouts.values()
            )
            results.append(
                {
                    "policy": policy,
                    "heldouts": heldouts,
                    "total_sequential_exits": total_exits,
                    "all_consumed_full_gate": full_gate,
                }
            )
    finally:
        v18.POLICY_SPECS.clear()
        v18.POLICY_SPECS.update(previous_policy_specs)
        v11._SIMULTANEOUS.clear()
        v11._SIMULTANEOUS.update(previous_simultaneous)

    candidates = tuple(
        row
        for row in results
        if row["policy"] != "SURFACE_CONTROL"
        and row["total_sequential_exits"] > 0
        and row["all_consumed_full_gate"]
    )

    support_rows = tuple(row for row in sequential_audits if row.support_gate)
    evidence_rows = tuple(row for row in sequential_audits if row.evidence_gate)
    applied_rows = tuple(row for row in sequential_audits if row.exit_applied)

    return {
        "identity": IDENTITY,
        "evaluation": "SEQUENTIAL_CAUSAL_PATH_LIKELIHOOD_RATIO",
        "policy": POLICY,
        "canonical_lifecycle_track": v21.CANONICAL_TRACK,
        "departure_r": str(v21.DEPARTURE_R),
        "minimum_unique_trade_support_per_external_model": MINIMUM_SUPPORT,
        "minimum_supported_transitions": MINIMUM_SUPPORTED_TRANSITIONS,
        "bayes_factor_minimum_each_external_model": str(
            BAYES_FACTOR_MINIMUM
        ),
        "smoothing": "SYMMETRIC_LAPLACE_PLUS_1",
        "entry_regime_hierarchy": ["R0", "R1", "R2", "R3"],
        "anti_pseudoreplication": (
            "UNIQUE_TRADE_PER_HIERARCHY_TOKEN_CLASS_AND_TOKEN_SUPPORT"
        ),
        "model_audit": model_audit,
        "decision_rows": len(sequential_audits),
        "support_qualified_rows": len(support_rows),
        "evidence_qualified_rows": len(evidence_rows),
        "applied_exit_rows": len(applied_rows),
        "results": results,
        "candidate_count": len(candidates),
        "all_entries_preserved": True,
        "density_retention": "1",
        "surface_multiplier_preserved": True,
        "fixed_target_r": "2.00",
        "original_stop_geometry_preserved": True,
        "max3_preserved": True,
        "symbol_session_side_time_features_used": False,
        "current_outcome_visible_to_decision": False,
        "future_bars_visible_to_decision": False,
        "original_exit_bar_excluded": True,
        "unchosen_counterfactual_visible_to_decision": False,
        "heldout_training_label_visible_to_decision": False,
        "training_label_uses_final_surface_r": True,
        "training_label_visible_to_heldout_inference": False,
        "full_source_recompetition_required_before_freeze": True,
        "historical_fresh_oos_available": False,
        "2018_2020_status": "CONSUMED_NOT_FRESH",
        "automatic_policy_promotion": False,
        "trader_certified": False,
        "live_authorized": False,
        "real_capital_authorized": False,
        "next_phase": (
            "FULL_SOURCE_RECOMPETITION_V24_SURVIVOR"
            if candidates
            else "V24_FALSIFIED_REPRESENTATION_CHANGE_REQUIRED"
        ),
    }, sequential_audits, tuple(economic_audits)


def write_report(
    report: dict[str, Any],
    sequential_audits: tuple[SequentialDecision, ...],
    economic_audits: tuple[v18.InvalidationDecision, ...],
    output: Path,
) -> None:
    output.mkdir(parents=True, exist_ok=True)
    (output / "capitalizer-sequential-causal-path-evidence-v24.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    with (
        output / "capitalizer-sequential-causal-path-evidence-v24-decisions.jsonl"
    ).open("w", encoding="utf-8") as handle:
        for row in sequential_audits:
            handle.write(json.dumps(asdict(row), sort_keys=True) + "\n")
    with (
        output / "capitalizer-sequential-causal-path-evidence-v24-economics.jsonl"
    ).open("w", encoding="utf-8") as handle:
        for row in economic_audits:
            handle.write(json.dumps(asdict(row), sort_keys=True) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("development_root", type=Path)
    parser.add_argument("validation_root", type=Path)
    parser.add_argument("reserved_root", type=Path)
    parser.add_argument("development_validation_context_root", type=Path)
    parser.add_argument("reserved_context_root", type=Path)
    parser.add_argument("v21_evidence_root", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()

    report, sequential_audits, economic_audits = build_report(
        args.development_root,
        args.validation_root,
        args.reserved_root,
        args.development_validation_context_root,
        args.reserved_context_root,
        args.v21_evidence_root,
    )
    write_report(
        report,
        sequential_audits,
        economic_audits,
        args.output,
    )
    print(json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    main()

"""Exact multi-position causal episode interaction simulator for Capitalizer V36.

V35 falsified local single-trigger structural drawdown control. V36 therefore
tests the next frozen mechanism before training another controller: whether
joint interventions on two concurrently-active positions inside the Surface
maximum-drawdown descent create economically useful interaction that cannot be
seen by isolated single-action scoring.

This module is diagnostic and outcome-aware by design. It is never a runtime
policy candidate. It preserves the frozen entrant set, density, sizing law,
target, stop-at-entry geometry, and the existing protection-mode toolbox.

Candidate reduction is deterministic and mechanical, not threshold tuning:
for every entrant in the Surface max-DD descent, retain at most two actions from
the authoritative single-action transition evidence:
  * TAIL_MIN: action with minimum exact single-rollout legacy DD;
  * VALUE_MAX: action with maximum exact single-rollout Total-R.
Duplicate actions collapse to one seed.

Only pairs on distinct entrants are evaluated, and only when the two positions
are concurrently active at at least one of their causal protection-trigger
timestamps under the Surface path. Each pair is then replayed exactly through
the existing dynamic plan engine, so later Surface modes, multipliers, memory,
and feedback are recomputed.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

from qore.infrastructure.trader_lab import (
    capitalizer_cognitive_r_milestone_protection_2r_v1 as milestone,
)
from qore.infrastructure.trader_lab import (
    capitalizer_counterfactual_portfolio_episode_simulator_v1 as simulator,
)
from qore.infrastructure.trader_lab import (
    capitalizer_dynamic_episode_sequence_feasibility_v1 as sequence_v1,
)
from qore.infrastructure.trader_lab import (
    capitalizer_factor_journey_probe_ranker_v11 as v11,
)
from qore.infrastructure.trader_lab import (
    capitalizer_portfolio_drawdown_feasibility_episode_anatomy_v1 as anatomy,
)
from qore.infrastructure.trader_lab import (
    capitalizer_sequence_failure_memory_abstention_v13 as v13,
)

IDENTITY = "QORE_CAPITALIZER_MULTI_POSITION_CAUSAL_EPISODE_SIMULATOR_V36"
SOURCE_TRANSITION_IDENTITY = (
    "QORE_CAPITALIZER_COUNTERFACTUAL_PORTFOLIO_EPISODE_SIMULATOR_V1"
)
ROLE_ORDER = ("TAIL_MIN", "VALUE_MAX")
MODE_ORDER = tuple(mode.value for mode in milestone.ProtectionMode)


@dataclass(frozen=True, slots=True)
class EpisodeSeed:
    period: str
    symbol: str
    entry_at: str
    trigger_at: str
    surface_mode: str
    action: str
    role: str
    source_single_total_r: str
    source_single_legacy_dd_r: str
    source_dynamic_total_delta_r: str
    source_legacy_dd_relief_r: str


@dataclass(frozen=True, slots=True)
class SingleReplay:
    seed: EpisodeSeed
    total_r: str
    profit_factor: str | None
    max_drawdown_r: str
    max_losing_streak: int
    dynamic_total_delta_r: str
    legacy_dd_relief_r: str


@dataclass(frozen=True, slots=True)
class PairAudit:
    period: str
    first_symbol: str
    first_entry_at: str
    first_trigger_at: str
    first_action: str
    first_role: str
    second_symbol: str
    second_entry_at: str
    second_trigger_at: str
    second_action: str
    second_role: str
    overlap_start_at: str
    overlap_end_at: str
    joint_active_trigger_at: str
    exact_pair_replay_valid: bool
    invalid_reason: str | None
    pair_profit_factor: str | None
    pair_total_r: str | None
    pair_max_drawdown_r: str | None
    pair_max_losing_streak: int | None
    pair_dynamic_total_delta_r: str | None
    pair_legacy_dd_relief_r: str | None
    first_single_dynamic_total_delta_r: str
    second_single_dynamic_total_delta_r: str
    first_single_legacy_dd_relief_r: str
    second_single_legacy_dd_relief_r: str
    total_interaction_r: str | None
    dd_relief_interaction_r: str | None
    improves_total_r_and_legacy_dd: bool
    beats_both_singles_on_dd: bool
    beats_both_singles_on_total_r: bool
    physical_full_gate_passed: bool
    owner_pf_per_era_gate_passed: bool | None
    same_entrant_identities: bool
    density_retention: str
    outcome_used_for_diagnostic_scoring: bool = True
    runtime_policy_candidate: bool = False
    fresh_holdout_opened: bool = False


def _aware(value: str) -> datetime:
    return milestone._aware(value)


def _mode_rank(action: str) -> int:
    return MODE_ORDER.index(action)


def _load_transition_rows(
    path: Path,
) -> dict[str, tuple[dict[str, Any], ...]]:
    result: dict[str, list[dict[str, Any]]] = {}
    with path.open(encoding="utf-8") as handle:
        for raw in handle:
            if not raw.strip():
                continue
            row = json.loads(raw)
            if not isinstance(row, dict):
                raise ValueError("V36 transition row must be object")
            if "period" not in row:
                raise ValueError("V36 transition row missing period")
            result.setdefault(str(row["period"]), []).append(row)
    return {
        period: tuple(rows)
        for period, rows in result.items()
    }


def _select_episode_seeds(
    rows: tuple[dict[str, Any], ...],
    *,
    period: str,
) -> tuple[EpisodeSeed, ...]:
    grouped: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for row in rows:
        if str(row.get("period")) != period:
            continue
        if not bool(row.get("entrant_in_surface_max_dd_descent")):
            continue
        key = (str(row["symbol"]), str(row["entry_at"]))
        grouped.setdefault(key, []).append(row)

    seeds: dict[tuple[str, str, str], EpisodeSeed] = {}
    for key, candidates in grouped.items():
        if not candidates:
            continue

        tail = min(
            candidates,
            key=lambda row: (
                Decimal(str(row["rollout_legacy_dd_r"])),
                -Decimal(str(row["rollout_total_r"])),
                _mode_rank(str(row["action"])),
            ),
        )
        value = min(
            candidates,
            key=lambda row: (
                -Decimal(str(row["rollout_total_r"])),
                Decimal(str(row["rollout_legacy_dd_r"])),
                _mode_rank(str(row["action"])),
            ),
        )

        for role, row in (("TAIL_MIN", tail), ("VALUE_MAX", value)):
            seed = EpisodeSeed(
                period=period,
                symbol=key[0],
                entry_at=key[1],
                trigger_at=str(row["trigger_at"]),
                surface_mode=str(row["surface_mode"]),
                action=str(row["action"]),
                role=role,
                source_single_total_r=str(row["rollout_total_r"]),
                source_single_legacy_dd_r=str(
                    row["rollout_legacy_dd_r"]
                ),
                source_dynamic_total_delta_r=str(
                    row["dynamic_total_delta_r"]
                ),
                source_legacy_dd_relief_r=str(
                    row["legacy_dd_relief_r"]
                ),
            )
            dedupe_key = (seed.symbol, seed.entry_at, seed.action)
            prior = seeds.get(dedupe_key)
            if prior is None:
                seeds[dedupe_key] = seed
            elif ROLE_ORDER.index(role) < ROLE_ORDER.index(prior.role):
                seeds[dedupe_key] = seed

    return tuple(
        sorted(
            seeds.values(),
            key=lambda seed: (
                _aware(seed.entry_at),
                seed.symbol,
                ROLE_ORDER.index(seed.role),
                _mode_rank(seed.action),
            ),
        )
    )


def _interval(
    row: milestone.SimulatedTrade,
) -> tuple[datetime, datetime]:
    start = _aware(row.entry_at)
    end = _aware(row.exit_at)
    if end <= start:
        raise ValueError("V36 trade interval must be positive")
    return start, end


def _joint_active_trigger(
    *,
    first_seed: EpisodeSeed,
    second_seed: EpisodeSeed,
    first_row: milestone.SimulatedTrade,
    second_row: milestone.SimulatedTrade,
) -> tuple[datetime, datetime, datetime] | None:
    first_start, first_end = _interval(first_row)
    second_start, second_end = _interval(second_row)
    overlap_start = max(first_start, second_start)
    overlap_end = min(first_end, second_end)
    if overlap_end <= overlap_start:
        return None

    triggers = tuple(
        sorted(
            (
                _aware(first_seed.trigger_at),
                _aware(second_seed.trigger_at),
            )
        )
    )
    joint_trigger = next(
        (
            trigger
            for trigger in triggers
            if overlap_start <= trigger < overlap_end
        ),
        None,
    )
    if joint_trigger is None:
        return None
    return overlap_start, overlap_end, joint_trigger


def _physical_full_gate(
    metrics: dict[str, Any],
    *,
    baseline: dict[str, Any],
    intervention_count: int,
) -> bool:
    return sequence_v1._full_gate(
        metrics,
        baseline=baseline,
        intervention_count=intervention_count,
    )


def _single_replays(
    *,
    period: str,
    seeds: tuple[EpisodeSeed, ...],
    ledgers: dict[str, tuple[milestone.SimulatedTrade, ...]],
    contexts: dict[tuple[str, str], Any],
    contextual_model: dict[str, Any],
    baseline: dict[str, Any],
) -> dict[tuple[str, str, str], SingleReplay]:
    baseline_total = Decimal(baseline["total_r"])
    baseline_dd = Decimal(baseline["max_drawdown_r"])
    result: dict[tuple[str, str, str], SingleReplay] = {}

    for seed in seeds:
        key = (seed.symbol, seed.entry_at)
        try:
            ledger, _decisions, applied = sequence_v1._replay_plan(
                period=period,
                ledgers=ledgers,
                contexts=contexts,
                contextual_model=contextual_model,
                plan={key: seed.action},
            )
        except sequence_v1.InvalidPlanError as exc:
            raise ValueError(
                f"V36 authoritative single seed became invalid: {seed}"
            ) from exc
        if key not in applied:
            raise ValueError("V36 single seed not applied")
        metrics = milestone._metrics(ledger)
        replay = SingleReplay(
            seed=seed,
            total_r=str(metrics["total_r"]),
            profit_factor=metrics["profit_factor"],
            max_drawdown_r=str(metrics["max_drawdown_r"]),
            max_losing_streak=int(metrics["max_losing_streak"]),
            dynamic_total_delta_r=str(
                Decimal(metrics["total_r"]) - baseline_total
            ),
            legacy_dd_relief_r=str(
                baseline_dd - Decimal(metrics["max_drawdown_r"])
            ),
        )
        result[(seed.symbol, seed.entry_at, seed.action)] = replay

    return result


def _pair_rank(row: PairAudit) -> tuple[Any, ...]:
    if not row.exact_pair_replay_valid:
        return (
            1,
            Decimal("Infinity"),
            Decimal("Infinity"),
            row.first_entry_at,
            row.first_symbol,
            row.second_entry_at,
            row.second_symbol,
        )
    assert row.pair_max_drawdown_r is not None
    assert row.pair_total_r is not None
    return (
        0,
        Decimal(row.pair_max_drawdown_r),
        -Decimal(row.pair_total_r),
        row.first_entry_at,
        row.first_symbol,
        row.second_entry_at,
        row.second_symbol,
        _mode_rank(row.first_action),
        _mode_rank(row.second_action),
    )


def _period_report(
    *,
    period: str,
    transition_rows: tuple[dict[str, Any], ...],
    ledgers: dict[str, tuple[milestone.SimulatedTrade, ...]],
    contexts: dict[tuple[str, str], Any],
    contextual_model: dict[str, Any],
) -> tuple[dict[str, Any], tuple[PairAudit, ...]]:
    control, baseline_ledger, _surface_decisions = anatomy._surface_ledger(
        period=period,
        ledgers=ledgers,
        contexts=contexts,
        contextual_model=contextual_model,
    )
    baseline_ledger, _baseline_decisions, _baseline_applied = (
        sequence_v1._replay_plan(
            period=period,
            ledgers=ledgers,
            contexts=contexts,
            contextual_model=contextual_model,
            plan={},
        )
    )
    baseline = milestone._metrics(baseline_ledger)
    if baseline != control["metrics"]:
        raise ValueError("V36 empty-plan Surface drift")

    baseline_by_key = {
        (row.symbol, row.entry_at): row for row in baseline_ledger
    }
    if len(baseline_by_key) != len(baseline_ledger):
        raise ValueError("V36 duplicate baseline entrant identity")

    seeds = _select_episode_seeds(
        transition_rows,
        period=period,
    )
    singles = _single_replays(
        period=period,
        seeds=seeds,
        ledgers=ledgers,
        contexts=contexts,
        contextual_model=contextual_model,
        baseline=baseline,
    )

    baseline_total = Decimal(baseline["total_r"])
    baseline_dd = Decimal(baseline["max_drawdown_r"])
    candidate_pairs = 0
    invalid_pairs = 0
    audits: list[PairAudit] = []

    for first_index, first in enumerate(seeds):
        first_key = (first.symbol, first.entry_at)
        first_row = baseline_by_key.get(first_key)
        if first_row is None:
            raise ValueError("V36 seed absent from baseline ledger")

        for second in seeds[first_index + 1 :]:
            second_key = (second.symbol, second.entry_at)
            if first_key == second_key:
                continue
            second_row = baseline_by_key.get(second_key)
            if second_row is None:
                raise ValueError("V36 seed absent from baseline ledger")

            overlap = _joint_active_trigger(
                first_seed=first,
                second_seed=second,
                first_row=first_row,
                second_row=second_row,
            )
            if overlap is None:
                continue
            candidate_pairs += 1
            overlap_start, overlap_end, joint_trigger = overlap

            first_single = singles[
                (first.symbol, first.entry_at, first.action)
            ]
            second_single = singles[
                (second.symbol, second.entry_at, second.action)
            ]
            plan = {
                first_key: first.action,
                second_key: second.action,
            }

            try:
                ledger, _decisions, applied = sequence_v1._replay_plan(
                    period=period,
                    ledgers=ledgers,
                    contexts=contexts,
                    contextual_model=contextual_model,
                    plan=plan,
                )
            except sequence_v1.InvalidPlanError as exc:
                invalid_pairs += 1
                audits.append(
                    PairAudit(
                        period=period,
                        first_symbol=first.symbol,
                        first_entry_at=first.entry_at,
                        first_trigger_at=first.trigger_at,
                        first_action=first.action,
                        first_role=first.role,
                        second_symbol=second.symbol,
                        second_entry_at=second.entry_at,
                        second_trigger_at=second.trigger_at,
                        second_action=second.action,
                        second_role=second.role,
                        overlap_start_at=overlap_start.isoformat(),
                        overlap_end_at=overlap_end.isoformat(),
                        joint_active_trigger_at=joint_trigger.isoformat(),
                        exact_pair_replay_valid=False,
                        invalid_reason=str(exc),
                        pair_profit_factor=None,
                        pair_total_r=None,
                        pair_max_drawdown_r=None,
                        pair_max_losing_streak=None,
                        pair_dynamic_total_delta_r=None,
                        pair_legacy_dd_relief_r=None,
                        first_single_dynamic_total_delta_r=(
                            first_single.dynamic_total_delta_r
                        ),
                        second_single_dynamic_total_delta_r=(
                            second_single.dynamic_total_delta_r
                        ),
                        first_single_legacy_dd_relief_r=(
                            first_single.legacy_dd_relief_r
                        ),
                        second_single_legacy_dd_relief_r=(
                            second_single.legacy_dd_relief_r
                        ),
                        total_interaction_r=None,
                        dd_relief_interaction_r=None,
                        improves_total_r_and_legacy_dd=False,
                        beats_both_singles_on_dd=False,
                        beats_both_singles_on_total_r=False,
                        physical_full_gate_passed=False,
                        owner_pf_per_era_gate_passed=None,
                        same_entrant_identities=True,
                        density_retention="1",
                    )
                )
                continue

            if set(applied) != set(plan):
                raise ValueError("V36 pair replay did not apply both actions")
            metrics = milestone._metrics(ledger)
            if int(metrics["trades"]) != int(baseline["trades"]):
                raise ValueError("V36 pair replay changed density")

            pair_total = Decimal(metrics["total_r"])
            pair_dd = Decimal(metrics["max_drawdown_r"])
            pair_total_delta = pair_total - baseline_total
            pair_dd_relief = baseline_dd - pair_dd
            first_total_delta = Decimal(
                first_single.dynamic_total_delta_r
            )
            second_total_delta = Decimal(
                second_single.dynamic_total_delta_r
            )
            first_dd_relief = Decimal(
                first_single.legacy_dd_relief_r
            )
            second_dd_relief = Decimal(
                second_single.legacy_dd_relief_r
            )
            total_interaction = (
                pair_total_delta - first_total_delta - second_total_delta
            )
            dd_interaction = (
                pair_dd_relief - first_dd_relief - second_dd_relief
            )
            pf = metrics["profit_factor"]
            owner_pf_pass = (
                None if pf is None else Decimal(pf) >= Decimal("1.50")
            )

            audits.append(
                PairAudit(
                    period=period,
                    first_symbol=first.symbol,
                    first_entry_at=first.entry_at,
                    first_trigger_at=first.trigger_at,
                    first_action=first.action,
                    first_role=first.role,
                    second_symbol=second.symbol,
                    second_entry_at=second.entry_at,
                    second_trigger_at=second.trigger_at,
                    second_action=second.action,
                    second_role=second.role,
                    overlap_start_at=overlap_start.isoformat(),
                    overlap_end_at=overlap_end.isoformat(),
                    joint_active_trigger_at=joint_trigger.isoformat(),
                    exact_pair_replay_valid=True,
                    invalid_reason=None,
                    pair_profit_factor=pf,
                    pair_total_r=str(pair_total),
                    pair_max_drawdown_r=str(pair_dd),
                    pair_max_losing_streak=int(
                        metrics["max_losing_streak"]
                    ),
                    pair_dynamic_total_delta_r=str(pair_total_delta),
                    pair_legacy_dd_relief_r=str(pair_dd_relief),
                    first_single_dynamic_total_delta_r=str(
                        first_total_delta
                    ),
                    second_single_dynamic_total_delta_r=str(
                        second_total_delta
                    ),
                    first_single_legacy_dd_relief_r=str(
                        first_dd_relief
                    ),
                    second_single_legacy_dd_relief_r=str(
                        second_dd_relief
                    ),
                    total_interaction_r=str(total_interaction),
                    dd_relief_interaction_r=str(dd_interaction),
                    improves_total_r_and_legacy_dd=(
                        pair_total_delta > 0 and pair_dd_relief > 0
                    ),
                    beats_both_singles_on_dd=(
                        pair_dd
                        < min(
                            Decimal(first_single.max_drawdown_r),
                            Decimal(second_single.max_drawdown_r),
                        )
                    ),
                    beats_both_singles_on_total_r=(
                        pair_total
                        > max(
                            Decimal(first_single.total_r),
                            Decimal(second_single.total_r),
                        )
                    ),
                    physical_full_gate_passed=_physical_full_gate(
                        metrics,
                        baseline=baseline,
                        intervention_count=2,
                    ),
                    owner_pf_per_era_gate_passed=owner_pf_pass,
                    same_entrant_identities=True,
                    density_retention="1",
                )
            )

    frozen = tuple(audits)
    valid = tuple(row for row in frozen if row.exact_pair_replay_valid)
    full = tuple(row for row in valid if row.physical_full_gate_passed)
    improves = tuple(
        row for row in valid if row.improves_total_r_and_legacy_dd
    )
    positive_interaction = tuple(
        row
        for row in valid
        if row.total_interaction_r is not None
        and Decimal(row.total_interaction_r) > 0
    )
    best = None if not valid else min(valid, key=_pair_rank)

    return {
        "period": period,
        "surface": baseline,
        "episode_seed_count": len(seeds),
        "episode_seed_entrant_count": len(
            {(seed.symbol, seed.entry_at) for seed in seeds}
        ),
        "candidate_concurrent_pair_count": candidate_pairs,
        "valid_exact_pair_count": len(valid),
        "invalid_after_feedback_pair_count": invalid_pairs,
        "improves_total_r_and_legacy_dd_count": len(improves),
        "positive_total_interaction_count": len(positive_interaction),
        "physical_full_gate_pair_count": len(full),
        "best_pair": (
            None
            if best is None
            else {
                "first_symbol": best.first_symbol,
                "first_entry_at": best.first_entry_at,
                "first_action": best.first_action,
                "second_symbol": best.second_symbol,
                "second_entry_at": best.second_entry_at,
                "second_action": best.second_action,
                "profit_factor": best.pair_profit_factor,
                "total_r": best.pair_total_r,
                "max_drawdown_r": best.pair_max_drawdown_r,
                "max_losing_streak": best.pair_max_losing_streak,
                "dynamic_total_delta_r": (
                    best.pair_dynamic_total_delta_r
                ),
                "legacy_dd_relief_r": best.pair_legacy_dd_relief_r,
                "total_interaction_r": best.total_interaction_r,
                "dd_relief_interaction_r": (
                    best.dd_relief_interaction_r
                ),
                "physical_full_gate_passed": (
                    best.physical_full_gate_passed
                ),
            }
        ),
        "same_entrant_identities": True,
        "density_retention": "1",
    }, frozen


def build_report(
    development_root: Path,
    validation_root: Path,
    reserved_root: Path,
    development_validation_context_root: Path,
    reserved_context_root: Path,
    transition_path: Path,
) -> tuple[dict[str, Any], tuple[PairAudit, ...]]:
    windows, contextual_model = v13._load_windows(
        development_root,
        validation_root,
        reserved_root,
        development_validation_context_root,
        reserved_context_root,
    )
    transition_rows = _load_transition_rows(transition_path)

    simultaneous: dict[
        tuple[str, str, str], tuple[milestone.SimulatedTrade, ...]
    ] = {}
    for period, (ledgers, _contexts) in windows.items():
        simultaneous.update(
            v11._simultaneous_map(
                period=period,
                ledgers=ledgers,
            )
        )

    previous = dict(v11._SIMULTANEOUS)
    v11._SIMULTANEOUS.clear()
    v11._SIMULTANEOUS.update(simultaneous)
    try:
        results: list[dict[str, Any]] = []
        audits: list[PairAudit] = []
        for period, (ledgers, contexts) in windows.items():
            rows = transition_rows.get(period)
            if rows is None:
                raise ValueError(
                    f"V36 missing transition evidence for {period}"
                )
            result, current = _period_report(
                period=period,
                transition_rows=rows,
                ledgers=ledgers,
                contexts=contexts,
                contextual_model=contextual_model,
            )
            results.append(result)
            audits.extend(current)
    finally:
        v11._SIMULTANEOUS.clear()
        v11._SIMULTANEOUS.update(previous)

    full_gate_pairs = sum(
        int(row["physical_full_gate_pair_count"])
        for row in results
    )
    any_interaction = any(
        int(row["positive_total_interaction_count"]) > 0
        or int(row["improves_total_r_and_legacy_dd_count"]) > 0
        for row in results
    )
    return {
        "identity": IDENTITY,
        "evaluation": "EXACT_CONCURRENT_TWO_POSITION_EPISODE_INTERACTION",
        "source_transition_identity": SOURCE_TRANSITION_IDENTITY,
        "transition_seed_selection": (
            "PER_MAX_DD_ENTRANT_TAIL_MIN_AND_VALUE_MAX"
        ),
        "seed_selection_numeric_threshold_added": False,
        "concurrency_requirement": (
            "DISTINCT_ENTRANTS_ACTIVE_AT_AT_LEAST_ONE_CAUSAL_TRIGGER"
        ),
        "pair_replay": "EXACT_DYNAMIC_PLAN_WITH_FEEDBACK",
        "downstream_surface_mode_recomputed": True,
        "downstream_surface_multiplier_recomputed": True,
        "memory_recomputed": True,
        "same_entrant_identities": True,
        "density_retention": "1",
        "new_protection_geometry_created": False,
        "sizing_changed": False,
        "max3_preserved": True,
        "outcome_aware_diagnostic": True,
        "runtime_policy_candidate": False,
        "fresh_holdout_opened": False,
        "results": results,
        "total_physical_full_gate_pairs": full_gate_pairs,
        "joint_interaction_evidence_found": any_interaction,
        "candidate_count": 0,
        "trader_certified": False,
        "live_authorized": False,
        "real_capital_authorized": False,
        "next_phase": (
            "BUILD_CAUSAL_MULTI_POSITION_EPISODE_CONTROLLER"
            if any_interaction
            else "PAIRWISE_EPISODE_CAPACITY_FALSIFIED_EXPAND_TO_BOUNDED_EPISODE_BEAM"
        ),
    }, tuple(audits)


def write_report(
    report: dict[str, Any],
    audits: tuple[PairAudit, ...],
    output: Path,
) -> None:
    output.mkdir(parents=True, exist_ok=True)
    stem = "capitalizer-multi-position-causal-episode-simulator-v36"
    (output / f"{stem}.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    with (output / f"{stem}-pairs.jsonl").open(
        "w",
        encoding="utf-8",
    ) as handle:
        for row in audits:
            handle.write(json.dumps(asdict(row), sort_keys=True) + "\n")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("development_root", type=Path)
    parser.add_argument("validation_root", type=Path)
    parser.add_argument("reserved_root", type=Path)
    parser.add_argument("development_validation_context_root", type=Path)
    parser.add_argument("reserved_context_root", type=Path)
    parser.add_argument("transition_path", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()

    report, audits = build_report(
        args.development_root,
        args.validation_root,
        args.reserved_root,
        args.development_validation_context_root,
        args.reserved_context_root,
        args.transition_path,
    )
    write_report(report, audits, args.output)
    print(json.dumps(report, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

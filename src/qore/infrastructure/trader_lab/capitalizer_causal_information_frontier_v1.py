"""Causal-information frontier diagnostic for Capitalizer.

The feasibility/anatomy audit proved that the existing nine-mode protection
toolbox has strong ex-post physical capacity, but most max-DD losses never reach
+0.50R.  Much of the oracle advantage instead comes from preserving right-tail
outcomes that Surface protects too early.

This module does not learn or promote a policy.  It asks whether the existing
strictly-causal V31 95-dimensional state contains transportable information
about that distinction.  For every held-out Surface first-intervention state it
finds one causal nearest-neighbour "twin" in each of the two external consumed
worlds, restricted to the same trigger family and same Surface mode.  Outcomes
are used only after matching to audit oracle-class and action-effect-sign
transport.
"""

from __future__ import annotations

import argparse
import json
import math
from collections import Counter, defaultdict
from collections.abc import Callable
from dataclasses import asdict, dataclass
from decimal import Decimal
from pathlib import Path
from typing import Any

from qore.infrastructure.trader_lab import (
    capitalizer_causal_trigger_state_veto_policy_v29 as v29,
)
from qore.infrastructure.trader_lab import (
    capitalizer_cognitive_r_milestone_protection_2r_v1 as milestone,
)
from qore.infrastructure.trader_lab import (
    capitalizer_continuation_value_model_v22 as v22,
)
from qore.infrastructure.trader_lab import (
    capitalizer_event_time_portfolio_trigger_state_v31 as v31,
)
from qore.infrastructure.trader_lab import (
    capitalizer_factor_journey_probe_ranker_v11 as v11,
)
from qore.infrastructure.trader_lab import (
    capitalizer_first_intervention_cross_trigger_optionality_v30 as v30,
)
from qore.infrastructure.trader_lab import (
    capitalizer_portfolio_drawdown_feasibility_episode_anatomy_v1 as anatomy,
)
from qore.infrastructure.trader_lab import (
    capitalizer_sequence_failure_memory_abstention_v13 as v13,
)

IDENTITY = "QORE_CAPITALIZER_CAUSAL_INFORMATION_FRONTIER_V1"
EXPECTED_FEATURE_DIMENSION = v31.EXPECTED_FEATURE_DIMENSION
PORTFOLIO_FEATURE_DIMENSION = v31.EVENT_PORTFOLIO_FEATURE_DIMENSION

SURFACE_OPTIMAL = "SURFACE_OPTIMAL"
INTERVENE_NOW = "INTERVENE_NOW"
PRESERVE_OPTIONALITY = "PRESERVE_OPTIONALITY"
MIXED_OPTIMUM = "MIXED_OPTIMUM"
ORACLE_CLASSES = (
    SURFACE_OPTIMAL,
    INTERVENE_NOW,
    PRESERVE_OPTIONALITY,
    MIXED_OPTIMUM,
)


@dataclass(frozen=True, slots=True)
class _Geometry:
    mean: tuple[float, ...]
    scale: tuple[float, ...]


@dataclass(frozen=True, slots=True)
class _StateSample:
    period: str
    symbol: str
    entry_at: str
    family: str
    surface_mode: str
    trigger_at: str
    current_dd_r: Decimal
    active_drawdown: bool
    entrant_in_max_dd_descent: bool
    vector: tuple[float, ...]
    surface_scaled_r: Decimal
    best_scaled_r: Decimal
    surface_regret_r: Decimal
    optimal_actions: tuple[str, ...]
    oracle_class: str
    action_deltas: tuple[tuple[str, Decimal], ...]


@dataclass(frozen=True, slots=True)
class TwinAudit:
    period: str
    symbol: str
    entry_at: str
    family: str
    surface_mode: str
    trigger_at: str
    current_dd_r: str
    active_drawdown: bool
    entrant_in_max_dd_descent: bool
    heldout_oracle_class: str
    heldout_surface_regret_r: str
    heldout_optimal_actions: tuple[str, ...]
    trainer_a_period: str
    trainer_b_period: str
    trainer_a_twin_symbol: str | None
    trainer_a_twin_entry_at: str | None
    trainer_b_twin_symbol: str | None
    trainer_b_twin_entry_at: str | None
    trainer_a_distance: str | None
    trainer_b_distance: str | None
    trainer_a_oracle_class: str | None
    trainer_b_oracle_class: str | None
    dual_world_class_agreement: bool
    agreed_class_matches_heldout: bool
    action_sign_comparisons: int
    dual_world_action_sign_agreements: int
    transported_action_sign_matches: int
    matching_used_outcomes: bool = False
    heldout_outcome_visible_to_matching: bool = False
    identity_features_used_in_matching: bool = False
    diagnostic_oracle_labels_use_future: bool = True
    policy_candidate: bool = False


def _sign(value: Decimal) -> int:
    if value > 0:
        return 1
    if value < 0:
        return -1
    return 0


def _quantile(values: tuple[float, ...], q: float) -> float | None:
    if not values:
        return None
    if not 0.0 <= q <= 1.0:
        raise ValueError("CIF quantile outside [0,1]")
    ordered = sorted(values)
    index = max(0, min(len(ordered) - 1, math.ceil(q * len(ordered)) - 1))
    return ordered[index]


def _geometry(rows: tuple[_StateSample, ...]) -> _Geometry:
    if not rows:
        raise ValueError("CIF geometry requires rows")
    dimension = len(rows[0].vector)
    if dimension != EXPECTED_FEATURE_DIMENSION:
        raise ValueError("CIF feature dimension drift")
    if any(len(row.vector) != dimension for row in rows):
        raise ValueError("CIF inconsistent vector dimensions")

    count = float(len(rows))
    means = tuple(
        sum(row.vector[index] for row in rows) / count
        for index in range(dimension)
    )
    scales: list[float] = []
    for index, mean in enumerate(means):
        variance = sum(
            (row.vector[index] - mean) ** 2 for row in rows
        ) / count
        scale = math.sqrt(variance)
        scales.append(1.0 if scale <= 1e-12 else scale)
    return _Geometry(mean=means, scale=tuple(scales))


def _distance(
    geometry: _Geometry,
    left: tuple[float, ...],
    right: tuple[float, ...],
) -> float:
    if len(left) != len(geometry.mean) or len(right) != len(geometry.mean):
        raise ValueError("CIF distance dimension mismatch")
    squared = sum(
        ((left[index] - right[index]) / geometry.scale[index]) ** 2
        for index in range(len(left))
    )
    return math.sqrt(squared / len(left))


def _nearest(
    heldout: _StateSample,
    candidates: tuple[_StateSample, ...],
    geometry: _Geometry,
) -> tuple[_StateSample, float]:
    if not candidates:
        raise ValueError("CIF nearest requires candidates")
    ranked = tuple(
        (
            _distance(geometry, heldout.vector, candidate.vector),
            candidate.entry_at,
            candidate.symbol,
            candidate,
        )
        for candidate in candidates
    )
    distance, _entry_at, _symbol, row = min(ranked)
    return row, distance


def _oracle_class(
    *,
    surface_mode: str,
    family: str,
    action_values: dict[str, Decimal],
) -> tuple[str, Decimal, tuple[str, ...]]:
    if surface_mode not in action_values:
        raise ValueError("CIF Surface mode missing from reachable actions")
    best = max(action_values.values())
    surface = action_values[surface_mode]
    optimal = tuple(
        action
        for action in v30._eligible_actions(family)
        if action_values[action] == best
    )
    regret = best - surface
    if regret <= 0:
        return SURFACE_OPTIMAL, Decimal("0"), optimal

    current_rank = v30.FAMILY_RANK[family]
    horizons: set[str] = set()
    for action in optimal:
        first_family = v30._mode_family(action)
        if first_family is None:
            horizons.add("OPTIONALITY")
            continue
        rank = v30.FAMILY_RANK[first_family]
        if rank == current_rank:
            horizons.add("NOW")
        elif rank > current_rank:
            horizons.add("OPTIONALITY")
        else:
            raise ValueError("CIF optimal action intervenes before decision")

    if horizons == {"NOW"}:
        label = INTERVENE_NOW
    elif horizons == {"OPTIONALITY"}:
        label = PRESERVE_OPTIONALITY
    else:
        label = MIXED_OPTIMUM
    return label, regret, optimal


def _max_dd_keys(
    ledger: tuple[milestone.SimulatedTrade, ...],
) -> set[tuple[str, str]]:
    rows = anatomy._canonical_rows(ledger)
    values = tuple(Decimal(row.realized_gross_r) for row in rows)
    episodes = anatomy._drawdown_episodes(values)
    if not episodes:
        return set()
    episode = max(
        episodes,
        key=lambda row: (Decimal(row.max_drawdown_r), -row.episode_id),
    )
    return {
        (rows[index].symbol, rows[index].entry_at)
        for index in range(episode.start_index, episode.trough_index + 1)
    }


def _sample(
    *,
    period: str,
    state: v31.ControlTriggerState,
    ledgers: dict[str, tuple[milestone.SimulatedTrade, ...]],
    max_dd_keys: set[tuple[str, str]],
) -> _StateSample:
    key = (state.symbol, state.entry_at)
    modes = v29._by_mode(ledgers)
    actions = v30._eligible_actions(state.family)
    v30._assert_common_path(
        key=key,
        trigger_at=state.trigger_at,
        actions=actions,
        modes=modes,
    )
    multiplier = Decimal(state.base_multiplier)
    action_values = {
        action: Decimal(modes[action][key].realized_gross_r) * multiplier
        for action in actions
    }
    label, regret, optimal = _oracle_class(
        surface_mode=state.surface_mode,
        family=state.family,
        action_values=action_values,
    )
    surface_r = action_values[state.surface_mode]
    current_dd = Decimal(
        str(state.vector[-PORTFOLIO_FEATURE_DIMENSION])
    )
    return _StateSample(
        period=period,
        symbol=state.symbol,
        entry_at=state.entry_at,
        family=state.family,
        surface_mode=state.surface_mode,
        trigger_at=state.trigger_at,
        current_dd_r=current_dd,
        active_drawdown=current_dd > 0,
        entrant_in_max_dd_descent=key in max_dd_keys,
        vector=state.vector,
        surface_scaled_r=surface_r,
        best_scaled_r=max(action_values.values()),
        surface_regret_r=regret,
        optimal_actions=optimal,
        oracle_class=label,
        action_deltas=tuple(
            (action, action_values[action] - surface_r)
            for action in actions
        ),
    )


def _prepare_samples(
    *,
    windows: dict[str, Any],
    contextual_model: dict[str, Any],
    native_states: dict[tuple[str, str, str, str], v29.TriggerState],
) -> dict[str, tuple[_StateSample, ...]]:
    controls, _rows, _maps = v22._control_decision_maps(
        windows,
        contextual_model,
    )
    result: dict[str, tuple[_StateSample, ...]] = {}

    for period, (ledgers, contexts) in windows.items():
        states, ledger = v31._control_event_replay(
            period=period,
            ledgers=ledgers,
            contexts=contexts,
            contextual_model=contextual_model,
            native_states=native_states,
        )
        if milestone._metrics(ledger) != controls[period]["metrics"]:
            raise ValueError(f"CIF Surface replay drift in {period}")
        max_keys = _max_dd_keys(ledger)
        samples = tuple(
            sorted(
                (
                    _sample(
                        period=period,
                        state=state,
                        ledgers=ledgers,
                        max_dd_keys=max_keys,
                    )
                    for state in states.values()
                ),
                key=lambda row: (milestone._aware(row.entry_at), row.symbol),
            )
        )
        result[period] = samples
    return result


def _cell(row: _StateSample) -> tuple[str, str]:
    return row.family, row.surface_mode


def _delta_map(row: _StateSample) -> dict[str, Decimal]:
    return dict(row.action_deltas)


def _twin_audit(
    *,
    heldout: _StateSample,
    trainer_a_period: str,
    trainer_b_period: str,
    by_cell: dict[
        str,
        dict[tuple[str, str], tuple[_StateSample, ...]],
    ],
) -> TwinAudit:
    cell = _cell(heldout)
    candidates_a = by_cell[trainer_a_period].get(cell, ())
    candidates_b = by_cell[trainer_b_period].get(cell, ())

    if not candidates_a or not candidates_b:
        return TwinAudit(
            period=heldout.period,
            symbol=heldout.symbol,
            entry_at=heldout.entry_at,
            family=heldout.family,
            surface_mode=heldout.surface_mode,
            trigger_at=heldout.trigger_at,
            current_dd_r=str(heldout.current_dd_r),
            active_drawdown=heldout.active_drawdown,
            entrant_in_max_dd_descent=heldout.entrant_in_max_dd_descent,
            heldout_oracle_class=heldout.oracle_class,
            heldout_surface_regret_r=str(heldout.surface_regret_r),
            heldout_optimal_actions=heldout.optimal_actions,
            trainer_a_period=trainer_a_period,
            trainer_b_period=trainer_b_period,
            trainer_a_twin_symbol=None,
            trainer_a_twin_entry_at=None,
            trainer_b_twin_symbol=None,
            trainer_b_twin_entry_at=None,
            trainer_a_distance=None,
            trainer_b_distance=None,
            trainer_a_oracle_class=None,
            trainer_b_oracle_class=None,
            dual_world_class_agreement=False,
            agreed_class_matches_heldout=False,
            action_sign_comparisons=0,
            dual_world_action_sign_agreements=0,
            transported_action_sign_matches=0,
        )

    geometry_a = _geometry(candidates_a)
    geometry_b = _geometry(candidates_b)
    twin_a, distance_a = _nearest(heldout, candidates_a, geometry_a)
    twin_b, distance_b = _nearest(heldout, candidates_b, geometry_b)

    class_agree = twin_a.oracle_class == twin_b.oracle_class
    class_correct = class_agree and twin_a.oracle_class == heldout.oracle_class

    heldout_deltas = _delta_map(heldout)
    a_deltas = _delta_map(twin_a)
    b_deltas = _delta_map(twin_b)
    actions = tuple(
        action
        for action in v30._eligible_actions(heldout.family)
        if action != heldout.surface_mode
    )
    comparisons = 0
    external_agreements = 0
    transported_matches = 0
    for action in actions:
        if action not in a_deltas or action not in b_deltas:
            continue
        comparisons += 1
        sign_a = _sign(a_deltas[action])
        sign_b = _sign(b_deltas[action])
        if sign_a != sign_b:
            continue
        external_agreements += 1
        if sign_a == _sign(heldout_deltas[action]):
            transported_matches += 1

    return TwinAudit(
        period=heldout.period,
        symbol=heldout.symbol,
        entry_at=heldout.entry_at,
        family=heldout.family,
        surface_mode=heldout.surface_mode,
        trigger_at=heldout.trigger_at,
        current_dd_r=str(heldout.current_dd_r),
        active_drawdown=heldout.active_drawdown,
        entrant_in_max_dd_descent=heldout.entrant_in_max_dd_descent,
        heldout_oracle_class=heldout.oracle_class,
        heldout_surface_regret_r=str(heldout.surface_regret_r),
        heldout_optimal_actions=heldout.optimal_actions,
        trainer_a_period=trainer_a_period,
        trainer_b_period=trainer_b_period,
        trainer_a_twin_symbol=twin_a.symbol,
        trainer_a_twin_entry_at=twin_a.entry_at,
        trainer_b_twin_symbol=twin_b.symbol,
        trainer_b_twin_entry_at=twin_b.entry_at,
        trainer_a_distance=str(distance_a),
        trainer_b_distance=str(distance_b),
        trainer_a_oracle_class=twin_a.oracle_class,
        trainer_b_oracle_class=twin_b.oracle_class,
        dual_world_class_agreement=class_agree,
        agreed_class_matches_heldout=class_correct,
        action_sign_comparisons=comparisons,
        dual_world_action_sign_agreements=external_agreements,
        transported_action_sign_matches=transported_matches,
    )


def _summary(
    audits: tuple[TwinAudit, ...],
    *,
    predicate: Callable[[TwinAudit], bool],
) -> dict[str, Any]:
    rows = tuple(row for row in audits if predicate(row))
    resolved = tuple(
        row
        for row in rows
        if row.trainer_a_oracle_class is not None
        and row.trainer_b_oracle_class is not None
    )
    agreed = tuple(row for row in resolved if row.dual_world_class_agreement)
    correct = tuple(row for row in agreed if row.agreed_class_matches_heldout)
    regret = tuple(
        row
        for row in rows
        if Decimal(row.heldout_surface_regret_r) > 0
    )
    distances = tuple(
        float(value)
        for row in resolved
        for value in (row.trainer_a_distance, row.trainer_b_distance)
        if value is not None
    )
    sign_comparisons = sum(row.action_sign_comparisons for row in resolved)
    sign_agreements = sum(
        row.dual_world_action_sign_agreements for row in resolved
    )
    sign_matches = sum(
        row.transported_action_sign_matches for row in resolved
    )
    regret_by_class: dict[str, Decimal] = defaultdict(lambda: Decimal("0"))
    for row in regret:
        regret_by_class[row.heldout_oracle_class] += Decimal(
            row.heldout_surface_regret_r
        )

    return {
        "states": len(rows),
        "resolved_twin_states": len(resolved),
        "oracle_class_counts": dict(
            sorted(Counter(row.heldout_oracle_class for row in rows).items())
        ),
        "surface_regret_states": len(regret),
        "surface_regret_r": str(
            sum(
                (
                    Decimal(row.heldout_surface_regret_r)
                    for row in regret
                ),
                Decimal("0"),
            )
        ),
        "surface_regret_r_by_class": {
            key: str(value)
            for key, value in sorted(regret_by_class.items())
        },
        "dual_world_class_agreements": len(agreed),
        "dual_world_class_agreement_rate": (
            None if not resolved else str(Decimal(len(agreed)) / Decimal(len(resolved)))
        ),
        "agreed_class_matches_heldout": len(correct),
        "agreed_class_transport_precision": (
            None if not agreed else str(Decimal(len(correct)) / Decimal(len(agreed)))
        ),
        "overall_class_transport_rate": (
            None if not resolved else str(Decimal(len(correct)) / Decimal(len(resolved)))
        ),
        "action_sign_comparisons": sign_comparisons,
        "dual_world_action_sign_agreements": sign_agreements,
        "dual_world_action_sign_agreement_rate": (
            None
            if sign_comparisons == 0
            else str(Decimal(sign_agreements) / Decimal(sign_comparisons))
        ),
        "transported_action_sign_matches": sign_matches,
        "agreed_action_sign_transport_precision": (
            None
            if sign_agreements == 0
            else str(Decimal(sign_matches) / Decimal(sign_agreements))
        ),
        "nearest_twin_distance_p50": _quantile(distances, 0.50),
        "nearest_twin_distance_p90": _quantile(distances, 0.90),
    }


def build_report(
    development_root: Path,
    validation_root: Path,
    reserved_root: Path,
    development_validation_context_root: Path,
    reserved_context_root: Path,
    trigger_state_root: Path,
) -> tuple[dict[str, Any], tuple[TwinAudit, ...]]:
    windows, contextual_model = v13._load_windows(
        development_root,
        validation_root,
        reserved_root,
        development_validation_context_root,
        reserved_context_root,
    )
    native_states = v29._load_trigger_states(trigger_state_root)

    simultaneous: dict[
        tuple[str, str, str], tuple[milestone.SimulatedTrade, ...]
    ] = {}
    for period, (ledgers, _contexts) in windows.items():
        simultaneous.update(
            v11._simultaneous_map(period=period, ledgers=ledgers)
        )

    previous = dict(v11._SIMULTANEOUS)
    v11._SIMULTANEOUS.clear()
    v11._SIMULTANEOUS.update(simultaneous)
    try:
        samples = _prepare_samples(
            windows=windows,
            contextual_model=contextual_model,
            native_states=native_states,
        )
    finally:
        v11._SIMULTANEOUS.clear()
        v11._SIMULTANEOUS.update(previous)

    by_cell: dict[
        str,
        dict[tuple[str, str], tuple[_StateSample, ...]],
    ] = {}
    for period, rows in samples.items():
        grouped: dict[tuple[str, str], list[_StateSample]] = defaultdict(list)
        for row in rows:
            grouped[_cell(row)].append(row)
        by_cell[period] = {
            cell: tuple(values)
            for cell, values in grouped.items()
        }

    audits: list[TwinAudit] = []
    period_order = tuple(samples)
    for heldout in period_order:
        trainers = tuple(period for period in period_order if period != heldout)
        if len(trainers) != 2:
            raise ValueError("CIF requires exactly two external periods")
        trainer_a, trainer_b = trainers
        for row in samples[heldout]:
            audits.append(
                _twin_audit(
                    heldout=row,
                    trainer_a_period=trainer_a,
                    trainer_b_period=trainer_b,
                    by_cell=by_cell,
                )
            )

    frozen = tuple(audits)
    period_results: list[dict[str, Any]] = []
    for period in period_order:
        period_audits = tuple(row for row in frozen if row.period == period)
        period_results.append(
            {
                "period": period,
                "all_surface_trigger_states": _summary(
                    period_audits,
                    predicate=lambda _row: True,
                ),
                "active_drawdown_states": _summary(
                    period_audits,
                    predicate=lambda row: row.active_drawdown,
                ),
                "max_dd_descent_entrants": _summary(
                    period_audits,
                    predicate=lambda row: row.entrant_in_max_dd_descent,
                ),
                "active_dd_max_descent_states": _summary(
                    period_audits,
                    predicate=lambda row: (
                        row.active_drawdown
                        and row.entrant_in_max_dd_descent
                    ),
                ),
            }
        )

    return (
        {
            "identity": IDENTITY,
            "evaluation": "CROSS_ERA_CAUSAL_TWIN_INFORMATION_FRONTIER",
            "source_state_identity": v31.IDENTITY,
            "causal_state_dimension": EXPECTED_FEATURE_DIMENSION,
            "matching_cell": "SAME_TRIGGER_FAMILY_AND_SAME_SURFACE_MODE",
            "matching_metric": "TRAINER_LOCAL_STANDARDIZED_EUCLIDEAN_RMS",
            "trainer_world_scaling_independent": True,
            "outcomes_used_in_matching": False,
            "heldout_outcome_visible_to_matching": False,
            "identity_features_used_in_matching": False,
            "oracle_classes": list(ORACLE_CLASSES),
            "oracle_labels_use_future_information": True,
            "oracle_labels_diagnostic_only": True,
            "action_effect_sign_is_vs_same_surface_mode": True,
            "results": period_results,
            "policy_economics_run": False,
            "automatic_policy_promotion": False,
            "admission_changed": False,
            "sizing_changed": False,
            "trader_certified": False,
            "live_authorized": False,
            "real_capital_authorized": False,
            "next_phase": "INTERPRET_CAUSAL_INFORMATION_FRONTIER_BEFORE_CONTROLLER_ARCHITECTURE",
        },
        frozen,
    )


def write_report(
    report: dict[str, Any],
    audits: tuple[TwinAudit, ...],
    output: Path,
) -> None:
    output.mkdir(parents=True, exist_ok=True)
    stem = "capitalizer-causal-information-frontier-v1"
    (output / f"{stem}.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    with (output / f"{stem}-twins.jsonl").open(
        "w", encoding="utf-8"
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
    parser.add_argument("trigger_state_root", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()

    report, audits = build_report(
        args.development_root,
        args.validation_root,
        args.reserved_root,
        args.development_validation_context_root,
        args.reserved_context_root,
        args.trigger_state_root,
    )
    write_report(report, audits, args.output)
    print(json.dumps(report, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

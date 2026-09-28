"""Structural drawdown first-passage guardian for Capitalizer V35.

V34 established that max drawdown is not an ordinary state -> action-value
problem. V35 implements the predeclared next object: while a realized portfolio
drawdown episode is active, estimate whether an already-existing protection
action reduces (a) the hazard of reaching a deeper trough before recovering the
pre-episode peak and (b) the additional trough severity, while preserving
trade value.

All inference inputs are causal and already available in the V31 95-dimensional
trigger state. Future first-passage outcomes are training labels only. Surface
is the fail-closed default.
"""

from __future__ import annotations

import argparse
import json
import math
from collections import Counter
from dataclasses import asdict, dataclass
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
    capitalizer_causal_trigger_state_veto_policy_v29 as v29,
)
from qore.infrastructure.trader_lab import (
    capitalizer_cognitive_invariant_tail_risk_guardian_v33 as v33,
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
    capitalizer_regularized_causal_state_space_v25 as v25,
)
from qore.infrastructure.trader_lab import (
    capitalizer_sequence_failure_memory_abstention_v13 as v13,
)

IDENTITY = "QORE_CAPITALIZER_STRUCTURAL_DRAWDOWN_HAZARD_TRANSITION_V35"
POLICY = "SURFACE_DEFAULT_DUAL_WORLD_EPISODE_TRANSITION_GUARDIAN"
SOURCE_TRIGGER_STATE_RUN_ID = v33.SOURCE_TRIGGER_STATE_RUN_ID
EXPECTED_FEATURE_DIMENSION = v31.EXPECTED_FEATURE_DIMENSION
L2_PRIOR_STRENGTH = v33.L2_PRIOR_STRENGTH
CHRONOLOGICAL_FOLDS = 5
MIN_CHRONOLOGICAL_CALIBRATION_EXAMPLES = CHRONOLOGICAL_FOLDS * 2
UPPER_RESIDUAL_QUANTILE = 0.80
LOWER_RESIDUAL_QUANTILE = 0.20
ACTION_ORDER = tuple(mode.value for mode in milestone.ProtectionMode)


@dataclass(frozen=True, slots=True)
class CalibratedHead:
    model: v25.RidgeModel
    residual_quantile: float
    chronological_residual_count: int


@dataclass(frozen=True, slots=True)
class HazardActionHeads:
    deepening_hazard: CalibratedHead
    additional_trough: CalibratedHead
    total_delta: CalibratedHead


FamilyModels = dict[str, dict[str, dict[str, HazardActionHeads]]]


@dataclass(frozen=True, slots=True)
class FirstPassageTarget:
    deepens_before_recovery: bool
    additional_trough_r: str
    recovered_peak: bool
    terminal_event: str


@dataclass(frozen=True, slots=True)
class V35Decision:
    period: str
    policy: str
    symbol: str
    session: str
    operating_date: str
    entry_at: str
    causal_surface_mode: str
    chosen_mode: str
    surface_first_family: str | None
    surface_first_protection_at: str | None
    decision_made: bool
    active_drawdown_episode: bool
    switched: bool
    metacognitive_state: str
    pretrigger_realized_dd_r: str
    base_multiplier: str
    completed_m1_bars: int | None
    trigger_delay_minutes: str | None
    trainer_a_period: str
    trainer_b_period: str
    robust_worst_world_severity_ucb: str | None
    robust_worst_world_hazard_ucb: str | None
    trainer_a_surface_hazard_ucb: str | None
    trainer_b_surface_hazard_ucb: str | None
    trainer_a_action_hazard_ucb: str | None
    trainer_b_action_hazard_ucb: str | None
    trainer_a_surface_severity_ucb: str | None
    trainer_b_surface_severity_ucb: str | None
    trainer_a_action_severity_ucb: str | None
    trainer_b_action_severity_ucb: str | None
    trainer_a_total_delta_lcb: str | None
    trainer_b_total_delta_lcb: str | None
    eligible_action_count: int
    current_outcome_visible: bool = False
    heldout_counterfactual_visible: bool = False
    future_after_trigger_visible: bool = False
    activation_bar_ohlc_visible: bool = False
    era_identity_feature_used: bool = False
    symbol_session_side_time_identity_features_used: bool = False


def _aware(value: str) -> datetime:
    return milestone._aware(value)


def _canonical_rows(
    rows: tuple[milestone.SimulatedTrade, ...],
) -> tuple[milestone.SimulatedTrade, ...]:
    ordered = tuple(
        sorted(rows, key=lambda row: (_aware(row.entry_at), row.symbol))
    )
    keys = tuple((row.symbol, row.entry_at) for row in ordered)
    if len(set(keys)) != len(keys):
        raise ValueError("V35 requires unique entrant identities")
    return ordered


def _closed_equity_state(
    rows: tuple[milestone.SimulatedTrade, ...],
    *,
    observed_at: datetime,
) -> tuple[Decimal, Decimal, Decimal]:
    closed = tuple(
        sorted(
            (row for row in rows if _aware(row.exit_at) < observed_at),
            key=lambda row: (
                _aware(row.exit_at),
                _aware(row.entry_at),
                row.symbol,
            ),
        )
    )
    equity = Decimal("0")
    peak = Decimal("0")
    for row in closed:
        equity += Decimal(row.realized_gross_r)
        peak = max(peak, equity)
    return equity, peak, peak - equity


def _first_passage_target(
    control_ledger: tuple[milestone.SimulatedTrade, ...],
    *,
    key: tuple[str, str],
    trigger_at: str,
    counterfactual: milestone.SimulatedTrade,
) -> FirstPassageTarget:
    rows = _canonical_rows(control_ledger)
    control_map = {(row.symbol, row.entry_at): row for row in rows}
    if key not in control_map:
        raise ValueError("V35 target key absent from Surface control ledger")

    observed_at = _aware(trigger_at)
    equity, peak, starting_dd = _closed_equity_state(
        rows,
        observed_at=observed_at,
    )
    if starting_dd <= 0:
        raise ValueError("V35 first-passage target requires active drawdown")

    future_rows = tuple(
        sorted(
            (
                counterfactual if (row.symbol, row.entry_at) == key else row
                for row in rows
                if (
                    (row.symbol, row.entry_at) == key
                    or _aware(row.exit_at) >= observed_at
                )
            ),
            key=lambda row: (
                _aware(row.exit_at),
                _aware(row.entry_at),
                row.symbol,
            ),
        )
    )
    seen_current = sum(
        (row.symbol, row.entry_at) == key for row in future_rows
    )
    if seen_current != 1:
        raise ValueError("V35 counterfactual identity replacement drift")

    deepened = False
    recovered = False
    first_event: str | None = None
    max_dd = starting_dd

    for row in future_rows:
        equity += Decimal(row.realized_gross_r)
        current_dd = max(Decimal("0"), peak - equity)
        max_dd = max(max_dd, current_dd)
        if current_dd > starting_dd:
            deepened = True
            if first_event is None:
                first_event = "DEEPEN_TROUGH"
        if equity >= peak:
            recovered = True
            if first_event is None:
                first_event = "RECOVER_PEAK"
            break

    terminal = (
        first_event
        if first_event is not None
        else "PERIOD_EXHAUSTED_NO_DEEPEN_OR_RECOVERY"
    )

    return FirstPassageTarget(
        deepens_before_recovery=deepened,
        additional_trough_r=str(max_dd - starting_dd),
        recovered_peak=recovered,
        terminal_event=terminal,
    )


def _training_table(
    *,
    family: str,
    states: dict[tuple[str, str, str], v31.ControlTriggerState],
    ledgers: dict[str, tuple[milestone.SimulatedTrade, ...]],
    control_ledger: tuple[milestone.SimulatedTrade, ...],
) -> tuple[
    tuple[tuple[float, ...], ...],
    tuple[tuple[str, str], ...],
    dict[tuple[str, str], tuple[float, ...]],
]:
    modes = v29._by_mode(ledgers)
    control_map = {
        (row.symbol, row.entry_at): row
        for row in _canonical_rows(control_ledger)
    }
    eligible = v30._eligible_actions(family)
    selected = tuple(
        sorted(
            (
                (symbol, entry_at, state)
                for (symbol, entry_at, state_family), state in states.items()
                if state_family == family
                and state.vector[-v31.EVENT_PORTFOLIO_FEATURE_DIMENSION] > 0.0
            ),
            key=lambda item: (_aware(item[1]), item[0]),
        )
    )

    features: list[tuple[float, ...]] = []
    keys: list[tuple[str, str]] = []
    targets: dict[tuple[str, str], list[float]] = {
        (action, head): []
        for action in eligible
        for head in ("HAZARD", "SEVERITY", "TOTAL")
    }

    for symbol, entry_at, state in selected:
        key = (symbol, entry_at)
        v30._assert_common_path(
            key=key,
            trigger_at=state.trigger_at,
            actions=eligible,
            modes=modes,
        )
        if key not in control_map:
            raise ValueError("V35 control ledger identity drift")

        surface = modes[state.surface_mode][key]
        surface_r = Decimal(surface.realized_gross_r)
        multiplier = Decimal(state.base_multiplier)
        expected_scaled = surface_r * multiplier
        control_scaled = Decimal(control_map[key].realized_gross_r)
        if control_scaled != expected_scaled:
            raise ValueError("V35 Surface scaled R mismatch")

        _equity, _peak, exact_dd = _closed_equity_state(
            control_ledger,
            observed_at=_aware(state.trigger_at),
        )
        vector_dd = Decimal(
            str(
                state.vector[
                    -v31.EVENT_PORTFOLIO_FEATURE_DIMENSION
                ]
            )
        )
        if abs(exact_dd - vector_dd) > Decimal("1e-9"):
            raise ValueError("V35 trigger DD feature drift")

        features.append(state.vector)
        keys.append(key)

        for action in eligible:
            action_row = modes[action][key]
            scaled = v31._scaled_trade(
                action_row,
                multiplier=multiplier,
            )
            passage = _first_passage_target(
                control_ledger,
                key=key,
                trigger_at=state.trigger_at,
                counterfactual=scaled,
            )
            action_r = Decimal(action_row.realized_gross_r)
            total_delta = (action_r - surface_r) * multiplier

            targets[(action, "HAZARD")].append(
                float(int(passage.deepens_before_recovery))
            )
            targets[(action, "SEVERITY")].append(
                float(Decimal(passage.additional_trough_r))
            )
            targets[(action, "TOTAL")].append(float(total_delta))

    return (
        tuple(features),
        tuple(keys),
        {target: tuple(values) for target, values in targets.items()},
    )


def _chronological_residuals_many(
    *,
    period: str,
    family: str,
    features: tuple[tuple[float, ...], ...],
    keys: tuple[tuple[str, str], ...],
    targets: dict[tuple[str, str], tuple[float, ...]],
) -> dict[tuple[str, str], tuple[float, ...]]:
    count = len(features)
    if count < MIN_CHRONOLOGICAL_CALIBRATION_EXAMPLES:
        raise ValueError("V35 insufficient chronological calibration support")

    block_size = math.ceil(count / CHRONOLOGICAL_FOLDS)
    residuals: dict[tuple[str, str], list[float]] = {
        target_id: [] for target_id in targets
    }

    for fold in range(1, CHRONOLOGICAL_FOLDS):
        test_start = fold * block_size
        if test_start >= count:
            break
        test_end = min(count, (fold + 1) * block_size)
        train_targets = {
            target_id: values[:test_start]
            for target_id, values in targets.items()
        }
        fold_models = v33._fit_many(
            label=f"{period}:{family}:V35:OOF{fold}",
            features=features[:test_start],
            keys=keys[:test_start],
            targets=train_targets,
        )
        for target_id, model in fold_models.items():
            values = targets[target_id]
            for index in range(test_start, test_end):
                prediction = v25._predict(model, features[index])
                residuals[target_id].append(values[index] - prediction)

    result = {
        target_id: tuple(values)
        for target_id, values in residuals.items()
    }
    if any(not values for values in result.values()):
        raise ValueError("V35 produced empty chronological residual set")
    return result


def _fit_family_heads(
    *,
    period: str,
    family: str,
    features: tuple[tuple[float, ...], ...],
    keys: tuple[tuple[str, str], ...],
    targets: dict[tuple[str, str], tuple[float, ...]],
) -> dict[str, HazardActionHeads]:
    models = v33._fit_many(
        label=f"{period}:{family}:V35:FULL",
        features=features,
        keys=keys,
        targets=targets,
    )
    residuals = _chronological_residuals_many(
        period=period,
        family=family,
        features=features,
        keys=keys,
        targets=targets,
    )

    result: dict[str, HazardActionHeads] = {}
    for action in v30._eligible_actions(family):
        hazard_id = (action, "HAZARD")
        severity_id = (action, "SEVERITY")
        total_id = (action, "TOTAL")
        result[action] = HazardActionHeads(
            deepening_hazard=CalibratedHead(
                model=models[hazard_id],
                residual_quantile=v33._quantile(
                    residuals[hazard_id],
                    UPPER_RESIDUAL_QUANTILE,
                ),
                chronological_residual_count=len(residuals[hazard_id]),
            ),
            additional_trough=CalibratedHead(
                model=models[severity_id],
                residual_quantile=v33._quantile(
                    residuals[severity_id],
                    UPPER_RESIDUAL_QUANTILE,
                ),
                chronological_residual_count=len(residuals[severity_id]),
            ),
            total_delta=CalibratedHead(
                model=models[total_id],
                residual_quantile=v33._quantile(
                    residuals[total_id],
                    LOWER_RESIDUAL_QUANTILE,
                ),
                chronological_residual_count=len(residuals[total_id]),
            ),
        )
    return result


def _fit_models(
    *,
    windows: dict[str, Any],
    control_states: dict[
        str, dict[tuple[str, str, str], v31.ControlTriggerState]
    ],
    control_ledgers: dict[str, tuple[milestone.SimulatedTrade, ...]],
) -> tuple[FamilyModels, dict[str, Any]]:
    models: FamilyModels = {}
    diagnostics: dict[str, Any] = {}

    for period, (ledgers, _contexts) in windows.items():
        period_models: dict[str, dict[str, HazardActionHeads]] = {}
        period_diagnostics: dict[str, Any] = {}
        for family in v30.FAMILY_ORDER:
            features, keys, targets = _training_table(
                family=family,
                states=control_states[period],
                ledgers=ledgers,
                control_ledger=control_ledgers[period],
            )
            if len(features) < MIN_CHRONOLOGICAL_CALIBRATION_EXAMPLES:
                period_models[family] = {}
                period_diagnostics[family] = {
                    "available": False,
                    "active_drawdown_training_states": len(features),
                    "minimum_required": (
                        MIN_CHRONOLOGICAL_CALIBRATION_EXAMPLES
                    ),
                    "reason": (
                        "INSUFFICIENT_ACTIVE_DRAWDOWN_CHRONOLOGICAL_SUPPORT"
                    ),
                }
                continue

            heads = _fit_family_heads(
                period=period,
                family=family,
                features=features,
                keys=keys,
                targets=targets,
            )
            period_models[family] = heads
            period_diagnostics[family] = {
                "available": True,
                "active_drawdown_training_states": len(features),
                "feature_dimension": len(features[0]),
                "actions": {
                    action: {
                        "hazard_target_mean": str(
                            action_heads.deepening_hazard.model.weighted_target_mean
                        ),
                        "hazard_residual_q80": str(
                            action_heads.deepening_hazard.residual_quantile
                        ),
                        "severity_target_mean": str(
                            action_heads.additional_trough.model.weighted_target_mean
                        ),
                        "severity_residual_q80": str(
                            action_heads.additional_trough.residual_quantile
                        ),
                        "total_target_mean": str(
                            action_heads.total_delta.model.weighted_target_mean
                        ),
                        "total_residual_q20": str(
                            action_heads.total_delta.residual_quantile
                        ),
                        "oof_residual_count": (
                            action_heads.deepening_hazard.chronological_residual_count
                        ),
                    }
                    for action, action_heads in heads.items()
                },
            }

        models[period] = period_models
        diagnostics[period] = period_diagnostics

    return models, diagnostics


def _upper(head: CalibratedHead, features: tuple[float, ...]) -> float:
    return v25._predict(head.model, features) + head.residual_quantile


def _lower(head: CalibratedHead, features: tuple[float, ...]) -> float:
    return v25._predict(head.model, features) + head.residual_quantile


def _choose_action(
    *,
    features: tuple[float, ...],
    surface_mode: str,
    actions: tuple[str, ...],
    model_a: dict[str, HazardActionHeads],
    model_b: dict[str, HazardActionHeads],
) -> tuple[
    str | None,
    tuple[float, ...] | None,
    str,
]:
    if surface_mode not in model_a or surface_mode not in model_b:
        return None, None, "UNRESOLVED"

    surface_a = model_a[surface_mode]
    surface_b = model_b[surface_mode]
    surface_hazard_a = _upper(surface_a.deepening_hazard, features)
    surface_hazard_b = _upper(surface_b.deepening_hazard, features)
    surface_severity_a = _upper(surface_a.additional_trough, features)
    surface_severity_b = _upper(surface_b.additional_trough, features)

    best_action: str | None = None
    best_values: tuple[float, ...] | None = None
    best_rank: tuple[float, float, int] | None = None
    saw_testable_alternative = False
    saw_conflict = False

    for action in ACTION_ORDER:
        if action not in actions or action == surface_mode:
            continue
        if action not in model_a or action not in model_b:
            continue
        saw_testable_alternative = True
        heads_a = model_a[action]
        heads_b = model_b[action]
        hazard_a = _upper(heads_a.deepening_hazard, features)
        hazard_b = _upper(heads_b.deepening_hazard, features)
        severity_a = _upper(heads_a.additional_trough, features)
        severity_b = _upper(heads_b.additional_trough, features)
        total_a = _lower(heads_a.total_delta, features)
        total_b = _lower(heads_b.total_delta, features)

        if not (
            hazard_a < surface_hazard_a
            and hazard_b < surface_hazard_b
            and severity_a < surface_severity_a
            and severity_b < surface_severity_b
            and total_a >= 0.0
            and total_b >= 0.0
        ):
            saw_conflict = True
            continue

        worst_severity = max(severity_a, severity_b)
        worst_hazard = max(hazard_a, hazard_b)
        rank = (
            worst_severity,
            worst_hazard,
            ACTION_ORDER.index(action),
        )
        if best_rank is None or rank < best_rank:
            best_rank = rank
            best_action = action
            best_values = (
                surface_hazard_a,
                surface_hazard_b,
                hazard_a,
                hazard_b,
                surface_severity_a,
                surface_severity_b,
                severity_a,
                severity_b,
                total_a,
                total_b,
                worst_severity,
                worst_hazard,
            )

    if best_action is not None:
        state = "WELL_SUPPORTED"
    elif saw_conflict:
        state = "CONFLICTED"
    elif saw_testable_alternative:
        state = "UNRESOLVED"
    else:
        state = "UNRESOLVED"
    return best_action, best_values, state


def _simulate_period(
    *,
    period: str,
    ledgers: dict[str, tuple[milestone.SimulatedTrade, ...]],
    contexts: dict[tuple[str, str], Any],
    contextual_model: dict[str, Any],
    trainer_a: str,
    trainer_b: str,
    model_a: dict[str, dict[str, HazardActionHeads]],
    model_b: dict[str, dict[str, HazardActionHeads]],
    native_states: dict[tuple[str, str, str, str], v29.TriggerState],
) -> tuple[dict[str, Any], tuple[V35Decision, ...]]:
    modes = v29._by_mode(ledgers)
    ordered = _canonical_rows(
        ledgers[milestone.ProtectionMode.ORIGINAL.value]
    )
    pointer = 0
    projections: dict[tuple[str, str], milestone.SimulatedTrade] = {}
    records: dict[tuple[str, str], memory.MemoryRecord] = {}
    pretrades: dict[tuple[str, str], v10.Pretrade] = {}
    pending: dict[tuple[str, str], tuple[Any, str]] = {}
    audit_data: dict[tuple[str, str], dict[str, Any]] = {}

    while pointer < len(ordered) or pending:
        now = v31._next_event_time(
            ordered=ordered,
            pointer=pointer,
            pending=pending,
        )
        if now is None:
            break

        snapshot_projections = v31._snapshot_rows(projections)
        snapshot_records = v31._snapshot_records(records)
        trigger_keys = tuple(
            sorted(
                (
                    key
                    for key, (trigger_at, _family) in pending.items()
                    if trigger_at == now
                ),
                key=lambda key: (key[1], key[0]),
            )
        )

        trigger_updates: dict[
            tuple[str, str],
            tuple[
                str,
                tuple[float, ...] | None,
                str,
                bool,
                float,
                int,
            ],
        ] = {}

        for key in trigger_keys:
            trigger_at, family = pending[key]
            pretrade = pretrades[key]
            trade = modes[milestone.ProtectionMode.ORIGINAL.value][key]
            native = native_states.get(
                (period, trade.symbol, trade.entry_at, family)
            )
            if native is None:
                raise ValueError("V35 missing held-out native trigger state")
            if _aware(native.trigger_at) != trigger_at:
                raise ValueError("V35 held-out trigger timestamp drift")

            portfolio = v31._portfolio_vector(
                current_trade=trade,
                observed_at=trigger_at,
                projections=snapshot_projections,
            )
            pretrigger_dd = portfolio[0]
            active_drawdown = pretrigger_dd > 0.0
            features = v31._full_trigger_vector(
                pretrade=pretrade,
                trade=trade,
                trigger_at=native.trigger_at,
                native_state=native,
                portfolio=portfolio,
            )
            actions = v30._eligible_actions(family)
            v30._assert_common_path(
                key=key,
                trigger_at=native.trigger_at,
                actions=actions,
                modes=modes,
            )

            if active_drawdown:
                action, values, epistemic = _choose_action(
                    features=features,
                    surface_mode=pretrade.mode,
                    actions=actions,
                    model_a=model_a[family],
                    model_b=model_b[family],
                )
                chosen_mode = pretrade.mode if action is None else action
            else:
                chosen_mode = pretrade.mode
                values = None
                epistemic = "OUTSIDE_ACTIVE_DRAWDOWN"

            trigger_updates[key] = (
                chosen_mode,
                values,
                epistemic,
                active_drawdown,
                pretrigger_dd,
                native.completed_m1_bars,
            )

        entry_rows: list[milestone.SimulatedTrade] = []
        while pointer < len(ordered) and _aware(ordered[pointer].entry_at) == now:
            entry_rows.append(ordered[pointer])
            pointer += 1

        if entry_rows:
            (
                new_pretrades,
                new_projections,
                new_records,
                new_triggers,
            ) = v31._entry_batch(
                period=period,
                rows=tuple(entry_rows),
                modes=modes,
                contexts=contexts,
                contextual_model=contextual_model,
                snapshot_projections=snapshot_projections,
                snapshot_records=snapshot_records,
            )
        else:
            new_pretrades = {}
            new_projections = {}
            new_records = {}
            new_triggers = {}

        for key in trigger_keys:
            trigger_at, family = pending.pop(key)
            (
                chosen_mode,
                values,
                epistemic,
                active_drawdown,
                pretrigger_dd,
                completed,
            ) = trigger_updates[key]
            pretrade = pretrades[key]
            selected = modes[chosen_mode][key]
            projections[key] = v31._scaled_trade(
                selected,
                multiplier=pretrade.base_multiplier,
            )
            records[key] = v31._record(
                pretrade=pretrade,
                selected=selected,
            )
            row = audit_data[key]
            row.update(
                decision_made=True,
                active_drawdown_episode=active_drawdown,
                chosen_mode=chosen_mode,
                completed_m1_bars=completed,
                trigger_delay_minutes=str(
                    (trigger_at - _aware(key[1])).total_seconds() / 60.0
                ),
                pretrigger_realized_dd_r=str(pretrigger_dd),
                values=values,
                metacognitive_state=epistemic,
                eligible_action_count=(
                    len(v30._eligible_actions(family))
                    if active_drawdown
                    else 0
                ),
            )

        for key, pretrade in new_pretrades.items():
            trade = modes[milestone.ProtectionMode.ORIGINAL.value][key]
            selected = modes[pretrade.mode][key]
            entry_family = v30._mode_family(pretrade.mode)
            audit_data[key] = {
                "causal_surface_mode": pretrade.mode,
                "chosen_mode": pretrade.mode,
                "surface_first_family": entry_family,
                "surface_first_protection_at": selected.first_protection_at,
                "base_multiplier": str(pretrade.base_multiplier),
                "decision_made": False,
                "active_drawdown_episode": False,
                "completed_m1_bars": None,
                "trigger_delay_minutes": None,
                "pretrigger_realized_dd_r": "0",
                "values": None,
                "metacognitive_state": "UNRESOLVED",
                "eligible_action_count": 0,
            }

        pretrades.update(new_pretrades)
        projections.update(new_projections)
        records.update(new_records)
        pending.update(new_triggers)

    ledger = v31._snapshot_rows(projections)
    if len(ledger) != len(ordered):
        raise ValueError("V35 held-out replay lost entrants")

    audits: list[V35Decision] = []
    action_counts: Counter[str] = Counter()
    epistemic_counts: Counter[str] = Counter()
    switches = 0
    active_decisions = 0
    total_trigger_decisions = 0

    for trade in ordered:
        key = (trade.symbol, trade.entry_at)
        row = audit_data[key]
        surface_mode = str(row["causal_surface_mode"])
        chosen_mode = str(row["chosen_mode"])
        switched = chosen_mode != surface_mode
        switches += int(switched)
        total_trigger_decisions += int(bool(row["decision_made"]))
        active_decisions += int(bool(row["active_drawdown_episode"]))
        action_counts[chosen_mode] += 1
        epistemic_counts[str(row["metacognitive_state"])] += 1

        values = row["values"]
        if values is None:
            (
                surf_haz_a,
                surf_haz_b,
                act_haz_a,
                act_haz_b,
                surf_sev_a,
                surf_sev_b,
                act_sev_a,
                act_sev_b,
                total_a,
                total_b,
                worst_sev,
                worst_haz,
            ) = (None,) * 12
        else:
            (
                surf_haz_a,
                surf_haz_b,
                act_haz_a,
                act_haz_b,
                surf_sev_a,
                surf_sev_b,
                act_sev_a,
                act_sev_b,
                total_a,
                total_b,
                worst_sev,
                worst_haz,
            ) = values

        audits.append(
            V35Decision(
                period=period,
                policy=POLICY,
                symbol=trade.symbol,
                session=trade.session,
                operating_date=trade.operating_date,
                entry_at=trade.entry_at,
                causal_surface_mode=surface_mode,
                chosen_mode=chosen_mode,
                surface_first_family=row["surface_first_family"],
                surface_first_protection_at=row[
                    "surface_first_protection_at"
                ],
                decision_made=bool(row["decision_made"]),
                active_drawdown_episode=bool(
                    row["active_drawdown_episode"]
                ),
                switched=switched,
                metacognitive_state=str(row["metacognitive_state"]),
                pretrigger_realized_dd_r=str(
                    row["pretrigger_realized_dd_r"]
                ),
                base_multiplier=str(row["base_multiplier"]),
                completed_m1_bars=row["completed_m1_bars"],
                trigger_delay_minutes=row["trigger_delay_minutes"],
                trainer_a_period=trainer_a,
                trainer_b_period=trainer_b,
                robust_worst_world_severity_ucb=(
                    None if worst_sev is None else str(worst_sev)
                ),
                robust_worst_world_hazard_ucb=(
                    None if worst_haz is None else str(worst_haz)
                ),
                trainer_a_surface_hazard_ucb=(
                    None if surf_haz_a is None else str(surf_haz_a)
                ),
                trainer_b_surface_hazard_ucb=(
                    None if surf_haz_b is None else str(surf_haz_b)
                ),
                trainer_a_action_hazard_ucb=(
                    None if act_haz_a is None else str(act_haz_a)
                ),
                trainer_b_action_hazard_ucb=(
                    None if act_haz_b is None else str(act_haz_b)
                ),
                trainer_a_surface_severity_ucb=(
                    None if surf_sev_a is None else str(surf_sev_a)
                ),
                trainer_b_surface_severity_ucb=(
                    None if surf_sev_b is None else str(surf_sev_b)
                ),
                trainer_a_action_severity_ucb=(
                    None if act_sev_a is None else str(act_sev_a)
                ),
                trainer_b_action_severity_ucb=(
                    None if act_sev_b is None else str(act_sev_b)
                ),
                trainer_a_total_delta_lcb=(
                    None if total_a is None else str(total_a)
                ),
                trainer_b_total_delta_lcb=(
                    None if total_b is None else str(total_b)
                ),
                eligible_action_count=int(row["eligible_action_count"]),
            )
        )

    return {
        "period": period,
        "policy": POLICY,
        "trades": len(ledger),
        "density_retention": "1",
        "metrics": milestone._metrics(ledger),
        "surface_trigger_decision_count": total_trigger_decisions,
        "active_drawdown_trigger_count": active_decisions,
        "action_override_count": switches,
        "action_counts": dict(sorted(action_counts.items())),
        "metacognitive_state_counts": dict(sorted(epistemic_counts.items())),
    }, tuple(audits)


def build_report(
    development_root: Path,
    validation_root: Path,
    reserved_root: Path,
    development_validation_context_root: Path,
    reserved_context_root: Path,
    trigger_state_root: Path,
) -> tuple[dict[str, Any], tuple[V35Decision, ...]]:
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
        controls, _control_rows, _control_maps = v22._control_decision_maps(
            windows,
            contextual_model,
        )
        control_states: dict[
            str, dict[tuple[str, str, str], v31.ControlTriggerState]
        ] = {}
        control_ledgers: dict[
            str, tuple[milestone.SimulatedTrade, ...]
        ] = {}
        for period, (ledgers, contexts) in windows.items():
            states, ledger = v31._control_event_replay(
                period=period,
                ledgers=ledgers,
                contexts=contexts,
                contextual_model=contextual_model,
                native_states=native_states,
            )
            if milestone._metrics(ledger) != controls[period]["metrics"]:
                raise ValueError(
                    f"V35 Surface control replay drift in {period}"
                )
            control_states[period] = states
            control_ledgers[period] = ledger

        models, model_diagnostics = _fit_models(
            windows=windows,
            control_states=control_states,
            control_ledgers=control_ledgers,
        )

        results: list[dict[str, Any]] = []
        audits: list[V35Decision] = []
        for heldout, (ledgers, contexts) in windows.items():
            trainers = tuple(period for period in windows if period != heldout)
            if len(trainers) != 2:
                raise ValueError("V35 requires exactly two external periods")
            trainer_a, trainer_b = trainers
            current, current_audits = _simulate_period(
                period=heldout,
                ledgers=ledgers,
                contexts=contexts,
                contextual_model=contextual_model,
                trainer_a=trainer_a,
                trainer_b=trainer_b,
                model_a=models[trainer_a],
                model_b=models[trainer_b],
                native_states=native_states,
            )
            v10._annotate(current, controls[heldout])
            current["losing_streak_not_worse"] = (
                int(current["metrics"]["max_losing_streak"])
                <= int(controls[heldout]["metrics"]["max_losing_streak"])
            )
            results.append(current)
            audits.extend(current_audits)
    finally:
        v11._SIMULTANEOUS.clear()
        v11._SIMULTANEOUS.update(previous)

    full_gate = all(
        row["pf_at_least_surface_control"]
        and row["total_r_at_least_surface_control"]
        and row["dd_below_surface_control"]
        and row["dd_at_or_below_6r"]
        and row["losing_streak_not_worse"]
        for row in results
    )
    total_overrides = sum(int(row["action_override_count"]) for row in results)
    candidate_count = int(full_gate and total_overrides > 0)

    return {
        "identity": IDENTITY,
        "evaluation": "STRUCTURAL_DRAWDOWN_FIRST_PASSAGE_TRANSITION",
        "policy": POLICY,
        "surface_default": True,
        "source_trigger_state_run_id": SOURCE_TRIGGER_STATE_RUN_ID,
        "source_trigger_state_identity": v29.IDENTITY,
        "v31_causal_state_preserved": True,
        "causal_state_dimension": EXPECTED_FEATURE_DIMENSION,
        "decision_only_inside_active_realized_drawdown": True,
        "first_passage_hazard_target": "DEEPEN_TROUGH_BEFORE_RECOVER_PEAK",
        "first_passage_event_order": "EXIT_AT_THEN_ENTRY_AT_THEN_SYMBOL_MATCH_V31",
        "additional_trough_severity_target": True,
        "value_preservation_total_delta_head": True,
        "chronological_calibration_folds": CHRONOLOGICAL_FOLDS,
        "minimum_chronological_calibration_examples": (
            MIN_CHRONOLOGICAL_CALIBRATION_EXAMPLES
        ),
        "hazard_severity_residual_upper_quantile": str(
            UPPER_RESIDUAL_QUANTILE
        ),
        "total_delta_residual_lower_quantile": str(
            LOWER_RESIDUAL_QUANTILE
        ),
        "l2_prior_strength_effective_trades": str(L2_PRIOR_STRENGTH),
        "dual_world_structural_dominance_gate": True,
        "numeric_improvement_threshold_added": False,
        "model_diagnostics": model_diagnostics,
        "results": results,
        "total_action_overrides": total_overrides,
        "candidate_count": candidate_count,
        "all_entries_preserved": True,
        "density_retention": "1",
        "same_entrant_identities": True,
        "fixed_target_r": "2.00",
        "original_stop_geometry_preserved_at_entry": True,
        "new_protection_geometry_created": False,
        "sizing_changed": False,
        "max3_preserved": True,
        "max3_slot_recycling": False,
        "chosen_prior_outcomes_recompute_future_state": True,
        "current_outcome_visible_to_decision": False,
        "heldout_counterfactual_visible_to_decision": False,
        "future_after_trigger_visible_to_decision": False,
        "activation_bar_ohlc_visible_to_decision": False,
        "era_identity_feature_used": False,
        "symbol_session_side_time_identity_features_used": False,
        "fresh_holdout_opened": False,
        "full_source_identity_proof_required_before_freeze": True,
        "certification_standard_v2_required_downstream": True,
        "automatic_policy_promotion": False,
        "trader_certified": False,
        "live_authorized": False,
        "real_capital_authorized": False,
        "next_phase": (
            "FULL_SOURCE_IDENTITY_PROOF_V35_SURVIVOR"
            if candidate_count
            else "V35_FALSIFIED_MULTI_POSITION_CAUSAL_EPISODE_SIMULATION_REQUIRED"
        ),
    }, tuple(audits)


def write_report(
    report: dict[str, Any],
    audits: tuple[V35Decision, ...],
    output: Path,
) -> None:
    output.mkdir(parents=True, exist_ok=True)
    stem = "capitalizer-structural-drawdown-hazard-transition-v35"
    (output / f"{stem}.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    with (output / f"{stem}-decisions.jsonl").open(
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

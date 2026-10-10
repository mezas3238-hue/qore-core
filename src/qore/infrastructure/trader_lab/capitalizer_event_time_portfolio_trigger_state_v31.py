"""Event-time portfolio/cross-market trigger-state policy for Capitalizer V31.

V31 keeps V30's physical protection toolbox and action gate unchanged. The only
experimental delta is a strictly-causal portfolio/cross-market vector computed
at Surface's first real protection intervention under a globally chronological
entry/trigger replay.

Same-timestamp entry and trigger decisions read one immutable pre-batch state.
No peer action or peer outcome from that timestamp is visible until later time.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
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
    capitalizer_causal_trigger_state_veto_policy_v29 as v29,
)
from qore.infrastructure.trader_lab import (
    capitalizer_cognitive_r_milestone_protection_2r_v1 as milestone,
)
from qore.infrastructure.trader_lab import (
    capitalizer_continuation_value_model_v22 as v22,
)
from qore.infrastructure.trader_lab import capitalizer_exposure_graph as exposure
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

IDENTITY = "QORE_CAPITALIZER_EVENT_TIME_PORTFOLIO_TRIGGER_STATE_V31"
POLICY = "FIRST_INTERVENTION_ROBUST_EVENT_TIME_PORTFOLIO_STATE"
L2_PRIOR_STRENGTH = v25.L2_PRIOR_STRENGTH
SOURCE_TRIGGER_STATE_RUN_ID = 36283499014
EVENT_PORTFOLIO_FEATURES = (
    "REALIZED_PORTFOLIO_DD_R",
    "RECENT_3_CLOSED_SCALED_R",
    "RECENT_5_CLOSED_SCALED_R",
    "RECENT_10_CLOSED_SCALED_R",
    "REALIZED_CLOSED_LOSS_STREAK",
    "CLOSED_SINCE_CURRENT_ENTRY_COUNT",
    "CLOSED_SINCE_CURRENT_ENTRY_SCALED_R",
    "NEGATIVE_CLOSED_SINCE_CURRENT_ENTRY_COUNT",
    "CLOSED_SINCE_REALIZED_EQUITY_PEAK_COUNT",
    "ACTIVE_OTHER_POSITION_COUNT",
    "ACTIVE_SAME_SESSION_OTHER_POSITION_COUNT",
    "ACTIVE_SHARED_FACTOR_POSITION_COUNT",
    "ACTIVE_ALIGNED_SHARED_FACTOR_STRUCTURAL_R",
    "ACTIVE_OPPOSED_SHARED_FACTOR_STRUCTURAL_R",
    "SAME_OPERATING_DAY_CLOSED_SCALED_R",
    "SAME_OPERATING_DAY_NEGATIVE_FRACTION",
    "CURRENT_SESSION_CLOSED_SCALED_R",
    "CURRENT_SESSION_NEGATIVE_FRACTION",
    "PRIOR_SESSION_CLOSED_SCALED_R",
    "PRIOR_SESSION_NEGATIVE_FRACTION",
)
EVENT_PORTFOLIO_FEATURE_DIMENSION = len(EVENT_PORTFOLIO_FEATURES)
EXPECTED_FEATURE_DIMENSION = 95

FamilyModels = dict[
    str,
    dict[str, dict[str, tuple[v25.RidgeModel, v25.RidgeModel]]],
]


@dataclass(frozen=True, slots=True)
class ControlTriggerState:
    period: str
    symbol: str
    session: str
    operating_date: str
    entry_at: str
    surface_mode: str
    family: str
    trigger_at: str
    base_multiplier: str
    completed_m1_bars: int
    vector: tuple[float, ...]
    current_outcome_visible: bool = False
    active_peer_outcome_visible: bool = False
    same_timestamp_peer_outcome_visible: bool = False
    future_exit_visible_as_outcome: bool = False
    activation_bar_ohlc_visible: bool = False
    identity_features_used: bool = False


@dataclass(frozen=True, slots=True)
class V31Decision:
    period: str
    policy: str
    symbol: str
    session: str
    operating_date: str
    entry_at: str
    causal_surface_mode: str
    surface_first_family: str | None
    surface_first_protection_at: str | None
    chosen_mode: str
    base_multiplier: str
    decision_made: bool
    switched: bool
    switched_to_original: bool
    switched_to_later_trigger: bool
    chosen_first_family: str | None
    completed_m1_bars: int | None
    trigger_delay_minutes: str | None
    trainer_a_period: str
    trainer_b_period: str
    robust_total_delta: str | None
    trainer_a_total_delta: str | None
    trainer_b_total_delta: str | None
    trainer_a_downside_delta: str | None
    trainer_b_downside_delta: str | None
    eligible_action_count: int
    portfolio_vector: tuple[float, ...] | None
    current_outcome_visible: bool = False
    active_peer_outcome_visible: bool = False
    same_timestamp_peer_outcome_visible: bool = False
    future_exit_visible_as_outcome: bool = False
    activation_bar_ohlc_visible: bool = False
    identity_features_used: bool = False


def _aware(value: str) -> datetime:
    return milestone._aware(value)


def _snapshot_rows(
    projections: dict[tuple[str, str], milestone.SimulatedTrade],
) -> tuple[milestone.SimulatedTrade, ...]:
    return tuple(
        sorted(
            projections.values(),
            key=lambda row: (_aware(row.entry_at), row.symbol),
        )
    )


def _snapshot_records(
    records: dict[tuple[str, str], memory.MemoryRecord],
) -> tuple[memory.MemoryRecord, ...]:
    return tuple(
        records[key]
        for key in sorted(
            records,
            key=lambda item: (_aware(item[1]), item[0]),
        )
    )


def _scaled_trade(
    row: milestone.SimulatedTrade,
    *,
    multiplier: Decimal,
) -> milestone.SimulatedTrade:
    return replace(
        row,
        realized_gross_r=str(Decimal(row.realized_gross_r) * multiplier),
    )


def _record(
    *,
    pretrade: v10.Pretrade,
    selected: milestone.SimulatedTrade,
) -> memory.MemoryRecord:
    return memory.MemoryRecord(
        symbol=pretrade.ctx.symbol,
        session=pretrade.ctx.session,
        destination_state=pretrade.ctx.destination_state,
        context_signature=pretrade.ctx.context_signature,
        exit_at=selected.exit_at,
        normalized_realized_r=selected.realized_gross_r,
    )


def _closed_before(
    rows: tuple[milestone.SimulatedTrade, ...],
    *,
    observed_at: datetime,
) -> tuple[milestone.SimulatedTrade, ...]:
    return tuple(
        sorted(
            (
                row
                for row in rows
                if _aware(row.exit_at) < observed_at
            ),
            key=lambda row: (
                _aware(row.exit_at),
                _aware(row.entry_at),
                row.symbol,
            ),
        )
    )


def _active_before_event(
    rows: tuple[milestone.SimulatedTrade, ...],
    *,
    observed_at: datetime,
    current_key: tuple[str, str],
) -> tuple[milestone.SimulatedTrade, ...]:
    return tuple(
        row
        for row in rows
        if (row.symbol, row.entry_at) != current_key
        and _aware(row.entry_at) < observed_at
        and observed_at <= _aware(row.exit_at)
    )


def _sum_and_negative_fraction(
    rows: tuple[milestone.SimulatedTrade, ...],
) -> tuple[Decimal, Decimal]:
    if not rows:
        return Decimal("0"), Decimal("0.5")
    values = tuple(Decimal(row.realized_gross_r) for row in rows)
    return (
        sum(values, Decimal("0")),
        Decimal(sum(value < 0 for value in values)) / Decimal(len(values)),
    )


def _portfolio_vector(
    *,
    current_trade: milestone.SimulatedTrade,
    observed_at: datetime,
    projections: tuple[milestone.SimulatedTrade, ...],
) -> tuple[float, ...]:
    current_key = (current_trade.symbol, current_trade.entry_at)
    closed = _closed_before(projections, observed_at=observed_at)
    active = _active_before_event(
        projections,
        observed_at=observed_at,
        current_key=current_key,
    )
    values = tuple(Decimal(row.realized_gross_r) for row in closed)

    equity = Decimal("0")
    peak = Decimal("0")
    peak_index = -1
    for index, value in enumerate(values):
        equity += value
        if equity >= peak:
            peak = equity
            peak_index = index
    realized_dd = peak - equity
    closed_since_peak = len(closed) - peak_index - 1

    def recent_sum(count: int) -> Decimal:
        return sum(values[-count:], Decimal("0"))

    loss_streak = 0
    for value in reversed(values):
        if value >= 0:
            break
        loss_streak += 1

    entry_at = _aware(current_trade.entry_at)
    closed_since_entry = tuple(
        row
        for row in closed
        if _aware(row.exit_at) > entry_at
    )
    since_entry_values = tuple(
        Decimal(row.realized_gross_r) for row in closed_since_entry
    )

    same_session_active = tuple(
        row for row in active if row.session == current_trade.session
    )

    candidate_factors = v11._factor_map(
        symbol=current_trade.symbol,
        side=current_trade.side,
    )
    current_factor_names = frozenset(candidate_factors)
    active_positions = tuple(
        exposure.CapitalizerExposurePosition(
            symbol=row.symbol,
            side=exposure.CapitalizerSide(row.side),
            risk_r=Decimal("1"),
        )
        for row in active
    )
    active_factor_map = {
        row.factor: row
        for row in exposure.factor_exposures(active_positions)
    }
    shared_positions = sum(
        bool(
            current_factor_names
            & frozenset(
                v11._factor_map(symbol=row.symbol, side=row.side)
            )
        )
        for row in active
    )
    aligned = Decimal("0")
    opposed = Decimal("0")
    for factor, candidate in candidate_factors.items():
        prior = active_factor_map.get(factor)
        if prior is None:
            continue
        product = candidate.net_r * prior.net_r
        if product > 0:
            aligned += abs(prior.net_r)
        elif product < 0:
            opposed += abs(prior.net_r)

    same_day = tuple(
        row
        for row in closed
        if row.operating_date == current_trade.operating_date
    )
    same_session = tuple(
        row for row in same_day if row.session == current_trade.session
    )
    rank = v11.SESSION_ORDER[current_trade.session]
    prior_sessions = tuple(
        row
        for row in same_day
        if v11.SESSION_ORDER.get(row.session, -1) < rank
    )
    day_sum, day_neg = _sum_and_negative_fraction(same_day)
    session_sum, session_neg = _sum_and_negative_fraction(same_session)
    prior_sum, prior_neg = _sum_and_negative_fraction(prior_sessions)

    vector = (
        float(realized_dd),
        float(recent_sum(3)),
        float(recent_sum(5)),
        float(recent_sum(10)),
        float(loss_streak),
        float(len(closed_since_entry)),
        float(sum(since_entry_values, Decimal("0"))),
        float(sum(value < 0 for value in since_entry_values)),
        float(closed_since_peak),
        float(len(active)),
        float(len(same_session_active)),
        float(shared_positions),
        float(aligned),
        float(opposed),
        float(day_sum),
        float(day_neg),
        float(session_sum),
        float(session_neg),
        float(prior_sum),
        float(prior_neg),
    )
    if len(vector) != EVENT_PORTFOLIO_FEATURE_DIMENSION:
        raise ValueError("V31 portfolio feature dimension drift")
    return vector


def _full_trigger_vector(
    *,
    pretrade: v10.Pretrade,
    trade: milestone.SimulatedTrade,
    trigger_at: str,
    native_state: v29.TriggerState,
    portfolio: tuple[float, ...],
) -> tuple[float, ...]:
    vector = (
        *v29._trigger_features(
            pretrade,
            entry_at=trade.entry_at,
            trigger_at=trigger_at,
            state=native_state,
        ),
        *portfolio,
    )
    if len(vector) != EXPECTED_FEATURE_DIMENSION:
        raise ValueError(
            f"V31 feature dimension drift {len(vector)} "
            f"!= {EXPECTED_FEATURE_DIMENSION}"
        )
    return vector


def _entry_batch(
    *,
    period: str,
    rows: tuple[milestone.SimulatedTrade, ...],
    modes: dict[str, dict[tuple[str, str], milestone.SimulatedTrade]],
    contexts: dict[tuple[str, str], Any],
    contextual_model: dict[str, Any],
    snapshot_projections: tuple[milestone.SimulatedTrade, ...],
    snapshot_records: tuple[memory.MemoryRecord, ...],
) -> tuple[
    dict[tuple[str, str], v10.Pretrade],
    dict[tuple[str, str], milestone.SimulatedTrade],
    dict[tuple[str, str], memory.MemoryRecord],
    dict[tuple[str, str], tuple[datetime, str]],
]:
    pretrades: dict[tuple[str, str], v10.Pretrade] = {}
    projections: dict[tuple[str, str], milestone.SimulatedTrade] = {}
    records: dict[tuple[str, str], memory.MemoryRecord] = {}
    triggers: dict[tuple[str, str], tuple[datetime, str]] = {}

    for trade in rows:
        key = (trade.symbol, trade.entry_at)
        pretrade = v11._pretrade(
            period=period,
            trade=trade,
            contexts=contexts,
            contextual_model=contextual_model,
            chosen_scaled=snapshot_projections,
            records=snapshot_records,
        )
        selected = modes[pretrade.mode][key]
        scaled = _scaled_trade(
            selected,
            multiplier=pretrade.base_multiplier,
        )
        pretrades[key] = pretrade
        projections[key] = scaled
        records[key] = _record(pretrade=pretrade, selected=selected)

        family = v30._mode_family(pretrade.mode)
        trigger_raw = selected.first_protection_at
        if family is not None and trigger_raw is not None:
            trigger_at = _aware(trigger_raw)
            if trigger_at <= _aware(trade.entry_at):
                raise ValueError("V31 protection trigger must follow entry")
            triggers[key] = (trigger_at, family)

    return pretrades, projections, records, triggers


def _next_event_time(
    *,
    ordered: tuple[milestone.SimulatedTrade, ...],
    pointer: int,
    pending: dict[tuple[str, str], tuple[datetime, str]],
) -> datetime | None:
    next_entry = (
        _aware(ordered[pointer].entry_at)
        if pointer < len(ordered)
        else None
    )
    next_trigger = (
        min(value[0] for value in pending.values())
        if pending
        else None
    )
    candidates = tuple(
        value for value in (next_entry, next_trigger) if value is not None
    )
    if not candidates:
        return None
    return min(candidates)


def _control_event_replay(
    *,
    period: str,
    ledgers: dict[str, tuple[milestone.SimulatedTrade, ...]],
    contexts: dict[tuple[str, str], Any],
    contextual_model: dict[str, Any],
    native_states: dict[tuple[str, str, str, str], v29.TriggerState],
) -> tuple[
    dict[tuple[str, str, str], ControlTriggerState],
    tuple[milestone.SimulatedTrade, ...],
]:
    modes = v29._by_mode(ledgers)
    ordered = tuple(
        sorted(
            ledgers[milestone.ProtectionMode.ORIGINAL.value],
            key=lambda row: (_aware(row.entry_at), row.symbol),
        )
    )
    pointer = 0
    projections: dict[
        tuple[str, str], milestone.SimulatedTrade
    ] = {}
    records: dict[tuple[str, str], memory.MemoryRecord] = {}
    pretrades: dict[tuple[str, str], v10.Pretrade] = {}
    pending: dict[tuple[str, str], tuple[datetime, str]] = {}
    states: dict[tuple[str, str, str], ControlTriggerState] = {}

    while pointer < len(ordered) or pending:
        now = _next_event_time(
            ordered=ordered,
            pointer=pointer,
            pending=pending,
        )
        if now is None:
            break
        snapshot_projections = _snapshot_rows(projections)
        snapshot_records = _snapshot_records(records)

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
        for key in trigger_keys:
            trigger_at, family = pending[key]
            pretrade = pretrades[key]
            trade = modes[milestone.ProtectionMode.ORIGINAL.value][key]
            native = native_states.get(
                (period, trade.symbol, trade.entry_at, family)
            )
            if native is None:
                raise ValueError("V31 missing control native trigger state")
            if _aware(native.trigger_at) != trigger_at:
                raise ValueError("V31 control trigger timestamp drift")
            portfolio = _portfolio_vector(
                current_trade=trade,
                observed_at=trigger_at,
                projections=snapshot_projections,
            )
            vector = _full_trigger_vector(
                pretrade=pretrade,
                trade=trade,
                trigger_at=native.trigger_at,
                native_state=native,
                portfolio=portfolio,
            )
            states[(trade.symbol, trade.entry_at, family)] = (
                ControlTriggerState(
                    period=period,
                    symbol=trade.symbol,
                    session=trade.session,
                    operating_date=trade.operating_date,
                    entry_at=trade.entry_at,
                    surface_mode=pretrade.mode,
                    family=family,
                    trigger_at=native.trigger_at,
                    base_multiplier=str(pretrade.base_multiplier),
                    completed_m1_bars=native.completed_m1_bars,
                    vector=vector,
                )
            )

        entry_rows: list[milestone.SimulatedTrade] = []
        while (
            pointer < len(ordered)
            and _aware(ordered[pointer].entry_at) == now
        ):
            entry_rows.append(ordered[pointer])
            pointer += 1
        if entry_rows:
            (
                new_pretrades,
                new_projections,
                new_records,
                new_triggers,
            ) = _entry_batch(
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
            pending.pop(key)
        pretrades.update(new_pretrades)
        projections.update(new_projections)
        records.update(new_records)
        pending.update(new_triggers)

    ledger = _snapshot_rows(projections)
    if len(ledger) != len(ordered):
        raise ValueError("V31 control replay lost entrants")
    return states, ledger


def _training_examples(
    *,
    family: str,
    action: str,
    states: dict[tuple[str, str, str], ControlTriggerState],
    ledgers: dict[str, tuple[milestone.SimulatedTrade, ...]],
) -> tuple[
    tuple[v25.TrainingExample, ...],
    tuple[v25.TrainingExample, ...],
]:
    if action not in v30._eligible_actions(family):
        raise ValueError("V31 action outside V30 reachability")
    modes = v29._by_mode(ledgers)
    total_examples: list[v25.TrainingExample] = []
    downside_examples: list[v25.TrainingExample] = []

    for key3, state in states.items():
        symbol, entry_at, state_family = key3
        if state_family != family:
            continue
        key = (symbol, entry_at)
        actions = v30._eligible_actions(family)
        v30._assert_common_path(
            key=key,
            trigger_at=state.trigger_at,
            actions=actions,
            modes=modes,
        )
        surface_r = Decimal(
            modes[state.surface_mode][key].realized_gross_r
        )
        action_r = Decimal(modes[action][key].realized_gross_r)
        total_delta = action_r - surface_r
        downside_delta = min(action_r, Decimal("0")) - min(
            surface_r,
            Decimal("0"),
        )
        total_examples.append(
            (state.vector, float(total_delta), 1.0, key)
        )
        downside_examples.append(
            (state.vector, float(downside_delta), 1.0, key)
        )

    return tuple(total_examples), tuple(downside_examples)


def _fit_models(
    *,
    windows: dict[str, Any],
    control_states: dict[
        str, dict[tuple[str, str, str], ControlTriggerState]
    ],
) -> tuple[FamilyModels, dict[str, Any]]:
    models: FamilyModels = {}
    diagnostics: dict[str, Any] = {}

    for period, (ledgers, _contexts) in windows.items():
        period_models: dict[
            str, dict[str, tuple[v25.RidgeModel, v25.RidgeModel]]
        ] = {}
        period_diagnostics: dict[str, Any] = {}

        for family in v30.FAMILY_ORDER:
            action_models: dict[
                str, tuple[v25.RidgeModel, v25.RidgeModel]
            ] = {}
            action_diagnostics: dict[str, Any] = {}
            for action in v30._eligible_actions(family):
                total_examples, downside_examples = _training_examples(
                    family=family,
                    action=action,
                    states=control_states[period],
                    ledgers=ledgers,
                )
                if not total_examples:
                    action_diagnostics[action] = {
                        "available": False,
                        "training_trades": 0,
                    }
                    continue
                total_model = v25._fit_model(
                    period=f"{period}:{family}:{action}:TOTAL",
                    examples=total_examples,
                )
                downside_model = v25._fit_model(
                    period=f"{period}:{family}:{action}:DOWNSIDE",
                    examples=downside_examples,
                )
                action_models[action] = (total_model, downside_model)
                action_diagnostics[action] = {
                    "available": True,
                    "training_trades": total_model.unique_training_trades,
                    "feature_dimension": total_model.feature_dimension,
                    "total_target_mean": str(
                        total_model.weighted_target_mean
                    ),
                    "downside_target_mean": str(
                        downside_model.weighted_target_mean
                    ),
                    "total_rmse": str(
                        total_model.weighted_training_rmse
                    ),
                    "downside_rmse": str(
                        downside_model.weighted_training_rmse
                    ),
                }
            period_models[family] = action_models
            period_diagnostics[family] = action_diagnostics

        models[period] = period_models
        diagnostics[period] = period_diagnostics

    return models, diagnostics


def _simulate_period(
    *,
    period: str,
    ledgers: dict[str, tuple[milestone.SimulatedTrade, ...]],
    contexts: dict[tuple[str, str], Any],
    contextual_model: dict[str, Any],
    trainer_a: str,
    trainer_b: str,
    model_a: dict[
        str, dict[str, tuple[v25.RidgeModel, v25.RidgeModel]]
    ],
    model_b: dict[
        str, dict[str, tuple[v25.RidgeModel, v25.RidgeModel]]
    ],
    native_states: dict[tuple[str, str, str, str], v29.TriggerState],
) -> tuple[dict[str, Any], tuple[V31Decision, ...]]:
    modes = v29._by_mode(ledgers)
    ordered = tuple(
        sorted(
            ledgers[milestone.ProtectionMode.ORIGINAL.value],
            key=lambda row: (_aware(row.entry_at), row.symbol),
        )
    )
    pointer = 0
    projections: dict[
        tuple[str, str], milestone.SimulatedTrade
    ] = {}
    records: dict[tuple[str, str], memory.MemoryRecord] = {}
    pretrades: dict[tuple[str, str], v10.Pretrade] = {}
    pending: dict[tuple[str, str], tuple[Any, str]] = {}
    audit_data: dict[tuple[str, str], dict[str, Any]] = {}

    while pointer < len(ordered) or pending:
        now = _next_event_time(
            ordered=ordered,
            pointer=pointer,
            pending=pending,
        )
        if now is None:
            break
        snapshot_projections = _snapshot_rows(projections)
        snapshot_records = _snapshot_records(records)

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
                float | None,
                tuple[float, float, float, float] | None,
                tuple[float, ...],
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
                raise ValueError("V31 missing held-out native trigger state")
            if _aware(native.trigger_at) != trigger_at:
                raise ValueError("V31 held-out trigger timestamp drift")
            portfolio = _portfolio_vector(
                current_trade=trade,
                observed_at=trigger_at,
                projections=snapshot_projections,
            )
            features = _full_trigger_vector(
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
            action, score, predictions = v30._choose_action(
                features=features,
                surface_mode=pretrade.mode,
                actions=actions,
                model_a=model_a[family],
                model_b=model_b[family],
            )
            chosen_mode = pretrade.mode if action is None else action
            trigger_updates[key] = (
                chosen_mode,
                score,
                predictions,
                portfolio,
                native.completed_m1_bars,
            )

        entry_rows: list[milestone.SimulatedTrade] = []
        while (
            pointer < len(ordered)
            and _aware(ordered[pointer].entry_at) == now
        ):
            entry_rows.append(ordered[pointer])
            pointer += 1
        if entry_rows:
            (
                new_pretrades,
                new_projections,
                new_records,
                new_triggers,
            ) = _entry_batch(
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
            chosen_mode, score, predictions, portfolio, completed = (
                trigger_updates[key]
            )
            pretrade = pretrades[key]
            selected = modes[chosen_mode][key]
            projections[key] = _scaled_trade(
                selected,
                multiplier=pretrade.base_multiplier,
            )
            records[key] = _record(
                pretrade=pretrade,
                selected=selected,
            )

            if predictions is None:
                total_a = total_b = downside_a = downside_b = None
            else:
                total_a, total_b, downside_a, downside_b = predictions
            row = audit_data[key]
            row.update(
                decision_made=True,
                chosen_mode=chosen_mode,
                chosen_first_family=v30._mode_family(chosen_mode),
                completed_m1_bars=completed,
                trigger_delay_minutes=str(
                    (
                        trigger_at
                        - _aware(key[1])
                    ).total_seconds()
                    / 60.0
                ),
                robust_total_delta=(
                    None if score is None else str(score)
                ),
                trainer_a_total_delta=(
                    None if total_a is None else str(total_a)
                ),
                trainer_b_total_delta=(
                    None if total_b is None else str(total_b)
                ),
                trainer_a_downside_delta=(
                    None if downside_a is None else str(downside_a)
                ),
                trainer_b_downside_delta=(
                    None if downside_b is None else str(downside_b)
                ),
                eligible_action_count=len(
                    v30._eligible_actions(family)
                ),
                portfolio_vector=portfolio,
            )

        for key, pretrade in new_pretrades.items():
            trade = modes[milestone.ProtectionMode.ORIGINAL.value][key]
            selected = modes[pretrade.mode][key]
            entry_family = v30._mode_family(pretrade.mode)
            audit_data[key] = {
                "period": period,
                "policy": POLICY,
                "symbol": trade.symbol,
                "session": trade.session,
                "operating_date": trade.operating_date,
                "entry_at": trade.entry_at,
                "causal_surface_mode": pretrade.mode,
                "surface_first_family": entry_family,
                "surface_first_protection_at": selected.first_protection_at,
                "chosen_mode": pretrade.mode,
                "base_multiplier": str(pretrade.base_multiplier),
                "decision_made": False,
                "chosen_first_family": entry_family,
                "completed_m1_bars": None,
                "trigger_delay_minutes": None,
                "trainer_a_period": trainer_a,
                "trainer_b_period": trainer_b,
                "robust_total_delta": None,
                "trainer_a_total_delta": None,
                "trainer_b_total_delta": None,
                "trainer_a_downside_delta": None,
                "trainer_b_downside_delta": None,
                "eligible_action_count": 0,
                "portfolio_vector": None,
            }

        pretrades.update(new_pretrades)
        projections.update(new_projections)
        records.update(new_records)
        pending.update(new_triggers)

    ledger = _snapshot_rows(projections)
    if len(ledger) != len(ordered):
        raise ValueError("V31 held-out replay lost entrants")

    audits: list[V31Decision] = []
    action_counts: Counter[str] = Counter()
    surface_family_counts: Counter[str] = Counter()
    switches = 0
    later_switches = 0
    original_switches = 0
    decisions = 0

    for trade in ordered:
        key = (trade.symbol, trade.entry_at)
        row = audit_data[key]
        surface_mode = str(row["causal_surface_mode"])
        chosen_mode = str(row["chosen_mode"])
        switched = chosen_mode != surface_mode
        surface_family = row["surface_first_family"]
        chosen_family = row["chosen_first_family"]
        switched_to_original = (
            switched
            and chosen_mode == milestone.ProtectionMode.ORIGINAL.value
        )
        switched_to_later = (
            switched
            and surface_family is not None
            and chosen_family is not None
            and v30.FAMILY_RANK[chosen_family]
            > v30.FAMILY_RANK[surface_family]
        )
        switches += int(switched)
        original_switches += int(switched_to_original)
        later_switches += int(switched_to_later)
        decisions += int(bool(row["decision_made"]))
        action_counts[chosen_mode] += 1
        if surface_family is not None and row["decision_made"]:
            surface_family_counts[surface_family] += 1

        audits.append(
            V31Decision(
                period=period,
                policy=POLICY,
                symbol=trade.symbol,
                session=trade.session,
                operating_date=trade.operating_date,
                entry_at=trade.entry_at,
                causal_surface_mode=surface_mode,
                surface_first_family=surface_family,
                surface_first_protection_at=row[
                    "surface_first_protection_at"
                ],
                chosen_mode=chosen_mode,
                base_multiplier=str(row["base_multiplier"]),
                decision_made=bool(row["decision_made"]),
                switched=switched,
                switched_to_original=switched_to_original,
                switched_to_later_trigger=switched_to_later,
                chosen_first_family=chosen_family,
                completed_m1_bars=row["completed_m1_bars"],
                trigger_delay_minutes=row["trigger_delay_minutes"],
                trainer_a_period=trainer_a,
                trainer_b_period=trainer_b,
                robust_total_delta=row["robust_total_delta"],
                trainer_a_total_delta=row["trainer_a_total_delta"],
                trainer_b_total_delta=row["trainer_b_total_delta"],
                trainer_a_downside_delta=row[
                    "trainer_a_downside_delta"
                ],
                trainer_b_downside_delta=row[
                    "trainer_b_downside_delta"
                ],
                eligible_action_count=int(row["eligible_action_count"]),
                portfolio_vector=row["portfolio_vector"],
            )
        )

    return {
        "period": period,
        "policy": POLICY,
        "trades": len(ledger),
        "density_retention": "1",
        "metrics": milestone._metrics(ledger),
        "first_intervention_decision_count": decisions,
        "action_switch_count": switches,
        "switch_to_original_count": original_switches,
        "switch_to_later_trigger_count": later_switches,
        "action_counts": dict(sorted(action_counts.items())),
        "surface_family_decision_counts": dict(
            sorted(surface_family_counts.items())
        ),
    }, tuple(audits)


def build_report(
    development_root: Path,
    validation_root: Path,
    reserved_root: Path,
    development_validation_context_root: Path,
    reserved_context_root: Path,
    trigger_state_root: Path,
) -> tuple[dict[str, Any], tuple[V31Decision, ...]]:
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
        controls, _control_rows, _control_maps = (
            v22._control_decision_maps(
                windows,
                contextual_model,
            )
        )
        control_states: dict[
            str, dict[tuple[str, str, str], ControlTriggerState]
        ] = {}
        for period, (ledgers, contexts) in windows.items():
            states, control_ledger = _control_event_replay(
                period=period,
                ledgers=ledgers,
                contexts=contexts,
                contextual_model=contextual_model,
                native_states=native_states,
            )
            control_metrics = milestone._metrics(control_ledger)
            if control_metrics != controls[period]["metrics"]:
                raise ValueError(
                    f"V31 control event replay drift in {period}"
                )
            control_states[period] = states

        models, model_diagnostics = _fit_models(
            windows=windows,
            control_states=control_states,
        )

        results: list[dict[str, Any]] = []
        audits: list[V31Decision] = []
        for heldout, (ledgers, contexts) in windows.items():
            trainers = tuple(period for period in windows if period != heldout)
            if len(trainers) != 2:
                raise ValueError("V31 requires exactly two external periods")
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
                <= int(
                    controls[heldout]["metrics"]["max_losing_streak"]
                )
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
    total_switches = sum(int(row["action_switch_count"]) for row in results)
    candidate_count = int(full_gate and total_switches > 0)

    return {
        "identity": IDENTITY,
        "evaluation": "GLOBAL_EVENT_TIME_PORTFOLIO_CROSS_MARKET_TRIGGER_STATE",
        "policy": POLICY,
        "source_trigger_state_run_id": SOURCE_TRIGGER_STATE_RUN_ID,
        "source_trigger_state_identity": v29.IDENTITY,
        "v30_action_policy_preserved": True,
        "v30_action_reachability_preserved": True,
        "single_decision_per_trade": True,
        "sequential_reevaluation_enabled": False,
        "globally_chronological_entry_trigger_replay": True,
        "same_timestamp_pre_batch_state": True,
        "same_timestamp_peer_action_visible": False,
        "same_timestamp_peer_outcome_visible": False,
        "closed_outcome_requires_exit_strictly_before_trigger": True,
        "active_trade_outcomes_visible": False,
        "event_portfolio_features": list(EVENT_PORTFOLIO_FEATURES),
        "event_portfolio_feature_dimension": (
            EVENT_PORTFOLIO_FEATURE_DIMENSION
        ),
        "expected_full_feature_dimension": EXPECTED_FEATURE_DIMENSION,
        "l2_prior_strength_effective_trades": str(L2_PRIOR_STRENGTH),
        "native_m1_trigger_state_reused_from_v29": True,
        "new_market_data_opened": False,
        "model_diagnostics": model_diagnostics,
        "results": results,
        "total_action_switches": total_switches,
        "total_switches_to_original": sum(
            int(row["switch_to_original_count"]) for row in results
        ),
        "total_switches_to_later_trigger": sum(
            int(row["switch_to_later_trigger_count"]) for row in results
        ),
        "candidate_count": candidate_count,
        "all_entries_preserved": True,
        "density_retention": "1",
        "same_entrant_identities": True,
        "fixed_target_r": "2.00",
        "original_stop_geometry_preserved_at_entry": True,
        "new_protection_geometry_created": False,
        "max3_preserved": True,
        "max3_slot_recycling": False,
        "chosen_prior_outcomes_recompute_future_state": True,
        "current_outcome_visible_to_decision": False,
        "heldout_counterfactual_visible_to_decision": False,
        "future_after_trigger_visible_to_decision": False,
        "activation_bar_ohlc_visible_to_decision": False,
        "symbol_session_side_time_identity_features_used": False,
        "full_source_identity_proof_required_before_freeze": True,
        "historical_fresh_oos_available": False,
        "2018_2020_status": "CONSUMED_NOT_FRESH",
        "automatic_policy_promotion": False,
        "trader_certified": False,
        "live_authorized": False,
        "real_capital_authorized": False,
        "next_phase": (
            "FULL_SOURCE_IDENTITY_PROOF_V31_SURVIVOR"
            if candidate_count
            else "V31_FALSIFIED_SEQUENTIAL_CONTROL_REQUIRED"
        ),
    }, tuple(audits)


def write_report(
    report: dict[str, Any],
    audits: tuple[V31Decision, ...],
    output: Path,
) -> None:
    output.mkdir(parents=True, exist_ok=True)
    stem = "capitalizer-event-time-portfolio-trigger-state-v31"
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


def main() -> None:
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


if __name__ == "__main__":
    main()

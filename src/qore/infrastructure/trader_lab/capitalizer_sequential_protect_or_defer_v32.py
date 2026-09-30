"""Sequential protect-or-defer controller for Capitalizer V32.

Every frozen entrant starts on the existing ORIGINAL protection path. At each
causally reached protection family, V32 may commit to an existing mode whose
first intervention is exactly that family, or DEFER without intervention and
re-evaluate at the next family.

V32 reuses V31's 95-dimension causal trigger representation. It adds no market
feature, no protection geometry, no future-labelled DEFER target, and no
identity/date/clock feature.
"""

from __future__ import annotations

import argparse
import json
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

IDENTITY = "QORE_CAPITALIZER_SEQUENTIAL_PROTECT_OR_DEFER_V32"
POLICY = "ROBUST_STAGEWISE_CURRENT_FAMILY_OR_DEFER"
REFERENCE_MODE = milestone.ProtectionMode.ORIGINAL.value
L2_PRIOR_STRENGTH = v25.L2_PRIOR_STRENGTH
SOURCE_TRIGGER_STATE_RUN_ID = 36283499014
EXPECTED_FEATURE_DIMENSION = v31.EXPECTED_FEATURE_DIMENSION

FAMILY_ORDER = v30.FAMILY_ORDER
FAMILY_RANK = v30.FAMILY_RANK
CURRENT_FAMILY_ACTIONS: dict[str, tuple[str, ...]] = {
    family: tuple(v29.FAMILIES[family][1])
    for family in FAMILY_ORDER
}

FamilyModels = dict[
    str,
    dict[str, dict[str, tuple[v25.RidgeModel, v25.RidgeModel]]],
]


@dataclass(frozen=True, slots=True)
class ReferenceTriggerState:
    period: str
    symbol: str
    session: str
    operating_date: str
    entry_at: str
    surface_hint_mode: str
    family: str
    trigger_at: str
    base_multiplier: str
    completed_m1_bars: int
    vector: tuple[float, ...]
    reference_mode: str = REFERENCE_MODE
    current_outcome_visible: bool = False
    active_peer_outcome_visible: bool = False
    same_timestamp_peer_outcome_visible: bool = False
    activation_bar_ohlc_visible: bool = False
    identity_features_used: bool = False


@dataclass(frozen=True, slots=True)
class V32TriggerDecision:
    period: str
    policy: str
    symbol: str
    session: str
    operating_date: str
    entry_at: str
    family: str
    trigger_at: str
    surface_hint_mode: str
    action_selected: str | None
    deferred: bool
    base_multiplier: str
    completed_m1_bars: int
    robust_total_delta: str | None
    trainer_a_period: str
    trainer_b_period: str
    trainer_a_total_delta: str | None
    trainer_b_total_delta: str | None
    trainer_a_downside_delta: str | None
    trainer_b_downside_delta: str | None
    current_family_action_count: int
    portfolio_vector: tuple[float, ...]
    current_outcome_visible: bool = False
    active_peer_outcome_visible: bool = False
    same_timestamp_peer_outcome_visible: bool = False
    activation_bar_ohlc_visible: bool = False
    identity_features_used: bool = False


@dataclass(frozen=True, slots=True)
class V32TradeOutcome:
    period: str
    policy: str
    symbol: str
    session: str
    operating_date: str
    entry_at: str
    exit_at: str
    surface_hint_mode: str
    chosen_mode: str
    base_multiplier: str
    realized_scaled_r: str
    trigger_decision_count: int
    defer_count: int
    committed_family: str | None
    committed: bool
    changed_from_surface_hint: bool


def _aware(value: str) -> datetime:
    return milestone._aware(value)


def _trigger_sequence(
    *,
    period: str,
    symbol: str,
    entry_at: str,
    native_states: dict[tuple[str, str, str, str], v29.TriggerState],
) -> tuple[tuple[datetime, str, v29.TriggerState], ...]:
    result: list[tuple[datetime, str, v29.TriggerState]] = []
    for family in FAMILY_ORDER:
        state = native_states.get((period, symbol, entry_at, family))
        if state is None:
            continue
        current = _aware(state.trigger_at)
        if current <= _aware(entry_at):
            raise ValueError("V32 trigger must follow entry")
        if result and current < result[-1][0]:
            raise ValueError("V32 trigger families reverse chronology")
        if result and current == result[-1][0]:
            # One completed M1 bar can cross multiple milestones. Serial
            # decisions at the same activation timestamp would violate the
            # immutable pre-batch law and invent evidence between milestones.
            # Keep exactly the highest causally reached family at that time.
            result[-1] = (current, family, state)
            continue
        result.append((current, family, state))
    return tuple(result)


def _next_event_time(
    *,
    ordered: tuple[milestone.SimulatedTrade, ...],
    pointer: int,
    pending: dict[tuple[str, str], tuple[datetime, str, int]],
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
    return None if not candidates else min(candidates)


def _original_entry_batch(
    *,
    period: str,
    rows: tuple[milestone.SimulatedTrade, ...],
    modes: dict[str, dict[tuple[str, str], milestone.SimulatedTrade]],
    contexts: dict[tuple[str, str], Any],
    contextual_model: dict[str, Any],
    snapshot_projections: tuple[milestone.SimulatedTrade, ...],
    snapshot_records: tuple[memory.MemoryRecord, ...],
    native_states: dict[tuple[str, str, str, str], v29.TriggerState],
) -> tuple[
    dict[tuple[str, str], v10.Pretrade],
    dict[tuple[str, str], milestone.SimulatedTrade],
    dict[tuple[str, str], memory.MemoryRecord],
    dict[
        tuple[str, str],
        tuple[tuple[datetime, str, v29.TriggerState], ...],
    ],
    dict[tuple[str, str], tuple[datetime, str, int]],
]:
    pretrades: dict[tuple[str, str], v10.Pretrade] = {}
    projections: dict[
        tuple[str, str], milestone.SimulatedTrade
    ] = {}
    records: dict[tuple[str, str], memory.MemoryRecord] = {}
    sequences: dict[
        tuple[str, str],
        tuple[tuple[datetime, str, v29.TriggerState], ...],
    ] = {}
    pending: dict[
        tuple[str, str], tuple[datetime, str, int]
    ] = {}

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
        original = modes[REFERENCE_MODE][key]
        pretrades[key] = pretrade
        projections[key] = v31._scaled_trade(
            original,
            multiplier=pretrade.base_multiplier,
        )
        records[key] = v31._record(
            pretrade=pretrade,
            selected=original,
        )
        sequence = _trigger_sequence(
            period=period,
            symbol=trade.symbol,
            entry_at=trade.entry_at,
            native_states=native_states,
        )
        sequences[key] = sequence
        if sequence:
            trigger_at, family, _state = sequence[0]
            pending[key] = (trigger_at, family, 0)

    return pretrades, projections, records, sequences, pending


def _reference_event_replay(
    *,
    period: str,
    ledgers: dict[str, tuple[milestone.SimulatedTrade, ...]],
    contexts: dict[tuple[str, str], Any],
    contextual_model: dict[str, Any],
    native_states: dict[tuple[str, str, str, str], v29.TriggerState],
) -> tuple[
    dict[tuple[str, str, str], ReferenceTriggerState],
    tuple[milestone.SimulatedTrade, ...],
]:
    modes = v29._by_mode(ledgers)
    ordered = tuple(
        sorted(
            ledgers[REFERENCE_MODE],
            key=lambda row: (_aware(row.entry_at), row.symbol),
        )
    )
    pointer = 0
    projections: dict[
        tuple[str, str], milestone.SimulatedTrade
    ] = {}
    records: dict[tuple[str, str], memory.MemoryRecord] = {}
    pretrades: dict[tuple[str, str], v10.Pretrade] = {}
    sequences: dict[
        tuple[str, str],
        tuple[tuple[datetime, str, v29.TriggerState], ...],
    ] = {}
    pending: dict[
        tuple[str, str], tuple[datetime, str, int]
    ] = {}
    states: dict[tuple[str, str, str], ReferenceTriggerState] = {}

    while pointer < len(ordered) or pending:
        now = _next_event_time(
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
                    for key, (trigger_at, _family, _index)
                    in pending.items()
                    if trigger_at == now
                ),
                key=lambda key: (key[1], key[0]),
            )
        )
        next_pending: dict[
            tuple[str, str], tuple[datetime, str, int]
        ] = {}
        for key in trigger_keys:
            trigger_at, family, index = pending[key]
            native = sequences[key][index][2]
            pretrade = pretrades[key]
            trade = modes[REFERENCE_MODE][key]
            portfolio = v31._portfolio_vector(
                current_trade=trade,
                observed_at=trigger_at,
                projections=snapshot_projections,
            )
            vector = v31._full_trigger_vector(
                pretrade=pretrade,
                trade=trade,
                trigger_at=native.trigger_at,
                native_state=native,
                portfolio=portfolio,
            )
            states[(trade.symbol, trade.entry_at, family)] = (
                ReferenceTriggerState(
                    period=period,
                    symbol=trade.symbol,
                    session=trade.session,
                    operating_date=trade.operating_date,
                    entry_at=trade.entry_at,
                    surface_hint_mode=pretrade.mode,
                    family=family,
                    trigger_at=native.trigger_at,
                    base_multiplier=str(pretrade.base_multiplier),
                    completed_m1_bars=native.completed_m1_bars,
                    vector=vector,
                )
            )
            next_index = index + 1
            if next_index < len(sequences[key]):
                nxt = sequences[key][next_index]
                next_pending[key] = (nxt[0], nxt[1], next_index)

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
                new_sequences,
                new_pending,
            ) = _original_entry_batch(
                period=period,
                rows=tuple(entry_rows),
                modes=modes,
                contexts=contexts,
                contextual_model=contextual_model,
                snapshot_projections=snapshot_projections,
                snapshot_records=snapshot_records,
                native_states=native_states,
            )
        else:
            new_pretrades = {}
            new_projections = {}
            new_records = {}
            new_sequences = {}
            new_pending = {}

        for key in trigger_keys:
            pending.pop(key)
        pending.update(next_pending)
        pretrades.update(new_pretrades)
        projections.update(new_projections)
        records.update(new_records)
        sequences.update(new_sequences)
        pending.update(new_pending)

    ledger = v31._snapshot_rows(projections)
    if len(ledger) != len(ordered):
        raise ValueError("V32 reference replay lost entrants")
    return states, ledger


def _training_examples(
    *,
    family: str,
    action: str,
    states: dict[tuple[str, str, str], ReferenceTriggerState],
    ledgers: dict[str, tuple[milestone.SimulatedTrade, ...]],
) -> tuple[
    tuple[v25.TrainingExample, ...],
    tuple[v25.TrainingExample, ...],
]:
    if action not in CURRENT_FAMILY_ACTIONS[family]:
        raise ValueError("V32 action outside current trigger family")
    modes = v29._by_mode(ledgers)
    total_examples: list[v25.TrainingExample] = []
    downside_examples: list[v25.TrainingExample] = []

    for (symbol, entry_at, state_family), state in states.items():
        if state_family != family:
            continue
        key = (symbol, entry_at)
        reference_r = Decimal(modes[REFERENCE_MODE][key].realized_gross_r)
        action_r = Decimal(modes[action][key].realized_gross_r)
        total_delta = action_r - reference_r
        downside_delta = min(action_r, Decimal("0")) - min(
            reference_r,
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
    reference_states: dict[
        str, dict[tuple[str, str, str], ReferenceTriggerState]
    ],
) -> tuple[FamilyModels, dict[str, Any]]:
    models: FamilyModels = {}
    diagnostics: dict[str, Any] = {}

    for period, (ledgers, _contexts) in windows.items():
        period_models: dict[
            str, dict[str, tuple[v25.RidgeModel, v25.RidgeModel]]
        ] = {}
        period_diagnostics: dict[str, Any] = {}
        for family in FAMILY_ORDER:
            action_models: dict[
                str, tuple[v25.RidgeModel, v25.RidgeModel]
            ] = {}
            action_diagnostics: dict[str, Any] = {}
            for action in CURRENT_FAMILY_ACTIONS[family]:
                total_examples, downside_examples = _training_examples(
                    family=family,
                    action=action,
                    states=reference_states[period],
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


def _choose_current_action(
    *,
    features: tuple[float, ...],
    actions: tuple[str, ...],
    model_a: dict[str, tuple[v25.RidgeModel, v25.RidgeModel]],
    model_b: dict[str, tuple[v25.RidgeModel, v25.RidgeModel]],
) -> tuple[
    str | None,
    float | None,
    tuple[float, float, float, float] | None,
]:
    return v30._choose_action(
        features=features,
        surface_mode=REFERENCE_MODE,
        actions=actions,
        model_a=model_a,
        model_b=model_b,
    )


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
) -> tuple[
    dict[str, Any],
    tuple[V32TradeOutcome, ...],
    tuple[V32TriggerDecision, ...],
]:
    modes = v29._by_mode(ledgers)
    ordered = tuple(
        sorted(
            ledgers[REFERENCE_MODE],
            key=lambda row: (_aware(row.entry_at), row.symbol),
        )
    )
    pointer = 0
    projections: dict[
        tuple[str, str], milestone.SimulatedTrade
    ] = {}
    records: dict[tuple[str, str], memory.MemoryRecord] = {}
    pretrades: dict[tuple[str, str], v10.Pretrade] = {}
    sequences: dict[
        tuple[str, str],
        tuple[tuple[datetime, str, v29.TriggerState], ...],
    ] = {}
    pending: dict[
        tuple[str, str], tuple[datetime, str, int]
    ] = {}
    audit: dict[tuple[str, str], dict[str, Any]] = {}
    trigger_audits: list[V32TriggerDecision] = []

    while pointer < len(ordered) or pending:
        now = _next_event_time(
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
                    for key, (trigger_at, _family, _index)
                    in pending.items()
                    if trigger_at == now
                ),
                key=lambda key: (key[1], key[0]),
            )
        )
        trigger_results: dict[
            tuple[str, str],
            tuple[
                str | None,
                float | None,
                tuple[float, float, float, float] | None,
                tuple[float, ...],
                v29.TriggerState,
                str,
                int,
            ],
        ] = {}

        for key in trigger_keys:
            trigger_at, family, index = pending[key]
            native = sequences[key][index][2]
            pretrade = pretrades[key]
            trade = modes[REFERENCE_MODE][key]
            portfolio = v31._portfolio_vector(
                current_trade=trade,
                observed_at=trigger_at,
                projections=snapshot_projections,
            )
            features = v31._full_trigger_vector(
                pretrade=pretrade,
                trade=trade,
                trigger_at=native.trigger_at,
                native_state=native,
                portfolio=portfolio,
            )
            actions = CURRENT_FAMILY_ACTIONS[family]
            action, score, predictions = _choose_current_action(
                features=features,
                actions=actions,
                model_a=model_a[family],
                model_b=model_b[family],
            )
            trigger_results[key] = (
                action,
                score,
                predictions,
                portfolio,
                native,
                family,
                index,
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
                new_sequences,
                new_pending,
            ) = _original_entry_batch(
                period=period,
                rows=tuple(entry_rows),
                modes=modes,
                contexts=contexts,
                contextual_model=contextual_model,
                snapshot_projections=snapshot_projections,
                snapshot_records=snapshot_records,
                native_states=native_states,
            )
        else:
            new_pretrades = {}
            new_projections = {}
            new_records = {}
            new_sequences = {}
            new_pending = {}

        deferred_pending: dict[
            tuple[str, str], tuple[datetime, str, int]
        ] = {}
        for key in trigger_keys:
            trigger_at, _pending_family, _pending_index = pending.pop(key)
            (
                action,
                score,
                predictions,
                portfolio,
                native,
                family,
                index,
            ) = trigger_results[key]
            pretrade = pretrades[key]
            row = audit[key]
            row["trigger_decision_count"] += 1

            if predictions is None:
                total_a = total_b = downside_a = downside_b = None
            else:
                total_a, total_b, downside_a, downside_b = predictions

            deferred = action is None
            trigger_audits.append(
                V32TriggerDecision(
                    period=period,
                    policy=POLICY,
                    symbol=key[0],
                    session=modes[REFERENCE_MODE][key].session,
                    operating_date=(
                        modes[REFERENCE_MODE][key].operating_date
                    ),
                    entry_at=key[1],
                    family=family,
                    trigger_at=native.trigger_at,
                    surface_hint_mode=pretrade.mode,
                    action_selected=action,
                    deferred=deferred,
                    base_multiplier=str(pretrade.base_multiplier),
                    completed_m1_bars=native.completed_m1_bars,
                    robust_total_delta=(
                        None if score is None else str(score)
                    ),
                    trainer_a_period=trainer_a,
                    trainer_b_period=trainer_b,
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
                    current_family_action_count=len(
                        CURRENT_FAMILY_ACTIONS[family]
                    ),
                    portfolio_vector=portfolio,
                )
            )

            if action is not None:
                selected = modes[action][key]
                if _aware(selected.exit_at) < trigger_at:
                    raise ValueError(
                        "V32 committed mode exits before its trigger"
                    )
                projections[key] = v31._scaled_trade(
                    selected,
                    multiplier=pretrade.base_multiplier,
                )
                records[key] = v31._record(
                    pretrade=pretrade,
                    selected=selected,
                )
                row["chosen_mode"] = action
                row["committed_family"] = family
            else:
                row["defer_count"] += 1
                next_index = index + 1
                if next_index < len(sequences[key]):
                    nxt = sequences[key][next_index]
                    deferred_pending[key] = (
                        nxt[0],
                        nxt[1],
                        next_index,
                    )

        for key, pretrade in new_pretrades.items():
            trade = modes[REFERENCE_MODE][key]
            audit[key] = {
                "surface_hint_mode": pretrade.mode,
                "chosen_mode": REFERENCE_MODE,
                "base_multiplier": str(pretrade.base_multiplier),
                "trigger_decision_count": 0,
                "defer_count": 0,
                "committed_family": None,
            }

        pretrades.update(new_pretrades)
        projections.update(new_projections)
        records.update(new_records)
        sequences.update(new_sequences)
        pending.update(deferred_pending)
        pending.update(new_pending)

    ledger = v31._snapshot_rows(projections)
    if len(ledger) != len(ordered):
        raise ValueError("V32 held-out replay lost entrants")

    outcomes: list[V32TradeOutcome] = []
    action_counts: Counter[str] = Counter()
    commitments = 0
    changed_from_surface = 0
    reevaluated = 0
    defers = 0

    for trade in ordered:
        key = (trade.symbol, trade.entry_at)
        row = audit[key]
        selected = projections[key]
        chosen_mode = str(row["chosen_mode"])
        committed = chosen_mode != REFERENCE_MODE
        commitments += int(committed)
        changed = chosen_mode != row["surface_hint_mode"]
        changed_from_surface += int(changed)
        reevaluated += int(row["trigger_decision_count"] > 1)
        defers += int(row["defer_count"])
        action_counts[chosen_mode] += 1
        outcomes.append(
            V32TradeOutcome(
                period=period,
                policy=POLICY,
                symbol=trade.symbol,
                session=trade.session,
                operating_date=trade.operating_date,
                entry_at=trade.entry_at,
                exit_at=selected.exit_at,
                surface_hint_mode=str(row["surface_hint_mode"]),
                chosen_mode=chosen_mode,
                base_multiplier=str(row["base_multiplier"]),
                realized_scaled_r=selected.realized_gross_r,
                trigger_decision_count=int(
                    row["trigger_decision_count"]
                ),
                defer_count=int(row["defer_count"]),
                committed_family=row["committed_family"],
                committed=committed,
                changed_from_surface_hint=changed,
            )
        )

    return {
        "period": period,
        "policy": POLICY,
        "trades": len(ledger),
        "density_retention": "1",
        "metrics": milestone._metrics(ledger),
        "protection_commitment_count": commitments,
        "changed_from_surface_hint_count": changed_from_surface,
        "sequential_reevaluation_trade_count": reevaluated,
        "defer_decision_count": defers,
        "action_counts": dict(sorted(action_counts.items())),
    }, tuple(outcomes), tuple(trigger_audits)


def build_report(
    development_root: Path,
    validation_root: Path,
    reserved_root: Path,
    development_validation_context_root: Path,
    reserved_context_root: Path,
    trigger_state_root: Path,
) -> tuple[
    dict[str, Any],
    tuple[V32TradeOutcome, ...],
    tuple[V32TriggerDecision, ...],
]:
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
        reference_states: dict[
            str, dict[tuple[str, str, str], ReferenceTriggerState]
        ] = {}
        reference_metrics: dict[str, Any] = {}
        for period, (ledgers, contexts) in windows.items():
            states, reference_ledger = _reference_event_replay(
                period=period,
                ledgers=ledgers,
                contexts=contexts,
                contextual_model=contextual_model,
                native_states=native_states,
            )
            reference_states[period] = states
            reference_metrics[period] = milestone._metrics(
                reference_ledger
            )

        models, model_diagnostics = _fit_models(
            windows=windows,
            reference_states=reference_states,
        )

        results: list[dict[str, Any]] = []
        outcomes: list[V32TradeOutcome] = []
        trigger_audits: list[V32TriggerDecision] = []
        for heldout, (ledgers, contexts) in windows.items():
            trainers = tuple(period for period in windows if period != heldout)
            if len(trainers) != 2:
                raise ValueError("V32 requires exactly two external periods")
            trainer_a, trainer_b = trainers
            current, current_outcomes, current_triggers = _simulate_period(
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
            outcomes.extend(current_outcomes)
            trigger_audits.extend(current_triggers)
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
    total_commitments = sum(
        int(row["protection_commitment_count"]) for row in results
    )
    candidate_count = int(full_gate and total_commitments > 0)

    return {
        "identity": IDENTITY,
        "evaluation": "SEQUENTIAL_CURRENT_FAMILY_COMMIT_OR_CAUSAL_DEFER",
        "policy": POLICY,
        "reference_protection_mode": REFERENCE_MODE,
        "source_trigger_state_run_id": SOURCE_TRIGGER_STATE_RUN_ID,
        "source_trigger_state_identity": v29.IDENTITY,
        "v31_feature_representation_preserved": True,
        "expected_full_feature_dimension": EXPECTED_FEATURE_DIMENSION,
        "current_family_actions": {
            family: list(actions)
            for family, actions in CURRENT_FAMILY_ACTIONS.items()
        },
        "sequential_reevaluation_enabled": True,
        "future_family_action_selected_early": False,
        "defer_is_implicit_original_continuation": True,
        "future_labelled_defer_model_used": False,
        "bellman_target_used": False,
        "commit_freezes_existing_mode": True,
        "globally_chronological_entry_trigger_replay": True,
        "same_timestamp_pre_batch_state": True,
        "same_timestamp_peer_action_visible": False,
        "same_timestamp_peer_outcome_visible": False,
        "closed_outcome_requires_exit_strictly_before_trigger": True,
        "active_trade_outcomes_visible": False,
        "l2_prior_strength_effective_trades": str(L2_PRIOR_STRENGTH),
        "native_m1_trigger_state_reused_from_v29": True,
        "new_market_data_opened": False,
        "reference_metrics": reference_metrics,
        "model_diagnostics": model_diagnostics,
        "results": results,
        "total_protection_commitments": total_commitments,
        "total_defer_decisions": sum(
            int(row["defer_decision_count"]) for row in results
        ),
        "total_sequential_reevaluation_trades": sum(
            int(row["sequential_reevaluation_trade_count"])
            for row in results
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
            "FULL_SOURCE_IDENTITY_PROOF_V32_SURVIVOR"
            if candidate_count
            else "V32_FALSIFIED_CROSS_ERA_INVARIANCE_REQUIRED"
        ),
    }, tuple(outcomes), tuple(trigger_audits)


def write_report(
    report: dict[str, Any],
    outcomes: tuple[V32TradeOutcome, ...],
    trigger_audits: tuple[V32TriggerDecision, ...],
    output: Path,
) -> None:
    output.mkdir(parents=True, exist_ok=True)
    stem = "capitalizer-sequential-protect-or-defer-v32"
    (output / f"{stem}.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    with (output / f"{stem}-trade-outcomes.jsonl").open(
        "w",
        encoding="utf-8",
    ) as handle:
        for outcome in outcomes:
            handle.write(
                json.dumps(asdict(outcome), sort_keys=True) + "\n"
            )
    with (output / f"{stem}-trigger-decisions.jsonl").open(
        "w",
        encoding="utf-8",
    ) as handle:
        for decision in trigger_audits:
            handle.write(
                json.dumps(asdict(decision), sort_keys=True) + "\n"
            )


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

    report, outcomes, trigger_audits = build_report(
        args.development_root,
        args.validation_root,
        args.reserved_root,
        args.development_validation_context_root,
        args.reserved_context_root,
        args.trigger_state_root,
    )
    write_report(report, outcomes, trigger_audits, args.output)
    print(json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    main()

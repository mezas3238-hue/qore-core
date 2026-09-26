"""Cross-period causal hypothesis survival model for Capitalizer V21.

V20 proved that causal lifecycle state contains information, but fixed terminal
thresholds do not generalize across the three consumed windows. V21 keeps entry,
stop, true-2R target, Surface sizing and MAX3 unchanged and asks a narrower
question: while a trade has not yet departed +0.25R, do two independent external
period models agree that the current structural state has low probability of
surviving to that departure?

The survival label is training-only. Held-out inference sees only causal,
fully-closed M1 observations strictly before the selected Surface exit. Symbol,
session, side, operating date and clock time are excluded from signatures.
Fresh 2018-2020 remains sealed.
"""

from __future__ import annotations

import argparse
import json
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
    capitalizer_factor_journey_probe_ranker_v11 as v11,
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
from qore.infrastructure.trader_lab import (
    capitalizer_structural_intratrade_invalidation_v19 as v19,
)
from qore.infrastructure.trader_lab.capitalizer_cibo_m1_reader_v1 import (
    CapitalizerM1Bar,
    iter_cibo_m1,
)

IDENTITY = "QORE_CAPITALIZER_HYPOTHESIS_SURVIVAL_MODEL_V21"
DEPARTURE_R = Decimal("0.25")
CANONICAL_TRACK = "HSM_BASE"
BETA_ALPHA = 1
BETA_BETA = 1
PERSISTENCE_REQUIRED = 2

# name -> (allowed lifecycle phases, maximum survival, minimum support)
POLICY_SPECS: dict[str, tuple[frozenset[str], Decimal, int]] = {
    "INVALIDATING_SURV20_N30_P2": (
        frozenset({v20.Phase.INVALIDATING.value}),
        Decimal("0.20"),
        30,
    ),
    "INVALIDATING_SURV25_N30_P2": (
        frozenset({v20.Phase.INVALIDATING.value}),
        Decimal("0.25"),
        30,
    ),
    "INVALIDATING_SURV30_N30_P2": (
        frozenset({v20.Phase.INVALIDATING.value}),
        Decimal("0.30"),
        30,
    ),
    "WEAK_OR_INVALID_SURV20_N50_P2": (
        frozenset(
            {
                v20.Phase.WEAKENING.value,
                v20.Phase.INVALIDATING.value,
            }
        ),
        Decimal("0.20"),
        50,
    ),
    "WEAK_OR_INVALID_SURV25_N50_P2": (
        frozenset(
            {
                v20.Phase.WEAKENING.value,
                v20.Phase.INVALIDATING.value,
            }
        ),
        Decimal("0.25"),
        50,
    ),
    "WEAK_OR_INVALID_SURV30_N50_P2": (
        frozenset(
            {
                v20.Phase.WEAKENING.value,
                v20.Phase.INVALIDATING.value,
            }
        ),
        Decimal("0.30"),
        50,
    ),
}
POLICIES = ("SURFACE_CONTROL", *POLICY_SPECS)


@dataclass(frozen=True, slots=True)
class Observation:
    period: str
    symbol: str
    session: str
    operating_date: str
    side: str
    entry_at: str
    observed_at: str
    phase: str
    elapsed_full_bars: int
    max_favorable_r: str
    close_r: str
    adverse_close_count: int
    invalidating_age: int
    adverse_displacement_observed: bool
    displacement_midpoint_reclaimed: bool
    adverse_extreme_extended: bool
    recovered_since_deterioration: bool
    current_outcome_visible: bool = False
    future_bars_visible: bool = False
    original_exit_bar_used: bool = False


@dataclass(frozen=True, slots=True)
class TrainingLabel:
    period: str
    symbol: str
    entry_at: str
    departure_at: str | None
    departure_r: str = str(DEPARTURE_R)
    training_only: bool = True
    terminal_pnl_used: bool = False
    terminal_reason_used: bool = False


@dataclass(frozen=True, slots=True)
class SurvivalDecision:
    period: str
    policy: str
    symbol: str
    entry_at: str
    observed_at: str
    phase: str
    signature_level: str | None
    signature: str | None
    trainer_a_period: str
    trainer_b_period: str
    trainer_a_support: int
    trainer_b_support: int
    trainer_a_survival: str | None
    trainer_b_survival: str | None
    persistence: int
    structural_gate: bool
    support_gate: bool
    survival_gate: bool
    exit_applied: bool
    current_outcome_visible: bool = False
    future_bars_visible: bool = False
    original_exit_bar_used: bool = False
    unchosen_counterfactual_visible: bool = False
    heldout_training_label_visible: bool = False


@dataclass(slots=True)
class _ObservationState:
    period: str
    trade: milestone.SimulatedTrade
    elapsed: int = 0
    max_favorable_r: Decimal = Decimal("0")
    departed: bool = False
    departure_at: str | None = None
    history: list[CapitalizerM1Bar] | None = None
    track: v20._Track | None = None
    recovered_since_deterioration: bool = False

    def __post_init__(self) -> None:
        if self.history is None:
            self.history = []
        if self.track is None:
            self.track = v20._Track()


Model = dict[str, dict[str, tuple[int, int]]]


def _elapsed_bin(value: int) -> str:
    if value <= 2:
        return "E_1_2"
    if value <= 4:
        return "E_3_4"
    if value <= 7:
        return "E_5_7"
    if value <= 12:
        return "E_8_12"
    return "E_13_PLUS"


def _mfe_bin(value: Decimal) -> str:
    if value < Decimal("0.05"):
        return "MFE_000_005"
    if value < Decimal("0.10"):
        return "MFE_005_010"
    if value < Decimal("0.15"):
        return "MFE_010_015"
    if value < Decimal("0.20"):
        return "MFE_015_020"
    return "MFE_020_025"


def _close_bin(value: Decimal) -> str:
    if value <= Decimal("-0.75"):
        return "C_LE_N075"
    if value <= Decimal("-0.50"):
        return "C_N075_N050"
    if value <= Decimal("-0.30"):
        return "C_N050_N030"
    if value <= Decimal("-0.15"):
        return "C_N030_N015"
    if value <= Decimal("-0.05"):
        return "C_N015_N005"
    return "C_GT_N005"


def _adverse_bin(value: int) -> str:
    if value <= 0:
        return "A0"
    if value == 1:
        return "A1"
    if value == 2:
        return "A2"
    return "A3_PLUS"


def _invalidating_age_bin(value: int) -> str:
    if value <= 0:
        return "I0"
    if value == 1:
        return "I1"
    if value == 2:
        return "I2"
    return "I3_PLUS"


def _entry_context_family(ctx: Any) -> str:
    if str(ctx.destination_state) == "LT_1R":
        return "DEST_LT1R"
    if (
        str(ctx.h1_body_alignment) == "OPPOSED"
        and str(ctx.m15_slope_alignment) == "OPPOSED"
    ):
        return "DUAL_OPPOSED"
    if str(ctx.volatility_state) == "EXPANSION":
        return "VOL_EXPANSION"
    return "OTHER"


def _flags(row: Observation) -> str:
    return "".join(
        (
            "D1" if row.adverse_displacement_observed else "D0",
            "R1" if row.displacement_midpoint_reclaimed else "R0",
            "X1" if row.adverse_extreme_extended else "X0",
            "C1" if row.recovered_since_deterioration else "C0",
        )
    )


def _signature_levels(
    row: Observation,
    *,
    entry_context_family: str,
) -> tuple[tuple[str, str], ...]:
    phase = row.phase
    flags = _flags(row)
    age = _invalidating_age_bin(row.invalidating_age)
    elapsed = _elapsed_bin(row.elapsed_full_bars)
    mfe = _mfe_bin(Decimal(row.max_favorable_r))
    close = _close_bin(Decimal(row.close_r))
    adverse = _adverse_bin(row.adverse_close_count)
    dynamic = "|".join((elapsed, mfe, close, adverse))
    return (
        (
            "L0",
            "|".join(
                (
                    phase,
                    flags,
                    age,
                    dynamic,
                    entry_context_family,
                )
            ),
        ),
        ("L1", "|".join((phase, flags, age, dynamic))),
        ("L2", "|".join((phase, flags, age))),
        ("L3", "|".join((phase, dynamic))),
        ("L4", phase),
    )


def _process_observation_bar(
    state: _ObservationState,
    bar: CapitalizerM1Bar,
) -> Observation | None:
    if bar.opened_at < v18._aware(state.trade.entry_at):
        return None
    if bar.closed_at >= v18._aware(state.trade.exit_at):
        return None
    if state.departed:
        return None

    state.elapsed += 1
    state.max_favorable_r = max(
        state.max_favorable_r,
        v18._favorable_r(bar, state.trade),
    )
    if state.max_favorable_r >= DEPARTURE_R:
        state.departed = True
        state.departure_at = bar.closed_at.isoformat()
        return None

    assert state.track is not None
    assert state.history is not None
    track = state.track
    close_r = v18._close_r(bar, state.trade)
    midpoint_reclaimed = False
    displacement_seen_before = track.midpoint is not None
    extension_seen_before = track.extension_seen

    minimum_bars, weakening_r, body_r, displacement_close_r, _, _ = (
        v20.STATE_SPECS[CANONICAL_TRACK]
    )

    if track.phase is v20.Phase.RECOVERED:
        track.phase = v20.Phase.ALIVE
        v20._reset_track(track)

    if track.phase in {v20.Phase.WEAKENING, v20.Phase.INVALIDATING} and v20._reclaim(
        bar=bar,
        track=track,
        trade=state.trade,
        close_r=close_r,
    ):
        midpoint_reclaimed = True
        track.phase = v20.Phase.RECOVERED
        state.recovered_since_deterioration = True
        v20._reset_track(track)
    else:
        if close_r <= -weakening_r:
            track.adverse_closes += 1
        else:
            track.adverse_closes = 0

        if (
            track.phase is v20.Phase.ALIVE
            and state.elapsed >= minimum_bars
            and track.adverse_closes >= v20.WEAKENING_CLOSES
        ):
            track.phase = v20.Phase.WEAKENING
            state.recovered_since_deterioration = False

        displacement_this_bar = False
        if (
            track.phase in {v20.Phase.ALIVE, v20.Phase.WEAKENING}
            and state.elapsed >= minimum_bars
            and len(state.history) >= 2
        ):
            prior = (state.history[-2], state.history[-1])
            if v19._displacement_qualifies(
                bar=bar,
                prior=prior,
                trade=state.trade,
                minimum_body_r=body_r,
                minimum_adverse_close_r=displacement_close_r,
            ):
                track.midpoint = v19._midpoint(bar)
                track.adverse_extreme = v19._adverse_extreme(
                    bar,
                    state.trade,
                )
                track.acceptance_count = 0
                track.extension_seen = False
                track.invalidating_age = 0
                track.phase = v20.Phase.INVALIDATING
                state.recovered_since_deterioration = False
                displacement_this_bar = True

        if track.phase is v20.Phase.INVALIDATING and not displacement_this_bar:
            track.invalidating_age += 1
            if v20._reclaim(
                bar=bar,
                track=track,
                trade=state.trade,
                close_r=close_r,
            ):
                midpoint_reclaimed = True
                track.phase = v20.Phase.RECOVERED
                state.recovered_since_deterioration = True
                v20._reset_track(track)
            else:
                track.acceptance_count += 1
                if track.adverse_extreme is not None:
                    pending = v19._Pending(
                        midpoint=(
                            track.midpoint
                            if track.midpoint is not None
                            else Decimal(state.trade.entry_price)
                        ),
                        adverse_extreme=track.adverse_extreme,
                    )
                    if v19._extends(
                        bar,
                        pending=pending,
                        trade=state.trade,
                    ):
                        track.extension_seen = True
                        track.adverse_extreme = v19._adverse_extreme(
                            bar,
                            state.trade,
                        )

    displacement_observed = (
        displacement_seen_before
        or track.midpoint is not None
        or track.phase is v20.Phase.INVALIDATING
    )
    extreme_extended = extension_seen_before or track.extension_seen

    row = Observation(
        period=state.period,
        symbol=state.trade.symbol,
        session=state.trade.session,
        operating_date=state.trade.operating_date,
        side=state.trade.side,
        entry_at=state.trade.entry_at,
        observed_at=bar.closed_at.isoformat(),
        phase=track.phase.value,
        elapsed_full_bars=state.elapsed,
        max_favorable_r=str(state.max_favorable_r),
        close_r=str(close_r),
        adverse_close_count=track.adverse_closes,
        invalidating_age=track.invalidating_age,
        adverse_displacement_observed=displacement_observed,
        displacement_midpoint_reclaimed=midpoint_reclaimed,
        adverse_extreme_extended=extreme_extended,
        recovered_since_deterioration=state.recovered_since_deterioration,
    )

    state.history.append(bar)
    if len(state.history) > 6:
        del state.history[:-6]
    return row


def _scan_symbol(
    *,
    symbol: str,
    period_rows: dict[str, tuple[milestone.SimulatedTrade, ...]],
    m1_root: Path,
) -> tuple[tuple[Observation, ...], tuple[TrainingLabel, ...]]:
    states = tuple(
        sorted(
            (
                _ObservationState(period=period, trade=trade)
                for period, rows in period_rows.items()
                for trade in rows
            ),
            key=lambda item: (
                v18._aware(item.trade.entry_at),
                item.period,
            ),
        )
    )
    if not states:
        raise ValueError("V21 has no market states")

    roots = tuple(path.parent for path in m1_root.rglob("RAW_M1_LEDGER"))
    if len(roots) != 1:
        raise ValueError(f"V21 requires one native-M1 root for {symbol}")

    first_entry = min(v18._aware(item.trade.entry_at) for item in states)
    last_exit = max(v18._aware(item.trade.exit_at) for item in states)
    active: list[_ObservationState] = []
    pointer = 0
    observations: list[Observation] = []

    for bar in iter_cibo_m1(roots[0]):
        if bar.symbol != symbol:
            raise ValueError("V21 M1 symbol drift")
        if bar.closed_at <= first_entry:
            continue
        if bar.opened_at >= last_exit:
            break

        while (
            pointer < len(states)
            and v18._aware(states[pointer].trade.entry_at) <= bar.opened_at
        ):
            active.append(states[pointer])
            pointer += 1

        next_active: list[_ObservationState] = []
        for state in active:
            if bar.opened_at >= v18._aware(state.trade.exit_at):
                continue
            row = _process_observation_bar(state, bar)
            if row is not None:
                observations.append(row)
            if (
                not state.departed
                and bar.closed_at < v18._aware(state.trade.exit_at)
            ):
                next_active.append(state)
        active = next_active

    labels = tuple(
        TrainingLabel(
            period=state.period,
            symbol=state.trade.symbol,
            entry_at=state.trade.entry_at,
            departure_at=state.departure_at,
        )
        for state in states
    )
    return tuple(observations), labels


def build_market_report(
    development_root: Path,
    validation_root: Path,
    reserved_root: Path,
    m1_root: Path,
    *,
    symbol: str,
) -> tuple[
    dict[str, Any],
    tuple[Observation, ...],
    tuple[TrainingLabel, ...],
]:
    periods = {
        v10.DEVELOPMENT_PERIOD: v18._market_original(
            development_root,
            symbol=symbol,
        ),
        "CONSUMED_VALIDATION_2022_2024": v18._market_original(
            validation_root,
            symbol=symbol,
        ),
        "CONSUMED_RESERVED_2020_2022": v18._market_original(
            reserved_root,
            symbol=symbol,
        ),
    }
    observations, labels = _scan_symbol(
        symbol=symbol,
        period_rows=periods,
        m1_root=m1_root,
    )
    return {
        "identity": IDENTITY,
        "symbol": symbol,
        "canonical_lifecycle_track": CANONICAL_TRACK,
        "source_trade_counts": {
            period: len(rows) for period, rows in periods.items()
        },
        "observation_count": len(observations),
        "label_count": len(labels),
        "departure_r": str(DEPARTURE_R),
        "terminal_pnl_used_for_labels": False,
        "terminal_reason_used_for_labels": False,
        "market_session_specific_features_used": False,
        "current_outcome_visible_to_observation": False,
        "future_bars_visible_to_observation": False,
        "original_exit_bar_excluded": True,
        "fresh_holdout_opened": False,
        "trader_certified": False,
    }, observations, labels


def write_market(
    report: dict[str, Any],
    observations: tuple[Observation, ...],
    labels: tuple[TrainingLabel, ...],
    output: Path,
) -> None:
    output.mkdir(parents=True, exist_ok=True)
    symbol = str(report["symbol"]).lower()
    stem = f"capitalizer-{symbol}-hypothesis-survival-model-v21"
    (output / f"{stem}.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    with (output / f"{stem}-observations.jsonl").open(
        "w",
        encoding="utf-8",
    ) as handle:
        for observation in observations:
            handle.write(json.dumps(asdict(observation), sort_keys=True) + "\n")
    with (output / f"{stem}-training-labels.jsonl").open(
        "w",
        encoding="utf-8",
    ) as handle:
        for label in labels:
            handle.write(json.dumps(asdict(label), sort_keys=True) + "\n")


def _load_market_evidence(
    root: Path,
) -> tuple[tuple[Observation, ...], tuple[TrainingLabel, ...]]:
    observation_paths = sorted(
        root.rglob("*-hypothesis-survival-model-v21-observations.jsonl")
    )
    label_paths = sorted(
        root.rglob("*-hypothesis-survival-model-v21-training-labels.jsonl")
    )
    if len(observation_paths) != 9 or len(label_paths) != 9:
        raise ValueError("V21 aggregate requires nine market evidence shards")

    observations: list[Observation] = []
    labels: list[TrainingLabel] = []
    for path in observation_paths:
        with path.open(encoding="utf-8") as handle:
            for line in handle:
                if line.strip():
                    observations.append(Observation(**json.loads(line)))
    for path in label_paths:
        with path.open(encoding="utf-8") as handle:
            for line in handle:
                if line.strip():
                    labels.append(TrainingLabel(**json.loads(line)))
    return tuple(observations), tuple(labels)


def _build_model(
    *,
    period: str,
    observations: tuple[Observation, ...],
    labels: dict[tuple[str, str, str], TrainingLabel],
    contexts: dict[tuple[str, str], Any],
    base_exits: dict[tuple[str, str], str],
) -> Model:
    counts: dict[str, dict[str, list[int]]] = {
        level: defaultdict(lambda: [0, 0])
        for level in ("L0", "L1", "L2", "L3", "L4")
    }
    seen: set[tuple[str, str, str, str]] = set()

    for row in sorted(
        (item for item in observations if item.period == period),
        key=lambda item: (item.entry_at, item.symbol, item.observed_at),
    ):
        key = (row.symbol, row.entry_at)
        base_exit = base_exits.get(key)
        if base_exit is None:
            continue
        if v18._aware(row.observed_at) >= v18._aware(base_exit):
            continue
        label = labels[(period, row.symbol, row.entry_at)]
        survived = (
            label.departure_at is not None
            and v18._aware(label.departure_at) < v18._aware(base_exit)
        )
        family = _entry_context_family(contexts[key])
        for level, signature in _signature_levels(
            row,
            entry_context_family=family,
        ):
            marker = (row.symbol, row.entry_at, level, signature)
            if marker in seen:
                continue
            seen.add(marker)
            counts[level][signature][0] += 1
            if survived:
                counts[level][signature][1] += 1

    return {
        level: {
            signature: (values[0], values[1])
            for signature, values in rows.items()
        }
        for level, rows in counts.items()
    }


def _estimate(
    model: Model,
    *,
    level: str,
    signature: str,
) -> tuple[int, Decimal]:
    support, survivors = model[level].get(signature, (0, 0))
    estimate = Decimal(survivors + BETA_ALPHA) / Decimal(
        support + BETA_ALPHA + BETA_BETA
    )
    return support, estimate


def _lookup_agreement(
    *,
    row: Observation,
    entry_context_family: str,
    model_a: Model,
    model_b: Model,
    minimum_support: int,
) -> tuple[str | None, str | None, int, int, Decimal | None, Decimal | None]:
    for level, signature in _signature_levels(
        row,
        entry_context_family=entry_context_family,
    ):
        support_a, estimate_a = _estimate(
            model_a,
            level=level,
            signature=signature,
        )
        support_b, estimate_b = _estimate(
            model_b,
            level=level,
            signature=signature,
        )
        if support_a >= minimum_support and support_b >= minimum_support:
            return (
                level,
                signature,
                support_a,
                support_b,
                estimate_a,
                estimate_b,
            )
    return None, None, 0, 0, None, None


def _controls_and_decisions(
    windows: dict[str, Any],
    contextual_model: dict[str, Any],
) -> tuple[
    dict[str, dict[str, Any]],
    dict[str, tuple[v18.InvalidationDecision, ...]],
]:
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
        controls: dict[str, dict[str, Any]] = {}
        decisions: dict[str, tuple[v18.InvalidationDecision, ...]] = {}
        for period, (ledgers, contexts) in windows.items():
            control, audit = v18._simulate(
                period=period,
                policy="SURFACE_CONTROL",
                ledgers=ledgers,
                contexts=contexts,
                contextual_model=contextual_model,
                events={},
            )
            controls[period] = control
            decisions[period] = audit
        return controls, decisions
    finally:
        v11._SIMULTANEOUS.clear()
        v11._SIMULTANEOUS.update(previous)


def _build_survival_events(
    *,
    windows: dict[str, Any],
    observations: tuple[Observation, ...],
    labels: tuple[TrainingLabel, ...],
    control_decisions: dict[str, tuple[v18.InvalidationDecision, ...]],
) -> tuple[
    dict[tuple[str, str, str, str], v18.TriggerEvent],
    tuple[SurvivalDecision, ...],
    dict[str, Any],
]:
    labels_by_key = {
        (row.period, row.symbol, row.entry_at): row
        for row in labels
    }
    models: dict[str, Model] = {}
    base_exit_maps: dict[str, dict[tuple[str, str], str]] = {}
    selected_keys: dict[str, set[tuple[str, str]]] = {}

    for period, (ledgers, contexts) in windows.items():
        keys = {
            (row.symbol, row.entry_at)
            for row in ledgers[milestone.ProtectionMode.ORIGINAL.value]
        }
        selected_keys[period] = keys
        decision_map = {
            (row.symbol, row.entry_at): row.final_exit_at
            for row in control_decisions[period]
        }
        if set(decision_map) != keys:
            raise ValueError("V21 control-decision identity mismatch")
        base_exit_maps[period] = decision_map
        models[period] = _build_model(
            period=period,
            observations=observations,
            labels=labels_by_key,
            contexts=contexts,
            base_exits=decision_map,
        )

    events: dict[tuple[str, str, str, str], v18.TriggerEvent] = {}
    audits: list[SurvivalDecision] = []
    model_audit: dict[str, Any] = {}

    period_order = tuple(windows)
    for heldout in period_order:
        trainers = tuple(period for period in period_order if period != heldout)
        if len(trainers) != 2:
            raise ValueError("V21 requires exactly two external trainer periods")
        trainer_a, trainer_b = trainers
        model_a = models[trainer_a]
        model_b = models[trainer_b]
        contexts = windows[heldout][1]
        base_exits = base_exit_maps[heldout]

        model_audit[heldout] = {
            "trainer_a": trainer_a,
            "trainer_b": trainer_b,
            "heldout_labels_visible_to_inference": False,
        }

        grouped: dict[tuple[str, str], list[Observation]] = defaultdict(list)
        for row in observations:
            key = (row.symbol, row.entry_at)
            if row.period != heldout or key not in selected_keys[heldout]:
                continue
            if v18._aware(row.observed_at) >= v18._aware(base_exits[key]):
                continue
            grouped[key].append(row)

        for key, rows in grouped.items():
            family = _entry_context_family(contexts[key])
            persistence = {policy: 0 for policy in POLICY_SPECS}
            triggered: set[str] = set()
            for row in sorted(rows, key=lambda item: v18._aware(item.observed_at)):
                for policy, (
                    phases,
                    maximum_survival,
                    minimum_support,
                ) in POLICY_SPECS.items():
                    if policy in triggered:
                        continue
                    structural_gate = row.phase in phases
                    (
                        level,
                        signature,
                        support_a,
                        support_b,
                        estimate_a,
                        estimate_b,
                    ) = _lookup_agreement(
                        row=row,
                        entry_context_family=family,
                        model_a=model_a,
                        model_b=model_b,
                        minimum_support=minimum_support,
                    )
                    support_gate = level is not None
                    survival_gate = (
                        support_gate
                        and estimate_a is not None
                        and estimate_b is not None
                        and estimate_a <= maximum_survival
                        and estimate_b <= maximum_survival
                    )
                    condition = structural_gate and survival_gate
                    persistence[policy] = (
                        persistence[policy] + 1 if condition else 0
                    )
                    apply = persistence[policy] >= PERSISTENCE_REQUIRED
                    audits.append(
                        SurvivalDecision(
                            period=heldout,
                            policy=policy,
                            symbol=row.symbol,
                            entry_at=row.entry_at,
                            observed_at=row.observed_at,
                            phase=row.phase,
                            signature_level=level,
                            signature=signature,
                            trainer_a_period=trainer_a,
                            trainer_b_period=trainer_b,
                            trainer_a_support=support_a,
                            trainer_b_support=support_b,
                            trainer_a_survival=(
                                None if estimate_a is None else str(estimate_a)
                            ),
                            trainer_b_survival=(
                                None if estimate_b is None else str(estimate_b)
                            ),
                            persistence=persistence[policy],
                            structural_gate=structural_gate,
                            support_gate=support_gate,
                            survival_gate=survival_gate,
                            exit_applied=apply,
                        )
                    )
                    if not apply:
                        continue
                    close_r = Decimal(row.close_r)
                    if close_r <= Decimal("-1"):
                        raise ValueError(
                            "V21 survival exit crossed original stop "
                            "before Surface exit"
                        )
                    triggered.add(policy)
                    events[
                        (
                            heldout,
                            row.symbol,
                            row.entry_at,
                            policy,
                        )
                    ] = v18.TriggerEvent(
                        period=heldout,
                        symbol=row.symbol,
                        session=row.session,
                        operating_date=row.operating_date,
                        entry_at=row.entry_at,
                        trigger=policy,
                        trigger_at=row.observed_at,
                        trigger_r=row.close_r,
                        elapsed_full_bars=row.elapsed_full_bars,
                        max_favorable_r_before_trigger=row.max_favorable_r,
                    )

    return events, tuple(audits), model_audit


def build_report(
    development_root: Path,
    validation_root: Path,
    reserved_root: Path,
    development_validation_context_root: Path,
    reserved_context_root: Path,
    evidence_root: Path,
) -> tuple[
    dict[str, Any],
    tuple[SurvivalDecision, ...],
    tuple[v18.InvalidationDecision, ...],
]:
    windows, contextual_model = v13._load_windows(
        development_root,
        validation_root,
        reserved_root,
        development_validation_context_root,
        reserved_context_root,
    )
    observations, labels = _load_market_evidence(evidence_root)
    controls, control_decisions = _controls_and_decisions(
        windows,
        contextual_model,
    )
    events, survival_audits, model_audit = _build_survival_events(
        windows=windows,
        observations=observations,
        labels=labels,
        control_decisions=control_decisions,
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
    v18.POLICY_SPECS.update(
        {
            policy: (policy, None, None)
            for policy in POLICY_SPECS
        }
    )
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
                    "total_survival_exits": total_exits,
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
        and row["total_survival_exits"] > 0
        and row["all_consumed_full_gate"]
    )
    return {
        "identity": IDENTITY,
        "evaluation": "CROSS_PERIOD_CAUSAL_HYPOTHESIS_SURVIVAL",
        "canonical_lifecycle_track": CANONICAL_TRACK,
        "departure_r": str(DEPARTURE_R),
        "smoothing": "BETA_1_1",
        "anti_pseudoreplication": "UNIQUE_TRADE_PER_SIGNATURE",
        "policy_specs": {
            policy: {
                "phases": sorted(phases),
                "maximum_survival": str(maximum_survival),
                "minimum_unique_trade_support_per_external_model": support,
                "persistence_full_m1_bars": PERSISTENCE_REQUIRED,
            }
            for policy, (
                phases,
                maximum_survival,
                support,
            ) in POLICY_SPECS.items()
        },
        "hierarchical_backoff": ["L0", "L1", "L2", "L3", "L4"],
        "model_audit": model_audit,
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
        "training_label_uses_terminal_pnl": False,
        "full_source_recompetition_required_before_freeze": True,
        "fresh_holdout_reserved": "2018-09-17_TO_2020-09-17",
        "fresh_holdout_opened": False,
        "automatic_policy_promotion": False,
        "trader_certified": False,
        "live_authorized": False,
        "real_capital_authorized": False,
        "next_phase": (
            "FULL_SOURCE_RECOMPETITION_V21_SURVIVORS"
            if candidates
            else "V21_FALSIFIED_RETURN_TO_CAUSAL_ENGINEERING"
        ),
    }, survival_audits, tuple(economic_audits)


def write_report(
    report: dict[str, Any],
    survival_audits: tuple[SurvivalDecision, ...],
    economic_audits: tuple[v18.InvalidationDecision, ...],
    output: Path,
) -> None:
    output.mkdir(parents=True, exist_ok=True)
    (output / "capitalizer-hypothesis-survival-model-v21.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    with (
        output / "capitalizer-hypothesis-survival-model-v21-decisions.jsonl"
    ).open("w", encoding="utf-8") as handle:
        for survival_row in survival_audits:
            handle.write(
                json.dumps(asdict(survival_row), sort_keys=True) + "\n"
            )
    with (
        output / "capitalizer-hypothesis-survival-model-v21-economics.jsonl"
    ).open("w", encoding="utf-8") as handle:
        for economic_row in economic_audits:
            handle.write(
                json.dumps(asdict(economic_row), sort_keys=True) + "\n"
            )


def main() -> None:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)

    market = sub.add_parser("market")
    market.add_argument("development_root", type=Path)
    market.add_argument("validation_root", type=Path)
    market.add_argument("reserved_root", type=Path)
    market.add_argument("m1_root", type=Path)
    market.add_argument("output", type=Path)
    market.add_argument("--symbol", required=True)

    aggregate = sub.add_parser("aggregate")
    aggregate.add_argument("development_root", type=Path)
    aggregate.add_argument("validation_root", type=Path)
    aggregate.add_argument("reserved_root", type=Path)
    aggregate.add_argument("development_validation_context_root", type=Path)
    aggregate.add_argument("reserved_context_root", type=Path)
    aggregate.add_argument("evidence_root", type=Path)
    aggregate.add_argument("output", type=Path)

    args = parser.parse_args()
    if args.command == "market":
        report, observations, labels = build_market_report(
            args.development_root,
            args.validation_root,
            args.reserved_root,
            args.m1_root,
            symbol=str(args.symbol).upper(),
        )
        write_market(report, observations, labels, args.output)
        print(json.dumps(report, sort_keys=True))
        return

    report, survival_audits, economic_audits = build_report(
        args.development_root,
        args.validation_root,
        args.reserved_root,
        args.development_validation_context_root,
        args.reserved_context_root,
        args.evidence_root,
    )
    write_report(
        report,
        survival_audits,
        economic_audits,
        args.output,
    )
    print(json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    main()

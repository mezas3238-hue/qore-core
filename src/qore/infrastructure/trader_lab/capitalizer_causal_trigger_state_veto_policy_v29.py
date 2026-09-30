"""Causal trigger-state intervention-veto policy for Capitalizer V29.

V28 proved that exact milestone timing is necessary but insufficient. V29 adds
two predeclared ingredients without changing entries, stop/target geometry or
MAX3:
- provider-native M1 trajectory state known before protection activation;
- a selective VETO_TO_ORIGINAL action when Surface itself is about to protect.

The veto is a decision token only. It selects the already-existing ORIGINAL
protection mode for the rest of the trade and does not create new geometry.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from dataclasses import asdict, dataclass, field, replace
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
    capitalizer_cognitive_r_milestone_protection_2r_v1 as milestone,
)
from qore.infrastructure.trader_lab import (
    capitalizer_continuation_value_model_v22 as v22,
)
from qore.infrastructure.trader_lab import (
    capitalizer_factor_journey_probe_ranker_v11 as v11,
)
from qore.infrastructure.trader_lab import (
    capitalizer_recovery_trajectory_trigger_v18 as recovery,
)
from qore.infrastructure.trader_lab import (
    capitalizer_regularized_causal_state_space_v25 as v25,
)
from qore.infrastructure.trader_lab import (
    capitalizer_robust_counterfactual_protection_policy_v27 as v27,
)
from qore.infrastructure.trader_lab import (
    capitalizer_sequence_failure_memory_abstention_v13 as v13,
)
from qore.infrastructure.trader_lab import (
    capitalizer_triggered_regularized_protection_policy_v28 as v28,
)
from qore.infrastructure.trader_lab.capitalizer_cibo_m1_reader_v1 import (
    CapitalizerM1Bar,
    iter_cibo_m1,
)

IDENTITY = "QORE_CAPITALIZER_CAUSAL_TRIGGER_STATE_VETO_POLICY_V29"
POLICY = "TRIGGER_STATE_ROBUST_POSDELTA_NONDOWNSIDE_WITH_VETO"
VETO_ACTION = "VETO_TO_ORIGINAL"
L2_PRIOR_STRENGTH = v25.L2_PRIOR_STRENGTH
SOURCE_M1_RUN_ID = 35548099334
SOURCE_M1_SHA = "18c338aedd5013ce65a6cb6408ffbc2e904a6217"

FAMILIES: dict[str, tuple[Decimal, tuple[str, ...]]] = {
    family: (trigger, tuple(arms))
    for family, (trigger, arms) in v28.FAMILIES.items()
}

TRAJECTORY_FEATURES = (
    "ELAPSED_COMPLETED_M1_BARS",
    "CURRENT_CLOSE_R",
    "CUMULATIVE_MFE_R",
    "CUMULATIVE_MAE_R",
    "RETRACEMENT_FROM_MFE_R",
    "VELOCITY_1_R",
    "VELOCITY_1_AVAILABLE",
    "VELOCITY_2_R",
    "VELOCITY_2_AVAILABLE",
    "BARS_SINCE_LAST_NEW_MFE",
    "LAST3_POSITIVE_CLOSE_FRACTION",
    "LAST5_POSITIVE_CLOSE_FRACTION",
    "LAST_BAR_DIRECTIONAL_BODY_R",
    "LAST_BAR_RANGE_R",
    "LAST_BAR_FAVORABLE_CLOSE_LOCATION",
    "LAST_BAR_MFE_INCREMENT_R",
    "CLOSE_TO_MFE_EFFICIENCY",
    "RETRACEMENT_TO_MFE_RATIO",
    "MAE_TO_MFE_RATIO",
)
TRAJECTORY_FEATURE_DIMENSION = len(TRAJECTORY_FEATURES)

FamilyModels = dict[
    str,
    dict[str, dict[str, tuple[v25.RidgeModel, v25.RidgeModel]]],
]


@dataclass(frozen=True, slots=True)
class TriggerState:
    period: str
    symbol: str
    session: str
    operating_date: str
    entry_at: str
    family: str
    trigger_at: str
    completed_m1_bars: int
    vector: tuple[float, ...]
    current_outcome_visible: bool = False
    future_bar_visible: bool = False
    activation_bar_ohlc_visible: bool = False


@dataclass(frozen=True, slots=True)
class V29Decision:
    period: str
    policy: str
    symbol: str
    session: str
    operating_date: str
    entry_at: str
    causal_surface_mode: str
    chosen_mode: str
    selected_action: str | None
    base_multiplier: str
    switched: bool
    veto_applied: bool
    chosen_family: str | None
    trigger_at: str | None
    trigger_delay_minutes: str | None
    completed_m1_bars: int | None
    trainer_a_period: str
    trainer_b_period: str
    robust_total_delta: str | None
    trainer_a_total_delta: str | None
    trainer_b_total_delta: str | None
    trainer_a_downside_delta: str | None
    trainer_b_downside_delta: str | None
    valid_common_trigger_count: int
    current_outcome_visible: bool = False
    heldout_counterfactual_visible: bool = False
    future_after_trigger_visible: bool = False
    activation_bar_ohlc_visible: bool = False
    identity_features_used: bool = False


@dataclass(slots=True)
class _TradeScan:
    period: str
    trade: milestone.SimulatedTrade
    triggers: list[tuple[str, datetime]]
    bars: list[CapitalizerM1Bar] = field(default_factory=list)


def _aware(value: str) -> datetime:
    return milestone._aware(value)


def _load_symbol_mode(
    root: Path,
    *,
    symbol: str,
    mode: milestone.ProtectionMode,
) -> tuple[milestone.SimulatedTrade, ...]:
    pattern = (
        f"capitalizer-{symbol.lower()}-max-recovery-direct-m1-replay-v1-"
        f"{mode.value.lower()}-trades.jsonl"
    )
    paths = sorted(root.rglob(pattern))
    if len(paths) != 1:
        raise ValueError(
            f"V29 requires one {symbol}/{mode.value} ledger, found {len(paths)}"
        )
    rows: list[milestone.SimulatedTrade] = []
    with paths[0].open(encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                rows.append(milestone.SimulatedTrade(**json.loads(line)))
    return tuple(
        sorted(rows, key=lambda row: (_aware(row.entry_at), row.symbol))
    )


def _market_windows(
    development_root: Path,
    validation_root: Path,
    reserved_root: Path,
    *,
    symbol: str,
) -> dict[str, dict[str, tuple[milestone.SimulatedTrade, ...]]]:
    period_roots = {
        v10.DEVELOPMENT_PERIOD: development_root,
        "CONSUMED_VALIDATION_2022_2024": validation_root,
        "CONSUMED_RESERVED_2020_2022": reserved_root,
    }
    result: dict[
        str, dict[str, tuple[milestone.SimulatedTrade, ...]]
    ] = {}
    for period, root in period_roots.items():
        result[period] = {
            mode.value: _load_symbol_mode(root, symbol=symbol, mode=mode)
            for mode in milestone.ProtectionMode
        }
        baseline_keys = {
            (row.symbol, row.entry_at)
            for row in result[period][milestone.ProtectionMode.ORIGINAL.value]
        }
        for mode, rows in result[period].items():
            if {(row.symbol, row.entry_at) for row in rows} != baseline_keys:
                raise ValueError(f"V29 mode identity drift in {period}/{mode}")
    return result


def _by_mode(
    ledgers: dict[str, tuple[milestone.SimulatedTrade, ...]],
) -> dict[str, dict[tuple[str, str], milestone.SimulatedTrade]]:
    return {
        mode: {(row.symbol, row.entry_at): row for row in rows}
        for mode, rows in ledgers.items()
    }


def _family_trigger_without_surface(
    *,
    key: tuple[str, str],
    arms: tuple[str, ...],
    modes: dict[str, dict[tuple[str, str], milestone.SimulatedTrade]],
) -> str | None:
    reference = modes[arms[0]][key].first_protection_at
    if reference is None:
        return None
    trigger_dt = _aware(reference)
    for arm in arms:
        candidate = modes[arm][key].first_protection_at
        if candidate is None or _aware(candidate) != trigger_dt:
            return None
    return reference


def _risk(trade: milestone.SimulatedTrade) -> Decimal:
    value = abs(
        Decimal(trade.entry_price) - Decimal(trade.original_stop_price)
    )
    if value <= 0:
        raise ValueError("V29 requires positive structural risk")
    return value


def _close_r(bar: CapitalizerM1Bar, trade: milestone.SimulatedTrade) -> Decimal:
    entry = Decimal(trade.entry_price)
    risk = _risk(trade)
    if trade.side == "LONG":
        return (bar.close - entry) / risk
    if trade.side == "SHORT":
        return (entry - bar.close) / risk
    raise ValueError(f"V29 unknown side {trade.side}")


def _favorable_r(
    bar: CapitalizerM1Bar,
    trade: milestone.SimulatedTrade,
) -> Decimal:
    entry = Decimal(trade.entry_price)
    risk = _risk(trade)
    if trade.side == "LONG":
        return max(Decimal("0"), (bar.high - entry) / risk)
    if trade.side == "SHORT":
        return max(Decimal("0"), (entry - bar.low) / risk)
    raise ValueError(f"V29 unknown side {trade.side}")


def _adverse_r(
    bar: CapitalizerM1Bar,
    trade: milestone.SimulatedTrade,
) -> Decimal:
    entry = Decimal(trade.entry_price)
    risk = _risk(trade)
    if trade.side == "LONG":
        return max(Decimal("0"), (entry - bar.low) / risk)
    if trade.side == "SHORT":
        return max(Decimal("0"), (bar.high - entry) / risk)
    raise ValueError(f"V29 unknown side {trade.side}")


def _directional_body_r(
    bar: CapitalizerM1Bar,
    trade: milestone.SimulatedTrade,
) -> Decimal:
    risk = _risk(trade)
    if trade.side == "LONG":
        return (bar.close - bar.open) / risk
    if trade.side == "SHORT":
        return (bar.open - bar.close) / risk
    raise ValueError(f"V29 unknown side {trade.side}")


def _favorable_close_location(
    bar: CapitalizerM1Bar,
    trade: milestone.SimulatedTrade,
) -> Decimal:
    if bar.range == 0:
        return Decimal("0.5")
    if trade.side == "LONG":
        return (bar.close - bar.low) / bar.range
    if trade.side == "SHORT":
        return (bar.high - bar.close) / bar.range
    raise ValueError(f"V29 unknown side {trade.side}")


def _fraction_positive(values: list[Decimal], count: int) -> float:
    tail = values[-count:]
    if not tail:
        return 0.0
    return sum(value > 0 for value in tail) / len(tail)


def _trajectory_vector(
    trade: milestone.SimulatedTrade,
    bars: list[CapitalizerM1Bar],
) -> tuple[float, ...]:
    if not bars:
        raise ValueError("V29 trigger state requires completed M1 bars")
    closes = [_close_r(bar, trade) for bar in bars]
    favorables = [_favorable_r(bar, trade) for bar in bars]
    adverses = [_adverse_r(bar, trade) for bar in bars]

    cumulative_mfe: list[Decimal] = []
    running = Decimal("0")
    last_new_mfe = 0
    for index, value in enumerate(favorables):
        if value > running:
            running = value
            last_new_mfe = index
        cumulative_mfe.append(running)

    mfe = cumulative_mfe[-1]
    mae = max(adverses, default=Decimal("0"))
    current = closes[-1]
    retracement = mfe - current
    velocity_1_available = len(closes) >= 2
    velocity_2_available = len(closes) >= 3
    velocity_1 = (
        current - closes[-2]
        if velocity_1_available
        else Decimal("0")
    )
    velocity_2 = (
        current - closes[-3]
        if velocity_2_available
        else Decimal("0")
    )
    prior_mfe = (
        cumulative_mfe[-2]
        if len(cumulative_mfe) >= 2
        else Decimal("0")
    )
    last_mfe_increment = max(Decimal("0"), mfe - prior_mfe)
    denominator = mfe if mfe > 0 else Decimal("1")
    risk = _risk(trade)
    last = bars[-1]

    vector = (
        float(len(bars)),
        float(current),
        float(mfe),
        float(mae),
        float(retracement),
        float(velocity_1),
        1.0 if velocity_1_available else 0.0,
        float(velocity_2),
        1.0 if velocity_2_available else 0.0,
        float(len(bars) - 1 - last_new_mfe),
        _fraction_positive(closes, 3),
        _fraction_positive(closes, 5),
        float(_directional_body_r(last, trade)),
        float(last.range / risk),
        float(_favorable_close_location(last, trade)),
        float(last_mfe_increment),
        float(current / denominator),
        float(retracement / denominator),
        float(mae / denominator),
    )
    if len(vector) != TRAJECTORY_FEATURE_DIMENSION:
        raise ValueError("V29 trajectory feature dimension drift")
    return vector


def _native_root(root: Path) -> Path:
    ledgers = tuple(root.rglob("RAW_M1_LEDGER"))
    if len(ledgers) != 1:
        raise ValueError(
            f"V29 requires one RAW_M1_LEDGER, found {len(ledgers)}"
        )
    return ledgers[0].parent


def _scan_trigger_states(
    *,
    symbol: str,
    windows: dict[str, dict[str, tuple[milestone.SimulatedTrade, ...]]],
    m1_root: Path,
) -> tuple[TriggerState, ...]:
    scans: list[_TradeScan] = []
    expected = 0

    for period, ledgers in windows.items():
        modes = _by_mode(ledgers)
        baseline = ledgers[milestone.ProtectionMode.ORIGINAL.value]
        for trade in baseline:
            key = (trade.symbol, trade.entry_at)
            triggers: list[tuple[str, datetime]] = []
            for family, (_threshold, arms) in FAMILIES.items():
                trigger_raw = _family_trigger_without_surface(
                    key=key,
                    arms=arms,
                    modes=modes,
                )
                if trigger_raw is not None:
                    triggers.append((family, _aware(trigger_raw)))
            if triggers:
                scans.append(
                    _TradeScan(
                        period=period,
                        trade=trade,
                        triggers=sorted(
                            triggers,
                            key=lambda item: (item[1], item[0]),
                        ),
                    )
                )
                expected += len(triggers)

    if not scans:
        raise ValueError("V29 found no market trigger requests")

    scans.sort(
        key=lambda item: (
            _aware(item.trade.entry_at),
            item.period,
            item.trade.symbol,
        )
    )
    first_entry = min(_aware(item.trade.entry_at) for item in scans)
    last_trigger = max(
        trigger
        for item in scans
        for _family, trigger in item.triggers
    )
    active: list[_TradeScan] = []
    pointer = 0
    states: list[TriggerState] = []

    def finalize_before(scan: _TradeScan, at: datetime) -> None:
        ready = [
            item for item in scan.triggers if item[1] <= at
        ]
        if not ready:
            return
        for family, trigger_at in ready:
            vector = _trajectory_vector(scan.trade, scan.bars)
            states.append(
                TriggerState(
                    period=scan.period,
                    symbol=scan.trade.symbol,
                    session=scan.trade.session,
                    operating_date=scan.trade.operating_date,
                    entry_at=scan.trade.entry_at,
                    family=family,
                    trigger_at=trigger_at.isoformat(),
                    completed_m1_bars=len(scan.bars),
                    vector=vector,
                )
            )
        ready_set = set(ready)
        scan.triggers = [
            item for item in scan.triggers if item not in ready_set
        ]

    for bar in iter_cibo_m1(_native_root(m1_root)):
        if bar.symbol != symbol:
            raise ValueError("V29 native-M1 symbol drift")
        if bar.closed_at <= first_entry:
            continue
        if bar.opened_at > last_trigger and pointer >= len(scans) and not active:
            break

        while (
            pointer < len(scans)
            and _aware(scans[pointer].trade.entry_at) <= bar.opened_at
        ):
            active.append(scans[pointer])
            pointer += 1

        survivors: list[_TradeScan] = []
        for scan in active:
            finalize_before(scan, bar.opened_at)
            if not scan.triggers:
                continue
            entry_at = _aware(scan.trade.entry_at)
            next_trigger = scan.triggers[0][1]
            if entry_at <= bar.opened_at and bar.closed_at <= next_trigger:
                scan.bars.append(bar)
            survivors.append(scan)
        active = survivors

    for scan in active:
        finalize_before(scan, last_trigger)
    if pointer != len(scans):
        raise ValueError("V29 native-M1 ended before all trigger scans activated")
    if len(states) != expected:
        raise ValueError(
            f"V29 trigger-state count mismatch {len(states)} != {expected}"
        )
    return tuple(
        sorted(
            states,
            key=lambda row: (
                row.period,
                row.entry_at,
                row.symbol,
                row.trigger_at,
                row.family,
            ),
        )
    )


def build_market_state_report(
    development_root: Path,
    validation_root: Path,
    reserved_root: Path,
    m1_root: Path,
    *,
    symbol: str,
) -> tuple[dict[str, Any], tuple[TriggerState, ...]]:
    windows = _market_windows(
        development_root,
        validation_root,
        reserved_root,
        symbol=symbol,
    )
    states = _scan_trigger_states(
        symbol=symbol,
        windows=windows,
        m1_root=m1_root,
    )
    by_period = Counter(row.period for row in states)
    by_family = Counter(row.family for row in states)
    return {
        "identity": IDENTITY,
        "evaluation": "NATIVE_M1_CAUSAL_TRIGGER_STATE_EXTRACTION",
        "symbol": symbol,
        "source_m1_run_id": SOURCE_M1_RUN_ID,
        "source_m1_sha": SOURCE_M1_SHA,
        "trigger_state_count": len(states),
        "trigger_states_by_period": dict(sorted(by_period.items())),
        "trigger_states_by_family": dict(sorted(by_family.items())),
        "trajectory_features": list(TRAJECTORY_FEATURES),
        "trajectory_feature_dimension": TRAJECTORY_FEATURE_DIMENSION,
        "bars_must_be_fully_completed_before_activation": True,
        "activation_bar_ohlc_visible": False,
        "current_outcome_visible": False,
        "future_bar_visible": False,
    }, states


def write_market_state(
    report: dict[str, Any],
    states: tuple[TriggerState, ...],
    output: Path,
) -> None:
    output.mkdir(parents=True, exist_ok=True)
    symbol = str(report["symbol"]).lower()
    stem = f"capitalizer-{symbol}-causal-trigger-state-v29"
    (output / f"{stem}.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    with (output / f"{stem}-trigger-states.jsonl").open(
        "w", encoding="utf-8"
    ) as handle:
        for row in states:
            handle.write(json.dumps(asdict(row), sort_keys=True) + "\n")


def _load_trigger_states(
    root: Path,
) -> dict[tuple[str, str, str, str], TriggerState]:
    paths = sorted(root.rglob("*-causal-trigger-state-v29-trigger-states.jsonl"))
    if len(paths) != 9:
        raise ValueError(
            f"V29 aggregate requires 9 trigger-state ledgers, found {len(paths)}"
        )
    result: dict[tuple[str, str, str, str], TriggerState] = {}
    for path in paths:
        with path.open(encoding="utf-8") as handle:
            for line in handle:
                if not line.strip():
                    continue
                raw = json.loads(line)
                raw["vector"] = tuple(float(value) for value in raw["vector"])
                row = TriggerState(**raw)
                key = (row.period, row.symbol, row.entry_at, row.family)
                if key in result:
                    raise ValueError("V29 duplicate trigger state")
                result[key] = row
    return result


def _trigger_features(
    pretrade: v10.Pretrade,
    *,
    entry_at: str,
    trigger_at: str,
    state: TriggerState,
) -> tuple[float, ...]:
    if state.trigger_at != trigger_at:
        raise ValueError("V29 trigger-state timestamp mismatch")
    delay = recovery._trigger_delay(entry_at, trigger_at)
    return (
        *v27._entry_features(pretrade),
        float(delay),
        *state.vector,
    )


def _veto_eligible(
    *,
    key: tuple[str, str],
    surface_mode: str,
    trigger_at: str,
    modes: dict[str, dict[tuple[str, str], milestone.SimulatedTrade]],
) -> bool:
    if surface_mode == milestone.ProtectionMode.ORIGINAL.value:
        return False
    first = modes[surface_mode][key].first_protection_at
    return first is not None and _aware(first) == _aware(trigger_at)


def _action_outcome(
    *,
    action: str,
    key: tuple[str, str],
    modes: dict[str, dict[tuple[str, str], milestone.SimulatedTrade]],
) -> milestone.SimulatedTrade:
    if action == VETO_ACTION:
        return modes[milestone.ProtectionMode.ORIGINAL.value][key]
    return modes[action][key]


def _training_examples(
    *,
    period: str,
    family: str,
    action: str,
    ledgers: dict[str, tuple[milestone.SimulatedTrade, ...]],
    pretrades: dict[tuple[str, str], v10.Pretrade],
    control_decisions: dict[tuple[str, str], Any],
    trigger_states: dict[tuple[str, str, str, str], TriggerState],
) -> tuple[
    tuple[v25.TrainingExample, ...],
    tuple[v25.TrainingExample, ...],
]:
    _threshold, family_arms = FAMILIES[family]
    if action not in family_arms and action != VETO_ACTION:
        raise ValueError("V29 action outside family")

    modes = _by_mode(ledgers)
    total_examples: list[v25.TrainingExample] = []
    downside_examples: list[v25.TrainingExample] = []

    for key, pretrade in pretrades.items():
        surface_mode = str(control_decisions[key].surface_mode)
        trigger_at = recovery._common_trigger(
            key=key,
            surface_mode=surface_mode,
            family_arms=family_arms,
            by_mode=modes,
        )
        if trigger_at is None:
            continue
        if action == VETO_ACTION and not _veto_eligible(
            key=key,
            surface_mode=surface_mode,
            trigger_at=trigger_at,
            modes=modes,
        ):
            continue

        state = trigger_states.get((period, key[0], key[1], family))
        if state is None:
            raise ValueError("V29 missing training trigger state")
        surface_r = Decimal(modes[surface_mode][key].realized_gross_r)
        action_r = Decimal(
            _action_outcome(
                action=action,
                key=key,
                modes=modes,
            ).realized_gross_r
        )
        total_delta = action_r - surface_r
        downside_delta = min(action_r, Decimal("0")) - min(
            surface_r, Decimal("0")
        )
        features = _trigger_features(
            pretrade,
            entry_at=key[1],
            trigger_at=trigger_at,
            state=state,
        )
        total_examples.append((features, float(total_delta), 1.0, key))
        downside_examples.append((features, float(downside_delta), 1.0, key))

    return tuple(total_examples), tuple(downside_examples)


def _fit_models(
    *,
    windows: dict[str, Any],
    pretrade_maps: dict[str, dict[tuple[str, str], v10.Pretrade]],
    control_maps: dict[str, dict[tuple[str, str], Any]],
    trigger_states: dict[tuple[str, str, str, str], TriggerState],
) -> tuple[FamilyModels, dict[str, Any]]:
    models: FamilyModels = {}
    diagnostics: dict[str, Any] = {}

    for period, (ledgers, _contexts) in windows.items():
        period_models: dict[
            str, dict[str, tuple[v25.RidgeModel, v25.RidgeModel]]
        ] = {}
        period_diagnostics: dict[str, Any] = {}
        for family, (_threshold, arms) in FAMILIES.items():
            action_models: dict[
                str, tuple[v25.RidgeModel, v25.RidgeModel]
            ] = {}
            action_diagnostics: dict[str, Any] = {}
            for action in (*arms, VETO_ACTION):
                total_examples, downside_examples = _training_examples(
                    period=period,
                    family=family,
                    action=action,
                    ledgers=ledgers,
                    pretrades=pretrade_maps[period],
                    control_decisions=control_maps[period],
                    trigger_states=trigger_states,
                )
                if not total_examples:
                    action_diagnostics[action] = {
                        "training_trades": 0,
                        "available": False,
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
                    "training_trades": total_model.unique_training_trades,
                    "feature_dimension": total_model.feature_dimension,
                    "total_target_mean": str(total_model.weighted_target_mean),
                    "downside_target_mean": str(
                        downside_model.weighted_target_mean
                    ),
                    "total_rmse": str(total_model.weighted_training_rmse),
                    "downside_rmse": str(
                        downside_model.weighted_training_rmse
                    ),
                    "available": True,
                }
            period_models[family] = action_models
            period_diagnostics[family] = action_diagnostics
        models[period] = period_models
        diagnostics[period] = period_diagnostics

    return models, diagnostics


def _choose_action(
    *,
    features: tuple[float, ...],
    surface_mode: str,
    actions: tuple[str, ...],
    model_a: dict[str, tuple[v25.RidgeModel, v25.RidgeModel]],
    model_b: dict[str, tuple[v25.RidgeModel, v25.RidgeModel]],
) -> tuple[
    str | None,
    float | None,
    tuple[float, float, float, float] | None,
]:
    chosen: str | None = None
    best_score: float | None = None
    best_predictions: tuple[float, float, float, float] | None = None

    for action in actions:
        if action == surface_mode:
            continue
        if action not in model_a or action not in model_b:
            continue
        total_a_model, downside_a_model = model_a[action]
        total_b_model, downside_b_model = model_b[action]
        total_a = v25._predict(total_a_model, features)
        total_b = v25._predict(total_b_model, features)
        downside_a = v25._predict(downside_a_model, features)
        downside_b = v25._predict(downside_b_model, features)
        if not (
            total_a > 0.0
            and total_b > 0.0
            and downside_a >= 0.0
            and downside_b >= 0.0
        ):
            continue
        score = min(total_a, total_b)
        if best_score is None or score > best_score:
            chosen = action
            best_score = score
            best_predictions = (
                total_a,
                total_b,
                downside_a,
                downside_b,
            )
    return chosen, best_score, best_predictions


def _valid_triggers(
    *,
    key: tuple[str, str],
    surface_mode: str,
    modes: dict[str, dict[tuple[str, str], milestone.SimulatedTrade]],
) -> tuple[tuple[str, str], ...]:
    result: list[tuple[str, str]] = []
    for family, (_trigger_r, arms) in FAMILIES.items():
        trigger_at = recovery._common_trigger(
            key=key,
            surface_mode=surface_mode,
            family_arms=arms,
            by_mode=modes,
        )
        if trigger_at is not None:
            result.append((family, trigger_at))
    return tuple(
        sorted(
            result,
            key=lambda row: (_aware(row[1]), row[0]),
        )
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
    trigger_states: dict[tuple[str, str, str, str], TriggerState],
) -> tuple[dict[str, Any], tuple[V29Decision, ...]]:
    modes = _by_mode(ledgers)
    ordered = tuple(
        sorted(
            ledgers[milestone.ProtectionMode.ORIGINAL.value],
            key=lambda row: (_aware(row.entry_at), row.symbol),
        )
    )
    chosen_scaled: list[milestone.SimulatedTrade] = []
    records: list[memory.MemoryRecord] = []
    audits: list[V29Decision] = []
    action_counts: Counter[str] = Counter()
    family_counts: Counter[str] = Counter()
    switches = 0
    vetoes = 0

    for trade in ordered:
        key = (trade.symbol, trade.entry_at)
        pretrade = v11._pretrade(
            period=period,
            trade=trade,
            contexts=contexts,
            contextual_model=contextual_model,
            chosen_scaled=tuple(chosen_scaled),
            records=tuple(records),
        )
        surface_mode = pretrade.mode
        triggers = _valid_triggers(
            key=key,
            surface_mode=surface_mode,
            modes=modes,
        )

        chosen_mode = surface_mode
        selected_action: str | None = None
        chosen_family: str | None = None
        chosen_trigger_at: str | None = None
        chosen_delay: str | None = None
        chosen_completed_bars: int | None = None
        robust_score: float | None = None
        predictions: tuple[float, float, float, float] | None = None

        for family, trigger_at in triggers:
            state = trigger_states.get(
                (period, trade.symbol, trade.entry_at, family)
            )
            if state is None:
                raise ValueError("V29 missing held-out trigger state")
            _threshold, arms = FAMILIES[family]
            actions = list(arms)
            if _veto_eligible(
                key=key,
                surface_mode=surface_mode,
                trigger_at=trigger_at,
                modes=modes,
            ):
                actions.append(VETO_ACTION)
            features = _trigger_features(
                pretrade,
                entry_at=trade.entry_at,
                trigger_at=trigger_at,
                state=state,
            )
            action, score, candidate_predictions = _choose_action(
                features=features,
                surface_mode=surface_mode,
                actions=tuple(actions),
                model_a=model_a[family],
                model_b=model_b[family],
            )
            if action is None:
                continue
            selected_action = action
            chosen_mode = (
                milestone.ProtectionMode.ORIGINAL.value
                if action == VETO_ACTION
                else action
            )
            chosen_family = family
            chosen_trigger_at = trigger_at
            chosen_delay = str(
                recovery._trigger_delay(trade.entry_at, trigger_at)
            )
            chosen_completed_bars = state.completed_m1_bars
            robust_score = score
            predictions = candidate_predictions
            break

        selected = modes[chosen_mode][key]
        normalized_r = Decimal(selected.realized_gross_r)
        scaled_r = normalized_r * pretrade.base_multiplier
        chosen_scaled.append(
            replace(selected, realized_gross_r=str(scaled_r))
        )
        records.append(
            memory.MemoryRecord(
                symbol=pretrade.ctx.symbol,
                session=pretrade.ctx.session,
                destination_state=pretrade.ctx.destination_state,
                context_signature=pretrade.ctx.context_signature,
                exit_at=selected.exit_at,
                normalized_realized_r=str(normalized_r),
            )
        )

        switched = chosen_mode != surface_mode
        switches += int(switched)
        veto_applied = selected_action == VETO_ACTION
        vetoes += int(veto_applied)
        action_counts[chosen_mode] += 1
        if chosen_family is not None:
            family_counts[chosen_family] += 1

        if predictions is None:
            total_a = total_b = downside_a = downside_b = None
        else:
            total_a, total_b, downside_a, downside_b = predictions

        audits.append(
            V29Decision(
                period=period,
                policy=POLICY,
                symbol=trade.symbol,
                session=trade.session,
                operating_date=trade.operating_date,
                entry_at=trade.entry_at,
                causal_surface_mode=surface_mode,
                chosen_mode=chosen_mode,
                selected_action=selected_action,
                base_multiplier=str(pretrade.base_multiplier),
                switched=switched,
                veto_applied=veto_applied,
                chosen_family=chosen_family,
                trigger_at=chosen_trigger_at,
                trigger_delay_minutes=chosen_delay,
                completed_m1_bars=chosen_completed_bars,
                trainer_a_period=trainer_a,
                trainer_b_period=trainer_b,
                robust_total_delta=(
                    None if robust_score is None else str(robust_score)
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
                valid_common_trigger_count=len(triggers),
            )
        )

    ledger = tuple(chosen_scaled)
    return {
        "period": period,
        "policy": POLICY,
        "trades": len(ledger),
        "density_retention": "1",
        "metrics": milestone._metrics(ledger),
        "action_switch_count": switches,
        "veto_to_original_count": vetoes,
        "action_counts": dict(sorted(action_counts.items())),
        "family_switch_counts": dict(sorted(family_counts.items())),
    }, tuple(audits)


def build_report(
    development_root: Path,
    validation_root: Path,
    reserved_root: Path,
    development_validation_context_root: Path,
    reserved_context_root: Path,
    trigger_state_root: Path,
) -> tuple[dict[str, Any], tuple[V29Decision, ...]]:
    windows, contextual_model = v13._load_windows(
        development_root,
        validation_root,
        reserved_root,
        development_validation_context_root,
        reserved_context_root,
    )
    trigger_states = _load_trigger_states(trigger_state_root)

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
        controls, _control_rows, control_maps = v22._control_decision_maps(
            windows,
            contextual_model,
        )
        pretrade_maps = v25._build_control_pretrades(
            windows=windows,
            contextual_model=contextual_model,
            control_maps=control_maps,
        )
        models, model_diagnostics = _fit_models(
            windows=windows,
            pretrade_maps=pretrade_maps,
            control_maps=control_maps,
            trigger_states=trigger_states,
        )

        results: list[dict[str, Any]] = []
        audits: list[V29Decision] = []
        for heldout, (ledgers, contexts) in windows.items():
            trainers = tuple(period for period in windows if period != heldout)
            if len(trainers) != 2:
                raise ValueError("V29 requires exactly two external periods")
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
                trigger_states=trigger_states,
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
    total_switches = sum(int(row["action_switch_count"]) for row in results)
    total_vetoes = sum(int(row["veto_to_original_count"]) for row in results)
    candidate_count = int(full_gate and total_switches > 0)

    return {
        "identity": IDENTITY,
        "evaluation": "NATIVE_M1_TRIGGER_STATE_WITH_SURFACE_INTERVENTION_VETO",
        "policy": POLICY,
        "veto_action": VETO_ACTION,
        "veto_semantics": "SELECT_EXISTING_ORIGINAL_FOR_REMAINDER_OF_TRADE",
        "defer_and_reevaluate_enabled": False,
        "families": {
            family: {
                "trigger_r": str(trigger_r),
                "arms": list(arms),
            }
            for family, (trigger_r, arms) in FAMILIES.items()
        },
        "l2_prior_strength_effective_trades": str(L2_PRIOR_STRENGTH),
        "source_m1_run_id": SOURCE_M1_RUN_ID,
        "source_m1_sha": SOURCE_M1_SHA,
        "trajectory_features": list(TRAJECTORY_FEATURES),
        "trajectory_feature_dimension": TRAJECTORY_FEATURE_DIMENSION,
        "pretrade_vector_source": "FULL_V10_V11_CAUSAL_PRETRADE",
        "exact_trigger_delay_used": True,
        "native_m1_trigger_state_used": True,
        "v21_post_025_state_reused": False,
        "trigger_time_portfolio_state_used": False,
        "trigger_time_cross_market_state_used": False,
        "model_diagnostics": model_diagnostics,
        "results": results,
        "total_action_switches": total_switches,
        "total_veto_to_original": total_vetoes,
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
            "FULL_SOURCE_IDENTITY_PROOF_V29_SURVIVOR"
            if candidate_count
            else "V29_FALSIFIED_PORTFOLIO_OR_SEQUENTIAL_DEFER_REQUIRED"
        ),
    }, tuple(audits)


def write_report(
    report: dict[str, Any],
    audits: tuple[V29Decision, ...],
    output: Path,
) -> None:
    output.mkdir(parents=True, exist_ok=True)
    (
        output
        / "capitalizer-causal-trigger-state-veto-policy-v29.json"
    ).write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    with (
        output
        / "capitalizer-causal-trigger-state-veto-policy-v29-decisions.jsonl"
    ).open("w", encoding="utf-8") as handle:
        for row in audits:
            handle.write(json.dumps(asdict(row), sort_keys=True) + "\n")


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
    aggregate.add_argument("trigger_state_root", type=Path)
    aggregate.add_argument("output", type=Path)

    args = parser.parse_args()
    if args.command == "market":
        report, states = build_market_state_report(
            args.development_root,
            args.validation_root,
            args.reserved_root,
            args.m1_root,
            symbol=args.symbol,
        )
        write_market_state(report, states, args.output)
        print(json.dumps(report, sort_keys=True))
        return

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

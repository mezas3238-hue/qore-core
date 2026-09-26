"""Cross-period counterfactual continuation-value model for Capitalizer V22.

V21 showed that failure to reach +0.25R is not equivalent to an economically
correct exit. V22 asks the decision-relevant question instead: at a causal,
fully completed M1 observation, do two independent external periods agree that
closing now has positive value versus continuing the frozen Surface trade?

The future Surface result is training-only. Held-out inference uses only causal
V21/HSM_BASE state plus retracement from observed MFE and two-bar close-R
velocity. Symbol, session, side, operating date and clock time are excluded from
model signatures.
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

IDENTITY = "QORE_CAPITALIZER_CONTINUATION_VALUE_MODEL_V22"
POLICY = "INVALIDATING_CV_W95_POSMEAN_N30_P2"
POLICIES = ("SURFACE_CONTROL", POLICY)
MINIMUM_SUPPORT = 30
PERSISTENCE_REQUIRED = 2
WILSON_Z = 1.959963984540054
WILSON_MINIMUM = Decimal("0.50")
ZERO_PRIOR_PSEUDO_SUPPORT = 2


@dataclass(frozen=True, slots=True)
class ValueObservation:
    row: v21.Observation
    retracement_r: str
    velocity_two_bar_r: str | None


@dataclass(frozen=True, slots=True)
class SignatureStats:
    support: int
    beneficial_exits: int
    sum_exit_advantage_r: str


@dataclass(frozen=True, slots=True)
class ValueDecision:
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
    trainer_a_wilson_lower: str | None
    trainer_b_wilson_lower: str | None
    trainer_a_shrunk_mean_advantage_r: str | None
    trainer_b_shrunk_mean_advantage_r: str | None
    persistence: int
    structural_gate: bool
    support_gate: bool
    evidence_gate: bool
    exit_applied: bool
    current_outcome_visible: bool = False
    future_bars_visible: bool = False
    original_exit_bar_used: bool = False
    unchosen_counterfactual_visible: bool = False
    heldout_training_label_visible: bool = False


Model = dict[str, dict[str, SignatureStats]]


def _retracement_bin(value: Decimal) -> str:
    if value < Decimal("0.15"):
        return "RET_LT_015"
    if value < Decimal("0.30"):
        return "RET_015_030"
    if value < Decimal("0.50"):
        return "RET_030_050"
    return "RET_GE_050"


def _velocity_bin(value: Decimal | None) -> str:
    if value is None:
        return "VEL_UNAVAILABLE"
    if value >= Decimal("0.05"):
        return "VEL_IMPROVING"
    if value <= Decimal("-0.05"):
        return "VEL_DETERIORATING"
    return "VEL_FLAT"


def _augment_observations(
    observations: tuple[v21.Observation, ...],
) -> tuple[ValueObservation, ...]:
    grouped: dict[tuple[str, str, str], list[v21.Observation]] = defaultdict(list)
    for row in observations:
        grouped[(row.period, row.symbol, row.entry_at)].append(row)

    result: list[ValueObservation] = []
    for rows in grouped.values():
        ordered = sorted(rows, key=lambda item: v18._aware(item.observed_at))
        closes: list[Decimal] = []
        for row in ordered:
            close_r = Decimal(row.close_r)
            retracement = Decimal(row.max_favorable_r) - close_r
            velocity = None if len(closes) < 2 else close_r - closes[-2]
            result.append(
                ValueObservation(
                    row=row,
                    retracement_r=str(retracement),
                    velocity_two_bar_r=None if velocity is None else str(velocity),
                )
            )
            closes.append(close_r)

    return tuple(
        sorted(
            result,
            key=lambda item: (
                item.row.period,
                item.row.entry_at,
                item.row.symbol,
                item.row.observed_at,
            ),
        )
    )


def _signature_levels(
    item: ValueObservation,
    *,
    entry_context_family: str,
) -> tuple[tuple[str, str], ...]:
    row = item.row
    phase = row.phase
    flags = v21._flags(row)
    age = v21._invalidating_age_bin(row.invalidating_age)
    elapsed = v21._elapsed_bin(row.elapsed_full_bars)
    mfe = v21._mfe_bin(Decimal(row.max_favorable_r))
    close = v21._close_bin(Decimal(row.close_r))
    adverse = v21._adverse_bin(row.adverse_close_count)
    retracement = _retracement_bin(Decimal(item.retracement_r))
    velocity = _velocity_bin(
        None
        if item.velocity_two_bar_r is None
        else Decimal(item.velocity_two_bar_r)
    )
    dynamic = "|".join((elapsed, mfe, close, adverse))
    trajectory = "|".join((retracement, velocity))
    return (
        (
            "L0",
            "|".join(
                (
                    phase,
                    flags,
                    age,
                    dynamic,
                    trajectory,
                    entry_context_family,
                )
            ),
        ),
        ("L1", "|".join((phase, flags, age, dynamic, trajectory))),
        ("L2", "|".join((phase, flags, age, trajectory))),
        ("L3", "|".join((phase, dynamic, trajectory))),
        ("L4", "|".join((phase, trajectory))),
        ("L5", phase),
    )


def _wilson_lower(beneficial: int, support: int) -> Decimal:
    if support <= 0:
        return Decimal("0")
    probability = beneficial / support
    z2 = WILSON_Z * WILSON_Z
    denominator = 1.0 + z2 / support
    center = probability + z2 / (2.0 * support)
    margin = WILSON_Z * math.sqrt(
        probability * (1.0 - probability) / support
        + z2 / (4.0 * support * support)
    )
    return Decimal(str((center - margin) / denominator))


def _shrunk_mean(stats: SignatureStats) -> Decimal:
    return Decimal(stats.sum_exit_advantage_r) / Decimal(
        stats.support + ZERO_PRIOR_PSEUDO_SUPPORT
    )


def _build_model(
    *,
    period: str,
    observations: tuple[ValueObservation, ...],
    contexts: dict[tuple[str, str], Any],
    control_decisions: dict[tuple[str, str], v18.InvalidationDecision],
) -> Model:
    accumulators: dict[str, dict[str, list[Any]]] = {
        level: defaultdict(lambda: [0, 0, Decimal("0")])
        for level in ("L0", "L1", "L2", "L3", "L4", "L5")
    }
    seen: set[tuple[str, str, str, str]] = set()

    for item in sorted(
        (value for value in observations if value.row.period == period),
        key=lambda value: (
            value.row.entry_at,
            value.row.symbol,
            value.row.observed_at,
        ),
    ):
        row = item.row
        key = (row.symbol, row.entry_at)
        decision = control_decisions.get(key)
        if decision is None:
            continue
        if v18._aware(row.observed_at) >= v18._aware(decision.final_exit_at):
            continue

        final_surface_r = Decimal(decision.normalized_realized_r)
        exit_advantage = Decimal(row.close_r) - final_surface_r
        family = v21._entry_context_family(contexts[key])

        for level, signature in _signature_levels(
            item,
            entry_context_family=family,
        ):
            marker = (row.symbol, row.entry_at, level, signature)
            if marker in seen:
                continue
            seen.add(marker)
            values = accumulators[level][signature]
            values[0] += 1
            values[1] += int(exit_advantage > 0)
            values[2] += exit_advantage

    return {
        level: {
            signature: SignatureStats(
                support=int(values[0]),
                beneficial_exits=int(values[1]),
                sum_exit_advantage_r=str(values[2]),
            )
            for signature, values in rows.items()
        }
        for level, rows in accumulators.items()
    }


def _lookup_agreement(
    *,
    item: ValueObservation,
    entry_context_family: str,
    model_a: Model,
    model_b: Model,
) -> tuple[
    str | None,
    str | None,
    SignatureStats | None,
    SignatureStats | None,
]:
    for level, signature in _signature_levels(
        item,
        entry_context_family=entry_context_family,
    ):
        left = model_a[level].get(signature)
        right = model_b[level].get(signature)
        if (
            left is not None
            and right is not None
            and left.support >= MINIMUM_SUPPORT
            and right.support >= MINIMUM_SUPPORT
        ):
            return level, signature, left, right
    return None, None, None, None


def _evidence_passes(stats: SignatureStats | None) -> bool:
    if stats is None or stats.support < MINIMUM_SUPPORT:
        return False
    return (
        _wilson_lower(stats.beneficial_exits, stats.support) > WILSON_MINIMUM
        and _shrunk_mean(stats) > 0
    )


def _control_decision_maps(
    windows: dict[str, Any],
    contextual_model: dict[str, Any],
) -> tuple[
    dict[str, dict[str, Any]],
    dict[str, tuple[v18.InvalidationDecision, ...]],
    dict[str, dict[tuple[str, str], v18.InvalidationDecision]],
]:
    controls, rows = v21._controls_and_decisions(windows, contextual_model)
    mappings = {
        period: {
            (item.symbol, item.entry_at): item
            for item in decisions
        }
        for period, decisions in rows.items()
    }
    return controls, rows, mappings


def _build_value_events(
    *,
    windows: dict[str, Any],
    observations: tuple[ValueObservation, ...],
    control_decision_maps: dict[
        str, dict[tuple[str, str], v18.InvalidationDecision]
    ],
) -> tuple[
    dict[tuple[str, str, str, str], v18.TriggerEvent],
    tuple[ValueDecision, ...],
    dict[str, Any],
]:
    models: dict[str, Model] = {}
    selected_keys: dict[str, set[tuple[str, str]]] = {}

    for period, (ledgers, contexts) in windows.items():
        keys = {
            (row.symbol, row.entry_at)
            for row in ledgers[milestone.ProtectionMode.ORIGINAL.value]
        }
        selected_keys[period] = keys
        if set(control_decision_maps[period]) != keys:
            raise ValueError("V22 control-decision identity mismatch")
        models[period] = _build_model(
            period=period,
            observations=observations,
            contexts=contexts,
            control_decisions=control_decision_maps[period],
        )

    events: dict[tuple[str, str, str, str], v18.TriggerEvent] = {}
    audits: list[ValueDecision] = []
    model_audit: dict[str, Any] = {}
    period_order = tuple(windows)

    for heldout in period_order:
        trainers = tuple(period for period in period_order if period != heldout)
        if len(trainers) != 2:
            raise ValueError("V22 requires exactly two external trainer periods")
        trainer_a, trainer_b = trainers
        model_a = models[trainer_a]
        model_b = models[trainer_b]
        contexts = windows[heldout][1]
        base_exits = {
            key: row.final_exit_at
            for key, row in control_decision_maps[heldout].items()
        }

        model_audit[heldout] = {
            "trainer_a": trainer_a,
            "trainer_b": trainer_b,
            "heldout_exit_advantage_visible_to_inference": False,
        }

        grouped: dict[tuple[str, str], list[ValueObservation]] = defaultdict(list)
        for item in observations:
            row = item.row
            key = (row.symbol, row.entry_at)
            if row.period != heldout or key not in selected_keys[heldout]:
                continue
            if v18._aware(row.observed_at) >= v18._aware(base_exits[key]):
                continue
            grouped[key].append(item)

        for key, rows in grouped.items():
            family = v21._entry_context_family(contexts[key])
            persistence = 0
            triggered = False
            for item in sorted(
                rows,
                key=lambda value: v18._aware(value.row.observed_at),
            ):
                if triggered:
                    break
                row = item.row
                level, signature, stats_a, stats_b = _lookup_agreement(
                    item=item,
                    entry_context_family=family,
                    model_a=model_a,
                    model_b=model_b,
                )
                structural_gate = row.phase == v20.Phase.INVALIDATING.value
                support_gate = level is not None
                evidence_gate = (
                    support_gate
                    and _evidence_passes(stats_a)
                    and _evidence_passes(stats_b)
                )
                condition = structural_gate and evidence_gate
                persistence = persistence + 1 if condition else 0
                apply = persistence >= PERSISTENCE_REQUIRED

                audits.append(
                    ValueDecision(
                        period=heldout,
                        policy=POLICY,
                        symbol=row.symbol,
                        entry_at=row.entry_at,
                        observed_at=row.observed_at,
                        phase=row.phase,
                        signature_level=level,
                        signature=signature,
                        trainer_a_period=trainer_a,
                        trainer_b_period=trainer_b,
                        trainer_a_support=0 if stats_a is None else stats_a.support,
                        trainer_b_support=0 if stats_b is None else stats_b.support,
                        trainer_a_wilson_lower=(
                            None
                            if stats_a is None
                            else str(
                                _wilson_lower(
                                    stats_a.beneficial_exits,
                                    stats_a.support,
                                )
                            )
                        ),
                        trainer_b_wilson_lower=(
                            None
                            if stats_b is None
                            else str(
                                _wilson_lower(
                                    stats_b.beneficial_exits,
                                    stats_b.support,
                                )
                            )
                        ),
                        trainer_a_shrunk_mean_advantage_r=(
                            None if stats_a is None else str(_shrunk_mean(stats_a))
                        ),
                        trainer_b_shrunk_mean_advantage_r=(
                            None if stats_b is None else str(_shrunk_mean(stats_b))
                        ),
                        persistence=persistence,
                        structural_gate=structural_gate,
                        support_gate=support_gate,
                        evidence_gate=evidence_gate,
                        exit_applied=apply,
                    )
                )
                if not apply:
                    continue

                close_r = Decimal(row.close_r)
                if close_r <= Decimal("-1"):
                    raise ValueError("V22 exit crossed original stop")
                triggered = True
                events[(heldout, row.symbol, row.entry_at, POLICY)] = v18.TriggerEvent(
                    period=heldout,
                    symbol=row.symbol,
                    session=row.session,
                    operating_date=row.operating_date,
                    entry_at=row.entry_at,
                    trigger=POLICY,
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
    v21_evidence_root: Path,
) -> tuple[
    dict[str, Any],
    tuple[ValueDecision, ...],
    tuple[v18.InvalidationDecision, ...],
]:
    windows, contextual_model = v13._load_windows(
        development_root,
        validation_root,
        reserved_root,
        development_validation_context_root,
        reserved_context_root,
    )
    raw_observations, _labels = v21._load_market_evidence(v21_evidence_root)
    observations = _augment_observations(raw_observations)
    controls, _control_rows, control_maps = _control_decision_maps(
        windows,
        contextual_model,
    )
    events, value_audits, model_audit = _build_value_events(
        windows=windows,
        observations=observations,
        control_decision_maps=control_maps,
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
                    "total_value_exits": total_exits,
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
        and row["total_value_exits"] > 0
        and row["all_consumed_full_gate"]
    )

    return {
        "identity": IDENTITY,
        "evaluation": "CROSS_PERIOD_COUNTERFACTUAL_CONTINUATION_VALUE",
        "policy": POLICY,
        "canonical_lifecycle_track": v21.CANONICAL_TRACK,
        "departure_r": str(v21.DEPARTURE_R),
        "minimum_unique_trade_support_per_external_model": MINIMUM_SUPPORT,
        "wilson_confidence": "0.95",
        "wilson_z": str(WILSON_Z),
        "wilson_lower_probability_must_exceed": str(WILSON_MINIMUM),
        "mean_advantage_shrinkage": (
            "SUM_EXIT_ADVANTAGE_DIV_SUPPORT_PLUS_2_ZERO_PRIOR"
        ),
        "persistence_full_m1_bars": PERSISTENCE_REQUIRED,
        "hierarchical_backoff": ["L0", "L1", "L2", "L3", "L4", "L5"],
        "anti_pseudoreplication": "UNIQUE_TRADE_PER_SIGNATURE",
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
            "FULL_SOURCE_RECOMPETITION_V22_SURVIVOR"
            if candidates
            else "V22_FALSIFIED_RETURN_TO_CAUSAL_ENGINEERING"
        ),
    }, value_audits, tuple(economic_audits)


def write_report(
    report: dict[str, Any],
    value_audits: tuple[ValueDecision, ...],
    economic_audits: tuple[v18.InvalidationDecision, ...],
    output: Path,
) -> None:
    output.mkdir(parents=True, exist_ok=True)
    (output / "capitalizer-continuation-value-model-v22.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    with (
        output / "capitalizer-continuation-value-model-v22-decisions.jsonl"
    ).open("w", encoding="utf-8") as handle:
        for row in value_audits:
            handle.write(json.dumps(asdict(row), sort_keys=True) + "\n")
    with (
        output / "capitalizer-continuation-value-model-v22-economics.jsonl"
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

    report, value_audits, economic_audits = build_report(
        args.development_root,
        args.validation_root,
        args.reserved_root,
        args.development_validation_context_root,
        args.reserved_context_root,
        args.v21_evidence_root,
    )
    write_report(report, value_audits, economic_audits, args.output)
    print(json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    main()

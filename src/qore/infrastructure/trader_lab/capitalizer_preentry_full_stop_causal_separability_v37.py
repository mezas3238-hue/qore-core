"""Pre-entry full-stop causal separability frontier for Capitalizer V37.

UTC-001 shows that the dominant consumed-data deficits are no longer only
drawdown: annual expectancy and payoff also fail. Earlier V12-V15 admission
rules are already falsified and must not be threshold-retuned.

V37 asks a narrower representation question before any new admission policy is
allowed:

    Can the complete causal V11 pre-entry state distinguish structural ORIGINAL
    full-stop losers from structural ORIGINAL target winners across eras?

STOP/TARGET are labels only and are first touched after each pre-entry feature
vector is frozen. Two independent external-era ridge models score every held-out
period. V37 reports transport AUC and one fixed dual-world top-decile risk probe;
it never abstains, changes sizing, changes exits, or becomes a runtime policy.

The top-decile probe is diagnostic only. Its threshold is the 90th percentile of
each trainer's own fitted training-score distribution and is frozen by design;
there is no threshold grid and no candidate promotion.
"""

from __future__ import annotations

import argparse
import json
import math
from collections import defaultdict
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
    capitalizer_factor_journey_probe_ranker_v11 as v11,
)
from qore.infrastructure.trader_lab import (
    capitalizer_regularized_causal_state_space_v25 as v25,
)
from qore.infrastructure.trader_lab import (
    capitalizer_sequence_failure_memory_abstention_v13 as v13,
)

IDENTITY = "QORE_CAPITALIZER_PREENTRY_FULL_STOP_CAUSAL_SEPARABILITY_V37"
LABEL_STOP = "STOP"
LABEL_TARGET = "TARGET"
TRAINING_TARGET_STOP = 1.0
TRAINING_TARGET_TARGET = 0.0
RISK_QUANTILE = 0.90
Z_95 = 1.959963984540054
EXPECTED_V11_FEATURE_DIMENSION = 45


@dataclass(frozen=True, slots=True)
class LabeledEntryState:
    period: str
    symbol: str
    session: str
    operating_date: str
    entry_at: str
    label: str
    original_realized_r: str
    vector: tuple[float, ...]
    label_visible_to_features: bool = False
    future_exit_visible_to_features: bool = False
    future_mfe_mae_visible_to_features: bool = False
    symbol_identity_feature_used: bool = False
    date_identity_feature_used: bool = False


@dataclass(frozen=True, slots=True)
class AucEvidence:
    auc: str
    standard_error: str
    lower_95: str
    upper_95: str
    stops: int
    targets: int


@dataclass(frozen=True, slots=True)
class HeldoutSeparability:
    heldout_period: str
    trainer_a_period: str
    trainer_b_period: str
    feature_dimension: int
    evaluated_states: int
    stops: int
    targets: int
    stop_prevalence: str
    trainer_a_auc: AucEvidence
    trainer_b_auc: AucEvidence
    consensus_mean_auc: AucEvidence
    trainer_a_q90_training_threshold: str
    trainer_b_q90_training_threshold: str
    dual_world_top_decile_selected: int
    dual_world_top_decile_stops: int
    dual_world_top_decile_targets: int
    dual_world_stop_precision: str | None
    dual_world_stop_recall: str
    dual_world_target_count_preservation: str
    dual_world_precision_lift_vs_base: str | None
    both_external_auc_lower95_above_chance: bool
    consensus_auc_lower95_above_chance: bool
    target_count_preservation_at_least_90pct: bool
    risk_tail_enriched_above_base: bool


def _aware(value: str):
    return milestone._aware(value)


def _label_original(row: milestone.SimulatedTrade) -> str | None:
    reason = row.exit_reason.upper()
    if reason == LABEL_STOP:
        return LABEL_STOP
    if reason == LABEL_TARGET:
        return LABEL_TARGET
    return None


def _surface_entry_states(
    *,
    period: str,
    ledgers: dict[str, tuple[milestone.SimulatedTrade, ...]],
    contexts: dict[tuple[str, str], Any],
    contextual_model: dict[str, Any],
) -> tuple[LabeledEntryState, ...]:
    by_mode = {
        mode: {(row.symbol, row.entry_at): row for row in rows}
        for mode, rows in ledgers.items()
    }
    ordered = tuple(
        sorted(
            ledgers[milestone.ProtectionMode.ORIGINAL.value],
            key=lambda row: (_aware(row.entry_at), row.symbol),
        )
    )
    chosen: list[milestone.SimulatedTrade] = []
    records: list[memory.MemoryRecord] = []
    states: list[LabeledEntryState] = []

    for trade in ordered:
        key = (trade.symbol, trade.entry_at)
        pre = v11._pretrade(
            period=period,
            trade=trade,
            contexts=contexts,
            contextual_model=contextual_model,
            chosen_scaled=tuple(chosen),
            records=tuple(records),
        )
        if len(pre.point.vector) != EXPECTED_V11_FEATURE_DIMENSION:
            raise ValueError(
                "V37 V11 feature dimension drift: "
                f"{len(pre.point.vector)} != {EXPECTED_V11_FEATURE_DIMENSION}"
            )

        # Freeze the feature vector before touching the structural outcome label.
        frozen_vector = tuple(pre.point.vector)
        original = by_mode[milestone.ProtectionMode.ORIGINAL.value][key]
        label = _label_original(original)
        if label is not None:
            states.append(
                LabeledEntryState(
                    period=period,
                    symbol=trade.symbol,
                    session=trade.session,
                    operating_date=trade.operating_date,
                    entry_at=trade.entry_at,
                    label=label,
                    original_realized_r=original.realized_gross_r,
                    vector=frozen_vector,
                )
            )

        selected = by_mode[pre.mode][key]
        scaled_r = Decimal(selected.realized_gross_r) * pre.base_multiplier
        chosen.append(
            replace(selected, realized_gross_r=str(scaled_r))
        )
        records.append(
            memory.MemoryRecord(
                symbol=pre.ctx.symbol,
                session=pre.ctx.session,
                destination_state=pre.ctx.destination_state,
                context_signature=pre.ctx.context_signature,
                exit_at=selected.exit_at,
                normalized_realized_r=selected.realized_gross_r,
            )
        )

    if not states:
        raise ValueError(f"V37 {period} produced no STOP/TARGET labels")
    return tuple(states)


def _training_examples(
    states: tuple[LabeledEntryState, ...],
) -> tuple[v25.TrainingExample, ...]:
    result: list[v25.TrainingExample] = []
    for row in states:
        target = (
            TRAINING_TARGET_STOP
            if row.label == LABEL_STOP
            else TRAINING_TARGET_TARGET
        )
        result.append(
            (
                row.vector,
                target,
                1.0,
                (row.symbol, row.entry_at),
            )
        )
    return tuple(result)


def _quantile(values: tuple[float, ...], probability: float) -> float:
    if not values:
        raise ValueError("V37 quantile requires values")
    if not 0.0 <= probability <= 1.0:
        raise ValueError("V37 quantile probability outside [0,1]")
    ordered = sorted(values)
    index = max(
        0,
        min(
            len(ordered) - 1,
            math.ceil(probability * len(ordered)) - 1,
        ),
    )
    return ordered[index]


def _auc(
    labels: tuple[int, ...],
    scores: tuple[float, ...],
) -> AucEvidence:
    if len(labels) != len(scores) or not labels:
        raise ValueError("V37 AUC label/score shape mismatch")
    positives = sum(labels)
    negatives = len(labels) - positives
    if positives == 0 or negatives == 0:
        raise ValueError("V37 AUC requires STOP and TARGET examples")

    ranked = sorted(
        zip(scores, labels, strict=True),
        key=lambda row: row[0],
    )
    rank_sum_positive = 0.0
    index = 0
    while index < len(ranked):
        end = index + 1
        while end < len(ranked) and ranked[end][0] == ranked[index][0]:
            end += 1
        # Ranks are 1-indexed. Tie group receives average rank.
        average_rank = ((index + 1) + end) / 2.0
        rank_sum_positive += average_rank * sum(
            label for _score, label in ranked[index:end]
        )
        index = end

    u_stat = (
        rank_sum_positive
        - positives * (positives + 1) / 2.0
    )
    auc = u_stat / (positives * negatives)
    q1 = auc / (2.0 - auc) if auc < 2.0 else 0.0
    q2 = (
        2.0 * auc * auc / (1.0 + auc)
        if auc > -1.0
        else 0.0
    )
    variance = (
        auc * (1.0 - auc)
        + (positives - 1) * (q1 - auc * auc)
        + (negatives - 1) * (q2 - auc * auc)
    ) / (positives * negatives)
    standard_error = math.sqrt(max(0.0, variance))
    lower = max(0.0, auc - Z_95 * standard_error)
    upper = min(1.0, auc + Z_95 * standard_error)
    return AucEvidence(
        auc=str(auc),
        standard_error=str(standard_error),
        lower_95=str(lower),
        upper_95=str(upper),
        stops=positives,
        targets=negatives,
    )


def _score(
    model: v25.RidgeModel,
    states: tuple[LabeledEntryState, ...],
) -> tuple[float, ...]:
    return tuple(v25._predict(model, row.vector) for row in states)


def _training_q90(
    model: v25.RidgeModel,
    states: tuple[LabeledEntryState, ...],
) -> float:
    return _quantile(_score(model, states), RISK_QUANTILE)


def _heldout_report(
    *,
    heldout: str,
    states_by_period: dict[str, tuple[LabeledEntryState, ...]],
    models: dict[str, v25.RidgeModel],
) -> HeldoutSeparability:
    trainers = tuple(period for period in states_by_period if period != heldout)
    if len(trainers) != 2:
        raise ValueError("V37 requires exactly two external trainer periods")
    trainer_a, trainer_b = trainers
    heldout_states = states_by_period[heldout]
    labels = tuple(
        1 if row.label == LABEL_STOP else 0
        for row in heldout_states
    )
    stops = sum(labels)
    targets = len(labels) - stops
    if stops == 0 or targets == 0:
        raise ValueError("V37 heldout lacks STOP or TARGET class")

    scores_a = _score(models[trainer_a], heldout_states)
    scores_b = _score(models[trainer_b], heldout_states)
    consensus = tuple(
        (a + b) / 2.0
        for a, b in zip(scores_a, scores_b, strict=True)
    )
    auc_a = _auc(labels, scores_a)
    auc_b = _auc(labels, scores_b)
    auc_consensus = _auc(labels, consensus)

    threshold_a = _training_q90(
        models[trainer_a],
        states_by_period[trainer_a],
    )
    threshold_b = _training_q90(
        models[trainer_b],
        states_by_period[trainer_b],
    )
    selected_indexes = tuple(
        index
        for index, (score_a, score_b) in enumerate(
            zip(scores_a, scores_b, strict=True)
        )
        if score_a >= threshold_a and score_b >= threshold_b
    )
    selected_stops = sum(labels[index] for index in selected_indexes)
    selected_targets = len(selected_indexes) - selected_stops

    base_prevalence = stops / len(labels)
    precision = (
        None
        if not selected_indexes
        else selected_stops / len(selected_indexes)
    )
    stop_recall = selected_stops / stops
    target_preservation = (targets - selected_targets) / targets
    precision_lift = (
        None
        if precision is None or base_prevalence == 0.0
        else precision / base_prevalence
    )

    return HeldoutSeparability(
        heldout_period=heldout,
        trainer_a_period=trainer_a,
        trainer_b_period=trainer_b,
        feature_dimension=models[trainer_a].feature_dimension,
        evaluated_states=len(labels),
        stops=stops,
        targets=targets,
        stop_prevalence=str(base_prevalence),
        trainer_a_auc=auc_a,
        trainer_b_auc=auc_b,
        consensus_mean_auc=auc_consensus,
        trainer_a_q90_training_threshold=str(threshold_a),
        trainer_b_q90_training_threshold=str(threshold_b),
        dual_world_top_decile_selected=len(selected_indexes),
        dual_world_top_decile_stops=selected_stops,
        dual_world_top_decile_targets=selected_targets,
        dual_world_stop_precision=None if precision is None else str(precision),
        dual_world_stop_recall=str(stop_recall),
        dual_world_target_count_preservation=str(target_preservation),
        dual_world_precision_lift_vs_base=(
            None if precision_lift is None else str(precision_lift)
        ),
        both_external_auc_lower95_above_chance=(
            float(auc_a.lower_95) > 0.5
            and float(auc_b.lower_95) > 0.5
        ),
        consensus_auc_lower95_above_chance=(
            float(auc_consensus.lower_95) > 0.5
        ),
        target_count_preservation_at_least_90pct=(
            target_preservation >= 0.90
        ),
        risk_tail_enriched_above_base=(
            precision is not None and precision > base_prevalence
        ),
    )


def build_report(
    development_root: Path,
    validation_root: Path,
    reserved_root: Path,
    development_validation_context_root: Path,
    reserved_context_root: Path,
) -> tuple[dict[str, Any], tuple[LabeledEntryState, ...]]:
    windows, contextual_model = v13._load_windows(
        development_root,
        validation_root,
        reserved_root,
        development_validation_context_root,
        reserved_context_root,
    )

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
        states_by_period: dict[
            str, tuple[LabeledEntryState, ...]
        ] = {}
        for period, (ledgers, contexts) in windows.items():
            states_by_period[period] = _surface_entry_states(
                period=period,
                ledgers=ledgers,
                contexts=contexts,
                contextual_model=contextual_model,
            )
    finally:
        v11._SIMULTANEOUS.clear()
        v11._SIMULTANEOUS.update(previous)

    models = {
        period: v25._fit_model(
            period=f"{period}:FULL_STOP_RISK",
            examples=_training_examples(states),
        )
        for period, states in states_by_period.items()
    }
    heldout = tuple(
        _heldout_report(
            heldout=period,
            states_by_period=states_by_period,
            models=models,
        )
        for period in states_by_period
    )

    transport_supported = all(
        row.both_external_auc_lower95_above_chance
        and row.consensus_auc_lower95_above_chance
        and row.target_count_preservation_at_least_90pct
        and row.risk_tail_enriched_above_base
        for row in heldout
    )
    all_states = tuple(
        row
        for period in states_by_period
        for row in states_by_period[period]
    )

    report = {
        "identity": IDENTITY,
        "evaluation": "PREENTRY_STOP_VS_TARGET_CAUSAL_SEPARABILITY",
        "feature_source": "V11_COMPLETE_CAUSAL_PREENTRY_VECTOR",
        "feature_dimension": EXPECTED_V11_FEATURE_DIMENSION,
        "training_label": "ORIGINAL_EXIT_REASON_STOP_VS_TARGET",
        "stop_target_labels_used_as_features": False,
        "current_outcome_visible_to_features": False,
        "future_exit_visible_to_features": False,
        "future_mfe_mae_visible_to_features": False,
        "symbol_identity_feature_used": False,
        "date_identity_feature_used": False,
        "two_external_worlds_required": True,
        "l2_prior_strength_effective_trades": str(v25.L2_PRIOR_STRENGTH),
        "fixed_diagnostic_risk_quantile": str(RISK_QUANTILE),
        "threshold_grid_searched": False,
        "policy_economics_run": False,
        "admission_changed": False,
        "sizing_changed": False,
        "protection_changed": False,
        "fresh_holdout_opened": False,
        "heldout_results": [asdict(row) for row in heldout],
        "representation_transport_supported": transport_supported,
        "candidate_count": 0,
        "runtime_policy_candidate": False,
        "trader_certified": False,
        "next_phase": (
            "PREDECLARE_CAUSAL_WINNER_PRESERVING_FULL_STOP_ABSTENTION"
            if transport_supported
            else "PREENTRY_V11_REPRESENTATION_FALSIFIED_REQUIRE_NEW_CAUSAL_INFORMATION"
        ),
    }
    return report, all_states


def write_report(
    report: dict[str, Any],
    states: tuple[LabeledEntryState, ...],
    output: Path,
) -> None:
    output.mkdir(parents=True, exist_ok=True)
    stem = "capitalizer-preentry-full-stop-causal-separability-v37"
    (output / f"{stem}.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    with (output / f"{stem}-states.jsonl").open(
        "w",
        encoding="utf-8",
    ) as handle:
        for row in states:
            handle.write(json.dumps(asdict(row), sort_keys=True) + "\n")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("development_root", type=Path)
    parser.add_argument("validation_root", type=Path)
    parser.add_argument("reserved_root", type=Path)
    parser.add_argument("development_validation_context_root", type=Path)
    parser.add_argument("reserved_context_root", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()

    report, states = build_report(
        args.development_root,
        args.validation_root,
        args.reserved_root,
        args.development_validation_context_root,
        args.reserved_context_root,
    )
    write_report(report, states, args.output)
    print(json.dumps(report, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

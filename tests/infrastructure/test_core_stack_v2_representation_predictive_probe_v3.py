from __future__ import annotations

from datetime import UTC, datetime, timedelta
from math import cos, sin

import pytest

from qore.infrastructure.core_stack_v2.representation_discovery_engine import (
    RepresentationEpisode,
    RepresentationValue,
)
from qore.infrastructure.core_stack_v2.representation_discovery_evaluation import (
    RepresentationEvaluationTarget,
)
from qore.infrastructure.core_stack_v2.representation_predictive_probe_v3 import (
    evaluate_predictive_incremental_probe,
    fit_predictive_incremental_probe,
    predictive_representation_fingerprint,
)
from qore.infrastructure.core_stack_v2.representation_predictive_v3 import (
    PredictiveRepresentationPolicy,
    PredictiveTransitionEpisode,
    fit_predictive_representation,
)

BASE = datetime(2020, 1, 1, tzinfo=UTC)


def _partition(
    partition: str,
    *,
    start_days: int,
    phase: float = 0.0,
    count: int = 128,
) -> tuple[
    tuple[PredictiveTransitionEpisode, ...],
    tuple[RepresentationEpisode, ...],
    tuple[RepresentationEvaluationTarget, ...],
]:
    transitions: list[PredictiveTransitionEpisode] = []
    episodes: list[RepresentationEpisode] = []
    targets: list[RepresentationEvaluationTarget] = []
    for index in range(count):
        source_at = BASE + timedelta(days=start_days, minutes=index * 60)
        future_at = source_at + timedelta(minutes=30)
        ontology = sin(index * 0.07 + phase)
        driver = sin(index * 0.17 + phase) + 0.35 * cos(index * 0.05)
        nuisance = 1.8 * cos(index * 0.31 + 1.2 * phase)
        source = RepresentationEpisode(
            episode_id=f"{partition}-{index}",
            as_of=source_at,
            partition=partition,
            features=(
                RepresentationValue("PREDICTIVE_DRIVER", driver + 0.2 * ontology),
                RepresentationValue("HIGH_VARIANCE_NUISANCE", nuisance),
            ),
            ontology=(RepresentationValue("ONTOLOGY_BASE", ontology),),
        )
        future_ontology = ontology + 0.03 * cos(index * 0.19)
        future = RepresentationEpisode(
            episode_id=f"{partition}-F-{index}",
            as_of=future_at,
            partition=partition,
            features=(
                RepresentationValue(
                    "PREDICTIVE_DRIVER",
                    driver + 0.85 * driver + 0.2 * future_ontology,
                ),
                RepresentationValue(
                    "HIGH_VARIANCE_NUISANCE",
                    nuisance + sin(index * 0.79 + phase),
                ),
            ),
            ontology=(RepresentationValue("ONTOLOGY_BASE", future_ontology),),
        )
        transitions.append(
            PredictiveTransitionEpisode(
                source=source,
                future=future,
                horizon_minutes=30,
            )
        )
        episodes.append(source)
        targets.append(
            RepresentationEvaluationTarget(
                episode_id=source.episode_id,
                observed_at=future_at,
                value=0.9 * driver + 0.1 * ontology,
            )
        )
    return tuple(transitions), tuple(episodes), tuple(targets)


def _model_and_data():
    raw = {
        "r8": _partition("r8", start_days=0),
        "r6": _partition("r6", start_days=200, phase=0.15),
        "r5": _partition("r5", start_days=400, phase=-0.12),
    }
    transitions = {name: value[0] for name, value in raw.items()}
    fitted_at = max(
        item.future.as_of
        for rows in transitions.values()
        for item in rows
    )
    model = fit_predictive_representation(
        fitted_at=fitted_at,
        discovery_partition="r8",
        development_partitions=("r6", "r5"),
        transitions_by_partition=transitions,
        policy=PredictiveRepresentationPolicy(
            maximum_concepts=2,
            candidate_multiplier=3,
            minimum_transition_count_per_partition=64,
            minimum_predictive_strength_bps=10,
            minimum_future_profile_alignment_bps=5_000,
            minimum_predictive_strength_ratio=0.25,
            maximum_predictive_strength_ratio=3.0,
            minimum_source_scale_ratio=0.25,
            maximum_source_scale_ratio=3.0,
            maximum_source_median_shift_scale=2.0,
        ),
    )
    assert model.concepts
    return model, raw


def test_predictive_probe_is_deterministic_and_authority_free() -> None:
    model, raw = _model_and_data()
    episodes = raw["r8"][1] + raw["r6"][1]
    targets = raw["r8"][2] + raw["r6"][2]
    fitted_at = max(item.observed_at for item in targets)

    first = fit_predictive_incremental_probe(
        model=model,
        fitted_at=fitted_at,
        calibration_partitions=("r8", "r6"),
        target_name="SYNTHETIC_TEMPORAL_TARGET",
        episodes=episodes,
        targets=targets,
    )
    second = fit_predictive_incremental_probe(
        model=model,
        fitted_at=fitted_at,
        calibration_partitions=("r8", "r6"),
        target_name="SYNTHETIC_TEMPORAL_TARGET",
        episodes=episodes,
        targets=targets,
    )

    assert first == second
    assert first.representation_fingerprint == predictive_representation_fingerprint(
        model
    )
    assert first.representation_training_future_only is True
    assert first.runtime_future_market_used is False
    assert first.holdout_used_for_fit is False
    assert first.identity_used is False
    assert first.knowledge_promotion_authority is False
    assert first.methodology_authority is False
    assert first.sizing_authority is False
    assert first.risk_authority is False
    assert first.order_authority is False
    assert first.execution_authority is False


def test_predictive_probe_adds_information_on_unseen_partition_without_refit() -> None:
    model, raw = _model_and_data()
    calibration_episodes = raw["r8"][1] + raw["r6"][1]
    calibration_targets = raw["r8"][2] + raw["r6"][2]
    probe = fit_predictive_incremental_probe(
        model=model,
        fitted_at=max(item.observed_at for item in calibration_targets),
        calibration_partitions=("r8", "r6"),
        target_name="SYNTHETIC_TEMPORAL_TARGET",
        episodes=calibration_episodes,
        targets=calibration_targets,
    )
    evaluation = evaluate_predictive_incremental_probe(
        model=model,
        probe=probe,
        partition="r5",
        episodes=raw["r5"][1],
        targets=raw["r5"][2],
    )

    assert evaluation.incremental_information_bps > 0
    assert evaluation.augmented_mse_micros < evaluation.baseline_mse_micros
    assert evaluation.holdout_refit is False
    assert evaluation.runtime_future_market_used is False
    assert evaluation.identity_used is False
    assert evaluation.knowledge_promotion_authority is False


def test_predictive_probe_rejects_future_calibration_target() -> None:
    model, raw = _model_and_data()
    targets = raw["r8"][2]
    with pytest.raises(ValueError, match="future calibration target"):
        fit_predictive_incremental_probe(
            model=model,
            fitted_at=max(item.as_of for item in raw["r8"][1]),
            calibration_partitions=("r8",),
            target_name="SYNTHETIC_TEMPORAL_TARGET",
            episodes=raw["r8"][1],
            targets=targets,
        )


def test_predictive_probe_cannot_refit_evaluation_partition() -> None:
    model, raw = _model_and_data()
    targets = raw["r8"][2]
    probe = fit_predictive_incremental_probe(
        model=model,
        fitted_at=max(item.observed_at for item in targets),
        calibration_partitions=("r8",),
        target_name="SYNTHETIC_TEMPORAL_TARGET",
        episodes=raw["r8"][1],
        targets=targets,
    )

    with pytest.raises(ValueError, match="used for probe fitting"):
        evaluate_predictive_incremental_probe(
            model=model,
            probe=probe,
            partition="r8",
            episodes=raw["r8"][1],
            targets=targets,
        )

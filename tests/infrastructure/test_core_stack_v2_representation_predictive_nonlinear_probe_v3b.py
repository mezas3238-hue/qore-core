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
from qore.infrastructure.core_stack_v2.representation_predictive_nonlinear_probe_v3b import (
    BASIS_ID,
    evaluate_predictive_second_order_probe,
    fit_predictive_second_order_probe,
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
    count: int = 160,
):
    transitions = []
    episodes = []
    targets = []
    for index in range(count):
        source_at = BASE + timedelta(days=start_days, minutes=index * 60)
        future_at = source_at + timedelta(minutes=30)
        ontology = sin(index * 0.07 + phase)
        driver = sin(index * 0.19 + phase) + 0.30 * cos(index * 0.05)
        nuisance = 1.5 * cos(index * 0.37 + phase)

        source = RepresentationEpisode(
            episode_id=f"{partition}-{index}",
            as_of=source_at,
            partition=partition,
            features=(
                RepresentationValue("TEMPORAL_DRIVER", driver + 0.15 * ontology),
                RepresentationValue("NUISANCE", nuisance),
            ),
            ontology=(RepresentationValue("ONTOLOGY_BASE", ontology),),
        )
        future = RepresentationEpisode(
            episode_id=f"{partition}-F-{index}",
            as_of=future_at,
            partition=partition,
            features=(
                RepresentationValue(
                    "TEMPORAL_DRIVER",
                    driver + 0.90 * driver + 0.15 * ontology,
                ),
                RepresentationValue(
                    "NUISANCE",
                    nuisance + 0.5 * sin(index * 0.71 + phase),
                ),
            ),
            ontology=(RepresentationValue("ONTOLOGY_BASE", ontology),),
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
                value=0.85 * (driver * driver) + 0.10 * ontology,
            )
        )
    return tuple(transitions), tuple(episodes), tuple(targets)


def _model_and_data():
    raw = {
        "r8": _partition("r8", start_days=0),
        "r6": _partition("r6", start_days=200, phase=0.13),
        "r5": _partition("r5", start_days=400, phase=-0.10),
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
            minimum_transition_count_per_partition=80,
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


def test_v3b_decodes_quadratic_latent_information_out_of_partition() -> None:
    model, raw = _model_and_data()
    calibration_episodes = raw["r8"][1] + raw["r6"][1]
    calibration_targets = raw["r8"][2] + raw["r6"][2]
    probe = fit_predictive_second_order_probe(
        model=model,
        fitted_at=max(item.observed_at for item in calibration_targets),
        calibration_partitions=("r8", "r6"),
        target_name="SYNTHETIC_NONLINEAR_FUTURE",
        episodes=calibration_episodes,
        targets=calibration_targets,
    )
    evaluation = evaluate_predictive_second_order_probe(
        model=model,
        probe=probe,
        partition="r5",
        episodes=raw["r5"][1],
        targets=raw["r5"][2],
    )

    assert probe.basis_id == BASIS_ID
    assert evaluation.incremental_information_bps > 0
    assert evaluation.augmented_mse_micros < evaluation.baseline_mse_micros
    assert evaluation.holdout_refit is False
    assert evaluation.runtime_future_market_used is False
    assert evaluation.identity_used is False
    assert evaluation.knowledge_promotion_authority is False


def test_v3b_baseline_has_symmetric_second_order_ontology_capacity() -> None:
    model, raw = _model_and_data()
    episodes = raw["r8"][1] + raw["r6"][1]
    targets = raw["r8"][2] + raw["r6"][2]
    probe = fit_predictive_second_order_probe(
        model=model,
        fitted_at=max(item.observed_at for item in targets),
        calibration_partitions=("r8", "r6"),
        target_name="SYNTHETIC_NONLINEAR_FUTURE",
        episodes=episodes,
        targets=targets,
    )

    ontology_count = len(model.ontology_names)
    expected_baseline_width = (
        1
        + ontology_count
        + ontology_count
        + ontology_count * (ontology_count - 1) // 2
    )
    assert len(probe.baseline_coefficients_micros) == expected_baseline_width
    assert len(probe.augmented_coefficients_micros) > expected_baseline_width
    assert probe.representation_training_future_only is True
    assert probe.runtime_future_market_used is False
    assert probe.holdout_used_for_fit is False
    assert probe.identity_used is False
    assert probe.knowledge_promotion_authority is False
    assert probe.methodology_authority is False
    assert probe.sizing_authority is False
    assert probe.risk_authority is False
    assert probe.order_authority is False
    assert probe.execution_authority is False


def test_v3b_is_deterministic() -> None:
    model, raw = _model_and_data()
    episodes = raw["r8"][1] + raw["r6"][1]
    targets = raw["r8"][2] + raw["r6"][2]
    fitted_at = max(item.observed_at for item in targets)

    first = fit_predictive_second_order_probe(
        model=model,
        fitted_at=fitted_at,
        calibration_partitions=("r8", "r6"),
        target_name="SYNTHETIC_NONLINEAR_FUTURE",
        episodes=episodes,
        targets=targets,
    )
    second = fit_predictive_second_order_probe(
        model=model,
        fitted_at=fitted_at,
        calibration_partitions=("r8", "r6"),
        target_name="SYNTHETIC_NONLINEAR_FUTURE",
        episodes=episodes,
        targets=targets,
    )
    assert first == second


def test_v3b_rejects_future_calibration_target() -> None:
    model, raw = _model_and_data()
    targets = raw["r8"][2]
    with pytest.raises(ValueError, match="future calibration target"):
        fit_predictive_second_order_probe(
            model=model,
            fitted_at=max(item.as_of for item in raw["r8"][1]),
            calibration_partitions=("r8",),
            target_name="SYNTHETIC_NONLINEAR_FUTURE",
            episodes=raw["r8"][1],
            targets=targets,
        )


def test_v3b_cannot_evaluate_partition_used_for_fit() -> None:
    model, raw = _model_and_data()
    targets = raw["r8"][2]
    probe = fit_predictive_second_order_probe(
        model=model,
        fitted_at=max(item.observed_at for item in targets),
        calibration_partitions=("r8",),
        target_name="SYNTHETIC_NONLINEAR_FUTURE",
        episodes=raw["r8"][1],
        targets=targets,
    )
    with pytest.raises(ValueError, match="used for probe fitting"):
        evaluate_predictive_second_order_probe(
            model=model,
            probe=probe,
            partition="r8",
            episodes=raw["r8"][1],
            targets=targets,
        )

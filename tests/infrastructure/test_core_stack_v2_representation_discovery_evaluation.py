from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from qore.infrastructure.core_stack_v2.representation_discovery_engine import (
    RepresentationDiscoveryPolicy,
    RepresentationEpisode,
    RepresentationValue,
    fit_representation_discovery,
)
from qore.infrastructure.core_stack_v2.representation_discovery_evaluation import (
    RepresentationEvaluationTarget,
    evaluate_incremental_representation,
    fit_incremental_representation_probe,
)

BASE = datetime(2026, 9, 26, 12, 0, tzinfo=UTC)


def _episode(
    index: int,
    *,
    partition: str,
    offset_minutes: int,
) -> tuple[RepresentationEpisode, RepresentationEvaluationTarget]:
    ontology = ((index % 19) - 9) / 5.0
    hidden = 1.0 if (index // 7) % 2 == 0 else -1.0
    as_of = BASE + timedelta(minutes=offset_minutes + index)
    episode = RepresentationEpisode(
        episode_id=f"{partition}-{index}",
        as_of=as_of,
        partition=partition,
        features=(
            RepresentationValue(
                "GENERIC_SEQUENCE_CURVATURE",
                0.80 * ontology + 2.25 * hidden,
            ),
            RepresentationValue(
                "GENERIC_ROTATION_ASYMMETRY",
                -0.40 * ontology + 1.75 * hidden,
            ),
            RepresentationValue(
                "GENERIC_RANGE_TEXTURE",
                0.65 * ontology - 0.15 * hidden,
            ),
        ),
        ontology=(
            RepresentationValue("ONTOLOGY_STRUCTURE", ontology),
            RepresentationValue("ONTOLOGY_VOLATILITY", ontology * 0.30),
        ),
    )
    target = RepresentationEvaluationTarget(
        episode_id=episode.episode_id,
        observed_at=as_of + timedelta(minutes=30),
        value=900.0 * hidden + 80.0 * ontology,
    )
    return episode, target


def _partition(
    count: int,
    *,
    partition: str,
    offset_minutes: int,
) -> tuple[
    tuple[RepresentationEpisode, ...],
    tuple[RepresentationEvaluationTarget, ...],
]:
    pairs = [
        _episode(
            index,
            partition=partition,
            offset_minutes=offset_minutes,
        )
        for index in range(count)
    ]
    return (
        tuple(item[0] for item in pairs),
        tuple(item[1] for item in pairs),
    )


def _fit():
    r8, r8_targets = _partition(
        800,
        partition="R8",
        offset_minutes=0,
    )
    model = fit_representation_discovery(
        fitted_at=BASE + timedelta(minutes=900),
        episodes=r8,
        policy=RepresentationDiscoveryPolicy(
            maximum_concepts=3,
            minimum_episode_count=500,
            minimum_component_variance_bps=100,
        ),
    )
    probe = fit_incremental_representation_probe(
        model=model,
        fitted_at=BASE + timedelta(minutes=900),
        calibration_partition="R8",
        target_name="GENERIC_FUTURE_STATE",
        episodes=r8,
        targets=r8_targets,
    )
    return model, probe


def test_latent_representation_adds_oos_information_beyond_ontology() -> None:
    model, probe = _fit()
    r6, r6_targets = _partition(
        500,
        partition="R6",
        offset_minutes=2_000,
    )

    evaluation = evaluate_incremental_representation(
        model=model,
        probe=probe,
        partition="R6",
        episodes=r6,
        targets=r6_targets,
    )

    assert evaluation.sample_count == 500
    assert evaluation.augmented_mse_micros < evaluation.baseline_mse_micros
    assert evaluation.incremental_information_bps > 8_000
    assert evaluation.holdout_refit is False
    assert evaluation.identity_used is False
    assert evaluation.knowledge_promotion_authority is False


def test_probe_preserves_target_blind_representation_and_no_authority() -> None:
    _model, probe = _fit()

    assert probe.representation_target_blind is True
    assert probe.holdout_used_for_fit is False
    assert probe.identity_used is False
    assert probe.knowledge_promotion_authority is False
    assert probe.methodology_authority is False
    assert probe.sizing_authority is False
    assert probe.risk_authority is False
    assert probe.order_authority is False
    assert probe.execution_authority is False


def test_probe_rejects_future_calibration_target() -> None:
    r8, targets = _partition(
        800,
        partition="R8",
        offset_minutes=0,
    )
    model = fit_representation_discovery(
        fitted_at=BASE + timedelta(minutes=900),
        episodes=r8,
    )
    poisoned = (
        *targets[:-1],
        RepresentationEvaluationTarget(
            episode_id=targets[-1].episode_id,
            observed_at=BASE + timedelta(days=2),
            value=targets[-1].value,
        ),
    )

    with pytest.raises(ValueError, match="future calibration target"):
        fit_incremental_representation_probe(
            model=model,
            fitted_at=BASE + timedelta(minutes=900),
            calibration_partition="R8",
            target_name="GENERIC_FUTURE_STATE",
            episodes=r8,
            targets=poisoned,
        )


def test_holdout_cannot_be_evaluated_as_calibration_partition() -> None:
    model, probe = _fit()
    r8, targets = _partition(
        100,
        partition="R8",
        offset_minutes=2_000,
    )

    with pytest.raises(ValueError, match="later partition"):
        evaluate_incremental_representation(
            model=model,
            probe=probe,
            partition="R8",
            episodes=r8,
            targets=targets,
        )

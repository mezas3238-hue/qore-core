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
from qore.infrastructure.core_stack_v2.representation_invariance_probe_v2 import (
    evaluate_invariant_incremental_probe,
    fit_invariant_incremental_probe,
    invariant_representation_fingerprint,
)
from qore.infrastructure.core_stack_v2.representation_invariance_v2 import (
    InvariantRepresentationPolicy,
    fit_invariant_representation,
)

BASE = datetime(2020, 1, 1, tzinfo=UTC)


def _episodes(
    partition: str,
    *,
    start_days: int,
    unstable_shift: float = 0.0,
    count: int = 96,
) -> tuple[RepresentationEpisode, ...]:
    rows: list[RepresentationEpisode] = []
    for index in range(count):
        ontology = sin(index * 0.05)
        stable = sin(index * 0.19) + 0.35 * cos(index * 0.07)
        stable_second = 0.8 * stable + 0.15 * sin(index * 0.43)
        unstable = cos(index * 0.11) + unstable_shift
        rows.append(
            RepresentationEpisode(
                episode_id=f"{partition}-{index}",
                as_of=BASE + timedelta(days=start_days, minutes=index),
                partition=partition,
                features=(
                    RepresentationValue(
                        "STABLE_HIDDEN",
                        stable + 0.20 * ontology,
                    ),
                    RepresentationValue(
                        "STABLE_SECOND",
                        stable_second - 0.10 * ontology,
                    ),
                    RepresentationValue(
                        "UNSTABLE_LEVEL",
                        unstable + 0.05 * ontology,
                    ),
                ),
                ontology=(
                    RepresentationValue("ONTOLOGY_BASE", ontology),
                ),
            )
        )
    return tuple(rows)


def _targets(
    rows: tuple[RepresentationEpisode, ...],
) -> tuple[RepresentationEvaluationTarget, ...]:
    targets: list[RepresentationEvaluationTarget] = []
    for row in rows:
        features = {item.name: item.value for item in row.features}
        ontology = {item.name: item.value for item in row.ontology}
        targets.append(
            RepresentationEvaluationTarget(
                episode_id=row.episode_id,
                observed_at=row.as_of + timedelta(minutes=30),
                value=(
                    0.85 * features["STABLE_HIDDEN"]
                    + 0.10 * ontology["ONTOLOGY_BASE"]
                ),
            )
        )
    return tuple(targets)


def _model():
    partitions = {
        "r8": _episodes("r8", start_days=0),
        "r6": _episodes("r6", start_days=200, unstable_shift=12.0),
        "r5": _episodes("r5", start_days=400, unstable_shift=-11.0),
    }
    fitted_at = max(
        item.as_of
        for rows in partitions.values()
        for item in rows
    )
    model = fit_invariant_representation(
        fitted_at=fitted_at,
        discovery_partition="r8",
        development_partitions=("r6", "r5"),
        episodes_by_partition=partitions,
        policy=InvariantRepresentationPolicy(
            maximum_concepts=2,
            candidate_multiplier=3,
            minimum_episode_count_per_partition=48,
            minimum_candidate_variance_bps=25,
        ),
    )
    assert model.concepts
    return model, partitions


def test_probe_fingerprint_is_deterministic_and_authority_free() -> None:
    model, partitions = _model()
    calibration_episodes = partitions["r8"] + partitions["r6"]
    calibration_targets = _targets(partitions["r8"]) + _targets(partitions["r6"])
    fitted_at = max(item.observed_at for item in calibration_targets)

    first = fit_invariant_incremental_probe(
        model=model,
        fitted_at=fitted_at,
        calibration_partitions=("r8", "r6"),
        target_name="SYNTHETIC_FUTURE_STATE",
        episodes=calibration_episodes,
        targets=calibration_targets,
    )
    second = fit_invariant_incremental_probe(
        model=model,
        fitted_at=fitted_at,
        calibration_partitions=("r8", "r6"),
        target_name="SYNTHETIC_FUTURE_STATE",
        episodes=calibration_episodes,
        targets=calibration_targets,
    )

    assert first == second
    assert first.representation_fingerprint == invariant_representation_fingerprint(
        model
    )
    assert len(first.probe_fingerprint) == 64
    assert first.representation_target_blind is True
    assert first.holdout_used_for_fit is False
    assert first.identity_used is False
    assert first.knowledge_promotion_authority is False
    assert first.methodology_authority is False
    assert first.sizing_authority is False
    assert first.risk_authority is False
    assert first.order_authority is False
    assert first.execution_authority is False


def test_probe_adds_information_on_unseen_target_labels_without_refit() -> None:
    model, partitions = _model()
    calibration_episodes = partitions["r8"] + partitions["r6"]
    calibration_targets = _targets(partitions["r8"]) + _targets(partitions["r6"])
    probe = fit_invariant_incremental_probe(
        model=model,
        fitted_at=max(item.observed_at for item in calibration_targets),
        calibration_partitions=("r8", "r6"),
        target_name="SYNTHETIC_FUTURE_STATE",
        episodes=calibration_episodes,
        targets=calibration_targets,
    )

    evaluation = evaluate_invariant_incremental_probe(
        model=model,
        probe=probe,
        partition="r5",
        episodes=partitions["r5"],
        targets=_targets(partitions["r5"]),
    )

    assert evaluation.sample_count == len(partitions["r5"])
    assert evaluation.incremental_information_bps > 0
    assert evaluation.augmented_mse_micros < evaluation.baseline_mse_micros
    assert evaluation.holdout_refit is False
    assert evaluation.identity_used is False
    assert evaluation.knowledge_promotion_authority is False


def test_probe_rejects_future_calibration_target() -> None:
    model, partitions = _model()
    targets = _targets(partitions["r8"])
    fitted_at = max(item.as_of for item in partitions["r8"])

    with pytest.raises(ValueError, match="future calibration target"):
        fit_invariant_incremental_probe(
            model=model,
            fitted_at=fitted_at,
            calibration_partitions=("r8",),
            target_name="SYNTHETIC_FUTURE_STATE",
            episodes=partitions["r8"],
            targets=targets,
        )


def test_probe_cannot_evaluate_partition_used_for_fit() -> None:
    model, partitions = _model()
    targets = _targets(partitions["r8"])
    probe = fit_invariant_incremental_probe(
        model=model,
        fitted_at=max(item.observed_at for item in targets),
        calibration_partitions=("r8",),
        target_name="SYNTHETIC_FUTURE_STATE",
        episodes=partitions["r8"],
        targets=targets,
    )

    with pytest.raises(ValueError, match="used for probe fitting"):
        evaluate_invariant_incremental_probe(
            model=model,
            probe=probe,
            partition="r8",
            episodes=partitions["r8"],
            targets=targets,
        )

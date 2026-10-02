from __future__ import annotations

from datetime import UTC, datetime, timedelta
from math import cos, sin

import pytest

from qore.infrastructure.core_stack_v2.representation_discovery_engine import (
    RepresentationEpisode,
    RepresentationValue,
)
from qore.infrastructure.core_stack_v2.representation_predictive_v3 import (
    PredictiveRepresentationPolicy,
    PredictiveTransitionEpisode,
    fit_predictive_representation,
    project_predictive_representation,
)

BASE = datetime(2020, 1, 1, tzinfo=UTC)


def _transition_partition(
    partition: str,
    *,
    start_days: int,
    phase: float = 0.0,
    noise_scale: float = 1.0,
    count: int = 128,
) -> tuple[PredictiveTransitionEpisode, ...]:
    rows: list[PredictiveTransitionEpisode] = []
    for index in range(count):
        source_at = BASE + timedelta(days=start_days, minutes=index * 60)
        future_at = source_at + timedelta(minutes=30)

        ontology = sin(index * 0.07 + phase)
        driver = sin(index * 0.17 + phase) + 0.35 * cos(index * 0.05)
        second = 0.75 * driver + 0.12 * sin(index * 0.41 + phase)
        nuisance = noise_scale * (
            2.4 * cos(index * 0.31 + 1.7 * phase)
            + 1.8 * sin(index * 0.47)
        )

        source = RepresentationEpisode(
            episode_id=f"{partition}-S-{index}",
            as_of=source_at,
            partition=partition,
            features=(
                RepresentationValue(
                    "PREDICTIVE_DRIVER",
                    driver + 0.20 * ontology,
                ),
                RepresentationValue(
                    "PREDICTIVE_SECOND",
                    second - 0.10 * ontology,
                ),
                RepresentationValue(
                    "HIGH_VARIANCE_NUISANCE",
                    nuisance,
                ),
            ),
            ontology=(
                RepresentationValue("ONTOLOGY_BASE", ontology),
            ),
        )

        next_driver = driver + 0.90 * driver + 0.08 * sin(index * 0.13)
        next_second = second + 0.60 * driver + 0.05 * cos(index * 0.23)
        next_nuisance = nuisance + noise_scale * sin(index * 0.79 + phase)
        future_ontology = ontology + 0.03 * cos(index * 0.19)
        future = RepresentationEpisode(
            episode_id=f"{partition}-F-{index}",
            as_of=future_at,
            partition=partition,
            features=(
                RepresentationValue(
                    "PREDICTIVE_DRIVER",
                    next_driver + 0.20 * future_ontology,
                ),
                RepresentationValue(
                    "PREDICTIVE_SECOND",
                    next_second - 0.10 * future_ontology,
                ),
                RepresentationValue(
                    "HIGH_VARIANCE_NUISANCE",
                    next_nuisance,
                ),
            ),
            ontology=(
                RepresentationValue("ONTOLOGY_BASE", future_ontology),
            ),
        )
        rows.append(
            PredictiveTransitionEpisode(
                source=source,
                future=future,
                horizon_minutes=30,
            )
        )
    return tuple(rows)


def _policy() -> PredictiveRepresentationPolicy:
    return PredictiveRepresentationPolicy(
        maximum_concepts=2,
        candidate_multiplier=3,
        minimum_transition_count_per_partition=64,
        minimum_predictive_strength_bps=10,
        minimum_future_profile_alignment_bps=6_000,
        minimum_predictive_strength_ratio=0.35,
        maximum_predictive_strength_ratio=2.50,
        minimum_source_scale_ratio=0.35,
        maximum_source_scale_ratio=2.50,
        maximum_source_median_shift_scale=2.0,
    )


def _partitions() -> dict[str, tuple[PredictiveTransitionEpisode, ...]]:
    return {
        "r8": _transition_partition(
            "r8",
            start_days=0,
            noise_scale=1.0,
        ),
        "r6": _transition_partition(
            "r6",
            start_days=200,
            phase=0.21,
            noise_scale=2.8,
        ),
        "r5": _transition_partition(
            "r5",
            start_days=400,
            phase=-0.17,
            noise_scale=0.55,
        ),
    }


def _fit():
    partitions = _partitions()
    fitted_at = max(
        item.future.as_of
        for rows in partitions.values()
        for item in rows
    )
    model = fit_predictive_representation(
        fitted_at=fitted_at,
        discovery_partition="r8",
        development_partitions=("r6", "r5"),
        transitions_by_partition=partitions,
        policy=_policy(),
    )
    return model, partitions


def test_v3_selects_temporal_driver_not_high_variance_nuisance() -> None:
    model, _partitions_value = _fit()

    assert model.candidate_count >= 1
    assert model.concepts
    assert all(
        diagnostic.passes
        for concept in model.concepts
        for diagnostic in concept.diagnostics
    )
    probes = {
        feature
        for concept in model.concepts
        for feature in (
            *concept.positive_probe_features,
            *concept.negative_probe_features,
        )
    }
    assert {"PREDICTIVE_DRIVER", "PREDICTIVE_SECOND"} & probes
    assert model.training_future_market_used is True
    assert model.runtime_future_market_used is False
    assert model.named_evaluation_target_used is False
    assert model.outcome_used is False
    assert model.pnl_used is False
    assert model.trader_identity_used is False
    assert model.symbol_identity_used is False
    assert model.partition_identity_as_feature_used is False


def test_v3_projection_is_deterministic_and_strictly_as_of() -> None:
    model, partitions = _fit()
    source = partitions["r5"][17].source

    first = project_predictive_representation(
        model=model,
        episode=source,
    )
    second = project_predictive_representation(
        model=model,
        episode=source,
    )

    assert first == second
    assert first.as_of == source.as_of
    assert first.target_used is False
    assert first.future_market_used is False
    assert first.trader_identity_used is False


def test_v3_is_deterministic_with_same_consumed_transitions() -> None:
    partitions = _partitions()
    fitted_at = max(
        item.future.as_of
        for rows in partitions.values()
        for item in rows
    )

    first = fit_predictive_representation(
        fitted_at=fitted_at,
        discovery_partition="r8",
        development_partitions=("r6", "r5"),
        transitions_by_partition=partitions,
        policy=_policy(),
    )
    second = fit_predictive_representation(
        fitted_at=fitted_at,
        discovery_partition="r8",
        development_partitions=("r6", "r5"),
        transitions_by_partition=partitions,
        policy=_policy(),
    )
    assert first == second


def test_v3_rejects_explicit_identity_shortcut() -> None:
    partitions = _partitions()
    row = partitions["r8"][0]
    source = RepresentationEpisode(
        episode_id=row.source.episode_id,
        as_of=row.source.as_of,
        partition=row.source.partition,
        features=(
            *row.source.features,
            RepresentationValue("SYMBOL_ID_HASH", 1.0),
        ),
        ontology=row.source.ontology,
    )
    future = RepresentationEpisode(
        episode_id=row.future.episode_id,
        as_of=row.future.as_of,
        partition=row.future.partition,
        features=(
            *row.future.features,
            RepresentationValue("SYMBOL_ID_HASH", 1.0),
        ),
        ontology=row.future.ontology,
    )
    r8 = list(partitions["r8"])
    r8[0] = PredictiveTransitionEpisode(
        source=source,
        future=future,
        horizon_minutes=30,
    )
    partitions["r8"] = tuple(r8)
    fitted_at = max(
        item.future.as_of
        for rows in partitions.values()
        for item in rows
    )

    with pytest.raises(ValueError, match="identity/outcome shortcut"):
        fit_predictive_representation(
            fitted_at=fitted_at,
            discovery_partition="r8",
            development_partitions=("r6", "r5"),
            transitions_by_partition=partitions,
            policy=_policy(),
        )


def test_transition_requires_exact_frozen_horizon() -> None:
    source = RepresentationEpisode(
        episode_id="S",
        as_of=BASE,
        partition="r8",
        features=(RepresentationValue("A", 1.0),),
        ontology=(RepresentationValue("O", 0.0),),
    )
    future = RepresentationEpisode(
        episode_id="F",
        as_of=BASE + timedelta(minutes=31),
        partition="r8",
        features=(RepresentationValue("A", 2.0),),
        ontology=(RepresentationValue("O", 0.0),),
    )

    with pytest.raises(ValueError, match="horizon mismatch"):
        PredictiveTransitionEpisode(
            source=source,
            future=future,
            horizon_minutes=30,
        )


def test_v3_rejects_training_evidence_after_fitted_at() -> None:
    partitions = _partitions()
    fitted_at = BASE + timedelta(days=300)

    with pytest.raises(
        ValueError,
        match="future training evidence beyond fitted_at",
    ):
        fit_predictive_representation(
            fitted_at=fitted_at,
            discovery_partition="r8",
            development_partitions=("r6", "r5"),
            transitions_by_partition=partitions,
            policy=_policy(),
        )

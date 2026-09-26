from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from qore.infrastructure.core_stack_v2.representation_discovery_engine import (
    RepresentationDiscoveryPolicy,
    RepresentationEpisode,
    RepresentationValue,
    fit_representation_discovery,
    project_representation,
)


BASE = datetime(2026, 9, 26, 12, 0, tzinfo=UTC)


def _episode(
    index: int,
    *,
    partition: str = "R8",
    latent: float | None = None,
) -> RepresentationEpisode:
    ontology = ((index % 17) - 8) / 4.0
    hidden = (
        (1.0 if (index // 5) % 2 == 0 else -1.0)
        if latent is None
        else latent
    )
    return RepresentationEpisode(
        episode_id=f"{partition}-{index}",
        as_of=BASE + timedelta(minutes=index),
        partition=partition,
        features=(
            RepresentationValue(
                "RETURN_SEQUENCE_CURVATURE",
                ontology + 2.0 * hidden,
            ),
            RepresentationValue(
                "CROSS_MARKET_ROTATION",
                -0.75 * ontology + 1.5 * hidden,
            ),
            RepresentationValue(
                "RANGE_PATH_ASYMMETRY",
                0.50 * ontology - 0.10 * hidden,
            ),
        ),
        ontology=(
            RepresentationValue("HUMAN_STRUCTURE", ontology),
            RepresentationValue(
                "HUMAN_VOLATILITY",
                ontology * 0.25,
            ),
        ),
    )


def _fit():
    episodes = tuple(_episode(index) for index in range(800))
    return fit_representation_discovery(
        fitted_at=BASE + timedelta(minutes=801),
        episodes=episodes,
        policy=RepresentationDiscoveryPolicy(
            maximum_concepts=3,
            minimum_episode_count=500,
            minimum_component_variance_bps=100,
        ),
    )


def test_discovers_residual_concept_beyond_existing_ontology() -> None:
    model = _fit()

    assert model.discovery_partition == "R8"
    assert model.episode_count == 800
    assert model.target_used is False
    assert model.future_market_used is False
    assert model.trader_identity_used is False
    assert model.knowledge_promotion_authority is False
    assert model.execution_authority is False
    assert model.concepts

    first = model.concepts[0]
    assert first.concept_id.startswith("LATENT_CONCEPT_")
    assert first.explained_residual_variance_bps > 5_000
    assert first.positive_probe_features
    assert first.positive_cluster_episode_ids
    assert first.negative_cluster_episode_ids


def test_frozen_projection_separates_hidden_sequence_state() -> None:
    model = _fit()
    positive = project_representation(
        model=model,
        episode=_episode(900, partition="R6", latent=2.0),
    )
    negative = project_representation(
        model=model,
        episode=_episode(901, partition="R6", latent=-2.0),
    )

    assert positive.activations
    assert negative.activations
    assert (
        positive.activations[0].activation_milli_z
        > negative.activations[0].activation_milli_z
    )
    assert positive.future_market_used is False
    assert positive.trader_identity_used is False


def test_discovery_is_deterministic() -> None:
    left = _fit()
    right = _fit()

    assert tuple(
        item.concept_id for item in left.concepts
    ) == tuple(
        item.concept_id for item in right.concepts
    )
    assert tuple(
        item.loading_micros for item in left.concepts
    ) == tuple(
        item.loading_micros for item in right.concepts
    )


def test_identity_and_outcome_leakage_names_are_rejected() -> None:
    for forbidden in (
        "TRADER_ID",
        "SETUP_NAME",
        "TRADE_OUTCOME",
        "PNL_R",
        "ENTRY_PRICE",
        "STOP_DISTANCE",
        "TARGET_DISTANCE",
    ):
        with pytest.raises(ValueError, match="leakage"):
            RepresentationValue(forbidden, 1.0)


def test_mixed_discovery_partitions_are_rejected() -> None:
    episodes = tuple(_episode(index) for index in range(799)) + (
        _episode(799, partition="R6"),
    )

    with pytest.raises(ValueError, match="one partition"):
        fit_representation_discovery(
            fitted_at=BASE + timedelta(minutes=801),
            episodes=episodes,
        )


def test_future_discovery_episode_fails_closed() -> None:
    episodes = tuple(_episode(index) for index in range(800))
    with pytest.raises(ValueError, match="future representation evidence"):
        fit_representation_discovery(
            fitted_at=BASE + timedelta(minutes=700),
            episodes=episodes,
        )


def test_projection_rejects_feature_schema_drift() -> None:
    model = _fit()
    episode = RepresentationEpisode(
        episode_id="R6-drift",
        as_of=BASE + timedelta(days=2),
        partition="R6",
        features=(
            RepresentationValue("RETURN_SEQUENCE_CURVATURE", 1.0),
            RepresentationValue("CROSS_MARKET_ROTATION", 1.0),
            RepresentationValue("UNKNOWN_FEATURE", 1.0),
        ),
        ontology=(
            RepresentationValue("HUMAN_STRUCTURE", 1.0),
            RepresentationValue("HUMAN_VOLATILITY", 1.0),
        ),
    )

    with pytest.raises(ValueError, match="schema drift"):
        project_representation(model=model, episode=episode)

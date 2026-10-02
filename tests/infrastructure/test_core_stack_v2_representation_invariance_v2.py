from __future__ import annotations

from datetime import UTC, datetime, timedelta
from math import cos, sin

import pytest

from qore.infrastructure.core_stack_v2.representation_discovery_engine import (
    RepresentationEpisode,
    RepresentationValue,
)
from qore.infrastructure.core_stack_v2.representation_invariance_v2 import (
    InvariantRepresentationPolicy,
    fit_invariant_representation,
    project_invariant_representation,
)

BASE = datetime(2020, 1, 1, tzinfo=UTC)


def _episodes(
    partition: str,
    *,
    start_days: int,
    unstable_shift: float = 0.0,
    unstable_scale: float = 1.0,
    count: int = 96,
) -> tuple[RepresentationEpisode, ...]:
    rows: list[RepresentationEpisode] = []
    for index in range(count):
        ontology = sin(index * 0.05)
        stable = sin(index * 0.19) + 0.35 * cos(index * 0.07)
        stable_second = 0.8 * stable + 0.15 * sin(index * 0.43)
        unstable = unstable_scale * (
            cos(index * 0.11) + 0.30 * sin(index * 0.29)
        ) + unstable_shift
        rows.append(
            RepresentationEpisode(
                episode_id=f"{partition}-{index}",
                as_of=BASE
                + timedelta(days=start_days, minutes=index),
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


def _policy() -> InvariantRepresentationPolicy:
    return InvariantRepresentationPolicy(
        maximum_concepts=2,
        candidate_multiplier=3,
        minimum_episode_count_per_partition=48,
        minimum_candidate_variance_bps=25,
    )


def _development() -> dict[str, tuple[RepresentationEpisode, ...]]:
    return {
        "r8": _episodes("r8", start_days=0),
        "r6": _episodes(
            "r6",
            start_days=200,
            unstable_shift=15.0,
        ),
        "r5": _episodes(
            "r5",
            start_days=400,
            unstable_shift=-12.0,
            unstable_scale=1.7,
        ),
    }


def test_v2_rejects_partition_specific_scale_mode_and_retains_invariant_signal() -> None:
    partitions = _development()
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
        policy=_policy(),
    )

    assert model.candidate_count >= 2
    assert model.rejected_candidate_count >= 1
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
    assert {"STABLE_HIDDEN", "STABLE_SECOND"} & probes
    assert model.target_used is False
    assert model.future_market_used is False
    assert model.outcome_used is False
    assert model.pnl_used is False
    assert model.trader_identity_used is False
    assert model.symbol_identity_used is False
    assert model.partition_identity_as_feature_used is False
    assert model.knowledge_promotion_authority is False
    assert model.methodology_authority is False
    assert model.sizing_authority is False
    assert model.risk_authority is False
    assert model.order_authority is False
    assert model.execution_authority is False


def test_v2_is_deterministic_and_projection_uses_frozen_discovery_transform() -> None:
    partitions = _development()
    fitted_at = max(
        item.as_of
        for rows in partitions.values()
        for item in rows
    )

    first = fit_invariant_representation(
        fitted_at=fitted_at,
        discovery_partition="r8",
        development_partitions=("r6", "r5"),
        episodes_by_partition=partitions,
        policy=_policy(),
    )
    second = fit_invariant_representation(
        fitted_at=fitted_at,
        discovery_partition="r8",
        development_partitions=("r6", "r5"),
        episodes_by_partition=partitions,
        policy=_policy(),
    )
    assert first == second

    episode = partitions["r5"][17]
    projected_first = project_invariant_representation(
        model=first,
        episode=episode,
    )
    projected_second = project_invariant_representation(
        model=first,
        episode=episode,
    )
    assert projected_first == projected_second
    assert projected_first.target_used is False
    assert projected_first.future_market_used is False
    assert projected_first.trader_identity_used is False


def test_v2_development_partitions_are_source_only_not_feature_shortcuts() -> None:
    partitions = _development()
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
        policy=_policy(),
    )

    assert model.discovery_partition == "r8"
    assert model.development_partitions == ("r6", "r5")
    assert set(name.lower() for name in model.feature_names).isdisjoint(
        {"r8", "r6", "r5"}
    )
    assert model.partition_identity_as_feature_used is False


def test_v2_rejects_explicit_symbol_or_partition_identity_feature() -> None:
    rows = list(_episodes("r8", start_days=0))
    first = rows[0]
    rows[0] = RepresentationEpisode(
        episode_id=first.episode_id,
        as_of=first.as_of,
        partition=first.partition,
        features=(
            *first.features,
            RepresentationValue("SYMBOL_ID_HASH", 1.0),
        ),
        ontology=first.ontology,
    )
    partitions = {
        "r8": tuple(rows),
        "r6": _episodes("r6", start_days=200),
        "r5": _episodes("r5", start_days=400),
    }
    fitted_at = max(
        item.as_of
        for values in partitions.values()
        for item in values
    )

    with pytest.raises(ValueError, match="identity shortcut feature"):
        fit_invariant_representation(
            fitted_at=fitted_at,
            discovery_partition="r8",
            development_partitions=("r6", "r5"),
            episodes_by_partition=partitions,
            policy=_policy(),
        )


def test_v2_rejects_future_source_evidence() -> None:
    partitions = _development()
    fitted_at = BASE + timedelta(days=300)

    with pytest.raises(ValueError, match="future source evidence"):
        fit_invariant_representation(
            fitted_at=fitted_at,
            discovery_partition="r8",
            development_partitions=("r6", "r5"),
            episodes_by_partition=partitions,
            policy=_policy(),
        )


def test_v2_requires_exact_declared_partition_set() -> None:
    partitions = _development()
    partitions["extra"] = _episodes("extra", start_days=600)
    fitted_at = max(
        item.as_of
        for rows in partitions.values()
        for item in rows
    )

    with pytest.raises(ValueError, match="exactly match declared partitions"):
        fit_invariant_representation(
            fitted_at=fitted_at,
            discovery_partition="r8",
            development_partitions=("r6", "r5"),
            episodes_by_partition=partitions,
            policy=_policy(),
        )

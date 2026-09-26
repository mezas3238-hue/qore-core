from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from qore.infrastructure.core_stack_v2.hierarchical_world_model import WorldScale
from qore.infrastructure.core_stack_v2.temporal_hierarchy_engine import (
    TemporalHierarchySnapshot,
    TemporalHierarchyTrainingEpisode,
    TemporalScaleState,
    assess_temporal_hierarchy,
    baseline_local_opposition,
    evaluate_temporal_hierarchy,
    fit_temporal_hierarchy_model,
)

BASE = datetime(2020, 1, 1, tzinfo=UTC)


def _level(
    scale: WorldScale,
    *,
    direction: int,
    persistence: int,
    coherence: int,
    efficiency: int,
    fragility: int,
    transition: int,
) -> TemporalScaleState:
    return TemporalScaleState(
        scale=scale,
        direction_milli=direction,
        persistence_bps=persistence,
        coherence_bps=coherence,
        efficiency_bps=efficiency,
        fragility_bps=fragility,
        transition_bps=transition,
    )


def _snapshot(
    index: int,
    *,
    terminal_shape: bool,
    partition: str,
) -> TemporalHierarchySnapshot:
    jitter = (index % 7) * 20
    if terminal_shape:
        h1_direction = 250 - jitter
        h4_direction = 420 - jitter
        high_persistence = 4_200 + jitter
        high_fragility = 7_700 - jitter
        transition = 8_100 - jitter
        m15_direction = -850 + jitter
    else:
        h1_direction = 720 - jitter
        h4_direction = 820 - jitter
        high_persistence = 8_500 - jitter
        high_fragility = 2_000 + jitter
        transition = 2_300 + jitter
        m15_direction = -550 + jitter

    return TemporalHierarchySnapshot(
        episode_id=f"{partition}-{index}",
        as_of=BASE + timedelta(days=index),
        levels=(
            _level(
                WorldScale.M1,
                direction=-900 + jitter,
                persistence=7_500,
                coherence=7_000,
                efficiency=7_400,
                fragility=4_500,
                transition=5_500,
            ),
            _level(
                WorldScale.M3,
                direction=-850 + jitter,
                persistence=7_200,
                coherence=7_100,
                efficiency=7_000,
                fragility=4_800,
                transition=5_800,
            ),
            _level(
                WorldScale.M5,
                direction=-800 + jitter,
                persistence=7_000,
                coherence=7_000,
                efficiency=6_800,
                fragility=5_000,
                transition=6_000,
            ),
            _level(
                WorldScale.M15,
                direction=m15_direction,
                persistence=6_500,
                coherence=6_800,
                efficiency=6_500,
                fragility=6_200 if terminal_shape else 3_400,
                transition=7_200 if terminal_shape else 3_500,
            ),
            _level(
                WorldScale.H1,
                direction=h1_direction,
                persistence=high_persistence,
                coherence=7_500,
                efficiency=6_600,
                fragility=high_fragility,
                transition=transition,
            ),
            _level(
                WorldScale.H4,
                direction=h4_direction,
                persistence=high_persistence + 300,
                coherence=7_800,
                efficiency=6_900,
                fragility=max(0, high_fragility - 300),
                transition=max(0, transition - 250),
            ),
            _level(
                WorldScale.DAILY,
                direction=900 - jitter,
                persistence=9_000,
                coherence=8_300,
                efficiency=7_200,
                fragility=2_300 if terminal_shape else 1_500,
                transition=3_000 if terminal_shape else 1_800,
            ),
        ),
    )


def _episodes(
    *,
    partition: str,
    count: int,
    terminal_every: int,
    start_days: int = 0,
) -> tuple[TemporalHierarchyTrainingEpisode, ...]:
    rows = []
    for index in range(count):
        terminal = index % terminal_every == 0
        snapshot = _snapshot(
            index + start_days,
            terminal_shape=terminal,
            partition=partition,
        )
        rows.append(
            TemporalHierarchyTrainingEpisode(
                snapshot=snapshot,
                observed_at=snapshot.as_of + timedelta(minutes=30),
                terminal_failure=terminal,
            )
        )
    return tuple(rows)


def test_hierarchy_reduces_false_failure_without_losing_terminals() -> None:
    training = _episodes(
        partition="r8",
        count=240,
        terminal_every=4,
    )
    fitted_at = max(item.observed_at for item in training)
    model = fit_temporal_hierarchy_model(
        fitted_at=fitted_at,
        fit_partition="r8",
        episodes=training,
        minimum_training_recall_bps=9_500,
    )

    evaluation = evaluate_temporal_hierarchy(
        model=model,
        partition="r6",
        episodes=_episodes(
            partition="r6",
            count=160,
            terminal_every=4,
            start_days=500,
        ),
    )

    assert evaluation.baseline_declaration_count == 160
    assert evaluation.baseline_false_declaration_count > 0
    assert evaluation.false_declaration_reduction_bps >= 8_000
    assert evaluation.terminal_detection_preservation_bps >= 9_500


def test_runtime_projection_uses_no_target_or_future_market() -> None:
    training = _episodes(
        partition="r8",
        count=160,
        terminal_every=4,
    )
    model = fit_temporal_hierarchy_model(
        fitted_at=max(item.observed_at for item in training),
        fit_partition="r8",
        episodes=training,
    )
    snapshot = _snapshot(
        900,
        terminal_shape=False,
        partition="runtime",
    )

    assessment = assess_temporal_hierarchy(
        model=model,
        snapshot=snapshot,
    )

    assert assessment.baseline_local_opposition is True
    assert assessment.pullback_only is True
    assert assessment.structural_failure_declared is False
    assert assessment.target_used is False
    assert assessment.future_market_used is False
    assert model.target_used_for_training_only is True
    assert model.runtime_future_market_used is False
    assert model.outcome_used_at_runtime is False
    assert model.trader_identity_used is False
    assert model.symbol_identity_used is False


def test_fit_and_projection_are_deterministic() -> None:
    training = _episodes(
        partition="r8",
        count=180,
        terminal_every=5,
    )
    fitted_at = max(item.observed_at for item in training)

    first = fit_temporal_hierarchy_model(
        fitted_at=fitted_at,
        fit_partition="r8",
        episodes=training,
    )
    second = fit_temporal_hierarchy_model(
        fitted_at=fitted_at,
        fit_partition="r8",
        episodes=training,
    )
    assert first == second

    snapshot = _snapshot(
        800,
        terminal_shape=True,
        partition="runtime",
    )
    assert assess_temporal_hierarchy(
        model=first,
        snapshot=snapshot,
    ) == assess_temporal_hierarchy(
        model=second,
        snapshot=snapshot,
    )


def test_future_training_label_is_rejected() -> None:
    training = _episodes(
        partition="r8",
        count=120,
        terminal_every=4,
    )
    cutoff = max(item.observed_at for item in training) - timedelta(days=5)

    with pytest.raises(ValueError, match="future training evidence"):
        fit_temporal_hierarchy_model(
            fitted_at=cutoff,
            fit_partition="r8",
            episodes=training,
        )


def test_local_opposition_is_not_itself_structural_failure() -> None:
    snapshot = _snapshot(
        50,
        terminal_shape=False,
        partition="runtime",
    )
    assert baseline_local_opposition(snapshot) is True

    training = _episodes(
        partition="r8",
        count=160,
        terminal_every=4,
    )
    model = fit_temporal_hierarchy_model(
        fitted_at=max(item.observed_at for item in training),
        fit_partition="r8",
        episodes=training,
    )
    assessment = assess_temporal_hierarchy(
        model=model,
        snapshot=snapshot,
    )
    assert assessment.pullback_only is True
    assert assessment.structural_failure_declared is False


def test_snapshot_rejects_future_or_identity_shortcut_flags() -> None:
    levels = _snapshot(
        1,
        terminal_shape=False,
        partition="x",
    ).levels

    with pytest.raises(ValueError, match="forbidden evidence"):
        TemporalHierarchySnapshot(
            episode_id="bad",
            as_of=BASE,
            levels=levels,
            future_market_used=True,
        )

    with pytest.raises(ValueError, match="forbidden evidence"):
        TemporalHierarchySnapshot(
            episode_id="bad-symbol",
            as_of=BASE,
            levels=levels,
            symbol_identity_used=True,
        )

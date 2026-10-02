from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from qore.infrastructure.core_stack_v2.hierarchical_world_model import WorldScale
from qore.infrastructure.core_stack_v2.temporal_hierarchy_engine import (
    TemporalHierarchySnapshot,
    TemporalScaleState,
)
from qore.infrastructure.core_stack_v2.temporal_hierarchy_transition_v2 import (
    TemporalHierarchyTrajectory,
    TemporalHierarchyTrajectoryTrainingEpisode,
    assess_temporal_hierarchy_transition,
    evaluate_temporal_hierarchy_transition,
    fit_temporal_hierarchy_transition_model,
)

BASE = datetime(2020, 1, 1, tzinfo=UTC)


def _level(
    scale: WorldScale,
    *,
    direction: int,
    persistence: int,
    coherence: int,
    fragility: int,
    transition: int,
) -> TemporalScaleState:
    return TemporalScaleState(
        scale=scale,
        direction_milli=direction,
        persistence_bps=persistence,
        coherence_bps=coherence,
        efficiency_bps=7_000,
        fragility_bps=fragility,
        transition_bps=transition,
    )


def _snapshot(
    *,
    as_of: datetime,
    phase: int,
    terminal: bool,
    jitter: int,
    episode_id: str,
) -> TemporalHierarchySnapshot:
    # Both classes have local bearish opposition against a bullish broad state.
    # Terminal paths progressively propagate upward and erode higher resilience.
    if terminal:
        m15 = -250 - phase * 220 + jitter
        h1 = 700 - phase * 330 + jitter
        h4 = 850 - phase * 260 + jitter
        h1_frag = 3_000 + phase * 2_000
        h4_frag = 2_500 + phase * 1_700
        high_persist = 8_400 - phase * 1_600
        high_transition = 2_500 + phase * 2_200
    else:
        m15 = -450 + jitter
        h1 = 760 + jitter
        h4 = 860 + jitter
        h1_frag = 2_200 + phase * 120
        h4_frag = 1_900 + phase * 100
        high_persist = 8_600 - phase * 80
        high_transition = 2_200 + phase * 90

    return TemporalHierarchySnapshot(
        episode_id=f"{episode_id}:{phase}",
        as_of=as_of,
        levels=(
            _level(
                WorldScale.M1,
                direction=-900 + jitter,
                persistence=7_800,
                coherence=7_100,
                fragility=4_800,
                transition=5_800,
            ),
            _level(
                WorldScale.M3,
                direction=-850 + jitter,
                persistence=7_500,
                coherence=7_000,
                fragility=5_000,
                transition=6_000,
            ),
            _level(
                WorldScale.M5,
                direction=-800 + jitter,
                persistence=7_200,
                coherence=6_900,
                fragility=5_200,
                transition=6_200,
            ),
            _level(
                WorldScale.M15,
                direction=m15,
                persistence=6_700,
                coherence=6_800,
                fragility=5_500 if terminal else 3_500,
                transition=6_000 if terminal else 3_300,
            ),
            _level(
                WorldScale.H1,
                direction=h1,
                persistence=max(500, high_persist),
                coherence=7_500,
                fragility=min(9_800, h1_frag),
                transition=min(9_800, high_transition),
            ),
            _level(
                WorldScale.H4,
                direction=h4,
                persistence=max(500, high_persist + 250),
                coherence=7_800,
                fragility=min(9_800, h4_frag),
                transition=min(9_800, high_transition - 150),
            ),
            _level(
                WorldScale.DAILY,
                direction=900 + jitter,
                persistence=9_000,
                coherence=8_300,
                fragility=1_600,
                transition=1_900,
            ),
        ),
    )


def _trajectory(
    index: int,
    *,
    terminal: bool,
    partition: str,
    day_offset: int = 0,
) -> TemporalHierarchyTrajectory:
    end = BASE + timedelta(days=day_offset + index)
    jitter = (index % 9 - 4) * 8
    snapshots = tuple(
        _snapshot(
            as_of=end - timedelta(minutes=60 - phase * 30),
            phase=phase,
            terminal=terminal,
            jitter=jitter,
            episode_id=f"{partition}-{index}",
        )
        for phase in range(3)
    )
    return TemporalHierarchyTrajectory(
        episode_id=f"{partition}-{index}",
        snapshots=snapshots,
    )


def _episodes(
    *,
    partition: str,
    count: int,
    terminal_every: int,
    day_offset: int = 0,
) -> tuple[TemporalHierarchyTrajectoryTrainingEpisode, ...]:
    rows = []
    for index in range(count):
        terminal = index % terminal_every == 0
        trajectory = _trajectory(
            index,
            terminal=terminal,
            partition=partition,
            day_offset=day_offset,
        )
        rows.append(
            TemporalHierarchyTrajectoryTrainingEpisode(
                trajectory=trajectory,
                observed_at=trajectory.snapshots[-1].as_of + timedelta(minutes=30),
                terminal_failure=terminal,
            )
        )
    return tuple(rows)


def test_v2_propagation_model_reduces_false_failure_and_preserves_terminals() -> None:
    training = _episodes(
        partition="r8",
        count=320,
        terminal_every=4,
    )
    model = fit_temporal_hierarchy_transition_model(
        fitted_at=max(item.observed_at for item in training),
        fit_partition="r8",
        episodes=training,
        minimum_training_recall_bps=9_500,
    )

    evaluation = evaluate_temporal_hierarchy_transition(
        model=model,
        partition="r6",
        episodes=_episodes(
            partition="r6",
            count=240,
            terminal_every=4,
            day_offset=600,
        ),
    )

    assert evaluation.baseline_false_declaration_count > 0
    assert evaluation.false_declaration_reduction_bps >= 8_000
    assert evaluation.terminal_detection_preservation_bps >= 9_500


def test_v2_runtime_uses_source_trajectory_only() -> None:
    training = _episodes(partition="r8", count=240, terminal_every=4)
    model = fit_temporal_hierarchy_transition_model(
        fitted_at=max(item.observed_at for item in training),
        fit_partition="r8",
        episodes=training,
    )
    trajectory = _trajectory(
        900,
        terminal=False,
        partition="runtime",
    )

    assessment = assess_temporal_hierarchy_transition(
        model=model,
        trajectory=trajectory,
    )

    assert assessment.baseline_local_opposition is True
    assert assessment.structural_failure_declared is False
    assert assessment.recoverable_pullback is True
    assert assessment.future_market_used is False
    assert assessment.target_used is False
    assert model.target_used_for_training_only is True
    assert model.runtime_future_market_used is False
    assert model.outcome_used_at_runtime is False


def test_v2_model_and_projection_are_deterministic() -> None:
    training = _episodes(partition="r8", count=280, terminal_every=5)
    fitted_at = max(item.observed_at for item in training)

    first = fit_temporal_hierarchy_transition_model(
        fitted_at=fitted_at,
        fit_partition="r8",
        episodes=training,
    )
    second = fit_temporal_hierarchy_transition_model(
        fitted_at=fitted_at,
        fit_partition="r8",
        episodes=training,
    )
    assert first == second

    trajectory = _trajectory(800, terminal=True, partition="runtime")
    assert assess_temporal_hierarchy_transition(
        model=first,
        trajectory=trajectory,
    ) == assess_temporal_hierarchy_transition(
        model=second,
        trajectory=trajectory,
    )


def test_v2_rejects_future_fit_evidence() -> None:
    training = _episodes(partition="r8", count=220, terminal_every=4)
    cutoff = max(item.observed_at for item in training) - timedelta(days=10)

    with pytest.raises(ValueError, match="future training evidence"):
        fit_temporal_hierarchy_transition_model(
            fitted_at=cutoff,
            fit_partition="r8",
            episodes=training,
        )


def test_v2_trajectory_rejects_runtime_future_flag() -> None:
    trajectory = _trajectory(10, terminal=False, partition="x")

    with pytest.raises(ValueError, match="forbidden evidence"):
        TemporalHierarchyTrajectory(
            episode_id="bad",
            snapshots=trajectory.snapshots,
            future_market_used=True,
        )

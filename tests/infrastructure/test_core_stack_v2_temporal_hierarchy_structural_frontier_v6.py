from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from qore.infrastructure.core_stack_v2.hierarchical_world_model import WorldScale
from qore.infrastructure.core_stack_v2.temporal_hierarchy_engine import (
    TemporalHierarchySnapshot,
    TemporalScaleState,
)
from qore.infrastructure.core_stack_v2.temporal_hierarchy_structural_frontier_v6 import (
    StructuralFrontierSourceState,
    StructuralFrontierTrainingEpisode,
    assess_structural_frontier,
    evaluate_structural_frontier,
    fit_structural_frontier_model,
    structural_frontier_hierarchy_motif,
)
from qore.infrastructure.core_stack_v2.temporal_hierarchy_transition_v2 import (
    TemporalHierarchyTrajectory,
)

BASE = datetime(2020, 1, 1, tzinfo=UTC)


def _episode(
    index: int,
    *,
    terminal: bool,
    shift: float = 0.0,
) -> StructuralFrontierTrainingEpisode:
    # Recoverable states stay farther from the failure frontier, show rejection,
    # lower adverse persistence and stronger high-timeframe resilience. Terminal
    # states approach the frontier with cross-market confirmation.
    wobble = (index % 13 - 6) * 0.01
    if terminal:
        distance = 0.35 + shift + wobble
        approach5 = 0.55 + wobble
        approach15 = 0.75 + wobble
        rejection5 = 0.05 + wobble / 4
        rejection15 = 0.08 + wobble / 4
        adverse_fraction = 0.80
        vol_ratio = 1.35
        peer5 = 0.65 + wobble
        peer15 = 0.72 + wobble
        resilience = -0.35
        depth = 0.82
        recession = -0.55
    else:
        distance = 1.65 + shift + wobble
        approach5 = 0.05 + wobble
        approach15 = 0.10 + wobble
        rejection5 = 0.65 + wobble
        rejection15 = 0.75 + wobble
        adverse_fraction = 0.35
        vol_ratio = 0.95
        peer5 = 0.05 + wobble
        peer15 = 0.08 + wobble
        resilience = 0.55
        depth = 0.35
        recession = 0.60

    at = BASE + timedelta(minutes=30 * index)
    source = StructuralFrontierSourceState(
        episode_id=f"e-{index}",
        as_of=at,
        anchor_direction=1,
        distance_now=distance,
        approach_5m=approach5,
        approach_15m=approach15,
        rejection_5m=rejection5,
        rejection_15m=rejection15,
        adverse_close_fraction_5m=adverse_fraction,
        volatility_ratio_5m_20m=vol_ratio,
        peer_adverse_5m=peer5,
        peer_adverse_15m=peer15,
        higher_resilience_minus_fragility=resilience,
        hierarchy_depth=depth,
        hierarchy_recession_minus_advance=recession,
    )
    return StructuralFrontierTrainingEpisode(
        source=source,
        observed_at=at + timedelta(minutes=30),
        terminal_failure=terminal,
    )


def _population(
    count: int,
    *,
    shift: float = 0.0,
) -> tuple[StructuralFrontierTrainingEpisode, ...]:
    return tuple(
        _episode(index, terminal=index % 4 == 0, shift=shift)
        for index in range(count)
    )


def test_v6_separates_frontier_survival_from_terminal_pressure() -> None:
    training = _population(800)
    model = fit_structural_frontier_model(
        fitted_at=max(item.observed_at for item in training),
        fit_partition="r8",
        episodes=training,
    )
    evaluation = evaluate_structural_frontier(
        model=model,
        partition="r6",
        episodes=_population(480, shift=0.04),
    )

    assert model.calibration_terminal_preservation_bps >= 9_800
    assert evaluation.false_declaration_reduction_bps >= 8_000
    assert evaluation.terminal_detection_preservation_bps >= 9_500


def test_v6_runtime_uses_only_source_state() -> None:
    training = _population(700)
    model = fit_structural_frontier_model(
        fitted_at=max(item.observed_at for item in training),
        fit_partition="r8",
        episodes=training,
    )
    recovered = assess_structural_frontier(
        model=model,
        source=_episode(901, terminal=False).source,
    )
    terminal = assess_structural_frontier(
        model=model,
        source=_episode(904, terminal=True).source,
    )

    assert recovered.recoverable_pullback is True
    assert recovered.structural_failure_declared is False
    assert terminal.structural_failure_declared is True
    assert model.runtime_future_market_used is False
    assert model.outcome_used_at_runtime is False
    assert model.methodology_authority is False
    assert model.sizing_authority is False
    assert model.risk_authority is False
    assert model.order_authority is False
    assert model.execution_authority is False


def test_v6_rejects_future_fit_evidence() -> None:
    training = _population(300)
    with pytest.raises(ValueError, match="future training evidence"):
        fit_structural_frontier_model(
            fitted_at=max(item.observed_at for item in training)
            - timedelta(days=1),
            fit_partition="r8",
            episodes=training,
        )



def _hierarchy_level(scale: WorldScale, direction: int) -> TemporalScaleState:
    return TemporalScaleState(
        scale=scale,
        direction_milli=direction,
        persistence_bps=7_000,
        coherence_bps=7_000,
        efficiency_bps=6_000,
        fragility_bps=2_000,
        transition_bps=2_000,
    )


def _hierarchy_snapshot(
    *,
    minute: int,
    m1: int,
    m3: int,
    h1: int = 900,
    h4: int = 900,
    daily: int = 900,
) -> TemporalHierarchySnapshot:
    return TemporalHierarchySnapshot(
        episode_id=f"motif-{minute}",
        as_of=BASE + timedelta(minutes=minute),
        levels=(
            _hierarchy_level(WorldScale.M1, m1),
            _hierarchy_level(WorldScale.M3, m3),
            _hierarchy_level(WorldScale.M5, 100),
            _hierarchy_level(WorldScale.M15, 100),
            _hierarchy_level(WorldScale.H1, h1),
            _hierarchy_level(WorldScale.H4, h4),
            _hierarchy_level(WorldScale.DAILY, daily),
        ),
    )


def test_v6_hierarchy_motif_honors_explicit_target_v2_anchor() -> None:
    # H1/H4 dominate the mean positively while D1 alone is negative. Under the
    # Target-V2 positive anchor, D1 is itself adverse (depth 7). Under the old
    # D1-priority negative coordinate, H1/H4 are adverse instead (depth 6).
    trajectory = TemporalHierarchyTrajectory(
        episode_id="explicit-anchor",
        snapshots=(
            _hierarchy_snapshot(
                minute=0,
                m1=300,
                m3=300,
                h1=900,
                h4=900,
                daily=-100,
            ),
            _hierarchy_snapshot(
                minute=15,
                m1=300,
                m3=300,
                h1=900,
                h4=900,
                daily=-100,
            ),
            _hierarchy_snapshot(
                minute=30,
                m1=300,
                m3=300,
                h1=900,
                h4=900,
                daily=-100,
            ),
        ),
    )

    target_v2 = structural_frontier_hierarchy_motif(
        trajectory=trajectory,
        anchor_direction=1,
    )
    d1_priority = structural_frontier_hierarchy_motif(
        trajectory=trajectory,
        anchor_direction=-1,
    )

    assert target_v2.depth_path == (7, 7, 7)
    assert d1_priority.depth_path == (6, 6, 6)


def test_v6_hierarchy_motif_tracks_recession_and_advance() -> None:
    trajectory = TemporalHierarchyTrajectory(
        episode_id="fixed-anchor-path",
        snapshots=(
            _hierarchy_snapshot(minute=0, m1=-700, m3=300),
            _hierarchy_snapshot(minute=15, m1=-700, m3=-600),
            _hierarchy_snapshot(minute=30, m1=300, m3=300),
        ),
    )

    motif = structural_frontier_hierarchy_motif(
        trajectory=trajectory,
        anchor_direction=1,
    )

    assert motif.depth_path == (1, 2, 0)
    assert motif.current_depth == 0
    assert motif.advance_count == 1
    assert motif.recession_count == 1


def test_v6_hierarchy_motif_rejects_unidentifiable_anchor() -> None:
    trajectory = TemporalHierarchyTrajectory(
        episode_id="neutral-anchor",
        snapshots=(
            _hierarchy_snapshot(minute=0, m1=-700, m3=300),
            _hierarchy_snapshot(minute=15, m1=-700, m3=-600),
            _hierarchy_snapshot(minute=30, m1=300, m3=300),
        ),
    )

    with pytest.raises(ValueError, match="identifiable anchor"):
        structural_frontier_hierarchy_motif(
            trajectory=trajectory,
            anchor_direction=0,
        )



def test_v6_source_state_requires_identifiable_anchor() -> None:
    base = _episode(20, terminal=True).source

    with pytest.raises(ValueError, match="identifiable anchor"):
        StructuralFrontierSourceState(
            episode_id=base.episode_id,
            as_of=base.as_of,
            anchor_direction=0,
            distance_now=base.distance_now,
            approach_5m=base.approach_5m,
            approach_15m=base.approach_15m,
            rejection_5m=base.rejection_5m,
            rejection_15m=base.rejection_15m,
            adverse_close_fraction_5m=base.adverse_close_fraction_5m,
            volatility_ratio_5m_20m=base.volatility_ratio_5m_20m,
            peer_adverse_5m=base.peer_adverse_5m,
            peer_adverse_15m=base.peer_adverse_15m,
            higher_resilience_minus_fragility=base.higher_resilience_minus_fragility,
            hierarchy_depth=base.hierarchy_depth,
            hierarchy_recession_minus_advance=(
                base.hierarchy_recession_minus_advance
            ),
        )



def test_v6_fit_protocol_is_frozen() -> None:
    training = _population(300)
    fitted_at = max(item.observed_at for item in training)

    with pytest.raises(ValueError, match="fit partition is frozen"):
        fit_structural_frontier_model(
            fitted_at=fitted_at,
            fit_partition="r6",
            episodes=training,
        )

    with pytest.raises(ValueError, match="discovery split is frozen"):
        fit_structural_frontier_model(
            fitted_at=fitted_at,
            fit_partition="r8",
            episodes=training,
            discovery_fraction_bps=7_500,
        )

    with pytest.raises(ValueError, match="calibration recall is frozen"):
        fit_structural_frontier_model(
            fitted_at=fitted_at,
            fit_partition="r8",
            episodes=training,
            calibration_recall_bps=9_700,
        )

    with pytest.raises(ValueError, match="ridge is frozen"):
        fit_structural_frontier_model(
            fitted_at=fitted_at,
            fit_partition="r8",
            episodes=training,
            ridge=3.0,
        )

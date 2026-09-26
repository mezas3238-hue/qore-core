from __future__ import annotations

from datetime import UTC, datetime

from qore.infrastructure.core_stack_v2.hierarchical_world_model import WorldScale
from qore.infrastructure.core_stack_v2.temporal_hierarchy_engine import (
    TemporalHierarchySnapshot,
    TemporalScaleState,
)
from qore.infrastructure.core_stack_v2.temporal_hierarchy_target_contract import (
    assess_temporal_hierarchy_target_semantics,
    higher_timeframe_anchor_direction,
    higher_timeframe_structural_failure_target,
)


def _level(scale: WorldScale, direction: int) -> TemporalScaleState:
    return TemporalScaleState(
        scale=scale,
        direction_milli=direction,
        persistence_bps=8_000,
        coherence_bps=8_000,
        efficiency_bps=7_000,
        fragility_bps=2_000,
        transition_bps=2_000,
    )


def _snapshot(*, m15: int, h1: int, h4: int, daily: int) -> TemporalHierarchySnapshot:
    return TemporalHierarchySnapshot(
        episode_id="audit",
        as_of=datetime(2026, 1, 1, tzinfo=UTC),
        levels=(
            _level(WorldScale.M1, -900),
            _level(WorldScale.M3, -850),
            _level(WorldScale.M5, -800),
            _level(WorldScale.M15, m15),
            _level(WorldScale.H1, h1),
            _level(WorldScale.H4, h4),
            _level(WorldScale.DAILY, daily),
        ),
    )


def test_target_semantics_detects_directional_inversion() -> None:
    snapshot = _snapshot(m15=-500, h1=700, h4=800, daily=900)
    audit = assess_temporal_hierarchy_target_semantics(snapshot)

    assert audit.baseline_local_opposition is True
    assert audit.m15_source_direction == -1
    assert audit.higher_timeframe_anchor_direction == 1
    assert audit.current_target_terminal_break_direction == 1
    assert audit.expected_structural_failure_break_direction == -1
    assert audit.directionally_identifiable is True
    assert audit.directionally_aligned is False
    assert audit.directionally_inverted is True


def test_target_semantics_accepts_m15_when_it_matches_high_anchor() -> None:
    snapshot = TemporalHierarchySnapshot(
        episode_id="aligned",
        as_of=datetime(2026, 1, 1, tzinfo=UTC),
        levels=(
            _level(WorldScale.M1, -1_000),
            _level(WorldScale.M3, -1_000),
            _level(WorldScale.M5, -1_000),
            _level(WorldScale.M15, 100),
            _level(WorldScale.H1, 700),
            _level(WorldScale.H4, 800),
            _level(WorldScale.DAILY, 900),
        ),
    )
    audit = assess_temporal_hierarchy_target_semantics(snapshot)

    assert audit.baseline_local_opposition is True
    assert audit.directionally_aligned is True
    assert audit.directionally_inverted is False
    assert audit.current_target_terminal_break_direction == -1
    assert audit.expected_structural_failure_break_direction == -1


def test_target_semantics_has_no_trading_authority() -> None:
    audit = assess_temporal_hierarchy_target_semantics(
        _snapshot(m15=-500, h1=700, h4=800, daily=900)
    )

    assert audit.methodology_authority is False
    assert audit.knowledge_promotion_authority is False
    assert audit.sizing_authority is False
    assert audit.risk_authority is False
    assert audit.order_authority is False
    assert audit.execution_authority is False


def test_structural_failure_target_v2_uses_higher_anchor_direction() -> None:
    assert higher_timeframe_structural_failure_target(
        anchor_direction=1,
        prior_peak=110.0,
        prior_floor=100.0,
        future_high=109.0,
        future_low=99.0,
        future_final_close=99.5,
    ) is True
    assert higher_timeframe_structural_failure_target(
        anchor_direction=-1,
        prior_peak=110.0,
        prior_floor=100.0,
        future_high=111.0,
        future_low=101.0,
        future_final_close=110.5,
    ) is True


def test_structural_failure_target_v2_requires_close_acceptance() -> None:
    assert higher_timeframe_structural_failure_target(
        anchor_direction=1,
        prior_peak=110.0,
        prior_floor=100.0,
        future_high=109.0,
        future_low=99.0,
        future_final_close=101.0,
    ) is False
    assert higher_timeframe_structural_failure_target(
        anchor_direction=-1,
        prior_peak=110.0,
        prior_floor=100.0,
        future_high=111.0,
        future_low=101.0,
        future_final_close=109.0,
    ) is False


def test_structural_failure_target_v2_abstains_without_anchor() -> None:
    assert higher_timeframe_structural_failure_target(
        anchor_direction=0,
        prior_peak=110.0,
        prior_floor=100.0,
        future_high=120.0,
        future_low=90.0,
        future_final_close=95.0,
    ) is False



def test_higher_anchor_exact_cancellation_remains_unidentifiable() -> None:
    snapshot = _snapshot(m15=-500, h1=-72, h4=-24, daily=96)

    assert higher_timeframe_anchor_direction(snapshot) == 0

    audit = assess_temporal_hierarchy_target_semantics(snapshot)
    assert audit.directionally_identifiable is False
    assert audit.expected_structural_failure_break_direction == 0
    assert audit.directionally_aligned is False
    assert audit.directionally_inverted is False

    assert higher_timeframe_structural_failure_target(
        anchor_direction=0,
        prior_peak=110.0,
        prior_floor=100.0,
        future_high=120.0,
        future_low=90.0,
        future_final_close=95.0,
    ) is False

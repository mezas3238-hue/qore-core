from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

import pytest

from qore.infrastructure.core_stack_v2.hierarchical_world_model import WorldScale
from qore.infrastructure.core_stack_v2.temporal_hierarchy_competing_survival_features_v7 import (
    build_competing_survival_source_state,
)
from qore.infrastructure.core_stack_v2.temporal_hierarchy_competing_survival_v7 import (
    RECOVERY_FEATURE_NAMES,
    TERMINAL_FEATURE_NAMES,
)
from qore.infrastructure.core_stack_v2.temporal_hierarchy_engine import (
    TemporalHierarchySnapshot,
    TemporalScaleState,
)
from qore.infrastructure.core_stack_v2.temporal_hierarchy_transition_v2 import (
    TemporalHierarchyTrajectory,
)

BASE = datetime(2020, 1, 1, tzinfo=UTC)


@dataclass(frozen=True)
class Bar:
    opened: float
    high: float
    low: float
    close: float


def _bars(count: int, *, offset: float = 0.0) -> tuple[Bar, ...]:
    rows = []
    price = 100.0 + offset
    for index in range(count):
        drift = 0.08 if index % 7 not in (0, 1) else -0.16
        opened = price
        close = opened + drift
        high = max(opened, close) + 0.20
        low = min(opened, close) - 0.20
        rows.append(Bar(opened=opened, high=high, low=low, close=close))
        price = close
    return tuple(rows)


def _level(
    scale: WorldScale,
    *,
    direction: int,
    fragility: int,
    transition: int,
    persistence: int,
    coherence: int,
) -> TemporalScaleState:
    return TemporalScaleState(
        scale=scale,
        direction_milli=direction,
        persistence_bps=persistence,
        coherence_bps=coherence,
        efficiency_bps=6_000,
        fragility_bps=fragility,
        transition_bps=transition,
    )


def _snapshot(minute: int, *, adverse_depth: int) -> TemporalHierarchySnapshot:
    scales = (
        WorldScale.M1,
        WorldScale.M3,
        WorldScale.M5,
        WorldScale.M15,
        WorldScale.H1,
        WorldScale.H4,
        WorldScale.DAILY,
    )
    levels = []
    for ordinal, scale in enumerate(scales, start=1):
        adverse = ordinal <= adverse_depth
        high_scale = scale in (WorldScale.H1, WorldScale.H4, WorldScale.DAILY)
        levels.append(
            _level(
                scale,
                direction=-700 if adverse else 700,
                fragility=4_000 if high_scale and adverse else 2_000,
                transition=4_500 if high_scale and adverse else 2_000,
                persistence=5_500 if high_scale and adverse else 7_500,
                coherence=5_500 if high_scale and adverse else 7_500,
            )
        )
    return TemporalHierarchySnapshot(
        episode_id=f"s-{minute}",
        as_of=BASE + timedelta(minutes=minute),
        levels=tuple(levels),
    )


def _trajectory() -> TemporalHierarchyTrajectory:
    return TemporalHierarchyTrajectory(
        episode_id="v7-source",
        snapshots=(
            _snapshot(0, adverse_depth=3),
            _snapshot(30, adverse_depth=4),
            _snapshot(60, adverse_depth=3),
            _snapshot(75, adverse_depth=2),
            _snapshot(90, adverse_depth=1),
        ),
    )


def _index(names: tuple[str, ...], name: str) -> int:
    return names.index(name)


def test_v7_feature_extractor_ignores_all_future_bars() -> None:
    nas = _bars(140)
    sp = _bars(140, offset=20.0)
    us = _bars(140, offset=40.0)
    source_index = 90

    first = build_competing_survival_source_state(
        trajectory=_trajectory(),
        anchor_direction=1,
        nas_bars=nas,
        nas_index=source_index,
        sp500_bars=sp,
        sp500_index=source_index,
        us30_bars=us,
        us30_index=source_index,
    )

    def mutate_future(rows: tuple[Bar, ...]) -> tuple[Bar, ...]:
        changed = list(rows)
        for index in range(source_index + 1, len(changed)):
            changed[index] = Bar(
                opened=10_000.0 + index,
                high=20_000.0 + index,
                low=-20_000.0 - index,
                close=-10_000.0 - index,
            )
        return tuple(changed)

    second = build_competing_survival_source_state(
        trajectory=_trajectory(),
        anchor_direction=1,
        nas_bars=mutate_future(nas),
        nas_index=source_index,
        sp500_bars=mutate_future(sp),
        sp500_index=source_index,
        us30_bars=mutate_future(us),
        us30_index=source_index,
    )

    assert first == second
    assert first.future_market_used is False
    assert first.target_used is False


def test_v7_exact_source_distance_and_causal_history_are_distinct() -> None:
    nas = list(_bars(140))
    source_index = 90
    # Create a historical causal downside breach five minutes before source.
    breached = nas[source_index - 5]
    nas[source_index - 5] = Bar(
        opened=breached.opened,
        high=breached.high,
        low=breached.low - 4.0,
        close=breached.close - 2.0,
    )
    state = build_competing_survival_source_state(
        trajectory=_trajectory(),
        anchor_direction=1,
        nas_bars=tuple(nas),
        nas_index=source_index,
        sp500_bars=_bars(140, offset=20.0),
        sp500_index=source_index,
        us30_bars=_bars(140, offset=40.0),
        us30_index=source_index,
    )

    distance_now = state.terminal_features[
        _index(TERMINAL_FEATURE_NAMES, "DISTANCE_NOW")
    ]
    distance_5m = state.terminal_features[
        _index(TERMINAL_FEATURE_NAMES, "DISTANCE_5M")
    ]
    breach_depth = state.terminal_features[
        _index(TERMINAL_FEATURE_NAMES, "BREACH_DEPTH")
    ]
    touches_30 = state.recovery_features[
        _index(RECOVERY_FEATURE_NAMES, "FRONTIER_TOUCHES_30M")
    ]

    assert state.evidence_complete is True
    assert distance_now != distance_5m
    assert breach_depth > 0.0
    assert touches_30 >= 1.0


def test_v7_feature_extractor_returns_incomplete_state_without_required_history() -> None:
    state = build_competing_survival_source_state(
        trajectory=_trajectory(),
        anchor_direction=1,
        nas_bars=_bars(50),
        nas_index=40,
        sp500_bars=_bars(50, offset=20.0),
        sp500_index=40,
        us30_bars=_bars(50, offset=40.0),
        us30_index=40,
    )

    assert state.evidence_complete is False
    assert set(state.terminal_features) == {0.0}
    assert set(state.recovery_features) == {0.0}


def test_v7_feature_extractor_rejects_neutral_anchor() -> None:
    with pytest.raises(ValueError, match="identifiable anchor"):
        build_competing_survival_source_state(
            trajectory=_trajectory(),
            anchor_direction=0,
            nas_bars=_bars(140),
            nas_index=90,
            sp500_bars=_bars(140, offset=20.0),
            sp500_index=90,
            us30_bars=_bars(140, offset=40.0),
            us30_index=90,
        )


def test_v7_hierarchy_path_uses_one_fixed_anchor() -> None:
    state = build_competing_survival_source_state(
        trajectory=_trajectory(),
        anchor_direction=1,
        nas_bars=_bars(140),
        nas_index=90,
        sp500_bars=_bars(140, offset=20.0),
        sp500_index=90,
        us30_bars=_bars(140, offset=40.0),
        us30_index=90,
    )
    recession = state.recovery_features[
        _index(RECOVERY_FEATURE_NAMES, "HIERARCHY_RECESSION_COUNT")
    ]
    advance = state.recovery_features[
        _index(RECOVERY_FEATURE_NAMES, "HIERARCHY_ADVANCE_COUNT")
    ]

    assert recession >= 1.0
    assert advance >= 1.0

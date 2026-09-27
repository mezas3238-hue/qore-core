from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime, timedelta

import pytest

import qore.infrastructure.core_stack_v2.temporal_hierarchy_event_manifold_v8 as event_manifold_v8
from qore.infrastructure.core_stack_v2.temporal_hierarchy_competing_survival_v7 import (
    RECOVERY_FEATURE_NAMES,
    TERMINAL_FEATURE_NAMES,
    CompetingSurvivalSourceState,
)
from qore.infrastructure.core_stack_v2.temporal_hierarchy_event_manifold_v8 import (
    EventManifoldLabel,
    EventManifoldState,
    EventManifoldTrainingEpisode,
    assess_event_manifold,
    event_manifold_model_fingerprint,
    event_manifold_representation_fingerprint,
    fit_event_manifold_model,
    matured_event_label,
)

BASE = datetime(2020, 1, 1, tzinfo=UTC)


class Bar:
    def __init__(self, *, high: float, low: float, close: float) -> None:
        self.high = high
        self.low = low
        self.close = close


def _future(
    *,
    values: list[tuple[float, float, float]],
) -> tuple[Bar, ...]:
    rows = [Bar(high=high, low=low, close=close) for high, low, close in values]
    while len(rows) < 30:
        rows.append(Bar(high=101.0, low=99.2, close=100.5))
    return tuple(rows[:30])


def test_v8_matured_event_label_preserves_target_v2_terminal() -> None:
    future = tuple(
        Bar(high=101.0, low=98.0, close=98.5)
        for _ in range(30)
    )
    assert matured_event_label(
        anchor_direction=1,
        prior_peak=110.0,
        prior_floor=99.0,
        future_bars=future,
    ) is EventManifoldLabel.TERMINAL_EVENT


def test_v8_verified_recovery_requires_contact_then_persistent_reclaim() -> None:
    values = [
        (101.0, 98.8, 99.1),
        (100.0, 98.7, 98.9),
        (100.5, 98.9, 99.2),
        (101.0, 99.2, 99.6),
        (101.2, 99.3, 99.7),
        (101.4, 99.4, 99.8),
    ]
    future = _future(values=values)
    assert matured_event_label(
        anchor_direction=1,
        prior_peak=110.0,
        prior_floor=99.0,
        future_bars=future,
    ) is EventManifoldLabel.VERIFIED_RECOVERY_EVENT


def test_v8_nonterminal_without_frontier_challenge_is_censored() -> None:
    future = tuple(
        Bar(high=103.0, low=100.0, close=101.0)
        for _ in range(30)
    )
    assert matured_event_label(
        anchor_direction=1,
        prior_peak=110.0,
        prior_floor=99.0,
        future_bars=future,
    ) is EventManifoldLabel.CENSORED_UNKNOWN


def test_v8_contact_without_three_safe_closes_after_last_contact_is_censored() -> None:
    rows = [Bar(high=101.0, low=100.0, close=100.5) for _ in range(27)]
    rows.extend(
        [
            Bar(high=100.0, low=98.7, close=99.2),
            Bar(high=100.2, low=99.1, close=99.4),
            Bar(high=100.3, low=99.2, close=99.5),
        ]
    )
    assert matured_event_label(
        anchor_direction=1,
        prior_peak=110.0,
        prior_floor=99.0,
        future_bars=tuple(rows),
    ) is EventManifoldLabel.CENSORED_UNKNOWN


def _source(
    index: int,
    *,
    label: EventManifoldLabel,
    censored_shift: float = 0.0,
    complete: bool = True,
) -> CompetingSurvivalSourceState:
    wobble = (index % 19 - 9) * 0.01
    if label is EventManifoldLabel.TERMINAL_EVENT:
        base = 2.0
    elif label is EventManifoldLabel.VERIFIED_RECOVERY_EVENT:
        base = -2.0
    else:
        base = censored_shift
    terminal = tuple(
        base + wobble + feature_index * 0.001
        for feature_index, _ in enumerate(TERMINAL_FEATURE_NAMES)
    )
    recovery = tuple(
        base + wobble - feature_index * 0.001
        for feature_index, _ in enumerate(RECOVERY_FEATURE_NAMES)
    )
    return CompetingSurvivalSourceState(
        episode_id=f"v8-{index}",
        as_of=BASE + timedelta(minutes=30 * index),
        anchor_direction=1,
        terminal_features=terminal,
        recovery_features=recovery,
        evidence_complete=complete,
    )


def _episodes(
    count: int,
    *,
    censored_shift: float = 0.0,
) -> tuple[EventManifoldTrainingEpisode, ...]:
    rows = []
    for index in range(count):
        cycle = index % 5
        if cycle == 0:
            label = EventManifoldLabel.TERMINAL_EVENT
        elif cycle in (1, 2):
            label = EventManifoldLabel.VERIFIED_RECOVERY_EVENT
        else:
            label = EventManifoldLabel.CENSORED_UNKNOWN
        source = _source(
            index,
            label=label,
            censored_shift=censored_shift,
        )
        rows.append(
            EventManifoldTrainingEpisode(
                source=source,
                observed_at=source.as_of + timedelta(minutes=30),
                label=label,
            )
        )
    return tuple(rows)


def test_v8_censored_unknown_does_not_define_event_manifolds() -> None:
    first_rows = _episodes(600, censored_shift=0.0)
    second_rows = _episodes(600, censored_shift=50.0)
    fitted_at = max(item.observed_at for item in first_rows)

    first = fit_event_manifold_model(
        fitted_at=fitted_at,
        fit_partition="r8",
        episodes=first_rows,
    )
    second = fit_event_manifold_model(
        fitted_at=fitted_at,
        fit_partition="r8",
        episodes=second_rows,
    )

    assert first.terminal_centers_micros == second.terminal_centers_micros
    assert first.terminal_scales_micros == second.terminal_scales_micros
    assert first.recovery_centers_micros == second.recovery_centers_micros
    assert first.recovery_scales_micros == second.recovery_scales_micros
    assert first.fit_censored_count > 0
    assert second.fit_censored_count == first.fit_censored_count


def test_v8_runtime_uses_source_only_and_incomplete_evidence_abstains() -> None:
    rows = _episodes(600)
    model = fit_event_manifold_model(
        fitted_at=max(item.observed_at for item in rows),
        fit_partition="r8",
        episodes=rows,
    )
    source = _source(
        900,
        label=EventManifoldLabel.VERIFIED_RECOVERY_EVENT,
        complete=False,
    )
    assessment = assess_event_manifold(model=model, source=source)

    assert assessment.state is EventManifoldState.UNRESOLVED
    assert assessment.structural_failure_declared is True
    assert assessment.target_used is False
    assert assessment.future_market_used is False
    assert model.runtime_future_market_used is False
    assert model.outcome_used_at_runtime is False
    assert model.methodology_authority is False
    assert model.sizing_authority is False
    assert model.risk_authority is False
    assert model.order_authority is False
    assert model.execution_authority is False


def test_v8_calibration_selects_max_reduction_subject_to_preservation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    rows = _episodes(600)

    monkeypatch.setattr(
        event_manifold_v8,
        "_quantile",
        lambda values, bps: bps / 1_000,
    )

    def metrics(*, rows, recovery_radius_micros, recovery_advantage_margin_micros):
        del rows, recovery_advantage_margin_micros
        if recovery_radius_micros == 1_000_000:
            return 10_000, 100
        if recovery_radius_micros == 1_500_000:
            return 9_800, 500
        return 9_700, 900

    monkeypatch.setattr(event_manifold_v8, "_metrics", metrics)

    model = fit_event_manifold_model(
        fitted_at=max(item.observed_at for item in rows),
        fit_partition="r8",
        episodes=rows,
    )

    assert model.calibration_gate_pass is True
    assert model.recovery_radius_quantile_bps == 1_500
    assert model.calibration_false_reduction_bps == 500
    assert model.calibration_terminal_preservation_bps == 9_800


def test_v8_model_and_representation_fingerprints_are_deterministic() -> None:
    rows = _episodes(600)
    fitted_at = max(item.observed_at for item in rows)
    first = fit_event_manifold_model(
        fitted_at=fitted_at,
        fit_partition="r8",
        episodes=rows,
    )
    second = fit_event_manifold_model(
        fitted_at=fitted_at,
        fit_partition="r8",
        episodes=rows,
    )

    assert first == second
    assert event_manifold_model_fingerprint(first) == (
        event_manifold_model_fingerprint(second)
    )
    assert len(event_manifold_model_fingerprint(first)) == 64
    assert len(event_manifold_representation_fingerprint()) == 64


def test_v8_protocol_is_frozen_and_source_forbids_future_evidence() -> None:
    rows = _episodes(300)
    fitted_at = max(item.observed_at for item in rows)

    with pytest.raises(ValueError, match="fit partition is frozen"):
        fit_event_manifold_model(
            fitted_at=fitted_at,
            fit_partition="r6",
            episodes=rows,
        )

    with pytest.raises(ValueError, match="discovery split is frozen"):
        fit_event_manifold_model(
            fitted_at=fitted_at,
            fit_partition="r8",
            episodes=rows,
            discovery_fraction_bps=7_500,
        )

    base = _source(20, label=EventManifoldLabel.TERMINAL_EVENT)
    with pytest.raises(ValueError, match="forbidden evidence"):
        replace(base, future_market_used=True)

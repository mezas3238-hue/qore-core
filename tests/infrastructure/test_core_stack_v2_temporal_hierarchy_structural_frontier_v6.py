from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from qore.infrastructure.core_stack_v2.temporal_hierarchy_structural_frontier_v6 import (
    StructuralFrontierSourceState,
    StructuralFrontierTrainingEpisode,
    assess_structural_frontier,
    evaluate_structural_frontier,
    fit_structural_frontier_model,
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

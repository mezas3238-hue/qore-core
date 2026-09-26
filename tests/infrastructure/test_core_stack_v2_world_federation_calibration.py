from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from qore.infrastructure.core_stack_v2.multi_world_engine import (
    WorldModelFamily,
)
from qore.infrastructure.core_stack_v2.world_federation_calibration import (
    RealizedWorldQuality,
    WorldCalibrationEpisode,
    WorldEvaluationPartition,
    compare_calibration_to_holdout,
    summarize_world_calibration,
)


BASE = datetime(2026, 1, 1, tzinfo=UTC)


def _posterior(
    winner: WorldModelFamily,
    confidence_bps: int,
) -> tuple[tuple[WorldModelFamily, int], ...]:
    families = list(WorldModelFamily)
    remainder = 10_000 - confidence_bps
    others = [family for family in families if family is not winner]
    base = remainder // len(others)
    extra = remainder - base * len(others)
    values: list[tuple[WorldModelFamily, int]] = []
    for family in families:
        if family is winner:
            values.append((family, confidence_bps))
            continue
        rank = others.index(family)
        values.append((family, base + int(rank < extra)))
    return tuple(values)


def _quality(
    winner: WorldModelFamily,
) -> tuple[RealizedWorldQuality, ...]:
    return tuple(
        RealizedWorldQuality(
            family=family,
            quality_bps=9_000 if family is winner else 3_000,
        )
        for family in WorldModelFamily
    )


def _episode(
    *,
    index: int,
    partition: WorldEvaluationPartition,
    regime: str,
    posterior_winner: WorldModelFamily,
    realized_winner: WorldModelFamily,
    confidence_bps: int,
    offset_days: int = 0,
) -> WorldCalibrationEpisode:
    as_of = BASE + timedelta(days=offset_days, minutes=index)
    return WorldCalibrationEpisode(
        as_of=as_of,
        evaluated_at=as_of + timedelta(seconds=30),
        partition=partition,
        regime_key=regime,
        posterior_bps=_posterior(posterior_winner, confidence_bps),
        realized_quality=_quality(realized_winner),
    )


def test_summary_measures_monopoly_and_regime_recovery() -> None:
    episodes = (
        _episode(
            index=0,
            partition=WorldEvaluationPartition.CALIBRATION,
            regime="A",
            posterior_winner=WorldModelFamily.MOMENTUM_DRIVEN,
            realized_winner=WorldModelFamily.MOMENTUM_DRIVEN,
            confidence_bps=9_900,
        ),
        _episode(
            index=1,
            partition=WorldEvaluationPartition.CALIBRATION,
            regime="A",
            posterior_winner=WorldModelFamily.MOMENTUM_DRIVEN,
            realized_winner=WorldModelFamily.MOMENTUM_DRIVEN,
            confidence_bps=9_900,
        ),
        _episode(
            index=2,
            partition=WorldEvaluationPartition.CALIBRATION,
            regime="B",
            posterior_winner=WorldModelFamily.MOMENTUM_DRIVEN,
            realized_winner=WorldModelFamily.LIQUIDITY_DRIVEN,
            confidence_bps=9_000,
        ),
        _episode(
            index=3,
            partition=WorldEvaluationPartition.CALIBRATION,
            regime="B",
            posterior_winner=WorldModelFamily.LIQUIDITY_DRIVEN,
            realized_winner=WorldModelFamily.LIQUIDITY_DRIVEN,
            confidence_bps=7_000,
        ),
    )

    summary = summarize_world_calibration(episodes)

    assert summary.episode_count == 4
    assert summary.top_world_accuracy_bps == 7_500
    assert summary.monopoly_episode_count == 2
    assert summary.monopoly_rate_bps == 5_000
    assert summary.regime_shift_count == 1
    assert summary.recovered_regime_shift_count == 1
    assert summary.unresolved_regime_shift_count == 0
    assert summary.mean_recovery_steps_milli == 1_000
    assert summary.evaluation_only is True
    assert summary.trading_authority is False


def test_compare_calibration_to_temporally_disjoint_holdout() -> None:
    calibration = (
        _episode(
            index=0,
            partition=WorldEvaluationPartition.CALIBRATION,
            regime="A",
            posterior_winner=WorldModelFamily.MOMENTUM_DRIVEN,
            realized_winner=WorldModelFamily.MOMENTUM_DRIVEN,
            confidence_bps=8_000,
        ),
    )
    holdout = (
        _episode(
            index=0,
            partition=WorldEvaluationPartition.HOLDOUT,
            regime="C",
            posterior_winner=WorldModelFamily.LIQUIDITY_DRIVEN,
            realized_winner=WorldModelFamily.LIQUIDITY_DRIVEN,
            confidence_bps=7_500,
            offset_days=2,
        ),
    )

    comparison = compare_calibration_to_holdout(
        calibration=calibration,
        holdout=holdout,
    )

    assert comparison.temporal_holdout is True
    assert comparison.evaluation_only is True
    assert comparison.trading_authority is False


def test_compare_rejects_overlapping_holdout() -> None:
    calibration = (
        _episode(
            index=0,
            partition=WorldEvaluationPartition.CALIBRATION,
            regime="A",
            posterior_winner=WorldModelFamily.MOMENTUM_DRIVEN,
            realized_winner=WorldModelFamily.MOMENTUM_DRIVEN,
            confidence_bps=8_000,
        ),
    )
    holdout = (
        _episode(
            index=0,
            partition=WorldEvaluationPartition.HOLDOUT,
            regime="B",
            posterior_winner=WorldModelFamily.LIQUIDITY_DRIVEN,
            realized_winner=WorldModelFamily.LIQUIDITY_DRIVEN,
            confidence_bps=8_000,
        ),
    )

    with pytest.raises(ValueError, match="temporally disjoint"):
        compare_calibration_to_holdout(
            calibration=calibration,
            holdout=holdout,
        )


def test_evaluation_label_must_mature_after_posterior_timestamp() -> None:
    with pytest.raises(ValueError, match="mature after"):
        WorldCalibrationEpisode(
            as_of=BASE,
            evaluated_at=BASE,
            partition=WorldEvaluationPartition.CALIBRATION,
            regime_key="A",
            posterior_bps=_posterior(
                WorldModelFamily.MOMENTUM_DRIVEN,
                8_000,
            ),
            realized_quality=_quality(WorldModelFamily.MOMENTUM_DRIVEN),
        )

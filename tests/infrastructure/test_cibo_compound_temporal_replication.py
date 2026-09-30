from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from qore.infrastructure.account_wide_risk import TraderLineage
from qore.infrastructure.cibo_compound_capital import CiboCompoundCapitalError
from qore.infrastructure.cibo_compound_path_monte_carlo import (
    CompoundMonteCarloEpisode,
    CompoundMonteCarloInitialState,
)
from qore.infrastructure.cibo_compound_temporal_replication import (
    COMPOUND_TEMPORAL_REPLICATION_SHA256,
    CompoundTemporalFold,
    run_compound_temporal_replication,
)

T0 = datetime(2026, 1, 1, tzinfo=UTC)


def _initial() -> CompoundMonteCarloInitialState:
    return CompoundMonteCarloInitialState(
        original_base_usd=Decimal("100"),
        generation_capacity_usd=((1, Decimal("20")),),
        protected_floor_usd=Decimal(0),
        total_stop_risk_capacity_usd=Decimal("3"),
        total_margin_capacity_usd=Decimal("10"),
    )


def _episode(
    episode_id: str,
    *,
    start: datetime,
) -> CompoundMonteCarloEpisode:
    return CompoundMonteCarloEpisode(
        episode_id=episode_id,
        deployment_id=f"{episode_id}:deployment",
        market_event_id=f"{episode_id}:market",
        decision_id=f"{episode_id}:decision",
        candidate_id=f"{episode_id}:candidate",
        trader_id=TraderLineage.VT31_NAS100,
        signal_fingerprint=f"{episode_id}:signal",
        deployed_at=start,
        settled_at=start + timedelta(hours=1),
        source_generation=1,
        deployed_capital_usd=Decimal("5"),
        stop_risk_usd=Decimal("1"),
        margin_usd=Decimal("2"),
        realized_pnl_usd=Decimal("1"),
        protected_floor_graduation_usd=Decimal(0),
        floor_evidence_sha256=None,
        market_record_present=True,
        terminal_release_present=True,
    )


def _fold(
    fold_id: str,
    *,
    start: datetime,
) -> CompoundTemporalFold:
    return CompoundTemporalFold(
        fold_id=fold_id,
        start_at=start,
        end_at=start + timedelta(days=7),
        initial_state=_initial(),
        episodes=(_episode(f"{fold_id}-episode", start=start),),
        provider_economics_sha256="sha256:" + "a" * 64,
    )


def test_temporal_replication_digest_is_frozen() -> None:
    assert COMPOUND_TEMPORAL_REPLICATION_SHA256 == (
        "sha256:792db6db7efbc0a8427d475f5b72e178efdb0069ea31d0bdac3444fc9b13c5d2"
    )


def test_temporal_replication_runs_same_mechanics_per_fold() -> None:
    folds = (
        _fold("fold-a", start=T0),
        _fold("fold-b", start=T0 + timedelta(days=7)),
    )
    report = run_compound_temporal_replication(
        research_id="replication",
        folds=folds,
        simulations_per_fold=2,
        draws_per_path=1,
        components_per_block=1,
        base_seed=10,
    )

    assert report.fold_count == 2
    assert report.same_policy_mechanics_all_folds is True
    assert report.outcomes_pooled_across_folds is False
    assert report.economic_replication_claimed is False
    assert report.certification_ready is False


def test_temporal_replication_rejects_overlapping_folds() -> None:
    folds = (
        _fold("fold-a", start=T0),
        _fold("fold-b", start=T0 + timedelta(days=6)),
    )
    with pytest.raises(
        CiboCompoundCapitalError,
        match="must not overlap",
    ):
        run_compound_temporal_replication(
            research_id="bad",
            folds=folds,
            simulations_per_fold=1,
            draws_per_path=1,
            components_per_block=1,
            base_seed=1,
        )


def test_temporal_fold_rejects_episode_outside_boundary() -> None:
    with pytest.raises(
        CiboCompoundCapitalError,
        match="escapes fold boundary",
    ):
        CompoundTemporalFold(
            fold_id="bad",
            start_at=T0,
            end_at=T0 + timedelta(hours=2),
            initial_state=_initial(),
            episodes=(
                _episode("late", start=T0 + timedelta(hours=2)),
            ),
        )

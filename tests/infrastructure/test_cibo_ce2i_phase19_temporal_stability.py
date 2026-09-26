from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from qore.infrastructure.account_wide_risk import TraderLineage
from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)
from qore.infrastructure.cibo_ce2i_phase19_portfolio_replay import (
    PHASE19_REQUIRED_TRADERS,
    Phase19ChronologicalOpportunity,
)
from qore.infrastructure.cibo_ce2i_phase19_temporal_stability import (
    Phase19TemporalStabilityStatus,
    measure_phase19_temporal_overlap_stability,
)

START = datetime(2022, 1, 1, tzinfo=UTC)
SPLIT = datetime(2022, 1, 11, tzinfo=UTC)
END = datetime(2022, 1, 21, tzinfo=UTC)


def _opportunity(
    trader: TraderLineage,
    *,
    fingerprint: str,
    entry_at: datetime,
    minutes: int = 60,
) -> Phase19ChronologicalOpportunity:
    return Phase19ChronologicalOpportunity(
        trader_id=trader,
        signal_fingerprint=fingerprint,
        qore_symbol=trader.value,
        entry_at=entry_at,
        exit_at=entry_at + timedelta(minutes=minutes),
    )


def _fully_overlapping_segment(
    *,
    at: datetime,
    suffix: str,
) -> tuple[Phase19ChronologicalOpportunity, ...]:
    return tuple(
        _opportunity(
            trader,
            fingerprint=f"{trader.value}:{suffix}",
            entry_at=at,
        )
        for trader in PHASE19_REQUIRED_TRADERS
    )


def test_identical_train_validation_overlap_distribution_is_stable() -> None:
    opportunities = (
        *_fully_overlapping_segment(
            at=START + timedelta(days=2),
            suffix="train",
        ),
        *_fully_overlapping_segment(
            at=SPLIT + timedelta(days=2),
            suffix="validation",
        ),
    )

    evidence = measure_phase19_temporal_overlap_stability(
        opportunities=opportunities,
        common_window_start=START,
        split_at=SPLIT,
        common_window_end=END,
    )

    assert evidence.status is (
        Phase19TemporalStabilityStatus.MEASURED_OBSERVATIONAL_ONLY
    )
    assert evidence.training_cross_trader_overlap_pairs == 21
    assert evidence.validation_cross_trader_overlap_pairs == 21
    assert evidence.total_variation_distance == Decimal(0)
    assert evidence.weighted_jaccard_similarity == Decimal(1)
    assert len(evidence.pair_stability) == 21


def test_boundary_crossing_position_is_excluded_from_both_segments() -> None:
    opportunities = (
        *_fully_overlapping_segment(
            at=START + timedelta(days=2),
            suffix="train",
        ),
        *_fully_overlapping_segment(
            at=SPLIT + timedelta(days=2),
            suffix="validation",
        ),
        _opportunity(
            TraderLineage.VT31_NAS100,
            fingerprint="boundary-crossing",
            entry_at=SPLIT - timedelta(minutes=30),
            minutes=60,
        ),
    )

    evidence = measure_phase19_temporal_overlap_stability(
        opportunities=opportunities,
        common_window_start=START,
        split_at=SPLIT,
        common_window_end=END,
    )

    assert evidence.boundary_crossing_opportunities_excluded == 1
    assert evidence.training_opportunities == 7
    assert evidence.validation_opportunities == 7
    assert evidence.total_variation_distance == Decimal(0)


def test_incomplete_validation_population_is_insufficient() -> None:
    training = _fully_overlapping_segment(
        at=START + timedelta(days=2),
        suffix="train",
    )
    validation = tuple(
        _opportunity(
            trader,
            fingerprint=f"{trader.value}:validation",
            entry_at=SPLIT + timedelta(days=2),
        )
        for trader in PHASE19_REQUIRED_TRADERS[:-1]
    )

    evidence = measure_phase19_temporal_overlap_stability(
        opportunities=(*training, *validation),
        common_window_start=START,
        split_at=SPLIT,
        common_window_end=END,
    )

    assert evidence.status is (
        Phase19TemporalStabilityStatus.INSUFFICIENT_SEGMENT_COVERAGE
    )
    assert TraderLineage.VT31_NAS100 not in evidence.validation_population


def test_temporal_stability_rejects_opportunity_outside_common_window() -> None:
    outside = _opportunity(
        TraderLineage.R34_XAUUSD,
        fingerprint="outside",
        entry_at=START - timedelta(minutes=30),
    )

    with pytest.raises(
        CiboCapitalManagementError,
        match="outside common window",
    ):
        measure_phase19_temporal_overlap_stability(
            opportunities=(outside,),
            common_window_start=START,
            split_at=SPLIT,
            common_window_end=END,
        )

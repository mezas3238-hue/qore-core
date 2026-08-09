from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime, timedelta
from uuid import UUID

import pytest

from qore.infrastructure.research_economic_evidence import (
    ResearchFillEvidence,
    ResearchGrossEconomicResult,
    ResearchReturnObservation,
    ResearchReturnObservationId,
)
from qore.infrastructure.research_frozen_oos_evidence import ResearchFrozenOosEvidence
from qore.infrastructure.research_oos_performance import (
    ResearchOosFoldPerformance,
    ResearchOosPerformanceEvidence,
)
from qore.infrastructure.research_performance_statistics import (
    ResearchPerformanceStatisticsSnapshot,
)
from qore.infrastructure.research_sampling_frame import (
    ResearchHoldingOverlapStatus,
    ResearchSamplingFrameId,
    ResearchSamplingFrameValidationError,
    ResearchSamplingUnit,
    build_research_sampling_frame,
)
from qore.kernel.result import Failure, Success

_BASE = datetime(2026, 1, 5, 12, 0, tzinfo=UTC)


def _uuid(suffix: int) -> UUID:
    return UUID(f"74000000-0000-0000-0000-{suffix:012d}")


def _fill(at: datetime) -> ResearchFillEvidence:
    fill = object.__new__(ResearchFillEvidence)
    object.__setattr__(fill, "filled_at", at)
    return fill


def _sample(
    *,
    suffix: int,
    opened_at: datetime,
    closed_at: datetime,
) -> ResearchReturnObservation:
    gross = object.__new__(ResearchGrossEconomicResult)
    object.__setattr__(gross, "entry_fills", (_fill(opened_at),))
    object.__setattr__(gross, "exit_fills", (_fill(closed_at),))
    object.__setattr__(gross, "valued_at", closed_at + timedelta(seconds=1))

    observation = object.__new__(ResearchReturnObservation)
    object.__setattr__(observation, "observation_id", ResearchReturnObservationId(_uuid(suffix)))
    object.__setattr__(observation, "source_result", gross)
    return observation


def _statistics(
    observations: tuple[ResearchReturnObservation, ...],
) -> ResearchPerformanceStatisticsSnapshot:
    statistics = object.__new__(ResearchPerformanceStatisticsSnapshot)
    object.__setattr__(statistics, "observations", observations)
    return statistics


def _fold_performance(
    observations: tuple[ResearchReturnObservation, ...],
) -> ResearchOosFoldPerformance:
    fold = object.__new__(ResearchOosFoldPerformance)
    object.__setattr__(fold, "statistics", _statistics(observations))
    return fold


def _frozen_oos(
    folds: tuple[tuple[ResearchReturnObservation, ...], ...],
) -> ResearchFrozenOosEvidence:
    oos = object.__new__(ResearchOosPerformanceEvidence)
    object.__setattr__(
        oos,
        "fold_performance",
        tuple(_fold_performance(observations) for observations in folds),
    )
    frozen = object.__new__(ResearchFrozenOosEvidence)
    object.__setattr__(frozen, "oos_performance", oos)
    return frozen


def test_sampling_frame_derives_canonical_samples_and_fold_sizes() -> None:
    first = _sample(
        suffix=1,
        opened_at=_BASE,
        closed_at=_BASE + timedelta(minutes=5),
    )
    second = _sample(
        suffix=2,
        opened_at=_BASE + timedelta(minutes=10),
        closed_at=_BASE + timedelta(minutes=15),
    )
    frozen = _frozen_oos(((second,), (first,)))

    built = build_research_sampling_frame(
        frame_id=ResearchSamplingFrameId(_uuid(100)),
        frozen_oos=frozen,
    )

    assert isinstance(built, Success)
    frame = built.value
    assert frame.sampling_unit is ResearchSamplingUnit.CLOSED_ECONOMIC_RESULT_RETURN
    assert frame.samples == (first, second)
    assert frame.fold_sample_sizes == (1, 1)
    assert frame.sample_size == 2
    assert frame.overlap_status is ResearchHoldingOverlapStatus.NON_OVERLAPPING
    assert frame.overlapping_pairs == ()


def test_sampling_frame_detects_overlapping_holding_intervals() -> None:
    first = _sample(
        suffix=10,
        opened_at=_BASE,
        closed_at=_BASE + timedelta(minutes=10),
    )
    second = _sample(
        suffix=11,
        opened_at=_BASE + timedelta(minutes=5),
        closed_at=_BASE + timedelta(minutes=15),
    )

    built = build_research_sampling_frame(
        frame_id=ResearchSamplingFrameId(_uuid(110)),
        frozen_oos=_frozen_oos(((first, second),)),
    )

    assert isinstance(built, Success)
    frame = built.value
    assert frame.overlap_status is ResearchHoldingOverlapStatus.OVERLAPPING
    assert frame.overlapping_pairs == ((first.observation_id, second.observation_id),)


def test_touching_half_open_holding_intervals_are_not_overlapping() -> None:
    first = _sample(
        suffix=20,
        opened_at=_BASE,
        closed_at=_BASE + timedelta(minutes=5),
    )
    second = _sample(
        suffix=21,
        opened_at=_BASE + timedelta(minutes=5),
        closed_at=_BASE + timedelta(minutes=10),
    )

    built = build_research_sampling_frame(
        frame_id=ResearchSamplingFrameId(_uuid(120)),
        frozen_oos=_frozen_oos(((first, second),)),
    )

    assert isinstance(built, Success)
    assert built.value.overlap_status is ResearchHoldingOverlapStatus.NON_OVERLAPPING


def test_sampling_frame_rejects_duplicate_return_identity() -> None:
    first = _sample(
        suffix=30,
        opened_at=_BASE,
        closed_at=_BASE + timedelta(minutes=5),
    )
    duplicate = _sample(
        suffix=30,
        opened_at=_BASE + timedelta(minutes=10),
        closed_at=_BASE + timedelta(minutes=15),
    )

    built = build_research_sampling_frame(
        frame_id=ResearchSamplingFrameId(_uuid(130)),
        frozen_oos=_frozen_oos(((first, duplicate),)),
    )

    assert isinstance(built, Failure)
    assert "observation ids must be unique" in str(built.error)


def test_sampling_frame_rejects_derived_overlap_tampering() -> None:
    first = _sample(
        suffix=40,
        opened_at=_BASE,
        closed_at=_BASE + timedelta(minutes=10),
    )
    second = _sample(
        suffix=41,
        opened_at=_BASE + timedelta(minutes=5),
        closed_at=_BASE + timedelta(minutes=15),
    )
    built = build_research_sampling_frame(
        frame_id=ResearchSamplingFrameId(_uuid(140)),
        frozen_oos=_frozen_oos(((first, second),)),
    )
    assert isinstance(built, Success)

    with pytest.raises(ResearchSamplingFrameValidationError):
        replace(
            built.value,
            overlap_status=ResearchHoldingOverlapStatus.NON_OVERLAPPING,
        )


def test_non_overlap_does_not_claim_independence_or_significance() -> None:
    sample = _sample(
        suffix=50,
        opened_at=_BASE,
        closed_at=_BASE + timedelta(minutes=5),
    )
    built = build_research_sampling_frame(
        frame_id=ResearchSamplingFrameId(_uuid(150)),
        frozen_oos=_frozen_oos(((sample,),)),
    )
    assert isinstance(built, Success)
    frame = built.value
    assert not hasattr(frame, "iid")
    assert not hasattr(frame, "independent")
    assert not hasattr(frame, "stationary")
    assert not hasattr(frame, "p_value")
    assert not hasattr(frame, "statistically_significant")

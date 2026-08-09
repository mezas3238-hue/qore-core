from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID

import pytest

from qore.infrastructure.research_confidence_calibration import (
    ResearchCalibrationTarget,
    ResearchConfidenceCalibrationPolicy,
    ResearchConfidenceCalibrationValidationError,
    ResearchConfidenceOutcomeObservation,
    build_research_confidence_calibration_snapshot,
)
from qore.kernel.result import Failure, Success
from qore.specialist.analysis import (
    SpecialistAnalysis,
    SpecialistAnalysisId,
    SpecialistAnalysisStatus,
    SpecialistConfidence,
    SpecialistKind,
)

_BASE = datetime(2026, 8, 9, 20, 0, tzinfo=UTC)


def _analysis(
    suffix: int,
    confidence: float | None,
    *,
    minutes: int = 0,
    kind: str = "virtual-trader.fx",
    status: SpecialistAnalysisStatus = SpecialistAnalysisStatus.COMPLETED,
) -> SpecialistAnalysis:
    analysis = object.__new__(SpecialistAnalysis)
    object.__setattr__(analysis, "analysis_id", SpecialistAnalysisId(UUID(int=suffix)))
    object.__setattr__(analysis, "timestamp", _BASE + timedelta(minutes=minutes))
    object.__setattr__(analysis, "kind", SpecialistKind(kind))
    object.__setattr__(analysis, "status", status)
    object.__setattr__(
        analysis,
        "confidence",
        SpecialistConfidence(confidence) if confidence is not None else None,
    )
    object.__setattr__(analysis, "metadata", None)
    object.__setattr__(analysis, "reasons", ())
    return analysis


def _observation(
    suffix: int,
    confidence: float,
    occurred: bool,
    *,
    minutes: int = 0,
    target: str = "next-period-positive-return",
    kind: str = "virtual-trader.fx",
) -> ResearchConfidenceOutcomeObservation:
    return ResearchConfidenceOutcomeObservation(
        analysis=_analysis(suffix, confidence, minutes=minutes, kind=kind),
        target=ResearchCalibrationTarget(target),
        event_occurred=occurred,
    )


def test_calibration_snapshot_derives_brier_reliability_bins_and_ece() -> None:
    built = build_research_confidence_calibration_snapshot(
        policy=ResearchConfidenceCalibrationPolicy(bin_count=2),
        observations=(
            _observation(2, 0.8, True, minutes=2),
            _observation(1, 0.2, False, minutes=1),
        ),
    )

    assert isinstance(built, Success)
    snapshot = built.value
    assert tuple(item.analysis.analysis_id.value.int for item in snapshot.observations) == (
        1,
        2,
    )
    assert snapshot.sample_size == 2
    assert snapshot.mean_confidence == Decimal("0.5")
    assert snapshot.empirical_event_rate == Decimal("0.5")
    assert snapshot.brier_score == Decimal("0.04")
    assert tuple(item.index for item in snapshot.bins) == (0, 1)
    assert tuple(item.sample_size for item in snapshot.bins) == (1, 1)
    assert tuple(item.absolute_gap for item in snapshot.bins) == (
        Decimal("0.2"),
        Decimal("0.2"),
    )
    assert snapshot.expected_calibration_error == Decimal("0.20")


def test_confidence_one_belongs_to_last_bin() -> None:
    built = build_research_confidence_calibration_snapshot(
        policy=ResearchConfidenceCalibrationPolicy(bin_count=4),
        observations=(
            _observation(10, 1.0, True),
            _observation(11, 0.0, False, minutes=1),
        ),
    )

    assert isinstance(built, Success)
    assert tuple(item.index for item in built.value.bins) == (0, 3)
    assert built.value.bins[-1].upper_bound == Decimal("1.00")


def test_calibration_rejects_duplicate_analysis_ids() -> None:
    first = _observation(20, 0.4, False)
    duplicate = ResearchConfidenceOutcomeObservation(
        analysis=_analysis(20, 0.6, minutes=1),
        target=first.target,
        event_occurred=True,
    )

    built = build_research_confidence_calibration_snapshot(
        policy=ResearchConfidenceCalibrationPolicy(bin_count=2),
        observations=(first, duplicate),
    )

    assert isinstance(built, Failure)
    assert "unique" in str(built.error)


def test_calibration_rejects_mixed_target_or_specialist_kind() -> None:
    mixed_target = build_research_confidence_calibration_snapshot(
        policy=ResearchConfidenceCalibrationPolicy(bin_count=2),
        observations=(
            _observation(30, 0.4, False, target="target-a"),
            _observation(31, 0.6, True, target="target-b", minutes=1),
        ),
    )
    mixed_kind = build_research_confidence_calibration_snapshot(
        policy=ResearchConfidenceCalibrationPolicy(bin_count=2),
        observations=(
            _observation(32, 0.4, False, kind="virtual-trader.fx"),
            _observation(
                33,
                0.6,
                True,
                kind="virtual-trader.futures",
                minutes=1,
            ),
        ),
    )

    assert isinstance(mixed_target, Failure)
    assert isinstance(mixed_kind, Failure)


def test_calibration_observation_requires_completed_confident_analysis() -> None:
    target = ResearchCalibrationTarget("next-period-positive-return")
    with pytest.raises(ResearchConfidenceCalibrationValidationError):
        ResearchConfidenceOutcomeObservation(
            analysis=_analysis(
                40,
                None,
                status=SpecialistAnalysisStatus.PENDING,
            ),
            target=target,
            event_occurred=False,
        )
    with pytest.raises(ResearchConfidenceCalibrationValidationError):
        ResearchConfidenceOutcomeObservation(
            analysis=_analysis(41, None),
            target=target,
            event_occurred=False,
        )


def test_calibration_policy_rejects_invalid_bin_count() -> None:
    for value in (1, 101, 2.0, True):
        with pytest.raises(ResearchConfidenceCalibrationValidationError):
            ResearchConfidenceCalibrationPolicy(bin_count=value)  # type: ignore[arg-type]


def test_calibration_snapshot_rejects_derived_metric_tampering() -> None:
    built = build_research_confidence_calibration_snapshot(
        policy=ResearchConfidenceCalibrationPolicy(bin_count=2),
        observations=(
            _observation(50, 0.2, False),
            _observation(51, 0.8, True, minutes=1),
        ),
    )
    assert isinstance(built, Success)

    with pytest.raises(ResearchConfidenceCalibrationValidationError):
        replace(built.value, brier_score=Decimal("0.99"))
    with pytest.raises(ResearchConfidenceCalibrationValidationError):
        replace(built.value, expected_calibration_error=Decimal("0.99"))


def test_calibration_diagnostics_do_not_convert_confidence_to_probability() -> None:
    built = build_research_confidence_calibration_snapshot(
        policy=ResearchConfidenceCalibrationPolicy(bin_count=2),
        observations=(
            _observation(60, 0.2, False),
            _observation(61, 0.8, True, minutes=1),
        ),
    )
    assert isinstance(built, Success)
    snapshot = built.value

    assert not hasattr(snapshot, "calibrated_probability")
    assert not hasattr(snapshot, "probability_mapping")
    assert not hasattr(snapshot, "is_calibrated")
    assert not hasattr(snapshot, "strategy_approved")
    assert not hasattr(snapshot, "production_ready")
    assert not hasattr(snapshot, "capital_authorized")

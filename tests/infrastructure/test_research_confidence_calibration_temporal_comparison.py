from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID

import pytest

from qore.infrastructure.research_confidence_calibration import (
    ResearchConfidenceOutcomeObservation,
)
from qore.infrastructure.research_confidence_calibration_mapping import (
    ResearchCalibrationMappingFingerprint,
    ResearchCalibrationMappingId,
    ResearchConfidenceCalibrationMappingFit,
)
from qore.infrastructure.research_confidence_calibration_oos_validation import (
    ResearchCalibrationOosValidationEvidence,
    ResearchCalibrationOosValidationFingerprint,
    ResearchCalibrationOosValidationObservation,
    ResearchCalibrationOosValidationPolicy,
    ResearchCalibrationOosValidationSet,
)
from qore.infrastructure.research_confidence_calibration_temporal_comparison import (
    ResearchCalibrationTemporalComparisonId,
    ResearchCalibrationTemporalComparisonValidationError,
    build_research_calibration_temporal_comparison_evidence,
)
from qore.kernel.result import Failure, Success
from qore.specialist.analysis import SpecialistAnalysis, SpecialistAnalysisId

_BASE = datetime(2026, 1, 5, 14, 0, tzinfo=UTC)


def _mapping(*, suffix: int = 1, fingerprint: str = "a") -> ResearchConfidenceCalibrationMappingFit:
    fit = object.__new__(ResearchConfidenceCalibrationMappingFit)
    object.__setattr__(fit, "mapping_id", ResearchCalibrationMappingId(UUID(int=suffix)))
    object.__setattr__(
        fit,
        "fingerprint",
        ResearchCalibrationMappingFingerprint(fingerprint * 64),
    )
    return fit


def _source(suffix: int) -> ResearchConfidenceOutcomeObservation:
    analysis = object.__new__(SpecialistAnalysis)
    object.__setattr__(analysis, "analysis_id", SpecialistAnalysisId(UUID(int=suffix)))
    source = object.__new__(ResearchConfidenceOutcomeObservation)
    object.__setattr__(source, "analysis", analysis)
    return source


def _observation(
    *,
    suffix: int,
    score_at: datetime,
    outcome_at: datetime,
) -> ResearchCalibrationOosValidationObservation:
    observation = object.__new__(ResearchCalibrationOosValidationObservation)
    object.__setattr__(observation, "source", _source(suffix))
    object.__setattr__(observation, "score_observed_at", score_at)
    object.__setattr__(observation, "outcome_observed_at", outcome_at)
    return observation


def _validation(
    *,
    mapping: ResearchConfidenceCalibrationMappingFit,
    observations: tuple[ResearchCalibrationOosValidationObservation, ...],
    mean_probability: str,
    event_rate: str,
    ece: str,
    fingerprint: str,
    bin_count: int = 4,
) -> ResearchCalibrationOosValidationEvidence:
    validation_set = object.__new__(ResearchCalibrationOosValidationSet)
    object.__setattr__(validation_set, "mapping_fit", mapping)
    object.__setattr__(validation_set, "fold_number", 1)
    object.__setattr__(validation_set, "observations", observations)
    validation = object.__new__(ResearchCalibrationOosValidationEvidence)
    object.__setattr__(validation, "validation_set", validation_set)
    object.__setattr__(
        validation,
        "policy",
        ResearchCalibrationOosValidationPolicy(bin_count=bin_count),
    )
    object.__setattr__(
        validation,
        "mean_estimated_probability",
        Decimal(mean_probability),
    )
    object.__setattr__(validation, "empirical_event_rate", Decimal(event_rate))
    object.__setattr__(validation, "expected_calibration_error", Decimal(ece))
    object.__setattr__(
        validation,
        "fingerprint",
        ResearchCalibrationOosValidationFingerprint(fingerprint * 64),
    )
    return validation


def _baseline(
    mapping: ResearchConfidenceCalibrationMappingFit,
) -> ResearchCalibrationOosValidationEvidence:
    return _validation(
        mapping=mapping,
        observations=(
            _observation(
                suffix=11,
                score_at=_BASE + timedelta(minutes=10),
                outcome_at=_BASE + timedelta(minutes=15),
            ),
            _observation(
                suffix=12,
                score_at=_BASE + timedelta(minutes=20),
                outcome_at=_BASE + timedelta(minutes=25),
            ),
        ),
        mean_probability="0.50",
        event_rate="0.45",
        ece="0.04",
        fingerprint="b",
    )


def _comparison(
    mapping: ResearchConfidenceCalibrationMappingFit,
) -> ResearchCalibrationOosValidationEvidence:
    return _validation(
        mapping=mapping,
        observations=(
            _observation(
                suffix=13,
                score_at=_BASE + timedelta(minutes=40),
                outcome_at=_BASE + timedelta(minutes=45),
            ),
            _observation(
                suffix=14,
                score_at=_BASE + timedelta(minutes=50),
                outcome_at=_BASE + timedelta(minutes=55),
            ),
        ),
        mean_probability="0.60",
        event_rate="0.50",
        ece="0.10",
        fingerprint="c",
    )


def test_temporal_comparison_reports_diagnostics_without_declaring_drift() -> None:
    mapping = _mapping()
    built = build_research_calibration_temporal_comparison_evidence(
        comparison_id=ResearchCalibrationTemporalComparisonId(UUID(int=9001)),
        baseline=_baseline(mapping),
        comparison=_comparison(mapping),
    )

    assert isinstance(built, Success)
    evidence = built.value
    assert evidence.baseline_sample_size == 2
    assert evidence.comparison_sample_size == 2
    assert evidence.baseline_absolute_mean_gap == Decimal("0.05")
    assert evidence.comparison_absolute_mean_gap == Decimal("0.10")
    assert evidence.absolute_mean_gap_change == Decimal("0.05")
    assert evidence.absolute_ece_change == Decimal("0.06")
    assert evidence.absolute_mean_probability_shift == Decimal("0.10")
    assert evidence.absolute_event_rate_shift == Decimal("0.05")
    assert not hasattr(evidence, "drift_detected")
    assert not hasattr(evidence, "statistically_significant")
    assert not hasattr(evidence, "calibrated_probability")
    assert not hasattr(evidence, "production_ready")
    assert not hasattr(evidence, "capital_authorized")


def test_temporal_comparison_requires_same_mapping_identity_and_fingerprint() -> None:
    baseline_mapping = _mapping(suffix=1, fingerprint="a")
    different_id = _mapping(suffix=2, fingerprint="a")
    different_fingerprint = _mapping(suffix=1, fingerprint="d")

    for comparison_mapping in (different_id, different_fingerprint):
        built = build_research_calibration_temporal_comparison_evidence(
            comparison_id=ResearchCalibrationTemporalComparisonId(UUID(int=9101)),
            baseline=_baseline(baseline_mapping),
            comparison=_comparison(comparison_mapping),
        )
        assert isinstance(built, Failure)
        assert "mapping" in str(built.error)


def test_temporal_comparison_requires_same_oos_diagnostic_policy() -> None:
    mapping = _mapping()
    comparison = _comparison(mapping)
    object.__setattr__(
        comparison,
        "policy",
        ResearchCalibrationOosValidationPolicy(bin_count=5),
    )

    built = build_research_calibration_temporal_comparison_evidence(
        comparison_id=ResearchCalibrationTemporalComparisonId(UUID(int=9151)),
        baseline=_baseline(mapping),
        comparison=comparison,
    )

    assert isinstance(built, Failure)
    assert "diagnostic policy" in str(built.error)


def test_temporal_comparison_rejects_reused_analysis_identity() -> None:
    mapping = _mapping()
    comparison = _comparison(mapping)
    reused = _observation(
        suffix=11,
        score_at=_BASE + timedelta(minutes=40),
        outcome_at=_BASE + timedelta(minutes=45),
    )
    object.__setattr__(
        comparison.validation_set,
        "observations",
        (reused, comparison.validation_set.observations[1]),
    )

    built = build_research_calibration_temporal_comparison_evidence(
        comparison_id=ResearchCalibrationTemporalComparisonId(UUID(int=9201)),
        baseline=_baseline(mapping),
        comparison=comparison,
    )

    assert isinstance(built, Failure)
    assert "disjoint" in str(built.error)


def test_temporal_comparison_rejects_overlapping_or_reversed_windows() -> None:
    mapping = _mapping()
    overlapping = _comparison(mapping)
    object.__setattr__(
        overlapping.validation_set.observations[0],
        "score_observed_at",
        _BASE + timedelta(minutes=24),
    )
    object.__setattr__(
        overlapping.validation_set.observations[0],
        "outcome_observed_at",
        _BASE + timedelta(minutes=29),
    )
    built = build_research_calibration_temporal_comparison_evidence(
        comparison_id=ResearchCalibrationTemporalComparisonId(UUID(int=9301)),
        baseline=_baseline(mapping),
        comparison=overlapping,
    )
    assert isinstance(built, Failure)
    assert "finish" in str(built.error)

    reversed_time = _comparison(mapping)
    object.__setattr__(
        reversed_time.validation_set.observations[0],
        "score_observed_at",
        _BASE + timedelta(minutes=45),
    )
    object.__setattr__(
        reversed_time.validation_set.observations[0],
        "outcome_observed_at",
        _BASE + timedelta(minutes=40),
    )
    built = build_research_calibration_temporal_comparison_evidence(
        comparison_id=ResearchCalibrationTemporalComparisonId(UUID(int=9302)),
        baseline=_baseline(mapping),
        comparison=reversed_time,
    )
    assert isinstance(built, Failure)
    assert "precede" in str(built.error)


def test_temporal_comparison_rejects_naive_simulated_time() -> None:
    mapping = _mapping()
    comparison = _comparison(mapping)
    object.__setattr__(
        comparison.validation_set.observations[0],
        "score_observed_at",
        datetime(2026, 1, 5, 14, 40),
    )

    built = build_research_calibration_temporal_comparison_evidence(
        comparison_id=ResearchCalibrationTemporalComparisonId(UUID(int=9401)),
        baseline=_baseline(mapping),
        comparison=comparison,
    )

    assert isinstance(built, Failure)
    assert "timezone-aware" in str(built.error)


def test_temporal_comparison_fingerprint_excludes_administrative_id() -> None:
    mapping = _mapping()
    baseline = _baseline(mapping)
    comparison = _comparison(mapping)
    first = build_research_calibration_temporal_comparison_evidence(
        comparison_id=ResearchCalibrationTemporalComparisonId(UUID(int=9501)),
        baseline=baseline,
        comparison=comparison,
    )
    second = build_research_calibration_temporal_comparison_evidence(
        comparison_id=ResearchCalibrationTemporalComparisonId(UUID(int=9502)),
        baseline=baseline,
        comparison=comparison,
    )

    assert isinstance(first, Success)
    assert isinstance(second, Success)
    assert first.value.fingerprint == second.value.fingerprint


def test_temporal_comparison_rejects_metric_and_fingerprint_tampering() -> None:
    mapping = _mapping()
    built = build_research_calibration_temporal_comparison_evidence(
        comparison_id=ResearchCalibrationTemporalComparisonId(UUID(int=9601)),
        baseline=_baseline(mapping),
        comparison=_comparison(mapping),
    )
    assert isinstance(built, Success)

    with pytest.raises(ResearchCalibrationTemporalComparisonValidationError):
        replace(built.value, absolute_ece_change=Decimal("0.01"))
    with pytest.raises(ResearchCalibrationTemporalComparisonValidationError):
        replace(
            built.value,
            fingerprint=replace(built.value.fingerprint, value="d" * 64),
        )

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
    ResearchCalibrationMappingBlock,
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
    ResearchCalibrationTemporalComparisonEvidence,
    ResearchCalibrationTemporalComparisonId,
    build_research_calibration_temporal_comparison_evidence,
)
from qore.infrastructure.research_confidence_calibration_temporal_comparison_uncertainty import (
    ResearchCalibrationTemporalComparisonUncertaintyId,
    ResearchCalibrationTemporalComparisonUncertaintyPolicy,
    ResearchCalibrationTemporalComparisonUncertaintyValidationError,
    build_research_calibration_temporal_comparison_uncertainty_evidence,
)
from qore.infrastructure.research_confidence_calibration_uncertainty import (
    ResearchCalibrationIntervalMethod,
)
from qore.kernel.result import Failure, Success
from qore.specialist.analysis import (
    SpecialistAnalysis,
    SpecialistAnalysisId,
    SpecialistConfidence,
)

_BASE = datetime(2026, 1, 5, 14, 0, tzinfo=UTC)


def _mapping() -> ResearchConfidenceCalibrationMappingFit:
    fit = object.__new__(ResearchConfidenceCalibrationMappingFit)
    object.__setattr__(fit, "mapping_id", ResearchCalibrationMappingId(UUID(int=1)))
    object.__setattr__(
        fit,
        "fingerprint",
        ResearchCalibrationMappingFingerprint("a" * 64),
    )
    object.__setattr__(
        fit,
        "blocks",
        (
            ResearchCalibrationMappingBlock(
                lower_score=Decimal("0.1"),
                upper_score=Decimal("0.1"),
                estimated_probability=Decimal("0"),
                sample_size=1,
            ),
            ResearchCalibrationMappingBlock(
                lower_score=Decimal("0.3"),
                upper_score=Decimal("0.6"),
                estimated_probability=Decimal("0.5"),
                sample_size=2,
            ),
            ResearchCalibrationMappingBlock(
                lower_score=Decimal("0.9"),
                upper_score=Decimal("0.9"),
                estimated_probability=Decimal("1"),
                sample_size=1,
            ),
        ),
    )
    return fit


def _source(
    *,
    suffix: int,
    confidence: float,
    occurred: bool,
) -> ResearchConfidenceOutcomeObservation:
    analysis = object.__new__(SpecialistAnalysis)
    object.__setattr__(analysis, "analysis_id", SpecialistAnalysisId(UUID(int=suffix)))
    object.__setattr__(analysis, "confidence", SpecialistConfidence(confidence))
    source = object.__new__(ResearchConfidenceOutcomeObservation)
    object.__setattr__(source, "analysis", analysis)
    object.__setattr__(source, "event_occurred", occurred)
    return source


def _observation(
    *,
    suffix: int,
    confidence: float,
    occurred: bool,
    minutes: int,
) -> ResearchCalibrationOosValidationObservation:
    observation = object.__new__(ResearchCalibrationOosValidationObservation)
    object.__setattr__(
        observation,
        "source",
        _source(suffix=suffix, confidence=confidence, occurred=occurred),
    )
    object.__setattr__(
        observation,
        "score_observed_at",
        _BASE + timedelta(minutes=minutes),
    )
    object.__setattr__(
        observation,
        "outcome_observed_at",
        _BASE + timedelta(minutes=minutes + 5),
    )
    return observation


def _validation(
    *,
    mapping: ResearchConfidenceCalibrationMappingFit,
    observations: tuple[ResearchCalibrationOosValidationObservation, ...],
    mean_probability: str,
    event_rate: str,
    ece: str,
    fingerprint: str,
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
        ResearchCalibrationOosValidationPolicy(bin_count=4),
    )
    object.__setattr__(validation, "sample_size", len(observations))
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


def _baseline(mapping: ResearchConfidenceCalibrationMappingFit) -> ResearchCalibrationOosValidationEvidence:
    return _validation(
        mapping=mapping,
        observations=(
            _observation(
                suffix=11,
                confidence=0.2,
                occurred=False,
                minutes=10,
            ),
            _observation(
                suffix=12,
                confidence=0.4,
                occurred=True,
                minutes=20,
            ),
            _observation(
                suffix=13,
                confidence=0.8,
                occurred=False,
                minutes=30,
            ),
            _observation(
                suffix=14,
                confidence=0.95,
                occurred=True,
                minutes=40,
            ),
        ),
        mean_probability="0.5",
        event_rate="0.5",
        ece="0",
        fingerprint="b",
    )


def _comparison(mapping: ResearchConfidenceCalibrationMappingFit) -> ResearchCalibrationOosValidationEvidence:
    return _validation(
        mapping=mapping,
        observations=(
            _observation(
                suffix=21,
                confidence=0.2,
                occurred=True,
                minutes=70,
            ),
            _observation(
                suffix=22,
                confidence=0.4,
                occurred=True,
                minutes=80,
            ),
            _observation(
                suffix=23,
                confidence=0.8,
                occurred=True,
                minutes=90,
            ),
            _observation(
                suffix=24,
                confidence=0.95,
                occurred=False,
                minutes=100,
            ),
        ),
        mean_probability="0.5",
        event_rate="0.75",
        ece="0.75",
        fingerprint="c",
    )


def _temporal_comparison() -> ResearchCalibrationTemporalComparisonEvidence:
    mapping = _mapping()
    built = build_research_calibration_temporal_comparison_evidence(
        comparison_id=ResearchCalibrationTemporalComparisonId(UUID(int=10001)),
        baseline=_baseline(mapping),
        comparison=_comparison(mapping),
    )
    assert isinstance(built, Success)
    return built.value


def _policy() -> ResearchCalibrationTemporalComparisonUncertaintyPolicy:
    return ResearchCalibrationTemporalComparisonUncertaintyPolicy(
        baseline_block_length=2,
        comparison_block_length=2,
        resample_count=32,
        seed=17,
        confidence_level=Decimal("0.80"),
        interval_method=ResearchCalibrationIntervalMethod.PERCENTILE_NEAREST_RANK,
    )


def test_temporal_comparison_uncertainty_is_deterministic_and_research_only() -> None:
    comparison = _temporal_comparison()
    first = build_research_calibration_temporal_comparison_uncertainty_evidence(
        uncertainty_id=ResearchCalibrationTemporalComparisonUncertaintyId(
            UUID(int=11001)
        ),
        comparison=comparison,
        policy=_policy(),
    )
    second = build_research_calibration_temporal_comparison_uncertainty_evidence(
        uncertainty_id=ResearchCalibrationTemporalComparisonUncertaintyId(
            UUID(int=11002)
        ),
        comparison=comparison,
        policy=_policy(),
    )

    assert isinstance(first, Success)
    assert isinstance(second, Success)
    evidence = first.value
    assert evidence.source_absolute_mean_gap_change == Decimal("0.25")
    assert evidence.source_absolute_ece_change == Decimal("0.75")
    assert evidence.source_absolute_mean_probability_shift == Decimal("0")
    assert evidence.source_absolute_event_rate_shift == Decimal("0.25")
    assert len(evidence.resampled_absolute_mean_gap_changes) == 32
    assert len(evidence.resampled_absolute_ece_changes) == 32
    assert len(evidence.resampled_absolute_mean_probability_shifts) == 32
    assert len(evidence.resampled_absolute_event_rate_shifts) == 32
    assert evidence.fingerprint == second.value.fingerprint
    assert (
        evidence.resampled_absolute_ece_changes
        == second.value.resampled_absolute_ece_changes
    )
    assert not hasattr(evidence, "drift_detected")
    assert not hasattr(evidence, "p_value")
    assert not hasattr(evidence, "statistically_significant")
    assert not hasattr(evidence, "calibrated_probability")
    assert not hasattr(evidence, "production_ready")
    assert not hasattr(evidence, "capital_authorized")


def test_temporal_comparison_uncertainty_intervals_are_bounded() -> None:
    built = build_research_calibration_temporal_comparison_uncertainty_evidence(
        uncertainty_id=ResearchCalibrationTemporalComparisonUncertaintyId(
            UUID(int=12001)
        ),
        comparison=_temporal_comparison(),
        policy=_policy(),
    )
    assert isinstance(built, Success)

    intervals = (
        built.value.absolute_mean_gap_change_interval,
        built.value.absolute_ece_change_interval,
        built.value.absolute_mean_probability_shift_interval,
        built.value.absolute_event_rate_shift_interval,
    )
    for interval in intervals:
        assert Decimal(0) <= interval.lower <= interval.upper <= Decimal(1)
        assert interval.confidence_level == Decimal("0.80")


def test_temporal_comparison_uncertainty_rejects_oversized_blocks() -> None:
    built = build_research_calibration_temporal_comparison_uncertainty_evidence(
        uncertainty_id=ResearchCalibrationTemporalComparisonUncertaintyId(
            UUID(int=13001)
        ),
        comparison=_temporal_comparison(),
        policy=replace(_policy(), baseline_block_length=5),
    )

    assert isinstance(built, Failure)
    assert "baseline sample size" in str(built.error)


def test_temporal_comparison_uncertainty_recomputes_source_changes() -> None:
    comparison = _temporal_comparison()
    object.__setattr__(comparison, "absolute_ece_change", Decimal("0.10"))

    built = build_research_calibration_temporal_comparison_uncertainty_evidence(
        uncertainty_id=ResearchCalibrationTemporalComparisonUncertaintyId(
            UUID(int=14001)
        ),
        comparison=comparison,
        policy=_policy(),
    )

    assert isinstance(built, Failure)
    assert "source temporal changes" in str(built.error)


def test_temporal_comparison_uncertainty_rejects_tampering() -> None:
    built = build_research_calibration_temporal_comparison_uncertainty_evidence(
        uncertainty_id=ResearchCalibrationTemporalComparisonUncertaintyId(
            UUID(int=15001)
        ),
        comparison=_temporal_comparison(),
        policy=_policy(),
    )
    assert isinstance(built, Success)

    changed = (
        Decimal("0"),
        *built.value.resampled_absolute_ece_changes[1:],
    )
    if changed == built.value.resampled_absolute_ece_changes:
        changed = (
            Decimal("1"),
            *built.value.resampled_absolute_ece_changes[1:],
        )
    with pytest.raises(
        ResearchCalibrationTemporalComparisonUncertaintyValidationError
    ):
        replace(built.value, resampled_absolute_ece_changes=changed)

    with pytest.raises(
        ResearchCalibrationTemporalComparisonUncertaintyValidationError
    ):
        replace(
            built.value,
            fingerprint=replace(built.value.fingerprint, value="d" * 64),
        )


def test_temporal_comparison_uncertainty_policy_rejects_invalid_choices() -> None:
    with pytest.raises(
        ResearchCalibrationTemporalComparisonUncertaintyValidationError
    ):
        replace(_policy(), baseline_block_length=1)
    with pytest.raises(
        ResearchCalibrationTemporalComparisonUncertaintyValidationError
    ):
        replace(_policy(), comparison_block_length=1)
    with pytest.raises(
        ResearchCalibrationTemporalComparisonUncertaintyValidationError
    ):
        replace(_policy(), resample_count=1)
    with pytest.raises(
        ResearchCalibrationTemporalComparisonUncertaintyValidationError
    ):
        replace(_policy(), seed=-1)
    with pytest.raises(
        ResearchCalibrationTemporalComparisonUncertaintyValidationError
    ):
        replace(_policy(), confidence_level=Decimal("1"))
    with pytest.raises(
        ResearchCalibrationTemporalComparisonUncertaintyValidationError
    ):
        replace(_policy(), confidence_level=0.8)  # type: ignore[arg-type]

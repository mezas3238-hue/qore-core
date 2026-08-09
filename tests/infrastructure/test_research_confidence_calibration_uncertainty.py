from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID

import pytest

from qore.infrastructure.research_confidence_calibration import (
    ResearchCalibrationTarget,
    ResearchConfidenceOutcomeObservation,
)
from qore.infrastructure.research_confidence_calibration_mapping import (
    ResearchCalibrationMappingBlock,
    ResearchConfidenceCalibrationMappingFit,
)
from qore.infrastructure.research_confidence_calibration_oos_validation import (
    ResearchCalibrationOosValidationFingerprint,
    ResearchCalibrationOosValidationObservation,
    ResearchCalibrationOosValidationPolicy,
    ResearchCalibrationOosValidationSet,
    ResearchCalibrationOosValidationEvidence,
)
from qore.infrastructure.research_confidence_calibration_uncertainty import (
    ResearchCalibrationIntervalMethod,
    ResearchCalibrationUncertaintyId,
    ResearchCalibrationUncertaintyPolicy,
    ResearchCalibrationUncertaintyValidationError,
    build_research_calibration_uncertainty_evidence,
)
from qore.infrastructure.research_run import ResearchRunEvidence
from qore.kernel.result import Failure, Success
from qore.specialist.analysis import (
    SpecialistAnalysis,
    SpecialistAnalysisId,
    SpecialistAnalysisStatus,
    SpecialistConfidence,
    SpecialistKind,
)

_PROCESS_BASE = datetime(2026, 8, 9, 20, 0, tzinfo=UTC)
_SIM_BASE = datetime(2026, 1, 5, 14, 0, tzinfo=UTC)
_TARGET = ResearchCalibrationTarget("next-period-positive-return")
_KIND = SpecialistKind("virtual-trader.fx")


def _analysis(suffix: int, confidence: float) -> SpecialistAnalysis:
    analysis = object.__new__(SpecialistAnalysis)
    object.__setattr__(analysis, "analysis_id", SpecialistAnalysisId(UUID(int=suffix)))
    object.__setattr__(analysis, "timestamp", _PROCESS_BASE + timedelta(minutes=suffix))
    object.__setattr__(analysis, "kind", _KIND)
    object.__setattr__(analysis, "status", SpecialistAnalysisStatus.COMPLETED)
    object.__setattr__(analysis, "confidence", SpecialistConfidence(confidence))
    object.__setattr__(analysis, "metadata", None)
    object.__setattr__(analysis, "reasons", ())
    return analysis


def _source(
    suffix: int,
    confidence: float,
    occurred: bool,
) -> ResearchConfidenceOutcomeObservation:
    return ResearchConfidenceOutcomeObservation(
        analysis=_analysis(suffix, confidence),
        target=_TARGET,
        event_occurred=occurred,
    )


def _mapping_fit() -> ResearchConfidenceCalibrationMappingFit:
    fit = object.__new__(ResearchConfidenceCalibrationMappingFit)
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


def _run() -> ResearchRunEvidence:
    return object.__new__(ResearchRunEvidence)


def _observation(
    *,
    suffix: int,
    confidence: float,
    occurred: bool,
    minutes: int,
) -> ResearchCalibrationOosValidationObservation:
    return ResearchCalibrationOosValidationObservation(
        source=_source(suffix, confidence, occurred),
        run=_run(),
        score_observed_at=_SIM_BASE + timedelta(minutes=minutes),
        outcome_observed_at=_SIM_BASE + timedelta(minutes=minutes + 5),
        recorded_at=_PROCESS_BASE + timedelta(minutes=minutes),
    )


def _validation() -> ResearchCalibrationOosValidationEvidence:
    fit = _mapping_fit()
    validation_set = object.__new__(ResearchCalibrationOosValidationSet)
    object.__setattr__(validation_set, "mapping_fit", fit)
    object.__setattr__(
        validation_set,
        "observations",
        (
            _observation(suffix=11, confidence=0.2, occurred=True, minutes=10),
            _observation(suffix=12, confidence=0.4, occurred=True, minutes=30),
            _observation(suffix=13, confidence=0.8, occurred=False, minutes=50),
            _observation(suffix=14, confidence=0.95, occurred=False, minutes=70),
        ),
    )
    validation = object.__new__(ResearchCalibrationOosValidationEvidence)
    object.__setattr__(validation, "validation_set", validation_set)
    object.__setattr__(validation, "policy", ResearchCalibrationOosValidationPolicy(bin_count=4))
    object.__setattr__(validation, "sample_size", 4)
    object.__setattr__(validation, "brier_score", Decimal("0.625"))
    object.__setattr__(validation, "expected_calibration_error", Decimal("0.5"))
    object.__setattr__(
        validation,
        "fingerprint",
        ResearchCalibrationOosValidationFingerprint("a" * 64),
    )
    return validation


def _policy() -> ResearchCalibrationUncertaintyPolicy:
    return ResearchCalibrationUncertaintyPolicy(
        block_length=2,
        resample_count=32,
        seed=17,
        confidence_level=Decimal("0.80"),
        interval_method=ResearchCalibrationIntervalMethod.PERCENTILE_NEAREST_RANK,
    )


def test_uncertainty_evidence_is_deterministic_and_research_only() -> None:
    validation = _validation()
    first = build_research_calibration_uncertainty_evidence(
        uncertainty_id=ResearchCalibrationUncertaintyId(UUID(int=6001)),
        validation=validation,
        policy=_policy(),
    )
    second = build_research_calibration_uncertainty_evidence(
        uncertainty_id=ResearchCalibrationUncertaintyId(UUID(int=6002)),
        validation=validation,
        policy=_policy(),
    )

    assert isinstance(first, Success)
    assert isinstance(second, Success)
    evidence = first.value
    assert evidence.sample_size == 4
    assert evidence.source_brier_score == Decimal("0.625")
    assert evidence.source_ece == Decimal("0.5")
    assert len(evidence.resampled_brier_scores) == 32
    assert len(evidence.resampled_ece) == 32
    assert evidence.resampled_brier_scores == second.value.resampled_brier_scores
    assert evidence.resampled_ece == second.value.resampled_ece
    assert evidence.fingerprint == second.value.fingerprint
    assert Decimal(0) <= evidence.brier_interval.lower <= evidence.brier_interval.upper <= Decimal(1)
    assert Decimal(0) <= evidence.ece_interval.lower <= evidence.ece_interval.upper <= Decimal(1)
    assert evidence.brier_interval.confidence_level == Decimal("0.80")
    assert evidence.ece_interval.method is ResearchCalibrationIntervalMethod.PERCENTILE_NEAREST_RANK
    assert not hasattr(evidence, "calibrated_probability")
    assert not hasattr(evidence, "is_calibrated")
    assert not hasattr(evidence, "sample_adequate")
    assert not hasattr(evidence, "production_ready")
    assert not hasattr(evidence, "capital_authorized")


def test_uncertainty_rejects_block_length_larger_than_oos_sample() -> None:
    built = build_research_calibration_uncertainty_evidence(
        uncertainty_id=ResearchCalibrationUncertaintyId(UUID(int=6101)),
        validation=_validation(),
        policy=replace(_policy(), block_length=5),
    )

    assert isinstance(built, Failure)
    assert "sample size" in str(built.error)


def test_uncertainty_recomputes_source_metrics_instead_of_trusting_fields() -> None:
    validation = _validation()
    object.__setattr__(validation, "brier_score", Decimal("0.1"))
    built = build_research_calibration_uncertainty_evidence(
        uncertainty_id=ResearchCalibrationUncertaintyId(UUID(int=6201)),
        validation=validation,
        policy=_policy(),
    )

    assert isinstance(built, Failure)
    assert "Brier" in str(built.error)


def test_uncertainty_rejects_distribution_interval_and_fingerprint_tampering() -> None:
    built = build_research_calibration_uncertainty_evidence(
        uncertainty_id=ResearchCalibrationUncertaintyId(UUID(int=6301)),
        validation=_validation(),
        policy=_policy(),
    )
    assert isinstance(built, Success)

    changed_distribution = (
        Decimal("0"),
        *built.value.resampled_brier_scores[1:],
    )
    if changed_distribution == built.value.resampled_brier_scores:
        changed_distribution = (
            Decimal("1"),
            *built.value.resampled_brier_scores[1:],
        )
    with pytest.raises(ResearchCalibrationUncertaintyValidationError):
        replace(built.value, resampled_brier_scores=changed_distribution)

    changed_interval = replace(built.value.brier_interval, lower=Decimal("0"))
    if changed_interval == built.value.brier_interval:
        changed_interval = replace(built.value.brier_interval, upper=Decimal("1"))
    with pytest.raises(ResearchCalibrationUncertaintyValidationError):
        replace(built.value, brier_interval=changed_interval)

    with pytest.raises(ResearchCalibrationUncertaintyValidationError):
        replace(
            built.value,
            fingerprint=replace(built.value.fingerprint, value="b" * 64),
        )


def test_uncertainty_policy_rejects_invalid_model_choices() -> None:
    with pytest.raises(ResearchCalibrationUncertaintyValidationError):
        replace(_policy(), block_length=1)
    with pytest.raises(ResearchCalibrationUncertaintyValidationError):
        replace(_policy(), resample_count=1)
    with pytest.raises(ResearchCalibrationUncertaintyValidationError):
        replace(_policy(), seed=-1)
    with pytest.raises(ResearchCalibrationUncertaintyValidationError):
        replace(_policy(), confidence_level=Decimal("0"))
    with pytest.raises(ResearchCalibrationUncertaintyValidationError):
        replace(_policy(), confidence_level=Decimal("1"))
    with pytest.raises(ResearchCalibrationUncertaintyValidationError):
        replace(_policy(), confidence_level=0.8)  # type: ignore[arg-type]

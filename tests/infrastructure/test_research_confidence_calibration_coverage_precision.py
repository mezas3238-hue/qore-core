from __future__ import annotations

from dataclasses import replace
from decimal import Decimal
from uuid import UUID

import pytest

from qore.infrastructure.research_confidence_calibration import (
    ResearchConfidenceOutcomeObservation,
)
from qore.infrastructure.research_confidence_calibration_oos_validation import (
    ResearchCalibrationOosValidationEvidence,
    ResearchCalibrationOosValidationObservation,
    ResearchCalibrationOosValidationSet,
)
from qore.infrastructure.research_confidence_calibration_coverage_precision import (
    ResearchCalibrationCoveragePrecisionAssessmentId,
    ResearchCalibrationCoveragePrecisionFailure,
    ResearchCalibrationCoveragePrecisionPolicy,
    ResearchCalibrationCoveragePrecisionStatus,
    ResearchCalibrationCoveragePrecisionValidationError,
    assess_research_calibration_coverage_precision,
)
from qore.infrastructure.research_confidence_calibration_uncertainty import (
    ResearchCalibrationPercentileInterval,
    ResearchCalibrationIntervalMethod,
    ResearchCalibrationUncertaintyEvidence,
    ResearchCalibrationUncertaintyFingerprint,
)
from qore.kernel.result import Failure, Success


def _source(*, occurred: bool) -> ResearchConfidenceOutcomeObservation:
    source = object.__new__(ResearchConfidenceOutcomeObservation)
    object.__setattr__(source, "event_occurred", occurred)
    return source


def _observation(*, occurred: bool) -> ResearchCalibrationOosValidationObservation:
    observation = object.__new__(ResearchCalibrationOosValidationObservation)
    object.__setattr__(observation, "source", _source(occurred=occurred))
    return observation


def _validation(*, event_count: int, non_event_count: int) -> ResearchCalibrationOosValidationEvidence:
    validation_set = object.__new__(ResearchCalibrationOosValidationSet)
    object.__setattr__(
        validation_set,
        "observations",
        tuple(_observation(occurred=True) for _ in range(event_count))
        + tuple(_observation(occurred=False) for _ in range(non_event_count)),
    )
    validation = object.__new__(ResearchCalibrationOosValidationEvidence)
    object.__setattr__(validation, "validation_set", validation_set)
    return validation


def _interval(lower: str, upper: str) -> ResearchCalibrationPercentileInterval:
    return ResearchCalibrationPercentileInterval(
        confidence_level=Decimal("0.90"),
        method=ResearchCalibrationIntervalMethod.PERCENTILE_NEAREST_RANK,
        lower=Decimal(lower),
        upper=Decimal(upper),
    )


def _uncertainty(
    *,
    event_count: int = 4,
    non_event_count: int = 6,
    brier_lower: str = "0.10",
    brier_upper: str = "0.20",
    ece_lower: str = "0.02",
    ece_upper: str = "0.08",
) -> ResearchCalibrationUncertaintyEvidence:
    evidence = object.__new__(ResearchCalibrationUncertaintyEvidence)
    object.__setattr__(
        evidence,
        "validation",
        _validation(event_count=event_count, non_event_count=non_event_count),
    )
    object.__setattr__(evidence, "sample_size", event_count + non_event_count)
    object.__setattr__(evidence, "brier_interval", _interval(brier_lower, brier_upper))
    object.__setattr__(evidence, "ece_interval", _interval(ece_lower, ece_upper))
    object.__setattr__(
        evidence,
        "fingerprint",
        ResearchCalibrationUncertaintyFingerprint("a" * 64),
    )
    return evidence


def _policy() -> ResearchCalibrationCoveragePrecisionPolicy:
    return ResearchCalibrationCoveragePrecisionPolicy(
        minimum_sample_size=10,
        minimum_event_count=4,
        minimum_non_event_count=6,
        maximum_brier_interval_width=Decimal("0.10"),
        maximum_ece_interval_width=Decimal("0.06"),
    )


def test_assessment_meets_exact_declared_thresholds_without_authority() -> None:
    built = assess_research_calibration_coverage_precision(
        assessment_id=ResearchCalibrationCoveragePrecisionAssessmentId(UUID(int=7001)),
        uncertainty=_uncertainty(),
        policy=_policy(),
    )

    assert isinstance(built, Success)
    assessment = built.value
    assert assessment.sample_size == 10
    assert assessment.event_count == 4
    assert assessment.non_event_count == 6
    assert assessment.brier_interval_width == Decimal("0.10")
    assert assessment.ece_interval_width == Decimal("0.06")
    assert assessment.failures == ()
    assert assessment.status is ResearchCalibrationCoveragePrecisionStatus.MEETS_DECLARED_POLICY
    assert assessment.meets_declared_policy is True
    assert not hasattr(assessment, "statistically_sufficient")
    assert not hasattr(assessment, "calibrated_probability")
    assert not hasattr(assessment, "is_calibrated")
    assert not hasattr(assessment, "strategy_approved")
    assert not hasattr(assessment, "production_ready")
    assert not hasattr(assessment, "capital_authorized")


def test_assessment_reports_all_failures_in_canonical_order() -> None:
    built = assess_research_calibration_coverage_precision(
        assessment_id=ResearchCalibrationCoveragePrecisionAssessmentId(UUID(int=7101)),
        uncertainty=_uncertainty(
            event_count=1,
            non_event_count=2,
            brier_lower="0.10",
            brier_upper="0.50",
            ece_lower="0.05",
            ece_upper="0.40",
        ),
        policy=_policy(),
    )

    assert isinstance(built, Success)
    assert built.value.failures == (
        ResearchCalibrationCoveragePrecisionFailure.SAMPLE_SIZE,
        ResearchCalibrationCoveragePrecisionFailure.EVENT_COUNT,
        ResearchCalibrationCoveragePrecisionFailure.NON_EVENT_COUNT,
        ResearchCalibrationCoveragePrecisionFailure.BRIER_INTERVAL_WIDTH,
        ResearchCalibrationCoveragePrecisionFailure.ECE_INTERVAL_WIDTH,
    )
    assert (
        built.value.status
        is ResearchCalibrationCoveragePrecisionStatus.DOES_NOT_MEET_DECLARED_POLICY
    )
    assert built.value.meets_declared_policy is False


def test_assessment_fingerprint_excludes_administrative_id() -> None:
    uncertainty = _uncertainty()
    first = assess_research_calibration_coverage_precision(
        assessment_id=ResearchCalibrationCoveragePrecisionAssessmentId(UUID(int=7201)),
        uncertainty=uncertainty,
        policy=_policy(),
    )
    second = assess_research_calibration_coverage_precision(
        assessment_id=ResearchCalibrationCoveragePrecisionAssessmentId(UUID(int=7202)),
        uncertainty=uncertainty,
        policy=_policy(),
    )

    assert isinstance(first, Success)
    assert isinstance(second, Success)
    assert first.value.fingerprint == second.value.fingerprint


def test_assessment_recomputes_upstream_sample_size() -> None:
    uncertainty = _uncertainty()
    object.__setattr__(uncertainty, "sample_size", 999)

    built = assess_research_calibration_coverage_precision(
        assessment_id=ResearchCalibrationCoveragePrecisionAssessmentId(UUID(int=7301)),
        uncertainty=uncertainty,
        policy=_policy(),
    )

    assert isinstance(built, Failure)
    assert "sample_size" in str(built.error)


def test_assessment_rejects_metric_status_and_fingerprint_tampering() -> None:
    built = assess_research_calibration_coverage_precision(
        assessment_id=ResearchCalibrationCoveragePrecisionAssessmentId(UUID(int=7401)),
        uncertainty=_uncertainty(),
        policy=_policy(),
    )
    assert isinstance(built, Success)

    with pytest.raises(ResearchCalibrationCoveragePrecisionValidationError):
        replace(built.value, event_count=3)
    with pytest.raises(ResearchCalibrationCoveragePrecisionValidationError):
        replace(
            built.value,
            status=(
                ResearchCalibrationCoveragePrecisionStatus.DOES_NOT_MEET_DECLARED_POLICY
            ),
        )
    with pytest.raises(ResearchCalibrationCoveragePrecisionValidationError):
        replace(
            built.value,
            fingerprint=replace(built.value.fingerprint, value="b" * 64),
        )


def test_policy_rejects_invalid_thresholds_without_inventing_defaults() -> None:
    with pytest.raises(ResearchCalibrationCoveragePrecisionValidationError):
        replace(_policy(), minimum_sample_size=1)
    with pytest.raises(ResearchCalibrationCoveragePrecisionValidationError):
        replace(_policy(), minimum_event_count=-1)
    with pytest.raises(ResearchCalibrationCoveragePrecisionValidationError):
        replace(_policy(), minimum_non_event_count=-1)
    with pytest.raises(ResearchCalibrationCoveragePrecisionValidationError):
        replace(_policy(), maximum_brier_interval_width=Decimal("1.01"))
    with pytest.raises(ResearchCalibrationCoveragePrecisionValidationError):
        replace(_policy(), maximum_ece_interval_width=Decimal("NaN"))
    with pytest.raises(ResearchCalibrationCoveragePrecisionValidationError):
        replace(_policy(), maximum_ece_interval_width=0.1)  # type: ignore[arg-type]

from __future__ import annotations

from dataclasses import replace
from decimal import Decimal
from uuid import UUID

import pytest

from qore.infrastructure.research_confidence_calibration_coverage_precision import (
    ResearchCalibrationCoveragePrecisionAssessment,
    ResearchCalibrationCoveragePrecisionFingerprint,
    ResearchCalibrationCoveragePrecisionStatus,
)
from qore.infrastructure.research_confidence_calibration_diagnostic_quality import (
    ResearchCalibrationDiagnosticQualityAssessmentId,
    ResearchCalibrationDiagnosticQualityFailure,
    ResearchCalibrationDiagnosticQualityPolicy,
    ResearchCalibrationDiagnosticQualityStatus,
    ResearchCalibrationDiagnosticQualityValidationError,
    assess_research_calibration_diagnostic_quality,
)
from qore.infrastructure.research_confidence_calibration_oos_validation import (
    ResearchCalibrationOosValidationEvidence,
)
from qore.infrastructure.research_confidence_calibration_uncertainty import (
    ResearchCalibrationIntervalMethod,
    ResearchCalibrationPercentileInterval,
    ResearchCalibrationUncertaintyEvidence,
)
from qore.kernel.result import Failure, Success


def _validation(
    *,
    mean_estimated_probability: str = "0.52",
    empirical_event_rate: str = "0.50",
    ece: str = "0.04",
) -> ResearchCalibrationOosValidationEvidence:
    validation = object.__new__(ResearchCalibrationOosValidationEvidence)
    object.__setattr__(
        validation,
        "mean_estimated_probability",
        Decimal(mean_estimated_probability),
    )
    object.__setattr__(validation, "empirical_event_rate", Decimal(empirical_event_rate))
    object.__setattr__(validation, "expected_calibration_error", Decimal(ece))
    return validation


def _uncertainty(
    *,
    validation: ResearchCalibrationOosValidationEvidence | None = None,
    ece_lower: str = "0.02",
    ece_upper: str = "0.07",
) -> ResearchCalibrationUncertaintyEvidence:
    uncertainty = object.__new__(ResearchCalibrationUncertaintyEvidence)
    object.__setattr__(uncertainty, "validation", validation or _validation())
    object.__setattr__(
        uncertainty,
        "ece_interval",
        ResearchCalibrationPercentileInterval(
            confidence_level=Decimal("0.90"),
            method=ResearchCalibrationIntervalMethod.PERCENTILE_NEAREST_RANK,
            lower=Decimal(ece_lower),
            upper=Decimal(ece_upper),
        ),
    )
    return uncertainty


def _coverage(
    *,
    uncertainty: ResearchCalibrationUncertaintyEvidence | None = None,
    meets: bool = True,
) -> ResearchCalibrationCoveragePrecisionAssessment:
    coverage = object.__new__(ResearchCalibrationCoveragePrecisionAssessment)
    object.__setattr__(coverage, "uncertainty", uncertainty or _uncertainty())
    object.__setattr__(
        coverage,
        "status",
        (
            ResearchCalibrationCoveragePrecisionStatus.MEETS_DECLARED_POLICY
            if meets
            else ResearchCalibrationCoveragePrecisionStatus.DOES_NOT_MEET_DECLARED_POLICY
        ),
    )
    object.__setattr__(
        coverage,
        "fingerprint",
        ResearchCalibrationCoveragePrecisionFingerprint("a" * 64),
    )
    return coverage


def _policy() -> ResearchCalibrationDiagnosticQualityPolicy:
    return ResearchCalibrationDiagnosticQualityPolicy(
        maximum_absolute_mean_gap=Decimal("0.02"),
        maximum_ece=Decimal("0.04"),
        maximum_ece_interval_upper_bound=Decimal("0.07"),
    )


def test_quality_assessment_meets_exact_thresholds_without_calibration_authority() -> None:
    built = assess_research_calibration_diagnostic_quality(
        assessment_id=ResearchCalibrationDiagnosticQualityAssessmentId(UUID(int=8001)),
        coverage_precision=_coverage(),
        policy=_policy(),
    )

    assert isinstance(built, Success)
    assessment = built.value
    assert assessment.absolute_mean_gap == Decimal("0.02")
    assert assessment.ece == Decimal("0.04")
    assert assessment.ece_interval_upper_bound == Decimal("0.07")
    assert assessment.failures == ()
    assert assessment.status is ResearchCalibrationDiagnosticQualityStatus.MEETS_DECLARED_POLICY
    assert assessment.meets_declared_policy is True
    assert not hasattr(assessment, "calibrated_probability")
    assert not hasattr(assessment, "is_calibrated")
    assert not hasattr(assessment, "externally_validated")
    assert not hasattr(assessment, "strategy_approved")
    assert not hasattr(assessment, "production_ready")
    assert not hasattr(assessment, "capital_authorized")


def test_quality_assessment_reports_all_failures_in_canonical_order() -> None:
    validation = _validation(
        mean_estimated_probability="0.70",
        empirical_event_rate="0.50",
        ece="0.15",
    )
    built = assess_research_calibration_diagnostic_quality(
        assessment_id=ResearchCalibrationDiagnosticQualityAssessmentId(UUID(int=8101)),
        coverage_precision=_coverage(
            uncertainty=_uncertainty(
                validation=validation,
                ece_lower="0.10",
                ece_upper="0.25",
            )
        ),
        policy=ResearchCalibrationDiagnosticQualityPolicy(
            maximum_absolute_mean_gap=Decimal("0.10"),
            maximum_ece=Decimal("0.10"),
            maximum_ece_interval_upper_bound=Decimal("0.20"),
        ),
    )

    assert isinstance(built, Success)
    assert built.value.failures == (
        ResearchCalibrationDiagnosticQualityFailure.ABSOLUTE_MEAN_GAP,
        ResearchCalibrationDiagnosticQualityFailure.ECE,
        ResearchCalibrationDiagnosticQualityFailure.ECE_INTERVAL_UPPER_BOUND,
    )
    assert (
        built.value.status
        is ResearchCalibrationDiagnosticQualityStatus.DOES_NOT_MEET_DECLARED_POLICY
    )
    assert built.value.meets_declared_policy is False


def test_quality_assessment_requires_coverage_precision_policy_to_pass_first() -> None:
    built = assess_research_calibration_diagnostic_quality(
        assessment_id=ResearchCalibrationDiagnosticQualityAssessmentId(UUID(int=8201)),
        coverage_precision=_coverage(meets=False),
        policy=_policy(),
    )

    assert isinstance(built, Failure)
    assert "coverage/precision" in str(built.error)


def test_quality_fingerprint_excludes_administrative_id() -> None:
    coverage = _coverage()
    first = assess_research_calibration_diagnostic_quality(
        assessment_id=ResearchCalibrationDiagnosticQualityAssessmentId(UUID(int=8301)),
        coverage_precision=coverage,
        policy=_policy(),
    )
    second = assess_research_calibration_diagnostic_quality(
        assessment_id=ResearchCalibrationDiagnosticQualityAssessmentId(UUID(int=8302)),
        coverage_precision=coverage,
        policy=_policy(),
    )

    assert isinstance(first, Success)
    assert isinstance(second, Success)
    assert first.value.fingerprint == second.value.fingerprint


def test_quality_assessment_rejects_metric_status_and_fingerprint_tampering() -> None:
    built = assess_research_calibration_diagnostic_quality(
        assessment_id=ResearchCalibrationDiagnosticQualityAssessmentId(UUID(int=8401)),
        coverage_precision=_coverage(),
        policy=_policy(),
    )
    assert isinstance(built, Success)

    with pytest.raises(ResearchCalibrationDiagnosticQualityValidationError):
        replace(built.value, ece=Decimal("0.01"))
    with pytest.raises(ResearchCalibrationDiagnosticQualityValidationError):
        replace(
            built.value,
            status=(
                ResearchCalibrationDiagnosticQualityStatus.DOES_NOT_MEET_DECLARED_POLICY
            ),
        )
    with pytest.raises(ResearchCalibrationDiagnosticQualityValidationError):
        replace(
            built.value,
            fingerprint=replace(built.value.fingerprint, value="b" * 64),
        )


def test_quality_policy_rejects_invalid_or_incoherent_thresholds() -> None:
    with pytest.raises(ResearchCalibrationDiagnosticQualityValidationError):
        replace(_policy(), maximum_absolute_mean_gap=Decimal("1.01"))
    with pytest.raises(ResearchCalibrationDiagnosticQualityValidationError):
        replace(_policy(), maximum_ece=Decimal("NaN"))
    with pytest.raises(ResearchCalibrationDiagnosticQualityValidationError):
        replace(_policy(), maximum_ece=0.1)  # type: ignore[arg-type]
    with pytest.raises(ResearchCalibrationDiagnosticQualityValidationError):
        ResearchCalibrationDiagnosticQualityPolicy(
            maximum_absolute_mean_gap=Decimal("0.10"),
            maximum_ece=Decimal("0.20"),
            maximum_ece_interval_upper_bound=Decimal("0.10"),
        )

from __future__ import annotations

from dataclasses import replace
from decimal import Decimal
from uuid import UUID

import pytest

from qore.infrastructure.research_confidence_calibration_temporal_change_policy import (
    ResearchCalibrationTemporalChangeAssessment,
    ResearchCalibrationTemporalChangeAssessmentId,
    ResearchCalibrationTemporalChangeFailure,
    ResearchCalibrationTemporalChangePolicy,
    ResearchCalibrationTemporalChangePolicyError,
    ResearchCalibrationTemporalChangePolicyValidationError,
    ResearchCalibrationTemporalChangeStatus,
    assess_research_calibration_temporal_change,
)
from qore.infrastructure.research_confidence_calibration_temporal_comparison_uncertainty import (
    ResearchCalibrationTemporalComparisonInterval,
    ResearchCalibrationTemporalComparisonUncertaintyEvidence,
    ResearchCalibrationTemporalComparisonUncertaintyFingerprint,
)
from qore.infrastructure.research_confidence_calibration_uncertainty import (
    ResearchCalibrationIntervalMethod,
)
from qore.kernel.result import Result, Success


def _interval(*, lower: str, upper: str) -> ResearchCalibrationTemporalComparisonInterval:
    return ResearchCalibrationTemporalComparisonInterval(
        confidence_level=Decimal("0.80"),
        method=ResearchCalibrationIntervalMethod.PERCENTILE_NEAREST_RANK,
        lower=Decimal(lower),
        upper=Decimal(upper),
    )


def _uncertainty() -> ResearchCalibrationTemporalComparisonUncertaintyEvidence:
    evidence = object.__new__(ResearchCalibrationTemporalComparisonUncertaintyEvidence)
    object.__setattr__(
        evidence,
        "source_absolute_mean_gap_change",
        Decimal("0.10"),
    )
    object.__setattr__(
        evidence,
        "source_absolute_ece_change",
        Decimal("0.20"),
    )
    object.__setattr__(
        evidence,
        "source_absolute_mean_probability_shift",
        Decimal("0.30"),
    )
    object.__setattr__(
        evidence,
        "source_absolute_event_rate_shift",
        Decimal("0.40"),
    )
    object.__setattr__(
        evidence,
        "absolute_mean_gap_change_interval",
        _interval(lower="0.05", upper="0.50"),
    )
    object.__setattr__(
        evidence,
        "absolute_ece_change_interval",
        _interval(lower="0.10", upper="0.60"),
    )
    object.__setattr__(
        evidence,
        "absolute_mean_probability_shift_interval",
        _interval(lower="0.15", upper="0.70"),
    )
    object.__setattr__(
        evidence,
        "absolute_event_rate_shift_interval",
        _interval(lower="0.20", upper="0.80"),
    )
    object.__setattr__(
        evidence,
        "fingerprint",
        ResearchCalibrationTemporalComparisonUncertaintyFingerprint("a" * 64),
    )
    return evidence


def _exact_policy() -> ResearchCalibrationTemporalChangePolicy:
    return ResearchCalibrationTemporalChangePolicy(
        maximum_absolute_mean_gap_change=Decimal("0.10"),
        maximum_absolute_ece_change=Decimal("0.20"),
        maximum_absolute_mean_probability_shift=Decimal("0.30"),
        maximum_absolute_event_rate_shift=Decimal("0.40"),
        maximum_mean_gap_change_interval_upper_bound=Decimal("0.50"),
        maximum_ece_change_interval_upper_bound=Decimal("0.60"),
        maximum_mean_probability_shift_interval_upper_bound=Decimal("0.70"),
        maximum_event_rate_shift_interval_upper_bound=Decimal("0.80"),
    )


def _assess(
    *,
    suffix: int = 1,
) -> Result[
    ResearchCalibrationTemporalChangeAssessment,
    ResearchCalibrationTemporalChangePolicyError,
]:
    return assess_research_calibration_temporal_change(
        assessment_id=ResearchCalibrationTemporalChangeAssessmentId(UUID(int=suffix)),
        uncertainty=_uncertainty(),
        policy=_exact_policy(),
    )


def test_temporal_change_policy_accepts_exact_threshold_equality() -> None:
    built = _assess()

    assert isinstance(built, Success)
    assessment = built.value
    assert assessment.status is ResearchCalibrationTemporalChangeStatus.MEETS_DECLARED_POLICY
    assert assessment.meets_declared_policy
    assert assessment.failures == ()
    assert assessment.absolute_mean_gap_change == Decimal("0.10")
    assert assessment.absolute_ece_change == Decimal("0.20")
    assert assessment.absolute_mean_probability_shift == Decimal("0.30")
    assert assessment.absolute_event_rate_shift == Decimal("0.40")
    assert assessment.mean_gap_change_interval_upper == Decimal("0.50")
    assert assessment.ece_change_interval_upper == Decimal("0.60")
    assert assessment.mean_probability_shift_interval_upper == Decimal("0.70")
    assert assessment.event_rate_shift_interval_upper == Decimal("0.80")


def test_temporal_change_policy_reports_all_failures_in_canonical_order() -> None:
    zero = Decimal(0)
    policy = ResearchCalibrationTemporalChangePolicy(
        maximum_absolute_mean_gap_change=zero,
        maximum_absolute_ece_change=zero,
        maximum_absolute_mean_probability_shift=zero,
        maximum_absolute_event_rate_shift=zero,
        maximum_mean_gap_change_interval_upper_bound=zero,
        maximum_ece_change_interval_upper_bound=zero,
        maximum_mean_probability_shift_interval_upper_bound=zero,
        maximum_event_rate_shift_interval_upper_bound=zero,
    )
    built = assess_research_calibration_temporal_change(
        assessment_id=ResearchCalibrationTemporalChangeAssessmentId(UUID(int=2)),
        uncertainty=_uncertainty(),
        policy=policy,
    )

    assert isinstance(built, Success)
    assessment = built.value
    assert (
        assessment.status
        is ResearchCalibrationTemporalChangeStatus.DOES_NOT_MEET_DECLARED_POLICY
    )
    assert not assessment.meets_declared_policy
    assert assessment.failures == (
        ResearchCalibrationTemporalChangeFailure.ABSOLUTE_MEAN_GAP_CHANGE,
        ResearchCalibrationTemporalChangeFailure.ABSOLUTE_ECE_CHANGE,
        ResearchCalibrationTemporalChangeFailure.ABSOLUTE_MEAN_PROBABILITY_SHIFT,
        ResearchCalibrationTemporalChangeFailure.ABSOLUTE_EVENT_RATE_SHIFT,
        ResearchCalibrationTemporalChangeFailure.MEAN_GAP_CHANGE_INTERVAL_UPPER_BOUND,
        ResearchCalibrationTemporalChangeFailure.ECE_CHANGE_INTERVAL_UPPER_BOUND,
        ResearchCalibrationTemporalChangeFailure.MEAN_PROBABILITY_SHIFT_INTERVAL_UPPER_BOUND,
        ResearchCalibrationTemporalChangeFailure.EVENT_RATE_SHIFT_INTERVAL_UPPER_BOUND,
    )


def test_temporal_change_fingerprint_excludes_administrative_assessment_id() -> None:
    first = _assess(suffix=10)
    second = _assess(suffix=11)

    assert isinstance(first, Success)
    assert isinstance(second, Success)
    assert first.value.assessment_id != second.value.assessment_id
    assert first.value.fingerprint == second.value.fingerprint


def test_temporal_change_assessment_rejects_metric_and_fingerprint_tampering() -> None:
    built = _assess()
    assert isinstance(built, Success)

    with pytest.raises(ResearchCalibrationTemporalChangePolicyValidationError):
        replace(
            built.value,
            absolute_ece_change=Decimal("0.19"),
        )

    with pytest.raises(ResearchCalibrationTemporalChangePolicyValidationError):
        replace(
            built.value,
            fingerprint=replace(built.value.fingerprint, value="b" * 64),
        )


def test_temporal_change_policy_rejects_invalid_thresholds() -> None:
    with pytest.raises(ResearchCalibrationTemporalChangePolicyValidationError):
        replace(
            _exact_policy(),
            maximum_absolute_mean_gap_change=Decimal("NaN"),
        )
    with pytest.raises(ResearchCalibrationTemporalChangePolicyValidationError):
        replace(
            _exact_policy(),
            maximum_absolute_ece_change=Decimal("1.01"),
        )
    with pytest.raises(ResearchCalibrationTemporalChangePolicyValidationError):
        replace(
            _exact_policy(),
            maximum_absolute_event_rate_shift=0.40,  # type: ignore[arg-type]
        )


def test_temporal_change_assessment_has_no_drift_or_operational_authority() -> None:
    built = _assess()
    assert isinstance(built, Success)
    assessment = built.value

    assert not hasattr(assessment, "drift_detected")
    assert not hasattr(assessment, "p_value")
    assert not hasattr(assessment, "statistically_significant")
    assert not hasattr(assessment, "calibrated_probability")
    assert not hasattr(assessment, "production_ready")
    assert not hasattr(assessment, "capital_authorized")
    assert not hasattr(assessment, "execution_authorized")

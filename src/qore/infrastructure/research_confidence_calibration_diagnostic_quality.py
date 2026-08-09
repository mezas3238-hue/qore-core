from __future__ import annotations

import json
from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum
from hashlib import sha256
from re import fullmatch
from uuid import UUID

from qore.infrastructure.research_confidence_calibration_coverage_precision import (
    ResearchCalibrationCoveragePrecisionAssessment,
)
from qore.kernel.errors import InfrastructureError
from qore.kernel.result import Failure, Result, Success

_ZERO = Decimal(0)
_ONE = Decimal(1)


class ResearchCalibrationDiagnosticQualityError(InfrastructureError):
    """Base error for research-only calibration diagnostic quality assessment."""

    __slots__ = ()


class ResearchCalibrationDiagnosticQualityValidationError(
    ResearchCalibrationDiagnosticQualityError
):
    """Violation of a calibration diagnostic quality assessment invariant."""

    __slots__ = ()


def _validate_unit_decimal(value: Decimal, *, field_name: str) -> None:
    if not isinstance(value, Decimal) or not value.is_finite():
        raise ResearchCalibrationDiagnosticQualityValidationError(
            f"{field_name} must be a finite Decimal"
        )
    if not _ZERO <= value <= _ONE:
        raise ResearchCalibrationDiagnosticQualityValidationError(
            f"{field_name} must remain inside [0, 1]"
        )


@dataclass(frozen=True, slots=True)
class ResearchCalibrationDiagnosticQualityAssessmentId:
    value: UUID

    def __post_init__(self) -> None:
        if not isinstance(self.value, UUID):
            raise ResearchCalibrationDiagnosticQualityValidationError(
                "diagnostic quality assessment id must be UUID"
            )

    def logical_values(self) -> tuple[str, ...]:
        return (str(self.value),)


@dataclass(frozen=True, slots=True)
class ResearchCalibrationDiagnosticQualityPolicy:
    """Explicit research thresholds for selected OOS calibration diagnostics.

    The thresholds are analyst-supplied and have no universal defaults. ECE remains
    an empirical, binning-dependent diagnostic; the ECE interval upper bound inherits
    the explicit block-bootstrap assumptions of upstream uncertainty evidence.

    Meeting this policy does not prove mathematical calibration, nominal interval
    coverage, external validity, future stability, or probability correctness.
    """

    maximum_absolute_mean_gap: Decimal
    maximum_ece: Decimal
    maximum_ece_interval_upper_bound: Decimal

    def __post_init__(self) -> None:
        _validate_unit_decimal(
            self.maximum_absolute_mean_gap,
            field_name="maximum_absolute_mean_gap",
        )
        _validate_unit_decimal(self.maximum_ece, field_name="maximum_ece")
        _validate_unit_decimal(
            self.maximum_ece_interval_upper_bound,
            field_name="maximum_ece_interval_upper_bound",
        )
        if self.maximum_ece_interval_upper_bound < self.maximum_ece:
            raise ResearchCalibrationDiagnosticQualityValidationError(
                "maximum_ece_interval_upper_bound cannot be stricter than maximum_ece"
            )

    def logical_values(self) -> tuple[str, str, str]:
        return (
            format(self.maximum_absolute_mean_gap, "f"),
            format(self.maximum_ece, "f"),
            format(self.maximum_ece_interval_upper_bound, "f"),
        )


class ResearchCalibrationDiagnosticQualityFailure(StrEnum):
    """Canonical reasons exact diagnostics do not meet the declared policy."""

    ABSOLUTE_MEAN_GAP = "absolute-mean-gap"
    ECE = "ece"
    ECE_INTERVAL_UPPER_BOUND = "ece-interval-upper-bound"


class ResearchCalibrationDiagnosticQualityStatus(StrEnum):
    """Policy-local diagnostic status; never an operational approval state."""

    MEETS_DECLARED_POLICY = "meets-declared-policy"
    DOES_NOT_MEET_DECLARED_POLICY = "does-not-meet-declared-policy"


type _DerivedAssessment = tuple[
    Decimal,
    Decimal,
    Decimal,
    tuple[ResearchCalibrationDiagnosticQualityFailure, ...],
    ResearchCalibrationDiagnosticQualityStatus,
]


def _derive_assessment(
    coverage_precision: ResearchCalibrationCoveragePrecisionAssessment,
    policy: ResearchCalibrationDiagnosticQualityPolicy,
) -> _DerivedAssessment:
    if not isinstance(
        coverage_precision,
        ResearchCalibrationCoveragePrecisionAssessment,
    ):
        raise ResearchCalibrationDiagnosticQualityValidationError(
            "diagnostic quality requires ResearchCalibrationCoveragePrecisionAssessment"
        )
    if not coverage_precision.meets_declared_policy:
        raise ResearchCalibrationDiagnosticQualityValidationError(
            "coverage/precision must meet its declared policy before quality assessment"
        )
    if not isinstance(policy, ResearchCalibrationDiagnosticQualityPolicy):
        raise ResearchCalibrationDiagnosticQualityValidationError(
            "diagnostic quality requires explicit ResearchCalibrationDiagnosticQualityPolicy"
        )

    uncertainty = coverage_precision.uncertainty
    validation = uncertainty.validation
    absolute_mean_gap = abs(
        validation.mean_estimated_probability - validation.empirical_event_rate
    )
    ece = validation.expected_calibration_error
    ece_upper = uncertainty.ece_interval.upper
    _validate_unit_decimal(absolute_mean_gap, field_name="derived absolute mean gap")
    _validate_unit_decimal(ece, field_name="derived ECE")
    _validate_unit_decimal(ece_upper, field_name="derived ECE interval upper bound")

    failures: list[ResearchCalibrationDiagnosticQualityFailure] = []
    if absolute_mean_gap > policy.maximum_absolute_mean_gap:
        failures.append(ResearchCalibrationDiagnosticQualityFailure.ABSOLUTE_MEAN_GAP)
    if ece > policy.maximum_ece:
        failures.append(ResearchCalibrationDiagnosticQualityFailure.ECE)
    if ece_upper > policy.maximum_ece_interval_upper_bound:
        failures.append(
            ResearchCalibrationDiagnosticQualityFailure.ECE_INTERVAL_UPPER_BOUND
        )

    failure_tuple = tuple(failures)
    status = (
        ResearchCalibrationDiagnosticQualityStatus.MEETS_DECLARED_POLICY
        if not failure_tuple
        else ResearchCalibrationDiagnosticQualityStatus.DOES_NOT_MEET_DECLARED_POLICY
    )
    return absolute_mean_gap, ece, ece_upper, failure_tuple, status


@dataclass(frozen=True, slots=True)
class ResearchCalibrationDiagnosticQualityFingerprint:
    value: str

    def __post_init__(self) -> None:
        if not isinstance(self.value, str) or fullmatch(r"[0-9a-f]{64}", self.value) is None:
            raise ResearchCalibrationDiagnosticQualityValidationError(
                "diagnostic quality fingerprint must be 64 lowercase hex characters"
            )

    def logical_values(self) -> tuple[str, ...]:
        return (self.value,)


def compute_research_calibration_diagnostic_quality_fingerprint(
    *,
    coverage_precision: ResearchCalibrationCoveragePrecisionAssessment,
    policy: ResearchCalibrationDiagnosticQualityPolicy,
    derived: _DerivedAssessment,
) -> ResearchCalibrationDiagnosticQualityFingerprint:
    """Hash exact upstream coverage evidence, policy, diagnostics and status."""

    expected = _derive_assessment(coverage_precision, policy)
    if derived != expected:
        raise ResearchCalibrationDiagnosticQualityValidationError(
            "diagnostic quality fingerprint inputs must match deterministic assessment"
        )
    canonical = {
        "coverage_precision_fingerprint": coverage_precision.fingerprint.logical_values(),
        "policy": policy.logical_values(),
        "absolute_mean_gap": format(derived[0], "f"),
        "ece": format(derived[1], "f"),
        "ece_interval_upper_bound": format(derived[2], "f"),
        "failures": tuple(item.value for item in derived[3]),
        "status": derived[4].value,
    }
    encoded = json.dumps(
        canonical,
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    return ResearchCalibrationDiagnosticQualityFingerprint(sha256(encoded).hexdigest())


@dataclass(frozen=True, slots=True)
class ResearchCalibrationDiagnosticQualityAssessment:
    """Research-only assessment of selected OOS calibration diagnostics.

    This evidence compares the absolute difference between mean estimated
    probability and empirical event rate, empirical binned ECE, and the upstream
    ECE bootstrap interval upper bound with an explicit policy. It requires the
    preceding coverage/precision assessment to meet its declared policy.

    `MEETS_DECLARED_POLICY` does not certify mathematical calibration, create a
    `CalibratedProbability`, prove external or future validity, authorize strategy
    or risk changes, authorize production/capital, or create execution authority.
    """

    assessment_id: ResearchCalibrationDiagnosticQualityAssessmentId
    coverage_precision: ResearchCalibrationCoveragePrecisionAssessment
    policy: ResearchCalibrationDiagnosticQualityPolicy
    absolute_mean_gap: Decimal
    ece: Decimal
    ece_interval_upper_bound: Decimal
    failures: tuple[ResearchCalibrationDiagnosticQualityFailure, ...]
    status: ResearchCalibrationDiagnosticQualityStatus
    fingerprint: ResearchCalibrationDiagnosticQualityFingerprint

    def __post_init__(self) -> None:
        if not isinstance(
            self.assessment_id,
            ResearchCalibrationDiagnosticQualityAssessmentId,
        ):
            raise ResearchCalibrationDiagnosticQualityValidationError(
                "assessment_id must be ResearchCalibrationDiagnosticQualityAssessmentId"
            )
        if not isinstance(
            self.coverage_precision,
            ResearchCalibrationCoveragePrecisionAssessment,
        ):
            raise ResearchCalibrationDiagnosticQualityValidationError(
                "coverage_precision must be ResearchCalibrationCoveragePrecisionAssessment"
            )
        if not isinstance(self.policy, ResearchCalibrationDiagnosticQualityPolicy):
            raise ResearchCalibrationDiagnosticQualityValidationError(
                "policy must be ResearchCalibrationDiagnosticQualityPolicy"
            )
        expected = _derive_assessment(self.coverage_precision, self.policy)
        actual: _DerivedAssessment = (
            self.absolute_mean_gap,
            self.ece,
            self.ece_interval_upper_bound,
            self.failures,
            self.status,
        )
        if actual != expected:
            raise ResearchCalibrationDiagnosticQualityValidationError(
                "diagnostic quality assessment must match exact upstream evidence and policy"
            )
        if not isinstance(
            self.fingerprint,
            ResearchCalibrationDiagnosticQualityFingerprint,
        ):
            raise ResearchCalibrationDiagnosticQualityValidationError(
                "fingerprint must be ResearchCalibrationDiagnosticQualityFingerprint"
            )
        expected_fingerprint = compute_research_calibration_diagnostic_quality_fingerprint(
            coverage_precision=self.coverage_precision,
            policy=self.policy,
            derived=expected,
        )
        if self.fingerprint != expected_fingerprint:
            raise ResearchCalibrationDiagnosticQualityValidationError(
                "diagnostic quality fingerprint must match exact assessment evidence"
            )

    @property
    def meets_declared_policy(self) -> bool:
        return self.status is ResearchCalibrationDiagnosticQualityStatus.MEETS_DECLARED_POLICY

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.assessment_id.logical_values(),
            self.coverage_precision.fingerprint.logical_values(),
            self.policy.logical_values(),
            format(self.absolute_mean_gap, "f"),
            format(self.ece, "f"),
            format(self.ece_interval_upper_bound, "f"),
            tuple(item.value for item in self.failures),
            self.status.value,
            self.fingerprint.logical_values(),
        )


def assess_research_calibration_diagnostic_quality(
    *,
    assessment_id: ResearchCalibrationDiagnosticQualityAssessmentId,
    coverage_precision: ResearchCalibrationCoveragePrecisionAssessment,
    policy: ResearchCalibrationDiagnosticQualityPolicy,
) -> Result[
    ResearchCalibrationDiagnosticQualityAssessment,
    ResearchCalibrationDiagnosticQualityError,
]:
    """Assess selected diagnostics without certifying calibrated probability."""

    try:
        derived = _derive_assessment(coverage_precision, policy)
        fingerprint = compute_research_calibration_diagnostic_quality_fingerprint(
            coverage_precision=coverage_precision,
            policy=policy,
            derived=derived,
        )
        return Success(
            ResearchCalibrationDiagnosticQualityAssessment(
                assessment_id=assessment_id,
                coverage_precision=coverage_precision,
                policy=policy,
                absolute_mean_gap=derived[0],
                ece=derived[1],
                ece_interval_upper_bound=derived[2],
                failures=derived[3],
                status=derived[4],
                fingerprint=fingerprint,
            )
        )
    except ResearchCalibrationDiagnosticQualityError as error:
        return Failure(error)

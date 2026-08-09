from __future__ import annotations

import json
from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum
from hashlib import sha256
from re import fullmatch
from uuid import UUID

from qore.infrastructure.research_confidence_calibration_uncertainty import (
    ResearchCalibrationUncertaintyEvidence,
)
from qore.kernel.errors import InfrastructureError
from qore.kernel.result import Failure, Result, Success

_ZERO = Decimal(0)
_ONE = Decimal(1)


class ResearchCalibrationCoveragePrecisionError(InfrastructureError):
    """Base error for research-only calibration coverage/precision assessment."""

    __slots__ = ()


class ResearchCalibrationCoveragePrecisionValidationError(
    ResearchCalibrationCoveragePrecisionError
):
    """Violation of a calibration coverage/precision assessment invariant."""

    __slots__ = ()


def _validate_width(value: Decimal, *, field_name: str) -> None:
    if not isinstance(value, Decimal) or not value.is_finite():
        raise ResearchCalibrationCoveragePrecisionValidationError(
            f"{field_name} must be a finite Decimal"
        )
    if not _ZERO <= value <= _ONE:
        raise ResearchCalibrationCoveragePrecisionValidationError(
            f"{field_name} must remain inside [0, 1]"
        )


@dataclass(frozen=True, slots=True)
class ResearchCalibrationCoveragePrecisionAssessmentId:
    value: UUID

    def __post_init__(self) -> None:
        if not isinstance(self.value, UUID):
            raise ResearchCalibrationCoveragePrecisionValidationError(
                "coverage/precision assessment id must be UUID"
            )

    def logical_values(self) -> tuple[str, ...]:
        return (str(self.value),)


@dataclass(frozen=True, slots=True)
class ResearchCalibrationCoveragePrecisionPolicy:
    """Explicit research thresholds for OOS sample coverage and metric precision.

    All thresholds are analyst-supplied. Meeting this policy means only that the
    exact OOS evidence satisfies these declared minimum counts and maximum interval
    widths. It does not establish a universal minimum sample size, statistical
    sufficiency, nominal interval coverage, calibration quality, or probability
    validity. No default rule-of-thumb is embedded in the contract.
    """

    minimum_sample_size: int
    minimum_event_count: int
    minimum_non_event_count: int
    maximum_brier_interval_width: Decimal
    maximum_ece_interval_width: Decimal

    def __post_init__(self) -> None:
        if type(self.minimum_sample_size) is not int or self.minimum_sample_size < 2:
            raise ResearchCalibrationCoveragePrecisionValidationError(
                "minimum_sample_size must be an integer of at least two"
            )
        for field_name, value in (
            ("minimum_event_count", self.minimum_event_count),
            ("minimum_non_event_count", self.minimum_non_event_count),
        ):
            if type(value) is not int or value < 0:
                raise ResearchCalibrationCoveragePrecisionValidationError(
                    f"{field_name} must be a non-negative integer"
                )
        _validate_width(
            self.maximum_brier_interval_width,
            field_name="maximum_brier_interval_width",
        )
        _validate_width(
            self.maximum_ece_interval_width,
            field_name="maximum_ece_interval_width",
        )

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.minimum_sample_size,
            self.minimum_event_count,
            self.minimum_non_event_count,
            format(self.maximum_brier_interval_width, "f"),
            format(self.maximum_ece_interval_width, "f"),
        )


class ResearchCalibrationCoveragePrecisionFailure(StrEnum):
    """Canonical reasons why exact evidence does not meet the declared policy."""

    SAMPLE_SIZE = "sample-size"
    EVENT_COUNT = "event-count"
    NON_EVENT_COUNT = "non-event-count"
    BRIER_INTERVAL_WIDTH = "brier-interval-width"
    ECE_INTERVAL_WIDTH = "ece-interval-width"


class ResearchCalibrationCoveragePrecisionStatus(StrEnum):
    """Policy-local assessment status; never an operational approval state."""

    MEETS_DECLARED_POLICY = "meets-declared-policy"
    DOES_NOT_MEET_DECLARED_POLICY = "does-not-meet-declared-policy"


type _DerivedAssessment = tuple[
    int,
    int,
    int,
    Decimal,
    Decimal,
    tuple[ResearchCalibrationCoveragePrecisionFailure, ...],
    ResearchCalibrationCoveragePrecisionStatus,
]


def _derive_assessment(
    uncertainty: ResearchCalibrationUncertaintyEvidence,
    policy: ResearchCalibrationCoveragePrecisionPolicy,
) -> _DerivedAssessment:
    if not isinstance(uncertainty, ResearchCalibrationUncertaintyEvidence):
        raise ResearchCalibrationCoveragePrecisionValidationError(
            "coverage/precision assessment requires ResearchCalibrationUncertaintyEvidence"
        )
    if not isinstance(policy, ResearchCalibrationCoveragePrecisionPolicy):
        raise ResearchCalibrationCoveragePrecisionValidationError(
            "coverage/precision assessment requires explicit policy"
        )

    observations = uncertainty.validation.validation_set.observations
    sample_size = len(observations)
    if sample_size != uncertainty.sample_size:
        raise ResearchCalibrationCoveragePrecisionValidationError(
            "uncertainty sample_size must match exact OOS validation observations"
        )
    event_count = sum(1 for item in observations if item.source.event_occurred)
    non_event_count = sample_size - event_count
    brier_width = uncertainty.brier_interval.upper - uncertainty.brier_interval.lower
    ece_width = uncertainty.ece_interval.upper - uncertainty.ece_interval.lower
    _validate_width(brier_width, field_name="derived Brier interval width")
    _validate_width(ece_width, field_name="derived ECE interval width")

    failures: list[ResearchCalibrationCoveragePrecisionFailure] = []
    if sample_size < policy.minimum_sample_size:
        failures.append(ResearchCalibrationCoveragePrecisionFailure.SAMPLE_SIZE)
    if event_count < policy.minimum_event_count:
        failures.append(ResearchCalibrationCoveragePrecisionFailure.EVENT_COUNT)
    if non_event_count < policy.minimum_non_event_count:
        failures.append(ResearchCalibrationCoveragePrecisionFailure.NON_EVENT_COUNT)
    if brier_width > policy.maximum_brier_interval_width:
        failures.append(ResearchCalibrationCoveragePrecisionFailure.BRIER_INTERVAL_WIDTH)
    if ece_width > policy.maximum_ece_interval_width:
        failures.append(ResearchCalibrationCoveragePrecisionFailure.ECE_INTERVAL_WIDTH)

    failure_tuple = tuple(failures)
    status = (
        ResearchCalibrationCoveragePrecisionStatus.MEETS_DECLARED_POLICY
        if not failure_tuple
        else ResearchCalibrationCoveragePrecisionStatus.DOES_NOT_MEET_DECLARED_POLICY
    )
    return (
        sample_size,
        event_count,
        non_event_count,
        brier_width,
        ece_width,
        failure_tuple,
        status,
    )


@dataclass(frozen=True, slots=True)
class ResearchCalibrationCoveragePrecisionFingerprint:
    value: str

    def __post_init__(self) -> None:
        if not isinstance(self.value, str) or fullmatch(r"[0-9a-f]{64}", self.value) is None:
            raise ResearchCalibrationCoveragePrecisionValidationError(
                "coverage/precision fingerprint must be 64 lowercase hex characters"
            )

    def logical_values(self) -> tuple[str, ...]:
        return (self.value,)


def compute_research_calibration_coverage_precision_fingerprint(
    *,
    uncertainty: ResearchCalibrationUncertaintyEvidence,
    policy: ResearchCalibrationCoveragePrecisionPolicy,
    derived: _DerivedAssessment,
) -> ResearchCalibrationCoveragePrecisionFingerprint:
    """Hash exact upstream uncertainty, policy, derived counts/widths and status."""

    expected = _derive_assessment(uncertainty, policy)
    if derived != expected:
        raise ResearchCalibrationCoveragePrecisionValidationError(
            "coverage/precision fingerprint inputs must match deterministic assessment"
        )
    canonical = {
        "uncertainty_fingerprint": uncertainty.fingerprint.logical_values(),
        "policy": policy.logical_values(),
        "sample_size": derived[0],
        "event_count": derived[1],
        "non_event_count": derived[2],
        "brier_interval_width": format(derived[3], "f"),
        "ece_interval_width": format(derived[4], "f"),
        "failures": tuple(item.value for item in derived[5]),
        "status": derived[6].value,
    }
    encoded = json.dumps(
        canonical,
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    return ResearchCalibrationCoveragePrecisionFingerprint(sha256(encoded).hexdigest())


@dataclass(frozen=True, slots=True)
class ResearchCalibrationCoveragePrecisionAssessment:
    """Research-only assessment of declared OOS coverage and precision thresholds.

    This evidence deterministically counts OOS events/non-events and compares exact
    bootstrap interval widths with an explicit policy. `MEETS_DECLARED_POLICY` is a
    local statement about those thresholds only.

    It does not establish a universal sample-size requirement, statistical
    sufficiency, calibration quality, a calibrated probability, future predictive
    validity, strategy approval, risk/capital authority, production readiness, or
    execution authority.
    """

    assessment_id: ResearchCalibrationCoveragePrecisionAssessmentId
    uncertainty: ResearchCalibrationUncertaintyEvidence
    policy: ResearchCalibrationCoveragePrecisionPolicy
    sample_size: int
    event_count: int
    non_event_count: int
    brier_interval_width: Decimal
    ece_interval_width: Decimal
    failures: tuple[ResearchCalibrationCoveragePrecisionFailure, ...]
    status: ResearchCalibrationCoveragePrecisionStatus
    fingerprint: ResearchCalibrationCoveragePrecisionFingerprint

    def __post_init__(self) -> None:
        if not isinstance(
            self.assessment_id,
            ResearchCalibrationCoveragePrecisionAssessmentId,
        ):
            raise ResearchCalibrationCoveragePrecisionValidationError(
                "assessment_id must be ResearchCalibrationCoveragePrecisionAssessmentId"
            )
        if not isinstance(self.uncertainty, ResearchCalibrationUncertaintyEvidence):
            raise ResearchCalibrationCoveragePrecisionValidationError(
                "uncertainty must be ResearchCalibrationUncertaintyEvidence"
            )
        if not isinstance(self.policy, ResearchCalibrationCoveragePrecisionPolicy):
            raise ResearchCalibrationCoveragePrecisionValidationError(
                "policy must be ResearchCalibrationCoveragePrecisionPolicy"
            )
        expected = _derive_assessment(self.uncertainty, self.policy)
        actual: _DerivedAssessment = (
            self.sample_size,
            self.event_count,
            self.non_event_count,
            self.brier_interval_width,
            self.ece_interval_width,
            self.failures,
            self.status,
        )
        if actual != expected:
            raise ResearchCalibrationCoveragePrecisionValidationError(
                "coverage/precision assessment must match exact upstream evidence and policy"
            )
        if not isinstance(
            self.fingerprint,
            ResearchCalibrationCoveragePrecisionFingerprint,
        ):
            raise ResearchCalibrationCoveragePrecisionValidationError(
                "fingerprint must be ResearchCalibrationCoveragePrecisionFingerprint"
            )
        expected_fingerprint = compute_research_calibration_coverage_precision_fingerprint(
            uncertainty=self.uncertainty,
            policy=self.policy,
            derived=expected,
        )
        if self.fingerprint != expected_fingerprint:
            raise ResearchCalibrationCoveragePrecisionValidationError(
                "coverage/precision fingerprint must match exact assessment evidence"
            )

    @property
    def meets_declared_policy(self) -> bool:
        return self.status is ResearchCalibrationCoveragePrecisionStatus.MEETS_DECLARED_POLICY

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.assessment_id.logical_values(),
            self.uncertainty.fingerprint.logical_values(),
            self.policy.logical_values(),
            self.sample_size,
            self.event_count,
            self.non_event_count,
            format(self.brier_interval_width, "f"),
            format(self.ece_interval_width, "f"),
            tuple(item.value for item in self.failures),
            self.status.value,
            self.fingerprint.logical_values(),
        )


def assess_research_calibration_coverage_precision(
    *,
    assessment_id: ResearchCalibrationCoveragePrecisionAssessmentId,
    uncertainty: ResearchCalibrationUncertaintyEvidence,
    policy: ResearchCalibrationCoveragePrecisionPolicy,
) -> Result[
    ResearchCalibrationCoveragePrecisionAssessment,
    ResearchCalibrationCoveragePrecisionError,
]:
    """Assess declared thresholds without certifying calibration or probability."""

    try:
        derived = _derive_assessment(uncertainty, policy)
        fingerprint = compute_research_calibration_coverage_precision_fingerprint(
            uncertainty=uncertainty,
            policy=policy,
            derived=derived,
        )
        return Success(
            ResearchCalibrationCoveragePrecisionAssessment(
                assessment_id=assessment_id,
                uncertainty=uncertainty,
                policy=policy,
                sample_size=derived[0],
                event_count=derived[1],
                non_event_count=derived[2],
                brier_interval_width=derived[3],
                ece_interval_width=derived[4],
                failures=derived[5],
                status=derived[6],
                fingerprint=fingerprint,
            )
        )
    except ResearchCalibrationCoveragePrecisionError as error:
        return Failure(error)

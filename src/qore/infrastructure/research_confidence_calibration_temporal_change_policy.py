from __future__ import annotations

import json
from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum
from hashlib import sha256
from re import fullmatch
from uuid import UUID

from qore.infrastructure.research_confidence_calibration_temporal_comparison_uncertainty import (
    ResearchCalibrationTemporalComparisonUncertaintyEvidence,
)
from qore.kernel.errors import InfrastructureError
from qore.kernel.result import Failure, Result, Success

_ZERO = Decimal(0)
_ONE = Decimal(1)


class ResearchCalibrationTemporalChangePolicyError(InfrastructureError):
    """Base error for research-only temporal calibration change assessment."""

    __slots__ = ()


class ResearchCalibrationTemporalChangePolicyValidationError(
    ResearchCalibrationTemporalChangePolicyError
):
    """Violation of a temporal calibration change-policy invariant."""

    __slots__ = ()


def _validate_threshold(value: Decimal, *, field_name: str) -> None:
    if not isinstance(value, Decimal) or not value.is_finite():
        raise ResearchCalibrationTemporalChangePolicyValidationError(
            f"{field_name} must be a finite Decimal"
        )
    if not _ZERO <= value <= _ONE:
        raise ResearchCalibrationTemporalChangePolicyValidationError(
            f"{field_name} must remain inside [0, 1]"
        )


@dataclass(frozen=True, slots=True)
class ResearchCalibrationTemporalChangeAssessmentId:
    value: UUID

    def __post_init__(self) -> None:
        if not isinstance(self.value, UUID):
            raise ResearchCalibrationTemporalChangePolicyValidationError(
                "temporal change assessment id must be UUID"
            )

    def logical_values(self) -> tuple[str, ...]:
        return (str(self.value),)


@dataclass(frozen=True, slots=True)
class ResearchCalibrationTemporalChangePolicy:
    """Explicit research limits for observed temporal calibration changes.

    Every threshold is analyst-supplied. Meeting this policy means only that the
    exact point changes and bootstrap interval upper bounds from one ordered
    baseline/comparison pair remain inside the declared limits. It is not a drift
    test, significance test, stability certification, calibration certification,
    or probability qualification, and it carries no operational authority.
    """

    maximum_absolute_mean_gap_change: Decimal
    maximum_absolute_ece_change: Decimal
    maximum_absolute_mean_probability_shift: Decimal
    maximum_absolute_event_rate_shift: Decimal
    maximum_mean_gap_change_interval_upper_bound: Decimal
    maximum_ece_change_interval_upper_bound: Decimal
    maximum_mean_probability_shift_interval_upper_bound: Decimal
    maximum_event_rate_shift_interval_upper_bound: Decimal

    def __post_init__(self) -> None:
        for field_name, value in (
            (
                "maximum_absolute_mean_gap_change",
                self.maximum_absolute_mean_gap_change,
            ),
            (
                "maximum_absolute_ece_change",
                self.maximum_absolute_ece_change,
            ),
            (
                "maximum_absolute_mean_probability_shift",
                self.maximum_absolute_mean_probability_shift,
            ),
            (
                "maximum_absolute_event_rate_shift",
                self.maximum_absolute_event_rate_shift,
            ),
            (
                "maximum_mean_gap_change_interval_upper_bound",
                self.maximum_mean_gap_change_interval_upper_bound,
            ),
            (
                "maximum_ece_change_interval_upper_bound",
                self.maximum_ece_change_interval_upper_bound,
            ),
            (
                "maximum_mean_probability_shift_interval_upper_bound",
                self.maximum_mean_probability_shift_interval_upper_bound,
            ),
            (
                "maximum_event_rate_shift_interval_upper_bound",
                self.maximum_event_rate_shift_interval_upper_bound,
            ),
        ):
            _validate_threshold(value, field_name=field_name)

    def logical_values(self) -> tuple[str, ...]:
        return (
            format(self.maximum_absolute_mean_gap_change, "f"),
            format(self.maximum_absolute_ece_change, "f"),
            format(self.maximum_absolute_mean_probability_shift, "f"),
            format(self.maximum_absolute_event_rate_shift, "f"),
            format(self.maximum_mean_gap_change_interval_upper_bound, "f"),
            format(self.maximum_ece_change_interval_upper_bound, "f"),
            format(
                self.maximum_mean_probability_shift_interval_upper_bound,
                "f",
            ),
            format(self.maximum_event_rate_shift_interval_upper_bound, "f"),
        )


class ResearchCalibrationTemporalChangeFailure(StrEnum):
    """Canonical reasons why exact evidence exceeds the declared limits."""

    ABSOLUTE_MEAN_GAP_CHANGE = "absolute-mean-gap-change"
    ABSOLUTE_ECE_CHANGE = "absolute-ece-change"
    ABSOLUTE_MEAN_PROBABILITY_SHIFT = "absolute-mean-probability-shift"
    ABSOLUTE_EVENT_RATE_SHIFT = "absolute-event-rate-shift"
    MEAN_GAP_CHANGE_INTERVAL_UPPER_BOUND = (
        "mean-gap-change-interval-upper-bound"
    )
    ECE_CHANGE_INTERVAL_UPPER_BOUND = "ece-change-interval-upper-bound"
    MEAN_PROBABILITY_SHIFT_INTERVAL_UPPER_BOUND = (
        "mean-probability-shift-interval-upper-bound"
    )
    EVENT_RATE_SHIFT_INTERVAL_UPPER_BOUND = (
        "event-rate-shift-interval-upper-bound"
    )


class ResearchCalibrationTemporalChangeStatus(StrEnum):
    """Policy-local result; never a drift or operational approval state."""

    MEETS_DECLARED_POLICY = "meets-declared-policy"
    DOES_NOT_MEET_DECLARED_POLICY = "does-not-meet-declared-policy"


type _DerivedAssessment = tuple[
    Decimal,
    Decimal,
    Decimal,
    Decimal,
    Decimal,
    Decimal,
    Decimal,
    Decimal,
    tuple[ResearchCalibrationTemporalChangeFailure, ...],
    ResearchCalibrationTemporalChangeStatus,
]


def _derive_assessment(
    uncertainty: ResearchCalibrationTemporalComparisonUncertaintyEvidence,
    policy: ResearchCalibrationTemporalChangePolicy,
) -> _DerivedAssessment:
    if not isinstance(
        uncertainty,
        ResearchCalibrationTemporalComparisonUncertaintyEvidence,
    ):
        raise ResearchCalibrationTemporalChangePolicyValidationError(
            "temporal change assessment requires exact uncertainty evidence"
        )
    if not isinstance(policy, ResearchCalibrationTemporalChangePolicy):
        raise ResearchCalibrationTemporalChangePolicyValidationError(
            "temporal change assessment requires explicit policy"
        )

    absolute_mean_gap_change = uncertainty.source_absolute_mean_gap_change
    absolute_ece_change = uncertainty.source_absolute_ece_change
    absolute_mean_probability_shift = (
        uncertainty.source_absolute_mean_probability_shift
    )
    absolute_event_rate_shift = uncertainty.source_absolute_event_rate_shift
    mean_gap_interval_upper = uncertainty.absolute_mean_gap_change_interval.upper
    ece_interval_upper = uncertainty.absolute_ece_change_interval.upper
    mean_probability_interval_upper = (
        uncertainty.absolute_mean_probability_shift_interval.upper
    )
    event_rate_interval_upper = (
        uncertainty.absolute_event_rate_shift_interval.upper
    )

    values = (
        ("absolute_mean_gap_change", absolute_mean_gap_change),
        ("absolute_ece_change", absolute_ece_change),
        (
            "absolute_mean_probability_shift",
            absolute_mean_probability_shift,
        ),
        ("absolute_event_rate_shift", absolute_event_rate_shift),
        ("mean_gap_change_interval_upper", mean_gap_interval_upper),
        ("ece_change_interval_upper", ece_interval_upper),
        (
            "mean_probability_shift_interval_upper",
            mean_probability_interval_upper,
        ),
        ("event_rate_shift_interval_upper", event_rate_interval_upper),
    )
    for field_name, value in values:
        _validate_threshold(value, field_name=field_name)

    failures: list[ResearchCalibrationTemporalChangeFailure] = []
    if absolute_mean_gap_change > policy.maximum_absolute_mean_gap_change:
        failures.append(
            ResearchCalibrationTemporalChangeFailure.ABSOLUTE_MEAN_GAP_CHANGE
        )
    if absolute_ece_change > policy.maximum_absolute_ece_change:
        failures.append(
            ResearchCalibrationTemporalChangeFailure.ABSOLUTE_ECE_CHANGE
        )
    if (
        absolute_mean_probability_shift
        > policy.maximum_absolute_mean_probability_shift
    ):
        failures.append(
            ResearchCalibrationTemporalChangeFailure.ABSOLUTE_MEAN_PROBABILITY_SHIFT
        )
    if absolute_event_rate_shift > policy.maximum_absolute_event_rate_shift:
        failures.append(
            ResearchCalibrationTemporalChangeFailure.ABSOLUTE_EVENT_RATE_SHIFT
        )
    if (
        mean_gap_interval_upper
        > policy.maximum_mean_gap_change_interval_upper_bound
    ):
        failures.append(
            ResearchCalibrationTemporalChangeFailure.MEAN_GAP_CHANGE_INTERVAL_UPPER_BOUND
        )
    if ece_interval_upper > policy.maximum_ece_change_interval_upper_bound:
        failures.append(
            ResearchCalibrationTemporalChangeFailure.ECE_CHANGE_INTERVAL_UPPER_BOUND
        )
    if (
        mean_probability_interval_upper
        > policy.maximum_mean_probability_shift_interval_upper_bound
    ):
        failures.append(
            ResearchCalibrationTemporalChangeFailure.MEAN_PROBABILITY_SHIFT_INTERVAL_UPPER_BOUND
        )
    if (
        event_rate_interval_upper
        > policy.maximum_event_rate_shift_interval_upper_bound
    ):
        failures.append(
            ResearchCalibrationTemporalChangeFailure.EVENT_RATE_SHIFT_INTERVAL_UPPER_BOUND
        )

    failure_tuple = tuple(failures)
    status = (
        ResearchCalibrationTemporalChangeStatus.MEETS_DECLARED_POLICY
        if not failure_tuple
        else ResearchCalibrationTemporalChangeStatus.DOES_NOT_MEET_DECLARED_POLICY
    )
    return (
        absolute_mean_gap_change,
        absolute_ece_change,
        absolute_mean_probability_shift,
        absolute_event_rate_shift,
        mean_gap_interval_upper,
        ece_interval_upper,
        mean_probability_interval_upper,
        event_rate_interval_upper,
        failure_tuple,
        status,
    )


@dataclass(frozen=True, slots=True)
class ResearchCalibrationTemporalChangeFingerprint:
    value: str

    def __post_init__(self) -> None:
        if (
            not isinstance(self.value, str)
            or fullmatch(r"[0-9a-f]{64}", self.value) is None
        ):
            raise ResearchCalibrationTemporalChangePolicyValidationError(
                "temporal change fingerprint must be 64 lowercase hex characters"
            )

    def logical_values(self) -> tuple[str, ...]:
        return (self.value,)


def compute_research_calibration_temporal_change_fingerprint(
    *,
    uncertainty: ResearchCalibrationTemporalComparisonUncertaintyEvidence,
    policy: ResearchCalibrationTemporalChangePolicy,
    derived: _DerivedAssessment,
) -> ResearchCalibrationTemporalChangeFingerprint:
    """Hash exact uncertainty evidence, policy, derived values and status."""

    expected = _derive_assessment(uncertainty, policy)
    if derived != expected:
        raise ResearchCalibrationTemporalChangePolicyValidationError(
            "temporal change fingerprint inputs must match exact assessment"
        )
    canonical = {
        "uncertainty_fingerprint": uncertainty.fingerprint.logical_values(),
        "policy": policy.logical_values(),
        "absolute_mean_gap_change": format(derived[0], "f"),
        "absolute_ece_change": format(derived[1], "f"),
        "absolute_mean_probability_shift": format(derived[2], "f"),
        "absolute_event_rate_shift": format(derived[3], "f"),
        "mean_gap_change_interval_upper": format(derived[4], "f"),
        "ece_change_interval_upper": format(derived[5], "f"),
        "mean_probability_shift_interval_upper": format(derived[6], "f"),
        "event_rate_shift_interval_upper": format(derived[7], "f"),
        "failures": tuple(item.value for item in derived[8]),
        "status": derived[9].value,
    }
    encoded = json.dumps(
        canonical,
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    return ResearchCalibrationTemporalChangeFingerprint(sha256(encoded).hexdigest())


@dataclass(frozen=True, slots=True)
class ResearchCalibrationTemporalChangeAssessment:
    """Research-only assessment against explicit temporal change limits.

    `MEETS_DECLARED_POLICY` means only that one exact temporal comparison and its
    deterministic uncertainty evidence stay inside analyst-declared point and
    interval-upper limits. It does not declare drift absence, statistical
    significance, temporal stability, external validity, calibrated probability,
    strategy approval, production readiness, capital authorization, or execution
    authority.
    """

    assessment_id: ResearchCalibrationTemporalChangeAssessmentId
    uncertainty: ResearchCalibrationTemporalComparisonUncertaintyEvidence
    policy: ResearchCalibrationTemporalChangePolicy
    absolute_mean_gap_change: Decimal
    absolute_ece_change: Decimal
    absolute_mean_probability_shift: Decimal
    absolute_event_rate_shift: Decimal
    mean_gap_change_interval_upper: Decimal
    ece_change_interval_upper: Decimal
    mean_probability_shift_interval_upper: Decimal
    event_rate_shift_interval_upper: Decimal
    failures: tuple[ResearchCalibrationTemporalChangeFailure, ...]
    status: ResearchCalibrationTemporalChangeStatus
    fingerprint: ResearchCalibrationTemporalChangeFingerprint

    def __post_init__(self) -> None:
        if not isinstance(
            self.assessment_id,
            ResearchCalibrationTemporalChangeAssessmentId,
        ):
            raise ResearchCalibrationTemporalChangePolicyValidationError(
                "assessment_id must use temporal change assessment id"
            )
        if not isinstance(
            self.uncertainty,
            ResearchCalibrationTemporalComparisonUncertaintyEvidence,
        ):
            raise ResearchCalibrationTemporalChangePolicyValidationError(
                "uncertainty must be temporal comparison uncertainty evidence"
            )
        if not isinstance(self.policy, ResearchCalibrationTemporalChangePolicy):
            raise ResearchCalibrationTemporalChangePolicyValidationError(
                "policy must be ResearchCalibrationTemporalChangePolicy"
            )
        expected = _derive_assessment(self.uncertainty, self.policy)
        actual: _DerivedAssessment = (
            self.absolute_mean_gap_change,
            self.absolute_ece_change,
            self.absolute_mean_probability_shift,
            self.absolute_event_rate_shift,
            self.mean_gap_change_interval_upper,
            self.ece_change_interval_upper,
            self.mean_probability_shift_interval_upper,
            self.event_rate_shift_interval_upper,
            self.failures,
            self.status,
        )
        if actual != expected:
            raise ResearchCalibrationTemporalChangePolicyValidationError(
                "temporal change assessment must match exact upstream evidence"
            )
        if not isinstance(
            self.fingerprint,
            ResearchCalibrationTemporalChangeFingerprint,
        ):
            raise ResearchCalibrationTemporalChangePolicyValidationError(
                "fingerprint must be temporal change fingerprint"
            )
        expected_fingerprint = compute_research_calibration_temporal_change_fingerprint(
            uncertainty=self.uncertainty,
            policy=self.policy,
            derived=expected,
        )
        if self.fingerprint != expected_fingerprint:
            raise ResearchCalibrationTemporalChangePolicyValidationError(
                "temporal change fingerprint must match exact assessment"
            )

    @property
    def meets_declared_policy(self) -> bool:
        return self.status is ResearchCalibrationTemporalChangeStatus.MEETS_DECLARED_POLICY

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.assessment_id.logical_values(),
            self.uncertainty.fingerprint.logical_values(),
            self.policy.logical_values(),
            format(self.absolute_mean_gap_change, "f"),
            format(self.absolute_ece_change, "f"),
            format(self.absolute_mean_probability_shift, "f"),
            format(self.absolute_event_rate_shift, "f"),
            format(self.mean_gap_change_interval_upper, "f"),
            format(self.ece_change_interval_upper, "f"),
            format(self.mean_probability_shift_interval_upper, "f"),
            format(self.event_rate_shift_interval_upper, "f"),
            tuple(item.value for item in self.failures),
            self.status.value,
            self.fingerprint.logical_values(),
        )


def assess_research_calibration_temporal_change(
    *,
    assessment_id: ResearchCalibrationTemporalChangeAssessmentId,
    uncertainty: ResearchCalibrationTemporalComparisonUncertaintyEvidence,
    policy: ResearchCalibrationTemporalChangePolicy,
) -> Result[
    ResearchCalibrationTemporalChangeAssessment,
    ResearchCalibrationTemporalChangePolicyError,
]:
    """Assess declared change limits without declaring drift or stability."""

    try:
        derived = _derive_assessment(uncertainty, policy)
        fingerprint = compute_research_calibration_temporal_change_fingerprint(
            uncertainty=uncertainty,
            policy=policy,
            derived=derived,
        )
        return Success(
            ResearchCalibrationTemporalChangeAssessment(
                assessment_id=assessment_id,
                uncertainty=uncertainty,
                policy=policy,
                absolute_mean_gap_change=derived[0],
                absolute_ece_change=derived[1],
                absolute_mean_probability_shift=derived[2],
                absolute_event_rate_shift=derived[3],
                mean_gap_change_interval_upper=derived[4],
                ece_change_interval_upper=derived[5],
                mean_probability_shift_interval_upper=derived[6],
                event_rate_shift_interval_upper=derived[7],
                failures=derived[8],
                status=derived[9],
                fingerprint=fingerprint,
            )
        )
    except ResearchCalibrationTemporalChangePolicyError as error:
        return Failure(error)

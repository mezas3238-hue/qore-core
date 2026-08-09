from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from hashlib import sha256
from re import fullmatch
from uuid import UUID

from qore.infrastructure.research_confidence_calibration_oos_validation import (
    ResearchCalibrationOosValidationEvidence,
)
from qore.kernel.errors import InfrastructureError
from qore.kernel.result import Failure, Result, Success

_ZERO = Decimal(0)
_ONE = Decimal(1)


class ResearchCalibrationTemporalComparisonError(InfrastructureError):
    """Base error for research-only temporal calibration comparison evidence."""

    __slots__ = ()


class ResearchCalibrationTemporalComparisonValidationError(
    ResearchCalibrationTemporalComparisonError
):
    """Violation of a temporal calibration comparison invariant."""

    __slots__ = ()


def _validate_timestamp(value: datetime, *, field_name: str) -> None:
    if not isinstance(value, datetime):
        raise ResearchCalibrationTemporalComparisonValidationError(
            f"{field_name} must be datetime"
        )
    if value.tzinfo is None or value.utcoffset() is None:
        raise ResearchCalibrationTemporalComparisonValidationError(
            f"{field_name} must be timezone-aware"
        )


def _validate_unit_decimal(value: Decimal, *, field_name: str) -> None:
    if not isinstance(value, Decimal) or not value.is_finite():
        raise ResearchCalibrationTemporalComparisonValidationError(
            f"{field_name} must be a finite Decimal"
        )
    if not _ZERO <= value <= _ONE:
        raise ResearchCalibrationTemporalComparisonValidationError(
            f"{field_name} must remain inside [0, 1]"
        )


@dataclass(frozen=True, slots=True)
class ResearchCalibrationTemporalComparisonId:
    value: UUID

    def __post_init__(self) -> None:
        if not isinstance(self.value, UUID):
            raise ResearchCalibrationTemporalComparisonValidationError(
                "temporal comparison id must be UUID"
            )

    def logical_values(self) -> tuple[str, ...]:
        return (str(self.value),)


type _DerivedComparison = tuple[
    int,
    int,
    Decimal,
    Decimal,
    Decimal,
    Decimal,
    Decimal,
    Decimal,
]


def _derive_comparison(
    baseline: ResearchCalibrationOosValidationEvidence,
    comparison: ResearchCalibrationOosValidationEvidence,
) -> _DerivedComparison:
    if not isinstance(baseline, ResearchCalibrationOosValidationEvidence):
        raise ResearchCalibrationTemporalComparisonValidationError(
            "baseline must be ResearchCalibrationOosValidationEvidence"
        )
    if not isinstance(comparison, ResearchCalibrationOosValidationEvidence):
        raise ResearchCalibrationTemporalComparisonValidationError(
            "comparison must be ResearchCalibrationOosValidationEvidence"
        )

    baseline_set = baseline.validation_set
    comparison_set = comparison.validation_set
    baseline_fit = baseline_set.mapping_fit
    comparison_fit = comparison_set.mapping_fit

    if baseline_fit.mapping_id != comparison_fit.mapping_id:
        raise ResearchCalibrationTemporalComparisonValidationError(
            "temporal comparison requires the same calibration mapping id"
        )
    if baseline_fit.fingerprint != comparison_fit.fingerprint:
        raise ResearchCalibrationTemporalComparisonValidationError(
            "temporal comparison requires the same calibration mapping fingerprint"
        )
    if baseline_set.fold_number != comparison_set.fold_number:
        raise ResearchCalibrationTemporalComparisonValidationError(
            "temporal comparison requires the same frozen evaluation fold"
        )
    if baseline.policy != comparison.policy:
        raise ResearchCalibrationTemporalComparisonValidationError(
            "temporal comparison requires the same OOS calibration diagnostic policy"
        )

    baseline_observations = baseline_set.observations
    comparison_observations = comparison_set.observations
    if not baseline_observations or not comparison_observations:
        raise ResearchCalibrationTemporalComparisonValidationError(
            "temporal comparison requires non-empty validation windows"
        )

    baseline_ids = {
        item.source.analysis.analysis_id for item in baseline_observations
    }
    comparison_ids = {
        item.source.analysis.analysis_id for item in comparison_observations
    }
    if baseline_ids.intersection(comparison_ids):
        raise ResearchCalibrationTemporalComparisonValidationError(
            "temporal comparison validation windows must use disjoint analysis ids"
        )

    for label, observations in (
        ("baseline", baseline_observations),
        ("comparison", comparison_observations),
    ):
        for item in observations:
            _validate_timestamp(
                item.score_observed_at,
                field_name=f"{label} score_observed_at",
            )
            _validate_timestamp(
                item.outcome_observed_at,
                field_name=f"{label} outcome_observed_at",
            )
            if item.outcome_observed_at < item.score_observed_at:
                raise ResearchCalibrationTemporalComparisonValidationError(
                    f"{label} outcome cannot precede score observation"
                )

    baseline_last_outcome = max(
        item.outcome_observed_at for item in baseline_observations
    )
    comparison_first_score = min(
        item.score_observed_at for item in comparison_observations
    )
    if baseline_last_outcome > comparison_first_score:
        raise ResearchCalibrationTemporalComparisonValidationError(
            "baseline validation window must finish before comparison begins"
        )

    baseline_gap = abs(
        baseline.mean_estimated_probability - baseline.empirical_event_rate
    )
    comparison_gap = abs(
        comparison.mean_estimated_probability - comparison.empirical_event_rate
    )
    gap_change = abs(comparison_gap - baseline_gap)
    ece_change = abs(
        comparison.expected_calibration_error - baseline.expected_calibration_error
    )
    mean_probability_shift = abs(
        comparison.mean_estimated_probability - baseline.mean_estimated_probability
    )
    event_rate_shift = abs(
        comparison.empirical_event_rate - baseline.empirical_event_rate
    )

    for field_name, value in (
        ("baseline absolute mean gap", baseline_gap),
        ("comparison absolute mean gap", comparison_gap),
        ("absolute mean-gap change", gap_change),
        ("absolute ECE change", ece_change),
        ("absolute mean-probability shift", mean_probability_shift),
        ("absolute event-rate shift", event_rate_shift),
    ):
        _validate_unit_decimal(value, field_name=field_name)

    return (
        len(baseline_observations),
        len(comparison_observations),
        baseline_gap,
        comparison_gap,
        gap_change,
        ece_change,
        mean_probability_shift,
        event_rate_shift,
    )


@dataclass(frozen=True, slots=True)
class ResearchCalibrationTemporalComparisonFingerprint:
    value: str

    def __post_init__(self) -> None:
        if not isinstance(self.value, str) or fullmatch(
            r"[0-9a-f]{64}",
            self.value,
        ) is None:
            raise ResearchCalibrationTemporalComparisonValidationError(
                "temporal comparison fingerprint must be 64 lowercase hex characters"
            )

    def logical_values(self) -> tuple[str, ...]:
        return (self.value,)


def compute_research_calibration_temporal_comparison_fingerprint(
    *,
    baseline: ResearchCalibrationOosValidationEvidence,
    comparison: ResearchCalibrationOosValidationEvidence,
    derived: _DerivedComparison,
) -> ResearchCalibrationTemporalComparisonFingerprint:
    """Hash exact ordered OOS evidence and deterministic temporal diagnostics."""

    expected = _derive_comparison(baseline, comparison)
    if derived != expected:
        raise ResearchCalibrationTemporalComparisonValidationError(
            "temporal comparison fingerprint inputs must match deterministic evidence"
        )
    canonical = {
        "baseline_fingerprint": baseline.fingerprint.logical_values(),
        "comparison_fingerprint": comparison.fingerprint.logical_values(),
        "baseline_sample_size": derived[0],
        "comparison_sample_size": derived[1],
        "baseline_absolute_mean_gap": format(derived[2], "f"),
        "comparison_absolute_mean_gap": format(derived[3], "f"),
        "absolute_mean_gap_change": format(derived[4], "f"),
        "absolute_ece_change": format(derived[5], "f"),
        "absolute_mean_probability_shift": format(derived[6], "f"),
        "absolute_event_rate_shift": format(derived[7], "f"),
    }
    encoded = json.dumps(
        canonical,
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    return ResearchCalibrationTemporalComparisonFingerprint(
        sha256(encoded).hexdigest()
    )


@dataclass(frozen=True, slots=True)
class ResearchCalibrationTemporalComparisonEvidence:
    """Research-only comparison of two ordered OOS windows for one fitted mapping.

    The evidence proves that two validation windows use the same mapping/fold and
    OOS diagnostic policy, contain disjoint analysis identities, are ordered without
    simulated-time overlap, and reports deterministic changes in selected
    calibration diagnostics.

    It does not detect calibration drift, establish statistical significance,
    estimate a drift onset, prove stationarity, quantify uncertainty of the changes,
    certify calibration, create `CalibratedProbability`, prove external validity,
    authorize production/capital, or create execution authority.
    """

    comparison_id: ResearchCalibrationTemporalComparisonId
    baseline: ResearchCalibrationOosValidationEvidence
    comparison: ResearchCalibrationOosValidationEvidence
    baseline_sample_size: int
    comparison_sample_size: int
    baseline_absolute_mean_gap: Decimal
    comparison_absolute_mean_gap: Decimal
    absolute_mean_gap_change: Decimal
    absolute_ece_change: Decimal
    absolute_mean_probability_shift: Decimal
    absolute_event_rate_shift: Decimal
    fingerprint: ResearchCalibrationTemporalComparisonFingerprint

    def __post_init__(self) -> None:
        if not isinstance(
            self.comparison_id,
            ResearchCalibrationTemporalComparisonId,
        ):
            raise ResearchCalibrationTemporalComparisonValidationError(
                "comparison_id must be ResearchCalibrationTemporalComparisonId"
            )
        expected = _derive_comparison(self.baseline, self.comparison)
        actual: _DerivedComparison = (
            self.baseline_sample_size,
            self.comparison_sample_size,
            self.baseline_absolute_mean_gap,
            self.comparison_absolute_mean_gap,
            self.absolute_mean_gap_change,
            self.absolute_ece_change,
            self.absolute_mean_probability_shift,
            self.absolute_event_rate_shift,
        )
        if actual != expected:
            raise ResearchCalibrationTemporalComparisonValidationError(
                "temporal comparison metrics must match exact ordered OOS evidence"
            )
        if not isinstance(
            self.fingerprint,
            ResearchCalibrationTemporalComparisonFingerprint,
        ):
            raise ResearchCalibrationTemporalComparisonValidationError(
                "fingerprint must be ResearchCalibrationTemporalComparisonFingerprint"
            )
        expected_fingerprint = (
            compute_research_calibration_temporal_comparison_fingerprint(
                baseline=self.baseline,
                comparison=self.comparison,
                derived=expected,
            )
        )
        if self.fingerprint != expected_fingerprint:
            raise ResearchCalibrationTemporalComparisonValidationError(
                "temporal comparison fingerprint must match exact evidence"
            )

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.comparison_id.logical_values(),
            self.baseline.fingerprint.logical_values(),
            self.comparison.fingerprint.logical_values(),
            self.baseline_sample_size,
            self.comparison_sample_size,
            format(self.baseline_absolute_mean_gap, "f"),
            format(self.comparison_absolute_mean_gap, "f"),
            format(self.absolute_mean_gap_change, "f"),
            format(self.absolute_ece_change, "f"),
            format(self.absolute_mean_probability_shift, "f"),
            format(self.absolute_event_rate_shift, "f"),
            self.fingerprint.logical_values(),
        )


def build_research_calibration_temporal_comparison_evidence(
    *,
    comparison_id: ResearchCalibrationTemporalComparisonId,
    baseline: ResearchCalibrationOosValidationEvidence,
    comparison: ResearchCalibrationOosValidationEvidence,
) -> Result[
    ResearchCalibrationTemporalComparisonEvidence,
    ResearchCalibrationTemporalComparisonError,
]:
    """Build ordered temporal comparison evidence without declaring drift."""

    try:
        derived = _derive_comparison(baseline, comparison)
        fingerprint = compute_research_calibration_temporal_comparison_fingerprint(
            baseline=baseline,
            comparison=comparison,
            derived=derived,
        )
        return Success(
            ResearchCalibrationTemporalComparisonEvidence(
                comparison_id=comparison_id,
                baseline=baseline,
                comparison=comparison,
                baseline_sample_size=derived[0],
                comparison_sample_size=derived[1],
                baseline_absolute_mean_gap=derived[2],
                comparison_absolute_mean_gap=derived[3],
                absolute_mean_gap_change=derived[4],
                absolute_ece_change=derived[5],
                absolute_mean_probability_shift=derived[6],
                absolute_event_rate_shift=derived[7],
                fingerprint=fingerprint,
            )
        )
    except ResearchCalibrationTemporalComparisonError as error:
        return Failure(error)

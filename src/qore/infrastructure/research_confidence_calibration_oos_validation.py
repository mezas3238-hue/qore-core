from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from decimal import ROUND_HALF_EVEN, Context, Decimal, localcontext
from hashlib import sha256
from re import fullmatch
from uuid import UUID

from qore.infrastructure.research_confidence_calibration import (
    ResearchCalibrationTarget,
    ResearchConfidenceOutcomeObservation,
)
from qore.infrastructure.research_confidence_calibration_mapping import (
    ResearchConfidenceCalibrationMappingFit,
)
from qore.infrastructure.research_run import (
    ResearchRunEvidence,
    ResearchRunInputFingerprint,
    ResearchSoftwareRevision,
)
from qore.infrastructure.research_temporal_evaluation import ResearchEvaluationWindow
from qore.kernel.errors import InfrastructureError
from qore.kernel.result import Failure, Result, Success
from qore.specialist.analysis import SpecialistKind

_DECIMAL128 = Context(prec=34, rounding=ROUND_HALF_EVEN)
_ZERO = Decimal(0)
_ONE = Decimal(1)


class ResearchCalibrationOosValidationError(InfrastructureError):
    """Base error for research-only OOS calibration validation evidence."""

    __slots__ = ()


class ResearchCalibrationOosValidationValidationError(
    ResearchCalibrationOosValidationError
):
    """Violation of an OOS calibration validation invariant."""

    __slots__ = ()


def _validate_timestamp(value: datetime, *, field_name: str) -> None:
    if not isinstance(value, datetime):
        raise ResearchCalibrationOosValidationValidationError(
            f"{field_name} must be datetime"
        )
    if value.tzinfo is None or value.utcoffset() is None:
        raise ResearchCalibrationOosValidationValidationError(
            f"{field_name} must be timezone-aware"
        )


def _validate_probability(value: Decimal, *, field_name: str) -> None:
    if not isinstance(value, Decimal) or not value.is_finite():
        raise ResearchCalibrationOosValidationValidationError(
            f"{field_name} must be a finite Decimal"
        )
    if not _ZERO <= value <= _ONE:
        raise ResearchCalibrationOosValidationValidationError(
            f"{field_name} must remain inside [0, 1]"
        )


def _mean(values: tuple[Decimal, ...]) -> Decimal:
    with localcontext(_DECIMAL128):
        return sum(values, _ZERO) / Decimal(len(values))


@dataclass(frozen=True, slots=True)
class ResearchCalibrationOosValidationId:
    value: UUID

    def __post_init__(self) -> None:
        if not isinstance(self.value, UUID):
            raise ResearchCalibrationOosValidationValidationError(
                "calibration OOS validation id must be UUID"
            )

    def logical_values(self) -> tuple[str, ...]:
        return (str(self.value),)


@dataclass(frozen=True, slots=True)
class ResearchCalibrationOosValidationPolicy:
    """Reliability-bin policy for OOS mapping diagnostics."""

    bin_count: int

    def __post_init__(self) -> None:
        if type(self.bin_count) is not int or not 2 <= self.bin_count <= 100:
            raise ResearchCalibrationOosValidationValidationError(
                "calibration OOS bin_count must be an integer between 2 and 100"
            )

    def logical_values(self) -> tuple[int, ...]:
        return (self.bin_count,)


@dataclass(frozen=True, slots=True)
class ResearchCalibrationOosValidationObservation:
    """One OOS score/outcome pair with explicit simulated and process provenance.

    `score_observed_at` and `outcome_observed_at` locate the observation on the
    simulated research axis. `recorded_at` belongs to the process/evidence axis and
    is compared only with process timestamps such as mapping `fitted_at`.

    A record created after fitting does not prove that no human or system accessed
    the outcome earlier; it only provides explicit evidence-record chronology.
    """

    source: ResearchConfidenceOutcomeObservation
    run: ResearchRunEvidence
    score_observed_at: datetime
    outcome_observed_at: datetime
    recorded_at: datetime

    def __post_init__(self) -> None:
        if not isinstance(self.source, ResearchConfidenceOutcomeObservation):
            raise ResearchCalibrationOosValidationValidationError(
                "OOS calibration source must be ResearchConfidenceOutcomeObservation"
            )
        if not isinstance(self.run, ResearchRunEvidence):
            raise ResearchCalibrationOosValidationValidationError(
                "OOS calibration observation run must be ResearchRunEvidence"
            )
        _validate_timestamp(self.score_observed_at, field_name="score_observed_at")
        _validate_timestamp(self.outcome_observed_at, field_name="outcome_observed_at")
        _validate_timestamp(self.recorded_at, field_name="recorded_at")
        if self.outcome_observed_at < self.score_observed_at:
            raise ResearchCalibrationOosValidationValidationError(
                "OOS calibration outcome cannot precede its score observation"
            )

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.source.logical_values(),
            self.run.input_fingerprint.logical_values(),
            self.score_observed_at.isoformat(),
            self.outcome_observed_at.isoformat(),
            self.recorded_at.isoformat(),
        )


def _canonical_observations(
    observations: tuple[ResearchCalibrationOosValidationObservation, ...],
) -> tuple[ResearchCalibrationOosValidationObservation, ...]:
    if not isinstance(observations, tuple) or len(observations) < 2:
        raise ResearchCalibrationOosValidationValidationError(
            "OOS calibration validation requires at least two immutable observations"
        )
    if any(
        not isinstance(item, ResearchCalibrationOosValidationObservation)
        for item in observations
    ):
        raise ResearchCalibrationOosValidationValidationError(
            "OOS calibration observations must use the validation observation contract"
        )
    ids = tuple(item.source.analysis.analysis_id for item in observations)
    if len(set(ids)) != len(ids):
        raise ResearchCalibrationOosValidationValidationError(
            "OOS calibration analysis ids must be unique"
        )
    return tuple(
        sorted(
            observations,
            key=lambda item: (
                item.score_observed_at,
                str(item.source.analysis.analysis_id.value),
            ),
        )
    )


@dataclass(frozen=True, slots=True)
class ResearchCalibrationOosValidationSet:
    """Exact validation set for one fitted mapping and its frozen fold OOS window.

    This contract proves source-ID disjointness from fit data, exact run binding,
    stable target/specialist semantics, OOS simulated-time placement, and evidence
    records no earlier than the mapping fit. It does not prove analyst blindness,
    absence of prior label access, statistical independence, sample adequacy,
    generalization, or calibrated-probability status.
    """

    mapping_fit: ResearchConfidenceCalibrationMappingFit
    fold_number: int
    observations: tuple[ResearchCalibrationOosValidationObservation, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.mapping_fit, ResearchConfidenceCalibrationMappingFit):
            raise ResearchCalibrationOosValidationValidationError(
                "OOS calibration set requires ResearchConfidenceCalibrationMappingFit"
            )
        if type(self.fold_number) is not int or self.fold_number <= 0:
            raise ResearchCalibrationOosValidationValidationError(
                "OOS calibration fold_number must be a positive integer"
            )
        if self.fold_number != self.mapping_fit.training_set.fold_number:
            raise ResearchCalibrationOosValidationValidationError(
                "OOS calibration must validate the fitted mapping on the same frozen fold"
            )
        ordered = _canonical_observations(self.observations)
        if self.observations != ordered:
            raise ResearchCalibrationOosValidationValidationError(
                "OOS calibration observations must use canonical simulated-time/id order"
            )
        plan = self.mapping_fit.training_set.evaluation_freeze.plan
        fold = next(
            (item for item in plan.folds if item.fold_number == self.fold_number),
            None,
        )
        if fold is None:
            raise ResearchCalibrationOosValidationValidationError(
                "OOS calibration fold must exist in the frozen temporal plan"
            )
        training_ids = {
            item.source.analysis.analysis_id
            for item in self.mapping_fit.training_set.observations
        }
        validation_ids = {
            item.source.analysis.analysis_id for item in self.observations
        }
        if training_ids.intersection(validation_ids):
            raise ResearchCalibrationOosValidationValidationError(
                "fit and OOS calibration validation analysis ids must be disjoint"
            )
        if any(item.source.target != self.mapping_fit.target for item in self.observations):
            raise ResearchCalibrationOosValidationValidationError(
                "OOS calibration target must match the fitted mapping target"
            )
        if any(
            item.source.analysis.kind != self.mapping_fit.specialist_kind
            for item in self.observations
        ):
            raise ResearchCalibrationOosValidationValidationError(
                "OOS calibration specialist kind must match the fitted mapping"
            )
        if any(
            item.run.run_id != plan.run.run_id
            or item.run.input_fingerprint != plan.run.input_fingerprint
            for item in self.observations
        ):
            raise ResearchCalibrationOosValidationValidationError(
                "every OOS calibration observation must bind the frozen research run"
            )
        window = fold.out_of_sample
        for item in self.observations:
            if not window.opened_at <= item.score_observed_at < window.closed_at:
                raise ResearchCalibrationOosValidationValidationError(
                    "every OOS calibration score must fall inside the OOS window"
                )
            if not window.opened_at <= item.outcome_observed_at < window.closed_at:
                raise ResearchCalibrationOosValidationValidationError(
                    "every OOS calibration outcome must fall inside the OOS window"
                )
            if item.recorded_at < self.mapping_fit.fitted_at:
                raise ResearchCalibrationOosValidationValidationError(
                    "OOS calibration evidence record cannot predate mapping fit"
                )

    @property
    def validation_window(self) -> ResearchEvaluationWindow:
        return next(
            item.out_of_sample
            for item in self.mapping_fit.training_set.evaluation_freeze.plan.folds
            if item.fold_number == self.fold_number
        )

    @property
    def target(self) -> ResearchCalibrationTarget:
        return self.mapping_fit.target

    @property
    def specialist_kind(self) -> SpecialistKind:
        return self.mapping_fit.specialist_kind

    @property
    def run_input_fingerprint(self) -> ResearchRunInputFingerprint:
        return self.mapping_fit.run_input_fingerprint

    @property
    def software_revision(self) -> ResearchSoftwareRevision:
        return self.mapping_fit.software_revision

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.mapping_fit.logical_values(),
            self.fold_number,
            self.validation_window.logical_values(),
            tuple(item.logical_values() for item in self.observations),
        )


@dataclass(frozen=True, slots=True)
class ResearchCalibrationOosValidationBin:
    index: int
    lower_bound: Decimal
    upper_bound: Decimal
    sample_size: int
    mean_estimated_probability: Decimal
    empirical_event_rate: Decimal
    absolute_gap: Decimal

    def __post_init__(self) -> None:
        if type(self.index) is not int or self.index < 0:
            raise ResearchCalibrationOosValidationValidationError(
                "OOS calibration bin index must be a non-negative integer"
            )
        if type(self.sample_size) is not int or self.sample_size <= 0:
            raise ResearchCalibrationOosValidationValidationError(
                "OOS calibration bin sample_size must be a positive integer"
            )
        for field_name, value in (
            ("lower_bound", self.lower_bound),
            ("upper_bound", self.upper_bound),
            ("mean_estimated_probability", self.mean_estimated_probability),
            ("empirical_event_rate", self.empirical_event_rate),
            ("absolute_gap", self.absolute_gap),
        ):
            _validate_probability(value, field_name=f"OOS calibration bin {field_name}")
        if not self.lower_bound < self.upper_bound:
            raise ResearchCalibrationOosValidationValidationError(
                "OOS calibration bin lower_bound must precede upper_bound"
            )
        if self.absolute_gap != abs(
            self.mean_estimated_probability - self.empirical_event_rate
        ):
            raise ResearchCalibrationOosValidationValidationError(
                "OOS calibration bin absolute_gap must match probability/event-rate gap"
            )

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.index,
            format(self.lower_bound, "f"),
            format(self.upper_bound, "f"),
            self.sample_size,
            format(self.mean_estimated_probability, "f"),
            format(self.empirical_event_rate, "f"),
            format(self.absolute_gap, "f"),
        )


def _derive_metrics(
    validation_set: ResearchCalibrationOosValidationSet,
    policy: ResearchCalibrationOosValidationPolicy,
) -> tuple[
    Decimal,
    Decimal,
    Decimal,
    tuple[ResearchCalibrationOosValidationBin, ...],
    Decimal,
]:
    if not isinstance(validation_set, ResearchCalibrationOosValidationSet):
        raise ResearchCalibrationOosValidationValidationError(
            "OOS calibration metrics require ResearchCalibrationOosValidationSet"
        )
    if not isinstance(policy, ResearchCalibrationOosValidationPolicy):
        raise ResearchCalibrationOosValidationValidationError(
            "OOS calibration metrics require ResearchCalibrationOosValidationPolicy"
        )
    estimates = tuple(
        validation_set.mapping_fit.estimate_probability(item.source.confidence_score)
        for item in validation_set.observations
    )
    outcomes = tuple(
        _ONE if item.source.event_occurred else _ZERO
        for item in validation_set.observations
    )
    mean_estimate = _mean(estimates)
    event_rate = _mean(outcomes)
    with localcontext(_DECIMAL128):
        brier = _mean(
            tuple(
                (estimate - outcome) ** 2
                for estimate, outcome in zip(estimates, outcomes, strict=True)
            )
        )
        width = _ONE / Decimal(policy.bin_count)

    buckets: list[list[tuple[Decimal, Decimal]]] = [
        [] for _ in range(policy.bin_count)
    ]
    for estimate, outcome in zip(estimates, outcomes, strict=True):
        index = policy.bin_count - 1 if estimate == _ONE else int(
            estimate * policy.bin_count
        )
        buckets[index].append((estimate, outcome))

    bins: list[ResearchCalibrationOosValidationBin] = []
    for index, bucket in enumerate(buckets):
        if not bucket:
            continue
        bucket_estimates = tuple(item[0] for item in bucket)
        bucket_outcomes = tuple(item[1] for item in bucket)
        with localcontext(_DECIMAL128):
            lower = Decimal(index) * width
            upper = Decimal(index + 1) * width
            bucket_mean = _mean(bucket_estimates)
            bucket_rate = _mean(bucket_outcomes)
            gap = abs(bucket_mean - bucket_rate)
        bins.append(
            ResearchCalibrationOosValidationBin(
                index=index,
                lower_bound=lower,
                upper_bound=upper,
                sample_size=len(bucket),
                mean_estimated_probability=bucket_mean,
                empirical_event_rate=bucket_rate,
                absolute_gap=gap,
            )
        )
    with localcontext(_DECIMAL128):
        ece = sum(
            (
                Decimal(item.sample_size)
                / Decimal(len(validation_set.observations))
                * item.absolute_gap
                for item in bins
            ),
            _ZERO,
        )
    return mean_estimate, event_rate, brier, tuple(bins), ece


@dataclass(frozen=True, slots=True)
class ResearchCalibrationOosValidationFingerprint:
    value: str

    def __post_init__(self) -> None:
        if not isinstance(self.value, str) or fullmatch(r"[0-9a-f]{64}", self.value) is None:
            raise ResearchCalibrationOosValidationValidationError(
                "OOS calibration validation fingerprint must be 64 lowercase hex characters"
            )

    def logical_values(self) -> tuple[str, ...]:
        return (self.value,)


def compute_research_calibration_oos_validation_fingerprint(
    *,
    validation_set: ResearchCalibrationOosValidationSet,
    policy: ResearchCalibrationOosValidationPolicy,
    metrics: tuple[
        Decimal,
        Decimal,
        Decimal,
        tuple[ResearchCalibrationOosValidationBin, ...],
        Decimal,
    ],
) -> ResearchCalibrationOosValidationFingerprint:
    """Hash exact mapping, OOS evidence and diagnostics excluding admin id/time."""

    expected = _derive_metrics(validation_set, policy)
    if metrics != expected:
        raise ResearchCalibrationOosValidationValidationError(
            "OOS calibration fingerprint metrics must match deterministic derivation"
        )
    canonical = {
        "validation_set": validation_set.logical_values(),
        "policy": policy.logical_values(),
        "metrics": (
            format(metrics[0], "f"),
            format(metrics[1], "f"),
            format(metrics[2], "f"),
            tuple(item.logical_values() for item in metrics[3]),
            format(metrics[4], "f"),
        ),
    }
    encoded = json.dumps(
        canonical,
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    return ResearchCalibrationOosValidationFingerprint(sha256(encoded).hexdigest())


@dataclass(frozen=True, slots=True)
class ResearchCalibrationOosValidationEvidence:
    """OOS diagnostics for one deterministic confidence-to-probability mapping.

    This evidence proves that a specific fitted mapping was applied to a distinct
    set of observations structurally located in its frozen fold's OOS window and
    reports deterministic Brier score, reliability bins and ECE on the resulting
    estimated probabilities.

    It does not certify a `CalibratedProbability`, establish minimum sample
    adequacy, quantify uncertainty, prove analyst blindness or absence of prior
    outcome access, prove future predictive validity, authorize strategy/risk,
    authorize production/capital, or create any execution authority.
    """

    validation_id: ResearchCalibrationOosValidationId
    validation_set: ResearchCalibrationOosValidationSet
    policy: ResearchCalibrationOosValidationPolicy
    sample_size: int
    mean_estimated_probability: Decimal
    empirical_event_rate: Decimal
    brier_score: Decimal
    bins: tuple[ResearchCalibrationOosValidationBin, ...]
    expected_calibration_error: Decimal
    validated_at: datetime
    fingerprint: ResearchCalibrationOosValidationFingerprint

    def __post_init__(self) -> None:
        if not isinstance(self.validation_id, ResearchCalibrationOosValidationId):
            raise ResearchCalibrationOosValidationValidationError(
                "validation_id must be ResearchCalibrationOosValidationId"
            )
        if not isinstance(self.validation_set, ResearchCalibrationOosValidationSet):
            raise ResearchCalibrationOosValidationValidationError(
                "validation_set must be ResearchCalibrationOosValidationSet"
            )
        if not isinstance(self.policy, ResearchCalibrationOosValidationPolicy):
            raise ResearchCalibrationOosValidationValidationError(
                "policy must be ResearchCalibrationOosValidationPolicy"
            )
        metrics = _derive_metrics(self.validation_set, self.policy)
        actual = (
            self.mean_estimated_probability,
            self.empirical_event_rate,
            self.brier_score,
            self.bins,
            self.expected_calibration_error,
        )
        if self.sample_size != len(self.validation_set.observations) or actual != metrics:
            raise ResearchCalibrationOosValidationValidationError(
                "OOS calibration metrics must match exact validation evidence"
            )
        _validate_timestamp(self.validated_at, field_name="validated_at")
        if self.validated_at < max(
            item.recorded_at for item in self.validation_set.observations
        ):
            raise ResearchCalibrationOosValidationValidationError(
                "OOS calibration validation cannot predate source evidence records"
            )
        if not isinstance(
            self.fingerprint,
            ResearchCalibrationOosValidationFingerprint,
        ):
            raise ResearchCalibrationOosValidationValidationError(
                "fingerprint must be ResearchCalibrationOosValidationFingerprint"
            )
        expected_fingerprint = compute_research_calibration_oos_validation_fingerprint(
            validation_set=self.validation_set,
            policy=self.policy,
            metrics=metrics,
        )
        if self.fingerprint != expected_fingerprint:
            raise ResearchCalibrationOosValidationValidationError(
                "OOS calibration fingerprint must match exact evidence and metrics"
            )

    @property
    def target(self) -> ResearchCalibrationTarget:
        return self.validation_set.target

    @property
    def specialist_kind(self) -> SpecialistKind:
        return self.validation_set.specialist_kind

    @property
    def run_input_fingerprint(self) -> ResearchRunInputFingerprint:
        return self.validation_set.run_input_fingerprint

    @property
    def software_revision(self) -> ResearchSoftwareRevision:
        return self.validation_set.software_revision

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.validation_id.logical_values(),
            self.validation_set.logical_values(),
            self.policy.logical_values(),
            self.sample_size,
            format(self.mean_estimated_probability, "f"),
            format(self.empirical_event_rate, "f"),
            format(self.brier_score, "f"),
            tuple(item.logical_values() for item in self.bins),
            format(self.expected_calibration_error, "f"),
            self.validated_at.isoformat(),
            self.fingerprint.logical_values(),
        )


def build_research_calibration_oos_validation_evidence(
    *,
    validation_id: ResearchCalibrationOosValidationId,
    validation_set: ResearchCalibrationOosValidationSet,
    policy: ResearchCalibrationOosValidationPolicy,
    validated_at: datetime,
) -> Result[
    ResearchCalibrationOosValidationEvidence,
    ResearchCalibrationOosValidationError,
]:
    """Build OOS mapping diagnostics without certifying calibrated probability."""

    try:
        metrics = _derive_metrics(validation_set, policy)
        fingerprint = compute_research_calibration_oos_validation_fingerprint(
            validation_set=validation_set,
            policy=policy,
            metrics=metrics,
        )
        return Success(
            ResearchCalibrationOosValidationEvidence(
                validation_id=validation_id,
                validation_set=validation_set,
                policy=policy,
                sample_size=len(validation_set.observations),
                mean_estimated_probability=metrics[0],
                empirical_event_rate=metrics[1],
                brier_score=metrics[2],
                bins=metrics[3],
                expected_calibration_error=metrics[4],
                validated_at=validated_at,
                fingerprint=fingerprint,
            )
        )
    except ResearchCalibrationOosValidationError as error:
        return Failure(error)

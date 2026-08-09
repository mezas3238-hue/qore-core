from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from decimal import ROUND_HALF_EVEN, Context, Decimal, localcontext
from enum import StrEnum
from hashlib import sha256
from re import fullmatch
from uuid import UUID

from qore.infrastructure.research_confidence_calibration import (
    ResearchCalibrationTarget,
    ResearchConfidenceCalibrationSnapshot,
    ResearchConfidenceOutcomeObservation,
)
from qore.infrastructure.research_evaluation_freeze import ResearchEvaluationFreezeEvidence
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


class ResearchCalibrationMappingError(InfrastructureError):
    """Base error for research-only confidence calibration mapping evidence."""

    __slots__ = ()


class ResearchCalibrationMappingValidationError(ResearchCalibrationMappingError):
    """Violation of a calibration mapping fit or provenance invariant."""

    __slots__ = ()


def _validate_timestamp(value: datetime, *, field_name: str) -> None:
    if not isinstance(value, datetime):
        raise ResearchCalibrationMappingValidationError(f"{field_name} must be datetime")
    if value.tzinfo is None or value.utcoffset() is None:
        raise ResearchCalibrationMappingValidationError(
            f"{field_name} must be timezone-aware"
        )


def _validate_probability_decimal(value: Decimal, *, field_name: str) -> None:
    if not isinstance(value, Decimal) or not value.is_finite():
        raise ResearchCalibrationMappingValidationError(
            f"{field_name} must be a finite Decimal"
        )
    if not _ZERO <= value <= _ONE:
        raise ResearchCalibrationMappingValidationError(
            f"{field_name} must remain inside [0, 1]"
        )


def _mean(total: Decimal, count: int) -> Decimal:
    with localcontext(_DECIMAL128):
        return total / Decimal(count)


@dataclass(frozen=True, slots=True)
class ResearchCalibrationMappingId:
    value: UUID

    def __post_init__(self) -> None:
        if not isinstance(self.value, UUID):
            raise ResearchCalibrationMappingValidationError(
                "calibration mapping id must be UUID"
            )

    def logical_values(self) -> tuple[str, ...]:
        return (str(self.value),)


@dataclass(frozen=True, slots=True)
class ResearchCalibrationMappingVersion:
    value: str

    def __post_init__(self) -> None:
        if not isinstance(self.value, str) or fullmatch(
            r"[A-Za-z0-9][A-Za-z0-9._-]*",
            self.value,
        ) is None:
            raise ResearchCalibrationMappingValidationError(
                "calibration mapping version must use canonical token syntax"
            )

    def logical_values(self) -> tuple[str, ...]:
        return (self.value,)


class ResearchCalibrationMappingMethodology(StrEnum):
    """Supported research mapping methodologies."""

    ISOTONIC_PAVA = "isotonic-pava"


class ResearchCalibrationMappingApplicationPolicy(StrEnum):
    """How a fitted isotonic step function is applied between observed scores."""

    RIGHT_CONTINUOUS_STEP = "right-continuous-step"


@dataclass(frozen=True, slots=True)
class ResearchCalibrationMappingFitPolicy:
    """Explicit versioned fitting policy; PAVA v1 has no tunable hyperparameters."""

    methodology: ResearchCalibrationMappingMethodology
    version: ResearchCalibrationMappingVersion
    application_policy: ResearchCalibrationMappingApplicationPolicy
    hyperparameters: tuple[tuple[str, str], ...]

    def __post_init__(self) -> None:
        if not isinstance(self.methodology, ResearchCalibrationMappingMethodology):
            raise ResearchCalibrationMappingValidationError(
                "mapping methodology must be ResearchCalibrationMappingMethodology"
            )
        if not isinstance(self.version, ResearchCalibrationMappingVersion):
            raise ResearchCalibrationMappingValidationError(
                "mapping version must be ResearchCalibrationMappingVersion"
            )
        if not isinstance(
            self.application_policy,
            ResearchCalibrationMappingApplicationPolicy,
        ):
            raise ResearchCalibrationMappingValidationError(
                "mapping application policy must be ResearchCalibrationMappingApplicationPolicy"
            )
        if not isinstance(self.hyperparameters, tuple) or any(
            not isinstance(item, tuple)
            or len(item) != 2
            or not isinstance(item[0], str)
            or not item[0]
            or not isinstance(item[1], str)
            or not item[1]
            for item in self.hyperparameters
        ):
            raise ResearchCalibrationMappingValidationError(
                "mapping hyperparameters must be immutable non-empty string pairs"
            )
        if tuple(sorted(self.hyperparameters)) != self.hyperparameters:
            raise ResearchCalibrationMappingValidationError(
                "mapping hyperparameters must use canonical key/value order"
            )
        names = tuple(name for name, _ in self.hyperparameters)
        if len(set(names)) != len(names):
            raise ResearchCalibrationMappingValidationError(
                "mapping hyperparameter names must be unique"
            )
        if self.methodology is ResearchCalibrationMappingMethodology.ISOTONIC_PAVA:
            if self.version.value != "1":
                raise ResearchCalibrationMappingValidationError(
                    "isotonic PAVA implementation currently supports mapping version 1 only"
                )
            if self.hyperparameters:
                raise ResearchCalibrationMappingValidationError(
                    "isotonic PAVA v1 does not accept tunable hyperparameters"
                )
            if (
                self.application_policy
                is not ResearchCalibrationMappingApplicationPolicy.RIGHT_CONTINUOUS_STEP
            ):
                raise ResearchCalibrationMappingValidationError(
                    "isotonic PAVA v1 requires right-continuous step application"
                )

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.methodology.value,
            self.version.logical_values(),
            self.application_policy.value,
            self.hyperparameters,
        )


@dataclass(frozen=True, slots=True)
class ResearchCalibrationTrainingObservation:
    """Research provenance for one score/outcome pair used to fit a mapping.

    `score_observed_at` and `outcome_observed_at` are explicit simulated research
    times. They are intentionally separate from `SpecialistAnalysis.timestamp`,
    whose semantic time axis is not assumed here.
    """

    source: ResearchConfidenceOutcomeObservation
    run: ResearchRunEvidence
    score_observed_at: datetime
    outcome_observed_at: datetime

    def __post_init__(self) -> None:
        if not isinstance(self.source, ResearchConfidenceOutcomeObservation):
            raise ResearchCalibrationMappingValidationError(
                "training source must be ResearchConfidenceOutcomeObservation"
            )
        if not isinstance(self.run, ResearchRunEvidence):
            raise ResearchCalibrationMappingValidationError(
                "training observation run must be ResearchRunEvidence"
            )
        _validate_timestamp(self.score_observed_at, field_name="score_observed_at")
        _validate_timestamp(self.outcome_observed_at, field_name="outcome_observed_at")
        if self.outcome_observed_at < self.score_observed_at:
            raise ResearchCalibrationMappingValidationError(
                "training outcome cannot precede its score observation"
            )

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.source.logical_values(),
            self.run.input_fingerprint.logical_values(),
            self.score_observed_at.isoformat(),
            self.outcome_observed_at.isoformat(),
        )


@dataclass(frozen=True, slots=True)
class ResearchCalibrationTrainingSet:
    """Exact in-sample evidence bound to one frozen research evaluation fold.

    The contract proves exact snapshot coverage, one research run, and declared
    score/outcome times inside one in-sample window. It does not prove that an
    analyst lacked prior access to labels, that the declared provenance is an
    external attestation, or that a fitted mapping will generalize out of sample.
    """

    snapshot: ResearchConfidenceCalibrationSnapshot
    evaluation_freeze: ResearchEvaluationFreezeEvidence
    fold_number: int
    observations: tuple[ResearchCalibrationTrainingObservation, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.snapshot, ResearchConfidenceCalibrationSnapshot):
            raise ResearchCalibrationMappingValidationError(
                "training set snapshot must be ResearchConfidenceCalibrationSnapshot"
            )
        if not isinstance(self.evaluation_freeze, ResearchEvaluationFreezeEvidence):
            raise ResearchCalibrationMappingValidationError(
                "training set requires ResearchEvaluationFreezeEvidence"
            )
        if type(self.fold_number) is not int or self.fold_number <= 0:
            raise ResearchCalibrationMappingValidationError(
                "training fold_number must be a positive integer"
            )
        if not isinstance(self.observations, tuple) or any(
            not isinstance(item, ResearchCalibrationTrainingObservation)
            for item in self.observations
        ):
            raise ResearchCalibrationMappingValidationError(
                "training observations must be an immutable research provenance tuple"
            )
        expected_sources = self.snapshot.observations
        actual_sources = tuple(item.source for item in self.observations)
        if actual_sources != expected_sources:
            raise ResearchCalibrationMappingValidationError(
                "training observations must cover the calibration snapshot exactly "
                "in canonical order"
            )
        if len(self.observations) != self.snapshot.sample_size:
            raise ResearchCalibrationMappingValidationError(
                "training observation count must match calibration snapshot sample_size"
            )
        plan = self.evaluation_freeze.plan
        fold = next(
            (item for item in plan.folds if item.fold_number == self.fold_number),
            None,
        )
        if fold is None:
            raise ResearchCalibrationMappingValidationError(
                "training fold_number must exist in the frozen temporal evaluation plan"
            )
        if any(
            item.run.run_id != plan.run.run_id
            or item.run.input_fingerprint != plan.run.input_fingerprint
            for item in self.observations
        ):
            raise ResearchCalibrationMappingValidationError(
                "every calibration training observation must bind the frozen research run"
            )
        window = fold.in_sample
        for item in self.observations:
            if not window.opened_at <= item.score_observed_at < window.closed_at:
                raise ResearchCalibrationMappingValidationError(
                    "every calibration score observation must fall inside the in-sample window"
                )
            if not window.opened_at <= item.outcome_observed_at < window.closed_at:
                raise ResearchCalibrationMappingValidationError(
                    "every calibration outcome must be observed inside the in-sample window"
                )

    @property
    def training_window(self) -> ResearchEvaluationWindow:
        return next(
            item.in_sample
            for item in self.evaluation_freeze.plan.folds
            if item.fold_number == self.fold_number
        )

    @property
    def target(self) -> ResearchCalibrationTarget:
        return self.snapshot.target

    @property
    def specialist_kind(self) -> SpecialistKind:
        return self.snapshot.specialist_kind

    @property
    def run_input_fingerprint(self) -> ResearchRunInputFingerprint:
        return self.evaluation_freeze.plan.run.input_fingerprint

    @property
    def software_revision(self) -> ResearchSoftwareRevision:
        return self.evaluation_freeze.plan.run.software_revision

    def logical_values(self) -> tuple[object, ...]:
        freeze = self.evaluation_freeze
        plan = freeze.plan
        return (
            self.snapshot.logical_values(),
            freeze.evidence_id.logical_values(),
            freeze.fingerprint.logical_values(),
            plan.plan_id.logical_values(),
            self.fold_number,
            self.training_window.logical_values(),
            self.run_input_fingerprint.logical_values(),
            self.software_revision.logical_values(),
            tuple(item.logical_values() for item in self.observations),
        )


@dataclass(frozen=True, slots=True)
class ResearchCalibrationMappingBlock:
    lower_score: Decimal
    upper_score: Decimal
    estimated_probability: Decimal
    sample_size: int

    def __post_init__(self) -> None:
        _validate_probability_decimal(self.lower_score, field_name="mapping lower_score")
        _validate_probability_decimal(self.upper_score, field_name="mapping upper_score")
        _validate_probability_decimal(
            self.estimated_probability,
            field_name="mapping estimated_probability",
        )
        if self.upper_score < self.lower_score:
            raise ResearchCalibrationMappingValidationError(
                "mapping block upper_score cannot precede lower_score"
            )
        if type(self.sample_size) is not int or self.sample_size <= 0:
            raise ResearchCalibrationMappingValidationError(
                "mapping block sample_size must be a positive integer"
            )

    def logical_values(self) -> tuple[object, ...]:
        return (
            format(self.lower_score, "f"),
            format(self.upper_score, "f"),
            format(self.estimated_probability, "f"),
            self.sample_size,
        )


@dataclass(slots=True)
class _MutablePavaBlock:
    lower_score: Decimal
    upper_score: Decimal
    event_total: Decimal
    sample_size: int

    @property
    def probability(self) -> Decimal:
        return _mean(self.event_total, self.sample_size)


def _fit_isotonic_pava(
    observations: tuple[ResearchCalibrationTrainingObservation, ...],
) -> tuple[ResearchCalibrationMappingBlock, ...]:
    grouped: dict[Decimal, tuple[Decimal, int]] = {}
    for item in observations:
        score = item.source.confidence_score
        event = _ONE if item.source.event_occurred else _ZERO
        current_total, current_count = grouped.get(score, (_ZERO, 0))
        grouped[score] = (current_total + event, current_count + 1)

    blocks: list[_MutablePavaBlock] = []
    for score in sorted(grouped):
        event_total, sample_size = grouped[score]
        blocks.append(
            _MutablePavaBlock(
                lower_score=score,
                upper_score=score,
                event_total=event_total,
                sample_size=sample_size,
            )
        )
        while len(blocks) >= 2 and blocks[-2].probability > blocks[-1].probability:
            right = blocks.pop()
            left = blocks.pop()
            blocks.append(
                _MutablePavaBlock(
                    lower_score=left.lower_score,
                    upper_score=right.upper_score,
                    event_total=left.event_total + right.event_total,
                    sample_size=left.sample_size + right.sample_size,
                )
            )

    return tuple(
        ResearchCalibrationMappingBlock(
            lower_score=item.lower_score,
            upper_score=item.upper_score,
            estimated_probability=item.probability,
            sample_size=item.sample_size,
        )
        for item in blocks
    )


def _derive_blocks(
    training_set: ResearchCalibrationTrainingSet,
    policy: ResearchCalibrationMappingFitPolicy,
) -> tuple[ResearchCalibrationMappingBlock, ...]:
    if not isinstance(training_set, ResearchCalibrationTrainingSet):
        raise ResearchCalibrationMappingValidationError(
            "mapping fit requires ResearchCalibrationTrainingSet"
        )
    if not isinstance(policy, ResearchCalibrationMappingFitPolicy):
        raise ResearchCalibrationMappingValidationError(
            "mapping fit requires ResearchCalibrationMappingFitPolicy"
        )
    if policy.methodology is ResearchCalibrationMappingMethodology.ISOTONIC_PAVA:
        return _fit_isotonic_pava(training_set.observations)
    raise ResearchCalibrationMappingValidationError("unsupported calibration mapping methodology")


@dataclass(frozen=True, slots=True)
class ResearchCalibrationMappingFingerprint:
    value: str

    def __post_init__(self) -> None:
        if not isinstance(self.value, str) or fullmatch(r"[0-9a-f]{64}", self.value) is None:
            raise ResearchCalibrationMappingValidationError(
                "calibration mapping fingerprint must be 64 lowercase hex characters"
            )

    def logical_values(self) -> tuple[str, ...]:
        return (self.value,)


def compute_research_calibration_mapping_fingerprint(
    *,
    training_set: ResearchCalibrationTrainingSet,
    policy: ResearchCalibrationMappingFitPolicy,
    blocks: tuple[ResearchCalibrationMappingBlock, ...],
) -> ResearchCalibrationMappingFingerprint:
    """Hash deterministic fit inputs and outputs, excluding administrative id/time."""

    if not isinstance(training_set, ResearchCalibrationTrainingSet):
        raise ResearchCalibrationMappingValidationError(
            "mapping fingerprint requires ResearchCalibrationTrainingSet"
        )
    if not isinstance(policy, ResearchCalibrationMappingFitPolicy):
        raise ResearchCalibrationMappingValidationError(
            "mapping fingerprint requires ResearchCalibrationMappingFitPolicy"
        )
    expected_blocks = _derive_blocks(training_set, policy)
    if blocks != expected_blocks:
        raise ResearchCalibrationMappingValidationError(
            "mapping fingerprint blocks must match deterministic fit result"
        )
    canonical = {
        "training_set": training_set.logical_values(),
        "policy": policy.logical_values(),
        "blocks": tuple(item.logical_values() for item in blocks),
    }
    encoded = json.dumps(
        canonical,
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    return ResearchCalibrationMappingFingerprint(sha256(encoded).hexdigest())


@dataclass(frozen=True, slots=True)
class ResearchConfidenceCalibrationMappingFit:
    """Deterministic research-only fit from confidence score to probability estimate.

    This proves the exact training evidence, frozen in-sample fold, methodology,
    version, hyperparameters, software revision, deterministic fitted blocks, and
    content fingerprint used to produce an estimated probability transformation.

    It does not certify calibration, create `CalibratedProbability`, prove OOS
    validity, predictive validity, sample adequacy, analyst blindness, production
    fitness, execution authority, risk authority, or capital authorization.
    """

    mapping_id: ResearchCalibrationMappingId
    training_set: ResearchCalibrationTrainingSet
    policy: ResearchCalibrationMappingFitPolicy
    blocks: tuple[ResearchCalibrationMappingBlock, ...]
    fitted_at: datetime
    fingerprint: ResearchCalibrationMappingFingerprint

    def __post_init__(self) -> None:
        if not isinstance(self.mapping_id, ResearchCalibrationMappingId):
            raise ResearchCalibrationMappingValidationError(
                "mapping_id must be ResearchCalibrationMappingId"
            )
        if not isinstance(self.training_set, ResearchCalibrationTrainingSet):
            raise ResearchCalibrationMappingValidationError(
                "mapping fit requires ResearchCalibrationTrainingSet"
            )
        if not isinstance(self.policy, ResearchCalibrationMappingFitPolicy):
            raise ResearchCalibrationMappingValidationError(
                "mapping fit requires ResearchCalibrationMappingFitPolicy"
            )
        expected_blocks = _derive_blocks(self.training_set, self.policy)
        if self.blocks != expected_blocks:
            raise ResearchCalibrationMappingValidationError(
                "mapping blocks must match deterministic fitting evidence"
            )
        _validate_timestamp(self.fitted_at, field_name="mapping fitted_at")
        if self.fitted_at < self.training_set.evaluation_freeze.established_at:
            raise ResearchCalibrationMappingValidationError(
                "mapping fit cannot predate evaluation freeze establishment"
            )
        if not isinstance(self.fingerprint, ResearchCalibrationMappingFingerprint):
            raise ResearchCalibrationMappingValidationError(
                "fingerprint must be ResearchCalibrationMappingFingerprint"
            )
        expected_fingerprint = compute_research_calibration_mapping_fingerprint(
            training_set=self.training_set,
            policy=self.policy,
            blocks=self.blocks,
        )
        if self.fingerprint != expected_fingerprint:
            raise ResearchCalibrationMappingValidationError(
                "mapping fingerprint must match exact fit inputs and outputs"
            )

    @property
    def target(self) -> ResearchCalibrationTarget:
        return self.training_set.target

    @property
    def specialist_kind(self) -> SpecialistKind:
        return self.training_set.specialist_kind

    @property
    def run_input_fingerprint(self) -> ResearchRunInputFingerprint:
        return self.training_set.run_input_fingerprint

    @property
    def software_revision(self) -> ResearchSoftwareRevision:
        return self.training_set.software_revision

    def estimate_probability(self, confidence_score: Decimal) -> Decimal:
        """Apply the right-continuous fitted step as an uncertified estimate.

        Between observed block starts, the preceding fitted level is carried forward.
        Scores inside the valid confidence domain but outside the observed score range
        use the nearest fitted edge level. No input is normalized or clipped.
        """

        _validate_probability_decimal(
            confidence_score,
            field_name="mapping confidence_score",
        )
        selected = self.blocks[0]
        for block in self.blocks:
            if confidence_score < block.lower_score:
                break
            selected = block
        return selected.estimated_probability

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.mapping_id.logical_values(),
            self.training_set.logical_values(),
            self.policy.logical_values(),
            tuple(item.logical_values() for item in self.blocks),
            self.fitted_at.isoformat(),
            self.fingerprint.logical_values(),
        )


def fit_research_confidence_calibration_mapping(
    *,
    mapping_id: ResearchCalibrationMappingId,
    training_set: ResearchCalibrationTrainingSet,
    policy: ResearchCalibrationMappingFitPolicy,
    fitted_at: datetime,
) -> Result[ResearchConfidenceCalibrationMappingFit, ResearchCalibrationMappingError]:
    """Fit research mapping evidence without certifying probability calibration."""

    try:
        blocks = _derive_blocks(training_set, policy)
        fingerprint = compute_research_calibration_mapping_fingerprint(
            training_set=training_set,
            policy=policy,
            blocks=blocks,
        )
        return Success(
            ResearchConfidenceCalibrationMappingFit(
                mapping_id=mapping_id,
                training_set=training_set,
                policy=policy,
                blocks=blocks,
                fitted_at=fitted_at,
                fingerprint=fingerprint,
            )
        )
    except ResearchCalibrationMappingError as error:
        return Failure(error)

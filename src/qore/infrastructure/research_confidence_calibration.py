from __future__ import annotations

from dataclasses import dataclass
from decimal import ROUND_HALF_EVEN, Context, Decimal, localcontext
from re import fullmatch

from qore.kernel.errors import InfrastructureError
from qore.kernel.result import Failure, Result, Success
from qore.specialist.analysis import (
    SpecialistAnalysis,
    SpecialistAnalysisStatus,
    SpecialistKind,
)

_DECIMAL128 = Context(prec=34, rounding=ROUND_HALF_EVEN)


class ResearchConfidenceCalibrationError(InfrastructureError):
    """Base error for research confidence-calibration diagnostics."""

    __slots__ = ()


class ResearchConfidenceCalibrationValidationError(ResearchConfidenceCalibrationError):
    """Violation of a confidence-calibration diagnostic invariant."""

    __slots__ = ()


@dataclass(frozen=True, slots=True)
class ResearchCalibrationTarget:
    """Stable binary outcome semantics used only for calibration diagnostics."""

    value: str

    def __post_init__(self) -> None:
        if not isinstance(self.value, str) or fullmatch(
            r"[a-z][a-z0-9.-]*",
            self.value,
        ) is None:
            raise ResearchConfidenceCalibrationValidationError(
                "calibration target must use lowercase letters, digits, dots, or hyphens"
            )

    def logical_values(self) -> tuple[str, ...]:
        return (self.value,)


@dataclass(frozen=True, slots=True)
class ResearchConfidenceOutcomeObservation:
    """One completed specialist confidence score paired with a binary outcome.

    The specialist confidence remains a score. Pairing it with an outcome permits
    diagnostics of the *candidate interpretation* of that score as probability;
    this observation does not declare that the score is a calibrated probability.
    """

    analysis: SpecialistAnalysis
    target: ResearchCalibrationTarget
    event_occurred: bool

    def __post_init__(self) -> None:
        if not isinstance(self.analysis, SpecialistAnalysis):
            raise ResearchConfidenceCalibrationValidationError(
                "calibration observation requires SpecialistAnalysis"
            )
        if self.analysis.status is not SpecialistAnalysisStatus.COMPLETED:
            raise ResearchConfidenceCalibrationValidationError(
                "calibration observation requires a completed specialist analysis"
            )
        if self.analysis.confidence is None:
            raise ResearchConfidenceCalibrationValidationError(
                "calibration observation requires specialist confidence"
            )
        if not isinstance(self.target, ResearchCalibrationTarget):
            raise ResearchConfidenceCalibrationValidationError(
                "calibration observation target must be ResearchCalibrationTarget"
            )
        if type(self.event_occurred) is not bool:
            raise ResearchConfidenceCalibrationValidationError(
                "calibration observation event_occurred must be bool"
            )

    @property
    def confidence_score(self) -> Decimal:
        confidence = self.analysis.confidence
        if confidence is None:  # pragma: no cover - guarded by __post_init__
            raise ResearchConfidenceCalibrationValidationError(
                "completed calibration observation lost confidence"
            )
        return Decimal(str(confidence.value))

    def logical_values(self) -> tuple[object, ...]:
        return (
            str(self.analysis.analysis_id.value),
            self.analysis.timestamp.isoformat(),
            self.analysis.kind.value,
            format(self.confidence_score, "f"),
            self.target.logical_values(),
            self.event_occurred,
        )


@dataclass(frozen=True, slots=True)
class ResearchConfidenceCalibrationPolicy:
    bin_count: int

    def __post_init__(self) -> None:
        if (
            type(self.bin_count) is not int
            or self.bin_count < 2
            or self.bin_count > 100
        ):
            raise ResearchConfidenceCalibrationValidationError(
                "calibration bin_count must be an integer between 2 and 100"
            )

    def logical_values(self) -> tuple[int, ...]:
        return (self.bin_count,)


@dataclass(frozen=True, slots=True)
class ResearchConfidenceCalibrationBin:
    index: int
    lower_bound: Decimal
    upper_bound: Decimal
    sample_size: int
    mean_confidence: Decimal
    empirical_event_rate: Decimal
    absolute_gap: Decimal

    def __post_init__(self) -> None:
        if type(self.index) is not int or self.index < 0:
            raise ResearchConfidenceCalibrationValidationError(
                "calibration bin index must be a non-negative integer"
            )
        if type(self.sample_size) is not int or self.sample_size <= 0:
            raise ResearchConfidenceCalibrationValidationError(
                "calibration bin sample_size must be a positive integer"
            )
        for name, value in (
            ("lower_bound", self.lower_bound),
            ("upper_bound", self.upper_bound),
            ("mean_confidence", self.mean_confidence),
            ("empirical_event_rate", self.empirical_event_rate),
            ("absolute_gap", self.absolute_gap),
        ):
            if not isinstance(value, Decimal) or not value.is_finite():
                raise ResearchConfidenceCalibrationValidationError(
                    f"calibration bin {name} must be a finite Decimal"
                )
        if not Decimal(0) <= self.lower_bound < self.upper_bound <= Decimal(1):
            raise ResearchConfidenceCalibrationValidationError(
                "calibration bin bounds must remain inside [0, 1]"
            )
        if not Decimal(0) <= self.mean_confidence <= Decimal(1):
            raise ResearchConfidenceCalibrationValidationError(
                "calibration bin mean_confidence must remain inside [0, 1]"
            )
        if not Decimal(0) <= self.empirical_event_rate <= Decimal(1):
            raise ResearchConfidenceCalibrationValidationError(
                "calibration bin empirical_event_rate must remain inside [0, 1]"
            )
        if self.absolute_gap != abs(
            self.mean_confidence - self.empirical_event_rate
        ):
            raise ResearchConfidenceCalibrationValidationError(
                "calibration bin absolute_gap must match confidence/event-rate gap"
            )

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.index,
            format(self.lower_bound, "f"),
            format(self.upper_bound, "f"),
            self.sample_size,
            format(self.mean_confidence, "f"),
            format(self.empirical_event_rate, "f"),
            format(self.absolute_gap, "f"),
        )


def _canonical_observations(
    observations: tuple[ResearchConfidenceOutcomeObservation, ...],
) -> tuple[ResearchConfidenceOutcomeObservation, ...]:
    if not isinstance(observations, tuple) or len(observations) < 2:
        raise ResearchConfidenceCalibrationValidationError(
            "confidence calibration requires at least two immutable observations"
        )
    if any(
        not isinstance(item, ResearchConfidenceOutcomeObservation)
        for item in observations
    ):
        raise ResearchConfidenceCalibrationValidationError(
            "confidence calibration observations must use the research observation contract"
        )
    analysis_ids = tuple(item.analysis.analysis_id for item in observations)
    if len(set(analysis_ids)) != len(analysis_ids):
        raise ResearchConfidenceCalibrationValidationError(
            "confidence calibration analysis ids must be unique"
        )
    target = observations[0].target
    if any(item.target != target for item in observations):
        raise ResearchConfidenceCalibrationValidationError(
            "confidence calibration observations must use one target"
        )
    kind = observations[0].analysis.kind
    if any(item.analysis.kind != kind for item in observations):
        raise ResearchConfidenceCalibrationValidationError(
            "confidence calibration observations must use one specialist kind"
        )
    return tuple(
        sorted(
            observations,
            key=lambda item: (
                item.analysis.timestamp,
                str(item.analysis.analysis_id.value),
            ),
        )
    )


def _mean(values: tuple[Decimal, ...]) -> Decimal:
    with localcontext(_DECIMAL128):
        return sum(values, Decimal(0)) / Decimal(len(values))


def _derive_metrics(
    observations: tuple[ResearchConfidenceOutcomeObservation, ...],
    policy: ResearchConfidenceCalibrationPolicy,
) -> tuple[
    Decimal,
    Decimal,
    Decimal,
    tuple[ResearchConfidenceCalibrationBin, ...],
    Decimal,
]:
    ordered = _canonical_observations(observations)
    if not isinstance(policy, ResearchConfidenceCalibrationPolicy):
        raise ResearchConfidenceCalibrationValidationError(
            "confidence calibration requires ResearchConfidenceCalibrationPolicy"
        )
    scores = tuple(item.confidence_score for item in ordered)
    outcomes = tuple(Decimal(1) if item.event_occurred else Decimal(0) for item in ordered)
    mean_confidence = _mean(scores)
    event_rate = _mean(outcomes)
    with localcontext(_DECIMAL128):
        brier_score = _mean(
            tuple((score - outcome) ** 2 for score, outcome in zip(scores, outcomes, strict=True))
        )
        width = Decimal(1) / Decimal(policy.bin_count)

    buckets: list[list[ResearchConfidenceOutcomeObservation]] = [
        [] for _ in range(policy.bin_count)
    ]
    for item in ordered:
        score = item.confidence_score
        index = policy.bin_count - 1 if score == 1 else int(score * policy.bin_count)
        buckets[index].append(item)

    bins: list[ResearchConfidenceCalibrationBin] = []
    for index, bucket in enumerate(buckets):
        if not bucket:
            continue
        bucket_scores = tuple(item.confidence_score for item in bucket)
        bucket_outcomes = tuple(
            Decimal(1) if item.event_occurred else Decimal(0) for item in bucket
        )
        with localcontext(_DECIMAL128):
            lower = Decimal(index) * width
            upper = Decimal(index + 1) * width
            bucket_mean = _mean(bucket_scores)
            bucket_rate = _mean(bucket_outcomes)
            gap = abs(bucket_mean - bucket_rate)
        bins.append(
            ResearchConfidenceCalibrationBin(
                index=index,
                lower_bound=lower,
                upper_bound=upper,
                sample_size=len(bucket),
                mean_confidence=bucket_mean,
                empirical_event_rate=bucket_rate,
                absolute_gap=gap,
            )
        )
    with localcontext(_DECIMAL128):
        ece = sum(
            Decimal(item.sample_size) / Decimal(len(ordered)) * item.absolute_gap
            for item in bins
        )
    return mean_confidence, event_rate, brier_score, tuple(bins), ece


@dataclass(frozen=True, slots=True)
class ResearchConfidenceCalibrationSnapshot:
    """Diagnostic evidence for a candidate probability interpretation of confidence.

    Brier score, reliability bins and expected calibration error quantify how the
    raw specialist confidence score behaves *if* interpreted as probability. The
    snapshot does not create a probability mapping, certify calibration, or alter
    the operational meaning of `SpecialistConfidence`.
    """

    target: ResearchCalibrationTarget
    specialist_kind: SpecialistKind
    policy: ResearchConfidenceCalibrationPolicy
    observations: tuple[ResearchConfidenceOutcomeObservation, ...]
    sample_size: int
    mean_confidence: Decimal
    empirical_event_rate: Decimal
    brier_score: Decimal
    bins: tuple[ResearchConfidenceCalibrationBin, ...]
    expected_calibration_error: Decimal

    def __post_init__(self) -> None:
        if not isinstance(self.target, ResearchCalibrationTarget):
            raise ResearchConfidenceCalibrationValidationError(
                "calibration snapshot target must be ResearchCalibrationTarget"
            )
        if not isinstance(self.specialist_kind, SpecialistKind):
            raise ResearchConfidenceCalibrationValidationError(
                "calibration snapshot specialist_kind must be SpecialistKind"
            )
        if not isinstance(self.policy, ResearchConfidenceCalibrationPolicy):
            raise ResearchConfidenceCalibrationValidationError(
                "calibration snapshot policy must be ResearchConfidenceCalibrationPolicy"
            )
        ordered = _canonical_observations(self.observations)
        if self.observations != ordered:
            raise ResearchConfidenceCalibrationValidationError(
                "calibration observations must use canonical time/id order"
            )
        if self.target != ordered[0].target:
            raise ResearchConfidenceCalibrationValidationError(
                "calibration snapshot target must match observations"
            )
        if self.specialist_kind != ordered[0].analysis.kind:
            raise ResearchConfidenceCalibrationValidationError(
                "calibration snapshot specialist kind must match observations"
            )
        expected = _derive_metrics(ordered, self.policy)
        actual = (
            self.mean_confidence,
            self.empirical_event_rate,
            self.brier_score,
            self.bins,
            self.expected_calibration_error,
        )
        if self.sample_size != len(ordered) or actual != expected:
            raise ResearchConfidenceCalibrationValidationError(
                "confidence calibration metrics must match source observations and policy"
            )

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.target.logical_values(),
            self.specialist_kind.value,
            self.policy.logical_values(),
            tuple(item.logical_values() for item in self.observations),
            self.sample_size,
            format(self.mean_confidence, "f"),
            format(self.empirical_event_rate, "f"),
            format(self.brier_score, "f"),
            tuple(item.logical_values() for item in self.bins),
            format(self.expected_calibration_error, "f"),
        )


def build_research_confidence_calibration_snapshot(
    *,
    policy: ResearchConfidenceCalibrationPolicy,
    observations: tuple[ResearchConfidenceOutcomeObservation, ...],
) -> Result[ResearchConfidenceCalibrationSnapshot, ResearchConfidenceCalibrationError]:
    """Build calibration diagnostics without declaring confidence to be probability."""

    try:
        ordered = _canonical_observations(observations)
        metrics = _derive_metrics(ordered, policy)
        return Success(
            ResearchConfidenceCalibrationSnapshot(
                target=ordered[0].target,
                specialist_kind=ordered[0].analysis.kind,
                policy=policy,
                observations=ordered,
                sample_size=len(ordered),
                mean_confidence=metrics[0],
                empirical_event_rate=metrics[1],
                brier_score=metrics[2],
                bins=metrics[3],
                expected_calibration_error=metrics[4],
            )
        )
    except ResearchConfidenceCalibrationError as error:
        return Failure(error)

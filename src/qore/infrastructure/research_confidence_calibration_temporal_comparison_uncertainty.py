from __future__ import annotations

import json
from dataclasses import dataclass
from decimal import ROUND_CEILING, ROUND_HALF_EVEN, Context, Decimal, localcontext
from hashlib import sha256
from re import fullmatch
from uuid import UUID

from qore.infrastructure.research_confidence_calibration_oos_validation import (
    ResearchCalibrationOosValidationEvidence,
)
from qore.infrastructure.research_confidence_calibration_temporal_comparison import (
    ResearchCalibrationTemporalComparisonEvidence,
)
from qore.infrastructure.research_confidence_calibration_uncertainty import (
    ResearchCalibrationIntervalMethod,
)
from qore.kernel.errors import InfrastructureError
from qore.kernel.result import Failure, Result, Success

_DECIMAL128 = Context(prec=34, rounding=ROUND_HALF_EVEN)
_DOMAIN = b"qore-research-calibration-temporal-comparison-bootstrap-v1"
_ZERO = Decimal(0)
_ONE = Decimal(1)


class ResearchCalibrationTemporalComparisonUncertaintyError(InfrastructureError):
    """Base error for temporal calibration-comparison uncertainty evidence."""

    __slots__ = ()


class ResearchCalibrationTemporalComparisonUncertaintyValidationError(
    ResearchCalibrationTemporalComparisonUncertaintyError
):
    """Violation of a temporal comparison uncertainty invariant."""

    __slots__ = ()


def _validate_unit_decimal(value: Decimal, *, field_name: str) -> None:
    if not isinstance(value, Decimal) or not value.is_finite():
        raise ResearchCalibrationTemporalComparisonUncertaintyValidationError(
            f"{field_name} must be a finite Decimal"
        )
    if not _ZERO <= value <= _ONE:
        raise ResearchCalibrationTemporalComparisonUncertaintyValidationError(
            f"{field_name} must remain inside [0, 1]"
        )


@dataclass(frozen=True, slots=True)
class ResearchCalibrationTemporalComparisonUncertaintyId:
    value: UUID

    def __post_init__(self) -> None:
        if not isinstance(self.value, UUID):
            raise ResearchCalibrationTemporalComparisonUncertaintyValidationError(
                "temporal comparison uncertainty id must be UUID"
            )

    def logical_values(self) -> tuple[str, ...]:
        return (str(self.value),)


@dataclass(frozen=True, slots=True)
class ResearchCalibrationTemporalComparisonUncertaintyPolicy:
    """Explicit resampling policy for two ordered OOS validation windows.

    Circular blocks are drawn independently by deterministic domain-separated
    streams for baseline and comparison windows. Block lengths, resample count,
    seed and confidence level are analyst-supplied modelling choices. The contract
    does not infer optimal block lengths, prove stationarity, prove the two windows
    are statistically independent, or guarantee nominal interval coverage.
    """

    baseline_block_length: int
    comparison_block_length: int
    resample_count: int
    seed: int
    confidence_level: Decimal
    interval_method: ResearchCalibrationIntervalMethod

    def __post_init__(self) -> None:
        for field_name, value in (
            ("baseline_block_length", self.baseline_block_length),
            ("comparison_block_length", self.comparison_block_length),
        ):
            if type(value) is not int or value < 2:
                raise ResearchCalibrationTemporalComparisonUncertaintyValidationError(
                    f"{field_name} must be an integer of at least two"
                )
        if type(self.resample_count) is not int or self.resample_count < 2:
            raise ResearchCalibrationTemporalComparisonUncertaintyValidationError(
                "resample_count must be an integer of at least two"
            )
        if type(self.seed) is not int or self.seed < 0:
            raise ResearchCalibrationTemporalComparisonUncertaintyValidationError(
                "seed must be a non-negative integer"
            )
        if not isinstance(self.confidence_level, Decimal) or not self.confidence_level.is_finite():
            raise ResearchCalibrationTemporalComparisonUncertaintyValidationError(
                "confidence_level must be a finite Decimal"
            )
        if not _ZERO < self.confidence_level < _ONE:
            raise ResearchCalibrationTemporalComparisonUncertaintyValidationError(
                "confidence_level must lie strictly inside (0, 1)"
            )
        if not isinstance(self.interval_method, ResearchCalibrationIntervalMethod):
            raise ResearchCalibrationTemporalComparisonUncertaintyValidationError(
                "interval_method must be explicit ResearchCalibrationIntervalMethod"
            )

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.baseline_block_length,
            self.comparison_block_length,
            self.resample_count,
            self.seed,
            format(self.confidence_level, "f"),
            self.interval_method.value,
        )


@dataclass(frozen=True, slots=True)
class ResearchCalibrationTemporalComparisonInterval:
    confidence_level: Decimal
    method: ResearchCalibrationIntervalMethod
    lower: Decimal
    upper: Decimal

    def __post_init__(self) -> None:
        if not isinstance(self.method, ResearchCalibrationIntervalMethod):
            raise ResearchCalibrationTemporalComparisonUncertaintyValidationError(
                "temporal comparison interval method must be explicit"
            )
        if not isinstance(self.confidence_level, Decimal) or not self.confidence_level.is_finite():
            raise ResearchCalibrationTemporalComparisonUncertaintyValidationError(
                "temporal comparison interval confidence_level must be finite Decimal"
            )
        if not _ZERO < self.confidence_level < _ONE:
            raise ResearchCalibrationTemporalComparisonUncertaintyValidationError(
                "temporal comparison interval confidence_level must lie inside (0, 1)"
            )
        _validate_unit_decimal(self.lower, field_name="temporal interval lower")
        _validate_unit_decimal(self.upper, field_name="temporal interval upper")
        if self.upper < self.lower:
            raise ResearchCalibrationTemporalComparisonUncertaintyValidationError(
                "temporal comparison interval upper cannot precede lower"
            )

    def logical_values(self) -> tuple[str, str, str, str]:
        return (
            format(self.confidence_level, "f"),
            self.method.value,
            format(self.lower, "f"),
            format(self.upper, "f"),
        )


type _Pair = tuple[Decimal, Decimal]
type _Distribution = tuple[Decimal, ...]
type _SourceChanges = tuple[Decimal, Decimal, Decimal, Decimal]
type _Derived = tuple[
    _SourceChanges,
    _Distribution,
    _Distribution,
    _Distribution,
    _Distribution,
]


def _mean(values: tuple[Decimal, ...]) -> Decimal:
    with localcontext(_DECIMAL128):
        return sum(values, _ZERO) / Decimal(len(values))


def _pairs_from_validation(
    validation: ResearchCalibrationOosValidationEvidence,
) -> tuple[_Pair, ...]:
    validation_set = validation.validation_set
    fit = validation_set.mapping_fit
    pairs = tuple(
        (
            fit.estimate_probability(item.source.confidence_score),
            _ONE if item.source.event_occurred else _ZERO,
        )
        for item in validation_set.observations
    )
    if not pairs:
        raise ResearchCalibrationTemporalComparisonUncertaintyValidationError(
            "temporal comparison uncertainty requires non-empty validation windows"
        )
    return pairs


def _ece(*, pairs: tuple[_Pair, ...], bin_count: int) -> Decimal:
    buckets: list[list[_Pair]] = [[] for _ in range(bin_count)]
    for estimate, outcome in pairs:
        index = bin_count - 1 if estimate == _ONE else int(estimate * bin_count)
        buckets[index].append((estimate, outcome))
    with localcontext(_DECIMAL128):
        total = _ZERO
        for bucket in buckets:
            if not bucket:
                continue
            estimates = tuple(item[0] for item in bucket)
            outcomes = tuple(item[1] for item in bucket)
            gap = abs(_mean(estimates) - _mean(outcomes))
            total += Decimal(len(bucket)) / Decimal(len(pairs)) * gap
        return total


def _window_metrics(
    *,
    pairs: tuple[_Pair, ...],
    bin_count: int,
) -> tuple[Decimal, Decimal, Decimal, Decimal]:
    mean_estimate = _mean(tuple(item[0] for item in pairs))
    event_rate = _mean(tuple(item[1] for item in pairs))
    absolute_mean_gap = abs(mean_estimate - event_rate)
    ece = _ece(pairs=pairs, bin_count=bin_count)
    return mean_estimate, event_rate, absolute_mean_gap, ece


def _changes(
    *,
    baseline_pairs: tuple[_Pair, ...],
    comparison_pairs: tuple[_Pair, ...],
    bin_count: int,
) -> _SourceChanges:
    baseline = _window_metrics(pairs=baseline_pairs, bin_count=bin_count)
    comparison = _window_metrics(pairs=comparison_pairs, bin_count=bin_count)
    values = (
        abs(comparison[2] - baseline[2]),
        abs(comparison[3] - baseline[3]),
        abs(comparison[0] - baseline[0]),
        abs(comparison[1] - baseline[1]),
    )
    for field_name, value in zip(
        (
            "absolute mean-gap change",
            "absolute ECE change",
            "absolute mean-probability shift",
            "absolute event-rate shift",
        ),
        values,
        strict=True,
    ):
        _validate_unit_decimal(value, field_name=field_name)
    return values


def _draw_start(
    *,
    seed: int,
    stream: bytes,
    replicate: int,
    draw: int,
    sample_size: int,
) -> int:
    payload = (
        _DOMAIN
        + b":"
        + stream
        + b":"
        + str(seed).encode("ascii")
        + b":"
        + str(replicate).encode("ascii")
        + b":"
        + str(draw).encode("ascii")
    )
    return int.from_bytes(sha256(payload).digest(), "big") % sample_size


def _resample(
    *,
    pairs: tuple[_Pair, ...],
    block_length: int,
    seed: int,
    stream: bytes,
    replicate: int,
) -> tuple[_Pair, ...]:
    if block_length > len(pairs):
        raise ResearchCalibrationTemporalComparisonUncertaintyValidationError(
            "temporal comparison block length cannot exceed its window sample size"
        )
    block_count = (len(pairs) + block_length - 1) // block_length
    result: list[_Pair] = []
    for draw in range(block_count):
        start = _draw_start(
            seed=seed,
            stream=stream,
            replicate=replicate,
            draw=draw,
            sample_size=len(pairs),
        )
        for offset in range(block_length):
            result.append(pairs[(start + offset) % len(pairs)])
            if len(result) == len(pairs):
                return tuple(result)
    return tuple(result)


def _derive(
    comparison: ResearchCalibrationTemporalComparisonEvidence,
    policy: ResearchCalibrationTemporalComparisonUncertaintyPolicy,
) -> _Derived:
    if not isinstance(comparison, ResearchCalibrationTemporalComparisonEvidence):
        raise ResearchCalibrationTemporalComparisonUncertaintyValidationError(
            "uncertainty requires ResearchCalibrationTemporalComparisonEvidence"
        )
    if not isinstance(policy, ResearchCalibrationTemporalComparisonUncertaintyPolicy):
        raise ResearchCalibrationTemporalComparisonUncertaintyValidationError(
            "uncertainty requires explicit temporal comparison uncertainty policy"
        )

    baseline_pairs = _pairs_from_validation(comparison.baseline)
    comparison_pairs = _pairs_from_validation(comparison.comparison)
    if len(baseline_pairs) != comparison.baseline_sample_size:
        raise ResearchCalibrationTemporalComparisonUncertaintyValidationError(
            "baseline sample size must match exact temporal comparison evidence"
        )
    if len(comparison_pairs) != comparison.comparison_sample_size:
        raise ResearchCalibrationTemporalComparisonUncertaintyValidationError(
            "comparison sample size must match exact temporal comparison evidence"
        )
    if policy.baseline_block_length > len(baseline_pairs):
        raise ResearchCalibrationTemporalComparisonUncertaintyValidationError(
            "baseline block length cannot exceed baseline sample size"
        )
    if policy.comparison_block_length > len(comparison_pairs):
        raise ResearchCalibrationTemporalComparisonUncertaintyValidationError(
            "comparison block length cannot exceed comparison sample size"
        )
    if comparison.baseline.policy != comparison.comparison.policy:
        raise ResearchCalibrationTemporalComparisonUncertaintyValidationError(
            "temporal comparison OOS diagnostic policies must remain identical"
        )
    bin_count = comparison.baseline.policy.bin_count
    source_changes = _changes(
        baseline_pairs=baseline_pairs,
        comparison_pairs=comparison_pairs,
        bin_count=bin_count,
    )
    expected_source = (
        comparison.absolute_mean_gap_change,
        comparison.absolute_ece_change,
        comparison.absolute_mean_probability_shift,
        comparison.absolute_event_rate_shift,
    )
    if source_changes != expected_source:
        raise ResearchCalibrationTemporalComparisonUncertaintyValidationError(
            "source temporal changes must match exact temporal comparison evidence"
        )

    mean_gap_changes: list[Decimal] = []
    ece_changes: list[Decimal] = []
    probability_shifts: list[Decimal] = []
    event_rate_shifts: list[Decimal] = []
    for replicate in range(policy.resample_count):
        baseline_resampled = _resample(
            pairs=baseline_pairs,
            block_length=policy.baseline_block_length,
            seed=policy.seed,
            stream=b"baseline",
            replicate=replicate,
        )
        comparison_resampled = _resample(
            pairs=comparison_pairs,
            block_length=policy.comparison_block_length,
            seed=policy.seed,
            stream=b"comparison",
            replicate=replicate,
        )
        changes = _changes(
            baseline_pairs=baseline_resampled,
            comparison_pairs=comparison_resampled,
            bin_count=bin_count,
        )
        mean_gap_changes.append(changes[0])
        ece_changes.append(changes[1])
        probability_shifts.append(changes[2])
        event_rate_shifts.append(changes[3])

    return (
        source_changes,
        tuple(mean_gap_changes),
        tuple(ece_changes),
        tuple(probability_shifts),
        tuple(event_rate_shifts),
    )


def _nearest_rank(values: _Distribution, probability: Decimal) -> Decimal:
    if not values:
        raise ResearchCalibrationTemporalComparisonUncertaintyValidationError(
            "temporal comparison percentile requires non-empty distribution"
        )
    if not _ZERO <= probability <= _ONE:
        raise ResearchCalibrationTemporalComparisonUncertaintyValidationError(
            "temporal comparison percentile probability must remain inside [0, 1]"
        )
    ordered = tuple(sorted(values))
    if probability == _ZERO:
        return ordered[0]
    rank = int(
        (probability * Decimal(len(ordered))).to_integral_value(rounding=ROUND_CEILING)
    )
    return ordered[max(1, rank) - 1]


def _interval(
    values: _Distribution,
    policy: ResearchCalibrationTemporalComparisonUncertaintyPolicy,
) -> ResearchCalibrationTemporalComparisonInterval:
    if policy.interval_method is not ResearchCalibrationIntervalMethod.PERCENTILE_NEAREST_RANK:
        raise ResearchCalibrationTemporalComparisonUncertaintyValidationError(
            "unsupported temporal comparison interval method"
        )
    with localcontext(_DECIMAL128):
        tail = (_ONE - policy.confidence_level) / Decimal(2)
    return ResearchCalibrationTemporalComparisonInterval(
        confidence_level=policy.confidence_level,
        method=policy.interval_method,
        lower=_nearest_rank(values, tail),
        upper=_nearest_rank(values, _ONE - tail),
    )


@dataclass(frozen=True, slots=True)
class ResearchCalibrationTemporalComparisonUncertaintyFingerprint:
    value: str

    def __post_init__(self) -> None:
        if not isinstance(self.value, str) or fullmatch(r"[0-9a-f]{64}", self.value) is None:
            raise ResearchCalibrationTemporalComparisonUncertaintyValidationError(
                "temporal comparison uncertainty fingerprint must be 64 lowercase hex"
            )

    def logical_values(self) -> tuple[str, ...]:
        return (self.value,)


def compute_research_calibration_temporal_comparison_uncertainty_fingerprint(
    *,
    comparison: ResearchCalibrationTemporalComparisonEvidence,
    policy: ResearchCalibrationTemporalComparisonUncertaintyPolicy,
    derived: _Derived,
    intervals: tuple[
        ResearchCalibrationTemporalComparisonInterval,
        ResearchCalibrationTemporalComparisonInterval,
        ResearchCalibrationTemporalComparisonInterval,
        ResearchCalibrationTemporalComparisonInterval,
    ],
) -> ResearchCalibrationTemporalComparisonUncertaintyFingerprint:
    expected = _derive(comparison, policy)
    if derived != expected:
        raise ResearchCalibrationTemporalComparisonUncertaintyValidationError(
            "temporal comparison uncertainty distributions must match deterministic resampling"
        )
    expected_intervals = tuple(_interval(values, policy) for values in derived[1:])
    if intervals != expected_intervals:
        raise ResearchCalibrationTemporalComparisonUncertaintyValidationError(
            "temporal comparison uncertainty intervals must match deterministic percentiles"
        )
    canonical = {
        "comparison_fingerprint": comparison.fingerprint.logical_values(),
        "policy": policy.logical_values(),
        "source_changes": tuple(format(item, "f") for item in derived[0]),
        "distributions": tuple(
            tuple(format(item, "f") for item in distribution)
            for distribution in derived[1:]
        ),
        "intervals": tuple(item.logical_values() for item in intervals),
    }
    encoded = json.dumps(
        canonical,
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    return ResearchCalibrationTemporalComparisonUncertaintyFingerprint(
        sha256(encoded).hexdigest()
    )


@dataclass(frozen=True, slots=True)
class ResearchCalibrationTemporalComparisonUncertaintyEvidence:
    """Deterministic resampling uncertainty for temporal calibration changes.

    Each ordered OOS window is circular-block resampled using a separate
    domain-separated deterministic stream. The evidence reports resampling
    distributions and percentile intervals for the four absolute changes already
    defined by `ResearchCalibrationTemporalComparisonEvidence`.

    It does not test a drift null hypothesis, produce a p-value, declare
    `drift_detected`, prove stationarity or window independence, infer optimal block
    lengths, guarantee nominal coverage, certify calibration, create
    `CalibratedProbability`, authorize production/capital, or create execution
    authority.
    """

    uncertainty_id: ResearchCalibrationTemporalComparisonUncertaintyId
    comparison: ResearchCalibrationTemporalComparisonEvidence
    policy: ResearchCalibrationTemporalComparisonUncertaintyPolicy
    source_absolute_mean_gap_change: Decimal
    source_absolute_ece_change: Decimal
    source_absolute_mean_probability_shift: Decimal
    source_absolute_event_rate_shift: Decimal
    resampled_absolute_mean_gap_changes: _Distribution
    resampled_absolute_ece_changes: _Distribution
    resampled_absolute_mean_probability_shifts: _Distribution
    resampled_absolute_event_rate_shifts: _Distribution
    absolute_mean_gap_change_interval: ResearchCalibrationTemporalComparisonInterval
    absolute_ece_change_interval: ResearchCalibrationTemporalComparisonInterval
    absolute_mean_probability_shift_interval: ResearchCalibrationTemporalComparisonInterval
    absolute_event_rate_shift_interval: ResearchCalibrationTemporalComparisonInterval
    fingerprint: ResearchCalibrationTemporalComparisonUncertaintyFingerprint

    def __post_init__(self) -> None:
        if not isinstance(
            self.uncertainty_id,
            ResearchCalibrationTemporalComparisonUncertaintyId,
        ):
            raise ResearchCalibrationTemporalComparisonUncertaintyValidationError(
                "uncertainty_id must use temporal comparison uncertainty id"
            )
        if not isinstance(self.comparison, ResearchCalibrationTemporalComparisonEvidence):
            raise ResearchCalibrationTemporalComparisonUncertaintyValidationError(
                "comparison must be ResearchCalibrationTemporalComparisonEvidence"
            )
        if not isinstance(self.policy, ResearchCalibrationTemporalComparisonUncertaintyPolicy):
            raise ResearchCalibrationTemporalComparisonUncertaintyValidationError(
                "policy must be temporal comparison uncertainty policy"
            )
        derived = _derive(self.comparison, self.policy)
        actual_source = (
            self.source_absolute_mean_gap_change,
            self.source_absolute_ece_change,
            self.source_absolute_mean_probability_shift,
            self.source_absolute_event_rate_shift,
        )
        actual_distributions = (
            self.resampled_absolute_mean_gap_changes,
            self.resampled_absolute_ece_changes,
            self.resampled_absolute_mean_probability_shifts,
            self.resampled_absolute_event_rate_shifts,
        )
        if actual_source != derived[0] or actual_distributions != derived[1:]:
            raise ResearchCalibrationTemporalComparisonUncertaintyValidationError(
                "temporal comparison uncertainty evidence must match exact resampling"
            )
        if any(len(item) != self.policy.resample_count for item in actual_distributions):
            raise ResearchCalibrationTemporalComparisonUncertaintyValidationError(
                "each temporal comparison distribution must match resample_count"
            )
        intervals = (
            self.absolute_mean_gap_change_interval,
            self.absolute_ece_change_interval,
            self.absolute_mean_probability_shift_interval,
            self.absolute_event_rate_shift_interval,
        )
        expected_intervals = tuple(_interval(values, self.policy) for values in derived[1:])
        if intervals != expected_intervals:
            raise ResearchCalibrationTemporalComparisonUncertaintyValidationError(
                "temporal comparison intervals must match exact resampling distributions"
            )
        if not isinstance(
            self.fingerprint,
            ResearchCalibrationTemporalComparisonUncertaintyFingerprint,
        ):
            raise ResearchCalibrationTemporalComparisonUncertaintyValidationError(
                "fingerprint must use temporal comparison uncertainty fingerprint"
            )
        expected_fingerprint = (
            compute_research_calibration_temporal_comparison_uncertainty_fingerprint(
                comparison=self.comparison,
                policy=self.policy,
                derived=derived,
                intervals=intervals,
            )
        )
        if self.fingerprint != expected_fingerprint:
            raise ResearchCalibrationTemporalComparisonUncertaintyValidationError(
                "temporal comparison uncertainty fingerprint must match exact evidence"
            )

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.uncertainty_id.logical_values(),
            self.comparison.fingerprint.logical_values(),
            self.policy.logical_values(),
            format(self.source_absolute_mean_gap_change, "f"),
            format(self.source_absolute_ece_change, "f"),
            format(self.source_absolute_mean_probability_shift, "f"),
            format(self.source_absolute_event_rate_shift, "f"),
            tuple(format(item, "f") for item in self.resampled_absolute_mean_gap_changes),
            tuple(format(item, "f") for item in self.resampled_absolute_ece_changes),
            tuple(
                format(item, "f")
                for item in self.resampled_absolute_mean_probability_shifts
            ),
            tuple(format(item, "f") for item in self.resampled_absolute_event_rate_shifts),
            self.absolute_mean_gap_change_interval.logical_values(),
            self.absolute_ece_change_interval.logical_values(),
            self.absolute_mean_probability_shift_interval.logical_values(),
            self.absolute_event_rate_shift_interval.logical_values(),
            self.fingerprint.logical_values(),
        )


def build_research_calibration_temporal_comparison_uncertainty_evidence(
    *,
    uncertainty_id: ResearchCalibrationTemporalComparisonUncertaintyId,
    comparison: ResearchCalibrationTemporalComparisonEvidence,
    policy: ResearchCalibrationTemporalComparisonUncertaintyPolicy,
) -> Result[
    ResearchCalibrationTemporalComparisonUncertaintyEvidence,
    ResearchCalibrationTemporalComparisonUncertaintyError,
]:
    """Build deterministic change uncertainty without declaring calibration drift."""

    try:
        derived = _derive(comparison, policy)
        intervals: tuple[
            ResearchCalibrationTemporalComparisonInterval,
            ResearchCalibrationTemporalComparisonInterval,
            ResearchCalibrationTemporalComparisonInterval,
            ResearchCalibrationTemporalComparisonInterval,
        ] = (
            _interval(derived[1], policy),
            _interval(derived[2], policy),
            _interval(derived[3], policy),
            _interval(derived[4], policy),
        )
        fingerprint = (
            compute_research_calibration_temporal_comparison_uncertainty_fingerprint(
                comparison=comparison,
                policy=policy,
                derived=derived,
                intervals=intervals,
            )
        )
        return Success(
            ResearchCalibrationTemporalComparisonUncertaintyEvidence(
                uncertainty_id=uncertainty_id,
                comparison=comparison,
                policy=policy,
                source_absolute_mean_gap_change=derived[0][0],
                source_absolute_ece_change=derived[0][1],
                source_absolute_mean_probability_shift=derived[0][2],
                source_absolute_event_rate_shift=derived[0][3],
                resampled_absolute_mean_gap_changes=derived[1],
                resampled_absolute_ece_changes=derived[2],
                resampled_absolute_mean_probability_shifts=derived[3],
                resampled_absolute_event_rate_shifts=derived[4],
                absolute_mean_gap_change_interval=intervals[0],
                absolute_ece_change_interval=intervals[1],
                absolute_mean_probability_shift_interval=intervals[2],
                absolute_event_rate_shift_interval=intervals[3],
                fingerprint=fingerprint,
            )
        )
    except ResearchCalibrationTemporalComparisonUncertaintyError as error:
        return Failure(error)

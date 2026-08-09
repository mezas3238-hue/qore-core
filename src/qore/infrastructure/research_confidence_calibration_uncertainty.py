from __future__ import annotations

import json
from dataclasses import dataclass
from decimal import ROUND_CEILING, ROUND_HALF_EVEN, Context, Decimal, localcontext
from enum import StrEnum
from hashlib import sha256
from re import fullmatch
from uuid import UUID

from qore.infrastructure.research_confidence_calibration_oos_validation import (
    ResearchCalibrationOosValidationEvidence,
)
from qore.kernel.errors import InfrastructureError
from qore.kernel.result import Failure, Result, Success

_DECIMAL128 = Context(prec=34, rounding=ROUND_HALF_EVEN)
_DOMAIN = b"qore-research-calibration-circular-block-bootstrap-v1"
_ZERO = Decimal(0)
_ONE = Decimal(1)


class ResearchCalibrationUncertaintyError(InfrastructureError):
    """Base error for research-only calibration uncertainty evidence."""

    __slots__ = ()


class ResearchCalibrationUncertaintyValidationError(ResearchCalibrationUncertaintyError):
    """Violation of a calibration uncertainty evidence invariant."""

    __slots__ = ()


def _validate_unit_decimal(value: Decimal, *, field_name: str) -> None:
    if not isinstance(value, Decimal) or not value.is_finite():
        raise ResearchCalibrationUncertaintyValidationError(
            f"{field_name} must be a finite Decimal"
        )
    if not _ZERO <= value <= _ONE:
        raise ResearchCalibrationUncertaintyValidationError(
            f"{field_name} must remain inside [0, 1]"
        )


@dataclass(frozen=True, slots=True)
class ResearchCalibrationUncertaintyId:
    value: UUID

    def __post_init__(self) -> None:
        if not isinstance(self.value, UUID):
            raise ResearchCalibrationUncertaintyValidationError(
                "calibration uncertainty id must be UUID"
            )

    def logical_values(self) -> tuple[str, ...]:
        return (str(self.value),)


class ResearchCalibrationIntervalMethod(StrEnum):
    """Supported deterministic interval construction methods."""

    PERCENTILE_NEAREST_RANK = "percentile-nearest-rank"


@dataclass(frozen=True, slots=True)
class ResearchCalibrationUncertaintyPolicy:
    """Explicit block-bootstrap and interval policy.

    `block_length`, `resample_count`, `seed`, and `confidence_level` are analyst-
    supplied modelling choices. The contract does not infer an optimal block size,
    prove stationarity, or guarantee nominal interval coverage.
    """

    block_length: int
    resample_count: int
    seed: int
    confidence_level: Decimal
    interval_method: ResearchCalibrationIntervalMethod

    def __post_init__(self) -> None:
        if type(self.block_length) is not int or self.block_length < 2:
            raise ResearchCalibrationUncertaintyValidationError(
                "calibration uncertainty block_length must be at least two"
            )
        if type(self.resample_count) is not int or self.resample_count < 2:
            raise ResearchCalibrationUncertaintyValidationError(
                "calibration uncertainty resample_count must be at least two"
            )
        if type(self.seed) is not int or self.seed < 0:
            raise ResearchCalibrationUncertaintyValidationError(
                "calibration uncertainty seed must be a non-negative integer"
            )
        if not isinstance(self.confidence_level, Decimal) or not self.confidence_level.is_finite():
            raise ResearchCalibrationUncertaintyValidationError(
                "calibration uncertainty confidence_level must be a finite Decimal"
            )
        if not _ZERO < self.confidence_level < _ONE:
            raise ResearchCalibrationUncertaintyValidationError(
                "calibration uncertainty confidence_level must lie strictly inside (0, 1)"
            )
        if not isinstance(self.interval_method, ResearchCalibrationIntervalMethod):
            raise ResearchCalibrationUncertaintyValidationError(
                "calibration uncertainty interval_method must be explicit"
            )

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.block_length,
            self.resample_count,
            self.seed,
            format(self.confidence_level, "f"),
            self.interval_method.value,
        )


@dataclass(frozen=True, slots=True)
class ResearchCalibrationPercentileInterval:
    confidence_level: Decimal
    method: ResearchCalibrationIntervalMethod
    lower: Decimal
    upper: Decimal

    def __post_init__(self) -> None:
        if not isinstance(self.method, ResearchCalibrationIntervalMethod):
            raise ResearchCalibrationUncertaintyValidationError(
                "calibration interval method must be explicit"
            )
        if not isinstance(self.confidence_level, Decimal) or not self.confidence_level.is_finite():
            raise ResearchCalibrationUncertaintyValidationError(
                "calibration interval confidence_level must be a finite Decimal"
            )
        if not _ZERO < self.confidence_level < _ONE:
            raise ResearchCalibrationUncertaintyValidationError(
                "calibration interval confidence_level must lie strictly inside (0, 1)"
            )
        _validate_unit_decimal(self.lower, field_name="calibration interval lower")
        _validate_unit_decimal(self.upper, field_name="calibration interval upper")
        if self.upper < self.lower:
            raise ResearchCalibrationUncertaintyValidationError(
                "calibration interval upper cannot precede lower"
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


def _source_pairs(
    validation: ResearchCalibrationOosValidationEvidence,
) -> tuple[_Pair, ...]:
    if not isinstance(validation, ResearchCalibrationOosValidationEvidence):
        raise ResearchCalibrationUncertaintyValidationError(
            "calibration uncertainty requires ResearchCalibrationOosValidationEvidence"
        )
    fit = validation.validation_set.mapping_fit
    pairs = tuple(
        (
            fit.estimate_probability(item.source.confidence_score),
            _ONE if item.source.event_occurred else _ZERO,
        )
        for item in validation.validation_set.observations
    )
    if len(pairs) != validation.sample_size:
        raise ResearchCalibrationUncertaintyValidationError(
            "calibration uncertainty source size must match OOS validation evidence"
        )
    return pairs


def _mean(values: tuple[Decimal, ...]) -> Decimal:
    with localcontext(_DECIMAL128):
        return sum(values, _ZERO) / Decimal(len(values))


def _brier(pairs: tuple[_Pair, ...]) -> Decimal:
    return _mean(tuple((estimate - outcome) ** 2 for estimate, outcome in pairs))


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


def _draw_start(*, seed: int, replicate: int, draw: int, sample_size: int) -> int:
    payload = (
        _DOMAIN
        + b":"
        + str(seed).encode("ascii")
        + b":"
        + str(replicate).encode("ascii")
        + b":"
        + str(draw).encode("ascii")
    )
    return int.from_bytes(sha256(payload).digest(), "big") % sample_size


def _resampled_pairs(
    *,
    pairs: tuple[_Pair, ...],
    policy: ResearchCalibrationUncertaintyPolicy,
    replicate: int,
) -> tuple[_Pair, ...]:
    sample_size = len(pairs)
    if policy.block_length > sample_size:
        raise ResearchCalibrationUncertaintyValidationError(
            "calibration uncertainty block_length cannot exceed OOS sample size"
        )
    blocks = (sample_size + policy.block_length - 1) // policy.block_length
    resampled: list[_Pair] = []
    for draw in range(blocks):
        start = _draw_start(
            seed=policy.seed,
            replicate=replicate,
            draw=draw,
            sample_size=sample_size,
        )
        for offset in range(policy.block_length):
            resampled.append(pairs[(start + offset) % sample_size])
            if len(resampled) == sample_size:
                return tuple(resampled)
    return tuple(resampled)


def _derive_distributions(
    validation: ResearchCalibrationOosValidationEvidence,
    policy: ResearchCalibrationUncertaintyPolicy,
) -> tuple[Decimal, Decimal, _Distribution, _Distribution]:
    if not isinstance(policy, ResearchCalibrationUncertaintyPolicy):
        raise ResearchCalibrationUncertaintyValidationError(
            "calibration uncertainty requires ResearchCalibrationUncertaintyPolicy"
        )
    pairs = _source_pairs(validation)
    if policy.block_length > len(pairs):
        raise ResearchCalibrationUncertaintyValidationError(
            "calibration uncertainty block_length cannot exceed OOS sample size"
        )
    source_brier = _brier(pairs)
    source_ece = _ece(pairs=pairs, bin_count=validation.policy.bin_count)
    if source_brier != validation.brier_score:
        raise ResearchCalibrationUncertaintyValidationError(
            "calibration uncertainty source Brier must match OOS validation"
        )
    if source_ece != validation.expected_calibration_error:
        raise ResearchCalibrationUncertaintyValidationError(
            "calibration uncertainty source ECE must match OOS validation"
        )
    brier_values: list[Decimal] = []
    ece_values: list[Decimal] = []
    for replicate in range(policy.resample_count):
        resampled = _resampled_pairs(pairs=pairs, policy=policy, replicate=replicate)
        brier_values.append(_brier(resampled))
        ece_values.append(_ece(pairs=resampled, bin_count=validation.policy.bin_count))
    return source_brier, source_ece, tuple(brier_values), tuple(ece_values)


def _nearest_rank(values: _Distribution, probability: Decimal) -> Decimal:
    if not values:
        raise ResearchCalibrationUncertaintyValidationError(
            "calibration percentile requires a non-empty distribution"
        )
    if not _ZERO <= probability <= _ONE:
        raise ResearchCalibrationUncertaintyValidationError(
            "calibration percentile probability must remain inside [0, 1]"
        )
    ordered = tuple(sorted(values))
    if probability == _ZERO:
        return ordered[0]
    rank = int(
        (probability * Decimal(len(ordered))).to_integral_value(rounding=ROUND_CEILING)
    )
    return ordered[max(1, rank) - 1]


def _percentile_interval(
    values: _Distribution,
    policy: ResearchCalibrationUncertaintyPolicy,
) -> ResearchCalibrationPercentileInterval:
    if policy.interval_method is not ResearchCalibrationIntervalMethod.PERCENTILE_NEAREST_RANK:
        raise ResearchCalibrationUncertaintyValidationError(
            "unsupported calibration uncertainty interval method"
        )
    with localcontext(_DECIMAL128):
        tail = (_ONE - policy.confidence_level) / Decimal(2)
    return ResearchCalibrationPercentileInterval(
        confidence_level=policy.confidence_level,
        method=policy.interval_method,
        lower=_nearest_rank(values, tail),
        upper=_nearest_rank(values, _ONE - tail),
    )


@dataclass(frozen=True, slots=True)
class ResearchCalibrationUncertaintyFingerprint:
    value: str

    def __post_init__(self) -> None:
        if not isinstance(self.value, str) or fullmatch(r"[0-9a-f]{64}", self.value) is None:
            raise ResearchCalibrationUncertaintyValidationError(
                "calibration uncertainty fingerprint must be 64 lowercase hex characters"
            )

    def logical_values(self) -> tuple[str, ...]:
        return (self.value,)


def compute_research_calibration_uncertainty_fingerprint(
    *,
    validation: ResearchCalibrationOosValidationEvidence,
    policy: ResearchCalibrationUncertaintyPolicy,
    source_brier_score: Decimal,
    source_ece: Decimal,
    resampled_brier_scores: _Distribution,
    resampled_ece: _Distribution,
    brier_interval: ResearchCalibrationPercentileInterval,
    ece_interval: ResearchCalibrationPercentileInterval,
) -> ResearchCalibrationUncertaintyFingerprint:
    expected = _derive_distributions(validation, policy)
    if (
        source_brier_score,
        source_ece,
        resampled_brier_scores,
        resampled_ece,
    ) != expected:
        raise ResearchCalibrationUncertaintyValidationError(
            "calibration uncertainty distribution must match deterministic resampling"
        )
    expected_brier_interval = _percentile_interval(resampled_brier_scores, policy)
    expected_ece_interval = _percentile_interval(resampled_ece, policy)
    if brier_interval != expected_brier_interval or ece_interval != expected_ece_interval:
        raise ResearchCalibrationUncertaintyValidationError(
            "calibration uncertainty intervals must match deterministic percentiles"
        )
    canonical = {
        "validation_fingerprint": validation.fingerprint.logical_values(),
        "policy": policy.logical_values(),
        "source_brier_score": format(source_brier_score, "f"),
        "source_ece": format(source_ece, "f"),
        "resampled_brier_scores": tuple(format(item, "f") for item in resampled_brier_scores),
        "resampled_ece": tuple(format(item, "f") for item in resampled_ece),
        "brier_interval": brier_interval.logical_values(),
        "ece_interval": ece_interval.logical_values(),
    }
    encoded = json.dumps(
        canonical,
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    return ResearchCalibrationUncertaintyFingerprint(sha256(encoded).hexdigest())


@dataclass(frozen=True, slots=True)
class ResearchCalibrationUncertaintyEvidence:
    """Deterministic block-bootstrap uncertainty around OOS calibration metrics.

    Circular blocks preserve local temporal adjacency at the explicitly supplied
    block length. Percentile nearest-rank intervals summarize the resampling
    distribution for OOS Brier score and ECE.

    This does not prove stationarity, independence, optimal block length, nominal
    coverage, sample adequacy, calibration, future predictive validity, strategy
    approval, production readiness, capital authorization, or execution authority.
    """

    uncertainty_id: ResearchCalibrationUncertaintyId
    validation: ResearchCalibrationOosValidationEvidence
    policy: ResearchCalibrationUncertaintyPolicy
    sample_size: int
    source_brier_score: Decimal
    source_ece: Decimal
    resampled_brier_scores: _Distribution
    resampled_ece: _Distribution
    brier_interval: ResearchCalibrationPercentileInterval
    ece_interval: ResearchCalibrationPercentileInterval
    fingerprint: ResearchCalibrationUncertaintyFingerprint

    def __post_init__(self) -> None:
        if not isinstance(self.uncertainty_id, ResearchCalibrationUncertaintyId):
            raise ResearchCalibrationUncertaintyValidationError(
                "uncertainty_id must be ResearchCalibrationUncertaintyId"
            )
        if not isinstance(self.validation, ResearchCalibrationOosValidationEvidence):
            raise ResearchCalibrationUncertaintyValidationError(
                "validation must be ResearchCalibrationOosValidationEvidence"
            )
        if not isinstance(self.policy, ResearchCalibrationUncertaintyPolicy):
            raise ResearchCalibrationUncertaintyValidationError(
                "policy must be ResearchCalibrationUncertaintyPolicy"
            )
        expected = _derive_distributions(self.validation, self.policy)
        actual = (
            self.source_brier_score,
            self.source_ece,
            self.resampled_brier_scores,
            self.resampled_ece,
        )
        if self.sample_size != self.validation.sample_size or actual != expected:
            raise ResearchCalibrationUncertaintyValidationError(
                "calibration uncertainty evidence must match exact OOS source and resampling"
            )
        if len(self.resampled_brier_scores) != self.policy.resample_count:
            raise ResearchCalibrationUncertaintyValidationError(
                "Brier resample count must match uncertainty policy"
            )
        if len(self.resampled_ece) != self.policy.resample_count:
            raise ResearchCalibrationUncertaintyValidationError(
                "ECE resample count must match uncertainty policy"
            )
        if self.brier_interval != _percentile_interval(
            self.resampled_brier_scores,
            self.policy,
        ):
            raise ResearchCalibrationUncertaintyValidationError(
                "Brier interval must match deterministic percentile evidence"
            )
        if self.ece_interval != _percentile_interval(self.resampled_ece, self.policy):
            raise ResearchCalibrationUncertaintyValidationError(
                "ECE interval must match deterministic percentile evidence"
            )
        if not isinstance(self.fingerprint, ResearchCalibrationUncertaintyFingerprint):
            raise ResearchCalibrationUncertaintyValidationError(
                "fingerprint must be ResearchCalibrationUncertaintyFingerprint"
            )
        expected_fingerprint = compute_research_calibration_uncertainty_fingerprint(
            validation=self.validation,
            policy=self.policy,
            source_brier_score=self.source_brier_score,
            source_ece=self.source_ece,
            resampled_brier_scores=self.resampled_brier_scores,
            resampled_ece=self.resampled_ece,
            brier_interval=self.brier_interval,
            ece_interval=self.ece_interval,
        )
        if self.fingerprint != expected_fingerprint:
            raise ResearchCalibrationUncertaintyValidationError(
                "calibration uncertainty fingerprint must match exact evidence"
            )

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.uncertainty_id.logical_values(),
            self.validation.fingerprint.logical_values(),
            self.policy.logical_values(),
            self.sample_size,
            format(self.source_brier_score, "f"),
            format(self.source_ece, "f"),
            tuple(format(item, "f") for item in self.resampled_brier_scores),
            tuple(format(item, "f") for item in self.resampled_ece),
            self.brier_interval.logical_values(),
            self.ece_interval.logical_values(),
            self.fingerprint.logical_values(),
        )


def build_research_calibration_uncertainty_evidence(
    *,
    uncertainty_id: ResearchCalibrationUncertaintyId,
    validation: ResearchCalibrationOosValidationEvidence,
    policy: ResearchCalibrationUncertaintyPolicy,
) -> Result[ResearchCalibrationUncertaintyEvidence, ResearchCalibrationUncertaintyError]:
    """Build deterministic OOS calibration uncertainty without certification claims."""

    try:
        source_brier, source_ece, brier_values, ece_values = _derive_distributions(
            validation,
            policy,
        )
        brier_interval = _percentile_interval(brier_values, policy)
        ece_interval = _percentile_interval(ece_values, policy)
        fingerprint = compute_research_calibration_uncertainty_fingerprint(
            validation=validation,
            policy=policy,
            source_brier_score=source_brier,
            source_ece=source_ece,
            resampled_brier_scores=brier_values,
            resampled_ece=ece_values,
            brier_interval=brier_interval,
            ece_interval=ece_interval,
        )
        return Success(
            ResearchCalibrationUncertaintyEvidence(
                uncertainty_id=uncertainty_id,
                validation=validation,
                policy=policy,
                sample_size=validation.sample_size,
                source_brier_score=source_brier,
                source_ece=source_ece,
                resampled_brier_scores=brier_values,
                resampled_ece=ece_values,
                brier_interval=brier_interval,
                ece_interval=ece_interval,
                fingerprint=fingerprint,
            )
        )
    except ResearchCalibrationUncertaintyError as error:
        return Failure(error)

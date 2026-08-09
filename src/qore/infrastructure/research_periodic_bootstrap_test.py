from __future__ import annotations

from dataclasses import dataclass
from decimal import ROUND_HALF_EVEN, Context, Decimal, localcontext
from enum import StrEnum
from hashlib import sha256
from uuid import UUID

from qore.infrastructure.research_periodic_equity import ResearchPeriodicEquityReturnSeries
from qore.kernel.errors import InfrastructureError
from qore.kernel.result import Failure, Result, Success

_DECIMAL128 = Context(prec=34, rounding=ROUND_HALF_EVEN)
_DOMAIN = b"qore-periodic-null-circular-block-bootstrap-v1"


class ResearchPeriodicBootstrapTestError(InfrastructureError):
    """Base error for fixed-period circular block-bootstrap hypothesis evidence."""

    __slots__ = ()


class ResearchPeriodicBootstrapTestValidationError(
    ResearchPeriodicBootstrapTestError
):
    """Violation of a periodic block-bootstrap test invariant."""

    __slots__ = ()


class ResearchPeriodicBootstrapAlternative(StrEnum):
    GREATER = "greater"
    LESS = "less"
    TWO_SIDED = "two_sided"


@dataclass(frozen=True, slots=True)
class ResearchPeriodicBootstrapTestId:
    value: UUID

    def __post_init__(self) -> None:
        if not isinstance(self.value, UUID):
            raise ResearchPeriodicBootstrapTestValidationError(
                "periodic bootstrap test id must be UUID"
            )

    def logical_values(self) -> tuple[str, ...]:
        return (str(self.value),)


@dataclass(frozen=True, slots=True)
class ResearchPeriodicBootstrapTestPolicy:
    """Explicit null, alternative, circular block length and deterministic draws."""

    null_mean_per_period: Decimal
    alternative: ResearchPeriodicBootstrapAlternative
    block_length: int
    resample_count: int
    seed: int

    def __post_init__(self) -> None:
        if (
            not isinstance(self.null_mean_per_period, Decimal)
            or not self.null_mean_per_period.is_finite()
        ):
            raise ResearchPeriodicBootstrapTestValidationError(
                "null_mean_per_period must be a finite Decimal"
            )
        if not isinstance(self.alternative, ResearchPeriodicBootstrapAlternative):
            raise ResearchPeriodicBootstrapTestValidationError(
                "alternative must be ResearchPeriodicBootstrapAlternative"
            )
        if type(self.block_length) is not int or self.block_length < 2:
            raise ResearchPeriodicBootstrapTestValidationError(
                "block_length must be an integer of at least two"
            )
        if type(self.resample_count) is not int or self.resample_count <= 0:
            raise ResearchPeriodicBootstrapTestValidationError(
                "resample_count must be a positive integer"
            )
        if type(self.seed) is not int or self.seed < 0:
            raise ResearchPeriodicBootstrapTestValidationError(
                "seed must be a non-negative integer"
            )

    def logical_values(self) -> tuple[object, ...]:
        return (
            format(self.null_mean_per_period, "f"),
            self.alternative.value,
            self.block_length,
            self.resample_count,
            self.seed,
        )


def _draw_start(*, seed: int, replicate: int, draw: int, sample_size: int) -> int:
    payload = b":".join(
        (
            _DOMAIN,
            str(seed).encode("ascii"),
            str(replicate).encode("ascii"),
            str(draw).encode("ascii"),
        )
    )
    return int.from_bytes(sha256(payload).digest(), "big") % sample_size


def _mean(values: tuple[Decimal, ...]) -> Decimal:
    with localcontext(_DECIMAL128):
        return sum(values, Decimal(0)) / Decimal(len(values))


def _resample_means_under_null(
    values: tuple[Decimal, ...],
    *,
    observed_mean: Decimal,
    policy: ResearchPeriodicBootstrapTestPolicy,
) -> tuple[Decimal, ...]:
    sample_size = len(values)
    with localcontext(_DECIMAL128):
        null_values = tuple(
            value - observed_mean + policy.null_mean_per_period for value in values
        )
    blocks_per_replicate = (
        sample_size + policy.block_length - 1
    ) // policy.block_length
    means: list[Decimal] = []
    for replicate in range(policy.resample_count):
        sample: list[Decimal] = []
        for draw in range(blocks_per_replicate):
            start = _draw_start(
                seed=policy.seed,
                replicate=replicate,
                draw=draw,
                sample_size=sample_size,
            )
            for offset in range(policy.block_length):
                sample.append(null_values[(start + offset) % sample_size])
                if len(sample) == sample_size:
                    break
            if len(sample) == sample_size:
                break
        means.append(_mean(tuple(sample)))
    return tuple(means)


def _is_extreme(
    replicate_mean: Decimal,
    *,
    observed_mean: Decimal,
    policy: ResearchPeriodicBootstrapTestPolicy,
) -> bool:
    null = policy.null_mean_per_period
    if policy.alternative is ResearchPeriodicBootstrapAlternative.GREATER:
        return replicate_mean >= observed_mean
    if policy.alternative is ResearchPeriodicBootstrapAlternative.LESS:
        return replicate_mean <= observed_mean
    return abs(replicate_mean - null) >= abs(observed_mean - null)


def _derive_test(
    series: ResearchPeriodicEquityReturnSeries,
    policy: ResearchPeriodicBootstrapTestPolicy,
) -> tuple[int, Decimal, tuple[Decimal, ...], int, Decimal]:
    if not isinstance(series, ResearchPeriodicEquityReturnSeries):
        raise ResearchPeriodicBootstrapTestValidationError(
            "periodic bootstrap test requires ResearchPeriodicEquityReturnSeries"
        )
    if not isinstance(policy, ResearchPeriodicBootstrapTestPolicy):
        raise ResearchPeriodicBootstrapTestValidationError(
            "periodic bootstrap test requires ResearchPeriodicBootstrapTestPolicy"
        )
    values = tuple(point.return_rate for point in series.returns)
    sample_size = len(values)
    if sample_size < 3:
        raise ResearchPeriodicBootstrapTestValidationError(
            "periodic bootstrap test requires at least three periodic returns"
        )
    if policy.block_length > sample_size:
        raise ResearchPeriodicBootstrapTestValidationError(
            "block_length cannot exceed periodic return sample size"
        )
    observed_mean = _mean(values)
    replicate_means = _resample_means_under_null(
        values,
        observed_mean=observed_mean,
        policy=policy,
    )
    extreme_count = sum(
        _is_extreme(
            replicate_mean,
            observed_mean=observed_mean,
            policy=policy,
        )
        for replicate_mean in replicate_means
    )
    with localcontext(_DECIMAL128):
        p_value = Decimal(extreme_count + 1) / Decimal(policy.resample_count + 1)
    return sample_size, observed_mean, replicate_means, extreme_count, p_value


@dataclass(frozen=True, slots=True)
class ResearchPeriodicBootstrapTestEvidence:
    """Deterministic circular block-bootstrap mean test under an explicit null.

    Source returns are recentered to the null mean before circular block
    resampling. The reported p-value uses the finite-resampling plus-one
    correction `(extreme + 1)/(B + 1)`. It is inferential evidence conditional on
    this exact frozen dataset/run, block length, null, alternative, seed and B.

    It does not select block length, correct for repeated strategy/model searches,
    prove stationarity, guarantee nominal test size, imply predictive validity, or
    decide a significance threshold. No `significant` boolean is provided.
    """

    test_id: ResearchPeriodicBootstrapTestId
    series: ResearchPeriodicEquityReturnSeries
    policy: ResearchPeriodicBootstrapTestPolicy
    sample_size: int
    observed_mean: Decimal
    null_resampled_means: tuple[Decimal, ...]
    extreme_count: int
    bootstrap_p_value: Decimal

    def __post_init__(self) -> None:
        if not isinstance(self.test_id, ResearchPeriodicBootstrapTestId):
            raise ResearchPeriodicBootstrapTestValidationError(
                "test_id must be ResearchPeriodicBootstrapTestId"
            )
        expected = _derive_test(self.series, self.policy)
        actual = (
            self.sample_size,
            self.observed_mean,
            self.null_resampled_means,
            self.extreme_count,
            self.bootstrap_p_value,
        )
        if actual != expected:
            raise ResearchPeriodicBootstrapTestValidationError(
                "bootstrap test evidence must match source returns and explicit policy"
            )
        if not 0 < self.bootstrap_p_value <= 1:
            raise ResearchPeriodicBootstrapTestValidationError(
                "bootstrap p-value must be in (0, 1]"
            )

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.test_id.logical_values(),
            self.series.logical_values(),
            self.policy.logical_values(),
            self.sample_size,
            format(self.observed_mean, "f"),
            tuple(format(value, "f") for value in self.null_resampled_means),
            self.extreme_count,
            format(self.bootstrap_p_value, "f"),
        )


def build_research_periodic_bootstrap_test_evidence(
    *,
    test_id: ResearchPeriodicBootstrapTestId,
    series: ResearchPeriodicEquityReturnSeries,
    policy: ResearchPeriodicBootstrapTestPolicy,
) -> Result[
    ResearchPeriodicBootstrapTestEvidence,
    ResearchPeriodicBootstrapTestError,
]:
    """Build block-bootstrap p-value evidence without a significance verdict."""

    try:
        (
            sample_size,
            observed_mean,
            replicate_means,
            extreme_count,
            p_value,
        ) = _derive_test(series, policy)
        return Success(
            ResearchPeriodicBootstrapTestEvidence(
                test_id=test_id,
                series=series,
                policy=policy,
                sample_size=sample_size,
                observed_mean=observed_mean,
                null_resampled_means=replicate_means,
                extreme_count=extreme_count,
                bootstrap_p_value=p_value,
            )
        )
    except ResearchPeriodicBootstrapTestError as error:
        return Failure(error)

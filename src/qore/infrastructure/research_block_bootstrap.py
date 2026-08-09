from __future__ import annotations

from dataclasses import dataclass
from decimal import ROUND_HALF_EVEN, Context, Decimal, localcontext
from hashlib import sha256
from uuid import UUID

from qore.infrastructure.research_serial_dependence import (
    ResearchSerialDependenceDiagnostic,
)
from qore.kernel.errors import InfrastructureError
from qore.kernel.result import Failure, Result, Success

_DECIMAL128 = Context(prec=34, rounding=ROUND_HALF_EVEN)
_DOMAIN = b"qore-research-circular-block-bootstrap-v1"


class ResearchBlockBootstrapError(InfrastructureError):
    """Base error for deterministic research block-resampling evidence."""

    __slots__ = ()


class ResearchBlockBootstrapValidationError(ResearchBlockBootstrapError):
    """Violation of a block-bootstrap evidence invariant."""

    __slots__ = ()


@dataclass(frozen=True, slots=True)
class ResearchBlockBootstrapDistributionId:
    value: UUID

    def __post_init__(self) -> None:
        if not isinstance(self.value, UUID):
            raise ResearchBlockBootstrapValidationError(
                "block bootstrap distribution id must be UUID"
            )

    def logical_values(self) -> tuple[str, ...]:
        return (str(self.value),)


@dataclass(frozen=True, slots=True)
class ResearchBlockBootstrapPolicy:
    """Explicit deterministic circular-block resampling policy.

    `block_length` is an analyst-supplied modelling choice. This contract does
    not infer an optimal block size or claim that the chosen value fully captures
    dependence in the return sequence.
    """

    block_length: int
    resample_count: int
    seed: int

    def __post_init__(self) -> None:
        if type(self.block_length) is not int or self.block_length < 2:
            raise ResearchBlockBootstrapValidationError(
                "block_length must be an integer of at least two"
            )
        if type(self.resample_count) is not int or self.resample_count <= 0:
            raise ResearchBlockBootstrapValidationError(
                "resample_count must be a positive integer"
            )
        if type(self.seed) is not int or self.seed < 0:
            raise ResearchBlockBootstrapValidationError(
                "seed must be a non-negative integer"
            )

    def logical_values(self) -> tuple[int, int, int]:
        return (self.block_length, self.resample_count, self.seed)


def _source_values(diagnostic: ResearchSerialDependenceDiagnostic) -> tuple[Decimal, ...]:
    if not isinstance(diagnostic, ResearchSerialDependenceDiagnostic):
        raise ResearchBlockBootstrapValidationError(
            "block bootstrap requires ResearchSerialDependenceDiagnostic"
        )
    values = tuple(sample.return_rate for sample in diagnostic.frame.samples)
    if not values:
        raise ResearchBlockBootstrapValidationError(
            "block bootstrap requires non-empty return samples"
        )
    return values


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


def _mean(values: tuple[Decimal, ...]) -> Decimal:
    with localcontext(_DECIMAL128):
        return sum(values, Decimal(0)) / Decimal(len(values))


def _bootstrap_means(
    diagnostic: ResearchSerialDependenceDiagnostic,
    policy: ResearchBlockBootstrapPolicy,
) -> tuple[Decimal, tuple[Decimal, ...]]:
    if not isinstance(policy, ResearchBlockBootstrapPolicy):
        raise ResearchBlockBootstrapValidationError(
            "policy must be ResearchBlockBootstrapPolicy"
        )
    values = _source_values(diagnostic)
    sample_size = len(values)
    if policy.block_length > sample_size:
        raise ResearchBlockBootstrapValidationError(
            "block_length cannot exceed source sample size"
        )
    source_mean = _mean(values)
    blocks_per_replicate = (sample_size + policy.block_length - 1) // policy.block_length
    means: list[Decimal] = []
    for replicate in range(policy.resample_count):
        resampled: list[Decimal] = []
        for draw in range(blocks_per_replicate):
            start = _draw_start(
                seed=policy.seed,
                replicate=replicate,
                draw=draw,
                sample_size=sample_size,
            )
            for offset in range(policy.block_length):
                resampled.append(values[(start + offset) % sample_size])
                if len(resampled) == sample_size:
                    break
            if len(resampled) == sample_size:
                break
        means.append(_mean(tuple(resampled)))
    return source_mean, tuple(means)


@dataclass(frozen=True, slots=True)
class ResearchBlockBootstrapDistribution:
    """Deterministic circular-block resampling distribution of mean trade return.

    The source is the exact frozen-OOS trade-return sampling frame already bound
    to its lag-one dependence diagnostic. The output is a resampling distribution,
    not a confidence interval, p-value, significance test, independence proof, or
    Sharpe/Sortino estimate. Circular blocks preserve local sequence adjacency at
    the explicitly chosen block length; they do not prove that longer-range,
    nonlinear, regime, cross-asset, or overlapping-exposure dependence is solved.
    """

    distribution_id: ResearchBlockBootstrapDistributionId
    diagnostic: ResearchSerialDependenceDiagnostic
    policy: ResearchBlockBootstrapPolicy
    sample_size: int
    source_mean: Decimal
    resampled_means: tuple[Decimal, ...]

    def __post_init__(self) -> None:
        if not isinstance(
            self.distribution_id,
            ResearchBlockBootstrapDistributionId,
        ):
            raise ResearchBlockBootstrapValidationError(
                "distribution_id must be ResearchBlockBootstrapDistributionId"
            )
        if not isinstance(self.diagnostic, ResearchSerialDependenceDiagnostic):
            raise ResearchBlockBootstrapValidationError(
                "distribution requires ResearchSerialDependenceDiagnostic"
            )
        if not isinstance(self.policy, ResearchBlockBootstrapPolicy):
            raise ResearchBlockBootstrapValidationError(
                "distribution requires ResearchBlockBootstrapPolicy"
            )
        expected_mean, expected_distribution = _bootstrap_means(
            self.diagnostic,
            self.policy,
        )
        expected_size = self.diagnostic.frame.sample_size
        if self.sample_size != expected_size:
            raise ResearchBlockBootstrapValidationError(
                "sample_size must match source sampling frame"
            )
        if self.source_mean != expected_mean:
            raise ResearchBlockBootstrapValidationError(
                "source_mean must equal the canonical sample mean"
            )
        if self.resampled_means != expected_distribution:
            raise ResearchBlockBootstrapValidationError(
                "resampled_means must equal deterministic circular-block draws"
            )
        if len(self.resampled_means) != self.policy.resample_count:
            raise ResearchBlockBootstrapValidationError(
                "resampled_means count must match bootstrap policy"
            )

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.distribution_id.logical_values(),
            self.diagnostic.logical_values(),
            self.policy.logical_values(),
            self.sample_size,
            format(self.source_mean, "f"),
            tuple(format(value, "f") for value in self.resampled_means),
        )


def build_research_block_bootstrap_distribution(
    *,
    distribution_id: ResearchBlockBootstrapDistributionId,
    diagnostic: ResearchSerialDependenceDiagnostic,
    policy: ResearchBlockBootstrapPolicy,
) -> Result[ResearchBlockBootstrapDistribution, ResearchBlockBootstrapError]:
    """Build reproducible block-resampling evidence without inference claims."""

    try:
        source_mean, distribution = _bootstrap_means(diagnostic, policy)
        return Success(
            ResearchBlockBootstrapDistribution(
                distribution_id=distribution_id,
                diagnostic=diagnostic,
                policy=policy,
                sample_size=diagnostic.frame.sample_size,
                source_mean=source_mean,
                resampled_means=distribution,
            )
        )
    except ResearchBlockBootstrapError as error:
        return Failure(error)

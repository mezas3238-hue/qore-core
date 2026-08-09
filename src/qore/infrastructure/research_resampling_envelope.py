from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum
from uuid import UUID

from qore.infrastructure.research_block_bootstrap import (
    ResearchBlockBootstrapDistribution,
)
from qore.kernel.errors import InfrastructureError
from qore.kernel.result import Failure, Result, Success


class ResearchResamplingEnvelopeError(InfrastructureError):
    """Base error for deterministic resampling-envelope evidence."""

    __slots__ = ()


class ResearchResamplingEnvelopeValidationError(ResearchResamplingEnvelopeError):
    """Violation of a resampling-envelope invariant."""

    __slots__ = ()


class ResearchEmpiricalQuantileRule(StrEnum):
    NEAREST_RANK = "nearest_rank"


@dataclass(frozen=True, slots=True)
class ResearchResamplingEnvelopeId:
    value: UUID

    def __post_init__(self) -> None:
        if not isinstance(self.value, UUID):
            raise ResearchResamplingEnvelopeValidationError(
                "resampling envelope id must be UUID"
            )

    def logical_values(self) -> tuple[str, ...]:
        return (str(self.value),)


@dataclass(frozen=True, slots=True)
class ResearchResamplingEnvelopePolicy:
    """Explicit finite-sample quantile policy in basis points.

    Quantile 0 returns the minimum. Positive quantiles use nearest-rank:
    rank = ceil(p * n), with rank one-based. This avoids hidden interpolation
    semantics and keeps the envelope deterministic across environments.
    """

    lower_quantile_bps: int
    upper_quantile_bps: int
    rule: ResearchEmpiricalQuantileRule = ResearchEmpiricalQuantileRule.NEAREST_RANK

    def __post_init__(self) -> None:
        if type(self.lower_quantile_bps) is not int or not 0 <= self.lower_quantile_bps <= 10_000:
            raise ResearchResamplingEnvelopeValidationError(
                "lower_quantile_bps must be an integer between 0 and 10000"
            )
        if type(self.upper_quantile_bps) is not int or not 0 <= self.upper_quantile_bps <= 10_000:
            raise ResearchResamplingEnvelopeValidationError(
                "upper_quantile_bps must be an integer between 0 and 10000"
            )
        if self.lower_quantile_bps >= self.upper_quantile_bps:
            raise ResearchResamplingEnvelopeValidationError(
                "lower quantile must be strictly below upper quantile"
            )
        if self.rule is not ResearchEmpiricalQuantileRule.NEAREST_RANK:
            raise ResearchResamplingEnvelopeValidationError(
                "resampling envelope currently supports nearest-rank only"
            )

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.lower_quantile_bps,
            self.upper_quantile_bps,
            self.rule.value,
        )


def _nearest_rank(sorted_values: tuple[Decimal, ...], quantile_bps: int) -> Decimal:
    if not sorted_values:
        raise ResearchResamplingEnvelopeValidationError(
            "empirical quantile requires non-empty values"
        )
    if type(quantile_bps) is not int or not 0 <= quantile_bps <= 10_000:
        raise ResearchResamplingEnvelopeValidationError(
            "quantile_bps must be an integer between 0 and 10000"
        )
    if quantile_bps == 0:
        return sorted_values[0]
    rank = (quantile_bps * len(sorted_values) + 9_999) // 10_000
    return sorted_values[rank - 1]


def _derive_envelope(
    distribution: ResearchBlockBootstrapDistribution,
    policy: ResearchResamplingEnvelopePolicy,
) -> tuple[int, Decimal, Decimal, Decimal]:
    if not isinstance(distribution, ResearchBlockBootstrapDistribution):
        raise ResearchResamplingEnvelopeValidationError(
            "resampling envelope requires ResearchBlockBootstrapDistribution"
        )
    if not isinstance(policy, ResearchResamplingEnvelopePolicy):
        raise ResearchResamplingEnvelopeValidationError(
            "policy must be ResearchResamplingEnvelopePolicy"
        )
    values = distribution.resampled_means
    if not values:
        raise ResearchResamplingEnvelopeValidationError(
            "resampling envelope requires non-empty bootstrap means"
        )
    ordered = tuple(sorted(values))
    return (
        len(ordered),
        _nearest_rank(ordered, policy.lower_quantile_bps),
        _nearest_rank(ordered, 5_000),
        _nearest_rank(ordered, policy.upper_quantile_bps),
    )


@dataclass(frozen=True, slots=True)
class ResearchResamplingEnvelope:
    """Finite resampling envelope over block-bootstrap mean trade returns.

    The envelope is conditional on the exact frozen-OOS sample, serial diagnostic,
    block-bootstrap policy, seed, resample count, and nearest-rank quantile rule.
    It is a descriptive empirical envelope, not a calibrated confidence interval,
    coverage guarantee, p-value, hypothesis test, statistical-significance claim,
    multiple-testing correction, independence proof, or production gate.
    """

    envelope_id: ResearchResamplingEnvelopeId
    distribution: ResearchBlockBootstrapDistribution
    policy: ResearchResamplingEnvelopePolicy
    empirical_sample_size: int
    lower_mean: Decimal
    median_mean: Decimal
    upper_mean: Decimal

    def __post_init__(self) -> None:
        if not isinstance(self.envelope_id, ResearchResamplingEnvelopeId):
            raise ResearchResamplingEnvelopeValidationError(
                "envelope_id must be ResearchResamplingEnvelopeId"
            )
        if not isinstance(self.distribution, ResearchBlockBootstrapDistribution):
            raise ResearchResamplingEnvelopeValidationError(
                "envelope requires ResearchBlockBootstrapDistribution"
            )
        if not isinstance(self.policy, ResearchResamplingEnvelopePolicy):
            raise ResearchResamplingEnvelopeValidationError(
                "envelope requires ResearchResamplingEnvelopePolicy"
            )
        expected = _derive_envelope(self.distribution, self.policy)
        actual = (
            self.empirical_sample_size,
            self.lower_mean,
            self.median_mean,
            self.upper_mean,
        )
        if actual != expected:
            raise ResearchResamplingEnvelopeValidationError(
                "resampling envelope metrics must match bootstrap distribution"
            )
        if not self.lower_mean <= self.median_mean <= self.upper_mean:
            raise ResearchResamplingEnvelopeValidationError(
                "resampling envelope bounds must be ordered"
            )

    @property
    def contains_zero(self) -> bool:
        """Descriptive membership only; this is not a significance decision."""
        return self.lower_mean <= 0 <= self.upper_mean

    def logical_values(self) -> tuple[object, ...]:
        return (
            self.envelope_id.logical_values(),
            self.distribution.logical_values(),
            self.policy.logical_values(),
            self.empirical_sample_size,
            format(self.lower_mean, "f"),
            format(self.median_mean, "f"),
            format(self.upper_mean, "f"),
            self.contains_zero,
        )


def build_research_resampling_envelope(
    *,
    envelope_id: ResearchResamplingEnvelopeId,
    distribution: ResearchBlockBootstrapDistribution,
    policy: ResearchResamplingEnvelopePolicy,
) -> Result[ResearchResamplingEnvelope, ResearchResamplingEnvelopeError]:
    """Build deterministic empirical quantiles without inferential overclaims."""

    try:
        sample_size, lower, median, upper = _derive_envelope(distribution, policy)
        return Success(
            ResearchResamplingEnvelope(
                envelope_id=envelope_id,
                distribution=distribution,
                policy=policy,
                empirical_sample_size=sample_size,
                lower_mean=lower,
                median_mean=median,
                upper_mean=upper,
            )
        )
    except ResearchResamplingEnvelopeError as error:
        return Failure(error)

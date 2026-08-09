from __future__ import annotations

from dataclasses import replace
from decimal import Decimal
from uuid import UUID

import pytest

from qore.infrastructure.research_block_bootstrap import (
    ResearchBlockBootstrapDistribution,
)
from qore.infrastructure.research_resampling_envelope import (
    ResearchResamplingEnvelopeId,
    ResearchResamplingEnvelopePolicy,
    ResearchResamplingEnvelopeValidationError,
    build_research_resampling_envelope,
)
from qore.kernel.result import Success


def _uuid(suffix: int) -> UUID:
    return UUID(f"77000000-0000-0000-0000-{suffix:012d}")


def _distribution(*values: str) -> ResearchBlockBootstrapDistribution:
    distribution = object.__new__(ResearchBlockBootstrapDistribution)
    object.__setattr__(
        distribution,
        "resampled_means",
        tuple(Decimal(value) for value in values),
    )
    return distribution


def test_nearest_rank_quantiles_are_explicit_and_deterministic() -> None:
    distribution = _distribution(
        "10",
        "1",
        "9",
        "2",
        "8",
        "3",
        "7",
        "4",
        "6",
        "5",
    )
    built = build_research_resampling_envelope(
        envelope_id=ResearchResamplingEnvelopeId(_uuid(1)),
        distribution=distribution,
        policy=ResearchResamplingEnvelopePolicy(
            lower_quantile_bps=2_500,
            upper_quantile_bps=7_500,
        ),
    )

    assert isinstance(built, Success)
    envelope = built.value
    assert envelope.empirical_sample_size == 10
    assert envelope.lower_mean == Decimal("3")
    assert envelope.median_mean == Decimal("5")
    assert envelope.upper_mean == Decimal("8")


def test_zero_and_full_quantiles_return_empirical_minimum_and_maximum() -> None:
    built = build_research_resampling_envelope(
        envelope_id=ResearchResamplingEnvelopeId(_uuid(2)),
        distribution=_distribution("0.4", "-0.2", "0.1", "0.3"),
        policy=ResearchResamplingEnvelopePolicy(
            lower_quantile_bps=0,
            upper_quantile_bps=10_000,
        ),
    )

    assert isinstance(built, Success)
    assert built.value.lower_mean == Decimal("-0.2")
    assert built.value.upper_mean == Decimal("0.4")


def test_contains_zero_is_descriptive_membership_only() -> None:
    crosses = build_research_resampling_envelope(
        envelope_id=ResearchResamplingEnvelopeId(_uuid(3)),
        distribution=_distribution("-0.2", "-0.1", "0.1", "0.2"),
        policy=ResearchResamplingEnvelopePolicy(
            lower_quantile_bps=0,
            upper_quantile_bps=10_000,
        ),
    )
    positive = build_research_resampling_envelope(
        envelope_id=ResearchResamplingEnvelopeId(_uuid(4)),
        distribution=_distribution("0.1", "0.2", "0.3", "0.4"),
        policy=ResearchResamplingEnvelopePolicy(
            lower_quantile_bps=0,
            upper_quantile_bps=10_000,
        ),
    )

    assert isinstance(crosses, Success)
    assert isinstance(positive, Success)
    assert crosses.value.contains_zero is True
    assert positive.value.contains_zero is False


def test_policy_rejects_invalid_or_collapsed_quantile_bounds() -> None:
    with pytest.raises(ResearchResamplingEnvelopeValidationError):
        ResearchResamplingEnvelopePolicy(
            lower_quantile_bps=-1,
            upper_quantile_bps=9_750,
        )
    with pytest.raises(ResearchResamplingEnvelopeValidationError):
        ResearchResamplingEnvelopePolicy(
            lower_quantile_bps=2_500,
            upper_quantile_bps=2_500,
        )
    with pytest.raises(ResearchResamplingEnvelopeValidationError):
        ResearchResamplingEnvelopePolicy(
            lower_quantile_bps=2_500,
            upper_quantile_bps=10_001,
        )


def test_envelope_rejects_derived_quantile_tampering() -> None:
    built = build_research_resampling_envelope(
        envelope_id=ResearchResamplingEnvelopeId(_uuid(5)),
        distribution=_distribution("-0.1", "0", "0.1", "0.2"),
        policy=ResearchResamplingEnvelopePolicy(
            lower_quantile_bps=0,
            upper_quantile_bps=10_000,
        ),
    )
    assert isinstance(built, Success)

    with pytest.raises(ResearchResamplingEnvelopeValidationError):
        replace(built.value, lower_mean=Decimal("999"))
    with pytest.raises(ResearchResamplingEnvelopeValidationError):
        replace(built.value, median_mean=Decimal("999"))
    with pytest.raises(ResearchResamplingEnvelopeValidationError):
        replace(built.value, upper_mean=Decimal("999"))


def test_resampling_envelope_makes_no_inferential_or_production_claims() -> None:
    built = build_research_resampling_envelope(
        envelope_id=ResearchResamplingEnvelopeId(_uuid(6)),
        distribution=_distribution("-0.1", "0", "0.1", "0.2"),
        policy=ResearchResamplingEnvelopePolicy(
            lower_quantile_bps=250,
            upper_quantile_bps=9_750,
        ),
    )
    assert isinstance(built, Success)
    envelope = built.value

    assert not hasattr(envelope, "confidence_interval")
    assert not hasattr(envelope, "coverage_probability")
    assert not hasattr(envelope, "p_value")
    assert not hasattr(envelope, "statistically_significant")
    assert not hasattr(envelope, "multiple_testing_corrected")
    assert not hasattr(envelope, "production_ready")

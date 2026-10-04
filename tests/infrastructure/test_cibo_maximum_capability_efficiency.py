from decimal import Decimal

from qore.infrastructure.cibo_maximum_capability_efficiency import (
    CiboMaximumCapabilityEvidence,
    MANDATORY_EFFICIENCY_DIMENSIONS,
    build_maximum_capability_scorecard,
)


def _evidence(value: Decimal = Decimal("1")) -> CiboMaximumCapabilityEvidence:
    return CiboMaximumCapabilityEvidence(
        causal_utility_captured=value,
        causal_utility_available=Decimal("1"),
        realized_value_captured=value,
        realized_value_frontier=Decimal("1"),
        risk_adjusted_utility_captured=value,
        risk_adjusted_utility_frontier=Decimal("1"),
        positive_opportunities_captured=value,
        positive_opportunities_available=Decimal("1"),
        efficient_redeployments=value,
        eligible_redeployments=Decimal("1"),
        optionality_preserved_value=value,
        optionality_frontier_value=Decimal("1"),
        cognitive_value_captured=value,
        cognitive_value_available=Decimal("1"),
        lifecycle_value_captured=value,
        lifecycle_value_frontier=Decimal("1"),
        compound_value_captured=value,
        compound_value_frontier=Decimal("1"),
        portfolio_value_captured=value,
        portfolio_value_frontier=Decimal("1"),
        leverage_value_captured=value,
        leverage_value_frontier=Decimal("1"),
        twin_value_captured=value,
        twin_value_frontier=Decimal("1"),
        t14_redeployed_value=value,
        t14_redeployable_value=Decimal("1"),
    )


def test_9999_requires_every_dimension_at_or_above_target() -> None:
    score = build_maximum_capability_scorecard(_evidence(Decimal("0.9999")))

    assert score.maximum_capability_efficiency == Decimal("0.9999")
    assert score.target_proven is True
    assert tuple(name for name, _ in score.dimensions) == (
        MANDATORY_EFFICIENCY_DIMENSIONS
    )


def test_one_weak_dimension_cannot_be_hidden_by_twelve_perfect_dimensions() -> None:
    evidence = _evidence(Decimal("1"))
    evidence = CiboMaximumCapabilityEvidence(
        **{
            item: getattr(evidence, item)
            for item in evidence.__dataclass_fields__
        }
        | {
            "portfolio_value_captured": Decimal("0.92"),
            "portfolio_value_frontier": Decimal("1"),
        }
    )

    score = build_maximum_capability_scorecard(evidence)

    assert score.maximum_capability_efficiency == Decimal("0.92")
    assert score.target_proven is False
    assert dict(score.dimensions)["PORTFOLIO_EFFICIENCY"] == Decimal("0.92")


def test_scorecard_exposes_each_remaining_gap() -> None:
    score = build_maximum_capability_scorecard(_evidence(Decimal("0.75")))

    assert len(score.gaps) == len(MANDATORY_EFFICIENCY_DIMENSIONS)
    assert all(gap == Decimal("0.25") for _, gap in score.gaps)
    assert score.target_proven is False

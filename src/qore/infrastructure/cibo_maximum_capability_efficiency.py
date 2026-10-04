"""Non-compensatory Maximum Capability efficiency scorecard.

The sovereign efficiency score is intentionally the minimum mandatory
dimension, not a weighted average.  A strong return or one excellent subsystem
therefore cannot hide a weak causal, lifecycle, portfolio, leverage or capital
velocity surface.  99.99% is achieved only when every mandatory dimension is
at least 99.99%.
"""

from __future__ import annotations

from dataclasses import dataclass, fields
from decimal import Decimal

from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)


MANDATORY_EFFICIENCY_DIMENSIONS = (
    "EX_ANTE_CAUSAL_EFFICIENCY",
    "REALIZED_ECONOMIC_CAPTURE",
    "RISK_ADJUSTED_CAPTURE",
    "OPPORTUNITY_CAPTURE_EFFICIENCY",
    "CAPITAL_VELOCITY_EFFICIENCY",
    "OPTIONALITY_EFFICIENCY",
    "COGNITIVE_ACTUATION_EFFICIENCY",
    "POSITION_LIFECYCLE_EFFICIENCY",
    "COMPOUND_EFFICIENCY",
    "PORTFOLIO_EFFICIENCY",
    "LEVERAGE_EFFICIENCY",
    "DIGITAL_TWIN_EFFICIENCY",
    "T14_REDEPLOYMENT_EFFICIENCY",
)


def _ratio(numerator: Decimal, denominator: Decimal, name: str) -> Decimal:
    if (
        not isinstance(numerator, Decimal)
        or not numerator.is_finite()
        or numerator < 0
        or not isinstance(denominator, Decimal)
        or not denominator.is_finite()
        or denominator < 0
    ):
        raise CiboCapitalManagementError(
            f"Maximum Capability {name} inputs must be finite non-negative Decimal"
        )
    if denominator == 0:
        return Decimal(1) if numerator == 0 else Decimal(0)
    return min(Decimal(1), numerator / denominator)


@dataclass(frozen=True, slots=True)
class CiboMaximumCapabilityEvidence:
    causal_utility_captured: Decimal
    causal_utility_available: Decimal
    realized_value_captured: Decimal
    realized_value_frontier: Decimal
    risk_adjusted_utility_captured: Decimal
    risk_adjusted_utility_frontier: Decimal
    positive_opportunities_captured: Decimal
    positive_opportunities_available: Decimal
    efficient_redeployments: Decimal
    eligible_redeployments: Decimal
    optionality_preserved_value: Decimal
    optionality_frontier_value: Decimal
    cognitive_value_captured: Decimal
    cognitive_value_available: Decimal
    lifecycle_value_captured: Decimal
    lifecycle_value_frontier: Decimal
    compound_value_captured: Decimal
    compound_value_frontier: Decimal
    portfolio_value_captured: Decimal
    portfolio_value_frontier: Decimal
    leverage_value_captured: Decimal
    leverage_value_frontier: Decimal
    twin_value_captured: Decimal
    twin_value_frontier: Decimal
    t14_redeployed_value: Decimal
    t14_redeployable_value: Decimal

    def __post_init__(self) -> None:
        for item in fields(self):
            value = getattr(self, item.name)
            if (
                not isinstance(value, Decimal)
                or not value.is_finite()
                or value < 0
            ):
                raise CiboCapitalManagementError(
                    f"Maximum Capability evidence {item.name} must be finite non-negative Decimal"
                )


@dataclass(frozen=True, slots=True)
class CiboMaximumCapabilityScorecard:
    dimensions: tuple[tuple[str, Decimal], ...]
    maximum_capability_efficiency: Decimal
    target_efficiency: Decimal = Decimal("0.9999")

    def __post_init__(self) -> None:
        keys = tuple(name for name, _ in self.dimensions)
        if keys != MANDATORY_EFFICIENCY_DIMENSIONS:
            raise CiboCapitalManagementError(
                "Maximum Capability scorecard dimension identity/order drift"
            )
        for name, value in self.dimensions:
            if value < 0 or value > 1:
                raise CiboCapitalManagementError(
                    f"Maximum Capability {name} outside [0,1]"
                )
        if self.maximum_capability_efficiency != min(
            value for _, value in self.dimensions
        ):
            raise CiboCapitalManagementError(
                "Maximum Capability sovereign score must equal weakest dimension"
            )
        if self.target_efficiency != Decimal("0.9999"):
            raise CiboCapitalManagementError(
                "Maximum Capability target must remain 99.99%"
            )

    @property
    def target_proven(self) -> bool:
        return self.maximum_capability_efficiency >= self.target_efficiency

    @property
    def gaps(self) -> tuple[tuple[str, Decimal], ...]:
        return tuple(
            (name, max(Decimal(0), Decimal(1) - value))
            for name, value in self.dimensions
        )


def build_maximum_capability_scorecard(
    evidence: CiboMaximumCapabilityEvidence,
) -> CiboMaximumCapabilityScorecard:
    """Build a transparent, non-compensatory 99.99% scorecard."""

    if not isinstance(evidence, CiboMaximumCapabilityEvidence):
        raise CiboCapitalManagementError(
            "Maximum Capability requires canonical evidence"
        )
    dimensions = (
        (
            "EX_ANTE_CAUSAL_EFFICIENCY",
            _ratio(
                evidence.causal_utility_captured,
                evidence.causal_utility_available,
                "ex-ante causal",
            ),
        ),
        (
            "REALIZED_ECONOMIC_CAPTURE",
            _ratio(
                evidence.realized_value_captured,
                evidence.realized_value_frontier,
                "realized capture",
            ),
        ),
        (
            "RISK_ADJUSTED_CAPTURE",
            _ratio(
                evidence.risk_adjusted_utility_captured,
                evidence.risk_adjusted_utility_frontier,
                "risk-adjusted capture",
            ),
        ),
        (
            "OPPORTUNITY_CAPTURE_EFFICIENCY",
            _ratio(
                evidence.positive_opportunities_captured,
                evidence.positive_opportunities_available,
                "opportunity capture",
            ),
        ),
        (
            "CAPITAL_VELOCITY_EFFICIENCY",
            _ratio(
                evidence.efficient_redeployments,
                evidence.eligible_redeployments,
                "capital velocity",
            ),
        ),
        (
            "OPTIONALITY_EFFICIENCY",
            _ratio(
                evidence.optionality_preserved_value,
                evidence.optionality_frontier_value,
                "optionality",
            ),
        ),
        (
            "COGNITIVE_ACTUATION_EFFICIENCY",
            _ratio(
                evidence.cognitive_value_captured,
                evidence.cognitive_value_available,
                "cognitive actuation",
            ),
        ),
        (
            "POSITION_LIFECYCLE_EFFICIENCY",
            _ratio(
                evidence.lifecycle_value_captured,
                evidence.lifecycle_value_frontier,
                "position lifecycle",
            ),
        ),
        (
            "COMPOUND_EFFICIENCY",
            _ratio(
                evidence.compound_value_captured,
                evidence.compound_value_frontier,
                "compound",
            ),
        ),
        (
            "PORTFOLIO_EFFICIENCY",
            _ratio(
                evidence.portfolio_value_captured,
                evidence.portfolio_value_frontier,
                "portfolio",
            ),
        ),
        (
            "LEVERAGE_EFFICIENCY",
            _ratio(
                evidence.leverage_value_captured,
                evidence.leverage_value_frontier,
                "leverage",
            ),
        ),
        (
            "DIGITAL_TWIN_EFFICIENCY",
            _ratio(
                evidence.twin_value_captured,
                evidence.twin_value_frontier,
                "digital twin",
            ),
        ),
        (
            "T14_REDEPLOYMENT_EFFICIENCY",
            _ratio(
                evidence.t14_redeployed_value,
                evidence.t14_redeployable_value,
                "T14 redeployment",
            ),
        ),
    )
    return CiboMaximumCapabilityScorecard(
        dimensions=dimensions,
        maximum_capability_efficiency=min(value for _, value in dimensions),
    )

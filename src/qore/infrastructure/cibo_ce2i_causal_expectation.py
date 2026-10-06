"""Causal expectation evidence for CE2I capital decisions.

Expected value is a forecast, not an observed trade outcome.  Any CE2I
competition/allocation decision that consumes expected value must carry the
forecast's evidence identity and as-of timestamp, and the forecast must prove
that it did not consume future market, realized outcome, PnL or post-entry path.

This contract owns no sizing, Risk, order or execution authority.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import StrEnum

from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)


class CausalExpectationBasis(StrEnum):
    """Permitted origins for a pre-decision capital expectation."""

    FROZEN_HISTORICAL_PRIOR = "FROZEN_HISTORICAL_PRIOR"
    CAUSAL_MODEL_FORECAST = "CAUSAL_MODEL_FORECAST"
    CURRENT_STATE_FORECAST = "CURRENT_STATE_FORECAST"


@dataclass(frozen=True, slots=True)
class CausalOpportunityExpectation:
    """Pre-decision forecast consumed by T09/T18 competition."""

    evidence_id: str
    as_of: datetime
    basis: CausalExpectationBasis
    expected_net_value_usd: Decimal
    expected_capital_minutes: Decimal
    future_market_used: bool = False
    outcome_used: bool = False
    pnl_used: bool = False
    post_entry_path_used: bool = False
    sizing_authority: bool = False
    risk_authority: bool = False
    order_authority: bool = False
    execution_authority: bool = False

    def __post_init__(self) -> None:
        if not self.evidence_id:
            raise CiboCapitalManagementError(
                "causal expectation evidence_id is required"
            )
        if self.as_of.tzinfo is None or self.as_of.utcoffset() is None:
            raise CiboCapitalManagementError(
                "causal expectation as_of must be timezone-aware"
            )
        if type(self.basis) is not CausalExpectationBasis:
            raise CiboCapitalManagementError(
                "causal expectation basis must be canonical"
            )
        if (
            not isinstance(self.expected_net_value_usd, Decimal)
            or not self.expected_net_value_usd.is_finite()
        ):
            raise CiboCapitalManagementError(
                "expected_net_value_usd must be finite Decimal"
            )
        if (
            not isinstance(self.expected_capital_minutes, Decimal)
            or not self.expected_capital_minutes.is_finite()
            or self.expected_capital_minutes <= 0
        ):
            raise CiboCapitalManagementError(
                "expected_capital_minutes must be finite positive Decimal"
            )
        for name in (
            "future_market_used",
            "outcome_used",
            "pnl_used",
            "post_entry_path_used",
            "sizing_authority",
            "risk_authority",
            "order_authority",
            "execution_authority",
        ):
            if type(getattr(self, name)) is not bool:
                raise CiboCapitalManagementError(
                    f"causal expectation {name} must be bool"
                )
        if (
            self.future_market_used
            or self.outcome_used
            or self.pnl_used
            or self.post_entry_path_used
        ):
            raise CiboCapitalManagementError(
                "causal expectation cannot consume future/outcome/PnL/post-entry path"
            )
        if (
            self.sizing_authority
            or self.risk_authority
            or self.order_authority
            or self.execution_authority
        ):
            raise CiboCapitalManagementError(
                "causal expectation cannot carry trading authority"
            )


def validate_expectation_before_decision(
    *,
    expectation: CausalOpportunityExpectation,
    decision_as_of: datetime,
) -> None:
    """Fail closed when a forecast was not available at decision time."""

    if not isinstance(expectation, CausalOpportunityExpectation):
        raise CiboCapitalManagementError(
            "expectation must be CausalOpportunityExpectation"
        )
    if decision_as_of.tzinfo is None or decision_as_of.utcoffset() is None:
        raise CiboCapitalManagementError(
            "decision_as_of must be timezone-aware"
        )
    if expectation.as_of > decision_as_of:
        raise CiboCapitalManagementError(
            "causal expectation cannot postdate capital decision"
        )

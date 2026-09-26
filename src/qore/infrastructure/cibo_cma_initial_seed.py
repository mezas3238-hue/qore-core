"""Initial CIBO CMA seed planning and Risk handoff.

This helper is the runtime bridge for the authority switch:
Trader opportunity -> CIBO minimal seed -> CiboRiskRequest.

It intentionally ignores every legacy Trader sizing multiplier or requested
volume. It does not submit broker orders.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from qore.infrastructure.account_wide_risk import CiboRiskRequest
from qore.infrastructure.cibo_capital_management_authority import (
    CapitalAction,
    CiboCapitalActionPlan,
    CiboCapitalManagementError,
    CiboCapitalState,
    TraderOpportunityEnvelope,
    plan_minimal_seed,
)
from qore.infrastructure.cibo_cma_risk_request import build_cma_risk_request


@dataclass(frozen=True, slots=True)
class CmaInitialSeed:
    plan: CiboCapitalActionPlan
    request: CiboRiskRequest


def build_initial_seed_request(
    *,
    request_id: str,
    opportunity: TraderOpportunityEnvelope,
    assigned_capital_usd: Decimal,
    observed_free_margin_usd: Decimal,
    requested_at: datetime,
    expires_at: datetime,
) -> CmaInitialSeed:
    """Create the smallest viable CIBO-owned request for one valid opportunity."""

    for name, value in (
        ("assigned_capital_usd", assigned_capital_usd),
        ("observed_free_margin_usd", observed_free_margin_usd),
    ):
        if not isinstance(value, Decimal) or not value.is_finite() or value < 0:
            raise CiboCapitalManagementError(
                f"{name} must be finite non-negative Decimal"
            )
    if assigned_capital_usd <= 0:
        raise CiboCapitalManagementError("assigned_capital_usd must be positive")
    if expires_at <= requested_at:
        raise CiboCapitalManagementError("expires_at must follow requested_at")

    capital = CiboCapitalState(
        assigned_capital_usd=assigned_capital_usd,
        hard_risk_headroom_usd=assigned_capital_usd,
        margin_headroom_usd=min(
            assigned_capital_usd,
            observed_free_margin_usd,
        ),
        base_capital_at_risk_usd=Decimal(0),
        realized_net_profit_usd=Decimal(0),
        protected_open_economic_floor_usd=Decimal(0),
        proven_self_financing_capacity_usd=Decimal(0),
        reserved_expansion_risk_usd=Decimal(0),
        cost_reserve_usd=Decimal(0),
    )
    plan = plan_minimal_seed(opportunity, capital)
    if plan.action is not CapitalAction.OPEN_MINIMAL_SEED:
        raise CiboCapitalManagementError(
            f"CIBO minimal seed unavailable: {plan.reason}"
        )

    request = build_cma_risk_request(
        request_id=request_id,
        opportunity=opportunity,
        plan=plan,
        requested_at=requested_at,
        expires_at=expires_at,
    )
    return CmaInitialSeed(plan=plan, request=request)

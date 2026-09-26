"""CMA-to-Risk handoff.

CIBO CMA owns the requested volume. This builder converts an already planned
CIBO capital action into the legacy-compatible CiboRiskRequest consumed by the
independent QORE Risk engine. The Trader has no volume input here.
"""

from __future__ import annotations

from datetime import datetime

from qore.infrastructure.account_wide_risk import (
    CiboCapitalProvenanceLot,
    CiboRiskRequest,
)
from qore.infrastructure.cibo_capital_management_authority import (
    CapitalAction,
    CiboCapitalActionPlan,
    CiboCapitalManagementError,
    TraderOpportunityEnvelope,
)


def build_cma_risk_request(
    *,
    request_id: str,
    opportunity: TraderOpportunityEnvelope,
    plan: CiboCapitalActionPlan,
    requested_at: datetime,
    expires_at: datetime,
    capital_source_id: str | None = None,
) -> CiboRiskRequest:
    """Build the Risk request from CIBO-owned volume and Trader-owned geometry."""

    if not request_id:
        raise CiboCapitalManagementError("request_id is required")
    if not isinstance(opportunity, TraderOpportunityEnvelope):
        raise CiboCapitalManagementError("opportunity must be TraderOpportunityEnvelope")
    if not isinstance(plan, CiboCapitalActionPlan):
        raise CiboCapitalManagementError("plan must be CiboCapitalActionPlan")
    if plan.action not in {
        CapitalAction.OPEN_MINIMAL_SEED,
        CapitalAction.EXPAND,
    }:
        raise CiboCapitalManagementError("only capital-deployment plans can reach Risk")
    if plan.trader_id is not opportunity.trader_id:
        raise CiboCapitalManagementError("plan/opportunity trader mismatch")
    if plan.qore_symbol != opportunity.qore_symbol:
        raise CiboCapitalManagementError("plan/opportunity symbol mismatch")

    expected_risk = plan.volume * opportunity.stop_loss_per_volume
    expected_margin = plan.volume * opportunity.margin_per_volume
    if plan.stop_risk_usd != expected_risk:
        raise CiboCapitalManagementError("plan stop risk differs from opportunity economics")
    if plan.margin_usd != expected_margin:
        raise CiboCapitalManagementError("plan margin differs from opportunity economics")

    provenance = _capital_provenance(
        opportunity=opportunity,
        plan=plan,
        capital_source_id=capital_source_id,
    )

    return CiboRiskRequest(
        request_id=request_id,
        trader_id=opportunity.trader_id,
        signal_fingerprint=opportunity.signal_fingerprint,
        qore_symbol=opportunity.qore_symbol,
        provider_symbol=opportunity.provider_symbol,
        side=opportunity.side,
        entry_type=opportunity.entry_type,
        intended_entry=opportunity.intended_entry,
        stop_loss=opportunity.stop_loss,
        take_profit=opportunity.take_profit,
        requested_volume=plan.volume,
        volume_step=opportunity.volume_step,
        minimum_volume=opportunity.minimum_volume,
        stop_loss_per_volume=opportunity.stop_loss_per_volume,
        margin_per_volume=opportunity.margin_per_volume,
        requested_at=requested_at,
        expires_at=expires_at,
        strategy_requested_risk_usd=None,
        minimum_volume_uplifted=False,
        capital_provenance=provenance,
    )



def _capital_provenance(
    *,
    opportunity: TraderOpportunityEnvelope,
    plan: CiboCapitalActionPlan,
    capital_source_id: str | None,
) -> tuple[CiboCapitalProvenanceLot, ...]:
    if plan.capital_source_lots:
        return tuple(
            CiboCapitalProvenanceLot(
                source_kind=item.source.value,
                source_id=item.source_id,
                amount_usd=item.amount_usd,
            )
            for item in plan.capital_source_lots
        )
    if plan.capital_source is None or plan.capital_source_amount_usd <= 0:
        raise CiboCapitalManagementError(
            "capital deployment requires provenance source"
        )
    source_id = capital_source_id or (
        f"cibo:{plan.capital_source.value}:"
        f"{opportunity.trader_id.value}:{opportunity.signal_fingerprint}"
    )
    return (
        CiboCapitalProvenanceLot(
            source_kind=plan.capital_source.value,
            source_id=source_id,
            amount_usd=plan.capital_source_amount_usd,
        ),
    )

"""Bridge legacy Trader requests into volume-free CMA opportunities.

This bridge is transitional. It deliberately discards the legacy Trader-selected
requested volume and strategy risk budget. The remaining geometry/economics become
inputs to CIBO Capital Management Authority.
"""

from __future__ import annotations

from decimal import Decimal

from qore.infrastructure.account_wide_risk import CiboRiskRequest, TraderLineage
from qore.infrastructure.cibo_capital_management_authority import TraderOpportunityEnvelope


ACTIVE_CMA_TRADERS: tuple[TraderLineage, ...] = (
    TraderLineage.VT08_FOREX,
    TraderLineage.R34_XAUUSD,
    TraderLineage.R38_EURUSD,
    TraderLineage.R43_GBPUSD,
    TraderLineage.R38_GBPJPY,
    TraderLineage.R42_AUDJPY,
    TraderLineage.VT31_NAS100,
)

_MINIMUM_EXECUTION_STEPS: dict[TraderLineage, int] = {
    TraderLineage.VT08_FOREX: 1,
    TraderLineage.R34_XAUUSD: 1,
    TraderLineage.R38_EURUSD: 1,
    TraderLineage.R43_GBPUSD: 1,
    TraderLineage.R38_GBPJPY: 1,
    TraderLineage.R42_AUDJPY: 1,
    # Certified VT31 management needs executable quarter legs.
    TraderLineage.VT31_NAS100: 4,
}


def legacy_request_to_cma_opportunity(
    request: CiboRiskRequest,
    *,
    provider_maximum_volume: Decimal,
) -> TraderOpportunityEnvelope:
    """Strip legacy sizing authority while preserving decision-time opportunity facts."""

    if not isinstance(request, CiboRiskRequest):
        raise TypeError("request must be CiboRiskRequest")
    if request.trader_id not in ACTIVE_CMA_TRADERS:
        raise ValueError("Trader lineage is outside active CMA migration scope")
    if (
        not isinstance(provider_maximum_volume, Decimal)
        or not provider_maximum_volume.is_finite()
        or provider_maximum_volume <= 0
    ):
        raise ValueError("provider_maximum_volume must be finite positive Decimal")

    return TraderOpportunityEnvelope(
        trader_id=request.trader_id,
        signal_fingerprint=request.signal_fingerprint,
        qore_symbol=request.qore_symbol,
        provider_symbol=request.provider_symbol,
        side=request.side,
        entry_type=request.entry_type,
        intended_entry=request.intended_entry,
        stop_loss=request.stop_loss,
        take_profit=request.take_profit,
        stop_loss_per_volume=request.stop_loss_per_volume,
        margin_per_volume=request.margin_per_volume,
        volume_step=request.volume_step,
        minimum_volume=request.minimum_volume,
        maximum_volume=provider_maximum_volume,
        minimum_execution_steps=_MINIMUM_EXECUTION_STEPS[request.trader_id],
    )

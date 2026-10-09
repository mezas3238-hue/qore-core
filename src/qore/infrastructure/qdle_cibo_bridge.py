"""Four-engine CIBO -> standalone QDLE adapter, reusable across all Traders.

Market direction and geometry remain Trader-owned; Sizing, CIBO Compound,
Adaptive Leverage and Portfolio Compound supply independent approved caps.
Only QDLE calculates lotage. Execution remains Trader/broker-owned.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from qore.infrastructure.cibo_capital_management_authority import (
    TraderOpportunityEnvelope, minimum_seed_volume,
)
from qore.infrastructure.qore_dynamic_lot_engine import (
    QDLE, QDLEError, QDLEIntent, QDLEResult,
)


@dataclass(frozen=True)
class CiboFourEngineLimits:
    requested_stop_loss_budget_usd: Decimal
    sizing_approved_stop_loss_usd: Decimal
    compound_approved_stop_loss_usd: Decimal
    portfolio_approved_funds_usd: Decimal
    adaptive_leverage_max_broker_lots: Decimal
    adaptive_leverage_margin_budget_usd: Decimal
    slippage_buffer_usd_per_lot: Decimal
    funded_source_lane: str
    account_sequence: int
    requested_target_lots: Decimal | None = None


def reserve_cibo_entry(
    engine: QDLE, opportunity: TraderOpportunityEnvelope,
    limits: CiboFourEngineLimits, now: datetime,
) -> QDLEResult:
    if not isinstance(engine, QDLE) or not isinstance(opportunity, TraderOpportunityEnvelope):
        raise QDLEError("verified QDLE and TraderOpportunityEnvelope required")
    if not isinstance(limits, CiboFourEngineLimits):
        raise QDLEError("four-engine economic authorization required")
    if not isinstance(opportunity.provider_symbol, str) or not opportunity.provider_symbol:
        raise QDLEError("broker symbol must be provided by Trader intent")
    # Signal fingerprint already belongs to Trader; unique per account entry.
    command = QDLEIntent(
        request_id=opportunity.signal_fingerprint,
        trader_id=opportunity.trader_id.value,
        symbol=opportunity.provider_symbol,
        side="BUY" if opportunity.side == "long" else "SELL",
        entry_price=opportunity.intended_entry,
        stop_price=opportunity.stop_loss,
        requested_risk_usd=limits.requested_stop_loss_budget_usd,
        sizing_cap_usd=limits.sizing_approved_stop_loss_usd,
        cibo_compound_cap_usd=limits.compound_approved_stop_loss_usd,
        portfolio_cap_usd=limits.portfolio_approved_funds_usd,
        leverage_cap_lots=limits.adaptive_leverage_max_broker_lots,
        margin_cap_usd=limits.adaptive_leverage_margin_budget_usd,
        source_lane=limits.funded_source_lane,
        slippage_usd_per_lot=limits.slippage_buffer_usd_per_lot,
        expected_account_sequence=limits.account_sequence,
        methodology_min_lots=minimum_seed_volume(opportunity),
        requested_target_lots=limits.requested_target_lots,
    )
    return engine.reserve_for_trader(command, now=now)

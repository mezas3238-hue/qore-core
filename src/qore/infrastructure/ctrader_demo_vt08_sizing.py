"""cTrader DEMO-native sizing for the frozen VT-08 R3.15 Forex methodology.

This module has no FundedNext account-policy dependency.  It converts the
strategy/CIBO risk envelope into broker volume from cTrader DEMO symbol
economics, then emits the canonical CiboRiskRequest consumed by the
CAPITAL_ALLOCATOR_ONLY account path.
"""

from __future__ import annotations

from decimal import Decimal

from qore.infrastructure.account_wide_risk import (
    AccountWideRiskError,
    CiboRiskRequest,
    TraderLineage,
)
from qore.infrastructure.broker_risk_sizing import size_volume_for_risk
from qore.infrastructure.cibo_capital_management_authority import (
    TraderOpportunityEnvelope,
)
from qore.infrastructure.cibo_live_opportunity import build_live_opportunity
from qore.infrastructure.ctrader_demo_compat import CTraderDemoSymbolSpecification
from qore.infrastructure.vt08_forex_cibo_operational import (
    R315_METHOD_FINGERPRINT,
    R315_RISK_FINGERPRINT,
    Vt08ForexCiboAuthorization,
    Vt08ForexCiboDecision,
)

R315_METHODOLOGY_FINGERPRINT = R315_METHOD_FINGERPRINT
R315_RISK_POLICY_FINGERPRINT = R315_RISK_FINGERPRINT
R315_BASE_RISK_BPS = {
    "AUDJPY": Decimal("25"),
    "GBPUSD": Decimal("25"),
    "GBPJPY": Decimal("20"),
}


def build_ctrader_demo_vt08_opportunity(
    *,
    cibo_authorization: Vt08ForexCiboAuthorization,
    provider_spec: CTraderDemoSymbolSpecification,
) -> TraderOpportunityEnvelope:
    """Convert a valid VT08 setup into a volume-free CMA opportunity."""

    if not isinstance(cibo_authorization, Vt08ForexCiboAuthorization):
        raise AccountWideRiskError("explicit VT08 Forex CIBO authorization required")
    if cibo_authorization.decision is not Vt08ForexCiboDecision.ALLOW:
        raise AccountWideRiskError("CIBO denied setup; opportunity forbidden")
    if not isinstance(provider_spec, CTraderDemoSymbolSpecification):
        raise AccountWideRiskError("fresh cTrader DEMO symbol specification is required")

    setup = cibo_authorization.setup
    return build_live_opportunity(
        trader_id=TraderLineage.VT08_FOREX,
        signal_fingerprint=setup.signal_fingerprint,
        qore_symbol=setup.qore_symbol,
        provider_symbol=provider_spec.provider_symbol,
        side=setup.side,
        entry_type=setup.entry_type,
        certified_entry=setup.intended_entry,
        execution_entry=setup.intended_entry,
        stop_loss=setup.stop_loss,
        take_profit=setup.take_profit,
        tick_size=provider_spec.tick_size,
        tick_value=provider_spec.tick_value,
        margin_per_volume=provider_spec.margin_per_volume,
        volume_step=provider_spec.volume_step,
        minimum_volume=provider_spec.minimum_volume,
        maximum_volume=provider_spec.maximum_volume,
        broker_risk_buffer=Decimal("1"),
        commission_per_volume_usd=Decimal("0"),
        maximum_adverse_entry_drift_r=None,
    )


def build_ctrader_demo_vt08_cibo_request(
    *,
    request_id: str,
    cibo_authorization: Vt08ForexCiboAuthorization,
    provider_spec: CTraderDemoSymbolSpecification,
    account_equity: Decimal,
) -> CiboRiskRequest:
    """Convert an explicit VT08/CIBO ALLOW decision into a DEMO request."""

    if not isinstance(cibo_authorization, Vt08ForexCiboAuthorization):
        raise AccountWideRiskError("explicit VT08 Forex CIBO authorization required")
    if cibo_authorization.decision is not Vt08ForexCiboDecision.ALLOW:
        raise AccountWideRiskError("CIBO denied setup; execution request forbidden")
    if not isinstance(provider_spec, CTraderDemoSymbolSpecification):
        raise AccountWideRiskError("fresh cTrader DEMO symbol specification is required")
    if (
        not isinstance(account_equity, Decimal)
        or not account_equity.is_finite()
        or account_equity <= 0
    ):
        raise AccountWideRiskError("assigned DEMO capital must be positive finite Decimal")

    setup = cibo_authorization.setup
    stop_distance = abs(setup.intended_entry - setup.stop_loss)
    ticks = stop_distance / provider_spec.tick_size
    if ticks <= 0:
        raise AccountWideRiskError("stop distance must be positive")
    stop_loss_per_volume = ticks * provider_spec.tick_value
    if stop_loss_per_volume <= 0:
        raise AccountWideRiskError("cTrader DEMO tick economics produced invalid stop risk")

    risk_fraction = R315_BASE_RISK_BPS[setup.qore_symbol] / Decimal("10000")
    monetary_risk = account_equity * risk_fraction
    sizing = size_volume_for_risk(
        requested_risk_usd=monetary_risk,
        stop_loss_per_volume=stop_loss_per_volume,
        volume_step=provider_spec.volume_step,
        minimum_volume=provider_spec.minimum_volume,
        maximum_volume=provider_spec.maximum_volume,
    )

    return CiboRiskRequest(
        request_id=request_id,
        trader_id=TraderLineage.VT08_FOREX,
        signal_fingerprint=setup.signal_fingerprint,
        qore_symbol=setup.qore_symbol,
        provider_symbol=provider_spec.provider_symbol,
        side=setup.side,
        entry_type=setup.entry_type,
        intended_entry=setup.intended_entry,
        stop_loss=setup.stop_loss,
        take_profit=setup.take_profit,
        requested_volume=sizing.authorized_volume,
        volume_step=provider_spec.volume_step,
        minimum_volume=provider_spec.minimum_volume,
        stop_loss_per_volume=stop_loss_per_volume,
        margin_per_volume=provider_spec.margin_per_volume,
        requested_at=setup.decided_at,
        expires_at=setup.expires_at,
        strategy_requested_risk_usd=monetary_risk,
        minimum_volume_uplifted=sizing.minimum_volume_uplifted,
    )

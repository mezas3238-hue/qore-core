"""Broker-exact sizing for the frozen VT-08 R3.15 B_COMBINED Forex contract.

The frozen economic policy is not optimized here. R3.15 certified A-base risk
at 25 bps and GBPJPY-base risk at 20 bps. This adapter accepts only an explicit
CIBO ALLOW decision, converts that envelope into broker volume using fresh MT5
tick economics plus known opening commission, and emits a CiboRiskRequest.
Sovereign account-wide Risk may still reduce or reject the request.
"""

from __future__ import annotations

from decimal import ROUND_FLOOR, Decimal

from qore.infrastructure.account_wide_risk import (
    AccountWideRiskError,
    CiboRiskRequest,
    TraderLineage,
)
from qore.infrastructure.fundednext_live_guard import FOREX_OPEN_COMMISSION_PER_LOT_USD
from qore.infrastructure.fundednext_mt5 import Mt5SymbolSpecification
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


def build_certified_vt08_forex_cibo_request(
    *,
    request_id: str,
    cibo_authorization: Vt08ForexCiboAuthorization,
    provider_spec: Mt5SymbolSpecification,
    account_equity: Decimal,
) -> CiboRiskRequest:
    """Convert one explicit CIBO ALLOW decision into broker-exact Risk request."""

    if not isinstance(cibo_authorization, Vt08ForexCiboAuthorization):
        raise AccountWideRiskError("explicit VT08 Forex CIBO authorization required")
    if cibo_authorization.decision is not Vt08ForexCiboDecision.ALLOW:
        raise AccountWideRiskError("CIBO denied setup; Risk request forbidden")
    setup = cibo_authorization.setup
    if not isinstance(provider_spec, Mt5SymbolSpecification):
        raise AccountWideRiskError("fresh MT5 symbol specification is required")
    if (
        not isinstance(account_equity, Decimal)
        or not account_equity.is_finite()
        or account_equity <= 0
    ):
        raise AccountWideRiskError("account equity must be positive finite Decimal")

    stop_distance = abs(setup.intended_entry - setup.stop_loss)
    ticks = stop_distance / provider_spec.tick_size
    if ticks <= 0:
        raise AccountWideRiskError("stop distance must be positive")
    price_stop_loss_per_volume = ticks * provider_spec.tick_value
    stop_loss_per_volume = (
        price_stop_loss_per_volume + FOREX_OPEN_COMMISSION_PER_LOT_USD
    )
    if stop_loss_per_volume <= 0:
        raise AccountWideRiskError("MT5 tick economics produced invalid stop risk")

    risk_fraction = R315_BASE_RISK_BPS[setup.qore_symbol] / Decimal("10000")
    monetary_risk = account_equity * risk_fraction
    raw_volume = monetary_risk / stop_loss_per_volume
    volume = _floor_to_step(raw_volume, provider_spec.volume_step)
    volume = min(volume, provider_spec.maximum_volume)
    if volume < provider_spec.minimum_volume:
        raise AccountWideRiskError("certified risk is below broker minimum volume")

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
        requested_volume=volume,
        volume_step=provider_spec.volume_step,
        minimum_volume=provider_spec.minimum_volume,
        stop_loss_per_volume=stop_loss_per_volume,
        margin_per_volume=provider_spec.margin_per_volume,
        requested_at=setup.decided_at,
        expires_at=setup.expires_at,
    )


def _floor_to_step(value: Decimal, step: Decimal) -> Decimal:
    if value < 0 or step <= 0:
        raise AccountWideRiskError("volume/step geometry is invalid")
    units = (value / step).to_integral_value(rounding=ROUND_FLOOR)
    return units * step

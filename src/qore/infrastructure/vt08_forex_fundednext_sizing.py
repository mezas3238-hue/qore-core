"""Broker-exact sizing for the frozen VT-08 R3.15 B_COMBINED Forex contract.

The frozen economic policy is not optimized here. R3.15 certified A-base risk
at 25 bps and GBPJPY-base risk at 20 bps. This adapter converts that monetary
risk envelope into broker volume using fresh MT5 tick economics and emits only a
CiboRiskRequest; sovereign account-wide Risk may still reduce or reject it.
"""

from __future__ import annotations

from datetime import datetime
from decimal import ROUND_FLOOR, Decimal

from qore.infrastructure.account_wide_risk import (
    AccountWideRiskError,
    CiboRiskRequest,
    TraderLineage,
)
from qore.infrastructure.fundednext_mt5 import Mt5SymbolSpecification
from qore.infrastructure.fundednext_operational import VT08_FOREX_RETAINED_MARKETS

R315_METHODOLOGY_FINGERPRINT = (
    "0c3fe8e1353386f7384a8532c7fe71bbbe9fcfdf1da7530be4b53e01bc59de0d"
)
R315_RISK_POLICY_FINGERPRINT = (
    "dfb3fc8217b9895356ed19f8d7e1ee47fae765d39a9bb2e72e14c4ac41fad1f5"
)
R315_BASE_RISK_BPS = {
    "AUDJPY": Decimal("25"),
    "GBPUSD": Decimal("25"),
    "GBPJPY": Decimal("20"),
}


def build_certified_vt08_forex_cibo_request(
    *,
    request_id: str,
    signal_fingerprint: str,
    methodology_fingerprint: str,
    risk_policy_fingerprint: str,
    qore_symbol: str,
    provider_spec: Mt5SymbolSpecification,
    side: str,
    entry_type: str,
    intended_entry: Decimal,
    stop_loss: Decimal,
    take_profit: Decimal,
    account_equity: Decimal,
    requested_at: datetime,
    expires_at: datetime,
) -> CiboRiskRequest:
    """Convert frozen R3.15 risk bps into exact MT5 lot volume."""

    if qore_symbol not in VT08_FOREX_RETAINED_MARKETS:
        raise AccountWideRiskError("VT08 Forex market is outside frozen B_COMBINED")
    if methodology_fingerprint != R315_METHODOLOGY_FINGERPRINT:
        raise AccountWideRiskError("VT08 Forex methodology fingerprint mismatch")
    if risk_policy_fingerprint != R315_RISK_POLICY_FINGERPRINT:
        raise AccountWideRiskError("VT08 Forex Risk policy fingerprint mismatch")
    if not isinstance(provider_spec, Mt5SymbolSpecification):
        raise AccountWideRiskError("fresh MT5 symbol specification is required")
    if (
        not isinstance(account_equity, Decimal)
        or not account_equity.is_finite()
        or account_equity <= 0
    ):
        raise AccountWideRiskError("account equity must be positive finite Decimal")
    if entry_type not in {"market", "limit"}:
        raise AccountWideRiskError("entry type must already be resolved upstream")
    if side not in {"long", "short"}:
        raise AccountWideRiskError("side must be long or short")
    if side == "long" and not stop_loss < intended_entry < take_profit:
        raise AccountWideRiskError("long geometry must be stop < entry < target")
    if side == "short" and not take_profit < intended_entry < stop_loss:
        raise AccountWideRiskError("short geometry must be target < entry < stop")

    stop_distance = abs(intended_entry - stop_loss)
    ticks = stop_distance / provider_spec.tick_size
    if ticks <= 0:
        raise AccountWideRiskError("stop distance must be positive")
    stop_loss_per_volume = ticks * provider_spec.tick_value
    if stop_loss_per_volume <= 0:
        raise AccountWideRiskError("MT5 tick economics produced invalid stop risk")

    risk_fraction = R315_BASE_RISK_BPS[qore_symbol] / Decimal("10000")
    monetary_risk = account_equity * risk_fraction
    raw_volume = monetary_risk / stop_loss_per_volume
    volume = _floor_to_step(raw_volume, provider_spec.volume_step)
    volume = min(volume, provider_spec.maximum_volume)
    if volume < provider_spec.minimum_volume:
        raise AccountWideRiskError("certified risk is below broker minimum volume")

    return CiboRiskRequest(
        request_id=request_id,
        trader_id=TraderLineage.VT08_FOREX,
        signal_fingerprint=signal_fingerprint,
        qore_symbol=qore_symbol,
        provider_symbol=provider_spec.provider_symbol,
        side=side,
        entry_type=entry_type,
        intended_entry=intended_entry,
        stop_loss=stop_loss,
        take_profit=take_profit,
        requested_volume=volume,
        volume_step=provider_spec.volume_step,
        minimum_volume=provider_spec.minimum_volume,
        stop_loss_per_volume=stop_loss_per_volume,
        margin_per_volume=provider_spec.margin_per_volume,
        requested_at=requested_at,
        expires_at=expires_at,
    )


def _floor_to_step(value: Decimal, step: Decimal) -> Decimal:
    if value < 0 or step <= 0:
        raise AccountWideRiskError("volume/step geometry is invalid")
    units = (value / step).to_integral_value(rounding=ROUND_FLOOR)
    return units * step

"""FundedNext MT5 provider facts for CIBO-owned sizing.

This adapter adds certified opening commission to the raw MT5 specification.
It contains no Trader risk fraction and chooses no volume.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from qore.infrastructure.account_wide_risk import AccountWideRiskError, TraderLineage
from qore.infrastructure.cibo_capital_management_authority import (
    TraderOpportunityEnvelope,
)
from qore.infrastructure.cibo_live_opportunity import build_live_opportunity
from qore.infrastructure.fundednext_mt5 import Mt5SymbolSpecification
from qore.infrastructure.fundednext_stellar_instant import (
    opening_commission_per_lot,
)
from qore.infrastructure.vt08_forex_cibo_operational import (
    Vt08ForexCiboAuthorization,
    Vt08ForexCiboDecision,
)


@dataclass(frozen=True, slots=True)
class FundedNextCiboSymbolSpecification:
    provider_symbol: str
    bid: Decimal
    ask: Decimal
    spread_points: Decimal
    digits: int
    point: Decimal
    contract_size: Decimal
    tick_size: Decimal
    tick_value: Decimal
    minimum_volume: Decimal
    maximum_volume: Decimal
    volume_step: Decimal
    minimum_stop_distance_points: Decimal
    freeze_level_points: Decimal
    margin_per_volume: Decimal
    trade_enabled: bool
    session_open: bool
    observed_at: datetime
    open_commission_per_lot_usd: Decimal


def fundednext_cibo_symbol_spec(
    *,
    qore_symbol: str,
    side: str,
    spec: Mt5SymbolSpecification,
) -> FundedNextCiboSymbolSpecification:
    """Attach official FundedNext commission to fresh MT5 broker facts."""

    if not isinstance(spec, Mt5SymbolSpecification):
        raise AccountWideRiskError(
            "fresh FundedNext MT5 symbol specification is required"
        )
    if side not in {"long", "short"}:
        raise AccountWideRiskError("side must be long/short")
    executable = spec.ask if side == "long" else spec.bid
    commission = opening_commission_per_lot(
        qore_symbol,
        executable_entry=executable,
        contract_size=spec.contract_size,
    )
    return FundedNextCiboSymbolSpecification(
        provider_symbol=spec.provider_symbol,
        bid=spec.bid,
        ask=spec.ask,
        spread_points=spec.spread_points,
        digits=spec.digits,
        point=spec.point,
        contract_size=spec.contract_size,
        tick_size=spec.tick_size,
        tick_value=spec.tick_value,
        minimum_volume=spec.minimum_volume,
        maximum_volume=spec.maximum_volume,
        volume_step=spec.volume_step,
        minimum_stop_distance_points=spec.minimum_stop_distance_points,
        freeze_level_points=spec.freeze_level_points,
        margin_per_volume=spec.margin_per_volume,
        trade_enabled=spec.trade_enabled,
        session_open=spec.session_open,
        observed_at=spec.observed_at,
        open_commission_per_lot_usd=commission,
    )


def build_fundednext_vt08_opportunity(
    *,
    cibo_authorization: Vt08ForexCiboAuthorization,
    provider_spec: Mt5SymbolSpecification,
) -> TraderOpportunityEnvelope:
    """Convert VT08 methodology facts into a volume-free FundedNext opportunity."""

    if not isinstance(cibo_authorization, Vt08ForexCiboAuthorization):
        raise AccountWideRiskError(
            "explicit VT08 Forex CIBO authorization required"
        )
    if cibo_authorization.decision is not Vt08ForexCiboDecision.ALLOW:
        raise AccountWideRiskError(
            "CIBO denied VT08 setup; opportunity forbidden"
        )
    setup = cibo_authorization.setup
    normalized = fundednext_cibo_symbol_spec(
        qore_symbol=setup.qore_symbol,
        side=setup.side,
        spec=provider_spec,
    )
    executable = (
        normalized.ask if setup.side == "long" else normalized.bid
    )
    return build_live_opportunity(
        trader_id=TraderLineage.VT08_FOREX,
        signal_fingerprint=setup.signal_fingerprint,
        qore_symbol=setup.qore_symbol,
        provider_symbol=normalized.provider_symbol,
        side=setup.side,
        entry_type=setup.entry_type,
        certified_entry=setup.intended_entry,
        execution_entry=executable,
        stop_loss=setup.stop_loss,
        take_profit=setup.take_profit,
        tick_size=normalized.tick_size,
        tick_value=normalized.tick_value,
        margin_per_volume=normalized.margin_per_volume,
        volume_step=normalized.volume_step,
        minimum_volume=normalized.minimum_volume,
        maximum_volume=normalized.maximum_volume,
        broker_risk_buffer=Decimal("1"),
        commission_per_volume_usd=normalized.open_commission_per_lot_usd,
        maximum_adverse_entry_drift_r=None,
    )

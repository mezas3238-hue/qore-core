"""CIBO H28: broker-legal exact stop-dollar sizing, no change to CIBO strategy.

Research-only sizing adapter. A real allocation MUST be rejected if USD3 stop
is not expressible in legal lot increments, cannot be funded at exchange
margin, or exceeds actual risk/sovereign cash. It never fabricates a fill or
changes any Trader decision, entry, cognitive mode, or position exit.
"""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal as D, ROUND_CEILING, ROUND_FLOOR, ROUND_HALF_UP


@dataclass(frozen=True)
class BrokerLotContract:
    min_lots: D
    lot_step: D
    max_lots: D
    stop_risk_usd_per_lot: D
    margin_usd_per_lot: D
    roundtrip_fee_usd_per_lot: D = D(0)


@dataclass(frozen=True)
class ExactStopSizing:
    accepted: bool
    reason: str
    target_at_stop_usd: D
    lots: D
    actual_stop_usd: D
    fee_usd: D
    margin_usd: D
    lower_attainable_stop_usd: D
    upper_attainable_stop_usd: D


def plan_exact_stop(
    *,
    capital_usd: D,
    target_at_stop_usd: D,
    available_unreserved_cash_usd: D,
    contract: BrokerLotContract,
    penny_precision: D = D("0.005"),
) -> ExactStopSizing:
    """Determine legally representable exact stop dollars or explicitly fail.

    Precision is HALF a cent: output dollar stop displays USD3.00.
    It never treats fees as part of user stop risk. Fees/margin must ALSO
    fit available liquidity. If funds are constrained, do not scale silently.
    """
    numbers = [
        capital_usd,target_at_stop_usd,available_unreserved_cash_usd,
        contract.min_lots,contract.lot_step,contract.max_lots,
        contract.stop_risk_usd_per_lot,contract.margin_usd_per_lot,
        contract.roundtrip_fee_usd_per_lot,penny_precision,
    ]
    if any(not isinstance(v,D) or not v.is_finite() for v in numbers):
        raise ValueError("all amounts must be finite Decimal values")
    if capital_usd<=0 or target_at_stop_usd<=0 or available_unreserved_cash_usd<0:
        raise ValueError("invalid bankroll/stop/cash")
    if any(v<=0 for v in [contract.min_lots,contract.lot_step,contract.max_lots,contract.stop_risk_usd_per_lot]):
        raise ValueError("invalid legal volume and stop unit")
    if contract.min_lots>contract.max_lots or contract.margin_usd_per_lot<0 or contract.roundtrip_fee_usd_per_lot<0 or penny_precision<0:
        raise ValueError("invalid limits/costs")
    # Real broker volume set is min_lots + k * lot_step, not arbitrary quantity.
    raw=(target_at_stop_usd/contract.stop_risk_usd_per_lot-contract.min_lots)/contract.lot_step
    lower_k=max(0,int(raw.to_integral_value(rounding=ROUND_FLOOR)))
    upper_k=max(0,int(raw.to_integral_value(rounding=ROUND_CEILING)))
    lower_lots=contract.min_lots+D(lower_k)*contract.lot_step
    upper_lots=contract.min_lots+D(upper_k)*contract.lot_step
    # A stop below the legal minimum is an immediate failure, with no fill.
    lower_risk=lower_lots*contract.stop_risk_usd_per_lot
    upper_risk=upper_lots*contract.stop_risk_usd_per_lot
    candidates=[lower_lots,upper_lots]
    candidates=[q for q in candidates if contract.min_lots<=q<=contract.max_lots and abs(q*contract.stop_risk_usd_per_lot-target_at_stop_usd)<=penny_precision]
    candidates.sort(key=lambda q:(abs(q*contract.stop_risk_usd_per_lot-target_at_stop_usd),q))
    if not candidates:
        return ExactStopSizing(False,"EXACT_STOP_NOT_REPRESENTABLE_IN_BROKER_LOT_STEPS",target_at_stop_usd,D(0),D(0),D(0),D(0),lower_risk,upper_risk)
    lots=candidates[0]
    stop=lots*contract.stop_risk_usd_per_lot
    margin=lots*contract.margin_usd_per_lot
    fee=lots*contract.roundtrip_fee_usd_per_lot
    # Explicit risk ceiling at start, interpreted as 5% stop risk, not fees.
    if stop > capital_usd*D(".05")+penny_precision:
        return ExactStopSizing(False,"STOP_EXCEEDS_5PCT_CURRENT_CAPITAL",target_at_stop_usd,D(0),D(0),D(0),D(0),lower_risk,upper_risk)
    if available_unreserved_cash_usd<margin+fee:
        return ExactStopSizing(False,"MARGIN_AND_FEES_NOT_FUNDED_WITH_UNRESERVED_CASH",target_at_stop_usd,D(0),D(0),D(0),D(0),lower_risk,upper_risk)
    return ExactStopSizing(True,"EXACT_STOP_RISK_FUNDED",target_at_stop_usd,lots,stop,fee,margin,lower_risk,upper_risk)

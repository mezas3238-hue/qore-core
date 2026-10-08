"""Research-only four independent proposals -> QDLEIntent contract; never SEND."""
from __future__ import annotations

from decimal import Decimal

from qore.infrastructure.cibo_four_motor_policy import (
    FourMotorObservation,
    FourMotorPolicyError,
    FourMotorProposal,
    nonnegative,
)
from qore.infrastructure.qore_dynamic_lot_engine import QDLEIntent


def build_four_motor_qdle_intent(*, observation: FourMotorObservation,
                                 votes: tuple[FourMotorProposal, ...],
                                 entry_price: Decimal, stop_price: Decimal,
                                 methodology_min_lots: Decimal = Decimal(0)) -> QDLEIntent:
    """Build economic caps: QDLE+Treasury still sign, verify, reserve and send."""
    if not isinstance(observation, FourMotorObservation):
        raise FourMotorPolicyError("causal economic observation required")
    if not isinstance(votes, tuple) or len(votes) != 4:
        raise FourMotorPolicyError("four motor votes required")
    by_name = {v.producer: v for v in votes if isinstance(v, FourMotorProposal)}
    if len(by_name) != 4 or set(by_name) != {
        "SIZING", "CIBO_COMPOUND", "ADAPTIVE_LEVERAGE", "PORTFOLIO_COMPOUND"
    }:
        raise FourMotorPolicyError("independent four motor votes required")
    if any(v.observation != observation for v in votes):
        raise FourMotorPolicyError("cross-epoch motor approval not permitted")
    for name, x in (("entry_price", entry_price), ("stop_price", stop_price)):
        if not isinstance(x, Decimal) or not x.is_finite() or x <= 0:
            raise FourMotorPolicyError(f"{name} must be positive finite")
    nonnegative("methodology_min_lots", methodology_min_lots)
    return QDLEIntent(
        request_id=observation.request_id, trader_id=observation.trader_id,
        symbol=observation.symbol, side=observation.side,
        entry_price=entry_price, stop_price=stop_price,
        requested_risk_usd=observation.base_entry_budget_usd,
        sizing_cap_usd=Decimal(by_name["SIZING"].limits["approved_risk_usd"]),
        cibo_compound_cap_usd=Decimal(by_name["CIBO_COMPOUND"].limits["approved_risk_usd"]),
        portfolio_cap_usd=Decimal(by_name["PORTFOLIO_COMPOUND"].limits["approved_source_funds_usd"]),
        leverage_cap_lots=Decimal(by_name["ADAPTIVE_LEVERAGE"].limits["approved_max_lots"]),
        margin_cap_usd=Decimal(by_name["ADAPTIVE_LEVERAGE"].limits["approved_margin_usd"]),
        source_lane=observation.source_lane,
        slippage_usd_per_lot=observation.execution_buffer_usd_per_lot,
        expected_account_sequence=observation.account_sequence,
        methodology_min_lots=methodology_min_lots,
    )

"""P0 SHADOW cross-architect bridge: causal CIBO state -> 4 votes -> QDLE.

This is NOT an authenticated CIBO decision feed, a broker adapter, or SEND
authority. All inputs must arrive from independently governed producers.
No fake deal/fill/fee or settled NAV is created here.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from qore.infrastructure.cibo_trade_ops_director import (
    Stage, TradeOpsError, TradeOpsEvent, TradeOpsState, apply_trade_event,
)
from qore.infrastructure.cibo_account_sizing_authority import propose_p0_sizing_vote
from qore.infrastructure.cibo_compound_capital import propose_p0_compound_vote
from qore.infrastructure.cibo_core_compound_portfolio import propose_p0_portfolio_vote
from qore.infrastructure.cibo_marginal_leverage_utility import propose_p0_adaptive_leverage_vote
from qore.infrastructure.cibo_four_motor_policy import FourMotorObservation, FourMotorProposal
from qore.infrastructure.qdle_cibo_authority import (
    CiboEconomicInstruction, CiboLotageAuditReceipt,
    audit_cibo_qdle_lotage, build_cibo_directed_qdle_intent,
)
from qore.infrastructure.qore_dynamic_lot_engine import QDLEIntent, QDLEResult


@dataclass(frozen=True, slots=True)
class PreparedShadowDecision:
    """Auditable preparation only; does not reserve volume or submit orders."""
    state: TradeOpsState
    cibo: CiboEconomicInstruction
    observation: FourMotorObservation
    votes: tuple[FourMotorProposal, ...]
    intent: QDLEIntent
    is_live_authorized: bool = False


def prepare_shadow_economic_decision(
    *, state: TradeOpsState, cibo: CiboEconomicInstruction,
    observation: FourMotorObservation,
) -> PreparedShadowDecision:
    """Join EXACT SAME signal and chronology; never let QDLE invent CIBO votes.

    Upstream provenance/authentication and actual funding are still obligatory;
    a syntactically valid SHA256 alone is not broker or CIBO authorization.
    """
    if type(state) is not TradeOpsState or state.stage is not Stage.ECONOMICALLY_VALUED:
        raise TradeOpsError("CIBO lifecycle must be economically valued first")
    if not isinstance(cibo, CiboEconomicInstruction) or not isinstance(
        observation, FourMotorObservation
    ):
        raise TradeOpsError("explicit CIBO and broker-backed four-motor input required")
    identity = (state.signal_id, state.trader_id, state.symbol, state.side)
    if identity != (cibo.signal_id, cibo.trader_id, cibo.symbol, cibo.side):
        raise TradeOpsError("CIBO direction and Trader event identity mismatch")
    if identity != (observation.request_id, observation.trader_id,
                    observation.symbol, observation.side):
        raise TradeOpsError("four motor broker observation identity mismatch")
    if observation.observed_at < state.last_at or cibo.issued_at < state.last_at:
        raise TradeOpsError("decision must not predate economically valued Trader event")
    votes = (
        propose_p0_sizing_vote(observation),
        propose_p0_compound_vote(observation),
        propose_p0_adaptive_leverage_vote(observation),
        propose_p0_portfolio_vote(observation),
    )
    intent = build_cibo_directed_qdle_intent(
        cibo=cibo, observation=observation, votes=votes,
    )
    return PreparedShadowDecision(state, cibo, observation, votes, intent)


@dataclass(frozen=True, slots=True)
class ShadowFundingOutcome:
    state: TradeOpsState
    receipt: CiboLotageAuditReceipt
    real_mt5_fill_proven: bool = False


def record_shadow_qdle_result(
    *, prepared: PreparedShadowDecision, result: QDLEResult,
    broker_min_lot: Decimal, broker_lot_step: Decimal,
    event_id: str, event_at: datetime,
) -> ShadowFundingOutcome:
    """Turn broker-grid reservation into funded/unfundable CIBO event, never fill.

    The QDLE reserve_for_trader call must happen on the owner-managed QDLE
    instance before this function. Only QDLE may compute physical volume.
    """
    if type(prepared) is not PreparedShadowDecision or prepared.is_live_authorized:
        raise TradeOpsError("SHADOW prepared decision required")
    if not isinstance(event_at, datetime) or event_at.tzinfo is None:
        raise TradeOpsError("funding event must have timezone-aware timestamp")
    if event_at < prepared.observation.observed_at:
        raise TradeOpsError("funding event cannot predate its economic observation")
    receipt = audit_cibo_qdle_lotage(
        cibo=prepared.cibo, observation=prepared.observation,
        votes=prepared.votes, result=result,
        broker_min_lot=broker_min_lot, broker_lot_step=broker_lot_step,
    )
    stage = Stage.ECONOMICALLY_FUNDED if receipt.lots > 0 else Stage.UNFUNDABLE
    evt = TradeOpsEvent(
        event_id=event_id, signal_id=prepared.state.signal_id,
        trader_id=prepared.state.trader_id, symbol=prepared.state.symbol,
        side=prepared.state.side, stage=stage, occurred_at=event_at,
        evidence_as_of=prepared.observation.observed_at,
        evidence_sha256=prepared.cibo.evidence_sha256,
        reason="QDLE_RESERVED_SHADOW_NOT_BROKER_EXECUTED"
        if receipt.lots > 0 else "QDLE_UNFUNDABLE_SHADOW",
        requested_lots=receipt.lots if receipt.lots > 0 else None,
    )
    return ShadowFundingOutcome(apply_trade_event(prepared.state, evt), receipt)


def administer_native_cibo_qdle_shadow(
    *, state: TradeOpsState, native_receipt: dict,
    cibo: CiboEconomicInstruction, observation: FourMotorObservation,
    qdle: "QDLE", event_id: str, at: datetime,
    broker_min_lot: Decimal, broker_lot_step: Decimal,
) -> "SovereignNativeQdleShadowOutcome":
    """Canonical CIBO Soberano P0 entrypoint for the Native MAX / QDLE bridge.

    A single request crosses Native cognitive management -> four independent
    economics -> physical QDLE -> CIBO lifecycle funding receipt. This direct
    wrapper intentionally imports the Native adapter lazily to prevent a
    circular module dependency; still NO SEND, NO broker fill, NO NAV credit.
    """
    from qore.infrastructure.cibo_native_sovereign_qdle import (
        administer_native_sovereign_qdle_shadow,
    )
    return administer_native_sovereign_qdle_shadow(
        state=state, native_receipt=native_receipt,
        cibo=cibo, observation=observation, qdle=qdle,
        event_id=event_id, at=at,
        broker_min_lot=broker_min_lot, broker_lot_step=broker_lot_step,
    )

"""CIBO-first economic authority -> QDLE physical lotage (RESEARCH boundary).

CIBO and the four economic producers decide budgets, lane and management.
QDLE is *only* the translator to broker-legal volume. No autonomous exit,
selection, allocation, entry, order_send or invented CIBO strategy.

CIBO directions are separate from proof of authenticated LIVE producer signing.
Broker funding still requires QDLE snapshot, independent votes and treasury gates.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, replace
from datetime import datetime, timezone
from decimal import Decimal, localcontext

from qore.infrastructure.cibo_four_motor_policy import (
    FourMotorObservation, FourMotorProposal, FourMotorPolicyError, nonnegative, positive, utc,
)
from qore.infrastructure.cibo_four_motor_qdle_proposal import build_four_motor_qdle_intent
from qore.infrastructure.qore_dynamic_lot_engine import QDLEIntent, QDLEResult


_SHA = re.compile(r"^sha256:[a-f0-9]{64}$")


@dataclass(frozen=True, slots=True)
class CiboEconomicInstruction:
    """Explicit CIBO direction. Source money != loss authorization.

    allocated_source_funds_usd = funds assigned to a Trader/strategy by CIBO
    authorized_all_in_risk_usd = loss limit including both commissions
    maximum_requested_lots = preferred/maximum physical lots, NOT permission
                             to override independent motors or broker limits
    Broker-verified fill/management/exit instructions are separate contracts.
    """
    signal_id: str
    trader_id: str
    symbol: str
    side: str
    entry_price: Decimal
    stop_price: Decimal
    source_lane: str
    allocated_source_funds_usd: Decimal
    authorized_all_in_risk_usd: Decimal
    maximum_requested_lots: Decimal | None
    account_sequence: int
    issued_at: datetime
    evidence_sha256: str

    def __post_init__(self) -> None:
        if not all(isinstance(x, str) and x for x in (
            self.signal_id, self.trader_id, self.symbol
        )):
            raise FourMotorPolicyError("CIBO signal/trader/symbol required")
        if self.side not in {"BUY", "SELL"}:
            raise FourMotorPolicyError("CIBO side invalid")
        if self.source_lane not in {"SOVEREIGN_BANK", "PORTFOLIO_CUSHION"}:
            raise FourMotorPolicyError("CIBO allocation source missing or invalid")
        if type(self.account_sequence) is not int or self.account_sequence <= 0:
            raise FourMotorPolicyError("CIBO account sequence invalid")
        utc("CIBO issued_at", self.issued_at)
        if not isinstance(self.evidence_sha256, str) or not _SHA.fullmatch(self.evidence_sha256):
            raise FourMotorPolicyError("CIBO instruction source SHA256 required")
        for name in ("entry_price", "stop_price", "allocated_source_funds_usd",
                     "authorized_all_in_risk_usd"):
            nonnegative(name, getattr(self, name))
        if self.entry_price == 0 or self.stop_price == 0 or self.entry_price == self.stop_price:
            raise FourMotorPolicyError("CIBO price/stop invalid")
        if self.side == "BUY" and self.stop_price >= self.entry_price:
            raise FourMotorPolicyError("CIBO BUY stop invalid")
        if self.side == "SELL" and self.stop_price <= self.entry_price:
            raise FourMotorPolicyError("CIBO SELL stop invalid")
        if self.maximum_requested_lots is not None:
            nonnegative("maximum_requested_lots", self.maximum_requested_lots)
            if self.maximum_requested_lots == 0:
                raise FourMotorPolicyError("zero CIBO target volume is not a valid intent")


def build_cibo_directed_qdle_intent(
    *, cibo: CiboEconomicInstruction, observation: FourMotorObservation,
    votes: tuple[FourMotorProposal, ...], methodology_min_lots: Decimal = Decimal(0),
) -> QDLEIntent:
    """Consume CIBO direction, NEVER substitute a simulator-selected budget or lane.

    Independent Sizing/Compound/Portfolio/Leverage votes and treasury are
    restrictive authorities, not a source of extra capital. CIBO's economic
    source is not the entire account and is never silently fungible.
    """
    if not isinstance(cibo, CiboEconomicInstruction):
        raise FourMotorPolicyError("independent CIBO instruction required")
    if not isinstance(observation, FourMotorObservation):
        raise FourMotorPolicyError("causal economic observation required")
    if (cibo.signal_id, cibo.trader_id, cibo.symbol, cibo.side, cibo.source_lane,
            cibo.account_sequence) != (
            observation.request_id, observation.trader_id, observation.symbol,
            observation.side, observation.source_lane, observation.account_sequence):
        raise FourMotorPolicyError("CIBO identity, lane or epoch mismatches four motors")
    if utc("CIBO issued_at", cibo.issued_at) != utc("four motor observed_at", observation.observed_at):
        raise FourMotorPolicyError("CIBO and motors must share economic epoch")
    if cibo.authorized_all_in_risk_usd > observation.base_entry_budget_usd:
        raise FourMotorPolicyError("CIBO requests risk above dynamic QORE 5pct")
    # Allocate money for ATTACK/other strategies, not a risk multiplier.
    source = observation.source_available_usd
    if cibo.allocated_source_funds_usd > source:
        raise FourMotorPolicyError("CIBO allocated unbacked portfolio capital")
    target = build_four_motor_qdle_intent(
        observation=observation, votes=votes,
        entry_price=cibo.entry_price, stop_price=cibo.stop_price,
        methodology_min_lots=methodology_min_lots,
        requested_target_lots=cibo.maximum_requested_lots,
    )
    return replace(
        target,
        requested_risk_usd=min(target.requested_risk_usd, cibo.authorized_all_in_risk_usd),
        portfolio_cap_usd=min(target.portfolio_cap_usd, cibo.allocated_source_funds_usd),
    )


@dataclass(frozen=True, slots=True)
class CiboLotageAuditReceipt:
    """Research decision audit, NOT a fill, a signed LIVE receipt or broker proof.

    Stop-risk and round-trip costs are separately reported; do not display
    broker margin as loss-risk or CIBO allocation as permission to lose it.
    """
    signal_id: str
    trader_id: str
    broker_symbol: str
    side: str
    source_lane: str
    decision_state: str
    entry_price: Decimal
    stop_price: Decimal
    lots: Decimal
    qore_nav_usd: Decimal
    sovereign_5pct_ceiling_usd: Decimal
    cibo_risk_budget_usd: Decimal
    cibo_allocated_funds_usd: Decimal
    stop_loss_usd: Decimal
    total_roundtrip_cost_usd: Decimal
    all_in_risk_usd: Decimal
    broker_margin_usd: Decimal
    broker_grid_min_lots: Decimal
    broker_grid_step_lots: Decimal
    reason_codes: tuple[str, ...]
    account_sequence: int
    cibo_source_evidence_sha256: str
    broker_source_evidence_sha256: str
    real_mt5_fill_proven: bool = False


def audit_cibo_qdle_lotage(
    *,
    cibo: CiboEconomicInstruction,
    observation: FourMotorObservation,
    votes: tuple[FourMotorProposal, ...],
    result: QDLEResult,
    broker_min_lot: Decimal,
    broker_lot_step: Decimal,
) -> CiboLotageAuditReceipt:
    """Check CIBO's request against QDLE's actual *computed* research result.

    Does not independently value a broker contract or authorize sending.
    The producer receipt/evidence and broker's stop valuation remain needed
    for anything LIVE; this audit makes no claims about MT5 fills or slippage.
    """
    if not isinstance(result, QDLEResult):
        raise FourMotorPolicyError("QDLE physical computation result required")
    intent = build_cibo_directed_qdle_intent(
        cibo=cibo, observation=observation, votes=votes,
    )
    if (result.request_id != intent.request_id or
            result.account_sequence != intent.expected_account_sequence):
        raise FourMotorPolicyError("QDLE receipt request/epoch mismatch")
    positive("broker_min_lot", broker_min_lot)
    positive("broker_lot_step", broker_lot_step)
    if result.state not in ("RESERVED_FOR_TRADER", "UNFUNDABLE"):
        raise FourMotorPolicyError("QDLE status not a broker proposal decision")
    if not isinstance(result.binding_limits, tuple):
        raise FourMotorPolicyError("QDLE binding constraints required")
    for label in ("lots", "stop_usd", "cost_usd", "total_risk_usd", "margin_usd"):
        nonnegative(label, getattr(result, label))
    # QDLE calculates stop + roundtrip costs with precision=100. The audit
    # must not round that exact Decimal identity back to the process default
    # (usually 28 digits); doing so incorrectly rejected valid FXJPY lots.
    with localcontext() as ctx:
        ctx.prec = max(
            100,
            len(result.stop_usd.as_tuple().digits)
            + len(result.cost_usd.as_tuple().digits) + 2,
        )
        if result.stop_usd + result.cost_usd != result.total_risk_usd:
            raise FourMotorPolicyError("QDLE risk excludes stop loss or costs")
    limits = {v.producer: v for v in votes}
    max_loss = min(
        cibo.authorized_all_in_risk_usd,
        observation.base_entry_budget_usd,
        intent.requested_risk_usd,
        intent.sizing_cap_usd,
        intent.cibo_compound_cap_usd,
        intent.portfolio_cap_usd,
        observation.source_available_usd,
    )
    if result.total_risk_usd > max_loss:
        raise FourMotorPolicyError("QDLE all-in risk exceeds CIBO or motor budget")
    margin_limit = min(
        intent.margin_cap_usd,
        observation.broker_free_margin_usd - observation.broker_margin_reservations_usd,
    )
    if result.margin_usd > max(Decimal(0), margin_limit):
        raise FourMotorPolicyError("QDLE exceeds broker/engine margin")
    if result.lots > intent.leverage_cap_lots:
        raise FourMotorPolicyError("QDLE volume exceeds Adaptive Leverage")
    if result.lots == 0:
        if (result.state != "UNFUNDABLE" or result.total_risk_usd != 0
                or result.margin_usd != 0):
            raise FourMotorPolicyError("zero lot must be unfundable with zero exposure")
        reason = ("NO_FINANCEABLE_BROKER_LOT",) + result.binding_limits
    else:
        if result.state != "RESERVED_FOR_TRADER":
            raise FourMotorPolicyError("positive lot must remain a proposal")
        if result.lots < broker_min_lot or result.lots % broker_lot_step != 0:
            raise FourMotorPolicyError("QDLE violated broker lot grid")
        if intent.requested_target_lots is not None and result.lots > intent.requested_target_lots:
            raise FourMotorPolicyError("QDLE exceeded CIBO volume preference")
        reason = ("RESERVED_NOT_EXECUTED",) + result.binding_limits
    # Require all four distinct independent proposals and their unit-bound limits.
    if set(limits) != {"SIZING", "CIBO_COMPOUND", "ADAPTIVE_LEVERAGE", "PORTFOLIO_COMPOUND"}:
        raise FourMotorPolicyError("all four economic producers required")
    return CiboLotageAuditReceipt(
        signal_id=cibo.signal_id, trader_id=cibo.trader_id,
        broker_symbol=result.symbol, side=cibo.side, source_lane=cibo.source_lane,
        decision_state=result.state, entry_price=cibo.entry_price,
        stop_price=cibo.stop_price, lots=result.lots,
        qore_nav_usd=observation.qore_nav_usd,
        sovereign_5pct_ceiling_usd=observation.base_entry_budget_usd,
        cibo_risk_budget_usd=cibo.authorized_all_in_risk_usd,
        cibo_allocated_funds_usd=cibo.allocated_source_funds_usd,
        stop_loss_usd=result.stop_usd, total_roundtrip_cost_usd=result.cost_usd,
        all_in_risk_usd=result.total_risk_usd, broker_margin_usd=result.margin_usd,
        broker_grid_min_lots=broker_min_lot, broker_grid_step_lots=broker_lot_step,
        reason_codes=reason, account_sequence=result.account_sequence,
        cibo_source_evidence_sha256=cibo.evidence_sha256,
        broker_source_evidence_sha256=observation.broker_evidence_sha256,
        real_mt5_fill_proven=False,
    )

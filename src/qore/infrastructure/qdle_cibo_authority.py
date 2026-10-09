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
from decimal import Decimal

from qore.infrastructure.cibo_four_motor_policy import (
    FourMotorObservation, FourMotorProposal, FourMotorPolicyError, nonnegative, utc,
)
from qore.infrastructure.cibo_four_motor_qdle_proposal import build_four_motor_qdle_intent
from qore.infrastructure.qore_dynamic_lot_engine import QDLEIntent


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

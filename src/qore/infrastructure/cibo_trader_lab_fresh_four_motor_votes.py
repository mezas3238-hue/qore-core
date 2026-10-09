"""One fresh economic four-producer evaluation per observed PAPER M5 opportunity.

DO NOT CALL FROM LIVE. No HMAC producer authentication, MT5 quote completeness,
historical bid/ask, mark-to-market equity or signature is claimed here.
The actual four independent CIBO producer implementations are invoked every time.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from qore.infrastructure.cibo_four_motor_policy import (
    FourMotorObservation, FourMotorProposal, ReconciledQoreCashflow,
)
from qore.infrastructure.cibo_account_sizing_authority import propose_p0_sizing_vote
from qore.infrastructure.cibo_compound_capital import propose_p0_compound_vote
from qore.infrastructure.cibo_marginal_leverage_utility import propose_p0_adaptive_leverage_vote
from qore.infrastructure.cibo_core_compound_portfolio import propose_p0_portfolio_vote
from qore.infrastructure.qore_dynamic_lot_engine import QDLEIntent

ZERO = Decimal("0")
FIVE = Decimal("0.05")
PRODUCERS = ("SIZING", "CIBO_COMPOUND", "ADAPTIVE_LEVERAGE", "PORTFOLIO_COMPOUND")


def _sha(material: object) -> str:
    packed = json.dumps(material, sort_keys=True, separators=(",", ":"),
                        default=lambda obj: str(obj)).encode("utf-8")
    return "sha256:" + hashlib.sha256(packed).hexdigest()


def _d(value: Decimal) -> str:
    return format(value, "f")


@dataclass(frozen=True)
class PaperEconomicDecision:
    observation: FourMotorObservation
    votes: tuple[FourMotorProposal, ...]
    intent: QDLEIntent

    def receipts(self) -> list[dict]:
        output = []
        for proposal in self.votes:
            payload = proposal.payload()
            # The unabridged event IDs remain in the PAPER cashbook. Do not
            # serialize the same growing event list four times per signal.
            cashbook_ids = payload.pop("realized_event_ids")
            payload["realized_event_count"] = len(cashbook_ids)
            payload["realized_event_ids_sha256"] = _sha(cashbook_ids)
            payload["scenario_receipt_sha256"] = _sha(payload)
            payload["producer_signature_authenticated"] = False
            payload["broker_evidence_authenticated"] = False
            output.append(payload)
        return output


def calculate_fresh_paper_four_votes(
    *,
    signal_id: str, trader_id: str, symbol: str, side: str,
    at: datetime, sequence: int, entry_price: Decimal, stop_price: Decimal,
    requested_fraction: Decimal, current_paper_cash_usd: Decimal,
    paper_initial_capital_usd: Decimal, paper_broker_balance_usd: Decimal,
    stop_loss_usd_per_lot: Decimal, estimated_fee_per_lot: Decimal,
    broker_margin_per_lot: Decimal, symbol_max_lots: Decimal,
    open_positions: dict, paper_cash_events: tuple[ReconciledQoreCashflow, ...],
) -> PaperEconomicDecision:
    """All inputs must be observations at/before `at`, never future trade outcomes.

    Ledger checks stop a stale NAV or settlement from producing a fresh vote.
    PAPER equity is deliberately not passed off as authentic MTM equity.
    """
    if not ZERO <= requested_fraction <= FIVE:
        raise ValueError("CIBO requested fraction must be 0..5% QORE capital")
    if not paper_cash_events or paper_cash_events[-1].realized_at <= at:
        pass
    else:
        raise ValueError("future PAPER cashflow leaked into economic vote")
    reconciled_cash = paper_initial_capital_usd + sum(
        (flow.net_usd for flow in paper_cash_events), ZERO
    )
    if abs(reconciled_cash - current_paper_cash_usd) > Decimal("0.000000000000001"):
        raise ValueError("PAPER ledger/cash mismatch: stale economic input")
    held_risk = sum((p["risk"] for p in open_positions.values()), ZERO)
    held_margin = sum((p["margin"] for p in open_positions.values()), ZERO)
    if any(p["opened_at"] > at for p in open_positions.values()):
        raise ValueError("future PAPER position injected into vote")
    if any(p["risk"] < 0 or p["margin"] < 0 for p in open_positions.values()):
        raise ValueError("negative active risk/margin")
    correlated = sum((p["risk"] for p in open_positions.values()
                      if p["symbol"] == symbol or (
                          p["symbol"].endswith("JPY") and symbol.endswith("JPY"))), ZERO)
    trader_risk = sum((p["risk"] for p in open_positions.values()
                       if p["trader"] == trader_id), ZERO)
    directional = sum((p["lots"] for p in open_positions.values()
                       if p["symbol"] == symbol and p["side"] == side), ZERO)
    evidence = _sha({
        "source": "TRADER_LAB_FIXED_2026_SPREAD_PAPER_ONLY_NOT_MT5",
        "signal": signal_id, "at": at.isoformat(), "sequence": sequence,
        "symbol": symbol, "side": side, "entry": _d(entry_price),
        "stop": _d(stop_price), "stop_per_lot": _d(stop_loss_usd_per_lot),
        "fee_scenario": _d(estimated_fee_per_lot),
        "margin_scenario": _d(broker_margin_per_lot),
        "paper_cash": _d(current_paper_cash_usd),
        "cashflow_ids": [f.event_id for f in paper_cash_events],
        "positions": sorted(open_positions),
    })
    obs = FourMotorObservation(
        request_id=signal_id, trader_id=trader_id, symbol=symbol, side=side,
        source_lane="SOVEREIGN_BANK", observed_at=at, account_sequence=sequence,
        broker_evidence_sha256=evidence,
        initial_qore_nav_usd=paper_initial_capital_usd,
        reconciled_cashflows=paper_cash_events,
        protected_capital_usd=ZERO, floating_loss_reserve_usd=ZERO,
        risk_reservations_usd=held_risk,
        bank_unreserved_usd=max(ZERO, current_paper_cash_usd - held_risk),
        cushion_unreserved_usd=ZERO,
        total_open_stop_risk_usd=held_risk,
        correlated_open_stop_risk_usd=correlated,
        trader_open_stop_risk_usd=trader_risk,
        broker_free_margin_usd=max(ZERO, paper_broker_balance_usd),
        broker_margin_reservations_usd=held_margin,
        stop_loss_usd_per_lot=stop_loss_usd_per_lot,
        roundtrip_fees_usd_per_lot=estimated_fee_per_lot,
        execution_buffer_usd_per_lot=ZERO,
        stress_extra_loss_usd_per_lot=ZERO,
        broker_margin_usd_per_lot=broker_margin_per_lot,
        symbol_max_lots=symbol_max_lots,
        provider_direction_max_lots=symbol_max_lots,
        open_and_reserved_direction_lots=directional,
        broker_quote_at=at,
        broker_fees_complete=False, broker_profit_valuation_complete=False,
        broker_margin_valuation_complete=False, research_scenario_only=True,
    )
    votes = (
        propose_p0_sizing_vote(obs),
        propose_p0_compound_vote(obs),
        propose_p0_adaptive_leverage_vote(obs),
        propose_p0_portfolio_vote(obs),
    )
    if tuple(v.producer for v in votes) != PRODUCERS:
        raise ValueError("four independent producer votes required")
    limits = {v.producer: v.limits for v in votes}
    intent = QDLEIntent(
        request_id=signal_id, trader_id=trader_id, symbol=symbol,
        side=side, entry_price=entry_price, stop_price=stop_price,
        requested_risk_usd=max(ZERO, obs.qore_nav_usd * requested_fraction),
        sizing_cap_usd=Decimal(limits["SIZING"]["approved_risk_usd"]),
        cibo_compound_cap_usd=Decimal(limits["CIBO_COMPOUND"]["approved_risk_usd"]),
        portfolio_cap_usd=Decimal(
            limits["PORTFOLIO_COMPOUND"]["approved_source_funds_usd"]),
        leverage_cap_lots=Decimal(limits["ADAPTIVE_LEVERAGE"]["approved_max_lots"]),
        margin_cap_usd=Decimal(limits["ADAPTIVE_LEVERAGE"]["approved_margin_usd"]),
        source_lane="SOVEREIGN_BANK",
        slippage_usd_per_lot=ZERO, expected_account_sequence=sequence,
    )
    return PaperEconomicDecision(obs, votes, intent)


def paper_cashflow(*, event_id: str, at: datetime,
                   delta_usd: Decimal) -> ReconciledQoreCashflow:
    """Signed only by a deterministic PAPER-event hash, NEVER broker proof."""
    return ReconciledQoreCashflow(
        event_id="PAPER_ONLY:" + event_id,
        realized_at=at, net_usd=delta_usd,
        source_settlement_sha256=_sha({
            "event": event_id, "at": at.isoformat(), "delta_usd": str(delta_usd),
            "provenance": "PAPER_INTERNAL_RECONCILIATION_NOT_MT5",
        }),
        reconciled=True,
    )

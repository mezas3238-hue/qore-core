"""QORE Alpha2 G2 cost STRESS calculator with complete causal evidence.

NOT an executable fill, account P&L or UTC001 certification. Historical tick
event timestamps recovered in 2026 MUST NOT be relabelled receipt timestamps.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Literal

from qore.research.alpha2_g2_bidask_causal_contract import (
    BrokerEvidenceError,
    QuoteObservation,
    asof_quote,
    causal_side_reference,
)

STATUS = "HYPOTHETICAL_QUOTE_COST_STRESS_NOT_NET_CERTIFICATION"
_HASH = re.compile(r"[0-9a-f]{64}\Z")


def _money(label: str, value: Decimal, *, positive: bool) -> None:
    if (type(value) is not Decimal or not value.is_finite()
            or (value <= 0 if positive else value < 0)):
        raise BrokerEvidenceError(f"{label}: explicit finite Decimal required")


def _stamp(label: str, value: datetime) -> None:
    if (type(value) is not datetime or value.tzinfo is None
            or value.utcoffset() != timedelta(0)):
        raise BrokerEvidenceError(f"{label}: exact aware UTC timestamp required")


def _sha(label: str, value: str) -> None:
    if not isinstance(value, str) or _HASH.fullmatch(value) is None:
        raise BrokerEvidenceError(f"{label}: verified original SHA256 missing")


@dataclass(frozen=True, slots=True)
class EconomicContractWitness:
    """Research source contract; external source identity is still required."""
    symbol: str
    broker_source_id: str
    account_scope_id: str
    provider_symbol: str
    provider_symbol_id: int
    account_currency: str
    quote_currency: str
    trade_units: Decimal
    cash_in_quote_per_unit_price: Decimal
    contract_known_at: datetime
    fee_schedule_known_at: datetime
    contract_valid_until: datetime
    fee_schedule_valid_until: datetime
    contract_sha256: str
    fees_sha256: str
    verified_linear_payoff: bool

    def __post_init__(self) -> None:
        if (not all(isinstance(s, str) and s.strip() for s in (
            self.symbol, self.broker_source_id, self.account_scope_id,
            self.provider_symbol, self.account_currency, self.quote_currency,
        )) or type(self.provider_symbol_id) is not int
                or self.provider_symbol_id <= 0
                or self.verified_linear_payoff is not True):
            raise BrokerEvidenceError("contract identity, symbol ID or linear payoff absent")
        if (self.account_currency.strip() != self.account_currency
                or self.quote_currency.strip() != self.quote_currency
                or len(self.account_currency) != 3 or len(self.quote_currency) != 3
                or not self.account_currency.isupper()
                or not self.quote_currency.isupper()):
            raise BrokerEvidenceError("explicit ISO-style currency identifier required")
        _money("trade_units", self.trade_units, positive=True)
        _money("cash_in_quote_per_unit_price",
               self.cash_in_quote_per_unit_price, positive=True)
        _stamp("contract_known_at", self.contract_known_at)
        _stamp("fee_schedule_known_at", self.fee_schedule_known_at)
        _stamp("contract_valid_until", self.contract_valid_until)
        _stamp("fee_schedule_valid_until", self.fee_schedule_valid_until)
        if (self.contract_valid_until <= self.contract_known_at
                or self.fee_schedule_valid_until <= self.fee_schedule_known_at):
            raise BrokerEvidenceError("broker contract/fee validity period missing")
        if self.provider_symbol != self.symbol:
            raise BrokerEvidenceError(
                "historical provider alias requires separate exact contract proof"
            )
        _sha("contract_sha256", self.contract_sha256)
        _sha("fees_sha256", self.fees_sha256)


@dataclass(frozen=True, slots=True)
class ExplicitCostWitness:
    """Every zero is EXPLICITLY supplied and SHA-bound, never defaulted."""
    entry_commission_deposit: Decimal
    exit_commission_deposit: Decimal
    funding_deposit: Decimal
    swap_deposit: Decimal
    entry_adverse_slippage_price: Decimal
    exit_adverse_slippage_price: Decimal

    def __post_init__(self) -> None:
        for field_name in (
            "entry_commission_deposit", "exit_commission_deposit",
            "funding_deposit", "swap_deposit",
            "entry_adverse_slippage_price", "exit_adverse_slippage_price",
        ):
            _money(field_name, getattr(self, field_name), positive=False)


@dataclass(frozen=True, slots=True)
class ConversionWitness:
    """Rate in deposit per quote currency; available at exit, not backfilled."""
    rate_deposit_per_quote: Decimal
    known_at: datetime
    source_sha256: str

    def __post_init__(self) -> None:
        _money("rate_deposit_per_quote", self.rate_deposit_per_quote, positive=True)
        _stamp("conversion_known_at", self.known_at)
        _sha("conversion_sha256", self.source_sha256)


@dataclass(frozen=True, slots=True)
class StressResult:
    """A quoted research estimate only; cannot be used as an order or NET gate."""
    status: str
    reference_entry_price: Decimal
    reference_exit_price: Decimal
    stressed_entry_price: Decimal
    stressed_exit_price: Decimal
    gross_reference_deposit: Decimal
    gross_after_slippage_deposit: Decimal
    fees_funding_swap_deposit: Decimal
    stressed_surplus_deposit: Decimal
    hypothetical_r_multiple: Decimal
    executable_fill_attested: bool = False
    broker_actual_net_attested: bool = False
    utc001_certified: bool = False


def quote_cost_stress(
    *,
    entry_series: tuple[QuoteObservation, ...],
    exit_series: tuple[QuoteObservation, ...],
    entry_decision: datetime,
    exit_decision: datetime,
    contract: EconomicContractWitness,
    costs: ExplicitCostWitness,
    conversion: ConversionWitness,
    direction: Literal[-1, 1],
    cash_risk_in_deposit: Decimal,
    source_mode: Literal["PROSPECTIVE_RECEIVED_QUOTES"],
) -> StressResult:
    if source_mode != "PROSPECTIVE_RECEIVED_QUOTES":
        raise BrokerEvidenceError("archived historical event-time cannot claim real receipt")
    _stamp("entry_decision", entry_decision)
    _stamp("exit_decision", exit_decision)
    if entry_decision >= exit_decision:
        raise BrokerEvidenceError("noncausal entry/exit order")
    if (not contract.contract_known_at <= entry_decision < contract.contract_valid_until
            or not contract.fee_schedule_known_at <= entry_decision
            < contract.fee_schedule_valid_until
            or conversion.known_at > exit_decision):
        raise BrokerEvidenceError("contract, fees or conversion unknown/expired as of trade")
    if (contract.account_currency == contract.quote_currency
            and conversion.rate_deposit_per_quote != Decimal("1")):
        raise BrokerEvidenceError("same-currency conversion must be exactly unity")
    if (contract.account_currency != contract.quote_currency
            and exit_decision-conversion.known_at > timedelta(seconds=5)):
        raise BrokerEvidenceError("FX conversion quote stale at exit")
    if not isinstance(costs, ExplicitCostWitness):
        raise BrokerEvidenceError("six explicit cost fields and source required")
    _money("cash_risk_in_deposit", cash_risk_in_deposit, positive=True)
    if type(direction) is not int or direction not in (-1, 1):
        raise BrokerEvidenceError("invalid +1 or -1 direction")

    kwargs = {
        "expected_symbol": contract.symbol,
        "broker_source_id": contract.broker_source_id,
        "account_scope_id": contract.account_scope_id,
    }
    entry = asof_quote(entry_series, decision_at=entry_decision, **kwargs)
    exit_ = asof_quote(exit_series, decision_at=exit_decision, **kwargs)
    # Verify both sides: positive spreads and source-only references.
    entry_side = causal_side_reference(
        entry, position_direction=direction, action="entry",
    )
    exit_side = causal_side_reference(
        exit_, position_direction=direction, action="exit",
    )
    reference_entry = Decimal(str(entry_side))
    reference_exit = Decimal(str(exit_side))
    adverse_entry = costs.entry_adverse_slippage_price
    adverse_exit = costs.exit_adverse_slippage_price
    stressed_entry = reference_entry + Decimal(direction) * adverse_entry
    stressed_exit = reference_exit - Decimal(direction) * adverse_exit
    if stressed_entry <= 0 or stressed_exit <= 0:
        raise BrokerEvidenceError("adverse slippage crosses nonpositive price")

    conversion_factor = (
        contract.trade_units
        * contract.cash_in_quote_per_unit_price
        * conversion.rate_deposit_per_quote
    )
    signed = Decimal(direction)
    gross = signed * (reference_exit - reference_entry) * conversion_factor
    after_slip = signed * (stressed_exit - stressed_entry) * conversion_factor
    charges = (
        costs.entry_commission_deposit + costs.exit_commission_deposit
        + costs.funding_deposit + costs.swap_deposit
    )
    surplus = after_slip - charges
    return StressResult(
        status=STATUS,
        reference_entry_price=reference_entry,
        reference_exit_price=reference_exit,
        stressed_entry_price=stressed_entry,
        stressed_exit_price=stressed_exit,
        gross_reference_deposit=gross,
        gross_after_slippage_deposit=after_slip,
        fees_funding_swap_deposit=charges,
        stressed_surplus_deposit=surplus,
        hypothetical_r_multiple=surplus / cash_risk_in_deposit,
    )

"""Synthetic-only fail-closed Alpha2 G2 causal economics stress tests."""
from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from qore.research.alpha2_g2_bidask_causal_contract import (
    BrokerEvidenceError,
    QuoteObservation,
)
from qore.research.alpha2_g2_causal_economic_stress import (
    STATUS,
    ConversionWitness,
    EconomicContractWitness,
    ExplicitCostWitness,
    quote_cost_stress,
)

T = datetime(2026, 10, 12, 10, 0, tzinfo=UTC)
EXIT = T + timedelta(minutes=5)
SHA = "c" * 64


def q(*, at: datetime, bid: float, ask: float, acct: str = "demo-pseudonym"):
    return QuoteObservation(
        symbol="EURUSD", broker_source_id="ctrader-icm-demo",
        account_scope_id=acct, quote_at=at - timedelta(milliseconds=200),
        available_at=at - timedelta(milliseconds=100),
        bid=bid, ask=ask,
    )


def contract(**kw):
    values = {
        "symbol": "EURUSD", "broker_source_id": "ctrader-icm-demo",
        "account_scope_id": "demo-pseudonym", "provider_symbol": "EURUSD",
        "provider_symbol_id": 1234, "account_currency": "USD",
        "quote_currency": "USD", "trade_units": Decimal("10"),
        "cash_in_quote_per_unit_price": Decimal("1"),
        "contract_known_at": T-timedelta(days=1),
        "fee_schedule_known_at": T-timedelta(days=1),
        "contract_valid_until": T+timedelta(days=1),
        "fee_schedule_valid_until": T+timedelta(days=1),
        "contract_sha256": SHA, "fees_sha256": SHA,
        "verified_linear_payoff": True,
    }
    values.update(kw)
    return EconomicContractWitness(**values)


def fees(**kw):
    values = {
        "entry_commission_deposit": Decimal("1"),
        "exit_commission_deposit": Decimal("2"),
        "funding_deposit": Decimal("0.1"),
        "swap_deposit": Decimal("0.5"),
        "entry_adverse_slippage_price": Decimal("0.1"),
        "exit_adverse_slippage_price": Decimal("0.2"),
    }
    values.update(kw)
    return ExplicitCostWitness(**values)


def conversion(**kw):
    values = {"rate_deposit_per_quote": Decimal("1"), "known_at": EXIT,
              "source_sha256": SHA}
    values.update(kw)
    return ConversionWitness(**values)


def inputs(**kw):
    data = {
        "entry_series": (q(at=T, bid=100, ask=101),),
        "exit_series": (q(at=EXIT, bid=103, ask=104),),
        "entry_decision": T, "exit_decision": EXIT,
        "contract": contract(), "costs": fees(),
        "conversion": conversion(), "direction": 1,
        "cash_risk_in_deposit": Decimal("100"),
        "source_mode": "PROSPECTIVE_RECEIVED_QUOTES",
    }
    data.update(kw)
    return data


def test_long_pays_actual_two_sided_quoted_spread_adverse_slip_and_all_charges():
    result = quote_cost_stress(**inputs())
    assert result.status == STATUS
    assert result.reference_entry_price == Decimal("101")
    assert result.reference_exit_price == Decimal("103")
    assert result.stressed_entry_price == Decimal("101.1")
    assert result.stressed_exit_price == Decimal("102.8")
    assert result.gross_reference_deposit == Decimal("20")
    assert result.gross_after_slippage_deposit == Decimal("17")
    assert result.fees_funding_swap_deposit == Decimal("3.6")
    assert result.stressed_surplus_deposit == Decimal("13.4")
    assert result.hypothetical_r_multiple == Decimal("0.134")
    assert not result.executable_fill_attested
    assert not result.broker_actual_net_attested
    assert not result.utc001_certified


def test_short_also_pays_bidask_spread_both_adverse_slippages():
    result = quote_cost_stress(**inputs(
        direction=-1,exit_series=(q(at=EXIT,bid=98,ask=99),)
    ))
    assert result.reference_entry_price == Decimal("100")
    assert result.reference_exit_price == Decimal("99")
    assert result.stressed_entry_price == Decimal("99.9")
    assert result.stressed_exit_price == Decimal("99.2")
    assert result.gross_after_slippage_deposit == Decimal("7")
    assert result.stressed_surplus_deposit == Decimal("3.4")


def test_quote_currency_to_deposit_conversion_requires_fx_evidence_asof_exit():
    result = quote_cost_stress(**inputs(
        contract=contract(account_currency="EUR"),
        conversion=conversion(rate_deposit_per_quote=Decimal("2")),
    ))
    assert result.gross_after_slippage_deposit == Decimal("34")
    assert result.stressed_surplus_deposit == Decimal("30.4")


def test_archived_tick_event_time_never_admitted_as_live_receipt():
    with pytest.raises(BrokerEvidenceError, match="archived historical"):
        quote_cost_stress(**inputs(source_mode="ARCHIVED_EVENT_TIME"))


def test_source_age_and_future_quote_visible_at_decision_rejected():
    with pytest.raises(BrokerEvidenceError, match="stale"):
        quote_cost_stress(**inputs(
            entry_series=(q(at=T-timedelta(seconds=12),bid=100,ask=101),)
        ))
    with pytest.raises(BrokerEvidenceError, match="no quote visible"):
        quote_cost_stress(**inputs(
            entry_series=(q(at=T+timedelta(seconds=1),bid=100,ask=101),)
        ))


def test_no_account_cohort_or_symbol_equivalence_shortcut():
    with pytest.raises(BrokerEvidenceError, match="mismatch"):
        quote_cost_stress(**inputs(
            entry_series=(q(at=T,bid=100,ask=101,acct="other-account"),)
        ))
    with pytest.raises(BrokerEvidenceError, match="alias"):
        contract(provider_symbol="USTEC")


def test_zero_spread_is_quarantined_not_free_cost():
    with pytest.raises(BrokerEvidenceError, match="ZERO_OR_CROSSED_SPREAD"):
        quote_cost_stress(**inputs(
            entry_series=(q(at=T,bid=100,ask=100),)
        ))


def test_negative_or_missing_commission_and_swap_rejected():
    with pytest.raises(BrokerEvidenceError, match="commission"):
        fees(entry_commission_deposit=Decimal("-0.01"))
    with pytest.raises(TypeError, match="exit_commission_deposit"):
        ExplicitCostWitness(
            entry_commission_deposit=Decimal("1"), swap_deposit=Decimal("0"),
            funding_deposit=Decimal("0"),
            entry_adverse_slippage_price=Decimal("0"),
            exit_adverse_slippage_price=Decimal("0"),
        )
    with pytest.raises(BrokerEvidenceError, match="six explicit cost"):
        quote_cost_stress(**inputs(costs=None))


def test_monetary_float_nan_bool_or_unverified_decimal_cannot_enter_ledger():
    with pytest.raises(BrokerEvidenceError, match="trade_units"):
        contract(trade_units=10.0)
    with pytest.raises(BrokerEvidenceError, match="trade_units"):
        contract(trade_units=Decimal("NaN"))
    with pytest.raises(BrokerEvidenceError, match="swap"):
        fees(swap_deposit=float("nan"))
    with pytest.raises(BrokerEvidenceError, match="cash_risk"):
        quote_cost_stress(**inputs(cash_risk_in_deposit=0))
    with pytest.raises(BrokerEvidenceError, match="direction"):
        quote_cost_stress(**inputs(direction=True))


def test_future_or_expired_contract_fees_and_conversion_block():
    with pytest.raises(BrokerEvidenceError, match="unknown/expired"):
        quote_cost_stress(**inputs(
            contract=contract(contract_known_at=T+timedelta(seconds=1))
        ))
    with pytest.raises(BrokerEvidenceError, match="unknown/expired"):
        quote_cost_stress(**inputs(
            contract=contract(fee_schedule_valid_until=T)
        ))
    with pytest.raises(BrokerEvidenceError, match="unknown/expired"):
        quote_cost_stress(**inputs(
            conversion=conversion(known_at=EXIT+timedelta(seconds=1))
        ))


def test_stale_currency_conversion_and_fake_same_currency_rate_rejected():
    with pytest.raises(BrokerEvidenceError, match="FX conversion quote stale"):
        quote_cost_stress(**inputs(
            contract=contract(account_currency="EUR"),
            conversion=conversion(rate_deposit_per_quote=Decimal("2"),
                                  known_at=EXIT-timedelta(seconds=6)),
        ))
    with pytest.raises(BrokerEvidenceError, match="same-currency"):
        quote_cost_stress(**inputs(
            conversion=conversion(rate_deposit_per_quote=Decimal("1.2"))
        ))


def test_unverified_contract_metadata_sha_or_non_linear_instrument_blocked():
    with pytest.raises(BrokerEvidenceError, match="SHA256"):
        contract(contract_sha256="")
    with pytest.raises(BrokerEvidenceError, match="linear payoff"):
        contract(verified_linear_payoff=False)
    with pytest.raises(BrokerEvidenceError, match="validity period"):
        contract(contract_valid_until=T-timedelta(days=2))


def test_zero_explicit_costs_can_be_represented_but_never_defaulted():
    zero = fees(
        entry_commission_deposit=Decimal("0"), exit_commission_deposit=Decimal("0"),
        funding_deposit=Decimal("0"),swap_deposit=Decimal("0"),
        entry_adverse_slippage_price=Decimal("0"),
        exit_adverse_slippage_price=Decimal("0"),
    )
    result = quote_cost_stress(**inputs(costs=zero))
    assert result.stressed_surplus_deposit == Decimal("20")
    assert not result.broker_actual_net_attested


def test_zero_risk_and_noncausal_exit_are_blocked():
    with pytest.raises(BrokerEvidenceError, match="cash_risk"):
        quote_cost_stress(**inputs(cash_risk_in_deposit=Decimal("0")))
    with pytest.raises(BrokerEvidenceError, match="noncausal"):
        quote_cost_stress(**inputs(exit_decision=T))


def test_extreme_slippage_cannot_produce_negative_stressed_order_price():
    with pytest.raises(BrokerEvidenceError, match="nonpositive"):
        quote_cost_stress(**inputs(
            direction=-1,costs=fees(entry_adverse_slippage_price=Decimal("101")),
        ))


def test_no_gratuitous_datetime_or_monotonicity_acceptance():
    with pytest.raises(BrokerEvidenceError, match="UTC"):
        quote_cost_stress(**inputs(entry_decision=datetime(2026,10,12,10,0)))
    with pytest.raises(BrokerEvidenceError, match="SHA256"):
        replace(contract(), contract_sha256="a"*63)

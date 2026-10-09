"""Cross-architect P0 synthetic smoke/negative tests. No MT5 fills, no live."""
from __future__ import annotations

import tempfile
import unittest
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal as D
from pathlib import Path

from qore.infrastructure.cibo_trade_ops_director import (
    Stage, TradeOpsError, TradeOpsEvent, apply_trade_event,
)
from qore.infrastructure.cibo_four_motor_policy import FourMotorObservation
from qore.infrastructure.qdle_cibo_authority import CiboEconomicInstruction
from qore.infrastructure.cibo_sovereign_integration import (
    prepare_shadow_economic_decision, record_shadow_qdle_result,
)
from qore.infrastructure.qore_dynamic_lot_engine import (
    QDLE, QDLEAccount, QDLESymbol, BrokerValuation,
)

T = datetime(2026, 10, 8, 13, 0, tzinfo=UTC)
SHA = "sha256:" + "a" * 64


class SyntheticBroker:
    def value(self, spec, intent, now):
        return BrokerValuation(D("100"), D("1000"), now, "SYNTHETIC_ONLY")
    def check_volume(self, spec, intent, lots):
        return None


def valued_state():
    s = None
    for n, stage in enumerate((Stage.SIGNAL_RECEIVED, Stage.ECONOMICALLY_VALUED)):
        event = TradeOpsEvent(
            event_id=f"synthetic-{n}", signal_id="signal-A",
            trader_id="trader-A", symbol="EURUSD", side="BUY",
            stage=stage, occurred_at=T, evidence_as_of=T,
            evidence_sha256=SHA, reason="SYNTHETIC_CONTRACT_TEST",
        )
        s = apply_trade_event(s, event)
    return s


def observation(**changes):
    data = dict(
        request_id="signal-A", trader_id="trader-A", symbol="EURUSD",
        side="BUY", source_lane="SOVEREIGN_BANK",
        observed_at=T, account_sequence=1,
        broker_evidence_sha256=SHA, initial_qore_nav_usd=D("60"),
        reconciled_cashflows=(), protected_capital_usd=D("0"),
        floating_loss_reserve_usd=D("0"), risk_reservations_usd=D("0"),
        bank_unreserved_usd=D("60"), cushion_unreserved_usd=D("0"),
        total_open_stop_risk_usd=D("0"),
        correlated_open_stop_risk_usd=D("0"),
        trader_open_stop_risk_usd=D("0"),
        broker_free_margin_usd=D("1900"),
        broker_margin_reservations_usd=D("0"),
        stop_loss_usd_per_lot=D("100"),
        roundtrip_fees_usd_per_lot=D("14"),
        execution_buffer_usd_per_lot=D("0"),
        stress_extra_loss_usd_per_lot=D("0"),
        broker_margin_usd_per_lot=D("1000"),
        symbol_max_lots=D("40"),
        provider_direction_max_lots=D("40"),
        open_and_reserved_direction_lots=D("0"),
        broker_quote_at=T, broker_fees_complete=True,
        broker_profit_valuation_complete=True,
        broker_margin_valuation_complete=True,
    )
    data.update(changes)
    return FourMotorObservation(**data)


def cibo(risk="3", **changes):
    d = dict(
        signal_id="signal-A", trader_id="trader-A",
        symbol="EURUSD", side="BUY",
        entry_price=D("1.1000"), stop_price=D("1.0990"),
        source_lane="SOVEREIGN_BANK",
        allocated_source_funds_usd=D("60"),
        authorized_all_in_risk_usd=D(risk),
        maximum_requested_lots=None,
        account_sequence=1, issued_at=T, evidence_sha256=SHA,
    )
    d.update(changes)
    return CiboEconomicInstruction(**d)


def qdle(path):
    engine = QDLE(path, SyntheticBroker(),
                  strict_four_motor_evidence=False, strict_provider_floor=False)
    engine.publish_account(QDLEAccount(
        "broker-acct", "FundedNext", "USD", 1, T,
        D("2000"), D("2000"), D("1900"), D("3"),
        D("60"), D("0"), D("60"),
    ))
    engine.publish_symbol(QDLESymbol(
        "EURUSD", ("EURUSD",), D(".01"), D("40"), D(".01"), D("0"),
        D(".00001"), D("1"), D("100000"), "USD", D("14"),
        "SYNTHETIC_OPEN7_CLOSE7_NOT_A_BROKER_RECEIPT", T,
    ))
    return engine


class TestSovereignIntegrationP0(unittest.TestCase):
    def test_a1_a2_a3_join_only_through_cibo_explicit_authority(self):
        prepared = prepare_shadow_economic_decision(
            state=valued_state(), cibo=cibo(), observation=observation())
        self.assertEqual({v.producer for v in prepared.votes}, {
            "SIZING", "CIBO_COMPOUND", "ADAPTIVE_LEVERAGE", "PORTFOLIO_COMPOUND"})
        self.assertEqual(prepared.intent.requested_risk_usd, D("3"))
        self.assertFalse(prepared.is_live_authorized)
        with tempfile.TemporaryDirectory() as work:
            engine = qdle(Path(work) / "qdle.sqlite")
            result = engine.reserve_for_trader(prepared.intent, T)
            outcome = record_shadow_qdle_result(
                prepared=prepared, result=result, broker_min_lot=D(".01"),
                broker_lot_step=D(".01"), event_id="funded-synthetic", event_at=T)
        self.assertEqual(result.state, "RESERVED_FOR_TRADER")
        self.assertEqual(outcome.state.stage, Stage.ECONOMICALLY_FUNDED)
        self.assertEqual(outcome.state.filled_lots, D("0"))
        self.assertEqual(outcome.receipt.lots, D(".02"))
        self.assertEqual(outcome.receipt.all_in_risk_usd, D("2.28"))
        self.assertFalse(outcome.real_mt5_fill_proven)

    def test_unfundable_zero_cibo_budget_never_auto_finances(self):
        prepared = prepare_shadow_economic_decision(
            state=valued_state(), cibo=cibo("0"), observation=observation())
        with tempfile.TemporaryDirectory() as work:
            result = qdle(Path(work) / "qdle.sqlite").reserve_for_trader(
                prepared.intent, T)
        outcome = record_shadow_qdle_result(
            prepared=prepared, result=result, broker_min_lot=D(".01"),
            broker_lot_step=D(".01"), event_id="unfundable-synthetic", event_at=T)
        self.assertEqual(outcome.state.stage, Stage.UNFUNDABLE)
        self.assertEqual(outcome.receipt.lots, D("0"))
        self.assertEqual(outcome.state.filled_lots, D("0"))

    def test_identity_and_epoch_drift_rejected_without_broker(self):
        s, o = valued_state(), observation()
        for instruction in (
            cibo(signal_id="different"),
            cibo(trader_id="different"),
            cibo(account_sequence=2),
            cibo(issued_at=T + timedelta(seconds=1)),
        ):
            with self.subTest(instruction=instruction):
                with self.assertRaises((TradeOpsError, ValueError)):
                    prepare_shadow_economic_decision(
                        state=s, cibo=instruction, observation=o)
        with self.assertRaises(TradeOpsError):
            prepare_shadow_economic_decision(
                state=s, cibo=cibo(), observation=replace(
                    o, request_id="different"))
        with self.assertRaises(TradeOpsError):
            prepare_shadow_economic_decision(
                state=s, cibo=cibo(), observation=replace(
                    o, observed_at=T - timedelta(seconds=1),
                    broker_quote_at=T - timedelta(seconds=1)))

    def test_cibo_over_5pct_rejected_even_with_four_votes(self):
        with self.assertRaisesRegex(ValueError, "5pct"):
            prepare_shadow_economic_decision(
                state=valued_state(), cibo=cibo("4"), observation=observation())

    def test_no_implicit_funding_on_raw_signal(self):
        raw = apply_trade_event(None, TradeOpsEvent(
            event_id="raw", signal_id="signal-A", trader_id="trader-A",
            symbol="EURUSD", side="BUY", stage=Stage.SIGNAL_RECEIVED,
            occurred_at=T, evidence_as_of=T, evidence_sha256=SHA,
            reason="SYNTHETIC"))
        with self.assertRaisesRegex(TradeOpsError, "economically valued"):
            prepare_shadow_economic_decision(
                state=raw, cibo=cibo(), observation=observation())


if __name__ == "__main__":
    unittest.main()

"""Adapter regressions: Trader retains intent, CIBO four engines bound real lotage."""
import tempfile
import unittest
from datetime import datetime, timezone
from decimal import Decimal as D
from pathlib import Path
from dataclasses import replace

from qore.infrastructure.account_wide_risk import TraderLineage
from qore.infrastructure.cibo_capital_management_authority import TraderOpportunityEnvelope
from qore.infrastructure.qdle_cibo_bridge import CiboFourEngineLimits, reserve_cibo_entry
from qore.infrastructure.qore_dynamic_lot_engine import (
    BrokerValuation, QDLE, QDLEAccount, QDLESymbol,
)

T = datetime(2026, 10, 8, 12, tzinfo=timezone.utc)


class Synthetic:
    def value(self, spec, intent, now):
        return BrokerValuation(D("100"), D("10"), now, "SYNTHETIC_TEST")
    def check_volume(self, spec, intent, lots):
        pass


def opportunity():
    return TraderOpportunityEnvelope(
        trader_id=TraderLineage.R38_EURUSD, signal_fingerprint="qdle-trader-entry",
        qore_symbol="EURUSD", provider_symbol="EURUSD", side="long",
        entry_type="MARKET", intended_entry=D("1.1000"),
        stop_loss=D("1.0950"), take_profit=D("1.11"),
        stop_loss_per_volume=D("100"), margin_per_volume=D("10"),
        volume_step=D(".01"), minimum_volume=D(".01"),
        maximum_volume=D("100"),
    )


def limits():
    return CiboFourEngineLimits(
        requested_stop_loss_budget_usd=D("3"),
        sizing_approved_stop_loss_usd=D("3"),
        compound_approved_stop_loss_usd=D("3"),
        portfolio_approved_funds_usd=D("3"),
        adaptive_leverage_max_broker_lots=D("10"),
        adaptive_leverage_margin_budget_usd=D("10"),
        slippage_buffer_usd_per_lot=D("0"),
        funded_source_lane="SOVEREIGN_BANK", account_sequence=1,
    )


class TestBridge(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.engine = QDLE(Path(self.tmp.name) / "test.sqlite", Synthetic())
        self.engine.publish_account(QDLEAccount(
            "login", "FundedNext", "USD", 1, T, D("60"), D("60"),
            D("50"), D("3"), D("3"), D("0"),
        ))
        self.engine.publish_symbol(QDLESymbol(
            broker_symbol="EURUSD", aliases=("EURUSD",),
            min_lot=D(".01"), max_lot=D("10"), lot_step=D(".01"),
            directional_volume_limit=D("0"), tick_size=D(".00001"),
            tick_value_loss_usd=D("1"), contract_size=D("100000"),
            currency_profit="USD", fee_usd_per_lot=D("0"),
            fee_provenance="SYNTHETIC_TEST", as_of=T,
        ))

    def tearDown(self):
        self.tmp.cleanup()

    def test_four_economic_engines_approve_and_qdle_fixes_lotage(self):
        decision = reserve_cibo_entry(self.engine, opportunity(), limits(), T)
        self.assertEqual(decision.lots, D(".03"))
        self.assertEqual(decision.stop_usd, D("3"))
        self.assertEqual(decision.state, "RESERVED_FOR_TRADER")

    def test_trader_minimum_execution_steps_may_make_trade_unfundable(self):
        entry = replace(opportunity(), minimum_execution_steps=5)
        decision = reserve_cibo_entry(self.engine, entry, limits(), T)
        self.assertEqual(decision.state, "UNFUNDABLE")
        self.assertEqual(decision.lots, D(0))


if __name__ == "__main__":
    unittest.main()

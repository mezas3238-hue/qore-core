"""QDLE must never price LIVE lotage from an entry-only or unknown fee."""
from __future__ import annotations

import tempfile
import unittest
from datetime import datetime, timezone
from decimal import Decimal as D
from pathlib import Path
from types import SimpleNamespace

from qore.infrastructure.qdle_mt5_read_only import VerifiedFee, read_mt5_symbols
from qore.infrastructure.qore_dynamic_lot_engine import (
    QDLE, QDLEError, BrokerValuation, QDLEAccount, QDLESymbol, QDLEIntent,
)

AT = datetime(2026, 10, 8, 12, tzinfo=timezone.utc)


class Broker:
    def value(self, symbol, intent, now):
        return BrokerValuation(D("100"), D("200"), now, "SYNTHETIC_ONLY")
    def check_volume(self, symbol, intent, lots):
        return None


class MT5Fake:
    SYMBOL_TRADE_MODE_FULL = 4
    def symbol_info(self, name):
        return SimpleNamespace(volume_min=.01, volume_max=40, volume_step=.01,
           volume_limit=0, trade_tick_size=.00001, trade_tick_value_loss=1,
           trade_contract_size=100000, currency_profit="USD",
           visible=True, trade_mode=4)


class TestFeeGate(unittest.TestCase):
    def test_entry_only_seven_dollars_is_not_round_trip(self):
        with self.assertRaisesRegex(QDLEError, "round-trip"):
            VerifiedFee(D("7"), "MT5_MOBILE_ENTRY_ONLY")
        with self.assertRaises(QDLEError):
            VerifiedFee(D("0"), "UNKNOWN", covers_open_and_close=True)

    def test_verified_total_fee_retained_as_one_lot_cost(self):
        symbol = read_mt5_symbols(
            MT5Fake(), {"EURUSD": "EURUSD"},
            lambda name, info: VerifiedFee(
                D("14"), "BROKER_STATEMENT_ENTRY_EXIT_EXAMPLE",
                covers_open_and_close=True), as_of=AT)[0]
        self.assertEqual(symbol.fee_usd_per_lot, D("14"))
        self.assertTrue(symbol.fee_provenance.startswith("BROKER_ROUND_TRIP_VERIFIED:"))

    def test_live_presend_rejects_research_fee_even_when_reservation_exists(self):
        with tempfile.TemporaryDirectory() as d:
            e = QDLE(Path(d) / "qdle.sqlite", Broker(), enforce_finance_approval=True)
            e.publish_account(QDLEAccount(
                "123", "FundedNext", "USD", 1, AT,
                D("2000"), D("2000"), D("1900"),
                D("60"), D("60"), D("0"), D("60"),
            ))
            e.publish_symbol(QDLESymbol(
                "EURUSD", ("EURUSD",), D(".01"), D("40"), D(".01"),
                D("0"), D(".00001"), D("1"), D("100000"), "USD",
                D("7"), "MT5_MOBILE_ENTRY_ONLY", AT))
            i = QDLEIntent(
                "fee-p0", "trader31", "EURUSD", "BUY", D("1.1000"),
                D("1.0900"), D("3"), D("3"), D("3"),
                D("60"), D("40"), D("1900"), "SOVEREIGN_BANK", D("0"), 1)
            e.publish_finance_approval(i, AT)
            res = e.reserve_for_trader(i, AT)
            self.assertGreater(res.lots, 0)
            with self.assertRaisesRegex(QDLEError, "open AND close"):
                e.arm_for_live_send(
                    request_id="fee-p0", provider_symbol="EURUSD", side="BUY",
                    lots=res.lots, executable_entry=D("1.1000"),
                    stop_price=D("1.0900"), now=AT)
            self.assertEqual(e.health(now=AT)["pending_or_unreconciled_reservations"], 1)


if __name__ == "__main__":
    unittest.main()

"""Provider headroom is separate from USD2000 margin and USD60 QORE NAV."""
import tempfile
import unittest
from datetime import datetime, timezone
from decimal import Decimal as D
from pathlib import Path
from qore.infrastructure.qore_dynamic_lot_engine import (
    QDLE, QDLEAccount, QDLESymbol, QDLEIntent, BrokerValuation, QDLEError,
)

NOW = datetime(2026, 10, 8, 21, tzinfo=timezone.utc)

class Broker:
    def value(self, spec, intent, now):
        return BrokerValuation(D("100"), D("500"), now, "SYNTHETIC")
    def check_volume(self, spec, intent, lots):
        pass

def snapshot(seq=1, floor=None):
    return QDLEAccount(
        "123", "FundedNext", "USD", seq, NOW,
        D("2000"), D("2000"), D("1900"),
        D("60"), D("60"), D("0"), D("60"),
        provider_loss_floor_usd=D(floor) if floor is not None else None,
    )

def order(name="floor-test"):
    return QDLEIntent(
        name, "r31", "EURUSD", "BUY", D("1.1000"), D("1.0900"),
        D("3"), D("3"), D("3"), D("60"), D("40"),
        D("1900"), "SOVEREIGN_BANK", D("0"), 1,
    )

class TestProviderFloor(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.q = QDLE(Path(self.tmp.name)/"qdle.sqlite", Broker(),
            enforce_finance_approval=True, strict_live_fee_evidence=False,
            strict_four_motor_evidence=False)
        self.q.publish_symbol(QDLESymbol(
            "EURUSD", ("EURUSD",), D(".01"), D("40"), D(".01"),
            D("0"), D(".00001"), D("1"), D("100000"),
            "USD", D("0"), "SYNTHETIC", NOW))

    def tearDown(self):
        self.tmp.cleanup()

    def test_unknown_loss_floor_blocks_economic_allocation(self):
        self.q.publish_account(snapshot())
        self.q.publish_finance_approval(order(), NOW)
        with self.assertRaisesRegex(QDLEError, "unknown provider loss floor"):
            self.q.reserve_for_trader(order(), NOW)

    def test_loss_buffer_limits_lots_even_with_2000_broker_and_60_nav(self):
        self.q.publish_account(snapshot(floor="1998.5"))
        self.q.publish_finance_approval(order(), NOW)
        r = self.q.reserve_for_trader(order(), NOW)
        self.assertEqual(r.lots, D(".01"))
        self.assertEqual(r.total_risk_usd, D("1"))

    def test_no_lots_when_provider_headroom_smaller_than_one_minimum(self):
        self.q.publish_account(snapshot(floor="1999.5"))
        self.q.publish_finance_approval(order(), NOW)
        r = self.q.reserve_for_trader(order(), NOW)
        self.assertEqual(r.lots, D("0"))
        self.assertEqual(r.state, "UNFUNDABLE")

    def test_live_presend_blocks_risk_reaching_floor_exactly(self):
        self.q.publish_account(snapshot(floor="1999"))
        self.q.publish_finance_approval(order(), NOW)
        r = self.q.reserve_for_trader(order(), NOW)
        self.assertEqual(r.lots, D(".01"))
        with self.assertRaisesRegex(QDLEError, "could breach"):
            self.q.arm_for_live_send(
                request_id="floor-test", provider_symbol="EURUSD", side="BUY",
                lots=r.lots, executable_entry=D("1.1000"),
                stop_price=D("1.0900"), now=NOW)


if __name__ == "__main__":
    unittest.main()

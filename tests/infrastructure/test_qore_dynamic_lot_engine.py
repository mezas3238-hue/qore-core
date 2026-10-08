"""QDLE P0: atomic funding, real lot grids, six instrument aliases and MT5 ABI."""
from __future__ import annotations

import tempfile
import threading
import unittest
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from decimal import Decimal as D
from pathlib import Path
from types import SimpleNamespace

from qore.infrastructure.qore_dynamic_lot_engine import (
    BrokerValuation, Position, QDLE, QDLEAccount, QDLEError, QDLEIntent, QDLESymbol,
)
from qore.infrastructure.qdle_mt5_read_only import (
    MT5ReadOnlyCalculator, VerifiedFee,
    read_mt5_account_with_qore_treasury, read_mt5_symbols,
)

UTC = timezone.utc
T = datetime(2026, 10, 8, 12, tzinfo=UTC)


class DeterministicBroker:
    """Synthetic fixtures. These are NOT FundedNext's observed contract values."""
    stop = {
        "AUDJPY": D("42"), "EURUSD": D("100"), "GBPJPY": D("75"),
        "GBPUSD": D("90"), "NDX100": D("300"), "XAUUSD": D("200"),
    }
    def __init__(self):
        self.checks: list[tuple[str, D]] = []
        self.fail_preflight = False

    def value(self, instrument, intent, now):
        return BrokerValuation(self.stop[instrument.broker_symbol],
                               D("10"), now, "SYNTHETIC_TEST_ONLY")

    def check_volume(self, instrument, intent, lots):
        if self.fail_preflight:
            raise QDLEError("simulated broker rejected order_check")
        self.checks.append((instrument.broker_symbol, lots))


def account(seq=1, *, risk="100", sovereign="100", cushion="100",
            margin="100", positions=(), covered=(), time=T, capital="1000", broker_equity="1000"):
    return QDLEAccount("demo-123", "FundedNext", "USD", seq, time,
                       D(broker_equity), D(broker_equity), D(margin), D(risk),
                       D(sovereign), D(cushion), D(capital), tuple(positions), tuple(covered))


def symbol(name, aliases=(), time=T, **overrides):
    vals = dict(
        broker_symbol=name, aliases=tuple(aliases) or (name,),
        min_lot=D("0.01"), max_lot=D("100"), lot_step=D("0.01"),
        directional_volume_limit=D("0"), tick_size=D("0.01"),
        tick_value_loss_usd=D("1"), contract_size=D("100"),
        currency_profit="USD", fee_usd_per_lot=D("0"),
        fee_provenance="SYNTHETIC_TEST_ONLY", as_of=time, tradable=True,
    )
    vals.update(overrides)
    return QDLESymbol(**vals)


def intent(rid, name="EURUSD", *, seq=1, risk="3", lane="SOVEREIGN_BANK",
           leverage="100", sourcecap="100", fee_slippage="0"):
    return QDLEIntent(
        request_id=rid, trader_id="trader-31", symbol=name,
        side="BUY", entry_price=D("10"), stop_price=D("9"),
        requested_risk_usd=D(risk), sizing_cap_usd=D(risk),
        cibo_compound_cap_usd=D(risk), portfolio_cap_usd=D(sourcecap),
        leverage_cap_lots=D(leverage), margin_cap_usd=D("100"),
        source_lane=lane, slippage_usd_per_lot=D(fee_slippage),
        expected_account_sequence=seq,
    )


class TestQDLE(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / "fundednext.sqlite"
        self.broker = DeterministicBroker()
        self.engine = QDLE(self.path, self.broker)
        self.engine.publish_account(account())
        for name in DeterministicBroker.stop:
            aliases = ("NAS100", "NDX100") if name == "NDX100" else (name,)
            self.engine.publish_symbol(symbol(name, aliases))

    def tearDown(self):
        self.tmp.cleanup()

    def test_all_six_under_explicit_synthetic_quotes(self):
        expected = {"AUDJPY": "0.07", "EURUSD": "0.03", "GBPJPY": "0.04",
                    "GBPUSD": "0.03", "NDX100": "0.01", "XAUUSD": "0.01"}
        for name, volume in expected.items():
            r = self.engine.reserve_for_trader(intent("six:" + name,
                     name="NAS100" if name == "NDX100" else name), now=T)
            self.assertEqual(r.state, "RESERVED_FOR_TRADER")
            self.assertEqual(r.lots, D(volume))
            self.assertLessEqual(r.total_risk_usd, D("3"))
            self.assertEqual(r.symbol, name)
        self.assertEqual(len(self.broker.checks), 6)

    def test_2000_broker_margin_can_support_gold_and_ndx_with_60_qore_nav(self):
        # Synthetically replays screenshot margin, NOT MT5 execution certification.
        # Proprietary risk remains $3 while broker margin headroom is $1900.
        from dataclasses import replace

        class ScreenshotMarginMock:
            def value(self, instrument, intent, now):
                margins = {"XAUUSD": D("53637.48"), "NDX100": D("61481.98")}
                return BrokerValuation(D("100"), margins[instrument.broker_symbol],
                                       now, "SYNTHETIC_MARGIN_FROM_SCREENSHOT")
            def check_volume(self, instrument, intent, lots):
                return None

        for name in ("XAUUSD", "NDX100"):
            with self.subTest(symbol=name):
                path = Path(self.tmp.name) / f"{name}.sqlite"
                engine = QDLE(path, ScreenshotMarginMock())
                engine.publish_account(account(
                    capital="60", broker_equity="2000", risk="60",
                    sovereign="60", cushion="0", margin="1900",
                ))
                engine.publish_symbol(symbol(name, aliases=(name,),
                                             max_lot=D("50") if name == "XAUUSD" else D("40")))
                order = replace(intent(f"two-layers:{name}", name=name,
                                       risk="30", sourcecap="60"),
                                margin_cap_usd=D("1900"))
                result = engine.reserve_for_trader(order, now=T)
                self.assertEqual(result.lots, D("0.03"))
                self.assertEqual(result.total_risk_usd, D("3"))
                self.assertLessEqual(result.margin_usd, D("1900"))
                self.assertGreater(result.margin_usd, D("60"))

    def test_same_request_is_idempotent(self):
        first = self.engine.reserve_for_trader(intent("same"), now=T)
        again = self.engine.reserve_for_trader(intent("same"), now=T)
        self.assertEqual(first, again)
        self.assertEqual(len(self.broker.checks), 1)
        with self.assertRaises(QDLEError):
            self.engine.reserve_for_trader(intent("same", risk="5"), now=T)

    def test_multi_thread_and_multi_instance_atomic_reservations(self):
        self.engine.publish_account(account(2, risk="12", sovereign="12"))
        alt = QDLE(self.path, DeterministicBroker())
        alt.publish_account(account(3, risk="12", sovereign="12"))
        # The third event is the current one, shared by both instances.
        def call(i):
            engine = self.engine if i % 2 else alt
            return engine.reserve_for_trader(intent("race:" + str(i),
                seq=3, risk="10"), now=T)
        with ThreadPoolExecutor(max_workers=12) as pool:
            results = list(pool.map(call, range(25)))
        self.assertEqual(sum((r.total_risk_usd for r in results), D(0)), D("12"))
        self.assertEqual(sum(r.state == "RESERVED_FOR_TRADER" for r in results), 2)
        self.assertEqual(sum(r.state == "UNFUNDABLE" for r in results), 23)

    def test_restarts_are_fail_closed_and_holds_are_durable(self):
        first = self.engine.reserve_for_trader(intent("before", risk="8"), now=T)
        self.assertEqual(first.lots, D("0.08"))
        restarted = QDLE(self.path, DeterministicBroker())
        with self.assertRaises(QDLEError):
            restarted.reserve_for_trader(intent("after", seq=1), now=T)
        restarted.publish_account(account(2, risk="10", sovereign="10"))
        result = restarted.reserve_for_trader(intent("after", seq=2, risk="5"), now=T)
        self.assertEqual(result.lots, D("0.02"))  # held USD8 deducted

    def test_fill_is_not_released_before_qore_and_mt5_reconcile(self):
        reserved = self.engine.reserve_for_trader(intent("entry", risk="6"), now=T)
        self.engine.acknowledge_fill("entry", "broker:1")
        self.assertEqual(self.engine.health(now=T)["pending_or_unreconciled_reservations"], 1)
        with self.assertRaises(QDLEError):
            self.engine.reconcile_fill("entry")
        self.engine.publish_account(account(2, risk="20", sovereign="20",
            positions=(Position("broker:1", "EURUSD", "BUY", reserved.lots),)))
        with self.assertRaises(QDLEError):
            self.engine.reconcile_fill("entry")
        self.engine.publish_account(account(3, risk="20", sovereign="20",
            positions=(Position("broker:1", "EURUSD", "BUY", reserved.lots),),
            covered=("broker:1",)))
        self.engine.reconcile_fill("entry")
        self.assertEqual(self.engine.health(now=T)["pending_or_unreconciled_reservations"], 0)

    def test_manual_release_only_with_verified_broker_no_fill(self):
        self.engine.reserve_for_trader(intent("refused"), now=T)
        with self.assertRaises(QDLEError):
            self.engine.confirm_rejection("refused", "")
        self.engine.confirm_rejection("refused", "broker:ORDER_REJECTED:42")
        self.assertEqual(self.engine.health(now=T)["pending_or_unreconciled_reservations"], 0)

    def test_zero_capacity_blocked_without_fake_one_x(self):
        self.engine.publish_account(account(2, risk="0", sovereign="0", margin="0"))
        r = self.engine.reserve_for_trader(intent("zero", seq=2), now=T)
        self.assertEqual((r.state, r.lots), ("UNFUNDABLE", D(0)))

    def test_provider_fee_and_slippage_are_inside_loss_budget(self):
        self.engine.publish_symbol(symbol("EURUSD", time=T+timedelta(seconds=1),
                                 fee_usd_per_lot=D("7")))
        r = self.engine.reserve_for_trader(intent("fees", fee_slippage="3"), now=T+timedelta(seconds=1))
        self.assertEqual(r.lots, D("0.02"))
        self.assertEqual(r.total_risk_usd, D("2.20"))

    def test_funding_lanes_isolated(self):
        self.engine.publish_account(account(2, risk="100", sovereign="0", cushion="100"))
        r = self.engine.reserve_for_trader(intent("bank-zero", seq=2), now=T)
        self.assertEqual(r.state, "UNFUNDABLE")
        allowed = self.engine.reserve_for_trader(intent("cushion",
                seq=2, lane="PORTFOLIO_CUSHION"), now=T)
        self.assertEqual(allowed.state, "RESERVED_FOR_TRADER")

    def test_trade_direction_volume_limit_and_existing_positions(self):
        self.engine.publish_symbol(symbol("EURUSD", time=T+timedelta(seconds=1),
                                 directional_volume_limit=D("0.04")))
        self.engine.publish_account(account(2, positions=(
            Position("existing", "EURUSD", "BUY", D("0.03")),)))
        a = self.engine.reserve_for_trader(intent("limited", seq=2), now=T+timedelta(seconds=1))
        self.assertEqual(a.lots, D("0.01"))
        b = self.engine.reserve_for_trader(intent("blocked", seq=2), now=T+timedelta(seconds=1))
        self.assertEqual(b.state, "UNFUNDABLE")

    def test_broker_preflight_failure_keeps_no_reservation(self):
        self.broker.fail_preflight = True
        with self.assertRaises(QDLEError):
            self.engine.reserve_for_trader(intent("preflight"), now=T)
        self.assertEqual(self.engine.health(now=T)["pending_or_unreconciled_reservations"], 0)

    def test_account_stale_or_wrong_epoch_fails_closed(self):
        with self.assertRaises(QDLEError):
            self.engine.reserve_for_trader(intent("stale"), now=T+timedelta(seconds=30))
        with self.assertRaises(QDLEError):
            self.engine.reserve_for_trader(intent("wrong", seq=3), now=T)
        with self.assertRaises(QDLEError):
            self.engine.publish_account(account(1))

    def test_health_and_audit_telemetry(self):
        self.assertTrue(self.engine.health(now=T)["ready"])
        self.engine.reserve_for_trader(intent("audit"), now=T)
        events = self.engine.ledger()
        self.assertTrue(any(r["event"] == "VOLUME_RESERVED" for r in events))
        self.assertTrue(any(r["event"] == "SYMBOL_SPEC" for r in events))
        self.assertFalse(self.engine.health(now=T+timedelta(seconds=12))["ready"])


class FakeMT5:
    ORDER_TYPE_BUY = 0
    ORDER_TYPE_SELL = 1
    ORDER_TYPE_BUY_LIMIT = 2
    ORDER_TYPE_SELL_LIMIT = 3
    ORDER_TYPE_BUY_STOP = 4
    ORDER_TYPE_SELL_STOP = 5
    ORDER_TYPE_BUY_STOP_LIMIT = 6
    ORDER_TYPE_SELL_STOP_LIMIT = 7
    POSITION_TYPE_BUY = 0
    POSITION_TYPE_SELL = 1
    SYMBOL_TRADE_MODE_FULL = 4
    TRADE_ACTION_DEAL = 1

    def __init__(self):
        self.calls = []
        self.fail = False

    def account_info(self):
        return SimpleNamespace(login=123, currency="USD", balance=60,
                               equity=60, margin_free=50)
    def symbol_info(self, symbol):
        return SimpleNamespace(volume_min=.01, volume_max=100.,
                               volume_step=.01, volume_limit=1.,
                               trade_tick_size=.01, trade_tick_value_loss=1.,
                               trade_contract_size=100., currency_profit="USD",
                               visible=True, trade_mode=4)
    def positions_get(self):
        return ()
    def orders_get(self):
        return ()
    def order_calc_profit(self, *args):
        self.calls.append("order_calc_profit")
        return None if self.fail else -float(args[2]) * 100
    def order_calc_margin(self, *args):
        self.calls.append("order_calc_margin")
        return 10 * float(args[2])
    def order_check(self, request):
        self.calls.append("order_check")
        return SimpleNamespace(retcode=0)
    def last_error(self):
        return ("SYNTHETIC", 0)


class TestMT5Adapter(unittest.TestCase):
    def test_read_only_real_field_contract_and_six_aliases(self):
        mt5 = FakeMT5()
        mapping = {x:x for x in ("AUDJPY", "EURUSD", "GBPJPY",
                                 "GBPUSD", "XAUUSD")}
        mapping["NAS100"] = "NDX100"
        mapping["NDX100"] = "NDX100"
        items = read_mt5_symbols(mt5, mapping,
            lambda symbol, info: VerifiedFee(D("7"), "TEST_CONFIG_EVIDENCE"), as_of=T)
        self.assertEqual(len(items), 6)
        self.assertIn("NAS100", next(s for s in items
                      if s.broker_symbol == "NDX100").aliases)
        self.assertEqual(items[0].lot_step, D("0.01"))
        account_data = read_mt5_account_with_qore_treasury(mt5, account_id="123",
            sequence=1, qore_unreserved_risk_usd=D("5"),
            qore_trading_capital_usd=D("60"),
            sovereign_free_source_usd=D("5"),
            cushion_free_source_usd=D("0"), as_of=T)
        self.assertEqual(account_data.free_margin, D("50"))
        self.assertEqual(account_data.sovereign_free_source_usd, D("5"))
        calculator = MT5ReadOnlyCalculator(mt5, "123")
        q = calculator.value(items[0], intent("x", name="AUDJPY"), T)
        self.assertEqual(q.stop_loss_per_lot_usd, D("100"))
        calculator.check_volume(items[0], intent("x", name="AUDJPY"), D(".01"))
        self.assertEqual(mt5.calls,
                         ["order_calc_profit", "order_calc_margin", "order_check"])
        mt5.fail = True
        with self.assertRaises(QDLEError):
            calculator.value(items[0], intent("x", name="AUDJPY"), T)

    def test_unknown_fee_or_missing_symbol_fails_closed(self):
        with self.assertRaises(QDLEError):
            read_mt5_symbols(FakeMT5(), {"EURUSD":"EURUSD"},
                             lambda s, i: None, as_of=T)


if __name__ == "__main__":
    unittest.main()

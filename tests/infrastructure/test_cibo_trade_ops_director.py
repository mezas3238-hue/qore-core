"""Contract-first tests for Architect 1: synthetic events, no broker fills."""

import unittest
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from qore.infrastructure.cibo_trade_ops_director import (
    Action, ManagementEvidence, Stage, TradeOpsError, TradeOpsEvent,
    apply_trade_event, decide_position_management,
)

NOW = datetime(2026, 10, 8, 14, 0, tzinfo=UTC)
SHA = "sha256:" + "a" * 64


def ev(n, stage, **kwargs):
    args = dict(
        event_id=f"e{n}", signal_id="signal-1", trader_id="VT31",
        symbol="NDX100", side="BUY", stage=stage,
        occurred_at=NOW + timedelta(seconds=n),
        evidence_as_of=NOW + timedelta(seconds=n),
        evidence_sha256=SHA, reason="synthetic-test-evidence",
    )
    args.update(kwargs)
    return TradeOpsEvent(**args)


def funded():
    state = None
    for event in (
        ev(0, Stage.SIGNAL_RECEIVED), ev(1, Stage.ECONOMICALLY_VALUED),
        ev(2, Stage.ECONOMICALLY_FUNDED, requested_lots=Decimal("0.02")),
        ev(3, Stage.ORDER_SUBMITTED, order_id="order-1", broker_verified=True),
    ):
        state = apply_trade_event(state, event)
    return state


def open_position(side="BUY", symbol="NDX100"):
    state = None
    for event in (
        ev(0, Stage.SIGNAL_RECEIVED, side=side, symbol=symbol),
        ev(1, Stage.ECONOMICALLY_VALUED, side=side, symbol=symbol),
        ev(2, Stage.ECONOMICALLY_FUNDED, side=side, symbol=symbol,
           requested_lots=Decimal("0.02")),
        ev(3, Stage.ORDER_SUBMITTED, side=side, symbol=symbol, order_id="order-1",
           broker_verified=True),
        ev(4, Stage.FILLED, side=side, symbol=symbol, order_id="order-1",
           deal_id="deal-1", position_id="position-1",
           cumulative_filled_lots=Decimal("0.02"), broker_verified=True),
    ):
        state = apply_trade_event(state, event)
    return state


def quote(side="BUY", **kwargs):
    if side == "BUY":
        data = dict(
            bid=Decimal("1.0210"), ask=Decimal("1.0212"),
            entry_price=Decimal("1.0100"), structural_stop=Decimal("1.0000"),
            current_stop=Decimal("1.0000"), target_price=Decimal("1.0400"),
        )
    else:
        data = dict(
            bid=Decimal("1.0088"), ask=Decimal("1.0090"),
            entry_price=Decimal("1.0200"), structural_stop=Decimal("1.0300"),
            current_stop=Decimal("1.0300"), target_price=Decimal("0.9900"),
        )
    data.update(dict(
        observed_at=NOW + timedelta(seconds=5),
        quote_as_of=NOW + timedelta(seconds=4), quote_sha256=SHA,
        atr_as_of=NOW + timedelta(seconds=4), atr_price=Decimal("0.002"),
    ))
    data.update(kwargs)
    return ManagementEvidence(**data)


class TestCiboTradeOps(unittest.TestCase):
    def test_synthetic_signal_coverage_3368_without_invented_fills(self):
        ids = set()
        for n in range(3368):
            s = apply_trade_event(None, ev(0, Stage.SIGNAL_RECEIVED, signal_id=f"s{n}"))
            ids.add(s.signal_id)
            self.assertEqual(s.filled_lots, 0)
        self.assertEqual(len(ids), 3368)

    def test_funding_includes_opaque_external_lots_without_resizing(self):
        s = funded()
        self.assertEqual(s.requested_lots, Decimal("0.02"))
        self.assertEqual(s.filled_lots, Decimal(0))

    def test_unfundable_terminal_captures_signal(self):
        s = apply_trade_event(None, ev(0, Stage.SIGNAL_RECEIVED))
        s = apply_trade_event(s, ev(1, Stage.ECONOMICALLY_VALUED))
        s = apply_trade_event(s, ev(2, Stage.UNFUNDABLE, reason="minimum lot too risky"))
        self.assertEqual(s.stage, Stage.UNFUNDABLE)
        with self.assertRaises(TradeOpsError):
            apply_trade_event(s, ev(
                3, Stage.ORDER_SUBMITTED, order_id="bad", broker_verified=True
            ))

    def test_requires_broker_receipt_for_send_fill_close(self):
        s = funded()
        with self.assertRaises(TradeOpsError):
            apply_trade_event(s, ev(
                4, Stage.FILLED, order_id="order-1", deal_id="d", position_id="p",
                cumulative_filled_lots=Decimal("0.02")
            ))
        with self.assertRaises(TradeOpsError):
            apply_trade_event(open_position(), ev(
                5, Stage.CLOSED, order_id="order-1", deal_id="d2",
                position_id="position-1"
            ))

    def test_partial_then_remainder_cancel_then_close(self):
        s = funded()
        s = apply_trade_event(s, ev(
            4, Stage.PARTIAL, order_id="order-1", deal_id="d1",
            position_id="p1", cumulative_filled_lots=Decimal("0.01"), broker_verified=True
        ))
        with self.assertRaises(TradeOpsError):
            apply_trade_event(s, ev(5, Stage.MANAGED))
        with self.assertRaises(TradeOpsError):
            apply_trade_event(s, ev(
                5, Stage.CLOSED, order_id="order-1", deal_id="exit",
                position_id="p1", broker_verified=True
            ))
        s = apply_trade_event(s, ev(
            5, Stage.MANAGED, remainder_cancelled=True, broker_verified=True
        ))
        s = apply_trade_event(s, ev(
            6, Stage.CLOSED, order_id="order-1", deal_id="exit",
            position_id="p1", broker_verified=True
        ))
        self.assertEqual(s.stage, Stage.CLOSED)
        self.assertEqual(s.filled_lots, Decimal("0.01"))
        self.assertEqual(s.broker_deal_ids, ("d1", "exit"))

    def test_duplicate_deal_event_and_overfill_rejected(self):
        s = funded()
        s = apply_trade_event(s, ev(
            4, Stage.PARTIAL, order_id="order-1", deal_id="d1",
            position_id="p1", cumulative_filled_lots=Decimal("0.01"), broker_verified=True
        ))
        with self.assertRaises(TradeOpsError):
            apply_trade_event(s, ev(
                5, Stage.PARTIAL, order_id="order-1", deal_id="d1",
                position_id="p1", cumulative_filled_lots=Decimal("0.015"), broker_verified=True
            ))
        with self.assertRaises(TradeOpsError):
            apply_trade_event(s, ev(
                5, Stage.FILLED, order_id="order-1", deal_id="d2",
                position_id="p1", cumulative_filled_lots=Decimal("0.03"), broker_verified=True
            ))
        s = apply_trade_event(s, ev(
            5, Stage.FILLED, order_id="order-1", deal_id="d2",
            position_id="p1", cumulative_filled_lots=Decimal("0.02"), broker_verified=True
        ))
        self.assertEqual(s.filled_lots, Decimal("0.02"))

    def test_no_unauthorized_order_without_funding(self):
        s = apply_trade_event(None, ev(0, Stage.SIGNAL_RECEIVED))
        with self.assertRaises(TradeOpsError):
            apply_trade_event(s, ev(
                1, Stage.ORDER_SUBMITTED, order_id="o1", broker_verified=True
            ))

    def test_identity_time_leakage_and_duplicate_event(self):
        s = funded()
        for change in (
            dict(signal_id="alien"), dict(side="SELL"),
            dict(occurred_at=NOW - timedelta(days=1)), dict(event_id="e3"),
        ):
            with self.subTest(change=change), self.assertRaises(TradeOpsError):
                apply_trade_event(s, ev(
                    4, Stage.ORDER_REJECTED, order_id="order-1",
                    broker_verified=True, **change
                ))
        with self.assertRaises(TradeOpsError):
            ev(4, Stage.ORDER_REJECTED, evidence_as_of=NOW + timedelta(seconds=5))

    def test_monotonic_hash_chain_and_determinism(self):
        a, b = funded(), funded()
        self.assertEqual(a.audit_hash, b.audit_hash)
        self.assertEqual(len(a.event_ids), 4)
        rejected = apply_trade_event(a, ev(
            4, Stage.ORDER_REJECTED, order_id="order-1", broker_verified=True
        ))
        self.assertNotEqual(a.audit_hash, rejected.audit_hash)

    def test_buy_sell_fx_gold_index_breakeven_proposal_only(self):
        for symbol in ("AUDJPY", "EURUSD", "GBPJPY", "GBPUSD", "XAUUSD", "NDX100"):
            for side in ("BUY", "SELL"):
                with self.subTest(symbol=symbol, side=side):
                    s = open_position(side, symbol)
                    d = decide_position_management(s, quote(side))
                    self.assertEqual(d.action, Action.REQUEST_STOP_TO_BREAKEVEN)
                    self.assertFalse(d.execution_authorized)
                    self.assertTrue(d.requires_broker_valuation)
                    self.assertIsNone(d.risk_after_usd)

    def test_quote_touch_stop_requires_broker_confirmation(self):
        s = open_position()
        d = decide_position_management(s, quote(
            bid=Decimal("0.998"), ask=Decimal("0.999")
        ))
        self.assertEqual(d.action, Action.ESCALATE_STOP_BREACH)
        self.assertIsNone(d.proposed_stop)
        self.assertFalse(d.execution_authorized)

    def test_stale_quote_and_stale_atr_fail_to_no_action(self):
        s = open_position()
        d = decide_position_management(s, quote(
            quote_as_of=NOW - timedelta(minutes=2)
        ))
        self.assertEqual(d.action, Action.EVIDENCE_INSUFFICIENT)
        d = decide_position_management(s, quote(
            atr_as_of=NOW - timedelta(minutes=10)
        ))
        self.assertEqual(d.action, Action.EVIDENCE_INSUFFICIENT)

    def test_spread_news_floor_and_correlation_escalate(self):
        s = open_position()
        for change in (
            dict(news_risk=True), dict(provider_floor_pressure=True),
            dict(correlation_pressure=True), dict(ask=Decimal("1.023")),
        ):
            with self.subTest(change=change):
                self.assertEqual(
                    decide_position_management(s, quote(**change)).action,
                    Action.REQUEST_DEFENSIVE_REVIEW,
                )

    def test_causal_risk_before_after_requires_complete_valuation(self):
        s = open_position()
        kwargs = dict(
            current_stop_risk_usd=Decimal("3.00"),
            breakeven_stop_risk_usd=Decimal("0.25"),
            valuation_as_of=NOW + timedelta(seconds=4),
            valuation_sha256=SHA,
        )
        d = decide_position_management(s, quote(**kwargs))
        self.assertEqual(
            (d.risk_before_usd, d.risk_after_usd),
            (Decimal("3.00"), Decimal("0.25")),
        )
        self.assertFalse(d.requires_broker_valuation)
        with self.assertRaises(TradeOpsError):
            quote(**{**kwargs, "breakeven_stop_risk_usd": Decimal("4.00")})
        with self.assertRaises(TradeOpsError):
            quote(**{**kwargs, "valuation_as_of": NOW + timedelta(seconds=6)})
        with self.assertRaises(TradeOpsError):
            quote(current_stop_risk_usd=Decimal("3.00"))

    def test_no_future_market_features_and_invalid_stop_widening(self):
        for change in (
            dict(quote_as_of=NOW + timedelta(minutes=5)),
            dict(atr_as_of=NOW + timedelta(minutes=5)),
            dict(current_stop=Decimal("0.9900")),
        ):
            with self.subTest(change=change), self.assertRaises(TradeOpsError):
                decide_position_management(open_position(), quote(**change))

    def test_no_manage_unfunded_or_closed(self):
        with self.assertRaises(TradeOpsError):
            decide_position_management(funded(), quote())
        s = open_position()
        s = apply_trade_event(s, ev(
            5, Stage.CLOSED, order_id="order-1", deal_id="exit",
            position_id="position-1", broker_verified=True
        ))
        with self.assertRaises(TradeOpsError):
            decide_position_management(s, quote(
                observed_at=NOW + timedelta(seconds=6)
            ))

    def test_sensitivity_not_post_trade_profit(self):
        s = open_position()
        before = decide_position_management(s, quote())
        changed = decide_position_management(s, quote(
            bid=Decimal("1.011"), ask=Decimal("1.0112")
        ))
        self.assertNotEqual(before.decision_id, changed.decision_id)
        self.assertEqual(changed.action, Action.OBSERVE)
        self.assertFalse(changed.execution_authorized)


if __name__ == "__main__":
    unittest.main()

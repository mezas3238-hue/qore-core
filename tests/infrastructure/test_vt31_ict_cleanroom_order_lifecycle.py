"""Single trader VT31: no fabricated fills from M1 or quote-touch.

External execution acknowledgement is the ONLY reconciled fill evidence.
The research module never calls MT5 or mutates an actual account.
"""
from __future__ import annotations

import unittest
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from qore.infrastructure.traders.vt31_ict_cleanroom.contracts import (
    FvgCandidate,
    SessionId,
    Side,
)
from qore.infrastructure.traders.vt31_ict_cleanroom.order_lifecycle import (
    ExternalExecutionAck,
    OrderResearchState,
    SourceLimitOrderAudit,
    TwoSidedQuote,
)


class TestOrderLifecycle(unittest.TestCase):
    def setUp(self) -> None:
        # Jul 07 14:00 UTC = 10:00 New York, genuine ICT NY AM.
        self.start = datetime(2025, 7, 7, 14, tzinfo=UTC)
        self.t0 = self.start + timedelta(minutes=3)
        self.source = FvgCandidate(
            session=SessionId.NY_AM,
            side=Side.SHORT,
            formed_at=self.t0,
            first_candle_open=self.start,
            lower=Decimal("103"),
            upper=Decimal("106"),
            consequent_encroachment=Decimal("104.5"),
            target_price=Decimal("80"),
            projected_index_points=Decimal("22"),
            observed_context_at=self.t0,
        )

    def order(self, source: FvgCandidate | None = None) -> SourceLimitOrderAudit:
        return SourceLimitOrderAudit(
            client_order_id="VT31-NAS100-20250707-NYAM-0001",
            source=self.source if source is None else source,
            offered_at=self.t0,
            source_provenance="COG-CLEANROOM-HTF-CAUSAL",
        )

    def q(self, minute: int, bid: str, ask: str) -> TwoSidedQuote:
        return TwoSidedQuote(
            observed_at=self.t0 + timedelta(minutes=minute),
            bid=Decimal(bid),
            ask=Decimal(ask),
            source="NAS100-CANONICAL-BID-ASK-TEST",
        )

    def ack(self, *, executed_at: datetime | None = None,
            received_at: datetime | None = None,
            limit: str = "104.5") -> ExternalExecutionAck:
        executed = self.t0 + timedelta(minutes=2) if executed_at is None else executed_at
        received = executed if received_at is None else received_at
        return ExternalExecutionAck(
            client_order_id="VT31-NAS100-20250707-NYAM-0001",
            broker_execution_id="MT5-ACK-EXPLICIT-EVIDENCE",
            executed_at=executed,
            received_at=received,
            executed_price=Decimal(limit),
            executed_volume=Decimal("0.01"),
            broker="BROKER-AUDIT-EXPLICIT-TEST",
        )

    def test_quote_cross_is_not_execution(self) -> None:
        order = self.order()
        self.assertEqual(
            order.observe_quote(self.q(1, "103.8", "104.7")),
            OrderResearchState.PENDING_UNROUTED,
        )
        self.assertEqual(
            order.observe_quote(self.q(2, "104.5", "104.7")),
            OrderResearchState.QUOTE_CROSSED_NOT_FILLED,
        )
        snap = order.snapshot()
        self.assertTrue(snap["quote_crossed_not_broker_fill"])
        self.assertIsNone(snap["ack_id"])
        self.assertFalse(snap["paper_or_live_order_submitted"])
        self.assertFalse(snap["broker_api_called"])
        self.assertFalse(snap["live_authorized"])

    def test_buy_requires_ask_not_bid(self) -> None:
        long_source = replace(
            self.source, side=Side.LONG,
            target_price=Decimal("140"), projected_index_points=Decimal("22"),
        )
        order = self.order(long_source)
        self.assertEqual(
            order.observe_quote(self.q(1, "104.3", "104.8")),
            OrderResearchState.PENDING_UNROUTED,
        )
        self.assertEqual(
            order.observe_quote(self.q(2, "104.1", "104.4")),
            OrderResearchState.QUOTE_CROSSED_NOT_FILLED,
        )

    def test_no_same_instant_quote_fill_hindsight(self) -> None:
        with self.assertRaises(ValueError):
            self.order().observe_quote(self.q(0, "105", "105.2"))

    def test_invalid_bid_ask_spread(self) -> None:
        with self.assertRaises(ValueError):
            self.q(1, "105", "104")

    def test_legacy_fvg_timestamp_and_expiry_blocked(self) -> None:
        with self.assertRaises(ValueError):
            self.order(replace(self.source, formed_at=self.start + timedelta(hours=1)))
        with self.assertRaises(ValueError):
            SourceLimitOrderAudit(
                client_order_id="X", source=self.source,
                offered_at=self.start + timedelta(hours=1),
                source_provenance="COG",
            )

    def test_cancel_at_window_end_and_never_auto_exit_position(self) -> None:
        order = self.order()
        end = self.start + timedelta(hours=1)
        with self.assertRaises(ValueError):
            order.expire(end - timedelta(microseconds=1))
        self.assertEqual(
            order.expire(end),
            OrderResearchState.EXPIRED_BEFORE_PROVEN_FILL,
        )
        with self.assertRaises(ValueError):
            order.observe_quote(self.q(58, "110", "110.3"))

    def test_expiry_no_implied_fill_on_quote_at_boundary(self) -> None:
        order = self.order()
        self.assertEqual(
            order.observe_quote(self.q(57, "105", "106")),
            OrderResearchState.EXPIRED_BEFORE_PROVEN_FILL,
        )
        self.assertIsNone(order.snapshot()["ack_id"])

    def test_out_of_order_quote_rejected(self) -> None:
        order = self.order()
        order.observe_quote(self.q(1, "102", "103"))
        with self.assertRaises(ValueError):
            order.observe_quote(self.q(1, "102", "103"))

    def test_source_invalidation_does_not_claim_a_fill(self) -> None:
        order = self.order()
        order.observe_quote(self.q(1, "105", "105.5"))
        self.assertEqual(
            order.invalidate_source(self.t0 + timedelta(minutes=2)),
            OrderResearchState.INVALIDATED_BEFORE_PROVEN_FILL,
        )
        self.assertFalse(order.snapshot()["replay_order_economics_proven"])
        with self.assertRaises(ValueError):
            order.observe_quote(self.q(3, "105", "106"))

    def test_external_fill_ack_is_explicit_reconciled_evidence(self) -> None:
        order = self.order()
        order.observe_quote(self.q(1, "104.8", "105"))
        self.assertEqual(
            order.reconcile_broker_ack(self.ack()),
            OrderResearchState.EXECUTION_ACK_RECONCILED,
        )
        self.assertEqual(order.snapshot()["ack_id"], "MT5-ACK-EXPLICIT-EVIDENCE")
        self.assertFalse(order.snapshot()["source_order_routed"])
        self.assertEqual(
            order.expire(self.start + timedelta(hours=1)),
            OrderResearchState.EXECUTION_ACK_RECONCILED,
        )
        with self.assertRaises(ValueError):
            order.reconcile_broker_ack(self.ack())

    def test_external_ack_after_cancellation_is_reconciliation_race(self) -> None:
        order = self.order()
        order.invalidate_source(self.t0 + timedelta(minutes=4))
        ack = self.ack(received_at=self.t0 + timedelta(minutes=5))
        self.assertEqual(
            order.reconcile_broker_ack(ack),
            OrderResearchState.CANCEL_ACK_RACE_REQUIRES_RECONCILIATION,
        )
        self.assertTrue(order.snapshot()["broker_ack_conflicts_with_cancellation"])

    def test_invalid_or_unrelated_broker_ack(self) -> None:
        order = self.order()
        with self.assertRaises(ValueError):
            order.reconcile_broker_ack(self.ack(limit="103"))
        with self.assertRaises(ValueError):
            order.reconcile_broker_ack(replace(
                self.ack(), client_order_id="SOMEONE-ELSE-ORDER",
            ))
        with self.assertRaises(ValueError):
            order.reconcile_broker_ack(self.ack(
                executed_at=self.start + timedelta(hours=1),
            ))
        with self.assertRaises(ValueError):
            self.ack(received_at=self.t0)

    def test_genuinely_identical_single_trader_for_any_window(self) -> None:
        order = self.order()
        self.assertEqual(order.snapshot()["trader_id"], "VT31")
        self.assertEqual(order.snapshot()["session_window"], "VT31_NY_AM")
        self.assertEqual(order.snapshot()["instrument"], "NAS100")


if __name__ == "__main__":
    unittest.main()

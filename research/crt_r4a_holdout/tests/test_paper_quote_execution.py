"""Synthetic quote execution tests only; no historical profit certification."""
from __future__ import annotations

import unittest
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from research.crt_r4a_holdout.paper_quote_execution import (
    BidAskM5,
    CostAssumptions,
    SwapDebit,
    simulate_single,
)

D = Decimal
T = datetime(2024, 2, 1, tzinfo=UTC)


@dataclass(frozen=True)
class Plan:
    source_event_id: str = "TEST|CRT|1"
    family: str = "CRT_TEST"
    direction: int = 1
    planned_entry_type: str = "HYPOTHETICAL_H4_BODY_LIMIT"
    available_at: datetime = T
    expiry_at: datetime = T + timedelta(minutes=30)
    entry_price: Decimal = D("100")
    stop_price: Decimal = D("95")
    take_profit_price: Decimal = D("110")


def q(
    n: int, *, bo: str = "100", bh: str = "101",
    bl: str = "99", bc: str = "100",
    ao: str = "100.2", ah: str = "101.2",
    al: str = "99.2", ac: str = "100.2",
) -> BidAskM5:
    return BidAskM5(
        T + timedelta(minutes=5*n),
        D(bo), D(bh), D(bl), D(bc),
        D(ao), D(ah), D(al), D(ac),
    )


C0 = CostAssumptions(D("0"), D("0"))


class QuoteExecutionQA(unittest.TestCase):
    def test_01_entry_bar_stop_beats_target(self) -> None:
        bar = q(0, bo="100", bh="112", bl="94", bc="101",
                ao="100.2", ah="112.2", al="94.2", ac="101.2")
        r = simulate_single(Plan(), [bar], quantity=D("1"), costs=C0)
        self.assertEqual(r.status, "CLOSED_STOP")
        self.assertEqual(r.entry_fill, D("100"))
        self.assertEqual(r.exit_fill, D("95"))
        self.assertEqual(r.net_r, D("-1"))

    def test_02_retest_uses_next_ask_not_m15_close(self) -> None:
        p = Plan(planned_entry_type="HYPOTHETICAL_M15_CLOSE")
        bars = [q(0), q(1, bh="112", ah="112.2")]
        r = simulate_single(p, bars, quantity=D("1"), costs=C0)
        self.assertEqual(r.status, "CLOSED_TARGET")
        self.assertEqual(r.entry_fill, D("100.2"))
        self.assertEqual(r.exit_fill, D("110"))
        self.assertEqual(r.gross_quote, D("9.8"))

    def test_03_short_stop_uses_ask_with_adverse_slippage(self) -> None:
        p = Plan(direction=-1, stop_price=D("105"),
                 take_profit_price=D("90"))
        bar = q(0, bh="102", bl="98", ah="106", al="98.2",
                ao="100.2", ac="100.2")
        r = simulate_single(
            p, [bar], quantity=D("1"),
            costs=CostAssumptions(D("0"), D("0.1"))
        )
        self.assertEqual(r.status, "CLOSED_STOP")
        self.assertEqual(r.entry_fill, D("100"))
        self.assertEqual(r.exit_fill, D("105.1"))
        self.assertEqual(r.gross_quote, D("-5.1"))

    def test_04_no_retroactive_fill_in_pre_signal_candle(self) -> None:
        p = Plan(available_at=T + timedelta(minutes=5))
        bars = [q(0, al="90"), q(1, al="101", ao="102", ac="102",
                                  ah="103", bo="101.8", bc="101.8", bh="102.8", bl="101")]
        r = simulate_single(p, bars, quantity=D("1"), costs=C0)
        self.assertEqual(r.status, "NO_FILL_TAPE_END")

    def test_05_expiry_does_not_fake_trade(self) -> None:
        p = Plan(expiry_at=T + timedelta(minutes=5))
        r = simulate_single(p, [
            q(0, al="100.1"), q(1)
        ], quantity=D("1"), costs=C0)
        self.assertEqual(r.status, "EXPIRED_NO_FILL")
        self.assertIsNone(r.net_quote)

    def test_06_open_position_is_not_a_realized_win(self) -> None:
        r = simulate_single(Plan(), [q(0)], quantity=D("1"), costs=C0)
        self.assertEqual(r.status, "OPEN_UNSETTLED")
        self.assertIsNone(r.net_r)

    def test_07_commission_and_explicit_swap_debit(self) -> None:
        p = Plan(planned_entry_type="HYPOTHETICAL_M15_CLOSE")
        r = simulate_single(
            p, [q(0), q(1, bh="112", ah="112.2")],
            quantity=D("2"),
            costs=CostAssumptions(D("0.25"), D("0")),
            swap_debits=[
                SwapDebit(T + timedelta(minutes=7), D("0.3")),
            ]
        )
        self.assertEqual(r.status, "CLOSED_TARGET")
        self.assertEqual(r.gross_quote, D("19.6"))
        self.assertEqual(r.commission_quote, D("1.00"))
        self.assertEqual(r.swap_quote, D("0.6"))
        self.assertEqual(r.net_quote, D("18.0"))
        self.assertFalse(r.provider_costs_certified)
        self.assertEqual(r.broker_orders_executed, 0)

    def test_08_reject_nonmonotone_quotes(self) -> None:
        with self.assertRaisesRegex(ValueError, "nonmonotone"):
            simulate_single(Plan(), [q(0, al="100.1"), q(0)],
                            quantity=D("1"), costs=C0)

    def test_09_reject_illogical_bid_ask(self) -> None:
        with self.assertRaisesRegex(ValueError, "invalid bid/ask"):
            q(0, bo="101", ao="100")

    def test_10_no_future_order_from_naive_time(self) -> None:
        p = Plan(available_at=datetime(2024, 2, 1))
        with self.assertRaisesRegex(ValueError, "causal"):
            simulate_single(p, [], quantity=D("1"), costs=C0)

    def test_11_invalid_costs_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "cost"):
            CostAssumptions(D("-1"), D("0"))

    def test_12_broker_permissions_never_given(self) -> None:
        r = simulate_single(Plan(), [q(0)], quantity=D("1"), costs=C0)
        self.assertFalse(r.original_pine_parity_certified)
        self.assertFalse(r.provider_costs_certified)
        self.assertEqual(r.broker_orders_executed, 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)

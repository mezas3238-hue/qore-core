"""Synthetic-only economic bridge checks: never historical PnL evidence."""
from __future__ import annotations

import unittest
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from research.crt_r4a_holdout.economic_replay import (
    FrozenResearchSignal,
    QuoteEvidence,
    replay_symbol,
)
from research.crt_r4a_holdout.paper_quote_execution import (
    BidAskM5,
    CostAssumptions,
)
from research.crt_r4a_holdout.seven_family_contract import Family
from research.crt_r4a_holdout.seven_family_paper_plan import MarketGeometry

D = Decimal
T = datetime(2024, 2, 1, 8, tzinfo=UTC)
COSTS = CostAssumptions(D("0.1"), D("0.1"))
G = MarketGeometry(D("120"), D("100"), D("109"), D("110"), D("116"), D("99"),
                   retest_high=D("112"), retest_low=D("106"),
                   retest_close=D("111"), retest_closed_at=T)


def bar(
    index: int, *, bo: str = "110", bh: str = "111", bl: str = "108",
    bc: str = "110", ao: str = "110.2", ah: str = "111.2",
    al: str = "108.2", ac: str = "110.2",
) -> BidAskM5:
    return BidAskM5(
        T + timedelta(minutes=index * 5),
        D(bo), D(bh), D(bl), D(bc),
        D(ao), D(ah), D(al), D(ac),
    )


def ticket(
    family: Family = Family.TWO_C_MSS_C2, *,
    name: str = "signal-01", at: datetime = T,
    symbol: str = "EURUSD", provider: str = "SYNTHETIC_TEST_ONLY",
) -> FrozenResearchSignal:
    return FrozenResearchSignal(
        symbol=symbol, provider_cohort=provider,
        family=family, source_event_id=name,
        direction=1, mss_at=T - timedelta(minutes=15),
        ratified_at=(
            T - timedelta(minutes=30)
            if family is Family.TWO_C_MSS_C3 else T
        ), available_at=at,
        geometry=G, atr_h4=D("4"), price_tick=D("0.1"),
    )


def no_fill_bar(index: int = 0) -> BidAskM5:
    return bar(
        index, bo="112", bh="113", bl="111", bc="112",
        ao="112.2", ah="113.2", al="112", ac="112.2",
    )


def tape(*bars: BidAskM5) -> QuoteEvidence:
    return QuoteEvidence(
        "EURUSD", "SYNTHETIC_TEST_ONLY", tuple(bars), COSTS
    )


class SevenFamilyBridgeQA(unittest.TestCase):
    def test_01_ledger_replays_realistic_bid_ask_single_family(self) -> None:
        quotes = tape(
            bar(0, al="109.2"),  # limit 109.5 fills, no stop
            bar(1, bh="121", ah="121.2"),
        )
        result = replay_symbol((ticket(),), quotes, quantity=D("1"))
        self.assertEqual(result.all_families.closed, 1)
        self.assertEqual(result.all_families.wins, 1)
        self.assertEqual(result.all_families.without_fill, 0)
        self.assertIsNotNone(result.all_families.net_quote)
        self.assertFalse(result.broker_costs_certified)
        self.assertEqual(result.broker_orders_executed, 0)

    def test_02_no_realized_pnl_when_limit_never_fills(self) -> None:
        quotes = tape(no_fill_bar())
        result = replay_symbol((ticket(),), quotes, quantity=D("1"))
        self.assertEqual(result.all_families.closed, 0)
        self.assertIsNone(result.all_families.net_quote)
        self.assertIsNone(result.all_families.mean_net_r)
        self.assertIsNone(result.all_families.profit_factor_net_quote)

    def test_03_retest_requires_own_m15_close(self) -> None:
        sig = ticket(Family.M15_RETEST)
        quotes = tape(bar(0), bar(1, bh="121", ah="121.2"))
        result = replay_symbol((sig,), quotes, quantity=D("1"))
        self.assertEqual(result.all_families.closed, 1)
        self.assertEqual(result.observations[0].result.entry_fill, D("110.3"))

    def test_04_all_seven_families_are_accounted_individually(self) -> None:
        quotes = tape(no_fill_bar())
        result = replay_symbol(
            tuple(ticket(f, name=f.value) for f in Family),
            quotes, quantity=D("1"),
        )
        self.assertEqual(len(result.by_family), 7)
        self.assertEqual(result.all_families.signals, 7)
        self.assertTrue(all(x.signals == 1 for x in result.by_family.values()))

    def test_05_no_double_positions_for_same_available_time(self) -> None:
        quotes = tape(bar(0, al="109.2"), bar(1, bh="110"),
                      bar(2, bh="121", ah="121.2"))
        signals = (
            ticket(Family.TRUE_3C, name="c"),
            ticket(Family.TWO_C_MSS_C2, name="a"),
        )
        result = replay_symbol(signals, quotes, quantity=D("1"))
        self.assertEqual(result.all_families.closed, 1)
        self.assertEqual(result.all_families.blocked, 1)
        self.assertIn(
            "BLOCKED_OVERLAPPING_EXPOSURE",
            [o.status for o in result.observations],
        )

    def test_06_opposite_family_same_id_can_be_distinct_events(self) -> None:
        quotes = tape(no_fill_bar())
        r = replay_symbol(
            (ticket(name="one"), ticket(Family.MULTI4, name="one")),
            quotes, quantity=D("1"),
        )
        self.assertEqual(r.all_families.signals, 2)

    def test_07_duplicate_same_family_cannot_double_count(self) -> None:
        with self.assertRaisesRegex(ValueError, "duplicated"):
            replay_symbol(
                (ticket(), ticket()), tape(bar(0)), quantity=D("1")
            )

    def test_08_cross_provider_signal_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "feed identity"):
            replay_symbol(
                (ticket(provider="ATLAS_DEMO_BROKER_UNVERIFIED"),),
                tape(bar(0)), quantity=D("1"),
            )

    def test_09_symbol_mismatch_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "feed identity"):
            replay_symbol(
                (ticket(symbol="USDCAD"),), tape(bar(0)), quantity=D("1")
            )

    def test_10_naive_signal_timestamp_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "noncausal"):
            ticket(at=datetime(2024, 2, 1, 8))

    def test_11_unknown_model_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "unregistered"):
            FrozenResearchSignal(
                symbol="EURUSD", provider_cohort="SYNTHETIC_TEST_ONLY",
                family="CRT_INVALID", source_event_id="x", direction=1,
                mss_at=T, ratified_at=T, available_at=T,
                geometry=G, atr_h4=D("4"), price_tick=D("0.1"),
            )

    def test_12_invalid_pine_blob_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "unregistered"):
            FrozenResearchSignal(
                symbol="EURUSD", provider_cohort="SYNTHETIC_TEST_ONLY",
                family=Family.TRUE_3C, source_event_id="x",
                direction=1, mss_at=T, ratified_at=T, available_at=T,
                geometry=G, atr_h4=D("4"), price_tick=D("0.1"),
                source_pine_blob="changed-source",
            )

    def test_13_zero_size_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "quantity"):
            replay_symbol((ticket(),), tape(bar(0)), quantity=D("0"))

    def test_14_zero_events_not_a_profitable_strategy(self) -> None:
        result = replay_symbol((), tape(bar(0)), quantity=D("1"))
        self.assertEqual(result.all_families.signals, 0)
        self.assertIsNone(result.all_families.net_quote)
        self.assertIsNone(result.all_families.profit_factor_net_quote)

    def test_15_unsupported_provider_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "unregistered"):
            ticket(provider="IC_CERTIFIED")

    def test_16_explicit_cost_hypotheses_never_certify_broker(self) -> None:
        quotes = tape(bar(0, al="109.2"), bar(1, bh="121", ah="121.2"))
        result = replay_symbol((ticket(),), quotes, quantity=D("1"))
        self.assertFalse(result.account_currency_pnl_certified)
        self.assertFalse(result.pine_parity_certified)
        self.assertFalse(result.holdout_24m_certified)
        self.assertFalse(result.broker_costs_certified)
        self.assertEqual(result.status, "EXPERIMENTAL_QUOTE_PRICE_REPLAY_NOT_CERTIFIED")

    def test_17_reject_unordered_bid_ask_data(self) -> None:
        with self.assertRaisesRegex(ValueError, "chronologically"):
            tape(bar(1), bar(0))

    def test_18_reject_quote_gap_after_open(self) -> None:
        quotes = tape(bar(0, al="109.2"), bar(4, bh="121", ah="121.2"))
        result = replay_symbol((ticket(),), quotes, quantity=D("1"))
        self.assertEqual(result.all_families.closed, 0)
        self.assertEqual(result.all_families.blocked, 1)
        self.assertEqual(result.observations[0].status, "BLOCKED_QUOTE_GAP")


    def test_19_wrong_c3_mss_timing_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "own-family"):
            FrozenResearchSignal(
                symbol="EURUSD", provider_cohort="SYNTHETIC_TEST_ONLY",
                family=Family.TWO_C_MSS_C3, source_event_id="invalid",
                direction=1, mss_at=T - timedelta(minutes=15),
                ratified_at=T, available_at=T,
                geometry=G, atr_h4=D("4"), price_tick=D("0.1"),
            )

    def test_20_wrong_c2_mss_timing_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "own-family"):
            FrozenResearchSignal(
                symbol="EURUSD", provider_cohort="SYNTHETIC_TEST_ONLY",
                family=Family.TWO_C_MSS_C2, source_event_id="invalid",
                direction=1, mss_at=T + timedelta(minutes=5),
                ratified_at=T, available_at=T + timedelta(minutes=5),
                geometry=G, atr_h4=D("4"), price_tick=D("0.1"),
            )


if __name__ == "__main__":
    unittest.main(verbosity=2)

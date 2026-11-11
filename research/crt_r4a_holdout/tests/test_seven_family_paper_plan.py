"""Synthetic-only paper risk brackets for seven independent CRT families."""
from __future__ import annotations

import unittest
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from research.crt_r4a_holdout.seven_family_contract import Family
from research.crt_r4a_holdout.seven_family_paper_plan import (
    MarketGeometry,
    plan_research_order,
)

T = datetime(2024, 2, 1, 8, tzinfo=UTC)
D = Decimal


def geometry() -> MarketGeometry:
    return MarketGeometry(
        c1_high=D("120"), c1_low=D("100"),
        setup_open=D("109"), setup_close=D("110"),
        sweep_high=D("116"), sweep_low=D("99"),
        retest_high=D("112"), retest_low=D("106"),
    )


def plan(family: Family, **kwargs: object):
    args = {
        "direction": 1, "source_event_id": "EURUSD|C1|unique",
        "geometry": geometry(), "available_at": T,
        "mss_at": T - timedelta(minutes=15),
        "ratified_at": T, "atr_h4": D("4"),
        "price_tick": D("0.1"),
    }
    args.update(kwargs)
    return plan_research_order(family, **args)


class SevenPaperHypotheses(unittest.TestCase):
    def test_01_each_registered_family_can_build_paper_plan(self) -> None:
        for family in Family:
            result = plan(family)
            self.assertEqual(result.family, family)
            self.assertGreater(result.reward_to_risk, 0)
            self.assertEqual(result.broker_orders_executed, 0)
            self.assertIs(result.pine_parity_certified, False)
            self.assertIs(result.broker_net_costs_certified, False)

    def test_02_h4_body_midpoint_limit_for_six(self) -> None:
        for family in Family:
            if family == Family.M15_RETEST:
                continue
            result = plan(family)
            self.assertEqual(result.entry_price, D("109.5"))
            self.assertEqual(
                result.planned_entry_type, "HYPOTHETICAL_H4_BODY_LIMIT"
            )

    def test_03_retest_uses_own_m15_close_not_h4_midpoint(self) -> None:
        result = plan(Family.M15_RETEST)
        self.assertEqual(result.entry_price, D("110"))
        self.assertEqual(result.stop_price, D("105"))
        self.assertEqual(result.planned_entry_type, "HYPOTHETICAL_M15_CLOSE")

    def test_04_stop_behind_own_sweep_long(self) -> None:
        result = plan(Family.MULTI4)
        self.assertEqual(result.stop_price, D("98"))
        self.assertEqual(result.take_profit_price, D("120"))
        self.assertEqual(result.risk_price_distance, D("11.5"))

    def test_05_short_uses_opposite_c1_endpoint(self) -> None:
        result = plan(
            Family.MULTIN, direction=-1,
            geometry=MarketGeometry(
                D("120"), D("100"), D("111"), D("110"),
                D("121"), D("105")
            )
        )
        self.assertEqual(result.stop_price, D("122"))
        self.assertEqual(result.take_profit_price, D("100"))
        self.assertEqual(result.entry_price, D("110.5"))

    def test_06_broker_spread_quote_widens_stop(self) -> None:
        result = plan(Family.INSIDE_RETURN, spread_quote=D("2"))
        self.assertEqual(result.stop_price, D("97"))
        self.assertLess(result.reward_to_risk, plan(
            Family.INSIDE_RETURN
        ).reward_to_risk)

    def test_07_never_enter_before_mss_is_confirmed(self) -> None:
        with self.assertRaisesRegex(ValueError, "future-looking"):
            plan(Family.TRUE_3C, mss_at=T + timedelta(minutes=5))

    def test_08_never_enter_before_h4_ratifies(self) -> None:
        with self.assertRaisesRegex(ValueError, "future-looking"):
            plan(Family.TWO_C_MSS_C2, ratified_at=T + timedelta(hours=4))

    def test_09_bad_family_or_missing_identity_rejected(self) -> None:
        with self.assertRaises(ValueError):
            plan("CRT_PENDING")
        with self.assertRaises(ValueError):
            plan(Family.MULTIN, source_event_id="")

    def test_10_too_far_from_close_does_not_backfill_limit(self) -> None:
        g = MarketGeometry(
            D("120"), D("100"), D("100"), D("110"),
            D("116"), D("99")
        )
        with self.assertRaisesRegex(ValueError, "too far"):
            plan(Family.MULTI4, geometry=g)

    def test_11_retest_requires_m15_own_high_low(self) -> None:
        g = MarketGeometry(
            D("120"), D("100"), D("109"), D("110"),
            D("116"), D("99"),
        )
        with self.assertRaisesRegex(ValueError, "OWN closed M15"):
            plan(Family.M15_RETEST, geometry=g)

    def test_12_limit_expiry_three_h4_and_no_trade(self) -> None:
        r = plan(Family.TRUE_3C)
        self.assertEqual(r.expiry_at, T + timedelta(hours=12))
        self.assertEqual(r.broker_orders_executed, 0)

    def test_13_costs_not_inferred_from_spread(self) -> None:
        r = plan(Family.TRUE_3C, spread_quote=D("0.3"))
        self.assertIs(r.broker_net_costs_certified, False)

    def test_14_invalid_price_geometry_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "invalid"):
            MarketGeometry(
                D("100"), D("120"), D("110"), D("110"),
                D("116"), D("99")
            )

    def test_15_invalid_broker_tick_blocked(self) -> None:
        with self.assertRaisesRegex(ValueError, "ATR/tick"):
            plan(Family.TRUE_3C, price_tick=D("0"))

    def test_16_invalid_negative_spread_blocked(self) -> None:
        with self.assertRaisesRegex(ValueError, "spread"):
            plan(Family.TRUE_3C, spread_quote=D("-0.1"))

    def test_17_expiry_must_be_small_positive_h4_window(self) -> None:
        for n in (0, 4, -1):
            with self.assertRaisesRegex(ValueError, "parameter"):
                plan(Family.TRUE_3C, expiry_h4=n)

    def test_18_stop_or_target_wrong_direction_rejected(self) -> None:
        g = MarketGeometry(
            D("120"), D("100"), D("130"), D("130"),
            D("125"), D("101")
        )
        with self.assertRaises(ValueError):
            plan(Family.TRUE_3C, geometry=g, atr_h4=D("10"))

    def test_19_exact_time_offset_required(self) -> None:
        with self.assertRaisesRegex(ValueError, "UTC offset"):
            plan(
                Family.TRUE_3C,
                available_at=datetime(2024, 2, 1, 8),
            )


if __name__ == "__main__":
    unittest.main(verbosity=2)

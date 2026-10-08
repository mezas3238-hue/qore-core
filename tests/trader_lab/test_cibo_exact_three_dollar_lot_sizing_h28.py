"""H28 fail-closed dollar-risk sizing: exact USD3 or no fabricated fill."""
import unittest
from decimal import Decimal as D

from qore.infrastructure.trader_lab.cibo_exact_three_dollar_lot_sizing_h28 import (
    BrokerLotContract, plan_exact_stop,
)


class TestExactStopDollarRisk(unittest.TestCase):
    def test_three_usd_supported_in_legal_lots(self):
        p=plan_exact_stop(
            capital_usd=D("60"), target_at_stop_usd=D("3"),
            available_unreserved_cash_usd=D("60"),
            contract=BrokerLotContract(
                min_lots=D(".01"),lot_step=D(".01"),max_lots=D("10"),
                stop_risk_usd_per_lot=D("30"),margin_usd_per_lot=D("5"),
                roundtrip_fee_usd_per_lot=D("14"),
            ),
        )
        self.assertTrue(p.accepted)
        self.assertEqual(p.lots,D(".10"))
        self.assertEqual(p.actual_stop_usd,D("3"))
        self.assertEqual(p.fee_usd,D("1.4"))

    def test_nas100_historical_unit_exact_three_unrepresentable(self):
        p=plan_exact_stop(
            capital_usd=D("60"), target_at_stop_usd=D("3"),
            available_unreserved_cash_usd=D("60"),
            contract=BrokerLotContract(
                min_lots=D(".1"),lot_step=D(".1"),max_lots=D("20"),
                stop_risk_usd_per_lot=D("2.95"),
                margin_usd_per_lot=D("777.885"),
                roundtrip_fee_usd_per_lot=D("14"),
            ),
        )
        self.assertFalse(p.accepted)
        self.assertEqual(p.reason,"EXACT_STOP_NOT_REPRESENTABLE_IN_BROKER_LOT_STEPS")
        self.assertEqual(p.lower_attainable_stop_usd,D("2.95"))
        self.assertEqual(p.upper_attainable_stop_usd,D("3.245"))

    def test_nas100_min_lot_margin_more_than_sixty(self):
        p=plan_exact_stop(
            capital_usd=D("60"), target_at_stop_usd=D(".295"),
            available_unreserved_cash_usd=D("60"),
            contract=BrokerLotContract(
                min_lots=D(".1"),lot_step=D(".1"),max_lots=D("20"),
                stop_risk_usd_per_lot=D("2.95"),
                margin_usd_per_lot=D("777.885"),
                roundtrip_fee_usd_per_lot=D("14"),
            ),
        )
        self.assertFalse(p.accepted)
        self.assertEqual(p.reason,"MARGIN_AND_FEES_NOT_FUNDED_WITH_UNRESERVED_CASH")

    def test_no_liquid_reserve_no_fill(self):
        p=plan_exact_stop(
            capital_usd=D("60"),target_at_stop_usd=D("3"),
            available_unreserved_cash_usd=D("1"),
            contract=BrokerLotContract(
                min_lots=D(".01"),lot_step=D(".01"),max_lots=D("10"),
                stop_risk_usd_per_lot=D("30"),margin_usd_per_lot=D("5"),
                roundtrip_fee_usd_per_lot=D("14"),
            ),
        )
        self.assertFalse(p.accepted)
        self.assertEqual(p.reason,"MARGIN_AND_FEES_NOT_FUNDED_WITH_UNRESERVED_CASH")

    def test_target_stop_over_five_percent_refused(self):
        p=plan_exact_stop(
            capital_usd=D("60"),target_at_stop_usd=D("6"),
            available_unreserved_cash_usd=D("60"),
            contract=BrokerLotContract(
                min_lots=D(".01"),lot_step=D(".01"),max_lots=D("10"),
                stop_risk_usd_per_lot=D("30"),margin_usd_per_lot=D("5"),
            ),
        )
        self.assertFalse(p.accepted)
        self.assertEqual(p.reason,"STOP_EXCEEDS_5PCT_CURRENT_CAPITAL")

    def test_real_growth_recalculates_current_stop_target(self):
        p=plan_exact_stop(
            capital_usd=D("100"),target_at_stop_usd=D("5"),
            available_unreserved_cash_usd=D("40"),
            contract=BrokerLotContract(
                min_lots=D(".01"),lot_step=D(".01"),max_lots=D("10"),
                stop_risk_usd_per_lot=D("50"),margin_usd_per_lot=D("5"),
            ),
        )
        self.assertTrue(p.accepted)
        self.assertEqual(p.actual_stop_usd,D("5"))


if __name__=="__main__":
    unittest.main()

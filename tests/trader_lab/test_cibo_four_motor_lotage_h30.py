import unittest
from dataclasses import replace
from decimal import Decimal as D
from qore.infrastructure.trader_lab.cibo_four_motor_lotage_h30 import (
    LotageContext, coordinate_four_motor_lotage,
    sizing_lotage,cibo_compound_lotage,portfolio_compound_lotage,adaptive_leverage_lotage
)


def setup(**kw):
    base=LotageContext(
        mode="MEDIUM",equity_usd=D(60),initial_capital_usd=D(60),
        initial_stop_target_usd=D("2.95"), min_lots=D(".1"),step_lots=D(".1"),
        max_multiplier=2500,native_cap=20,
        stop_usd_per_min_lot=D(".295"),margin_usd_per_min_lot=D("15.299"),
        fee_usd_per_min_lot=D(".10"),risk_left_usd=D("10"),
        margin_left_usd=D("6000"),bank_free_usd=D(60),
        cushion_free_usd=D(10),portfolio_credit_free_usd=D(10),
        strict_account_cash_margin=True)
    return replace(base,**kw)


class FourMotorLotageTests(unittest.TestCase):
    def test_all_four_distinct_budget_calculators(self):
        c=setup()
        a=sizing_lotage(c);b=cibo_compound_lotage(c,a)
        d=portfolio_compound_lotage(c,b);e=adaptive_leverage_lotage(c,d)
        self.assertEqual([x.motor for x in (a,b,d,e)],
                         ["SIZING","CIBO_COMPOUND","COMPOUND_PORTFOLIO","ADAPTIVE_LEVERAGE"])
        self.assertEqual(a.approved_lots,D("1.0"))
        self.assertEqual(b.approved_lots,D("1.0"))
        self.assertEqual(d.approved_lots,D("1.0"))
        self.assertEqual(e.approved_lots,D(".3")) # physical $60 margin at $152.99 / lot
        p=coordinate_four_motor_lotage(c)
        self.assertEqual(p.selected_stop_usd,D(".885"))
        self.assertEqual(p.requested_stop_usd,D("2.95"))
        self.assertFalse(p.target_attained)
        self.assertTrue(p.minimum_lot_fundable)

    def test_three_dollar_model_margin_overcash_not_faked(self):
        c=setup(equity_usd=D(60), strict_account_cash_margin=False)
        p=coordinate_four_motor_lotage(c)
        self.assertEqual(p.selected_multiplier,10)
        self.assertEqual(p.selected_stop_usd,D("2.95"))
        self.assertTrue(p.target_attained)
        self.assertNotEqual(coordinate_four_motor_lotage(setup()).selected_multiplier,10)

    def test_economic_capital_compounds_target_and_stop(self):
        c=setup(equity_usd=D(120),bank_free_usd=D(120),margin_left_usd=D(9000))
        p=coordinate_four_motor_lotage(c)
        self.assertEqual(p.requested_stop_usd,D("5.90"))
        self.assertEqual(p.selected_stop_usd,D("2.065")) # 120/15.299 = 7.84 => 7x
        self.assertEqual(p.selected_multiplier,7)

    def test_bank_is_never_spent_by_attack(self):
        c=setup(mode="ATTACK",bank_free_usd=D("10000"),cushion_free_usd=D("0.60"),
                portfolio_credit_free_usd=D(".6"))
        p=coordinate_four_motor_lotage(c)
        self.assertEqual(p.selected_multiplier,1)
        self.assertEqual(p.selected_stop_usd,D(".295"))
        c2=replace(c,cushion_free_usd=D(".1"))
        p2=coordinate_four_motor_lotage(c2)
        self.assertEqual(p2.selected_multiplier,0)
        self.assertFalse(p2.funded)

    def test_unreserved_risk_not_double_spent(self):
        c=setup(risk_left_usd=D(".6"))
        p=coordinate_four_motor_lotage(c)
        self.assertEqual(p.selected_multiplier,2)
        self.assertEqual(p.selected_stop_usd,D(".59"))

    def test_minlot_physical_funding_blocked(self):
        c=setup(equity_usd=D(10),bank_free_usd=D(10))
        p=coordinate_four_motor_lotage(c)
        self.assertFalse(p.funded)
        self.assertFalse(p.minimum_lot_fundable)

    def test_min_lot_step_mismatch_fails_closed(self):
        with self.assertRaises(ValueError):
            coordinate_four_motor_lotage(setup(step_lots=D(".01")))

    def test_no_negative_wallet(self):
        with self.assertRaises(ValueError):
            coordinate_four_motor_lotage(setup(cushion_free_usd=D(-1)))

if __name__=="__main__":
    unittest.main()

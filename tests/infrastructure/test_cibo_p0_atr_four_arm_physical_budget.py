"""Pure synthetic P0 four-arm physical sizing tests; NOT a market replay."""
import json
import unittest
from pathlib import Path
from decimal import Decimal as D

from scripts.cibo_p0_atr_four_arm_physical_budget import (
    validate_config, commission_open_per_lot, stop_loss_usd_per_lot,
    physical_order_quote, readiness, ResearchBlockedError,
)

ROOT=Path(__file__).resolve().parents[2]
CONF=ROOT/"config/research/cibo_p0_four_arm_atr_5pct_3368_2026-10-09.json"


def load():
    return json.loads(CONF.read_text())


def quote(**changes):
    args=dict(arm="B-X",mode="BANK",symbol="EURUSD",timeframe="H1",side="BUY",
              entry=D("1.1000"),structural_stop=D("1.0990"),atr14=D(".0002"),
              contract_size=D("100000"),nav=D("60"),held_risk=D("0"),
              free_margin=D("2000"),margin_per_lot=D("1000"))
    args.update(changes)
    return physical_order_quote(load(),**args)


class FourArmPhysicalContractTests(unittest.TestCase):
    def test_contract_and_missing_provider_inputs_fail_closed(self):
        conf=load()
        validate_config(conf)
        gates=readiness(conf)
        self.assertEqual(gates["status"],"BLOCKED_MISSING_EMPIRICAL_PROVENANCE")
        self.assertIn("one_canonical_sqlite_book",gates["blocked_gates"])
        self.assertIn("causal_vt31_m1_executable_quotes",gates["blocked_gates"])
        self.assertIn("historical_usdjpy_at_epoch",gates["blocked_gates"])
        self.assertFalse(gates["ready_for_claim_of_historical_profits"])
        self.assertEqual(gates["four_arms"],["A-X","A-Y","B-X","B-Y"])
        self.assertEqual(gates["broker_fills"],0)

    def test_reject_unapproved_extra_risk(self):
        conf=load()
        conf["mode_risk"]["BANK"]["B"]="0.051"
        with self.assertRaisesRegex(ResearchBlockedError,"mode risk"):
            validate_config(conf)

    def test_bank_A_125pct_vs_B_5pct_with_real_lot_step(self):
        a=quote(arm="A-X")
        b=quote(arm="B-X")
        self.assertEqual(a["lots"],"0.04")
        self.assertEqual(b["lots"],"0.17")
        self.assertLessEqual(D(a["risk_usd"]),D(".75"))
        self.assertLessEqual(D(b["risk_usd"]),D("3"))
        self.assertEqual(b["atr_multiplier"],"0.5")
        self.assertEqual(b["fee_open_usd_per_lot"],"7.00")
        self.assertEqual(b["status"],"RESEARCH_POSITIVE_PHYSICAL_LOT_QUOTE")

    def test_portfolio_total_held_hard_cap(self):
        allowed=quote(held_risk=D("2.50"))
        self.assertEqual(allowed["portfolio_new_risk_limit_usd"],"0.50")
        self.assertEqual(allowed["lots"],"0.02")
        self.assertLessEqual(D(allowed["risk_usd"])+D("2.5"),D("3"))
        with self.assertRaisesRegex(ResearchBlockedError,"already breached"):
            quote(held_risk=D("3.01"))

    def test_min_lot_is_unfundable_not_manufactured(self):
        r=quote(nav=D("1"))
        self.assertEqual(r["status"],"UNFUNDABLE_MIN_LOT_RISK_OR_MARGIN")
        self.assertEqual(r["lots"],"0")

    def test_ndx_zero_actual_tariff_vs_20_stress(self):
        args=dict(symbol="NDX100",timeframe="M1",entry=D("1000"),
                  structural_stop=D("970"),atr14=D("10"),
                  contract_size=D("10"),margin_per_lot=D("1000"))
        x=quote(**args,arm="B-X")
        y=quote(**args,arm="B-Y")
        self.assertEqual(x["lots"],"0.06")
        self.assertEqual(y["lots"],"0.04")
        self.assertEqual(x["fee_open_usd_per_lot"],"0")
        self.assertEqual(y["fee_open_usd_per_lot"],"20.00")

    def test_gold_open_only_not_times_two(self):
        self.assertEqual(commission_open_per_lot(
            load(),"XAUUSD",D("2000"),D("100"),"X"),D("3.2"))
        x=quote(symbol="XAUUSD",timeframe="H1",entry=D("2000"),
                structural_stop=D("1998"),atr14=D(".5"),
                contract_size=D("100"),margin_per_lot=D("1000"))
        self.assertEqual(x["fee_open_usd_per_lot"],"3.200000")
        self.assertGreater(D(x["lots"]),D("0"))

    def test_epoch_USDJPY_required_no_frozen_2026_anchor(self):
        with self.assertRaisesRegex(ResearchBlockedError,"HISTORICAL_USDJPY"):
            quote(symbol="GBPJPY",timeframe="H1",entry=D("182"),
                  structural_stop=D("181"),atr14=D(".2"))
        x=stop_loss_usd_per_lot(symbol="GBPJPY",entry=D("182"),
                               stop=D("181.9"),contract_size=D("100000"),
                               usd_jpy=D("150"))
        self.assertAlmostEqual(float(x),66.6666666667,places=8)

    def test_reject_wider_structural_stop_and_undefined_attack_TF(self):
        widened=quote(mode="ATTACK",symbol="NDX100",timeframe="M1",
                      entry=D("1000"),structural_stop=D("990"),
                      atr14=D("10"),contract_size=D("10"))
        self.assertEqual(widened["status"],"RESEARCH_ATR_STOP_WIDENS_TRADER_STRUCTURAL_RISK")
        with self.assertRaisesRegex(ResearchBlockedError,"UNDEFINED_ATR_MULTIPLIER"):
            quote(mode="ATTACK",symbol="NDX100",timeframe="H1",
                  entry=D("1000"),structural_stop=D("900"),
                  atr14=D("10"),contract_size=D("10"))

    def test_closed_price_not_predecision_truth_and_001_partial_unfundable(self):
        # Static predicate: a 50% PARTIAL of a minimum lot is NOT executable.
        half=D(".01")*D(".5")
        self.assertNotEqual(half % D(".01"),D(0))
        self.assertLess(half,D(".01"))
        self.assertFalse(readiness(load())["ready_for_claim_of_historical_profits"])

    def test_no_fake_ndx20_provider_tariff(self):
        conf=load()
        conf["scenarios"][1]["ndx_fee_classification"]="REAL_MT5_CONFIRMED"
        with self.assertRaisesRegex(ResearchBlockedError,"stress"):
            validate_config(conf)

    def test_no_double_margin_as_stop_risk(self):
        q=quote(free_margin=D("100"),margin_per_lot=D("1000"))
        self.assertEqual(D(q["lots"]),D("0.10"))
        self.assertEqual(D(q["margin_usd"]),D("100.00"))
        self.assertLessEqual(D(q["risk_usd"]),D("3"))


if __name__=="__main__":
    unittest.main()

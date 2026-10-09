"""CIBO Compuesto audit is read-only, detects actual three-loss 50% haircut."""
from __future__ import annotations

import importlib.util
import sys
import unittest
from decimal import Decimal as D
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
SPEC=importlib.util.spec_from_file_location(
    "cibo_p0_compound_replay_audit", ROOT/"scripts/cibo_p0_compound_replay_audit.py"
)
M=importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name]=M
SPEC.loader.exec_module(M)


def fixture(*,compound="1.50",cost="2.0",nav="60",
            triple=True, reason=M.CIBO_REASON, leverage="0.01",
            protected=None):
    return {
        "signal_fingerprint":"sha256:"+"a"*64,
        "trader":"VT31","symbol":"EURUSD",
        "at":"2020-01-01T00:00:00+00:00",
        "cibo_manager_received":True,
        "cibo_manager_action":"ECONOMIC_PROTECTIVE_STOP_PROPOSED",
        "status":"UNFUNDABLE",
        "reason":reason,
        "nav_at_decision_usd":nav,
        "four_engine_caps_usd":{
            "CIBO_COMPOUND":compound,"SIZING":"3.00",
            "PORTFOLIO_COMPOUND_AVAILABLE_SOURCE":"60"
        },
        "stop_loss_usd_per_lot":"186",
        "commission_roundtrip_proxy_per_lot":"14",
        "leverage_margin_budget_usd":"2000",
        "leverage_max_lots":leverage,
        "four_engine_reason_codes":{
            "CIBO_COMPOUND":[
                "RECONCILED_ONLY_NET_QORE_NAV",
                "PROTECTED_AND_FLOAT_LOSS_AND_RESERVATION_DEDUCTED",
                "THREE_SETTLED_LOSSES_HAIR_CUT" if triple
                else "NORMAL_COMPOUND_REINVESTMENT"
            ]
        },
    }


class CompoundP0Audit(unittest.TestCase):
    def test_explains_half_budget_exact_and_affordable_5pct(self):
        d=M.classify(fixture())
        self.assertTrue(d["compound_first_binding"])
        self.assertEqual(d["compound_primary_subcause"],"THREE_SETTLED_LOSSES_HALF_RISK_BUDGET")
        self.assertEqual(D(d["original_risk_5pct_nav_usd"]),D("3.00"))
        self.assertEqual(D(d["compound_authorized_risk_usd"]),D("1.5"))
        self.assertEqual(D(d["min_lot_stop_loss_plus_roundtrip_fee_proxy_usd"]),D("2"))
        self.assertTrue(d["no_haircut_one_trade_price_and_caps_sensitivity"])
        self.assertTrue(all(d["other_proxy_caps_sufficient_for_minlot"].values()))
        self.assertIsNone(d["no_haircut_replay_pnl_usd"])

    def test_no_haircut_does_not_claim_real_financing(self):
        d=M.classify(fixture(compound="3",triple=False,reason=""))
        self.assertFalse(d["compound_first_binding"])
        self.assertEqual(d["compound_primary_subcause"],"NOT_COMPOUND_FIRST_BINDING")
        self.assertTrue(d["compound_budget_equal_full_nav5"])
        self.assertFalse(d["broker_order_checked"])

    def test_effective_cap_mismatch_cannot_be_silently_attributed(self):
        d=M.classify(fixture(compound="1.8",triple=True))
        self.assertEqual(d["compound_primary_subcause"],"OTHER_COMPOUND_BINDING_NEEDS_INVESTIGATION")

    def test_other_margin_rule_still_binds_in_alternative(self):
        d=M.classify(fixture(leverage="0.001"))
        self.assertFalse(d["no_haircut_one_trade_price_and_caps_sensitivity"])
        self.assertFalse(d["other_proxy_caps_sufficient_for_minlot"]["LEVERAGE_MAX_LOTS"])

    def test_incomplete_or_corrupt_evidence_fails_closed(self):
        a=fixture()
        a.pop("four_engine_caps_usd")
        with self.assertRaises(M.CompoundAuditError):
            M.classify(a)
        b=fixture(nav="NaN")
        with self.assertRaises(M.CompoundAuditError):
            M.classify(b)
        c=fixture()
        c["cibo_manager_received"]=False
        with self.assertRaises(M.CompoundAuditError):
            M.classify(c)

    def test_does_not_mutate_original_receipt(self):
        original=fixture()
        import copy
        snap=copy.deepcopy(original)
        M.classify(original)
        self.assertEqual(original,snap)


if __name__=="__main__":
    unittest.main()

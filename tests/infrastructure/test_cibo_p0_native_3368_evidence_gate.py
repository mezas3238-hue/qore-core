"""Seal original Trader opportunity identities; fail closed without historical prices."""
import copy
import json
import unittest
from datetime import datetime,timedelta,timezone
from decimal import Decimal as D
from pathlib import Path

from scripts.cibo_p0_native_3368_evidence_gate import audit,CorpusError

ROOT=Path(__file__).resolve().parents[2]
CONF=json.loads((ROOT/"config/research/cibo_p0_four_arm_atr_5pct_3368_2026-10-09.json").read_text())
T=datetime(2020,1,1,10,tzinfo=timezone.utc)
H="sha256:"+"a"*64


def source(i,tf,symbol,trader):
    return dict(signal_fingerprint="sig-"+str(i),
        trader_id=trader,qore_symbol=symbol,market_decision_at=(T+timedelta(minutes=20)).isoformat(),
        trader_opportunity=dict(side="long",decision_context=[["ctx_timeframe",tf]]))


def signal(i,tf,symbol,with_quotes=True,with_fees=True):
    delta=timedelta(minutes={"M1":1,"M15":15,"H1":60,"H4":240}[tf])
    bars=[dict(symbol=symbol,timeframe=tf,
        opened_at=(T+j*delta).isoformat(),closed_at=(T+(j+1)*delta).isoformat(),
        open="100",high="101",low="99",close="100",content_sha256=H)
        for j in range(20)]
    quotes=[dict(symbol=symbol,observed_at=(T+timedelta(minutes=20)).isoformat(),
        bid="100",ask="100.1",content_sha256=H,
        source_type="BROKER_HISTORICAL_EXECUTABLE_BID_ASK")] if with_quotes else []
    return dict(signal_fingerprint="sig-"+str(i),symbol=symbol,
        source_timeframe=tf,decision_at=(T+timedelta(minutes=20)).isoformat(),
        native_closed_bars=bars,historical_bid_ask=quotes,
        historical_usdjpy_bid_ask=[],
        physical_contract_size="10",
        account_fee_evidence=({"classification":"BROKER_ACCOUNT_HISTORICALLY_VERIFIED",
                               "deal_receipts_sha256":H} if with_fees else {}))


def small():
    return dict(opportunities=[
        source(1,"M1","NDX100","VT31_NAS100"),
        source(2,"M1","GBPJPY","R38_GBPJPY"),
    ])


def pack(rows):
    return dict(schema="qore.cibo.p0.native-broker-evidence-by-signal.v1",
                signals=rows)


class P0RealSourceGate(unittest.TestCase):
    def check(self,manifest,pack_=None):
        return audit(manifest,pack_,CONF,expected_count=2,require_original_seven=False)

    def test_no_pack_produces_two_explicit_causes_no_gains(self):
        r=self.check(small())
        self.assertEqual(r["source_signals"],2)
        self.assertEqual(r["unassessable_count"],2)
        self.assertEqual(r["status_counts"],{
            "NO_CAUSAL_EVIDENCE_PACK_FOR_SIGNAL":2
        })
        self.assertFalse(r["full_replay_ready"])
        self.assertEqual(r["broker_fills"],0)
        self.assertEqual(r["four_arms"],["A-X","A-Y","B-X","B-Y"])

    def test_reject_fingerprint_spoofing_or_duplicates(self):
        m=small()
        m["opportunities"][1]["signal_fingerprint"]="sig-1"
        with self.assertRaisesRegex(CorpusError,"duplicate"):
            self.check(m)
        with self.assertRaisesRegex(CorpusError,"outside sealed"):
            self.check(small(),pack([signal(99,"M1","NDX100")]))

    def test_incomplete_quote_at_broker_epoch_is_unassessable(self):
        first=signal(1,"M1","NDX100",with_quotes=False)
        r=self.check(small(),pack([first]))
        self.assertIn("NO_CAUSAL_HISTORICAL_BID_ASK",r["status_counts"])
        self.assertEqual(r["unassessable_count"],2)

    def test_native_bars_with_future_timeframe_drift_rejected(self):
        first=signal(1,"M1","NDX100")
        first["native_closed_bars"][0]["timeframe"]="M15"
        r=self.check(small(),pack([first]))
        self.assertIn("native bar exact timeframe mismatch",r["status_counts"])

    def test_structural_data_is_not_broker_certification(self):
        first=signal(1,"M1","NDX100")
        r=self.check(small(),pack([first]))
        self.assertEqual(r["status_counts"]["STRUCTURALLY_COMPLETE_BUT_NOT_BROKER_AUTHENTICATED"],1)
        self.assertEqual(r["status_counts"]["NO_CAUSAL_EVIDENCE_PACK_FOR_SIGNAL"],1)
        self.assertFalse(r["full_replay_ready"])
        self.assertFalse(r["opportunities"][0]["causal_market_context"]["source_authentication_verified"])

    def test_jpy_requires_epoch_contemporaneous_usdjpy(self):
        cross=signal(2,"M1","GBPJPY")
        r=self.check(small(),pack([cross]))
        self.assertIn("NO_EPOCH_USDJPY_EVIDENCE",r["status_counts"])
        cross["historical_usdjpy_bid_ask"]=[dict(
            symbol="USDJPY",observed_at=(T+timedelta(minutes=20)).isoformat(),
            bid="150",ask="150.1",content_sha256=H,
            source_type="BROKER_HISTORICAL_EXECUTABLE_BID_ASK")]
        r=self.check(small(),pack([cross]))
        self.assertEqual(r["status_counts"]["STRUCTURALLY_COMPLETE_BUT_NOT_BROKER_AUTHENTICATED"],1)

    def test_published_tariff_without_historical_receipt_is_not_real(self):
        first=signal(1,"M1","NDX100",with_fees=False)
        r=self.check(small(),pack([first]))
        self.assertIn("MISSING_VERIFIABLE_ACCOUNT_FEE_EVIDENCE",r["status_counts"])

    def test_original_epoch_unmodifiable(self):
        first=signal(1,"M1","NDX100")
        first["decision_at"]=(T+timedelta(minutes=25)).isoformat()
        r=self.check(small(),pack([first]))
        self.assertIn("ORIGINAL_TRADER_IDENTITY_OR_EPOCH_DRIFT",r["status_counts"])


if __name__=="__main__":
    unittest.main()

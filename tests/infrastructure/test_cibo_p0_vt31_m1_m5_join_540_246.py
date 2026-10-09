"""P0 VT31 timestamp and PAPER population audit: synthetic, no live trading."""
import unittest
from copy import deepcopy
from datetime import datetime, timedelta, timezone

from scripts.cibo_p0_vt31_m1_m5_join_540_246 import compare

T=datetime(2020,1,2,12,0,0,tzinfo=timezone.utc)
HASH="sha256:"+"a"*64


def source(sid,trader,minute,symbol):
    at=T+timedelta(minutes=minute)
    return {
        "signal_fingerprint":sid,"trader_id":trader,"qore_symbol":symbol,
        "market_decision_at":at.isoformat(),
        "trader_opportunity":{"decision_context":[[
            "ctx_timeframe", "M1" if trader=="VT31_NAS100" else "H1"]]},
    }


def decision(s,opened,entry_minute=None):
    r={"signal_fingerprint":s["signal_fingerprint"],"symbol":s["qore_symbol"],
       "signal_at":s["market_decision_at"],"qdle_at":s["market_decision_at"],
       "qdle_binding_limits":["REQUESTED_USD"],
       "mode":"BANK",
       "status":"PAPER_OPEN" if opened else "QDLE_NO_FINANCEABLE_LOT"}
    if opened:
        r["paper_entry_at"]=(T+timedelta(minutes=entry_minute)).isoformat()
        r["paper_entry_price"]="100.05"
    return r


def fixtures():
    m={"opportunities":[
        source("a","VT31_NAS100",1,"NAS100"),
        source("b","VT31_NAS100",3,"NAS100"),
        source("c","R38_GBPJPY",0,"GBPJPY"),
        source("d","R42_AUDJPY",0,"AUDJPY"),
    ]}
    old={"signal_count":4,"origin_manifest_sha256":HASH,
         "counts":{"paper_open":2,"settled":2},
         "certified":False,"broker_fills":0,
         "signal_decisions":[
            decision(m["opportunities"][0],True,5),
            decision(m["opportunities"][1],False),
            decision(m["opportunities"][2],True,0),
            decision(m["opportunities"][3],False),
         ],
         "closed_trades":[
            {"signal_fingerprint":"a","net_usd":"-0.5"},
            {"signal_fingerprint":"c","net_usd":"1"},
         ]}
    new={"signal_count":4,"origin_manifest_sha256":HASH,
         "counts":{"paper_open":1,"settled":1},
         "certified":False,"broker_fills":0,
         "signal_decisions":[
            decision(m["opportunities"][0],False),
            decision(m["opportunities"][1],True,5),
            decision(m["opportunities"][2],False),
            decision(m["opportunities"][3],False),
         ],
         "closed_trades":[{"signal_fingerprint":"b","net_usd":"-1"}]}
    return m,old,new


def run(m=None,a=None,b=None):
    orig,old,new=fixtures()
    return compare(m if m is not None else orig,
                   a if a is not None else old,
                   b if b is not None else new,
                   expected_signals=4,expected_old=2,
                   expected_new=1,expected_vt31=2)


class TimingSelectionTests(unittest.TestCase):
    def test_two_books_have_same_source_but_294_delta_not_identity_delta(self):
        result=run()
        self.assertEqual(result["opening_intersection"],{
            "source_signals":4,"opened_both":0,
            "opened_only_540":2,"opened_only_246":1,
            "opened_neither":1})
        self.assertEqual(result["by_trader"]["VT31_NAS100"]["revised"]["opened"],1)
        self.assertEqual(result["by_trader"]["R38_GBPJPY"]["revised"]["opened"],0)
        self.assertEqual(result["by_trader"]["VT31_NAS100"]["original"]["net_pnl_usd"],"-0.5")
        self.assertTrue(result["no_live"])

    def test_future_M5_open_is_distinct_from_M1_decision(self):
        r=run()["vt31_delays"]
        self.assertEqual(r["540"]["future_M5_open_quoted_at_earlier_decision_count"],1)
        self.assertEqual(r["246"]["future_M5_open_quoted_at_earlier_decision_count"],1)
        self.assertEqual(r["540"]["measured_delay_seconds"]["max"],"240.0")
        self.assertEqual(r["246"]["measured_delay_seconds"]["max"],"120.0")
        self.assertFalse(r["246"]["m1_broker_price_verified"])
        self.assertEqual(r["246"]["missing_M1_executable_price_count"],2)

    def test_failed_quote_has_no_invented_fill_delay(self):
        r=run()["vt31_delays"]["246"]
        self.assertEqual(r["paper_openings_with_observed_atlas_M5_time"],1)
        self.assertEqual(r["calendar_only_expected_delay_seconds"]["n"],2)

    def test_refuse_double_signal_fingerprint(self):
        m,a,b=fixtures()
        m["opportunities"][1]["signal_fingerprint"]="a"
        with self.assertRaisesRegex(ValueError,"duplicate"):
            run(m,a,b)

    def test_refuse_unknown_source_drift(self):
        m,a,b=fixtures()
        b["signal_decisions"][0]["signal_fingerprint"]="other"
        with self.assertRaisesRegex(ValueError,"different Trader"):
            run(m,a,b)

    def test_refuse_replayed_future_trader_context(self):
        m,a,b=fixtures()
        b["signal_decisions"][1]["qdle_at"]=(T+timedelta(minutes=5)).isoformat()
        with self.assertRaisesRegex(ValueError,"decision time"):
            run(m,a,b)

    def test_refuse_fill_before_decision(self):
        m,a,b=fixtures()
        b["signal_decisions"][1]["paper_entry_at"]=T.isoformat()
        with self.assertRaisesRegex(ValueError,"out of M5 tolerance"):
            run(m,a,b)

    def test_refuse_off_grid_m5_fill(self):
        m,a,b=fixtures()
        b["signal_decisions"][1]["paper_entry_at"]=(T+timedelta(minutes=4)).isoformat()
        with self.assertRaisesRegex(ValueError,"not aligned"):
            run(m,a,b)

    def test_refuse_no_fill_masquerading_as_trade(self):
        m,a,b=fixtures()
        b["signal_decisions"][0]["paper_entry_at"]=(T+timedelta(minutes=5)).isoformat()
        with self.assertRaisesRegex(ValueError,"no-fill"):
            run(m,a,b)

    def test_refuse_fake_live_certification(self):
        m,a,b=fixtures()
        b["certified"]=True
        with self.assertRaisesRegex(ValueError,"authority"):
            run(m,a,b)

    def test_refuse_different_manifest_sha(self):
        m,a,b=fixtures()
        b["origin_manifest_sha256"]="sha256:"+"b"*64
        with self.assertRaisesRegex(ValueError,"different original manifest"):
            run(m,a,b)


if __name__=="__main__":
    unittest.main()

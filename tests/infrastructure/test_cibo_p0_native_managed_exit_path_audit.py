"""Native MAX sparse price path -> true managed shadow exit, never CONTROL R."""
from __future__ import annotations

import copy
import unittest
from datetime import datetime, timedelta, timezone

from qore.infrastructure.cibo_managed_exit_replay import ManagedReplayError
from scripts.cibo_p0_native_managed_exit_path_audit import (
    SCHEMA, ManagedPathEvidenceError, audit_native_managed_paths,
)

START=datetime(2020,1,1,12,tzinfo=timezone.utc)
STAMP=START.isoformat()
H="sha256:"+"a"*64


def bar(idx, bo, bh, bl, bc):
    from decimal import Decimal
    times=(START+timedelta(minutes=idx), START+timedelta(minutes=idx+1))
    bid=list(map(Decimal,(bo,bh,bl,bc)))
    ask=[x+Decimal(".2") for x in bid]
    return dict(opened_at=times[0].isoformat(),closed_at=times[1].isoformat(),
                bid_open=str(bid[0]),bid_high=str(bid[1]),
                bid_low=str(bid[2]),bid_close=str(bid[3]),
                ask_open=str(ask[0]),ask_high=str(ask[1]),
                ask_low=str(ask[2]),ask_close=str(ask[3]),
                evidence_sha256=H)


def fixture():
    raw=[]
    qs=[]
    for sid in ("sig-1","sig-2"):
        raw.append({
            "signal_fingerprint":sid,
            "trader_opportunity":{
                "side":"long","intended_entry":"100.1","stop_loss":"95.1",
                "take_profit":"110.1"},
            "market_decision_at":STAMP
        })
        qs.append({
            "signal_fingerprint":sid,
            "status":"CIBO_NATIVE_COGNITIVE_QDLE_QUOTE_SHADOW",
            "lots":"0.02","symbol":"EURUSD","at":STAMP,
            "stop_loss_usd_per_lot":"5",
            "commission_roundtrip_proxy_per_lot":"1",
            "nav_at_decision_usd":"60",
            "cibo_max_native_economic_budget_requested_usd":"3",
            "cibo_manager_stop_proposed":"95.1",
            "cibo_max_native_proposed_exit_management":{
                "partial_at_r":"1","breakeven_at_r":"1",
                "trailing_activate_at_r":"1.5",
                "trailing_distance_r":"0.75","defensive_close_at_r":"-0.5"},
        })
    m={"opportunities":raw}
    r={"decisions":qs,"native_max_cognitive_economic_intents_applied":2,
       "native_max_control_cashflows_excluded_from_manager_nav":True,
       "real_fundednext_fills":0}
    p={"schema":SCHEMA,"source_type":"SYNTHETIC_TEST_FIXTURE",
       "source_description":"synthetic unit-test bar path; no broker source",
       "items":[{"signal_fingerprint":"sig-1","symbol":"EURUSD",
                 "bars":[bar(0,"99.9","111","94.9","103")]}]}
    return m,r,p


class NativeManagedPricePathAdapterTests(unittest.TestCase):
    def test_complete_path_changes_pnl_without_control_structural_r(self):
        m,r,p=fixture()
        out=audit_native_managed_paths(m,r,p,expected_count=2)
        self.assertEqual(out["signal_count"],2)
        self.assertEqual(out["outcomes"],{
            "SHADOW_SETTLED":1,"MISSING_BID_ASK_PRICE_PATH":1})
        first=out["decisions"][0]
        self.assertEqual(first["exit_reason"],"STOP_FIRST_OR_SL_ONLY")
        self.assertEqual(first["net_usd_research"],"-0.120")
        self.assertEqual(out["shadow_subset_net_usd_research_only"],"-0.120")
        self.assertIsNone(out["global_manager_nav_usd"])
        self.assertEqual(out["real_mt5_fills"],0)
        self.assertTrue(out["missing_bars_are_never_filled_using_trader_structural_r"])

    def test_no_terminal_path_never_invents_settlement(self):
        m,r,p=fixture()
        p["items"][0]["bars"]=[bar(0,"99.9","102","98","100")]
        out=audit_native_managed_paths(m,r,p,expected_count=2)
        self.assertEqual(out["outcomes"]["NEEDS_PRICE_PATH"],1)
        self.assertIsNone(out["decisions"][0]["net_usd_research"])
        self.assertEqual(out["shadow_subset_net_usd_research_only"],"0")

    def test_reject_noncausal_gap_and_symbol_confusion(self):
        m,r,p=fixture()
        p["items"][0]["bars"]=[bar(0,"99.9","101","98","100"),
                                bar(2,"100","102","98","101")]
        with self.assertRaisesRegex(ManagedReplayError, "gaps"):
            audit_native_managed_paths(m,r,p,expected_count=2)
        p["items"][0]["symbol"]="XAUUSD"
        with self.assertRaisesRegex(ManagedPathEvidenceError,"symbol"):
            audit_native_managed_paths(m,r,p,expected_count=2)

    def test_reject_spoofed_reconciled_population(self):
        m,r,p=fixture()
        r["native_max_control_cashflows_excluded_from_manager_nav"]=False
        with self.assertRaisesRegex(ManagedPathEvidenceError,"isolated"):
            audit_native_managed_paths(m,r,p,expected_count=2)
        m,r,p=fixture()
        p["items"].append(dict(p["items"][0]))
        with self.assertRaisesRegex(ManagedPathEvidenceError,"duplicate"):
            audit_native_managed_paths(m,r,p,expected_count=2)


if __name__=="__main__":
    unittest.main()

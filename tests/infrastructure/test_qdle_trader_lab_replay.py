"""Trader Lab integration test: QDLE never turns an unfundable trade into profit."""
from __future__ import annotations

import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from sys import path as pythonpath

pythonpath.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
from qdle_trader_lab_replay import replay

AT = "2026-10-08T12:00:00+00:00"


def event_set(number: int = 1) -> list[dict]:
    events = [
        dict(type="ACCOUNT", at=AT, account_id="replay-1", provider="FundedNext",
             currency="USD", sequence=1, balance="60", equity="60",
             free_margin="100", qore_unreserved_risk_usd="3",
             sovereign_free_source_usd="3", cushion_free_source_usd="0",
             positions=[], covered_fill_tickets=[]),
        dict(type="SYMBOL", at=AT, symbol="EURUSD", aliases=["EURUSD"],
             volume_min="0.01", volume_max="10", volume_step="0.01",
             volume_limit="0", tick_size="0.00001",
             tick_value_loss_usd="1", contract_size="100000",
             currency_profit="USD", fee_usd_per_lot="0",
             fee_provenance="SYNTHETIC_TEST_ONLY", tradable=True),
        dict(type="VALUATION", at=AT, symbol="EURUSD", source_id="SEALED_SYNTHETIC",
             stop_loss_usd_per_lot="100", margin_usd_per_lot="200",
             preflight_pass=True),
    ]
    for i in range(number):
        events.append(dict(type="INTENT", at=AT, request_id=f"trade:{i}",
            trader_id="r38", symbol="EURUSD", side="BUY",
            entry_price="1.10", stop_price="1.095",
            requested_risk_usd="3", sizing_cap_usd="3",
            cibo_compound_cap_usd="3", portfolio_cap_usd="3",
            leverage_cap_lots="1", margin_cap_usd="100",
            source_lane="SOVEREIGN_BANK", slippage_usd_per_lot="0",
            expected_account_sequence=1))
    return events


class TestQDLETraderLab(unittest.TestCase):
    def test_one_intent_financed_not_claimed_executed(self):
        with tempfile.TemporaryDirectory() as d:
            out = replay(event_set(1), Path(d) / "r.sqlite", expected_intents=1)
        self.assertEqual(out["status"], "RESEARCH_PHYSICAL_GATE_PASS")
        self.assertEqual(out["reserved_proposals"], 1)
        self.assertFalse(out["certified"])
        self.assertFalse(out["broker_execution_proven"])
        self.assertEqual(out["intents"][0]["lotage"], "0.03")

    def test_second_intent_fails_without_hidden_capital(self):
        with tempfile.TemporaryDirectory() as d:
            out = replay(event_set(2), Path(d) / "r.sqlite", expected_intents=2)
        self.assertEqual(out["status"], "RESEARCH_FAIL_CLOSED")
        self.assertEqual(out["reserved_proposals"], 1)
        self.assertEqual(out["unfundable_or_invalid"], 1)
        self.assertEqual(out["intents"][1]["lotage"], "0")

    def test_missing_historical_entries_are_not_silently_dropped(self):
        with tempfile.TemporaryDirectory() as d:
            out = replay(event_set(1), Path(d) / "r.sqlite", expected_intents=3368)
        self.assertEqual(out["status"], "RESEARCH_FAIL_CLOSED")
        self.assertIn("EXPECTED_ENTRY_COUNT_MISMATCH",
                      [e["reason"] for e in out["failures"]])


if __name__ == "__main__":
    unittest.main()

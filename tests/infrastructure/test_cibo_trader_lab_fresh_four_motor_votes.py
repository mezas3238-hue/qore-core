"""Independent P0 PAPER economics: account changes must drive new producer votes."""
from __future__ import annotations

import unittest
from datetime import datetime, timedelta, timezone
from decimal import Decimal as D

from qore.infrastructure.cibo_four_motor_policy import (
    FourMotorObservation, FourMotorPolicyError,
)
from qore.infrastructure.cibo_trader_lab_fresh_four_motor_votes import (
    calculate_fresh_paper_four_votes, paper_cashflow,
)

AT = datetime(2026, 10, 9, 14, tzinfo=timezone.utc)


def make(*, balance=D("60"), events=(), positions=None, at=AT, seq=1,
         sid="fresh-1", fraction=D("0.05")):
    if positions is None:
        positions = {}
    return calculate_fresh_paper_four_votes(
        signal_id=sid, trader_id="A1", symbol="EURUSD", side="BUY",
        at=at, sequence=seq, entry_price=D("1.1000"),
        stop_price=D("1.0990"), requested_fraction=fraction,
        current_paper_cash_usd=balance, paper_initial_capital_usd=D("60"),
        paper_broker_balance_usd=D("2000") + balance - D("60"),
        stop_loss_usd_per_lot=D("100"),
        estimated_fee_per_lot=D("7"),
        broker_margin_per_lot=D("3000"),
        symbol_max_lots=D("40"),
        open_positions=positions, paper_cash_events=tuple(events),
    )


class TestFreshFourMotorPaper(unittest.TestCase):
    def test_four_distinct_real_producer_invocations_at_current_nav(self):
        initial = make()
        self.assertEqual(initial.observation.base_entry_budget_usd, D("3"))
        self.assertEqual([v.producer for v in initial.votes], [
            "SIZING", "CIBO_COMPOUND", "ADAPTIVE_LEVERAGE", "PORTFOLIO_COMPOUND"
        ])
        self.assertEqual(initial.intent.requested_risk_usd, D("3"))
        self.assertEqual(initial.intent.cibo_compound_cap_usd, D("3"))
        e = paper_cashflow(event_id="REALIZED_PAPER_1", at=AT - timedelta(seconds=1),
                           delta_usd=D("40"))
        gain = make(balance=D("100"), events=(e,), sid="fresh-2", seq=2)
        self.assertEqual(gain.observation.qore_nav_usd, D("100"))
        self.assertEqual(gain.intent.requested_risk_usd, D("5"))
        self.assertEqual(gain.intent.cibo_compound_cap_usd, D("5"))
        self.assertNotEqual(initial.receipts()[1]["scenario_receipt_sha256"],
                            gain.receipts()[1]["scenario_receipt_sha256"])
        self.assertTrue(all(
            x["research_scenario_only"] and not x["broker_evidence_authenticated"]
            and not x["producer_signature_authenticated"]
            and x["decision_state"] == "RESEARCH_SCENARIO_NON_BROKER"
            and x["realized_event_count"] == 1
            and "realized_event_ids" not in x
            and x["realized_event_ids_sha256"].startswith("sha256:")
            for x in gain.receipts()
        ))

    def test_portfolio_reads_real_open_exposure_but_no_hidden_paper_quota(self):
        active = {
            "older": {
                "opened_at": AT - timedelta(minutes=2), "risk": D("12"),
                "margin": D("70"), "symbol": "EURUSD", "side": "BUY",
                "lots": D("0.02"), "trader": "A1",
            },
        }
        item = make(positions=active)
        self.assertEqual(item.observation.total_open_stop_risk_usd, D("12"))
        self.assertEqual(item.observation.correlated_open_stop_risk_usd, D("12"))
        self.assertEqual(item.observation.trader_open_stop_risk_usd, D("12"))
        self.assertEqual(item.observation.source_available_usd, D("48"))
        self.assertEqual(item.intent.portfolio_cap_usd, D("48"))
        self.assertEqual(item.intent.cibo_compound_cap_usd, D("3"))
        self.assertEqual(item.intent.margin_cap_usd, D("1930"))
        self.assertIn("PAPER_NO_ARBITRARY_GLOBAL_CORRELATED_TRADER_QUOTAS",
                      item.votes[3].reason_codes)

    def test_future_observations_and_stale_cashbook_fail_closed(self):
        e = paper_cashflow(event_id="FUTURE", at=AT + timedelta(seconds=10),
                           delta_usd=D("4"))
        with self.assertRaises((ValueError, FourMotorPolicyError)):
            make(balance=D("64"), events=(e,))
        with self.assertRaises(ValueError):
            make(balance=D("61"))
        with self.assertRaises(ValueError):
            make(fraction=D("0.051"))
        with self.assertRaises(ValueError):
            make(positions={"future": {
                "opened_at": AT + timedelta(seconds=1), "risk": D("1"),
                "margin": D("2"), "symbol": "EURUSD", "side": "BUY",
                "lots": D("0.01"), "trader": "A1",
            }})

    def test_nonbroker_inputs_require_research_flag(self):
        p = make().observation
        from dataclasses import replace
        with self.assertRaises(FourMotorPolicyError):
            replace(p, research_scenario_only=False)
        with self.assertRaises(FourMotorPolicyError):
            replace(p, broker_fees_complete=True)
        # Scenario-only exception does not change strict defaults.


if __name__ == "__main__":
    unittest.main()

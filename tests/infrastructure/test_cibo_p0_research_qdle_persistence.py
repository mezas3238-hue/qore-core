"""P0 research ledger regression: no broker fill, no fictitious 3,368 executions."""
from __future__ import annotations

import tempfile
import unittest
from datetime import UTC, datetime, timedelta
from decimal import Decimal as D
from pathlib import Path

from qore.infrastructure.qore_dynamic_lot_engine import (
    QDLE, QDLEAccount, QDLEError, QDLESymbol, QDLEIntent, BrokerValuation,
)
from qore.infrastructure.cibo_four_motor_policy import FourMotorObservation, FourMotorPolicyError
from qore.infrastructure.cibo_compound_capital import propose_p0_compound_vote
from qore.infrastructure.cibo_core_compound_portfolio import propose_p0_portfolio_vote
from qore.infrastructure.cibo_marginal_leverage_utility import propose_p0_adaptive_leverage_vote

T = datetime(2026, 10, 9, 12, tzinfo=UTC)
H = "sha256:" + "e"*64


class PaperBroker:
    def value(self, spec, intent, now):
        return BrokerValuation(D("100"), D("1000"), now, "RESEARCH_ONLY")
    def check_volume(self, spec, intent, lots):
        if lots < spec.min_lot or lots % spec.lot_step:
            raise QDLEError("illegal grid")


def publish(q, n, at, *, account_id="RESEARCH_TEST"):
    q.publish_account(QDLEAccount(
        account_id, "FundedNext", "USD", n, at,
        D("2000"), D("2000"), D("2000"),
        D("3"), D("3"), D("0"), D("60"),
    ))
    q.publish_symbol(QDLESymbol(
        "EURUSD", ("EURUSD",), D(".01"), D("40"), D(".01"), D("0"),
        D(".00001"), D("1"), D("100000"), "USD", D("14"),
        "RESEARCH_ONLY", at,
    ))


def intent(request, n):
    return QDLEIntent(
        request, "R38", "EURUSD", "BUY", D("1.1"), D("1.09"),
        D("3"), D("3"), D("3"), D("3"), D("40"), D("2000"),
        "SOVEREIGN_BANK", D("0"), n,
    )


def observation(**changes):
    data=dict(
        request_id="paper1",trader_id="R38",symbol="EURUSD",side="BUY",
        source_lane="SOVEREIGN_BANK",observed_at=T,account_sequence=1,
        broker_evidence_sha256=H,initial_qore_nav_usd=D("60"),
        reconciled_cashflows=(),protected_capital_usd=D("0"),
        floating_loss_reserve_usd=D("0"),risk_reservations_usd=D("0"),
        bank_unreserved_usd=D("60"),cushion_unreserved_usd=D("0"),
        total_open_stop_risk_usd=D("0"),correlated_open_stop_risk_usd=D("0"),
        trader_open_stop_risk_usd=D("0"),broker_free_margin_usd=D("2000"),
        broker_margin_reservations_usd=D("0"),
        stop_loss_usd_per_lot=D("100"),roundtrip_fees_usd_per_lot=D("14"),
        execution_buffer_usd_per_lot=D("0"),stress_extra_loss_usd_per_lot=D("0"),
        broker_margin_usd_per_lot=D("1000"),symbol_max_lots=D("40"),
        provider_direction_max_lots=D("40"),
        open_and_reserved_direction_lots=D("0"),broker_quote_at=T,
        research_proxy_only=True,broker_fees_complete=False,
        broker_profit_valuation_complete=False,broker_margin_valuation_complete=False,
    )
    data.update(changes)
    return FourMotorObservation(**data)


class ResearchLedgerP0Test(unittest.TestCase):
    def test_one_database_reserves_once_and_releases_on_paper_terminal(self):
        with tempfile.TemporaryDirectory() as d:
            q=QDLE(Path(d)/"portfolio.sqlite",PaperBroker(),
                   strict_live_fee_evidence=False,strict_four_motor_evidence=False)
            publish(q,1,T)
            first=q.reserve_for_trader(intent("a",1),T)
            self.assertEqual(first.lots,D(".02"))
            second=q.reserve_for_trader(intent("b",1),T)
            self.assertEqual(second.lots,D("0"))
            self.assertEqual(q.health(T)["pending_or_unreconciled_reservations"],1)
            q.finish_research_reservation(
                request_id="a",event_id="paper-close:a",reason="PAPER_CLOSED",
                now=T+timedelta(seconds=1))
            q.finish_research_reservation(
                request_id="a",event_id="paper-close:a",reason="PAPER_CLOSED",
                now=T+timedelta(seconds=1))
            self.assertEqual(q.health(T)["pending_or_unreconciled_reservations"],0)
            with self.assertRaisesRegex(QDLEError,"conflicting"):
                q.finish_research_reservation(
                    request_id="a",event_id="contradiction",reason="PAPER_CLOSED",
                    now=T+timedelta(seconds=1))
            publish(q,2,T+timedelta(seconds=2))
            third=q.reserve_for_trader(intent("c",2),T+timedelta(seconds=2))
            self.assertEqual(third.lots,D(".02"))

    def test_zero_price_or_invalid_geometry_audited_without_fake_lot(self):
        with tempfile.TemporaryDirectory() as d:
            q=QDLE(Path(d)/"paper.sqlite",PaperBroker(),
                   strict_live_fee_evidence=False,strict_four_motor_evidence=False)
            publish(q,1,T)
            r=q.reject_research_unquotable(
                request_id="bad",trader_id="R38",symbol="EURUSD",
                side="BUY",reason="INVALID_GEOMETRY",now=T)
            self.assertEqual(r.lots,D(0))
            self.assertEqual(r.state,"UNQUOTABLE_RESEARCH")
            self.assertEqual(r.binding_limits,("INVALID_GEOMETRY",))
            again=q.reject_research_unquotable(
                request_id="bad",trader_id="R38",symbol="EURUSD",
                side="BUY",reason="INVALID_GEOMETRY",now=T)
            self.assertEqual(r,again)
            self.assertEqual(q.health(T)["pending_or_unreconciled_reservations"],0)
            with self.assertRaisesRegex(QDLEError,"different rejection"):
                q.reject_research_unquotable(
                    request_id="bad",trader_id="R38",symbol="EURUSD",
                    side="BUY",reason="NO_ATLAS_M5_ENTRY",now=T)

    def test_live_qdle_cannot_issue_paper_releases(self):
        with tempfile.TemporaryDirectory() as d:
            q=QDLE(Path(d)/"live.sqlite",PaperBroker())
            publish(q,1,T)
            with self.assertRaisesRegex(QDLEError,"forbidden"):
                q.reject_research_unquotable(
                    request_id="bad",trader_id="R38",symbol="EURUSD",
                    side="BUY",reason="INVALID_GEOMETRY",now=T)
            with self.assertRaisesRegex(QDLEError,"forbidden"):
                q.finish_research_reservation(
                    request_id="x",event_id="fake",reason="PAPER_CLOSED",now=T)

    def test_incomplete_historical_broker_data_never_claims_verified(self):
        o=observation()
        self.assertFalse(o.broker_fees_complete)
        with self.assertRaisesRegex(FourMotorPolicyError,"required"):
            observation(research_proxy_only=False)
        with self.assertRaisesRegex(FourMotorPolicyError,"paper proxy"):
            observation(broker_fees_complete=True)
        self.assertEqual(propose_p0_compound_vote(o).producer,"CIBO_COMPOUND")

    def test_legacy_quotas_disabled_only_in_explicit_paper_arm(self):
        o=observation(total_open_stop_risk_usd=D("8"),
                      correlated_open_stop_risk_usd=D("8"),
                      trader_open_stop_risk_usd=D("8"))
        self.assertEqual(D(propose_p0_portfolio_vote(o).limits["approved_source_funds_usd"]),D("0"))
        research=propose_p0_portfolio_vote(o,research_disable_legacy_quotas=True)
        self.assertEqual(D(research.limits["approved_source_funds_usd"]),D("60"))
        self.assertIn("RESEARCH_LEGACY",research.reason_codes[0])
        baseline=propose_p0_adaptive_leverage_vote(o)
        paper=propose_p0_adaptive_leverage_vote(o,research_use_full_free_margin=True)
        self.assertEqual(D(baseline.limits["approved_margin_usd"]),D("1600"))
        self.assertEqual(D(paper.limits["approved_margin_usd"]),D("2000"))


if __name__=="__main__":
    unittest.main()

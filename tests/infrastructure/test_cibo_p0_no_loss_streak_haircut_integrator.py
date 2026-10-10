"""P0 user directive: no arbitrary three-loss haircut in compound capital."""
from __future__ import annotations

import unittest
from datetime import datetime, timedelta, timezone
from decimal import Decimal as D

from qore.infrastructure.cibo_compound_capital import propose_p0_compound_vote
from qore.infrastructure.cibo_four_motor_policy import FourMotorObservation, ReconciledQoreCashflow

T=datetime(2026,10,9,12,0,tzinfo=timezone.utc)
HASH="sha256:"+"a"*64


def cash(n,amount):
    return ReconciledQoreCashflow(
        event_id="settled-"+str(n),realized_at=T-timedelta(seconds=20-n),
        net_usd=D(str(amount)),source_settlement_sha256=HASH,reconciled=True,
    )


def obs(events=(), **kw):
    base=dict(
        request_id="p0-no-haircut",trader_id="R42_AUDJPY",
        symbol="AUDJPY",side="BUY",source_lane="SOVEREIGN_BANK",
        observed_at=T,account_sequence=1,broker_evidence_sha256=HASH,
        initial_qore_nav_usd=D("60"),reconciled_cashflows=tuple(events),
        protected_capital_usd=D(0),floating_loss_reserve_usd=D(0),
        risk_reservations_usd=D(0),bank_unreserved_usd=D("60"),
        cushion_unreserved_usd=D(0),total_open_stop_risk_usd=D(0),
        correlated_open_stop_risk_usd=D(0),trader_open_stop_risk_usd=D(0),
        broker_free_margin_usd=D("2000"),broker_margin_reservations_usd=D(0),
        stop_loss_usd_per_lot=D("100"),roundtrip_fees_usd_per_lot=D("7"),
        execution_buffer_usd_per_lot=D(0),stress_extra_loss_usd_per_lot=D(0),
        broker_margin_usd_per_lot=D("1000"),symbol_max_lots=D("40"),
        provider_direction_max_lots=D("40"),open_and_reserved_direction_lots=D(0),
        broker_quote_at=T,broker_fees_complete=True,
        broker_profit_valuation_complete=True,
        broker_margin_valuation_complete=True,
    )
    base.update(kw)
    return FourMotorObservation(**base)


class NoHaircutGate(unittest.TestCase):
    def test_three_genuine_settled_losses_reduce_nav_once_not_twice(self):
        o=obs((cash(1,-8),cash(2,-2),cash(3,-10)))
        self.assertEqual(o.qore_nav_usd,D("40"))
        vote=propose_p0_compound_vote(o)
        self.assertEqual(D(vote.limits["approved_risk_usd"]),D("2"))
        self.assertIn("NO_LEGACY_LOSS_STREAK_PENALTY",vote.reason_codes)
        self.assertNotIn("THREE_SETTLED_LOSSES_HAIR_CUT",vote.reason_codes)

    def test_real_protected_capital_still_limits_funds(self):
        o=obs((cash(1,-8),cash(2,-2),cash(3,-10)),
              protected_capital_usd=D("39"))
        v=propose_p0_compound_vote(o)
        self.assertLessEqual(D(v.limits["approved_risk_usd"]),D("1"))

    def test_consecutive_loss_vs_nonconsecutive_same_nav_is_same_budget(self):
        streak=obs((cash(1,-8),cash(2,-2),cash(3,-10)))
        nonstreak=obs((cash(1,-8),cash(2,5),cash(3,-15),cash(4,-2)))
        self.assertEqual(streak.qore_nav_usd,nonstreak.qore_nav_usd)
        self.assertEqual(propose_p0_compound_vote(streak).limits,
                         propose_p0_compound_vote(nonstreak).limits)


if __name__=="__main__":
    unittest.main()

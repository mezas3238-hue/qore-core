"""Native MAX postfill cognitive bar-close redecision: causal next-open only."""
from __future__ import annotations

import sys
import unittest
from datetime import UTC, datetime, timedelta
from decimal import Decimal as D
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/"scripts"))

from qore.infrastructure.cibo_managed_exit_replay import (
    CiboPositionCloseObservation, CiboCognitivePostfillAction,
    ManagedReplayError, replay_cibo_managed_position,
)
from cibo_p0_native_postfill_director import (
    CiboNativeMaxPostfillResearchDirector, ResearchAccountAtClose,
)
from test_cibo_managed_exit_replay import bar, trade
from test_cibo_p0_native_replay_runtime import AT, original

SHA="sha256:"+"b"*64


def native_order(obs, action="EXIT_NEXT_OPEN", **kw):
    return CiboCognitivePostfillAction(
        signal_id=obs.signal_id, decided_at=obs.observed_at,
        action=action,native_episode_digest=SHA,**kw)


class CiboPostfillCognitionTests(unittest.TestCase):
    def test_close_only_decision_executes_at_next_open(self):
        observed=[]
        def decide(obs):
            observed.append(obs)
            return native_order(obs)
        bars=(bar(0,"99.9","101","99","99"),
              bar(1,"98.5","100","96.2","98"))
        result=replay_cibo_managed_position(
            trade(),bars,postfill_decider=decide)
        self.assertEqual(len(observed),1)
        self.assertEqual(observed[0].observed_at,bars[0].closed_at)
        self.assertEqual(result.exit_at,bars[1].opened_at)
        self.assertEqual(result.exit_reason,"DEFENSIVE_CLOSE_NEXT_OPEN")
        self.assertIn("NATIVE_POSTFILL_AT_CLOSE", "|".join(result.actions))
        self.assertFalse(result.certified)
        self.assertEqual(result.mt5_fills_proven,0)

    def test_bad_epoch_and_widening_fail_without_old_policy_fallback(self):
        bars=(bar(0,"99.9","100","99","99.8"),
              bar(1,"99.8","102","99","100"))
        def stale(obs):
            return CiboCognitivePostfillAction(
                signal_id=obs.signal_id,decided_at=obs.observed_at-timedelta(minutes=1),
                action="HOLD",native_episode_digest=SHA)
        with self.assertRaisesRegex(ManagedReplayError,"timestamp-causal"):
            replay_cibo_managed_position(trade(),bars,postfill_decider=stale)
        with self.assertRaisesRegex(ManagedReplayError,"cannot widen"):
            replay_cibo_managed_position(
                trade(),bars,
                postfill_decider=lambda obs:native_order(
                    obs,"TIGHTEN_STOP_NEXT_OPEN",proposed_stop=D("94")),
            )

    def test_genuine_native_max_reconsults_current_close_and_account(self):
        def cash(at):
            return ResearchAccountAtClose(
                observed_at=at,qore_cash_usd=D("60"),peak_cash_usd=D("60"),
                open_stop_risk_usd=D("1"),broker_margin_held_usd=D("100"),
                open_positions=1,broker_cash_usd=D("2000"),
            )
        director=CiboNativeMaxPostfillResearchDirector(
            original=original(),account_at_close=cash,min_lot=D(".01"))
        args=dict(
            signal_id="native-case-1",entry_price=D("3000"),
            protective_stop=D("2990"),remaining_lots=D(".02"),
            original_lots=D(".02"),side="BUY",bar_evidence_sha256=SHA,
        )
        a=director(CiboPositionCloseObservation(
            observed_at=AT+timedelta(minutes=5),
            executable_close=D("2998"),favorable_r=D("-.2"),**args))
        b=director(CiboPositionCloseObservation(
            observed_at=AT+timedelta(minutes=10),
            executable_close=D("3008"),favorable_r=D(".8"),**args))
        self.assertIn(a.action,{"HOLD","EXIT_NEXT_OPEN"})
        self.assertIn(b.action,{"HOLD","TIGHTEN_STOP_NEXT_OPEN","PARTIAL_NEXT_OPEN"})
        self.assertNotEqual(a.native_episode_digest,b.native_episode_digest)
        self.assertEqual(len(director.receipts),2)
        self.assertTrue(all(x["next_open_only"] for x in director.receipts))
        self.assertTrue(all(x["native_faculties_applicable"]>=16
                            for x in director.receipts))

    def test_postfill_account_is_exact_bar_epoch(self):
        director=CiboNativeMaxPostfillResearchDirector(
            original=original(),
            account_at_close=lambda t:ResearchAccountAtClose(
                observed_at=t-timedelta(minutes=1),
                qore_cash_usd=D("60"),peak_cash_usd=D("60"),
                open_stop_risk_usd=D("1"),broker_margin_held_usd=D("100"),
                open_positions=1,broker_cash_usd=D("2000"),
            ),
            min_lot=D(".01"),
        )
        with self.assertRaisesRegex(ManagedReplayError,"match closed-bar"):
            director(CiboPositionCloseObservation(
                signal_id="native-case-1",observed_at=AT+timedelta(minutes=5),
                executable_close=D("3001"),entry_price=D("3000"),
                protective_stop=D("2990"),favorable_r=D(".1"),
                remaining_lots=D(".02"),original_lots=D(".02"),
                side="BUY",bar_evidence_sha256=SHA,
            ))


if __name__=="__main__":
    unittest.main()

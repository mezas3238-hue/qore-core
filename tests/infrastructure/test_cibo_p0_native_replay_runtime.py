"""Native MAX P0 replay smoke tests: genuine CF01-CF19, no archived mode."""
from __future__ import annotations

import sys
import unittest
from datetime import UTC, datetime, timedelta
from decimal import Decimal as D
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parents[2]/"scripts"))
from cibo_p0_native_replay_runtime import (
    NativeReplayReconstructionError, reconstruct_native_max_at_epoch,
)

AT=datetime(2026,10,9,12,tzinfo=UTC)


def original():
    return {
        "market_decision_at":AT.isoformat(),
        "signal_fingerprint":"native-case-1",
        "trader_id":"R34_XAUUSD",
        "qore_symbol":"XAUUSD",
        "trader_opportunity":{
            "provider_symbol":"XAUUSD","side":"long","entry_type":"market",
            "intended_entry":"3000","stop_loss":"2990","take_profit":"3030",
            "stop_loss_per_volume":"100","margin_per_volume":"500",
            "volume_step":"0.01","minimum_volume":"0.01","maximum_volume":"20",
            "decision_context":[[f"ctx_native_{i:02d}",f"evidence-{i:02d}"]
                                for i in range(30)],
        },
        "ce2i_predecision_evidence":{"runtime_receipts":[{
            "engine_name":"select_ce2i_tools_for_regime",
            "input_payload":{"liquidity":"NORMAL","volatility":"NORMAL",
                             "correlation":"NORMAL","provider_condition":"HEALTHY",
                             "risk_utilization":"0","margin_utilization":"0",
                             "drawdown_utilization":"0","opportunity_count":1},
        }]},
    }


def rebuild(**overrides):
    args=dict(
        original=original(),decision_at=AT,qore_cash_usd=D("60"),
        peak_cash_usd=D("60"),open_stop_risk_usd=D("0"),
        broker_margin_held_usd=D("0"),open_positions=0,
        broker_cash_usd=D("2000"),
    )
    args.update(overrides)
    return reconstruct_native_max_at_epoch(**args)


class NativeReplayReconstructionTest(unittest.TestCase):
    def test_real_faculties_and_native_mode_not_historical_json(self):
        instruction,proof=rebuild()
        self.assertTrue(proof["recomputed_native_max"])
        self.assertTrue(proof["cf01_cf19_consultation_id"].startswith("sha256:"))
        self.assertEqual(proof["native_decision_digest"],instruction.decision_digest)
        self.assertEqual(proof["native_decided_at"],AT.isoformat())
        self.assertIn(instruction.mode,("BANK","MEDIUM","ATTACK"))
        self.assertLessEqual(instruction.requested_risk_fraction_of_nav,D(".05"))
        self.assertFalse(instruction.broker_execution_authorized)

    def test_account_change_recomputes_cognitive_semantics(self):
        before,trace_before=rebuild()
        after,trace_after=rebuild(
            qore_cash_usd=D("32"),open_stop_risk_usd=D("10"),
            broker_margin_held_usd=D("1200"),open_positions=2,
        )
        self.assertNotEqual(trace_before["native_semantic_digest"],
                            trace_after["native_semantic_digest"])
        self.assertNotEqual(before.decision_digest,after.decision_digest)
        self.assertGreater(D(trace_after["native_regime_risk_utilization"]),D(0))

    def test_future_perception_fails_closed(self):
        row=original()
        row["market_decision_at"]=(AT+timedelta(minutes=1)).isoformat()
        with self.assertRaisesRegex(NativeReplayReconstructionError,"future"):
            rebuild(original=row)


if __name__=="__main__":
    unittest.main()

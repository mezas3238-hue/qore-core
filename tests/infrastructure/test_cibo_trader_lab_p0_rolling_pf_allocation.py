"""Rolling PF research allocation: no future info, liveness, physical grid."""
from __future__ import annotations

import sys
import unittest
from datetime import datetime, timedelta, timezone
from decimal import Decimal as D
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parents[2] / "scripts"))
from cibo_trader_lab_p0_rolling_pf_allocation_540 import (
    RollingTrader, simulate_mode, _floor_lot,
)

AT = datetime(2026, 10, 9, 15, 0, tzinfo=timezone.utc)


class TestCausalRollingPF(unittest.TestCase):
    def test_neutral_before_minimum_history_and_broker_lot_grid(self):
        model=RollingTrader()
        weight, reason, n, pf = model.decide(mode="ROLLING_PF")
        self.assertEqual((weight,n,pf),(D("1"),0,D("1")))
        self.assertEqual(_floor_lot(D(".015")),D(".01"))
        self.assertEqual(_floor_lot(D(".009")),D("0"))
        for i in range(8):
            model.update(D("-1"),AT + timedelta(seconds=i))
        weight, _, count, _ = model.decide(mode="ROLLING_PF")
        self.assertEqual(count,8)
        self.assertEqual(weight,D("1"))

    def test_pf_shrink_and_history_gate_after_realized_losses(self):
        model=RollingTrader()
        for i in range(12):
            model.update(D("-1"),AT + timedelta(seconds=i))
        weight, _,n,pf=model.decide(mode="ROLLING_PF")
        self.assertEqual(n,12)
        self.assertEqual(pf,D("3") / D("15"))
        self.assertEqual(weight,D(".25"))
        with self.assertRaises(ValueError):
            model.update(D("1"),AT-timedelta(seconds=1))

    def test_cooldown_pauses_then_mandatory_probation(self):
        model=RollingTrader()
        for i in range(10):
            model.update(D("-1"),AT + timedelta(seconds=i))
        outcomes=[model.decide(mode="COOLDOWN") for _ in range(11)]
        self.assertEqual([str(x[0]) for x in outcomes[:10]],["0"]*10)
        self.assertEqual(outcomes[-1][0],D("1"))
        self.assertEqual(outcomes[-1][1],"PAPER_PROBATION")
        # New loss becomes learnable ONLY on settlement; without one no
        # extra automatic permanent pause (probation avoids deadlock).

    def test_only_actually_filled_settlements_enter_rolling_history(self):
        sid="A"
        rows=[{
            "signal_fingerprint":sid,"paper_entry_at":AT.isoformat(),
            "qdle_lots":"0.01","qdle_all_in_risk":"0.40",
            "qdle_margin_usd":"20","paper_open_fee_usd":"0.07",
        }]
        closes={sid:{"net_usd":"-0.30","exit_at":(AT+timedelta(minutes=5)).isoformat()}}
        for mode in ("BASELINE","ROLLING_PF","COOLDOWN","ROLLING_PF_AND_COOLDOWN"):
            result,decisions,settled=simulate_mode(rows,closes,{sid:"T1"},mode)
            self.assertEqual(result["paper_openings"],1)
            self.assertEqual(result["closed"],1)
            self.assertEqual(D(result["net_usd"]),D("-0.30"))
            self.assertEqual(D(result["paper_cash_after_events_usd"]),D("59.70"))
            self.assertEqual(decisions[0]["prior_settled_n"],0)

    def test_concurrent_open_cannot_learn_future_close(self):
        rows=[]
        closes={}
        for i in range(2):
            sid=str(i)
            rows.append({
                "signal_fingerprint":sid,
                "paper_entry_at":(AT+timedelta(minutes=i)).isoformat(),
                "qdle_lots":"0.01","qdle_all_in_risk":"0.30",
                "qdle_margin_usd":"10","paper_open_fee_usd":"0",
            })
            closes[sid]={"net_usd":"-1", "exit_at":(AT+timedelta(minutes=5+i)).isoformat()}
        outcome,decisions,_=simulate_mode(rows,closes,{"0":"T1","1":"T1"},"ROLLING_PF")
        self.assertEqual([d["prior_settled_n"] for d in decisions],[0,0])
        self.assertEqual(outcome["paper_openings"],2)


if __name__=="__main__":
    unittest.main()

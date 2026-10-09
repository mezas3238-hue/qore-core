"""Stop-first conservative, frozen fill, and pre-entry ATR regression tests."""
from __future__ import annotations

import sys
import unittest
from datetime import datetime, timedelta, timezone
from decimal import Decimal as D
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
from cibo_trader_lab_p0_winrate_540_diagnostic import (
    atr14_before, fixed_exit, pre_exit_extremes, post_stop_tp_hindsight,
)


def bar(i, o, h, l, c):
    t = datetime(2026, 10, 9, 12, 0, tzinfo=timezone.utc) + timedelta(minutes=5*i)
    return SimpleNamespace(opened_at=t, closed_at=t+timedelta(minutes=5),
                           open=D(o), high=D(h), low=D(l), close=D(c))


class TestP0WinrateDiagnostics(unittest.TestCase):
    def test_stop_first_and_no_fake_profit_on_same_bar(self):
        path = [bar(0, "100", "110", "90", "100")]
        r = fixed_exit(path, entry=D("100"), stop=D("95"),
                       target=D("105"), side="BUY", spread=D("0"),
                       lots=D("0.01"), per_unit=D("10"), open_fee=D("0.10"))
        self.assertEqual(r["exit_reason"], "STOP")
        self.assertTrue(r["same_bar_sl_tp_ambiguous"])
        self.assertEqual(D(r["net_usd"]), D("-0.60"))
        self.assertEqual(
            post_stop_tp_hindsight(path, r, entry=D("100"),
                                   original_target=D("105"),side="BUY",
                                   spread=D("0"))["status"],
            "AFTER_STOP_24H_PATH_CENSORED")

    def test_pre_exit_excludes_terminal_intrabar(self):
        p = [bar(0,"100","102","99","101"),
             bar(1,"101","120","90","99")]
        e = pre_exit_extremes(
            p, exit_at=p[1].closed_at, entry=D("100"), target=D("110"),
            side="BUY", spread=D("0"))
        self.assertEqual(e["completed_bars"], 1)
        self.assertEqual(D(e["mfe_price_units"]), D("2"))
        self.assertFalse(e["hit_half_original_tp_before_exit_bar"])

    def test_atr_before_excludes_entry_and_current_bar(self):
        p = [bar(i, "100","101","99","100") for i in range(15)]
        p.append(bar(15,"100","200","1","150"))
        self.assertEqual(atr14_before(p,15),D("2"))
        self.assertIsNone(atr14_before(p,14))
        # A known market discontinuity invalidates historical ATR.
        p[14] = SimpleNamespace(opened_at=p[14].opened_at,
             closed_at=p[14].closed_at-timedelta(minutes=1),
             open=D("100"),high=D("101"),low=D("99"),close=D("100"))
        self.assertIsNone(atr14_before(p,15))

    def test_short_side_sl_tp_and_open_gap(self):
        a = [bar(0,"101","107","99","102")]
        r = fixed_exit(a,entry=D("100"),stop=D("105"),target=D("95"),
                       side="SELL",spread=D("0"),lots=D("1"),
                       per_unit=D("1"),open_fee=D("0"))
        self.assertEqual(r["exit_reason"],"STOP")
        self.assertEqual(D(r["net_usd"]),D("-5"))
        b = [bar(0,"107","108","106","107")]
        r = fixed_exit(b,entry=D("100"),stop=D("105"),target=D("95"),
                       side="SELL",spread=D("0"),lots=D("1"),
                       per_unit=D("1"),open_fee=D("0"))
        self.assertEqual(r["exit_reason"],"GAP_STOP")
        self.assertEqual(D(r["net_usd"]),D("-7"))


if __name__ == "__main__":
    unittest.main()

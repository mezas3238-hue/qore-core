"""P0 causal managed exits: broker side, conservative OHLC, risk, chronology."""
from __future__ import annotations

import unittest
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from decimal import Decimal as D

from qore.infrastructure.cibo_managed_exit_replay import (
    CiboManagedTrade, CiboExitPolicy, ExecutableOhlcBar,
    ManagedReplayError, replay_cibo_managed_position,
)

AT = datetime(2020,1,1,12,tzinfo=timezone.utc)
HASH = "sha256:" + "a"*64


def trade(**kw):
    defaults=dict(
        signal_id="signal-1",symbol="EURUSD",side="BUY",entry_at=AT,
        entry_price=D("100.1"),trader_structural_stop_price=D("95.1"),
        economic_stop_price=D("95.1"),trader_take_profit_price=D("110.1"),
        lots=D(".02"), min_lot=D(".01"),lot_step=D(".01"),
        price_pnl_usd_per_lot_per_unit=D("1"),
        roundtrip_commission_usd_per_lot=D("1"),
        maximum_all_in_risk_usd=D("3"),
    )
    defaults.update(kw)
    return CiboManagedTrade(**defaults)


def bar(idx,bo,bh,bl,bc,spread="0.2"):
    o,h,l,c=map(D,(bo,bh,bl,bc))
    s=D(spread)
    return ExecutableOhlcBar(
        AT+timedelta(minutes=idx),AT+timedelta(minutes=idx+1),
        o,h,l,c,o+s,h+s,l+s,c+s,HASH,
    )


class ManagedExit(unittest.TestCase):
    def test_stop_first_when_target_and_stop_same_bar(self):
        b=(bar(0,"99.9","111","94.9","103"),)
        r=replay_cibo_managed_position(trade(),b)
        self.assertEqual(r.status,"SHADOW_SETTLED")
        self.assertEqual(r.exit_reason,"STOP_FIRST_OR_SL_ONLY")
        self.assertEqual(r.gross_pnl_usd_proxy,D("-.1"))
        self.assertEqual(r.commission_usd_proxy,D(".02"))
        self.assertEqual(r.net_pnl_usd_proxy,D("-.12"))
        self.assertFalse(r.certified)
        self.assertEqual(r.mt5_fills_proven,0)

    def test_partial_at_next_open_and_breakeven_stop(self):
        b=(bar(0,"99.9","107","99","106"),
           bar(1,"106","109","99","102"))
        r=replay_cibo_managed_position(trade(),b)
        self.assertEqual(r.status,"SHADOW_SETTLED")
        self.assertEqual(r.partial_count,1)
        self.assertEqual(r.stop_update_count,1)
        self.assertEqual(r.exit_reason,"STOP_FIRST_OR_SL_ONLY")
        self.assertEqual(r.gross_pnl_usd_proxy,D(".059"))
        self.assertEqual(r.commission_usd_proxy,D(".02"))

    def test_defensive_close_on_next_bar_not_same_bar_hindsight(self):
        b=(bar(0,"99.9","100","96","97"),
           bar(1,"97.1","98","96.5","97.3"))
        r=replay_cibo_managed_position(trade(),b)
        self.assertEqual(r.exit_reason,"DEFENSIVE_CLOSE_NEXT_OPEN")
        self.assertEqual(r.defensive_trigger_count,1)
        self.assertEqual(r.exit_at,b[1].opened_at)
        self.assertEqual(r.remaining_lots,D("0"))

    def test_trailing_tightening_next_bar(self):
        b=(bar(0,"99.9","109.2","99","109"),
           bar(1,"109","109.9","104","106"))
        r=replay_cibo_managed_position(trade(),b)
        self.assertEqual(r.status,"SHADOW_SETTLED")
        self.assertEqual(r.stop_update_count,1)
        self.assertIn("APPLY_PROTECTIVE_STOP_NEXT_OPEN", "|".join(r.actions))
        self.assertEqual(r.partial_count,1)
        self.assertEqual(r.exit_reason,"STOP_FIRST_OR_SL_ONLY")

    def test_gap_worse_than_stop_not_guaranteed(self):
        b=(bar(0,"99.9","100","96","99"),
           bar(1,"90","94","89","92"))
        r=replay_cibo_managed_position(trade(),b)
        self.assertEqual(r.exit_reason,"GAP_OPEN_STOP")
        self.assertLess(r.net_pnl_usd_proxy,D("-.12"))

    def test_missing_bars_returns_unknown_no_pnl(self):
        r=replay_cibo_managed_position(trade(),tuple())
        self.assertEqual(r.status,"NEEDS_PRICE_PATH")
        self.assertIsNone(r.net_pnl_usd_proxy)
        self.assertIsNone(r.intratrade_worst_pnl_usd_proxy)

    def test_incomplete_history_no_invented_exit(self):
        r=replay_cibo_managed_position(trade(),(bar(0,"99.9","102","98","100"),))
        self.assertEqual(r.status,"NEEDS_PRICE_PATH")
        self.assertIsNone(r.exit_reason)
        self.assertIsNone(r.net_pnl_usd_proxy)

    def test_market_bar_gap_and_duplicate_strict_fail(self):
        with self.assertRaisesRegex(ManagedReplayError,"gaps or overlaps"):
            replay_cibo_managed_position(trade(),(
                bar(0,"99.9","102","98","100"),
                bar(2,"100","103","98","101")
            ))

    def test_cannot_fake_lot_or_budget_or_stop_widening(self):
        with self.assertRaisesRegex(ManagedReplayError,"nonphysical"):
            trade(lots=D(".015"))
        with self.assertRaisesRegex(ManagedReplayError,"risk at economic"):
            trade(maximum_all_in_risk_usd=D(".01"))
        with self.assertRaisesRegex(ManagedReplayError,"structural risk"):
            trade(economic_stop_price=D("94"))
        with self.assertRaisesRegex(ManagedReplayError,"partial fraction"):
            CiboExitPolicy(partial_fraction=D("1"))

    def test_closed_bar_does_not_trigger_partial_from_intra_high_only(self):
        b=(bar(0,"99.9","108","99","100"),
           bar(1,"100","101","94","98"))
        r=replay_cibo_managed_position(trade(),b)
        self.assertEqual(r.partial_count,0)
        self.assertEqual(r.exit_reason,"STOP_FIRST_OR_SL_ONLY")

    def test_sell_uses_ask_for_risk_and_exec(self):
        t=trade(side="SELL", entry_price=D("99.9"),
                trader_structural_stop_price=D("105"),
                economic_stop_price=D("105"),trader_take_profit_price=D("90"))
        b=(bar(0,"99.9","108","89","101"),)
        r=replay_cibo_managed_position(t,b)
        self.assertEqual(r.exit_reason,"STOP_FIRST_OR_SL_ONLY")
        self.assertLess(r.net_pnl_usd_proxy,D("0"))


if __name__=="__main__":
    unittest.main()

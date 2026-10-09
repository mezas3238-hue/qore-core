"""P0 no-lookahead native ATR14 and historical bid/ask/JPY evidence tests."""
from __future__ import annotations

import unittest
from datetime import datetime,timedelta,timezone
from decimal import Decimal as D
from qore.infrastructure.cibo_p0_native_causal_market import (
    NativeBar,HistoricalBidAsk,CausalEvidenceError,native_wilder_atr14,
    exact_asof_quote,jpy_pip_value_usd_per_lot,native_entry_context,
)

T=datetime(2020,6,1,10,0,tzinfo=timezone.utc)
H="sha256:"+"a"*64


def bars(symbol="NDX100",timeframe="M1",n=20,high=D(101),low=D(99)):
    t=timedelta(minutes={"M1":1,"M15":15,"H1":60,"H4":240}[timeframe])
    return tuple(NativeBar(
        symbol,timeframe,T+i*t,T+(i+1)*t,D(100),high,low,D(100),H)
        for i in range(n))


def quote(symbol="NDX100",when=None,bid=D("100"),ask=D("100.1"),
          source="BROKER_HISTORICAL_EXECUTABLE_BID_ASK"):
    return HistoricalBidAsk(symbol,when or T+timedelta(minutes=20),
                            bid,ask,H,source)


class CausalMarketTests(unittest.TestCase):
    def test_true_wilder_atr14_only_closed_native_m1_bars(self):
        a=bars(n=20)
        atr,sha,at=native_wilder_atr14(
            a,symbol="NDX100",timeframe="M1",
            decision_at=T+timedelta(minutes=20))
        self.assertEqual(atr,D(2))
        self.assertEqual(sha,H)
        self.assertEqual(at,T+timedelta(minutes=20))

    def test_wilder_smoothing_after_seed(self):
        a=bars(n=15)+(bars(n=16,high=D(102),low=D(98))[-1],)
        atr,*_=native_wilder_atr14(
            a,symbol="NDX100",timeframe="M1",
            decision_at=T+timedelta(minutes=16))
        self.assertAlmostEqual(float(atr),float((D(2)*D(13)+D(4))/D(14)),10)

    def test_future_native_bar_cannot_change_prior_atr(self):
        prior=bars(n=16)
        surprise=bars(n=17,high=D(1000),low=D("0.1"))[-1]
        v1=native_wilder_atr14(
            prior,symbol="NDX100",timeframe="M1",
            decision_at=T+timedelta(minutes=16))
        v2=native_wilder_atr14(
            prior+(surprise,),symbol="NDX100",timeframe="M1",
            decision_at=T+timedelta(minutes=16))
        self.assertEqual(v1,v2)

    def test_missing_native_m1_cannot_substitute_M5(self):
        with self.assertRaisesRegex(CausalEvidenceError,"timeframe"):
            native_wilder_atr14(
                bars(timeframe="M15"),symbol="NDX100",timeframe="M1",
                decision_at=T+timedelta(hours=5))
        with self.assertRaisesRegex(CausalEvidenceError,"WARMUP"):
            native_wilder_atr14(
                bars(n=14),symbol="NDX100",timeframe="M1",
                decision_at=T+timedelta(minutes=14))

    def test_gaps_in_final_native_warmup_fail(self):
        series=list(bars(n=20))
        series[9]=NativeBar("NDX100","M1",
            series[9].opened_at+timedelta(minutes=10),
            series[9].closed_at+timedelta(minutes=10),
            D(100),D(101),D(99),D(100),H)
        with self.assertRaisesRegex(CausalEvidenceError,"unordered"):
            native_wilder_atr14(series,symbol="NDX100",timeframe="M1",
                                decision_at=T+timedelta(minutes=20))
        series=list(bars(n=20))
        # Remove one completely closed M1 candle (no synthetic resampling).
        series.pop(13)
        with self.assertRaisesRegex(CausalEvidenceError,"GAPPED"):
            native_wilder_atr14(series,symbol="NDX100",timeframe="M1",
                                decision_at=T+timedelta(minutes=20))

    def test_future_bid_ask_rejected_no_m5_open_lookahead(self):
        with self.assertRaisesRegex(CausalEvidenceError,"NO_CAUSAL"):
            exact_asof_quote([quote(when=T+timedelta(minutes=1))],
                             symbol="NDX100",decision_at=T)
        past=quote(when=T)
        future=quote(when=T+timedelta(minutes=2),bid=D(500),ask=D(500))
        self.assertEqual(exact_asof_quote(
            (past,future),symbol="NDX100",decision_at=T+timedelta(seconds=5)),
            past)

    def test_stale_quote_and_fake_fixed_spread_rejected(self):
        with self.assertRaisesRegex(CausalEvidenceError,"STALE"):
            exact_asof_quote((quote(when=T),),symbol="NDX100",
                             decision_at=T+timedelta(minutes=2))
        with self.assertRaisesRegex(CausalEvidenceError,"not historical"):
            quote(source="M5_PLUS_FIXED_2026_SPREAD")

    def test_historical_usdjpy_asof_and_bid_for_loss_conservative(self):
        cross=quote("USDJPY",when=T,bid=D(150),ask=D("150.05"))
        self.assertEqual(jpy_pip_value_usd_per_lot(
            symbol="GBPJPY",contract_size=D(100000),
            usd_jpy_quote=cross,decision_at=T),D(1000)/D(150))
        with self.assertRaisesRegex(CausalEvidenceError,"NO_CAUSAL"):
            jpy_pip_value_usd_per_lot(
                symbol="AUDJPY",contract_size=D(100000),
                usd_jpy_quote=quote("USDJPY",when=T+timedelta(seconds=1),
                                   bid=D(150),ask=D(151)),decision_at=T)

    def test_native_entry_context_both_sides_causal_and_not_certified(self):
        at=T+timedelta(minutes=20)
        a=bars(n=20)
        q=quote(when=at,bid=D("99.9"),ask=D("100.1"))
        buy=native_entry_context(
            symbol="NDX100",timeframe="M1",side="BUY",decision_at=at,
            bars=a,quotes=(q,),contract_size=D(10))
        sell=native_entry_context(
            symbol="NDX100",timeframe="M1",side="SELL",decision_at=at,
            bars=a,quotes=(q,),contract_size=D(10))
        self.assertEqual(D(buy["predecision_side_entry_price"]),D("100.1"))
        self.assertEqual(D(sell["predecision_side_entry_price"]),D("99.9"))
        self.assertEqual(D(buy["native_wilder_atr14"]),D(2))
        self.assertEqual(buy["source_timeframe"],"M1")
        self.assertFalse(buy["source_authentication_verified"])
        self.assertFalse(buy["account_fee_receipts_verified"])
        self.assertEqual(buy["broker_fills"],0)

    def test_jpy_requires_epoch_quote(self):
        at=T+timedelta(minutes=20)
        a=bars(symbol="GBPJPY",n=20)
        q=quote(symbol="GBPJPY",when=at,bid=D(180),ask=D("180.05"))
        with self.assertRaisesRegex(CausalEvidenceError,"NO_EPOCH_USDJPY"):
            native_entry_context(symbol="GBPJPY",timeframe="M1",side="BUY",
                decision_at=at,bars=a,quotes=(q,),contract_size=D(100000))
        ctx=native_entry_context(
            symbol="GBPJPY",timeframe="M1",side="BUY",decision_at=at,
            bars=a,quotes=(q,),contract_size=D(100000),
            usd_jpy_quote=quote("USDJPY",when=at,bid=D(150),ask=D("150.1")))
        self.assertEqual(D(ctx["stop_loss_usd_per_lot_per_price_unit"]),
                         D(100000)/D(150))


if __name__=="__main__":
    unittest.main()

"""P0 FundedNext simulator unit tests: NEVER claim these are real MT5 specs."""
from dataclasses import dataclass
from decimal import Decimal as D
from types import SimpleNamespace as NS
import threading,unittest
from qore.infrastructure.trader_lab.cibo_fundednext_mt5_lotage_p0 import (
 FundedNextMT5Calculator, AtomicPortfolioReservations, RiskPolicy, FundingError
)


@dataclass
class Asset:
 symbol:str
 contract:float
 point:float
 step:float
 minlot:float
 maxlot:float
 rate:float
 profit_ccy:str="USD"


ASSETS={
 "EURUSD":Asset("EURUSD",100000,0.00001,.01,.01,100,30),
 "GBPUSD":Asset("GBPUSD",100000,0.00001,.01,.01,100,30),
 "AUDJPY":Asset("AUDJPY",100000,0.001,.01,.01,100,30,"JPY"),
 "GBPJPY":Asset("GBPJPY",100000,0.001,.01,.01,100,30,"JPY"),
 "NDX100":Asset("NDX100",10,0.01,.1,.1,100,5),
 "XAUUSD":Asset("XAUUSD",100,.01,.01,.01,100,7.5),
}


class MockMT5:
 ORDER_TYPE_BUY=0;ORDER_TYPE_SELL=1
 def __init__(self,capital=2000):
  self.capital=capital
  self.free=capital
  self.held=0
  self.account_currency="USD"
  self.fx_jpy=158.21
  self.price={
   "EURUSD":(1.09998,1.10),"GBPUSD":(1.24998,1.25),
   "AUDJPY":(98.998,99),"GBPJPY":(198.998,199),
   "NDX100":(19999.95,20000.0),"XAUUSD":(2699.99,2700.0)}
  self.stop_margin_fail=False
  self.bad_profit=False
  self.specs=ASSETS.copy()
 def symbol_info(self,sym):
  c=self.specs.get(sym)
  if c is None:return None
  return NS(volume_min=c.minlot,volume_step=c.step,volume_max=c.maxlot,
   trade_contract_size=c.contract,trade_tick_size=c.point,point=c.point)
 def symbol_info_tick(self,sym):
  if sym not in self.price:return None
  bid,ask=self.price[sym]
  return NS(bid=bid,ask=ask)
 def account_info(self):
  return NS(equity=self.capital,margin_free=self.free,margin=self.held,
    currency=self.account_currency)
 def order_calc_profit(self,kind,sym,volume,start,end):
  if self.bad_profit:return None
  a=self.specs[sym]
  pnl=(end-start)*a.contract*volume*(1 if kind==0 else -1)
  if a.profit_ccy=="JPY":pnl/=self.fx_jpy
  return pnl
 def order_calc_margin(self,kind,sym,volume,entry):
  if self.stop_margin_fail:return None
  a=self.specs[sym]
  nominal=a.contract*volume*entry
  if a.profit_ccy=="JPY":nominal/=self.fx_jpy
  return nominal/a.rate


MAP={"EURUSD":"EURUSD","GBPUSD":"GBPUSD","AUDJPY":"AUDJPY",
 "GBPJPY":"GBPJPY","NAS100":"NDX100","XAUUSD":"XAUUSD"}


class FundedNextP0Tests(unittest.TestCase):
 def setUp(self):
  self.mt5=MockMT5()
  self.c=FundedNextMT5Calculator(self.mt5,MAP)
  self.p=RiskPolicy()
 def ask(self,sym,side,stop,**kw):
  return self.c.quote(trade_id=kw.pop("trade_id","A"),
     trader_id=kw.pop("trader_id","VT31"),core_symbol=sym,
     side=side,stop_price=D(str(stop)),policy=kw.pop("policy",self.p),**kw)

 def test_eurusd_buy_10pip_three_dollar_less_commission(self):
  q=self.ask("EURUSD","BUY",1.0990)
  self.assertEqual(q.lots,D(".02"))
  self.assertLessEqual(q.total_stop_risk_usd,D(3))
  self.assertEqual(q.commission_usd,D(".14"))
  self.assertGreater(q.theoretical_lots,D(".02"))
  self.assertLess(q.theoretical_lots,D(".03"))
 def test_eurusd_buy_30pip_min_lot_too_expensive(self):
  with self.assertRaisesRegex(FundingError,"MIN_LOT_RISK_EXCEEDS"):
   self.ask("EURUSD","BUY",1.0970)
 def test_gbpusd_sell_10pip(self):
  q=self.ask("GBPUSD","SELL",1.25098)
  self.assertEqual(q.lots,D(".02"))
  self.assertEqual(q.entry_price,D("1.24998"))
  self.assertLessEqual(q.total_stop_risk_usd,D(3))
 def test_jpy_conversion_buy_audjpy(self):
  q=self.ask("AUDJPY","BUY",98.97)
  self.assertGreater(q.price_stop_risk_usd,D(0))
  self.assertLessEqual(q.total_stop_risk_usd,D(3))
 def test_jpy_conversion_sell_gbpjpy(self):
  q=self.ask("GBPJPY","SELL",199.04)
  self.assertGreater(q.lots,D(0))
  self.assertLessEqual(q.total_stop_risk_usd,D(3))
 def test_index_nas100_physical_unfundable_10pt_stop(self):
  with self.assertRaisesRegex(FundingError,"MIN_LOT_RISK_EXCEEDS"):
   self.ask("NAS100","BUY",19990)
 def test_index_nas100_no_commission_proper_margin(self):
  self.mt5.capital=10000;self.mt5.free=10000
  q=self.ask("NAS100","BUY",19998.0)
  self.assertEqual(q.commission_usd,D(0))
  self.assertEqual(q.lots,D(".1"))
  self.assertGreater(q.margin_usd,D(0))
 def test_gold_percentage_opening_not_flat_charge(self):
  q=self.ask("XAUUSD","BUY",2699.0)
  self.assertEqual(q.lots,D(".02"))
  self.assertEqual(q.commission_usd,D(".08640000"))
  self.assertLessEqual(q.total_stop_risk_usd,D(3))
 def test_gold_variable_price_affects_commission(self):
  q=self.ask("XAUUSD","BUY",2699.0)
  self.mt5.price["XAUUSD"]=(3099.99,3100.0)
  x=self.ask("XAUUSD","BUY",3099.0,trade_id="B")
  self.assertGreater(x.commission_usd,q.commission_usd)
 def test_cap_295_is_not_forced_to_three(self):
  q=self.ask("EURUSD","BUY",1.0990,policy=RiskPolicy(per_entry_usd=D("2.95")))
  self.assertLessEqual(q.total_stop_risk_usd,D("2.95"))
 def test_slippage_decreases_allowed_lotage(self):
  x=self.ask("EURUSD","BUY",1.0991)
  y=self.ask("EURUSD","BUY",1.0991,policy=RiskPolicy(slippage_points=D("3")),trade_id="B")
  self.assertLessEqual(y.lots,x.lots)
 def test_wrong_side_sl_rejected(self):
  with self.assertRaisesRegex(FundingError,"BUY_STOP"):self.ask("EURUSD","BUY",1.101)
  with self.assertRaisesRegex(FundingError,"SELL_STOP"):self.ask("EURUSD","SELL",1.098)
 def test_min_lot_not_universal(self):
  self.assertEqual(D(str(self.mt5.specs["NDX100"].minlot)),D(".1"))
  self.assertEqual(D(str(self.mt5.specs["EURUSD"].minlot)),D(".01"))
 def test_margin_insufficient(self):
  self.mt5.free=1
  with self.assertRaisesRegex(FundingError,"MIN_LOT_MARGIN"):self.ask("EURUSD","BUY",1.0990)
 def test_missing_mt5_snapshot_hard_failure(self):
  del self.c.symbol_map["NAS100"]
  with self.assertRaisesRegex(FundingError,"MAPPING_UNVERIFIED"):
   self.ask("NAS100","BUY",19998)
 def test_malformed_mt5_margin_hard_failure(self):
  self.mt5.stop_margin_fail=True
  with self.assertRaisesRegex(FundingError,"MT5_PROFIT_OR_MARGIN"):
   self.ask("EURUSD","BUY",1.0990)
 def test_account_wrong_currency_fails_not_implicit_convert(self):
  self.mt5.account_currency="EUR"
  with self.assertRaisesRegex(FundingError,"ACCOUNT_CURRENCY_NOT_USD"):
   self.ask("EURUSD","BUY",1.0990)
 def test_group_risk_cap_and_symbol_risk_cap(self):
  q=self.ask("EURUSD","BUY",1.0990,group_open_risk=D("7.0"))
  self.assertLessEqual(q.total_stop_risk_usd,D("2.0"))
  with self.assertRaisesRegex(FundingError,"RISK_BUDGET_EXHAUSTED"):
   self.ask("EURUSD","BUY",1.0990,symbol_open_risk=D(6),trade_id="C")
 def test_wallet_double_spend_and_retries(self):
  ledger=AtomicPortfolioReservations(self.c,self.p)
  a=ledger.authorize(trade_id="unique-a",trader_id="R38",core_symbol="EURUSD",
      side="BUY",stop_price=D("1.099"),group_id="USD")
  b=ledger.authorize(trade_id="unique-a",trader_id="R38",core_symbol="EURUSD",
      side="BUY",stop_price=D("1.099"),group_id="USD")
  self.assertIs(a,b)
  with self.assertRaisesRegex(FundingError,"DIFFERENT_PAYLOAD"):
   ledger.authorize(trade_id="unique-a",trader_id="R43",core_symbol="EURUSD",
      side="BUY",stop_price=D("1.099"),group_id="USD")
  c=ledger.authorize(trade_id="unique-c",trader_id="R38",core_symbol="EURUSD",
      side="BUY",stop_price=D("1.099"),group_id="USD")
  self.assertGreater(c.margin_free_before_usd-c.margin_free_after_usd,D(0))
  self.assertLessEqual(c.total_open_risk_after_usd,D("9"))
  ledger.release("unique-a")
  with self.assertRaisesRegex(FundingError,"UNKNOWN_OR_ALREADY_RELEASED"):
   ledger.release("unique-a")
  with self.assertRaisesRegex(FundingError,"ALREADY_CLOSED"):
   ledger.authorize(trade_id="unique-a",trader_id="R38",core_symbol="EURUSD",
      side="BUY",stop_price=D("1.099"),group_id="USD")
 def test_concurrent_trade_id_one_reservation(self):
  ledger=AtomicPortfolioReservations(self.c,self.p)
  got=[]; errors=[]
  def run():
   try:got.append(ledger.authorize(trade_id="X",trader_id="T",core_symbol="EURUSD",
      side="BUY",stop_price=D("1.099"),group_id="USD"))
   except Exception as e:errors.append(e)
  threads=[threading.Thread(target=run) for _ in range(10)]
  for t in threads:t.start()
  for t in threads:t.join()
  self.assertFalse(errors)
  self.assertEqual(len(ledger.pending()),1)
  self.assertTrue(all(q is got[0] for q in got))
 def test_dd_floor_enforced(self):
  with self.assertRaisesRegex(FundingError,"MIN_LOT_RISK_EXCEEDS_BUDGET"):
   self.ask("EURUSD","BUY",1.099,policy=RiskPolicy(sovereign_floor_usd=D("1999.99")))
 def test_spread_is_included_via_bid_ask(self):
  a=self.ask("EURUSD","BUY",1.0990)
  self.mt5.price["EURUSD"]=(1.09998,1.1002)
  b=self.ask("EURUSD","BUY",1.0990,trade_id="x")
  self.assertGreater(b.price_stop_risk_usd,a.price_stop_risk_usd)
 def test_no_fabricated_profit_if_server_returns_none(self):
  self.mt5.bad_profit=True
  with self.assertRaisesRegex(FundingError,"MT5_PROFIT_OR_MARGIN"):
   self.ask("EURUSD","BUY",1.099)


if __name__=="__main__":unittest.main()

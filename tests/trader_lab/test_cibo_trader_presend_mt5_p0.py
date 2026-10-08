"""Pre-submit Trader remains signal authority; CIBO controls only volume."""
import unittest
from decimal import Decimal as D
from types import SimpleNamespace as NS
from qore.infrastructure.trader_lab.cibo_fundednext_mt5_lotage_p0 import (
 FundedNextMT5Calculator,RiskPolicy,FundingError
)
from qore.infrastructure.trader_lab.cibo_four_motor_fundednext_p0 import CoordinatedCiboCapital
from qore.infrastructure.trader_lab.cibo_trader_presend_mt5_p0 import (
 TraderSignal,prepare_trader_order,check_broker_execution
)
from test_cibo_fundednext_mt5_lotage_p0 import MockMT5,MAP


class TestTraderPreSend(unittest.TestCase):
 def setUp(self):
  self.mt5=MockMT5()
  self.mt5.TRADE_ACTION_DEAL=1
  self.mt5.TRADE_RETCODE_DONE=10009
  self.cibo=CoordinatedCiboCapital(
      FundedNextMT5Calculator(self.mt5,MAP),RiskPolicy(),realized_bank_usd=D(60))
  self.sig=TraderSignal("VT31-2019-07-01","VT31","EURUSD",
         "BUY",D("1.099"),D("1.102"),"USD","MEDIUM")
 def test_trader_asks_and_receives_lotage_no_order_sent(self):
  p=prepare_trader_order(signal=self.sig,cibo=self.cibo,mt5=self.mt5)
  self.assertFalse(p.broker_sent)
  self.assertFalse(p.broker_filled)
  self.assertEqual(p.broker_order_request["volume"],0.02)
  self.assertEqual(p.broker_order_request["sl"],1.099)
  self.assertEqual(len(self.cibo.ledger.pending()),1)
 def test_server_reject_never_counts_as_open(self):
  p=prepare_trader_order(signal=self.sig,cibo=self.cibo,mt5=self.mt5)
  report=check_broker_execution(presend=p,order_result=NS(retcode=10006,deal=0,volume=0),
         mt5=self.mt5)
  self.assertFalse(report["certified"])
  self.assertEqual(report["status"],"BROKER_ORDER_NOT_FILLED")
  self.cibo.cancel_unfilled(self.sig.decision_id)
  self.assertEqual(len(self.cibo.ledger.pending()),0)
 def test_partial_fill_requires_repricing(self):
  p=prepare_trader_order(signal=self.sig,cibo=self.cibo,mt5=self.mt5)
  report=check_broker_execution(presend=p,order_result=NS(
       retcode=10009,deal=123,volume=.01,price=1.1),mt5=self.mt5)
  self.assertFalse(report["certified"])
  self.assertEqual(report["status"],"BROKER_VOLUME_MISMATCH_REQUIRES_REPRICING")
 def test_price_slippage_requires_new_stop_risk_calculation(self):
  p=prepare_trader_order(signal=self.sig,cibo=self.cibo,mt5=self.mt5)
  report=check_broker_execution(presend=p,order_result=NS(
       retcode=10009,deal=123,volume=.02,price=1.1001),mt5=self.mt5)
  self.assertFalse(report["certified"])
  self.assertEqual(report["status"],"BROKER_FILL_PRICE_DIFFERS_RISK_RECALC_REQUIRED")
 def test_exact_broker_ack_vol_and_price(self):
  p=prepare_trader_order(signal=self.sig,cibo=self.cibo,mt5=self.mt5)
  report=check_broker_execution(presend=p,order_result=NS(
      retcode=10009,deal=123,volume=.02,price=1.1),mt5=self.mt5)
  self.assertTrue(report["certified"])
 def test_inverted_take_profit_cannot_leave_reservation(self):
  bad=TraderSignal(self.sig.decision_id,self.sig.trader_id,
     self.sig.core_symbol,"BUY",D("1.099"),D("1.05"),"USD","MEDIUM")
  with self.assertRaisesRegex(FundingError,"TRADER_TP_DIRECTION"):
   prepare_trader_order(signal=bad,cibo=self.cibo,mt5=self.mt5)
  self.assertEqual(len(self.cibo.ledger.pending()),0)


if __name__=="__main__":unittest.main()

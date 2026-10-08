"""Four CIBO economic engine integration against one MT5 source and ledger."""
from decimal import Decimal as D
import unittest
from qore.infrastructure.trader_lab.cibo_four_motor_fundednext_p0 import CoordinatedCiboCapital
from qore.infrastructure.trader_lab.cibo_fundednext_mt5_lotage_p0 import (
 FundedNextMT5Calculator,RiskPolicy,FundingError,
)
from test_cibo_fundednext_mt5_lotage_p0 import MockMT5,MAP


class P0FourMotorTests(unittest.TestCase):
 def setUp(self):
  self.m=MockMT5(capital=2000)
  self.c=CoordinatedCiboCapital(
   FundedNextMT5Calculator(self.m,MAP),
   RiskPolicy(per_entry_usd=D("3"),
     max_portfolio_open_stop_usd=D("9"),
     max_symbol_open_stop_usd=D("6"),
     max_trader_open_stop_usd=D("6"),
     max_group_open_stop_usd=D("9")),
   realized_bank_usd=D(60),realized_cushion_usd=D(0))
 def allow(self,trade_id,mode="MEDIUM",**kwargs):
  args=dict(trade_id=trade_id,trader_id="R38",core_symbol="EURUSD",
   side="BUY",stop_price=D("1.099"),group_id="USD",mode=mode)
  args.update(kwargs)
  return self.c.authorize(**args)
 def test_all_four_components_separate_receipts(self):
  a=self.allow("one")
  self.assertEqual([v.motor for v in a.decisions],
   ["SIZING","CIBO_COMPOUND","COMPOUND_PORTFOLIO","ADAPTIVE_LEVERAGE"])
  self.assertEqual(a.quote.lots,D(".02"))
  self.assertFalse(a.broker_order_sent)
  self.assertFalse(a.can_submit_to_broker) # no authenticated portfolio rehydration
 def test_attack_cannot_use_sovereign_bank(self):
  with self.assertRaisesRegex(FundingError,"COMPOUND_SOURCE"):
   self.allow("one",mode="ATTACK")
  self.assertEqual(len(self.c.ledger.pending()),0)
 def test_medium_only_consumes_its_own_lane(self):
  a=self.allow("m")
  w=self.c.wallet()
  self.assertLess(w["BANK_AVAILABLE"],D(60))
  self.assertEqual(w["CUSHION_AVAILABLE"],D(0))
  self.assertEqual(w["BANK_RESERVED"],a.quote.total_stop_risk_usd)
 def test_duplicate_authorization_same_output_no_double_reserve(self):
  x=self.allow("z");y=self.allow("z")
  self.assertIs(x,y)
  self.assertEqual(len(self.c.ledger.pending()),1)
 def test_duplicate_conflicting_request_rejected(self):
  self.allow("z")
  with self.assertRaisesRegex(FundingError,"DUPLICATE"):
   self.allow("z",trader_id="R43")
 def test_cancel_unfilled_no_fake_execution(self):
  self.allow("x")
  self.c.cancel_unfilled("x")
  self.assertEqual(len(self.c.ledger.pending()),0)
  with self.assertRaisesRegex(FundingError,"SETTLED_TRADE_ID"):
   self.allow("x")
 def test_realized_profit_recycled_only_after_broker_proof(self):
  self.allow("x")
  with self.assertRaisesRegex(FundingError,"BROKER_CLOSE_RECEIPT_MISSING"):
   self.c.close_after_broker_receipt("x",realized_net_usd=D(12),
       broker_execution_proven=False)
  self.assertEqual(self.c.wallet()["BANK_REALIZED"],D(60))
  self.c.close_after_broker_receipt("x",realized_net_usd=D(12),
       broker_execution_proven=True)
  self.assertEqual(self.c.wallet()["BANK_REALIZED"],D(72))
  self.assertEqual(self.c.wallet()["BANK_RESERVED"],D(0))
 def test_realized_loss_declined_before_state_mutation(self):
  self.allow("x")
  with self.assertRaisesRegex(FundingError,"REALIZED_LOSS_VIOLATES"):
   self.c.close_after_broker_receipt("x",realized_net_usd=D(-70),
       broker_execution_proven=True)
  self.assertEqual(self.c.wallet()["BANK_REALIZED"],D(60))
  self.assertEqual(len(self.c.ledger.pending()),1)
 def test_attack_has_only_realized_profit_not_floating(self):
  self.c.cushion=D(10)
  a=self.allow("a",mode="ATTACK")
  self.assertTrue(a.quote.total_stop_risk_usd<=D(3))
  self.assertLess(self.c.wallet()["CUSHION_AVAILABLE"],D(10))
 def test_cibo_four_motors_share_dynamic_five_percent_after_realized_gain(self):
  self.c=CoordinatedCiboCapital(
   FundedNextMT5Calculator(self.m,MAP),RiskPolicy(),
   realized_bank_usd=D(2000),realized_cushion_usd=D(0))
  first=self.allow("baseline")
  self.assertEqual(first.quote.dynamic_risk_target_usd,D(100))
  self.assertEqual(first.decisions[0].authorized_usd,D(100))
  self.c.close_after_broker_receipt("baseline",realized_net_usd=D(1000),
      broker_execution_proven=True)
  self.m.capital=3000
  self.m.balance=3000
  self.m.free=3000
  second=self.allow("after-gain")
  self.assertEqual(second.quote.dynamic_risk_target_usd,D(150))
  self.assertEqual(second.decisions[0].authorized_usd,D(150))
  self.assertGreater(second.quote.lots,first.quote.lots)
 def test_cibo_four_motors_risk_shrinks_after_realized_loss(self):
  self.c=CoordinatedCiboCapital(
   FundedNextMT5Calculator(self.m,MAP),RiskPolicy(),
   realized_bank_usd=D(2000),realized_cushion_usd=D(0))
  first=self.allow("before-loss")
  self.c.close_after_broker_receipt("before-loss",realized_net_usd=D(-1000),
      broker_execution_proven=True)
  self.m.capital=1000
  self.m.balance=1000
  self.m.free=1000
  second=self.allow("after-loss")
  self.assertEqual(second.quote.dynamic_risk_target_usd,D(50))
  self.assertLess(second.quote.lots,first.quote.lots)
 def test_wallet_bank_floor_prevents_spend(self):
  calculator=FundedNextMT5Calculator(self.m,MAP)
  c=CoordinatedCiboCapital(calculator,RiskPolicy(sovereign_floor_usd=D(59.5)),
   realized_bank_usd=D(60))
  with self.assertRaisesRegex(FundingError,"MIN_LOT_RISK_EXCEEDS"):
   c.authorize(trade_id="x",trader_id="R38",core_symbol="EURUSD",
    side="BUY",stop_price=D("1.099"),group_id="USD",mode="MEDIUM")

if __name__=="__main__":unittest.main()

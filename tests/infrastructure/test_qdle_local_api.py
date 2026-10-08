"""QDLE authenticated loopback API authority separation and refusal tests."""
import json
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from datetime import datetime, timezone
from decimal import Decimal as D
from http.server import ThreadingHTTPServer
from pathlib import Path

from qore.infrastructure.qdle_local_api import build_local_handler
from qore.infrastructure.qore_dynamic_lot_engine import BrokerValuation, QDLE, QDLEError


class Broker:
    def value(self, spec, intent, now):
        return BrokerValuation(D("100"), D("200"), now, "TEST_ONLY")
    def check_volume(self, spec, intent, lots):
        pass


class TestQDLELocalAPI(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.engine = QDLE(Path(self.directory.name) / "qdle.db", Broker(),
                           enforce_finance_approval=True,
                           strict_live_fee_evidence=False)
        self.trader = "trader-token-supersecret-123456"
        self.treasury = "treasury-token-supersecret-123456"
        self.provider = "provider-token-supersecret-123456"
        handler = build_local_handler(
            self.engine, trader_token=self.trader,
            treasury_token=self.treasury, provider_token=self.provider)
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.url = f"http://127.0.0.1:{self.server.server_address[1]}"
        self.now = datetime.now(timezone.utc).isoformat()

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=3)
        self.directory.cleanup()

    def request(self, method, path, token, data=None):
        payload = None if data is None else json.dumps(data).encode()
        req = urllib.request.Request(
            self.url + path, data=payload, method=method,
            headers={"X-QDLE-Token":token, "Content-Type":"application/json"})
        try:
            with urllib.request.urlopen(req, timeout=3) as resp:
                return resp.status, json.loads(resp.read())
        except urllib.error.HTTPError as exc:
            return exc.code, json.loads(exc.read())

    def test_separate_authority_and_nonexecuting_reserve(self):
        self.assertEqual(self.request("GET", "/health", "")[0], 403)
        status, health = self.request("GET", "/health", self.trader)
        self.assertEqual(status, 200)
        self.assertFalse(health["ready"])
        acc = dict(account_id="123", provider="FundedNext", currency="USD",
                   sequence=1, as_of=self.now, balance="2000", equity="2000",
                   free_margin="1900", qore_trading_capital_usd="60", qore_unreserved_risk_usd="3",
                   sovereign_free_source_usd="3", cushion_free_source_usd="0",
                   positions=[], covered_fill_tickets=[])
        self.assertEqual(self.request("POST", "/v1/account-event", self.trader, acc)[0], 403)
        self.assertEqual(self.request("POST", "/v1/account-event", self.treasury, acc)[0], 200)
        spec = dict(broker_symbol="EURUSD", aliases=["EURUSD"],
                    min_lot="0.01", max_lot="10", lot_step="0.01",
                    directional_volume_limit="0", tick_size="0.00001",
                    tick_value_loss_usd="1", contract_size="100000",
                    currency_profit="USD", fee_usd_per_lot="0",
                    fee_provenance="TEST_ONLY", as_of=self.now, tradable=True)
        self.assertEqual(self.request("POST", "/v1/symbol-event", self.treasury, spec)[0], 403)
        self.assertEqual(self.request("POST", "/v1/symbol-event", self.provider, spec)[0], 200)
        intent = dict(request_id="api-1", trader_id="r38", symbol="EURUSD", side="BUY",
                      entry_price="1.1", stop_price="1.09",
                      requested_risk_usd="3", sizing_cap_usd="3",
                      cibo_compound_cap_usd="3", portfolio_cap_usd="3",
                      leverage_cap_lots="1", margin_cap_usd="50",
                      source_lane="SOVEREIGN_BANK", slippage_usd_per_lot="0",
                      expected_account_sequence=1)
        self.assertEqual(self.request("POST", "/v1/reserve", self.provider, intent)[0], 403)
        self.assertEqual(self.request("POST", "/v1/finance-approval", self.trader,
                                      dict(intent, approved_at=self.now))[0], 403)
        self.assertEqual(self.request("POST", "/v1/reserve", self.trader, intent)[0], 409)
        self.assertEqual(self.request("POST", "/v1/finance-approval", self.treasury,
                                      dict(intent, approved_at=self.now))[0], 200)
        self.assertEqual(self.request("POST", "/v1/reserve", self.trader,
                                      dict(intent, requested_risk_usd="30"))[0], 409)
        code, result = self.request("POST", "/v1/reserve", self.trader, intent)
        self.assertEqual(code, 200)
        self.assertEqual(result["state"], "RESERVED_FOR_TRADER")
        self.assertEqual(result["lots"], "0.03")
        self.assertEqual(result["total_risk_usd"], "3.00")
        self.assertFalse(self.engine.ledger(limit=1)[0]["event"] == "BROKER_FILL_UNRECONCILED")
        presend = dict(request_id="api-1", provider_symbol="EURUSD",
                       side="BUY", lots="0.03", executable_entry="1.1",
                       stop_price="1.09", at=self.now)
        self.assertEqual(self.request("POST", "/v1/pre-send-check",
                                      self.trader, presend)[0], 403)
        self.assertEqual(self.request("POST", "/v1/pre-send-check",
                                      self.provider, presend)[0], 200)
        self.assertEqual(self.request("POST", "/v1/pre-send-check",
                                      self.provider, presend)[0], 409)
        self.assertEqual(self.engine.health()["pending_or_unreconciled_reservations"], 1)


    def test_high_entropy_tokens_required(self):
        with self.assertRaises(QDLEError):
            build_local_handler(self.engine, trader_token="abc",
                                treasury_token="abc", provider_token="abc")


if __name__ == "__main__":
    unittest.main()

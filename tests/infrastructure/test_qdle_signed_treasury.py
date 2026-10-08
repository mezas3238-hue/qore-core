"""Signed treasury source isolation and provider-loss-floor regressions."""
import hashlib
import hmac
import json
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from decimal import Decimal as D
from pathlib import Path
from sys import path as py_path
from types import SimpleNamespace
from unittest.mock import patch

py_path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
from qdle_qore_account_event_publisher import forward_account
from qore.infrastructure.qdle_signed_treasury import verify_treasury_hmac_event
from qore.infrastructure.qore_dynamic_lot_engine import QDLEError

T = datetime(2026, 10, 8, 12, tzinfo=timezone.utc)
KEY = b"treasury-secret-unique-at-least-32-bytes!!"


def signed(risk="3", floor="56.4", source="15", now=T):
    payload = dict(account_id="123", sequence=1, observed_at=now.isoformat(),
                   qore_unreserved_risk_usd=risk,
                   sovereign_free_source_usd=source,
                   cushion_free_source_usd="10",
                   active_provider_mll_floor_usd=floor,
                   covered_fill_tickets=[], ledger_receipt="qore-ledger-proof-1")
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"),
                         ensure_ascii=True).encode()
    return dict(payload=payload, hmac_sha256=hmac.new(KEY, encoded, hashlib.sha256).hexdigest())


class MT5:
    def account_info(self):
        return SimpleNamespace(login=123, currency="USD", balance=60,
                               equity=60, margin_free=50)
    def positions_get(self):
        return ()
    def orders_get(self):
        return ()


class Response:
    status = 200
    def __enter__(self):
        return self
    def __exit__(self, *args):
        return False


class TestTreasury(unittest.TestCase):
    def test_verified_event_and_fundednext_provider_equity_loss_headroom(self):
        verified = verify_treasury_hmac_event(
            signed(), KEY, now=T, expected_account_id="123")
        self.assertEqual(verified.active_provider_mll_floor_usd, D("56.4"))
        with patch("qdle_qore_account_event_publisher.urllib.request.urlopen",
                   return_value=Response()) as send:
            seq = forward_account(MT5(), signed_event=signed(),
                    hmac_key=KEY, account_id="123",
                    token="treasury-token-placeholder", base_url="http://127.0.0.1:9999",
                    now=T)
            self.assertEqual(seq, 1)
            self.assertEqual(send.call_count, 1)

    def test_tampered_negative_or_expired_cash_source_is_rejected(self):
        payload = signed()
        payload["payload"]["sovereign_free_source_usd"] = "999"
        with self.assertRaises(QDLEError):
            verify_treasury_hmac_event(payload, KEY, now=T, expected_account_id="123")
        with self.assertRaises(QDLEError):
            verify_treasury_hmac_event(signed(source="-1"), KEY,
                                        now=T, expected_account_id="123")
        with self.assertRaises(QDLEError):
            verify_treasury_hmac_event(signed(now=T-timedelta(seconds=20)), KEY,
                                        now=T, expected_account_id="123")

    def test_qore_risk_cannot_exceed_signed_prop_floor_headroom(self):
        with self.assertRaises(QDLEError):
            forward_account(MT5(), signed_event=signed(risk="4"),
                hmac_key=KEY, account_id="123", token="t",
                base_url="http://127.0.0.1:9999", now=T)

    def test_cash_cannot_claim_more_than_broker_equity(self):
        with self.assertRaises(QDLEError):
            forward_account(MT5(), signed_event=signed(source="100"),
                hmac_key=KEY, account_id="123", token="t",
                base_url="http://127.0.0.1:9999", now=T)


if __name__ == "__main__":
    unittest.main()

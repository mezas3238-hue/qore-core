"""Independent economic receipt gate; authenticity still belongs to treasury."""
from __future__ import annotations

import hashlib
import hmac
import json
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from decimal import Decimal as D
from pathlib import Path

from qore.infrastructure.qore_dynamic_lot_engine import (
    QDLE, QDLEAccount, QDLESymbol, QDLEIntent, BrokerValuation, QDLEError
)

T = datetime(2026, 10, 8, 12, tzinfo=timezone.utc)
KEYS = {name: (name + "-never-live-test-only-crypto-key").encode().ljust(64, b"x")
        for name in ("SIZING", "CIBO_COMPOUND", "ADAPTIVE_LEVERAGE", "PORTFOLIO_COMPOUND")}


class FakeBroker:
    def value(self, spec, intent, now):
        return BrokerValuation(D("100"), D("100"), now, "SYNTHETIC_ONLY")
    def check_volume(self, spec, intent, lots):
        pass


def signal():
    return QDLEIntent(
        "four-receipts", "r38", "EURUSD", "BUY", D("1.1000"), D("1.0900"),
        D("3"), D("3"), D("3"), D("60"), D("40"), D("1900"),
        "SOVEREIGN_BANK", D("0"), 1,
    )


def receipts():
    caps = {
        "SIZING": {"approved_risk_usd": "3"},
        "CIBO_COMPOUND": {"approved_risk_usd": "3"},
        "ADAPTIVE_LEVERAGE": {
            "approved_max_lots": "40", "approved_margin_usd": "1900"},
        "PORTFOLIO_COMPOUND": {"approved_source_funds_usd": "60"},
    }
    signed = {}
    for name, fields in caps.items():
        payload = dict(producer=name, request_id="four-receipts", account_sequence=1,
                       observed_at=T.isoformat(), **fields)
        canonical = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
        signed[name] = dict(
            payload, source_event_sha256="sha256:" + hashlib.sha256(canonical).hexdigest(),
            hmac_sha256=hmac.new(KEYS[name], canonical, hashlib.sha256).hexdigest())
    return signed


class TestFourMotorEvidence(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.q = QDLE(Path(self.folder.name) / "motor.sqlite",
                      FakeBroker(), enforce_finance_approval=True,
                      motor_hmac_keys=KEYS)
        self.q.publish_account(QDLEAccount(
            "123", "FundedNext", "USD", 1, T, D("2000"), D("2000"),
            D("1900"), D("60"), D("60"), D("0"), D("60")))
        self.q.publish_symbol(QDLESymbol(
            "EURUSD", ("EURUSD",), D(".01"), D("40"), D(".01"),
            D("0"), D(".00001"), D("1"), D("100000"), "USD",
            D("0"), "SYNTHETIC_ONLY", T))

    def tearDown(self):
        self.folder.cleanup()

    def test_missing_economic_decisions_block_live_authority(self):
        with self.assertRaisesRegex(QDLEError, "four-motor"):
            self.q.publish_finance_approval(signal(), T)
        with self.assertRaisesRegex(QDLEError, "four-motor"):
            self.q.publish_finance_approval(signal(), T, {"SIZING": receipts()["SIZING"]})

    def test_distinct_timed_proofs_bound_to_same_budget_allow_reservation(self):
        four = receipts()
        self.q.publish_finance_approval(signal(), T, four)
        funded = self.q.reserve_for_trader(signal(), T)
        self.assertEqual(funded.lots, D(".03"))
        self.assertEqual(funded.total_risk_usd, D("3"))
        with self.assertRaisesRegex(QDLEError, "cannot alter"):
            altered = receipts()
            altered["SIZING"]["source_event_sha256"] = "sha256:" + "a"*64
            self.q.publish_finance_approval(signal(), T, altered)

    def test_tampered_signature_and_missing_real_keys_block(self):
        tampered = receipts()
        tampered["SIZING"]["hmac_sha256"] = "0" * 64
        with self.assertRaisesRegex(QDLEError, "signature invalid"):
            self.q.publish_finance_approval(signal(), T, tampered)
        with tempfile.TemporaryDirectory() as d:
            missing = QDLE(Path(d) / "missing.sqlite", FakeBroker(),
                           enforce_finance_approval=True)
            missing.publish_account(QDLEAccount(
                "123", "FundedNext", "USD", 1, T, D("2000"), D("2000"),
                D("1900"), D("60"), D("60"), D("0"), D("60")))
            with self.assertRaisesRegex(QDLEError, "signing keys required"):
                missing.publish_finance_approval(signal(), T, receipts())

    def test_reused_proof_wrong_economics_and_stale_decision_fail(self):
        same = receipts()
        same["CIBO_COMPOUND"]["source_event_sha256"] = same["SIZING"]["source_event_sha256"]
        with self.assertRaisesRegex(QDLEError, "hash not bound"):
            self.q.publish_finance_approval(signal(), T, same)
        wrong = receipts()
        wrong["SIZING"]["approved_risk_usd"] = "100"
        with self.assertRaisesRegex(QDLEError, "hash not bound"):
            self.q.publish_finance_approval(signal(), T, wrong)
        stale = receipts()
        stale["PORTFOLIO_COMPOUND"]["observed_at"] = (T-timedelta(minutes=1)).isoformat()
        with self.assertRaisesRegex(QDLEError, "hash not bound"):
            self.q.publish_finance_approval(signal(), T, stale)


if __name__ == "__main__":
    unittest.main()

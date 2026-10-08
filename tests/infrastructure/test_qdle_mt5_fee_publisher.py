"""Synthetic contract tests: fees MUST cover both legs before QDLE metadata."""
from __future__ import annotations

import unittest
from decimal import Decimal as D
from types import SimpleNamespace

from qore.infrastructure.qdle_mt5_read_only import read_mt5_symbols
from qore.infrastructure.qore_dynamic_lot_engine import QDLEError
from scripts.qdle_mt5_metadata_publisher import verified_roundtrip_fee_for_symbol


class FakeReadOnlyMt5:
    SYMBOL_TRADE_MODE_FULL = 4

    def __init__(self):
        self.names = []

    def symbol_info(self, name):
        self.names.append(name)
        return SimpleNamespace(
            volume_min=.01, volume_max=40, volume_step=.01, volume_limit=0,
            trade_tick_size=.00001, trade_tick_value_loss=1,
            trade_contract_size=100000, currency_profit="USD",
            visible=True, trade_mode=self.SYMBOL_TRADE_MODE_FULL,
        )


class TestPublisherVerifiedRoundTrip(unittest.TestCase):
    @staticmethod
    def verified():
        # Synthetic evidence name only; actual broker provenance must be supplied
        # from the account outside these tests.
        return {
            "EURUSD": {
                "usd_per_lot": "12.50",
                "evidence": "SYNTHETIC_BOTH_LEGS_TEST_RECEIPT",
                "covers_open_and_close": True,
            }
        }

    def test_explicit_roundtrip_reaches_symbol_contract(self):
        mt5 = FakeReadOnlyMt5()
        result = read_mt5_symbols(
            mt5, {"EURUSD": "EURUSD"},
            lambda name, info: verified_roundtrip_fee_for_symbol(
                self.verified(), name),
        )
        self.assertEqual(mt5.names, ["EURUSD"])
        self.assertEqual(result[0].fee_usd_per_lot, D("12.50"))
        self.assertEqual(
            result[0].fee_provenance,
            "BROKER_ROUND_TRIP_VERIFIED:SYNTHETIC_BOTH_LEGS_TEST_RECEIPT",
        )

    def test_missing_field_fail_closed_not_legacy_default_false(self):
        rate = self.verified()
        del rate["EURUSD"]["covers_open_and_close"]
        with self.assertRaisesRegex(QDLEError, "open AND close"):
            verified_roundtrip_fee_for_symbol(rate, "EURUSD")

    def test_open_only_and_string_true_are_not_verified(self):
        for flag in (False, "true", 1, None):
            with self.subTest(flag=flag):
                rate = self.verified()
                rate["EURUSD"]["covers_open_and_close"] = flag
                with self.assertRaisesRegex(QDLEError, "open AND close"):
                    verified_roundtrip_fee_for_symbol(rate, "EURUSD")

    def test_missing_index_fee_never_substituted_with_zero(self):
        with self.assertRaisesRegex(QDLEError, "missing verified"):
            verified_roundtrip_fee_for_symbol(self.verified(), "NDX100")

    def test_invalid_numeric_fee_and_missing_source_rejected(self):
        for amount in ("nan", "-0.01", "nonsense"):
            with self.subTest(amount=amount):
                rate = self.verified()
                rate["EURUSD"]["usd_per_lot"] = amount
                with self.assertRaises(QDLEError):
                    verified_roundtrip_fee_for_symbol(rate, "EURUSD")
        rate = self.verified()
        rate["EURUSD"]["evidence"] = ""
        with self.assertRaises(QDLEError):
            verified_roundtrip_fee_for_symbol(rate, "EURUSD")

    def test_verified_zero_fee_can_exist_only_with_account_evidence(self):
        rate = self.verified()
        rate["EURUSD"]["usd_per_lot"] = "0"
        result = verified_roundtrip_fee_for_symbol(rate, "EURUSD")
        self.assertEqual(result.usd_per_lot, D("0"))
        self.assertTrue(result.covers_open_and_close)


if __name__ == "__main__":
    unittest.main()

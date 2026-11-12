"""Offline SHA-pinned bid/ask research tape I/O fixtures only."""
from __future__ import annotations

import csv
import hashlib
import json
import tempfile
import unittest
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path

from research.crt_r4a_holdout.economic_replay import SOURCE_PINE
from research.crt_r4a_holdout.economic_replay_io import load_and_replay
from research.crt_r4a_holdout.seven_family_contract import Family

T = datetime(2024, 2, 1, 8, tzinfo=UTC)


def hashfile(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


class IngestionQA(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        root = Path(self.tmp.name)
        self.paths = {
            key: root / (key + (".csv" if key in ("quotes", "swaps") else ".json"))
            for key in ("signals", "quotes", "costs", "swaps")
        }
        self.manifest = root / "manifest.json"
        self.signals = [{
            "symbol": "EURUSD", "provider_cohort": "SYNTHETIC_TEST_ONLY",
            "source_pine_blob": SOURCE_PINE,
            "family": Family.TWO_C_MSS_C2.value,
            "source_event_id": "AUDIT-EVENT-1",
            "direction": 1,
            "mss_at": (T - timedelta(minutes=15)).isoformat(),
            "ratified_at": T.isoformat(),
            "available_at": T.isoformat(),
            "atr_h4": "4", "price_tick": "0.1",
            "geometry": {
                "c1_high": "120", "c1_low": "100",
                "setup_open": "109", "setup_close": "110",
                "sweep_high": "116", "sweep_low": "99",
            },
        }]
        self.paths["signals"].write_text(json.dumps(self.signals), encoding="utf-8")
        self.paths["costs"].write_text(json.dumps({
            "commission_per_unit_per_side_quote": "0.1",
            "adverse_slippage_price": "0.1",
        }), encoding="utf-8")
        with self.paths["quotes"].open("w", newline="", encoding="utf-8") as fh:
            w = csv.writer(fh)
            w.writerow((
                "opened_at", "bid_open", "bid_high", "bid_low", "bid_close",
                "ask_open", "ask_high", "ask_low", "ask_close",
            ))
            w.writerow((T.isoformat(), "110", "111", "108", "110",
                        "110.2", "111.2", "109.2", "110.2"))
            w.writerow(((T + timedelta(minutes=5)).isoformat(),
                        "110", "121", "108", "111",
                        "110.2", "121.2", "108.2", "111.2"))
        self.paths["swaps"].write_text(
            "charged_at,quote_amount_per_unit\n", encoding="utf-8"
        )
        self.refresh_manifest()

    def refresh_manifest(self) -> None:
        self.manifest.write_text(json.dumps({
            "symbol": "EURUSD",
            "provider_cohort": "SYNTHETIC_TEST_ONLY",
            "source_pine_blob": SOURCE_PINE,
            "sha256": {
                key: hashfile(p) for key, p in self.paths.items()
            },
        }), encoding="utf-8")

    def run_replay(self) -> dict:
        return load_and_replay(
            manifest=self.manifest,
            signals=self.paths["signals"],
            quotes=self.paths["quotes"],
            costs=self.paths["costs"],
            swaps=self.paths["swaps"],
            quantity=Decimal("1"),
        )

    def test_01_valid_sha_pinned_synthetic_quotes_produce_ledger(self) -> None:
        report = self.run_replay()
        self.assertEqual(report["all_families"]["closed"], 1)
        self.assertEqual(report["ledger"][0]["status"], "CLOSED_TARGET")
        self.assertEqual(len(report["by_family"]), 7)
        self.assertEqual(report["broker_orders_executed"], 0)

    def test_02_tampering_with_quote_file_blocks_replay(self) -> None:
        with self.paths["quotes"].open("a", encoding="utf-8") as fh:
            fh.write("\n")
        with self.assertRaisesRegex(ValueError, "quotes.*SHA256"):
            self.run_replay()

    def test_03_tampering_with_signal_file_blocks_replay(self) -> None:
        self.paths["signals"].write_text("[]", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "signals.*SHA256"):
            self.run_replay()

    def test_04_no_pine_parity_or_holdout_claims(self) -> None:
        report = self.run_replay()
        self.assertFalse(report["original_pine_event_parity"])
        self.assertFalse(report["unseen_24m_holdout"])
        self.assertFalse(report["provider_identity_independently_certified"])
        self.assertFalse(report["verified_account_currency_pnl"])
        self.assertEqual(report["unit"], "QUOTE_PRICE_TIMES_SUPPLIED_QUANTITY_NOT_ACCOUNT_USD")

    def test_05_invalid_source_pine_fingerprint_fails(self) -> None:
        data = json.loads(self.manifest.read_text())
        data["source_pine_blob"] = "another"
        self.manifest.write_text(json.dumps(data), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "Pine R4-A"):
            self.run_replay()

    def test_06_naive_timestamp_cannot_be_loaded(self) -> None:
        self.signals[0]["available_at"] = "2024-02-01T08:00:00"
        self.paths["signals"].write_text(json.dumps(self.signals), encoding="utf-8")
        self.refresh_manifest()
        with self.assertRaisesRegex(ValueError, "UTC offset"):
            self.run_replay()

    def test_07_missing_ask_column_fails_closed(self) -> None:
        self.paths["quotes"].write_text(
            "opened_at,bid_open,bid_high,bid_low,bid_close\n",
            encoding="utf-8",
        )
        self.refresh_manifest()
        with self.assertRaisesRegex(ValueError, "missing required"):
            self.run_replay()

    def test_08_duplicate_event_is_not_two_trades(self) -> None:
        self.signals.append(dict(self.signals[0]))
        self.paths["signals"].write_text(json.dumps(self.signals), encoding="utf-8")
        self.refresh_manifest()
        with self.assertRaisesRegex(ValueError, "duplicated"):
            self.run_replay()


if __name__ == "__main__":
    unittest.main(verbosity=2)

"""Synthetic fail-closed controls for Native 10Y cTrader M1 capture, no network."""
from __future__ import annotations

import os
import tempfile
import unittest
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from qore.infrastructure.trader_lab import (
    qore_native_icmarkets_missing_m1_capture_v1 as m,
)
from qore.infrastructure.trader_lab import (
    qore_native_icmarkets_missing_m5_capture_v1 as m5,
)
from qore.infrastructure.trader_lab.qore_native_icmarkets_catalog_preflight_v1 import (
    match_catalog,
)
from qore.infrastructure.trader_lab.qore_native_universe_33_source_registry_v1 import (
    M1_10Y, universe,
)


class NativeMissingM1Tests(unittest.TestCase):
    def test_exact_universe_count_and_distinctness(self):
        self.assertEqual(len(universe()), 33)
        self.assertEqual(len(m.TARGET_SYMBOLS), 24)
        self.assertEqual(len(set(m.TARGET_SYMBOLS)), 24)
        self.assertEqual(set(m.TARGET_SYMBOLS), set(universe()) - M1_10Y)

    def test_reject_archived_native_m1_symbols(self):
        for sym in M1_10Y:
            self.assertNotIn(sym, m.TARGET_SYMBOLS)
            with self.assertRaisesRegex(ValueError, "NOT_ADMITTED"):
                m.require_icmarkets_source(sym)

    def test_symbol_mappings_provenance_not_silent_alias(self):
        self.assertEqual(m.PROVIDER_SYMBOL_MAP["SP500"], "US500")
        self.assertEqual(m.PROVIDER_SYMBOL_MAP["US30"], "US30")
        self.assertEqual(m.PROVIDER_SYMBOL_MAP["XAGUSD"], "XAGUSD")
        self.assertEqual(m.PROVIDER_SYMBOL_MAP["NZDUSD"], "NZDUSD")
        self.assertEqual(len(m.PROVIDER_SYMBOL_MAP), 24)

    def test_provider_alias_us500_must_be_exact_in_catalog(self):
        q = match_catalog([SimpleNamespace(
            symbolName="US500", symbolId=47, enabled=True
        )])
        self.assertIn("US500", q["available_exact"])
        self.assertEqual(q["catalog_exact_matches"]["US500"]["symbol_id"], 47)

    def test_provider_unavailable_closed(self):
        with patch.object(m, "probe_catalog", return_value={
            "status": "ICMARKETS_DEMO_CATALOG_VERIFIED",
            "_ephemeral_account_id": 17,
            "catalog": {"catalog_exact_matches": {}},
        }):
            with self.assertRaisesRegex(ValueError, "EXACT_PROVIDER"):
                m.require_icmarkets_source("SP500")

    def test_provider_disabled_closed(self):
        with patch.object(m, "probe_catalog", return_value={
            "status": "ICMARKETS_DEMO_CATALOG_VERIFIED",
            "_ephemeral_account_id": 17,
            "catalog": {"catalog_exact_matches": {
                "US500": {"broker_symbol": "US500", "symbol_id": 27, "enabled": False},
            }},
        }):
            with self.assertRaisesRegex(ValueError, "EXACT_PROVIDER"):
                m.require_icmarkets_source("SP500")

    def test_positive_source_proof_only_icmarkets(self):
        with patch.object(m, "probe_catalog", return_value={
            "status": "ICMARKETS_DEMO_CATALOG_VERIFIED",
            "_ephemeral_account_id": 101,
            "catalog": {"catalog_exact_matches": {
                "US500": {"broker_symbol": "US500", "symbol_id": 27, "enabled": True},
            }},
        }):
            self.assertEqual(m.require_icmarkets_source("SP500"), (101, 27))

    def test_foreign_account_catalog_is_rejected(self):
        with patch.object(m, "probe_catalog", return_value={
            "status": "ICMARKETS_DEMO_AUTH_OR_CATALOG_BLOCKED",
            "_ephemeral_account_id": 101,
            "catalog": {},
        }):
            with self.assertRaisesRegex(ValueError, "ACCOUNT_PROOF_FAILED"):
                m.require_icmarkets_source("NZDUSD")

    def test_no_demo_source_proof_no_file_created(self):
        with tempfile.TemporaryDirectory() as td:
            output = Path(td) / "artifact"
            for proof in (None, (0, 20), (7, -3), (True, 9), ("10", 10)):
                with self.subTest(proof=proof):
                    with self.assertRaisesRegex(ValueError, "SOURCE_PROOF_REQUIRED"):
                        m.clone_symbol("NZDUSD", output, source_proof=proof)
                    self.assertFalse(output.exists())

    def test_10y_period_no_future_no_fill(self):
        self.assertEqual(m.PERIOD_M1, 1)
        self.assertEqual(m.TARGET_START.isoformat(), "2016-09-17T00:00:00+00:00")
        self.assertEqual(m.TARGET_END_EXCLUSIVE.isoformat(), "2026-09-17T00:00:00+00:00")
        self.assertEqual(m.CHUNK_DAYS, 2)
        self.assertEqual(m.MAX_BARS_PER_CHUNK, 2880)

    def test_year_partitions_contiguous(self):
        items = m._year_partitions()
        self.assertEqual(items[0][1], m.TARGET_START)
        self.assertEqual(items[-1][2], m.TARGET_END_EXCLUSIVE)
        self.assertEqual(len(items), 11)
        for left, right in zip(items, items[1:]):
            self.assertEqual(left[2], right[1])

    def test_provider_relative_raw_decode(self):
        row = m._provider_bar(SimpleNamespace(
            utcTimestampInMinutes=30000000,
            low=2000000,
            deltaOpen=12,
            deltaHigh=30,
            deltaClose=14,
            volume=5,
        ), canonical_symbol="NZDUSD", provider_symbol="NZDUSD",
            symbol_id=12, digits=5)
        self.assertEqual(row.open_relative, 2000012)
        self.assertEqual(row.high_relative, 2000030)
        self.assertEqual(row.close_relative, 2000014)
        self.assertEqual(row.volume, 5)
        self.assertEqual(row.utc_timestamp_in_minutes, 30000000)

    def test_invalid_native_bar_rejected(self):
        for low, high in ((0, 30), (100, 3)):
            x = SimpleNamespace(
                utcTimestampInMinutes=30000000, low=low,
                deltaOpen=12, deltaHigh=high, deltaClose=14,
                volume=None)
            with self.assertRaises(ValueError):
                m._provider_bar(
                    x, canonical_symbol="XAGUSD", provider_symbol="XAGUSD",
                    symbol_id=1, digits=3)

    def test_m1_reader_requests_native_provider_resolution(self):
        calls = []
        class Fake:
            account_id = 101
            def request(self, op, fields, **kwargs):
                calls.append((op, fields, kwargs))
                return SimpleNamespace(value=SimpleNamespace(trendbar=()))
        left = datetime(2022, 6, 1, tzinfo=UTC)
        right = datetime(2022, 6, 3, tzinfo=UTC)
        bars = m._read_chunk(Fake(), symbol="NZDUSD", symbol_id=12,
                             opened_at=left, closed_at=right, chunk_index=4)
        self.assertEqual(bars, ())
        self.assertEqual(len(calls), 1)
        op, params, _ = calls[0]
        self.assertEqual(op, "ProtoOAGetTrendbarsReq")
        self.assertEqual(params["period"], 1)
        self.assertEqual(params["symbolId"], 12)
        self.assertEqual(params["toTimestamp"], int(right.timestamp() * 1000) - 1)
        self.assertNotIn("count", params)

    def test_no_provider_overfull_m1(self):
        class Fake:
            account_id = 101
            def request(self, op, fields, **kwargs):
                return SimpleNamespace(value=SimpleNamespace(
                    trendbar=[object()] * 2881))
        with self.assertRaisesRegex(RuntimeError, "calendar grid"):
            m._read_chunk(Fake(), symbol="NZDUSD", symbol_id=12,
                          opened_at=datetime(2022, 6, 1, tzinfo=UTC),
                          closed_at=datetime(2022, 6, 3, tzinfo=UTC),
                          chunk_index=0)

    def test_m1_adapter_isolated_scope_and_refresh(self):
        self.assertIs(m._ReadOnlyIcMarketsHistoryClient, m5._ReadOnlyIcMarketsHistoryClient)
        self.assertTrue(m5._history_scope_allowed(0))
        self.assertFalse(m5._history_scope_allowed(True))
        self.assertIn("REAUTH_REQUIRED",
                      str(m._ReadOnlyIcMarketsHistoryClient._refresh_tokens(None).error))

    def test_capture_uses_ephemeral_account_and_not_live_broker(self):
        with tempfile.TemporaryDirectory() as td, patch.dict(os.environ, {}, clear=True):
            with patch.object(m, "_credentials", side_effect=RuntimeError("DUMMY_CREDENTIALS")):
                with self.assertRaisesRegex(RuntimeError, "DUMMY_CREDENTIALS"):
                    m.clone_symbol("NZDUSD", Path(td) / "sample", source_proof=(101, 12))
            self.assertEqual(os.environ.get("QORE_CTRADER_DEMO_ACCOUNT_ID"), "101")

    def test_sha256_is_content_based(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td) / "a.txt"
            p.write_bytes(b"abc")
            self.assertEqual(
                m._sha256(p),
                "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"
            )


if __name__ == "__main__":
    unittest.main()

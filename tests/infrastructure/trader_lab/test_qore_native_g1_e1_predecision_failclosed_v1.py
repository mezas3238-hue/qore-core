"""Synthetic strict Gate checks: no original broker quotes or holdout needed."""
from __future__ import annotations

import gzip
import hashlib
import json
import tempfile
import unittest
from datetime import UTC, datetime
from pathlib import Path

from qore.infrastructure.trader_lab import qore_native_g1_e1_predecision_failclosed_v1 as gate


def record():
    start = datetime(2023, 3, 21, 13, 0, tzinfo=UTC)
    end = datetime(2023, 3, 21, 15, 0, tzinfo=UTC)
    method, symbol = "SWEEP_RECLAIM", "USDJPY"
    identity = hashlib.sha256(
        f"{gate.E1_SHA}|{method}|{symbol}|{start.isoformat()}".encode()
    ).hexdigest()
    return {
        "opportunity_sha256": identity, "method_id": method, "symbol": symbol,
        "entry_research_utc": start.isoformat(),
        "theoretical_M5_target_close_utc": end.isoformat(),
        "duration_minutes": 120,
        "broker_provenance": "ORIGINAL12_G0_CONTRACT_UNHOMOLOGATED",
        "news_asof_filtered": False, "real_broker_fill": False,
        "outcome_exported": False,
    }


def witness(row):
    return {
        "opportunity_sha256": row["opportunity_sha256"],
        "symbol": row["symbol"], "method_id": row["method_id"],
        "closed_bar_available_at_utc": "2023-03-21T13:05:00+00:00",
        "all_features_observed_at_utc": "2023-03-21T13:05:01+00:00",
        "decision_emitted_at_utc": "2023-03-21T13:05:02+00:00",
        "entry_order_eligible_at_utc": "2023-03-21T13:05:03+00:00",
        "order_expiration_at_utc": "2023-03-21T13:15:00+00:00",
        "independent_witness_sha256": "b"*64,
        "signal_side": "LONG",
    }


class ResearchClockAndCausalWitnessTest(unittest.TestCase):
    def test_original_clock_is_valid_research_not_trading(self):
        row = record()
        self.assertEqual(gate.read_research_event(row)[0].year, 2023)
        result = gate.assess_predecision_shape(row, None)
        self.assertFalse(result["causal_structure_pass"])
        self.assertFalse(result["historical_NET_authorized"])
        self.assertEqual(result["reason"], gate.BLOCK_REASON)

    def test_unsigned_structurally_valid_witness_never_authorizes(self):
        row = record()
        result = gate.assess_predecision_shape(row, witness(row))
        self.assertTrue(result["causal_structure_pass"])
        self.assertFalse(result["witness_verified"])
        self.assertFalse(result["order_authorized"])
        self.assertFalse(result["historical_NET_authorized"])

    def test_reject_future_feature_observation(self):
        row = record()
        w = witness(row)
        w["all_features_observed_at_utc"] = "2023-03-21T13:05:04+00:00"
        with self.assertRaisesRegex(ValueError, "CAUSAL_CLOCK"):
            gate.assess_predecision_shape(row, w)

    def test_reject_bar_close_available_after_decision(self):
        row = record()
        w = witness(row)
        w["closed_bar_available_at_utc"] = "2023-03-21T13:07:00+00:00"
        with self.assertRaisesRegex(ValueError, "CAUSAL_CLOCK"):
            gate.assess_predecision_shape(row, w)

    def test_reject_ambiguous_time_and_expired_order(self):
        row = record()
        w = witness(row)
        w["decision_emitted_at_utc"] = "2023-03-21T13:05:02"
        with self.assertRaisesRegex(ValueError, "NOT_EXPLICIT_UTC"):
            gate.assess_predecision_shape(row, w)
        w = witness(row)
        w["order_expiration_at_utc"] = w["entry_order_eligible_at_utc"]
        with self.assertRaisesRegex(ValueError, "CAUSAL_CLOCK"):
            gate.assess_predecision_shape(row, w)

    def test_reject_tampered_identity_or_outcome_field(self):
        row = record()
        row["opportunity_sha256"] = "a"*64
        with self.assertRaisesRegex(ValueError, "IDENTITY_DRIFT"):
            gate.read_research_event(row)
        row = record()
        row["gross_bps"] = 100000
        with self.assertRaisesRegex(ValueError, "SCHEMA_DRIFT"):
            gate.read_research_event(row)

    def test_reject_embargo_and_fake_fill(self):
        row = record()
        row["entry_research_utc"] = "2025-01-01T13:00:00+00:00"
        with self.assertRaises(ValueError):
            gate.read_research_event(row)
        row = record()
        row["real_broker_fill"] = True
        with self.assertRaisesRegex(ValueError, "NO_EXECUTION"):
            gate.read_research_event(row)

    def test_six_methods_reject_preclose_feature_witness(self):
        row = record()
        self.assertIn(row["method_id"], gate.SAME_BOUNDARY_SIGNAL_METHODS)
        w = witness(row)
        w["closed_bar_available_at_utc"] = "2023-03-21T12:55:00+00:00"
        w["all_features_observed_at_utc"] = "2023-03-21T12:55:01+00:00"
        with self.assertRaisesRegex(ValueError, "M5_CLOSE_BEFORE_BAR_FINISHED"):
            gate.assess_predecision_shape(row, w)

    def test_trend_prior_session_signal_not_confused_with_current_baseline(self):
        row = record()
        row["method_id"] = "TREND_MULTI_DAY"
        row["entry_research_utc"] = "2023-03-21T16:00:00+00:00"
        row["theoretical_M5_target_close_utc"] = "2023-03-21T20:00:00+00:00"
        row["duration_minutes"] = 240
        start = gate.utc(row["entry_research_utc"])
        row["opportunity_sha256"] = hashlib.sha256(
            f"{gate.E1_SHA}|TREND_MULTI_DAY|USDJPY|{start.isoformat()}".encode()
        ).hexdigest()
        w = witness(row)
        w["closed_bar_available_at_utc"] = "2023-03-21T15:00:00+00:00"
        w["all_features_observed_at_utc"] = "2023-03-21T15:01:00+00:00"
        w["decision_emitted_at_utc"] = "2023-03-21T15:02:00+00:00"
        w["entry_order_eligible_at_utc"] = "2023-03-21T15:02:01+00:00"
        w["order_expiration_at_utc"] = "2023-03-21T16:10:00+00:00"
        result = gate.assess_predecision_shape(row, w)
        self.assertTrue(result["causal_structure_pass"])
        self.assertFalse(result["historical_NET_authorized"])

    def test_reject_witness_provenance_mismatch(self):
        row = record()
        w = witness(row)
        w["symbol"] = "GBPUSD"
        with self.assertRaisesRegex(ValueError, "PROVENANCE"):
            gate.assess_predecision_shape(row, w)

    def test_one_row_full_stream_and_determinism(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            source = root / "clocks.gz"
            with gzip.open(source, "wt", encoding="utf-8") as f:
                f.write(json.dumps(record()) + "\n")
            a = gate.audit_legacy_clock_ledger(source, root/"a", expected_rows=1)
            b = gate.audit_legacy_clock_ledger(source, root/"b", expected_rows=1)
            self.assertEqual(a["blocked_ledger_gzip_sha256"],
                             b["blocked_ledger_gzip_sha256"])
            self.assertEqual(a["research_clocks_rejected_as_orders"], 1)
            self.assertFalse(a["historical_NET_authorized"])
            with gzip.open(root/"a"/"E1_PREDECISION_REJECTED_CLOCKS_ONLY.jsonl.gz",
                           "rt", encoding="utf-8") as f:
                blocked = json.loads(f.readline())
            self.assertIsNone(blocked["entry_order_eligible_at_utc"])
            self.assertFalse(blocked["orders_authorized"])
            self.assertNotIn("gross_bps", blocked)

    def test_duplicate_opportunity_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            source = root/"clocks.gz"
            with gzip.open(source, "wt", encoding="utf-8") as f:
                f.write(json.dumps(record()) + "\n")
                f.write(json.dumps(record()) + "\n")
            with self.assertRaisesRegex(ValueError, "DUPLICATE_RESEARCH"):
                gate.audit_legacy_clock_ledger(source, root/"out", expected_rows=2)
            self.assertFalse(
                (root/"out"/"E1_PREDECISION_REJECTED_CLOCKS_ONLY.jsonl.gz").exists())

    def test_duplicate_json_key_rejected(self):
        with self.assertRaisesRegex(ValueError, "DUPLICATE_JSON_KEY"):
            json.loads('{"symbol":"USDJPY","symbol":"EURUSD"}',
                       object_pairs_hook=gate.unique_keys)


if __name__ == "__main__":
    unittest.main()

"""Aggregation of independently owned event tapes, not economic trades."""
from __future__ import annotations

import json
import tempfile
import unittest
from datetime import UTC, datetime, timedelta
from pathlib import Path

from research.crt_r4a_holdout.aggregate_seven_family_events import (
    validate_event_tape,
)
from research.crt_r4a_holdout.seven_family_contract import Family
from research.crt_r4a_holdout.seven_family_event_tape import (
    PINE_BLOB,
    SCHEMA,
    GATES_NOT_SATISFIED,
)
from research.crt_r4a_holdout.economic_replay_io import digest

T = datetime(2024, 2, 1, 8, tzinfo=UTC)


class EventTapeAggregationQA(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        p = Path(self.tmp.name) / "qore-crt-r4a-seven-EURUSD"
        p.mkdir()
        self.path = p / "integrated.json"
        self.tape = p / "events.jsonl"
        self.rows = [
            {
                "schema": SCHEMA,
                "source_pine_blob": PINE_BLOB,
                "symbol": "EURUSD",
                "original_provider_symbol": "EURUSD",
                "provider_cohort": "ATLAS_DEMO_BROKER_UNVERIFIED",
                "family": Family.TWO_C_MSS_C2.value,
                "source_event_id": "original-owned-id",
                "available_at": T.isoformat(),
                "source_ownership": "OWN_BASE_CRT_FROZEN_MSS",
                "parent_event_id": None,
                "geometry": {"c1_high": "120", "c1_low": "100"},
                "economic_ready": False,
                "missing_certification_gates": list(GATES_NOT_SATISFIED),
                "broker_orders_executed": 0,
            },
            {
                "schema": SCHEMA,
                "source_pine_blob": PINE_BLOB,
                "symbol": "EURUSD",
                "original_provider_symbol": "EURUSD",
                "provider_cohort": "ATLAS_DEMO_BROKER_UNVERIFIED",
                "family": Family.M15_RETEST.value,
                "source_event_id": "retest-owned-source-id",
                "available_at": (T + timedelta(minutes=15)).isoformat(),
                "source_ownership": "LINKED_PARENT_2C_MSS15_CLOSED_M15_RETEST",
                "parent_event_id": "original-owned-id",
                "geometry": {
                    "retest_close": "111",
                    "retest_closed_at": (T + timedelta(minutes=15)).isoformat(),
                },
                "economic_ready": False,
                "missing_certification_gates": list(GATES_NOT_SATISFIED),
                "broker_orders_executed": 0,
            },
        ]
        self.write_tape()
        self.counts = {family.value: 0 for family in Family}
        self.counts[Family.TWO_C_MSS_C2.value] = 1
        self.counts[Family.M15_RETEST.value] = 1
        self.report = {
            "canonical_symbol": "EURUSD",
            "original_symbol": "EURUSD",
            "provider_cohort": "ATLAS_DEMO_BROKER_UNVERIFIED",
            "seven_family_research_event_counts": self.counts,
        }
        self.refresh_manifest()

    def write_tape(self) -> None:
        self.tape.write_text(
            "".join(
                json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n"
                for row in self.rows
            ),
            encoding="utf-8",
        )

    def refresh_manifest(self) -> None:
        self.report["source_event_tape"] = {
            "events_file_sha256": digest(self.tape),
            "rows": len(self.rows),
            "by_family": self.counts,
            "price_backtest_certified": False,
            "broker_orders_executed": 0,
        }

    def test_01_provenance_and_owner_relationship_reconciled(self) -> None:
        validate_event_tape(self.report, self.path)
        self.assertTrue(self.report["individual_source_event_tape_verified"])

    def test_02_tampered_tape_does_not_pass_hash(self) -> None:
        self.tape.write_bytes(self.tape.read_bytes() + b" ")
        with self.assertRaisesRegex(ValueError, "hash mismatch"):
            validate_event_tape(self.report, self.path)

    def test_03_unknown_parent_fails_even_with_matching_sha(self) -> None:
        self.rows[1]["parent_event_id"] = "other-cycle"
        self.write_tape()
        self.refresh_manifest()
        with self.assertRaisesRegex(ValueError, "unmatched parent"):
            validate_event_tape(self.report, self.path)

    def test_04_fake_price_certification_fails_even_with_matching_sha(self) -> None:
        self.rows[0]["economic_ready"] = True
        self.write_tape()
        self.refresh_manifest()
        with self.assertRaisesRegex(ValueError, "economic-gate"):
            validate_event_tape(self.report, self.path)

    def test_05_duplicate_event_ids_fail(self) -> None:
        self.rows[1]["source_event_id"] = self.rows[0]["source_event_id"]
        self.write_tape()
        self.refresh_manifest()
        with self.assertRaisesRegex(ValueError, "duplicate"):
            validate_event_tape(self.report, self.path)

    def test_06_unordered_available_times_fail(self) -> None:
        self.rows[0]["available_at"] = (
            T + timedelta(minutes=30)
        ).isoformat()
        self.write_tape()
        self.refresh_manifest()
        with self.assertRaisesRegex(ValueError, "unordered"):
            validate_event_tape(self.report, self.path)

    def test_07_unseen_provider_alias_does_not_pass(self) -> None:
        self.rows[1]["symbol"] = "NAS100"
        self.write_tape()
        self.refresh_manifest()
        with self.assertRaisesRegex(ValueError, "identity"):
            validate_event_tape(self.report, self.path)

    def test_08_wrong_per_family_totals_fail(self) -> None:
        self.report["seven_family_research_event_counts"] = dict(self.counts)
        self.report["seven_family_research_event_counts"][Family.M15_RETEST.value] = 0
        with self.assertRaisesRegex(ValueError, "does not reconcile"):
            validate_event_tape(self.report, self.path)


if __name__ == "__main__":
    unittest.main(verbosity=2)

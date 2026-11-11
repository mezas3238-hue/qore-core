"""Synthetic-only Pine/replay exact event parity gate; no actual Pine data."""
from __future__ import annotations

import csv
import tempfile
import unittest
from pathlib import Path

from research.crt_r4a_holdout.parity_gate import ALL, compare


def row(**changes: str) -> dict[str, str]:
    result = {
        "event_id": "IC_EURUSD_2024_02_01_C1_001",
        "symbol": "EURUSD",
        "model": "B_TRUE3C_MSS5",
        "side": "LONG",
        "c1_at": "2024-02-01T00:00:00Z",
        "sweep_at": "2024-02-01T06:00:00Z",
        "ratified_at": "2024-02-01T08:00:00Z",
        "mss_at": "2024-02-01T07:00:00Z",
        "available_at": "2024-02-01T08:00:00Z",
        "c1_high": "105",
        "c1_low": "95",
        "sweep_high": "104",
        "sweep_low": "92",
        "mss_pivot": "100.50",
    }
    result.update(changes)
    return result


class ParityTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.base = Path(self.tmp.name)
        self.pine = self.base / "pine.csv"
        self.replay = self.base / "replay.csv"
        self.write(self.pine, [row()])
        self.write(self.replay, [row()])

    def tearDown(self) -> None:
        self.tmp.cleanup()

    @staticmethod
    def write(path: Path, records: list[dict[str, str]]) -> None:
        with path.open("w", newline="", encoding="utf-8") as fh:
            writer = csv.DictWriter(fh, fieldnames=list(ALL))
            writer.writeheader()
            writer.writerows(records)

    def test_01_identical_causal_event_passes(self) -> None:
        report = compare(self.pine, self.replay)
        self.assertEqual(report["status"], "PASS_EVENT_PARITY_ONLY")
        self.assertEqual(report["field_mismatch_count"], 0)

    def test_02_exact_integer_decimal_equality(self) -> None:
        self.write(self.replay, [row(mss_pivot="100.5000")])
        self.assertEqual(compare(self.pine, self.replay)["status"], "PASS_EVENT_PARITY_ONLY")

    def test_03_mss_level_difference_fails(self) -> None:
        self.write(self.replay, [row(mss_pivot="100.51")])
        report = compare(self.pine, self.replay)
        self.assertEqual(report["status"], "FAIL_PARITY")
        self.assertEqual(report["field_mismatch_count"], 1)

    def test_04_timestamp_one_minute_drift_fails(self) -> None:
        self.write(self.replay, [row(mss_at="2024-02-01T07:01:00Z")])
        self.assertEqual(compare(self.pine, self.replay)["status"], "FAIL_PARITY")

    def test_05_correct_timezone_equivalence(self) -> None:
        self.write(self.replay, [row(mss_at="2024-02-01T04:00:00-03:00")])
        self.assertEqual(compare(self.pine, self.replay)["status"], "PASS_EVENT_PARITY_ONLY")

    def test_06_extra_event_fails(self) -> None:
        self.write(self.replay, [
            row(), row(event_id="ANOTHER_EVENT", symbol="GBPUSD")
        ])
        r = compare(self.pine, self.replay)
        self.assertEqual(r["status"], "FAIL_PARITY")
        self.assertEqual(r["extra_in_replay_count"], 1)

    def test_07_missing_event_fails(self) -> None:
        self.write(self.replay, [])
        self.assertEqual(compare(self.pine, self.replay)["status"], "BLOCKED_EMPTY_EVENT_TAPE")

    def test_08_duplicated_event_rejected(self) -> None:
        self.write(self.replay, [row(), row()])
        with self.assertRaisesRegex(ValueError, "duplicated"):
            compare(self.pine, self.replay)

    def test_09_future_lookahead_rejected(self) -> None:
        self.write(self.replay, [row(available_at="2024-02-01T07:00:00Z")])
        with self.assertRaisesRegex(ValueError, "future-looking"):
            compare(self.pine, self.replay)

    def test_10_true3c_mss_after_c3_close_rejected(self) -> None:
        self.write(self.replay, [
            row(
                mss_at="2024-02-01T08:05:00Z",
                available_at="2024-02-01T08:05:00Z"
            )
        ])
        with self.assertRaisesRegex(ValueError, "TRUE3C MSS5"):
            compare(self.pine, self.replay)

    def test_11_model_a_late_mss_accepted(self) -> None:
        example = row(
            model="A_2C_MSS15",
            mss_at="2024-02-01T08:15:00Z",
            available_at="2024-02-01T08:15:00Z",
        )
        self.write(self.pine, [example])
        self.write(self.replay, [example])
        self.assertEqual(compare(self.pine, self.replay)["status"], "PASS_EVENT_PARITY_ONLY")

    def test_12_different_model_not_equivalent(self) -> None:
        self.write(self.replay, [row(model="A_2C_MSS15")])
        self.assertEqual(compare(self.pine, self.replay)["status"], "FAIL_PARITY")

    def test_13_fake_source_not_accepted(self) -> None:
        self.write(self.replay, [row(symbol="NOT_IC")])
        with self.assertRaisesRegex(ValueError, "invalid universe"):
            compare(self.pine, self.replay)

    def test_14_no_naive_timestamp(self) -> None:
        self.write(self.replay, [row(mss_at="2024-02-01T07:00:00")])
        with self.assertRaisesRegex(ValueError, "offset"):
            compare(self.pine, self.replay)

    def test_15_price_geometry_invalid(self) -> None:
        self.write(self.replay, [row(c1_low="107")])
        with self.assertRaisesRegex(ValueError, "geometry"):
            compare(self.pine, self.replay)

    def test_16_never_claims_economic_certification(self) -> None:
        result = compare(self.pine, self.replay)
        self.assertIs(result["holdout_virginity_proven"], False)
        self.assertIs(result["market_data_parity_independently_proven"], False)
        self.assertIn("NO_ECONOMIC_CERTIFICATION", result["scope"])


if __name__ == "__main__":
    unittest.main(verbosity=2)

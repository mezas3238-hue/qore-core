"""Reproducible GitHub artifact metadata-only source census (no network)."""
from __future__ import annotations

import unittest
from datetime import UTC, datetime, timedelta

from qore.infrastructure.trader_lab import qore_native_data_archive_expiry_register_v1 as m

NOW = datetime(2026, 10, 12, 15, 0, tzinfo=UTC)


def samples(
    *,
    completed: set[int] | None = None,
    omitted: tuple[int, str] | None = None,
    expiry: datetime | None = None,
) -> tuple[dict, dict]:
    good = completed if completed is not None else set(x[0] for x in m.RUNS)
    runs, assets = {}, {}
    for rid, _, symbols, prefix in m.RUNS:
        sha = ("%040x" % rid)
        runs[rid] = {
            "id": rid, "status": "completed" if rid in good else "in_progress",
            "conclusion": "success" if rid in good else None, "head_sha": sha,
        }
        assets[rid] = []
        for i, symbol in enumerate(sorted(symbols), start=1):
            if omitted == (rid, symbol):
                continue
            assets[rid].append({
                "id": rid * 100 + i,
                "name": f"{prefix}{symbol}-{sha}",
                "size_in_bytes": 1000000,
                "expired": False,
                "expires_at": (expiry or NOW + timedelta(days=50)).isoformat(),
            })
    return runs, assets


class ArchiveRegisterTests(unittest.TestCase):
    def test_real_cohort_contract(self):
        self.assertEqual(len(m.RUNS), 5)
        self.assertEqual(sum(len(x[2]) for x in m.RUNS[:2]), 33)
        self.assertEqual(sum(len(x[2]) for x in m.RUNS[2:]), 33)
        self.assertEqual(len(m.M1_PILOT), 3)
        self.assertEqual(len(m.M1_REMAINING), 21)

    def test_33x2_fully_available_metadata_only(self):
        runs, arts = samples()
        o = m.evaluate(runs, arts, now=NOW)
        self.assertEqual(o["metadata_available"], {"M5": 33, "M1": 33, "universe": 33})
        self.assertEqual((o["m5_missing"], o["m1_missing"]), ([], []))
        self.assertFalse(o["all_artifacts_restored_and_hashed"])
        self.assertFalse(o["all_artifacts_backed_up_permanently"])

    def test_pilot_pending_leaves_nine_old_m1(self):
        runs, arts = samples(completed={m.M5_ORIGINAL_RUN, m.M5_NEW_RUN, m.M1_ORIGINAL_RUN})
        o = m.evaluate(runs, arts, now=NOW)
        self.assertEqual(o["metadata_available"], {"M5": 33, "M1": 9, "universe": 33})
        self.assertEqual(len(o["m1_missing"]), 24)

    def test_pilot_finished_but_remaining_pending(self):
        runs, arts = samples(completed={
            m.M5_ORIGINAL_RUN, m.M5_NEW_RUN, m.M1_ORIGINAL_RUN, m.M1_PILOT_RUN
        })
        o = m.evaluate(runs, arts, now=NOW)
        self.assertEqual(o["metadata_available"]["M1"], 12)
        self.assertEqual(len(o["m1_missing"]), 21)

    def test_missing_zip_does_not_count(self):
        runs, arts = samples(omitted=(m.M5_NEW_RUN, "USDCHF"))
        o = m.evaluate(runs, arts, now=NOW)
        self.assertEqual(o["metadata_available"]["M5"], 32)
        self.assertEqual(o["m5_missing"], ["USDCHF"])

    def test_expired_zip_does_not_count(self):
        runs, arts = samples(expiry=NOW - timedelta(seconds=1))
        o = m.evaluate(runs, arts, now=NOW)
        self.assertEqual(o["metadata_available"]["M5"], 0)
        self.assertEqual(o["metadata_available"]["M1"], 0)

    def test_now_is_expired(self):
        self.assertTrue(m._expired_at(NOW.isoformat(), NOW))
        self.assertFalse(m._expired_at((NOW + timedelta(seconds=1)).isoformat(), NOW))
        self.assertTrue(m._expired_at(None, NOW))
        self.assertTrue(m._expired_at("NOT_DATE", NOW))

    def test_ambiguous_duplicate_both_are_rejected(self):
        runs, arts = samples()
        arts[m.M1_ORIGINAL_RUN].append(dict(arts[m.M1_ORIGINAL_RUN][0]))
        o = m.evaluate(runs, arts, now=NOW)
        self.assertEqual(o["metadata_available"]["M1"], 32)
        self.assertEqual(len(o["m1_missing"]), 1)

    def test_sha_in_name_must_match_run_head(self):
        runs, arts = samples()
        arts[m.M5_NEW_RUN][0]["name"] = (
            arts[m.M5_NEW_RUN][0]["name"].rsplit("-", 1)[0] + "-" + "a" * 40
        )
        o = m.evaluate(runs, arts, now=NOW)
        self.assertEqual(o["metadata_available"]["M5"], 32)

    def test_zero_byte_file_rejected(self):
        runs, arts = samples()
        arts[m.M5_ORIGINAL_RUN][0]["size_in_bytes"] = 0
        o = m.evaluate(runs, arts, now=NOW)
        self.assertEqual(o["metadata_available"]["M5"], 32)

    def test_unexpected_naming_or_aggregate_ignored(self):
        runs, arts = samples()
        arts[m.M5_ORIGINAL_RUN].append({
            "name": "qore-cibo-market-atlas-10y-windowed-aggregate-2026",
            "id": 44, "size_in_bytes": 999, "expired": False,
            "expires_at": (NOW + timedelta(days=5)).isoformat(),
        })
        o = m.evaluate(runs, arts, now=NOW)
        self.assertEqual(o["metadata_available"]["M5"], 33)

    def test_nearest_expiry_is_not_90_days_from_current_time(self):
        runs, arts = samples()
        arts[m.M5_ORIGINAL_RUN][0]["expires_at"] = (NOW + timedelta(days=2)).isoformat()
        o = m.evaluate(runs, arts, now=NOW)
        self.assertEqual(o["nearest_expiry_utc"], (NOW + timedelta(days=2)).isoformat())

    def test_naive_now_rejected(self):
        runs, arts = samples()
        with self.assertRaisesRegex(ValueError, "TZ_AWARE"):
            m.evaluate(runs, arts, now=datetime(2026, 10, 12))

    def test_unsupported_repo_and_blank_token_rejected(self):
        with self.assertRaisesRegex(ValueError, "INVALID_GITHUB_REPO"):
            m._api("actions/runs/1", repo="not/a/repo", token="abc")
        with self.assertRaisesRegex(ValueError, "READ_TOKEN_REQUIRED"):
            m._api("actions/runs/1", repo="example/repo", token="")


if __name__ == "__main__":
    unittest.main()

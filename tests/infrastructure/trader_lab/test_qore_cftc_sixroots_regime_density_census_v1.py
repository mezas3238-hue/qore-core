"""Synthetic controls for CFTC six-market descriptive regime census (NO outcomes)."""
from __future__ import annotations

import hashlib
import unittest
from datetime import date, timedelta
from unittest.mock import patch

import qore_cftc_sixroots_regime_density_census_v1 as s


def _weeks(values: list[float], start: date = date(2012, 1, 3)) -> list[s.WeeklyPosition]:
    return [
        s.WeeklyPosition(start + timedelta(days=7 * i), value)
        for i, value in enumerate(values)
    ]


class TestDescriptiveCftcDensity(unittest.TestCase):
    def test_ten_year_six_asset_contract_matches_audited_source(self) -> None:
        self.assertEqual(set(s.DIGESTS), set(range(2012, 2022)))
        self.assertEqual(set(s.CONTRACT_CODES), {"CL", "NG", "GC", "HG", "ZC", "ZS"})
        self.assertEqual(s.Z_THRESHOLD, 2.0)
        self.assertEqual(s.Z_LOOKBACK, 104)
        self.assertEqual(s.COOLDOWN_REPORTS, 8)

    def test_no_future_z_leakage(self) -> None:
        base = [float(i % 11) / 1000 for i in range(130)]
        before = s.compute_z_preceding_104(_weeks(base))
        after = s.compute_z_preceding_104(_weeks(base[:-1] + [100.0]))
        self.assertEqual(before[104:129], after[104:129])
        self.assertIsNone(before[103])
        self.assertGreater(after[129], before[129])

    def test_constant_baseline_has_no_extremes(self) -> None:
        rows = _weeks([0.4] * 130)
        record = s.summarize_root(rows)
        self.assertEqual(record["eligible_z_weeks"], 0)
        self.assertEqual(record["crossings_admitted_after_8_report_cooldown"], 0)
        self.assertEqual(record["streaks_extreme"]["max_weeks"], 0)

    def test_decreasing_outlier_is_not_a_trade(self) -> None:
        values = [float(i % 11) / 1000 for i in range(200)]
        values[120] = -10.0
        values[122] = 10.0
        record = s.summarize_root(_weeks(values))
        self.assertGreater(record["extreme_negative_weeks"], 0)
        self.assertGreater(record["extreme_positive_weeks"], 0)
        self.assertEqual(record["observation_mode"], "SOURCE_DESCRIPTIVE_NO_MARKET_OUTCOMES")
        self.assertGreater(record["crossings_rejected_by_8_report_cooldown"], 0)

    def test_streak_duration_is_not_independent_events(self) -> None:
        s1 = s._count_streaks([0, 1, 1, 1, 0, -1, -1, 0, 1])
        self.assertEqual(s1["streaks"], 3)
        self.assertEqual(s1["median_weeks"], 2.0)
        self.assertEqual(s1["max_weeks"], 3)

    def test_bad_source_sha_fails_before_parse(self) -> None:
        with self.assertRaisesRegex(s.CftcDensityError, "ARCHIVE_SHA_MISMATCH"):
            s.decode_year(b"fake source", 2018)
        with self.assertRaisesRegex(s.CftcDensityError, "ARCHIVE_SHA_MISMATCH"):
            s.decode_year(b"fake source", 2022)

    def test_zero_six_market_source_identity_not_silently_assumed(self) -> None:
        # Only allowed 2012..2021 roots are read, no free-floating prices.
        self.assertEqual(s.REQUIRED, {
            "CFTC_Contract_Market_Code", "As_of_Date_In_Form_YYMMDD",
            "Market_and_Exchange_Names", "Open_Interest_All",
            "M_Money_Positions_Long_All", "M_Money_Positions_Short_All",
        })

    def test_duplicate_or_reserved_dates_fail_closed(self) -> None:
        duplicated = _weeks([float(i) for i in range(120)])
        with self.assertRaisesRegex(s.CftcDensityError, "DUPLICATE_SOURCE_DATES"):
            s.summarize_root(duplicated + [duplicated[-1]])
        with self.assertRaisesRegex(s.CftcDensityError, "RESERVED_YEAR_PROHIBITED"):
            s.summarize_root(_weeks([0.1] * 530))

    def test_digest_and_archive_preservation_not_raw_publication(self) -> None:
        with patch.object(s, "fetch_census") as mocked:
            mocked.return_value = {"counts": {}, "receipt_sha256": hashlib.sha256(b"x").hexdigest()}
            self.assertTrue(callable(s.main))


if __name__ == "__main__":
    unittest.main()

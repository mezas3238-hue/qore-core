"""Gate B census: synthetic coverage tests only (no strategy/backtest)."""
import unittest
from datetime import UTC, datetime, timedelta

from qore.infrastructure.trader_lab.qore_london_lona_data_census_gate_b_v1 import (
    bucket_start, ny_h4_anchor, ny_h4_expected_minutes, summarize_coverage,
)


class CensusGateBTests(unittest.TestCase):
    def test_bin_utc_boundaries_d1_h4_m15(self):
        moment = datetime(2026, 3, 8, 9, 17, tzinfo=UTC)
        self.assertEqual(bucket_start(moment, 15).isoformat(), "2026-03-08T09:15:00+00:00")
        self.assertEqual(bucket_start(moment, 240).isoformat(), "2026-03-08T08:00:00+00:00")
        self.assertEqual(bucket_start(moment, 1440).isoformat(), "2026-03-08T00:00:00+00:00")

    def test_complete_m15_from_exactly_15_native_minutes(self):
        start = datetime(2026, 10, 6, 8, 0, tzinfo=UTC)
        data = [start + timedelta(minutes=i) for i in range(15)]
        output = summarize_coverage(data)
        self.assertEqual(output["retained_m1_in_window"], 15)
        self.assertEqual(output["utc_bins"]["M15_UTC"]["complete_buckets"], 1)
        self.assertEqual(output["utc_bins"]["H4_UTC"]["complete_buckets"], 0)
        self.assertEqual(output["utc_bins"]["H4_UTC"]["partial_buckets"], 1)
        self.assertEqual(output["utc_bins"]["D1_UTC"]["partial_buckets"], 1)

    def test_partial_window_not_forward_filled(self):
        start = datetime(2026, 10, 6, 8, 0, tzinfo=UTC)
        data = [start + timedelta(minutes=i) for i in range(15) if i != 4]
        output = summarize_coverage(data)
        self.assertEqual(output["utc_bins"]["M15_UTC"]["partial_buckets"], 1)
        self.assertEqual(output["utc_bins"]["M15_UTC"]["complete_buckets"], 0)
        self.assertEqual(output["discontinuity_events_including_weekends_and_holidays"], 1)

    def test_two_M15_bars_with_one_incomplete(self):
        start = datetime(2026, 10, 6, 8, 0, tzinfo=UTC)
        data = [start + timedelta(minutes=i) for i in range(30) if i != 20]
        output = summarize_coverage(data)
        self.assertEqual(output["utc_bins"]["M15_UTC"]["complete_buckets"], 1)
        self.assertEqual(output["utc_bins"]["M15_UTC"]["partial_buckets"], 1)

    def test_complete_H4_240_native_minutes(self):
        start = datetime(2026, 10, 6, 8, 0, tzinfo=UTC)
        output = summarize_coverage(start + timedelta(minutes=i) for i in range(240))
        self.assertEqual(output["utc_bins"]["H4_UTC"]["complete_buckets"], 1)
        self.assertEqual(output["utc_bins"]["M15_UTC"]["complete_buckets"], 16)

    def test_empty_has_no_completeness_claim(self):
        result = summarize_coverage(())
        self.assertIsNone(result["utc_bins"]["M15_UTC"]["complete_fraction_of_observed_nonempty_bins"])

    def test_duplicate_minute_is_fatal(self):
        x = datetime(2026, 10, 6, 8, 0, tzinfo=UTC)
        with self.assertRaisesRegex(ValueError, "M1_NONMONOTONIC_OR_DUPLICATE"):
            summarize_coverage((x, x))

    def test_unordered_minute_is_fatal(self):
        x = datetime(2026, 10, 6, 8, 0, tzinfo=UTC)
        with self.assertRaisesRegex(ValueError, "M1_NONMONOTONIC_OR_DUPLICATE"):
            summarize_coverage((x + timedelta(minutes=1), x))

    def test_non_utc_is_fatal(self):
        from datetime import timezone
        x = datetime(2026, 10, 6, 8, tzinfo=timezone(timedelta(hours=-4)))
        with self.assertRaisesRegex(ValueError, "UTC_REQUIRED"):
            summarize_coverage((x,))

    def test_non_minute_grid_is_fatal(self):
        x = datetime(2026, 10, 6, 8, 0, 30, tzinfo=UTC)
        with self.assertRaisesRegex(ValueError, "M1_GRID_MISALIGNED"):
            summarize_coverage((x,))

    def test_dense_daily_missing_slots_are_observed_not_filled(self):
        # Fixed synthetic 1438/1440 day with two missing minute slots:
        start = datetime(2026, 10, 6, 0, 0, tzinfo=UTC)
        present = (start + timedelta(minutes=i) for i in range(1440) if i not in (1319, 1320))
        output = summarize_coverage(present)
        details = output["dense_utc_day_missing_minute_diagnostic"]
        self.assertEqual(details["days_meeting_threshold"], 1)
        self.assertEqual(details["days_with_1438_m1"], 1)
        self.assertEqual(details["days_with_1440_m1"], 0)
        self.assertEqual(details["missing_minutes_per_dense_day_counts"], {"2": 1})
        self.assertEqual(
            [x["utc_hhmm"] for x in details["most_frequent_missing_utc_minute_slots"]],
            ["21:59", "22:00"])
        self.assertTrue(details["missing_minute_cause_unclassified"])
        self.assertTrue(details["no_forward_fill"])

    def test_sparse_partial_daily_does_not_enter_dense_classification(self):
        start = datetime(2026, 10, 6, 0, 0, tzinfo=UTC)
        output = summarize_coverage(start + timedelta(minutes=i) for i in range(10))
        detail = output["dense_utc_day_missing_minute_diagnostic"]
        self.assertEqual(detail["days_meeting_threshold"], 0)
        self.assertEqual(detail["most_frequent_missing_utc_minute_slots"], [])

    def test_weekend_gap_is_not_called_feed_defect(self):
        friday = datetime(2026, 10, 9, 21, 59, tzinfo=UTC)
        sunday = datetime(2026, 10, 11, 21, 0, tzinfo=UTC)
        out = summarize_coverage((friday, sunday))
        self.assertEqual(out["discontinuity_events_including_weekends_and_holidays"], 1)
        self.assertTrue(out["market_closure_vs_feed_gap_unresolved"])


    def test_dst_spring_wall_clock_H4_span_is_three_hours(self):
        # March 8, 2026 NY springs from 01:59:59 to 03:00:00.
        now = datetime(2026, 3, 8, 7, 30, tzinfo=UTC)
        a = ny_h4_anchor(now, (2, 6, 10, 14, 18, 22))
        self.assertEqual(a.hour, 2)
        self.assertEqual(ny_h4_expected_minutes(a), 180)

    def test_dst_fall_wall_clock_H4_span_is_five_hours(self):
        # NY 22:00 previous day to 02:00 after fall-back spans 5 real hours.
        now = datetime(2026, 11, 1, 6, 30, tzinfo=UTC)
        a = ny_h4_anchor(now, (2, 6, 10, 14, 18, 22))
        self.assertEqual(a.hour, 22)
        self.assertEqual(ny_h4_expected_minutes(a), 300)

    def test_competing_NY_H4_clocks_are_only_hypotheses(self):
        first = datetime(2026, 10, 6, 8, 0, tzinfo=UTC)
        counts = summarize_coverage(first + timedelta(minutes=k) for k in range(60))
        self.assertEqual(set(counts["ny_h4_hypothesis_bins"]),
                         {"H4_NY_22_02_06_HYPOTHESIS", "H4_NY_01_05_09_HYPOTHESIS"})
        self.assertTrue(all(x["not_an_author_clock_certification"]
                            for x in counts["ny_h4_hypothesis_bins"].values()))

    def test_no_fill_authorization_flag_in_bin_schema(self):
        x = datetime(2026, 10, 6, 8, 0, tzinfo=UTC)
        out = summarize_coverage((x,))
        self.assertTrue(out["utc_bins"]["H4_UTC"]["market_closed_or_empty_calendar_bins_not_assessed"])


if __name__ == "__main__":
    unittest.main()

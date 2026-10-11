"""No-data LON-A research-observer fixtures: NEVER validate an author-exact trade."""
import unittest
from dataclasses import replace
from datetime import datetime, timedelta, timezone

from qore.infrastructure.trader_lab.qore_london_lona_m15_cisd_sequence_observer_v1 import (
    Candle, observe_sequences,
)

START = datetime(2026, 10, 10, 8, tzinfo=timezone.utc)
DECISION = "2026-10-10T10:00:00Z"


def candle(index, o, h, l, c, *, symbol="EURUSD", provider="SYNTHETIC", known=None):
    start = START + timedelta(minutes=15 * index)
    end = start + timedelta(minutes=15)
    return Candle(
        symbol=symbol, provider_id=provider, bar_open_utc=start.isoformat(),
        bar_close_utc=end.isoformat(), first_known_utc=known or
        (end + timedelta(seconds=1)).isoformat(),
        open=str(o), high=str(h), low=str(l), close=str(c),
    )


UP = (
    candle(0, "1.1000", "1.1002", "1.0992", "1.0995"),
    candle(1, "1.0995", "1.0997", "1.0988", "1.0990"),
    candle(2, "1.0990", "1.1003", "1.0989", "1.1001"),
)
DOWN = (
    candle(0, "1.1000", "1.1010", "1.0998", "1.1005"),
    candle(1, "1.1005", "1.1013", "1.1003", "1.1010"),
    candle(2, "1.1010", "1.1011", "1.0996", "1.0999"),
)


def observe(bars=UP, *, direction="BULLISH", at=DECISION):
    return observe_sequences(bars=tuple(bars), decision_at_utc=at, direction=direction)


class CISDObserverTests(unittest.TestCase):
    def test_bullish_first_open_and_earliest_close(self):
        result = observe()
        self.assertEqual(result["status"], "OBSERVATIONAL_ONLY")
        self.assertEqual(len(result["schematic_candidates"]), 1)
        x = result["schematic_candidates"][0]
        self.assertEqual(x["first_opposing_open_price"], "1.1000")
        self.assertEqual(x["series_length_observed_not_author_threshold"], 2)
        self.assertEqual(x["raw_series_extreme_not_protected_swing"], "1.0988")
        self.assertEqual(x["cross_bar_close_utc"], UP[2].bar_close_utc)
        self.assertFalse(x["valid_protected_swing"])
        self.assertIsNone(x["fill_price"])

    def test_bearish_sequence_reference(self):
        result = observe(DOWN, direction="BEARISH")
        self.assertEqual(len(result["schematic_candidates"]), 1)
        self.assertEqual(result["schematic_candidates"][0]["first_opposing_open_price"], "1.1000")

    def test_no_close_through_not_cisd(self):
        bars = UP[:2] + (candle(2, "1.0990", "1.1003", "1.0989", "1.0999"),)
        self.assertEqual(observe(bars)["schematic_candidates"], [])

    def test_equal_price_not_cross(self):
        bars = UP[:2] + (candle(2, "1.0990", "1.1003", "1.0989", "1.1000"),)
        self.assertEqual(observe(bars)["schematic_candidates"], [])

    def test_multiple_candidate_series_no_auto_selection(self):
        bars = (
            candle(0, "1.1000", "1.1001", "1.0987", "1.0990"),
            candle(1, "1.0990", "1.0995", "1.0988", "1.0993"),
            candle(2, "1.0993", "1.0994", "1.0981", "1.0988"),
            candle(3, "1.0988", "1.1007", "1.0987", "1.1005"),
        )
        result = observe(bars)
        self.assertEqual(len(result["schematic_candidates"]), 2)
        self.assertEqual(result["ambiguous_same_bar_candidate_count"], 2)
        self.assertTrue(all(x["multiple_series_cross_same_bar"] for x in result["schematic_candidates"]))
        self.assertFalse(result["entry_authorized"])

    def test_new_extreme_after_sequence_is_explicit_uncertainty(self):
        bars = UP[:2] + (
            candle(2, "1.0990", "1.0996", "1.0980", "1.0993"),
            candle(3, "1.0993", "1.1004", "1.0992", "1.1002"),
        )
        self.assertTrue(observe(bars)["schematic_candidates"][0]["post_series_extreme_worse_before_cross"])

    def test_future_append_does_not_rewrite_past(self):
        prior = observe(UP, at="2026-10-10T08:45:01Z")
        future = candle(3, "1.1001", "1.1006", "1.1000", "1.1003")
        combined = observe(UP + (future,), at="2026-10-10T08:45:01Z")
        self.assertEqual(prior["schematic_candidates"], combined["schematic_candidates"])
        self.assertEqual(combined["future_bars_ignored"], 1)

    def test_future_bar_with_past_timestamp_but_late_delivery_ignored(self):
        late = replace(UP[1], first_known_utc="2026-10-10T12:00:00Z")
        output = observe((UP[0], late), at="2026-10-10T09:00:00Z")
        self.assertEqual(output["visible_bars"], 1)
        self.assertEqual(output["future_bars_ignored"], 1)

    def test_gap_fails_closed(self):
        self.assertIn("M15_GAP_NOT_BACKFILLED", observe((UP[0], UP[2]))["blockers"])

    def test_overlap_fails_closed(self):
        self.assertIn("DUPLICATE_OR_OVERLAPPING_BARS", observe((UP[0], UP[0]))["blockers"])

    def test_out_of_order_fails_closed(self):
        self.assertIn("DUPLICATE_OR_OVERLAPPING_BARS", observe((UP[1], UP[0]))["blockers"])

    def test_cross_symbol_fails_closed(self):
        other = replace(UP[1], symbol="GBPUSD")
        self.assertIn("CROSS_SYMBOL_BAR_MIX", observe((UP[0], other, UP[2]))["blockers"])

    def test_cross_provider_fails_closed(self):
        other = replace(UP[1], provider_id="OTHER")
        self.assertIn("CROSS_PROVIDER_BAR_MIX", observe((UP[0], other, UP[2]))["blockers"])

    def test_invalid_ohlc_fails_closed(self):
        broken = replace(UP[1], high="1.0000")
        self.assertTrue(any("INVALID_OHLC_GEOMETRY" in x for x in observe((UP[0], broken))["blockers"]))

    def test_known_before_close_fails_closed(self):
        broken = replace(UP[1], first_known_utc="2026-10-10T08:20:00Z")
        self.assertTrue(any("BAR_DURATION_OR_FUTURE_CLOSE_LEAK" in x
                            for x in observe((UP[0], broken), at="2026-10-10T08:46:00Z")["blockers"]))

    def test_naive_time_fails_closed(self):
        with self.assertRaisesRegex(ValueError, "EXPLICIT_UTC_REQUIRED"):
            observe(at="2026-10-10T08:45:01")

    def test_non_m15_grid_fails_closed(self):
        broken = replace(UP[0], bar_open_utc="2026-10-10T08:01:00Z",
                         bar_close_utc="2026-10-10T08:16:00Z",
                         first_known_utc="2026-10-10T08:16:01Z")
        self.assertTrue(any("M15_GRID_MISALIGNED" in x for x in observe((broken,))["blockers"]))

    def test_nondecimal_and_nan_prices_fail_closed(self):
        for value in ("NaN", "Infinity", "-1", "not a number"):
            with self.subTest(value=value):
                broken = replace(UP[0], close=value)
                self.assertEqual(observe((broken,))["status"], "BLOCKED_INPUT")

    def test_doji_ends_run_without_fabricating_opposing_candle(self):
        bars = (
            UP[0],
            candle(1, "1.0995", "1.0997", "1.0990", "1.0995"),
            candle(2, "1.0995", "1.1003", "1.0990", "1.1001"),
        )
        result = observe(bars)
        self.assertEqual(result["schematic_candidates"][0]["series_length_observed_not_author_threshold"], 1)

    def test_all_cases_never_authorize_live_or_net_replay(self):
        for result in (observe(), observe(DOWN, direction="BEARISH"),
                       observe((UP[0], UP[2]))):
            for key in ("author_exact", "protected_swing_certified",
                        "entry_authorized", "economic_replay_authorized"):
                self.assertFalse(result[key])

    def test_wrong_direction_fails(self):
        with self.assertRaisesRegex(ValueError, "DIRECTION_MUST_BE_EXPLICIT"):
            observe(direction="UNKNOWN")


if __name__ == "__main__":
    unittest.main()

"""Causal synthetic fixtures for R4-A M5/M15 swing and MSS research primitives.

No real-market performance, Pine event parity, provider live execution or capital.
"""
from __future__ import annotations

import unittest
from datetime import UTC, datetime, timedelta

from research.crt_r4a_holdout.pine_swing_primitives import (
    Bar,
    M5Swings,
    M15Close,
    M15Swings,
    Pivot,
    SwingSnapshot,
    freeze_pre_sweep,
    mss5_cross,
    mss15_cross,
)

T = datetime(2024, 1, 2, tzinfo=UTC)


def bar(mins: int, hi: float, low: float = 1, close: float = 2) -> Bar:
    return Bar(T + timedelta(minutes=mins), hi, low, close)


def pivot(kind: str = "HIGH", level: float = 10) -> Pivot:
    return Pivot(
        kind, level, T, T + timedelta(minutes=25), T
    )


def m15(mins: int, prev: float, close: float) -> M15Close:
    return M15Close(
        T + timedelta(minutes=mins - 15),
        T + timedelta(minutes=mins), 12, 1, close, prev, True, 0
    )


class CausalM5(unittest.TestCase):
    def test_01_swing_input_bounds(self) -> None:
        for left, right in ((0, 2), (2, 0), (8, 1), (1, 8)):
            with self.assertRaises(ValueError):
                M5Swings(left, right)

    def test_02_bar_requires_timezone_and_valid_ohlc(self) -> None:
        with self.assertRaises(ValueError):
            Bar(datetime(2024, 1, 2), 3, 1, 2)
        with self.assertRaises(ValueError):
            Bar(T, 1, 2, 2)
        with self.assertRaises(ValueError):
            Bar(T, 3, 1, 4)

    def test_03_pivot_needs_two_right_and_two_left_bars(self) -> None:
        m = M5Swings(2, 2)
        highs = [3, 4, 10, 5, 4]
        for i, h in enumerate(highs):
            before, _ = m.before_closed_bar(bar(i * 5, h))
            self.assertIsNone(before.high)
            m.finish_bar(bar(i * 5, h))
        s, continuity = m.before_closed_bar(bar(25, 4))
        self.assertTrue(continuity)
        self.assertEqual(s.high.level, 10)  # type: ignore[union-attr]
        self.assertEqual(s.high.pivot_at, T + timedelta(minutes=10))  # type: ignore[union-attr]
        self.assertEqual(s.high.confirmed_at, T + timedelta(minutes=25))  # type: ignore[union-attr]

    def test_04_sweep_cannot_see_pivot_confirmed_on_same_bar(self) -> None:
        m = M5Swings(2, 2)
        for i, h in enumerate((1, 2, 10, 4)):
            b = bar(i * 5, h)
            m.before_closed_bar(b)
            m.finish_bar(b)
        fifth = bar(20, 3)
        before, _ = m.before_closed_bar(fifth)
        self.assertIsNone(freeze_pre_sweep(before, 1, fifth.opened_at))
        m.finish_bar(fifth)
        sixth = bar(25, 4)
        after, _ = m.before_closed_bar(sixth)
        self.assertIsNotNone(freeze_pre_sweep(after, 1, sixth.opened_at))

    def test_05_gap_clears_segment_and_stale_m5_high(self) -> None:
        m = M5Swings()
        for i, h in enumerate((1, 2, 10, 4, 3)):
            b = bar(i * 5, h)
            m.before_closed_bar(b)
            m.finish_bar(b)
        before, valid = m.before_closed_bar(bar(45, 4))
        self.assertFalse(valid)
        self.assertIsNone(before.high)
        self.assertEqual(before.segment_at, T + timedelta(minutes=45))

    def test_06_equal_highs_rejected_as_unproven_tie_semantics(self) -> None:
        m = M5Swings()
        for i, h in enumerate((1, 2, 10, 10, 1)):
            b = bar(i * 5, h)
            m.before_closed_bar(b)
            m.finish_bar(b)
        before, _ = m.before_closed_bar(bar(25, 1))
        self.assertIsNone(before.high)

    def test_07_pre_sweep_pivot_age_limit(self) -> None:
        p = pivot()
        snap = SwingSnapshot(p, None, T)
        self.assertIsNotNone(
            freeze_pre_sweep(snap, 1, T + timedelta(minutes=720))
        )
        self.assertIsNone(
            freeze_pre_sweep(snap, 1, T + timedelta(minutes=721))
        )

    def test_08_pre_sweep_pivot_direction_matters(self) -> None:
        s = SwingSnapshot(pivot(), None, T)
        self.assertIsNone(freeze_pre_sweep(s, -1, T + timedelta(minutes=30)))
        with self.assertRaises(ValueError):
            freeze_pre_sweep(s, 0, T + timedelta(minutes=30))

    def test_09_segment_guard_disallows_old_pivot(self) -> None:
        s = SwingSnapshot(pivot(), None, T + timedelta(hours=1))
        self.assertIsNone(freeze_pre_sweep(s, 1, T + timedelta(hours=1, minutes=5)))

    def test_10_mss5_long_cross_after_sweep(self) -> None:
        p = pivot()
        self.assertTrue(mss5_cross(
            previous_close=10, current=bar(30, 12, 8, 11),
            previous_continuous=True, direction=1, pivot=p,
            sweep_closed_at=T + timedelta(minutes=30),
            latest_closed_at=T + timedelta(minutes=40)
        ))

    def test_11_mss5_reject_cross_during_sweep_candle(self) -> None:
        self.assertFalse(mss5_cross(
            previous_close=9, current=bar(25, 12, 8, 11),
            previous_continuous=True, direction=1, pivot=pivot(),
            sweep_closed_at=T + timedelta(minutes=30),
            latest_closed_at=T + timedelta(minutes=40)
        ))

    def test_12_mss5_reject_gap_or_missing_previous(self) -> None:
        for previous, continuous in ((9, False), (None, True)):
            self.assertFalse(mss5_cross(
                previous_close=previous, current=bar(30, 12, 8, 11),
                previous_continuous=continuous, direction=1, pivot=pivot(),
                sweep_closed_at=T + timedelta(minutes=30),
                latest_closed_at=T + timedelta(minutes=40)
            ))

    def test_13_mss5_short_causal_downcross(self) -> None:
        self.assertTrue(mss5_cross(
            previous_close=10, current=bar(35, 12, 8, 9),
            previous_continuous=True, direction=-1, pivot=pivot("LOW"),
            sweep_closed_at=T + timedelta(minutes=30),
            latest_closed_at=T + timedelta(minutes=40),
        ))

    def test_14_mss5_no_cross_on_exact_equal_close(self) -> None:
        self.assertFalse(mss5_cross(
            previous_close=9, current=bar(30, 12, 8, 10),
            previous_continuous=True, direction=1, pivot=pivot(),
            sweep_closed_at=T + timedelta(minutes=30),
            latest_closed_at=T + timedelta(minutes=40),
        ))


class NativeM15(unittest.TestCase):
    def test_15_m15_params_and_phase_bounds(self) -> None:
        for phase in (-1, 5):
            with self.assertRaises(ValueError):
                M15Swings(source_phase_min=phase)
        for left, right in ((0, 2), (2, 8)):
            with self.assertRaises(ValueError):
                M15Swings(left, right)

    def test_16_m15_requires_all_three_consecutive_m5(self) -> None:
        s = M15Swings()
        for i in range(3):
            self.assertIsNone(s.on_closed_m5(bar(i * 5, 4)))
        closed = s.on_closed_m5(bar(15, 4))
        self.assertIsNotNone(closed)
        self.assertEqual(closed.closed_at, T + timedelta(minutes=15))  # type: ignore[union-attr]
        self.assertFalse(closed.previous_continuous)  # type: ignore[union-attr]

    def test_17_m15_one_missing_bar_resets_no_forged_close(self) -> None:
        s = M15Swings()
        s.on_closed_m5(bar(0, 4))
        s.on_closed_m5(bar(5, 5))
        self.assertIsNone(s.on_closed_m5(bar(15, 4)))
        self.assertIsNone(s.on_closed_m5(bar(30, 4)))

    def test_18_m15_provider_phase_2_native_alignment(self) -> None:
        s = M15Swings(source_phase_min=2)
        for mins in (2, 7, 12):
            self.assertIsNone(s.on_closed_m5(bar(mins, 5)))
        closed = s.on_closed_m5(bar(17, 5))
        self.assertEqual(closed.closed_at, T + timedelta(minutes=17))  # type: ignore[union-attr]
        self.assertEqual(closed.source_phase_min, 2)  # type: ignore[union-attr]

    def test_19_m15_wrong_source_phase_cannot_silently_normalize(self) -> None:
        s = M15Swings(source_phase_min=2)
        with self.assertRaises(ValueError):
            s.on_closed_m5(bar(0, 4))

    def test_20_m15_pivot_confirmed_only_after_two_right_m15(self) -> None:
        s = M15Swings()
        # 5 complete M15 candles: high at third, confirmed only when
        # the fifth M15 is finalized by M5 starting at minute 75.
        highs = (3, 4, 10, 5, 4, 3)
        for interval in range(6):
            for offset in (0, 5, 10):
                s.on_closed_m5(bar(interval * 15 + offset, highs[interval]))
            # The next iteration's first M5 will finalize this block.
            if interval < 5:
                self.assertIsNone(s.snapshot().high)  # type: ignore[union-attr]
        s.on_closed_m5(bar(90, 3))
        self.assertEqual(s.snapshot().high.level, 10)  # type: ignore[union-attr]
        self.assertEqual(s.snapshot().high.pivot_at, T + timedelta(minutes=30))  # type: ignore[union-attr]
        self.assertEqual(s.snapshot().high.confirmed_at, T + timedelta(minutes=75))  # type: ignore[union-attr]

    def test_21_m15_prev_immediately_contiguous_close(self) -> None:
        s = M15Swings()
        for i in range(7):
            closed = s.on_closed_m5(bar(i * 5, 6))
            if i == 6:
                self.assertTrue(closed.previous_continuous)  # type: ignore[union-attr]
                self.assertEqual(closed.previous_close, 2)  # type: ignore[union-attr]

    def test_22_mss15_strict_cross_after_sweep(self) -> None:
        self.assertTrue(mss15_cross(
            m15(45, 10, 11), direction=1, pivot=pivot(),
            sweep_closed_at=T + timedelta(minutes=30),
            latest_closed_at=T + timedelta(minutes=60),
        ))

    def test_23_mss15_reject_old_or_noncontiguous(self) -> None:
        closed = m15(45, 10, 11)
        bad = M15Close(
            closed.start_at, closed.closed_at, closed.high, closed.low,
            closed.close, closed.previous_close, False, closed.source_phase_min
        )
        self.assertFalse(mss15_cross(
            bad, direction=1, pivot=pivot(),
            sweep_closed_at=T + timedelta(minutes=30),
            latest_closed_at=T + timedelta(minutes=60),
        ))
        self.assertFalse(mss15_cross(
            closed, direction=1, pivot=pivot(),
            sweep_closed_at=T + timedelta(minutes=45),
            latest_closed_at=T + timedelta(minutes=60),
        ))

    def test_24_mss15_reject_phase_mismatch(self) -> None:
        closed = m15(45, 10, 11)
        bad = M15Close(
            closed.start_at, closed.closed_at, closed.high, closed.low,
            closed.close, closed.previous_close, True, 2
        )
        self.assertFalse(mss15_cross(
            bad, direction=1, pivot=pivot(),
            sweep_closed_at=T + timedelta(minutes=30),
            latest_closed_at=T + timedelta(minutes=60),
        ))

    def test_25_mss15_short_bearish_cross(self) -> None:
        self.assertTrue(mss15_cross(
            m15(45, 11, 9), direction=-1, pivot=pivot("LOW"),
            sweep_closed_at=T + timedelta(minutes=30),
            latest_closed_at=T + timedelta(minutes=60),
        ))


if __name__ == "__main__":
    unittest.main(verbosity=2)

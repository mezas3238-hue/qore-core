"""No-PnL causal H4 R4-A structural boundary and 6 NY clocks tests."""
from __future__ import annotations

import unittest
from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo

from research.crt_r4a_holdout.pine_h4_geometry import (
    C1_CLOCKS,
    ClosedH4,
    c1_allowed,
    proxy_old_c1_allowed,
    true_three_c,
    two_c_return,
)

NY = ZoneInfo("America/New_York")
DAY = datetime(2024, 2, 1, tzinfo=NY)


def h4(h: int, hi: float, lo: float, close: float) -> ClosedH4:
    st = DAY + timedelta(hours=h)
    return ClosedH4(st, st + timedelta(hours=4), hi, lo, close)


class R4AH4SourceContract(unittest.TestCase):
    def test_01_six_forex_clocks_exact(self) -> None:
        self.assertEqual(C1_CLOCKS["forex"], frozenset((1, 5, 9, 13, 17, 21)))

    def test_02_six_index_clocks_exact(self) -> None:
        self.assertEqual(C1_CLOCKS["index"], frozenset((2, 6, 10, 14, 18, 22)))

    def test_03_full_vs_legacy_three_clocks(self) -> None:
        n = 0
        old = 0
        for hour in range(24):
            instant = DAY.replace(hour=hour)
            n += c1_allowed(instant, "forex")
            old += proxy_old_c1_allowed(instant, "forex")
        self.assertEqual((n, old), (6, 3))

    def test_04_index_full_vs_legacy_three_clocks(self) -> None:
        full = sum(
            c1_allowed(DAY.replace(hour=h), "index") for h in range(24)
        )
        old = sum(
            proxy_old_c1_allowed(DAY.replace(hour=h), "index")
            for h in range(24)
        )
        self.assertEqual((full, old), (6, 3))

    def test_05_btc_original_is_six_not_three(self) -> None:
        self.assertEqual(C1_CLOCKS["btc"], C1_CLOCKS["forex"])

    def test_06_dst_utc_to_ny_daytime_gate(self) -> None:
        ny = datetime(2024, 7, 1, 13, 0, tzinfo=NY)
        self.assertTrue(c1_allowed(ny.astimezone(UTC), "forex"))
        self.assertFalse(proxy_old_c1_allowed(ny.astimezone(UTC), "forex"))

    def test_07_wrong_family_and_naive_clock_blocked(self) -> None:
        with self.assertRaises(ValueError):
            c1_allowed(DAY, "commodities")
        with self.assertRaises(ValueError):
            c1_allowed(datetime(2024, 1, 1), "forex")

    def test_08_one_strict_low_sweep_c2_return(self) -> None:
        self.assertEqual(two_c_return(
            h4(1, 110, 90, 100), h4(5, 108, 88, 100), "forex"
        ), 1)

    def test_09_one_strict_high_sweep_c2_return(self) -> None:
        self.assertEqual(two_c_return(
            h4(1, 110, 90, 100), h4(5, 112, 91, 100), "forex"
        ), -1)

    def test_10_c2_double_sweep_no_signal(self) -> None:
        self.assertEqual(two_c_return(
            h4(1, 110, 90, 100), h4(5, 112, 88, 101), "forex"
        ), 0)

    def test_11_no_strict_sweep_no_signal(self) -> None:
        self.assertEqual(two_c_return(
            h4(1, 110, 90, 100), h4(5, 110, 90, 100), "forex"
        ), 0)

    def test_12_c2_expansion_rejected(self) -> None:
        self.assertEqual(two_c_return(
            h4(1, 110, 90, 100), h4(5, 109, 88, 89), "forex"
        ), 0)

    def test_13_legacy_omitted_13h_c1_now_admitted(self) -> None:
        self.assertEqual(two_c_return(
            h4(13, 110, 90, 100), h4(17, 109, 88, 97), "forex"
        ), 1)

    def test_14_true3c_low_sweep(self) -> None:
        self.assertEqual(true_three_c(
            h4(1, 110, 90, 100),
            h4(5, 108, 92, 101),
            h4(9, 109, 89, 99),
            "forex"
        ), 1)

    def test_15_true3c_high_sweep(self) -> None:
        self.assertEqual(true_three_c(
            h4(1, 110, 90, 100),
            h4(5, 108, 92, 101),
            h4(9, 111, 91, 99),
            "forex"
        ), -1)

    def test_16_true3c_equal_boundary_touch_not_sweep(self) -> None:
        self.assertEqual(true_three_c(
            h4(1, 110, 90, 100),
            h4(5, 108, 92, 101),
            h4(9, 110, 90, 99),
            "forex"
        ), 0)

    def test_17_true3c_c2_sweep_disqualifies(self) -> None:
        self.assertEqual(true_three_c(
            h4(1, 110, 90, 100),
            h4(5, 111, 92, 101),
            h4(9, 109, 89, 99),
            "forex"
        ), 0)

    def test_18_true3c_c3_closes_outside_c1(self) -> None:
        self.assertEqual(true_three_c(
            h4(1, 110, 90, 100),
            h4(5, 108, 92, 101),
            h4(9, 109, 88, 88),
            "forex"
        ), 0)

    def test_19_c3_dual_sweep_disqualifies(self) -> None:
        self.assertEqual(true_three_c(
            h4(1, 110, 90, 100),
            h4(5, 108, 92, 101),
            h4(9, 112, 88, 100),
            "forex"
        ), 0)

    def test_20_true3c_at_omitted_09h_ny_c1_is_valid(self) -> None:
        self.assertEqual(true_three_c(
            h4(9, 110, 90, 100),
            h4(13, 108, 92, 101),
            h4(17, 109, 88, 101),
            "forex"
        ), 1)

    def test_21_c1_with_invalid_h4_data_blocked(self) -> None:
        c1 = h4(1, 110, 90, 100)
        invalid = ClosedH4(
            c1.opened_at, c1.closed_at, c1.high, c1.low,
            c1.close, False
        )
        self.assertEqual(two_c_return(invalid, h4(5, 109, 88, 100), "forex"), 0)

    def test_22_nonconsecutive_c1_c2_c3_blocked(self) -> None:
        self.assertEqual(true_three_c(
            h4(1, 110, 90, 100),
            h4(9, 108, 92, 101),
            h4(13, 109, 88, 101),
            "forex"
        ), 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)

"""Boundary tests for independent Inside, Multi4, MultiN and M15 retest QA."""
from __future__ import annotations

import unittest
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from research.crt_r4a_holdout.pine_h4_geometry import ClosedH4
from research.crt_r4a_holdout.pine_swing_primitives import M15Close
from research.crt_r4a_holdout.secondary_family_geometry import (
    RetestSource,
    inside_return,
    multi4,
    multi_n,
    retest_m15,
)

BASE = datetime(2024, 2, 1, 1, tzinfo=ZoneInfo("America/New_York"))


def h4(i: int, lo: float, hi: float, cl: float) -> ClosedH4:
    opened = BASE + timedelta(hours=4*i)
    return ClosedH4(opened, opened + timedelta(hours=4), hi, lo, cl)


def c1() -> ClosedH4:
    return h4(0, 100, 120, 110)


def m15closed(i: int, lo: float, hi: float, cl: float) -> M15Close:
    closed = BASE + timedelta(hours=4, minutes=15*i)
    return M15Close(
        closed - timedelta(minutes=15), closed, hi, lo, cl,
        109, True, 0
    )


def source(mss_at: datetime | None = None) -> RetestSource:
    return RetestSource(
        BASE, 1,
        mss_at or BASE + timedelta(hours=4),
        108, BASE + timedelta(hours=4)
    )


class InsideTests(unittest.TestCase):
    def test_01_bull_inside_return_independent_of_c1_sweep(self) -> None:
        r = inside_return(
            c1(), h4(1, 105, 115, 110),
            h4(2, 104, 114, 110), "forex"
        )
        self.assertEqual(r.direction, 1)  # type: ignore[union-attr]
        self.assertEqual(r.name, "INSIDE_RETURN")  # type: ignore[union-attr]
        self.assertIs(r.own_mss_ever_certified, False)  # type: ignore[union-attr]

    def test_02_bear_inside_return(self) -> None:
        r = inside_return(
            c1(), h4(1, 105, 115, 110),
            h4(2, 107, 117, 109), "forex"
        )
        self.assertEqual(r.direction, -1)  # type: ignore[union-attr]

    def test_03_c2_must_be_strict_inside(self) -> None:
        self.assertIsNone(inside_return(
            c1(), h4(1, 100, 115, 110), h4(2, 99, 114, 110),
            "forex"
        ))

    def test_04_double_sweep_is_ambiguous(self) -> None:
        self.assertIsNone(inside_return(
            c1(), h4(1, 105, 115, 110), h4(2, 104, 116, 110),
            "forex"
        ))

    def test_05_inside_continuation_outside_c2_rejected(self) -> None:
        self.assertIsNone(inside_return(
            c1(), h4(1, 105, 115, 110), h4(2, 104, 119, 118),
            "forex"
        ))

    def test_06_nonconsecutive_inside_h4_rejected(self) -> None:
        self.assertIsNone(inside_return(
            c1(), h4(1, 105, 115, 110), h4(3, 104, 114, 110),
            "forex"
        ))


class MultiTests(unittest.TestCase):
    def test_07_multi4_bull_geometry_four_closed(self) -> None:
        r = multi4(
            c1(), h4(1, 99, 119, 110), h4(2, 100, 118, 107),
            h4(3, 105, 120, 112), "forex"
        )
        self.assertEqual((r.name, r.direction), ("MULTI4", 1))  # type: ignore[union-attr]
        self.assertFalse(r.own_mss_ever_certified)  # type: ignore[union-attr]

    def test_08_multi4_bear_geometry(self) -> None:
        r = multi4(
            c1(), h4(1, 102, 121, 110), h4(2, 101, 122, 110),
            h4(3, 105, 118, 108), "forex"
        )
        self.assertEqual(r.direction, -1)  # type: ignore[union-attr]

    def test_09_multi4_nonconsecutive_disallowed(self) -> None:
        self.assertIsNone(multi4(
            c1(), h4(1, 99, 119, 110), h4(3, 100, 118, 107),
            h4(4, 105, 120, 112), "forex"
        ))

    def test_10_multi4_not_arbitrary_fewer_h4(self) -> None:
        self.assertIsNone(multi4(
            c1(), h4(1, 99, 119, 110), h4(2, 110, 119, 115),
            h4(3, 105, 120, 112), "forex"
        ))

    def test_11_multin_2_inside_plus_terminal(self) -> None:
        r = multi_n((
            c1(), h4(1, 105, 115, 110), h4(2, 104, 116, 109),
            h4(3, 99, 118, 108)
        ), "forex")
        self.assertEqual((r.name, r.direction), ("MULTI_N", 1))  # type: ignore[union-attr]

    def test_12_multin_5_inside_plus_terminal(self) -> None:
        bars = [c1()]
        bars.extend(h4(i, 105, 115, 110) for i in range(1, 6))
        bars.append(h4(6, 100, 121, 109))
        r = multi_n(tuple(bars), "forex")
        self.assertEqual(r.direction, -1)  # type: ignore[union-attr]

    def test_13_multin_wrong_consolidation_count_rejected(self) -> None:
        self.assertIsNone(multi_n((
            c1(), h4(1, 105, 115, 110), h4(2, 99, 118, 109)
        ), "forex"))

    def test_14_multin_terminal_dual_sweep_rejected(self) -> None:
        self.assertIsNone(multi_n((
            c1(), h4(1, 105, 115, 110), h4(2, 104, 116, 109),
            h4(3, 99, 121, 110)
        ), "forex"))

    def test_15_multin_terminal_outside_c1_rejected(self) -> None:
        self.assertIsNone(multi_n((
            c1(), h4(1, 105, 115, 110), h4(2, 104, 116, 109),
            h4(3, 99, 118, 99)
        ), "forex"))


class RetestTests(unittest.TestCase):
    def test_16_retest_closes_after_mss_with_own_c1(self) -> None:
        m15 = m15closed(2, 107, 115, 110)
        r = retest_m15(source(), m15, linked_c1_at=BASE)
        self.assertEqual((r.name, r.direction), ("M15_RETEST", 1))  # type: ignore[union-attr]

    def test_17_cannot_borrow_other_crt_c1(self) -> None:
        self.assertIsNone(retest_m15(
            source(), m15closed(2, 107, 115, 110),
            linked_c1_at=BASE + timedelta(hours=4),
        ))

    def test_18_no_retest_on_exact_mss_bar(self) -> None:
        self.assertIsNone(retest_m15(
            source(), m15closed(0, 107, 115, 110),
            linked_c1_at=BASE
        ))

    def test_19_no_retest_after_4_hours(self) -> None:
        self.assertIsNone(retest_m15(
            source(), m15closed(17, 107, 115, 110),
            linked_c1_at=BASE
        ))

    def test_20_no_m15_retest_without_contiguous_m15(self) -> None:
        old = m15closed(2, 107, 115, 110)
        broken = M15Close(
            old.start_at, old.closed_at, old.high, old.low,
            old.close, old.previous_close, False, old.source_phase_min
        )
        self.assertIsNone(retest_m15(
            source(), broken, linked_c1_at=BASE
        ))

    def test_21_no_retest_without_own_source_type(self) -> None:
        x = source()
        forged = RetestSource(
            x.c1_at, x.direction, x.own_mss15_at,
            x.own_mss15_pivot, x.parent_crt_ratified_at,
            "OTHER_FAMILY"
        )
        self.assertIsNone(retest_m15(
            forged, m15closed(2, 107, 115, 110),
            linked_c1_at=BASE
        ))

    def test_22_ratif_after_original_h4_if_retest_during_c2(self) -> None:
        x = RetestSource(
            BASE, 1, BASE + timedelta(minutes=30), 108,
            BASE + timedelta(hours=4)
        )
        m15 = M15Close(
            BASE + timedelta(minutes=30),
            BASE + timedelta(minutes=45),
            110, 107, 109, 107, True, 0
        )
        # M15 closes at NY 01:45, earlier than the H4 containing C1 ends.
        # Geometry may be observed; not legally tradable before parent closes.
        r = retest_m15(x, m15, linked_c1_at=BASE)
        self.assertIsNotNone(r)
        self.assertEqual(
            r.ratified_at, x.parent_crt_ratified_at  # type: ignore[union-attr]
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)

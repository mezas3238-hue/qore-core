"""No borrowed MSS and no execution, four independent closed-geometry lanes."""
from __future__ import annotations

import unittest
from dataclasses import dataclass
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from research.crt_r4a_holdout.pine_h4_geometry import ClosedH4
from research.crt_r4a_holdout.pine_swing_primitives import M15Close
from research.crt_r4a_holdout.secondary_family_observer import (
    SecondaryGeometryObserver,
)
from research.crt_r4a_holdout.seven_family_contract import Family

T = datetime(2024, 2, 1, 1, tzinfo=ZoneInfo("America/New_York"))


def h4(n: int, low: int, high: int, close: int) -> ClosedH4:
    opened = T + timedelta(hours=4 * n)
    return ClosedH4(opened, opened + timedelta(hours=4), high, low, close)


def seed() -> ClosedH4:
    return h4(0, 100, 120, 110)


@dataclass
class BaseMSS:
    identity: str = "EURUSD|2C|C1"
    model: str = "A_2C_MSS15"
    side: str = "LONG"
    c1_at: datetime = T
    mss_at: datetime = T + timedelta(hours=7, minutes=45)
    mss_pivot: float = 108
    ratified_at: datetime = T + timedelta(hours=8)


def retest_closed() -> M15Close:
    end = T + timedelta(hours=8, minutes=15)
    return M15Close(
        end - timedelta(minutes=15), end,
        112, 107, 109, 107, True, 0
    )


class SecondaryGeometryOnly(unittest.TestCase):
    def test_01_inside_return_observed_but_not_tradable(self) -> None:
        e = SecondaryGeometryObserver("forex")
        for c in (seed(), h4(1, 105, 115, 110), h4(2, 104, 114, 110)):
            e.on_closed_h4(c)
        a = e.readout()
        self.assertEqual(
            a["family_geometry_event_counts"][Family.INSIDE_RETURN.value], 1
        )
        self.assertIs(a["family_own_mss_state_machines_certified"], False)
        self.assertEqual(a["trades_executed"], 0)

    def test_02_multi4_own_geometry_observed(self) -> None:
        e = SecondaryGeometryObserver("forex")
        for c in (
            seed(), h4(1, 99, 119, 110), h4(2, 100, 118, 107),
            h4(3, 105, 120, 112)
        ):
            e.on_closed_h4(c)
        self.assertEqual(
            e.readout()["family_geometry_event_counts"][Family.MULTI4.value],
            1,
        )

    def test_03_multi_n_2_inside_bars_observed(self) -> None:
        e = SecondaryGeometryObserver("forex")
        for c in (
            seed(), h4(1, 105, 115, 110), h4(2, 104, 116, 109),
            h4(3, 99, 118, 108)
        ):
            e.on_closed_h4(c)
        self.assertEqual(
            e.readout()["family_geometry_event_counts"][Family.MULTIN.value],
            1
        )

    def test_04_geometry_never_claims_own_mss(self) -> None:
        e = SecondaryGeometryObserver("forex")
        for c in (seed(), h4(1, 105, 115, 110), h4(2, 104, 114, 110)):
            e.on_closed_h4(c)
        self.assertEqual(len(e.events), 1)
        self.assertIs(e.events[0].independently_mss_certified, False)

    def test_05_h4_gap_invalidates_context(self) -> None:
        e = SecondaryGeometryObserver("forex")
        e.on_closed_h4(seed())
        e.on_closed_h4(h4(1, 105, 115, 110))
        e.on_closed_h4(None)
        e.on_closed_h4(h4(2, 104, 114, 110))
        self.assertEqual(e.readout()["total_geometry_only_events"], 0)

    def test_06_retest_requires_same_2c_source_mss(self) -> None:
        e = SecondaryGeometryObserver("forex")
        e.on_m15_retest(retest_closed(), [BaseMSS()])
        self.assertEqual(
            e.readout()["family_geometry_event_counts"][Family.M15_RETEST.value],
            1
        )
        item = e.events[0]
        self.assertEqual(item.source_parent_id, "EURUSD|2C|C1")
        self.assertTrue(item.has_parent_owned_mss)
        self.assertIs(item.independently_mss_certified, False)

    def test_07_same_source_retest_only_once(self) -> None:
        e = SecondaryGeometryObserver("forex")
        e.on_m15_retest(retest_closed(), [BaseMSS()])
        e.on_m15_retest(retest_closed(), [BaseMSS()])
        self.assertEqual(len(e.events), 1)

    def test_08_retest_cannot_borrow_true3c_mss(self) -> None:
        e = SecondaryGeometryObserver("forex")
        foreign = BaseMSS(model="B_TRUE3C_MSS5")
        e.on_m15_retest(retest_closed(), [foreign])
        self.assertEqual(len(e.events), 0)

    def test_09_retest_after_4h_not_evidence(self) -> None:
        e = SecondaryGeometryObserver("forex")
        closed = retest_closed()
        end = closed.closed_at + timedelta(hours=5)
        late = M15Close(
            end - timedelta(minutes=15), end,
            112, 107, 109, 107, True, 0
        )
        e.on_m15_retest(late, [BaseMSS()])
        self.assertEqual(len(e.events), 0)

    def test_10_never_promote_secondary_geometry_to_trade(self) -> None:
        e = SecondaryGeometryObserver("forex")
        for c in (
            seed(), h4(1, 105, 115, 110), h4(2, 104, 116, 109),
            h4(3, 99, 118, 108)
        ):
            e.on_closed_h4(c)
        self.assertTrue(all(x.broker_orders_executed == 0 for x in e.events))
        self.assertTrue(all(not x.independently_mss_certified for x in e.events))

    def test_11_no_unknown_family(self) -> None:
        with self.assertRaises(ValueError):
            SecondaryGeometryObserver("unknown")


if __name__ == "__main__":
    unittest.main(verbosity=2)

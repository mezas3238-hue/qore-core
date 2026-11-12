"""Independent closed-M5 and own M15 MSS for Inside, Multi4, MultiN."""
from __future__ import annotations

import unittest
from dataclasses import dataclass
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from research.crt_r4a_holdout.pine_h4_geometry import ClosedH4
from research.crt_r4a_holdout.pine_swing_primitives import (
    M15Close,
    Pivot,
    SwingSnapshot,
)
from research.crt_r4a_holdout.secondary_family_mss import AuxiliaryOwnedMss
from research.crt_r4a_holdout.secondary_family_observer import SecondaryGeometryObserver
from research.crt_r4a_holdout.seven_family_contract import Family

T = datetime(2024, 2, 1, 1, tzinfo=ZoneInfo("America/New_York"))


def h4(i: int, lo: float, hi: float, close: float) -> ClosedH4:
    at = T + timedelta(hours=4*i)
    return ClosedH4(at, at + timedelta(hours=4), hi, lo, close)


@dataclass
class M5:
    opened_at: datetime
    high: float
    low: float
    close: float

    @property
    def end(self) -> datetime:
        return self.opened_at + timedelta(minutes=5)


def swing() -> SwingSnapshot:
    p5 = Pivot("HIGH", 108, T, T + timedelta(hours=1), T)
    return SwingSnapshot(p5, None, T)


def m15_cross(at: datetime) -> M15Close:
    return M15Close(
        at - timedelta(minutes=15), at, 111, 99, 109, 107, True, 0
    )


def sweep(
    model: AuxiliaryOwnedMss, *, start: datetime, low: float,
    high: float, before: SwingSnapshot | None = None
) -> None:
    s = before or swing()
    model.on_closed_m5(
        M5(start, high, low, 107),
        before5=s, before15=s, previous_close=107,
        previous_continuous=True
    )


class OwnedResearchMSS(unittest.TestCase):
    def test_01_inside_return_owned_mss15_emitted_only_on_terminal_h4(self) -> None:
        e = AuxiliaryOwnedMss("EURUSD", "forex")
        e.on_closed_h4(h4(0, 100, 120, 110))
        e.on_closed_h4(h4(1, 105, 115, 110))
        at = T + timedelta(hours=8, minutes=5)
        sweep(e, start=at, low=104, high=114)
        self.assertEqual(len(e.events), 0)
        e.on_closed_m15(m15_cross(T + timedelta(hours=8, minutes=30)))
        self.assertEqual(len(e.events), 0)
        e.on_closed_h4(h4(2, 104, 114, 110))
        self.assertEqual(len(e.events), 1)
        result = e.events[0]
        self.assertEqual(result.family, Family.INSIDE_RETURN)
        self.assertEqual(result.side, "LONG")
        self.assertLess(result.own_pivot_at, result.sweep_at)
        self.assertEqual(result.available_at, result.ratified_at)
        self.assertEqual(result.broker_orders_executed, 0)

    def test_02_inside_return_geometry_without_own_mss_blocked(self) -> None:
        e = AuxiliaryOwnedMss("EURUSD", "forex")
        e.on_closed_h4(h4(0, 100, 120, 110))
        e.on_closed_h4(h4(1, 105, 115, 110))
        sweep(
            e, start=T + timedelta(hours=8, minutes=5),
            low=104, high=114
        )
        e.on_closed_h4(h4(2, 104, 114, 110))
        self.assertEqual(len(e.events), 0)

    def test_03_inside_double_sweep_cannot_emit(self) -> None:
        e = AuxiliaryOwnedMss("EURUSD", "forex")
        e.on_closed_h4(h4(0, 100, 120, 110))
        e.on_closed_h4(h4(1, 105, 115, 110))
        sweep(
            e, start=T + timedelta(hours=8, minutes=5),
            low=104, high=114
        )
        sweep(
            e, start=T + timedelta(hours=8, minutes=10),
            low=106, high=116
        )
        e.on_closed_m15(m15_cross(T + timedelta(hours=8, minutes=30)))
        e.on_closed_h4(h4(2, 104, 116, 110))
        self.assertEqual(len(e.events), 0)

    def test_04_multi4_requires_four_closed_h4_and_c2a_sweep(self) -> None:
        e = AuxiliaryOwnedMss("EURUSD", "forex")
        e.on_closed_h4(h4(0, 100, 120, 110))
        sweep(
            e, start=T + timedelta(hours=4, minutes=5),
            low=99, high=119
        )
        e.on_closed_m15(m15_cross(T + timedelta(hours=4, minutes=30)))
        e.on_closed_h4(h4(1, 99, 119, 110))
        self.assertEqual(len(e.events), 0)
        e.on_closed_h4(h4(2, 100, 118, 107))
        self.assertEqual(len(e.events), 0)
        e.on_closed_h4(h4(3, 105, 120, 112))
        self.assertEqual(len(e.events), 1)
        self.assertEqual(e.events[0].family, Family.MULTI4)

    def test_05_multi4_sweep_in_c2b_not_accepted(self) -> None:
        e = AuxiliaryOwnedMss("EURUSD", "forex")
        e.on_closed_h4(h4(0, 100, 120, 110))
        e.on_closed_h4(h4(1, 99, 119, 110))
        sweep(
            e, start=T + timedelta(hours=8, minutes=5),
            low=99, high=119
        )
        e.on_closed_m15(m15_cross(T + timedelta(hours=8, minutes=30)))
        e.on_closed_h4(h4(2, 100, 118, 107))
        e.on_closed_h4(h4(3, 105, 120, 112))
        self.assertFalse(e.events)

    def test_06_multi_n_two_inside_and_terminal_own_mss(self) -> None:
        e = AuxiliaryOwnedMss("EURUSD", "forex")
        e.on_closed_h4(h4(0, 100, 120, 110))
        e.on_closed_h4(h4(1, 105, 115, 110))
        e.on_closed_h4(h4(2, 104, 116, 109))
        # The pre-sweep confirmed swing must be fresh (<720m), not
        # the 12h25 old C1 pivot from the other test fixtures.
        fresh = T + timedelta(hours=11)
        own = SwingSnapshot(
            Pivot("HIGH", 108, fresh, fresh + timedelta(minutes=30), fresh),
            None, fresh
        )
        sweep(
            e, start=T + timedelta(hours=12, minutes=5),
            low=99, high=118, before=own
        )
        e.on_closed_m15(m15_cross(T + timedelta(hours=12, minutes=30)))
        e.on_closed_h4(h4(3, 99, 118, 108))
        self.assertEqual(len(e.events), 1)
        self.assertEqual(e.events[0].family, Family.MULTIN)

    def test_07_multi_n_double_sweep_rejects(self) -> None:
        e = AuxiliaryOwnedMss("EURUSD", "forex")
        for x in (
            h4(0, 100, 120, 110),
            h4(1, 105, 115, 110),
            h4(2, 104, 116, 109),
        ):
            e.on_closed_h4(x)
        sweep(
            e, start=T + timedelta(hours=12, minutes=5),
            low=99, high=121
        )
        e.on_closed_m15(m15_cross(T + timedelta(hours=12, minutes=30)))
        e.on_closed_h4(h4(3, 99, 121, 108))
        self.assertEqual(len(e.events), 0)

    def test_08_no_pivot_cannot_borrow_base_mss(self) -> None:
        e = AuxiliaryOwnedMss("EURUSD", "forex")
        for x in (h4(0, 100, 120, 110), h4(1, 105, 115, 110)):
            e.on_closed_h4(x)
        empty = SwingSnapshot(None, None, T)
        sweep(
            e, start=T + timedelta(hours=8, minutes=5),
            low=104, high=114, before=empty
        )
        e.on_closed_m15(m15_cross(T + timedelta(hours=8, minutes=30)))
        e.on_closed_h4(h4(2, 104, 114, 110))
        self.assertFalse(e.events)

    def test_09_reject_discontinuous_h4_history(self) -> None:
        e = AuxiliaryOwnedMss("EURUSD", "forex")
        e.on_closed_h4(h4(0, 100, 120, 110))
        e.on_closed_h4(None)
        e.on_closed_h4(h4(1, 105, 115, 110))
        self.assertTrue(all(
            p.c1.opened_at == h4(1, 105, 115, 110).opened_at
            for p in e.pending
        ))

    def test_10_no_signal_before_mss15_bar_closes(self) -> None:
        e = AuxiliaryOwnedMss("EURUSD", "forex")
        e.on_closed_h4(h4(0, 100, 120, 110))
        e.on_closed_h4(h4(1, 105, 115, 110))
        sweep(
            e, start=T + timedelta(hours=8, minutes=5),
            low=104, high=114
        )
        e.on_closed_m15(m15_cross(T + timedelta(hours=8)))
        e.on_closed_h4(h4(2, 104, 114, 110))
        self.assertFalse(e.events)

    def test_11_research_requires_explicit_family(self) -> None:
        with self.assertRaises(ValueError):
            AuxiliaryOwnedMss("EURUSD", "unknown")

    def test_12_families_observed_are_not_broker_trade_orders(self) -> None:
        e = AuxiliaryOwnedMss("EURUSD", "forex")
        x = e.readout()
        self.assertEqual(x["trades_executed"], 0)
        self.assertIs(x["not_identical_pine_f_engine"], True)
        self.assertIs(x["unseen_holdout"], False)


    def test_13_multi_n_geometry_owner_precedes_optional_mss(self) -> None:
        # Two valid C1s for one terminal. The geometric observer selects
        # the most recent C1; MSS on the older C1 MUST NOT create a signal.
        own = AuxiliaryOwnedMss("EURUSD", "forex")
        geometry = SecondaryGeometryObserver("forex")
        candles = (
            h4(0, 100, 120, 110),
            h4(1, 104, 116, 110),
            h4(2, 106, 114, 110),
            h4(3, 107, 113, 110),
        )
        terminal = h4(4, 99, 115, 110)
        for candle in candles:
            own.on_closed_h4(candle)
            geometry.on_closed_h4(candle)
        due = [
            p for p in own.pending
            if p.family == Family.MULTIN
            and p.terminal_end == terminal.closed_at
        ]
        self.assertEqual(
            {p.c1.opened_at for p in due},
            {candles[0].opened_at, candles[1].opened_at}
        )
        older = next(p for p in due if p.c1.opened_at == candles[0].opened_at)
        older.direction = 1
        older.sweep_at = T + timedelta(hours=16, minutes=10)
        older.own_pivot15 = Pivot(
            "HIGH", 108, T + timedelta(hours=15),
            T + timedelta(hours=15, minutes=10),
            T + timedelta(hours=15)
        )
        older.own_mss15_at = T + timedelta(hours=16, minutes=30)
        own.on_closed_h4(terminal)
        geometry.on_closed_h4(terminal)
        confirmed = [
            g for g in geometry.events
            if g.family == Family.MULTIN
            and g.ratified_at == terminal.closed_at
        ]
        self.assertEqual(len(confirmed), 1)
        self.assertEqual(confirmed[0].c1_at, candles[1].opened_at)
        # Old implementation emitted an older, unobserved C1 here.
        self.assertEqual(own.events, [])

    def test_14_multi_n_own_mss_on_selected_geometry_is_allowed(self) -> None:
        own = AuxiliaryOwnedMss("EURUSD", "forex")
        candles = (
            h4(0, 100, 120, 110), h4(1, 104, 116, 110),
            h4(2, 106, 114, 110), h4(3, 107, 113, 110)
        )
        terminal = h4(4, 99, 115, 110)
        for candle in candles:
            own.on_closed_h4(candle)
        due = [
            p for p in own.pending
            if p.family == Family.MULTIN
            and p.terminal_end == terminal.closed_at
        ]
        for p in due:
            p.direction = 1
            p.sweep_at = T + timedelta(hours=16, minutes=10)
            p.own_pivot15 = Pivot(
                "HIGH", 108, T + timedelta(hours=15),
                T + timedelta(hours=15, minutes=10),
                T + timedelta(hours=15)
            )
            p.own_mss15_at = T + timedelta(hours=16, minutes=30)
        own.on_closed_h4(terminal)
        signals = [x for x in own.events if x.family == Family.MULTIN]
        self.assertEqual(len(signals), 1)
        self.assertEqual(signals[0].c1_at, candles[1].opened_at)


if __name__ == "__main__":
    unittest.main(verbosity=2)

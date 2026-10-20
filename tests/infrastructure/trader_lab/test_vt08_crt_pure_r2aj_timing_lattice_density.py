from __future__ import annotations

from datetime import UTC, datetime

from qore.infrastructure.trader_lab.vt08_crt_pure_r2aj_timing_lattice_density import (
    END,
    IDENTITY,
    START,
    START_HOURS,
    TimingLattice,
    _window,
)


def test_r2aj_identity_and_lattices_are_frozen() -> None:
    assert IDENTITY == "VT08_CRT_PURE_R2AJ_H4_TIMING_LATTICE_DENSITY_001"
    assert START_HOURS[TimingLattice.CONTROL_NON_OVERLAP] == (1, 13)
    assert START_HOURS[TimingLattice.ROLLING_H4] == (1, 5, 9, 13, 17, 21)


def test_r2aj_common_window_is_six_years_utc() -> None:
    assert START == datetime(2020, 9, 21, 0, 0, tzinfo=UTC)
    assert END == datetime(2026, 9, 21, 0, 0, tzinfo=UTC)


def test_rolling_window_preserves_consecutive_h4_geometry() -> None:
    day = datetime(2026, 1, 5, 12, 0, tzinfo=UTC)
    window = _window(day, 5)

    assert (window.c2_open - window.c1_open).total_seconds() == 4 * 3600
    assert (window.c3_open - window.c2_open).total_seconds() == 4 * 3600
    assert (window.close - window.c3_open).total_seconds() == 4 * 3600

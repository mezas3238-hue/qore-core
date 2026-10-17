from __future__ import annotations

from qore.infrastructure.trader_lab.vt08_crt_pure_r2ak_timing_economic import (
    BASE_POLICY,
    END,
    IDENTITY,
    START,
    TimingLattice,
)
from qore.infrastructure.trader_lab.vt08_crt_pure_r2g_competition_lab import (
    CompetitionPolicy,
)


def test_r2ak_identity_and_window_are_frozen() -> None:
    assert IDENTITY == "VT08_CRT_PURE_R2AK_H4_TIMING_ECONOMIC_001"
    assert START.year == 2020
    assert END.year == 2026


def test_r2ak_uses_existing_competition_policy() -> None:
    assert BASE_POLICY is CompetitionPolicy.NEWEST_SUPERSEDES_CONFIRMATION_FIRST


def test_r2ak_has_control_and_rolling_lattices() -> None:
    assert tuple(TimingLattice) == (
        TimingLattice.CONTROL_NON_OVERLAP,
        TimingLattice.ROLLING_H4,
    )

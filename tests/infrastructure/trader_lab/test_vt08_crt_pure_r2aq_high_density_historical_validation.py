from __future__ import annotations

from qore.infrastructure.trader_lab.vt08_crt_pure_r2af_audusd_target_family import (
    TargetArm,
)
from qore.infrastructure.trader_lab.vt08_crt_pure_r2aj_timing_lattice_density import (
    TimingLattice,
)
from qore.infrastructure.trader_lab.vt08_crt_pure_r2aq_high_density_historical_validation import (
    ARM,
    IDENTITY,
    LATTICE,
    WINDOWS,
)
from qore.infrastructure.traders.crt_pure_identity import CrtPureMarket


def test_r2aq_identity_and_candidate_are_frozen() -> None:
    assert IDENTITY == "VT08_CRT_PURE_R2AQ_HIGH_DENSITY_HISTORICAL_VALIDATION_001"
    assert LATTICE is TimingLattice.ROLLING_H4
    assert ARM is TargetArm.FIXED_1_5R


def test_r2aq_validation_windows_precede_development() -> None:
    aud = WINDOWS[CrtPureMarket.AUDUSD]
    uj = WINDOWS[CrtPureMarket.USDJPY]

    assert (aud.start.year, aud.end.year) == (2016, 2020)
    assert (uj.start.year, uj.end.year) == (2014, 2020)

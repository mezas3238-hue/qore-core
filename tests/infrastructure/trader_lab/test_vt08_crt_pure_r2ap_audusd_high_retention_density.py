from __future__ import annotations

from decimal import Decimal

from qore.infrastructure.trader_lab.vt08_crt_pure_r2af_audusd_target_family import (
    TargetArm,
)
from qore.infrastructure.trader_lab.vt08_crt_pure_r2aj_timing_lattice_density import (
    TimingLattice,
)
from qore.infrastructure.trader_lab.vt08_crt_pure_r2ap_audusd_high_retention_density import (
    ARM,
    IDENTITY,
    LATTICE,
    MANIP_HIGH,
    MANIP_LOW,
)


def test_r2ap_identity_is_frozen() -> None:
    assert IDENTITY == "VT08_CRT_PURE_R2AP_AUDUSD_HIGH_RETENTION_DENSITY_001"


def test_r2ap_combination_is_frozen() -> None:
    assert LATTICE is TimingLattice.ROLLING_H4
    assert ARM is TargetArm.FIXED_2R
    assert MANIP_LOW == Decimal("0.10")
    assert MANIP_HIGH == Decimal("0.25")

from __future__ import annotations

from qore.infrastructure.trader_lab.vt08_crt_pure_r2af_audusd_target_family import (
    TargetArm,
)
from qore.infrastructure.trader_lab.vt08_crt_pure_r2aj_timing_lattice_density import (
    TimingLattice,
)
from qore.infrastructure.trader_lab.vt08_crt_pure_r2as_rolling_overlap_census import (
    ARM,
    IDENTITY,
    LATTICE,
    _multiplicity,
)


def test_r2as_contract_is_frozen() -> None:
    assert IDENTITY == "VT08_CRT_PURE_R2AS_ROLLING_CAUSAL_OVERLAP_CENSUS_001"
    assert LATTICE is TimingLattice.ROLLING_H4
    assert ARM is TargetArm.FIXED_1_5R


def test_multiplicity_reports_duplicates() -> None:
    report = _multiplicity((("a",), ("a",), ("b",)))

    assert report["unique"] == 2
    assert report["duplicate_rows"] == 1
    assert report["max_multiplicity"] == 2

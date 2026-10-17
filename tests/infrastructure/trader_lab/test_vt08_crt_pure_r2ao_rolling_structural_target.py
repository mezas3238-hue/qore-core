from __future__ import annotations

from qore.infrastructure.trader_lab.vt08_crt_pure_r2af_audusd_target_family import (
    TargetArm,
)
from qore.infrastructure.trader_lab.vt08_crt_pure_r2aj_timing_lattice_density import (
    TimingLattice,
)
from qore.infrastructure.trader_lab.vt08_crt_pure_r2ao_rolling_structural_target import (
    ARMS,
    BASE_POLICY,
    END,
    IDENTITY,
    LATTICE,
    START,
)
from qore.infrastructure.trader_lab.vt08_crt_pure_r2g_competition_lab import (
    CompetitionPolicy,
)


def test_r2ao_identity_and_window_are_frozen() -> None:
    assert IDENTITY == "VT08_CRT_PURE_R2AO_ROLLING_STRUCTURAL_TARGET_001"
    assert START.year == 2020
    assert END.year == 2026


def test_r2ao_uses_rolling_h4_and_existing_competition() -> None:
    assert LATTICE is TimingLattice.ROLLING_H4
    assert BASE_POLICY is CompetitionPolicy.NEWEST_SUPERSEDES_CONFIRMATION_FIRST


def test_r2ao_target_family_is_frozen() -> None:
    assert ARMS == (
        TargetArm.MIDPOINT_CONTROL,
        TargetArm.FIXED_1R,
        TargetArm.FIXED_1_5R,
        TargetArm.FIXED_2R,
    )

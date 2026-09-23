from __future__ import annotations

from qore.infrastructure.trader_lab.vt08_crt_pure_r2al_structural_target_density import (
    ARMS,
    BASE_POLICY,
    END,
    IDENTITY,
    START,
)
from qore.infrastructure.trader_lab.vt08_crt_pure_r2af_audusd_target_family import (
    TargetArm,
)
from qore.infrastructure.trader_lab.vt08_crt_pure_r2g_competition_lab import (
    CompetitionPolicy,
)


def test_r2al_identity_and_window_are_frozen() -> None:
    assert IDENTITY == "VT08_CRT_PURE_R2AL_STRUCTURAL_TARGET_DENSITY_001"
    assert START.year == 2020
    assert END.year == 2026


def test_r2al_reuses_existing_competition_policy() -> None:
    assert BASE_POLICY is CompetitionPolicy.NEWEST_SUPERSEDES_CONFIRMATION_FIRST


def test_r2al_target_family_is_frozen() -> None:
    assert ARMS == (
        TargetArm.MIDPOINT_CONTROL,
        TargetArm.FIXED_1R,
        TargetArm.FIXED_1_5R,
        TargetArm.FIXED_2R,
    )

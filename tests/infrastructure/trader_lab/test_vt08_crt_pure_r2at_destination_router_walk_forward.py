from __future__ import annotations

from qore.infrastructure.trader_lab.vt08_crt_pure_r2af_audusd_target_family import (
    TargetArm,
)
from qore.infrastructure.trader_lab.vt08_crt_pure_r2at_destination_router_walk_forward import (
    ARMS,
    BASELINE_ARM,
    IDENTITY,
    TRAINING_YEARS,
    _select_arm,
)


def test_r2at_contract_is_frozen() -> None:
    assert IDENTITY == "VT08_CRT_PURE_R2AT_DESTINATION_ROUTER_WALK_FORWARD_001"
    assert TRAINING_YEARS == 3
    assert BASELINE_ARM is TargetArm.FIXED_1_5R
    assert ARMS == (
        TargetArm.FIXED_1R,
        TargetArm.FIXED_1_5R,
        TargetArm.FIXED_2R,
    )


def test_empty_training_tie_break_is_deterministic() -> None:
    arm, totals = _select_arm(())

    assert arm is TargetArm.FIXED_1R
    assert all(value == 0 for value in totals.values())

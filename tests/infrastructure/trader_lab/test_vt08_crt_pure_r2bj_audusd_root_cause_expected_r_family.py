from __future__ import annotations

from qore.infrastructure.trader_lab.vt08_crt_pure_r2bj_audusd_root_cause_expected_r_family import (
    ABSTENTION_FRACTION,
    IDENTITY,
    MIN_CELL_SUPPORT,
    PRIOR_STRENGTH,
    MemoryHead,
)


def test_r2bj_contract_is_frozen() -> None:
    assert IDENTITY == "VT08_CRT_PURE_R2BJ_AUDUSD_ROOT_CAUSE_EXPECTED_R_FAMILY_001"
    assert ABSTENTION_FRACTION == 0.20
    assert MIN_CELL_SUPPORT == 30
    assert PRIOR_STRENGTH == 100.0


def test_r2bj_heads_are_frozen() -> None:
    assert tuple(MemoryHead) == (
        MemoryHead.REF_DELAY,
        MemoryHead.REF_DELAY_DIRECTION,
        MemoryHead.TIMING_REF_DELAY,
    )

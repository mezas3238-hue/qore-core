from __future__ import annotations

from qore.infrastructure.trader_lab.vt08_crt_pure_r2bu_usdjpy_overlap_expected_r_wf import (
    IDENTITY,
    MemoryHead,
)


def test_r2bu_contract_is_frozen() -> None:
    assert IDENTITY == "VT08_CRT_PURE_R2BU_USDJPY_OVERLAP_EXPECTED_R_WF_001"
    assert tuple(MemoryHead) == (
        MemoryHead.REF_DELAY_DIRECTION_CONTROL,
        MemoryHead.REF_DELAY_OVERLAP,
        MemoryHead.REF_DELAY_DIRECTION_OVERLAP,
    )

from __future__ import annotations

from qore.infrastructure.trader_lab.vt08_crt_pure_r2bu_usdjpy_overlap_expected_r_wf import (
    MemoryHead,
)
from qore.infrastructure.trader_lab.vt08_crt_pure_r2bv_usdjpy_overlap_tie_safe_wf import (
    HEAD,
    IDENTITY,
)


def test_r2bv_contract_is_frozen() -> None:
    assert IDENTITY == "VT08_CRT_PURE_R2BV_USDJPY_OVERLAP_TIE_SAFE_WF_001"
    assert HEAD is MemoryHead.REF_DELAY_OVERLAP

from __future__ import annotations

from qore.infrastructure.trader_lab.vt08_crt_pure_r2bx_usdjpy_displacement_overlap_expected_r_wf import (
    IDENTITY,
    TOXIC_STATE,
)


def test_r2bx_contract_is_frozen() -> None:
    assert IDENTITY == (
        "VT08_CRT_PURE_R2BX_USDJPY_DISPLACEMENT_OVERLAP_EXPECTED_R_WF_001"
    )
    assert TOXIC_STATE == "CONFDISP_LT_0_50|CONFOVERLAP_0_50_TO_0_75"

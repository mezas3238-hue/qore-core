from __future__ import annotations

from qore.infrastructure.trader_lab import (
    vt08_crt_pure_r2bx_usdjpy_displacement_overlap_expected_r_wf as r2bx,
)


def test_r2bx_contract_is_frozen() -> None:
    assert r2bx.IDENTITY == (
        "VT08_CRT_PURE_R2BX_USDJPY_DISPLACEMENT_OVERLAP_EXPECTED_R_WF_001"
    )
    assert (
        r2bx.TOXIC_STATE
        == "CONFDISP_LT_0_50|CONFOVERLAP_0_50_TO_0_75"
    )

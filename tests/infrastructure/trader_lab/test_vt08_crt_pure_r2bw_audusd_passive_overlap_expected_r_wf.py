from __future__ import annotations

from qore.infrastructure.trader_lab.vt08_crt_pure_r2bw_audusd_passive_overlap_expected_r_wf import (
    HEAD,
    IDENTITY,
    TOXIC_OVERLAP_LABEL,
)


def test_r2bw_contract_is_frozen() -> None:
    assert IDENTITY == (
        "VT08_CRT_PURE_R2BW_AUDUSD_PASSIVE_OVERLAP_EXPECTED_R_WF_001"
    )
    assert HEAD == "REF_DELAY_DIRECTION_OVERLAP_FLAG"
    assert TOXIC_OVERLAP_LABEL == "CONFOVERLAP_0_50_TO_0_75"

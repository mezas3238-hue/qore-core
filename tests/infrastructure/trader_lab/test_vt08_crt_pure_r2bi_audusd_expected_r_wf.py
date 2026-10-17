from __future__ import annotations

from qore.infrastructure.trader_lab.vt08_crt_pure_r2bi_audusd_expected_r_wf import (
    ABSTENTION_FRACTION,
    IDENTITY,
    MIN_STATE_SUPPORT,
    PRIOR_STRENGTH,
    TRAINING_YEARS,
)


def test_r2bi_contract_is_frozen() -> None:
    assert IDENTITY == "VT08_CRT_PURE_R2BI_AUDUSD_EXPECTED_R_WF_001"
    assert TRAINING_YEARS == 4
    assert ABSTENTION_FRACTION == 0.20
    assert MIN_STATE_SUPPORT == 30
    assert PRIOR_STRENGTH == 50.0

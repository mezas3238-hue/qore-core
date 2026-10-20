from __future__ import annotations

from qore.infrastructure.trader_lab.vt08_crt_pure_r2bh_audusd_entry_viability_wf import (
    IDENTITY,
    LAPLACE_STRENGTH,
    MIN_STATE_SUPPORT,
    REMOVAL_FRACTIONS,
    TRAINING_YEARS,
)


def test_r2bh_contract_is_frozen() -> None:
    assert IDENTITY == "VT08_CRT_PURE_R2BH_AUDUSD_ENTRY_VIABILITY_WF_001"
    assert TRAINING_YEARS == 4
    assert REMOVAL_FRACTIONS == (0.10, 0.15, 0.20, 0.25)
    assert MIN_STATE_SUPPORT == 30
    assert LAPLACE_STRENGTH == 5.0

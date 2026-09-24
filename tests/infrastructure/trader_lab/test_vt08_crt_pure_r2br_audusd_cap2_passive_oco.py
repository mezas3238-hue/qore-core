from __future__ import annotations

from qore.infrastructure.trader_lab.vt08_crt_pure_r2br_audusd_cap2_passive_oco import (
    IDENTITY,
    MAX_PENDING_HYPOTHESES,
    MAX_REALISED_TRADES_PER_PARENT,
)


def test_r2br_cap2_contract_is_frozen() -> None:
    assert IDENTITY == "VT08_CRT_PURE_R2BR_AUDUSD_CAP2_PASSIVE_OCO_001"
    assert MAX_PENDING_HYPOTHESES == 2
    assert MAX_REALISED_TRADES_PER_PARENT == 1

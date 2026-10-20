from __future__ import annotations

from qore.infrastructure.trader_lab import (
    vt08_crt_pure_r2cb_usdjpy_wait_journey_atlas as r2cb,
)


def test_r2cb_contract_is_frozen() -> None:
    assert r2cb.IDENTITY == (
        "VT08_CRT_PURE_R2CB_USDJPY_WAIT_JOURNEY_ATLAS_001"
    )

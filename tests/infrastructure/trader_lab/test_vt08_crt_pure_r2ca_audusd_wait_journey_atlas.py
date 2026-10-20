from __future__ import annotations

from qore.infrastructure.trader_lab import (
    vt08_crt_pure_r2ca_audusd_wait_journey_atlas as r2ca,
)


def test_r2ca_contract_is_frozen() -> None:
    assert r2ca.IDENTITY == (
        "VT08_CRT_PURE_R2CA_AUDUSD_WAIT_JOURNEY_ATLAS_001"
    )

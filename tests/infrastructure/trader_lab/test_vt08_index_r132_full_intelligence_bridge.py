from __future__ import annotations

from decimal import Decimal

from qore.infrastructure.trader_lab import (
    vt08_index_r132_full_intelligence_bridge as r132,
)


def test_r132_shared_snapshot_is_pinned() -> None:
    assert r132.SHARED_SOURCE_PR == 635
    assert r132.SHARED_SOURCE_HEAD == (
        "0429fbe210246f04e1b572191737e86a490781fc"
    )
    assert r132.SHARED_SNAPSHOT_FILES["perception_engine.py"] == (
        "696cf267a5f2e17ae40cdb7b322a7e6be9612d32"
    )
    assert r132.SHARED_SNAPSHOT_FILES[
        "competing_future_intelligence.py"
    ] == "f6e2624100c8457e9c7c79dc35b12c79e51e9bd8"


def test_r132_density_contract_is_reopened() -> None:
    assert r132.EXPECTED_CANONICAL == {
        "5Y": 2448,
        "2Y": 1017,
        "R66": 773,
    }
    assert r132.HORIZON_BARS == (
        (60, 4),
        (240, 16),
        (960, 64),
    )


def test_r132_bps_clamps() -> None:
    assert r132._clamp_bps(Decimal("-1")) == 0
    assert r132._clamp_bps(Decimal("0.5")) == 5000
    assert r132._clamp_bps(Decimal("2")) == 10000

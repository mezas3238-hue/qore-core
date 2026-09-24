from __future__ import annotations

from decimal import Decimal

from qore.infrastructure.trader_lab import (
    vt08_index_r80_source_2r_target_transport as r80,
)
from qore.infrastructure.trader_lab import (
    vt08_index_r126_targeted_source_2r as r126,
)
from qore.infrastructure.traders.contracts import DemoTradingSetupSide


def test_r126_source_and_target_state_are_pinned() -> None:
    assert r126.SOURCE_R125_RUN_ID == 36059043366
    assert r126.SOURCE_R125_ARTIFACT_ID == 10834116084
    assert r126.SOURCE_R125_ARTIFACT_DIGEST == (
        "sha256:203ac657aefac8762fb3f38c66f90931"
        "21626d5ed7460cea48fdc596b61c0192"
    )
    assert r126.TARGET_STATE == (
        "SWEEP_REVERSAL|PRIOR_DEEPER_THAN_FINAL_PS"
    )
    assert r126.EXPECTED_TARGET_STATE == {
        "5Y": 235,
        "2Y": 110,
        "R66": 101,
    }
    assert r126.SOURCE_TARGET_R == r80.SOURCE_TARGET_R == Decimal("2")


def test_r126_target_price_uses_exact_2r() -> None:
    assert r126._target_price(
        entry=Decimal("100"),
        stop=Decimal("90"),
        side=DemoTradingSetupSide.LONG,
    ) == Decimal("120")
    assert r126._target_price(
        entry=Decimal("100"),
        stop=Decimal("110"),
        side=DemoTradingSetupSide.SHORT,
    ) == Decimal("80")

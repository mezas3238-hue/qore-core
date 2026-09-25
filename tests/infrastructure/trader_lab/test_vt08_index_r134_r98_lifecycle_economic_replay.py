from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

from qore.infrastructure.trader_lab import (
    vt08_index_r134_r98_lifecycle_economic_replay as r134,
)
from qore.infrastructure.traders.contracts import DemoTradingSetupSide


def test_r134_source_r133_is_pinned() -> None:
    assert r134.SOURCE_R133_RUN_ID == 36174956716
    assert r134.SOURCE_R133_ARTIFACT_ID == 10882800411
    assert r134.SOURCE_R133_ARTIFACT_DIGEST == (
        "sha256:049a0a71b393413386abd87cbef82a7f"
        "0cd01442968eb2927f21411591475025"
    )


def test_r134_target_and_stress_are_current_contract() -> None:
    assert r134.TARGET_R == Decimal("2.5")
    assert r134.PRIMARY_STRESS == Decimal("0.05")
    assert r134.SECONDARY_STRESS == Decimal("0.10")


def test_r134_execution_key_is_exact() -> None:
    row = r134.LifecycleExecution(
        symbol="NAS100",
        side=DemoTradingSetupSide.LONG,
        signal_at=datetime(2026, 1, 1, tzinfo=UTC),
        entry=Decimal("100"),
        stop=Decimal("90"),
        source_kind="IDEAL_C2",
    )
    assert row.key() == (
        "NAS100",
        datetime(2026, 1, 1, tzinfo=UTC),
        "long",
        Decimal("100"),
        Decimal("90"),
    )

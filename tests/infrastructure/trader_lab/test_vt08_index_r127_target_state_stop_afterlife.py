from __future__ import annotations

from decimal import Decimal

from qore.infrastructure.trader_lab import (
    vt08_index_r127_target_state_stop_afterlife as r127,
)
from qore.infrastructure.traders.contracts import DemoTradingSetupSide
from qore.infrastructure.traders.vt08_index_c2_positional_r1 import (
    Vt08IndexC2R1Bar,
)


def test_r127_source_and_target_state_are_pinned() -> None:
    assert r127.SOURCE_R126_RUN_ID == 36059660561
    assert r127.SOURCE_R126_ARTIFACT_ID == 10833354775
    assert r127.SOURCE_R126_ARTIFACT_DIGEST == (
        "sha256:e52e6033dc75d61e631603f006c18f87"
        "e090f2346c9b1f7942208e48cb19131c"
    )
    assert r127.TARGET_STATE == (
        "SWEEP_REVERSAL|PRIOR_DEEPER_THAN_FINAL_PS"
    )
    assert r127.EXPECTED_TARGET_STATE == {
        "5Y": 235,
        "2Y": 110,
        "R66": 101,
    }


def test_r127_breach_is_side_aware() -> None:
    from datetime import UTC, datetime, timedelta

    opened = datetime(2026, 1, 1, tzinfo=UTC)
    bar = Vt08IndexC2R1Bar(
        opened_at=opened,
        closed_at=opened + timedelta(minutes=15),
        open=Decimal("100"),
        high=Decimal("112"),
        low=Decimal("88"),
        close=Decimal("101"),
    )
    assert r127._breached(
        side=DemoTradingSetupSide.LONG,
        level=Decimal("90"),
        bar=bar,
    )
    assert r127._breached(
        side=DemoTradingSetupSide.SHORT,
        level=Decimal("110"),
        bar=bar,
    )


def test_r127_buckets_are_frozen() -> None:
    assert r127._mfe_bucket(Decimal("0.1")) == "LT_0_25R"
    assert r127._mfe_bucket(Decimal("0.4")) == "R_0_25_TO_0_5"
    assert r127._mfe_bucket(Decimal("0.8")) == "R_0_5_TO_1"
    assert r127._mfe_bucket(Decimal("1")) == "GE_1R"
    assert r127._extension_bucket(Decimal("0.2")) == "LE_0_25R"
    assert r127._extension_bucket(Decimal("0.4")) == "R_0_25_TO_0_5"
    assert r127._extension_bucket(Decimal("0.8")) == "R_0_5_TO_1"
    assert r127._extension_bucket(Decimal("1.1")) == "GT_1R"

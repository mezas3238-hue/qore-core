from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

from qore.infrastructure.trader_lab.vt08_crt_pure_r2q_usdjpy_multi_regime_atlas import (
    BLOCK_2,
    BLOCK_3,
    END,
    START,
    _bucket_efficiency,
    _bucket_fraction,
    _bucket_ratio,
)


def test_r2q_regime_blocks_are_frozen() -> None:
    assert START == datetime(2020, 9, 21, 0, 0, tzinfo=UTC)
    assert BLOCK_2 == datetime(2022, 9, 21, 0, 0, tzinfo=UTC)
    assert BLOCK_3 == datetime(2024, 9, 21, 0, 0, tzinfo=UTC)
    assert END == datetime(2026, 9, 21, 0, 0, tzinfo=UTC)


def test_r2q_ratio_buckets_are_frozen() -> None:
    assert _bucket_ratio(Decimal("0.79"), "VOL") == "VOL_LT_0_80"
    assert _bucket_ratio(Decimal("0.80"), "VOL") == "VOL_0_80_TO_1_20"
    assert _bucket_ratio(Decimal("1.20"), "VOL") == "VOL_GE_1_20"


def test_r2q_efficiency_buckets_are_frozen() -> None:
    assert _bucket_efficiency(Decimal("0.09"), "EFF") == "EFF_LT_0_10"
    assert _bucket_efficiency(Decimal("0.10"), "EFF") == "EFF_0_10_TO_0_20"
    assert _bucket_efficiency(Decimal("0.20"), "EFF") == "EFF_0_20_TO_0_35"
    assert _bucket_efficiency(Decimal("0.35"), "EFF") == "EFF_GE_0_35"


def test_r2q_fraction_buckets_are_quartiles() -> None:
    assert _bucket_fraction(Decimal("0.24"), "X") == "X_LT_0_25"
    assert _bucket_fraction(Decimal("0.25"), "X") == "X_0_25_TO_0_50"
    assert _bucket_fraction(Decimal("0.50"), "X") == "X_0_50_TO_0_75"
    assert _bucket_fraction(Decimal("0.75"), "X") == "X_GE_0_75"

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from types import SimpleNamespace

from qore.infrastructure.trader_lab import (
    vt08_index_r92_fractal_cascade_union as r92,
)
from qore.infrastructure.traders.contracts import DemoTradingSetupSide


def test_r92_canonical_identity_matches_nested_shape() -> None:
    signal = SimpleNamespace(
        symbol="NAS100",
        signal_at=datetime(2018, 1, 2, 12, 0, tzinfo=UTC),
        side=DemoTradingSetupSide.LONG,
        entry=Decimal("100"),
        stop=Decimal("99"),
    )
    item = SimpleNamespace(signal=signal)
    identity = r92._canonical_identity(item)
    assert identity == (
        "NAS100",
        signal.signal_at,
        "long",
        Decimal("100"),
        Decimal("99"),
    )


def test_r92_nested_identity_preserves_exact_mechanical_fields() -> None:
    nested = SimpleNamespace(
        identity=lambda: (
            "US30",
            datetime(2018, 1, 2, 13, 0, tzinfo=UTC),
            "short",
            Decimal("25000"),
            Decimal("25100"),
        )
    )
    assert r92._nested_identity(nested) == (
        "US30",
        datetime(2018, 1, 2, 13, 0, tzinfo=UTC),
        "short",
        Decimal("25000"),
        Decimal("25100"),
    )


def test_r92_source_runs_are_pinned() -> None:
    assert r92.SOURCE_R88_RUN_ID == 35526661105
    assert r92.SOURCE_R91_RUN_ID == 35528095177


def test_r92_exact_union_identity_has_no_fuzzy_tolerance_field() -> None:
    assert r92.IDENTITY == "VT08_INDEX_R92_R66_EXACT_FRACTAL_CASCADE_UNION_001"

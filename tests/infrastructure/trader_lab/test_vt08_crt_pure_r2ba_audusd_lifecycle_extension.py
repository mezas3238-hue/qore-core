from __future__ import annotations

from datetime import UTC, datetime, timedelta

from qore.infrastructure.trader_lab.vt08_crt_pure_r2_model1_reference_lab import M15Bar
from qore.infrastructure.trader_lab.vt08_crt_pure_r2ba_audusd_lifecycle_extension import (
    EXPECTED_EXTENSION_BARS,
    EXTENSION,
    IDENTITY,
    LifecyclePolicy,
    _extension_complete,
)


def test_r2ba_identity_and_family_are_frozen() -> None:
    assert IDENTITY == "VT08_CRT_PURE_R2BA_AUDUSD_LIFECYCLE_EXTENSION_001"
    assert EXTENSION == timedelta(hours=4)
    assert EXPECTED_EXTENSION_BARS == 16
    assert tuple(LifecyclePolicy) == (
        LifecyclePolicy.CONTROL_C3_CLOSE,
        LifecyclePolicy.NEXT_H4,
    )


def test_extension_requires_all_sixteen_contiguous_m15_bars() -> None:
    c3_close = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)
    bars = {
        c3_close + timedelta(minutes=15 * index): M15Bar(
            opened_at=c3_close + timedelta(minutes=15 * index),
            open_price=100,
            high_price=101,
            low_price=99,
            close_price=100,
        )
        for index in range(16)
    }
    assert _extension_complete(c3_close=c3_close, m15_by_time=bars)

    bars.pop(c3_close + timedelta(minutes=15 * 7))
    assert not _extension_complete(c3_close=c3_close, m15_by_time=bars)

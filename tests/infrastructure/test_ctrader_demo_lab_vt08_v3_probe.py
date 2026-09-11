from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import pytest

from qore.infrastructure.ctrader_demo_lab_probe import (
    CTraderDemoLabClosedTrendbar,
    CTraderDemoLabProbeError,
)
from qore.infrastructure.ctrader_demo_lab_vt08_v3_probe import _parse_d1_bar


def _native(opened_at: datetime) -> SimpleNamespace:
    return SimpleNamespace(
        low=100_000,
        deltaOpen=1_000,
        deltaHigh=2_000,
        deltaClose=1_500,
        utcTimestampInMinutes=int(opened_at.timestamp() // 60),
    )


def test_v3_parses_provider_native_d1_without_widening_shared_lab_periods() -> None:
    opened = datetime(2026, 9, 1, tzinfo=UTC)
    parsed = _parse_d1_bar(
        _native(opened),
        digits=5,
        checked_at=opened + timedelta(days=2),
    )
    assert parsed is not None
    assert parsed.opened_at == opened
    assert parsed.closed_at == opened + timedelta(days=1)
    assert parsed.payload()["period"] == "D1"
    assert parsed.payload()["open"] == "1.01000"
    assert parsed.payload()["high"] == "1.02000"
    assert parsed.payload()["low"] == "1.00000"
    assert parsed.payload()["close"] == "1.01500"

    with pytest.raises(CTraderDemoLabProbeError, match="unsupported Lab trendbar period"):
        CTraderDemoLabClosedTrendbar(
            period="D1",
            opened_at=opened,
            closed_at=opened + timedelta(days=1),
            open="1.01000",
            high="1.02000",
            low="1.00000",
            close="1.01500",
        )


def test_v3_d1_parser_rejects_still_open_provider_candle() -> None:
    opened = datetime(2026, 9, 1, tzinfo=UTC)
    parsed = _parse_d1_bar(
        _native(opened),
        digits=5,
        checked_at=opened + timedelta(hours=12),
    )
    assert parsed is None

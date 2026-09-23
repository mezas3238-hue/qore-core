from datetime import UTC, datetime, timedelta

from qore.infrastructure.trader_lab.capitalizer_v3_max3_deep_forensics_2y_v1 import (
    EXPECTED_MAX3_TRADES,
    IDENTITY,
    MATRIX_IDENTITY,
    _freshness,
)


def test_max3_deep_forensics_contract() -> None:
    assert IDENTITY == "QORE_CAPITALIZER_V3_MAX3_DEEP_FORENSICS_2Y_V1"
    assert MATRIX_IDENTITY == (
        "QORE_CAPITALIZER_NINE_MARKET_V3_MAX3_DEEP_FORENSICS_2Y_V1"
    )
    assert EXPECTED_MAX3_TRADES == 474


def test_freshness_boundary_remains_30_minutes() -> None:
    base = datetime(2026, 9, 22, 10, tzinfo=UTC)
    assert _freshness(
        {
            "m5_closeback_at": base.isoformat(),
            "m3_mss_at": (base + timedelta(minutes=30)).isoformat(),
        }
    ) == "FRESH_LE_30M"
    assert _freshness(
        {
            "m5_closeback_at": base.isoformat(),
            "m3_mss_at": (base + timedelta(minutes=31)).isoformat(),
        }
    ) == "STALE_GT_30M"

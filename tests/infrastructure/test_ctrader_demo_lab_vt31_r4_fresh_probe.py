from datetime import UTC, datetime

from qore.infrastructure.ctrader_demo_lab_vt31_r4_fresh_probe import (
    FRESH_END_AT,
    FRESH_LOOKBACK_DAYS,
)


def test_vt31_r4_fresh_partition_is_predeclared_and_historical() -> None:
    assert FRESH_END_AT == datetime(2024, 8, 15, tzinfo=UTC)
    assert FRESH_LOOKBACK_DAYS == 760

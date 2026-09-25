from datetime import UTC, datetime

from qore.infrastructure.trader_lab.vt08_cognitive_expansion_7y_base_archive_v1 import (
    ARCHIVE_LOOKBACK_DAYS,
    ARCHIVE_MARKETS,
    FRESH_CUTOFF,
    REQUIRED_PERIODS,
)


def test_vt08_expansion_seven_year_archive_scope() -> None:
    assert ARCHIVE_LOOKBACK_DAYS == 2555
    assert ARCHIVE_MARKETS == ("EURJPY", "USDCHF", "NZDUSD", "CADJPY", "USDCAD")
    assert REQUIRED_PERIODS == ("M5", "M15", "H4")
    assert FRESH_CUTOFF == datetime(2023, 9, 24, 23, 45, tzinfo=UTC)

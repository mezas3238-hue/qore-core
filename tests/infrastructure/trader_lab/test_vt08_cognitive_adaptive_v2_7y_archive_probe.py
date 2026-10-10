from qore.infrastructure.trader_lab.vt08_cognitive_adaptive_v2_7y_archive_probe import (
    ARCHIVE_LOOKBACK_DAYS,
    ARCHIVE_MARKETS,
    MIN_ARCHIVE_SPAN_DAYS,
)


def test_adaptive_v2_seven_year_archive_scope() -> None:
    assert ARCHIVE_MARKETS == ("CADJPY", "NZDUSD")
    assert ARCHIVE_LOOKBACK_DAYS == 2555
    assert MIN_ARCHIVE_SPAN_DAYS == 2545

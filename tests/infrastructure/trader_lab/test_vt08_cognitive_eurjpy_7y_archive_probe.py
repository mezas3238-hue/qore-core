from qore.infrastructure.trader_lab.vt08_cognitive_eurjpy_7y_archive_probe import (
    ARCHIVE_LOOKBACK_DAYS,
    ARCHIVE_SYMBOL,
    MIN_ARCHIVE_SPAN_DAYS,
)


def test_seven_year_archive_is_raw_and_strict() -> None:
    assert ARCHIVE_SYMBOL == "EURJPY"
    assert ARCHIVE_LOOKBACK_DAYS == 2555
    assert MIN_ARCHIVE_SPAN_DAYS == 2545

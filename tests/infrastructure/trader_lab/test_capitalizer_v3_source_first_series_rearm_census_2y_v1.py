from qore.infrastructure.trader_lab import (
    capitalizer_v3_source_first_series_rearm_census_2y_v1 as census,
)


def test_series_rearm_census_contract_is_frozen() -> None:
    assert census.IDENTITY == (
        "QORE_CAPITALIZER_V3_SOURCE_FIRST_SERIES_REARM_CENSUS_2Y_V1"
    )
    assert census.EXPECTED_CLOSEBACKS == 8099
    assert census.EXPECTED_SOURCE_FIRST_MSS == 2692
    assert census.EXPECTED_CURRENT_V3_MSS == 1254
    assert census.EXPECTED_V3_ONLY == 87


def test_series_rearm_relation_partition() -> None:
    from datetime import UTC, datetime

    first = datetime(2026, 1, 1, 10, 0, tzinfo=UTC)
    later = datetime(2026, 1, 1, 10, 3, tzinfo=UTC)
    assert census._relation(first, first) == "SAME_CONFIRMATION"
    assert census._relation(first, later) == "PREEMPTS_REFERENCE"
    assert census._relation(later, first) == "LATER_THAN_REFERENCE"
    assert census._relation(first, None) == "RECOVERS_MISSING"
    assert census._relation(None, first) == "LOSES_REFERENCE"

from datetime import UTC, datetime

from qore.infrastructure.cibo_phase22_v4_m5_source import (
    MAX_CALENDAR_M5_BARS_PER_CHUNK,
    REQUIRED_SYMBOLS,
    v4_partition_grid,
)


def test_v4_m5_partition_grid_is_exact_candidate_window() -> None:
    partitions = v4_partition_grid()

    assert tuple(item.label for item in partitions) == (
        "2014-v4-a",
        "2015-v4-b",
    )
    assert partitions[0].opened_at == datetime(
        2014,
        10,
        19,
        tzinfo=UTC,
    )
    assert partitions[0].closed_at == datetime(
        2015,
        1,
        1,
        tzinfo=UTC,
    )
    assert partitions[1].opened_at == datetime(
        2015,
        1,
        1,
        tzinfo=UTC,
    )
    assert partitions[1].closed_at == datetime(
        2015,
        4,
        19,
        tzinfo=UTC,
    )


def test_v4_m5_source_surface_is_complete_and_transport_bounded() -> None:
    assert REQUIRED_SYMBOLS == (
        "AUDJPY",
        "AUDUSD",
        "EURUSD",
        "GBPJPY",
        "GBPUSD",
        "NAS100",
        "USDCAD",
        "USDJPY",
        "XAUUSD",
    )
    assert MAX_CALENDAR_M5_BARS_PER_CHUNK == 2016

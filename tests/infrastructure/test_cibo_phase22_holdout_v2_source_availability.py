from datetime import UTC, datetime

import pytest

from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)
from qore.infrastructure.cibo_phase22_holdout_v2_source_availability import (
    assess_boundary_probe,
    probe_windows,
)


def test_v2_probe_windows_are_boundary_only() -> None:
    start = datetime(2015, 10, 19, tzinfo=UTC)
    end = datetime(2016, 4, 19, tzinfo=UTC)

    first_m5, last_m5 = probe_windows(
        start_at=start,
        end_exclusive_at=end,
        timeframe="M5",
    )
    first_m1, last_m1 = probe_windows(
        start_at=start,
        end_exclusive_at=end,
        timeframe="M1",
    )

    assert first_m5 == (
        datetime(2015, 10, 19, tzinfo=UTC),
        datetime(2015, 10, 26, tzinfo=UTC),
    )
    assert last_m5 == (
        datetime(2016, 4, 12, tzinfo=UTC),
        datetime(2016, 4, 19, tzinfo=UTC),
    )
    assert first_m1 == (
        datetime(2015, 10, 19, tzinfo=UTC),
        datetime(2015, 10, 21, tzinfo=UTC),
    )
    assert last_m1 == (
        datetime(2016, 4, 17, tzinfo=UTC),
        datetime(2016, 4, 19, tzinfo=UTC),
    )


def test_v2_probe_requires_data_at_both_boundaries() -> None:
    start = datetime(2015, 10, 19, tzinfo=UTC)
    end = datetime(2016, 4, 19, tzinfo=UTC)
    first, last = probe_windows(
        start_at=start,
        end_exclusive_at=end,
        timeframe="M5",
    )

    report = assess_boundary_probe(
        symbol="EURUSD",
        provider_symbol="EURUSD",
        timeframe="M5",
        first_window=first,
        last_window=last,
        first_timestamps=(datetime(2015, 10, 19, 0, 0, tzinfo=UTC),),
        last_timestamps=(datetime(2016, 4, 18, 23, 55, tzinfo=UTC),),
    )
    assert report.available is True

    unavailable = assess_boundary_probe(
        symbol="EURUSD",
        provider_symbol="EURUSD",
        timeframe="M5",
        first_window=first,
        last_window=last,
        first_timestamps=(),
        last_timestamps=(datetime(2016, 4, 18, 23, 55, tzinfo=UTC),),
    )
    assert unavailable.available is False


def test_v2_probe_rejects_non_aligned_timestamp() -> None:
    start = datetime(2015, 10, 19, tzinfo=UTC)
    end = datetime(2016, 4, 19, tzinfo=UTC)
    first, last = probe_windows(
        start_at=start,
        end_exclusive_at=end,
        timeframe="M5",
    )

    with pytest.raises(CiboCapitalManagementError, match="alignment"):
        assess_boundary_probe(
            symbol="EURUSD",
            provider_symbol="EURUSD",
            timeframe="M5",
            first_window=first,
            last_window=last,
            first_timestamps=(datetime(2015, 10, 19, 0, 1, tzinfo=UTC),),
            last_timestamps=(datetime(2016, 4, 18, 23, 55, tzinfo=UTC),),
        )

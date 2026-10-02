from datetime import UTC, datetime

import pytest

from qore.infrastructure.cibo_capital_management_authority import (
    CiboCapitalManagementError,
)
from qore.infrastructure.cibo_phase22_next_exam_source_availability import (
    REQUIRED_M5_SYMBOLS,
    assess_boundary_probe,
    probe_windows,
)
from qore.infrastructure.cibo_phase22_next_exam_governance import (
    NEXT_PHASE22_CANDIDATE,
)


def test_next_probe_candidate_is_exact_preregistered_window() -> None:
    candidate = NEXT_PHASE22_CANDIDATE

    assert candidate.start_at == datetime(2015, 4, 19, tzinfo=UTC)
    assert candidate.end_exclusive_at == datetime(2015, 10, 19, tzinfo=UTC)
    assert candidate.outcome_data_inspected_at_selection is False
    assert candidate.source_validation_complete is False


def test_next_probe_windows_are_boundary_only() -> None:
    start = datetime(2015, 4, 19, tzinfo=UTC)
    end = datetime(2015, 10, 19, tzinfo=UTC)

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
        datetime(2015, 4, 19, tzinfo=UTC),
        datetime(2015, 4, 26, tzinfo=UTC),
    )
    assert last_m5 == (
        datetime(2015, 10, 12, tzinfo=UTC),
        datetime(2015, 10, 19, tzinfo=UTC),
    )
    assert first_m1 == (
        datetime(2015, 4, 19, tzinfo=UTC),
        datetime(2015, 4, 21, tzinfo=UTC),
    )
    assert last_m1 == (
        datetime(2015, 10, 17, tzinfo=UTC),
        datetime(2015, 10, 19, tzinfo=UTC),
    )


def test_next_probe_surface_is_exact() -> None:
    assert REQUIRED_M5_SYMBOLS == (
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


def test_next_probe_requires_data_at_both_boundaries() -> None:
    start = datetime(2015, 4, 19, tzinfo=UTC)
    end = datetime(2015, 10, 19, tzinfo=UTC)
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
        first_timestamps=(
            datetime(2015, 4, 20, 0, 0, tzinfo=UTC),
        ),
        last_timestamps=(
            datetime(2015, 10, 16, 23, 55, tzinfo=UTC),
        ),
    )
    assert report.available is True

    unavailable = assess_boundary_probe(
        symbol="EURUSD",
        provider_symbol="EURUSD",
        timeframe="M5",
        first_window=first,
        last_window=last,
        first_timestamps=(),
        last_timestamps=(
            datetime(2015, 10, 16, 23, 55, tzinfo=UTC),
        ),
    )
    assert unavailable.available is False


def test_next_probe_rejects_non_aligned_timestamp() -> None:
    start = datetime(2015, 4, 19, tzinfo=UTC)
    end = datetime(2015, 10, 19, tzinfo=UTC)
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
            first_timestamps=(
                datetime(2015, 4, 20, 0, 1, tzinfo=UTC),
            ),
            last_timestamps=(
                datetime(2015, 10, 16, 23, 55, tzinfo=UTC),
            ),
        )

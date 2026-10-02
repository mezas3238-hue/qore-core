from datetime import UTC, datetime, timedelta

from qore.infrastructure.cibo_phase22_v4_governance import PHASE22_V4_CANDIDATE
from qore.infrastructure.cibo_phase22_v4_m1_source import (
    CHUNK_DAYS,
    MAX_CALENDAR_BARS_PER_CHUNK,
    chunk_grid,
)


def test_v4_m1_chunk_grid_covers_exact_candidate() -> None:
    start = datetime(2014, 10, 19, tzinfo=UTC)
    end = datetime(2015, 4, 19, tzinfo=UTC)
    chunks = chunk_grid(start, end)

    assert PHASE22_V4_CANDIDATE.start_at == start
    assert PHASE22_V4_CANDIDATE.end_exclusive_at == end
    assert chunks[0][0] == start
    assert chunks[-1][1] == end
    assert all(left < right for left, right in chunks)
    assert all(
        right - left <= timedelta(days=CHUNK_DAYS)
        for left, right in chunks
    )
    assert all(
        chunks[index][1] == chunks[index + 1][0]
        for index in range(len(chunks) - 1)
    )


def test_v4_m1_transport_bound_matches_two_day_calendar() -> None:
    assert CHUNK_DAYS == 2
    assert MAX_CALENDAR_BARS_PER_CHUNK == 2880

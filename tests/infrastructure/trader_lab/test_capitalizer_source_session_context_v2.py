from datetime import UTC, datetime

from qore.infrastructure.trader_lab.capitalizer_contract import CapitalizerSession
from qore.infrastructure.trader_lab.capitalizer_source_session_context_v2 import (
    CapitalizerSourceSessionResolution,
    assess_source_session_context,
)


def test_london_source_window_is_0200_0500_new_york_dst_aware() -> None:
    inside = assess_source_session_context(
        session=CapitalizerSession.LONDON,
        observed_at=datetime(2026, 7, 1, 6, 30, tzinfo=UTC),
    )
    boundary_out = assess_source_session_context(
        session=CapitalizerSession.LONDON,
        observed_at=datetime(2026, 7, 1, 9, 0, tzinfo=UTC),
    )

    assert inside.resolution is CapitalizerSourceSessionResolution.ELIGIBLE
    assert inside.local_time.hour == 2
    assert inside.local_time.minute == 30
    assert boundary_out.resolution is CapitalizerSourceSessionResolution.OUTSIDE
    assert inside.qore_surveillance_bucket_equated_to_source_window is False


def test_new_york_source_window_is_0700_0900_new_york() -> None:
    inside = assess_source_session_context(
        session=CapitalizerSession.NEW_YORK,
        observed_at=datetime(2026, 1, 5, 12, 30, tzinfo=UTC),
    )
    before = assess_source_session_context(
        session=CapitalizerSession.NEW_YORK,
        observed_at=datetime(2026, 1, 5, 11, 59, tzinfo=UTC),
    )

    assert inside.resolution is CapitalizerSourceSessionResolution.ELIGIBLE
    assert inside.local_time.hour == 7
    assert inside.local_time.minute == 30
    assert before.resolution is CapitalizerSourceSessionResolution.OUTSIDE


def test_asian_exact_fixed_clock_fails_closed_pending_source_resolution() -> None:
    result = assess_source_session_context(
        session=CapitalizerSession.ASIA,
        observed_at=datetime(2026, 1, 5, 1, 0, tzinfo=UTC),
    )

    assert result.resolution is CapitalizerSourceSessionResolution.REVIEW_REQUIRED
    assert result.source_window_id == "ICT_ASIAN_KILLZONE_EXACT_CLOCK_REVIEW_REQUIRED"
    assert "EXACT_FIXED_CLOCK_NOT_FROZEN" in result.reasons
    assert result.qore_surveillance_bucket_equated_to_source_window is False

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


def test_asian_without_historical_open_reference_fails_closed() -> None:
    result = assess_source_session_context(
        session=CapitalizerSession.ASIA,
        observed_at=datetime(2026, 1, 5, 1, 0, tzinfo=UTC),
    )

    assert result.resolution is CapitalizerSourceSessionResolution.REVIEW_REQUIRED
    assert result.source_window_id == "ICT_ASIAN_OPEN_REFERENCE_REQUIRED"
    assert "SOURCE_USES_DST_RELATIVE_ASIAN_OPEN" in result.reasons
    assert result.qore_surveillance_bucket_equated_to_source_window is False


def test_asian_uses_two_hour_window_relative_to_historical_open_reference() -> None:
    asian_open = datetime(2026, 1, 5, 0, 0, tzinfo=UTC)
    inside = assess_source_session_context(
        session=CapitalizerSession.ASIA,
        observed_at=datetime(2026, 1, 5, 1, 30, tzinfo=UTC),
        asian_open_reference_at=asian_open,
    )
    boundary_out = assess_source_session_context(
        session=CapitalizerSession.ASIA,
        observed_at=datetime(2026, 1, 5, 2, 0, tzinfo=UTC),
        asian_open_reference_at=asian_open,
    )

    assert inside.resolution is CapitalizerSourceSessionResolution.ELIGIBLE
    assert inside.source_window_id == "ICT_ASIAN_OPEN_RELATIVE_TWO_HOUR_WINDOW"
    assert "NO_FIXED_1900_2000_ASSUMPTION" in inside.reasons
    assert boundary_out.resolution is CapitalizerSourceSessionResolution.OUTSIDE

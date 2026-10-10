"""DST-aware original V49 clock consistency does not certify ICT killzones."""
from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime

import pytest
from test_capitalizer_a1_source_sensor_independent_attestation_v1 import (
    _source,
)

from qore.infrastructure.trader_lab import (
    capitalizer_a1_native_source_session_clock_attestation_v1 as native_clock,
)
from qore.infrastructure.trader_lab.capitalizer_high_frequency_capacity_census_v49 import (
    V49Opportunity,
)
from qore.infrastructure.trader_lab.capitalizer_source_session_context_v2 import (
    CapitalizerSourceSessionResolution,
)


def _clock_case(
    *, session: str, symbol: str, time: datetime,
    operating_date: str,
) -> V49Opportunity:
    return replace(
        _source(), session=session, symbol=symbol,
        m1_trigger_confirmed_at=time.isoformat(),
        operating_date=operating_date,
    )


def test_asian_source_group_reconfirmed_but_author_open_not_invented() -> None:
    # 2026-01-05T01:04Z -> 2026-01-04 20:04 EST, Asian operation 04 Jan.
    src = _clock_case(
        session="ASIA", symbol="AUDJPY",
        time=datetime(2026, 1, 5, 1, 4, tzinfo=UTC),
        operating_date="2026-01-04",
    )
    clock = native_clock.assess_v49_source_clock(src)
    assert clock.qore_bucket_reconfirmed is (
        native_clock.ClockAttestationStatus.QORE_BUCKET_RECONFIRMED
    )
    assert clock.local_operating_day_reconfirmed
    assert clock.methodology_window_resolution is (
        CapitalizerSourceSessionResolution.REVIEW_REQUIRED
    )
    assert clock.new_york_utc_offset_minutes == -300
    assert clock.remaining_session_seconds == 5 * 3600 + 56 * 60
    assert not clock.source_author_fidelity_proven
    assert not clock.new_entry_veto


def test_london_and_ny_broad_source_window_are_independent() -> None:
    london = _clock_case(
        session="LONDON", symbol="EURUSD",
        time=datetime(2026, 1, 5, 8, tzinfo=UTC),
        operating_date="2026-01-05",
    )
    clock = native_clock.assess_v49_source_clock(london)
    assert clock.qore_bucket_reconfirmed is (
        native_clock.ClockAttestationStatus.QORE_BUCKET_RECONFIRMED
    )
    assert clock.local_operating_day_reconfirmed
    assert clock.methodology_window_resolution is (
        CapitalizerSourceSessionResolution.ELIGIBLE
    )
    # 09:00 NY belongs to the broad QORE NY research bucket,
    # not to author ICT NY killzone [07:00,09:00).
    ny = _clock_case(
        session="NEW_YORK", symbol="XAUUSD",
        time=datetime(2026, 1, 5, 14, tzinfo=UTC),
        operating_date="2026-01-05",
    )
    actual = native_clock.assess_v49_source_clock(ny)
    assert actual.qore_bucket_reconfirmed is (
        native_clock.ClockAttestationStatus.QORE_BUCKET_RECONFIRMED
    )
    assert actual.methodology_window_resolution is (
        CapitalizerSourceSessionResolution.OUTSIDE
    )
    assert not actual.new_entry_veto


def test_dst_conversions_do_not_use_fixed_new_york_offset() -> None:
    winter = native_clock.assess_v49_source_clock(_clock_case(
        session="NEW_YORK", symbol="NAS100",
        time=datetime(2026, 1, 5, 14, tzinfo=UTC),
        operating_date="2026-01-05",
    ))
    summer = native_clock.assess_v49_source_clock(_clock_case(
        session="NEW_YORK", symbol="NAS100",
        time=datetime(2026, 7, 1, 13, tzinfo=UTC),
        operating_date="2026-07-01",
    ))
    assert winter.new_york_utc_offset_minutes == -300
    assert summer.new_york_utc_offset_minutes == -240
    assert winter.new_york_local_time.endswith("-05:00")
    assert summer.new_york_local_time.endswith("-04:00")


def test_contradictory_source_does_not_silently_gain_clock_proof() -> None:
    source = _clock_case(
        session="ASIA", symbol="GBPJPY",
        time=datetime(2026, 1, 5, 8, tzinfo=UTC),
        operating_date="2026-01-05",
    )
    wrong = native_clock.assess_v49_source_clock(source)
    assert wrong.qore_bucket_reconfirmed is (
        native_clock.ClockAttestationStatus.QORE_BUCKET_CONTRADICTED
    )
    assert not wrong.local_operating_day_reconfirmed
    assert not wrong.within_qore_research_session
    assert wrong.remaining_session_seconds is None
    assert not wrong.new_entry_veto


def test_source_m1_naive_clock_is_not_allowed() -> None:
    source = replace(
        _source(), m1_trigger_confirmed_at="2026-01-05T01:04:00",
    )
    with pytest.raises(ValueError, match="timezone"):
        native_clock.assess_v49_source_clock(source)

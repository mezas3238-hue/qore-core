from datetime import UTC, datetime
from zoneinfo import ZoneInfo

from qore.infrastructure.core_stack_v2.shared_lab_temporal_context import (
    TemporalContextFailure,
    normalize_provider_local,
    validate_epoch_roundtrip,
    validate_session_rollover,
)


def test_provider_local_new_york_normalizes_to_expected_utc() -> None:
    local = datetime(2026, 3, 9, 9, 30, tzinfo=ZoneInfo("America/New_York"))
    expected = datetime(2026, 3, 9, 13, 30, tzinfo=UTC)
    receipt = normalize_provider_local(local, provider_timezone="America/New_York", expected_utc=expected)
    assert receipt.passed
    assert receipt.normalized_utc == expected


def test_provider_local_utc_mismatch_fails() -> None:
    local = datetime(2026, 3, 9, 9, 30, tzinfo=ZoneInfo("America/New_York"))
    wrong = datetime(2026, 3, 9, 14, 30, tzinfo=UTC)
    receipt = normalize_provider_local(local, provider_timezone="America/New_York", expected_utc=wrong)
    assert not receipt.passed
    assert TemporalContextFailure.PROVIDER_LOCAL_UTC_MISMATCH in receipt.failures


def test_naive_datetime_fails_closed() -> None:
    receipt = normalize_provider_local(datetime(2026, 1, 1, 0, 0), provider_timezone="UTC")
    assert not receipt.passed
    assert TemporalContextFailure.NAIVE_DATETIME in receipt.failures


def test_dst_fold_is_explicitly_flagged() -> None:
    local = datetime(2026, 11, 1, 1, 30, tzinfo=ZoneInfo("America/New_York"), fold=1)
    receipt = normalize_provider_local(local, provider_timezone="America/New_York")
    assert not receipt.passed
    assert TemporalContextFailure.DST_FOLD_AMBIGUOUS in receipt.failures


def test_epoch_roundtrip_exact_for_millisecond_boundary() -> None:
    ok, failures = validate_epoch_roundtrip(1_767_225_600_000_000_000)
    assert ok
    assert failures == ()


def test_session_rollover_requires_contract_permission() -> None:
    before = datetime(2026, 1, 1, 23, 59, tzinfo=UTC)
    after = datetime(2026, 1, 2, 0, 1, tzinfo=UTC)
    ok, failures = validate_session_rollover(
        previous_session_id="S1",
        current_session_id="S2",
        previous_utc=before,
        current_utc=after,
        rollover_allowed=False,
    )
    assert not ok
    assert TemporalContextFailure.SESSION_BOUNDARY_ROLLOVER in failures

    ok, failures = validate_session_rollover(
        previous_session_id="S1",
        current_session_id="S2",
        previous_utc=before,
        current_utc=after,
        rollover_allowed=True,
    )
    assert ok
    assert failures == ()

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID

import pytest

from qore.infrastructure.operational_persistence import (
    InMemoryOperationalPersistence,
    OperationalIdempotencyKey,
    OperationalPersistenceConflictError,
    OperationalPersistenceValidationError,
    OperationalRecordKey,
    OperationalWriteRequest,
)
from qore.kernel.result import Failure, Success

_NOW = datetime(2026, 8, 8, 5, 50, tzinfo=UTC)
_KEY = OperationalRecordKey("runtime.health.snapshot")
_IDEMPOTENCY = OperationalIdempotencyKey(
    UUID("ab000000-0000-0000-0000-000000000001")
)


def _request(
    *,
    expected_version: int = 0,
    idempotency_key: OperationalIdempotencyKey = _IDEMPOTENCY,
    value: str = "ready",
) -> OperationalWriteRequest:
    return OperationalWriteRequest(
        key=_KEY,
        idempotency_key=idempotency_key,
        expected_version=expected_version,
        persisted_at=_NOW + timedelta(seconds=expected_version),
        values={"runtime.state": value},
    )


def test_first_write_creates_version_one_and_read_returns_snapshot() -> None:
    store = InMemoryOperationalPersistence()

    written = store.write(_request())
    read = store.read(_KEY)

    assert isinstance(written, Success)
    assert written.value.record.version == 1
    assert isinstance(read, Success)
    assert read.value == written.value.record


def test_identical_idempotent_replay_returns_exact_same_receipt() -> None:
    store = InMemoryOperationalPersistence()
    request = _request()

    first = store.write(request)
    replay = store.write(request)

    assert isinstance(first, Success)
    assert isinstance(replay, Success)
    assert replay.value is first.value


def test_idempotency_key_collision_with_different_intent_fails() -> None:
    store = InMemoryOperationalPersistence()
    first = store.write(_request())
    collision = store.write(_request(value="degraded"))

    assert isinstance(first, Success)
    assert isinstance(collision, Failure)
    assert isinstance(collision.error, OperationalPersistenceConflictError)


def test_expected_version_conflict_fails_without_overwrite() -> None:
    store = InMemoryOperationalPersistence()
    first = store.write(_request())
    second = store.write(
        _request(
            expected_version=0,
            idempotency_key=OperationalIdempotencyKey(
                UUID("ab000000-0000-0000-0000-000000000002")
            ),
            value="degraded",
        )
    )

    assert isinstance(first, Success)
    assert isinstance(second, Failure)
    assert isinstance(second.error, OperationalPersistenceConflictError)
    read = store.read(_KEY)
    assert isinstance(read, Success)
    assert read.value == first.value.record


def test_next_version_write_succeeds_with_new_idempotency_key() -> None:
    store = InMemoryOperationalPersistence()
    first = store.write(_request())
    second = store.write(
        _request(
            expected_version=1,
            idempotency_key=OperationalIdempotencyKey(
                UUID("ab000000-0000-0000-0000-000000000003")
            ),
            value="degraded",
        )
    )

    assert isinstance(first, Success)
    assert isinstance(second, Success)
    assert second.value.record.version == 2
    assert second.value.record.values["runtime.state"] == "degraded"


def test_operational_keys_reject_trading_namespaces() -> None:
    for value in (
        "runtime.order.state",
        "position.snapshot",
        "trade.audit",
        "broker.health",
        "execution.receipt",
    ):
        with pytest.raises(OperationalPersistenceValidationError):
            OperationalRecordKey(value)


def test_operational_values_reject_secret_like_keys_and_material() -> None:
    with pytest.raises(OperationalPersistenceValidationError):
        OperationalWriteRequest(
            key=_KEY,
            idempotency_key=_IDEMPOTENCY,
            expected_version=0,
            persisted_at=_NOW,
            values={"provider.api_token": "redacted"},
        )
    with pytest.raises(OperationalPersistenceValidationError):
        OperationalWriteRequest(
            key=_KEY,
            idempotency_key=_IDEMPOTENCY,
            expected_version=0,
            persisted_at=_NOW,
            values={"provider.header": "Bearer must-not-appear"},
        )


def test_expected_version_rejects_bool() -> None:
    with pytest.raises(OperationalPersistenceValidationError):
        OperationalWriteRequest(
            key=_KEY,
            idempotency_key=_IDEMPOTENCY,
            expected_version=True,
            persisted_at=_NOW,
        )


def test_missing_record_reads_as_none() -> None:
    store = InMemoryOperationalPersistence()
    result = store.read(OperationalRecordKey("runtime.missing"))

    assert isinstance(result, Success)
    assert result.value is None

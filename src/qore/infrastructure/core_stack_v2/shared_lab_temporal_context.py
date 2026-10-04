"""Timezone, DST, epoch and session-boundary reality for QORE Shared Lab."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from zoneinfo import ZoneInfo


class TemporalContextFailure(StrEnum):
    NAIVE_DATETIME = "NAIVE_DATETIME"
    TIMEZONE_MISMATCH = "TIMEZONE_MISMATCH"
    PROVIDER_LOCAL_UTC_MISMATCH = "PROVIDER_LOCAL_UTC_MISMATCH"
    EPOCH_CONVERSION_MISMATCH = "EPOCH_CONVERSION_MISMATCH"
    DST_FOLD_AMBIGUOUS = "DST_FOLD_AMBIGUOUS"
    SESSION_BOUNDARY_ROLLOVER = "SESSION_BOUNDARY_ROLLOVER"


@dataclass(frozen=True, slots=True)
class TemporalContextReceipt:
    provider_local: datetime
    normalized_utc: datetime | None
    expected_utc: datetime | None
    failures: tuple[TemporalContextFailure, ...]

    @property
    def passed(self) -> bool:
        return self.normalized_utc is not None and not self.failures


def normalize_provider_local(
    provider_local: datetime,
    *,
    provider_timezone: str,
    expected_utc: datetime | None = None,
) -> TemporalContextReceipt:
    failures: list[TemporalContextFailure] = []
    if provider_local.tzinfo is None:
        return TemporalContextReceipt(
            provider_local, None, expected_utc, (TemporalContextFailure.NAIVE_DATETIME,)
        )

    zone = ZoneInfo(provider_timezone)
    local_in_zone = provider_local.astimezone(zone)
    normalized = local_in_zone.astimezone(UTC)

    if expected_utc is not None:
        if expected_utc.tzinfo is None:
            failures.append(TemporalContextFailure.TIMEZONE_MISMATCH)
        elif normalized != expected_utc.astimezone(UTC):
            failures.append(TemporalContextFailure.PROVIDER_LOCAL_UTC_MISMATCH)

    if getattr(provider_local, "fold", 0) == 1:
        failures.append(TemporalContextFailure.DST_FOLD_AMBIGUOUS)

    return TemporalContextReceipt(provider_local, normalized, expected_utc, tuple(failures))


def epoch_ns_to_utc(epoch_ns: int) -> datetime:
    if epoch_ns < 0:
        raise ValueError("epoch_ns cannot be negative")
    return datetime.fromtimestamp(epoch_ns / 1_000_000_000, tz=UTC)


def validate_epoch_roundtrip(epoch_ns: int) -> tuple[bool, tuple[TemporalContextFailure, ...]]:
    converted = epoch_ns_to_utc(epoch_ns)
    roundtrip = int(converted.timestamp() * 1_000_000_000)
    if roundtrip != epoch_ns:
        return False, (TemporalContextFailure.EPOCH_CONVERSION_MISMATCH,)
    return True, ()


def validate_session_rollover(
    *,
    previous_session_id: str,
    current_session_id: str,
    previous_utc: datetime,
    current_utc: datetime,
    rollover_allowed: bool,
) -> tuple[bool, tuple[TemporalContextFailure, ...]]:
    changed = previous_session_id != current_session_id
    chronological = current_utc >= previous_utc
    if changed and not rollover_allowed:
        return False, (TemporalContextFailure.SESSION_BOUNDARY_ROLLOVER,)
    if not chronological:
        return False, (TemporalContextFailure.SESSION_BOUNDARY_ROLLOVER,)
    return True, ()

"""MC-28 runtime clock-drift diagnostic over bounded remote references."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from typing import Final

from qore.infrastructure.ctrader_open_api_client import (
    CTraderOpenApiClientError,
    CTraderOpenApiMessageClientBoundary,
)
from qore.kernel.result import Failure, Result, Success

IDENTITY: Final = "QORE_SHARED_MC28_RUNTIME_CLOCK_DRIFT_DIAGNOSTIC_001"
MAX_ABSOLUTE_CLOCK_OFFSET_MS: Final = 1_000
MAX_WALL_MONOTONIC_DIVERGENCE_MS: Final = 100
TRANSPORT_JITTER_MARGIN_MS: Final = 250
MINIMUM_REAL_SAMPLES: Final = 5

_CLOCK_READ_ONLY_REQUESTS: Final = frozenset(
    {
        "ProtoOASymbolsListReq",
        "ProtoOASubscribeSpotsReq",
    }
)


def _aware_utc(value: datetime, *, field_name: str) -> datetime:
    if (
        not isinstance(value, datetime)
        or value.tzinfo is None
        or value.utcoffset() is None
    ):
        raise ValueError(f"{field_name} must be timezone-aware datetime")
    return value.astimezone(UTC)


class RuntimeClockStatus(StrEnum):
    PASS = "PASS"
    DRIFT = "DRIFT"
    INSUFFICIENT = "INSUFFICIENT"


@dataclass(frozen=True, slots=True)
class RuntimeClockReferenceSample:
    sample_id: str
    provider_event_at: datetime
    local_received_at: datetime
    transport_upper_bound_ms: int
    local_wall_elapsed_ms: int
    local_monotonic_elapsed_ms: int

    def __post_init__(self) -> None:
        if not self.sample_id.strip():
            raise ValueError("sample_id must be non-empty")
        _aware_utc(self.provider_event_at, field_name="provider_event_at")
        _aware_utc(self.local_received_at, field_name="local_received_at")
        for name in (
            "transport_upper_bound_ms",
            "local_wall_elapsed_ms",
            "local_monotonic_elapsed_ms",
        ):
            value = getattr(self, name)
            if type(value) is not int or value < 0:
                raise ValueError(f"{name} must be non-negative int")

    @property
    def provider_minus_local_receive_ms(self) -> int:
        delta = (
            _aware_utc(
                self.provider_event_at,
                field_name="provider_event_at",
            )
            - _aware_utc(
                self.local_received_at,
                field_name="local_received_at",
            )
        )
        return round(delta.total_seconds() * 1000)

    @property
    def offset_lower_bound_ms(self) -> int:
        return self.provider_minus_local_receive_ms

    @property
    def offset_upper_bound_ms(self) -> int:
        return (
            self.provider_minus_local_receive_ms
            + self.transport_upper_bound_ms
        )

    @property
    def wall_monotonic_divergence_ms(self) -> int:
        return abs(
            self.local_wall_elapsed_ms
            - self.local_monotonic_elapsed_ms
        )


@dataclass(frozen=True, slots=True)
class RuntimeClockAssessment:
    status: RuntimeClockStatus
    sample_count: int
    offset_lower_bound_ms: int | None
    offset_upper_bound_ms: int | None
    max_wall_monotonic_divergence_ms: int | None
    reason_codes: tuple[str, ...]

    @property
    def diagnostic_pass(self) -> bool:
        return self.status is RuntimeClockStatus.PASS


def assess_runtime_clock(
    samples: tuple[RuntimeClockReferenceSample, ...],
    *,
    maximum_absolute_clock_offset_ms: int = MAX_ABSOLUTE_CLOCK_OFFSET_MS,
    maximum_wall_monotonic_divergence_ms: int = (
        MAX_WALL_MONOTONIC_DIVERGENCE_MS
    ),
    minimum_real_samples: int = MINIMUM_REAL_SAMPLES,
) -> RuntimeClockAssessment:
    """Bound provider-vs-local clock offset without assuming zero network delay.

    For a spot event, let d = provider_timestamp - local_receive_timestamp.
    If one-way transport delay is conservatively bounded by R, the provider
    clock offset relative to local time lies in [d, d + R]. Intersecting those
    intervals across independent events prevents network delay from being
    mislabelled as clock drift.
    """

    for name, value in (
        ("maximum_absolute_clock_offset_ms", maximum_absolute_clock_offset_ms),
        (
            "maximum_wall_monotonic_divergence_ms",
            maximum_wall_monotonic_divergence_ms,
        ),
        ("minimum_real_samples", minimum_real_samples),
    ):
        if type(value) is not int or value <= 0:
            raise ValueError(f"{name} must be positive int")

    if len(samples) < minimum_real_samples:
        return RuntimeClockAssessment(
            status=RuntimeClockStatus.INSUFFICIENT,
            sample_count=len(samples),
            offset_lower_bound_ms=None,
            offset_upper_bound_ms=None,
            max_wall_monotonic_divergence_ms=(
                max(
                    (
                        item.wall_monotonic_divergence_ms
                        for item in samples
                    ),
                    default=None,
                )
            ),
            reason_codes=("INSUFFICIENT_REAL_CLOCK_SAMPLES",),
        )

    sample_ids = [item.sample_id for item in samples]
    if sample_ids != sorted(set(sample_ids)):
        raise ValueError("clock sample ids must be unique and canonical")

    provider_times = [
        _aware_utc(item.provider_event_at, field_name="provider_event_at")
        for item in samples
    ]
    if any(
        right <= left
        for left, right in zip(
            provider_times,
            provider_times[1:],
            strict=False,
        )
    ):
        return RuntimeClockAssessment(
            status=RuntimeClockStatus.INSUFFICIENT,
            sample_count=len(samples),
            offset_lower_bound_ms=None,
            offset_upper_bound_ms=None,
            max_wall_monotonic_divergence_ms=max(
                item.wall_monotonic_divergence_ms
                for item in samples
            ),
            reason_codes=("PROVIDER_CLOCK_NOT_STRICTLY_INCREASING",),
        )

    max_divergence = max(
        item.wall_monotonic_divergence_ms
        for item in samples
    )
    if max_divergence > maximum_wall_monotonic_divergence_ms:
        return RuntimeClockAssessment(
            status=RuntimeClockStatus.DRIFT,
            sample_count=len(samples),
            offset_lower_bound_ms=None,
            offset_upper_bound_ms=None,
            max_wall_monotonic_divergence_ms=max_divergence,
            reason_codes=("LOCAL_WALL_CLOCK_INSTABILITY_DETECTED",),
        )

    lower = max(item.offset_lower_bound_ms for item in samples)
    upper = min(item.offset_upper_bound_ms for item in samples)
    if lower > upper:
        return RuntimeClockAssessment(
            status=RuntimeClockStatus.INSUFFICIENT,
            sample_count=len(samples),
            offset_lower_bound_ms=lower,
            offset_upper_bound_ms=upper,
            max_wall_monotonic_divergence_ms=max_divergence,
            reason_codes=("TRANSPORT_BOUND_INCONSISTENT",),
        )

    limit = maximum_absolute_clock_offset_ms
    if lower >= -limit and upper <= limit:
        return RuntimeClockAssessment(
            status=RuntimeClockStatus.PASS,
            sample_count=len(samples),
            offset_lower_bound_ms=lower,
            offset_upper_bound_ms=upper,
            max_wall_monotonic_divergence_ms=max_divergence,
            reason_codes=("CLOCK_OFFSET_BOUNDED_WITHIN_FROZEN_LIMIT",),
        )
    if lower > limit or upper < -limit:
        return RuntimeClockAssessment(
            status=RuntimeClockStatus.DRIFT,
            sample_count=len(samples),
            offset_lower_bound_ms=lower,
            offset_upper_bound_ms=upper,
            max_wall_monotonic_divergence_ms=max_divergence,
            reason_codes=("CLOCK_OFFSET_OUTSIDE_FROZEN_LIMIT",),
        )
    return RuntimeClockAssessment(
        status=RuntimeClockStatus.INSUFFICIENT,
        sample_count=len(samples),
        offset_lower_bound_ms=lower,
        offset_upper_bound_ms=upper,
        max_wall_monotonic_divergence_ms=max_divergence,
        reason_codes=("CLOCK_OFFSET_BOUND_OVERLAPS_FROZEN_LIMIT",),
    )


class CTraderClockReadOnlyMessageClient:
    """Fail-closed cTrader wrapper admitting only clock-observation messages."""

    __slots__ = ("_client",)

    def __init__(self, client: CTraderOpenApiMessageClientBoundary) -> None:
        self._client = client

    @property
    def is_ready(self) -> bool:
        return self._client.is_ready

    @property
    def account_id(self) -> int:
        return self._client.account_id

    def connect_and_authenticate(
        self,
    ) -> Result[None, CTraderOpenApiClientError]:
        return self._client.connect_and_authenticate()

    def request(
        self,
        message_name: str,
        fields: Mapping[str, object],
        *,
        client_msg_id: str,
        timeout_seconds: float,
    ) -> Result[object, CTraderOpenApiClientError]:
        if message_name not in _CLOCK_READ_ONLY_REQUESTS:
            return Failure(
                CTraderOpenApiClientError(
                    "clock diagnostic rejected non-read-only provider message"
                )
            )
        result = self._client.request(
            message_name,
            fields,
            client_msg_id=client_msg_id,
            timeout_seconds=timeout_seconds,
        )
        if isinstance(result, Failure):
            return result
        return Success(result.value)

    def wait_for_event(
        self,
        message_name: str,
        *,
        timeout_seconds: float,
        predicate: Callable[[object], bool] | None = None,
    ) -> Result[object, CTraderOpenApiClientError]:
        if message_name != "ProtoOASpotEvent":
            return Failure(
                CTraderOpenApiClientError(
                    "clock diagnostic rejected non-spot provider event"
                )
            )
        return self._client.wait_for_event(
            message_name,
            timeout_seconds=timeout_seconds,
            predicate=predicate,
        )

    def close(self) -> None:
        self._client.close()

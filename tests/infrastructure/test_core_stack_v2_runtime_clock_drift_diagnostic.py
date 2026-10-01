from __future__ import annotations

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

from qore.infrastructure.core_stack_v2.runtime_clock_drift_diagnostic import (
    CTraderClockReadOnlyMessageClient,
    RuntimeClockReferenceSample,
    RuntimeClockStatus,
    assess_runtime_clock,
)
from qore.infrastructure.ctrader_open_api_client import (
    CTraderOpenApiClientError,
)
from qore.kernel.result import Failure, Success

_BASE = datetime(2026, 9, 30, 12, 0, tzinfo=UTC)


def _sample(
    index: int,
    *,
    provider_offset_ms: int,
    transport_delay_ms: int = 100,
    transport_bound_ms: int = 250,
    wall_elapsed_ms: int = 100,
    monotonic_elapsed_ms: int = 100,
) -> RuntimeClockReferenceSample:
    received = _BASE + timedelta(seconds=index)
    provider = received + timedelta(
        milliseconds=provider_offset_ms - transport_delay_ms
    )
    return RuntimeClockReferenceSample(
        sample_id=f"{index:03d}",
        provider_event_at=provider,
        local_received_at=received,
        transport_upper_bound_ms=transport_bound_ms,
        local_wall_elapsed_ms=wall_elapsed_ms,
        local_monotonic_elapsed_ms=monotonic_elapsed_ms,
    )


def test_runtime_clock_passes_when_bounded_offset_is_inside_limit() -> None:
    samples = tuple(
        _sample(index, provider_offset_ms=100)
        for index in range(5)
    )
    result = assess_runtime_clock(samples)
    assert result.status is RuntimeClockStatus.PASS
    assert result.offset_lower_bound_ms == 0
    assert result.offset_upper_bound_ms == 250


def test_runtime_clock_detects_positive_provider_clock_drift() -> None:
    samples = tuple(
        _sample(index, provider_offset_ms=2_500)
        for index in range(5)
    )
    result = assess_runtime_clock(samples)
    assert result.status is RuntimeClockStatus.DRIFT
    assert "CLOCK_OFFSET_OUTSIDE_FROZEN_LIMIT" in result.reason_codes


def test_runtime_clock_detects_negative_provider_clock_drift() -> None:
    samples = tuple(
        _sample(index, provider_offset_ms=-2_500)
        for index in range(5)
    )
    result = assess_runtime_clock(samples)
    assert result.status is RuntimeClockStatus.DRIFT
    assert "CLOCK_OFFSET_OUTSIDE_FROZEN_LIMIT" in result.reason_codes


def test_runtime_clock_abstains_when_bound_overlaps_limit() -> None:
    samples = tuple(
        _sample(
            index,
            provider_offset_ms=1_050,
            transport_delay_ms=100,
            transport_bound_ms=250,
        )
        for index in range(5)
    )
    result = assess_runtime_clock(samples)
    assert result.status is RuntimeClockStatus.INSUFFICIENT
    assert "CLOCK_OFFSET_BOUND_OVERLAPS_FROZEN_LIMIT" in result.reason_codes


def test_runtime_clock_detects_local_wall_clock_instability() -> None:
    samples = tuple(
        _sample(
            index,
            provider_offset_ms=0,
            wall_elapsed_ms=400 if index == 3 else 100,
            monotonic_elapsed_ms=100,
        )
        for index in range(5)
    )
    result = assess_runtime_clock(samples)
    assert result.status is RuntimeClockStatus.DRIFT
    assert "LOCAL_WALL_CLOCK_INSTABILITY_DETECTED" in result.reason_codes


class _FakeClient:
    is_ready = True
    account_id = 424242

    def connect_and_authenticate(self):
        return Success(None)

    def request(
        self,
        message_name,
        fields,
        *,
        client_msg_id,
        timeout_seconds,
    ):
        del fields, client_msg_id, timeout_seconds
        return Success(SimpleNamespace(message_name=message_name))

    def wait_for_event(
        self,
        message_name,
        *,
        timeout_seconds,
        predicate=None,
    ):
        del timeout_seconds, predicate
        return Success(SimpleNamespace(message_name=message_name))

    def close(self):
        return None


def test_clock_client_firewall_rejects_mutating_provider_message() -> None:
    client = CTraderClockReadOnlyMessageClient(_FakeClient())
    rejected = client.request(
        "ProtoOANewOrderReq",
        {"ctidTraderAccountId": 424242},
        client_msg_id="forbidden",
        timeout_seconds=1.0,
    )
    assert isinstance(rejected, Failure)
    assert isinstance(rejected.error, CTraderOpenApiClientError)


def test_clock_client_allows_only_spot_clock_observation() -> None:
    client = CTraderClockReadOnlyMessageClient(_FakeClient())
    assert isinstance(
        client.request(
            "ProtoOASymbolsListReq",
            {"ctidTraderAccountId": 424242},
            client_msg_id="symbols",
            timeout_seconds=1.0,
        ),
        Success,
    )
    assert isinstance(
        client.request(
            "ProtoOASubscribeSpotsReq",
            {
                "ctidTraderAccountId": 424242,
                "subscribeToSpotTimestamp": True,
                "symbolId": [1],
            },
            client_msg_id="spots",
            timeout_seconds=1.0,
        ),
        Success,
    )
    rejected = client.wait_for_event(
        "ProtoOAExecutionEvent",
        timeout_seconds=1.0,
    )
    assert isinstance(rejected, Failure)

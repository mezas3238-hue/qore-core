from __future__ import annotations

from types import SimpleNamespace
from typing import cast

from qore.infrastructure.ctrader_open_api_client import (
    CTraderOpenApiCredentials,
    SpotwareCTraderOpenApiClient,
    _SdkBindings,
)
from qore.kernel.result import Success


class _NativeClient:
    def __init__(self, *_args: object, **_kwargs: object) -> None:
        self.message_callback = None

    def __getattr__(self, name: str) -> object:
        if name == "setMessageReceivedCallback":
            return lambda callback: setattr(self, "message_callback", callback)
        if name in {"setConnectedCallback", "setDisconnectedCallback"}:
            return lambda callback: None
        raise AttributeError(name)


class _Heartbeat:
    pass


class _Invalidated:
    pass


class _Spot:
    pass


class _Execution:
    pass


class _OrderError:
    pass


class _Response:
    pass


def _client() -> SpotwareCTraderOpenApiClient:
    messages = {
        "ProtoHeartbeatEvent": _Heartbeat,
        "ProtoOAAccountsTokenInvalidatedEvent": _Invalidated,
        "ProtoOASpotEvent": _Spot,
        "ProtoOAExecutionEvent": _Execution,
        "ProtoOAOrderErrorEvent": _OrderError,
        "ProtoOAResponse": _Response,
    }
    bindings = SimpleNamespace(
        client_type=_NativeClient,
        tcp_protocol=object,
        reactor=object(),
        extract=lambda value: value,
        messages=messages,
    )
    return SpotwareCTraderOpenApiClient(
        credentials=CTraderOpenApiCredentials(
            client_id="client",
            client_secret="secret",
            access_token="access",
            refresh_token="refresh",
            ctid_trader_account_id=42,
        ),
        _bindings=cast(_SdkBindings, bindings),
    )


def test_spot_wait_does_not_scan_or_requeue_unrelated_messages() -> None:
    client = _client()
    native = object.__getattribute__(client, "_client")
    heartbeat = _Heartbeat()
    spot = _Spot()
    for _ in range(5_000):
        client._on_message(native, heartbeat)
    client._on_message(native, _Response())
    client._on_message(native, spot)

    queues = object.__getattribute__(client, "_event_queues")
    heartbeat_depth = queues[_Heartbeat].qsize()
    result = client.wait_for_event("ProtoOASpotEvent", timeout_seconds=0.01)

    assert isinstance(result, Success)
    assert result.value is spot
    assert queues[_Heartbeat].qsize() == heartbeat_depth == 5_000
    assert _Response not in queues

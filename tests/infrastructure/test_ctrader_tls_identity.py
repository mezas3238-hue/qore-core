from __future__ import annotations

import inspect
import ssl
from types import SimpleNamespace
from typing import Any, cast

from qore.infrastructure import ctrader_open_api_client as client_module
from qore.infrastructure.ctrader_open_api_client import (
    CTraderOpenApiConnectionError,
    CTraderOpenApiCredentials,
    SpotwareCTraderOpenApiClient,
    _SdkBindings,
    _verified_tls_endpoint_description,
    verify_ctrader_tls_server_identity,
)
from qore.kernel.result import Failure


class _ContextResource:
    def __enter__(self) -> _ContextResource:
        return self

    def __exit__(self, *_args: object) -> None:
        return None

    def getpeercert(self) -> dict[str, str]:
        return {"subject": "demo.ctraderapi.com"}


class _VerifiedContext:
    verify_mode = ssl.CERT_REQUIRED
    check_hostname = True

    def __init__(self) -> None:
        self.server_hostname: str | None = None

    def wrap_socket(
        self, connection: object, *, server_hostname: str
    ) -> _ContextResource:
        del connection
        self.server_hostname = server_hostname
        return _ContextResource()


class _NeverStartedClient:
    def __init__(self, *_args: object, **_kwargs: object) -> None:
        self.started = False

    def __getattr__(self, name: str) -> object:
        if name in {
            "setConnectedCallback",
            "setDisconnectedCallback",
            "setMessageReceivedCallback",
        }:
            return lambda callback: None
        if name == "startService":
            return self._start
        raise AttributeError(name)

    def _start(self) -> None:
        self.started = True


def _credentials() -> CTraderOpenApiCredentials:
    return CTraderOpenApiCredentials(
        client_id="client",
        client_secret="secret",
        access_token="access",
        refresh_token="refresh",
        ctid_trader_account_id=42,
    )


def test_sdk_endpoint_requires_hostname_service_identity() -> None:
    assert _verified_tls_endpoint_description("demo.ctraderapi.com", 5035) == (
        "ssl:host=demo.ctraderapi.com:port=5035:hostname=demo.ctraderapi.com"
    )


def test_platform_tls_verifier_uses_ca_policy_and_exact_hostname(
    monkeypatch: Any,
) -> None:
    context = _VerifiedContext()
    tls_module = cast(Any, vars(client_module)["ssl"])
    socket_module = cast(Any, vars(client_module)["socket"])
    monkeypatch.setattr(tls_module, "create_default_context", lambda: context)
    monkeypatch.setattr(
        socket_module,
        "create_connection",
        lambda address, timeout: _ContextResource(),
    )

    verify_ctrader_tls_server_identity("demo.ctraderapi.com", 5035, 1.0)

    assert context.verify_mode is ssl.CERT_REQUIRED
    assert context.check_hostname is True
    assert context.server_hostname == "demo.ctraderapi.com"


def test_invalid_certificate_identity_prevents_session_or_trading() -> None:
    bindings = SimpleNamespace(
        client_type=_NeverStartedClient,
        tcp_protocol=object,
        reactor=object(),
        extract=lambda value: value,
        messages={},
    )

    def invalid_identity(host: str, port: int, timeout_seconds: float) -> None:
        del host, port, timeout_seconds
        raise ssl.SSLCertVerificationError("hostname mismatch")

    client = SpotwareCTraderOpenApiClient(
        credentials=_credentials(),
        server_identity_verifier=invalid_identity,
        _bindings=cast(_SdkBindings, bindings),
    )
    result = client.connect_and_authenticate()

    assert isinstance(result, Failure)
    assert isinstance(result.error, CTraderOpenApiConnectionError)
    native = cast(_NeverStartedClient, object.__getattribute__(client, "_client"))
    assert native.started is False
    assert client.is_ready is False


def test_qore_ctrader_client_contains_no_insecure_tls_bypass() -> None:
    source = inspect.getsource(client_module)
    assert "CERT_NONE" not in source
    assert "check_hostname = False" not in source
    assert "verify=False" not in source

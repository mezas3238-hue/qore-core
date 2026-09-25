"""Fail-closed discovery of the single cTrader DEMO account authorized by a token.

This bootstrap is intentionally read-only. It authenticates the Open API application,
queries the account list attached to the supplied access token, refreshes the token in
memory if necessary, and returns an account id only when exactly one account is
explicitly classified as DEMO. It never submits, amends, or cancels an order.
"""

from __future__ import annotations

import os
from collections.abc import Callable, Iterable
from threading import Event, Lock, Thread
from time import monotonic
from typing import cast

from qore.infrastructure.ctrader_open_api_client import (
    CTraderOpenApiClientError,
    _SdkBindings,
    verify_ctrader_tls_server_identity,
)
from qore.kernel.errors import InfrastructureError


class CTraderDemoAccountDiscoveryError(InfrastructureError):
    """The DEMO account could not be discovered without ambiguity."""

    __slots__ = ()


def _required_env(name: str, *aliases: str) -> str:
    for candidate in (name, *aliases):
        value = os.environ.get(candidate, "")
        if value:
            return value
    raise CTraderDemoAccountDiscoveryError(
        f"missing required environment input: {name}"
    )


def _set_sdk_field(value: object, name: str, field_value: object) -> None:
    """Assign a provider-defined Protobuf field without weakening static typing."""

    try:
        setattr(value, name, field_value)
    except (AttributeError, TypeError, ValueError) as error:
        raise CTraderDemoAccountDiscoveryError(
            f"invalid cTrader discovery request field: {name}"
        ) from error


def _has_explicit_is_live(account: object) -> bool:
    has_field = getattr(account, "HasField", None)
    if callable(has_field):
        try:
            return has_field("isLive") is True
        except (TypeError, ValueError):
            return False
    return hasattr(account, "isLive")


def select_single_demo_account_id(accounts: Iterable[object]) -> int:
    """Return one exact DEMO id and reject zero, multiple, or ambiguous accounts."""

    demo_ids: list[int] = []
    for account in accounts:
        if not _has_explicit_is_live(account):
            continue
        if getattr(account, "isLive", None) is not False:
            continue
        account_id = getattr(account, "ctidTraderAccountId", None)
        if type(account_id) is not int or account_id <= 0:
            raise CTraderDemoAccountDiscoveryError(
                "cTrader DEMO account id must be an explicit positive int"
            )
        demo_ids.append(account_id)
    if len(demo_ids) != 1:
        raise CTraderDemoAccountDiscoveryError(
            "cTrader token must authorize exactly one explicitly classified DEMO account"
        )
    return demo_ids[0]


_REACTOR_LOCK = Lock()


def _method(value: object, name: str) -> Callable[..., object]:
    member = getattr(value, name, None)
    if not callable(member):
        raise CTraderDemoAccountDiscoveryError(
            f"official cTrader SDK is missing required member {name}"
        )
    return cast(Callable[..., object], member)


def _ensure_reactor_running(reactor: object) -> None:
    if getattr(reactor, "running", None) is True:
        return
    with _REACTOR_LOCK:
        if getattr(reactor, "running", None) is True:
            return
        run = _method(reactor, "run")
        thread = Thread(
            target=lambda: run(installSignalHandlers=False),
            name="qore-ctrader-account-discovery-reactor",
            daemon=True,
        )
        thread.start()
        deadline = monotonic() + 5.0
        while getattr(reactor, "running", None) is not True and monotonic() < deadline:
            Event().wait(0.01)
        if getattr(reactor, "running", None) is not True:
            raise CTraderDemoAccountDiscoveryError(
                "cTrader Open API reactor did not enter running state"
            )


def discover_single_ctrader_demo_account_id(
    *,
    client_id: str,
    client_secret: str,
    access_token: str,
    refresh_token: str,
    timeout_seconds: float = 10.0,
) -> int:
    """Authenticate read-only and discover exactly one DEMO account from the token."""

    for name, value in (
        ("client_id", client_id),
        ("client_secret", client_secret),
        ("access_token", access_token),
        ("refresh_token", refresh_token),
    ):
        if not isinstance(value, str) or not value:
            raise CTraderDemoAccountDiscoveryError(f"{name} must be a non-empty secret")
    if not isinstance(timeout_seconds, float) or timeout_seconds <= 0:
        raise CTraderDemoAccountDiscoveryError("timeout_seconds must be positive")

    try:
        bindings = _SdkBindings()
        client_type = bindings.client_type
        tcp_protocol = bindings.tcp_protocol
        extract = bindings.extract
        reactor = bindings.reactor
    except CTraderOpenApiClientError as error:
        raise CTraderDemoAccountDiscoveryError(
            "install the qore-core ctrader optional dependency"
        ) from error

    app_req_type = bindings.messages.get("ProtoOAApplicationAuthReq")
    app_res_type = bindings.messages.get("ProtoOAApplicationAuthRes")
    accounts_req_type = bindings.messages.get("ProtoOAGetAccountListByAccessTokenReq")
    accounts_res_type = bindings.messages.get("ProtoOAGetAccountListByAccessTokenRes")
    refresh_req_type = bindings.messages.get("ProtoOARefreshTokenReq")
    refresh_res_type = bindings.messages.get("ProtoOARefreshTokenRes")
    required_types = (
        app_req_type,
        app_res_type,
        accounts_req_type,
        accounts_res_type,
        refresh_req_type,
        refresh_res_type,
    )
    if any(item is None for item in required_types):
        raise CTraderDemoAccountDiscoveryError(
            "official cTrader SDK is missing required authentication messages"
        )
    assert app_req_type is not None
    assert app_res_type is not None
    assert accounts_req_type is not None
    assert accounts_res_type is not None
    assert refresh_req_type is not None
    assert refresh_res_type is not None

    client = client_type(
        "demo.ctraderapi.com",
        5035,
        tcp_protocol,
        numberOfMessagesToSendPerSecond=5,
    )
    connected = Event()
    disconnected = Event()
    _method(client, "setConnectedCallback")(
        lambda received: connected.set() if received is client else None
    )
    _method(client, "setDisconnectedCallback")(
        lambda received, reason: disconnected.set() if received is client else None
    )

    def request(message: object, client_msg_id: str) -> object:
        completed = Event()
        responses: list[object] = []
        failures: list[object] = []

        def send() -> None:
            deferred = _method(client, "send")(
                message,
                clientMsgId=client_msg_id,
                responseTimeoutInSeconds=timeout_seconds,
            )

            def succeeded(value: object) -> object:
                responses.append(value)
                completed.set()
                return value

            def failed(value: object) -> object:
                failures.append(value)
                completed.set()
                return value

            _method(deferred, "addCallbacks")(succeeded, failed)

        _method(reactor, "callFromThread")(send)
        if not completed.wait(timeout_seconds + 0.5):
            raise CTraderDemoAccountDiscoveryError("cTrader discovery request timed out")
        if failures or not responses:
            raise CTraderDemoAccountDiscoveryError("cTrader discovery request failed")
        try:
            return extract(responses[0])
        except (KeyError, TypeError, ValueError) as error:
            raise CTraderDemoAccountDiscoveryError(
                "cTrader discovery response could not be decoded"
            ) from error

    current_access_token = access_token
    try:
        try:
            verify_ctrader_tls_server_identity(
                "demo.ctraderapi.com",
                5035,
                timeout_seconds,
            )
        except (CTraderOpenApiClientError, OSError) as error:
            raise CTraderDemoAccountDiscoveryError(
                "cTrader DEMO TLS server identity verification failed"
            ) from error
        _ensure_reactor_running(reactor)
        _method(reactor, "callFromThread")(_method(client, "startService"))
        if not connected.wait(timeout_seconds) or disconnected.is_set():
            raise CTraderDemoAccountDiscoveryError(
                "cTrader DEMO TLS connect timed out or disconnected"
            )

        app_req = app_req_type()
        _set_sdk_field(app_req, "clientId", client_id)
        _set_sdk_field(app_req, "clientSecret", client_secret)
        app_response = request(app_req, "qore-demo-account-discovery-app-auth")
        if not isinstance(app_response, app_res_type):
            raise CTraderDemoAccountDiscoveryError(
                "cTrader application authentication failed"
            )

        def account_list(token: str, suffix: str) -> object:
            account_req = accounts_req_type()
            _set_sdk_field(account_req, "accessToken", token)
            return request(account_req, f"qore-demo-account-discovery-{suffix}")

        accounts_response = account_list(current_access_token, "account-list")
        if not isinstance(accounts_response, accounts_res_type):
            refresh_req = refresh_req_type()
            _set_sdk_field(refresh_req, "refreshToken", refresh_token)
            refreshed = request(refresh_req, "qore-demo-account-discovery-refresh")
            if not isinstance(refreshed, refresh_res_type):
                raise CTraderDemoAccountDiscoveryError(
                    "cTrader access token invalid and refresh failed"
                )
            refreshed_access = getattr(refreshed, "accessToken", None)
            if not isinstance(refreshed_access, str) or not refreshed_access:
                raise CTraderDemoAccountDiscoveryError(
                    "cTrader token refresh omitted access token"
                )
            current_access_token = refreshed_access
            accounts_response = account_list(
                current_access_token,
                "account-list-after-refresh",
            )
        if not isinstance(accounts_response, accounts_res_type):
            raise CTraderDemoAccountDiscoveryError(
                "cTrader account-list authentication failed"
            )
        if getattr(accounts_response, "permissionScope", None) != 1:
            raise CTraderDemoAccountDiscoveryError(
                "cTrader token does not carry trading permission"
            )
        entries = getattr(accounts_response, "ctidTraderAccount", None)
        if entries is None:
            raise CTraderDemoAccountDiscoveryError(
                "cTrader token returned no account evidence"
            )
        return select_single_demo_account_id(cast(Iterable[object], entries))
    finally:
        stop = getattr(client, "stopService", None)
        if callable(stop) and getattr(reactor, "running", None) is True:
            _method(reactor, "callFromThread")(stop)


def main() -> None:
    account_id = discover_single_ctrader_demo_account_id(
        client_id=_required_env("QORE_CTRADER_CLIENT_ID", "QORE_CTRADER_DEMO_CLIENT_ID"),
        client_secret=_required_env(
            "QORE_CTRADER_CLIENT_SECRET", "QORE_CTRADER_DEMO_CLIENT_SECRET"
        ),
        access_token=_required_env(
            "QORE_CTRADER_ACCESS_TOKEN", "QORE_CTRADER_DEMO_ACCESS_TOKEN"
        ),
        refresh_token=_required_env(
            "QORE_CTRADER_REFRESH_TOKEN", "QORE_CTRADER_DEMO_REFRESH_TOKEN"
        ),
    )
    print(account_id)


if __name__ == "__main__":
    main()

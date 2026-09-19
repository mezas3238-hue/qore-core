from __future__ import annotations

import socket
import ssl
from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass, field
from importlib import import_module
from queue import Empty, Queue
from threading import Event, Lock, Thread
from time import monotonic
from typing import Protocol, cast

from qore.infrastructure.ports import ExternalPortError
from qore.kernel.result import Failure, Result, Success


class CTraderOpenApiClientError(ExternalPortError):
    """Sanitized base error for the Spotware Open API client boundary."""

    __slots__ = ()


class CTraderOpenApiDependencyError(CTraderOpenApiClientError):
    """The optional official cTrader Python SDK is unavailable."""

    __slots__ = ()


class CTraderOpenApiConnectionError(CTraderOpenApiClientError):
    """The DEMO TLS session could not reach an authenticated ready state."""

    __slots__ = ()


class CTraderOpenApiProtocolError(CTraderOpenApiClientError):
    """The provider returned an unexpected or unsafe protocol message."""

    __slots__ = ()


@dataclass(frozen=True, slots=True, repr=False)
class CTraderOpenApiCredentials:
    """Secret-bearing credentials; values never participate in repr or equality."""

    client_id: str = field(repr=False, compare=False, hash=False)
    client_secret: str = field(repr=False, compare=False, hash=False)
    access_token: str = field(repr=False, compare=False, hash=False)
    refresh_token: str = field(repr=False, compare=False, hash=False)
    ctid_trader_account_id: int

    def __post_init__(self) -> None:
        for name, value in (
            ("client_id", self.client_id),
            ("client_secret", self.client_secret),
            ("access_token", self.access_token),
            ("refresh_token", self.refresh_token),
        ):
            if not isinstance(value, str) or not value:
                raise CTraderOpenApiProtocolError(f"{name} must be a non-empty secret")
        if type(self.ctid_trader_account_id) is not int or self.ctid_trader_account_id <= 0:
            raise CTraderOpenApiProtocolError("ctid_trader_account_id must be a positive int")

    def __repr__(self) -> str:
        return (
            "CTraderOpenApiCredentials(client_id=<redacted>, "
            "client_secret=<redacted>, access_token=<redacted>, "
            "refresh_token=<redacted>, "
            f"ctid_trader_account_id={self.ctid_trader_account_id})"
        )


class CTraderOpenApiMessageClientBoundary(Protocol):
    """Synchronous QORE-facing port over the SDK's asynchronous message client."""

    @property
    def is_ready(self) -> bool: ...

    @property
    def account_id(self) -> int: ...

    def connect_and_authenticate(self) -> Result[None, CTraderOpenApiClientError]: ...

    def request(
        self,
        message_name: str,
        fields: Mapping[str, object],
        *,
        client_msg_id: str,
        timeout_seconds: float,
    ) -> Result[object, CTraderOpenApiClientError]: ...

    def wait_for_event(
        self,
        message_name: str,
        *,
        timeout_seconds: float,
        predicate: Callable[[object], bool] | None = None,
    ) -> Result[object, CTraderOpenApiClientError]: ...

    def close(self) -> None: ...


class CTraderTlsServerIdentityVerifier(Protocol):
    """Verify CA chain and exact DNS identity before session authentication."""

    def __call__(self, host: str, port: int, timeout_seconds: float) -> None: ...


def verify_ctrader_tls_server_identity(
    host: str,
    port: int,
    timeout_seconds: float,
) -> None:
    """Perform a fail-closed CA + hostname handshake using platform trust roots."""
    context = ssl.create_default_context()
    if context.verify_mode is not ssl.CERT_REQUIRED or context.check_hostname is not True:
        raise CTraderOpenApiConnectionError("secure TLS identity policy is unavailable")
    with socket.create_connection((host, port), timeout=timeout_seconds) as connection:
        with context.wrap_socket(connection, server_hostname=host) as verified:
            if not verified.getpeercert():
                raise CTraderOpenApiConnectionError(
                    "cTrader DEMO TLS peer omitted certificate identity"
                )


def _verified_tls_endpoint_description(host: str, port: int) -> str:
    """Twisted endpoint with mandatory DNS service-identity verification."""
    return f"ssl:host={host}:port={port}:hostname={host}"


def _attribute(value: object, name: str) -> object:
    try:
        return getattr(value, name)
    except AttributeError as error:
        raise CTraderOpenApiDependencyError(
            f"official cTrader SDK is missing required member {name}"
        ) from error


def _method(value: object, name: str) -> Callable[..., object]:
    method = _attribute(value, name)
    if not callable(method):
        raise CTraderOpenApiDependencyError(f"official cTrader SDK member {name} is not callable")
    return cast(Callable[..., object], method)


class _SdkBindings:
    """Late-bound official SDK symbols, keeping the dependency optional for Core."""

    __slots__ = ("client_type", "extract", "messages", "reactor", "tcp_protocol")

    def __init__(self) -> None:
        try:
            package = import_module("ctrader_open_api")
            common = import_module("ctrader_open_api.messages.OpenApiCommonMessages_pb2")
            messages = import_module("ctrader_open_api.messages.OpenApiMessages_pb2")
            reactor_module = import_module("twisted.internet.reactor")
            application_internet = import_module("twisted.application.internet")
            endpoints = import_module("twisted.internet.endpoints")
            sdk_factory_module = import_module("ctrader_open_api.factory")
        except ImportError as error:
            raise CTraderOpenApiDependencyError(
                "install the qore-core ctrader optional dependency"
            ) from error

        sdk_client_type = cast(type[object], _attribute(package, "Client"))
        client_service = cast(type[object], _attribute(application_internet, "ClientService"))
        client_from_string = _method(endpoints, "clientFromString")
        factory_type = _attribute(sdk_factory_module, "Factory")

        def verified_identity_init(
            client: object,
            host: str,
            port: int,
            protocol: type[object],
            **options: int,
        ) -> None:
            send_rate = options.pop("numberOfMessagesToSendPerSecond", 5)
            if options:
                raise CTraderOpenApiDependencyError(
                    "verified SDK client received unsupported options"
                )
            client_state = vars(client)
            client_state["_runningReactor"] = reactor_module
            client_state["numberOfMessagesToSendPerSecond"] = send_rate
            endpoint = client_from_string(
                reactor_module,
                _verified_tls_endpoint_description(host, port),
            )
            factory = _method(factory_type, "forProtocol")(protocol, client=client)
            _method(client_service, "__init__")(client, endpoint, factory)
            client_state["_events"] = {}
            client_state["_responseDeferreds"] = {}
            client_state["isConnected"] = False

        verified_client_type = type(
            "VerifiedIdentityClient",
            (sdk_client_type,),
            {"__init__": verified_identity_init},
        )
        self.client_type = cast(Callable[..., object], verified_client_type)
        self.tcp_protocol = cast(type[object], _attribute(package, "TcpProtocol"))
        protobuf = _attribute(package, "Protobuf")
        self.extract = cast(Callable[[object], object], _method(protobuf, "extract"))
        self.reactor = reactor_module
        names = (
            "ProtoOAApplicationAuthReq",
            "ProtoOAApplicationAuthRes",
            "ProtoHeartbeatEvent",
            "ProtoOAGetAccountListByAccessTokenReq",
            "ProtoOAGetAccountListByAccessTokenRes",
            "ProtoOARefreshTokenReq",
            "ProtoOARefreshTokenRes",
            "ProtoOAAccountsTokenInvalidatedEvent",
            "ProtoOAAccountAuthReq",
            "ProtoOAAccountAuthRes",
            "ProtoOANewOrderReq",
            "ProtoOASymbolsListReq",
            "ProtoOASymbolsListRes",
            "ProtoOASymbolByIdReq",
            "ProtoOASymbolByIdRes",
            "ProtoOACancelOrderReq",
            "ProtoOAOrderListReq",
            "ProtoOAOrderDetailsReq",
            "ProtoOAReconcileReq",
            "ProtoOAGetTrendbarsReq",
            "ProtoOASubscribeSpotsReq",
            "ProtoOASpotEvent",
            "ProtoOAExecutionEvent",
            "ProtoOAOrderErrorEvent",
            "ProtoOAErrorRes",
        )
        resolved: dict[str, type[object]] = {}
        for name in names:
            module = common if hasattr(common, name) else messages
            symbol = getattr(module, name, None)
            if not isinstance(symbol, type):
                raise CTraderOpenApiDependencyError(
                    f"official cTrader SDK is missing required message {name}"
                )
            resolved[name] = symbol
        self.messages = resolved


_REACTOR_START_LOCK = Lock()


def _reactor_running(reactor: object) -> bool:
    return _attribute(reactor, "running") is True


def _ensure_reactor_running(reactor: object) -> None:
    if _reactor_running(reactor):
        return
    with _REACTOR_START_LOCK:
        if _reactor_running(reactor):
            return
        run = _method(reactor, "run")
        thread = Thread(
            target=lambda: run(installSignalHandlers=False),
            name="qore-ctrader-open-api-reactor",
            daemon=True,
        )
        thread.start()
        deadline = monotonic() + 5.0
        while not _reactor_running(reactor) and monotonic() < deadline:
            Event().wait(0.01)
        if not _reactor_running(reactor):
            raise CTraderOpenApiConnectionError(
                "cTrader Open API reactor did not enter running state"
            )


class SpotwareCTraderOpenApiClient:
    """Concrete official-SDK client, permanently pinned to the DEMO TLS endpoint."""

    __slots__ = (
        "_bindings",
        "_client",
        "_connected",
        "_credentials",
        "_disconnected",
        "_events",
        "_ready",
        "_access_token",
        "_refresh_token",
        "_request_timeout_seconds",
        "_server_identity_verifier",
    )

    DEMO_HOST = "demo.ctraderapi.com"
    PROTOBUF_PORT = 5035

    def __init__(
        self,
        *,
        credentials: CTraderOpenApiCredentials,
        request_timeout_seconds: float = 10.0,
        server_identity_verifier: CTraderTlsServerIdentityVerifier | None = None,
        _bindings: _SdkBindings | None = None,
    ) -> None:
        if not isinstance(credentials, CTraderOpenApiCredentials):
            raise CTraderOpenApiProtocolError("credentials must be CTraderOpenApiCredentials")
        if not isinstance(request_timeout_seconds, float) or request_timeout_seconds <= 0.0:
            raise CTraderOpenApiProtocolError("request_timeout_seconds must be a positive float")
        bindings = _bindings or _SdkBindings()
        self._bindings = bindings
        self._credentials = credentials
        self._access_token = credentials.access_token
        self._refresh_token = credentials.refresh_token
        self._request_timeout_seconds = request_timeout_seconds
        self._server_identity_verifier = (
            server_identity_verifier or verify_ctrader_tls_server_identity
        )
        self._connected = Event()
        self._disconnected = Event()
        self._ready = False
        self._events: Queue[object] = Queue()
        self._client = bindings.client_type(
            self.DEMO_HOST,
            self.PROTOBUF_PORT,
            bindings.tcp_protocol,
            numberOfMessagesToSendPerSecond=5,
        )
        _method(self._client, "setConnectedCallback")(self._on_connected)
        _method(self._client, "setDisconnectedCallback")(self._on_disconnected)
        _method(self._client, "setMessageReceivedCallback")(self._on_message)

    @property
    def is_ready(self) -> bool:
        return self._ready and not self._disconnected.is_set()

    @property
    def account_id(self) -> int:
        return self._credentials.ctid_trader_account_id

    def _on_connected(self, client: object) -> None:
        if client is self._client:
            self._connected.set()

    def _on_disconnected(self, client: object, reason: object) -> None:
        del reason
        if client is self._client:
            self._ready = False
            self._disconnected.set()

    def _on_message(self, client: object, message: object) -> None:
        if client is not self._client:
            return
        try:
            extracted = self._bindings.extract(message)
        except (KeyError, ValueError, TypeError):
            return
        invalidated_type = self._bindings.messages["ProtoOAAccountsTokenInvalidatedEvent"]
        if isinstance(extracted, invalidated_type):
            account_ids = getattr(extracted, "ctidTraderAccountIds", ())
            if self.account_id in account_ids:
                self._ready = False
        self._events.put(extracted)

    def _message(self, name: str, fields: Mapping[str, object]) -> object:
        message_type = self._bindings.messages.get(name)
        if message_type is None:
            raise CTraderOpenApiProtocolError(
                "cTrader request message is not admitted by this runtime"
            )
        message = message_type()
        for field_name, value in fields.items():
            if not isinstance(field_name, str) or not field_name:
                raise CTraderOpenApiProtocolError("cTrader request fields require non-empty names")
            try:
                if isinstance(value, (list, tuple)):
                    repeated = _attribute(message, field_name)
                    _method(repeated, "extend")(value)
                else:
                    setattr(message, field_name, value)
            except (AttributeError, TypeError, ValueError) as error:
                raise CTraderOpenApiProtocolError(
                    f"invalid cTrader request field: {field_name}"
                ) from error
        return message

    def request(
        self,
        message_name: str,
        fields: Mapping[str, object],
        *,
        client_msg_id: str,
        timeout_seconds: float,
    ) -> Result[object, CTraderOpenApiClientError]:
        if not self._connected.is_set() or self._disconnected.is_set():
            return Failure(CTraderOpenApiConnectionError("cTrader session is not connected"))
        if not isinstance(client_msg_id, str) or not client_msg_id:
            return Failure(CTraderOpenApiProtocolError("client_msg_id must be non-empty"))
        if not isinstance(timeout_seconds, float) or timeout_seconds <= 0.0:
            return Failure(CTraderOpenApiProtocolError("timeout_seconds must be positive"))
        try:
            message = self._message(message_name, fields)
        except CTraderOpenApiClientError as error:
            return Failure(error)
        completed = Event()
        response: list[object] = []
        failed: list[object] = []

        def send_on_reactor() -> None:
            deferred = _method(self._client, "send")(
                message,
                clientMsgId=client_msg_id,
                responseTimeoutInSeconds=timeout_seconds,
            )

            def succeeded(value: object) -> object:
                response.append(value)
                completed.set()
                return value

            def errored(value: object) -> object:
                failed.append(value)
                completed.set()
                return value

            _method(deferred, "addCallbacks")(succeeded, errored)

        _method(self._bindings.reactor, "callFromThread")(send_on_reactor)
        if not completed.wait(timeout_seconds + 0.5):
            return Failure(CTraderOpenApiConnectionError("cTrader request timed out"))
        if failed or not response:
            return Failure(CTraderOpenApiConnectionError("cTrader request failed"))
        try:
            extracted = self._bindings.extract(response[0])
        except (KeyError, ValueError, TypeError):
            return Failure(CTraderOpenApiProtocolError("cTrader response could not be decoded"))
        error_types = (
            self._bindings.messages["ProtoOAErrorRes"],
            self._bindings.messages["ProtoOAOrderErrorEvent"],
        )
        if isinstance(extracted, error_types):
            error_code = getattr(extracted, "errorCode", "UNKNOWN")
            if not isinstance(error_code, str) or not error_code:
                error_code = "UNKNOWN"
            return Failure(CTraderOpenApiProtocolError(f"cTrader request rejected: {error_code}"))
        return Success(extracted)

    def _authenticate_request(
        self, name: str, fields: Mapping[str, object], client_msg_id: str
    ) -> Result[object, CTraderOpenApiClientError]:
        return self.request(
            name,
            fields,
            client_msg_id=client_msg_id,
            timeout_seconds=self._request_timeout_seconds,
        )

    def _refresh_tokens(self) -> Result[None, CTraderOpenApiClientError]:
        refreshed = self._authenticate_request(
            "ProtoOARefreshTokenReq",
            {"refreshToken": self._refresh_token},
            "qore-token-refresh",
        )
        if isinstance(refreshed, Failure):
            return refreshed
        if not isinstance(
            refreshed.value,
            self._bindings.messages["ProtoOARefreshTokenRes"],
        ):
            return Failure(CTraderOpenApiProtocolError("unexpected token refresh response"))
        access_token = getattr(refreshed.value, "accessToken", None)
        refresh_token = getattr(refreshed.value, "refreshToken", None)
        if not isinstance(access_token, str) or not access_token:
            return Failure(CTraderOpenApiProtocolError("token refresh omitted access token"))
        if not isinstance(refresh_token, str) or not refresh_token:
            return Failure(CTraderOpenApiProtocolError("token refresh omitted refresh token"))
        self._access_token = access_token
        self._refresh_token = refresh_token
        return Success(None)

    def connect_and_authenticate(self) -> Result[None, CTraderOpenApiClientError]:
        if self.is_ready:
            return Success(None)
        self._disconnected.clear()
        try:
            self._server_identity_verifier(
                self.DEMO_HOST,
                self.PROTOBUF_PORT,
                self._request_timeout_seconds,
            )
        except (CTraderOpenApiClientError, OSError, ssl.SSLError):
            return Failure(
                CTraderOpenApiConnectionError(
                    "cTrader DEMO TLS server identity verification failed"
                )
            )
        try:
            _ensure_reactor_running(self._bindings.reactor)
            _method(self._bindings.reactor, "callFromThread")(_method(self._client, "startService"))
        except CTraderOpenApiClientError as error:
            return Failure(error)
        if not self._connected.wait(self._request_timeout_seconds):
            return Failure(CTraderOpenApiConnectionError("cTrader DEMO TLS connect timed out"))

        app = self._authenticate_request(
            "ProtoOAApplicationAuthReq",
            {
                "clientId": self._credentials.client_id,
                "clientSecret": self._credentials.client_secret,
            },
            "qore-app-auth",
        )
        if isinstance(app, Failure):
            return app
        if not isinstance(app.value, self._bindings.messages["ProtoOAApplicationAuthRes"]):
            return Failure(CTraderOpenApiProtocolError("unexpected application auth response"))
        accounts = self._authenticate_request(
            "ProtoOAGetAccountListByAccessTokenReq",
            {"accessToken": self._access_token},
            "qore-account-list",
        )
        if isinstance(accounts, Failure):
            refreshed = self._refresh_tokens()
            if isinstance(refreshed, Failure):
                return accounts
            accounts = self._authenticate_request(
                "ProtoOAGetAccountListByAccessTokenReq",
                {"accessToken": self._access_token},
                "qore-account-list-after-refresh",
            )
            if isinstance(accounts, Failure):
                return accounts
        account_entries = getattr(accounts.value, "ctidTraderAccount", None)
        permission_scope = getattr(accounts.value, "permissionScope", None)
        if permission_scope != 1 or account_entries is None:
            return Failure(
                CTraderOpenApiProtocolError(
                    "cTrader token lacks trading permission or account evidence"
                )
            )
        selected: object | None = None
        if not isinstance(
            accounts.value,
            self._bindings.messages["ProtoOAGetAccountListByAccessTokenRes"],
        ):
            return Failure(CTraderOpenApiProtocolError("unexpected account-list response"))
        accounts_iterable = cast(Iterable[object], account_entries)
        for account in accounts_iterable:
            if (
                getattr(account, "ctidTraderAccountId", None)
                == self._credentials.ctid_trader_account_id
            ):
                selected = account
                break
        if selected is None:
            return Failure(CTraderOpenApiProtocolError("configured account is not authorized"))
        has_field = getattr(selected, "HasField", None)
        is_live_present = True
        if callable(has_field):
            try:
                is_live_present = has_field("isLive") is True
            except (TypeError, ValueError):
                is_live_present = False
        if not is_live_present or getattr(selected, "isLive", None) is not False:
            return Failure(
                CTraderOpenApiProtocolError(
                    "configured cTrader account is LIVE or ambiguously classified"
                )
            )
        account_auth = self._authenticate_request(
            "ProtoOAAccountAuthReq",
            {
                "ctidTraderAccountId": self._credentials.ctid_trader_account_id,
                "accessToken": self._access_token,
            },
            "qore-account-auth",
        )
        if isinstance(account_auth, Failure):
            return account_auth
        if not isinstance(
            account_auth.value,
            self._bindings.messages["ProtoOAAccountAuthRes"],
        ):
            return Failure(CTraderOpenApiProtocolError("unexpected account auth response"))
        if (
            getattr(account_auth.value, "ctidTraderAccountId", None)
            != self._credentials.ctid_trader_account_id
        ):
            return Failure(CTraderOpenApiProtocolError("account auth response mismatch"))
        self._ready = True
        return Success(None)

    def wait_for_event(
        self,
        message_name: str,
        *,
        timeout_seconds: float,
        predicate: Callable[[object], bool] | None = None,
    ) -> Result[object, CTraderOpenApiClientError]:
        message_type = self._bindings.messages.get(message_name)
        if message_type is None:
            return Failure(CTraderOpenApiProtocolError("unknown cTrader event type"))
        deadline = monotonic() + timeout_seconds
        deferred: list[object] = []
        while monotonic() < deadline:
            try:
                event = self._events.get(timeout=max(0.01, deadline - monotonic()))
            except Empty:
                break
            if isinstance(event, message_type) and (predicate is None or predicate(event)):
                for item in deferred:
                    self._events.put(item)
                return Success(event)
            deferred.append(event)
        for item in deferred:
            self._events.put(item)
        return Failure(CTraderOpenApiConnectionError("cTrader event wait timed out"))

    def close(self) -> None:
        self._ready = False
        stop = _method(self._client, "stopService")
        if _reactor_running(self._bindings.reactor):
            _method(self._bindings.reactor, "callFromThread")(stop)
